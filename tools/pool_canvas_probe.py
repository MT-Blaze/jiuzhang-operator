# -*- coding: utf-8 -*-
"""军令 #32 · S6d-browser：重题池画布九条真人路径 + 逐像素色值证据（测试工程师）。

产品代码（``app/``、``plugins/``、``static/``）全程只读；点按与按键一律走
Playwright 的真实输入（鼠标事件 + 键盘事件），不用 ``element.focus()`` /
``dispatchEvent`` 冒充人手。reduced-motion 用 ``emulate_media``，不用假时钟。

隔离：随机端口 + 独立 JZO_DATA_DIR/JZO_PLUGINS_DIR + 自带一次性令牌 +
JZO_RESTART_DISABLED=1；显式删掉 JZO_POOL_ADMIT_DISABLED（要验的就是生产那条
自动抽走链）；绝不碰仓库 ``data/`` 里的真实库。

证据落点：``.qoder/records/biz/2026-11/20261103_order32-s6-evidence/``
  · 画布截图 → ``s6b-shots/<tag>-<序号>-<内容>.png``
  · 辅助栏截图与 DOM 转储 → ``s6b-panels/<tag>-<序号>-<内容>.png/.txt``
  · 结果 JSON → ``<tag>-browser-result.toml``
所有文件只新增不覆盖：撞名自动加 ``-1/-2`` 后缀。

用法：``.venv\\Scripts\\python.exe tools\\pool_canvas_probe.py <tag>``
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.pixel_scan import decode_png  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / ".qoder" / "records" / "biz" / "2026-11" / "20261103_order32-s6-evidence"
SHOTS = EVID / "s6b-shots"
PANELS = EVID / "s6b-panels"
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
TOKEN = "pool-canvas-probe-token"
AMBER = (192, 138, 46)        # --amber #c08a2e
DANGER = (155, 59, 45)         # --danger 实测 computed #9b3b2d（layout_canvas.css:661-665 亮灯帧 boxShadow 反读），旧值 #d33 作废
CHECKS: list[dict] = []
NOTES: dict[str, object] = {}
TIERS: dict[str, object] = {}
CONSOLE: dict[str, list[str]] = {"boot": [], "review": [], "pool": []}
PAGE_ERRORS: list[str] = []
POOL_RESPONSES: list[str] = []

S1 = ("S6d 原题甲：已知 $x^2-5x+6=0$，求它的两个根之和（　　）。"
      "选项 A $5$、B $6$、C $11$、D $1$，答案 A。")
S2 = ("S6d 原题乙：数列 $\\{a_n\\}$ 满足 $a_n=2n-1$，求前 3 项的和（　　）。"
      "选项 A $9$、B $6$、C $3$、D $12$，答案 A。")
S3 = ("S6d 原题丙：已知 $x^2-7x+12=0$，求它的两个根之积（　　）。"
      "选项 A $12$、B $7$、C $5$、D $14$，答案 A。")
D3 = ("S6d 丙的近形：已知 $x^2-9x+20=0$，求它的两个根之积（　　）。"
      "选项 A $20$、B $9$、C $4$、D $18$，答案 A。")
R2_STEM = ("S6d 未清项题：已知 $a_n=$（待识别），求它的前三项和（　　）。"
           "选项 A $6$、B $3$、C $9$、D $12$，答案 A。")


def check(name: str, ok: object, detail: object = None) -> None:
    CHECKS.append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " | "
          + wire.dumps(detail, ensure_ascii=False, default=str)[:700], flush=True)


def guarded(name: str, fn) -> None:
    """一条路径塌了不许带走后面八条：异常就地记成该条的失败证据。"""
    try:
        fn()
    except Exception as exc:
        import traceback
        check(name, False, {"probe_exception": f"{type(exc).__name__}: {exc}",
                            "trace_tail": traceback.format_exc().splitlines()[-3:]})


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _decode(resp) -> tuple[int, dict]:
    body = resp.read().decode("utf-8", errors="replace")
    try:
        return int(getattr(resp, "status", 200)), wire.loads(body or "{}")
    except wire.JSONDecodeError:
        return int(getattr(resp, "status", 200)), {"raw": body[:300]}


def GET(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return _decode(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        e.close()
        try:
            return e.code, wire.loads(body or "{}")
        except wire.JSONDecodeError:
            return e.code, {"raw": body[:300]}


def POST(url: str, payload: object) -> tuple[int, dict]:
    req = urllib.request.Request(url, data=wire.dumps(payload, ensure_ascii=False).encode(),
                                 method="POST",
                                 headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return _decode(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        e.close()
        try:
            return e.code, wire.loads(body or "{}")
        except wire.JSONDecodeError:
            return e.code, {"raw": body[:300]}


def wait_health(base: str, proc, log: Path) -> None:
    end = time.time() + 90
    while time.time() < end:
        if proc.poll() is not None:
            raise RuntimeError("服务早退：" + log.read_text(encoding="utf-8", errors="replace")[-2000:])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.6) as r:
                if r.status == 200:
                    return
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("服务未就绪")


_FRAME_PROBE = """(sel) => {
  const n = document.querySelector(sel);
  if (!n) return null;
  const b = n.getBoundingClientRect(), cs = getComputedStyle(n);
  let slot = null, hostIframeRect = null, e = n;
  while (e && !slot) { slot = e.getAttribute && (e.getAttribute('data-slot')
      || e.getAttribute('data-area') || e.getAttribute('data-zone')); e = e.parentElement; }
  return {exists: true, hidden: n.hidden === true, display: cs.display,
          visibility: cs.visibility, rect: [Math.round(b.x), Math.round(b.y),
          Math.round(b.width), Math.round(b.height)],
          nonZero: b.width > 0 && b.height > 0, slot: slot};
}"""


def frame_with(page, sel, timeout=30):
    """按「页签身份」认帧，不再靠首个 id 命中（军令 #32 · S6d 修正 ①）。

    实况（S6d 帧普查原始输出）：画布页签与辅助栏是**同一份 index.html 的两个实例**，
    两个帧里 `#edRoot` 与 `#epRoot` 都存在，但不属于自己那一侧的根节点永久 hidden、
    rect 全 0。旧写法「第一个 query_selector 命中的帧就返回」把 panel 交到了画布帧的
    死副本上，于是 `epPoolList_children=0`、`epDock=[0,0]`、`[data-tier]` 点击超时
    全部是**探针无效**。这里改成两把键：
      ① 元素存在且 `hidden!==true`、`display!=='none'`、`visibility!=='hidden'`、
         rect 宽高都 >0 —— 这一帧真的在渲染它；
      ② 仍有多个候选时，用宿主侧 `data-slot/data-area/data-zone` 祖先做二级键。
    每一轮的候选与最终选择写进 NOTES["frame_choice"]，逐条可复核。
    """
    end = time.time() + timeout
    while time.time() < end:
        cands = []
        for i, fr in enumerate(page.frames):
            try:
                st = fr.evaluate(_FRAME_PROBE, sel)
            except Exception:
                continue
            if not st:
                continue
            if st.get("hidden") is False and st.get("nonZero") \
                    and st.get("display") not in (None, "none") \
                    and st.get("visibility") != "hidden":
                cands.append((i, fr, st))
        NOTES.setdefault("frame_choice", []).append(
            {"sel": sel, "candidates": [[c[0], c[2]["rect"], c[2]["slot"]] for c in cands]})
        if cands:
            return cands[0][1]
        time.sleep(0.2)
    NOTES.setdefault("frame_choice", []).append({"sel": sel, "candidates": [], "result": "NONE"})
    return None


def reopen_editor(page, wait_ms: int = 3500):
    """reload 之后必须真人再点一次【录题工作台】（军令 #32 · S6d 修正 ②）。

    开机默认落数据看板，插件帧随 reload 退场；不点回来 `frame_with` 只会返回 None，
    紧接着的 `panel.evaluate(...)` 就抛 `AttributeError: 'NoneType' object has no
    attribute 'evaluate'`（实现者 s8c1 实跑正是崩在这一行）。
    """
    item = page.locator(".ws-plugin-item", has_text="录题工作台").first
    item.wait_for(state="visible", timeout=15000)
    item.click()
    page.wait_for_timeout(wait_ms)
    return item


def uniq(path: Path) -> Path:
    """只新增不覆盖：撞名就加 -1/-2 后缀。"""
    if not path.exists():
        return path
    n = 1
    while True:
        cand = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not cand.exists():
            return cand
        n += 1


def shot(obj, name: str, page=None) -> Path | None:
    folder = PANELS if name.startswith("panel") else SHOTS
    folder.mkdir(parents=True, exist_ok=True)
    path = uniq(folder / name)
    try:
        obj.screenshot(path=str(path))
        return path
    except Exception as exc:
        NOTES.setdefault("shot_errors", []).append(f"{name}: {type(exc).__name__}")
        if page is not None:
            try:
                page.screenshot(path=str(path))
                return path
            except Exception:
                return None
        return None


def dump(name: str, payload: object) -> Path:
    folder = PANELS if name.startswith("panel") else SHOTS
    folder.mkdir(parents=True, exist_ok=True)
    path = uniq(folder / name)
    path.write_text(toml_io.dumps(payload, default=str),
                    encoding="utf-8")
    return path


def rgb_at(path: Path, x: int, y: int) -> tuple[int, int, int]:
    w, h, ch, buf = decode_png(path)
    x = max(0, min(int(x), w - 1))
    y = max(0, min(int(y), h - 1))
    i = (y * w + x) * ch
    return (buf[i], buf[i + 1], buf[i + 2])


def edge_band(path: Path, box: list[int], depth: int = 4) -> list[tuple]:
    """盒子内缘 depth 像素那一圈（inset box-shadow 就画在这里），逐点取色。"""
    w, h, ch, buf = decode_png(path)  # 修③：原来解成 _ch 却在下面用 ch，RGBA 下 ch=4
    x0, y0, x1, y1 = (max(0, int(v)) for v in box)
    x1, y1 = min(w - 1, x1), min(h - 1, y1)
    pts: list[tuple] = []
    for d in range(depth):
        for x in range(x0 + d, x1 - d + 1):
            pts += [(x, y0 + d), (x, y1 - d)]
        for y in range(y0 + d + 1, y1 - d):
            pts += [(x0 + d, y), (x1 - d, y)]
    out = []
    for (x, y) in pts:
        i = (y * w + x) * ch
        out.append((x, y, (buf[i], buf[i + 1], buf[i + 2])))
    return out


def best_family(path: Path, box: list[int], kind: str, depth: int = 5) -> dict:
    """S6e 统一带（与 s6d_amber_chroma.py:29 同一条口径的族）：
    琥珀=色度带（r>g>b、r-b>=45、r∈[150,235]、g∈[130,215]，硬段 d<2、软段 2–24px）；
    红=合成色线 ±8（T 按局部底反解，a∈[0.16,0.80]，硬段 d<3、软段 3–37px；
    下限 0.16 用于排除米底压暗噪声 α≈0.11，s6ered2 实测），硬段另计「静态 .55 严带」
    （|c-(.55T+.45*bg_local)|inf<=8——**只在 reduced 档作判据**，layout_canvas.css:670）。
    背景参考＝命中点法向向内 40px（辉光 34/22px 之外），单帧只解码一次。
    旧两条带作废：橙饰 (187,106,29) 被 r>=150,g<=110 误收；tightDanger 精确源色±8 亮灯帧必然 0。"""
    target = AMBER if kind == "amber" else DANGER
    W, H, ch, buf = decode_png(path)

    def px(cx: int, cy: int) -> tuple[int, int, int]:
        cx = max(0, min(int(cx), W - 1))
        cy = max(0, min(int(cy), H - 1))
        o = (cy * W + cx) * ch
        return (buf[o], buf[o + 1], buf[o + 2])

    bx0, by0, bx1, by1 = (max(0, int(v)) for v in box[:4])
    bx1, by1 = min(W - 1, bx1), min(H - 1, by1)
    hard_max, scan = (3, 37) if kind == "red" else (2, 24)
    cells: list = []
    for d_ in range(scan):
        for cx in range(bx0 + d_, bx1 - d_ + 1):
            cells += [(cx, by0 + d_, d_), (cx, by1 - d_, d_)]
        for cy in range(by0 + d_ + 1, by1 - d_):
            cells += [(bx0 + d_, cy, d_), (bx1 - d_, cy, d_)]
    fam: list = []
    hard = glow = strict55 = hard_cells = 0
    bgsum = [0, 0, 0]
    bgk = 0
    for (x, y, d_) in cells:
        r, g, b = c = px(x, y)
        ds = (x - bx0, bx1 - x, y - by0, by1 - y)
        j = min(range(4), key=lambda i2: ds[i2])
        bgl = px(*[(bx0 + 40, y), (bx1 - 40, y), (x, by0 + 40), (x, by1 - 40)][j])
        bgsum = [bgsum[i2] + bgl[i2] for i2 in range(3)]
        bgk += 1
        if d_ < hard_max:
            hard_cells += 1
        if kind == "amber":
            hit = r > g > b and (r - b) >= 45 and 150 <= r <= 235 and 130 <= g <= 215
        else:
            den = sum((target[i2] - bgl[i2]) ** 2 for i2 in range(3))
            if den < 1e-6:
                hit = False
            else:
                a = sum((target[i2] - bgl[i2]) * (c[i2] - bgl[i2]) for i2 in range(3)) / den
                line = tuple(bgl[i2] + a * (target[i2] - bgl[i2]) for i2 in range(3))
                hit = max(abs(line[i2] - c[i2]) for i2 in range(3)) <= 8 and 0.16 <= a <= 0.80
            if d_ < hard_max and max(abs(c[i2] - (0.55 * target[i2] + 0.45 * bgl[i2]))
                                     for i2 in range(3)) <= 8:
                strict55 += 1
        if hit:
            fam.append((abs(r - target[0]) + abs(g - target[1]) + abs(b - target[2]), x, y, c))
            if d_ < hard_max:
                hard += 1
            else:
                glow += 1
    bgm = tuple(round(v / max(1, bgk), 1) for v in bgsum)
    band_formula = (
        "amber: r>g>b & r-b>=45 & r in[150,235] & g in[130,215]; bands d<2 / 2-24px"
        if kind == "amber" else
        f"danger: |c-(bg_local+a*(T-bg_local))|inf<=8, a in[0.16,0.80]; T={target}; "
        f"bg_local=inward_40px_normal, mean={bgm}; strict a=0.55±8 on d<3")
    base = {"hard_band": hard, "glow_band": glow, "hard_cells": hard_cells,
            "strict_055_band": strict55, "background": list(bgm),
            "background_ref": "inward_40px_normal", "band_formula": band_formula,
            "target": target}
    if not fam:
        return {"hits": 0, "best": None, **base}
    fam.sort(key=lambda t: t[0])
    d0, x, y, rgb0 = fam[0]
    return {"hits": len(fam), "best": {"file": path.name, "x": x, "y": y, "rgb": rgb0,
                                       "distance_to_target": d0}, **base}


def family_count(path: Path, kind: str, box: list[int] | None = None, depth: int = 6) -> int:
    boxes = [box] if box else [[0, 0, decode_png(path)[0] - 1, decode_png(path)[1] - 1]]
    return sum(best_family(path, b, kind, depth)["hits"] for b in boxes if b)


LIVE_TOPIC: dict = {"id": None}  # 夹具考向：造现场前从大纲树实取一个已存在节点（S6e 修）


def doc(stem: str, answer: str = "A", taxonomy: bool = True) -> dict:
    d = {"type": "single_choice", "stem": stem, "difficulty": "L2",
         "options": [{"key": "A", "content": "$5$"}, {"key": "B", "content": "$6$"},
                     {"key": "C", "content": "$11$"}, {"key": "D", "content": "$1$"}],
         "answer": {"kind": "choice", "choice_keys": [answer], "final": answer},
         "solution": "由韦达定理，两根之和为 $5$。", "tags": ["基础"],
         "source": {"paper_title": "S6d 画布探针卷", "question_no": "1", "year": 2024,
                    "exam_type": "一模"}}
    if taxonomy:
        if LIVE_TOPIC["id"]:
            d["taxonomy"] = {"topic": "S6e 大纲实节点", "topic_ids": [LIVE_TOPIC["id"]]}
        # 取不到实节点就不挂考向：approve 200 已在 s6damber3/census 实测
    return d


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("s6dbr%H%M%S")
    NOTES["tag"] = tag
    work = ROOT / ".system_generated" / "pool_canvas" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir = work / "data", work / "plugins"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    for pid in (EDITOR_ID, BANK_ID):
        shutil.copytree(ROOT / "plugins" / pid, plugins_dir / pid)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    NOTES["bypass_env_in_parent"] = env.pop("JZO_POOL_ADMIT_DISABLED", None)
    env.update(JZO_DATA_DIR=str(data_dir), JZO_PLUGINS_DIR=str(plugins_dir),
               JZO_LOCAL_TOKEN=TOKEN, JZO_RESTART_DISABLED="1")
    log_path = work / "server.log"
    handle = log_path.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen([str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn",
                             "app.main:app", "--host", "127.0.0.1", "--port", str(port),
                             "--log-level", "info", "--no-server-header"],
                            cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
    bank0 = 0
    try:
        wait_health(base, proc, log_path)
        # S6e 修夹具：考向改用大纲树里真实存在的节点（旧 t_s6d_canvas 不存在→approve 422）
        try:
            _, tt = GET(base + f"/api/bank/plugins/{BANK_ID}/topics")
            items = (tt.get("items") if isinstance(tt, dict) else tt) or []
            first = items[0] if items else {}
            tid = str((first or {}).get("id") or (first or {}).get("topic_id") or "") or None
            LIVE_TOPIC["id"] = tid
            NOTES["live_topic"] = {"via": f"GET /api/bank/plugins/{BANK_ID}/topics",
                                   "count": len(items), "picked": tid,
                                   "head": str(items[:1])[:180]}
        except Exception as exc:
            NOTES["live_topic_error"] = f"{type(exc).__name__}: {str(exc)[:240]}"
        if not LIVE_TOPIC["id"]:
            NOTES["live_topic_fallback"] = "取不到实节点，doc() 将不挂考向（s6damber3/census 实测 approve 200）"
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})

            def wire(bucket: str):
                page.on("console", lambda m: CONSOLE[bucket].append(m.text)
                        if m.type == "error" else None)
                page.on("pageerror", lambda e: PAGE_ERRORS.append(str(e)))
                page.on("response", lambda r: POOL_RESPONSES.append(
                    f"{r.status} {r.url} {str(r.body())[:160]}" if "/api/pending/pool" in r.url else None)
                    if "/api/pending/pool" in r.url else None)

            wire("boot")
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            item.wait_for(state="visible", timeout=15000)
            item.click()
            canvas = frame_with(page, "#edRoot")
            panel = frame_with(page, "#epRoot")
            boot_shot = shot(page, f"{tag}-01-boot.png", page=page)

            def c1():
                ok = canvas is not None and panel is not None
                check("C1 开机链：真人点进录题工作台，画布与辅助栏都在",
                      ok, {"canvas": canvas is not None, "panel": panel is not None,
                           "shot": boot_shot.name if boot_shot else None,
                           "console_errors": list(CONSOLE["boot"]), "page_errors": list(PAGE_ERRORS)})
            guarded("C1 开机链", c1)

            def c5_empty():
                sec = panel.evaluate("""() => {const s=document.getElementById('epPoolSec');
                    const r=s?s.getBoundingClientRect():null; const cs=s?getComputedStyle(s):null;
                    return {present: Boolean(s), hidden: s?s.hidden:null,
                            display: cs?cs.display:null, rect: r?[r.x,r.y,r.width,r.height]:null,
                            text: s?(s.innerText||'').trim():null};}""")
                check("C5 空池留白：整段收起、零占位文案（此时池里必然还没东西）",
                      sec.get("present") and (sec.get("hidden") or sec.get("display") == "none")
                      and not re.search(r"暂无|没有重题|空池", str(sec.get("text") or "")),
                      {"state": sec, "pool_http_total": GET(base + "/api/pending/pool")[1].get("total")})
            guarded("C5 空池留白", c5_empty)

            # ---------- 造现场（HTTP，插件不开口）：主库 3 道原题 → 重题批 → 审核批 ----------
            s_orig, b_orig = POST(base + "/api/pending/batches",
                                  {"questions": [doc(S1), doc(S2), doc(S3)]})
            orig_batch = str(b_orig.get("batch_id") or "")
            ids = [it.get("id") for it in (GET(base + f"/api/pending/batches/{orig_batch}/questions")[1]
                                           .get("items") or [])]
            for pid in ids:
                POST(base + f"/api/pending/items/{pid}/approve", {})
            s_dup, b_dup = POST(base + "/api/pending/batches", {"questions": [
                doc(S1),                                            # 逐字同 → certain
                doc(S2.replace("$\\{a_n\\}$", "$\\{ a_n \\}$")),   # 写法差 → very_similar 期望
                doc(D3),                                            # 数字差 → fairly/possible 期望
                doc("S6d 独题：已知 $y=\\sin x$ 的周期是（　　）。选项 A $2\\pi$、B $\\pi$、C $\\pi/2$、D $4\\pi$，答案 A。"),
            ]})
            dup_batch = str(b_dup.get("batch_id") or "")
            deadline = time.time() + 90
            pool_rows: list[dict] = []
            while time.time() < deadline:
                pool_rows = (GET(base + "/api/pending/pool")[1].get("items") or [])
                if len(pool_rows) >= 2:
                    break
                time.sleep(0.5)
            s_rev, b_rev = POST(base + "/api/pending/batches",
                                {"questions": [doc(S1.replace("甲", "审核批干净题")), doc(R2_STEM, taxonomy=False)]})
            review_batch = str(b_rev.get("batch_id") or "")
            time.sleep(3.0)   # 两个批次的后台初查各跑一会儿，看抽走有没有把审核批也带走
            for tier in ("strict", "standard", "loose"):
                body = GET(base + f"/api/pending/pool?tier={tier}")[1]
                TIERS[tier] = {"total": body.get("total"),
                               "rows": [{"pool_id": r.get("pool_id"), "level": r.get("level"),
                                         "label": r.get("label"), "percent": r.get("percent"),
                                         "main_id": r.get("main_id")} for r in body.get("items") or []]}
            NOTES["seed"] = {"orig_batch": orig_batch, "dup_batch": dup_batch,
                             "review_batch": review_batch, "post": [s_orig, s_dup, s_rev],
                             "dup_card": next((r for r in GET(base + "/api/pending/batches")[1]
                                              .get("batches") or []
                                              if str(r.get("batch_id")) == dup_batch), {}),
                             "review_card": next((r for r in GET(base + "/api/pending/batches")[1]
                                                  .get("batches") or []
                                                  if str(r.get("batch_id")) == review_batch), {}),
                             "pool_after_seed": len(pool_rows), "bank_total_http": None}
            dump(f"{tag}-00-seed-and-tiers.toml", {"note": NOTES["seed"], "tiers": TIERS})
            check("造现场：主库 3 道原题 + 重题批自动抽走后进池 ≥2 条",
                  s_orig == 200 and s_dup == 200 and len(pool_rows) >= 2,
                  {"pool_rows": len(pool_rows), "dup_card": NOTES["seed"]["dup_card"].get("pending_count"),
                   "levels": [r.get("level") for r in pool_rows]})

            # ---------- 缺陷 A 的取数链：面板只在 wire() 里取一次， reload 才算真人重开 ----------
            panel_state_before = panel.evaluate("""() => ({
                rows: (document.querySelectorAll('#epPoolList .ep-pool-row')||[]).length,
                html: (document.getElementById('epPoolList')||{}).innerHTML || '',
                secHidden: (document.getElementById('epPoolSec')||{}).hidden,
                count: (document.getElementById('epPoolCount')||{}).textContent})""")
            NOTES["panel_before_reload"] = panel_state_before
            page.reload(wait_until="networkidle")
            reopen_editor(page)
            canvas = frame_with(page, "#edRoot")
            panel = frame_with(page, "#epRoot")
            panel_state_after = panel.evaluate("""() => ({
                rows: (document.querySelectorAll('#epPoolList .ep-pool-row')||[]).length,
                secHidden: (document.getElementById('epPoolSec')||{}).hidden,
                count: (document.getElementById('epPoolCount')||{}).textContent,
                poolReqs: (window.__jzoSeenPoolRequests||[]).length})""")
            NOTES["panel_after_reload"] = panel_state_after
            shot(panel.locator(".ep-root"), f"panel{tag}-05-pool-list-after-reload.png", page=page)
            check("C5b 池列表取数链：重开辅助栏后条目真的渲染出来（reload 前后对比）",
                  (panel_state_after or {}).get("rows", 0) >= 2,
                  {"rows_before_reload": panel_state_before.get("rows"),
                   "rows_after_reload": panel_state_after.get("rows"),
                   "count_text_after": panel_state_after.get("count"),
                   "http_pool_total": GET(base + "/api/pending/pool")[1].get("total"),
                   "panel_pool_responses": list(POOL_RESPONSES)[-3:]})

            # ---------- 进审核模式（真人点批次卡） ----------
            def enter_review():
                card = canvas.get_by_label(re.compile("点开审核")).first
                card.wait_for(state="visible", timeout=15000)
                card.click()
                canvas.wait_for_selector(".ed-q-block", timeout=20000)
            guarded("进审核模式", enter_review)
            mode = canvas.evaluate("""() => {const r=document.querySelector('.ed-root');
                return {mode: r?r.getAttribute('data-mode'):null,
                        dup: r?r.getAttribute('data-dup'):null,
                        blocks: (document.querySelectorAll('.ed-q-block')||[]).length};}""")

            def c2_red():
                root_box = canvas.evaluate("""() => {const r=document.querySelector('.ed-root')
                    .getBoundingClientRect(); return [r.x,r.y,r.width,r.height];}""")
                native = shot(canvas.locator(".ed-root"), f"{tag}-02-review-no-red.png", page=page)
                cnt_native = family_count(native, "red",
                                          [0, 0, int(root_box[2]) - 1, int(root_box[3]) - 1]) if native else None
                canvas.evaluate("""() => {document.querySelector('.ed-root').setAttribute('data-dup','on');}""")
                forced = shot(canvas.locator(".ed-root"), f"{tag}-02-review-forced-dup.png", page=page)
                cnt_forced = family_count(forced, "red",
                                          [0, 0, int(root_box[2]) - 1, int(root_box[3]) - 1]) if forced else None
                canvas.evaluate("""() => {document.querySelector('.ed-root').removeAttribute('data-dup');}""")
                check("C2 审核画布无红灯：原生 0 枚红族像素，人造 data-dup=on 也扫不到",
                      mode.get("mode") == "review" and cnt_native == 0 and cnt_forced == 0,
                      {"mode": mode, "native_red_hits": cnt_native, "forced_red_hits": cnt_forced,
                       "shots": [native.name if native else None, forced.name if forced else None],
                       "red_family": "r>=150 且 g<=110 且 b<=120 且 r-max(g,b)>=60（对准 --danger #d33）"})
            guarded("C2 审核画布无红灯", c2_red)

            def c6_amber():
                state = canvas.evaluate("""() => {const bs=[...document.querySelectorAll('.ed-q-block')];
                    return bs.map((b,i)=>{const r=b.getBoundingClientRect(),
                        rr=document.querySelector('.ed-root').getBoundingClientRect();
                        return {i, amber: b.getAttribute('data-amber'), reasons: b.getAttribute('data-amber-reasons'),
                                box: [r.left-rr.left, r.top-rr.top, r.right-rr.left, r.bottom-rr.top]};});}""")
                panel_lit = panel.evaluate("""() => {const p=document.querySelector('.ep-root');
                    return {amber: p?p.getAttribute('data-amber'):null,
                            reasons: p?p.getAttribute('data-amber-reasons'):null};}""")
            # 呼吸灯要多帧同坐标采样
                frames = []
                for k in range(4):
                    p = shot(canvas.locator(".ed-root"), f"{tag}-06-amber-frame-{k}.png", page=page)
                    if p:
                        lit = [b for b in state if b.get("amber") == "on"]
                        off = [b for b in state if b.get("amber") != "on"]
                        frames.append({"file": p.name,
                                       "lit": best_family(p, lit[0]["box"], "amber") if lit else None,
                                       "off_ref": best_family(p, off[0]["box"], "amber") if off else None})
                    time.sleep(0.7)
                pp = shot(panel.locator(".ep-root"), f"panel{tag}-06-panel-amber.png", page=page)
                panel_box = panel.evaluate("""() => {const r=document.querySelector('.ep-root')
                    .getBoundingClientRect(); return [0,0,Math.round(r.width)-1,Math.round(r.height)-1];}""")
                panel_sample = best_family(pp, panel_box, "amber") if pp else None
                lits = [f["lit"] for f in frames if f["lit"] and f["lit"]["hits"]]
                check("C6 琥珀灯：未清题亮、干净题不亮，边缘像素逐帧取色并反解合成透明度",
                      any(b.get("amber") == "on" for b in state)
                      and panel_lit.get("amber") == "on" and bool(lits),
                      {"blocks": state, "panel": panel_lit, "frames": frames,
                       "panel_edge": panel_sample, "shots": [f["file"] for f in frames] + [pp.name if pp else None]})
            guarded("C6 琥珀灯像素", c6_amber)

            def c3_pool_canvas():
                # 修④：池区是「默认收起、点了才展开」（16:47 新加的行为口径），
                # 不点 #epPoolEntry 就轮询 trigger 必然 33 次全 hidden。
                try:
                    entry = panel.locator("#epPoolEntry").first
                    if entry.count() and (entry.get_attribute("aria-expanded") or "false") == "false":
                        entry.click(timeout=5000)
                        panel.wait_for_timeout(900)
                except Exception as exc:
                    NOTES["c3_entry_error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
                first = panel.locator("#epPoolList .ep-pool-row .ep-pool-trigger").first
                first.wait_for(state="visible", timeout=15000)
                first.click()
                panel.wait_for_timeout(2500)
                st = canvas.evaluate("""() => {const r=document.querySelector('.ed-root');
                    const pool=document.getElementById('edPool');
                    const canvasEl=document.getElementById('edPoolCanvas');
                    const rootRect=r.getBoundingClientRect();
                    const cr=canvasEl?canvasEl.getBoundingClientRect():null;
                    return {mode: r.getAttribute('data-mode'), dup: r.getAttribute('data-dup'),
                            poolPresent: Boolean(pool), poolVisible: pool? !!(pool.offsetWidth||pool.offsetHeight||getComputedStyle(pool).display!=='none'):null,
                            buttonsInPool: pool? pool.querySelectorAll('button').length : null,
                            buttonsInCanvas: canvasEl? canvasEl.querySelectorAll('button').length : null,
                            sourceBar: [...document.querySelectorAll('.ed-src, #edSource, .ed-source, [data-slot=source]')]
                                      .filter(n=>getComputedStyle(n).display!=='none').map(n=>n.id||n.className),
                            note: (document.getElementById('edPoolNote')||{}).textContent,
                            canvasBox: cr?[cr.left-rootRect.left,cr.top-rootRect.top,cr.right-rootRect.left,cr.bottom-rootRect.top]:null};}""")
                p = shot(canvas.locator(".ed-root"), f"{tag}-03-pool-canvas.png", page=page)
                red = best_family(p, [0, 0, 1439, 899], "red", depth=8) if p else None
                dump(f"{tag}-03-pool-canvas-dom.toml", {"state": st, "red": red})
                check("C3 池画布：模式=pool、这一屏一颗按钮都没有、没有源码栏",
                      st.get("mode") == "pool" and st.get("buttonsInPool") == 0
                      and not st.get("sourceBar"),
                      {"state": st, "shot": p.name if p else None})
                check("C2 对照：同一台扫描器在池模式下确实扫得到红（证明不是瞎子）",
                      st.get("dup") == "on" and red and red.get("hits", 0) > 0,
                      {"data_dup": st.get("dup"), "red": red, "shot": p.name if p else None})
            guarded("C3 池画布与红灯对照", c3_pool_canvas)

            def c9_esc():
                before = canvas.evaluate("""() => document.querySelector('.ed-root').getAttribute('data-mode')""")
                del_btn = panel.locator("#epPoolDelete")
                del_btn.wait_for(state="visible", timeout=10000)
                del_btn.click()
                panel.wait_for_timeout(800)
                modal = panel.evaluate("""() => {const m=document.getElementById('epPoolDelModal');
                    const cs=m?getComputedStyle(m):null;
                    return {present: Boolean(m), hidden: m?m.hidden:null, display: cs?cs.display:null,
                            text: m?(m.innerText||'').trim().slice(0,120):null};}""")
                open_shot = shot(panel.locator(".ep-root"), f"panel{tag}-09-del-modal-open.png", page=page)
                page.keyboard.press("Escape")
                panel.wait_for_timeout(900)
                after = panel.evaluate("""() => {const m=document.getElementById('epPoolDelModal');
                    const cs=m?getComputedStyle(m):null;
                    return {hidden: m?m.hidden:null, display: cs?cs.display:null,
                            focus: document.activeElement ? (document.activeElement.id||document.activeElement.tagName) : null};}""")
                after_shot = shot(panel.locator(".ep-root"), f"panel{tag}-09-after-esc.png", page=page)
                mode_after = canvas.evaluate("""() => document.querySelector('.ed-root').getAttribute('data-mode')""")
                check("C9 Esc：删除二次确认关掉后两帧都不残留（真人按键，不是 dispatchEvent）",
                      modal.get("present") and modal.get("display") != "none"
                      and (after.get("hidden") is True or after.get("display") == "none"),
                      {"modal_open": modal, "after_esc": after, "canvas_mode": [before, mode_after],
                       "shots": [open_shot.name if open_shot else None, after_shot.name if after_shot else None]})
            guarded("C9 Esc", c9_esc)

            def c4_tiers():
                nonlocal canvas, panel
                observed = []
                for tier in ("strict", "standard", "loose"):
                    POOL_RESPONSES.clear()
                    btn = panel.locator(f"#epPoolTiers [data-tier='{tier}']")
                    btn.wait_for(state="visible", timeout=10000)
                    btn.click()
                    panel.wait_for_timeout(1500)
                    rows = panel.evaluate("""() => (document.querySelectorAll('#epPoolList .ep-pool-row')||[]).length""")
                    observed.append({"tier": tier, "rows_in_panel": rows,
                                     "http_total": TIERS[tier]["total"],
                                     "http_levels": [r["level"] for r in TIERS[tier]["rows"]],
                                     "panel_requests": list(POOL_RESPONSES)})
                active = panel.evaluate("""() => [...document.querySelectorAll('#epPoolTiers [data-tier]')]
                    .map(n => [n.getAttribute('data-tier'), n.classList.contains('is-on'), n.textContent.trim()])""")
                page.reload(wait_until="networkidle")
                reopen_editor(page)
                panel2 = frame_with(page, "#epRoot")
                panel = panel2
                after_reload = panel2.evaluate("""() => [...document.querySelectorAll('#epPoolTiers [data-tier]')]
                    .map(n => [n.getAttribute('data-tier'), n.classList.contains('is-on')])""")
                ls = panel2.evaluate("""() => {try { return {ok:false, note:'sandboxed'}; }
                    catch (e) { return {ok:false, note:String(e.name)}; } }""")
                shot(panel2.locator("#epPoolTiers"), f"panel{tag}-04-tier-after-reload.png", page=page)
                check("C4 三档：默认宽、切档即时重取、刷新后回落宽（不落盘）",
                      [o["tier"] for o in observed] == ["strict", "standard", "loose"]
                      and any(x[0] == "loose" and x[1] for x in (after_reload or [])),
                      {"observed": observed, "active_at_loose": active, "after_reload": after_reload,
                       "localStorage": ls})
                canvas = frame_with(page, "#edRoot")
                NOTES["reframe_after_c4"] = {"canvas": canvas is not None}
            guarded("C4 三档", c4_tiers)

            def c7_approve_all():
                dock = panel.evaluate("""() => {const d=document.getElementById('epDock');
                    if (!d) return {present:false};
                    const r=d.getBoundingClientRect(), cs=getComputedStyle(d);
                    const p=d.parentElement, pr=p?p.getBoundingClientRect():null, pcs=p?getComputedStyle(p):null;
                    const b=document.getElementById('epApproveAll'), br=b?b.getBoundingClientRect():null;
                    return {present:true, rect:[r.x,r.y,r.width,r.height], display:cs.display,
                            visibility:cs.visibility, overflow:cs.overflow, height:cs.height,
                            flex:cs.flex, parent:{tag:p?p.tagName:null,cls:p?p.className:null,
                              rect: pr?[pr.x,pr.y,pr.width,pr.height]:null, display: pcs?pcs.display:null,
                              overflow: pcs?pcs.overflow:null, flexDirection: pcs?pcs.flexDirection:null,
                              childCount: p?p.childElementCount:null},
                            btnRect: br?[br.x,br.y,br.width,br.height]:null,
                            btnDisplay: b?getComputedStyle(b).display:null,
                            btnHidden: b?b.hidden:null, scrollTop: document.scrollingElement?document.scrollingElement.scrollTop:null,
                            rootScroll:{h:document.documentElement.scrollHeight, ch:document.documentElement.clientHeight}};}""")
                NOTES["c7_dock_dom"] = dock
                dump(f"panel{tag}-07-dock-dom.toml", dock)
                total_before = GET(base + "/api/bank/questions?page=1&page_size=1")[1]
                bank_before = total_before.get("total")
                try:
                    panel.locator("#epApproveAll").click(timeout=8000)
                    clicked = True
                except Exception as exc:
                    clicked = False
                    NOTES["c7_click_error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                panel.wait_for_clicked = None
                page.wait_for_timeout(4000)
                msg = panel.evaluate("""() => {const m=document.getElementById('epMessage');
                    return m?(m.innerText||'').trim():null;}""")
                bank_after = GET(base + "/api/bank/questions?page=1&page_size=1")[1].get("total")
                p = shot(page, f"{tag}-07-approve-all.png", page=page)
                check("C7 判据 43：亮着琥珀灯点【全部入库】→ 一题都不存，并把位置给最上面那道未清题",
                      clicked and bank_after == bank_before,
                      {"clicked": clicked, "bank_before": bank_before, "bank_after": bank_after,
                       "panel_message": msg, "dock": dock, "click_error": NOTES.get("c7_click_error"),
                       "shot": p.name if p else None})
            guarded("C7 全部入库被灯拦住", c7_approve_all)

            def c8_clean():
                st = panel.evaluate("""() => {const single=document.getElementById('epAiClean');
                    const nodes=[...document.querySelectorAll('#epRoot button')];
                    return {singlePresent: Boolean(single), singleText: single?single.textContent.trim():null,
                            cleanButtons: nodes.filter(n=>/清洗|LaTeX/i.test(n.textContent||''))
                                     .map(n=>({id:n.id, text:n.textContent.trim(), disabled:n.disabled})),
                            preview: (document.getElementById('epAiPreview')||{}).textContent};}""")
                vis = panel.evaluate("""() => {const n=document.getElementById('epAiClean');
                    if(!n) return null; const cs=getComputedStyle(n); const r=n.getBoundingClientRect();
                    const anc=[]; let p=n;
                    while(p && anc.length<8){const c=getComputedStyle(p);
                        anc.push({id:p.id||String(p.className).slice(0,30), hidden:!!p.hidden,
                                  display:c.display, visibility:c.visibility}); p=p.parentElement;}
                    return {rect:[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)],
                            cs:{display:cs.display,visibility:cs.visibility,pointerEvents:cs.pointerEvents},
                            anc:anc};}""")
                NOTES["c8_visibility"] = vis
                clicked = []
                for bid in ("epAiClean",):
                    try:
                        panel.locator(f"#{bid}").click(timeout=5000)
                        clicked.append(bid)
                        page.wait_for_timeout(2500)
                    except Exception as exc:
                        NOTES[f"c8_{bid}_error"] = f"{type(exc).__name__}: {str(exc)[:420]}"
                after = panel.evaluate("""() => ({
                    message: (document.getElementById('epMessage')||{}).textContent,
                    preview: (document.getElementById('epAiPreview')||{}).textContent,
                    applyEnabled: !(document.getElementById('epAiApply')||{}).disabled})""")
                dump(f"panel{tag}-08-clean-entry.toml", {"state": st, "clicked": clicked, "after": after})
                shot(panel.locator(".ep-root"), f"panel{tag}-08-clean.png", page=page)
                # 修C8：原 URL /api/text/clean-latex 全仓不存在（404 定论=探针写错）；
                # 真实路由 = agents.py:19 prefix("/api/agent") + :399 post("/clean_latex")
                base_out = POST(base + "/api/agent/clean_latex", {"text": "$\\\\frac{1}{2}$", "mode": "exam_source"})
                check("C8 清洗双入口：面板里那颗清洗钮真能点，底座那把尺子在 HTTP 侧同一份",
                      st.get("singlePresent") is True and bool(clicked),
                      {"entry": st, "clicked": clicked, "after": after,
                       "base_route_status": base_out[0], "base_route_body": str(base_out[1])[:200]})
            guarded("C8 清洗双入口", c8_clean)

            # ---------- reduced-motion 单开一次（不开假时钟） ----------
            def reduced():
                ctx = browser.new_context(viewport={"width": 1440, "height": 900},
                                          reduced_motion="reduce")
                p2 = ctx.new_page()
                p2.on("pageerror", lambda e: PAGE_ERRORS.append("reduced:" + str(e)))
                p2.goto(base + "/workspace", wait_until="networkidle")
                p2.locator(".ws-plugin-item", has_text="录题工作台").first.click()
                c2 = frame_with(p2, "#edRoot")
                card = c2.get_by_label(re.compile("点开审核")).first
                card.wait_for(state="visible", timeout=15000)
                card.click()
                c2.wait_for_selector(".ed-q-block", timeout=20000)
                st = c2.evaluate("""() => {const b=[...document.querySelectorAll('.ed-q-block')]
                        .find(x=>x.getAttribute('data-amber')==='on');
                    const r=document.querySelector('.ed-root').getBoundingClientRect();
                    if(!b) return null; const q=b.getBoundingClientRect();
                    return {box:[q.left-r.left,q.top-r.top,q.right-r.left,q.bottom-r.top],
                            mq: matchMedia('(prefers-reduced-motion: reduce)').matches};}""")
                fa = shot(c2.locator(".ed-root"), f"{tag}-06-reduced-a.png", page=p2)
                p2.wait_for_timeout(1200)
                fb = shot(c2.locator(".ed-root"), f"{tag}-06-reduced-b.png", page=p2)
                identical = bool(fa) and bool(fb) and fa.read_bytes() == fb.read_bytes()
                samp = best_family(fa, st["box"], "amber") if (fa and st) else None
                check("C6b reduced-motion：真人级「减少动态效果」下灯仍在、两帧像素全等（静态描边）",
                      st and st.get("mq") is True and identical and samp.get("hits", 0) > 0,
                      {"media": st, "two_frames_identical": identical, "pixel": samp,
                       "shots": [fa.name if fa else None, fb.name if fb else None]})
                ctx.close()
            guarded("C6b reduced-motion", reduced)

            check("C1b 全程控制台与页面异常：pageerror 必须为零（悬挂引用那类必须现形）",
                  not PAGE_ERRORS,
                  {"page_errors": PAGE_ERRORS, "console_errors": {k: v for k, v in CONSOLE.items() if v},
                   "counts": {k: len(v) for k, v in CONSOLE.items()}})
            browser.close()
    except Exception as exc:
        import traceback
        check("S6d-browser 探针整体执行", False,
              {"exception": f"{type(exc).__name__}: {exc}",
               "trace": traceback.format_exc().splitlines()[-5:]})
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()
        handle.close()
        EVID.mkdir(parents=True, exist_ok=True)
        out = uniq(EVID / f"{tag}-browser-result.toml")
        out.write_text(toml_io.dumps({"tag": tag, "base": base, "checks": CHECKS, "note": NOTES,
                                   "tiers": TIERS, "page_errors": PAGE_ERRORS,
                                   "console_errors": CONSOLE,
                                   "pool_responses": POOL_RESPONSES[-20:]}, default=str), encoding="utf-8")
        print(f"证据：{out}", flush=True)
    ok = sum(1 for c in CHECKS if c["ok"])
    print("=" * 60)
    print(f"九条路径共 {len(CHECKS)} 条检查，通过 {ok}，失败 {len(CHECKS) - ok}，tag={tag}")
    return 0 if ok == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())

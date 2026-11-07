# -*- coding: utf-8 -*-
"""查重三栏变身 + 裁判台 + 静默流转 + 渲染冻结的真人路径探针（军令·查重三栏）。

隔离：随机端口 + 独立 JZO_DATA_DIR/JZO_PLUGINS_DIR + 一次性令牌 +
JZO_RESTART_DISABLED=1；不碰仓库 data/。点按一律走 Playwright 真实鼠标。

验四件事：
  1. 点【查重对比】→ 画布 data-mode=compare，原图栏收起，第三栏（原题渲染）滑出；
  2. 辅助栏 data-judge=on，审核表单整段让位，裁判台只列差异；
  3. 决断（不重复）后自动跳下一道，对比不退出；
  4. 跳题前后 #edRenderBody / #edCmpIncoming 是同一只节点，换题只换内容不重建。

证据落点：``.qoder/records/biz/2026-11/20261106_dup-compare-evidence/``

用法：``.venv\\Scripts\\python.exe tools\\dup_compare_probe.py <tag>``
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
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / ".qoder" / "records" / "biz" / "2026-11" / "20261106_dup-compare-evidence"
SHOTS = EVID / "shots"
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
TOKEN = "dup-compare-probe-token"
CHECKS: list[dict] = []
NOTES: dict[str, object] = {}
PAGE_ERRORS: list[str] = []
CONSOLE_ERRORS: list[str] = []


def check(name: str, ok: object, detail: object = None) -> None:
    CHECKS.append({"name": name, "ok": bool(ok), "detail": detail})
    print(("PASS " if ok else "FAIL ") + name + " | "
          + wire.dumps(detail, ensure_ascii=False, default=str)[:900], flush=True)


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
                                 headers={"Content-Type": "application/json",
                                          "X-JZO-Token": TOKEN})
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
  return {hidden: n.hidden === true, display: cs.display,
          visibility: cs.visibility, rect: [b.x, b.y, b.width, b.height],
          nonZero: b.width > 0 && b.height > 0};
}"""


def frame_with(page, sel: str, timeout: float = 30):
    """按「这一帧真的在渲染它」认帧：宽高非零 + 未 hidden（两帧共用同一份 index.html）。"""
    end = time.time() + timeout
    while time.time() < end:
        for fr in page.frames:
            try:
                st = fr.evaluate(_FRAME_PROBE, sel)
            except Exception:
                continue
            if st and st.get("hidden") is False and st.get("nonZero") \
                    and st.get("display") != "none" and st.get("visibility") != "hidden":
                return fr
        time.sleep(0.2)
    return None


def uniq(path: Path) -> Path:
    if not path.exists():
        return path
    n = 1
    while True:
        cand = path.with_name(f"{path.stem}-{n}{path.suffix}")
        if not cand.exists():
            return cand
        n += 1


def shot(obj, name: str, page=None) -> Path | None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = uniq(SHOTS / name)
    try:
        obj.screenshot(path=str(path))
        return path
    except Exception:
        if page is not None:
            try:
                page.screenshot(path=str(path))
                return path
            except Exception:
                pass
        return None


def dump(name: str, payload: object) -> Path:
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = uniq(SHOTS / name)
    path.write_text(toml_io.dumps(payload, default=str),
                    encoding="utf-8")
    return path


def bank_find(base: str, marker: str) -> dict | None:
    """按题干里的探针标记找回刚入库的题；回 None 表示没写进去。"""
    url = (base + f"/api/bank/plugins/{BANK_ID}/questions?q="
           + urllib.parse.quote(marker) + "&page_size=100")
    _, data = GET(url)
    for item in data.get("items") or []:
        if marker in str(item.get("stem") or ""):
            return item
    return None


_EDIT_SOURCE = r"""([stemMarker, solutionMarker]) => {
  const ta = document.getElementById('edCmpSource');
  if (!ta) return null;
  ta.value = ta.value
    .replace('\\begin{question}\n', '\\begin{question}\n' + stemMarker + ' ')
    .replace('\\end{solution}', solutionMarker + '\n\\end{solution}');
  ta.dispatchEvent(new Event('input', {bubbles: true}));
  return ta.value;
}"""


def doc(stem: str, tags: list[str], paper: str, no: str, topic_id: str | None = None) -> dict:
    entry = {
        "type": "single_choice", "stem": stem, "difficulty": "L2",
        "options": [{"key": "A", "content": "$5$"}, {"key": "B", "content": "$6$"},
                    {"key": "C", "content": "$11$"}, {"key": "D", "content": "$1$"}],
        "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
        "solution": "由韦达定理，两根之和为 $5$。",
        "tags": tags,
        "source": {"paper_title": paper, "question_no": no, "year": 2025,
                   "exam_type": "一模"},
    }
    if topic_id:
        entry["taxonomy"] = {"topic": "查重三栏实节点", "topic_ids": [topic_id]}
    return entry


S1 = "查重三栏甲：已知 $x^2-5x+6=0$，求它的两个根之和（　　）。选项 A $5$、B $6$、C $11$、D $1$，答案 A。"
S2 = "查重三栏乙：数列 $\\{a_n\\}$ 满足 $a_n=2n-1$，求前 3 项的和（　　）。选项 A $9$、B $6$、C $3$、D $12$，答案 A。"
D1 = "查重三栏甲近形：已知 $x^2-5x+6=0$，求它的两个根之和（　　）。选项 A $5$、B $6$、C $11$、D $1$，答案 A。"
D2 = "查重三栏乙近形：数列 $\\{a_n\\}$ 满足 $a_n=2n-1$，求前 3 项的和（　　）。选项 A $9$、B $6$、C $3$、D $12$，答案 A。"


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("dup%H%M%S")
    NOTES["tag"] = tag
    work = ROOT / ".system_generated" / "dup_compare" / tag
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
    env.pop("JZO_POOL_ADMIT_DISABLED", None)
    env.update(JZO_DATA_DIR=str(data_dir), JZO_PLUGINS_DIR=str(plugins_dir),
               JZO_LOCAL_TOKEN=TOKEN, JZO_RESTART_DISABLED="1")
    log_path = work / "server.log"
    handle = log_path.open("w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen([str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn",
                             "app.main:app", "--host", "127.0.0.1", "--port", str(port),
                             "--log-level", "info", "--no-server-header"],
                            cwd=str(ROOT), env=env, stdout=handle,
                            stderr=subprocess.STDOUT, text=True)
    try:
        wait_health(base, proc, log_path)
        # ---- 造现场：先主库两道原题，再一批近形题自动进重题池 ----
        try:
            _, topics = GET(base + f"/api/bank/plugins/{BANK_ID}/topics")
            items = (topics.get("items") if isinstance(topics, dict) else topics) or []
            topic_id = str((items[0] or {}).get("id") or "") or None if items else None
        except Exception:
            topic_id = None
        NOTES["topic_id"] = topic_id
        _, b_orig = POST(base + "/api/pending/batches",
                         {"questions": [doc(S1, ["基础"], "甲卷", "1", topic_id),
                                        doc(S2, ["基础"], "乙卷", "2", topic_id)]})
        orig_batch = str(b_orig.get("batch_id") or "")
        ids = [it.get("id") for it in (GET(base + f"/api/pending/batches/{orig_batch}/questions")[1]
                                       .get("items") or [])]
        for pid in ids:
            POST(base + f"/api/pending/items/{pid}/approve", {})
        _, b_dup = POST(base + "/api/pending/batches",
                        {"questions": [doc(D1, ["函数", "基础"], "甲卷", "1", topic_id),
                                       doc(D2, ["数列", "基础"], "乙卷", "2", topic_id)]})
        dup_batch = str(b_dup.get("batch_id") or "")
        rows: list[dict] = []
        deadline = time.time() + 90
        while time.time() < deadline:
            rows = (GET(base + "/api/pending/pool")[1].get("items") or [])
            if len(rows) >= 2:
                break
            time.sleep(0.5)
        NOTES["seed"] = {"orig_batch": orig_batch, "dup_batch": dup_batch,
                         "bank_questions": GET(base + "/api/bank/questions?page=1&page_size=1")[1].get("total"),
                         "pool_rows": [{"pool_id": r.get("pool_id"), "level": r.get("level")}
                                       for r in rows]}
        dump(f"{tag}-00-seed.toml", NOTES["seed"])
        check("造现场：主库 2 道原题，重题批自动抽走 ≥2 条进池",
              len(ids) == 2 and len(rows) >= 2, NOTES["seed"])

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: CONSOLE_ERRORS.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: PAGE_ERRORS.append(str(e)))
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            item.wait_for(state="visible", timeout=15000)
            item.click()
            page.wait_for_timeout(3500)
            canvas = frame_with(page, "#edRoot")
            panel = frame_with(page, "#epRoot")
            for fr in (canvas, panel):
                try:
                    fr.evaluate("""() => {
                        window.__dupSeen=[];
                        window.__activateSeen=0;
                        window.addEventListener('message', e => {
                            const d=e.data||{};
                            if (d.event === 'editor.dup_compare') {
                                const raw=(d.payload&&d.payload.raw)||d.payload||{};
                                window.__dupSeen.push({kind:d.kind, phase:raw.phase, from:raw.from});
                            }
                            if (d.kind === 'request' && d.method === 'plugin.activate') {
                                window.__activateSeen += 1;
                            }
                        });
                    }""")
                except Exception:
                    pass
            page.evaluate("""() => {
                window.__dupSeen=[];
                window.addEventListener('message', e => {
                    const d=e.data||{};
                    if (d.event === 'editor.dup_compare') {
                        const raw=(d.payload&&d.payload.raw)||d.payload||{};
                        window.__dupSeen.push({kind:d.kind, phase:raw.phase, from:raw.from});
                    }
                });
            }""")
            check("开机：画布帧与辅助栏帧都活着", canvas is not None and panel is not None,
                  {"canvas": canvas is not None, "panel": panel is not None,
                   "page_errors": PAGE_ERRORS[:5]})

            def open_pool():
                sec = panel.locator("#epPoolSec").first
                if sec.is_visible():
                    return
                entry = panel.locator("#epPoolEntry").first
                if entry.is_visible():
                    entry.click()
                sec.wait_for(state="visible", timeout=10000)
                panel.wait_for_timeout(800)

            def c_enter_compare():
                open_pool()
                btn = panel.locator("#epPoolCompare")
                btn.wait_for(state="visible", timeout=10000)
                visible = btn.is_visible()
                enabled = btn.is_enabled()
                btn.click()
                mode_seq = []
                for _ in range(24):
                    mode_seq.append(canvas.evaluate("""() => [
                        document.querySelector('.ed-root').getAttribute('data-mode'),
                        document.getElementById('edCols').getAttribute('data-compare')]"""))
                    panel.wait_for_timeout(100)
                canvas.wait_for_timeout(400)
                state = canvas.evaluate("""() => {
                  const cols=document.getElementById('edCols');
                  const img=document.getElementById('edPaneImage');
                  const src=document.getElementById('edPaneSource');
                  const org=document.getElementById('edPaneOriginal');
                  const ren=document.getElementById('edPaneRender');
                  const box=n=>{const r=n.getBoundingClientRect();return [r.x,r.y,r.width,r.height];};
                  return {mode: document.querySelector('.ed-root').getAttribute('data-mode'),
                          compare: cols?cols.getAttribute('data-compare'):null,
                          imageHidden: img?img.hidden:null, imageBox: img?box(img):null,
                          sourceBox: src?box(src):null, originalHidden: org?org.hidden:null,
                          originalBox: org?box(org):null, renderBox: ren?box(ren):null,
                          incoming: Boolean(document.getElementById('edCmpIncoming')),
                          original: Boolean(document.getElementById('edCmpOriginal')),
                          sourceArea: Boolean(document.getElementById('edCmpSource'))};}""")
                pstate = panel.evaluate("""() => {
                  const root=document.getElementById('epRoot');
                  const sec=document.getElementById('epJudgeSec');
                  const head=document.getElementById('epHead');
                  const cs=n=>n?getComputedStyle(n):null;
                  return {judge: root?root.getAttribute('data-judge'):null,
                          secHidden: sec?sec.hidden:null,
                          secDisplay: cs(sec)?cs(sec).display:null,
                          headDisplay: cs(head)?cs(head).display:null,
                          diffText: (document.getElementById('epJudgeDiff')||{}).innerText||'',
                          chips: (document.querySelectorAll('#epJudgeDiff .ep-judge-chip')||[]).length,
                          acts: [...document.querySelectorAll('#epJudgeActs button')]
                                 .map(b=>({id:b.id, text:b.textContent.trim(), disabled:b.disabled}))};}""")
                NOTES["enter_compare"] = {"canvas": state, "panel": pstate, "mode_seq": mode_seq}
                NOTES["dup_msgs"] = {
                    "host": page.evaluate("() => window.__dupSeen || []"),
                    "canvas": canvas.evaluate("() => window.__dupSeen || []"),
                    "panel": panel.evaluate("() => window.__dupSeen || []"),
                    "canvas_activate": canvas.evaluate("() => window.__activateSeen || 0"),
                    "canvas_api": canvas.evaluate(
                        "() => Boolean(window.__jzoEditorV2 && window.__jzoEditorV2.uiDupCompare)"),
                }
                p1 = shot(canvas.locator(".ed-root"), f"{tag}-01-compare-canvas.png", page=page)
                p2 = shot(panel.locator(".ep-root"), f"{tag}-01-compare-panel.png", page=page)
                check("任务一：原图栏收起（hidden/0 宽），第三栏从右滑出且宽 > 0",
                      state.get("mode") == "compare" and state.get("compare") == "true"
                      and state.get("imageHidden") is True
                      and state.get("originalHidden") is False
                      and (state.get("originalBox") or [0, 0, 0, 0])[2] > 40
                      and (state.get("sourceBox") or [0, 0, 0, 0])[2] > 40,
                      {"canvas": state, "shots": [p1.name if p1 else None, p2.name if p2 else None]})
                check("任务二：辅助栏整栏变脸，审核表单让位、裁判台只列差异",
                      pstate.get("judge") == "on" and pstate.get("secHidden") is False
                      and pstate.get("headDisplay") == "none"
                      and len([a for a in pstate.get("acts") or []]) == 4
                      and not re.search(r"暂无|空", pstate.get("diffText") or ""),
                      pstate)
                NOTES["compare_ident"] = panel.evaluate(
                    "() => (document.getElementById('epJudgeIdent')||{}).textContent")

            c_enter_compare()

            # 标好节点身份：换题后只许换内容，不许换壳。
            canvas.evaluate("""() => {
                const rb=document.getElementById('edRenderBody');
                const inc=document.getElementById('edCmpIncoming');
                rb.__probeMark='render-body-stable';
                inc.__probeMark='incoming-stable';
                window.__probeRemovals=0;
                window.__probeObserver=new MutationObserver(ms=>{
                    ms.forEach(m=>{ if (m.type==='childList' && m.removedNodes.length) {
                        for (const n of m.removedNodes) {
                            if (n===inc || (n.contains && n.contains(inc))) window.__probeRemovals++;
                        }}});
                });
                window.__probeObserver.observe(rb, {childList:true});
            }""")
            before = canvas.evaluate("""() => ({
                bodyMark: document.getElementById('edRenderBody').__probeMark||null,
                incMark: document.getElementById('edCmpIncoming').__probeMark||null,
                incText: (document.getElementById('edCmpIncoming').innerText||'').trim().length,
                incBox: (()=>{const r=document.getElementById('edCmpIncoming').getBoundingClientRect();return [r.width,r.height];})(),
                src: ((document.getElementById('edCmpSource')||{}).value||'').trim().slice(0,80),
                current: window.__jzoEditorV2 && window.__jzoEditorV2.uiDupCompare
                         ? window.__jzoEditorV2.uiDupCompare.currentId() : null})""")
            first_ident = panel.evaluate(
                "() => (document.getElementById('epJudgeIdent')||{}).textContent||''")

            # ---- 任务四：改源码 → 500ms 防抖静默回写池内 ----
            marker_a_stem = "查重回写探针甲"
            marker_a_sol = "回写解析甲：先移项，再合并同类项。"
            canvas.evaluate(_EDIT_SOURCE, [marker_a_stem, marker_a_sol])
            pool_url = base + f"/api/pending/pool/{before.get('current')}"
            saved_a = None
            deadline = time.time() + 8
            while time.time() < deadline:
                _, entry_now = GET(pool_url)
                incoming = (entry_now or {}).get("incoming") or {}
                if marker_a_stem in str(incoming.get("stem") or ""):
                    saved_a = incoming
                    break
                time.sleep(0.2)
            check("任务四：新题源码停止输入 500ms 后静默回写池内",
                  bool(saved_a) and marker_a_sol in str(saved_a.get("solution") or ""),
                  {"pool_id": before.get("current"),
                   "stem": str((saved_a or {}).get("stem") or "")[:80],
                   "solution": str((saved_a or {}).get("solution") or "")[:80]})

            def c_advance():
                btn = panel.locator("#epJudgeSeparate")
                btn.wait_for(state="visible", timeout=10000)
                btn.click()
                page.wait_for_timeout(2600)
                after = canvas.evaluate("""() => ({
                    bodyMark: document.getElementById('edRenderBody').__probeMark||null,
                    incMark: (document.getElementById('edCmpIncoming')||{}).__probeMark||null,
                    incText: (document.getElementById('edCmpIncoming').innerText||'').trim().length,
                    incBox: (()=>{const n=document.getElementById('edCmpIncoming');
                        const r=n.getBoundingClientRect();return [r.width,r.height];})(),
                    mode: document.querySelector('.ed-root').getAttribute('data-mode'),
                    removals: window.__probeRemovals,
                    src: ((document.getElementById('edCmpSource')||{}).value||'').trim().slice(0,80),
                    current: window.__jzoEditorV2 && window.__jzoEditorV2.uiDupCompare
                             ? window.__jzoEditorV2.uiDupCompare.currentId() : null})""")
                after_ident = panel.evaluate(
                    "() => (document.getElementById('epJudgeIdent')||{}).textContent||''")
                pool_total = GET(base + "/api/pending/pool")[1].get("total")
                p = shot(canvas.locator(".ed-root"), f"{tag}-02-after-decision.png", page=page)
                pp = shot(panel.locator(".ep-root"), f"{tag}-02-after-decision-panel.png", page=page)
                NOTES["advance"] = {"before": before, "after": after,
                                    "ident_before": first_ident, "ident_after": after_ident,
                                    "pool_total_after": pool_total}
                dump(f"{tag}-02-advance.toml", NOTES["advance"])
                check("任务三：决断后自动跳下一道（池子少一条、当前 id 与源码都变了、对比没退出）",
                      pool_total >= 1 and after.get("mode") == "compare"
                      and after.get("current") and after.get("current") != before.get("current")
                      and after.get("src") and after.get("src") != before.get("src"),
                      {"ident_before": first_ident, "ident_after": after_ident,
                       "src_before": before.get("src"), "src_after": after.get("src"),
                       "current_before": before.get("current"), "current_after": after.get("current"),
                       "pool_total_after": pool_total,
                       "shots": [p.name if p else None, pp.name if pp else None]})
                check("渲染冻结：换题前后 #edRenderBody / #edCmpIncoming 同一只节点，0 次容器移除",
                      after.get("bodyMark") == "render-body-stable"
                      and after.get("incMark") == "incoming-stable"
                      and after.get("removals") == 0
                      and after.get("incText", 0) > 0
                      and (after.get("incBox") or [0, 0])[1] > 20,
                      {"before": before, "after": after})

            c_advance()

            in_bank_a = bank_find(base, marker_a_stem)
            check("任务四续：点【不重复】后，入库题干/解析是修改后的最新值",
                  bool(in_bank_a) and marker_a_sol in str(in_bank_a.get("solution") or ""),
                  {"question_id": (in_bank_a or {}).get("id"),
                   "stem": str((in_bank_a or {}).get("stem") or "")[:80],
                   "solution": str((in_bank_a or {}).get("solution") or "")[:80]})

            # ---- 任务五：改完立刻点裁决，走提交前强保存 ----
            second_id = canvas.evaluate(
                "() => (window.__jzoEditorV2 && window.__jzoEditorV2.uiDupCompare)"
                " ? window.__jzoEditorV2.uiDupCompare.currentId() : null")
            marker_b_stem = "查重回写探针乙"
            marker_b_sol = "回写解析乙：直接点裁决也要带上。"
            canvas.evaluate(_EDIT_SOURCE, [marker_b_stem, marker_b_sol])
            dirty_b = canvas.evaluate(
                "() => {const n=document.getElementById('edCmpSource');"
                " return n ? n.getAttribute('data-dirty') : null;}")
            panel.locator("#epJudgeSeparate").click()
            page.wait_for_timeout(2600)
            in_bank_b = bank_find(base, marker_b_stem)
            check("任务五：改完立刻点【不重复】，强保存把最新题干/解析带进库",
                  dirty_b == "true" and bool(in_bank_b)
                  and marker_b_sol in str(in_bank_b.get("solution") or ""),
                  {"pool_id": second_id, "dirty_at_click": dirty_b,
                   "question_id": (in_bank_b or {}).get("id"),
                   "stem": str((in_bank_b or {}).get("stem") or "")[:80],
                   "solution": str((in_bank_b or {}).get("solution") or "")[:80]})

            check("全程零 pageerror / 零 console error",
                  not PAGE_ERRORS and not CONSOLE_ERRORS,
                  {"page_errors": PAGE_ERRORS[:6], "console_errors": CONSOLE_ERRORS[:6]})
            browser.close()
    except Exception as exc:
        import traceback
        check("探针整体执行", False,
              {"exception": f"{type(exc).__name__}: {exc}",
               "trace": traceback.format_exc().splitlines()[-6:]})
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except Exception:
            proc.kill()
        handle.close()
        EVID.mkdir(parents=True, exist_ok=True)
        out = uniq(EVID / f"{tag}-result.toml")
        out.write_text(toml_io.dumps({"tag": tag, "base": base, "checks": CHECKS,
                                   "note": NOTES, "page_errors": PAGE_ERRORS,
                                   "console_errors": CONSOLE_ERRORS}, default=str),
                       encoding="utf-8")
        print(f"证据：{out}", flush=True)
    ok = sum(1 for c in CHECKS if c["ok"])
    print("=" * 60)
    print(f"{len(CHECKS)} 条检查，通过 {ok}，失败 {len(CHECKS) - ok}，tag={tag}")
    return 0 if ok == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())

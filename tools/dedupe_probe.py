# -*- coding: utf-8 -*-
"""core-bank 查重清洗双栏审查面板真机取证（军令 #18-终 阶段五）。

用法：``.venv/Scripts/python.exe tools/dedupe_probe.py <tag>``

隔离口径：``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` 都指向
``.system_generated/dedupe_probe/<tag>/``，题库由探针自己按冻结 schema 建空库再铺夹具，
不碰开发者 ``data/``，也不复制本机 456 题种子。夹具就是「同题录了两遍」的三种排版。

判据（画布内 1:1 双栏是宿主布局铁律 PLUGIN_SPEC §2.4/§2.9 下的唯一可实现口径）：
  1. 顶部出现【查重清洗】页签（role=tab），点它即扫描，状态行报「已扫 N 题 · 重复 M 题可清」；
  2. 题卡落 ``.cb-dupe-cards`` 网格：**两列等宽**，4 题→左2右2、3 题→左2右1、2 题→左1右1；
  3. 没选保留项时【确认合并】disabled 且提示「先点一张卡上的「保留这题」」；
  4. 单选保留项（鼠标 + 键盘方向键都算）→ 朱砂标记只落在所选卡、按钮解禁、提示改「将删除其余 N 题」；
  5. 【确认合并】落库后队列前进一组（审一组存一组不阻塞），toast 报搬过来的考向/来源/备注数量；
  6. 库内复核：保留项解析追加「解法二/三」且同解法不重复追加、考向与来源并集、副本行真删、
     被删题单题详情接口 404、总行数只按删除数下降；
  7. 【跳过这组】把组轮回队尾且不落库；清完出空态，再点【一键扫描】不重复报组；
  8. 375px 视口双栏并成一栏、插件与宿主都无横向溢出；
  9. 宿主页零未捕获 JS 错误；插件源码三查（``fetch(``/``parent.document``/``localStorage``）归零。
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PLUGIN_ID = "org.jiuzhang.core-bank"
TOKEN = "dedupe-probe-token"
# 建库时间必须落在过去：schema 上有 ck_questions_updated，合并写入的 updated_at 是真机当前时间。
STAMP = "2026-01-15T09:00:00+08:00"

TEXTBOOK = "tb_0d0d0d0d"
SRC_A = "src_0a0a0a0a"
SRC_B = "src_0b0b0b0b"
BO = "tp_bo00000001"
CH = "tp_ch00000001"
KX_A = "tp_kx00000001"
KX_B = "tp_kx00000002"
KX_C = "tp_kx00000003"

STEM_1 = "若 $a>b>0$，则下列不等式成立的是（　　）"
STEM_2 = "若 \\(a>b>0\\)，则下列不等式成立的是(  )"
STEM_3 = "若$a > b > 0$ ， 则下列不等式成立的是 （　　）"
STEM_4 = "若 \\( a>b>0 \\)，则下列不等式成立的是（　）"
OPTIONS = [
    {"key": "A", "content": "$2a>2b$"},
    {"key": "B", "content": "$\\ln a>\\ln b$"},
    {"key": "C", "content": "$a^{2}>b^{2}$"},
    {"key": "D", "content": "$\\dfrac{1}{a}<\\dfrac{1}{b}$"},
]
SOL_A = "两边同乘 2 得 $2a>2b$，故选 A。"
SOL_B = "**解析**：取对数单调性知 $\\ln a>\\ln b$，故选 B。"
SOL_C = "取 $a=2, b=1$ 逐项代入，四个选项里只有 C 恒不成立。"
SOL_B_SPACED = "**解析** ： 取对数单调性 知 $\\ln a > \\ln b$ ， 故选 B 。"   # 与 SOL_B 归一后同句

FILL_1 = "已知 $f(x)=x^{3}-x$，则 $f'(1)=$ ____。"
FILL_2 = "已知 \\(f(x)=x^{3}-x\\)，则 $f'(1)=$　____。"
FILL_SOL_1 = "求导得 $f'(x)=3x^{2}-1$，代 $x=1$ 得 $2$。"
FILL_SOL_2 = "设 $g(x)=x^{3}$，则 $g'(1)=3$，另 $x$ 项导数为 $1$，故 $3-1=2$。"

ESSAY_1 = "已知等差数列 $\\{a_n\\}$ 的前 $n$ 项和为 $S_n$，求 $a_5$。"
ESSAY_2 = "已知等差数列 $\\{ a_n \\}$ 的前 $n$ 项和为 $S_n$ ， 求 $a_5$ 。"
ESSAY_SOL_1 = "由 $S_n$ 的定义展开，$a_5=S_5-S_4$。"
ESSAY_SOL_2 = "读题可知公差为 $2$，$a_5=a_1+4d$。"

GROUP_KEEP = "q_dp002"
GROUP_GHOSTS = ["q_dp001", "q_dp003", "q_dp004"]


def _encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _options(*, shuffle: bool = False) -> str:
    items = [dict(item) for item in OPTIONS]
    if shuffle:
        # 字母不动、正文倒过来：正文集合相同，必须撞成同一个指纹
        items = [{"key": item["key"], "content": other["content"]}
                 for item, other in zip(items, reversed(items))]
    return _encode(items)


def _ext(entries: dict[str, object]) -> str:
    from app.core import bank  # noqa: PLC0415

    return _encode(bank.extensions_to_array(entries))


def _row(qid: str, qtype: str, stem: str, *, options: str | None = None, answer: str | None = "A",
         solution: str | None = None, difficulty: str = "L2", extensions: str | None = None) -> tuple:
    return (qid, qtype, stem, options if options is not None else _options(), answer, solution,
            extensions if extensions is not None else _ext(
                {"org.jiuzhang.core-bank.grade": {"grade": "高一"}}),
            difficulty, STAMP, STAMP)


# 4 题组（q_dp001~004）/ 3 题组（q_dq001~003）/ 2 题组（q_dr001~002）+ 独苗 q_sx001。
QUESTION_ROWS = [
    _row("q_dp001", "single_choice", STEM_1, answer="A", solution=SOL_A,
         extensions=_ext({"org.jiuzhang.core-bank.grade": {"grade": "高一"},
                          "org.jiuzhang.editor": {"note": "副本甲的备注"}})),
    _row(GROUP_KEEP, "single_choice", STEM_2, answer="B", difficulty="L3", solution=SOL_B,
         options=_options(shuffle=True),
         extensions=_ext({"org.jiuzhang.core-bank.grade": {"grade": "高一"},
                          "org.jiuzhang.probe.kept": {"note": "保留项自己的备注"}})),
    _row("q_dp003", "single_choice", STEM_3, answer="A", solution=SOL_C,
         extensions=_ext({"org.jiuzhang.core-bank.grade": {"grade": "高二"},
                          "org.jiuzhang.core-bank.migration": {"flags": ["answer_absent"]}})),
    _row("q_dp004", "single_choice", STEM_4, answer="B", difficulty="L4", solution=SOL_B_SPACED,
         extensions=_ext({"org.jiuzhang.core-bank.grade": {"grade": "高一"}})),
    _row("q_dq001", "fill_blank", FILL_1, options="[]", answer="2", solution=FILL_SOL_1),
    _row("q_dq002", "fill_blank", FILL_2, options="[]", answer="2", solution=FILL_SOL_2),
    _row("q_dq003", "fill_blank", FILL_1, options="[]", answer="2",
         solution=FILL_SOL_1.replace("，", " 、 ")),
    _row("q_dr001", "solution", ESSAY_1, options="[]", answer="a_5=S_5-S_4", solution=ESSAY_SOL_1,
         difficulty="L3"),
    _row("q_dr002", "solution", ESSAY_2, options="[]", answer="a_5=a_1+4d", solution=ESSAY_SOL_2,
         difficulty="L2"),
    _row("q_sx001", "single_choice", "计算 $5!$ 与 $3:2$ 的商是（　　）",
         options=_encode([{"key": "A", "content": "$60$"}, {"key": "B", "content": "$1.5$"}])),
]

TOPIC_LINKS = [
    ("q_dp001", KX_A, 1, 0),
    (GROUP_KEEP, KX_B, 1, 0),
    ("q_dp003", KX_A, 1, 0),
    ("q_dp003", KX_C, 0, 1),
    ("q_dq001", KX_C, 1, 0),
    ("q_dq002", KX_C, 1, 0),
    ("q_dq003", KX_C, 1, 0),
    ("q_dr001", KX_A, 1, 0),
    ("q_dr002", KX_A, 1, 0),
    ("q_sx001", KX_A, 1, 0),
]
SOURCE_LINKS = [
    ("q_dp001", SRC_A, "1"),
    (GROUP_KEEP, SRC_B, "7"),
    ("q_dp003", SRC_A, "1"),        # 与 q_dp001 同卷同题号：合并时必须跳过，不重复成行
    ("q_dp004", SRC_A, "9"),
    ("q_dq001", SRC_A, "12"),
    ("q_dq002", SRC_A, "12"),
    ("q_dq003", SRC_B, "4"),
    ("q_dr001", SRC_B, "18"),
    ("q_dr002", SRC_B, "18"),
    ("q_sx001", SRC_A, "3"),
]

TOPIC_NODES = [
    (BO, None, "必修第一册", BO, 0),
    (CH, BO, "第一章 不等式", f"{BO}/{CH}", 0),
    (KX_A, CH, "不等式性质", f"{BO}/{CH}/{KX_A}", 0),
    (KX_B, CH, "对数比较", f"{BO}/{CH}/{KX_B}", 1),
    (KX_C, CH, "平方比较", f"{BO}/{CH}/{KX_C}", 2),
]

CARDS_JS = """() => {
    const host = document.querySelector('.cb-dupe-cards');
    if (!host) return {missing: true};
    const tracks = getComputedStyle(host).gridTemplateColumns.split(' ').filter(Boolean);
    const boxes = Array.from(host.querySelectorAll('.cb-dupe-card')).map((node) => {
      const r = node.getBoundingClientRect();
      return {id: node.getAttribute('data-dupe-id'), x: Math.round(r.x),
              y: Math.round(r.y), w: Math.round(r.width)};
    });
    const kept = Array.from(document.querySelectorAll('.cb-dupe-kept'))
      .map((node) => node.getAttribute('data-dupe-id'));
    return {tracks: tracks.length, widths: boxes.map((b) => b.w), boxes, kept,
            frameWidth: window.innerWidth,
            overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth};
}"""

PORT = 0


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 30
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError("服务提前退出：\n" + output[:3000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 30 秒内就绪")


def call(method: str, path: str, token: str = "") -> tuple[int, dict]:
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", method=method)
    request.add_header("Accept", "application/json")
    if token:
        request.add_header("X-JZO-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(text or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": text[:400]}


def grid_report(metrics: dict) -> tuple[int, int, int, int]:
    """由题卡包围盒算 (列数, 最左栏张数, 最右栏张数, 最大宽度差)。"""
    boxes = metrics.get("boxes") or []
    if not boxes:
        return 0, 0, 0, 0
    xs = sorted({box["x"] for box in boxes})
    left = [box for box in boxes if box["x"] == xs[0]]
    right = [box for box in boxes if len(xs) > 1 and box["x"] == xs[-1]]
    widths = [box["w"] for box in boxes]
    return len(xs), len(left), len(right), max(widths) - min(widths)


def build_bank(path: Path) -> None:
    from app.core import bank  # noqa: PLC0415

    bank.init_bank(PLUGIN_ID, db_path=path)
    con = sqlite3.connect(path)
    try:
        con.execute(
            "INSERT INTO textbooks (id, name, publisher, edition, is_default, created_at, updated_at)"
            " VALUES (?, '人教A版', '人民教育出版社', '2019 课标版', 1, ?, ?)", (TEXTBOOK, STAMP, STAMP))
        con.executemany(
            "INSERT INTO topics (id, parent_id, textbook_id, name, path, sort_order, status,"
            " created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?)",
            [(node_id, parent, None if node_id.startswith("tp_kx") else TEXTBOOK,
              name, path_value, order, STAMP, STAMP)
             for node_id, parent, name, path_value, order in TOPIC_NODES])
        con.executemany(
            "INSERT INTO sources (id, school_id, year, exam_type, grade, paper_name,"
            " created_at, updated_at) VALUES (?, NULL, ?, '期中考试', '高一', ?, ?, ?)",
            [(SRC_A, 2026, "2026 级高一期中", STAMP, STAMP),
             (SRC_B, 2025, "2025 级高一期末", STAMP, STAMP)])
        con.executemany(
            "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
            " difficulty, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", QUESTION_ROWS)
        con.executemany(
            "INSERT INTO question_topics (question_id, topic_id, is_primary, sort_order, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            [(qid, topic, primary, order, STAMP) for qid, topic, primary, order in TOPIC_LINKS])
        con.executemany(
            "INSERT INTO question_sources (question_id, source_id, question_no, created_at)"
            " VALUES (?, ?, ?, ?)",
            [(qid, source, number, STAMP) for qid, source, number in SOURCE_LINKS])
        con.commit()
    finally:
        con.close()


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    global PORT
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "dedupe_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    shots.mkdir(parents=True)

    shutil.copytree(ROOT / "plugins" / PLUGIN_ID, plugins_dir / PLUGIN_ID)
    # 夹具自给自足：本机 456 题种子与历史备份不进探针现场，免得扫描结果受真实数据干扰
    for junk in (plugins_dir / PLUGIN_ID / "bank").glob("*.db*"):
        junk.unlink()

    os.environ["JZO_DATA_DIR"] = str(data_dir)
    os.environ["JZO_PLUGINS_DIR"] = str(plugins_dir)
    os.environ["JZO_LOCAL_TOKEN"] = TOKEN
    from app.core import bank  # noqa: PLC0415

    # 路径只从 config 取：工作区物理隔离后落点是 data/workspaces/<id>/banks/，别自己拼
    bank_db = bank.bank_db_path(PLUGIN_ID)
    build_bank(bank_db)

    PORT = free_port()
    base = f"http://127.0.0.1:{PORT}"
    env = os.environ.copy()
    env["JZO_RESTART_DISABLED"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(PORT), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [], "page_errors": []}

    def dump() -> None:
        passed = sum(1 for item in result["checks"] if item["ok"])
        result["passed"] = passed
        result["total"] = len(result["checks"])
        result["console_errors"] = result["console_errors"][:20]
        result["ok"] = (result["total"] > 0 and passed == result["total"]
                        and not result["page_errors"] and not result.get("crashed"))
        (work / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    def db() -> sqlite3.Connection:
        con = sqlite3.connect(bank_db)
        con.row_factory = sqlite3.Row
        return con

    try:
        wait_health(base, process)
        status, payload = call("GET", f"/api/bank/plugins/{PLUGIN_ID}/duplicates")
        counts = [group.get("count") for group in payload.get("groups", [])]
        check("扫描接口只读可达且夹具自证",
              status == 200 and payload.get("scanned") == 10 and payload.get("redundant") == 6
              and counts == [4, 3, 2],
              {"status": status, "scanned": payload.get("scanned"),
               "redundant": payload.get("redundant"), "counts": counts})

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            frame = page.frame_locator(".ws-plugin-frame")

            def cards() -> dict:
                return frame.locator("body").evaluate(CARDS_JS)

            def wait_for_cards(expected: int, timeout_ms: int = 20000) -> dict:
                """等队列落到预期张数；不等就把现场记进 probe.json，而不是让整轮白跑。"""
                deadline = time.time() + timeout_ms / 1000
                metrics = cards()
                while time.time() < deadline:
                    metrics = cards()
                    if len(metrics.get("boxes") or []) == expected:
                        return metrics
                    page.wait_for_timeout(200)
                return metrics

            def wait_text(getter, fragment: str, timeout_ms: int = 20000) -> str:
                deadline = time.time() + timeout_ms / 1000
                text = ""
                while time.time() < deadline:
                    node = getter()
                    text = node.inner_text() if node.count() else ""
                    if fragment in text:
                        return text
                    page.wait_for_timeout(200)
                return text

            def pick_card(index: int) -> str:
                card = frame.locator(".cb-dupe-card").nth(index)
                card.locator("input[type=radio]").check()
                return card.get_attribute("data-dupe-id")

            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="真题题库").first
            expect(item).to_be_visible(timeout=15000)
            item.click()
            expect(frame.locator(".cb-title")).to_have_text("真题题库", timeout=20000)
            expect(frame.locator(".cb-row").first).to_be_visible(timeout=20000)
            check("插件挂载并进入题库画布", True)
            header = wait_text(lambda: frame.locator(".cb-sub").first, "共 10 题")
            check("头部题数随库走（不再写死 456）", "共 10 题" in header
                  and "456" not in header, {"header": header})

            tab = frame.locator("button[data-dupe-tab]")
            check("顶部出现查重清洗页签", tab.count() == 1 and tab.get_attribute("role") == "tab",
                  {"role": tab.get_attribute("role"), "text": tab.inner_text()})
            tab.click()
            status_text = wait_text(lambda: frame.locator(".cb-dupe-status"), "已扫")
            check("状态行报总数与可清数", "已扫 10 题" in status_text and "重复 6 题可清" in status_text,
                  {"status": status_text})
            check("页签角标显示重复组数", "查重清洗 3" in tab.inner_text(), {"tab": tab.inner_text()})

            metrics = cards()
            cols, left, right, delta = grid_report(metrics)
            check("4 题组排成左2右2", cols == 2 and left == 2 and right == 2,
                  {"cols": cols, "left": left, "right": right})
            check("双栏 1:1 等宽（宽度差 ≤1px）", delta <= 1, {"widths": metrics.get("widths")})
            check("组头报题数与差异字段",
                  "4 道题面完全相同" in frame.locator(".cb-dupe-title").inner_text()
                  and "考向挂载" in frame.locator(".cb-dupe-diff").inner_text(),
                  {"head": frame.locator(".cb-dupe-title").inner_text(),
                   "diff": frame.locator(".cb-dupe-diff").inner_text()})
            check("题卡内公式落 KaTeX", frame.locator(".cb-dupe-card .katex").count() > 0,
                  {"katex": frame.locator(".cb-dupe-card .katex").count()})

            merge = frame.locator(".cb-dupe-merge")
            check("未选保留项时确认合并禁用",
                  merge.is_disabled() and merge.get_attribute("aria-busy") == "false",
                  {"disabled": merge.is_disabled()})
            check("未选时提示先点保留这题",
                  "先点一张卡上的「保留这题」" in frame.locator(".cb-dupe-merge-tip").inner_text(),
                  {"tip": frame.locator(".cb-dupe-merge-tip").inner_text()})

            picked = pick_card(1)
            check("鼠标单选：朱砂标记只落在所选卡",
                  picked == GROUP_KEEP and cards().get("kept") == [GROUP_KEEP],
                  {"kept": cards().get("kept"), "want": GROUP_KEEP})
            check("选中后解禁并提示将删除其余 3 题",
                  not frame.locator(".cb-dupe-merge").is_disabled()
                  and "将删除其余 3 题" in frame.locator(".cb-dupe-merge-tip").inner_text(),
                  {"tip": frame.locator(".cb-dupe-merge-tip").inner_text()})

            frame.locator(".cb-dupe-card").nth(1).locator("input[type=radio]").press("ArrowRight")
            after_key = cards().get("kept") or []
            check("键盘方向键也能换保留项", len(after_key) == 1 and after_key[0] != picked,
                  {"before": picked, "after": after_key})
            pick_card(1)
            check("换回保留项仍是同一条", cards().get("kept") == [picked], {"kept": cards().get("kept")})

            frame.locator(".cb-dupe-actions button", has_text="展开解析").click()
            check("展开解析后每题都出解析块",
                  frame.locator(".cb-dupe-card .cb-solution").count() == 4,
                  {"solutions": frame.locator(".cb-dupe-card .cb-solution").count()})
            page.screenshot(path=str(shots / "01-dupe-4cards.png"))

            page.set_viewport_size({"width": 375, "height": 740})
            page.wait_for_timeout(500)
            narrow = cards()
            frame_width = page.locator(".ws-plugin-frame").evaluate(
                "(node) => node.getBoundingClientRect().width")
            check("375px 视口下双栏并成一栏",
                  narrow.get("tracks") == 1 and narrow.get("overflowX", 99) <= 1
                  and frame_width < 880,
                  {"tracks": narrow.get("tracks"), "frameWidth": narrow.get("frameWidth"),
                   "frame_css_width": round(frame_width, 1), "overflowX": narrow.get("overflowX")})
            host_metrics = page.evaluate(
                "() => ({scrollWidth: document.documentElement.scrollWidth,"
                " clientWidth: document.documentElement.clientWidth})")
            check("375px 宿主无横向溢出",
                  host_metrics["scrollWidth"] <= host_metrics["clientWidth"] + 1, host_metrics)
            page.screenshot(path=str(shots / "02-dupe-375.png"))
            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_timeout(400)
            back = cards()
            check("回到宽视口双栏复位", grid_report(back)[0] == 2,
                  {"tracks": back.get("tracks"), "frameWidth": back.get("frameWidth")})

            frame.locator(".cb-dupe-merge").click()
            toast_text = wait_text(lambda: frame.locator(".cb-toast"), "已收敛 3 题")
            check("toast 报搬过来的考向/来源/备注",
                  "考向 +2" in toast_text and "来源 +2" in toast_text and "备注 +2" in toast_text,
                  {"toast": toast_text})
            metrics3 = wait_for_cards(3)
            cols3, left3, right3, delta3 = grid_report(metrics3)
            check("审一组存一组：队列前进到 3 题组，排成左2右1",
                  cols3 == 2 and left3 == 2 and right3 == 1 and delta3 <= 1,
                  {"cols": cols3, "left": left3, "right": right3,
                   "ids": [box["id"] for box in metrics3.get("boxes", [])]})
            dock_text = page.locator("#wsDockLog").inner_text()
            check("底栏记录保留项与被删项",
                  f"查重合并完成：保留 {picked}" in dock_text and "q_dp001" in dock_text,
                  {"dock": dock_text[-200:]})
            page.screenshot(path=str(shots / "03-dupe-3cards.png"))

            con = db()
            try:
                total_after = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
                kept_row = con.execute(
                    "SELECT solution, extensions FROM questions WHERE id = ?", (picked,)).fetchone()
                ghost_rows = int(con.execute(
                    f"SELECT COUNT(*) FROM questions WHERE id IN ({','.join('?' * 3)})",
                    GROUP_GHOSTS).fetchone()[0])
                orphan_links = int(con.execute(
                    "SELECT COUNT(*) FROM question_topics WHERE question_id IN"
                    " ('q_dp001','q_dp003','q_dp004')").fetchone()[0])
                orphan_sources = int(con.execute(
                    "SELECT COUNT(*) FROM question_sources WHERE question_id IN"
                    " ('q_dp001','q_dp003','q_dp004')").fetchone()[0])
                mounts = [row[0] for row in con.execute(
                    "SELECT topic_id FROM question_topics WHERE question_id = ? ORDER BY topic_id",
                    (picked,))]
                primary_mounts = [row[0] for row in con.execute(
                    "SELECT topic_id FROM question_topics WHERE question_id = ? AND is_primary = 1",
                    (picked,))]
                sources = [f"{row[0]}#{row[1]}" for row in con.execute(
                    "SELECT source_id, question_no FROM question_sources WHERE question_id = ?"
                    " ORDER BY source_id, question_no", (picked,))]
                fts_rows = None
                if con.execute("SELECT 1 FROM sqlite_master WHERE name='question_fts'").fetchone():
                    fts_rows = int(con.execute("SELECT COUNT(*) FROM question_fts").fetchone()[0])
                fk_bad = len(con.execute("PRAGMA foreign_key_check").fetchall())
            finally:
                con.close()
            solution = kept_row["solution"] or ""
            ext_keys = [item.get("key") for item in json.loads(kept_row["extensions"] or "[]")]
            check("库内：总行数只按删除数下降", total_after == 7,
                  {"total": total_after, "fts_rows": fts_rows})
            check("库内：副本真删且零残留（挂载/来源/外键）",
                  ghost_rows == 0 and orphan_links == 0 and orphan_sources == 0 and fk_bad == 0,
                  {"rows": ghost_rows, "topic_links": orphan_links,
                   "source_links": orphan_sources, "fk_violations": fk_bad})
            check("库内：不同解析追加解法二/三，同解法不重复追加",
                  "**解法二**" in solution and "**解法三**" in solution and "解法四" not in solution,
                  {"solution_tail": solution[-200:]})
            check("库内：考向并集且不顶替主挂载",
                  mounts == sorted([KX_A, KX_B, KX_C]) and primary_mounts == [KX_B],
                  {"mounts": mounts, "primary": primary_mounts})
            check("库内：来源并集且同卷同题号不重复成行",
                  sources == [f"{SRC_A}#1", f"{SRC_A}#9", f"{SRC_B}#7"], {"sources": sources})
            check("库内：备注同名键保留项赢、副本独有键搬走",
                  "org.jiuzhang.editor" in ext_keys
                  and "org.jiuzhang.core-bank.migration" in ext_keys
                  and ext_keys.count("org.jiuzhang.core-bank.grade") == 1,
                  {"keys": ext_keys})

            gone_status, gone_body = call("GET", f"/api/bank/plugins/{PLUGIN_ID}/questions/q_dp001")
            check("被删副本单题详情 404", gone_status == 404,
                  {"status": gone_status, "body": gone_body})

            frame.locator(".cb-dupe-actions button", has_text="跳过这组").click()
            metrics2 = wait_for_cards(2)
            skip_status = frame.locator(".cb-dupe-status").inner_text()
            cols2, left2, right2, delta2 = grid_report(metrics2)
            check("跳过这组：轮回队尾且不落库，2 题组左1右1",
                  cols2 == 2 and left2 == 1 and right2 == 1 and delta2 <= 1
                  and "跳过 1 组" in skip_status and "本轮已收敛 3 题" in skip_status,
                  {"cols": cols2, "left": left2, "right": right2, "status": skip_status,
                   "head": frame.locator(".cb-dupe-title").inner_text()})
            page.screenshot(path=str(shots / "04-dupe-2cards.png"))

            pick_card(1)
            frame.locator(".cb-dupe-merge").click()
            metrics_b = wait_for_cards(3)
            back_ids = [box["id"] for box in metrics_b.get("boxes", [])]
            check("合并 2 题组后，被跳过的 3 题组轮回队首",
                  back_ids == ["q_dq001", "q_dq002", "q_dq003"], {"ids": back_ids})

            check("换组后保留项选择已清空，确认合并重新禁用",
                  frame.locator(".cb-dupe-merge").is_disabled()
                  and not frame.locator(".cb-dupe-kept").count(),
                  {"disabled": frame.locator(".cb-dupe-merge").is_disabled(),
                   "kept": frame.locator(".cb-dupe-kept").count()})
            pick_card(0)
            frame.locator(".cb-dupe-merge").click()
            wait_for_cards(0)
            empty_text = wait_text(lambda: frame.locator(".cb-empty"), "没有需要清洗的重复组了")
            check("清完出空态文案", "没有需要清洗的重复组了" in empty_text, {"empty": empty_text})
            con = db()
            try:
                final_total = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
            finally:
                con.close()
            check("清完：库内只剩 4 题（10 减 6）", final_total == 4, {"total": final_total})
            page.screenshot(path=str(shots / "05-dupe-empty.png"))

            frame.locator(".cb-dupe-bar button", has_text="一键扫描").click()
            dock_rescan = wait_text(lambda: page.locator("#wsDockLog"), "查重扫描完成：4 题里有 0 组")
            rescan = frame.locator(".cb-dupe-status").inner_text()
            check("再扫描不重复报组",
                  "重复 0 题可清" in rescan and frame.locator(".cb-dupe-card").count() == 0
                  and "查重扫描完成：4 题里有 0 组" in dock_rescan,
                  {"status": rescan, "dock": dock_rescan[-160:]})
            check("清完后页签角标归零", tab.inner_text().strip() == "查重清洗",
                  {"tab": tab.inner_text()})
            status_http, payload = call("GET", f"/api/bank/plugins/{PLUGIN_ID}/duplicates")
            check("扫描接口复核：零重复组",
                  status_http == 200 and payload.get("group_count") == 0
                  and payload.get("scanned") == 4,
                  {"group_count": payload.get("group_count"), "scanned": payload.get("scanned")})

            # 题目列表视图必须还回得来：查重清洗接管的是画布，不是把浏览功能换掉
            frame.locator(".cb-views button", has_text="题目列表").click()
            list_text = wait_text(lambda: frame.locator(".cb-pager"), "共 4 题")
            check("清完回到列表视图，剩下的 4 题照常浏览",
                  "共 4 题" in list_text and frame.locator(".cb-row").count() == 4,
                  {"pager": list_text, "rows": frame.locator(".cb-row").count()})

            browser.close()

        js_source = (plugins_dir / PLUGIN_ID / "dist" / "plugin.js").read_text(encoding="utf-8")
        css_source = (plugins_dir / PLUGIN_ID / "dist" / "plugin.css").read_text(encoding="utf-8")
        hits = {
            "fetch(": js_source.count("fetch("),
            "parent.document": js_source.count("parent.document"),
            "localStorage": js_source.count("localStorage"),
            "css @import": css_source.count("@import"),
        }
        check("插件侧三查归零", all(value == 0 for value in hits.values()), hits)
    except BaseException:
        # 长探针崩在半路也得把已跑到的判据落盘，否则整轮白跑、连现场都找不回来
        result["crashed"] = traceback.format_exc()[-4000:]
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    dump()
    print(f"passed {result['passed']}/{result['total']} · {work}")
    for entry in result["checks"]:
        print(("  ✓ " if entry["ok"] else "  ✗ ") + entry["name"])
    if result["page_errors"]:
        print("页面异常：" + " | ".join(result["page_errors"][:5]))
    if result.get("crashed"):
        print("探针中途崩溃：\n" + result["crashed"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

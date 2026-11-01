# -*- coding: utf-8 -*-
"""录题工作台 v3 真机探针（军令 #24）：批次列表首屏 → 点入审核 → 存草稿 → 审完入库 → 批次清零变灰。

用法：``.venv/Scripts/python.exe tools/editor_probe.py <tag>``

隔离：把 editor 与题库两端复制进独立插件目录，另起端口与独立数据目录，
不写本机 data/banks/。题数一律用「保存前后差值」判据，绝不写死绝对数。
AI 改写走本机 OpenAI 兼容桩（JZO_AI_BASE_URL 指向 127.0.0.1），
探针全程不出网，也不依赖本机 .env 里老师的真密钥。

检查项（按军令 #24 的六条铁律逐条落地）：
- **首屏是批次列表**：整幅画布铺满卡片行，左边「时间-星期-时刻-批次编号 #B-xxx」，
  右边「未审：n / N」（数字绿色、贴紧右边缘、垂直居中），整行悬停有反馈；
- **点行任意位置**（连左内边距那种空白处）直接切入三栏审核，抬头写着当前批次号；
- **二屏只有三颗钮**：存入主库 / 存为待办 / 彻底删除；旧的保存、变式与批量条全撤；
- **防呆**：停留超 3 分钟静默存回待审核池，只在底部日志留一行灰字，不弹窗；
- **查重**：主库已有同题时弹窗给「返回修改 / 强行覆盖」，强行覆盖不新增题目；
- **识别有出入照切不误**：画布上不弹红窗，只有底部日志一行警告；
- 审完的批次卡片变灰、沉到列表最底下、点不动（未审 0 / N ✅）；
- 全流程闭环：后台入池 → 批次列表展现 → 点入审核 → 存草稿 → 审完入库 → 批次清零变灰。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
BANK_UI_ID = "org.jiuzhang.bank-ui"
# 右栏的默认住户 AI 助手：探针必须把它一起装上。
# 少了它，右栏没人争，录题的接管自然成功——那种环境验不出「谁才是右栏的主人」。
CHAT_ID = "org.jiuzhang.chat"
TOKEN = "editor-probe-token"
MARK = "探针v3草稿"

CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
PANEL = "#wsContextSlot .ws-context-frame"
BANK_UI = "#wsPanel_plugin_org_jiuzhang_bank-ui .ws-plugin-frame"

BATCH_STAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-星期[日一二三四五六]-\d{2}:\d{2}-批次编号 #B-\d{3,}$")
UNREVIEWED_RE = re.compile(r"未审：\s*(\d+)\s*/\s*(\d+)")
IDLE_NOTE_RE = re.compile(r"^\[\d{2}:\d{2}\] 检测到长时间无操作，已自动存入待审核池。$")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 40
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
    raise RuntimeError("服务未在 40 秒内就绪")


def http_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, json.loads(payload or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": payload}


def http_post(url: str, payload: dict) -> tuple[int, dict]:
    """带写令牌直接打 Host API：探针要自己往中转站塞批次（模拟后台识别入池）。"""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, json.loads(payload or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": payload}


def pending_cards(base: str) -> list[dict]:
    _, data = http_json(base + "/api/pending/batches")
    cards = data.get("batches")
    return cards if isinstance(cards, list) else []


def pending_items(base: str, batch_id: str) -> list[dict]:
    _, data = http_json(base + f"/api/pending/batches/{batch_id}/questions")
    items = data.get("items")
    return items if isinstance(items, list) else []


def bank_total(base: str) -> int:
    _, data = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
    return int(data.get("total") or 0)


def inject_mark(source: str) -> str:
    """把标记塞进题干段的第一行：不管这一题是单选还是解答，都落在正文里。"""
    for env in ("question", "problem"):
        token = "\\begin{" + env + "}\n"
        if token in source:
            return source.replace(token, token + MARK + "：", 1)
    return MARK + source


def wait_attribute(locator, name: str, predicate, timeout: float = 12) -> str:
    """等某个 data-* 属性达到期望值；不达标就返回最后看到的值，让检查项如实报红。"""
    deadline = time.time() + timeout
    value = ""
    while time.time() < deadline:
        value = locator.get_attribute(name) or ""
        if predicate(value):
            return value
        time.sleep(0.15)
    return value


def wait_height(locator, predicate, timeout: float = 12) -> float:
    """渲染是防抖 + KaTeX 同步排版，挂载那一瞬高度还没长开；量高度必须等它稳。"""
    deadline = time.time() + timeout
    height = 0.0
    while time.time() < deadline:
        height = float(locator.evaluate("node => node.getBoundingClientRect().height"))
        if predicate(height):
            return height
        time.sleep(0.15)
    return height


class StubProvider:
    """本机 OpenAI 兼容桩：把 /api/agent/refine 变成确定性回包，探针一律不出网。"""

    MARKER = "探针AI改写"

    def __init__(self) -> None:
        self.hits = 0
        self.fields: list[str] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 的固定入口
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                try:
                    body = json.loads(raw or "{}")
                except json.JSONDecodeError:
                    body = {}
                user = ""
                for message in body.get("messages") or []:
                    if message.get("role") == "user":
                        user = str(message.get("content") or "")
                field_match = re.search(r"## 需要改写的字段\n(\w+)", user)
                field = field_match.group(1) if field_match else "stem"
                content_match = re.search(r"## 该字段当前内容\n([\s\S]*?)\n\n## 老师指令", user)
                original = content_match.group(1).strip() if content_match else ""
                owner.hits += 1
                owner.fields.append(field)
                payload = json.dumps({field: self.server.marker_text(original),
                                      "note": "探针桩按指令改写"}, ensure_ascii=False)
                reply = json.dumps({
                    "choices": [{"message": {"content": payload}}],
                    "model": "probe-stub",
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

        self.port = free_port()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self.httpd.marker_text = lambda original: f"{StubProvider.MARKER}·{original}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


# 两份「后台识别入池」的假卷：一份识别得有出入（题干里嵌了 solution 环境），
# 一份干净但独一无二（留着给彻底删除与自动存草稿验）。
BROKEN_DOC = {
    "schema_version": "2.0",
    "type": "single_choice",
    "stem": "已知函数 $f(x)=x^2+1$，求其最小值（  ）\n\\begin{solution}\n答案：B\n\\end{solution}",
    "options": [
        {"key": "A", "content": "$0$"},
        {"key": "B", "content": "$1$"},
        {"key": "C", "content": "$2$"},
        {"key": "D", "content": "$3$"},
    ],
    "answer": {"kind": "choice", "choice_keys": ["B"], "final": "B"},
    "solution": "解析：配方得 $f(x)=(x-1)^2+1$，故最小值为 $1$。",
    "difficulty": "L1",
    "grade": "高一",
    "tags": ["二次函数"],
    "source": {"paper_title": "探针识别卷", "question_no": "1", "year": 2024, "exam_type": "一模"},
}

UNIQUE_DOC = {
    "schema_version": "2.0",
    "type": "single_choice",
    "stem": "探针专用待删题：直线 $g(x)=2x+1$ 的最小值是（  ）",
    "options": [
        {"key": "A", "content": "$-1$"},
        {"key": "B", "content": "$1$"},
    ],
    "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
    "solution": "解析：$g(x)=2x+1$ 单调递增，最小值为 $-1$。",
    "difficulty": "L1",
    "grade": "高一",
    "tags": ["一次函数"],
    "source": {"paper_title": "探针待删卷", "question_no": "1", "year": 2024, "exam_type": "一模"},
}


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "editor_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    for plugin_id in (EDITOR_ID, BANK_ID, BANK_UI_ID, CHAT_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    stub = StubProvider()
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["JZO_RESTART_DISABLED"] = "1"
    # 活跃档指向本机桩：环境变量优先于仓库 .env（app/__init__._load_local_env 用 setdefault）
    env["JZO_AI_PROVIDER"] = "openai-compatible"
    env["JZO_AI_BASE_URL"] = stub.base_url
    env["JZO_AI_API_KEY"] = "probe-stub-key"
    env["JZO_AI_MODEL"] = "probe-stub"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "metrics": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process)
        total_before = bank_total(base)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()

            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            panel = page.frame_locator(PANEL)
            expect(panel.locator("#epRoot")).to_be_visible(timeout=20000)

            # ---------- 记录器：一帧里所有「话术」与「弹窗」的瞬时变化都留档 ----------
            # 面板回执与画布浮窗都是一改就换的短命状态，轮询会漏；用 MutationObserver 兜住。
            recorder = """() => {
              window.__probeMessages = [];
              window.__probeToasts = [];
              function watch(node, list) {
                if (!node) return;
                var mo = new MutationObserver(function () {
                  list.push({
                    text: (node.textContent || '').trim(),
                    state: node.getAttribute('data-save-state') || '',
                    tone: node.getAttribute('data-tone') || '',
                    show: node.getAttribute('data-show') || ''
                  });
                });
                mo.observe(node, {
                  childList: true, characterData: true, subtree: true,
                  attributes: true,
                  attributeFilter: ['data-save-state', 'data-tone', 'data-show']
                });
                list.push({
                  text: (node.textContent || '').trim(),
                  state: node.getAttribute('data-save-state') || '',
                  tone: node.getAttribute('data-tone') || '',
                  show: node.getAttribute('data-show') || ''
                });
              }
              watch(document.getElementById('epMessage'), window.__probeMessages);
              watch(document.getElementById('edToast'), window.__probeToasts);
              return true;
            }"""
            panel.locator("#epRoot").evaluate(recorder)
            canvas.locator("#edRoot").evaluate(recorder)

            def probe_messages() -> list[dict]:
                return panel.locator("#epRoot").evaluate("() => window.__probeMessages || []")

            def probe_toasts() -> list[dict]:
                return canvas.locator("#edRoot").evaluate("() => window.__probeToasts || []")

            def dock_entries() -> list[dict]:
                """底部日志全量条目：底栏收起时正文不可见，但条目还在 DOM 里。"""
                return page.locator("#wsDockLog .ws-dock-item").evaluate_all(
                    """nodes => nodes.map(node => ({
                        level: node.getAttribute('data-level') || '',
                        copy: node.getAttribute('data-copy') || '',
                        text: (node.querySelector('.ws-dock-text') || {}).textContent || ''
                    }))""")

            def wait_dock(predicate, timeout: float = 30, since: int = 0):
                deadline = time.time() + timeout
                while time.time() < deadline:
                    entries = dock_entries()
                    for entry in entries[since:]:
                        if predicate(entry):
                            return entry
                    page.wait_for_timeout(200)
                return None

            def wait_message(fragment: str, timeout: float = 25) -> bool:
                """面板回执是短命状态：轮询 + 记录器双保险。"""
                deadline = time.time() + timeout
                while time.time() < deadline:
                    if any(fragment in item.get("text", "") for item in probe_messages()):
                        return True
                    page.wait_for_timeout(40)
                return False

            def panel_pending_id() -> str:
                return panel.locator("#epRoot").evaluate(
                    "() => { var p = window.__jzoEditorV2.panel;"
                    " return p && p.selection ? String(p.selection.pending_id || '') : ''; }")

            def canvas_pending_id() -> str:
                return canvas.locator("#edRoot").evaluate(
                    """() => { var s = window.__jzoEditorV2.state;
                       var it = s.items ? s.items[s.active] : null;
                       return it ? String(it.pendingId || '') : ''; }""")

            def sync_panel(timeout: float = 20) -> str:
                """等辅助栏的选区追上涨布的当前题：审核动作全靠 pending_id 对得上。"""
                deadline = time.time() + timeout
                current = ""
                while time.time() < deadline:
                    current = canvas_pending_id()
                    if current and current == panel_pending_id():
                        return current
                    page.wait_for_timeout(120)
                return ""

            def to_list() -> None:
                """回到首屏批次列表：审核界面里那批卡片是收着的，点不到。"""
                if canvas.locator("#edRoot").get_attribute("data-mode") == "list":
                    return
                canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.backToList()")
                expect(canvas.locator("#edBatches")).to_be_visible(timeout=20000)

            def open_batch(batch_id: str) -> None:
                to_list()
                row = canvas.locator('.ed-batch-row[data-batch="%s"]' % batch_id)
                expect(row).to_be_visible(timeout=20000)
                row.click()
                expect(canvas.locator("#edCols")).to_be_visible(timeout=20000)

            def wait_pool_shrink(base_url: str, batch: str, before: int, timeout: float = 30) -> int:
                deadline = time.time() + timeout
                count = before
                while time.time() < deadline:
                    count = len(pending_items(base_url, batch))
                    if count < before:
                        return count
                    page.wait_for_timeout(200)
                return count

            # ---------- 首屏：批次列表 ----------
            check("首屏铺满批次列表（三栏还收着）",
                  canvas.locator("#edBatches").is_visible()
                  and canvas.locator("#edCols").is_hidden()
                  and canvas.locator("#edBatchBar").is_hidden()
                  and canvas.locator("#edRoot").get_attribute("data-mode") == "list",
                  {"mode": canvas.locator("#edRoot").get_attribute("data-mode")})
            seed_row = canvas.locator(".ed-batch-row").first
            expect(seed_row).to_be_visible(timeout=20000)
            cards = pending_cards(base)
            check("识别结果已入池，首屏就有批次可点",
                  len(cards) >= 1 and canvas.locator(".ed-batch-row").count() == len(cards),
                  {"cards": len(cards), "rows": canvas.locator(".ed-batch-row").count()})
            batch_id = cards[0]["batch_id"]
            result["metrics"]["seed_batch"] = batch_id
            # 这一批是插件自己入池的识别结果：题型/答案长什么样，底座说了算，
            # 探针不自己编一份预期，全按 API 回的正文来对。
            seed_items = pending_items(base, batch_id)
            seed_doc = dict((seed_items[0].get("question") or {})) if seed_items else {}
            result["metrics"]["seed_type"] = seed_doc.get("type")

            left_text = seed_row.locator(".ed-batch-left").inner_text()
            check("卡片左侧是「日期-星期-时刻-批次编号 #B-xxx」",
                  bool(BATCH_STAMP_RE.match(left_text.strip())),
                  {"left": left_text})
            right_text = seed_row.locator(".ed-batch-right").inner_text()
            hit = UNREVIEWED_RE.search(right_text)
            check("卡片右侧是「未审：n / N」，数字与底座对得上",
                  bool(hit)
                  and int(hit.group(1)) == int(cards[0]["pending_count"])
                  and int(hit.group(2)) == int(cards[0]["total"]),
                  {"right": right_text, "card": cards[0]})
            num_color = seed_row.locator(".ed-batch-num").first.evaluate(
                "n => getComputedStyle(n).color")
            check("未审数字是绿色的", num_color == "rgb(47, 107, 79)",
                  {"color": num_color})
            justify = seed_row.evaluate("n => getComputedStyle(n).justifyContent")
            check("卡片两端对齐（space-between）", justify == "space-between",
                  {"justify": justify})
            row_box = seed_row.bounding_box()
            right_box = seed_row.locator(".ed-batch-right").bounding_box()
            flush = round((row_box["x"] + row_box["width"])
                          - (right_box["x"] + right_box["width"]), 2)
            vertical = round(abs((row_box["y"] + row_box["height"] / 2)
                                 - (right_box["y"] + right_box["height"] / 2)), 2)
            check("未审数贴紧右边缘、垂直居中",
                  0 <= flush <= 24 and vertical <= 4,
                  {"flush": flush, "vertical": vertical})
            bg_before = seed_row.evaluate("n => getComputedStyle(n).backgroundColor")
            seed_row.hover()
            page.wait_for_timeout(300)
            bg_after = seed_row.evaluate("n => getComputedStyle(n).backgroundColor")
            check("整行悬停有反馈", bg_before != bg_after,
                  {"before": bg_before, "after": bg_after})
            page.screenshot(path=str(shots / "v3-batch-list.png"))

            # ---------- 后台识别入池：再塞两批（一份识别有出入，一份干净待删） ----------
            status_broken, broken_body = http_post(
                base + "/api/pending/batches",
                {"questions": [{"question": BROKEN_DOC}], "origin": "probe.recognize"})
            status_unique, unique_body = http_post(
                base + "/api/pending/batches",
                {"questions": [{"question": UNIQUE_DOC}], "origin": "probe.recognize"})
            check("后台可把识别结果整批入池",
                  status_broken == 201 and status_unique == 201,
                  {"broken": status_broken, "unique": status_unique})
            broken_batch = str(broken_body.get("batch_id") or "")
            unique_batch = str(unique_body.get("batch_id") or "")
            canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.refreshBatches()")
            page.wait_for_timeout(700)
            check("批次列表跟着底座走（新批次立刻显形）",
                  canvas.locator(".ed-batch-row").count() == len(pending_cards(base)),
                  {"rows": canvas.locator(".ed-batch-row").count(),
                   "cards": len(pending_cards(base))})

            # ---------- 点行任意位置：连左内边距的空白处也进得去 ----------
            target_row = canvas.locator('.ed-batch-row[data-batch="%s"]' % batch_id)
            expect(target_row).to_be_visible(timeout=10000)
            box = target_row.bounding_box()
            page.mouse.click(box["x"] + 4, box["y"] + box["height"] / 2)
            expect(canvas.locator("#edCols")).to_be_visible(timeout=20000)
            check("点行任意位置直接切入三栏审核",
                  canvas.locator("#edBatches").is_hidden()
                  and canvas.locator("#edBatchBar").is_visible(),
                  {"mode": canvas.locator("#edRoot").get_attribute("data-mode")})
            batch_no = canvas.locator("#edBatchNo").inner_text().strip()
            check("二屏抬头写着当前批次号", batch_no == "批次 #" + batch_id,
                  {"batch_no": batch_no})
            batch_stat = canvas.locator("#edBatchStat").inner_text().strip()
            card = next(c for c in pending_cards(base) if c["batch_id"] == batch_id)
            check("二屏抬头报着这一批还剩几道",
                  batch_stat == "未审 %d / %d" % (int(card["pending_count"]), int(card["total"])),
                  {"stat": batch_stat, "card": card})

            # ---------- 三栏骨架 ----------
            pending_count = int(card["pending_count"])
            check("画布恰好三栏", canvas.locator(".ed-col").count() == 3,
                  {"panes": canvas.locator(".ed-col").count()})
            check("两条拖手在场", canvas.locator(".ed-split").count() == 2)
            first_source = canvas.locator(".ed-src-area").first.input_value()
            seed_stem = str(seed_doc.get("stem") or "")
            check("中栏装整段 exam-zh 源码",
                  bool(seed_stem) and seed_stem in first_source
                  and "\\begin{" in first_source and "\\end{" in first_source
                  and "\\begin{solution}" in first_source,
                  {"head": first_source[:80], "stem": seed_stem[:80]})
            check("三栏铺的是这一批的待审题",
                  canvas.locator(".ed-src-area").count() == pending_count,
                  {"rows": canvas.locator(".ed-src-area").count(),
                   "pending": pending_count})
            block_height = wait_height(canvas.locator(".ed-q-block").first,
                                       lambda value: value > 40)
            check("渲染块按内容实际高度生长", block_height > 40, {"height": block_height})
            check("画布不再有 A4 固定页节点",
                  canvas.locator(".ed-page, [data-page-h]").count() == 0)
            check("画布内没有任何顶栏或工具条",
                  canvas.locator(".ed-bar, #edRoot header, #edFmtLatex, #edFmtBoxed, #edSwapMode")
                  .count() == 0)
            check("画布没有底部横条，钮只有逐题跳转与回列表",
                  canvas.locator(".ed-foot").count() == 0
                  and canvas.locator("#edCols button").count()
                  == canvas.locator(".ed-img-jump").count()
                  and canvas.locator("#edBatchBar button").count() == 1,
                  {"col_buttons": canvas.locator("#edCols button").count(),
                   "jumps": canvas.locator(".ed-img-jump").count(),
                   "bar_buttons": canvas.locator("#edBatchBar button").count(),
                   "foot": canvas.locator(".ed-foot").count()})

            def row_lines():
                """三栏每一行虚线的位置：行内三栏的 cell 底边该落在同一条线上。"""
                return canvas.locator("#edImageBody").evaluate(
                    """node => {
                        var bodies = {
                            image: node,
                            source: document.querySelector('#edSourceBody'),
                            render: document.querySelector('#edRenderBody')
                        };
                        var counts = ['image', 'source', 'render'].map(function (key) {
                            return bodies[key] ? bodies[key].children.length : 0;
                        });
                        var count = Math.min.apply(null, counts);
                        var rows = [];
                        for (var i = 0; i < count; i += 1) {
                            var line = { row: i + 1 };
                            var values = [];
                            ['image', 'source', 'render'].forEach(function (key) {
                                var body = bodies[key];
                                var cell = body ? body.children[i] : null;
                                var box = cell ? cell.getBoundingClientRect() : null;
                                var value = box
                                    ? Math.round((box.top + box.height) * 100) / 100 : null;
                                line[key] = value;
                                if (value !== null) values.push(value);
                            });
                            line.spread = values.length
                                ? Math.round((Math.max.apply(null, values)
                                    - Math.min.apply(null, values)) * 100) / 100
                                : null;
                            rows.push(line);
                        }
                        return rows;
                    }""")

            def dashed_ok(rows) -> bool:
                return bool(rows) and all(
                    row["spread"] is not None and row["spread"] <= 1.0 for row in rows)

            frame_tops = [round(canvas.locator(sel).bounding_box()["y"], 2) for sel in
                          ("#edPaneImage", "#edWorkbench")]
            head_tops = [round(canvas.locator(sel + " .ed-pane-head").bounding_box()["y"], 2)
                         for sel in ("#edPaneImage", "#edPaneSource", "#edPaneRender")]
            check("三栏顶部框线落在同一像素水平线",
                  max(frame_tops) - min(frame_tops) <= 0.5
                  and max(head_tops) - min(head_tops) <= 0.5,
                  {"frame_tops": frame_tops, "head_tops": head_tops})
            src_box = canvas.locator("#edPaneSource").bounding_box()
            rnd_box = canvas.locator("#edPaneRender").bounding_box()
            check("中右两栏底边落在同一像素水平线",
                  abs(round(src_box["y"] + src_box["height"], 2)
                      - round(rnd_box["y"] + rnd_box["height"], 2)) <= 0.5,
                  {"source_bottom": round(src_box["y"] + src_box["height"], 2),
                   "render_bottom": round(rnd_box["y"] + rnd_box["height"], 2)})
            lines = row_lines()
            check("三栏虚线逐行落在同一条线上", dashed_ok(lines), {"rows": lines[:3]})
            page.screenshot(path=str(shots / "v3-review.png"))

            # ---------- 右栏辅助面板 ----------
            check("辅助栏不放源码框", panel.locator(".ed-src-area, .ed-box-area").count() == 0,
                  {"src": panel.locator(".ed-src-area").count(),
                   "boxes": panel.locator(".ed-box-area").count()})
            check("辅助栏不放渲染预览", panel.locator(".ed-q-block").count() == 0)
            audit_texts = [text.strip() for text in
                           panel.locator('section[aria-label="审核动作"] button').all_inner_texts()]
            check("审核动作只有三颗钮：存入主库 / 存为待办 / 彻底删除",
                  audit_texts == ["存入主库", "存为待办", "彻底删除"],
                  {"buttons": audit_texts})
            check("旧的保存、变式与批量条全撤了",
                  panel.locator("#epSave, #epVariant, #edSaveAll, #edPoolStash").count() == 0
                  and canvas.locator("#edSaveAll, .ed-foot").count() == 0,
                  {"panel_legacy": panel.locator("#epSave, #epVariant, #edSaveAll, #edPoolStash").count(),
                   "canvas_legacy": canvas.locator("#edSaveAll, .ed-foot").count()})
            check("台账只报数，不带任何按钮", panel.locator("#edPool button").count() == 0,
                  {"buttons": panel.locator("#edPool button").count()})
            slot_title = page.locator("#wsContextSlotTitle").inner_text().strip()
            slot_badge = page.locator("#wsContextSlotBadge").inner_text().strip()
            slot_src = page.locator("#wsContextSlotBody .ws-context-frame").get_attribute("src") or ""
            check("右栏主人是录题工作台（不是 AI 助手）",
                  slot_title == "录题工作台" and slot_badge == "插件接管"
                  and "org.jiuzhang.editor" in slot_src,
                  {"title": slot_title, "badge": slot_badge, "src": slot_src})
            for label, selector in (("题型", "#epType"), ("难度", "#epDifficulty"),
                                    ("年级", "#epGrade")):
                check(f"辅助栏里元数据表单还在（{label}）",
                      panel.locator(selector).count() == 1
                      and panel.locator(selector).is_visible(),
                      {"selector": selector})
            fmt_boxes = [panel.locator(sel).bounding_box() for sel in
                         ("#epFmtLatex", "#epFmtBoxed", "#epSwap")]
            one_row = all(box is not None for box in fmt_boxes) and (
                max(box["y"] for box in fmt_boxes) - min(box["y"] for box in fmt_boxes) < 8)
            check("格式一/格式二/互换同一行", one_row, {"boxes": fmt_boxes})
            dock_box = panel.locator("#epDock").bounding_box()
            root_box = panel.locator("#epRoot").bounding_box()
            check("台账钉在辅助栏最底边",
                  dock_box is not None and root_box is not None
                  and 0 <= root_box["y"] + root_box["height"]
                  - (dock_box["y"] + dock_box["height"]) <= 4,
                  {"root": root_box, "dock": dock_box})
            page.screenshot(path=str(shots / "v3-panel.png"))

            # ---------- 存为待办：改过的题原地写回中转池 ----------
            area = canvas.locator('.ed-src-area[data-index="0"]').first
            expect(area).to_be_visible(timeout=10000)
            area.click()
            area.fill(inject_mark(area.input_value()))
            edited_source = area.input_value()
            deadline = time.time() + 15
            panel_got = False
            while time.time() < deadline:
                current = panel.locator("#epRoot").evaluate(
                    "() => String((window.__jzoEditorV2.panel || {}).source || '')")
                if MARK in current:
                    panel_got = True
                    break
                page.wait_for_timeout(100)
            check("改动经选区送进辅助栏", panel_got,
                  {"panel_source": current[:80] if current else ""})
            pool_before = pending_items(base, batch_id)
            panel.locator("#epStash").click()
            check("【存为待办】给出回执", wait_message("已存为待办"),
                  {"messages": [m.get("text", "") for m in probe_messages()][-4:]})
            pool_after = pending_items(base, batch_id)
            check("存为待办是原地更新：池子里不多出一道重影",
                  len(pool_after) == len(pool_before),
                  {"before": len(pool_before), "after": len(pool_after)})
            check("改过的内容真的落进中转池",
                  any(MARK in str(item.get("question", {}).get("stem", ""))
                      for item in pool_after),
                  {"stems": [str(item.get("question", {}).get("stem", ""))[:40]
                             for item in pool_after][:3]})
            page.screenshot(path=str(shots / "v3-stash.png"))

            # ---------- 存入主库：p_ 号段换成 q_ 号段 ----------
            dock_mark = len(dock_entries())
            total_pre_approve = bank_total(base)
            panel.locator("#epApprove").click()
            approve_line = wait_dock(lambda e: "已存入主库" in e.get("text", ""), 30, dock_mark)
            check("【存入主库】给出回执", wait_message("已存入主库"),
                  {"messages": [m.get("text", "") for m in probe_messages()][-4:]})
            check("底部日志记下入库回执", approve_line is not None, {"line": approve_line})
            question_id = ""
            if approve_line:
                hit = re.search(r"(q_[A-Za-z0-9_-]{8,64})", approve_line.get("text", ""))
                question_id = hit.group(1) if hit else ""
            result["metrics"]["question_id"] = question_id
            check("入库回执带着合法的题目 ID",
                  bool(re.fullmatch(r"q_[A-Za-z0-9_-]{8,64}", question_id)),
                  {"id": question_id})
            total_post_approve = bank_total(base)
            check("主库总数 +1", total_post_approve == total_before + 1,
                  {"before": total_before, "after": total_post_approve})
            status, document = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}")
            check("主库里查得到这道题", status == 200, {"status": status})
            check("入库的是改过的那一版题干",
                  MARK in str(document.get("stem", "")),
                  {"stem": str(document.get("stem", ""))[:80]})
            doc_answer = document.get("answer") or {}
            seed_answer = seed_doc.get("answer") or {}
            choice_types = ("single_choice", "multiple_choice")
            if str(seed_doc.get("type") or "") in choice_types:
                answer_ok = list(doc_answer.get("choice_keys") or []) == list(
                    seed_answer.get("choice_keys") or [])
            else:
                answer_ok = str(doc_answer.get("final") or "").strip() == str(
                    seed_answer.get("final") or "").strip()
            check("题型/答案按源码还原",
                  str(document.get("type") or "") == str(seed_doc.get("type") or "")
                  and answer_ok
                  and str(doc_answer.get("final") or "") in edited_source,
                  {"type": document.get("type"), "answer": doc_answer,
                   "seed_type": seed_doc.get("type"), "seed_answer": seed_answer})
            pool_now = pending_items(base, batch_id)
            check("入库后这一题从中转池消失",
                  len(pool_now) == len(pool_after) - 1,
                  {"before": len(pool_after), "after": len(pool_now)})
            check("画布上那一道也撤了下来",
                  canvas.locator(".ed-src-area").count() == pending_count - 1,
                  {"rows": canvas.locator(".ed-src-area").count()})

            # ---------- 审完这一批：剩下的逐道入库 ----------
            for _ in range(pending_count - 1):
                if not sync_panel():
                    break
                before = len(pending_items(base, batch_id))
                panel.locator("#epApprove").click()
                wait_pool_shrink(base, batch_id, before, 30)
            check("这一批审完了：池子里一条不剩", not pending_items(base, batch_id),
                  {"items": len(pending_items(base, batch_id))})
            expect(canvas.locator("#edBatches")).to_be_visible(timeout=20000)
            check("审完自动回到批次列表",
                  canvas.locator("#edRoot").get_attribute("data-mode") == "list",
                  {"mode": canvas.locator("#edRoot").get_attribute("data-mode")})

            # ---------- 审完的卡片：变灰、沉底、点不动 ----------
            done_row = canvas.locator('.ed-batch-row[data-batch="%s"]' % batch_id)
            expect(done_row).to_be_visible(timeout=10000)
            done_text = done_row.inner_text()
            check("审完的卡片写着「未审：0 / N ✅」",
                  bool(re.search(r"未审：\s*0\s*/\s*\d+\s*✅", done_text)),
                  {"text": done_text})
            check("审完的卡片点不动",
                  done_row.is_disabled()
                  and done_row.get_attribute("aria-disabled") == "true"
                  and done_row.get_attribute("data-done") == "true",
                  {"disabled": done_row.is_disabled(),
                   "aria": done_row.get_attribute("aria-disabled"),
                   "done": done_row.get_attribute("data-done")})
            done_opacity = done_row.evaluate("n => getComputedStyle(n).opacity")
            check("审完的卡片整行变灰", float(done_opacity) < 1,
                  {"opacity": done_opacity})
            done_num_color = done_row.locator(".ed-batch-num").first.evaluate(
                "n => getComputedStyle(n).color")
            check("审完的卡片数字也褪成灰的", done_num_color == "rgb(109, 99, 85)",
                  {"color": done_num_color})
            order = canvas.locator(".ed-batch-row").evaluate_all(
                "nodes => nodes.map(n => [n.getAttribute('data-batch'),"
                " n.getAttribute('data-done')])")
            flags = [flag for _batch, flag in order]
            first_done = flags.index("true") if "true" in flags else len(flags)
            check("审完的批次沉到列表最底下",
                  flags[first_done:] == ["true"] * len(flags[first_done:])
                  and order[first_done][0] == batch_id,
                  {"order": order})
            page.screenshot(path=str(shots / "v3-done.png"))
            done_box = done_row.bounding_box()
            page.mouse.click(done_box["x"] + 4, done_box["y"] + done_box["height"] / 2)
            page.wait_for_timeout(500)
            check("点不动的批次进不去审核",
                  canvas.locator("#edRoot").get_attribute("data-mode") == "list"
                  and canvas.locator("#edCols").is_hidden(),
                  {"mode": canvas.locator("#edRoot").get_attribute("data-mode")})

            # ---------- 查重：主库已有同题 → 返回修改 / 强行覆盖 ----------
            status, dup_doc = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}")
            status_dup, dup_body = http_post(
                base + "/api/pending/batches",
                {"questions": [{"question": dup_doc}], "origin": "probe.recognize"})
            check("另一份卷认出同一道题，已入池",
                  status_dup == 201 and int(dup_body.get("batch", {}).get("total") or 0) >= 1,
                  {"status": status_dup, "batch": dup_body.get("batch")})
            dup_batch = str(dup_body.get("batch_id") or "")
            canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.refreshBatches()")
            page.wait_for_timeout(500)
            check("批次列表多出一行",
                  canvas.locator(".ed-batch-row").count() == len(pending_cards(base)),
                  {"rows": canvas.locator(".ed-batch-row").count()})
            open_batch(dup_batch)
            sync_panel()
            panel.locator("#epApprove").click()
            expect(panel.locator("#epDupModal")).to_be_visible(timeout=25000)
            check("查重命中弹出「返回修改 / 强行覆盖」",
                  panel.locator("#epDupBack").inner_text().strip() == "返回修改"
                  and panel.locator("#epDupForce").inner_text().strip() == "强行覆盖",
                  {"back": panel.locator("#epDupBack").inner_text(),
                   "force": panel.locator("#epDupForce").inner_text()})
            check("弹窗里带着主库那道题的编号",
                  bool(re.search(r"q_[A-Za-z0-9_-]{8,64}", panel.locator("#epDupText").inner_text())),
                  {"text": panel.locator("#epDupText").inner_text()})
            page.screenshot(path=str(shots / "v3-dup.png"))
            panel.locator("#epDupBack").click()
            expect(panel.locator("#epDupModal")).to_be_hidden(timeout=10000)
            check("点【返回修改】：题还留在中转池里",
                  len(pending_items(base, dup_batch)) == 1,
                  {"items": len(pending_items(base, dup_batch))})
            total_before_force = bank_total(base)
            panel.locator("#epApprove").click()
            expect(panel.locator("#epDupModal")).to_be_visible(timeout=25000)
            panel.locator("#epDupForce").click()
            deadline = time.time() + 30
            while time.time() < deadline and pending_items(base, dup_batch):
                page.wait_for_timeout(200)
            check("【强行覆盖】把主库那道题盖掉，题数不增",
                  bank_total(base) == total_before_force
                  and not pending_items(base, dup_batch),
                  {"before": total_before_force, "after": bank_total(base),
                   "items": len(pending_items(base, dup_batch))})

            # ---------- 识别有出入：照切不误，只在底部日志留一行警告 ----------
            toasts_before = len(probe_toasts())
            open_batch(broken_batch)
            warn_line = wait_dock(lambda e: "识别有出入" in e.get("text", ""), 30)
            check("识别有出入只在底部日志留一行警告",
                  warn_line is not None and warn_line.get("level") == "warn",
                  {"line": warn_line})
            check("画布上没有弹红窗",
                  not any(item.get("tone") == "error" for item in probe_toasts()[toasts_before:]),
                  {"toasts": probe_toasts()[toasts_before:]})
            check("识别有出入的题照样切进三栏",
                  canvas.locator(".ed-src-area").count() >= 1,
                  {"rows": canvas.locator(".ed-src-area").count()})
            page.screenshot(path=str(shots / "v3-broken.png"))

            # ---------- 三分钟无操作：静默存回中转池，只留一行灰字 ----------
            open_batch(unique_batch)
            sync_panel()
            items_before_idle = pending_items(base, unique_batch)
            doc_before = dict(items_before_idle[0].get("question", {})) if items_before_idle else {}
            stamp_before = items_before_idle[0].get("updated_at", "") if items_before_idle else ""
            canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.tickIdle()")
            idle_line = wait_dock(lambda e: IDLE_NOTE_RE.match(e.get("copy", "") or "") is not None, 40)
            check("长时间无操作只留一行灰字",
                  idle_line is not None and idle_line.get("level") == "note",
                  {"line": idle_line})
            items_after_idle = pending_items(base, unique_batch)
            check("自动存草稿是原地更新：池子里条数不变",
                  len(items_after_idle) == len(items_before_idle),
                  {"before": len(items_before_idle), "after": len(items_after_idle)})
            check("自动存草稿真的写回中转池",
                  bool(items_after_idle)
                  and str(items_after_idle[0].get("updated_at", "")) != stamp_before,
                  {"before": stamp_before,
                   "after": items_after_idle[0].get("updated_at") if items_after_idle else ""})
            doc_after = dict(items_after_idle[0].get("question", {})) if items_after_idle else {}
            check("自动存草稿不抹掉年级、标签与来源",
                  doc_after.get("grade") == doc_before.get("grade")
                  and doc_after.get("tags") == doc_before.get("tags")
                  and doc_after.get("source") == doc_before.get("source"),
                  {"before": {"grade": doc_before.get("grade"), "tags": doc_before.get("tags"),
                              "source": doc_before.get("source")},
                   "after": {"grade": doc_after.get("grade"), "tags": doc_after.get("tags"),
                             "source": doc_after.get("source")}})
            check("自动存草稿不弹窗",
                  not any(item.get("tone") == "error" for item in probe_toasts()[toasts_before:]),
                  {"toasts": probe_toasts()[toasts_before:]})

            # ---------- 彻底删除：先问一句再删 ----------
            total_before_delete = bank_total(base)
            card_before = next(c for c in pending_cards(base)
                               if c["batch_id"] == unique_batch)
            panel.locator("#epDelete").click()
            expect(panel.locator("#epDelModal")).to_be_visible(timeout=10000)
            check("彻底删除先弹确认框",
                  panel.locator("#epDelOk").inner_text().strip() == "彻底删除",
                  {"ok": panel.locator("#epDelOk").inner_text()})
            panel.locator("#epDelCancel").click()
            expect(panel.locator("#epDelModal")).to_be_hidden(timeout=10000)
            page.wait_for_timeout(400)
            check("点【取消】什么也没删",
                  len(pending_items(base, unique_batch)) == 1,
                  {"items": len(pending_items(base, unique_batch))})
            panel.locator("#epDelete").click()
            expect(panel.locator("#epDelModal")).to_be_visible(timeout=10000)
            panel.locator("#epDelOk").click()
            deadline = time.time() + 25
            while time.time() < deadline and pending_items(base, unique_batch):
                page.wait_for_timeout(200)
            check("【彻底删除】把这一题从中转池抹掉",
                  not pending_items(base, unique_batch),
                  {"items": len(pending_items(base, unique_batch))})
            check("彻底删除不碰主库", bank_total(base) == total_before_delete,
                  {"before": total_before_delete, "after": bank_total(base)})
            card_after = next(c for c in pending_cards(base)
                              if c["batch_id"] == unique_batch)
            check("删掉一题，这一批的总题数也减一",
                  int(card_after["total"]) == int(card_before["total"]) - 1,
                  {"before": card_before["total"], "after": card_after["total"]})
            page.screenshot(path=str(shots / "v3-delete.png"))

            # ---------- F5 连刷三轮：首屏永远是批次列表 ----------
            for round_index in range(1, 4):
                page.reload(wait_until="networkidle")
                page.wait_for_timeout(1200)
                reopen = page.locator(".ws-plugin-item", has_text="录题工作台").first
                expect(reopen).to_be_visible(timeout=15000)
                reopen.click()
                expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
                page.wait_for_timeout(900)
                check(f"第 {round_index} 次刷新：首屏仍是批次列表",
                      canvas.locator("#edBatches").is_visible()
                      and canvas.locator("#edCols").is_hidden()
                      and canvas.locator("#edRoot").get_attribute("data-mode") == "list",
                      {"mode": canvas.locator("#edRoot").get_attribute("data-mode")})
                check(f"第 {round_index} 次刷新：批次一条没少",
                      canvas.locator(".ed-batch-row").count() == len(pending_cards(base)),
                      {"rows": canvas.locator(".ed-batch-row").count(),
                       "cards": len(pending_cards(base))})
                page.screenshot(path=str(shots / f"v3-reload-{round_index}.png"))

            # ---------- 回流：题库画布搜得到本次入库的题 ----------
            bank_item = page.locator(".ws-plugin-item", has_text="真题题库").first
            bank_item.click()
            bank_frame = page.frame_locator(BANK_UI)
            search = bank_frame.locator(".cb-search")
            expect(search).to_be_visible(timeout=20000)
            search.fill(MARK)
            search.press("Enter")
            page.wait_for_timeout(1500)
            rows = bank_frame.locator(".cb-row").count()
            check("题库画布搜到本次入库的题", rows >= 1, {"rows": rows})
            page.screenshot(path=str(shots / "v3-bank-ui.png"))

            size_host = page.locator("body").evaluate(
                "() => ({scrollWidth: document.body.scrollWidth,"
                " clientWidth: document.documentElement.clientWidth})")
            check("宿主无横向溢出", size_host["scrollWidth"] <= size_host["clientWidth"] + 1,
                  size_host)
            check("全流程跑完页面仍无脚本错误", not result["page_errors"],
                  {"page_errors": result["page_errors"][:3]})
            browser.close()
    except Exception as exc:  # noqa: BLE001 - 探针要把失败原样落盘
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            page.screenshot(path=str(shots / "failure.png"))
        except Exception:
            pass
    finally:
        stub.stop()
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = bool(result["checks"]) and all(item["ok"] for item in result["checks"]) \
        and not result["page_errors"] and "error" not in result
    (work / "probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    passed = sum(1 for item in result["checks"] if item["ok"])
    print(("PASS" if result["ok"] else "FAIL")
          + f" · {passed}/{len(result['checks'])} 项 · {work}")
    for item in result["checks"]:
        print(("  OK  " if item["ok"] else "  FAIL") + item["name"])
        if not item["ok"]:
            print("      " + json.dumps(item.get("detail"), ensure_ascii=False)[:400])
    if result["console_errors"]:
        print("console:", result["console_errors"][:8])
    if result["page_errors"]:
        print("pageerrors:", result["page_errors"][:8])
    if "error" in result:
        print("error:", result["error"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

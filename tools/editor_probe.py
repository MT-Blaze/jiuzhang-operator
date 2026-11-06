# -*- coding: utf-8 -*-
"""录题工作台 v3 真机探针（军令 #24）：批次列表首屏 → 点入审核 → 存草稿 → 审完入库 → 批次清零变灰。

用法：``.venv/Scripts/python.exe tools/editor_probe.py <tag>``

隔离：把 editor 与题库两端复制进独立插件目录，另起端口与独立数据目录，
不写本机 data/banks/。题数一律用「保存前后差值」判据，绝不写死绝对数。
AI 改写走本机 OpenAI 兼容桩（JZO_AI_BASE_URL 指向 127.0.0.1），
探针全程不出网，也不依赖本机 .env 里老师的真密钥。

检查项（按军令 #24 的六条铁律逐条落地）：
- **首屏是批次列表**：整幅画布铺满卡片行，第一行是原文件名，第二行灰字
  「月-日 时刻 | 批次 #B-xxx」，右边「待审 n / N」（数字绿色），整行悬停有反馈；
- **点行任意位置**（连左内边距那种空白处）直接切入三栏审核，抬头写着当前批次号；
- **二屏底栏四颗钮**：单题入库 / 全部入库 / 存为待审 / 彻底删除；旧的保存、变式与批量条全撤；
- **防呆**：停留超 3 分钟静默存回待审核池，只在底部日志留一行灰字，不弹窗；
- **查重拦截**（军令 #31）：命中先亮画布红呼吸灯与辅助栏红字，两侧**渲染**对比，
  三个裁决「覆盖 / 放弃 / 合并为解析二」只住辅助栏（画布里一颗按钮都没有）；
  两边答案不同时两颗写库钮锁死、只留放弃；覆盖不新增题目，合并只增「解法二」；
- **识别有出入照切不误**：画布上不弹红窗，只有底部日志一行警告；
- 审完的批次卡片变灰、沉到列表最底下、点不动（待审 0 / N ✅）；
- 全流程闭环：后台入池 → 批次列表展现 → 点入审核 → 存草稿 → 审完入库 → 批次清零变灰。
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import socket
import sqlite3
import struct
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
BANK_UI_ID = "org.jiuzhang.bank-ui"
TOKEN = "editor-probe-token"
MARK = "探针v3草稿"

CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
PANEL = "#wsContextSlot .ws-context-frame"
BANK_UI = "#wsPanel_plugin_org_jiuzhang_bank-ui .ws-plugin-frame"

BATCH_STAMP_RE = re.compile(r"^\d{2}-\d{2} \d{2}:\d{2} \| 批次 #B-\d{3,}$")
# 卡片右侧是「待审 n / N」：n 是这一批在池里的真实行数，N 是录入时累加的总数。
CARD_COUNT_RE = re.compile(r"待审\s*(?P<pending>\d+)\s*/\s*(?P<total>\d+)")
# 军令 #32 第五步的账：抽走的题另记「池内」，入库的记「已入库」，池内【删除】的记「已裁删」，
# 四段合起来才等于总数（ui_batches.js:206-219 卡片、:129-134 ledgerText 抬头同一份算法）。
# 首屏卡片正脸已精简成「待审 n / N」，四段账仍留在 aria-label 与隐藏的批次状态里，
# 这里按 aria-label 断等式，不放宽成「含未审二字」。
LEDGER_RE = re.compile(
    r"未审\s*(?P<pending>\d+)"
    r"(?:\s*＋ 池内\s*(?P<pooled>\d+))?"
    r"(?:\s*＋ 已入库\s*(?P<stored>\d+))?"
    r"(?:\s*＋ 已裁删\s*(?P<gone>\d+))?"
    r"\s*＝\s*总数\s*(?P<total>\d+)")
STAT_LEDGER_RE = re.compile(
    r"未审 (?P<pending>\d+)"
    r"(?: ＋ 池内 (?P<pooled>\d+))?"
    r"(?: ＋ 已入库 (?P<stored>\d+))?"
    r"(?: ＋ 已裁删 (?P<gone>\d+))?"
    r" ＝ 总数 (?P<total>\d+)")


def ledger_terms(hit: "re.Match[str] | None") -> dict:
    """把上面两条正则的命中拆成四个数＋一个对平布尔（缺段按 0）。"""
    if hit is None:
        return {}
    terms = {name: int(hit.group(name) or 0)
             for name in ("pending", "pooled", "stored", "gone", "total")}
    terms["balanced"] = (terms["pending"] + terms["pooled"] + terms["stored"] + terms["gone"]
                         == terms["total"])
    return terms
IDLE_NOTE_RE = re.compile(r"^\[\d{2}:\d{2}\] 检测到长时间无操作，已自动存入待审核池。$")
# 1×1 的 PNG：粘贴只验「字节进了批次」，不验图像内容。
# 字节用**数字数组**递进页面，不走 base64 字符串——atob 在不同浏览器上对
# 补位字符的宽容度不一样，字符串一旦少一位就是一条看不懂的 InvalidCharacterError。
PNG_BYTES = list(base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAE"
    "hQGAhKmMIQAAAABJRU5ErkJggg=="
))


def make_png(width: int, height: int) -> bytes:
    """纯 Python 造一张四色块的 PNG：切图切到哪一块，按像素就能判出来。

    不依赖 PIL：探针环境里未必装了 Pillow，而这一张图只需要几行 zlib 与 CRC。
    """
    rows = []
    for y in range(height):
        row = bytearray([0])                      # filter type 0（None）
        for x in range(width):
            left = x < width // 2
            top = y < height // 2
            row += bytes((255, 0, 0) if left and top else
                         (0, 255, 0) if not left and top else
                         (0, 0, 255) if left else
                         (255, 255, 0))
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
            + chunk(b"IEND", b""))


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen, log_path: Path | None = None) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        if process.poll() is not None:
            output = ""
            if log_path and log_path.exists():
                output = log_path.read_text(encoding="utf-8", errors="replace")
            elif process.stdout:
                output = process.stdout.read()
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


def seed_topics(data_dir: Path, plugin_id: str) -> list[dict]:
    """给隔离题库种一棵小小的考向树。

    非 default 工作区按底座口径一律建空库（没有考向、也没有题），
    幽灵胶囊的「带路径模糊搜索」就没有路径可拼——这里手工种一棵，
    让探针能真验到「册 › 章 › 节 › 考向」这条路径，而不是只看个空壳。
    """
    db = data_dir / "banks" / f"{plugin_id}.db"
    if not db.is_file():
        return []
    now = time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
    rows = [
        ("tp_bo00000001", None, "必修一册", "tp_bo00000001"),
        ("tp_ch00000002", "tp_bo00000001", "第一章 函数与导数",
         "tp_bo00000001/tp_ch00000002"),
        ("tp_se00000003", "tp_ch00000002", "1.1 函数的概念与性质",
         "tp_bo00000001/tp_ch00000002/tp_se00000003"),
        ("tp_kx00000004", "tp_se00000003", "函数单调性与最值",
         "tp_bo00000001/tp_ch00000002/tp_se00000003/tp_kx00000004"),
    ]
    con = sqlite3.connect(db, timeout=10.0)
    try:
        for order, (topic_id, parent_id, name, path) in enumerate(rows):
            con.execute(
                "INSERT OR REPLACE INTO topics"
                " (id, parent_id, textbook_id, name, path, sort_order, status,"
                "  created_at, updated_at)"
                " VALUES (?, ?, NULL, ?, ?, ?, 'active', ?, ?)",
                (topic_id, parent_id, name, path, order, now, now))
        con.commit()
    finally:
        con.close()
    return [{"id": row[0], "name": row[2], "path": row[3]} for row in rows]


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
    """渲染是防抖 + MathJax 同步排版，挂载那一瞬高度还没长开；量高度必须等它稳。"""
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

            def do_GET(self) -> None:  # noqa: N802 - 密钥池连通性要读 /v1/models
                if not self.path.rstrip("/").endswith("/models"):
                    self.send_response(404)
                    self.end_headers()
                    return
                reply = json.dumps({
                    "object": "list",
                    "data": [{"id": "probe-stub", "object": "model"}],
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 的固定入口
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                try:
                    body = json.loads(raw or "{}")
                except json.JSONDecodeError:
                    body = {}
                user = ""
                system = ""
                for message in body.get("messages") or []:
                    role = message.get("role")
                    if role == "user":
                        user = str(message.get("content") or "")
                    elif role == "system":
                        system = str(message.get("content") or "")
                # 单题/批量 AI 识别（任务三）也走同一个 OpenAI 兼容口：
                # 桩必须按 SYSTEM_PROMPT 回结构化题，否则解析结果缺答案，
                # 静默存池会被 validateForSave 拦下，批量账上全记失败。
                if "数学试卷录题助手" in system or "数学解题助手" in system:
                    solve_only = "数学解题助手" in system
                    marker = f"{StubProvider.MARKER}·"
                    document = (
                        {"answer": "x=1",
                         "solution": marker + "由 $x+1=2$ 得 $x=1$。",
                         "note": "探针桩按系统提示回结构化题"}
                        if solve_only else
                        {"type": "solution",
                         "stem": marker + "求 $x+1=2$ 的解。",
                         "options": [], "answer": "x=1",
                         "solution": marker + "由 $x+1=2$ 得 $x=1$。",
                         "question_no": "", "difficulty": "L1"}
                    )
                    payload = json.dumps(document, ensure_ascii=False)
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
                    return
                # 军令 #28：学校全称补全走同一个 OpenAI 兼容口，桩也得认出来，
                # 否则 UI 只会拿到一段「改写结果」JSON，全称永远是空的。
                if "名称补全助手" in system or user.startswith("简称："):
                    matched = re.search(r"简称：(.+)", user)
                    short = matched.group(1).strip().splitlines()[0].strip() if matched else ""
                    known = {
                        "哈三中": "哈尔滨市第三中学校",
                        "师大附中": "哈尔滨师范大学附属中学",
                        "哈师大附中": "哈尔滨师范大学附属中学",
                        "哈九中": "哈尔滨市第九中学校",
                    }
                    full = known.get(short, f"{short}（探针补全）" if short else "")
                    payload = json.dumps(
                        {"full_name": full, "confidence": 0.9 if full else 0.0},
                        ensure_ascii=False,
                    )
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
                    return
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
    for plugin_id in (EDITOR_ID, BANK_ID, BANK_UI_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    stub = StubProvider()
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["JZO_RESTART_DISABLED"] = "1"
    # 种子卷的四道题本来就长得很像：不关查重准入，后台会当场抽走 3 道，
    # 后面的题号/行数/沉底判据全都会对着一条残卷比，必假红。
    env["JZO_POOL_ADMIT_DISABLED"] = "1"
    # 活跃档指向本机桩：环境变量优先于仓库 .env（app/__init__._load_local_env 用 setdefault）
    env["JZO_AI_PROVIDER"] = "openai-compatible"
    env["JZO_AI_BASE_URL"] = stub.base_url
    env["JZO_AI_API_KEY"] = "probe-stub-key"
    env["JZO_AI_MODEL"] = "probe-stub"
    server_log = work / "server.log"
    # 服务端日志落盘：访问日志能回答「哪个口子的 400」，
    # 控制台只说「有个资源 400」，定位不到人。
    log_handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": [], "write_calls": [],
                    "metrics": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process, server_log)
        total_before = bank_total(base)
        # 隔离工作区是空库：种一棵考向树，幽灵胶囊才有真路径可拼。
        seeded_topics = seed_topics(data_dir, BANK_ID)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            # 非 2xx 的响应单独记一笔：控制台只说「有个资源 400」，
            # 不知道是哪个口子的锅——这行日志才是定位用的证据。
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url))
                if response.status >= 400 else None)
            # 写操作（建学校、记标签、入池）连请求体一起留档：
            # 只看状态码分不清「没发出去」和「发出去被拦」。
            page.on("request", lambda request: result["write_calls"].append(
                "%s %s %s" % (request.method, request.url, request.post_data or ""))
                if request.method == "POST" and "/api/meta/" in request.url else None)
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
                # 上一批留下的对比浮层还开着时，它会挡住卡片行：老师用 Esc 收窗，探针跟着走。
                if canvas.locator("#edDupModal").is_visible():
                    canvas.locator("#edDupModal").press("Escape")
                    expect(canvas.locator("#edDupModal")).to_be_hidden(timeout=10000)
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
                  and canvas.locator("#edBatchBar").count() == 0
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

            left_text = seed_row.locator(".ed-batch-name").inner_text()
            meta_text = seed_row.locator(".ed-batch-meta").inner_text()
            check("卡片第一行是原文件名",
                  bool(left_text.strip()),
                  {"name": left_text})
            check("卡片第二行是「月-日 时刻 | 批次 #B-xxx」",
                  bool(BATCH_STAMP_RE.match(meta_text.strip())),
                  {"meta": meta_text})
            right_text = seed_row.locator(".ed-batch-right").inner_text()
            count = CARD_COUNT_RE.search(right_text)
            aria = seed_row.locator(".ed-batch-open").get_attribute("aria-label") or ""
            hit = LEDGER_RE.search(aria)
            terms = ledger_terms(hit)
            check("卡片右侧是「待审 n / N」，数字与底座对得上，账目等式仍成立",
                  bool(count)
                  and int(count.group("pending")) == int(cards[0]["pending_count"])
                  and int(count.group("total")) == int(cards[0]["total"])
                  and terms["balanced"],
                  {"right": right_text, "aria": aria, "card": cards[0]})
            num_color = seed_row.locator(".ed-batch-num").first.evaluate(
                "n => getComputedStyle(n).color")
            check("未审数字是绿色的", num_color == "rgb(47, 107, 79)",
                  {"color": num_color})
            justify = seed_row.locator(".ed-batch-open").evaluate(
                "n => getComputedStyle(n).justifyContent")
            check("卡片的题面与未审数两端对齐（space-between）", justify == "space-between",
                  {"justify": justify})
            row_box = seed_row.bounding_box()
            right_box = seed_row.locator(".ed-batch-right").bounding_box()
            open_box = seed_row.locator(".ed-batch-open").bounding_box()
            flush = round((open_box["x"] + open_box["width"])
                          - (right_box["x"] + right_box["width"]), 2)
            vertical = round(abs((open_box["y"] + open_box["height"] / 2)
                                 - (right_box["y"] + right_box["height"] / 2)), 2)
            check("未审数贴紧题面按钮右缘、垂直居中",
                  0 <= flush <= 24 and vertical <= 4,
                  {"flush": flush, "vertical": vertical})
            purge_box = seed_row.locator(".ed-batch-purge").bounding_box()
            delete_box = seed_row.locator(".btn-delete-batch").bounding_box()
            row_gap = round((row_box["x"] + row_box["width"])
                            - (delete_box["x"] + delete_box["width"]), 2)
            pair_gap = round(delete_box["x"]
                             - (purge_box["x"] + purge_box["width"]), 2)
            check("「删除批次」贴紧整行右缘，「剔除重复」紧挨在它左边",
                  0 <= row_gap <= 24 and 0 <= pair_gap <= 16,
                  {"row_gap": row_gap, "pair_gap": pair_gap,
                   "purge_x": purge_box["x"], "delete_x": delete_box["x"]})
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
            check("点行任意位置直接切入三栏审核（画布抬头一根毛都不留）",
                  canvas.locator("#edBatches").is_hidden()
                  and canvas.locator("#edBatchBar").count() == 0
                  and canvas.locator("#edBackList").count() == 0
                  and panel.locator("#epBackList").is_visible(),
                  {"mode": canvas.locator("#edRoot").get_attribute("data-mode")})
            batch_no = canvas.locator("#edBatchNo").inner_text().strip()
            check("读屏状态位记着当前批次号", batch_no == "批次 #" + batch_id,
                  {"batch_no": batch_no})
            batch_stat = canvas.locator("#edBatchStat").inner_text().strip()
            card = next(c for c in pending_cards(base) if c["batch_id"] == batch_id)
            stat_terms = ledger_terms(STAT_LEDGER_RE.match(batch_stat))
            check("二屏抬头报着这一批还剩几道（与卡片同一份分段账）",
                  bool(stat_terms)
                  and stat_terms["pending"] == int(card["pending_count"])
                  and stat_terms["total"] == int(card["total"])
                  and stat_terms["balanced"],
                  {"stat": batch_stat, "card": card})

            # ---------- 批次公共元数据：辅助栏顶部，改一次整批跟着改 ----------
            check("辅助栏顶部有公共元数据面板",
                  panel.locator(".ep-meta").count() == 1
                  and panel.locator("#epMetaYear").count() == 1
                  and panel.locator("#epMetaRegion").count() == 1
                  and panel.locator("#epMetaBody").count() == 1
                  and panel.locator("#epMetaScene").count() == 1
                  and panel.locator("#epMetaExamType").count() == 1
                  and panel.locator("#epMetaSubject").count() == 1
                  and panel.locator("#epStdName").count() == 1
                  and panel.locator("#epSchoolInput").count() == 1,
                  {"meta_sections": panel.locator(".ep-meta").count()})
            check("标准名那一格可以手改（双向联动的入口）",
                  panel.locator("#epStdName").get_attribute("readonly") is None
                  and panel.locator("#epStdName").get_attribute("data-mode") == "auto"
                  and panel.locator("#epStdHint").get_attribute("data-mode") == "auto",
                  {"readonly": panel.locator("#epStdName").get_attribute("readonly"),
                   "mode": panel.locator("#epStdName").get_attribute("data-mode")})
            check("辅助栏顶部第一行是原文件名、第二行是标准名",
                  panel.locator("#epSrcName").count() == 1
                  and panel.locator("#epStdName").count() == 1
                  and panel.locator(".ep-top .ep-src-name").count() == 1,
                  {})
            # 11 个场景由底座字典下发：先等下拉真的装满，再往下考标准名。
            expect(panel.locator("#epMetaScene option")).to_have_count(12, timeout=15000)
            panel.locator("#epMetaYear").fill("2024")
            panel.locator("#epMetaRegion").fill("黑吉辽")
            panel.locator("#epMetaBody").fill("三省六校")
            panel.locator("#epMetaScene").select_option("校考题")
            panel.locator("#epMetaExamType").fill("高三联考")
            panel.locator("#epMetaSubject").fill("数学")
            expect(panel.locator("#epMetaSchools")).to_be_visible(timeout=8000)

            # ---------- 军令 #28：学校字典（AI 补全 → 确认 → 建档） ----------
            panel.locator("#epSchoolInput").fill("哈三中")
            panel.locator("#epSchoolInput").press("Enter")
            expect(panel.locator("#epSchoolConfirm")).to_be_visible(timeout=15000)
            expect(panel.locator("#epSchoolConfirmOk")).to_be_enabled(timeout=15000)
            suggest_full = panel.locator("#epSchoolFullName").input_value()
            check("查不到学校时先让 AI 补全全称，不擅自建档",
                  suggest_full == "哈尔滨市第三中学校",
                  {"full_name": suggest_full})
            status, dict_before = http_json(
                base + "/api/meta/schools?q=" + urllib.parse.quote("哈三中"))
            check("AI 建议只放在确认卡里：此刻字典还是空的",
                  status == 200 and dict_before.get("schools") == [],
                  {"schools": dict_before.get("schools")})
            panel.locator("#epSchoolConfirmOk").click()
            expect(panel.locator("#epSchoolList .ep-school")).to_have_count(1, timeout=15000)
            chip = panel.locator("#epSchoolList .ep-school").first
            chip_id = chip.get_attribute("data-school-id") or ""
            chip_text = panel.locator("#epSchoolList").inner_text()
            check("老师确认后学校进字典，胶囊带 school_id、显示简称",
                  chip_id.startswith("sch_") and "哈三中" in chip_text,
                  {"id": chip_id, "chips": chip_text})

            # ---------- 军令 #28：交叉标签（按场景加权 + 模糊匹配 + 回车即记） ----------
            panel.locator("#epMetaExamType").fill("")
            panel.locator("#epMetaScene").select_option("外国题")
            panel.locator("#epMetaExamType").focus()
            expect(panel.locator("#epTagMenu")).to_be_visible(timeout=10000)
            foreign_menu = [text.strip() for text in
                            panel.locator("#epTagMenu .ep-menu-item").all_inner_texts()]
            check("选【外国题】时 AMC / A-Level / IB 先冒头",
                  [line.split("\n")[0].strip() for line in foreign_menu][:3]
                  == ["AMC", "A-Level", "IB"],
                  {"menu": foreign_menu})
            panel.locator("#epMetaScene").select_option("校考题")
            panel.locator("#epMetaExamType").fill("模")
            expect(panel.locator("#epTagMenu .ep-menu-item")).to_have_count(8, timeout=10000)
            mo_menu = [text.strip().split("\n")[0].strip() for text in
                       panel.locator("#epTagMenu .ep-menu-item").all_inner_texts()]
            check("打一个「模」字，零到七模一次带出来",
                  all(name in mo_menu for name in
                      ("零模", "一模", "二模", "三模", "四模", "五模", "六模", "七模")),
                  {"menu": mo_menu})
            page.screenshot(path=str(shots / "v28-tag-menu.png"))
            # 终极军令任务二：拼音首字母是第二条检索路，依据还得亮在候选右边。
            panel.locator("#epMetaExamType").fill("ym")
            expect(panel.locator("#epTagMenu")).to_be_visible(timeout=10000)
            pinyin_menu = [text.strip().split("\n")[0].strip() for text in
                           panel.locator("#epTagMenu .ep-menu-item").all_inner_texts()]
            check("敲拼音首字母 ym 捞出「一模」", "一模" in pinyin_menu, {"menu": pinyin_menu})
            tag_hints = panel.locator("#epTagMenu .ep-menu-hint").all_inner_texts()
            check("候选右侧亮出首字母依据", any("YM" in str(h) for h in tag_hints),
                  {"hints": tag_hints[:8]})
            panel.locator("#epMetaExamType").fill("百日誓师考")
            panel.locator("#epMetaExamType").press("Enter")
            deadline = time.time() + 20
            saved_tag = None
            while time.time() < deadline:
                status, tag_body = http_json(
                    base + "/api/meta/tags?scene=" + urllib.parse.quote("校考题")
                    + "&q=" + urllib.parse.quote("百日"))
                saved_tag = next((tag for tag in tag_body.get("tags", [])
                                  if tag.get("name") == "百日誓师考"), None)
                # 种子里早有一条全局权重的「百日誓师考」；要等的是本场景那一笔。
                if saved_tag and saved_tag.get("scene_weight", 0) >= 1:
                    break
                page.wait_for_timeout(200)
            check("老师手打的新标签，回车即记进本地标签库",
                  saved_tag is not None and saved_tag.get("scene_weight", 0) >= 1,
                  {"tag": saved_tag})
            panel.locator("#epMetaExamType").fill("百日")
            expect(panel.locator("#epTagMenu")).to_be_visible(timeout=10000)
            next_menu = panel.locator("#epTagMenu").inner_text()
            check("下次再打「百日」，新标签立刻弹出来",
                  "百日誓师考" in next_menu, {"menu": next_menu[:120]})
            panel.locator("#epMetaExamType").fill("rsk")
            expect(panel.locator("#epTagMenu")).to_be_visible(timeout=10000)
            remembered_menu = [text.strip().split("\n")[0].strip() for text in
                               panel.locator("#epTagMenu .ep-menu-item").all_inner_texts()]
            check("手打的标签连拼音一起记住：敲 rsk 捞出「百日誓师考」",
                  "百日誓师考" in remembered_menu, {"menu": remembered_menu})
            panel.locator("#epMetaExamType").fill("高三联考")
            panel.locator("#epMetaExamType").press("Enter")
            page.wait_for_timeout(300)

            standard = panel.locator("#epStdName").input_value()
            check("标准名按「年份-地区-主体-场景-类型-学科」自动拼出来",
                  standard == "2024-黑吉辽-三省六校-校考题-高三联考-数学",
                  {"standard": standard})

            # ---------- 军令 #28：标准名双向联动（闪烁 / 手改暂停 / 再动恢复） ----------
            panel.locator("#epMetaRegion").fill("黑龙江")
            page.wait_for_timeout(150)
            flash_live = panel.locator("#epStdFlash").evaluate(
                "n => ({text: (n.textContent || '').trim(), show: n.getAttribute('data-show')})")
            std_paint = panel.locator("#epStdName").evaluate(
                """n => ({
                    flash: n.getAttribute('data-flash'),
                    background: getComputedStyle(n).backgroundColor
                })""")
            check("元数据一改，标准名实时重拼并闪一下「已更新」",
                  flash_live["show"] == "true" and "已更新" in flash_live["text"],
                  {"flash": flash_live, "name": panel.locator("#epStdName").input_value()})
            check("重拼的标准名当场闪淡黄（主公要的是那一闪，不是只有文字）",
                  std_paint["flash"] == "true"
                  and std_paint["background"] == "rgb(253, 243, 214)",
                  {"paint": std_paint})
            page.screenshot(path=str(shots / "v28-std-flash.png"))
            panel.locator("#epStdName").fill("我手改的卷名")
            page.wait_for_timeout(200)
            check("手改标准名：自动拼接当场暂停",
                  panel.locator("#epStdName").get_attribute("data-mode") == "manual"
                  and "暂停" in panel.locator("#epStdHint").inner_text(),
                  {"mode": panel.locator("#epStdName").get_attribute("data-mode"),
                   "hint": panel.locator("#epStdHint").inner_text()})
            panel.locator("#epMetaRegion").fill("黑吉辽")
            page.wait_for_timeout(400)
            resumed = panel.locator("#epStdName").input_value()
            resumed_mode = panel.locator("#epStdName").get_attribute("data-mode")
            check("再动元数据：自动拼接恢复，手改名被重拼覆盖",
                  resumed_mode == "auto"
                  and resumed == "2024-黑吉辽-三省六校-校考题-高三联考-数学",
                  {"mode": resumed_mode, "name": resumed})

            expected_name = "2024-黑吉辽-三省六校-校考题-高三联考-数学"
            # UI 极致瘦身令收尾：年级回到批次公共元数据，与年份、地区同一行。
            grade_wiring = panel.locator("#epMetaGrade").evaluate(
                """n => ({
                    row: !!(n.closest('.ep-row')
                            && n.closest('.ep-row').querySelector('#epMetaYear, #epMetaRegion')),
                    maxlength: n.getAttribute('maxlength'),
                    placeholder: n.getAttribute('placeholder')
                })""")
            check("批次公共元数据有年级输入框，就排在年份、地区旁边",
                  panel.locator("#epMetaGrade").count() == 1 and grade_wiring["row"],
                  {"grade": grade_wiring})
            deadline = time.time() + 30
            synced_source: dict = {}
            synced_tags: list = []
            while time.time() < deadline:
                items = pending_items(base, batch_id)
                synced_source = dict((items[0].get("question") or {}).get("source") or {}) if items else {}
                synced_tags = list((items[0].get("question") or {}).get("tags") or []) if items else []
                if synced_source.get("paper_title") == expected_name \
                        and synced_source.get("scene_type") == "校考题":
                    break
                page.wait_for_timeout(300)
            check("改公共字段，这一批的题立刻同步 sources",
                  synced_source.get("body") == "三省六校"
                  and synced_source.get("region") == "黑吉辽"
                  and synced_source.get("scene_type") == "校考题"
                  and synced_source.get("exam_type") == "高三联考"
                  and int(synced_source.get("year") or 0) == 2024
                  and synced_source.get("paper_title") == expected_name,
                  {"source": synced_source})
            check("题目只落 school_id，校名一个字节都不进题目",
                  synced_source.get("school_id") == chip_id
                  and chip_id in list(synced_source.get("school_ids") or [])
                  and not synced_source.get("school"),
                  {"source": synced_source})
            check("老口径的隐藏校名标签不再生成",
                  not [tag for tag in synced_tags if str(tag).startswith("#")],
                  {"tags": synced_tags})

            # ---------- 终极军令任务一：简称一撞车就当场锁死 ----------
            def lock_state():
                return panel.locator("#epRoot").evaluate(
                    """() => ({
                        invalid: document.getElementById('epSchoolInput').getAttribute('aria-invalid'),
                        error_hidden: document.getElementById('epSchoolError').hidden,
                        error_text: document.getElementById('epSchoolError').textContent,
                        create_rows: document.querySelectorAll('#epSchoolMenu [data-school-create]').length,
                        confirm: document.getElementById('epSchoolConfirmOk').disabled,
                        approve: document.getElementById('epApprove').disabled
                    })""")

            approve_open = panel.locator("#epApprove").evaluate("n => !n.disabled")
            status, seeded = http_post(
                base + "/api/meta/schools",
                {"full_name": "哈尔滨师范大学附属中学", "short_name": "师大附中"})
            check("预置一所同名简称的学校", status == 201, {"status": status, "body": seeded})
            panel.locator("#epSchoolInput").fill("师大附中")
            deadline = time.time() + 20
            during = {}
            while time.time() < deadline:
                during = lock_state()
                if "简称冲突" in str(during.get("error_text") or ""):
                    break
                page.wait_for_timeout(200)
            border_color = panel.locator("#epSchoolInput").evaluate(
                "n => getComputedStyle(n).borderTopColor")
            check("输入简称就撞车：不等点确认，输入框当场爆红",
                  during.get("invalid") == "true"
                  and during.get("error_hidden") is False
                  and "简称冲突，已被【哈尔滨师范大学附属中学】占用" in str(during.get("error_text") or "")
                  and "is-invalid" in (panel.locator("#epSchoolInput").get_attribute("class") or "")
                  and border_color == "rgb(155, 59, 45)",
                  {"state": during, "border": border_color})
            check("撞车期间不给第二所同名简称开门",
                  int(during.get("create_rows") or 0) == 0,
                  {"menu": panel.locator("#epSchoolMenu").inner_text(), "state": during})
            check("撞车期间【确认建档】与【单题入库】双双锁死",
                  # 「撞车前按钮是开的」这一条不能当判据：它取的是上一段入库之后的瞬时态，
                  # 早一拍晚一拍都不一样（2026-11-02 同码两轮，一轮开一轮关）。锁的因果由
                  # 下面「换成没被占用的简称：红与锁当场退掉」那一查负责——只改简称就把按钮放开了。
                  during.get("confirm") is True and during.get("approve") is True,
                  {"approve_open_before": approve_open, "state": during})
            check("撞车期间硬走底座也建不成：409 原话回显",
                  http_post(base + "/api/meta/schools", {
                      "full_name": "哈尔滨市第九中学校", "short_name": "师大附中"})[0] == 409,
                  {})
            page.screenshot(path=str(shots / "v28-school-conflict.png"))
            # 改个没被占用的简称，红与锁当场退掉 —— 老师有路可走。
            panel.locator("#epSchoolInput").fill("哈九中")
            deadline = time.time() + 20
            released = {}
            while time.time() < deadline:
                released = lock_state()
                if released.get("error_hidden") and released.get("approve") is False:
                    break
                page.wait_for_timeout(200)
            check("换成没被占用的简称：红与锁当场退掉",
                  released.get("invalid") == "false"
                  and released.get("error_hidden") is True
                  and released.get("approve") is False,
                  {"state": released})
            expect(panel.locator(
                '#epSchoolMenu [data-school-create="哈九中"]')).to_be_visible(timeout=15000)
            panel.locator("#epSchoolInput").press("Enter")
            expect(panel.locator("#epSchoolConfirm")).to_be_visible(timeout=15000)
            expect(panel.locator("#epSchoolConfirmOk")).to_be_enabled(timeout=15000)
            expect(panel.locator("#epSchoolFullName")).to_have_value(
                "哈尔滨市第九中学校", timeout=15000)
            before_ok = panel.locator("#epRoot").evaluate(
                """() => {
                    var panel = window.__jzoEditorV2.panel || {};
                    var full = document.getElementById('epSchoolFullName');
                    var input = document.getElementById('epSchoolInput');
                    return {
                        pending: JSON.stringify(panel.schoolPending || null),
                        full_value: full ? full.value : '',
                        input_value: input ? input.value : ''
                    };
                }""")
            panel.locator("#epSchoolConfirmOk").click()
            deadline = time.time() + 15
            school_chips = 0
            while time.time() < deadline:
                school_chips = panel.locator("#epSchoolList .ep-school").count()
                if school_chips >= 2:
                    break
                page.wait_for_timeout(200)
            check("换个没被占用的简称，确认后正常建档",
                  school_chips == 2
                  and "哈九中" in panel.locator("#epSchoolList").inner_text(),
                  {"count": school_chips,
                   "chips": panel.locator("#epSchoolList").inner_text(),
                   "error": panel.locator("#epSchoolError").inner_text(),
                   "before_ok": before_ok,
                   "writes": result["write_calls"][:8],
                   "panel_schools": panel.locator("#epRoot").evaluate(
                       "() => JSON.stringify((window.__jzoEditorV2.panel || {}).schools || [])")})
            # 元数据同步是异步的：等回执落地再点，别在半路把胶囊列表换成旧快照。
            page.wait_for_timeout(1200)
            panel.locator('#epSchoolList .ep-school:has-text("哈九中") .ep-school-x').click()
            page.wait_for_timeout(300)
            check("胶囊上的 × 能把学校从这一批里去掉",
                  panel.locator("#epSchoolList .ep-school").count() == 1,
                  {"chips": panel.locator("#epSchoolList .ep-school").count()})

            deadline = time.time() + 15
            std_value = ""
            while time.time() < deadline:
                std_value = panel.locator("#epStdName").input_value()
                if std_value == expected_name:
                    break
                page.wait_for_timeout(200)
            check("公共标准名如实拼出（题级原卷名镜像已随瘦身令下线）",
                  std_value == expected_name, {"std": std_value})
            leftover = panel.locator("#epPaper, #epYear, #epExamType, #epGrade, #epTopicTree").count()
            check("辅助栏不重抄来源：原卷名/年份/类型/年级与大纲树都已退场",
                  leftover == 0, {"leftover": leftover})

            # ---------- UI 极致瘦身令收尾：年级回到批次公共元数据 ----------
            # 用「高三」而不是题级 fixture 里的「高一」：撞值的同步会假绿，差值才是证据。
            panel.locator("#epMetaGrade").fill("高三")
            page.wait_for_timeout(700)
            deadline = time.time() + 20
            grade_items: list = []
            card_grade = ""
            while time.time() < deadline:
                grade_items = pending_items(base, batch_id)
                card_grade = str(next((
                    dict(each.get("meta") or {}).get("grade") for each in pending_cards(base)
                    if str(each.get("batch_id") or "") == batch_id
                ), "") or "")
                if card_grade == "高三" and grade_items and all(
                        str((each.get("question") or {}).get("grade") or "") == "高三"
                        for each in grade_items):
                    break
                page.wait_for_timeout(300)
            check("批次一填年级，这一批的题全部按契约根字段 grade 跟上",
                  card_grade == "高三" and bool(grade_items)
                  and all(str((each.get("question") or {}).get("grade") or "") == "高三"
                          for each in grade_items),
                  {"card_grade": card_grade,
                   "input": panel.locator("#epMetaGrade").input_value(),
                   "items": [str((each.get("question") or {}).get("grade") or "")
                             for each in grade_items]})
            check("年级不进标准名口径：仍按年份-地区-主体-场景-类型-学科拼",
                  panel.locator("#epStdName").input_value() == expected_name,
                  {"std": panel.locator("#epStdName").input_value()})

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
            # 每题只读条右侧多了一颗【AI识题】（终极军令任务三），
            # 它和跳转/切图一样是逐题控件，不是横条上的批量钮。
            check("画布没有底部横条，钮只有逐题跳转、切图、每题 AI 识别与添加配图",
                  canvas.locator(".ed-foot").count() == 0
                  and canvas.locator("#edCols button").count()
                  == canvas.locator(".ed-img-jump").count()
                  + canvas.locator(".ed-img-crop-btn").count()
                  + canvas.locator(".ed-q-meta-ai").count()
                  + canvas.locator("#edAddIllustration").count()
                  # 任务三每题两颗（识别本题 + 解析本题）。
                  and canvas.locator(".ed-q-meta-ai").count() == pending_count * 2
                  and canvas.locator("#edBatchBar, #edBackList").count() == 0,
                  {"col_buttons": canvas.locator("#edCols button").count(),
                   "jumps": canvas.locator(".ed-img-jump").count(),
                   "crops": canvas.locator(".ed-img-crop-btn").count(),
                   "ai": canvas.locator(".ed-q-meta-ai").count(),
                   "illustration": canvas.locator("#edAddIllustration").count(),
                   "bar": canvas.locator("#edBatchBar, #edBackList").count(),
                   "foot": canvas.locator(".ed-foot").count()})

            # ---------- 终极军令任务一/三：配置中心 + 单题/批量 AI 识别 ----------
            # 带题图的专用批：识别得真走一遍「取图 → 指派模型 → 套环境 → 换源」。
            ai_png = make_png(64, 48)
            (data_dir / "uploads").mkdir(parents=True, exist_ok=True)
            (data_dir / "uploads" / "img_ai_probe.png").write_bytes(ai_png)
            ai_question = {
                "schema_version": "2.0", "type": "solution",
                "stem": "探针 AI 原题：求 $x+1=2$ 的解。", "difficulty": "L1",
                "images": [{"id": "img_ai_probe", "role": "stem",
                            "uri": "/static/uploads/img_ai_probe.png"}],
            }
            ai_item = {
                "question": ai_question,
                "assets": [{"id": "img_ai_probe",
                            "data_url": "data:image/png;base64,"
                                        + base64.b64encode(ai_png).decode()}],
            }
            status_ai, ai_body = http_post(base + "/api/pending/batches", {
                "questions": [ai_item, ai_item],
                "origin": "probe.ai_copilot",
            })
            ai_batch = str(ai_body.get("batch_id") or "")
            check("AI 探针批（两道带题图）已入池", status_ai == 201 and bool(ai_batch),
                  {"status": status_ai, "batch": ai_batch})
            canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.refreshBatches()")
            page.wait_for_timeout(600)
            open_batch(ai_batch)

            panel.locator("#epAiConfig").click()
            expect(canvas.locator("#epAiConfigModal")).to_be_visible(timeout=10000)
            columns = canvas.locator("#epAiConfigModal .ep-ai-cols").evaluate(
                "n => getComputedStyle(n).gridTemplateColumns")
            check("辅助栏【API 配置】把双栏窗开在画布",
                  len(columns.split()) == 2
                  and canvas.locator("#epAiConfigModal .ep-ai-col").count() == 2,
                  {"columns": columns})
            modal_box = canvas.locator("#epAiConfigModal .ep-ai-card").bounding_box() or {}
            scrolls = canvas.locator("#epAiConfigModal .ep-ai-card").evaluate(
                "n => ({pool: getComputedStyle(n.querySelector('.ep-ai-pool')).overflowY,"
                " assign: getComputedStyle(n.querySelector('.ep-ai-assign')).overflowY,"
                " client: n.clientHeight, scroll: n.scrollHeight,"
                " poolScroll: n.querySelector('.ep-ai-pool').scrollHeight"
                " - n.querySelector('.ep-ai-pool').clientHeight,"
                " assignScroll: n.querySelector('.ep-ai-assign').scrollHeight"
                " - n.querySelector('.ep-ai-assign').clientHeight})")
            form_hidden = canvas.locator("#epAiAccountForm").is_hidden()
            check("弹窗放大到 900px 宽，左右内层都不滚，新增表单默认收起",
                  modal_box.get("width", 0) >= 850
                  and scrolls["pool"] == "visible" and scrolls["assign"] == "visible"
                  and form_hidden,
                  {"width": modal_box.get("width"), "overflow": scrolls,
                   "form_hidden": form_hidden})
            canvas.locator("#epAiNewAccount").click()
            expect(canvas.locator("#epAiAccountForm")).to_be_visible(timeout=5000)
            canvas.locator("#epAiName").fill("探针AI")
            canvas.locator("#epAiBase").fill(stub.base_url)
            canvas.locator("#epAiKey").fill("sk-probe-secret-1234")
            page.screenshot(path=str(shots / "ai-config-form.png"))
            canvas.locator("#epAiSaveAccount").click()
            pool_row = canvas.locator(".ep-ai-acc").first
            expect(pool_row.locator(".ep-ai-acc-name")).to_have_text("探针AI", timeout=20000)
            expect(canvas.locator("#epAiAccountForm")).to_be_hidden(timeout=20000)
            check("保存成功后表单自动清空并收起",
                  canvas.locator("#epAiName").input_value() == ""
                  and canvas.locator("#epAiKey").input_value() == "",
                  {"name": canvas.locator("#epAiName").input_value()})
            test_icon = pool_row.locator(".ep-ai-test")
            expect(test_icon).to_have_attribute("data-state", "ok", timeout=20000)
            modal_text = canvas.locator("#epAiConfigModal").inner_text()
            check("密钥池单行只留名称，Base URL 与 Key 不上屏",
                  pool_row.locator(".ep-ai-acc-meta, .ep-ai-acc-key").count() == 0
                  and "127.0.0.1" not in modal_text and "sk-p" not in modal_text
                  and "probe-secret" not in modal_text
                  and canvas.locator("#epAiKey").input_value() == "",
                  {"row": pool_row.inner_text(), "modal": modal_text[:160]})
            check("操作收成三个图标钮，靠右贴行末",
                  pool_row.locator("button.ep-icon-btn").count() == 3,
                  {"buttons": pool_row.locator("button.ep-icon-btn").count()})
            check("保存后当场验证连通：原地绿勾 + 连接正常悬停",
                  test_icon.get_attribute("title") == "连接正常"
                  and test_icon.inner_text() == "✅",
                  {"state": test_icon.get_attribute("data-state"),
                   "title": test_icon.get_attribute("title")})
            test_icon.click()
            expect(test_icon).to_have_attribute("data-state", "ok", timeout=20000)

            ocr_task = canvas.locator('.ep-ai-task[data-task="ocr"]')
            ocr_task.locator("select").select_option(label="探针AI")
            ocr_task.locator("input").fill("probe-stub")
            ocr_task.locator("button.ep-btn-primary").click()
            expect(ocr_task.locator(".ep-ai-job-ready")).to_have_text("已就绪", timeout=20000)
            check("四个任务可指派，模型名手输也留得住",
                  canvas.locator(".ep-ai-task").count() == 4
                  and ocr_task.locator("input").input_value() == "probe-stub",
                  {"tasks": canvas.locator(".ep-ai-task").count()})
            fit = canvas.locator("#epAiConfigModal .ep-ai-card").evaluate(
                "n => ({client: n.clientHeight, scroll: n.scrollHeight,"
                " pool: [n.querySelector('.ep-ai-pool').clientHeight,"
                " n.querySelector('.ep-ai-pool').scrollHeight],"
                " assign: [n.querySelector('.ep-ai-assign').clientHeight,"
                " n.querySelector('.ep-ai-assign').scrollHeight]})")
            # 密钥池不量 scrollHeight：图标钮的透明外扩伪元素会把它撑大几像素，
            # 但 overflow 是 visible，没有可滚动的内层。
            check("四个任务与密钥池一屏放完，弹窗内外都不需要滚动条",
                  fit["scroll"] <= fit["client"]
                  and fit["assign"][1] <= fit["assign"][0],
                  fit)
            page.screenshot(path=str(shots / "ai-config.png"))
            canvas.locator("#epAiConfigClose").click()
            expect(canvas.locator("#epAiConfigModal")).to_be_hidden(timeout=10000)

            def source_text(index: int) -> str:
                return canvas.locator(".ed-src-area").nth(index).input_value()

            def wait_source(index: int, fragment: str, timeout: float = 40) -> bool:
                deadline = time.time() + timeout
                while time.time() < deadline:
                    if fragment in source_text(index):
                        return True
                    page.wait_for_timeout(200)
                return False

            ai_reply = {}
            try:
                with page.expect_response(
                        lambda r: "/api/ai-center/recognize" in r.url, timeout=60000) as hit:
                    canvas.locator(".ed-q-meta-ai").first.click()
                ai_reply = hit.value.json()
            except Exception as error:  # noqa: BLE001 - 失败现场要原样进判据
                ai_reply = {"probe_error": f"{type(error).__name__}: {error}"}
            check("单题 AI 识别：底座套好环境后整题换源，不弹窗",
                  wait_source(0, "探针AI改写", timeout=20)
                  and not canvas.locator("#epAiOverwriteModal").is_visible()
                  and canvas.locator(".ed-q-meta-ai").first.get_attribute("data-error") is None,
                  {"source": source_text(0)[:120], "reply": ai_reply})
            page.screenshot(path=str(shots / "ai-single.png"))

            batch_replies: list = []

            def collect_ai_reply(response) -> None:
                if "/api/ai-center/recognize" not in response.url:
                    return
                try:
                    batch_replies.append(response.json())
                except Exception:  # noqa: BLE001 - 非 JSON 回执原样跳过，不打断采集
                    pass

            page.on("response", collect_ai_reply)
            panel.locator("#epAiBatch").click()
            batch_note = ""
            deadline = time.time() + 180
            while time.time() < deadline:
                batch_note = panel.locator("#epAiBatchNote").inner_text()
                if "批量识别完成" in batch_note:
                    break
                page.wait_for_timeout(300)
            check("批量 AI 识别全卷：进度与结果回到辅助栏，全程不弹窗",
                  "批量识别完成" in batch_note and "失败 0" in batch_note
                  and not canvas.locator("#epAiOverwriteModal").is_visible(),
                  {"note": batch_note, "replies": batch_replies[:3]})
            page.screenshot(path=str(shots / "ai-batch.png"))

            canvas.locator(".ed-src-area").first.fill(source_text(0) + "\n% 人工改动")
            page.wait_for_timeout(300)
            canvas.locator(".ed-q-meta-ai").first.click()
            expect(canvas.locator("#epAiOverwriteModal")).to_be_visible(timeout=10000)
            page.screenshot(path=str(shots / "ai-overwrite.png"))
            canvas.locator("#epAiOverwriteCancel").click()
            expect(canvas.locator("#epAiOverwriteModal")).to_be_hidden(timeout=10000)
            check("有人工修改先弹确认；取消不动正文",
                  "% 人工改动" in source_text(0))
            canvas.locator(".ed-q-meta-ai").first.click()
            expect(canvas.locator("#epAiOverwriteModal")).to_be_visible(timeout=10000)
            canvas.locator("#epAiOverwriteOk").click()
            # 覆盖要等往返回来：fill 里本来就有「探针AI改写」，不能当成立刻换源成功。
            overwrite_deadline = time.time() + 30
            while time.time() < overwrite_deadline and "% 人工改动" in source_text(0):
                page.wait_for_timeout(200)
            check("确认覆盖后正文换成 AI 结果",
                  "% 人工改动" not in source_text(0)
                  and wait_source(0, "探针AI改写"),
                  {"source": source_text(0)[:120]})

            # 回到探针的主批次：后面的元数据/入库判据都按那一批的账来对。
            open_batch(batch_id)

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
            # 题图是异步加载的：图没长完就量，对齐还停在旧高度，逐行虚线必然差一截。
            img_deadline = time.time() + 15
            while time.time() < img_deadline:
                ready = canvas.locator("#edImageBody").evaluate(
                    "node => Array.prototype.every.call("
                    "node.querySelectorAll('img'), img => img.complete)")
                if ready:
                    break
                page.wait_for_timeout(200)
            page.wait_for_timeout(300)
            lines = row_lines()
            check("三栏虚线逐行落在同一条线上", dashed_ok(lines), {"rows": lines[:3]})
            page.screenshot(path=str(shots / "v3-review.png"))

            # ---------- 右栏辅助面板 ----------
            check("辅助栏不放源码框", panel.locator(".ed-src-area, .ed-box-area").count() == 0,
                  {"src": panel.locator(".ed-src-area").count(),
                   "boxes": panel.locator(".ed-box-area").count()})
            check("辅助栏不放渲染预览", panel.locator(".ed-q-block").count() == 0)
            audit_texts = [text.strip() for text in
                           panel.locator("#epApprove, #epStash, #epDelete").all_inner_texts()]
            check("审核动作包含：单题入库 / 存为待审 / 彻底删除",
                  audit_texts == ["单题入库", "存为待审", "彻底删除"],
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
                                    ("分值", "#epScore"), ("考向胶囊", "#epMounted")):
                check(f"辅助栏里元数据表单还在（{label}）",
                      panel.locator(selector).count() == 1
                      and panel.locator(selector).is_visible(),
                      {"selector": selector})
            fmt_boxes = [panel.locator(sel).bounding_box() for sel in
                         ("#epBackList", "#epFmtLatex", "#epFmtBoxed", "#epSwap")]
            one_row = all(box is not None for box in fmt_boxes) and (
                max(box["y"] for box in fmt_boxes) - min(box["y"] for box in fmt_boxes) < 8)
            check("返回列表/源码/卡片/布局同一行", one_row
                  and panel.locator("#epHead #epBackList").count() == 1
                  and panel.locator("#epHead #epFmtLatex").count() == 1,
                  {"boxes": fmt_boxes})
            dock_box = panel.locator("#epDock").bounding_box()
            root_box = panel.locator("#epRoot").bounding_box()
            check("台账钉在辅助栏最底边",
                  dock_box is not None and root_box is not None
                  and 0 <= root_box["y"] + root_box["height"]
                  - (dock_box["y"] + dock_box["height"]) <= 4,
                  {"root": root_box, "dock": dock_box})
            page.screenshot(path=str(shots / "v3-panel.png"))

            # ---------- 军令 #29：辅助栏三段式 + 双侧呼吸灯 + 幽灵胶囊 ----------
            head_box = panel.locator("#epHead").bounding_box()
            mid_box = panel.locator("#epScroll").bounding_box()
            foot_box = panel.locator("#epDock").bounding_box()
            root_box = panel.locator("#epRoot").bounding_box()
            check("辅助栏排成三段：段一顶部 · 段二中部 · 段三底部",
                  None not in (head_box, mid_box, foot_box)
                  and head_box["y"] + head_box["height"] <= mid_box["y"] + 1
                  and mid_box["y"] + mid_box["height"] <= foot_box["y"] + 1,
                  {"head": head_box, "mid": mid_box, "foot": foot_box})
            check("段一钉在顶边、段三钉在底边（只有中段会滚）",
                  root_box is not None and head_box is not None and foot_box is not None
                  and abs(head_box["y"] - root_box["y"]) <= 2
                  and 0 <= root_box["y"] + root_box["height"]
                  - (foot_box["y"] + foot_box["height"]) <= 4,
                  {"root": root_box, "head": head_box, "foot": foot_box})
            check("段一只装单题私有元数据：题号 · 题型 · 分值 · 难度 · 考向 · 标签",
                  panel.locator("#epHead").locator(
                      "#epQuestionNo, #epType, #epScore, #epDifficulty").count() == 4
                  and panel.locator("#epHead #epMounted").count() == 1
                  and panel.locator("#epHead #epTagList").count() == 1
                  and panel.locator("#epScroll #epMetaSec").count() == 1
                  and panel.locator("#epScroll #epMetaYear").count() == 1,
                  {"private": panel.locator("#epHead").locator(
                      "#epQuestionNo, #epType, #epScore, #epDifficulty").count()})
            # 终极军令任务三：私有元数据就三行——1 行四控件，2 行考向，3 行标签。
            head_boxes = [panel.locator(sel).bounding_box()
                          for sel in ("#epQuestionNo", "#epType", "#epScore", "#epDifficulty")]
            head_order = sorted(range(4), key=lambda i: (head_boxes[i]["y"], head_boxes[i]["x"]))
            topic_box = panel.locator("#epMounted").bounding_box()
            tag_box = panel.locator("#epTagList").bounding_box()
            check("第 1 行的次序就是 题号 | 题型 | 分值 | 难度（窄栏折行也不许乱序）",
                  head_order == [0, 1, 2, 3],
                  {"order": head_order,
                   "boxes": [{"y": round(b["y"]), "x": round(b["x"])} for b in head_boxes]})
            check("第 2 行考向、第 3 行标签：都在四控件之下，考向先于标签",
                  topic_box["y"] > max(b["y"] for b in head_boxes)
                  and tag_box["y"] > topic_box["y"],
                  {"topic_y": round(topic_box["y"]), "tag_y": round(tag_box["y"]),
                   "grid_max_y": round(max(b["y"] for b in head_boxes))})
            check("AI 帮改默认展开（军令#32·P0「默认不是收起的」）：启动即 open，指令框与预览都在场",
                  panel.locator("#epAiSec").get_attribute("data-fold") == "open"
                  and panel.locator("#epAiFold").get_attribute("aria-expanded") == "true"
                  and panel.locator("#epAiAsk").is_visible()
                  and panel.locator("#epAiPreview").is_visible(),
                  {"fold": panel.locator("#epAiSec").get_attribute("data-fold"),
                   "expanded": panel.locator("#epAiFold").get_attribute("aria-expanded")})
            panel.locator("#epAiFold").click()
            page.wait_for_timeout(200)
            check("点一下手动收起：closed／aria-expanded=false，指令框与预览都不占位",
                  panel.locator("#epAiSec").get_attribute("data-fold") == "closed"
                  and panel.locator("#epAiFold").get_attribute("aria-expanded") == "false"
                  and panel.locator("#epAiAsk").is_visible() is False
                  and panel.locator("#epAiPreview").is_visible() is False,
                  {"fold": panel.locator("#epAiSec").get_attribute("data-fold"),
                   "expanded": panel.locator("#epAiFold").get_attribute("aria-expanded")})
            panel.locator("#epAiFold").click()
            page.wait_for_timeout(200)
            check("再点一下恢复展开：open／true，输入框与预览当场现身",
                  panel.locator("#epAiSec").get_attribute("data-fold") == "open"
                  and panel.locator("#epAiFold").get_attribute("aria-expanded") == "true"
                  and panel.locator("#epAiAsk").is_visible()
                  and panel.locator("#epAiPreview").is_visible(),
                  {"fold": panel.locator("#epAiSec").get_attribute("data-fold")})
            check("段一死锁区装着返回列表与视图切换",
                  panel.locator("#epHead #epBackList").count() == 1
                  and panel.locator("#epHead #epFmtLatex").count() == 1
                  and panel.locator("#epHead #epFmtBoxed").count() == 1
                  and panel.locator("#epHead #epSwap").count() == 1,
                  {})
            check("段三只装审核动作（视图切换已搬进段一）",
                  panel.locator("#epDock #epApprove").count() == 1
                  and panel.locator("#epDock #epStash").count() == 1
                  and panel.locator("#epDock #epDelete").count() == 1
                  and panel.locator("#epDock #epFmtLatex").count() == 0
                  and panel.locator("#epDock #epSwap").count() == 0,
                  {})
            wrap_mode = panel.locator("#epHead .ep-head-grid").evaluate(
                "node => getComputedStyle(node).flexWrap")
            check("辅助栏拉窄时私有字段自动折行", wrap_mode == "wrap",
                  {"flex_wrap": wrap_mode})
            foot_heights = [round(panel.locator(sel).bounding_box()["height"], 1)
                            for sel in ("#epApprove", "#epStash", "#epDelete",
                                        "#epBackList", "#epFmtLatex", "#epFmtBoxed", "#epSwap")]
            check("段三与死锁区全是极矮的一排", max(foot_heights) <= 40,
                  {"heights": foot_heights})
            check("段三压到两行以内", foot_box["height"] <= 130,
                  {"foot_height": round(foot_box["height"], 1)})
            ledger = panel.locator("#edPool").inner_text().strip()
            check("最下一行灰字报账：待入库 N · 已入库 M",
                  re.match(r"^待入库：\d+ · 已入库：\d+", ledger) is not None,
                  {"ledger": ledger})

            # ---------- 段二自动折叠：画布一滚动就收成一行矮标题 ----------
            check("批次公共元数据默认展开",
                  panel.locator("#epMetaSec").get_attribute("data-fold") == "open",
                  {"fold": panel.locator("#epMetaSec").get_attribute("data-fold")})
            # 1440×900 下这一卷的内容还没撑出滚动条：先把窗口压矮，让"滚动触发折叠"
            # 这个判据真的有一根滚动条可拉；判完立刻恢复原窗口尺寸。
            page.set_viewport_size({"width": 1440, "height": 520})
            page.wait_for_timeout(400)
            scrolled = canvas.locator("#edRoot").evaluate(
                """() => {
                    var bodies = ['#edImageBody', '#edSourceBody', '#edRenderBody'];
                    for (var i = 0; i < bodies.length; i += 1) {
                        var node = document.querySelector(bodies[i]);
                        if (!node) continue;
                        if (node.scrollHeight > node.clientHeight + 4) {
                            node.scrollTop = Math.min(60, node.scrollHeight);
                            return bodies[i];
                        }
                    }
                    return '';
                }""")
            fold_state = ""
            deadline = time.time() + 10
            while time.time() < deadline:
                fold_state = panel.locator("#epMetaSec").get_attribute("data-fold") or ""
                if fold_state == "closed":
                    break
                page.wait_for_timeout(100)
            check("画布一滚动，批次公共元数据立刻收成一行矮标题",
                  fold_state == "closed", {"fold": fold_state, "scrolled": scrolled})
            page.set_viewport_size({"width": 1440, "height": 900})
            page.wait_for_timeout(300)
            check("辅助栏不留虚线接收框（收件只有画布的收集筐）",
                  panel.locator("#epIntake").count() == 0,
                  {"intake": panel.locator("#epIntake").count()})
            std_now = panel.locator("#epStdName").input_value()
            fold_summary = panel.locator("#epMetaSummary").inner_text().strip()
            check("收起后那行矮标题报着标准名",
                  fold_summary == std_now and bool(std_now),
                  {"summary": fold_summary, "std": std_now})
            page.screenshot(path=str(shots / "v29-fold.png"))
            panel.locator("#epMetaFold").hover()
            page.wait_for_timeout(400)
            check("鼠标悬停在矮标题上：批次公共元数据展开",
                  panel.locator("#epMetaSec").get_attribute("data-fold") == "open",
                  {"fold": panel.locator("#epMetaSec").get_attribute("data-fold")})
            panel.locator("#epMessage").hover()
            page.wait_for_timeout(600)
            check("鼠标移开也不收起（老师正在填的字段不许被抢走）",
                  panel.locator("#epMetaSec").get_attribute("data-fold") == "open",
                  {"fold": panel.locator("#epMetaSec").get_attribute("data-fold")})

            # ---------- 双侧呼吸灯：画布悬停 200ms，两边同时亮 ----------
            row0 = canvas.locator('.ed-img-cell[data-index="0"]')
            expect(row0).to_be_visible(timeout=10000)
            row0.hover()
            page.wait_for_timeout(700)
            lamp_cells = canvas.locator('#edRoot [data-lamp="on"]').count()
            check("画布悬停超过 200ms：该题在三栏里同时亮起呼吸灯",
                  lamp_cells >= 3
                  and canvas.locator('.ed-img-cell[data-index="0"]').get_attribute("data-lamp") == "on"
                  and canvas.locator('.ed-src-cell[data-index="0"]').get_attribute("data-lamp") == "on"
                  and canvas.locator('.ed-q-block[data-index="0"]').get_attribute("data-lamp") == "on",
                  {"lit": lamp_cells})
            lamp_anim = canvas.locator('.ed-img-cell[data-index="0"]').evaluate(
                """node => {
                    var style = getComputedStyle(node, '::after');
                    return {name: style.animationName, duration: style.animationDuration};
                }""")
            check("呼吸灯是真在呼吸：2 秒一轮的透明度动画",
                  lamp_anim["name"] == "ep-lamp-breathe"
                  and lamp_anim["duration"] == "2s",
                  lamp_anim)
            check("辅助栏边缘跟着一起亮（同一道题）",
                  panel.locator('#epRoot[data-lamp="on"]').count() == 1
                  and panel.locator("#epRoot").get_attribute("data-hover") == "0",
                  {"hover": panel.locator("#epRoot").get_attribute("data-hover")})
            panel_lamp_anim = panel.locator("#epRoot").evaluate(
                """node => {
                    var style = getComputedStyle(node, '::after');
                    return {name: style.animationName, duration: style.animationDuration};
                }""")
            check("辅助栏那圈灯也在呼吸",
                  panel_lamp_anim["name"] == "ep-lamp-breathe"
                  and panel_lamp_anim["duration"] == "2s",
                  panel_lamp_anim)
            page.screenshot(path=str(shots / "v29-lamp.png"))
            panel.locator("#epMessage").hover()
            page.wait_for_timeout(700)
            check("鼠标移开：两边的灯同时熄灭",
                  canvas.locator('#edRoot [data-lamp="on"]').count() == 0
                  and panel.locator('#epRoot[data-lamp="on"]').count() == 0,
                  {"canvas": canvas.locator('#edRoot [data-lamp="on"]').count(),
                   "panel": panel.locator('#epRoot[data-lamp="on"]').count()})

            # ---------- 幽灵胶囊：悬停 150ms 自动聚焦，打字出候选，回车取第一条 ----------
            panel.locator("#epTagList").hover()
            tag_ghost = panel.locator("#epTagList .ep-ghost")
            expect(tag_ghost).to_be_visible(timeout=10000)
            ghost_text = tag_ghost.text_content().strip()
            check("标签串尾巴挂着一颗虚线空壳「+ 请添加…」",
                  ghost_text.startswith("+ 请添加"), {"text": ghost_text})
            tag_ghost.hover()
            page.wait_for_timeout(500)
            ghost_state = tag_ghost.get_attribute("data-state")
            ghost_focus = panel.locator("#epTagList").evaluate(
                """host => {
                    var input = host.querySelector('.ep-ghost-input');
                    return !!(input && document.activeElement === input);
                }""")
            check("悬停 150ms 空壳自己活过来并接上光标（不用点）",
                  ghost_state == "active" and ghost_focus,
                  {"state": ghost_state, "focused": ghost_focus})
            chips_before = panel.locator("#epTagList .ep-chip").count()
            panel.locator("#epTagList .ep-ghost-input").fill("百日")
            page.wait_for_timeout(800)
            menu_names = [text.strip() for text in
                          panel.locator("#epGhostTagMenu .ep-menu-text").all_inner_texts()]
            check("打字弹出候选菜单", len(menu_names) >= 1, {"menu": menu_names})
            panel.locator("#epTagList .ep-ghost-input").press("Enter")
            page.wait_for_timeout(600)
            chips_after = panel.locator("#epTagList .ep-chip").count()
            chip_names = [text.strip() for text in
                          panel.locator("#epTagList .ep-chip-name").all_inner_texts()]
            check("回车默认取第一条上屏",
                  chips_after == chips_before + 1
                  and bool(menu_names) and chip_names and chip_names[-1] == menu_names[0],
                  {"before": chips_before, "after": chips_after,
                   "chips": chip_names, "menu": menu_names})
            next_ghost = panel.locator("#epTagList .ep-ghost")
            check("取完一颗，下一颗空壳立刻接上",
                  next_ghost.get_attribute("data-state") == "active"
                  and panel.locator("#epTagList .ep-ghost-input").input_value() == "",
                  {"state": next_ghost.get_attribute("data-state")})
            page.screenshot(path=str(shots / "v29-ghost-tag.png"))

            panel.locator("#epMounted").hover()
            topic_ghost = panel.locator("#epMounted .ep-ghost")
            expect(topic_ghost).to_be_visible(timeout=10000)
            topic_ghost.hover()
            page.wait_for_timeout(500)
            topic_focus = panel.locator("#epMounted").evaluate(
                """host => {
                    var input = host.querySelector('.ep-ghost-input');
                    return !!(input && document.activeElement === input);
                }""")
            check("考向串尾巴也有一颗幽灵空壳，悬停 150ms 同样接上光标",
                  topic_ghost.get_attribute("data-state") == "active" and topic_focus,
                  {"state": topic_ghost.get_attribute("data-state"),
                   "focused": topic_focus})
            panel.locator("#epMounted .ep-ghost-input").fill("函数")
            page.wait_for_timeout(1200)
            topic_names = [text.strip() for text in
                           panel.locator("#epGhostTopicMenu .ep-menu-text").all_inner_texts()]
            topic_paths = [text.strip() for text in
                           panel.locator("#epGhostTopicMenu .ep-menu-path").all_inner_texts()]
            check("考向候选带着路径（册 › 章 › 节 › 考向）",
                  len(topic_names) >= 1 and any("›" in path for path in topic_paths),
                  {"names": topic_names, "paths": topic_paths})
            panel.locator("#epMounted .ep-ghost-input").fill("hs")
            page.wait_for_timeout(1200)
            initials_names = [text.strip() for text in
                              panel.locator("#epGhostTopicMenu .ep-menu-text").all_inner_texts()]
            check("考向也认拼音首字母：敲 hs 捞出带「函数」的考向",
                  any("函数" in name for name in initials_names),
                  {"names": initials_names[:8]})
            panel.locator("#epMounted .ep-ghost-input").fill("函数")
            page.wait_for_timeout(1000)
            topic_names = [text.strip() for text in
                           panel.locator("#epGhostTopicMenu .ep-menu-text").all_inner_texts()]
            if topic_names:
                panel.locator("#epMounted .ep-ghost-input").press("Enter")
                page.wait_for_timeout(600)
                mounted_names = [text.strip() for text in
                                 panel.locator("#epMounted .ep-chip-name").all_inner_texts()]
                check("回车把考向挂上这一题",
                      topic_names[0] in mounted_names,
                      {"mounted": mounted_names, "first": topic_names[0]})
            page.screenshot(path=str(shots / "v29-ghost-topic.png"))

            # ---------- 存为待审：改过的题原地写回中转池 ----------
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
            check("【存为待审】给出回执", wait_message("已存为待审"),
                  {"messages": [m.get("text", "") for m in probe_messages()][-4:]})
            pool_after = pending_items(base, batch_id)
            check("存为待审是原地更新：池子里不多出一道重影",
                  len(pool_after) == len(pool_before),
                  {"before": len(pool_before), "after": len(pool_after)})
            check("改过的内容真的落进中转池",
                  any(MARK in str(item.get("question", {}).get("stem", ""))
                      for item in pool_after),
                  {"stems": [str(item.get("question", {}).get("stem", ""))[:40]
                             for item in pool_after][:3]})
            page.screenshot(path=str(shots / "v3-stash.png"))

            # ---------- 单题入库：p_ 号段换成 q_ 号段 ----------
            dock_mark = len(dock_entries())
            total_pre_approve = bank_total(base)
            panel.locator("#epApprove").click()
            approve_line = wait_dock(lambda e: "已存入主库" in e.get("text", ""), 30, dock_mark)
            check("【单题入库】给出回执", wait_message("已存入主库"),
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
            is_choice = str(seed_doc.get("type") or "") in choice_types
            if is_choice:
                keys = list(doc_answer.get("choice_keys") or [])
                answer_ok = keys == list(seed_answer.get("choice_keys") or [])
                # 库内选择题答案存成「A,B」，源码里写的是「AB」——两种写法都认。
                literal_ok = ("".join(keys) in edited_source
                              or ",".join(keys) in edited_source)
            else:
                answer_ok = str(doc_answer.get("final") or "").strip() == str(
                    seed_answer.get("final") or "").strip()
                literal_ok = str(doc_answer.get("final") or "") in edited_source
            check("题型/答案按源码还原",
                  str(document.get("type") or "") == str(seed_doc.get("type") or "")
                  and answer_ok
                  and literal_ok,
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
            done_aria = done_row.locator(".ed-batch-open").get_attribute("aria-label") or ""
            done_terms = ledger_terms(LEDGER_RE.search(done_aria))
            done_count = CARD_COUNT_RE.search(done_row.locator(".ed-batch-right").inner_text())
            # ✅ 只在「一条没抽走」时挂（ui_batches.js:219 done && !pooled）：
            # 池里还有条数时红着的是「剔除重复」那颗钮，不许再打勾冒充审干净了。
            check("审完的卡片写着「待审 0 / N」，四段账在 aria-label 里对平，✅ 只在没有池内条时出现",
                  bool(done_terms) and done_terms["pending"] == 0 and done_terms["balanced"]
                  and bool(done_count) and int(done_count.group("pending")) == 0
                  and ("✅" in done_text) == (done_terms["pooled"] == 0),
                  {"text": done_text, "aria": done_aria})
            # 行是 div（一颗按钮旁边还要挂「剔除重复」），禁用态挂在题面按钮上，
            # data-done 挂在行上——判据跟着分两处锚，别指望 div 会认 disabled。
            done_open = done_row.locator(".ed-batch-open")
            check("审完的卡片点不动",
                  done_open.is_disabled()
                  and done_open.get_attribute("aria-disabled") == "true"
                  and done_row.get_attribute("data-done") == "true",
                  {"disabled": done_open.is_disabled(),
                   "aria": done_open.get_attribute("aria-disabled"),
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
                  bool(order) and order[-1][0] == batch_id
                  and flags[first_done:] == ["true"] * len(flags[first_done:]),
                  {"order": order})
            page.screenshot(path=str(shots / "v3-done.png"))
            done_box = done_row.bounding_box()
            page.mouse.click(done_box["x"] + 4, done_box["y"] + done_box["height"] / 2)
            page.wait_for_timeout(500)
            check("点不动的批次进不去审核",
                  canvas.locator("#edRoot").get_attribute("data-mode") == "list"
                  and canvas.locator("#edCols").is_hidden(),
                  {"mode": canvas.locator("#edRoot").get_attribute("data-mode")})

            # ---------- 查重拦截（军令 #31）：红呼吸灯 + 渲染对比 + 三个裁决 ----------
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

            # 入库前后台查重：命中就亮红字、点红灯、开左右渲染对比，**绝不直接写库**。
            panel.locator("#epApprove").click()
            expect(panel.locator("#epDupBox")).to_be_visible(timeout=25000)
            check("命中后辅助栏红字逐字是「主库已存在高度相似题目」",
                  panel.locator("#epDupWarn").inner_text().strip().startswith("主库已存在高度相似题目"),
                  {"text": panel.locator("#epDupWarn").inner_text()})
            # 浮层经宿主投递到画布那帧，是异步的：先等它出来，再断言灯与内容。
            expect(canvas.locator("#edDupModal")).to_be_visible(timeout=25000)
            expect(canvas.locator("#edRoot")).to_have_attribute("data-dup", "on", timeout=10000)
            check("左侧画布亮起红呼吸灯（data-dup=on）",
                  canvas.locator("#edRoot").get_attribute("data-dup") == "on",
                  {"dup": canvas.locator("#edRoot").get_attribute("data-dup")})
            check("对比浮层左右两侧都渲染出了选项（比渲染，不比源码）",
                  canvas.locator("#edDupMineBody .ed-dup-option").count() >= 2
                  and canvas.locator("#edDupTheirBody .ed-dup-option").count() >= 2,
                  {"mine": canvas.locator("#edDupMineBody .ed-dup-option").count(),
                   "theirs": canvas.locator("#edDupTheirBody .ed-dup-option").count()})
            check("两侧都带答案行，且画布里一颗按钮都没有",
                  canvas.locator("#edDupMineBody .ed-dup-answer").count() == 1
                  and canvas.locator("#edDupTheirBody .ed-dup-answer").count() == 1
                  and canvas.locator("#edDupModal button").count() == 0,
                  {"buttons": canvas.locator("#edDupModal button").count()})
            check("三个裁决动作都住在辅助栏",
                  panel.locator("#epDupOverwrite").inner_text().strip() == "覆盖"
                  and panel.locator("#epDupMerge").inner_text().strip() == "合并为解析二"
                  and panel.locator("#epDupAbandon").inner_text().strip() == "放弃"
                  and panel.locator("#epDupInspect").inner_text().strip() == "查看主库原题",
                  {"overwrite": panel.locator("#epDupOverwrite").inner_text(),
                   "merge": panel.locator("#epDupMerge").inner_text(),
                   "abandon": panel.locator("#epDupAbandon").inner_text()})
            page.screenshot(path=str(shots / "v3-dup.png"))

            # 【查看主库原题】关了再开一次：浮层由辅助栏那帧投过来，不是画布自己找的。
            panel.locator("#epDupInspect").click()
            expect(canvas.locator("#edDupModal")).to_be_visible(timeout=10000)

            # 【放弃】：主库一个字节都不碰，题留在池子里。
            panel.locator("#epDupAbandon").click()
            expect(panel.locator("#epDupBox")).to_be_hidden(timeout=10000)
            expect(canvas.locator("#edDupModal")).to_be_hidden(timeout=10000)
            check("点【放弃】：红字与红灯都熄了，题还留在中转池里",
                  canvas.locator("#edRoot").get_attribute("data-dup") is None
                  and len(pending_items(base, dup_batch)) == 1,
                  {"items": len(pending_items(base, dup_batch))})

            # 【覆盖】：以池子里这条为准盖掉主库那一条，题目 id 不变、题数不增。
            total_before_force = bank_total(base)
            panel.locator("#epApprove").click()
            expect(panel.locator("#epDupOverwrite")).to_be_visible(timeout=25000)
            panel.locator("#epDupOverwrite").click()
            deadline = time.time() + 30
            while time.time() < deadline and pending_items(base, dup_batch):
                page.wait_for_timeout(200)
            check("【覆盖】把主库那道题盖掉，题数不增、池子清空",
                  bank_total(base) == total_before_force
                  and not pending_items(base, dup_batch)
                  and canvas.locator("#edRoot").get_attribute("data-dup") is None,
                  {"before": total_before_force, "after": bank_total(base),
                   "items": len(pending_items(base, dup_batch))})

            # 【合并为解析二】：主库那题留着，只把池子里这条的解析并进去。
            merge_doc = json.loads(json.dumps(dup_doc))
            merge_doc["solution"] = "探针解法二：把 $x$ 直接代回原式即可。"
            status_m, merge_body = http_post(
                base + "/api/pending/batches",
                {"questions": [{"question": merge_doc}], "origin": "probe.recognize"})
            merge_batch = str(merge_body.get("batch_id") or "")
            canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.refreshBatches()")
            page.wait_for_timeout(400)
            open_batch(merge_batch)
            synced_merge = sync_panel()
            total_before_merge = bank_total(base)
            panel.locator("#epApprove").click()
            # 查重没出裁决前这颗钮是锁死的：钮在裁决回来前就「enabled」，
            # 只等 enabled 会抢在「正在查重…」时点下去，动作被吞。先等裁决框真露出来。
            expect(panel.locator("#epDupBox")).to_be_visible(timeout=25000)
            expect(panel.locator("#epDupMerge")).to_be_visible(timeout=25000)
            expect(panel.locator("#epDupMerge")).to_be_enabled(timeout=10000)
            # 点下去之前先核对"辅助栏现在这道题，就是池子里那一条"：
            # 合并这条动作全靠 pending_id 对上，选区慢半拍会把请求吞掉，
            # 界面不报错、池子不动，判据只剩一条"解析没变"——看不出是哪儿没接上。
            sel_merge = panel_pending_id()
            pool_merge = [str(i.get("id") or "") for i in pending_items(base, merge_batch)]
            check("【合并】点之前辅助栏选中的就是池子里那一条",
                  bool(sel_merge) and sel_merge in pool_merge and bool(synced_merge),
                  {"selection": sel_merge, "pool": pool_merge[:3],
                   "synced": synced_merge})
            panel.locator("#epDupMerge").click()
            deadline = time.time() + 30
            while time.time() < deadline and pending_items(base, merge_batch):
                page.wait_for_timeout(200)
            status_after, merged_doc = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}")
            merged_solution = str((merged_doc or {}).get("solution") or "")
            check("【合并为解析二】把池子里那段并成解法二，主库题数不增",
                  bank_total(base) == total_before_merge
                  and not pending_items(base, merge_batch)
                  and "解法二" in merged_solution
                  and "探针解法二" in merged_solution,
                  {"before": total_before_merge, "after": bank_total(base),
                   "solution": merged_solution[:120],
                   "selection": sel_merge, "pool": pool_merge[:3],
                   "synced": synced_merge,
                   "panel_said": [m.get("text") for m in probe_messages()][-4:]})

            # 答案不同 → 红字拦截：覆盖与合并两颗钮都锁死，只留放弃。
            original_keys = list(((dup_doc or {}).get("answer") or {}).get("choice_keys") or ["A"])
            other_key = next(k for k in ("A", "B", "C", "D") if k not in original_keys)
            clash_doc = json.loads(json.dumps(dup_doc))
            clash_doc["answer"] = {"kind": "choice", "choice_keys": [other_key], "final": other_key}
            status_c, clash_body = http_post(
                base + "/api/pending/batches",
                {"questions": [{"question": clash_doc}], "origin": "probe.recognize"})
            clash_batch = str(clash_body.get("batch_id") or "")
            canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.refreshBatches()")
            page.wait_for_timeout(400)
            open_batch(clash_batch)
            sync_panel()
            # 只切题、不点任何按钮：后台查重自己就该把红灯与红字亮起来（只点灯不开窗）。
            expect(panel.locator("#epDupBox")).to_be_visible(timeout=25000)
            expect(canvas.locator("#edRoot")).to_have_attribute("data-dup", "on", timeout=15000)
            check("只切题不点按钮：后台查重就把红字与红灯亮起来，且不自动弹窗",
                  panel.locator("#epDupWarn").inner_text().strip().startswith("主库已存在高度相似题目")
                  and canvas.locator("#edDupModal").is_hidden(),
                  {"warn": panel.locator("#epDupWarn").inner_text(),
                   "modal_hidden": canvas.locator("#edDupModal").is_hidden()})
            panel.locator("#epApprove").click()
            expect(panel.locator("#epDupBox")).to_be_visible(timeout=25000)
            check("答案不同：红字明说只能放弃，覆盖与合并两颗钮都锁死",
                  "答案不同" in panel.locator("#epDupWarn").inner_text()
                  and panel.locator("#epDupOverwrite").is_disabled()
                  and panel.locator("#epDupMerge").is_disabled()
                  and not panel.locator("#epDupAbandon").is_disabled(),
                  {"warn": panel.locator("#epDupWarn").inner_text(),
                   "overwrite_disabled": panel.locator("#epDupOverwrite").is_disabled(),
                   "merge_disabled": panel.locator("#epDupMerge").is_disabled()})
            expect(canvas.locator("#edDupBlock")).to_be_visible(timeout=10000)
            check("画布浮层同步亮出红字拦截说明",
                  "答案不同" in canvas.locator("#edDupBlock").inner_text(),
                  {"block": canvas.locator("#edDupBlock").inner_text()})
            page.screenshot(path=str(shots / "v3-dup-blocked.png"))
            panel.locator("#epDupAbandon").click()
            expect(panel.locator("#epDupBox")).to_be_hidden(timeout=10000)

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

            # ---------- 军令 #27：文件收集筐（拖入 / 大图粘贴 / 开始解析） ----------
            to_list()

            # 首屏黄金分割 1.618 : 1：左栏批次列表宽，右栏一只巨大的圆角虚线筐。
            split = canvas.locator("#edRoot").evaluate("""() => {
              function rect(node) {
                if (!node) return null;
                var r = node.getBoundingClientRect();
                return {x: r.x, y: r.y, w: r.width, h: r.height};
              }
              var body = document.querySelector('.ed-batches-body');
              var left = document.querySelector('.ed-batch-col');
              var right = document.querySelector('.ed-basket-col');
              var box = document.getElementById('edBasket');
              var cs = box ? getComputedStyle(box) : null;
              return {
                body: rect(body), left: rect(left), right: rect(right), basket: rect(box),
                borderStyle: cs ? cs.borderTopStyle : '',
                borderRadius: parseFloat(cs ? cs.borderTopLeftRadius : '0') || 0,
                textAlign: cs ? cs.textAlign : '',
                flexDirection: cs ? cs.flexDirection : ''
              };
            }""")
            result["metrics"]["split"] = split
            gap = (split["right"]["x"] - split["left"]["x"] - split["left"]["w"]
                   if split["left"] and split["right"] else 0)
            ratio = (split["left"]["w"] / split["right"]["w"]
                     if split["left"] and split["right"] and split["right"]["w"] else 0)
            check("首屏是黄金分割 1.618 : 1（左宽右窄）",
                  bool(split["left"] and split["right"] and split["body"])
                  and abs(ratio - 1.618) <= 0.02
                  and split["left"]["w"] > split["right"]["w"],
                  {"gap": gap, "ratio": round(ratio, 4),
                   "left": split["left"]["w"], "right": split["right"]["w"],
                   "body": split["body"]["w"]})
            check("右栏是圆角虚线筐，里面改成垂直单列",
                  split["borderStyle"] == "dashed"
                  and split["borderRadius"] >= 12
                  and split["textAlign"] == "left"
                  and split["flexDirection"] == "column",
                  {"border": split["borderStyle"], "radius": split["borderRadius"],
                   "align": split["textAlign"], "flex": split["flexDirection"]})
            check("虚线筐占满右栏（不是一小块）",
                  bool(split["basket"] and split["right"]
                       and split["basket"]["w"] >= split["right"]["w"] * 0.9),
                  {"basket": split["basket"], "right": split["right"]})
            check("辅助栏已无接收区（瘦身令：收件只剩画布的筐）",
                  panel.locator("#epIntake").count() == 0,
                  {"intake": panel.locator("#epIntake").count()})

            def host_drag(name: str, mime: str, kind: str) -> None:
                page.evaluate(
                    """([name, mime, kind]) => {
                        var dt = new DataTransfer();
                        dt.items.add(new File([new Uint8Array([1, 2, 3])], name, {type: mime}));
                        window.dispatchEvent(new DragEvent(kind, {dataTransfer: dt, bubbles: true}));
                    }""", [name, mime, kind])

            intake_overlay = page.locator("#wsIntakeOverlay")
            zip_overlay = page.locator("#wsDropOverlay")
            host_drag("卷子.pdf", "application/pdf", "dragenter")
            page.wait_for_timeout(250)
            overlay_text = intake_overlay.inner_text() if intake_overlay.count() else ""
            check("拖卷子时弹「松开鼠标」遮罩，且落点是收集筐",
                  intake_overlay.is_visible()
                  and "松开鼠标" in overlay_text
                  and "收集筐" in overlay_text
                  and zip_overlay.is_hidden(),
                  {"intake": overlay_text[:60]})
            host_drag("插件包.zip", "application/zip", "dragenter")
            page.wait_for_timeout(250)
            check("拖插件包时弹的是「松手即安装插件」那一层",
                  zip_overlay.is_visible() and intake_overlay.is_hidden(), {})
            host_drag("卷子.pdf", "application/pdf", "dragleave")
            host_drag("插件包.zip", "application/zip", "dragleave")
            page.wait_for_timeout(250)
            check("拖走之后两块遮罩都收起来",
                  intake_overlay.is_hidden() and zip_overlay.is_hidden(), {})

            # 拖一个普通文件进筐：筐里出现带文件名的条目 + 一个 × 移除钮，
            # 但批次还不许多出来——建批次只能由【开始解析】发起。
            cards_before_drag = len(pending_cards(base))

            def basket_drop(name: str, mime: str) -> None:
                # 参数必须内联进脚本：Locator.evaluate 收到字符串函数时不会把数组
                # 原样送进浏览器（页面级 evaluate 才送），解构参数会当场炸。
                script = (
                    "function () {"
                    "  var dt = new DataTransfer();"
                    "  dt.items.add(new File([new Uint8Array([1, 2, 3])], %s, {type: %s}));"
                    "  var node = document.getElementById('edBasket');"
                    "  ['dragenter', 'dragover', 'drop'].forEach(function (kind) {"
                    "    node.dispatchEvent(new DragEvent(kind, {dataTransfer: dt, bubbles: true}));"
                    "  });"
                    "  return true;"
                    "}()" % (json.dumps(name), json.dumps(mime))
                )
                canvas.locator("#edBasket").evaluate(script)

            basket_drop("三省联考.pdf", "application/pdf")
            page.wait_for_timeout(300)
            long_name = "2024年黑龙江省哈尔滨市第三中学校高三第三次模拟考试数学试卷（理科）.pdf"
            basket_drop(long_name, "application/pdf")
            page.wait_for_timeout(400)
            items = canvas.locator("#edBasketList .ed-basket-item")
            names = [items.nth(index).get_attribute("data-name")
                     for index in range(items.count())]
            check("拖进来的普通文件在筐里排成一条，带文件名",
                  items.count() == 2 and names[0] == "三省联考.pdf" and names[1] == long_name,
                  {"count": items.count(), "names": names})
            check("文档行左边是带后缀的页图标",
                  canvas.locator("#edBasketList .ed-basket-icon").count() == items.count()
                  and canvas.locator("#edBasketList .ed-basket-icon-ext").first.inner_text().strip()
                  == "PDF",
                  {"icons": canvas.locator("#edBasketList .ed-basket-icon").count(),
                   "ext": canvas.locator("#edBasketList .ed-basket-icon-ext").first.inner_text()})
            row_boxes = [items.nth(index).bounding_box() for index in range(items.count())]
            basket_box = canvas.locator("#edBasket").bounding_box()
            list_box = canvas.locator("#edBasketList").bounding_box()
            check("垂直单列：每行等宽铺满、从上往下叠",
                  bool(row_boxes[0] and row_boxes[1] and list_box)
                  and abs(row_boxes[0]["width"] - row_boxes[1]["width"]) <= 1
                  and abs(row_boxes[0]["x"] - row_boxes[1]["x"]) <= 1
                  and row_boxes[1]["y"] >= row_boxes[0]["y"] + row_boxes[0]["height"]
                  and abs(row_boxes[0]["width"] - list_box["width"]) <= 8,
                  {"rows": row_boxes, "list": list_box})
            ellipsis = items.nth(1).locator(".ed-basket-name").evaluate(
                "n => ({overflow: getComputedStyle(n).textOverflow,"
                " nowrap: getComputedStyle(n).whiteSpace,"
                " clipped: n.scrollWidth > n.clientWidth, title: n.title})")
            check("文件名太长自动省略，悬停看全名",
                  ellipsis["overflow"] == "ellipsis" and ellipsis["nowrap"] == "nowrap"
                  and ellipsis["clipped"] and ellipsis["title"] == long_name,
                  ellipsis)
            overflow = canvas.locator("#edBasketList").evaluate(
                "n => getComputedStyle(n).overflowY")
            check("文件列表在虚线框内独立滚动", overflow == "auto", {"overflow": overflow})
            foot_box = canvas.locator("#edBasketFoot").bounding_box()
            check("【开始解析】钉在筐底，不跟列表一起滚",
                  bool(foot_box and basket_box and list_box)
                  and foot_box["y"] >= list_box["y"] + list_box["height"] - 1
                  and abs((foot_box["y"] + foot_box["height"])
                          - (basket_box["y"] + basket_box["height"])) <= 20,
                  {"foot": foot_box, "basket": basket_box, "list": list_box})
            page.screenshot(path=str(shots / "v28-basket-list.png"))
            check("每个条目都带一个 × 移除钮",
                  canvas.locator("#edBasketList .ed-basket-x").count() == items.count(),
                  {"x": canvas.locator("#edBasketList .ed-basket-x").count(),
                   "items": items.count()})
            check("拖进筐里还没建批次（要老师点【开始解析】）",
                  len(pending_cards(base)) == cards_before_drag,
                  {"before": cards_before_drag, "after": len(pending_cards(base))})
            check("筐里有东西时底部才出现【开始解析】",
                  canvas.locator("#edBasketFoot").is_visible()
                  and "开始解析" in canvas.locator("#edBasketGo").inner_text(),
                  {"foot": canvas.locator("#edBasketFoot").is_visible(),
                   "go": canvas.locator("#edBasketGo").inner_text()})

            # × 移除：一行一行点干净
            while canvas.locator("#edBasketList .ed-basket-x").count():
                canvas.locator("#edBasketList .ed-basket-x").first.click()
                page.wait_for_timeout(150)
            page.wait_for_timeout(200)
            check("点 × 把条目逐行移除",
                  canvas.locator("#edBasketList .ed-basket-item").count() == 0
                  and canvas.locator("#edBasketFoot").is_hidden(),
                  {"count": canvas.locator("#edBasketList .ed-basket-item").count()})

            # 辅助栏那侧粘进来的图：面板实例与画布实例是两张 iframe，不能直连，
            # 只能经宿主中转——从辅助栏粘一次，看画布的筐有没有接到。
            # （虚线接收框已随瘦身令下线，面板侧只剩这一条全局粘贴通路。）
            panel_paste_script = (
                "function () {"
                "  var dt = new DataTransfer();"
                "  dt.items.add(new File([new Uint8Array(3)], %s, {type: 'image/png'}));"
                "  window.dispatchEvent(new ClipboardEvent('paste',"
                "    {clipboardData: dt, bubbles: true}));"
                "  return true;"
                "}()" % json.dumps("辅助栏粘来的.png")
            )
            panel.locator("#epRoot").evaluate(panel_paste_script)
            page.wait_for_timeout(800)
            relayed = canvas.locator("#edBasketList .ed-basket-item[data-name='辅助栏粘来的.png']")
            check("辅助栏粘进来的图，经宿主转进画布的收集筐",
                  relayed.count() == 1,
                  {"relayed": relayed.count(),
                   "items": canvas.locator("#edBasketList .ed-basket-item").count()})
            if relayed.count():
                relayed.first.locator(".ed-basket-x").click()
                page.wait_for_timeout(300)
            check("辅助栏转进来的那一条也能移除",
                  canvas.locator("#edBasketList .ed-basket-item").count() == 0,
                  {"count": canvas.locator("#edBasketList .ed-basket-item").count()})

            # Ctrl+V 粘贴截图 → 进筐，不直接建批次
            # 字节必须内联进脚本：Playwright 把数组参数送进 iframe 时会变成空对象，
            # Uint8Array 拿到空数组 → 粘进去的是一张 0 字节的图。
            paste_script = (
                "function () {"
                "  var dt = new DataTransfer();"
                "  dt.items.add(new File([new Uint8Array(%s)], %s, {type: 'image/png'}));"
                "  window.dispatchEvent(new ClipboardEvent('paste',"
                "    {clipboardData: dt, bubbles: true}));"
                "  return true;"
                "}()" % (json.dumps(PNG_BYTES), json.dumps("粘贴截图.png"))
            )
            cards_before_paste = len(pending_cards(base))
            canvas.locator("#edRoot").evaluate(paste_script)
            page.wait_for_timeout(500)
            thumb = canvas.locator("#edBasketList .ed-basket-thumb")
            check("Ctrl+V 粘贴的截图在筐里出小缩略图",
                  thumb.count() == 1,
                  {"thumbs": thumb.count(),
                   "items": canvas.locator("#edBasketList .ed-basket-item").count()})
            thumb_box = thumb.first.bounding_box() if thumb.count() else None
            check("缩略图是 44×44 的小方图（行首一眼认出是哪道题）",
                  bool(thumb_box)
                  and round(thumb_box["width"]) == 44
                  and round(thumb_box["height"]) == 44,
                  {"box": thumb_box})
            # 光看盒子不够：插件沙箱的 CSP 会把 blob:/data: 的 <img> 挡成空框，
            # 这里直接数画布上的像素，证明题面真画出来了。
            thumb_state = canvas.locator("#edRoot").evaluate("""() => {
              var node = document.querySelector('#edBasketList .ed-basket-thumb');
              if (!node) return null;
              var ctx = node.getContext('2d');
              var data = ctx.getImageData(0, 0, node.width, node.height).data;
              var painted = 0;
              for (var i = 3; i < data.length; i += 4) { if (data[i] > 0) painted += 1; }
              return {width: node.width, height: node.height, painted: painted};
            }""")
            check("缩略图里真画出了像素（不是被 CSP 挡掉的空框）",
                  bool(thumb_state)
                  and thumb_state["width"] == 44
                  and thumb_state["height"] == 44
                  and thumb_state["painted"] > 0,
                  {"state": thumb_state})
            check("缩略图没被内容安全策略拦下",
                  not [line for line in result["console_errors"]
                       if "Content Security Policy" in line],
                  {"console": [line for line in result["console_errors"]
                               if "Content Security Policy" in line][:2]})
            check("粘贴的截图也带 × 移除钮",
                  canvas.locator("#edBasketList .ed-basket-x").count() == 1,
                  {"x": canvas.locator("#edBasketList .ed-basket-x").count()})
            check("粘贴也不建批次",
                  len(pending_cards(base)) == cards_before_paste,
                  {"before": cards_before_paste, "after": len(pending_cards(base))})

            # 点【开始解析】才正式建批次并推入后台流水线
            canvas.locator("#edBasketGo").click()
            deadline = time.time() + 60
            pasted_cards = pending_cards(base)
            while time.time() < deadline and len(pasted_cards) <= cards_before_paste:
                page.wait_for_timeout(400)
                pasted_cards = pending_cards(base)
            check("点【开始解析】才建批次",
                  len(pasted_cards) > cards_before_paste,
                  {"before": cards_before_paste, "after": len(pasted_cards),
                   "dock": [entry.get("text", "") for entry in dock_entries()[-3:]],
                   "http": result["http_failures"][-4:]})
            pasted_card = None
            for entry in pasted_cards:
                if entry.get("source_name") == "粘贴截图.png":
                    pasted_card = entry
            check("粘贴进来的截图原文件名留在批次卡片上",
                  pasted_card is not None,
                  {"names": [entry.get("source_name") for entry in pasted_cards]})
            check("解析完筐里清空，【开始解析】退场",
                  canvas.locator("#edBasketList .ed-basket-item").count() == 0
                  and canvas.locator("#edBasketFoot").is_hidden(),
                  {"items": canvas.locator("#edBasketList .ed-basket-item").count()})
            page.screenshot(path=str(shots / "v3-basket.png"))

            # ---------- 军令 #26：截屏下线，放大镜搬进左栏「重新框选」 ----------
            check("辅助栏里没有截屏钮了",
                  panel.locator("#epCapture").count() == 0,
                  {"count": panel.locator("#epCapture").count()})
            check("宿主页面上没有截屏遮罩",
                  page.locator(".jzo-cap-layer").count() == 0, {})

            # 一道带托管配图的题进池：切图要有真像素，字节得先落在 pending_assets/。
            crop_png = make_png(64, 48)
            crop_doc = dict(UNIQUE_DOC)
            crop_doc["stem"] = "军令#26 切图专用题：放大镜搬进左栏后，切出来的图落回中转站（  ）"
            status, crop_body = http_post(
                base + "/api/pending/batches",
                {"questions": [{
                    "question": dict(crop_doc, images=[{
                        "id": "img_probe_crop", "role": "stem",
                        "uri": "/static/uploads/img_probe_crop.png", "alt": "待切图"}]),
                    "assets": [{"id": "img_probe_crop",
                                "data_url": "data:image/png;base64,"
                                            + base64.b64encode(crop_png).decode()}],
                }], "origin": "probe.crop"})
            check("带配图的题能入池", status == 201, {"status": status, "body": crop_body})
            crop_batch = str(crop_body.get("batch_id") or "")
            canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.refreshBatches()")
            page.wait_for_timeout(600)
            open_batch(crop_batch)
            expect(canvas.locator(".ed-img-frame img")).to_be_visible(timeout=15000)
            check("左栏画着这一题的原图",
                  canvas.locator(".ed-img-frame img").count() >= 1,
                  {"imgs": canvas.locator(".ed-img-frame img").count()})

            crop_btn = canvas.locator(".ed-img-crop-btn").first
            expect(crop_btn).to_be_visible(timeout=10000)
            crop_label = crop_btn.inner_text()
            check("左栏每一题都有【重新框选】入口",
                  "框选" in crop_label, {"label": crop_label})
            crop_btn.click()
            page.wait_for_timeout(2500)
            crop_hint = ""
            if canvas.locator(".ed-crop-hint").count():
                crop_hint = canvas.locator(".ed-crop-hint").first.inner_text()
            check("切图台亮出来了", canvas.locator(".ed-crop-canvas").count() == 1,
                  {"hint": crop_hint,
                   "diag": canvas.locator("#edRoot").evaluate(
                       """() => ({
                            cells: document.querySelectorAll('.ed-img-cell').length,
                            indexed: document.querySelectorAll('.ed-img-cell[data-index]').length,
                            buttons: document.querySelectorAll('.ed-img-crop-btn').length,
                            hints: document.querySelectorAll('.ed-crop-hint').length,
                            canvases: document.querySelectorAll('canvas').length,
                            first: (function () {
                                var n = document.querySelector('.ed-img-cell');
                                return n ? n.outerHTML.slice(0, 260) : '';
                            })()
                       })"""),
                   "console": [text[:200] for text in result["console_errors"][-6:]],
                   "page": [text[:200] for text in result["page_errors"][-6:]]})
            expect(canvas.locator(".ed-crop-canvas")).to_be_visible(timeout=15000)
            check("切图台给出手势提示（移动看像素、拖拽框选、松开后选动作）",
                  "像素" in crop_hint and "拖拽" in crop_hint and "松开" in crop_hint,
                  {"hint": crop_hint})
            check("切图台上鼠标是十字",
                  canvas.locator(".ed-crop-canvas").evaluate(
                      "n => getComputedStyle(n).cursor") == "crosshair", {})

            # 放大镜：跟着鼠标走，镜心一根红十字。
            box = canvas.locator(".ed-crop-canvas").bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.wait_for_timeout(400)
            check("放大镜层挂上来了", canvas.locator(".ed-crop-lens").count() == 1,
                  {"count": canvas.locator(".ed-crop-lens").count()})
            lens_pixels = canvas.locator(".ed-crop-lens").evaluate(
                """c => {
                    var ctx = c.getContext('2d');
                    var d = ctx.getImageData(0, 0, c.width, c.height).data;
                    var opaque = 0; var red = 0; var ring = 0;
                    for (var i = 0; i < d.length; i += 4) {
                        if (d[i + 3] > 8) opaque += 1;
                        if (d[i] > 220 && d[i + 1] < 140 && d[i + 2] < 140 && d[i + 3] > 120) red += 1;
                        // 镜圈是 rgba(255,255,255,0.9)：叠在四色块上合成后不会纯白
                        // （如蓝底约 229,229,255），按“近白且三通道都亮”认，别卡 230。
                        if (d[i] > 200 && d[i + 1] > 200 && d[i + 2] > 200 && d[i + 3] > 80) ring += 1;
                    }
                    return {opaque: opaque, red: red, ring: ring,
                            smooth: ctx.imageSmoothingEnabled, w: c.width, h: c.height};
                }""")
            # 平滑是有意设计：2 倍取样下关掉就是马赛克，老师要看公式不是看像素格。
            check("放大镜开着平滑看公式", lens_pixels["smooth"] is True, lens_pixels)
            check("放大镜真画出了东西（不是空画布）",
                  lens_pixels["opaque"] > 2000, lens_pixels)
            check("镜心那根红十字在（按像素数出来的）",
                  lens_pixels["red"] > 20, lens_pixels)
            check("镜圈是那圈白边",
                  lens_pixels["ring"] > 20, lens_pixels)
            page.screenshot(path=str(shots / "v4-crop-lens.png"))

            # 拖拽框选 → 左键松开 → 切完。
            page.mouse.move(box["x"] + 4, box["y"] + 4)
            page.mouse.down()
            page.mouse.move(box["x"] + box["width"] - 4, box["y"] + box["height"] - 4,
                            steps=10)
            page.mouse.up()
            # 普通题的框可能是配图：松开鼠标先弹动作条，老师选完才收摊。
            expect(canvas.locator(".ed-crop-actions")).to_be_visible(timeout=5000)
            canvas.locator(".ed-crop-actions").get_by_role(
                "button", name="提取为本题配图").click()
            # 选完动作当场就得收摊：镜子与切图台不许等到落库回执才撤。
            deadline_lens = time.time() + 5
            lens_left = 1
            crop_left = 1
            while time.time() < deadline_lens:
                lens_left = canvas.locator(".ed-crop-lens").count()
                crop_left = canvas.locator(".ed-crop-canvas").count()
                if lens_left == 0 and crop_left == 0:
                    break
                page.wait_for_timeout(100)
            check("切完放大镜消失", lens_left == 0, {"count": lens_left})
            check("切图台也收起来了", crop_left == 0, {"count": crop_left})
            deadline = time.time() + 40
            crop_uri = ""
            while time.time() < deadline:
                items = pending_items(base, crop_batch)
                images = ((items[0].get("question") or {}).get("images") or []) if items else []
                if images:
                    crop_uri = str(images[0].get("uri") or "")
                    if crop_uri.startswith("/static/pending/"):
                        break
                page.wait_for_timeout(400)
            check("选【提取为本题配图】后切图落回中转站",
                  crop_uri.startswith("/static/pending/"), {"uri": crop_uri})
            check("切完的图又出现在左栏里",
                  canvas.locator(".ed-img-frame img").count() >= 1,
                  {"imgs": canvas.locator(".ed-img-frame img").count()})
            page.screenshot(path=str(shots / "v4-crop-done.png"))
            to_list()
            page.screenshot(path=str(shots / "v4-intake.png"))

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

            # ---------- 军令 #31 · 3.1a 导入批次后台自动初查的显形（判据 7/8/9/10） ----------
            # 台账 ⑤（913-921 行）+ 勘误·二（936-980 行）为准：
            # 「导入完成当场自动亮」**不是**判据，老师的【返回列表】才是显形点；
            # pending 态取 DOM 属性 data-dedupe-status，不取文案；
            # 「无红字」= 不含「疑似重复」字样（不按颜色判：failed 与 done 共用 danger 红）。
            page.locator(".ws-plugin-item", has_text="录题工作台").first.click()
            page.wait_for_timeout(800)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            to_list()

            def b31a_doc(mark: str, no: int) -> dict:
                """本批独有的干净题：主库里没有，同 mark 同序号的才在批内互相撞车。"""
                doc = json.loads(json.dumps(UNIQUE_DOC))
                doc["stem"] = ("探针31a初查题 %s#%d：双曲线 $y=\\frac{1}{x+%d}$ 的定义域是（  ）"
                               % (mark, no, no))
                doc["source"] = dict(UNIQUE_DOC["source"], paper_title="探针31a卷",
                                     question_no=str(no))
                return doc

            def b31a_api_dedupe(batch: str) -> dict:
                card = next((c for c in pending_cards(base)
                             if c.get("batch_id") == batch), None)
                info = (card or {}).get("dedupe")
                return info if isinstance(info, dict) else {}

            def b31a_refresh_list() -> None:
                canvas.locator("#edRoot").evaluate(
                    "() => window.__jzoEditorV2.refreshBatches()")
                page.wait_for_timeout(350)

            def b31a_node(batch: str):
                """N2 纪律：只按 stage_ingest 回来的 batch_id 定位那一张卡片，不取第一张。"""
                return canvas.locator('.ed-batch-row[data-batch="%s"] .ed-batch-dedupe' % batch)

            def b31a_card_view(batch: str) -> dict:
                node = b31a_node(batch)
                if node.count() == 0:
                    return {"present": False, "status": None, "text": "",
                            "aria_busy": None, "red": False,
                            "row": canvas.locator(
                                '.ed-batch-row[data-batch="%s"]' % batch).count()}
                text = node.first.inner_text().strip()
                return {"present": True,
                        "status": node.first.get_attribute("data-dedupe-status"),
                        "text": text,
                        "aria_busy": node.first.get_attribute("aria-busy"),
                        "red": "疑似重复" in text,
                        "row": 1}

            def b31a_wait_api(batch: str, status: str, timeout: float) -> tuple[dict, float]:
                start = time.perf_counter()
                info: dict = {}
                deadline = time.perf_counter() + timeout
                while time.perf_counter() < deadline:
                    info = b31a_api_dedupe(batch)
                    if info.get("status") == status:
                        break
                    page.wait_for_timeout(300)
                return info, round(time.perf_counter() - start, 2)

            # ---------- 判据 10：导入时长与初查解耦（与「未挂初查基线」做差值，不写死绝对秒数） ----------
            payload50 = [{"question": b31a_doc("五十题", i)} for i in range(50)]

            def b31a_import(origin: str) -> tuple[float, int, dict]:
                start = time.perf_counter()
                status, body = http_post(base + "/api/pending/batches",
                                         {"questions": payload50, "origin": origin})
                return time.perf_counter() - start, status, body

            # 占位轮口径（app/core/pending_bank.py:219）：origin=="ingest" 且本次不传
            # batch_id 就不挂初查任务——拿它当「未挂初查基线」，与挂了的做同payload差值。
            base_rounds = [b31a_import("ingest") for _ in range(2)]
            hook_rounds = [b31a_import("probe.recognize") for _ in range(2)]
            base_secs = [round(r[0], 4) for r in base_rounds]
            hook_secs = [round(r[0], 4) for r in hook_rounds]
            base_min, hook_min = min(base_rounds[0][0], base_rounds[1][0]), \
                min(hook_rounds[0][0], hook_rounds[1][0])
            delta = round(hook_min - base_min, 4)
            check("判据10 · 后台初查没把导入请求拖成长请求（差值口径：≤基线的 50%，地板 0.25s 只是计时噪声余量）",
                  all(r[1] == 201 for r in base_rounds + hook_rounds)
                  and base_rounds[0][2].get("dedupe_queued") is False
                  and hook_rounds[0][2].get("dedupe_queued") is True
                  and delta <= max(0.25, 0.5 * base_min),
                  {"baseline_seconds": base_secs, "hooked_seconds": hook_secs,
                   "delta_seconds": delta, "floor_note": "0.25s 是噪声余量，不是时限承诺",
                   "dedupe_queued": [base_rounds[0][2].get("dedupe_queued"),
                                     hook_rounds[0][2].get("dedupe_queued")]})
            batch_placeholder = str(base_rounds[0][2].get("batch_id") or "")
            batch50 = str(hook_rounds[0][2].get("batch_id") or "")

            # ---------- pending 态（勘误·二 ①，第 949 行）：占位轮批次必然没缓存 → 稳定 pending ----------
            b31a_refresh_list()
            view_pending = b31a_card_view(batch_placeholder)
            view_50 = b31a_card_view(batch50)  # 挂初查的那一批：能撞上 pending 就一起留档
            check("pending 态口径：data-dedupe-status==pending、不含「疑似重复」字样、aria-busy=true、新文案逐字",
                  view_pending["present"] and view_pending["status"] == "pending"
                  and view_pending["red"] is False
                  and view_pending["aria_busy"] == "true"
                  and view_pending["text"] == "初查结果未出，存入前仍会强校验",
                  {"placeholder": view_pending, "hooked50_at_first_refresh": view_50})
            page.screenshot(path=str(shots / "v31a-pending.png"),
                            full_page=False)

            # ---------- 判据 7：导入含重复题的一批，不点任何查重按钮，走【返回列表】自动显形 ----------
            dup_docs = ([b31a_doc("批内撞车", 1)] * 3) + \
                [b31a_doc("独立甲", 2), b31a_doc("独立乙", 3)]
            t31a_ingest = time.perf_counter()
            status_dup31a, body_dup31a = http_post(
                base + "/api/pending/batches",
                {"questions": [{"question": d} for d in dup_docs], "origin": "probe.recognize"})
            batch_dup31a = str(body_dup31a.get("batch_id") or "")
            status_clean31a, body_clean31a = http_post(
                base + "/api/pending/batches",
                {"questions": [{"question": b31a_doc("干净甲", 7)},
                               {"question": b31a_doc("干净乙", 8)}],
                 "origin": "probe.recognize"})
            batch_clean31a = str(body_clean31a.get("batch_id") or "")
            check("3.1a 前置：含批内重复的一批与干净的一批都进了池子",
                  status_dup31a == 201 and status_clean31a == 201
                  and body_dup31a.get("dedupe_queued") is True
                  and bool(batch_dup31a) and bool(batch_clean31a),
                  {"dup": status_dup31a, "clean": status_clean31a,
                   "dedupe_queued": body_dup31a.get("dedupe_queued"),
                   "batch_dup": batch_dup31a, "batch_clean": batch_clean31a})
            api_done, secs_api_done = b31a_wait_api(batch_dup31a, "done", 15)
            # 卡片要先进插件的 state.batches 才点得动：底座数据回投靠刷新，不靠定时器。
            b31a_refresh_list()
            # 老师的路径：开进这一批看一眼 → 点辅助栏【返回列表】（不碰任何查重/剔除按钮）。
            open_batch(batch_dup31a)
            back_btn = panel.locator("#epBackList")
            expect(back_btn).to_be_visible(timeout=20000)
            back_btn.click()
            expect(canvas.locator("#edBatches")).to_be_visible(timeout=20000)
            view_done = b31a_card_view(batch_dup31a)
            secs_visible = round(time.perf_counter() - t31a_ingest, 2)
            red_match = re.search(
                r"疑似重复 (\d+) 道（批内重复 (\d+) 题 / 主库已有 (\d+) 题）",
                view_done["text"])
            check("判据7 · 【返回列表】后卡片自动亮含「疑似重复」的红字，批内/主库两栏拆开，≤15 秒",
                  bool(red_match) and secs_visible <= 15
                  and [int(g) for g in red_match.groups()] ==
                  [int(api_done.get("redundant", -1)),
                   int(api_done.get("batch_redundant", -1)),
                   int(api_done.get("bank_redundant", -1))],
                  {"elapsed_seconds": secs_visible, "api_wait_seconds": secs_api_done,
                   "card": view_done, "api_dedupe": api_done})
            check("判据7 · 全程没点任何按钮，也没有自动弹窗（对比浮层与剔除清单都没自己开）",
                  canvas.locator("#edDupModal").is_hidden()
                  and canvas.locator("#epBatchPurgeModal").is_hidden()
                  and canvas.locator("#edRoot").get_attribute("data-dup") is None,
                  {"dup_modal": canvas.locator("#edDupModal").is_visible(),
                   "purge_modal": canvas.locator("#epBatchPurgeModal").is_visible()})
            page.screenshot(path=str(shots / "v31a-done-red.png"), full_page=False)

            # ---------- DOM①：done 且 redundant==0 的卡片上 .ed-batch-dedupe 节点必须不存在 ----------
            api_clean, secs_clean = b31a_wait_api(batch_clean31a, "done", 15)
            b31a_refresh_list()
            node_clean = b31a_node(batch_clean31a)
            clean_view = b31a_card_view(batch_clean31a)
            check("done 且 redundant<=0 的批次卡片不渲染 .ed-batch-dedupe 节点（任何路径不写「没有重复」）",
                  api_clean.get("status") == "done"
                  and int(api_clean.get("redundant", -1)) == 0
                  and clean_view["row"] == 1 and node_clean.count() == 0,
                  {"api_dedupe": api_clean, "wait_seconds": secs_clean, "card": clean_view})

            # ---------- 判据 8：红字的「批内组」条数 == 【剔除重复】弹窗默认勾选集 ----------
            pool_before = len(pending_items(base, batch_dup31a))
            row_dup = canvas.locator('.ed-batch-row[data-batch="%s"]' % batch_dup31a)
            expect(row_dup.locator(".ed-batch-purge")).to_be_visible(timeout=20000)
            row_dup.locator(".ed-batch-purge").first.click()
            expect(canvas.locator("#epBatchPurgeModal")).to_be_visible(timeout=25000)
            deadline = time.time() + 25
            summary = ""
            while time.time() < deadline:
                summary = canvas.locator("#epBatchPurgeSummary").inner_text().strip()
                if "已默认勾选" in summary or "没有重复题" in summary:
                    break
                page.wait_for_timeout(300)
            purge_groups = canvas.locator("#epBatchPurgeGroups .ep-purge-group").evaluate_all(
                """nodes => nodes.map(n => {
                    var boxes = Array.prototype.slice.call(
                      n.querySelectorAll('.ep-purge-list input[type=checkbox]'));
                    return {
                      reason: (n.querySelector('.ep-purge-badge') || {}).textContent || '',
                      boxes: boxes.length,
                      checked: boxes.filter(function (b) { return b.checked; }).length
                    };
                })""")
            pool_after = len(pending_items(base, batch_dup31a))
            scanned_summary = re.search(r"本批实读 (\d+) 道", summary)
            prereq_ok = (pool_before == pool_after
                         and bool(scanned_summary)
                         and int(scanned_summary.group(1)) == int(api_done.get("scanned", -1)))
            batch_checked = sum(g["checked"] for g in purge_groups if "批内" in g["reason"])
            bank_checked = sum(g["checked"] for g in purge_groups if "主库" in g["reason"])
            total_checked = sum(g["checked"] for g in purge_groups)
            if prereq_ok:
                check("判据8 · 弹窗默认勾选集与卡片红字同源同尺（批内组勾选数==批内重复数，总勾选==redundant）",
                      batch_checked == int(api_done.get("batch_redundant", -1))
                      and bank_checked == int(api_done.get("bank_redundant", -1))
                      and total_checked == int(api_done.get("redundant", -1)),
                      {"card": {"redundant": api_done.get("redundant"),
                                "batch_redundant": api_done.get("batch_redundant"),
                                "bank_redundant": api_done.get("bank_redundant"),
                                "scanned": api_done.get("scanned")},
                       "modal": {"summary": summary, "groups": purge_groups,
                                 "batch_checked": batch_checked,
                                 "bank_checked": bank_checked,
                                 "total_checked": total_checked},
                       "pool_before": pool_before, "pool_after": pool_after})
            else:
                result.setdefault("na_notes", []).append({
                    "name": "判据8 · 弹窗默认勾选集 vs 卡片红字批内组条数",
                    "verdict": "判据不适用",
                    "reason": "前置条件（b）两次读取之间池内容不变 被破坏："
                              "pool_before=%s pool_after=%s summary=%r scanned=%s"
                              % (pool_before, pool_after, summary[:80],
                                 api_done.get("scanned")),
                })
            page.screenshot(path=str(shots / "v31a-purge-modal.png"), full_page=False)
            canvas.locator("#epBatchPurgeModal").press("Escape")
            expect(canvas.locator("#epBatchPurgeModal")).to_be_hidden(timeout=10000)
            result["metrics"]["b31a"] = {
                "batch_placeholder": batch_placeholder, "batch50": batch50,
                "batch_dup": batch_dup31a, "batch_clean": batch_clean31a,
                "api_done_seconds": secs_api_done, "visible_seconds": secs_visible,
                "baseline_seconds": base_secs, "hooked_seconds": hook_secs,
                "shots": ["v31a-pending.png", "v31a-done-red.png", "v31a-purge-modal.png",
                          "v31a-failed.png"],
            }

            # ---------- 判据 9：主库读不通 → 卡片「初查未完成」，任何路径不出现「没有重复」 ----------
            # 让主库真读不通：把活跃题库的 db 就地写坏（隔离工作区内的文件，探针自产）。
            # failed/超时分支按 N1 纪律不承诺 ≤15 秒，只等它落状态；写坏失败就记「不适用」。
            bank_db = next((p for p in sorted(data_dir.rglob("*.db"))
                            if BANK_ID in p.name), None)
            induced = ""
            backup = b""
            if bank_db is None:
                induced = "找不到活跃题库的 db 文件（%s 下无 *%s*.db）" % (data_dir, BANK_ID)
            else:
                try:
                    backup = bank_db.read_bytes()
                    bank_db.write_bytes(b"31a-probe: not a sqlite file\n" * 8)
                    induced = ""
                except OSError as exc:
                    induced = "db 文件被占用，写不进去：%r" % (exc,)
            if induced:
                result.setdefault("na_notes", []).append({
                    "name": "判据9 · 主库不可用时卡片显示「初查未完成」",
                    "verdict": "判据不适用（界面不可达）",
                    "reason": induced + "；failed 态仅由单测覆盖（tests/test_pending_dedupe_scan.py）",
                })
            else:
                fail_docs = [b31a_doc("主库不通甲", 91), b31a_doc("主库不通乙", 92)]
                status_fail, body_fail = http_post(
                    base + "/api/pending/batches",
                    {"questions": [{"question": d} for d in fail_docs],
                     "origin": "probe.recognize"})
                batch_fail = str(body_fail.get("batch_id") or "")
                api_failed, secs_failed = b31a_wait_api(batch_fail, "failed", 30) \
                    if batch_fail else ({}, 30.0)
                b31a_refresh_list()
                view_failed = b31a_card_view(batch_fail)
                all_texts = canvas.locator(".ed-batch-dedupe").evaluate_all(
                    "nodes => nodes.map(n => (n.textContent || '').trim())")
                no_absolution = not any(("没有重复" in t) or ("无重复" in t)
                                         for t in all_texts)
                check("判据9 · 主库读不通时卡片逐字是「初查未完成（主库读不通），存入前仍会强校验」，"
                      "且所有卡片都不出现「没有重复」",
                      status_fail == 201 and api_failed.get("status") == "failed"
                      and view_failed["status"] == "failed"
                      and view_failed["text"] == "初查未完成（主库读不通），存入前仍会强校验"
                      and view_failed["red"] is False and no_absolution,
                      {"batch": batch_fail, "wait_seconds": secs_failed,
                       "api_dedupe": api_failed, "card": view_failed,
                       "all_dedupe_texts": all_texts[:12]})
                page.screenshot(path=str(shots / "v31a-failed.png"), full_page=False)
                try:
                    bank_db.write_bytes(backup)
                except OSError as exc:
                    result.setdefault("na_notes", []).append({
                        "name": "判据9 · 主库 db 复位",
                        "verdict": "环境收尾",
                        "reason": "写回原字节失败：%r（隔离工作区，随 tag 目录整体丢弃）" % (exc,),
                    })

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
    if result["http_failures"]:
        print("http:", result["http_failures"][:12])
    if result["page_errors"]:
        print("pageerrors:", result["page_errors"][:8])
    if result.get("na_notes"):
        print("na:", json.dumps(result["na_notes"], ensure_ascii=False)[:1200])
    if "error" in result:
        print("error:", result["error"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

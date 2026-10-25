# -*- coding: utf-8 -*-
"""AI 命令面真机取证：军令 #20 第三部分。

用法：``.venv/Scripts/python.exe tools/command_ai_probe.py <out_dir_tag>``

脚本自己在 8788 起隔离底座、在 8799 起一个 OpenAI 兼容的假模型，跑完全部关掉；
工作区数据与插件目录都在临时目录里，不碰本机老师的数据。

假模型只按「本轮指令」返回 tool_calls，用来证明 AI 发出的命令调用真的走了
``command_list`` / ``command_execute`` 两件工具；其余判据全部在真人路径上取证：

1. 字典查询：AI 查引擎命令，回答里带 3 条命令与 bank_search 的 id；
2. 标准数据放行：无界面引擎的 bank_search 由底座就地执行，命中 2 道题；
3. 有界面低风险命令：回 command_request，对话插件经宿主自动转发，夹具真的执行；
4. 高副作用拦截：合并重复题只发确认卡（调用插件/功能/涉及数据/风险等级），库不动；
5. 取消：令牌作废、宿主确认框不出现、库仍然 3 题，旧令牌再确认回「已失效」；
6. 确认：先过卡片、再过宿主 requires_user 确认框，点允许后题库真的从 3 题变 2 题；
7. 上下文防绑架：拿数据库行号当 question_id 在发车前被拒，宿主确认框不出现；
8. 不存在的命令被字典拒绝，不静默执行。
"""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8788
AI_PORT = 8799
ORIGIN = f"http://127.0.0.1:{PORT}"
AI_BASE = f"http://127.0.0.1:{AI_PORT}/v1"
TOKEN = "command-ai-probe-token"

ENGINE = "org.jiuzhang.bank-engine"
BANK_UI = "org.jiuzhang.bank-ui"
CHAT = "org.jiuzhang.chat"
FIXTURE = "com.example.ai-probe"
SEARCH = "org.jiuzhang.action.data.bank_search"
MERGE = "org.jiuzhang.action.data.dedupe_merge"
OPEN = "org.jiuzhang.action.input.open_question"
PING = "com.example.ai-probe.ping"
PRIMARY = "q_ai_probe_0001"
COPY = "q_ai_probe_0002"
KEEP = "q_ai_probe_0003"
PLUGINS = [
    ENGINE, BANK_UI, "org.jiuzhang.paper-gen", "org.jiuzhang.handout",
    "org.jiuzhang.editor", CHAT,
]
HOST_VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")).group(1)

FIXTURE_JS = """
(function () {
  "use strict";
  var P = "jzo-plugin/1";
  var mark = document.getElementById("mark");
  mark.textContent = "READY";
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== P || message.kind !== "request") return;
    if (message.method === "command.execute") {
      var payload = message.payload || {};
      var context = payload.context || {};
      mark.textContent = "RAN:" + payload.command_id + ":" + (context.text || "");
      window.parent.postMessage({
        protocol: P, id: message.id, kind: "response", ok: true,
        result: { command_id: payload.command_id, echoed: context.text || "" }
      }, "*");
      return;
    }
    window.parent.postMessage({
      protocol: P, id: message.id, kind: "response", ok: true,
      result: { ready: true, plugin_id: "%s", api_version: "1.0" }
    }, "*");
  });
})();
""" % FIXTURE


def fixture_zip() -> bytes:
    manifest = {
        "schema_version": "1.0",
        "id": FIXTURE,
        "name": "AI 命令探针夹具",
        "version": "1.0.0",
        "api_version": "1.0",
        "kind": "tool",
        "description": "只用于 AI 命令面取证的最小有界面插件",
        "author": "九章算子",
        "license": "Apache-2.0",
        "min_host_version": HOST_VERSION,
        "entry": {"frontend": "dist/index.html"},
        "slots": ["stage.center"],
        "capabilities": ["question.render"],
        "permissions": [],
        "stage": {"region": "center", "mode": "takeover", "title": "AI 命令探针夹具",
                  "priority": 5, "singleton": False, "weight": "light"},
        "bus": {"subscribe": [], "publish": []},
        "show_in_sidebar": False,
        "contributes": {
            "commands": [{
                "id": PING,
                "title": "探针回声",
                "description": "把 context.text 原样回显，用来证明宿主真的把命令送进了插件。",
                "params_schema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "maxLength": 40, "description": "要回显的文字"}
                    },
                    "additionalProperties": False,
                },
                "returns": "{ command_id, echoed }",
            }]
        },
    }
    html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"></head>'
            '<body><p id="mark">HTML-ONLY</p><script src="./plugin.js"></script></body></html>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{FIXTURE}/plugin.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr(f"{FIXTURE}/dist/index.html", html)
        zf.writestr(f"{FIXTURE}/dist/plugin.js", FIXTURE_JS)
        zf.writestr(f"{FIXTURE}/LICENSE", (ROOT / "LICENSE").read_text(encoding="utf-8"))
    return buf.getvalue()


# --- 假模型：OpenAI 兼容 /v1/chat/completions -------------------------------
class FakeModel:
    """只认本轮指令里几个取证句式；其余回一句澄清文本，绝不猜命令。"""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.lock = threading.Lock()
        model = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:  # noqa: D401 - 静音
                return

            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 约定
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    payload = {}
                reply = model.reply(payload)
                body = json.dumps(reply, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", AI_PORT), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.server.shutdown()
        self.server.server_close()

    def reply(self, payload: dict) -> dict:
        messages = payload.get("messages") or []
        last = ""
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "user":
                last = str(message.get("content") or "")
                break
        _, _, tail = last.rpartition("## 本轮指令")
        instruction = (tail or last).strip()
        tools = [
            ((item.get("function") or {}).get("name"))
            for item in (payload.get("tools") or []) if isinstance(item, dict)
        ]
        with self.lock:
            self.calls.append({"instruction": instruction[:200], "tools": tools})

        pick: tuple[str, dict] | None = None
        if "引擎插件能做的事" in instruction:
            pick = ("command_list", {"plugin_id": ENGINE})
        elif "彩虹独角兽" in instruction and "查" in instruction:
            pick = ("command_execute", {"command_id": SEARCH,
                                        "context": {"query": "彩虹独角兽", "limit": 5}})
        elif "探针回声" in instruction:
            pick = ("command_execute", {"command_id": PING,
                                        "context": {"text": "收到"}})
        elif "把重复题合并" in instruction:
            pick = ("command_execute", {"command_id": MERGE,
                                        "context": {"primary_id": PRIMARY,
                                                    "copy_ids": [COPY]}})
        elif "打开第 42 号" in instruction:
            pick = ("command_execute", {"command_id": OPEN,
                                        "context": {"question_id": "42"}})
        elif "不存在的命令" in instruction:
            pick = ("command_execute", {"command_id": "com.example.ai-probe.missing",
                                        "context": {}})

        if pick is None:
            return {
                "choices": [{"message": {"role": "assistant",
                                         "content": "这句不是命令取证句式，本次不调用工具。"}}],
                "model": "probe-model",
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
            }
        name, arguments = pick
        return {
            "choices": [{"message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{
                    "id": "call_probe_1",
                    "type": "function",
                    "function": {"name": name,
                                 "arguments": json.dumps(arguments, ensure_ascii=False)},
                }],
            }}],
            "model": "probe-model",
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }


# --- 通用工具 ---------------------------------------------------------------
def api_status(method: str, path: str, blob: bytes | None = None,
               body: dict | None = None) -> tuple[int, dict]:
    data = blob
    request = urllib.request.Request(ORIGIN + path, data=data, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("X-JZO-Token", TOKEN)
    if blob is not None:
        request.add_header("Content-Type", "application/octet-stream")
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(ORIGIN + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        request.add_header("X-JZO-Token", TOKEN)
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, json.loads(raw)
        except json.JSONDecodeError:
            return error.code, {"detail": raw}


def wait_port(port: int, deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.3)
    return False


def port_free(port: int) -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", port)) != 0


def seed_script() -> str:
    return """
import json, sqlite3
from app.core import bank
path = bank.ensure_bank("org.jiuzhang.bank-engine")
stamp = "2026-02-01T09:00:00+08:00"
con = sqlite3.connect(path)
try:
    for question_id, stem in (
        (%r, "AI 命令面取证：彩虹独角兽与导数"),
        (%r, "AI 命令面取证：彩虹独角兽与数列"),
        (%r, "AI 命令面取证：普通函数题"),
    ):
        con.execute(
            "INSERT OR REPLACE INTO questions (id,type,stem,options,answer,solution,"
            "extensions,difficulty,created_at,updated_at)"
            " VALUES (?,'solution',?,'[]',NULL,NULL,'[]','L2',?,?)",
            (question_id, stem, stamp, stamp),
        )
    con.commit()
finally:
    con.close()
print(json.dumps({"path": str(path)}))
""" % (PRIMARY, COPY, KEEP)


def count_questions(db_path: Path) -> int:
    con = sqlite3.connect(db_path)
    try:
        return int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
    finally:
        con.close()


def has_question(db_path: Path, question_id: str) -> bool:
    con = sqlite3.connect(db_path)
    try:
        row = con.execute("SELECT 1 FROM questions WHERE id = ?", (question_id,)).fetchone()
        return row is not None
    finally:
        con.close()


def chat_frame(page):
    deadline = time.time() + 30
    while time.time() < deadline:
        for frame in page.frames:
            if CHAT in (frame.url or ""):
                try:
                    if frame.locator("#chatPrompt").count() == 1:
                        return frame
                except Exception:  # noqa: BLE001 - iframe 正在挂载
                    pass
        page.wait_for_timeout(250)
    return None


def fixture_frame(page):
    for frame in page.frames:
        if f"/plugin-assets/{FIXTURE}/" in (frame.url or ""):
            return frame
    return None


def thread_since(frame, index: int) -> str:
    return frame.evaluate("""
    (index) => Array.from(document.querySelectorAll('#chatThread .jzochat-msg'))
      .slice(index).map(node => node.innerText).join('\\n')
    """, index)


def wait_since(frame, index: int, needle: str, deadline_seconds: float = 30) -> str:
    """只在本轮新增的气泡里找关键词，避免匹配到上一轮的历史回答。"""
    deadline = time.time() + deadline_seconds
    text = ""
    while time.time() < deadline:
        try:
            text = thread_since(frame, index)
        except Exception:  # noqa: BLE001 - iframe 正在导航
            text = ""
        if needle in (text or ""):
            return text
        time.sleep(0.15)
    return text


def send_prompt(frame, text: str) -> int:
    before = frame.locator(".jzochat-msg").count()
    frame.fill("#chatPrompt", text)
    frame.click("#chatSend")
    return before


def wait_new_confirm_card(frame, prior_count: int, deadline_seconds: float = 30):
    """等一张「本轮新出现」的确认卡；旧卡按钮已禁用，不能拿 .last 硬点。"""
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        count = frame.locator(".jzochat-confirm-card").count()
        if count > prior_count:
            card = frame.locator(".jzochat-confirm-card").last
            return {
                "title": card.locator(".jzochat-card-title").inner_text(),
                "description": card.locator(".jzochat-card-desc").inner_text(),
                "buttons": card.locator("footer button").all_inner_texts(),
                "count": count,
            }
        time.sleep(0.15)
    return None


def click_confirm_button(frame, label: str) -> bool:
    card = frame.locator(".jzochat-confirm-card").last
    button = card.locator("footer button", has_text=label)
    if button.count() != 1:
        return False
    try:
        button.click(timeout=8000)
    except Exception:  # noqa: BLE001 - 旧卡按钮已禁用
        return False
    return True


def dialog_info(page):
    return page.evaluate("""
    () => {
      const box = document.querySelector('.ws-dialog');
      if (!box) return null;
      const lede = box.querySelector('.ws-dialog-lede');
      return {
        message: lede ? lede.textContent : '',
        buttons: Array.from(box.querySelectorAll('.ws-dialog-tools button'))
          .map(btn => btn.textContent.trim())
      };
    }
    """)


def wait_dialog(page, deadline_seconds: float = 15):
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        info = dialog_info(page)
        if info:
            return info
        page.wait_for_timeout(100)
    return None


def click_dialog(page, label: str) -> bool:
    return page.evaluate("""
    (label) => {
      const buttons = Array.from(document.querySelectorAll('.ws-dialog-tools button'));
      const target = buttons.find(btn => btn.textContent.trim() === label);
      if (!target) return false;
      target.click();
      return true;
    }
    """, label)


def dump(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "command_ai_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    work = out / "isolated"
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir = work / "data", work / "plugins"
    for path in (data_dir, plugins_dir):
        path.mkdir(parents=True, exist_ok=True)
    for plugin_id in PLUGINS:
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)
    # 本机开发目录里有 456 题的种子 bank.db（发行包不带）；取证要确定性计数，
    # 所以从隔离副本里摘掉种子，让引擎按 schema.sql 建空库。
    for seed in (plugins_dir / ENGINE / "bank").glob("*.db*"):
        seed.unlink()

    checks: list[dict] = []
    evidence: dict = {}
    raw: dict = {}

    def check(name: str, passed, detail="") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:600]})

    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_STATE_FILE"] = str(data_dir / "workspaces" / "default" / "plugin_state.json")
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["JZO_RESTART_DISABLED"] = "1"
    env["JZO_AI_PROVIDER"] = "openai-compatible"
    env["JZO_AI_API_KEY"] = "probe-key"
    env["JZO_AI_BASE_URL"] = AI_BASE
    env["JZO_AI_MODEL"] = "probe-model"

    server = None
    model = None
    browser = None
    pw = None
    db_path: Path | None = None
    responses: list[dict] = []
    try:
        check(f"00 端口 {PORT}/{AI_PORT} 空闲", port_free(PORT) and port_free(AI_PORT),
              f"host_free={port_free(PORT)} ai_free={port_free(AI_PORT)}")
        if not (port_free(PORT) and port_free(AI_PORT)):
            raise RuntimeError("port occupied")

        seeded = subprocess.run(
            [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-c", seed_script()],
            cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=120)
        if seeded.returncode != 0:
            raise RuntimeError("seed failed: " + seeded.stderr[-800:])
        db_path = Path(json.loads(seeded.stdout.strip().splitlines()[-1])["path"])
        initial = count_questions(db_path)
        check("01 隔离题库种下 3 道题（其中 2 道含关键词「彩虹独角兽」）",
              initial == 3 and has_question(db_path, PRIMARY)
              and has_question(db_path, COPY) and has_question(db_path, KEEP),
              {"path": str(db_path), "total": initial})

        model = FakeModel()
        model.start()
        check(f"02 假 OpenAI 兼容服务在 {AI_PORT} 起来", wait_port(AI_PORT, 15), AI_BASE)

        log_path = out / "host.log"
        server = subprocess.Popen(
            [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(PORT)],
            cwd=str(ROOT), env=env, stdout=log_path.open("wb"), stderr=subprocess.STDOUT)
        check("03 隔离底座起来了（六个官方插件，AI Provider 指向假模型）",
              wait_port(PORT, 60), f"log={log_path}")

        status, installed = api_status(
            "POST", "/api/plugins/install?replace=true", blob=fixture_zip())
        raw["install_fixture"] = {"status": status, "payload": installed}
        check("04 第三方有界面夹具装上（自带低风险命令 probe.ping）",
              status == 200 and installed.get("installed") is True,
              installed.get("detail") or installed.get("plugin"))

        pw = sync_playwright().start()
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))

        def on_response(response):
            if "/api/agent/chat" not in (response.url or ""):
                return
            try:
                responses.append(response.json())
            except Exception:  # noqa: BLE001 - 响应体可能已被导航丢弃
                pass

        page.on("response", on_response)
        page.goto(f"{ORIGIN}/workspace", wait_until="networkidle")
        page.wait_for_timeout(1800)
        chat = chat_frame(page)
        check("05 AI 助手 iframe 就绪（真实宿主 iframe + postMessage 通道）",
              chat is not None, chat.url if chat else "NO_FRAME")
        if chat is None:
            raise RuntimeError("chat frame missing")

        # --- 1. 字典查询：模型发 command_list -------------------------------
        turn = send_prompt(chat, "引擎插件能做的事给我列一下")
        listed_text = wait_since(chat, turn, "条命令", 30)
        evidence["command_list_text"] = listed_text[-600:]
        check("06 AI 经 command_list 查字典：回答里有 3 条引擎命令与 bank_search id",
              "3 条命令" in listed_text and SEARCH in listed_text,
              listed_text[-300:])

        # --- 2. 标准数据放行：无界面引擎就地执行 ---------------------------
        turn = send_prompt(chat, "查一下题库里关于彩虹独角兽的题")
        search_text = wait_since(chat, turn, "道匹配", 30)
        evidence["bank_search_text"] = search_text[-600:]
        check("07 无界面 bank_search 由底座就地执行：命中 2 道题且回显题干",
              "共 2 道匹配" in search_text and "彩虹独角兽" in search_text,
              search_text[-300:])

        # --- 3. 低风险有界面命令：command_request 交给宿主转发 -------------
        turn = send_prompt(chat, "让探针回声说一声收到")
        ping_text = wait_since(chat, turn, "已由", 40)
        deadline = time.time() + 20
        mark = ""
        while time.time() < deadline:
            frame = fixture_frame(page)
            if frame is not None:
                try:
                    mark = frame.evaluate("() => document.getElementById('mark').textContent")
                except Exception:  # noqa: BLE001
                    mark = ""
            if mark.startswith("RAN:"):
                break
            time.sleep(0.2)
        evidence["ping"] = {"bubble": ping_text[-400:], "mark": mark,
                            "frames": [item.url for item in page.frames]}
        check("08 低风险有界面命令经宿主转发，夹具真的收到并回显",
              mark == f"RAN:{PING}:收到" and "探针回声" in ping_text,
              {"mark": mark, "bubble": ping_text[-300:],
               "frames": evidence["ping"]["frames"]})

        # --- 4. 高副作用：只发确认卡，不发命令 ------------------------------
        responses.clear()
        cards_before = chat.locator(".jzochat-confirm-card").count()
        turn = send_prompt(chat, "把重复题合并掉")
        card = wait_new_confirm_card(chat, cards_before, 30)
        evidence["confirm_card"] = card
        time.sleep(1.0)
        card_tokens = []
        for entry in responses:
            for call in ((entry or {}).get("data") or {}).get("plugin_calls") or []:
                for block in call.get("cards") or []:
                    if block.get("type") == "confirm_card":
                        card_tokens.append(block)
        check("09 高副作用命令只发确认卡：点名调用插件、功能、涉及数据与风险等级",
              card is not None
              and "合并重复题" in card["title"]
              and "调用插件" in card["description"]
              and "功能" in card["description"]
              and "涉及数据" in card["description"]
              and "风险等级" in card["description"]
              and card["buttons"] == ["确认执行", "取消"],
              card)
        check("10 卡片到达前命令没有执行：题库仍是 3 题",
              count_questions(db_path) == 3, count_questions(db_path))
        first_token = ""
        if card_tokens:
            match = re.search(r"确认码\s*([A-Za-z0-9_-]{8,64})",
                              card_tokens[-1]["actions"][0]["command"])
            first_token = match.group(1) if match else ""
        evidence["first_token_len"] = len(first_token)

        # --- 5. 取消：令牌作废、宿主确认框不出现、库不动 -------------------
        turn = chat.locator(".jzochat-msg").count()
        cancelled = click_confirm_button(chat, "取消")
        cancel_text = wait_since(chat, turn, "已取消", 20)
        page.wait_for_timeout(800)
        evidence["cancel"] = {"clicked": cancelled, "bubble": cancel_text[-400:],
                              "dialog": dialog_info(page)}
        check("11 点「取消」：回已取消、宿主确认框不出现、题库仍 3 题",
              cancelled and "已取消" in cancel_text and dialog_info(page) is None
              and count_questions(db_path) == 3,
              {"dialog": dialog_info(page), "total": count_questions(db_path)})

        if first_token:
            status, reused = api_status(
                "POST", "/api/agent/chat",
                body={"user_input": f"确认执行命令（确认码 {first_token}）", "task_id": "reuse"})
            call = ((reused.get("data") or {}).get("plugin_calls") or [{}])[0]
            raw["reuse_token"] = {"status": status, "payload": reused}
            check("12 已取消的确认码不能二次使用：回「已失效」且不执行",
                  status == 200 and call.get("ok") is False
                  and ("失效" in str(call.get("error")) or "取消" in str(call.get("error"))),
                  call.get("error"))
        else:
            check("12 已取消的确认码不能二次使用：回「已失效」且不执行", False,
                  "没有从卡片回包里取到确认码")

        # --- 6. 确认：卡片 → 宿主确认框 → 真执行 ---------------------------
        responses.clear()
        cards_before = chat.locator(".jzochat-confirm-card").count()
        send_prompt(chat, "把重复题合并掉")
        card2 = wait_new_confirm_card(chat, cards_before, 30)
        turn = chat.locator(".jzochat-msg").count()
        confirmed = click_confirm_button(chat, "确认执行") if card2 else False
        dialog = wait_dialog(page, 20)
        evidence["host_dialog"] = dialog
        check("13 点「确认执行」后还要过宿主 requires_user 闸：弹框点名命令与目标插件",
              confirmed and dialog is not None
              and "合并重复题" in (dialog or {}).get("message", "")
              and "真题题库" in (dialog or {}).get("message", "")
              and "允许执行" in (dialog or {}).get("buttons", []),
              dialog)
        check("14 宿主确认框还没点允许时题库仍是 3 题（没有提前执行）",
              count_questions(db_path) == 3, count_questions(db_path))
        if dialog:
            page.screenshot(path=str(out / "host_confirm_dialog.png"), full_page=True)
        allowed = click_dialog(page, "允许执行") if dialog else False
        done_text = wait_since(chat, turn, "已由", 40)
        deadline = time.time() + 30
        total = count_questions(db_path)
        while time.time() < deadline and total != 2:
            time.sleep(0.25)
            total = count_questions(db_path)
        evidence["confirm"] = {"bubble": done_text[-400:], "total": total,
                               "copy_left": has_question(db_path, COPY)}
        check("15 点「允许执行」后命令真的落地：题库 3→2，副本被并掉",
              allowed and total == 2 and not has_question(db_path, COPY)
              and has_question(db_path, PRIMARY),
              {"total": total, "copy_left": has_question(db_path, COPY)})
        page.screenshot(path=str(out / "after_confirm.png"), full_page=True)

        # --- 7. 上下文防绑架：行号冒充题目 id ------------------------------
        turn = send_prompt(chat, "打开第 42 号题目")
        rowid_text = wait_since(chat, turn, "公开 id", 30)
        evidence["rowid_reject"] = rowid_text[-600:]
        check("16 数据库行号 42 冒充 question_id：发车前被拒，点名公开 id 口径",
              "公开 id" in rowid_text and "42" in rowid_text
              and dialog_info(page) is None,
              rowid_text[-300:])

        # --- 8. 不存在的命令 -------------------------------------------------
        turn = send_prompt(chat, "帮我执行一条不存在的命令")
        missing_text = wait_since(chat, turn, "能力字典里没有", 30)
        evidence["missing"] = missing_text[-600:]
        check("17 字典里没有的命令被拒绝，不静默执行",
              "能力字典里没有" in missing_text and count_questions(db_path) == 2,
              missing_text[-300:])

        page.screenshot(path=str(out / "chat_thread.png"), full_page=True)
        evidence["model_calls"] = model.calls
        tool_names = sorted({name for call in model.calls for name in call.get("tools") or []})
        check("18 AI 工具链真的下发了 command_list / command_execute 两件工具",
              "command_list" in tool_names and "command_execute" in tool_names,
              tool_names)
        check("19 全程宿主页零未捕获 JS 错误", not errors, errors[:2])
    except Exception as exc:  # noqa: BLE001 - 崩了也要把已有判据带出去
        checks.append({"name": "CRASH", "passed": False, "detail": repr(exc)[:600]})
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:  # noqa: BLE001
                pass
        if pw is not None:
            try:
                pw.stop()
            except Exception:  # noqa: BLE001
                pass
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
        if model is not None:
            try:
                model.stop()
            except Exception:  # noqa: BLE001
                pass

    passed = sum(1 for item in checks if item["passed"])
    result = {"tag": tag, "total": len(checks), "passed": passed,
              "checks": checks, "evidence": evidence, "raw_api": raw}
    dump(out / "probe.json", result)
    print(json.dumps({"total": result["total"], "passed": passed}, ensure_ascii=False))
    for item in checks:
        print(("PASS " if item["passed"] else "FAIL ") + item["name"] + " | " + item["detail"])
    return result


if __name__ == "__main__":
    outcome = run(sys.argv[1] if len(sys.argv) > 1 else "run")
    sys.exit(0 if outcome["passed"] == outcome["total"] else 1)

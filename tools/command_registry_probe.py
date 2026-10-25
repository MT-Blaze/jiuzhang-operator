# -*- coding: utf-8 -*-
"""能力路由字典（Command Registry）真机取证：军令 #19 第二、三部分。

用法：``.venv/Scripts/python.exe tools/command_registry_probe.py <out_dir_tag>``
（脚本自己在 8786 起隔离服务，跑完关掉）

夹具四类，都在第三方命名空间（``com.example.*``）：

- ``com.example.cmd-provider``：清单里声明 ``echo``、``with_tags``、**高副作用**
  ``destructive``（``requires_user: true``）、``slow``（1.5 秒才回）、``big``（回包 70 KB），
  以及一条**越权抢官方名**的 ``org.jiuzhang.action.output.export_word``。
  它把每次执行到的 ``command_id / context / from / trace`` 记在内存并写进 DOM；
  ``slow`` 另记 start/end 时间线，用来验宿主串行。
- ``com.example.cmd-caller``：声明自己的 ``ping``，页面内暴露 ``probeCall`` /
  ``probeStart``，由探针驱动它走真实 postMessage 通道——不注入任何宿主私有句柄。
- ``com.example.cmd-panel``：只声明 ``sidebar.right`` + ``assistant.chat``，成为右栏默认住户，
  用来验「命令转发到面板目标」这条分支（不该被强行搬到画布）。
- ``com.example.cap-1..6``：六支极轻插件，各声明一条命令，用来验自动开页上限（5 个）。

判据覆盖：清单归一与越权丢弃 → ``/api/plugins`` 同源 → 宿主内存字典 →
目标页签未开时自动开页并等就绪 → context 原样到达、``from`` 是调用方 →
未知/越权/坏形状/超大上下文/伪造环路各自拿到明确错误码 → 用户拒绝/允许高副作用命令 →
右栏面板目标转发 → 慢命令 pending 通知与按目标串行 → 64 KB 结果上限 →
自动开页上限 → 卸载后字典同步退场。
"""
from __future__ import annotations

import io
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8786
ORIGIN = f"http://127.0.0.1:{PORT}"
WORKSPACE = f"{ORIGIN}/workspace"
TOKEN = "command-registry-probe-token"
CALLER_ID = "com.example.cmd-caller"
PROVIDER_ID = "com.example.cmd-provider"
PANEL_ID = "com.example.cmd-panel"
CAP_IDS = ["com.example.cap-%d" % index for index in range(1, 7)]
CALLER_PING = "com.example.cmd-caller.ping"
PROVIDER_ECHO = "com.example.cmd-provider.echo"
PROVIDER_TAGS = "com.example.cmd-provider.with_tags"
PROVIDER_DESTRUCTIVE = "com.example.cmd-provider.destructive"
PROVIDER_SLOW = "com.example.cmd-provider.slow"
PROVIDER_BIG = "com.example.cmd-provider.big"
PANEL_FLASH = "com.example.cmd-panel.flash"
CAP_COMMANDS = ["com.example.cap-%d.run" % index for index in range(1, 7)]
OFFICIAL_CLAIM = "org.jiuzhang.action.output.export_word"
HOST_VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")).group(1)

CONTEXT = {
    "question_ids": ["q_3f9a2c71", "q_b18e440d"],
    "topic": "三角函数·正弦定理",
    "nested": {"depth": [1, 2.5, None, True], "note": "带中文与符号 ∑"},
}

JS_OPEN = """
async (pluginId) => {
  const resp = await fetch('/api/plugins', {cache: 'no-store'});
  const data = await resp.json();
  const plugin = (data.plugins || []).find(item => item.id === pluginId);
  if (!plugin || !window.JzoStage || typeof window.JzoStage.openPlugin !== 'function') return false;
  window.JzoStage.openPlugin(plugin);
  return true;
}
"""

JS_STATE = """
() => ({
  labels: Array.from(document.querySelectorAll('#wsTabs .ws-tab-label'))
    .map(el => el.textContent.trim()),
  dock: Array.from(document.querySelectorAll('#wsDockLog li')).map(li => li.textContent)
})
"""

CALLER_JS = """
(function () {
  "use strict";
  var P = "jzo-plugin/1";
  var ID = "%s";
  var seq = 0;
  var pending = {};
  var notifications = [];
  var results = {};
  document.getElementById("mark").textContent = "CALLER:IDLE";

  window.probeCall = function (method, payload) {
    return new Promise(function (resolve) {
      seq += 1;
      var requestId = "c" + seq + "_" + Date.now().toString(36);
      pending[requestId] = resolve;
      window.parent.postMessage({
        protocol: P, id: requestId, kind: "request", method: method, payload: payload || {}
      }, "*");
    });
  };
  // 需要「请求在飞、页面还能点」的场景（用户确认框、慢命令）用这两个：
  // probeStart 只登记 Promise，probeResult 由探针轮询，避免 evaluate 阻塞住对话框。
  window.probeStart = function (tag, method, payload) {
    results[tag] = null;
    window.probeCall(method, payload).then(function (value) { results[tag] = value; });
  };
  window.probeResult = function (tag) { return results[tag]; };
  window.probeNotifications = function () { return notifications.slice(); };

  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== P) return;
    if (message.kind === "response") {
      var settle = pending[message.id];
      if (!settle) return;
      delete pending[message.id];
      settle(message.ok
        ? { ok: true, result: message.result }
        : { ok: false, error: message.error });
      return;
    }
    if (message.kind === "notification") {
      if (message.event === "command.pending") notifications.push(message.payload || {});
      return;
    }
    if (message.kind !== "request") return;
    if (message.method === "command.execute") {
      // 本条只在环路判据里当靶子：伪造 trace 已满，宿主必须在转发前拦下。
      window.parent.postMessage({
        protocol: P, id: message.id, kind: "response", ok: true,
        result: { pong: true, from: (message.payload || {}).from }
      }, "*");
      return;
    }
    window.parent.postMessage({
      protocol: P, id: message.id, kind: "response", ok: true,
      result: { ready: true, plugin_id: ID, api_version: "1.0" }
    }, "*");
  });
})();
""" % CALLER_ID

PROVIDER_JS = """
(function () {
  "use strict";
  var P = "jzo-plugin/1";
  var ID = "%(id)s";
  var ECHO = "%(echo)s";
  var TAGS = "%(tags)s";
  var DESTRUCTIVE = "%(destructive)s";
  var SLOW = "%(slow)s";
  var BIG = "%(big)s";
  var KNOWN = [ECHO, TAGS, DESTRUCTIVE, SLOW, BIG];
  var runs = [];
  var timeline = [];
  var slowSeq = 0;
  var seq = 0;
  var pending = {};
  var mark = document.getElementById("mark");
  mark.textContent = "PROVIDER:IDLE";

  window.probeState = function () {
    return { runs: runs.slice(), timeline: timeline.slice(), mark: mark.textContent };
  };
  // 环路判据要由提供方自己发起一跳：走与正式插件完全相同的 request/response 通道。
  window.probeCall = function (method, payload) {
    return new Promise(function (resolve) {
      seq += 1;
      var requestId = "q" + seq + "_" + Date.now().toString(36);
      pending[requestId] = resolve;
      window.parent.postMessage({
        protocol: P, id: requestId, kind: "request", method: method, payload: payload || {}
      }, "*");
    });
  };

  function respond(id, result) {
    window.parent.postMessage({
      protocol: P, id: id, kind: "response", ok: true, result: result
    }, "*");
  }

  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== P) return;
    if (message.kind === "response") {
      var settle = pending[message.id];
      if (!settle) return;
      delete pending[message.id];
      settle(message.ok
        ? { ok: true, result: message.result }
        : { ok: false, error: message.error });
      return;
    }
    if (message.kind !== "request") return;
    if (message.method === "command.execute") {
      var payload = message.payload || {};
      if (KNOWN.indexOf(payload.command_id) < 0) {
        window.parent.postMessage({
          protocol: P, id: message.id, kind: "response", ok: false,
          error: { code: "UNKNOWN_COMMAND", message: "未声明：" + String(payload.command_id || "") }
        }, "*");
        return;
      }
      // 只记真收到的报文：context 保真、from 是否调用方、trace 是否宿主盖章。
      runs.push({
        command_id: payload.command_id,
        context: payload.context,
        from: payload.from,
        trace: payload.trace
      });
      mark.textContent = "RUN:" + payload.command_id + ":" + runs.length;
      if (payload.command_id === SLOW) {
        // 1.5 秒后才回：宿主应在 1 秒处发 command.pending，且两条 slow 必须串行。
        slowSeq += 1;
        var ticket = slowSeq;
        timeline.push({ ticket: ticket, phase: "start", at: Date.now() });
        window.setTimeout(function () {
          timeline.push({ ticket: ticket, phase: "end", at: Date.now() });
          respond(message.id, { command_id: SLOW, ticket: ticket, count: runs.length });
        }, 1500);
        return;
      }
      if (payload.command_id === BIG) {
        // 目标真的执行了，回包故意做成 70000 字符：宿主必须在交给调用方之前拦下。
        respond(message.id, { command_id: BIG, blob: new Array(70001).join("x") });
        return;
      }
      respond(message.id, {
        command_id: payload.command_id,
        got: payload.context,
        from: payload.from,
        trace: payload.trace,
        count: runs.length
      });
      return;
    }
    respond(message.id, { ready: true, plugin_id: ID, api_version: "1.0" });
  });
})();
""" % {
    "id": PROVIDER_ID, "echo": PROVIDER_ECHO, "tags": PROVIDER_TAGS,
    "destructive": PROVIDER_DESTRUCTIVE, "slow": PROVIDER_SLOW, "big": PROVIDER_BIG,
}

PANEL_JS = """
(function () {
  "use strict";
  var P = "jzo-plugin/1";
  var ID = "%(id)s";
  var CMD = "%(cmd)s";
  var runs = [];
  var mark = document.getElementById("mark");
  mark.textContent = "PANEL:IDLE";

  window.probeState = function () {
    return { runs: runs.slice(), mark: mark.textContent };
  };

  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== P) return;
    if (message.kind !== "request") return;
    if (message.method === "command.execute") {
      var payload = message.payload || {};
      if (payload.command_id !== CMD) {
        window.parent.postMessage({
          protocol: P, id: message.id, kind: "response", ok: false,
          error: { code: "UNKNOWN_COMMAND", message: "未声明：" + String(payload.command_id || "") }
        }, "*");
        return;
      }
      runs.push({ command_id: payload.command_id, from: payload.from, trace: payload.trace });
      mark.textContent = "PANEL:RUN:" + runs.length;
      window.parent.postMessage({
        protocol: P, id: message.id, kind: "response", ok: true,
        result: { panel: true, count: runs.length, from: payload.from }
      }, "*");
      return;
    }
    window.parent.postMessage({
      protocol: P, id: message.id, kind: "response", ok: true,
      result: { ready: true, plugin_id: ID, api_version: "1.0" }
    }, "*");
  });
})();
""" % {"id": PANEL_ID, "cmd": PANEL_FLASH}

CAP_JS = """
(function () {
  "use strict";
  var P = "jzo-plugin/1";
  var CMD = "%(cmd)s";
  var runs = 0;
  var mark = document.getElementById("mark");
  mark.textContent = "CAP:IDLE";
  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== P) return;
    if (message.kind !== "request") return;
    if (message.method === "command.execute") {
      runs += 1;
      mark.textContent = "CAP:RUN:" + runs;
      window.parent.postMessage({
        protocol: P, id: message.id, kind: "response", ok: true,
        result: { ran: true, command_id: CMD, count: runs }
      }, "*");
      return;
    }
    window.parent.postMessage({
      protocol: P, id: message.id, kind: "response", ok: true,
      result: { ready: true, api_version: "1.0" }
    }, "*");
  });
})();
"""


def manifest(plugin_id: str, name: str, description: str, commands=None,
             slots=None, capabilities=None, with_stage: bool = True) -> dict:
    data = {
        "schema_version": "1.0",
        "id": plugin_id,
        "name": name,
        "version": "1.0.0",
        "api_version": "1.0",
        "kind": "tool",
        "description": description,
        "author": "九章算子",
        "license": "Apache-2.0",
        "entry": {"frontend": "dist/index.html"},
        "slots": slots or ["stage.center"],
        "capabilities": capabilities or ["question.render"],
        "permissions": [],
        "bus": {"subscribe": [], "publish": []},
        "min_host_version": "0.9.0",
        "engine": {"host_version": HOST_VERSION},
    }
    if with_stage:
        data["stage"] = {"region": "center", "mode": "takeover", "title": name,
                         "priority": 5, "singleton": False, "weight": "light"}
    if commands is not None:
        data["contributes"] = {"commands": commands}
    return data


def build_zip(plugin_id: str, name: str, description: str, script: str, commands=None,
              slots=None, capabilities=None, with_stage: bool = True) -> bytes:
    """zip 最外层目录名 == id，与老师拖装的包同形同校验。"""
    body = manifest(plugin_id, name, description, commands, slots, capabilities, with_stage)
    html = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        f"<title>{name}</title></head><body><p id=\"mark\">HTML-ONLY</p>"
        '<script src="./plugin.js"></script></body></html>'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{plugin_id}/plugin.json", json.dumps(body, ensure_ascii=False, indent=2))
        zf.writestr(f"{plugin_id}/dist/index.html", html)
        zf.writestr(f"{plugin_id}/dist/plugin.js", script)
        zf.writestr(f"{plugin_id}/LICENSE", (ROOT / "LICENSE").read_text(encoding="utf-8"))
    return buf.getvalue()


def api_status(method: str, path: str, body=None, blob: bytes | None = None) -> tuple[int, dict]:
    data = blob if blob is not None else (
        json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None)
    request = urllib.request.Request(ORIGIN + path, data=data, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("X-JZO-Token", TOKEN)
    if data is not None and blob is None:
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


def wait_port(deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


def frame_of(page, plugin_id: str):
    for frame in page.frames:
        if f"/plugin-assets/{plugin_id}/" in (frame.url or ""):
            return frame
    return None


def wait_frame(page, plugin_id: str, deadline_seconds: float = 20):
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        frame = frame_of(page, plugin_id)
        if frame is not None:
            try:
                if frame.evaluate("() => typeof window.probeCall === 'function' "
                                  "|| typeof window.probeState === 'function'"):
                    return frame
            except Exception:  # noqa: BLE001 - iframe 刚挂上还没跑脚本，下一轮再看
                pass
        page.wait_for_timeout(300)
    return None


def poll_result(caller, tag: str, deadline_seconds: float = 15):
    """轮询调用方页面里登记的 Promise 结果：对话框要边等边点，不能卡住 evaluate。"""
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        try:
            value = caller.evaluate("(tag) => window.probeResult(tag)", tag)
        except Exception:  # noqa: BLE001 - iframe 正在导航或已被摘掉，下一轮再看
            value = None
        if value is not None:
            return value
        time.sleep(0.1)
    return None


def wait_notifications(caller, predicate, deadline_seconds: float = 6):
    deadline = time.time() + deadline_seconds
    items = []
    while time.time() < deadline:
        items = caller.evaluate("() => window.probeNotifications()")
        if any(predicate(item) for item in items):
            return items
        time.sleep(0.1)
    return items


def dialog_info(page):
    return page.evaluate("""
    () => {
      const box = document.querySelector('.ws-dialog');
      if (!box) return null;
      const title = box.querySelector('.ws-dialog-title');
      const lede = box.querySelector('.ws-dialog-lede');
      return {
        title: title ? title.textContent : '',
        message: lede ? lede.textContent : '',
        buttons: Array.from(box.querySelectorAll('.ws-dialog-tools button'))
          .map(btn => btn.textContent.trim()),
        focus: document.activeElement ? String(document.activeElement.textContent || '').trim() : ''
      };
    }
    """)


def wait_dialog(page, deadline_seconds: float = 8):
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        info = dialog_info(page)
        if info:
            return info
        page.wait_for_timeout(100)
    return None


def click_dialog(page, index: int) -> bool:
    return page.evaluate("""
    (index) => {
      const buttons = document.querySelectorAll('.ws-dialog-tools button');
      if (!buttons[index]) return false;
      buttons[index].click();
      return true;
    }
    """, index)


def dump(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "command_registry_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    work = out / "isolated"
    data_dir, plugins_dir = work / "data", work / "plugins"
    for path in (data_dir, plugins_dir):
        path.mkdir(parents=True, exist_ok=True)

    checks: list[dict] = []
    evidence: dict = {}
    raw: dict = {}
    crashed: list[str] = []

    def call(method: str, path: str, body=None, blob: bytes | None = None, key: str = ""):
        status, payload = api_status(method, path, body=body, blob=blob)
        raw[key or f"{method} {path}"] = {"status": status, "payload": payload}
        return status, payload

    def check(name: str, passed, detail="") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": str(detail)[:500]})

    server = None
    browser = None
    pw = None
    try:
        with socket.socket() as probe:
            occupied = probe.connect_ex(("127.0.0.1", PORT)) == 0
        check(f"00 端口 {PORT} 空闲（本探针独占，绝不打到别人的底座）", not occupied,
              "端口已被占用：上一轮孤儿进程还在，本轮红绿都不算数" if occupied else "OK")
        if occupied:
            raise RuntimeError("port occupied")

        env = dict(os.environ)
        env["JZO_DATA_DIR"] = str(data_dir)
        env["JZO_PLUGINS_DIR"] = str(plugins_dir)
        env["JZO_STATE_FILE"] = str(data_dir / "workspaces" / "default" / "plugin_state.json")
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env["JZO_RESTART_DISABLED"] = "1"
        env.pop("JZO_AI_API_KEY", None)
        env.pop("JZO_AI_BASE_URL", None)
        log_path = out / "host.log"
        server = subprocess.Popen(
            [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(PORT)],
            cwd=str(ROOT), env=env, stdout=log_path.open("wb"), stderr=subprocess.STDOUT)
        check("01 隔离底座起来了", wait_port(60), f"log={log_path}")

        status, installed_caller = call(
            "POST", "/api/plugins/install?replace=true",
            blob=build_zip(CALLER_ID, "命令调用方", "只用于能力路由字典取证的调用方夹具",
                           CALLER_JS, [{"id": CALLER_PING, "title": "ping"}]),
            key="install_caller")
        check("02 调用方夹具装上（自带 com.example.cmd-caller.ping）",
              status == 200 and installed_caller.get("installed") is True,
              installed_caller.get("detail") or installed_caller.get("plugin", {}).get("id"))

        provider_script = PROVIDER_JS
        status, installed_provider = call(
            "POST", "/api/plugins/install?replace=true",
            blob=build_zip(
                PROVIDER_ID, "命令提供方", "只用于能力路由字典取证的提供方夹具", provider_script,
                [
                    {"id": PROVIDER_ECHO, "title": "回显上下文"},
                    {"id": PROVIDER_TAGS, "title": "整理标签"},
                    {"id": PROVIDER_DESTRUCTIVE, "title": "批量删改", "requires_user": True},
                    {"id": PROVIDER_SLOW, "title": "慢命令"},
                    {"id": PROVIDER_BIG, "title": "超大回包"},
                    {"id": OFFICIAL_CLAIM, "title": "越权抢官方名"},
                ]),
            key="install_provider")
        check("03 提供方夹具装上（声明六条命令，其中一条越权、一条高副作用）",
              status == 200 and installed_provider.get("installed") is True,
              installed_provider.get("detail", ""))

        status, installed_panel = call(
            "POST", "/api/plugins/install?replace=true",
            blob=build_zip(
                PANEL_ID, "右栏命令面板", "只用于 sidebar.right 命令转发取证的面板夹具",
                PANEL_JS, [{"id": PANEL_FLASH, "title": "面板高亮"}],
                slots=["sidebar.right"], capabilities=["assistant.chat"], with_stage=False),
            key="install_panel")
        check("03b 右栏面板夹具装上（sidebar.right + assistant.chat，成为默认住户）",
              status == 200 and installed_panel.get("installed") is True,
              installed_panel.get("detail", ""))

        status, listing = call("GET", "/api/plugins", key="plugins")
        plugins = {item.get("id"): item for item in listing.get("plugins", [])}
        provider_entry = plugins.get(PROVIDER_ID, {})
        provider_cmds = [item.get("id") for item in provider_entry.get("commands") or []]
        evidence["provider_commands"] = provider_cmds
        check("04 /api/plugins 里提供方只登记五条合法命令，越权的那条不进清单",
              provider_cmds == [PROVIDER_ECHO, PROVIDER_TAGS, PROVIDER_DESTRUCTIVE,
                                PROVIDER_SLOW, PROVIDER_BIG], provider_cmds)

        rejected = listing.get("commands_rejected") or []
        evidence["commands_rejected"] = rejected
        official_issue = next((item for item in rejected
                               if item.get("id") == OFFICIAL_CLAIM), {})
        check("05 越权声明逐条记账：commands_rejected 指明官方命名空间只给官方插件",
              official_issue.get("plugin_id") == PROVIDER_ID
              and "官方" in str(official_issue.get("reason")), official_issue)

        registry_ids = [item.get("id") for item in listing.get("commands") or []]
        evidence["registry_ids"] = registry_ids
        check("06 全局字典同时收进调用方、提供方与右栏面板的命令（同源 /api/plugins）",
              registry_ids == sorted([CALLER_PING, PANEL_FLASH, PROVIDER_ECHO, PROVIDER_TAGS,
                                      PROVIDER_DESTRUCTIVE, PROVIDER_SLOW, PROVIDER_BIG]),
              registry_ids)
        destructive_entry = next((item for item in listing.get("commands") or []
                                  if item.get("id") == PROVIDER_DESTRUCTIVE), {})
        check("06b 字典条目把 requires_user 原样带给前端（其余命令为 false）",
              destructive_entry.get("requires_user") is True
              and all(item.get("requires_user") is False
                      for item in listing.get("commands") or []
                      if item.get("id") != PROVIDER_DESTRUCTIVE),
              destructive_entry)

        pw = sync_playwright().start()
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 860})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(WORKSPACE, wait_until="networkidle")
        page.wait_for_timeout(1500)

        # 只开调用方：提供方此刻没有页签，正好验「命令自动开页」。
        opened = page.evaluate(JS_OPEN, CALLER_ID)
        caller = wait_frame(page, CALLER_ID)
        check("07 只手动打开调用方页签，提供方此时没有 iframe（右栏面板是自动住户）",
              opened and caller is not None and frame_of(page, PROVIDER_ID) is None,
              [f.url for f in page.frames if "/plugin-assets/" in (f.url or "")])
        check("08 调用方 iframe 就绪并暴露 probeCall（走真实 postMessage 通道）",
              caller is not None, caller.url if caller else "NO_FRAME")

        panel_frame = wait_frame(page, PANEL_ID, 20)
        check("08b 右栏默认住户是面板夹具（sidebar.right 已挂载，不占画布页签）",
              panel_frame is not None
              and page.evaluate(
                  "() => !document.querySelector('.ws-tab[data-tab=\"plugin:" + PANEL_ID + "\"]')"),
              panel_frame.url if panel_frame else "NO_FRAME")

        listed = caller.evaluate("() => window.probeCall('command.list')")
        listed_ids = [item.get("id") for item in (listed.get("result") or {}).get("commands") or []]
        evidence["command_list"] = listed
        expected_ids = sorted([CALLER_PING, PANEL_FLASH, PROVIDER_ECHO, PROVIDER_TAGS,
                               PROVIDER_DESTRUCTIVE, PROVIDER_SLOW, PROVIDER_BIG])
        check("09 command.list 当场列出宿主内存字典（含面板命令，不含越权命令）",
              listed.get("ok") is True and listed_ids == expected_ids, listed_ids)
        owner = next((item for item in (listed.get("result") or {}).get("commands") or []
                      if item.get("id") == PROVIDER_ECHO), {})
        check("10 字典条目带归属插件（id 与显示名），调用方不必猜目标",
              owner.get("plugin_id") == PROVIDER_ID and owner.get("plugin_name") == "命令提供方",
              owner)

        first = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                {"command_id": PROVIDER_ECHO, "context": CONTEXT})
        evidence["execute_first"] = first
        wrapper = first.get("result") or {}
        echoed = (wrapper.get("result") or {})
        check("11 command.execute 精准调度到未打开的提供方，context 逐字段原样到达",
              first.get("ok") is True
              and wrapper.get("command_id") == PROVIDER_ECHO
              and wrapper.get("plugin_id") == PROVIDER_ID
              and echoed.get("got") == CONTEXT, wrapper)

        check("12 目标 iframe 由宿主现开现等，调用方没有自己找过任何页签",
              frame_of(page, PROVIDER_ID) is not None,
              [f.url for f in page.frames if "/plugin-assets/" in (f.url or "")])
        dock = page.evaluate(JS_STATE)["dock"]
        evidence["dock"] = dock[-6:]
        check("13 底栏说明宿主为命令自动开了画布页（可解释、不偷袭）",
              any("已为它开一个画布页" in line for line in dock), dock[-1] if dock else "")

        provider = wait_frame(page, PROVIDER_ID)
        state = provider.evaluate("() => window.probeState()") if provider else {}
        evidence["provider_state_1"] = state
        run1 = (state.get("runs") or [{}])[0]
        check("14 提供方真的执行了一次，from 是调用方、trace 由宿主盖章",
              len(state.get("runs") or []) == 1
              and run1.get("context") == CONTEXT
              and run1.get("from") == CALLER_ID
              and run1.get("trace") == [PROVIDER_ID],
              {"runs": len(state.get("runs") or []), "from": run1.get("from"),
               "trace": run1.get("trace")})
        check("15 DOM 标记由目标脚本自己写出（执行痕迹不是宿主伪造的）",
              "RUN:%s:1" % PROVIDER_ECHO in str(state.get("mark")), state.get("mark"))

        second = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                 {"command_id": PROVIDER_TAGS,
                                  "context": {"tags": ["函数", "单调性"]}})
        evidence["execute_second"] = second
        state2 = provider.evaluate("() => window.probeState()")
        evidence["provider_state_2"] = state2
        check("16 第二条命令复用已就绪的页签（不重开、计数累加）",
              second.get("ok") is True
              and len(state2.get("runs") or []) == 2
              and (state2.get("runs") or [{}])[1].get("command_id") == PROVIDER_TAGS,
              {"count": len(state2.get("runs") or []), "mark": state2.get("mark")})

        unknown = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                  {"command_id": "com.example.nobody.ghost", "context": {}})
        evidence["unknown"] = unknown
        check("17 未知命令回 COMMAND_NOT_FOUND，不静默、不猜目标",
              unknown.get("ok") is False
              and (unknown.get("error") or {}).get("code") == "COMMAND_NOT_FOUND", unknown.get("error"))

        claim = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                {"command_id": OFFICIAL_CLAIM, "context": {}})
        evidence["official_claim"] = claim
        check("18 第三方调官方命名空间的命令同样查无此条（越权声明从未生效）",
              claim.get("ok") is False
              and (claim.get("error") or {}).get("code") == "COMMAND_NOT_FOUND", claim.get("error"))

        malformed = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                    {"command_id": "Not.-A.Command!", "context": {}})
        evidence["malformed"] = malformed
        check("19 形状不对的命令 id 回 BAD_REQUEST（连查表都不进）",
              malformed.get("ok") is False
              and (malformed.get("error") or {}).get("code") == "BAD_REQUEST", malformed.get("error"))

        oversized = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                    {"command_id": PROVIDER_ECHO, "context": {"blob": "x" * 17000}})
        evidence["oversized"] = oversized
        check("20 context 超过 16384 字符回 BAD_REQUEST，不把大包塞进 iframe",
              oversized.get("ok") is False
              and (oversized.get("error") or {}).get("code") == "BAD_REQUEST", oversized.get("error"))

        loop = provider.evaluate("(args) => window.probeCall('command.execute', args)",
                                 {"command_id": CALLER_PING, "context": {},
                                  "trace": ["a", "b", "c", "d"]})
        evidence["loop"] = loop
        check("21 伪造满链的 trace 回 COMMAND_LOOP，转发在出发前被截断",
              loop.get("ok") is False
              and (loop.get("error") or {}).get("code") == "COMMAND_LOOP", loop.get("error"))

        # ---- 调用安全加固（军令 #19 第三部分 Round 2）----
        caller.evaluate("(args) => window.probeStart(args.tag, args.method, args.payload)",
                        {"tag": "deny", "method": "command.execute",
                         "payload": {"command_id": PROVIDER_DESTRUCTIVE,
                                     "context": {"scope": "整卷"}}})
        deny_dialog = wait_dialog(page)
        evidence["deny_dialog"] = deny_dialog
        deny_text = (deny_dialog or {}).get("message") or ""
        check("22 高副作用命令先弹当场确认：文案点名调用方、命令与处理方，默认焦点在「允许执行」",
              deny_dialog is not None
              and "命令调用方" in deny_text and "批量删改" in deny_text
              and PROVIDER_DESTRUCTIVE in deny_text and "命令提供方" in deny_text
              and deny_dialog.get("buttons") == ["拒绝", "允许执行"]
              and deny_dialog.get("focus") == "允许执行", deny_dialog)

        clicked_deny = click_dialog(page, 0)
        denied = poll_result(caller, "deny")
        state_after_deny = provider.evaluate("() => window.probeState()")
        evidence["denied"] = denied
        check("23 点「拒绝」回 COMMAND_DENIED，请求根本没落到目标插件（runs 不增）",
              clicked_deny and denied is not None and denied.get("ok") is False
              and (denied.get("error") or {}).get("code") == "COMMAND_DENIED"
              and len(state_after_deny.get("runs") or []) == 2,
              {"error": (denied or {}).get("error"),
               "runs": len(state_after_deny.get("runs") or [])})

        caller.evaluate("(args) => window.probeStart(args.tag, args.method, args.payload)",
                        {"tag": "allow", "method": "command.execute",
                         "payload": {"command_id": PROVIDER_DESTRUCTIVE,
                                     "context": {"scope": "整卷"}}})
        allow_dialog = wait_dialog(page)
        clicked_allow = click_dialog(page, 1)
        allowed = poll_result(caller, "allow")
        state_after_allow = provider.evaluate("() => window.probeState()")
        evidence["allowed"] = allowed
        check("24 点「允许执行」才真正转发：参数原样到达，目标记下第三个 run",
              allow_dialog is not None and clicked_allow
              and allowed is not None and allowed.get("ok") is True
              and (allowed.get("result") or {}).get("plugin_id") == PROVIDER_ID
              and ((allowed.get("result") or {}).get("result") or {}).get("count") == 3
              and len(state_after_allow.get("runs") or []) == 3
              and (state_after_allow.get("runs") or [{}])[2].get("command_id")
              == PROVIDER_DESTRUCTIVE,
              {"count": ((allowed or {}).get("result") or {}).get("result"),
               "runs": len(state_after_allow.get("runs") or [])})

        panel_before = panel_frame.evaluate("() => window.probeState()")
        panel_call = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                     {"command_id": PANEL_FLASH, "context": {"panel": True}})
        panel_after = panel_frame.evaluate("() => window.probeState()")
        panel_tab = page.evaluate(
            "(id) => !!document.querySelector('.ws-tab[data-tab=\"plugin:' + id + '\"]')", PANEL_ID)
        panel_dock = [line for line in page.evaluate(JS_STATE)["dock"]
                      if "右栏命令面板" in line]
        panel_wrapper = panel_call.get("result") or {}
        panel_result = panel_wrapper.get("result") or {}
        evidence["panel_call"] = panel_call
        check("25 sidebar.right 面板目标直接投递：不进画布、不占页签、底栏不报开页",
              panel_call.get("ok") is True
              and panel_wrapper.get("plugin_id") == PANEL_ID
              and panel_result.get("panel") is True
              and panel_result.get("from") == CALLER_ID
              and len(panel_after.get("runs") or []) == len(panel_before.get("runs") or []) + 1
              and panel_after.get("mark") == "PANEL:RUN:%d" % len(panel_after.get("runs") or [])
              and panel_tab is False and panel_dock == [],
              {"wrapper": panel_wrapper, "tab": panel_tab, "dock": panel_dock})

        caller.evaluate("(args) => window.probeStart(args.tag, args.method, args.payload)",
                        {"tag": "slow1", "method": "command.execute",
                         "payload": {"command_id": PROVIDER_SLOW, "context": {"seq": 1}}})
        notes = wait_notifications(
            caller, lambda item: item.get("command_id") == PROVIDER_SLOW, 6)
        slow1 = poll_result(caller, "slow1")
        dock_slow = page.evaluate(JS_STATE)["dock"]
        evidence["notifications"] = notes
        slow1_result = (slow1 or {}).get("result") or {}
        check("26 慢命令超过 1 秒先发 command.pending 通知并在底栏记账，请求本身继续等回包",
              slow1 is not None and slow1.get("ok") is True
              and any(item.get("code") == "COMMAND_PENDING"
                      and item.get("target_plugin_id") == PROVIDER_ID for item in notes)
              and any("超过 1 秒未回" in line for line in dock_slow)
              and (slow1_result.get("result") or {}).get("ticket") == 1,
              {"ticket": slow1_result.get("result"), "notifications": len(notes)})

        for tag, seq in (("slowA", 2), ("slowB", 3)):
            caller.evaluate("(args) => window.probeStart(args.tag, args.method, args.payload)",
                            {"tag": tag, "method": "command.execute",
                             "payload": {"command_id": PROVIDER_SLOW, "context": {"seq": seq}}})
        slow_a = poll_result(caller, "slowA", 20)
        slow_b = poll_result(caller, "slowB", 20)
        state_slow = provider.evaluate("() => window.probeState()")
        timeline = state_slow.get("timeline") or []
        tail = timeline[-4:]
        serial_ok = (len(tail) == 4
                     and [item.get("phase") for item in tail]
                     == ["start", "end", "start", "end"]
                     and [item.get("ticket") for item in tail] == [2, 2, 3, 3]
                     and int(tail[2].get("at") or 0) >= int(tail[1].get("at") or 0))
        evidence["timeline"] = timeline
        check("27 同一目标的并发命令按队列串行：第二条在第一条回包之后才开跑",
              slow_a is not None and slow_a.get("ok") is True
              and slow_b is not None and slow_b.get("ok") is True
              and serial_ok, {"tail": tail,
                              "ok": [slow_a is not None and slow_a.get("ok"),
                                     slow_b is not None and slow_b.get("ok")]})

        big = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                              {"command_id": PROVIDER_BIG, "context": {}})
        big_error = big.get("error") or {}
        state_big = provider.evaluate("() => window.probeState()")
        evidence["big"] = big
        check("28 目标回了 70 KB 结果：宿主在交给调用方之前按 64 KB 上限拦下",
              big.get("ok") is False
              and big_error.get("code") == "COMMAND_RESULT_TOO_LARGE"
              and "65536" in str(big_error.get("message"))
              and (state_big.get("runs") or [{}])[-1].get("command_id") == PROVIDER_BIG,
              {"error": big_error, "runs": len(state_big.get("runs") or [])})

        page.screenshot(path=str(out / "final_state.png"), full_page=True)
        check("29 全程宿主页零未捕获 JS 错误", not errors, errors[:2])

        status, uninstalled = call("DELETE", f"/api/plugins/{PROVIDER_ID}?keep_data=true",
                                   key="uninstall")
        page.wait_for_timeout(6500)   # 前端 5 秒轮询整表替换字典
        after_uninstall = caller.evaluate("() => window.probeCall('command.list')")
        after_ids = [item.get("id") for item in
                     (after_uninstall.get("result") or {}).get("commands") or []]
        evidence["after_uninstall"] = after_uninstall
        check("30 卸载后字典当场退场：command.list 只剩调用方与右栏面板的命令",
              status == 200 and after_ids == sorted([CALLER_PING, PANEL_FLASH]), after_ids)
        gone = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                               {"command_id": PROVIDER_ECHO, "context": {}})
        evidence["execute_after_uninstall"] = gone
        check("31 卸载后旧命令回 COMMAND_NOT_FOUND（不留幽灵路由）",
              gone.get("ok") is False
              and (gone.get("error") or {}).get("code") == "COMMAND_NOT_FOUND", gone.get("error"))
        check("32 隔离插件目录不留提供方代码",
              not (plugins_dir / PROVIDER_ID).exists(), str(plugins_dir))

        # ---- 自动开页上限：先关掉除调用方以外的插件页签，再装六支轻量夹具 ----
        closed = page.evaluate("""
        (keep) => {
          const tabs = Array.from(document.querySelectorAll('#wsTabs .ws-tab[data-tab^="plugin:"]'));
          let count = 0;
          tabs.forEach(btn => {
            if (btn.getAttribute('data-tab') === keep) return;
            const close = btn.querySelector('.ws-tab-close');
            if (close) { close.click(); count += 1; }
          });
          return count;
        }
        """, "plugin:" + CALLER_ID)
        page.wait_for_timeout(500)

        cap_ok = []
        for index, plugin_id in enumerate(CAP_IDS, start=1):
            command_id = CAP_COMMANDS[index - 1]
            status, installed_cap = call(
                "POST", "/api/plugins/install?replace=true",
                blob=build_zip(plugin_id, "自动开页夹具 %d" % index,
                               "只用于命令自动开页上限取证的轻量夹具",
                               CAP_JS % {"cmd": command_id},
                               [{"id": command_id, "title": "执行 %d" % index}]),
                key="install_cap_%d" % index)
            cap_ok.append(status == 200 and installed_cap.get("installed") is True)
        page.wait_for_timeout(6500)   # 等前端轮询把六条命令收进字典
        cap_listed = caller.evaluate("() => window.probeCall('command.list')")
        cap_ids = [item.get("id") for item in
                   (cap_listed.get("result") or {}).get("commands") or []]
        evidence["cap_ids"] = cap_ids
        check("33 六支轻量夹具装上并进字典（含关闭期间被自动开出来的旧页签不影响计数）",
              all(cap_ok) and all(command_id in cap_ids for command_id in CAP_COMMANDS),
              {"closed": closed, "listed": cap_ids})

        ran = []
        for index in range(5):
            outcome = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                      {"command_id": CAP_COMMANDS[index], "context": {}})
            ran.append(outcome.get("ok") is True)
        open_tabs = page.evaluate(
            "() => Array.from(document.querySelectorAll('#wsTabs .ws-tab[data-tab^=\"plugin:\"]'))"
            ".map(el => el.getAttribute('data-tab'))")
        cap_tabs = sorted(tab for tab in open_tabs
                          if tab != "plugin:" + CALLER_ID)
        check("34 前五条命令各自动开出一个画布页：命令开页数正好 5，调用方的页签不占名额",
              all(ran) and cap_tabs == sorted("plugin:" + cid for cid in CAP_IDS[:5]),
              {"ran": ran, "tabs": cap_tabs})

        sixth = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                                {"command_id": CAP_COMMANDS[5], "context": {}})
        sixth_tab = page.evaluate(
            "() => !!document.querySelector('.ws-tab[data-tab=\"plugin:" + CAP_IDS[5] + "\"]')")
        sixth_error = sixth.get("error") or {}
        evidence["sixth"] = sixth
        check("35 第六条命令撞上自动开页上限：回 COMMAND_LIMIT，且没有再开页签",
              sixth.get("ok") is False and sixth_error.get("code") == "COMMAND_LIMIT"
              and sixth_tab is False, {"error": sixth_error, "tab": sixth_tab})
    except Exception as exc:  # noqa: BLE001 - 崩了也要把已有判据带出去
        crashed.append(repr(exc))
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

    passed = sum(1 for item in checks if item["passed"])
    result = {"tag": tag, "total": len(checks), "passed": passed,
              "crashed": crashed, "checks": checks, "evidence": evidence, "raw_api": raw}
    dump(out / "probe.json", result)
    print(json.dumps({"total": result["total"], "passed": passed}, ensure_ascii=False))
    for item in checks:
        print(("PASS " if item["passed"] else "FAIL ") + item["name"] + " | " + item["detail"])
    if crashed:
        print("CRASHED " + " ; ".join(crashed))
    return result


if __name__ == "__main__":
    outcome = run(sys.argv[1] if len(sys.argv) > 1 else "run")
    sys.exit(0 if outcome["passed"] == outcome["total"] and not outcome["crashed"] else 1)

# -*- coding: utf-8 -*-
"""能力路由字典（Command Registry）真机取证：军令 #19 第二部分。

用法：``.venv/Scripts/python.exe tools/command_registry_probe.py <out_dir_tag>``
（脚本自己在 8786 起隔离服务，跑完关掉）

夹具两支，都在第三方命名空间（``com.example.*``）：

- ``com.example.cmd-provider``：清单里声明三条命令——``echo``、带下划线的
  ``with_tags``，以及一条**越权抢官方名**的 ``org.jiuzhang.action.output.export_word``。
  它把每次执行到的 ``command_id / context / from / trace`` 记在内存并写进 DOM
  ``RUN:<命令>:<次数>``，回包也原样带回。
- ``com.example.cmd-caller``：声明自己的 ``ping``，页面内暴露 ``probeCall``，
  由探针驱动它走 ``command.list`` / ``command.execute``——与真实插件同一条
  postMessage 通道，不注入任何宿主私有句柄。

判据覆盖：清单归一与越权丢弃 → ``/api/plugins`` 同源 → 宿主内存字典 →
目标页签未开时自动开页并等就绪 → context 原样到达、``from`` 是调用方 →
未知/越权/坏形状/超大上下文/伪造环路各自拿到明确错误码 → 卸载后字典同步退场。
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
CALLER_PING = "com.example.cmd-caller.ping"
PROVIDER_ECHO = "com.example.cmd-provider.echo"
PROVIDER_TAGS = "com.example.cmd-provider.with_tags"
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
  var runs = [];
  var seq = 0;
  var pending = {};
  var mark = document.getElementById("mark");
  mark.textContent = "PROVIDER:IDLE";

  window.probeState = function () {
    return { runs: runs.slice(), mark: mark.textContent };
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
      if (payload.command_id !== ECHO && payload.command_id !== TAGS) {
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
      window.parent.postMessage({
        protocol: P, id: message.id, kind: "response", ok: true,
        result: {
          command_id: payload.command_id,
          got: payload.context,
          from: payload.from,
          trace: payload.trace,
          count: runs.length
        }
      }, "*");
      return;
    }
    window.parent.postMessage({
      protocol: P, id: message.id, kind: "response", ok: true,
      result: { ready: true, plugin_id: ID, api_version: "1.0" }
    }, "*");
  });
})();
""" % {"id": PROVIDER_ID, "echo": PROVIDER_ECHO, "tags": PROVIDER_TAGS}


def manifest(plugin_id: str, name: str, description: str, commands=None) -> dict:
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
        "slots": ["stage.center"],
        "capabilities": ["question.render"],
        "permissions": [],
        "stage": {"region": "center", "mode": "takeover", "title": name,
                  "priority": 5, "singleton": False, "weight": "light"},
        "bus": {"subscribe": [], "publish": []},
        "min_host_version": "0.9.0",
        "engine": {"host_version": HOST_VERSION},
    }
    if commands is not None:
        data["contributes"] = {"commands": commands}
    return data


def build_zip(plugin_id: str, name: str, description: str, script: str, commands=None) -> bytes:
    """zip 最外层目录名 == id，与老师拖装的包同形同校验。"""
    body = manifest(plugin_id, name, description, commands)
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
                    {"id": OFFICIAL_CLAIM, "title": "越权抢官方名"},
                ]),
            key="install_provider")
        check("03 提供方夹具装上（声明三条命令，其中一条越权）",
              status == 200 and installed_provider.get("installed") is True,
              installed_provider.get("detail", ""))

        status, listing = call("GET", "/api/plugins", key="plugins")
        plugins = {item.get("id"): item for item in listing.get("plugins", [])}
        provider_entry = plugins.get(PROVIDER_ID, {})
        provider_cmds = [item.get("id") for item in provider_entry.get("commands") or []]
        evidence["provider_commands"] = provider_cmds
        check("04 /api/plugins 里提供方只登记两条合法命令，越权的那条不进清单",
              provider_cmds == [PROVIDER_ECHO, PROVIDER_TAGS], provider_cmds)

        rejected = listing.get("commands_rejected") or []
        evidence["commands_rejected"] = rejected
        official_issue = next((item for item in rejected
                               if item.get("id") == OFFICIAL_CLAIM), {})
        check("05 越权声明逐条记账：commands_rejected 指明官方命名空间只给官方插件",
              official_issue.get("plugin_id") == PROVIDER_ID
              and "官方" in str(official_issue.get("reason")), official_issue)

        registry_ids = [item.get("id") for item in listing.get("commands") or []]
        evidence["registry_ids"] = registry_ids
        check("06 全局字典同时收进调用方与提供方的命令（同源 /api/plugins）",
              registry_ids == sorted([CALLER_PING, PROVIDER_ECHO, PROVIDER_TAGS]),
              registry_ids)

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
        check("07 只打开调用方页签，提供方此时没有 iframe",
              opened and caller is not None and frame_of(page, PROVIDER_ID) is None,
              [f.url for f in page.frames if "/plugin-assets/" in (f.url or "")])
        check("08 调用方 iframe 就绪并暴露 probeCall（走真实 postMessage 通道）",
              caller is not None, caller.url if caller else "NO_FRAME")

        listed = caller.evaluate("() => window.probeCall('command.list')")
        listed_ids = [item.get("id") for item in (listed.get("result") or {}).get("commands") or []]
        evidence["command_list"] = listed
        check("09 command.list 当场列出宿主内存字典（含下划线命令，不含越权命令）",
              listed.get("ok") is True
              and listed_ids == [CALLER_PING, PROVIDER_ECHO, PROVIDER_TAGS],
              listed_ids)
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

        page.screenshot(path=str(out / "final_state.png"), full_page=True)
        check("22 全程宿主页零未捕获 JS 错误", not errors, errors[:2])

        status, uninstalled = call("DELETE", f"/api/plugins/{PROVIDER_ID}?keep_data=true",
                                   key="uninstall")
        page.wait_for_timeout(6500)   # 前端 5 秒轮询整表替换字典
        after_uninstall = caller.evaluate("() => window.probeCall('command.list')")
        after_ids = [item.get("id") for item in
                     (after_uninstall.get("result") or {}).get("commands") or []]
        evidence["after_uninstall"] = after_uninstall
        check("23 卸载后字典当场退场：command.list 只剩调用方自己的命令",
              status == 200 and after_ids == [CALLER_PING], after_ids)
        gone = caller.evaluate("(args) => window.probeCall('command.execute', args)",
                               {"command_id": PROVIDER_ECHO, "context": {}})
        evidence["execute_after_uninstall"] = gone
        check("24 卸载后旧命令回 COMMAND_NOT_FOUND（不留幽灵路由）",
              gone.get("ok") is False
              and (gone.get("error") or {}).get("code") == "COMMAND_NOT_FOUND", gone.get("error"))
        check("25 隔离插件目录不留夹具代码",
              not (plugins_dir / PROVIDER_ID).exists(), str(plugins_dir))
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

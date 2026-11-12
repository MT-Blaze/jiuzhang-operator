# -*- coding: utf-8 -*-
"""官方插件能力契约真机取证：军令 #20 第二部分。

用法：``.venv/Scripts/python.exe tools/command_contract_probe.py <out_dir_tag>``
（脚本自己在 8787 起隔离服务，跑完关掉；工作区数据与插件目录都在临时目录里）

取证对象是仓库里的五个官方插件，不装任何替身夹具（只额外装一个第三方调用方，
用来走真实的 postMessage / command.execute 通道）：

1. ``/api/plugins``：12 条命令、五类命名空间、requires_user 标记、说明与参数 schema 同源；
2. ``command.list`` 从调用方 iframe 查表：每条都带 description / params_schema / returns；
3. 无界面引擎命令经宿主转发回 ``COMMAND_HEADLESS``，不假装执行；
4. 录题命令用数据库行号冒充题目 id：插件按 ``q_`` 公开 id 口径拒绝；
5. 高副作用命令（保存当前题目）先弹确认卡，点「拒绝」回 ``COMMAND_DENIED``；
6. 设置页「命令能力字典」表头含「说明」，行数与字典一致且说明列非空。
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

import io
import os
import re
import shutil
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
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
PORT = 8787
ORIGIN = f"http://127.0.0.1:{PORT}"
TOKEN = "command-contract-probe-token"
CALLER_ID = "com.example.contract-caller"
CALLER_CMD = "com.example.contract-caller.ping"
OFFICIAL = [
    "org.jiuzhang.bank-engine",
    "org.jiuzhang.paper-gen",
    "org.jiuzhang.handout",
    "org.jiuzhang.editor",
]
EXPECTED_IDS = [
    "org.jiuzhang.action.data.bank_search",
    "org.jiuzhang.action.data.bank_stats",
    "org.jiuzhang.action.data.bank_topics",
    "org.jiuzhang.action.input.open_question",
    "org.jiuzhang.action.input.save_question",
    "org.jiuzhang.action.input.set_handout_markdown",
    "org.jiuzhang.action.output.export_handout",
    "org.jiuzhang.action.output.export_paper",
    "org.jiuzhang.action.process.clean_latex",
    "org.jiuzhang.action.process.create_variant",
    "org.jiuzhang.action.process.generate_paper",
    "org.jiuzhang.action.process.render_handout",
]
DATA_CMD = "org.jiuzhang.action.data.bank_stats"
SEARCH_CMD = "org.jiuzhang.action.data.bank_search"
CONFIRM_CMD = "org.jiuzhang.action.input.save_question"
OPEN_CMD = "org.jiuzhang.action.input.open_question"
HOST_VERSION = re.search(
    r'__version__\s*=\s*"([^"]+)"',
    (ROOT / "app" / "__init__.py").read_text(encoding="utf-8")).group(1)


def manifest_versions() -> dict[str, str]:
    """仓内清单的版本号——探针不许写死版本，否则插件一升号就把判据打成假红。"""
    return {plugin_id: toml_io.load(PLUGIN_SOURCE_DIR / plugin_id / "plugin.toml")["version"]
        for plugin_id in OFFICIAL}

CALLER_JS = """
(function () {
  "use strict";
  var P = "jzo-plugin/1";
  var seq = 0;
  var pending = {};
  var results = {};
  document.getElementById("mark").textContent = "CALLER:IDLE";

  window.probeCall = function (method, payload) {
    return new Promise(function (resolve) {
      seq += 1;
      var id = "c" + seq + "_" + Date.now().toString(36);
      pending[id] = resolve;
      window.parent.postMessage({
        protocol: P, id: id, kind: "request", method: method, payload: payload || {}
      }, "*");
    });
  };
  window.probeStart = function (tag, method, payload) {
    results[tag] = null;
    window.probeCall(method, payload).then(function (value) { results[tag] = value; });
  };
  window.probeResult = function (tag) { return results[tag]; };

  window.addEventListener("message", function (event) {
    var message = event.data;
    if (!message || message.protocol !== P) return;
    if (message.kind === "response") {
      var settle = pending[message.id];
      if (!settle) return;
      delete pending[message.id];
      settle(message.ok ? { ok: true, result: message.result }
                        : { ok: false, error: message.error });
      return;
    }
    if (message.kind !== "request") return;
    window.parent.postMessage({
      protocol: P, id: message.id, kind: "response", ok: true,
      result: { ready: true, plugin_id: "%s", api_version: "1.0" }
    }, "*");
  });
})();
""" % CALLER_ID


def caller_zip() -> bytes:
    manifest = {
        "schema_version": "1.0",
        "id": CALLER_ID,
        "name": "命令契约调用方",
        "version": "1.0.0",
        "api_version": "1.0",
        "kind": "tool",
        "description": "只用于官方插件能力契约取证的最小调用方",
        "author": "九章算子",
        "license": "Apache-2.0",
        "min_host_version": HOST_VERSION,
        "entry": {"frontend": "dist/index.html"},
        "slots": ["stage.center"],
        "capabilities": ["question.render"],
        "permissions": [],
        "stage": {"region": "center", "mode": "takeover", "title": "命令契约调用方",
                  "priority": 5, "singleton": False, "weight": "light"},
        "bus": {"subscribe": [], "publish": []},
        "contributes": {"commands": [{"id": CALLER_CMD, "title": "ping"}]},
    }
    html = ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"></head>'
            '<body><p id="mark">HTML-ONLY</p><script src="./plugin.js"></script></body></html>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{CALLER_ID}/plugin.toml", toml_io.dumps(manifest))
        zf.writestr(f"{CALLER_ID}/dist/index.html", html)
        zf.writestr(f"{CALLER_ID}/dist/plugin.js", CALLER_JS)
        zf.writestr(f"{CALLER_ID}/LICENSE", (ROOT / "LICENSE").read_text(encoding="utf-8"))
    return buf.getvalue()


def api_status(method: str, path: str, blob: bytes | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(ORIGIN + path, data=blob, method=method)
    request.add_header("Accept", "application/json")
    request.add_header("X-JZO-Token", TOKEN)
    if blob is not None:
        request.add_header("Content-Type", "application/octet-stream")
    try:
        with urllib.request.urlopen(request, timeout=120) as resp:
            return resp.status, wire.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            return error.code, wire.loads(raw)
        except wire.JSONDecodeError:
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
                if frame.evaluate("() => typeof window.probeCall === 'function'"):
                    return frame
            except Exception:  # noqa: BLE001 - iframe 正在挂载
                pass
        page.wait_for_timeout(250)
    return None


def poll_result(caller, tag: str, deadline_seconds: float = 15):
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        try:
            value = caller.evaluate("(tag) => window.probeResult(tag)", tag)
        except Exception:  # noqa: BLE001 - iframe 正在导航
            value = None
        if value is not None:
            return value
        time.sleep(0.1)
    return None


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
    path.write_text(toml_io.dumps(payload), encoding="utf-8")


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "command_contract_probe" / tag
    out.mkdir(parents=True, exist_ok=True)
    work = out / "isolated"
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir = work / "data", work / "plugins"
    for path in (data_dir, plugins_dir):
        path.mkdir(parents=True, exist_ok=True)
    for plugin_id in OFFICIAL:
        shutil.copytree(PLUGIN_SOURCE_DIR / plugin_id, plugins_dir / plugin_id)

    checks: list[dict] = []
    evidence: dict = {}
    raw: dict = {}
    crashed: list[str] = []

    def call(method: str, path: str, blob: bytes | None = None, key: str = ""):
        status, payload = api_status(method, path, blob=blob)
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
        check(f"00 端口 {PORT} 空闲", not occupied,
              "端口已被占用：上一轮孤儿进程还在" if occupied else "OK")
        if occupied:
            raise RuntimeError("port occupied")

        env = dict(os.environ)
        env["JZO_DATA_DIR"] = str(data_dir)
        env["JZO_PLUGINS_DIR"] = str(plugins_dir)
        env["JZO_STATE_FILE"] = str(data_dir / "workspaces" / "default" / "plugin_state.toml")
        env["JZO_LOCAL_TOKEN"] = TOKEN
        env["JZO_RESTART_DISABLED"] = "1"
        env.pop("JZO_AI_API_KEY", None)
        env.pop("JZO_AI_BASE_URL", None)
        log_path = out / "host.log"
        server = subprocess.Popen(
            [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(PORT)],
            cwd=str(ROOT), env=env, stdout=log_path.open("wb"), stderr=subprocess.STDOUT)
        check("01 隔离底座起来了（只装仓库里的五个官方插件）", wait_port(60), f"log={log_path}")

        status, listing = call("GET", "/api/plugins", key="plugins")
        commands = {item.get("id"): item for item in listing.get("commands") or []}
        evidence["registry_ids"] = sorted(commands)
        evidence["commands_rejected"] = listing.get("commands_rejected")
        check("02 /api/plugins 收齐五个官方插件的 14 条命令，零丢弃",
              status == 200 and sorted(commands) == EXPECTED_IDS
              and (listing.get("commands_rejected") or []) == [],
              {"ids": sorted(commands), "rejected": listing.get("commands_rejected")})
        check("03 每条命令都带说明、封口参数 schema 与返回摘要",
              all(item.get("description") and item.get("returns")
                  and isinstance(item.get("params_schema"), dict)
                  and item["params_schema"].get("type") == "object"
                  and item["params_schema"].get("additionalProperties") is False
                  for item in commands.values()),
              {cid: {"desc": len(item.get("description") or ""),
                     "schema": bool(item.get("params_schema")),
                     "returns": bool(item.get("returns"))}
               for cid, item in list(commands.items())[:3]})
        flagged = sorted(cid for cid, item in commands.items() if item.get("requires_user"))
        evidence["requires_user"] = flagged
        check("04 高副作用命令的确认标记与说明书一致（6 条）",
              flagged == sorted([
                  "org.jiuzhang.action.input.save_question",
                  "org.jiuzhang.action.input.set_handout_markdown",
                  "org.jiuzhang.action.output.export_handout",
                  "org.jiuzhang.action.output.export_paper",
                  "org.jiuzhang.action.process.clean_latex",
                  "org.jiuzhang.action.process.create_variant",
              ]), flagged)
        engine = next((item for item in listing.get("plugins") or []
                       if item.get("id") == "org.jiuzhang.bank-engine"), {})
        check("05 引擎是无界面插件且照常出现在字典里（headless + show_in_sidebar:false）",
              engine.get("headless") is True and engine.get("show_in_sidebar") is False
              and len(engine.get("commands") or []) == 3, engine.get("version"))
        check("06 五个官方插件版本与仓内清单一致",
              {item.get("id"): item.get("version") for item in listing.get("plugins") or []
               if item.get("id") in OFFICIAL} == manifest_versions(),
              {item.get("id"): item.get("version") for item in listing.get("plugins") or []})

        status, installed = call(
            "POST", "/api/plugins/install?replace=true", blob=caller_zip(), key="install_caller")
        check("07 第三方调用方夹具装上（自带一条 ping 命令）",
              status == 200 and installed.get("installed") is True,
              installed.get("detail") or installed.get("plugin", {}).get("id"))

        pw = sync_playwright().start()
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={"width": 1360, "height": 900})
        errors: list[str] = []
        page.on("pageerror", lambda exc: errors.append(str(exc)))
        page.goto(f"{ORIGIN}/workspace", wait_until="networkidle")
        page.wait_for_timeout(1500)
        page.evaluate("""
        async (pluginId) => {
          const resp = await fetch('/api/plugins', {cache: 'no-store'});
          const data = await resp.json();
          const plugin = (data.plugins || []).find(item => item.id === pluginId);
          window.JzoStage.openPlugin(plugin);
        }
        """, CALLER_ID)
        caller = wait_frame(page, CALLER_ID)
        check("08 调用方 iframe 就绪（真实 postMessage 通道）",
              caller is not None, caller.url if caller else "NO_FRAME")

        listed = caller.evaluate("() => window.probeCall('command.list')")
        listed_commands = (listed.get("result") or {}).get("commands") or []
        evidence["command_list"] = listed_commands[:3]
        official_listed = {item.get("id"): item for item in listed_commands
                           if item.get("id") in EXPECTED_IDS}
        check("09 command.list 对调用方公开官方命令的说明、schema 与返回值",
              listed.get("ok") is True and len(official_listed) == len(EXPECTED_IDS)
              and all(item.get("description") and item.get("returns")
                      and item.get("params_schema", {}).get("additionalProperties") is False
                      for item in official_listed.values()),
              len(official_listed))
        check("10 字典条目的提供方是纯后台引擎本身，不串号",
              official_listed.get(DATA_CMD, {}).get("plugin_id") == "org.jiuzhang.bank-engine"
              and official_listed.get(SEARCH_CMD, {}).get("plugin_id")
              == "org.jiuzhang.bank-engine",
              {cid: item.get("plugin_id") for cid, item in list(official_listed.items())[:3]})

        data_run = caller.evaluate(
            "(args) => window.probeCall('command.execute', args)",
            {"command_id": DATA_CMD, "context": {}})
        evidence["data_command"] = data_run
        check("11 无界面引擎不经 iframe 假装执行，回 COMMAND_HEADLESS 指路 Host API",
              data_run.get("ok") is False
              and (data_run.get("error") or {}).get("code") == "COMMAND_HEADLESS",
              data_run.get("error"))

        bad_id = caller.evaluate(
            "(args) => window.probeCall('command.execute', args)",
            {"command_id": OPEN_CMD, "context": {"question_id": "42"}})
        evidence["bad_id"] = bad_id
        bad_message = str(((bad_id.get("error") or {}).get("message")) or "")
        check("12 用数据库行号冒充题目 id 被插件按 q_ 公开 id 口径拒绝",
              bad_id.get("ok") is False and "q_" in bad_message,
              bad_id.get("error"))

        caller.evaluate("(args) => window.probeStart(args.tag, args.method, args.payload)",
                        {"tag": "confirm", "method": "command.execute",
                         "payload": {"command_id": CONFIRM_CMD,
                                     "context": {}}})
        confirm_dialog = wait_dialog(page)
        evidence["confirm_dialog"] = confirm_dialog
        confirm_text = (confirm_dialog or {}).get("message") or ""
        check("13 高副作用命令先弹确认卡：点名调用方、命令与目标插件",
              confirm_dialog is not None and "命令契约调用方" in confirm_text
              and "保存当前题目" in confirm_text and "录题工作台" in confirm_text,
              confirm_dialog)
        clicked = click_dialog(page, 0)
        denied = poll_result(caller, "confirm")
        evidence["confirm_denied"] = denied
        check("14 点「拒绝」回 COMMAND_DENIED，目标插件没有执行",
              clicked and denied is not None
              and (denied.get("error") or {}).get("code") == "COMMAND_DENIED",
              denied.get("error") if denied else "NO_RESULT")

        settings = browser.new_page(viewport={"width": 1360, "height": 900})
        settings.goto(f"{ORIGIN}/settings", wait_until="networkidle")
        settings.click("#stNavPlugin")
        settings.wait_for_selector("#cmdRegistryBody tr", timeout=15000)
        table = settings.evaluate("""
        () => ({
          headers: Array.from(document.querySelectorAll('#cmdRegistry thead th'))
            .map(th => th.textContent.trim()),
          rows: Array.from(document.querySelectorAll('#cmdRegistryBody tr')).map(tr => ({
            id: (tr.querySelector('.mg-cmd-id') || {}).textContent || '',
            desc: (tr.querySelector('.mg-cmd-desc') || {}).textContent || '',
            flag: (tr.querySelector('.mg-cmd-flag') || {}).textContent || ''
          }))
        })
        """)
        evidence["settings_table"] = {"headers": table["headers"], "rows": table["rows"][:4]}
        check("15 设置页字典表头含「说明」，13 条命令（12 官方 + 1 夹具）逐行渲染",
              table["headers"] == ["命令 id", "标题", "提供方", "说明", "执行前"]
              and len(table["rows"]) == len(EXPECTED_IDS) + 1
              and all(row["id"] for row in table["rows"])
              and all(row["desc"] for row in table["rows"]
                      if row["id"] in EXPECTED_IDS),
              {"headers": table["headers"], "rows": len(table["rows"])})
        check("16 设置页把高副作用命令标成「需确认」，只读命令标「直接执行」",
              next((row["flag"] for row in table["rows"] if row["id"] == CONFIRM_CMD), "") == "需确认"
              and next((row["flag"] for row in table["rows"] if row["id"] == DATA_CMD), "") == "直接执行",
              {row["id"]: row["flag"] for row in table["rows"][:4]})
        settings.screenshot(path=str(out / "settings_commands.png"), full_page=True)
        page.screenshot(path=str(out / "workspace_after_commands.png"), full_page=True)
        check("17 全程宿主页零未捕获 JS 错误", not errors, errors[:2])
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
    dump(out / "probe.toml", result)
    print(wire.dumps({"total": result["total"], "passed": passed}, ensure_ascii=False))
    for item in checks:
        print(("PASS " if item["passed"] else "FAIL ") + item["name"] + " | " + item["detail"])
    if crashed:
        print("CRASHED " + " ; ".join(crashed))
    return result


if __name__ == "__main__":
    outcome = run(sys.argv[1] if len(sys.argv) > 1 else "run")
    sys.exit(0 if outcome["passed"] == outcome["total"] and not outcome["crashed"] else 1)

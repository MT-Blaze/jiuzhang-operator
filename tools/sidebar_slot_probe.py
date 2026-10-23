# -*- coding: utf-8 -*-
"""右栏辅助面板（sidebar.right）真机取证（军令 #13 任务 3）。

用法：``.venv/Scripts/python.exe tools/sidebar_slot_probe.py <tag>``

隔离口径：``JZO_DATA_DIR`` 与 ``JZO_PLUGINS_DIR`` 都指向
``.system_generated/sidebar-slot-probe/<tag>/``，不碰开发者 ``data/`` 与仓库 ``plugins/``。
探针现场生成一个只声明 ``sidebar.right`` 的一次性插件，验完即弃（不进仓库）。

判据：
  1. 有插件认领插槽 → 右栏露出插槽、藏起 AI 副驾，标题为插件名；
  2. 面板 iframe 的 sandbox 为 ``allow-scripts allow-modals``（不得带 allow-same-origin）；
  3. ``plugin.activate`` 带 ``{"slot":"sidebar.right"}``，插件回 ready；
  4. 面板能走 Host API（``basket.list`` 往返成功）；
  5. 插件被停用后，右栏回退原生 AI 副驾，插槽整块隐藏；
  6. 宿主页零未捕获 JS 错误。
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8794
BASE = f"http://127.0.0.1:{PORT}/workspace"
PLUGIN_ID = "com.example.side-panel"

PLUGIN_HTML = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>右栏探针</title>
<style>
  body { margin: 0; padding: 12px; font: 13px/1.6 system-ui, sans-serif; color: #2b2b2b; }
  #root { font-weight: 600; margin-bottom: 8px; }
</style></head>
<body>
<div id="root">等待宿主激活…</div>
<div id="api">接口未连</div>
<script src="./plugin.js"></script>
</body></html>
"""

# 宿主 CSP 是 script-src 'self'：插件脚本必须落独立文件，内联脚本会被整段拦掉。
PLUGIN_JS = """(function () {
  "use strict";
  var PROTOCOL = "jzo-plugin/1";
  var seq = 0;

  function reply(id, ok, result) {
    parent.postMessage({ protocol: PROTOCOL, id: id, kind: "response", ok: ok, result: result || {} }, "*");
  }

  function request(method, payload) {
    return new Promise(function (resolve, reject) {
      var id = "p" + (++seq) + "_" + Date.now().toString(36);
      var timer = setTimeout(function () {
        window.removeEventListener("message", onMessage);
        reject(new Error("timeout"));
      }, 5000);
      function onMessage(event) {
        var data = event.data;
        if (!data || data.protocol !== PROTOCOL || data.kind !== "response" || data.id !== id) return;
        clearTimeout(timer);
        window.removeEventListener("message", onMessage);
        if (data.ok) resolve(data.result || {});
        else reject(new Error((data.error && data.error.message) || "failed"));
      }
      window.addEventListener("message", onMessage);
      parent.postMessage({
        protocol: PROTOCOL, id: id, kind: "request", method: method, payload: payload || {}
      }, "*");
    });
  }

  window.addEventListener("message", function (event) {
    var data = event.data;
    if (!data || data.protocol !== PROTOCOL) return;
    if (data.kind === "request" && data.method === "plugin.activate") {
      var slot = (data.payload && data.payload.slot) || "";
      document.body.setAttribute("data-slot", slot);
      document.getElementById("root").textContent = "面板已就绪";
      reply(data.id, true, { ready: true });
      request("basket.list", { expand: false }).then(function (result) {
        var total = typeof result.total === "number" ? result.total : 0;
        document.getElementById("api").textContent = "题篮 " + total + " 题";
      }, function (error) {
        document.getElementById("api").textContent = "接口失败：" + error.message;
      });
    }
  });
})();
"""

MANIFEST = {
    "schema_version": "1.0",
    "id": PLUGIN_ID,
    "name": "右栏探针",
    "version": "1.0.0",
    "api_version": "1.0",
    "kind": "renderer",
    "description": "军令 #13 任务 3 的一次性右栏插件",
    "license": "Apache-2.0",
    "entry": {"frontend": "dist/index.html"},
    "slots": ["sidebar.right"],
    "capabilities": ["question.render"],
    "permissions": ["questions:read"],
}


def wait_port(deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


def call(method: str, path: str, payload=None, token: str = "", port: int = PORT):
    import urllib.error
    import urllib.request

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("X-JZO-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload_text = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(payload_text or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": payload_text}


def build_plugin(plugins_dir: Path) -> None:
    target = plugins_dir / PLUGIN_ID
    (target / "dist").mkdir(parents=True, exist_ok=True)
    (target / "LICENSE").write_text("Apache License 2.0 (probe fixture)", encoding="utf-8")
    (target / "dist" / "index.html").write_text(PLUGIN_HTML, encoding="utf-8")
    (target / "dist" / "plugin.js").write_text(PLUGIN_JS, encoding="utf-8")
    (target / "plugin.json").write_text(json.dumps(MANIFEST, ensure_ascii=False, indent=2), encoding="utf-8")


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "sidebar-slot-probe" / tag
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    data_dir = out / "data"
    plugins_dir = out / "plugins"
    data_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)
    build_plugin(plugins_dir)

    report = {"tag": tag, "checks": [], "console": [], "errors": [], "shots": [], "notes": {}}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
        return bool(ok)

    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env.pop("JZO_AI_API_KEY", None)
    env.pop("JZO_AI_BASE_URL", None)

    server_log = open(out / "server.log", "w", encoding="utf-8", errors="replace")
    server = subprocess.Popen(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT), env=env, stdout=server_log, stderr=subprocess.STDOUT)
    try:
        if not wait_port(40):
            check("隔离服务启动", False, "40 秒内未监听")
            return finish(report, out)
        check("隔离服务启动", True, str(data_dir))

        status, listing = call("GET", "/api/plugins")
        ids = [item.get("id") for item in listing.get("plugins", [])]
        check("探针插件被后端接受（slots 含 sidebar.right）", status == 200 and PLUGIN_ID in ids,
              json.dumps(listing.get("rejected"), ensure_ascii=False)[:300])

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:300]}))
            page.on("pageerror", lambda e: report["errors"].append(str(e)[:300]))

            def snap(step):
                png = out / f"{step}.png"
                page.screenshot(path=str(png))
                report["shots"].append(str(png))

            page.goto(BASE, wait_until="networkidle")
            page.wait_for_selector("#wsContextSlotBody iframe", timeout=15000)
            page.wait_for_timeout(1500)
            state = page.evaluate("""() => {
              const slot = document.getElementById('wsContextSlot');
              const copilot = document.getElementById('wsCopilot');
              const frame = document.querySelector('#wsContextSlotBody iframe');
              return {
                slotHidden: slot ? slot.hidden : null,
                copilotHidden: copilot ? copilot.hidden : null,
                copilotDisplay: copilot ? getComputedStyle(copilot).display : null,
                title: (document.getElementById('wsContextSlotTitle') || {}).textContent || '',
                sandbox: frame ? frame.getAttribute('sandbox') : null,
                src: frame ? frame.getAttribute('src') : null,
                frameCount: document.querySelectorAll('#wsContextSlotBody iframe').length
              };
            }""")
            report["notes"]["initial"] = state
            snap("10-panel-mounted")

            check("有插件认领时插槽可见", state["slotHidden"] is False, json.dumps(state, ensure_ascii=False))
            check("AI 复驾让位（hidden + display:none）",
                  state["copilotHidden"] is True and state["copilotDisplay"] == "none",
                  f"hidden={state['copilotHidden']} display={state['copilotDisplay']}")
            check("插槽标题就是插件名", state["title"] == "右栏探针", state["title"])
            check("面板 iframe 沙箱为 allow-scripts allow-modals", state["sandbox"] == "allow-scripts allow-modals", str(state["sandbox"]))
            check("右栏只挂一个面板", state["frameCount"] == 1, str(state["frameCount"]))

            panel = page.frame_locator("#wsContextSlotBody iframe")
            panel.locator("#root").wait_for(timeout=10000)
            page.wait_for_timeout(600)
            inside = {
                "slot": panel.locator("body").get_attribute("data-slot"),
                "root": panel.locator("#root").inner_text(),
                "api": panel.locator("#api").inner_text(),
            }
            report["notes"]["inside"] = inside
            check("activate 收到 sidebar.right 且插件回 ready",
                  inside["slot"] == "sidebar.right" and inside["root"] == "面板已就绪",
                  json.dumps(inside, ensure_ascii=False))
            check("面板可走 Host API（basket.list 往返）", inside["api"] == "题篮 0 题", inside["api"])

            status, settings = call("GET", "/api/settings")
            token = (settings or {}).get("local_token", "")
            status, body = call("POST", f"/api/plugins/{PLUGIN_ID}/enabled", {"enabled": False}, token=token)
            check("插件可被停用（隔离库）", status == 200 and body.get("enabled") is False,
                  f"{status} {body}")
            page.reload(wait_until="networkidle")
            page.wait_for_timeout(1500)
            fallback = page.evaluate("""() => {
              const slot = document.getElementById('wsContextSlot');
              const copilot = document.getElementById('wsCopilot');
              return {
                slotHidden: slot ? slot.hidden : null,
                copilotHidden: copilot ? copilot.hidden : null,
                frames: document.querySelectorAll('#wsContextSlotBody iframe').length
              };
            }""")
            report["notes"]["fallback"] = fallback
            snap("20-fallback-copilot")
            check("停用后回退原生 AI 复驾",
                  fallback["copilotHidden"] is False and fallback["slotHidden"] is True
                  and fallback["frames"] == 0,
                  json.dumps(fallback, ensure_ascii=False))
            check("宿主页零未捕获 JS 错误", not report["errors"], json.dumps(report["errors"])[:300])
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
        server_log.close()
    return finish(report, out)


def finish(report: dict, out: Path) -> dict:
    passed = sum(1 for c in report["checks"] if c["ok"])
    report["passed"] = passed
    report["total"] = len(report["checks"])
    (out / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"passed {passed}/{len(report['checks'])} -> {out / 'probe.json'}")
    for item in report["checks"]:
        if not item["ok"]:
            print("FAIL:", item["name"], "|", item["detail"])
    return report


if __name__ == "__main__":
    report = run(sys.argv[1] if len(sys.argv) > 1 else "task3")
    sys.exit(0 if report["total"] and report["passed"] == report["total"] else 1)

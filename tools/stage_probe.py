# -*- coding: utf-8 -*-
"""画布 Tabs / 沙箱插件 / LRU 休眠：真机取证脚本（Playwright + Chromium）。

用法：``python tools/stage_probe.py <out_dir_tag>``（脚本自己在 8778 起隔离服务，跑完关掉）

隔离口径：``JZO_DATA_DIR`` 与 ``JZO_PLUGINS_DIR`` 指向 ``.system_generated/stage/<tag>/``，
不碰开发者本机的 ``data/`` 与 ``plugins/``；探针插件是脚本临时生成的，跑完留在隔离目录里备查。

产出：截图 png + probe.json（结构化断言、页签状态轨迹、console 错误）。

判据来自 2026-10-26 军令任务 3：
  1. 画布顶部 Tabs 常驻一枚**原生**引导页签（不进 iframe）；
  2. 声明 ``stage`` 的插件被点击后开一枚沙箱 iframe 页签，``plugin.activate`` 真回 ready；
  3. 同时存活 iframe ≤3，第 4 个进来时最久未用的那个休眠（摘 iframe、页签标「休眠」），
     点回页签能唤醒重挂；
  4. 右栏面板参数一改，画布里的插件通过 notification 收到，并能往底栏回一条 region.dock；
  5. ``stage.mode = fullscreen`` 只翻全屏标志，不改用户的折叠偏好；
  6. 插件页签可关闭；关掉后画布回到引导页签，底座照常可用。
  7. 原生页签（引导 / 设置与控制台）同样可关闭，控制台能从左栏入口重建；
     页签栏左端「入口」按钮与页签同高、同字号、同底色、同圆角（2026-10-31 军令）。
"""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8778
BASE = f"http://127.0.0.1:{PORT}/workspace"
MAX_LIVE = 3

PLUGIN_JS = """
(function () {
  "use strict";
  var PROTOCOL = "jzo-plugin/1";
  var ID = "__ID__";
  var params = {};
  var activations = 0;

  function reply(target, id, result) {
    target.postMessage({ protocol: PROTOCOL, id: id, kind: "response", ok: true, result: result }, "*");
  }
  function fail(target, id, code, message) {
    target.postMessage({ protocol: PROTOCOL, id: id, kind: "response", ok: false,
      error: { code: code, message: message, retryable: false } }, "*");
  }
  function redraw() {
    var root = document.getElementById("root");
    if (!root) return;
    root.textContent = "";
    var mark = document.createElement("p");
    mark.className = "probe-mark";
    mark.id = "probeMark";
    mark.textContent = ID + " 已激活 " + activations + " 次；面板参数 grade=" + (params.grade || "（未收到）");
    root.appendChild(mark);
    document.title = ID + "-ready";
  }
  function publish(target, text) {
    target.postMessage({ protocol: PROTOCOL, kind: "notification",
      event: "region.dock", payload: { text: text } }, "*");
  }

  window.addEventListener("message", function (event) {
    var msg = event.data;
    if (!msg || msg.protocol !== PROTOCOL) return;
    if (msg.kind === "notification") {
      if (msg.event === "ui.params.changed") {
        params = (msg.payload && msg.payload.values) || {};
        redraw();
        publish(event.source, ID + " 收到面板参数 grade=" + (params.grade || "空"));
      }
      return;
    }
    if (msg.kind !== "request") return;
    if (msg.method === "plugin.activate") {
      activations += 1;
      if (msg.payload && msg.payload.slot === "stage.center") {
        redraw();
        publish(event.source, ID + " 已接管中央画布（slot=" + msg.payload.slot + "）");
      }
      return reply(event.source, msg.id, { ready: true, plugin_id: ID, api_version: "1.0" });
    }
    if (msg.method === "plugin.deactivate") {
      return reply(event.source, msg.id, { ready: false });
    }
    if (msg.method === "question.render") {
      var q = (msg.payload || {}).question || {};
      return reply(event.source, msg.id, { html: "<p>" + String(q.stem || "") + "</p>", height: 40 });
    }
    fail(event.source, msg.id, "UNSUPPORTED_METHOD", String(msg.method));
  });
})();
"""

MANIFEST = {
    "schema_version": "1.0",
    "id": "",
    "name": "",
    "version": "1.0.0",
    "api_version": "1.0",
    "kind": "renderer",
    "description": "舞台探针：只用于验证画布页签、LRU 休眠与事件总线。",
    "license": "Apache-2.0",
    "entry": {"frontend": "dist/index.html"},
    "slots": ["question.card", "stage.center"],
    "capabilities": ["question.render"],
    "permissions": [],
    "stage": {"region": "center", "mode": "takeover", "title": "", "priority": 10, "singleton": True},
    "bus": {"subscribe": ["ui.params.changed"], "publish": ["region.dock"]},
    "ui": {
        "title": "探针面板",
        "hint": "改一下下拉，画布里的插件应当立刻收到通知。",
        "controls": [{
            "type": "select", "key": "grade", "label": "年级",
            "options": [{"value": "初一", "label": "初一"}, {"value": "高一", "label": "高一"}],
            "default": "初一",
        }],
    },
}


def make_plugin(plugins_dir: Path, letter: str, mode: str = "takeover") -> str:
    plugin_id = f"org.jiuzhang.stage-probe-{letter}"
    plugin_dir = plugins_dir / plugin_id
    (plugin_dir / "dist").mkdir(parents=True, exist_ok=True)
    manifest = json.loads(json.dumps(MANIFEST))
    manifest["id"] = plugin_id
    manifest["name"] = f"舞台探针{letter.upper()}"
    manifest["stage"]["title"] = f"探针{letter.upper()}"
    manifest["stage"]["mode"] = mode
    (plugin_dir / "plugin.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (plugin_dir / "LICENSE").write_text("Apache License 2.0 (probe fixture)", encoding="utf-8")
    # 插件页 CSP 只给 style-src 'self' <底座源>：内联 <style> 会被拦，样式必须外挂
    (plugin_dir / "dist" / "plugin.css").write_text(
        "body{font:14px system-ui;margin:16px;color:#123456}\n"
        ".probe-mark{padding:12px;border:1px solid #99aacc;border-radius:8px}\n",
        encoding="utf-8")
    (plugin_dir / "dist" / "index.html").write_text(
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>probe</title>'
        '<link rel="stylesheet" href="plugin.css"></head>'
        '<body><div id="root"></div><script src="plugin.js"></script></body></html>',
        encoding="utf-8")
    (plugin_dir / "dist" / "plugin.js").write_text(PLUGIN_JS.replace("__ID__", plugin_id), encoding="utf-8")
    return plugin_id


def free_port() -> bool:
    with socket.socket() as sock:
        return sock.connect_ex(("127.0.0.1", PORT)) != 0


JS_TABS = """
() => {
  const tabs = Array.from(document.querySelectorAll('#wsTabs .ws-tab')).map(t => ({
    key: t.getAttribute('data-tab'),
    label: (t.querySelector('.ws-tab-label') || {}).textContent || t.textContent.trim(),
    selected: t.getAttribute('aria-selected'),
    state: (t.querySelector('.ws-tab-state') || {}).textContent || ''
  }));
  const frames = Array.from(document.querySelectorAll('.ws-plugin-frame')).map(f => ({
    tab: (f.closest('.ws-tab-panel') || {}).getAttribute ? f.closest('.ws-tab-panel').getAttribute('data-tab') : null,
    sandbox: f.getAttribute('sandbox'),
    src: (f.getAttribute('src') || '').slice(0, 80),
    title: ''
  }));
  const page = document.querySelector('.ws-page');
  const marks = Array.from(document.querySelectorAll('.ws-tab-panel')).map(p => ({
    tab: p.getAttribute('data-tab'),
    hidden: p.hidden,
    // 插件在沙箱里自渲染，宿主读不到 iframe 内部（opaque origin）——
    // 这里只取宿主侧可见证据：iframe 在不在、有没有故障框、休眠说明写了什么
    hasFrame: Boolean(p.querySelector('.ws-plugin-frame')),
    error: (p.querySelector('.ws-frame-error') || {}).textContent || '',
    note: (p.querySelector('.ws-frame-note') || {}).textContent || ''
  }));
  return {
    tabs: tabs,
    frames: frames,
    frameCount: frames.length,
    marks: marks,
    fullscreen: page.getAttribute('data-fullscreen'),
    dataSide: page.getAttribute('data-side'),
    dataCtx: page.getAttribute('data-ctx'),
    dataDock: page.getAttribute('data-dock'),
    sidebarVisible: document.getElementById('wsSidebar').getBoundingClientRect().width > 1,
    ctxVisible: document.getElementById('wsContext').getBoundingClientRect().width > 1,
    dockVisible: document.getElementById('wsDock').getBoundingClientRect().height > 1,
    dockText: document.getElementById('wsDockLog').textContent.replace(/\\s+/g, ' ').slice(0, 400)
  };
}
"""


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "stage" / tag
    data_dir = out / "data"
    plugins_dir = out / "plugins"
    data_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    ids = [make_plugin(plugins_dir, letter) for letter in "abcd"]
    fullscreen_id = make_plugin(plugins_dir, "f", mode="fullscreen")

    report = {"tag": tag, "ids": ids + [fullscreen_id], "checks": [], "states": [],
              "console": [], "errors": [], "shots": []}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_PORT"] = str(PORT)
    # 强制 Mock：探针只验宿主↔插件链路，不烧模型额度
    env.pop("JZO_AI_API_KEY", None)
    env.pop("JZO_AI_BASE_URL", None)

    server = subprocess.Popen(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")

    try:
        deadline = time.time() + 40
        ready = False
        while time.time() < deadline:
            if server.poll() is not None:
                break
            with socket.socket() as sock:
                sock.settimeout(1)
                if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                    ready = True
                    break
            time.sleep(0.5)
        if not ready:
            out_text = ""
            try:
                out_text = server.stdout.read() or ""
            except Exception:  # noqa: BLE001
                pass
            check("隔离服务起在 8778", False, out_text[-800:])
            return finish(report, out, None)
        check("隔离服务起在 8778", True, f"data={data_dir} plugins={plugins_dir}")
        time.sleep(1.5)   # 留给种子插件静默安装

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:300]}))
            page.on("pageerror", lambda e: report["errors"].append(str(e)[:300]))
            page.goto(BASE, wait_until="networkidle")
            page.wait_for_timeout(600)

            def snap(step):
                st = page.evaluate(JS_TABS)
                st["step"] = step
                report["states"].append(st)
                png = out / f"{step}.png"
                page.screenshot(path=str(png))
                report["shots"].append(str(png))
                return st

            def click_plugin(label_part):
                return page.evaluate("""
                part => {
                  const items = Array.from(document.querySelectorAll('#wsPluginList .ws-plugin-item'));
                  const t = items.find(b => b.textContent.indexOf(part) >= 0);
                  if (!t) return null;
                  t.click();
                  return t.textContent.trim().slice(0, 40);
                }
                """, label_part)

            initial = snap("00-initial")
            # 宿主自己占两枚页签：引导（原生）与设置与控制台（宿主同源 iframe）。
            check("画布初始是引导与控制台两枚宿主页签",
                  len(initial["tabs"]) == 2
                  and initial["tabs"][0]["key"] == "home"
                  and any(t["key"] == "console" for t in initial["tabs"]),
                  json.dumps(initial["tabs"], ensure_ascii=False))
            check("引导页签不含 iframe（原生）", initial["frameCount"] == 0, str(initial["frameCount"]))
            check("左栏列出探针插件",
                  page.evaluate("() => document.querySelectorAll('#wsPluginList .ws-plugin-item').length") >= 5,
                  str(page.evaluate("() => document.querySelectorAll('#wsPluginList .ws-plugin-item').length")))

            # ---------- 逐个开页签，撞 LRU ----------
            # 插件在沙箱里自渲染，宿主读不到 iframe 内部；跨边界的硬证据是底栏：
            # 探针插件收到 plugin.activate 才会发「已接管中央画布」，收到 ui.params.changed
            # 才会发「收到面板参数」。这两条能落到底栏，说明请求/通知与回执真的走通了。
            def dock_text():
                return page.evaluate("() => document.getElementById('wsDockLog').textContent")

            def panel_of(state, plugin_id):
                return next((m for m in state["marks"] if m["tab"] == f"plugin:{plugin_id}"), None)

            live_peak = 0
            for index, letter in enumerate("abcd", start=1):
                pid = ids[index - 1]
                clicked = click_plugin(f"探针{letter.upper()}")
                page.wait_for_timeout(1500)
                st = snap(f"1{index}-open-{letter}")
                dock = dock_text()
                live_peak = max(live_peak, st["frameCount"])
                probe_tab = next((t for t in st["tabs"] if t["key"] == f"plugin:{pid}"), None)
                check(f"插件{letter.upper()} 开出画布页签",
                      clicked is not None and probe_tab is not None,
                      f"clicked={clicked} tabs={len(st['tabs'])}")
                check(f"插件{letter.upper()} 页签为选中态", probe_tab and probe_tab["selected"] == "true",
                      json.dumps(probe_tab, ensure_ascii=False) if probe_tab else "无此页签")
                panel = panel_of(st, pid)
                frame = next((f for f in st["frames"] if f["tab"] == f"plugin:{pid}"), None)
                check(f"插件{letter.upper()} iframe 沙箱为 allow-scripts allow-modals",
                      bool(frame and frame["sandbox"] == "allow-scripts allow-modals"),
                      json.dumps(frame, ensure_ascii=False) if frame else "")
                check(f"插件{letter.upper()} 挂载无故障框（activate 30s 内回 ready）",
                      bool(panel and panel["hasFrame"] and not panel["error"]),
                      json.dumps(panel, ensure_ascii=False) if panel else "")
                check(f"插件{letter.upper()} activate 后经总线回话（底栏出现其自报的接管事件）",
                      f"{pid} 已接管中央画布" in dock, dock[-200:])
                if index <= MAX_LIVE:
                    check(f"开第 {index} 个时 iframe 全部存活", st["frameCount"] == index, str(st["frameCount"]))
                else:
                    check(f"开第 {index} 个时 LRU 生效（存活 iframe ≤{MAX_LIVE}）",
                          st["frameCount"] <= MAX_LIVE, str(st["frameCount"]))
                    first_tab = next((t for t in st["tabs"] if t["key"] == f"plugin:{ids[0]}"), None)
                    check("最久未用的插件A 被标为休眠",
                          first_tab and "休眠" in first_tab["state"],
                          json.dumps(first_tab, ensure_ascii=False) if first_tab else "")
                    first_panel = panel_of(st, ids[0])
                    check("休眠页签的 iframe 已摘除并留说明",
                          bool(first_panel and not first_panel["hasFrame"] and "休眠" in first_panel["note"]),
                          json.dumps(first_panel, ensure_ascii=False) if first_panel else "")
                    check("当前活动页签没被自己休眠掉",
                          bool(panel_of(st, pid) and panel_of(st, pid)["hasFrame"]), str(pid))

            check(f"存活 iframe 峰值不超过 {MAX_LIVE}", live_peak <= MAX_LIVE, str(live_peak))

            # ---------- 唤醒 ----------
            wake_before = dock_text().count(f"{ids[0]} 已接管中央画布")
            page.locator(f'#wsTabs .ws-tab[data-tab="plugin:{ids[0]}"]').click()
            page.wait_for_timeout(1800)
            woke = snap("15-wake-a")
            wake_dock = dock_text()
            panel_a = panel_of(woke, ids[0])
            check("点休眠页签能唤醒并重挂 iframe",
                  bool(panel_a and panel_a["hasFrame"] and not panel_a["error"]),
                  json.dumps(panel_a, ensure_ascii=False) if panel_a else "")
            check("唤醒后插件重新走了一遍 activate（底栏接管事件计数 +1）",
                  wake_dock.count(f"{ids[0]} 已接管中央画布") == wake_before + 1,
                  f"{wake_before} → {wake_dock.count(f'{ids[0]} 已接管中央画布')}")
            tab_a = next((t for t in woke["tabs"] if t["key"] == f"plugin:{ids[0]}"), None)
            check("唤醒后页签去掉休眠标记", tab_a and not tab_a["state"], json.dumps(tab_a, ensure_ascii=False))
            check("唤醒一个就休眠另一个（总数仍受 LRU 管住）", woke["frameCount"] <= MAX_LIVE, str(woke["frameCount"]))

            # ---------- 右栏参数 → notification → region.dock ----------
            changed = page.evaluate("""
            () => {
              const sel = document.querySelector('#wsPluginControls select.ws-ui-select');
              if (!sel) return null;
              const next = Array.from(sel.options).map(o => o.value).find(v => v !== sel.value);
              sel.value = next;
              sel.dispatchEvent(new Event('change', {bubbles: true}));
              return {value: next};
            }
            """)
            page.wait_for_timeout(1000)
            after = snap("16-param-change")
            after_dock = dock_text()
            check("右栏面板下拉可改", changed is not None, json.dumps(changed, ensure_ascii=False))
            live_ids = [m["tab"].split("plugin:", 1)[1] for m in after["marks"] if m["hasFrame"]]
            check("面板改动经 notification 抵达存活插件，插件回话带上新值",
                  bool(changed) and any(
                      f"{pid} 收到面板参数 grade={changed['value']}" in after_dock for pid in live_ids),
                  f"alive={live_ids} dock_tail={after_dock[-200:]}")
            check("未授权话题发不出去（插件只发白名单 region.dock，底栏无越权告警之外的噪声）",
                  "想发未授权事件" not in after_dock, after_dock[-120:])

            # ---------- fullscreen ----------
            click_plugin("探针F")
            page.wait_for_timeout(1500)
            full = snap("17-fullscreen")
            check("fullscreen 插件接管时翻全屏标志", full["fullscreen"] == "on", str(full["fullscreen"]))
            check("全屏下左右栏与底栏让位",
                  not full["sidebarVisible"] and not full["ctxVisible"] and not full["dockVisible"],
                  json.dumps({k: full[k] for k in ("sidebarVisible", "ctxVisible", "dockVisible")}))
            check("全屏不改用户的折叠偏好（data-side/data-ctx 原样）",
                  full["dataSide"] in (None, "open") and full["dataCtx"] in (None, "open"),
                  json.dumps({"side": full["dataSide"], "ctx": full["dataCtx"]}))
            # 切回引导页签应退出全屏
            page.locator('#wsTabs .ws-tab[data-tab="home"]').click()
            page.wait_for_timeout(600)
            back = snap("18-back-to-home")
            check("切回引导页签即退出全屏", back["fullscreen"] in (None, "off"), str(back["fullscreen"]))
            check("退出全屏后左右栏与底栏回来",
                  back["sidebarVisible"] and back["ctxVisible"],
                  json.dumps({k: back[k] for k in ("sidebarVisible", "ctxVisible", "dockVisible")}))

            # ---------- 关闭页签 ----------
            tab_count_before = len(back["tabs"])
            page.locator(f'#wsTabs .ws-tab[data-tab="plugin:{ids[3]}"] .ws-tab-close').click()
            page.wait_for_timeout(600)
            closed = snap("19-close-tab")
            check("插件页签可关闭", len(closed["tabs"]) == tab_count_before - 1,
                  f"{tab_count_before} → {len(closed['tabs'])}")
            check("引导页签可关闭（有 × 按钮）",
                  page.evaluate("""() => {
                    const t = document.querySelector('#wsTabs .ws-tab[data-tab=\"home\"]');
                    return t ? Boolean(t.querySelector('.ws-tab-close')) : false;
                  }"""), "")
            check("设置与控制台页签可关闭（有 × 按钮）",
                  page.evaluate("""() => {
                    const t = document.querySelector('#wsTabs .ws-tab[data-tab=\"console\"]');
                    return t ? Boolean(t.querySelector('.ws-tab-close')) : false;
                  }"""), "")

            # ---------- 原生页签关闭与重建 ----------
            n_before_console = len(closed["tabs"])
            page.locator('#wsTabs .ws-tab[data-tab="console"] .ws-tab-close').click()
            page.wait_for_timeout(500)
            console_closed = snap("20-close-console")
            check("关闭设置与控制台后页签释放空间",
                  len(console_closed["tabs"]) == n_before_console - 1,
                  f"{n_before_console} → {len(console_closed['tabs'])}")
            page.locator("#wsConsoleBtn").click()
            page.wait_for_timeout(800)
            console_back = snap("21-reopen-console")
            console_tab = next((t for t in console_back["tabs"] if t["key"] == "console"), None)
            check("左栏底部入口能把控制台页签叫回来",
                  console_tab is not None and console_tab["selected"] == "true"
                  and len(console_back["tabs"]) == n_before_console,
                  json.dumps(console_back["tabs"], ensure_ascii=False))

            # ---------- 入口按钮与页签同形（2026-10-31 军令） ----------
            page.locator("#wsToggleSidebar").click()
            page.wait_for_timeout(400)
            snap("22-entry-shape")
            shape = page.evaluate("""() => {
              const btn = document.getElementById('wsOpenSidebar');
              const tab = document.querySelector('#wsTabs .ws-tab');
              const cs = node => getComputedStyle(node);
              const pick = node => ({
                h: Math.round(node.getBoundingClientRect().height),
                radius: cs(node).borderTopLeftRadius,
                font: cs(node).fontSize,
                bg: cs(node).backgroundColor,
                padTop: cs(node).paddingTop,
                padLeft: cs(node).paddingLeft,
                borderBottom: cs(node).borderBottomWidth,
                visible: node.getBoundingClientRect().width > 0
              });
              return {button: pick(btn), tab: pick(tab)};
            }""")
            btn_shape, tab_shape = shape["button"], shape["tab"]
            check("收起左栏后入口按钮可见", btn_shape["visible"], json.dumps(shape, ensure_ascii=False))
            check("入口按钮与页签同高、同字号、同底色、同圆角、同内边距",
                  all(btn_shape[k] == tab_shape[k]
                      for k in ("h", "font", "bg", "radius", "padTop", "padLeft", "borderBottom")),
                  json.dumps(shape, ensure_ascii=False))
            page.locator("#wsOpenSidebar").click()
            page.wait_for_timeout(400)

            page.close()
            browser.close()
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    return finish(report, out, None)


def finish(report: dict, out: Path, _unused) -> dict:
    total = len(report["checks"])
    passed = sum(1 for c in report["checks"] if c["ok"])
    report["summary"] = {"total": total, "passed": passed, "failed": total - passed,
                         "pageErrors": len(report["errors"])}
    out.mkdir(parents=True, exist_ok=True)
    (out / "probe.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["out_dir"] = str(out)
    return report


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "run"
    if not free_port():
        print(f"端口 {PORT} 被占用，先关掉旧实例再跑。")
        sys.exit(2)
    rep = run(tag)
    print("out_dir:", rep.get("out_dir"))
    print("summary:", json.dumps(rep.get("summary", {}), ensure_ascii=False))
    for c in rep["checks"]:
        print(("  PASS  " if c["ok"] else "  FAIL  ") + c["name"] + ("  | " + c["detail"] if c["detail"] else ""))
    if rep["errors"]:
        print("PAGE ERRORS:", json.dumps(rep["errors"], ensure_ascii=False))
    bad_console = [c for c in rep["console"] if c["type"] == "error"]
    if bad_console:
        print("CONSOLE ERRORS:", json.dumps(bad_console[:8], ensure_ascii=False))

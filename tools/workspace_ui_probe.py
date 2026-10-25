# -*- coding: utf-8 -*-
"""工作台 UI 重构真机取证（军令 #13 任务 2）。

用法：``.venv/Scripts/python.exe tools/workspace_ui_probe.py <out_dir_tag>``

隔离口径：``JZO_DATA_DIR`` 指向 ``.system_generated/workspace-ui-probe/<tag>/data``，
不碰开发者本机 ``data/``；插件目录仍用仓库 ``plugins/``（只读）。

判据：
  1. 左右栏头部等高（48px）且顶线对齐；
  2. 左栏没有题库下拉、自由对话在插件列表内、管理入口死锁栏底；
  3. 画布没有舞台头 / 模型胶囊 / 上下文按钮，也没有「沙箱运行中」提示；
  4. 底栏三视图可切换，报错诊断悬停提示 + 双击原位变字、剪贴板内容=整行、
     不弹 Toast、不选中文字、不抢焦点（含 http 老回路的焦点归还）；
  5. 插件行可原生拖拽排序，顺序写回后端偏好树（data/plugin_state.json），刷新后保持；
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
PORT = 8793
BASE = f"http://127.0.0.1:{PORT}/workspace"


def wait_port(deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


STATE_JS = """
() => {
  const rect = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { top: Math.round(r.top), height: Math.round(r.height), bottom: Math.round(r.bottom) };
  };
  const list = document.getElementById('wsPluginList');
  const rows = list ? Array.from(list.querySelectorAll('.ws-plugin-row')).map(r => ({
    key: r.getAttribute('data-key'),
    draggable: r.getAttribute('draggable'),
    name: (r.querySelector('.ws-plugin-item-name') || {}).textContent || ''
  })) : [];
  const dock = document.getElementById('wsDockLog');
  return {
    sidebarHead: rect('.ws-sidebar-head'),
    contextHead: rect('.ws-context-head'),
    bankSelect: !!document.getElementById('wsBankSelect'),
    bankNew: !!document.getElementById('wsBankNew'),
    modelBtn: !!document.getElementById('wsModelBtn'),
    contextBtn: !!document.getElementById('wsToggleContext'),
    stageHead: !!document.querySelector('.ws-stage-head'),
    chatInList: !!(list && (list.querySelector('#wsChatEntry')
      || list.querySelector('[data-key="plugin:org.jiuzhang.chat"]'))),
    rows: rows,
    footConsole: !!document.querySelector('.ws-sidebar-foot #wsConsoleBtn'),
    footReset: !!document.querySelector('.ws-sidebar-foot #wsResetLayout'),
    dockTabs: Array.from(document.querySelectorAll('#wsDockTabs .ws-dock-tab')).map(b => b.textContent.trim()),
    dockView: dock ? dock.getAttribute('data-view') : null,
    frameNote: !!document.querySelector('.ws-frame-note')
  };
}
"""


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "workspace-ui-probe" / tag
    data_dir = out / "data"
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    report = {"tag": tag, "checks": [], "console": [], "errors": [], "shots": [], "notes": {}}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
        return bool(ok)

    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(data_dir)
    # 探针只借仓库 plugins/ 当代码目录（只读）。ADR-012 之后不设这个口子，插件区
    # 会解析到 data/workspaces/default/plugins——空目录，左栏一行都没有。
    env["JZO_PLUGINS_DIR"] = str(ROOT / "plugins")
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
        time.sleep(1.2)

        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 900},
                                          permissions=["clipboard-read", "clipboard-write"])
            page = context.new_page()
            page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:300]}))
            page.on("pageerror", lambda e: report["errors"].append(str(e)[:300]))

            def snap(step):
                png = out / f"{step}.png"
                page.screenshot(path=str(png))
                report["shots"].append(str(png))

            page.goto(BASE, wait_until="networkidle")
            page.wait_for_selector("#wsPluginList .ws-plugin-row")
            page.wait_for_timeout(1800)
            state = page.evaluate(STATE_JS)
            report["notes"]["initial"] = state
            snap("10-layout")

            check("左右栏头部等高", state["sidebarHead"] and state["contextHead"]
                  and state["sidebarHead"]["height"] == state["contextHead"]["height"] == 48,
                  json.dumps([state["sidebarHead"], state["contextHead"]]))
            check("左右栏头部顶线对齐", state["sidebarHead"] and state["contextHead"]
                  and state["sidebarHead"]["top"] == state["contextHead"]["top"], "")
            check("左栏题库下拉已移入设置", not state["bankSelect"] and not state["bankNew"], "")
            check("自由对话（现为 AI 助手插件行）在插件列表内", state["chatInList"], json.dumps(state["rows"], ensure_ascii=False)[:200])
            check("管理入口死锁栏底且无悬浮小图标",
                  state["footConsole"] and not state["footReset"], "")
            check("舞台头/模型胶囊/上下文按钮已删除",
                  not state["stageHead"] and not state["modelBtn"] and not state["contextBtn"], "")
            check("底栏三视图就位", state["dockTabs"] == ["运行日志", "报错诊断", "系统终端"],
                  json.dumps(state["dockTabs"], ensure_ascii=False))

            # ---------- 报错诊断：悬停提示、双击原位变字 ----------
            page.evaluate("""() => {
              window.JzoBus.emit('region.dock', {
                text: '插件“演示”激活失败：入口加载失败', topic: 'plugin.error'
              });
              window.JzoBus.emit('region.dock', { text: '普通运行日志一行', topic: 'plugin.mounted' });
            }""")
            page.click('#wsDockTabError')
            page.wait_for_timeout(200)
            error_state = page.evaluate("""() => {
              const dock = document.getElementById('wsDockLog');
              const rows = Array.from(dock.querySelectorAll('.ws-dock-item'));
              return {
                view: dock.getAttribute('data-view'),
                rows: rows.length,
                hint: rows[0] ? (rows[0].querySelector('.ws-dock-copy') || {}).textContent : '',
                toast: document.querySelectorAll('.ws-toast, .toast, [role="status"].toast').length
              };
            }""")
            report["notes"]["error_view"] = error_state
            check("报错诊断只显示错误行", error_state["view"] == "error" and error_state["rows"] == 1,
                  json.dumps(error_state, ensure_ascii=False))
            check("错误行带「双击复制」提示", error_state["hint"] == "双击复制", str(error_state["hint"]))
            page.hover('#wsDockLog .ws-dock-item')
            snap("20-error-hover")
            page.dblclick('#wsDockLog .ws-dock-item')
            page.wait_for_timeout(250)
            copied = page.evaluate("""() => {
              const row = document.querySelector('#wsDockLog .ws-dock-item');
              return {
                copied: row.classList.contains('is-copied'),
                hint: (row.querySelector('.ws-dock-copy') || {}).textContent,
                green: getComputedStyle(row).backgroundColor,
                toast: document.querySelectorAll('.ws-toast, .toast').length
              };
            }""")
            report["notes"]["copied"] = copied
            snap("21-error-copied")
            check("双击后原位变字为「已复制」", copied["hint"] == "已复制" and copied["copied"],
                  json.dumps(copied, ensure_ascii=False))
            check("复制反馈不弹 Toast", copied["toast"] == 0, str(copied["toast"]))

            # 剪贴板必须拿到整行（时间 + 主题 + 正文），不是行内某个 span
            clipboard_probe = page.evaluate("""() => {
              const row = document.querySelector('#wsDockLog .ws-dock-item');
              const hint = row.querySelector('.ws-dock-copy');
              const rr = row.getBoundingClientRect();
              const hr = hint.getBoundingClientRect();
              return {
                row: row.getAttribute('data-copy'),
                selection: window.getSelection().toString(),
                userSelect: getComputedStyle(row).userSelect,
                sameRow: Math.abs((hr.top + hr.bottom) / 2 - (rr.top + rr.bottom) / 2) < 10,
                inside: hr.left >= rr.left && hr.right <= rr.right + 0.5,
                rightAligned: Math.abs(hr.right - rr.right) < 20
              };
            }""")
            clipboard_probe["clipboard"] = page.evaluate(
                "() => navigator.clipboard.readText()")
            report["notes"]["clipboard"] = clipboard_probe
            check("剪贴板内容与整行 data-copy 完全一致",
                  clipboard_probe["clipboard"] == clipboard_probe["row"],
                  json.dumps(clipboard_probe, ensure_ascii=False)[:300])
            check("双击不留下文字选区", clipboard_probe["selection"] == "",
                  repr(clipboard_probe["selection"]))
            check("报错行禁用文本选择（CSS user-select）",
                  clipboard_probe["userSelect"] == "none", clipboard_probe["userSelect"])
            check("「已复制」落在被双击行内且右对齐（不串行、不飘出）",
                  clipboard_probe["sameRow"] and clipboard_probe["inside"]
                  and clipboard_probe["rightAligned"],
                  json.dumps(clipboard_probe, ensure_ascii=False)[:300])

            # http 老回路：隐藏 textarea 会抢焦点，复制后必须还给原元素
            page.wait_for_timeout(1400)   # 等上一轮「已复制」闪完，避免误判成本轮结果
            page.focus('#wsDockTabError')
            fallback = page.evaluate("""() => {
              Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true });
              return document.activeElement.id;
            }""")
            page.dblclick('#wsDockLog .ws-dock-item')
            page.wait_for_timeout(250)
            after_fallback = page.evaluate("""() => ({
              active: document.activeElement.id,
              selection: window.getSelection().toString(),
              hint: (document.querySelector('#wsDockLog .ws-dock-item .ws-dock-copy') || {}).textContent,
              toast: document.querySelectorAll('.ws-toast, .toast').length
            })""")
            report["notes"]["fallback"] = {"before": fallback, "after": after_fallback}
            snap("22-error-copied-fallback")
            check("老回路复制后焦点归还（不抢焦点）",
                  after_fallback["active"] == "wsDockTabError" and fallback == "wsDockTabError",
                  json.dumps(report["notes"]["fallback"], ensure_ascii=False))
            check("老回路复制不选中文字", after_fallback["selection"] == "",
                  repr(after_fallback["selection"]))
            check("老回路复制仍是原位文字反馈、无 Toast",
                  after_fallback["hint"] in ("已复制", "复制失败") and after_fallback["toast"] == 0,
                  json.dumps(after_fallback, ensure_ascii=False))
            page.click('#wsDockTabTerminal')
            page.wait_for_timeout(150)
            terminal_rows = page.evaluate(
                "() => document.querySelectorAll('#wsDockLog .ws-dock-item').length")
            check("系统终端显示宿主生命周期事件", terminal_rows >= 1, f"rows={terminal_rows}")
            page.click('#wsDockTabLog')

            # ---------- 原生拖拽排序 + 刷新保持 ----------
            rows = state["rows"]
            check("插件行声明原生 draggable", all(r["draggable"] == "true" for r in rows),
                  json.dumps([r["draggable"] for r in rows]))
            keys_before = [r["key"] for r in rows]
            if len(rows) >= 3:
                first = page.locator('.ws-plugin-row').nth(0)
                last = page.locator('.ws-plugin-row').nth(len(rows) - 1)
                last.drag_to(first)
                page.wait_for_timeout(400)
                keys_after = page.evaluate("""() => Array.from(
                  document.querySelectorAll('#wsPluginList .ws-plugin-row')
                ).map(r => r.getAttribute('data-key'))""")
                # 顺序的事实来源已经从浏览器挪到后端偏好树（PLUGIN_SPEC §2.12 第 5）条），
                # 所以这里查的是「拖完有没有整棵树写回 /api/plugins/sidebar」。
                stored = page.evaluate(
                    "() => fetch('/api/plugins').then(r => r.json()).then(d => (d.sidebar || [])"
                    ".reduce((acc, n) => { if (n.kind === 'folder') "
                    "(n.children || []).forEach(c => acc.push(c.id || c)); else acc.push(n.id); "
                    "return acc; }, []))"
                )
                report["notes"]["drag"] = {"before": keys_before, "after": keys_after, "stored": stored}
                check("拖拽改变了行顺序", keys_after != keys_before,
                      json.dumps({"before": keys_before[:3], "after": keys_after[:3]}, ensure_ascii=False))
                visible = [k for k in (stored or []) if k in keys_after]
                check("顺序写回后端偏好树（左栏树是顺序唯一事实来源）",
                      bool(keys_after) and visible == keys_after, str(stored)[:200])
                check("拖拽后首行是原末行", keys_after and keys_after[0] == keys_before[-1],
                      f"{keys_after[:1]} vs {keys_before[-1:]}")
                page.reload(wait_until="networkidle")
                page.wait_for_selector("#wsPluginList .ws-plugin-row")
                page.wait_for_timeout(1200)
                keys_reload = page.evaluate("""() => Array.from(
                  document.querySelectorAll('#wsPluginList .ws-plugin-row')
                ).map(r => r.getAttribute('data-key'))""")
                check("刷新后拖拽顺序保持", keys_reload == keys_after, json.dumps(keys_reload[:3]))
                snap("30-drag-order")
            else:
                check("至少有 3 个条目可拖拽", False, json.dumps(keys_before, ensure_ascii=False))

            # ---------- 沙箱提示已删：打开一个插件画布 ----------
            page.get_by_role("button", name="录题、改题、删题工作台").click()
            page.wait_for_timeout(2500)
            note = page.evaluate("() => !!document.querySelector('.ws-frame-note')")
            check("「沙箱运行中」提示已删除", not note, "")
            snap("40-plugin-canvas")

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
    report = run(sys.argv[1] if len(sys.argv) > 1 else "task2")
    sys.exit(0 if report["total"] and report["passed"] == report["total"] else 1)

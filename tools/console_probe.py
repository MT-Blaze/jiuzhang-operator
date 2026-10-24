# -*- coding: utf-8 -*-
"""控制台页签与设置页真机探针（v0.9.0 口径）。

取证口径（军令 #14 阶段二）：
- 工作台左下入口是**带文字**的「设置与控制台」，有更新待办时挂文字徽标；
- 工作台**不许再有弹窗**：模型胶囊与 Provider 弹窗节点全数退役；
- 页签内是同源 iframe 装载的 ``/settings?embedded=1``，站点外壳必须隐藏；
- 设置页左菜单五项（工作区/插件/模型配置/备份与恢复/系统设置），右详情；
- 插件分区是二级页签（管理/检查更新/在线索引/手动安装），键盘可切、不做弹窗；
- 检查更新分区带 aria 进度条，空闲时收起；
- 工作区列表里的教材版本下拉与 ``/api/bank/textbooks`` 的生效版本一致；
- 大纲树根层按生效教材版本过滤，考向并集（textbook_id 为 NULL）仍可见；
- 有更新待办时点左下入口直接落到「插件 · 检查更新」；
- 防变砖：直连 /settings 仍是完整独立页；
- 375px 不横向溢出，菜单与二级页签热区仍 ≥44px；全程零 console / page error。

用法：``.venv/Scripts/python.exe tools/console_probe.py <tag>``
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 25
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("服务提前退出：" + (process.stdout.read() if process.stdout else "")[:2000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 25 秒内就绪")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "console_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    (work / "shots").mkdir(parents=True)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_LOCAL_TOKEN"] = "console-probe-token"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    result: dict = {"tag": tag, "checks": [], "console_errors": [], "page_errors": [], "geometry": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type in {"error", "warning"} else None)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.goto(base + "/workspace", wait_until="networkidle")

            btn = page.locator("#wsConsoleBtn")
            expect(btn).to_be_visible(timeout=10000)
            label = btn.inner_text().strip()
            check("左下入口带文字「设置与控制台」", "设置与控制台" in label, {"text": label})
            check("初始无更新徽标", page.locator("#wsConsoleDot").is_hidden())
            check("旧模型胶囊与 Provider 弹窗节点已删除",
                  page.locator("#wsModelBtn").count() == 0
                  and page.locator("#wsProviderModal").count() == 0
                  and page.locator("#wsSettingsLink").count() == 0
                  and page.locator(".ws-modal-overlay").count() == 0)

            btn.click()
            tab = page.locator(".ws-tab", has_text="设置与控制台").first
            expect(tab).to_be_visible(timeout=10000)
            check("点击入口在中栏开【设置与控制台】页签",
                  tab.get_attribute("aria-selected") == "true")

            frame = page.frame_locator("#wsConsoleFrame")
            expect(frame.locator(".st-nav")).to_be_visible(timeout=15000)
            inner = frame.locator("body").evaluate(
                """() => ({
                    embedded: document.documentElement.getAttribute('data-embedded'),
                    navVisible: (() => { const n = document.querySelector('.topnav');
                        return !!n && getComputedStyle(n).display !== 'none'; })(),
                    headVisible: (() => { const h = document.querySelector('.st-head');
                        return !!h && getComputedStyle(h).display !== 'none'; })(),
                    nav: Array.from(document.querySelectorAll('.st-nav-item')).map((b) => b.textContent.trim()),
                    panels: (() => {
                        const box = (id) => { const n = document.getElementById(id);
                            return !!n && n.getBoundingClientRect().width > 0; };
                        return { workspace: box('stPanelWorkspace'),
                                 plugin: box('stPanelPlugin'),
                                 provider: box('stPanelProvider'),
                                 backup: box('stPanelBackup'),
                                 system: box('stPanelSystem') };
                    })(),
                    split: (() => {
                        const nav = document.querySelector('.st-nav');
                        const panels = document.querySelector('.st-panels');
                        if (!nav || !panels) return null;
                        const a = nav.getBoundingClientRect(), b = panels.getBoundingClientRect();
                        return { navLeft: Math.round(a.left), navRight: Math.round(a.right),
                                 navW: Math.round(a.width), navH: Math.round(a.height),
                                 panelLeft: Math.round(b.left), panelW: Math.round(b.width),
                                 navHit: Math.round(nav.getBoundingClientRect().height /
                                     Math.max(1, nav.querySelectorAll('.st-nav-item').length)) };
                    })()
                })""")
            check("页签内是内嵌模式（embedded=1）", inner["embedded"] == "1", inner)
            check("内嵌时收起站点外壳（主导航/页头不可见）",
                  inner["navVisible"] is False and inner["headVisible"] is False, inner)
            check("左菜单五项齐全（工作区/插件/模型配置/备份与恢复/系统设置）",
                  inner["nav"] == ["工作区", "插件", "模型配置", "备份与恢复", "系统设置"], inner["nav"])
            check("默认落在工作区面板，其余面板不占位",
                  inner["panels"]["workspace"] is True
                  and not any(inner["panels"][key] for key in ("plugin", "provider", "backup", "system")),
                  inner["panels"])
            check("真左右分栏（菜单在左、面板在右、菜单宽 200 上下）",
                  inner["split"] and inner["split"]["navLeft"] < inner["split"]["panelLeft"]
                  and inner["split"]["navRight"] <= inner["split"]["panelLeft"]
                  and 160 <= inner["split"]["navW"] <= 260
                  and inner["split"]["navHit"] >= 44, inner["split"])

            # ---- 插件分区：二级页签，不做弹窗 ----
            frame.locator("#stNavPlugin").click()
            expect(frame.locator("#stPluginTabs")).to_be_visible(timeout=10000)
            subnav = frame.locator("#stPluginTabs").evaluate(
                """(el) => ({
                    labels: Array.from(el.querySelectorAll('.st-subnav-item')).map((b) => b.textContent.trim()),
                    heights: Array.from(el.querySelectorAll('.st-subnav-item'))
                        .map((b) => Math.round(b.getBoundingClientRect().height)),
                    selected: Array.from(el.querySelectorAll('.st-subnav-item'))
                        .map((b) => [b.textContent.trim(), b.getAttribute('aria-selected')])
                })""")
            check("插件分区四项二级页签",
                  subnav["labels"] == ["管理", "检查更新", "在线索引", "手动安装"], subnav["labels"])
            check("二级页签默认落在「管理」",
                  dict(subnav["selected"]).get("管理") == "true"
                  and frame.locator("#stPluginPanelManage").is_visible())
            check("二级页签热区 ≥44px", min(subnav["heights"]) >= 44, subnav["heights"])
            check("插件管理面板可用（无弹窗）",
                  frame.locator("#mg-title").inner_text() == "插件管理与控制"
                  and page.locator(".ws-modal-overlay").count() == 0)

            frame.locator("#stPluginTabUpdate").click()
            expect(frame.locator("#stPluginPanelUpdate")).to_be_visible(timeout=10000)
            progress = frame.locator("#upProgress")
            check("检查更新页签含 aria 进度条（空闲收起）",
                  progress.get_attribute("role") == "progressbar"
                  and progress.get_attribute("aria-valuetext") == "空闲"
                  and progress.is_hidden())
            check("只有「检查更新」页签占位，管理页签收起",
                  frame.locator("#stPluginPanelManage").is_hidden())
            check("检查更新按钮仍在", frame.locator("#upCheckBtn").is_visible())

            # 键盘：右箭头从「检查更新」切到「在线索引」
            frame.locator("#stPluginTabUpdate").focus()
            frame.locator("#stPluginTabUpdate").press("ArrowRight")
            expect(frame.locator("#stPluginPanelIndex")).to_be_visible(timeout=5000)
            check("二级页签键盘可切（ArrowRight → 在线索引）",
                  frame.locator("#stPluginTabIndex").get_attribute("aria-selected") == "true")

            # 宿主 postMessage 深链：直接落到「手动安装」
            page.evaluate(
                """() => { const f = document.getElementById('wsConsoleFrame');
                    f.contentWindow.postMessage({jzo: 'console.panel', panel: 'plugin', tab: 'install'},
                        window.location.origin); }""")
            expect(frame.locator("#stPluginPanelInstall")).to_be_visible(timeout=5000)
            check("宿主消息可直达二级页签（install）",
                  frame.locator("#stPluginTabInstall").get_attribute("aria-selected") == "true"
                  and frame.locator("#stDropZone").is_visible())

            # ---- 工作区：教材版本生效值 + 大纲树过滤 ----
            frame.locator("#stNavWorkspace").click()
            expect(frame.locator("#stWsTextbook")).to_be_visible(timeout=10000)
            expect(frame.locator("#stWsList li").first).to_be_visible(timeout=10000)
            textbook = frame.locator("#stWsTextbook").evaluate(
                """(el) => ({ count: el.options.length,
                              values: Array.from(el.options).map((o) => o.value),
                              labels: Array.from(el.options).map((o) => o.textContent.trim()) })""")
            inline = frame.locator("#stWsList").evaluate(
                """(el) => Array.from(el.querySelectorAll('select.st-ws-textbook-inline'))
                    .map((s) => ({ value: s.value, options: s.options.length }))""")
            check("新建工作区含【教材版本】下拉且首项为「跟随默认版本」",
                  textbook["count"] >= 1 and textbook["values"][0] == "", textbook)
            check("已有工作区带内联教材版本下拉",
                  len(inline) >= 1 and all(item["options"] >= 1 for item in inline), inline)
            scope = page.evaluate(
                """async () => {
                    const provider = await (await fetch('/api/bank/provider', {cache:'no-store'})).json();
                    const books = await (await fetch('/api/bank/textbooks', {cache:'no-store'})).json();
                    const topics = await (await fetch('/api/bank/plugins/' + encodeURIComponent(provider.plugin_id)
                        + '/topics', {cache:'no-store'})).json();
                    return { provider: provider.plugin_id, books: books, topics: topics };
                }""")
            active = scope["books"].get("active_textbook_id") or ""
            items = scope["topics"].get("items") or []
            check("教材版本接口给出当前工作区生效版本",
                  bool(active) and any(item["id"] == active for item in scope["books"].get("items", [])),
                  {"active": active, "ids": [item["id"] for item in scope["books"].get("items", [])]})
            check("大纲根层按生效版本过滤（考向并集 NULL 仍可见）",
                  scope["topics"].get("textbook_id") == active
                  and all(item.get("textbook_id") in (active, None) for item in items)
                  and len(items) > 0,
                  {"active": active, "roots": [(item["id"], item.get("textbook_id")) for item in items[:8]]})
            check("教材下拉与后端清单同源",
                  all(item["id"] in textbook["values"] for item in scope["books"].get("items", [])),
                  {"backend": [item["id"] for item in scope["books"].get("items", [])],
                   "options": textbook["values"]})

            # ---- 模型配置迁入控制台，页签内是唯一表单 ----
            frame.locator("#stNavProvider").click()
            expect(frame.locator("#stPanelProvider")).to_be_visible(timeout=10000)
            check("模型配置在控制台页签内（无弹窗）",
                  frame.locator("#pvSelect").is_visible()
                  and page.locator(".ws-modal-overlay").count() == 0)
            check("不再有顶栏模型胶囊", page.locator("#wsModelBtn").count() == 0)

            geo = page.evaluate(
                """() => {
                    const rect = (sel) => { const el = document.querySelector(sel);
                        return el ? el.getBoundingClientRect() : null; };
                    const side = rect('.ws-sidebar'), ctx = rect('.ws-context'),
                          dock = rect('.ws-dock'), stage = rect('.ws-tabs'),
                          center = rect('.ws-center');
                    return {
                        viewportH: window.innerHeight, viewportW: window.innerWidth,
                        sideH: side && Math.round(side.height), ctxH: ctx && Math.round(ctx.height),
                        sideTop: side && Math.round(side.top), ctxTop: ctx && Math.round(ctx.top),
                        dockW: dock && Math.round(dock.width), centerW: center && Math.round(center.width),
                        dockLeft: dock && Math.round(dock.left), centerLeft: center && Math.round(center.left),
                        dockTop: dock && Math.round(dock.top), stageBottom: stage && Math.round(stage.bottom),
                        dockTitle: (document.querySelector('#wsDockTitle') || {}).textContent || '',
                        dockLabel: (document.querySelector('.ws-dock') || {}).getAttribute
                            ? document.querySelector('.ws-dock').getAttribute('aria-label') : ''
                    };
                }""")
            result["geometry"] = geo
            check("左栏上下通高（顶到视口顶、高≈视口高）",
                  geo["sideTop"] == 0 and abs(geo["sideH"] - geo["viewportH"]) <= 1, geo)
            check("右栏上下通高", geo["ctxTop"] == 0 and abs(geo["ctxH"] - geo["viewportH"]) <= 1, geo)
            check("输出日志区宽度严格等于中列宽度", geo["dockW"] == geo["centerW"], geo)
            check("输出日志区不横跨左右两栏（左边界与画布对齐）",
                  geo["dockLeft"] == geo["centerLeft"], geo)
            check("输出日志区在画布下方（中列内上下分栏）",
                  geo["dockTop"] >= (geo["stageBottom"] or 0) - 4, geo)
            check("底栏定名【输出日志区】", "输出日志区" in geo["dockTitle"], geo)
            check("该区不被叫成控制台", "控制台" not in geo["dockTitle"] + geo["dockLabel"], geo)

            frame.locator("#stNavWorkspace").click()
            expect(frame.locator("#stWsTextbook")).to_be_visible(timeout=10000)
            page.screenshot(path=str(work / "shots" / "console-tab.png"))

            # ---- 更新待办：本地红点 + 直接落到「插件 · 检查更新」 ----
            page.evaluate("() => localStorage.setItem('jzo.updateNotice', JSON.stringify({count: 2}))")
            page.reload(wait_until="networkidle")
            dot = page.locator("#wsConsoleDot")
            expect(dot).to_be_visible(timeout=10000)
            check("更新待办以文字徽标呈现（不只靠颜色）",
                  "2" in dot.inner_text() and "更新" in dot.inner_text(),
                  {"badge": dot.inner_text(), "aria": page.locator("#wsConsoleBtn").get_attribute("aria-label")})
            page.locator("#wsConsoleBtn").click()
            expect(page.locator("#wsConsoleFrame")).to_be_visible(timeout=10000)
            page.wait_for_timeout(600)
            frame = page.frame_locator("#wsConsoleFrame")
            expect(frame.locator("#stPluginTabs")).to_be_visible(timeout=15000)
            check("点更新徽标直达「插件 · 检查更新」",
                  frame.locator("#stPluginTabUpdate").get_attribute("aria-selected") == "true"
                  and frame.locator("#stPluginPanelUpdate").is_visible())
            page.screenshot(path=str(work / "shots" / "console-update-tab.png"))
            page.evaluate("() => localStorage.removeItem('jzo.updateNotice')")

            # ---- 独立页与 375px ----
            standalone = browser.new_page(viewport={"width": 1280, "height": 860})
            standalone.goto(base + "/settings", wait_until="domcontentloaded")
            expect(standalone.locator(".st-nav")).to_be_visible(timeout=10000)
            fallback = standalone.evaluate(
                """() => ({
                    embedded: document.documentElement.getAttribute('data-embedded'),
                    navVisible: !!document.querySelector('.topnav'),
                    navCount: document.querySelectorAll('.st-nav-item').length,
                    split: (() => { const n = document.querySelector('.st-nav'),
                                    p = document.querySelector('.st-panels');
                        if (!n || !p) return null;
                        const a = n.getBoundingClientRect(), b = p.getBoundingClientRect();
                        return { navLeft: Math.round(a.left), panelLeft: Math.round(b.left),
                                 sameRow: Math.abs(a.top - b.top) <= 2 }; })()
                })""")
            check("防变砖：直连 /settings 仍是完整独立页",
                  fallback["embedded"] is None and fallback["navVisible"] is True, fallback)
            check("独立页同样是五项左菜单右详情",
                  fallback["navCount"] == 5 and fallback["split"]
                  and fallback["split"]["navLeft"] < fallback["split"]["panelLeft"]
                  and fallback["split"]["sameRow"] is True, fallback["split"])
            standalone.locator("#stNavProvider").click()
            check("独立页菜单可切区（点模型配置出表单）",
                  standalone.locator("#stPanelProvider").is_visible()
                  and standalone.locator("#pvSelect").is_visible())
            compact = standalone.evaluate(
                """() => {
                    const ids = ['pvSelect', 'pvBaseUrl', 'pvApiKey', 'pvModel'];
                    const rects = ids.map((id) => document.getElementById(id).getBoundingClientRect());
                    const gaps = [];
                    for (let i = 1; i < rects.length; i += 1) {
                        gaps.push(Math.round(rects[i].top - rects[i - 1].bottom));
                    }
                    return { heights: rects.map((r) => Math.round(r.height)),
                             maxGap: Math.max.apply(null, gaps),
                             panelH: Math.round(document.getElementById('stPanelProvider')
                                 .getBoundingClientRect().height) };
                }""")
            check("表单未被拉伸（字段高 ≤60、相邻间距 ≤40）",
                  max(compact["heights"]) <= 60 and compact["maxGap"] <= 40, compact)
            standalone.screenshot(path=str(work / "shots" / "settings-standalone.png"))
            standalone.set_viewport_size({"width": 375, "height": 780})
            standalone.wait_for_timeout(250)
            narrow = standalone.evaluate(
                """() => ({
                    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    stacked: (() => { const n = document.querySelector('.st-nav'),
                                       p = document.querySelector('.st-panels');
                        return n.getBoundingClientRect().bottom <= p.getBoundingClientRect().top + 1; })(),
                    minHit: Math.min.apply(null, Array.from(document.querySelectorAll('.st-nav-item'))
                        .map((b) => Math.round(b.getBoundingClientRect().height)))
                })""")
            check("375px 窄屏不横向溢出且菜单堆到面板上方",
                  narrow["overflow"] <= 0 and narrow["stacked"] is True, narrow)
            check("窄屏菜单项热区仍 ≥44px", narrow["minHit"] >= 44, narrow)
            standalone.locator("#stNavPlugin").click()
            expect(standalone.locator("#stPluginTabs")).to_be_visible(timeout=10000)
            narrow_sub = standalone.evaluate(
                """() => ({
                    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    minHit: Math.min.apply(null,
                        Array.from(document.querySelectorAll('.st-subnav-item'))
                            .map((b) => Math.round(b.getBoundingClientRect().height)))
                })""")
            check("375px 插件二级页签不溢出且热区 ≥44px",
                  narrow_sub["overflow"] <= 0 and narrow_sub["minHit"] >= 44, narrow_sub)
            standalone.screenshot(path=str(work / "shots" / "settings-375.png"))
            standalone.close()

            # ---- 深链：地址参数直落二级页签 ----
            deep = browser.new_page(viewport={"width": 1280, "height": 860})
            deep.goto(base + "/settings?embedded=1&panel=plugin&tab=update", wait_until="domcontentloaded")
            expect(deep.locator("#stPluginPanelUpdate")).to_be_visible(timeout=10000)
            check("地址深链 ?panel=plugin&tab=update 生效",
                  deep.locator("#stPluginTabUpdate").get_attribute("aria-selected") == "true"
                  and deep.locator("#upProgress").get_attribute("role") == "progressbar")
            deep.close()

            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = (all(item["ok"] for item in result["checks"])
                    and not result["page_errors"] and not result["console_errors"])
    (work / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(("PASS" if result["ok"] else "FAIL") + f" · {len(result['checks'])} 项 · {work}")
    for item in result["checks"]:
        print(("  ok " if item["ok"] else "  XX ") + item["name"])
    if result["page_errors"]:
        print("页面异常：" + " | ".join(result["page_errors"][:5]))
    if result["console_errors"]:
        print("控制台报错：" + " | ".join(result["console_errors"][:5]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

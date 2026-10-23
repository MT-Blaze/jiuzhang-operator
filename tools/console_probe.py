# -*- coding: utf-8 -*-
"""控制台标签页、设置页左右分栏与四区几何真机探针。

取证口径（军令「UI 术语修正与四区几何布局定调」+「控制台弹窗废除与页签重构」）：
- 左栏底部是**纯图标按钮**，旧齿轮链接已退役；点它在中栏开【设置与控制台】页签；
- 页签内是同源 iframe 装载的 ``/settings?embedded=1``，内嵌时站点外壳（主导航）必须隐藏；
- 设置页是**左菜单（工作区/插件/模型配置）+ 右详情**的真分栏，菜单项热区 ≥44px；
- 新建工作区表单必须带【教材版本】下拉，且选项与 ``GET /api/bank/textbooks`` 同源；
- 工作台**不许再有弹窗**：``#wsProviderModal`` 与 ``.ws-modal-overlay`` 节点数为 0，
  点顶栏模型胶囊只会把老师带进控制台的模型配置面板；
- 四区几何：左栏与右栏**上下通高**（高度 == 视口高），输出日志区**只占中列**
  （宽度 == 画布宽度，明显小于视口宽，不得横跨左右两栏）；
- 术语：底栏标题含「输出日志区」，全页不得把这一区叫成「控制台」；
- 防变砖：直接访问 /settings 仍是完整独立页（无 embedded 标记、导航可见、同样分栏）；
- 全程零 console / page error。

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
            check("左栏底部是纯图标控制台入口", btn.is_visible() and not btn.inner_text().strip(),
                  {"aria-label": btn.get_attribute("aria-label")})
            check("旧齿轮链接已退役", page.locator("#wsSettingsLink").count() == 0)

            btn.click()
            tab = page.locator(".ws-tab", has_text="设置与控制台").first
            expect(tab).to_be_visible(timeout=10000)
            check("点击图标在中栏开【设置与控制台】页签",
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
                                 provider: box('stPanelProvider') };
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
            check("左菜单三项齐全（工作区/插件/模型配置）",
                  inner["nav"] == ["工作区", "插件", "模型配置"], inner["nav"])
            check("默认落在工作区面板，其余面板不占位",
                  inner["panels"]["workspace"] is True and inner["panels"]["plugin"] is False
                  and inner["panels"]["provider"] is False, inner["panels"])
            check("真左右分栏（菜单在左、面板在右、菜单宽 200 上下）",
                  inner["split"] and inner["split"]["navLeft"] < inner["split"]["panelLeft"]
                  and inner["split"]["navRight"] <= inner["split"]["panelLeft"]
                  and 160 <= inner["split"]["navW"] <= 260
                  and inner["split"]["navHit"] >= 44, inner["split"])

            # 菜单切区：插件区里要能看到既有的插件管理面板（内嵌整页 → 分区的回归点）
            frame.locator("#stNavPlugin").click()
            expect(frame.locator("#manage")).to_be_visible(timeout=10000)
            check("插件面板在页签里可用", frame.locator("#mg-title").inner_text() == "插件管理与控制")

            # 工作区面板：新建表单必须带教材版本下拉，且接的是 /api/bank/textbooks
            frame.locator("#stNavWorkspace").click()
            expect(frame.locator("#stWsTextbook")).to_be_visible(timeout=10000)
            textbook = frame.locator("#stWsTextbook").evaluate(
                """(el) => ({ count: el.options.length,
                              values: Array.from(el.options).map((o) => o.value),
                              labels: Array.from(el.options).map((o) => o.textContent.trim()) })""")
            check("新建工作区含【教材版本】下拉且首项为「跟随默认版本」",
                  textbook["count"] >= 1 and textbook["values"][0] == "", textbook)
            backend = page.evaluate(
                """async () => { const r = await fetch('/api/bank/textbooks', {cache:'no-store'});
                                 return await r.json(); }""")
            check("教材版本下拉与后端清单同源",
                  all(i["id"] in textbook["values"] for i in backend.get("items", [])),
                  {"backend": [i["id"] for i in backend.get("items", [])],
                   "options": textbook["values"]})

            # Provider 弹窗退役：工作台不得再有弹窗节点，模型胶囊只把老师带进控制台
            check("Provider 弹窗节点已彻底删除",
                  page.locator("#wsProviderModal").count() == 0
                  and page.locator(".ws-modal-overlay").count() == 0)
            page.locator("#wsModelBtn").click()
            expect(frame.locator("#stPanelProvider")).to_be_visible(timeout=10000)
            check("点模型胶囊进【设置与控制台 · 模型配置】（无弹窗）",
                  frame.locator("#stPanelProvider").is_visible()
                  and page.locator(".ws-modal-overlay").count() == 0,
                  {"chip": page.locator("#wsModelLabel").inner_text()})

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
            standalone = browser.new_page(viewport={"width": 1280, "height": 860})
            standalone.goto(base + "/settings", wait_until="domcontentloaded")
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
            check("独立页同样是左菜单右详情",
                  fallback["navCount"] == 3 and fallback["split"]
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
            standalone.screenshot(path=str(work / "shots" / "settings-375.png"))
            standalone.close()
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

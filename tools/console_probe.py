# -*- coding: utf-8 -*-
"""v0.8.2 控制台标签页与四区几何真机探针。

取证口径（军令「UI 术语修正与四区几何布局定调」+「控制台插件化」）：
- 左栏底部是**纯图标按钮**，旧齿轮链接已退役；点它在中栏开【设置与控制台】页签；
- 页签内是同源 iframe 装载的 ``/settings?embedded=1``，内嵌时站点外壳（主导航）必须隐藏；
- 四区几何：左栏与右栏**上下通高**（高度 == 视口高），输出日志区**只占中列**
  （宽度 == 画布宽度，明显小于视口宽，不得横跨左右两栏）；
- 术语：底栏标题含「输出日志区」，全页不得把这一区叫成「控制台」；
- 防变砖：直接访问 /settings 仍是完整独立页（无 embedded 标记、导航可见）；
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
            expect(frame.locator("#manage")).to_be_visible(timeout=15000)
            inner = frame.locator("body").evaluate(
                """() => ({
                    embedded: document.documentElement.getAttribute('data-embedded'),
                    navVisible: (() => { const n = document.querySelector('.topnav');
                        return !!n && getComputedStyle(n).display !== 'none'; })(),
                    headVisible: (() => { const h = document.querySelector('.st-head');
                        return !!h && getComputedStyle(h).display !== 'none'; })(),
                    title: (document.querySelector('#mg-title') || {}).textContent || ''
                })""")
            check("页签内是内嵌模式（embedded=1）", inner["embedded"] == "1", inner)
            check("内嵌时收起站点外壳（主导航/页头不可见）",
                  inner["navVisible"] is False and inner["headVisible"] is False, inner)
            check("插件管理面板在页签里可用", "插件管理" in inner["title"] or "插件" in inner["title"], inner)

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

            page.screenshot(path=str(work / "shots" / "console-tab.png"))
            standalone = browser.new_page(viewport={"width": 1280, "height": 860})
            standalone.goto(base + "/settings", wait_until="domcontentloaded")
            fallback = standalone.evaluate(
                """() => ({
                    embedded: document.documentElement.getAttribute('data-embedded'),
                    navVisible: !!document.querySelector('.topnav')
                })""")
            check("防变砖：直连 /settings 仍是完整独立页",
                  fallback["embedded"] is None and fallback["navVisible"] is True, fallback)
            standalone.screenshot(path=str(work / "shots" / "settings-standalone.png"))
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

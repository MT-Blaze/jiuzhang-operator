# -*- coding: utf-8 -*-
"""数据字典控制台「缓存修复」像素证据探针（2026-11-11）。

针对正在运行的 8000 实例取证（只读操作，不写真实数据）：
- 页面全部 CSS/JS 请求带 ?v=20261111a 且 200；
- 辅助栏齿轮折叠按钮与 16 枚字典 Chips 真实渲染；
- 真人路径：鼠标点齿轮展开/收起全局设置，键盘 Tab+Space/Enter 可操作，
  点「学科」Chip 在画布新开页签；
- 375px 视口不横向溢出；全程收集 console / page error。

用法：``.venv/Scripts/python.exe tools/dict_console_cache_proof.py``
产物：``.system_generated/dict_console_cache_fix/v20261111a/`` 截图 + probe.toml
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path

_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
_sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core import toml_io  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
PAGE = BASE + "/static/dict_console.html"
TAG = "v20261111a"
OUT = ROOT / ".system_generated" / "dict_console_cache_fix" / TAG


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    static_requests: list[dict] = []
    console_errors: list[str] = []
    page_errors: list[str] = []
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
        print(("PASS" if passed else "FAIL") + " | " + name + (" | " + detail if detail else ""))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.on("response", lambda r: static_requests.append({"url": r.url, "status": r.status})
                if "/static/" in r.url and (r.url.endswith(".js") or ".js?" in r.url
                                            or r.url.endswith(".css") or ".css?" in r.url) else None)
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        page.goto(PAGE, wait_until="load", timeout=20000)
        page.wait_for_selector(".dc-chip", timeout=15000)
        page.wait_for_function(
            "document.getElementById('dcGlobalsToggleLabel')"
            " && !document.getElementById('dcGlobalsToggleLabel').textContent.includes('加载中')",
            timeout=15000,
        )

        chips = page.locator(".dc-chip")
        chip_count = chips.count()
        check("Chips 渲染数量 == 16（6 基石 + 5 实体 + 5 教研）", chip_count == 16, "实际 " + str(chip_count))
        gear = page.locator("#dcGlobalsToggle")
        panel = page.locator("#dcGlobalsPanel")
        check("齿轮初始折叠 aria-expanded=false", gear.get_attribute("aria-expanded") == "false")
        check("全局设置面板初始 hidden", panel.get_attribute("hidden") is not None)
        gear_text = gear.inner_text()
        check("齿轮含 ⚙️ 图标", "⚙️" in gear_text, repr(gear_text))
        page.screenshot(path=str(OUT / "01_chips_gear_collapsed.png"))
        print("SHOT | 1440x900 | " + str(OUT / "01_chips_gear_collapsed.png"))

        gear.click()
        page.wait_for_function(
            "document.getElementById('dcGlobalsToggle').getAttribute('aria-expanded') === 'true'")
        check("鼠标点齿轮后面板展开", panel.is_visible())
        page.screenshot(path=str(OUT / "02_globals_expanded.png"))
        print("SHOT | 1440x900 | " + str(OUT / "02_globals_expanded.png"))
        gear.click()
        page.wait_for_function(
            "document.getElementById('dcGlobalsToggle').getAttribute('aria-expanded') === 'false'")
        check("再点齿轮收起", not panel.is_visible())

        focused = False
        for _ in range(40):
            page.keyboard.press("Tab")
            if page.evaluate("document.activeElement && document.activeElement.id") == "dcGlobalsToggle":
                focused = True
                break
        check("键盘 Tab 可聚焦齿轮", focused)
        if focused:
            page.keyboard.press("Space")
            page.wait_for_function(
                "document.getElementById('dcGlobalsToggle').getAttribute('aria-expanded') === 'true'")
            check("Space 展开面板", True)
            focus_in_panel = page.evaluate("document.activeElement && document.activeElement.id")
            check("展开后焦点落入学段下拉", focus_in_panel == "dcStage", "activeElement=" + str(focus_in_panel))
            page.keyboard.press("Escape")
            page.wait_for_function(
                "document.getElementById('dcGlobalsToggle').getAttribute('aria-expanded') === 'false'")
            focus_back = page.evaluate("document.activeElement && document.activeElement.id")
            check("Esc 收起且焦点还原齿轮", focus_back == "dcGlobalsToggle", "activeElement=" + str(focus_back))
            page.keyboard.press("Enter")
            page.wait_for_function(
                "document.getElementById('dcGlobalsToggle').getAttribute('aria-expanded') === 'true'")
            check("Enter 再次展开面板", True)
            page.keyboard.press("Escape")
            page.wait_for_function(
                "document.getElementById('dcGlobalsToggle').getAttribute('aria-expanded') === 'false'")

        page.get_by_role("button", name="在画布新开「学科」页签").click()
        tab = page.get_by_role("tab", name="学科")
        tab.wait_for(timeout=10000)
        check("点 Chip 新开「学科」页签并激活", tab.get_attribute("aria-selected") == "true")
        page.screenshot(path=str(OUT / "03_chip_opens_tab.png"))
        print("SHOT | 1440x900 | " + str(OUT / "03_chip_opens_tab.png"))

        gear_box = gear.bounding_box()
        chip_box = chips.first.bounding_box()
        check("齿轮触控高度 >= 44px", gear_box and gear_box["height"] >= 44,
              "实际 %.1fpx" % (gear_box["height"] if gear_box else -1))
        print("INFO | Chip 首枚高度 %.1fpx（设计口径 32px 起步，桌面辅助栏）"
              % (chip_box["height"] if chip_box else -1))

        page.set_viewport_size({"width": 375, "height": 812})
        page.reload(wait_until="load")
        page.wait_for_selector(".dc-chip", timeout=15000)
        scroll_width = page.evaluate("document.documentElement.scrollWidth")
        check("375px 不横向溢出", scroll_width <= 375, "scrollWidth=" + str(scroll_width))
        page.screenshot(path=str(OUT / "04_mobile_375.png"))
        print("SHOT | 375x812 | " + str(OUT / "04_mobile_375.png"))

        browser.close()

    versioned = [r for r in static_requests if "v=20261111a" in r["url"]]
    unversioned = [r for r in static_requests if "v=20261111a" not in r["url"]]
    bad_status = [r for r in static_requests if r["status"] != 200]
    check("静态 JS/CSS 请求全部带版本号", len(unversioned) == 0,
          "带版本 %d 条 / 不带 %d 条" % (len(versioned), len(unversioned)))
    check("静态请求全部 200", len(bad_status) == 0, "非 200: %d 条" % len(bad_status))
    check("零 console error", len(console_errors) == 0, "; ".join(console_errors[:3]))
    check("零 page error", len(page_errors) == 0, "; ".join(page_errors[:3]))

    passed = sum(1 for c in checks if c["passed"])
    result = {
        "probe": "dict_console_cache_proof",
        "tag": TAG,
        "url": PAGE,
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "static_versioned": len(versioned),
        "static_unversioned": [r["url"] for r in unversioned],
        "console_errors": console_errors,
        "page_errors": page_errors,
    }
    (OUT / "probe.toml").write_text(toml_io.dumps(result), encoding="utf-8")
    print("RESULT | %d/%d passed | probe.toml -> %s" % (passed, len(checks), OUT / "probe.toml"))
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
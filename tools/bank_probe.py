# -*- coding: utf-8 -*-
"""core-bank 真机取证：插件挂载、右栏筛选联动、题篮与 KaTeX 字体。

用法：``.venv/Scripts/python.exe tools/bank_probe.py <tag>``

隔离：复制插件与数据到 ``.system_generated/bank_probe/<tag>/``，服务另起端口，
不碰开发者本机 data/ 与 plugins/。产出 screenshots + probe.json。
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
PLUGIN_ID = "org.jiuzhang.core-bank"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 25
    while time.time() < deadline:
        if process.poll() is not None:
            output = process.stdout.read() if process.stdout else ""
            raise RuntimeError("服务提前退出：\n" + output[:3000])
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
    work = ROOT / ".system_generated" / "bank_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    shots.mkdir(parents=True)
    (data_dir / ".seed-demo-bank.installed").write_text("probe\n", encoding="utf-8")

    shutil.copytree(ROOT / "plugins" / PLUGIN_ID, plugins_dir / PLUGIN_ID)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = "bank-probe-token"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [], "page_errors": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="真题题库").first
            expect(item).to_be_visible(timeout=10000)
            check("左栏出现真题题库", True)
            item.click()

            frame_locator = page.frame_locator(".ws-plugin-frame")
            expect(frame_locator.locator(".cb-title")).to_have_text("真题题库", timeout=15000)
            expect(frame_locator.locator(".cb-row")).to_have_count(12, timeout=15000)
            expect(frame_locator.locator(".cb-pager")).to_contain_text("共 456 题", timeout=15000)
            check("插件挂载并载入 456 题", True)

            # KaTeX 真渲染 + 字体已加载（沙箱 CORS 字体）
            frame = page.frame_locator(".ws-plugin-frame")
            math_count = frame.locator(".katex").count()
            check("公式渲染为 KaTeX", math_count > 0, {"katex_nodes": math_count})
            fonts = frame.locator("body").evaluate(
                """async () => {
                    await document.fonts.ready;
                    return {
                        status: document.fonts.status,
                        check: document.fonts.check('16px KaTeX_Main'),
                        families: Array.from(document.fonts).map(f => f.family).slice(0, 6)
                    };
                }"""
            )
            check("KaTeX 字体已加载", bool(fonts.get("check")), fonts)

            # 右栏改年级 → 题库按高三过滤
            grade = page.locator('#wsPluginControls select[data-ui-key="grade"]')
            expect(grade).to_be_visible(timeout=10000)
            grade.select_option("高三")
            expect(frame.locator(".cb-pager")).to_contain_text("共 36 题", timeout=15000)
            grades = frame.locator("body").evaluate(
                "() => Array.from(document.querySelectorAll('.cb-row')).map(r => r.textContent)"
            )
            check("切年级到高三 → 36 题", all("高三" in row for row in grades), {"rows": len(grades)})
            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "grade-gaosan.png"), full_page=False)

            # 再叠难度 → 高三 hard = 11
            difficulty = page.locator('#wsPluginControls select[data-ui-key="difficulty"]')
            difficulty.select_option("hard")
            expect(frame.locator(".cb-pager")).to_contain_text("共 11 题", timeout=15000)
            check("再切难度到压轴 → 11 题", True)
            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "grade-hard.png"), full_page=False)

            # 归零 → 456，再入篮一题
            grade.select_option("全部")
            difficulty.select_option("全部")
            expect(frame.locator(".cb-pager")).to_contain_text("共 456 题", timeout=15000)

            first_row = frame.locator(".cb-row").first
            first_row.locator("button", has_text="入篮").click()
            expect(frame.locator("#cbBasketCount")).to_contain_text("题篮 1", timeout=15000)
            check("题篮计数 1", True)
            page.wait_for_timeout(400)
            basket_file = data_dir / "basket.json"
            basket = json.loads(basket_file.read_text(encoding="utf-8")) if basket_file.is_file() else {}
            basket_items = basket.get("items") or []
            check("题篮落盘", len(basket_items) == 1, {"items": len(basket_items)})
            dock_text = page.locator("#wsDockLog").inner_text()
            check("底栏记录入篮", "加入 1 题" in dock_text, {"dock_tail": dock_text[-160:]})

            # 详情 + 解析
            first_row.click()
            expect(frame.locator(".cb-detail h2")).to_be_visible(timeout=10000)
            toggle = frame.locator(".cb-detail button", has_text="显示解析")
            if toggle.count():
                toggle.first.click()
            check("详情与解析可见", frame.locator(".cb-detail").count() == 1)
            detail_katex = frame.locator(".cb-detail .cb-question .katex").count()
            detail_text = frame.locator(".cb-detail .cb-question").inner_text()
            check(
                "详情公式渲染",
                detail_katex > 0 and "$" not in detail_text.split("答案")[0],
                {"katex": detail_katex, "head": detail_text[:160]},
            )
            page.wait_for_timeout(400)
            page.screenshot(path=str(shots / "detail.png"), full_page=False)

            frame_metrics = frame.locator("body").evaluate(
                """() => {
                    const el = document.documentElement;
                    const shell = document.querySelector('.cb-body');
                    return {
                        scrollWidth: el.scrollWidth,
                        clientWidth: el.clientWidth,
                        bodyScrollWidth: document.body.scrollWidth,
                        shellScrollWidth: shell ? shell.scrollWidth : null,
                        shellClientWidth: shell ? shell.clientWidth : null
                    };
                }"""
            )
            check(
                "插件内无横向溢出",
                frame_metrics["scrollWidth"] <= frame_metrics["clientWidth"] + 1,
                frame_metrics,
            )
            page_metrics = page.evaluate(
                "() => ({scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth})"
            )
            check("宿主无横向溢出", page_metrics["scrollWidth"] <= page_metrics["clientWidth"] + 1, page_metrics)

            page.screenshot(path=str(shots / "workspace-full.png"), full_page=True)
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = all(item["ok"] for item in result["checks"]) and not result["page_errors"]
    result["console_errors"] = result["console_errors"][:20]
    (work / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(("PASS" if result["ok"] else "FAIL") + f" · {len(result['checks'])} 项检查 · {work}")
    for item in result["checks"]:
        print(("  ✓ " if item["ok"] else "  ✗ ") + item["name"])
    if result["page_errors"]:
        print("页面异常：" + " | ".join(result["page_errors"]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

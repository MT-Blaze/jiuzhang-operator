# -*- coding: utf-8 -*-
"""handout 真机压测：Markdown 实时排版 → A4 纸面取证。

用法：``.venv/Scripts/python.exe tools/handout_probe.py <tag>``

隔离：只复制 handout 插件与独立数据目录，另起端口，不碰本机 data/。
检查项：
- 打开即载入示例讲义，自动分页 > 1 页，首屏排版 < 1000ms；
- 逐页无纵向/横向溢出，公式块不越界，正文不越出纸张；
- KaTeX 真渲染、字体已加载；
- 左侧改稿后 160ms 防抖内自动重排，页数与字数跟随；
- 右栏切「大字」字号后整篇重排且不溢页；
- 宿主 1440×900 无横向溢出。
"""

from __future__ import annotations

import json
import os
import re
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
PLUGIN_ID = "org.jiuzhang.handout"


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


def wait_reflow(metrics, previous: int, timeout: float = 30) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = metrics.get_attribute("data-reflow")
        if raw and int(raw) > previous:
            return int(raw)
        time.sleep(0.05)
    raise AssertionError(f"等重排序号 > {previous} 超时（{timeout}s）")


def wait_stable(metrics, idle_ms: int = 350, timeout: float = 10) -> int:
    """等重排序号连续 idle_ms 不再增长，避免读到上一轮刚写的指标。"""
    deadline = time.time() + timeout
    last = metrics.get_attribute("data-reflow")
    stable_since = time.time()
    while time.time() < deadline:
        time.sleep(0.05)
        current = metrics.get_attribute("data-reflow")
        if current != last:
            last = current
            stable_since = time.time()
        elif (time.time() - stable_since) * 1000 >= idle_ms:
            return int(current or 0)
    raise AssertionError(f"重排在 {timeout}s 内未稳定")


def body_overflow(frame) -> dict:
    return frame.locator("body").evaluate(
        """() => {
            const bodies = Array.from(document.querySelectorAll('.hp-page-body'));
            const vertical = bodies.map((node, index) => ({
                page: index + 1,
                scrollHeight: node.scrollHeight,
                clientHeight: node.clientHeight
            })).filter(item => item.scrollHeight > item.clientHeight + 1);
            const horizontal = bodies.map((node, index) => ({
                page: index + 1,
                scrollWidth: node.scrollWidth,
                clientWidth: node.clientWidth
            })).filter(item => item.scrollWidth > item.clientWidth + 1);
            const wideMath = Array.from(document.querySelectorAll('.hp-math-block')).map((node, index) => ({
                index: index + 1,
                scrollWidth: node.scrollWidth,
                clientWidth: node.clientWidth
            })).filter(item => item.scrollWidth > item.clientWidth + 2);
            const pages = Array.from(document.querySelectorAll('.hp-page'));
            const outOfPage = pages.filter(node => {
                const body = node.querySelector('.hp-page-body');
                if (!body) return false;
                const pageRect = node.getBoundingClientRect();
                const bodyRect = body.getBoundingClientRect();
                return bodyRect.bottom > pageRect.bottom + 1 || bodyRect.right > pageRect.right + 1;
            }).length;
            return {
                pages: pages.length,
                vertical: vertical,
                horizontal: horizontal,
                wideMath: wideMath,
                overflowNodes: document.querySelectorAll('[data-overflow="true"]').length,
                outOfPage: outOfPage
            };
        }"""
    )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "handout_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    shots.mkdir(parents=True)
    shutil.copytree(ROOT / "plugins" / PLUGIN_ID, plugins_dir / PLUGIN_ID)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = "handout-probe-token"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "metrics": {}}

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

            item = page.locator(".ws-plugin-item", has_text="讲义排版").first
            expect(item).to_be_visible(timeout=10000)
            check("左栏出现讲义排版", True)
            item.click()

            panel = page.locator("#wsPanel_plugin_org_jiuzhang_handout")
            frame_locator = panel.frame_locator(".ws-plugin-frame")
            metrics = frame_locator.locator("#hpMetrics")
            try:
                seq = wait_reflow(metrics, -1, timeout=40)
            except AssertionError:
                page.screenshot(path=str(shots / "timeout.png"))
                print("console:", result["console_errors"][:8])
                print("page:", result["page_errors"][:8])
                print("panel:", panel.inner_html()[:1200])
                raise

            expect(metrics).to_have_attribute("data-pages", re.compile(r"\d+"), timeout=30000)
            seq = wait_stable(metrics)
            first_ms = metrics.get_attribute("data-render-ms") or "0"
            pages = metrics.get_attribute("data-pages") or "0"
            blocks = metrics.get_attribute("data-blocks") or "0"
            chars = metrics.get_attribute("data-chars") or "0"
            overflow_attr = metrics.get_attribute("data-overflow") or "?"
            result["metrics"]["initial"] = {
                "pages": pages, "blocks": blocks, "chars": chars,
                "render_ms": first_ms, "overflow": overflow_attr, "reflow": seq,
            }
            check("示例讲义自动入纸", int(chars) > 500, {"chars": chars})
            check("首屏排版 < 1000ms", 0 < float(first_ms) < 1000, {"render_ms": first_ms})
            check("自动分页成多页", int(pages) > 1, {"pages": pages})
            check("块级元素已解析", int(blocks) >= 10, {"blocks": blocks})
            check("无超高块", overflow_attr == "0", {"overflow": overflow_attr})

            layout = body_overflow(frame_locator)
            result["metrics"]["layout_initial"] = layout
            check("逐页无纵向溢出", layout["vertical"] == [], layout["vertical"])
            check("逐页无横向溢出", layout["horizontal"] == [], layout["horizontal"])
            check("公式块不越界", layout["wideMath"] == [], layout["wideMath"])
            check("正文未越出纸张", layout["outOfPage"] == 0, {"out_of_page": layout["outOfPage"]})

            math_count = frame_locator.locator(".katex").count()
            check("公式真渲染为 KaTeX", math_count > 0, {"katex": math_count})
            fonts = frame_locator.locator("body").evaluate(
                """async () => {
                    await document.fonts.ready;
                    return {
                        status: document.fonts.status,
                        check: document.fonts.check('16px KaTeX_Main'),
                        loaded: Array.from(document.fonts).filter(f => f.status === 'loaded').length
                    };
                }"""
            )
            check("KaTeX 字体已加载", bool(fonts.get("check")), fonts)

            # 表格必须是真表格，不能把 Markdown 管道符原样印出来
            table_cells = frame_locator.locator(".hp-page-body table td, .hp-page-body table th").count()
            check("Markdown 表格已落成真表格", table_cells >= 8, {"cells": table_cells})

            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "handout-initial.png"))
            page_info = frame_locator.locator("body").evaluate(
                """() => Array.from(document.querySelectorAll('.hp-page-body')).map((body, index) => ({
                    page: index + 1,
                    children: body.children.length,
                    text: (body.innerText || '').replace(/\\s+/g, ' ').slice(0, 40),
                    scrollHeight: body.scrollHeight
                }))"""
            )
            result["metrics"]["pages"] = page_info
            check("每页都有内容", all(item["children"] > 0 for item in page_info), page_info)
            frame_locator.locator(".hp-page-wrap").nth(1).evaluate(
                "node => node.scrollIntoView({block: 'start'})"
            )
            page.wait_for_timeout(250)
            page.screenshot(path=str(shots / "handout-page2.png"))
            frame_locator.locator(".hp-page-wrap").first.evaluate(
                "node => node.scrollIntoView({block: 'start'})"
            )

            # ---------- 实时改稿 ----------
            textarea = frame_locator.locator("#hpInput")
            original = textarea.input_value()
            extra = "\n\n## 六、追加章节\n\n实时排版验证：改变左侧原稿后，右侧应在一瞬之内重新分页。" \
                    "设 $a>0$，则 $a+\\dfrac{1}{a} \\ge 2$，当且仅当 $a=1$ 时取等号。\n"
            textarea.fill(original + extra)
            seq_live = wait_reflow(metrics, seq, timeout=15)
            live_ms = metrics.get_attribute("data-render-ms") or "0"
            live_chars = int(metrics.get_attribute("data-chars") or "0")
            live_pages = metrics.get_attribute("data-pages") or "0"
            result["metrics"]["live"] = {
                "render_ms": live_ms, "chars": live_chars, "pages": live_pages, "reflow": seq_live,
            }
            check("改稿触发自动重排", seq_live > seq, {"from": seq, "to": seq_live})
            check("字数跟随原稿", live_chars > int(chars), {"before": chars, "after": live_chars})
            check("实时重排 < 1000ms", 0 < float(live_ms) < 1000, {"render_ms": live_ms})
            layout_live = body_overflow(frame_locator)
            check("改稿后仍无纵向溢出", layout_live["vertical"] == [], layout_live["vertical"])
            page.wait_for_timeout(250)
            page.screenshot(path=str(shots / "handout-live-edit.png"))

            # ---------- 字号切换 ----------
            size = page.locator('#wsPluginControls select[data-ui-key="size"]')
            expect(size).to_be_visible(timeout=10000)
            size.select_option("大字")
            seq_big = wait_reflow(metrics, seq_live, timeout=15)
            big_ms = metrics.get_attribute("data-render-ms") or "0"
            result["metrics"]["large"] = {
                "render_ms": big_ms,
                "pages": metrics.get_attribute("data-pages"),
                "overflow": metrics.get_attribute("data-overflow"),
                "size": metrics.get_attribute("data-size"),
            }
            check("大字模式已生效", metrics.get_attribute("data-size") == "large")
            check("大字重排 < 1000ms", 0 < float(big_ms) < 1000, {"render_ms": big_ms})
            layout_big = body_overflow(frame_locator)
            check("大字模式无纵向溢出", layout_big["vertical"] == [], layout_big["vertical"])
            page.wait_for_timeout(250)
            page.screenshot(path=str(shots / "handout-large.png"))
            size.select_option("标准")
            wait_reflow(metrics, seq_big, timeout=15)

            # ---------- 宿主边界 ----------
            size_host = page.locator("body").evaluate(
                "() => ({scrollWidth: document.body.scrollWidth, clientWidth: document.documentElement.clientWidth})"
            )
            result["metrics"]["host"] = size_host
            check("宿主无横向溢出", size_host["scrollWidth"] <= size_host["clientWidth"] + 1, size_host)

            browser.close()
    except Exception as exc:  # noqa: BLE001 - 探针要把失败原样落盘
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = bool(result["checks"]) and all(item["ok"] for item in result["checks"]) \
        and not result["page_errors"] and "error" not in result
    (work / "probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    passed = sum(1 for item in result["checks"] if item["ok"])
    print(("PASS" if result["ok"] else "FAIL") + f" · {passed} 项检查 · {work}")
    for item in result["checks"]:
        print(("  ✓ " if item["ok"] else "  ✗ ") + item["name"])
    if result["console_errors"]:
        print("console:", result["console_errors"][:8])
    if result["page_errors"]:
        print("pageerrors:", result["page_errors"][:8])
    if "error" in result:
        print("error:", result["error"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

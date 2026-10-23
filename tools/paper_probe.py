# -*- coding: utf-8 -*-
"""paper-gen 真机压测：50 道长题入篮 → A4 重排 → 视觉与性能取证。

用法：``.venv/Scripts/python.exe tools/paper_probe.py <tag>``

隔离：插件、数据都复制到 ``.system_generated/paper_probe/<tag>/``，另起端口，
不碰本机 data/。检查项：
- 50 题全部进题篮，组卷页显示 50 题 / 多页 / 渲染 < 1000ms；
- 每页正文 ``scrollHeight <= clientHeight``，无 ``[data-overflow]``；
- KaTeX 节点与字体真实加载；公式块不横向溢出；
- 右栏切「显示答案」「紧凑」后重排完成且 < 4000ms（记录真实耗时：
  带答案时 50 题解析全文重建，KaTeX 布局耗时随内容量增长，属已知欠账）；
- 题库再入篮一题 → 组卷页经 basket.changed 自动 +1；
- 组卷侧栏移除一题 → 题篮回到 50 且预览重排。
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BANK_ID = "org.jiuzhang.core-bank"
PAPER_ID = "org.jiuzhang.paper-gen"
PAGE_BODY_H = 925


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


def http_json(url: str, method: str = "GET", body: dict | None = None, token: str | None = None) -> dict:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-JZO-Token"] = token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def longest_questions(limit: int) -> list[str]:
    """按题干 + 选项 + 解析总字数挑最长的真题，专挑排版最难的。"""
    db_path = ROOT / "plugins" / BANK_ID / "bank" / "bank.db"
    connection = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """SELECT id FROM questions
               ORDER BY (length(stem) + length(COALESCE(solution, ''))
                         + length(COALESCE(options, ''))) DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    finally:
        connection.close()
    return [row[0] for row in rows]


def wait_reflow(metrics, previous: int, timeout: float = 30) -> int:
    """等 data-reflow 序号增长：比等某个 DOM 节点出现更可靠，重排是一整轮的。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        raw = metrics.get_attribute("data-reflow")
        if raw and int(raw) > previous:
            return int(raw)
        time.sleep(0.05)
    raise AssertionError(f"等重排序号 > {previous} 超时（{timeout}s）")


def body_overflow(frame) -> dict:
    """逐页检查：纵向溢出、横向溢出、超高块与公式块越界。"""
    return frame.locator("body").evaluate(
        """() => {
            const bodies = Array.from(document.querySelectorAll('.pg-page-body'));
            const vertical = bodies.map((node, index) => ({
                page: index + 1,
                scrollHeight: node.scrollHeight,
                clientHeight: node.clientHeight
            })).filter(item => item.scrollHeight > item.clientHeight + 1);
            const verticalDetail = Array.from(document.querySelectorAll('.pg-page-body'))
                .map((node, index) => ({ node, index }))
                .filter(item => item.node.scrollHeight > item.node.clientHeight + 1)
                .map(item => {
                    const style = getComputedStyle(item.node);
                    return {
                        page: item.index + 1,
                        scrollHeight: item.node.scrollHeight,
                        clientHeight: item.node.clientHeight,
                        fontSize: style.fontSize,
                        lineHeight: style.lineHeight,
                        children: Array.from(item.node.children).map(child => ({
                            cls: child.className,
                            declared: child.getAttribute('data-height'),
                            offset: child.offsetHeight,
                            rect: Math.round(child.getBoundingClientRect().height * 10) / 10,
                            text: (child.textContent || '').slice(0, 60)
                        }))
                    };
                });
            const pages = Array.from(document.querySelectorAll('.pg-page'));
            const horizontal = bodies.map((node, index) => ({
                page: index + 1,
                scrollWidth: node.scrollWidth,
                clientWidth: node.clientWidth
            })).filter(item => item.scrollWidth > item.clientWidth + 1);
            const wideMath = Array.from(document.querySelectorAll('.pg-math-block')).map((node, index) => ({
                index: index + 1,
                scrollWidth: node.scrollWidth,
                clientWidth: node.clientWidth
            })).filter(item => item.scrollWidth > item.clientWidth + 2);
            const outOfPage = pages.filter(node => {
                const body = node.querySelector('.pg-page-body');
                if (!body) return false;
                const pageRect = node.getBoundingClientRect();
                const bodyRect = body.getBoundingClientRect();
                return bodyRect.bottom > pageRect.bottom + 1 || bodyRect.right > pageRect.right + 1;
            }).length;
            return {
                pages: pages.length,
                vertical: vertical,
                verticalDetail: verticalDetail,
                horizontal: horizontal,
                wideMath: wideMath,
                overflowNodes: document.querySelectorAll('[data-overflow="true"]').length,
                outOfPage: outOfPage,
                previews: bodies.map(node => node.clientHeight)
            };
        }"""
    )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "paper_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    shots.mkdir(parents=True)
    (data_dir / ".seed-demo-bank.installed").write_text("probe\n", encoding="utf-8")

    for plugin_id in (BANK_ID, PAPER_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = "paper-probe-token"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "metrics": {}}
    seeded: list[str] = []

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process)

        # ---------- 数据准备：50 道最长真题 ----------
        seeded = longest_questions(50)
        token = http_json(base + "/api/settings").get("local_token")
        added = http_json(
            base + "/api/basket",
            method="POST",
            body={"plugin_id": BANK_ID, "ids": seeded},
            token=token,
        )
        check("题篮灌入 50 道长题", added.get("total") == 50, {"total": added.get("total")})

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="组卷排版").first
            expect(item).to_be_visible(timeout=10000)
            check("左栏出现组卷排版", True)
            item.click()

            paper_panel = page.locator("#wsPanel_plugin_org_jiuzhang_paper-gen")
            frame_locator = paper_panel.frame_locator(".ws-plugin-frame")
            metrics = frame_locator.locator("#pgMetrics")
            try:
                seq = wait_reflow(metrics, -1, timeout=40)
            except AssertionError:
                page.screenshot(path=str(shots / "timeout.png"))
                print("console:", result["console_errors"][:8])
                print("page:", result["page_errors"][:8])
                print("panel:", paper_panel.inner_html()[:1200])
                raise
            expect(metrics).to_have_attribute("data-questions", "50", timeout=30000)

            first = metrics.get_attribute("data-render-ms") or "0"
            pages = metrics.get_attribute("data-pages") or "0"
            overflow_attr = metrics.get_attribute("data-overflow") or "?"
            result["metrics"]["normal"] = {
                "questions": metrics.get_attribute("data-questions"),
                "pages": pages,
                "render_ms": first,
                "overflow": overflow_attr,
            }
            check("50 题全部入卷", metrics.get_attribute("data-questions") == "50")
            check("A4 渲染 < 1000ms", 0 < float(first) < 1000, {"render_ms": first})
            check("自动分页成多页", int(pages) > 1, {"pages": pages})
            check("无超高题块", overflow_attr == "0", {"overflow": overflow_attr})

            layout = body_overflow(frame_locator)
            result["metrics"]["layout_normal"] = layout
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

            # 图片即使按预留尺寸排版，也要等它们真正解码后再复核一次
            frame_locator.locator("body").evaluate(
                """async () => {
                    const images = Array.from(document.querySelectorAll('.pg-image'));
                    await Promise.all(images.map(img => img.complete ? null : new Promise(resolve => {
                        img.addEventListener('load', resolve, { once: true });
                        img.addEventListener('error', resolve, { once: true });
                    })));
                }"""
            )
            images = frame_locator.locator(".pg-image").evaluate_all(
                """els => els.map(img => ({
                    src: img.getAttribute('src'),
                    complete: img.complete,
                    naturalHeight: img.naturalHeight,
                    boxHeight: Math.round(img.getBoundingClientRect().height)
                }))"""
            )
            check("配图加载且按预留高度占位",
                  bool(images) and all(item["complete"] and item["naturalHeight"] > 0 for item in images),
                  {"images": len(images), "detail": images[:3]})
            layout_after_images = body_overflow(frame_locator)
            check("图片解码后仍无纵向溢出", layout_after_images["vertical"] == [],
                  layout_after_images["vertical"])

            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "a4-normal-top.png"))
            # 滚到第二页再截一张，核对分页边界与页眉页脚
            frame_locator.locator(".pg-page-wrap").nth(1).scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "a4-normal-page2.png"))
            frame_locator.locator(".pg-page-wrap").first.scroll_into_view_if_needed()
            page.wait_for_timeout(200)

            # ---------- 右栏：显示答案 ----------
            answers = page.locator('#wsPluginControls select[data-ui-key="answers"]')
            expect(answers).to_be_visible(timeout=10000)
            answers.select_option("显示")
            seq = wait_reflow(metrics, seq)
            expect(metrics).to_have_attribute("data-questions", "50", timeout=30000)
            expect(frame_locator.locator(".pg-answer").first).to_be_visible(timeout=20000)
            answers_ms = metrics.get_attribute("data-render-ms") or "0"
            answer_count = frame_locator.locator(".pg-answer").count()
            result["metrics"]["answers"] = {"render_ms": answers_ms, "answers": answer_count,
                                            "pages": metrics.get_attribute("data-pages")}
            result["metrics"]["timing_answers"] = metrics.evaluate("el => Object.assign({}, el.dataset)")
            # 带答案时每题要重建「答案 + 解析」全文，KaTeX 布局量约为首屏的三倍；
            # 记录真实耗时并设 4s 回归上限，避免性能继续劣化。
            check("显示答案后重排完成（记录耗时）", 0 < float(answers_ms) < 4000,
                  {"render_ms": answers_ms})
            check("答案块已渲染", answer_count > 0, {"answers": answer_count})
            layout_answers = body_overflow(frame_locator)
            result["metrics"]["layout_answers"] = layout_answers
            check("带答案仍无纵向溢出", layout_answers["vertical"] == [], layout_answers["vertical"])
            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "a4-answers.png"))

            # ---------- 右栏：紧凑密度 ----------
            density = page.locator('#wsPluginControls select[data-ui-key="density"]')
            density.select_option("紧凑")
            seq = wait_reflow(metrics, seq)
            expect(frame_locator.locator("#pgPages")).to_have_attribute("data-density", "compact", timeout=30000)
            compact_ms = metrics.get_attribute("data-render-ms") or "0"
            result["metrics"]["compact"] = {"render_ms": compact_ms,
                                            "pages": metrics.get_attribute("data-pages"),
                                            "overflow": metrics.get_attribute("data-overflow")}
            check("紧凑密度重排完成（记录耗时）", 0 < float(compact_ms) < 4000,
                  {"render_ms": compact_ms})
            layout_compact = body_overflow(frame_locator)
            result["metrics"]["layout_compact"] = layout_compact
            check("紧凑模式逐页无溢出", layout_compact["vertical"] == [], layout_compact["vertical"])
            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "a4-compact.png"))
            density.select_option("标准")
            expect(frame_locator.locator("#pgPages")).to_have_attribute("data-density", "normal", timeout=30000)
            answers.select_option("隐藏")
            expect(frame_locator.locator(".pg-answer")).to_have_count(0, timeout=30000)
            seq = int(metrics.get_attribute("data-reflow") or "0")

            # ---------- EventBus：题库再入篮一题 → 组卷自动 +1 ----------
            page.locator(".ws-plugin-item", has_text="真题题库").first.click()
            bank_panel = page.locator("#wsPanel_plugin_org_jiuzhang_core-bank")
            bank_frame = bank_panel.frame_locator(".ws-plugin-frame")
            expect(bank_frame.locator(".cb-row").first).to_be_visible(timeout=20000)
            seeded_set = set(seeded)
            row_ids = bank_frame.locator(".cb-row").evaluate_all(
                "els => els.map(el => el.getAttribute('data-id'))"
            )
            candidate = next((rid for rid in row_ids if rid not in seeded_set), None)
            check("找到未入篮的真题", bool(candidate), {"id": candidate})
            if candidate:
                row = bank_frame.locator(f'.cb-row[data-id="{candidate}"]')
                row.locator("button", has_text="入篮").click()
                expect(bank_frame.locator("#cbBasketCount")).to_contain_text("题篮 51", timeout=20000)
                page.locator(".ws-tab", has_text="组卷排版").first.click()
                seq = wait_reflow(metrics, seq)
                expect(metrics).to_have_attribute("data-questions", "51", timeout=30000)
                check("basket.changed 驱动组卷 +1", True, {"candidate": candidate})
                page.wait_for_timeout(400)
                basket = json.loads((data_dir / "basket.json").read_text(encoding="utf-8"))
                check("题篮落盘 51 题", len(basket.get("items") or []) == 51,
                      {"items": len(basket.get("items") or [])})

            # ---------- 侧栏移除一题 → 回到 50 ----------
            paper_frame = paper_panel.frame_locator(".ws-plugin-frame")
            expect(paper_frame.locator(".pg-item").first).to_be_visible(timeout=20000)
            paper_frame.locator(".pg-remove").first.click()
            seq = wait_reflow(metrics, seq)
            expect(metrics).to_have_attribute("data-questions", "50", timeout=30000)
            check("侧栏移除一题 → 50", True)
            page.wait_for_timeout(400)
            basket = json.loads((data_dir / "basket.json").read_text(encoding="utf-8"))
            check("题篮文件同步回 50", len(basket.get("items") or []) == 50,
                  {"items": len(basket.get("items") or [])})
            page.screenshot(path=str(shots / "a4-after-remove.png"))

            host_metrics = page.evaluate(
                "() => ({scrollWidth: document.documentElement.scrollWidth,"
                " clientWidth: document.documentElement.clientWidth})"
            )
            check("宿主无横向溢出",
                  host_metrics["scrollWidth"] <= host_metrics["clientWidth"] + 1, host_metrics)

            result["console_errors"] = result["console_errors"][:20]
            browser.close()
    finally:
        if result["page_errors"]:
            print("页面异常：" + " | ".join(result["page_errors"][:5]))
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = all(item["ok"] for item in result["checks"]) and not result["page_errors"]
    (work / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(("PASS" if result["ok"] else "FAIL") + f" · {len(result['checks'])} 项检查 · {work}")
    for item in result["checks"]:
        print(("  ✓ " if item["ok"] else "  ✗ ") + item["name"])
    if result["page_errors"]:
        print("页面异常：" + " | ".join(result["page_errors"]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

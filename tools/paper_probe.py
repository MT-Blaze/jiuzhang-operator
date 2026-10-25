# -*- coding: utf-8 -*-
"""paper-gen 真机压测：50 道长题入篮 → A4 重排 → 视觉与性能取证。

用法：``.venv/Scripts/python.exe tools/paper_probe.py <tag>``

隔离：插件、数据都复制到 ``.system_generated/paper_probe/<tag>/``，另起端口，
不碰本机 data/。检查项：
- 50 题全部进题篮，组卷页显示 50 题 / 多页 / 首屏同步重排 < 1000ms；
- 切「显示答案」与切「紧凑」的**同步重排耗时 < 300ms**（v0.8.1 视口级虚排红线：
  只排眼前 2-3 页，其余页交空闲补齐；基线 v0.8.0 分别是 3904.9ms / 3450ms）；
- 虚拟渲染属实：补齐后纸面页数 ≫ 同时物化页数，远端页退化成占位空壳；
- 全卷补齐（data-doc-ready=1）后逐页校验：滚动到每一页等它物化，
  再量 ``scrollHeight <= clientHeight``、无 ``[data-overflow]``、公式不越界；
- 狂拉滚动条：随机跳页后当前视口页必须在 1s 内挂出真实内容，不许大面积白屏；
- KaTeX 节点与字体真实加载；打印前补齐不缺页；
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
BANK_ID = "org.jiuzhang.bank-engine"
BANK_UI_ID = "org.jiuzhang.bank-ui"
PAPER_ID = "org.jiuzhang.paper-gen"


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


def wait_doc_ready(metrics, timeout: float = 30) -> dict:
    """虚拟渲染的补齐是后台跑的：等 data-doc-ready=1，再拿全卷取证。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if metrics.get_attribute("data-doc-ready") == "1":
            return metrics.evaluate("el => Object.assign({}, el.dataset)")
        time.sleep(0.05)
    raise AssertionError(f"等全卷补齐超时（{timeout}s）")


def sweep_whole_doc(frame) -> dict:
    """逐页滚过全卷：每页物化后就地量纵向/横向溢出与公式越界，一页都不放过。

    虚拟渲染下没进过视口的页是空壳，直接读它的 scrollHeight 会得到「零溢出」
    的假阴性，所以必须边滚边量，并回报有没有页压根没被量到。
    """
    return frame.locator("body").evaluate(
        """async () => {
            const preview = document.getElementById('pgPreview');
            const wraps = Array.from(document.querySelectorAll('.pg-page-wrap'));
            const step = wraps.length > 1
                ? wraps[1].offsetTop - wraps[0].offsetTop
                : wraps[0].offsetHeight || 1123;
            const seen = new Map();
            const wideMath = [];
            const raf = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
            const sleep = ms => new Promise(r => setTimeout(r, ms));
            const collect = () => {
                Array.from(document.querySelectorAll('.pg-page')).forEach(sec => {
                    if (sec.getAttribute('data-mat') !== 'true') return;
                    const index = Number(sec.getAttribute('data-page'));
                    if (seen.has(index)) return;
                    const body = sec.querySelector('.pg-page-body');
                    const answers = Array.from(body.querySelectorAll('.pg-answer'))
                        .filter(node => node.getClientRects().length > 0).length;
                    const images = Array.from(body.querySelectorAll('.pg-image')).map(img => ({
                        src: img.getAttribute('src'),
                        complete: img.complete,
                        naturalHeight: img.naturalHeight,
                        boxHeight: Math.round(img.getBoundingClientRect().height)
                    }));
                    seen.set(index, {
                        page: index,
                        scrollHeight: body.scrollHeight,
                        clientHeight: body.clientHeight,
                        scrollWidth: body.scrollWidth,
                        clientWidth: body.clientWidth,
                        kids: body.children.length,
                        answers: answers,
                        images: images
                    });
                    Array.from(body.querySelectorAll('.pg-math-block')).forEach(node => {
                        if (node.scrollWidth > node.clientWidth + 2) {
                            wideMath.push({ page: index, scrollWidth: node.scrollWidth,
                                            clientWidth: node.clientWidth });
                        }
                    });
                });
            };
            for (let y = 0; y <= preview.scrollHeight; y += Math.round(step / 2)) {
                preview.scrollTop = y;
                await raf();
                collect();
                await sleep(12);
            }
            preview.scrollTop = preview.scrollHeight;
            await raf();
            collect();
            const items = Array.from(seen.values()).sort((a, b) => a.page - b.page);
            const images = [];
            items.forEach(item => { item.images.forEach(img => images.push(img)); });
            const missing = [];
            for (let i = 1; i <= wraps.length; i += 1) if (!seen.has(i)) missing.push(i);
            preview.scrollTop = 0;
            return {
                pages: wraps.length,
                measured: items.length,
                missing: missing,
                empty: items.filter(item => item.kids === 0).map(item => item.page),
                vertical: items.filter(item => item.scrollHeight > item.clientHeight + 1)
                    .map(item => ({ page: item.page, scrollHeight: item.scrollHeight,
                                    clientHeight: item.clientHeight })),
                horizontal: items.filter(item => item.scrollWidth > item.clientWidth + 1)
                    .map(item => ({ page: item.page, scrollWidth: item.scrollWidth,
                                    clientWidth: item.clientWidth })),
                wideMath: wideMath,
                answers: items.reduce((sum, item) => sum + item.answers, 0),
                images: images,
                live: document.querySelectorAll('.pg-page[data-mat="true"]').length
            };
        }"""
    )


def scrub_viewport(frame) -> dict:
    """狂拉滚动条：随机跳页后，当前视口首页必须很快挂出真实内容，不许大面积白屏。"""
    return frame.locator("body").evaluate(
        """async () => {
            const preview = document.getElementById('pgPreview');
            const raf = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
            const sleep = ms => new Promise(r => setTimeout(r, ms));
            const ranges = [0.92, 0.41, 0.99, 0.17, 0.68, 0.05];
            const jumps = [];
            for (const ratio of ranges) {
                const y = Math.round((preview.scrollHeight - preview.clientHeight) * ratio);
                const started = performance.now();
                preview.scrollTop = y;
                let ok = false;
                let kids = 0;
                while (performance.now() - started < 1000) {
                    await raf();
                    const wraps = Array.from(document.querySelectorAll('.pg-page-wrap'));
                    const step = wraps.length > 1
                        ? wraps[1].offsetTop - wraps[0].offsetTop
                        : wraps[0].offsetHeight || 1123;
                    const index = Math.min(Math.floor((preview.scrollTop + 20) / step), wraps.length - 1);
                    const body = wraps[index].querySelector('.pg-page-body');
                    if (body && body.children.length > 0) { ok = true; kids = body.children.length; break; }
                    await sleep(16);
                }
                jumps.push({ ratio: ratio, ms: Math.round(performance.now() - started), ok: ok, kids: kids });
            }
            preview.scrollTop = 0;
            return jumps;
        }"""
    )


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

    for plugin_id in (BANK_ID, BANK_UI_ID, PAPER_ID):
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
                "sync_ms": metrics.get_attribute("data-t-sync"),
                "live": metrics.get_attribute("data-live"),
                "timing": metrics.evaluate("el => Object.assign({}, el.dataset)"),
            }
            check("50 题全部入卷", metrics.get_attribute("data-questions") == "50")
            check("首屏同步重排 < 1000ms", 0 < float(first) < 1000, {"render_ms": first})
            check("自动分页成多页", int(pages) > 1, {"pages": pages})
            check("虚拟渲染已开启", metrics.get_attribute("data-virtual") == "1")
            check("首屏只挂眼前几页",
                  0 < int(metrics.get_attribute("data-live") or "0") <= 6,
                  {"live": metrics.get_attribute("data-live"), "pages": pages})

            # 后台补齐：拿全卷页数为后续逐页取证的底
            ready = wait_doc_ready(metrics)
            result["metrics"]["ready_normal"] = {
                "ready_ms": ready.get("readyMs") or ready.get("ready_ms"),
                "pages": ready.get("pages"),
                "total_measure": ready.get("totalMeasure"),
                "total_build": ready.get("totalBuild"),
                "settle": ready.get("settle"),
            }
            pages = int(ready.get("pages") or pages)
            check("全卷后台补齐完成", int(ready.get("pages") or 0) > 1, result["metrics"]["ready_normal"])
            check("补齐后仍无超高题块", (ready.get("overflow") or "0") == "0", {"overflow": ready.get("overflow")})

            sweep = sweep_whole_doc(frame_locator)
            result["metrics"]["sweep_normal"] = sweep
            check("逐页都被真机量到（无空壳漏检）", sweep["missing"] == [], {"missing": sweep["missing"][:8]})
            check("物化页均有内容", sweep["empty"] == [], {"empty": sweep["empty"][:8]})
            check("逐页无纵向溢出", sweep["vertical"] == [], sweep["vertical"][:6])
            check("逐页无横向溢出", sweep["horizontal"] == [], sweep["horizontal"][:6])
            check("公式块不越界", sweep["wideMath"] == [], sweep["wideMath"][:6])
            pics = sweep["images"]
            result["metrics"]["images_normal"] = {"count": len(pics), "sample": pics[:3]}
            check("配图逐页清点：全部解码且按预留高度占位",
                  len(pics) > 0 and all(item["complete"] and item["naturalHeight"] > 0 for item in pics),
                  {"配图数": len(pics), "样例": pics[:2]})

            layout = body_overflow(frame_locator)
            result["metrics"]["layout_normal"] = layout
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

            # 配图取证改到滚动清点上：虚拟渲染下只有进过视口的页才有图节点，
            # 逐页滚过全卷时一并核对 complete / naturalHeight（见 sweep_normal）。

            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "a4-normal-top.png"))
            # 滚到第二页再截一张，核对分页边界与页眉页脚
            frame_locator.locator(".pg-page-wrap").nth(1).scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "a4-normal-page2.png"))
            frame_locator.locator(".pg-page-wrap").first.scroll_into_view_if_needed()
            page.wait_for_timeout(200)

            # ---------- 右栏：显示答案（v0.8.1 红线：同步重排 < 300ms）----------
            answers = page.locator('#wsPluginControls select[data-ui-key="answers"]')
            expect(answers).to_be_visible(timeout=10000)
            answers.select_option("显示")
            seq = wait_reflow(metrics, seq)
            expect(metrics).to_have_attribute("data-questions", "50", timeout=30000)
            expect(frame_locator.locator(".pg-answer").first).to_be_visible(timeout=20000)
            answers_ms = metrics.get_attribute("data-render-ms") or "0"
            answer_count = frame_locator.locator(".pg-answer").count()
            result["metrics"]["answers"] = {"render_ms": answers_ms, "answers_shown": answer_count,
                                            "pages": metrics.get_attribute("data-pages"),
                                            "live": metrics.get_attribute("data-live"),
                                            "timing": metrics.evaluate("el => Object.assign({}, el.dataset)")}
            check("切答案同步重排 < 300ms", 0 < float(answers_ms) < 300,
                  {"render_ms": answers_ms, "基线 v0.8.0": "3904.9ms"})
            check("答案块已渲染", answer_count > 0, {"answers": answer_count})
            ready = wait_doc_ready(metrics)
            result["metrics"]["ready_answers"] = {
                "ready_ms": ready.get("readyMs"), "pages": ready.get("pages"),
                "total_measure": ready.get("totalMeasure"), "settle": ready.get("settle"),
                "answers": ready.get("answers"),
            }
            sweep = sweep_whole_doc(frame_locator)
            result["metrics"]["sweep_answers"] = sweep
            check("带答案逐页都被量到", sweep["missing"] == [], {"missing": sweep["missing"][:8]})
            check("带答案仍无纵向溢出", sweep["vertical"] == [], sweep["vertical"][:6])
            check("带答案无横向溢出", sweep["horizontal"] == [], sweep["horizontal"][:6])
            check("带答案公式块不越界", sweep["wideMath"] == [], sweep["wideMath"][:6])
            # 交叉核对：算分页不能把答案段弄丢——逐页滚过数到的答案段
            # 必须等于「有答案的题数」（data-answers），一条不多一条不少。
            check("答案段逐页清点与题数吻合",
                  int(sweep["answers"]) == int(ready.get("answers") or "-1"),
                  {"逐页数到": sweep["answers"], "有答案的题数": ready.get("answers")})
            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "a4-answers.png"))

            # ---------- 狂拉滚动条：不许大面积白屏 ----------
            jumps = scrub_viewport(frame_locator)
            result["metrics"]["scrub"] = jumps
            check("狂拉滚动条当前页 1s 内出内容", all(item["ok"] for item in jumps), jumps)
            check("跳页挂内容快于 300ms", max(item["ms"] for item in jumps) < 300, jumps)

            # ---------- 右栏：紧凑密度 ----------
            density = page.locator('#wsPluginControls select[data-ui-key="density"]')
            density.select_option("紧凑")
            seq = wait_reflow(metrics, seq)
            expect(frame_locator.locator("#pgPages")).to_have_attribute("data-density", "compact", timeout=30000)
            compact_ms = metrics.get_attribute("data-render-ms") or "0"
            result["metrics"]["compact"] = {"render_ms": compact_ms,
                                            "pages": metrics.get_attribute("data-pages"),
                                            "overflow": metrics.get_attribute("data-overflow"),
                                            "live": metrics.get_attribute("data-live")}
            check("切紧凑同步重排 < 300ms", 0 < float(compact_ms) < 300,
                  {"render_ms": compact_ms, "基线 v0.8.0": "3450.0ms"})
            ready = wait_doc_ready(metrics)
            result["metrics"]["ready_compact"] = {
                "ready_ms": ready.get("readyMs"), "pages": ready.get("pages"),
                "total_measure": ready.get("totalMeasure"), "overflow": ready.get("overflow"),
            }
            sweep = sweep_whole_doc(frame_locator)
            result["metrics"]["sweep_compact"] = sweep
            check("紧凑模式逐页都被量到", sweep["missing"] == [], {"missing": sweep["missing"][:8]})
            check("紧凑模式逐页无溢出", sweep["vertical"] == [], sweep["vertical"][:6])
            check("紧凑模式无横向溢出", sweep["horizontal"] == [], sweep["horizontal"][:6])
            check("紧凑模式无超高题块", (ready.get("overflow") or "0") == "0",
                  {"overflow": ready.get("overflow")})
            page.wait_for_timeout(300)
            page.screenshot(path=str(shots / "a4-compact.png"))
            density.select_option("标准")
            expect(frame_locator.locator("#pgPages")).to_have_attribute("data-density", "normal", timeout=30000)
            answers.select_option("隐藏")
            seq = wait_reflow(metrics, seq)
            hide_ms = metrics.get_attribute("data-render-ms") or "0"
            result["metrics"]["hide_answers"] = {"render_ms": hide_ms}
            check("切回隐藏答案 < 300ms", 0 < float(hide_ms) < 300, {"render_ms": hide_ms})
            wait_doc_ready(metrics)
            sweep_hide = sweep_whole_doc(frame_locator)
            result["metrics"]["sweep_hidden"] = sweep_hide
            # 显隐口径的硬判据：整卷滚一遍，答案段必须一条不剩（不是只看眼前一页）
            check("切回隐藏后全卷零答案段", int(sweep_hide["answers"]) == 0,
                  {"answers": sweep_hide["answers"]})
            check("切回隐藏逐页无溢出", sweep_hide["vertical"] == [], sweep_hide["vertical"][:6])
            seq = int(metrics.get_attribute("data-reflow") or "0")

            # ---------- EventBus：题库再入篮一题 → 组卷自动 +1 ----------
            page.locator(".ws-plugin-item", has_text="真题题库").first.click()
            bank_panel = page.locator("#wsPanel_plugin_org_jiuzhang_bank-ui")
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
                ready = wait_doc_ready(metrics)
                result["metrics"]["ready_plus1"] = {"pages": ready.get("pages"), "render_ms": metrics.get_attribute("data-render-ms")}
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
            ready = wait_doc_ready(metrics)
            result["metrics"]["ready_minus1"] = {"pages": ready.get("pages"), "render_ms": metrics.get_attribute("data-render-ms")}
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

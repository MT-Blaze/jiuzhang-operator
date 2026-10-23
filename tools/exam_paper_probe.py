# -*- coding: utf-8 -*-
"""试卷排版插件（org.jiuzhang.exam-paper）真机探针：军令 #13 任务 6。

用法：``.venv/Scripts/python.exe tools/exam_paper_probe.py <tag>``

隔离口径：``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` 指向
``.system_generated/exam-paper-probe/<tag>/``；把仓库里的 core-bank 与 exam-paper
各复制一份进去，不碰开发者 ``data/`` 与仓库 ``plugins/``。

判据：
  1. 插件被后端接受，左栏出现入口；点击后中栏开出沙箱舞台页；
  2. 题篮 6~8 道真题能排成 A4：大题标号、连续题号、选项、作答位都在；
  3. 纸面宽度 = 210mm（793.7px ± 2）；
  4. 切到「标准答题卡」后每页都有密封线，涂卡区气泡与作答框齐全，绝不回抄题干；
  5. 切回「日常小练」题干回来；
  6. 改卷名后纸面标题同步；
  7. 宿主页与插件页零未捕获 JS 错误。
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
PORT = 8795
BASE = f"http://127.0.0.1:{PORT}/workspace"
PLUGIN_ID = "org.jiuzhang.exam-paper"
BANK_ID = "org.jiuzhang.core-bank"


def wait_port(deadline_seconds: float) -> bool:
    deadline = time.time() + deadline_seconds
    while time.time() < deadline:
        with socket.socket() as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", PORT)) == 0:
                return True
        time.sleep(0.5)
    return False


def call(method: str, path: str, payload=None, token: str = ""):
    import urllib.error
    import urllib.request

    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=data, method=method)
    request.add_header("Accept", "application/json")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("X-JZO-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(text or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": text}


def seed_basket() -> list[str]:
    ids: list[str] = []
    for kind in ("single_choice", "multiple_choice", "fill_blank", "solution", "proof"):
        status, listing = call(
            "GET",
            f"/api/bank/plugins/{BANK_ID}/questions?type={kind}&page_size=2",
        )
        if status != 200:
            continue
        for item in listing.get("items", [])[:2]:
            if isinstance(item.get("id"), str):
                ids.append(item["id"])
    if not ids:
        return []
    status, settings = call("GET", "/api/settings")
    token = (settings or {}).get("local_token", "")
    status, body = call("POST", "/api/basket", {"plugin_id": BANK_ID, "ids": ids, "mode": "replace"}, token)
    if status != 200:
        return []
    return ids


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "exam-paper-probe" / tag
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    data_dir = out / "data"
    plugins_dir = out / "plugins"
    data_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "plugins" / BANK_ID, plugins_dir / BANK_ID)
    shutil.copytree(ROOT / "plugins" / PLUGIN_ID, plugins_dir / PLUGIN_ID)

    report = {"tag": tag, "checks": [], "console": [], "errors": [], "shots": [], "notes": {}}

    def check(name, ok, detail=""):
        report["checks"].append({"name": name, "ok": bool(ok), "detail": str(detail)[:400]})
        return bool(ok)

    env = dict(os.environ)
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
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

        status, listing = call("GET", "/api/plugins")
        ids = [item.get("id") for item in listing.get("plugins", [])]
        check("试卷插件被后端接受", status == 200 and PLUGIN_ID in ids,
              json.dumps(listing.get("rejected"), ensure_ascii=False)[:300])

        seeded = seed_basket()
        report["notes"]["seeded"] = seeded
        check("题篮灌入真实题目", len(seeded) >= 5, f"{len(seeded)} 道")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 950})
            page.on("console", lambda m: report["console"].append({"type": m.type, "text": m.text[:300]}))
            page.on("pageerror", lambda e: report["errors"].append(str(e)[:300]))

            def snap(step):
                png = out / f"{step}.png"
                page.screenshot(path=str(png))
                report["shots"].append(str(png))

            page.goto(BASE, wait_until="networkidle")
            page.wait_for_selector(f'.ws-plugin-item[data-plugin-id="{PLUGIN_ID}"]', timeout=20000)
            page.click(f'.ws-plugin-item[data-plugin-id="{PLUGIN_ID}"]')
            page.wait_for_selector("#wsCanvasBody iframe.ws-plugin-frame", timeout=20000)
            frame_handle = page.wait_for_selector("#wsCanvasBody iframe.ws-plugin-frame")
            check("舞台 iframe 沙箱为 allow-scripts allow-modals",
                  frame_handle.get_attribute("sandbox") == "allow-scripts allow-modals",
                  str(frame_handle.get_attribute("sandbox")))
            frame = frame_handle.content_frame()
            frame.wait_for_selector("#epRoot:not([hidden])", timeout=20000)
            frame.wait_for_selector(".ep-item", timeout=25000)
            page.wait_for_timeout(500)
            snap("10-practice")

            practice = frame.evaluate("""() => {
              const sheets = Array.from(document.querySelectorAll('.ep-paper > .ep-sheet'));
              const first = sheets[0];
              const text = document.querySelector('#epPaper').innerText;
              return {
                mode: document.querySelector('#epPaper').getAttribute('data-mode'),
                metrics: document.querySelector('#epMetrics').textContent,
                sheets: sheets.length,
                width: first ? Math.round(first.getBoundingClientRect().width) : 0,
                height: first ? Math.round(first.getBoundingClientRect().height) : 0,
                sections: Array.from(document.querySelectorAll('.ep-section-title')).map(n => n.textContent),
                nos: Array.from(document.querySelectorAll('.ep-item .ep-no')).map(n => n.textContent),
                options: document.querySelectorAll('.ep-options li').length,
                lines: document.querySelectorAll('.ep-line').length,
                works: document.querySelectorAll('.ep-work').length,
                title: (document.querySelector('.ep-paper-title') || {}).textContent || '',
                text: text.slice(0, 400)
              };
            }""")
            report["notes"]["practice"] = practice
            check("默认是日常小练模板", practice["mode"] == "practice", practice["mode"])
            check("题号连续且从 1 开始", practice["nos"][:1] == ["1."] and len(practice["nos"]) >= 5,
                  practice["nos"])
            check("大题标号齐全（选择题/填空题/解答题）",
                  any("一、选择题" in s for s in practice["sections"])
                  and any("二、填空题" in s for s in practice["sections"])
                  and any("三、解答题" in s for s in practice["sections"]),
                  practice["sections"])
            check("A4 纸面宽 210mm", abs(practice["width"] - 794) <= 2, practice["width"])
            check("A4 纸面高至少 297mm", practice["height"] >= 1120, practice["height"])
            check("选择题选项与填空横线都在", practice["options"] > 0 and practice["lines"] > 0,
                  json.dumps({"options": practice["options"], "lines": practice["lines"]}))
            check("解答题留白框存在", practice["works"] > 0, practice["works"])
            check("指标写明题数与页数", "题" in practice["metrics"] and "页" in practice["metrics"],
                  practice["metrics"])

            frame.click('button[data-mode="card"]')
            frame.wait_for_selector('.ep-sheet[data-kind="card"]', timeout=10000)
            page.wait_for_timeout(400)
            snap("20-card")
            card = frame.evaluate("""() => {
              const sheets = Array.from(document.querySelectorAll('.ep-sheet[data-kind="card"]'));
              return {
                modes: Array.from(document.querySelectorAll('.ep-mode')).map(b => [b.dataset.mode, b.getAttribute('aria-pressed')]),
                sheets: sheets.length,
                seals: document.querySelectorAll('.ep-seal').length,
                bubbles: document.querySelectorAll('.ep-bubble').length,
                boxes: document.querySelectorAll('.ep-answer-box').length,
                items: document.querySelectorAll('.ep-item').length,
                coverTitle: (document.querySelector('.ep-paper-title') || {}).textContent || '',
                meta: Array.from(document.querySelectorAll('.ep-card-meta label')).map(n => n.textContent.trim()),
                metrics: document.querySelector('#epMetrics').textContent
              };
            }""")
            report["notes"]["card"] = card
            check("标准答题卡模板生效", card["sheets"] >= 1 and card["items"] == 0,
                  json.dumps(card, ensure_ascii=False)[:300])
            check("每一页都有密封线", card["seals"] == card["sheets"], f"{card['seals']}/{card['sheets']}")
            check("涂卡区气泡存在", card["bubbles"] >= 4, card["bubbles"])
            check("主观题作答框存在", card["boxes"] >= 1, card["boxes"])
            check("封面含姓名/班级/考号/座位号", len(card["meta"]) == 4, card["meta"])
            check("模式按钮状态同步", ["card", "true"] in card["modes"], card["modes"])

            frame.fill("#epTitle", "高二 · 数列专项小练")
            page.wait_for_timeout(600)
            title = frame.evaluate("() => (document.querySelector('.ep-paper-title') || {}).textContent || ''")
            check("改卷名后纸面标题同步", title == "高二 · 数列专项小练", title)

            frame.click('button[data-mode="practice"]')
            frame.wait_for_selector(".ep-item", timeout=10000)
            page.wait_for_timeout(300)
            snap("30-back-to-practice")
            back = frame.evaluate("""() => ({
              items: document.querySelectorAll('.ep-item').length,
              sheets: document.querySelectorAll('.ep-sheet[data-kind="practice"]').length,
              mode: document.querySelector('#epPaper').getAttribute('data-mode')
            })""")
            report["notes"]["back"] = back
            check("切回日常小练后题干回来", back["mode"] == "practice" and back["items"] >= 5, back)

            frame.evaluate("() => window.dispatchEvent(new Event('beforeprint'))")
            page.wait_for_timeout(400)
            after_print = frame.evaluate("() => document.querySelectorAll('.ep-sheet').length")
            check("打印前重排不丢页", after_print >= 1, after_print)

            # ---- PDF 导出：打印态隔离 + 真实 A4 PDF ----
            frame.click('button[data-mode="card"]')
            frame.wait_for_selector('.ep-sheet[data-kind="card"]', timeout=10000)
            page.emulate_media(media="print")
            page.wait_for_timeout(400)
            printed_state = frame.evaluate("""() => {
              const sheet = document.querySelector('.ep-sheet');
              const top = document.querySelector('.ep-top');
              const cs = sheet ? getComputedStyle(sheet) : null;
              return {
                topHidden: top ? getComputedStyle(top).display === 'none' : false,
                sheetW: sheet ? Math.round(sheet.getBoundingClientRect().width) : 0,
                sheets: document.querySelectorAll('.ep-sheet').length,
                seals: document.querySelectorAll('.ep-seal').length,
                breakAfter: cs ? (cs.breakAfter || cs.pageBreakAfter) : ''
              };
            }""")
            report["notes"]["print"] = printed_state
            check("打印态工具条整块隐藏（PDF 不带网页按钮）",
                  printed_state["topHidden"], printed_state)
            check("打印态纸面宽 210mm", abs(printed_state["sheetW"] - 794) <= 2,
                  printed_state["sheetW"])
            check("打印态每页都有密封线",
                  printed_state["seals"] == printed_state["sheets"] and printed_state["sheets"] >= 1,
                  f"{printed_state['seals']}/{printed_state['sheets']}")
            check("打印态每页强制分页", printed_state["breakAfter"] == "page",
                  printed_state["breakAfter"])
            snap("40-print-card")
            page.emulate_media(media="screen")

            # 沙箱必须放行 window.print()：Chromium 对缺 allow-modals 的沙箱会静默忽略。
            console_before = len(report["console"])
            frame.evaluate("() => window.print()")
            page.wait_for_timeout(600)
            ignored = [entry for entry in report["console"][console_before:]
                       if "Ignored call to 'print()'" in entry["text"]]
            check("沙箱放行 window.print（allow-modals）", not ignored,
                  json.dumps(ignored[:2], ensure_ascii=False))

            # 用同一份纸面与样式生成 A4 PDF，核对页数和不空白。
            paper_html = frame.evaluate(
                "() => { const p = document.getElementById('epPaper'); return p ? p.outerHTML : ''; }")
            paper_css = page.evaluate(
                """async () => (await (await fetch('/plugin-assets/org.jiuzhang.exam-paper/dist/plugin.css',
                    {cache: 'no-store'})).text())""")
            pdf_page = browser.new_page()
            origin = f"http://127.0.0.1:{PORT}"
            pdf_page.set_content(
                "<!doctype html><html><head><meta charset='utf-8'>"
                + f"<base href='{origin}/'>"
                + f"<link rel='stylesheet' href='{origin}/static/vendor/katex/katex.min.css'>"
                + "<style>" + paper_css + "</style></head><body>"
                + "<div id='epRoot' class='ep-root'><main class='ep-desk'><div class='ep-zoom'>"
                + paper_html + "</div></main></div></body></html>",
                wait_until="networkidle")
            pdf_path = out / "exam-paper-a4.pdf"
            pdf_page.pdf(path=str(pdf_path), format="A4", print_background=True)
            pdf_page.close()
            raw = pdf_path.read_bytes()
            import re as _re
            page_count = len(_re.findall(rb"/Type\s*/Page[^s]", raw))
            report["notes"]["pdf"] = {"path": str(pdf_path), "bytes": len(raw), "pages": page_count}
            check("A4 PDF 生成且非空",
                  raw.startswith(b"%PDF") and len(raw) > 20000, len(raw))
            check("PDF 页数与纸面页数一致",
                  page_count == printed_state["sheets"], f"{page_count}/{printed_state['sheets']}")

            check("宿主页零未捕获 JS 错误", not report["errors"], json.dumps(report["errors"])[:300])
            frame_errors = [item for item in report["console"]
                            if item["type"] == "error" and "favicon" not in item["text"]]
            check("插件页零控制台错误", not frame_errors, json.dumps(frame_errors[:3], ensure_ascii=False))
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
    report = run(sys.argv[1] if len(sys.argv) > 1 else "task6")
    sys.exit(0 if report["total"] and report["passed"] == report["total"] else 1)

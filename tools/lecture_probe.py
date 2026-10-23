# -*- coding: utf-8 -*-
"""专题讲义插件（org.jiuzhang.lecture）真机探针：军令 #13 任务 7。

用法：``.venv/Scripts/python.exe tools/lecture_probe.py <tag>``

隔离口径：``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` 指向
``.system_generated/lecture-probe/<tag>/``；复制仓库里的 core-bank 与 lecture，
不碰开发者 ``data/`` 与仓库 ``plugins/``。

判据：
  1. 插件被后端接受，点击后中栏开出沙箱舞台页；
  2. 题篮真题按考向铺出三块骨架：知识点 / 方法 / 易错点条目一一对应，题源计数如实；
  3. 正文改动即时原生渲染：标题成 h 标签、`$...$` 出 KaTeX；
  4. 「＋ 添加」真的加一条；
  5. 保存草稿 → 刷新页面重新打开，标题与正文原样回来（说明走的是宿主代持）；
  6. 已有内容时重建骨架要点两次，第一次只警告不覆盖；
  7. 打印前重排不报错；宿主页与插件页零未捕获 JS 错误。
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
PORT = 8796
BASE = f"http://127.0.0.1:{PORT}/workspace"
PLUGIN_ID = "org.jiuzhang.lecture"
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
    for kind in ("single_choice", "multiple_choice", "fill_blank", "solution"):
        status, listing = call("GET", f"/api/bank/plugins/{BANK_ID}/questions?type={kind}&page_size=3")
        if status != 200:
            continue
        for item in listing.get("items", [])[:3]:
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
    out = ROOT / ".system_generated" / "lecture-probe" / tag
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
        check("讲义插件被后端接受", status == 200 and PLUGIN_ID in ids,
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

            def open_plugin():
                page.goto(BASE, wait_until="networkidle")
                page.wait_for_selector(f'.ws-plugin-item[data-plugin-id="{PLUGIN_ID}"]', timeout=20000)
                page.click(f'.ws-plugin-item[data-plugin-id="{PLUGIN_ID}"]')
                page.wait_for_selector("#wsCanvasBody iframe.ws-plugin-frame", timeout=20000)
                handle = page.wait_for_selector("#wsCanvasBody iframe.ws-plugin-frame")
                frame = handle.content_frame()
                frame.wait_for_selector("#lcRoot:not([hidden])", timeout=20000)
                return frame, handle

            frame, handle = open_plugin()
            check("舞台 iframe 沙箱为 allow-scripts allow-modals",
                  handle.get_attribute("sandbox") == "allow-scripts allow-modals",
                  str(handle.get_attribute("sandbox")))
            frame.wait_for_selector('.lc-entry textarea', timeout=25000)
            page.wait_for_timeout(500)
            snap("10-skeleton")

            skeleton = frame.evaluate("""() => {
              const entries = key => Array.from(document.querySelectorAll('[data-entries="' + key + '"] .lc-entry textarea'));
              const texts = key => entries(key).map(t => t.value);
              return {
                knowledge: entries('knowledge').length,
                methods: entries('methods').length,
                pitfalls: entries('pitfalls').length,
                sources: document.querySelectorAll('.lc-source').length,
                sourceCount: document.querySelector('#lcSourceCount').textContent,
                meta: document.querySelector('#lcDocMeta').textContent,
                firstKnowledge: texts('knowledge')[0] || '',
                firstMethod: texts('methods')[0] || '',
                firstPitfall: texts('pitfalls')[0] || '',
                counts: Array.from(document.querySelectorAll('.lc-block-count')).map(n => n.textContent),
                totalText: document.querySelector('.lc-doc').innerText.slice(0, 300)
              };
            }""")
            report["notes"]["skeleton"] = skeleton
            check("按考向铺出三块骨架", skeleton["knowledge"] >= 2
                  and skeleton["knowledge"] == skeleton["methods"] == skeleton["pitfalls"],
                  json.dumps({"k": skeleton["knowledge"], "m": skeleton["methods"], "p": skeleton["pitfalls"]}))
            check("题源计数与题篮一致", str(skeleton["sources"]) == skeleton["sourceCount"] == str(len(seeded)),
                  f"{skeleton['sources']}/{skeleton['sourceCount']}/{len(seeded)}")
            check("骨架条目含考向标题与题源数",
                  skeleton["firstKnowledge"].startswith("## ") and "题源" in skeleton["firstKnowledge"],
                  skeleton["firstKnowledge"][:80])
            check("方法骨架是编号步骤", "1." in skeleton["firstMethod"] and "2." in skeleton["firstMethod"],
                  skeleton["firstMethod"][:80])
            check("易错点骨架成形", "易错点" in skeleton["firstPitfall"], skeleton["firstPitfall"][:80])
            check("文档元信息写明题源数", f"题源 {len(seeded)} 道" in skeleton["meta"], skeleton["meta"])

            probe_text = "## 探针公式\n- 勾股定理：$a^2+b^2=c^2$\n- 强调：**先看定义域**"
            first = frame.locator('[data-entries="knowledge"] textarea').first
            first.fill(probe_text)
            page.wait_for_timeout(500)
            snap("20-edited")
            rendered = frame.evaluate("""() => {
              const preview = document.querySelector('[data-entries="knowledge"] .lc-entry .lc-preview');
              return {
                heading: (preview.querySelector('h3, h2, h4') || {}).textContent || '',
                katex: preview.querySelectorAll('.katex').length,
                strong: preview.querySelectorAll('strong').length,
                items: preview.querySelectorAll('li').length,
                rawDollar: preview.innerText.includes('$a^2')
              };
            }""")
            report["notes"]["rendered"] = rendered
            check("Markdown 标题原生渲染", rendered["heading"] == "探针公式", rendered["heading"])
            check("行内公式出 KaTeX", rendered["katex"] >= 1, rendered["katex"])
            check("加粗与列表原生渲染", rendered["strong"] >= 1 and rendered["items"] >= 2,
                  json.dumps(rendered))
            check("预览不回显源码定界符", rendered["rawDollar"] is False, rendered["rawDollar"])

            before_add = frame.locator('[data-entries="pitfalls"] textarea').count()
            frame.click('[data-add="pitfalls"]')
            page.wait_for_timeout(300)
            after_add = frame.locator('[data-entries="pitfalls"] textarea').count()
            check("「＋ 添加」真的加一条", after_add == before_add + 1, f"{before_add} → {after_add}")

            frame.fill("#lcTitle", "高二 · 数列专题讲义")
            frame.click("#lcSave")
            page.wait_for_timeout(600)
            saved_status = frame.inner_text("#lcStatus")
            check("保存草稿走到宿主并回执", "已保存" in saved_status, saved_status)

            before_guard = frame.locator('[data-entries="knowledge"] textarea').first.input_value()
            frame.click("#lcSkeleton")
            page.wait_for_timeout(300)
            guard_status = frame.inner_text("#lcStatus")
            after_guard = frame.locator('[data-entries="knowledge"] textarea').first.input_value()
            check("重建骨架第一次只警告不覆盖",
                  "再点一次" in guard_status and before_guard == after_guard,
                  guard_status)

            frame, handle = open_plugin()
            frame.wait_for_selector('.lc-entry textarea', timeout=25000)
            page.wait_for_timeout(600)
            snap("30-restored")
            restored = frame.evaluate("""() => ({
              titleValue: document.querySelector('#lcTitle').value,
              docTitle: document.querySelector('#lcDocTitle').textContent,
              first: document.querySelector('[data-entries="knowledge"] textarea').value,
              pitfalls: document.querySelectorAll('[data-entries="pitfalls"] textarea').length,
              status: document.querySelector('#lcStatus').textContent
            })""")
            report["notes"]["restored"] = restored
            check("刷新后标题恢复", restored["titleValue"] == "高二 · 数列专题讲义"
                  and restored["docTitle"] == "高二 · 数列专题讲义",
                  json.dumps(restored, ensure_ascii=False)[:200])
            check("刷新后正文恢复", restored["first"] == probe_text, restored["first"][:80])
            check("刷新后新增条目仍在", restored["pitfalls"] == after_add, restored["pitfalls"])
            check("恢复后提示已载入草稿", "草稿" in restored["status"], restored["status"])

            frame.evaluate("() => window.dispatchEvent(new Event('beforeprint'))")
            page.wait_for_timeout(300)
            printed = frame.evaluate("""() => ({
              previews: document.querySelectorAll('.lc-preview').length,
              nonEmpty: Array.from(document.querySelectorAll('.lc-preview')).filter(n => n.textContent.trim()).length
            })""")
            check("打印态正文预览齐全", printed["previews"] >= 3 and printed["nonEmpty"] >= 1, printed)

            # ---- PDF 导出：打印态隔离 + 真实 A4 PDF ----
            page.emulate_media(media="print")
            page.wait_for_timeout(300)
            print_state = frame.evaluate("""() => {
              const top = document.querySelector('.lc-top');
              const src = document.querySelector('.lc-sources');
              const doc = document.querySelector('.lc-doc');
              const add = document.querySelectorAll('.lc-add').length;
              const areas = document.querySelectorAll('.lc-entry textarea').length;
              return {
                topHidden: top ? getComputedStyle(top).display === 'none' : false,
                sourcesHidden: src ? getComputedStyle(src).display === 'none' : false,
                docVisible: !!doc && doc.getBoundingClientRect().width > 0,
                addButtons: add, textareas: areas
              };
            }""")
            report["notes"]["print"] = print_state
            check("打印态隐藏工具栏与题源栏（PDF 不带网页按钮）",
                  print_state["topHidden"] and print_state["sourcesHidden"], print_state)
            check("打印态正文可见且编辑控件收起",
                  print_state["docVisible"] and print_state["addButtons"] > 0, print_state)
            snap("40-print")
            page.emulate_media(media="screen")

            console_before = len(report["console"])
            frame.evaluate("() => window.print()")
            page.wait_for_timeout(600)
            ignored = [entry for entry in report["console"][console_before:]
                       if "Ignored call to 'print()'" in entry["text"]]
            check("沙箱放行 window.print（allow-modals）", not ignored,
                  json.dumps(ignored[:2], ensure_ascii=False))

            lecture_html = frame.evaluate(
                "() => { const n = document.getElementById('lcRoot'); return n ? n.outerHTML : ''; }")
            lecture_css = page.evaluate(
                """async () => (await (await fetch('/plugin-assets/org.jiuzhang.lecture/dist/plugin.css',
                    {cache: 'no-store'})).text())""")
            pdf_page = browser.new_page()
            origin = f"http://127.0.0.1:{PORT}"
            pdf_page.set_content(
                "<!doctype html><html><head><meta charset='utf-8'>"
                + f"<base href='{origin}/'>"
                + f"<link rel='stylesheet' href='{origin}/static/vendor/katex/katex.min.css'>"
                + "<style>" + lecture_css + "</style></head><body>"
                + lecture_html + "</body></html>",
                wait_until="networkidle")
            pdf_path = out / "lecture-a4.pdf"
            pdf_page.pdf(path=str(pdf_path), format="A4", print_background=True)
            pdf_page.close()
            raw = pdf_path.read_bytes()
            import re as _re
            page_count = len(_re.findall(rb"/Type\s*/Page[^s]", raw))
            report["notes"]["pdf"] = {"path": str(pdf_path), "bytes": len(raw), "pages": page_count}
            check("A4 PDF 生成且非空",
                  raw.startswith(b"%PDF") and len(raw) > 20000, len(raw))
            check("讲义 PDF 至少一页", page_count >= 1, page_count)

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
    report = run(sys.argv[1] if len(sys.argv) > 1 else "task7")
    sys.exit(0 if report["total"] and report["passed"] == report["total"] else 1)

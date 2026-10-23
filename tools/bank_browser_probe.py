# -*- coding: utf-8 -*-
"""题库浏览插件（org.jiuzhang.bank-browser）真机探针：军令 #13 任务 8。

用法：``.venv/Scripts/python.exe tools/bank_browser_probe.py <tag>``

隔离口径：``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` 指向
``.system_generated/bank-browser-probe/<tag>/``；复制仓库里的 core-bank、
bank-browser 与 editor，不碰开发者 ``data/`` 与仓库 ``plugins/``。

判据：
  1. 插件被后端接受，点击后中栏开出 sandbox=allow-scripts allow-modals 的舞台页；
  2. 首屏 12 张卡片、总数 456、抬头全库计数来自活跃 provider；
  3. 左树懒展开：点箭头才向宿主取下一层，点节点按子树筛题且计数对得上；
  4. 全局搜索清掉目录范围，总数与后端 `q=函数` 完全一致；
  5. 【加入题篮】记在活跃 provider 名下（API 复核 plugin_id），按钮变「已在题篮」；
  6. 【去编辑】经宿主打开录题页签并注入同一个题号；
  7. 分页可翻页且卡片换批；宿主页与插件页零未捕获 JS 错误。
"""
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PORT = 8797
BASE = f"http://127.0.0.1:{PORT}/workspace"
PLUGIN_ID = "org.jiuzhang.bank-browser"
BANK_ID = "org.jiuzhang.core-bank"
EDITOR_ID = "org.jiuzhang.editor"


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


def run(tag: str) -> dict:
    out = ROOT / ".system_generated" / "bank-browser-probe" / tag
    if out.exists():
        shutil.rmtree(out, ignore_errors=True)
    data_dir = out / "data"
    plugins_dir = out / "plugins"
    data_dir.mkdir(parents=True, exist_ok=True)
    plugins_dir.mkdir(parents=True, exist_ok=True)
    for plugin_id in (BANK_ID, PLUGIN_ID, EDITOR_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)

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
        check("浏览插件被后端接受", status == 200 and PLUGIN_ID in ids,
              json.dumps(listing.get("rejected"), ensure_ascii=False)[:300])

        _, stats = call("GET", f"/api/bank/plugins/{BANK_ID}/stats")
        bank_total = int(stats.get("total") or 0)
        _, search_api = call("GET", f"/api/bank/plugins/{BANK_ID}/questions?q={quote('函数')}&page_size=1")
        search_total = int(search_api.get("total") or 0)
        _, roots_api = call("GET", f"/api/bank/plugins/{BANK_ID}/topics")
        roots = roots_api.get("items") or []
        first_root = roots[0] if roots else {}
        _, chapters_api = call(
            "GET", f"/api/bank/plugins/{BANK_ID}/topics?parent_id={first_root.get('id', '')}")
        first_chapter = (chapters_api.get("items") or [{}])[0]
        report["notes"]["api"] = {
            "bank_total": bank_total, "search_total": search_total,
            "root": first_root.get("name"), "chapter": first_chapter.get("name"),
            "chapter_count": first_chapter.get("question_count"),
        }
        check("夹具题库有真题与目录", bank_total >= 100 and search_total >= 1
              and bool(first_root.get("id")) and bool(first_chapter.get("id")),
              json.dumps(report["notes"]["api"], ensure_ascii=False))

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
            handle = page.wait_for_selector(
                'iframe.ws-plugin-frame[src*="org.jiuzhang.bank-browser"]', timeout=20000)
            frame = handle.content_frame()
            frame.wait_for_selector("#bbRoot:not([hidden])", timeout=20000)
            frame.wait_for_function("() => document.querySelectorAll('.bb-card').length > 0", timeout=25000)
            page.wait_for_timeout(500)
            snap("10-overview")

            check("舞台 iframe 沙箱为 allow-scripts allow-modals",
                  handle.get_attribute("sandbox") == "allow-scripts allow-modals",
                  str(handle.get_attribute("sandbox")))

            overview = frame.evaluate("""() => ({
              cards: document.querySelectorAll('.bb-card').length,
              total: document.querySelector('#bbTotal').textContent,
              scope: document.querySelector('#bbScope').textContent,
              roots: document.querySelectorAll('#bbTree > .bb-node').length,
              treeTop: document.querySelector('#bbTree > .bb-node .bb-node-name')?.textContent || '',
              firstId: document.querySelector('.bb-card')?.getAttribute('data-question-id') || '',
              katex: document.querySelectorAll('.bb-card .katex').length,
              addButtons: document.querySelectorAll('.bb-add').length,
              editButtons: document.querySelectorAll('.bb-edit').length
            })""")
            report["notes"]["overview"] = overview
            check("首屏 12 张题卡", overview["cards"] == 12, overview["cards"])
            check("总数来自活跃题库", overview["total"] == f"共 {bank_total} 题", overview["total"])
            check("抬头全库计数同源", f"全库 {bank_total} 题" in overview["scope"], overview["scope"])
            check("左树根层是教材版本", overview["roots"] == len(roots)
                  and overview["treeTop"] == first_root.get("name"),
                  f"{overview['roots']}/{len(roots)} · {overview['treeTop']}")
            check("每张卡都带入篮与编辑按钮",
                  overview["addButtons"] == 12 and overview["editButtons"] == 12,
                  f"{overview['addButtons']}/{overview['editButtons']}")
            check("题干公式出 KaTeX", overview["katex"] >= 1, overview["katex"])

            first_id = overview["firstId"]

            # ---- 左树懒展开 + 按子树筛题 ----
            before_children = frame.evaluate("() => document.querySelectorAll('#bbTree .bb-children .bb-node').length")
            frame.click("#bbTree .bb-node .bb-twisty")
            frame.wait_for_function(
                "() => document.querySelectorAll('#bbTree > .bb-node:first-child .bb-children .bb-node').length > 0",
                timeout=15000)
            page.wait_for_timeout(300)
            snap("20-tree-expanded")
            expanded = frame.evaluate("""() => {
              const root = document.querySelector('#bbTree > .bb-node');
              return {
                before: %d,
                children: root.querySelectorAll(':scope > .bb-children > .bb-node').length,
                aria: root.getAttribute('aria-expanded'),
                firstName: root.querySelector(':scope > .bb-children .bb-node-name').textContent,
                firstCount: root.querySelector(':scope > .bb-children .bb-node-count').textContent
              };
            }""" % before_children)
            report["notes"]["expanded"] = expanded
            check("点箭头才懒加载下一层",
                  before_children == 0 and expanded["children"] > 0 and expanded["aria"] == "true",
                  json.dumps(expanded, ensure_ascii=False)[:200])

            frame.click("#bbTree > .bb-node:first-child .bb-children .bb-node:first-child .bb-node-name")
            frame.wait_for_function(
                "() => document.querySelector('#bbTotal').textContent !== '共 %d 题'" % bank_total,
                timeout=15000)
            page.wait_for_timeout(400)
            snap("30-topic-filter")
            filtered = frame.evaluate("""() => ({
              crumb: document.querySelector('#bbCrumb').textContent,
              total: document.querySelector('#bbTotal').textContent,
              selected: document.querySelectorAll('#bbTree .bb-node-name[aria-current="true"]').length,
              cards: document.querySelectorAll('.bb-card').length
            })""")
            report["notes"]["filtered"] = filtered
            expected_chapter_count = int(first_chapter.get("question_count") or 0)
            check("目录筛选落到标签与选中态",
                  expanded["firstName"] in filtered["crumb"] and filtered["selected"] == 1,
                  json.dumps(filtered, ensure_ascii=False)[:200])
            check("目录筛选总数与子树计数一致",
                  filtered["total"] == f"共 {expected_chapter_count} 题",
                  f"{filtered['total']} vs {expected_chapter_count}")

            # ---- 全局搜索清掉目录范围 ----
            frame.fill("#bbSearch", "函数")
            frame.click("#bbSearchBtn")
            frame.wait_for_function(
                "() => document.querySelector('#bbTotal').textContent === '共 %d 题'" % search_total,
                timeout=15000)
            page.wait_for_timeout(400)
            snap("40-search")
            searched = frame.evaluate("""() => ({
              crumb: document.querySelector('#bbCrumb').textContent,
              total: document.querySelector('#bbTotal').textContent,
              selected: document.querySelectorAll('#bbTree .bb-node-name[aria-current="true"]').length,
              input: document.querySelector('#bbSearch').value,
              clearVisible: !document.querySelector('#bbClear').hidden
            })""")
            report["notes"]["searched"] = searched
            check("全局搜索总数与后端一致", searched["total"] == f"共 {search_total} 题", searched["total"])
            check("搜索时清掉目录范围", searched["crumb"] == "搜索「函数」"
                  and searched["selected"] == 0 and searched["clearVisible"],
                  json.dumps(searched, ensure_ascii=False)[:200])

            frame.click("#bbClear")
            frame.wait_for_function(
                "() => document.querySelector('#bbTotal').textContent === '共 %d 题'" % bank_total,
                timeout=15000)
            page.wait_for_timeout(300)
            check("清空搜索回到全部题目",
                  frame.inner_text("#bbCrumb") == "全部题目", frame.inner_text("#bbCrumb"))

            # ---- 加入题篮：记在活跃 provider 名下 ----
            frame.click(".bb-card .bb-add")
            frame.wait_for_function(
                "() => document.querySelector('.bb-card .bb-add').textContent === '已在题篮'",
                timeout=15000)
            page.wait_for_timeout(500)
            snap("50-basket")
            status, basket = call("GET", "/api/basket")
            basket_items = basket.get("items") or []
            report["notes"]["basket"] = basket
            check("入篮按钮变为已在题篮",
                  frame.inner_text(".bb-card .bb-add") == "已在题篮",
                  frame.inner_text(".bb-card .bb-add"))
            check("题篮条目记在活跃 provider 名下",
                  status == 200 and len(basket_items) == 1
                  and basket_items[0].get("plugin_id") == BANK_ID
                  and basket_items[0].get("question_id") == first_id,
                  json.dumps(basket_items, ensure_ascii=False)[:300])

            # ---- 去编辑：经宿主打开录题页签并注入题号 ----
            frame.click(".bb-card .bb-edit")
            editor_handle = page.wait_for_selector(
                'iframe.ws-plugin-frame[src*="org.jiuzhang.editor"]', timeout=25000)
            editor_frame = editor_handle.content_frame()
            editor_frame.wait_for_function(
                "() => (document.querySelector('#edEditingId')?.textContent || '') !== ''", timeout=25000)
            page.wait_for_timeout(600)
            snap("60-editor")
            editing = editor_frame.inner_text("#edEditingId")
            report["notes"]["editing"] = editing
            check("去编辑把同一个题号注入录题页签", editing == first_id, f"{editing} vs {first_id}")

            # ---- 分页 ----
            page.click(f'.ws-plugin-item[data-plugin-id="{PLUGIN_ID}"]')
            browser_handle = page.wait_for_selector(
                'iframe.ws-plugin-frame[src*="org.jiuzhang.bank-browser"]', timeout=20000)
            frame = browser_handle.content_frame()
            frame.wait_for_selector("#bbRoot:not([hidden])", timeout=20000)
            frame.wait_for_selector(".bb-card", timeout=20000)
            before_page = frame.inner_text("#bbPageInfo")
            first_before = frame.evaluate("() => document.querySelector('.bb-card').getAttribute('data-question-id')")
            frame.click("#bbNext")
            frame.wait_for_function(
                "() => document.querySelector('#bbPageInfo').textContent.indexOf('第 2 /') === 0",
                timeout=15000)
            frame.wait_for_function(
                "() => document.querySelector('.bb-card') && document.querySelector('.bb-card').getAttribute('data-question-id') !== '%s'" % first_before,
                timeout=15000)
            page.wait_for_timeout(300)
            snap("70-page2")
            paged = frame.evaluate("""() => ({
              info: document.querySelector('#bbPageInfo').textContent,
              first: document.querySelector('.bb-card').getAttribute('data-question-id'),
              total: document.querySelector('#bbTotal').textContent
            })""")
            report["notes"]["paged"] = paged
            check("翻页换批且页码前进",
                  before_page.startswith("第 1 /") and paged["info"].startswith("第 2 /")
                  and paged["first"] != first_before and paged["total"] == f"共 {bank_total} 题",
                  json.dumps(paged, ensure_ascii=False)[:200])

            check("宿主页零未捕获 JS 错误", not report["errors"], json.dumps(report["errors"])[:300])
            frame_errors = [item for item in report["console"]
                            if item["type"] == "error" and "favicon" not in item["text"]]
            check("插件页零控制台错误", not frame_errors,
                  json.dumps(frame_errors[:3], ensure_ascii=False))
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
    report = run(sys.argv[1] if len(sys.argv) > 1 else "task8")
    sys.exit(0 if report["total"] and report["passed"] == report["total"] else 1)

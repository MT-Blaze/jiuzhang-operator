# -*- coding: utf-8 -*-
"""数据字典控制台阶段三真机探针（四栏联动 + sort_order 持久化）。

取证口径（全部走真人路径，夹具运行时从 API 解析，不写死 id）：
- 未选教材时左栏如实提示，选教材后自动加载真实章节树（种子 3519 章节）；
- 点章节 → 中栏知识点（桥表 sort_order 顺序）；双击改名 blur 保存；
  键盘 Alt+方向键排序 → sort_order 落库；
- 中栏选点 → 右栏考向；新增 / 双击改名 / 删除；
- 选中考向 → 最右栏辅助标签：全局搜索添加、拖拽排序；
- 给考向挂第二个标签后再删该考向 → 409「已被引用，禁止删除」（防呆）；
- 刷新后知识点顺序、标签顺序仍在（sort_order 真持久化），再移除标签可删考向；
- /status 报 v7（迁移生效）；375px 不横溢、热区 ≥44px；零页面异常
  （预期 409 的诊断日志单独归类）。

环境坑⑦口径：端口 free_port() 动态、令牌 secrets 随机经 /api/settings 运行时读取、
数据目录隔离临时目录，绝不碰真实 data/，也不动端口 8000 的用户旧进程。

用法：``.venv/Scripts/python.exe tools/dict_console_probe_stage3.py <tag>``
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402

import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
TREE = ".dcl-col[aria-label='教材章节树']"
POINTS = ".dcl-col[aria-label='章节知识点清单']"
DIRS = ".dcl-col[aria-label='考向清单']"
TAGS = ".dcl-col[aria-label='辅助知识点标签']"

# 夹具解析：学科「数学」→ 含「必修一」的教材 → 首个带 ≥2 个知识点的章节 → 首个带考向的点。
DISCOVER = """async () => {
  const get = async (url) => (await fetch(url, {cache: 'no-store'})).json();
  const meta = await get('/api/bank/engine/meta');
  const subject = (meta.subjects || []).find((s) => s.name === '数学') || meta.subjects[0];
  const books = await get('/api/bank/engine/textbooks?subject_id=' + subject.id);
  const book = (books.items || []).find((b) => String(b.name).indexOf('必修一') >= 0)
    || (books.items || [])[0];
  const tree = await get('/api/bank/engine/linkage/chapter-tree?textbook_id=' + book.id);
  const leaves = [];
  (function walk(nodes) {
    (nodes || []).forEach((n) => {
      if ((n.children || []).length) walk(n.children); else leaves.push(n.chapter);
    });
  })(tree.items || []);
  let chapter = null, points = [];
  for (let i = 0; i < Math.min(leaves.length, 40) && !chapter; i += 1) {
    const data = await get('/api/bank/engine/linkage/chapters/' + leaves[i].id + '/points');
    if ((data.items || []).length >= 2) { chapter = leaves[i]; points = data.items; }
  }
  let pick = points[0] || null;
  for (let i = 0; i < points.length; i += 1) {
    const dirs = await get('/api/bank/engine/linkage/points/' + points[i].id + '/directions');
    if ((dirs.items || []).length) { pick = points[i]; break; }
  }
  return { subject: subject, book: book, chapter: chapter, points: points, pick: pick,
           leafCount: leaves.length };
}"""


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


def api(page, path: str):
    return page.evaluate("async (p) => (await fetch(p, {cache: 'no-store'})).json()", path)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "dict_console_probe_stage3" / tag
    if work.exists():
        shutil.rmtree(work)
    (work / "shots").mkdir(parents=True)
    data_dir = Path(tempfile.mkdtemp(prefix="jzo-dict-s3-"))
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_LOCAL_TOKEN"] = secrets.token_hex(16)
    env["JZO_DATA_DIR"] = str(data_dir)
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    result: dict = {"tag": tag, "checks": [], "console_errors": [], "page_errors": [],
                    "http_diagnostics": [], "viewport": {"width": 1440, "height": 900}, "geometry": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    def on_console(message) -> None:
        if message.type not in {"error", "warning"}:
            return
        text = message.text
        expected_http = text.startswith("[JZO 请求失败]") or (
            text.startswith("Failed to load resource") and ("409" in text or "400" in text)
        )
        if expected_http:
            result["http_diagnostics"].append(text)
        else:
            result["console_errors"].append(text)

    try:
        wait_health(base, process)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", on_console)
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.goto(base + "/dict", wait_until="domcontentloaded")
            expect(page.locator("#dcGlobalsState")).to_contain_text("当前：", timeout=60000)

            status = api(page, "/api/bank/engine/status")
            check("引擎库已迁移到 v7（sort_order 列生效）",
                  status.get("schema_version") == 7 and status.get("integrity") == "ok",
                  {"schema_version": status.get("schema_version")})

            # ---- 未选教材时左栏如实提示 ----
            page.locator(".dc-nav-item", has_text="教研属性字典").click()
            tree_state = page.locator(TREE + " .dcl-state")
            expect(tree_state).to_contain_text("请先在右侧全局设置选择教材版本", timeout=10000)
            check("未选教材时章节树如实提示（不造假数据）",
                  "选择教材版本" in tree_state.inner_text())

            # ---- 选数学 + 教材：树自动加载（dc:globals-changed） ----
            fixture = page.evaluate(DISCOVER)
            chapter = fixture["chapter"]
            check("运行时夹具解析成功（章节 + ≥2 知识点）",
                  bool(chapter) and len(fixture["points"]) >= 2,
                  {"book": fixture["book"].get("name"), "chapter": chapter,
                   "points": len(fixture["points"])})
            check("教材过滤后仍为真实种子（必修一且属数学）",
                  "必修一" in fixture["book"]["name"] and fixture["leafCount"] >= 10,
                  {"book": fixture["book"], "leaves": fixture["leafCount"]})
            page.locator("#dcSubject").select_option(label="数学")
            page.locator("#dcTextbook").select_option(value=str(fixture["book"]["id"]))
            expect(tree_state).to_contain_text("共", timeout=30000)
            node = page.locator(TREE + " .dcl-tree-node[data-id='" + str(chapter["id"]) + "']")
            expect(node).to_be_visible(timeout=10000)
            tree_total = tree_state.inner_text()
            check("选教材后整树渲染真实章节层级",
                  "共" in tree_total and int("".join(c for c in tree_total if c.isdigit())) >= 10,
                  tree_total)

            # ---- 章节 → 知识点列（桥表顺序） ----
            node.click()
            points_col = page.locator(POINTS)
            expect(points_col.locator(".dcl-state")).to_contain_text("共", timeout=10000)
            api_points = api(page, "/api/bank/engine/linkage/chapters/" + str(chapter["id"]) + "/points")
            points = fixture["points"]
            p0, p1 = points[0], points[1]
            expect(points_col.locator(".dcl-item")).to_have_count(len(points), timeout=10000)
            check("章节知识点按桥表顺序渲染真实知识点",
                  [i["id"] for i in api_points["items"]] == [i["id"] for i in points]
                  and points[0]["name"] in points_col.locator(".dcl-list").inner_text(),
                  {"count": len(points), "first": points[0]["name"]})
            page.screenshot(path=str(work / "shots" / "01_tree_points.png"))

            # ---- 双击改名 blur 保存（PUT 落库） ----
            new_name = p0["name"] + "·探针"
            item0 = points_col.locator("li.dcl-item[data-id='" + str(p0["id"]) + "'] .dcl-item-main")
            item0.dblclick()
            editor = points_col.locator("input.dc-cell-input")
            expect(editor).to_be_visible(timeout=5000)
            editor.fill(new_name)
            editor.press("Tab")
            expect(item0).to_contain_text("·探针", timeout=10000)
            readback = api(page, "/api/bank/engine/linkage/chapters/" + str(chapter["id"]) + "/points")
            row0 = [r for r in readback["items"] if r["id"] == p0["id"]][0]
            check("知识点双击改名 blur 保存且服务端回读一致", row0["name"] == new_name,
                  {"saved": row0["name"]})

            # ---- 键盘排序：Alt+方向键 → sort_order 落库 ----
            item0.click()  # 真实点击把焦点放到条目上，随后键盘排序
            page.keyboard.press("Alt+ArrowDown")
            expect(points_col.locator(".dcl-state")).to_contain_text("排序已保存", timeout=10000)
            ordered = api(page, "/api/bank/engine/linkage/chapters/" + str(chapter["id"]) + "/points")
            ids_after = [r["id"] for r in ordered["items"]]
            check("知识点 Alt+方向键排序持久化（p1 提到 p0 前）",
                  ids_after[:2] == [p1["id"], p0["id"]], {"order": ids_after[:4]})
            points_order_expected = ids_after
            page.screenshot(path=str(work / "shots" / "02_point_sorted.png"))

            # ---- 选中知识点 → 右栏考向：新增 + 改名 ----
            pick_id = fixture["pick"]["id"] if fixture["pick"] else p0["id"]
            pick_name = next((i["name"] for i in points if i["id"] == pick_id), p0["name"])
            page.locator(POINTS + " li.dcl-item[data-id='" + str(pick_id) + "'] .dcl-item-main").click()
            dirs_col = page.locator(DIRS)
            expect(dirs_col.locator(".dcl-add")).to_be_enabled(timeout=10000)
            dirs_col.locator(".dcl-add").click()
            new_input = dirs_col.locator("input.dcl-new-input")
            expect(new_input).to_be_visible(timeout=5000)
            new_input.fill("探针考向甲")
            new_input.press("Enter")
            expect(dirs_col.locator(".dcl-state")).to_contain_text("已新增考向", timeout=10000)
            new_li = dirs_col.locator("li.dcl-item", has_text="探针考向甲")
            expect(new_li).to_be_visible(timeout=10000)
            new_li.locator(".dcl-item-main").dblclick()
            dir_editor = dirs_col.locator("input.dc-cell-input")
            expect(dir_editor).to_be_visible(timeout=5000)
            dir_editor.fill("探针考向乙")
            dir_editor.press("Tab")
            renamed_li = dirs_col.locator("li.dcl-item", has_text="探针考向乙")
            expect(renamed_li.locator(".dcl-item-main")).to_contain_text("探针考向乙", timeout=10000)
            dir_list = api(page, "/api/bank/engine/linkage/points/" + str(pick_id) + "/directions")
            d2 = next((d for d in dir_list["items"] if d["name"] == "探针考向乙"), None)
            check("新增考向并双击改名落库（学科继承知识点）", bool(d2), {"d2": d2})
            check("已改名考向出现在真实清单中", bool(d2) and "探针考向乙" in dirs_col.inner_text())
            page.screenshot(path=str(work / "shots" / "03_direction_added.png"))

            # ---- 最右栏标签：全局搜索添加第二条标签 ----
            renamed_li.locator(".dcl-item-main").click()
            tags_col = page.locator(TAGS)
            expect(tags_col.locator(".dcl-state")).to_contain_text("共", timeout=10000)
            search = tags_col.locator(".dcl-tag-search")
            expect(search).to_be_enabled(timeout=10000)
            search.fill("函数")
            expect(tags_col.locator(".dcl-search-results")).to_be_visible(timeout=10000)
            pick_name_now = next(
                (i["name"] for i in points if i["id"] == pick_id), pick_name)
            index = page.evaluate(
                """(p0) => Array.from(document.querySelectorAll('.dcl-search-item'))
                    .findIndex((li) => {
                        const btn = li.querySelector('.dcl-search-add');
                        const name = (li.querySelector('.dcl-search-name') || {}).textContent || '';
                        return btn && !btn.disabled && name.trim() !== p0;
                    })""", pick_name_now)
            check("全局搜索返回可添加知识点", index >= 0)
            tags_col.locator(".dcl-search-item").nth(index).locator(".dcl-search-add").click()
            expect(tags_col.locator(".dcl-state")).to_contain_text("已添加辅助标签", timeout=10000)
            tags_api = api(page, "/api/bank/engine/linkage/directions/" + str(d2["id"]) + "/tags")
            tag_ids = [i["id"] for i in tags_api["items"]]
            x_id = next((i["id"] for i in tags_api["items"] if i["id"] != pick_id), None)
            check("辅助标签添加后共 2 条（当前点 + 搜索添加）",
                  len(tag_ids) == 2 and x_id is not None, {"tags": tag_ids})
            tag_hit = tags_col.locator(".dcl-tag-del").first.evaluate(
                "el => { const r = el.getBoundingClientRect();"
                " return [Math.round(r.width), Math.round(r.height)]; }")
            check("辅助标签删除按钮热区 ≥44px", min(tag_hit) >= 44, tag_hit)

            # ---- 标签拖拽排序（显式鼠标轨迹驱动原生 HTML5 拖拽，落点目标下沿） ----
            tag_items = tags_col.locator(".dcl-tag-list li.dcl-item")
            src_box = tag_items.nth(0).bounding_box()
            dst_box = tag_items.nth(1).bounding_box()
            page.mouse.move(src_box["x"] + src_box["width"] / 2, src_box["y"] + src_box["height"] / 2)
            page.mouse.down()
            page.mouse.move(src_box["x"] + src_box["width"] / 2 + 6,
                            src_box["y"] + src_box["height"] / 2 + 6, steps=5)
            page.mouse.move(dst_box["x"] + dst_box["width"] / 2,
                            dst_box["y"] + dst_box["height"] * 0.8, steps=12)
            page.mouse.up()
            expect(tags_col.locator(".dcl-state")).to_contain_text("排序已保存", timeout=10000)
            tags_api = api(page, "/api/bank/engine/linkage/directions/" + str(d2["id"]) + "/tags")
            tag_order_expected = [i["id"] for i in tags_api["items"]]
            check("标签拖拽排序持久化（sort_order 落库）",
                  tag_order_expected == [tag_ids[1], tag_ids[0]],
                  {"before": tag_ids, "after": tag_order_expected})
            page.screenshot(path=str(work / "shots" / "04_tags_sorted.png"))

            # ---- 被引用考向删除被 409 拦截（标签仍挂在它上面） ----
            renamed_li.locator(".dcl-item-del").click()
            expect(page.locator(".dc-dialog-title")).to_have_text("删除确认", timeout=5000)
            page.locator(".dc-dialog .dc-btn-primary").click()
            expect(page.locator(".dc-dialog-title")).to_have_text("已被引用，禁止删除", timeout=10000)
            block_message = page.locator(".dc-dialog-message").inner_text()
            check("被引用考向删除弹 409 防呆并列出引用来源",
                  "已被引用，禁止删除" in block_message and "引用来源" in block_message,
                  block_message)
            check("409 走真实 HTTP（诊断日志含 409）",
                  any("409" in t for t in result["http_diagnostics"]),
                  result["http_diagnostics"][:2])
            page.screenshot(path=str(work / "shots" / "05_referenced_409.png"))
            page.keyboard.press("Escape")
            check("Esc 关闭防呆对话框",
                  not bool(page.evaluate("() => window.DcDialog.isOpen()")))

            # ---- 刷新：知识点顺序与标签顺序都还在 ----
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#dcGlobalsState")).to_contain_text("当前：", timeout=60000)
            page.locator(".dc-nav-item", has_text="教研属性字典").click()
            expect(page.locator(TREE + " .dcl-tree-node[data-id='" + str(chapter["id"]) + "']")
                   ).to_be_visible(timeout=30000)
            page.locator(TREE + " .dcl-tree-node[data-id='" + str(chapter["id"]) + "']").click()
            expect(page.locator(POINTS + " .dcl-state")).to_contain_text("共", timeout=10000)
            dom_ids = page.evaluate(
                """() => Array.from(document.querySelectorAll(
                    '.dcl-col[aria-label="章节知识点清单"] li.dcl-item'))
                    .map((li) => Number(li.getAttribute('data-id')))""")
            check("刷新后知识点顺序仍是拖拽后的顺序",
                  dom_ids[:len(points_order_expected)] == points_order_expected,
                  {"dom": dom_ids[:4], "expected": points_order_expected[:4]})
            page.locator(POINTS + " li.dcl-item[data-id='" + str(pick_id) + "'] .dcl-item-main").click()
            expect(page.locator(DIRS + " .dcl-list")).to_contain_text("探针考向乙", timeout=10000)
            page.locator(DIRS + " li.dcl-item", has_text="探针考向乙").locator(".dcl-item-main").click()
            expect(page.locator(TAGS + " .dcl-state")).to_contain_text("共", timeout=10000)
            dom_tags = page.evaluate(
                """() => Array.from(document.querySelectorAll(
                    '.dcl-col[aria-label="辅助知识点标签"] .dcl-tag-list li.dcl-item'))
                    .map((li) => Number(li.getAttribute('data-id')))""")
            check("刷新后辅助标签顺序仍在（sort_order 真持久化）",
                  dom_tags == tag_order_expected, {"dom": dom_tags, "expected": tag_order_expected})
            page.screenshot(path=str(work / "shots" / "06_after_reload.png"))

            # ---- 收尾：移除搜索添加的标签后可删考向（无引用删除成功） ----
            tag_to_remove = page.locator(
                TAGS + " .dcl-tag-list li.dcl-item[data-id='" + str(x_id) + "'] .dcl-tag-del")
            tag_to_remove.click()
            expect(page.locator(TAGS + " .dcl-state")).to_contain_text("已移除", timeout=10000)
            page.locator(DIRS + " li.dcl-item", has_text="探针考向乙").locator(".dcl-item-del").click()
            expect(page.locator(".dc-dialog-title")).to_have_text("删除确认", timeout=5000)
            page.locator(".dc-dialog .dc-btn-primary").click()
            expect(page.locator(DIRS + " .dcl-list")).not_to_contain_text("探针考向乙", timeout=10000)
            final_dirs = api(page, "/api/bank/engine/linkage/points/" + str(pick_id) + "/directions")
            check("解除引用后考向删除成功（服务端回读不含）",
                  all(d["name"] != "探针考向乙" for d in final_dirs["items"]),
                  {"remaining": len(final_dirs["items"])})

            # ---- 375px：不横溢 + 热区 ----
            page.set_viewport_size({"width": 375, "height": 780})
            page.wait_for_timeout(400)
            narrow = page.evaluate(
                """() => {
                    const hit = (sel) => Array.from(document.querySelectorAll(sel))
                        .filter((el) => el.getBoundingClientRect().width > 0)
                        .map((el) => { const r = el.getBoundingClientRect();
                            return { w: Math.round(r.width), h: Math.round(r.height) }; });
                    const groups = { node: hit('.dcl-tree-node'), main: hit('.dcl-item-main'),
                                     del: hit('.dcl-item-del'), tagDel: hit('.dcl-tag-del'),
                                     search: hit('.dcl-tag-search'), btn: hit('.dc-btn') };
                    const mins = {};
                    Object.keys(groups).forEach((k) => {
                        mins[k] = groups[k].length ? Math.min.apply(null,
                            groups[k].map((r) => Math.min(r.w, r.h))) : null;
                    });
                    return { overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                             stacked: (() => { const cols = document.querySelectorAll('.dcl-col');
                                 return cols.length === 4
                                     && cols[0].getBoundingClientRect().bottom
                                        <= cols[1].getBoundingClientRect().top + 1; })(),
                             mins: mins };
                }""")
            result["geometry"]["narrow"] = narrow
            check("375px 不横向溢出且四栏纵向堆叠", narrow["overflow"] <= 0 and narrow["stacked"], narrow)
            present = {k: v for k, v in narrow["mins"].items() if v is not None}
            check("375px 联动区交互热区 ≥44px（树节点/条目/删除/搜索/按钮）",
                  len(present) >= 4 and all(v >= 44 for v in present.values()), narrow["mins"])
            page.screenshot(path=str(work / "shots" / "07_375px.png"))
            browser.close()
    except Exception as exc:  # 探针中途失败也把已完成的检查落盘，便于定位
        result["fatal"] = repr(exc)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        shutil.rmtree(data_dir, ignore_errors=True)

    result["ok"] = (all(item["ok"] for item in result["checks"])
                    and not result["page_errors"] and not result["console_errors"]
                    and "fatal" not in result)
    (work / "probe.toml").write_text(toml_io.dumps(result), encoding="utf-8")
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
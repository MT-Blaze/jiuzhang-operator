# -*- coding: utf-8 -*-
"""四栏联动两处业务错误修复的取证探针（跑真库，只读）。

覆盖主公亲自验收的两处：
1. 主知识点「交、并、补集的混合运算」选中后，最右栏辅助标签必须为空
   （不能再出现自己）；有辅助行的考向（1113）只显示真正的辅助点。
2. 全局【教材版本】只列纯净版本名（人教A版/人教版…），选版本后左栏
   顶级节点是册次（必修一…选修三），再往下才是章、节。

环境口径同其它探针：free_port() 动态端口、JZO_LOCAL_TOKEN 随机；
但数据目录**指向真实 data/**（只读 GET，不写库），不动端口 8000 旧进程。
证据落 .system_generated/acceptance_linkage_fix/<tag>/。
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

KP_MIXED = 960011  # 交、并、补集的混合运算
DIR_MIXED = 1026   # 集合的交并补混合运算（该点主考向，无辅助行）
KP_POW = 960037    # 有理数指数幂及根式（考向 1113 的主知识点）
KP_POW_AUX = 960038  # 无理数指数幂及其运算性质（考向 1113 的辅助点）
DIR_POW = 1113
CHAPTER_SET = 930047   # 1.3 集合的基本运算
CHAPTER_POW = 930003   # 4.1 指数运算（指数与指数幂的运算）


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 60
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("服务提前退出：" + (process.stdout.read() if process.stdout else "")[:2000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 60 秒内就绪")


def api(page, path: str):
    return page.evaluate("async (p) => (await fetch(p, {cache: 'no-store'})).json()", path)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "acceptance_linkage_fix" / tag
    if work.exists():
        shutil.rmtree(work)
    (work / "shots").mkdir(parents=True)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_LOCAL_TOKEN"] = secrets.token_hex(16)
    env["JZO_DATA_DIR"] = str(ROOT / "data")  # 真库只读取证
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    result: dict = {"tag": tag, "checks": [], "console_errors": [], "page_errors": [],
                    "viewport": {"width": 1440, "height": 900}, "geometry": {}}

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
            page.goto(base + "/dict", wait_until="domcontentloaded")
            expect(page.locator("#dcGlobalsState")).to_contain_text("当前：", timeout=60000)

            status = api(page, "/api/bank/engine/status")
            check("真库已迁移到 v9", status.get("schema_version") == 9 and status.get("integrity") == "ok",
                  {"schema_version": status.get("schema_version")})

            page.locator(".dc-nav-item", has_text="教研属性字典").click()
            expect(page.locator(TREE + " .dcl-state")).to_contain_text("选择教材版本", timeout=10000)

            # ---- 错误二：全局设置只列纯净版本名 ----
            page.locator("#dcSubject").select_option(label="数学")
            version_labels = page.evaluate(
                """() => Array.from(document.querySelectorAll('#dcTextbook option')).map(o => o.textContent)""")
            check("【教材版本】只列纯净版本名（无册次/无·）",
                  version_labels == ["全部版本", "人教A版", "人教版"]
                  and not any(("必修" in v or "选修" in v or "·" in v) for v in version_labels),
                  {"options": version_labels})
            page.evaluate("""() => { const s = document.getElementById('dcTextbook');
                              s.setAttribute('size', String(s.options.length)); }""")
            page.wait_for_timeout(200)
            page.locator("#dcGlobalsState").scroll_into_view_if_needed()
            clip = page.evaluate("""() => { const r = document.querySelector('.dc-block[aria-labelledby="dcGlobalsTitle"]')
                    .getBoundingClientRect();
                    return {x: r.x + window.scrollX, y: r.y + window.scrollY,
                            width: r.width, height: Math.min(r.height, 560)}; }""")
            page.screenshot(path=str(work / "shots" / "01_globals_versions.png"), clip=clip)
            page.evaluate("""() => document.getElementById('dcTextbook').removeAttribute('size')""")

            # ---- 错误二续：选版本 → 左栏顶级节点是册次 ----
            page.locator("#dcTextbook").select_option(label="人教A版")
            expect(page.locator(TREE + " .dcl-state")).to_contain_text("共 5 册", timeout=30000)
            volumes = page.evaluate(
                """() => Array.from(document.querySelectorAll('.dcl-tree-volume'))
                         .map(b => b.textContent.trim())""")
            check("左栏顶级节点是册次：必修一/二 + 选修一/二/三",
                  volumes == ["必修一", "必修二", "选修一", "选修二", "选修三"], {"volumes": volumes})
            page.screenshot(path=str(work / "shots" / "02_version_tree.png"),
                            clip=page.locator(TREE).bounding_box())
            page.evaluate(
                """() => document.querySelectorAll('.dcl-tree-book > .dcl-tree-row > .dcl-tree-caret')
                         .forEach(b => { if (b.getAttribute('aria-expanded') === 'true') b.click(); })""")
            page.wait_for_timeout(150)
            all_volumes = page.evaluate(
                """() => Array.from(document.querySelectorAll('.dcl-tree-volume'))
                         .map(b => { const r = b.getBoundingClientRect();
                             return {name: b.textContent.trim(), top: Math.round(r.top)}; })""")
            check("收起全部册次后五册次同屏可见",
                  [v["name"] for v in all_volumes] == ["必修一", "必修二", "选修一", "选修二", "选修三"]
                  and all_volumes[-1]["top"] - all_volumes[0]["top"] < 320,
                  {"visible": all_volumes})
            page.screenshot(path=str(work / "shots" / "02b_all_volumes.png"),
                            clip=page.evaluate("""() => { const r = document.querySelector('.dcl-tree')
                                  .getBoundingClientRect(); return {x: r.x + window.scrollX,
                                  y: r.y + window.scrollY, width: r.width, height: r.height}; }"""))
            page.locator(TREE + " .dcl-tree-book").first.locator(
                ":scope > .dcl-tree-row > .dcl-tree-caret").click()
            page.wait_for_timeout(150)

            # ---- 错误一：960011 的辅助栏不得再出现自己 ----
            page.locator(TREE + " .dcl-tree-node[data-id='" + str(CHAPTER_SET) + "']").click()
            expect(page.locator(POINTS + " .dcl-state")).to_contain_text("共", timeout=10000)
            page.locator(POINTS + " li.dcl-item[data-id='" + str(KP_MIXED) + "'] .dcl-item-main").click()
            expect(page.locator(DIRS + " .dcl-state")).to_contain_text("共", timeout=10000)
            page.locator(DIRS + " li.dcl-item[data-id='" + str(DIR_MIXED) + "'] .dcl-item-main").click()
            expect(page.locator(TAGS + " .dcl-state")).to_contain_text("共 0 个辅助标签", timeout=10000)
            tags_text = page.locator(TAGS + " .dcl-tag-list").inner_text()
            check("选中主知识点后辅助栏为空，不再重复自己",
                  "暂无辅助标签" in tags_text and "交、并、补集的混合运算" not in tags_text,
                  {"tags": tags_text})
            api_tags = api(page, "/api/bank/engine/linkage/directions/" + str(DIR_MIXED)
                           + "/tags?exclude_point_id=" + str(KP_MIXED))
            check("API 口径：1026 的辅助标签为 []（sort_order>0 且排除主点）",
                  api_tags.get("items") == [], {"items": api_tags.get("items")})
            page.locator(TAGS).scroll_into_view_if_needed()
            clip = page.evaluate("""() => { const r = document.querySelector('.dcl-grid').getBoundingClientRect();
                    return {x: r.x + window.scrollX, y: r.y + window.scrollY,
                            width: r.width, height: Math.min(r.height, 900)}; }""")
            page.screenshot(path=str(work / "shots" / "03_mixed_primary_no_dup.png"), clip=clip)

            # ---- 错误一正例：1113 有真正的辅助点，且主点缺席 ----
            page.locator(TREE + " .dcl-tree-node[data-id='" + str(CHAPTER_POW) + "']").click()
            expect(page.locator(POINTS + " .dcl-state")).to_contain_text("共", timeout=10000)
            page.locator(POINTS + " li.dcl-item[data-id='" + str(KP_POW) + "'] .dcl-item-main").click()
            expect(page.locator(DIRS + " .dcl-state")).to_contain_text("共", timeout=10000)
            page.locator(DIRS + " li.dcl-item[data-id='" + str(DIR_POW) + "'] .dcl-item-main").click()
            expect(page.locator(TAGS + " .dcl-state")).to_contain_text("共 1 个辅助标签", timeout=10000)
            tag_names = page.evaluate(
                """() => Array.from(document.querySelectorAll('.dcl-tag-list li.dcl-item'))
                         .map(li => ({id: li.getAttribute('data-id'),
                                      name: li.querySelector('.dcl-tag-name').textContent}))""")
            check("有辅助行的考向只显示真辅助点，主点不出现",
                  [t["id"] for t in tag_names] == [str(KP_POW_AUX)]
                  and "有理数指数幂及根式" not in [t["name"] for t in tag_names],
                  {"tags": tag_names})
            api_aux = api(page, "/api/bank/engine/linkage/directions/" + str(DIR_POW)
                          + "/tags?exclude_point_id=" + str(KP_POW))
            check("API 口径：1113 排除 960037 后仍返回 960038",
                  [i["id"] for i in api_aux.get("items", [])] == [KP_POW_AUX],
                  {"items": api_aux.get("items")})
            page.locator(TAGS).scroll_into_view_if_needed()
            clip = page.evaluate("""() => { const r = document.querySelector('.dcl-grid').getBoundingClientRect();
                    return {x: r.x + window.scrollX, y: r.y + window.scrollY,
                            width: r.width, height: Math.min(r.height, 900)}; }""")
            page.screenshot(path=str(work / "shots" / "04_aux_tags_only.png"), clip=clip)

            # ---- 几何：四栏不重叠、热区 ≥44px ----
            geometry = page.evaluate(
                """() => { const cols = Array.from(document.querySelectorAll('.dcl-col')).map(c => {
                        const r = c.getBoundingClientRect();
                        return {left: Math.round(r.left), right: Math.round(r.right),
                                width: Math.round(r.width)}; });
                    const nodes = Array.from(document.querySelectorAll('.dcl-tree-node, .dcl-item-main'))
                        .filter(el => el.getBoundingClientRect().width > 0)
                        .map(el => Math.round(el.getBoundingClientRect().height));
                    return {cols, minHeight: Math.min.apply(null, nodes),
                            overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth}; }""")
            result["geometry"] = geometry
            overlaps = any(geometry["cols"][i]["right"] > geometry["cols"][i + 1]["left"] + 1
                           for i in range(len(geometry["cols"]) - 1))
            check("四栏并排不重叠、页面不横溢、树节点热区 ≥44px",
                  len(geometry["cols"]) == 4 and not overlaps
                  and geometry["overflow"] <= 0 and geometry["minHeight"] >= 44, geometry)
            browser.close()
    except Exception as exc:
        result["fatal"] = repr(exc)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = (bool(result["checks"]) and all(item["ok"] for item in result["checks"])
                    and not result["page_errors"] and not result["console_errors"]
                    and "fatal" not in result)
    (work / "probe.toml").write_text(toml_io.dumps(result), encoding="utf-8")
    print(("PASS" if result["ok"] else "FAIL") + f" · {len(result['checks'])} 项 · {work}")
    for item in result["checks"]:
        print(("  ok " if item["ok"] else "  XX ") + item["name"])
    if result.get("fatal"):
        print("探针异常：" + result["fatal"])
    if result["page_errors"]:
        print("页面异常：" + " | ".join(result["page_errors"][:5]))
    if result["console_errors"]:
        print("控制台报错：" + " | ".join(result["console_errors"][:5]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

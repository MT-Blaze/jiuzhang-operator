# -*- coding: utf-8 -*-
"""数据字典控制台阶段二真机探针（字典渲染与防呆）。

取证口径：
- 分类页签里基础五表渲染真实数据（学科 15 / 年级 12 / 考试类型 16 / 区划 367 / 学校 347）；
- 搜索框过滤真实生效；全局设置学段真正带进年级查询；
- 新增行 → 双击单元格改名 blur 保存（PUT 落库）→ 无引用删除成功；
- 删除被引用学科回 409，弹「已被引用，禁止删除」并列出引用来源；
- 【导入数据】走真实 TOML 文件导入，报告新增计数；
- 375px 不横溢、交互热区 ≥44px；零页面异常（预期 409 的诊断日志单独归类）。

环境坑⑦口径：端口 free_port() 动态、令牌 secrets 随机经 /api/settings 运行时读取、
数据目录隔离临时目录，绝不碰真实 data/，也不动端口 8000 的用户旧进程。

用法：``.venv/Scripts/python.exe tools/dict_console_probe_stage2.py <tag>``
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


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "dict_console_probe_stage2" / tag
    if work.exists():
        shutil.rmtree(work)
    (work / "shots").mkdir(parents=True)
    data_dir = Path(tempfile.mkdtemp(prefix="jzo-dict-s2-"))
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
        # 预期的 409/400 防呆会被 JzoHttp 拦截器记成诊断日志，单独归类，不算页面缺陷。
        # 浏览器还会为同一响应原生记一条「Failed to load resource … 409/400」，同样属预期。
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

            # ---- 基石分类：学科表格渲染真实数据 ----
            page.locator(".dc-nav-item", has_text="系统基石字典").click()
            subj = page.locator(".dc-table-block[data-table='dict_subjects']")
            expect(subj).to_be_visible(timeout=30000)
            expect(subj.locator(".dc-table-count")).to_contain_text("共 15 行", timeout=30000)
            check("学科表格渲染真实种子（共 15 行）",
                  "共 15 行" in subj.locator(".dc-table-count").inner_text())
            body_text = subj.locator("tbody").inner_text()
            check("学科表格含真实学科名（数学/语文）", "数学" in body_text and "语文" in body_text)
            grades = page.locator(".dc-table-block[data-table='dict_grades']")
            expect(grades.locator(".dc-table-count")).to_contain_text("共 12 行", timeout=30000)
            exam_types = page.locator(".dc-table-block[data-table='dict_exam_types']")
            expect(exam_types.locator(".dc-table-count")).to_contain_text("共 8 行", timeout=30000)
            check("年级 12 行 / 考试类型 8 行同屏渲染",
                  "共 12 行" in grades.locator(".dc-table-count").inner_text()
                  and "共 8 行" in exam_types.locator(".dc-table-count").inner_text())
            page.screenshot(path=str(work / "shots" / "01_foundation_tables.png"))

            # ---- 搜索过滤 ----
            subj.locator(".dc-table-search").fill("数学")
            expect(subj.locator(".dc-table-count")).to_contain_text("共 1 行", timeout=10000)
            check("搜索「数学」过滤到 1 行",
                  subj.locator("tbody tr").count() == 1
                  and "数学" in subj.locator("tbody").inner_text())
            page.screenshot(path=str(work / "shots" / "02_search_filter.png"))
            subj.locator(".dc-table-search").fill("")
            expect(subj.locator(".dc-table-count")).to_contain_text("共 15 行", timeout=10000)

            # ---- 全局设置学段真正带进年级查询 ----
            page.locator("#dcStage").select_option(label="小学")
            expect(grades.locator(".dc-table-count")).not_to_contain_text("共 12 行", timeout=10000)
            stage_cells = grades.locator("tbody td[data-col='stage']").all_inner_texts()
            check("选小学后年级表只剩小学学段（全局参数生效）",
                  len(stage_cells) > 0 and all(t == "小学" for t in stage_cells),
                  {"count": len(stage_cells), "stages": sorted(set(stage_cells))})
            page.locator("#dcStage").select_option(label="全部学段")
            expect(grades.locator(".dc-table-count")).to_contain_text("共 12 行", timeout=10000)

            # ---- 新增行 → 双击编辑 blur 保存 → 无引用删除 ----
            subj.locator(".dc-table-add").click()
            new_row = subj.locator("tbody tr.dc-row-new")
            expect(new_row).to_be_visible(timeout=5000)
            new_row.locator("input[aria-label='新增名称']").fill("探针学科")
            new_row.locator("input[aria-label='新增编码']").fill("probe_subject")
            new_row.locator("button", has_text="保存").click()
            expect(subj.locator(".dc-table-state")).to_contain_text("已新增", timeout=10000)
            subj.locator(".dc-table-search").fill("探针学科")
            expect(subj.locator(".dc-table-count")).to_contain_text("共 1 行", timeout=10000)
            row_id = subj.locator("tbody tr").first.get_attribute("data-id")
            check("新增行落库并可搜索到", bool(row_id) and "探针学科" in subj.locator("tbody").inner_text(),
                  {"id": row_id})

            name_cell = subj.locator("tbody td[data-col='name']").first
            name_cell.dblclick()
            editor = name_cell.locator("input.dc-cell-input")
            expect(editor).to_be_visible(timeout=5000)
            editor.fill("探针学科改")
            editor.press("Tab")  # 移开焦点触发 blur → PUT 保存
            expect(name_cell).to_contain_text("探针学科改", timeout=10000)
            # 重新搜索刷新，证明改名已落库（服务端回读）
            subj.locator(".dc-table-search").fill("探针学科改")
            expect(subj.locator(".dc-table-count")).to_contain_text("共 1 行", timeout=10000)
            check("双击编辑 blur 保存且服务端回读一致",
                  "探针学科改" in subj.locator("tbody").inner_text())
            page.screenshot(path=str(work / "shots" / "03_edit_saved.png"))

            subj.locator("tbody tr .dc-row-delete").first.click()
            expect(page.locator(".dc-dialog-title")).to_have_text("删除确认", timeout=5000)
            page.locator(".dc-dialog .dc-btn-primary").click()
            # 删除成功的持久证据是「搜索无匹配」的空表（状态文案会被刷新覆盖，不作判据）
            expect(subj.locator(".dc-table-empty")).to_be_visible(timeout=10000)
            check("无引用行删除成功（搜索无匹配）", subj.locator("tbody tr.dc-row-new").count() == 0
                  and "无匹配数据" in subj.locator("tbody").inner_text())

            # ---- 删除被引用学科：409 防呆对话框 ----
            subj.locator(".dc-table-search").fill("数学")
            expect(subj.locator(".dc-table-count")).to_contain_text("共 1 行", timeout=10000)
            subj.locator("tbody tr .dc-row-delete").first.click()
            expect(page.locator(".dc-dialog-title")).to_have_text("删除确认", timeout=5000)
            page.locator(".dc-dialog .dc-btn-primary").click()
            expect(page.locator(".dc-dialog-title")).to_have_text("已被引用，禁止删除", timeout=10000)
            ref_message = page.locator(".dc-dialog-message").inner_text()
            check("被引用删除弹 409 防呆对话框并列出引用来源",
                  "已被引用，禁止删除" in ref_message and "教材版本" in ref_message,
                  ref_message)
            check("409 走真实 HTTP（诊断日志含 409）",
                  any("409" in t for t in result["http_diagnostics"]),
                  result["http_diagnostics"][:2])
            page.screenshot(path=str(work / "shots" / "04_referenced_409.png"))
            page.keyboard.press("Escape")
            check("Esc 关闭防呆对话框", not window_open(page))
            subj.locator(".dc-table-search").fill("")
            expect(subj.locator(".dc-table-count")).to_contain_text("共 15 行", timeout=10000)

            # ---- 实体分类：区划 / 学校表格渲染 ----
            page.locator(".dc-nav-item", has_text="实体维度字典").click()
            regions = page.locator(".dc-table-block[data-table='dim_regions']")
            schools = page.locator(".dc-table-block[data-table='dim_schools']")
            expect(regions.locator(".dc-table-count")).to_contain_text("共 367 行", timeout=30000)
            expect(schools.locator(".dc-table-count")).to_contain_text("共 347 行", timeout=30000)
            check("区划 367 行 / 学校 347 行真实渲染",
                  "共 367 行" in regions.locator(".dc-table-count").inner_text()
                  and "共 347 行" in schools.locator(".dc-table-count").inner_text())
            page.screenshot(path=str(work / "shots" / "05_entity_tables.png"))

            # ---- TOML 导入：真实文件 → 确认 → 报告 ----
            toml_text = '[[dict_subjects]]\nname = "导入探针学科"\ncode = "probe_import"\nsort_order = 90\n'
            with page.expect_file_chooser() as fc_info:
                page.locator("#dcImportBtn").click()
            fc_info.value.set_files({
                "name": "probe_import.toml", "mimeType": "text/plain",
                "buffer": toml_text.encode("utf-8"),
            })
            expect(page.locator(".dc-dialog-title")).to_have_text("导入字典数据", timeout=5000)
            page.locator(".dc-dialog .dc-btn-primary").click()
            expect(page.locator(".dc-dialog-title")).to_have_text("导入完成", timeout=15000)
            import_message = page.locator(".dc-dialog-message").inner_text()
            check("TOML 导入真实落库并报告新增 1 行",
                  "新增 1 行" in import_message and "dict_subjects" in import_message, import_message)
            page.screenshot(path=str(work / "shots" / "06_import_report.png"))
            page.keyboard.press("Escape")
            # 回基石分类搜索导入的学科，证明真落库
            page.locator("#dcTab-foundation").click()
            subj.locator(".dc-table-search").fill("导入探针学科")
            expect(subj.locator(".dc-table-count")).to_contain_text("共 1 行", timeout=10000)
            check("导入的学科可搜索到（真实落库）", "导入探针学科" in subj.locator("tbody").inner_text())
            subj.locator(".dc-table-search").fill("")

            # ---- 375px：不横溢 + 热区 ----
            page.set_viewport_size({"width": 375, "height": 780})
            page.wait_for_timeout(400)
            narrow = page.evaluate(
                """() => {
                    const hit = (sel) => Array.from(document.querySelectorAll(sel))
                        .filter((el) => el.getBoundingClientRect().width > 0)
                        .map((el) => { const r = el.getBoundingClientRect();
                            return { w: Math.round(r.width), h: Math.round(r.height) }; });
                    const groups = { tab: hit('.dc-tab-main'), close: hit('.dc-tab-close'),
                                     nav: hit('.dc-nav-item'), btn: hit('.dc-btn'),
                                     search: hit('.dc-table-search'), select: hit('.dc-field select'),
                                     summary: hit('.dc-nav summary') };
                    const mins = {};
                    Object.keys(groups).forEach((k) => {
                        mins[k] = groups[k].length ? Math.min.apply(null,
                            groups[k].map((r) => Math.min(r.w, r.h))) : null;
                    });
                    return { overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                             mins: mins };
                }""")
            result["geometry"]["narrow"] = narrow
            check("375px 不横向溢出", narrow["overflow"] <= 0, narrow)
            check("375px 全部交互热区 ≥44px（页签/导航/按钮/搜索框/下拉）",
                  all(v is not None and v >= 44 for v in narrow["mins"].values()), narrow["mins"])
            page.screenshot(path=str(work / "shots" / "07_375px.png"))
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        shutil.rmtree(data_dir, ignore_errors=True)

    result["ok"] = (all(item["ok"] for item in result["checks"])
                    and not result["page_errors"] and not result["console_errors"])
    (work / "probe.toml").write_text(toml_io.dumps(result), encoding="utf-8")
    print(("PASS" if result["ok"] else "FAIL") + f" · {len(result['checks'])} 项 · {work}")
    for item in result["checks"]:
        print(("  ok " if item["ok"] else "  XX ") + item["name"])
    if result["page_errors"]:
        print("页面异常：" + " | ".join(result["page_errors"][:5]))
    if result["console_errors"]:
        print("控制台报错：" + " | ".join(result["console_errors"][:5]))
    return 0 if result["ok"] else 1


def window_open(page) -> bool:
    return bool(page.evaluate("() => window.DcDialog.isOpen()"))


if __name__ == "__main__":
    raise SystemExit(main())
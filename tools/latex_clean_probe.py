# -*- coding: utf-8 -*-
"""LaTeX 清洗「先看后换」真机取证（军令 #31 · 4.3，设计 §5.6 判据 4~10）。

用法：``.venv/Scripts/python.exe tools/latex_clean_probe.py <tag>``

隔离口径：editor 插件复制进独立插件目录，另起随机端口与独立 ``JZO_DATA_DIR``，
不碰本机 ``data/``。三批各一道题——① 题干与解析都脏、② 两段都已规范、
③ 解析段里带 ``\\begin{choices}``——随后**只走界面**：批次列表点入审核、
辅助栏掀开【AI 帮改】、点【清洗当前题 LaTeX】、逐段点【采用替换】/【放弃】、
Esc 收窗、关掉画布页签再试图清洗。

每题一批是刻意的：画布的「跳到第 N 题」会被滚动跟随改走当前题，
把判据挂在跳题上会测到错的题；一题一批则 ``openBatch`` 直接把当前题定为第 0 题，
画布活动题与辅助栏选区必然同源。

判据：
- 清洗只出预览，**点采用之前一条 ``editor.apply_patch`` 都不发**（底栏留痕计数）；
- 预览浮层左右两栏在像素上确有差异（真看到对照，不是两块同文）；
- 采用后画布源码的题干段/解析段 == 浮层右栏所见，且 choices 块与「答案：」行逐字节不动；
- 已规范文本 → 无浮层、无按钮、摘要写「未改动」；
- 解析段含选项块 → 【采用替换】禁用，绝不允许整段覆盖结构；
- Esc 收窗后辅助栏收到 ``closed`` 回执，焦点回到【清洗当前题 LaTeX】；
- 画布不在场时绝不发生回填（降级锁键或辅助栏一并退场，二者都不许发出 patch）；
- 全程只改内存里的画布源码，中转池里的题目一个字节都不动。
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

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
sys.path.insert(0, str(ROOT / "tools"))
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
from pixel_scan import decode_png  # noqa: E402  纯标准库 PNG 解码，复用既有像素工具

EDITOR_ID = "org.jiuzhang.editor"
TOKEN = "latex-clean-probe-token"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
PANEL = "#wsContextSlot .ws-context-frame"

DIRTY_STEM = r"探针清洗题：已知 \(x>0\)，求 \[y=\dfrac{1}{x}\] 的最小值（  ）"
DIRTY_SOLUTION = r"由 \(x>0\) 得 \(y=x+\dfrac{1}{x}\ge 2\)，当 \(x=1\) 时取等，故最小值为 \fillin。"
CLEAN_STEM = r"探针规范题：已知 $x>0$，求 $y=\frac{1}{x}$ 的最小值（  ）"
CLEAN_SOLUTION = r"由 $x>0$ 得 $y\ge 2$，故最小值为 2。"
CHOICE_SOLUTION = ("由 \\(x>0\\) 得 \\(y\\ge 2\\)。选项对照：\\begin{choices}\n"
                   "\\item $1$\n\\item $2$\n\\end{choices}")


def _doc(stem: str, solution: str) -> dict:
    return {
        "schema_version": "2.0",
        "type": "single_choice",
        "stem": stem,
        "options": [{"key": "A", "content": r"$0$"}, {"key": "B", "content": r"$1$"}],
        "answer": {"kind": "choice", "choice_keys": ["B"], "final": "B"},
        "solution": solution,
        "difficulty": "L1",
        "grade": "高一",
        "tags": ["探针清洗"],
        "source": {"paper_title": "探针清洗卷", "question_no": "1", "year": 2024,
                   "exam_type": "一模"},
    }


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, wire.loads(payload or "{}")
        except wire.JSONDecodeError:
            return error.code, {"raw": payload}


def http_post(url: str, payload: dict) -> tuple[int, dict]:
    body = wire.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, wire.loads(payload or "{}")
        except wire.JSONDecodeError:
            return error.code, {"raw": payload}


def wait_health(base: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("服务提前退出：\n" + log_path.read_text(
                encoding="utf-8", errors="replace")[:3000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 40 秒内就绪")


def stem_region(source: str) -> str:
    r"""题干段：question 环境与 choices 之间（格式宪法锁死的那一段）。"""
    start = source.index("\\begin{question}") + len("\\begin{question}")
    stop = source.index("\\begin{choices}", start)
    return source[start:stop].strip()


def solution_region(source: str) -> str:
    r"""解析段：solution 正文里、「答案：」首行之后那一段。"""
    start = source.index("\\begin{solution}") + len("\\begin{solution}")
    stop = source.index("\\end{solution}", start)
    body = source[start:stop]
    head = re.match(r"^[ \t]*答案\s*[:：][^\n]*\n", body)
    return body[head.end():].strip() if head else body.strip()


def locked_blocks(source: str) -> dict:
    r"""清洗不许碰的两块：choices 整块与「答案：」行，逐字节取出来对比。"""
    choices_start = source.index("\\begin{choices}")
    choices_end = source.index("\\end{choices}") + len("\\end{choices}")
    answer = re.search(r"^[ \t]*答案\s*[:：][^\n]*$", source, re.MULTILINE)
    return {"choices": source[choices_start:choices_end],
            "answer_line": answer.group(0) if answer else ""}


def pixel_diff(path_a: Path, path_b: Path) -> dict:
    """两张截图逐像素比差异占比——只有几何判据主公不认，这里要的是像素。"""
    wa, ha, ca, ba = decode_png(path_a)
    wb, hb, cb, bb = decode_png(path_b)
    width, height = min(wa, wb), min(ha, hb)
    if width < 8 or height < 8:
        return {"ok": False, "reason": "截图太小", "a": [wa, ha], "b": [wb, hb]}
    stride_a, stride_b = wa * ca, wb * cb
    differs = 0
    for y in range(height):
        row_a = y * stride_a
        row_b = y * stride_b
        for x in range(width):
            oa = row_a + x * ca
            ob = row_b + x * cb
            if ba[oa:oa + 3] != bb[ob:ob + 3]:
                differs += 1
    total = width * height
    return {"ok": True, "a": [wa, ha], "b": [wb, hb], "total": total,
            "differs": differs, "ratio": round(differs / total, 6)}


def dock_patch_count(dock_text: str) -> int:
    return (dock_text.count("请求把改写的题干回填")
            + dock_text.count("请求把改写的解析回填"))


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "latex_clean_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    shutil.copytree(PLUGIN_SOURCE_DIR / EDITOR_ID, plugins_dir / EDITOR_ID)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["JZO_RESTART_DISABLED"] = "1"
    server_log = work / "server.log"
    log_handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": [], "metrics": {}, "shots": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    def shot(name: str) -> Path:
        path = shots / name
        result["shots"].append(str(path))
        return path

    try:
        wait_health(base, process, server_log)
        batch_ids: list[str] = []
        for stem, solution in ((DIRTY_STEM, DIRTY_SOLUTION),
                               (CLEAN_STEM, CLEAN_SOLUTION),
                               (DIRTY_STEM, CHOICE_SOLUTION)):
            status, body = http_post(
                base + "/api/pending/batches",
                {"questions": [{"question": _doc(stem, solution)}], "origin": "probe.clean"})
            batch_ids.append(str(body.get("batch_id") or ""))
            if status != 201 or not batch_ids[-1]:
                raise RuntimeError("入池失败：status=%s body=%s" % (status, body))
        _, pool = http_json(base + f"/api/pending/batches/{batch_ids[0]}/questions")
        pool_doc_before = wire.dumps((pool.get("items") or [{}])[0].get("question"),
                                     ensure_ascii=False, sort_keys=True)
        check("三批各一道题入池（脏 / 已规范 / 解析带选项块）",
              len(set(batch_ids)) == 3 and all(batch_ids), {"batches": batch_ids})

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1560, "height": 1000})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type == "error" else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url))
                if response.status >= 400 else None)
            clean_calls: list[str] = []
            page.on("request", lambda request: clean_calls.append(request.url)
                    if "/api/agent/clean_latex" in request.url else None)
            page.goto(base + "/workspace", wait_until="networkidle")

            canvas = page.frame_locator(CANVAS)
            panel = page.frame_locator(PANEL)
            dock = page.locator("#wsDockLog")

            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)

            def dock_text() -> str:
                return dock.inner_text() if dock.count() else ""

            def open_batch(batch_id: str) -> None:
                row = canvas.locator('.ed-batch-row[data-batch="%s"]' % batch_id)
                expect(row).to_be_visible(timeout=20000)
                row.locator(".ed-batch-open").click()
                expect(canvas.locator(".ed-src-area")).to_have_count(1, timeout=20000)
                page.wait_for_timeout(500)

            def back_to_list() -> None:
                panel.locator("#epBackList").click()
                expect(canvas.locator(".ed-batch-row")).to_have_count(3, timeout=20000)
                page.wait_for_timeout(400)

            clean_button = panel.locator("#epAiClean")
            deadline = time.time() + 20
            while time.time() < deadline and clean_button.count() == 0:
                page.wait_for_timeout(150)

            # ================= ①脏题：预览 → 逐段采用 =================
            open_batch(batch_ids[0])
            # 军令#32·S9b：AI 帮改块**默认就是展开**（data-fold="open"），无条件点反而把它收掉、
            # 清洗键就此不可见。只有当前不是 open 才补一次掀开（兼容老师手动收起的态）。
            if panel.locator("#epAiSec").get_attribute("data-fold") != "open":
                panel.locator("#epAiFold").click()
                page.wait_for_timeout(150)
            expect(clean_button).to_be_enabled(timeout=20000)
            expect(clean_button).to_be_visible(timeout=10000)
            check("点入批次后画布出源码框，辅助栏【清洗当前题 LaTeX】可见可用",
                  canvas.locator(".ed-src-area").count() == 1
                  and clean_button.is_enabled() and clean_button.is_visible()
                  and "清洗当前题 LaTeX" in clean_button.inner_text(),
                  {"label": clean_button.inner_text()})

            area = canvas.locator('.ed-src-area[data-index="0"]')
            source_before = area.input_value()
            blocks_before = locked_blocks(source_before)
            clean_button.click()
            modal = canvas.locator("#edCleanModal")
            expect(modal).to_be_visible(timeout=20000)
            sections = canvas.locator("#edCleanSections .ed-clean-section")
            expect(sections).to_have_count(2, timeout=20000)
            heads = [t.strip() for t in sections.locator(".ed-clean-head").all_inner_texts()]
            note = canvas.locator("#edCleanNote").inner_text().strip()
            check("点清洗后画布浮层出现，题干与解析两段都标「有改动」",
                  heads == ["题干 · 有改动", "解析 · 有改动"] and "2 段有改动" in note,
                  {"heads": heads, "note": note})
            check("未点采用之前一条 apply_patch 都不发",
                  dock_patch_count(dock_text()) == 0,
                  {"dock": dock_text()[-400:]})

            left_card = sections.nth(0).locator(".ed-dup-side").nth(0)
            right_card = sections.nth(0).locator(".ed-dup-side").nth(1)
            seen_before = left_card.locator(".ed-dup-body").inner_text()
            seen_stem = right_card.locator(".ed-dup-body").inner_text()
            left_card.screenshot(path=str(shot("clean-left-stem.png")))
            right_card.screenshot(path=str(shot("clean-right-stem.png")))
            page.screenshot(path=str(shot("clean-overlay-open.png")))
            diff = pixel_diff(shots / "clean-left-stem.png", shots / "clean-right-stem.png")
            result["metrics"]["pixel_diff"] = diff
            check("浮层左右两栏在像素上确有差异（不是两块同文）",
                  bool(diff.get("ok")) and diff.get("ratio", 0) > 0.005, diff)
            check("清洗真生效：右栏已无 \\( \\[ \\dfrac \\fillin 脏写法",
                  seen_stem != seen_before
                  and not re.search(r"\\\(|\\\[|\\dfrac|\\fillin", seen_stem),
                  {"before": seen_before[:70], "after": seen_stem[:70]})

            panel.locator("#epCleanApplyStem").click()
            deadline = time.time() + 15
            stem_now = area.input_value()
            while time.time() < deadline:
                stem_now = area.input_value()
                if stem_region(stem_now) == seen_stem.strip():
                    break
                page.wait_for_timeout(120)
            patches_after_stem = dock_patch_count(dock_text())
            check("点【采用替换（题干）】：底栏只多一条「题干」回填留痕，画布题干段==浮层右栏所见",
                  patches_after_stem == 1 and "请求把改写的题干回填" in dock_text()
                  and stem_region(stem_now) == seen_stem.strip(),
                  {"patches": patches_after_stem, "canvas_stem": stem_region(stem_now)[:70],
                   "overlay_after": seen_stem.strip()[:70]})
            check("采用题干后 choices 块与「答案：」行逐字节未动",
                  locked_blocks(stem_now) == blocks_before,
                  {"before": blocks_before, "after": locked_blocks(stem_now)})

            seen_solution = (sections.nth(1).locator(".ed-dup-side").nth(1)
                             .locator(".ed-dup-body").inner_text())
            stem_frozen = stem_region(stem_now)
            panel.locator("#epCleanApplySolution").click()
            deadline = time.time() + 15
            source_two = area.input_value()
            while time.time() < deadline:
                source_two = area.input_value()
                if solution_region(source_two) == seen_solution.strip():
                    break
                page.wait_for_timeout(120)
            patches_after_solution = dock_patch_count(dock_text())
            check("点【采用替换（解析）】：计数变 2 且这条写「解析」，解析段==所见",
                  patches_after_solution == 2 and "请求把改写的解析回填" in dock_text()
                  and solution_region(source_two) == seen_solution.strip(),
                  {"patches": patches_after_solution,
                   "canvas_solution": solution_region(source_two)[:70]})
            check("第二段采用不再动第一段：题干段与上一次完全一致",
                  stem_region(source_two) == stem_frozen,
                  {"frozen": stem_frozen[:70], "now": stem_region(source_two)[:70]})
            deadline = time.time() + 10
            summary = panel.locator("#epCleanSummary").inner_text()
            while time.time() < deadline and not modal.is_hidden():
                page.wait_for_timeout(120)
                summary = panel.locator("#epCleanSummary").inner_text()
            focused = panel.locator("#epRoot").evaluate(
                "() => String(document.activeElement && document.activeElement.id || '')")
            page.screenshot(path=str(shot("clean-adopted-both.png")))
            check("两段都替换完：摘要标两个「已替换」，浮层自己收掉、焦点回到清洗键",
                  summary.count("已替换") == 2 and modal.is_hidden()
                  and focused == "epAiClean",
                  {"summary": summary, "modal_hidden": modal.is_hidden(),
                   "activeElement": focused})

            # ================= ②已规范题：无浮层、无按钮 =================
            _, pool_mid = http_json(base + f"/api/pending/batches/{batch_ids[0]}/questions")
            pool_doc_mid = wire.dumps((pool_mid.get("items") or [{}])[0].get("question"),
                                      ensure_ascii=False, sort_keys=True)
            check("两段都采用后：中转池里那道题仍与入池时逐字节相同（采用只改内存里的画布源码）",
                  pool_doc_mid == pool_doc_before,
                  {"same": pool_doc_mid == pool_doc_before, "head": pool_doc_mid[:200]})
            back_to_list()
            open_batch(batch_ids[1])
            clean_button.click()
            page.wait_for_timeout(1500)
            summary2 = panel.locator("#epCleanSummary").inner_text()
            check("已规范文本清洗：不出浮层、四按钮都不出现",
                  canvas.locator("#edCleanModal").is_hidden()
                  and panel.locator("#epCleanApplyStem").is_hidden()
                  and panel.locator("#epCleanApplySolution").is_hidden()
                  and panel.locator("#epCleanDropStem").is_hidden()
                  and panel.locator("#epCleanDropSolution").is_hidden(),
                  {"summary": summary2})
            check("已规范文本摘要写两个「未改动」，且 apply_patch 计数仍是 2",
                  summary2.count("未改动") == 2 and dock_patch_count(dock_text()) == 2,
                  {"summary": summary2, "patches": dock_patch_count(dock_text())})
            page.screenshot(path=str(shot("clean-already-canonical.png")))

            # ================= ③解析段带 choices：采用锁死 + Esc =================
            back_to_list()
            open_batch(batch_ids[2])
            clean_button.click()
            expect(canvas.locator("#edCleanModal")).to_be_visible(timeout=20000)
            apply_sol = panel.locator("#epCleanApplySolution")
            drop_sol = panel.locator("#epCleanDropSolution")
            expect(apply_sol).to_be_disabled(timeout=10000)
            check("解析段含选项块 → 【采用替换（解析）】禁用、【放弃】仍可用",
                  apply_sol.is_disabled() and drop_sol.is_enabled(),
                  {"summary": panel.locator("#epCleanSummary").inner_text()})
            page.screenshot(path=str(shot("clean-choices-locked.png")))
            canvas.locator("#edCleanTitle").click()
            page.keyboard.press("Escape")
            deadline = time.time() + 10
            while time.time() < deadline and not canvas.locator("#edCleanModal").is_hidden():
                page.wait_for_timeout(120)
            esc_focus = panel.locator("#epRoot").evaluate(
                "() => String(document.activeElement && document.activeElement.id || '')")
            check("Esc 关预览：画布浮层收起，辅助栏收到 closed 回执并把焦点还给清洗键",
                  canvas.locator("#edCleanModal").is_hidden() and esc_focus == "epAiClean",
                  {"activeElement": esc_focus})
            panel.locator("#epCleanDropStem").click()
            panel.locator("#epCleanDropSolution").click()
            page.wait_for_timeout(700)
            summary3 = panel.locator("#epCleanSummary").inner_text()
            check("两段都放弃：摘要标两个「已放弃」，一条 apply_patch 都没多发",
                  summary3.count("已放弃") == 2 and dock_patch_count(dock_text()) == 2,
                  {"summary": summary3, "patches": dock_patch_count(dock_text())})

            # ================= 画布不在场：绝不发生回填 =================
            back_to_list()
            open_batch(batch_ids[2])
            tab = page.locator('#wsTabs [data-tab="plugin:%s"]' % EDITOR_ID)
            if tab.count() == 0:
                tab = page.locator('.ws-tab', has_text="录题工作台")
            expect(tab.first).to_be_visible(timeout=10000)
            tab.first.locator(".ws-tab-close").click()
            expect(page.locator(CANVAS)).to_have_count(0, timeout=20000)
            panel_alive = panel.locator("#epAiClean").count() > 0
            clicked = False
            if panel_alive and panel.locator("#epAiClean").is_enabled():
                panel.locator("#epAiClean").click()
                clicked = True
                page.wait_for_timeout(1500)
            degraded = (panel.locator("#epCleanSummary").inner_text() if panel_alive else "")
            buttons = ([panel.locator(sel).is_disabled() for sel in
                        ("#epCleanApplyStem", "#epCleanDropStem",
                         "#epCleanApplySolution", "#epCleanDropSolution")]
                       if panel_alive else [])
            page.screenshot(path=str(shot("clean-canvas-closed.png")))
            result["metrics"]["canvas_closed"] = {
                "panel_alive": panel_alive, "clicked": clicked,
                "summary": degraded, "buttons_disabled": buttons,
                "patches": dock_patch_count(dock_text())}
            check("画布不在场时清洗绝不产生回填：要么降级锁四键，要么辅助栏一并退场",
                  dock_patch_count(dock_text()) == 2
                  and (not panel_alive or (all(buttons) and "画布未打开" in degraded)),
                  result["metrics"]["canvas_closed"])

            check("清洗全程走宿主 text.clean_latex 确定性端点，未调用大模型",
                  len(clean_calls) >= 6 and all("/api/agent/clean_latex" in url
                                               for url in clean_calls),
                  {"count": len(clean_calls)})
            browser.close()

        _, pool_after = http_json(base + f"/api/pending/batches/{batch_ids[0]}/questions")
        rows_after = pool_after.get("items") or []
        result["metrics"]["pool_after_leave"] = wire.dumps(
            (rows_after[0].get("question") if rows_after else {}), ensure_ascii=False)[:300]
        check("清洗全程不新增题、不删题（池子里还是那一道）",
              len(rows_after) == 1, {"rows": len(rows_after),
                                     "pool": result["metrics"]["pool_after_leave"][:200]})
        check("宿主页无未捕获 JS 错误", not result["page_errors"],
              {"page_errors": result["page_errors"][:5]})
        check("全程无 4xx/5xx 响应", not result["http_failures"],
              {"http_failures": result["http_failures"][:6]})
    except Exception as exc:  # noqa: BLE001 - 探针要把异常也写进回传单
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log_handle.close()

    passed = sum(1 for entry in result["checks"] if entry["ok"])
    total = len(result["checks"])
    result["passed"] = passed
    result["total"] = total
    report = work / "probe.toml"
    report.write_text(toml_io.dumps(result), encoding="utf-8")
    print(wire.dumps({"tag": tag, "passed": passed, "total": total,
                      "error": result.get("error"), "report": str(report)},
                     ensure_ascii=False))
    for entry in result["checks"]:
        if not entry["ok"]:
            print("FAIL:", entry["name"], wire.dumps(entry["detail"], ensure_ascii=False)[:320])
    return 0 if passed == total and total > 0 and not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())

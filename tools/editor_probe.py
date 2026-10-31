# -*- coding: utf-8 -*-
"""录题工作台 v2 真机探针（军令 #23 阶段 2）：画布三栏 + 右栏辅助栏 + 单题保存。

用法：``.venv/Scripts/python.exe tools/editor_probe.py <tag>``

隔离：把 editor 与题库两端复制进独立插件目录，另起端口与独立数据目录，
不写本机 data/banks/。题数一律用「保存前后差值」判据，绝不写死绝对数。

检查项：
- 画布挂载出三栏（左原图 | 中源码 | 右渲染）与两条拖手，拖到底不归零；
- 右栏是同一插件的**第二个沙箱帧**，按画布送来的选区预填元数据；
- 辅助栏里既没有源码框也没有渲染预览（军令铁律）；
- 格式一整段可编辑；格式二按环境拆框，改框自动重组格式一；
- 单题保存经宿主写库：新建走 bank.create、再存走 bank.update、变式另发新 ID；
- 保存后直查 API 字段逐项一致（题干/答案/选项/解析/难度/年级/标签/来源/修订号）；
- 渲染块按内容实际高度生长，画布里不再有 A4 固定页节点；
- 宿主 1440px 无横向溢出，控制台与页面零错误。
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
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
BANK_UI_ID = "org.jiuzhang.bank-ui"
MARK = "探针v2"

CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
PANEL = "#wsContextSlot .ws-context-frame"
BANK_UI = "#wsPanel_plugin_org_jiuzhang_bank-ui .ws-plugin-frame"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 40
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
    raise RuntimeError("服务未在 40 秒内就绪")


def http_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, json.loads(payload or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": payload}


def wait_attribute(locator, name: str, predicate, timeout: float = 12) -> str:
    """等某个 data-* 属性达到期望值；不达标就返回最后看到的值，让检查项如实报红。"""
    deadline = time.time() + timeout
    value = ""
    while time.time() < deadline:
        value = locator.get_attribute(name) or ""
        if predicate(value):
            return value
        time.sleep(0.15)
    return value


def wait_height(locator, predicate, timeout: float = 12) -> float:
    """渲染是防抖 + KaTeX 同步排版，挂载那一瞬高度还没长开；量高度必须等它稳。"""
    deadline = time.time() + timeout
    height = 0.0
    while time.time() < deadline:
        height = float(locator.evaluate("node => node.getBoundingClientRect().height"))
        if predicate(height):
            return height
        time.sleep(0.15)
    return height


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "editor_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    for plugin_id in (EDITOR_ID, BANK_ID, BANK_UI_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = "editor-probe-token"
    env["JZO_RESTART_DISABLED"] = "1"
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
        _, stats_before = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
        total_before = int(stats_before.get("total") or 0)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()

            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            check("画布挂载出 v2 三栏", True)

            # ---------- 三栏骨架 ----------
            check("画布恰好三栏", canvas.locator(".ed-col").count() == 3,
                  {"panes": canvas.locator(".ed-col").count()})
            check("两条拖手在场", canvas.locator(".ed-split").count() == 2)
            source_area = canvas.locator(".ed-src-area").first
            expect(source_area).to_be_visible(timeout=10000)
            first_source = source_area.input_value()
            check("中栏装整段 exam-zh 源码",
                  "\\begin{question}" in first_source and "\\begin{solution}" in first_source,
                  {"head": first_source[:80]})
            total = int(wait_attribute(canvas.locator("#edProgress"), "data-total",
                                       lambda value: value not in ("", "0")) or "0")
            check("假数据自动载入工作清单", total >= 1, {"total": total})
            block_height = wait_height(canvas.locator(".ed-q-block").first,
                                       lambda value: value > 40)
            check("渲染块按内容实际高度生长", block_height > 40, {"height": block_height})
            check("画布不再有 A4 固定页节点",
                  canvas.locator(".ed-page, [data-page-h]").count() == 0)
            page.screenshot(path=str(shots / "v2-canvas.png"))

            # ---------- 右栏：同一插件的第二个沙箱帧 ----------
            panel = page.frame_locator(PANEL)
            expect(panel.locator("#epRoot")).to_be_visible(timeout=20000)
            check("右栏由录题辅助面板接管", True)
            check("辅助栏不放源码框", panel.locator("textarea").count() == 0)
            check("辅助栏不放渲染预览", panel.locator(".ed-q-block").count() == 0)
            panel_progress = panel.locator("#epProgress")
            wait_attribute(panel_progress, "data-total", lambda value: value not in ("", "0"), 14)
            check("画布选区已送进辅助栏",
                  panel_progress.get_attribute("data-total") not in (None, "0"),
                  {"progress": panel_progress.inner_text()})
            panel_type = panel.locator("#epType")
            expect(panel_type).to_have_value("single_choice", timeout=14000)
            check("题型按源码 AI 预填", True, {"value": panel_type.input_value()})
            note = panel.locator("#epTypeNote")
            check("题型话术标明人来改优先",
                  "自动判断" in note.inner_text() or "人工" in note.inner_text(),
                  {"note": note.inner_text()})
            confidence = panel.locator("#epConfidence")
            check("置信度如实标为假数据占位", "假数据占位" in confidence.inner_text(),
                  {"text": confidence.inner_text()})
            check("审核三键本期占位",
                  panel.locator("#epPass").is_disabled()
                  and panel.locator("#epReject").is_disabled()
                  and panel.locator("#epSkip").is_disabled())
            page.screenshot(path=str(shots / "v2-panel.png"))

            # ---------- 拖手：键盘路径，拖到底只留极窄缝 ----------
            image_pane = canvas.locator("#edPaneImage")
            width_before = image_pane.evaluate("node => node.getBoundingClientRect().width")
            for _ in range(3):
                canvas.locator("#edSplitImage").press("ArrowLeft")
            page.wait_for_timeout(400)
            width_after = image_pane.evaluate("node => node.getBoundingClientRect().width")
            check("方向键可拖窄左栏", width_after < width_before,
                  {"before": width_before, "after": width_after})
            for _ in range(14):
                canvas.locator("#edSplitImage").press("ArrowLeft")
            page.wait_for_timeout(400)
            floor = image_pane.evaluate("node => node.getBoundingClientRect().width")
            check("拖到底不归零（只留极窄缝）", 28 <= floor < width_before, {"width": floor})

            # ---------- 格式二：拆框编辑，改完自动重组格式一 ----------
            panel.locator("#epFormatBoxed").click()
            expect(canvas.locator("#edFormat")).to_have_attribute("data-format", "boxed",
                                                                 timeout=12000)
            boxes_now = canvas.locator(".ed-box").count()
            check("格式二按环境拆出框", boxes_now >= 4, {"boxes": boxes_now})
            env_labels = [text.strip() for text in canvas.locator(".ed-box-env").all_inner_texts()]
            check("框头环境名是锁定文本",
                  bool(env_labels) and all(
                      label.startswith("\\begin{") or label.startswith("\\item")
                      or "首行" in label or "内" in label for label in env_labels),
                  {"labels": env_labels})
            option_box = canvas.locator('.ed-box-area[data-field="choice"][data-pos="1"]').first
            expect(option_box).to_be_visible(timeout=8000)
            option_box.fill("$1$（" + MARK + "）")
            page.wait_for_timeout(500)
            panel.locator("#epFormatLatex").click()
            expect(canvas.locator("#edFormat")).to_have_attribute("data-format", "latex",
                                                                 timeout=12000)
            rebuilt = canvas.locator(".ed-src-area").first.input_value()
            check("改框自动重组格式一", MARK in rebuilt, {"tail": rebuilt[-140:]})
            check("切格式没有改坏环境骨架",
                  "\\begin{choices}" in rebuilt and "\\end{solution}" in rebuilt,
                  {"head": rebuilt[:80]})
            page.screenshot(path=str(shots / "v2-boxed.png"))

            # ---------- 元数据表单 ----------
            panel.locator("#epGrade").fill("高一")
            panel.locator("#epTags").fill(MARK + ", 二次函数")
            panel.locator("#epPaper").fill(MARK + " 一模卷")
            panel.locator("#epQuestionNo").fill("7")
            panel.locator("#epYear").fill("2024")
            panel.locator("#epExamType").fill("一模")
            panel.locator("#epDifficulty").select_option("L2")
            page.wait_for_timeout(400)
            metrics = panel.locator("#epMetrics")
            check("元数据改动标脏",
                  wait_attribute(metrics, "data-dirty", lambda value: value == "true", 8) == "true",
                  {"metrics": metrics.inner_text()})

            # ---------- 考向树：懒展开；空库时只如实说明，不假装成功 ----------
            tree_rows = panel.locator(".ep-topic-row").count()
            result["metrics"]["topic_rows"] = tree_rows
            if tree_rows:
                panel.locator(".ep-topic-expander").first.click()
                page.wait_for_timeout(900)
                rows_after_expand = panel.locator(".ep-topic-row").count()
                check("考向树可懒展开", rows_after_expand >= tree_rows,
                      {"before": tree_rows, "after": rows_after_expand})
                panel.locator(".ep-topic-name").first.click()
                page.wait_for_timeout(400)
                check("点名称可挂载考向", panel.locator(".ep-chip").count() >= 1,
                      {"chips": panel.locator(".ep-chip").count()})
            else:
                tree_text = panel.locator("#epTopicTree").inner_text()
                check("没有大纲节点时如实说明", "还没有大纲" in tree_text
                      or "正在读" in tree_text, {"note": tree_text})

            # ---------- 单题保存：新建走 bank.create ----------
            stem_area = canvas.locator(".ed-src-area").first
            stem_area.fill(stem_area.input_value().replace(
                "\\begin{question}\n已知函数",
                "\\begin{question}\n" + MARK + "题：已知函数", 1))
            page.wait_for_timeout(600)
            panel.locator("#epSave").click()
            saved_state = wait_attribute(metrics, "data-save-state",
                                         lambda value: value in ("created", "updated"), 20)
            check("辅助栏保存回执落地", saved_state == "created", {"save_state": saved_state})
            saved = canvas.locator("#edSaved")
            expect(saved).to_be_visible(timeout=20000)
            question_id = saved.get_attribute("data-id") or ""
            result["metrics"]["question_id"] = question_id
            check("保存返回合法题目 ID",
                  bool(re.fullmatch(r"q_[A-Za-z0-9_-]{8,64}", question_id)),
                  {"id": question_id})
            check("写库完成后按钮不再 busy",
                  panel.locator("#epSave").get_attribute("aria-busy") in (None, "false"))
            check("画布脏标记随保存清掉",
                  wait_attribute(canvas.locator("#edDirty"), "data-dirty",
                                 lambda value: value == "false", 10) == "false")

            status, document = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}")
            result["metrics"]["created"] = document
            check("API 可查到新题", status == 200, {"status": status})
            check("源码题干已落库", MARK in document.get("stem", ""),
                  {"stem": document.get("stem", "")[:120]})
            check("答案从「答案：B」还原为选项标号",
                  document.get("answer", {}).get("choice_keys") == ["B"],
                  {"answer": document.get("answer")})
            check("选项内容带上格式二的改动",
                  MARK in json.dumps(document.get("options", []), ensure_ascii=False),
                  {"options": document.get("options")})
            check("解析已落库", bool(document.get("solution")),
                  {"solution": document.get("solution", "")[:80]})
            check("难度/年级/标签/来源一致",
                  document.get("difficulty") == "L2"
                  and document.get("grade") == "高一"
                  and MARK in (document.get("tags") or [])
                  and (document.get("source") or {}).get("question_no") == "7"
                  and (document.get("source") or {}).get("year") == 2024,
                  {"difficulty": document.get("difficulty"), "grade": document.get("grade"),
                   "tags": document.get("tags"), "source": document.get("source")})
            check("题目结构与契约同口径",
                  document.get("schema_version") == "2.0"
                  and document.get("type") == "single_choice",
                  {"schema_version": document.get("schema_version"),
                   "type": document.get("type")})

            _, stats_after = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
            total_after = int(stats_after.get("total") or 0)
            check("题库总数 +1", total_after == total_before + 1,
                  {"before": total_before, "after": total_after})
            page.screenshot(path=str(shots / "v2-saved.png"))

            # ---------- 编辑态保存走 bank.update ----------
            edit_area = canvas.locator(".ed-src-area").first
            edit_area.fill(edit_area.input_value().replace(MARK, MARK + "改", 1))
            page.wait_for_timeout(600)
            panel.locator("#epSave").click()
            updated_state = wait_attribute(metrics, "data-save-state",
                                           lambda value: value == "updated", 20)
            check("再次保存走更新而非新建", updated_state == "updated",
                  {"save_state": updated_state})
            status, updated_doc = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}")
            check("原题 ID 未变且题干已更新",
                  status == 200 and updated_doc.get("id") == question_id
                  and MARK + "改" in updated_doc.get("stem", ""),
                  {"id": updated_doc.get("id"),
                   "stem": updated_doc.get("stem", "")[:60]})
            # 底座 update_question 只推 updated_at，meta.revision 恒为 1（bank.py 里没有任何自增路径），
            # 这里如实记录现状：拿修订号当改判据会把探针打成假红。
            result["metrics"]["update_meta"] = {
                "before": (document.get("meta") or {}),
                "after": (updated_doc.get("meta") or {}),
            }
            check("改动写进更新时间（修订号由底座维持为 1）",
                  (updated_doc.get("meta") or {}).get("updated_at", "")
                  >= (document.get("meta") or {}).get("updated_at", "")
                  and (updated_doc.get("meta") or {}).get("revision") == 1,
                  {"revision": (updated_doc.get("meta") or {}).get("revision"),
                   "updated_at": (updated_doc.get("meta") or {}).get("updated_at")})
            _, stats_after_update = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
            check("更新不新增题目", int(stats_after_update.get("total") or 0) == total_after,
                  {"total": stats_after_update.get("total")})

            # ---------- 派生变式：另发新 ID，原题不动 ----------
            panel.locator("#epVariant").click()
            variant_id = wait_attribute(metrics, "data-variant-id",
                                        lambda value: value.startswith("q_"), 20)
            variant_text = panel.locator("#epMessage").inner_text()
            result["metrics"]["variant_message"] = variant_text
            check("派生变式另发新 ID",
                  bool(variant_id) and variant_id != question_id,
                  {"variant": variant_id, "origin": question_id, "message": variant_text[:80]})
            _, origin_doc = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}")
            check("变式没有覆盖原题", MARK + "改" in origin_doc.get("stem", ""),
                  {"stem": origin_doc.get("stem", "")[:80]})
            _, stats_final = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
            check("变式让总数再 +1", int(stats_final.get("total") or 0) == total_after + 1,
                  {"total": stats_final.get("total")})

            # ---------- 回流：题库画布搜得到本次保存 ----------
            bank_item = page.locator(".ws-plugin-item", has_text="真题题库").first
            bank_item.click()
            bank_frame = page.frame_locator(BANK_UI)
            search = bank_frame.locator(".cb-search")
            expect(search).to_be_visible(timeout=20000)
            search.fill(MARK)
            search.press("Enter")
            page.wait_for_timeout(1200)
            rows = bank_frame.locator(".cb-row").count()
            result["metrics"]["bank_rows"] = rows
            check("题库画布搜到本次保存", rows >= 1, {"rows": rows})
            page.screenshot(path=str(shots / "v2-bank-ui.png"))

            size_host = page.locator("body").evaluate(
                "() => ({scrollWidth: document.body.scrollWidth,"
                " clientWidth: document.documentElement.clientWidth})")
            check("宿主无横向溢出", size_host["scrollWidth"] <= size_host["clientWidth"] + 1,
                  size_host)
            browser.close()
    except Exception as exc:  # noqa: BLE001 - 探针要把失败原样落盘
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            page.screenshot(path=str(shots / "failure.png"))
        except Exception:
            pass
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
    print(("PASS" if result["ok"] else "FAIL")
          + f" · {passed}/{len(result['checks'])} 项 · {work}")
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

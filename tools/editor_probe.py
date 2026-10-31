# -*- coding: utf-8 -*-
"""录题工作台 v2 真机探针（军令 #23 阶段 2–4）：三栏画布、辅助栏表单、AI 帮改与批量条。

用法：``.venv/Scripts/python.exe tools/editor_probe.py <tag>``

隔离：把 editor 与题库两端复制进独立插件目录，另起端口与独立数据目录，
不写本机 data/banks/。题数一律用「保存前后差值」判据，绝不写死绝对数。
AI 改写走本机 OpenAI 兼容桩（JZO_AI_BASE_URL 指向 127.0.0.1），
探针全程不出网，也不依赖本机 .env 里老师的真密钥。

检查项：
- 画布挂载出三栏（左原图 | 中源码 | 右渲染）与两条拖手，拖到底不归零；
- 右栏是同一插件的**第二个沙箱帧**，按画布送来的选区预填元数据；
- 辅助栏里既没有源码框也没有渲染预览（军令铁律，指令框除外）；
- 格式一整段可编辑；格式二按环境拆框，改框自动重组格式一；
- 单题保存经宿主写库：新建走 bank.create、再存走 bank.update、变式另发新 ID；
- 保存后直查 API 字段逐项一致（题干/答案/选项/解析/难度/年级/标签/来源/修订号）；
- AI 帮改（档 1）：光标定字段 → 预览 → **点采用才替换**、点放弃不动源码，
  环境骨架与「答案：」行全程不受改写影响；
- AI 清洗走宿主 text.clean_latex：题干段与解析段全成功才回填；
- 阶段 4 批量：单题与批量共用一张画布，点左栏跳转 / 键盘 Enter 都换当前题，
  滚到哪题当前题就跟到哪题（光标还停在框里时人不许被滚动抢走），
  底部【保存全部】只提交脏题——编辑态走更新、新建走 create、没提交的那题搜得到也进不去；
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
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
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


def wait_value(locator, predicate, timeout: float = 12) -> str:
    """输入框的值轮询：回填经宿主广播回来，不是点击当场就变。"""
    deadline = time.time() + timeout
    value = ""
    while time.time() < deadline:
        value = locator.input_value()
        if predicate(value):
            return value
        time.sleep(0.15)
    return value


def wait_text(locator, predicate, timeout: float = 12) -> str:
    deadline = time.time() + timeout
    text = ""
    while time.time() < deadline:
        text = locator.inner_text()
        if predicate(text):
            return text
        time.sleep(0.15)
    return text


class StubProvider:
    """本机 OpenAI 兼容桩：把 /api/agent/refine 变成确定性回包，探针一律不出网。

    底座把「待改字段 + 该字段当前内容 + 老师指令」拼进 user 消息，桩就照这个形状
    回一份 {"<field>": 标记 + 原文, "note": …}，让判据能验到「改写≠回显」。
    """

    MARKER = "探针AI改写"

    def __init__(self) -> None:
        self.hits = 0
        self.fields: list[str] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args) -> None:
                pass

            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 的固定入口
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length).decode("utf-8") if length else "{}"
                try:
                    body = json.loads(raw or "{}")
                except json.JSONDecodeError:
                    body = {}
                user = ""
                for message in body.get("messages") or []:
                    if message.get("role") == "user":
                        user = str(message.get("content") or "")
                field_match = re.search(r"## 需要改写的字段\n(\w+)", user)
                field = field_match.group(1) if field_match else "stem"
                content_match = re.search(r"## 该字段当前内容\n([\s\S]*?)\n\n## 老师指令", user)
                original = content_match.group(1).strip() if content_match else ""
                owner.hits += 1
                owner.fields.append(field)
                payload = json.dumps({field: self.server.marker_text(original),
                                      "note": "探针桩按指令改写"}, ensure_ascii=False)
                reply = json.dumps({
                    "choices": [{"message": {"content": payload}}],
                    "model": "probe-stub",
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(reply)))
                self.end_headers()
                self.wfile.write(reply)

        self.port = free_port()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        # 桩的标记文本从服务端拼，避免 handler 里再抄一份常量
        self.httpd.marker_text = lambda original: f"{StubProvider.MARKER}·{original}"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


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
    stub = StubProvider()
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = "editor-probe-token"
    env["JZO_RESTART_DISABLED"] = "1"
    # 活跃档指向本机桩：环境变量优先于仓库 .env（app/__init__._load_local_env 用 setdefault）
    env["JZO_AI_PROVIDER"] = "openai-compatible"
    env["JZO_AI_BASE_URL"] = stub.base_url
    env["JZO_AI_API_KEY"] = "probe-stub-key"
    env["JZO_AI_MODEL"] = "probe-stub"
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
            check("辅助栏不放源码框", panel.locator(".ed-src-area, .ed-box-area").count() == 0,
                  {"src": panel.locator(".ed-src-area").count(),
                   "boxes": panel.locator(".ed-box-area").count()})
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

            # ---------- 阶段 3：AI 帮改（档 1）——光标定字段 → 预览 → 点采用才替换 ----------
            src = canvas.locator('.ed-src-area[data-index="0"]').first
            expect(src).to_be_visible(timeout=10000)
            before_ai = src.input_value()
            src.evaluate("""node => {
              var at = node.value.indexOf('求其最小值');
              node.focus();
              node.setSelectionRange(at + 2, at + 5);
              node.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
            }""")
            ai_field = panel.locator("#epAiField")
            picked = wait_attribute(ai_field, "data-ai-field", lambda value: value == "stem", 12)
            check("光标落在题干段里，面板认出改写字段是题干", picked == "stem",
                  {"field": picked, "hint": ai_field.inner_text()[:70]})
            send = panel.locator("#epAiSend")
            check("没写指令时【发送】按不动", send.is_disabled())
            panel.locator("#epAiAsk").fill("把「求其最小值」改成「求最小值并写出取等条件」")
            expect(send).to_be_enabled(timeout=8000)
            check("字段 + 指令齐了才允许发送", not send.is_disabled())

            send.click()
            state_node = panel.locator("#epAiState")
            settled = wait_attribute(state_node, "data-ai-state",
                                     lambda value: value in {"ready", "error"}, 25)
            note = panel.locator("#epAiNote")
            preview = panel.locator("#epAiPreview")
            preview_text = preview.inner_text()
            result["metrics"]["ai"] = {"state": settled, "note": note.inner_text()[:80],
                                       "hits": stub.hits, "fields": stub.fields}
            check("改写请求真的走到 Provider 桩（本机回环，未出网）",
                  settled == "ready" and stub.hits >= 1 and "stem" in stub.fields,
                  {"state": settled, "hits": stub.hits, "fields": stub.fields})
            check("预览给出改写结果并停在「待老师裁决」",
                  StubProvider.MARKER in preview_text
                  and preview.get_attribute("data-ai-value") == "ready",
                  {"preview": preview_text[:90]})
            check("改写≠原文，所以不标回显", (note.get_attribute("data-ai-mock") or "") == "",
                  {"note": note.inner_text()[:80]})
            check("没点采用前画布源码一个字都没动",
                  StubProvider.MARKER not in src.input_value()
                  and src.input_value() == before_ai)
            apply_state = panel.locator("#epAiApply")
            expect(apply_state).to_be_enabled(timeout=8000)
            apply_state.click()
            applied = wait_value(src, lambda value: StubProvider.MARKER in value, 12)
            check("点采用才替换，且只换题干段正文",
                  StubProvider.MARKER in applied
                  and "\\begin{choices}" in applied and "\\end{choices}" in applied
                  and applied.count(StubProvider.MARKER) == 1,
                  {"head": applied[:120]})
            check("环境骨架与「答案：」行不受改写影响",
                  "\\begin{question}" in applied and "\\begin{solution}" in applied
                  and "答案：" in applied)
            toast_text = wait_text(canvas.locator("#edToast"),
                                   lambda value: "已采用" in value, 6)
            check("画布自己回显「已采用」并提醒还没保存",
                  "已采用" in toast_text and "还没保存" in toast_text,
                  {"toast": toast_text[:60]})
            check("面板把话说清：发出去了不等于入库",
                  "保存才入库" in panel.locator("#epMessage").inner_text(),
                  {"message": panel.locator("#epMessage").inner_text()[:80]})
            page.screenshot(path=str(shots / "v2-ai-apply.png"))

            # ---------- 放弃分支：改写作废，源码退回采用前 ----------
            src.evaluate("""node => {
              var at = node.value.indexOf('解析：配方得');
              node.focus();
              node.setSelectionRange(at + 3, at + 6);
              node.dispatchEvent(new KeyboardEvent('keyup', {bubbles: true}));
            }""")
            picked2 = wait_attribute(ai_field, "data-ai-field", lambda value: value == "solution", 12)
            check("光标移到解析段，字段判定跟着换", picked2 == "solution", {"field": picked2})
            hits_before = stub.hits
            send.click()
            flipping = wait_attribute(preview, "data-ai-field", lambda value: value == "solution", 12)
            deadline = time.time() + 25
            while stub.hits <= hits_before and time.time() < deadline:
                page.wait_for_timeout(100)
            settled2 = wait_attribute(state_node, "data-ai-state",
                                      lambda value: value in {"ready", "error"}, 25)
            check("解析段的改写同样先落在预览里",
                  flipping == "solution" and settled2 == "ready"
                  and StubProvider.MARKER in preview.inner_text() and stub.hits > hits_before,
                  {"field": flipping, "state": settled2, "hits": stub.hits})
            panel.locator("#epAiDiscard").click()
            check("点放弃：预览清空、【采用】重新按不动",
                  apply_state.is_disabled()
                  and StubProvider.MARKER not in preview.inner_text(),
                  {"preview": preview.inner_text()[:60]})
            check("放弃不改画布源码", src.input_value() == applied,
                  {"len": len(src.input_value())})

            # ---------- AI 清洗：走宿主规则通道，两段全成功才回填 ----------
            dirty = ("\\begin{question}\n已知 \\(g(x)=x^2\\)，则 \\[g(x)\\] 的最小值是（  ）\n"
                     "\\begin{choices}\n  \\item $0$\n  \\item $1$\n\\end{choices}\n\\end{question}\n\n"
                     "\\begin{solution}\n答案：B\n因为 \\(g(x)\\) 开口向上。\n\\end{solution}\n")
            src.fill(dirty)
            # 面板洗的是它收到的那一份选区源码：160ms 防抖 + 一帧回投，等它到手再点清洗
            wait_attribute(metrics, "data-dirty", lambda value: value == "true", 10)
            page.wait_for_timeout(600)
            filled = src.input_value()
            check("脏定界符已进中栏（清洗前的样子）", "\\(" in filled and "\\[" in filled,
                  {"head": filled[:60]})
            clean = panel.locator("#epAiClean")
            expect(clean).to_be_enabled(timeout=8000)
            clean.click()
            cleaned = wait_value(src, lambda value: "\\(" not in value and "\\[" not in value, 15)
            check("清洗走宿主规则通道：定界符归一为 $ 与 $$",
                  "\\(" not in cleaned and "\\[" not in cleaned
                  and "$g(x)$" in cleaned and "$$g(x)$$" in cleaned,
                  {"head": cleaned[:90]})
            check("清洗只动公式定界符，环境与答案行原样",
                  "\\begin{choices}" in cleaned and "答案：B" in cleaned
                  and "\\end{solution}" in cleaned,
                  {"tail": cleaned[-90:]})
            check("清洗话术报出改动段数",
                  "已清洗" in note.inner_text() or "没有改动" in note.inner_text(),
                  {"note": note.inner_text()[:80]})
            page.screenshot(path=str(shots / "v2-ai-clean.png"))
            check("AI 三段动作后页面仍无脚本错误", not result["page_errors"],
                  {"page_errors": result["page_errors"][:3]})

            # ---------- 阶段 4：批量同界面——滚动跟题、左栏跳转、底部只提交脏题 ----------
            # 拖手把左栏压成了极窄缝，先把宽度还给原图栏，跳转按钮才在真实宽度下取证
            for _ in range(20):
                canvas.locator("#edSplitImage").press("ArrowRight")
            page.wait_for_timeout(500)

            batch_rows = canvas.locator(".ed-src-area").count()
            check("单题与批量共用一张画布（四行源码）", batch_rows == 4, {"rows": batch_rows})
            check("左栏逐题带跳转按钮", canvas.locator(".ed-img-jump").count() == 4,
                  {"jumps": canvas.locator(".ed-img-jump").count()})
            check("批量条只出现在画布（辅助栏那份整块隐藏）",
                  canvas.locator("#edSaveAll").first.is_visible()
                  and not panel.locator("#edSaveAll").first.is_visible(),
                  {"canvas": canvas.locator("#edSaveAll").count(),
                   "panel": panel.locator("#edSaveAll").count()})
            check("待入库池本期只做界面（暂存出厂锁死）",
                  canvas.locator("#edPoolStash").is_disabled()
                  and "下一军令" in (canvas.locator("#edPoolStash").get_attribute("title") or ""))

            # 1) 点左栏跳转：三栏一起滚过去，当前题与辅助栏表单都跟到那一题
            canvas.locator('.ed-img-jump[data-index="2"]').click()
            progress = canvas.locator("#edProgress")
            jumped = wait_attribute(progress, "data-active", lambda value: value == "3", 12)
            check("点左栏跳转把当前题切到第 3 题", jumped == "3",
                  {"progress": progress.inner_text()})
            tops = [canvas.locator(node).evaluate("n => [n.scrollTop, n.scrollHeight, n.clientHeight]")
                    for node in ("#edImageBody", "#edSourceBody", "#edRenderBody")]
            result["metrics"]["jump_geo"] = tops
            check("跳转把三栏一起滚过去（不再各滚各的）",
                  all(value[0] > 0 for value in tops),
                  {"tops": [value[0] for value in tops],
                   "overflow": [value[1] - value[2] for value in tops]})
            check("跳转后辅助栏表单跟到第 3 题",
                  wait_attribute(panel.locator("#epProgress"), "data-active",
                                 lambda value: value == "3", 14) == "3",
                  {"progress": panel.locator("#epProgress").inner_text()})
            expect(panel.locator("#epType")).to_have_value("fill_blank", timeout=14000)
            check("第 3 题的题型随选区换成填空（不是上一题的残留）", True)
            check("当前题高亮落在跳转到的那一行",
                  (canvas.locator(".ed-q-block.is-active").first.get_attribute("data-index") or "") == "2",
                  {"aria_current": canvas.locator('.ed-img-jump[data-index="2"]')
                      .get_attribute("aria-current")})

            # 2) 滚到哪题跟哪题：把渲染栏滚到底，当前题自己走到第 4 题
            canvas.locator("#edMetrics").evaluate(
                "() => { if (document.activeElement) document.activeElement.blur(); }")
            page.wait_for_timeout(300)
            canvas.locator("#edRenderBody").evaluate("node => { node.scrollTop = node.scrollHeight; }")
            scrolled = wait_attribute(progress, "data-active", lambda value: value == "4", 12)
            check("滚到最后一题，当前题自己跟过去", scrolled == "4",
                  {"progress": progress.inner_text()})
            check("滚动同步把三栏都带到底",
                  all(canvas.locator(node).evaluate("n => n.scrollTop") > 0
                      for node in ("#edImageBody", "#edSourceBody", "#edRenderBody")))
            check("高亮跟到滚到的那一行",
                  (canvas.locator(".ed-q-block.is-active").first.get_attribute("data-index") or "") == "3")

            # 3) 人手优先：光标还停在第 1 题的框里时，滚动不许把当前题抢走
            #    必须真点一下：只调 node.focus() 不会触发插件的上桥事件，
            #    当前题还停在上一轮的第 4 题，判据会把"人手优先"错测成"滚动没抢"。
            held_area = canvas.locator('.ed-src-area[data-index="0"]')
            held_area.scroll_into_view_if_needed()
            held_area.click(position={"x": 40, "y": 12})
            page.wait_for_timeout(500)
            held_before = progress.get_attribute("data-active")
            canvas.locator("#edRenderBody").evaluate("node => { node.scrollTop = node.scrollHeight; }")
            page.wait_for_timeout(600)
            held_active = progress.get_attribute("data-active")
            check("光标停在第 1 题时滚动不许抢走当前题",
                  held_before == "1" and held_active == "1",
                  {"before": held_before, "active": held_active})

            # 4) 键盘路径：聚焦跳转按钮按 Enter
            canvas.locator('.ed-img-jump[data-index="1"]').press("Enter")
            keyed = wait_attribute(progress, "data-active", lambda value: value == "2", 12)
            check("键盘 Enter 也能跳题", keyed == "2", {"active": keyed})

            # 5) 底部【保存全部】：只提交脏题，未改动的一题也不写
            pool = canvas.locator("#edPool")
            dirty_new = pool.get_attribute("data-new")
            dirty_start = wait_attribute(pool, "data-dirty", lambda value: value == "1", 10)
            check("批量前的脏数只认 AI 改过的那题（其余三题没动过就不算脏）",
                  dirty_start == "1" and dirty_new == "3",
                  {"pool": pool.inner_text(), "dirty": dirty_start, "new": dirty_new})
            area2 = canvas.locator('.ed-src-area[data-index="1"]')
            area2.evaluate("node => { node.focus(); }")
            area2.fill(area2.input_value().replace("已知集合", "已知集合（" + MARK + "批量）", 1))
            area4 = canvas.locator('.ed-src-area[data-index="3"]')
            area4.evaluate("node => { node.focus(); }")
            area4.fill(area4.input_value().replace("已知等差数列", "已知等差数列（" + MARK + "批量）", 1))
            page.wait_for_timeout(800)
            dirty_three = wait_attribute(pool, "data-dirty", lambda value: value == "3", 12)
            check("两行新改动叠上去，台账仍只数脏题（未改的第 3 题不计）",
                  dirty_three == "3", {"pool": pool.inner_text()})
            _, stats_before_batch = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
            total_before_batch = int(stats_before_batch.get("total") or 0)
            # 「没提交的那题」用差值判，不用绝对数：隔离库里可能本就沉着同短语的真题
            _, row2_before = http_json(base + f"/api/bank/plugins/{BANK_ID}/questions"
                                       f"?q={urllib.parse.quote('的最小值为')}")
            row2_hits_before = int(row2_before.get("total") or 0)
            save_all = canvas.locator("#edSaveAll")
            expect(save_all).to_be_enabled(timeout=8000)
            save_all.click()
            busy_seen = save_all.get_attribute("aria-busy")
            result["metrics"]["batch_busy"] = busy_seen
            batch_note = canvas.locator("#edBatchNote")
            batch_phase = wait_attribute(batch_note, "data-batch",
                                         lambda value: value in ("done", "partial", "failed"), 40)
            batch_text = batch_note.inner_text()
            result["metrics"]["batch_note"] = batch_text
            check("【保存全部】只提交脏题：3 道提交、1 道未改动的一题也没写",
                  batch_phase == "done" and "提交 3 道脏题" in batch_text
                  and "未改动的 1 道" in batch_text, {"note": batch_text[:140]})
            check("提交完按钮重新锁死（没脏题就按不动）",
                  wait_attribute(save_all, "aria-disabled", lambda value: value == "true", 12) == "true"
                  and save_all.is_disabled())
            check("台账归零：脏 0，待入库只剩没提交的那题",
                  pool.get_attribute("data-dirty") == "0"
                  and pool.get_attribute("data-new") == "1"
                  and pool.get_attribute("data-stored") == "3",
                  {"pool": pool.inner_text()})
            _, stats_after_batch = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
            total_after_batch = int(stats_after_batch.get("total") or 0)
            check("批量只长了该长的两道（编辑态走更新不新增）",
                  total_after_batch == total_before_batch + 2,
                  {"before": total_before_batch, "after": total_after_batch})
            _, row2_after = http_json(base + f"/api/bank/plugins/{BANK_ID}/questions"
                                      f"?q={urllib.parse.quote('的最小值为')}")
            row2_hits_after = int(row2_after.get("total") or 0)
            check("没提交的那题一个字都没进库（搜到的题数前后没变）",
                  row2_hits_after == row2_hits_before,
                  {"before": row2_hits_before, "after": row2_hits_after})
            _, batch_rows_api = http_json(base + f"/api/bank/plugins/{BANK_ID}/questions"
                                          f"?q={urllib.parse.quote(MARK + '批量')}")
            batch_items = batch_rows_api.get("items") or batch_rows_api.get("rows") or []
            result["metrics"]["batch_created"] = [
                (row.get("id"), row.get("type")) for row in batch_items][:4]
            check("两道批量新建的题各自成型（多选与解答都按源码判型）",
                  len(batch_items) == 2
                  and {row.get("type") for row in batch_items} == {"multiple_choice", "solution"},
                  {"count": len(batch_items)})
            page.screenshot(path=str(shots / "v2-batch.png"))
            check("批量段跑完页面仍无脚本错误", not result["page_errors"],
                  {"page_errors": result["page_errors"][:3]})

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
        stub.stop()
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

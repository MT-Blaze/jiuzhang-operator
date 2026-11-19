# -*- coding: utf-8 -*-
"""配置中心画布内联展开真机探针（回执 #CV-01）。

用法：``.venv/Scripts/python.exe tools/canvas_inline_config_probe.py [tag]``

隔离：独立 JZO_DATA_DIR / JZO_PLUGINS_DIR 副本＋动态空闲端口＋每次随机令牌，
不碰用户 data/ 与正式服务；收口点杀进程并复验端口关闭。
产物落 .system_generated/canvas-inline-config/<tag>/（probe.toml＋shots）。

判据（只验本卡契约，不真装 MinerU、不跑推理）：
1. 模型/API 配置点开是画布内联视图：无 .ep-modal 遮罩、无 aria-modal、非 fixed 定位，
   批次列表期间隐藏，#edRoot data-mode 切到配置屏；
2. 打开焦点落标题；Esc 不再关配置视图；Tab 在视图内全控件可达；
3. 停用/改默认经 relay 落隔离插件目录 model_prefs.toml，data/ 全树无此文件；
4. 【返回批次】还原先前屏＋滚动位置＋触发按钮焦点；辅助栏常驻 API 入口同钮再点＝收
   （模型入口住批次屏头部，随批次屏隐藏，收只走【返回批次】——卡片「批次期间隐藏」的必然结果）；
5. 模型视图【去 API 配置指派】跳 API 视图后返回仍落批次屏（记账不被覆盖）；
6. 辅助栏入口开视图，返回焦点落画布入口（跨帧焦点还原的兜底口径）；
7. 375px 不横向溢出、双栏折单栏、表单控件与迷你钮命中区 ≥44px；
8. 零 JS 异常、零 HTTP 失败、三查=0。

批次用 POST /api/pending/batches 真口种 24 批（隔离库），让列表滚得动，
滚动位置还原才有非零判据；种批次走宿主写口，不算仪表改动。
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
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
EDITOR_ID = "org.jiuzhang.editor"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
PANEL = "#wsContextSlot .ws-context-frame"


def _doc(no: int) -> dict:
    return {
        "schema_version": "2.0", "type": "single_choice",
        "stem": "探针内联卷第 %d 题：$x+%d=%d$ 的解是（  ）" % (no, no, no + 1),
        "options": [{"key": "A", "content": "$1$"}, {"key": "B", "content": "$2$"}],
        "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
        "solution": "解析：移项即得。", "difficulty": "L1", "grade": "高一",
        "tags": ["探针内联"],
        "source": {"paper_title": "探针内联卷", "question_no": str(no),
                   "year": 2026, "exam_type": "一模"},
    }


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        if process.poll() is not None:
            output = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
            raise RuntimeError("服务提前退出：\n" + output[:3000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 40 秒内就绪")


def http_json(base: str, path: str, payload: dict | None = None,
              token: str | None = None) -> tuple[int, dict]:
    import json
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-JZO-Token"] = token
    request = urllib.request.Request(
        base + path, data=body, method="POST" if payload is not None else "GET",
        headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, json.loads(raw or "{}")
        except ValueError:
            return error.code, {"raw": raw}


VIEW_SHAPE = """(node, id) => {
  var view = document.getElementById(id);
  var cs = getComputedStyle(view);
  var overlays = Array.from(document.querySelectorAll('.ep-modal')).filter(
    function (n) { return !n.hidden && getComputedStyle(n).display !== 'none'; });
  return {position: cs.position, inModal: !!view.closest('.ep-modal'),
          ariaModal: view.getAttribute('aria-modal'), role: view.getAttribute('role'),
          overlays: overlays.length,
          batchesHidden: document.getElementById('edBatches').hidden,
          mode: document.getElementById('edRoot').getAttribute('data-mode')};
}"""


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    token = "probe-" + secrets.token_hex(8)
    work = ROOT / ".system_generated" / "canvas-inline-config" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir, shots = work / "data", work / "plugins", work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    plugin_dir = plugins_dir / EDITOR_ID
    shutil.copytree(PLUGIN_SOURCE_DIR / EDITOR_ID, plugin_dir)
    shutil.rmtree(plugin_dir / "models", ignore_errors=True)

    # 造一份「已下载」的满血版权重（隔离副本内），让 YOLO 就绪可供停用/下拉动证。
    config = toml_io.load(plugin_dir / "model_config.toml", {})
    full = (config.get("models") or {}).get("full") or {}
    min_bytes = int(full.get("min_bytes") or full.get("size_bytes") or 70000000)
    models_dir = plugin_dir / "models"
    models_dir.mkdir(exist_ok=True)
    (models_dir / str(full.get("filename") or "doclayout_yolo_full_v1.0.onnx")).write_bytes(
        b"0" * (min_bytes + 1))

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = token
    env["JZO_RESTART_DISABLED"] = "1"
    env["JZO_POOL_ADMIT_DISABLED"] = "1"
    server_log = work / "server.log"
    handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)

    result: dict = {"tag": tag, "base": base, "viewport": "1440x900",
                    "checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    prefs_file = plugin_dir / "model_prefs.toml"
    try:
        wait_health(base, process, server_log)
        seeded = 0
        for no in range(1, 25):
            code, _ = http_json(base, "/api/pending/batches",
                                {"questions": [{"question": _doc(no)}],
                                 "source_name": "探针内联卷%d.pdf" % no,
                                 "origin": "probe.inline"}, token=token)
            seeded += 1 if code == 201 else 0
        check("宿主写口种 24 批（滚动还原的非零判据）", seeded == 24, {"seeded": seeded})

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url)) if response.status >= 400 else None)
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            panel = page.frame_locator(PANEL)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            expect(canvas.locator(".ed-batch-row").first).to_be_visible(timeout=20000)
            check("批次列表 24 行上屏", canvas.locator(".ed-batch-row").count() == 24)

            # ---------- 滚一段批次列表，记下滚动位置供返回还原比对 ----------
            list_box = canvas.locator("#edBatchList").bounding_box()
            page.mouse.move(list_box["x"] + list_box["width"] / 2,
                            list_box["y"] + min(120.0, list_box["height"] / 2))
            page.mouse.wheel(0, 400)
            page.wait_for_timeout(300)
            scrolls_before = canvas.locator("#edRoot").evaluate(
                """() => [document.getElementById('edBatches'),
                          document.getElementById('edBatchList').parentNode]
                         .map(n => n.scrollTop)""")
            check("批次列表真的滚起来了（非零）", max(scrolls_before) > 0,
                  {"scrollTop": scrolls_before})
            page.screenshot(path=str(shots / "01-batches-scrolled.png"))

            # ---------- 模型配置：内联视图形状 ----------
            canvas.locator("#epModelConfigList").click()
            view = canvas.locator("#edModelConfigModal")
            expect(view).to_be_visible(timeout=10000)
            expect(canvas.locator(".ep-mt-row").first).to_be_visible(timeout=15000)
            shape = canvas.locator("#edRoot").evaluate(VIEW_SHAPE, "edModelConfigModal")
            check("模型配置无遮罩/无 aria-modal/非 fixed/批次隐藏",
                  shape["overlays"] == 0 and not shape["inModal"]
                  and shape["ariaModal"] is None and shape["position"] != "fixed"
                  and shape["batchesHidden"] and shape["mode"] == "model_config", shape)
            focused = canvas.locator("#edModelConfigTitle").evaluate(
                "node => node === document.activeElement")
            check("打开焦点落视图标题", bool(focused))
            page.screenshot(path=str(shots / "02-model-config-inline.png"))

            # ---------- Esc 不关配置视图（真模态才吃 Esc） ----------
            page.keyboard.press("Escape")
            page.wait_for_timeout(200)
            check("Esc 不再关模型配置视图", view.is_visible()
                  and canvas.locator("#edRoot").get_attribute("data-mode") == "model_config")

            # ---------- Tab 全控件可达（无焦点陷阱，但走得出标题进得了控件） ----------
            seen = []
            for _ in range(10):
                page.keyboard.press("Tab")
                info = canvas.locator("#edRoot").evaluate(
                    """() => { var a = document.activeElement;
                         var v = document.getElementById('edModelConfigModal');
                         return {inside: v.contains(a), tag: a.tagName,
                                 cls: a.className || ''}; }""")
                seen.append(info)
            check("Tab 十步全在视图内且摸到钮与下拉",
                  all(s["inside"] for s in seen)
                  and any(s["tag"] == "BUTTON" for s in seen)
                  and any(s["tag"] == "SELECT" for s in seen), seen[:10])

            # ---------- 键盘改默认选择：落隔离插件目录 ----------
            layout_select = canvas.locator(
                ".ep-model-config-defaults:not(.ep-model-config-auto-seats) "
                ".ep-model-config-default-select").first
            expected_default = layout_select.evaluate("node => node.options[1].value")
            layout_select.click()
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            deadline = time.time() + 15
            picked = ""
            while time.time() < deadline:
                picked = str(toml_io.load(prefs_file, {}).get("default_layout") or "")
                if picked and picked != "auto":
                    break
                page.wait_for_timeout(300)
            check("键盘改默认落插件目录", picked == expected_default,
                  {"default_layout": picked, "expected": expected_default})

            # ---------- 停用 YOLO：下拉不显示＋状态住插件目录 ----------
            engine = canvas.locator("#edLayoutEngine")
            yolo_row = canvas.locator(".ep-mt-row", has_text="YOLO·版面")
            yolo_row.locator(".ep-mt-toggle").click()
            expect(engine.locator('option[value="yolo"]')).to_have_count(0, timeout=15000)
            prefs = toml_io.load(prefs_file, {})
            check("UI 停用经 relay 落插件目录", "yolo" in prefs.get("disabled", []),
                  {"prefs": prefs})
            check("data/ 全树无 model_prefs.toml",
                  not list(data_dir.rglob("model_prefs.toml")))
            page.screenshot(path=str(shots / "03-model-disabled.png"))

            # ---------- 返回批次：屏/滚动/焦点三还原 ----------
            canvas.locator("#edModelConfigBack").click()
            expect(view).to_be_hidden(timeout=5000)
            expect(canvas.locator("#edBatches")).to_be_visible(timeout=5000)
            scrolls_after = canvas.locator("#edRoot").evaluate(
                """() => [document.getElementById('edBatches'),
                          document.getElementById('edBatchList').parentNode]
                         .map(n => n.scrollTop)""")
            restored = canvas.locator("#epModelConfigList").evaluate(
                "node => node === document.activeElement")
            check("返回还原批次屏＋滚动位置＋入口焦点",
                  scrolls_after == scrolls_before and bool(restored)
                  and canvas.locator("#edRoot").get_attribute("data-mode") == "list",
                  {"before": scrolls_before, "after": scrolls_after, "focus": bool(restored)})
            page.screenshot(path=str(shots / "04-batches-restored.png"))

            # ---------- 重开启用恢复；模型入口住批次屏头部随屏隐藏，收走【返回批次】 ----------
            canvas.locator("#epModelConfigList").click()
            expect(view).to_be_visible(timeout=10000)
            yolo_row.locator(".ep-mt-toggle").click()
            expect(engine.locator('option[value="yolo"]')).to_have_count(1, timeout=15000)
            canvas.locator("#edModelConfigBack").click()
            expect(view).to_be_hidden(timeout=5000)
            check("重开启用恢复下拉＋返回收视图",
                  canvas.locator("#edRoot").get_attribute("data-mode") == "list")

            # ---------- 模型→API 跳转：返回仍落批次屏 ----------
            canvas.locator("#epModelConfigList").click()
            expect(view).to_be_visible(timeout=10000)
            assign = canvas.locator(".ep-mt-act", has_text="去 API 配置").first
            expect(assign).to_be_visible(timeout=10000)
            assign.click()
            ai_view = canvas.locator("#epAiConfigModal")
            expect(ai_view).to_be_visible(timeout=10000)
            expect(view).to_be_hidden(timeout=5000)
            shape = canvas.locator("#edRoot").evaluate(VIEW_SHAPE, "epAiConfigModal")
            check("指派跳转互斥切 API 视图（同样无遮罩）",
                  shape["overlays"] == 0 and not shape["inModal"]
                  and shape["ariaModal"] is None and shape["position"] != "fixed"
                  and shape["mode"] == "ai_config", shape)
            canvas.locator("#epAiConfigBack").click()
            expect(canvas.locator("#edBatches")).to_be_visible(timeout=5000)
            check("跨视图返回仍落批次屏（记账不被覆盖）",
                  canvas.locator("#edRoot").get_attribute("data-mode") == "list"
                  and ai_view.is_hidden())

            # ---------- API 配置：画布入口直达＋焦点落标题 ----------
            canvas.locator("#epAiConfigList").click()
            expect(ai_view).to_be_visible(timeout=10000)
            expect(canvas.locator("#epAiConfigMsg")).to_be_visible(timeout=10000)
            page.wait_for_timeout(800)
            focused = canvas.locator("#epAiConfigTitle").evaluate(
                "node => node === document.activeElement")
            shape = canvas.locator("#edRoot").evaluate(VIEW_SHAPE, "epAiConfigModal")
            check("API 配置内联展开＋焦点落标题",
                  bool(focused) and shape["overlays"] == 0 and not shape["inModal"]
                  and shape["batchesHidden"] and shape["mode"] == "ai_config", shape)
            page.screenshot(path=str(shots / "05-api-config-inline.png"))
            canvas.locator("#epAiConfigBack").click()
            expect(ai_view).to_be_hidden(timeout=5000)

            # ---------- 辅助栏常驻入口：同钮再点收＋开视图返回焦点兜底 ----------
            panel.locator("#epAiConfig").click()
            expect(ai_view).to_be_visible(timeout=10000)
            panel.locator("#epAiConfig").click()
            expect(ai_view).to_be_hidden(timeout=5000)
            check("辅助栏同入口再点收视图",
                  canvas.locator("#edRoot").get_attribute("data-mode") == "list")
            panel.locator("#epAiConfig").click()
            expect(ai_view).to_be_visible(timeout=10000)
            canvas.locator("#epAiConfigBack").click()
            expect(ai_view).to_be_hidden(timeout=5000)
            fallback = canvas.locator("#epAiConfigList").evaluate(
                "node => node === document.activeElement")
            check("辅助栏开视图返回焦点兜底落画布入口", bool(fallback))

            # ---------- 375px：不溢出＋双栏折单栏＋触控 ≥44px ----------
            page.set_viewport_size({"width": 375, "height": 720})
            canvas.locator("#epModelConfigList").click()
            expect(view).to_be_visible(timeout=10000)
            overflow = canvas.locator("#edRoot").evaluate(
                """() => { var v = document.getElementById('edModelConfigModal');
                     return Math.max(v.scrollWidth - v.clientWidth,
                       document.querySelector('.ep-model-config-card').scrollWidth
                       - document.querySelector('.ep-model-config-card').clientWidth); }""")
            check("375px 模型视图不横向溢出", overflow <= 0, {"overflow_px": overflow})
            page.screenshot(path=str(shots / "06-mobile-375-model.png"))
            canvas.locator("#edModelConfigBack").click()
            canvas.locator("#epAiConfigList").click()
            expect(ai_view).to_be_visible(timeout=10000)
            page.wait_for_timeout(500)
            narrow = canvas.locator("#edRoot").evaluate(
                """() => { var v = document.getElementById('epAiConfigModal');
                     var cols = getComputedStyle(document.querySelector('.ep-ai-cols'))
                       .gridTemplateColumns.split(' ').length;
                     var sel = getComputedStyle(document.querySelector('.ep-ai-select')).minHeight;
                     var back = document.getElementById('epAiConfigBack');
                     var hit = parseFloat(getComputedStyle(back, '::after').height);
                     return {overflow: v.scrollWidth - v.clientWidth, cols: cols,
                             selectMin: sel, backHit: hit}; }""")
            check("375px API 视图不溢出＋双栏折单栏＋控件/命中区 ≥44px",
                  narrow["overflow"] <= 0 and narrow["cols"] == 1
                  and float(narrow["selectMin"].replace("px", "")) >= 44
                  and narrow["backHit"] >= 44, narrow)
            page.screenshot(path=str(shots / "07-mobile-375-api.png"))
            browser.close()

        # ---------- 三查＋零异常 ----------
        counts = {"fetch(": 0, "parent.document": 0, "localStorage": 0}
        for script in sorted((plugin_dir / "dist").glob("*.js")):
            text = script.read_text(encoding="utf-8", errors="replace")
            for needle in counts:
                counts[needle] += text.count(needle)
        check("三查 fetch(/parent.document/localStorage=0",
              all(value == 0 for value in counts.values()), counts)
        check("页面零 JS 异常", not result["page_errors"], result["page_errors"][:5])
        check("全程零 HTTP 失败", not result["http_failures"], result["http_failures"][:5])
    except Exception as error:  # noqa: BLE001 - 探针要把现场带回去
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        handle.close()
        time.sleep(0.5)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            closed = sock.connect_ex(("127.0.0.1", port)) != 0
        check("收口端口复验关闭", closed, {"port": port})

    failed = [item for item in result["checks"] if not item["ok"]]
    result["ok"] = not failed and not result.get("error")
    report = work / "probe.toml"
    report.write_text(toml_io.dumps(result, default=str), encoding="utf-8")
    for item in result["checks"]:
        print("[%s] %s" % ("PASS" if item["ok"] else "FAIL", item["name"]))
    print("ok=%s checks=%d failed=%d" % (result["ok"], len(result["checks"]), len(failed)))
    print("probe:", report)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
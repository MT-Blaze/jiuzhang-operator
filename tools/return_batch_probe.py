# -*- coding: utf-8 -*-
"""整批打回重新识别真机探针（2.20.0 卡§2）。

用法：``.venv/Scripts/python.exe tools/return_batch_probe.py [tag]``

隔离：独立 JZO_DATA_DIR / JZO_PLUGINS_DIR 副本＋动态空闲端口＋每次随机令牌，
不碰用户 data/ 与正式服务 65496。种批走进程内核心函数（真库真副本），
不起任何后台解析引擎；重入腿的后台识别撞「已停用」座显性失败——
prefs 先把 vlm_qwen / mineru_local 停用并把 auto_image_seat 指到 vlm_qwen，
MinerU 本地 CPU 逐题填充在任何探针禁跑（主公停跑令），这里从路由上就断死。

判据：
1. 批次行【重新识别】住删除旁，触控 ≥44px，aria-label 点批次号；
2. 键盘 Enter 触发确认弹窗，dismiss 后零打回请求（点头才动账）；
3. 确认弹窗摆明「2 道未入库题随批作废；1 道已入库题留库不动」；
4. accept 后原卷落收集框（文件名原样）、焦点还原到【开始解析】、批次行消失；
5. 元数据随 File 递进宿主：重入新批 meta 原样（year/subject/grade/region）；
6. 纯图卷把组合路灰掉＋人话 title；已选组合路弹回自动分流并 dock 明示；
7. 识别下拉＝自动＋registry 就绪且启用的识别席（条件断言，不硬编七链）；
8. 重入后台识别显性失败（已停用/不偷换），零 MinerU/VLM 引擎请求；
9. 375px 零横溢；零 JS 异常、零 HTTP 失败、三查=0、收口端口关闭。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402
from app.core.config import plugin_source_root  # noqa: E402

import base64
import json
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
PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
EDITOR_ID = "org.jiuzhang.editor"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
PNG_1PX = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
META = {"year": "2026", "subject": "数学", "grade": "九年级", "region": "海淀"}


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


def api_json(base: str, token: str, path: str) -> dict:
    request = urllib.request.Request(base + path, headers={"X-JZO-Token": token})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def seed_in_process() -> str:
    """进程内种一批：真副本＋2 待审＋1 已入库账＋元数据＋text_layer=False。"""
    from app.core.config import settings
    settings.workspace_id = None
    from app.core.pending import assets as p_assets, service as p_service
    from app.core.pending.batch import bank_batches, batches as p_batches
    from app.core.pending.db import connect

    rel = p_assets.store_source_backup("探针纯图卷.png", PNG_1PX)
    bid = bank_batches.create_batch(source_backup=rel,
                                    source_name="探针纯图卷.png")["batch_id"]
    docs = []
    for no in (1, 2):
        docs.append({"question": {
            "schema_version": "2.0", "type": "single_choice",
            "stem": "探针打回卷第 %d 题：$x+%d=%d$ 的解是（  ）" % (no, no, no + 1),
            "options": [{"key": "A", "content": "$1$"}, {"key": "B", "content": "$2$"}],
            "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
            "solution": "移项即得。", "difficulty": "L1",
            "source": {"paper_title": "探针打回卷", "question_no": str(no)}}})
    p_service.save_draft(docs, batch_id=bid, origin="probe.return")
    p_service.set_batch_meta(bid, META)
    bank_batches.set_batch_route(bid, {"text_layer": False})
    con = connect()
    try:
        p_batches.remember_approved(con, bid, "q_probe_kept_0001")
        con.commit()
    finally:
        con.close()
    return bid


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    token = "probe-" + secrets.token_hex(8)
    work = ROOT / ".system_generated" / "return-batch" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir, shots = work / "data", work / "plugins", work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    plugin_dir = plugins_dir / EDITOR_ID
    shutil.copytree(PLUGIN_SOURCE_DIR / EDITOR_ID, plugin_dir)
    shutil.rmtree(plugin_dir / "models", ignore_errors=True)
    # 停跑令护栏：两个本地引擎停用＋自动整题座指到停用座＝显性失败，绝不偷跑。
    toml_io.write(plugin_dir / "model_prefs.toml", {
        "disabled": ["vlm_qwen", "mineru_local"],
        "default_layout": "auto", "default_recognize": "auto",
        "auto_image_seat": "vlm_qwen", "auto_text_formula_seat": "auto"})

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = token
    env["JZO_RESTART_DISABLED"] = "1"
    env["JZO_POOL_ADMIT_DISABLED"] = "1"
    os.environ["JZO_DATA_DIR"] = str(data_dir)
    os.environ["JZO_PLUGINS_DIR"] = str(plugins_dir)
    server_log = work / "server.log"
    handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = None

    result: dict = {"tag": tag, "base": base, "viewport": "1920x1080",
                    "checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": [], "return_requests": [],
                    "engine_requests": [], "dialogs": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    dialog_state = {"accept": False}

    def on_dialog(dialog) -> None:
        result["dialogs"].append(dialog.message)
        if dialog_state["accept"]:
            dialog.accept()
        else:
            dialog.dismiss()

    try:
        bid = seed_in_process()
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "info", "--no-server-header"],
            cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
        wait_health(base, process, server_log)
        registry = api_json(base, token, "/api/models/registry?probe=0")
        ready_recognize = {str(entry["id"]) for entry in registry["entries"]
                           if entry.get("state") == "ready" and entry.get("enabled", True)
                           and entry.get("plan_recognize")}
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url)) if response.status >= 400 else None)

            def on_request(request) -> None:
                url = request.url
                if "/api/pending/return_batch" in url:
                    result["return_requests"].append(url)
                if "/api/models/" in url and ("install" in url or "uninstall" in url):
                    result["engine_requests"].append(url)
                if "/api/mineru" in url or "/api/vlm" in url:
                    result["engine_requests"].append(url)

            page.on("request", on_request)
            page.on("dialog", on_dialog)
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            row = canvas.locator(".ed-batch-row", has_text="探针纯图卷.png")
            expect(row).to_be_visible(timeout=20000)

            # ---------- 1/2. 按钮住删除旁＋键盘 Enter＋dismiss 零请求 ----------
            return_btn = row.locator(".btn-return-batch")
            expect(return_btn).to_be_visible(timeout=5000)
            box = return_btn.bounding_box()
            check("【重新识别】触控面 ≥44px", box and box["height"] >= 44, box)
            check("aria-label 点批次号",
                  bid in (return_btn.get_attribute("aria-label") or ""),
                  return_btn.get_attribute("aria-label"))
            order = row.evaluate(
                """node => { var del = node.querySelector('.btn-delete-batch');
                     var ret = node.querySelector('.btn-return-batch');
                     return !!(del && ret &&
                       (del.compareDocumentPosition(ret) & Node.DOCUMENT_POSITION_FOLLOWING)); }""")
            check("按钮住删除批次旁（其后）", bool(order))
            return_btn.focus()
            page.keyboard.press("Enter")
            page.wait_for_timeout(400)
            check("键盘 Enter 触发确认弹窗", bool(result["dialogs"]), result["dialogs"][-1:])
            check("dismiss 后零打回请求（点头才动账）",
                  not result["return_requests"], result["return_requests"])

            # ---------- 3. 确认弹窗摆明作废/留库账 ----------
            message = result["dialogs"][-1] if result["dialogs"] else ""
            check("弹窗摆明 2 道作废／1 道留库",
                  "2 道未入库题随批作废" in message and "1 道已入库题留库不动" in message
                  and bid in message, message)

            # ---------- 6/7. 空筐先选组合路，打回后灰掉弹回自动 ----------
            select = canvas.locator("#edRecognizeEngine")
            # 启动注入是异步 relay：等下拉就位再断言，不抢在 registry 响应前。
            expected = {"auto"} | ready_recognize
            options: list = []
            deadline = time.time() + 15
            while time.time() < deadline:
                options = select.evaluate(
                    "node => Array.from(node.options).map(o => o.value)")
                if set(options) == expected:
                    break
                page.wait_for_timeout(300)
            check("识别下拉＝自动＋就绪启用识别席（条件断言）",
                  set(options) == expected,
                  {"options": options, "expected": sorted(ready_recognize)})
            combo_value = "combo_pp_m" if "combo_pp_m" in options else ""
            if combo_value:
                select.select_option(combo_value)
                check("空筐时组合路可选", select.input_value() == combo_value)

            # ---------- 4. accept：原卷落筐＋焦点还原＋批次行消失 ----------
            dialog_state["accept"] = True
            with page.expect_response(
                    lambda r: "/api/pending/return_batch" in r.url, timeout=30000) as resp:
                return_btn.click()
            check("打回请求 200", resp.value.status == 200, resp.value.status)
            basket_item = canvas.locator(".ed-basket-item", has_text="探针纯图卷.png")
            expect(basket_item).to_be_visible(timeout=10000)
            check("原卷文件名原样落筐", basket_item.count() == 1)
            focused = canvas.locator("#edRoot").evaluate(
                "() => document.activeElement && document.activeElement.id")
            check("焦点还原到【开始解析】", focused == "edBasketGo", focused)
            expect(canvas.locator(".ed-batch-row")).to_have_count(0, timeout=10000)
            check("打回后批次行消失（未入库随批作废）", True)
            # dock 走宿主底栏日志（追加式），不在插件画布里；后一条弹回提示不抹前账。
            dock_text = "\n".join(page.locator(".ws-dock-item").all_text_contents())
            check("dock 明示打回账", "已打回收集框" in dock_text and "留库" in dock_text,
                  dock_text[-300:])
            if combo_value:
                combo_state = select.evaluate(
                    """node => { var o = Array.from(node.options).find(
                         x => x.value === 'combo_pp_m');
                       return { disabled: o.disabled, title: o.title, value: node.value }; }""")
                check("纯图卷把组合路灰掉＋人话 title",
                      combo_state["disabled"] and "纯图卷" in combo_state["title"],
                      combo_state)
                check("已选组合路弹回自动分流（显性不静默）",
                      combo_state["value"] == "auto" and "自动分流" in dock_text,
                      combo_state)
            page.screenshot(path=str(shots / "01-basket-returned.png"))

            # ---------- 5/8. 重入：元数据往返＋后台识别显性失败 ----------
            with page.expect_response(
                    lambda r: "/api/ingest/files" in r.url, timeout=30000) as ingest_resp:
                canvas.locator("#edBasketGo").click()
            check("重入解析请求发出", ingest_resp.value.status in (200, 201),
                  ingest_resp.value.status)
            new_card: dict = {}
            deadline = time.time() + 40
            while time.time() < deadline:
                payload = api_json(base, token, "/api/pending/batches")
                cards = [c for c in payload.get("batches", [])
                         if c.get("source_name") == "探针纯图卷.png"]
                if cards and (cards[0].get("route") or {}).get("done"):
                    new_card = cards[0]
                    break
                time.sleep(0.5)
            check("重入新批立起（原卷副本重生）", bool(new_card),
                  {"batch_id": new_card.get("batch_id")})
            meta = new_card.get("meta") or {}
            check("元数据原样往返（year/subject/grade/region）",
                  str(meta.get("year")) == "2026" and meta.get("subject") == "数学"
                  and meta.get("grade") == "九年级" and meta.get("region") == "海淀", meta)
            route = new_card.get("route") or {}
            failures = route.get("failures") or []
            check("后台识别显性失败（停用座，不偷换）",
                  bool(failures) and "不偷换" in str(failures[0].get("reason", "")),
                  failures[:1])
            check("text_layer=False 随重入落路由", route.get("text_layer") is False,
                  route.get("text_layer"))
            check("零引擎安装/卸载/服务请求（停跑令）",
                  not result["engine_requests"], result["engine_requests"])
            page.wait_for_timeout(600)
            page.screenshot(path=str(shots / "02-reentry-explicit-failure.png"))

            # ---------- 9. 375px 零横溢 ----------
            page.set_viewport_size({"width": 375, "height": 720})
            page.wait_for_timeout(500)
            overflow = canvas.locator("#edRoot").evaluate(
                "() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check("375px 零横溢", overflow <= 0, {"overflow_px": overflow})
            narrow_btn = canvas.locator(".btn-return-batch").first
            narrow_box = narrow_btn.bounding_box()
            check("窄屏打回按钮仍 ≥44px", narrow_box and narrow_box["height"] >= 44,
                  narrow_box)
            page.screenshot(path=str(shots / "03-mobile-375.png"))
            browser.close()

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
        if process is not None:
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
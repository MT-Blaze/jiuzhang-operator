# -*- coding: utf-8 -*-
"""本地 VLM 小题图微批真测（2.20.0 卡§0/§4：GPU 秒级产品路径）。

用法：``.venv/Scripts/python.exe tools/vlm_micro_probe.py [tag]``

隔离：独立 JZO_DATA_DIR / JZO_PLUGINS_DIR 副本＋动态空闲端口＋每次随机令牌，
不碰用户 data/ 与正式服务 65496。engines/ 是真机共享目录：安装走产品路径
（配置中心【安装】点击＋确认弹窗 accept），发动机 pip 四家测速选路、全败迁移
engines/mineru 现成 Vulkan 栈；GGUF 权重已在则 sha256 逐件校验跳过下载。
出网只由界面点击发起（卡§0 铁律）。

判据：
1. 配置中心 VLM 行【安装】点击＋确认 → 后台安装收口 done（发动机 vulkan）；
2. 权重已在：安装全程零 GGUF 下载请求（字节校验跳过）；
3. 收集框拖入 3 张小题图、识别下拉显式选 vlm_qwen、【开始解析】；
4. 三批各识别出 1 道非占位待审题，零失败清单；
5. GPU 秒级：单题墙钟 <60s、三题合计 <300s（首题含模型加载，如实报数）；
6. 零 JS 异常、零 HTTP 失败、收口端口关闭、llama-server 零孤儿。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402
from app.core.config import plugin_source_root  # noqa: E402

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
QUESTIONS = [
    "1. 解方程：x + 3 = 7，求 x 的值。",
    "2. 解方程：2x - 5 = 9，求 x 的值。",
    "3. 若 3x = 12，求 x 的值。",
]


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


def make_inputs(folder: Path) -> list[Path]:
    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 34)
    paths = []
    for index, text in enumerate(QUESTIONS, start=1):
        image = Image.new("RGB", (960, 200), "white")
        draw = ImageDraw.Draw(image)
        draw.text((40, 80), text, font=font, fill="black")
        path = folder / ("探针小题%d.png" % index)
        image.save(path)
        paths.append(path)
    return paths


def llama_pids() -> set[int]:
    output = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                            capture_output=True, text=True, timeout=30).stdout
    pids = set()
    for line in output.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if parts and parts[0].lower() == "llama-server.exe":
            try:
                pids.add(int(parts[1]))
            except (ValueError, IndexError):
                pass
    return pids


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    token = "probe-" + secrets.token_hex(8)
    work = ROOT / ".system_generated" / "vlm-micro" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir, shots = work / "data", work / "plugins", work / "shots"
    inputs = work / "inputs"
    for folder in (data_dir, plugins_dir, shots, inputs):
        folder.mkdir(parents=True)
    plugin_dir = plugins_dir / EDITOR_ID
    shutil.copytree(PLUGIN_SOURCE_DIR / EDITOR_ID, plugin_dir)
    shutil.rmtree(plugin_dir / "models", ignore_errors=True)
    toml_io.write(plugin_dir / "model_prefs.toml", {
        "disabled": [], "default_layout": "auto", "default_recognize": "auto",
        "auto_image_seat": "auto", "auto_text_formula_seat": "auto"})
    input_paths = make_inputs(inputs)

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
    process = None
    before_pids = llama_pids()

    result: dict = {"tag": tag, "base": base, "viewport": "1920x1080",
                    "checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": [], "install_requests": [],
                    "weight_downloads": [], "dialogs": [], "timing": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "info", "--no-server-header"],
            cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0)
        wait_health(base, process, server_log)
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
                if "/api/models/vlm/install" in url:
                    result["install_requests"].append(url)
                if ".gguf" in url.lower():
                    result["weight_downloads"].append(url)

            page.on("request", on_request)
            page.on("dialog", lambda dialog: (result["dialogs"].append(dialog.message),
                                              dialog.accept()))
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)

            # ---------- 1/2. 配置中心【安装】点击：产品路径，出网由点头发起 ----------
            with page.expect_response(
                    lambda r: "/api/models/registry?probe=1" in r.url, timeout=20000):
                canvas.locator("#epModelConfigList").click()
            vlm_row = canvas.locator(".ep-mt-row", has_text="千问 Qwen2.5-VL")
            install_btn = vlm_row.locator(".ep-mt-act", has_text="安装")
            took_install = install_btn.count() > 0
            if took_install:
                install_btn.click()
                page.wait_for_timeout(500)
                check("安装确认弹窗已摆成本并 accept", bool(result["dialogs"]),
                      result["dialogs"][-1:])
            install_state: dict = {}
            deadline = time.time() + 600
            while time.time() < deadline:
                install_state = api_json(base, token, "/api/models/vlm/status")
                if install_state.get("state") in ("done", "error"):
                    break
                if not took_install and install_state.get("state") == "idle":
                    break  # 已装复跑：没有安装线程，idle 即就绪态
                time.sleep(2)
            ready_now = install_state.get("state") == "done" or (
                not took_install and install_state.get("state") == "idle")
            check("安装收口就绪（首跑老师点击发起／复跑已装）", ready_now, install_state)
            if took_install:
                check("安装请求确由界面点击发出", bool(result["install_requests"]),
                      result["install_requests"])
            check("权重已在：零 GGUF 下载（字节校验跳过）",
                  not result["weight_downloads"], result["weight_downloads"][:3])
            from app.core.ingest import vlm_setup
            engine_kind = vlm_setup.engine_type()
            check("发动机真二进制现算＝vulkan", engine_kind == "vulkan", engine_kind)
            result["timing"]["engine"] = engine_kind
            expect(vlm_row.locator(".ep-mt-badge")).to_contain_text("就绪", timeout=30000)
            page.screenshot(path=str(shots / "01-config-installed.png"))
            canvas.locator("#edModelConfigBack").click()

            # ---------- 3. 收集框 3 张小题图＋显式选 vlm_qwen＋开始解析 ----------
            select = canvas.locator("#edRecognizeEngine")
            deadline = time.time() + 15
            options: list = []
            while time.time() < deadline:
                options = select.evaluate(
                    "node => Array.from(node.options).map(o => o.value)")
                if "vlm_qwen" in options:
                    break
                page.wait_for_timeout(300)
            check("就绪后 vlm_qwen 进识别下拉", "vlm_qwen" in options, options)
            canvas.locator("#edBasketFile").set_input_files(
                [str(path) for path in input_paths])
            expect(canvas.locator(".ed-basket-item")).to_have_count(3, timeout=10000)
            select.select_option("vlm_qwen")
            started = time.monotonic()
            with page.expect_response(
                    lambda r: "/api/ingest/files" in r.url, timeout=30000) as ingest_resp:
                canvas.locator("#edBasketGo").click()
            check("三图一批次各立（解析请求 201）", ingest_resp.value.status == 201,
                  ingest_resp.value.status)

            # ---------- 4/5. 三批识别收口：非占位＋零失败＋GPU 秒级 ----------
            done_at: dict[str, float] = {}
            cards: dict[str, dict] = {}
            deadline = time.time() + 300
            while time.time() < deadline and len(done_at) < 3:
                payload = api_json(base, token, "/api/pending/batches")
                for card in payload.get("batches", []):
                    name = str(card.get("source_name") or "")
                    if name.startswith("探针小题") and (card.get("route") or {}).get("done"):
                        if name not in done_at:
                            done_at[name] = time.monotonic() - started
                            cards[name] = card
                if len(done_at) < 3:
                    time.sleep(1)
            check("三批全部识别收口", len(done_at) == 3,
                  {"done": sorted(done_at), "elapsed_s": round(time.monotonic() - started, 1)})
            result["timing"]["per_question_wall_s"] = {
                name: round(seconds, 1) for name, seconds in sorted(done_at.items())}
            result["timing"]["total_wall_s"] = round(time.monotonic() - started, 1)
            ok_docs = True
            doc_notes = []
            for name, card in sorted(cards.items()):
                route = card.get("route") or {}
                failures = route.get("failures") or []
                questions = api_json(base, token,
                                     "/api/pending/batches/%s/questions" % card["batch_id"])
                items = questions.get("items") or []
                text = json.dumps(items, ensure_ascii=False)
                good = (len(items) == 1 and not failures
                        and "正在识别" not in text and "待识别" not in text
                        and "x" in text)
                ok_docs = ok_docs and good
                doc_notes.append({"name": name, "items": len(items),
                                  "failures": failures[:1], "stem_head": text[:120]})
            check("各批 1 道非占位待审题＋零失败清单", ok_docs, doc_notes)
            per_ok = all(seconds < 60 for seconds in done_at.values())
            check("GPU 秒级：单题墙钟 <60s", per_ok and len(done_at) == 3,
                  result["timing"]["per_question_wall_s"])
            check("三题合计 <300s（含首题模型加载）",
                  result["timing"]["total_wall_s"] < 300, result["timing"]["total_wall_s"])
            page.screenshot(path=str(shots / "02-batches-recognized.png"))
            first_card = cards.get("探针小题1.png") or {}
            if first_card:
                canvas.locator(".ed-batch-row", has_text="探针小题1.png").first.click()
                page.wait_for_timeout(1500)
                page.screenshot(path=str(shots / "03-question-review.png"))
            browser.close()

        check("页面零 JS 异常", not result["page_errors"], result["page_errors"][:5])
        check("全程零 HTTP 失败", not result["http_failures"], result["http_failures"][:5])
    except Exception as error:  # noqa: BLE001 - 探针要把现场带回去
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        if process is not None:
            # Windows terminate() 是硬杀，lifespan 停服跑不到＝llama-server 成孤儿；
            # 发 CTRL_BREAK 让 uvicorn 走优雅收口（main.py 停机钩子停 VLM 子进程树）。
            if sys.platform == "win32":
                import signal
                try:
                    os.kill(process.pid, signal.CTRL_BREAK_EVENT)
                except OSError:
                    process.terminate()
            else:
                process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
        handle.close()
        time.sleep(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            closed = sock.connect_ex(("127.0.0.1", port)) != 0
        check("收口端口复验关闭", closed, {"port": port})
        after_pids = llama_pids()
        orphans = after_pids - before_pids
        for pid in orphans:  # 本探针起的 llama-server 若成孤儿，点 PID 收掉（禁 /IM）
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=30)
        check("llama-server 零孤儿（lifespan 停服）", not orphans,
              {"before": sorted(before_pids), "orphans": sorted(orphans)})

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
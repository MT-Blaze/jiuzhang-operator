# -*- coding: utf-8 -*-
"""本地 YOLO 模型按需下载与路由播报真机探针。

用法：``.venv/Scripts/python.exe tools/yolo_model_probe.py <tag>``

隔离：独立 ``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` / 端口，不写本机 data。

判据：
1. 选【YOLO】且本机无模型 → 弹出模型下载窗，文案同时含「满血版 / 量化版」与体积；
2. 取消后不拦截老师继续换引擎；
3. 纯图 PDF 走 YOLO 降级链，批次 route 上带 ``layout_status``；
4. 该状态经宿主中继落进底部【运行日志】，原文含
   ``[WARN] 本地 YOLO 彻底失败，已自动降级至云端版面 API``。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

import base64
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
EDITOR_ID = "org.jiuzhang.editor"
TOKEN = "yolo-model-probe-token"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
CLOUD_WARNING = "[WARN] 本地 YOLO 彻底失败，已自动降级至云端版面 API"


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


def http_json(url: str, payload: dict | None = None) -> tuple[int, dict]:
    body = None if payload is None else wire.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        headers["X-JZO-Token"] = TOKEN
    request = urllib.request.Request(url, data=body, method="POST" if payload is not None else "GET",
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, wire.loads(raw or "{}")
        except wire.JSONDecodeError:
            return error.code, {"raw": raw}


def scanned_pdf(width: int = 300, height: int = 400) -> bytes:
    """手搓一页「纯图 PDF」：只有黑色横条，没有文本层，逼 YOLO 上场。"""
    raw = bytearray()
    for y in range(height):
        for x in range(width):
            ink = ((30 <= y <= 44 or 70 <= y <= 84 or 110 <= y <= 124
                    or 150 <= y <= 164) and 20 <= x <= width - 20)
            raw += b"\x28\x28\x28" if ink else b"\xff\xff\xff"
    image = zlib.compress(bytes(raw), 9)
    content = ("q %d 0 0 %d 0 0 cm /Im0 Do Q" % (width, height)).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d]"
         " /Resources << /XObject << /Im0 4 0 R >> >> /Contents 5 0 R >>"
         % (width, height)).encode(),
        ("<< /Type /XObject /Subtype /Image /Width %d /Height %d"
         " /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode"
         " /Length %d >>\nstream\n" % (width, height, len(image))).encode()
        + image + b"\nendstream",
        ("<< /Length %d >>\nstream\n" % len(content)).encode() + content + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for index, body in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += ("%d 0 obj\n" % index).encode() + body + b"\nendobj\n"
    xref = len(pdf)
    pdf += ("xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)).encode()
    for offset in offsets:
        pdf += ("%010d 00000 n \n" % offset).encode()
    pdf += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n"
            % (len(objects) + 1, xref)).encode()
    return bytes(pdf)


def batch_route(base: str, batch_id: str) -> dict:
    _, data = http_json(base + "/api/pending/batches")
    for card in data.get("batches") or []:
        if str(card.get("batch_id") or "") == batch_id:
            return card.get("route") or {}
    return {}


def wait_route_status(base: str, batch_id: str, timeout: float = 90) -> list[dict]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        statuses = batch_route(base, batch_id).get("layout_status") or []
        if statuses:
            return [item for item in statuses if isinstance(item, dict)]
        time.sleep(0.5)
    return []


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "yolo_model_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    plugin_dir = plugins_dir / EDITOR_ID
    shutil.copytree(PLUGIN_SOURCE_DIR / EDITOR_ID, plugin_dir)
    pdf_path = work / "scan.pdf"
    pdf_path.write_bytes(scanned_pdf())

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["JZO_RESTART_DISABLED"] = "1"
    env["JZO_POOL_ADMIT_DISABLED"] = "1"
    server_log = work / "server.log"
    handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process, server_log)

        # ---------- 后端：纯图 PDF 走 YOLO 降级链 ----------
        payload = {
            "files": [{"name": "纯图卷.pdf", "data_url":
                       "data:application/pdf;base64," + base64.b64encode(pdf_path.read_bytes()).decode()}],
            "layout_engine": "yolo",
            "recognize_engine": "auto",
        }
        status, staged = http_json(base + "/api/ingest/files", payload)
        batch_id = str(staged.get("batch_id") or "")
        check("纯图 PDF 能立批次", status == 201 and bool(batch_id), {"status": status})
        statuses = wait_route_status(base, batch_id)
        texts = [str(item.get("text") or "") for item in statuses]
        check("批次路由带 layout_status", bool(statuses), {"statuses": statuses})
        check("YOLO 失败时播报云端降级", CLOUD_WARNING in texts, {"texts": texts})

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
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)

            # ---------- 弹窗：无模型时选 YOLO ----------
            engine = canvas.locator("#edLayoutEngine")
            engine.select_option("yolo")
            modal = canvas.locator("#edModelModal")
            expect(modal).to_be_visible(timeout=10000)
            note = canvas.locator("#edModelNote").inner_text()
            hint = canvas.locator("#edModelHint").inner_text()
            full_text = canvas.locator("#edModelFull").inner_text()
            check("模型弹窗给出满血版入口", "满血版" in full_text,
                  {"note": note, "full": full_text})
            check("模型弹窗提示量化版", "量化版" in hint, {"hint": hint})
            check("两个下载入口都可点",
                  canvas.locator("#edModelFull").is_enabled()
                  and canvas.locator("#edModelQuantized").is_enabled())
            page.screenshot(path=str(shots / "model-modal.png"), full_page=False)
            canvas.locator("#edModelCancel").click()
            expect(modal).to_be_hidden(timeout=5000)

            # ---------- 造一个「已下载」的量化模型，放行 YOLO 解析 ----------
            models_dir = plugin_dir / "models"
            models_dir.mkdir(exist_ok=True)
            (models_dir / "doclayout_yolo_int8_v1.0.onnx").write_bytes(b"0" * (11 * 1024 * 1024))
            engine.select_option("auto")
            page.wait_for_timeout(300)
            engine.select_option("yolo")
            page.wait_for_timeout(800)
            check("模型就位后不再拦路", modal.is_hidden())

            # ---------- UI 走一遍解析：状态落【运行日志】 ----------
            canvas.locator("#edBasketFile").set_input_files(str(pdf_path))
            expect(canvas.locator("#edBasketGo")).to_be_visible(timeout=8000)
            canvas.locator("#edBasketGo").click()
            dock = page.locator("#wsDockLog")
            deadline = time.time() + 60
            log_text = ""
            while time.time() < deadline:
                log_text = dock.inner_text()
                if "本地 YOLO 彻底失败" in log_text:
                    break
                page.wait_for_timeout(500)
            check("状态原文进底部【运行日志】", "本地 YOLO 彻底失败" in log_text,
                  {"dock": log_text[-1200:]})
            check("日志带 [WARN] 前缀", "[WARN]" in log_text, {"dock": log_text[-1200:]})
            page.screenshot(path=str(shots / "dock-log.png"), full_page=False)
            browser.close()
    except Exception as error:  # noqa: BLE001 - 探针要把现场带回去
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        handle.close()

    failed = [item for item in result["checks"] if not item["ok"]]
    result["ok"] = not failed and not result.get("error")
    report = work / "report.toml"
    report.write_text(toml_io.dumps(result), encoding="utf-8")
    print(wire.dumps(result, ensure_ascii=False, indent=2))
    print("\nreport:", report)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

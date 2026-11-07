# -*- coding: utf-8 -*-
"""源码栏【添加配图】真机探针（终极军令 任务四）。

用法：``.venv/Scripts/python.exe tools/illustration_probe.py <tag>``

隔离：editor / bank-engine / bank-ui 复制进独立插件目录，另起端口与数据目录。
探针自己往中转站塞一道带题图的选择题，然后在真浏览器里走完整动线：

1. 光标落在 ``\\item`` 选项里 → 【添加配图】→ 左栏原图变画板（十字准心）；
2. 拖框后不落刀，双击才确认 → 选项里只多出一行
   ``\\includegraphics[width=0.2\\textwidth]{/static/uploads/...}``，
   **没有** ``\\\\``、**没有** ``A.`` 前缀；
3. 光标落在题干里 → 同样框选 → 插进 ``\\vspace{1ex}`` + ``\\begin{center}`` 环境；
4. Esc 取消：画板撤掉、源码一个字节都不动；
5. 全程零未捕获 JS 错误、零 4xx/5xx。
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
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
BANK_UI_ID = "org.jiuzhang.bank-ui"
TOKEN = "illustration-probe-token"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"


def make_png(width: int, height: int) -> bytes:
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            left = x < width // 2
            top = y < height // 2
            row += bytes((255, 0, 0) if left and top else
                         (0, 255, 0) if not left and top else
                         (0, 0, 255) if left else
                         (255, 255, 0))
        rows.append(bytes(row))

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
            + chunk(b"IEND", b""))


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
        payload_text = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, wire.loads(payload_text or "{}")
        except wire.JSONDecodeError:
            return error.code, {"raw": payload_text}


def seed_question() -> dict:
    return {
        "schema_version": "2.0",
        "id": "q_illu_probe_0001",
        "type": "single_choice",
        "stem": "探针配图题：求 $x+1=2$ 的解。",
        "options": [{"key": "A", "content": "$x=1$"}, {"key": "B", "content": "$x=2$"}],
        "answer": {"kind": "choice", "choice_keys": ["A"], "final": "A"},
        "solution": "由 $x+1=2$ 得 $x=1$。",
        "difficulty": "L1",
        "images": [{"id": "img_illu_probe", "role": "stem",
                    "uri": "/static/uploads/img_illu_probe.png"}],
        "extensions": {},
        "meta": {"created_at": "2026-11-05T10:00:00+08:00",
                 "updated_at": "2026-11-05T10:00:00+08:00",
                 "revision": 1, "status": "draft"},
    }


SOURCE = (
    "\\begin{question}\n"
    "探针配图题：求 $x+1=2$ 的解。\n"
    "\n"
    "\\begin{choices}\n"
    "  \\item $x=1$\n"
    "  \\item $x=2$\n"
    "\\end{choices}\n"
    "\\end{question}\n"
    "\n"
    "\\begin{solution}\n"
    "答案：A\n"
    "由 $x+1=2$ 得 $x=1$。\n"
    "\\end{solution}\n"
)


def run(tag: str) -> dict:
    work = ROOT / ".system_generated" / "illustration_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    for folder in (data_dir, plugins_dir, shots, data_dir / "uploads"):
        folder.mkdir(parents=True)
    for plugin_id in (EDITOR_ID, BANK_ID, BANK_UI_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)
    (data_dir / "uploads" / "img_illu_probe.png").write_bytes(make_png(240, 160))

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["JZO_RESTART_DISABLED"] = "1"
    env["JZO_POOL_ADMIT_DISABLED"] = "1"
    log_path = work / "server.log"
    log_handle = log_path.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": [], "notes": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    def snap(page, step: str) -> None:
        page.screenshot(path=str(shots / f"{step}.png"))

    try:
        wait_health(base, process, log_path)
        status, body = http_post(base + "/api/pending/batches", {
            "questions": [{"question": seed_question(),
                           "assets": [{"id": "img_illu_probe",
                                       "data_url": "data:image/png;base64,"
                                                   + base64.b64encode(
                                                       make_png(240, 160)).decode()}]}],
            "origin": "probe.illustration",
        })
        batch_id = str(body.get("batch_id") or "")
        check("带题图的探针批已入池", status == 201 and bool(batch_id), {"status": status})

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type == "error" else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url))
                if response.status >= 400 else None)
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=15000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            canvas.locator("#edRoot").evaluate("() => window.__jzoEditorV2.refreshBatches()")
            page.wait_for_timeout(700)
            row = canvas.locator('.ed-batch-row[data-batch="%s"]' % batch_id)
            expect(row).to_be_visible(timeout=10000)
            row.click()
            expect(canvas.locator("#edCols")).to_be_visible(timeout=20000)

            area = canvas.locator(".ed-src-area").first
            expect(area).to_be_visible(timeout=10000)
            area.fill(SOURCE)
            page.wait_for_timeout(300)

            def put_caret(needle: str, offset: int = 0) -> None:
                area.evaluate(
                    """(node, [needle, offset]) => {
                        const at = node.value.indexOf(needle) + offset;
                        node.focus();
                        node.setSelectionRange(at, at);
                        node.dispatchEvent(new Event('select', { bubbles: true }));
                    }""", [needle, offset])

            def canvas_box():
                board = canvas.locator(".ed-illustration-canvas")
                expect(board).to_be_visible(timeout=10000)
                return board, board.bounding_box()

            def drag_and_confirm(box) -> None:
                x1, y1 = box["x"] + 24, box["y"] + 24
                x2, y2 = box["x"] + box["width"] - 24, box["y"] + box["height"] - 24
                page.mouse.move(x1, y1)
                page.mouse.down()
                page.mouse.move(x2, y2, steps=8)
                page.mouse.up()
                page.wait_for_timeout(150)
                page.mouse.dblclick((x1 + x2) / 2, (y1 + y2) / 2)
                page.wait_for_timeout(800)

            def value_contains(needle: str, timeout: float = 20) -> bool:
                deadline = time.time() + timeout
                while time.time() < deadline:
                    if needle in area.input_value():
                        return True
                    page.wait_for_timeout(200)
                return False

            # ---------- 一、选项里插配图：只许纯 includegraphics ----------
            put_caret("\\item $x=1$", len("\\item "))
            canvas.locator("#edAddIllustration").click()
            board, box = canvas_box()
            result["notes"]["cursor"] = board.evaluate("n => getComputedStyle(n).cursor")
            check("点【添加配图】后原图变画板且是十字准心",
                  result["notes"]["cursor"] == "crosshair", result["notes"]["cursor"])
            snap(page, "10-board-open")
            drag_and_confirm(box)
            check("选项里插入了 0.2 宽度的配图",
                  value_contains("\\includegraphics[width=0.2\\textwidth]{/static/uploads/img_"),
                  area.input_value()[:400])
            check("选项配图没有多补 \\\\",
                  "\\includegraphics[width=0.2\\textwidth]{/static/uploads/img_"
                  in area.input_value()
                  and "\\\\includegraphics" not in area.input_value(),
                  area.input_value())
            option_line = next((line for line in area.input_value().splitlines()
                                if "includegraphics[width=0.2" in line), "")
            check("选项行没有 A./B. 前缀，也没被拆成两行",
                  "A." not in option_line and "B." not in option_line
                  and "\\\\" not in option_line,
                  option_line)
            check("确认后画板自动收摊", canvas.locator(".ed-illustration-canvas").count() == 0)
            snap(page, "20-option-inserted")

            # ---------- 二、题干里插配图：居中环境 + vspace ----------
            put_caret("探针配图题：", 0)
            canvas.locator("#edAddIllustration").click()
            board, box = canvas_box()
            drag_and_confirm(box)
            check("题干插入了 vspace + center 环境",
                  value_contains("\\vspace{1ex}") and value_contains("\\begin{center}")
                  and value_contains("\\end{center}"), area.input_value()[:500])
            check("题干配图在 center 环境里",
                  "\\begin{center}\n\\includegraphics[" in area.input_value(),
                  area.input_value()[:600])
            snap(page, "30-stem-inserted")

            # ---------- 三、Esc 取消：源码一个字节都不动 ----------
            before = area.input_value()
            put_caret("探针配图题：", 0)
            canvas.locator("#edAddIllustration").click()
            canvas_box()
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)
            check("Esc 撤掉画板", canvas.locator(".ed-illustration-canvas").count() == 0)
            check("Esc 不动源码", area.input_value() == before)
            snap(page, "40-esc-cancelled")

            check("宿主页零未捕获 JS 错误", not result["page_errors"],
                  wire.dumps(result["page_errors"], ensure_ascii=False)[:400])
            check("零 4xx/5xx", not result["http_failures"],
                  wire.dumps(result["http_failures"], ensure_ascii=False)[:400])
            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log_handle.close()

    passed = sum(1 for item in result["checks"] if item["ok"])
    result["passed"] = passed
    result["total"] = len(result["checks"])
    (work / "probe.toml").write_text(toml_io.dumps(result), encoding="utf-8")
    print(f"passed {passed}/{len(result['checks'])} -> {work / 'probe.toml'}")
    for item in result["checks"]:
        if not item["ok"]:
            print("FAIL:", item["name"], "|", item["detail"])
    return result


if __name__ == "__main__":
    report = run(sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S"))
    sys.exit(0 if report["total"] and report["passed"] == report["total"] else 1)

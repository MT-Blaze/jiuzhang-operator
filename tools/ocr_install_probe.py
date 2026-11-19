# -*- coding: utf-8 -*-
"""RapidOCR·准档安装点击＋3 样本 bench 收口（2.20.0 卡§0/§6）。

用法：``.venv/Scripts/python.exe tools/ocr_install_probe.py [tag]``

隔离：独立 JZO_DATA_DIR / JZO_PLUGINS_DIR 副本＋动态空闲端口＋每次随机令牌，
不碰用户 data/ 与正式服务 65496。权重落 engines/ocr/models/（真机共享目录，
产品安装行为）：出网只由配置中心【安装】点击＋确认弹窗 accept 发起，
modelscope 内置通道主源、三源点击内测速、sha256 逐件校验。
装完跑 tools/ocr_medium_bench.py（离线 CPU，快/准两档各 3 样本对照）——
MinerU 本地 CPU 逐题填充禁跑令与此无关，OCR bench 是卡面钦定真测。

判据：
1. 准档行【安装】点击＋139MB 成本确认弹窗 accept → 安装收口 done；
2. 两件 medium 权重落地且 weights_ready（sha256 逐件校验过）；
3. bench 离线跑通：3 样本 × 快/准两档，行数/链得分/耗时如实报；
4. 零 JS 异常、零 HTTP 失败、收口端口关闭。
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


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else "run1"
    token = "probe-" + secrets.token_hex(8)
    work = ROOT / ".system_generated" / "ocr-install" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir, plugins_dir, shots = work / "data", work / "plugins", work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    plugin_dir = plugins_dir / EDITOR_ID
    shutil.copytree(PLUGIN_SOURCE_DIR / EDITOR_ID, plugin_dir)
    shutil.rmtree(plugin_dir / "models", ignore_errors=True)
    toml_io.write(plugin_dir / "model_prefs.toml", {
        "disabled": [], "default_layout": "auto", "default_recognize": "auto",
        "auto_image_seat": "auto", "auto_text_formula_seat": "auto"})

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

    result: dict = {"tag": tag, "base": base, "viewport": "1920x1080",
                    "checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": [], "install_requests": [], "dialogs": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(port), "--log-level", "info", "--no-server-header"],
            cwd=str(ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT, text=True)
        wait_health(base, process, server_log)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url)) if response.status >= 400 else None)
            page.on("request", lambda request: result["install_requests"].append(request.url)
                    if "/api/models/ocr/install" in request.url else None)
            page.on("dialog", lambda dialog: (result["dialogs"].append(dialog.message),
                                              dialog.accept()))
            page.goto(base + "/workspace", wait_until="networkidle")
            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            with page.expect_response(
                    lambda r: "/api/models/registry?probe=1" in r.url, timeout=20000):
                canvas.locator("#epModelConfigList").click()
            acc_row = canvas.locator(".ep-mt-row", has_text="RapidOCR·准")
            install_btn = acc_row.locator(".ep-mt-act", has_text="安装")
            took_install = install_btn.count() > 0
            if took_install:
                install_btn.click()
                page.wait_for_timeout(500)
                check("139MB 成本确认弹窗已摆并 accept",
                      bool(result["dialogs"]) and "139MB" in result["dialogs"][-1],
                      result["dialogs"][-1:])
            install_state: dict = {}
            deadline = time.time() + 600
            while time.time() < deadline:
                install_state = api_json(base, token, "/api/models/ocr/status")
                if install_state.get("state") in ("done", "error"):
                    break
                if not took_install and install_state.get("state") == "idle":
                    break  # 已装复跑：没有安装线程
                time.sleep(2)
            from app.core.ingest import ocr_setup
            ready_now = ocr_setup.weights_ready()
            check("准档权重落地（sha256 逐件校验过）", ready_now, install_state)
            if took_install:
                check("安装请求确由界面点击发起", bool(result["install_requests"]),
                      result["install_requests"])
            paths = ocr_setup.model_paths()
            result["weights"] = [{"path": str(p), "bytes": p.stat().st_size if p.is_file() else 0}
                                 for p in paths]
            check("两件 medium 权重真文件在盘", all(p.is_file() for p in paths),
                  result["weights"])
            expect(acc_row.locator(".ep-mt-badge")).to_contain_text("就绪", timeout=30000)
            page.screenshot(path=str(shots / "01-ocr-installed.png"))
            browser.close()
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

    # ---------- 离线 bench：快/准两档 × 3 样本（卡面钦定真测，不出网） ----------
    bench_log = work / "bench.log"
    bench = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "ocr_medium_bench.py")],
        cwd=str(ROOT), capture_output=True, text=True, timeout=900,
        encoding="utf-8", errors="replace")
    bench_log.write_text(bench.stdout + "\n" + bench.stderr, encoding="utf-8")
    bench_report = ROOT / ".system_generated" / "ocr-medium-bench" / "bench.toml"
    bench_data = toml_io.load(bench_report, {}) if bench_report.is_file() else {}
    check("bench 离线跑通（rc=0）", bench.returncode == 0, bench.stdout[-300:])
    samples = bench_data.get("samples") or []
    check("bench 3 样本 × 快/准两档齐账", len(samples) == 3,
          {"samples": len(samples), "keys": sorted(bench_data)[:8]})
    result["bench"] = bench_data

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
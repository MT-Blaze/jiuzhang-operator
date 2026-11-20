# -*- coding: utf-8 -*-
"""MinerU 四合一真机探针：配置面＋一键装入口＋硬件门＋启用停用＋默认选择。

用法：``.venv/Scripts/python.exe tools/mineru_four_probe.py <tag>``

隔离：独立 ``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` 副本＋独立端口＋固定本地令牌，
不碰用户 data/ 与正式服务；收口点杀进程并复验端口关闭。

判据（只验本卡配置面，不真装 MinerU、不跑推理）：
1. registry 数据驱动：16 条目全带 summary_usage，档位表 6G 起共 7 档无 4G；
2. MinerU 本地座未装 → degraded＋【安装本地 MinerU】按钮在；安装写口无令牌被拒；
3. 硬件门：低于 6G 直写「电脑硬件不支持」，够格写「待 T6」；公式四位 blocked 待 T6；
4. 启用/停用＋默认选择代笔进隔离插件目录 model_prefs.toml，绝不落 data/；
   停用后下拉不显示，启用后恢复；默认选择键盘可达；
5. 弹窗 Esc 可关、焦点还原；375px 不横向溢出；
6. 三查：插件侧 fetch( / parent.document / localStorage 计数为 0。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io  # noqa: E402

import os
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
TOKEN = "mineru-four-probe-token"
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


def http_json(base: str, path: str, payload: dict | None = None,
              token: str | None = TOKEN) -> tuple[int, dict]:
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


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "mineru-four-card" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    plugin_dir = plugins_dir / EDITOR_ID
    shutil.copytree(PLUGIN_SOURCE_DIR / EDITOR_ID, plugin_dir)
    shutil.rmtree(plugin_dir / "models", ignore_errors=True)

    # 造一份「已下载」的满血版权重（隔离副本内），让 YOLO 就绪可供下拉/停用取证。
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

    result: dict = {"tag": tag, "base": base, "viewport": "1440x900",
                    "checks": [], "console_errors": [], "page_errors": [],
                    "http_failures": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    prefs_file = plugin_dir / "model_prefs.toml"
    try:
        wait_health(base, process, server_log)

        # ---------- 后端：目录数据驱动＋硬件门＋写口鉴权 ----------
        status, registry = http_json(base, "/api/models/registry")
        entries = registry.get("entries") or []
        by_id = {str(item.get("id")): item for item in entries}
        check("registry 200 且 18 条目", status == 200 and len(entries) == 18,
              {"status": status, "count": len(entries)})
        check("每条目带大白话使用说明",
              all(str(item.get("summary_usage") or "") for item in entries))
        tiers = registry.get("vram_tiers") or []
        tier_gb = [int(item.get("min_gb") or 0) for item in tiers]
        check("档位表 6G 起共 7 档无 4G", tier_gb == [6, 8, 10, 16, 20, 32, 48],
              {"tiers": tier_gb})
        hw = registry.get("hardware") or {}
        result["hardware"] = hw
        vram = float(hw.get("vram_gb") or 0)
        vlm = by_id.get("vlm_qwen") or {}
        if vram < 6:
            check("低于 6G 直写电脑硬件不支持",
                  vlm.get("state") == "blocked" and "电脑硬件不支持" in str(vlm.get("detail")),
                  {"vram": vram, "detail": vlm.get("detail")})
        else:
            check("够格 VLM 登记待 T6 不建推理",
                  vlm.get("state") == "blocked" and "待 T6" in str(vlm.get("detail")),
                  {"vram": vram, "detail": vlm.get("detail")})
        check("公式四位 blocked 待 T6",
              all((by_id.get(key) or {}).get("state") == "blocked"
                  and "待 T6" in str((by_id.get(key) or {}).get("detail"))
                  for key in ("formula_pp_m", "formula_pp_l", "formula_p2t", "formula_texify")))
        local = by_id.get("mineru_local") or {}
        check("MinerU 本地座未装 degraded＋安装动作",
              local.get("state") == "degraded" and local.get("action") == "install",
              {"state": local.get("state"), "detail": local.get("detail")})
        check("YOLO 权重就位 ready", (by_id.get("yolo") or {}).get("state") == "ready")

        code, _ = http_json(base, "/api/models/prefs", {"disabled": ["yolo"]}, token=None)
        check("prefs 写口无令牌被拒", code in (401, 403), {"code": code})
        code, _ = http_json(base, "/api/models/mineru/install", {}, token=None)
        check("install 写口无令牌被拒（不真装）", code in (401, 403), {"code": code})
        code, body = http_json(base, "/api/models/prefs", {"disabled": ["不存在的型号"]})
        check("未知型号 400", code == 400, {"code": code, "body": body})
        code, _ = http_json(base, "/api/models/mineru/status")
        check("安装进度只读可查", code == 200, {"code": code})

        # ---------- UI：配置页全貌 ----------
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

            engine = canvas.locator("#edLayoutEngine")
            expect(engine.locator('option[value="yolo"]')).to_have_count(1, timeout=15000)
            canvas.locator("#epModelConfigList").click()
            modal = canvas.locator("#edModelConfigModal")
            expect(modal).to_be_visible(timeout=10000)
            expect(canvas.locator(".ep-model-config-row")).to_have_count(16, timeout=15000)
            hw_text = canvas.locator(".ep-model-config-hw-line").inner_text()
            check("硬件快照上页", "显存" in hw_text, {"line": hw_text})
            check("档位表 7 行上页",
                  canvas.locator(".ep-model-config-tiers tr").count() == 8)
            check("使用说明逐条展示",
                  canvas.locator(".ep-model-config-usage").count() == 16)
            mineru_row = canvas.locator(".ep-model-config-row", has_text="MinerU·本地")
            check("未装时给安装按钮",
                  mineru_row.locator("button", has_text="安装本地 MinerU").count() == 1)
            canvas.locator("#edModelConfigList").evaluate("node => node.scrollTop = 0")
            page.wait_for_timeout(200)
            page.screenshot(path=str(shots / "config-overview.png"), full_page=False)
            mineru_row.scroll_into_view_if_needed()
            page.wait_for_timeout(200)
            page.screenshot(path=str(shots / "mineru-install.png"), full_page=False)

            # ---------- 停用＝下拉不显示＋状态住插件目录 ----------
            yolo_row = canvas.locator(".ep-model-config-row", has_text="YOLO·版面")
            yolo_row.locator(".ep-model-config-toggle").click()
            expect(engine.locator('option[value="yolo"]')).to_have_count(0, timeout=15000)
            expect(yolo_row.locator(".ep-model-config-toggle")).to_have_text("启用", timeout=15000)
            check("停用后下拉不显示 YOLO", True)
            check("停用态行有标记", "ep-model-config-disabled" in
                  (yolo_row.get_attribute("class") or ""))
            prefs = toml_io.load(prefs_file, {})
            check("状态文件住隔离插件目录", prefs_file.is_file() and "yolo" in prefs.get("disabled", []),
                  {"path": str(prefs_file), "prefs": prefs})
            check("状态绝不落宿主 data/", not list(data_dir.rglob("model_prefs.toml")))
            page.screenshot(path=str(shots / "disabled-state.png"), full_page=False)

            # ---------- 默认选择：键盘可达 ----------
            expected_default = "rapidocr_fast" if (by_id.get("rapidocr_fast") or {}).get("state") == "ready" else "yolo"
            layout_select = canvas.locator(".ep-model-config-default-select").first
            layout_select.click()
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
            expect(canvas.locator(".ep-model-config-defaults")).to_be_visible(timeout=10000)
            deadline = time.time() + 15
            picked = ""
            while time.time() < deadline:
                prefs = toml_io.load(prefs_file, {})
                picked = str(prefs.get("default_layout") or "")
                if picked and picked != "auto":
                    break
                page.wait_for_timeout(300)
            check("键盘改默认选择落插件目录", picked == expected_default,
                  {"default_layout": picked, "expected": expected_default})
            page.screenshot(path=str(shots / "defaults-keyboard.png"), full_page=False)

            # ---------- 启用恢复＋Esc 关弹窗焦点还原 ----------
            yolo_row.locator(".ep-model-config-toggle").click()
            expect(engine.locator('option[value="yolo"]')).to_have_count(1, timeout=15000)
            check("启用后下拉恢复 YOLO", True)
            page.keyboard.press("Escape")
            expect(modal).to_be_hidden(timeout=5000)
            restored = canvas.locator("#epModelConfigList").evaluate(
                "node => node === document.activeElement")
            check("Esc 关弹窗且焦点还原", bool(restored))

            # ---------- 375px 不横向溢出 ----------
            page.set_viewport_size({"width": 375, "height": 720})
            canvas.locator("#epModelConfigList").click()
            expect(modal).to_be_visible(timeout=10000)
            overflow = canvas.locator(".ep-model-config-card").evaluate(
                "node => node.scrollWidth - node.clientWidth")
            check("375px 弹窗不横向溢出", overflow <= 0, {"overflow_px": overflow})
            page.screenshot(path=str(shots / "mobile-375.png"), full_page=False)
            page.keyboard.press("Escape")
            browser.close()

        # ---------- 三查：插件侧零直连 ----------
        counts = {"fetch(": 0, "parent.document": 0, "localStorage": 0}
        for script in sorted((plugin_dir / "dist").glob("*.js")):
            text = script.read_text(encoding="utf-8", errors="replace")
            for needle in counts:
                counts[needle] += text.count(needle)
        check("三查 fetch(/parent.document/localStorage=0",
              all(value == 0 for value in counts.values()), counts)
        check("页面零 JS 异常", not result["page_errors"], result["page_errors"][:5])
        check("UI 阶段零 HTTP 失败", not result["http_failures"], result["http_failures"][:5])
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
# -*- coding: utf-8 -*-
"""配置归插件真机探针：目录住插件＋通用规则＋勾选代笔＋清单可更新。

用法：``.venv/Scripts/python.exe tools/config_to_plugin_probe.py <tag>``

隔离：独立 ``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` 副本＋动态空闲端口＋
每次随机本地令牌（不写死端口与令牌），不碰用户 data/ 与正式服务；
收口点杀进程并复验端口关闭。产物落 .system_generated/config-to-plugin/<tag>/。

判据（只验本卡契约，不真装 MinerU、不跑推理）：
1. 目录提供者：registry 16 条目来自隔离插件目录 catalog.toml；底座 app/ 下旧目录已搬走；
2. 通用规则：往隔离目录塞一条未知规则条目 → blocked＋「底座不认识这条规则」；删掉即恢复；
3. 清单可更新：改隔离目录 vram_note → registry 现读现变（不缓存、不用重启）；
4. 勾选代笔：prefs 写口必须带 plugin_id（缺省/幽灵 id 一律 403），落隔离插件目录，
   data/ 全树无 model_prefs.toml；无令牌被拒；
5. UI 真人路径：配置页 16 行＋说明＋档位表，停用/启用联动下拉，默认选择键盘可达，
   Esc 关弹窗焦点还原，375px 不横向溢出；
6. 三查：插件侧 fetch( / parent.document / localStorage 计数为 0。
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


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    token = "probe-" + secrets.token_hex(8)
    work = ROOT / ".system_generated" / "config-to-plugin" / tag
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
    catalog_file = plugin_dir / "catalog.toml"
    catalog_backup = catalog_file.read_text(encoding="utf-8")

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
    env["JZO_LOCAL_TOKEN"] = token
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

        # ---------- 目录提供者：数据来自插件目录，底座旧目录已搬走 ----------
        check("底座 app/ 下旧 catalog.toml 已搬走",
              not (ROOT / "app" / "core" / "ingest" / "catalog.toml").exists())
        check("隔离插件目录带 catalog.toml", catalog_file.is_file())
        status, registry = http_json(base, "/api/models/registry")
        entries = registry.get("entries") or []
        by_id = {str(item.get("id")): item for item in entries}
        check("registry 200 且 16 条目", status == 200 and len(entries) == 16,
              {"status": status, "count": len(entries)})
        check("每条目带大白话使用说明",
              all(str(item.get("summary_usage") or "") for item in entries))
        check("每条目声明通用规则名",
              all(str(item.get("rule") or "") for item in entries))
        tiers = registry.get("vram_tiers") or []
        tier_gb = [int(item.get("min_gb") or 0) for item in tiers]
        check("档位表 6G 起共 7 档无 4G", tier_gb == [6, 8, 10, 16, 20, 32, 48],
              {"tiers": tier_gb})
        hw = registry.get("hardware") or {}
        result["hardware"] = hw
        check("YOLO 权重就位 ready", (by_id.get("yolo") or {}).get("state") == "ready")
        check("MinerU 本地座未装 degraded＋安装动作",
              (by_id.get("mineru_local") or {}).get("state") == "degraded"
              and (by_id.get("mineru_local") or {}).get("action") == "install")

        # ---------- 通用规则：未知规则＝blocked＋提示更新底座 ----------
        catalog_file.write_text(
            catalog_backup + '\n[[entry]]\nid = "probe_future"\nname = "探针未来模型"\n'
            'capability = "layout"\nrule = "quantum_probe"\nsummary = "探针"\n'
            'summary_usage = "探针用"\nmin_vram = 0\ncan_cpu = true\n',
            encoding="utf-8")
        _, registry = http_json(base, "/api/models/registry")
        future = {str(item.get("id")): item for item in registry.get("entries") or []}.get("probe_future") or {}
        check("未知规则 blocked＋提示更新底座（不静默）",
              future.get("state") == "blocked"
              and "底座不认识这条规则" in str(future.get("detail"))
              and "更新底座" in str(future.get("detail")),
              {"state": future.get("state"), "detail": future.get("detail")})
        catalog_file.write_text(catalog_backup, encoding="utf-8")

        # ---------- 清单可更新：改目录现读现变，不缓存不用重启 ----------
        marked = catalog_backup.replace(
            'vram_note = "', 'vram_note = "探针标记·', 1)
        catalog_file.write_text(marked, encoding="utf-8")
        _, registry = http_json(base, "/api/models/registry")
        check("改目录 vram_note 立即生效（清单可更新）",
              "探针标记" in str(registry.get("vram_note") or ""),
              {"vram_note": registry.get("vram_note")})
        catalog_file.write_text(catalog_backup, encoding="utf-8")
        _, registry = http_json(base, "/api/models/registry")
        check("还原目录立即恢复", "探针标记" not in str(registry.get("vram_note") or ""))

        # ---------- 勾选代笔：plugin_id 资格＋写令牌＋落插件目录 ----------
        code, _ = http_json(base, "/api/models/prefs", {"disabled": ["yolo"]}, token=None)
        check("prefs 写口无令牌被拒", code in (401, 403), {"code": code})
        code, body = http_json(base, "/api/models/prefs", {"disabled": []}, token=token)
        check("缺 plugin_id 一律 403", code == 403, {"code": code, "body": body})
        code, body = http_json(base, "/api/models/prefs?plugin_id=org.example.ghost",
                               {"disabled": []}, token=token)
        check("幽灵插件 id 403", code == 403, {"code": code, "body": body})
        code, body = http_json(base, "/api/models/prefs?plugin_id=" + EDITOR_ID,
                               {"disabled": ["不存在的型号"]}, token=token)
        check("未知型号 400", code == 400, {"code": code, "body": body})
        code, body = http_json(base, "/api/models/prefs?plugin_id=" + EDITOR_ID,
                               {"disabled": ["yolo"]}, token=token)
        check("带 plugin_id 代笔成功", code == 200 and body.get("disabled") == ["yolo"],
              {"code": code, "body": body})
        prefs = toml_io.load(prefs_file, {})
        check("状态文件住隔离插件目录", prefs_file.is_file() and "yolo" in prefs.get("disabled", []),
              {"path": str(prefs_file), "prefs": prefs})
        check("data/ 全树无 model_prefs.toml", not list(data_dir.rglob("model_prefs.toml")))
        http_json(base, "/api/models/prefs?plugin_id=" + EDITOR_ID,
                  {"disabled": []}, token=token)

        # ---------- UI：配置页真人路径 ----------
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
            canvas.locator("#edModelConfigList").evaluate("node => node.scrollTop = 0")
            page.wait_for_timeout(200)
            page.screenshot(path=str(shots / "config-overview.png"), full_page=False)

            # ---------- 停用＝下拉不显示＋状态住插件目录（经 relay 代笔） ----------
            yolo_row = canvas.locator(".ep-model-config-row", has_text="YOLO·版面")
            yolo_row.locator(".ep-model-config-toggle").click()
            expect(engine.locator('option[value="yolo"]')).to_have_count(0, timeout=15000)
            expect(yolo_row.locator(".ep-model-config-toggle")).to_have_text("启用", timeout=15000)
            check("停用后下拉不显示 YOLO", True)
            prefs = toml_io.load(prefs_file, {})
            check("UI 停用经 relay 落插件目录", "yolo" in prefs.get("disabled", []),
                  {"prefs": prefs})
            check("UI 阶段 data/ 仍无 model_prefs.toml",
                  not list(data_dir.rglob("model_prefs.toml")))
            page.screenshot(path=str(shots / "disabled-state.png"), full_page=False)

            # ---------- 默认选择：键盘可达 ----------
            expected_default = "rapidocr_fast" if (by_id.get("rapidocr_fast") or {}).get("state") == "ready" else "yolo"
            layout_select = canvas.locator(".ep-model-config-default-select").first
            layout_select.click()
            page.keyboard.press("ArrowDown")
            page.keyboard.press("Enter")
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
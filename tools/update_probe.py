# -*- coding: utf-8 -*-
"""双轨更新真机探针（军令 #13 任务 10）：插件热更新 + 底座自更新。

用法：``.venv/Scripts/python.exe tools/update_probe.py <tag>``

隔离口径：``JZO_DATA_DIR`` / ``JZO_PLUGINS_DIR`` 指向
``.system_generated/update_probe/<tag>/``，本机 ``data/`` 与仓库 ``plugins/`` 一律不碰。
探针现场起一个只读静态服务器，托管一份合成索引与四个一次性插件 zip（不进仓库）。

判据：
  1. 设置页【检查更新】按本机索引出表：可更新 / 需先更新底座 / 底座新版本；
  2. 单条【更新】热更成功，新代码落地，新包里的空壳数据文件不覆盖本地题库；
  3. 新包没带的本地文件原地保留；
  4. 索引层 ``min_host_version`` 拦截：按钮灰、磁盘版本不变；
  5. 【一键更新全部插件】：兼容的更新、包内 ``min_host_version`` 不够的失败、不兼容的跳过；
  6. 【更新并重启】第一次只下载校验并生成 ``update.bat``，开发工作树如实拒绝覆盖重启；
  7. ``update.bat`` 在沙箱里真跑一遍：程序文件被覆盖，data/.venv/.git/dist/__pycache__/.system_generated 不被碰；
  8. 工作台控制台里热更 → 父页面输出日志出现「插件热更新」，无需刷新；
  9. 375px 无横向溢出，控制台零错误。
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.plugin_update import HOST_EXCLUDED_DIRS, build_update_script  # noqa: E402

PLUGIN_HOT = "org.probe.hot"
PLUGIN_BULK = "org.probe.bulk"
PLUGIN_MANIFEST = "org.probe.manifest"
PLUGIN_BLOCKED = "org.probe.blocked"
PLUGIN_BROADCAST = "org.probe.broadcast"
LICENSE_TEXT = "Apache License 2.0 (probe fixture, not the project license)"
HOST_VERSION = "99.0.0"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen, timeout: float = 30,
                log_path: Path | None = None) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            output = log_path.read_text(encoding="utf-8", errors="replace") if log_path else ""
            raise RuntimeError("服务提前退出：\n" + output[:4000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 %d 秒内就绪" % timeout)


def http_json(base: str, path: str, token: str = "", body: dict | None = None) -> tuple[int, dict]:
    data = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(base + path, data=data, method="POST" if data else "GET")
    if data is not None:
        request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("X-JZO-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, json.loads(payload or "{}")
        except json.JSONDecodeError:
            return error.code, {"raw": payload}


def manifest(plugin_id: str, version: str, min_host: str = "") -> dict:
    body = {
        "schema_version": "1.0",
        "id": plugin_id,
        "name": "双轨探针 " + plugin_id.split(".")[-1],
        "version": version,
        "api_version": "1.0",
        "kind": "renderer",
        "description": "军令 #13 任务 10 的一次性更新探针插件",
        "license": "Apache-2.0",
        "slots": ["question.card"],
        "capabilities": ["question.render"],
        "permissions": ["questions:read"],
        "entry": {"frontend": "dist/index.html"},
    }
    if min_host:
        body["min_host_version"] = min_host
    return body


def plugin_zip(plugin_id: str, version: str, marker: str, *, min_host: str = "",
               extra: dict[str, str] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        prefix = plugin_id + "/"
        archive.writestr(prefix + "plugin.json",
                         json.dumps(manifest(plugin_id, version, min_host), ensure_ascii=False))
        archive.writestr(prefix + "LICENSE", LICENSE_TEXT)
        archive.writestr(prefix + "dist/index.html",
                         "<!doctype html><title>%s</title><p>%s</p>" % (plugin_id, marker))
        for name, text in (extra or {}).items():
            archive.writestr(prefix + name, text)
    return buffer.getvalue()


def host_zip(version: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        prefix = "jiuzhang-operator-%s/" % version
        files = {
            "app/main.py": "# probe host %s\n" % version,
            "app/__init__.py": '__version__ = "%s"\n' % version,
            "static/workspace.html": "<!doctype html><title>九章算子 %s</title>" % version,
            "LICENSE": LICENSE_TEXT,
            "PROBE_HOST_MARKER.txt": "staged host payload " + version,
        }
        for name, text in files.items():
            archive.writestr(prefix + name, text)
    return buffer.getvalue()


def write_installed(plugins_dir: Path, plugin_id: str, version: str = "0.1.0",
                    files: dict[str, str] | None = None) -> Path:
    target = plugins_dir / plugin_id
    (target / "dist").mkdir(parents=True, exist_ok=True)
    (target / "plugin.json").write_text(
        json.dumps(manifest(plugin_id, version), ensure_ascii=False), encoding="utf-8")
    (target / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
    (target / "dist" / "index.html").write_text(
        "<!doctype html><p>%s %s</p>" % (plugin_id, version), encoding="utf-8")
    for name, text in (files or {}).items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return target


def entry(plugin_id: str, version: str, base: str, *, min_host: str = "") -> dict:
    row = {
        "id": plugin_id,
        "name": "双轨探针 " + plugin_id.split(".")[-1],
        "version": version,
        "zip_url": base + "/zips/%s-%s.zip" % (plugin_id, version),
        "mirrors": [],
        "description": "双轨更新真机探针条目",
        "homepage": None,
        "kind": "renderer",
        "api_version": "1.0",
    }
    if min_host:
        row["min_host_version"] = min_host
    return row


def write_index(server_dir: Path, base: str, plugin_ids: list[str]) -> None:
    payload = {
        "index_version": "1.0",
        "index_name": "双轨更新真机探针",
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "entries": [entry(plugin_id, "0.2.0", base,
                          min_host="99.0.0" if plugin_id == PLUGIN_BLOCKED else "")
                    for plugin_id in plugin_ids],
        "host": {
            "version": HOST_VERSION,
            "zip_url": base + "/host.zip",
            "mirrors": [],
            "notes": "探针底座包（只校验、不真替换）",
        },
    }
    (server_dir / "plugins.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - 基类签名
        return


def start_server(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = lambda *args, **kwargs: SilentHandler(*args, directory=str(directory), **kwargs)  # noqa: E731
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, "http://127.0.0.1:%d" % port


def version_on_disk(plugin_dir: Path) -> str:
    try:
        return str(json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))["version"])
    except (OSError, ValueError, KeyError):
        return ""


def wait_disk_version(plugin_dir: Path, expected: str, timeout: float = 20) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if version_on_disk(plugin_dir) == expected:
            return True
        time.sleep(0.1)
    return False


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_update_script_sandbox(work: Path) -> list[str]:
    """在一次性沙箱目录里真跑一遍 update.bat，确认覆盖范围与排除清单。"""
    details: list[str] = []
    sandbox_root = work / "bat-root"
    staged = work / "bat-stage"
    source = {
        "app/main.py": "OLD-MAIN",
        "static/workspace.html": "OLD-WS",
        "LICENSE": "OLD-LICENSE",
        "data/keep.db": "LOCAL-DB",
        ".git/config": "LOCAL-GIT",
        "dist/keep.txt": "LOCAL-DIST",
        "__pycache__/stale.pyc": "LOCAL-PYC",
        ".system_generated/tmp.txt": "LOCAL-SYSGEN",
    }
    incoming = {
        "app/main.py": "NEW-MAIN",
        "static/workspace.html": "NEW-WS",
        "LICENSE": "NEW-LICENSE",
        "PROBE_MARKER.txt": "NEW-MARKER",
        "data/keep.db": "REMOTE-DB",
        ".git/config": "REMOTE-GIT",
        "dist/keep.txt": "REMOTE-DIST",
        "__pycache__/stale.pyc": "REMOTE-PYC",
        ".system_generated/tmp.txt": "REMOTE-SYSGEN",
    }
    for name, text in source.items():
        path = sandbox_root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    for name, text in incoming.items():
        path = staged / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    stub = sandbox_root / ".venv" / "Scripts" / "python.exe"
    stub.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "whoami.exe", stub)
    stub_hash = sha256(stub)

    script_path = work / "update_sandbox.bat"
    script_path.write_text(
        build_update_script(root=sandbox_root, staged=staged, pid=999999, port=free_port()),
        encoding="utf-8", newline="\r\n")
    completed = subprocess.run(["cmd.exe", "/c", str(script_path)], cwd=str(sandbox_root),
                               capture_output=True, timeout=120)
    details.append("update.bat 退出码 %d" % completed.returncode)

    expected = {
        "app/main.py": "NEW-MAIN",
        "static/workspace.html": "NEW-WS",
        "LICENSE": "NEW-LICENSE",
        "PROBE_MARKER.txt": "NEW-MARKER",
        "data/keep.db": "LOCAL-DB",
        ".git/config": "LOCAL-GIT",
        "dist/keep.txt": "LOCAL-DIST",
        "__pycache__/stale.pyc": "LOCAL-PYC",
        ".system_generated/tmp.txt": "LOCAL-SYSGEN",
    }
    checks = []
    for name, want in expected.items():
        path = sandbox_root / name
        got = path.read_text(encoding="utf-8") if path.is_file() else "<missing>"
        checks.append((got == want, name, want, got))
    venv_ok = sha256(stub) == stub_hash
    checks.append((venv_ok, ".venv/Scripts/python.exe", "unchanged",
                   "unchanged" if venv_ok else "changed"))
    stage_gone = not staged.exists()
    checks.append((stage_gone, "暂存目录", "已清理", "已清理" if stage_gone else "仍存在"))
    script_gone = not script_path.exists()
    checks.append((script_gone, "update.bat", "已自删", "已自删" if script_gone else "仍存在"))
    failed = [item for item in checks if not item[0]]
    for ok, name, want, got in checks:
        details.append(("PASS " if ok else "FAIL ") + "%s → %s（实际 %s）" % (name, want, got))
    if failed:
        raise AssertionError("update.bat 沙箱执行不符：\n" + "\n".join(details))
    return details


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "update_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    shots = work / "shots"
    shots.mkdir(parents=True)
    plugins_dir = work / "plugins"
    data_dir = work / "data"
    server_dir = work / "server"
    (server_dir / "zips").mkdir(parents=True)
    plugins_dir.mkdir()
    data_dir.mkdir()

    write_installed(plugins_dir, PLUGIN_HOT, files={
        "bank/bank.db": "LOCAL-DB", "notes.txt": "KEEP-ME"})
    write_installed(plugins_dir, PLUGIN_BULK)
    write_installed(plugins_dir, PLUGIN_MANIFEST)
    write_installed(plugins_dir, PLUGIN_BLOCKED)
    write_installed(plugins_dir, PLUGIN_BROADCAST)
    # 工作台要有活跃题库才不会让 /api/bank/* 回 400（控制台零报错判据需要）。
    # 复制的是当前仓库里的官方插件，只进隔离目录，不动源目录。
    shutil.copytree(ROOT / "plugins" / "org.jiuzhang.core-bank",
                    plugins_dir / "org.jiuzhang.core-bank")

    basic_ids = [PLUGIN_HOT, PLUGIN_BULK, PLUGIN_MANIFEST, PLUGIN_BLOCKED]
    full_ids = basic_ids + [PLUGIN_BROADCAST]

    # 先写基础索引占位；拿到静态服务器端口后再写两份真实地址。
    server, base = start_server(server_dir)
    write_index(server_dir, base, basic_ids)
    (server_dir / "plugins-full.json").write_text(
        json.dumps({
            "index_version": "1.0",
            "index_name": "双轨更新真机探针（含广播条目）",
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "entries": [entry(plugin_id, "0.2.0", base,
                              min_host="99.0.0" if plugin_id == PLUGIN_BLOCKED else "")
                        for plugin_id in full_ids],
            "host": {"version": HOST_VERSION, "zip_url": base + "/host.zip", "mirrors": [],
                     "notes": "探针底座包（只校验、不真替换）"},
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    (server_dir / "zips" / (PLUGIN_HOT + "-0.2.0.zip")).write_bytes(plugin_zip(
        PLUGIN_HOT, "0.2.0", "HOT-0.2.0", extra={
            "bank/bank.db": "REMOTE-EMPTY-DB",
            "dist/plugin.js": "console.log('hot 0.2.0');",
        }))
    (server_dir / "zips" / (PLUGIN_BULK + "-0.2.0.zip")).write_bytes(plugin_zip(
        PLUGIN_BULK, "0.2.0", "BULK-0.2.0"))
    (server_dir / "zips" / (PLUGIN_MANIFEST + "-0.2.0.zip")).write_bytes(plugin_zip(
        PLUGIN_MANIFEST, "0.2.0", "MANIFEST-0.2.0", min_host="99.0.0"))
    (server_dir / "zips" / (PLUGIN_BLOCKED + "-0.2.0.zip")).write_bytes(plugin_zip(
        PLUGIN_BLOCKED, "0.2.0", "BLOCKED-0.2.0"))
    (server_dir / "zips" / (PLUGIN_BROADCAST + "-0.2.0.zip")).write_bytes(plugin_zip(
        PLUGIN_BROADCAST, "0.2.0", "BROADCAST-0.2.0"))
    (server_dir / "host.zip").write_bytes(host_zip(HOST_VERSION))

    port = free_port()
    base_app = "http://127.0.0.1:%d" % port
    env = dict(os.environ)
    env.update({
        "JZO_DATA_DIR": str(data_dir),
        "JZO_PLUGINS_DIR": str(plugins_dir),
        "JZO_PORT": str(port),
        "PYTHONIOENCODING": "utf-8",
    })
    log_path = work / "app.log"
    log_handle = log_path.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [str(ROOT / ".venv" / "Scripts" / "python.exe"), "-m", "uvicorn", "app.main:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True)

    results: list[tuple[bool, str]] = []
    artifacts: dict[str, object] = {"tag": tag, "work": str(work), "port": port,
                                    "index_url": base + "/plugins.json"}
    page_errors: list[str] = []
    console_errors: list[str] = []
    script_path: Path | None = None
    stage_path: Path | None = None
    try:
        wait_health(base_app, process, log_path=log_path)
        _status, settings = http_json(base_app, "/api/settings")
        token = str(settings.get("local_token") or "")
        if not token:
            raise RuntimeError("拿不到本地写令牌")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_context(viewport={"width": 1440, "height": 960}).new_page()
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.on("console", lambda message: console_errors.append(message.text)
                    if message.type == "error" else None)

            page.goto(base_app + "/settings?panel=plugin&tab=index", wait_until="networkidle")
            page.fill("#plIndexUrl", base + "/plugins.json")
            page.click("#stPluginTabUpdate")
            page.click("#upCheckBtn")

            hot_card = page.locator('#upList li[data-id="%s"]' % PLUGIN_HOT)
            bulk_card = page.locator('#upList li[data-id="%s"]' % PLUGIN_BULK)
            manifest_card = page.locator('#upList li[data-id="%s"]' % PLUGIN_MANIFEST)
            blocked_card = page.locator('#upList li[data-id="%s"]' % PLUGIN_BLOCKED)
            expect(hot_card).to_have_attribute("data-state", "update_available")
            expect(bulk_card).to_have_attribute("data-state", "update_available")
            expect(manifest_card).to_have_attribute("data-state", "update_available")
            expect(blocked_card).to_have_attribute("data-state", "incompatible")
            blocked_button = blocked_card.locator("button")
            expect(blocked_button).to_be_disabled()
            expect(blocked_button).to_have_text("需先更新底座")
            expect(page.locator("#upHostText")).to_contain_text(HOST_VERSION)
            expect(page.locator("#upHostBtn")).to_be_enabled()
            results.append((True, "检查更新：4 条状态正确，min_host_version 拦截可见，底座新版本可见"))
            page.screenshot(path=str(shots / "10-checked.png"), full_page=True)

            hot_card.locator("button").click()
            expect(page.locator("#upLog")).to_contain_text("已更新 " + PLUGIN_HOT)
            ok = wait_disk_version(plugins_dir / PLUGIN_HOT, "0.2.0")
            results.append((ok, "单条更新：磁盘 plugin.json 0.1.0 → 0.2.0"))
            hot_code = plugins_dir / PLUGIN_HOT / "dist" / "plugin.js"
            hot_code_text = hot_code.read_text(encoding="utf-8") if hot_code.is_file() else ""
            results.append((hot_code.is_file() and "hot 0.2.0" in hot_code_text,
                            "单条更新：新代码落地"))
            db_text = (plugins_dir / PLUGIN_HOT / "bank" / "bank.db").read_text(encoding="utf-8")
            results.append((db_text == "LOCAL-DB", "数据必保：新包空壳 bank.db 没覆盖本地题库"))
            kept_note = plugins_dir / PLUGIN_HOT / "notes.txt"
            kept_text = kept_note.read_text(encoding="utf-8") if kept_note.is_file() else ""
            results.append((kept_text == "KEEP-ME", "数据必保：新包没带的本地文件原地保留"))
            results.append((version_on_disk(plugins_dir / PLUGIN_BLOCKED) == "0.1.0",
                            "不兼容条目未被覆盖"))
            page.screenshot(path=str(shots / "20-hot-updated.png"), full_page=True)

            page.locator("#upAllBtn").click()
            expect(page.locator("#upLog")).to_contain_text("已更新 " + PLUGIN_BULK)
            expect(page.locator("#upLog")).to_contain_text("更新失败 " + PLUGIN_MANIFEST)
            expect(page.locator("#upLog")).to_contain_text("已跳过 " + PLUGIN_BLOCKED)
            results.append((wait_disk_version(plugins_dir / PLUGIN_BULK, "0.2.0"),
                            "一键更新：兼容条目热更成功"))
            results.append((version_on_disk(plugins_dir / PLUGIN_MANIFEST) == "0.1.0",
                            "包内 min_host_version 拦截：不覆盖本地代码"))
            results.append((version_on_disk(plugins_dir / PLUGIN_BLOCKED) == "0.1.0",
                            "索引层 min_host_version 拦截：一键更新跳过"))
            page.screenshot(path=str(shots / "30-batch.png"), full_page=True)

            page.locator("#upHostBtn").click()
            expect(page.locator("#upLog")).to_contain_text("一次性脚本已生成")
            expect(page.locator("#upLog")).to_contain_text("开发工作树")
            expect(page.locator("#upHostBtn")).to_be_disabled()
            update_log = page.locator("#upLog").inner_text()
            found = re.search(r"jzo_update_(\d+)\.bat", update_log)
            results.append((found is not None, "界面如实报出一次性脚本路径"))
            pid = found.group(1) if found else str(process.pid)
            script_path = Path(tempfile.gettempdir()) / ("jzo_update_%s.bat" % pid)
            stage_path = Path(tempfile.gettempdir()) / ("jzo_host_update_%s" % pid)
            script_text = script_path.read_text(encoding="utf-8") if script_path.is_file() else ""
            results.append((script_path.is_file(), "底座自更新：一次性 update.bat 已生成"))
            results.append(("robocopy" in script_text and all(name in script_text
                                                            for name in HOST_EXCLUDED_DIRS),
                            "update.bat 含 robocopy 与全部排除目录"))
            results.append(("uvicorn app.main:app" in script_text and 'del "%~f0"' in script_text,
                            "update.bat 含重启与自删步骤"))
            host_marker = stage_path / "app" / "main.py"
            results.append((host_marker.is_file() and "probe host" in host_marker.read_text(encoding="utf-8"),
                            "底座包已解到暂存区并通过三件套校验"))
            results.append(((Path(ROOT) / ".git").exists(), "开发工作树如实拒绝覆盖重启"))
            page.screenshot(path=str(shots / "40-host-prepared.png"), full_page=True)

            status, applied = http_json(base_app, "/api/plugins/update/apply", token,
                                        {"ids": [PLUGIN_BLOCKED]})
            skipped = applied.get("skipped") or []
            results.append((status == 200 and any(row.get("id") == PLUGIN_BLOCKED for row in skipped)
                            and version_on_disk(plugins_dir / PLUGIN_BLOCKED) == "0.1.0",
                            "API 直调：不兼容条目进 skipped、磁盘版本不变"))

            bat_details = verify_update_script_sandbox(work)
            artifacts["update_bat"] = bat_details
            results.append((True, "update.bat 沙箱真跑：覆盖程序文件、保护六个目录、自删"))

            # 工作台控制台内热更 → 父页面广播路径
            console_page = browser.new_context(viewport={"width": 1440, "height": 960}).new_page()
            console_events: list[str] = []
            console_page.on("pageerror", lambda error: page_errors.append(str(error)))
            console_page.on("console", lambda message: console_events.append(
                "console[%s] %s" % (message.type, message.text)))
            console_page.on("requestfailed", lambda request: console_events.append(
                "requestfailed %s %s" % (request.url, request.failure)))
            console_page.on("response", lambda response: console_events.append(
                "response %d %s" % (response.status, response.url))
                if ("/api/settings" in response.url or "/api/plugins/update" in response.url) else None)
            console_page.goto(base_app + "/workspace", wait_until="networkidle")
            console_page.click("#wsConsoleBtn")
            frame = console_page.frame_locator("#wsConsoleFrame")
            frame.locator("#stNavPlugin").click()
            frame.locator("#stPluginTabIndex").click()
            frame.locator("#plIndexUrl").fill(base + "/plugins-full.json")
            frame.locator("#stPluginTabUpdate").click()
            frame.locator("#upCheckBtn").click()
            broadcast_card = frame.locator('#upList li[data-id="%s"]' % PLUGIN_BROADCAST)
            try:
                expect(broadcast_card).to_have_attribute("data-state", "update_available",
                                                         timeout=15000)
            except AssertionError as error:
                body = frame.locator("body").inner_text()[:1500]
                started = time.time()
                try:
                    health_status, _ = http_json(base_app, "/healthz")
                    check_status, _ = http_json(
                        base_app, "/api/plugins/update/check", token,
                        {"url": base + "/plugins-full.json"})
                    direct = "healthz=%d check=%d 用时 %.2fs" % (
                        health_status, check_status, time.time() - started)
                except Exception as exc:  # noqa: BLE001 - 诊断路径
                    direct = "直连 API 也失败：%r" % (exc,)
                raise AssertionError("控制台内检查更新失败，页面正文：\n" + body
                                     + "\n直连：" + direct
                                     + "\n事件：\n" + "\n".join(console_events)
                                     + "\n底座日志尾部：\n"
                                     + "\n".join(log_path.read_text(
                                         encoding="utf-8", errors="replace").splitlines()[-25:])) from error
            broadcast_card.locator("button").click()
            expect(console_page.locator("#ctxHistory")).to_contain_text(
                "插件热更新：" + PLUGIN_BROADCAST, timeout=20000)
            results.append((wait_disk_version(plugins_dir / PLUGIN_BROADCAST, "0.2.0"),
                            "工作台控制台热更：父页面输出日志收到「插件热更新」广播"))
            console_page.screenshot(path=str(shots / "50-workspace-hotupdate.png"), full_page=True)

            mobile = browser.new_context(viewport={"width": 375, "height": 780}).new_page()
            mobile.goto(base_app + "/settings", wait_until="networkidle")
            mobile.click("#stNavPlugin")
            no_overflow = mobile.evaluate(
                "() => document.documentElement.scrollWidth <= window.innerWidth + 1")
            results.append((no_overflow, "375px 设置页无横向溢出"))
            mobile.screenshot(path=str(shots / "60-mobile-375.png"), full_page=True)

            results.append((not page_errors, "页面零未捕获错误" +
                            ("" if not page_errors else "：" + " | ".join(page_errors[:3]))))
            results.append((not console_errors, "控制台零报错" +
                            ("" if not console_errors else "：" + " | ".join(console_errors[:3]))))
            browser.close()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
        server.shutdown()
        server.server_close()
        log_handle.close()
        for leftover in (script_path, stage_path):
            if leftover is None:
                continue
            if leftover.is_dir():
                shutil.rmtree(leftover, ignore_errors=True)
            elif leftover.is_file():
                try:
                    leftover.unlink()
                except OSError:
                    pass

    passed = sum(1 for ok, _ in results if ok)
    total = len(results)
    artifacts["checks"] = [{"ok": ok, "label": label} for ok, label in results]
    artifacts["page_errors"] = page_errors
    artifacts["console_errors"] = console_errors
    (work / "probe.json").write_text(
        json.dumps(artifacts, ensure_ascii=False, indent=2), encoding="utf-8")

    for ok, label in results:
        print(("PASS " if ok else "FAIL ") + label)
    verdict = "PASS" if passed == total else "FAIL"
    print("\n%s · %d/%d · %s" % (verdict, passed, total, work))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

# -*- coding: utf-8 -*-
"""套件真机验收：干净环境装一次套件，左栏不再出现题库入口，引擎可读题。

用法：``.venv/Scripts/python.exe tools/suite_probe.py <tag>``
（脚本自己在随机端口起隔离服务，临时 data/plugins 目录，跑完关掉）

判据：
  1. 干净环境起始零插件；
  2. 上传 org.jiuzhang.bank-suite.zip 后，响应带 suite 元信息与唯一成员；
  3. /api/plugins 里引擎启用、headless、不占左栏，无依赖阻塞；
  4. 左栏没有任何【九章题库】入口（纯后台引擎不配画布）；
  5. 经引擎写一道题再读回来，题干一致（引擎真在后台干活）；
  6. 真实浏览器里宿主工作区正常打开，无 JS 错误。

产出：``.system_generated/suite_probe/<tag>/probe.toml`` + 截图；任一判据红即非零退出。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

import importlib.util
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
ENGINE_ID = "org.jiuzhang.bank-engine"
UI_ID = ENGINE_ID
SUITE_ID = "org.jiuzhang.bank-suite"
TOKEN = "suite-probe-token"


def _load_build_tool():
    spec = importlib.util.spec_from_file_location(
        "jzo_build_plugin_probe", ROOT / "tools" / "build_plugin.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 25
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
    raise RuntimeError("服务未在 25 秒内就绪")


def api_json(base: str, path: str, *, method: str = "GET", payload=None,
             token: bool = False) -> tuple[int, object]:
    data = None
    headers = {}
    if payload is not None:
        data = wire.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-JZO-Token"] = TOKEN
    request = urllib.request.Request(base + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            return response.status, wire.loads(raw.decode("utf-8") or "null")
    except urllib.error.HTTPError as error:
        raw = error.read()
        error.close()
        try:
            return error.code, wire.loads(raw.decode("utf-8") or "null")
        except wire.JSONDecodeError:
            return error.code, raw.decode("utf-8", "replace")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "suite_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    shots.mkdir(parents=True)

    build_tool = _load_build_tool()
    suite_zip = build_tool.build_suite(
        [ROOT / "plugins" / ENGINE_ID], work / "out"
    ).read_bytes()

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    report: dict = {
        "tag": tag, "base": base, "checks": [], "passed": 0, "total": 0,
        "console_errors": [], "page_errors": [], "shots": [], "notes": {},
    }

    def check(name: str, ok: bool, detail=None) -> bool:
        report["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
        return bool(ok)

    def finish(code: int) -> int:
        report["total"] = len(report["checks"])
        report["passed"] = sum(1 for item in report["checks"] if item["ok"])
        (work / "probe.toml").write_text(
            toml_io.dumps(report), encoding="utf-8")
        print(wire.dumps({"passed": report["passed"], "total": report["total"],
                          "probe": str(work / "probe.toml")}, ensure_ascii=False))
        return code

    try:
        wait_health(base, process)

        status, initial = api_json(base, "/api/plugins")
        check("干净环境起始零插件",
              status == 200 and not (initial or {}).get("plugins"),
              {"status": status, "plugins": len((initial or {}).get("plugins") or [])})

        request = urllib.request.Request(
            base + "/api/plugins/install",
            data=suite_zip,
            headers={"Content-Type": "application/zip", "X-JZO-Token": TOKEN},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                status, body = response.status, wire.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read().decode("utf-8", "replace")
        members = [item.get("id") for item in (body or {}).get("plugins", [])] \
            if isinstance(body, dict) else []
        report["notes"]["install"] = body
        check("套件一次安装成功", status == 200 and (body or {}).get("installed") is True,
              {"status": status, "body": body if status != 200 else None})
        check("响应带回套件元信息与唯一成员",
              isinstance(body, dict) and (body.get("suite") or {}).get("id") == SUITE_ID
              and members == [ENGINE_ID], members)

        status, discovery = api_json(base, "/api/plugins")
        plugins = (discovery or {}).get("plugins") or []
        by_id = {item.get("id"): item for item in plugins}
        engine = by_id.get(ENGINE_ID) or {}
        report["notes"]["plugins"] = {
            key: {
                "enabled": item.get("enabled"),
                "headless": item.get("headless"),
                "show_in_sidebar": item.get("show_in_sidebar"),
                "requires": item.get("requires"),
                "dependency_blocked": item.get("dependency_blocked"),
            }
            for key, item in by_id.items()
        }
        check("引擎启用、headless 且不占左栏",
              engine.get("enabled") is True and engine.get("headless") is True
              and engine.get("show_in_sidebar") is False, engine)
        visible = [item.get("id") for item in plugins
                   if item.get("enabled") is not False and item.get("show_in_sidebar") is not False]
        check("左栏没有题库入口", visible == [], visible)
        check("没有依赖阻塞项", not (discovery or {}).get("dependency_blocked"),
              (discovery or {}).get("dependency_blocked"))

        question = {
            "question": {
                "schema_version": "1.0",
                "type": "fill_blank",
                "stem": "套件验收题：$1+1=$ ＿＿＿＿。",
                "answer": {"kind": "expression", "content": "$2$", "final": "2"},
                "difficulty": "basic",
                "extensions": {"org.jiuzhang.editor": {"grade": "高一"}},
                "meta": {"status": "published", "author": "套件探针"},
            }
        }
        status, created = api_json(
            base, f"/api/bank/plugins/{ENGINE_ID}/questions",
            method="POST", payload=question, token=True,
        )
        check("经引擎写入一道题", status == 201, {"status": status, "body": created})
        status, listed = api_json(
            base, f"/api/bank/plugins/{ENGINE_ID}/questions?q=%E5%A5%97%E4%BB%B6%E9%AA%8C%E6%94%B6&page_size=10"
        )
        items = (listed or {}).get("items") or []
        check("引擎读回刚写的题",
              status == 200 and any("套件验收题" in str(item.get("stem")) for item in items),
              {"status": status, "total": (listed or {}).get("total")})

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: report["console_errors"].append(message.text)
                    if message.type == "error" else None)
            page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
            page.goto(base + "/workspace", wait_until="networkidle")

            entries = page.locator(".ws-plugin-item")
            expect(entries).to_have_count(0, timeout=10000)
            check("浏览器左栏没有题库入口", entries.count() == 0)

            shot = shots / "suite.png"
            page.screenshot(path=str(shot))
            report["shots"].append(str(shot))

            check("宿主页无 JS 错误", not report["page_errors"], report["page_errors"][:5])
            check("控制台无 error", not report["console_errors"], report["console_errors"][:5])
            browser.close()
    except Exception as error:  # noqa: BLE001 - 探针把失败落成证据，不抛裸栈
        check("探针执行完成", False, f"{type(error).__name__}: {error}")
        return finish(1)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    failed = [item for item in report["checks"] if not item["ok"]]
    return finish(0 if not failed else 1)


if __name__ == "__main__":
    sys.exit(main())

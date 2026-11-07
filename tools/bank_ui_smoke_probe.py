# -*- coding: utf-8 -*-
"""bank-ui 真机冒烟（3.6 下架全库查重后的替代探针）。

用法：``.venv/Scripts/python.exe tools/bank_ui_smoke_probe.py <tag>``
（脚本自己在随机端口起隔离服务，跑完关掉）

判据（design §4.4-5/6）：
  1. 左栏点「真题题库」能挂载，页签只剩「题目列表」「待审任务」两个；
  2. 两个页签各点一次都不报错、不空白；
  3. 全程没有对 ``/api/bank/plugins/*/duplicates`` 的请求；
  4. ``/api/plugins`` 里 bank-ui 的 commands 恰为两条；
  5. 后端两条旧路由直接 404（前端不可达之外再加一道）；
  6. 宿主页与插件 iframe 无未捕获 JS 错误。

产出：``.system_generated/bank_ui_smoke_probe/<tag>/probe.toml``（① checks[] + passed/total）
与两张截图。任一判据红即以非零码退出，但 probe.toml 始终落盘。
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

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
PLUGIN_ID = "org.jiuzhang.bank-ui"
ENGINE_ID = "org.jiuzhang.bank-engine"


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


def api_get(base: str, path: str) -> tuple[int, object]:
    try:
        with urllib.request.urlopen(base + path, timeout=15) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "null")
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
    work = ROOT / ".system_generated" / "bank_ui_smoke_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    shots.mkdir(parents=True)
    shutil.copytree(ROOT / "plugins" / PLUGIN_ID, plugins_dir / PLUGIN_ID)
    shutil.copytree(ROOT / "plugins" / ENGINE_ID, plugins_dir / ENGINE_ID)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = "bank-ui-smoke-token"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    report: dict = {
        "tag": tag, "base": base, "checks": [], "passed": 0, "total": 0,
        "console_errors": [], "page_errors": [], "requested_urls": [], "shots": [], "notes": {},
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

        status, discovery = api_get(base, "/api/plugins")
        entry = next((item for item in (discovery or {}).get("plugins", [])
                      if item.get("id") == PLUGIN_ID), None)
        commands = [item.get("id") for item in ((entry or {}).get("commands") or [])]
        report["notes"]["bank_ui_commands"] = commands
        check("底座发现 bank-ui", entry is not None, bool(entry))
        check("bank-ui 只剩两条命令", len(commands) == 2, commands)
        check("查重两条命令已下架",
              "org.jiuzhang.action.data.dedupe_scan" not in commands
              and "org.jiuzhang.action.data.dedupe_merge" not in commands, commands)

        for path, method in (
            (f"/api/bank/plugins/{ENGINE_ID}/duplicates", "GET"),
            (f"/api/bank/plugins/{ENGINE_ID}/duplicates/merge", "POST"),
        ):
            if method == "POST":
                request = urllib.request.Request(base + path, data=b"{}", method=method)
                request.add_header("Content-Type", "application/json")
                try:
                    with urllib.request.urlopen(request, timeout=15) as response:
                        status, body = response.status, response.read().decode("utf-8", "replace")
                except urllib.error.HTTPError as error:
                    status, body = error.code, error.read().decode("utf-8", "replace")
                    error.close()
            else:
                status, body = api_get(base, path)
            check(f"旧路由 {method} {path.rsplit('/api', 1)[-1]} 已下线",
                  status in (404, 405), {"status": status, "body": str(body)[:200]})

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: report["console_errors"].append(message.text)
                    if message.type == "error" else None)
            page.on("pageerror", lambda error: report["page_errors"].append(str(error)))
            page.on("request", lambda request: report["requested_urls"].append(request.url))
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="真题题库").first
            expect(item).to_be_visible(timeout=10000)
            item.click()
            frame = page.frame_locator(".ws-plugin-frame")
            expect(frame.locator(".cb-title")).to_have_text("真题题库", timeout=15000)
            check("bank-ui 挂载", True)

            tabs = frame.locator('[role="tab"]')
            expect(tabs).to_have_count(2, timeout=15000)
            labels = [tabs.nth(index).inner_text().strip() for index in range(2)]
            report["notes"]["tabs"] = labels
            check("页签只剩题目列表与待审任务",
                  any("题目列表" in label for label in labels)
                  and any("待审任务" in label for label in labels), labels)

            list_tab = frame.locator('[role="tab"]', has_text="题目列表").first
            list_tab.click()
            expect(frame.locator(".cb-body .cb-row").first).to_be_visible(timeout=15000)
            first_shot = shots / "list.png"
            page.screenshot(path=str(first_shot))
            report["shots"].append(str(first_shot))
            check("题目列表页有内容", frame.locator(".cb-body .cb-row").count() > 0)

            review_tab = frame.locator('[role="tab"]', has_text="待审任务").first
            review_tab.click()
            expect(frame.locator(".cb-body-review .cb-review").first).to_be_visible(timeout=15000)
            second_shot = shots / "review.png"
            page.screenshot(path=str(second_shot))
            report["shots"].append(str(second_shot))
            check("待审任务页有内容", frame.locator(".cb-body-review").count() > 0)

            list_tab.click()
            expect(frame.locator(".cb-body .cb-row").first).to_be_visible(timeout=15000)
            check("来回切换后列表仍可渲染", True)

            duplicates_hits = [url for url in report["requested_urls"] if "/duplicates" in url]
            check("全程零查重请求", not duplicates_hits, duplicates_hits[:5])
            check("宿主页无 JS 错误", not report["page_errors"], report["page_errors"][:5])
            check("控制台无 error", not report["console_errors"], report["console_errors"][:5])
            browser.close()
    except Exception as error:  # noqa: BLE001 - 探针要把失败落成证据，不抛裸栈
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

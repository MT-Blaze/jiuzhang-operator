# -*- coding: utf-8 -*-
"""题库批量导入导出真机探针（v0.9.0 口径）。

取证口径（军令 #14 阶段四）：
- 控制台「工作区」面板带【导入题目包】与【导出当前题库】两个入口；
- 导出点下去真下载一个 ``.json``，内容是标准交换包，题数与题库一致；
- 导入走真实文件选择器（``<input type=file>`` → base64 → 宿主校验 → 批量写入），
  状态行如实报「已导入 N 题」，题库里真的多了这 N 道；
- 坏包必须被宿主拒掉并报「导入失败」，题库一题不增；
- 全程零 console error / page error。

跑在临时 data 目录里，绝不碰老师自己的题库。

用法：``.venv/Scripts/python.exe tools/bank_io_probe.py <tag>``
"""

from __future__ import annotations

import json
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
PLUGIN_ID = "org.jiuzhang.bank-engine"
TOKEN = "bank-io-probe-token"


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_health(base: str, process: subprocess.Popen) -> None:
    deadline = time.time() + 25
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("服务提前退出：" + (process.stdout.read() if process.stdout else "")[:2000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 25 秒内就绪")


def seed_questions(count: int, offset: int = 0) -> list[dict]:
    return [
        {
            "schema_version": "2.0",
            "id": f"q_probe{index:06d}",
            "type": "fill_blank",
            "stem": f"探针第 {index} 题：解方程 $x^{2}-{index}=0$。",
            "answer": {"kind": "expression", "content": "$x=\\pm 1$", "final": "±1"},
            "difficulty": "L2",
            "extensions": {"org.jiuzhang.core-bank.grade": {"grade": "高一"}},
            "meta": {
                "created_at": "2026-10-24T09:00:00+08:00",
                "updated_at": "2026-10-24T09:00:00+08:00",
                "revision": 1,
                "status": "published",
            },
        }
        for index in range(offset + 1, offset + count + 1)
    ]


def api_total(base: str) -> int:
    url = f"{base}/api/bank/plugins/{PLUGIN_ID}/questions?page_size=1"
    with urllib.request.urlopen(url, timeout=10) as response:
        return int(json.loads(response.read().decode("utf-8"))["total"])


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "bank_io_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    (work / "shots").mkdir(parents=True)

    # 临时题库：老师自己的 data/ 一概不碰
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    seed_dir = plugins_dir / PLUGIN_ID / "bank"
    seed_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql", seed_dir / "schema.sql")
    sys.path.insert(0, str(ROOT))
    from app.core import bank  # noqa: PLC0415

    # 表结构按 plugins_dir() 现取现算（app/core/config.py:93 的 JZO_PLUGINS_DIR 口子），
    # 所以这两个变量必须在进程内调用 bank.* 之前就位——否则 schema.sql 会去默认工作区找。
    os.environ["JZO_DATA_DIR"] = str(data_dir)
    os.environ["JZO_PLUGINS_DIR"] = str(plugins_dir)
    bank.import_documents(PLUGIN_ID, seed_questions(3), reset=True, db_path=seed_dir / "bank.db")

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_LOCAL_TOKEN"] = TOKEN
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    result: dict = {"tag": tag, "checks": [], "console_errors": [], "console_warnings": [],
                    "page_errors": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            page.on("console", lambda m: result["console_errors"].append(m.text)
                    if m.type == "error" else
                    (result["console_warnings"].append(m.text) if m.type == "warning" else None))
            page.on("pageerror", lambda e: result["page_errors"].append(str(e)))
            page.goto(base + "/settings", wait_until="networkidle")

            import_btn = page.locator("#bankImportBtn")
            export_btn = page.locator("#bankExportBtn")
            expect(import_btn).to_be_visible(timeout=15000)
            expect(export_btn).to_be_visible(timeout=15000)
            check("工作区面板带【导入题目包】入口",
                  "导入题目包" in import_btn.inner_text(), {"text": import_btn.inner_text()})
            check("工作区面板带【导出当前题库】入口",
                  "导出当前题库" in export_btn.inner_text(), {"text": export_btn.inner_text()})
            check("文件选择器藏起来（用按钮触发，不裸奔在页面上）",
                  page.locator("#bankImportFile").is_hidden())
            check("状态行初始收起", page.locator("#bankIoStatus").is_hidden())

            # ---- 导出：真下载 ----
            before = api_total(base)
            with page.expect_download(timeout=20000) as download_info:
                export_btn.click()
            download = download_info.value
            target = work / "exported-bank.json"
            download.save_as(str(target))
            bundle = json.loads(target.read_text(encoding="utf-8"))
            check("导出点下去真下载了一个 .json 文件",
                  download.suggested_filename.endswith(".json"), {"name": download.suggested_filename})
            check("导出内容是标准交换包",
                  bundle.get("format") == "jiuzhang.question.bundle" and bundle.get("count") == len(
                      bundle.get("questions") or []), {"format": bundle.get("format")})
            check("导出题数与题库一致", bundle.get("count") == before,
                  {"count": bundle.get("count"), "bank": before})
            expect(page.locator("#bankIoStatus")).to_be_visible(timeout=10000)
            status_text = page.locator("#bankIoStatus").inner_text()
            check("导出后状态行如实报已导出", "已导出" in status_text, {"text": status_text})
            page.screenshot(path=str(work / "shots" / "bank-export.png"))

            # ---- 导入：真文件选择器 ----
            pack = work / "pack.json"
            pack.write_text(
                json.dumps({"questions": seed_questions(2, offset=900)}, ensure_ascii=False),
                encoding="utf-8",
            )
            with page.expect_file_chooser(timeout=10000) as chooser_info:
                import_btn.click()
            chooser_info.value.set_files(str(pack))
            expect(page.locator("#bankIoStatus")).to_contain_text("已导入", timeout=20000)
            import_status = page.locator("#bankIoStatus").inner_text()
            check("导入后状态行如实报已导入 N 题", "已导入" in import_status, {"text": import_status})
            after = api_total(base)
            check("导入的题真进了题库", after == before + 2, {"before": before, "after": after})
            page.screenshot(path=str(work / "shots" / "bank-import.png"))

            # ---- 坏包必须被拒 ----
            broken = work / "broken.json"
            broken.write_text("{ 这不是 JSON", encoding="utf-8")
            noise_mark = len(result["console_errors"])
            with page.expect_file_chooser(timeout=10000) as chooser_info:
                import_btn.click()
            chooser_info.value.set_files(str(broken))
            expect(page.locator("#bankIoStatus")).to_contain_text("导入失败", timeout=20000)
            broken_status = page.locator("#bankIoStatus").inner_text()
            check("坏包被拒并报「导入失败」", "导入失败" in broken_status, {"text": broken_status})
            check("坏包一题不增", api_total(base) == after, {"after": after})
            # 坏包是宿主如实回的 400，浏览器会把这次资源加载失败记成 console error：
            # 这是负向用例故意触发的，单列出来，不与真报错混在一起。
            result["expected_http_noise"] = result["console_errors"][noise_mark:]
            del result["console_errors"][noise_mark:]

            browser.close()
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = (all(item["ok"] for item in result["checks"])
                    and not result["page_errors"] and not result["console_errors"])
    (work / "probe.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(("PASS" if result["ok"] else "FAIL") + f" · {len(result['checks'])} 项 · {work}")
    for item in result["checks"]:
        print(("  ok " if item["ok"] else "  XX ") + item["name"])
    if result["page_errors"]:
        print("页面异常：" + " | ".join(result["page_errors"][:5]))
    if result["console_errors"]:
        print("控制台报错：" + " | ".join(result["console_errors"][:5]))
    if result["console_warnings"]:
        print("控制台告警：" + " | ".join(result["console_warnings"][:5]))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

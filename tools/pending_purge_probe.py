# -*- coding: utf-8 -*-
"""一键剔除本批次重复题真机取证（军令 #31 · 3.5）。

用法：``.venv/Scripts/python.exe tools/pending_purge_probe.py <tag>``

隔离口径：editor / 引擎 / 题库视图复制进独立插件目录，另起随机端口与独立
``JZO_DATA_DIR``，不碰本机 ``data/``。探针自己往中转站塞两批题（一批 4 道、
其中 2 道逐字重复；另一批 1 道独题），随后**只走界面**：批次列表点
「剔除重复」→ 弹窗清单 → 执行剔除，再回接口核对池子与主库。

判据：
1. 批次卡片右侧出现「剔除重复」，弹窗打开后清单是批内重复组，默认勾选 1 道；
2. 执行后弹窗关闭、卡片「待审 3 / 3」、底栏报「剔除 1 道」；
3. 接口侧池子只剩 3 道、被剔的 p_ id 消失，另一批 1 道原样保留；
4. 主库题数前后不变（剔除只碰中转站）；
5. 全程宿主页无未捕获 JS 错误，写口返回 200。
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

from app.core import toml_io, wire  # noqa: E402

import os
import re
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
EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
BANK_UI_ID = BANK_ID
TOKEN = "pending-purge-probe-token"
CANVAS = "#wsPanel_plugin_org_jiuzhang_editor .ws-plugin-frame"
CARD_RE = re.compile(r"待审\s*(\d+)\s*/\s*(\d+)")


def _doc(stem: str, answer: str) -> dict:
    return {
        "schema_version": "2.0",
        "type": "single_choice",
        "stem": stem,
        "options": [
            {"key": "A", "content": "$0$"},
            {"key": "B", "content": "$1$"},
        ],
        "answer": {"kind": "choice", "choice_keys": [answer], "final": answer},
        "solution": "解析：按定义直接计算。",
        "difficulty": "L1",
        "grade": "高一",
        "tags": ["探针剔除"],
        "source": {"paper_title": "探针剔除卷", "question_no": "1", "year": 2024,
                   "exam_type": "一模"},
    }


DUP_A = _doc("探针剔除重复题：函数 $f(x)=x^2$ 的最小值是（  ）", "A")
DUP_B = _doc("探针剔除重复题：函数 $f(x)=x^2$ 的最小值是（  ）", "A")
ALONE = _doc("探针保留题：数列 $a_n=n$ 的第三项是（  ）", "B")
OTHER = _doc("探针另一批独题：向量 $\\vec a=(1,2)$ 的模是（  ）", "B")


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, wire.loads(payload or "{}")
        except wire.JSONDecodeError:
            return error.code, {"raw": payload}


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
        payload = error.read().decode("utf-8")
        error.close()
        try:
            return error.code, wire.loads(payload or "{}")
        except wire.JSONDecodeError:
            return error.code, {"raw": payload}


def wait_health(base: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        if process.poll() is not None:
            output = log_path.read_text(encoding="utf-8", errors="replace")
            raise RuntimeError("服务提前退出：\n" + output[:3000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 40 秒内就绪")


def cards(base: str) -> list[dict]:
    _, data = http_json(base + "/api/pending/batches")
    rows = data.get("batches")
    return rows if isinstance(rows, list) else []


def items(base: str, batch_id: str) -> list[dict]:
    _, data = http_json(base + f"/api/pending/batches/{batch_id}/questions")
    rows = data.get("items")
    return rows if isinstance(rows, list) else []


def bank_total(base: str) -> int:
    _, data = http_json(base + f"/api/bank/plugins/{BANK_ID}/stats")
    return int(data.get("total") or 0)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "pending_purge_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    for plugin_id in (EDITOR_ID, BANK_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["JZO_RESTART_DISABLED"] = "1"
    server_log = work / "server.log"
    log_handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": [], "metrics": {}, "shots": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process, server_log)
        total_before = bank_total(base)

        # 两批题：主角批次 4 道（两道逐字重复），旁证批次 1 道独题。
        status_main, body_main = http_post(
            base + "/api/pending/batches",
            {"questions": [{"question": DUP_A}, {"question": DUP_B},
                           {"question": ALONE}],
             "origin": "probe.purge"})
        # DUP_B 与 DUP_A 同批同指纹；再塞一道独题把本批撑到 4 道。
        status_extra, body_extra = http_post(
            base + "/api/pending/batches",
            {"questions": [{"question": _doc("探针第四题：方程 $x+1=2$ 的解是（  ）", "B")}],
             "batch_id": body_main.get("batch_id"), "origin": "probe.purge"})
        status_side, body_side = http_post(
            base + "/api/pending/batches",
            {"questions": [{"question": OTHER}], "origin": "probe.purge"})
        batch_id = str(body_main.get("batch_id") or "")
        side_batch = str(body_side.get("batch_id") or "")
        seeds_ok = (status_main == 201 and status_extra == 201 and status_side == 201
                    and bool(batch_id) and bool(side_batch) and side_batch != batch_id)
        seeded = items(base, batch_id) if seeds_ok else []
        side_before = items(base, side_batch) if seeds_ok else []
        check("两批入池（主角 4 道含 1 组重复、旁证 1 道）",
              seeds_ok and len(seeded) == 4 and len(side_before) == 1,
              {"main": status_main, "extra": status_extra, "side": status_side,
               "seeded": len(seeded), "side_before": len(side_before)})
        if not seeds_ok or len(seeded) != 4:
            raise RuntimeError("入池形状不对，后续界面判据无从谈起")

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type == "error" else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url))
                if response.status >= 400 else None)
            write_status: list[str] = []
            page.on("response", lambda response: write_status.append(
                "%s %s" % (response.status, response.url))
                if "/purge-duplicates" in response.url else None)
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()

            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=20000)
            row = canvas.locator('.ed-batch-row[data-batch="%s"]' % batch_id)
            expect(row).to_be_visible(timeout=20000)
            purge = row.locator(".ed-batch-purge")
            expect(purge).to_be_visible(timeout=10000)
            check("批次卡片右侧有「剔除重复」", purge.inner_text().strip() == "剔除重复",
                  {"label": purge.inner_text().strip()})

            purge.click()
            modal = canvas.locator("#epBatchPurgeModal")
            expect(modal).to_be_visible(timeout=20000)
            groups = canvas.locator(".ep-purge-group")
            expect(groups).to_have_count(1, timeout=20000)
            check("弹窗列出 1 组批内重复", True,
                  {"groups": groups.count(),
                   "summary": canvas.locator("#epBatchPurgeSummary").inner_text().strip()})
            badge = canvas.locator(".ep-purge-badge").first.inner_text().strip()
            checked = canvas.locator(".ep-purge-item input:checked").count()
            ok_button = canvas.locator("#epBatchPurgeOk")
            check("重复组标「批内重复」且默认勾选 1 道",
                  badge == "批内重复" and checked == 1
                  and "当前勾选 1 道" in ok_button.inner_text(),
                  {"badge": badge, "checked": checked, "button": ok_button.inner_text()})
            check("保留行写明录入序", "保留录入序" in canvas.locator(".ep-purge-keep").first.inner_text(),
                  {"keep": canvas.locator(".ep-purge-keep").first.inner_text()})
            shot_modal = shots / "purge-modal.png"
            page.screenshot(path=str(shot_modal))
            result["shots"].append(str(shot_modal))

            ok_button.click()
            expect(modal).to_be_hidden(timeout=20000)
            expect(row.locator(".ed-batch-right")).to_contain_text("待审 3 / 3", timeout=20000)
            dock = page.locator("#wsDockLog")
            deadline = time.time() + 15
            logged = ""
            while time.time() < deadline:
                logged = dock.inner_text() if dock.count() else ""
                if "已从批次 #%s 剔除 1 道重复题" % batch_id in logged:
                    break
                page.wait_for_timeout(150)
            card_text = "".join(row.locator(".ed-batch-right").inner_text().split())
            check("执行后卡片变「待审 3 / 3」且底栏留痕",
                  card_text == "待审3/3"
                  and "已从批次 #%s 剔除 1 道重复题" % batch_id in logged,
                  {"card": card_text,
                   "dock": [line for line in logged.splitlines()
                            if "剔除" in line or "批次" in line][-4:]})
            shot_done = shots / "purge-done.png"
            page.screenshot(path=str(shot_done))
            result["shots"].append(str(shot_done))

            check("写口返回 200", bool(write_status)
                  and all(entry.startswith("200 ") for entry in write_status),
                  {"calls": write_status})

        after = items(base, batch_id)
        after_ids = {str(entry.get("id") or "") for entry in after}
        dropped = sorted({str(entry.get("id") or "") for entry in seeded} - after_ids)
        card = next((c for c in cards(base) if c.get("batch_id") == batch_id), {})
        side_after = items(base, side_batch)
        total_after = bank_total(base)
        check("池子只剩 3 道、被剔的 p_ id 已消失",
              len(after) == 3 and len(dropped) == 1 and dropped[0].startswith("p_"),
              {"left": len(after), "dropped": dropped})
        check("批次账本 total / pending_count 同步为 3",
              int(card.get("total") or 0) == 3 and int(card.get("pending_count") or 0) == 3,
              {"card": card})
        check("另一批 1 道独题原样保留",
              len(side_after) == 1
              and str(side_after[0].get("id")) == str(side_before[0].get("id")),
              {"side_before": side_before[0].get("id") if side_before else None,
               "side_after": [entry.get("id") for entry in side_after]})
        check("主库题数前后不变（剔除只碰中转站）", total_after == total_before,
              {"before": total_before, "after": total_after})
        check("宿主页无未捕获 JS 错误", not result["page_errors"],
              {"page_errors": result["page_errors"][:5]})
    except Exception as exc:  # noqa: BLE001 - 探针要把异常也写进回传单
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log_handle.close()

    passed = sum(1 for entry in result["checks"] if entry["ok"])
    total = len(result["checks"])
    result["passed"] = passed
    result["total"] = total
    report = work / "probe.toml"
    report.write_text(toml_io.dumps(result), encoding="utf-8")
    print(wire.dumps({"tag": tag, "passed": passed, "total": total,
                      "error": result.get("error"), "report": str(report)},
                     ensure_ascii=False))
    for entry in result["checks"]:
        if not entry["ok"]:
            print("FAIL:", entry["name"], wire.dumps(entry["detail"], ensure_ascii=False)[:300])
    return 0 if passed == total and total > 0 and not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())

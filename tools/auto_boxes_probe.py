# -*- coding: utf-8 -*-
"""原卷自动切分框真机探针：模拟1.pdf → 19 个绿框 → 微调 / 确认切分 / 松手切题。

用法：``.venv/Scripts/python.exe tools/auto_boxes_probe.py <tag>``

隔离：复制 editor 插件到临时插件目录，另起端口与独立数据目录；试卷从
``E:/jiuzhang/testdata/20261105/模拟1.pdf`` 读，不写开发者 data/。
"""

from __future__ import annotations

import base64
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
PAPER = ROOT.parent / "testdata" / "20261105" / "模拟1.pdf"
EDITOR_ID = "org.jiuzhang.editor"
TOKEN = "auto-boxes-probe-token"
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


def http_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def http_post(url: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-JZO-Token": TOKEN},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        error.close()
        raise RuntimeError("POST %s → %s %s" % (url, error.code, detail[:800])) from error


def batch_items(base: str, batch_id: str) -> dict:
    return http_json(base + "/api/pending/batches/" + batch_id + "/questions")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "auto_boxes_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    for folder in (data_dir, plugins_dir, shots):
        folder.mkdir(parents=True)
    shutil.copytree(ROOT / "plugins" / EDITOR_ID, plugins_dir / EDITOR_ID)

    if not PAPER.is_file():
        print("找不到试卷：" + str(PAPER))
        return 2

    port = free_port()
    base = "http://127.0.0.1:%d" % port
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = TOKEN
    env["JZO_RESTART_DISABLED"] = "1"
    env["JZO_POOL_ADMIT_DISABLED"] = "1"
    server_log = work / "server.log"
    log_handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "info", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "http_failures": [], "metrics": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    try:
        wait_health(base, process, server_log)
        payload = {"files": [{
            "name": "模拟1.pdf",
            "data_url": "data:application/pdf;base64,"
                        + base64.b64encode(PAPER.read_bytes()).decode("ascii"),
        }]}
        staged = http_post(base + "/api/ingest/files", payload)
        batch_id = str(staged.get("batch_id") or "")
        check("01 批次已建立", bool(batch_id), batch_id)

        deadline = time.time() + 90
        pages: list[dict] = []
        items: list[dict] = []
        while time.time() < deadline:
            detail = batch_items(base, batch_id)
            pages = detail.get("page_images") or []
            items = detail.get("items") or []
            total_regions = sum(len(page.get("regions") or []) for page in pages)
            if len(pages) >= 5 and total_regions >= 19:
                break
            time.sleep(0.3)
        total_regions = sum(len(page.get("regions") or []) for page in pages)
        numbers = [region.get("no") for page in pages for region in (page.get("regions") or [])]
        result["metrics"].update({
            "pages": len(pages),
            "regions": total_regions,
            "numbers": numbers,
            "initial_pending": len(items),
        })
        check("02 后端返回 5 页页图", len(pages) == 5, len(pages))
        check("03 后端共 19 个题块坐标", total_regions == 19, total_regions)
        check("04 题号连续 1..19", numbers == list(range(1, 20)), numbers)
        check("05 纯图批次不落占位题", items == [], len(items))
        if pages:
            first = pages[0]
            check("06 页图带像素尺寸",
                  bool(first.get("width")) and bool(first.get("height")),
                  [first.get("width"), first.get("height")])

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.on("response", lambda response: result["http_failures"].append(
                "%s %s" % (response.status, response.url)) if response.status >= 400 else None)
            page.goto(base + "/workspace", wait_until="networkidle")

            entry = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(entry).to_be_visible(timeout=15000)
            entry.click()
            canvas = page.frame_locator(CANVAS)
            expect(canvas.locator("#edRoot")).to_be_visible(timeout=25000)

            card = canvas.locator(".ed-batch-row").first
            expect(card).to_be_visible(timeout=20000)
            card.click()

            expect(canvas.locator(".ed-page-cell").first).to_be_visible(timeout=25000)
            expect(canvas.locator(".ed-auto-box").first).to_be_visible(timeout=20000)
            page.wait_for_timeout(800)

            box_count = canvas.locator(".ed-auto-box").count()
            per_page = canvas.locator(".ed-page-cell").evaluate_all(
                "nodes => nodes.map(node => node.querySelectorAll('.ed-auto-box').length)")
            result["metrics"]["dom_boxes"] = box_count
            result["metrics"]["boxes_per_page"] = per_page
            check("07 左栏自动画出 19 个绿框", box_count == 19, box_count)
            check("08 每页框数与后端一致", per_page == [5, 7, 4, 3, 0], per_page)

            style = canvas.locator(".ed-auto-box").first.evaluate(
                "node => { var s = getComputedStyle(node);"
                " return [s.borderTopStyle, s.borderTopColor, s.borderTopWidth, s.position]; }")
            result["metrics"]["box_style"] = style
            check("09 绿框是 2px 绿虚线且绝对定位",
                  style[0] == "dashed" and style[1] == "rgb(47, 158, 90)"
                  and style[2] == "2px" and style[3] == "absolute", style)

            numbers_dom = canvas.locator(".ed-auto-box").evaluate_all(
                "nodes => nodes.map(node => Number(node.getAttribute('data-no')))")
            check("10 框上标出第 N 题", numbers_dom == list(range(1, 20)), numbers_dom)
            buttons = canvas.locator(".ed-auto-box-split").all_inner_texts()
            check("11 每个框都有确认切分按钮",
                  len(buttons) == 19 and buttons[0] == "确认切分", buttons[:3])

            page.screenshot(path=str(shots / "01_auto_boxes.png"), full_page=False)

            # ---------- 放大镜：运行时量半径与偏移 ----------
            hook = """() => {
              window.__arcLog = [];
              window.__probeMouse = null;
              document.addEventListener("mousemove", function (event) {
                window.__probeMouse = {x: event.clientX, y: event.clientY};
              }, true);
              var proto = CanvasRenderingContext2D.prototype;
              if (!proto.__probePatched) {
                var original = proto.arc;
                proto.arc = function (x, y, r, start, end, anticlockwise) {
                  if (r >= 20 && r <= 200) {
                    window.__arcLog.push({x: x, y: y, r: r, at: Date.now()});
                  }
                  return original.call(this, x, y, r, start, end, anticlockwise);
                };
                proto.__probePatched = true;
              }
              return true;
            }"""
            canvas.locator("#edRoot").evaluate(hook)

            canvas.locator(".ed-page-cell").first.locator(".ed-img-crop-btn").click()
            crop_canvas = canvas.locator(".ed-crop-canvas").first
            expect(crop_canvas).to_be_visible(timeout=20000)
            page.wait_for_timeout(1200)
            crop_box = crop_canvas.bounding_box()
            check("12 手动切图台已铺开", bool(crop_box), crop_box)
            assert crop_box is not None
            target_x = crop_box["x"] + crop_box["width"] * 0.35
            target_y = crop_box["y"] + crop_box["height"] * 0.3
            page.mouse.move(target_x, target_y)
            page.wait_for_timeout(400)
            arcs = canvas.locator("#edRoot").evaluate("() => window.__arcLog || []")
            lens = arcs[-1] if arcs else {}
            # 镜心与指针都按 iframe 视口坐标比，主页面坐标隔着 iframe 偏移，不能混算。
            pointer = canvas.locator("#edRoot").evaluate("() => window.__probeMouse || {}")
            result["metrics"]["lens"] = lens
            result["metrics"]["pointer"] = pointer
            check("13 放大镜直径不超过 120px", bool(lens) and lens.get("r", 999) * 2 <= 120, lens)
            check("14 放大镜半径 60 / 1.2 倍",
                  bool(lens) and abs(float(lens.get("r", 0)) - 60) < 0.5, lens)
            offset_x = abs(float(lens.get("x", 0)) - float(pointer.get("x", 0))) if lens else 0
            offset_y = abs(float(lens.get("y", 0)) - float(pointer.get("y", 0))) if lens else 0
            check("15 镜心与指针错开，不压住光标下的字",
                  bool(pointer) and 70 <= offset_x <= 90 and 70 <= offset_y <= 90,
                  {"offset_x": offset_x, "offset_y": offset_y})
            page.screenshot(path=str(shots / "02_lens.png"))

            # ---------- 拖拽松手即切：走鼠标抬起，验证不再无响应 ----------
            start_x = crop_box["x"] + crop_box["width"] * 0.2
            start_y = crop_box["y"] + crop_box["height"] * 0.35
            end_x = crop_box["x"] + crop_box["width"] * 0.55
            end_y = crop_box["y"] + crop_box["height"] * 0.5
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move((start_x + end_x) / 2, (start_y + end_y) / 2, steps=6)
            page.mouse.move(end_x, end_y, steps=6)
            page.mouse.up()

            items_after_drag = []
            deadline = time.time() + 30
            while time.time() < deadline:
                items_after_drag = batch_items(base, batch_id).get("items") or []
                if len(items_after_drag) == 1:
                    break
                page.wait_for_timeout(250)
            result["metrics"]["after_drag"] = len(items_after_drag)
            check("16 手动框选松手即生成新待审题", len(items_after_drag) == 1,
                  len(items_after_drag))
            if items_after_drag:
                doc = items_after_drag[0].get("question") or {}
                images = doc.get("images") or []
                check("17 新题带裁出来的配图",
                      bool(images and images[0].get("uri")), images)
            expect(canvas.locator(".ed-auto-box").first).to_be_visible(timeout=20000)

            # ---------- 微调 + 确认切分 ----------
            first_box = canvas.locator(".ed-auto-box").first
            before = first_box.evaluate(
                "node => [node.style.left, node.style.top, node.style.width, node.style.height]")
            first_box.hover()
            page.wait_for_timeout(150)
            handle = first_box.locator('.ed-auto-handle[data-handle="e"]')
            handle_box = handle.bounding_box()
            check("18 悬停后出现微调手柄", bool(handle_box), handle_box)
            assert handle_box is not None
            hx = handle_box["x"] + handle_box["width"] / 2
            hy = handle_box["y"] + handle_box["height"] / 2
            page.mouse.move(hx, hy)
            page.mouse.down()
            page.mouse.move(hx + 20, hy, steps=8)
            page.mouse.up()
            page.wait_for_timeout(300)
            after = first_box.evaluate(
                "node => [node.style.left, node.style.top, node.style.width, node.style.height]")
            result["metrics"]["box_before"] = before
            result["metrics"]["box_after"] = after
            check("19 拖手柄微调了框的宽高", before != after, {"before": before, "after": after})
            page.screenshot(path=str(shots / "03_adjusted.png"))

            first_box.hover()
            page.wait_for_timeout(150)
            first_box.locator(".ed-auto-box-split").click()
            items_after_confirm = []
            deadline = time.time() + 30
            while time.time() < deadline:
                items_after_confirm = batch_items(base, batch_id).get("items") or []
                if len(items_after_confirm) == 2:
                    break
                page.wait_for_timeout(250)
            result["metrics"]["after_confirm"] = len(items_after_confirm)
            check("20 确认切分再生成一道新待审题", len(items_after_confirm) == 2,
                  len(items_after_confirm))
            page.wait_for_timeout(600)
            states = canvas.locator(".ed-auto-box").evaluate_all(
                "nodes => nodes.map(node => [node.getAttribute('data-no'),"
                " node.getAttribute('data-done') || ''])")
            result["metrics"]["box_states"] = states[:3]
            check("21 已切的框标成已完成",
                  any(state[1] == "on" for state in states), states[:3])
            page.screenshot(path=str(shots / "04_after_confirm.png"), full_page=False)

            result["metrics"]["console_errors"] = result["console_errors"]
            result["metrics"]["page_errors"] = result["page_errors"]
            check("22 全流程无页面脚本错误", not result["page_errors"], result["page_errors"])
            browser.close()
    except Exception as error:  # noqa: BLE001 - 探针要把失败本身落盘，不能裸崩
        result["error"] = repr(error)
        check("探针执行未抛异常", False, str(error))
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
        log_handle.close()

    passed = sum(1 for item in result["checks"] if item["ok"])
    result["passed"] = passed
    result["total"] = len(result["checks"])
    result["ok"] = passed == len(result["checks"])
    (work / "probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for item in result["checks"]:
        print(("PASS " if item["ok"] else "FAIL ") + item["name"] + " " + str(item.get("detail")))
    print("probe: %d/%d · %s" % (passed, len(result["checks"]),
                                 "PASS" if result["ok"] else "FAIL"))
    print("证据：" + str(work / "probe.json"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

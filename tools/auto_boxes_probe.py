# -*- coding: utf-8 -*-
"""原卷自动切分框真机探针：模拟1.pdf → 19 个绿框 + 19 道待审题。

一次跑通整条闭环：解析完自动裁图入池、中栏排好题、右栏显示元数据，
老师拖绿框微调时坐标回写并重切题图，手动补框仍能再切一道。

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
PANEL = "#wsContextSlot .ws-context-frame"


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


def item_image_uri(detail: dict, index: int = 0) -> str:
    items = detail.get("items") or []
    if index >= len(items):
        return ""
    images = (items[index].get("question") or {}).get("images") or []
    return str(images[0].get("uri") or "") if images else ""


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
    # 生产口径：不再用 JZO_POOL_ADMIT_DISABLED 遮住自动抽走——原卷大图批次本来就
    # 只查不抽，19 个框必须自己站住 19 道待审题。
    env.pop("JZO_POOL_ADMIT_DISABLED", None)
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

        deadline = time.time() + 120
        pages: list[dict] = []
        items: list[dict] = []
        while time.time() < deadline:
            detail = batch_items(base, batch_id)
            pages = detail.get("page_images") or []
            items = detail.get("items") or []
            total_regions = sum(len(page.get("regions") or []) for page in pages)
            if len(pages) >= 5 and total_regions >= 19 and len(items) >= 19:
                break
            time.sleep(0.3)
        total_regions = sum(len(page.get("regions") or []) for page in pages)
        numbers = [region.get("no") for page in pages for region in (page.get("regions") or [])]
        linked = [bool(region.get("pending_id")) for page in pages
                  for region in (page.get("regions") or [])]
        result["metrics"].update({
            "pages": len(pages),
            "regions": total_regions,
            "numbers": numbers,
            "initial_pending": len(items),
            "linked_regions": sum(1 for flag in linked if flag),
        })
        check("02 后端返回 5 页页图", len(pages) == 5, len(pages))
        check("03 后端共 19 个题块坐标", total_regions == 19, total_regions)
        check("04 题号连续 1..19", numbers == list(range(1, 20)), numbers)
        check("05 解析完成即生成 19 道待审题", len(items) == 19, len(items))
        check("06 每个框都绑定了一道待审题", all(linked) and len(linked) == 19,
              result["metrics"]["linked_regions"])
        first_images = ((items[0].get("question") or {}).get("images") or []) if items else []
        check("07 待审题自带切好的题图",
              len(first_images) == 1
              and str(first_images[0].get("uri") or "").startswith("/static/pending/pimg_"),
              first_images)
        if pages:
            first = pages[0]
            check("08 页图带像素尺寸",
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
            batch_pending = card.locator(".ed-batch-num").first.inner_text()
            batch_total = card.locator(".ed-batch-total").first.inner_text()
            result["metrics"]["batch_card"] = [batch_pending, batch_total]
            check("09a 批次卡待审数与总数都是 19", batch_pending == "19" and batch_total == "19",
                  result["metrics"]["batch_card"])
            card.click()

            expect(canvas.locator(".ed-page-cell").first).to_be_visible(timeout=25000)
            expect(canvas.locator(".ed-auto-box").first).to_be_visible(timeout=20000)
            page.wait_for_timeout(800)

            box_count = canvas.locator(".ed-auto-box").count()
            per_page = canvas.locator(".ed-page-cell").evaluate_all(
                "nodes => nodes.map(node => node.querySelectorAll('.ed-auto-box').length)")
            result["metrics"]["dom_boxes"] = box_count
            result["metrics"]["boxes_per_page"] = per_page
            check("09 左栏自动画出 19 个绿框", box_count == 19, box_count)
            check("10 每页框数与后端一致", per_page == [5, 7, 4, 3, 0], per_page)

            first_box = canvas.locator(".ed-auto-box").first
            style = first_box.evaluate(
                "node => { var s = getComputedStyle(node);"
                " return [s.borderTopStyle, s.borderTopColor, s.borderTopWidth, s.position,"
                " node.getAttribute('data-pending') || '']; }")
            result["metrics"]["box_style"] = style
            check("11 已入池的框是 2px 实线绿框且绝对定位",
                  style[0] == "solid" and style[1] == "rgb(47, 158, 90)"
                  and style[2] == "2px" and style[3] == "absolute"
                  and style[4] == "on", style)

            numbers_dom = canvas.locator(".ed-auto-box").evaluate_all(
                "nodes => nodes.map(node => Number(node.getAttribute('data-no')))")
            chips = canvas.locator(".ed-auto-box-no").all_inner_texts()
            check("12 框上常显题号 1..19",
                  numbers_dom == list(range(1, 20))
                  and chips == [str(number) for number in range(1, 20)],
                  [numbers_dom[:3], chips[:3]])
            buttons = canvas.locator(".ed-auto-box-split").evaluate_all(
                "nodes => nodes.map(node => [node.textContent, node.disabled])")
            check("13 已入池的框标成『已入池』且按钮禁用",
                  len(buttons) == 19 and buttons[0] == ["已入池", True], buttons[:3])

            source_cells = canvas.locator("#edSourceBody .ed-src-area").count()
            render_blocks = canvas.locator("#edRenderBody .ed-q-block").count()
            first_block_image = canvas.locator("#edRenderBody .ed-q-image img").count()
            result["metrics"].update({
                "source_cells": source_cells,
                "render_blocks": render_blocks,
                "render_images": first_block_image,
            })
            check("14 中栏自动排好 19 道题的源码行", source_cells == 19, source_cells)
            check("15 右栏渲染 19 道题且带题图",
                  render_blocks == 19 and first_block_image == 19,
                  [render_blocks, first_block_image])

            # ---------- 只读信息条：待审进度 + 原卷题号 ----------
            strips = canvas.locator("#edRenderBody .ed-q-meta").evaluate_all(
                "nodes => nodes.map(node => node.textContent)")
            first_parts = canvas.locator("#edRenderBody .ed-q-block").first.locator(
                ".ed-q-meta-item").all_inner_texts()
            fifth_parts = canvas.locator("#edRenderBody .ed-q-block").nth(4).locator(
                ".ed-q-meta-item").all_inner_texts()
            num_spans = canvas.locator("#edRenderBody .ed-num").count()
            first_stem = canvas.locator("#edRenderBody .ed-q-stem").first.inner_text()
            result["metrics"]["meta_strips"] = {"count": len(strips), "first": first_parts,
                                                "fifth": fifth_parts,
                                                "ed_num": num_spans}
            check("15a 每道题都有只读信息条且首格是进度+原卷题号",
                  len(strips) == 19 and first_parts[:1] == ["1 / 19 (原卷第1题)"]
                  and fifth_parts[:1] == ["5 / 19 (原卷第5题)"],
                  result["metrics"]["meta_strips"])
            check("15b 渲染区没有自增序号",
                  num_spans == 0 and not first_stem.startswith("1."),
                  {"ed_num": num_spans, "stem": first_stem[:80]})

            # ---------- 文字与公式：源码是真题干，右栏真的渲染了 MathJax ----------
            source_areas = canvas.locator("#edSourceBody .ed-src-area")
            first_source = source_areas.first.input_value()
            sources = source_areas.evaluate_all(
                "nodes => nodes.map(node => node.value)")
            filled = sum(1 for text in sources if "自动切题" not in text and text.strip())
            math_count = canvas.locator("#edRenderBody mjx-container").count()
            first_render = canvas.locator("#edRenderBody .ed-q-block").first.inner_text()
            result["metrics"]["source"] = {
                "filled": filled,
                "first": first_source[:400],
                "math": math_count,
            }
            check("16 中栏源码填的是真正题干，不是占位提示",
                  "已知集合" in first_source and "\\pi" in first_source
                  and "自动切题" not in first_source, first_source[:160])
            check("17 选择题源码带 choices 选项",
                  "\\begin{choices}" in first_source and "\\item" in first_source,
                  first_source[:240])
            check("18 19 道题的源码都填上了文字", filled == 19, filled)
            check("19 右栏渲染出 MathJax 公式", math_count > 0, math_count)
            check("20 右栏第一题显示题干文字",
                  "已知集合" in first_render, first_render[:160])

            panel = page.frame_locator(PANEL)
            expect(panel.locator("#epRoot")).to_be_visible(timeout=20000)
            src_name = panel.locator("#epSrcName").inner_text()
            head_no = panel.locator("#epHeadNo").inner_text()
            question_no = panel.locator("#epQuestionNo").input_value()
            result["metrics"]["panel"] = {
                "src": src_name, "head_no": head_no, "question_no": question_no}
            check("21 右侧辅助栏显示批次元数据与当前题号",
                  "模拟1" in src_name and "第 1 题" in head_no and question_no == "1",
                  result["metrics"]["panel"])

            page.screenshot(path=str(shots / "01_auto_boxes.png"), full_page=False)

            # ---------- 拖绿框微调：坐标回写 + 题图重切 ----------
            detail_before = batch_items(base, batch_id)
            old_x = detail_before["page_images"][0]["regions"][0]["x"]
            old_uri = item_image_uri(detail_before)
            drag = canvas.locator(".ed-auto-box").first.bounding_box()
            check("22 第一个绿框可拖拽（有可见尺寸）", bool(drag), drag)
            assert drag is not None
            center_x = drag["x"] + drag["width"] / 2
            center_y = drag["y"] + drag["height"] / 2
            page.mouse.move(center_x, center_y)
            page.mouse.down()
            page.mouse.move(center_x + 30, center_y, steps=8)
            page.mouse.up()

            new_x = old_x
            new_uri = old_uri
            deadline = time.time() + 30
            while time.time() < deadline:
                detail_now = batch_items(base, batch_id)
                pages_now = detail_now.get("page_images") or []
                if pages_now and (pages_now[0].get("regions") or []):
                    new_x = pages_now[0]["regions"][0]["x"]
                new_uri = item_image_uri(detail_now)
                if new_x != old_x and new_uri and new_uri != old_uri:
                    break
                page.wait_for_timeout(300)
            result["metrics"]["regions_after_drag"] = {
                "before": old_x, "after": new_x,
                "image_before": old_uri, "image_after": new_uri}
            # 拖的是缩略图上的框：30 个屏幕像素折回页图像素是一大段位移，
            # 只挪零点几像素说明手势被手柄或按钮吃掉了，不能算回写成功。
            check("23 拖框后新坐标回写到批次页图", new_x - old_x >= 20,
                  {"before": old_x, "after": new_x})
            check("24 拖框后题图已重切", bool(new_uri) and new_uri != old_uri,
                  {"before": old_uri, "after": new_uri})
            check("25 微调不会多出或少掉题",
                  len(batch_items(base, batch_id).get("items") or []) == 19,
                  len(batch_items(base, batch_id).get("items") or []))
            page.screenshot(path=str(shots / "02_adjusted.png"))

            # ---------- 手动补框：松手即切，与自动题共用同一条通道 ----------
            crop_button = canvas.locator(".ed-page-cell .ed-img-crop-btn").first
            expect(crop_button).to_be_visible(timeout=20000)
            crop_button.click()
            crop_canvas = canvas.locator(".ed-crop-canvas").first
            expect(crop_canvas).to_be_visible(timeout=20000)
            page.wait_for_timeout(900)
            crop_box = crop_canvas.bounding_box()
            check("26 手动切图台已铺开", bool(crop_box), crop_box)
            assert crop_box is not None
            start_x = crop_box["x"] + crop_box["width"] * 0.2
            start_y = crop_box["y"] + crop_box["height"] * 0.35
            end_x = crop_box["x"] + crop_box["width"] * 0.55
            end_y = crop_box["y"] + crop_box["height"] * 0.5
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move((start_x + end_x) / 2, (start_y + end_y) / 2, steps=6)
            page.mouse.move(end_x, end_y, steps=6)
            page.mouse.up()

            items_after_manual = []
            deadline = time.time() + 30
            while time.time() < deadline:
                items_after_manual = batch_items(base, batch_id).get("items") or []
                if len(items_after_manual) == 20:
                    break
                page.wait_for_timeout(250)
            result["metrics"]["after_manual"] = len(items_after_manual)
            check("27 手动框选再生成一道新待审题", len(items_after_manual) == 20,
                  len(items_after_manual))
            manual_image = item_image_uri(batch_items(base, batch_id))
            check("28 新题带裁出来的配图", bool(manual_image), manual_image)

            result["metrics"]["console_errors"] = result["console_errors"]
            result["metrics"]["page_errors"] = result["page_errors"]
            check("29 全流程无页面脚本错误", not result["page_errors"], result["page_errors"])
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

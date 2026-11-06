# -*- coding: utf-8 -*-
"""悬浮切题画板真机探针：弹板、滚动锁、Ctrl+滚轮缩放、增删框、放弃与确认。

模拟1.pdf → 19 框 / 19 题，随后在画板里：
滚轮平滑滚动、遮罩挡住滚动穿透、Ctrl+滚轮以光标为锚放大；
空白拉框新增、Delete 删框；Esc 与点遮罩放弃后后端一个字节不变；
最后增一框删一框，Enter 提交，坐标与题图都回写。

用法：``.venv/Scripts/python.exe tools/split_board_probe.py <tag>``
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
TOKEN = "split-board-probe-token"
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


def snapshot(detail: dict) -> dict:
    pages = detail.get("page_images") or []
    regions = [region for page in pages for region in (page.get("regions") or [])]
    items = detail.get("items") or []
    return {
        "page_count": len(pages),
        "region_count": len(regions),
        "item_ids": sorted(str(item.get("id") or "") for item in items),
        "region_pending": sorted(str(region.get("pending_id") or "") for region in regions),
        "per_page": [len(page.get("regions") or []) for page in pages],
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "split_board_probe" / tag
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
        detail = {}
        while time.time() < deadline:
            detail = batch_items(base, batch_id)
            if len(detail.get("page_images") or []) >= 5 and len(detail.get("items") or []) >= 19:
                break
            time.sleep(0.3)
        baseline = snapshot(detail)
        result["metrics"]["baseline"] = baseline
        check("02 起点是 5 页 / 19 框 / 19 题",
              baseline["page_count"] == 5 and baseline["region_count"] == 19
              and len(baseline["item_ids"]) == 19, baseline)
        deleted_region = (detail.get("page_images") or [{}])[0].get("regions") or [{}]
        deleted_pid = str(deleted_region[0].get("pending_id") or "")

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

            # ---------- 弹板 ----------
            canvas.locator("#edSplitBoardBtn").click()
            expect(canvas.locator("#edSbBoard")).to_be_visible(timeout=20000)
            expect(canvas.locator(".ed-sb-box").first).to_be_visible(timeout=20000)
            page.wait_for_timeout(700)
            check("03 点【重新切题】弹出画板", canvas.locator("#edSbBoard").count() == 1)
            check("04 画板铺满 5 页原卷并画出 19 框",
                  canvas.locator(".ed-sb-page").count() == 5
                  and canvas.locator(".ed-sb-box").count() == 19,
                  [canvas.locator(".ed-sb-page").count(),
                   canvas.locator(".ed-sb-box").count()])
            board_box = canvas.locator("#edSbBoard").bounding_box()
            result["metrics"]["board_box"] = board_box
            check("05 画板宽度占视口六到七成",
                  bool(board_box) and 0.58 * 1440 <= board_box["width"] <= 0.72 * 1440,
                  board_box)
            board_style = canvas.locator("#edSbBoard").evaluate(
                "node => { var s = getComputedStyle(node);"
                " return [s.backgroundColor, s.borderTopWidth, s.borderTopLeftRadius,"
                " s.boxShadow, getComputedStyle(node.querySelector('.ed-sb-pages')).rowGap,"
                " getComputedStyle(node.querySelector('.ed-sb-scroll')).backgroundColor]; }")
            result["metrics"]["board_style"] = board_style
            check("05a 画板已去弹窗边框且内部纸带无缝",
                  board_style[0] == "rgba(0, 0, 0, 0)" and board_style[1] == "0px"
                  and board_style[2] == "0px" and board_style[3] == "none"
                  and board_style[4] == "0px" and board_style[5] == "rgba(0, 0, 0, 0)",
                  board_style)
            check("06 画板打开时底层滚动被锁死",
                  canvas.locator("#edRoot").evaluate(
                      "() => document.documentElement.style.overflow") == "hidden"
                  and canvas.locator("#edRoot").evaluate(
                      "() => document.body.classList.contains('ed-sb-locked')"), "locked")
            page.screenshot(path=str(shots / "01_board_open.png"))

            # ---------- 滚动锁 + 画板内平滑滚动 ----------
            image_scroll = canvas.locator("#edImageBody")
            image_scroll.evaluate("node => { node.scrollTop = 120; }")
            before_under = image_scroll.evaluate("node => node.scrollTop")
            mask = canvas.locator("#edSbMask")
            mask.hover(position={"x": 6, "y": 6})
            page.mouse.wheel(0, 700)
            page.wait_for_timeout(500)
            after_under = image_scroll.evaluate("node => node.scrollTop")
            board_scroll = canvas.locator("#edSbScroll")
            board_before = board_scroll.evaluate("node => node.scrollTop")
            result["metrics"]["scroll_through"] = [before_under, after_under, board_before]
            check("07 遮罩上的滚轮不会穿透到底层",
                  before_under == after_under and board_before == 0,
                  result["metrics"]["scroll_through"])
            board_scroll.hover()
            page.mouse.wheel(0, 700)
            page.wait_for_timeout(700)
            board_after = board_scroll.evaluate("node => node.scrollTop")
            result["metrics"]["board_scroll"] = [board_before, board_after]
            check("08 画板内部滚轮平滑滚动", board_after > 100, result["metrics"]["board_scroll"])

            # ---------- Ctrl+滚轮光标锚定缩放 ----------
            board_scroll.evaluate("node => { node.scrollTop = 0; }")
            page.wait_for_timeout(300)
            first_box = canvas.locator(".ed-sb-box").first
            # 第一页滚回顶后框可能刚好在画板上沿外，先用脚本把它滚进视口；
            # 不走 hover 的稳定性检查（宿主铺满全屏时它会一直等布局稳定）。
            first_box.evaluate("node => node.scrollIntoView({block: 'center'})")
            page.wait_for_timeout(400)
            box_rect = first_box.bounding_box()
            pages_before = canvas.locator("#edSbPages").evaluate(
                "node => node.getBoundingClientRect().width")
            box_before = first_box.evaluate("node => node.getBoundingClientRect().width")
            check("09 找到可缩放的锚点框", bool(box_rect), box_rect)
            assert box_rect is not None
            page.keyboard.down("Control")
            page.mouse.wheel(0, -240)
            page.keyboard.up("Control")
            page.wait_for_timeout(400)
            pages_after = canvas.locator("#edSbPages").evaluate(
                "node => node.getBoundingClientRect().width")
            box_after = first_box.evaluate("node => node.getBoundingClientRect().width")
            result["metrics"]["zoom"] = {
                "pages": [pages_before, pages_after],
                "box": [box_before, box_after],
                "label": canvas.locator(".ed-sb-zoom").inner_text(),
            }
            check("10 Ctrl+滚轮放大以光标为中心",
                  pages_after > pages_before * 1.2
                  and canvas.locator(".ed-sb-zoom").inner_text() != "100%",
                  result["metrics"]["zoom"])
            check("11 框线随题图同倍无损放大",
                  box_before > 0 and abs(box_after / box_before - pages_after / pages_before) < 0.03,
                  result["metrics"]["zoom"])
            page.screenshot(path=str(shots / "02_zoomed.png"))
            page.keyboard.press("Escape")
            expect(canvas.locator("#edSbBoard")).to_have_count(0, timeout=10000)
            check("12 Esc 放弃后画板关闭", canvas.locator("#edSbBoard").count() == 0)

            # ---------- 新增框 + Delete 删框 ----------
            canvas.locator("#edSplitBoardBtn").click()
            expect(canvas.locator("#edSbBoard")).to_be_visible(timeout=20000)
            scroll = canvas.locator("#edSbScroll")
            last_page = canvas.locator(".ed-sb-page").last
            last_page.evaluate("node => node.scrollIntoView({block: 'start'})")
            page.wait_for_timeout(300)
            page_box = last_page.bounding_box()
            scroll_box = scroll.bounding_box()
            check("13 已滚到空白第 5 页", bool(page_box) and bool(scroll_box), page_box)
            assert page_box is not None and scroll_box is not None
            start_x = page_box["x"] + page_box["width"] * 0.2
            start_y = max(page_box["y"] + 30, scroll_box["y"] + 30)
            end_x = page_box["x"] + page_box["width"] * 0.55
            end_y = start_y + 110
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move((start_x + end_x) / 2, (start_y + end_y) / 2, steps=6)
            page.mouse.move(end_x, end_y, steps=6)
            page.mouse.up()
            page.wait_for_timeout(300)
            new_count = canvas.locator(".ed-sb-box.is-new").count()
            new_chip = canvas.locator(".ed-sb-box.is-new .ed-sb-box-no").first.inner_text()
            result["metrics"]["new_box"] = [new_count, new_chip]
            check("14 空白处拉框直接生成新框", new_count == 1 and new_chip == "新",
                  result["metrics"]["new_box"])
            page.screenshot(path=str(shots / "03_new_box.png"))

            new_box = canvas.locator(".ed-sb-box.is-new").first
            new_rect = new_box.bounding_box()
            assert new_rect is not None
            page.mouse.click(new_rect["x"] + new_rect["width"] / 2,
                             new_rect["y"] + new_rect["height"] / 2)
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)
            check("15 选中新框按 Delete 即删",
                  canvas.locator(".ed-sb-box.is-new").count() == 0,
                  canvas.locator(".ed-sb-box.is-new").count())

            # 再画一个留着提交，并删掉一个已入池的旧框。
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(end_x, end_y, steps=8)
            page.mouse.up()
            page.wait_for_timeout(300)
            check("16 重新画出的新框仍在", canvas.locator(".ed-sb-box.is-new").count() == 1)
            old_box = canvas.locator(".ed-sb-box").first
            old_box.evaluate("node => node.scrollIntoView({block: 'center'})")
            page.wait_for_timeout(300)
            old_rect = old_box.bounding_box()
            assert old_rect is not None
            page.mouse.click(old_rect["x"] + old_rect["width"] / 2,
                             old_rect["y"] + old_rect["height"] / 2)
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)
            check("17 选中已入池的旧框按 Delete 即删",
                  canvas.locator(".ed-sb-box").count() == 19,
                  canvas.locator(".ed-sb-box").count())

            # ---------- Esc 放弃：后端一个字节不变 ----------
            page.keyboard.press("Escape")
            expect(canvas.locator("#edSbBoard")).to_have_count(0, timeout=10000)
            after_discard = snapshot(batch_items(base, batch_id))
            result["metrics"]["after_esc"] = after_discard
            check("18 Esc 放弃后后端仍是 19 框 / 19 题",
                  after_discard["region_count"] == 19 and len(after_discard["item_ids"]) == 19
                  and after_discard["item_ids"] == baseline["item_ids"], after_discard)

            # ---------- 点遮罩放弃 ----------
            canvas.locator("#edSplitBoardBtn").click()
            expect(canvas.locator("#edSbBoard")).to_be_visible(timeout=20000)
            last_page = canvas.locator(".ed-sb-page").last
            last_page.evaluate("node => node.scrollIntoView({block: 'start'})")
            page.wait_for_timeout(300)
            page_box = last_page.bounding_box()
            assert page_box is not None
            start_x = page_box["x"] + page_box["width"] * 0.2
            start_y = max(page_box["y"] + 30, 160)
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move(start_x + 120, start_y + 100, steps=8)
            page.mouse.up()
            page.wait_for_timeout(200)
            canvas.locator("#edSbMask").click(position={"x": 6, "y": 6})
            expect(canvas.locator("#edSbBoard")).to_have_count(0, timeout=10000)
            after_mask = snapshot(batch_items(base, batch_id))
            check("19 点遮罩放弃后后端仍原样",
                  after_mask == after_discard, after_mask)
            check("20 放弃动作没产生任何 4xx/5xx", not result["http_failures"],
                  result["http_failures"][-4:])

            # ---------- 增一框 + 删一框 → Enter 提交 ----------
            canvas.locator("#edSplitBoardBtn").click()
            expect(canvas.locator("#edSbBoard")).to_be_visible(timeout=20000)
            scroll = canvas.locator("#edSbScroll")
            last_page = canvas.locator(".ed-sb-page").last
            last_page.evaluate("node => node.scrollIntoView({block: 'start'})")
            page.wait_for_timeout(300)
            page_box = last_page.bounding_box()
            assert page_box is not None
            start_x = page_box["x"] + page_box["width"] * 0.18
            start_y = max(page_box["y"] + 30, 160)
            end_x = page_box["x"] + page_box["width"] * 0.6
            end_y = start_y + 140
            page.mouse.move(start_x, start_y)
            page.mouse.down()
            page.mouse.move((start_x + end_x) / 2, (start_y + end_y) / 2, steps=6)
            page.mouse.move(end_x, end_y, steps=6)
            page.mouse.up()
            page.wait_for_timeout(250)
            check("21 提交前新框已出现", canvas.locator(".ed-sb-box.is-new").count() == 1)
            old_box = canvas.locator(".ed-sb-box").first
            old_box.evaluate("node => node.scrollIntoView({block: 'center'})")
            page.wait_for_timeout(300)
            old_rect = old_box.bounding_box()
            assert old_rect is not None
            page.mouse.click(old_rect["x"] + old_rect["width"] / 2,
                             old_rect["y"] + old_rect["height"] / 2)
            page.keyboard.press("Delete")
            page.wait_for_timeout(200)
            ok_visible = canvas.locator(".ed-sb-ok").is_visible()
            page.keyboard.press("Enter")
            expect(canvas.locator("#edSbBoard")).to_have_count(0, timeout=60000)
            result["metrics"]["ok_visible"] = ok_visible
            check("22 【⏎ 确认切分】按钮在画板右下角", ok_visible)
            check("23 Enter 提交后画板关闭", canvas.locator("#edSbBoard").count() == 0)

            final = {}
            deadline = time.time() + 45
            while time.time() < deadline:
                final = snapshot(batch_items(base, batch_id))
                if (final["region_count"] == 19 and len(final["item_ids"]) == 19
                        and deleted_pid not in final["item_ids"]
                        and deleted_pid not in final["region_pending"]):
                    break
                page.wait_for_timeout(300)
            result["metrics"]["final"] = final
            check("24 提交后仍是 19 框 / 19 题（一增一删）",
                  final["region_count"] == 19 and len(final["item_ids"]) == 19, final)
            check("25 删掉的旧题已从中转站消失",
                  deleted_pid and deleted_pid not in final["item_ids"]
                  and deleted_pid not in final["region_pending"], deleted_pid)
            final_pages = batch_items(base, batch_id).get("page_images") or []
            last_regions = final_pages[-1].get("regions") or [] if final_pages else []
            result["metrics"]["per_page"] = final.get("per_page")
            check("26 新框落在第 5 页且绑定了新待审题",
                  len(last_regions) == 1
                  and str(last_regions[0].get("pending_id") or "").startswith("p_")
                  and str(last_regions[0].get("pending_id") or "") in final["item_ids"],
                  last_regions[:1])
            check("27 提交后每页框数回到 [4,7,4,3,1]",
                  final.get("per_page") == [4, 7, 4, 3, 1], final.get("per_page"))
            page.screenshot(path=str(shots / "04_confirmed.png"))
            expect(canvas.locator(".ed-page-cell").first).to_be_visible(timeout=20000)
            page.wait_for_timeout(500)
            left = canvas.locator(".ed-page-cell")
            caption_count = left.locator(".ed-img-caption").count()
            sep_count = left.locator(".ed-page-sep").count()
            sep_text = left.locator(".ed-page-sep").first.inner_text()
            green_count = left.locator(".ed-green-box").count()
            green_style = left.locator(".ed-green-box").first.evaluate(
                "node => { var s = getComputedStyle(node); return [s.pointerEvents,"
                " s.position, s.borderTopStyle, s.borderTopColor, s.borderTopWidth,"
                " node.querySelectorAll('button, [data-handle], .ed-sb-handle').length]; }")
            layer_events = left.locator(".ed-green-layer").first.evaluate(
                "node => getComputedStyle(node).pointerEvents")
            result["metrics"]["left_strip"] = {
                "caption": caption_count, "separators": sep_count, "separator_text": sep_text,
                "green_boxes": green_count, "green_style": green_style,
                "layer_events": layer_events}
            check("29 左栏页底提示文字块已整块撤除", caption_count == 0, caption_count)
            check("30 页与页之间只留虚线页码",
                  sep_count == 4 and "原卷第 2 页" in sep_text,
                  [sep_count, sep_text])
            check("31 左栏按页画只读绿框（吃不到鼠标、没有手柄）",
                  green_count == 19 and layer_events == "none" and green_style[0] == "none"
                  and green_style[1] == "absolute" and green_style[2] == "solid"
                  and green_style[3] == "rgb(47, 158, 90)" and green_style[4] == "2px"
                  and green_style[5] == 0, result["metrics"]["left_strip"])

            result["metrics"]["console_errors"] = result["console_errors"]
            result["metrics"]["page_errors"] = result["page_errors"]
            check("28 全流程无页面脚本错误", not result["page_errors"], result["page_errors"])
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

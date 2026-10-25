# -*- coding: utf-8 -*-
"""录题工作台三栏对比 + 框选切图真机探针（军令 #13）。

用法：``.venv/Scripts/python.exe tools/editor_crop_probe.py <tag>``

隔离：复制 editor 与 core-bank 到独立插件目录，另起端口与数据目录，
不写本机 data/。检查项：

- 1440/1600 宽下三栏真实并排：左表单 < 中栏（源码 < A4）< 右原图框选；
- 选择本地 PNG 后 Canvas 按原图分辨率解码，整图插入按钮可用；
- 鼠标真实拖拽出矩形 → 选区框出现 → 【插入选区】走宿主 asset.upload；
- 上传文件是合法 PNG，像素尺寸与选区提示逐像素一致（读 IHDR 复核）；
- 题干落 `\\includegraphics{/static/uploads/...}`，A4 预览真加载该图；
- 保存后 API 能读回 `images[]`（role=stem、uri 一致）；
- 375px 窄屏三栏按「表单 → 对照 → 原图」纵向堆叠且无横向溢出；
- 控制台零错误、页面零异常。
"""

from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
import zlib
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from editor_probe import free_port, http_json, wait_health  # noqa: E402

EDITOR_ID = "org.jiuzhang.editor"
BANK_ID = "org.jiuzhang.bank-engine"
IMAGE_W = 640
IMAGE_H = 960


def write_source_png(path: Path) -> None:
    """生成一张有明确色块的「原题」图，不依赖 PIL。"""
    rows = []
    for y in range(IMAGE_H):
        row = bytearray([0])
        for x in range(IMAGE_W):
            if 90 <= x < 550 and 110 <= y < 360:
                row += bytes((214, 86, 58))
            elif 70 <= x < 570 and 520 <= y < 880:
                row += bytes(((x * 3) % 180 + 30, (y * 2) % 170 + 40, 150))
            else:
                row += bytes((252, 250, 244))
        rows.append(bytes(row))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", IMAGE_W, IMAGE_H, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
        + chunk(b"IEND", b"")
    )


def png_size(raw: bytes) -> tuple[int, int]:
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("不是 PNG")
    return struct.unpack(">II", raw[16:24])


def download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read()


def rect_of(frame, selector: str) -> dict:
    return frame.locator(selector).evaluate(
        "el => {const r = el.getBoundingClientRect();"
        "return {x: r.x, y: r.y, w: r.width, h: r.height};}"
    )


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "editor_crop_probe" / tag
    if work.exists():
        shutil.rmtree(work)
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    shots = work / "shots"
    data_dir.mkdir(parents=True)
    plugins_dir.mkdir(parents=True)
    shots.mkdir(parents=True)
    for plugin_id in (EDITOR_ID, BANK_ID):
        shutil.copytree(ROOT / "plugins" / plugin_id, plugins_dir / plugin_id)
    source_png = work / "source-exam.png"
    write_source_png(source_png)

    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = "editor-crop-probe-token"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )

    result: dict = {"tag": tag, "base": base, "checks": [], "console_errors": [],
                    "page_errors": [], "metrics": {}, "shots": []}

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    page = None
    try:
        wait_health(base, process)
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            page.on("console", lambda message: result["console_errors"].append(message.text)
                    if message.type in {"error", "warning"} else None)
            page.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            page.goto(base + "/workspace", wait_until="networkidle")

            item = page.locator(".ws-plugin-item", has_text="录题工作台").first
            expect(item).to_be_visible(timeout=10000)
            item.click()
            panel = page.locator("#wsPanel_plugin_org_jiuzhang_editor")
            frame = panel.frame_locator(".ws-plugin-frame")
            expect(frame.locator("#root")).to_be_visible(timeout=15000)

            # ---------- 三栏几何 ----------
            form_rect = rect_of(frame, ".ed-form")
            compare_rect = rect_of(frame, ".ed-compare")
            code_rect = rect_of(frame, ".ed-code")
            preview_rect = rect_of(frame, ".ed-preview")
            source_rect = rect_of(frame, ".ed-source")
            result["metrics"]["columns"] = {
                "form": form_rect, "compare": compare_rect, "code": code_rect,
                "preview": preview_rect, "source": source_rect,
            }
            check("三栏从左到右：表单 → 对照 → 原图",
                  form_rect["x"] + form_rect["w"] <= compare_rect["x"] + 1
                  and compare_rect["x"] + compare_rect["w"] <= source_rect["x"] + 1,
                  {"form_right": form_rect["x"] + form_rect["w"],
                   "compare": compare_rect["x"], "source": source_rect["x"]})
            check("中栏左源码右 A4",
                  code_rect["x"] + code_rect["w"] <= preview_rect["x"] + 1,
                  {"code_right": code_rect["x"] + code_rect["w"], "preview": preview_rect["x"]})
            check("三栏都有可用宽度",
                  min(form_rect["w"], compare_rect["w"], source_rect["w"]) > 180,
                  {"widths": [round(form_rect["w"]), round(compare_rect["w"]), round(source_rect["w"])]})

            stem = frame.locator("#edStem")
            stem.fill("已知函数 $f(x)=x^{2}-5x+6$，则方程 $f(x)=0$ 的解为（　　）")
            page.wait_for_timeout(220)
            page.screenshot(path=str(shots / "10-three-columns.png"))
            result["shots"].append(str(shots / "10-three-columns.png"))

            # ---------- 载入原图 ----------
            frame.locator("#edImageFile").set_input_files(str(source_png))
            expect(frame.locator("#edSourceStage")).to_be_visible(timeout=10000)
            expect(frame.locator("#edCropAll")).to_be_enabled(timeout=10000)
            canvas_size = frame.locator("#edSourceCanvas").evaluate(
                "c => ({w: c.width, h: c.height, cssW: c.getBoundingClientRect().width,"
                " cssH: c.getBoundingClientRect().height})"
            )
            result["metrics"]["canvas"] = canvas_size
            check("原图按真实分辨率解码进 Canvas",
                  canvas_size["w"] == IMAGE_W and canvas_size["h"] == IMAGE_H, canvas_size)
            name_text = frame.locator("#edSourceName").inner_text()
            check("右栏显示原图名与尺寸",
                  f"{IMAGE_W}×{IMAGE_H}" in name_text, name_text)

            # ---------- 原生矩形框选 ----------
            canvas_box = frame.locator("#edSourceCanvas").bounding_box()
            if not canvas_box:
                raise AssertionError("无法取得原图画布位置")
            start = (canvas_box["x"] + canvas_box["width"] * 0.25,
                     canvas_box["y"] + canvas_box["height"] * 0.30)
            end = (canvas_box["x"] + canvas_box["width"] * 0.75,
                   canvas_box["y"] + canvas_box["height"] * 0.60)
            page.mouse.move(*start)
            page.mouse.down()
            page.mouse.move(end[0], end[1], steps=10)
            page.mouse.up()
            expect(frame.locator("#edCropBox")).to_be_visible(timeout=3000)
            expect(frame.locator("#edCropInsert")).to_be_enabled(timeout=3000)
            hint = frame.locator("#edCropHint").inner_text()
            check("拖拽后出现选区并可插入", "选区" in hint, hint)
            page.screenshot(path=str(shots / "20-crop-selected.png"))
            result["shots"].append(str(shots / "20-crop-selected.png"))

            # ---------- Canvas 截取 → 宿主上传 ----------
            frame.locator("#edCropInsert").click()
            status = frame.locator("#edSourceStatus")
            expect(status).to_have_attribute("data-asset-id", re.compile(r"^img_"), timeout=20000)
            first_id = status.get_attribute("data-asset-id") or ""
            first_uri = status.get_attribute("data-asset-uri") or ""
            status_text = status.inner_text()
            result["metrics"]["crop"] = {"id": first_id, "uri": first_uri, "status": status_text}
            stem_value = stem.input_value()
            check("题干插入 \\includegraphics{托管路径}",
                  f"\\includegraphics{{{first_uri}}}" in stem_value, stem_value[:160])
            crop_pixels = re.search(r"(\d+)×(\d+) px", status_text)
            if not crop_pixels:
                raise AssertionError("状态栏没有回显选区像素尺寸：" + status_text)
            expected_w, expected_h = int(crop_pixels.group(1)), int(crop_pixels.group(2))
            uploaded = download(base + first_uri)
            uploaded_w, uploaded_h = png_size(uploaded)
            result["metrics"]["uploaded_png"] = {
                "declared": [expected_w, expected_h],
                "actual": [uploaded_w, uploaded_h],
                "bytes": len(uploaded),
            }
            check("上传的确实是 PNG 且尺寸与选区一致",
                  (uploaded_w, uploaded_h) == (expected_w, expected_h),
                  result["metrics"]["uploaded_png"])
            check("选区小于原图（不是整图冒充选区）",
                  uploaded_w < IMAGE_W and uploaded_h < IMAGE_H,
                  {"crop": [uploaded_w, uploaded_h], "source": [IMAGE_W, IMAGE_H]})

            preview_img = frame.locator("#edPageBody img.ed-inline-img")
            expect(preview_img).to_have_count(1, timeout=5000)
            natural = preview_img.evaluate("img => ({w: img.naturalWidth, h: img.naturalHeight})")
            check("A4 预览真加载切出的配图",
                  natural["w"] == uploaded_w and natural["h"] == uploaded_h, natural)

            # ---------- 整图插入（键盘可达的兜底） ----------
            frame.locator("#edCropAll").click()
            deadline = time.time() + 20
            second_id = first_id
            while time.time() < deadline and second_id == first_id:
                second_id = status.get_attribute("data-asset-id") or first_id
                time.sleep(0.1)
            second_uri = status.get_attribute("data-asset-uri") or ""
            check("整图插入也可用且生成第二个资产",
                  second_id != first_id and second_uri.endswith(".png"),
                  {"first": first_id, "second": second_id})
            expect(preview_img).to_have_count(2, timeout=5000)
            page.screenshot(path=str(shots / "30-inserted.png"))
            result["shots"].append(str(shots / "30-inserted.png"))

            # ---------- 保存后 images[] 回读 ----------
            frame.locator("#edType").select_option("fill_blank")
            frame.locator("#edAnswer").fill("$x=2$ 或 $x=3$")
            frame.locator("#edSave").click()
            saved = frame.locator("#edSaved")
            expect(saved).to_be_visible(timeout=20000)
            question_id = saved.get_attribute("data-id") or ""
            status_code, document = http_json(
                base + f"/api/bank/plugins/{BANK_ID}/questions/{question_id}"
            )
            result["metrics"]["question"] = {
                "id": question_id, "status": status_code,
                "images": document.get("images"), "stem": document.get("stem"),
            }
            images = document.get("images") or []
            uris = [item.get("uri") for item in images]
            check("保存成功且题号合法",
                  bool(re.fullmatch(r"q_[A-Za-z0-9_-]{8,64}", question_id)) and status_code == 200,
                  {"id": question_id, "status": status_code})
            check("images[] 随题落库且角色为 stem",
                  len(images) >= 2 and all(item.get("role") == "stem" for item in images),
                  images)
            check("正文与 images[].uri 一一对应",
                  first_uri in uris and second_uri in uris
                  and f"\\includegraphics{{{first_uri}}}" in (document.get("stem") or ""),
                  uris)
            page.screenshot(path=str(shots / "40-saved.png"))
            result["shots"].append(str(shots / "40-saved.png"))

            page.close()

            # ---------- 375px 窄屏：三栏纵向堆叠、无横向溢出 ----------
            mobile = browser.new_page(viewport={"width": 375, "height": 780})
            mobile.on("console", lambda message: result["console_errors"].append(message.text)
                      if message.type in {"error", "warning"} else None)
            mobile.on("pageerror", lambda error: result["page_errors"].append(str(error)))
            mobile.goto(base + f"/plugin-assets/{EDITOR_ID}/dist/index.html",
                        wait_until="networkidle")
            expect(mobile.locator("#root")).to_be_visible(timeout=10000)
            mobile.wait_for_timeout(350)
            narrow = mobile.evaluate(
                "() => {const r = s => {const b = document.querySelector(s).getBoundingClientRect();"
                "return {x: b.x, y: b.y, w: b.width, h: b.height};};"
                "return {scrollWidth: document.documentElement.scrollWidth,"
                " innerWidth: window.innerWidth, form: r('.ed-form'),"
                " compare: r('.ed-compare'), source: r('.ed-source')};}"
            )
            result["metrics"]["narrow"] = narrow
            check("375px 三栏纵向堆叠",
                  narrow["form"]["y"] + narrow["form"]["h"] <= narrow["compare"]["y"] + 1
                  and narrow["compare"]["y"] + narrow["compare"]["h"] <= narrow["source"]["y"] + 1,
                  narrow)
            check("375px 无横向溢出",
                  narrow["scrollWidth"] <= narrow["innerWidth"] + 1, narrow)
            mobile.screenshot(path=str(shots / "50-mobile-375.png"), full_page=False)
            result["shots"].append(str(shots / "50-mobile-375.png"))
            mobile.close()
            browser.close()
    except Exception as exc:  # noqa: BLE001 - 探针要把失败原样落盘
        result["error"] = f"{type(exc).__name__}: {exc}"
        try:
            if page is not None:
                page.screenshot(path=str(shots / "failure.png"))
        except Exception:
            pass
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()

    result["ok"] = bool(result["checks"]) and all(item["ok"] for item in result["checks"]) \
        and not result["page_errors"] and "error" not in result
    (work / "probe.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    passed = sum(1 for item in result["checks"] if item["ok"])
    total = len(result["checks"])
    print(("PASS" if result["ok"] else "FAIL") + f" · {passed}/{total} · {work}")
    for item in result["checks"]:
        print(("  ✓ " if item["ok"] else "  ✗ ") + item["name"])
    if result["console_errors"]:
        print("console:", result["console_errors"][:8])
    if result["page_errors"]:
        print("pageerrors:", result["page_errors"][:8])
    if "error" in result:
        print("error:", result["error"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

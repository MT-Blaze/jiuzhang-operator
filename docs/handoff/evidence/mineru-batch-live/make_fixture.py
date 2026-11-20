"""微批夹具：用 OCR 管线自己探出的题块框，从 A1 纯图真卷裁 4 道真题 → 4 页纯图 PDF。

供 MinerU 云整批真测微批 3–5 题：每页一道真题（管线认得的题块），整批一次发送
files=4。题块框来自 ocr.detect 本身（非合成），隔离成页后应仍被认作 4 题。
运行：.venv/Scripts/python.exe docs/handoff/evidence/mineru-batch-live/make_fixture.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import pypdfium2  # noqa: E402
from PIL import Image  # noqa: E402

from app.core.ingest.recognize import ocr  # noqa: E402
from app.core.ingest.render import pdf as pdf_render  # noqa: E402
from app.core.ingest.render.common import PDF_RENDER_DPI  # noqa: E402

SRC = ROOT / "test_papers" / "A1_【数学】2025届高三押题信息卷（一）（含答案解析）【微信搜_龙考网查看更多】.pdf"
OUT = ROOT / ".system_generated" / "mineru-batch-live"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_PAGE = 2  # A1 第 2 页有 6 个干净题块（题 6–11）
WANT = 4


def main() -> int:
    data = SRC.read_bytes()
    detected = ocr.detect("A1.pdf", data, [{"page": SOURCE_PAGE}], tier="small")
    regions = (detected.get("pages") or {}).get(SOURCE_PAGE) or []
    print("source page%d regions=%d" % (SOURCE_PAGE, len(regions)))
    if len(regions) < WANT:
        print("NOT ENOUGH REGIONS")
        return 2
    doc = pypdfium2.PdfDocument(data)
    page = doc[SOURCE_PAGE - 1]
    bmp = page.render(scale=PDF_RENDER_DPI / 72.0)
    png = pdf_render._png_from_bitmap(bmp, bytes(bmp.buffer))
    bmp.close(); page.close(); doc.close()
    img = Image.open(io.BytesIO(png)).convert("RGB")
    print("rendered page size=%s dpi=%d" % (img.size, PDF_RENDER_DPI))
    pages = []
    for i, r in enumerate(regions[:WANT], 1):
        x, y = float(r["x"]), float(r["y"])
        w, h = float(r["w"]), float(r["h"])
        pad = 16
        box = (max(0, int(x) - pad), max(0, int(y) - pad),
               min(img.width, int(x + w) + pad), min(img.height, int(y + h) + pad))
        crop = img.crop(box)
        canvas = Image.new("RGB", (crop.width + 120, crop.height + 200), "white")
        canvas.paste(crop, (60, 100))
        pages.append(canvas)
        crop.save(OUT / ("q%d.png" % i))
        print("q%d no=%s box=%s crop=%s" % (i, r.get("no"), box, crop.size))
    fixture = OUT / "fixture_4q.pdf"
    pages[0].save(fixture, save_all=True, append_images=pages[1:], resolution=PDF_RENDER_DPI)
    print("fixture:", fixture, "pages=%d" % len(pages))
    verify = ocr.detect("fixture_4q.pdf", fixture.read_bytes(),
                        [{"page": i} for i in range(1, len(pages) + 1)], tier="small")
    per_page = {k: len(v) for k, v in (verify.get("pages") or {}).items()}
    total = sum(per_page.values())
    print("verify ok=%s regions_per_page=%s total=%d" % (verify.get("ok"), per_page, total))
    return 0 if total == WANT else 2


if __name__ == "__main__":
    raise SystemExit(main())
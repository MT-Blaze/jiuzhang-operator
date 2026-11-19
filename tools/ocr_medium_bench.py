"""RapidOCR 快(small) vs 准(medium) 3 样本对照 bench（2.20.0 卡§6，离线合规）。

不出网：medium 权重必须已经由老师在配置中心点【安装】落地（engines/ocr/models/），
本工具只读权重与样本卷，缺权重显性拒绝、绝不代下。样本默认取证据副本里的三份
真卷（可 argv 覆盖），各渲染第 1 页，两档分别跑行清单＋题号链，报行数/均分/
链得分/切块数/耗时。结论只摆事实，升不升默认由主公另点头。

运行：``.venv/Scripts/python.exe tools/ocr_medium_bench.py [pdf1 pdf2 pdf3]``
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from app.core import toml_io  # noqa: E402
from app.core.ingest import ocr_setup  # noqa: E402
from app.core.ingest.recognize import ocr  # noqa: E402
from app.core.ingest.render import pdf as pdf_render  # noqa: E402
from app.core.ingest.render.common import PDF_RENDER_DPI  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLES = [
    ROOT / ".system_generated/a2_image_ingest/ev1/data/pending_sources/"
           "20261118-193020_220dac_东北师大附中2023-2024高一上学期第一次月考试题.pdf",
    ROOT / ".system_generated/a2_image_ingest/ev1/data/pending_sources/"
           "20261118-193046_006bea_2023一中高一上学期期末试卷.pdf",
    ROOT / ".system_generated/a2_image_ingest/ev1/data/pending_sources/"
           "20261118-193131_f39f1b_蜜蜂试卷-2023年庆中高一下学期期中试卷.pdf",
]
OUT = ROOT / ".system_generated" / "ocr-medium-bench" / "bench.toml"


def page_array(data: bytes):
    import cv2
    import numpy as np
    doc = pdf_render._pdfium.PdfDocument(data)
    try:
        page = doc[0]
        bmp = page.render(scale=PDF_RENDER_DPI / 72.0)
        png = pdf_render._png_from_bitmap(bmp, bytes(bmp.buffer))
        bmp.close()
        page.close()
    finally:
        doc.close()
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)


def run_tier(tier: str, arr) -> dict:
    engine = ocr._engine(tier)
    started = time.monotonic()
    result = ocr._analyze(engine, arr, True)
    elapsed = time.monotonic() - started
    rows = result["rows"]
    return {
        "rows": len(rows),
        "mean_score": round(sum(r["score"] for r in rows) / len(rows), 4) if rows else 0.0,
        "chain_score": result["score"],
        "regions": len(result["regions"]),
        "columns": result["columns"],
        "seconds": round(elapsed, 2),
    }


def main() -> int:
    samples = [Path(arg) for arg in sys.argv[1:]] or DEFAULT_SAMPLES
    if len(samples) != 3:
        print(" bench 口径＝3 样本，请给恰好 3 份 PDF")
        return 2
    for path in samples:
        if not path.is_file():
            print("样本不在：%s" % path)
            return 2
    if not ocr_setup.weights_ready():
        print("medium 权重未安装：请先在模型配置中心点【安装】（出网须界面点击），本工具不代下。")
        return 2
    report: dict = {"note": "快=small 准=medium；各卷第 1 页；CPU；只摆事实不排座",
                    "samples": []}
    for path in samples:
        arr = page_array(path.read_bytes())
        if arr is None:
            print("页图解码失败：%s" % path.name)
            return 2
        small = run_tier("small", arr)
        medium = run_tier("medium", arr)
        row = {"file": path.name, "small": small, "medium": medium}
        report["samples"].append(row)
        print("%s\n  small: %s\n  medium: %s" % (path.name, small, medium))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    toml_io.write(OUT, report)
    print("证据落盘：%s" % OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
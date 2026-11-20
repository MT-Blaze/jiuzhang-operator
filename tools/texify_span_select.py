# -*- coding: utf-8 -*-
"""探针微批选块器（只读）：在隔离副本环境里按公式形状挑 span 序号，TSV _stdout。

用法：python tools/texify_span_select.py <operator副本根> <pid> [<pid>…]
env 须已带 JZO_DATA_DIR／JZO_PLUGINS_DIR（探针传入，与服务同口径）。
形状滤：单行、无汉字、宽 60–700px、高≥20px、宽高比 1–12——长条/多行串不是公式裁图。
每个 pid 至多回一行「pid\tindex\tpreview」；挑不出不回。绝不写库。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1]).resolve()))

from app.core.ingest.recognize import formula  # noqa: E402
from app.core.pending.batch import batches  # noqa: E402


def shaped(span: dict) -> bool:
    text = str(span.get("text") or "")
    if not text or "\n" in text or "\r" in text:
        return False
    if any("一" <= ch <= "鿿" for ch in text):
        return False
    x, y, w, h = span["bbox"]
    return 60 <= w <= 700 and h >= 20 and 1.0 <= w / h <= 12


for pid in sys.argv[2:]:
    try:
        item = batches.get_pending(pid)
        page_images, pdf_bytes = formula.batch_context(str(item.get("batch_id") or ""))
        spans = formula.discover_spans(item, page_images, pdf_bytes)
    except Exception:  # noqa: BLE001 - 单题读不到只跳过
        continue
    for index, span in enumerate(spans):
        if shaped(span):
            preview = str(span.get("text") or "")[:40].replace("\t", " ")
            print("%s\t%d\t%s" % (pid, index, preview), flush=True)
            break
"""图片型卷自动切题 T4：RapidOCR 行清单＋坐标 → 现有题号链（决策台账 D7）。

只做「页图 → OCR 行清单 → 交现有链切题」：朝向纠正、双栏、丢点题号修补
全是机械预处理，不猜题。认不出就如实交 ok=False，宿主退回版面引擎与框选。
坐标桥：OCR 像素系 y 向下 → 链的 y 向上像素系（page_width=像素宽，scale=1）；
旋转页切完再换回原页像素系，裁图映射才不错位。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.ingest.layout import python as text_layout
from app.core.ingest.render import pdf as pdf_render
from app.core.ingest.render import regions as chain
from app.core.ingest.render.common import PDF_RENDER_DPI

logger = logging.getLogger(__name__)

_ENGINES: dict[str, Any] = {}
_FOOTER_SLASH = re.compile(r"第\s*(\d+)\s*页\s*[/／]\s*共\s*(\d+)\s*页")
_DOTLESS = re.compile(r"^(\d{1,2})\s+(?=\S)")


def _engine(tier: str = "small") -> Any:
    if tier not in _ENGINES:
        from rapidocr import RapidOCR
        logging.getLogger("rapidocr").setLevel(logging.ERROR)
        if tier == "medium":
            from app.core.ingest import ocr_setup
            if not ocr_setup.weights_ready():
                raise RuntimeError("准档权重未安装，先在模型配置中心点【安装】")
            det, rec = ocr_setup.model_paths()
            # model_path 指入 engines/ocr/models/：包见本地路径就不走自带下载通道。
            # 钉版 rapidocr 的 model_type 只认 Enum，字符串会被 ParseParams 拒。
            from rapidocr.utils.typings import ModelType
            _ENGINES[tier] = RapidOCR(params={
                "Det.model_type": ModelType.MEDIUM, "Rec.model_type": ModelType.MEDIUM,
                "Det.model_path": str(det), "Rec.model_path": str(rec)})
        else:
            _ENGINES[tier] = RapidOCR()
    return _ENGINES[tier]


def reset(tier: str | None = None) -> None:
    """丢引擎缓存（卸载权重前调用，防会话占着文件）；不给档位＝全丢。"""
    if tier is None:
        _ENGINES.clear()
    else:
        _ENGINES.pop(tier, None)


def _rows(engine: Any, arr: Any) -> list[dict[str, Any]]:
    import numpy as np
    res = engine(arr)
    boxes = res.boxes if res.boxes is not None else []
    txts = res.txts if res.txts is not None else []
    scores = res.scores if res.scores is not None else []
    rows = []
    for box, txt, score in zip(boxes, txts, scores):
        xs = [float(p[0]) for p in box]
        ys = [float(p[1]) for p in box]
        rows.append({"text": str(txt), "score": float(score),
                     "x0": min(xs), "y0": min(ys), "x1": max(xs), "y1": max(ys)})
    rows.sort(key=lambda r: (round(r["y0"] / 40), r["x0"]))
    return _dedupe(rows)


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """OCR 偶发同位重复框（19 与 22 叠在一处）会断链：重叠超八成留分高者。"""
    kept: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda r: -r["score"]):
        duplicate = False
        for other in kept:
            ix = max(0.0, min(row["x1"], other["x1"]) - max(row["x0"], other["x0"]))
            iy = max(0.0, min(row["y1"], other["y1"]) - max(row["y0"], other["y0"]))
            smaller = min((row["x1"] - row["x0"]) * (row["y1"] - row["y0"]),
                          (other["x1"] - other["x0"]) * (other["y1"] - other["y0"]))
            if smaller > 0 and ix * iy / smaller > 0.8:
                duplicate = True
                break
        if not duplicate:
            kept.append(row)
    kept.sort(key=lambda r: (round(r["y0"] / 40), r["x0"]))
    return kept


def _up_lines(rows: list[dict[str, Any]], height: int) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        text = _FOOTER_SLASH.sub(lambda m: "第%s页（共%s页）" % (m.group(1), m.group(2)),
                                 r["text"])
        out.append({"text": text, "left": r["x0"], "right": r["x1"],
                    "bottom": height - r["y1"], "top": height - r["y0"], "missing": 0})
    return out


def _repair_dotless(up: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[int]]:
    """OCR 丢点号的题号（「17 已知…」）：前后邻号都在链上才补点，不猜。"""
    pos = {}
    for i, line in enumerate(up):
        matched = chain._PDF_HEAD.match(line["text"])
        if matched and not chain._PDF_INSTRUCTION.search(line["text"]):
            pos[int(matched.group(1))] = i
    out = [dict(line) for line in up]
    fixed = []
    for i, line in enumerate(up):
        if chain._PDF_HEAD.match(line["text"]):
            continue
        matched = _DOTLESS.match(line["text"])
        if not matched:
            continue
        number = int(matched.group(1))
        if pos.get(number - 1, 10 ** 9) < i < pos.get(number + 1, -1):
            out[i]["text"] = _DOTLESS.sub(lambda m: m.group(1) + ". ",
                                          line["text"], count=1)
            fixed.append(number)
    return out, fixed


def _heads(up: list[dict[str, Any]]) -> list[tuple[int, int]]:
    heads = []
    for i, line in enumerate(up):
        matched = chain._PDF_HEAD.match(line["text"])
        if matched and not chain._PDF_INSTRUCTION.search(line["text"]):
            heads.append((i, int(matched.group(1))))
    return heads


def _chain(up: list[dict[str, Any]], width: int, height: int,
           ink: bytearray, first_page: bool) -> tuple[list[dict[str, Any]], int, int]:
    """行清单 → (题块, 栏数, 链得分)；双栏复用文本层那套分栏几何。"""
    info = {"width_pt": float(width), "height_pt": float(height), "lines": up}
    entry = {"width": width, "height": height}
    # 旋转横页栏沟实测 42.5px（2% 阈 46.8 会漏），OCR 侧放宽到 1.5%；
    # 末栏只有一道题（如 22 题独占右栏）也认栏，min_heads 放 1；文本路默认不动。
    split = text_layout._column_split(info, 0.015, 1)
    if split is not None:
        regions = text_layout._column_regions(info, entry, split, increasing=True)
        if regions:
            score = 0
            for column in ([l for l in up if l["left"] < split],
                           [l for l in up if l["left"] >= split]):
                heads = [(int(chain._PDF_HEAD.match(l["text"]).group(1)), l)
                         for l in column
                         if chain._PDF_HEAD.match(l["text"])
                         and not chain._PDF_INSTRUCTION.search(l["text"])]
                heads.sort(key=lambda pair: pair[1]["top"], reverse=True)
                score += len(text_layout._increasing_heads(heads))
            return regions, 2, score
    regions = chain._question_regions(up, float(width), float(height), width, height,
                                      ink_rows=ink, first_page=first_page,
                                      apply_fallbacks=True)
    return regions, 1, len(chain._longest_number_run(_heads(up)))


def _ink(arr: Any) -> bytearray:
    import numpy as np
    return bytearray((arr.min(axis=2) < 245).any(axis=1).astype(np.uint8))


def _analyze(engine: Any, arr: Any, first_page: bool) -> dict[str, Any]:
    import numpy as np
    rows = _rows(engine, arr)
    height, width = arr.shape[:2]
    up, _fixed = _repair_dotless(_up_lines(rows, height))
    regions, columns, score = _chain(up, width, height, _ink(arr), first_page)
    ratios = sorted((r["x1"] - r["x0"]) / max(1.0, r["y1"] - r["y0"]) for r in rows)
    median = ratios[len(ratios) // 2] if ratios else 99.0
    return {"rows": rows, "regions": regions, "columns": columns,
            "score": score, "median": median, "rot": 0}


def _orient(engine: Any, arr: Any, first_page: bool) -> dict[str, Any]:
    """竖框占多数 ⇒ 卷面躺倒：试 90° 两向，取栏感知链得分最高者。"""
    import numpy as np
    base = _analyze(engine, arr, first_page)
    if base["median"] >= 0.9:
        return base
    best = base
    for k in (1, 3):
        cand = _analyze(engine, np.ascontiguousarray(np.rot90(arr, k)), first_page)
        cand["rot"] = k
        if cand["score"] > best["score"]:
            best = cand
    return best


def _unrotate_box(box: tuple[float, float, float, float], k: int,
                  width: int, height: int) -> tuple[float, float, float, float]:
    """旋转页像素框 → 原页像素框（x0, y0, x1, y1）。"""
    x0, y0, x1, y1 = box
    if k == 1:
        return (width - 1 - y1, x0, width - 1 - y0, x1)
    return (y0, height - 1 - x1, y1, height - 1 - x0)


def _down_lines(rows: list[dict[str, Any]], rot: int,
                width: int, height: int) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        x0, y0, x1, y1 = _unrotate_box((r["x0"], r["y0"], r["x1"], r["y1"]),
                                       rot, width, height) if rot else (
                                           r["x0"], r["y0"], r["x1"], r["y1"])
        out.append({"text": r["text"], "left": x0, "top": y0,
                    "right": x1, "bottom": y1})
    return out


def detect(name: str, data: bytes,
           page_images: list[dict[str, Any]], tier: str = "small") -> dict[str, Any]:
    """整份图片卷 → 版面引擎同形状的题块 dict；另带 y 向下行清单供跨页判定。

    tier=small（快档，随底座自带）行为不变；tier=medium（准档，2.20.0 卡§6）
    走 engines/ocr/models/ 的 medium 权重，未安装显性 ok=False 不偷换快档。
    """
    import cv2
    import numpy as np
    label = "ocr" if tier == "small" else "ocr_medium"
    say_name = "RapidOCR" if tier == "small" else "RapidOCR·准"
    empty = {"ok": False, "engine": label, "pages": {}, "columns": {},
             "lines_by_page": {}, "status": []}
    if pdf_render._pdfium is None:
        return dict(empty, detail="内置 PDF 渲染器（pypdfium2）没有装上，OCR 切题未执行")
    try:
        engine = _engine(tier)
    except Exception as error:  # noqa: BLE001 - 引擎缺装只该降级，不该拖垮整批
        return dict(empty, detail=f"{say_name} 没装上或起不来（{error}）")
    try:
        doc = pdf_render._pdfium.PdfDocument(data)
    except Exception as error:  # noqa: BLE001
        return dict(empty, detail=f"OCR 切题打不开原 PDF（{error}）")
    pages: dict[int, list[dict[str, Any]]] = {}
    columns: dict[int, int] = {}
    lines_by_page: dict[int, list[dict[str, Any]]] = {}
    status: list[str] = []
    try:
        for entry in page_images or []:
            try:
                page_no = int(entry.get("page") or 0)
            except (TypeError, ValueError):
                continue
            if page_no < 1 or page_no > len(doc):
                continue
            page = doc[page_no - 1]
            bmp = page.render(scale=PDF_RENDER_DPI / 72.0)
            png = pdf_render._png_from_bitmap(bmp, bytes(bmp.buffer))
            bmp.close()
            page.close()
            arr = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR)
            if arr is None:
                status.append({"text": f"第 {page_no} 页页图解码失败，OCR 跳过",
                               "level": "warn"})
                continue
            height, width = arr.shape[:2]
            result = _orient(engine, arr, page_no == 1)
            rot = result["rot"]
            regions = result["regions"]
            if rot:
                for region in regions:
                    x0, y0, x1, y1 = _unrotate_box(
                        (region["x"], region["y"],
                         region["x"] + region["w"], region["y"] + region["h"]),
                        rot, width, height)
                    region["x"], region["y"] = round(x0, 1), round(y0, 1)
                    region["w"], region["h"] = round(x1 - x0, 1), round(y1 - y0, 1)
            columns[page_no] = result["columns"]
            lines_by_page[page_no] = _down_lines(result["rows"], rot, width, height)
            if regions:
                pages[page_no] = regions
            status.append({"text": "第 %d 页 OCR %d 行%s，切 %d 块"
                           % (page_no, len(result["rows"]),
                              f"（朝向纠正 {rot}）" if rot else "", len(regions)),
                           "level": "info"})
    finally:
        doc.close()
    ok = bool(pages)
    blocks = sum(len(value) for value in pages.values())
    return {"ok": ok, "engine": label, "pages": pages, "columns": columns,
            "lines_by_page": lines_by_page, "status": status,
            "detail": (f"{say_name} 本地识别切出 {blocks} 个题块" if ok
                       else f"{say_name} 没探出题号链")}
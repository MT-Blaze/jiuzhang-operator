"""公式裁图通道调度（T6 §2 组合路＋§4 重认裁块）：坐标 → 同张题图裁块 → 送席。

坐标两条来源（都侦查过）：MinerU 本地结果包 middle_json.json 的公式块
归一化 bbox（存题身 extensions org.jiuzhang.editor 前缀）；文字卷文字层
charbox（pypdfium2）按题块区域换算到同张题图像素（D12：不撞老师框的图）。
无坐标＝不裸拼，交回整题重认兜底。通道按 catalog plan_recognize 步骤名
分派：ai＝云 VLM 单图、vlm_local＝本地千问、mineru/mineru_local＝MinerU、
formula_pp_m/formula_pp_l/formula_p2t＝公式专科（PP-M/L＋Pix2Text）；其余专科座 blocked 显性。失败 ok=False。
"""

from __future__ import annotations

import asyncio
import base64
import io
import logging
import re
from typing import Any, Callable

from app.core.ai.platform import center as ai_center
from app.core.ai.recognition import recognize as ai_recognize
from app.core.content import scan_text
from app.core.ingest.recognize import (
    formula_p2t, formula_pp_l, formula_pp_m, mineru_extract, mineru_local, mineru_service,
    shared as recognize_shared, vlm_local, vlm_service,
)

logger = logging.getLogger(__name__)

EDITOR_NS = "org.jiuzhang.editor"
CROP_DPI = 300
MAX_SPANS = 32
MIN_SPAN_PX = 8.0


def batch_context(batch_id: str) -> tuple[list[dict[str, Any]], bytes]:
    """批次的页图题块清单＋原卷 PDF 字节（文字层坐标用）；读不到就当没有。"""
    from app.core.pending import assets, service
    from app.core.pending.batch import batches
    from app.core.pending.db import connect

    try:
        page_images = service.list_batch_questions(batch_id).get("page_images") or []
    except Exception:  # noqa: BLE001 - 批次不在/库读不通只影响坐标来源
        page_images = []
    con = connect()
    try:
        row = batches.batch_row(con, batch_id)
        backup = str(row["source_backup"] or "") if row is not None else ""
    finally:
        con.close()
    for path in assets.backup_paths(backup):
        if path.suffix.lower() == ".pdf":
            try:
                return page_images, path.read_bytes()
            except OSError:
                break
    return page_images, b""


def _editor_ext(item: dict[str, Any]) -> dict[str, Any]:
    document = item.get("question") if isinstance(item.get("question"), dict) else {}
    extensions = document.get("extensions")
    if not isinstance(extensions, dict):
        return {}
    editor = extensions.get(EDITOR_NS)
    return editor if isinstance(editor, dict) else {}


def crop_png(png: bytes, bbox: list[float]) -> bytes:
    """按像素 bbox 从同张题图裁公式块；裁不出交空字节，绝不编图。"""
    from PIL import Image

    try:
        with Image.open(io.BytesIO(png)) as image:
            width, height = image.size
            x, y, w, h = (float(v) for v in bbox)
            x = max(0.0, min(x, width - 1))
            y = max(0.0, min(y, height - 1))
            right = min(float(width), x + max(w, 1.0))
            bottom = min(float(height), y + max(h, 1.0))
            if right - x < MIN_SPAN_PX or bottom - y < MIN_SPAN_PX:
                return b""
            out = io.BytesIO()
            image.crop((int(x), int(y), int(right), int(bottom))).save(out, "PNG")
            return out.getvalue()
    except Exception:  # noqa: BLE001 - 单块裁不出只影响这一块
        return b""


def _mineru_spans(item: dict[str, Any], png: bytes) -> list[dict[str, Any]]:
    """MinerU 公式块：归一化 0–1 bbox → 同张题图像素。"""
    from PIL import Image

    boxes = _editor_ext(item).get("formula_boxes")
    if not isinstance(boxes, list) or not boxes:
        return []
    try:
        with Image.open(io.BytesIO(png)) as image:
            width, height = image.size
    except Exception:  # noqa: BLE001
        return []
    spans = []
    for box in boxes[:MAX_SPANS]:
        if not isinstance(box, dict):
            continue
        bbox = box.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        x0, y0, x1, y1 = (float(v) for v in bbox)
        spans.append({"bbox": [x0 * width, y0 * height,
                               (x1 - x0) * width, (y1 - y0) * height],
                      "text": "", "latex": str(box.get("latex") or ""),
                      "origin": "mineru"})
    return spans


def _textlayer_spans(item: dict[str, Any], page_images: list[dict[str, Any]],
                     pdf_bytes: bytes) -> list[dict[str, Any]]:
    """文字层强数学串 → 题块区域内的公式 span（PDF 点 → 题图像素 @300dpi）。"""
    import pypdfium2

    pending_id = str(item.get("id") or "")
    region = entry = None
    for page in page_images:
        for candidate in page.get("regions") or []:
            if isinstance(candidate, dict) and str(candidate.get("pending_id") or "") == pending_id:
                region, entry = candidate, page
                break
        if region is not None:
            break
    if region is None or not pdf_bytes:
        return []
    try:
        page_no = int(entry.get("page") or 0)
        pixel_width = float(entry.get("width") or 0)
        pixel_height = float(entry.get("height") or 0)
        document = pypdfium2.PdfDocument(pdf_bytes)
        page = document[page_no - 1]
        page_width, page_height = (float(v) for v in page.get_size())
        textpage = page.get_textpage()
    except Exception:  # noqa: BLE001 - 坐标探不到只影响这一题
        return []
    spans: list[dict[str, Any]] = []
    try:
        if pixel_width <= 0 or pixel_height <= 0:
            return []
        scale_x = page_width / pixel_width
        scale_y = page_height / pixel_height
        origin_x = float(region.get("x") or 0) * scale_x
        origin_y = float(region.get("y") or 0) * scale_y
        factor = CROP_DPI / 72.0
        run_chars: list[str] = []
        run_box: list[float] = []

        def flush() -> None:
            if not run_chars or not scan_text._is_strong_math(run_chars):
                run_chars.clear()
                run_box.clear()
                return
            left, bottom, right, top = run_box
            x = (left - origin_x) * factor
            y = ((page_height - top) - origin_y) * factor
            w = (right - left) * factor
            h = (top - bottom) * factor
            if w >= MIN_SPAN_PX and h >= MIN_SPAN_PX and x >= -2 and y >= -2:
                spans.append({"bbox": [max(0.0, x), max(0.0, y), w, h],
                              "text": "".join(run_chars), "latex": "",
                              "origin": "textlayer"})
            run_chars.clear()
            run_box.clear()

        for index in range(textpage.count_chars()):
            char = textpage.get_text_range(index, 1)
            if char and scan_text._is_math_char(char) and not scan_text._is_cjk(char):
                box = textpage.get_charbox(index)
                run_chars.append(char)
                if not run_box:
                    run_box = list(box)
                else:
                    run_box[0] = min(run_box[0], box[0])
                    run_box[1] = min(run_box[1], box[1])
                    run_box[2] = max(run_box[2], box[2])
                    run_box[3] = max(run_box[3], box[3])
            else:
                flush()
        flush()
    finally:
        textpage.close()
        page.close()
        document.close()
    return spans[:MAX_SPANS]


def discover_spans(item: dict[str, Any], page_images: list[dict[str, Any]] | None = None,
                   pdf_bytes: bytes = b"") -> list[dict[str, Any]]:
    """一道题的公式坐标：MinerU extensions 优先，其次文字层；都没有＝空。"""
    png = recognize_shared.item_image_bytes(item)
    if not png:
        return []
    spans = _mineru_spans(item, png)
    if spans:
        return spans
    if page_images and pdf_bytes:
        return _textlayer_spans(item, page_images, pdf_bytes)
    return []


def _strip_math(text: str) -> str:
    return str(text or "").strip().strip("$").strip()


async def dispatch(entry: dict[str, Any], png: bytes,
                   item: dict[str, Any]) -> dict[str, Any]:
    """把一块公式图送选中席；按 catalog 步骤名分派，失败 ok=False 显性。"""
    if not png:
        return {"ok": False, "detail": "公式块裁不出来（坐标落在题图外或太小）"}
    steps = [str(step) for step in entry.get("plan_recognize") or []]
    step = steps[0] if steps else ""
    if step == "combo":
        return {"ok": False,
                "detail": "组合路是整批链路（文字直取＋公式裁图），不支持单块公式重认；请选公式专科座。"}
    if step == "ai":
        binding = ai_center.resolve_task("ocr")
        if not binding.is_configured:
            return {"ok": False, "detail": "「视觉识别(OCR)」还没指派可用模型"}
        url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        try:
            outcome = await ai_recognize.recognize(
                [url], context={"type": "formula", "stem": "", "question_no": ""},
                task="ocr")
        except Exception as exc:  # noqa: BLE001 - 出网失败显性
            return {"ok": False, "detail": "云端视觉公式识别失败：%s" % str(exc)[:200]}
        if not outcome.get("ok") or not outcome.get("question"):
            return {"ok": False, "detail": str(outcome.get("detail") or "云端视觉没认出公式")}
        latex = _strip_math(str(outcome["question"].get("stem") or ""))
        return {"ok": bool(latex), "latex": latex,
                "detail": "" if latex else "云端视觉返回的公式正文为空"}
    if step == "vlm_local":
        ready = await asyncio.to_thread(
            vlm_service.ensure_ready, str(entry.get("id") or "").removeprefix("vlm_"))
        if not ready.get("ok"):
            return {"ok": False, "detail": str(ready.get("detail") or "本地 VLM 不可用")}
        outcome = await asyncio.to_thread(
            vlm_local.recognize_image, png, ready, kind="formula")
        if not outcome.get("ok"):
            return {"ok": False, "detail": str(outcome.get("detail") or "本地 VLM 没认出公式")}
        return {"ok": True, "latex": str(outcome.get("latex") or ""),
                "detail": "本地 VLM 公式已转写"}
    if step in ("mineru", "mineru_local"):
        if step == "mineru_local":
            ready = await asyncio.to_thread(mineru_service.ensure_ready)
            if not ready.get("ok"):
                return {"ok": False, "detail": str(ready.get("detail") or "本地 MinerU 不可用")}
            outcome = await asyncio.to_thread(
                mineru_local.parse_image, "公式块.png", png, ready)
        else:
            binding = ai_center.find_mineru()
            if binding is None:
                return {"ok": False, "detail": "MinerU 没有可用的账号"}
            outcome = await asyncio.to_thread(
                mineru_extract.extract, "公式块.png", png,
                binding.base_url, binding.api_key,
                model=binding.model or "mineru")
        if not outcome.get("ok"):
            return {"ok": False, "detail": str(outcome.get("detail") or "MinerU 没认出公式")}
        latex = _strip_math(str(outcome.get("markdown") or ""))
        return {"ok": bool(latex), "latex": latex,
                "detail": "" if latex else "MinerU 返回的公式正文为空"}
    if step == "formula_pp_m":
        outcome = await asyncio.to_thread(formula_pp_m.recognize, png)
        return {"ok": bool(outcome.get("ok")), "latex": str(outcome.get("latex") or ""),
                "detail": str(outcome.get("detail") or "")}
    if step == "formula_pp_l":
        outcome = await asyncio.to_thread(formula_pp_l.recognize, png)
        return {"ok": bool(outcome.get("ok")), "latex": str(outcome.get("latex") or ""),
                "detail": str(outcome.get("detail") or "")}
    if step == "formula_p2t":
        outcome = await asyncio.to_thread(formula_p2t.recognize, png)
        return {"ok": bool(outcome.get("ok")), "latex": str(outcome.get("latex") or ""),
                "detail": str(outcome.get("detail") or "")}
    return {"ok": False,
            "detail": str(entry.get("detail") or "")
            or "专科推理通道下一卡开（D 卡擂台），本卡只登记；请选其他就绪座。"}


def replace_fragment(stem: str, span: dict[str, Any], new_latex: str) -> str | None:
    """原位替换（D12）：文字层按原串替换，原串已被归一包 $ 时按同规则推已知片段；
    MinerU 按已有 LaTeX 片段匹配。"""
    text = str(stem or "")
    original = str(span.get("text") or "")
    if original and original in text:
        return text.replace(original, "$%s$" % new_latex, 1)
    known = _strip_math(str(span.get("latex") or ""))
    if not known and str(span.get("origin") or "") == "textlayer" and original.strip(" \t"):
        # 题面已经 scan_text 归一包成 $...$，原串不复存在：按同一归一规则推已知片段。
        known = scan_text._run_to_latex(list(original.strip(" \t")))
    if known:
        for match in re.finditer(r"\$\$?([^$]+)\$\$?", text):
            if _strip_math(match.group(1)).replace(" ", "") == known.replace(" ", ""):
                return text[:match.start()] + "$%s$" % new_latex + text[match.end():]
    return None


def mark_pending(item: dict[str, Any], batch_id: str) -> bool:
    """公式待核标记（D11 口径）：正文保留文字直取，只挂 extensions 待核旗。"""
    document = dict(item.get("question") or {})
    extensions = dict(document.get("extensions") or {})
    editor = dict(extensions.get(EDITOR_NS) or {})
    editor["formula_pending"] = True
    extensions[EDITOR_NS] = editor
    document["extensions"] = extensions
    return recognize_shared.save_back(item, document, batch_id, "ingest.combo_formula")


def _surface(route: dict[str, Any], step: str, reason: str, detail: str) -> None:
    failures = route.setdefault("failures", [])
    for entry in failures:
        if entry.get("step") == step:
            return
    failures.append({"file": "", "page_no": 0, "step": step,
                     "reason": reason[:400], "detail": detail[:4000],
                     "retryable": True})


async def run_combo(batch_id: str, items: list[dict[str, Any]], indexes: list[int],
                    seat_id: str, route: dict[str, Any],
                    on_progress: Callable[[dict[str, Any]], None] | None,
                    page_images: list[dict[str, Any]], pdf_bytes: bytes) -> dict[str, Any]:
    """文字卷组合路：文字直取正文已在池里，这里只裁公式送席、原位替换。

    无坐标题进 no_coord_indexes 交整题兜底；公式座失败/未就绪→该题公式标
    待核＋失败清单显性，正文不动、不整题降级。
    """
    from app.core.ingest import registry

    entry = registry.entry_state(seat_id) if seat_id else None
    filled_indexes: list[int] = []
    no_coord_indexes: list[int] = []
    pending_marks = 0
    attempted = 0
    seat_ready = bool(entry and entry.get("state") == "ready" and entry.get("enabled", True))
    seat_reason = ""
    if entry is None:
        seat_reason = "自动分流默认公式座「%s」不在模型目录里，请到【模型配置】改选就绪座。" % (seat_id or "空")
    elif not seat_ready:
        seat_reason = "公式座「%s」未就绪（%s）。" % (entry.get("name") or seat_id,
                                                     entry.get("detail") or "不可用")
    for position, index in enumerate(indexes, start=1):
        item = items[index]
        spans = discover_spans(item, page_images, pdf_bytes)
        if not spans:
            no_coord_indexes.append(index)
            continue
        attempted += 1
        route["note"] = "组合路第 %d/%d 题：裁出 %d 个公式块，交「%s」转写…" % (
            position, len(indexes), len(spans), (entry or {}).get("name") or seat_id or "无")
        if on_progress:
            try:
                on_progress(route)
            except Exception:  # noqa: BLE001
                pass
        if not seat_ready:
            if mark_pending(item, batch_id):
                pending_marks += 1
            _surface(route, "识别·公式裁图", seat_reason,
                     "公式座未就绪，公式标待核，正文保留文字直取。")
            continue
        document = dict(item.get("question") or {})
        stem = str(document.get("stem") or "")
        changed = False
        last_detail = ""
        png = recognize_shared.item_image_bytes(item)
        for span in spans:
            outcome = await dispatch(entry, crop_png(png, span["bbox"]), item)
            if not outcome.get("ok"):
                last_detail = str(outcome.get("detail") or "")
                continue
            replaced = replace_fragment(stem, span, str(outcome.get("latex") or ""))
            if replaced is not None:
                stem = replaced
                changed = True
        if changed:
            document["stem"] = stem
            editor = dict(_editor_ext(item))
            editor.pop("formula_pending", None)
            extensions = dict(document.get("extensions") or {})
            extensions[EDITOR_NS] = editor
            document["extensions"] = extensions
            if recognize_shared.save_back(item, document, batch_id, "ingest.combo_formula"):
                filled_indexes.append(index)
        else:
            if mark_pending(item, batch_id):
                pending_marks += 1
            _surface(route, "识别·公式裁图",
                     "公式转写没成功（%s），该题公式标待核，正文保留文字直取。" % (last_detail or "不可用"),
                     last_detail)
    return {
        "ok": bool(filled_indexes) or (attempted == 0 and not no_coord_indexes),
        "attempted": attempted,
        "filled": len(filled_indexes),
        "filled_indexes": filled_indexes,
        "no_coord_indexes": no_coord_indexes,
        "pending_marks": pending_marks,
        "seat_ready": seat_ready,
        "seat_reason": seat_reason,
        "detail": "" if not pending_marks else ("%d 道题公式标待核" % pending_marks),
    }
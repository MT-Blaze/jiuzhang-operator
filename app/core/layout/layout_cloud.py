"""云端版面兜底：把页图交给视觉模型，只换回题块坐标。

它是瀑布流的最后一级，只在本地文本层与 YOLO 都探不出题块时才该被调用。
模型只许回答「框在哪」，不许替代识别引擎写题干；没有可用账号时直接失败，
绝不空跑一次出网。
"""

from __future__ import annotations

import base64
import re
from typing import Any

from app.core import ai_center, pending_assets, wire
from app.core.ai_client import OpenAICompatibleProvider

MAX_PAGES = 20
MAX_IMAGE_BYTES = 8 * 1024 * 1024
REQUEST_TIMEOUT = 120

SYSTEM_PROMPT = r"""你是试卷版面分析器。看一张试卷页图，只输出一个 JSON 对象，不要 Markdown 代码块，不要解释。
格式：{"regions":[{"no":1,"x":0,"y":0,"w":100,"h":80}]}
- 每道题一个框，按卷面阅读顺序编号（先左栏后右栏，栏内从上到下）。
- 坐标是相对整页图左上角的千分比（0-1000 的整数）；x/y 是左上角，w/h 是宽高。
- 框要覆盖题干、选项、答案与解析，但不许把相邻两题框进同一个框。
- 看不清是否是一道题时就不要框；宁缺毋滥，绝不编造题块。
"""

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.I)
_MIME = {".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".webp": "image/webp"}


async def detect(request: dict[str, Any]) -> dict[str, Any]:
    """逐页问云端要题块；单页失败只丢那一页。"""
    binding = ai_center.resolve_task("ocr")
    if not binding.is_configured:
        return _fail("「视觉识别(OCR)」还没指派可用模型，云端版面用不了")
    client = OpenAICompatibleProvider(
        api_key=binding.api_key, base_url=binding.base_url,
        default_model=binding.model, timeout=REQUEST_TIMEOUT, label=binding.name)
    pages: dict[int, list[dict[str, Any]]] = {}
    notes: list[str] = []
    for entry in (request.get("pages") or [])[:MAX_PAGES]:
        try:
            page_no = int(entry.get("page") or 0)
            width = float(entry.get("width") or 0)
            height = float(entry.get("height") or 0)
        except (TypeError, ValueError):
            continue
        image = _image_data_url(entry)
        if page_no <= 0 or width <= 0 or height <= 0 or not image:
            continue
        try:
            result = await client.chat_completion(
                system_prompt=SYSTEM_PROMPT,
                user_message="请只输出这一页的题块 JSON。",
                temperature=0.0, max_tokens=2000, images=[image])
            content = _unwrap(str(result.get("content") or ""))
            document = wire.loads(content)
        except Exception as exc:  # noqa: BLE001 - 单页失败只影响这一页
            notes.append(f"第 {page_no} 页云端版面失败：{exc}")
            continue
        regions = _regions_of(document, width, height)
        if regions:
            pages[page_no] = regions
    ok = bool(pages)
    return {
        "ok": ok,
        "engine": "cloud",
        "pages": pages,
        "columns": {page: 1 for page in pages},
        "detail": (f"云端探出 {len(pages)} 页题块" if ok
                   else "云端没探出题块" + (("：" + "；".join(notes[:2])) if notes else "")),
    }


def _unwrap(content: str) -> str:
    text = content.strip()
    fence = _FENCE.search(text)
    if fence:
        text = fence.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start >= 0 and end > start else text


def _image_data_url(entry: dict[str, Any]) -> str:
    name = str(entry.get("name") or "").strip()
    if not name:
        return ""
    try:
        raw = pending_assets.asset_path(name).read_bytes()
    except Exception:  # noqa: BLE001 - 页图不在就不出网
        return ""
    if not raw or len(raw) > MAX_IMAGE_BYTES:
        return ""
    suffix = ("." + name.rsplit(".", 1)[-1].lower()) if "." in name else ""
    mime = _MIME.get(suffix, "image/png")
    return f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")


def _regions_of(document: Any, width: float, height: float) -> list[dict[str, Any]]:
    raw = document.get("regions") if isinstance(document, dict) else None
    boxes: list[tuple[float, float, float, float]] = []
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            x = float(item.get("x") or 0)
            y = float(item.get("y") or 0)
            w = float(item.get("w") or 0)
            h = float(item.get("h") or 0)
        except (TypeError, ValueError):
            continue
        boxes.append((x, y, w, h))
    if not boxes:
        return []
    # 千分比与像素两种口径都认：最大值不超过 1000 且存在小数/边界外的才按千分比换算。
    scaled = max(max(box[0] + box[2], box[1] + box[3]) for box in boxes) <= 1000.0
    regions: list[dict[str, Any]] = []
    for order, (x, y, w, h) in enumerate(boxes, start=1):
        if scaled:
            x, w = x * width / 1000.0, w * width / 1000.0
            y, h = y * height / 1000.0, h * height / 1000.0
        if w < 8 or h < 8 or x < 0 or y < 0:
            continue
        w = min(w, max(1.0, width - x))
        h = min(h, max(1.0, height - y))
        regions.append({
            "no": order,
            "x": round(x, 1), "y": round(y, 1),
            "w": round(w, 1), "h": round(h, 1),
            "label": "", "text": "",
        })
    regions.sort(key=lambda region: (region["y"], region["x"]))
    for order, region in enumerate(regions, start=1):
        region["no"] = order
    return regions


def _fail(detail: str) -> dict[str, Any]:
    return {"ok": False, "engine": "cloud", "pages": {}, "columns": {},
            "detail": detail}

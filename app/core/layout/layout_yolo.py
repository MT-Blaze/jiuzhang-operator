"""本地 YOLO 版面探路：把页图交给本机部署的检测服务，换回题块坐标。

只认**本机**服务（``JZO_YOLO_LAYOUT_URL``），绝不偷偷连公网；没部署、
连不上、返回坏 JSON 都只算这一级失败，由调度员继续降级到云端。
YOLO 只交坐标、不交文字——正文交给识别引擎，绝不拿模型猜题面。
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.core import pending_assets

URL_ENV = "JZO_YOLO_LAYOUT_URL"
TIMEOUT_ENV = "JZO_YOLO_LAYOUT_TIMEOUT"
DEFAULT_TIMEOUT = 60.0
_MIME = {".png": "image/png", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".webp": "image/webp"}

def detect(request: dict[str, Any]) -> dict[str, Any]:
    """逐页调用本机 YOLO；任何一页失败只丢那一页。"""
    url = str(os.environ.get(URL_ENV) or "").strip()
    if not url:
        return _fail("本机没有部署 YOLO 版面服务（未设置 " + URL_ENV + "）")
    if not url.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]")):
        return _fail("YOLO 版面服务必须监听本机回环地址")
    pages: dict[int, list[dict[str, Any]]] = {}
    notes: list[str] = []
    for entry in request.get("pages") or []:
        try:
            page_no = int(entry.get("page") or 0)
            width = float(entry.get("width") or 0)
            height = float(entry.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if page_no <= 0 or width <= 0 or height <= 0:
            continue
        image = _page_image(entry)
        if not image:
            notes.append(f"第 {page_no} 页读不到页图")
            continue
        raw, mime = image
        try:
            reply = _post(url, {
                "page": page_no,
                "width": width,
                "height": height,
                "mime": mime,
                "image_b64": base64.b64encode(raw).decode("ascii"),
            })
        except Exception as exc:  # noqa: BLE001 - 单页失败继续下一张
            notes.append(f"第 {page_no} 页 YOLO 调用失败：{exc}")
            continue
        regions = _clean_regions(reply.get("regions"), width, height)
        if regions:
            pages[page_no] = regions
    ok = bool(pages)
    return {
        "ok": ok,
        "engine": "yolo",
        "pages": pages,
        "columns": {page: 1 for page in pages},
        "detail": (f"YOLO 探出 {len(pages)} 页题块" if ok
                   else "YOLO 没探出题块" + (("：" + "；".join(notes[:3])) if notes else "")),
    }


def _page_image(entry: dict[str, Any]) -> tuple[bytes, str] | None:
    name = str(entry.get("name") or "").strip()
    if not name:
        return None
    try:
        raw = pending_assets.asset_path(name).read_bytes()
    except Exception:  # noqa: BLE001 - 页图不在就交给下一级
        return None
    suffix = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return (raw, _MIME.get("." + suffix, "image/png")) if raw else None


def _post(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    timeout = _timeout()
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        document = json.loads(response.read(4 * 1024 * 1024).decode("utf-8", "replace"))
    return document if isinstance(document, dict) else {}


def _timeout() -> float:
    raw = str(os.environ.get(TIMEOUT_ENV) or "").strip()
    if not raw:
        return DEFAULT_TIMEOUT
    try:
        value = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT
    return value if 1.0 <= value <= 600.0 else DEFAULT_TIMEOUT


def _clean_regions(raw: Any, width: float, height: float) -> list[dict[str, Any]]:
    """服务返回值 → 与 ``page_render`` 同形的题块；越界框直接丢。"""
    regions: list[dict[str, Any]] = []
    for index, item in enumerate(raw if isinstance(raw, list) else []):
        if not isinstance(item, dict):
            continue
        try:
            x = float(item.get("x") or 0)
            y = float(item.get("y") or 0)
            w = float(item.get("w") or item.get("width") or 0)
            h = float(item.get("h") or item.get("height") or 0)
        except (TypeError, ValueError):
            continue
        if w <= 0 or h <= 0 or x < 0 or y < 0:
            continue
        w = min(w, width - x)
        h = min(h, height - y)
        if w < 8 or h < 8:
            continue
        number = item.get("no")
        regions.append({
            "no": int(number) if isinstance(number, int) or str(number).isdigit() else index + 1,
            "x": round(x, 1), "y": round(y, 1),
            "w": round(w, 1), "h": round(h, 1),
            "label": " ".join(str(item.get("label") or "").split())[:48],
            "text": str(item.get("text") or "")[:2000],
        })
    regions.sort(key=lambda region: (region["y"], region["x"]))
    for order, region in enumerate(regions, start=1):
        region["no"] = order
    return regions


def _fail(detail: str) -> dict[str, Any]:
    return {"ok": False, "engine": "yolo", "pages": {}, "columns": {},
            "detail": detail}

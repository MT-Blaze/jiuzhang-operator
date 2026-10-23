"""题目配图上传：把插件框选/切出的本地截图落进当前工作区 ``uploads/``。

插件拿不到文件系统与写令牌，只能把 Canvas 截图以 data URL 交给宿主，
宿主再带一次性令牌 POST 到这里（PLUGIN_SPEC §2.6 ``asset.upload``）。

安全边界（AGENTS §5）：

- 只认 PNG / JPEG / WebP，且必须与声明 MIME 的**魔数**一致；SVG 直接拒绝
  （可内嵌脚本，不能当作图片放行）；
- 文件名一律由底座生成（``img_<hex>.<ext>``），请求里的任何路径片段都不参与落盘；
- 解码后硬上限 8 MiB，避免把本机磁盘和后续读接口拖垮；
- 先写临时文件再原子改名，半截文件不会以图片身份被读到。
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import os
import re
import secrets
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.config import settings
from app.core.security import require_write_token

router = APIRouter(tags=["assets"])

MAX_ASSET_BYTES = 8 * 1024 * 1024
# base64 比原文大约 4/3；再留一点给 data URL 头与换行
MAX_DATA_URL_CHARS = 12 * 1024 * 1024
DATA_URL_RE = re.compile(r"^data:(image/(?:png|jpeg|webp));base64,([A-Za-z0-9+/=]+)$")
EXTENSIONS = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}


def _sniff_mime(data: bytes) -> str:
    """按魔数认图；不认识就回空串（绝不信请求自报的 MIME）。"""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return ""


@router.post("/api/assets", status_code=201, summary="上传题目配图（框选切图）",
             dependencies=[Depends(require_write_token)])
def upload_asset(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """接收 ``{"data_url": "data:image/png;base64,..."}``，返回资产 id 与托管地址。"""
    data_url = body.get("data_url")
    if not isinstance(data_url, str) or not data_url:
        raise HTTPException(status_code=400, detail="缺少 data_url")
    if len(data_url) > MAX_DATA_URL_CHARS:
        raise HTTPException(status_code=400, detail="图片过大（解码后上限 8 MiB）")
    matched = DATA_URL_RE.match(data_url)
    if matched is None:
        raise HTTPException(status_code=400, detail="只接受 PNG / JPEG / WebP 的 base64 data URL")
    declared, payload = matched.group(1), matched.group(2)
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="图片 base64 内容不合法") from exc
    if not raw:
        raise HTTPException(status_code=400, detail="图片内容为空")
    if len(raw) > MAX_ASSET_BYTES:
        raise HTTPException(status_code=400, detail="图片过大（解码后上限 8 MiB）")
    actual = _sniff_mime(raw)
    if not actual:
        raise HTTPException(status_code=400, detail="不是可识别的 PNG / JPEG / WebP 图片")
    if actual != declared:
        raise HTTPException(status_code=400, detail="图片魔数与声明的格式不一致")

    root = settings.uploads_dir
    root.mkdir(parents=True, exist_ok=True)
    suffix = EXTENSIONS[actual]
    for _ in range(5):
        asset_id = "img_" + secrets.token_hex(8)
        target = root / (asset_id + suffix)
        if target.exists():
            continue
        temp = root / (".upload-" + secrets.token_hex(8) + ".tmp")
        try:
            temp.write_bytes(raw)
            os.replace(temp, target)
        finally:
            if temp.exists():
                temp.unlink()
        return {
            "id": asset_id,
            "uri": "/static/uploads/" + target.name,
            "mime": actual,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    raise HTTPException(status_code=500, detail="生成资产文件名失败，请重试")

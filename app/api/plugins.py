"""插件发现、只读资产服务与用户自填地址的索引拉取。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from app.core import plugin_index
from app.core.plugins import (
    PluginAssetError,
    discover_plugins,
    resolve_plugin_asset,
)
from app.core.security import require_write_token

router = APIRouter(tags=["plugins"])

_MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".webp": "image/webp",
    ".woff2": "font/woff2",
}


@router.get("/api/plugins", summary="发现已安装插件")
async def list_plugins() -> dict:
    return discover_plugins()


@router.post(
    "/api/plugins/index",
    summary="按用户填入的地址拉取插件索引（只读，不解压不安装）",
    dependencies=[Depends(require_write_token)],
)
def read_plugin_index(payload: dict[str, Any] = Body(...)) -> dict:
    """底座不写死任何索引地址：URL 只能由用户在这一步亲手交进来。

    带写令牌不是为了「改数据」，而是因为这是唯一会替用户发起外部请求的入口，
    不能让浏览器里另一个页面的脚本随手驱动。

    同步函数不是省事：FastAPI 会把它放进线程池执行。写成 ``async def`` 会让
    阻塞的 urllib 卡住事件循环——用户填一个指向本底座自己的地址就直接自锁死。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    try:
        return plugin_index.fetch_index(str(payload.get("url", "")))
    except plugin_index.IndexRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plugin-assets/{plugin_id}/{asset_path:path}", include_in_schema=False)
async def plugin_asset(plugin_id: str, asset_path: str, request: Request) -> FileResponse:
    try:
        path: Path = resolve_plugin_asset(plugin_id, asset_path)
    except PluginAssetError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    media_type = _MEDIA_TYPES.get(path.suffix.lower())
    if media_type is None:
        raise HTTPException(status_code=404, detail="不允许的插件资源类型")

    headers = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "no-cache",
    }
    if media_type.startswith("text/html"):
        # 沙箱 iframe 没有 allow-same-origin，文档处于不透明源，
        # 仅写 'self' 会让插件脚本全部被拦截；因此额外授权宿主自身的源。
        origin = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"
        headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            f"script-src 'self' {origin}; "
            f"style-src 'self' {origin}; "
            f"img-src 'self' {origin}; "
            "connect-src 'none'; base-uri 'none'; form-action 'none'"
        )
    return FileResponse(path, media_type=media_type, headers=headers)

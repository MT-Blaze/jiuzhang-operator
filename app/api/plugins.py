"""插件发现与只读资产服务。"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from app.core.plugins import (
    PluginAssetError,
    discover_plugins,
    resolve_plugin_asset,
)

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

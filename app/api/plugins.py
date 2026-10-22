"""插件发现、只读资产服务、索引拉取、本机 zip 安装与在线安装（按需下载单个 zip）。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core import plugin_index
from app.core.plugin_download import download_plugin_zip
from app.core.plugin_install import (
    MAX_ZIP_BYTES,
    PluginInstallError,
    install_plugin_from_zip,
)
from app.core.plugins import (
    PluginAssetError,
    discover_plugins,
    resolve_plugin_asset,
)
from app.core.security import require_write_token

router = APIRouter(tags=["plugins"])


class InstalledPlugin(BaseModel):
    """安装成功后下发的插件信息，与 GET /api/plugins 的条目同构。"""

    id: str
    name: str
    version: str
    api_version: str
    kind: str
    description: str
    author: str | None = None
    license: str
    slots: list[str]
    capabilities: list[str]
    permissions: list[str]
    entry_url: str
    css_url: str | None = None


class PluginInstallResponse(BaseModel):
    installed: bool
    plugin: InstalledPlugin


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
    "/api/plugins/install",
    response_model=PluginInstallResponse,
    summary="安装用户亲手上传的插件 zip 包（本机拖拽/选文件；在线安装走 install-url）",
    dependencies=[Depends(require_write_token)],
)
async def install_plugin(request: Request, replace: bool = False) -> PluginInstallResponse:
    """把用户拖进来的 zip 校验后落地 plugins/。

    安全底线（PLUGIN_SPEC §1.2）：拒绝加密条目、符号链接、绝对路径、``..``
    穿越与嵌套 zip；条目数与解压总量设上限；先暂存校验、后落地。
    请求体就是 zip 二进制本身（Content-Type: application/zip），
    不走 multipart——底座不为此引入 python-multipart 依赖（STACK §0）。
    """
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_ZIP_BYTES:
        raise HTTPException(status_code=413, detail="zip 包超过 50 MB 上限")

    chunks: list[bytes] = []
    received = 0
    async for chunk in request.stream():
        received += len(chunk)
        if received > MAX_ZIP_BYTES:
            raise HTTPException(status_code=413, detail="zip 包超过 50 MB 上限")
        chunks.append(chunk)

    try:
        # 解压与磁盘 IO 是阻塞操作，放线程池执行，不卡事件循环
        info = await run_in_threadpool(install_plugin_from_zip, b"".join(chunks), replace)
    except PluginInstallError as exc:
        raise HTTPException(
            status_code=exc.status, detail={"message": exc.message, "code": exc.code}
        ) from exc
    return PluginInstallResponse(installed=True, plugin=InstalledPlugin(**info))


@router.post(
    "/api/plugins/install-url",
    response_model=PluginInstallResponse,
    summary="在线安装：按用户点选的索引条目地址下载单个 zip 并走本机安装同款校验落地",
    dependencies=[Depends(require_write_token)],
)
def install_plugin_from_url(payload: dict[str, Any] = Body(...)) -> PluginInstallResponse:
    """用户点了索引卡片上的【在线安装】才会进到这里：只下载那一个 zip。

    与 §1.3 索引拉取同款信任模型——地址来自用户当场点选的条目，底座不预置
    任何下载源、不自动更新。同步函数不是省事：FastAPI 放线程池执行，下载
    与解压都是阻塞 IO，写成 ``async def`` 会把事件循环卡死（PLUGIN_SPEC §1.4）。

    失败回滚：下载半途出错只是丢弃内存里的字节；安装走暂存区校验 + 原子
    改名落地，任何一步失败 ``plugins/`` 都不留半个文件。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    url = payload.get("url")
    replace = bool(payload.get("replace", False))
    if not isinstance(url, str):
        raise HTTPException(status_code=400, detail="缺少要下载的 zip 地址（url）")

    try:
        data = download_plugin_zip(url)
        info = install_plugin_from_zip(data, replace)
    except PluginInstallError as exc:
        raise HTTPException(
            status_code=exc.status, detail={"message": exc.message, "code": exc.code}
        ) from exc
    return PluginInstallResponse(installed=True, plugin=InstalledPlugin(**info))


@router.post(
    "/api/plugins/index",
    summary="按用户填入的地址拉取插件索引（只读，不解压不安装）",
    dependencies=[Depends(require_write_token)],
)
def read_plugin_index(payload: dict[str, Any] = Body(...)) -> dict:
    """索引地址来自前端输入框（默认预填官方 Raw 直链，用户可当场改掉）。

    带写令牌不是为了「改数据」，而是因为它会替用户发起外部请求，
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

"""插件发现、只读资产服务、索引拉取、本机 zip 安装与在线安装（按需下载单个 zip）。"""

from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.core import plugin_index, plugin_search, plugin_state, plugin_update
from app.core.config import settings
from app.core.plugin_download import download_plugin_zip_sources
from app.core.plugin_install import (
    MAX_ZIP_BYTES,
    PluginInstallError,
    install_plugin_from_zip,
)
from app.core.plugin_lifecycle import PluginUninstallError, uninstall_plugin
from app.core.plugins import (
    PluginAssetError,
    discover_plugins,
    resolve_plugin_asset,
)
from app.core.security import require_write_token

router = APIRouter(tags=["plugins"])

# 用户点【更新并重启】后，先让响应回到浏览器再结束自身进程的等待时间
RESTART_DELAY_MS = 800


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
    ui: dict[str, Any] | None = None
    stage: dict[str, Any] | None = None
    bus: dict[str, Any] | None = None
    min_host_version: str = ""
    # 渲染/工具类插件可显式声明不占左栏；缺省一律显示。
    show_in_sidebar: bool = True


class PluginInstallResponse(BaseModel):
    installed: bool
    plugin: InstalledPlugin
    source_host: str | None = None


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

    raw_mirrors = payload.get("mirrors", [])
    if raw_mirrors is None:
        raw_mirrors = []
    if not isinstance(raw_mirrors, list):
        raise HTTPException(status_code=400, detail="mirrors 必须是数组")
    mirrors = [item for item in raw_mirrors[:8] if isinstance(item, str)]

    try:
        data, used_url = download_plugin_zip_sources(url, mirrors)
        info = install_plugin_from_zip(data, replace)
    except PluginInstallError as exc:
        raise HTTPException(
            status_code=exc.status, detail={"message": exc.message, "code": exc.code}
        ) from exc
    return PluginInstallResponse(
        installed=True,
        plugin=InstalledPlugin(**info),
        source_host=plugin_index.describe_public_url(used_url),
    )


@router.post(
    "/api/plugins/index",
    summary="按用户填入的地址拉取插件索引（只读，不解压不安装）",
    dependencies=[Depends(require_write_token)],
)
def read_plugin_index(payload: dict[str, Any] = Body(...)) -> dict:
    """索引地址来自前端输入框（默认预填官方国内镜像，用户可当场改掉）。

    官方地址拉取失败时按 ``plugin_sources`` 的备用镜像自动回退；用户填第三方
    地址时只访问那一个地址，不擅自换源。带写令牌不是为了「改数据」，而是因为
    它会替用户发起外部请求，不能让浏览器里另一个页面的脚本随手驱动。

    同步函数不是省事：FastAPI 会把它放进线程池执行。写成 ``async def`` 会让
    阻塞的 urllib 卡住事件循环——用户填一个指向本底座自己的地址就直接自锁死。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    allow_mirrors = payload.get("allow_mirrors", True) is not False
    try:
        index = plugin_index.fetch_index(str(payload.get("url", "")), allow_mirrors=allow_mirrors)
    except plugin_index.IndexRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # 只缓存用户亲手拉取成功的清单，供对话里的插件搜索离线使用；
    # 缓存失败不影响本次拉取结果（plugin_search 会回落到「尚未拉取」提示）。
    plugin_search.save_index_cache(index)
    return index


@router.post(
    "/api/plugins/{plugin_id}/enabled",
    summary="启用/停用插件（停用只从导航摘除并释放内存，代码与数据原地保留）",
    dependencies=[Depends(require_write_token)],
)
def set_plugin_enabled(plugin_id: str, payload: dict[str, Any] = Body(...)) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("enabled"), bool):
        raise HTTPException(status_code=400, detail="enabled 必须是布尔值")
    if not (Path(plugin_id).name == plugin_id and plugin_id):
        raise HTTPException(status_code=400, detail="插件 ID 非法")
    if not (Path(settings.plugins_dir) / plugin_id / "plugin.json").is_file():
        raise HTTPException(status_code=404, detail=f"插件不存在：{plugin_id}")
    enabled = payload["enabled"]
    plugin_state.set_enabled(plugin_id, enabled)
    return {"id": plugin_id, "enabled": enabled}


@router.post(
    "/api/plugins/{plugin_id}/nickname",
    summary="给插件起自定义昵称（空串即清掉，回落官方原名；只写本机状态文件）",
    dependencies=[Depends(require_write_token)],
)
def set_plugin_nickname(plugin_id: str, payload: dict[str, Any] = Body(...)) -> dict:
    """昵称是老师给插件起的名字，不是清单字段——发布件不许被本机改动污染。

    写范围只有 ``data/plugin_state.json``（ADR-007）：插件代码目录与题库原地不动。
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("nickname"), str):
        raise HTTPException(status_code=400, detail="nickname 必须是字符串")
    if not (Path(plugin_id).name == plugin_id and plugin_id):
        raise HTTPException(status_code=400, detail="插件 ID 非法")
    if not (Path(settings.plugins_dir) / plugin_id / "plugin.json").is_file():
        raise HTTPException(status_code=404, detail=f"插件不存在：{plugin_id}")
    nickname = plugin_state.set_nickname(plugin_id, payload["nickname"])
    return {"id": plugin_id, "nickname": nickname}


@router.post(
    "/api/plugins/sidebar",
    summary="整棵左栏树落盘（拖拽排序与右键建文件夹的唯一写口）",
    dependencies=[Depends(require_write_token)],
)
def set_plugin_sidebar(payload: dict[str, Any] = Body(...)) -> dict:
    """左栏顺序是「已启用列表顺序」的唯一事实来源：两边读同一棵树。

    非法条目由 :func:`normalize_sidebar` 宽容剔除，不会因为一处手滑把树清零。
    """
    if not isinstance(payload, dict) or not isinstance(payload.get("sidebar"), list):
        raise HTTPException(status_code=400, detail="sidebar 必须是数组")
    return {"sidebar": plugin_state.set_sidebar(payload["sidebar"])}


@router.delete(
    "/api/plugins/{plugin_id}",
    summary="卸载插件；keep_data=false 时连同各工作区的物理题库一并销毁",
    dependencies=[Depends(require_write_token)],
)
def uninstall(plugin_id: str, keep_data: bool = True) -> dict:
    try:
        return uninstall_plugin(plugin_id, keep_data=keep_data)
    except PluginUninstallError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from exc


# ------------------------------------------------- 双轨更新（PLUGIN_SPEC §1.7）
#
# 出网铁律（AGENTS §2 / 裁决 1、2）：下面五个端点没有任何一个会被定时器、启动钩子
# 或对话工具触发——它们的唯一入口是设置页上用户当场的那一次点击。
# 检查更新只发一次只读 GET；批量下载只发生在【一键更新全部插件】这一次点击里，
# 跑完即止，不排队、不续跑、不重试。写范围只有 plugins/<id>/ 与底座程序文件，
# 严禁触碰 data/（唯一例外是 data/update_state.json 这份续更清单）。

def _index_for_check(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """取本次检查用的索引：给了 url 就当场拉一次，否则复用用户上一轮亲手拉回的缓存。"""
    url = payload.get("url")
    if isinstance(url, str) and url.strip():
        allow_mirrors = payload.get("allow_mirrors", True) is not False
        try:
            index = plugin_index.fetch_index(url.strip(), allow_mirrors=allow_mirrors)
        except plugin_index.IndexRejected as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        plugin_search.save_index_cache(index)
        return index, "fetched"

    cached = plugin_search.load_index_cache()
    if cached is None:
        raise HTTPException(
            status_code=409,
            detail="本机还没有插件索引缓存。请先在「插件索引」页点【拉取清单】，"
                   "或在本次请求里给出 url（底座不会自己出网）。",
        )
    return cached, "cache"


@router.post(
    "/api/plugins/update/check",
    summary="双轨更新·检查：把已装插件与索引对账（只在用户点【检查更新】后出网）",
    dependencies=[Depends(require_write_token)],
)
def check_updates_endpoint(payload: dict[str, Any] = Body(default={})) -> dict:
    """产出「哪些插件有新版本 / 哪些需先更新底座 / 底座自己要不要更新」这张表。

    只读对账，不解压、不执行、不落地任何文件。版本写坏或索引没收录的条目
    只让它自己出局并带上原因，不牵连其他插件（PLUGIN_SPEC §1.7）。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    index, source = _index_for_check(payload)
    result = plugin_update.check_updates(index)
    result["index_source"] = source
    result["source_host"] = str(index.get("source_host") or "")
    result["saved_at"] = str(index.get("saved_at") or index.get("fetched_at") or "")
    return result


@router.post(
    "/api/plugins/update/apply",
    summary="双轨更新·执行：下载并热更插件（一次点击 = 一次批量任务，跑完即止）",
    dependencies=[Depends(require_write_token)],
)
def apply_updates_endpoint(payload: dict[str, Any] = Body(...)) -> dict:
    """``{"all": true}`` = 用户点【一键更新全部插件】；``{"ids": [...]}`` = 只更点选的那几个。

    范围就是本次检查结果里「有更新且兼容」的条目，不多不少：不兼容与版本写坏的
    一律跳过并如实列进 ``skipped``，**绝不覆盖本地代码**。串行执行、不跨条目借源，
    失败逐条记原因，由人再点一次。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    want_all = payload.get("all") is True
    raw_ids = payload.get("ids") or []
    if not isinstance(raw_ids, list):
        raise HTTPException(status_code=400, detail="ids 必须是数组")
    wanted = [item for item in raw_ids if isinstance(item, str) and item]
    if not want_all and not wanted:
        raise HTTPException(status_code=400, detail="要么给出 all=true，要么列出要更新的插件 ids")

    index, source = _index_for_check(payload)
    checked = plugin_update.check_updates(index)
    rows = checked["plugins"]
    if not want_all:
        rows = [row for row in rows if row["id"] in set(wanted)]
        missing = set(wanted) - {row["id"] for row in rows}
        if missing:
            raise HTTPException(status_code=404,
                                detail="这些插件本机没装，无从更新：" + "、".join(sorted(missing)))

    result = plugin_update.apply_updates(rows)
    result["index_source"] = source
    result["host"] = checked["host"]
    return result


@router.get(
    "/api/plugins/update/pending",
    summary="双轨更新·续更待办：读 data/update_state.json（底座唯一允许写进 data/ 的更新痕迹）",
    dependencies=[Depends(require_write_token)],
)
def pending_updates_endpoint() -> dict:
    state = plugin_update.read_pending()
    state["path"] = str(plugin_update.pending_path())
    state["last_resume"] = plugin_update.last_resume()
    return state


@router.post(
    "/api/plugins/update/pending-clear",
    summary="双轨更新·作废续更待办（补齐跑完或用户明确要求清空）",
    dependencies=[Depends(require_write_token)],
)
def clear_pending_updates_endpoint() -> dict:
    return {"cleared": True, **plugin_update.clear_pending()}


@router.post(
    "/api/plugins/update/host-apply",
    summary="双轨更新·底座自更新：下载校验新版本并生成一次性 update.bat（重启由用户点【更新并重启】触发）",
    dependencies=[Depends(require_write_token)],
)
def host_update_endpoint(payload: dict[str, Any] = Body(...)) -> dict:
    """``launch`` 缺省为 ``false``：只下载、校验、生成脚本，不动正在运行的底座。

    ``launch=true``（用户点【更新并重启】）才会拉起脚本并结束自身进程；开发工作树
    （存在 ``.git``）直接 409 拒绝——robocopy 覆盖正在运行的工作树会抹掉未提交的活儿。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    index, _source = _index_for_check(payload)
    host_block = index.get("host")
    if not isinstance(host_block, dict):
        raise HTTPException(status_code=409, detail="索引没有声明底座新版本（host 块缺失）")

    port = payload.get("port")
    try:
        prepared = plugin_update.prepare_host_update(
            host_block, port=int(port) if isinstance(port, (int, str)) and str(port).isdigit() else None)
    except plugin_update.UpdateRejected as exc:
        raise HTTPException(status_code=409, detail={"message": exc.message, "code": exc.code}) from exc
    except PluginInstallError as exc:
        raise HTTPException(status_code=exc.status,
                            detail={"message": exc.message, "code": exc.code}) from exc

    if payload.get("launch") is not True:
        return {"launched": False, "restart_scheduled": False, **prepared}

    try:
        plugin_update.launch_host_update(prepared["script_path"])
    except plugin_update.UpdateRejected as exc:
        raise HTTPException(status_code=409, detail={"message": exc.message, "code": exc.code}) from exc
    threading.Thread(target=_terminate_after_response, daemon=True).start()
    return {"launched": True, "restart_scheduled": True, "restart_in_ms": RESTART_DELAY_MS, **prepared}


def _terminate_after_response() -> None:  # pragma: no cover - 只在真机重启路径上执行
    """让 HTTP 响应先回到浏览器，再结束自身进程交给 update.bat 接管。"""
    time.sleep(RESTART_DELAY_MS / 1000)
    plugin_update.terminate_self()


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
            # KaTeX 用内联 style 描公式间距；内联样式不能执行脚本，风险可控
            f"style-src 'self' 'unsafe-inline' {origin}; "
            f"img-src 'self' {origin}; "
            # 公式要字体：KaTeX 的 woff2 由宿主静态目录提供，缺了会退化成豆腐块
            f"font-src 'self' {origin}; "
            "connect-src 'none'; base-uri 'none'; form-action 'none'"
        )
    return FileResponse(path, media_type=media_type, headers=headers)

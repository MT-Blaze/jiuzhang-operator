"""九章算子底座入口。

底座只负责装配：健康检查、静态资源、只读契约入口。
业务能力一律由插件提供，见 docs/PLUGIN_SPEC.md。
"""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path, PurePosixPath

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.agents import router as agents_router
from app.api.ai_center import router as ai_center_router
from app.api.assets import router as assets_router
from app.api.bank import router as bank_router
from app.api.health import router as health_router
from app.api.ingest import router as ingest_router
from app.api.layout import router as layout_router
from app.api.meta import router as meta_router
from app.api.pending import router as pending_router
from app.api.plugins import router as plugins_router
from app.api.providers import router as providers_router
from app.api.questions import router as questions_router
from app.api.settings import router as settings_router
from app.api.workspaces import router as workspaces_router
from app.core import plugin_update, pwa, workspace_bootstrap
from app.core.config import current_workspace_id, settings
from app.core.db import init_db
from app.core.plugins import discover_plugins
from app.core.security import local_write_token


def _serve_local_asset(root: Path, asset_path: str) -> FileResponse:
    """按当前工作区的资源根读一张本地图片，越界一律 404。

    uploads/（题目正式配图）与 pending_assets/（中转站暂存配图）共用这一套
    边界：拒绝绝对路径、``..``、隐藏段与符号链接，扩展名只认图片。
    """
    resolved = root.resolve()
    relative = PurePosixPath(asset_path.replace("\\", "/"))
    if (
        not relative.parts
        or relative.is_absolute()
        or ".." in relative.parts
        or relative.parts[0].startswith(".")
    ):
        raise HTTPException(status_code=404, detail="资源路径非法")
    target = resolved.joinpath(*relative.parts)
    if target.is_symlink():
        raise HTTPException(status_code=404, detail="不允许符号链接")
    try:
        target.resolve().relative_to(resolved)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="资源路径越界") from exc
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".gif": "image/gif",
    }
    media_type = media_types.get(target.suffix.lower())
    if media_type is None or not target.is_file():
        raise HTTPException(status_code=404, detail="资源不存在")
    return FileResponse(
        target,
        media_type=media_type,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "public, max-age=86400",
        },
    )


# 宿主壳（HTML/JS/CSS）一律禁止落缓存。只写 no-cache 不够：Chrome 的软刷新
# （F5）会把 no-cache 的响应从内存缓存里直接复用，旧 stage.js 就会让页签关闭叉
# 消失，只有 Ctrl+F5 才恢复；no-store + must-revalidate 才能保证每次刷新都取最新代码。
NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


class RevalidatingStaticFiles(StaticFiles):
    """静态资源一律禁止浏览器缓存（no-store + must-revalidate）。

    Starlette 的 StaticFiles 默认不带 Cache-Control，浏览器按 Last-Modified
    猜一个启发式保鲜期，旧版脚本会在缓存里活很久；加 no-cache 后普通刷新仍可能
    命中内存缓存。本站是 127.0.0.1 本地服务，每次都回源的成本可以忽略，
    换来「刷新即最新」，也杜绝「F5 丢功能、Ctrl+F5 才正常」这类假 bug。
    """

    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            for name, value in NO_CACHE_HEADERS.items():
                response.headers[name] = value
        return response

# 走 uvicorn 自己的 logger：应用自建 logger 在没有 handler 时，INFO 记录会被
# logging.lastResort 直接丢掉（它只兜 WARNING+），更新记录就真的「静默」不见了。
logger = logging.getLogger("uvicorn.error")


def _resume_plugin_updates() -> None:
    """重启续更：把上一轮用户亲手点选、因底座重启没更完的插件补齐。

    **只消费 ``data/update_state.json`` 与本机已下载的包，不出网**（AGENTS §2
    出网铁律的续更例外）。放在守护线程里跑：补齐失败绝不能挡住启动，
    用户打开设置页还能再点一次。
    """
    try:
        outcome = plugin_update.resume_pending()
    except Exception:  # noqa: BLE001 - 续更是增强能力，任何异常都不许拖垮底座
        logger.exception("重启续更失败，已跳过；可在「设置与控制台 → 插件」里再点一次更新")
        return
    if not outcome.get("had_pending"):
        return
    for row in outcome.get("resumed") or []:
        logger.info("续更完成：%s %s → %s（保住本机文件 %d 个）", row.get("id"),
                    row.get("from") or "?", row.get("to"), len(row.get("preserved") or []))
    for row in outcome.get("failed") or []:
        logger.warning("续更失败：%s（%s）", row.get("id"), row.get("reason"))


def _log_plugin_dependency_problems() -> None:
    """启动时点名缺依赖的插件（PLUGIN_SPEC §1.8）。

    发现流程已把它们置为 enabled=false，这里只是让老师在控制台也看得见原因；
    自检失败只记日志，绝不因为一个坏插件拖垮底座启动。
    """
    try:
        report = discover_plugins()
    except Exception:  # noqa: BLE001 - 自检是增强能力，不允许挡住启动
        logger.exception("插件依赖自检失败，已跳过")
        return
    for row in report.get("dependency_blocked") or []:
        logger.warning("插件依赖不满足：%s", row.get("reason") or row.get("id"))


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # 军令 #18：先装载工作区指针、迁移旧全局数据并生成 plugins/ 结构，
    # 之后所有插件路径才按当前工作区求值。
    workspace_bootstrap.bootstrap()
    init_db()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    _log_plugin_dependency_problems()
    # v0.8.0：不再首启自动安装示例题库插件（demo-bank 属历史包袱）；
    # 插件一律由用户在「设置 → 插件管理与控制」里亲手装。
    threading.Thread(target=_resume_plugin_updates, name="jzo-update-resume", daemon=True).start()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Jiuzhang Operator",
        version=__version__,
        description="九章算子底座：鉴权、导航、数据总线与插件生命周期。",
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.include_router(health_router)
    app.include_router(questions_router)
    app.include_router(plugins_router)
    app.include_router(providers_router)
    app.include_router(ai_center_router)
    app.include_router(agents_router)
    app.include_router(workspaces_router)
    app.include_router(bank_router)
    app.include_router(assets_router)
    app.include_router(pending_router)
    app.include_router(meta_router)
    app.include_router(ingest_router)
    app.include_router(layout_router)
    app.include_router(settings_router)

    @app.get("/static/uploads/{asset_path:path}", include_in_schema=False)
    async def read_upload(asset_path: str) -> FileResponse:
        """题目配图：只读当前工作区 uploads/，拒绝穿越、符号链接与非图片扩展名。

        不能直接 mount 一个固定目录：工作区切换后上传根会变，路由必须按请求
        当时的 ``settings.uploads_dir`` 解析（见 PLUGIN_SPEC §3.1）。
        """
        return _serve_local_asset(settings.uploads_dir, asset_path)

    @app.get("/static/pending/{asset_path:path}", include_in_schema=False)
    async def read_pending_asset(asset_path: str) -> FileResponse:
        """中转站配图：只读当前工作区 pending_assets/，边界与 uploads 那条一模一样。

        池子里的题配图不进 uploads/，这条路由就是它在审核界面的唯一出口。
        """
        return _serve_local_asset(settings.pending_assets_dir, asset_path)

    @app.get("/static/pool/{asset_path:path}", include_in_schema=False)
    async def read_pool_asset(asset_path: str) -> FileResponse:
        """重题池成品图：只读当前工作区 pool_assets/，边界与 pending 那条一模一样。

        池里这条的图是抽走时复制出来的**独立一份**，批次消失、原文件副本被清掉
        都跟它无关（军令 #32 · 判据 4.2/4.7）。
        """
        return _serve_local_asset(settings.pool_assets_dir, asset_path)

    app.mount("/static", RevalidatingStaticFiles(directory=settings.static_dir), name="static")

    @app.get("/sw.js", include_in_schema=False)
    async def read_service_worker() -> FileResponse:
        """根作用域 Service Worker，供浏览器识别「安装为应用」。

        只做网络透传、不缓存，避免旧页面被 SW 锁死；放在根路径是为了让
        scope 覆盖整站，而不是被 /static/ 限制住。
        """
        return FileResponse(
            settings.static_dir / "sw.js",
            media_type="application/javascript; charset=utf-8",
            headers={
                **NO_CACHE_HEADERS,
                "Service-Worker-Allowed": "/",
            },
        )

    @app.get(pwa.MANIFEST_PATH, include_in_schema=False)
    async def read_web_manifest() -> JSONResponse:
        """PWA 清单：Web 标准强制 JSON，内容由 dataclass 生成，磁盘上不留 .json 文件。"""
        return JSONResponse(
            content=pwa.MANIFEST.as_dict(),
            media_type=pwa.MANIFEST_MEDIA_TYPE,
            headers=NO_CACHE_HEADERS,
        )

    @app.get("/", include_in_schema=False)
    async def read_root() -> FileResponse:
        """根路径直达工作台（10.24 军令任务 1）：用户打开浏览器就该看到能干活的地方，
        底座介绍页移挂 /about，不丢失。"""
        return FileResponse(settings.static_dir / "workspace.html",
                            headers=NO_CACHE_HEADERS)

    @app.get("/workspace", include_in_schema=False)
    async def read_workspace_page() -> FileResponse:
        return FileResponse(settings.static_dir / "workspace.html",
                            headers=NO_CACHE_HEADERS)

    @app.get("/about", include_in_schema=False)
    async def read_about_page() -> FileResponse:
        return FileResponse(settings.static_dir / "index.html",
                            headers=NO_CACHE_HEADERS)

    @app.get("/api/settings", summary="获取系统设置与令牌")
    async def get_settings() -> dict[str, str]:
        """返回当前有效的写操作令牌（一次性，用后即焚）与当前工作区 id。

        ``workspace_id`` 给宿主壳的草稿箱分箱用：草稿按区分槽位，
        切库重启后 A 区没录完的题不会串进 B 区（插件拿不到令牌，也拿不到这个 id 的写权）。
        """
        return {"local_token": local_write_token(), "workspace_id": current_workspace_id()}

    @app.get("/plugins", include_in_schema=False)
    async def read_plugins_page() -> FileResponse:
        return FileResponse(settings.static_dir / "plugins.html",
                            headers=NO_CACHE_HEADERS)

    @app.get("/settings", include_in_schema=False)
    async def read_settings_page() -> FileResponse:
        """低频操作统一收口：在线索引、手动安装 zip、底座信息。

        工作台左栏只留入口与已装插件，齿轮入口直达这里（v0.5.4）。
        """
        return FileResponse(settings.static_dir / "settings.html",
                            headers=NO_CACHE_HEADERS)

    @app.get("/plugins/index-example", include_in_schema=False)
    async def read_example_index() -> FileResponse:
        """本机自带的示例索引，供「先试一次」按钮用同源地址走通流程。

        它不是内置插件市场：底座不会自动读它，也只有用户点了按钮才会访问。
        """
        return FileResponse(
            settings.project_root / "examples" / "plugins-index.example.toml",
            media_type="application/toml; charset=utf-8",
        )

    @app.get("/schemas/question.json", include_in_schema=False)
    async def read_question_schema() -> FileResponse:
        return FileResponse(
            settings.schemas_dir / "question.json",
            media_type="application/schema+json",
        )

    @app.get("/schemas/plugins-index.json", include_in_schema=False)
    async def read_plugins_index_schema() -> FileResponse:
        return FileResponse(
            settings.schemas_dir / "plugins-index.json",
            media_type="application/schema+json",
        )

    @app.get("/spec/plugin", include_in_schema=False)
    async def read_plugin_spec() -> FileResponse:
        return FileResponse(
            settings.docs_dir / "PLUGIN_SPEC.md",
            media_type="text/markdown; charset=utf-8",
        )

    return app


app = create_app()

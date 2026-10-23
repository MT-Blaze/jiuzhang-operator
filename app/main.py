"""九章算子底座入口。

底座只负责装配：健康检查、静态资源、只读契约入口。
业务能力一律由插件提供，见 PLUGIN_SPEC.md。
"""

from __future__ import annotations

import logging
import re
import threading
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import PurePosixPath

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.agents import router as agents_router
from app.api.bank import router as bank_router
from app.api.health import router as health_router
from app.api.plugins import router as plugins_router
from app.api.providers import router as providers_router
from app.api.questions import router as questions_router
from app.api.settings import router as settings_router
from app.api.workspaces import router as workspaces_router
from app.core import plugin_update
from app.core.config import settings
from app.core.db import init_db
from app.core.security import local_write_token

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


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
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
    app.include_router(agents_router)
    app.include_router(workspaces_router)
    app.include_router(bank_router)
    app.include_router(settings_router)

    @app.get("/static/uploads/{asset_path:path}", include_in_schema=False)
    async def read_upload(asset_path: str) -> FileResponse:
        """题目配图：只读当前工作区 uploads/，拒绝穿越、符号链接与非图片扩展名。

        不能直接 mount 一个固定目录：工作区切换后上传根会变，路由必须按请求
        当时的 ``settings.uploads_dir`` 解析（见 PLUGIN_SPEC §3.1）。
        """
        root = settings.uploads_dir.resolve()
        relative = PurePosixPath(asset_path.replace("\\", "/"))
        if (
            not relative.parts
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.parts[0].startswith(".")
        ):
            raise HTTPException(status_code=404, detail="资源路径非法")
        target = root.joinpath(*relative.parts)
        if target.is_symlink():
            raise HTTPException(status_code=404, detail="不允许符号链接")
        try:
            target.resolve().relative_to(root)
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

    @app.get("/static/vendor/katex/fonts/{font_name}", include_in_schema=False)
    async def read_katex_font(font_name: str) -> FileResponse:
        """KaTeX 字体：沙箱插件是不透明源，@font-face 属于 CORS 请求。

        StaticFiles 不会替字体补 ``Access-Control-Allow-Origin``，缺了它公式
        会退化成缺字方框；字体是公开静态资源，这里只放行白名单文件名。
        """
        if re.fullmatch(r"KaTeX_[A-Za-z0-9_-]+\.(?:woff2|woff|ttf)", font_name) is None:
            raise HTTPException(status_code=404, detail="字体不存在")
        path = settings.static_dir / "vendor" / "katex" / "fonts" / font_name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="字体不存在")
        return FileResponse(
            path,
            media_type="font/woff2" if font_name.endswith(".woff2") else "font/woff",
            headers={
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Resource-Policy": "cross-origin",
                "X-Content-Type-Options": "nosniff",
                "Cache-Control": "public, max-age=604800",
            },
        )

    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

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
                "Service-Worker-Allowed": "/",
                "Cache-Control": "no-cache",
            },
        )

    @app.get("/", include_in_schema=False)
    async def read_root() -> FileResponse:
        """根路径直达工作台（10.24 军令任务 1）：用户打开浏览器就该看到能干活的地方，
        底座介绍页移挂 /about，不丢失。"""
        return FileResponse(settings.static_dir / "workspace.html")

    @app.get("/workspace", include_in_schema=False)
    async def read_workspace_page() -> FileResponse:
        return FileResponse(settings.static_dir / "workspace.html")

    @app.get("/about", include_in_schema=False)
    async def read_about_page() -> FileResponse:
        return FileResponse(settings.static_dir / "index.html")

    @app.get("/api/settings", summary="获取系统设置与令牌")
    async def get_settings() -> dict[str, str]:
        """返回当前有效的写操作令牌（一次性，用后即焚）。"""
        return {"local_token": local_write_token()}

    @app.get("/plugins", include_in_schema=False)
    async def read_plugins_page() -> FileResponse:
        return FileResponse(settings.static_dir / "plugins.html")

    @app.get("/settings", include_in_schema=False)
    async def read_settings_page() -> FileResponse:
        """低频操作统一收口：在线索引、手动安装 zip、底座信息。

        工作台左栏只留入口与已装插件，齿轮入口直达这里（v0.5.4）。
        """
        return FileResponse(settings.static_dir / "settings.html")

    @app.get("/plugins/index-example", include_in_schema=False)
    async def read_example_index() -> FileResponse:
        """本机自带的示例索引，供「先试一次」按钮用同源地址走通流程。

        它不是内置插件市场：底座不会自动读它，也只有用户点了按钮才会访问。
        """
        return FileResponse(
            settings.project_root / "examples" / "plugins-index.example.json",
            media_type="application/json; charset=utf-8",
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
            settings.project_root / "PLUGIN_SPEC.md",
            media_type="text/markdown; charset=utf-8",
        )

    return app


app = create_app()

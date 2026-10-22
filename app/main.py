"""九章算子底座入口。

底座只负责装配：健康检查、静态资源、只读契约入口。
业务能力一律由插件提供，见 PLUGIN_SPEC.md。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.api.agents import router as agents_router
from app.api.health import router as health_router
from app.api.plugins import router as plugins_router
from app.api.providers import router as providers_router
from app.api.questions import router as questions_router
from app.api.workspaces import router as workspaces_router
from app.core.config import settings
from app.core.db import init_db
from app.core.security import local_write_token


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
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
    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def read_index() -> FileResponse:
        return FileResponse(settings.static_dir / "index.html")

    @app.get("/workspace", include_in_schema=False)
    async def read_workspace_page() -> FileResponse:
        return FileResponse(settings.static_dir / "workspace.html")

    @app.get("/api/settings", summary="获取系统设置与令牌")
    async def get_settings() -> dict[str, str]:
        """返回当前有效的写操作令牌（一次性，用后即焚）。"""
        return {"local_token": local_write_token()}

    @app.get("/plugins", include_in_schema=False)
    async def read_plugins_page() -> FileResponse:
        return FileResponse(settings.static_dir / "plugins.html")

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

"""TikZ 渲染路由：源码进、底座托管的 SVG 地址出。

只读能力：不写题库、不动原图；缓存落在当前工作区 ``uploads/tikz/``。
本机没有 LaTeX 引擎时返回 503，前端按既有优先级回退到 ``path`` 原图。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, HTTPException

from app.core import tikz_render

router = APIRouter(prefix="/api/tikz", tags=["tikz"])


@router.get("/status", summary="TikZ 渲染引擎可用性")
def tikz_status() -> dict[str, Any]:
    return tikz_render.status()


@router.post("/render", summary="把 TikZ 源码渲染为底座托管的 SVG")
def tikz_render_code(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    code = payload.get("code")
    if not isinstance(code, str) or not code.strip():
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "缺少 TikZ 源码（code 字段）"},
        )
    try:
        uri = tikz_render.render(code)
    except tikz_render.TikzUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "tikz_unavailable", "message": str(exc)},
        ) from exc
    except tikz_render.TikzError as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "tikz_rejected", "message": str(exc)},
        ) from exc
    return {"uri": uri, "engine": tikz_render.ENGINE_LABEL}

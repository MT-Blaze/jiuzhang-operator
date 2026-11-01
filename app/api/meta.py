"""全域数据字典 Host API：学校、主场景与交叉标签。

插件跑在沙箱里，摸不到 ``pending.db``（AGENTS §2）；这三张表的读写全部收在
底座：读开放、写带一次性令牌。学校简称冲突按主公裁定的原话回 409，
AI 补全只给建议，老师确认后才建档。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response

from app.core import meta_dict, pending_bank
from app.core.security import require_write_token

router = APIRouter(tags=["meta"])


def _error(exc: Exception) -> HTTPException:
    if isinstance(exc, meta_dict.SchoolShortNameConflict):
        return HTTPException(
            status_code=409,
            detail={
                "code": "short_name_conflict",
                "message": str(exc),
                "short_name": exc.short_name,
                "existing_full_name": exc.existing_full_name,
            },
        )
    if isinstance(exc, pending_bank.PendingError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/api/meta/scenes", summary="11 个主场景")
def meta_scenes() -> dict[str, Any]:
    try:
        return meta_dict.list_scenes()
    except pending_bank.PendingError as exc:
        raise _error(exc) from exc


@router.get("/api/meta/schools", summary="查学校字典（全称/简称模糊匹配）")
def meta_schools(q: str = "", limit: int = Query(default=30, ge=1, le=100)) -> dict[str, Any]:
    try:
        return meta_dict.list_schools(q, limit)
    except (meta_dict.MetaDictError, pending_bank.PendingError) as exc:
        raise _error(exc) from exc


@router.post(
    "/api/meta/schools",
    summary="新建学校（简称唯一；冲突时按裁定原话拦截）",
    dependencies=[Depends(require_write_token)],
)
def meta_schools_create(
    response: Response,
    payload: dict[str, Any] = Body(...),
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    try:
        result = meta_dict.create_school(payload.get("full_name"), payload.get("short_name"))
    except meta_dict.SchoolShortNameConflict as exc:
        raise _error(exc) from exc
    except (meta_dict.MetaDictError, pending_bank.PendingError) as exc:
        raise _error(exc) from exc
    response.status_code = 201 if result.get("created") else 200
    return result


@router.post(
    "/api/meta/schools/suggest",
    summary="AI 补全学校全称（只给建议，不落库）",
    dependencies=[Depends(require_write_token)],
)
async def meta_schools_suggest(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    if not str(payload.get("short_name") or "").strip():
        raise HTTPException(status_code=400, detail="先填一个简称或别名，才能让 AI 补全")
    try:
        return await meta_dict.suggest_school_full_name(
            payload.get("short_name"), payload.get("region")
        )
    except meta_dict.MetaDictError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise _error(exc) from exc


@router.get("/api/meta/tags", summary="交叉标签：按场景权重排序，支持模糊匹配")
def meta_tags(
    scene: str = "",
    q: str = "",
    limit: int = Query(default=20, ge=1, le=50),
) -> dict[str, Any]:
    try:
        return meta_dict.list_tags(scene, q, limit)
    except (meta_dict.MetaDictError, pending_bank.PendingError) as exc:
        raise _error(exc) from exc


@router.post(
    "/api/meta/tags",
    summary="记住一个交叉标签（老师手打回车即入本地标签库）",
    dependencies=[Depends(require_write_token)],
)
def meta_tags_remember(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    try:
        return meta_dict.remember_tag(payload.get("name"), payload.get("scene"))
    except (meta_dict.MetaDictError, pending_bank.PendingError) as exc:
        raise _error(exc) from exc

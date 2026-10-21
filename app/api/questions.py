"""题目 CRUD。

GET 保持只读开放；POST/PUT/DELETE 必须通过 X-JZO-Token。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response

from app.core import questions as store
from app.core.security import require_write_token

router = APIRouter(prefix="/api/questions", tags=["questions"])

ListBody = dict[str, Any]


@router.get("", summary="分页浏览题目")
async def list_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=store.MAX_PAGE_SIZE),
    q: str = Query("", max_length=200),
    question_type: str | None = Query(None, alias="type"),
    difficulty: str | None = Query(None),
    status: str | None = Query(None),
) -> dict[str, Any]:
    try:
        items, total = store.list_questions(
            page=page,
            page_size=page_size,
            search=q.strip(),
            question_type=question_type,
            difficulty=difficulty,
            status=status,
        )
    except store.QuestionValidationError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "errors": exc.errors}) from exc

    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get("/{question_id}", summary="读取单题")
async def read_question(question_id: str) -> dict[str, Any]:
    try:
        return store.get_question(question_id)
    except store.QuestionNotFound as exc:
        raise HTTPException(status_code=404, detail=f"题目 {question_id} 不存在。") from exc


@router.post(
    "",
    status_code=201,
    summary="新建题目",
    dependencies=[Depends(require_write_token)],
)
async def create_question(payload: ListBody = Body(...)) -> dict[str, Any]:
    try:
        return store.create_question(payload)
    except store.QuestionValidationError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "errors": exc.errors}) from exc
    except store.QuestionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put(
    "/{question_id}",
    summary="整题替换",
    dependencies=[Depends(require_write_token)],
)
async def replace_question(question_id: str, payload: ListBody = Body(...)) -> dict[str, Any]:
    try:
        return store.replace_question(question_id, payload)
    except store.QuestionNotFound as exc:
        raise HTTPException(status_code=404, detail=f"题目 {question_id} 不存在。") from exc
    except store.QuestionValidationError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc), "errors": exc.errors}) from exc
    except store.QuestionConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.delete(
    "/{question_id}",
    status_code=204,
    summary="删除题目",
    dependencies=[Depends(require_write_token)],
)
async def delete_question(question_id: str) -> Response:
    try:
        store.delete_question(question_id)
    except store.QuestionNotFound as exc:
        raise HTTPException(status_code=404, detail=f"题目 {question_id} 不存在。") from exc
    return Response(status_code=204)

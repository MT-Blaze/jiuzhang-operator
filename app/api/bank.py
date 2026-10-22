"""题库与题篮 Host API：给沙箱插件提供受控的数据通道。

插件不直接联网、不直接读库；舞台宿主（static/js/stage.js）把插件的
``bank.*`` / ``basket.*`` 请求转发到这些只读或带令牌的接口。

- 读取接口开放（与题目列表一致，本机只读不鉴权）；
- 题篮修改必须带一次性写令牌（AGENTS §5：修改类接口必须鉴权）；
- 所有过滤条件参数化，禁止把插件输入拼进 SQL。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.core import bank, basket, questions
from app.core.security import require_write_token

router = APIRouter(tags=["bank"])


@router.get("/api/bank/plugins/{plugin_id}/stats", summary="题库统计（年级/难度/题型/章节）")
def bank_stats(plugin_id: str) -> dict[str, Any]:
    try:
        data = bank.stats(plugin_id)
        data["meta"] = bank.metadata(plugin_id)
        return data
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/bank/plugins/{plugin_id}/questions", summary="按年级/难度/题型/关键词分页取题")
def bank_questions(
    plugin_id: str,
    grade: str = Query("", max_length=32),
    difficulty: str = Query("", max_length=32),
    type: str = Query("", max_length=32),
    chapter: str = Query("", max_length=64),
    textbook: str = Query("", max_length=64),
    q: str = Query("", max_length=100),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=bank.MAX_PAGE_SIZE),
) -> dict[str, Any]:
    try:
        items, total = bank.list_questions(
            plugin_id,
            grade=grade,
            difficulty=difficulty,
            question_type=type,
            chapter=chapter,
            textbook=textbook,
            search=q,
            page=page,
            page_size=page_size,
        )
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/api/bank/plugins/{plugin_id}/questions/{question_id}", summary="单题详情")
def bank_question(plugin_id: str, question_id: str) -> dict[str, Any]:
    try:
        return bank.get_question(plugin_id, question_id)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/bank/plugins/{plugin_id}/questions",
    status_code=201,
    summary="新增一道题（录题插件经宿主写入）",
    dependencies=[Depends(require_write_token)],
)
def bank_create_question(plugin_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """写入插件题库。请求体形如 ``{"question": {...标准结构...}}``。

    权限边界：插件声明 ``questions:write`` 才能经宿主转发到这里；ID 与时间戳
    由底座生成，请求里带来的 ``id`` / ``meta`` 会被底座覆盖。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    question = payload.get("question")
    if not isinstance(question, dict):
        raise HTTPException(status_code=400, detail="缺少 question 对象")
    try:
        return bank.create_question(plugin_id, question)
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "题目不符合 Schema", "errors": exc.errors},
        ) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/bank/plugins/{plugin_id}/random", summary="按筛选条件随机取一题")
def bank_random(
    plugin_id: str,
    grade: str = Query("", max_length=32),
    difficulty: str = Query("", max_length=32),
    type: str = Query("", max_length=32),
    q: str = Query("", max_length=100),
) -> dict[str, Any]:
    try:
        question = bank.random_question(
            plugin_id,
            grade=grade,
            difficulty=difficulty,
            question_type=type,
            search=q,
        )
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if question is None:
        raise HTTPException(status_code=404, detail="当前筛选条件下没有题目")
    return question


@router.get("/api/basket", summary="读题篮；expand=true 时附带题目全文")
def read_basket(expand: bool = Query(False)) -> dict[str, Any]:
    items = basket.list_items()
    if not expand:
        return {"items": items, "total": len(items)}
    grouped: dict[str, list[str]] = {}
    for item in items:
        grouped.setdefault(item["plugin_id"], []).append(item["question_id"])
    documents: dict[str, dict[str, Any]] = {}
    for plugin_id, ids in grouped.items():
        try:
            for document in bank.get_many(plugin_id, ids):
                documents[document["id"]] = document
        except bank.BankError:
            # 插件被卸载或题库缺失：题篮保留 ID，但本次不回全文，不把整篮判死
            continue
    enriched = []
    for item in items:
        document = documents.get(item["question_id"])
        if document:
            enriched.append({**item, "question": document})
    return {"items": enriched, "total": len(enriched), "missing": len(items) - len(enriched)}


@router.post(
    "/api/basket",
    summary="向题篮加题（批量）；默认追加，mode=replace 时整体替换",
    dependencies=[Depends(require_write_token)],
)
def write_basket(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    plugin_id = payload.get("plugin_id")
    ids = payload.get("ids")
    if isinstance(payload.get("id"), str):
        ids = [payload["id"]]
    if not isinstance(ids, list) or not ids:
        raise HTTPException(status_code=400, detail="ids 必须是非空数组")
    if len(ids) > basket.MAX_BASKET:
        raise HTTPException(status_code=400, detail=f"一次最多加 {basket.MAX_BASKET} 题")
    if not isinstance(plugin_id, str):
        raise HTTPException(status_code=400, detail="缺少 plugin_id")

    try:
        found = bank.get_many(plugin_id, ids)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if len(found) != len({item for item in ids if isinstance(item, str)}):
        raise HTTPException(status_code=400, detail="有题目不在该题库中，题篮未写入")

    mode = str(payload.get("mode") or "append")
    try:
        if mode == "replace":
            items = basket.replace(
                [{"question_id": item["id"], "plugin_id": plugin_id} for item in found]
            )
        else:
            items = basket.add(plugin_id, [item["id"] for item in found])
    except basket.BasketError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"items": items, "total": len(items)}


@router.delete(
    "/api/basket/{question_id}",
    summary="从题篮移除一题",
    dependencies=[Depends(require_write_token)],
)
def delete_basket_item(question_id: str) -> dict[str, Any]:
    try:
        items = basket.remove(question_id)
    except basket.BasketError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"items": items, "total": len(items)}


@router.delete(
    "/api/basket",
    summary="清空题篮",
    dependencies=[Depends(require_write_token)],
)
def clear_basket() -> dict[str, Any]:
    return {"items": basket.clear(), "total": 0}

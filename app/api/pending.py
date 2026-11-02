"""中转站（待审核池）Host API：给沙箱插件提供受控的批次暂存通道。

插件不直接碰数据库、不直接碰文件系统（AGENTS §2）；它把题目交给宿主，
宿主落进与主库物理隔离的中转站（``app/core/pending_bank.py``），老师审核
通过后才转成正式题目写进主库。

- 写接口（存草稿 / 通过入库 / 彻底删除）必须带一次性写令牌（AGENTS §5）；
- 读接口（批次列表 / 批次题目）开放，与题目列表同口径；
- **入库到哪个题库由底座定**：活跃题库 provider 由服务端解析，插件自报的一律
  不认——否则插件就能往任意一个已装题库里塞题。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core import bank, bank_provider as provider, pending_bank, questions
from app.core.security import require_write_token

router = APIRouter(tags=["pending"])


@router.get("/api/pending/batches", summary="拉取所有批次（卡片视图）")
def pending_batches() -> dict[str, Any]:
    """批次卡片：时间、编号、未审数 / 总题数。

    有未审的批次在前，已审完的沉在最后——老师一眼看见「还欠多少」。
    """
    try:
        return pending_bank.batch_list()
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/pending/batches/{batch_id}/questions",
    summary="按批次拉取待审题目",
)
def pending_batch_questions(batch_id: str) -> dict[str, Any]:
    """返回的每一条都带完整题目文档，审核界面拿到就能直接渲染。"""
    try:
        return pending_bank.list_batch_questions(batch_id)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/api/pending/meta/history",
    summary="公共元数据的历史值",
)
def pending_meta_history() -> dict[str, Any]:
    """最近用过的地区 / 主体 / 考试类型 / 学科 / 明细学校，开新批次时自动带出。"""
    try:
        return pending_bank.meta_history()
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/api/pending/batches/{batch_id}/meta",
    summary="改批次公共元数据，并立刻同步这一批所有题",
    dependencies=[Depends(require_write_token)],
)
def pending_set_meta(batch_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体形如 ``{"year": 2024, "region": "黑吉辽", "body": "三省六校",
    "exam_type": "高三联考", "subject": "数学", "schools": ["哈三中"]}``。

    标准名不收：它是底座按 ``年份-地区-主体-类型-学科`` 拼出来的，客户端说了不算。

    改完立刻同步两处：池子里的待审题（``source`` 与隐藏标签），
    以及这一批已经进主库的题（补写主库 ``sources``）。同步不上的题一条也不动，
    并在 ``warnings`` 里如实报出原因。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    try:
        return pending_bank.set_batch_meta(batch_id, payload)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/pending/batches",
    status_code=201,
    summary="存为待审：单题或批量题进中转站",
    dependencies=[Depends(require_write_token)],
)
def pending_save_draft(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体形如 ``{"questions": [{"question": {...}, "assets": [...]}], "source_backup": "..."}``。

    ``id`` 与 ``meta`` 由底座签发，插件带来的作废；暂存题的 id 走 ``p_`` 号段，
    与主库的 ``q_`` 号段永不相交。``assets`` 可省略：给了就把配图字节落进
    ``pending_assets/``，题目在池子里期间配图不碰 ``uploads/``。
    ``batch_id`` 给了就并进那一批；不给就新开一批（``B-001`` 起）。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    items = payload.get("questions")
    if items is None and isinstance(payload.get("question"), dict):
        items = [{
            "question": payload.get("question"),
            "assets": payload.get("assets"),
        }]
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="缺少 questions 数组")
    try:
        return pending_bank.save_draft(
            items,
            batch_id=payload.get("batch_id"),
            source_backup=payload.get("source_backup"),
            source_name=payload.get("source_name"),
            origin=str(payload.get("origin") or ""),
        )
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": "题目不符合 Schema", "errors": exc.errors}
        ) from exc
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/pending/items/{pending_id}/approve",
    summary="存入主库：中转站的题转成正式题入库",
    dependencies=[Depends(require_write_token)],
)
def pending_approve(pending_id: str, payload: dict[str, Any] | None = Body(default=None)) -> dict[str, Any]:
    """``p_`` 号段换成底座新签发的 ``q_``，配图搬进 ``uploads/``，池子里删干净。

    入哪个题库由服务端按**活跃题库 provider** 决定，插件无权指定。

    主库已有同题时回 **409**，并在 ``detail`` 里带上主库那道题的 id：老师可以在
    界面上选「强行覆盖」再带 ``{"force": true}`` 提交一次。底座只负责如实报出
    「哪一道、差在哪儿」，绝不自己替老师做主。
    """
    body = payload if isinstance(payload, dict) else {}
    force = body.get("force") is True
    try:
        plugin_id = provider.resolve()["plugin_id"]
        return pending_bank.approve(pending_id, plugin_id, force=force)
    except pending_bank.PendingDuplicate as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "existing_id": exc.existing_id, "duplicate": True},
        ) from exc
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422, detail={"message": "题目不符合 Schema", "errors": exc.errors}
        ) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/pending/items/{pending_id}/delete",
    summary="彻底删除：从中转站删掉这一条",
    dependencies=[Depends(require_write_token)],
)
def pending_delete(pending_id: str) -> dict[str, Any]:
    """连同它在 ``pending_assets/`` 里的配图一起删；主库一个字节都不碰。"""
    try:
        return pending_bank.delete_pending(pending_id)
    except pending_bank.PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except pending_bank.PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

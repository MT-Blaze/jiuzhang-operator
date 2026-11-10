"""题库引擎 v2 的 Host API：录题下拉框的真实字典、考向 / 知识点检索与录题落库。

插件在沙箱里碰不到 ``.v2.db``；这里把 35 张表的能力收成四条口子：

- 读字典（学科 / 年级 / 题型 / 难度 / 质量）与考试类型清单；
- 按关键字查考向、知识点，返回给幽灵胶囊直接上屏；
- 录题：校验表单 → 签发 ``q_`` → 主表与从表分步写入，写失败整题回滚。

所有读接口开放（本机只读口径与旧题库一致），写接口必须带一次性令牌。
返回体一律由 Dataclass 转普通对象，不在底座内部拼 JSON 文本。
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.bank_engine import service
from app.bank_engine.writer import EntryRejected
from app.core.security import require_write_token

router = APIRouter(tags=["bank-engine"])


@router.get("/api/bank/engine/status", summary="引擎库状态：表数、完整性、种子计数")
def engine_status() -> dict[str, Any]:
    return asdict(service.status())


@router.get("/api/bank/engine/meta", summary="录题下拉框的五张小字典与考试类型清单")
def engine_meta() -> dict[str, Any]:
    dictionaries = service.dictionaries()
    return {
        "subjects": [asdict(item) for item in dictionaries.subjects],
        "grades": [asdict(item) for item in dictionaries.grades],
        "question_types": [asdict(item) for item in dictionaries.question_types],
        "difficulties": [asdict(item) for item in dictionaries.difficulties],
        "qualities": [asdict(item) for item in dictionaries.qualities],
        "exam_types": [asdict(item) for item in dictionaries.exam_types],
    }


@router.get("/api/bank/engine/textbooks", summary="教材版本清单：按学科/年级过滤，供字典控制台全局设置")
def engine_textbooks(
    subject_id: int | None = Query(default=None, ge=1),
    grade_id: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    items = service.textbooks(subject_id=subject_id, grade_id=grade_id)
    return {"items": [asdict(item) for item in items], "total": len(items)}


@router.get("/api/bank/engine/exam-directions", summary="考向检索：关键字模糊查，按大纲顺序")
def engine_exam_directions(
    q: str = Query(default="", max_length=100),
    subject_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items, total = service.exam_directions(
        subject_id=subject_id,
        keyword=q.strip() or None,
        limit=limit,
        offset=offset,
    )
    # 胶囊串以 code 作身份：``tp_`` 前脸与旧大纲一致，落库时再由引擎换回整数外键。
    return {
        "items": [
            {
                "id": item.code,
                "direction_id": item.id,
                "name": item.name,
                "code": item.code,
                "chapter_id": item.chapter_id,
            }
            for item in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/bank/engine/knowledge-points", summary="知识点检索：关键字模糊查，按大纲顺序")
def engine_knowledge_points(
    q: str = Query(default="", max_length=100),
    subject_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items, total = service.knowledge_points(
        subject_id=subject_id,
        keyword=q.strip() or None,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": item.code,
                "point_id": item.id,
                "name": item.name,
                "code": item.code,
                "parent_id": item.parent_id,
            }
            for item in items
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.post(
    "/api/bank/engine/questions",
    summary="录入一道题：签发 q_ 号，主表与从表分步落库",
    dependencies=[Depends(require_write_token)],
)
def engine_create_question(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """只认表单内容；``id`` 之类的自带身份一律忽略，题目号由引擎签发。"""
    try:
        created = service.create_question(payload)
    except EntryRejected as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "entry_rejected", "message": str(exc), "errors": exc.errors},
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": created.id, "created": created.created}

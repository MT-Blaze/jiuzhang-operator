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
from typing import Any, Callable

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.bank_engine import dao_console, service
from app.bank_engine.writer import EntryRejected
from app.core.security import require_write_token

router = APIRouter(tags=["bank-engine"])


def _guard(call: Callable[[], Any]) -> Any:
    """把字典控制台的领域异常统一换成 HTTP：404 找不到 / 409 被引用或冲突 / 400 校验。"""
    try:
        return call()
    except dao_console.ConsoleLookupError as exc:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": str(exc)}
        ) from exc
    except dao_console.ReferencedError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "referenced",
                "message": "已被引用，禁止删除",
                "references": [asdict(hit) for hit in exc.hits],
            },
        ) from exc
    except dao_console.ConflictError as exc:
        raise HTTPException(
            status_code=409, detail={"code": "conflict", "message": str(exc)}
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail={"code": "bad_request", "message": str(exc)}
        ) from exc


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


# ---- 字典控制台（阶段二）：基础五表读写与删除防呆 ----
# 读接口开放；写接口（新增 / 改名 / 删除 / 导入）必须带一次性令牌。
# 全局设置三参数（stage / subject_id / textbook_id）随读接口带入，
# 每张表只应用与自己相关的绑定（见 dao_console.SPECS.global_filters）。


@router.post(
    "/api/bank/engine/dict/import",
    summary="TOML 批量导入基础五表：顶层键为表名，值为行表数组",
    dependencies=[Depends(require_write_token)],
)
def engine_dict_import(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    text = payload.get("content")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "缺少 TOML 文本（content 字段）"},
        )
    report = _guard(lambda: service.console_import(text))
    return asdict(report)


@router.get("/api/bank/engine/dict/{table}", summary="字典分页检索：关键字 + 全局设置过滤")
def engine_dict_list(
    table: str,
    q: str = Query(default="", max_length=100),
    stage: str | None = Query(default=None, max_length=20),
    subject_id: int | None = Query(default=None, ge=1),
    textbook_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    filters = {"stage": stage, "subject_id": subject_id, "textbook_id": textbook_id}
    items, total = _guard(lambda: service.console_list(
        table, keyword=q.strip() or None, filters=filters, limit=limit, offset=offset
    ))
    spec = dao_console.get_spec(table)
    return {
        "table": table,
        "label": spec.label,
        "fields": list(dao_console.fields_meta(spec)),
        "items": [asdict(item) for item in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get(
    "/api/bank/engine/dict/{table}/{row_id}/references",
    summary="查某行被哪些子表引用（删除防呆预览）",
)
def engine_dict_references(table: str, row_id: int) -> dict[str, Any]:
    hits = _guard(lambda: service.console_references(table, row_id))
    return {"references": [asdict(hit) for hit in hits]}


@router.get("/api/bank/engine/dict/{table}/{row_id}", summary="读单行字典")
def engine_dict_row(table: str, row_id: int) -> dict[str, Any]:
    return asdict(_guard(lambda: service.console_row(table, row_id)))


@router.post(
    "/api/bank/engine/dict/{table}",
    summary="新增一行字典",
    dependencies=[Depends(require_write_token)],
)
def engine_dict_insert(table: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    return asdict(_guard(lambda: service.console_insert(table, payload)))


@router.put(
    "/api/bank/engine/dict/{table}/{row_id}",
    summary="改名字典行：双击单元格 blur 保存",
    dependencies=[Depends(require_write_token)],
)
def engine_dict_update(
    table: str, row_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    return asdict(_guard(lambda: service.console_update(table, row_id, payload)))


@router.delete(
    "/api/bank/engine/dict/{table}/{row_id}",
    summary="删除字典行：先查外键引用，被引用即 409 拦截",
    dependencies=[Depends(require_write_token)],
)
def engine_dict_delete(table: str, row_id: int) -> dict[str, Any]:
    _guard(lambda: service.console_delete(table, row_id))
    return {"deleted": True, "id": row_id}

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
from app.core import tikz_render
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
                "message": "已被引用，无法删除",
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


@router.get("/api/bank/engine/textbook-versions", summary="教材版本清单：只出纯净版本名，供全局设置下拉")
def engine_textbook_versions(
    subject_id: int | None = Query(default=None, ge=1),
    stage: str | None = Query(default=None, max_length=20),
) -> dict[str, Any]:
    items = service.textbook_versions(subject_id=subject_id, stage=stage)
    return {"items": [asdict(item) for item in items], "total": len(items)}


@router.get("/api/bank/engine/textbooks", summary="教材册清单：按学科/年级/版本过滤")
def engine_textbooks(
    subject_id: int | None = Query(default=None, ge=1),
    grade_id: int | None = Query(default=None, ge=1),
    version_id: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    items = service.textbooks(
        subject_id=subject_id, grade_id=grade_id, version_id=version_id
    )
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


@router.get("/api/bank/engine/questions/{question_id}", summary="读单题：图片按 tikz_code 优先生成矢量图")
def engine_question(question_id: str) -> dict[str, Any]:
    record = service.question(question_id)
    if record is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    payload = asdict(record)
    payload["images"] = [
        tikz_render.resolve_image(dict(image)) for image in payload.get("images", [])
    ]
    return payload


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


# ---- 四栏联动（阶段三）：章节树 → 章节知识点 → 考向 → 辅助标签 ----
# 读接口开放；写接口（新增 / 删除 / 排序 / 挂标签）必须带一次性令牌。
# 整块下架：删本段路由 + dao_linkage / migrate_v7 + 前端 linkage 模块即可。


def _id_list(payload: dict[str, Any], key: str) -> list[int]:
    values = payload.get(key)
    if not isinstance(values, list):
        raise ValueError("缺少整数 id 数组：" + key)
    return values


@router.get("/api/bank/engine/linkage/chapter-tree", summary="教材章节树：全局设置选定教材后整树读出")
def engine_linkage_chapter_tree(textbook_id: int = Query(ge=1)) -> dict[str, Any]:
    nodes = _guard(lambda: service.linkage_chapter_tree(textbook_id))
    return {"items": [asdict(node) for node in nodes], "total": len(nodes)}


@router.get("/api/bank/engine/linkage/version-tree", summary="版本章节树：版本 → 册次 → 章 → 节")
def engine_linkage_version_tree(version_id: int = Query(ge=1)) -> dict[str, Any]:
    books = _guard(lambda: service.linkage_version_tree(version_id))
    return {"items": [asdict(book) for book in books], "total": len(books)}


@router.get("/api/bank/engine/linkage/chapters/{chapter_id}/points", summary="章节知识点清单：按桥表 sort_order")
def engine_linkage_chapter_points(chapter_id: int) -> dict[str, Any]:
    items = _guard(lambda: service.linkage_chapter_points(chapter_id))
    return {"items": [asdict(item) for item in items], "total": len(items)}


@router.get("/api/bank/engine/linkage/points/{point_id}/directions", summary="知识点考向清单")
def engine_linkage_point_directions(point_id: int) -> dict[str, Any]:
    items = _guard(lambda: service.linkage_point_directions(point_id))
    return {"items": [asdict(item) for item in items], "total": len(items)}


@router.get("/api/bank/engine/linkage/directions/{direction_id}/tags", summary="考向辅助知识点标签：只出辅助标签并排除当前主知识点")
def engine_linkage_direction_tags(
    direction_id: int,
    exclude_point_id: int | None = Query(default=None, ge=1),
) -> dict[str, Any]:
    items = _guard(lambda: service.linkage_direction_tags(
        direction_id, exclude_point_id=exclude_point_id
    ))
    return {"items": [asdict(item) for item in items], "total": len(items)}


@router.put(
    "/api/bank/engine/linkage/chapters/{chapter_id}/points/order",
    summary="章节内知识点拖拽排序：提交完整清单，sort_order 落库",
    dependencies=[Depends(require_write_token)],
)
def engine_linkage_chapter_points_order(
    chapter_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    ids = _guard(lambda: _id_list(payload, "point_ids"))
    _guard(lambda: service.linkage_reorder("chapter_points", chapter_id, ids))
    return {"saved": True, "count": len(ids)}


@router.put(
    "/api/bank/engine/linkage/directions/{direction_id}/tags/order",
    summary="考向内辅助标签拖拽排序：提交完整清单，sort_order 落库",
    dependencies=[Depends(require_write_token)],
)
def engine_linkage_direction_tags_order(
    direction_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    ids = _guard(lambda: _id_list(payload, "point_ids"))
    exclude = payload.get("exclude_point_id")
    if exclude is not None and (not isinstance(exclude, int) or isinstance(exclude, bool)):
        raise HTTPException(
            status_code=400,
            detail={"code": "bad_request", "message": "exclude_point_id 必须是整数"},
        )
    _guard(lambda: service.linkage_reorder(
        "direction_tags", direction_id, ids, exclude_point_id=exclude
    ))
    return {"saved": True, "count": len(ids)}


@router.post(
    "/api/bank/engine/linkage/points/{point_id}/directions",
    summary="新增考向并挂到当前知识点：学科继承知识点",
    dependencies=[Depends(require_write_token)],
)
def engine_linkage_add_direction(
    point_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    name = payload.get("name")
    if not isinstance(name, str):
        raise HTTPException(
            status_code=400, detail={"code": "bad_request", "message": "缺少考向名称（name 字段）"}
        )
    return asdict(_guard(lambda: service.linkage_add_direction(point_id, name)))


@router.delete(
    "/api/bank/engine/linkage/points/{point_id}/directions/{direction_id}",
    summary="删除考向：排除当前关联后仍被引用即 409 防呆",
    dependencies=[Depends(require_write_token)],
)
def engine_linkage_delete_direction(point_id: int, direction_id: int) -> dict[str, Any]:
    _guard(lambda: service.linkage_delete_direction(point_id, direction_id))
    return {"deleted": True, "id": direction_id}


@router.post(
    "/api/bank/engine/linkage/directions/{direction_id}/tags",
    summary="全局搜索知识点挂为考向辅助标签：排到末尾",
    dependencies=[Depends(require_write_token)],
)
def engine_linkage_add_tag(
    direction_id: int, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    point_id = payload.get("point_id")
    if not isinstance(point_id, int) or isinstance(point_id, bool):
        raise HTTPException(
            status_code=400, detail={"code": "bad_request", "message": "缺少整数 point_id"}
        )
    return asdict(_guard(lambda: service.linkage_add_tag(direction_id, point_id)))


@router.delete(
    "/api/bank/engine/linkage/directions/{direction_id}/tags/{point_id}",
    summary="移除辅助标签：只解除关联，不删知识点本体",
    dependencies=[Depends(require_write_token)],
)
def engine_linkage_remove_tag(direction_id: int, point_id: int) -> dict[str, Any]:
    _guard(lambda: service.linkage_remove_tag(direction_id, point_id))
    return {"deleted": True, "id": point_id}

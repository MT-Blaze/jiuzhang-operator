"""题库与题篮 Host API：给沙箱插件提供受控的数据通道。

插件不直接联网、不直接读库；舞台宿主（static/js/stage.js）把插件的
``bank.*`` / ``basket.*`` 请求转发到这些只读或带令牌的接口。

- 读取接口开放（与题目列表一致，本机只读不鉴权）；
- 题篮修改必须带一次性写令牌（AGENTS §5：修改类接口必须鉴权）；
- 所有过滤条件参数化，禁止把插件输入拼进 SQL。
"""

from __future__ import annotations

import base64
import binascii
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response

from app.core import bank, basket, questions
from app.core import bank_dedupe as dedupe
from app.core import bank_provider as provider
from app.core import bank_transfer as transfer
from app.core.security import require_write_token
from app.api import workspaces as workspace_api

router = APIRouter(tags=["bank"])


@router.get("/api/bank/textbooks", summary="当前题库的教材版本清单（多版本大纲地基）")
def bank_textbooks() -> dict[str, Any]:
    """列活跃题库 provider 里登记的教材版本，并给出当前工作区实际生效的那一版。"""
    plugin_id = provider.resolve()["plugin_id"]
    try:
        items = bank.textbooks(plugin_id)
        active = workspace_api.active_textbook_id(plugin_id)
        return {"plugin_id": plugin_id, "items": items, "active_textbook_id": active}
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/bank/provider", summary="当前活跃的题库 provider（宿主与控制台都读它）")
def bank_provider_current() -> dict[str, Any]:
    """返回底座实际使用的题库插件；配置失效时回退默认并带 ``fallback_reason``。"""
    return provider.resolve()


@router.get("/api/bank/provider/candidates", summary="可被选为题库的已装插件")
def bank_provider_candidates() -> dict[str, Any]:
    return {"active": provider.resolve()["plugin_id"], "candidates": provider.candidates()}


@router.post("/api/bank/provider", summary="切换活跃题库 provider",
             dependencies=[Depends(require_write_token)])
def bank_provider_set(body: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """用户亲手选的题库：必须已安装且声明 ``bank.provider``，否则 400（PLUGIN_SPEC §2.6.1）。"""
    try:
        return provider.set_provider(str(body.get("plugin_id") or ""))
    except provider.ProviderRejected as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/bank/dashboard/stats", summary="数据看板：四个数与最近录入（活跃题库，只读）")
def bank_dashboard_stats() -> dict[str, Any]:
    """总题数 / 今日入库 / 待审核 / 已落库 + 最近 5 题摘要；口径见 API_REFERENCE.md。"""
    plugin_id = provider.resolve()["plugin_id"]
    try:
        data = bank.dashboard_stats(plugin_id)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"plugin_id": plugin_id, **data}


@router.get("/api/bank/dashboard/heatmap", summary="数据看板：过去 365 天按日入库热力图（活跃题库，只读）")
def bank_dashboard_heatmap(days: int = Query(365, ge=1, le=3650)) -> list[dict[str, Any]]:
    """返回裸数组 ``[{"date": "YYYY-MM-DD", "count": N}, ...]``，含今天、逐日补零。"""
    plugin_id = provider.resolve()["plugin_id"]
    try:
        return bank.daily_counts(plugin_id, days)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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


@router.get("/api/bank/plugins/{plugin_id}/questions", summary="按年级/难度/题型/考向/关键词分页取题")
def bank_questions(
    plugin_id: str,
    grade: str = Query("", max_length=32),
    difficulty: str = Query("", max_length=32),
    type: str = Query("", max_length=32),
    chapter: str = Query("", max_length=64),
    textbook: str = Query("", max_length=64),
    topic: str = Query("", max_length=20),
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
            topic=topic,
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


@router.get("/api/bank/plugins/{plugin_id}/topics", summary="大纲树懒展开：不给 parent 取所选版本的册层")
def bank_topics(
    plugin_id: str,
    parent_id: str = Query("", max_length=20),
    q: str = Query("", max_length=100),
    textbook_id: str = Query("", max_length=32),
) -> dict[str, Any]:
    """返回一层节点，带子树题量与教研笔记条数，供左侧大纲树按 sort_order 懒展开。

    未显式给 ``textbook_id`` 时取当前工作区的教材版本偏好；偏好缺失或失效则用题库默认版本。
    根层与搜索结果只展示该版本的目录节点，考向并集（textbook_id 为 NULL）照常出现。
    """
    scope = textbook_id.strip()
    if not scope:
        try:
            scope = workspace_api.active_textbook_id(plugin_id)
        except (bank.BankNotFound, bank.BankError):
            scope = ""
    try:
        items = bank.topics(plugin_id, parent_id=parent_id, search=q, textbook_id=scope)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"items": items, "total": len(items), "parent_id": parent_id, "textbook_id": scope}


@router.get(
    "/api/bank/plugins/{plugin_id}/topics/{topic_id}/notes",
    summary="考向节点的教研笔记（方法/易错点）",
)
def bank_topic_notes(plugin_id: str, topic_id: str) -> dict[str, Any]:
    try:
        return bank.topic_notes(plugin_id, topic_id)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/bank/plugins/{plugin_id}/review", summary="待审队列：按灌库标记筛题并给分组计数")
def bank_review(
    plugin_id: str,
    flag: str = Query("", max_length=32),
    page: int = Query(1, ge=1, le=10000),
    page_size: int = Query(20, ge=1, le=bank.MAX_PAGE_SIZE),
) -> dict[str, Any]:
    try:
        items, total = bank.list_questions(
            plugin_id, flag=flag or "any", page=page, page_size=page_size
        )
        summary = bank.review_summary(plugin_id)
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
        "summary": summary,
    }


@router.patch(
    "/api/bank/plugins/{plugin_id}/questions/{question_id}",
    summary="按题回写可审字段并清除审核标记（人工审核页专用）",
    dependencies=[Depends(require_write_token)],
)
def bank_update_question(
    plugin_id: str, question_id: str, payload: dict[str, Any] = Body(...)
) -> dict[str, Any]:
    """请求体形如 ``{"question": {...可审字段..., "clear_flags": ["answer_absent"]}}``。

    只接受题目内容与 ``clear_flags``；大纲挂载、来源关系与题目身份都不在此通道里改，
    避免人工审核页变成能悄悄挪动题目归属的旁路（那属于录题插件的改题范围）。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    patch = payload.get("question")
    if not isinstance(patch, dict):
        raise HTTPException(status_code=400, detail="缺少 question 对象")
    try:
        return bank.update_question(plugin_id, question_id, patch)
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "修改后的题目不符合 Schema", "errors": exc.errors},
        ) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/bank/plugins/{plugin_id}/questions/{question_id}", summary="单题详情")
def bank_question(plugin_id: str, question_id: str) -> dict[str, Any]:
    try:
        return bank.get_question(plugin_id, question_id)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/api/bank/plugins/{plugin_id}/questions/{question_id}",
    summary="按题号删除一道题（录题插件删题经宿主写入）",
    dependencies=[Depends(require_write_token)],
)
def bank_delete_question(plugin_id: str, question_id: str) -> dict[str, Any]:
    """删题只删题目本身：关联表靠外键级联摘净，共享的来源/学校/大纲节点保留。

    删成功后把该题从题篮一并摘掉——否则组卷页会留一条指向已删题目的死引用。
    题篮摘除失败不影响删除结果（题篮是易失的展示态集合，不是事实来源）。
    """
    try:
        result = bank.delete_question(plugin_id, question_id)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        basket.remove(question_id)
    except basket.BasketError:
        pass
    return result


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


@router.get("/api/bank/export", summary="导出当前工作区题库为标准 .json（可再导入回来）")
def bank_export() -> Response:
    """把当前工作区题库打包成交换包，直接落盘成 ``.json``。

    出参是 ``schemas/question.json`` 的标准结构，与题库浏览器、组卷插件看到的是
    同一份口径；导出的文件原样再导入回来即幂等还原。
    """
    plugin_id = provider.resolve()["plugin_id"]
    try:
        documents = bank.export_documents(plugin_id)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bundle = transfer.build_bundle(plugin_id, documents, questions.now_iso())
    filename = f"jiuzhang-bank-{plugin_id}-{questions.now_iso()[:10].replace('-', '')}.json"
    return JSONResponse(
        content=bundle,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/api/bank/import",
    summary="批量导入 .json / .zip 题目包（宿主校验后批量写入）",
    dependencies=[Depends(require_write_token)],
)
def bank_import(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """把老师选中的题目包导进当前工作区题库。

    请求体形如 ``{"filename": "pack.json", "content_base64": "..."}``：包可以是单个
    题目对象、题目数组，或带 ``questions`` 的交换包；``.zip`` 里每个 ``.json`` 成员
    都按同一口径解析。校验在宿主做（``schemas/question.json``），任一题不合格即整批
    回滚并逐题报错，不写半截数据。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    filename = str(payload.get("filename") or "").strip()[:160]
    content = payload.get("content_base64")
    if not isinstance(content, str) or not content.strip():
        raise HTTPException(status_code=400, detail="缺少 content_base64")
    mode = str(payload.get("mode") or "upsert")
    if mode not in ("upsert", "skip"):
        raise HTTPException(status_code=400, detail="mode 只能是 upsert 或 skip")
    try:
        raw = base64.b64decode(content, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status_code=400, detail="题目包不是合法的 base64") from exc
    try:
        documents = transfer.parse_bundle(raw, filename)
    except transfer.TransferError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    plugin_id = provider.resolve()["plugin_id"]
    try:
        report = bank.import_questions(plugin_id, documents, mode=mode)
    except bank.BankImportError as exc:
        summary = "；".join(
            f"第 {item['index']} 题" + (f"（{item['id']}）" if item.get("id") else "")
            + "：" + "；".join(item["errors"][:2])
            for item in exc.errors[:4]
        )
        raise HTTPException(
            status_code=422,
            detail={"message": f"{len(exc.errors)} 道题不符合 Schema，导入已整体回滚：{summary}",
                    "errors": exc.errors},
        ) from exc
    except questions.QuestionValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "题目不符合 Schema", "errors": exc.errors},
        ) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"plugin_id": plugin_id, **report}


@router.get("/api/bank/plugins/{plugin_id}/duplicates",
            summary="查重扫描（只读）：全库题面指纹分组，返回 ≥2 题的重复组与全文")
def bank_duplicates(plugin_id: str) -> dict[str, Any]:
    """题面归一 → SHA-256 指纹 → 分组，口径见 ``app/core/bank_dedupe.py`` 模块头。

    扫描不动任何数据，也不鉴权（与题目列表同口径）。``differing_fields`` 只报
    「答案/解析/难度/年级/考向/来源/备注里哪几项不一样」，老师据此决定保留哪一条。
    """
    try:
        return dedupe.duplicate_groups(plugin_id)
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/api/bank/plugins/{plugin_id}/duplicates/merge",
    summary="查重收敛合并：把副本的大纲/来源/备注并进保留项，追加解法二，删副本",
    dependencies=[Depends(require_write_token)],
)
def bank_duplicates_merge(plugin_id: str, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    """请求体形如 ``{"primary_id": "q_keep", "copy_ids": ["q_dup1", "q_dup2"]}``。

    单事务、先核对后提交：行数、残留引用、外键、完整性任一项对不上就整体回滚，
    库里一条不动（409）。合并成功后把被删的副本从题篮一并摘掉，与删题同一口径。
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    copy_ids = payload.get("copy_ids")
    if not isinstance(copy_ids, list) or not copy_ids:
        raise HTTPException(status_code=400, detail="copy_ids 必须是非空数组")
    if "primary_id" not in payload:
        raise HTTPException(status_code=400, detail="缺少 primary_id（保留项）")
    try:
        result = dedupe.merge_questions(plugin_id, payload.get("primary_id"), copy_ids)
    except questions.QuestionValidationError as exc:
        raise HTTPException(status_code=422, detail={"errors": exc.errors}) from exc
    except bank.BankNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except bank.BankConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except bank.BankError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    for question_id in result["merged"]:
        try:
            basket.remove(question_id)
        except basket.BasketError:
            # 题篮是易失的展示态集合，摘不掉不影响合并结果
            pass
    return result


@router.get("/api/bank/plugins/{plugin_id}/random", summary="按筛选条件随机取一题")
def bank_random(
    plugin_id: str,
    grade: str = Query("", max_length=32),
    difficulty: str = Query("", max_length=32),
    type: str = Query("", max_length=32),
    chapter: str = Query("", max_length=64),
    textbook: str = Query("", max_length=64),
    topic: str = Query("", max_length=20),
    q: str = Query("", max_length=100),
) -> dict[str, Any]:
    try:
        question = bank.random_question(
            plugin_id,
            grade=grade,
            difficulty=difficulty,
            question_type=type,
            chapter=chapter,
            textbook=textbook,
            topic=topic,
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

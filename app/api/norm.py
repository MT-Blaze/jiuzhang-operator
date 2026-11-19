"""记号标准字典 Host API（2.21.0 卡 §4）：闭集选择＋开集人闸。

整机库 ``data/latex_norm.db`` 住底座，插件在沙箱里摸不到（AGENTS §2）：读开放、
写带一次性令牌。闭集内容出厂冻结，老师只写 ``chosen_default_variant_id``（choose/reset）；
开集四态只有 pending 可裁决（decide），confirmed 才参与清洗改写。字典不进任何模型提示词。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.core.content import latex_norm
from app.core.security import require_write_token

router = APIRouter(tags=["norm"])


def _error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail={"code": "norm_error", "message": str(exc)})


def _body(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    return payload


@router.get("/api/norm/entries", summary="闭集条目＋变体行（effective_default 老师选择优先）")
def norm_entries() -> dict[str, Any]:
    try:
        return {
            "entries": latex_norm.list_entries(),
            "families": list(latex_norm.FAMILIES),
            "source_labels": sorted(latex_norm.SOURCE_LABELS),
        }
    except latex_norm.NormError as exc:
        raise _error(exc) from exc


@router.get("/api/norm/corrections", summary="开集候选（按状态过滤；pending 命中排序）＋四态计数")
def norm_corrections(status: str = Query(default="")) -> dict[str, Any]:
    try:
        return {
            "corrections": latex_norm.list_corrections(status or None),
            "counts": latex_norm.correction_counts(),
        }
    except latex_norm.NormError as exc:
        raise _error(exc) from exc


@router.post(
    "/api/norm/choose",
    summary="选默认字形（老师只写选择，出厂内容永不动）",
    dependencies=[Depends(require_write_token)],
)
def norm_choose(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    data = _body(payload)
    entry_key = str(data.get("entry_key") or "").strip()
    try:
        variant_id = int(data.get("variant_id"))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="variant_id 必须是整数") from exc
    try:
        return latex_norm.choose_default(entry_key, variant_id)
    except latex_norm.NormError as exc:
        raise _error(exc) from exc


@router.post(
    "/api/norm/reset",
    summary="恢复出厂＝选择回退（置 NULL），出厂默认本身永不动",
    dependencies=[Depends(require_write_token)],
)
def norm_reset(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    data = _body(payload)
    try:
        return latex_norm.reset_default(str(data.get("entry_key") or "").strip())
    except latex_norm.NormError as exc:
        raise _error(exc) from exc


@router.post(
    "/api/norm/decide",
    summary="开集人闸裁决：pending → confirmed（须给目标代码）／rejected（黑名单）",
    dependencies=[Depends(require_write_token)],
)
def norm_decide(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    data = _body(payload)
    try:
        return latex_norm.decide_correction(
            str(data.get("raw_code") or "").strip(),
            str(data.get("decision") or "").strip(),
            str(data.get("target_code") or ""),
        )
    except latex_norm.NormError as exc:
        raise _error(exc) from exc
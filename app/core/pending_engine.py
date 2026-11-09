"""中转站 → 题库引擎 v2 的入库分支：只做新题落库，旧主库的查重/覆盖不参与。

引擎库与旧 17 表库是两个物理文件；这里守住与新题入库相同的顺序：
先把配图搬进 ``uploads/``，再写引擎库，写库失败就把配图搬回去，
池子里那一条原样留着。
"""

from __future__ import annotations

import copy
from typing import Any

from app.core.pending_assets import move_assets_to_uploads, restore_assets, rewrite_asset_uris
from app.core.pending_finish import finish_pending


def approve_engine(
    pending_id: str,
    item: dict[str, Any],
    document: dict[str, Any] | None,
) -> dict[str, Any]:
    from app.bank_engine import service as engine_service

    assets = item.get("assets") or []
    doc = copy.deepcopy(document) if isinstance(document, dict) else copy.deepcopy(item["question"])
    doc.pop("id", None)
    mapping = move_assets_to_uploads(assets)
    rewrite_asset_uris(doc, mapping)
    try:
        created = engine_service.create_question(doc)
    except BaseException:
        restore_assets(mapping)
        raise
    finished = finish_pending(item, pending_id, created.id)
    return {
        "pending_id": pending_id,
        "question_id": created.id,
        "created": True,
        "overwritten": False,
        "merged_solution": False,
        "engine": 2,
        "batch": finished,
        "question": doc,
    }


__all__ = ["approve_engine"]

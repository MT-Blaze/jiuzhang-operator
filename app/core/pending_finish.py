"""批次收尾：删掉池子里的那一条、批次记一笔、未审数归零就物理清理。

旧主库与题库引擎 v2 两条入库路径共用这一处收尾，保证「题进了库、池子没清」
这种半截状态不会出现。
"""

from __future__ import annotations

from typing import Any

from app.core.pending_assets import drop_assets
from app.core.pending_bank_batches import _settle_batch
from app.core.pending_batches import remember_approved
from app.core.pending_db import connect


def finish_pending(item: dict[str, Any], pending_id: str,
                   question_id: str) -> dict[str, Any]:
    """入库/合并的收尾：池子里这条删掉、批次记一笔、未审数归零就物理清理。"""
    batch_id = str(item.get("batch_id") or "")
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM pending_questions WHERE id = ?", (pending_id,))
        remember_approved(con, batch_id, str(question_id or ""))
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    drop_assets(item.get("assets") or [])
    return _settle_batch(batch_id)


__all__ = ["finish_pending"]

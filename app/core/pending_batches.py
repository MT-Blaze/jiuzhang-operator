"""中转站的批次与条目读写：``batches`` / ``pending_questions`` 两张表的账。

批次卡片上的未审数一律按池子里真实的行数算——存的 ``pending_count`` 只是缓存，
不是事实来源；``seq`` 是「录入次序」的正身：同一批题一次写进去、时间戳全一样，
光看时间分不出先后。

公共元数据的读法（``read_meta``）与「已入库题号」（``read_approved``）也在这里，
因为它们就是 ``batches`` 上的两个 JSON 列。
"""

from __future__ import annotations

import json
from typing import Any

from app.core import questions
from app.core.pending_db import (
    BATCH_ID_RE,
    PENDING_ID_RE,
    PendingError,
    PendingNotFound,
    connect,
)

def read_meta(row: sqlite3.Row) -> dict[str, Any]:
    """批次上的公共元数据；读不出来就当空对象，不猜。"""
    try:
        data = json.loads(row["meta_json"] or "{}")
    except (TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def read_approved(row: sqlite3.Row) -> list[dict[str, Any]]:
    """这一批已经进主库的题号（公共元数据后改时还要补写它们）。"""
    try:
        data = json.loads(row["approved_json"] or "[]")
    except (TypeError, ValueError):
        return []
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def remember_approved(con: sqlite3.Connection, batch_id: str, question_id: str) -> None:
    """记一笔「这一批的哪道题进了主库」。

    记下来是为了公共元数据后改时能补写：题已经不在池子里了，
    但它仍属于这一批，标准名与明细学校照样得落到它的 ``sources`` 上。
    """
    if not batch_id or not question_id:
        return
    row = batch_row(con, batch_id)
    if row is None:
        return
    items = read_approved(row)
    if any(str(item.get("question_id") or "") == question_id for item in items):
        return
    items.append({"question_id": question_id, "approved_at": questions.now_iso()})
    con.execute(
        "UPDATE batches SET approved_json = ? WHERE batch_id = ?",
        (json.dumps(items[-200:], ensure_ascii=False, separators=(",", ":")), batch_id),
    )


def batch_card(row: sqlite3.Row, live: int, *, pooled: int | None = None,
               con: sqlite3.Connection | None = None) -> dict[str, Any]:
    """批次卡片：时间、编号、未审数 / 总题数，外加原文件名、公共元数据与初查状态。

    ``pooled``／``con``（G5）是调用方**在同一条读事务里**给好的池内条数与那条连接：
    给了就照用、结论也从这条连接回读；都不传才让 ``scan_state`` 按老样子自己开连接——
    单点调用方（``pending_bank``、``pending_pool``）行为不变。
    """
    from app.core import meta_dict, pending_dedupe

    batch_id = str(row["batch_id"])
    return {
        "batch_id": batch_id,
        "label": str(row["label"]),
        "created_at": str(row["created_at"]),
        "updated_at": str(row["updated_at"]),
        "source_backup": str(row["source_backup"] or ""),
        "source_name": str(row["source_name"] or ""),
        "meta": meta_dict.decorate_meta(read_meta(row)),
        "approved_count": len(read_approved(row)),
        "total": int(row["total"] or 0),
        "pending_count": live,
        "done": live == 0,
        # 后台初查的进程内注解（3.1a）：纯读、不发 IO，无缓存即 pending。
        "dedupe": pending_dedupe.scan_state(batch_id, pooled=pooled, con=con),
    }


def batch_list() -> dict[str, Any]:
    """所有批次（卡片视图）。

    排序口径：**有未审的批次在前**（新到旧），**已审完的批次沉在最后**（新到旧）。
    未审数一律按池子里真实的行数算——存的计数只是缓存，不是事实来源。

    **一张卡片的所有读数出自同一快照**（G5）：``batches`` 行、待审行数、池内行数、
    初查结论，全部在**同一条连接的同一条读事务**里取完（``duplicate_pool`` 与
    ``dedupe_scans`` 各一次批量数，不再逐卡自开连接）。过去 ``batch_card`` 里的
    ``scan_state`` 自己开第二条连接数 ``pooled``、第三条连接回读结论，而抽走事务
    （写池行＋删待审＋落 done 一次提交）恰好落在这几次读之间，卡片就能读出
    「待审 2 ＋ 池内 2，总数才 2」这种重复计数的帧，或反过来「``done`` 配 ``pooled=0``」
    的空窗帧。卡片是在读事务内构造的，``BEGIN`` 之后到 ``rollback`` 之前不落任何人提交。
    """
    from app.core import pending_dedupe

    con = connect()
    try:
        con.execute("BEGIN")  # 只读事务：把这一批卡片的读点钉在同一份快照上
        try:
            rows = con.execute("SELECT * FROM batches").fetchall()
            live = {str(row["batch_id"]): int(row["n"]) for row in con.execute(
                "SELECT batch_id, COUNT(*) AS n FROM pending_questions GROUP BY batch_id"
            )}
            pooled = pending_dedupe.pooled_counts(con)
            cards = [batch_card(row, live.get(str(row["batch_id"]), 0),
                                 pooled=pooled.get(str(row["batch_id"]), 0), con=con)
                     for row in rows]
        finally:
            con.rollback()  # 只读事务就地收尾：本连接一行都没写
    finally:
        con.close()
    cards.sort(key=lambda card: (card["pending_count"] == 0,
                                 _sort_key(card["created_at"], card["batch_id"])))
    return {"batches": cards}


def _sort_key(created_at: str, batch_id: str) -> tuple[str, str]:
    """倒序用的排序键：先看时间，时间相同再看批次号（号大的新）。"""
    return (str(created_at or ""), str(batch_id or ""))


def batch_row(con: sqlite3.Connection, batch_id: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()


def refresh_batch(con: sqlite3.Connection, batch_id: str) -> None:
    """把批次的未审数刷成池子里的真实行数（总题数另有其账，见 save_draft）。"""
    live = int(con.execute(
        "SELECT COUNT(*) FROM pending_questions WHERE batch_id = ?", (batch_id,)
    ).fetchone()[0])
    row = batch_row(con, batch_id)
    if row is None:
        return
    con.execute(
        "UPDATE batches SET pending_count = ?, updated_at = ? WHERE batch_id = ?",
        (live, questions.now_iso(), batch_id),
    )


def next_seq(con: sqlite3.Connection, batch_id: str) -> int:
    """这一批的下一个次序号。

    次序号是「录入次序」的正身：同一批题是一次写进去的，时间戳全一样，
    光看时间分不出先后，只能靠这个号。
    """
    row = con.execute(
        "SELECT COALESCE(MAX(seq), 0) AS top FROM pending_questions WHERE batch_id = ?",
        (batch_id,),
    ).fetchone()
    return int(row["top"] or 0) + 1


def list_batch_questions(batch_id: str) -> dict[str, Any]:
    """按批次拉取待审题目（录入先后顺序）。"""
    if not BATCH_ID_RE.match(str(batch_id or "")):
        raise PendingNotFound("批次编号不合法")
    con = connect()
    try:
        batch = batch_row(con, batch_id)
        if batch is None:
            raise PendingNotFound("中转站里没有这个批次")
        rows = con.execute(
            "SELECT id, batch_id, doc_json, assets_json, origin, created_at, updated_at"
            " FROM pending_questions WHERE batch_id = ? ORDER BY seq ASC, id ASC",
            (batch_id,),
        ).fetchall()
    finally:
        con.close()
    return {
        "batch_id": batch_id,
        "items": [row_to_item(row) for row in rows],
        "pending_count": len(rows),
        "total": int(batch["total"] or 0),
    }


def row_to_item(row: sqlite3.Row) -> dict[str, Any]:
    document = json.loads(row["doc_json"])
    document["id"] = row["id"]
    assets = json.loads(row["assets_json"]) if row["assets_json"] else []
    return {
        "id": row["id"],
        "batch_id": row["batch_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "origin": row["origin"],
        "question": document,
        "assets": assets,
    }
def get_pending(pending_id: str) -> dict[str, Any]:
    """取池子里的一条；不在就是 404。"""
    if not PENDING_ID_RE.match(str(pending_id or "")):
        raise PendingNotFound("中转站编号不合法")
    con = connect()
    try:
        row = con.execute(
            "SELECT id, batch_id, doc_json, assets_json, origin, created_at, updated_at"
            " FROM pending_questions WHERE id = ?",
            (pending_id,),
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise PendingNotFound("中转站里没有这一条")
    return row_to_item(row)

def item_parts(item: Any) -> tuple[dict[str, Any], Any, str]:
    """把一条待暂存内容拆成「题目文档 + 配图清单 + 要更新的中转站号」。

    两种形状都收：``{"question": {...}, "assets": [...]}``（信封）与裸题目文档。
    信封里还可以带 ``pending_id``：带了就表示**就地更新**池子里那一条，而不是
    再塞一条新的进去——老师改完点【存为待审】，池子里不该多出一道重影。
    """
    if not isinstance(item, dict):
        raise PendingError("每一条待暂存内容都必须是对象")
    pending_id = str(item.get("pending_id") or "").strip()
    if pending_id and not PENDING_ID_RE.match(pending_id):
        raise PendingError("中转站编号不合法")
    if isinstance(item.get("question"), dict):
        return item["question"], item.get("assets"), pending_id
    return item, None, pending_id

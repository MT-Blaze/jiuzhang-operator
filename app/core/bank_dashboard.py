"""core-bank 引擎的看板口径：题数、录入节奏与近 N 日曲线。

只读聚合，不改任何数据；「近 N 日」按本地时区（UTC+8）切日，
与老师看日历的直觉一致——缺题的那天要补 0，不然曲线会自己「跳过」周末。"""

from __future__ import annotations

from app.core.bank_schema import EXT_MIGRATION_KEY, LOCAL_TZ, connect
from datetime import datetime, timedelta
from typing import Any



# ---------------------------------------------------------------- 数据看板

def dashboard_stats(plugin_id: str) -> dict[str, Any]:
    """看板四数 + 最近录入 5 题（只读，军令 #11 阶段一）。

    口径（写进 docs/API_REFERENCE.md，别处不得另说一套）：
    - ``total_questions``：questions 表总行数；
    - ``today_added``：按 ``created_at`` 前 10 位（东八区本地日）等于今天的入库数；
    - ``pending_review``：仍带未清灌库审核标记的题数（与待审队列 ``flag=any`` 同判据）；
    - ``stored_total``：总题数 − 待审核，即已清审、正式落库的题数；
    - ``recent``：按 ``created_at`` 倒序的 5 条轻量摘要（题干截 80 字），不装配全文。
    """
    today = datetime.now(LOCAL_TZ).date().isoformat()
    con = connect(plugin_id)
    try:
        total = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        today_added = int(con.execute(
            "SELECT COUNT(*) FROM questions WHERE substr(created_at, 1, 10) = ?",
            (today,),
        ).fetchone()[0])
        pending_review = int(con.execute(
            "SELECT COUNT(*) FROM questions q WHERE EXISTS ("
            " SELECT 1 FROM json_each(q.extensions) e"
            " WHERE json_extract(e.value, '$.key') = ?"
            " AND json_array_length(json_extract(e.value, '$.value.flags')) > 0)",
            (EXT_MIGRATION_KEY,),
        ).fetchone()[0])
        rows = con.execute(
            "SELECT id, type, difficulty, stem, created_at FROM questions"
            " ORDER BY created_at DESC, id DESC LIMIT 5"
        ).fetchall()
        return {
            "date": today,
            "total_questions": total,
            "today_added": today_added,
            "pending_review": pending_review,
            "stored_total": total - pending_review,
            "recent": [
                {
                    "id": row["id"],
                    "type": row["type"],
                    "difficulty": row["difficulty"],
                    "stem": row["stem"][:80],
                    "created_at": row["created_at"],
                }
                for row in rows
            ],
        }
    finally:
        con.close()


def daily_counts(plugin_id: str, days: int = 365) -> list[dict[str, Any]]:
    """最近 ``days`` 天（含今天）的按日入库数，逐日补零，供热力图直接铺格子。"""
    days = max(1, min(int(days), 3650))
    start = datetime.now(LOCAL_TZ).date() - timedelta(days=days - 1)
    con = connect(plugin_id)
    try:
        rows = con.execute(
            "SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count FROM questions"
            " WHERE substr(created_at, 1, 10) >= ? GROUP BY day",
            (start.isoformat(),),
        ).fetchall()
    finally:
        con.close()
    counts = {row["day"]: int(row["count"]) for row in rows}
    result: list[dict[str, Any]] = []
    for offset in range(days):
        day = (start + timedelta(days=offset)).isoformat()
        result.append({"date": day, "count": counts.get(day, 0)})
    return result

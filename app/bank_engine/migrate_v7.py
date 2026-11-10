"""引擎库 v6 → v7 迁移：两张关联桥表补 sort_order，支撑四栏联动的拖拽排序。

迁移三律（add-data-store 技能口径）：
- 版本化分派：由 builder.migrate 统一调度，本模块只管 v6 → v7 一步；
- 备份优先：动结构前先落 ``<库名>.pre-v7.bak``（sqlite backup API，幂等，WAL 安全）；
- 可回滚：整段单事务，失败 ROLLBACK；另提供 rollback 显式降回 v6（测试与救灾用）。

回填口径：桥表原本没有顺序信息，按主键序（分组列 + 成员列）给每个分组
回填 0..n-1——章节内知识点按知识点 id、考向内辅助标签按知识点 id，
与种子大纲的递增编号一致，老师看到的初始顺序稳定且可解释。
不变量自检：回填后逐组核对 0..n-1 连续无重复，不满足即回滚。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# (表名, 分组列, 成员列)：全部白名单常量，SQL 只拼这里，绝不拼用户输入。
ORDERED_MAPS: tuple[tuple[str, str, str], ...] = (
    ("chapter_knowledge_map", "chapter_id", "knowledge_point_id"),
    ("knowledge_exam_map", "exam_direction_id", "knowledge_point_id"),
)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(" + table + ")")}


def backup_pre_v7(conn: sqlite3.Connection) -> Path | None:
    """迁移前备份：已存在则跳过（幂等）；内存库无文件可备，返回 None。"""
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = str(row[2]) if row is not None else ""
    if not raw:
        return None
    path = Path(raw)
    target = path.with_name(path.name + ".pre-v7.bak")
    if target.exists():
        return target
    dest = sqlite3.connect(target, timeout=10.0)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def backfill_sort_order(conn: sqlite3.Connection) -> None:
    """按主键序给每个分组回填 0..n-1；新建库灌种后与迁移共用这一份口径。"""
    for table, group_col, member_col in ORDERED_MAPS:
        rows = conn.execute(
            "SELECT " + group_col + ", " + member_col + " FROM " + table
            + " ORDER BY " + group_col + ", " + member_col
        ).fetchall()
        seq: dict[int, int] = {}
        updates: list[tuple[int, int, int]] = []
        for row in rows:
            group = int(row[0])
            order = seq.get(group, 0)
            seq[group] = order + 1
            updates.append((order, group, int(row[1])))
        conn.executemany(
            "UPDATE " + table + " SET sort_order = ? WHERE "
            + group_col + " = ? AND " + member_col + " = ?",
            updates,
        )


def verify_sort_order(conn: sqlite3.Connection) -> None:
    """不变量自检：每个分组的 sort_order 必须是 0..n-1 连续且无重复。"""
    from app.bank_engine.builder import EngineBuildError

    for table, group_col, _ in ORDERED_MAPS:
        rows = conn.execute(
            "SELECT " + group_col + ", COUNT(*), MIN(sort_order), MAX(sort_order), "
            "COUNT(DISTINCT sort_order) FROM " + table + " GROUP BY " + group_col
        ).fetchall()
        for row in rows:
            count = int(row[1])
            if int(row[2]) != 0 or int(row[3]) != count - 1 or int(row[4]) != count:
                raise EngineBuildError(
                    "sort_order 回填自检失败：" + table + " 分组 " + str(row[0])
                )


def upgrade(conn: sqlite3.Connection) -> None:
    """v6 → v7：补列 + 回填 + 自检，单事务；任何一步失败整体回滚。"""
    backup_pre_v7(conn)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            for table, _, _ in ORDERED_MAPS:
                if "sort_order" not in _columns(conn, table):
                    conn.execute(
                        "ALTER TABLE " + table
                        + " ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"
                    )
            backfill_sort_order(conn)
            verify_sort_order(conn)
            conn.execute("PRAGMA user_version = 7")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = ""


def rollback(conn: sqlite3.Connection) -> None:
    """v7 → v6：丢掉两表 sort_order 列（顺序信息随之丢弃），显式降级路径。"""
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            for table, _, _ in ORDERED_MAPS:
                if "sort_order" in _columns(conn, table):
                    conn.execute("ALTER TABLE " + table + " DROP COLUMN sort_order")
            conn.execute("PRAGMA user_version = 6")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = ""


__all__ = [
    "ORDERED_MAPS",
    "backfill_sort_order",
    "backup_pre_v7",
    "rollback",
    "upgrade",
    "verify_sort_order",
]
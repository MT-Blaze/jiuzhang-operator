"""引擎库 v12 → v13 迁移：考试类型字典把「模考」正名为「模拟考」。

只改字典里的一个名字，不动任何题目、试卷与关联行：``dict_exam_types`` 的主键
与 ``exams.exam_type_id`` 原样保留，题库里已有的模拟考卷自动跟着换新名字。

迁移三律：
- 版本化分派：由 ``builder.migrate`` 统一调度，本模块只管 v12 → v13 一步；
- 备份优先：动数据前先落 ``<库名>.pre-v13.bak``（sqlite backup API，幂等）；
- 可回滚：整段单事务，失败 ROLLBACK；``rollback`` 把名字换回「模考」。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

OLD_NAME = "模考"
NEW_NAME = "模拟考"
MOCK_CODE = "mock"


def backup_pre_v13(conn: sqlite3.Connection) -> Path | None:
    """迁移前备份：已存在则跳过（幂等）；内存库无文件可备，返回 None。"""
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = str(row[2]) if row is not None else ""
    if not raw:
        return None
    path = Path(raw)
    target = path.with_name(path.name + ".pre-v13.bak")
    if target.exists():
        return target
    dest = sqlite3.connect(target, timeout=10.0)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def _rename(conn: sqlite3.Connection, source: str, target: str) -> int:
    """按 code 认准那一行再改名：不靠名字猜，换过名的库回滚也不会认错。"""
    cursor = conn.execute(
        "UPDATE dict_exam_types SET name = ? WHERE code = ? AND name = ?",
        (target, MOCK_CODE, source),
    )
    return int(cursor.rowcount or 0)


def _run(conn: sqlite3.Connection, body, version: int) -> None:
    previous_factory = conn.row_factory
    conn.isolation_level = None
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("BEGIN")
        try:
            body(conn)
            conn.execute("PRAGMA user_version = " + str(version))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = ""
        conn.row_factory = previous_factory


def upgrade(conn: sqlite3.Connection) -> None:
    """v12 → v13：``dict_exam_types`` 的 mock 行由「模考」改为「模拟考」。"""
    backup_pre_v13(conn)
    _run(conn, lambda inner: _rename(inner, OLD_NAME, NEW_NAME), 13)


def rollback(conn: sqlite3.Connection) -> None:
    """v13 → v12：把 mock 行的名字换回「模考」，其余一律不动。"""
    _run(conn, lambda inner: _rename(inner, NEW_NAME, OLD_NAME), 12)


__all__ = ["backup_pre_v13", "rollback", "upgrade"]

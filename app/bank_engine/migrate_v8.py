"""引擎库 v7 → v8 迁移：图片从表补 TikZ 源码列。

只加列、不搬数据：``path`` 仍指向原图文件，``tikz_code`` 为空时前端照旧显示原图；
两者可以共存，迁移与回滚都不得删除或覆盖磁盘上的任何原图。

迁移三律：
- 版本化分派：由 ``builder.migrate`` 统一调度，本模块只管 v7 → v8 一步；
- 备份优先：动结构前先落 ``<库名>.pre-v8.bak``（sqlite backup API，幂等，WAL 安全）；
- 可回滚：整段单事务，失败 ROLLBACK；``rollback`` 显式降回 v7（只丢代码列）。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

TABLE = "question_images"
COLUMN = "tikz_code"


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(" + table + ")")}


def backup_pre_v8(conn: sqlite3.Connection) -> Path | None:
    """迁移前备份：已存在则跳过（幂等）；内存库无文件可备，返回 None。"""
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = str(row[2]) if row is not None else ""
    if not raw:
        return None
    path = Path(raw)
    target = path.with_name(path.name + ".pre-v8.bak")
    if target.exists():
        return target
    dest = sqlite3.connect(target, timeout=10.0)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def upgrade(conn: sqlite3.Connection) -> None:
    """v7 → v8：question_images 补 tikz_code 列，单事务，失败整体回滚。"""
    backup_pre_v8(conn)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            if COLUMN not in _columns(conn, TABLE):
                conn.execute(
                    "ALTER TABLE " + TABLE + " ADD COLUMN " + COLUMN + " TEXT"
                )
            conn.execute("PRAGMA user_version = 8")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = ""


def rollback(conn: sqlite3.Connection) -> None:
    """v8 → v7：只丢掉 tikz_code 列；path 与磁盘原图一概不碰。"""
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            if COLUMN in _columns(conn, TABLE):
                conn.execute("ALTER TABLE " + TABLE + " DROP COLUMN " + COLUMN)
            conn.execute("PRAGMA user_version = 7")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = ""


__all__ = ["COLUMN", "TABLE", "backup_pre_v8", "rollback", "upgrade"]

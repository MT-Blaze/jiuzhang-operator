"""引擎库 v8 → v9 迁移：教材版本与册次解耦。

版本升为一等表 ``dim_textbook_versions``，``dim_textbooks`` 补 ``version_id`` 外键与
``volume_name``（纯册次名）。``name`` 保留完整书名，迁移不删不改任何书名/章节/关联。

迁移三律：
- 版本化分派：由 ``builder.migrate`` 统一调度，本模块只管 v8 → v9 一步；
- 备份优先：动结构前先落 ``<库名>.pre-v9.bak``（sqlite backup API，幂等，WAL 安全）；
- 可回滚：整段单事务，失败 ROLLBACK；``rollback`` 显式降回 v8（只丢新表/新列）。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from app.bank_engine import textbook_versions

VERSIONS_TABLE = "dim_textbook_versions"
BOOKS_TABLE = "dim_textbooks"
VERSION_COLUMN = "version_id"
VOLUME_COLUMN = "volume_name"
VERSION_INDEX = "ix_dim_textbooks_version"

CREATE_VERSIONS = """
CREATE TABLE IF NOT EXISTS dim_textbook_versions (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    code       TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    publisher  TEXT,
    subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    UNIQUE (subject_id, name)
)
"""

BOOK_COLUMNS = "id, name, code, sort_order, publisher, subject_id, grade_id"


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(" + table + ")")}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def backup_pre_v9(conn: sqlite3.Connection) -> Path | None:
    """迁移前备份：已存在则跳过（幂等）；内存库无文件可备，返回 None。"""
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = str(row[2]) if row is not None else ""
    if not raw:
        return None
    path = Path(raw)
    target = path.with_name(path.name + ".pre-v9.bak")
    if target.exists():
        return target
    dest = sqlite3.connect(target, timeout=10.0)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def backfill_versions(conn: sqlite3.Connection) -> None:
    """按书名切出版本行并回填每册的 version_id / volume_name；幂等可重跑。"""
    conn.execute(CREATE_VERSIONS)
    columns = _columns(conn, BOOKS_TABLE)
    if VERSION_COLUMN not in columns:
        conn.execute(
            "ALTER TABLE " + BOOKS_TABLE + " ADD COLUMN " + VERSION_COLUMN
            + " INTEGER REFERENCES " + VERSIONS_TABLE + "(id) ON DELETE RESTRICT"
        )
    if VOLUME_COLUMN not in columns:
        conn.execute("ALTER TABLE " + BOOKS_TABLE + " ADD COLUMN " + VOLUME_COLUMN + " TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS " + VERSION_INDEX
        + " ON " + BOOKS_TABLE + " (" + VERSION_COLUMN + ")"
    )
    rows = conn.execute(
        "SELECT " + BOOK_COLUMNS + " FROM " + BOOKS_TABLE + " ORDER BY subject_id, sort_order, id"
    ).fetchall()
    version_rows, mapping = textbook_versions.build_version_rows(rows)
    conn.executemany(
        "INSERT OR IGNORE INTO " + VERSIONS_TABLE
        + " (id, name, code, sort_order, publisher, subject_id) VALUES (?, ?, ?, ?, ?, ?)",
        version_rows,
    )
    conn.executemany(
        "UPDATE " + BOOKS_TABLE + " SET " + VERSION_COLUMN + " = ?, "
        + VOLUME_COLUMN + " = ? WHERE id = ?",
        [(version_id, volume, book_id) for book_id, (version_id, volume) in mapping.items()],
    )
    verify_versions(conn)


def verify_versions(conn: sqlite3.Connection) -> None:
    """不变量自检：每册都必须挂到已存在的版本，册次名不得为空。"""
    from app.bank_engine.builder import EngineBuildError

    missing = int(conn.execute(
        "SELECT COUNT(*) FROM " + BOOKS_TABLE + " WHERE " + VERSION_COLUMN + " IS NULL"
        " OR " + VOLUME_COLUMN + " IS NULL OR TRIM(" + VOLUME_COLUMN + ") = ''"
    ).fetchone()[0])
    if missing:
        raise EngineBuildError(f"教材版本回填缺失：{missing} 册未挂版本或册次为空")
    orphan = int(conn.execute(
        "SELECT COUNT(*) FROM " + BOOKS_TABLE + " AS b WHERE NOT EXISTS "
        "(SELECT 1 FROM " + VERSIONS_TABLE + " AS v WHERE v.id = b." + VERSION_COLUMN + ")"
    ).fetchone()[0])
    if orphan:
        raise EngineBuildError(f"教材版本外键悬空：{orphan} 册找不到版本")


def upgrade(conn: sqlite3.Connection) -> None:
    """v8 → v9：建版本表、补列、回填，单事务，失败整体回滚。"""
    backup_pre_v9(conn)
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            backfill_versions(conn)
            conn.execute("PRAGMA user_version = 9")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = ""


def rollback(conn: sqlite3.Connection) -> None:
    """v9 → v8：只丢版本表与两列；书名、章节、桥表一概不碰。"""
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            conn.execute("DROP INDEX IF EXISTS " + VERSION_INDEX)
            columns = _columns(conn, BOOKS_TABLE)
            if VOLUME_COLUMN in columns:
                conn.execute(
                    "ALTER TABLE " + BOOKS_TABLE + " DROP COLUMN " + VOLUME_COLUMN
                )
            if VERSION_COLUMN in columns:
                conn.execute(
                    "ALTER TABLE " + BOOKS_TABLE + " DROP COLUMN " + VERSION_COLUMN
                )
            conn.execute("DROP TABLE IF EXISTS " + VERSIONS_TABLE)
            conn.execute("PRAGMA user_version = 8")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = ""


__all__ = [
    "VERSIONS_TABLE",
    "backfill_versions",
    "backup_pre_v9",
    "rollback",
    "upgrade",
    "verify_versions",
]

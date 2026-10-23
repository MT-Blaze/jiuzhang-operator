"""SQLite 连接与结构自举。

结构版本写入 ``PRAGMA user_version``。任何后续迁移都必须在这里按版本递增，
并在改动结构前生成可验证备份（见 AGENTS.md 第 4 节）。

v1 → v2：difficulty 的 CHECK 由 basic/medium/hard/novel 改为 L1/L2/L3/L4
（schemas/question.json 2.0 的连带项）。SQLite 不能就地改 CHECK，因此走
「备份 → 建新表 → 按映射搬值 → 换名 → 校验行数」的重建路径。
"""

from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import DATABASE_FILENAME, settings
from app.core.contract import LEGACY_DIFFICULTY

SCHEMA_VERSION = 2

_QUESTIONS_TABLE_V2 = """
CREATE TABLE {target} (
    id              TEXT PRIMARY KEY,
    schema_version  TEXT NOT NULL,
    type            TEXT NOT NULL CHECK (
        type IN ('single_choice','multiple_choice','fill_blank','solution','proof','unknown')
    ),
    stem            TEXT NOT NULL,
    options_json    TEXT,
    answer_json     TEXT,
    solution        TEXT,
    difficulty      TEXT NOT NULL CHECK (
        difficulty IN ('L1','L2','L3','L4')
    ),
    tags_json       TEXT,
    taxonomy_json   TEXT,
    source_json     TEXT,
    images_json     TEXT,
    extensions_json TEXT,
    status          TEXT NOT NULL CHECK (
        status IN ('draft','published','archived')
    ),
    revision        INTEGER NOT NULL CHECK (revision >= 1),
    author          TEXT,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

_QUESTIONS_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions (created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_questions_type ON questions (type);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions (difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions (status);
"""

_DDL = (
    _QUESTIONS_TABLE_V2.format(target="questions")
    + _QUESTIONS_INDEXES
    + """
CREATE TABLE IF NOT EXISTS question_tombstones (
    id         TEXT PRIMARY KEY,
    deleted_at TEXT NOT NULL
);
"""
)

# 旧表搬到新表时难度按契约 2.0 的映射改值；映射外的脏值原样搬，
# 由新表 CHECK 挡下并让整次迁移回滚——宁可拒绝打开，不悄悄编造难度。
_MIGRATE_COLUMNS = (
    "id", "schema_version", "type", "stem", "options_json", "answer_json", "solution",
    "difficulty", "tags_json", "taxonomy_json", "source_json", "images_json",
    "extensions_json", "status", "revision", "author", "created_at", "updated_at",
)


def database_path() -> Path:
    return Path(settings.data_dir) / DATABASE_FILENAME


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    con = connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()


def _backup_before_migration(path: Path) -> Path:
    stamp = Path(str(path) + ".pre-v2.bak")
    if stamp.exists():
        return stamp
    con = sqlite3.connect(path, timeout=10.0)
    try:
        con.commit()
        target = sqlite3.connect(stamp)
        try:
            con.backup(target)
        finally:
            target.close()
    finally:
        con.close()
    return stamp


def _migrate_v1_to_v2(con: sqlite3.Connection, path: Path) -> None:
    _backup_before_migration(path)
    before = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
    case = "CASE difficulty " + " ".join(
        f"WHEN '{legacy}' THEN '{level}'" for legacy, level in LEGACY_DIFFICULTY.items()
    ) + " ELSE difficulty END"
    columns = ", ".join(_MIGRATE_COLUMNS)
    con.execute(_QUESTIONS_TABLE_V2.format(target="questions__v2"))
    con.execute(
        f"INSERT INTO questions__v2 ({columns}) "
        f"SELECT id, '2.0', type, stem, options_json, answer_json, solution, {case}, "
        "tags_json, taxonomy_json, source_json, images_json, extensions_json, status, "
        "revision, author, created_at, updated_at FROM questions"
    )
    moved = int(con.execute("SELECT COUNT(*) FROM questions__v2").fetchone()[0])
    if moved != before:
        raise RuntimeError(f"难度口径迁移行数不符：搬 {moved} 行，原表 {before} 行，已回滚。")
    con.execute("DROP TABLE questions")
    con.execute("ALTER TABLE questions__v2 RENAME TO questions")
    con.executescript(_QUESTIONS_INDEXES)


def init_db() -> None:
    """幂等建库；拒绝打开高于当前程序支持版本的数据库。"""

    con = connect()
    try:
        try:
            con.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error:
            # 只读或网络文件系统可能不支持 WAL，单机回退到默认日志模式。
            pass

        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise RuntimeError(
                f"数据库结构版本 {version} 高于程序支持的 {SCHEMA_VERSION}，请升级程序或恢复备份。"
            )
        if version < 1:
            con.executescript(_DDL)
        elif version == 1:
            _migrate_v1_to_v2(con, database_path())
        if version != SCHEMA_VERSION:
            con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

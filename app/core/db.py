"""SQLite 连接与结构自举。

结构版本写入 ``PRAGMA user_version``。任何后续迁移都必须在这里按版本递增，
并在改动结构前生成可验证备份（见 AGENTS.md 第 4 节）。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.config import DATABASE_FILENAME, settings

SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS questions (
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
        difficulty IN ('basic','medium','hard','novel')
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

CREATE INDEX IF NOT EXISTS idx_questions_created_at ON questions (created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_questions_type ON questions (type);
CREATE INDEX IF NOT EXISTS idx_questions_difficulty ON questions (difficulty);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions (status);

CREATE TABLE IF NOT EXISTS question_tombstones (
    id         TEXT PRIMARY KEY,
    deleted_at TEXT NOT NULL
);
"""


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
        if version != SCHEMA_VERSION:
            con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        con.commit()
    finally:
        con.close()

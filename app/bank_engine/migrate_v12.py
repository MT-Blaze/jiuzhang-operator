"""引擎库 v11 → v12 迁移：教研字典唯一键补上学段维度。

课标原文里同一名称会在不同学段各自成立（如「运算能力」小学与初中、
「物理观念」初中与高中）。v11 的 ``(subject_id, name)`` 联合唯一挡死了
逐学段分列，只能退回「全学段」糊成一行。v12 把唯一口径改成
``(subject_id, name, stage)``，让课标清单按学段原样落库。

迁移三律：
- 版本化分派：由 ``builder.migrate`` 统一调度，本模块只管 v11 → v12 一步；
- 备份优先：动结构前先落 ``<库名>.pre-v12.bak``（sqlite backup API，幂等，WAL 安全）；
- 可回滚：整段单事务，失败 ROLLBACK；``rollback`` 降回 v11 时对跨学段重名
  临时补「（学段）」后缀，``upgrade`` 再把该后缀洗掉，往返不丢行、不改 id。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

TABLES: tuple[str, ...] = (
    "dict_subject_thoughts",
    "dict_solution_methods",
    "dict_core_competencies",
)
STAGE_ALL = "全学段"
STAGE_VALUES: tuple[str, ...] = ("小学", "初中", "高中", STAGE_ALL)

NEW_TABLE = """
CREATE TABLE {staging} (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    code       TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    stage      TEXT NOT NULL DEFAULT '全学段'
               CHECK (stage IN ('小学', '初中', '高中', '全学段')),
    UNIQUE (subject_id, name, stage)
)
"""

OLD_TABLE = """
CREATE TABLE {staging} (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    code       TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    stage      TEXT NOT NULL DEFAULT '全学段'
               CHECK (stage IN ('小学', '初中', '高中', '全学段')),
    UNIQUE (subject_id, name)
)
"""


def _rows(conn: sqlite3.Connection, table: str) -> list[tuple]:
    return [
        tuple(row)
        for row in conn.execute(
            "SELECT id, name, code, sort_order, subject_id, stage FROM " + table
            + " ORDER BY id"
        )
    ]


def _stage(value: object) -> str:
    text = str(value or "").strip()
    return text if text in STAGE_VALUES else STAGE_ALL


def _strip_stage_suffix(name: object, stage: str) -> str:
    """洗净 rollback 临时补上的「（学段）」后缀，只认与本行学段一致的那种。"""
    text = str(name or "").strip()
    if stage == STAGE_ALL:
        return text
    suffix = "（" + stage + "）"
    return text[: -len(suffix)].strip() if text.endswith(suffix) else text


def _widened(table: str, rows: list[tuple]) -> list[tuple]:
    """v11 → v12：只放宽唯一键，名称与 id 原样保留。"""
    out: list[tuple] = []
    for row_id, name, code, sort_order, subject_id, stage in rows:
        stage_text = _stage(stage)
        clean = _strip_stage_suffix(name, stage_text)
        if not clean:
            raise RuntimeError(f"{table} 第 {row_id} 行清洗后名称为空")
        out.append((int(row_id), clean, str(code), int(sort_order), int(subject_id), stage_text))
    return out


def _narrowed(table: str, rows: list[tuple]) -> list[tuple]:
    """v12 → v11：跨学段重名临时补「（学段）」后缀，保证 (subject_id, name) 不撞。"""
    out: list[tuple] = []
    seen: set[tuple[int, str]] = set()
    for row_id, name, code, sort_order, subject_id, stage in rows:
        subject_id = int(subject_id)
        stage_text = _stage(stage)
        text = str(name)
        key = (subject_id, text)
        if key in seen:
            text = f"{text}（{stage_text}）"
            key = (subject_id, text)
            if key in seen:
                raise RuntimeError(
                    f"{table} 学科 {subject_id} 回滚时重名：{text}（id={row_id}）"
                )
        seen.add(key)
        out.append((int(row_id), text, str(code), int(sort_order), subject_id, stage_text))
    return out


def _replace(conn: sqlite3.Connection, table: str, staging: str) -> None:
    conn.execute("DROP TABLE " + table)
    conn.execute("ALTER TABLE " + staging + " RENAME TO " + table)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_" + table + "_subject ON " + table + " (subject_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_" + table + "_stage ON " + table + " (stage)"
    )


def _rebuild(conn: sqlite3.Connection, template: str, transform) -> None:
    for table in TABLES:
        staging = table + "_v12"
        rows = transform(table, _rows(conn, table))
        conn.execute("DROP TABLE IF EXISTS " + staging)
        conn.execute(template.format(staging=staging))
        conn.executemany(
            "INSERT INTO " + staging
            + " (id, name, code, sort_order, subject_id, stage) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        _replace(conn, table, staging)


def backup_pre_v12(conn: sqlite3.Connection) -> Path | None:
    """迁移前备份：已存在则跳过（幂等）；内存库无文件可备，返回 None。"""
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = str(row[2]) if row is not None else ""
    if not raw:
        return None
    path = Path(raw)
    target = path.with_name(path.name + ".pre-v12.bak")
    if target.exists():
        return target
    dest = sqlite3.connect(target, timeout=10.0)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    return target


def _run(conn: sqlite3.Connection, body, version: int) -> None:
    previous_factory = conn.row_factory
    conn.isolation_level = None
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
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
        conn.execute("PRAGMA foreign_keys = ON")
        conn.isolation_level = ""
        conn.row_factory = previous_factory


def upgrade(conn: sqlite3.Connection) -> None:
    """v11 → v12：三张教研字典唯一键改为 (subject_id, name, stage)。"""
    backup_pre_v12(conn)
    _run(conn, lambda inner: _rebuild(inner, NEW_TABLE, _widened), 12)


def rollback(conn: sqlite3.Connection) -> None:
    """v12 → v11：恢复 (subject_id, name) 唯一；跨学段重名补「（学段）」后缀。"""
    _run(conn, lambda inner: _rebuild(inner, OLD_TABLE, _narrowed), 11)


__all__ = ["backup_pre_v12", "rollback", "upgrade"]

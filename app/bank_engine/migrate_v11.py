"""引擎库 v10 → v11 迁移：教研字典名称改同学科联合唯一，并清洗学科后缀。

三张教研字典（学科思想 / 解题方法 / 核心素养）原先对 ``name`` 做全表唯一，
为了绕开冲突只能把生物、科学、美术里的同名条目写成「科学思维（生物）」这类
脏名字。v11 把唯一口径改成 ``(subject_id, name)`` 联合唯一，同时：
- 去掉名称末尾由旧约束逼出来的学科括注；
- 保留 ``code`` 的全表唯一，系统标识不改；
- 保留全部行 id 与学段，关联表不需要跟着改号。

迁移三律：
- 版本化分派：由 ``builder.migrate`` 统一调度，本模块只管 v10 → v11 一步；
- 备份优先：动结构前先落 ``<库名>.pre-v11.bak``（sqlite backup API，幂等，WAL 安全）；
- 可回滚：整段单事务，失败 ROLLBACK；``rollback`` 显式降回 v10 结构。
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
# 初中引入、高中继续高频使用的通用方法：学段口径统一改「全学段」。
CROSS_STAGE_METHOD_CODES: frozenset[str] = frozenset({
    "math_completing_square",
    "math_undetermined",
    "math_discriminant",
    "math_contradiction",
    "math_substitution_elimination",
    "math_add_sub_elimination",
    "math_factorization_method",
})

NEW_TABLE = """
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

OLD_TABLE = """
CREATE TABLE {staging} (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL UNIQUE,
    code       TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    stage      TEXT NOT NULL DEFAULT '全学段'
               CHECK (stage IN ('小学', '初中', '高中', '全学段'))
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


def _subject_names(conn: sqlite3.Connection) -> dict[int, str]:
    return {
        int(row[0]): str(row[1])
        for row in conn.execute("SELECT id, name FROM dict_subjects")
    }


def _clean_name(name: object, subject_name: str) -> str:
    text = str(name or "").strip()
    for suffix in ("（" + subject_name + "）", "(" + subject_name + ")"):
        if text.endswith(suffix):
            return text[: -len(suffix)].strip()
    return text


def _stage(value: object) -> str:
    text = str(value or "").strip()
    return text if text in STAGE_VALUES else STAGE_ALL


def _unique_names(
    table: str, rows: list[tuple], subjects: dict[int, str]
) -> list[tuple]:
    cleaned: list[tuple] = []
    seen: set[tuple[int, str]] = set()
    for row_id, name, code, sort_order, subject_id, stage in rows:
        subject_id = int(subject_id)
        clean = _clean_name(name, subjects.get(subject_id, ""))
        if not clean:
            raise RuntimeError(f"{table} 第 {row_id} 行清洗后名称为空")
        key = (subject_id, clean)
        if key in seen:
            raise RuntimeError(
                f"{table} 学科 {subject_id} 清洗后出现重名：{clean}（id={row_id}）"
            )
        seen.add(key)
        stage_text = _stage(stage)
        if table == "dict_solution_methods" and str(code) in CROSS_STAGE_METHOD_CODES:
            stage_text = STAGE_ALL
        cleaned.append(
            (int(row_id), clean, str(code), int(sort_order), subject_id, stage_text)
        )
    return cleaned


def _disambiguated(
    table: str, rows: list[tuple], subjects: dict[int, str]
) -> list[tuple]:
    """回滚到全局唯一口径：跨学科重名重新加回学科括注。"""
    counts: dict[str, int] = {}
    for _, name, *_ in rows:
        counts[str(name)] = counts.get(str(name), 0) + 1
    out: list[tuple] = []
    for row_id, name, code, sort_order, subject_id, stage in rows:
        text = str(name)
        if counts[text] > 1:
            text = f"{text}（{subjects.get(int(subject_id), '其他')}）"
        out.append((row_id, text, code, sort_order, subject_id, stage))
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
    subjects = _subject_names(conn)
    for table in TABLES:
        staging = table + "_v11"
        rows = transform(table, _rows(conn, table), subjects)
        conn.execute("DROP TABLE IF EXISTS " + staging)
        conn.execute(template.format(staging=staging))
        conn.executemany(
            "INSERT INTO " + staging
            + " (id, name, code, sort_order, subject_id, stage) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        _replace(conn, table, staging)


def backup_pre_v11(conn: sqlite3.Connection) -> Path | None:
    """迁移前备份：已存在则跳过（幂等）；内存库无文件可备，返回 None。"""
    row = conn.execute("PRAGMA database_list").fetchone()
    raw = str(row[2]) if row is not None else ""
    if not raw:
        return None
    path = Path(raw)
    target = path.with_name(path.name + ".pre-v11.bak")
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
    """v10 → v11：三张教研字典改同学科联合唯一并洗掉名称里的学科括注。"""
    backup_pre_v11(conn)
    _run(
        conn,
        lambda inner: _rebuild(inner, NEW_TABLE, _unique_names),
        11,
    )


def rollback(conn: sqlite3.Connection) -> None:
    """v11 → v10：恢复名称全表唯一；跨学科重名重新加学科括注。"""
    _run(
        conn,
        lambda inner: _rebuild(inner, OLD_TABLE, _disambiguated),
        10,
    )


__all__ = ["backup_pre_v11", "rollback", "upgrade"]

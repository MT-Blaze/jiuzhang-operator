"""题库引擎 v2 的自动建库：按插件 schema 建 36 表，再灌入全量种子。

建库在临时文件里完成，原子替换目标库；任何一步失败都不留下半成品。
已有合法结构直接复用；低版本库先在原地迁移，只有显式 ``force`` 或结构损坏时才重建，
重建前先备份。
"""

from __future__ import annotations

import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

from app.bank_engine import (
    migrate_legacy,
    migrate_v10,
    migrate_v11,
    migrate_v12,
    migrate_v7,
    migrate_v8,
    migrate_v9,
    paths,
    seeding,
)
from app.bank_engine.models import BuildReport

BASE_TABLES: tuple[str, ...] = (
    "dict_subjects",
    "dict_grades",
    "dict_question_types",
    "dict_difficulties",
    "dict_question_qualities",
    "dict_exam_types",
    "dim_regions",
    "dim_schools",
    "dim_textbook_versions",
    "dim_textbooks",
    "dim_textbook_chapters",
    "exams",
    "exam_school_map",
    "dim_knowledge_points",
    "dim_exam_directions",
    "knowledge_exam_map",
    "chapter_knowledge_map",
    "ingest_batches",
    "raw_questions",
    "questions",
    "question_options",
    "question_images",
    "question_answers",
    "question_remarks",
    "question_solutions",
    "question_supplements",
    "question_statistics",
    "question_exam_map",
    "question_knowledge_map",
    "question_exams",
    "dict_subject_thoughts",
    "dict_solution_methods",
    "dict_core_competencies",
    "solution_thought_map",
    "solution_method_map",
    "solution_competency_map",
)
CREATE_TABLE_RE = re.compile(
    r"CREATE\s+(?:VIRTUAL\s+)?TABLE\s+([A-Za-z_][A-Za-z0-9_]*)", re.IGNORECASE
)


class EngineBuildError(RuntimeError):
    pass


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {
        table: int(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
        for table in seeding.EXPECTED_COUNTS
    }


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' "
            "AND name NOT LIKE 'sqlite_%'"
        )
    }


def validate_connection(conn: sqlite3.Connection, *, require_seeds: bool) -> dict[str, int]:
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    if version != paths.SCHEMA_VERSION:
        raise EngineBuildError(f"结构版本 {version} != {paths.SCHEMA_VERSION}")
    names = _table_names(conn)
    missing = sorted(set(BASE_TABLES) - names)
    if missing:
        raise EngineBuildError("缺表：" + "、".join(missing))
    integrity = [row[0] for row in conn.execute("PRAGMA integrity_check")]
    if integrity != ["ok"]:
        raise EngineBuildError(f"integrity_check 异常：{integrity}")
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise EngineBuildError(f"foreign_key_check 异常：{violations[:5]}")
    counts = _counts(conn)
    if require_seeds:
        mismatched = {
            table: (counts[table], expected)
            for table, expected in seeding.EXPECTED_COUNTS.items()
            if counts[table] != expected
        }
        if mismatched:
            raise EngineBuildError(f"种子计数不符：{mismatched}")
    return counts


def _backup_invalid(path: Path) -> Path | None:
    if not path.is_file():
        return None
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    target = path.with_name(path.name + f".invalid-{stamp}.bak")
    path.replace(target)
    return target


def migrate(conn: sqlite3.Connection, version: int) -> bool:
    if version == paths.SCHEMA_VERSION:
        return False
    if version not in (2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
        raise EngineBuildError(f"无法从结构版本 {version} 迁移到 {paths.SCHEMA_VERSION}")
    if version < 6:
        migrate_legacy.run(conn, version)
    # v7 的迁移含 sort_order 回填，只对 v6 及更老的库执行；v7 库直接进 v8，
    # 否则会按主键序重排老师已经拖好的顺序。
    if version in (2, 3, 4, 5, 6):
        migrate_v7.upgrade(conn)
    if version < 8:
        migrate_v8.upgrade(conn)
    if version < 9:
        migrate_v9.upgrade(conn)
    if version < 10:
        migrate_v10.upgrade(conn)
    if version < 11:
        migrate_v11.upgrade(conn)
    if version < 12:
        migrate_v12.upgrade(conn)
    return True


def _build_into(path: Path, schema: Path) -> dict[str, int]:
    temp = path.with_name(path.name + ".part")
    for suffix in ("", "-wal", "-shm", "-journal"):
        candidate = Path(str(temp) + suffix)
        if candidate.exists():
            candidate.unlink()
    body = schema.read_text(encoding="utf-8")
    declared = {name.lower() for name in CREATE_TABLE_RE.findall(body)}
    missing = sorted(name for name in BASE_TABLES if name not in declared)
    if missing:
        raise EngineBuildError("schema 缺表：" + "、".join(missing))
    conn = sqlite3.connect(temp, timeout=30.0)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(body)
        with conn:
            counts = seeding.apply_seeds(conn)
            migrate_v7.backfill_sort_order(conn)
        validate_connection(conn, require_seeds=True)
    finally:
        conn.close()
    os.replace(temp, path)
    return counts


def build_engine(
    *,
    force: bool = False,
    db_path: Path | None = None,
    schema: Path | None = None,
) -> BuildReport:
    target = Path(db_path) if db_path else paths.engine_db_path()
    schema_file = Path(schema) if schema else paths.schema_path()
    if not schema_file.is_file():
        raise EngineBuildError(f"缺 schema：{schema_file}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_file() and not force:
        conn = sqlite3.connect(target, timeout=10.0)
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            migrate(conn, version)
            counts = validate_connection(conn, require_seeds=False)
        except (sqlite3.Error, EngineBuildError):
            conn.close()
            _backup_invalid(target)
        else:
            conn.close()
            return BuildReport(str(target), False, counts)
    elif target.is_file():
        _backup_invalid(target)
    counts = _build_into(target, schema_file)
    return BuildReport(str(target), True, counts)

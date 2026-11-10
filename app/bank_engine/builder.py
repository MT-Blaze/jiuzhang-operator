"""题库引擎 v2 的自动建库：按插件 schema 建 35 表，再灌入全量种子。

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

from app.bank_engine import paths, regions, seeding
from app.bank_engine.models import BuildReport
from app.bank_engine.seeds.exam_seed import EXAM_ROWS, EXAM_SCHOOL_ROWS, EXAM_TYPE_ROWS

BASE_TABLES: tuple[str, ...] = (
    "dict_subjects",
    "dict_grades",
    "dict_question_types",
    "dict_difficulties",
    "dict_question_qualities",
    "dict_exam_types",
    "dim_regions",
    "dim_schools",
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


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(" + table + ")")}


_TEACHING_TABLES = (
    "dict_subject_thoughts",
    "dict_solution_methods",
    "dict_core_competencies",
)


def _migrate_v2_to_v3(conn: sqlite3.Connection) -> None:
    """v2 → v3：知识点/考向/教学字典去掉年级外键，教学字典改驻学段。

    教学字典原有年级先折算成学段再删列，迁移不丢数据；整段在单事务内完成。
    """
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            for index in (
                "ix_dim_knowledge_points_grade",
                "ix_dim_exam_directions_grade",
                "ix_dict_subject_thoughts_grade",
                "ix_dict_solution_methods_grade",
                "ix_dict_core_competencies_grade",
            ):
                conn.execute("DROP INDEX IF EXISTS " + index)
            for table in _TEACHING_TABLES:
                if "stage" not in _columns(conn, table):
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN stage TEXT")
                    conn.execute(
                        f"UPDATE {table} SET stage = (SELECT g.stage FROM dict_grades g "
                        f"WHERE g.id = {table}.grade_id) WHERE grade_id IS NOT NULL"
                    )
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS ix_{table}_stage ON {table} (stage)"
                )
            for table in ("dim_knowledge_points", "dim_exam_directions", *_TEACHING_TABLES):
                if "grade_id" in _columns(conn, table):
                    conn.execute(f"ALTER TABLE {table} DROP COLUMN grade_id")
            conn.execute("PRAGMA user_version = 3")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _migrate_v3_to_v4(conn: sqlite3.Connection) -> None:
    """v3 → v4：补章节-知识点桥表，教材物理目录与逻辑知识点彻底解耦。"""
    conn.isolation_level = None
    try:
        conn.execute("BEGIN")
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS chapter_knowledge_map ("
                "chapter_id INTEGER NOT NULL "
                "REFERENCES dim_textbook_chapters(id) ON DELETE RESTRICT, "
                "knowledge_point_id INTEGER NOT NULL "
                "REFERENCES dim_knowledge_points(id) ON DELETE RESTRICT, "
                "PRIMARY KEY (chapter_id, knowledge_point_id)) WITHOUT ROWID"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_chapter_knowledge_map_knowledge_point "
                "ON chapter_knowledge_map (knowledge_point_id)"
            )
            conn.execute("PRAGMA user_version = 4")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.isolation_level = ""


def _migrate_v4_to_v5(conn: sqlite3.Connection) -> None:
    """v4 → v5：补行政区划字典，学校表加 region_id 并按现有 region 文本回填。"""
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            regions.ensure_regions(conn)
            if "region_id" not in _columns(conn, "dim_schools"):
                conn.execute(
                    "ALTER TABLE dim_schools ADD COLUMN region_id INTEGER "
                    "REFERENCES dim_regions(id) ON DELETE RESTRICT"
                )
            regions.backfill_schools(conn)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS ix_dim_schools_region "
                "ON dim_schools (region_id)"
            )
            conn.execute("PRAGMA user_version = 5")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def _exam_type_id(conn: sqlite3.Connection, name: str) -> int:
    row = conn.execute("SELECT id FROM dict_exam_types WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return int(row[0])
    row = conn.execute("SELECT id FROM dict_exam_types WHERE name = '自编题'").fetchone()
    if row is None:
        raise EngineBuildError("考试类型字典缺少「自编题」兜底行")
    return int(row[0])


def _source_subject_grade(conn: sqlite3.Connection, row: tuple) -> tuple[int, int]:
    """旧来源没有学科列：优先沿章节 → 教材版本继承，取不到才落数学 / 高三。"""
    subject_id = 2
    grade_id = int(row[6]) if row[6] is not None else 12
    chapter_id = row[7]
    if chapter_id is not None:
        chapter = conn.execute(
            "SELECT textbook_id FROM dim_textbook_chapters WHERE id = ?", (chapter_id,)
        ).fetchone()
        if chapter is not None:
            book = conn.execute(
                "SELECT subject_id, grade_id FROM dim_textbooks WHERE id = ?",
                (int(chapter[0]),),
            ).fetchone()
            if book is not None:
                subject_id = int(book[0])
                if row[6] is None and book[1] is not None:
                    grade_id = int(book[1])
    return subject_id, grade_id


def _create_exam_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS dict_exam_types ("
        "id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, "
        "code TEXT NOT NULL UNIQUE, sort_order INTEGER NOT NULL DEFAULT 0)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS exams ("
        "id INTEGER PRIMARY KEY, code TEXT NOT NULL UNIQUE, "
        "year INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 2100), "
        "month INTEGER CHECK (month IS NULL OR month BETWEEN 1 AND 12), "
        "subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT, "
        "grade_id INTEGER NOT NULL REFERENCES dict_grades(id) ON DELETE RESTRICT, "
        "exam_type_id INTEGER NOT NULL REFERENCES dict_exam_types(id) ON DELETE RESTRICT, "
        "exam_subject TEXT NOT NULL, "
        "created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')))"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS exam_school_map ("
        "exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE RESTRICT, "
        "school_id INTEGER NOT NULL REFERENCES dim_schools(id) ON DELETE RESTRICT, "
        "PRIMARY KEY (exam_id, school_id)) WITHOUT ROWID"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS question_exams ("
        "question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE, "
        "exam_id INTEGER NOT NULL REFERENCES exams(id) ON DELETE RESTRICT, "
        "question_no TEXT, score REAL NOT NULL DEFAULT 0 CHECK (score >= 0), "
        "PRIMARY KEY (question_id, exam_id)) WITHOUT ROWID"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_exams_lookup "
        "ON exams (year, month, subject_id, grade_id, exam_type_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_exam_school_map_school "
        "ON exam_school_map (school_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_question_exams_exam ON question_exams (exam_id)"
    )


def _seed_exam_types(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO dict_exam_types (id, name, code, sort_order) "
        "VALUES (?, ?, ?, ?)",
        EXAM_TYPE_ROWS,
    )


def _migrate_sources(conn: sqlite3.Connection) -> None:
    from app.bank_engine.writer import normalize_exam_type

    if not _table_exists(conn, "dim_sources"):
        return
    id_map: dict[int, int] = {}
    rows = conn.execute(
        "SELECT id, name, code, exam_type, year, region, grade_id, chapter_id, school_id "
        "FROM dim_sources ORDER BY id"
    ).fetchall()
    for row in rows:
        subject_id, grade_id = _source_subject_grade(conn, row)
        exam_subject = str(row[1] or row[5] or "未命名试卷")[:120]
        cursor = conn.execute(
            "INSERT INTO exams "
            "(code, year, month, subject_id, grade_id, exam_type_id, exam_subject) "
            "VALUES (?, ?, NULL, ?, ?, ?, ?)",
            (
                "exm_" + str(row[2] or row[0]),
                int(row[4]) if row[4] is not None else 1900,
                subject_id,
                grade_id,
                _exam_type_id(conn, normalize_exam_type(str(row[3] or ""))),
                exam_subject,
            ),
        )
        exam_id = int(cursor.lastrowid)
        id_map[int(row[0])] = exam_id
        if row[8] is not None:
            conn.execute(
                "INSERT OR IGNORE INTO exam_school_map (exam_id, school_id) VALUES (?, ?)",
                (exam_id, int(row[8])),
            )
    if _table_exists(conn, "question_source_map"):
        for row in conn.execute(
            "SELECT question_id, source_id, question_no, score FROM question_source_map"
        ):
            exam_id = id_map.get(int(row[1]))
            if exam_id is not None:
                conn.execute(
                    "INSERT OR IGNORE INTO question_exams "
                    "(question_id, exam_id, question_no, score) VALUES (?, ?, ?, ?)",
                    (str(row[0]), exam_id, row[2], float(row[3])),
                )


def _seed_sample_exams(conn: sqlite3.Connection) -> None:
    """示例卷按 code 幂等追加，不抢迁移卷的自增 ID。"""
    sample_ids: dict[str, int] = {}
    for _, code, year, month, subject_id, grade_id, exam_type_id, subject in EXAM_ROWS:
        row = conn.execute("SELECT id FROM exams WHERE code = ?", (code,)).fetchone()
        if row is not None:
            sample_ids[code] = int(row[0])
            continue
        cursor = conn.execute(
            "INSERT INTO exams "
            "(code, year, month, subject_id, grade_id, exam_type_id, exam_subject) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (code, year, month, subject_id, grade_id, exam_type_id, subject),
        )
        sample_ids[code] = int(cursor.lastrowid)
    for exam_index, school_id in EXAM_SCHOOL_ROWS:
        code = EXAM_ROWS[exam_index - 1][1]
        conn.execute(
            "INSERT OR IGNORE INTO exam_school_map (exam_id, school_id) VALUES (?, ?)",
            (sample_ids[code], school_id),
        )


def _migrate_v5_to_v6(conn: sqlite3.Connection) -> None:
    """v5 → v6：废弃 dim_sources，改由 exams 属性组合 + exam_school_map 多校关联。"""
    conn.isolation_level = None
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN")
        try:
            _create_exam_tables(conn)
            _seed_exam_types(conn)
            _migrate_sources(conn)
            _seed_sample_exams(conn)
            conn.execute("DROP TRIGGER IF EXISTS trg_question_source_map_statistics_insert")
            conn.execute("DROP TRIGGER IF EXISTS trg_question_source_map_statistics_delete")
            conn.execute("DROP TABLE IF EXISTS question_source_map")
            conn.execute("DROP TABLE IF EXISTS dim_sources")
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS trg_question_exams_statistics_insert "
                "AFTER INSERT ON question_exams BEGIN "
                "UPDATE question_statistics SET reference_count = reference_count + 1 "
                "WHERE question_id = new.question_id; END"
            )
            conn.execute(
                "CREATE TRIGGER IF NOT EXISTS trg_question_exams_statistics_delete "
                "AFTER DELETE ON question_exams BEGIN "
                "UPDATE question_statistics SET reference_count = reference_count - 1 "
                "WHERE question_id = old.question_id; END"
            )
            conn.execute("PRAGMA user_version = 6")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def migrate(conn: sqlite3.Connection, version: int) -> bool:
    if version == paths.SCHEMA_VERSION:
        return False
    if version not in (2, 3, 4, 5):
        raise EngineBuildError(f"无法从结构版本 {version} 迁移到 {paths.SCHEMA_VERSION}")
    if version == 2:
        _migrate_v2_to_v3(conn)
    if version in (2, 3):
        _migrate_v3_to_v4(conn)
    if version in (2, 3, 4):
        _migrate_v4_to_v5(conn)
    _migrate_v5_to_v6(conn)
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

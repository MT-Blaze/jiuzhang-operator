"""v2 → v6 历史迁移：从旧 17 表底座与 dim_sources 演进到 exams 属性组合。

这些迁移只在老库原地升级时执行，``builder`` 仍负责建库与版本分派；
``run`` 按传入的起始版本顺序执行，每一步保持单事务与可重跑。
"""

from __future__ import annotations

import sqlite3

from app.bank_engine import regions
from app.bank_engine.seeds.exam_seed import EXAM_ROWS, EXAM_SCHOOL_ROWS, EXAM_TYPE_ROWS

_TEACHING_TABLES = (
    "dict_subject_thoughts",
    "dict_solution_methods",
    "dict_core_competencies",
)


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in conn.execute("PRAGMA table_info(" + table + ")")}


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
    ).fetchone()
    return row is not None


def _exam_type_id(conn: sqlite3.Connection, name: str) -> int:
    from app.bank_engine.builder import EngineBuildError

    row = conn.execute("SELECT id FROM dict_exam_types WHERE name = ?", (name,)).fetchone()
    if row is not None:
        return int(row[0])
    row = conn.execute("SELECT id FROM dict_exam_types WHERE name = '模考'").fetchone()
    if row is None:
        raise EngineBuildError("考试类型字典缺少「模考」兜底行")
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
        "id INTEGER PRIMARY KEY, "
        "year INTEGER NOT NULL CHECK (year BETWEEN 1900 AND 2100), "
        "exam_org_name TEXT, "
        "school_id INTEGER REFERENCES dim_schools(id) ON DELETE RESTRICT, "
        "month INTEGER CHECK (month IS NULL OR month BETWEEN 1 AND 12), "
        "exam_type_id INTEGER NOT NULL REFERENCES dict_exam_types(id) ON DELETE RESTRICT, "
        "mock_round INTEGER CHECK (mock_round IS NULL OR mock_round BETWEEN 1 AND 10), "
        "grade_id INTEGER NOT NULL REFERENCES dict_grades(id) ON DELETE RESTRICT, "
        "semester TEXT CHECK (semester IS NULL OR semester IN ('上学期', '下学期')), "
        "subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT)"
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
    conn.execute("CREATE INDEX IF NOT EXISTS ix_exams_school ON exams (school_id)")
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
        exam_org_name = str(row[1] or row[5] or "未命名试卷")[:120]
        cursor = conn.execute(
            "INSERT INTO exams "
            "(year, exam_org_name, school_id, month, exam_type_id, "
            "mock_round, grade_id, semester, subject_id) "
            "VALUES (?, ?, ?, NULL, ?, NULL, ?, NULL, ?)",
            (
                int(row[4]) if row[4] is not None else 1900,
                exam_org_name,
                None if row[8] is None else int(row[8]),
                _exam_type_id(conn, normalize_exam_type(str(row[3] or ""))),
                grade_id,
                subject_id,
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
    """示例卷按属性幂等追加，不抢迁移卷的自增 ID。"""
    sample_ids: dict[int, int] = {}
    for (
        seed_id, year, org, school_id, month, exam_type_id, mock_round, grade_id,
        semester, subject_id,
    ) in EXAM_ROWS:
        row = conn.execute(
            "SELECT id FROM exams WHERE year = ? AND COALESCE(month, 0) = ? "
            "AND COALESCE(mock_round, 0) = ? AND COALESCE(semester, '') = ? "
            "AND COALESCE(exam_org_name, '') = ? AND COALESCE(school_id, 0) = ? "
            "AND subject_id = ? AND grade_id = ? AND exam_type_id = ? "
            "ORDER BY id LIMIT 1",
            (
                year, month or 0, mock_round or 0, semester or "", org or "",
                school_id or 0, subject_id, grade_id, exam_type_id,
            ),
        ).fetchone()
        if row is not None:
            sample_ids[seed_id] = int(row[0])
            continue
        cursor = conn.execute(
            "INSERT INTO exams "
            "(year, exam_org_name, school_id, month, exam_type_id, "
            "mock_round, grade_id, semester, subject_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (year, org, school_id, month, exam_type_id, mock_round, grade_id,
             semester, subject_id),
        )
        sample_ids[seed_id] = int(cursor.lastrowid)
    for exam_id, school_id in EXAM_SCHOOL_ROWS:
        conn.execute(
            "INSERT OR IGNORE INTO exam_school_map (exam_id, school_id) VALUES (?, ?)",
            (sample_ids[exam_id], school_id),
        )


def _v2_to_v3(conn: sqlite3.Connection) -> None:
    """v2 → v3：知识点/考向/教学字典去掉年级外键，教学字典改驻学段。"""
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


def _v3_to_v4(conn: sqlite3.Connection) -> None:
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


def _v4_to_v5(conn: sqlite3.Connection) -> None:
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


def _v5_to_v6(conn: sqlite3.Connection) -> None:
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


def run(conn: sqlite3.Connection, version: int) -> None:
    """把 v2–v5 的库逐级升到 v6；调用方保证 version < 6。"""
    if version == 2:
        _v2_to_v3(conn)
    if version in (2, 3):
        _v3_to_v4(conn)
    if version in (2, 3, 4):
        _v4_to_v5(conn)
    if version in (2, 3, 4, 5):
        _v5_to_v6(conn)


__all__ = ["run"]

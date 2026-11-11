"""把沙盒验收库的全量种子翻译成关系表插入语句。

只做单表 ``executemany``，不在 SQL 里拼跨表结构；父子顺序即插入顺序。
"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.bank_engine import regions, textbook_versions
from app.bank_engine.seeds.books.registry import BOOK_ROWS, CHAPTER_ROWS
from app.bank_engine.seeds.curriculum import (
    CORE_COMPETENCY_ROWS,
    GRADE_ROWS,
    QUESTION_TYPE_ROWS,
    SOLUTION_METHOD_ROWS,
    SUBJECT_ROWS,
    SUBJECT_THOUGHT_ROWS,
)
from app.bank_engine.seeds.dictionaries import DIFFICULTY_SEED_ROWS, QUALITY_SEED_ROWS
from app.bank_engine.seeds.exam_seed import EXAM_ROWS, EXAM_SCHOOL_ROWS, EXAM_TYPE_ROWS
from app.bank_engine.seeds.exam_direction_seed import EXAM_DIRECTION_ROWS
from app.bank_engine.seeds.knowledge_seed import KNOWLEDGE_POINT_ROWS
from app.bank_engine.seeds.math_required1 import (
    MATH_REQUIRED1_CHAPTER_KNOWLEDGE_ROWS,
    MATH_REQUIRED1_EXAM_ROWS,
    MATH_REQUIRED1_KNOWLEDGE_EXAM_ROWS,
    MATH_REQUIRED1_KNOWLEDGE_ROWS,
)
from app.bank_engine.seeds.migrated_textbook_seed import (
    MIGRATED_BOOK_ROWS,
    MIGRATED_CHAPTER_ROWS,
)
from app.bank_engine.seeds.region_seed import REGION_ROWS
from app.bank_engine.seeds.school_seed import SCHOOL_ROWS
from app.bank_engine.seeds import national_catalog
from app.bank_engine.seeds.textbook_catalog import (
    CATALOG_BOOK_ROWS,
    CATALOG_VERSION_ROWS,
)

# 完整书名在灌种时切成「版本 + 册次」：版本行先落，教材册再挂 version_id。
# 高中数学与物理的 9 个新增版本由 textbook_catalog 显式给号，不参与自动切版本，
# 避免新增分组挤动既有 1..19 的版本 id。
BOOK_SOURCE_ROWS = tuple(BOOK_ROWS) + tuple(MIGRATED_BOOK_ROWS)
VERSION_ROWS, BOOK_VERSION_MAP = textbook_versions.build_version_rows(BOOK_SOURCE_ROWS)


def _stage_coverage(rows: tuple[tuple, ...]) -> dict[int, set[str]]:
    codes = {name: code for code, name in national_catalog.STAGE_NAMES.items()}
    stages = {int(row[0]): codes.get(str(row[4]), "") for row in GRADE_ROWS}
    covered: dict[int, set[str]] = {}
    for row in rows:
        stage = stages.get(int(row[6]))
        if stage:
            covered.setdefault(int(row[7]), set()).add(stage)
    return covered


_BASE_VERSION_ROWS = VERSION_ROWS + CATALOG_VERSION_ROWS
_BASE_BOOK_ROWS = (
    tuple((*row, *BOOK_VERSION_MAP[int(row[0])]) for row in BOOK_SOURCE_ROWS)
    + CATALOG_BOOK_ROWS
)
# 全国版本目录只补「已有版本没覆盖到的学段」，每版每学段挂一册真实首册当锚点。
NATIONAL_VERSION_ROWS, NATIONAL_BOOK_ROWS = national_catalog.build(
    {(int(row[5]), str(row[1])): int(row[0]) for row in _BASE_VERSION_ROWS},
    _stage_coverage(_BASE_BOOK_ROWS),
)
ALL_VERSION_ROWS = _BASE_VERSION_ROWS + NATIONAL_VERSION_ROWS
ALL_BOOK_ROWS = _BASE_BOOK_ROWS + NATIONAL_BOOK_ROWS

EXPECTED_COUNTS: dict[str, int] = {
    "dict_subjects": 15,
    "dict_grades": 12,
    "dict_question_types": 3,
    "dict_difficulties": 5,
    "dict_question_qualities": 3,
    "dict_exam_types": 8,
    "dict_subject_thoughts": 34,
    "dict_solution_methods": 85,
    "dict_core_competencies": 64,
    "dim_textbook_versions": len(ALL_VERSION_ROWS),
    "dim_textbooks": len(ALL_BOOK_ROWS),
    "dim_textbook_chapters": 3519,
    "dim_knowledge_points": 11388,
    "dim_exam_directions": 567,
    "knowledge_exam_map": 200,
    "chapter_knowledge_map": 74,
    "dim_regions": len(REGION_ROWS),
    "dim_schools": 347,
    "exams": 1,
    "exam_school_map": 2,
}

_TEACHING_DICTIONARIES = (
    ("dict_subject_thoughts", SUBJECT_THOUGHT_ROWS),
    ("dict_solution_methods", SOLUTION_METHOD_ROWS),
    ("dict_core_competencies", CORE_COMPETENCY_ROWS),
)


def _statements() -> tuple[tuple[str, tuple[tuple[Any, ...], ...]], ...]:
    subjects = tuple((row[0], row[1], row[2], row[0]) for row in SUBJECT_ROWS)
    qualities = tuple((row[0], row[1], row[2], row[0]) for row in QUALITY_SEED_ROWS)
    textbooks = ALL_BOOK_ROWS
    chapters = tuple(CHAPTER_ROWS) + tuple(MIGRATED_CHAPTER_ROWS)
    knowledge = tuple(KNOWLEDGE_POINT_ROWS) + tuple(MATH_REQUIRED1_KNOWLEDGE_ROWS)
    schools = tuple((*row, regions.match_region_id(row[4])) for row in SCHOOL_ROWS)
    directions = tuple(EXAM_DIRECTION_ROWS) + tuple(MATH_REQUIRED1_EXAM_ROWS)
    statements: list[tuple[str, tuple[tuple[Any, ...], ...]]] = [
        (
            "INSERT INTO dict_subjects (id, code, name, sort_order) "
            "VALUES (?, ?, ?, ?)",
            subjects,
        ),
        (
            "INSERT INTO dict_grades (id, code, name, sort_order, stage) "
            "VALUES (?, ?, ?, ?, ?)",
            tuple(GRADE_ROWS),
        ),
        (
            "INSERT INTO dict_question_types (id, code, name, sort_order) "
            "VALUES (?, ?, ?, ?)",
            tuple(QUESTION_TYPE_ROWS),
        ),
        (
            "INSERT INTO dict_difficulties "
            "(id, code, name, sort_order, level, description, ai_prompt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            tuple(DIFFICULTY_SEED_ROWS),
        ),
        (
            "INSERT INTO dict_question_qualities (id, code, name, sort_order) "
            "VALUES (?, ?, ?, ?)",
            qualities,
        ),
        (
            "INSERT INTO dict_exam_types (id, name, code, sort_order) "
            "VALUES (?, ?, ?, ?)",
            tuple(EXAM_TYPE_ROWS),
        ),
    ]
    for table, rows in _TEACHING_DICTIONARIES:
        statements.append(
            (
                f"INSERT INTO {table} "
                "(id, code, name, sort_order, subject_id, stage) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                tuple(rows),
            )
        )
    statements.extend(
        (
            (
                "INSERT INTO dim_regions "
                "(id, name, code, level, parent_id, sort_order) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                tuple(REGION_ROWS),
            ),
            (
                "INSERT INTO dim_textbook_versions "
                "(id, name, code, sort_order, publisher, subject_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ALL_VERSION_ROWS,
            ),
            (
                "INSERT INTO dim_textbooks "
                "(id, name, code, sort_order, publisher, subject_id, grade_id, "
                "version_id, volume_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                textbooks,
            ),
            (
                "INSERT INTO dim_textbook_chapters "
                "(id, name, code, sort_order, textbook_id, parent_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                chapters,
            ),
            (
                "INSERT INTO dim_knowledge_points "
                "(id, code, name, sort_order, subject_id, parent_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                knowledge,
            ),
            (
                "INSERT INTO dim_exam_directions "
                "(id, name, code, sort_order, subject_id, chapter_id, description) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                directions,
            ),
            (
                "INSERT INTO knowledge_exam_map "
                "(knowledge_point_id, exam_direction_id) VALUES (?, ?)",
                tuple(MATH_REQUIRED1_KNOWLEDGE_EXAM_ROWS),
            ),
            (
                "INSERT INTO chapter_knowledge_map "
                "(chapter_id, knowledge_point_id) VALUES (?, ?)",
                tuple(MATH_REQUIRED1_CHAPTER_KNOWLEDGE_ROWS),
            ),
            (
                "INSERT INTO dim_schools "
                "(id, name, short_name, code, region, textbook_id, region_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                schools,
            ),
            (
                "INSERT INTO exams "
                "(id, year, exam_org_name, school_id, month, exam_type_id, "
                "mock_round, grade_id, semester, subject_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(EXAM_ROWS),
            ),
            (
                "INSERT INTO exam_school_map (exam_id, school_id) VALUES (?, ?)",
                tuple(EXAM_SCHOOL_ROWS),
            ),
        )
    )
    return tuple(statements)


def apply_seeds(conn: sqlite3.Connection) -> dict[str, int]:
    for sql, rows in _statements():
        conn.executemany(sql, rows)
    counts = {
        table: int(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
        for table in EXPECTED_COUNTS
    }
    mismatched = {
        table: (counts[table], expected)
        for table, expected in EXPECTED_COUNTS.items()
        if counts[table] != expected
    }
    if mismatched:
        raise ValueError(f"种子计数不符：{mismatched}")
    return counts

"""字典 DAO：学科 / 年级 / 题型 / 难度 / 质量五张 dict 表，每次只读一张表。

录入表单只交名字或编码，落库前必须在这里解析成整数外键；解析不了的词
不回写数据库，由服务层换成老师看得懂的错误。考向与知识点按编码批量取 id，
同样只走单表 ``IN`` 查询。
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from app.bank_engine import dao_base
from app.bank_engine.models import (
    Dictionaries,
    Difficulty,
    ExamLevel,
    ExamOrg,
    ExamType,
    Grade,
    Quality,
    QuestionType,
    Subject,
)

# 录题工作台的四种题型映射到题库字典的三类：单选 / 多选都落「选择题」。
EDITOR_TYPE_CODES: dict[str, str] = {
    "single_choice": "choice",
    "multiple_choice": "choice",
    "choice": "choice",
    "fill_blank": "fill_blank",
    "solution": "solution",
    "proof": "solution",
    "unknown": "choice",
}


def load_dictionaries(conn: sqlite3.Connection) -> Dictionaries:
    subjects = tuple(
        Subject(int(row["id"]), str(row["name"]), str(row["code"]), int(row["sort_order"]))
        for row in conn.execute(
            "SELECT id, name, code, sort_order FROM dict_subjects ORDER BY sort_order, id"
        )
    )
    grades = tuple(
        Grade(
            int(row["id"]),
            str(row["name"]),
            str(row["code"]),
            int(row["sort_order"]),
            None if row["stage"] is None else str(row["stage"]),
        )
        for row in conn.execute(
            "SELECT id, name, code, sort_order, stage FROM dict_grades "
            "ORDER BY sort_order, id"
        )
    )
    types = tuple(
        QuestionType(int(row["id"]), str(row["name"]), str(row["code"]), int(row["sort_order"]))
        for row in conn.execute(
            "SELECT id, name, code, sort_order FROM dict_question_types "
            "ORDER BY sort_order, id"
        )
    )
    difficulties = tuple(
        Difficulty(
            int(row["id"]),
            str(row["name"]),
            str(row["code"]),
            int(row["sort_order"]),
            int(row["level"]),
            None if row["description"] is None else str(row["description"]),
        )
        for row in conn.execute(
            "SELECT id, name, code, sort_order, level, description FROM dict_difficulties "
            "ORDER BY sort_order, id"
        )
    )
    qualities = tuple(
        Quality(int(row["id"]), str(row["name"]), str(row["code"]), int(row["sort_order"]))
        for row in conn.execute(
            "SELECT id, name, code, sort_order FROM dict_question_qualities "
            "ORDER BY sort_order, id"
        )
    )
    exam_types = tuple(
        ExamType(int(row["id"]), str(row["name"]), str(row["code"]), int(row["sort_order"]))
        for row in conn.execute(
            "SELECT id, name, code, sort_order FROM dict_exam_types ORDER BY sort_order, id"
        )
    )
    exam_levels = tuple(
        ExamLevel(int(row["id"]), str(row["name"]), str(row["code"]), int(row["sort_order"]))
        for row in conn.execute(
            "SELECT id, name, code, sort_order FROM dict_exam_levels ORDER BY sort_order, id"
        )
    )
    exam_orgs = tuple(
        ExamOrg(
            int(row["id"]),
            str(row["name"]),
            str(row["org_type"]),
            None if row["school_id"] is None else int(row["school_id"]),
        )
        for row in conn.execute(
            "SELECT id, name, org_type, school_id FROM dict_exam_orgs ORDER BY id"
        )
    )
    return Dictionaries(
        subjects, grades, types, difficulties, qualities,
        exam_types, exam_levels, exam_orgs,
    )


def _find(items: Iterable, value: str, attr: str):
    for item in items:
        if getattr(item, attr) == value:
            return item
    return None


def resolve_subject(
    dictionaries: Dictionaries, *, subject_id: int | None, name: str, code: str
) -> Subject | None:
    if subject_id is not None:
        found = next((item for item in dictionaries.subjects if item.id == subject_id), None)
        if found is not None:
            return found
    found = _find(dictionaries.subjects, name, "name") if name else None
    if found is None and code:
        found = _find(dictionaries.subjects, code, "code")
    return found


def resolve_grade(
    dictionaries: Dictionaries, *, grade_id: int | None, name: str, code: str
) -> Grade | None:
    if grade_id is not None:
        found = next((item for item in dictionaries.grades if item.id == grade_id), None)
        if found is not None:
            return found
    found = _find(dictionaries.grades, name, "name") if name else None
    if found is None and code:
        found = _find(dictionaries.grades, code, "code")
    return found


def resolve_question_type(dictionaries: Dictionaries, value: str) -> QuestionType | None:
    code = EDITOR_TYPE_CODES.get(value, value)
    return _find(dictionaries.question_types, code, "code")


def resolve_difficulty(dictionaries: Dictionaries, value: str) -> Difficulty | None:
    return _find(dictionaries.difficulties, str(value or "L1"), "code")


def resolve_quality(dictionaries: Dictionaries, value: str) -> Quality | None:
    return _find(dictionaries.qualities, str(value or "NORMAL"), "code")


def direction_ids_by_codes(
    conn: sqlite3.Connection, codes: Iterable[str]
) -> tuple[tuple[int, ...], tuple[str, ...]]:
    wanted = list(dict.fromkeys(code for code in codes if code))
    if not wanted:
        return (), ()
    found: dict[str, int] = {}
    for part in dao_base.chunks(wanted):
        clause, params = dao_base.in_sql("code", part)
        for row in conn.execute(
            "SELECT code, id FROM dim_exam_directions WHERE " + clause, params
        ):
            found[str(row["code"])] = int(row["id"])
    missing = tuple(code for code in wanted if code not in found)
    return tuple(found[code] for code in wanted if code in found), missing


def knowledge_ids_by_codes(
    conn: sqlite3.Connection, codes: Iterable[str]
) -> tuple[tuple[int, ...], tuple[str, ...]]:
    wanted = list(dict.fromkeys(code for code in codes if code))
    if not wanted:
        return (), ()
    found: dict[str, int] = {}
    for part in dao_base.chunks(wanted):
        clause, params = dao_base.in_sql("code", part)
        for row in conn.execute(
            "SELECT code, id FROM dim_knowledge_points WHERE " + clause, params
        ):
            found[str(row["code"])] = int(row["id"])
    missing = tuple(code for code in wanted if code not in found)
    return tuple(found[code] for code in wanted if code in found), missing


__all__ = [
    "EDITOR_TYPE_CODES",
    "direction_ids_by_codes",
    "knowledge_ids_by_codes",
    "load_dictionaries",
    "resolve_difficulty",
    "resolve_grade",
    "resolve_quality",
    "resolve_question_type",
    "resolve_subject",
]

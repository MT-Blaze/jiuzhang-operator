"""题目 DAO：按考向 / 知识点分页与整题装配。

每次只让一张表当驱动表：先取关系表里的题目 id，再按 id 分片回 ``questions``，
其余从表各自按 ``question_id`` 单表取回，全部拼装留在 Python 层。
"""

from __future__ import annotations

import sqlite3
from typing import Iterable

from app.bank_engine import dao_base
from app.bank_engine.models import (
    QuestionAnswer,
    QuestionExam,
    QuestionImage,
    QuestionOption,
    QuestionPage,
    QuestionRecord,
    QuestionSolution,
    QuestionSummary,
    QuestionSupplement,
)

QUESTION_COLUMNS = (
    "id, stem, subject_id, question_type_id, difficulty_id, quality_id, "
    "deleted_at, created_at, updated_at"
)


def _optional_int(value: object) -> int | None:
    return None if value is None else int(value)


def _summary(row: sqlite3.Row, codes: dict[str, dict[int, str]]) -> QuestionSummary:
    return QuestionSummary(
        id=str(row["id"]),
        stem=str(row["stem"]),
        subject_id=int(row["subject_id"]),
        question_type=codes["question_types"].get(int(row["question_type_id"]), ""),
        difficulty=codes["difficulties"].get(int(row["difficulty_id"]), ""),
        quality=codes["qualities"].get(int(row["quality_id"]), ""),
        deleted_at=None if row["deleted_at"] is None else str(row["deleted_at"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _count(conn: sqlite3.Connection, table: str, column: str, value: int) -> int:
    sql = "SELECT COUNT(*) FROM " + table + " WHERE " + column + " = ?"
    return int(conn.execute(sql, (value,)).fetchone()[0])


def _driver_ids(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    value: int,
    limit: int,
    offset: int,
) -> list[str]:
    sql = (
        "SELECT question_id FROM " + table + " WHERE " + column + " = ? "
        "ORDER BY question_id LIMIT ? OFFSET ?"
    )
    return [str(row[0]) for row in conn.execute(sql, (value, limit, offset))]


def _page(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    value: int,
    limit: int,
    offset: int,
) -> QuestionPage:
    total = _count(conn, table, column, value)
    ids = _driver_ids(conn, table, column, value, limit, offset)
    if not ids:
        return QuestionPage((), total, limit, offset)
    rows = dao_base.load_rows_by_ids(
        conn, "SELECT " + QUESTION_COLUMNS + " FROM questions", ids
    )
    codes = dao_base.dictionary_codes(conn)
    items = tuple(_summary(rows[qid], codes) for qid in ids if qid in rows)
    return QuestionPage(items, total, limit, offset)


def questions_by_exam_direction(
    conn: sqlite3.Connection,
    exam_direction_id: int,
    limit: int = 20,
    offset: int = 0,
) -> QuestionPage:
    return _page(conn, "question_exam_map", "exam_direction_id", exam_direction_id, limit, offset)


def questions_by_knowledge_point(
    conn: sqlite3.Connection,
    knowledge_point_id: int,
    limit: int = 20,
    offset: int = 0,
) -> QuestionPage:
    return _page(
        conn, "question_knowledge_map", "knowledge_point_id", knowledge_point_id, limit, offset
    )


def _children(conn: sqlite3.Connection, table: str, question_id: str, order: str) -> list[sqlite3.Row]:
    sql = "SELECT * FROM " + table + " WHERE question_id = ? ORDER BY " + order
    return list(conn.execute(sql, (question_id,)))


def _options(conn: sqlite3.Connection, question_id: str) -> tuple[QuestionOption, ...]:
    rows = conn.execute(
        "SELECT id, option_label, content, is_correct FROM question_options "
        "WHERE question_id = ? ORDER BY option_label",
        (question_id,),
    )
    return tuple(
        QuestionOption(
            id=int(row["id"]),
            label=str(row["option_label"]),
            content=str(row["content"]),
            is_correct=bool(row["is_correct"]),
        )
        for row in rows
    )


def _answers(conn: sqlite3.Connection, question_id: str) -> tuple[QuestionAnswer, ...]:
    rows = _children(conn, "question_answers", question_id, "sort_order, id")
    return tuple(
        QuestionAnswer(str(row["answer_content"]), bool(row["is_primary"]), int(row["sort_order"]))
        for row in rows
    )


def _solutions(conn: sqlite3.Connection, question_id: str) -> tuple[QuestionSolution, ...]:
    rows = _children(conn, "question_solutions", question_id, "sort_order, id")
    return tuple(
        QuestionSolution(str(row["content"]), bool(row["is_primary"]), int(row["sort_order"]))
        for row in rows
    )


def _remarks(conn: sqlite3.Connection, question_id: str) -> tuple[str, ...]:
    row = conn.execute(
        "SELECT remark FROM question_remarks WHERE question_id = ?", (question_id,)
    ).fetchone()
    return () if row is None else (str(row["remark"]),)


def _supplements(conn: sqlite3.Connection, question_id: str) -> tuple[QuestionSupplement, ...]:
    rows = _children(conn, "question_supplements", question_id, "namespace, sort_order, id")
    return tuple(
        QuestionSupplement(
            str(row["namespace"]),
            str(row["field_key"]),
            str(row["field_value"]),
            int(row["sort_order"]),
        )
        for row in rows
    )


def _images(conn: sqlite3.Connection, question_id: str) -> tuple[QuestionImage, ...]:
    rows = _children(conn, "question_images", question_id, "belongs_to, sort_order, id")
    return tuple(
        QuestionImage(
            str(row["belongs_to"]),
            str(row["path"]),
            None if row["alt"] is None else str(row["alt"]),
            int(row["sort_order"]),
            _optional_int(row["option_id"]),
            None if row["tikz_code"] is None else str(row["tikz_code"]),
        )
        for row in rows
    )


def _schools_by_exam(
    conn: sqlite3.Connection, exam_ids: list[int]
) -> dict[int, tuple[tuple[int, str], ...]]:
    links: dict[int, list[int]] = {}
    for part in dao_base.chunks(exam_ids):
        clause, params = dao_base.in_sql("exam_id", part)
        for row in conn.execute(
            "SELECT exam_id, school_id FROM exam_school_map WHERE " + clause
            + " ORDER BY exam_id, school_id",
            params,
        ):
            links.setdefault(int(row["exam_id"]), []).append(int(row["school_id"]))
    school_ids = [school_id for values in links.values() for school_id in values]
    schools = dao_base.load_rows_by_ids(conn, "SELECT id, name FROM dim_schools", school_ids)
    return {
        exam_id: tuple(
            (school_id, str(schools[school_id]["name"]))
            for school_id in school_ids_of_exam
            if school_id in schools
        )
        for exam_id, school_ids_of_exam in links.items()
    }


def _exams(conn: sqlite3.Connection, question_id: str) -> tuple[QuestionExam, ...]:
    maps = conn.execute(
        "SELECT exam_id, question_no, score FROM question_exams "
        "WHERE question_id = ? ORDER BY exam_id",
        (question_id,),
    ).fetchall()
    if not maps:
        return ()
    exam_ids = [int(row["exam_id"]) for row in maps]
    rows = dao_base.load_rows_by_ids(
        conn,
        "SELECT id, code, year, month, subject_id, grade_id, exam_type_id, exam_subject "
        "FROM exams",
        exam_ids,
    )
    type_ids = [int(row["exam_type_id"]) for row in rows.values()]
    types = dao_base.load_rows_by_ids(
        conn, "SELECT id, name FROM dict_exam_types", type_ids
    )
    schools = _schools_by_exam(conn, exam_ids)
    items: list[QuestionExam] = []
    for row in maps:
        exam = rows.get(int(row["exam_id"]))
        if exam is None:
            continue
        exam_schools = schools.get(int(exam["id"]), ())
        items.append(
            QuestionExam(
                id=int(exam["id"]),
                code=str(exam["code"]),
                year=int(exam["year"]),
                month=None if exam["month"] is None else int(exam["month"]),
                subject_id=int(exam["subject_id"]),
                grade_id=int(exam["grade_id"]),
                exam_type=str(types[int(exam["exam_type_id"])]["name"])
                if int(exam["exam_type_id"]) in types else "",
                exam_subject=str(exam["exam_subject"]),
                question_no=None if row["question_no"] is None else str(row["question_no"]),
                score=float(row["score"]),
                school_ids=tuple(school_id for school_id, _ in exam_schools),
                school_names=tuple(name for _, name in exam_schools),
            )
        )
    return tuple(items)


def _direction_ids(conn: sqlite3.Connection, question_id: str) -> list[int]:
    rows = conn.execute(
        "SELECT exam_direction_id FROM question_exam_map "
        "WHERE question_id = ? ORDER BY exam_direction_id",
        (question_id,),
    )
    return [int(row[0]) for row in rows]


def _point_ids(conn: sqlite3.Connection, question_id: str) -> list[int]:
    rows = conn.execute(
        "SELECT knowledge_point_id FROM question_knowledge_map "
        "WHERE question_id = ? ORDER BY knowledge_point_id",
        (question_id,),
    )
    return [int(row[0]) for row in rows]


def get_question(conn: sqlite3.Connection, question_id: str) -> QuestionRecord | None:
    row = conn.execute(
        "SELECT " + QUESTION_COLUMNS + " FROM questions WHERE id = ?", (question_id,)
    ).fetchone()
    if row is None:
        return None
    codes = dao_base.dictionary_codes(conn)
    directions = dao_base.load_exam_directions(conn, _direction_ids(conn, question_id))
    points = dao_base.load_knowledge_points(conn, _point_ids(conn, question_id))
    summary = _summary(row, codes)
    return QuestionRecord(
        id=summary.id,
        stem=summary.stem,
        subject_id=summary.subject_id,
        question_type=summary.question_type,
        difficulty=summary.difficulty,
        quality=summary.quality,
        deleted_at=summary.deleted_at,
        created_at=summary.created_at,
        updated_at=summary.updated_at,
        options=_options(conn, question_id),
        answers=_answers(conn, question_id),
        solutions=_solutions(conn, question_id),
        remarks=_remarks(conn, question_id),
        supplements=_supplements(conn, question_id),
        images=_images(conn, question_id),
        exams=_exams(conn, question_id),
        exam_directions=tuple(
            directions[key] for key in sorted(directions)
        ),
        knowledge_points=tuple(points[key] for key in sorted(points)),
    )


def direction_question_counts(
    conn: sqlite3.Connection, direction_ids: Iterable[int]
) -> dict[int, int]:
    ids = list(dict.fromkeys(direction_ids))
    counts: dict[int, int] = {}
    for part in dao_base.chunks(ids):
        clause, params = dao_base.in_sql("exam_direction_id", part)
        sql = "SELECT exam_direction_id, COUNT(*) FROM question_exam_map WHERE " + clause
        rows = conn.execute(sql, params)
        counts.update({int(row[0]): int(row[1]) for row in rows if row[0] is not None})
    return counts


def point_question_counts(
    conn: sqlite3.Connection, point_ids: Iterable[int]
) -> dict[int, int]:
    ids = list(dict.fromkeys(point_ids))
    counts: dict[int, int] = {}
    for part in dao_base.chunks(ids):
        clause, params = dao_base.in_sql("knowledge_point_id", part)
        sql = "SELECT knowledge_point_id, COUNT(*) FROM question_knowledge_map WHERE " + clause
        rows = conn.execute(sql, params)
        counts.update({int(row[0]): int(row[1]) for row in rows if row[0] is not None})
    return counts


__all__ = [
    "direction_question_counts",
    "get_question",
    "point_question_counts",
    "questions_by_exam_direction",
    "questions_by_knowledge_point",
]

"""维度 DAO：考向、知识点树、教材与章节。每次只读一张表，树形结构在 Python 层组装。"""

from __future__ import annotations

import sqlite3
from typing import Any

from app.bank_engine import dao_base
from app.bank_engine.dao_questions import direction_question_counts, point_question_counts
from app.bank_engine.models import (
    Chapter,
    ExamDirection,
    KnowledgeNode,
    KnowledgePoint,
    Region,
    Textbook,
    TextbookVersion,
)

DIRECTION_COLUMNS = "id, name, code, sort_order, subject_id, chapter_id, description"
POINT_COLUMNS = "id, name, code, sort_order, subject_id, parent_id"
REGION_COLUMNS = "id, name, code, level, parent_id, sort_order"
TEXTBOOK_COLUMNS = (
    "id, name, code, sort_order, publisher, subject_id, grade_id, version_id, volume_name"
)
VERSION_COLUMNS = "id, name, code, sort_order, publisher, subject_id"
CHAPTER_COLUMNS = "id, name, code, sort_order, textbook_id, parent_id"


def _where(clauses: list[str], params: list[Any]) -> str:
    return "" if not clauses else " WHERE " + " AND ".join(clauses)


def _direction(row: sqlite3.Row, counts: dict[int, int]) -> ExamDirection:
    direction_id = int(row["id"])
    return ExamDirection(
        id=direction_id,
        name=str(row["name"]),
        code=str(row["code"]),
        sort_order=int(row["sort_order"]),
        subject_id=int(row["subject_id"]),
        chapter_id=None if row["chapter_id"] is None else int(row["chapter_id"]),
        description=None if row["description"] is None else str(row["description"]),
        question_count=counts.get(direction_id, 0),
    )


def _point(row: sqlite3.Row, counts: dict[int, int]) -> KnowledgePoint:
    point_id = int(row["id"])
    return KnowledgePoint(
        id=point_id,
        name=str(row["name"]),
        code=str(row["code"]),
        sort_order=int(row["sort_order"]),
        subject_id=int(row["subject_id"]),
        parent_id=None if row["parent_id"] is None else int(row["parent_id"]),
        question_count=counts.get(point_id, 0),
    )


def count_exam_directions(
    conn: sqlite3.Connection,
    *,
    subject_id: int | None = None,
    chapter_id: int | None = None,
    keyword: str | None = None,
) -> int:
    clauses: list[str] = []
    params: list[Any] = []
    if subject_id is not None:
        clauses.append("subject_id = ?")
        params.append(subject_id)
    if chapter_id is not None:
        clauses.append("chapter_id = ?")
        params.append(chapter_id)
    if keyword:
        clauses.append("name LIKE ?")
        params.append("%" + keyword + "%")
    sql = "SELECT COUNT(*) FROM dim_exam_directions" + _where(clauses, params)
    return int(conn.execute(sql, params).fetchone()[0])


def list_exam_directions(
    conn: sqlite3.Connection,
    *,
    subject_id: int | None = None,
    chapter_id: int | None = None,
    keyword: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[ExamDirection, ...]:
    clauses: list[str] = []
    params: list[Any] = []
    if subject_id is not None:
        clauses.append("subject_id = ?")
        params.append(subject_id)
    if chapter_id is not None:
        clauses.append("chapter_id = ?")
        params.append(chapter_id)
    if keyword:
        clauses.append("name LIKE ?")
        params.append("%" + keyword + "%")
    sql = (
        "SELECT " + DIRECTION_COLUMNS + " FROM dim_exam_directions"
        + _where(clauses, params)
        + " ORDER BY subject_id, sort_order, id LIMIT ? OFFSET ?"
    )
    rows = conn.execute(sql, params + [limit, offset]).fetchall()
    counts = direction_question_counts(conn, [int(row["id"]) for row in rows])
    return tuple(_direction(row, counts) for row in rows)


def get_exam_direction(
    conn: sqlite3.Connection, direction_id: int
) -> ExamDirection | None:
    row = conn.execute(
        "SELECT " + DIRECTION_COLUMNS + " FROM dim_exam_directions WHERE id = ?",
        (direction_id,),
    ).fetchone()
    if row is None:
        return None
    counts = direction_question_counts(conn, [direction_id])
    return _direction(row, counts)


def count_knowledge_points(
    conn: sqlite3.Connection,
    *,
    subject_id: int | None = None,
    parent_id: int | None = None,
    roots_only: bool = False,
    keyword: str | None = None,
) -> int:
    clauses, params = _point_filters(subject_id, parent_id, roots_only, keyword)
    sql = "SELECT COUNT(*) FROM dim_knowledge_points" + _where(clauses, params)
    return int(conn.execute(sql, params).fetchone()[0])


def _point_filters(
    subject_id: int | None,
    parent_id: int | None,
    roots_only: bool,
    keyword: str | None,
) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if subject_id is not None:
        clauses.append("subject_id = ?")
        params.append(subject_id)
    if roots_only:
        clauses.append("parent_id IS NULL")
    elif parent_id is not None:
        clauses.append("parent_id = ?")
        params.append(parent_id)
    if keyword:
        clauses.append("name LIKE ?")
        params.append("%" + keyword + "%")
    return clauses, params


def list_knowledge_points(
    conn: sqlite3.Connection,
    *,
    subject_id: int | None = None,
    parent_id: int | None = None,
    roots_only: bool = False,
    keyword: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[KnowledgePoint, ...]:
    clauses, params = _point_filters(subject_id, parent_id, roots_only, keyword)
    sql = (
        "SELECT " + POINT_COLUMNS + " FROM dim_knowledge_points"
        + _where(clauses, params)
        + " ORDER BY subject_id, sort_order, id LIMIT ? OFFSET ?"
    )
    rows = conn.execute(sql, params + [limit, offset]).fetchall()
    counts = point_question_counts(conn, [int(row["id"]) for row in rows])
    return tuple(_point(row, counts) for row in rows)


def get_knowledge_point(
    conn: sqlite3.Connection, point_id: int
) -> KnowledgePoint | None:
    row = conn.execute(
        "SELECT " + POINT_COLUMNS + " FROM dim_knowledge_points WHERE id = ?",
        (point_id,),
    ).fetchone()
    if row is None:
        return None
    counts = point_question_counts(conn, [point_id])
    return _point(row, counts)


def knowledge_tree(
    conn: sqlite3.Connection,
    *,
    subject_id: int,
) -> tuple[KnowledgeNode, ...]:
    clauses = ["subject_id = ?"]
    params: list[Any] = [subject_id]
    sql = (
        "SELECT " + POINT_COLUMNS + " FROM dim_knowledge_points WHERE "
        + " AND ".join(clauses)
        + " ORDER BY sort_order, id"
    )
    rows = conn.execute(sql, params).fetchall()
    counts = point_question_counts(conn, [int(row["id"]) for row in rows])
    children: dict[int | None, list[KnowledgePoint]] = {}
    for row in rows:
        point = _point(row, counts)
        children.setdefault(point.parent_id, []).append(point)

    def build(point: KnowledgePoint) -> KnowledgeNode:
        return KnowledgeNode(point, tuple(build(child) for child in children.get(point.id, ())))

    return tuple(build(root) for root in children.get(None, ()))


STAGE_ORDER = ("小学", "初中", "高中")


def version_stages(conn: sqlite3.Connection) -> dict[int, tuple[str, ...]]:
    """版本 → 学段集合：由该版本下教材册的年级反推，分步查三张表后在应用层组装。"""
    grade_stage = {
        int(row["id"]): str(row["stage"])
        for row in conn.execute("SELECT id, stage FROM dict_grades WHERE stage IS NOT NULL")
    }
    buckets: dict[int, list[str]] = {}
    for row in conn.execute(
        "SELECT version_id, grade_id FROM dim_textbooks WHERE version_id IS NOT NULL"
    ):
        stage = grade_stage.get(int(row["grade_id"])) if row["grade_id"] is not None else None
        if stage is None:
            continue
        filled = buckets.setdefault(int(row["version_id"]), [])
        if stage not in filled:
            filled.append(stage)
    return {
        version_id: tuple(sorted(stages, key=STAGE_ORDER.index))
        for version_id, stages in buckets.items()
    }


def list_textbook_versions(
    conn: sqlite3.Connection,
    *,
    subject_id: int | None = None,
    stage: str | None = None,
) -> tuple[TextbookVersion, ...]:
    """版本下拉框的唯一数据源：只出纯净版本名，绝不混入册次。

    ``stage`` 按教材册所属年级的学段收口：选高中时不把小学/初中版本混进来。
    """
    clauses: list[str] = []
    params: list[Any] = []
    if subject_id is not None:
        clauses.append("subject_id = ?")
        params.append(subject_id)
    sql = (
        "SELECT " + VERSION_COLUMNS + " FROM dim_textbook_versions"
        + _where(clauses, params)
        + " ORDER BY subject_id, sort_order, id"
    )
    stages_by_version = version_stages(conn)
    items: list[TextbookVersion] = []
    for row in conn.execute(sql, params):
        stages = stages_by_version.get(int(row["id"]), ())
        if stage and stage not in stages:
            continue
        items.append(
            TextbookVersion(
                id=int(row["id"]),
                name=str(row["name"]),
                code=str(row["code"]),
                sort_order=int(row["sort_order"]),
                publisher=None if row["publisher"] is None else str(row["publisher"]),
                subject_id=int(row["subject_id"]),
                stages=stages,
            )
        )
    return tuple(items)


def list_textbooks(
    conn: sqlite3.Connection,
    *,
    subject_id: int | None = None,
    grade_id: int | None = None,
    version_id: int | None = None,
) -> tuple[Textbook, ...]:
    clauses: list[str] = []
    params: list[Any] = []
    if subject_id is not None:
        clauses.append("subject_id = ?")
        params.append(subject_id)
    if grade_id is not None:
        clauses.append("grade_id = ?")
        params.append(grade_id)
    if version_id is not None:
        clauses.append("version_id = ?")
        params.append(version_id)
    sql = (
        "SELECT " + TEXTBOOK_COLUMNS + " FROM dim_textbooks"
        + _where(clauses, params)
        + " ORDER BY subject_id, grade_id, sort_order, id"
    )
    return tuple(
        Textbook(
            id=int(row["id"]),
            name=str(row["name"]),
            code=str(row["code"]),
            sort_order=int(row["sort_order"]),
            publisher=None if row["publisher"] is None else str(row["publisher"]),
            subject_id=int(row["subject_id"]),
            grade_id=None if row["grade_id"] is None else int(row["grade_id"]),
            version_id=None if row["version_id"] is None else int(row["version_id"]),
            volume_name=None if row["volume_name"] is None else str(row["volume_name"]),
        )
        for row in conn.execute(sql, params)
    )


def list_regions(
    conn: sqlite3.Connection,
    *,
    keyword: str | None = None,
    level: int | None = None,
) -> tuple[Region, ...]:
    """行政区划字典：省 / 市两级，做参考地区的模糊搜索。"""
    clauses: list[str] = []
    params: list[Any] = []
    if keyword:
        clauses.append("name LIKE ?")
        params.append("%" + keyword + "%")
    if level is not None:
        clauses.append("level = ?")
        params.append(level)
    sql = (
        "SELECT " + REGION_COLUMNS + " FROM dim_regions" + _where(clauses, params)
        + " ORDER BY sort_order, id"
    )
    return tuple(
        Region(
            id=int(row["id"]),
            name=str(row["name"]),
            code=str(row["code"]),
            level=int(row["level"]),
            parent_id=None if row["parent_id"] is None else int(row["parent_id"]),
            sort_order=int(row["sort_order"]),
        )
        for row in conn.execute(sql, params)
    )


def list_chapters(
    conn: sqlite3.Connection,
    textbook_id: int,
    *,
    parent_id: int | None = None,
    roots_only: bool = True,
) -> tuple[Chapter, ...]:
    clauses = ["textbook_id = ?"]
    params: list[Any] = [textbook_id]
    if roots_only:
        clauses.append("parent_id IS NULL")
    elif parent_id is not None:
        clauses.append("parent_id = ?")
        params.append(parent_id)
    sql = (
        "SELECT " + CHAPTER_COLUMNS + " FROM dim_textbook_chapters WHERE "
        + " AND ".join(clauses)
        + " ORDER BY sort_order, id"
    )
    return tuple(
        Chapter(
            id=int(row["id"]),
            name=str(row["name"]),
            code=str(row["code"]),
            sort_order=int(row["sort_order"]),
            textbook_id=int(row["textbook_id"]),
            parent_id=None if row["parent_id"] is None else int(row["parent_id"]),
        )
        for row in conn.execute(sql, params)
    )


__all__ = [
    "count_exam_directions",
    "count_knowledge_points",
    "get_exam_direction",
    "get_knowledge_point",
    "knowledge_tree",
    "list_chapters",
    "list_exam_directions",
    "list_knowledge_points",
    "list_regions",
    "list_textbook_versions",
    "list_textbooks",
    "version_stages",
]

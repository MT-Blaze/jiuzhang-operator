"""题库引擎 v2 的微内核服务层：短连接、参数校验与 Dataclass 出口。

对外只暴露 Python 对象，不序列化 JSON；数据库读写全部经 dao 模块的单表查询。
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app.bank_engine import (
    builder,
    dao_base,
    dao_dictionary,
    dao_dimensions,
    dao_questions,
    entry,
    seeding,
    writer,
)
from app.bank_engine.models import (
    Chapter,
    CreatedQuestion,
    Dictionaries,
    EngineStatus,
    ExamDirection,
    KnowledgeNode,
    KnowledgePoint,
    QuestionPage,
    QuestionRecord,
    Textbook,
)

DEFAULT_LIMIT = 20
MAX_LIMIT = 200


def _bounds(limit: int, offset: int) -> tuple[int, int]:
    if limit < 1 or limit > MAX_LIMIT:
        raise ValueError(f"limit 必须在 1..{MAX_LIMIT} 之间")
    if offset < 0:
        raise ValueError("offset 不能为负数")
    return limit, offset


@contextmanager
def session(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = dao_base.connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def ensure_ready(db_path: Path | None = None) -> EngineStatus:
    with session(db_path) as conn:
        counts = builder.validate_connection(conn, require_seeds=False)
        return _status(conn, counts)


def _status(conn: sqlite3.Connection, counts: dict[str, int]) -> EngineStatus:
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0])
    violations = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    tables = int(conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchone()[0])
    return EngineStatus(
        db_path=str(conn.execute("PRAGMA database_list").fetchone()[2]),
        schema_version=version,
        integrity=integrity,
        foreign_key_violations=violations,
        table_count=tables,
        counts=counts,
    )


def status(db_path: Path | None = None) -> EngineStatus:
    with session(db_path) as conn:
        counts = {
            table: int(conn.execute("SELECT COUNT(*) FROM " + table).fetchone()[0])
            for table in seeding.EXPECTED_COUNTS
        }
        return _status(conn, counts)


def exam_directions(
    *,
    subject_id: int | None = None,
    chapter_id: int | None = None,
    keyword: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db_path: Path | None = None,
) -> tuple[tuple[ExamDirection, ...], int]:
    limit, offset = _bounds(limit, offset)
    with session(db_path) as conn:
        items = dao_dimensions.list_exam_directions(
            conn,
            subject_id=subject_id,
            chapter_id=chapter_id,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        total = dao_dimensions.count_exam_directions(
            conn,
            subject_id=subject_id,
            chapter_id=chapter_id,
            keyword=keyword,
        )
        return items, total


def exam_direction(direction_id: int, *, db_path: Path | None = None) -> ExamDirection | None:
    with session(db_path) as conn:
        return dao_dimensions.get_exam_direction(conn, direction_id)


def questions_of_direction(
    direction_id: int,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    db_path: Path | None = None,
) -> QuestionPage:
    limit, offset = _bounds(limit, offset)
    with session(db_path) as conn:
        return dao_questions.questions_by_exam_direction(
            conn, direction_id, limit=limit, offset=offset
        )


def knowledge_points(
    *,
    subject_id: int | None = None,
    parent_id: int | None = None,
    roots_only: bool = False,
    keyword: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db_path: Path | None = None,
) -> tuple[tuple[KnowledgePoint, ...], int]:
    limit, offset = _bounds(limit, offset)
    with session(db_path) as conn:
        items = dao_dimensions.list_knowledge_points(
            conn,
            subject_id=subject_id,
            parent_id=parent_id,
            roots_only=roots_only,
            keyword=keyword,
            limit=limit,
            offset=offset,
        )
        total = dao_dimensions.count_knowledge_points(
            conn,
            subject_id=subject_id,
            parent_id=parent_id,
            roots_only=roots_only,
            keyword=keyword,
        )
        return items, total


def knowledge_point(point_id: int, *, db_path: Path | None = None) -> KnowledgePoint | None:
    with session(db_path) as conn:
        return dao_dimensions.get_knowledge_point(conn, point_id)


def knowledge_tree(
    subject_id: int,
    *,
    db_path: Path | None = None,
) -> tuple[KnowledgeNode, ...]:
    with session(db_path) as conn:
        return dao_dimensions.knowledge_tree(conn, subject_id=subject_id)


def questions_of_point(
    point_id: int,
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
    db_path: Path | None = None,
) -> QuestionPage:
    limit, offset = _bounds(limit, offset)
    with session(db_path) as conn:
        return dao_questions.questions_by_knowledge_point(
            conn, point_id, limit=limit, offset=offset
        )


def question(question_id: str, *, db_path: Path | None = None) -> QuestionRecord | None:
    with session(db_path) as conn:
        return dao_questions.get_question(conn, question_id)


def dictionaries(*, db_path: Path | None = None) -> Dictionaries:
    """录题下拉框的五张小字典：每一张都单表读出，不做跨表拼接。"""
    with session(db_path) as conn:
        return dao_dictionary.load_dictionaries(conn)


def create_question(document: Any, *, db_path: Path | None = None) -> CreatedQuestion:
    """表单 → 解析外键 → 主表与从表分步落库；不合法时抛 ``EntryRejected``。

    一次会话内完成解析与写入：解析看到的外键与写入时的库是同一份，
    避免两次开库之间维度表被改掉。
    """
    with session(db_path) as conn:
        prepared = entry.prepare_question(conn, document)
        return writer.create_question(conn, prepared)


def textbooks(
    *,
    subject_id: int | None = None,
    grade_id: int | None = None,
    db_path: Path | None = None,
) -> tuple[Textbook, ...]:
    with session(db_path) as conn:
        return dao_dimensions.list_textbooks(
            conn, subject_id=subject_id, grade_id=grade_id
        )


def chapters(
    textbook_id: int,
    *,
    parent_id: int | None = None,
    roots_only: bool = True,
    db_path: Path | None = None,
) -> tuple[Chapter, ...]:
    with session(db_path) as conn:
        return dao_dimensions.list_chapters(
            conn, textbook_id, parent_id=parent_id, roots_only=roots_only
        )


__all__ = [
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "chapters",
    "create_question",
    "dictionaries",
    "ensure_ready",
    "exam_direction",
    "exam_directions",
    "knowledge_point",
    "knowledge_points",
    "knowledge_tree",
    "question",
    "questions_of_direction",
    "questions_of_point",
    "session",
    "status",
    "textbooks",
]

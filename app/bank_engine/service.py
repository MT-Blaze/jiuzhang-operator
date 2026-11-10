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
    dao_console,
    dao_dictionary,
    dao_dimensions,
    dao_linkage,
    dao_questions,
    entry,
    seeding,
    writer,
)
from app.bank_engine.models import (
    Chapter,
    ChapterNode,
    CreatedQuestion,
    Dictionaries,
    EngineStatus,
    ExamDirection,
    ImportReport,
    KnowledgeNode,
    KnowledgePoint,
    LinkedKnowledgePoint,
    QuestionPage,
    QuestionRecord,
    ReferenceHit,
    Textbook,
)
from app.core import toml_io

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


# ---- 字典控制台（阶段二）：基础五表读写与删除防呆，dataclass 进出 ----


def console_list(
    table: str,
    *,
    keyword: str | None = None,
    filters: dict[str, Any] | None = None,
    limit: int = 50,
    offset: int = 0,
    db_path: Path | None = None,
) -> tuple[tuple[Any, ...], int]:
    limit, offset = _bounds(limit, offset)
    with session(db_path) as conn:
        return dao_console.list_rows(
            conn, table, keyword=keyword, filters=filters, limit=limit, offset=offset
        )


def console_row(table: str, row_id: int, *, db_path: Path | None = None) -> Any:
    with session(db_path) as conn:
        return dao_console.get_row(conn, table, row_id)


def console_references(
    table: str, row_id: int, *, db_path: Path | None = None
) -> tuple[ReferenceHit, ...]:
    with session(db_path) as conn:
        return dao_console.find_references(conn, table, row_id)


def console_insert(table: str, values: dict[str, Any], *, db_path: Path | None = None) -> Any:
    with session(db_path) as conn:
        return dao_console.insert_row(conn, table, values)


def console_update(
    table: str, row_id: int, values: dict[str, Any], *, db_path: Path | None = None
) -> Any:
    with session(db_path) as conn:
        return dao_console.update_row(conn, table, row_id, values)


def console_delete(table: str, row_id: int, *, db_path: Path | None = None) -> None:
    with session(db_path) as conn:
        dao_console.delete_row(conn, table, row_id)


def console_import(text: str, *, db_path: Path | None = None) -> ImportReport:
    try:
        data = toml_io.loads(text)
    except ValueError as exc:
        raise ValueError("TOML 解析失败：" + str(exc)) from exc
    with session(db_path) as conn:
        return dao_console.import_rows(conn, data)


# ---- 四栏联动（阶段三）：章节树 / 关联读写 / 拖拽排序，dataclass 进出 ----


def linkage_chapter_tree(textbook_id: int, *, db_path: Path | None = None) -> tuple[ChapterNode, ...]:
    with session(db_path) as conn:
        return dao_linkage.chapter_tree(conn, textbook_id)


def linkage_chapter_points(
    chapter_id: int, *, db_path: Path | None = None
) -> tuple[LinkedKnowledgePoint, ...]:
    with session(db_path) as conn:
        return dao_linkage.chapter_points(conn, chapter_id)


def linkage_point_directions(
    point_id: int, *, db_path: Path | None = None
) -> tuple[ExamDirection, ...]:
    with session(db_path) as conn:
        return dao_linkage.point_directions(conn, point_id)


def linkage_direction_tags(
    direction_id: int, *, db_path: Path | None = None
) -> tuple[LinkedKnowledgePoint, ...]:
    with session(db_path) as conn:
        return dao_linkage.direction_tags(conn, direction_id)


def linkage_reorder(
    map_key: str, group_id: int, member_ids: list[int], *, db_path: Path | None = None
) -> None:
    with session(db_path) as conn:
        dao_linkage.reorder(conn, map_key, group_id, member_ids)


def linkage_add_direction(
    point_id: int, name: str, *, db_path: Path | None = None
) -> ExamDirection:
    with session(db_path) as conn:
        return dao_linkage.add_direction(conn, point_id, name)


def linkage_delete_direction(
    point_id: int, direction_id: int, *, db_path: Path | None = None
) -> None:
    with session(db_path) as conn:
        dao_linkage.delete_direction(conn, point_id, direction_id)


def linkage_add_tag(
    direction_id: int, point_id: int, *, db_path: Path | None = None
) -> LinkedKnowledgePoint:
    with session(db_path) as conn:
        return dao_linkage.add_tag(conn, direction_id, point_id)


def linkage_remove_tag(
    direction_id: int, point_id: int, *, db_path: Path | None = None
) -> None:
    with session(db_path) as conn:
        dao_linkage.remove_tag(conn, direction_id, point_id)


__all__ = [
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "chapters",
    "console_delete",
    "console_import",
    "console_insert",
    "console_list",
    "console_references",
    "console_row",
    "console_update",
    "create_question",
    "dictionaries",
    "ensure_ready",
    "exam_direction",
    "exam_directions",
    "knowledge_point",
    "knowledge_points",
    "knowledge_tree",
    "linkage_add_direction",
    "linkage_add_tag",
    "linkage_chapter_points",
    "linkage_chapter_tree",
    "linkage_delete_direction",
    "linkage_direction_tags",
    "linkage_point_directions",
    "linkage_remove_tag",
    "linkage_reorder",
    "question",
    "questions_of_direction",
    "questions_of_point",
    "session",
    "status",
    "textbooks",
]

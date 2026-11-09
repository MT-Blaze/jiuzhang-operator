"""DAO 地基：连接、分片、字典映射与维度行装载。所有 SQL 只碰单表。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Iterator

from app.bank_engine import paths
from app.bank_engine.models import ExamDirection, KnowledgePoint

ASSEMBLE_CHUNK = 300


class EngineNotReady(RuntimeError):
    pass


class QuestionNotFound(EngineNotReady):
    pass


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else paths.engine_db_path()
    if not path.is_file():
        from app.bank_engine.builder import build_engine

        build_engine(db_path=path)
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def chunks(values: list[Any] | tuple[Any, ...], size: int = ASSEMBLE_CHUNK) -> Iterator[list[Any]]:
    for start in range(0, len(values), size):
        yield list(values[start:start + size])


def in_sql(column: str, values: list[Any]) -> tuple[str, list[Any]]:
    placeholders = ",".join("?" for _ in values)
    return column + " IN (" + placeholders + ")", list(values)


def load_rows_by_ids(
    conn: sqlite3.Connection,
    sql_prefix: str,
    ids: Iterable[int | str],
    *,
    key: str = "id",
) -> dict[Any, sqlite3.Row]:
    unique = list(dict.fromkeys(ids))
    found: dict[Any, sqlite3.Row] = {}
    for part in chunks(unique):
        clause, params = in_sql(key, part)
        sql = sql_prefix + " WHERE " + clause
        for row in conn.execute(sql, params):
            found[row[key]] = row
    return found


def dictionary_codes(conn: sqlite3.Connection) -> dict[str, dict[int, str]]:
    def load(table: str) -> dict[int, str]:
        return {int(row["id"]): str(row["code"]) for row in conn.execute(
            "SELECT id, code FROM " + table)}

    return {
        "subjects": load("dict_subjects"),
        "question_types": load("dict_question_types"),
        "difficulties": load("dict_difficulties"),
        "qualities": load("dict_question_qualities"),
    }


def dictionary_names(conn: sqlite3.Connection) -> dict[str, dict[int, str]]:
    def load(table: str) -> dict[int, str]:
        return {int(row["id"]): str(row["name"]) for row in conn.execute(
            "SELECT id, name FROM " + table)}

    return {
        "subjects": load("dict_subjects"),
        "grades": load("dict_grades"),
        "question_types": load("dict_question_types"),
        "difficulties": load("dict_difficulties"),
        "qualities": load("dict_question_qualities"),
    }


def load_exam_directions(
    conn: sqlite3.Connection, ids: Iterable[int]
) -> dict[int, ExamDirection]:
    rows = load_rows_by_ids(
        conn,
        "SELECT id, name, code, sort_order, subject_id, chapter_id, description "
        "FROM dim_exam_directions",
        ids,
    )
    return {
        int(row["id"]): ExamDirection(
            id=int(row["id"]),
            name=str(row["name"]),
            code=str(row["code"]),
            sort_order=int(row["sort_order"]),
            subject_id=int(row["subject_id"]),
            chapter_id=None if row["chapter_id"] is None else int(row["chapter_id"]),
            description=None if row["description"] is None else str(row["description"]),
        )
        for row in rows.values()
    }


def load_knowledge_points(
    conn: sqlite3.Connection, ids: Iterable[int]
) -> dict[int, KnowledgePoint]:
    rows = load_rows_by_ids(
        conn,
        "SELECT id, name, code, sort_order, subject_id, parent_id "
        "FROM dim_knowledge_points",
        ids,
    )
    return {
        int(row["id"]): KnowledgePoint(
            id=int(row["id"]),
            name=str(row["name"]),
            code=str(row["code"]),
            sort_order=int(row["sort_order"]),
            subject_id=int(row["subject_id"]),
            parent_id=None if row["parent_id"] is None else int(row["parent_id"]),
        )
        for row in rows.values()
    }

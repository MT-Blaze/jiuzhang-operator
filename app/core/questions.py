"""题目仓储：Schema 校验、行 ↔ 标准结构转换与 SQLite 读写。

``schemas/question.json`` 是唯一校验来源；本模块不另造字段规则。
"""

from __future__ import annotations

import copy
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Iterable

from jsonschema import Draft202012Validator

from app.core.config import settings
from app.core.contract import (
    DIFFICULTY_LEVELS,
    normalize_contract_version,
    normalize_difficulty,
)
from app.core.db import connect, transaction

LOCAL_TZ = timezone(timedelta(hours=8))
MAX_PAGE_SIZE = 100
JSON_FIELDS = {
    "options": "options_json",
    "answer": "answer_json",
    "tags": "tags_json",
    "taxonomy": "taxonomy_json",
    "source": "source_json",
    "images": "images_json",
    "extensions": "extensions_json",
}
COLUMN_ORDER = (
    "id",
    "schema_version",
    "type",
    "stem",
    "options_json",
    "answer_json",
    "solution",
    "difficulty",
    "tags_json",
    "taxonomy_json",
    "source_json",
    "images_json",
    "extensions_json",
    "status",
    "revision",
    "author",
    "created_at",
    "updated_at",
)
FILTER_FIELDS = {
    "type": ("single_choice", "multiple_choice", "fill_blank", "solution", "proof", "unknown"),
    "difficulty": DIFFICULTY_LEVELS,
    "status": ("draft", "published", "archived"),
}


class QuestionError(Exception):
    """题目读写的基类错误。"""


class QuestionNotFound(QuestionError):
    pass


class QuestionConflict(QuestionError):
    pass


class QuestionValidationError(QuestionError):
    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("题目不符合 Schema")


def now_iso() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


@lru_cache(maxsize=1)
def _validator() -> Draft202012Validator:
    schema = json.loads((settings.schemas_dir / "question.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_question(document: dict[str, Any]) -> None:
    errors: list[str] = []
    for error in sorted(_validator().iter_errors(document), key=lambda item: list(item.absolute_path)):
        location = ".".join(str(part) for part in error.absolute_path) or "(root)"
        errors.append(f"{location}: {error.message}")
        if len(errors) >= 20:
            break
    if errors:
        raise QuestionValidationError(errors)


def _encode_json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _new_id() -> str:
    return "q_" + secrets.token_urlsafe(18)


def _row_is_taken(con: sqlite3.Connection, question_id: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM questions WHERE id = ? UNION ALL SELECT 1 FROM question_tombstones WHERE id = ?",
        (question_id, question_id),
    ).fetchone()
    return row is not None


def _document_to_row(document: dict[str, Any]) -> dict[str, Any]:
    meta = document["meta"]
    row = {
        "id": document["id"],
        "schema_version": document["schema_version"],
        "type": document["type"],
        "stem": document["stem"],
        "solution": document.get("solution"),
        "difficulty": document["difficulty"],
        "status": meta["status"],
        "revision": int(meta["revision"]),
        "author": meta.get("author"),
        "created_at": meta["created_at"],
        "updated_at": meta["updated_at"],
    }
    for field, column in JSON_FIELDS.items():
        row[column] = _encode_json(document.get(field))
    return row


def _row_to_document(row: sqlite3.Row) -> dict[str, Any]:
    document: dict[str, Any] = {
        "schema_version": row["schema_version"],
        "id": row["id"],
        "type": row["type"],
        "stem": row["stem"],
        "difficulty": row["difficulty"],
    }
    for field, column in JSON_FIELDS.items():
        raw = row[column]
        if raw is not None:
            document[field] = json.loads(raw)
    if row["solution"] is not None:
        document["solution"] = row["solution"]

    meta: dict[str, Any] = {
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "revision": int(row["revision"]),
        "status": row["status"],
    }
    if row["author"] is not None:
        meta["author"] = row["author"]
    document["meta"] = meta
    return document


def _prepare_create(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise QuestionValidationError(["(root): 请求体必须是 JSON 对象"])

    document = copy.deepcopy(payload)
    document["schema_version"] = normalize_contract_version(document.get("schema_version"))
    if "difficulty" in document:
        document["difficulty"] = normalize_difficulty(document["difficulty"])
    if not document.get("id"):
        document["id"] = _new_id()

    meta = document.get("meta")
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise QuestionValidationError(["meta: 必须是对象"])

    timestamp = now_iso()
    meta["created_at"] = timestamp
    meta["updated_at"] = timestamp
    meta["revision"] = 1
    meta.setdefault("status", "draft")
    document["meta"] = meta
    return document


def prepare_new_question(payload: Any) -> dict[str, Any]:
    """补齐 schema_version / 新 id / meta 时间戳，供其他题库写入端复用。

    录题插件写的是插件题库（core-bank 的 SQLite），与底座 ``questions`` 表
    不是同一份存储；两边必须共用同一套题目契约，否则同题在两库字段口径不一。
    """
    return _prepare_create(payload)


def create_question(payload: Any) -> dict[str, Any]:
    document = _prepare_create(payload)
    validate_question(document)
    row = _document_to_row(document)

    with transaction() as con:
        if _row_is_taken(con, document["id"]):
            raise QuestionConflict(f"题目 ID {document['id']} 已存在或已被删除，按契约不得复用。")
        columns = ", ".join(COLUMN_ORDER)
        placeholders = ", ".join("?" for _ in COLUMN_ORDER)
        try:
            con.execute(
                f"INSERT INTO questions ({columns}) VALUES ({placeholders})",
                [row[column] for column in COLUMN_ORDER],
            )
        except sqlite3.IntegrityError as exc:
            raise QuestionConflict(f"题目 ID {document['id']} 已存在。") from exc
    return document


def get_question(question_id: str) -> dict[str, Any]:
    con = connect()
    try:
        row = con.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
    finally:
        con.close()
    if row is None:
        raise QuestionNotFound(question_id)
    return _row_to_document(row)


def _escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_questions(
    *,
    page: int = 1,
    page_size: int = 20,
    search: str = "",
    question_type: str | None = None,
    difficulty: str | None = None,
    status: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
    page = max(1, int(page))
    where: list[str] = []
    params: list[Any] = []

    if search:
        pattern = f"%{_escape_like(search)}%"
        where.append("(stem LIKE ? ESCAPE '\\' OR id = ?)")
        params.extend([pattern, search])
    for column, value in (
        ("type", question_type),
        ("difficulty", difficulty),
        ("status", status),
    ):
        if value:
            if column == "difficulty":
                value = normalize_difficulty(value)
            if value not in FILTER_FIELDS[column]:
                raise QuestionValidationError([f"{column}: 不支持的值 {value!r}"])
            where.append(f"{column} = ?")
            params.append(value)

    clause = f"WHERE {' AND '.join(where)}" if where else ""
    con = connect()
    try:
        total = int(
            con.execute(f"SELECT COUNT(*) FROM questions {clause}", params).fetchone()[0]
        )
        rows = con.execute(
            f"SELECT * FROM questions {clause} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            [*params, page_size, (page - 1) * page_size],
        ).fetchall()
    finally:
        con.close()
    return [_row_to_document(row) for row in rows], total


def replace_question(question_id: str, payload: Any) -> dict[str, Any]:
    current = get_question(question_id)
    if not isinstance(payload, dict):
        raise QuestionValidationError(["(root): 请求体必须是 JSON 对象"])

    document = copy.deepcopy(payload)
    if document.get("id") and document["id"] != question_id:
        raise QuestionValidationError(["id: 不允许通过更新修改题目 ID"])
    document["id"] = question_id
    document["schema_version"] = normalize_contract_version(
        document.get("schema_version") or current["schema_version"]
    )
    if "difficulty" in document:
        document["difficulty"] = normalize_difficulty(document["difficulty"])

    incoming_meta = document.get("meta")
    if incoming_meta is None:
        incoming_meta = {}
    if not isinstance(incoming_meta, dict):
        raise QuestionValidationError(["meta: 必须是对象"])

    expected = incoming_meta.get("revision")
    if expected is not None:
        try:
            expected_revision = int(expected)
        except (TypeError, ValueError) as exc:
            raise QuestionValidationError(["meta.revision: 必须是整数"]) from exc
        if expected_revision != current["meta"]["revision"]:
            raise QuestionConflict(
                f"版本冲突：当前 revision={current['meta']['revision']}，请求为 {expected_revision}。"
            )

    meta: dict[str, Any] = {
        "created_at": current["meta"]["created_at"],
        "updated_at": now_iso(),
        "revision": current["meta"]["revision"] + 1,
        "status": incoming_meta.get("status", current["meta"]["status"]),
    }
    if "author" in incoming_meta:
        meta["author"] = incoming_meta["author"]
    document["meta"] = meta

    validate_question(document)
    row = _document_to_row(document)
    assignments = ", ".join(f"{column} = ?" for column in COLUMN_ORDER if column != "id")
    values = [row[column] for column in COLUMN_ORDER if column != "id"]

    with transaction() as con:
        cursor = con.execute(f"UPDATE questions SET {assignments} WHERE id = ?", [*values, question_id])
        if cursor.rowcount == 0:
            raise QuestionNotFound(question_id)
    return document


def delete_question(question_id: str) -> None:
    timestamp = now_iso()
    with transaction() as con:
        cursor = con.execute("DELETE FROM questions WHERE id = ?", (question_id,))
        if cursor.rowcount == 0:
            raise QuestionNotFound(question_id)
        con.execute(
            "INSERT INTO question_tombstones (id, deleted_at) VALUES (?, ?) "
            "ON CONFLICT(id) DO UPDATE SET deleted_at = excluded.deleted_at",
            (question_id, timestamp),
        )

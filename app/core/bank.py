"""插件题库服务：为前端插件提供只读、参数化的 SQLite 题库。

为什么放在底座（而不是插件 JS 里）：
- 插件运行在沙箱 iframe 中，拿不到文件系统与数据库（AGENTS §2）；
- 插件又需要真题列表、年级/难度过滤与组卷取数，因此由底座提供一条
  **只读 Host API**，插件经舞台消息协议申请数据，宿主代为查询并回传。

安全边界：
- 插件 ID 必须匹配反向域名；数据库文件路径由底座拼装，插件传不了任意路径；
- 全部过滤条件走参数绑定；排序与列名只从常量表取，不接受插件输入；
- 单页最多 100 条，搜索词最多 100 字，避免一次把 456 题全倒进 iframe。

数据库随插件包分发：``plugins/<id>/bank/bank.db``。首次访问时由底座原子复制到
当前工作区的 ``data/banks/<id>.db``，之后只读取这份工作区副本。
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable

from app.core.config import settings

PLUGIN_ID_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
MAX_PAGE_SIZE = 100
MAX_SEARCH = 100
MAX_BASKET = 200

SCHEMA_VERSION = 1

_DDL = """
CREATE TABLE IF NOT EXISTS bank_questions (
    id              TEXT PRIMARY KEY,
    grade           TEXT NOT NULL DEFAULT '',
    difficulty      TEXT NOT NULL DEFAULT '',
    type            TEXT NOT NULL DEFAULT '',
    chapter         TEXT NOT NULL DEFAULT '',
    textbook        TEXT NOT NULL DEFAULT '',
    question_no     TEXT NOT NULL DEFAULT '',
    stem            TEXT NOT NULL,
    options_json    TEXT,
    answer_json     TEXT,
    solution        TEXT,
    tags_json       TEXT,
    taxonomy_json   TEXT,
    source_json     TEXT,
    images_json     TEXT,
    extensions_json TEXT,
    meta_json       TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_bank_grade ON bank_questions (grade);
CREATE INDEX IF NOT EXISTS idx_bank_difficulty ON bank_questions (difficulty);
CREATE INDEX IF NOT EXISTS idx_bank_type ON bank_questions (type);
CREATE INDEX IF NOT EXISTS idx_bank_chapter ON bank_questions (chapter);
CREATE TABLE IF NOT EXISTS bank_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

_COLUMNS = (
    "id", "grade", "difficulty", "type", "chapter", "textbook", "question_no",
    "stem", "options_json", "answer_json", "solution", "tags_json",
    "taxonomy_json", "source_json", "images_json", "extensions_json",
    "meta_json", "created_at", "updated_at",
)

_JSON_FIELDS = (
    ("options", "options_json"),
    ("answer", "answer_json"),
    ("tags", "tags_json"),
    ("taxonomy", "taxonomy_json"),
    ("source", "source_json"),
    ("images", "images_json"),
    ("extensions", "extensions_json"),
)

# 初始化只复制一次；同一进程内并发访问共享这把锁，避免半写文件被发现。
_seed_lock = threading.Lock()


class BankError(Exception):
    pass


class BankNotFound(BankError):
    pass


def validate_plugin_id(plugin_id: str) -> str:
    if not isinstance(plugin_id, str) or PLUGIN_ID_RE.fullmatch(plugin_id) is None:
        raise BankError("插件 ID 非法")
    return plugin_id


def bank_db_path(plugin_id: str, *, create: bool = True) -> Path:
    plugin_id = validate_plugin_id(plugin_id)
    path = Path(settings.data_dir) / "banks" / f"{plugin_id}.db"
    if create:
        path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _seed_path(plugin_id: str) -> Path:
    return Path(settings.plugins_dir) / plugin_id / "bank" / "bank.db"


def ensure_bank(plugin_id: str) -> Path:
    """确保工作区题库存在；缺失时从插件包自带的 bank.db 原子复制。"""
    plugin_id = validate_plugin_id(plugin_id)
    path = bank_db_path(plugin_id)
    if path.is_file() and path.stat().st_size > 0:
        return path

    source = _seed_path(plugin_id)
    if not source.is_file():
        raise BankNotFound(
            f"题库尚未初始化：缺少 {source}。请先运行 tools/migrate_legacy_bank.py。"
        )

    with _seed_lock:
        if path.is_file() and path.stat().st_size > 0:
            return path
        tmp = path.with_suffix(".db.part")
        try:
            shutil.copyfile(source, tmp)
            tmp.replace(path)
        finally:
            if tmp.exists():
                tmp.unlink()
        _seed_assets(plugin_id)
    return path


def _seed_assets(plugin_id: str) -> None:
    """把插件包 ``bank/assets`` 里的配图补进当前工作区 uploads/（只补缺失文件）。

    图片不是题目结构的一部分，但 schema 指向 ``/static/uploads/``；插件要能在
    另一台机器上“装上就有图”，随包的图必须由底座在首次建库时落位。
    """
    source = Path(settings.plugins_dir) / plugin_id / "bank" / "assets"
    if not source.is_dir():
        return
    target_dir = Path(settings.uploads_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        if not item.is_file() or item.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            continue
        target = target_dir / item.name
        if target.is_file():
            continue
        try:
            shutil.copyfile(item, target)
        except OSError:
            # 单张图坏了不阻断题库读取；题目里会显示缺图占位
            continue


def connect(plugin_id: str) -> sqlite3.Connection:
    path = ensure_bank(plugin_id)
    con = sqlite3.connect(path, timeout=10.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA busy_timeout = 5000")
    return con


def init_bank(plugin_id: str, db_path: Path | None = None) -> Path:
    """创建/升级一份空题库（迁移脚本与测试共用）。"""
    path = db_path or bank_db_path(plugin_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=10.0)
    try:
        try:
            con.execute("PRAGMA journal_mode = WAL")
        except sqlite3.Error:
            pass
        con.executescript(_DDL)
        version = int(con.execute("PRAGMA user_version").fetchone()[0])
        if version > SCHEMA_VERSION:
            raise BankError(
                f"题库结构版本 {version} 高于程序支持的 {SCHEMA_VERSION}，请升级底座。"
            )
        con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        con.commit()
    finally:
        con.close()
    return path


def _encode(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _document_row(document: dict[str, Any]) -> dict[str, Any]:
    meta = document.get("meta") or {}
    taxonomy = document.get("taxonomy") or {}
    source = document.get("source") or {}
    legacy = (document.get("extensions") or {}).get("org.jiuzhang.legacy") or {}
    return {
        "id": document["id"],
        "grade": str(document.get("grade") or legacy.get("grade") or ""),
        "difficulty": document.get("difficulty", ""),
        "type": document.get("type", ""),
        "chapter": str(taxonomy.get("chapter") or ""),
        "textbook": str(taxonomy.get("textbook") or ""),
        "question_no": str(source.get("question_no") or ""),
        "stem": document["stem"],
        "options_json": _encode(document.get("options")),
        "answer_json": _encode(document.get("answer")),
        "solution": document.get("solution"),
        "tags_json": _encode(document.get("tags")),
        "taxonomy_json": _encode(document.get("taxonomy")),
        "source_json": _encode(source),
        "images_json": _encode(document.get("images")),
        "extensions_json": _encode(document.get("extensions")),
        "meta_json": _encode(meta),
        "created_at": str(meta.get("created_at") or ""),
        "updated_at": str(meta.get("updated_at") or ""),
    }


def _row_document(row: sqlite3.Row) -> dict[str, Any]:
    document: dict[str, Any] = {
        "id": row["id"],
        "type": row["type"],
        "stem": row["stem"],
        "difficulty": row["difficulty"],
        "grade": row["grade"],
    }
    for field, column in _JSON_FIELDS:
        raw = row[column]
        if raw:
            document[field] = json.loads(raw)
    if row["solution"]:
        document["solution"] = row["solution"]
    document["meta"] = json.loads(row["meta_json"]) if row["meta_json"] else {}
    return document


def import_documents(
    plugin_id: str,
    documents: Iterable[dict[str, Any]],
    *,
    reset: bool = False,
    source_info: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    """批量写入题库（迁移与测试专用），单事务，失败整体回滚。"""
    path = db_path or bank_db_path(plugin_id)
    if reset and path.exists():
        for suffix in ("", "-wal", "-shm"):
            candidate = Path(str(path) + suffix)
            if candidate.exists():
                candidate.unlink()
    init_bank(plugin_id, path)

    rows = [_document_row(document) for document in documents]
    con = sqlite3.connect(path, timeout=10.0)
    try:
        con.execute("PRAGMA busy_timeout = 5000")
        con.execute("BEGIN IMMEDIATE")
        if reset:
            con.execute("DELETE FROM bank_questions")
        placeholders = ", ".join("?" for _ in _COLUMNS)
        columns = ", ".join(_COLUMNS)
        con.executemany(
            f"INSERT OR REPLACE INTO bank_questions ({columns}) VALUES ({placeholders})",
            [[row[column] for column in _COLUMNS] for row in rows],
        )
        if source_info:
            for key, value in source_info.items():
                con.execute(
                    "INSERT INTO bank_meta (key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (str(key), json.dumps(value, ensure_ascii=False)),
                )
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return len(rows)


def metadata(plugin_id: str) -> dict[str, Any]:
    con = connect(plugin_id)
    try:
        rows = con.execute("SELECT key, value FROM bank_meta").fetchall()
    finally:
        con.close()
    result: dict[str, Any] = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except json.JSONDecodeError:
            result[row["key"]] = row["value"]
    return result


def _like(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def _build_where(
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    chapter: str = "",
    textbook: str = "",
    search: str = "",
    ids: Iterable[str] | None = None,
) -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("grade", grade),
        ("difficulty", difficulty),
        ("type", question_type),
        ("chapter", chapter),
        ("textbook", textbook),
    ):
        value = str(value or "").strip()
        if value and value != "全部":
            where.append(f"{column} = ?")
            params.append(value[:64])
    term = str(search or "").strip()[:MAX_SEARCH]
    if term:
        where.append("(stem LIKE ? ESCAPE '\\' OR id = ?)")
        params.extend([_like(term), term])
    if ids is not None:
        wanted = list(ids)
        if not wanted:
            return "WHERE 1 = 0", []
        where.append("id IN (" + ", ".join("?" for _ in wanted) + ")")
        params.extend(wanted)
    clause = "WHERE " + " AND ".join(where) if where else ""
    return clause, params


def list_questions(
    plugin_id: str,
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    chapter: str = "",
    textbook: str = "",
    search: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
    clause, params = _build_where(
        grade=grade,
        difficulty=difficulty,
        question_type=question_type,
        chapter=chapter,
        textbook=textbook,
        search=search,
    )
    con = connect(plugin_id)
    try:
        total = int(con.execute(f"SELECT COUNT(*) FROM bank_questions {clause}", params).fetchone()[0])
        rows = con.execute(
            f"SELECT * FROM bank_questions {clause} ORDER BY id LIMIT ? OFFSET ?",
            [*params, page_size, (page - 1) * page_size],
        ).fetchall()
    finally:
        con.close()
    return [_row_document(row) for row in rows], total


def get_question(plugin_id: str, question_id: str) -> dict[str, Any]:
    if not isinstance(question_id, str) or not question_id.startswith("q_"):
        raise BankNotFound("题目 ID 非法")
    con = connect(plugin_id)
    try:
        row = con.execute(
            "SELECT * FROM bank_questions WHERE id = ?", (question_id,)
        ).fetchone()
    finally:
        con.close()
    if row is None:
        raise BankNotFound(f"题库中没有题目 {question_id}")
    return _row_document(row)


def get_many(plugin_id: str, ids: Iterable[str]) -> list[dict[str, Any]]:
    wanted = [item for item in ids if isinstance(item, str) and item.startswith("q_")][:MAX_BASKET]
    if not wanted:
        return []
    clause, params = _build_where(ids=wanted)
    con = connect(plugin_id)
    try:
        rows = con.execute(f"SELECT * FROM bank_questions {clause}", params).fetchall()
    finally:
        con.close()
    by_id = {row["id"]: _row_document(row) for row in rows}
    return [by_id[item] for item in wanted if item in by_id]


def random_question(
    plugin_id: str,
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    search: str = "",
) -> dict[str, Any] | None:
    clause, params = _build_where(
        grade=grade,
        difficulty=difficulty,
        question_type=question_type,
        search=search,
    )
    con = connect(plugin_id)
    try:
        row = con.execute(
            f"SELECT * FROM bank_questions {clause} ORDER BY RANDOM() LIMIT 1", params
        ).fetchone()
    finally:
        con.close()
    return _row_document(row) if row else None


def stats(plugin_id: str) -> dict[str, Any]:
    con = connect(plugin_id)
    try:
        total = int(con.execute("SELECT COUNT(*) FROM bank_questions").fetchone()[0])

        def grouped(column: str, limit: int = 40) -> list[dict[str, Any]]:
            rows = con.execute(
                f"SELECT {column} AS name, COUNT(*) AS count FROM bank_questions "
                f"GROUP BY {column} ORDER BY count DESC, name ASC LIMIT ?",
                (limit,),
            ).fetchall()
            return [{"name": row["name"], "count": int(row["count"])} for row in rows]

        return {
            "total": total,
            "grades": grouped("grade"),
            "difficulties": grouped("difficulty"),
            "types": grouped("type"),
            "chapters": grouped("chapter", 30),
            "textbooks": grouped("textbook"),
        }
    finally:
        con.close()


def import_count(plugin_id: str) -> int:
    con = connect(plugin_id)
    try:
        return int(con.execute("SELECT COUNT(*) FROM bank_questions").fetchone()[0])
    finally:
        con.close()

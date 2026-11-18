"""题干全文检索预研：SQLite FTS5 虚拟表 + 中文逐字切分。

为什么不直接用默认 tokenizer：FTS5 的 ``unicode61`` 把一整串连续汉字当成
**一个** token，搜「二次方程」命中不了「一元二次方程的解法」；``trigram``
又要三个字符起才能查（「函数」这种两字词直接落空）。

这里把中文拆成单字 token 入索引，查询同样拆字后按**短语**检索——
相邻性由 FTS5 的 phrase 保证，两字词、长句、中英混排都能命中，
公式片段（``f(x)``、``x^2``）仍按原样成词。

索引是独立虚拟表，不动 ``questions`` 本表结构；建不起来时调用方应退回
现有的 ``LIKE`` 路径，绝不因此打不开题库。
"""

from __future__ import annotations

import re
import sqlite3
from typing import Iterable

__all__ = [
    "FtsUnavailable",
    "CJK",
    "segment",
    "available",
    "ensure_schema",
    "upsert",
    "remove",
    "index_all",
    "rebuild",
    "query_expression",
    "query_ids",
    "doc_count",
]

TABLE = "question_fts"

# 汉字与中文标点都按单字切：标点留在句子里会让短语查询断档，统一当分隔符。
CJK = re.compile(r"[\u3000-\u303f\u3400-\u4dbf\u4e00-\u9fff\uff00-\uffef]")
_SPACES = re.compile(r"\s+")


class FtsUnavailable(RuntimeError):
    """当前 SQLite 没编译 FTS5 模块。调用方据此退回 LIKE，不影响题库可用。"""


def segment(text: str) -> str:
    """把中文切成单字 token，英文/公式原样保留，多余空白压成一个空格。"""
    if not isinstance(text, str):
        return ""
    chars: list[str] = []
    for char in text:
        if CJK.match(char):
            chars.append(" " + char + " ")
        else:
            chars.append(char)
    return _SPACES.sub(" ", "".join(chars)).strip()


_AVAILABLE: bool | None = None


def available() -> bool:
    """探测本机 SQLite 是否带 FTS5。

    用独立内存库探测而不是借用调用方连接：FTS5 是编译期能力，与具体库无关；
    在调用方已经开着事务/游标时往它的 temp 库里建表，可能被误判成「没有 FTS5」。
    """
    global _AVAILABLE
    if _AVAILABLE is None:
        probe = sqlite3.connect(":memory:")
        try:
            probe.execute("CREATE VIRTUAL TABLE __fts_probe USING fts5(x)")
            _AVAILABLE = True
        except sqlite3.OperationalError:
            _AVAILABLE = False
        finally:
            probe.close()
    return _AVAILABLE


def ensure_schema(connection: sqlite3.Connection) -> None:
    if not available():
        raise FtsUnavailable("当前 SQLite 未编译 FTS5")
    connection.execute(
        f"CREATE VIRTUAL TABLE IF NOT EXISTS {TABLE} USING fts5("
        "stem, question_id UNINDEXED, tokenize='unicode61')"
    )


def upsert(connection: sqlite3.Connection, question_id: str, stem: str) -> None:
    """单题写入：先删后插，避免 FTS 里留旧版本残影。"""
    ensure_schema(connection)
    remove(connection, question_id)
    connection.execute(
        f"INSERT INTO {TABLE}(stem, question_id) VALUES (?, ?)",
        (segment(stem), str(question_id)),
    )


def remove(connection: sqlite3.Connection, question_id: str) -> int:
    ensure_schema(connection)
    cursor = connection.execute(
        f"DELETE FROM {TABLE} WHERE question_id = ?", (str(question_id),)
    )
    return cursor.rowcount


def index_all(connection: sqlite3.Connection, rows: Iterable[tuple[str, str]]) -> int:
    """全量重建：一次事务写入 (question_id, stem) 序列，返回写入条数。"""
    ensure_schema(connection)
    payload = [(segment(stem), str(question_id)) for question_id, stem in rows]
    with connection:
        connection.execute(f"DELETE FROM {TABLE}")
        connection.executemany(
            f"INSERT INTO {TABLE}(stem, question_id) VALUES (?, ?)", payload
        )
    return len(payload)


def rebuild(connection: sqlite3.Connection, source_table: str = "questions") -> int:
    """从题目主表全量重建索引；调用方负责连接的是正确的题库。"""
    cursor = connection.execute(f"SELECT id, stem FROM {source_table}")
    return index_all(connection, ((row[0], row[1]) for row in cursor))


def query_expression(text: str) -> str:
    """拆字后包成 FTS5 短语；引号按 FTS5 规则双写转义。

    公开出来是给调用方把 ``MATCH`` 直接嵌进自己的查询（分页计数时不丢筛选条件）。
    """
    tokens = segment(text).replace('"', '""')
    return f'"{tokens}"' if tokens else ""


def query_ids(connection: sqlite3.Connection, text: str, limit: int = 20) -> list[str]:
    expression = query_expression(text)
    if not expression:
        return []
    ensure_schema(connection)
    capped = max(1, min(int(limit), 200))
    rows = connection.execute(
        f"SELECT question_id FROM {TABLE} WHERE {TABLE} MATCH ? LIMIT ?",
        (expression, capped),
    )
    return [str(row[0]) for row in rows]


def doc_count(connection: sqlite3.Connection) -> int:
    ensure_schema(connection)
    row = connection.execute(f"SELECT count(*) FROM {TABLE}").fetchone()
    return int(row[0]) if row else 0

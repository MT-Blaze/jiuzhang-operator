"""core-bank 引擎的审核与改删：待审标记、打标、改题与删题。

``review_summary`` 按 ``REVIEW_FLAGS`` 汇总待审题；``update_question`` 只认白名单字段，
改哪几列写哪几列，并推进修订号；``delete_question`` 连带摘掉考向链接、来源与
FTS 索引——主库里不留孤儿行。"""

from __future__ import annotations

from app.core import questions as question_contract
from app.core.bank_codec import _extension_value
from app.core.bank_query import _fts_remove, _fts_upsert, get_question
from app.core.bank_schema import (
    BankNotFound,
    CHOICE_TYPES,
    EXT_GRADE_KEY,
    EXT_MIGRATION_KEY,
    REVIEW_FLAGS,
    _now,
    connect,
)
from app.core.bank_write import (
    _intake_document,
    _link_sources,
    _normalize_sources,
    _question_row,
    _remount_topics,
    _storage_ready,
)
from app.core.contract import normalize_contract_version, normalize_difficulty
from typing import Any, Iterable



# ---------------------------------------------------------------- 人工审核

def review_summary(plugin_id: str) -> dict[str, Any]:
    """待审队列概览：按灌库标记分组计数，供「待审任务」页签打角标。"""
    con = connect(plugin_id)
    try:
        total = int(con.execute(
            "SELECT COUNT(*) FROM questions q WHERE EXISTS ("
            " SELECT 1 FROM json_each(q.extensions) e"
            " WHERE json_extract(e.value, '$.key') = ?"
            " AND json_array_length(json_extract(e.value, '$.value.flags')) > 0)",
            (EXT_MIGRATION_KEY,),
        ).fetchone()[0])
        rows = con.execute(
            "SELECT f.value AS name, COUNT(DISTINCT q.id) AS count"
            " FROM questions q, json_each(q.extensions) e,"
            " json_each(json_extract(e.value, '$.value.flags')) f"
            " WHERE json_extract(e.value, '$.key') = ?"
            " GROUP BY f.value ORDER BY count DESC, name ASC",
            (EXT_MIGRATION_KEY,),
        ).fetchall()
        return {
            "total": total,
            "flags": [{"name": row["name"], "count": int(row["count"])} for row in rows],
            "known_flags": list(REVIEW_FLAGS),
        }
    finally:
        con.close()


def _strip_flags(extensions: dict[str, Any], flags: Iterable[str]) -> dict[str, Any]:
    """清掉指定审核标记；一个不剩时连迁移条目一起移出库（不留空壳）。"""
    entry = _extension_value(extensions, EXT_MIGRATION_KEY)
    if not entry:
        return extensions
    remaining = [item for item in (entry.get("flags") or []) if item not in set(flags)]
    result = dict(extensions)
    if remaining:
        result[EXT_MIGRATION_KEY] = {**entry, "flags": remaining}
    else:
        result.pop(EXT_MIGRATION_KEY, None)
    return result


def update_question(plugin_id: str, question_id: str, patch: Any, *,
                    sources: Any = None) -> dict[str, Any]:
    """按题回写可审字段并清除审核标记，合并后仍过同一份契约。

    只接受题目内容与 ``clear_flags``；``id`` / ``meta.created_at`` 不在此通道里改。
    录题插件改题会带上 ``source`` 与 ``sources``：``source`` 是主来源（契约字段），
    ``sources`` 是其余原卷（关系表）；给了 ``sources`` 就整组重挂，没给则保持原样。
    """
    if not isinstance(patch, dict):
        raise question_contract.QuestionValidationError(["(root): 请求体必须是 JSON 对象"])
    extra_sources = _normalize_sources(sources)
    current = get_question(plugin_id, question_id)
    document = dict(current)
    for key in ("stem", "options", "answer", "solution", "type", "difficulty", "grade",
                "taxonomy", "tags", "source", "images"):
        if key not in patch:
            continue
        if key == "source" and patch[key] is None:
            # 老师把主来源清空：显式传 null 才算数（契约里 source 不接受 null 值，
            # 这里只把它当「删除」指令，合并后的文档不会再带这个键）。
            document.pop(key, None)
            continue
        document[key] = patch[key]
    # 改题型时答案形态必须跟着走：选择题的字母改判成非选择题后，那串字母就是答案正文。
    # 留着 choice 形态会被契约的 kind 约束整条拒掉，老师反而改不动——这里保事实，不编内容。
    answer = document.get("answer")
    if isinstance(answer, dict) and answer.get("kind") == "choice" and document["type"] not in CHOICE_TYPES:
        letters = ",".join(item for item in (answer.get("choice_keys") or []) if isinstance(item, str))
        body = letters or str(answer.get("final") or "")
        document["answer"] = {"kind": "text", "content": body, "final": body[:2000]} if body else None
        if document["answer"] is None:
            document.pop("answer")
    document["schema_version"] = normalize_contract_version(document.get("schema_version"))
    document["difficulty"] = normalize_difficulty(document.get("difficulty"))
    document = _intake_document(document, baseline=current)

    clear = patch.get("clear_flags")
    clear = [clear] if isinstance(clear, str) else list(clear or [])
    unknown = [item for item in clear if item not in REVIEW_FLAGS]
    if unknown:
        raise question_contract.QuestionValidationError(
            [f"clear_flags: 未知审核标记 {', '.join(map(repr, unknown))}"]
        )
    extensions = _strip_flags(dict(current.get("extensions") or {}), clear)
    grade = str(document.pop("grade", "") or "")
    if grade:
        extensions[EXT_GRADE_KEY] = {"grade": grade}
    document["extensions"] = extensions
    document["meta"] = {**current["meta"], "updated_at": _now()}

    document = _storage_ready(document)
    question_contract.validate_question(document)

    row = _question_row(document, _now())
    remount = "taxonomy" in patch
    remount_sources = sources is not None or "source" in patch
    con = connect(plugin_id)
    try:
        con.execute("BEGIN IMMEDIATE")
        cursor = con.execute(
            "UPDATE questions SET type = ?, stem = ?, options = ?, answer = ?, solution = ?,"
            " extensions = ?, difficulty = ?, updated_at = ? WHERE id = ?",
            [row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[9], row[0]],
        )
        if cursor.rowcount == 0:
            raise BankNotFound(f"题库中没有题目 {question_id}")
        _fts_upsert(con, question_id, document["stem"])
        if remount:
            _remount_topics(con, question_id, document.get("taxonomy") or {}, _now())
        if remount_sources:
            con.execute("DELETE FROM question_sources WHERE question_id = ?", (question_id,))
            _link_sources(con, document, _now(), extra_sources)
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()
    return get_question(plugin_id, question_id)


def delete_question(plugin_id: str, question_id: str) -> dict[str, Any]:
    """按题号删除一道题（录题插件删题专用，经宿主带令牌转发到这里）。

    只删这道题本身：``question_topics`` / ``question_sources`` 两张关联表靠
    ``ON DELETE CASCADE`` 自动摘干净，共享的来源、学校与大纲节点一律保留——
    删一题不该顺带拆掉别人的考点。删除前确认题目在本库存在，查无即 404。
    """
    if not isinstance(question_id, str) or not question_id.startswith("q_"):
        raise BankNotFound("题目 ID 非法")
    con = connect(plugin_id)
    try:
        con.execute("BEGIN IMMEDIATE")
        try:
            cursor = con.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            if cursor.rowcount == 0:
                raise BankNotFound(f"题库中没有题目 {question_id}")
            _fts_remove(con, question_id)
        except BaseException:
            con.rollback()
            raise
        con.commit()
    finally:
        con.close()
    return {"id": question_id, "deleted": True}

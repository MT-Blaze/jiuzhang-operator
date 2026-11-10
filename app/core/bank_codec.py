"""core-bank 引擎的编解码层：七张关系表 ⇄ ``app/core/question_contract.py`` 标准文档。

存储层与契约的差异全部在这里抹平：``extensions``（库内有序数组 ↔ 契约反向域名对象）、
``answer``（库内单列文本 ↔ 契约对象；库内 NULL 时出参**省略**该字段，不拿字母冒充答案）、
``grade``（库内落在 ``sources.grade``，出参仍给顶层）、``taxonomy``（物化路径树按祖先名还原）、
``images``（寄生在 extensions 的配图条目回到顶层数组）。

出参装配（``_document_from`` / ``_assemble``）也在这里：读路径与写路径共用同一份装配口径，
「列表里看到的」与「取详情拿到的」才不会是两种形状。"""

from __future__ import annotations

import re
import sqlite3
from app.core.bank_schema import (
    CHOICE_TYPES,
    EXTENSION_LABELS,
    EXTENSION_ORDER,
    EXT_GRADE_KEY,
    EXT_IMAGES_KEY,
    EXT_TAGS_KEY,
    EXT_TAXONOMY_KEY,
    LAYER_TAXONOMY_KEY,
    _decode,
    _placeholders,
)
from app.core.contract import CONTRACT_VERSION
from typing import Any, Iterable



# ---------------------------------------------------------------- extensions

def extensions_to_array(extensions: Any) -> list[dict[str, Any]]:
    """契约的对象态 → 库内的有序数组态 ``[{key,label,value}]``。"""
    if not isinstance(extensions, dict):
        return []

    def rank(key: str) -> tuple[int, str]:
        index = EXTENSION_ORDER.index(key) if key in EXTENSION_ORDER else len(EXTENSION_ORDER)
        return (index, key)

    return [
        {"key": key, "label": EXTENSION_LABELS.get(key, key), "value": value}
        for key, value in sorted(extensions.items(), key=lambda item: rank(item[0]))
    ]


def extensions_to_object(raw: Any) -> dict[str, Any]:
    """库内的数组态 → 契约的反向域名对象态；缺 key 的残条目直接丢弃。"""
    items = raw if isinstance(raw, list) else _decode(raw, [])
    result: dict[str, Any] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("key"), str):
            result[item["key"]] = item.get("value")
    return result


def _extension_value(extensions: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = extensions.get(key)
    return value if isinstance(value, dict) else None


def _grade_from(extensions: dict[str, Any]) -> str:
    """年级的取值顺序：底座年级条目 → 录题插件 → 旧库还原。"""
    for key in (EXT_GRADE_KEY, "org.jiuzhang.editor", "org.jiuzhang.legacy"):
        entry = _extension_value(extensions, key)
        if entry and entry.get("grade"):
            return str(entry["grade"])[:20]
    return ""


# -------------------------------------------------------------------- answer

def answer_to_storage(answer: Any, question_type: str) -> str | None:
    """契约答案对象 → 库内单个文本列。

    选择题存字母串（``A,C``）；非选择题存答案正文（``content`` 优先，退回 ``final``）。
    答案形态（text/expression/proof）在存储层不分列，读回统一合成 text。
    """
    if not isinstance(answer, dict):
        return None
    if question_type in CHOICE_TYPES or answer.get("kind") == "choice":
        keys = [item for item in (answer.get("choice_keys") or []) if isinstance(item, str)]
        return ",".join(keys) or None
    body = answer.get("content") or answer.get("final")
    return str(body)[:20000] if body else None


def answer_from_storage(value: str | None, question_type: str) -> dict[str, Any] | None:
    """库内文本 → 契约答案对象；``NULL`` 返回 None，由调用方省略该字段。"""
    if not value:
        return None
    if question_type in CHOICE_TYPES:
        keys = [item for item in re.split(r"[,\s]+", value) if item]
        return {"kind": "choice", "choice_keys": keys, "final": ",".join(keys)}
    return {"kind": "text", "content": value, "final": value[:2000]}


# ---------------------------------------------------------------- 出参装配

def _topic_index(con: sqlite3.Connection, qids: list[str]) -> dict[str, list[dict[str, Any]]]:
    """一题的考向挂载，带物化路径上各级祖先名。"""
    if not qids:
        return {}
    rows = con.execute(
        "SELECT qt.question_id, t.id, t.name, t.path, qt.is_primary"
        " FROM question_topics qt JOIN topics t ON t.id = qt.topic_id"
        f" WHERE qt.question_id IN ({_placeholders(len(qids))})"
        " ORDER BY qt.is_primary DESC, qt.sort_order, t.name",
        qids,
    ).fetchall()
    linked: dict[str, list[dict[str, Any]]] = {}
    ancestor_ids: set[str] = set()
    for row in rows:
        item = dict(row)
        item["ancestor_ids"] = [part for part in row["path"].split("/") if part]
        linked.setdefault(row["question_id"], []).append(item)
        ancestor_ids.update(item["ancestor_ids"])
    names: dict[str, str] = {}
    if ancestor_ids:
        ids = sorted(ancestor_ids)
        for row in con.execute(
            f"SELECT id, name FROM topics WHERE id IN ({_placeholders(len(ids))})", ids
        ):
            names[row["id"]] = row["name"]
    for items in linked.values():
        for item in items:
            item["ancestors"] = [
                {"id": pid, "name": names.get(pid, "")} for pid in item["ancestor_ids"]
            ]
    return linked


def _source_index(con: sqlite3.Connection, qids: list[str]) -> dict[str, dict[str, Any]]:
    """一题的首个来源（含学校与年级）；一题多来源的完整展开属于 P1 录题升级范围。"""
    if not qids:
        return {}
    rows = con.execute(
        "SELECT qs.question_id, qs.question_no, s.paper_name, s.year, s.exam_type, s.grade,"
        " s.school_id, sc.full_name, sc.short_name, sc.city, sc.province"
        " FROM question_sources qs"
        " JOIN sources s ON s.id = qs.source_id"
        " LEFT JOIN schools sc ON sc.id = s.school_id"
        f" WHERE qs.question_id IN ({_placeholders(len(qids))})"
        " ORDER BY qs.id",
        qids,
    ).fetchall()
    picked: dict[str, dict[str, Any]] = {}
    for row in rows:
        picked.setdefault(row["question_id"], dict(row))
    return picked


def _taxonomy_from_links(links: list[dict[str, Any]]) -> dict[str, Any]:
    """层名取主挂载，``topic_ids`` 必须带上**全部**挂载。

    插件是「读—改—写」：读回来的 taxonomy 会原样回传，这里少列一个副考向，
    保存时 ``_remount_topics`` 就先 DELETE 再按入参重插，副挂载就此静默消失。
    """
    taxonomy: dict[str, Any] = {}
    for node in links[0]["ancestors"]:
        field = LAYER_TAXONOMY_KEY.get(node["id"][3:5])
        if field and node["name"]:
            taxonomy[field] = node["name"]
    taxonomy["topic_ids"] = list(dict.fromkeys(link["id"] for link in links))
    return taxonomy


def _document_from(row: sqlite3.Row, links: list[dict[str, Any]],
                   source: dict[str, Any] | None) -> dict[str, Any]:
    extensions = extensions_to_object(row["extensions"])
    document: dict[str, Any] = {
        "schema_version": CONTRACT_VERSION,
        "id": row["id"],
        "type": row["type"],
        "stem": row["stem"],
        "difficulty": row["difficulty"],
    }
    options = _decode(row["options"], [])
    if options:
        document["options"] = options
    answer = answer_from_storage(row["answer"], row["type"])
    if answer:
        document["answer"] = answer
    if row["solution"]:
        document["solution"] = row["solution"]

    if links:
        document["taxonomy"] = _taxonomy_from_links(links)
    else:
        legacy_tax = _extension_value(extensions, EXT_TAXONOMY_KEY)
        if legacy_tax:
            document["taxonomy"] = {
                key: value
                for key, value in legacy_tax.items()
                if key in ("textbook", "chapter", "section", "topic") and value
            }
    images = _extension_value(extensions, EXT_IMAGES_KEY)
    if images and images.get("images"):
        from app.core.tikz_render import resolve_images

        document["images"] = resolve_images(images["images"])
    stored_tags = _extension_value(extensions, EXT_TAGS_KEY)
    if stored_tags and stored_tags.get("tags"):
        document["tags"] = stored_tags["tags"]

    grade = ""
    if source:
        grade = source["grade"] or ""
        document["source"] = {
            "paper_title": source["paper_name"],
            "question_no": source["question_no"],
        }
        if source["year"] is not None:
            document["source"]["year"] = int(source["year"])
        for field, column in (("exam_type", "exam_type"), ("school", "short_name"),
                              ("region", "city")):
            value = source.get(column)
            if value:
                document["source"][field] = value
        if source.get("school_id"):
            document["source"]["school_id"] = str(source["school_id"])
    if not grade:
        grade = _grade_from(extensions)
    if grade:
        document["grade"] = grade
    document["extensions"] = extensions
    document["meta"] = {
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "revision": 1,
        "status": "published",
    }
    return document


def _assemble(con: sqlite3.Connection, rows: Iterable[sqlite3.Row]) -> list[dict[str, Any]]:
    row_list = list(rows)
    qids = [row["id"] for row in row_list]
    topics_by_qid = _topic_index(con, qids)
    sources_by_qid = _source_index(con, qids)
    return [
        _document_from(row, topics_by_qid.get(row["id"]) or [], sources_by_qid.get(row["id"]))
        for row in row_list
    ]

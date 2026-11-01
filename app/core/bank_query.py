"""core-bank 引擎的读路径：过滤条件装配、分页检索、大纲树与统计。

安全边界全压在这一步：所有过滤条件走参数绑定，表名/列名/层别码只从常量取；
``_escape_like`` 把 LIKE 的通配符按字面量处理；题干检索走 FTS5 索引，
索引不可用时退回 ``LIKE``（口径不变，只是慢）。单页上限、搜索词上限由地基层的常量钉死。

装配一律批量做（``_assemble`` + ``_topic_index`` + ``_source_index``）：
一页 100 道题只发三条 SQL，绝不 per-row 查库。"""

from __future__ import annotations

import json
import sqlite3
from app.core import bank_fts, pinyin, question_parser
from app.core.bank_codec import _assemble
from app.core.bank_schema import (
    ASSEMBLE_CHUNK,
    BankError,
    BankNotFound,
    EXT_MIGRATION_KEY,
    EXT_TAGS_KEY,
    LAYER_TAXONOMY_KEY,
    MAX_BASKET,
    MAX_PAGE_SIZE,
    MAX_SEARCH,
    MAX_SEARCH_NODES,
    REVIEW_FLAGS,
    TEXTBOOK_ID_RE,
    TOPIC_ID_RE,
    _like,
    _placeholders,
    connect,
)
from app.core.contract import normalize_difficulty
from typing import Any, Iterable



def _topic_name_match(con: sqlite3.Connection, term: str) -> tuple[str, list[Any]]:
    """考向搜索的 WHERE 片段：原文之外再给一条拼音首字母的路。

    老师敲一个 ``J`` 想捞「集合」——库里存的是汉字，只能现算首字母。
    打了汉字就不开这条路：「模」会把 AMC 端上桌（amc 里也有个 m）。
    ``py_initials()`` 走不了索引，但考向树只有几千个节点，一次全表扫不过几毫秒。
    """
    clauses = ["name LIKE ? ESCAPE '\\'"]
    args: list[Any] = [_like(term)]
    key = pinyin.initials(term) if term.isascii() else ""
    if key:
        con.create_function("py_initials", 1, pinyin.initials, deterministic=True)
        clauses.append("py_initials(name) LIKE ? ESCAPE '\\'")
        args.append(_like(key))
    return "(" + " OR ".join(clauses) + ")", args


# ---------------------------------------------------------------- 过滤与读取

def _flag_clause(flag: str) -> tuple[str, list[Any]]:
    """按灌库审核标记筛题；``any`` 表示「带任何未清标记」，即整条待审队列。"""
    if flag == "any":
        return (
            "EXISTS (SELECT 1 FROM json_each(q.extensions) e"
            " WHERE json_extract(e.value, '$.key') = ?"
            " AND json_array_length(json_extract(e.value, '$.value.flags')) > 0)",
            [EXT_MIGRATION_KEY],
        )
    if flag not in REVIEW_FLAGS:
        raise BankError(f"未知审核标记 {flag!r}，只认 any/{'/'.join(REVIEW_FLAGS)}")
    return (
        "EXISTS (SELECT 1 FROM json_each(q.extensions) e"
        " WHERE json_extract(e.value, '$.key') = ?"
        " AND EXISTS (SELECT 1 FROM json_each(json_extract(e.value, '$.value.flags')) f"
        "             WHERE f.value = ?))",
        [EXT_MIGRATION_KEY, flag],
    )


# ---------------------------------------------------------------- 题干索引

def _fts_ready(con: sqlite3.Connection) -> bool:
    """确保 FTS5 索引存在且条数与主表一致；任何失败都让调用方退回 LIKE。

    懒重建只发生在读路径：索引是派生数据，丢了可以随时从 questions 重建，
    绝不能因为索引坏了让题库打不开。
    """
    if not bank_fts.available():
        return False
    try:
        bank_fts.ensure_schema(con)
        total = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        if int(bank_fts.doc_count(con)) != total:
            bank_fts.index_all(con, con.execute("SELECT id, stem FROM questions"))
        return True
    except (bank_fts.FtsUnavailable, sqlite3.DatabaseError):
        return False


def _fts_upsert(con: sqlite3.Connection, question_id: str, stem: str) -> None:
    if not bank_fts.available():
        return
    try:
        bank_fts.upsert(con, question_id, stem)
    except (bank_fts.FtsUnavailable, sqlite3.DatabaseError):
        pass


def _fts_remove(con: sqlite3.Connection, question_id: str) -> None:
    if not bank_fts.available():
        return
    try:
        bank_fts.remove(con, question_id)
    except (bank_fts.FtsUnavailable, sqlite3.DatabaseError):
        pass


def _fts_clear(con: sqlite3.Connection) -> None:
    if not bank_fts.available():
        return
    try:
        bank_fts.ensure_schema(con)
        con.execute(f"DELETE FROM {bank_fts.TABLE}")
    except (bank_fts.FtsUnavailable, sqlite3.DatabaseError):
        pass


def _search_extra_clause(term: str) -> tuple[str, list[Any]]:
    """题干以外的命中口径：标签（含隐藏标签）与来源（卷名 / 考试类型 / 学校）。

    「搜哈三中能搜出三省六校那道题」靠的就是这一段：明细学校拆成隐藏标签
    存在标签里，题干里当然搜不到，但标签里在。
    """
    sql = (
        "(EXISTS (SELECT 1 FROM json_each(q.extensions) e"
        " WHERE json_extract(e.value, '$.key') = ?"
        " AND json_extract(e.value, '$.value.tags') LIKE ? ESCAPE '\\')"
        " OR EXISTS (SELECT 1 FROM question_sources qs"
        " JOIN sources s ON s.id = qs.source_id"
        " LEFT JOIN schools sc ON sc.id = s.school_id"
        " WHERE qs.question_id = q.id"
        " AND (s.paper_name LIKE ? ESCAPE '\\'"
        " OR s.exam_type LIKE ? ESCAPE '\\'"
        " OR sc.full_name LIKE ? ESCAPE '\\'"
        " OR sc.short_name LIKE ? ESCAPE '\\')))"
    )
    params = [EXT_TAGS_KEY, _like(term), _like(term), _like(term), _like(term), _like(term)]
    return sql, params


def _build_where(
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    chapter: str = "",
    textbook: str = "",
    search: str = "",
    flag: str = "",
    fts: bool = False,
) -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    values = {
        "grade": str(grade or "").strip(),
        "difficulty": str(normalize_difficulty(difficulty) or "").strip(),
        "type": str(question_type or "").strip(),
        "chapter": str(chapter or "").strip(),
        "textbook": str(textbook or "").strip(),
    }
    if values["difficulty"] and values["difficulty"] != "全部":
        where.append("q.difficulty = ?")
        params.append(values["difficulty"][:8])
    if values["type"] and values["type"] != "全部":
        where.append("q.type = ?")
        params.append(values["type"][:32])
    if values["grade"] and values["grade"] != "全部":
        where.append(
            "EXISTS (SELECT 1 FROM question_sources qs"
            " JOIN sources s ON s.id = qs.source_id"
            " WHERE qs.question_id = q.id AND s.grade = ?)"
        )
        params.append(values["grade"][:20])
    for value, layer in ((values["chapter"], "tp_ch"), (values["textbook"], "tp_bo")):
        if value and value != "全部":
            where.append(
                "EXISTS (SELECT 1 FROM question_topics qt"
                " JOIN topics node ON node.id = qt.topic_id"
                " JOIN topics ancestor ON ancestor.path = node.path"
                " OR node.path LIKE ancestor.path || '/%'"
                f" WHERE qt.question_id = q.id AND substr(ancestor.id, 1, 5) = '{layer}'"
                " AND ancestor.name = ?)"
            )
            params.append(value[:64])
    term = str(search or "").strip()[:MAX_SEARCH]
    if term:
        extra_sql, extra_params = _search_extra_clause(term)
        if fts:
            where.append(
                f"(q.id IN (SELECT question_id FROM {bank_fts.TABLE}"
                f" WHERE {bank_fts.TABLE} MATCH ?) OR q.id = ? OR {extra_sql})"
            )
            params.extend([bank_fts.query_expression(term), term])
        else:
            where.append(f"(q.stem LIKE ? ESCAPE '\\' OR q.id = ? OR {extra_sql})")
            params.extend([_like(term), term])
        params.extend(extra_params)
    if flag:
        flag_sql, flag_params = _flag_clause(flag)
        where.append(flag_sql)
        params.extend(flag_params)
    clause = "WHERE " + " AND ".join(where) if where else ""
    return clause, params


def _topic_subtree_sql(con: sqlite3.Connection, topic: str) -> tuple[str, list[Any]]:
    """按大纲节点取题：点节/章/册时把它子树里的题一并捞出来。

    物化路径只有册节点等于自身 id，章/节/考向的 path 是「祖先 id/…/自身 id」，
    所以必须先把 path 查出来当前缀，不能拿 id 直接比。节点 id 由 TOPIC_ID_RE
    严格校验、不含 LIKE 通配符，直接拼前缀即可；节点 id 定长且都以 "tp_" 开头，
    前缀匹配不会误伤兄弟子树。
    """
    if TOPIC_ID_RE.fullmatch(topic) is None:
        raise BankError("考向节点 ID 非法")
    row = con.execute("SELECT path FROM topics WHERE id = ?", (topic,)).fetchone()
    if row is None:
        raise BankNotFound(f"大纲里没有节点 {topic}")
    return (
        "EXISTS (SELECT 1 FROM question_topics qt JOIN topics node ON node.id = qt.topic_id"
        " WHERE qt.question_id = q.id AND (node.path = ? OR node.path LIKE ?))",
        [row["path"], row["path"] + "/%"],
    )


def list_questions(
    plugin_id: str,
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    chapter: str = "",
    textbook: str = "",
    topic: str = "",
    search: str = "",
    flag: str = "",
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[dict[str, Any]], int]:
    page = max(1, int(page))
    page_size = max(1, min(int(page_size), MAX_PAGE_SIZE))
    con = connect(plugin_id)
    try:
        use_fts = bool(str(search or "").strip()) and _fts_ready(con)
        clause, params = _build_where(
            grade=grade, difficulty=difficulty, question_type=question_type,
            chapter=chapter, textbook=textbook, search=search, flag=flag,
            fts=use_fts,
        )
        if topic:
            scope, scope_params = _topic_subtree_sql(con, topic)
            clause = f"{clause} AND {scope}" if clause else f"WHERE {scope}"
            params.extend(scope_params)
        total = int(con.execute(f"SELECT COUNT(*) FROM questions q {clause}", params).fetchone()[0])
        rows = con.execute(
            f"SELECT q.* FROM questions q {clause} ORDER BY q.id LIMIT ? OFFSET ?",
            [*params, page_size, (page - 1) * page_size],
        ).fetchall()
        return _assemble(con, rows), total
    finally:
        con.close()


def export_documents(plugin_id: str) -> list[dict[str, Any]]:
    """导出当前工作区题库的全部题目（标准结构，按 ID 排序）。

    走读路径装配而不是直接读表：出参必须与题库浏览器、组卷插件看到的是同一份口径，
    否则导出的文件再导入回来就会变形。
    """
    documents: list[dict[str, Any]] = []
    page = 1
    while True:
        items, total = list_questions(plugin_id, page=page, page_size=MAX_PAGE_SIZE)
        documents.extend(items)
        if not items or len(documents) >= total:
            return documents
        page += 1


def get_question(plugin_id: str, question_id: str) -> dict[str, Any]:
    if not isinstance(question_id, str) or not question_id.startswith("q_"):
        raise BankNotFound("题目 ID 非法")
    con = connect(plugin_id)
    try:
        row = con.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
        if row is None:
            raise BankNotFound(f"题库中没有题目 {question_id}")
        return _assemble(con, [row])[0]
    finally:
        con.close()


def question_sources(plugin_id: str, question_id: str) -> dict[str, Any]:
    """一题挂的全部原卷（一题多卷，各自带原卷题号），按挂载先后返回。"""
    if not isinstance(question_id, str) or not question_id.startswith("q_"):
        raise BankNotFound("题目 ID 非法")
    con = connect(plugin_id)
    try:
        if con.execute("SELECT 1 FROM questions WHERE id = ?", (question_id,)).fetchone() is None:
            raise BankNotFound(f"题库中没有题目 {question_id}")
        rows = con.execute(
            "SELECT s.id AS source_id, s.paper_name, s.year, s.exam_type, s.grade,"
            " qs.question_no, sc.full_name, sc.short_name, sc.city, sc.province"
            " FROM question_sources qs"
            " JOIN sources s ON s.id = qs.source_id"
            " LEFT JOIN schools sc ON sc.id = s.school_id"
            " WHERE qs.question_id = ? ORDER BY qs.id",
            (question_id,),
        ).fetchall()
    finally:
        con.close()
    items: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {
            "source_id": row["source_id"],
            "paper_title": row["paper_name"],
            "question_no": row["question_no"],
            "grade": row["grade"],
        }
        if row["year"] is not None:
            item["year"] = int(row["year"])
        for field, column in (("exam_type", "exam_type"), ("school", "short_name"),
                              ("region", "city")):
            value = row[column]
            if value:
                item[field] = value
        items.append(item)
    return {"question_id": question_id, "items": items}


def get_many(plugin_id: str, ids: Iterable[str]) -> list[dict[str, Any]]:
    wanted = [item for item in ids if isinstance(item, str) and item.startswith("q_")][:MAX_BASKET]
    if not wanted:
        return []
    con = connect(plugin_id)
    try:
        rows = con.execute(
            f"SELECT * FROM questions WHERE id IN ({_placeholders(len(wanted))})", wanted
        ).fetchall()
        documents = _assemble(con, rows)
    finally:
        con.close()
    by_id = {document["id"]: document for document in documents}
    return [by_id[item] for item in wanted if item in by_id]


def assemble_ids(plugin_id: str, ids: Iterable[str]) -> list[dict[str, Any]]:
    """按 ID 批量装配标准结构全文，条数不受题篮上限约束（查重引擎一次要拿一整组）。

    与 ``get_many`` 的差别只在容量与顺序：那条按题篮顺序回、卡 MAX_BASKET；
    这条按分片拼 ``IN``，避开 SQLite 单条语句的变量数上限，返回顺序不保证、
    调用方自己按 id 索引。
    """
    wanted = [item for item in ids if isinstance(item, str) and item.startswith("q_")]
    if not wanted:
        return []
    documents: list[dict[str, Any]] = []
    con = connect(plugin_id)
    try:
        for start in range(0, len(wanted), ASSEMBLE_CHUNK):
            batch = wanted[start:start + ASSEMBLE_CHUNK]
            rows = con.execute(
                f"SELECT * FROM questions WHERE id IN ({_placeholders(len(batch))})", batch
            ).fetchall()
            documents.extend(_assemble(con, rows))
    finally:
        con.close()
    return documents


def random_question(
    plugin_id: str,
    *,
    grade: str = "",
    difficulty: str = "",
    question_type: str = "",
    chapter: str = "",
    textbook: str = "",
    topic: str = "",
    search: str = "",
) -> dict[str, Any] | None:
    clause, params = "", []
    con = connect(plugin_id)
    try:
        clause, params = _build_where(
            grade=grade, difficulty=difficulty, question_type=question_type,
            chapter=chapter, textbook=textbook, search=search,
            fts=bool(str(search or "").strip()) and _fts_ready(con),
        )
        if topic:
            scope, scope_params = _topic_subtree_sql(con, topic)
            clause = f"{clause} AND {scope}" if clause else f"WHERE {scope}"
            params.extend(scope_params)
        row = con.execute(
            f"SELECT q.* FROM questions q {clause} ORDER BY RANDOM() LIMIT 1", params
        ).fetchone()
        if row is None:
            return None
        return _assemble(con, [row])[0]
    finally:
        con.close()


def _grouped_counts(con: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    return [
        {"name": row["name"], "count": int(row["count"]), "id": row["id"]}
        for row in con.execute(sql, params)
    ]


def stats(plugin_id: str) -> dict[str, Any]:
    """出参键名与 v0.6.2 一致（total/grades/difficulties/types/chapters/textbooks）。"""
    con = connect(plugin_id)
    try:
        total = int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])

        def column_grouped(column: str, limit: int) -> list[dict[str, Any]]:
            return _grouped_counts(
                con,
                f"SELECT '' AS id, {column} AS name, COUNT(*) AS count FROM questions"
                f" GROUP BY {column} ORDER BY count DESC, name ASC LIMIT ?",
                (limit,),
            )

        grades = _grouped_counts(
            con,
            "SELECT '' AS id, s.grade AS name, COUNT(DISTINCT qs.question_id) AS count"
            " FROM question_sources qs JOIN sources s ON s.id = qs.source_id"
            " WHERE s.grade <> '' GROUP BY s.grade ORDER BY count DESC, name ASC LIMIT 40",
        )
        # 大纲层的题量是子树之和：题目只挂在末级节点上
        outline = (
            "SELECT ancestor.id AS id, ancestor.name AS name,"
            " COUNT(DISTINCT qt.question_id) AS count"
            " FROM topics ancestor"
            " LEFT JOIN topics descendant ON descendant.path LIKE ancestor.path || '/%'"
            " LEFT JOIN question_topics qt ON qt.topic_id = descendant.id"
            " WHERE substr(ancestor.id, 1, 5) = ?"
            " GROUP BY ancestor.id ORDER BY count DESC, name ASC LIMIT ?"
        )
        return {
            "total": total,
            "grades": grades,
            "difficulties": column_grouped("difficulty", 40),
            "types": column_grouped("type", 40),
            "chapters": _grouped_counts(con, outline, ("tp_ch", 30)),
            "textbooks": _grouped_counts(con, outline, ("tp_bo", 40)),
        }
    finally:
        con.close()


def topics(
    plugin_id: str, *, parent_id: str = "", search: str = "", textbook_id: str = ""
) -> list[dict[str, Any]]:
    """大纲树的一层子节点（懒展开用），带题量、是否有下级与教研笔记条数。

    ``textbook_id`` 只约束**根层与搜索结果**：册/章/节是版本目录节点，选哪版就看哪版；
    考向（``tp_kx``）是全库并集、``textbook_id IS NULL``，永远随版本一起出现。
    给定 ``parent_id`` 时不再过滤——父节点本身已确定了版本身份。
    """
    if textbook_id and TEXTBOOK_ID_RE.fullmatch(textbook_id) is None:
        raise BankError("教材版本 ID 非法")
    con = connect(plugin_id)
    try:
        term = str(search or "").strip()[:MAX_SEARCH]
        fields = "id, parent_id, textbook_id, name, path, sort_order, status"
        if term:
            match, match_args = _topic_name_match(con, term)
            scope = " AND (textbook_id = ? OR textbook_id IS NULL)" if textbook_id else ""
            tail_args: list[Any] = [textbook_id] if textbook_id else []
            rows = con.execute(
                f"SELECT {fields} FROM topics"
                f" WHERE {match}{scope}"
                " ORDER BY path LIMIT ?",
                (*match_args, *tail_args, MAX_SEARCH_NODES),
            ).fetchall()
        elif parent_id:
            if TOPIC_ID_RE.fullmatch(parent_id) is None:
                raise BankError("考向节点 ID 非法")
            rows = con.execute(
                f"SELECT {fields} FROM topics"
                " WHERE parent_id = ? ORDER BY sort_order, name",
                (parent_id,),
            ).fetchall()
        elif textbook_id:
            rows = con.execute(
                f"SELECT {fields} FROM topics"
                " WHERE parent_id IS NULL AND textbook_id = ? ORDER BY sort_order, name",
                (textbook_id,),
            ).fetchall()
        else:
            rows = con.execute(
                f"SELECT {fields} FROM topics"
                " WHERE parent_id IS NULL ORDER BY sort_order, name"
            ).fetchall()
        result = []
        for row in rows:
            children = int(con.execute(
                "SELECT COUNT(*) FROM topics WHERE parent_id = ?", (row["id"],)
            ).fetchone()[0])
            mounted = int(con.execute(
                "SELECT COUNT(DISTINCT qt.question_id) FROM question_topics qt"
                " JOIN topics descendant ON descendant.id = qt.topic_id"
                " WHERE descendant.path = ? OR descendant.path LIKE ?",
                (row["path"], row["path"] + "/%"),
            ).fetchone()[0])
            notes = int(con.execute(
                "SELECT COUNT(*) FROM topic_notes WHERE topic_id = ?", (row["id"],)
            ).fetchone()[0])
            result.append({
                "id": row["id"],
                "parent_id": row["parent_id"],
                "textbook_id": row["textbook_id"],
                "name": row["name"],
                "layer": LAYER_TAXONOMY_KEY.get(row["id"][3:5], ""),
                "path": row["path"],
                "sort_order": int(row["sort_order"]),
                "status": row["status"],
                "has_children": children > 0,
                "question_count": mounted,
                "note_count": notes,
            })
        return result
    finally:
        con.close()


def topic_notes(plugin_id: str, topic_id: str) -> dict[str, Any]:
    """考向节点上的教研笔记（method/pitfall/knowledge/insight）。"""
    if TOPIC_ID_RE.fullmatch(topic_id) is None:
        raise BankError("考向节点 ID 非法")
    con = connect(plugin_id)
    try:
        node = con.execute(
            "SELECT id, name, path, status FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if node is None:
            raise BankNotFound(f"大纲里没有节点 {topic_id}")
        rows = con.execute(
            "SELECT id, note_type, content, sort_order FROM topic_notes"
            " WHERE topic_id = ? ORDER BY note_type, sort_order",
            (topic_id,),
        ).fetchall()
        return {
            "topic": {
                "id": node["id"], "name": node["name"],
                "path": node["path"], "status": node["status"],
            },
            "notes": [
                {
                    "id": int(row["id"]),
                    "note_type": row["note_type"],
                    # 存量 150 条笔记里 141 条是旧导入器写的 \(...\)，而契约只认 $...$。
                    # 读出时过一遍底座唯一的清洗函数：各插件不必自造公式方言，老师库里的原文也不动。
                    "content": question_parser.normalize_latex(row["content"]),
                    "sort_order": int(row["sort_order"]),
                }
                for row in rows
            ],
        }
    finally:
        con.close()


def import_count(plugin_id: str) -> int:
    con = connect(plugin_id)
    try:
        return int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
    finally:
        con.close()


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

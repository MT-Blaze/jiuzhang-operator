"""四栏联动 DAO（阶段三）：章节树 → 章节知识点 → 考向 → 辅助知识点标签。

铁律对照：
- 每条 SQL 只碰一张表；桥表查关联、维度表查本体，跨表拼装在 Python 层完成；
- 表名 / 列名全部来自下方白名单常量，值一律 ``?`` 占位，不用 f-string 拼 SQL；
- 删除考向沿用阶段二防呆：先查外键引用（排除当前知识点自己的关联行），
  仍被引用即抛 ReferencedError，由 API 换成 409。

sort_order 口径（v9 起）：
- chapter_knowledge_map.sort_order：章节内知识点顺序，按 chapter_id 分组，0..n-1；
- knowledge_exam_map.sort_order：0 = 考向归属该知识点（主关联），>=1 = 辅助标签顺序，
  按 exam_direction_id 分组；辅助标签只读 >0 且排除当前主知识点，绝不把自己挂回自己；
- 拖拽排序提交完整成员清单，集合不一致即拒绝，防止误丢关联。
"""

from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from app.bank_engine import dao_base, dao_console, dao_dimensions
from app.bank_engine.dao_console import ConflictError, ConsoleLookupError, ReferencedError
from app.bank_engine.models import (
    ChapterNode,
    ExamDirection,
    LinkedKnowledgePoint,
    TextbookTree,
)

# knowledge_exam_map.sort_order 的主次口径（v9 起明确）：
# 0 = 该考向归属当前知识点（主关联，不参与辅助标签展示/排序）；
# >=1 = 辅助知识点标签，按 1..n 排序。
PRIMARY_ORDER = 0

# 联动键 → (桥表, 分组列, 成员列)：白名单常量，排序 API 只认这两个键。
LINK_MAPS: dict[str, tuple[str, str, str]] = {
    "chapter_points": ("chapter_knowledge_map", "chapter_id", "knowledge_point_id"),
    "direction_tags": ("knowledge_exam_map", "exam_direction_id", "knowledge_point_id"),
}


def _map_spec(map_key: str) -> tuple[str, str, str]:
    spec = LINK_MAPS.get(map_key)
    if spec is None:
        raise ConsoleLookupError("未知的联动表：" + str(map_key))
    return spec


def _require(conn: sqlite3.Connection, table: str, row_id: int) -> None:
    row = conn.execute("SELECT 1 FROM " + table + " WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise ConsoleLookupError("行不存在：" + table + "#" + str(row_id))


def chapter_tree(conn: sqlite3.Connection, textbook_id: int) -> tuple[ChapterNode, ...]:
    """整本教材的章节一次单表读出，父子层级在 Python 层组装。"""
    _require(conn, "dim_textbooks", textbook_id)
    chapters = dao_dimensions.list_chapters(conn, textbook_id, roots_only=False)
    children: dict[int | None, list[Any]] = {}
    for chapter in chapters:
        children.setdefault(chapter.parent_id, []).append(chapter)

    def build(chapter: Any) -> ChapterNode:
        return ChapterNode(chapter, tuple(build(child) for child in children.get(chapter.id, ())))

    return tuple(build(root) for root in children.get(None, ()))


def version_tree(conn: sqlite3.Connection, version_id: int) -> tuple[TextbookTree, ...]:
    """版本 → 册次 → 章 → 节：每册单表读章节，层级在 Python 层组装。"""
    _require(conn, "dim_textbook_versions", version_id)
    books = dao_dimensions.list_textbooks(conn, version_id=version_id)
    return tuple(
        TextbookTree(textbook=book, chapters=chapter_tree(conn, book.id))
        for book in books
    )


def _linked_points(
    conn: sqlite3.Connection,
    map_key: str,
    group_id: int,
    *,
    exclude_point_id: int | None = None,
) -> tuple[LinkedKnowledgePoint, ...]:
    table, group_col, member_col = _map_spec(map_key)
    clauses = [group_col + " = ?"]
    params: list[Any] = [group_id]
    if map_key == "direction_tags":
        clauses.append("sort_order > ?")
        params.append(PRIMARY_ORDER)
        if exclude_point_id is not None:
            clauses.append(member_col + " <> ?")
            params.append(int(exclude_point_id))
    rows = conn.execute(
        "SELECT " + member_col + ", sort_order FROM " + table
        + " WHERE " + " AND ".join(clauses)
        + " ORDER BY sort_order, " + member_col,
        params,
    ).fetchall()
    points = dao_base.load_knowledge_points(conn, [int(row[0]) for row in rows])
    out: list[LinkedKnowledgePoint] = []
    for row in rows:
        point = points.get(int(row[0]))
        if point is None:
            continue
        out.append(LinkedKnowledgePoint(
            id=point.id, name=point.name, code=point.code,
            subject_id=point.subject_id, parent_id=point.parent_id,
            sort_order=int(row[1]),
        ))
    return tuple(out)


def chapter_points(conn: sqlite3.Connection, chapter_id: int) -> tuple[LinkedKnowledgePoint, ...]:
    _require(conn, "dim_textbook_chapters", chapter_id)
    return _linked_points(conn, "chapter_points", chapter_id)


def direction_tags(
    conn: sqlite3.Connection,
    direction_id: int,
    *,
    exclude_point_id: int | None = None,
) -> tuple[LinkedKnowledgePoint, ...]:
    """辅助知识点标签：只取 sort_order>0，且排除当前选中的主知识点。"""
    _require(conn, "dim_exam_directions", direction_id)
    return _linked_points(
        conn, "direction_tags", direction_id, exclude_point_id=exclude_point_id
    )


def point_directions(conn: sqlite3.Connection, point_id: int) -> tuple[ExamDirection, ...]:
    """知识点自己的考向：只认 sort_order=0 的归属关系，辅助关联不算。"""
    _require(conn, "dim_knowledge_points", point_id)
    rows = conn.execute(
        "SELECT exam_direction_id FROM knowledge_exam_map "
        "WHERE knowledge_point_id = ? AND sort_order = ?",
        (point_id, PRIMARY_ORDER),
    ).fetchall()
    directions = dao_base.load_exam_directions(conn, [int(row[0]) for row in rows])
    return tuple(sorted(directions.values(), key=lambda item: (item.sort_order, item.id)))


def _order_members(
    conn: sqlite3.Connection, map_key: str, group_id: int
) -> list[tuple[int, int]]:
    """排序分组的现有成员（成员 id, sort_order）：辅助标签组只含 >0 的行。"""
    table, group_col, member_col = _map_spec(map_key)
    clauses = [group_col + " = ?"]
    params: list[Any] = [group_id]
    if map_key == "direction_tags":
        clauses.append("sort_order > ?")
        params.append(PRIMARY_ORDER)
    rows = conn.execute(
        "SELECT " + member_col + ", sort_order FROM " + table
        + " WHERE " + " AND ".join(clauses)
        + " ORDER BY sort_order, " + member_col,
        params,
    ).fetchall()
    return [(int(row[0]), int(row[1])) for row in rows]


def reorder(
    conn: sqlite3.Connection,
    map_key: str,
    group_id: int,
    member_ids: list[int],
    *,
    exclude_point_id: int | None = None,
) -> None:
    """拖拽排序落库：提交的清单必须与现有成员完全一致（不多不少不重）。

    辅助标签组从 1 起编号，0 永远留给主关联；被当前主知识点排除的行
    不进清单、排在最后，保证组内编号仍连续。
    """
    _map_spec(map_key)
    if not isinstance(member_ids, list) or any(
        not isinstance(value, int) or isinstance(value, bool) for value in member_ids
    ):
        raise ValueError("排序清单必须是整数 id 数组")
    members = _order_members(conn, map_key, group_id)
    hidden: list[int] = []
    if map_key == "direction_tags" and exclude_point_id is not None:
        hidden = [member for member, _ in members if member == int(exclude_point_id)]
        members = [item for item in members if item[0] != int(exclude_point_id)]
    existing = {member for member, _ in members}
    if len(member_ids) != len(existing) or set(member_ids) != existing:
        raise ValueError("排序清单与现有条目不一致：请先刷新再拖拽")
    table, group_col, member_col = _map_spec(map_key)
    start = 1 if map_key == "direction_tags" else 0
    ordered = member_ids + hidden
    try:
        conn.executemany(
            "UPDATE " + table + " SET sort_order = ? WHERE "
            + group_col + " = ? AND " + member_col + " = ?",
            [(order, group_id, member)
             for order, member in enumerate(ordered, start=start)],
        )
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise


def add_direction(conn: sqlite3.Connection, point_id: int, name: str) -> ExamDirection:
    """新增考向并挂到当前知识点：学科继承知识点，编码自动签发。"""
    _require(conn, "dim_knowledge_points", point_id)
    clean = str(name or "").strip()
    if not clean:
        raise ValueError("考向名称不能为空")
    point = dao_base.load_knowledge_points(conn, [point_id])[point_id]
    next_order = int(conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 FROM dim_exam_directions WHERE subject_id = ?",
        (point.subject_id,),
    ).fetchone()[0])
    code = "tp_u" + uuid.uuid4().hex[:12]
    try:
        cursor = conn.execute(
            "INSERT INTO dim_exam_directions (name, code, sort_order, subject_id) "
            "VALUES (?, ?, ?, ?)",
            (clean, code, next_order, point.subject_id),
        )
        direction_id = int(cursor.lastrowid)
        conn.execute(
            "INSERT INTO knowledge_exam_map "
            "(knowledge_point_id, exam_direction_id, sort_order) VALUES (?, ?, 0)",
            (point_id, direction_id),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ConflictError("考向名称同学科内已存在，或约束冲突（" + str(exc) + "）") from exc
    except sqlite3.Error:
        conn.rollback()
        raise
    return dao_base.load_exam_directions(conn, [direction_id])[direction_id]


def delete_direction(conn: sqlite3.Connection, point_id: int, direction_id: int) -> None:
    """删除考向：先解除当前知识点的关联，再查其余引用；仍被引用即 409 防呆。"""
    _require(conn, "dim_exam_directions", direction_id)
    link = conn.execute(
        "SELECT 1 FROM knowledge_exam_map WHERE knowledge_point_id = ? AND exam_direction_id = ?",
        (point_id, direction_id),
    ).fetchone()
    if link is None:
        raise ConsoleLookupError("该知识点下没有这个考向")
    hits = dao_console.find_references(
        conn, "dim_exam_directions", direction_id,
        exclude={"knowledge_exam_map": ("knowledge_point_id", point_id)},
    )
    if hits:
        raise ReferencedError(hits)
    try:
        conn.execute(
            "DELETE FROM knowledge_exam_map WHERE knowledge_point_id = ? AND exam_direction_id = ?",
            (point_id, direction_id),
        )
        conn.execute("DELETE FROM dim_exam_directions WHERE id = ?", (direction_id,))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise


def add_tag(conn: sqlite3.Connection, direction_id: int, point_id: int) -> LinkedKnowledgePoint:
    """全局搜索到的知识点挂为考向辅助标签：排到末尾，重复挂载即冲突。"""
    _require(conn, "dim_exam_directions", direction_id)
    _require(conn, "dim_knowledge_points", point_id)
    duplicate = conn.execute(
        "SELECT sort_order FROM knowledge_exam_map "
        "WHERE knowledge_point_id = ? AND exam_direction_id = ?",
        (point_id, direction_id),
    ).fetchone()
    if duplicate is not None:
        if int(duplicate[0]) == PRIMARY_ORDER:
            raise ConflictError("该知识点是本考向的主知识点，不能再挂为辅助标签")
        raise ConflictError("该知识点已是此考向的辅助标签")
    # sort_order=0 永远留给主关联，辅助标签从 1 起排。
    next_order = int(conn.execute(
        "SELECT COALESCE(MAX(sort_order), ?) + 1 FROM knowledge_exam_map "
        "WHERE exam_direction_id = ?",
        (PRIMARY_ORDER, direction_id),
    ).fetchone()[0])
    try:
        conn.execute(
            "INSERT INTO knowledge_exam_map "
            "(knowledge_point_id, exam_direction_id, sort_order) VALUES (?, ?, ?)",
            (point_id, direction_id, next_order),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ConflictError("辅助标签挂载冲突（" + str(exc) + "）") from exc
    point = dao_base.load_knowledge_points(conn, [point_id])[point_id]
    return LinkedKnowledgePoint(
        id=point.id, name=point.name, code=point.code,
        subject_id=point.subject_id, parent_id=point.parent_id, sort_order=next_order,
    )


def remove_tag(conn: sqlite3.Connection, direction_id: int, point_id: int) -> None:
    """移除辅助标签只解除关联，不删知识点本体。"""
    link = conn.execute(
        "SELECT 1 FROM knowledge_exam_map WHERE knowledge_point_id = ? AND exam_direction_id = ?",
        (point_id, direction_id),
    ).fetchone()
    if link is None:
        raise ConsoleLookupError("该考向下没有这个辅助标签")
    conn.execute(
        "DELETE FROM knowledge_exam_map WHERE knowledge_point_id = ? AND exam_direction_id = ?",
        (point_id, direction_id),
    )
    conn.commit()


__all__ = [
    "LINK_MAPS",
    "add_direction",
    "add_tag",
    "chapter_points",
    "chapter_tree",
    "delete_direction",
    "direction_tags",
    "point_directions",
    "remove_tag",
    "reorder",
    "version_tree",
]
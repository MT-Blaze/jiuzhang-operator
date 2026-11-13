"""人教版（2019）高中物理六册：考向与教材-知识点桥表汇总。

知识点树本身由 ``seeds/books/book_physics_*.py`` 持有，本包补齐叶子层的真实考向，
并校验「册次 → 章 → 节 → 知识点 → 考向」链路无断点。
"""

from __future__ import annotations

from ..books.registry import CHAPTER_ROWS, KNOWLEDGE_ROWS
from . import compulsory1, compulsory2, compulsory3, elective1, elective2, elective3

MODULES = (
    compulsory1,
    compulsory2,
    compulsory3,
    elective1,
    elective2,
    elective3,
)

PHYSICS_EXAM_ROWS: tuple[tuple[object, ...], ...] = tuple(
    row for module in MODULES for row in module.EXAM_ROWS
)
PHYSICS_KNOWLEDGE_EXAM_ROWS: tuple[tuple[int, int, int], ...] = tuple(
    row for module in MODULES for row in module.KNOWLEDGE_EXAM_ROWS
)
PHYSICS_CHAPTER_KNOWLEDGE_ROWS: tuple[tuple[int, int, int], ...] = tuple(
    row for module in MODULES for row in module.CHAPTER_KNOWLEDGE_ROWS
)

SUBJECT_ID = 4
BOOK_IDS = frozenset({4101, 4102, 4103, 4104, 4105, 4106})
KNOWLEDGE_RANGE = range(410000, 470000)


def _validate() -> None:
    chapter_books = {row[0]: row[4] for row in CHAPTER_ROWS}
    knowledge = {row[0]: row for row in KNOWLEDGE_ROWS}

    exam_ids: set[int] = set()
    exam_codes: set[str] = set()
    exam_names: set[str] = set()
    for row in PHYSICS_EXAM_ROWS:
        direction_id, name, code, _sort, subject_id, chapter_id, _desc = row
        if subject_id != SUBJECT_ID:
            raise ValueError(f"物理考向学科错误：{direction_id}")
        if direction_id in exam_ids:
            raise ValueError(f"物理考向 ID 重复：{direction_id}")
        if code in exam_codes:
            raise ValueError(f"物理考向编码重复：{code}")
        if name in exam_names:
            raise ValueError(f"物理考向重名：{name}")
        if chapter_id not in chapter_books:
            raise ValueError(f"物理考向 {direction_id} 挂到不存在的章节 {chapter_id}")
        if chapter_books[chapter_id] not in BOOK_IDS:
            raise ValueError(f"物理考向 {direction_id} 挂到非高中物理册次")
        exam_ids.add(int(direction_id))
        exam_codes.add(str(code))
        exam_names.add(str(name))

    point_pairs: set[tuple[int, int]] = set()
    covered: set[int] = set()
    for knowledge_id, direction_id, _order in PHYSICS_KNOWLEDGE_EXAM_ROWS:
        if knowledge_id not in knowledge:
            raise ValueError(f"物理考向映射挂到不存在的知识点 {knowledge_id}")
        if knowledge[knowledge_id][4] != SUBJECT_ID:
            raise ValueError(f"物理考向映射挂到非物理知识点 {knowledge_id}")
        if direction_id not in exam_ids:
            raise ValueError(f"物理考向映射挂到不存在的考向 {direction_id}")
        pair = (knowledge_id, direction_id)
        if pair in point_pairs:
            raise ValueError(f"知识点-考向映射重复：{pair}")
        point_pairs.add(pair)
        covered.add(int(knowledge_id))

    bridge_pairs: set[tuple[int, int]] = set()
    for chapter_id, knowledge_id, _order in PHYSICS_CHAPTER_KNOWLEDGE_ROWS:
        if chapter_id not in chapter_books:
            raise ValueError(f"物理章节-知识点映射挂到不存在的章节 {chapter_id}")
        if knowledge_id not in knowledge:
            raise ValueError(f"物理章节-知识点映射挂到不存在的知识点 {knowledge_id}")
        pair = (chapter_id, knowledge_id)
        if pair in bridge_pairs:
            raise ValueError(f"章节-知识点映射重复：{pair}")
        bridge_pairs.add(pair)

    parents = {row[5] for row in KNOWLEDGE_ROWS if row[5] is not None}
    leaves = {
        row[0]
        for row in KNOWLEDGE_ROWS
        if row[4] == SUBJECT_ID and row[0] in KNOWLEDGE_RANGE and row[0] not in parents
    }
    missing = sorted(leaves - covered)
    if missing:
        raise ValueError(f"以下物理叶子知识点没有考向：{missing[:10]}")


_validate()

__all__ = [
    "MODULES",
    "PHYSICS_CHAPTER_KNOWLEDGE_ROWS",
    "PHYSICS_EXAM_ROWS",
    "PHYSICS_KNOWLEDGE_EXAM_ROWS",
]

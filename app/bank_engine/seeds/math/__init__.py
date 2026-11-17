"""人教A版（2019）高中数学五册：知识点、考向与两张桥表的统一出口。

验收三条底线：
1. 每册的教材节都必须挂上知识点，杜绝「4.1 数列的概念」这类空节；
2. 所有叶子知识点都必须有考向，杜绝只有骨架没有考法；
3. ID 与 code 按册号段隔离，五册之间以及与既有种子之间不得撞号。
"""

from __future__ import annotations

from ..exam_direction_seed import EXAM_DIRECTION_ROWS
from ..knowledge_math import MATH_KNOWLEDGE_ROWS as BASE_MATH_KNOWLEDGE_ROWS
from ..migrated_textbook_seed import MIGRATED_CHAPTER_ROWS
from . import compulsory1, compulsory2, elective1, elective2, elective3

MODULES = (compulsory1, compulsory2, elective1, elective2, elective3)

MATH_KNOWLEDGE_ROWS: tuple[tuple[object, ...], ...] = tuple(
    row for module in MODULES for row in module.KNOWLEDGE_ROWS
)
MATH_EXAM_ROWS: tuple[tuple[object, ...], ...] = tuple(
    row for module in MODULES for row in module.EXAM_ROWS
)
MATH_KNOWLEDGE_EXAM_ROWS: tuple[tuple[int, int, int], ...] = tuple(
    row for module in MODULES for row in module.KNOWLEDGE_EXAM_ROWS
)
MATH_CHAPTER_KNOWLEDGE_ROWS: tuple[tuple[int, int, int], ...] = tuple(
    row for module in MODULES for row in module.CHAPTER_KNOWLEDGE_ROWS
)

SUBJECT_ID = 2
BOOK_IDS = frozenset({9101, 9102, 9103, 9104, 9105})
KNOWLEDGE_BASES = {
    "H": 960001,
    "C2": 961001,
    "X1": 962001,
    "X2": 963001,
    "X3": 964001,
}
EXAM_BASES = {
    "H": 1001,
    "C2": 1201,
    "X1": 2001,
    "X2": 2801,
    "X3": 3601,
}


def _validate() -> None:
    chapter_rows = {
        row[0]: row for row in MIGRATED_CHAPTER_ROWS if row[4] in BOOK_IDS
    }
    sections = {
        chapter_id for chapter_id, row in chapter_rows.items() if row[5] is not None
    }
    knowledge = {row[0]: row for row in (*BASE_MATH_KNOWLEDGE_ROWS, *MATH_KNOWLEDGE_ROWS)}
    exams = {row[0]: row for row in (*EXAM_DIRECTION_ROWS, *MATH_EXAM_ROWS)}

    for row_id, code, name, _sort, subject_id, parent_id in MATH_KNOWLEDGE_ROWS:
        if subject_id != SUBJECT_ID:
            raise ValueError(f"数学知识点学科错误：{row_id}")
        if parent_id is not None:
            parent = knowledge.get(parent_id)
            if parent is None:
                raise ValueError(f"数学知识点 {row_id} 的父节点 {parent_id} 不存在")
            if parent[4] != SUBJECT_ID:
                raise ValueError(f"数学知识点 {row_id} 与父节点学科不一致")
        if not name or not code:
            raise ValueError(f"数学知识点 {row_id} 缺名称或编码")

    knowledge_ids: set[int] = set()
    knowledge_codes: set[str] = set()
    for row in MATH_KNOWLEDGE_ROWS:
        if row[0] in knowledge_ids:
            raise ValueError(f"数学知识点 ID 重复：{row[0]}")
        if row[1] in knowledge_codes:
            raise ValueError(f"数学知识点编码重复：{row[1]}")
        knowledge_ids.add(row[0])
        knowledge_codes.add(row[1])

    exam_ids: set[int] = set()
    exam_codes: set[str] = set()
    exam_names: set[str] = {row[1] for row in EXAM_DIRECTION_ROWS if row[4] == SUBJECT_ID}
    exam_keys: set[tuple[int, str]] = set()
    for direction_id, name, code, _sort, subject_id, chapter_id, _desc in MATH_EXAM_ROWS:
        if subject_id != SUBJECT_ID:
            raise ValueError(f"数学考向学科错误：{direction_id}")
        if direction_id in exam_ids:
            raise ValueError(f"数学考向 ID 重复：{direction_id}")
        if code in exam_codes:
            raise ValueError(f"数学考向编码重复：{code}")
        if name in exam_names:
            raise ValueError(f"数学考向重名：{name}")
        if chapter_id is not None and chapter_id not in sections:
            raise ValueError(f"数学考向 {direction_id} 未挂到教材节：{chapter_id}")
        key = (chapter_id or 0, name)
        if key in exam_keys:
            raise ValueError(f"同一教材节下考向重名：{chapter_id}/{name}")
        exam_ids.add(direction_id)
        exam_codes.add(code)
        exam_names.add(name)
        exam_keys.add(key)

    pairs: set[tuple[int, int]] = set()
    covered_points: set[int] = set()
    for point_id, direction_id, _order in MATH_KNOWLEDGE_EXAM_ROWS:
        if point_id not in knowledge:
            raise ValueError(f"数学知识点-考向映射挂到不存在的知识点 {point_id}")
        if direction_id not in exams:
            raise ValueError(f"数学知识点-考向映射挂到不存在的考向 {direction_id}")
        pair = (point_id, direction_id)
        if pair in pairs:
            raise ValueError(f"数学知识点-考向映射重复：{pair}")
        pairs.add(pair)
        covered_points.add(point_id)

    bridge_pairs: set[tuple[int, int]] = set()
    covered_chapters: set[int] = set()
    for chapter_id, point_id, _order in MATH_CHAPTER_KNOWLEDGE_ROWS:
        if chapter_id not in sections:
            raise ValueError(f"数学教材节-知识点映射挂到不存在的节 {chapter_id}")
        if point_id not in knowledge:
            raise ValueError(f"数学教材节-知识点映射挂到不存在的知识点 {point_id}")
        pair = (chapter_id, point_id)
        if pair in bridge_pairs:
            raise ValueError(f"数学教材节-知识点映射重复：{pair}")
        bridge_pairs.add(pair)
        covered_chapters.add(chapter_id)

    missing = sorted(sections - covered_chapters)
    if missing:
        raise ValueError(f"以下高中数学教材节没有知识点：{missing[:10]}")

    parent_ids = {row[5] for row in MATH_KNOWLEDGE_ROWS if row[5] is not None}
    leaves = {
        row[0]
        for row in MATH_KNOWLEDGE_ROWS
        if row[0] >= 960001 and row[0] not in parent_ids
    }
    without_direction = sorted(leaves - covered_points)
    if without_direction:
        raise ValueError(f"以下高中数学知识点没有考向：{without_direction[:10]}")

    _validate_segments()


def _validate_segments() -> None:
    for code, base in KNOWLEDGE_BASES.items():
        rows = [row for row in MATH_KNOWLEDGE_ROWS if row[1].startswith(f"KP_MATH_{code}_")]
        if not rows:
            raise ValueError(f"数学知识点号段 {code} 为空")
        offsets = [row[0] - base for row in rows]
        if min(offsets) != 0 or max(offsets) >= 1000:
            raise ValueError(f"数学知识点号段越界：{code}")
    for code, base in EXAM_BASES.items():
        rows = [row for row in MATH_EXAM_ROWS if row[2].startswith(f"ED_MATH_{code}_")]
        if not rows:
            raise ValueError(f"数学考向号段 {code} 为空")
        offsets = [row[0] - base for row in rows]
        if min(offsets) != 0 or max(offsets) >= 800:
            raise ValueError(f"数学考向号段越界：{code}")


_validate()

__all__ = [
    "MATH_CHAPTER_KNOWLEDGE_ROWS",
    "MATH_EXAM_ROWS",
    "MATH_KNOWLEDGE_EXAM_ROWS",
    "MATH_KNOWLEDGE_ROWS",
    "MODULES",
]

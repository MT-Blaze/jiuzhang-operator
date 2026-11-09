"""全学科知识点总表：汇总各学科模块并做父子层级与唯一性校验。"""

from __future__ import annotations

from .books.registry import KNOWLEDGE_ROWS as BOOK_KNOWLEDGE_ROWS
from .knowledge_humanities import CHINESE_KNOWLEDGE_ROWS, ENGLISH_KNOWLEDGE_ROWS
from .knowledge_math import MATH_KNOWLEDGE_ROWS
from .knowledge_sciences import (
    BIOLOGY_KNOWLEDGE_ROWS,
    CHEMISTRY_KNOWLEDGE_ROWS,
    PHYSICS_KNOWLEDGE_ROWS,
)

KNOWLEDGE_POINT_ROWS: tuple[
    tuple[int, str, str, int, int, int | None], ...
] = (
    *CHINESE_KNOWLEDGE_ROWS,
    *MATH_KNOWLEDGE_ROWS,
    *ENGLISH_KNOWLEDGE_ROWS,
    *PHYSICS_KNOWLEDGE_ROWS,
    *CHEMISTRY_KNOWLEDGE_ROWS,
    *BIOLOGY_KNOWLEDGE_ROWS,
    *BOOK_KNOWLEDGE_ROWS,
)


def validate_knowledge_rows() -> None:
    by_id = {row[0]: row for row in KNOWLEDGE_POINT_ROWS}
    if len(by_id) != len(KNOWLEDGE_POINT_ROWS):
        raise ValueError("知识点 ID 重复")
    codes = [row[1] for row in KNOWLEDGE_POINT_ROWS]
    if len(set(codes)) != len(codes):
        raise ValueError("知识点编码重复")
    siblings: set[tuple[int, int, str]] = set()
    for row_id, _code, name, _sort, subject, parent in KNOWLEDGE_POINT_ROWS:
        if parent == row_id:
            raise ValueError(f"知识点自环：{row_id}")
        if parent is not None:
            parent_row = by_id.get(parent)
            if parent_row is None:
                raise ValueError(f"知识点 {row_id} 的父节点 {parent} 不存在")
            if parent_row[4] != subject:
                raise ValueError(f"知识点 {row_id} 与父节点学科不一致")
        key = (subject, parent or 0, name)
        if key in siblings:
            raise ValueError(f"同学科同父节点下重名：{subject}/{parent}/{name}")
        siblings.add(key)


validate_knowledge_rows()

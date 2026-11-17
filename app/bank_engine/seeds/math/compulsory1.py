"""人教A版（2019）必修第一册：沿用已签发的知识点与考向种子。

必修一的数据在 2026-11 已按节落库并签发（70 个知识点、194 个考向），
此处只做统一出口与三列桥表归一，避免重写造成既有 ID 与引用漂移。
"""

from __future__ import annotations

from ..math_required1 import (
    MATH_REQUIRED1_CHAPTER_KNOWLEDGE_ROWS,
    MATH_REQUIRED1_EXAM_ROWS,
    MATH_REQUIRED1_KNOWLEDGE_EXAM_ROWS,
    MATH_REQUIRED1_KNOWLEDGE_ROWS,
)

KNOWLEDGE_ROWS = MATH_REQUIRED1_KNOWLEDGE_ROWS
EXAM_ROWS = MATH_REQUIRED1_EXAM_ROWS
KNOWLEDGE_EXAM_ROWS = tuple((point, direction, 0) for point, direction in MATH_REQUIRED1_KNOWLEDGE_EXAM_ROWS)
CHAPTER_KNOWLEDGE_ROWS = tuple((chapter, point, 0) for chapter, point in MATH_REQUIRED1_CHAPTER_KNOWLEDGE_ROWS)

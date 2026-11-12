"""试卷自然去重键：年份 / 月 / 轮次 / 学期 / 主体 / 学科 / 年级 / 类型。

范围（region_id）与层级（exam_level_id）只描述这张卷的“口径”，
同一场考试改口径不该另开一张卷，所以二者刻意不进自然键。
"""

from __future__ import annotations

import sqlite3

NATURAL_KEY_WHERE = (
    "year = ? AND COALESCE(month, 0) = ? AND COALESCE(mock_round, 0) = ? "
    "AND COALESCE(semester, '') = ? AND COALESCE(exam_org_id, 0) = ? "
    "AND subject_id = ? AND grade_id = ? AND exam_type_id = ?"
)


def exam_natural_key(
    *,
    year: int,
    month: int | None,
    mock_round: int | None,
    semester: str | None,
    exam_org_id: int | None,
    subject_id: int,
    grade_id: int,
    exam_type_id: int,
) -> tuple[int, int, int, str, int, int, int, int]:
    return (
        int(year),
        int(month or 0),
        int(mock_round or 0),
        str(semester or ""),
        int(exam_org_id or 0),
        int(subject_id),
        int(grade_id),
        int(exam_type_id),
    )


def find_exam_id(conn: sqlite3.Connection, key: tuple) -> int | None:
    row = conn.execute(
        "SELECT id FROM exams WHERE " + NATURAL_KEY_WHERE + " ORDER BY id LIMIT 1",
        key,
    ).fetchone()
    return None if row is None else int(row[0])


__all__ = ["NATURAL_KEY_WHERE", "exam_natural_key", "find_exam_id"]

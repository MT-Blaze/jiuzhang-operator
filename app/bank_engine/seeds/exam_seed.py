"""考试类型字典与示例试卷种子。

考试类型只保留 8 个大类，轮次由 ``exams.mock_round`` 承载，
考试组织/学校由 ``exams.exam_org_name`` 与 ``exams.school_id`` 承载。
示例试卷用真实学科/年级/学校 ID 演示“一张一模卷关联多所学校”。
"""

from __future__ import annotations

# id / name / code / sort_order
EXAM_TYPE_ROWS: tuple[tuple[int, str, str, int], ...] = (
    (1, '高考', 'gaokao', 1),
    (2, '结业考试', 'academic_proficiency', 2),
    (3, '模拟考', 'mock', 3),
    (4, '期中', 'midterm', 4),
    (5, '期末', 'final', 5),
    (6, '月考', 'monthly', 6),
    (7, '小考', 'weekly_test', 7),
    (8, '开学考', 'opening_exam', 8),
)

# id / year / exam_org_name / school_id / month / exam_type_id / mock_round
# / grade_id / semester / subject_id
EXAM_ROWS: tuple[
    tuple[int, int, str | None, int | None, int | None, int, int | None, int, str | None, int],
    ...,
] = (
    (4, 2025, None, 258, None, 3, 1, 12, None, 2),
)

# exam_id / school_id：一场一模同时落多所学校
EXAM_SCHOOL_ROWS: tuple[tuple[int, int], ...] = (
    (4, 258),
    (4, 237),
)

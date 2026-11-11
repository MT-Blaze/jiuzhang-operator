"""考试类型字典与示例试卷种子。

考试类型只保留命题来源口径（高考真题、模考、期中期末、竞赛等）；
联考、区域统考、校考属于考试范围，由 ``exams.exam_subject`` 承载。
示例试卷用真实学科/年级/学校 ID 演示“一张一模卷关联多所学校”。
"""

from __future__ import annotations

# id / name / code / sort_order
EXAM_TYPE_ROWS: tuple[tuple[int, str, str, int], ...] = (
    (1, "高考真题", "gaokao", 1),
    (5, "一模", "mock_one", 2),
    (6, "二模", "mock_two", 3),
    (7, "期中", "midterm", 4),
    (8, "期末", "final", 5),
    (9, "月考", "monthly", 6),
    (10, "竞赛题", "competition", 7),
    (11, "强基题", "qiangji", 8),
    (12, "自主招生", "independent_enrollment", 9),
    (13, "外国题", "foreign", 10),
    (14, "机构题", "institution", 11),
    (15, "汇编题", "compilation", 12),
    (16, "自编题", "self_made", 13),
)

# id / code / year / month / subject_id / grade_id / exam_type_id / exam_subject
EXAM_ROWS: tuple[tuple[int, str, int, int | None, int, int, int, str], ...] = (
    (4, "exm_seed_harbin_mock1_2025_g12", 2025, 1, 2, 12, 5, "哈尔滨一模"),
)

# exam_id / school_id：一场一模同时落多所学校
EXAM_SCHOOL_ROWS: tuple[tuple[int, int], ...] = (
    (4, 258),
    (4, 237),
)

"""考试类型字典与示例试卷种子。

考试类型覆盖高考、联考、区域统考、校考、一模、二模、期中、期末、月考等场景；
示例试卷用真实学科/年级/学校 ID 演示“一张联考卷关联多所学校”。
"""

from __future__ import annotations

# id / name / code / sort_order
EXAM_TYPE_ROWS: tuple[tuple[int, str, str, int], ...] = (
    (1, "高考题", "gaokao", 1),
    (2, "联考题", "joint_exam", 2),
    (3, "区域统考题", "regional_exam", 3),
    (4, "校考题", "school_exam", 4),
    (5, "一模", "mock_one", 5),
    (6, "二模", "mock_two", 6),
    (7, "期中", "midterm", 7),
    (8, "期末", "final", 8),
    (9, "月考", "monthly", 9),
    (10, "竞赛题", "competition", 10),
    (11, "强基题", "qiangji", 11),
    (12, "自主招生题", "independent_enrollment", 12),
    (13, "外国题", "foreign", 13),
    (14, "机构题", "institution", 14),
    (15, "汇编题", "compilation", 15),
    (16, "自编题", "self_made", 16),
)

# id / code / year / month / subject_id / grade_id / exam_type_id / exam_subject
EXAM_ROWS: tuple[tuple[int, str, int, int | None, int, int, int, str], ...] = (
    (1, "exm_seed_t8_2024_g12", 2024, 9, 2, 12, 2, "T8联盟"),
    (2, "exm_seed_northeast_2024_g12", 2024, 6, 2, 12, 3, "东北三省联考"),
    (3, "exm_seed_harbin_mock1_2025_g12", 2025, 1, 2, 12, 5, "哈尔滨一模"),
    (4, "exm_seed_harbin3_2025_g12", 2025, 3, 2, 12, 4, "哈三中"),
)

# exam_id / school_id：一场联考同时落多所学校
EXAM_SCHOOL_ROWS: tuple[tuple[int, int], ...] = (
    (1, 258),
    (1, 19),
    (1, 80),
    (2, 19),
    (2, 80),
    (2, 195),
    (3, 258),
    (3, 237),
    (4, 258),
)

"""考试字典与示例试卷种子。

考试类型只保留 8 个大类：高考 / 学业水平 / 模拟考 / 期中 / 期末 / 月考 / 周测 / 开学考。
轮次由 ``exams.mock_round`` 承载，考试组织由 ``dict_exam_orgs`` 承载，
考试范围与地域分别由 ``dict_exam_levels`` 与 ``dim_regions`` 承载。
示例试卷用真实学科/年级/学校 ID 演示“一张跨省联考卷关联多所学校”。
"""

from __future__ import annotations

# id / name / code / sort_order
EXAM_TYPE_ROWS: tuple[tuple[int, str, str, int], ...] = (
    (1, '高考', 'gaokao', 1),
    (2, '学业水平', 'academic_proficiency', 2),
    (3, '模拟考', 'mock', 3),
    (4, '期中', 'midterm', 4),
    (5, '期末', 'final', 5),
    (6, '月考', 'monthly', 6),
    (7, '周测', 'weekly_test', 7),
    (8, '开学考', 'opening_exam', 8),
)

# id / name / code / sort_order
EXAM_LEVEL_ROWS: tuple[tuple[int, str, str, int], ...] = (
    (1, '全国统考', 'national', 1),
    (2, '跨省联考', 'cross_province', 2),
    (3, '省级统考', 'provincial', 3),
    (4, '跨地市联考', 'cross_city', 4),
    (5, '地市统考', 'city', 5),
    (6, '学区/区县统考', 'district', 6),
    (7, '学校统考', 'school', 7),
)

# 只种一个真实存在的联考联盟；其余主体由老师在录题时按需懒创建。
# id / name / org_type / school_id
EXAM_ORG_ROWS: tuple[tuple[int, str, str, int | None], ...] = (
    (1, 'T8联盟', '联考联盟', None),
)

# id / year / region_id / exam_org_id / exam_level_id / month / exam_type_id
# / mock_round / grade_id / semester / subject_id
EXAM_ROWS: tuple[
    tuple[int, int, int | None, int | None, int | None, int | None, int, int | None, int,
          str | None, int],
    ...,
] = (
    (4, 2025, 370, 1, 2, None, 3, 1, 12, None, 2),
)

# exam_id / school_id：一场跨省联考同时落多所学校
EXAM_SCHOOL_ROWS: tuple[tuple[int, int], ...] = (
    (4, 258),
    (4, 237),
)

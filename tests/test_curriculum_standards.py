"""课标原文清单契约：全学科、全学段逐条钉死，零「全学段」、零自造词。

依据《义务教育课程方案和课程标准（2022 年版）》与《普通高中课程标准
（2017 年版 2020 年修订）》；学科没有官方「学科思想」单列清单时留空，
不拿解题方法或自造术语充数。

运行：``.venv/Scripts/python.exe -m unittest tests.test_curriculum_standards -v``
"""

from __future__ import annotations

import unittest

from app.bank_engine.seeds.curriculum import CURRICULUM_COUNTS
from app.bank_engine.seeds.curriculum_standards import (
    CORE_COMPETENCY_ROWS,
    SUBJECT_THOUGHT_ROWS,
)

# (subject_id, stage) -> 课标原文条目，顺序即课标顺序。
EXPECTED: dict[tuple[int, str], tuple[str, ...]] = {
    (2, "小学"): (
        "数感", "量感", "符号意识", "运算能力", "几何直观", "空间观念",
        "推理意识", "数据意识", "模型意识", "应用意识", "创新意识",
    ),
    (2, "初中"): (
        "抽象能力", "运算能力", "几何直观", "空间观念", "推理能力",
        "数据观念", "模型观念", "应用意识", "创新意识",
    ),
    (2, "高中"): (
        "数学抽象", "逻辑推理", "数学建模", "直观想象", "数学运算", "数据分析",
    ),
    (4, "初中"): ("物理观念", "科学思维", "科学探究", "科学态度与责任"),
    (4, "高中"): ("物理观念", "科学思维", "科学探究", "科学态度与责任"),
    (5, "初中"): ("化学观念", "科学思维", "科学探究与实践", "科学态度与责任"),
    (5, "高中"): (
        "宏观辨识与微观探析", "变化观念与平衡思想", "证据推理与模型认知",
        "科学探究与创新意识", "科学态度与社会责任",
    ),
    (1, "小学"): ("文化自信", "语言运用", "思维能力", "审美创造"),
    (1, "初中"): ("文化自信", "语言运用", "思维能力", "审美创造"),
    (1, "高中"): ("文化自信", "语言运用", "思维能力", "审美创造"),
    (3, "小学"): ("语言能力", "文化意识", "思维品质", "学习能力"),
    (3, "初中"): ("语言能力", "文化意识", "思维品质", "学习能力"),
    (3, "高中"): ("语言能力", "文化意识", "思维品质", "学习能力"),
    (6, "初中"): ("生命观念", "科学思维", "探究实践", "态度责任"),
    (6, "高中"): ("生命观念", "科学思维", "科学探究", "社会责任"),
    (7, "小学"): ("政治认同", "道德修养", "法治观念", "健全人格", "责任意识"),
    (7, "初中"): ("政治认同", "道德修养", "法治观念", "健全人格", "责任意识"),
    (7, "高中"): ("政治认同", "科学精神", "法治意识", "公共参与"),
    (8, "初中"): ("唯物史观", "时空观念", "史料实证", "历史解释", "家国情怀"),
    (8, "高中"): ("唯物史观", "时空观念", "史料实证", "历史解释", "家国情怀"),
    (9, "初中"): ("人地协调观", "综合思维", "区域认知", "地理实践力"),
    (9, "高中"): ("人地协调观", "综合思维", "区域认知", "地理实践力"),
    (11, "小学"): ("信息意识", "计算思维", "数字化学习与创新", "信息社会责任"),
    (11, "初中"): ("信息意识", "计算思维", "数字化学习与创新", "信息社会责任"),
    (11, "高中"): ("信息意识", "计算思维", "数字化学习与创新", "信息社会责任"),
    (12, "小学"): ("运动能力", "健康行为", "体育品德"),
    (12, "初中"): ("运动能力", "健康行为", "体育品德"),
    (12, "高中"): ("运动能力", "健康行为", "体育品德"),
    (10, "小学"): ("科学观念", "科学思维", "探究实践", "态度责任"),
    (10, "初中"): ("科学观念", "科学思维", "探究实践", "态度责任"),
    (13, "小学"): ("审美感知", "艺术表现", "创意实践", "文化理解"),
    (13, "初中"): ("审美感知", "艺术表现", "创意实践", "文化理解"),
    (13, "高中"): ("审美感知", "艺术表现", "文化理解"),
    (14, "小学"): ("审美感知", "艺术表现", "创意实践", "文化理解"),
    (14, "初中"): ("审美感知", "艺术表现", "创意实践", "文化理解"),
    (14, "高中"): ("图像识读", "美术表现", "审美判断", "创意实践", "文化理解"),
    (15, "小学"): ("劳动观念", "劳动能力", "劳动习惯和品质", "劳动精神"),
    (15, "初中"): ("劳动观念", "劳动能力", "劳动习惯和品质", "劳动精神"),
}

EXPECTED_THOUGHTS: dict[tuple[int, str], tuple[str, ...]] = {
    (2, "小学"): ("数形结合",),
    (2, "初中"): ("数形结合",),
    (2, "高中"): ("数学抽象", "逻辑推理", "数学建模", "数形结合"),
}

DIRTY_TERMS = (
    "等效替代", "守恒", "微元", "控制变量", "函数思想", "方程思想",
    "转化与化归", "分类讨论", "整体思想", "类比思想", "模型思想",
    "系统思想", "对称思想", "理想化思想", "转换思想", "模型建构思想",
    "（生物）", "（科学）", "（美术）",
)


def _groups(rows: tuple[tuple[int, str, str, int, int, str], ...]) -> dict:
    out: dict[tuple[int, str], list[str]] = {}
    for _, _, name, _, subject_id, stage in rows:
        out.setdefault((subject_id, stage), []).append(name)
    return out


class CurriculumStandardsTest(unittest.TestCase):
    def test_core_competencies_match_curriculum_per_stage(self) -> None:
        groups = _groups(CORE_COMPETENCY_ROWS)
        self.assertEqual(set(groups), set(EXPECTED))
        for key, names in EXPECTED.items():
            with self.subTest(subject_stage=key):
                self.assertEqual(tuple(groups[key]), names)

    def test_subject_thoughts_only_official_math_terms(self) -> None:
        groups = _groups(SUBJECT_THOUGHT_ROWS)
        self.assertEqual(set(groups), set(EXPECTED_THOUGHTS))
        for key, names in EXPECTED_THOUGHTS.items():
            self.assertEqual(tuple(groups[key]), names)
        self.assertEqual(
            sum(len(names) for names in groups.values()),
            CURRICULUM_COUNTS["dict_subject_thoughts"],
        )

    def test_never_writes_all_stage(self) -> None:
        for rows in (CORE_COMPETENCY_ROWS, SUBJECT_THOUGHT_ROWS):
            self.assertNotIn("全学段", {row[5] for row in rows})

    def test_no_dirty_or_self_invented_terms(self) -> None:
        for rows in (CORE_COMPETENCY_ROWS, SUBJECT_THOUGHT_ROWS):
            for _, _, name, _, _, _ in rows:
                for term in DIRTY_TERMS:
                    self.assertNotIn(term, name)

    def test_ids_and_codes_are_unique(self) -> None:
        for rows in (CORE_COMPETENCY_ROWS, SUBJECT_THOUGHT_ROWS):
            ids = [row[0] for row in rows]
            codes = [row[1] for row in rows]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertEqual(len(codes), len(set(codes)))

    def test_counts_follow_seed_source(self) -> None:
        self.assertEqual(len(CORE_COMPETENCY_ROWS), 168)
        self.assertEqual(len(SUBJECT_THOUGHT_ROWS), 6)
        self.assertEqual(CURRICULUM_COUNTS["dict_core_competencies"], 168)
        self.assertEqual(CURRICULUM_COUNTS["dict_subject_thoughts"], 6)


if __name__ == "__main__":
    unittest.main()

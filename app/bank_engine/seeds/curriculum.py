"""国家课标基础字典：年级、学科、题型与教研三维（思想 / 方法 / 素养）。

依据《义务教育课程方案和课程标准（2022 年版）》与《普通高中课程标准
（2017 年版 2020 年修订）》整理。教研维度的 stage 只允许四个明码值：
小学 / 初中 / 高中 / 全学段，绝不留空；跨学段通用条目一律标「全学段」。
"""

from __future__ import annotations

from .knowledge_seed import KNOWLEDGE_POINT_ROWS

# id / code / name
SUBJECT_ROWS: tuple[tuple[int, str, str], ...] = (
    (1, "chinese", "语文"),
    (2, "mathematics", "数学"),
    (3, "english", "英语"),
    (4, "physics", "物理"),
    (5, "chemistry", "化学"),
    (6, "biology", "生物"),
    (7, "politics", "政治"),
    (8, "history", "历史"),
    (9, "geography", "地理"),
    (10, "science", "科学"),
    (11, "information_technology", "信息科技"),
    (12, "physical_education", "体育与健康"),
    (13, "music", "音乐"),
    (14, "art", "美术"),
    (15, "labor", "劳动"),
)

# id / code / name / sort_order / stage
GRADE_ROWS: tuple[tuple[int, str, str, int, str], ...] = (
    (1, "g1", "一年级", 1, "小学"),
    (2, "g2", "二年级", 2, "小学"),
    (3, "g3", "三年级", 3, "小学"),
    (4, "g4", "四年级", 4, "小学"),
    (5, "g5", "五年级", 5, "小学"),
    (6, "g6", "六年级", 6, "小学"),
    (7, "g7", "七年级", 7, "初中"),
    (8, "g8", "八年级", 8, "初中"),
    (9, "g9", "九年级", 9, "初中"),
    (10, "g10", "高一", 10, "高中"),
    (11, "g11", "高二", 11, "高中"),
    (12, "g12", "高三", 12, "高中"),
)

# id / code / name / sort_order
QUESTION_TYPE_ROWS: tuple[tuple[int, str, str, int], ...] = (
    (1, "choice", "选择题", 1),
    (2, "fill_blank", "填空题", 2),
    (3, "solution", "解答题", 3),
)

SUBJECT_MATH_ID = 2
STAGE_PRIMARY = "小学"
STAGE_JUNIOR = "初中"
STAGE_SENIOR = "高中"
STAGE_ALL = "全学段"
QUESTION_TYPE_CHOICE_ID = 1
QUESTION_TYPE_SOLUTION_ID = 3

# id / code / name / sort_order / subject_id / stage
SUBJECT_THOUGHT_ROWS: tuple[tuple[int, str, str, int, int, str], ...] = (
    (9001, "math_number_shape", "数形结合", 1, SUBJECT_MATH_ID, STAGE_ALL),
    (9002, "math_function_equation", "函数与方程", 2, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9003, "math_transformation", "转化与化归", 3, SUBJECT_MATH_ID, STAGE_ALL),
    (9004, "math_classification", "分类讨论", 4, SUBJECT_MATH_ID, STAGE_ALL),
    (9005, "math_special_general", "特殊与一般", 5, SUBJECT_MATH_ID, STAGE_ALL),
    (9101, "physics_equivalent_substitution", "等效替代", 1, 4, STAGE_ALL),
    (9102, "physics_conservation", "守恒思想", 2, 4, STAGE_ALL),
    (9103, "physics_idealization", "理想化思想", 3, 4, STAGE_ALL),
    (9104, "physics_symmetry", "对称思想", 4, 4, STAGE_ALL),
    (9201, "chem_macro_micro", "宏微结合", 1, 5, STAGE_ALL),
    (9202, "chem_change_conservation", "变化守恒", 2, 5, STAGE_ALL),
    (9203, "chem_classification", "分类思想", 3, 5, STAGE_ALL),
    (9204, "chem_structure_property", "结构决定性质", 4, 5, STAGE_ALL),
    (9205, "chem_equilibrium", "平衡思想", 5, 5, STAGE_ALL),
    (9301, "chinese_unity", "文道统一", 1, 1, STAGE_ALL),
    (9302, "chinese_context", "情境体验", 2, 1, STAGE_ALL),
    (9303, "chinese_reading_writing", "读写结合", 3, 1, STAGE_ALL),
    (9304, "chinese_immersion", "涵泳品味", 4, 1, STAGE_ALL),
    (9401, "english_discourse", "语篇意识", 1, 3, STAGE_ALL),
    (9402, "english_cross_culture", "跨文化交际", 2, 3, STAGE_ALL),
    (9403, "english_situational", "情境交际", 3, 3, STAGE_ALL),
    (9404, "english_pragmatic", "语用意识", 4, 3, STAGE_ALL),
)

# id / code / name / sort_order / subject_id / stage
SOLUTION_METHOD_ROWS: tuple[tuple[int, str, str, int, int, str], ...] = (
    (9001, "math_definition", "定义法", 1, SUBJECT_MATH_ID, STAGE_ALL),
    (9002, "math_substitution", "换元法", 2, SUBJECT_MATH_ID, STAGE_ALL),
    (9003, "math_completing_square", "配方法", 3, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9004, "math_undetermined", "待定系数法", 4, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9005, "math_shift_subtract", "错位相减", 5, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9006, "math_telescoping", "裂项相消", 6, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9007, "math_discriminant", "判别式法", 7, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9008, "math_derivative", "导数法", 8, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9009, "math_construction", "构造法", 9, SUBJECT_MATH_ID, STAGE_ALL),
    (
        9010,
        "math_induction",
        "数学归纳法",
        10,
        SUBJECT_MATH_ID,
        STAGE_SENIOR,
    ),
    (9011, "math_contradiction", "反证法", 11, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9101, "physics_control_variable", "控制变量法", 1, 4, STAGE_JUNIOR),
    (9102, "physics_infinitesimal", "微元法", 2, 4, STAGE_SENIOR),
    (9103, "physics_ratio_definition", "比值定义法", 3, 4, STAGE_JUNIOR),
    (9104, "physics_equivalent_method", "等效替代法", 4, 4, STAGE_JUNIOR),
    (9105, "physics_graph", "图像法", 5, 4, STAGE_ALL),
    (9106, "physics_isolation", "隔离法", 6, 4, STAGE_SENIOR),
    (9107, "physics_whole_system", "整体法", 7, 4, STAGE_SENIOR),
    (9108, "physics_hypothesis", "假设法", 8, 4, STAGE_ALL),
    (9201, "chem_cross", "十字交叉法", 1, 5, STAGE_SENIOR),
    (9202, "chem_extreme", "极值法", 2, 5, STAGE_SENIOR),
    (9203, "chem_conservation_method", "守恒法", 3, 5, STAGE_SENIOR),
    (9204, "chem_relation", "关系式法", 4, 5, STAGE_SENIOR),
    (9205, "chem_difference", "差量法", 5, 5, STAGE_SENIOR),
    (9206, "chem_balancing", "配平法", 6, 5, STAGE_JUNIOR),
    (9301, "chinese_close_reading", "文本细读法", 1, 1, STAGE_ALL),
    (9302, "chinese_comparative_reading", "比较阅读法", 2, 1, STAGE_ALL),
    (9303, "chinese_annotation", "批注法", 3, 1, STAGE_ALL),
    (9304, "chinese_recitation", "诵读品味法", 4, 1, STAGE_ALL),
    (9401, "english_skimming", "略读法", 1, 3, STAGE_ALL),
    (9402, "english_scanning", "寻读法", 2, 3, STAGE_ALL),
    (9403, "english_context_guessing", "语境猜词法", 3, 3, STAGE_ALL),
    (9404, "english_word_formation", "构词法", 4, 3, STAGE_ALL),
    (9405, "english_discourse_analysis", "语篇分析法", 5, 3, STAGE_ALL),
)

# id / code / name / sort_order / subject_id / stage
CORE_COMPETENCY_ROWS: tuple[tuple[int, str, str, int, int, str], ...] = (
    (9001, "math_abstraction", "数学抽象", 1, SUBJECT_MATH_ID, STAGE_ALL),
    (9002, "math_logical_reasoning", "逻辑推理", 2, SUBJECT_MATH_ID, STAGE_ALL),
    (9003, "math_modeling", "数学建模", 3, SUBJECT_MATH_ID, STAGE_ALL),
    (9004, "math_intuitive_imagination", "直观想象", 4, SUBJECT_MATH_ID, STAGE_ALL),
    (9005, "math_operation", "数学运算", 5, SUBJECT_MATH_ID, STAGE_ALL),
    (9006, "math_data_analysis", "数据分析", 6, SUBJECT_MATH_ID, STAGE_ALL),
    (9101, "physics_concept", "物理观念", 1, 4, STAGE_ALL),
    (9102, "physics_scientific_thinking", "科学思维", 2, 4, STAGE_ALL),
    (9103, "physics_inquiry", "科学探究", 3, 4, STAGE_ALL),
    (9104, "physics_attitude", "科学态度与责任", 4, 4, STAGE_ALL),
    (9201, "chem_macro_micro_analysis", "宏观辨识与微观探析", 1, 5, STAGE_ALL),
    (9202, "chem_change_equilibrium", "变化观念与平衡思想", 2, 5, STAGE_ALL),
    (9203, "chem_evidence_model", "证据推理与模型认知", 3, 5, STAGE_ALL),
    (9204, "chem_inquiry_innovation", "科学探究与创新意识", 4, 5, STAGE_ALL),
    (9205, "chem_social_responsibility", "科学态度与社会责任", 5, 5, STAGE_ALL),
    (9301, "chinese_cultural_confidence", "文化自信", 1, 1, STAGE_ALL),
    (9302, "chinese_language_use", "语言运用", 2, 1, STAGE_ALL),
    (9303, "chinese_thinking", "思维能力", 3, 1, STAGE_ALL),
    (9304, "chinese_aesthetic_creation", "审美创造", 4, 1, STAGE_ALL),
    (9401, "english_language_ability", "语言能力", 1, 3, STAGE_ALL),
    (9402, "english_cultural_awareness", "文化意识", 2, 3, STAGE_ALL),
    (9403, "english_thinking_quality", "思维品质", 3, 3, STAGE_ALL),
    (9404, "english_learning_ability", "学习能力", 4, 3, STAGE_ALL),
    (9601, "politics_identity", "政治认同", 1, 7, STAGE_ALL),
    (9602, "politics_scientific_spirit", "科学精神", 2, 7, STAGE_ALL),
    (9603, "politics_rule_of_law", "法治意识", 3, 7, STAGE_ALL),
    (9604, "politics_public_participation", "公共参与", 4, 7, STAGE_ALL),
    (9701, "history_materialism", "唯物史观", 1, 8, STAGE_ALL),
    (9702, "history_time_space", "时空观念", 2, 8, STAGE_ALL),
    (9703, "history_evidence", "史料实证", 3, 8, STAGE_ALL),
    (9704, "history_interpretation", "历史解释", 4, 8, STAGE_ALL),
    (9705, "history_patriotism", "家国情怀", 5, 8, STAGE_ALL),
    (9801, "geography_human_nature", "人地协调观", 1, 9, STAGE_ALL),
    (9802, "geography_comprehensive_thinking", "综合思维", 2, 9, STAGE_ALL),
    (9803, "geography_regional_cognition", "区域认知", 3, 9, STAGE_ALL),
    (9804, "geography_practice", "地理实践力", 4, 9, STAGE_ALL),
    (9901, "it_awareness", "信息意识", 1, 11, STAGE_ALL),
    (9902, "it_computational_thinking", "计算思维", 2, 11, STAGE_ALL),
    (9903, "it_digital_innovation", "数字化学习与创新", 3, 11, STAGE_ALL),
    (9904, "it_social_responsibility", "信息社会责任", 4, 11, STAGE_ALL),
    (9911, "pe_movement_ability", "运动能力", 1, 12, STAGE_ALL),
    (9912, "pe_health_behavior", "健康行为", 2, 12, STAGE_ALL),
    (9913, "pe_sports_morality", "体育品德", 3, 12, STAGE_ALL),
    (9921, "labor_concept", "劳动观念", 1, 15, STAGE_ALL),
    (9922, "labor_ability", "劳动能力", 2, 15, STAGE_ALL),
    (9923, "labor_habit_quality", "劳动习惯和品质", 3, 15, STAGE_ALL),
    (9924, "labor_spirit", "劳动精神", 4, 15, STAGE_ALL),
)

CURRICULUM_COUNTS: dict[str, int] = {
    "dict_subjects": len(SUBJECT_ROWS),
    "dict_grades": len(GRADE_ROWS),
    "dict_question_types": len(QUESTION_TYPE_ROWS),
    "dict_subject_thoughts": len(SUBJECT_THOUGHT_ROWS),
    "dict_solution_methods": len(SOLUTION_METHOD_ROWS),
    "dict_core_competencies": len(CORE_COMPETENCY_ROWS),
    "dim_knowledge_points": len(KNOWLEDGE_POINT_ROWS),
}


def curriculum_statements() -> list[tuple[str, tuple]]:
    statements: list[tuple[str, tuple]] = []
    statements.extend(
        (
            "INSERT INTO dict_subjects (id, code, name, sort_order) "
            "VALUES (?, ?, ?, ?)",
            (subject_id, code, name, subject_id),
        )
        for subject_id, code, name in SUBJECT_ROWS
    )
    statements.extend(
        (
            "INSERT INTO dict_grades (id, code, name, sort_order, stage) "
            "VALUES (?, ?, ?, ?, ?)",
            row,
        )
        for row in GRADE_ROWS
    )
    statements.extend(
        (
            "INSERT INTO dict_question_types (id, code, name, sort_order) "
            "VALUES (?, ?, ?, ?)",
            row,
        )
        for row in QUESTION_TYPE_ROWS
    )
    statements.extend(
        (
            "INSERT INTO dim_knowledge_points "
            "(id, code, name, sort_order, subject_id, parent_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            row,
        )
        for row in KNOWLEDGE_POINT_ROWS
    )
    statements.extend(
        (
            "INSERT INTO dict_subject_thoughts "
            "(id, code, name, sort_order, subject_id, stage) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            row,
        )
        for row in SUBJECT_THOUGHT_ROWS
    )
    statements.extend(
        (
            "INSERT INTO dict_solution_methods "
            "(id, code, name, sort_order, subject_id, stage) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            row,
        )
        for row in SOLUTION_METHOD_ROWS
    )
    statements.extend(
        (
            "INSERT INTO dict_core_competencies "
            "(id, code, name, sort_order, subject_id, stage) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            row,
        )
        for row in CORE_COMPETENCY_ROWS
    )
    return statements

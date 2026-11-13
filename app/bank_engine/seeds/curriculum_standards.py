"""国家课标原文清单：核心素养与学科思想，逐学段分列。

依据：
- 《普通高中课程方案和语文等学科课程标准（2017 年版 2020 年修订）》；
- 《义务教育课程方案和课程标准（2022 年版）》。

硬口径：
1. 学科名称、素养名称一律照抄课标原文，不加学科后缀、不改写、不合并；
2. 同一名称在不同学段都属于官方表述时，按学段各存一行，不写「全学段」；
3. 课标没有单列「学科思想」的学科，只收该学科教研大纲稳定沿用的通用思想名，
   不写自造词；暂未整理的学段留空，宁缺毋滥。
"""

from __future__ import annotations

# 学科思想：只收课标或教研口径明确出现的名称，并按学段分列。
# id / code / name / sort_order / subject_id / stage
SUBJECT_THOUGHT_ROWS: tuple[tuple[int, str, str, int, int, str], ...] = (
    (9001, 'math_number_shape_primary', '数形结合', 1, 2, '小学'),
    (9002, 'math_number_shape_junior', '数形结合', 1, 2, '初中'),
    (9003, 'math_abstraction_thought', '数学抽象', 1, 2, '高中'),
    (9004, 'math_logical_reasoning_thought', '逻辑推理', 2, 2, '高中'),
    (9005, 'math_modeling_thought', '数学建模', 3, 2, '高中'),
    (9006, 'math_number_shape_senior', '数形结合', 4, 2, '高中'),
    # 物理：课标未单列「学科思想」清单，按初高中物理教研大纲的通用思想名整理。
    (9121, 'physics_junior_ideal_model_thought', '理想模型', 1, 4, '初中'),
    (9122, 'physics_junior_equivalent_substitution_thought', '等效替代', 2, 4, '初中'),
    (9123, 'physics_junior_control_variable_thought', '控制变量', 3, 4, '初中'),
    (9124, 'physics_junior_ratio_definition_thought', '比值定义', 4, 4, '初中'),
    (9125, 'physics_junior_conversion_thought', '转换', 5, 4, '初中'),
    (9126, 'physics_junior_analogy_thought', '类比', 6, 4, '初中'),
    (9127, 'physics_junior_comparison_thought', '比较', 7, 4, '初中'),
    (9128, 'physics_junior_induction_thought', '归纳', 8, 4, '初中'),
    (9129, 'physics_junior_reasoning_thought', '科学推理', 9, 4, '初中'),
    (9130, 'physics_junior_conservation_thought', '守恒', 10, 4, '初中'),
    (9131, 'physics_junior_number_shape_thought', '数形结合', 11, 4, '初中'),
    (9101, 'physics_ideal_model_thought', '理想模型', 1, 4, '高中'),
    (9102, 'physics_equivalent_substitution_thought', '等效替代', 2, 4, '高中'),
    (9103, 'physics_control_variable_thought', '控制变量', 3, 4, '高中'),
    (9104, 'physics_infinitesimal_thought', '微元', 4, 4, '高中'),
    (9105, 'physics_limit_thought', '极限', 5, 4, '高中'),
    (9106, 'physics_symmetry_thought', '对称', 6, 4, '高中'),
    (9107, 'physics_conservation_thought', '守恒', 7, 4, '高中'),
    (9108, 'physics_analogy_thought', '类比', 8, 4, '高中'),
    (9109, 'physics_number_shape_thought', '数形结合', 9, 4, '高中'),
    (9110, 'physics_experimental_induction_thought', '实验归纳', 10, 4, '高中'),
    (9111, 'physics_hypothesis_thought', '科学假说', 11, 4, '高中'),
    (9112, 'physics_transformation_thought', '转化', 12, 4, '高中'),
)

# (subject_id, stage, id_base, ((code, name), ...))
_COMPETENCY_GROUPS: tuple[
    tuple[int, str, int, tuple[tuple[str, str], ...]], ...
] = (
    # 数学：义务教育 2022 分小学 11 条、初中 9 条；高中 2017/2020 六条。
    (2, "小学", 9000, (
        ("math_primary_number_sense", "数感"),
        ("math_primary_quantity_sense", "量感"),
        ("math_primary_symbol_awareness", "符号意识"),
        ("math_primary_operation_ability", "运算能力"),
        ("math_primary_geometric_intuition", "几何直观"),
        ("math_primary_spatial_concept", "空间观念"),
        ("math_primary_reasoning_awareness", "推理意识"),
        ("math_primary_data_awareness", "数据意识"),
        ("math_primary_model_awareness", "模型意识"),
        ("math_primary_application_awareness", "应用意识"),
        ("math_primary_innovation_awareness", "创新意识"),
    )),
    (2, "初中", 9011, (
        ("math_junior_abstraction_ability", "抽象能力"),
        ("math_junior_operation_ability", "运算能力"),
        ("math_junior_geometric_intuition", "几何直观"),
        ("math_junior_spatial_concept", "空间观念"),
        ("math_junior_reasoning_ability", "推理能力"),
        ("math_junior_data_concept", "数据观念"),
        ("math_junior_model_concept", "模型观念"),
        ("math_junior_application_awareness", "应用意识"),
        ("math_junior_innovation_awareness", "创新意识"),
    )),
    (2, "高中", 9020, (
        ("math_abstraction", "数学抽象"),
        ("math_logical_reasoning", "逻辑推理"),
        ("math_modeling", "数学建模"),
        ("math_intuitive_imagination", "直观想象"),
        ("math_operation", "数学运算"),
        ("math_data_analysis", "数据分析"),
    )),
    # 物理：义务教育 2022 与高中 2017/2020 同为四条。
    (4, "初中", 9100, (
        ("physics_junior_concept", "物理观念"),
        ("physics_junior_scientific_thinking", "科学思维"),
        ("physics_junior_inquiry", "科学探究"),
        ("physics_junior_attitude", "科学态度与责任"),
    )),
    (4, "高中", 9110, (
        ("physics_senior_concept", "物理观念"),
        ("physics_senior_scientific_thinking", "科学思维"),
        ("physics_senior_inquiry", "科学探究"),
        ("physics_senior_attitude", "科学态度与责任"),
    )),
    # 化学：义务教育 2022 四条；高中 2017/2020 五条。
    (5, "初中", 9200, (
        ("chem_junior_concept", "化学观念"),
        ("chem_junior_scientific_thinking", "科学思维"),
        ("chem_junior_inquiry_practice", "科学探究与实践"),
        ("chem_junior_attitude", "科学态度与责任"),
    )),
    (5, "高中", 9210, (
        ("chem_macro_micro_analysis", "宏观辨识与微观探析"),
        ("chem_change_equilibrium", "变化观念与平衡思想"),
        ("chem_evidence_model", "证据推理与模型认知"),
        ("chem_inquiry_innovation", "科学探究与创新意识"),
        ("chem_social_responsibility", "科学态度与社会责任"),
    )),
    # 语文：义务教育 2022 与高中 2017/2020 同为四条。
    (1, "小学", 9300, (
        ("chinese_primary_cultural_confidence", "文化自信"),
        ("chinese_primary_language_use", "语言运用"),
        ("chinese_primary_thinking", "思维能力"),
        ("chinese_primary_aesthetic_creation", "审美创造"),
    )),
    (1, "初中", 9310, (
        ("chinese_junior_cultural_confidence", "文化自信"),
        ("chinese_junior_language_use", "语言运用"),
        ("chinese_junior_thinking", "思维能力"),
        ("chinese_junior_aesthetic_creation", "审美创造"),
    )),
    (1, "高中", 9320, (
        ("chinese_senior_cultural_confidence", "文化自信"),
        ("chinese_senior_language_use", "语言运用"),
        ("chinese_senior_thinking", "思维能力"),
        ("chinese_senior_aesthetic_creation", "审美创造"),
    )),
    # 英语：义务教育 2022 与高中 2017/2020 同为四条。
    (3, "小学", 9400, (
        ("english_primary_language_ability", "语言能力"),
        ("english_primary_cultural_awareness", "文化意识"),
        ("english_primary_thinking_quality", "思维品质"),
        ("english_primary_learning_ability", "学习能力"),
    )),
    (3, "初中", 9410, (
        ("english_junior_language_ability", "语言能力"),
        ("english_junior_cultural_awareness", "文化意识"),
        ("english_junior_thinking_quality", "思维品质"),
        ("english_junior_learning_ability", "学习能力"),
    )),
    (3, "高中", 9420, (
        ("english_senior_language_ability", "语言能力"),
        ("english_senior_cultural_awareness", "文化意识"),
        ("english_senior_thinking_quality", "思维品质"),
        ("english_senior_learning_ability", "学习能力"),
    )),
    # 生物：义务教育 2022 四条；高中 2017/2020 四条。
    (6, "初中", 9500, (
        ("bio_junior_life_concept", "生命观念"),
        ("bio_junior_scientific_thinking", "科学思维"),
        ("bio_junior_inquiry_practice", "探究实践"),
        ("bio_junior_attitude", "态度责任"),
    )),
    (6, "高中", 9510, (
        ("bio_life_concept", "生命观念"),
        ("bio_scientific_thinking", "科学思维"),
        ("bio_inquiry", "科学探究"),
        ("bio_social_responsibility", "社会责任"),
    )),
    # 政治：义务教育道德与法治 2022 五条；高中思想政治 2017/2020 四条。
    (7, "小学", 9600, (
        ("politics_primary_identity", "政治认同"),
        ("politics_primary_moral_cultivation", "道德修养"),
        ("politics_primary_rule_of_law_concept", "法治观念"),
        ("politics_primary_healthy_personality", "健全人格"),
        ("politics_primary_responsibility_awareness", "责任意识"),
    )),
    (7, "初中", 9610, (
        ("politics_junior_identity", "政治认同"),
        ("politics_junior_moral_cultivation", "道德修养"),
        ("politics_junior_rule_of_law_concept", "法治观念"),
        ("politics_junior_healthy_personality", "健全人格"),
        ("politics_junior_responsibility_awareness", "责任意识"),
    )),
    (7, "高中", 9620, (
        ("politics_identity", "政治认同"),
        ("politics_scientific_spirit", "科学精神"),
        ("politics_rule_of_law", "法治意识"),
        ("politics_public_participation", "公共参与"),
    )),
    # 历史：义务教育 2022 与高中 2017/2020 同为五条。
    (8, "初中", 9700, (
        ("history_junior_materialism", "唯物史观"),
        ("history_junior_time_space", "时空观念"),
        ("history_junior_evidence", "史料实证"),
        ("history_junior_interpretation", "历史解释"),
        ("history_junior_patriotism", "家国情怀"),
    )),
    (8, "高中", 9710, (
        ("history_materialism", "唯物史观"),
        ("history_time_space", "时空观念"),
        ("history_evidence", "史料实证"),
        ("history_interpretation", "历史解释"),
        ("history_patriotism", "家国情怀"),
    )),
    # 地理：义务教育 2022 与高中 2017/2020 同为四条。
    (9, "初中", 9800, (
        ("geography_junior_human_nature", "人地协调观"),
        ("geography_junior_comprehensive_thinking", "综合思维"),
        ("geography_junior_regional_cognition", "区域认知"),
        ("geography_junior_practice", "地理实践力"),
    )),
    (9, "高中", 9810, (
        ("geography_human_nature", "人地协调观"),
        ("geography_comprehensive_thinking", "综合思维"),
        ("geography_regional_cognition", "区域认知"),
        ("geography_practice", "地理实践力"),
    )),
    # 信息科技：义务教育 2022 四条；高中信息技术 2017/2020 同名四条。
    (11, "小学", 9900, (
        ("it_primary_awareness", "信息意识"),
        ("it_primary_computational_thinking", "计算思维"),
        ("it_primary_digital_innovation", "数字化学习与创新"),
        ("it_primary_social_responsibility", "信息社会责任"),
    )),
    (11, "初中", 9910, (
        ("it_junior_awareness", "信息意识"),
        ("it_junior_computational_thinking", "计算思维"),
        ("it_junior_digital_innovation", "数字化学习与创新"),
        ("it_junior_social_responsibility", "信息社会责任"),
    )),
    (11, "高中", 9920, (
        ("it_senior_awareness", "信息意识"),
        ("it_senior_computational_thinking", "计算思维"),
        ("it_senior_digital_innovation", "数字化学习与创新"),
        ("it_senior_social_responsibility", "信息社会责任"),
    )),
    # 体育与健康：义务教育 2022 与高中 2017/2020 同为三条。
    (12, "小学", 9930, (
        ("pe_primary_movement_ability", "运动能力"),
        ("pe_primary_health_behavior", "健康行为"),
        ("pe_primary_sports_morality", "体育品德"),
    )),
    (12, "初中", 9933, (
        ("pe_junior_movement_ability", "运动能力"),
        ("pe_junior_health_behavior", "健康行为"),
        ("pe_junior_sports_morality", "体育品德"),
    )),
    (12, "高中", 9936, (
        ("pe_senior_movement_ability", "运动能力"),
        ("pe_senior_health_behavior", "健康行为"),
        ("pe_senior_sports_morality", "体育品德"),
    )),
    # 科学：义务教育 2022 四条，覆盖小学与初中。
    (10, "小学", 9940, (
        ("science_primary_concept", "科学观念"),
        ("science_primary_thinking", "科学思维"),
        ("science_primary_inquiry", "探究实践"),
        ("science_primary_attitude", "态度责任"),
    )),
    (10, "初中", 9944, (
        ("science_junior_concept", "科学观念"),
        ("science_junior_thinking", "科学思维"),
        ("science_junior_inquiry", "探究实践"),
        ("science_junior_attitude", "态度责任"),
    )),
    # 音乐：义务教育艺术 2022 四条；高中音乐 2017/2020 三条。
    (13, "小学", 9950, (
        ("music_primary_aesthetic_perception", "审美感知"),
        ("music_primary_artistic_expression", "艺术表现"),
        ("music_primary_creative_practice", "创意实践"),
        ("music_primary_cultural_understanding", "文化理解"),
    )),
    (13, "初中", 9954, (
        ("music_junior_aesthetic_perception", "审美感知"),
        ("music_junior_artistic_expression", "艺术表现"),
        ("music_junior_creative_practice", "创意实践"),
        ("music_junior_cultural_understanding", "文化理解"),
    )),
    (13, "高中", 9958, (
        ("music_senior_aesthetic_perception", "审美感知"),
        ("music_senior_artistic_expression", "艺术表现"),
        ("music_senior_cultural_understanding", "文化理解"),
    )),
    # 美术：义务教育艺术 2022 四条；高中美术 2017/2020 五条。
    (14, "小学", 9970, (
        ("art_primary_aesthetic_perception", "审美感知"),
        ("art_primary_artistic_expression", "艺术表现"),
        ("art_primary_creative_practice", "创意实践"),
        ("art_primary_cultural_understanding", "文化理解"),
    )),
    (14, "初中", 9974, (
        ("art_junior_aesthetic_perception", "审美感知"),
        ("art_junior_artistic_expression", "艺术表现"),
        ("art_junior_creative_practice", "创意实践"),
        ("art_junior_cultural_understanding", "文化理解"),
    )),
    (14, "高中", 9978, (
        ("art_senior_image_reading", "图像识读"),
        ("art_senior_artistic_expression", "美术表现"),
        ("art_senior_aesthetic_judgment", "审美判断"),
        ("art_senior_creative_practice", "创意实践"),
        ("art_senior_cultural_understanding", "文化理解"),
    )),
    # 劳动：义务教育劳动 2022 四条，覆盖小学与初中。
    (15, "小学", 9990, (
        ("labor_primary_concept", "劳动观念"),
        ("labor_primary_ability", "劳动能力"),
        ("labor_primary_habit_quality", "劳动习惯和品质"),
        ("labor_primary_spirit", "劳动精神"),
    )),
    (15, "初中", 9994, (
        ("labor_junior_concept", "劳动观念"),
        ("labor_junior_ability", "劳动能力"),
        ("labor_junior_habit_quality", "劳动习惯和品质"),
        ("labor_junior_spirit", "劳动精神"),
    )),
)


def _competency_rows() -> tuple[tuple[int, str, str, int, int, str], ...]:
    rows: list[tuple[int, str, str, int, int, str]] = []
    for subject_id, stage, id_base, items in _COMPETENCY_GROUPS:
        for index, (code, name) in enumerate(items, start=1):
            rows.append((id_base + index, code, name, index, subject_id, stage))
    return tuple(rows)


CORE_COMPETENCY_ROWS = _competency_rows()

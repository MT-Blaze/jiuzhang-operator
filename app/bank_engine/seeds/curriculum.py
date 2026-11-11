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
    (9001, "math_number_shape", "数形结合思想", 1, SUBJECT_MATH_ID, STAGE_ALL),
    (9002, "math_function_equation", "函数与方程思想", 2, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9003, "math_transformation", "转化与化归思想", 3, SUBJECT_MATH_ID, STAGE_ALL),
    (9004, "math_classification", "分类讨论思想", 4, SUBJECT_MATH_ID, STAGE_ALL),
    (9005, "math_special_general", "特殊与一般思想", 5, SUBJECT_MATH_ID, STAGE_ALL),
    (9006, "math_function_thought", "函数思想", 6, SUBJECT_MATH_ID, STAGE_ALL),
    (9007, "math_modeling_thought", "建模思想", 7, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9008, "math_limit_thought", "极限思想", 8, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9009, "math_statistics_thought", "统计思想", 9, SUBJECT_MATH_ID, STAGE_ALL),
    (9010, "math_algorithm_thought", "算法思想", 10, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9011, "math_holistic_thought", "整体思想", 11, SUBJECT_MATH_ID, STAGE_ALL),
    (9012, "math_analogy_thought", "类比思想", 12, SUBJECT_MATH_ID, STAGE_ALL),
    (9013, "math_induction_thought", "归纳思想", 13, SUBJECT_MATH_ID, STAGE_ALL),
    # 义务教育阶段常用的基本思想：方程、模型、抽象、推理三条为全学段通用口径。
    (9601, "math_equation_thought", "方程思想", 70, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9602, "math_model_thought", "模型思想", 71, SUBJECT_MATH_ID, STAGE_ALL),
    (9603, "math_abstraction_thought", "抽象思想", 72, SUBJECT_MATH_ID, STAGE_ALL),
    (9604, "math_reasoning_thought", "推理思想", 73, SUBJECT_MATH_ID, STAGE_ALL),
    (9605, "math_correspondence_thought", "对应思想", 74, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9606, "math_symbol_thought", "符号思想", 75, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9607, "math_set_thought", "集合思想", 76, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9101, "physics_equivalent_substitution", "等效替代", 1, 4, STAGE_ALL),
    (9102, "physics_conservation", "守恒思想", 2, 4, STAGE_ALL),
    (9103, "physics_idealization", "理想化思想", 3, 4, STAGE_ALL),
    (9104, "physics_symmetry", "对称思想", 4, 4, STAGE_ALL),
    (9110, "physics_infinitesimal_thought", "微元思想", 5, 4, STAGE_ALL),
    (9111, "physics_limit_thought", "极限思想", 6, 4, STAGE_ALL),
    (9112, "physics_number_shape_thought", "数形结合思想", 7, 4, STAGE_ALL),
    (9113, "physics_control_variable_thought", "控制变量思想", 8, 4, STAGE_ALL),
    (9114, "physics_conversion_thought", "转换思想", 9, 4, STAGE_ALL),
    (9115, "physics_analogy_thought", "类比思想", 10, 4, STAGE_ALL),
    (9116, "physics_system_thought", "系统思想", 11, 4, STAGE_ALL),
    (9117, "physics_modeling_thought", "建模思想", 12, 4, STAGE_ALL),
    # 初中物理起步阶段就要求建立的两种思想。
    (9641, "physics_model_construction_thought", "模型建构思想", 70, 4, STAGE_JUNIOR),
    (9642, "physics_experiment_thought", "实验思想", 71, 4, STAGE_JUNIOR),
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
    (9501, "bio_structure_function", "结构与功能观", 1, 6, STAGE_ALL),
    (9502, "bio_evolution_adaptation", "进化与适应观", 2, 6, STAGE_ALL),
    (9503, "bio_homeostasis", "稳态与平衡观", 3, 6, STAGE_ALL),
    (9504, "bio_matter_energy", "物质与能量观", 4, 6, STAGE_ALL),
)

# id / code / name / sort_order / subject_id / stage
SOLUTION_METHOD_ROWS: tuple[tuple[int, str, str, int, int, str], ...] = (
    (9001, "math_definition", "定义法", 1, SUBJECT_MATH_ID, STAGE_ALL),
    (9002, "math_substitution", "换元法", 2, SUBJECT_MATH_ID, STAGE_ALL),
    (9003, "math_completing_square", "配方法", 3, SUBJECT_MATH_ID, STAGE_ALL),
    (9004, "math_undetermined", "待定系数法", 4, SUBJECT_MATH_ID, STAGE_ALL),
    (9005, "math_shift_subtract", "错位相减", 5, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9006, "math_telescoping", "裂项相消", 6, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9007, "math_discriminant", "判别式法", 7, SUBJECT_MATH_ID, STAGE_ALL),
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
    (9011, "math_contradiction", "反证法", 11, SUBJECT_MATH_ID, STAGE_ALL),
    (9021, "math_separation_parameter", "分离参数法", 12, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9022, "math_number_shape_method", "数形结合法", 13, SUBJECT_MATH_ID, STAGE_ALL),
    (9023, "math_scaling", "放缩法", 14, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9024, "math_reverse_sum", "倒序相加法", 15, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9025, "math_hidden_zero", "隐零点法", 16, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9026, "math_extremum_shift", "极值点偏移法", 17, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9027, "math_main_variable", "变更主元法", 18, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9028, "math_vector_method", "向量法", 19, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9029, "math_coordinate_method", "坐标法", 20, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9030, "math_geometric_transform", "几何变换法", 21, SUBJECT_MATH_ID, STAGE_ALL),
    (9031, "math_dissection", "割补法", 22, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9032, "math_equal_volume", "等体积法", 23, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9033, "math_point_difference", "点差法", 24, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9034, "math_formula_method", "公式法", 25, SUBJECT_MATH_ID, STAGE_ALL),
    (9035, "math_substitution_elimination", "代入消元法", 26, SUBJECT_MATH_ID, STAGE_ALL),
    (9036, "math_add_sub_elimination", "加减消元法", 27, SUBJECT_MATH_ID, STAGE_ALL),
    (9037, "math_factorization_method", "因式分解法", 28, SUBJECT_MATH_ID, STAGE_ALL),
    (9038, "math_matching_method", "配凑法", 29, SUBJECT_MATH_ID, STAGE_ALL),
    (9039, "math_analysis_method", "分析法", 30, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9040, "math_synthesis_method", "综合法", 31, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9041, "math_comparison_method", "比较法", 32, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9042, "math_basic_inequality", "基本不等式法", 33, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9043, "math_trig_substitution", "三角换元法", 34, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9044, "math_auxiliary_angle", "辅助角公式法", 35, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9045, "math_tangent_to_sine", "切化弦法", 36, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9046, "math_holistic_substitution", "整体代换法", 37, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9047, "math_set_without_solving", "设而不求法", 38, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9048, "math_vieta", "韦达定理法", 39, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9049, "math_chord_length", "弦长公式法", 40, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9050, "math_direct_locus", "直接法", 41, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9051, "math_related_point", "相关点法", 42, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9052, "math_parametric_locus", "参数法", 43, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9053, "math_intersection_locus", "交轨法", 44, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9054, "math_space_vector", "空间向量法", 45, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9055, "math_basis_vector", "基底法", 46, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9056, "math_net_unfold", "展开图法", 47, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9057, "math_cross_section", "截面法", 48, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9058, "math_symmetry_method", "对称法", 49, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9059, "math_separation_constant", "分离常数法", 50, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9060, "math_monotonicity_method", "单调性法", 51, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9061, "math_boundedness_method", "有界性法", 52, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9062, "math_accumulation_add", "累加法", 53, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9063, "math_accumulation_multiply", "累乘法", 54, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9064, "math_group_sum", "分组求和法", 55, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9065, "math_pair_sum", "并项求和法", 56, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9066, "math_assignment_method", "赋值法", 57, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9067, "math_homogeneous_method", "齐次化法", 58, SUBJECT_MATH_ID, STAGE_SENIOR),
    (9068, "math_special_value_method", "特殊值法", 59, SUBJECT_MATH_ID, STAGE_ALL),
    (9069, "math_exclusion_method", "排除法", 60, SUBJECT_MATH_ID, STAGE_ALL),
    (9070, "math_estimation_method", "估算法", 61, SUBJECT_MATH_ID, STAGE_ALL),
    (9071, "math_verification_method", "验证法", 62, SUBJECT_MATH_ID, STAGE_ALL),
    # 初中数学：几何证明、方程不等式与概率统计的常用解法。
    (9601, "math_area_method", "面积法", 70, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9602, "math_cut_patch", "截长补短法", 71, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9603, "math_classification_method", "分类讨论法", 72, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9604, "math_median_doubling", "倍长中线法", 73, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9605, "math_cross_multiplication", "十字相乘法", 74, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9606, "math_common_factor", "提公因式法", 75, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9607, "math_group_factorization", "分组分解法", 76, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9608, "math_identity_method", "同一法", 77, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9609, "math_similarity_method", "相似三角形法", 78, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9610, "math_congruence_method", "全等三角形法", 79, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9611, "math_pythagorean_method", "勾股定理法", 80, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9612, "math_acute_trig_function", "锐角三角函数法", 81, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9613, "math_equation_method", "方程法", 82, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9614, "math_inequality_method", "不等式法", 83, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9615, "math_number_line_method", "数轴法", 84, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9616, "math_translation_method", "平移法", 85, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9617, "math_rotation_method", "旋转法", 86, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9618, "math_folding_method", "翻折法", 87, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9619, "math_auxiliary_line", "辅助线法", 88, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9620, "math_counterexample", "举反例法", 89, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9621, "math_function_method", "函数法", 90, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9622, "math_tree_diagram", "树状图法", 91, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9623, "math_ruler_compass", "尺规作图法", 92, SUBJECT_MATH_ID, STAGE_JUNIOR),
    # 小学数学：认数计算、解决问题与数学广角的核心策略。
    (9641, "math_drawing_primary", "画图法", 100, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9642, "math_line_segment_diagram", "线段图法", 101, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9643, "math_list_method", "列表法", 102, SUBJECT_MATH_ID, STAGE_ALL),
    (9644, "math_assumption_method", "假设法", 103, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9645, "math_conversion_method", "转化法", 104, SUBJECT_MATH_ID, STAGE_ALL),
    (9646, "math_correspondence_method", "对应法", 105, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9647, "math_algebraic_method", "代数法", 106, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9648, "math_arithmetic_method", "算术法", 107, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9649, "math_make_ten", "凑十法", 108, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9650, "math_break_ten", "破十法", 109, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9651, "math_flat_ten", "平十法", 110, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9652, "math_addition_to_subtract", "想加算减法", 111, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9653, "math_enumeration_method", "枚举法", 112, SUBJECT_MATH_ID, STAGE_ALL),
    (9654, "math_backward_reasoning", "倒推法", 113, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9655, "math_replacement_method", "替换法", 114, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9656, "math_unitary_method", "归一法", 115, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9657, "math_total_method", "归总法", 116, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9658, "math_proportion_method", "比例法", 117, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9659, "math_optimization_method", "统筹法", 118, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9660, "math_pigeonhole_method", "抽屉原理法", 119, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9101, "physics_control_variable", "控制变量法", 1, 4, STAGE_ALL),
    (9102, "physics_infinitesimal", "微元法", 2, 4, STAGE_SENIOR),
    (9103, "physics_ratio_definition", "比值定义法", 3, 4, STAGE_ALL),
    (9104, "physics_equivalent_method", "等效替代法", 4, 4, STAGE_ALL),
    (9105, "physics_graph", "图像法", 5, 4, STAGE_ALL),
    (9106, "physics_isolation", "隔离法", 6, 4, STAGE_ALL),
    (9107, "physics_whole_system", "整体法", 7, 4, STAGE_ALL),
    (9108, "physics_hypothesis", "假设法", 8, 4, STAGE_ALL),
    (9110, "physics_orthogonal_decomposition", "正交分解法", 9, 4, STAGE_SENIOR),
    (9111, "physics_force_composition", "力的合成与分解法", 10, 4, STAGE_SENIOR),
    (9112, "physics_vector_triangle", "矢量三角形法", 11, 4, STAGE_SENIOR),
    (9113, "physics_dynamic_equilibrium", "动态平衡分析法", 12, 4, STAGE_SENIOR),
    (9114, "physics_extreme_value", "极值法", 13, 4, STAGE_ALL),
    (9115, "physics_critical_state", "临界状态法", 14, 4, STAGE_SENIOR),
    (9116, "physics_symmetry_method", "对称法", 15, 4, STAGE_SENIOR),
    (9117, "physics_limit_thinking", "极限思维法", 16, 4, STAGE_SENIOR),
    (9118, "physics_analytic_method", "解析法", 17, 4, STAGE_SENIOR),
    (9119, "physics_drawing_method", "作图法", 18, 4, STAGE_ALL),
    (9120, "physics_experimental_inquiry", "实验探究法", 19, 4, STAGE_ALL),
    (9121, "physics_conversion_method", "转换法", 20, 4, STAGE_ALL),
    (9122, "physics_analogy_method", "类比法", 21, 4, STAGE_ALL),
    (9123, "physics_reverse_thinking", "逆向思维法", 22, 4, STAGE_ALL),
    (9124, "physics_whole_process", "全过程法", 23, 4, STAGE_SENIOR),
    (9125, "physics_successive_difference", "逐差法", 24, 4, STAGE_SENIOR),
    (9126, "physics_average_velocity", "平均速度法", 25, 4, STAGE_SENIOR),
    (9127, "physics_proportion_method", "比例法", 26, 4, STAGE_ALL),
    (9128, "physics_estimation_method", "估算法", 27, 4, STAGE_ALL),
    (9129, "physics_dimensional_analysis", "量纲分析法", 28, 4, STAGE_SENIOR),
    (9130, "physics_ideal_experiment", "理想实验法", 29, 4, STAGE_ALL),
    (9131, "physics_model_method", "模型法", 30, 4, STAGE_ALL),
    (9132, "physics_conservation_method", "守恒法", 31, 4, STAGE_SENIOR),
    (9133, "physics_kinetic_energy_theorem", "动能定理法", 32, 4, STAGE_SENIOR),
    (9134, "physics_momentum_theorem", "动量定理法", 33, 4, STAGE_SENIOR),
    (9135, "physics_motion_composition", "运动的合成与分解法", 34, 4, STAGE_SENIOR),
    (9136, "physics_accumulation_method", "累积法", 35, 4, STAGE_SENIOR),
    (9137, "physics_compensation_method", "补偿法", 36, 4, STAGE_SENIOR),
    (9138, "physics_amplification_method", "放大法", 37, 4, STAGE_ALL),
    (9139, "physics_extrapolation", "外推法", 38, 4, STAGE_SENIOR),
    # 初中物理：教材实验与解题中反复使用的具体方法。
    (9681, "physics_limit_method", "极限法", 70, 4, STAGE_JUNIOR),
    (9682, "physics_reasoning_method", "推理法", 71, 4, STAGE_JUNIOR),
    (9683, "physics_observation_method", "观察法", 72, 4, STAGE_JUNIOR),
    (9684, "physics_induction_method", "归纳法", 73, 4, STAGE_JUNIOR),
    (9685, "physics_comparison_method", "比较法", 74, 4, STAGE_JUNIOR),
    (9686, "physics_table_method", "表格法", 75, 4, STAGE_JUNIOR),
    (9687, "physics_formula_method", "公式法", 76, 4, STAGE_JUNIOR),
    (9688, "physics_state_analysis", "状态分析法", 77, 4, STAGE_JUNIOR),
    (9689, "physics_force_analysis", "受力分析法", 78, 4, STAGE_JUNIOR),
    (9690, "physics_circuit_analysis", "电路分析法", 79, 4, STAGE_JUNIOR),
    (9691, "physics_ray_diagram", "光路图法", 80, 4, STAGE_JUNIOR),
    (9692, "physics_data_analysis_method", "数据分析法", 81, 4, STAGE_JUNIOR),
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
    # 义务教育数学课标（2022 年版）11 个核心素养表现，小学、初中分列。
    (9631, "math_operation_ability", "运算能力", 70, SUBJECT_MATH_ID, STAGE_ALL),
    (9632, "math_geometric_intuition", "几何直观", 71, SUBJECT_MATH_ID, STAGE_ALL),
    (9633, "math_spatial_concept", "空间观念", 72, SUBJECT_MATH_ID, STAGE_ALL),
    (9634, "math_application_awareness", "应用意识", 73, SUBJECT_MATH_ID, STAGE_ALL),
    (9635, "math_innovation_awareness", "创新意识", 74, SUBJECT_MATH_ID, STAGE_ALL),
    (9641, "math_abstraction_ability", "抽象能力", 75, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9642, "math_reasoning_ability", "推理能力", 76, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9643, "math_data_concept", "数据观念", 77, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9644, "math_model_concept", "模型观念", 78, SUBJECT_MATH_ID, STAGE_JUNIOR),
    (9651, "math_number_sense", "数感", 79, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9652, "math_quantity_sense", "量感", 80, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9653, "math_symbol_awareness", "符号意识", 81, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9654, "math_reasoning_awareness", "推理意识", 82, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9655, "math_data_awareness", "数据意识", 83, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9656, "math_model_awareness", "模型意识", 84, SUBJECT_MATH_ID, STAGE_PRIMARY),
    (9101, "physics_concept", "物理观念", 1, 4, STAGE_ALL),
    (9102, "physics_scientific_thinking", "科学思维", 2, 4, STAGE_ALL),
    (9103, "physics_inquiry", "科学探究", 3, 4, STAGE_ALL),
    (9104, "physics_attitude", "科学态度与责任", 4, 4, STAGE_ALL),
    (9110, "physics_matter_concept", "物质观念", 5, 4, STAGE_ALL),
    (9111, "physics_motion_interaction_concept", "运动与相互作用观念", 6, 4, STAGE_ALL),
    (9112, "physics_energy_concept", "能量观念", 7, 4, STAGE_ALL),
    (9113, "physics_model_construction", "模型建构", 8, 4, STAGE_ALL),
    (9114, "physics_scientific_reasoning", "科学推理", 9, 4, STAGE_ALL),
    (9115, "physics_scientific_argumentation", "科学论证", 10, 4, STAGE_ALL),
    (9116, "physics_questioning_innovation", "质疑创新", 11, 4, STAGE_ALL),
    (9117, "physics_raising_questions", "提出问题", 12, 4, STAGE_ALL),
    (9118, "physics_obtaining_evidence", "获取证据", 13, 4, STAGE_ALL),
    (9119, "physics_making_explanation", "作出解释", 14, 4, STAGE_ALL),
    (9120, "physics_expression_communication", "表达交流", 15, 4, STAGE_ALL),
    (9121, "physics_nature_of_science", "科学本质", 16, 4, STAGE_ALL),
    (9122, "physics_scientific_attitude", "科学态度", 17, 4, STAGE_ALL),
    (9123, "physics_social_responsibility", "社会责任", 18, 4, STAGE_ALL),
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
    (9501, "bio_life_concept", "生命观念", 1, 6, STAGE_ALL),
    (9502, "bio_scientific_thinking", "科学思维", 2, 6, STAGE_ALL),
    (9503, "bio_inquiry", "科学探究", 3, 6, STAGE_ALL),
    (9504, "bio_social_responsibility", "社会责任", 4, 6, STAGE_ALL),
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
    # 同名课标条目按 (subject_id, name) 联合唯一，不再给名称加学科后缀。
    (9951, "science_concept", "科学观念", 1, 10, STAGE_ALL),
    (9952, "science_thinking", "科学思维", 2, 10, STAGE_ALL),
    (9953, "science_inquiry", "探究实践", 3, 10, STAGE_ALL),
    (9954, "science_attitude", "态度责任", 4, 10, STAGE_ALL),
    (9961, "music_aesthetic_perception", "审美感知", 1, 13, STAGE_ALL),
    (9962, "music_artistic_expression", "艺术表现", 2, 13, STAGE_ALL),
    (9963, "music_creative_practice", "创意实践", 3, 13, STAGE_ALL),
    (9964, "music_cultural_understanding", "文化理解", 4, 13, STAGE_ALL),
    (9971, "art_image_reading", "图像识读", 1, 14, STAGE_ALL),
    (9972, "art_artistic_expression", "美术表现", 2, 14, STAGE_ALL),
    (9973, "art_aesthetic_judgment", "审美判断", 3, 14, STAGE_ALL),
    (9974, "art_creative_practice", "创意实践", 4, 14, STAGE_ALL),
    (9975, "art_cultural_understanding", "文化理解", 5, 14, STAGE_ALL),
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

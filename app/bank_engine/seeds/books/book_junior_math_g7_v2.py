"""人教版（2012）初中数学七年级下册：章节树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G7 = 7
BOOK_ID = 1308

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版七年级数学下册",
    "jmath_g7b",
    8,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第五章 相交线与平行线
    (130801, "第五章 相交线与平行线", "jmath_g7b_c05", 1, BOOK_ID, None),
    (130811, "5.1 相交线", "jmath_g7b_s51", 1, BOOK_ID, 130801),
    (130812, "5.2 平行线及其判定", "jmath_g7b_s52", 2, BOOK_ID, 130801),
    (130813, "5.3 平行线的性质", "jmath_g7b_s53", 3, BOOK_ID, 130801),
    (130814, "5.4 平移", "jmath_g7b_s54", 4, BOOK_ID, 130801),

    # 第六章 实数
    (130802, "第六章 实数", "jmath_g7b_c06", 2, BOOK_ID, None),
    (130821, "6.1 平方根", "jmath_g7b_s61", 1, BOOK_ID, 130802),
    (130822, "6.2 立方根", "jmath_g7b_s62", 2, BOOK_ID, 130802),
    (130823, "6.3 实数", "jmath_g7b_s63", 3, BOOK_ID, 130802),

    # 第七章 平面直角坐标系
    (130803, "第七章 平面直角坐标系", "jmath_g7b_c07", 3, BOOK_ID, None),
    (130831, "7.1 平面直角坐标系", "jmath_g7b_s71", 1, BOOK_ID, 130803),
    (130832, "7.2 坐标方法的简单应用", "jmath_g7b_s72", 2, BOOK_ID, 130803),

    # 第八章 二元一次方程组
    (130804, "第八章 二元一次方程组", "jmath_g7b_c08", 4, BOOK_ID, None),
    (130841, "8.1 二元一次方程组", "jmath_g7b_s81", 1, BOOK_ID, 130804),
    (130842, "8.2 消元——解二元一次方程组", "jmath_g7b_s82", 2, BOOK_ID, 130804),
    (130843, "8.3 实际问题与二元一次方程组", "jmath_g7b_s83", 3, BOOK_ID, 130804),
    (130844, "8.4 三元一次方程组的解法", "jmath_g7b_s84", 4, BOOK_ID, 130804),

    # 第九章 不等式与不等式组
    (130805, "第九章 不等式与不等式组", "jmath_g7b_c09", 5, BOOK_ID, None),
    (130851, "9.1 不等式", "jmath_g7b_s91", 1, BOOK_ID, 130805),
    (130852, "9.2 一元一次不等式", "jmath_g7b_s92", 2, BOOK_ID, 130805),
    (130853, "9.3 一元一次不等式组", "jmath_g7b_s93", 3, BOOK_ID, 130805),

    # 第十章 数据的收集、整理与描述
    (130806, "第十章 数据的收集、整理与描述", "jmath_g7b_c10", 6, BOOK_ID, None),
    (130861, "10.1 统计调查", "jmath_g7b_s101", 1, BOOK_ID, 130806),
    (130862, "10.2 直方图", "jmath_g7b_s102", 2, BOOK_ID, 130806),
    (130863, "10.3 课题学习 从数据谈节水", "jmath_g7b_s103", 3, BOOK_ID, 130806),
)

# id / code / name / sort_order / subject_id / parent_id
# 208001-208009 为册域层，208011-208094 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (208001, "jmath_g7b_domain_intersect", "初中七下·相交线与垂线", 1, SUBJECT, None),
    (208002, "jmath_g7b_domain_parallel", "初中七下·平行线的判定与性质", 2, SUBJECT, None),
    (208003, "jmath_g7b_domain_translation", "初中七下·平移与命题证明", 3, SUBJECT, None),
    (208004, "jmath_g7b_domain_real", "初中七下·平方根、立方根与实数", 4, SUBJECT, None),
    (208005, "jmath_g7b_domain_coordinate", "初中七下·平面直角坐标系", 5, SUBJECT, None),
    (208006, "jmath_g7b_domain_linear_system", "初中七下·二元一次方程组解法", 6, SUBJECT, None),
    (208007, "jmath_g7b_domain_linear_app", "初中七下·二元一次方程组应用", 7, SUBJECT, None),
    (208008, "jmath_g7b_domain_inequality", "初中七下·不等式与不等式组", 8, SUBJECT, None),
    (208009, "jmath_g7b_domain_statistics", "初中七下·数据收集整理与直方图", 9, SUBJECT, None),

    # 相交线与垂线
    (208011, "jmath_g7b_point_vertical_angle", "对顶角的定义与对顶角相等的性质", 1, SUBJECT, 208001),
    (208012, "jmath_g7b_point_adjacent_angle", "邻补角的定义及邻补角互补的角度计算", 2, SUBJECT, 208001),
    (208013, "jmath_g7b_point_angle_identify", "对顶角与邻补角在复杂图形中的辨认", 3, SUBJECT, 208001),
    (208014, "jmath_g7b_point_perpendicular_def", "垂直的定义与垂线的两种画法", 4, SUBJECT, 208001),
    (208015, "jmath_g7b_point_perpendicular_unique", "垂线性质：过一点有且只有一条直线与已知直线垂直", 5, SUBJECT, 208001),
    (208016, "jmath_g7b_point_shortest_segment", "垂线段最短与点到直线的距离", 6, SUBJECT, 208001),
    (208017, "jmath_g7b_point_three_angle_pairs", "同位角、内错角、同旁内角的识别", 7, SUBJECT, 208001),
    (208018, "jmath_g7b_point_three_angle_variant", "三线八角图形变式中的角关系判断", 8, SUBJECT, 208001),
    (208019, "jmath_g7b_point_intersect_angle_calc", "相交线中结合对顶角与垂线的角度计算", 9, SUBJECT, 208001),
    (208020, "jmath_g7b_point_perpendicular_app", "垂线段最短在测量与路径最短问题中的应用", 10, SUBJECT, 208001),

    # 平行线的判定与性质
    (208021, "jmath_g7b_point_parallel_def", "同一平面内两条直线的位置关系与平行线定义", 1, SUBJECT, 208002),
    (208022, "jmath_g7b_point_parallel_postulate", "平行公理及其推论：平行于同一直线的两直线平行", 2, SUBJECT, 208002),
    (208023, "jmath_g7b_point_judge_corresponding", "判定定理：同位角相等，两直线平行", 3, SUBJECT, 208002),
    (208024, "jmath_g7b_point_judge_alternate", "判定定理：内错角相等，两直线平行", 4, SUBJECT, 208002),
    (208025, "jmath_g7b_point_judge_consecutive", "判定定理：同旁内角互补，两直线平行", 5, SUBJECT, 208002),
    (208026, "jmath_g7b_point_judge_comprehensive", "平行线判定的综合推理与书写规范", 6, SUBJECT, 208002),
    (208027, "jmath_g7b_point_property_corresponding", "性质定理：两直线平行，同位角相等", 7, SUBJECT, 208002),
    (208028, "jmath_g7b_point_property_alternate", "性质定理：两直线平行，内错角相等", 8, SUBJECT, 208002),
    (208029, "jmath_g7b_point_property_consecutive", "性质定理：两直线平行，同旁内角互补", 9, SUBJECT, 208002),
    (208030, "jmath_g7b_point_judge_vs_property", "平行线判定与性质的条件结论互逆辨析", 10, SUBJECT, 208002),
    (208031, "jmath_g7b_point_zigzag_parallel", "平行线间拐点问题与辅助线构造", 11, SUBJECT, 208002),
    (208032, "jmath_g7b_point_parallel_distance", "两平行线间的距离与等底等高面积转化", 12, SUBJECT, 208002),

    # 平移与命题证明
    (208033, "jmath_g7b_point_translation_concept", "平移的概念及平移的方向与距离", 1, SUBJECT, 208003),
    (208034, "jmath_g7b_point_translation_property", "平移的性质：对应线段平行（共线）且相等", 2, SUBJECT, 208003),
    (208035, "jmath_g7b_point_translation_draw", "平移作图与坐标系中图形平移的坐标变化", 3, SUBJECT, 208003),
    (208036, "jmath_g7b_point_translation_area", "利用平移求不规则图形的周长与面积", 4, SUBJECT, 208003),
    (208037, "jmath_g7b_point_proposition_parts", "命题的组成：题设与结论的划分", 5, SUBJECT, 208003),
    (208038, "jmath_g7b_point_true_false_proposition", "真命题、假命题的判定与举反例", 6, SUBJECT, 208003),
    (208039, "jmath_g7b_point_proof_writing", "定理与证明的书写步骤及推理依据", 7, SUBJECT, 208003),

    # 平方根、立方根与实数
    (208040, "jmath_g7b_point_arithmetic_sqrt", "算术平方根的定义、符号表示与求法", 1, SUBJECT, 208004),
    (208041, "jmath_g7b_point_square_root", "平方根的定义及正数有两个互为相反数的平方根", 2, SUBJECT, 208004),
    (208042, "jmath_g7b_point_sqrt_relation", "平方根与算术平方根的区别与联系", 3, SUBJECT, 208004),
    (208043, "jmath_g7b_point_sqrt_property", "开平方运算与平方根的非负性", 4, SUBJECT, 208004),
    (208044, "jmath_g7b_point_cube_root", "立方根的定义与开立方运算", 5, SUBJECT, 208004),
    (208045, "jmath_g7b_point_cube_root_property", "立方根的性质：正负数的立方根符号不变", 6, SUBJECT, 208004),
    (208046, "jmath_g7b_point_irrational", "无理数的认识与常见无理数的判别", 7, SUBJECT, 208004),
    (208047, "jmath_g7b_point_real_classification", "实数的分类及实数与数轴上的点一一对应", 8, SUBJECT, 208004),
    (208048, "jmath_g7b_point_real_compare", "实数的大小比较与无理数的估算", 9, SUBJECT, 208004),
    (208049, "jmath_g7b_point_real_operation", "实数的相反数、绝对值与混合运算", 10, SUBJECT, 208004),

    # 平面直角坐标系
    (208050, "jmath_g7b_point_ordered_pair", "有序数对与平面直角坐标系的建立", 1, SUBJECT, 208005),
    (208051, "jmath_g7b_point_quadrant_sign", "各象限内点的坐标符号规律", 2, SUBJECT, 208005),
    (208052, "jmath_g7b_point_axis_point", "坐标轴上点的坐标特征与原点坐标", 3, SUBJECT, 208005),
    (208053, "jmath_g7b_point_point_distance", "点到坐标轴的距离与坐标的绝对值关系", 4, SUBJECT, 208005),
    (208054, "jmath_g7b_point_parallel_axis", "平行于坐标轴的直线上点的坐标特征", 5, SUBJECT, 208005),
    (208055, "jmath_g7b_point_location_coordinate", "用坐标表示地理位置与方向距离描述", 6, SUBJECT, 208005),
    (208056, "jmath_g7b_point_translate_coordinate", "用坐标表示平移及左右上下平移的坐标变化", 7, SUBJECT, 208005),
    (208057, "jmath_g7b_point_figure_translate", "图形在坐标系中的平移与对应点坐标", 8, SUBJECT, 208005),
    (208058, "jmath_g7b_point_triangle_area", "坐标系中三角形面积的割补计算", 9, SUBJECT, 208005),
    (208059, "jmath_g7b_point_symmetry_coordinate", "关于坐标轴及原点对称的点的坐标规律", 10, SUBJECT, 208005),

    # 二元一次方程组解法
    (208060, "jmath_g7b_point_linear_eq_two", "二元一次方程的定义与解的不唯一性", 1, SUBJECT, 208006),
    (208061, "jmath_g7b_point_system_concept", "二元一次方程组及其解的含义与检验", 2, SUBJECT, 208006),
    (208062, "jmath_g7b_point_substitution", "代入消元法解二元一次方程组", 3, SUBJECT, 208006),
    (208063, "jmath_g7b_point_elimination", "加减消元法解二元一次方程组", 4, SUBJECT, 208006),
    (208064, "jmath_g7b_point_method_choice", "消元思想与代入、加减消元法的选择策略", 5, SUBJECT, 208006),
    (208065, "jmath_g7b_point_param_system", "含参数二元一次方程组的解与参数求值", 6, SUBJECT, 208006),
    (208066, "jmath_g7b_point_three_variable", "三元一次方程组的消元解法", 7, SUBJECT, 208006),
    (208067, "jmath_g7b_point_system_check", "方程组的错解分析与解的回代检验", 8, SUBJECT, 208006),

    # 二元一次方程组应用
    (208068, "jmath_g7b_point_app_steps", "列方程组解应用题：设元、找等量关系与检验", 1, SUBJECT, 208007),
    (208069, "jmath_g7b_point_sum_multiple_app", "和差倍分问题与配套问题的方程组模型", 2, SUBJECT, 208007),
    (208070, "jmath_g7b_point_travel_app", "行程问题中的相遇、追及与航速水流", 3, SUBJECT, 208007),
    (208071, "jmath_g7b_point_sales_app", "销售问题中的进价、售价与利润率", 4, SUBJECT, 208007),
    (208072, "jmath_g7b_point_work_mixture_app", "工程问题与浓度配比问题的方程组建模", 5, SUBJECT, 208007),
    (208073, "jmath_g7b_point_plan_app", "方案设计与最优选择类应用", 6, SUBJECT, 208007),
    (208074, "jmath_g7b_point_chart_app", "图表信息类应用题的读表与建模", 7, SUBJECT, 208007),

    # 不等式与不等式组
    (208075, "jmath_g7b_point_inequality_concept", "不等式的定义与不等号的正确使用", 1, SUBJECT, 208008),
    (208076, "jmath_g7b_point_inequality_property", "不等式的基本性质及乘除负数变号", 2, SUBJECT, 208008),
    (208077, "jmath_g7b_point_solution_set", "不等式的解与解集的概念辨析", 3, SUBJECT, 208008),
    (208078, "jmath_g7b_point_number_line_set", "在数轴上表示不等式的解集（实心点与空心圈）", 4, SUBJECT, 208008),
    (208079, "jmath_g7b_point_linear_inequality", "一元一次不等式的定义与解法步骤", 5, SUBJECT, 208008),
    (208080, "jmath_g7b_point_clear_denominator_ineq", "去分母解一元一次不等式时的变号与漏乘", 6, SUBJECT, 208008),
    (208081, "jmath_g7b_point_integer_solution", "一元一次不等式的正整数解与整数解", 7, SUBJECT, 208008),
    (208082, "jmath_g7b_point_system_solve", "一元一次不等式组的解法与解集确定", 8, SUBJECT, 208008),
    (208083, "jmath_g7b_point_system_rule", "不等式组解集的数轴表示与“同大取大”口诀", 9, SUBJECT, 208008),
    (208084, "jmath_g7b_point_param_inequality", "含参数不等式组的取值范围讨论", 10, SUBJECT, 208008),
    (208085, "jmath_g7b_point_inequality_app", "一元一次不等式（组）在方案决策中的应用", 11, SUBJECT, 208008),

    # 数据收集整理与直方图
    (208086, "jmath_g7b_point_census_sample", "全面调查与抽样调查的适用情形与优劣", 1, SUBJECT, 208009),
    (208087, "jmath_g7b_point_population_sample", "总体、个体、样本与样本容量的辨析", 2, SUBJECT, 208009),
    (208088, "jmath_g7b_point_random_sampling", "简单随机抽样与样本代表性的判断", 3, SUBJECT, 208009),
    (208089, "jmath_g7b_point_chart_choice", "统计表、条形图与扇形图的适用与选择", 4, SUBJECT, 208009),
    (208090, "jmath_g7b_point_sector_angle", "扇形统计图中圆心角与百分比的计算", 5, SUBJECT, 208009),
    (208091, "jmath_g7b_point_frequency", "频数与频率的概念及二者关系", 6, SUBJECT, 208009),
    (208092, "jmath_g7b_point_frequency_table", "频数分布表的分组、组距与组数确定", 7, SUBJECT, 208009),
    (208093, "jmath_g7b_point_histogram", "频数分布直方图的绘制与信息读取", 8, SUBJECT, 208009),
    (208094, "jmath_g7b_point_sample_estimate", "用样本估计总体及统计结论的表述", 9, SUBJECT, 208009),
)

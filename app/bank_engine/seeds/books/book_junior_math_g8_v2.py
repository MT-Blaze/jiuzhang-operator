"""人教版（2013）初中数学八年级下册：章节树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G8 = 8
BOOK_ID = 1310

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级数学下册",
    "jmath_g8b",
    10,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第十六章 二次根式
    (131001, "第十六章 二次根式", "jmath_g8b_c16", 1, BOOK_ID, None),
    (131011, "16.1 二次根式", "jmath_g8b_s161", 1, BOOK_ID, 131001),
    (131012, "16.2 二次根式的乘除", "jmath_g8b_s162", 2, BOOK_ID, 131001),
    (131013, "16.3 二次根式的加减", "jmath_g8b_s163", 3, BOOK_ID, 131001),

    # 第十七章 勾股定理
    (131002, "第十七章 勾股定理", "jmath_g8b_c17", 2, BOOK_ID, None),
    (131021, "17.1 勾股定理", "jmath_g8b_s171", 1, BOOK_ID, 131002),
    (131022, "17.2 勾股定理的逆定理", "jmath_g8b_s172", 2, BOOK_ID, 131002),

    # 第十八章 平行四边形
    (131003, "第十八章 平行四边形", "jmath_g8b_c18", 3, BOOK_ID, None),
    (131031, "18.1 平行四边形", "jmath_g8b_s181", 1, BOOK_ID, 131003),
    (131032, "18.2 特殊的平行四边形", "jmath_g8b_s182", 2, BOOK_ID, 131003),

    # 第十九章 一次函数
    (131004, "第十九章 一次函数", "jmath_g8b_c19", 4, BOOK_ID, None),
    (131041, "19.1 函数", "jmath_g8b_s191", 1, BOOK_ID, 131004),
    (131042, "19.2 一次函数", "jmath_g8b_s192", 2, BOOK_ID, 131004),
    (131043, "19.3 课题学习 选择方案", "jmath_g8b_s193", 3, BOOK_ID, 131004),

    # 第二十章 数据的分析
    (131005, "第二十章 数据的分析", "jmath_g8b_c20", 5, BOOK_ID, None),
    (131051, "20.1 数据的集中趋势", "jmath_g8b_s201", 1, BOOK_ID, 131005),
    (131052, "20.2 数据的波动程度", "jmath_g8b_s202", 2, BOOK_ID, 131005),
    (131053, "20.3 课题学习 体质健康测试中的数据分析", "jmath_g8b_s203", 3, BOOK_ID, 131005),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 210001-210016 为册域层，210017-210098 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (210001, "jmath_g8b_domain_radical_concept", "初中八下·二次根式的概念与性质", 1, SUBJECT, G8, None),
    (210002, "jmath_g8b_domain_radical_muldiv", "初中八下·二次根式的乘除", 2, SUBJECT, G8, None),
    (210003, "jmath_g8b_domain_radical_addsub", "初中八下·二次根式的加减与混合运算", 3, SUBJECT, G8, None),
    (210004, "jmath_g8b_domain_pythagoras", "初中八下·勾股定理及其应用", 4, SUBJECT, G8, None),
    (210005, "jmath_g8b_domain_pythagoras_converse", "初中八下·勾股定理的逆定理与勾股数", 5, SUBJECT, G8, None),
    (210006, "jmath_g8b_domain_parallelogram", "初中八下·平行四边形的性质与判定", 6, SUBJECT, G8, None),
    (210007, "jmath_g8b_domain_midline", "初中八下·三角形的中位线", 7, SUBJECT, G8, None),
    (210008, "jmath_g8b_domain_rectangle", "初中八下·矩形的性质与判定", 8, SUBJECT, G8, None),
    (210009, "jmath_g8b_domain_rhombus", "初中八下·菱形的性质与判定", 9, SUBJECT, G8, None),
    (210010, "jmath_g8b_domain_square", "初中八下·正方形的性质与判定", 10, SUBJECT, G8, None),
    (210011, "jmath_g8b_domain_linear_concept", "初中八下·一次函数的概念与图象", 11, SUBJECT, G8, None),
    (210012, "jmath_g8b_domain_linear_property", "初中八下·一次函数的性质与解析式", 12, SUBJECT, G8, None),
    (210013, "jmath_g8b_domain_linear_equation", "初中八下·一次函数与方程、不等式", 13, SUBJECT, G8, None),
    (210014, "jmath_g8b_domain_linear_application", "初中八下·一次函数的实际应用与方案选择", 14, SUBJECT, G8, None),
    (210015, "jmath_g8b_domain_central_tendency", "初中八下·数据的集中趋势", 15, SUBJECT, G8, None),
    (210016, "jmath_g8b_domain_dispersion", "初中八下·数据的波动程度与统计决策", 16, SUBJECT, G8, None),

    # 二次根式的概念与性质
    (210017, "jmath_g8b_point_radical_meaning", "二次根式的定义与被开方数非负条件", 1, SUBJECT, G8, 210001),
    (210018, "jmath_g8b_point_radical_domain", "二次根式有意义的字母取值范围讨论", 2, SUBJECT, G8, 210001),
    (210019, "jmath_g8b_point_radical_nonnegative", "二次根式的双重非负性：a≥0 且√a≥0", 3, SUBJECT, G8, 210001),
    (210020, "jmath_g8b_point_radical_square", "(√a)²与√(a²)的区别及绝对值化简", 4, SUBJECT, G8, 210001),
    (210021, "jmath_g8b_point_radical_simplest", "最简二次根式的两个判断条件", 5, SUBJECT, G8, 210001),
    (210022, "jmath_g8b_point_radical_rationalize", "分母有理化与化去根号内的分母", 6, SUBJECT, G8, 210001),

    # 二次根式的乘除
    (210023, "jmath_g8b_point_radical_mul", "二次根式的乘法法则与积的算术平方根", 1, SUBJECT, G8, 210002),
    (210024, "jmath_g8b_point_radical_div", "二次根式的除法法则与商的算术平方根", 2, SUBJECT, G8, 210002),
    (210025, "jmath_g8b_point_radical_coefficient", "二次根式乘除中的系数与符号处理", 3, SUBJECT, G8, 210002),
    (210026, "jmath_g8b_point_radical_reduce", "二次根式乘除运算中的化简与约分", 4, SUBJECT, G8, 210002),
    (210027, "jmath_g8b_point_radical_compare", "二次根式大小比较：平方法与估算法", 5, SUBJECT, G8, 210002),

    # 二次根式的加减与混合运算
    (210028, "jmath_g8b_point_radical_like", "同类二次根式的识别与合并", 1, SUBJECT, G8, 210003),
    (210029, "jmath_g8b_point_radical_addsub", "二次根式加减：先化简后合并的步骤", 2, SUBJECT, G8, 210003),
    (210030, "jmath_g8b_point_radical_mixed", "二次根式混合运算的运算顺序", 3, SUBJECT, G8, 210003),
    (210031, "jmath_g8b_point_radical_formula", "乘法公式在二次根式运算中的迁移", 4, SUBJECT, G8, 210003),
    (210032, "jmath_g8b_point_radical_evaluate", "二次根式的化简求值与整体代入", 5, SUBJECT, G8, 210003),

    # 勾股定理及其应用
    (210033, "jmath_g8b_point_pythagoras_proof", "勾股定理的内容与赵爽弦图面积证明", 1, SUBJECT, G8, 210004),
    (210034, "jmath_g8b_point_pythagoras_calc", "已知直角边求斜边与已知斜边求直角边", 2, SUBJECT, G8, 210004),
    (210035, "jmath_g8b_point_pythagoras_case", "直角边与斜边身份不确定时的分类讨论", 3, SUBJECT, G8, 210004),
    (210036, "jmath_g8b_point_pythagoras_altitude", "直角三角形斜边上的高与面积法求线段", 4, SUBJECT, G8, 210004),
    (210037, "jmath_g8b_point_pythagoras_shortest", "立体图形展开后的最短路径问题", 5, SUBJECT, G8, 210004),
    (210038, "jmath_g8b_point_pythagoras_model", "勾股定理在测量、航海中的建模与计算", 6, SUBJECT, G8, 210004),

    # 勾股定理的逆定理与勾股数
    (210039, "jmath_g8b_point_converse_steps", "勾股定理逆定理的判定步骤与书写规范", 1, SUBJECT, G8, 210005),
    (210040, "jmath_g8b_point_pythagorean_triple", "常见勾股数及其整数倍规律", 2, SUBJECT, G8, 210005),
    (210041, "jmath_g8b_point_converse_shape", "用逆定理判断三角形的形状", 3, SUBJECT, G8, 210005),
    (210042, "jmath_g8b_point_grid_perpendicular", "网格中线段长度与垂直关系的判定", 4, SUBJECT, G8, 210005),
    (210043, "jmath_g8b_point_converse_bearing", "逆定理在方位角与面积问题中的综合", 5, SUBJECT, G8, 210005),

    # 平行四边形的性质与判定
    (210044, "jmath_g8b_point_parallelogram_property", "平行四边形的对边、对角与邻角性质", 1, SUBJECT, G8, 210006),
    (210045, "jmath_g8b_point_parallelogram_diagonal", "平行四边形对角线互相平分的性质", 2, SUBJECT, G8, 210006),
    (210046, "jmath_g8b_point_parallelogram_define", "两组对边分别平行的平行四边形判定", 3, SUBJECT, G8, 210006),
    (210047, "jmath_g8b_point_parallelogram_sides", "两组对边分别相等或一组对边平行且相等的判定", 4, SUBJECT, G8, 210006),
    (210048, "jmath_g8b_point_parallelogram_diag_judge", "对角线互相平分的平行四边形判定", 5, SUBJECT, G8, 210006),
    (210049, "jmath_g8b_point_parallelogram_choice", "平行四边形判定条件的选用与反例辨析", 6, SUBJECT, G8, 210006),

    # 三角形的中位线
    (210050, "jmath_g8b_point_midline_theorem", "三角形中位线的定义与中位线定理", 1, SUBJECT, G8, 210007),
    (210051, "jmath_g8b_point_midpoint_quad", "中点四边形的形状判定", 2, SUBJECT, G8, 210007),
    (210052, "jmath_g8b_point_midline_application", "中位线在测量与几何证明中的应用", 3, SUBJECT, G8, 210007),

    # 矩形的性质与判定
    (210053, "jmath_g8b_point_rectangle_property", "矩形的定义与四个角都是直角的性质", 1, SUBJECT, G8, 210008),
    (210054, "jmath_g8b_point_rectangle_diagonal", "矩形对角线相等与直角三角形斜边中线", 2, SUBJECT, G8, 210008),
    (210055, "jmath_g8b_point_rectangle_judge_angle", "有一个角是直角的平行四边形是矩形", 3, SUBJECT, G8, 210008),
    (210056, "jmath_g8b_point_rectangle_judge_diag", "对角线相等的平行四边形是矩形", 4, SUBJECT, G8, 210008),
    (210057, "jmath_g8b_point_rectangle_fold", "矩形中的折叠与最短路径问题", 5, SUBJECT, G8, 210008),

    # 菱形的性质与判定
    (210058, "jmath_g8b_point_rhombus_property", "菱形的定义与四条边相等的性质", 1, SUBJECT, G8, 210009),
    (210059, "jmath_g8b_point_rhombus_diagonal", "菱形对角线互相垂直且平分每组对角", 2, SUBJECT, G8, 210009),
    (210060, "jmath_g8b_point_rhombus_area", "菱形面积等于两条对角线乘积的一半", 3, SUBJECT, G8, 210009),
    (210061, "jmath_g8b_point_rhombus_judge", "菱形的三种判定途径与书写", 4, SUBJECT, G8, 210009),
    (210062, "jmath_g8b_point_rhombus_rectangle", "菱形与矩形判定条件的区分与综合", 5, SUBJECT, G8, 210009),

    # 正方形的性质与判定
    (210063, "jmath_g8b_point_square_property", "正方形的性质：兼具矩形与菱形全部性质", 1, SUBJECT, G8, 210010),
    (210064, "jmath_g8b_point_square_judge", "菱形加直角或矩形加邻边相等的判定", 2, SUBJECT, G8, 210010),
    (210065, "jmath_g8b_point_square_rotate", "正方形中的旋转、全等与45°角模型", 3, SUBJECT, G8, 210010),
    (210066, "jmath_g8b_point_square_area", "正方形与中点四边形、面积分割的综合", 4, SUBJECT, G8, 210010),

    # 一次函数的概念与图象
    (210067, "jmath_g8b_point_function_concept", "变量与常量、函数的概念及表示方法", 1, SUBJECT, G8, 210011),
    (210068, "jmath_g8b_point_function_domain", "自变量取值范围与分式、根式限制", 2, SUBJECT, G8, 210011),
    (210069, "jmath_g8b_point_function_graph", "函数图象的识读与从图象获取信息", 3, SUBJECT, G8, 210011),
    (210070, "jmath_g8b_point_direct_proportion", "正比例函数y=kx的定义与图象过原点", 4, SUBJECT, G8, 210011),
    (210071, "jmath_g8b_point_direct_property", "正比例函数的增减性与k的符号", 5, SUBJECT, G8, 210011),
    (210072, "jmath_g8b_point_direct_coefficient", "用待定系数法求正比例函数解析式", 6, SUBJECT, G8, 210011),
    (210073, "jmath_g8b_point_linear_define", "一次函数y=kx+b的定义与常数项意义", 7, SUBJECT, G8, 210011),

    # 一次函数的性质与解析式
    (210074, "jmath_g8b_point_linear_sign", "一次函数图象与k、b符号的对应关系", 1, SUBJECT, G8, 210012),
    (210075, "jmath_g8b_point_linear_monotonic", "一次函数的增减性与所过象限", 2, SUBJECT, G8, 210012),
    (210076, "jmath_g8b_point_linear_shift", "一次函数图象的平移规律", 3, SUBJECT, G8, 210012),
    (210077, "jmath_g8b_point_linear_coefficient", "待定系数法求一次函数解析式", 4, SUBJECT, G8, 210012),
    (210078, "jmath_g8b_point_linear_intercept", "一次函数与坐标轴交点及围成面积", 5, SUBJECT, G8, 210012),

    # 一次函数与方程、不等式
    (210079, "jmath_g8b_point_linear_equation", "一次函数与一元一次方程的解", 1, SUBJECT, G8, 210013),
    (210080, "jmath_g8b_point_linear_inequality", "用函数图象法解一元一次不等式", 2, SUBJECT, G8, 210013),
    (210081, "jmath_g8b_point_linear_system", "两条直线交点与二元一次方程组", 3, SUBJECT, G8, 210013),
    (210082, "jmath_g8b_point_linear_inequality_set", "一次函数图象与不等式组的解集", 4, SUBJECT, G8, 210013),

    # 一次函数的实际应用与方案选择
    (210083, "jmath_g8b_point_linear_model", "从实际问题抽象一次函数模型", 1, SUBJECT, G8, 210014),
    (210084, "jmath_g8b_point_piecewise", "分段计费与分段函数图象", 2, SUBJECT, G8, 210014),
    (210085, "jmath_g8b_point_scheme_compare", "方案选择中的图象交点与最优决策", 3, SUBJECT, G8, 210014),
    (210086, "jmath_g8b_point_linear_real", "一次函数在工程、行程、销售中的应用", 4, SUBJECT, G8, 210014),
    (210087, "jmath_g8b_point_scheme_project", "课题学习：选择方案的建模与检验", 5, SUBJECT, G8, 210014),

    # 数据的集中趋势
    (210088, "jmath_g8b_point_mean", "算术平均数的计算与基本性质", 1, SUBJECT, G8, 210015),
    (210089, "jmath_g8b_point_weighted_mean", "加权平均数的计算与权的意义", 2, SUBJECT, G8, 210015),
    (210090, "jmath_g8b_point_median", "中位数的定义与奇偶数据求法", 3, SUBJECT, G8, 210015),
    (210091, "jmath_g8b_point_mode", "众数的意义与不唯一情形", 4, SUBJECT, G8, 210015),
    (210092, "jmath_g8b_point_three_means", "平均数、中位数、众数的适用场景", 5, SUBJECT, G8, 210015),
    (210093, "jmath_g8b_point_mean_reverse", "由统计表反求缺失数据与统计量", 6, SUBJECT, G8, 210015),
    (210094, "jmath_g8b_point_sample_mean", "用样本平均数估计总体平均数", 7, SUBJECT, G8, 210015),

    # 数据的波动程度与统计决策
    (210095, "jmath_g8b_point_variance", "方差的定义与计算公式", 1, SUBJECT, G8, 210016),
    (210096, "jmath_g8b_point_variance_compare", "方差比较数据波动与稳定性", 2, SUBJECT, G8, 210016),
    (210097, "jmath_g8b_point_std_deviation", "标准差与数据整体变化对方差的影响", 3, SUBJECT, G8, 210016),
    (210098, "jmath_g8b_point_data_decision", "体质健康测试数据分析与统计决策", 4, SUBJECT, G8, 210016),
)

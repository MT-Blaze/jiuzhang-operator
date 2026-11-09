"""人教版（2013）初中数学八年级上册：章节树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G8 = 8
BOOK_ID = 1309

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级数学上册",
    "jmath_g8a",
    9,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第十一章 三角形
    (130901, "第十一章 三角形", "jmath_g8a_c11", 1, BOOK_ID, None),
    (130911, "11.1 与三角形有关的线段", "jmath_g8a_s111", 1, BOOK_ID, 130901),
    (130912, "11.2 与三角形有关的角", "jmath_g8a_s112", 2, BOOK_ID, 130901),
    (130913, "11.3 多边形及其内角和", "jmath_g8a_s113", 3, BOOK_ID, 130901),

    # 第十二章 全等三角形
    (130902, "第十二章 全等三角形", "jmath_g8a_c12", 2, BOOK_ID, None),
    (130921, "12.1 全等三角形", "jmath_g8a_s121", 1, BOOK_ID, 130902),
    (130922, "12.2 三角形全等的判定", "jmath_g8a_s122", 2, BOOK_ID, 130902),
    (130923, "12.3 角的平分线的性质", "jmath_g8a_s123", 3, BOOK_ID, 130902),

    # 第十三章 轴对称
    (130903, "第十三章 轴对称", "jmath_g8a_c13", 3, BOOK_ID, None),
    (130931, "13.1 轴对称", "jmath_g8a_s131", 1, BOOK_ID, 130903),
    (130932, "13.2 画轴对称图形", "jmath_g8a_s132", 2, BOOK_ID, 130903),
    (130933, "13.3 等腰三角形", "jmath_g8a_s133", 3, BOOK_ID, 130903),
    (130934, "13.4 课题学习 最短路径问题", "jmath_g8a_s134", 4, BOOK_ID, 130903),

    # 第十四章 整式的乘法与因式分解
    (130904, "第十四章 整式的乘法与因式分解", "jmath_g8a_c14", 4, BOOK_ID, None),
    (130941, "14.1 整式的乘法", "jmath_g8a_s141", 1, BOOK_ID, 130904),
    (130942, "14.2 乘法公式", "jmath_g8a_s142", 2, BOOK_ID, 130904),
    (130943, "14.3 因式分解", "jmath_g8a_s143", 3, BOOK_ID, 130904),

    # 第十五章 分式
    (130905, "第十五章 分式", "jmath_g8a_c15", 5, BOOK_ID, None),
    (130951, "15.1 分式", "jmath_g8a_s151", 1, BOOK_ID, 130905),
    (130952, "15.2 分式的运算", "jmath_g8a_s152", 2, BOOK_ID, 130905),
    (130953, "15.3 分式方程", "jmath_g8a_s153", 3, BOOK_ID, 130905),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 209001-209010 为册域层，209011-209088 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (209001, "jmath_g8a_domain_triangle", "初中八上·三角形的边角关系", 1, SUBJECT, G8, None),
    (209002, "jmath_g8a_domain_polygon", "初中八上·多边形内角和与外角和", 2, SUBJECT, G8, None),
    (209003, "jmath_g8a_domain_congruent", "初中八上·全等三角形的性质与判定", 3, SUBJECT, G8, None),
    (209004, "jmath_g8a_domain_bisector", "初中八上·角平分线与尺规作图", 4, SUBJECT, G8, None),
    (209005, "jmath_g8a_domain_axis_symmetry", "初中八上·轴对称与坐标对称", 5, SUBJECT, G8, None),
    (209006, "jmath_g8a_domain_isosceles", "初中八上·等腰三角形与等边三角形", 6, SUBJECT, G8, None),
    (209007, "jmath_g8a_domain_shortest_path", "初中八上·最短路径问题", 7, SUBJECT, G8, None),
    (209008, "jmath_g8a_domain_monomial", "初中八上·整式乘法与乘法公式", 8, SUBJECT, G8, None),
    (209009, "jmath_g8a_domain_factorization", "初中八上·因式分解", 9, SUBJECT, G8, None),
    (209010, "jmath_g8a_domain_fraction", "初中八上·分式与分式方程", 10, SUBJECT, G8, None),

    # 三角形的边角关系
    (209011, "jmath_g8a_point_triangle_concept", "三角形的定义、基本元素与按边按角分类", 1, SUBJECT, G8, 209001),
    (209012, "jmath_g8a_point_triangle_inequality", "三角形三边关系定理与第三边取值范围", 2, SUBJECT, G8, 209001),
    (209013, "jmath_g8a_point_triangle_three_lines", "三角形的高、中线、角平分线的画法辨析", 3, SUBJECT, G8, 209001),
    (209014, "jmath_g8a_point_obtuse_altitude", "钝角三角形高的位置与高相关的面积计算", 4, SUBJECT, G8, 209001),
    (209015, "jmath_g8a_point_median_centroid", "三角形中线与重心性质的初步应用", 5, SUBJECT, G8, 209001),
    (209016, "jmath_g8a_point_stability", "三角形的稳定性及其在生活中的应用", 6, SUBJECT, G8, 209001),
    (209017, "jmath_g8a_point_angle_sum", "三角形内角和定理的证明与角度计算", 7, SUBJECT, G8, 209001),
    (209018, "jmath_g8a_point_right_triangle_angles", "直角三角形两锐角互余及同角余角相等", 8, SUBJECT, G8, 209001),
    (209019, "jmath_g8a_point_exterior_angle", "三角形外角的定义与外角性质的应用", 9, SUBJECT, G8, 209001),

    # 多边形内角和与外角和
    (209020, "jmath_g8a_point_diagonal", "多边形的对角线定义与对角线条数公式", 1, SUBJECT, G8, 209002),
    (209021, "jmath_g8a_point_polygon_angle_proof", "n边形内角和公式(n-2)×180°的推导", 2, SUBJECT, G8, 209002),
    (209022, "jmath_g8a_point_polygon_angle_calc", "多边形内角和公式的正向与逆向计算", 3, SUBJECT, G8, 209002),
    (209023, "jmath_g8a_point_polygon_exterior", "多边形外角和恒为360°及正多边形外角", 4, SUBJECT, G8, 209002),
    (209024, "jmath_g8a_point_regular_polygon", "正多边形的内角、外角与边数互求", 5, SUBJECT, G8, 209002),
    (209025, "jmath_g8a_point_tessellation", "平面镶嵌中多边形内角需整除360°的条件", 6, SUBJECT, G8, 209002),

    # 全等三角形的性质与判定
    (209026, "jmath_g8a_point_congruent_concept", "全等形的概念与全等三角形的定义", 1, SUBJECT, G8, 209003),
    (209027, "jmath_g8a_point_corresponding", "全等三角形对应边、对应角的寻找方法", 2, SUBJECT, G8, 209003),
    (209028, "jmath_g8a_point_congruent_property", "全等三角形性质与线段、角相等的转化", 3, SUBJECT, G8, 209003),
    (209029, "jmath_g8a_point_sss", "边边边（SSS）判定条件及其应用", 4, SUBJECT, G8, 209003),
    (209030, "jmath_g8a_point_sas", "边角边（SAS）判定与夹角位置的辨析", 5, SUBJECT, G8, 209003),
    (209031, "jmath_g8a_point_asa_aas", "角边角（ASA）与角角边（AAS）判定", 6, SUBJECT, G8, 209003),
    (209032, "jmath_g8a_point_hl", "斜边、直角边（HL）判定及适用前提", 7, SUBJECT, G8, 209003),
    (209033, "jmath_g8a_point_ssa_invalid", "两边及其中一边对角（SSA）不能判定全等", 8, SUBJECT, G8, 209003),
    (209034, "jmath_g8a_point_judge_selection", "全等判定条件的选用策略与开放探究", 9, SUBJECT, G8, 209003),
    (209035, "jmath_g8a_point_congruent_proof", "全等三角形证明的书写规范与辅助线构造", 10, SUBJECT, G8, 209003),

    # 角平分线与尺规作图
    (209036, "jmath_g8a_point_bisector_property", "角平分线性质定理与点到两边的距离", 1, SUBJECT, G8, 209004),
    (209037, "jmath_g8a_point_bisector_converse", "角平分线性质定理的逆定理及应用", 2, SUBJECT, G8, 209004),
    (209038, "jmath_g8a_point_bisector_construction", "尺规作角的平分线的步骤与作图依据", 3, SUBJECT, G8, 209004),
    (209039, "jmath_g8a_point_bisector_area", "角平分线与全等、面积问题的综合", 4, SUBJECT, G8, 209004),
    (209040, "jmath_g8a_point_incenter", "三角形三条角平分线交于一点的初步认识", 5, SUBJECT, G8, 209004),
    (209041, "jmath_g8a_point_construct_triangle", "尺规作三角形与全等判定依据的对应", 6, SUBJECT, G8, 209004),

    # 轴对称与坐标对称
    (209042, "jmath_g8a_point_symmetry_concept", "轴对称图形与两个图形成轴对称的辨析", 1, SUBJECT, G8, 209005),
    (209043, "jmath_g8a_point_symmetry_property", "轴对称的性质：对应点连线被对称轴垂直平分", 2, SUBJECT, G8, 209005),
    (209044, "jmath_g8a_point_perp_bisector", "线段垂直平分线的性质定理", 3, SUBJECT, G8, 209005),
    (209045, "jmath_g8a_point_perp_bisector_converse", "线段垂直平分线性质定理的逆定理", 4, SUBJECT, G8, 209005),
    (209046, "jmath_g8a_point_draw_symmetry", "画轴对称图形与对称轴的确定", 5, SUBJECT, G8, 209005),
    (209047, "jmath_g8a_point_axis_coordinate", "坐标系中关于x轴、y轴对称的点的坐标规律", 6, SUBJECT, G8, 209005),
    (209048, "jmath_g8a_point_origin_symmetry", "坐标系中关于原点对称及对称图形作图", 7, SUBJECT, G8, 209005),

    # 等腰三角形与等边三角形
    (209049, "jmath_g8a_point_isosceles_property", "等腰三角形性质：等边对等角", 1, SUBJECT, G8, 209006),
    (209050, "jmath_g8a_point_three_in_one", "等腰三角形“三线合一”的性质", 2, SUBJECT, G8, 209006),
    (209051, "jmath_g8a_point_isosceles_judge", "等腰三角形的判定：等角对等边", 3, SUBJECT, G8, 209006),
    (209052, "jmath_g8a_point_isosceles_discussion", "等腰三角形边角分类讨论与周长计算", 4, SUBJECT, G8, 209006),
    (209053, "jmath_g8a_point_equilateral", "等边三角形的性质与判定", 5, SUBJECT, G8, 209006),
    (209054, "jmath_g8a_point_thirty_degree", "含30°角的直角三角形的边角关系", 6, SUBJECT, G8, 209006),
    (209055, "jmath_g8a_point_isosceles_auxiliary", "等腰三角形常用辅助线：作底边高与截长补短", 7, SUBJECT, G8, 209006),

    # 最短路径问题
    (209056, "jmath_g8a_point_general_drinking", "轴对称转化“将军饮马”型最短路径", 1, SUBJECT, G8, 209007),
    (209057, "jmath_g8a_point_sum_minimum", "两条线段和最小问题的作图与证明", 2, SUBJECT, G8, 209007),
    (209058, "jmath_g8a_point_bridge_site", "造桥选址与平移转化类最短路径", 3, SUBJECT, G8, 209007),
    (209059, "jmath_g8a_point_path_model", "最短路径问题的建模步骤与答案检验", 4, SUBJECT, G8, 209007),

    # 整式乘法与乘法公式
    (209060, "jmath_g8a_point_power_product", "同底数幂的乘法法则及其逆用", 1, SUBJECT, G8, 209008),
    (209061, "jmath_g8a_point_power_power", "幂的乘方法则与符号处理", 2, SUBJECT, G8, 209008),
    (209062, "jmath_g8a_point_power_product_rule", "积的乘方法则及幂的混合运算", 3, SUBJECT, G8, 209008),
    (209063, "jmath_g8a_point_monomial_product", "单项式乘单项式与单项式乘多项式", 4, SUBJECT, G8, 209008),
    (209064, "jmath_g8a_point_polynomial_product", "多项式乘多项式与积的项数规律", 5, SUBJECT, G8, 209008),
    (209065, "jmath_g8a_point_power_quotient", "同底数幂的除法与零指数幂", 6, SUBJECT, G8, 209008),
    (209066, "jmath_g8a_point_polynomial_division", "单项式除以单项式与多项式除以单项式", 7, SUBJECT, G8, 209008),
    (209067, "jmath_g8a_point_square_difference", "平方差公式的结构识别与应用", 8, SUBJECT, G8, 209008),
    (209068, "jmath_g8a_point_perfect_square", "完全平方公式及和差与积的互化变形", 9, SUBJECT, G8, 209008),
    (209069, "jmath_g8a_point_add_parentheses", "添括号法则在乘法公式中的应用", 10, SUBJECT, G8, 209008),
    (209070, "jmath_g8a_point_formula_geometry", "乘法公式的几何背景与综合变形求值", 11, SUBJECT, G8, 209008),

    # 因式分解
    (209071, "jmath_g8a_point_factor_concept", "因式分解的意义及与整式乘法的互逆关系", 1, SUBJECT, G8, 209009),
    (209072, "jmath_g8a_point_common_factor", "提公因式法：公因式的确定与符号处理", 2, SUBJECT, G8, 209009),
    (209073, "jmath_g8a_point_difference_factor", "平方差公式法因式分解", 3, SUBJECT, G8, 209009),
    (209074, "jmath_g8a_point_perfect_factor", "完全平方公式法因式分解", 4, SUBJECT, G8, 209009),
    (209075, "jmath_g8a_point_factor_steps", "因式分解步骤：“一提二套三检查”", 5, SUBJECT, G8, 209009),
    (209076, "jmath_g8a_point_factor_calc", "因式分解在简便计算与代数式求值中的应用", 6, SUBJECT, G8, 209009),
    (209077, "jmath_g8a_point_factor_whole", "因式分解中的整体思想与换元处理", 7, SUBJECT, G8, 209009),

    # 分式与分式方程
    (209078, "jmath_g8a_point_fraction_concept", "分式的定义与分式有意义的条件", 1, SUBJECT, G8, 209010),
    (209079, "jmath_g8a_point_fraction_zero", "分式值为零的条件与字母取值讨论", 2, SUBJECT, G8, 209010),
    (209080, "jmath_g8a_point_fraction_property", "分式的基本性质与符号法则", 3, SUBJECT, G8, 209010),
    (209081, "jmath_g8a_point_reduce", "约分与最简分式的判断", 4, SUBJECT, G8, 209010),
    (209082, "jmath_g8a_point_common_denominator", "通分与最简公分母的确定", 5, SUBJECT, G8, 209010),
    (209083, "jmath_g8a_point_fraction_multiply", "分式的乘除与乘方运算", 6, SUBJECT, G8, 209010),
    (209084, "jmath_g8a_point_fraction_add", "分式的加减与混合运算顺序", 7, SUBJECT, G8, 209010),
    (209085, "jmath_g8a_point_negative_exponent", "负整数指数幂与科学记数法", 8, SUBJECT, G8, 209010),
    (209086, "jmath_g8a_point_fraction_equation", "分式方程的解法与去分母", 9, SUBJECT, G8, 209010),
    (209087, "jmath_g8a_point_extraneous_root", "分式方程的增根与验根", 10, SUBJECT, G8, 209010),
    (209088, "jmath_g8a_point_fraction_app", "列分式方程解工程、行程与销售应用题", 11, SUBJECT, G8, 209010),
)

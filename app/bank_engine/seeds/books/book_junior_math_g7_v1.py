"""人教版（2012）初中数学七年级上册：章节树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G7 = 7
BOOK_ID = 1307

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版七年级数学上册",
    "jmath_g7a",
    7,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一章 有理数
    (130701, "第一章 有理数", "jmath_g7a_c01", 1, BOOK_ID, None),
    (130711, "1.1 正数和负数", "jmath_g7a_s11", 1, BOOK_ID, 130701),
    (130712, "1.2 有理数", "jmath_g7a_s12", 2, BOOK_ID, 130701),
    (130713, "1.2.1 有理数", "jmath_g7a_s121", 1, BOOK_ID, 130712),
    (130714, "1.2.2 数轴", "jmath_g7a_s122", 2, BOOK_ID, 130712),
    (130715, "1.2.3 相反数", "jmath_g7a_s123", 3, BOOK_ID, 130712),
    (130716, "1.2.4 绝对值", "jmath_g7a_s124", 4, BOOK_ID, 130712),
    (130717, "1.3 有理数的加减法", "jmath_g7a_s13", 3, BOOK_ID, 130701),
    (130718, "1.4 有理数的乘除法", "jmath_g7a_s14", 4, BOOK_ID, 130701),
    (130719, "1.5 有理数的乘方", "jmath_g7a_s15", 5, BOOK_ID, 130701),

    # 第二章 整式的加减
    (130702, "第二章 整式的加减", "jmath_g7a_c02", 2, BOOK_ID, None),
    (130721, "2.1 整式", "jmath_g7a_s21", 1, BOOK_ID, 130702),
    (130722, "2.2 整式的加减", "jmath_g7a_s22", 2, BOOK_ID, 130702),

    # 第三章 一元一次方程
    (130703, "第三章 一元一次方程", "jmath_g7a_c03", 3, BOOK_ID, None),
    (130731, "3.1 从算式到方程", "jmath_g7a_s31", 1, BOOK_ID, 130703),
    (130732, "3.2 解一元一次方程（一）——合并同类项与移项", "jmath_g7a_s32", 2, BOOK_ID, 130703),
    (130733, "3.3 解一元一次方程（二）——去括号与去分母", "jmath_g7a_s33", 3, BOOK_ID, 130703),
    (130734, "3.4 实际问题与一元一次方程", "jmath_g7a_s34", 4, BOOK_ID, 130703),

    # 第四章 几何图形初步
    (130704, "第四章 几何图形初步", "jmath_g7a_c04", 4, BOOK_ID, None),
    (130741, "4.1 几何图形", "jmath_g7a_s41", 1, BOOK_ID, 130704),
    (130742, "4.2 直线、射线、线段", "jmath_g7a_s42", 2, BOOK_ID, 130704),
    (130743, "4.3 角", "jmath_g7a_s43", 3, BOOK_ID, 130704),
    (130744, "4.4 课题学习 设计制作长方体形状的包装纸盒", "jmath_g7a_s44", 4, BOOK_ID, 130704),
)

# id / code / name / sort_order / subject_id / parent_id
# 207001-207008 为册域层，207011-207099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (207001, "jmath_g7a_domain_rational", "初中七上·有理数概念与数轴", 1, SUBJECT, None),
    (207002, "jmath_g7a_domain_rational_ops", "初中七上·有理数运算", 2, SUBJECT, None),
    (207003, "jmath_g7a_domain_algebra", "初中七上·整式与合并同类项", 3, SUBJECT, None),
    (207004, "jmath_g7a_domain_equation", "初中七上·一元一次方程解法", 4, SUBJECT, None),
    (207005, "jmath_g7a_domain_equation_app", "初中七上·一元一次方程应用", 5, SUBJECT, None),
    (207006, "jmath_g7a_domain_geometry", "初中七上·几何图形初步", 6, SUBJECT, None),
    (207007, "jmath_g7a_domain_line", "初中七上·直线、射线、线段", 7, SUBJECT, None),
    (207008, "jmath_g7a_domain_angle", "初中七上·角与角平分线", 8, SUBJECT, None),

    # 有理数概念与数轴
    (207011, "jmath_g7a_point_pos_negative_meaning", "正数与负数的意义及用正负数表示相反意义的量", 1, SUBJECT, 207001),
    (207012, "jmath_g7a_point_rational_classification", "有理数的分类（按定义与按符号）及0的双重身份", 2, SUBJECT, 207001),
    (207013, "jmath_g7a_point_number_axis", "数轴三要素与有理数在数轴上的表示", 3, SUBJECT, 207001),
    (207014, "jmath_g7a_point_opposite_number", "相反数的定义与多重符号化简", 4, SUBJECT, 207001),
    (207015, "jmath_g7a_point_absolute_value", "绝对值的几何意义与代数定义", 5, SUBJECT, 207001),
    (207016, "jmath_g7a_point_abs_nonnegative", "绝对值的非负性及|a|与±a的关系", 6, SUBJECT, 207001),
    (207017, "jmath_g7a_point_compare_rational", "有理数大小比较：数轴法、绝对值法与作差法", 7, SUBJECT, 207001),
    (207018, "jmath_g7a_point_abs_parameter", "由绝对值求字母取值范围的分类讨论", 8, SUBJECT, 207001),
    (207019, "jmath_g7a_point_axis_distance", "数轴上两点间距离与中点坐标", 9, SUBJECT, 207001),
    (207020, "jmath_g7a_point_rational_review", "有理数概念综合：0、相反数、绝对值易错辨析", 10, SUBJECT, 207001),

    # 有理数运算
    (207021, "jmath_g7a_point_add_sign", "有理数加法法则与异号两数相加的符号判定", 1, SUBJECT, 207002),
    (207022, "jmath_g7a_point_add_laws", "加法运算律在有理数加法中的简便运用", 2, SUBJECT, 207002),
    (207023, "jmath_g7a_point_subtract_rule", "有理数减法法则：减去一个数等于加上它的相反数", 3, SUBJECT, 207002),
    (207024, "jmath_g7a_point_mixed_add_sub", "加减混合运算的统一成加法与省略括号写法", 4, SUBJECT, 207002),
    (207025, "jmath_g7a_point_multiply_sign", "有理数乘法法则与多个因数积的符号判定", 5, SUBJECT, 207002),
    (207026, "jmath_g7a_point_distributive", "乘法分配律在有理数乘法中的正用与逆用", 6, SUBJECT, 207002),
    (207027, "jmath_g7a_point_divide_reciprocal", "有理数除法法则与倒数关系", 7, SUBJECT, 207002),
    (207028, "jmath_g7a_point_mixed_mul_div", "乘除混合运算的顺序与符号处理", 8, SUBJECT, 207002),
    (207029, "jmath_g7a_point_power_sign", "有理数乘方的意义与幂的符号规律", 9, SUBJECT, 207002),
    (207030, "jmath_g7a_point_scientific_notation", "科学记数法表示绝对值较大的数", 10, SUBJECT, 207002),
    (207031, "jmath_g7a_point_significant_digits", "近似数与有效数字的确定", 11, SUBJECT, 207002),
    (207032, "jmath_g7a_point_mixed_order", "有理数混合运算的运算顺序与简算技巧", 12, SUBJECT, 207002),

    # 整式与合并同类项
    (207033, "jmath_g7a_point_letter_expression", "用含字母的式子表示数量关系", 1, SUBJECT, 207003),
    (207034, "jmath_g7a_point_monomial_degree", "单项式的系数与次数", 2, SUBJECT, 207003),
    (207035, "jmath_g7a_point_polynomial_degree", "多项式的项、常数项与次数", 3, SUBJECT, 207003),
    (207036, "jmath_g7a_point_like_terms", "同类项的判定：字母相同且相同字母指数相同", 4, SUBJECT, 207003),
    (207037, "jmath_g7a_point_combine_like_terms", "合并同类项法则与系数相加", 5, SUBJECT, 207003),
    (207038, "jmath_g7a_point_remove_parentheses", "去括号法则与括号前负号的变号", 6, SUBJECT, 207003),
    (207039, "jmath_g7a_point_add_parentheses", "添括号法则及其在整式变形中的应用", 7, SUBJECT, 207003),
    (207040, "jmath_g7a_point_poly_add_sub", "整式加减的实质：去括号与合并同类项", 8, SUBJECT, 207003),
    (207041, "jmath_g7a_point_simplify_evaluate", "整式化简求值：先化简再代入", 9, SUBJECT, 207003),

    # 一元一次方程解法
    (207042, "jmath_g7a_point_equation_concept", "方程、方程的解与解方程的概念辨析", 1, SUBJECT, 207004),
    (207043, "jmath_g7a_point_linear_definition", "一元一次方程的定义与判定", 2, SUBJECT, 207004),
    (207044, "jmath_g7a_point_equality_property", "等式的性质及其在解方程中的应用", 3, SUBJECT, 207004),
    (207045, "jmath_g7a_point_transposition", "移项法则与移项要变号", 4, SUBJECT, 207004),
    (207046, "jmath_g7a_point_solve_combine", "合并同类项解一元一次方程", 5, SUBJECT, 207004),
    (207047, "jmath_g7a_point_solve_brackets", "去括号解一元一次方程", 6, SUBJECT, 207004),
    (207048, "jmath_g7a_point_clear_denominator", "去分母解一元一次方程时最小公倍数的确定", 7, SUBJECT, 207004),
    (207049, "jmath_g7a_point_solve_steps", "解一元一次方程的一般步骤与检验", 8, SUBJECT, 207004),
    (207050, "jmath_g7a_point_decimal_denominator", "分母含小数的一元一次方程化整处理", 9, SUBJECT, 207004),
    (207051, "jmath_g7a_point_parameter_equation", "一元一次方程解的讨论与含参方程", 10, SUBJECT, 207004),

    # 一元一次方程应用
    (207052, "jmath_g7a_point_set_unknown", "列方程解应用题：设未知数与找等量关系", 1, SUBJECT, 207005),
    (207053, "jmath_g7a_point_sum_multiple", "和差倍分问题中的等量关系", 2, SUBJECT, 207005),
    (207054, "jmath_g7a_point_travel", "行程问题：相遇、追及与环形跑道", 3, SUBJECT, 207005),
    (207055, "jmath_g7a_point_work", "工程问题：工作总量设为1与效率叠加", 4, SUBJECT, 207005),
    (207056, "jmath_g7a_point_sales_profit", "销售问题：进价、标价、折扣与利润", 5, SUBJECT, 207005),
    (207057, "jmath_g7a_point_interest", "储蓄与利率问题中的本金利息计算", 6, SUBJECT, 207005),
    (207058, "jmath_g7a_point_matching", "配套问题与比例分配", 7, SUBJECT, 207005),
    (207059, "jmath_g7a_point_number_age", "数字问题与年龄问题中的等量关系", 8, SUBJECT, 207005),
    (207060, "jmath_g7a_point_scheme", "方案选择与分段计费问题", 9, SUBJECT, 207005),

    # 几何图形初步
    (207061, "jmath_g7a_point_solid_plane", "立体图形与平面图形的识别", 1, SUBJECT, 207006),
    (207062, "jmath_g7a_point_solid_net", "常见立体图形的展开图", 2, SUBJECT, 207006),
    (207063, "jmath_g7a_point_point_line_surface", "点、线、面、体的关系与点动成线", 3, SUBJECT, 207006),
    (207064, "jmath_g7a_point_three_views", "从不同方向看几何体得到的三视图", 4, SUBJECT, 207006),
    (207065, "jmath_g7a_point_restore_views", "由三视图还原几何体的方法", 5, SUBJECT, 207006),
    (207066, "jmath_g7a_point_cube_net", "正方体表面展开图的判断与相对面", 6, SUBJECT, 207006),
    (207067, "jmath_g7a_point_plane_cut", "平面图形的分割与拼接", 7, SUBJECT, 207006),
    (207068, "jmath_g7a_point_packaging_box", "课题学习：长方体包装纸盒的设计与制作", 8, SUBJECT, 207006),

    # 直线、射线、线段
    (207069, "jmath_g7a_point_line_ray_segment", "直线、射线、线段的表示方法与区别", 1, SUBJECT, 207007),
    (207070, "jmath_g7a_point_line_basic_facts", "两点确定一条直线与两点之间线段最短", 2, SUBJECT, 207007),
    (207071, "jmath_g7a_point_segment_midpoint", "线段的和差与中点定义", 3, SUBJECT, 207007),
    (207072, "jmath_g7a_point_midpoint_length", "线段中点相关的长度计算", 4, SUBJECT, 207007),
    (207073, "jmath_g7a_point_segment_distance", "线段比较与两点间距离", 5, SUBJECT, 207007),
    (207074, "jmath_g7a_point_compass_construction", "尺规作图：作一条线段等于已知线段", 6, SUBJECT, 207007),
    (207075, "jmath_g7a_point_moving_point", "线段上的动点与分类讨论", 7, SUBJECT, 207007),
    (207076, "jmath_g7a_point_line_intersection", "平面内直线相交与交点个数规律", 8, SUBJECT, 207007),

    # 角与角平分线
    (207077, "jmath_g7a_point_angle_definition", "角的两种定义与表示方法", 1, SUBJECT, 207008),
    (207078, "jmath_g7a_point_degree_minute_second", "度分秒的换算与角度计算", 2, SUBJECT, 207008),
    (207079, "jmath_g7a_point_angle_compare", "角的比较与角的和差", 3, SUBJECT, 207008),
    (207080, "jmath_g7a_point_angle_bisector", "角平分线的定义与角度计算", 4, SUBJECT, 207008),
    (207081, "jmath_g7a_point_complementary", "余角与补角的概念及性质", 5, SUBJECT, 207008),
    (207082, "jmath_g7a_point_equal_angle", "同角或等角的余角相等、补角相等的推理", 6, SUBJECT, 207008),
    (207083, "jmath_g7a_point_direction_angle", "方位角与方向角的表示", 7, SUBJECT, 207008),
    (207084, "jmath_g7a_point_clock_angle", "钟面角与时针分针夹角的计算", 8, SUBJECT, 207008),
    (207085, "jmath_g7a_point_dynamic_angle", "角的动态定义与旋转角", 9, SUBJECT, 207008),
)

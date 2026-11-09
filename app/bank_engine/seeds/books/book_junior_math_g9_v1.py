"""人教版（2013）初中数学九年级上册：章节树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G9 = 9
BOOK_ID = 1311

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版九年级数学上册",
    "jmath_g9a",
    11,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第二十一章 一元二次方程
    (131101, "第二十一章 一元二次方程", "jmath_g9a_c21", 1, BOOK_ID, None),
    (131111, "21.1 一元二次方程", "jmath_g9a_s211", 1, BOOK_ID, 131101),
    (131112, "21.2 解一元二次方程", "jmath_g9a_s212", 2, BOOK_ID, 131101),
    (131113, "21.3 实际问题与一元二次方程", "jmath_g9a_s213", 3, BOOK_ID, 131101),

    # 第二十二章 二次函数
    (131102, "第二十二章 二次函数", "jmath_g9a_c22", 2, BOOK_ID, None),
    (131121, "22.1 二次函数的图象和性质", "jmath_g9a_s221", 1, BOOK_ID, 131102),
    (131122, "22.2 二次函数与一元二次方程", "jmath_g9a_s222", 2, BOOK_ID, 131102),
    (131123, "22.3 实际问题与二次函数", "jmath_g9a_s223", 3, BOOK_ID, 131102),

    # 第二十三章 旋转
    (131103, "第二十三章 旋转", "jmath_g9a_c23", 3, BOOK_ID, None),
    (131131, "23.1 图形的旋转", "jmath_g9a_s231", 1, BOOK_ID, 131103),
    (131132, "23.2 中心对称", "jmath_g9a_s232", 2, BOOK_ID, 131103),
    (131133, "23.3 课题学习 图案设计", "jmath_g9a_s233", 3, BOOK_ID, 131103),

    # 第二十四章 圆
    (131104, "第二十四章 圆", "jmath_g9a_c24", 4, BOOK_ID, None),
    (131141, "24.1 圆的有关性质", "jmath_g9a_s241", 1, BOOK_ID, 131104),
    (131142, "24.2 点和圆、直线和圆的位置关系", "jmath_g9a_s242", 2, BOOK_ID, 131104),
    (131143, "24.3 正多边形和圆", "jmath_g9a_s243", 3, BOOK_ID, 131104),
    (131144, "24.4 弧长和扇形面积", "jmath_g9a_s244", 4, BOOK_ID, 131104),

    # 第二十五章 概率初步
    (131105, "第二十五章 概率初步", "jmath_g9a_c25", 5, BOOK_ID, None),
    (131151, "25.1 随机事件与概率", "jmath_g9a_s251", 1, BOOK_ID, 131105),
    (131152, "25.2 用列举法求概率", "jmath_g9a_s252", 2, BOOK_ID, 131105),
    (131153, "25.3 用频率估计概率", "jmath_g9a_s253", 3, BOOK_ID, 131105),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 211001-211018 为册域层，211019-211098 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (211001, "jmath_g9a_domain_quadratic_concept", "初中九上·一元二次方程的概念与一般形式", 1, SUBJECT, G9, None),
    (211002, "jmath_g9a_domain_quadratic_solve", "初中九上·一元二次方程的解法", 2, SUBJECT, G9, None),
    (211003, "jmath_g9a_domain_quadratic_discriminant", "初中九上·根的判别式与根与系数的关系", 3, SUBJECT, G9, None),
    (211004, "jmath_g9a_domain_quadratic_application", "初中九上·一元二次方程的实际应用", 4, SUBJECT, G9, None),
    (211005, "jmath_g9a_domain_parabola_basic", "初中九上·二次函数的概念与基本图象", 5, SUBJECT, G9, None),
    (211006, "jmath_g9a_domain_parabola_vertex_form", "初中九上·二次函数的顶点式与图象性质", 6, SUBJECT, G9, None),
    (211007, "jmath_g9a_domain_parabola_equation", "初中九上·二次函数与一元二次方程的联系", 7, SUBJECT, G9, None),
    (211008, "jmath_g9a_domain_parabola_application", "初中九上·二次函数的实际应用与最值", 8, SUBJECT, G9, None),
    (211009, "jmath_g9a_domain_rotation", "初中九上·图形的旋转", 9, SUBJECT, G9, None),
    (211010, "jmath_g9a_domain_central_symmetry", "初中九上·中心对称与中心对称图形", 10, SUBJECT, G9, None),
    (211011, "jmath_g9a_domain_pattern_design", "初中九上·旋转综合与图案设计", 11, SUBJECT, G9, None),
    (211012, "jmath_g9a_domain_circle_property", "初中九上·圆的有关性质", 12, SUBJECT, G9, None),
    (211013, "jmath_g9a_domain_circle_position", "初中九上·点、直线与圆的位置关系", 13, SUBJECT, G9, None),
    (211014, "jmath_g9a_domain_regular_polygon", "初中九上·正多边形和圆", 14, SUBJECT, G9, None),
    (211015, "jmath_g9a_domain_arc_sector", "初中九上·弧长、扇形面积与圆锥", 15, SUBJECT, G9, None),
    (211016, "jmath_g9a_domain_random_event", "初中九上·随机事件与概率", 16, SUBJECT, G9, None),
    (211017, "jmath_g9a_domain_enumeration", "初中九上·用列举法求概率", 17, SUBJECT, G9, None),
    (211018, "jmath_g9a_domain_frequency", "初中九上·用频率估计概率", 18, SUBJECT, G9, None),

    # 一元二次方程的概念与一般形式
    (211019, "jmath_g9a_point_quadratic_define", "一元二次方程的定义与三个必备条件", 1, SUBJECT, G9, 211001),
    (211020, "jmath_g9a_point_quadratic_general_form", "一般形式 ax²+bx+c=0 中各项系数的识别", 2, SUBJECT, G9, 211001),
    (211021, "jmath_g9a_point_quadratic_parameter", "含参数方程为一元二次方程的 a≠0 条件", 3, SUBJECT, G9, 211001),
    (211022, "jmath_g9a_point_quadratic_root", "方程的根的意义与整体代入求值", 4, SUBJECT, G9, 211001),

    # 一元二次方程的解法
    (211023, "jmath_g9a_point_solve_square_root", "直接开平方法解 (x+m)²=n 型方程", 1, SUBJECT, G9, 211002),
    (211024, "jmath_g9a_point_solve_complete_square", "配方法的步骤与配方依据", 2, SUBJECT, G9, 211002),
    (211025, "jmath_g9a_point_solve_complete_lead", "二次项系数不为 1 时的配方处理", 3, SUBJECT, G9, 211002),
    (211026, "jmath_g9a_point_solve_formula", "求根公式的推导与公式法使用条件", 4, SUBJECT, G9, 211002),
    (211027, "jmath_g9a_point_solve_factor", "因式分解法：提公因式与平方差公式", 5, SUBJECT, G9, 211002),
    (211028, "jmath_g9a_point_solve_cross", "十字相乘法解整数系数的二次方程", 6, SUBJECT, G9, 211002),

    # 根的判别式与根与系数的关系
    (211029, "jmath_g9a_point_discriminant_sign", "判别式 Δ=b²−4ac 与根的情况对应", 1, SUBJECT, G9, 211003),
    (211030, "jmath_g9a_point_discriminant_parameter", "由根的情况求参数取值范围", 2, SUBJECT, G9, 211003),
    (211031, "jmath_g9a_point_vieta_sum_product", "韦达定理：两根之和与两根之积", 3, SUBJECT, G9, 211003),
    (211032, "jmath_g9a_point_vieta_symmetric", "利用韦达定理求对称代数式的值", 4, SUBJECT, G9, 211003),
    (211033, "jmath_g9a_point_vieta_condition", "韦达定理与判别式非负的联合使用", 5, SUBJECT, G9, 211003),

    # 一元二次方程的实际应用
    (211034, "jmath_g9a_point_app_growth", "平均增长率与平均降低率模型", 1, SUBJECT, G9, 211004),
    (211035, "jmath_g9a_point_app_spread", "传播、握手与比赛场次模型", 2, SUBJECT, G9, 211004),
    (211036, "jmath_g9a_point_app_area", "面积与几何图形中的方程建模", 3, SUBJECT, G9, 211004),
    (211037, "jmath_g9a_point_app_check", "方程解的实际意义取舍与检验", 4, SUBJECT, G9, 211004),

    # 二次函数的概念与基本图象
    (211038, "jmath_g9a_point_parabola_define", "二次函数的定义与一般式结构", 1, SUBJECT, G9, 211005),
    (211039, "jmath_g9a_point_parabola_domain", "二次函数自变量的取值范围", 2, SUBJECT, G9, 211005),
    (211040, "jmath_g9a_point_parabola_ax2", "y=ax² 的开口方向、对称轴与开口大小", 3, SUBJECT, G9, 211005),
    (211041, "jmath_g9a_point_parabola_plot", "描点法画图与抛物线的对称性", 4, SUBJECT, G9, 211005),

    # 二次函数的顶点式与图象性质
    (211042, "jmath_g9a_point_vertex_form", "顶点式中的顶点坐标与对称轴", 1, SUBJECT, G9, 211006),
    (211043, "jmath_g9a_point_parabola_shift", "抛物线平移的左加右减、上加下减", 2, SUBJECT, G9, 211006),
    (211044, "jmath_g9a_point_general_to_vertex", "一般式化为顶点式的配方过程", 3, SUBJECT, G9, 211006),
    (211045, "jmath_g9a_point_parabola_monotonic", "二次函数的增减性与最值判断", 4, SUBJECT, G9, 211006),
    (211046, "jmath_g9a_point_parabola_undetermined", "待定系数法求二次函数解析式", 5, SUBJECT, G9, 211006),
    (211047, "jmath_g9a_point_parabola_coefficient", "图象与系数 a、b、c 符号的对应关系", 6, SUBJECT, G9, 211006),

    # 二次函数与一元二次方程的联系
    (211048, "jmath_g9a_point_parabola_root", "抛物线与 x 轴交点横坐标即方程的根", 1, SUBJECT, G9, 211007),
    (211049, "jmath_g9a_point_parabola_intersections", "交点个数与判别式符号的对应", 2, SUBJECT, G9, 211007),
    (211050, "jmath_g9a_point_parabola_inequality", "二次函数图象与不等式解集", 3, SUBJECT, G9, 211007),
    (211051, "jmath_g9a_point_parabola_line", "抛物线与直线的交点及方程组的解", 4, SUBJECT, G9, 211007),

    # 二次函数的实际应用与最值
    (211052, "jmath_g9a_point_app_max_area", "面积最大的二次函数建模", 1, SUBJECT, G9, 211008),
    (211053, "jmath_g9a_point_app_profit", "销售利润最大化的定价模型", 2, SUBJECT, G9, 211008),
    (211054, "jmath_g9a_point_app_arch", "拱桥、喷泉等抛物线型实际问题", 3, SUBJECT, G9, 211008),
    (211055, "jmath_g9a_point_app_range", "自变量范围约束下的最值检验", 4, SUBJECT, G9, 211008),

    # 图形的旋转
    (211056, "jmath_g9a_point_rotation_elements", "旋转的三要素与旋转角", 1, SUBJECT, G9, 211009),
    (211057, "jmath_g9a_point_rotation_property", "旋转的性质：对应点到旋转中心距离相等", 2, SUBJECT, G9, 211009),
    (211058, "jmath_g9a_point_rotation_construct", "旋转作图与旋转中心的确定", 3, SUBJECT, G9, 211009),
    (211059, "jmath_g9a_point_rotation_coordinate", "坐标系中旋转后点的坐标变化", 4, SUBJECT, G9, 211009),
    (211060, "jmath_g9a_point_rotation_model", "旋转在等边三角形与正方形中的模型", 5, SUBJECT, G9, 211009),

    # 中心对称与中心对称图形
    (211061, "jmath_g9a_point_central_define", "中心对称的定义与对称中心的确定", 1, SUBJECT, G9, 211010),
    (211062, "jmath_g9a_point_central_property", "中心对称的性质：对称点连线被对称中心平分", 2, SUBJECT, G9, 211010),
    (211063, "jmath_g9a_point_central_vs_axis", "中心对称与轴对称的区别与联系", 3, SUBJECT, G9, 211010),
    (211064, "jmath_g9a_point_central_figure", "中心对称图形的识别与判断", 4, SUBJECT, G9, 211010),
    (211065, "jmath_g9a_point_origin_symmetry", "关于原点对称的点的坐标特征", 5, SUBJECT, G9, 211010),

    # 旋转综合与图案设计
    (211066, "jmath_g9a_point_pattern_design", "利用旋转进行图案设计与图形分割", 1, SUBJECT, G9, 211011),
    (211067, "jmath_g9a_point_rotation_congruence", "旋转与全等的综合证明", 2, SUBJECT, G9, 211011),
    (211068, "jmath_g9a_point_rotation_path", "旋转中的线段最值与路径长问题", 3, SUBJECT, G9, 211011),

    # 圆的有关性质
    (211069, "jmath_g9a_point_circle_concept", "圆的定义、弦、弧与圆心角的概念", 1, SUBJECT, G9, 211012),
    (211070, "jmath_g9a_point_perpendicular_chord", "垂径定理及其推论", 2, SUBJECT, G9, 211012),
    (211071, "jmath_g9a_point_chord_calc", "垂径定理在弦长与拱高计算中的应用", 3, SUBJECT, G9, 211012),
    (211072, "jmath_g9a_point_inscribed_angle", "圆周角定理与同弧所对圆周角相等", 4, SUBJECT, G9, 211012),
    (211073, "jmath_g9a_point_diameter_angle", "直径所对圆周角为直角及圆内接四边形性质", 5, SUBJECT, G9, 211012),

    # 点、直线与圆的位置关系
    (211074, "jmath_g9a_point_point_circle", "点与圆位置关系的数量判定及外接圆", 1, SUBJECT, G9, 211013),
    (211075, "jmath_g9a_point_line_circle", "直线与圆位置关系的判定", 2, SUBJECT, G9, 211013),
    (211076, "jmath_g9a_point_tangent_judge", "切线的判定定理与证明思路", 3, SUBJECT, G9, 211013),
    (211077, "jmath_g9a_point_tangent_property", "切线的性质：垂直于过切点的半径", 4, SUBJECT, G9, 211013),
    (211078, "jmath_g9a_point_tangent_length", "切线长定理与三角形内切圆", 5, SUBJECT, G9, 211013),

    # 正多边形和圆
    (211079, "jmath_g9a_point_polygon_elements", "正多边形的中心、半径、边心距与中心角", 1, SUBJECT, G9, 211014),
    (211080, "jmath_g9a_point_polygon_angle", "正多边形中心角与内角的计算", 2, SUBJECT, G9, 211014),
    (211081, "jmath_g9a_point_polygon_relation", "正多边形中半径、边心距与边长的关系", 3, SUBJECT, G9, 211014),
    (211082, "jmath_g9a_point_polygon_draw", "正多边形的画法与面积分割计算", 4, SUBJECT, G9, 211014),

    # 弧长、扇形面积与圆锥
    (211083, "jmath_g9a_point_arc_length", "弧长公式 l=nπR/180 的推导与计算", 1, SUBJECT, G9, 211015),
    (211084, "jmath_g9a_point_sector_area", "扇形面积公式及其与弧长公式的联系", 2, SUBJECT, G9, 211015),
    (211085, "jmath_g9a_point_shaded_area", "弓形面积与不规则阴影面积的转化", 3, SUBJECT, G9, 211015),
    (211086, "jmath_g9a_point_cone_net", "圆锥侧面展开图与母线、底面半径的关系", 4, SUBJECT, G9, 211015),
    (211087, "jmath_g9a_point_cone_area", "圆锥侧面积与全面积的计算", 5, SUBJECT, G9, 211015),

    # 随机事件与概率
    (211088, "jmath_g9a_point_event_type", "必然事件、不可能事件与随机事件", 1, SUBJECT, G9, 211016),
    (211089, "jmath_g9a_point_probability_meaning", "概率的意义与取值范围", 2, SUBJECT, G9, 211016),
    (211090, "jmath_g9a_point_probability_formula", "等可能情形下概率的计算公式", 3, SUBJECT, G9, 211016),
    (211091, "jmath_g9a_point_geometric_probability", "几何概率与面积型概率模型", 4, SUBJECT, G9, 211016),

    # 用列举法求概率
    (211092, "jmath_g9a_point_list_direct", "直接列举法求简单事件的概率", 1, SUBJECT, G9, 211017),
    (211093, "jmath_g9a_point_list_table", "列表法求两步试验的概率", 2, SUBJECT, G9, 211017),
    (211094, "jmath_g9a_point_list_tree", "树状图法求两步及以上试验的概率", 3, SUBJECT, G9, 211017),
    (211095, "jmath_g9a_point_list_replacement", "放回与不放回抽取的概率差异", 4, SUBJECT, G9, 211017),

    # 用频率估计概率
    (211096, "jmath_g9a_point_frequency_probability", "频率与概率的区别与联系", 1, SUBJECT, G9, 211018),
    (211097, "jmath_g9a_point_frequency_estimate", "用大量重复试验的频率估计概率", 2, SUBJECT, G9, 211018),
    (211098, "jmath_g9a_point_frequency_chart", "频率折线图的稳定性与实际决策", 3, SUBJECT, G9, 211018),
)

"""人教版（2013）初中数学九年级下册：章节树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G9 = 9
BOOK_ID = 1312

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版九年级数学下册",
    "jmath_g9b",
    12,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第二十六章 反比例函数
    (131201, "第二十六章 反比例函数", "jmath_g9b_c26", 1, BOOK_ID, None),
    (131211, "26.1 反比例函数", "jmath_g9b_s261", 1, BOOK_ID, 131201),
    (131212, "26.2 实际问题与反比例函数", "jmath_g9b_s262", 2, BOOK_ID, 131201),

    # 第二十七章 相似
    (131202, "第二十七章 相似", "jmath_g9b_c27", 2, BOOK_ID, None),
    (131221, "27.1 图形的相似", "jmath_g9b_s271", 1, BOOK_ID, 131202),
    (131222, "27.2 相似三角形", "jmath_g9b_s272", 2, BOOK_ID, 131202),
    (131223, "27.2.1 相似三角形的判定", "jmath_g9b_s2721", 1, BOOK_ID, 131222),
    (131224, "27.2.2 相似三角形的性质", "jmath_g9b_s2722", 2, BOOK_ID, 131222),
    (131225, "27.2.3 相似三角形应用举例", "jmath_g9b_s2723", 3, BOOK_ID, 131222),
    (131226, "27.3 位似", "jmath_g9b_s273", 3, BOOK_ID, 131202),

    # 第二十八章 锐角三角函数
    (131203, "第二十八章 锐角三角函数", "jmath_g9b_c28", 3, BOOK_ID, None),
    (131231, "28.1 锐角三角函数", "jmath_g9b_s281", 1, BOOK_ID, 131203),
    (131232, "28.2 解直角三角形及其应用", "jmath_g9b_s282", 2, BOOK_ID, 131203),
    (131233, "28.2.1 解直角三角形", "jmath_g9b_s2821", 1, BOOK_ID, 131232),
    (131234, "28.2.2 应用举例", "jmath_g9b_s2822", 2, BOOK_ID, 131232),

    # 第二十九章 投影与视图
    (131204, "第二十九章 投影与视图", "jmath_g9b_c29", 4, BOOK_ID, None),
    (131241, "29.1 投影", "jmath_g9b_s291", 1, BOOK_ID, 131204),
    (131242, "29.2 三视图", "jmath_g9b_s292", 2, BOOK_ID, 131204),
    (131243, "29.3 课题学习 制作立体模型", "jmath_g9b_s293", 3, BOOK_ID, 131204),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 212001-212015 为册域层，212016-212098 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (212001, "jmath_g9b_domain_inverse_concept", "初中九下·反比例函数的概念与解析式", 1, SUBJECT, G9, None),
    (212002, "jmath_g9b_domain_inverse_graph", "初中九下·反比例函数的图象与性质", 2, SUBJECT, G9, None),
    (212003, "jmath_g9b_domain_inverse_application", "初中九下·反比例函数的实际应用", 3, SUBJECT, G9, None),
    (212004, "jmath_g9b_domain_ratio_similar", "初中九下·比例线段与相似图形", 4, SUBJECT, G9, None),
    (212005, "jmath_g9b_domain_similar_judge", "初中九下·相似三角形的判定", 5, SUBJECT, G9, None),
    (212006, "jmath_g9b_domain_similar_property", "初中九下·相似三角形的性质", 6, SUBJECT, G9, None),
    (212007, "jmath_g9b_domain_similar_model", "初中九下·相似三角形的应用与模型", 7, SUBJECT, G9, None),
    (212008, "jmath_g9b_domain_homothetic", "初中九下·位似与坐标变换", 8, SUBJECT, G9, None),
    (212009, "jmath_g9b_domain_trig_concept", "初中九下·锐角三角函数的概念", 9, SUBJECT, G9, None),
    (212010, "jmath_g9b_domain_trig_special", "初中九下·特殊角的三角函数值", 10, SUBJECT, G9, None),
    (212011, "jmath_g9b_domain_right_triangle", "初中九下·解直角三角形", 11, SUBJECT, G9, None),
    (212012, "jmath_g9b_domain_trig_application", "初中九下·解直角三角形的实际应用", 12, SUBJECT, G9, None),
    (212013, "jmath_g9b_domain_projection", "初中九下·投影", 13, SUBJECT, G9, None),
    (212014, "jmath_g9b_domain_three_view", "初中九下·三视图", 14, SUBJECT, G9, None),
    (212015, "jmath_g9b_domain_solid_model", "初中九下·立体模型与展开图", 15, SUBJECT, G9, None),

    # 反比例函数的概念与解析式
    (212016, "jmath_g9b_point_inverse_define", "反比例函数的定义与 y=k/x 形式识别", 1, SUBJECT, G9, 212001),
    (212017, "jmath_g9b_point_inverse_k", "待定系数法确定反比例函数中的 k", 2, SUBJECT, G9, 212001),
    (212018, "jmath_g9b_point_inverse_forms", "y=k/x、xy=k、y=kx⁻¹ 三种等价形式", 3, SUBJECT, G9, 212001),
    (212019, "jmath_g9b_point_inverse_domain", "反比例函数中 k≠0 与自变量取值范围", 4, SUBJECT, G9, 212001),

    # 反比例函数的图象与性质
    (212020, "jmath_g9b_point_inverse_hyperbola", "双曲线的两支及其关于原点的对称性", 1, SUBJECT, G9, 212002),
    (212021, "jmath_g9b_point_inverse_quadrant", "k>0 与 k<0 时图象所在象限的判断", 2, SUBJECT, G9, 212002),
    (212022, "jmath_g9b_point_inverse_monotonic", "反比例函数在每一分支内的增减性", 3, SUBJECT, G9, 212002),
    (212023, "jmath_g9b_point_inverse_product", "图象上点的横纵坐标之积恒等于 k", 4, SUBJECT, G9, 212002),
    (212024, "jmath_g9b_point_inverse_axis_symmetry", "双曲线关于直线 y=x 与 y=−x 的对称性", 5, SUBJECT, G9, 212002),
    (212025, "jmath_g9b_point_inverse_plot", "描点法画反比例函数图象的步骤", 6, SUBJECT, G9, 212002),
    (212026, "jmath_g9b_point_inverse_k_area", "比例系数 k 的几何意义与矩形面积 |k|", 7, SUBJECT, G9, 212002),
    (212027, "jmath_g9b_point_inverse_line_intersect", "反比例函数与一次函数图象的交点求法", 8, SUBJECT, G9, 212002),
    (212028, "jmath_g9b_point_inverse_compare", "利用图象比较双曲线上两点函数值的大小", 9, SUBJECT, G9, 212002),

    # 反比例函数的实际应用
    (212029, "jmath_g9b_point_inverse_speed", "行程与工程问题中 v=s/t 型反比例建模", 1, SUBJECT, G9, 212003),
    (212030, "jmath_g9b_point_inverse_pressure", "压强、杠杆原理中的反比例关系", 2, SUBJECT, G9, 212003),
    (212031, "jmath_g9b_point_inverse_circuit", "电学中 I=U/R 的反比例关系", 3, SUBJECT, G9, 212003),
    (212032, "jmath_g9b_point_inverse_range", "实际问题中自变量的取值范围与图象端点", 4, SUBJECT, G9, 212003),

    # 比例线段与相似图形
    (212033, "jmath_g9b_point_ratio_segment", "比例线段的定义与比例的基本性质", 1, SUBJECT, G9, 212004),
    (212034, "jmath_g9b_point_ratio_property", "合比、分比与等比性质的应用", 2, SUBJECT, G9, 212004),
    (212035, "jmath_g9b_point_golden_ratio", "黄金分割与黄金比的计算", 3, SUBJECT, G9, 212004),
    (212036, "jmath_g9b_point_parallel_ratio", "平行线分线段成比例定理及其推论", 4, SUBJECT, G9, 212004),
    (212037, "jmath_g9b_point_similar_polygon", "相似多边形的定义、相似比与周长面积比", 5, SUBJECT, G9, 212004),

    # 相似三角形的判定
    (212038, "jmath_g9b_point_similar_prepare", "平行于一边的直线截得三角形相似", 1, SUBJECT, G9, 212005),
    (212039, "jmath_g9b_point_similar_sss", "三边成比例判定两个三角形相似", 2, SUBJECT, G9, 212005),
    (212040, "jmath_g9b_point_similar_sas", "两边成比例且夹角相等判定相似", 3, SUBJECT, G9, 212005),
    (212041, "jmath_g9b_point_similar_aa", "两角分别相等判定两个三角形相似", 4, SUBJECT, G9, 212005),
    (212042, "jmath_g9b_point_similar_choose", "相似判定方法的选择与证明书写规范", 5, SUBJECT, G9, 212005),

    # 相似三角形的性质
    (212043, "jmath_g9b_point_similar_correspond", "相似三角形对应边成比例、对应角相等", 1, SUBJECT, G9, 212006),
    (212044, "jmath_g9b_point_similar_height", "相似三角形对应高的比等于相似比", 2, SUBJECT, G9, 212006),
    (212045, "jmath_g9b_point_similar_median", "对应中线与角平分线的比等于相似比", 3, SUBJECT, G9, 212006),
    (212046, "jmath_g9b_point_similar_perimeter", "相似三角形周长比等于相似比", 4, SUBJECT, G9, 212006),
    (212047, "jmath_g9b_point_similar_area", "相似三角形面积比等于相似比的平方", 5, SUBJECT, G9, 212006),

    # 相似三角形的应用与模型
    (212048, "jmath_g9b_point_similar_shadow", "利用影长与相似测量物体高度", 1, SUBJECT, G9, 212007),
    (212049, "jmath_g9b_point_similar_river", "利用相似测量河宽等不可直接测距离", 2, SUBJECT, G9, 212007),
    (212050, "jmath_g9b_point_similar_models", "“A 字型”与“X 字型”基本相似模型", 3, SUBJECT, G9, 212007),
    (212051, "jmath_g9b_point_similar_projection", "直角三角形中的射影定理与相似", 4, SUBJECT, G9, 212007),

    # 位似与坐标变换
    (212052, "jmath_g9b_point_homothetic_define", "位似图形的定义与位似中心的确定", 1, SUBJECT, G9, 212008),
    (212053, "jmath_g9b_point_homothetic_relation", "位似图形与相似图形的关系及位似比", 2, SUBJECT, G9, 212008),
    (212054, "jmath_g9b_point_homothetic_coordinate", "以原点为位似中心的坐标变化规律", 3, SUBJECT, G9, 212008),
    (212055, "jmath_g9b_point_homothetic_negative", "位似比为负时对应点位于反向延长线", 4, SUBJECT, G9, 212008),
    (212056, "jmath_g9b_point_homothetic_draw", "位似作图与图形的放大与缩小", 5, SUBJECT, G9, 212008),

    # 锐角三角函数的概念
    (212057, "jmath_g9b_point_trig_define", "正弦、余弦、正切的定义与边角对应", 1, SUBJECT, G9, 212009),
    (212058, "jmath_g9b_point_trig_ratio", "锐角三角函数值只与角的大小有关", 2, SUBJECT, G9, 212009),
    (212059, "jmath_g9b_point_trig_identity", "同角关系 sin²A+cos²A=1 与 tanA=sinA/cosA", 3, SUBJECT, G9, 212009),
    (212060, "jmath_g9b_point_trig_complement", "互余两角关系 sinA=cos(90°−A)", 4, SUBJECT, G9, 212009),
    (212061, "jmath_g9b_point_trig_value_range", "锐角三角函数值的范围与增减性", 5, SUBJECT, G9, 212009),

    # 特殊角的三角函数值
    (212062, "jmath_g9b_point_trig_table", "30°、45°、60° 三角函数值表", 1, SUBJECT, G9, 212010),
    (212063, "jmath_g9b_point_trig_angle_back", "由特殊角三角函数值反求锐角", 2, SUBJECT, G9, 212010),
    (212064, "jmath_g9b_point_trig_simplify", "含特殊角的三角函数式化简求值", 3, SUBJECT, G9, 212010),

    # 解直角三角形
    (212065, "jmath_g9b_point_solve_define", "解直角三角形的定义与已知元素分析", 1, SUBJECT, G9, 212011),
    (212066, "jmath_g9b_point_solve_two_sides", "已知两边解直角三角形", 2, SUBJECT, G9, 212011),
    (212067, "jmath_g9b_point_solve_one_angle", "已知一边一锐角解直角三角形", 3, SUBJECT, G9, 212011),
    (212068, "jmath_g9b_point_solve_obtuse", "作高把斜三角形转化为直角三角形", 4, SUBJECT, G9, 212011),

    # 解直角三角形的实际应用
    (212069, "jmath_g9b_point_app_elevation", "仰角、俯角的概念与高度测量问题", 1, SUBJECT, G9, 212012),
    (212070, "jmath_g9b_point_app_slope", "坡度、坡角的概念与斜坡计算", 2, SUBJECT, G9, 212012),
    (212071, "jmath_g9b_point_app_bearing", "方位角与航海、航空方向问题", 3, SUBJECT, G9, 212012),
    (212072, "jmath_g9b_point_app_approx", "实际测量中的近似计算与有效数字", 4, SUBJECT, G9, 212012),

    # 投影
    (212073, "jmath_g9b_point_projection_parallel", "平行投影与中心投影的区别", 1, SUBJECT, G9, 212013),
    (212074, "jmath_g9b_point_projection_orthogonal", "正投影的概念与基本性质", 2, SUBJECT, G9, 212013),
    (212075, "jmath_g9b_point_projection_shadow", "阳光下影子的方向与长短变化规律", 3, SUBJECT, G9, 212013),
    (212076, "jmath_g9b_point_projection_height", "由投影确定物体的高度与位置", 4, SUBJECT, G9, 212013),

    # 三视图
    (212077, "jmath_g9b_point_view_form", "三视图的形成与主视、左视、俯视方向", 1, SUBJECT, G9, 212014),
    (212078, "jmath_g9b_point_view_relation", "三视图“长对正、高平齐、宽相等”", 2, SUBJECT, G9, 212014),
    (212079, "jmath_g9b_point_view_draw", "由几何体画出三视图", 3, SUBJECT, G9, 212014),
    (212080, "jmath_g9b_point_view_restore", "由三视图还原几何体", 4, SUBJECT, G9, 212014),
    (212081, "jmath_g9b_point_view_surface", "由三视图计算表面积与体积", 5, SUBJECT, G9, 212014),
    (212082, "jmath_g9b_point_view_cubes", "小正方体堆砌体的三视图与个数问题", 6, SUBJECT, G9, 212014),

    # 立体模型与展开图
    (212083, "jmath_g9b_point_net_common", "常见几何体的展开图", 1, SUBJECT, G9, 212015),
    (212084, "jmath_g9b_point_net_judge", "由展开图判断对应的立体图形", 2, SUBJECT, G9, 212015),
    (212085, "jmath_g9b_point_net_cube_opposite", "正方体展开图中的相对面判断", 3, SUBJECT, G9, 212015),
)

"""人教版小学数学四年级上册：九个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G4 = 4
BOOK_ID = 1419

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学四年级上册",
    "pmath_g4a",
    19,
    "人民教育出版社",
    SUBJECT,
    G4,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 九个单元
    (141901, "第一单元 大数的认识", "pmath_g4a_u01", 1, BOOK_ID, None),
    (141902, "第二单元 公顷和平方千米", "pmath_g4a_u02", 2, BOOK_ID, None),
    (141903, "第三单元 角的度量", "pmath_g4a_u03", 3, BOOK_ID, None),
    (141904, "第四单元 三位数乘两位数", "pmath_g4a_u04", 4, BOOK_ID, None),
    (141905, "第五单元 平行四边形和梯形", "pmath_g4a_u05", 5, BOOK_ID, None),
    (141906, "第六单元 除数是两位数的除法", "pmath_g4a_u06", 6, BOOK_ID, None),
    (141907, "第七单元 条形统计图", "pmath_g4a_u07", 7, BOOK_ID, None),
    (141908, "第八单元 数学广角——优化", "pmath_g4a_u08", 8, BOOK_ID, None),
    (141909, "第九单元 总复习", "pmath_g4a_u09", 9, BOOK_ID, None),

    # 第一单元 大数的认识
    (141910, "亿以内数的认识", "pmath_g4a_l01", 1, BOOK_ID, 141901),
    (141911, "数的产生与十进制计数法", "pmath_g4a_l02", 2, BOOK_ID, 141901),
    (141912, "亿以上数的认识", "pmath_g4a_l03", 3, BOOK_ID, 141901),
    (141913, "计算工具的认识", "pmath_g4a_l04", 4, BOOK_ID, 141901),

    # 第二单元 公顷和平方千米
    (141914, "公顷和平方千米的认识与换算", "pmath_g4a_l05", 1, BOOK_ID, 141902),

    # 第三单元 角的度量
    (141915, "线段、直线、射线", "pmath_g4a_l06", 1, BOOK_ID, 141903),
    (141916, "角的度量", "pmath_g4a_l07", 2, BOOK_ID, 141903),
    (141917, "角的分类", "pmath_g4a_l08", 3, BOOK_ID, 141903),
    (141918, "画角", "pmath_g4a_l09", 4, BOOK_ID, 141903),

    # 第四单元 三位数乘两位数
    (141919, "笔算乘法", "pmath_g4a_l10", 1, BOOK_ID, 141904),
    (141920, "积的变化规律", "pmath_g4a_l11", 2, BOOK_ID, 141904),
    (141921, "常见的数量关系", "pmath_g4a_l12", 3, BOOK_ID, 141904),

    # 第五单元 平行四边形和梯形
    (141922, "平行与垂直", "pmath_g4a_l13", 1, BOOK_ID, 141905),
    (141923, "平行四边形", "pmath_g4a_l14", 2, BOOK_ID, 141905),
    (141924, "梯形", "pmath_g4a_l15", 3, BOOK_ID, 141905),

    # 第六单元 除数是两位数的除法
    (141925, "口算除法", "pmath_g4a_l16", 1, BOOK_ID, 141906),
    (141926, "笔算除法", "pmath_g4a_l17", 2, BOOK_ID, 141906),
    (141927, "整理和复习", "pmath_g4a_l18", 3, BOOK_ID, 141906),

    # 第七单元 条形统计图
    (141928, "认识条形统计图", "pmath_g4a_l19", 1, BOOK_ID, 141907),

    # 第八单元 数学广角——优化
    (141929, "合理安排时间与对策问题", "pmath_g4a_l20", 1, BOOK_ID, 141908),

    # 第九单元 总复习
    (141930, "总复习", "pmath_g4a_l21", 1, BOOK_ID, 141909),
)

# id / code / name / sort_order / subject_id / parent_id
# 261001-261009 为册域层，261010-261085 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (261001, "pmath_g4a_domain_u01", "小学数学四上·第一单元 大数的认识", 1, SUBJECT, None),
    (261002, "pmath_g4a_domain_u02", "小学数学四上·第二单元 公顷和平方千米", 2, SUBJECT, None),
    (261003, "pmath_g4a_domain_u03", "小学数学四上·第三单元 角的度量", 3, SUBJECT, None),
    (261004, "pmath_g4a_domain_u04", "小学数学四上·第四单元 三位数乘两位数", 4, SUBJECT, None),
    (261005, "pmath_g4a_domain_u05", "小学数学四上·第五单元 平行四边形和梯形", 5, SUBJECT, None),
    (261006, "pmath_g4a_domain_u06", "小学数学四上·第六单元 除数是两位数的除法", 6, SUBJECT, None),
    (261007, "pmath_g4a_domain_u07", "小学数学四上·第七单元 条形统计图", 7, SUBJECT, None),
    (261008, "pmath_g4a_domain_u08", "小学数学四上·第八单元 数学广角——优化", 8, SUBJECT, None),
    (261009, "pmath_g4a_domain_u09", "小学数学四上·第九单元 总复习", 9, SUBJECT, None),

    # 第一单元 大数的认识
    (261010, "pmath_g4a_point_units_order", "数位与计数单位：个、十、百、千、万、十万、百万、千万、亿，相邻两个计数单位间的进率是10", 1, SUBJECT, 261001),
    (261011, "pmath_g4a_point_number_grades", "数位顺序表的分级：从右起每四位一级，依次是个级、万级、亿级，每级都有四个数位", 2, SUBJECT, 261001),
    (261012, "pmath_g4a_point_read_within_yi", "亿以内数的读法：先分级再读，先读万级、后读个级，每级末尾的0都不读", 3, SUBJECT, 261001),
    (261013, "pmath_g4a_point_read_zero_rule", "中间有0的读法：每级中间有一个0或连续几个0，都只读一个“零”，不能逐位读", 4, SUBJECT, 261001),
    (261014, "pmath_g4a_point_write_within_yi", "亿以内数的写法：从高位写起，先写万级再写个级，哪一位上一个单位也没有就写0占位", 5, SUBJECT, 261001),
    (261015, "pmath_g4a_point_compare_within_yi", "亿以内数的大小比较：位数不同时位数多的数大；位数相同时从最高位起逐位比较", 6, SUBJECT, 261001),
    (261016, "pmath_g4a_point_rewrite_wan", "整万数的改写：把万位后面的四个0去掉，换成一个“万”字，数的大小不变", 7, SUBJECT, 261001),
    (261017, "pmath_g4a_point_approx_wan", "省略万位后面的尾数：看千位上的数四舍五入，再在得数后面写“万”字，用“≈”连接", 8, SUBJECT, 261001),
    (261018, "pmath_g4a_point_number_origin", "数的产生：从实物记数、结绳记数、刻道记数逐步发展到用数字符号表示数量", 9, SUBJECT, 261001),
    (261019, "pmath_g4a_point_natural_number", "自然数的认识：0是最小的自然数，没有最大的自然数，自然数的个数是无限的", 10, SUBJECT, 261001),
    (261020, "pmath_g4a_point_decimal_system", "十进制计数法：每相邻两个计数单位之间的进率都是10，满十就向前一位进一", 11, SUBJECT, 261001),
    (261021, "pmath_g4a_point_read_beyond_yi", "亿以上数的读写法：按亿级、万级、个级分级读写，0的读写规则与亿以内数完全相同", 12, SUBJECT, 261001),
    (261022, "pmath_g4a_point_rewrite_yi", "整亿数的改写与近似数：去掉亿位后面的八个0写“亿”；省略亿位后面尾数要看千万位四舍五入", 13, SUBJECT, 261001),

    # 第二单元 公顷和平方千米
    (261023, "pmath_g4a_point_hectare", "公顷的认识：边长100米的正方形面积是1公顷，1公顷=10000平方米", 1, SUBJECT, 261002),
    (261024, "pmath_g4a_point_square_km", "平方千米的认识：边长1000米的正方形面积是1平方千米，1平方千米=1000000平方米", 2, SUBJECT, 261002),
    (261025, "pmath_g4a_point_ha_km_rate", "公顷与平方千米的进率：1平方千米=100公顷，二者相差100倍", 3, SUBJECT, 261002),
    (261026, "pmath_g4a_point_area_convert_g4", "平方米与公顷的换算：平方米数除以10000得公顷数，公顷数乘10000得平方米数", 4, SUBJECT, 261002),
    (261027, "pmath_g4a_point_area_unit_choose", "面积单位的选择：教室用平方米、公园用公顷、城市和国土用平方千米，按实际大小选单位", 5, SUBJECT, 261002),
    (261028, "pmath_g4a_point_area_apply_g4", "公顷平方千米的实际应用：先算长方形或正方形的面积，再按进率换算，注意1公顷不是1000平方米", 6, SUBJECT, 261002),

    # 第三单元 角的度量
    (261029, "pmath_g4a_point_segment", "线段的认识：有两个端点，可以量出长度，两点之间所有连线中线段最短", 1, SUBJECT, 261003),
    (261030, "pmath_g4a_point_line_ray", "直线与射线：直线没有端点、向两端无限延伸；射线只有一个端点、向一端无限延伸", 2, SUBJECT, 261003),
    (261031, "pmath_g4a_point_line_compare", "线段、直线、射线的区别：端点个数不同、能否度量不同、延伸方向不同，三者都是直的", 3, SUBJECT, 261003),
    (261032, "pmath_g4a_point_angle_define", "角的定义：从一点引出两条射线所组成的图形，这一点叫角的顶点，两条射线叫角的边", 4, SUBJECT, 261003),
    (261033, "pmath_g4a_point_angle_size", "角的大小：角的大小与两条边张开的大小有关，与边画得长短无关", 5, SUBJECT, 261003),
    (261034, "pmath_g4a_point_protractor", "量角器的认识：中心点、0刻度线、内圈刻度与外圈刻度，量角前先认清刻度方向", 6, SUBJECT, 261003),
    (261035, "pmath_g4a_point_measure_angle", "量角的方法：中心对顶点、0刻度线对一条边，看另一条边落在哪个刻度上，注意读内圈还是外圈", 7, SUBJECT, 261003),
    (261036, "pmath_g4a_point_angle_classify", "角的分类：锐角小于90°，直角等于90°，钝角大于90°小于180°，平角180°，周角360°", 8, SUBJECT, 261003),
    (261037, "pmath_g4a_point_draw_angle", "画角的方法：先画一条射线，量角器中心对端点、0刻度线对射线，找到刻度点再画另一条射线", 9, SUBJECT, 261003),
    (261038, "pmath_g4a_point_angle_calc", "角度的计算：1平角=2直角，1周角=2平角=4直角，用三角尺30°、45°、60°、90°拼出指定角", 10, SUBJECT, 261003),

    # 第四单元 三位数乘两位数
    (261039, "pmath_g4a_point_multiply_3by2", "三位数乘两位数的笔算：先用个位上的数乘，再用十位上的数乘，最后把两次积相加", 1, SUBJECT, 261004),
    (261040, "pmath_g4a_point_partial_align", "第二部分积的对位：用十位上的数去乘，得数的末位要与十位对齐，不能与个位对齐", 2, SUBJECT, 261004),
    (261041, "pmath_g4a_point_multiply_carry_g4", "乘法的进位处理：每一步乘得的积满几十就向前一位进几，下一步要把进位数加上", 3, SUBJECT, 261004),
    (261042, "pmath_g4a_point_factor_middle_zero", "因数中间有0的乘法：0乘任何数都得0，该位仍要占位，注意与前一位的进位数相加", 4, SUBJECT, 261004),
    (261043, "pmath_g4a_point_factor_tail_zero", "因数末尾有0的乘法：先算0前面的数，再看两个因数末尾共有几个0，就在积的末尾添几个0", 5, SUBJECT, 261004),
    (261044, "pmath_g4a_point_product_change", "积的变化规律：一个因数不变，另一个因数乘几或除以几（0除外），积也乘几或除以几", 6, SUBJECT, 261004),
    (261045, "pmath_g4a_point_product_change_mix", "积的变化规律拓展：两个因数分别乘a和乘b，积乘a×b；一个因数乘a另一个除以a，积不变", 7, SUBJECT, 261004),
    (261046, "pmath_g4a_point_price_quantity", "单价、数量、总价：单价×数量=总价，总价÷数量=单价，总价÷单价=数量", 8, SUBJECT, 261004),
    (261047, "pmath_g4a_point_speed_time", "速度、时间、路程：速度×时间=路程，路程÷时间=速度，路程÷速度=时间；速度写作“千米/时”", 9, SUBJECT, 261004),

    # 第五单元 平行四边形和梯形
    (261048, "pmath_g4a_point_two_lines", "同一平面内两条直线的位置关系：要么相交，要么不相交，不相交就是平行", 1, SUBJECT, 261005),
    (261049, "pmath_g4a_point_parallel", "平行的定义与表示：同一平面内不相交的两条直线互相平行，记作a∥b，平行线间的距离处处相等", 2, SUBJECT, 261005),
    (261050, "pmath_g4a_point_perpendicular", "垂直的定义与表示：两条直线相交成直角时互相垂直，交点叫垂足，记作a⊥b", 3, SUBJECT, 261005),
    (261051, "pmath_g4a_point_draw_parallel", "平行线的画法：用直尺和三角尺，一靠、二移、三画，三角尺移动时不能转动", 4, SUBJECT, 261005),
    (261052, "pmath_g4a_point_draw_perpendicular", "垂线的画法：过直线上一点或直线外一点画已知直线的垂线，都只能画一条", 5, SUBJECT, 261005),
    (261053, "pmath_g4a_point_point_line_distance", "点到直线的距离：从直线外一点到这条直线所画的垂直线段最短，它的长度叫点到直线的距离", 6, SUBJECT, 261005),
    (261054, "pmath_g4a_point_parallelogram_feature", "平行四边形的特征：两组对边分别平行且相等，对角相等，容易变形，具有不稳定性", 7, SUBJECT, 261005),
    (261055, "pmath_g4a_point_parallelogram_height", "平行四边形的底和高：从一条边上的一点向对边引垂线，这点到垂足间的线段叫高，高与底互相垂直", 8, SUBJECT, 261005),
    (261056, "pmath_g4a_point_trapezoid_feature", "梯形的特征：只有一组对边平行的四边形，平行的一组对边叫上底和下底，另一组叫腰", 9, SUBJECT, 261005),
    (261057, "pmath_g4a_point_quad_relation", "四边形之间的关系：长方形、正方形是特殊的平行四边形，等腰梯形和直角梯形是特殊的梯形", 10, SUBJECT, 261005),

    # 第六单元 除数是两位数的除法
    (261058, "pmath_g4a_point_divide_tens_oral", "整十数除法的口算：想乘法算除法，或把被除数和除数都看成几个十再除", 1, SUBJECT, 261006),
    (261059, "pmath_g4a_point_divide_estimate_g4", "除法的估算：把除数看成接近的整十数，把被除数看成接近的整百整十数，结果用“≈”表示", 2, SUBJECT, 261006),
    (261060, "pmath_g4a_point_divide_tens_written", "除数是整十数的笔算：先看被除数前两位，够除就除，商写在对应数位上", 3, SUBJECT, 261006),
    (261061, "pmath_g4a_point_trial_round_down", "四舍试商：除数个位是1、2、3、4时舍去尾数看作整十数试商，初商可能偏大要调小", 4, SUBJECT, 261006),
    (261062, "pmath_g4a_point_trial_round_up", "五入试商：除数个位是5、6、7、8、9时向前一位进一看作整十数试商，初商可能偏小要调大", 5, SUBJECT, 261006),
    (261063, "pmath_g4a_point_trial_flexible", "不接近整十数的试商：如26、24等除数，可借助乘法口诀灵活试商，试商后必须检验余数", 6, SUBJECT, 261006),
    (261064, "pmath_g4a_point_quotient_one", "商是一位数的笔算：确定商的书写位置，每次除后的余数必须比除数小", 7, SUBJECT, 261006),
    (261065, "pmath_g4a_point_quotient_two", "商是两位数的笔算：先看被除数前两位，除到哪一位商就写在哪一位的上面", 8, SUBJECT, 261006),
    (261066, "pmath_g4a_point_quotient_zero_g4", "商中间或末尾有0的除法：哪一位不够商1就在那一位商0占位，末尾余数不够除也要商0", 9, SUBJECT, 261006),
    (261067, "pmath_g4a_point_quotient_constant", "商不变的规律：被除数和除数同时乘或除以相同的数（0除外），商不变", 10, SUBJECT, 261006),
    (261068, "pmath_g4a_point_quotient_constant_apply", "商不变规律的应用：被除数和除数末尾同时去掉相同个数的0使计算简便，但余数要按原数还原", 11, SUBJECT, 261006),
    (261069, "pmath_g4a_point_divide_check_g4", "除法验算与整理复习：商×除数+余数=被除数，余数一定小于除数，试商调商要反复检验", 12, SUBJECT, 261006),

    # 第七单元 条形统计图
    (261070, "pmath_g4a_point_bar_chart", "条形统计图的认识：用直条的长短表示数量的多少，能直观地看出各类数据的差别", 1, SUBJECT, 261007),
    (261071, "pmath_g4a_point_bar_parts", "条形统计图的组成：标题、横轴表示项目、纵轴表示数量与单位、直条和数据标注缺一不可", 2, SUBJECT, 261007),
    (261072, "pmath_g4a_point_bar_grid_scale", "一格表示多个单位：数据较大时可用1格表示2个、5个或更多个单位，纵轴刻度要均匀", 3, SUBJECT, 261007),
    (261073, "pmath_g4a_point_bar_draw", "条形统计图的绘制：先确定横纵轴和每格代表的数量，再画等宽直条并标注数据", 4, SUBJECT, 261007),
    (261074, "pmath_g4a_point_bar_analyze", "条形统计图的分析：比较数量多少、求总数与相差，并根据数据变化做出合理判断和预测", 5, SUBJECT, 261007),

    # 第八单元 数学广角——优化
    (261075, "pmath_g4a_point_tea_optimize", "沏茶问题：先理清各项事情的先后顺序，能同时做的事情同时做，找出最省时的安排", 1, SUBJECT, 261008),
    (261076, "pmath_g4a_point_pancake", "烙饼问题：每次最多烙2张、每面3分钟，3张饼用交替烙法只需9分钟，尽量让锅里不空位", 2, SUBJECT, 261008),
    (261077, "pmath_g4a_point_tianji", "田忌赛马的对策：用下等马对上等马、上等马对中等马、中等马对下等马，以三局两胜取胜", 3, SUBJECT, 261008),
    (261078, "pmath_g4a_point_optimize_method", "优化的思考方法：列举所有可行方案，比较所用时间或胜负场次，从中选出最优方案", 4, SUBJECT, 261008),
    (261079, "pmath_g4a_point_queue_optimize", "排队等候问题：按每人用时从少到多排序，能使所有人等候的总时间最短", 5, SUBJECT, 261008),

    # 第九单元 总复习
    (261080, "pmath_g4a_point_review_big_number", "大数总复习：数位顺序表、分级读写、大小比较、改写与四舍五入求近似数", 1, SUBJECT, 261009),
    (261081, "pmath_g4a_point_review_multiply_divide", "乘除法总复习：三位数乘两位数、除数是两位数的笔算，试商调商与验算方法", 2, SUBJECT, 261009),
    (261082, "pmath_g4a_point_review_geometry", "图形与几何总复习：线段直线射线、角的度量与分类、平行与垂直、平行四边形和梯形", 3, SUBJECT, 261009),
    (261083, "pmath_g4a_point_review_area_unit", "面积单位总复习：公顷和平方千米的意义、进率与单位换算，结合实际选择合适单位", 4, SUBJECT, 261009),
    (261084, "pmath_g4a_point_review_stat_optimize", "统计与优化总复习：条形统计图的绘制与分析，合理安排时间与田忌赛马类对策问题", 5, SUBJECT, 261009),
    (261085, "pmath_g4a_point_review_error", "易错点与检查习惯：分级读写不漏0、试商后验余数、换算先看进率、画高要标直角符号", 6, SUBJECT, 261009),
)

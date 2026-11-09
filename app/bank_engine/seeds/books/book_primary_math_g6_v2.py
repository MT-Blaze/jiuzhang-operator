"""人教版小学数学六年级下册：六个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G6 = 6
BOOK_ID = 1424

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学六年级下册",
    "pmath_g6b",
    24,
    "人民教育出版社",
    SUBJECT,
    G6,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 六个单元
    (142401, "第一单元 负数", "pmath_g6b_u01", 1, BOOK_ID, None),
    (142410, "第二单元 百分数（二）", "pmath_g6b_u02", 2, BOOK_ID, None),
    (142420, "第三单元 圆柱与圆锥", "pmath_g6b_u03", 3, BOOK_ID, None),
    (142430, "第四单元 比例", "pmath_g6b_u04", 4, BOOK_ID, None),
    (142440, "第五单元 数学广角——鸽巢问题", "pmath_g6b_u05", 5, BOOK_ID, None),
    (142450, "第六单元 整理和复习", "pmath_g6b_u06", 6, BOOK_ID, None),

    # 第一单元 负数
    (142402, "负数的认识", "pmath_g6b_l01", 1, BOOK_ID, 142401),
    (142403, "在数轴上表示数", "pmath_g6b_l02", 2, BOOK_ID, 142401),

    # 第二单元 百分数（二）
    (142411, "折扣", "pmath_g6b_l03", 1, BOOK_ID, 142410),
    (142412, "成数", "pmath_g6b_l04", 2, BOOK_ID, 142410),
    (142413, "税率", "pmath_g6b_l05", 3, BOOK_ID, 142410),
    (142414, "利率", "pmath_g6b_l06", 4, BOOK_ID, 142410),
    (142415, "购物中的实际问题", "pmath_g6b_l07", 5, BOOK_ID, 142410),

    # 第三单元 圆柱与圆锥
    (142421, "圆柱的认识", "pmath_g6b_l08", 1, BOOK_ID, 142420),
    (142422, "圆柱的表面积", "pmath_g6b_l09", 2, BOOK_ID, 142420),
    (142423, "圆柱的体积", "pmath_g6b_l10", 3, BOOK_ID, 142420),
    (142424, "圆锥的认识", "pmath_g6b_l11", 4, BOOK_ID, 142420),
    (142425, "圆锥的体积", "pmath_g6b_l12", 5, BOOK_ID, 142420),

    # 第四单元 比例
    (142431, "比例的意义和基本性质", "pmath_g6b_l13", 1, BOOK_ID, 142430),
    (142432, "正比例和反比例", "pmath_g6b_l14", 2, BOOK_ID, 142430),
    (142433, "比例尺", "pmath_g6b_l15", 3, BOOK_ID, 142430),
    (142434, "图形的放大与缩小", "pmath_g6b_l16", 4, BOOK_ID, 142430),
    (142435, "用比例解决问题", "pmath_g6b_l17", 5, BOOK_ID, 142430),

    # 第五单元 数学广角——鸽巢问题
    (142441, "鸽巢问题", "pmath_g6b_l18", 1, BOOK_ID, 142440),

    # 第六单元 整理和复习
    (142451, "数与代数", "pmath_g6b_l19", 1, BOOK_ID, 142450),
    (142452, "图形与几何", "pmath_g6b_l20", 2, BOOK_ID, 142450),
    (142453, "统计与概率", "pmath_g6b_l21", 3, BOOK_ID, 142450),
    (142454, "数学思考", "pmath_g6b_l22", 4, BOOK_ID, 142450),
    (142455, "综合与实践", "pmath_g6b_l23", 5, BOOK_ID, 142450),
)

# id / code / name / sort_order / subject_id / parent_id
# 266001-266006 为册域层，266010-266090 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (266001, "pmath_g6b_domain_u01", "小学数学六下·第一单元 负数", 1, SUBJECT, None),
    (266002, "pmath_g6b_domain_u02", "小学数学六下·第二单元 百分数（二）", 2, SUBJECT, None),
    (266003, "pmath_g6b_domain_u03", "小学数学六下·第三单元 圆柱与圆锥", 3, SUBJECT, None),
    (266004, "pmath_g6b_domain_u04", "小学数学六下·第四单元 比例", 4, SUBJECT, None),
    (266005, "pmath_g6b_domain_u05", "小学数学六下·第五单元 数学广角——鸽巢问题", 5, SUBJECT, None),
    (266006, "pmath_g6b_domain_u06", "小学数学六下·第六单元 整理和复习", 6, SUBJECT, None),

    # 第一单元 负数
    (266010, "pmath_g6b_point_negative_origin", "负数的产生：在测量温度、记录海拔、表示收支等情境中，出现了不够减或方向相反的量，需要引入负数", 1, SUBJECT, 266001),
    (266011, "pmath_g6b_point_negative_read_write", "正负数的读写法：正数前面可加“+”也可省略，负数前面必须写“-”，负号表示与正数意义相反", 2, SUBJECT, 266001),
    (266012, "pmath_g6b_point_zero_meaning", "0的特殊地位：0既不是正数也不是负数，它是正数和负数的分界点", 3, SUBJECT, 266001),
    (266013, "pmath_g6b_point_opposite_quantity", "用正负数表示相反意义的量：规定一种量为正，与它意义相反的量就记为负，如收入为正则支出为负", 4, SUBJECT, 266001),
    (266014, "pmath_g6b_point_number_line_elements", "数轴的三要素：原点、正方向、单位长度，三者缺一不可", 5, SUBJECT, 266001),
    (266015, "pmath_g6b_point_number_line_place", "在数轴上表示正负数：以0为原点，正数在原点右侧，负数在原点左侧，每个数对应唯一一个点", 6, SUBJECT, 266001),
    (266016, "pmath_g6b_point_negative_compare", "负数的大小比较：数轴上右边的数总比左边的数大，因此负数都小于0，两个负数绝对值大的反而小", 7, SUBJECT, 266001),
    (266017, "pmath_g6b_point_negative_application", "正负数的实际应用：用正负数表示海拔高度、水位变化、盈亏、时差和误差范围等，先确定基准再判断正负", 8, SUBJECT, 266001),
    (266018, "pmath_g6b_point_number_line_distance", "数轴上两点间的关系：互为相反数的两个点到原点距离相等，两点间距离等于对应两数之差的绝对值", 9, SUBJECT, 266001),

    # 第二单元 百分数（二）
    (266020, "pmath_g6b_point_discount_mean", "折扣的意义：几折就是十分之几，也就是百分之几十，如八折=80%，八五折=85%", 1, SUBJECT, 266002),
    (266021, "pmath_g6b_point_discount_calc", "折扣的计算：现价=原价×折扣，折扣通常化成百分数再计算，注意折扣不能超过十折", 2, SUBJECT, 266002),
    (266022, "pmath_g6b_point_discount_reverse", "折扣问题的逆向求解：已知现价和折扣求原价用除法，已知原价和现价求折扣用现价除以原价", 3, SUBJECT, 266002),
    (266023, "pmath_g6b_point_chengshu_mean", "成数的意义：几成就是十分之几，也就是百分之几十，成数常用于表示农业增产、减产等幅度", 4, SUBJECT, 266002),
    (266024, "pmath_g6b_point_chengshu_calc", "成数的计算：增产几成就是原产量的(1+成数)，减产几成就是原产量的(1-成数)，单位“1”是原产量", 5, SUBJECT, 266002),
    (266025, "pmath_g6b_point_tax_mean", "纳税与税率的含义：应纳税额与各种收入的比率叫税率，依法纳税是公民的义务", 6, SUBJECT, 266002),
    (266026, "pmath_g6b_point_tax_calc", "应纳税额的计算：应纳税额=收入×税率，已知应纳税额和税率可反求收入", 7, SUBJECT, 266002),
    (266027, "pmath_g6b_point_interest_parts", "储蓄的相关概念：存入银行的钱叫本金，取款时银行多付的钱叫利息，利息与本金的比率叫利率", 8, SUBJECT, 266002),
    (266028, "pmath_g6b_point_interest_formula", "利息的计算公式：利息=本金×利率×时间，计算时利率与时间单位要一致，本息合计=本金+利息", 9, SUBJECT, 266002),
    (266029, "pmath_g6b_point_interest_unit", "年利率与月利率的换算：年利率=月利率×12，存期按月计算时要用月利率，到期取回的钱包括本金和利息", 10, SUBJECT, 266002),
    (266030, "pmath_g6b_point_shopping_plan", "购物方案比较：分别算出打折、满减、买赠等方案下的实际花费，再比较优劣，注意比较的是最终付款额", 11, SUBJECT, 266002),
    (266031, "pmath_g6b_point_percent2_unit1", "百分数（二）中的单位“1”：折扣、成数、税率、利率问题的单位“1”各不相同，解题前必须找准基准量", 12, SUBJECT, 266002),

    # 第三单元 圆柱与圆锥
    (266035, "pmath_g6b_point_cylinder_feature", "圆柱的特征：上下两个底面是完全相同的圆，侧面是一个曲面，两个底面之间的距离叫高，圆柱有无数条高", 1, SUBJECT, 266003),
    (266036, "pmath_g6b_point_cylinder_net", "圆柱的侧面展开图：沿高剪开展开是长方形，长等于底面周长，宽等于圆柱的高；斜剪展开则是平行四边形", 2, SUBJECT, 266003),
    (266037, "pmath_g6b_point_cylinder_lateral", "圆柱的侧面积：S侧=Ch=πdh=2πrh，计算时先统一单位再代入公式", 3, SUBJECT, 266003),
    (266038, "pmath_g6b_point_cylinder_surface", "圆柱的表面积：S表=S侧+2S底=2πrh+2πr²，注意根据实际情况判断需要计算几个底面", 4, SUBJECT, 266003),
    (266039, "pmath_g6b_point_cylinder_surface_apply", "圆柱表面积的实际应用：无盖水桶只算一个底面，通风管只算侧面积，压路机滚筒只算侧面积", 5, SUBJECT, 266003),
    (266040, "pmath_g6b_point_cylinder_volume_derive", "圆柱体积公式的推导：把圆柱沿底面直径等分后拼成近似长方体，底面积相当于长方体底面积，高不变", 6, SUBJECT, 266003),
    (266041, "pmath_g6b_point_cylinder_volume_formula", "圆柱的体积公式：V=Sh=πr²h，已知底面周长时先求半径再求体积", 7, SUBJECT, 266003),
    (266042, "pmath_g6b_point_cylinder_capacity", "圆柱的容积与排水法：容器容积按内壁尺寸计算，不规则物体体积可用排水法转化为圆柱体积求解", 8, SUBJECT, 266003),
    (266043, "pmath_g6b_point_cone_feature", "圆锥的特征：底面是一个圆，侧面是曲面，从顶点到底面圆心的距离叫高，圆锥只有一条高", 9, SUBJECT, 266003),
    (266044, "pmath_g6b_point_cone_volume_formula", "圆锥的体积公式：V=1/3Sh=1/3πr²h，公式中的1/3不能遗漏", 10, SUBJECT, 266003),
    (266045, "pmath_g6b_point_cone_cylinder_relation", "等底等高的圆柱与圆锥：圆锥体积是圆柱体积的1/3，圆柱体积是圆锥体积的3倍，此关系仅限等底等高", 11, SUBJECT, 266003),
    (266046, "pmath_g6b_point_solid_combined", "组合立体图形：圆柱与圆锥拼合时分别计算各部分体积再相加，容器内液体形状变化时抓住体积不变", 12, SUBJECT, 266003),
    (266047, "pmath_g6b_point_cylinder_cross_section", "圆柱的截面：平行于底面截得圆，沿底面直径纵截得长方形，截后表面积会增加两个长方形面", 13, SUBJECT, 266003),

    # 第四单元 比例
    (266050, "pmath_g6b_point_proportion_mean", "比例的意义：表示两个比相等的式子叫比例，判断两个比能否组成比例要看它们的比值是否相等", 1, SUBJECT, 266004),
    (266051, "pmath_g6b_point_proportion_terms", "比例的各部分名称：组成比例的四个数叫比例的项，两端的两项叫外项，中间的两项叫内项", 2, SUBJECT, 266004),
    (266052, "pmath_g6b_point_proportion_property", "比例的基本性质：在比例里两个外项的积等于两个内项的积，这是解比例和判断比例的依据", 3, SUBJECT, 266004),
    (266053, "pmath_g6b_point_solve_proportion", "解比例：依据比例的基本性质把比例转化成方程，求出未知项后代入原比例检验", 4, SUBJECT, 266004),
    (266054, "pmath_g6b_point_direct_mean", "正比例的意义：两种相关联的量，一种量变化另一种量也随着变化，且比值一定，这两种量成正比例关系", 5, SUBJECT, 266004),
    (266055, "pmath_g6b_point_inverse_mean", "反比例的意义：两种相关联的量，一种量变化另一种量也随着变化，且乘积一定，这两种量成反比例关系", 6, SUBJECT, 266004),
    (266056, "pmath_g6b_point_judge_direct_inverse", "正反比例的判断：先看两种量是否相关联，再看比值一定还是乘积一定，比值一定成正比例，乘积一定成反比例", 7, SUBJECT, 266004),
    (266057, "pmath_g6b_point_direct_graph", "正比例的图像：正比例关系的图像是一条经过原点的直线，从图像上可以读出对应的数值", 8, SUBJECT, 266004),
    (266058, "pmath_g6b_point_scale_mean", "比例尺的意义：图上距离与实际距离的比叫这幅图的比例尺，比例尺是一个比，不带单位", 9, SUBJECT, 266004),
    (266059, "pmath_g6b_point_scale_forms", "比例尺的三种形式：数值比例尺、线段比例尺和文字比例尺，三者可以相互转化", 10, SUBJECT, 266004),
    (266060, "pmath_g6b_point_scale_formula", "比例尺的基本关系：比例尺=图上距离÷实际距离，图上距离=实际距离×比例尺，实际距离=图上距离÷比例尺", 11, SUBJECT, 266004),
    (266061, "pmath_g6b_point_scale_apply", "比例尺的应用：计算时图上距离与实际距离的单位必须统一，缩小比例尺前项为1，放大比例尺后项为1", 12, SUBJECT, 266004),
    (266062, "pmath_g6b_point_enlarge_reduce", "图形的放大与缩小：按一定的比放大或缩小后，图形形状不变、大小改变，对应边的比相等", 13, SUBJECT, 266004),
    (266063, "pmath_g6b_point_draw_on_grid", "在方格纸上放大或缩小图形：先按比算出各对应边的长度，再依次描点连线，角度保持不变", 14, SUBJECT, 266004),
    (266064, "pmath_g6b_point_direct_apply", "用正比例解决问题：先判断两种量成正比例，再设未知数列出比例式，解比例后检验", 15, SUBJECT, 266004),
    (266065, "pmath_g6b_point_inverse_apply", "用反比例解决问题：先判断两种量成反比例，再根据乘积相等列方程，注意总量保持不变", 16, SUBJECT, 266004),
    (266066, "pmath_g6b_point_proportion_mixed", "比例综合应用：工程、行程、配料等问题中先辨析正反比例，再选择列比例式或列方程求解", 17, SUBJECT, 266004),
    (266067, "pmath_g6b_point_scale_area_ratio", "比例尺与面积变化：长度按比放大或缩小后，面积按对应比的平方变化，不能直接用长度比代替面积比", 18, SUBJECT, 266004),
    (266068, "pmath_g6b_point_ratio_link", "比、比例与分数除法的联系：比是两数相除，比例是两个比相等，三者可以互相转化并统一用方程解决", 19, SUBJECT, 266004),

    # 第五单元 数学广角——鸽巢问题
    (266070, "pmath_g6b_point_pigeonhole_basic", "鸽巢原理的基本形式：把m个物体放进n个抽屉（m>n），总有一个抽屉里至少放进2个物体", 1, SUBJECT, 266005),
    (266071, "pmath_g6b_point_pigeonhole_general", "鸽巢原理的推广：把m个物体放进n个抽屉，总有一个抽屉至少放进m÷n的商加1个物体（有余数时）", 2, SUBJECT, 266005),
    (266072, "pmath_g6b_point_pigeonhole_apply", "鸽巢原理的应用：摸球、生日、颜色、书籍分类等问题，先确定“抽屉”与“物体”再套用结论", 3, SUBJECT, 266005),
    (266073, "pmath_g6b_point_worst_case", "最不利原则与构造抽屉：求“至少取出几个才能保证……”时，先考虑最坏情况再多取1个，抽屉要按题意合理构造", 4, SUBJECT, 266005),

    # 第六单元 整理和复习
    (266075, "pmath_g6b_point_review_number", "数的认识复习：整数、小数、分数、百分数、负数的意义与互化，数位顺序表与大小比较", 1, SUBJECT, 266006),
    (266076, "pmath_g6b_point_review_operation", "数的运算复习：四则运算的意义与法则、运算定律与简便计算、估算与验算", 2, SUBJECT, 266006),
    (266077, "pmath_g6b_point_review_equation_ratio", "式与方程、比和比例复习：用字母表示数、解方程、比的意义与基本性质、正反比例与比例尺", 3, SUBJECT, 266006),
    (266078, "pmath_g6b_point_review_quantity_geometry", "常见的量与图形测量复习：长度、面积、体积、质量、时间单位及换算，平面与立体图形的周长、面积、体积公式", 4, SUBJECT, 266006),
    (266079, "pmath_g6b_point_review_position_motion", "图形的位置与运动复习：用数对确定位置、用方向和距离描述位置，平移、旋转、轴对称与放大缩小", 5, SUBJECT, 266006),
    (266080, "pmath_g6b_point_review_statistics", "统计与概率复习：条形、折线、扇形统计图的特点与选择，平均数的意义，简单事件可能性的大小", 6, SUBJECT, 266006),
    (266081, "pmath_g6b_point_review_thinking", "数学思考复习：找规律、简单推理、数形结合与列表枚举，用数学思想方法分析和解决问题", 7, SUBJECT, 266006),
    (266082, "pmath_g6b_point_review_practice", "综合与实践复习：从实际问题中提取数量关系，设计解决方案并检验结果，经历完整的解决问题过程", 8, SUBJECT, 266006),
    (266083, "pmath_g6b_point_review_estimation", "估算与检验复习：根据实际情境选择合理的估算策略，用逆运算、代入法或常识检验答案的合理性", 9, SUBJECT, 266006),
)

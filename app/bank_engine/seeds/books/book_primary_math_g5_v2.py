"""人教版小学数学五年级下册：九个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G5 = 5
BOOK_ID = 1422

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学五年级下册",
    "pmath_g5b",
    22,
    "人民教育出版社",
    SUBJECT,
    G5,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 九个单元
    (142201, "第一单元 观察物体（三）", "pmath_g5b_u01", 1, BOOK_ID, None),
    (142203, "第二单元 因数与倍数", "pmath_g5b_u02", 2, BOOK_ID, None),
    (142207, "第三单元 长方体和正方体", "pmath_g5b_u03", 3, BOOK_ID, None),
    (142213, "第四单元 分数的意义和性质", "pmath_g5b_u04", 4, BOOK_ID, None),
    (142222, "第五单元 图形的运动（三）", "pmath_g5b_u05", 5, BOOK_ID, None),
    (142224, "第六单元 分数的加法和减法", "pmath_g5b_u06", 6, BOOK_ID, None),
    (142228, "第七单元 折线统计图", "pmath_g5b_u07", 7, BOOK_ID, None),
    (142231, "第八单元 数学广角——找次品", "pmath_g5b_u08", 8, BOOK_ID, None),
    (142233, "第九单元 总复习", "pmath_g5b_u09", 9, BOOK_ID, None),

    # 第一单元 观察物体（三）
    (142202, "根据视图摆搭积木", "pmath_g5b_l01", 1, BOOK_ID, 142201),

    # 第二单元 因数与倍数
    (142204, "因数和倍数", "pmath_g5b_l02", 1, BOOK_ID, 142203),
    (142205, "2、5、3的倍数的特征", "pmath_g5b_l03", 2, BOOK_ID, 142203),
    (142206, "质数和合数", "pmath_g5b_l04", 3, BOOK_ID, 142203),

    # 第三单元 长方体和正方体
    (142208, "长方体和正方体的认识", "pmath_g5b_l05", 1, BOOK_ID, 142207),
    (142209, "长方体和正方体的表面积", "pmath_g5b_l06", 2, BOOK_ID, 142207),
    (142210, "长方体和正方体的体积", "pmath_g5b_l07", 3, BOOK_ID, 142207),
    (142211, "体积单位间的进率", "pmath_g5b_l08", 4, BOOK_ID, 142207),
    (142212, "容积和容积单位", "pmath_g5b_l09", 5, BOOK_ID, 142207),

    # 第四单元 分数的意义和性质
    (142214, "分数的意义", "pmath_g5b_l10", 1, BOOK_ID, 142213),
    (142215, "真分数和假分数", "pmath_g5b_l11", 2, BOOK_ID, 142213),
    (142216, "分数的基本性质", "pmath_g5b_l12", 3, BOOK_ID, 142213),
    (142217, "最大公因数", "pmath_g5b_l13", 4, BOOK_ID, 142213),
    (142218, "约分", "pmath_g5b_l14", 5, BOOK_ID, 142213),
    (142219, "最小公倍数", "pmath_g5b_l15", 6, BOOK_ID, 142213),
    (142220, "通分", "pmath_g5b_l16", 7, BOOK_ID, 142213),
    (142221, "分数和小数的互化", "pmath_g5b_l17", 8, BOOK_ID, 142213),

    # 第五单元 图形的运动（三）
    (142223, "旋转", "pmath_g5b_l18", 1, BOOK_ID, 142222),

    # 第六单元 分数的加法和减法
    (142225, "同分母分数加减法", "pmath_g5b_l19", 1, BOOK_ID, 142224),
    (142226, "异分母分数加减法", "pmath_g5b_l20", 2, BOOK_ID, 142224),
    (142227, "分数加减混合运算", "pmath_g5b_l21", 3, BOOK_ID, 142224),

    # 第七单元 折线统计图
    (142229, "单式折线统计图", "pmath_g5b_l22", 1, BOOK_ID, 142228),
    (142230, "复式折线统计图", "pmath_g5b_l23", 2, BOOK_ID, 142228),

    # 第八单元 数学广角——找次品
    (142232, "找次品", "pmath_g5b_l24", 1, BOOK_ID, 142231),

    # 第九单元 总复习
    (142234, "总复习", "pmath_g5b_l25", 1, BOOK_ID, 142233),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 264001-264009 为册域层，264010-264094 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (264001, "pmath_g5b_domain_u01", "小学数学五下·第一单元 观察物体（三）", 1, SUBJECT, G5, None),
    (264002, "pmath_g5b_domain_u02", "小学数学五下·第二单元 因数与倍数", 2, SUBJECT, G5, None),
    (264003, "pmath_g5b_domain_u03", "小学数学五下·第三单元 长方体和正方体", 3, SUBJECT, G5, None),
    (264004, "pmath_g5b_domain_u04", "小学数学五下·第四单元 分数的意义和性质", 4, SUBJECT, G5, None),
    (264005, "pmath_g5b_domain_u05", "小学数学五下·第五单元 图形的运动（三）", 5, SUBJECT, G5, None),
    (264006, "pmath_g5b_domain_u06", "小学数学五下·第六单元 分数的加法和减法", 6, SUBJECT, G5, None),
    (264007, "pmath_g5b_domain_u07", "小学数学五下·第七单元 折线统计图", 7, SUBJECT, G5, None),
    (264008, "pmath_g5b_domain_u08", "小学数学五下·第八单元 数学广角——找次品", 8, SUBJECT, G5, None),
    (264009, "pmath_g5b_domain_u09", "小学数学五下·第九单元 总复习", 9, SUBJECT, G5, None),

    # 第一单元 观察物体（三）
    (264010, "pmath_g5b_point_view_three_dirs", "从三个方向观察物体：正面看宽与高、上面看宽与深、左面看深与高，同一物体不同方向形状不同", 1, SUBJECT, G5, 264001),
    (264011, "pmath_g5b_point_view_guess_many", "根据一个方向看到的图形摆积木：符合该视图的摆法不唯一，可能需增加或减少小正方体", 2, SUBJECT, G5, 264001),
    (264012, "pmath_g5b_point_view_restore_unique", "根据从三个方向看到的图形还原：先定底层行列数，再按其它视图确定各位置层数，搭法一般唯一", 3, SUBJECT, G5, 264001),
    (264013, "pmath_g5b_point_view_pitfall", "观察物体的易错点：被遮挡的小正方体也要计数，注意“最多”与“最少”两种摆法", 4, SUBJECT, G5, 264001),

    # 第二单元 因数与倍数
    (264014, "pmath_g5b_point_factor_multiple_mean", "因数与倍数的意义：若a×b=c，则a与b是c的因数，c是a与b的倍数，因数倍数相互依存不能单独说", 1, SUBJECT, G5, 264002),
    (264015, "pmath_g5b_point_find_factor", "找一个数的因数：用乘法成对找或用除法依次除，从1开始一对一对地找不重不漏", 2, SUBJECT, G5, 264002),
    (264016, "pmath_g5b_point_factor_feature", "一个数的因数的特征：最小的因数是1，最大的因数是它本身，因数的个数是有限的", 3, SUBJECT, G5, 264002),
    (264017, "pmath_g5b_point_find_multiple", "找一个数的倍数：用这个数依次乘1、2、3……也可用这个数依次累加", 4, SUBJECT, G5, 264002),
    (264018, "pmath_g5b_point_multiple_feature", "一个数的倍数的特征：最小的倍数是它本身，没有最大的倍数，倍数的个数是无限的", 5, SUBJECT, G5, 264002),
    (264019, "pmath_g5b_point_feature_235", "2、5、3的倍数的特征：先看个位判断2和5的倍数，再看各位数字之和判断3的倍数", 6, SUBJECT, G5, 264002),
    (264020, "pmath_g5b_point_feature_2", "2的倍数特征：个位上是0、2、4、6、8的数都是2的倍数，如12、30、46", 1, SUBJECT, G5, 264019),
    (264021, "pmath_g5b_point_feature_5", "5的倍数特征：个位上是0或5的数都是5的倍数，如15、20、35", 2, SUBJECT, G5, 264019),
    (264022, "pmath_g5b_point_feature_3", "3的倍数特征：一个数各位上数字的和是3的倍数，这个数就是3的倍数，如123、105", 3, SUBJECT, G5, 264019),
    (264023, "pmath_g5b_point_odd_even", "奇数与偶数：是2的倍数的数叫偶数（0也是偶数），不是2的倍数的数叫奇数", 7, SUBJECT, G5, 264002),
    (264024, "pmath_g5b_point_odd_even_rule", "奇数偶数的运算性质：奇+奇=偶，偶+偶=偶，奇+偶=奇，奇×奇=奇，只要有一个偶因数积就是偶数", 8, SUBJECT, G5, 264002),
    (264025, "pmath_g5b_point_prime_composite", "质数与合数：只有1和它本身两个因数的数叫质数，除1和它本身外还有别的因数的数叫合数", 9, SUBJECT, G5, 264002),
    (264026, "pmath_g5b_point_prime_judge", "判断质数的方法：用2、3、5、7等质数依次试除，除到商比除数小为止，能整除就是合数", 10, SUBJECT, G5, 264002),
    (264027, "pmath_g5b_point_prime_table", "20以内的质数与1的特殊性：20以内质数为2、3、5、7、11、13、17、19，1既不是质数也不是合数", 11, SUBJECT, G5, 264002),

    # 第三单元 长方体和正方体
    (264028, "pmath_g5b_point_cuboid_feature", "长方体的特征：6个面都是长方形（特殊情况有两个相对的面是正方形），相对的面完全相同，有12条棱、8个顶点", 1, SUBJECT, G5, 264003),
    (264029, "pmath_g5b_point_cube_feature", "正方体的特征：6个面都是完全相同的正方形，12条棱长度全相等，8个顶点，是特殊的长方体", 2, SUBJECT, G5, 264003),
    (264030, "pmath_g5b_point_length_width_height", "长、宽、高的意义：相交于一个顶点的三条棱的长度分别叫长方体的长、宽、高，正方体三者相等", 3, SUBJECT, G5, 264003),
    (264031, "pmath_g5b_point_edge_sum", "棱长总和：长方体棱长总和=（长+宽+高）×4，正方体棱长总和=棱长×12，可用于求框架用料", 4, SUBJECT, G5, 264003),
    (264032, "pmath_g5b_point_net", "长方体与正方体的展开图：沿棱剪开得到平面图形，展开图由6个面组成，可判断相对面与折叠还原", 5, SUBJECT, G5, 264003),
    (264033, "pmath_g5b_point_surface_meaning", "表面积的意义：长方体或正方体6个面的总面积叫它的表面积", 6, SUBJECT, G5, 264003),
    (264034, "pmath_g5b_point_cuboid_surface", "长方体的表面积：S=2(ab+ah+bh)，先求出三个不同面的面积再乘2，注意长宽高单位统一", 7, SUBJECT, G5, 264003),
    (264035, "pmath_g5b_point_cube_surface", "正方体的表面积：S=6a²，先求一个面的面积再乘6", 8, SUBJECT, G5, 264003),
    (264036, "pmath_g5b_point_surface_apply", "表面积的实际应用：无盖水箱少算一个上面，通风管只算侧面4个面，贴瓷砖要扣除门窗面积", 9, SUBJECT, G5, 264003),
    (264037, "pmath_g5b_point_volume_meaning", "体积的意义：物体所占空间的大小叫物体的体积，体积大的物体占的空间大", 10, SUBJECT, G5, 264003),
    (264038, "pmath_g5b_point_cuboid_volume", "长方体的体积：V=长×宽×高，即V=abh，已知体积和底面积可求高h=V÷S", 11, SUBJECT, G5, 264003),
    (264039, "pmath_g5b_point_cube_volume", "正方体的体积：V=棱长×棱长×棱长，即V=a³，a³表示3个a相乘", 12, SUBJECT, G5, 264003),
    (264040, "pmath_g5b_point_volume_common", "统一的体积公式：长方体（正方体）体积=底面积×高，V=Sh，对柱状直立体同样适用", 13, SUBJECT, G5, 264003),
    (264041, "pmath_g5b_point_volume_unit", "体积单位：常用的体积单位有立方厘米、立方分米、立方米，棱长1厘米的正方体体积是1立方厘米", 14, SUBJECT, G5, 264003),
    (264042, "pmath_g5b_point_volume_rate", "体积单位间的进率：1立方分米=1000立方厘米，1立方米=1000立方分米，相邻两级进率是1000", 15, SUBJECT, G5, 264003),
    (264043, "pmath_g5b_point_volume_capacity_convert", "体积单位与容积单位的换算：1升=1立方分米，1毫升=1立方厘米，1升=1000毫升", 16, SUBJECT, G5, 264003),
    (264044, "pmath_g5b_point_capacity_meaning", "容积的意义与单位：容器所能容纳物体的体积叫容积，常用升和毫升，容器容积要从里面量长宽高", 17, SUBJECT, G5, 264003),
    (264045, "pmath_g5b_point_capacity_compute", "容积的计算与排水法：规则容器用V=abh计算，不规则物体用排水法测上升水的体积", 18, SUBJECT, G5, 264003),
    (264046, "pmath_g5b_point_cuboid_pitfall", "长正方体的易错点：表面积用面积单位、体积用体积单位，切割或拼接后表面积变化而体积不变", 19, SUBJECT, G5, 264003),

    # 第四单元 分数的意义和性质
    (264047, "pmath_g5b_point_fraction_mean", "分数的意义：把单位“1”平均分成若干份，表示这样一份或几份的数叫分数，单位“1”可以是一个物体或一个整体", 1, SUBJECT, G5, 264004),
    (264048, "pmath_g5b_point_fraction_unit", "分数单位：把单位“1”平均分成若干份，表示其中1份的数叫分数单位，如3/5的分数单位是1/5", 2, SUBJECT, G5, 264004),
    (264049, "pmath_g5b_point_fraction_div", "分数与除法的关系：a÷b=a/b（b≠0），被除数相当于分子、除数相当于分母，商不能整除时用分数表示", 3, SUBJECT, G5, 264004),
    (264050, "pmath_g5b_point_share_fraction", "求一个数是另一个数的几分之几：用除法计算，结果写成分数并约成最简，如3÷5=3/5", 4, SUBJECT, G5, 264004),
    (264051, "pmath_g5b_point_proper_fraction", "真分数的意义：分子比分母小的分数叫真分数，真分数都小于1", 5, SUBJECT, G5, 264004),
    (264052, "pmath_g5b_point_improper_fraction", "假分数的意义：分子比分母大或分子与分母相等的分数叫假分数，假分数大于或等于1", 6, SUBJECT, G5, 264004),
    (264053, "pmath_g5b_point_mixed_convert", "带分数与假分数的互化：假分数化带分数用分子除以分母商作整数部分余数作分子，带分数化假分数用整数×分母+分子", 7, SUBJECT, G5, 264004),
    (264054, "pmath_g5b_point_fraction_property", "分数的基本性质：分数的分子和分母同时乘或除以相同的数（0除外），分数的大小不变", 8, SUBJECT, G5, 264004),
    (264055, "pmath_g5b_point_common_factor", "公因数与最大公因数：几个数公有的因数叫公因数，其中最大的一个叫最大公因数", 9, SUBJECT, G5, 264004),
    (264056, "pmath_g5b_point_find_max_factor", "求最大公因数的方法：列举法、分解法或短除法，成倍数关系时小数即最大公因数", 10, SUBJECT, G5, 264004),
    (264057, "pmath_g5b_point_coprime", "互质数：公因数只有1的两个数叫互质数，互质的两个数最大公因数是1，但两个数可以都是合数", 11, SUBJECT, G5, 264004),
    (264058, "pmath_g5b_point_reduce", "约分的意义与方法：把一个分数化成和它相等但分子分母都比较小的分数叫约分，用分子分母的公因数去除", 12, SUBJECT, G5, 264004),
    (264059, "pmath_g5b_point_simplest", "最简分数：分子和分母只有公因数1的分数叫最简分数，约分要一直约到最简为止", 13, SUBJECT, G5, 264004),
    (264060, "pmath_g5b_point_common_multiple", "公倍数与最小公倍数：几个数公有的倍数叫公倍数，其中最小的一个叫最小公倍数，公倍数个数无限", 14, SUBJECT, G5, 264004),
    (264061, "pmath_g5b_point_find_min_multiple", "求最小公倍数的方法：列举法或短除法，成倍数关系时大数即最小公倍数，互质时两数之积即最小公倍数", 15, SUBJECT, G5, 264004),
    (264062, "pmath_g5b_point_common_denominator", "通分的意义与方法：把异分母分数化成和原来相等且分母相同的分数叫通分，通常用最小公倍数作公分母", 16, SUBJECT, G5, 264004),
    (264063, "pmath_g5b_point_fraction_compare", "分数大小比较：同分母比分子、同分子比分母，异分母先通分再比较，也可化成小数比较", 17, SUBJECT, G5, 264004),
    (264064, "pmath_g5b_point_fraction_decimal_convert", "分数和小数的互化：依据分数与除法的关系及小数的意义互相改写，互化前要化成最简分数", 18, SUBJECT, G5, 264004),
    (264065, "pmath_g5b_point_fraction_to_decimal", "分数化成小数：用分子除以分母，除不尽时按需要保留小数位数，如3/4=0.75", 1, SUBJECT, G5, 264064),
    (264066, "pmath_g5b_point_decimal_to_fraction", "小数化成分数：把小数写成分母是10、100、1000的分数再约分，如0.35=35/100=7/20", 2, SUBJECT, G5, 264064),
    (264067, "pmath_g5b_point_finite_decimal", "判断能否化成有限小数：最简分数的分母只含质因数2和5时能化成有限小数，否则是无限小数", 3, SUBJECT, G5, 264064),

    # 第五单元 图形的运动（三）
    (264068, "pmath_g5b_point_rotation_three", "旋转的三要素：旋转中心、旋转方向（顺时针或逆时针）和旋转角度，三者缺一不可", 1, SUBJECT, G5, 264005),
    (264069, "pmath_g5b_point_rotation_feature", "旋转的特征：图形形状大小不变、位置改变，对应点到旋转中心的距离相等，对应线段夹角等于旋转角", 2, SUBJECT, G5, 264005),
    (264070, "pmath_g5b_point_rotation_draw", "在方格纸上画旋转后的图形：先确定旋转中心，再把关键点按方向和角度找到对应点，最后顺次连接", 3, SUBJECT, G5, 264005),
    (264071, "pmath_g5b_point_rotation_combine", "平移、旋转与轴对称的综合：图形可由多种运动得到，描述时要按顺序说清每种运动的方向和格数或角度", 4, SUBJECT, G5, 264005),
    (264072, "pmath_g5b_point_rotation_pitfall", "旋转的易错点：绕图形内一点旋转与绕图形外一点旋转结果不同，逆时针90°与顺时针270°等效", 5, SUBJECT, G5, 264005),

    # 第六单元 分数的加法和减法
    (264073, "pmath_g5b_point_same_den_add", "同分母分数加减法：分母不变，分子相加减，最后结果能约分的要约成最简分数", 1, SUBJECT, G5, 264006),
    (264074, "pmath_g5b_point_result_simplest", "分数加减结果的处理：结果要化成最简分数，是假分数时通常化成带分数，得数为1时可写作1", 2, SUBJECT, G5, 264006),
    (264075, "pmath_g5b_point_diff_den_add", "异分母分数加减法：先通分化成同分母分数，再按同分母分数加减法计算", 3, SUBJECT, G5, 264006),
    (264076, "pmath_g5b_point_mixed_order", "分数加减混合运算顺序：没有括号的从左往右依次计算，有括号的先算括号里面的", 4, SUBJECT, G5, 264006),
    (264077, "pmath_g5b_point_add_laws", "加法运算定律推广到分数：加法交换律、结合律对分数加法同样适用，可用字母表示", 5, SUBJECT, G5, 264006),
    (264078, "pmath_g5b_point_simplify_add", "分数加减的简便计算：把和为1的分数先结合，同分母分数先相加减，括号前是减号去括号要变号", 6, SUBJECT, G5, 264006),
    (264079, "pmath_g5b_point_fraction_solve", "分数加减解决问题：先确定单位“1”，总量可记为1，用加减法求剩余部分或比较多少", 7, SUBJECT, G5, 264006),

    # 第七单元 折线统计图
    (264080, "pmath_g5b_point_line_chart_feature", "折线统计图的特点：既能表示数量的多少，又能清楚地反映数量的增减变化趋势", 1, SUBJECT, G5, 264007),
    (264081, "pmath_g5b_point_single_line_chart", "单式折线统计图：先描点再顺次连线，横轴表示时间等项目，纵轴表示数量，注意单位与刻度", 2, SUBJECT, G5, 264007),
    (264082, "pmath_g5b_point_multi_line_chart", "复式折线统计图：用不同颜色或线型区分两组数据，必须标明图例，便于比较两组数据的变化", 3, SUBJECT, G5, 264007),
    (264083, "pmath_g5b_point_trend_predict", "折线统计图的分析与预测：看线段的陡缓判断变化快慢，根据变化趋势对后续数据作出合理预测", 4, SUBJECT, G5, 264007),
    (264084, "pmath_g5b_point_chart_compare", "折线统计图与条形统计图的区别：条形图便于比较数量的多少，折线图便于反映数量的变化趋势", 5, SUBJECT, G5, 264007),

    # 第八单元 数学广角——找次品
    (264085, "pmath_g5b_point_find_defect_basic", "找次品的基本思路：用天平称量，平衡说明次品在未称的那组，不平衡说明次品在较重或较轻的一组", 1, SUBJECT, G5, 264008),
    (264086, "pmath_g5b_point_find_defect_small", "从少量物品中找次品：3个物品称1次可找出，5个物品至少称2次，要写出称量步骤", 2, SUBJECT, G5, 264008),
    (264087, "pmath_g5b_point_find_defect_best", "找次品的最优策略：把待测物品尽量平均分成3份，不能平均分时使多的一份与少的一份相差1", 3, SUBJECT, G5, 264008),
    (264088, "pmath_g5b_point_find_defect_rule", "找次品的规律：称n次最多能从3的n次方个物品中找出1个次品，如称2次最多测9个", 4, SUBJECT, G5, 264008),

    # 第九单元 总复习
    (264089, "pmath_g5b_point_review_factor", "因数与倍数总复习：因数倍数的意义与求法、2、5、3的倍数特征、奇数偶数与质数合数的分类", 1, SUBJECT, G5, 264009),
    (264090, "pmath_g5b_point_review_cuboid", "长方体和正方体总复习：特征、棱长总和、表面积与体积公式、体积单位进率及容积与排水法", 2, SUBJECT, G5, 264009),
    (264091, "pmath_g5b_point_review_fraction_mean", "分数的意义和性质总复习：单位“1”与分数单位、真假带分数、基本性质、约分通分与分数小数互化", 3, SUBJECT, G5, 264009),
    (264092, "pmath_g5b_point_review_fraction_calc", "分数加减法总复习：同分母与异分母加减、混合运算顺序、运算定律与简便计算及实际问题", 4, SUBJECT, G5, 264009),
    (264093, "pmath_g5b_point_review_motion_chart", "图形运动与统计总复习：旋转三要素与画旋转图形、单式与复式折线统计图的绘制和趋势分析", 5, SUBJECT, G5, 264009),
    (264094, "pmath_g5b_point_review_defect", "找次品与综合应用总复习：天平称量的推理方法、平均分3份的最优策略与称量次数规律", 6, SUBJECT, G5, 264009),
)

"""人教版小学数学六年级上册：九个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G6 = 6
BOOK_ID = 1423

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学六年级上册",
    "pmath_g6a",
    23,
    "人民教育出版社",
    SUBJECT,
    G6,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 九个单元
    (142301, "第一单元 分数乘法", "pmath_g6a_u01", 1, BOOK_ID, None),
    (142310, "第二单元 位置与方向（二）", "pmath_g6a_u02", 2, BOOK_ID, None),
    (142320, "第三单元 分数除法", "pmath_g6a_u03", 3, BOOK_ID, None),
    (142330, "第四单元 比", "pmath_g6a_u04", 4, BOOK_ID, None),
    (142340, "第五单元 圆", "pmath_g6a_u05", 5, BOOK_ID, None),
    (142350, "第六单元 百分数（一）", "pmath_g6a_u06", 6, BOOK_ID, None),
    (142360, "第七单元 扇形统计图", "pmath_g6a_u07", 7, BOOK_ID, None),
    (142370, "第八单元 数学广角——数与形", "pmath_g6a_u08", 8, BOOK_ID, None),
    (142380, "第九单元 总复习", "pmath_g6a_u09", 9, BOOK_ID, None),

    # 第一单元 分数乘法
    (142302, "分数乘整数", "pmath_g6a_l01", 1, BOOK_ID, 142301),
    (142303, "分数乘分数", "pmath_g6a_l02", 2, BOOK_ID, 142301),
    (142304, "分数乘法运算定律", "pmath_g6a_l03", 3, BOOK_ID, 142301),
    (142305, "解决问题", "pmath_g6a_l04", 4, BOOK_ID, 142301),
    (142306, "倒数的认识", "pmath_g6a_l05", 5, BOOK_ID, 142301),

    # 第二单元 位置与方向（二）
    (142311, "描述物体的位置", "pmath_g6a_l06", 1, BOOK_ID, 142310),
    (142312, "标出物体的位置", "pmath_g6a_l07", 2, BOOK_ID, 142310),
    (142313, "路线图", "pmath_g6a_l08", 3, BOOK_ID, 142310),

    # 第三单元 分数除法
    (142321, "分数除法", "pmath_g6a_l09", 1, BOOK_ID, 142320),
    (142322, "解决问题", "pmath_g6a_l10", 2, BOOK_ID, 142320),
    (142323, "整理和复习", "pmath_g6a_l11", 3, BOOK_ID, 142320),

    # 第四单元 比
    (142331, "比的意义", "pmath_g6a_l12", 1, BOOK_ID, 142330),
    (142332, "比的基本性质", "pmath_g6a_l13", 2, BOOK_ID, 142330),
    (142333, "比的应用", "pmath_g6a_l14", 3, BOOK_ID, 142330),

    # 第五单元 圆
    (142341, "圆的认识", "pmath_g6a_l15", 1, BOOK_ID, 142340),
    (142342, "圆的周长", "pmath_g6a_l16", 2, BOOK_ID, 142340),
    (142343, "圆的面积", "pmath_g6a_l17", 3, BOOK_ID, 142340),
    (142344, "扇形", "pmath_g6a_l18", 4, BOOK_ID, 142340),

    # 第六单元 百分数（一）
    (142351, "百分数的意义和写法", "pmath_g6a_l19", 1, BOOK_ID, 142350),
    (142352, "百分数和分数、小数的互化", "pmath_g6a_l20", 2, BOOK_ID, 142350),
    (142353, "用百分数解决问题", "pmath_g6a_l21", 3, BOOK_ID, 142350),

    # 第七单元 扇形统计图
    (142361, "认识扇形统计图", "pmath_g6a_l22", 1, BOOK_ID, 142360),

    # 第八单元 数学广角——数与形
    (142371, "数与形", "pmath_g6a_l23", 1, BOOK_ID, 142370),

    # 第九单元 总复习
    (142381, "总复习", "pmath_g6a_l24", 1, BOOK_ID, 142380),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 265001-265009 为册域层，265010-265080 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (265001, "pmath_g6a_domain_u01", "小学数学六上·第一单元 分数乘法", 1, SUBJECT, G6, None),
    (265002, "pmath_g6a_domain_u02", "小学数学六上·第二单元 位置与方向（二）", 2, SUBJECT, G6, None),
    (265003, "pmath_g6a_domain_u03", "小学数学六上·第三单元 分数除法", 3, SUBJECT, G6, None),
    (265004, "pmath_g6a_domain_u04", "小学数学六上·第四单元 比", 4, SUBJECT, G6, None),
    (265005, "pmath_g6a_domain_u05", "小学数学六上·第五单元 圆", 5, SUBJECT, G6, None),
    (265006, "pmath_g6a_domain_u06", "小学数学六上·第六单元 百分数（一）", 6, SUBJECT, G6, None),
    (265007, "pmath_g6a_domain_u07", "小学数学六上·第七单元 扇形统计图", 7, SUBJECT, G6, None),
    (265008, "pmath_g6a_domain_u08", "小学数学六上·第八单元 数学广角——数与形", 8, SUBJECT, G6, None),
    (265009, "pmath_g6a_domain_u09", "小学数学六上·第九单元 总复习", 9, SUBJECT, G6, None),

    # 第一单元 分数乘法
    (265010, "pmath_g6a_point_mul_int_mean", "分数乘整数的意义与算理：表示求几个相同加数的和的简便运算，如2/9×3表示3个2/9相加", 1, SUBJECT, G6, 265001),
    (265011, "pmath_g6a_point_mul_int_method", "分数乘整数的计算方法：用分子与整数相乘的积作分子，分母不变，能约分的先约分", 2, SUBJECT, G6, 265001),
    (265012, "pmath_g6a_point_num_times_fraction", "一个数乘分数的意义：表示求这个数的几分之几是多少，如20×3/4表示求20的3/4是多少", 3, SUBJECT, G6, 265001),
    (265013, "pmath_g6a_point_mul_fraction_method", "分数乘分数的计算方法：分子相乘的积作分子，分母相乘的积作分母，结果化成最简分数", 4, SUBJECT, G6, 265001),
    (265014, "pmath_g6a_point_mul_reduce", "分数乘法中的约分：先看分子与分母的公因数，交叉约分后再乘，避免大数运算出错", 5, SUBJECT, G6, 265001),
    (265015, "pmath_g6a_point_mul_laws", "分数乘法的运算定律：整数乘法的交换律、结合律、分配律对分数乘法同样适用", 6, SUBJECT, G6, 265001),
    (265016, "pmath_g6a_point_mul_simplify", "分数乘法的简便计算：用分配律提取公因数，或把接近1的数拆成1与几分之一的和再计算", 7, SUBJECT, G6, 265001),
    (265017, "pmath_g6a_point_find_part", "求一个数的几分之几是多少：用单位“1”的量乘对应分率，找准单位“1”和分率是关键", 8, SUBJECT, G6, 265001),
    (265018, "pmath_g6a_point_find_part_chain", "连续求一个数的几分之几：分步确定每一步的单位“1”再依次相乘，注意单位“1”会变化", 9, SUBJECT, G6, 265001),
    (265019, "pmath_g6a_point_reciprocal_mean", "倒数的意义：乘积是1的两个数互为倒数，倒数表示两个数之间的关系，不能单独说某数是倒数", 10, SUBJECT, G6, 265001),
    (265020, "pmath_g6a_point_reciprocal_method", "求倒数的方法：分数交换分子分母，整数写成几分之一，1的倒数是1，0没有倒数", 11, SUBJECT, G6, 265001),
    (265021, "pmath_g6a_point_mul_add_diff", "分数乘法与加法的区别：乘法先约分再乘分子分母，加法必须先通分，两种运算不能混淆", 12, SUBJECT, G6, 265001),
    (265022, "pmath_g6a_point_mul_rate_match", "分数乘法中的量率对应：已知总量与分率求部分量用乘法，注意分率不带单位，要与具体数量区分", 13, SUBJECT, G6, 265001),

    # 第二单元 位置与方向（二）
    (265023, "pmath_g6a_point_position_elements", "用方向和距离确定位置：需要观测点、方向和距离三个要素，缺少任何一个都无法唯一确定位置", 1, SUBJECT, G6, 265002),
    (265024, "pmath_g6a_point_position_describe", "描述物体位置的方法：以观测点为中心，用北偏东（西）、南偏东（西）加角度和距离描述，角度从南北方向量起", 2, SUBJECT, G6, 265002),
    (265025, "pmath_g6a_point_position_draw", "根据描述标出物体位置：先定观测点画方向线，再用量角器量出角度，最后按比例尺截取距离标出点", 3, SUBJECT, G6, 265002),
    (265026, "pmath_g6a_point_route_map", "路线图的描述：路线分段描述，每到一处观测点就会改变，方向、角度和距离都要随之调整", 4, SUBJECT, G6, 265002),

    # 第三单元 分数除法
    (265027, "pmath_g6a_point_div_mean", "分数除法的意义：已知两个因数的积与其中一个因数，求另一个因数的运算，与整数除法意义一致", 1, SUBJECT, G6, 265003),
    (265028, "pmath_g6a_point_div_int", "分数除以整数：分数除以整数（0除外）等于分数乘这个整数的倒数", 2, SUBJECT, G6, 265003),
    (265029, "pmath_g6a_point_div_fraction", "一个数除以分数：一个数除以分数等于这个数乘分数的倒数，整数除以分数也按此法则计算", 3, SUBJECT, G6, 265003),
    (265030, "pmath_g6a_point_div_rule", "分数除法的计算法则：甲数除以乙数（0除外）等于甲数乘乙数的倒数，除法转化为乘法", 4, SUBJECT, G6, 265003),
    (265031, "pmath_g6a_point_find_whole", "已知一个数的几分之几是多少求这个数：用部分量除以对应分率，或设单位“1”为x列方程", 5, SUBJECT, G6, 265003),
    (265032, "pmath_g6a_point_div_mixed", "分数乘除混合运算：先把除法统一成乘法，再从左到右依次计算，能约分的先约分", 6, SUBJECT, G6, 265003),
    (265033, "pmath_g6a_point_work_problem", "工程问题：把工作总量看作单位“1”，工作效率是工作时间的倒数，合作时间=1÷工作效率之和", 7, SUBJECT, G6, 265003),
    (265034, "pmath_g6a_point_mul_div_compare", "分数乘除法的联系与区别：乘法由单位“1”求部分量，除法由部分量求单位“1”，二者互为逆运算", 8, SUBJECT, G6, 265003),
    (265035, "pmath_g6a_point_div_review", "分数除法整理和复习：梳理倒数、除法法则与实际问题，建立分数乘除法的互逆关系", 9, SUBJECT, G6, 265003),

    # 第四单元 比
    (265036, "pmath_g6a_point_ratio_mean", "比的意义：两个数相除又叫两个数的比，比表示两个量之间的倍比关系", 1, SUBJECT, G6, 265004),
    (265037, "pmath_g6a_point_ratio_parts", "比的各部分名称：比号前面的数叫前项，后面的数叫后项，前项除以后项的商叫比值", 2, SUBJECT, G6, 265004),
    (265038, "pmath_g6a_point_ratio_relation", "比与除法、分数的关系：a:b=a÷b=a/b（b≠0），后项、除数、分母都不能为0", 3, SUBJECT, G6, 265004),
    (265039, "pmath_g6a_point_ratio_property", "比的基本性质：比的前项和后项同时乘或除以相同的数（0除外），比值不变", 4, SUBJECT, G6, 265004),
    (265040, "pmath_g6a_point_ratio_simplify", "化简比：整数比用最大公因数去除，分数比乘分母的最小公倍数，小数比先化成整数比再化简", 5, SUBJECT, G6, 265004),
    (265041, "pmath_g6a_point_ratio_value_diff", "求比值与化简比的区别：求比值的结果是一个数，化简比的结果仍是一个最简整数比", 6, SUBJECT, G6, 265004),
    (265042, "pmath_g6a_point_ratio_allocate", "按比分配：先求总份数，再求每份对应的数量，最后按各部分份数分配总量", 7, SUBJECT, G6, 265004),
    (265043, "pmath_g6a_point_ratio_allocate_variant", "按比分配的变式：已知一部分量求总量或另一部分量，先用部分量除以它的份数求每份数", 8, SUBJECT, G6, 265004),
    (265044, "pmath_g6a_point_ratio_continue", "连比：三个量之间的比可以写成连比，如a:b:c，按比分配时总份数为各比之和", 9, SUBJECT, G6, 265004),

    # 第五单元 圆
    (265045, "pmath_g6a_point_circle_mean", "圆的认识：圆是平面上到定点距离等于定长的所有点组成的曲线图形，这个定点叫圆心", 1, SUBJECT, G6, 265005),
    (265046, "pmath_g6a_point_circle_parts", "圆心、半径和直径：圆心确定圆的位置，半径确定圆的大小，直径是通过圆心且两端都在圆上的线段", 2, SUBJECT, G6, 265005),
    (265047, "pmath_g6a_point_circle_feature", "圆的特征：同圆或等圆中所有半径相等、所有直径相等，直径是半径的2倍，即d=2r", 3, SUBJECT, G6, 265005),
    (265048, "pmath_g6a_point_circle_draw", "用圆规画圆：针尖固定在圆心，两脚间的距离等于半径，旋转一周画出圆", 4, SUBJECT, G6, 265005),
    (265049, "pmath_g6a_point_circle_symmetry", "圆的对称性：圆是轴对称图形，任何一条直径所在的直线都是它的对称轴，圆有无数条对称轴", 5, SUBJECT, G6, 265005),
    (265050, "pmath_g6a_point_circumference_mean", "圆周长的意义：围成圆的曲线的长度叫圆的周长", 6, SUBJECT, G6, 265005),
    (265051, "pmath_g6a_point_pi", "圆周率：圆的周长与直径的比值叫圆周率，用π表示，π≈3.14，是无限不循环小数", 7, SUBJECT, G6, 265005),
    (265052, "pmath_g6a_point_circumference_formula", "圆的周长公式：C=πd或C=2πr，已知半径或直径可直接求出圆的周长", 8, SUBJECT, G6, 265005),
    (265053, "pmath_g6a_point_semicircle_perimeter", "半圆的周长：半圆周长等于圆周长的一半加一条直径，即C半=πr+2r", 9, SUBJECT, G6, 265005),
    (265054, "pmath_g6a_point_circle_area_derive", "圆的面积公式推导：把圆平均分成若干等份拼成近似长方形，长相当于圆周长的一半，宽相当于半径", 10, SUBJECT, G6, 265005),
    (265055, "pmath_g6a_point_circle_area_formula", "圆的面积公式：S=πr²，已知直径先用d÷2求出半径，再代入公式计算", 11, SUBJECT, G6, 265005),
    (265056, "pmath_g6a_point_ring_area", "圆环的面积：S环=πR²-πr²=π(R²-r²)，其中R为外圆半径，r为内圆半径", 12, SUBJECT, G6, 265005),
    (265057, "pmath_g6a_point_composite_circle", "组合图形中的圆：用分割、添补、割补等方法把组合图形转化为规则图形，再求面积或周长", 13, SUBJECT, G6, 265005),
    (265058, "pmath_g6a_point_sector", "扇形和圆心角：圆上两点之间的部分叫弧，顶点在圆心的角叫圆心角，扇形由一条弧和经过弧两端的两条半径围成", 14, SUBJECT, G6, 265005),

    # 第六单元 百分数（一）
    (265059, "pmath_g6a_point_percent_mean", "百分数的意义：表示一个数是另一个数的百分之几的数叫百分数，也叫百分率或百分比", 1, SUBJECT, G6, 265006),
    (265060, "pmath_g6a_point_percent_read", "百分数的读法和写法：先写数字再写百分号，读作百分之几，百分号不能省略或写错", 2, SUBJECT, G6, 265006),
    (265061, "pmath_g6a_point_percent_vs_fraction", "百分数与分数的区别：百分数只表示两个数的倍比关系，不带单位；分数既可表示具体数量又可表示关系", 3, SUBJECT, G6, 265006),
    (265062, "pmath_g6a_point_percent_decimal", "百分数与小数的互化：小数化百分数小数点向右移两位添百分号，百分数化小数去掉百分号小数点左移两位", 4, SUBJECT, G6, 265006),
    (265063, "pmath_g6a_point_percent_fraction", "百分数与分数的互化：百分数化成分母是100的分数再约分，分数化成小数后再化成百分数", 5, SUBJECT, G6, 265006),
    (265064, "pmath_g6a_point_percent_rate", "求一个数是另一个数的百分之几：用除法计算，结果化成百分数，如发芽率=发芽数÷种子总数×100%", 6, SUBJECT, G6, 265006),
    (265065, "pmath_g6a_point_percent_common_rate", "常见的百分率：及格率、出勤率、合格率、发芽率等都表示部分量占总量的百分之几，结果不超过100%", 7, SUBJECT, G6, 265006),
    (265066, "pmath_g6a_point_percent_more_less", "求一个数比另一个数多（少）百分之几：先求相差量，再除以单位“1”的量，结果化成百分数", 8, SUBJECT, G6, 265006),
    (265067, "pmath_g6a_point_percent_find_whole", "已知一个数的百分之几是多少求这个数：用部分量除以对应百分率，也可设单位“1”为x列方程", 9, SUBJECT, G6, 265006),
    (265068, "pmath_g6a_point_discount", "折扣：几折表示十分之几，也就是百分之几十，现价=原价×折扣，折扣问题常与百分数互化结合", 10, SUBJECT, G6, 265006),

    # 第七单元 扇形统计图
    (265069, "pmath_g6a_point_pie_feature", "扇形统计图的特点：用整个圆表示总数，用大小不同的扇形表示各部分占总数的百分比，能直观反映部分与整体的关系", 1, SUBJECT, G6, 265007),
    (265070, "pmath_g6a_point_pie_read", "扇形统计图的读取与绘制：各部分百分比之和为100%，表示某部分的扇形圆心角=360°×该部分百分比", 2, SUBJECT, G6, 265007),
    (265071, "pmath_g6a_point_pie_analyze", "根据扇形统计图分析数据：已知总数可求各部分数量，已知某部分数量可求总数，注意与条形、折线统计图的区别", 3, SUBJECT, G6, 265007),

    # 第八单元 数学广角——数与形
    (265072, "pmath_g6a_point_number_shape", "数形结合的思想：把数量关系与图形结合起来思考，用形助数、以数解形，使抽象问题直观化", 1, SUBJECT, G6, 265008),
    (265073, "pmath_g6a_point_square_triangle_number", "正方形数与三角形数：用小正方形摆出正方形，第n个正方形数是n²；用小圆点摆三角形，第n个三角形数是n(n+1)÷2", 2, SUBJECT, G6, 265008),
    (265074, "pmath_g6a_point_odd_square", "从1开始的连续奇数之和：1+3+5+…+(2n-1)=n²，可用正方形图形直观说明其规律", 3, SUBJECT, G6, 265008),
    (265075, "pmath_g6a_point_find_pattern", "用图形发现规律的方法：从简单情形入手画图，观察图形与算式的对应关系，归纳出一般规律", 4, SUBJECT, G6, 265008),

    # 第九单元 总复习
    (265076, "pmath_g6a_point_review_fraction", "分数乘除法总复习：梳理分数乘除法的意义、计算法则、倒数以及相关的实际问题", 1, SUBJECT, G6, 265009),
    (265077, "pmath_g6a_point_review_ratio", "比和按比分配总复习：比的意义与基本性质、化简比与求比值、按比分配的实际应用", 2, SUBJECT, G6, 265009),
    (265078, "pmath_g6a_point_review_circle", "圆的总复习：圆的认识、半径直径关系、周长与面积公式、圆环与组合图形的计算", 3, SUBJECT, G6, 265009),
    (265079, "pmath_g6a_point_review_percent_chart", "百分数与统计总复习：百分数的意义与互化、百分率与折扣、扇形统计图的读取与分析", 4, SUBJECT, G6, 265009),
    (265080, "pmath_g6a_point_review_position_pattern", "位置方向与数形结合总复习：用方向和距离确定位置、描述路线图，数形结合的规律探究", 5, SUBJECT, G6, 265009),
)

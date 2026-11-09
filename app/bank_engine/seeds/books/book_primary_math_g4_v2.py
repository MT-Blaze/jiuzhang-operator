"""人教版小学数学四年级下册：十个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G4 = 4
BOOK_ID = 1420

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学四年级下册",
    "pmath_g4b",
    20,
    "人民教育出版社",
    SUBJECT,
    G4,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 十个单元
    (142001, "第一单元 四则运算", "pmath_g4b_u01", 1, BOOK_ID, None),
    (142002, "第二单元 观察物体（二）", "pmath_g4b_u02", 2, BOOK_ID, None),
    (142003, "第三单元 运算定律", "pmath_g4b_u03", 3, BOOK_ID, None),
    (142004, "第四单元 小数的意义和性质", "pmath_g4b_u04", 4, BOOK_ID, None),
    (142005, "第五单元 三角形", "pmath_g4b_u05", 5, BOOK_ID, None),
    (142006, "第六单元 小数的加法和减法", "pmath_g4b_u06", 6, BOOK_ID, None),
    (142007, "第七单元 图形的运动（二）", "pmath_g4b_u07", 7, BOOK_ID, None),
    (142008, "第八单元 平均数与条形统计图", "pmath_g4b_u08", 8, BOOK_ID, None),
    (142009, "第九单元 数学广角——鸡兔同笼", "pmath_g4b_u09", 9, BOOK_ID, None),
    (142010, "第十单元 总复习", "pmath_g4b_u10", 10, BOOK_ID, None),

    # 第一单元 四则运算
    (142011, "加减法的意义和各部分间的关系", "pmath_g4b_l01", 1, BOOK_ID, 142001),
    (142012, "乘除法的意义和各部分间的关系", "pmath_g4b_l02", 2, BOOK_ID, 142001),
    (142013, "括号", "pmath_g4b_l03", 3, BOOK_ID, 142001),
    (142014, "租船问题", "pmath_g4b_l04", 4, BOOK_ID, 142001),

    # 第二单元 观察物体（二）
    (142015, "从不同位置观察同一物体", "pmath_g4b_l05", 1, BOOK_ID, 142002),
    (142016, "根据看到的图形摆小正方体", "pmath_g4b_l06", 2, BOOK_ID, 142002),

    # 第三单元 运算定律
    (142017, "加法运算定律", "pmath_g4b_l07", 1, BOOK_ID, 142003),
    (142018, "乘法运算定律", "pmath_g4b_l08", 2, BOOK_ID, 142003),
    (142019, "简便计算", "pmath_g4b_l09", 3, BOOK_ID, 142003),

    # 第四单元 小数的意义和性质
    (142020, "小数的意义和读写法", "pmath_g4b_l10", 1, BOOK_ID, 142004),
    (142021, "小数的性质和大小比较", "pmath_g4b_l11", 2, BOOK_ID, 142004),
    (142022, "小数点移动引起小数大小的变化", "pmath_g4b_l12", 3, BOOK_ID, 142004),
    (142023, "小数与单位换算", "pmath_g4b_l13", 4, BOOK_ID, 142004),
    (142024, "小数的近似数", "pmath_g4b_l14", 5, BOOK_ID, 142004),

    # 第五单元 三角形
    (142025, "三角形的特性", "pmath_g4b_l15", 1, BOOK_ID, 142005),
    (142026, "三角形的分类", "pmath_g4b_l16", 2, BOOK_ID, 142005),
    (142027, "三角形的内角和", "pmath_g4b_l17", 3, BOOK_ID, 142005),
    (142028, "图形的拼组", "pmath_g4b_l18", 4, BOOK_ID, 142005),

    # 第六单元 小数的加法和减法
    (142029, "小数加减法", "pmath_g4b_l19", 1, BOOK_ID, 142006),
    (142030, "小数加减混合运算", "pmath_g4b_l20", 2, BOOK_ID, 142006),
    (142031, "整数加法运算定律推广到小数", "pmath_g4b_l21", 3, BOOK_ID, 142006),

    # 第七单元 图形的运动（二）
    (142032, "轴对称", "pmath_g4b_l22", 1, BOOK_ID, 142007),
    (142033, "平移", "pmath_g4b_l23", 2, BOOK_ID, 142007),

    # 第八单元 平均数与条形统计图
    (142034, "平均数", "pmath_g4b_l24", 1, BOOK_ID, 142008),
    (142035, "复式条形统计图", "pmath_g4b_l25", 2, BOOK_ID, 142008),

    # 第九单元 数学广角——鸡兔同笼
    (142036, "鸡兔同笼", "pmath_g4b_l26", 1, BOOK_ID, 142009),

    # 第十单元 总复习
    (142037, "总复习", "pmath_g4b_l27", 1, BOOK_ID, 142010),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 262001-262010 为册域层，262011-262078 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (262001, "pmath_g4b_domain_u01", "小学数学四下·第一单元 四则运算", 1, SUBJECT, G4, None),
    (262002, "pmath_g4b_domain_u02", "小学数学四下·第二单元 观察物体（二）", 2, SUBJECT, G4, None),
    (262003, "pmath_g4b_domain_u03", "小学数学四下·第三单元 运算定律", 3, SUBJECT, G4, None),
    (262004, "pmath_g4b_domain_u04", "小学数学四下·第四单元 小数的意义和性质", 4, SUBJECT, G4, None),
    (262005, "pmath_g4b_domain_u05", "小学数学四下·第五单元 三角形", 5, SUBJECT, G4, None),
    (262006, "pmath_g4b_domain_u06", "小学数学四下·第六单元 小数的加法和减法", 6, SUBJECT, G4, None),
    (262007, "pmath_g4b_domain_u07", "小学数学四下·第七单元 图形的运动（二）", 7, SUBJECT, G4, None),
    (262008, "pmath_g4b_domain_u08", "小学数学四下·第八单元 平均数与条形统计图", 8, SUBJECT, G4, None),
    (262009, "pmath_g4b_domain_u09", "小学数学四下·第九单元 数学广角——鸡兔同笼", 9, SUBJECT, G4, None),
    (262010, "pmath_g4b_domain_u10", "小学数学四下·第十单元 总复习", 10, SUBJECT, G4, None),

    # 第一单元 四则运算
    (262011, "pmath_g4b_point_add_meaning", "加法的意义和各部分关系：把两个数合并成一个数的运算叫加法，和=加数+加数，一个加数=和-另一个加数", 1, SUBJECT, G4, 262001),
    (262012, "pmath_g4b_point_sub_meaning", "减法的意义和各部分关系：已知两个数的和与其中一个加数，求另一个加数的运算叫减法，差=被减数-减数", 2, SUBJECT, G4, 262001),
    (262013, "pmath_g4b_point_add_sub_relation", "加减法各部分关系的应用：被减数=差+减数，减数=被减数-差，可据此求未知数并验算", 3, SUBJECT, G4, 262001),
    (262014, "pmath_g4b_point_mul_meaning", "乘法的意义和各部分关系：求几个相同加数的和的简便运算叫乘法，积=因数×因数，一个因数=积÷另一个因数", 4, SUBJECT, G4, 262001),
    (262015, "pmath_g4b_point_div_meaning", "除法的意义和各部分关系：已知两个因数的积与其中一个因数求另一个因数叫除法，商=被除数÷除数，0不能作除数", 5, SUBJECT, G4, 262001),
    (262016, "pmath_g4b_point_div_remainder", "有余数除法各部分关系：被除数=商×除数+余数，余数一定小于除数，验算用商×除数+余数", 6, SUBJECT, G4, 262001),
    (262017, "pmath_g4b_point_bracket_order", "含括号的运算顺序：先算小括号里面的，再算中括号里面的，最后算括号外面的；括号内仍先乘除后加减", 7, SUBJECT, G4, 262001),
    (262018, "pmath_g4b_point_charter_boat", "租船问题：先分别求大船小船的人均租金，比较后确定哪种便宜，尽量坐满，空位时调整方案使总租金最少", 8, SUBJECT, G4, 262001),

    # 第二单元 观察物体（二）
    (262019, "pmath_g4b_point_observe_position", "从不同位置观察同一物体：观察位置不同，看到的形状可能不同，一次最多同时看到物体的三个面", 1, SUBJECT, G4, 262002),
    (262020, "pmath_g4b_point_judge_view", "根据看到的形状判断观察位置：看小正方体的个数、排列与遮挡关系，推断观察者在正面、左面还是上面", 2, SUBJECT, G4, 262002),
    (262021, "pmath_g4b_point_build_from_views", "根据三视图摆小正方体：综合从正面、左面、上面看到的图形确定层数与列数，注意被遮挡的小正方体不能漏摆", 3, SUBJECT, G4, 262002),
    (262022, "pmath_g4b_point_draw_view", "画出观察到的图形：在方格纸上按看到的轮廓画图，只看得到的面，被挡住的部分不画", 4, SUBJECT, G4, 262002),

    # 第三单元 运算定律
    (262023, "pmath_g4b_point_add_commutative", "加法交换律：两个数相加，交换加数的位置和不变，字母表示 a+b=b+a", 1, SUBJECT, G4, 262003),
    (262024, "pmath_g4b_point_add_associative", "加法结合律：三个数相加，先把前两个数相加或先把后两个数相加，和不变，(a+b)+c=a+(b+c)", 2, SUBJECT, G4, 262003),
    (262025, "pmath_g4b_point_mul_commutative", "乘法交换律：两个数相乘，交换因数的位置积不变，a×b=b×a，验算乘法时常用", 3, SUBJECT, G4, 262003),
    (262026, "pmath_g4b_point_mul_associative", "乘法结合律：三个数相乘，先乘前两个或先乘后两个积不变，(a×b)×c=a×(b×c)", 4, SUBJECT, G4, 262003),
    (262027, "pmath_g4b_point_mul_distributive", "乘法分配律：两个数的和与一个数相乘，可以先把它们分别与这个数相乘再相加，(a+b)×c=a×c+b×c", 5, SUBJECT, G4, 262003),
    (262028, "pmath_g4b_point_distributive_reverse", "乘法分配律的逆用：a×c+b×c=(a+b)×c，提取相同因数凑整，如 38×7+62×7=100×7", 6, SUBJECT, G4, 262003),
    (262029, "pmath_g4b_point_sub_property", "减法的性质：一个数连续减去两个数，等于减去这两个数的和，a-b-c=a-(b+c)", 7, SUBJECT, G4, 262003),
    (262030, "pmath_g4b_point_div_property", "除法的性质：一个数连续除以两个数，等于除以这两个数的积，a÷b÷c=a÷(b×c)", 8, SUBJECT, G4, 262003),
    (262031, "pmath_g4b_point_simplify_pairs", "简便计算凑整技巧：牢记 25×4=100、125×8=1000，把接近整十整百的数拆成整百加减一个数再计算", 9, SUBJECT, G4, 262003),
    (262032, "pmath_g4b_point_distributive_trap", "乘法分配律易错点：只有两个数的和（或差）与一个数相乘才能分配，a×c+c 不能写成 a×(c+c)", 10, SUBJECT, G4, 262003),

    # 第四单元 小数的意义和性质
    (262033, "pmath_g4b_point_decimal_meaning", "小数的意义：分母是10、100、1000的分数可以写成小数，一位小数表示十分之几，两位小数表示百分之几", 1, SUBJECT, G4, 262004),
    (262034, "pmath_g4b_point_decimal_units", "小数的数位与计数单位：十分位、百分位、千分位的计数单位分别是0.1、0.01、0.001，相邻单位进率是10", 2, SUBJECT, G4, 262004),
    (262035, "pmath_g4b_point_decimal_read_write", "小数的读写法：读法先读整数部分再读小数点后各位；写法整数部分按整数写，小数部分依次写出每个数字", 3, SUBJECT, G4, 262004),
    (262036, "pmath_g4b_point_decimal_property", "小数的性质：小数末尾添上0或去掉0，小数的大小不变，但计数单位和精确度会改变", 4, SUBJECT, G4, 262004),
    (262037, "pmath_g4b_point_decimal_compare", "小数大小比较：先比较整数部分，整数部分相同再依次比较十分位、百分位，不能按位数多少判断", 5, SUBJECT, G4, 262004),
    (262038, "pmath_g4b_point_point_move_right", "小数点向右移动的规律：向右移动一位、两位、三位，小数就扩大到原来的10倍、100倍、1000倍，位数不够用0补足", 6, SUBJECT, G4, 262004),
    (262039, "pmath_g4b_point_point_move_left", "小数点向左移动的规律：向左移动一位、两位、三位，小数就缩小到原来的十分之一、百分之一、千分之一", 7, SUBJECT, G4, 262004),
    (262040, "pmath_g4b_point_point_move_apply", "小数点移动的应用：乘10、100、1000就是小数点向右移相应位数，除以10、100、1000就向左移相应位数", 8, SUBJECT, G4, 262004),
    (262041, "pmath_g4b_point_unit_convert", "小数与单位换算：高级单位化低级单位乘进率，低级单位化高级单位除以进率，结果可用小数表示", 9, SUBJECT, G4, 262004),
    (262042, "pmath_g4b_point_decimal_approx", "求小数的近似数：用四舍五入法保留一定位数，保留两位小数要看千分位，近似数末尾的0不能去掉", 10, SUBJECT, G4, 262004),
    (262043, "pmath_g4b_point_rewrite_wan_yi", "把大数改写成用万或亿作单位：是整万整亿数直接去0写单位，不是整万整亿数先四舍五入再写单位用≈", 11, SUBJECT, G4, 262004),

    # 第五单元 三角形
    (262044, "pmath_g4b_point_triangle_define", "三角形的定义与各部分：由三条线段首尾相连围成的图形叫三角形，有3个顶点、3条边、3个角和底与高", 1, SUBJECT, G4, 262005),
    (262045, "pmath_g4b_point_triangle_height", "三角形的底和高：从顶点向对边作垂线，顶点到垂足间的线段叫高，一个三角形有三组对应的底和高", 2, SUBJECT, G4, 262005),
    (262046, "pmath_g4b_point_stability", "三角形的稳定性：三角形三条边确定后形状和大小就确定，具有稳定性；四边形容易变形，可加斜撑固定", 3, SUBJECT, G4, 262005),
    (262047, "pmath_g4b_point_three_sides", "三角形三边关系：任意两边之和大于第三边，任意两边之差小于第三边，三条边中较短两边和大于最长边才能围成", 4, SUBJECT, G4, 262005),
    (262048, "pmath_g4b_point_classify_angle", "三角形按角分类：三个角都是锐角的是锐角三角形，有一个直角的是直角三角形，有一个钝角的是钝角三角形", 5, SUBJECT, G4, 262005),
    (262049, "pmath_g4b_point_classify_side", "三角形按边分类：有两条边相等的是等腰三角形，三条边都相等的是等边三角形，三边都不等的是不等边三角形", 6, SUBJECT, G4, 262005),
    (262050, "pmath_g4b_point_isosceles", "等腰三角形特征：两腰相等、两个底角相等，等边三角形是特殊的等腰三角形，三个角都是60°", 7, SUBJECT, G4, 262005),
    (262051, "pmath_g4b_point_angle_sum", "三角形内角和：任意三角形的内角和都是180°，已知两个角可求第三个角，180°减两角之和", 8, SUBJECT, G4, 262005),
    (262052, "pmath_g4b_point_angle_sum_apply", "三角形内角和的应用：直角三角形两个锐角的和是90°，等腰三角形已知顶角可求底角=(180°-顶角)÷2", 9, SUBJECT, G4, 262005),
    (262053, "pmath_g4b_point_shape_combine", "图形的拼组：两个完全一样的三角形可以拼成平行四边形，两个完全一样的直角三角形可拼成长方形或大三角形", 10, SUBJECT, G4, 262005),

    # 第六单元 小数的加法和减法
    (262054, "pmath_g4b_point_decimal_add", "小数加法竖式：把小数点对齐也就是相同数位对齐，从末位加起，哪一位满十向前一位进一", 1, SUBJECT, G4, 262006),
    (262055, "pmath_g4b_point_decimal_sub", "小数减法竖式：小数点对齐，被减数位数不够时用0补足，从末位减起，哪一位不够减向前一位借一当十", 2, SUBJECT, G4, 262006),
    (262056, "pmath_g4b_point_decimal_add_sub_check", "小数加减法的验算：加法交换加数位置再算一遍，减法用差加减数看是否等于被减数", 3, SUBJECT, G4, 262006),
    (262057, "pmath_g4b_point_decimal_mixed", "小数加减混合运算：没有括号按从左到右的顺序计算，有括号先算括号里面的，结果小数末尾的0可去掉", 4, SUBJECT, G4, 262006),
    (262058, "pmath_g4b_point_int_law_to_decimal", "整数加法运算定律推广到小数：加法交换律、结合律对小数同样适用，可把能凑整的小数先相加", 5, SUBJECT, G4, 262006),
    (262059, "pmath_g4b_point_decimal_sub_property", "小数减法的简便计算：连续减去两个数等于减去这两个数的和，a-b-c=a-(b+c)，注意凑整后小数位数", 6, SUBJECT, G4, 262006),
    (262060, "pmath_g4b_point_decimal_life", "小数加减法的实际应用：购物付款找零、身高体重比较、比赛成绩求和，列式后按小数加减法则计算并写单位", 7, SUBJECT, G4, 262006),

    # 第七单元 图形的运动（二）
    (262061, "pmath_g4b_point_axis_symmetric", "轴对称图形的认识：沿一条直线对折后两边完全重合的图形叫轴对称图形，这条直线叫对称轴，对称轴用虚线画", 1, SUBJECT, G4, 262007),
    (262062, "pmath_g4b_point_complete_symmetric", "补全轴对称图形：找出图形的关键点，数出每点到对称轴的格数，在另一侧数出同样格数找到对称点，再依次连线", 2, SUBJECT, G4, 262007),
    (262063, "pmath_g4b_point_translate_distance", "平移的方向和距离：图形平移后形状大小和方向都不变，对应点移动的格数就是平移的距离", 3, SUBJECT, G4, 262007),
    (262064, "pmath_g4b_point_draw_translate", "画出平移后的图形：先确定平移方向和格数，把每个关键点按方向平移相同格数，再按原图顺序连线", 4, SUBJECT, G4, 262007),
    (262065, "pmath_g4b_point_motion_apply", "轴对称与平移的应用：判断图形经过的是轴对称还是平移，利用两种变换设计或补全图案", 5, SUBJECT, G4, 262007),
    (262066, "pmath_g4b_point_motion_trap", "图形运动的易错点：平移格数要数对应点之间的格数而不是图形之间的空格，补全轴对称图形不能改变原图形的形状", 6, SUBJECT, G4, 262007),

    # 第八单元 平均数与条形统计图
    (262067, "pmath_g4b_point_mean_meaning", "平均数的意义：平均数表示一组数据的整体水平，是一个虚拟数，一定在最小数和最大数之间", 1, SUBJECT, G4, 262008),
    (262068, "pmath_g4b_point_mean_formula", "求平均数的方法：平均数=总数量÷总份数，也可以用移多补少的方法把多的补给少的使各组同样多", 2, SUBJECT, G4, 262008),
    (262069, "pmath_g4b_point_mean_apply", "平均数的应用与辨析：平均数不一定是这组数据中的某个数，不能代表其中某一个个体的情况", 3, SUBJECT, G4, 262008),
    (262070, "pmath_g4b_point_compound_bar", "复式条形统计图的认识：用两种不同颜色或花纹的直条表示两组数据，必须有图例说明每种直条代表的对象", 4, SUBJECT, G4, 262008),
    (262071, "pmath_g4b_point_compound_bar_draw", "复式条形统计图的绘制：确定横轴项目、纵轴数量和每格代表的数量，同一项目画两根等宽直条并标数据", 5, SUBJECT, G4, 262008),
    (262072, "pmath_g4b_point_compound_bar_analyze", "复式条形统计图的分析：直接比较两组数据的多少和变化，求两组数据的和与差，据此作出判断和预测", 6, SUBJECT, G4, 262008),

    # 第九单元 数学广角——鸡兔同笼
    (262073, "pmath_g4b_point_chicken_structure", "鸡兔同笼问题的结构：已知鸡和兔的总头数与总脚数，求鸡和兔各有多少只，鸡2只脚、兔4只脚", 1, SUBJECT, G4, 262009),
    (262074, "pmath_g4b_point_assume_chicken", "假设法一：假设全是鸡，总脚数会比实际少，少的脚数÷(4-2)就是兔的只数", 2, SUBJECT, G4, 262009),
    (262075, "pmath_g4b_point_assume_rabbit", "假设法二：假设全是兔，总脚数会比实际多，多的脚数÷(4-2)就是鸡的只数", 3, SUBJECT, G4, 262009),
    (262076, "pmath_g4b_point_list_method", "列表法：把鸡的只数从0开始有序增加，逐一算出脚数并与实际比较，直到脚数相等，适合数据较小的问题", 4, SUBJECT, G4, 262009),
    (262077, "pmath_g4b_point_chicken_variant", "鸡兔同笼的变式应用：龟鹤问题、租船问题、答题得分问题都可转化成鸡兔同笼，先找准两种量和总差", 5, SUBJECT, G4, 262009),

    # 第十单元 总复习
    (262078, "pmath_g4b_point_review_operation", "四则运算与运算定律总复习：含括号的运算顺序、加法乘法五大定律、减法与除法性质及简便计算凑整", 1, SUBJECT, G4, 262010),
    (262079, "pmath_g4b_point_review_decimal", "小数意义与性质总复习：计数单位与进率、小数性质、大小比较、小数点移动规律、单位换算与近似数", 2, SUBJECT, G4, 262010),
    (262080, "pmath_g4b_point_review_decimal_calc", "小数加减法总复习：小数点对齐、位数不足补0、混合运算顺序，以及用运算定律进行简便计算", 3, SUBJECT, G4, 262010),
    (262081, "pmath_g4b_point_review_triangle", "三角形总复习：三边关系、稳定性、按角和按边分类、内角和180°及图形拼组", 4, SUBJECT, G4, 262010),
    (262082, "pmath_g4b_point_review_motion", "图形运动总复习：轴对称图形的判断与补全、平移的方向与格数，以及两种变换的联系与区别", 5, SUBJECT, G4, 262010),
    (262083, "pmath_g4b_point_review_stat_chicken", "统计与数学广角总复习：平均数的求法与意义、复式条形统计图的绘制分析、鸡兔同笼假设法", 6, SUBJECT, G4, 262010),
)

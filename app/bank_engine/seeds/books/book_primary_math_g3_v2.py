"""人教版小学数学三年级下册：九个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G3 = 3
BOOK_ID = 1418

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学三年级下册",
    "pmath_g3b",
    18,
    "人民教育出版社",
    SUBJECT,
    G3,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 九个单元
    (141801, "第一单元 位置与方向（一）", "pmath_g3b_u01", 1, BOOK_ID, None),
    (141802, "第二单元 除数是一位数的除法", "pmath_g3b_u02", 2, BOOK_ID, None),
    (141803, "第三单元 复式统计表", "pmath_g3b_u03", 3, BOOK_ID, None),
    (141804, "第四单元 两位数乘两位数", "pmath_g3b_u04", 4, BOOK_ID, None),
    (141805, "第五单元 面积", "pmath_g3b_u05", 5, BOOK_ID, None),
    (141806, "第六单元 年月日", "pmath_g3b_u06", 6, BOOK_ID, None),
    (141807, "第七单元 小数的初步认识", "pmath_g3b_u07", 7, BOOK_ID, None),
    (141808, "第八单元 数学广角——搭配（二）", "pmath_g3b_u08", 8, BOOK_ID, None),
    (141809, "第九单元 总复习", "pmath_g3b_u09", 9, BOOK_ID, None),

    # 第一单元 位置与方向（一）
    (141810, "认识东南西北", "pmath_g3b_l01", 1, BOOK_ID, 141801),
    (141811, "认识东北、东南、西北、西南", "pmath_g3b_l02", 2, BOOK_ID, 141801),

    # 第二单元 除数是一位数的除法
    (141812, "口算除法", "pmath_g3b_l03", 1, BOOK_ID, 141802),
    (141813, "笔算除法", "pmath_g3b_l04", 2, BOOK_ID, 141802),
    (141814, "解决问题", "pmath_g3b_l05", 3, BOOK_ID, 141802),
    (141815, "整理和复习", "pmath_g3b_l06", 4, BOOK_ID, 141802),

    # 第三单元 复式统计表
    (141816, "认识复式统计表", "pmath_g3b_l07", 1, BOOK_ID, 141803),

    # 第四单元 两位数乘两位数
    (141817, "口算乘法", "pmath_g3b_l08", 1, BOOK_ID, 141804),
    (141818, "笔算乘法", "pmath_g3b_l09", 2, BOOK_ID, 141804),
    (141819, "解决问题", "pmath_g3b_l10", 3, BOOK_ID, 141804),
    (141820, "整理和复习", "pmath_g3b_l11", 4, BOOK_ID, 141804),

    # 第五单元 面积
    (141821, "面积和面积单位", "pmath_g3b_l12", 1, BOOK_ID, 141805),
    (141822, "长方形、正方形面积的计算", "pmath_g3b_l13", 2, BOOK_ID, 141805),
    (141823, "面积单位间的进率", "pmath_g3b_l14", 3, BOOK_ID, 141805),

    # 第六单元 年月日
    (141824, "年、月、日", "pmath_g3b_l15", 1, BOOK_ID, 141806),
    (141825, "24时计时法", "pmath_g3b_l16", 2, BOOK_ID, 141806),

    # 第七单元 小数的初步认识
    (141826, "认识小数", "pmath_g3b_l17", 1, BOOK_ID, 141807),
    (141827, "简单的小数加、减法", "pmath_g3b_l18", 2, BOOK_ID, 141807),

    # 第八单元 数学广角——搭配（二）
    (141828, "简单的排列与组合", "pmath_g3b_l19", 1, BOOK_ID, 141808),

    # 第九单元 总复习
    (141829, "总复习", "pmath_g3b_l20", 1, BOOK_ID, 141809),
)

# id / code / name / sort_order / subject_id / parent_id
# 260001-260009 为册域层，260010-260096 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (260001, "pmath_g3b_domain_u01", "小学数学三下·第一单元 位置与方向（一）", 1, SUBJECT, None),
    (260002, "pmath_g3b_domain_u02", "小学数学三下·第二单元 除数是一位数的除法", 2, SUBJECT, None),
    (260003, "pmath_g3b_domain_u03", "小学数学三下·第三单元 复式统计表", 3, SUBJECT, None),
    (260004, "pmath_g3b_domain_u04", "小学数学三下·第四单元 两位数乘两位数", 4, SUBJECT, None),
    (260005, "pmath_g3b_domain_u05", "小学数学三下·第五单元 面积", 5, SUBJECT, None),
    (260006, "pmath_g3b_domain_u06", "小学数学三下·第六单元 年月日", 6, SUBJECT, None),
    (260007, "pmath_g3b_domain_u07", "小学数学三下·第七单元 小数的初步认识", 7, SUBJECT, None),
    (260008, "pmath_g3b_domain_u08", "小学数学三下·第八单元 数学广角——搭配（二）", 8, SUBJECT, None),
    (260009, "pmath_g3b_domain_u09", "小学数学三下·第九单元 总复习", 9, SUBJECT, None),

    # 第一单元 位置与方向（一）
    (260010, "pmath_g3b_point_four_directions", "东南西北的认识：早晨面向太阳，前面是东、后面是西、左面是北、右面是南", 1, SUBJECT, 260001),
    (260011, "pmath_g3b_point_map_direction", "地图上的方向：地图通常按上北下南、左西右东绘制，看清方向标再读图", 2, SUBJECT, 260001),
    (260012, "pmath_g3b_point_observe_point", "观测点的确定：描述位置前先明确以谁为观测点，观测点变了方向也随之改变", 3, SUBJECT, 260001),
    (260013, "pmath_g3b_point_eight_directions", "八个方向的认识：东与北之间是东北，东与南之间是东南，西与北之间是西北，西与南之间是西南", 4, SUBJECT, 260001),
    (260014, "pmath_g3b_point_opposite_direction", "相对方向的判断：东与西相对、南与北相对，东北与西南相对、东南与西北相对", 5, SUBJECT, 260001),
    (260015, "pmath_g3b_point_clockwise_direction", "顺时针辨认方向：面向东时顺时针依次是南、西、北，用这一顺序可推出任意方向", 6, SUBJECT, 260001),
    (260016, "pmath_g3b_point_route_describe", "路线图的描述：按“从哪出发—向什么方向走—到达哪里”的顺序说清一段行程", 7, SUBJECT, 260001),
    (260017, "pmath_g3b_point_route_draw", "简单路线图的绘制：用箭头标出行走方向，方向改变处注明转向，保持上北下南", 8, SUBJECT, 260001),
    (260018, "pmath_g3b_point_direction_apply", "方向与位置的实际应用：在校园图、社区示意图中判断两地之间的方向和位置关系", 9, SUBJECT, 260001),
    (260019, "pmath_g3b_point_direction_word", "方向词的规范表达：东北、东南、西北、西南不能颠倒说成北东、南东、北西、南西", 10, SUBJECT, 260001),

    # 第二单元 除数是一位数的除法
    (260020, "pmath_g3b_point_tens_divide", "整十整百数除以一位数的口算：把被除数看成几个十或几个百，用表内除法算出商", 1, SUBJECT, 260002),
    (260021, "pmath_g3b_point_two_digit_divide", "两位数除以一位数的口算：把两位数拆成整十数和一位数分别除，再把两个商相加", 2, SUBJECT, 260002),
    (260022, "pmath_g3b_point_divide_estimate", "除法的估算：把被除数看成接近的整十整百数，用口算求出近似商并写“≈”", 3, SUBJECT, 260002),
    (260023, "pmath_g3b_point_divide_vertical", "三位数除以一位数首位够除的笔算：从最高位除起，除到哪一位商就写在哪一位上面", 4, SUBJECT, 260002),
    (260024, "pmath_g3b_point_divide_first_short", "首位不够除的笔算：先看被除数前两位，商写在十位上，余下的数继续往下除", 5, SUBJECT, 260002),
    (260025, "pmath_g3b_point_quotient_middle_zero", "商中间有0的除法：哪一位不够商1就在那一位商0占位，0不能省略不写", 6, SUBJECT, 260002),
    (260026, "pmath_g3b_point_quotient_tail_zero", "商末尾有0的除法：除到十位正好除尽而个位不够除时，个位要商0占位", 7, SUBJECT, 260002),
    (260027, "pmath_g3b_point_divide_check_exact", "没有余数除法的验算：用商乘除数，看积是否等于被除数", 8, SUBJECT, 260002),
    (260028, "pmath_g3b_point_divide_check_remainder", "有余数除法的验算：用商乘除数再加余数，看结果是否等于被除数", 9, SUBJECT, 260002),
    (260029, "pmath_g3b_point_average_divide", "平均分问题：总数÷份数=每份数，已知总数和每份数则用总数÷每份数求份数", 10, SUBJECT, 260002),
    (260030, "pmath_g3b_point_contain_divide", "包含除问题：求一个数里面有几个另一个数，用除法计算并注意商与余数的含义", 11, SUBJECT, 260002),
    (260031, "pmath_g3b_point_continuous_divide", "连除问题：先把总数平均分成若干大份，再把每大份平均分成小份，按顺序依次除", 12, SUBJECT, 260002),
    (260032, "pmath_g3b_point_divide_mixed", "除法与加减混合的实际问题：先理清数量关系，再确定先除后加减的运算顺序", 13, SUBJECT, 260002),

    # 第三单元 复式统计表
    (260033, "pmath_g3b_point_compound_table", "复式统计表的认识：把两组或多组数据合并在一个表里，便于整体比较和分析", 1, SUBJECT, 260003),
    (260034, "pmath_g3b_point_table_header", "复式统计表的表头：左上角分栏注明横栏和纵栏分别表示的项目，读表先看表头", 2, SUBJECT, 260003),
    (260035, "pmath_g3b_point_table_read", "复式统计表的读数：先确定行列项目，再在交叉格中找到对应数据，注意单位", 3, SUBJECT, 260003),
    (260036, "pmath_g3b_point_table_fill", "复式统计表的填写：先分类整理原始数据，再逐项填入对应格，最后核对合计", 4, SUBJECT, 260003),
    (260037, "pmath_g3b_point_table_compare", "单式与复式统计表的比较：复式表信息集中便于对比，但栏目更多、读表要更细心", 5, SUBJECT, 260003),
    (260038, "pmath_g3b_point_table_analyze", "根据统计表分析问题：比较各组数据的多少，求合计与相差，并说明数据背后的情况", 6, SUBJECT, 260003),

    # 第四单元 两位数乘两位数
    (260039, "pmath_g3b_point_tens_times_tens", "整十数乘整十数的口算：先算0前面的数相乘，再在积的末尾添上两个0", 1, SUBJECT, 260004),
    (260040, "pmath_g3b_point_two_digit_times_tens", "两位数乘整十数的口算：先算两位数乘十位上的数，再在积的末尾添一个0", 2, SUBJECT, 260004),
    (260041, "pmath_g3b_point_multiply_estimate", "两位数乘两位数的估算：把两个因数看成接近的整十数再乘，结果用“≈”表示", 3, SUBJECT, 260004),
    (260042, "pmath_g3b_point_multiply_plain", "两位数乘两位数（不进位）笔算：先用个位乘，再用十位乘，最后把两次的积相加", 4, SUBJECT, 260004),
    (260043, "pmath_g3b_point_multiply_carry", "两位数乘两位数的进位笔算：哪一位乘得的积满几十就向前一位进几，下一步要加上进位数", 5, SUBJECT, 260004),
    (260044, "pmath_g3b_point_second_partial", "第二部分积的对位：用十位上的数去乘，得数的末位要与十位对齐，不能与个位对齐", 6, SUBJECT, 260004),
    (260045, "pmath_g3b_point_multiply_check", "两位数乘两位数的验算：交换两个因数的位置再乘一遍，两次积相同说明计算正确", 7, SUBJECT, 260004),
    (260046, "pmath_g3b_point_continuous_multiply", "连乘问题：先求一份有多少，再求这样的几份是多少，按顺序依次相乘", 8, SUBJECT, 260004),
    (260047, "pmath_g3b_point_multiply_add_sub", "乘加、乘减的实际问题：先算乘法求出总数，再根据题意加上或减去相应数量", 9, SUBJECT, 260004),
    (260048, "pmath_g3b_point_multiply_shopping", "估算在购物中的应用：把单价和数量估大或估小，判断所带的钱够不够", 10, SUBJECT, 260004),
    (260049, "pmath_g3b_point_multiply_divide_choose", "乘法与除法的选择：求几个几是多少用乘法，把一个数平均分或求包含几个用除法", 11, SUBJECT, 260004),
    (260050, "pmath_g3b_point_multiply_review", "乘法整理和复习：口算、笔算、估算三类方法的特点与适用情境，注意进位和对位", 12, SUBJECT, 260004),

    # 第五单元 面积
    (260051, "pmath_g3b_point_area_meaning", "面积的意义：物体表面或封闭图形的大小就是它们的面积，面积描述的是面的大小", 1, SUBJECT, 260005),
    (260052, "pmath_g3b_point_area_perimeter_diff", "面积与周长的区别：周长是围一周边线的长度，面积是面的大小，二者单位不同不能比较", 2, SUBJECT, 260005),
    (260053, "pmath_g3b_point_area_units", "常用面积单位：平方厘米、平方分米、平方米，分别用于测量不同大小的面", 3, SUBJECT, 260005),
    (260054, "pmath_g3b_point_area_unit_image", "面积单位的表象：边长1厘米的正方形面积是1平方厘米，边长1分米的是1平方分米，边长1米的是1平方米", 4, SUBJECT, 260005),
    (260055, "pmath_g3b_point_area_unit_choose", "面积单位的选择：邮票面约4平方厘米、手帕面约4平方分米、教室地面约50平方米", 5, SUBJECT, 260005),
    (260056, "pmath_g3b_point_rectangle_area", "长方形面积公式：长方形面积=长×宽，已知长和宽可直接相乘求面积", 6, SUBJECT, 260005),
    (260057, "pmath_g3b_point_square_area", "正方形面积公式：正方形面积=边长×边长，边长相等所以两个因数相同", 7, SUBJECT, 260005),
    (260058, "pmath_g3b_point_area_apply", "面积计算的实际应用：求地面、墙面、菜地等长方形或正方形面的面积，先量出必要数据", 8, SUBJECT, 260005),
    (260059, "pmath_g3b_point_area_rate", "面积单位间的进率：1平方分米=100平方厘米，1平方米=100平方分米，相邻面积单位进率是100", 9, SUBJECT, 260005),
    (260060, "pmath_g3b_point_area_convert", "面积单位换算：大单位化小单位乘100，小单位化大单位除以100，换算时看清单位名称", 10, SUBJECT, 260005),
    (260061, "pmath_g3b_point_area_reverse", "已知面积求边长或宽：长方形宽=面积÷长，正方形边长用乘法口诀找相同的两个因数", 11, SUBJECT, 260005),
    (260062, "pmath_g3b_point_area_perimeter_apply", "面积与周长的综合应用：同一个长方形的面积和周长算法不同，解决实际问题要先判断求什么", 12, SUBJECT, 260005),

    # 第六单元 年月日
    (260063, "pmath_g3b_point_year_month_day", "年、月、日的关系：1年有12个月，每月有28天、29天、30天或31天，1日有24小时", 1, SUBJECT, 260006),
    (260064, "pmath_g3b_point_big_small_month", "大月与小月：1、3、5、7、8、10、12月是大月有31天，4、6、9、11月是小月有30天", 2, SUBJECT, 260006),
    (260065, "pmath_g3b_point_february", "二月的天数：平年二月28天，闰年二月29天，二月是唯一天数会变化的月份", 3, SUBJECT, 260006),
    (260066, "pmath_g3b_point_leap_year", "平年与闰年的判断：公历年份是4的倍数的一般是闰年，整百年份必须是400的倍数才是闰年", 4, SUBJECT, 260006),
    (260067, "pmath_g3b_point_year_days", "全年天数：平年365天，闰年366天，闰年比平年多的一天在二月", 5, SUBJECT, 260006),
    (260068, "pmath_g3b_point_month_memory", "大月小月的记忆方法：用拳头凸凹处记忆，或记歌诀“一三五七八十腊，三十一天永不差”", 6, SUBJECT, 260006),
    (260069, "pmath_g3b_point_24hour_meaning", "24时计时法的意义：一天从0时到24时连续计时，下午和晚上的时刻要加上12", 7, SUBJECT, 260006),
    (260070, "pmath_g3b_point_24hour_convert", "两种计时法的转换：普通计时法转24时计时法下午加12，24时计时法转普通计时法下午减12并加“下午”等词", 8, SUBJECT, 260006),
    (260071, "pmath_g3b_point_elapsed_time", "经过时间的计算：经过时间=结束时刻-开始时刻，同一时段内直接相减", 9, SUBJECT, 260006),
    (260072, "pmath_g3b_point_cross_day_time", "跨天经过时间的计算：先算到24时的时间，再加上第二天的时间，如21时到次日7时经过10小时", 10, SUBJECT, 260006),
    (260073, "pmath_g3b_point_calendar_make", "年历和月历的制作：按大月小月和二月天数排出每月日期，注意每月1日是星期几", 11, SUBJECT, 260006),
    (260074, "pmath_g3b_point_date_apply", "年月日在生活中的应用：计算天数、年龄、假期长度和星期几，先判断平年闰年", 12, SUBJECT, 260006),

    # 第七单元 小数的初步认识
    (260075, "pmath_g3b_point_decimal_meaning", "小数的意义：把1平均分成10份、100份，其中的几份可以用十分之几、百分之几写成小数", 1, SUBJECT, 260007),
    (260076, "pmath_g3b_point_decimal_read", "小数的读法：小数点读作“点”，整数部分按整数读，小数部分依次读出每个数字", 2, SUBJECT, 260007),
    (260077, "pmath_g3b_point_decimal_write", "小数的写法：先写整数部分，再写小数点，最后按顺序写出小数部分的每个数字", 3, SUBJECT, 260007),
    (260078, "pmath_g3b_point_decimal_parts", "小数的组成：小数由整数部分、小数点和小数部分组成，小数点左边是整数部分", 4, SUBJECT, 260007),
    (260079, "pmath_g3b_point_yuan_decimal", "元角分与小数：1元=10角，5角=0.5元，1元=100分，几元几角写成以元为单位的小数", 5, SUBJECT, 260007),
    (260080, "pmath_g3b_point_meter_decimal", "米分米厘米与小数：1分米=0.1米，1厘米=0.01米，复名数可以改写成以米为单位的小数", 6, SUBJECT, 260007),
    (260081, "pmath_g3b_point_decimal_compare", "小数的大小比较：先比整数部分，整数部分相同再依次比较小数部分，不能只看位数多少", 7, SUBJECT, 260007),
    (260082, "pmath_g3b_point_decimal_add", "简单的小数加法：小数点对齐，从末位加起，哪一位满十向前一位进1，得数点上小数点", 8, SUBJECT, 260007),
    (260083, "pmath_g3b_point_decimal_sub", "简单的小数减法：小数点对齐，从末位减起，哪一位不够减向前一位借1当10", 9, SUBJECT, 260007),
    (260084, "pmath_g3b_point_decimal_apply", "小数加减的实际应用：购物时算总价和找零，先把相同单位的数对齐再计算", 10, SUBJECT, 260007),

    # 第八单元 数学广角——搭配（二）
    (260085, "pmath_g3b_point_arrange_simple", "简单的排列：把几个元素按一定顺序排成一列，按固定首位依次变换其余位置", 1, SUBJECT, 260008),
    (260086, "pmath_g3b_point_arrange_order", "排列的有序列举：按从小到大或固定首位的顺序列举，做到不重复、不遗漏", 2, SUBJECT, 260008),
    (260087, "pmath_g3b_point_combine_simple", "简单的组合：从几个元素中任选两个配成一组，交换先后顺序仍是同一种组合", 3, SUBJECT, 260008),
    (260088, "pmath_g3b_point_arrange_vs_combine", "排列与组合的区别：交换位置后结果不同是排列，交换位置后结果相同是组合", 4, SUBJECT, 260008),
    (260089, "pmath_g3b_point_match_problem", "搭配问题的解决：衣服搭配、路线选择等问题用连线或列表列举出所有搭配方案", 5, SUBJECT, 260008),
    (260090, "pmath_g3b_point_order_thinking", "有序思考的策略：先确定一个元素再依次搭配其余元素，列举完再检查是否遗漏", 6, SUBJECT, 260008),

    # 第九单元 总复习
    (260091, "pmath_g3b_point_review_number", "数与运算总复习：除数是一位数的除法、两位数乘两位数的口算笔算与验算方法", 1, SUBJECT, 260009),
    (260092, "pmath_g3b_point_review_measure", "量与计量总复习：年月日与平闰年、24时计时法与经过时间、面积单位及换算", 2, SUBJECT, 260009),
    (260093, "pmath_g3b_point_review_shape", "图形与几何总复习：面积的意义、长方形和正方形的面积公式、面积与周长的区别", 3, SUBJECT, 260009),
    (260094, "pmath_g3b_point_review_statistics", "统计总复习：复式统计表的表头、读数、填写以及根据数据分析问题", 4, SUBJECT, 260009),
    (260095, "pmath_g3b_point_review_solve", "解决问题总复习：位置与方向、搭配、购物等实际问题的数量关系与解题步骤", 5, SUBJECT, 260009),
    (260096, "pmath_g3b_point_review_check", "易错点与检查习惯：商中0不漏写、乘法对位要准确、单位先统一、得数写完整答语", 6, SUBJECT, 260009),
)

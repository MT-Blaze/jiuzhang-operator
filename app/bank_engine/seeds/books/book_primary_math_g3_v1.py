"""人教版小学数学三年级上册：十个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G3 = 3
BOOK_ID = 1417

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学三年级上册",
    "pmath_g3a",
    17,
    "人民教育出版社",
    SUBJECT,
    G3,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 十个单元
    (141701, "第一单元 时分秒", "pmath_g3a_u01", 1, BOOK_ID, None),
    (141702, "第二单元 万以内的加法和减法（一）", "pmath_g3a_u02", 2, BOOK_ID, None),
    (141703, "第三单元 测量", "pmath_g3a_u03", 3, BOOK_ID, None),
    (141704, "第四单元 万以内的加法和减法（二）", "pmath_g3a_u04", 4, BOOK_ID, None),
    (141705, "第五单元 倍的认识", "pmath_g3a_u05", 5, BOOK_ID, None),
    (141706, "第六单元 多位数乘一位数", "pmath_g3a_u06", 6, BOOK_ID, None),
    (141707, "第七单元 长方形和正方形", "pmath_g3a_u07", 7, BOOK_ID, None),
    (141708, "第八单元 分数的初步认识", "pmath_g3a_u08", 8, BOOK_ID, None),
    (141709, "第九单元 数学广角——集合", "pmath_g3a_u09", 9, BOOK_ID, None),
    (141710, "第十单元 总复习", "pmath_g3a_u10", 10, BOOK_ID, None),

    # 第一单元 时分秒
    (141711, "秒的认识", "pmath_g3a_l01", 1, BOOK_ID, 141701),
    (141712, "时间的计算", "pmath_g3a_l02", 2, BOOK_ID, 141701),

    # 第二单元 万以内的加法和减法（一）
    (141713, "两位数加两位数", "pmath_g3a_l03", 1, BOOK_ID, 141702),
    (141714, "两位数减两位数", "pmath_g3a_l04", 2, BOOK_ID, 141702),
    (141715, "几百几十加减几百几十", "pmath_g3a_l05", 3, BOOK_ID, 141702),
    (141716, "估算", "pmath_g3a_l06", 4, BOOK_ID, 141702),

    # 第三单元 测量
    (141717, "毫米、分米的认识", "pmath_g3a_l07", 1, BOOK_ID, 141703),
    (141718, "千米的认识", "pmath_g3a_l08", 2, BOOK_ID, 141703),
    (141719, "吨的认识", "pmath_g3a_l09", 3, BOOK_ID, 141703),

    # 第四单元 万以内的加法和减法（二）
    (141720, "三位数加三位数", "pmath_g3a_l10", 1, BOOK_ID, 141704),
    (141721, "三位数减三位数", "pmath_g3a_l11", 2, BOOK_ID, 141704),
    (141722, "整理和复习", "pmath_g3a_l12", 3, BOOK_ID, 141704),

    # 第五单元 倍的认识
    (141723, "求一个数是另一个数的几倍", "pmath_g3a_l13", 1, BOOK_ID, 141705),
    (141724, "求一个数的几倍是多少", "pmath_g3a_l14", 2, BOOK_ID, 141705),

    # 第六单元 多位数乘一位数
    (141725, "口算乘法", "pmath_g3a_l15", 1, BOOK_ID, 141706),
    (141726, "笔算乘法", "pmath_g3a_l16", 2, BOOK_ID, 141706),
    (141727, "解决问题", "pmath_g3a_l17", 3, BOOK_ID, 141706),
    (141728, "整理和复习", "pmath_g3a_l18", 4, BOOK_ID, 141706),

    # 第七单元 长方形和正方形
    (141729, "四边形", "pmath_g3a_l19", 1, BOOK_ID, 141707),
    (141730, "周长", "pmath_g3a_l20", 2, BOOK_ID, 141707),
    (141731, "长方形和正方形的周长", "pmath_g3a_l21", 3, BOOK_ID, 141707),

    # 第八单元 分数的初步认识
    (141732, "几分之一", "pmath_g3a_l22", 1, BOOK_ID, 141708),
    (141733, "几分之几", "pmath_g3a_l23", 2, BOOK_ID, 141708),
    (141734, "分数的简单计算", "pmath_g3a_l24", 3, BOOK_ID, 141708),
    (141735, "分数的简单应用", "pmath_g3a_l25", 4, BOOK_ID, 141708),

    # 第九单元 数学广角——集合
    (141736, "重叠问题", "pmath_g3a_l26", 1, BOOK_ID, 141709),

    # 第十单元 总复习
    (141737, "总复习", "pmath_g3a_l27", 1, BOOK_ID, 141710),
)

# id / code / name / sort_order / subject_id / parent_id
# 259001-259010 为册域层，259011-259096 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (259001, "pmath_g3a_domain_u01", "小学数学三上·第一单元 时分秒", 1, SUBJECT, None),
    (259002, "pmath_g3a_domain_u02", "小学数学三上·第二单元 万以内的加法和减法（一）", 2, SUBJECT, None),
    (259003, "pmath_g3a_domain_u03", "小学数学三上·第三单元 测量", 3, SUBJECT, None),
    (259004, "pmath_g3a_domain_u04", "小学数学三上·第四单元 万以内的加法和减法（二）", 4, SUBJECT, None),
    (259005, "pmath_g3a_domain_u05", "小学数学三上·第五单元 倍的认识", 5, SUBJECT, None),
    (259006, "pmath_g3a_domain_u06", "小学数学三上·第六单元 多位数乘一位数", 6, SUBJECT, None),
    (259007, "pmath_g3a_domain_u07", "小学数学三上·第七单元 长方形和正方形", 7, SUBJECT, None),
    (259008, "pmath_g3a_domain_u08", "小学数学三上·第八单元 分数的初步认识", 8, SUBJECT, None),
    (259009, "pmath_g3a_domain_u09", "小学数学三上·第九单元 数学广角——集合", 9, SUBJECT, None),
    (259010, "pmath_g3a_domain_u10", "小学数学三上·第十单元 总复习", 10, SUBJECT, None),

    # 第一单元 时分秒
    (259011, "pmath_g3a_point_second_recognize", "秒的认识：计量很短的时间用秒，钟面上最细最长、走得最快的针是秒针，秒针走1小格是1秒", 1, SUBJECT, 259001),
    (259012, "pmath_g3a_point_minute_second_rate", "分与秒的进率：秒针走1圈是60秒，同时分针走1小格，所以1分=60秒", 2, SUBJECT, 259001),
    (259013, "pmath_g3a_point_hour_minute_rate", "时与分的进率：分针走1圈是60分，同时时针走1大格，所以1时=60分", 3, SUBJECT, 259001),
    (259014, "pmath_g3a_point_time_unit_choose", "时间单位的选择：跑50米约用10秒、刷牙约用3分、睡觉约用9时，按时间长短选合适单位", 4, SUBJECT, 259001),
    (259015, "pmath_g3a_point_elapsed_time", "经过时间的计算：用结束时刻减开始时刻，如8时20分到9时05分经过45分", 5, SUBJECT, 259001),
    (259016, "pmath_g3a_point_time_borrow", "时间计算的借位：分不够减时从时借1当60分再减，如9时10分减8时35分要先借位", 6, SUBJECT, 259001),
    (259017, "pmath_g3a_point_time_reasonable", "时间估测与合理性判断：算出结果后对照生活常识检查，跑100米用35分显然不合理", 7, SUBJECT, 259001),

    # 第二单元 万以内的加法和减法（一）
    (259018, "pmath_g3a_point_two_digit_add", "两位数加两位数口算：把第二个加数拆成整十数和一位数，先加整十数再加一位数", 1, SUBJECT, 259002),
    (259019, "pmath_g3a_point_two_digit_add_carry", "两位数加两位数的进位口算：个位满十向十位进1，口算时先算整十部分再补上进位", 2, SUBJECT, 259002),
    (259020, "pmath_g3a_point_two_digit_sub", "两位数减两位数口算：把减数拆成整十数和一位数，先减整十数再减一位数", 3, SUBJECT, 259002),
    (259021, "pmath_g3a_point_two_digit_sub_borrow", "两位数减两位数的退位口算：个位不够减从十位退1当10，注意退位后十位少1", 4, SUBJECT, 259002),
    (259022, "pmath_g3a_point_hundreds_add", "几百几十加几百几十笔算：相同数位对齐，从个位加起，哪一位满十向前一位进1", 5, SUBJECT, 259002),
    (259023, "pmath_g3a_point_hundreds_sub", "几百几十减几百几十笔算：相同数位对齐，从个位减起，哪一位不够减从前一位退1当10", 6, SUBJECT, 259002),
    (259024, "pmath_g3a_point_add_sub_check", "加减法的验算：加法交换加数位置再算或和减一个加数，减法用差加减数看是否得被减数", 7, SUBJECT, 259002),
    (259025, "pmath_g3a_point_estimate_strategy", "估算的策略：把两位数看成接近的整十数、把几百几十看成整百整十数，再口算得近似结果", 8, SUBJECT, 259002),
    (259026, "pmath_g3a_point_estimate_compare", "估算与精确值的比较：估大还是估小要说明理由，结合“够不够”“能不能”等情境作判断", 9, SUBJECT, 259002),

    # 第三单元 测量
    (259027, "pmath_g3a_point_millimeter", "毫米的认识：量比较短或要求精确到毫米时用毫米，1厘米中间的1小格长1毫米", 1, SUBJECT, 259003),
    (259028, "pmath_g3a_point_cm_mm_rate", "厘米与毫米的进率：1厘米=10毫米，3厘米5毫米合起来是35毫米", 2, SUBJECT, 259003),
    (259029, "pmath_g3a_point_decimeter", "分米的认识：10厘米长的一段是1分米，1分米=10厘米，1米=10分米", 3, SUBJECT, 259003),
    (259030, "pmath_g3a_point_length_convert", "长度单位换算方法：大单位化小单位乘进率，小单位化大单位除以进率", 4, SUBJECT, 259003),
    (259031, "pmath_g3a_point_length_choose", "长度单位的选择：铅笔长约18厘米、课桌高约7分米、教室长约8米，按物体长短选单位", 5, SUBJECT, 259003),
    (259032, "pmath_g3a_point_kilometer", "千米的认识：计量较远的路程用千米，1千米=1000米，操场跑道1圈约200米，5圈约1千米", 6, SUBJECT, 259003),
    (259033, "pmath_g3a_point_km_m_convert", "千米与米的换算：3千米=3000米，2500米=2千米500米，换算时注意进率是1000", 7, SUBJECT, 259003),
    (259034, "pmath_g3a_point_ton", "吨的认识：计量大宗物品的质量用吨，1吨=1000千克，1头大象约重5吨", 8, SUBJECT, 259003),
    (259035, "pmath_g3a_point_ton_kg_convert", "吨与千克的换算：2吨=2000千克，4500千克=4吨500千克，先按进率1000换算", 9, SUBJECT, 259003),
    (259036, "pmath_g3a_point_mass_choose", "质量单位的选择：一个鸡蛋约50克、一袋大米约25千克、一车煤约8吨，按物品轻重选单位", 10, SUBJECT, 259003),
    (259037, "pmath_g3a_point_measure_solve", "长度与质量单位的综合应用：解决载重、限高等问题先统一单位，再比较或计算", 11, SUBJECT, 259003),

    # 第四单元 万以内的加法和减法（二）
    (259038, "pmath_g3a_point_three_add_plain", "三位数加三位数（不进位）：相同数位对齐，从个位加起，逐位相加并写清结果", 1, SUBJECT, 259004),
    (259039, "pmath_g3a_point_three_add_carry", "三位数加三位数的进位加法：哪一位相加满十向前一位进1，连续进位要记清进位数", 2, SUBJECT, 259004),
    (259040, "pmath_g3a_point_three_sub_plain", "三位数减三位数（不退位）：相同数位对齐，从个位减起，逐位相减", 3, SUBJECT, 259004),
    (259041, "pmath_g3a_point_three_sub_borrow", "三位数减三位数的退位减法：哪一位不够减从前一位退1当10，连续退位注意前位已少1", 4, SUBJECT, 259004),
    (259042, "pmath_g3a_point_sub_middle_zero", "被减数中间有0的退位减法：0不够减向前一位借，借来的10要先给本位再继续往前退", 5, SUBJECT, 259004),
    (259043, "pmath_g3a_point_add_check", "加法的验算方法：交换两个加数的位置再加一遍，或用和减去一个加数看是否得另一个加数", 6, SUBJECT, 259004),
    (259044, "pmath_g3a_point_sub_check", "减法的验算方法：用差加减数看是否等于被减数，或用被减数减差看是否等于减数", 7, SUBJECT, 259004),
    (259045, "pmath_g3a_point_wan_estimate", "万以内加减法的估算：把三位数看成接近的整百数再计算，结果用“≈”表示并说明理由", 8, SUBJECT, 259004),
    (259046, "pmath_g3a_point_compare_more_less", "求比一个数多几或少几的数：多用加法、少用减法，画线段图理清两个数量之间的关系", 9, SUBJECT, 259004),

    # 第五单元 倍的认识
    (259047, "pmath_g3a_point_times_meaning", "倍的意义：把较小数看作1份，较大数里有几个这样的一份，就说较大数是较小数的几倍", 1, SUBJECT, 259005),
    (259048, "pmath_g3a_point_times_relation", "倍与乘除法的联系：求一个数的几倍是多少用乘法，求一个数是另一个数的几倍用除法", 2, SUBJECT, 259005),
    (259049, "pmath_g3a_point_times_divide", "求一个数是另一个数的几倍：用除法计算，如12是3的4倍，列式12÷3=4，得数后面不写“倍”", 3, SUBJECT, 259005),
    (259050, "pmath_g3a_point_times_multiply", "求一个数的几倍是多少：用乘法计算，如4的3倍是12，列式4×3=12", 4, SUBJECT, 259005),
    (259051, "pmath_g3a_point_times_segment", "用线段图表示倍数关系：先画表示1倍数的短线段，再按倍数画出几倍数的长线段", 5, SUBJECT, 259005),
    (259052, "pmath_g3a_point_times_reverse", "倍数问题的变式：已知几倍数和倍数求1倍数用除法，解题先找准谁是1份的量", 6, SUBJECT, 259005),
    (259053, "pmath_g3a_point_times_vs_more", "倍与“多几”的区别：倍表示份数关系用乘除计算，“多几”表示相差多少用减法计算", 7, SUBJECT, 259005),

    # 第六单元 多位数乘一位数
    (259054, "pmath_g3a_point_tens_multiply", "整十整百数乘一位数口算：先按表内乘法算出积，再在积的末尾添上相应个数的0", 1, SUBJECT, 259006),
    (259055, "pmath_g3a_point_two_digit_multiply", "两位数乘一位数口算：把两位数拆成整十数和一位数分别乘，再把两个积相加", 2, SUBJECT, 259006),
    (259056, "pmath_g3a_point_two_digit_vertical", "两位数乘一位数不进位笔算：从个位乘起，用一位数依次乘两位数的每一位", 3, SUBJECT, 259006),
    (259057, "pmath_g3a_point_two_digit_carry", "两位数乘一位数进位笔算：哪一位乘得的积满几十就向前一位进几，下一步别忘加上进位数", 4, SUBJECT, 259006),
    (259058, "pmath_g3a_point_three_digit_vertical", "三位数乘一位数笔算：从个位乘起，用一位数依次乘个位、十位、百位，注意连续进位", 5, SUBJECT, 259006),
    (259059, "pmath_g3a_point_middle_zero", "因数中间有0的乘法：0乘任何数都得0，但要加上前一位进上来的数，不能直接写0", 6, SUBJECT, 259006),
    (259060, "pmath_g3a_point_tail_zero", "因数末尾有0的乘法：先算0前面的数，再看因数末尾共有几个0，就在积的末尾添几个0", 7, SUBJECT, 259006),
    (259061, "pmath_g3a_point_multiply_estimate", "乘法的估算：把多位数看成接近的整十、整百数再乘，结果用“≈”表示", 8, SUBJECT, 259006),
    (259062, "pmath_g3a_point_normalize", "归一问题：先求出1份是多少，再求几份是多少，列式时先除后乘", 9, SUBJECT, 259006),
    (259063, "pmath_g3a_point_total_normalize", "归总问题：先求出总数，再按新的每份数重新分配，列式时先乘后除", 10, SUBJECT, 259006),
    (259064, "pmath_g3a_point_multiply_check", "乘法验算与错题检查：交换因数位置再乘一遍，检查积的位数和末尾0的个数是否正确", 11, SUBJECT, 259006),

    # 第七单元 长方形和正方形
    (259065, "pmath_g3a_point_quadrilateral", "四边形的特征：有4条直的边、4个角，并且是封闭图形，缺一不可", 1, SUBJECT, 259007),
    (259066, "pmath_g3a_point_rectangle_square_feature", "长方形与正方形的特征：长方形对边相等、4个角都是直角；正方形4条边相等、4个角都是直角", 2, SUBJECT, 259007),
    (259067, "pmath_g3a_point_square_special", "正方形是特殊的长方形：正方形具备长方形的全部特征，还多了四条边都相等这一条", 3, SUBJECT, 259007),
    (259068, "pmath_g3a_point_perimeter_meaning", "周长的意义：封闭图形一周的长度就是它的周长，图形不封闭就没有周长", 4, SUBJECT, 259007),
    (259069, "pmath_g3a_point_perimeter_measure", "测量并计算周长：先用尺量出各边长度再相加，规则图形可以直接用公式", 5, SUBJECT, 259007),
    (259070, "pmath_g3a_point_rectangle_perimeter", "长方形周长公式：长方形周长=(长+宽)×2，也可以写成“长×2+宽×2”", 6, SUBJECT, 259007),
    (259071, "pmath_g3a_point_square_perimeter", "正方形周长公式：正方形周长=边长×4，已知边长直接乘4", 7, SUBJECT, 259007),
    (259072, "pmath_g3a_point_perimeter_apply", "周长的实际应用：围篱笆、镶边框等问题先判断求的是周长还是边长，再选公式", 8, SUBJECT, 259007),
    (259073, "pmath_g3a_point_perimeter_reverse", "已知周长求边长：正方形边长=周长÷4，长方形宽=周长÷2-长", 9, SUBJECT, 259007),
    (259074, "pmath_g3a_point_perimeter_change", "拼组图形的周长变化：两个图形拼在一起周长减少，把一个图形剪开周长增加", 10, SUBJECT, 259007),

    # 第八单元 分数的初步认识
    (259075, "pmath_g3a_point_fraction_meaning", "分数的意义：把一个物体或图形平均分成若干份，表示其中1份或几份的数叫分数", 1, SUBJECT, 259008),
    (259076, "pmath_g3a_point_unit_fraction", "几分之一的认识：把一个图形平均分成4份，取其中1份就是四分之一，写作1/4", 2, SUBJECT, 259008),
    (259077, "pmath_g3a_point_fraction_parts", "分数各部分的名称：分数线下面的数叫分母表示平均分的份数，上面的数叫分子表示取的份数", 3, SUBJECT, 259008),
    (259078, "pmath_g3a_point_fraction_several", "几分之几的认识：平均分成5份取3份是五分之三，写作3/5，读作五分之三", 4, SUBJECT, 259008),
    (259079, "pmath_g3a_point_fraction_same_den", "同分母分数的大小比较：分母相同，分子大的分数就大，如3/5大于2/5", 5, SUBJECT, 259008),
    (259080, "pmath_g3a_point_fraction_same_num", "同分子分数的大小比较：分子相同，分母小的分数反而大，如1/3大于1/5", 6, SUBJECT, 259008),
    (259081, "pmath_g3a_point_fraction_one", "分数与1的关系：分子和分母相同的分数等于1，如4/4=1，5/5=1", 7, SUBJECT, 259008),
    (259082, "pmath_g3a_point_fraction_add", "同分母分数的加法：分母不变，分子相加，结果等于1时直接写成1", 8, SUBJECT, 259008),
    (259083, "pmath_g3a_point_fraction_sub", "同分母分数的减法：分母不变，分子相减，得数要约成最简形式或写成1", 9, SUBJECT, 259008),
    (259084, "pmath_g3a_point_fraction_one_sub", "1减去真分数：把1看成与减数分母相同的分数再减，如1-2/5=5/5-2/5=3/5", 10, SUBJECT, 259008),
    (259085, "pmath_g3a_point_fraction_part_apply", "分数的简单应用（求部分）：已知总数和平均分的份数，先求1份是多少，再乘取的份数", 11, SUBJECT, 259008),
    (259086, "pmath_g3a_point_fraction_compare_apply", "分数的简单应用（比较）：在同一个整体下，比较两个分数所表示的数量多少", 12, SUBJECT, 259008),

    # 第九单元 数学广角——集合
    (259087, "pmath_g3a_point_venn_structure", "集合图的组成：用两个相交的圈表示两类事物，重叠部分表示两类都包含的对象", 1, SUBJECT, 259009),
    (259088, "pmath_g3a_point_venn_total", "重叠问题的计数公式：总数=A类人数+B类人数-重叠人数", 2, SUBJECT, 259009),
    (259089, "pmath_g3a_point_venn_overlap", "求重叠部分：重叠人数=A类人数+B类人数-总人数", 3, SUBJECT, 259009),
    (259090, "pmath_g3a_point_venn_fill", "韦恩图的填数方法：先填重叠部分，再填只属于一类的部分，最后核对总数是否相符", 4, SUBJECT, 259009),
    (259091, "pmath_g3a_point_venn_apply", "集合思想解决实际问题：报名、参加活动等“既……又……”的问题用集合图分析", 5, SUBJECT, 259009),

    # 第十单元 总复习
    (259092, "pmath_g3a_point_review_number", "数与运算总复习：万以内加减法的笔算与验算、多位数乘一位数的口算与笔算、倍和分数", 1, SUBJECT, 259010),
    (259093, "pmath_g3a_point_review_measure", "量与计量总复习：时分秒的进率与经过时间、毫米分米千米吨的换算与单位选择", 2, SUBJECT, 259010),
    (259094, "pmath_g3a_point_review_shape", "图形与几何总复习：四边形的特征、周长的意义以及长方形和正方形的周长公式", 3, SUBJECT, 259010),
    (259095, "pmath_g3a_point_review_solve", "解决问题总复习：估算、归一归总、集合重叠等题型的数量关系与解题步骤", 4, SUBJECT, 259010),
    (259096, "pmath_g3a_point_review_check", "易错点与检查习惯：进位退位不丢数、0的处理要仔细、单位先统一、得数写完整答语", 5, SUBJECT, 259010),
)

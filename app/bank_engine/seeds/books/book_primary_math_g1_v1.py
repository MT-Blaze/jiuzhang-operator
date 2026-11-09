"""人教版小学数学一年级上册：九个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G1 = 1
BOOK_ID = 1413

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学一年级上册",
    "pmath_g1a",
    13,
    "人民教育出版社",
    SUBJECT,
    G1,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 九个单元
    (141301, "第一单元 准备课", "pmath_g1a_u01", 1, BOOK_ID, None),
    (141302, "第二单元 位置", "pmath_g1a_u02", 2, BOOK_ID, None),
    (141303, "第三单元 1~5的认识和加减法", "pmath_g1a_u03", 3, BOOK_ID, None),
    (141304, "第四单元 认识图形（一）", "pmath_g1a_u04", 4, BOOK_ID, None),
    (141305, "第五单元 6~10的认识和加减法", "pmath_g1a_u05", 5, BOOK_ID, None),
    (141306, "第六单元 11~20各数的认识", "pmath_g1a_u06", 6, BOOK_ID, None),
    (141307, "第七单元 认识钟表", "pmath_g1a_u07", 7, BOOK_ID, None),
    (141308, "第八单元 20以内的进位加法", "pmath_g1a_u08", 8, BOOK_ID, None),
    (141309, "第九单元 总复习", "pmath_g1a_u09", 9, BOOK_ID, None),

    # 第一单元 准备课
    (141311, "数一数", "pmath_g1a_l01", 1, BOOK_ID, 141301),
    (141312, "比多少", "pmath_g1a_l02", 2, BOOK_ID, 141301),

    # 第二单元 位置
    (141321, "上、下、前、后", "pmath_g1a_l03", 1, BOOK_ID, 141302),
    (141322, "左、右", "pmath_g1a_l04", 2, BOOK_ID, 141302),

    # 第三单元 1~5的认识和加减法
    (141331, "1~5的认识", "pmath_g1a_l05", 1, BOOK_ID, 141303),
    (141332, "比大小", "pmath_g1a_l06", 2, BOOK_ID, 141303),
    (141333, "第几", "pmath_g1a_l07", 3, BOOK_ID, 141303),
    (141334, "分与合", "pmath_g1a_l08", 4, BOOK_ID, 141303),
    (141335, "加法", "pmath_g1a_l09", 5, BOOK_ID, 141303),
    (141336, "减法", "pmath_g1a_l10", 6, BOOK_ID, 141303),
    (141337, "整理和复习", "pmath_g1a_l11", 7, BOOK_ID, 141303),

    # 第四单元 认识图形（一）
    (141341, "长方体、正方体、圆柱和球", "pmath_g1a_l12", 1, BOOK_ID, 141304),

    # 第五单元 6~10的认识和加减法
    (141351, "6和7", "pmath_g1a_l13", 1, BOOK_ID, 141305),
    (141352, "8和9", "pmath_g1a_l14", 2, BOOK_ID, 141305),
    (141353, "10", "pmath_g1a_l15", 3, BOOK_ID, 141305),
    (141354, "连加连减", "pmath_g1a_l16", 4, BOOK_ID, 141305),
    (141355, "加减混合", "pmath_g1a_l17", 5, BOOK_ID, 141305),
    (141356, "整理和复习", "pmath_g1a_l18", 6, BOOK_ID, 141305),

    # 第六单元 11~20各数的认识
    (141361, "数数、读数", "pmath_g1a_l19", 1, BOOK_ID, 141306),
    (141362, "写数", "pmath_g1a_l20", 2, BOOK_ID, 141306),
    (141363, "10加几、十几加几与相应的减法", "pmath_g1a_l21", 3, BOOK_ID, 141306),

    # 第七单元 认识钟表
    (141371, "认识整时", "pmath_g1a_l22", 1, BOOK_ID, 141307),

    # 第八单元 20以内的进位加法
    (141381, "9加几", "pmath_g1a_l23", 1, BOOK_ID, 141308),
    (141382, "8、7、6加几", "pmath_g1a_l24", 2, BOOK_ID, 141308),
    (141383, "5、4、3、2加几", "pmath_g1a_l25", 3, BOOK_ID, 141308),
    (141384, "整理和复习", "pmath_g1a_l26", 4, BOOK_ID, 141308),

    # 第九单元 总复习
    (141391, "总复习", "pmath_g1a_l27", 1, BOOK_ID, 141309),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 255001-255009 为册域层，255011-255073 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (255001, "pmath_g1a_domain_u01", "小学数学一上·第一单元 准备课与数数比多少", 1, SUBJECT, G1, None),
    (255002, "pmath_g1a_domain_u02", "小学数学一上·第二单元 位置与方向", 2, SUBJECT, G1, None),
    (255003, "pmath_g1a_domain_u03", "小学数学一上·第三单元 1~5的认识和加减法", 3, SUBJECT, G1, None),
    (255004, "pmath_g1a_domain_u04", "小学数学一上·第四单元 认识立体图形", 4, SUBJECT, G1, None),
    (255005, "pmath_g1a_domain_u05", "小学数学一上·第五单元 6~10的认识和加减法", 5, SUBJECT, G1, None),
    (255006, "pmath_g1a_domain_u06", "小学数学一上·第六单元 11~20各数的认识", 6, SUBJECT, G1, None),
    (255007, "pmath_g1a_domain_u07", "小学数学一上·第七单元 认识钟表与整时", 7, SUBJECT, G1, None),
    (255008, "pmath_g1a_domain_u08", "小学数学一上·第八单元 20以内的进位加法", 8, SUBJECT, G1, None),
    (255009, "pmath_g1a_domain_u09", "小学数学一上·第九单元 总复习与方法梳理", 9, SUBJECT, G1, None),

    # 第一单元 准备课与数数比多少
    (255011, "pmath_g1a_point_count_order", "手口一致地点数10以内的物体：从左到右或从上到下按顺序数，做到不重复、不遗漏", 1, SUBJECT, G1, 255001),
    (255012, "pmath_g1a_point_count_cardinal", "数数与基数：数到最后一个物体所对应的数就是这组物体的总数", 2, SUBJECT, G1, 255001),
    (255013, "pmath_g1a_point_match_one_one", "一一对应比多少：一个物体对一个物体地连线比较，建立同样多、多、少的直观概念", 3, SUBJECT, G1, 255001),
    (255014, "pmath_g1a_point_compare_more_less", "用“多”“少”“一样多”描述比较结果，会用添上或去掉的方法使两组物体同样多", 4, SUBJECT, G1, 255001),
    (255015, "pmath_g1a_point_count_error", "数数常见错误辨析：乱序点数、漏数被遮挡的物体、比较时未一一对应", 5, SUBJECT, G1, 255001),

    # 第二单元 位置与方向
    (255021, "pmath_g1a_point_up_down", "以自身或指定物体为参照，用上、下描述物体位置；上下位置具有相对性", 1, SUBJECT, G1, 255002),
    (255022, "pmath_g1a_point_front_back", "用前、后描述物体位置与排列顺序，理解前后与观察方向有关", 2, SUBJECT, G1, 255002),
    (255023, "pmath_g1a_point_left_right_self", "以自身为中心辨别左、右，区分左手与右手，用左、右描述身边物体的位置", 3, SUBJECT, G1, 255002),
    (255024, "pmath_g1a_point_left_right_relative", "左右的相对性：两人面对面时左右方向相反，判断他人左右需换位思考", 4, SUBJECT, G1, 255002),

    # 第三单元 1~5的认识和加减法
    (255031, "pmath_g1a_point_num1_5_read", "1~5各数的认读：数出物体个数并用相应数字表示，掌握1~5的书写笔顺与占格", 1, SUBJECT, G1, 255003),
    (255032, "pmath_g1a_point_num1_5_order", "1~5的顺序：从小到大排列，相邻两数相差1，会按顺序数、倒着数", 2, SUBJECT, G1, 255003),
    (255033, "pmath_g1a_point_compare_symbol", "比大小：用>、<、=表示两数大小关系，符号开口朝向较大的数", 3, SUBJECT, G1, 255003),
    (255034, "pmath_g1a_point_ordinal", "第几：序数含义，区分“几个”与“第几个”，会用第几描述排列位置", 4, SUBJECT, G1, 255003),
    (255035, "pmath_g1a_point_split_2_5", "2~5的分与合：把一个数分成两个数，两个数合起来等于原数", 5, SUBJECT, G1, 255003),
    (255036, "pmath_g1a_point_split_ordered", "有序分与合：按一定顺序分拆（如5分成1和4、2和3、3和2、4和1），不重不漏", 6, SUBJECT, G1, 255003),
    (255037, "pmath_g1a_point_add_meaning", "加法的含义：把两部分合并成一个整体，认识加号，会读写算式a+b=c", 7, SUBJECT, G1, 255003),
    (255038, "pmath_g1a_point_add_5", "5以内加法计算：用点数、接着数、数的组成三种方法求出和", 8, SUBJECT, G1, 255003),
    (255039, "pmath_g1a_point_sub_meaning", "减法的含义：从整体中去掉一部分求剩下部分，认识减号，会读写算式a-b=c", 9, SUBJECT, G1, 255003),
    (255040, "pmath_g1a_point_one_fig_equations", "一图两式与一图四式：根据一幅图写出两道加法算式或两道减法算式", 10, SUBJECT, G1, 255003),
    (255041, "pmath_g1a_point_zero_meaning", "0的认识：0表示一个也没有，会读写0，了解0在生活中的含义（起点、分界、占位）", 11, SUBJECT, G1, 255003),
    (255042, "pmath_g1a_point_zero_ops", "有关0的加减法：a+0=a、a-0=a、a-a=0，并通过整理和复习熟记5以内加减法表", 12, SUBJECT, G1, 255003),

    # 第四单元 认识立体图形
    (255051, "pmath_g1a_point_cuboid", "直观认识长方体：长长方方，有6个平平的面且面的大小不一，不能滚动", 1, SUBJECT, G1, 255004),
    (255052, "pmath_g1a_point_cube", "直观认识正方体：6个面都是正方形且大小相同，能稳稳堆叠、不能滚动", 2, SUBJECT, G1, 255004),
    (255053, "pmath_g1a_point_cylinder", "直观认识圆柱：上下两个面是大小相同的圆，侧面是曲面，放倒后能滚动", 3, SUBJECT, G1, 255004),
    (255054, "pmath_g1a_point_sphere", "直观认识球：表面是曲面，能向各个方向滚动，没有平平的面", 4, SUBJECT, G1, 255004),
    (255055, "pmath_g1a_point_solid_classify", "立体图形的分类与辨认：按面是否平平、能否滚动分类，能在生活情境中找出长方体、正方体、圆柱和球", 5, SUBJECT, G1, 255004),

    # 第五单元 6~10的认识和加减法
    (255061, "pmath_g1a_point_num6_7", "6和7的数数与认读：数出6、7个物体，理解基数与序数含义，掌握书写", 1, SUBJECT, G1, 255005),
    (255062, "pmath_g1a_point_split6_7", "6和7的组成：如6分成1和5、2和4、3和3，7分成1和6……有序记忆", 2, SUBJECT, G1, 255005),
    (255063, "pmath_g1a_point_addsub6_7", "6和7的加减法：依据数的组成口算，会根据一幅图写出四道算式", 3, SUBJECT, G1, 255005),
    (255064, "pmath_g1a_point_picture_problem", "用图画表示的实际问题：认识括线和问号，求总数用加法、求其中一部分用减法", 4, SUBJECT, G1, 255005),
    (255065, "pmath_g1a_point_num8_9", "8和9的数数、认读与顺序：会数、会读、会写，掌握8、9在数序中的位置", 5, SUBJECT, G1, 255005),
    (255066, "pmath_g1a_point_split8_9", "8和9的组成：按顺序分拆8和9，为8、9的加减法提供依据", 6, SUBJECT, G1, 255005),
    (255067, "pmath_g1a_point_addsub8_9", "8和9的加减法：利用数的组成口算，能根据一幅图写出一图四式", 7, SUBJECT, G1, 255005),
    (255068, "pmath_g1a_point_num10", "10的认识：10个一是1个十，掌握10的读写、顺序与基数序数含义", 8, SUBJECT, G1, 255005),
    (255069, "pmath_g1a_point_split10", "10的组成：10分成1和9、2和8……5和5，是凑十法的重要基础", 9, SUBJECT, G1, 255005),
    (255070, "pmath_g1a_point_addsub10", "10的加减法与一图四式：熟练口算10以内的加减，理解加减法之间的联系", 10, SUBJECT, G1, 255005),
    (255071, "pmath_g1a_point_continuous_add_sub", "连加连减：三个数连续相加或相减，按从左到右的顺序依次计算", 11, SUBJECT, G1, 255005),
    (255072, "pmath_g1a_point_mixed_add_sub", "加减混合：算式中既有加又有减，按从左到右的顺序计算，并整理复习10以内加减法表", 12, SUBJECT, G1, 255005),

    # 第六单元 11~20各数的认识
    (255074, "pmath_g1a_point_num11_20_count", "11~20各数的数数与读数：会一个一个数、两个两个数、五个五个数，正确读出各数", 1, SUBJECT, G1, 255006),
    (255075, "pmath_g1a_point_ten_bundle", "10根小棒捆成一捆表示1个十，1个十和几个一合起来就是十几", 2, SUBJECT, G1, 255006),
    (255076, "pmath_g1a_point_place_value", "数位：从右边起第一位是个位、第二位是十位，会用计数器表示11~20各数", 3, SUBJECT, G1, 255006),
    (255077, "pmath_g1a_point_write11_20", "11~20各数的写数：按数位书写，十位上的数表示几个十，个位上的数表示几个一", 4, SUBJECT, G1, 255006),
    (255078, "pmath_g1a_point_order11_20", "11~20各数的顺序与大小比较：借助数序和数的组成比较大小", 5, SUBJECT, G1, 255006),
    (255079, "pmath_g1a_point_ten_plus", "10加几及相应的减法：10+3=13、13-3=10、13-10=3，理解三个算式之间的联系", 6, SUBJECT, G1, 255006),
    (255080, "pmath_g1a_point_teen_add_sub", "十几加几（不进位）与十几减几（不退位）的口算：个位相加、个位相减，十位不变", 7, SUBJECT, G1, 255006),
    (255081, "pmath_g1a_point_add_sub_names", "加减法各部分名称：加数、和；被减数、减数、差，会结合算式指认", 8, SUBJECT, G1, 255006),

    # 第七单元 认识钟表与整时
    (255082, "pmath_g1a_point_clock_face", "认识钟面：钟面上有12个数，短而粗的是时针，长而细的是分针", 1, SUBJECT, G1, 255007),
    (255083, "pmath_g1a_point_whole_hour", "认识整时：分针指向12、时针指向几就是几时，如时针指8是8时", 2, SUBJECT, G1, 255007),
    (255084, "pmath_g1a_point_time_notation", "整时的两种写法：文字形式“8时”与电子表形式“8:00”互相对应", 3, SUBJECT, G1, 255007),
    (255085, "pmath_g1a_point_about_hour", "大约几时：会判断“快几时了”与“刚过几时”，结合作息合理安排时间", 4, SUBJECT, G1, 255007),

    # 第八单元 20以内的进位加法
    (255086, "pmath_g1a_point_9_plus", "9加几：用凑十法计算，看大数、拆小数、凑成十、十加几，如9+5=9+1+4", 1, SUBJECT, G1, 255008),
    (255087, "pmath_g1a_point_9_plus_rule", "9加几的规律：得数的十位是1，个位比另一个加数少1，可用于快速口算与检验", 2, SUBJECT, G1, 255008),
    (255088, "pmath_g1a_point_876_plus", "8、7、6加几：拆小数凑十，如8+5把5分成2和3，8+2=10，10+3=13", 3, SUBJECT, G1, 255008),
    (255089, "pmath_g1a_point_add_strategy", "8、7、6加几的算法多样化：凑十法、接着数法、交换加数位置法，择优口算", 4, SUBJECT, G1, 255008),
    (255090, "pmath_g1a_point_5432_plus", "5、4、3、2加几：用交换加数位置和不变，转化为9、8、7加几计算", 5, SUBJECT, G1, 255008),
    (255091, "pmath_g1a_point_carry_fluency", "20以内进位加法口算：熟练运用凑十法，做到正确、迅速，并会检验结果", 6, SUBJECT, G1, 255008),
    (255092, "pmath_g1a_point_carry_problem", "用进位加法解决实际问题：读懂情境，求“一共有多少”时把两部分合并用加法", 7, SUBJECT, G1, 255008),
    (255093, "pmath_g1a_point_carry_table", "20以内进位加法表：按一个加数排列整理，观察算式排列规律", 8, SUBJECT, G1, 255008),
    (255094, "pmath_g1a_point_carry_review", "整理和复习：一个加数不变，另一个加数加1，和也加1；发现规律并灵活运用", 9, SUBJECT, G1, 255008),

    # 第九单元 总复习与方法梳理
    (255095, "pmath_g1a_point_review_number", "数的认识复习：20以内数的顺序、组成、数位与大小比较综合梳理", 1, SUBJECT, G1, 255009),
    (255096, "pmath_g1a_point_review_calc", "计算复习：20以内加减法（含进位加法）的口算与混合运算，提高正确率", 2, SUBJECT, G1, 255009),
    (255097, "pmath_g1a_point_review_geometry", "图形与生活复习：立体图形辨认、上下前后左右位置、整时认读综合运用", 3, SUBJECT, G1, 255009),
    (255098, "pmath_g1a_point_review_problem", "解决简单实际问题的步骤：读题、找条件和问题、选择加法或减法列式、检验并口答", 4, SUBJECT, G1, 255009),
)

"""人教版小学数学二年级上册：九个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G2 = 2
BOOK_ID = 1415

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学二年级上册",
    "pmath_g2a",
    15,
    "人民教育出版社",
    SUBJECT,
    G2,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 九个单元
    (141501, "第一单元 长度单位", "pmath_g2a_u01", 1, BOOK_ID, None),
    (141502, "第二单元 100以内的加法和减法（二）", "pmath_g2a_u02", 2, BOOK_ID, None),
    (141503, "第三单元 角的初步认识", "pmath_g2a_u03", 3, BOOK_ID, None),
    (141504, "第四单元 表内乘法（一）", "pmath_g2a_u04", 4, BOOK_ID, None),
    (141505, "第五单元 观察物体（一）", "pmath_g2a_u05", 5, BOOK_ID, None),
    (141506, "第六单元 表内乘法（二）", "pmath_g2a_u06", 6, BOOK_ID, None),
    (141507, "第七单元 认识时间", "pmath_g2a_u07", 7, BOOK_ID, None),
    (141508, "第八单元 数学广角——搭配（一）", "pmath_g2a_u08", 8, BOOK_ID, None),
    (141509, "第九单元 总复习", "pmath_g2a_u09", 9, BOOK_ID, None),

    # 第一单元 长度单位
    (141511, "认识厘米", "pmath_g2a_l01", 1, BOOK_ID, 141501),
    (141512, "认识米", "pmath_g2a_l02", 2, BOOK_ID, 141501),
    (141513, "认识线段", "pmath_g2a_l03", 3, BOOK_ID, 141501),
    (141514, "长度单位的解决问题", "pmath_g2a_l04", 4, BOOK_ID, 141501),

    # 第二单元 100以内的加法和减法（二）
    (141521, "加法", "pmath_g2a_l05", 1, BOOK_ID, 141502),
    (141522, "减法", "pmath_g2a_l06", 2, BOOK_ID, 141502),
    (141523, "连加、连减和加减混合", "pmath_g2a_l07", 3, BOOK_ID, 141502),
    (141524, "求比一个数多几或少几", "pmath_g2a_l08", 4, BOOK_ID, 141502),
    (141525, "整理和复习", "pmath_g2a_l09", 5, BOOK_ID, 141502),

    # 第三单元 角的初步认识
    (141531, "角的初步认识", "pmath_g2a_l10", 1, BOOK_ID, 141503),
    (141532, "直角的初步认识", "pmath_g2a_l11", 2, BOOK_ID, 141503),
    (141533, "锐角和钝角", "pmath_g2a_l12", 3, BOOK_ID, 141503),

    # 第四单元 表内乘法（一）
    (141541, "乘法的初步认识", "pmath_g2a_l13", 1, BOOK_ID, 141504),
    (141542, "5的乘法口诀", "pmath_g2a_l14", 2, BOOK_ID, 141504),
    (141543, "2、3、4的乘法口诀", "pmath_g2a_l15", 3, BOOK_ID, 141504),
    (141544, "6的乘法口诀", "pmath_g2a_l16", 4, BOOK_ID, 141504),
    (141545, "用乘法解决问题", "pmath_g2a_l17", 5, BOOK_ID, 141504),
    (141546, "整理和复习", "pmath_g2a_l18", 6, BOOK_ID, 141504),

    # 第五单元 观察物体（一）
    (141551, "从不同位置观察物体", "pmath_g2a_l19", 1, BOOK_ID, 141505),

    # 第六单元 表内乘法（二）
    (141561, "7的乘法口诀", "pmath_g2a_l20", 1, BOOK_ID, 141506),
    (141562, "8的乘法口诀", "pmath_g2a_l21", 2, BOOK_ID, 141506),
    (141563, "9的乘法口诀", "pmath_g2a_l22", 3, BOOK_ID, 141506),
    (141564, "解决问题（倍与几个几）", "pmath_g2a_l23", 4, BOOK_ID, 141506),
    (141565, "整理和复习", "pmath_g2a_l24", 5, BOOK_ID, 141506),

    # 第七单元 认识时间
    (141571, "认识几时几分", "pmath_g2a_l25", 1, BOOK_ID, 141507),

    # 第八单元 数学广角——搭配（一）
    (141581, "简单的排列与组合", "pmath_g2a_l26", 1, BOOK_ID, 141508),

    # 第九单元 总复习
    (141591, "总复习", "pmath_g2a_l27", 1, BOOK_ID, 141509),
)

# id / code / name / sort_order / subject_id / parent_id
# 257001-257009 为册域层，257011-257083 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (257001, "pmath_g2a_domain_u01", "小学数学二上·第一单元 长度单位与线段", 1, SUBJECT, None),
    (257002, "pmath_g2a_domain_u02", "小学数学二上·第二单元 100以内的加法和减法（二）", 2, SUBJECT, None),
    (257003, "pmath_g2a_domain_u03", "小学数学二上·第三单元 角的初步认识", 3, SUBJECT, None),
    (257004, "pmath_g2a_domain_u04", "小学数学二上·第四单元 表内乘法（一）", 4, SUBJECT, None),
    (257005, "pmath_g2a_domain_u05", "小学数学二上·第五单元 观察物体（一）", 5, SUBJECT, None),
    (257006, "pmath_g2a_domain_u06", "小学数学二上·第六单元 表内乘法（二）", 6, SUBJECT, None),
    (257007, "pmath_g2a_domain_u07", "小学数学二上·第七单元 认识时间", 7, SUBJECT, None),
    (257008, "pmath_g2a_domain_u08", "小学数学二上·第八单元 数学广角——搭配（一）", 8, SUBJECT, None),
    (257009, "pmath_g2a_domain_u09", "小学数学二上·第九单元 总复习与综合应用", 9, SUBJECT, None),

    # 第一单元 长度单位与线段
    (257011, "pmath_g2a_point_unit_unify", "统一长度单位：用不同物品量同一物体结果不同，必须用统一的长度单位测量", 1, SUBJECT, 257001),
    (257012, "pmath_g2a_point_cm_meaning", "1厘米的表象：尺子上0到1之间的一段长1厘米，食指宽约1厘米，图钉长约1厘米", 2, SUBJECT, 257001),
    (257013, "pmath_g2a_point_cm_measure", "用厘米尺量长度：物体左端对准0刻度，右端对着几就是几厘米，尺子放平并紧贴物体", 3, SUBJECT, 257001),
    (257014, "pmath_g2a_point_cm_broken_ruler", "断尺测量：不从0刻度量起时，用末端刻度减去起始刻度求长度，如从2量到7是5厘米", 4, SUBJECT, 257001),
    (257015, "pmath_g2a_point_meter", "认识米：量较长物体用米尺，1米=100厘米，米用字母m表示，厘米用字母cm表示", 5, SUBJECT, 257001),
    (257016, "pmath_g2a_point_length_estimate", "长度估测与单位选择：借助1厘米、1米的表象估计，课桌高约70厘米、教室长约8米，选对单位", 6, SUBJECT, 257001),
    (257017, "pmath_g2a_point_segment_feature", "线段的特征：直直的、有两个端点、可以量出长度，两端不能再延长", 7, SUBJECT, 257001),
    (257018, "pmath_g2a_point_segment_draw", "画线段：从尺子0刻度画到指定刻度得到指定厘米数的线段，也可从任意刻度起量出长度后画", 8, SUBJECT, 257001),
    (257019, "pmath_g2a_point_length_problem", "长度计算的实际问题：如绳子长90厘米剪去30厘米还剩60厘米，两段接起来要把长度相加", 9, SUBJECT, 257001),

    # 第二单元 100以内的加法和减法（二）
    (257020, "pmath_g2a_point_add2_nocarry", "两位数加两位数（不进位）：相同数位对齐，从个位加起，个位不满十，十位相加，如34+25=59", 1, SUBJECT, 257002),
    (257021, "pmath_g2a_point_add2_carry", "两位数加两位数（进位）：个位相加满十向十位进1，在十位下写小1，如38+25=63", 2, SUBJECT, 257002),
    (257022, "pmath_g2a_point_vertical_format", "笔算加法书写规范：相同数位对齐，从个位算起，横线用尺子画直，进位的1写在十位数字右下角", 3, SUBJECT, 257002),
    (257023, "pmath_g2a_point_sub2_noborrow", "两位数减两位数（不退位）：相同数位对齐，从个位减起，个位够减直接减，如76-42=34", 4, SUBJECT, 257002),
    (257024, "pmath_g2a_point_sub2_borrow", "两位数减两位数（退位）：个位不够减从十位退1当10再减，在十位数字上点退位点，如52-38=14", 5, SUBJECT, 257002),
    (257025, "pmath_g2a_point_check_addsub", "加减法的验算：加法用和减一个加数看是否等于另一个加数，减法用差加减数看是否等于被减数", 6, SUBJECT, 257002),
    (257026, "pmath_g2a_point_chain_add", "连加的运算顺序：没有括号时从左到右依次计算，可写两个竖式或一个连加竖式，如28+34+22=84", 7, SUBJECT, 257002),
    (257027, "pmath_g2a_point_chain_sub", "连减的运算顺序：从左到右依次减，如90-25-30=35，第一步的得数再参与第二步计算", 8, SUBJECT, 257002),
    (257028, "pmath_g2a_point_add_sub_mix", "加减混合的运算顺序：按从左到右的顺序计算，如45+28-36=37，先算加法再算减法", 9, SUBJECT, 257002),
    (257029, "pmath_g2a_point_more_than", "求比一个数多几的数：用加法，如二（1）班23人，二（2）班多5人，二（2）班有23+5=28人", 10, SUBJECT, 257002),
    (257030, "pmath_g2a_point_less_than", "求比一个数少几的数：用减法，如小明有35张画片，小红少8张，小红有35-8=27张", 11, SUBJECT, 257002),
    (257031, "pmath_g2a_point_two_questions", "连续两问的实际问题：先解答第一问，把结果作为条件再解答第二问，两问都要写答语", 12, SUBJECT, 257002),

    # 第三单元 角的初步认识
    (257032, "pmath_g2a_point_angle_parts", "角的组成：角由一个顶点和两条边组成，边是直直的，角通常用符号“∠”表示", 1, SUBJECT, 257003),
    (257033, "pmath_g2a_point_angle_size", "角的大小比较：角的大小与两条边张开的大小有关，与边画得长短无关，开口越大角越大", 2, SUBJECT, 257003),
    (257034, "pmath_g2a_point_angle_draw", "画角的方法：先画一个顶点，再从顶点起用尺子画两条直直的边，可以画出大小不同的角", 3, SUBJECT, 257003),
    (257035, "pmath_g2a_point_right_angle", "直角的认识：三角尺上有一个角是直角，直角是判断其他角的标准，用三角尺上的直角比一比", 4, SUBJECT, 257003),
    (257036, "pmath_g2a_point_right_angle_draw", "画直角：用三角尺的直角，先画顶点和一条边，再沿另一条直角边画出另一边，标上直角符号", 5, SUBJECT, 257003),
    (257037, "pmath_g2a_point_acute_angle", "锐角的认识：比直角小的角叫锐角，判断时把三角尺直角的顶点和一条边对齐被比的角", 6, SUBJECT, 257003),
    (257038, "pmath_g2a_point_obtuse_angle", "钝角的认识与分类：比直角大的角叫钝角，角按大小分为锐角、直角、钝角三类", 7, SUBJECT, 257003),

    # 第四单元 表内乘法（一）
    (257039, "pmath_g2a_point_multiply_meaning", "乘法的意义：求几个相同加数的和用乘法计算比较简便，如3+3+3+3表示4个3相加", 1, SUBJECT, 257004),
    (257040, "pmath_g2a_point_multiply_parts", "乘法算式各部分名称：因数×因数=积，“×”是乘号，算式读作几乘几等于几", 2, SUBJECT, 257004),
    (257041, "pmath_g2a_point_add_to_multiply", "加法算式改写成乘法算式：相同加数是几就写几，相同加数的个数是几就乘几，如2+2+2=2×3", 3, SUBJECT, 257004),
    (257042, "pmath_g2a_point_table5", "5的乘法口诀：一五得五、二五一十、三五十五、四五二十、五五二十五，积的个位是0或5", 4, SUBJECT, 257004),
    (257043, "pmath_g2a_point_table234", "2、3、4的乘法口诀：一二得二、二二得四；一三得三、二三得六、三三得九；一四得四到四四十六", 5, SUBJECT, 257004),
    (257044, "pmath_g2a_point_table6", "6的乘法口诀：一六得六、二六十二、三六十八、四六二十四、五六三十、六六三十六", 6, SUBJECT, 257004),
    (257045, "pmath_g2a_point_table_rule", "口诀的记忆规律：相邻两句口诀的积相差一个相同的加数，如5的口诀相邻两句积相差5", 7, SUBJECT, 257004),
    (257046, "pmath_g2a_point_one_rhyme_two", "一句口诀写两个乘法算式：如“三四十二”可写3×4=12和4×3=12，两个因数相同的口诀只写一个", 8, SUBJECT, 257004),
    (257047, "pmath_g2a_point_multiply_add", "乘加混合运算：先算乘法再算加法，如4×5+6先算4×5=20，再加6得26", 9, SUBJECT, 257004),
    (257048, "pmath_g2a_point_multiply_sub", "乘减混合运算：先算乘法再算减法，如5×6-8先算5×6=30，再减8得22", 10, SUBJECT, 257004),
    (257049, "pmath_g2a_point_multiply_problem", "用乘法解决实际问题：求几个几是多少用乘法，如每盘4个苹果、3盘一共4×3=12个", 11, SUBJECT, 257004),
    (257050, "pmath_g2a_point_add_or_multiply", "乘法与加法的选择：加数相同时用乘法简便，加数不同时只能用加法，先判断再加或乘", 12, SUBJECT, 257004),
    (257051, "pmath_g2a_point_table_review1", "1~6的乘法口诀整理：按因数顺序整理口诀表，横看竖看发现积的变化规律并熟记", 13, SUBJECT, 257004),

    # 第五单元 观察物体（一）
    (257052, "pmath_g2a_point_observe_diff", "不同位置观察同一物体：站在前面、后面、左面、右面看到的形状可能不同，最多看到三个面", 1, SUBJECT, 257005),
    (257053, "pmath_g2a_point_observe_views", "辨认简单物体的视图：能指出从前面、后面、左面、右面看到的形状，注意左右方向相反", 2, SUBJECT, 257005),
    (257054, "pmath_g2a_point_observe_position", "根据形状判断观察位置：由看到的形状反推观察者站在物体的哪一面，抓住关键特征", 3, SUBJECT, 257005),
    (257055, "pmath_g2a_point_observe_method", "观察物体的方法：平视物体，整体与局部结合，按一定顺序观察并描述看到的形状", 4, SUBJECT, 257005),

    # 第六单元 表内乘法（二）
    (257056, "pmath_g2a_point_table7", "7的乘法口诀：一七得七、二七十四、三七二十一、四七二十八、五七三十五、六七四十二、七七四十九", 1, SUBJECT, 257006),
    (257057, "pmath_g2a_point_table8", "8的乘法口诀：一八得八、二八十六、三八二十四、四八三十二、五八四十、六八四十八、七八五十六、八八六十四", 2, SUBJECT, 257006),
    (257058, "pmath_g2a_point_table9", "9的乘法口诀：一九得九、二九十八、三九二十七、四九三十六、五九四十五、六九五十四、七九六十三、八九七十二、九九八十一", 3, SUBJECT, 257006),
    (257059, "pmath_g2a_point_table9_rule", "9的口诀规律：积的十位数字依次加1、个位数字依次减1，两个数字之和都是9，可用手指帮助记忆", 4, SUBJECT, 257006),
    (257060, "pmath_g2a_point_table_all", "1~9乘法口诀表：按顺序整理成表，横看是同一因数的口诀，竖看积依次增加这个因数，斜看两个因数相同", 5, SUBJECT, 257006),
    (257061, "pmath_g2a_point_table_factor", "用口诀求积与求因数：已知两个因数用口诀求积，已知积和一个因数想口诀求另一个因数", 6, SUBJECT, 257006),
    (257062, "pmath_g2a_point_times_meaning", "倍的意义：求一个数的几倍是多少就是求几个这个数相加，用乘法，如3的4倍是3×4=12", 7, SUBJECT, 257006),
    (257063, "pmath_g2a_point_times_problem", "解决倍的实际问题：先找准“1倍”的量，再根据倍数用乘法求几倍的量，注意与“多几”区分", 8, SUBJECT, 257006),
    (257064, "pmath_g2a_point_mix_apply", "乘加乘减综合应用：结合图形或生活情境先乘后加减，说清每一步求的是什么", 9, SUBJECT, 257006),
    (257065, "pmath_g2a_point_table_review2", "表内乘法整理复习：熟记1~9口诀，灵活选择口诀求积，用乘法解决求几个几和求几倍的问题", 10, SUBJECT, 257006),

    # 第七单元 认识时间
    (257066, "pmath_g2a_point_clock_face", "钟面的结构：钟面上有12个大格、60个小格，有12个数字，时针短、分针长", 1, SUBJECT, 257007),
    (257067, "pmath_g2a_point_hour_minute", "时与分的关系：分针走一圈是60分，时针正好走1大格，所以1时=60分", 2, SUBJECT, 257007),
    (257068, "pmath_g2a_point_read_time", "认识几时几分：时针走过数字几就是几时多，分针从12起走过几小格就是几分，合起来读作几时几分", 3, SUBJECT, 257007),
    (257069, "pmath_g2a_point_count_minutes", "5分5分数与1分1分数：分针指在数字上时用5分5分数，指在两个数字之间时1分1分数", 4, SUBJECT, 257007),
    (257070, "pmath_g2a_point_write_time", "时间的读写：会用“几时几分”和电子表形式“几:几”表示时间，8时5分写作8:05", 5, SUBJECT, 257007),
    (257071, "pmath_g2a_point_elapsed_time", "经过时间的计算：在同一小时内用结束时刻减开始时刻，如从8:10到8:40经过了30分", 6, SUBJECT, 257007),
    (257072, "pmath_g2a_point_time_plan", "合理安排时间：结合作息认识时间的有序性，能说出做某件事大约需要多长时间", 7, SUBJECT, 257007),

    # 第八单元 数学广角——搭配（一）
    (257073, "pmath_g2a_point_permutation_two", "简单的排列：用两个数字组两位数，交换位置得到不同的数，如1和2组成12和21", 1, SUBJECT, 257008),
    (257074, "pmath_g2a_point_permutation_three", "三个数字组两位数：固定十位法或交换位置法有序列举，做到不重复、不遗漏", 2, SUBJECT, 257008),
    (257075, "pmath_g2a_point_combination", "简单的组合：握手、比赛场次等问题与顺序无关，如3人每两人握一次手共握3次", 3, SUBJECT, 257008),
    (257076, "pmath_g2a_point_permute_vs_combine", "排列与组合的区别：排列与顺序有关，组合与顺序无关，解题前先判断是否讲顺序", 4, SUBJECT, 257008),
    (257077, "pmath_g2a_point_order_thinking", "有序思考的策略：按固定十位、固定个位等顺序列举，用标记或连线记录，检查是否重复遗漏", 5, SUBJECT, 257008),

    # 第九单元 总复习与综合应用
    (257078, "pmath_g2a_point_review_length", "长度单位与线段复习：厘米和米的认识、1米=100厘米、用尺测量与画线段、长度估测", 1, SUBJECT, 257009),
    (257079, "pmath_g2a_point_review_calc100", "100以内加减法复习：两位数加减两位数的笔算方法、进位与退位、连加连减和加减混合的运算顺序", 2, SUBJECT, 257009),
    (257080, "pmath_g2a_point_review_multiply", "表内乘法复习：1~9的乘法口诀、乘法算式的意义、乘加乘减和用乘法解决实际问题", 3, SUBJECT, 257009),
    (257081, "pmath_g2a_point_review_angle_observe", "角与观察物体复习：角的组成与大小比较、直角锐角钝角的判断、从不同位置观察物体", 4, SUBJECT, 257009),
    (257082, "pmath_g2a_point_review_time_pair", "认识时间与搭配复习：时分的读写与经过时间、简单排列组合的有序思考", 5, SUBJECT, 257009),
    (257083, "pmath_g2a_point_review_problem", "综合解决问题的步骤：读题找条件和问题、分析数量关系、选择算法列式计算、检验并写答语", 6, SUBJECT, 257009),
)

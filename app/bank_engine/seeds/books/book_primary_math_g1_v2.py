"""人教版小学数学一年级下册：八个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G1 = 1
BOOK_ID = 1414

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学一年级下册",
    "pmath_g1b",
    14,
    "人民教育出版社",
    SUBJECT,
    G1,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 八个单元
    (141401, "第一单元 认识图形（二）", "pmath_g1b_u01", 1, BOOK_ID, None),
    (141402, "第二单元 20以内的退位减法", "pmath_g1b_u02", 2, BOOK_ID, None),
    (141403, "第三单元 分类与整理", "pmath_g1b_u03", 3, BOOK_ID, None),
    (141404, "第四单元 100以内数的认识", "pmath_g1b_u04", 4, BOOK_ID, None),
    (141405, "第五单元 认识人民币", "pmath_g1b_u05", 5, BOOK_ID, None),
    (141406, "第六单元 100以内的加法和减法（一）", "pmath_g1b_u06", 6, BOOK_ID, None),
    (141407, "第七单元 找规律", "pmath_g1b_u07", 7, BOOK_ID, None),
    (141408, "第八单元 总复习", "pmath_g1b_u08", 8, BOOK_ID, None),

    # 第一单元 认识图形（二）
    (141411, "认识平面图形", "pmath_g1b_l01", 1, BOOK_ID, 141401),
    (141412, "拼一拼", "pmath_g1b_l02", 2, BOOK_ID, 141401),

    # 第二单元 20以内的退位减法
    (141421, "十几减9", "pmath_g1b_l03", 1, BOOK_ID, 141402),
    (141422, "十几减8、7、6", "pmath_g1b_l04", 2, BOOK_ID, 141402),
    (141423, "十几减5、4、3、2", "pmath_g1b_l05", 3, BOOK_ID, 141402),
    (141424, "解决问题", "pmath_g1b_l06", 4, BOOK_ID, 141402),
    (141425, "整理和复习", "pmath_g1b_l07", 5, BOOK_ID, 141402),

    # 第三单元 分类与整理
    (141431, "按给定标准分类", "pmath_g1b_l08", 1, BOOK_ID, 141403),
    (141432, "按不同标准分类", "pmath_g1b_l09", 2, BOOK_ID, 141403),

    # 第四单元 100以内数的认识
    (141441, "数数 数的组成", "pmath_g1b_l10", 1, BOOK_ID, 141404),
    (141442, "数的顺序 比较大小", "pmath_g1b_l11", 2, BOOK_ID, 141404),
    (141443, "整十数加一位数及相应的减法", "pmath_g1b_l12", 3, BOOK_ID, 141404),

    # 第五单元 认识人民币
    (141451, "认识人民币", "pmath_g1b_l13", 1, BOOK_ID, 141405),
    (141452, "简单的计算", "pmath_g1b_l14", 2, BOOK_ID, 141405),

    # 第六单元 100以内的加法和减法（一）
    (141461, "整十数加、减整十数", "pmath_g1b_l15", 1, BOOK_ID, 141406),
    (141462, "两位数加一位数、整十数", "pmath_g1b_l16", 2, BOOK_ID, 141406),
    (141463, "两位数减一位数、整十数", "pmath_g1b_l17", 3, BOOK_ID, 141406),
    (141464, "解决问题", "pmath_g1b_l18", 4, BOOK_ID, 141406),
    (141465, "整理和复习", "pmath_g1b_l19", 5, BOOK_ID, 141406),

    # 第七单元 找规律
    (141471, "图形与数字的排列规律", "pmath_g1b_l20", 1, BOOK_ID, 141407),

    # 第八单元 总复习
    (141481, "总复习", "pmath_g1b_l21", 1, BOOK_ID, 141408),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 256001-256008 为册域层，256011-256076 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (256001, "pmath_g1b_domain_u01", "小学数学一下·第一单元 认识平面图形与拼组", 1, SUBJECT, G1, None),
    (256002, "pmath_g1b_domain_u02", "小学数学一下·第二单元 20以内的退位减法", 2, SUBJECT, G1, None),
    (256003, "pmath_g1b_domain_u03", "小学数学一下·第三单元 分类与整理", 3, SUBJECT, G1, None),
    (256004, "pmath_g1b_domain_u04", "小学数学一下·第四单元 100以内数的认识", 4, SUBJECT, G1, None),
    (256005, "pmath_g1b_domain_u05", "小学数学一下·第五单元 认识人民币与购物计算", 5, SUBJECT, G1, None),
    (256006, "pmath_g1b_domain_u06", "小学数学一下·第六单元 100以内的加法和减法（一）", 6, SUBJECT, G1, None),
    (256007, "pmath_g1b_domain_u07", "小学数学一下·第七单元 图形与数字的排列规律", 7, SUBJECT, G1, None),
    (256008, "pmath_g1b_domain_u08", "小学数学一下·第八单元 总复习与综合应用", 8, SUBJECT, G1, None),

    # 第一单元 认识平面图形与拼组
    (256011, "pmath_g1b_point_plane_shape_intro", "从长方体、正方体、圆柱的面上拓印出长方形、正方形、圆，体会“面在体上”", 1, SUBJECT, G1, 256001),
    (256012, "pmath_g1b_point_rectangle", "长方形：长长方方，有4条边、4个角，对边相等，4个角都是直角", 2, SUBJECT, G1, 256001),
    (256013, "pmath_g1b_point_square", "正方形：四四方方，4条边都相等，4个角都是直角，是特殊的长方形", 3, SUBJECT, G1, 256001),
    (256014, "pmath_g1b_point_triangle", "三角形：由3条边围成，有3个角，形状多种多样，具有稳定性", 4, SUBJECT, G1, 256001),
    (256015, "pmath_g1b_point_circle", "圆：由一条曲线围成，没有角，边缘光滑，沿任意方向滚动", 5, SUBJECT, G1, 256001),
    (256016, "pmath_g1b_point_parallelogram", "平行四边形：两组对边分别平行且相等，4个角不都是直角，容易变形", 6, SUBJECT, G1, 256001),
    (256017, "pmath_g1b_point_shape_make", "平面图形的拼组：两个完全一样的三角形可拼成平行四边形、长方形或正方形", 7, SUBJECT, G1, 256001),
    (256018, "pmath_g1b_point_tangram", "七巧板：由5个三角形、1个正方形、1个平行四边形组成，能拼出多种图案", 8, SUBJECT, G1, 256001),
    (256019, "pmath_g1b_point_shape_count_split", "数组合图形中的基本图形要有序点数；会用一条直线把图形分成两个指定的图形", 9, SUBJECT, G1, 256001),

    # 第二单元 20以内的退位减法
    (256021, "pmath_g1b_point_sub9_break", "十几减9的破十法：把十几分成10和几，先用10减9得1，再把1与被减数个位相加", 1, SUBJECT, G1, 256002),
    (256022, "pmath_g1b_point_sub9_think_add", "十几减9的想加算减法：想9加几得被减数，则减9的结果就是那个几", 2, SUBJECT, G1, 256002),
    (256023, "pmath_g1b_point_sub9_rule", "十几减9的规律：得数比被减数个位上的数多1，可用来快速口算和检验", 3, SUBJECT, G1, 256002),
    (256024, "pmath_g1b_point_sub876_break", "十几减8、7、6：用破十法计算，如13-8把13分成10和3，10-8=2，2+3=5", 4, SUBJECT, G1, 256002),
    (256025, "pmath_g1b_point_sub876_flat", "平十法（连减）：把减数分成两个数，先减到10，再减去剩下的数，如12-8=12-2-6", 5, SUBJECT, G1, 256002),
    (256026, "pmath_g1b_point_sub5432", "十几减5、4、3、2：算法迁移，灵活选用破十法或想加算减，正确口算", 6, SUBJECT, G1, 256002),
    (256027, "pmath_g1b_point_sub20_fluency", "20以内退位减法口算：弄清算理、熟练算法，做到正确、迅速、书写规范", 7, SUBJECT, G1, 256002),
    (256028, "pmath_g1b_point_sub_table", "20以内退位减法表：按减数整理排列，横看、竖看、斜看发现得数变化规律", 8, SUBJECT, G1, 256002),
    (256029, "pmath_g1b_point_sub_problem_other", "求另一部分的实际问题：已知总数和其中一部分，求另一部分用减法计算并口答", 9, SUBJECT, G1, 256002),
    (256030, "pmath_g1b_point_sub_extra_condition", "有多余条件的实际问题：读题筛选与问题有关的条件，排除干扰信息再列式", 10, SUBJECT, G1, 256002),
    (256031, "pmath_g1b_point_sub_review", "整理和复习：加减法互为逆运算，可用加法检验退位减法，沟通算式之间的联系", 11, SUBJECT, G1, 256002),

    # 第三单元 分类与整理
    (256032, "pmath_g1b_point_class_one_standard", "按给定标准分类：按形状、颜色或用途等单一标准把物品分组，做到不重不漏", 1, SUBJECT, G1, 256003),
    (256033, "pmath_g1b_point_pictograph", "分类结果的象形统计图：用图形或符号一个对一个地记录各类物品的数量", 2, SUBJECT, G1, 256003),
    (256034, "pmath_g1b_point_class_multi_standard", "按不同标准分类：同一组物品可按颜色、形状等不同标准分，分类结果各不相同", 3, SUBJECT, G1, 256003),
    (256035, "pmath_g1b_point_class_invariant", "分类结果的比较：无论按哪种标准分，各类数量之和都等于物品总数", 4, SUBJECT, G1, 256003),
    (256036, "pmath_g1b_point_stat_table", "简单统计表：把各类数量填入表格，会读表、填表并核对合计", 5, SUBJECT, G1, 256003),
    (256037, "pmath_g1b_point_data_analyze", "根据整理结果回答问题：判断哪类最多、哪类最少、两类相差多少或一共有多少", 6, SUBJECT, G1, 256003),

    # 第四单元 100以内数的认识
    (256038, "pmath_g1b_point_count100", "100以内数的数法：一个一个数、两个两个数、五个五个数、十个十个数，做到不重复不遗漏", 1, SUBJECT, G1, 256004),
    (256039, "pmath_g1b_point_hundred_make", "10个十是一百：一百里面有10个十，100是最大的三位数基础，读写为“一百”", 2, SUBJECT, G1, 256004),
    (256040, "pmath_g1b_point_number_compose", "数的组成：几十几由几个十和几个一组成，如35由3个十和5个一组成", 3, SUBJECT, G1, 256004),
    (256041, "pmath_g1b_point_place_value100", "数位顺序：从右边起第一位是个位、第二位是十位、第三位是百位，计数单位是一、十、百", 4, SUBJECT, G1, 256004),
    (256042, "pmath_g1b_point_read_write100", "100以内数的读写：从高位起按数位读数和写数，中间或末尾有0时正确读写", 5, SUBJECT, G1, 256004),
    (256043, "pmath_g1b_point_hundred_chart", "百数表的顺序规律：横看相邻两数相差1，竖看上下两数相差10，会按规律填数", 6, SUBJECT, G1, 256004),
    (256044, "pmath_g1b_point_compare100", "100以内数的大小比较：先比十位，十位大的数大；十位相同再比个位", 7, SUBJECT, G1, 256004),
    (256045, "pmath_g1b_point_compare_words", "用多得多、多一些、少得多、少一些描述两数大小相差的程度", 8, SUBJECT, G1, 256004),
    (256046, "pmath_g1b_point_ten_plus_one", "整十数加一位数及相应的减法：30+5=35、35-5=30、35-30=5，理解三个算式的关系", 9, SUBJECT, G1, 256004),
    (256047, "pmath_g1b_point_estimate100", "100以内数的估计：借助十个十个地数和参照物，估计物品的大致数量并说明理由", 10, SUBJECT, G1, 256004),

    # 第五单元 认识人民币与购物计算
    (256048, "pmath_g1b_point_rmb_units", "人民币的单位：元、角、分，认识元币、角币、分币及常见面值", 1, SUBJECT, G1, 256005),
    (256049, "pmath_g1b_point_rmb_rate", "元角分的进率：1元=10角，1角=10分，1元=100分", 2, SUBJECT, G1, 256005),
    (256050, "pmath_g1b_point_rmb_recognize", "人民币面值辨认：能认出1元、5元、10元、20元、50元、100元纸币和1角、5角、1元硬币", 3, SUBJECT, G1, 256005),
    (256051, "pmath_g1b_point_rmb_exchange", "人民币的兑换：如1张10元换10张1元，1张100元换10张10元或2张50元", 4, SUBJECT, G1, 256005),
    (256052, "pmath_g1b_point_rmb_add_same", "相同单位的人民币计算：几元加几元、几角加几角，单位不变直接相加减", 5, SUBJECT, G1, 256005),
    (256053, "pmath_g1b_point_rmb_convert", "人民币单位换算：1元2角=12角，15角=1元5角，先统一单位再计算", 6, SUBJECT, G1, 256005),
    (256054, "pmath_g1b_point_rmb_shopping", "购物中的付钱与找钱：应付钱数用加法求，找回钱数用“付出钱数-应付钱数”计算", 7, SUBJECT, G1, 256005),
    (256055, "pmath_g1b_point_rmb_pay_plan", "合理付钱方案：根据商品价格选择合适面值的人民币组合付款，并检验金额是否足够", 8, SUBJECT, G1, 256005),

    # 第六单元 100以内的加法和减法（一）
    (256056, "pmath_g1b_point_ten_add_ten", "整十数加整十数：20+30，2个十加3个十是5个十，结果是50", 1, SUBJECT, G1, 256006),
    (256057, "pmath_g1b_point_ten_sub_ten", "整十数减整十数：50-20，5个十减2个十是3个十，结果是30", 2, SUBJECT, G1, 256006),
    (256058, "pmath_g1b_point_two_add_one_nocarry", "两位数加一位数（不进位）：个位相加、十位不变，如23+4=27", 3, SUBJECT, G1, 256006),
    (256059, "pmath_g1b_point_two_add_ten", "两位数加整十数：十位相加、个位不变，如23+40=63", 4, SUBJECT, G1, 256006),
    (256060, "pmath_g1b_point_two_add_one_carry", "两位数加一位数（进位）：先把个位相加，满十向十位进1，如28+5=33", 5, SUBJECT, G1, 256006),
    (256061, "pmath_g1b_point_two_sub_one_noborrow", "两位数减一位数（不退位）：个位相减、十位不变，如35-4=31", 6, SUBJECT, G1, 256006),
    (256062, "pmath_g1b_point_two_sub_ten", "两位数减整十数：十位相减、个位不变，如35-20=15", 7, SUBJECT, G1, 256006),
    (256063, "pmath_g1b_point_two_sub_one_borrow", "两位数减一位数（退位）：个位不够减时从十位退1当十，如32-5=27", 8, SUBJECT, G1, 256006),
    (256064, "pmath_g1b_point_problem_repeat_add", "同数连加的实际问题：如每盒装6个、共3盒，用连加或乘法雏形求总数", 9, SUBJECT, G1, 256006),
    (256065, "pmath_g1b_point_problem_repeat_sub", "减去相同数的实际问题：如28个橘子每9个装一袋，用连续减法求能装满几袋", 10, SUBJECT, G1, 256006),
    (256066, "pmath_g1b_point_addsub100_review", "整理和复习：100以内加减法口算方法梳理，理解加减法关系和算法多样化", 11, SUBJECT, G1, 256006),

    # 第七单元 图形与数字的排列规律
    (256067, "pmath_g1b_point_pattern_shape", "图形排列规律：按颜色、形状、大小的重复排列寻找规律，找出重复出现的一组", 1, SUBJECT, G1, 256007),
    (256068, "pmath_g1b_point_pattern_number", "数字排列规律：数列中相邻两数的差保持不变，或按一定规律递增、递减", 2, SUBJECT, G1, 256007),
    (256069, "pmath_g1b_point_pattern_describe", "规律的描述：用“几个一组、重复出现”说清规律，确定循环单位与顺序", 3, SUBJECT, G1, 256007),
    (256070, "pmath_g1b_point_pattern_continue", "续写规律：根据已有排列接着画图形、接着填数，保证与前面规律一致", 4, SUBJECT, G1, 256007),
    (256071, "pmath_g1b_point_pattern_problem", "找规律解决问题：综合图形与数字规律，推断被遮挡或缺失的部分并说明依据", 5, SUBJECT, G1, 256007),

    # 第八单元 总复习与综合应用
    (256072, "pmath_g1b_point_review_number100", "100以内数的认识复习：数位顺序、数的组成、读写、顺序与大小比较综合梳理", 1, SUBJECT, G1, 256008),
    (256073, "pmath_g1b_point_review_calc100", "100以内加减法复习：整十数加减、两位数加减一位数或整十数的口算与检验", 2, SUBJECT, G1, 256008),
    (256074, "pmath_g1b_point_review_shape", "认识图形复习：长方形、正方形、三角形、圆、平行四边形的特征与拼组", 3, SUBJECT, G1, 256008),
    (256075, "pmath_g1b_point_review_rmb_class", "人民币与分类整理复习：元角分换算、购物计算、按标准分类与统计表", 4, SUBJECT, G1, 256008),
    (256076, "pmath_g1b_point_review_problem", "综合解决问题的步骤：读题、找条件和问题、分析数量关系、列式计算、检验并口答", 5, SUBJECT, G1, 256008),
)

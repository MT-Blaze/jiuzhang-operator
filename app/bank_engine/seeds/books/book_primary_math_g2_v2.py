"""人教版小学数学二年级下册：十个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G2 = 2
BOOK_ID = 1416

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学二年级下册",
    "pmath_g2b",
    16,
    "人民教育出版社",
    SUBJECT,
    G2,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 十个单元
    (141601, "第一单元 数据收集整理", "pmath_g2b_u01", 1, BOOK_ID, None),
    (141602, "第二单元 表内除法（一）", "pmath_g2b_u02", 2, BOOK_ID, None),
    (141603, "第三单元 图形的运动（一）", "pmath_g2b_u03", 3, BOOK_ID, None),
    (141604, "第四单元 表内除法（二）", "pmath_g2b_u04", 4, BOOK_ID, None),
    (141605, "第五单元 混合运算", "pmath_g2b_u05", 5, BOOK_ID, None),
    (141606, "第六单元 有余数的除法", "pmath_g2b_u06", 6, BOOK_ID, None),
    (141607, "第七单元 万以内数的认识", "pmath_g2b_u07", 7, BOOK_ID, None),
    (141608, "第八单元 克和千克", "pmath_g2b_u08", 8, BOOK_ID, None),
    (141609, "第九单元 数学广角——推理", "pmath_g2b_u09", 9, BOOK_ID, None),
    (141610, "第十单元 总复习", "pmath_g2b_u10", 10, BOOK_ID, None),

    # 第一单元 数据收集整理
    (141611, "调查与记录", "pmath_g2b_l01", 1, BOOK_ID, 141601),
    (141612, "统计表", "pmath_g2b_l02", 2, BOOK_ID, 141601),

    # 第二单元 表内除法（一）
    (141621, "平均分", "pmath_g2b_l03", 1, BOOK_ID, 141602),
    (141622, "除法", "pmath_g2b_l04", 2, BOOK_ID, 141602),
    (141623, "用2~6的乘法口诀求商", "pmath_g2b_l05", 3, BOOK_ID, 141602),
    (141624, "解决问题", "pmath_g2b_l06", 4, BOOK_ID, 141602),
    (141625, "整理和复习", "pmath_g2b_l07", 5, BOOK_ID, 141602),

    # 第三单元 图形的运动（一）
    (141631, "轴对称图形", "pmath_g2b_l08", 1, BOOK_ID, 141603),
    (141632, "平移", "pmath_g2b_l09", 2, BOOK_ID, 141603),
    (141633, "旋转", "pmath_g2b_l10", 3, BOOK_ID, 141603),

    # 第四单元 表内除法（二）
    (141641, "用7、8、9的乘法口诀求商", "pmath_g2b_l11", 1, BOOK_ID, 141604),
    (141642, "解决问题", "pmath_g2b_l12", 2, BOOK_ID, 141604),
    (141643, "整理和复习", "pmath_g2b_l13", 3, BOOK_ID, 141604),

    # 第五单元 混合运算
    (141651, "同级运算", "pmath_g2b_l14", 1, BOOK_ID, 141605),
    (141652, "两级运算", "pmath_g2b_l15", 2, BOOK_ID, 141605),
    (141653, "有小括号的运算", "pmath_g2b_l16", 3, BOOK_ID, 141605),
    (141654, "解决问题", "pmath_g2b_l17", 4, BOOK_ID, 141605),
    (141655, "整理和复习", "pmath_g2b_l18", 5, BOOK_ID, 141605),

    # 第六单元 有余数的除法
    (141661, "有余数除法的意义", "pmath_g2b_l19", 1, BOOK_ID, 141606),
    (141662, "余数与除数的关系", "pmath_g2b_l20", 2, BOOK_ID, 141606),
    (141663, "竖式计算", "pmath_g2b_l21", 3, BOOK_ID, 141606),
    (141664, "解决问题", "pmath_g2b_l22", 4, BOOK_ID, 141606),
    (141665, "整理和复习", "pmath_g2b_l23", 5, BOOK_ID, 141606),

    # 第七单元 万以内数的认识
    (141671, "1000以内数的认识", "pmath_g2b_l24", 1, BOOK_ID, 141607),
    (141672, "10000以内数的认识", "pmath_g2b_l25", 2, BOOK_ID, 141607),
    (141673, "整百整千数加减法", "pmath_g2b_l26", 3, BOOK_ID, 141607),

    # 第八单元 克和千克
    (141681, "认识克与千克", "pmath_g2b_l27", 1, BOOK_ID, 141608),
    (141682, "单位换算", "pmath_g2b_l28", 2, BOOK_ID, 141608),

    # 第九单元 数学广角——推理
    (141691, "简单推理", "pmath_g2b_l29", 1, BOOK_ID, 141609),

    # 第十单元 总复习
    (141692, "总复习", "pmath_g2b_l30", 1, BOOK_ID, 141610),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 258001-258010 为册域层，258011-258085 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (258001, "pmath_g2b_domain_u01", "小学数学二下·第一单元 数据收集整理", 1, SUBJECT, G2, None),
    (258002, "pmath_g2b_domain_u02", "小学数学二下·第二单元 表内除法（一）", 2, SUBJECT, G2, None),
    (258003, "pmath_g2b_domain_u03", "小学数学二下·第三单元 图形的运动（一）", 3, SUBJECT, G2, None),
    (258004, "pmath_g2b_domain_u04", "小学数学二下·第四单元 表内除法（二）", 4, SUBJECT, G2, None),
    (258005, "pmath_g2b_domain_u05", "小学数学二下·第五单元 混合运算", 5, SUBJECT, G2, None),
    (258006, "pmath_g2b_domain_u06", "小学数学二下·第六单元 有余数的除法", 6, SUBJECT, G2, None),
    (258007, "pmath_g2b_domain_u07", "小学数学二下·第七单元 万以内数的认识", 7, SUBJECT, G2, None),
    (258008, "pmath_g2b_domain_u08", "小学数学二下·第八单元 克和千克", 8, SUBJECT, G2, None),
    (258009, "pmath_g2b_domain_u09", "小学数学二下·第九单元 数学广角——推理", 9, SUBJECT, G2, None),
    (258010, "pmath_g2b_domain_u10", "小学数学二下·第十单元 总复习与综合应用", 10, SUBJECT, G2, None),

    # 第一单元 数据收集整理
    (258011, "pmath_g2b_point_survey_method", "调查方法的种类：全班调查可用举手、投票或发放问卷，人数多或不便集中时用问卷", 1, SUBJECT, G2, 258001),
    (258012, "pmath_g2b_point_record_tally", "用画正字记录数据：一笔代表1个，每个“正”字5笔，数正字笔画即得数据个数", 2, SUBJECT, G2, 258001),
    (258013, "pmath_g2b_point_record_symbol", "用符号记录数据：用打√、画○或写数字逐项记录，边数边记，避免重复和遗漏", 3, SUBJECT, G2, 258001),
    (258014, "pmath_g2b_point_table_structure", "统计表的结构：表头写明项目，第一行是类别，第二行是人数或数量，最后可加合计一栏", 4, SUBJECT, G2, 258001),
    (258015, "pmath_g2b_point_table_read", "从统计表读取信息：比较各栏数量多少，找出最多和最少，算出相差多少", 5, SUBJECT, G2, 258001),
    (258016, "pmath_g2b_point_table_decide", "根据统计结果作判断：依据数据多少提出建议或作出决定，如多准备最受欢迎的水果", 6, SUBJECT, G2, 258001),

    # 第二单元 表内除法（一）
    (258017, "pmath_g2b_point_average_meaning", "平均分的含义：把一些物品分成若干份，每份分得同样多，叫做平均分", 1, SUBJECT, G2, 258002),
    (258018, "pmath_g2b_point_average_by_parts", "按指定的份数平均分：知道分成几份，可以一份一份地分或几个几个地分，直到分完", 2, SUBJECT, G2, 258002),
    (258019, "pmath_g2b_point_average_by_each", "按每份的个数平均分：知道每份放几个，一份一份地拿，看能分成几份，剩下的不能再分", 3, SUBJECT, G2, 258002),
    (258020, "pmath_g2b_point_average_to_divide", "平均分用除法表示：把12个平均分成3份，每份4个，写作12÷3=4，读作12除以3等于4", 4, SUBJECT, G2, 258002),
    (258021, "pmath_g2b_point_divide_parts", "除法算式各部分名称：被除数÷除数=商，“÷”是除号，被除数是要分的总数，除数是份数或每份数", 5, SUBJECT, G2, 258002),
    (258022, "pmath_g2b_point_divide_read", "除法算式的读法与写法：从左往右读作“几除以几等于几”，书写时除号是横线上下各一点", 6, SUBJECT, G2, 258002),
    (258023, "pmath_g2b_point_divide_by_table", "用2~6的乘法口诀求商：想“除数×几=被除数”，如12÷3想三四十二，商是4", 7, SUBJECT, G2, 258002),
    (258024, "pmath_g2b_point_one_rhyme_divide", "一句口诀算两道除法：如“三四十二”可算12÷3=4和12÷4=3，看被除数和除数想口诀", 8, SUBJECT, G2, 258002),
    (258025, "pmath_g2b_point_multiply_divide_relation", "乘除法之间的关系：乘法算式中的积是除法中的被除数，两个因数分别是除数和商", 9, SUBJECT, G2, 258002),
    (258026, "pmath_g2b_point_divide_equal_share", "等分除的实际问题：已知总数和份数求每份数，用总数÷份数=每份数，如15÷5=3", 10, SUBJECT, G2, 258002),
    (258027, "pmath_g2b_point_divide_grouping", "包含除的实际问题：已知总数和每份数求份数，用总数÷每份数=份数，如15个每5个一份可分成3份", 11, SUBJECT, G2, 258002),
    (258028, "pmath_g2b_point_divide_review1", "表内除法（一）整理复习：平均分的两种分法、除法算式各部分名称、用2~6口诀求商的熟练运用", 12, SUBJECT, G2, 258002),

    # 第三单元 图形的运动（一）
    (258029, "pmath_g2b_point_symmetry_feature", "轴对称图形的特征：沿一条直线对折后两边完全重合，这样的图形叫轴对称图形", 1, SUBJECT, G2, 258003),
    (258030, "pmath_g2b_point_symmetry_axis", "对称轴的认识：对折时的折痕所在的直线就是对称轴，有的图形有一条，有的有多条", 2, SUBJECT, G2, 258003),
    (258031, "pmath_g2b_point_symmetry_judge", "判断轴对称图形：先想象对折，再实际折一折，两边能完全重合才是轴对称图形", 3, SUBJECT, G2, 258003),
    (258032, "pmath_g2b_point_symmetry_cut", "剪轴对称图形：把纸对折，沿折痕一侧画出半个图形再剪开，展开后得到完整的轴对称图形", 4, SUBJECT, G2, 258003),
    (258033, "pmath_g2b_point_translate_feature", "平移的特征：物体沿直线移动，方向不变，形状、大小都不改变，只是位置变了", 5, SUBJECT, G2, 258003),
    (258034, "pmath_g2b_point_translate_judge", "平移的判断：电梯上下、推拉窗左右移动都是平移，移动路线是直的", 6, SUBJECT, G2, 258003),
    (258035, "pmath_g2b_point_rotate_feature", "旋转的特征：物体绕一个点或一条轴转动，如风车、钟表指针的转动，形状大小不变", 7, SUBJECT, G2, 258003),
    (258036, "pmath_g2b_point_translate_vs_rotate", "平移与旋转的区别：平移是沿直线移动不转向，旋转是绕点或轴转动，方向发生改变", 8, SUBJECT, G2, 258003),

    # 第四单元 表内除法（二）
    (258037, "pmath_g2b_point_divide_table7", "用7的乘法口诀求商：想七几得被除数，如42÷7想六七四十二，商是6", 1, SUBJECT, G2, 258004),
    (258038, "pmath_g2b_point_divide_table8", "用8的乘法口诀求商：如56÷8想七八五十六，商是7，注意一句口诀对应两道除法", 2, SUBJECT, G2, 258004),
    (258039, "pmath_g2b_point_divide_table9", "用9的乘法口诀求商：如63÷9想七九六十三，商是7，可用9的口诀规律检查", 3, SUBJECT, G2, 258004),
    (258040, "pmath_g2b_point_divide_quick", "除法的口算与想口诀：看除法算式先想“除数×几=被除数”，把口诀背熟可提高速度", 4, SUBJECT, G2, 258004),
    (258041, "pmath_g2b_point_times_divide", "求一个数是另一个数的几倍：用除法，如12是3的几倍，列式12÷3=4", 5, SUBJECT, G2, 258004),
    (258042, "pmath_g2b_point_times_problem2", "倍的实际问题（二）：已知两个数量求倍数用除法，已知1倍数和倍数求几倍数用乘法", 6, SUBJECT, G2, 258004),
    (258043, "pmath_g2b_point_divide_problem_steps", "用除法解决问题的步骤：读题找总数和份数、判断是等分还是包含、列式并检验", 7, SUBJECT, G2, 258004),
    (258044, "pmath_g2b_point_divide_review2", "表内除法（二）整理复习：熟练用7~9口诀求商，用除法解决求倍数与平均分问题", 8, SUBJECT, G2, 258004),

    # 第五单元 混合运算
    (258045, "pmath_g2b_point_same_level", "同级运算的运算顺序：只有加减或只有乘除时，从左到右依次计算", 1, SUBJECT, G2, 258005),
    (258046, "pmath_g2b_point_two_level", "两级运算的运算顺序：既有乘除又有加减时，先算乘除，再算加减", 2, SUBJECT, G2, 258005),
    (258047, "pmath_g2b_point_parentheses_role", "小括号的作用：小括号能改变运算顺序，先算小括号里面的", 3, SUBJECT, G2, 258005),
    (258048, "pmath_g2b_point_two_level_parentheses", "含小括号的两级运算：不管括号里是加减还是乘除，都先算括号里的，再算括号外的", 4, SUBJECT, G2, 258005),
    (258049, "pmath_g2b_point_step_calc_format", "脱式计算的书写格式：每算一步写一行，等号对齐，没参与计算的部分照抄下来", 5, SUBJECT, G2, 258005),
    (258050, "pmath_g2b_point_two_step_problem", "用两步计算解决实际问题：先想先求什么，再求什么，必要时用小括号保证先算部分", 6, SUBJECT, G2, 258005),
    (258051, "pmath_g2b_point_mix_review", "混合运算整理复习：同级从左到右、先乘除后加减、有括号先算括号里的三条规则", 7, SUBJECT, G2, 258005),

    # 第六单元 有余数的除法
    (258052, "pmath_g2b_point_remainder_meaning", "有余数除法的意义：平均分物品时不能正好分完，剩下的不够再分一份，剩下的数叫余数", 1, SUBJECT, G2, 258006),
    (258053, "pmath_g2b_point_remainder_symbol", "余数的表示：有余数的除法用“……”连接，如7÷2=3……1，读作7除以2商3余1", 2, SUBJECT, G2, 258006),
    (258054, "pmath_g2b_point_remainder_less", "余数与除数的关系：余数必须比除数小，余数等于或大于除数说明还能再分，商算错了", 3, SUBJECT, G2, 258006),
    (258055, "pmath_g2b_point_remainder_vertical", "有余数除法的竖式：被除数写在里面，除数写在左边，商写在上面，商乘除数的积写在被除数下面，差就是余数", 4, SUBJECT, G2, 258006),
    (258056, "pmath_g2b_point_trial_quotient", "试商的方法：想除数乘几最接近被除数又不超过它，那个几就是商，再算余数", 5, SUBJECT, G2, 258006),
    (258057, "pmath_g2b_point_remainder_check", "有余数除法的验算：商×除数+余数=被除数，用这个方法检查计算是否正确", 6, SUBJECT, G2, 258006),
    (258058, "pmath_g2b_point_remainder_problem", "解决“最多”“至少”问题：装袋、租船等问题按余数判断是进一还是舍去，如坐船有余数要再加一条船", 7, SUBJECT, G2, 258006),
    (258059, "pmath_g2b_point_remainder_unit", "余数的实际含义：余数的单位和被除数相同，表示剩下不够再分的数量，答语要写清楚", 8, SUBJECT, G2, 258006),
    (258060, "pmath_g2b_point_remainder_review", "有余数除法整理复习：余数小于除数、竖式计算、验算和解决实际问题的方法", 9, SUBJECT, G2, 258006),

    # 第七单元 万以内数的认识
    (258061, "pmath_g2b_point_count_1000", "1000以内数的数数：一个一个数、一十一十数、一百一百数，数到拐弯处注意进位", 1, SUBJECT, G2, 258007),
    (258062, "pmath_g2b_point_compose_1000", "1000以内数的组成：由几个百、几个十和几个一组成，如356是3个百、5个十和6个一", 2, SUBJECT, G2, 258007),
    (258063, "pmath_g2b_point_read_1000", "1000以内数的读法：从高位读起，百位是几读几百，中间有0读零，末尾的0不读", 3, SUBJECT, G2, 258007),
    (258064, "pmath_g2b_point_write_1000", "1000以内数的写法：从高位写起，哪一位上一个单位也没有就写0占位", 4, SUBJECT, G2, 258007),
    (258065, "pmath_g2b_point_place_order", "数位顺序表：从右起依次是个位、十位、百位、千位、万位，每相邻两个数位间的进率是10", 5, SUBJECT, G2, 258007),
    (258066, "pmath_g2b_point_compose_10000", "10000以内数的组成：由几个千、几个百、几个十和几个一组成，如2408是2个千、4个百和8个一", 6, SUBJECT, G2, 258007),
    (258067, "pmath_g2b_point_read_10000", "10000以内数的读法：中间有一个0或两个0都只读一个零，末尾的0都不读", 7, SUBJECT, G2, 258007),
    (258068, "pmath_g2b_point_write_10000", "10000以内数的写法：中间或末尾哪一位没有单位就写0，0不能漏写也不能多写", 8, SUBJECT, G2, 258007),
    (258069, "pmath_g2b_point_compare_10000", "万以内数的大小比较：位数多的数大；位数相同从最高位比起，最高位相同再比下一位", 9, SUBJECT, G2, 258007),
    (258070, "pmath_g2b_point_approximate", "近似数：与准确数接近的整十、整百、整千数，如998约是1000，用“≈”表示", 10, SUBJECT, G2, 258007),
    (258071, "pmath_g2b_point_add_sub_hundred", "整百整千数的加减法：先去掉末尾的0，用一位数加减法计算，再在得数末尾添上相同个数的0", 11, SUBJECT, G2, 258007),
    (258072, "pmath_g2b_point_estimate_10000", "万以内数的估算：把数看成接近的整百或整千数再计算，结果用“≈”并说明估算理由", 12, SUBJECT, G2, 258007),

    # 第八单元 克和千克
    (258073, "pmath_g2b_point_gram", "克的认识：计量较轻物品用克作单位，用字母g表示，1枚2分硬币约重1克", 1, SUBJECT, G2, 258008),
    (258074, "pmath_g2b_point_balance", "用天平称物品：天平平衡时砝码的总质量就是物品的质量，可称较轻的小物品", 2, SUBJECT, G2, 258008),
    (258075, "pmath_g2b_point_kilogram", "千克的认识：计量较重物品用千克作单位，用字母kg表示，1袋食盐重约500克，2袋约1千克", 3, SUBJECT, G2, 258008),
    (258076, "pmath_g2b_point_kg_g_convert", "克与千克的换算：1千克=1000克，3千克=3000克，2000克=2千克", 4, SUBJECT, G2, 258008),
    (258077, "pmath_g2b_point_mass_choose", "质量单位的选择与估测：先估计物品轻重再选克或千克，如一个苹果约200克、一袋大米约25千克", 5, SUBJECT, G2, 258008),

    # 第九单元 数学广角——推理
    (258078, "pmath_g2b_point_exclusion", "排除法推理：由“不是……就是……”逐条排除不可能的情况，剩下的就是答案", 1, SUBJECT, G2, 258009),
    (258079, "pmath_g2b_point_inference_grid", "连线与列表辅助推理：把人物和物品分列两行，用连线或打√打×记录确定与排除的信息", 2, SUBJECT, G2, 258009),
    (258080, "pmath_g2b_point_inference_express", "有条理地表达推理过程：先确定最容易判断的一条，再逐步推出其余结果，说清每一步依据", 3, SUBJECT, G2, 258009),

    # 第十单元 总复习与综合应用
    (258081, "pmath_g2b_point_review_number", "数与运算总复习：表内除法、混合运算顺序、有余数除法的竖式与验算、万以内数的读写与比较", 1, SUBJECT, G2, 258010),
    (258082, "pmath_g2b_point_review_shape", "图形与运动总复习：轴对称图形的判断与对称轴、平移和旋转的特征及区别", 2, SUBJECT, G2, 258010),
    (258083, "pmath_g2b_point_review_stat_mass", "统计与质量单位总复习：调查记录与统计表的填写分析、克和千克的认识与换算", 3, SUBJECT, G2, 258010),
    (258084, "pmath_g2b_point_review_strategy", "综合解决问题的策略：读题圈条件与问题、分析数量关系、选择算法、检验并写完整答语", 4, SUBJECT, G2, 258010),
    (258085, "pmath_g2b_point_review_check", "易错点回顾与检查习惯：余数要比除数小、0的读写不漏写、运算顺序不颠倒，做完要复查", 5, SUBJECT, G2, 258010),
)

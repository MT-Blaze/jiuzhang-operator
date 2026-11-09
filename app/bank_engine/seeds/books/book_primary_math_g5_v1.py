"""人教版小学数学五年级上册：八个单元、课时树与细颗粒知识点。"""

from __future__ import annotations

SUBJECT = 2
G5 = 5
BOOK_ID = 1421

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版小学数学五年级上册",
    "pmath_g5a",
    21,
    "人民教育出版社",
    SUBJECT,
    G5,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 八个单元
    (142101, "第一单元 小数乘法", "pmath_g5a_u01", 1, BOOK_ID, None),
    (142107, "第二单元 位置", "pmath_g5a_u02", 2, BOOK_ID, None),
    (142109, "第三单元 小数除法", "pmath_g5a_u03", 3, BOOK_ID, None),
    (142116, "第四单元 可能性", "pmath_g5a_u04", 4, BOOK_ID, None),
    (142118, "第五单元 简易方程", "pmath_g5a_u05", 5, BOOK_ID, None),
    (142123, "第六单元 多边形的面积", "pmath_g5a_u06", 6, BOOK_ID, None),
    (142128, "第七单元 数学广角——植树问题", "pmath_g5a_u07", 7, BOOK_ID, None),
    (142130, "第八单元 总复习", "pmath_g5a_u08", 8, BOOK_ID, None),

    # 第一单元 小数乘法
    (142102, "小数乘整数", "pmath_g5a_l01", 1, BOOK_ID, 142101),
    (142103, "小数乘小数", "pmath_g5a_l02", 2, BOOK_ID, 142101),
    (142104, "积的近似数", "pmath_g5a_l03", 3, BOOK_ID, 142101),
    (142105, "整数乘法运算定律推广到小数", "pmath_g5a_l04", 4, BOOK_ID, 142101),
    (142106, "解决问题", "pmath_g5a_l05", 5, BOOK_ID, 142101),

    # 第二单元 位置
    (142108, "用数对表示位置", "pmath_g5a_l06", 1, BOOK_ID, 142107),

    # 第三单元 小数除法
    (142110, "除数是整数的小数除法", "pmath_g5a_l07", 1, BOOK_ID, 142109),
    (142111, "一个数除以小数", "pmath_g5a_l08", 2, BOOK_ID, 142109),
    (142112, "商的近似数", "pmath_g5a_l09", 3, BOOK_ID, 142109),
    (142113, "循环小数", "pmath_g5a_l10", 4, BOOK_ID, 142109),
    (142114, "用计算器探索规律", "pmath_g5a_l11", 5, BOOK_ID, 142109),
    (142115, "解决问题", "pmath_g5a_l12", 6, BOOK_ID, 142109),

    # 第四单元 可能性
    (142117, "事件发生的可能性", "pmath_g5a_l13", 1, BOOK_ID, 142116),

    # 第五单元 简易方程
    (142119, "用字母表示数", "pmath_g5a_l14", 1, BOOK_ID, 142118),
    (142120, "方程的意义", "pmath_g5a_l15", 2, BOOK_ID, 142118),
    (142121, "解方程", "pmath_g5a_l16", 3, BOOK_ID, 142118),
    (142122, "实际问题与方程", "pmath_g5a_l17", 4, BOOK_ID, 142118),

    # 第六单元 多边形的面积
    (142124, "平行四边形的面积", "pmath_g5a_l18", 1, BOOK_ID, 142123),
    (142125, "三角形的面积", "pmath_g5a_l19", 2, BOOK_ID, 142123),
    (142126, "梯形的面积", "pmath_g5a_l20", 3, BOOK_ID, 142123),
    (142127, "组合图形的面积", "pmath_g5a_l21", 4, BOOK_ID, 142123),

    # 第七单元 数学广角——植树问题
    (142129, "植树问题", "pmath_g5a_l22", 1, BOOK_ID, 142128),

    # 第八单元 总复习
    (142131, "总复习", "pmath_g5a_l23", 1, BOOK_ID, 142130),
)

# id / code / name / sort_order / subject_id / parent_id
# 263001-263008 为册域层，263009-263087 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (263001, "pmath_g5a_domain_u01", "小学数学五上·第一单元 小数乘法", 1, SUBJECT, None),
    (263002, "pmath_g5a_domain_u02", "小学数学五上·第二单元 位置", 2, SUBJECT, None),
    (263003, "pmath_g5a_domain_u03", "小学数学五上·第三单元 小数除法", 3, SUBJECT, None),
    (263004, "pmath_g5a_domain_u04", "小学数学五上·第四单元 可能性", 4, SUBJECT, None),
    (263005, "pmath_g5a_domain_u05", "小学数学五上·第五单元 简易方程", 5, SUBJECT, None),
    (263006, "pmath_g5a_domain_u06", "小学数学五上·第六单元 多边形的面积", 6, SUBJECT, None),
    (263007, "pmath_g5a_domain_u07", "小学数学五上·第七单元 数学广角——植树问题", 7, SUBJECT, None),
    (263008, "pmath_g5a_domain_u08", "小学数学五上·第八单元 总复习", 8, SUBJECT, None),

    # 第一单元 小数乘法
    (263009, "pmath_g5a_point_mul_int_meaning", "小数乘整数的意义：求几个相同小数的和的简便运算，与整数乘法意义相同，如0.8×3表示3个0.8相加", 1, SUBJECT, 263001),
    (263010, "pmath_g5a_point_mul_int_reason", "小数乘整数的算理：先把小数扩大到原来的若干倍看成整数乘，积再缩小到原来的几分之一", 2, SUBJECT, 263001),
    (263011, "pmath_g5a_point_mul_int_vertical", "小数乘整数的竖式：按整数乘法算出积，看因数中有几位小数，就从积的右边起数出几位点上小数点", 3, SUBJECT, 263001),
    (263012, "pmath_g5a_point_mul_decimal_rule", "小数乘小数的计算方法：先按整数乘法算出积，再看两个因数中一共有几位小数，就从积的右边起数出几位点小数点", 4, SUBJECT, 263001),
    (263013, "pmath_g5a_point_product_digits", "积的小数位数：两个因数中一共有几位小数，积就有几位小数，积末尾的0可以去掉但计数位数时先按原位数对齐", 5, SUBJECT, 263001),
    (263014, "pmath_g5a_point_product_pad_zero", "积的小数位数不够：积的小数位数不够时，要在积的前面用0补足再点小数点，如0.02×0.03=0.0006", 6, SUBJECT, 263001),
    (263015, "pmath_g5a_point_mul_compare", "因数与积的大小关系：一个数（0除外）乘大于1的数积比原数大，乘小于1的数积比原数小，乘1积不变", 7, SUBJECT, 263001),
    (263016, "pmath_g5a_point_mul_check", "小数乘法的验算：交换两个因数的位置再乘一遍，或用积除以一个因数看是否等于另一个因数", 8, SUBJECT, 263001),
    (263017, "pmath_g5a_point_product_approx", "积的近似数：先算出准确积，再用四舍五入法保留指定小数位数，保留两位小数要看千分位上的数", 9, SUBJECT, 263001),
    (263018, "pmath_g5a_point_mul_laws", "整数乘法运算定律推广到小数：乘法交换律、结合律、分配律对小数乘法同样适用，字母表示形式不变", 10, SUBJECT, 263001),
    (263019, "pmath_g5a_point_mul_simplify", "小数乘法的简便计算：把2.5×4、0.125×8、0.25×4凑成整数，分配律逆用提取相同因数，如0.25×36+0.25×4", 11, SUBJECT, 263001),
    (263020, "pmath_g5a_point_mul_solve", "小数乘法解决问题：先估算判断结果范围，再精确计算；水费电费、分段计费类问题要分段计算后相加", 12, SUBJECT, 263001),

    # 第二单元 位置
    (263021, "pmath_g5a_point_row_column", "列与行的规定：竖排叫列，从前往后数；横排叫行，从左往右数；确定位置时先说列再说行", 1, SUBJECT, 263002),
    (263022, "pmath_g5a_point_number_pair", "数对的含义：用一对有序数（列，行）表示位置，如（3，5）表示第3列第5行，两个数不能交换", 2, SUBJECT, 263002),
    (263023, "pmath_g5a_point_locate_by_pair", "根据数对找位置：在方格纸上先找到对应的列，再找到对应的行，列与行的交点就是所表示的位置", 3, SUBJECT, 263002),
    (263024, "pmath_g5a_point_same_column_row", "同行同列的数对特征：同一列各点数对的第一个数相同，同一行各点数对的第二个数相同", 4, SUBJECT, 263002),
    (263025, "pmath_g5a_point_pair_translate", "数对与平移：列数变大表示向右平移，行数变大表示向上平移，平移几格对应数对就加几", 5, SUBJECT, 263002),
    (263026, "pmath_g5a_point_pair_shape", "数对与图形：用数对表示多边形各顶点位置，按顺序连线可还原图形，并可判断图形是否为长方形或平行四边形", 6, SUBJECT, 263002),

    # 第三单元 小数除法
    (263027, "pmath_g5a_point_div_int_align", "除数是整数的小数除法：按整数除法的方法去除，商的小数点要与被除数的小数点对齐", 1, SUBJECT, 263003),
    (263028, "pmath_g5a_point_div_int_remainder", "除到被除数末尾仍有余数：在余数后面添0继续除，商的小数点位置不变，如5÷4=1.25", 2, SUBJECT, 263003),
    (263029, "pmath_g5a_point_div_less_one", "整数部分不够商1：被除数比除数小时，商的整数部分写0，点上小数点后继续除，如1.2÷5=0.24", 3, SUBJECT, 263003),
    (263030, "pmath_g5a_point_div_decimal_int", "一个数除以小数：先利用商不变性质把除数变成整数，被除数同时扩大相同的倍数", 4, SUBJECT, 263003),
    (263031, "pmath_g5a_point_quotient_property", "商不变性质：被除数和除数同时乘或除以相同的数（0除外），商不变，这是转化除数为整数的依据", 5, SUBJECT, 263003),
    (263032, "pmath_g5a_point_div_decimal_digits", "除数转化时被除数位数不够：被除数的小数位数比除数少时，要用0补足再移动小数点，如1.2÷0.15", 6, SUBJECT, 263003),
    (263033, "pmath_g5a_point_quotient_approx", "商的近似数：除到比需要保留的小数位数多一位，再用四舍五入法取近似数，保留两位小数要除到千分位", 7, SUBJECT, 263003),
    (263034, "pmath_g5a_point_circular_decimal", "循环小数的意义：一个数的小数部分从某一位起，一个或几个数字依次不断重复出现，这样的小数叫循环小数", 8, SUBJECT, 263003),
    (263035, "pmath_g5a_point_circular_section", "循环节与简便记法：循环小数中依次不断重复出现的数字叫循环节，写时在循环节首末两位数字上各点一个圆点", 9, SUBJECT, 263003),
    (263036, "pmath_g5a_point_finite_infinite", "有限小数与无限小数：小数位数有限的是有限小数，位数无限的是无限小数，循环小数属于无限小数", 10, SUBJECT, 263003),
    (263037, "pmath_g5a_point_decimal_compare_div", "循环小数的大小比较：先把循环小数多写出几位再比较，不能只看循环节长短，如0.3·与0.33的大小", 11, SUBJECT, 263003),
    (263038, "pmath_g5a_point_calculator_pattern", "用计算器探索规律：先依次计算几道题，观察得数的变化规律，再用规律直接写出后面各题的结果", 12, SUBJECT, 263003),
    (263039, "pmath_g5a_point_div_solve", "小数除法的实际应用：根据实际需要取整数结果，装物品用进一法，做衣服用去尾法，不能一律四舍五入", 13, SUBJECT, 263003),

    # 第四单元 可能性
    (263040, "pmath_g5a_point_certain_impossible", "事件的确定性：“一定”表示必然发生，“不可能”表示绝不会发生，二者都是确定事件", 1, SUBJECT, 263004),
    (263041, "pmath_g5a_point_possible", "事件的不确定性：“可能”表示有时发生有时不发生，结果不止一种时用“可能”描述", 2, SUBJECT, 263004),
    (263042, "pmath_g5a_point_more_less_likely", "可能性大小的判断：数量多的物体被摸到的可能性大，数量少的可能性小，数量相等可能性相等", 3, SUBJECT, 263004),
    (263043, "pmath_g5a_point_infer_quantity", "根据可能性大小推测数量：可能性大说明该种物体数量多，可能性小说明数量少，但无法确定具体个数", 4, SUBJECT, 263004),
    (263044, "pmath_g5a_point_fair_rule", "游戏规则的公平性：双方获胜的可能性相等，规则才公平；可能性不等时要调整物体数量或规则", 5, SUBJECT, 263004),
    (263045, "pmath_g5a_point_design_game", "设计公平游戏：先确定两种结果，使两种颜色或两种数字的球数量相同，摸到任一种的可能性各占一半", 6, SUBJECT, 263004),
    (263046, "pmath_g5a_point_probability_life", "可能性在生活中的应用：抽奖、天气预报、掷骰子都用可能性描述，可能性大不等于一定发生", 7, SUBJECT, 263004),

    # 第五单元 简易方程
    (263047, "pmath_g5a_point_letter_number", "用字母表示数：字母可以表示任意数，也可以表示数量关系，如a表示任意一个数", 1, SUBJECT, 263005),
    (263048, "pmath_g5a_point_letter_relation", "用字母表示数量关系：用含字母的式子表示比一个数多几、少几、几倍的数量，如a+3表示比a多3的数", 2, SUBJECT, 263005),
    (263049, "pmath_g5a_point_letter_formula", "用字母表示运算定律和公式：a+b=b+a，(a+b)c=ac+bc，长方形面积S=ab，周长C=2(a+b)", 3, SUBJECT, 263005),
    (263050, "pmath_g5a_point_letter_write", "字母相乘的简写规则：a×b写作ab或a·b，1×a写作a，a×a写作a²，a²表示两个a相乘", 4, SUBJECT, 263005),
    (263051, "pmath_g5a_point_letter_value", "含字母式子的求值：把字母所取的数值代入式子，按运算顺序计算，结果要写单位", 5, SUBJECT, 263005),
    (263052, "pmath_g5a_point_equation_meaning", "方程的意义：含有未知数的等式叫方程，判断方程必须同时满足“含未知数”和“是等式”两个条件", 6, SUBJECT, 263005),
    (263053, "pmath_g5a_point_equation_relation", "方程与等式的关系：方程一定是等式，等式不一定是方程，等式包含方程", 7, SUBJECT, 263005),
    (263054, "pmath_g5a_point_equality_add_sub", "等式的性质一：等式两边同时加上或减去同一个数，左右两边仍然相等", 8, SUBJECT, 263005),
    (263055, "pmath_g5a_point_equality_mul_div", "等式的性质二：等式两边同时乘或除以同一个不为0的数，左右两边仍然相等", 9, SUBJECT, 263005),
    (263056, "pmath_g5a_point_solution_definition", "方程的解与解方程：使方程左右两边相等的未知数的值叫方程的解，求方程的解的过程叫解方程", 10, SUBJECT, 263005),
    (263057, "pmath_g5a_point_equation_check", "方程的检验：把求出的解代入原方程，分别计算左右两边的值，相等则解正确，书写要写“左边=”“右边=”", 11, SUBJECT, 263005),
    (263058, "pmath_g5a_point_solve_add_sub", "解形如x±a=b的方程：利用等式性质一，方程两边同时减去或加上a，求出x=b∓a", 12, SUBJECT, 263005),
    (263059, "pmath_g5a_point_solve_mul_div", "解形如ax=b、x÷a=b的方程：利用等式性质二，两边同时除以a或乘a，注意除数不能为0", 13, SUBJECT, 263005),
    (263060, "pmath_g5a_point_solve_two_step", "解形如ax±b=c的方程：先把ax看作一个整体，两边同时加减b，再两边同时除以a", 14, SUBJECT, 263005),
    (263061, "pmath_g5a_point_solve_bracket", "解形如a(x±b)=c的方程：先把括号看作整体，两边同时除以a，再按x±b的形式求解", 15, SUBJECT, 263005),
    (263062, "pmath_g5a_point_equation_steps", "列方程解决问题的步骤：设未知数、找等量关系、列方程、解方程、检验并作答，关键是找准等量关系", 16, SUBJECT, 263005),
    (263063, "pmath_g5a_point_equation_times", "和倍差倍问题：设一份数为x，几倍数为nx，根据两数的和或差列方程，如x+3x=120", 17, SUBJECT, 263005),
    (263064, "pmath_g5a_point_equation_meet", "相遇问题列方程：甲的路程+乙的路程=总路程，或速度和×相遇时间=总路程，注意时间相同", 18, SUBJECT, 263005),

    # 第六单元 多边形的面积
    (263065, "pmath_g5a_point_parallelogram_derive", "平行四边形面积公式推导：沿高剪开平移拼成长方形，长方形的长等于底、宽等于高，面积不变", 1, SUBJECT, 263006),
    (263066, "pmath_g5a_point_parallelogram_area", "平行四边形的面积：面积=底×高，字母表示S=ah，已知面积和底可求高h=S÷a", 2, SUBJECT, 263006),
    (263067, "pmath_g5a_point_parallelogram_base_height", "平行四边形的底与高对应：计算面积时底和高必须互相对应，不能取任意一条高配任意一条底", 3, SUBJECT, 263006),
    (263068, "pmath_g5a_point_triangle_derive", "三角形面积公式推导：两个完全一样的三角形可以拼成一个平行四边形，三角形面积是平行四边形面积的一半", 4, SUBJECT, 263006),
    (263069, "pmath_g5a_point_triangle_area", "三角形的面积：面积=底×高÷2，字母表示S=ah÷2，已知面积和底可求高h=2S÷a", 5, SUBJECT, 263006),
    (263070, "pmath_g5a_point_triangle_equal_area", "等底等高的三角形：底相等、高相等的三角形面积一定相等，但形状可以不同", 6, SUBJECT, 263006),
    (263071, "pmath_g5a_point_trapezoid_derive", "梯形面积公式推导：两个完全一样的梯形拼成平行四边形，平行四边形的底等于上底与下底的和，高等于梯形的高", 7, SUBJECT, 263006),
    (263072, "pmath_g5a_point_trapezoid_area", "梯形的面积：面积=（上底+下底）×高÷2，字母表示S=(a+b)h÷2，逆用可求高h=2S÷(a+b)", 8, SUBJECT, 263006),
    (263073, "pmath_g5a_point_combination_area", "组合图形的面积：用分割法把图形分成几个基本图形分别求面积再相加，或用添补法补成基本图形再相减", 9, SUBJECT, 263006),
    (263074, "pmath_g5a_point_area_unit_rate", "面积单位的进率：1公顷=10000平方米，1平方千米=100公顷，1平方千米=1000000平方米", 10, SUBJECT, 263006),
    (263075, "pmath_g5a_point_area_estimate", "不规则图形面积的估算：用数方格的方法，满格算1格，不满一格的按半格计算，再乘以每格代表的面积", 11, SUBJECT, 263006),
    (263076, "pmath_g5a_point_area_trap", "面积计算的易错点：三角形和梯形别漏除2，平行四边形别与三角形公式混淆，单位要统一后再计算", 12, SUBJECT, 263006),

    # 第七单元 数学广角——植树问题
    (263077, "pmath_g5a_point_plant_both", "两端都栽：棵数=间隔数+1，间隔数=总长÷间距，如20米每隔5米栽一棵两端都栽共5棵", 1, SUBJECT, 263007),
    (263078, "pmath_g5a_point_plant_one_end", "只栽一端：棵数=间隔数，一端栽一端不栽时棵数与间隔数相等", 2, SUBJECT, 263007),
    (263079, "pmath_g5a_point_plant_no_end", "两端都不栽：棵数=间隔数-1，两端都不栽时棵数比间隔数少1", 3, SUBJECT, 263007),
    (263080, "pmath_g5a_point_plant_closed", "封闭图形植树：在圆形、正方形等封闭路线植树，棵数=间隔数，首尾重合不能重复算", 4, SUBJECT, 263007),
    (263081, "pmath_g5a_point_plant_interval", "间隔数与总长的关系：总长=间隔数×间距，间距=总长÷间隔数，先分清属于哪种栽法再列式", 5, SUBJECT, 263007),
    (263082, "pmath_g5a_point_plant_variant", "植树问题的变式：锯木头次数=段数-1，爬楼梯层数=楼层数-1，敲钟间隔数与次数、队列人数与间隔同理", 6, SUBJECT, 263007),

    # 第八单元 总复习
    (263083, "pmath_g5a_point_review_decimal_calc", "小数乘除法总复习：小数乘法的算理与积的小数位数、除数是小数的转化、商的近似数与循环小数", 1, SUBJECT, 263008),
    (263084, "pmath_g5a_point_review_equation", "简易方程总复习：用字母表示数与数量关系、方程的意义、等式的性质及各类方程的解法与检验", 2, SUBJECT, 263008),
    (263085, "pmath_g5a_point_review_area", "多边形面积总复习：平行四边形、三角形、梯形的面积公式及推导过程，组合图形与不规则图形面积", 3, SUBJECT, 263008),
    (263086, "pmath_g5a_point_review_position_probability", "位置与可能性总复习：用数对表示和确定位置、数对与平移的关系、事件发生的可能性大小与游戏公平性", 4, SUBJECT, 263008),
    (263087, "pmath_g5a_point_review_plant", "植树问题总复习：两端都栽、只栽一端、两端都不栽、封闭图形四种情况的棵数与间隔数关系及变式应用", 5, SUBJECT, 263008),
)

"""人教版（PEP）小学英语一年级下册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G1 = 1
BOOK_ID = 1426

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语一年级下册",
    "peng_g1b",
    26,
    "人民教育出版社",
    SUBJECT,
    G1,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 Classroom
    (142601, "Unit 1 Classroom", "peng_g1b_u01", 1, BOOK_ID, None),
    (142602, "Part A", "peng_g1b_u01_a", 1, BOOK_ID, 142601),
    (142603, "Part B", "peng_g1b_u01_b", 2, BOOK_ID, 142601),
    (142604, "Part C", "peng_g1b_u01_c", 3, BOOK_ID, 142601),

    # Unit 2 Room
    (142610, "Unit 2 Room", "peng_g1b_u02", 2, BOOK_ID, None),
    (142611, "Part A", "peng_g1b_u02_a", 1, BOOK_ID, 142610),
    (142612, "Part B", "peng_g1b_u02_b", 2, BOOK_ID, 142610),
    (142613, "Part C", "peng_g1b_u02_c", 3, BOOK_ID, 142610),

    # Unit 3 Toys
    (142620, "Unit 3 Toys", "peng_g1b_u03", 3, BOOK_ID, None),
    (142621, "Part A", "peng_g1b_u03_a", 1, BOOK_ID, 142620),
    (142622, "Part B", "peng_g1b_u03_b", 2, BOOK_ID, 142620),
    (142623, "Part C", "peng_g1b_u03_c", 3, BOOK_ID, 142620),

    # Unit 4 Food
    (142630, "Unit 4 Food", "peng_g1b_u04", 4, BOOK_ID, None),
    (142631, "Part A", "peng_g1b_u04_a", 1, BOOK_ID, 142630),
    (142632, "Part B", "peng_g1b_u04_b", 2, BOOK_ID, 142630),
    (142633, "Part C", "peng_g1b_u04_c", 3, BOOK_ID, 142630),

    # Unit 5 Drinks
    (142640, "Unit 5 Drinks", "peng_g1b_u05", 5, BOOK_ID, None),
    (142641, "Part A", "peng_g1b_u05_a", 1, BOOK_ID, 142640),
    (142642, "Part B", "peng_g1b_u05_b", 2, BOOK_ID, 142640),
    (142643, "Part C", "peng_g1b_u05_c", 3, BOOK_ID, 142640),

    # Unit 6 Clothes
    (142650, "Unit 6 Clothes", "peng_g1b_u06", 6, BOOK_ID, None),
    (142651, "Part A", "peng_g1b_u06_a", 1, BOOK_ID, 142650),
    (142652, "Part B", "peng_g1b_u06_b", 2, BOOK_ID, 142650),
    (142653, "Part C", "peng_g1b_u06_c", 3, BOOK_ID, 142650),

    # Revision
    (142660, "Revision 1", "peng_g1b_rev1", 7, BOOK_ID, None),
    (142670, "Revision 2", "peng_g1b_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 268001-268009 为册域层，268010-268099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (268001, "peng_g1b_domain_u01", "小学英语一下·Unit 1 Classroom", 1, SUBJECT, G1, None),
    (268002, "peng_g1b_domain_u02", "小学英语一下·Unit 2 Room", 2, SUBJECT, G1, None),
    (268003, "peng_g1b_domain_u03", "小学英语一下·Unit 3 Toys", 3, SUBJECT, G1, None),
    (268004, "peng_g1b_domain_u04", "小学英语一下·Unit 4 Food", 4, SUBJECT, G1, None),
    (268005, "peng_g1b_domain_u05", "小学英语一下·Unit 5 Drinks", 5, SUBJECT, G1, None),
    (268006, "peng_g1b_domain_u06", "小学英语一下·Unit 6 Clothes", 6, SUBJECT, G1, None),
    (268007, "peng_g1b_domain_rev1", "小学英语一下·Revision 1", 7, SUBJECT, G1, None),
    (268008, "peng_g1b_domain_rev2", "小学英语一下·Revision 2", 8, SUBJECT, G1, None),

    # Unit 1 Classroom
    (268010, "peng_g1b_point_classroom_core", "教室物品 desk／chair／blackboard：认读并指认课桌、椅子、黑板，注意 blackboard 由 black 与 board 合成", 1, SUBJECT, G1, 268001),
    (268011, "peng_g1b_point_classroom_more", "教室物品 door／window／classroom：认读门窗与教室，能结合实物快速反应", 2, SUBJECT, G1, 268001),
    (268012, "peng_g1b_point_whats_this_classroom", "What's this? 与 It's a desk.：询问近处单件物品并用 It's a ... 作答", 3, SUBJECT, G1, 268001),
    (268013, "peng_g1b_point_what_are_these", "What are these? 与 They're chairs.：询问近处多件物品，回答用复数代词 they", 4, SUBJECT, G1, 268001),
    (268014, "peng_g1b_point_this_is_classroom", "句型 This is my classroom.：向他人介绍自己的教室，this 指近处单数事物", 5, SUBJECT, G1, 268001),
    (268015, "peng_g1b_point_prep_in_on_under", "方位介词 in／on／under：理解“在里面／在上面／在下面”的空间关系", 6, SUBJECT, G1, 268001),
    (268016, "peng_g1b_point_a_an_choice", "a 与 an 的选择：辅音音素开头的名词前用 a，元音音素开头的名词前用 an，如 an egg", 7, SUBJECT, G1, 268001),
    (268017, "peng_g1b_point_plural_s", "名词复数加 -s：desk→desks、chair→chairs、window→windows，复数与 are 搭配", 8, SUBJECT, G1, 268001),
    (268018, "peng_g1b_point_classroom_commands", "课堂指令 Open the door／Close the window／Clean the blackboard：听懂指令并做出动作", 9, SUBJECT, G1, 268001),
    (268019, "peng_g1b_point_letters_af_phonics", "字母 Aa–Ff 复习与首音拼读：认读大小写并拼读 cat／bag／desk 等含目标字母的单词", 10, SUBJECT, G1, 268001),

    # Unit 2 Room
    (268020, "peng_g1b_point_room_furniture", "房间物品 bed／table／sofa／lamp：认读床、桌子、沙发、台灯并指认", 1, SUBJECT, G1, 268002),
    (268021, "peng_g1b_point_room_words", "房间类词汇 room／bedroom／box：理解 room 为房间总称，bedroom 为卧室，box 为盒子", 2, SUBJECT, G1, 268002),
    (268022, "peng_g1b_point_this_is_room", "句型 This is my room.：介绍自己的房间，my 表示“我的”", 3, SUBJECT, G1, 268002),
    (268023, "peng_g1b_point_where_is", "Where is ...? 与 It's on the bed.：询问单件物品位置并作答", 4, SUBJECT, G1, 268002),
    (268024, "peng_g1b_point_place_phrases", "方位短语 in the box／on the table／under the bed：把介词与地点名词组合使用", 5, SUBJECT, G1, 268002),
    (268025, "peng_g1b_point_is_it_yes_no", "Is it on the bed? 与 Yes, it is.／No, it isn't.：一般疑问句的肯定与否定回答", 6, SUBJECT, G1, 268002),
    (268026, "peng_g1b_point_lamp_position", "句型 The lamp is on the table.：用“物品＋is＋方位短语”描述物品摆放", 7, SUBJECT, G1, 268002),
    (268027, "peng_g1b_point_article_room", "冠词 a／the 的区别：a 表示不确定的一件，the 指双方都知道的特定物品", 8, SUBJECT, G1, 268002),
    (268028, "peng_g1b_point_letters_gl_phonics", "字母 Gg–Ll 复习与首音拼读：区分 g 与 j、l 与 r 的读音，拼读 lamp／bed 等词", 9, SUBJECT, G1, 268002),
    (268029, "peng_g1b_point_room_listening", "听辨与描述：听句子判断物品在房间中的位置，并用完整句复述", 10, SUBJECT, G1, 268002),

    # Unit 3 Toys
    (268030, "peng_g1b_point_toys_core", "玩具词汇 ball／doll／kite／car：认读球、洋娃娃、风筝、小汽车", 1, SUBJECT, G1, 268003),
    (268031, "peng_g1b_point_toys_more", "玩具词汇 plane／train／toy：扩展认读飞机、火车，toy 为玩具总称", 2, SUBJECT, G1, 268003),
    (268032, "peng_g1b_point_i_have_toy", "句型 I have a ball.：表达自己拥有某件玩具，a 后接单数名词", 3, SUBJECT, G1, 268003),
    (268033, "peng_g1b_point_toy_whats_this", "What's this? 与 It's a kite.：结合玩具实物进行单数问答", 4, SUBJECT, G1, 268003),
    (268034, "peng_g1b_point_toy_what_are_these", "What are these? 与 They're balls.：多件玩具的问答，注意名词与 be 动词同时变复数", 5, SUBJECT, G1, 268003),
    (268035, "peng_g1b_point_lets_play", "句型 Let's play with the ball.：Let's 提议一起玩，with 表示“和……一起”", 6, SUBJECT, G1, 268003),
    (268036, "peng_g1b_point_colour_toy", "形容词修饰玩具：a red kite／a blue car，颜色词放在名词前", 7, SUBJECT, G1, 268003),
    (268037, "peng_g1b_point_toy_plural", "玩具名词复数：ball→balls、doll→dolls、kite→kites、car→cars", 8, SUBJECT, G1, 268003),
    (268038, "peng_g1b_point_letters_mr_phonics", "字母 Mm–Rr 复习与首音拼读：拼读 map／red／kite 等词，注意 m 与 n 的区别", 9, SUBJECT, G1, 268003),
    (268039, "peng_g1b_point_how_many_toys", "How many ...? 与数字回答：结合玩具数量进行问答，如 How many balls?", 10, SUBJECT, G1, 268003),

    # Unit 4 Food
    (268040, "peng_g1b_point_food_staple", "食物词汇 rice／noodles／bread：认读米饭、面条、面包，注意 noodles 常用复数", 1, SUBJECT, G1, 268004),
    (268041, "peng_g1b_point_food_more", "食物词汇 cake／egg／fish：认读蛋糕、鸡蛋、鱼，fish 单复数同形", 2, SUBJECT, G1, 268004),
    (268042, "peng_g1b_point_like_food", "句型 I like ...／I don't like ...：表达对食物的喜好与不喜欢", 3, SUBJECT, G1, 268004),
    (268043, "peng_g1b_point_do_you_like", "Do you like ...? 与 Yes, I do.／No, I don't.：询问对方饮食喜好并作答", 4, SUBJECT, G1, 268004),
    (268044, "peng_g1b_point_have_some_food", "句型 Have some bread.：招待他人吃东西，some 后接不可数名词或复数名词", 5, SUBJECT, G1, 268004),
    (268045, "peng_g1b_point_food_uncountable", "不可数名词 rice／bread：作主语时视为单数，前面用 some 而非 a", 6, SUBJECT, G1, 268004),
    (268046, "peng_g1b_point_food_plural", "可数名词复数 egg→eggs／cake→cakes：数量大于一时名词与 are 同变复数", 7, SUBJECT, G1, 268004),
    (268047, "peng_g1b_point_letters_sz_phonics", "字母 Ss–Zz 复习与首音拼读：拼读 sun／egg／fish 等词，区分 s 与 z 的读音", 8, SUBJECT, G1, 268004),
    (268048, "peng_g1b_point_food_article", "a／an 与食物名词：an egg 用 an，a cake 用 a，判断依据是首音而非首字母", 9, SUBJECT, G1, 268004),
    (268049, "peng_g1b_point_food_dialogue", "情景对话：餐桌上表达喜好、招待与应答的连贯交流", 10, SUBJECT, G1, 268004),

    # Unit 5 Drinks
    (268050, "peng_g1b_point_drinks_core", "饮料词汇 water／milk／juice：认读水、牛奶、果汁", 1, SUBJECT, G1, 268005),
    (268051, "peng_g1b_point_drinks_more", "饮料词汇 tea／drink：认读茶，drink 可作名词“饮料”也可作动词“喝”", 2, SUBJECT, G1, 268005),
    (268052, "peng_g1b_point_thirsty", "句型 I'm thirsty.：表达口渴，thirsty 注意 th 的咬舌音", 3, SUBJECT, G1, 268005),
    (268053, "peng_g1b_point_want_some", "句型 I want some water.：表达想要的饮料，some 后接不可数名词", 4, SUBJECT, G1, 268005),
    (268054, "peng_g1b_point_would_you_like", "Would you like some juice? 与 Yes, please.／No, thanks.：礼貌询问并回应", 5, SUBJECT, G1, 268005),
    (268055, "peng_g1b_point_measure_phrase", "量词短语 a glass of water／a cup of tea：用容器量词表达一杯饮品", 6, SUBJECT, G1, 268005),
    (268056, "peng_g1b_point_drinks_uncountable", "不可数名词 water／milk／juice／tea：词尾不加 -s，数量借助量词短语表达", 7, SUBJECT, G1, 268005),
    (268057, "peng_g1b_point_alphabet_order", "字母表 Aa–Zz 顺序复习：按顺序背诵、补全缺失字母并快速认读", 8, SUBJECT, G1, 268005),
    (268058, "peng_g1b_point_drinks_phonics", "首音辨听 w／m／t：区分 water、milk、tea 的起始音并跟读单词", 9, SUBJECT, G1, 268005),
    (268059, "peng_g1b_point_drinks_dialogue", "情景对话：待客时询问、递送饮料并礼貌应答", 10, SUBJECT, G1, 268005),

    # Unit 6 Clothes
    (268060, "peng_g1b_point_clothes_core", "衣物词汇 shirt／dress／skirt：认读衬衫、连衣裙、短裙", 1, SUBJECT, G1, 268006),
    (268061, "peng_g1b_point_clothes_more", "衣物词汇 shoes／socks／hat：认读鞋、袜子、帽子，shoes 与 socks 常用复数", 2, SUBJECT, G1, 268006),
    (268062, "peng_g1b_point_this_these_clothes", "This is my shirt.／These are my shoes.：单件用 this is，多件用 these are", 3, SUBJECT, G1, 268006),
    (268063, "peng_g1b_point_this_vs_these", "this 与 these 的区别：this 指近处单数，these 指近处复数，be 动词随之变化", 4, SUBJECT, G1, 268006),
    (268064, "peng_g1b_point_put_on", "指令 Put on your ...／Take off your ...：听懂穿脱衣物的指令并做动作", 5, SUBJECT, G1, 268006),
    (268065, "peng_g1b_point_colour_clothes", "颜色词修饰衣物：a red dress／blue shoes，形容词放在名词前", 6, SUBJECT, G1, 268006),
    (268066, "peng_g1b_point_clothes_plural", "成对衣物用复数：shoes／socks 表示一双，作主语时 be 动词用 are", 7, SUBJECT, G1, 268006),
    (268067, "peng_g1b_point_letters_case_match", "字母大小写配对 Aa–Zz：连线、补全与排序，巩固全册字母认读", 8, SUBJECT, G1, 268006),
    (268068, "peng_g1b_point_clothes_phonics", "CVC 单词拼读 hat／sock／dress：按首音—中音—尾音切分拼读简单单词", 9, SUBJECT, G1, 268006),
    (268069, "peng_g1b_point_clothes_dialogue", "情景对话：介绍自己的衣着并询问他人穿着", 10, SUBJECT, G1, 268006),

    # Revision 1
    (268070, "peng_g1b_point_review_places", "词汇归类复习：教室物品与房间物品两类词汇的听音指认与分类", 1, SUBJECT, G1, 268007),
    (268071, "peng_g1b_point_review_prepositions", "方位介词综合：in／on／under 在图片与实景中的位置判断与描述", 2, SUBJECT, G1, 268007),
    (268072, "peng_g1b_point_review_singular_plural", "单复数问答复习：What's this?／What are these? 与 It's／They're 的对应", 3, SUBJECT, G1, 268007),
    (268073, "peng_g1b_point_review_toys_food", "玩具与食物词汇复习：认读、分类并在句型中替换使用", 4, SUBJECT, G1, 268007),
    (268074, "peng_g1b_point_review_letters_am", "字母 Aa–Mm 复习：大小写认读、书写与首音拼读", 5, SUBJECT, G1, 268007),

    # Revision 2
    (268075, "peng_g1b_point_review_drinks_clothes", "饮料与衣物词汇复习：认读、分类与情景替换", 1, SUBJECT, G1, 268008),
    (268076, "peng_g1b_point_review_this_these", "This is／These are 综合运用：介绍身边物品的单复数表达", 2, SUBJECT, G1, 268008),
    (268077, "peng_g1b_point_review_offers", "Do you like ...?／Would you like ...? 情景问答：喜好与招待的区分使用", 3, SUBJECT, G1, 268008),
    (268078, "peng_g1b_point_review_letters_nz", "字母 Nn–Zz 复习：认读、书写与字母表顺序", 4, SUBJECT, G1, 268008),
    (268079, "peng_g1b_point_review_sentences", "全册核心句型综合：What's this?／What are these?／I have ...／I like ... 的灵活运用", 5, SUBJECT, G1, 268008),
)

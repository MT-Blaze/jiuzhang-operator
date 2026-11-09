"""人教版（PEP 2024）小学英语三年级下册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G3 = 3
BOOK_ID = 1430

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语三年级下册",
    "peng_g3b",
    30,
    "人民教育出版社",
    SUBJECT,
    G3,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 Animal friends
    (143001, "Unit 1 Animal friends", "peng_g3b_u01", 1, BOOK_ID, None),
    (143002, "Part A", "peng_g3b_u01_a", 1, BOOK_ID, 143001),
    (143003, "Part B", "peng_g3b_u01_b", 2, BOOK_ID, 143001),
    (143004, "Part C", "peng_g3b_u01_c", 3, BOOK_ID, 143001),

    # Unit 2 Expressing yourself
    (143010, "Unit 2 Expressing yourself", "peng_g3b_u02", 2, BOOK_ID, None),
    (143011, "Part A", "peng_g3b_u02_a", 1, BOOK_ID, 143010),
    (143012, "Part B", "peng_g3b_u02_b", 2, BOOK_ID, 143010),
    (143013, "Part C", "peng_g3b_u02_c", 3, BOOK_ID, 143010),

    # Unit 3 Learning better
    (143020, "Unit 3 Learning better", "peng_g3b_u03", 3, BOOK_ID, None),
    (143021, "Part A", "peng_g3b_u03_a", 1, BOOK_ID, 143020),
    (143022, "Part B", "peng_g3b_u03_b", 2, BOOK_ID, 143020),
    (143023, "Part C", "peng_g3b_u03_c", 3, BOOK_ID, 143020),

    # Unit 4 Healthy food
    (143030, "Unit 4 Healthy food", "peng_g3b_u04", 4, BOOK_ID, None),
    (143031, "Part A", "peng_g3b_u04_a", 1, BOOK_ID, 143030),
    (143032, "Part B", "peng_g3b_u04_b", 2, BOOK_ID, 143030),
    (143033, "Part C", "peng_g3b_u04_c", 3, BOOK_ID, 143030),

    # Unit 5 Old toys
    (143040, "Unit 5 Old toys", "peng_g3b_u05", 5, BOOK_ID, None),
    (143041, "Part A", "peng_g3b_u05_a", 1, BOOK_ID, 143040),
    (143042, "Part B", "peng_g3b_u05_b", 2, BOOK_ID, 143040),
    (143043, "Part C", "peng_g3b_u05_c", 3, BOOK_ID, 143040),

    # Unit 6 Numbers in life
    (143050, "Unit 6 Numbers in life", "peng_g3b_u06", 6, BOOK_ID, None),
    (143051, "Part A", "peng_g3b_u06_a", 1, BOOK_ID, 143050),
    (143052, "Part B", "peng_g3b_u06_b", 2, BOOK_ID, 143050),
    (143053, "Part C", "peng_g3b_u06_c", 3, BOOK_ID, 143050),

    # Revision
    (143060, "Revision 1", "peng_g3b_rev1", 7, BOOK_ID, None),
    (143061, "Revision 2", "peng_g3b_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 272001-272008 为册域层，272010-272099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (272001, "peng_g3b_domain_u01", "小学英语三下·Unit 1 Animal friends", 1, SUBJECT, G3, None),
    (272002, "peng_g3b_domain_u02", "小学英语三下·Unit 2 Expressing yourself", 2, SUBJECT, G3, None),
    (272003, "peng_g3b_domain_u03", "小学英语三下·Unit 3 Learning better", 3, SUBJECT, G3, None),
    (272004, "peng_g3b_domain_u04", "小学英语三下·Unit 4 Healthy food", 4, SUBJECT, G3, None),
    (272005, "peng_g3b_domain_u05", "小学英语三下·Unit 5 Old toys", 5, SUBJECT, G3, None),
    (272006, "peng_g3b_domain_u06", "小学英语三下·Unit 6 Numbers in life", 6, SUBJECT, G3, None),
    (272007, "peng_g3b_domain_rev1", "小学英语三下·Revision 1", 7, SUBJECT, G3, None),
    (272008, "peng_g3b_domain_rev2", "小学英语三下·Revision 2", 8, SUBJECT, G3, None),

    # Unit 1 Animal friends
    (272010, "peng_g3b_point_animal_vocab_a", "动物词汇 panda／monkey／elephant／tiger：认读并区分单复数形式", 1, SUBJECT, G3, 272001),
    (272011, "peng_g3b_point_animal_vocab_b", "动物词汇 bear／giraffe／lion／zebra：认读野生动物，注意 giraffe 拼写", 2, SUBJECT, G3, 272001),
    (272012, "peng_g3b_point_what_this_that", "句型 What's this?／What's that? 与 It's a ...：this 指近处，that 指远处", 3, SUBJECT, G3, 272001),
    (272013, "peng_g3b_point_article_a_an", "不定冠词 a／an：元音音素前用 an，如 an elephant／an apple", 4, SUBJECT, G3, 272001),
    (272014, "peng_g3b_point_animal_appearance", "动物外形 It's big／small／tall／short／long.：用形容词描述体型特征", 5, SUBJECT, G3, 272001),
    (272015, "peng_g3b_point_animal_body_has", "身体特征 It has a long nose.／It has big ears.：第三人称单数用 has", 6, SUBJECT, G3, 272001),
    (272016, "peng_g3b_point_can_ability", "能力表达 It can run／fly／swim／jump.：can 后接动词原形，不随人称变化", 7, SUBJECT, G3, 272001),
    (272017, "peng_g3b_point_can_question", "能力问答 Can it climb? 与 Yes, it can.／No, it can't.：can 提前构成疑问句", 8, SUBJECT, G3, 272001),
    (272018, "peng_g3b_point_like_plural", "喜好表达 I like pandas.：like 后接可数名词复数表示一类动物", 9, SUBJECT, G3, 272001),
    (272019, "peng_g3b_point_zoo_imperative", "建议与祈使 Let's go to the zoo.／Look at the panda.：Let's 后接动词原形", 10, SUBJECT, G3, 272001),
    (272020, "peng_g3b_point_phonics_a_e", "字母组合 a-e 发音 /eɪ/：cake, name, face, game 中 a 发字母音", 11, SUBJECT, G3, 272001),

    # Unit 2 Expressing yourself
    (272021, "peng_g3b_point_feeling_basic", "情绪词汇 happy／sad／angry／tired：认读并描述基本情绪", 1, SUBJECT, G3, 272002),
    (272022, "peng_g3b_point_feeling_more", "感受词汇 hungry／thirsty／scared／excited：认读生理与心理感受", 2, SUBJECT, G3, 272002),
    (272023, "peng_g3b_point_how_feel", "句型 How do you feel? 与 I feel happy.：询问并回答自己的感受", 3, SUBJECT, G3, 272002),
    (272024, "peng_g3b_point_are_you_feeling", "句型 Are you happy? 与 Yes, I am.／No, I'm not.：be 动词提问确认感受", 4, SUBJECT, G3, 272002),
    (272025, "peng_g3b_point_third_person_feel", "第三人称 How does he feel? 与 He feels sad.：does 提问，动词用 feels", 5, SUBJECT, G3, 272002),
    (272026, "peng_g3b_point_sorry_reply", "礼貌用语 I'm sorry. 与 That's OK.：道歉与宽容回应配对", 6, SUBJECT, G3, 272002),
    (272027, "peng_g3b_point_dont_imperative", "否定祈使句 Don't be sad.／Don't worry.：Don't 后接动词原形", 7, SUBJECT, G3, 272002),
    (272028, "peng_g3b_point_because_reason", "原因表达 I'm happy because I have a new toy.：because 连接原因", 8, SUBJECT, G3, 272002),
    (272029, "peng_g3b_point_would_like", "意愿表达 I'd like some water.：would like 表示想要，缩写为 'd like", 9, SUBJECT, G3, 272002),
    (272030, "peng_g3b_point_like_doing", "喜好表达 I like singing and dancing.：like 后接动词 -ing 形式", 10, SUBJECT, G3, 272002),
    (272031, "peng_g3b_point_phonics_i_e", "字母组合 i-e 发音 /aɪ/：bike, kite, five, nine 中 i 发字母音", 11, SUBJECT, G3, 272002),

    # Unit 3 Learning better
    (272032, "peng_g3b_point_school_things_a", "学习用品 pen／pencil／ruler／eraser：认读并说出用途", 1, SUBJECT, G3, 272003),
    (272033, "peng_g3b_point_school_things_b", "学习用品 book／bag／pencil box／crayon：认读并注意复数形式", 2, SUBJECT, G3, 272003),
    (272034, "peng_g3b_point_whats_in_bag", "句型 What's in your bag? 与 I have a pen.：询问并回答包内物品", 3, SUBJECT, G3, 272003),
    (272035, "peng_g3b_point_learning_verbs", "学习行为 read／write／draw／listen／speak：认读并做出相应动作", 4, SUBJECT, G3, 272003),
    (272036, "peng_g3b_point_classroom_imperative", "课堂祈使句 Open your book.／Close your book.／Listen to me.：动词原形开头", 5, SUBJECT, G3, 272003),
    (272037, "peng_g3b_point_lets_together", "建议句型 Let's read together.：Let's 后接动词原形表示共同活动", 6, SUBJECT, G3, 272003),
    (272038, "peng_g3b_point_can_learning", "能力表达 I can read and write.：用 can 连接两项学习能力", 7, SUBJECT, G3, 272003),
    (272039, "peng_g3b_point_ask_help", "请求帮助 Can you help me? 与 Sure.／Of course.：提出请求并应答", 8, SUBJECT, G3, 272003),
    (272040, "peng_g3b_point_may_i", "礼貌请求 May I use your pencil? 与 Here you are.：征求许可", 9, SUBJECT, G3, 272003),
    (272041, "peng_g3b_point_preposition_place", "介词 in／on／under：描述学习用品之间的位置关系", 10, SUBJECT, G3, 272003),
    (272042, "peng_g3b_point_phonics_o_e", "字母组合 o-e 发音 /əʊ/：nose, rose, home, hope 中 o 发字母音", 11, SUBJECT, G3, 272003),

    # Unit 4 Healthy food
    (272043, "peng_g3b_point_food_staple", "食物词汇 rice／noodles／bread：认读主食，rice 为不可数名词", 1, SUBJECT, G3, 272004),
    (272044, "peng_g3b_point_food_protein", "食物词汇 milk／egg／fish／meat：认读蛋白质类食物", 2, SUBJECT, G3, 272004),
    (272045, "peng_g3b_point_food_plant", "食物词汇 vegetables／fruit／apple／banana：认读蔬果，vegetables 常用复数", 3, SUBJECT, G3, 272004),
    (272046, "peng_g3b_point_like_food", "喜好表达 I like apples.／I don't like ...：表达对食物的喜好", 4, SUBJECT, G3, 272004),
    (272047, "peng_g3b_point_would_you_like", "句型 Would you like some rice? 与 Yes, please.／No, thanks.：礼貌提供食物", 5, SUBJECT, G3, 272004),
    (272048, "peng_g3b_point_id_like_food", "句型 I'd like some noodles.：would like 后接名词表达想要的食物", 6, SUBJECT, G3, 272004),
    (272049, "peng_g3b_point_some_usage", "some 的用法：肯定句与请求句中修饰可数与不可数名词", 7, SUBJECT, G3, 272004),
    (272050, "peng_g3b_point_healthy_advice", "饮食建议 Eat more vegetables.／Drink more water.：祈使句给出健康建议", 8, SUBJECT, G3, 272004),
    (272051, "peng_g3b_point_three_meals", "三餐词汇 breakfast／lunch／dinner：搭配 have breakfast 等短语", 9, SUBJECT, G3, 272004),
    (272052, "peng_g3b_point_dont_eat", "否定建议 Don't eat too much candy.：Don't 后接动词原形", 10, SUBJECT, G3, 272004),
    (272053, "peng_g3b_point_phonics_u_e", "字母组合 u-e 发音 /juː/：cute, use, huge, music 中 u 发字母音", 11, SUBJECT, G3, 272004),

    # Unit 5 Old toys
    (272054, "peng_g3b_point_toy_vocab_a", "玩具词汇 ball／doll／kite／car：认读常见玩具名称", 1, SUBJECT, G3, 272005),
    (272055, "peng_g3b_point_toy_vocab_b", "玩具词汇 boat／plane／train／robot：认读交通工具类玩具", 2, SUBJECT, G3, 272005),
    (272056, "peng_g3b_point_whose_question", "句型 Whose ball is this? 与 It's mine.：询问物品归属", 3, SUBJECT, G3, 272005),
    (272057, "peng_g3b_point_possessive_pronoun", "名词性物主代词 mine／yours／his／hers：独立使用，后不接名词", 4, SUBJECT, G3, 272005),
    (272058, "peng_g3b_point_is_this_yours", "句型 Is this your doll? 与 Yes, it is.／No, it isn't.：确认物品归属", 5, SUBJECT, G3, 272005),
    (272059, "peng_g3b_point_these_old_toys", "句型 These are my old toys.：These are 后接可数名词复数", 6, SUBJECT, G3, 272005),
    (272060, "peng_g3b_point_this_that_contrast", "指示代词 this／that：This is mine.／That is yours. 区分远近", 7, SUBJECT, G3, 272005),
    (272061, "peng_g3b_point_noun_possessive", "名词所有格 Tom's ball：人名后加 's 表示所属关系", 8, SUBJECT, G3, 272005),
    (272062, "peng_g3b_point_have_have_not", "句型 I have a kite.／I don't have a robot.：have 表示拥有", 9, SUBJECT, G3, 272005),
    (272063, "peng_g3b_point_reuse_old_toys", "旧物处理 We can reuse old toys.／Let's donate them.：用 can 与 Let's 提建议", 10, SUBJECT, G3, 272005),
    (272064, "peng_g3b_point_phonics_ee", "字母组合 e-e／ee 发音 /iː/：he, she, me, see, tree", 11, SUBJECT, G3, 272005),

    # Unit 6 Numbers in life
    (272065, "peng_g3b_point_number_11_20", "数字 eleven—twenty：认读 11—20，注意 -teen 与 twenty 拼写", 1, SUBJECT, G3, 272006),
    (272066, "peng_g3b_point_number_tens", "整十数 twenty／thirty／forty／fifty／sixty／seventy／eighty／ninety／one hundred", 2, SUBJECT, G3, 272006),
    (272067, "peng_g3b_point_number_21_99", "数字 21—99 构成：十位与个位之间加连字符，如 twenty-one", 3, SUBJECT, G3, 272006),
    (272068, "peng_g3b_point_how_many", "句型 How many books do you have? 与 I have five.：询问并回答数量", 4, SUBJECT, G3, 272006),
    (272069, "peng_g3b_point_how_much_price", "句型 How much is it? 与 It's ten yuan.：询问并回答价格", 5, SUBJECT, G3, 272006),
    (272070, "peng_g3b_point_what_time", "句型 What time is it? 与 It's seven o'clock.：询问并回答整点时间", 6, SUBJECT, G3, 272006),
    (272071, "peng_g3b_point_phone_number", "电话号码与门牌号：数字逐位朗读，如 138 读作 one three eight", 7, SUBJECT, G3, 272006),
    (272072, "peng_g3b_point_how_old", "句型 How old are you? 与 I'm nine.：询问并回答年龄", 8, SUBJECT, G3, 272006),
    (272073, "peng_g3b_point_plural_rules", "名词复数规则：一般加 -s，以 s／x／ch／sh 结尾加 -es", 9, SUBJECT, G3, 272006),
    (272074, "peng_g3b_point_there_are", "句型 There are twenty students.：There be 结构表达存在数量", 10, SUBJECT, G3, 272006),
    (272075, "peng_g3b_point_irregular_plural", "不规则复数 man—men／child—children／foot—feet：特殊变化需记忆", 11, SUBJECT, G3, 272006),
    (272076, "peng_g3b_point_phonics_digraph", "字母组合 sh／ch／th 发音：she, chair, three 的辅音组合读音", 12, SUBJECT, G3, 272006),

    # Revision 1
    (272077, "peng_g3b_point_review_units_1_3_words", "Units 1—3 词汇复习：动物、情绪、学习用品分类认读", 1, SUBJECT, G3, 272007),
    (272078, "peng_g3b_point_review_questions", "句型复习 What's this?／How do you feel?／Can you ...? 情景问答", 2, SUBJECT, G3, 272007),
    (272079, "peng_g3b_point_review_phonics_a_i_o", "语音复习 a-e／i-e／o-e：拼读 cake, bike, nose 等词", 3, SUBJECT, G3, 272007),
    (272080, "peng_g3b_point_review_dialogue", "综合情景对话：介绍动物朋友、表达感受、谈论学习", 4, SUBJECT, G3, 272007),

    # Revision 2
    (272081, "peng_g3b_point_review_units_4_6_words", "Units 4—6 词汇复习：食物、玩具、数字分类认读", 1, SUBJECT, G3, 272008),
    (272082, "peng_g3b_point_review_questions_2", "句型复习 Would you like ...?／How much ...?／What time ...? 情景问答", 2, SUBJECT, G3, 272008),
    (272083, "peng_g3b_point_review_phonics_u_e_digraph", "语音复习 u-e／ee／sh／ch／th：拼读 cute, tree, chair 等词", 3, SUBJECT, G3, 272008),
    (272084, "peng_g3b_point_review_project", "综合运用与项目展示：制定健康食谱、整理旧玩具、介绍生活中的数字", 4, SUBJECT, G3, 272008),
)

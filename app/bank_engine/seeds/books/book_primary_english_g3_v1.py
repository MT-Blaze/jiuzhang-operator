"""人教版（PEP 2024）小学英语三年级上册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G3 = 3
BOOK_ID = 1429

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语三年级上册",
    "peng_g3a",
    29,
    "人民教育出版社",
    SUBJECT,
    G3,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 Making friends
    (142901, "Unit 1 Making friends", "peng_g3a_u01", 1, BOOK_ID, None),
    (142902, "Part A", "peng_g3a_u01_a", 1, BOOK_ID, 142901),
    (142903, "Part B", "peng_g3a_u01_b", 2, BOOK_ID, 142901),
    (142904, "Part C", "peng_g3a_u01_c", 3, BOOK_ID, 142901),

    # Unit 2 Different families
    (142910, "Unit 2 Different families", "peng_g3a_u02", 2, BOOK_ID, None),
    (142911, "Part A", "peng_g3a_u02_a", 1, BOOK_ID, 142910),
    (142912, "Part B", "peng_g3a_u02_b", 2, BOOK_ID, 142910),
    (142913, "Part C", "peng_g3a_u02_c", 3, BOOK_ID, 142910),

    # Unit 3 Amazing animals
    (142920, "Unit 3 Amazing animals", "peng_g3a_u03", 3, BOOK_ID, None),
    (142921, "Part A", "peng_g3a_u03_a", 1, BOOK_ID, 142920),
    (142922, "Part B", "peng_g3a_u03_b", 2, BOOK_ID, 142920),
    (142923, "Part C", "peng_g3a_u03_c", 3, BOOK_ID, 142920),

    # Unit 4 Plants around us
    (142930, "Unit 4 Plants around us", "peng_g3a_u04", 4, BOOK_ID, None),
    (142931, "Part A", "peng_g3a_u04_a", 1, BOOK_ID, 142930),
    (142932, "Part B", "peng_g3a_u04_b", 2, BOOK_ID, 142930),
    (142933, "Part C", "peng_g3a_u04_c", 3, BOOK_ID, 142930),

    # Unit 5 The colourful world
    (142940, "Unit 5 The colourful world", "peng_g3a_u05", 5, BOOK_ID, None),
    (142941, "Part A", "peng_g3a_u05_a", 1, BOOK_ID, 142940),
    (142942, "Part B", "peng_g3a_u05_b", 2, BOOK_ID, 142940),
    (142943, "Part C", "peng_g3a_u05_c", 3, BOOK_ID, 142940),

    # Unit 6 Useful numbers
    (142950, "Unit 6 Useful numbers", "peng_g3a_u06", 6, BOOK_ID, None),
    (142951, "Part A", "peng_g3a_u06_a", 1, BOOK_ID, 142950),
    (142952, "Part B", "peng_g3a_u06_b", 2, BOOK_ID, 142950),
    (142953, "Part C", "peng_g3a_u06_c", 3, BOOK_ID, 142950),

    # Revision
    (142960, "Revision 1", "peng_g3a_rev1", 7, BOOK_ID, None),
    (142961, "Revision 2", "peng_g3a_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 271001-271008 为册域层，271010-271099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (271001, "peng_g3a_domain_u01", "小学英语三上·Unit 1 Making friends", 1, SUBJECT, G3, None),
    (271002, "peng_g3a_domain_u02", "小学英语三上·Unit 2 Different families", 2, SUBJECT, G3, None),
    (271003, "peng_g3a_domain_u03", "小学英语三上·Unit 3 Amazing animals", 3, SUBJECT, G3, None),
    (271004, "peng_g3a_domain_u04", "小学英语三上·Unit 4 Plants around us", 4, SUBJECT, G3, None),
    (271005, "peng_g3a_domain_u05", "小学英语三上·Unit 5 The colourful world", 5, SUBJECT, G3, None),
    (271006, "peng_g3a_domain_u06", "小学英语三上·Unit 6 Useful numbers", 6, SUBJECT, G3, None),
    (271007, "peng_g3a_domain_rev1", "小学英语三上·Revision 1", 7, SUBJECT, G3, None),
    (271008, "peng_g3a_domain_rev2", "小学英语三上·Revision 2", 8, SUBJECT, G3, None),

    # Unit 1 Making friends
    (271010, "peng_g3a_point_greet_hello", "问候语 Hello!／Hi!：见面打招呼，Hi 更随意，答语可重复原句", 1, SUBJECT, G3, 271001),
    (271011, "peng_g3a_point_greet_morning", "早上问候 Good morning!：上午见面使用，答语同为 Good morning!", 2, SUBJECT, G3, 271001),
    (271012, "peng_g3a_point_intro_i_am", "自我介绍 I'm ...：I'm Mike. 与 My name is Mike. 两种同义表达", 3, SUBJECT, G3, 271001),
    (271013, "peng_g3a_point_ask_name", "询问姓名 What's your name? 与 My name is ...：What's 是 What is 的缩写", 4, SUBJECT, G3, 271001),
    (271014, "peng_g3a_point_intro_friend", "介绍朋友 This is my friend, Amy.：用 This is 把朋友介绍给他人", 5, SUBJECT, G3, 271001),
    (271015, "peng_g3a_point_friend_desc", "朋友描述 He's tall.／She's friendly.：用 He's／She's 加形容词描述朋友", 6, SUBJECT, G3, 271001),
    (271016, "peng_g3a_point_greet_bye", "告别用语 Goodbye!／Bye!：分别时的礼貌表达，Bye 较口语化", 7, SUBJECT, G3, 271001),
    (271017, "peng_g3a_point_lets_play", "建议句型 Let's play together!：Let's 后接动词原形，提出一起做某事", 8, SUBJECT, G3, 271001),
    (271018, "peng_g3a_point_nice_meet", "初次见面 Nice to meet you. 与 Nice to meet you, too.：问候与应答配对", 9, SUBJECT, G3, 271001),
    (271019, "peng_g3a_point_letters_a_d", "字母 Aa—Dd 音形：apple, book, cat, dog 的首字母与发音对应", 10, SUBJECT, G3, 271001),

    # Unit 2 Different families
    (271020, "peng_g3a_point_family_father", "家庭成员 father／dad：认读父亲，dad 为口语称呼", 1, SUBJECT, G3, 271002),
    (271021, "peng_g3a_point_family_mother", "家庭成员 mother／mum：认读母亲，mum 为口语称呼", 2, SUBJECT, G3, 271002),
    (271022, "peng_g3a_point_family_siblings", "家庭成员 brother／sister：认读兄弟与姐妹，注意 th 咬舌音", 3, SUBJECT, G3, 271002),
    (271023, "peng_g3a_point_family_grandparents", "家庭成员 grandfather／grandmother：认读祖父母，口语作 grandpa／grandma", 4, SUBJECT, G3, 271002),
    (271024, "peng_g3a_point_family_word", "家庭词汇 family：This is my family. 指“这是我的家庭”", 5, SUBJECT, G3, 271002),
    (271025, "peng_g3a_point_family_intro", "介绍家人 This is my mother.：向朋友逐一介绍家庭成员", 6, SUBJECT, G3, 271002),
    (271026, "peng_g3a_point_family_who", "询问身份 Who's that? 与 He's／She's my ...：Who's 是 Who is 的缩写", 7, SUBJECT, G3, 271002),
    (271027, "peng_g3a_point_possessive_his_her", "物主代词 his／her：his father 指他的父亲，her sister 指她的姐妹", 8, SUBJECT, G3, 271002),
    (271028, "peng_g3a_point_family_yes_no", "句型 Is this your sister? 与 Yes, it is.／No, it isn't.：确认家人身份", 9, SUBJECT, G3, 271002),
    (271029, "peng_g3a_point_letters_e_h", "字母 Ee—Hh 音形：egg, fish, girl, hand 的首字母与发音对应", 10, SUBJECT, G3, 271002),

    # Unit 3 Amazing animals
    (271030, "peng_g3a_point_animal_panda_monkey", "动物词汇 panda／monkey：认读熊猫与猴子，注意 ea／ey 的读音", 1, SUBJECT, G3, 271003),
    (271031, "peng_g3a_point_animal_elephant_tiger", "动物词汇 elephant／tiger：认读大象与老虎，ph 读 /f/", 2, SUBJECT, G3, 271003),
    (271032, "peng_g3a_point_animal_rabbit_bird_fish", "动物词汇 rabbit／bird／fish：认读兔子、鸟与鱼，fish 单复数同形", 3, SUBJECT, G3, 271003),
    (271033, "peng_g3a_point_animal_what_this", "句型 What's this? 与 It's a panda.：指认近处单个动物并回答", 4, SUBJECT, G3, 271003),
    (271034, "peng_g3a_point_animal_is_this", "句型 Is this a monkey? 与 Yes, it is.／No, it isn't.：确认动物身份", 5, SUBJECT, G3, 271003),
    (271035, "peng_g3a_point_animal_adjective", "动物特征 It's big／small／tall／cute.：用形容词描述动物外形", 6, SUBJECT, G3, 271003),
    (271036, "peng_g3a_point_animal_and", "形容词并列 It's big and strong.：用 and 连接两个形容词共同描述", 7, SUBJECT, G3, 271003),
    (271037, "peng_g3a_point_animal_can", "动物能力 It can run／fly／swim／jump.：情态动词 can 后接动词原形", 8, SUBJECT, G3, 271003),
    (271038, "peng_g3a_point_animal_zoo", "建议句型 Let's go to the zoo!：邀请同伴去动物园看动物", 9, SUBJECT, G3, 271003),
    (271039, "peng_g3a_point_letters_i_l", "字母 Ii—Ll 音形：ice, juice, kite, lion 的首字母与发音对应", 10, SUBJECT, G3, 271003),

    # Unit 4 Plants around us
    (271040, "peng_g3a_point_plant_root_stem", "植物部位 root／stem：认读根与茎，说明其支撑与吸水作用", 1, SUBJECT, G3, 271004),
    (271041, "peng_g3a_point_plant_leaf_flower", "植物部位 leaf／flower：认读叶与花，leaf 的复数为 leaves", 2, SUBJECT, G3, 271004),
    (271042, "peng_g3a_point_plant_seed_fruit", "植物部位 seed／fruit：认读种子与果实，果实由花发育而来", 3, SUBJECT, G3, 271004),
    (271043, "peng_g3a_point_plant_grow", "植物生长顺序 seed→sprout→plant→flower：用顺序词描述生长过程", 4, SUBJECT, G3, 271004),
    (271044, "peng_g3a_point_plant_what_this", "句型 What's this? 与 It's a flower.：指认植物并回答", 5, SUBJECT, G3, 271004),
    (271045, "peng_g3a_point_plant_these_are", "句型 These are leaves.：These are 后接可数名词复数，指近处多个事物", 6, SUBJECT, G3, 271004),
    (271046, "peng_g3a_point_plant_are_these", "句型 Are these flowers? 与 Yes, they are.／No, they aren't.：复数一般疑问句", 7, SUBJECT, G3, 271004),
    (271047, "peng_g3a_point_plant_need", "植物需求 Plants need water and sun.：water, sun, soil, air 四个生长条件", 8, SUBJECT, G3, 271004),
    (271048, "peng_g3a_point_plant_water_them", "建议与行动 Let's water the plants.：Let's 后接动词原形，表达共同行动", 9, SUBJECT, G3, 271004),
    (271049, "peng_g3a_point_letters_m_p", "字母 Mm—Pp 音形：milk, nose, orange, pen 的首字母与发音对应", 10, SUBJECT, G3, 271004),

    # Unit 5 The colourful world
    (271050, "peng_g3a_point_colour_ryb", "颜色词汇 red／yellow／blue：认读红、黄、蓝三种基本颜色", 1, SUBJECT, G3, 271005),
    (271051, "peng_g3a_point_colour_gop", "颜色词汇 green／orange／purple：认读绿、橙、紫，orange 兼指橙子", 2, SUBJECT, G3, 271005),
    (271052, "peng_g3a_point_colour_pbbw", "颜色词汇 pink／brown／black／white：认读粉、棕、黑、白", 3, SUBJECT, G3, 271005),
    (271053, "peng_g3a_point_colour_ask", "句型 What colour is it? 与 It's red.：询问并回答物品颜色", 4, SUBJECT, G3, 271005),
    (271054, "peng_g3a_point_colour_is_it", "句型 Is it blue? 与 Yes, it is.／No, it isn't.：确认物品颜色", 5, SUBJECT, G3, 271005),
    (271055, "peng_g3a_point_colour_attribute", "颜色作定语 a red apple：形容词放在名词前，顺序为“颜色＋名词”", 6, SUBJECT, G3, 271005),
    (271056, "peng_g3a_point_colour_mix", "颜色混合 Red and yellow make orange.：用 make 表达两种颜色调出新颜色", 7, SUBJECT, G3, 271005),
    (271057, "peng_g3a_point_colour_describe", "描述周围颜色 The sky is blue.：用“主语＋is＋颜色”描述事物", 8, SUBJECT, G3, 271005),
    (271058, "peng_g3a_point_colour_like", "喜好表达 I like green.：表达喜欢的颜色，colour 英式拼写", 9, SUBJECT, G3, 271005),
    (271059, "peng_g3a_point_letters_q_t", "字母 Qq—Tt 音形：queen, red, sun, tiger 的首字母与发音对应", 10, SUBJECT, G3, 271005),

    # Unit 6 Useful numbers
    (271060, "peng_g3a_point_number_1_10", "数字 one—ten：认读并书写 1—10，注意 three／five 的拼写", 1, SUBJECT, G3, 271006),
    (271061, "peng_g3a_point_number_11_15", "数字 eleven—fifteen：认读 11—15，注意 -teen 结尾与重音", 2, SUBJECT, G3, 271006),
    (271062, "peng_g3a_point_number_16_20", "数字 sixteen—twenty：认读 16—20，注意 twenty 的拼写变化", 3, SUBJECT, G3, 271006),
    (271063, "peng_g3a_point_number_how_many", "句型 How many ...? 与 I have five.：询问并回答可数物品的数量", 4, SUBJECT, G3, 271006),
    (271064, "peng_g3a_point_number_plural_s", "可数名词复数 -s：two books／three pens，数量大于一是名词加 s", 5, SUBJECT, G3, 271006),
    (271065, "peng_g3a_point_number_how_old", "句型 How old are you? 与 I'm nine.：询问并回答年龄，用 be 动词", 6, SUBJECT, G3, 271006),
    (271066, "peng_g3a_point_number_count_items", "数量与物品匹配 I can see four birds.：数字与可数名词复数搭配", 7, SUBJECT, G3, 271006),
    (271067, "peng_g3a_point_number_real_life", "数字实际运用：认读电话号码、页码与价格中的数字", 8, SUBJECT, G3, 271006),
    (271068, "peng_g3a_point_number_lets_count", "建议句型 Let's count!：邀请同伴一起数数，count 表示数数", 9, SUBJECT, G3, 271006),
    (271069, "peng_g3a_point_letters_u_z", "字母 Uu—Zz 音形：umbrella, van, water, box, yellow, zoo 的发音对应", 10, SUBJECT, G3, 271006),

    # Revision 1
    (271070, "peng_g3a_point_review_greet_intro", "问候与自我介绍复习：Hello! I'm ... / What's your name? 情景对话", 1, SUBJECT, G3, 271007),
    (271071, "peng_g3a_point_review_family", "家庭词汇与 his／her 复习：看家庭照片介绍家人", 2, SUBJECT, G3, 271007),
    (271072, "peng_g3a_point_review_animals", "动物词汇与 What's this?／Is this ...? 复习：看图问答", 3, SUBJECT, G3, 271007),
    (271073, "peng_g3a_point_review_letters_a_l", "字母 Aa—Ll 音形拼读复习：首字母归类与单词认读", 4, SUBJECT, G3, 271007),

    # Revision 2
    (271080, "peng_g3a_point_review_plants", "植物部位与 These are ... 复习：用复数句型介绍植物", 1, SUBJECT, G3, 271008),
    (271081, "peng_g3a_point_review_colours", "颜色词汇与 What colour is it? 复习：看图问答并描述颜色", 2, SUBJECT, G3, 271008),
    (271082, "peng_g3a_point_review_numbers", "数字 1—20 与 How many ...? 复习：数数并回答数量", 3, SUBJECT, G3, 271008),
    (271083, "peng_g3a_point_review_letters_m_z", "字母 Mm—Zz 音形拼读复习：首字母归类与单词认读", 4, SUBJECT, G3, 271008),
    (271085, "peng_g3a_point_review_sentence_mix", "综合句型复习：This is ...／These are ...／Let's ... 情景运用", 5, SUBJECT, G3, 271008),
)

"""人教版（PEP）小学英语二年级上册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G2 = 2
BOOK_ID = 1427

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语二年级上册",
    "peng_g2a",
    27,
    "人民教育出版社",
    SUBJECT,
    G2,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 My family
    (142701, "Unit 1 My family", "peng_g2a_u01", 1, BOOK_ID, None),
    (142702, "Part A", "peng_g2a_u01_a", 1, BOOK_ID, 142701),
    (142703, "Part B", "peng_g2a_u01_b", 2, BOOK_ID, 142701),
    (142704, "Part C", "peng_g2a_u01_c", 3, BOOK_ID, 142701),

    # Unit 2 My friends
    (142710, "Unit 2 My friends", "peng_g2a_u02", 2, BOOK_ID, None),
    (142711, "Part A", "peng_g2a_u02_a", 1, BOOK_ID, 142710),
    (142712, "Part B", "peng_g2a_u02_b", 2, BOOK_ID, 142710),
    (142713, "Part C", "peng_g2a_u02_c", 3, BOOK_ID, 142710),

    # Unit 3 My school
    (142720, "Unit 3 My school", "peng_g2a_u03", 3, BOOK_ID, None),
    (142721, "Part A", "peng_g2a_u03_a", 1, BOOK_ID, 142720),
    (142722, "Part B", "peng_g2a_u03_b", 2, BOOK_ID, 142720),
    (142723, "Part C", "peng_g2a_u03_c", 3, BOOK_ID, 142720),

    # Unit 4 My body
    (142730, "Unit 4 My body", "peng_g2a_u04", 4, BOOK_ID, None),
    (142731, "Part A", "peng_g2a_u04_a", 1, BOOK_ID, 142730),
    (142732, "Part B", "peng_g2a_u04_b", 2, BOOK_ID, 142730),
    (142733, "Part C", "peng_g2a_u04_c", 3, BOOK_ID, 142730),

    # Unit 5 My toys
    (142740, "Unit 5 My toys", "peng_g2a_u05", 5, BOOK_ID, None),
    (142741, "Part A", "peng_g2a_u05_a", 1, BOOK_ID, 142740),
    (142742, "Part B", "peng_g2a_u05_b", 2, BOOK_ID, 142740),
    (142743, "Part C", "peng_g2a_u05_c", 3, BOOK_ID, 142740),

    # Unit 6 My food
    (142750, "Unit 6 My food", "peng_g2a_u06", 6, BOOK_ID, None),
    (142751, "Part A", "peng_g2a_u06_a", 1, BOOK_ID, 142750),
    (142752, "Part B", "peng_g2a_u06_b", 2, BOOK_ID, 142750),
    (142753, "Part C", "peng_g2a_u06_c", 3, BOOK_ID, 142750),

    # Revision
    (142760, "Revision 1", "peng_g2a_rev1", 7, BOOK_ID, None),
    (142770, "Revision 2", "peng_g2a_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / parent_id
# 269001-269008 为册域层，269010-269099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (269001, "peng_g2a_domain_u01", "小学英语二上·Unit 1 My family", 1, SUBJECT, None),
    (269002, "peng_g2a_domain_u02", "小学英语二上·Unit 2 My friends", 2, SUBJECT, None),
    (269003, "peng_g2a_domain_u03", "小学英语二上·Unit 3 My school", 3, SUBJECT, None),
    (269004, "peng_g2a_domain_u04", "小学英语二上·Unit 4 My body", 4, SUBJECT, None),
    (269005, "peng_g2a_domain_u05", "小学英语二上·Unit 5 My toys", 5, SUBJECT, None),
    (269006, "peng_g2a_domain_u06", "小学英语二上·Unit 6 My food", 6, SUBJECT, None),
    (269007, "peng_g2a_domain_rev1", "小学英语二上·Revision 1", 7, SUBJECT, None),
    (269008, "peng_g2a_domain_rev2", "小学英语二上·Revision 2", 8, SUBJECT, None),

    # Unit 1 My family
    (269010, "peng_g2a_point_family_parents", "家庭成员 father／mother：认读父母，并区分口语称呼 dad／mum", 1, SUBJECT, 269001),
    (269011, "peng_g2a_point_family_siblings", "家庭成员 brother／sister：认读哥哥弟弟与姐姐妹妹，brother 含 th 咬舌音", 2, SUBJECT, 269001),
    (269012, "peng_g2a_point_family_grandparents", "家庭成员 grandpa／grandma：认读祖父母，grand- 表示隔代长辈", 3, SUBJECT, 269001),
    (269013, "peng_g2a_point_this_is_family", "句型 This is my father.：用 this is 介绍近处的单数家人", 4, SUBJECT, 269001),
    (269014, "peng_g2a_point_he_she_family", "句型 He is my brother.／She is my sister.：用 he／she 区分男女家人", 5, SUBJECT, 269001),
    (269015, "peng_g2a_point_who_is_he", "Who's he? 与 He's my father.：询问并回答男性家庭成员身份", 6, SUBJECT, 269001),
    (269016, "peng_g2a_point_who_is_she", "Who's she? 与 She's my mother.：询问并回答女性家庭成员身份", 7, SUBJECT, 269001),
    (269017, "peng_g2a_point_my_your", "形容词性物主代词 my／your：区分“我的”与“你的”，后接名词", 8, SUBJECT, 269001),

    # Unit 2 My friends
    (269020, "peng_g2a_point_friend_tall_short", "外貌描述 tall／short：认读高与矮，搭配 be 动词描述朋友", 1, SUBJECT, 269002),
    (269021, "peng_g2a_point_friend_fat_thin", "体型描述 fat／thin：认读胖与瘦，注意 thin 的 th 咬舌音", 2, SUBJECT, 269002),
    (269022, "peng_g2a_point_he_is_friend", "句型 He is my friend.：介绍男性朋友，he 指代男性", 3, SUBJECT, 269002),
    (269023, "peng_g2a_point_she_is_friend", "句型 She is my friend.：介绍女性朋友，she 指代女性", 4, SUBJECT, 269002),
    (269024, "peng_g2a_point_who_friend", "Who's he?／Who's she? 朋友情境问答：结合照片指认并回答", 5, SUBJECT, 269002),
    (269025, "peng_g2a_point_be_adjective", "句型 He is tall.：掌握“主语＋be＋形容词”的表语结构", 6, SUBJECT, 269002),
    (269026, "peng_g2a_point_adj_noun", "形容词修饰名词：a tall boy／a short girl，形容词放在名词之前", 7, SUBJECT, 269002),
    (269027, "peng_g2a_point_he_she_it", "人称代词 he／she／it：按性别指人、按事物指物，避免混用", 8, SUBJECT, 269002),

    # Unit 3 My school
    (269030, "peng_g2a_point_school_classroom", "学校场所 classroom：认读教室，理解 class＋room 的合成构词", 1, SUBJECT, 269003),
    (269031, "peng_g2a_point_school_playground", "学校场所 playground：认读操场，理解 play＋ground 的合成构词", 2, SUBJECT, 269003),
    (269032, "peng_g2a_point_school_library", "学校场所 library：认读图书馆，注意重音位置与发音", 3, SUBJECT, 269003),
    (269033, "peng_g2a_point_this_is_school", "句型 This is my school.：向他人介绍自己的学校", 4, SUBJECT, 269003),
    (269034, "peng_g2a_point_this_is_our", "句型 This is our classroom.：用 our 介绍共同使用的场所", 5, SUBJECT, 269003),
    (269035, "peng_g2a_point_where_is_school", "Where is the library? 与 It's over there.：询问场所位置并指路", 6, SUBJECT, 269003),
    (269036, "peng_g2a_point_is_this_school", "Is this your classroom? 与 Yes, it is.／No, it isn't.：确认场所归属", 7, SUBJECT, 269003),
    (269037, "peng_g2a_point_school_prep", "介词短语 in the classroom／on the playground：场所与介词的正确搭配", 8, SUBJECT, 269003),

    # Unit 4 My body
    (269040, "peng_g2a_point_body_head_face", "身体部位 head／face：认读头与脸，并指认自己相应部位", 1, SUBJECT, 269004),
    (269041, "peng_g2a_point_body_arm_hand", "身体部位 arm／hand：认读手臂与手，注意 arm 中 ar 的读音", 2, SUBJECT, 269004),
    (269042, "peng_g2a_point_body_leg_foot", "身体部位 leg／foot：认读腿与脚，foot 的复数为不规则形式 feet", 3, SUBJECT, 269004),
    (269043, "peng_g2a_point_body_face_parts", "五官 eye／ear／nose／mouth：认读眼睛、耳朵、鼻子与嘴", 4, SUBJECT, 269004),
    (269044, "peng_g2a_point_this_is_body", "句型 This is my head.：用 this is 介绍单数身体部位", 5, SUBJECT, 269004),
    (269045, "peng_g2a_point_these_are_body", "句型 These are my hands.：复数身体部位用 these are 表达", 6, SUBJECT, 269004),
    (269046, "peng_g2a_point_body_commands", "指令 Touch your nose.／Clap your hands.：听懂身体动作指令并做出反应", 7, SUBJECT, 269004),
    (269047, "peng_g2a_point_foot_feet", "不规则复数 foot→feet：单数用 this is，复数用 these are 并同步变形", 8, SUBJECT, 269004),

    # Unit 5 My toys
    (269050, "peng_g2a_point_toy_ball_doll", "玩具词汇 ball／doll：认读球与洋娃娃并指认实物", 1, SUBJECT, 269005),
    (269051, "peng_g2a_point_toy_kite_car", "玩具词汇 kite／car：认读风筝与小汽车，注意 kite 中 i 的读音", 2, SUBJECT, 269005),
    (269052, "peng_g2a_point_toy_robot_bear", "玩具词汇 robot／teddy bear：认读机器人与泰迪熊，bear 含 ear 字母组合", 3, SUBJECT, 269005),
    (269053, "peng_g2a_point_this_is_toy", "句型 This is my toy car.：介绍自己拥有的一件玩具", 4, SUBJECT, 269005),
    (269054, "peng_g2a_point_possessive", "所属关系 my／your／his／her：按人称区分玩具归谁所有", 5, SUBJECT, 269005),
    (269055, "peng_g2a_point_whose_is_this", "Whose ball is this? 与 It's my ball.：询问并回答物品归属", 6, SUBJECT, 269005),
    (269056, "peng_g2a_point_is_this_your_toy", "Is this your doll? 与 Yes, it is.／No, it isn't.：确认玩具归属", 7, SUBJECT, 269005),
    (269057, "peng_g2a_point_toy_adjective", "形容词修饰玩具：a red kite／a big ball，颜色与大小词置于名词前", 8, SUBJECT, 269005),

    # Unit 6 My food
    (269060, "peng_g2a_point_food_apple_banana", "食物词汇 apple／banana：认读苹果与香蕉，apple 首音为元音", 1, SUBJECT, 269006),
    (269061, "peng_g2a_point_food_egg_bread", "食物词汇 egg／bread：认读鸡蛋与面包，an egg 前用 an", 2, SUBJECT, 269006),
    (269062, "peng_g2a_point_food_milk_juice", "食物词汇 milk／juice：认读牛奶与果汁，均为不可数名词", 3, SUBJECT, 269006),
    (269063, "peng_g2a_point_i_like_food", "句型 I like apples.：表达喜好，可数名词用复数泛指一类", 4, SUBJECT, 269006),
    (269064, "peng_g2a_point_i_dont_like", "句型 I don't like ...：表达不喜欢的食物，don't 后接动词原形", 5, SUBJECT, 269006),
    (269065, "peng_g2a_point_do_you_like_food", "Do you like ...? 与 Yes, I do.／No, I don't.：询问并回答饮食喜好", 6, SUBJECT, 269006),
    (269066, "peng_g2a_point_what_do_you_like", "What do you like? 与 I like ...：开放询问对方喜欢的食物", 7, SUBJECT, 269006),
    (269067, "peng_g2a_point_some_a_an", "some 与 a／an 的区别：some apples 表若干，an apple 表单数一个", 8, SUBJECT, 269006),

    # Revision 1
    (269070, "peng_g2a_point_review_family_friends", "家庭成员与朋友词汇归类复习：听音指认、分类与快速认读", 1, SUBJECT, 269007),
    (269071, "peng_g2a_point_review_he_she", "He is／She is 句型综合：结合人物图片选择正确代词", 2, SUBJECT, 269007),
    (269072, "peng_g2a_point_review_who", "Who's he?／Who's she? 情景问答复习：问答匹配与角色扮演", 3, SUBJECT, 269007),
    (269073, "peng_g2a_point_review_school", "学校场所词汇与 This is ... 介绍复习：看图说场所并组句", 4, SUBJECT, 269007),

    # Revision 2
    (269080, "peng_g2a_point_review_body_toys", "身体部位与玩具词汇归类复习：听音指认与图片配对", 1, SUBJECT, 269008),
    (269081, "peng_g2a_point_review_this_these", "This is／These are 单复数复习：按图片数量选择正确句型", 2, SUBJECT, 269008),
    (269082, "peng_g2a_point_review_like", "喜好表达复习：I like ...／Do you like ...? 的问答与替换练习", 3, SUBJECT, 269008),
    (269083, "peng_g2a_point_vowel_letters", "元音字母 Aa Ee Ii Oo Uu 初步认读：识别五个元音字母并感知短音", 4, SUBJECT, 269008),
)

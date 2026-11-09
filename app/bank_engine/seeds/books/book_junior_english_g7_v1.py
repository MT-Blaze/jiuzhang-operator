"""人教版（Go for it!）七年级英语上册：Starter Unit 1—3 与 Unit 1—9 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G7 = 7
BOOK_ID = 1325

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版七年级英语上册",
    "jeng_g7a",
    25,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Starter Units
    (132501, "Starter Unit 1 Good morning!", "jeng_g7a_starter1", 1, BOOK_ID, None),
    (132521, "Section A", "jeng_g7a_starter1_a", 1, BOOK_ID, 132501),
    (132522, "Section B", "jeng_g7a_starter1_b", 2, BOOK_ID, 132501),
    (132502, "Starter Unit 2 What's this in English?", "jeng_g7a_starter2", 2, BOOK_ID, None),
    (132523, "Section A", "jeng_g7a_starter2_a", 1, BOOK_ID, 132502),
    (132524, "Section B", "jeng_g7a_starter2_b", 2, BOOK_ID, 132502),
    (132503, "Starter Unit 3 What color is it?", "jeng_g7a_starter3", 3, BOOK_ID, None),
    (132525, "Section A", "jeng_g7a_starter3_a", 1, BOOK_ID, 132503),
    (132526, "Section B", "jeng_g7a_starter3_b", 2, BOOK_ID, 132503),

    # Units 1—9
    (132504, "Unit 1 My name's Gina.", "jeng_g7a_u01", 4, BOOK_ID, None),
    (132527, "Section A", "jeng_g7a_u01_a", 1, BOOK_ID, 132504),
    (132528, "Section B", "jeng_g7a_u01_b", 2, BOOK_ID, 132504),
    (132505, "Unit 2 This is my sister.", "jeng_g7a_u02", 5, BOOK_ID, None),
    (132529, "Section A", "jeng_g7a_u02_a", 1, BOOK_ID, 132505),
    (132530, "Section B", "jeng_g7a_u02_b", 2, BOOK_ID, 132505),
    (132506, "Unit 3 Is this your pencil?", "jeng_g7a_u03", 6, BOOK_ID, None),
    (132531, "Section A", "jeng_g7a_u03_a", 1, BOOK_ID, 132506),
    (132532, "Section B", "jeng_g7a_u03_b", 2, BOOK_ID, 132506),
    (132507, "Unit 4 Where's my schoolbag?", "jeng_g7a_u04", 7, BOOK_ID, None),
    (132533, "Section A", "jeng_g7a_u04_a", 1, BOOK_ID, 132507),
    (132534, "Section B", "jeng_g7a_u04_b", 2, BOOK_ID, 132507),
    (132508, "Unit 5 Do you have a soccer ball?", "jeng_g7a_u05", 8, BOOK_ID, None),
    (132535, "Section A", "jeng_g7a_u05_a", 1, BOOK_ID, 132508),
    (132536, "Section B", "jeng_g7a_u05_b", 2, BOOK_ID, 132508),
    (132509, "Unit 6 Do you like bananas?", "jeng_g7a_u06", 9, BOOK_ID, None),
    (132537, "Section A", "jeng_g7a_u06_a", 1, BOOK_ID, 132509),
    (132538, "Section B", "jeng_g7a_u06_b", 2, BOOK_ID, 132509),
    (132510, "Unit 7 How much are these socks?", "jeng_g7a_u07", 10, BOOK_ID, None),
    (132539, "Section A", "jeng_g7a_u07_a", 1, BOOK_ID, 132510),
    (132540, "Section B", "jeng_g7a_u07_b", 2, BOOK_ID, 132510),
    (132511, "Unit 8 When is your birthday?", "jeng_g7a_u08", 11, BOOK_ID, None),
    (132541, "Section A", "jeng_g7a_u08_a", 1, BOOK_ID, 132511),
    (132542, "Section B", "jeng_g7a_u08_b", 2, BOOK_ID, 132511),
    (132512, "Unit 9 My favorite subject is science.", "jeng_g7a_u09", 12, BOOK_ID, None),
    (132543, "Section A", "jeng_g7a_u09_a", 1, BOOK_ID, 132512),
    (132544, "Section B", "jeng_g7a_u09_b", 2, BOOK_ID, 132512),
)

# id / code / name / sort_order / subject_id / parent_id
# 225001-225013 为册域层，225014-225077 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (225001, "jeng_g7a_domain_letters", "初中七上·字母与音标", 1, SUBJECT, None),
    (225002, "jeng_g7a_domain_greetings", "初中七上·问候与自我介绍", 2, SUBJECT, None),
    (225003, "jeng_g7a_domain_be_verb", "初中七上·be 动词与介绍他人", 3, SUBJECT, None),
    (225004, "jeng_g7a_domain_demonstratives", "初中七上·指示代词与物品辨认", 4, SUBJECT, None),
    (225005, "jeng_g7a_domain_colors", "初中七上·颜色与形容描述", 5, SUBJECT, None),
    (225006, "jeng_g7a_domain_family", "初中七上·家庭成员与名词所有格", 6, SUBJECT, None),
    (225007, "jeng_g7a_domain_possessive", "初中七上·物主代词与失物招领", 7, SUBJECT, None),
    (225008, "jeng_g7a_domain_prepositions", "初中七上·方位介词与房间陈设", 8, SUBJECT, None),
    (225009, "jeng_g7a_domain_present_simple", "初中七上·一般现在时与球类运动", 9, SUBJECT, None),
    (225010, "jeng_g7a_domain_food", "初中七上·食物与 like 句型", 10, SUBJECT, None),
    (225011, "jeng_g7a_domain_shopping", "初中七上·购物与问价", 11, SUBJECT, None),
    (225012, "jeng_g7a_domain_dates", "初中七上·日期与生日", 12, SUBJECT, None),
    (225013, "jeng_g7a_domain_subjects", "初中七上·学科与课程安排", 13, SUBJECT, None),

    # 字母与音标
    (225014, "jeng_g7a_point_letters_ah", "字母 Aa—Hh 的大小写书写规范与升降调读音", 1, SUBJECT, 225001),
    (225015, "jeng_g7a_point_alphabet_order", "26 个字母的排列顺序与字母表默写", 2, SUBJECT, 225001),
    (225016, "jeng_g7a_point_vowel_letters", "元音字母 Aa、Ee、Ii、Oo、Uu 的识别与开音节读音", 3, SUBJECT, 225001),
    (225017, "jeng_g7a_point_letters_ir", "字母 Ii—Rr 的读音及 CD、BBC 等常见缩略词", 4, SUBJECT, 225001),
    (225018, "jeng_g7a_point_letters_sz", "字母 Ss—Zz 的读音与字母组合发音归类", 5, SUBJECT, 225001),

    # 问候与自我介绍
    (225019, "jeng_g7a_point_greeting_time", "Good morning/afternoon/evening 的时段划分与对应应答", 1, SUBJECT, 225002),
    (225020, "jeng_g7a_point_how_are_you", "How are you? 与 I'm fine, thanks. 的问候应答链", 2, SUBJECT, 225002),
    (225021, "jeng_g7a_point_name_question", "What's your name? 与 My name's... 的姓名问答", 3, SUBJECT, 225002),
    (225022, "jeng_g7a_point_possessive_adj", "形容词性物主代词 my/your/his/her 的指代与位置", 4, SUBJECT, 225002),
    (225023, "jeng_g7a_point_nice_to_meet", "Nice to meet you. 及初次见面的交际用语与回应", 5, SUBJECT, 225002),

    # be 动词与介绍他人
    (225024, "jeng_g7a_point_be_person", "am/is/are 与 I、he/she/it、you/we/they 的人称搭配", 1, SUBJECT, 225003),
    (225025, "jeng_g7a_point_be_negative_question", "be 动词否定句与一般疑问句的构成及简答", 2, SUBJECT, 225003),
    (225026, "jeng_g7a_point_his_her_name", "What's his/her name? 与介绍他人的句型转换", 3, SUBJECT, 225003),
    (225027, "jeng_g7a_point_first_last_name", "first name 与 last name：中英文姓名顺序差异", 4, SUBJECT, 225003),

    # 指示代词与物品辨认
    (225028, "jeng_g7a_point_this_that", "this/that 的远近指代与 What's this/that in English? 问答", 1, SUBJECT, 225004),
    (225029, "jeng_g7a_point_a_an", "不定冠词 a 与 an 的选择：以元音音素开头用 an", 2, SUBJECT, 225004),
    (225030, "jeng_g7a_point_these_those", "these/those 与复数名词、are 的搭配使用", 3, SUBJECT, 225004),
    (225031, "jeng_g7a_point_spelling", "How do you spell it? 与 Spell it, please. 的拼写问答", 4, SUBJECT, 225004),
    (225032, "jeng_g7a_point_school_things", "学习用品词汇：pen、ruler、eraser、schoolbag、dictionary 等", 5, SUBJECT, 225004),

    # 颜色与形容描述
    (225033, "jeng_g7a_point_color_question", "What color is/are...? 的颜色问答与 It's/They're 应答", 1, SUBJECT, 225005),
    (225034, "jeng_g7a_point_color_words", "颜色词 red、yellow、blue、green、black、white 等的认读", 2, SUBJECT, 225005),
    (225035, "jeng_g7a_point_adj_position", "形容词作定语（red pen）与作表语（It's red.）的位置差异", 3, SUBJECT, 225005),
    (225036, "jeng_g7a_point_definite_the", "定冠词 the 特指上文出现过或双方已知的事物", 4, SUBJECT, 225005),

    # 家庭成员与名词所有格
    (225037, "jeng_g7a_point_family_words", "家庭成员词汇：father、mother、brother、sister、grandparent 等", 1, SUBJECT, 225006),
    (225038, "jeng_g7a_point_family_demonstratives", "用 this/that/these/those 介绍家人的单复数表达", 2, SUBJECT, 225006),
    (225039, "jeng_g7a_point_who_is", "Who's he/she? 问答与人称代词主格 he/she/they 的指代", 3, SUBJECT, 225006),
    (225040, "jeng_g7a_point_plural_regular", "名词复数规则变化：一般加 -s，s/x/ch/sh 结尾加 -es，辅音字母+y 变 y 为 i 加 -es", 4, SUBJECT, 225006),
    (225041, "jeng_g7a_point_plural_irregular", "名词复数不规则变化：man→men、woman→women、child→children", 5, SUBJECT, 225006),
    (225042, "jeng_g7a_point_possessive_noun", "名词所有格 's 的构成及 of 短语的所属表达", 6, SUBJECT, 225006),

    # 物主代词与失物招领
    (225043, "jeng_g7a_point_nominal_possessive", "名词性物主代词 mine/yours/his/hers/ours/theirs 的用法", 1, SUBJECT, 225007),
    (225044, "jeng_g7a_point_is_this_yours", "Is this yours? 的一般疑问句、肯定与否定简答", 2, SUBJECT, 225007),
    (225045, "jeng_g7a_point_possessive_compare", "形容词性物主代词与名词性物主代词的区别：后是否接名词", 3, SUBJECT, 225007),
    (225046, "jeng_g7a_point_lost_found", "失物招领启事（Lost and Found）的要素与写作格式", 4, SUBJECT, 225007),

    # 方位介词与房间陈设
    (225047, "jeng_g7a_point_where_question", "Where's/Where are...? 的方位问答与 It's/They're 应答", 1, SUBJECT, 225008),
    (225048, "jeng_g7a_point_prep_in_on_under", "方位介词 in/on/under 的空间意义辨析", 2, SUBJECT, 225008),
    (225049, "jeng_g7a_point_furniture", "家具与房间陈设词汇：bed、table、bookcase、sofa、chair、drawer", 3, SUBJECT, 225008),
    (225050, "jeng_g7a_point_prep_phrase", "介词短语作后置定语：the keys on the table 的语序", 4, SUBJECT, 225008),

    # 一般现在时与球类运动
    (225051, "jeng_g7a_point_have_has", "have/has 的第三人称单数变化及肯定句用法", 1, SUBJECT, 225009),
    (225052, "jeng_g7a_point_do_does_question", "Do/Does 引导的一般疑问句、否定句与简答", 2, SUBJECT, 225009),
    (225053, "jeng_g7a_point_lets", "Let's + 动词原形表示建议及 Let's... 的应答", 3, SUBJECT, 225009),
    (225054, "jeng_g7a_point_activity_adjectives", "形容词 fun/interesting/boring/difficult/relaxing 评价活动", 4, SUBJECT, 225009),
    (225055, "jeng_g7a_point_play_sports", "play + 球类/棋类与 play + the + 乐器的搭配规则", 5, SUBJECT, 225009),

    # 食物与 like 句型
    (225056, "jeng_g7a_point_like_question", "Do you like...? 问答及 like 后接名词的用法", 1, SUBJECT, 225010),
    (225057, "jeng_g7a_point_countable", "可数名词与不可数名词的区分：banana 与 milk 的表达差异", 2, SUBJECT, 225010),
    (225058, "jeng_g7a_point_meals", "三餐词汇与 have...for breakfast/lunch/dinner 的句型", 3, SUBJECT, 225010),
    (225059, "jeng_g7a_point_like_third_person", "一般现在时第三人称单数 like→likes 的变化与运用", 4, SUBJECT, 225010),
    (225060, "jeng_g7a_point_healthy_food", "healthy food 与饮食喜好、健康饮食习惯的表达", 5, SUBJECT, 225010),

    # 购物与问价
    (225061, "jeng_g7a_point_how_much", "How much is/are...? 的价格问答与 It's/They're... dollars 应答", 1, SUBJECT, 225011),
    (225062, "jeng_g7a_point_numbers", "基数词 10—31、整十与百位的读法与拼写", 2, SUBJECT, 225011),
    (225063, "jeng_g7a_point_clothes", "服装词汇：socks、T-shirt、shorts、trousers、sweater、skirt", 3, SUBJECT, 225011),
    (225064, "jeng_g7a_point_size_adjectives", "big/small/short/long 描述商品大小与长短", 4, SUBJECT, 225011),
    (225065, "jeng_g7a_point_shopping_dialogue", "购物交际用语：Can I help you? 与 I'll take it.", 5, SUBJECT, 225011),
    (225066, "jeng_g7a_point_pair_of", "a pair of 与复数商品的数量、价格表达", 6, SUBJECT, 225011),

    # 日期与生日
    (225067, "jeng_g7a_point_months", "十二个月份词汇 January—December 的认读与拼写", 1, SUBJECT, 225012),
    (225068, "jeng_g7a_point_ordinals", "序数词 1st—31st 的构成规则与缩写形式", 2, SUBJECT, 225012),
    (225069, "jeng_g7a_point_birthday_date", "When is your birthday? 与 on + 月日 的日期表达", 3, SUBJECT, 225012),
    (225070, "jeng_g7a_point_age", "How old are you? 与年龄、出生年份的表达", 4, SUBJECT, 225012),
    (225071, "jeng_g7a_point_birthday_party", "生日聚会邀请与 party、present 等相关词汇", 5, SUBJECT, 225012),
    (225072, "jeng_g7a_point_time_prepositions", "时间介词 in/on/at 在年份、日期、钟点前的辨析", 6, SUBJECT, 225012),

    # 学科与课程安排
    (225073, "jeng_g7a_point_subjects", "学科词汇：science、math、English、Chinese、history、art 等", 1, SUBJECT, 225013),
    (225074, "jeng_g7a_point_favorite_subject", "What's your favorite subject? 与 favorite 的用法", 2, SUBJECT, 225013),
    (225075, "jeng_g7a_point_why_because", "Why...? Because... 的因果问答与回答完整性", 3, SUBJECT, 225013),
    (225076, "jeng_g7a_point_weekdays", "星期词汇 Monday—Sunday 的认读与缩写", 4, SUBJECT, 225013),
    (225077, "jeng_g7a_point_schedule_time", "at + 钟点、on + 星期的课程时间表达", 5, SUBJECT, 225013),
)

"""人教版（PEP 2024）小学英语四年级上册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G4 = 4
BOOK_ID = 1431

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语四年级上册",
    "peng_g4a",
    31,
    "人民教育出版社",
    SUBJECT,
    G4,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 Helping at home
    (143101, "Unit 1 Helping at home", "peng_g4a_u01", 1, BOOK_ID, None),
    (143102, "Part A", "peng_g4a_u01_a", 1, BOOK_ID, 143101),
    (143103, "Part B", "peng_g4a_u01_b", 2, BOOK_ID, 143101),
    (143104, "Part C", "peng_g4a_u01_c", 3, BOOK_ID, 143101),

    # Unit 2 My friends
    (143105, "Unit 2 My friends", "peng_g4a_u02", 2, BOOK_ID, None),
    (143106, "Part A", "peng_g4a_u02_a", 1, BOOK_ID, 143105),
    (143107, "Part B", "peng_g4a_u02_b", 2, BOOK_ID, 143105),
    (143108, "Part C", "peng_g4a_u02_c", 3, BOOK_ID, 143105),

    # Unit 3 Places we live in
    (143109, "Unit 3 Places we live in", "peng_g4a_u03", 3, BOOK_ID, None),
    (143110, "Part A", "peng_g4a_u03_a", 1, BOOK_ID, 143109),
    (143111, "Part B", "peng_g4a_u03_b", 2, BOOK_ID, 143109),
    (143112, "Part C", "peng_g4a_u03_c", 3, BOOK_ID, 143109),

    # Unit 4 My home
    (143113, "Unit 4 My home", "peng_g4a_u04", 4, BOOK_ID, None),
    (143114, "Part A", "peng_g4a_u04_a", 1, BOOK_ID, 143113),
    (143115, "Part B", "peng_g4a_u04_b", 2, BOOK_ID, 143113),
    (143116, "Part C", "peng_g4a_u04_c", 3, BOOK_ID, 143113),

    # Unit 5 The weather and us
    (143117, "Unit 5 The weather and us", "peng_g4a_u05", 5, BOOK_ID, None),
    (143118, "Part A", "peng_g4a_u05_a", 1, BOOK_ID, 143117),
    (143119, "Part B", "peng_g4a_u05_b", 2, BOOK_ID, 143117),
    (143120, "Part C", "peng_g4a_u05_c", 3, BOOK_ID, 143117),

    # Unit 6 Jobs
    (143121, "Unit 6 Jobs", "peng_g4a_u06", 6, BOOK_ID, None),
    (143122, "Part A", "peng_g4a_u06_a", 1, BOOK_ID, 143121),
    (143123, "Part B", "peng_g4a_u06_b", 2, BOOK_ID, 143121),
    (143124, "Part C", "peng_g4a_u06_c", 3, BOOK_ID, 143121),

    # Revision
    (143125, "Revision 1", "peng_g4a_rev1", 7, BOOK_ID, None),
    (143126, "Revision 2", "peng_g4a_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / parent_id
# 273001-273008 为册域层，273010-273099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (273001, "peng_g4a_domain_u01", "小学英语四上·Unit 1 Helping at home", 1, SUBJECT, None),
    (273002, "peng_g4a_domain_u02", "小学英语四上·Unit 2 My friends", 2, SUBJECT, None),
    (273003, "peng_g4a_domain_u03", "小学英语四上·Unit 3 Places we live in", 3, SUBJECT, None),
    (273004, "peng_g4a_domain_u04", "小学英语四上·Unit 4 My home", 4, SUBJECT, None),
    (273005, "peng_g4a_domain_u05", "小学英语四上·Unit 5 The weather and us", 5, SUBJECT, None),
    (273006, "peng_g4a_domain_u06", "小学英语四上·Unit 6 Jobs", 6, SUBJECT, None),
    (273007, "peng_g4a_domain_rev1", "小学英语四上·Revision 1", 7, SUBJECT, None),
    (273008, "peng_g4a_domain_rev2", "小学英语四上·Revision 2", 8, SUBJECT, None),

    # Unit 1 Helping at home
    (273010, "peng_g4a_point_chore_verbs_a", "家务动词 sweep the floor／clean the room／wash the dishes／make the bed：认读并搭配", 1, SUBJECT, 273001),
    (273011, "peng_g4a_point_chore_verbs_b", "家务动词 cook the meal／water the plants／feed the pet／take out the rubbish：认读并搭配", 2, SUBJECT, 273001),
    (273012, "peng_g4a_point_what_do_at_home", "句型 What do you do at home? 与 I often help my mum.：询问并回答家务分担", 3, SUBJECT, 273001),
    (273013, "peng_g4a_point_third_person_chore", "句型 What does he do at home? 与 He usually washes the dishes.：does 提问，动词还原", 4, SUBJECT, 273001),
    (273014, "peng_g4a_point_third_person_s", "一般现在时第三人称单数：helps／washes／does／goes 加 -s 或 -es 的变化规则", 5, SUBJECT, 273001),
    (273015, "peng_g4a_point_frequency_adverbs", "频率副词 always／usually／often／sometimes／never：位于实义动词前、be 动词后", 6, SUBJECT, 273001),
    (273016, "peng_g4a_point_can_ability_home", "情态动词 can 表能力：I can make the bed.／She can cook noodles.，后接动词原形", 7, SUBJECT, 273001),
    (273017, "peng_g4a_point_must_obligation", "情态动词 must 表义务：We must keep our home clean.／You must help your parents.", 8, SUBJECT, 273001),
    (273018, "peng_g4a_point_who_sweeps", "句型 Who sweeps the floor? 与 I do.／My dad does.：用 do／does 替代前文动词", 9, SUBJECT, 273001),
    (273019, "peng_g4a_point_offer_help", "提供帮助 Let me help you.／Can I help you? 与 Thank you.：礼貌回应他人", 10, SUBJECT, 273001),
    (273020, "peng_g4a_point_phonics_er", "字母组合 er 在词尾发 /ə/：helper, sweeper, teacher, water 的弱读音", 11, SUBJECT, 273001),

    # Unit 2 My friends
    (273021, "peng_g4a_point_appearance_adjectives", "外貌形容词 tall／short／thin／heavy：用 be 动词描述朋友体型", 1, SUBJECT, 273002),
    (273022, "peng_g4a_point_hair_eyes", "头发与五官 long hair／short hair／big eyes／small eyes：搭配 has 描述特征", 2, SUBJECT, 273002),
    (273023, "peng_g4a_point_personality_words", "性格词汇 friendly／quiet／clever／kind／funny／hard-working：认读并分类", 3, SUBJECT, 273002),
    (273024, "peng_g4a_point_what_like", "句型 What's he/she like? 与 He's friendly.／She's quiet.：询问并回答性格", 4, SUBJECT, 273002),
    (273025, "peng_g4a_point_has_appearance", "句型 He has short hair.／She has big eyes.：第三人称单数用 has 描述外貌", 5, SUBJECT, 273002),
    (273026, "peng_g4a_point_is_vs_has", "is 与 has 的分工：性格用 is，外貌特征用 has，不可混用", 6, SUBJECT, 273002),
    (273027, "peng_g4a_point_who_is_friend", "句型 Who is your friend? 与 ... is my friend.：介绍自己的朋友", 7, SUBJECT, 273002),
    (273028, "peng_g4a_point_plural_describe", "复数描述 They are friendly.／They have long hair.：be 与 have 随主语复数还原", 8, SUBJECT, 273002),
    (273029, "peng_g4a_point_can_friend", "能力描述 My friend can sing well.：can 后接动词原形，不随人称变化", 9, SUBJECT, 273002),
    (273030, "peng_g4a_point_greeting_friend", "交友用语 Nice to meet you.／Glad to meet you. 与 Nice to meet you, too.：初次见面应答", 10, SUBJECT, 273002),

    # Unit 3 Places we live in
    (273031, "peng_g4a_point_place_words_a", "社区场所 park／supermarket／library／hospital：认读并说出功能", 1, SUBJECT, 273003),
    (273032, "peng_g4a_point_place_words_b", "社区场所 school／post office／zoo／restaurant：认读并注意 post office 连写", 2, SUBJECT, 273003),
    (273033, "peng_g4a_point_there_be_community", "There be 句型：There is a park near my home.／There are two shops.", 3, SUBJECT, 273003),
    (273034, "peng_g4a_point_where_is_place", "句型 Where is the library? 与 It's next to the park.：询问场所位置", 4, SUBJECT, 273003),
    (273035, "peng_g4a_point_preposition_a", "方位介词 next to／between／behind：描述场所相对位置", 5, SUBJECT, 273003),
    (273036, "peng_g4a_point_preposition_b", "方位介词 in front of／across from／near：描述场所相对位置", 6, SUBJECT, 273003),
    (273037, "peng_g4a_point_is_there_near", "句型 Is there a ... near here? 与 Yes, there is.／No, there isn't.：确认附近场所", 7, SUBJECT, 273003),
    (273038, "peng_g4a_point_ask_the_way", "问路句型 Excuse me, how can I get to the zoo?：礼貌询问路线", 8, SUBJECT, 273003),
    (273039, "peng_g4a_point_give_directions", "指路祈使句 Go straight.／Turn left at the crossing.／Turn right.：动词原形开头", 9, SUBJECT, 273003),
    (273040, "peng_g4a_point_place_function", "场所功能 We can read books in the library.／We can buy food in the supermarket.", 10, SUBJECT, 273003),
    (273041, "peng_g4a_point_can_permission", "情态动词 can 表许可 You can take a bus to the park.：提出可行方式", 11, SUBJECT, 273003),

    # Unit 4 My home
    (273042, "peng_g4a_point_room_words", "房间词汇 bedroom／living room／kitchen／bathroom／study：认读并对应家庭功能区", 1, SUBJECT, 273004),
    (273043, "peng_g4a_point_furniture_words", "家具词汇 bed／sofa／table／chair／fridge／TV／desk：认读并搭配所在房间", 2, SUBJECT, 273004),
    (273044, "peng_g4a_point_there_is_home", "There is a sofa in the living room.：There is 后接可数名词单数或不可数名词", 3, SUBJECT, 273004),
    (273045, "peng_g4a_point_there_are_home", "There are two chairs in the kitchen.：There are 后接可数名词复数", 4, SUBJECT, 273004),
    (273046, "peng_g4a_point_where_in_on_under", "句型 Where is the cat? 与 It's on／in／under the bed.：介词区分位置", 5, SUBJECT, 273004),
    (273047, "peng_g4a_point_where_behind_near", "方位介词 behind／near／next to：Where are the books? 与 They're behind the door.", 6, SUBJECT, 273004),
    (273048, "peng_g4a_point_is_there_home", "句型 Is there a study in your home? 与 Yes, there is.／No, there isn't.：单数确认", 7, SUBJECT, 273004),
    (273049, "peng_g4a_point_are_there_home", "句型 Are there any pictures on the wall? 与 Yes, there are.／No, there aren't.", 8, SUBJECT, 273004),
    (273050, "peng_g4a_point_phrase_modifier", "介词短语后置修饰 the book on the desk／the ball under the chair：先中心词后位置", 9, SUBJECT, 273004),
    (273051, "peng_g4a_point_describe_home", "描述自己的家 My home is big and clean. There is a ... in my room.", 10, SUBJECT, 273004),
    (273052, "peng_g4a_point_phonics_oo", "字母组合 oo 发音：/ʊ/ 如 book, look；/uː/ 如 room, food", 11, SUBJECT, 273004),

    # Unit 5 The weather and us
    (273053, "peng_g4a_point_weather_words", "天气词汇 sunny／rainy／cloudy／windy／snowy：由名词加 -y 构成形容词", 1, SUBJECT, 273005),
    (273054, "peng_g4a_point_temperature_words", "温度词汇 hot／cold／warm／cool：描述四季与体感温度", 2, SUBJECT, 273005),
    (273055, "peng_g4a_point_whats_weather_like", "句型 What's the weather like today? 与 It's sunny.：询问并回答天气", 3, SUBJECT, 273005),
    (273056, "peng_g4a_point_hows_weather", "句型 How's the weather? 与 It's windy and cool.：用并列形容词描述天气", 4, SUBJECT, 273005),
    (273057, "peng_g4a_point_weather_activities", "天气活动 fly a kite on a windy day／make a snowman on a snowy day", 5, SUBJECT, 273005),
    (273058, "peng_g4a_point_can_weather_advice", "情态动词 can 表建议 You can wear a coat.／You can play outside.", 6, SUBJECT, 273005),
    (273059, "peng_g4a_point_must_weather", "情态动词 must 表提醒 You must take an umbrella.／We must stay at home.", 7, SUBJECT, 273005),
    (273060, "peng_g4a_point_frequency_weather", "频率副词与天气 It's sometimes rainy in spring.／It's always hot in summer.", 8, SUBJECT, 273005),
    (273061, "peng_g4a_point_degrees", "温度表达 It's twenty degrees.／It's five degrees below zero.：读法与含义", 9, SUBJECT, 273005),
    (273062, "peng_g4a_point_weather_clothes", "天气与衣物匹配 raincoat／boots／sunglasses／scarf：按天气选择穿戴", 10, SUBJECT, 273005),

    # Unit 6 Jobs
    (273063, "peng_g4a_point_job_words_a", "职业词汇 doctor／nurse／teacher／farmer：认读并说出职业名称", 1, SUBJECT, 273006),
    (273064, "peng_g4a_point_job_words_b", "职业词汇 driver／cook／police officer／worker：认读并注意 police officer 拼写", 2, SUBJECT, 273006),
    (273065, "peng_g4a_point_what_does_he_do", "句型 What does he/she do? 与 He's a doctor.／She's a nurse.：询问职业", 3, SUBJECT, 273006),
    (273066, "peng_g4a_point_work_place", "工作地点 in a hospital／in a school／on a farm／in a restaurant：介词搭配", 4, SUBJECT, 273006),
    (273067, "peng_g4a_point_where_does_work", "句型 Where does he work? 与 He works in a hospital.：does 提问，works 三单", 5, SUBJECT, 273006),
    (273068, "peng_g4a_point_third_person_job", "第三人称单数 works／teaches／helps／drives：一般现在时动词变化", 6, SUBJECT, 273006),
    (273069, "peng_g4a_point_want_to_be", "句型 What do you want to be? 与 I want to be a teacher.：表达职业理想", 7, SUBJECT, 273006),
    (273070, "peng_g4a_point_job_duty", "职业职责 A doctor helps sick people.／A teacher teaches students.：用三单描述职责", 8, SUBJECT, 273006),
    (273071, "peng_g4a_point_must_job", "情态动词 must 表职业要求 A driver must be careful.／A nurse must be kind.", 9, SUBJECT, 273006),
    (273072, "peng_g4a_point_job_plural", "职业名词复数 doctors／nurses／teachers／police officers：一般加 -s", 10, SUBJECT, 273006),
    (273073, "peng_g4a_point_phonics_er_or", "词尾 er／or 发 /ə/：teacher, farmer, doctor, worker 的弱读音", 11, SUBJECT, 273006),

    # Revision 1
    (273074, "peng_g4a_point_review_units_1_3_words", "Units 1—3 词汇复习：家务、性格外貌、社区场所分类认读", 1, SUBJECT, 273007),
    (273075, "peng_g4a_point_review_units_1_3_sentences", "句型复习 What do you do at home?／What's he like?／Where is the library?", 2, SUBJECT, 273007),
    (273076, "peng_g4a_point_review_units_1_3_grammar", "语法复习：一般现在时三单变化、There be 与方位介词综合运用", 3, SUBJECT, 273007),
    (273077, "peng_g4a_point_review_units_1_3_dialogue", "综合情景对话：介绍朋友、分担家务、为他人指路", 4, SUBJECT, 273007),

    # Revision 2
    (273078, "peng_g4a_point_review_units_4_6_words", "Units 4—6 词汇复习：房间家具、天气、职业分类认读", 1, SUBJECT, 273008),
    (273079, "peng_g4a_point_review_units_4_6_sentences", "句型复习 What's the weather like?／What does he do?／Is there a ...?", 2, SUBJECT, 273008),
    (273080, "peng_g4a_point_review_units_4_6_grammar", "语法复习：can 与 must、第三人称单数、There is／are 问答", 3, SUBJECT, 273008),
    (273081, "peng_g4a_point_review_units_4_6_project", "项目展示：绘制理想之家并介绍家人职业与天气活动安排", 4, SUBJECT, 273008),
)

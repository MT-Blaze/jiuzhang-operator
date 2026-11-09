"""人教版（Go for it!）七年级英语下册：Unit 1—12 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G7 = 7
BOOK_ID = 1326

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版七年级英语下册",
    "jeng_g7b",
    26,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1—12，每单元下挂 Section A／Section B
    (132601, "Unit 1 Can you play the guitar?", "jeng_g7b_u01", 1, BOOK_ID, None),
    (132621, "Section A", "jeng_g7b_u01_a", 1, BOOK_ID, 132601),
    (132622, "Section B", "jeng_g7b_u01_b", 2, BOOK_ID, 132601),
    (132602, "Unit 2 What time do you go to school?", "jeng_g7b_u02", 2, BOOK_ID, None),
    (132623, "Section A", "jeng_g7b_u02_a", 1, BOOK_ID, 132602),
    (132624, "Section B", "jeng_g7b_u02_b", 2, BOOK_ID, 132602),
    (132603, "Unit 3 How do you get to school?", "jeng_g7b_u03", 3, BOOK_ID, None),
    (132625, "Section A", "jeng_g7b_u03_a", 1, BOOK_ID, 132603),
    (132626, "Section B", "jeng_g7b_u03_b", 2, BOOK_ID, 132603),
    (132604, "Unit 4 Don't eat in class.", "jeng_g7b_u04", 4, BOOK_ID, None),
    (132627, "Section A", "jeng_g7b_u04_a", 1, BOOK_ID, 132604),
    (132628, "Section B", "jeng_g7b_u04_b", 2, BOOK_ID, 132604),
    (132605, "Unit 5 Why do you like pandas?", "jeng_g7b_u05", 5, BOOK_ID, None),
    (132629, "Section A", "jeng_g7b_u05_a", 1, BOOK_ID, 132605),
    (132630, "Section B", "jeng_g7b_u05_b", 2, BOOK_ID, 132605),
    (132606, "Unit 6 I'm watching TV.", "jeng_g7b_u06", 6, BOOK_ID, None),
    (132631, "Section A", "jeng_g7b_u06_a", 1, BOOK_ID, 132606),
    (132632, "Section B", "jeng_g7b_u06_b", 2, BOOK_ID, 132606),
    (132607, "Unit 7 It's raining!", "jeng_g7b_u07", 7, BOOK_ID, None),
    (132633, "Section A", "jeng_g7b_u07_a", 1, BOOK_ID, 132607),
    (132634, "Section B", "jeng_g7b_u07_b", 2, BOOK_ID, 132607),
    (132608, "Unit 8 Is there a post office near here?", "jeng_g7b_u08", 8, BOOK_ID, None),
    (132635, "Section A", "jeng_g7b_u08_a", 1, BOOK_ID, 132608),
    (132636, "Section B", "jeng_g7b_u08_b", 2, BOOK_ID, 132608),
    (132609, "Unit 9 What does he look like?", "jeng_g7b_u09", 9, BOOK_ID, None),
    (132637, "Section A", "jeng_g7b_u09_a", 1, BOOK_ID, 132609),
    (132638, "Section B", "jeng_g7b_u09_b", 2, BOOK_ID, 132609),
    (132610, "Unit 10 I'd like some noodles.", "jeng_g7b_u10", 10, BOOK_ID, None),
    (132639, "Section A", "jeng_g7b_u10_a", 1, BOOK_ID, 132610),
    (132640, "Section B", "jeng_g7b_u10_b", 2, BOOK_ID, 132610),
    (132611, "Unit 11 How was your school trip?", "jeng_g7b_u11", 11, BOOK_ID, None),
    (132641, "Section A", "jeng_g7b_u11_a", 1, BOOK_ID, 132611),
    (132642, "Section B", "jeng_g7b_u11_b", 2, BOOK_ID, 132611),
    (132612, "Unit 12 What did you do last weekend?", "jeng_g7b_u12", 12, BOOK_ID, None),
    (132643, "Section A", "jeng_g7b_u12_a", 1, BOOK_ID, 132612),
    (132644, "Section B", "jeng_g7b_u12_b", 2, BOOK_ID, 132612),
)

# id / code / name / sort_order / subject_id / parent_id
# 226001-226013 为册域层，226014-226081 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (226001, "jeng_g7b_domain_can_clubs", "初中七下·情态动词 can 与俱乐部", 1, SUBJECT, None),
    (226002, "jeng_g7b_domain_daily_time", "初中七下·时间表达与日常作息", 2, SUBJECT, None),
    (226003, "jeng_g7b_domain_transport", "初中七下·交通方式与路程问答", 3, SUBJECT, None),
    (226004, "jeng_g7b_domain_imperative_rules", "初中七下·祈使句与规章制度", 4, SUBJECT, None),
    (226005, "jeng_g7b_domain_animals", "初中七下·动物描述与原因表达", 5, SUBJECT, None),
    (226006, "jeng_g7b_domain_present_continuous", "初中七下·现在进行时与电话交际", 6, SUBJECT, None),
    (226007, "jeng_g7b_domain_weather", "初中七下·天气描述与假期问候", 7, SUBJECT, None),
    (226008, "jeng_g7b_domain_there_be", "初中七下·there be 句型与问路指路", 8, SUBJECT, None),
    (226009, "jeng_g7b_domain_appearance", "初中七下·外貌描述与选择疑问句", 9, SUBJECT, None),
    (226010, "jeng_g7b_domain_ordering", "初中七下·可数与不可数名词与点餐", 10, SUBJECT, None),
    (226011, "jeng_g7b_domain_past_school_trip", "初中七下·一般过去时与学校旅行", 11, SUBJECT, None),
    (226012, "jeng_g7b_domain_past_weekend", "初中七下·一般过去时不规则动词与周末活动", 12, SUBJECT, None),
    (226013, "jeng_g7b_domain_phonics_intonation", "初中七下·语音、重音与语调", 13, SUBJECT, None),

    # 情态动词 can 与俱乐部
    (226014, "jeng_g7b_point_can_ability", "can + 动词原形表示能力的肯定句与否定句 can't", 1, SUBJECT, 226001),
    (226015, "jeng_g7b_point_can_question", "Can you...? 一般疑问句及 Yes, I can./No, I can't. 简答", 2, SUBJECT, 226001),
    (226016, "jeng_g7b_point_want_to_join", "What club do you want to join? 与 want to do sth. 结构", 3, SUBJECT, 226001),
    (226017, "jeng_g7b_point_play_instrument", "play the guitar/piano 与 play basketball 的冠词搭配差异", 4, SUBJECT, 226001),
    (226018, "jeng_g7b_point_club_ad", "俱乐部招聘广告：musicians wanted 的要素与写作格式", 5, SUBJECT, 226001),

    # 时间表达与日常作息
    (226019, "jeng_g7b_point_clock_time", "整点、半点与钟点表达：six thirty、half past six、a quarter to seven", 1, SUBJECT, 226002),
    (226020, "jeng_g7b_point_what_time_when", "What time do you...? 与 When do you...? 的问句与应答", 2, SUBJECT, 226002),
    (226021, "jeng_g7b_point_daily_routine", "日常作息短语：get up、brush teeth、take a shower、go to bed", 3, SUBJECT, 226002),
    (226022, "jeng_g7b_point_frequency_adverbs", "频度副词 always/usually/never 在行为动词前、be 动词后的位置", 4, SUBJECT, 226002),
    (226023, "jeng_g7b_point_third_person_routine", "一般现在时第三人称单数在作息描述中的动词变化", 5, SUBJECT, 226002),
    (226024, "jeng_g7b_point_time_prep_daily", "时间介词 at night、in the morning、on school days 的辨析", 6, SUBJECT, 226002),

    # 交通方式与路程问答
    (226025, "jeng_g7b_point_how_get", "How do you get to school? 与 by bus/on foot 的方式表达", 1, SUBJECT, 226003),
    (226026, "jeng_g7b_point_take_ride_walk", "take the bus、ride a bike、walk to 与 by 短语的转换", 2, SUBJECT, 226003),
    (226027, "jeng_g7b_point_how_long_take", "How long does it take? 与 It takes sb. some time to do 句型", 3, SUBJECT, 226003),
    (226028, "jeng_g7b_point_how_far", "How far is it from...to...? 与 It's... kilometers 的距离问答", 4, SUBJECT, 226003),
    (226029, "jeng_g7b_point_transport_vocab", "交通词汇：subway、train、ship、bike 及出行情景对话", 5, SUBJECT, 226003),

    # 祈使句与规章制度
    (226030, "jeng_g7b_point_imperative_affirmative", "祈使句肯定式以动词原形开头，主语 you 省略", 1, SUBJECT, 226004),
    (226031, "jeng_g7b_point_imperative_negative", "祈使句否定式 Don't + 动词原形 的构成", 2, SUBJECT, 226004),
    (226032, "jeng_g7b_point_must_have_to", "must 与 have to 表示“必须”的语义与形式差异", 3, SUBJECT, 226004),
    (226033, "jeng_g7b_point_cant_prohibition", "can't 表示“禁止、不允许”的规则表达", 4, SUBJECT, 226004),
    (226034, "jeng_g7b_point_rules_writing", "校规家规写作：must、have to、can't 句型的综合运用", 5, SUBJECT, 226004),

    # 动物描述与原因表达
    (226035, "jeng_g7b_point_animal_vocab", "动物词汇与产地：panda、elephant、tiger、koala、lion", 1, SUBJECT, 226005),
    (226036, "jeng_g7b_point_why_because_animal", "Why do you like...? 与 Because they're... 的因果问答", 2, SUBJECT, 226005),
    (226037, "jeng_g7b_point_animal_adjectives", "描述动物的形容词：cute、smart、friendly、shy、lazy", 3, SUBJECT, 226005),
    (226038, "jeng_g7b_point_kind_of", "kind of、very、really 修饰形容词的程度表达", 4, SUBJECT, 226005),
    (226039, "jeng_g7b_point_animal_intro", "动物介绍写作：be from、live in、eat 等信息的组织", 5, SUBJECT, 226005),

    # 现在进行时与电话交际
    (226040, "jeng_g7b_point_pc_form", "现在进行时 be + doing 的构成与动词 -ing 变化规则", 1, SUBJECT, 226006),
    (226041, "jeng_g7b_point_pc_negative_question", "现在进行时的否定句与 Is/Are...doing? 一般疑问句", 2, SUBJECT, 226006),
    (226042, "jeng_g7b_point_what_doing", "What are you doing? 与 I'm watching TV. 的问答", 3, SUBJECT, 226006),
    (226043, "jeng_g7b_point_pc_vs_ps", "现在进行时与一般现在时：此刻正在进行与经常性动作的对比", 4, SUBJECT, 226006),
    (226044, "jeng_g7b_point_phone_english", "电话用语：This is... speaking. / Is that...? / Hold on, please.", 5, SUBJECT, 226006),
    (226045, "jeng_g7b_point_pc_scene", "用现在进行时描述公园、泳池等场景中多人同时进行的活动", 6, SUBJECT, 226006),

    # 天气描述与假期问候
    (226046, "jeng_g7b_point_weather_question", "How's the weather? 与 What's the weather like? 的同义问答", 1, SUBJECT, 226007),
    (226047, "jeng_g7b_point_weather_forms", "It's raining/snowing 与 sunny/windy/cloudy 的表达差异", 2, SUBJECT, 226007),
    (226048, "jeng_g7b_point_how_is_it_going", "How's it going? 问候及 Not bad./Pretty good. 应答", 3, SUBJECT, 226007),
    (226049, "jeng_g7b_point_weather_activity", "天气与活动搭配：rainy day 的室内外活动表达", 4, SUBJECT, 226007),
    (226050, "jeng_g7b_point_postcard", "明信片写作：描述天气、地点与假期活动的时态选择", 5, SUBJECT, 226007),

    # there be 句型与问路指路
    (226051, "jeng_g7b_point_there_be_affirmative", "there be 肯定句与就近原则：There is a.../There are...", 1, SUBJECT, 226008),
    (226052, "jeng_g7b_point_there_be_question", "there be 的否定句与 Is there...?/Are there...? 简答", 2, SUBJECT, 226008),
    (226053, "jeng_g7b_point_place_prepositions", "方位介词 across from、next to、between...and、behind、in front of", 3, SUBJECT, 226008),
    (226054, "jeng_g7b_point_ask_way", "问路句型：Is there a...near here? / Where is the...?", 4, SUBJECT, 226008),
    (226055, "jeng_g7b_point_give_directions", "指路用语：Go along...、turn left/right、It's on your left.", 5, SUBJECT, 226008),
    (226056, "jeng_g7b_point_places_vocab", "场所词汇：post office、bank、hotel、restaurant、supermarket", 6, SUBJECT, 226008),

    # 外貌描述与选择疑问句
    (226057, "jeng_g7b_point_what_look_like", "What does he/she look like? 的外貌问答", 1, SUBJECT, 226009),
    (226058, "jeng_g7b_point_be_vs_have", "be + 形容词（tall/heavy）与 have/has + 名词（curly hair/glasses）的分工", 2, SUBJECT, 226009),
    (226059, "jeng_g7b_point_choice_question", "选择疑问句 Is he tall or short? 的构成与应答", 3, SUBJECT, 226009),
    (226060, "jeng_g7b_point_appearance_order", "身高、体型、发型到衣着的描述顺序与常用词汇", 4, SUBJECT, 226009),
    (226061, "jeng_g7b_point_describe_person", "人物外貌写作：用 is/has 组织连贯的外貌描写", 5, SUBJECT, 226009),

    # 可数与不可数名词与点餐
    (226062, "jeng_g7b_point_would_like", "would like 的用法及 I'd like... 的委婉表达", 1, SUBJECT, 226010),
    (226063, "jeng_g7b_point_count_uncount_food", "点餐中的可数与不可数名词：noodles、beef、mutton、cabbage", 2, SUBJECT, 226010),
    (226064, "jeng_g7b_point_some_any", "some 与 any 在肯定句、否定句和疑问句中的用法区别", 3, SUBJECT, 226010),
    (226065, "jeng_g7b_point_what_would_like", "What would you like? 与 What size bowl would you like? 问答", 4, SUBJECT, 226010),
    (226066, "jeng_g7b_point_ordering_dialogue", "点餐交际：May I take your order? / Here's your bill. 的流程", 5, SUBJECT, 226010),
    (226067, "jeng_g7b_point_special_dish", "特色菜 special 的介绍与价格、配料表达", 6, SUBJECT, 226010),

    # 一般过去时与学校旅行
    (226068, "jeng_g7b_point_past_be", "一般过去时 be 动词 was/were 的人称搭配", 1, SUBJECT, 226011),
    (226069, "jeng_g7b_point_past_regular_ed", "规则动词过去式 -ed 的构成与三种读音", 2, SUBJECT, 226011),
    (226070, "jeng_g7b_point_past_negative_question", "一般过去时的否定句 didn't 与 Did...? 一般疑问句", 3, SUBJECT, 226011),
    (226071, "jeng_g7b_point_school_trip_vocab", "学校旅行活动：visit a museum、go to the zoo、ride a horse", 4, SUBJECT, 226011),
    (226072, "jeng_g7b_point_trip_diary", "旅行日记写作：按时间顺序用一般过去时叙述经历", 5, SUBJECT, 226011),

    # 一般过去时不规则动词与周末活动
    (226073, "jeng_g7b_point_irregular_past", "常见不规则动词过去式：go-went、do-did、have-had、see-saw", 1, SUBJECT, 226012),
    (226074, "jeng_g7b_point_what_did_do", "What did you do last weekend? 的问答与动词还原", 2, SUBJECT, 226012),
    (226075, "jeng_g7b_point_past_time_adverbial", "过去时间状语 last weekend、yesterday、...ago 的搭配", 3, SUBJECT, 226012),
    (226076, "jeng_g7b_point_past_vs_present", "一般过去时与一般现在时在时间标志和动词形式上的对比", 4, SUBJECT, 226012),
    (226077, "jeng_g7b_point_weekend_writing", "周末活动写作：用过去式串联活动与感受", 5, SUBJECT, 226012),

    # 语音、重音与语调
    (226078, "jeng_g7b_point_vowel_sounds", "单元音与双元音在单词中的辨析与拼读", 1, SUBJECT, 226013),
    (226079, "jeng_g7b_point_word_stress", "双音节、多音节单词的重音位置与句子重读", 2, SUBJECT, 226013),
    (226080, "jeng_g7b_point_question_intonation", "一般疑问句升调与特殊疑问句降调的语调规则", 3, SUBJECT, 226013),
    (226081, "jeng_g7b_point_linking_loss", "连读与不完全爆破在口语语流中的听辨与模仿", 4, SUBJECT, 226013),
)

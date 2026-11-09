"""人教版（Go for it!）八年级英语下册：Unit 1—10 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G8 = 8
BOOK_ID = 1328

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级英语下册",
    "jeng_g8b",
    28,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1—10，每单元下挂 Section A／Section B
    (132801, "Unit 1 What's the matter?", "jeng_g8b_u01", 1, BOOK_ID, None),
    (132811, "Section A", "jeng_g8b_u01_a", 1, BOOK_ID, 132801),
    (132812, "Section B", "jeng_g8b_u01_b", 2, BOOK_ID, 132801),
    (132802, "Unit 2 I'll help to clean up the city parks.", "jeng_g8b_u02", 2, BOOK_ID, None),
    (132813, "Section A", "jeng_g8b_u02_a", 1, BOOK_ID, 132802),
    (132814, "Section B", "jeng_g8b_u02_b", 2, BOOK_ID, 132802),
    (132803, "Unit 3 Could you please clean your room?", "jeng_g8b_u03", 3, BOOK_ID, None),
    (132815, "Section A", "jeng_g8b_u03_a", 1, BOOK_ID, 132803),
    (132816, "Section B", "jeng_g8b_u03_b", 2, BOOK_ID, 132803),
    (132804, "Unit 4 Why don't you talk to your parents?", "jeng_g8b_u04", 4, BOOK_ID, None),
    (132817, "Section A", "jeng_g8b_u04_a", 1, BOOK_ID, 132804),
    (132818, "Section B", "jeng_g8b_u04_b", 2, BOOK_ID, 132804),
    (
        132805,
        "Unit 5 What were you doing when the rainstorm came?",
        "jeng_g8b_u05",
        5,
        BOOK_ID,
        None,
    ),
    (132819, "Section A", "jeng_g8b_u05_a", 1, BOOK_ID, 132805),
    (132820, "Section B", "jeng_g8b_u05_b", 2, BOOK_ID, 132805),
    (132806, "Unit 6 An old man tried to move the mountains.", "jeng_g8b_u06", 6, BOOK_ID, None),
    (132821, "Section A", "jeng_g8b_u06_a", 1, BOOK_ID, 132806),
    (132822, "Section B", "jeng_g8b_u06_b", 2, BOOK_ID, 132806),
    (132807, "Unit 7 What's the highest mountain in the world?", "jeng_g8b_u07", 7, BOOK_ID, None),
    (132823, "Section A", "jeng_g8b_u07_a", 1, BOOK_ID, 132807),
    (132824, "Section B", "jeng_g8b_u07_b", 2, BOOK_ID, 132807),
    (132808, "Unit 8 Have you read Treasure Island yet?", "jeng_g8b_u08", 8, BOOK_ID, None),
    (132825, "Section A", "jeng_g8b_u08_a", 1, BOOK_ID, 132808),
    (132826, "Section B", "jeng_g8b_u08_b", 2, BOOK_ID, 132808),
    (132809, "Unit 9 Have you ever been to a museum?", "jeng_g8b_u09", 9, BOOK_ID, None),
    (132827, "Section A", "jeng_g8b_u09_a", 1, BOOK_ID, 132809),
    (132828, "Section B", "jeng_g8b_u09_b", 2, BOOK_ID, 132809),
    (132810, "Unit 10 I've had this bike for three years.", "jeng_g8b_u10", 10, BOOK_ID, None),
    (132829, "Section A", "jeng_g8b_u10_a", 1, BOOK_ID, 132810),
    (132830, "Section B", "jeng_g8b_u10_b", 2, BOOK_ID, 132810),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 228001-228010 为册域层，228011-228060 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (228001, "jeng_g8b_domain_health_advice", "初中八下·身体不适与 should 建议", 1, SUBJECT, G8, None),
    (228002, "jeng_g8b_domain_volunteer_phrases", "初中八下·志愿服务与动词短语", 2, SUBJECT, G8, None),
    (228003, "jeng_g8b_domain_polite_request", "初中八下·委婉请求 Could you please 与家务", 3, SUBJECT, G8, None),
    (228004, "jeng_g8b_domain_advice_clause", "初中八下·提建议与状语从句", 4, SUBJECT, G8, None),
    (228005, "jeng_g8b_domain_past_continuous", "初中八下·过去进行时与突发事件", 5, SUBJECT, G8, None),
    (228006, "jeng_g8b_domain_story_narration", "初中八下·一般过去时与故事叙述", 6, SUBJECT, G8, None),
    (228007, "jeng_g8b_domain_superlative_fact", "初中八下·最高级与地理事实描述", 7, SUBJECT, G8, None),
    (228008, "jeng_g8b_domain_perfect_already_yet", "初中八下·现在完成时 already/yet 与阅读", 8, SUBJECT, G8, None),
    (228009, "jeng_g8b_domain_perfect_been_gone", "初中八下·现在完成时 have been/gone 与经历", 9, SUBJECT, G8, None),
    (228010, "jeng_g8b_domain_perfect_for_since", "初中八下·现在完成时 for/since 与持续动作", 10, SUBJECT, G8, None),

    # Unit 1 身体不适与 should 建议
    (228011, "jeng_g8b_u01_illness_phrases", "have a cold/stomachache/headache/sore throat 身体不适表达", 1, SUBJECT, G8, 228001),
    (228012, "jeng_g8b_u01_whats_matter", "What's the matter?/What's wrong? 询问病情与应答", 2, SUBJECT, G8, 228001),
    (228013, "jeng_g8b_u01_should_advice", "should/shouldn't + 动词原形提建议与 had better 的替代表达", 3, SUBJECT, G8, 228001),
    (228014, "jeng_g8b_u01_reflexive", "反身代词 myself/yourself/himself 与 by oneself 的用法", 4, SUBJECT, G8, 228001),
    (228015, "jeng_g8b_u01_see_doctor", "就医表达 see a doctor/take one's temperature 与 advice 不可数用法", 5, SUBJECT, G8, 228001),

    # Unit 2 志愿服务与动词短语
    (228016, "jeng_g8b_u02_phrasal_object", "clean up/cheer up/give out 等动副短语中代词宾语必须居中", 1, SUBJECT, G8, 228002),
    (228017, "jeng_g8b_u02_phrasal_meaning", "come up with/put off/call up/fix up 的语义辨析", 2, SUBJECT, G8, 228002),
    (228018, "jeng_g8b_u02_infinitive_object", "hope/decide/volunteer/plan + to do 不定式作宾语", 3, SUBJECT, G8, 228002),
    (228019, "jeng_g8b_u02_could_suggest", "could 表建议与 Why don't you 的志愿服务语境运用", 4, SUBJECT, G8, 228002),
    (228020, "jeng_g8b_u02_volunteer_writing", "志愿服务申请写作：I'd like to... 与能力说明", 5, SUBJECT, G8, 228002),

    # Unit 3 委婉请求与家务
    (228021, "jeng_g8b_u03_could_request", "Could you please (not) do...? 礼貌请求、应答与拒绝", 1, SUBJECT, G8, 228003),
    (228022, "jeng_g8b_u03_borrow_lend", "borrow/lend/keep 的语义区别与搭配", 2, SUBJECT, G8, 228003),
    (228023, "jeng_g8b_u03_chores_vocab", "家务词汇 do the dishes/sweep the floor/fold the clothes", 3, SUBJECT, G8, 228003),
    (228024, "jeng_g8b_u03_make_let_have", "make/let/have sb. do 与 help sb. (to) do 的使役结构", 4, SUBJECT, G8, 228003),
    (228025, "jeng_g8b_u03_permission", "Could I...? 请求许可与 Yes, you can./No, you can't. 应答", 5, SUBJECT, G8, 228003),

    # Unit 4 提建议与状语从句
    (228026, "jeng_g8b_u04_why_dont_you", "Why don't you...?/Why not...? 提建议及同义转换", 1, SUBJECT, G8, 228004),
    (228027, "jeng_g8b_u04_until_although", "until/although 引导时间与让步状语从句的连词用法", 2, SUBJECT, G8, 228004),
    (228028, "jeng_g8b_u04_so_that", "so that 引导目的状语从句与从句谓语含 can/could", 3, SUBJECT, G8, 228004),
    (228029, "jeng_g8b_u04_communication", "get on with/argue with/communicate with 沟通话题搭配", 4, SUBJECT, G8, 228004),
    (228030, "jeng_g8b_u04_advice_letter", "建议信写作：问题陈述 + 建议句型 + 祝愿结构", 5, SUBJECT, G8, 228004),

    # Unit 5 过去进行时与突发事件
    (228031, "jeng_g8b_u05_past_cont_form", "过去进行时 was/were + doing 的构成与肯定否定句式", 1, SUBJECT, G8, 228005),
    (228032, "jeng_g8b_u05_when_while", "when 与 while 引导时间状语从句的用法区别", 2, SUBJECT, G8, 228005),
    (228033, "jeng_g8b_u05_cont_vs_past", "过去进行时与一般过去时在同一句中的配合", 3, SUBJECT, G8, 228005),
    (228034, "jeng_g8b_u05_weather_vocab", "rainstorm/thunder/lightning/beat 等天气与灾害词汇", 4, SUBJECT, G8, 228005),
    (228035, "jeng_g8b_u05_event_writing", "用过去进行时叙述突发事件经过的记叙文写作", 5, SUBJECT, G8, 228005),

    # Unit 6 一般过去时与故事叙述
    (228036, "jeng_g8b_u06_past_narration", "一般过去时按时间顺序叙述故事情节的时态连贯", 1, SUBJECT, G8, 228006),
    (228037, "jeng_g8b_u06_unless", "unless 引导条件状语从句及与 if...not 的转换", 2, SUBJECT, G8, 228006),
    (228038, "jeng_g8b_u06_as_soon_as", "as soon as 引导时间状语从句与主将从现原则", 3, SUBJECT, G8, 228006),
    (228039, "jeng_g8b_u06_so_such_that", "so...that 与 such...that 结果状语从句的区分", 4, SUBJECT, G8, 228006),
    (228040, "jeng_g8b_u06_story_retell", "故事复述写作：The Monkey King/Journey to the West 情节概括", 5, SUBJECT, G8, 228006),

    # Unit 7 最高级与地理事实
    (228041, "jeng_g8b_u07_superlative_form", "最高级构成规则与 the + 最高级的基本句式", 1, SUBJECT, G8, 228007),
    (228042, "jeng_g8b_u07_in_of_range", "最高级后 in/of 短语表示比较范围的用法", 2, SUBJECT, G8, 228007),
    (228043, "jeng_g8b_u07_one_of", "one of the + 最高级 + 复数名词的固定搭配", 3, SUBJECT, G8, 228007),
    (228044, "jeng_g8b_u07_transform", "比较级与最高级句式的同义转换", 4, SUBJECT, G8, 228007),
    (228045, "jeng_g8b_u07_geography_fact", "Qomolangma/the Sahara/the Nile 等地理之最的数据表达", 5, SUBJECT, G8, 228007),

    # Unit 8 现在完成时 already/yet 与阅读
    (228046, "jeng_g8b_u08_perfect_form", "现在完成时 have/has + 过去分词的构成与句式", 1, SUBJECT, G8, 228008),
    (228047, "jeng_g8b_u08_already_yet", "already 用于肯定句、yet 用于否定与疑问句的位置", 2, SUBJECT, G8, 228008),
    (228048, "jeng_g8b_u08_ever_never", "ever/never 与 Have you ever...? 的问答", 3, SUBJECT, G8, 228008),
    (228049, "jeng_g8b_u08_past_participle", "规则与不规则动词过去分词的构成与辨析", 4, SUBJECT, G8, 228008),
    (228050, "jeng_g8b_u08_book_recommend", "读后推荐写作：I've just read... 与情节、评价表达", 5, SUBJECT, G8, 228008),

    # Unit 9 现在完成时 have been/gone 与经历
    (228051, "jeng_g8b_u09_been_gone", "have been to 与 have gone to 的语义区别", 1, SUBJECT, G8, 228009),
    (228052, "jeng_g8b_u09_perfect_vs_past", "现在完成时与一般过去时的时间状语区分", 2, SUBJECT, G8, 228009),
    (228053, "jeng_g8b_u09_place_vocab", "museum/amusement park/space museum 等场所话题词汇", 3, SUBJECT, G8, 228009),
    (228054, "jeng_g8b_u09_so_neither", "So have I./Neither have I. 倒装应答与 Me too/Me neither", 4, SUBJECT, G8, 228009),
    (228055, "jeng_g8b_u09_travel_writing", "旅游经历写作：Have you ever been to...? 与经历描述", 5, SUBJECT, G8, 228009),

    # Unit 10 现在完成时 for/since 与持续动作
    (228056, "jeng_g8b_u10_for_since", "for + 时间段与 since + 时间点的用法区别", 1, SUBJECT, G8, 228010),
    (228057, "jeng_g8b_u10_how_long", "How long have you...? 问答与延续性动词的选择", 2, SUBJECT, G8, 228010),
    (228058, "jeng_g8b_u10_non_continuous", "非延续性动词 borrow/buy/die 转 keep/have/be dead", 3, SUBJECT, G8, 228010),
    (228059, "jeng_g8b_u10_have_been_in", "have/has been in 表居住时长与 have been to 的区别", 4, SUBJECT, G8, 228010),
    (228060, "jeng_g8b_u10_old_things", "旧物与童年记忆写作：I've had... for/since... 的叙述", 5, SUBJECT, G8, 228010),
)

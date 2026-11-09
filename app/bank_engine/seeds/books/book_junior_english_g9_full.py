"""人教版（Go for it!）九年级英语全一册：Unit 1—14 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G9 = 9
BOOK_ID = 1329

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版九年级英语全一册",
    "jeng_g9",
    29,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1—14，每单元下挂 Section A／Section B
    (132901, "Unit 1 How can we become good learners?", "jeng_g9_u01", 1, BOOK_ID, None),
    (132915, "Section A", "jeng_g9_u01_a", 1, BOOK_ID, 132901),
    (132916, "Section B", "jeng_g9_u01_b", 2, BOOK_ID, 132901),
    (132902, "Unit 2 I think that mooncakes are delicious!", "jeng_g9_u02", 2, BOOK_ID, None),
    (132917, "Section A", "jeng_g9_u02_a", 1, BOOK_ID, 132902),
    (132918, "Section B", "jeng_g9_u02_b", 2, BOOK_ID, 132902),
    (
        132903,
        "Unit 3 Could you tell me where the restrooms are?",
        "jeng_g9_u03",
        3,
        BOOK_ID,
        None,
    ),
    (132919, "Section A", "jeng_g9_u03_a", 1, BOOK_ID, 132903),
    (132920, "Section B", "jeng_g9_u03_b", 2, BOOK_ID, 132903),
    (132904, "Unit 4 I used to be afraid of the dark.", "jeng_g9_u04", 4, BOOK_ID, None),
    (132921, "Section A", "jeng_g9_u04_a", 1, BOOK_ID, 132904),
    (132922, "Section B", "jeng_g9_u04_b", 2, BOOK_ID, 132904),
    (132905, "Unit 5 What are the shirts made of?", "jeng_g9_u05", 5, BOOK_ID, None),
    (132923, "Section A", "jeng_g9_u05_a", 1, BOOK_ID, 132905),
    (132924, "Section B", "jeng_g9_u05_b", 2, BOOK_ID, 132905),
    (132906, "Unit 6 When was it invented?", "jeng_g9_u06", 6, BOOK_ID, None),
    (132925, "Section A", "jeng_g9_u06_a", 1, BOOK_ID, 132906),
    (132926, "Section B", "jeng_g9_u06_b", 2, BOOK_ID, 132906),
    (
        132907,
        "Unit 7 Teenagers should be allowed to choose their own clothes.",
        "jeng_g9_u07",
        7,
        BOOK_ID,
        None,
    ),
    (132927, "Section A", "jeng_g9_u07_a", 1, BOOK_ID, 132907),
    (132928, "Section B", "jeng_g9_u07_b", 2, BOOK_ID, 132907),
    (132908, "Unit 8 It must belong to Carla.", "jeng_g9_u08", 8, BOOK_ID, None),
    (132929, "Section A", "jeng_g9_u08_a", 1, BOOK_ID, 132908),
    (132930, "Section B", "jeng_g9_u08_b", 2, BOOK_ID, 132908),
    (132909, "Unit 9 I like music that I can dance to.", "jeng_g9_u09", 9, BOOK_ID, None),
    (132931, "Section A", "jeng_g9_u09_a", 1, BOOK_ID, 132909),
    (132932, "Section B", "jeng_g9_u09_b", 2, BOOK_ID, 132909),
    (132910, "Unit 10 You're supposed to shake hands.", "jeng_g9_u10", 10, BOOK_ID, None),
    (132933, "Section A", "jeng_g9_u10_a", 1, BOOK_ID, 132910),
    (132934, "Section B", "jeng_g9_u10_b", 2, BOOK_ID, 132910),
    (132911, "Unit 11 Sad movies make me cry.", "jeng_g9_u11", 11, BOOK_ID, None),
    (132935, "Section A", "jeng_g9_u11_a", 1, BOOK_ID, 132911),
    (132936, "Section B", "jeng_g9_u11_b", 2, BOOK_ID, 132911),
    (132912, "Unit 12 Life is full of the unexpected.", "jeng_g9_u12", 12, BOOK_ID, None),
    (132937, "Section A", "jeng_g9_u12_a", 1, BOOK_ID, 132912),
    (132938, "Section B", "jeng_g9_u12_b", 2, BOOK_ID, 132912),
    (132913, "Unit 13 We're trying to save the earth!", "jeng_g9_u13", 13, BOOK_ID, None),
    (132939, "Section A", "jeng_g9_u13_a", 1, BOOK_ID, 132913),
    (132940, "Section B", "jeng_g9_u13_b", 2, BOOK_ID, 132913),
    (
        132914,
        "Unit 14 I remember meeting all of you in Grade 7.",
        "jeng_g9_u14",
        14,
        BOOK_ID,
        None,
    ),
    (132941, "Section A", "jeng_g9_u14_a", 1, BOOK_ID, 132914),
    (132942, "Section B", "jeng_g9_u14_b", 2, BOOK_ID, 132914),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 229001-229014 为册域层，229015-229084 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (229001, "jeng_g9_domain_learning_by_doing", "初中九全·Unit 1 学习方式与 by doing", 1, SUBJECT, G9, None),
    (229002, "jeng_g9_domain_object_clause", "初中九全·Unit 2 宾语从句与感叹句", 2, SUBJECT, G9, None),
    (229003, "jeng_g9_domain_indirect_question", "初中九全·Unit 3 间接疑问句与礼貌问路", 3, SUBJECT, G9, None),
    (229004, "jeng_g9_domain_used_to", "初中九全·Unit 4 used to 与过去对比", 4, SUBJECT, G9, None),
    (229005, "jeng_g9_domain_passive_present", "初中九全·Unit 5 一般现在时被动语态与材料", 5, SUBJECT, G9, None),
    (229006, "jeng_g9_domain_passive_past", "初中九全·Unit 6 一般过去时被动语态与发明", 6, SUBJECT, G9, None),
    (229007, "jeng_g9_domain_modal_passive", "初中九全·Unit 7 情态动词被动语态与规则", 7, SUBJECT, G9, None),
    (229008, "jeng_g9_domain_speculation", "初中九全·Unit 8 情态动词表推测与归属", 8, SUBJECT, G9, None),
    (229009, "jeng_g9_domain_relative_clause", "初中九全·Unit 9 定语从句 that/who/which", 9, SUBJECT, G9, None),
    (229010, "jeng_g9_domain_supposed_to", "初中九全·Unit 10 be supposed to 与礼仪", 10, SUBJECT, G9, None),
    (229011, "jeng_g9_domain_causative_make", "初中九全·Unit 11 make 使役结构与情绪", 11, SUBJECT, G9, None),
    (229012, "jeng_g9_domain_past_perfect", "初中九全·Unit 12 过去完成时与意外事件", 12, SUBJECT, G9, None),
    (229013, "jeng_g9_domain_environment_review", "初中九全·Unit 13 时态复习与环境保护", 13, SUBJECT, G9, None),
    (229014, "jeng_g9_domain_graduation", "初中九全·Unit 14 毕业回顾与 remember doing", 14, SUBJECT, G9, None),

    # Unit 1 学习方式与 by doing
    (229015, "jeng_g9_u01_by_doing", "by + 动名词表方式：by reading aloud/by working with friends", 1, SUBJECT, G9, 229001),
    (229016, "jeng_g9_u01_advice_patterns", "提建议句型 Why don't you...?/How about...?/You could...", 2, SUBJECT, G9, 229001),
    (229017, "jeng_g9_u01_gerund_subject", "动名词作主语与 It's + adj. + to do 的句式转换", 3, SUBJECT, G9, 229001),
    (229018, "jeng_g9_u01_learning_vocab", "学习策略词汇 be afraid to do/take notes/look up 的搭配", 4, SUBJECT, G9, 229001),
    (229019, "jeng_g9_u01_how_study", "How do you study...? 问答与学习经验短文写作", 5, SUBJECT, G9, 229001),

    # Unit 2 宾语从句与感叹句
    (229020, "jeng_g9_u02_that_clause", "that 引导的宾语从句及 that 在口语中的省略", 1, SUBJECT, G9, 229002),
    (229021, "jeng_g9_u02_if_whether", "if/whether 引导宾语从句及 whether...or not 搭配", 2, SUBJECT, G9, 229002),
    (229022, "jeng_g9_u02_statement_order", "宾语从句用陈述语序：疑问词 + 主语 + 谓语", 3, SUBJECT, G9, 229002),
    (229023, "jeng_g9_u02_tense_agreement", "主句为过去时宾语从句的时态呼应规则", 4, SUBJECT, G9, 229002),
    (229024, "jeng_g9_u02_exclamation", "What/How 引导的感叹句结构与互换", 5, SUBJECT, G9, 229002),

    # Unit 3 间接疑问句与礼貌问路
    (229025, "jeng_g9_u03_where_clause", "Could you tell me where...? 间接疑问句的语序", 1, SUBJECT, G9, 229003),
    (229026, "jeng_g9_u03_polite_request", "Could you please...?/I wonder if... 的礼貌请求", 2, SUBJECT, G9, 229003),
    (229027, "jeng_g9_u03_direct_indirect", "直接引语变间接引语的人称、时态与语序变化", 3, SUBJECT, G9, 229003),
    (229028, "jeng_g9_u03_asking_way", "问路指路词汇 restroom/bookstore/Go along 与方位表达", 4, SUBJECT, G9, 229003),
    (229029, "jeng_g9_u03_politeness_writing", "礼貌程度选择与问路邮件写作", 5, SUBJECT, G9, 229003),

    # Unit 4 used to 与过去对比
    (229030, "jeng_g9_u04_used_to_form", "used to do 的肯定、否定 didn't use to 与疑问句式", 1, SUBJECT, G9, 229004),
    (229031, "jeng_g9_u04_used_to_compare", "used to do/be used to doing/be used to do 三组辨析", 2, SUBJECT, G9, 229004),
    (229032, "jeng_g9_u04_tag_question", "反意疑问句的构成规则与答语一致原则", 3, SUBJECT, G9, 229004),
    (229033, "jeng_g9_u04_appearance", "描述外貌与性格变化的形容词及比较表达", 4, SUBJECT, G9, 229004),
    (229034, "jeng_g9_u04_past_now_writing", "过去与现在对比的记叙文写作：I used to... but now...", 5, SUBJECT, G9, 229004),

    # Unit 5 一般现在时被动语态与材料
    (229035, "jeng_g9_u05_passive_form", "一般现在时被动语态 am/is/are + 过去分词", 1, SUBJECT, G9, 229005),
    (229036, "jeng_g9_u05_made_of_from", "be made of/from/in/by 的语义区别与选用", 2, SUBJECT, G9, 229005),
    (229037, "jeng_g9_u05_passive_question", "被动语态的一般疑问句与特殊疑问句改写", 3, SUBJECT, G9, 229005),
    (229038, "jeng_g9_u05_active_to_passive", "主动句变被动句的步骤与双宾语结构处理", 4, SUBJECT, G9, 229005),
    (229039, "jeng_g9_u05_material_vocab", "材料与产地话题词汇 silk/glass/steel/produce 的运用", 5, SUBJECT, G9, 229005),

    # Unit 6 一般过去时被动语态与发明
    (229040, "jeng_g9_u06_passive_past_form", "一般过去时被动语态 was/were + 过去分词", 1, SUBJECT, G9, 229006),
    (229041, "jeng_g9_u06_when_invented", "When was it invented? 被动语态特殊疑问句", 2, SUBJECT, G9, 229006),
    (229042, "jeng_g9_u06_invent_family", "invent/invention/inventor 词族与词性转换", 3, SUBJECT, G9, 229006),
    (229043, "jeng_g9_u06_by_accident", "by accident/by mistake/be used for 等介词短语", 4, SUBJECT, G9, 229006),
    (229044, "jeng_g9_u06_invention_writing", "发明介绍写作：时间、发明者、用途与影响的被动表达", 5, SUBJECT, G9, 229006),

    # Unit 7 情态动词被动语态与规则
    (229045, "jeng_g9_u07_should_allowed", "should be allowed to do 含情态动词的被动语态", 1, SUBJECT, G9, 229007),
    (229046, "jeng_g9_u07_allow_patterns", "allow sb. to do/allow doing 与被动结构转换", 2, SUBJECT, G9, 229007),
    (229047, "jeng_g9_u07_agree_disagree", "同意与不同意表达 I agree/disagree 及理由陈述", 3, SUBJECT, G9, 229007),
    (229048, "jeng_g9_u07_rules_vocab", "青少年规则话题词汇 license/part-time job/get in the way", 4, SUBJECT, G9, 229007),
    (229049, "jeng_g9_u07_rules_writing", "校规班规议论文写作：观点 + 被动语态论据", 5, SUBJECT, G9, 229007),

    # Unit 8 情态动词表推测与归属
    (229050, "jeng_g9_u08_speculation_degree", "must/might/could/can't 表推测的语气强弱", 1, SUBJECT, G9, 229008),
    (229051, "jeng_g9_u08_belong_to", "belong to sb. 与名词所有格表达物品归属", 2, SUBJECT, G9, 229008),
    (229052, "jeng_g9_u08_negative_speculation", "情态动词推测句的否定形式与反义推测", 3, SUBJECT, G9, 229008),
    (229053, "jeng_g9_u08_mystery_vocab", "神秘事件阅读词汇 noise/creature/policeman/at first", 4, SUBJECT, G9, 229008),
    (229054, "jeng_g9_u08_inference_writing", "推理判断写作：证据陈述 + 情态动词推测链", 5, SUBJECT, G9, 229008),

    # Unit 9 定语从句 that/who/which
    (229055, "jeng_g9_u09_relative_choice", "定语从句中 that/who/which 的选用规则", 1, SUBJECT, G9, 229009),
    (229056, "jeng_g9_u09_subject_verb", "关系代词作主语时从句谓语的单复数一致", 2, SUBJECT, G9, 229009),
    (229057, "jeng_g9_u09_object_omission", "关系代词作宾语时可省略及先行词判断", 3, SUBJECT, G9, 229009),
    (229058, "jeng_g9_u09_whose", "先行词为人/物时 whose 表所属的用法", 4, SUBJECT, G9, 229009),
    (229059, "jeng_g9_u09_preference", "音乐电影话题词汇与 I prefer...that... 偏好表达", 5, SUBJECT, G9, 229009),

    # Unit 10 be supposed to 与礼仪
    (229060, "jeng_g9_u10_supposed_to", "be supposed to do 的用法、否定与疑问形式", 1, SUBJECT, G9, 229010),
    (229061, "jeng_g9_u10_expected_polite", "be expected to do 与 It is polite/impolite to do 句式", 2, SUBJECT, G9, 229010),
    (229062, "jeng_g9_u10_custom_vocab", "礼仪习俗话题词汇 bow/kiss/custom/table manners", 3, SUBJECT, G9, 229010),
    (229063, "jeng_g9_u10_time_place", "时间与地点状语表达 on time/at the table/in public", 4, SUBJECT, G9, 229010),
    (229064, "jeng_g9_u10_manners_writing", "跨文化礼仪建议信写作：be supposed to 句型链", 5, SUBJECT, G9, 229010),

    # Unit 11 make 使役结构与情绪
    (229065, "jeng_g9_u11_make_do_adj", "make sb. do 与 make sb. + adj. 的使役结构", 1, SUBJECT, G9, 229011),
    (229066, "jeng_g9_u11_make_passive", "make 的被动结构 be made to do 及 to 的还原", 2, SUBJECT, G9, 229011),
    (229067, "jeng_g9_u11_would_rather", "would rather do than do 的偏好表达", 3, SUBJECT, G9, 229011),
    (229068, "jeng_g9_u11_sense_verbs", "感官动词 feel/look/sound + 形容词的系表用法", 4, SUBJECT, G9, 229011),
    (229069, "jeng_g9_u11_emotion_vocab", "情绪与电影话题词汇 sad/relaxed/uneasy 的辨析", 5, SUBJECT, G9, 229011),

    # Unit 12 过去完成时与意外事件
    (229070, "jeng_g9_u12_past_perfect_form", "过去完成时 had + 过去分词的构成与句式", 1, SUBJECT, G9, 229012),
    (229071, "jeng_g9_u12_by_the_time", "by the time 引导时间状语从句的时态配合", 2, SUBJECT, G9, 229012),
    (229072, "jeng_g9_u12_sequence", "过去完成时与一般过去时表示动作先后", 3, SUBJECT, G9, 229012),
    (229073, "jeng_g9_u12_unexpected_vocab", "意外事件话题词汇 unexpected/backpack/rush out", 4, SUBJECT, G9, 229012),
    (229074, "jeng_g9_u12_event_writing", "意外事件记叙文写作：过去完成时交代背景", 5, SUBJECT, G9, 229012),

    # Unit 13 时态复习与环境保护
    (229075, "jeng_g9_u13_perfect_review", "现在完成时 have/has + 过去分词的综合复习", 1, SUBJECT, G9, 229013),
    (229076, "jeng_g9_u13_tense_mix", "现在进行时与一般现在时的语境辨析与复习", 2, SUBJECT, G9, 229013),
    (229077, "jeng_g9_u13_passive_modal_review", "被动语态与情态动词的综合复习与改写", 3, SUBJECT, G9, 229013),
    (229078, "jeng_g9_u13_environment_vocab", "环保话题词汇 pollution/litter/recycle/plastic 的搭配", 4, SUBJECT, G9, 229013),
    (229079, "jeng_g9_u13_environment_writing", "环保倡议写作：问题 + 建议 + 呼吁三段式", 5, SUBJECT, G9, 229013),

    # Unit 14 毕业回顾与 remember doing
    (229080, "jeng_g9_u14_remember_doing", "remember doing 与 remember to do 的语义区别", 1, SUBJECT, G9, 229014),
    (229081, "jeng_g9_u14_perfect_review", "现在完成时回顾初中经历与 for/since 表达", 2, SUBJECT, G9, 229014),
    (229082, "jeng_g9_u14_speech_structure", "毕业演讲结构与感恩表达 thank you for doing", 3, SUBJECT, G9, 229014),
    (229083, "jeng_g9_u14_future_plan", "be going to/will 表达未来计划的区别", 4, SUBJECT, G9, 229014),
    (229084, "jeng_g9_u14_graduation_writing", "初中生活回顾写作：remember doing + 情感升华", 5, SUBJECT, G9, 229014),
)

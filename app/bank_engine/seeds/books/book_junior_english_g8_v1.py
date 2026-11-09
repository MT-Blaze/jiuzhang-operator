"""人教版（Go for it!）八年级英语上册：Unit 1—10 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G8 = 8
BOOK_ID = 1327

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级英语上册",
    "jeng_g8a",
    27,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1—10，每单元下挂 Section A／Section B
    (132701, "Unit 1 Where did you go on vacation?", "jeng_g8a_u01", 1, BOOK_ID, None),
    (132711, "Section A", "jeng_g8a_u01_a", 1, BOOK_ID, 132701),
    (132712, "Section B", "jeng_g8a_u01_b", 2, BOOK_ID, 132701),
    (132702, "Unit 2 How often do you exercise?", "jeng_g8a_u02", 2, BOOK_ID, None),
    (132713, "Section A", "jeng_g8a_u02_a", 1, BOOK_ID, 132702),
    (132714, "Section B", "jeng_g8a_u02_b", 2, BOOK_ID, 132702),
    (132703, "Unit 3 I'm more outgoing than my sister.", "jeng_g8a_u03", 3, BOOK_ID, None),
    (132715, "Section A", "jeng_g8a_u03_a", 1, BOOK_ID, 132703),
    (132716, "Section B", "jeng_g8a_u03_b", 2, BOOK_ID, 132703),
    (132704, "Unit 4 What's the best movie theater?", "jeng_g8a_u04", 4, BOOK_ID, None),
    (132717, "Section A", "jeng_g8a_u04_a", 1, BOOK_ID, 132704),
    (132718, "Section B", "jeng_g8a_u04_b", 2, BOOK_ID, 132704),
    (132705, "Unit 5 Do you want to watch a game show?", "jeng_g8a_u05", 5, BOOK_ID, None),
    (132719, "Section A", "jeng_g8a_u05_a", 1, BOOK_ID, 132705),
    (132720, "Section B", "jeng_g8a_u05_b", 2, BOOK_ID, 132705),
    (132706, "Unit 6 I'm going to study computer science.", "jeng_g8a_u06", 6, BOOK_ID, None),
    (132721, "Section A", "jeng_g8a_u06_a", 1, BOOK_ID, 132706),
    (132722, "Section B", "jeng_g8a_u06_b", 2, BOOK_ID, 132706),
    (132707, "Unit 7 Will people have robots?", "jeng_g8a_u07", 7, BOOK_ID, None),
    (132723, "Section A", "jeng_g8a_u07_a", 1, BOOK_ID, 132707),
    (132724, "Section B", "jeng_g8a_u07_b", 2, BOOK_ID, 132707),
    (132708, "Unit 8 How do you make a banana milk shake?", "jeng_g8a_u08", 8, BOOK_ID, None),
    (132725, "Section A", "jeng_g8a_u08_a", 1, BOOK_ID, 132708),
    (132726, "Section B", "jeng_g8a_u08_b", 2, BOOK_ID, 132708),
    (132709, "Unit 9 Can you come to my party?", "jeng_g8a_u09", 9, BOOK_ID, None),
    (132727, "Section A", "jeng_g8a_u09_a", 1, BOOK_ID, 132709),
    (132728, "Section B", "jeng_g8a_u09_b", 2, BOOK_ID, 132709),
    (
        132710,
        "Unit 10 If you go to the party, you'll have a great time!",
        "jeng_g8a_u10",
        10,
        BOOK_ID,
        None,
    ),
    (132729, "Section A", "jeng_g8a_u10_a", 1, BOOK_ID, 132710),
    (132730, "Section B", "jeng_g8a_u10_b", 2, BOOK_ID, 132710),
)

# id / code / name / sort_order / subject_id / parent_id
# 227001-227010 为册域层，227011-227066 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (227001, "jeng_g8a_domain_past_vacation", "初中八上·一般过去时与假期旅行", 1, SUBJECT, None),
    (227002, "jeng_g8a_domain_frequency_health", "初中八上·频率副词与健康习惯", 2, SUBJECT, None),
    (227003, "jeng_g8a_domain_comparative", "初中八上·形容词比较级与人物对比", 3, SUBJECT, None),
    (227004, "jeng_g8a_domain_superlative", "初中八上·形容词最高级与场所评价", 4, SUBJECT, None),
    (227005, "jeng_g8a_domain_infinitive_tv", "初中八上·动词不定式与电视节目", 5, SUBJECT, None),
    (227006, "jeng_g8a_domain_be_going_to", "初中八上·be going to 与未来计划", 6, SUBJECT, None),
    (227007, "jeng_g8a_domain_will_future", "初中八上·will 将来时与数量比较", 7, SUBJECT, None),
    (227008, "jeng_g8a_domain_imperative_recipe", "初中八上·祈使句与步骤描述", 8, SUBJECT, None),
    (227009, "jeng_g8a_domain_invitation_modal", "初中八上·邀请与情态动词", 9, SUBJECT, None),
    (227010, "jeng_g8a_domain_if_clause", "初中八上·if 条件状语从句", 10, SUBJECT, None),

    # 一般过去时与假期旅行
    (227011, "jeng_g8a_u01_past_be", "一般过去时 be 动词 was/were 与主语人称的搭配", 1, SUBJECT, 227001),
    (227012, "jeng_g8a_u01_past_ed", "规则动词过去式 -ed 的拼写变化与读音规则", 2, SUBJECT, 227001),
    (227013, "jeng_g8a_u01_irregular", "常见不规则动词过去式：go-went、buy-bought、feel-felt", 3, SUBJECT, 227001),
    (227014, "jeng_g8a_u01_did_question", "Did you go...? 一般疑问句与 didn't 否定句中的动词还原", 4, SUBJECT, 227001),
    (227015, "jeng_g8a_u01_compound_pronoun", "复合不定代词 someone/anything/nothing 及形容词后置定语", 5, SUBJECT, 227001),
    (227016, "jeng_g8a_u01_trip_writing", "假期旅行写作：Where did you go...? 与过去时连贯叙述", 6, SUBJECT, 227001),

    # 频率副词与健康习惯
    (227017, "jeng_g8a_u02_how_often", "How often...? 与 once/twice/three times a week 的频率应答", 1, SUBJECT, 227002),
    (227018, "jeng_g8a_u02_freq_adverbs", "频度副词 always/usually/often/sometimes/hardly ever/never 的排序与位置", 2, SUBJECT, 227002),
    (227019, "jeng_g8a_u02_third_person", "一般现在时第三人称单数在习惯描述中的动词变化", 3, SUBJECT, 227002),
    (227020, "jeng_g8a_u02_health_vocab", "健康话题词汇：junk food、be good for、although 引导让步", 4, SUBJECT, 227002),
    (227021, "jeng_g8a_u02_habit_writing", "用频度副词描述个人生活习惯的短文写作", 5, SUBJECT, 227002),

    # 形容词比较级与人物对比
    (227022, "jeng_g8a_u03_comparative_form", "比较级构成规则：-er、双写辅音、变 y 为 i、more + 多音节词", 1, SUBJECT, 227003),
    (227023, "jeng_g8a_u03_than_structure", "than 引导的比较结构与比较对象的一致性", 2, SUBJECT, 227003),
    (227024, "jeng_g8a_u03_as_as", "as...as 同级比较与 not as/so...as 的否定比较", 3, SUBJECT, 227003),
    (227025, "jeng_g8a_u03_modifier", "比较级前的修饰语 much、a lot、a little、even", 4, SUBJECT, 227003),
    (227026, "jeng_g8a_u03_irregular", "比较级特殊形式：better、worse、more、less、farther", 5, SUBJECT, 227003),
    (227027, "jeng_g8a_u03_compare_writing", "用比较级描述人物性格与外貌差异的写作", 6, SUBJECT, 227003),

    # 形容词最高级与场所评价
    (227028, "jeng_g8a_u04_superlative_form", "最高级构成规则与 the + 最高级的定冠词使用", 1, SUBJECT, 227004),
    (227029, "jeng_g8a_u04_in_of", "最高级后 in/of 短语表示比较范围的用法", 2, SUBJECT, 227004),
    (227030, "jeng_g8a_u04_one_of", "one of the + 最高级 + 复数名词的固定结构", 3, SUBJECT, 227004),
    (227031, "jeng_g8a_u04_transform", "最高级与比较级句式之间的同义转换", 4, SUBJECT, 227004),
    (227032, "jeng_g8a_u04_best_question", "What's the best...? 与 It's the most... 的问答", 5, SUBJECT, 227004),
    (227033, "jeng_g8a_u04_place_writing", "场所评价写作：the best movie theater/clothes store 的比较说明", 6, SUBJECT, 227004),

    # 动词不定式与电视节目
    (227034, "jeng_g8a_u05_to_do_verbs", "want/hope/plan/decide + to do 的动词不定式搭配", 1, SUBJECT, 227005),
    (227035, "jeng_g8a_u05_to_purpose", "动词不定式作宾语与作目的状语的区分", 2, SUBJECT, 227005),
    (227036, "jeng_g8a_u05_like_doing", "love/like/enjoy + doing 与 + to do 的语义差别", 3, SUBJECT, 227005),
    (227037, "jeng_g8a_u05_think_of", "What do you think of...? 与 love/like/don't mind/can't stand 评价", 4, SUBJECT, 227005),
    (227038, "jeng_g8a_u05_tv_vocab", "电视节目类型词汇：sitcom、talk show、talent show、soap opera", 5, SUBJECT, 227005),
    (227039, "jeng_g8a_u05_review_writing", "节目评论写作：用不定式与评价句型表达观点", 6, SUBJECT, 227005),

    # be going to 与未来计划
    (227040, "jeng_g8a_u06_be_going_to", "be going to + 动词原形表示计划与打算", 1, SUBJECT, 227006),
    (227041, "jeng_g8a_u06_going_to_question", "be going to 的一般疑问句、否定句与简答", 2, SUBJECT, 227006),
    (227042, "jeng_g8a_u06_want_to_be", "want to be + 职业名词表达理想职业", 3, SUBJECT, 227006),
    (227043, "jeng_g8a_u06_resolution", "新年决心的三种表达：be going to、will、plan to", 4, SUBJECT, 227006),
    (227044, "jeng_g8a_u06_plan_writing", "用 be going to 描述周末与假期计划的写作", 5, SUBJECT, 227006),

    # will 将来时与数量比较
    (227045, "jeng_g8a_u07_will_form", "will + 动词原形表示将来预测与客观趋势", 1, SUBJECT, 227007),
    (227046, "jeng_g8a_u07_will_question", "will 的否定式 won't 与 Will...? 一般疑问句及简答", 2, SUBJECT, 227007),
    (227047, "jeng_g8a_u07_there_will_be", "there will be 将来存在句与 there be 的转换", 3, SUBJECT, 227007),
    (227048, "jeng_g8a_u07_more_fewer_less", "more/fewer/less 修饰可数与不可数名词的比较表达", 4, SUBJECT, 227007),
    (227049, "jeng_g8a_u07_future_adverbial", "in the future、in 100 years 等将来时间状语", 5, SUBJECT, 227007),
    (227050, "jeng_g8a_u07_future_writing", "未来生活预测写作：robot、space station 等话题", 6, SUBJECT, 227007),

    # 祈使句与步骤描述
    (227051, "jeng_g8a_u08_imperative_steps", "食谱步骤中的祈使句肯定式与 Don't + 动词原形否定式", 1, SUBJECT, 227008),
    (227052, "jeng_g8a_u08_sequence", "first/next/then/finally 等步骤连接词与操作顺序", 2, SUBJECT, 227008),
    (227053, "jeng_g8a_u08_how_make", "How do you make...? 与 How many/How much 的问答", 3, SUBJECT, 227008),
    (227054, "jeng_g8a_u08_measure", "可数与不可数食物名词及量词 a cup of、two spoons of", 4, SUBJECT, 227008),
    (227055, "jeng_g8a_u08_recipe_writing", "食谱写作：配料清单与制作过程的说明文结构", 5, SUBJECT, 227008),

    # 邀请与情态动词
    (227056, "jeng_g8a_u09_invitation", "Can you come to...? 邀请句型及接受应答", 1, SUBJECT, 227009),
    (227057, "jeng_g8a_u09_have_to", "have to/must 表示义务与必要以及否定形式差异", 2, SUBJECT, 227009),
    (227058, "jeng_g8a_u09_decline", "婉拒句型 I'd love to, but I have to... 与 Sorry, I can't.", 3, SUBJECT, 227009),
    (227059, "jeng_g8a_u09_could_might", "could/might 用于礼貌请求与可能性推测", 4, SUBJECT, 227009),
    (227060, "jeng_g8a_u09_invitation_writing", "邀请函写作：时间、地点、活动的完整信息与回复", 5, SUBJECT, 227009),

    # if 条件状语从句
    (227061, "jeng_g8a_u10_if_main_will", "if 真实条件句的主将从现原则", 1, SUBJECT, 227010),
    (227062, "jeng_g8a_u10_if_question", "if 条件句的否定形式与一般疑问句结构", 2, SUBJECT, 227010),
    (227063, "jeng_g8a_u10_if_position", "if 从句位于句首或句尾时的标点与语序", 3, SUBJECT, 227010),
    (227064, "jeng_g8a_u10_unless", "unless 与 if...not 的同义转换", 4, SUBJECT, 227010),
    (227065, "jeng_g8a_u10_if_modal", "条件句中 should/can 表达建议与能力", 5, SUBJECT, 227010),
    (227066, "jeng_g8a_u10_if_writing", "用 if 条件句写建议与后果的短文", 6, SUBJECT, 227010),
)

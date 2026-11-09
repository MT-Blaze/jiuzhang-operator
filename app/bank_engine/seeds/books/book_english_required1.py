"""人教版（2019）高中英语必修第一册：单元板块目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G10 = 10
BOOK_ID = 1201

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中英语必修第一册",
    "eng_r1",
    1,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (120101, "Welcome Unit", "eng_r1_u00", 1, BOOK_ID, None),
    (120102, "Unit 1 Teenage Life", "eng_r1_u01", 2, BOOK_ID, None),
    (120103, "Unit 2 Travelling Around", "eng_r1_u02", 3, BOOK_ID, None),
    (120104, "Unit 3 Sports and Fitness", "eng_r1_u03", 4, BOOK_ID, None),
    (120105, "Unit 4 Natural Disasters", "eng_r1_u04", 5, BOOK_ID, None),
    (120106, "Unit 5 Languages Around the World", "eng_r1_u05", 6, BOOK_ID, None),
    (120111, "First Impressions／Build Up Your Vocabulary／Reading for Writing", "eng_r1_s01", 1, BOOK_ID, 120101),
    (120112, "Listening and Speaking: School Clubs", "eng_r1_s02", 1, BOOK_ID, 120102),
    (120113, "Reading and Thinking: The Freshman Challenge", "eng_r1_s03", 2, BOOK_ID, 120102),
    (120114, "Discovering Useful Structures: Noun Phrases, Adjective Phrases and Adverb Phrases", "eng_r1_s04", 3, BOOK_ID, 120102),
    (120115, "Reading for Writing: A Letter of Advice", "eng_r1_s05", 4, BOOK_ID, 120102),
    (120116, "Listening and Speaking: Travel Plans", "eng_r1_s06", 1, BOOK_ID, 120103),
    (120117, "Reading and Thinking: Travel Peru", "eng_r1_s07", 2, BOOK_ID, 120103),
    (120118, "Discovering Useful Structures: The Present Continuous Tense for Future Plans", "eng_r1_s08", 3, BOOK_ID, 120103),
    (120119, "Reading for Writing: A Travel Plan", "eng_r1_s09", 4, BOOK_ID, 120103),
    (120120, "Listening and Speaking: Sports Events", "eng_r1_s10", 1, BOOK_ID, 120104),
    (120121, "Reading and Thinking: Living Legends", "eng_r1_s11", 2, BOOK_ID, 120104),
    (120122, "Discovering Useful Structures: Tag Questions", "eng_r1_s12", 3, BOOK_ID, 120104),
    (120123, "Reading for Writing: A Healthful Lifestyle", "eng_r1_s13", 4, BOOK_ID, 120104),
    (120124, "Listening and Speaking: Natural Disasters", "eng_r1_s14", 1, BOOK_ID, 120105),
    (120125, "Reading and Thinking: The Night the Earth Didn't Sleep", "eng_r1_s15", 2, BOOK_ID, 120105),
    (120126, "Discovering Useful Structures: Restrictive Relative Clauses (1)", "eng_r1_s16", 3, BOOK_ID, 120105),
    (120127, "Reading for Writing: A News Report", "eng_r1_s17", 4, BOOK_ID, 120105),
    (120128, "Listening and Speaking: Language Learning", "eng_r1_s18", 1, BOOK_ID, 120106),
    (120129, "Reading and Thinking: The Chinese Writing System", "eng_r1_s19", 2, BOOK_ID, 120106),
    (120130, "Discovering Useful Structures: Restrictive Relative Clauses (2)", "eng_r1_s20", 3, BOOK_ID, 120106),
    (120131, "Reading for Writing: A Blog about Language Learning", "eng_r1_s21", 4, BOOK_ID, 120106),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 161001-161010 为册域能力层，161011-161099 为单元细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (161001, "eng_r1_domain_vocab", "必修一·单元核心词汇与短语", 1, SUBJECT, G10, None),
    (161002, "eng_r1_domain_phrase", "必修一·语法：短语结构与句子成分", 2, SUBJECT, G10, None),
    (161003, "eng_r1_domain_tense", "必修一·语法：时态与语态", 3, SUBJECT, G10, None),
    (161004, "eng_r1_domain_clause", "必修一·语法：定语从句与反意疑问句", 4, SUBJECT, G10, None),
    (161005, "eng_r1_domain_listening", "必修一·听力与语音", 5, SUBJECT, G10, None),
    (161006, "eng_r1_domain_speaking", "必修一·口语与交际功能", 6, SUBJECT, G10, None),
    (161007, "eng_r1_domain_reading", "必修一·阅读策略与语篇分析", 7, SUBJECT, G10, None),
    (161008, "eng_r1_domain_writing", "必修一·写作体裁与过程", 8, SUBJECT, G10, None),
    (161009, "eng_r1_domain_culture", "必修一·文化意识与主题探究", 9, SUBJECT, G10, None),
    (161010, "eng_r1_domain_strategy", "必修一·学习策略与单元任务", 10, SUBJECT, G10, None),

    # 单元核心词汇与短语
    (161011, "eng_r1_point_welcome_greeting", "Welcome Unit 问候与自我介绍的礼貌用语词块", 1, SUBJECT, G10, 161001),
    (161012, "eng_r1_point_welcome_campus", "Welcome Unit 校园场所与课程名词（campus, dormitory, laboratory）", 2, SUBJECT, G10, 161001),
    (161013, "eng_r1_point_welcome_subject", "Welcome Unit 学科与学习用品名词的搭配与复数形式", 3, SUBJECT, G10, 161001),
    (161014, "eng_r1_point_welcome_feeling", "Welcome Unit 描述性格与感受的形容词（curious, confident, anxious）", 4, SUBJECT, G10, 161001),
    (161015, "eng_r1_point_u1_club", "Unit 1 社团与课外活动词块（sign up for, debate club, extra-curricular）", 5, SUBJECT, G10, 161001),
    (161016, "eng_r1_point_u1_growth", "Unit 1 青少年成长与责任词汇（challenge, responsibility, volunteer）", 6, SUBJECT, G10, 161001),
    (161017, "eng_r1_point_u1_advice", "Unit 1 建议与选择词块（recommend, advise, prefer... to..., be suitable for）", 7, SUBJECT, G10, 161001),
    (161018, "eng_r1_point_u1_study", "Unit 1 学业压力与时间管理表达（fall behind, catch up with, manage one's time）", 8, SUBJECT, G10, 161001),
    (161019, "eng_r1_point_u2_transport", "Unit 2 旅行准备与交通词块（book a ticket, check in, flight, pack）", 9, SUBJECT, G10, 161001),
    (161020, "eng_r1_point_u2_scenery", "Unit 2 目的地与景点描述词（ancient, breathtaking, landmark, architecture）", 10, SUBJECT, G10, 161001),
    (161021, "eng_r1_point_u2_itinerary", "Unit 2 行程安排动词短语（set off, take a tour, look forward to）", 11, SUBJECT, G10, 161001),
    (161022, "eng_r1_point_u2_promotion", "Unit 2 旅游宣传文本中形容词与副词的强化表达", 12, SUBJECT, G10, 161001),
    (161023, "eng_r1_point_u3_sport", "Unit 3 运动项目与健身词汇（badminton, marathon, gym, fitness）", 13, SUBJECT, G10, 161001),
    (161024, "eng_r1_point_u3_spirit", "Unit 3 体育精神与赛事词块（champion, compete, break a record）", 14, SUBJECT, G10, 161001),
    (161025, "eng_r1_point_u3_health", "Unit 3 健康生活方式词块（balanced diet, work out, stay in shape）", 15, SUBJECT, G10, 161001),
    (161026, "eng_r1_point_u3_injury", "Unit 3 伤病与恢复表达（injure, recover, suffer from, give up）", 16, SUBJECT, G10, 161001),
    (161027, "eng_r1_point_u4_disaster", "Unit 4 自然灾害名词（earthquake, flood, drought, landslide, tsunami）", 17, SUBJECT, G10, 161001),
    (161028, "eng_r1_point_u4_rescue", "Unit 4 灾害破坏与救援动词（destroy, rescue, evacuate, survive）", 18, SUBJECT, G10, 161001),
    (161029, "eng_r1_point_u4_degree", "Unit 4 程度与数量描述（in ruins, a great number of, completely）", 19, SUBJECT, G10, 161001),
    (161030, "eng_r1_point_u4_rebuild", "Unit 4 灾后重建与互助词块（rebuild, donate, pull together, in need）", 20, SUBJECT, G10, 161001),
    (161031, "eng_r1_point_u5_language", "Unit 5 语言与文字词汇（character, dialect, symbol, translate）", 21, SUBJECT, G10, 161001),
    (161032, "eng_r1_point_u5_learning", "Unit 5 语言学习策略词块（memorize, look up, make sense of）", 22, SUBJECT, G10, 161001),
    (161033, "eng_r1_point_u5_evolve", "Unit 5 语言演变与交流表达（evolve, communicate, connect... with...）", 23, SUBJECT, G10, 161001),
    (161034, "eng_r1_point_u5_calligraphy", "Unit 5 汉字与书法文化词块（calligraphy, brush, stroke, carve）", 24, SUBJECT, G10, 161001),

    # 短语结构与句子成分
    (161035, "eng_r1_point_phrase_noun_form", "Welcome Unit 名词短语的构成：限定词＋形容词＋名词", 1, SUBJECT, G10, 161002),
    (161036, "eng_r1_point_phrase_adj", "Welcome Unit 形容词短语作定语与表语", 2, SUBJECT, G10, 161002),
    (161037, "eng_r1_point_phrase_adv", "Welcome Unit 副词短语修饰动词与形容词", 3, SUBJECT, G10, 161002),
    (161038, "eng_r1_point_phrase_subject", "Unit 1 名词短语作主语与宾语时中心词的识别", 4, SUBJECT, G10, 161002),
    (161039, "eng_r1_point_phrase_agreement", "Unit 1 名词短语作主语时的主谓一致判定", 5, SUBJECT, G10, 161002),
    (161040, "eng_r1_point_phrase_order", "Unit 1 多个形容词并列修饰名词的语序规则", 6, SUBJECT, G10, 161002),
    (161041, "eng_r1_point_phrase_postmodifier", "Unit 2 形容词短语作后置定语与宾语补足语", 7, SUBJECT, G10, 161002),
    (161042, "eng_r1_point_phrase_adv_position", "Unit 2 副词短语在句中的位置与强调效果", 8, SUBJECT, G10, 161002),
    (161043, "eng_r1_point_phrase_expand", "Unit 3 从单词到短语的句法扩展与信息增量", 9, SUBJECT, G10, 161002),
    (161044, "eng_r1_point_phrase_nominal", "Unit 5 短语层面的名词化表达与书面语提升", 10, SUBJECT, G10, 161002),

    # 时态与语态
    (161045, "eng_r1_point_tense_pc_future", "Unit 2 现在进行时表将来计划的结构与时间状语", 1, SUBJECT, G10, 161003),
    (161046, "eng_r1_point_tense_pc_compare", "Unit 2 现在进行时表将来与 will／be going to 的语义差别", 2, SUBJECT, G10, 161003),
    (161047, "eng_r1_point_tense_pc_move", "Unit 2 位移动词（go, come, leave, arrive）进行时表将来", 3, SUBJECT, G10, 161003),
    (161048, "eng_r1_point_tense_present_habit", "Unit 3 一般现在时描述习惯、常态与客观事实", 4, SUBJECT, G10, 161003),
    (161049, "eng_r1_point_tense_past_event", "Unit 4 一般过去时叙述灾害事件的时间线", 5, SUBJECT, G10, 161003),
    (161050, "eng_r1_point_tense_past_continuous", "Unit 4 过去进行时与一般过去时在叙事中的配合", 6, SUBJECT, G10, 161003),
    (161051, "eng_r1_point_tense_present_perfect", "Unit 5 现在完成时描述语言学习经历与持续状态", 7, SUBJECT, G10, 161003),
    (161052, "eng_r1_point_tense_perfect_past", "Unit 5 现在完成时与一般过去时的时间指向辨析", 8, SUBJECT, G10, 161003),

    # 定语从句与反意疑问句
    (161053, "eng_r1_point_clause_basic", "Unit 4 限制性定语从句的概念、先行词与关系词判定", 1, SUBJECT, G10, 161004),
    (161054, "eng_r1_point_clause_that_which", "Unit 4 关系代词 that／which 指物时的选用", 2, SUBJECT, G10, 161004),
    (161055, "eng_r1_point_clause_who", "Unit 4 关系代词 who／whom／whose 指人时的选用", 3, SUBJECT, G10, 161004),
    (161056, "eng_r1_point_clause_omit", "Unit 4 关系代词作宾语时可省略的条件", 4, SUBJECT, G10, 161004),
    (161057, "eng_r1_point_clause_adv", "Unit 4 关系副词 when／where／why 与介词＋which 的转换", 5, SUBJECT, G10, 161004),
    (161058, "eng_r1_point_clause_restrict", "Unit 5 限制性定语从句中 that 与 which 的特殊限制", 6, SUBJECT, G10, 161004),
    (161059, "eng_r1_point_clause_agreement", "Unit 5 定语从句主谓一致：one of＋复数名词结构", 7, SUBJECT, G10, 161004),
    (161060, "eng_r1_point_clause_appositive", "Unit 5 定语从句与同位语从句的句法区分", 8, SUBJECT, G10, 161004),
    (161061, "eng_r1_point_tag_form", "Unit 3 反意疑问句的构成：陈述句＋简短问句", 9, SUBJECT, G10, 161004),
    (161062, "eng_r1_point_tag_answer", "Unit 3 反意疑问句的回答逻辑与语调选择", 10, SUBJECT, G10, 161004),

    # 听力与语音
    (161063, "eng_r1_point_listen_relation", "Welcome Unit 听力中的人物关系与场景推断", 1, SUBJECT, G10, 161005),
    (161064, "eng_r1_point_listen_advice", "Unit 1 听力抓取建议内容与理由的关键词", 2, SUBJECT, G10, 161005),
    (161065, "eng_r1_point_listen_travel", "Unit 2 听力中的时间、价格与航班信息记录", 3, SUBJECT, G10, 161005),
    (161066, "eng_r1_point_listen_number", "Unit 3 听力中的数字、比分与名次速记", 4, SUBJECT, G10, 161005),
    (161067, "eng_r1_point_listen_news", "Unit 4 新闻报道听力的导语识别与事实抓取", 5, SUBJECT, G10, 161005),
    (161068, "eng_r1_point_phonetic_vowel", "本册音标复习：元音长短与重读音节", 6, SUBJECT, G10, 161005),
    (161069, "eng_r1_point_phonetic_link", "连读、失去爆破与弱读的辨音训练", 7, SUBJECT, G10, 161005),
    (161070, "eng_r1_point_phonetic_intonation", "陈述、疑问与列举的升降调辨析", 8, SUBJECT, G10, 161005),

    # 口语与交际功能
    (161071, "eng_r1_point_speak_intro", "Welcome Unit 自我介绍与询问他人信息的交际用语", 1, SUBJECT, G10, 161006),
    (161072, "eng_r1_point_speak_suggest", "Unit 1 提建议与委婉拒绝的功能句型", 2, SUBJECT, G10, 161006),
    (161073, "eng_r1_point_speak_booking", "Unit 2 预订与确认行程的对话策略", 3, SUBJECT, G10, 161006),
    (161074, "eng_r1_point_speak_prefer", "Unit 3 表达喜好与比较运动项目的句型", 4, SUBJECT, G10, 161006),
    (161075, "eng_r1_point_speak_sympathy", "Unit 4 描述经历与表达同情的交际功能", 5, SUBJECT, G10, 161006),
    (161076, "eng_r1_point_speak_clarify", "Unit 5 请求重复与澄清误解的交际策略", 6, SUBJECT, G10, 161006),
    (161077, "eng_r1_point_speak_turn", "本册小组讨论中的话轮转换与观点承接", 7, SUBJECT, G10, 161006),

    # 阅读策略与语篇分析
    (161078, "eng_r1_point_read_skim", "Welcome Unit 略读找主旨与扫读找细节", 1, SUBJECT, G10, 161007),
    (161079, "eng_r1_point_read_growth", "Unit 1 记叙文中人物成长线索的梳理", 2, SUBJECT, G10, 161007),
    (161080, "eng_r1_point_read_brochure", "Unit 2 旅游宣传册的多模态信息整合", 3, SUBJECT, G10, 161007),
    (161081, "eng_r1_point_read_feature", "Unit 3 人物特写中事实与评价的区分", 4, SUBJECT, G10, 161007),
    (161082, "eng_r1_point_read_news", "Unit 4 新闻报道的倒金字塔结构与标题解读", 5, SUBJECT, G10, 161007),
    (161083, "eng_r1_point_read_explain", "Unit 5 说明文中时间顺序与因果关系图", 6, SUBJECT, G10, 161007),
    (161084, "eng_r1_point_read_cohesion", "语篇衔接：指代、替代与逻辑连接词", 7, SUBJECT, G10, 161007),
    (161085, "eng_r1_point_read_guessing", "生词猜测：构词法、上下文与同义复现", 8, SUBJECT, G10, 161007),

    # 写作体裁与过程
    (161086, "eng_r1_point_write_profile", "Welcome Unit 个人简介的写作框架与信息组织", 1, SUBJECT, G10, 161008),
    (161087, "eng_r1_point_write_advice_structure", "Unit 1 建议信的结构：问题—建议—理由—祝愿", 2, SUBJECT, G10, 161008),
    (161088, "eng_r1_point_write_advice_modal", "Unit 1 建议信中的情态动词与委婉表达", 3, SUBJECT, G10, 161008),
    (161089, "eng_r1_point_write_travel_plan", "Unit 2 旅行计划的要素与将来时态选择", 4, SUBJECT, G10, 161008),
    (161090, "eng_r1_point_write_travel_link", "Unit 2 旅行计划中的衔接词与顺序表达", 5, SUBJECT, G10, 161008),
    (161091, "eng_r1_point_write_health", "Unit 3 健康生活方式短文的论点与例证", 6, SUBJECT, G10, 161008),
    (161092, "eng_r1_point_write_news", "Unit 4 新闻报道的标题、导语与事实陈述", 7, SUBJECT, G10, 161008),
    (161093, "eng_r1_point_write_blog", "Unit 5 语言学习博客的反思性写作与人称选择", 8, SUBJECT, G10, 161008),

    # 文化意识与主题探究
    (161094, "eng_r1_point_culture_campus", "中外校园文化与社团活动的比较", 1, SUBJECT, G10, 161009),
    (161095, "eng_r1_point_culture_heritage", "秘鲁等旅游目的地的文化遗产保护意识", 2, SUBJECT, G10, 161009),
    (161096, "eng_r1_point_culture_sport", "中外体育精神与全民健身观念", 3, SUBJECT, G10, 161009),
    (161097, "eng_r1_point_culture_writing", "汉字与中华书写文化的世界意义", 4, SUBJECT, G10, 161009),

    # 学习策略与单元任务
    (161098, "eng_r1_point_strategy_project", "本册单元任务中的项目式学习与小组分工", 1, SUBJECT, G10, 161010),
    (161099, "eng_r1_point_strategy_reflect", "词汇记忆与错题反思的自主学习策略", 2, SUBJECT, G10, 161010),
)

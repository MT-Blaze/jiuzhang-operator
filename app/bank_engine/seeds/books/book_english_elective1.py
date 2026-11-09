"""人教版（2019）高中英语选择性必修第一册：单元板块目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G10 = 10
BOOK_ID = 1204

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中英语选择性必修第一册",
    "eng_x1",
    1,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (120401, "Unit 1 People of Achievement", "eng_x1_u01", 1, BOOK_ID, None),
    (120402, "Unit 2 Looking into the Future", "eng_x1_u02", 2, BOOK_ID, None),
    (120403, "Unit 3 Fascinating Parks", "eng_x1_u03", 3, BOOK_ID, None),
    (120404, "Unit 4 Body Language", "eng_x1_u04", 4, BOOK_ID, None),
    (120405, "Unit 5 Working the Land", "eng_x1_u05", 5, BOOK_ID, None),
    # Unit 1 板块
    (120411, "Listening and Speaking: Great People", "eng_x1_s01", 1, BOOK_ID, 120401),
    (120412, "Reading and Thinking: Tu Youyou Awarded Nobel Prize", "eng_x1_s02", 2, BOOK_ID, 120401),
    (120413, "Discovering Useful Structures: Non-restrictive Relative Clauses", "eng_x1_s03", 3, BOOK_ID, 120401),
    (120414, "Reading for Writing: Introduce Someone You Admire", "eng_x1_s04", 4, BOOK_ID, 120401),
    # Unit 2 板块
    (120415, "Listening and Speaking: Life in the Future", "eng_x1_s05", 1, BOOK_ID, 120402),
    (120416, "Reading and Thinking: Smart Homes to Make Life Easier", "eng_x1_s06", 2, BOOK_ID, 120402),
    (120417, "Discovering Useful Structures: The Future Continuous Tense", "eng_x1_s07", 3, BOOK_ID, 120402),
    (120418, "Reading for Writing: A Letter about the Future", "eng_x1_s08", 4, BOOK_ID, 120402),
    # Unit 3 板块
    (120419, "Listening and Speaking: National Parks", "eng_x1_s09", 1, BOOK_ID, 120403),
    (120420, "Reading and Thinking: Sarek National Park", "eng_x1_s10", 2, BOOK_ID, 120403),
    (120421, "Discovering Useful Structures: The -ing Form as Subject", "eng_x1_s11", 3, BOOK_ID, 120403),
    (120422, "Reading for Writing: A Park Introduction", "eng_x1_s12", 4, BOOK_ID, 120403),
    # Unit 4 板块
    (120423, "Listening and Speaking: Body Language", "eng_x1_s13", 1, BOOK_ID, 120404),
    (120424, "Reading and Thinking: Listening to How Bodies Talk", "eng_x1_s14", 2, BOOK_ID, 120404),
    (120425, "Discovering Useful Structures: The -ing Form as Object", "eng_x1_s15", 3, BOOK_ID, 120404),
    (120426, "Reading for Writing: A Description of Body Language", "eng_x1_s16", 4, BOOK_ID, 120404),
    # Unit 5 板块
    (120427, "Listening and Speaking: Agriculture", "eng_x1_s17", 1, BOOK_ID, 120405),
    (120428, "Reading and Thinking: A Pioneer for All People", "eng_x1_s18", 2, BOOK_ID, 120405),
    (120429, "Discovering Useful Structures: Subject Clauses", "eng_x1_s19", 3, BOOK_ID, 120405),
    (120430, "Reading for Writing: An Introduction to a Person", "eng_x1_s20", 4, BOOK_ID, 120405),
)

# id / code / name / sort_order / subject_id / parent_id
# 164001-164010 为册域能力层，164011-164099 为单元细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (164001, "eng_x1_domain_vocab", "选必一·单元核心词汇与短语", 1, SUBJECT, None),
    (164002, "eng_x1_domain_relclause", "选必一·语法：非限制性定语从句", 2, SUBJECT, None),
    (164003, "eng_x1_domain_future", "选必一·语法：将来进行时", 3, SUBJECT, None),
    (164004, "eng_x1_domain_ing", "选必一·语法：-ing 形式作主语与宾语", 4, SUBJECT, None),
    (164005, "eng_x1_domain_subjclause", "选必一·语法：主语从句", 5, SUBJECT, None),
    (164006, "eng_x1_domain_reading", "选必一·阅读策略与语篇分析", 6, SUBJECT, None),
    (164007, "eng_x1_domain_writing", "选必一·写作体裁与过程", 7, SUBJECT, None),
    (164008, "eng_x1_domain_listening", "选必一·听力与语音策略", 8, SUBJECT, None),
    (164009, "eng_x1_domain_speaking", "选必一·口语与交际功能", 9, SUBJECT, None),
    (164010, "eng_x1_domain_culture", "选必一·文化意识与主题探究", 10, SUBJECT, None),

    # 单元核心词汇与短语
    (164011, "eng_x1_point_u1_achievement", "Unit 1 杰出人物与成就名词（achievement, contribution, breakthrough, reputation）", 1, SUBJECT, 164001),
    (164012, "eng_x1_point_u1_research", "Unit 1 科研与探索动词（discover, develop, conduct, obtain）", 2, SUBJECT, 164001),
    (164013, "eng_x1_point_u1_medicine", "Unit 1 医学与奖项词块（cure, medicine, Nobel Prize, be awarded）", 3, SUBJECT, 164001),
    (164014, "eng_x1_point_u1_quality", "Unit 1 品质与精神形容词（determined, committed, modest, optimistic）", 4, SUBJECT, 164001),
    (164015, "eng_x1_point_u1_phrase", "Unit 1 成就表达短语（make a difference, devote oneself to, in recognition of, be known for）", 5, SUBJECT, 164001),
    (164016, "eng_x1_point_u2_tech", "Unit 2 科技与未来名词（technology, innovation, device, automation）", 6, SUBJECT, 164001),
    (164017, "eng_x1_point_u2_predict", "Unit 2 预测与趋势动词（predict, forecast, transform, replace）", 7, SUBJECT, 164001),
    (164018, "eng_x1_point_u2_smarthome", "Unit 2 智能生活词块（smart home, artificial intelligence, remote control, energy-efficient）", 8, SUBJECT, 164001),
    (164019, "eng_x1_point_u2_risk", "Unit 2 利弊与风险表达（benefit, drawback, risk, side effect）", 9, SUBJECT, 164001),
    (164020, "eng_x1_point_u2_outlook", "Unit 2 未来展望短语（in the near future, be likely to, keep pace with, make full use of）", 10, SUBJECT, 164001),
    (164021, "eng_x1_point_u3_park", "Unit 3 国家公园与自然名词（national park, landscape, wilderness, wildlife）", 11, SUBJECT, 164001),
    (164022, "eng_x1_point_u3_landform", "Unit 3 地貌与生态词汇（glacier, valley, vegetation, ecosystem）", 12, SUBJECT, 164001),
    (164023, "eng_x1_point_u3_outdoor", "Unit 3 户外活动动词（hike, camp, explore, preserve）", 13, SUBJECT, 164001),
    (164024, "eng_x1_point_u3_scenery", "Unit 3 景观描写形容词（breathtaking, remote, untouched, spectacular）", 14, SUBJECT, 164001),
    (164025, "eng_x1_point_u3_protect", "Unit 3 保护与游览短语（be home to, protect... from..., in harmony with, set aside）", 15, SUBJECT, 164001),
    (164026, "eng_x1_point_u4_gesture", "Unit 4 身势语名词（gesture, posture, facial expression, eye contact）", 16, SUBJECT, 164001),
    (164027, "eng_x1_point_u4_action", "Unit 4 动作与姿态动词（nod, shrug, frown, lean）", 17, SUBJECT, 164001),
    (164028, "eng_x1_point_u4_emotion", "Unit 4 情绪与态度词（friendly, nervous, confident, respectful）", 18, SUBJECT, 164001),
    (164029, "eng_x1_point_u4_communication", "Unit 4 跨文化交际词块（body language, cultural difference, first impression, misread）", 19, SUBJECT, 164001),
    (164030, "eng_x1_point_u4_response", "Unit 4 解释与致意短语（in response to, be aware of, differ from, come across）", 20, SUBJECT, 164001),
    (164031, "eng_x1_point_u5_agriculture", "Unit 5 农业与作物名词（agriculture, crop, harvest, yield）", 21, SUBJECT, 164001),
    (164032, "eng_x1_point_u5_cultivate", "Unit 5 耕作与培育动词（cultivate, plant, irrigate, fertilize）", 22, SUBJECT, 164001),
    (164033, "eng_x1_point_u5_food", "Unit 5 粮食安全词块（food security, hybrid rice, output, shortage）", 23, SUBJECT, 164001),
    (164034, "eng_x1_point_u5_land", "Unit 5 乡村与土地形容词（rural, fertile, sustainable, productive）", 24, SUBJECT, 164001),
    (164035, "eng_x1_point_u5_devotion", "Unit 5 奉献与影响短语（devote one's life to, feed the world, pass on, dream of）", 25, SUBJECT, 164001),

    # 非限制性定语从句
    (164036, "eng_x1_point_rel_which_who", "Unit 1 非限制性定语从句中 which/who/whose 的指代与逗号使用", 1, SUBJECT, 164002),
    (164037, "eng_x1_point_rel_sentence", "Unit 1 非限制性定语从句中 which 指代整个主句的用法", 2, SUBJECT, 164002),
    (164038, "eng_x1_point_rel_restrictive", "Unit 1 限制性与非限制性定语从句的语义差异及逗号判定", 3, SUBJECT, 164002),
    (164039, "eng_x1_point_rel_that", "Unit 1 非限制性定语从句中 that 不可使用的规则", 4, SUBJECT, 164002),
    (164040, "eng_x1_point_rel_prep", "Unit 1 非限制性定语从句中“介词+which/whom”结构", 5, SUBJECT, 164002),
    (164041, "eng_x1_point_rel_as", "Unit 1 as 引导的非限制性定语从句（as is known to all）", 6, SUBJECT, 164002),
    (164042, "eng_x1_point_rel_adv", "Unit 1 非限制性定语从句中关系副词 when/where 的选用", 7, SUBJECT, 164002),
    (164043, "eng_x1_point_rel_appositive", "Unit 1 非限制性定语从句与同位语从句的辨析", 8, SUBJECT, 164002),
    (164044, "eng_x1_point_rel_person", "Unit 1 非限制性定语从句在人物介绍中的补充说明功能", 9, SUBJECT, 164002),

    # 将来进行时
    (164045, "eng_x1_point_fut_form", "Unit 2 将来进行时的构成 will be doing 及否定、疑问形式", 1, SUBJECT, 164003),
    (164046, "eng_x1_point_fut_time", "Unit 2 将来进行时表示将来某时刻正在进行的动作", 2, SUBJECT, 164003),
    (164047, "eng_x1_point_fut_vs_will", "Unit 2 将来进行时与一般将来时的语义分工", 3, SUBJECT, 164003),
    (164048, "eng_x1_point_fut_arrangement", "Unit 2 将来进行时表示已安排好的将来事件", 4, SUBJECT, 164003),
    (164049, "eng_x1_point_fut_polite", "Unit 2 将来进行时用于礼貌询问与委婉推测", 5, SUBJECT, 164003),
    (164050, "eng_x1_point_fut_vs_present", "Unit 2 将来进行时与现在进行时表将来的区别", 6, SUBJECT, 164003),
    (164051, "eng_x1_point_fut_adverbial", "Unit 2 将来进行时的典型时间状语（at this time tomorrow）", 7, SUBJECT, 164003),
    (164052, "eng_x1_point_fut_discourse", "Unit 2 将来进行时在科技预测语篇中的表达功能", 8, SUBJECT, 164003),

    # -ing 形式作主语与宾语
    (164053, "eng_x1_point_ing_subject", "Unit 3 -ing 形式作主语：动名词与不定式的语义差异", 1, SUBJECT, 164004),
    (164054, "eng_x1_point_ing_agreement", "Unit 3 -ing 形式作主语时谓语动词的单复数一致", 2, SUBJECT, 164004),
    (164055, "eng_x1_point_ing_it", "Unit 3 it 作形式主语、-ing 短语后置的句型转换", 3, SUBJECT, 164004),
    (164056, "eng_x1_point_ing_complex", "Unit 3 动名词的复合结构作主语（his coming late）", 4, SUBJECT, 164004),
    (164057, "eng_x1_point_ing_object", "Unit 3 只接动名词作宾语的常见动词（enjoy, avoid, suggest）", 5, SUBJECT, 164004),
    (164058, "eng_x1_point_ing_prep", "Unit 3 -ing 形式作介词宾语与固定搭配（be used to doing）", 6, SUBJECT, 164004),
    (164059, "eng_x1_point_ing_vs_inf", "Unit 3 动名词与不定式作宾语的语义差别（remember/forget/stop）", 7, SUBJECT, 164004),
    (164060, "eng_x1_point_ing_tense", "Unit 3 动名词的完成式与被动式（having done/being done）", 8, SUBJECT, 164004),
    (164061, "eng_x1_point_ing_body", "Unit 4 -ing 形式作宾语在身势语描写中的表意功能", 9, SUBJECT, 164004),

    # 主语从句
    (164062, "eng_x1_point_subj_that", "Unit 5 主语从句引导词 that/whether 的选用与 that 不可省略", 1, SUBJECT, 164005),
    (164063, "eng_x1_point_subj_it", "Unit 5 it 作形式主语的主语从句常见句型", 2, SUBJECT, 164005),
    (164064, "eng_x1_point_subj_pron", "Unit 5 连接代词 what/who/which 引导的主语从句", 3, SUBJECT, 164005),
    (164065, "eng_x1_point_subj_adv", "Unit 5 连接副词 when/where/why/how 引导的主语从句", 4, SUBJECT, 164005),
    (164066, "eng_x1_point_subj_agreement", "Unit 5 主语从句的主谓一致与谓语单复数判断", 5, SUBJECT, 164005),
    (164067, "eng_x1_point_subj_compare", "Unit 5 主语从句与强调句、定语从句的辨析", 6, SUBJECT, 164005),
    (164068, "eng_x1_point_subj_ever", "Unit 5 whatever/whoever 引导的主语从句", 7, SUBJECT, 164005),
    (164069, "eng_x1_point_subj_argument", "Unit 5 主语从句在农业议题议论文中表达观点的功能", 8, SUBJECT, 164005),

    # 阅读策略与语篇分析
    (164070, "eng_x1_point_read_timeline", "Unit 1 人物传记语篇的成就线索与时间线梳理", 1, SUBJECT, 164006),
    (164071, "eng_x1_point_read_quality", "Unit 1 阅读中提取人物品质评价的文本证据", 2, SUBJECT, 164006),
    (164072, "eng_x1_point_read_tech", "Unit 2 科技说明文“现状—预测—评价”的语篇结构", 3, SUBJECT, 164006),
    (164073, "eng_x1_point_read_fact", "Unit 2 阅读中区分事实陈述与作者预测", 4, SUBJECT, 164006),
    (164074, "eng_x1_point_read_space_order", "Unit 3 国家公园介绍语篇的空间描写顺序", 5, SUBJECT, 164006),
    (164075, "eng_x1_point_read_scenery", "Unit 3 景物描写的感官词汇与修辞识别", 6, SUBJECT, 164006),
    (164076, "eng_x1_point_read_define", "Unit 4 身势语说明文“定义—举例—比较”的解读路径", 7, SUBJECT, 164006),
    (164077, "eng_x1_point_read_misunderstand", "Unit 4 跨文化误解案例的因果分析", 8, SUBJECT, 164006),
    (164078, "eng_x1_point_read_data", "Unit 5 人物特写中数据与引语的论证作用", 9, SUBJECT, 164006),
    (164079, "eng_x1_point_read_causation", "Unit 5 农业议题语篇的因果链与解决方案梳理", 10, SUBJECT, 164006),

    # 写作体裁与过程
    (164080, "eng_x1_point_write_person", "Unit 1 人物介绍写作：身份、成就与品质的三段式组织", 1, SUBJECT, 164007),
    (164081, "eng_x1_point_write_relative", "Unit 1 人物介绍中非限制性定语从句的增补信息用法", 2, SUBJECT, 164007),
    (164082, "eng_x1_point_write_future", "Unit 2 未来生活书信：预测内容与礼貌语气的平衡", 3, SUBJECT, 164007),
    (164083, "eng_x1_point_write_format", "Unit 2 英文书信格式：称呼、正文分层与落款规范", 4, SUBJECT, 164007),
    (164084, "eng_x1_point_write_park", "Unit 3 公园介绍：位置、景观与活动信息的说明顺序", 5, SUBJECT, 164007),
    (164085, "eng_x1_point_write_detail", "Unit 3 公园介绍中形容词与感官细节的选用", 6, SUBJECT, 164007),
    (164086, "eng_x1_point_write_body", "Unit 4 身势语描写：动作分解与情绪对应", 7, SUBJECT, 164007),
    (164087, "eng_x1_point_write_stereotype", "Unit 4 身势语描写中避免文化刻板印象的表达策略", 8, SUBJECT, 164007),
    (164088, "eng_x1_point_write_profile", "Unit 5 人物简介写作：贡献、影响与评价的层次安排", 9, SUBJECT, 164007),

    # 听力与语音策略
    (164089, "eng_x1_point_listen_interview", "Unit 1 人物成就访谈的关键信息与数字速记", 1, SUBJECT, 164008),
    (164090, "eng_x1_point_listen_stance", "Unit 2 科技预测类听力的立场与态度推断", 2, SUBJECT, 164008),
    (164091, "eng_x1_point_listen_route", "Unit 3 地貌与路线描述听力的空间定位", 3, SUBJECT, 164008),
    (164092, "eng_x1_point_listen_body", "Unit 4 身势语话题听力的语境与语气辨识", 4, SUBJECT, 164008),
    (164093, "eng_x1_point_phonetic_focus", "本册语音：句子重音、语调与语义焦点的辨听", 5, SUBJECT, 164008),

    # 口语与交际功能
    (164094, "eng_x1_point_speak_clarify", "Unit 4 解释与澄清身势语含义的功能句型", 1, SUBJECT, 164009),
    (164095, "eng_x1_point_speak_agri", "Unit 5 谈论农业与粮食安全的观点表达与追问", 2, SUBJECT, 164009),
    (164096, "eng_x1_point_speak_admire", "Unit 1 介绍敬佩之人的评价性形容词与例证句型", 3, SUBJECT, 164009),

    # 文化意识与主题探究
    (164097, "eng_x1_point_culture_scientist", "Unit 1 中外科学家精神与诺贝尔奖的文化解读", 1, SUBJECT, 164010),
    (164098, "eng_x1_point_culture_park", "Unit 3 国家公园理念与生态文明的中西对话", 2, SUBJECT, 164010),
    (164099, "eng_x1_point_culture_farming", "Unit 5 从传统农耕到现代农业的文化传承", 3, SUBJECT, 164010),
)

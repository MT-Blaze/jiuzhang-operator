"""人教版（2019）高中英语必修第二册：单元板块目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G10 = 10
BOOK_ID = 1202

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中英语必修第二册",
    "eng_r2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (120201, "Unit 1 Cultural Heritage", "eng_r2_u01", 1, BOOK_ID, None),
    (120202, "Unit 2 Wildlife Protection", "eng_r2_u02", 2, BOOK_ID, None),
    (120203, "Unit 3 The Internet", "eng_r2_u03", 3, BOOK_ID, None),
    (120204, "Unit 4 History and Traditions", "eng_r2_u04", 4, BOOK_ID, None),
    (120205, "Unit 5 Music", "eng_r2_u05", 5, BOOK_ID, None),
    (120211, "Listening and Speaking: Take Part in a Youth Project", "eng_r2_s01", 1, BOOK_ID, 120201),
    (120212, "Reading and Thinking: From Problems to Solutions", "eng_r2_s02", 2, BOOK_ID, 120201),
    (120213, "Discovering Useful Structures: Restrictive Relative Clauses (3)", "eng_r2_s03", 3, BOOK_ID, 120201),
    (120214, "Reading for Writing: A News Report", "eng_r2_s04", 4, BOOK_ID, 120201),
    (120215, "Listening and Speaking: Wildlife Protection", "eng_r2_s05", 1, BOOK_ID, 120202),
    (120216, "Reading and Thinking: A Day in the Clouds", "eng_r2_s06", 2, BOOK_ID, 120202),
    (120217, "Discovering Useful Structures: The Present Continuous Passive", "eng_r2_s07", 3, BOOK_ID, 120202),
    (120218, "Reading for Writing: A Letter of Complaint", "eng_r2_s08", 4, BOOK_ID, 120202),
    (120219, "Listening and Speaking: The Internet", "eng_r2_s09", 1, BOOK_ID, 120203),
    (120220, "Reading and Thinking: Stronger Together", "eng_r2_s10", 2, BOOK_ID, 120203),
    (120221, "Discovering Useful Structures: The Present Perfect Passive", "eng_r2_s11", 3, BOOK_ID, 120203),
    (120222, "Reading for Writing: A Blog Post", "eng_r2_s12", 4, BOOK_ID, 120203),
    (120223, "Listening and Speaking: History and Traditions", "eng_r2_s13", 1, BOOK_ID, 120204),
    (120224, "Reading and Thinking: What's in a Name?", "eng_r2_s14", 2, BOOK_ID, 120204),
    (120225, "Discovering Useful Structures: Past Participles as Attributive and Object Complement", "eng_r2_s15", 3, BOOK_ID, 120204),
    (120226, "Reading for Writing: A Description of a Historic Place", "eng_r2_s16", 4, BOOK_ID, 120204),
    (120227, "Listening and Speaking: Music", "eng_r2_s17", 1, BOOK_ID, 120205),
    (120228, "Reading and Thinking: The Virtual Choir", "eng_r2_s18", 2, BOOK_ID, 120205),
    (120229, "Discovering Useful Structures: Past Participles as Adverbial and Predicative", "eng_r2_s19", 3, BOOK_ID, 120205),
    (120230, "Reading for Writing: A Speech about Music", "eng_r2_s20", 4, BOOK_ID, 120205),
)

# id / code / name / sort_order / subject_id / parent_id
# 162001-162010 为册域能力层，162011-162099 为单元细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (162001, "eng_r2_domain_vocab", "必修二·单元核心词汇与短语", 1, SUBJECT, None),
    (162002, "eng_r2_domain_clause", "必修二·语法：关系副词与非限制性定语从句", 2, SUBJECT, None),
    (162003, "eng_r2_domain_passive", "必修二·语法：进行时与完成时被动语态", 3, SUBJECT, None),
    (162004, "eng_r2_domain_participle", "必修二·语法：过去分词与分词短语", 4, SUBJECT, None),
    (162005, "eng_r2_domain_listening", "必修二·听力与语音", 5, SUBJECT, None),
    (162006, "eng_r2_domain_speaking", "必修二·口语与交际功能", 6, SUBJECT, None),
    (162007, "eng_r2_domain_reading", "必修二·阅读策略与语篇分析", 7, SUBJECT, None),
    (162008, "eng_r2_domain_writing", "必修二·写作体裁与过程", 8, SUBJECT, None),
    (162009, "eng_r2_domain_culture", "必修二·文化意识与主题探究", 9, SUBJECT, None),
    (162010, "eng_r2_domain_strategy", "必修二·学习策略与单元任务", 10, SUBJECT, None),

    # 单元核心词汇与短语
    (162011, "eng_r2_point_u1_heritage", "Unit 1 文化遗产名词与动词（heritage, relic, preserve, restore）", 1, SUBJECT, 162001),
    (162012, "eng_r2_point_u1_protect", "Unit 1 遗产保护措施词块（protect... from..., take measures, rebuild）", 2, SUBJECT, 162001),
    (162013, "eng_r2_point_u1_fund", "Unit 1 项目与资金表达（project, fund, donate, raise money）", 3, SUBJECT, 162001),
    (162014, "eng_r2_point_u1_damage", "Unit 1 损毁与濒危描述（in ruins, be at risk, give way to）", 4, SUBJECT, 162001),
    (162015, "eng_r2_point_u1_cooperate", "Unit 1 合作与意识词块（cooperate, awareness, take part in, in return）", 5, SUBJECT, 162001),
    (162016, "eng_r2_point_u2_wildlife", "Unit 2 野生动物与栖息地名词（wildlife, species, habitat, ecosystem）", 6, SUBJECT, 162001),
    (162017, "eng_r2_point_u2_endangered", "Unit 2 濒危与威胁表达（endangered, extinct, threaten, illegal hunting）", 7, SUBJECT, 162001),
    (162018, "eng_r2_point_u2_reserve", "Unit 2 保护措施词块（reserve, ban, protect... from..., take measures）", 8, SUBJECT, 162001),
    (162019, "eng_r2_point_u2_population", "Unit 2 种群数量与趋势表达（population, decline, survive, recover）", 9, SUBJECT, 162001),
    (162020, "eng_r2_point_u2_harmony", "Unit 2 和谐共处词块（in harmony with, make a difference, be aware of）", 10, SUBJECT, 162001),
    (162021, "eng_r2_point_u3_internet", "Unit 3 互联网与网络工具名词（website, browser, search engine, app）", 11, SUBJECT, 162001),
    (162022, "eng_r2_point_u3_divide", "Unit 3 数字鸿沟与网络接入表达（digital divide, access, connect, convenient）", 12, SUBJECT, 162001),
    (162023, "eng_r2_point_u3_social", "Unit 3 网络社交动词与名词（post, comment, share, online community）", 13, SUBJECT, 162001),
    (162024, "eng_r2_point_u3_safety", "Unit 3 网络安全词块（privacy, password, cyberbully, personal information）", 14, SUBJECT, 162001),
    (162025, "eng_r2_point_u3_impact", "Unit 3 技术影响表达（benefit, rely on, keep in touch, change one's life）", 15, SUBJECT, 162001),
    (162026, "eng_r2_point_u4_history", "Unit 4 历史与传统名词（history, tradition, ancient, dynasty）", 16, SUBJECT, 162001),
    (162027, "eng_r2_point_u4_origin", "Unit 4 地名由来表达（origin, meaning, refer to, be made up of）", 17, SUBJECT, 162001),
    (162028, "eng_r2_point_u4_union", "Unit 4 联合与统治词块（unite, union, kingdom, conquer, rule）", 18, SUBJECT, 162001),
    (162029, "eng_r2_point_u4_site", "Unit 4 历史遗址名词（castle, cathedral, monument, ruins）", 19, SUBJECT, 162001),
    (162030, "eng_r2_point_u4_legacy", "Unit 4 历史影响与认同表达（influence, legacy, identity, date back to）", 20, SUBJECT, 162001),
    (162031, "eng_r2_point_u5_genre", "Unit 5 音乐类型名词（classical, folk, jazz, hip-hop, rock）", 21, SUBJECT, 162001),
    (162032, "eng_r2_point_u5_perform", "Unit 5 乐器与演出词块（instrument, piano, violin, perform, concert）", 22, SUBJECT, 162001),
    (162033, "eng_r2_point_u5_musician", "Unit 5 音乐职业名词（musician, composer, conductor, choir）", 23, SUBJECT, 162001),
    (162034, "eng_r2_point_u5_emotion", "Unit 5 音乐感受与作用动词（move, inspire, relax, express）", 24, SUBJECT, 162001),
    (162035, "eng_r2_point_u5_virtual", "Unit 5 虚拟合唱相关词块（virtual choir, record, upload, mix）", 25, SUBJECT, 162001),

    # 关系副词与非限制性定语从句
    (162036, "eng_r2_point_clause_where", "Unit 1 关系副词 where 与“介词+which”的转换", 1, SUBJECT, 162002),
    (162037, "eng_r2_point_clause_when", "Unit 1 关系副词 when 与“介词+which”的转换", 2, SUBJECT, 162002),
    (162038, "eng_r2_point_clause_why", "Unit 1 关系副词 why 与 for which 的使用条件", 3, SUBJECT, 162002),
    (162039, "eng_r2_point_clause_choose", "Unit 1 关系副词与关系代词的选择：从句缺状语还是缺主宾", 4, SUBJECT, 162002),
    (162040, "eng_r2_point_clause_non_define", "Unit 1 非限制性定语从句的逗号、先行词与 that 禁用", 5, SUBJECT, 162002),
    (162041, "eng_r2_point_clause_non_which", "Unit 1 非限制性定语从句中 which／who 的指代与补充说明", 6, SUBJECT, 162002),
    (162042, "eng_r2_point_clause_prep", "Unit 1 “介词+关系代词”结构中关系词的选用与语序", 7, SUBJECT, 162002),

    # 进行时与完成时被动语态
    (162043, "eng_r2_point_passive_pc_form", "Unit 2 现在进行时被动语态 am/is/are being done 的构成", 1, SUBJECT, 162003),
    (162044, "eng_r2_point_passive_pc_use", "Unit 2 现在进行时被动的使用场景：正在被进行的动作", 2, SUBJECT, 162003),
    (162045, "eng_r2_point_passive_pc_compare", "Unit 2 现在进行时被动与一般现在时被动的对比", 3, SUBJECT, 162003),
    (162046, "eng_r2_point_passive_by", "Unit 2 被动语态中 by 短语的省略与保留", 4, SUBJECT, 162003),
    (162047, "eng_r2_point_passive_pp_form", "Unit 3 现在完成时被动语态 have/has been done 的构成与使用", 5, SUBJECT, 162003),
    (162048, "eng_r2_point_passive_pp_compare", "Unit 3 现在完成时被动与现在完成进行时的语义辨析", 6, SUBJECT, 162003),
    (162049, "eng_r2_point_passive_past", "Unit 3 现在完成时被动与一般过去时被动的辨析", 7, SUBJECT, 162003),

    # 过去分词与分词短语
    (162050, "eng_r2_point_part_attr_pos", "Unit 4 过去分词作定语：前置与后置的位置及被动含义", 1, SUBJECT, 162004),
    (162051, "eng_r2_point_part_attr_clause", "Unit 4 过去分词短语作定语与定语从句的转换", 2, SUBJECT, 162004),
    (162052, "eng_r2_point_part_oc_have", "Unit 4 过去分词作宾语补足语：have／get sth done 结构", 3, SUBJECT, 162004),
    (162053, "eng_r2_point_part_oc_compare", "Unit 4 过去分词作宾补与现在分词作宾补的辨析", 4, SUBJECT, 162004),
    (162054, "eng_r2_point_part_oc_sense", "Unit 4 感官动词后接过去分词作宾补的用法", 5, SUBJECT, 162004),
    (162055, "eng_r2_point_part_adv", "Unit 5 过去分词作状语：时间、原因、条件与让步", 6, SUBJECT, 162004),
    (162056, "eng_r2_point_part_pred", "Unit 5 过去分词作表语与被动语态的结构区分", 7, SUBJECT, 162004),
    (162057, "eng_r2_point_part_adv_subject", "Unit 5 过去分词作状语与现在分词作状语的逻辑主语判定", 8, SUBJECT, 162004),

    # 听力与语音
    (162058, "eng_r2_point_listen_heritage", "Unit 1 听力中文化遗产项目信息的抓取（时间、地点、措施）", 1, SUBJECT, 162005),
    (162059, "eng_r2_point_listen_number", "Unit 1 听力中年代、数字与专有名词的速记", 2, SUBJECT, 162005),
    (162060, "eng_r2_point_listen_wildlife", "Unit 2 听力中动物保护话题的关键词与观点判断", 3, SUBJECT, 162005),
    (162061, "eng_r2_point_listen_cause", "Unit 2 听力中因果关系与建议信息的识别", 4, SUBJECT, 162005),
    (162062, "eng_r2_point_listen_net", "Unit 3 听力中互联网应用场景与功能描述", 5, SUBJECT, 162005),
    (162063, "eng_r2_point_listen_attitude", "Unit 3 听力中说话者态度与语气的推断", 6, SUBJECT, 162005),
    (162064, "eng_r2_point_listen_history", "Unit 4 听力中地名、朝代与历史事件的对应", 7, SUBJECT, 162005),
    (162065, "eng_r2_point_phonetic_link", "本册语音：连读、同化与失去爆破在长句中的辨音", 8, SUBJECT, 162005),

    # 口语与交际功能
    (162066, "eng_r2_point_speak_project", "Unit 1 讨论遗产保护方案的功能句型（建议、赞同、补充）", 1, SUBJECT, 162006),
    (162067, "eng_r2_point_speak_concern", "Unit 2 表达担忧与提出保护措施的交际用语", 2, SUBJECT, 162006),
    (162068, "eng_r2_point_speak_online", "Unit 3 描述网络使用习惯与表达观点的句型", 3, SUBJECT, 162006),
    (162069, "eng_r2_point_speak_place", "Unit 4 介绍历史地点的顺序表达与信息组织", 4, SUBJECT, 162006),
    (162070, "eng_r2_point_speak_music", "Unit 5 谈论音乐喜好与评价演出的功能句型", 5, SUBJECT, 162006),

    # 阅读策略与语篇分析
    (162071, "eng_r2_point_read_problem", "Unit 1 说明文“问题—解决”结构的梳理", 1, SUBJECT, 162007),
    (162072, "eng_r2_point_read_fact", "Unit 1 说明文中事实、数据与观点的区分", 2, SUBJECT, 162007),
    (162073, "eng_r2_point_read_topic", "Unit 2 科普说明文的主题句与支撑细节定位", 3, SUBJECT, 162007),
    (162074, "eng_r2_point_read_emotion", "Unit 2 描写性语篇中环境与情感线索的解读", 4, SUBJECT, 162007),
    (162075, "eng_r2_point_read_argument", "Unit 3 议论文“现象—原因—影响—对策”结构分析", 5, SUBJECT, 162007),
    (162076, "eng_r2_point_read_stance", "Unit 3 网络语篇中作者立场与读者意识的识别", 6, SUBJECT, 162007),
    (162077, "eng_r2_point_read_place", "Unit 4 说明文中地名由来与历史信息的整合", 7, SUBJECT, 162007),
    (162078, "eng_r2_point_read_timeline", "Unit 4 时间线与因果关系图在历史语篇中的运用", 8, SUBJECT, 162007),
    (162079, "eng_r2_point_read_character", "Unit 5 叙事文本中人物动机与情感变化的梳理", 9, SUBJECT, 162007),
    (162080, "eng_r2_point_read_rhetoric", "Unit 5 演讲词中重复、排比与呼告的修辞识别", 10, SUBJECT, 162007),

    # 写作体裁与过程
    (162081, "eng_r2_point_write_news_structure", "Unit 1 新闻报道的标题、导语与倒金字塔结构", 1, SUBJECT, 162008),
    (162082, "eng_r2_point_write_news_passive", "Unit 1 新闻报道中被动语态与客观引述的运用", 2, SUBJECT, 162008),
    (162083, "eng_r2_point_write_complaint_form", "Unit 2 投诉信的格式、语气与诉求表达", 3, SUBJECT, 162008),
    (162084, "eng_r2_point_write_complaint_fact", "Unit 2 投诉信中事实陈述与礼貌驳斥的平衡", 4, SUBJECT, 162008),
    (162085, "eng_r2_point_write_blog_voice", "Unit 3 博客的语篇特征、人称与互动性表达", 5, SUBJECT, 162008),
    (162086, "eng_r2_point_write_blog_media", "Unit 3 博客中链接、标签与多媒体信息的文字化呈现", 6, SUBJECT, 162008),
    (162087, "eng_r2_point_write_place_space", "Unit 4 地点描写的空间顺序与感官细节", 7, SUBJECT, 162008),
    (162088, "eng_r2_point_write_place_history", "Unit 4 地点描写中历史背景与个人感受的融合", 8, SUBJECT, 162008),
    (162089, "eng_r2_point_write_speech_structure", "Unit 5 演讲稿的开场、主体与结尾结构", 9, SUBJECT, 162008),
    (162090, "eng_r2_point_write_speech_rhetoric", "Unit 5 演讲稿中呼告、排比与情感升华的表达", 10, SUBJECT, 162008),

    # 文化意识与主题探究
    (162091, "eng_r2_point_culture_heritage", "Unit 1 中外文化遗产保护理念与国际合作", 1, SUBJECT, 162009),
    (162092, "eng_r2_point_culture_wildlife", "Unit 2 生物多样性保护与人与自然和谐共生", 2, SUBJECT, 162009),
    (162093, "eng_r2_point_culture_online", "Unit 3 数字时代的网络文明与信息素养", 3, SUBJECT, 162009),
    (162094, "eng_r2_point_culture_place", "Unit 4 中外历史地名背后的文化认同", 4, SUBJECT, 162009),
    (162095, "eng_r2_point_culture_music", "Unit 5 音乐作为跨文化沟通的桥梁", 5, SUBJECT, 162009),

    # 学习策略与单元任务
    (162096, "eng_r2_point_strategy_project", "本册单元任务：项目式学习中的资料检索与分工", 1, SUBJECT, 162010),
    (162097, "eng_r2_point_strategy_vocab", "词汇学习：主题词块归类与构词法记忆", 2, SUBJECT, 162010),
    (162098, "eng_r2_point_strategy_grammar", "语法学习：在语篇中归纳规则与错题反思", 3, SUBJECT, 162010),
    (162099, "eng_r2_point_strategy_transfer", "听说读写整合：以读促写与仿写迁移", 4, SUBJECT, 162010),
)

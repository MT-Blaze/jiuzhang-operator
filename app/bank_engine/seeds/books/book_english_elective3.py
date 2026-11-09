"""人教版（2019）高中英语选择性必修第三册：单元板块目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G10 = 10
BOOK_ID = 1206

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中英语选择性必修第三册",
    "eng_x3",
    3,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (120601, "Unit 1 Art", "eng_x3_u01", 1, BOOK_ID, None),
    (120602, "Unit 2 Healthy Lifestyle", "eng_x3_u02", 2, BOOK_ID, None),
    (120603, "Unit 3 Environmental Protection", "eng_x3_u03", 3, BOOK_ID, None),
    (120604, "Unit 4 Adversity and Courage", "eng_x3_u04", 4, BOOK_ID, None),
    (120605, "Unit 5 Poems", "eng_x3_u05", 5, BOOK_ID, None),
    # Unit 1 板块
    (120611, "Listening and Speaking: Art Forms", "eng_x3_s01", 1, BOOK_ID, 120601),
    (120612, "Reading and Thinking: A Short History of Western Painting", "eng_x3_s02", 2, BOOK_ID, 120601),
    (120613, "Discovering Useful Structures: The Subjunctive Mood (1): If-clauses", "eng_x3_s03", 3, BOOK_ID, 120601),
    (120614, "Reading for Writing: An Art Review", "eng_x3_s04", 4, BOOK_ID, 120601),
    # Unit 2 板块
    (120615, "Listening and Speaking: Healthy Habits", "eng_x3_s05", 1, BOOK_ID, 120602),
    (120616, "Reading and Thinking: Habits for a Healthy Lifestyle", "eng_x3_s06", 2, BOOK_ID, 120602),
    (120617, "Discovering Useful Structures: The Subjunctive Mood (2): Wish and If Only", "eng_x3_s07", 3, BOOK_ID, 120602),
    (120618, "Reading for Writing: A Health Survey Report", "eng_x3_s08", 4, BOOK_ID, 120602),
    # Unit 3 板块
    (120619, "Listening and Speaking: Environmental Issues", "eng_x3_s09", 1, BOOK_ID, 120603),
    (120620, "Reading and Thinking: Climate Change Requires the World's Attention", "eng_x3_s10", 2, BOOK_ID, 120603),
    (120621, "Discovering Useful Structures: The Present Perfect Continuous Tense", "eng_x3_s11", 3, BOOK_ID, 120603),
    (120622, "Reading for Writing: An Environmental Proposal", "eng_x3_s12", 4, BOOK_ID, 120603),
    # Unit 4 板块
    (120623, "Listening and Speaking: Facing Adversity", "eng_x3_s13", 1, BOOK_ID, 120604),
    (120624, "Reading and Thinking: A Successful Failure", "eng_x3_s14", 2, BOOK_ID, 120604),
    (120625, "Discovering Useful Structures: Inversion", "eng_x3_s15", 3, BOOK_ID, 120604),
    (120626, "Reading for Writing: A Story of Survival", "eng_x3_s16", 4, BOOK_ID, 120604),
    # Unit 5 板块
    (120627, "Listening and Speaking: Appreciating Poems", "eng_x3_s17", 1, BOOK_ID, 120605),
    (120628, "Reading and Thinking: A Few Simple Forms of English Poems", "eng_x3_s18", 2, BOOK_ID, 120605),
    (120629, "Discovering Useful Structures: Review of the Subjunctive Mood and Inversion", "eng_x3_s19", 3, BOOK_ID, 120605),
    (120630, "Reading for Writing: Writing a Poem", "eng_x3_s20", 4, BOOK_ID, 120605),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 166001-166010 为册域能力层，166011-166099 为单元细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (166001, "eng_x3_domain_vocab", "选必三·单元核心词汇与短语", 1, SUBJECT, G10, None),
    (166002, "eng_x3_domain_ifclause", "选必三·语法：虚拟语气（一）if 条件句", 2, SUBJECT, G10, None),
    (166003, "eng_x3_domain_wish", "选必三·语法：虚拟语气（二）wish 与 if only", 3, SUBJECT, G10, None),
    (166004, "eng_x3_domain_perfectcont", "选必三·语法：现在完成进行时", 4, SUBJECT, G10, None),
    (166005, "eng_x3_domain_inversion", "选必三·语法：倒装", 5, SUBJECT, G10, None),
    (166006, "eng_x3_domain_review", "选必三·语法：虚拟语气与倒装综合复习", 6, SUBJECT, G10, None),
    (166007, "eng_x3_domain_reading", "选必三·阅读策略与语篇分析", 7, SUBJECT, G10, None),
    (166008, "eng_x3_domain_writing", "选必三·写作体裁与过程", 8, SUBJECT, G10, None),
    (166009, "eng_x3_domain_listening", "选必三·听力、语音与口语策略", 9, SUBJECT, G10, None),
    (166010, "eng_x3_domain_culture", "选必三·文化意识与主题探究", 10, SUBJECT, G10, None),

    # 单元核心词汇与短语
    (166011, "eng_x3_point_u1_forms", "Unit 1 艺术门类名词（painting, sculpture, architecture, pottery, calligraphy）", 1, SUBJECT, G10, 166001),
    (166012, "eng_x3_point_u1_styles", "Unit 1 艺术流派与风格词块（realism, impressionism, cubism, abstract art）", 2, SUBJECT, G10, 166001),
    (166013, "eng_x3_point_u1_technique", "Unit 1 创作与技法动词（sketch, carve, compose, portray, shade）", 3, SUBJECT, G10, 166001),
    (166014, "eng_x3_point_u1_appraise", "Unit 1 艺术鉴赏形容词（lifelike, abstract, delicate, striking, timeless）", 4, SUBJECT, G10, 166001),
    (166015, "eng_x3_point_u1_phrases", "Unit 1 艺术评论短语（be renowned for, date back to, appeal to, convey emotion）", 5, SUBJECT, G10, 166001),
    (166016, "eng_x3_point_u2_health", "Unit 2 健康与习惯名词（lifestyle, habit, routine, willpower, relapse）", 6, SUBJECT, G10, 166001),
    (166017, "eng_x3_point_u2_addiction", "Unit 2 成瘾与危害词块（addiction, tobacco, alcohol, obesity, junk food）", 7, SUBJECT, G10, 166001),
    (166018, "eng_x3_point_u2_action", "Unit 2 锻炼与戒除动词（work out, quit, resist, maintain, recover）", 8, SUBJECT, G10, 166001),
    (166019, "eng_x3_point_u2_state", "Unit 2 身心状态形容词（energetic, stressful, addictive, balanced, depressed）", 9, SUBJECT, G10, 166001),
    (166020, "eng_x3_point_u2_phrases", "Unit 2 健康生活短语（be addicted to, cut down on, stick to, take up, in the long run）", 10, SUBJECT, G10, 166001),
    (166021, "eng_x3_point_u3_climate", "Unit 3 环境与气候名词（climate, greenhouse gas, emission, ecosystem, biodiversity）", 11, SUBJECT, G10, 166001),
    (166022, "eng_x3_point_u3_pollution", "Unit 3 污染与治理词块（pollution, waste, sewage, plastic, conservation）", 12, SUBJECT, G10, 166001),
    (166023, "eng_x3_point_u3_reduce", "Unit 3 节能减排动词（reduce, recycle, conserve, emit, restore）", 13, SUBJECT, G10, 166001),
    (166024, "eng_x3_point_u3_state", "Unit 3 环境状况形容词（sustainable, renewable, fragile, severe, irreversible）", 14, SUBJECT, G10, 166001),
    (166025, "eng_x3_point_u3_phrases", "Unit 3 环保行动短语（carbon footprint, global warming, sea level, die out, take action）", 15, SUBJECT, G10, 166001),
    (166026, "eng_x3_point_u4_adversity", "Unit 4 逆境与探险名词（adversity, hardship, expedition, endurance, survival）", 16, SUBJECT, G10, 166001),
    (166027, "eng_x3_point_u4_polar", "Unit 4 极地环境词块（Antarctica, ice pack, blizzard, crew, rescue）", 17, SUBJECT, G10, 166001),
    (166028, "eng_x3_point_u4_survive", "Unit 4 求生与航行动词（endure, abandon, navigate, shelter, rescue）", 18, SUBJECT, G10, 166001),
    (166029, "eng_x3_point_u4_spirit", "Unit 4 意志品质形容词（courageous, determined, desperate, resilient, hopeless）", 19, SUBJECT, G10, 166001),
    (166030, "eng_x3_point_u4_phrases", "Unit 4 逆境应对短语（give up, hold on, come to terms with, in despair, pull through）", 20, SUBJECT, G10, 166001),
    (166031, "eng_x3_point_u5_form", "Unit 5 诗歌形式名词（poem, rhyme, stanza, syllable, imagery）", 21, SUBJECT, G10, 166001),
    (166032, "eng_x3_point_u5_types", "Unit 5 诗歌类型词块（nursery rhyme, list poem, cinquain, haiku, sonnet）", 22, SUBJECT, G10, 166001),
    (166033, "eng_x3_point_u5_compose", "Unit 5 诗歌创作动词（rhyme, compose, recite, convey, evoke）", 23, SUBJECT, G10, 166001),
    (166034, "eng_x3_point_u5_language", "Unit 5 诗歌语言形容词（rhythmic, vivid, figurative, concise, melodious）", 24, SUBJECT, G10, 166001),
    (166035, "eng_x3_point_u5_phrases", "Unit 5 诗歌赏析短语（in free verse, figure of speech, sensory detail, emotional appeal）", 25, SUBJECT, G10, 166001),

    # 虚拟语气（一）if 条件句
    (166036, "eng_x3_point_if_three", "Unit 1 虚拟条件句的现在、过去、将来三种时间框架", 1, SUBJECT, G10, 166002),
    (166037, "eng_x3_point_if_present", "Unit 1 与现在事实相反的虚拟条件句（If + did/were, would do）", 2, SUBJECT, G10, 166002),
    (166038, "eng_x3_point_if_past", "Unit 1 与过去事实相反的虚拟条件句（If + had done, would have done）", 3, SUBJECT, G10, 166002),
    (166039, "eng_x3_point_if_future", "Unit 1 与将来事实相反的虚拟条件句（If + did/were to do/should do）", 4, SUBJECT, G10, 166002),
    (166040, "eng_x3_point_if_mixed", "Unit 1 错综时间虚拟条件句：从句与主句时间不一致", 5, SUBJECT, G10, 166002),
    (166041, "eng_x3_point_if_inversion", "Unit 1 省略 if 的倒装条件句（Were I, Had I, Should I）", 6, SUBJECT, G10, 166002),
    (166042, "eng_x3_point_if_implicit", "Unit 1 but for、without 与 otherwise 引导的含蓄虚拟", 7, SUBJECT, G10, 166002),
    (166043, "eng_x3_point_if_pragmatic", "Unit 1 虚拟条件句在艺术评论假设与推测中的语用", 8, SUBJECT, G10, 166002),

    # 虚拟语气（二）wish 与 if only
    (166044, "eng_x3_point_wish_present", "Unit 2 wish 后接过去时表示与现在事实相反的愿望", 1, SUBJECT, G10, 166003),
    (166045, "eng_x3_point_wish_past", "Unit 2 wish 后接过去完成时表示对过去的遗憾", 2, SUBJECT, G10, 166003),
    (166046, "eng_x3_point_wish_future", "Unit 2 wish 后接 would/could 表示对将来的期待", 3, SUBJECT, G10, 166003),
    (166047, "eng_x3_point_ifonly", "Unit 2 if only 感叹式虚拟的构成与语气强度", 4, SUBJECT, G10, 166003),
    (166048, "eng_x3_point_rather", "Unit 2 would rather 与 would sooner 后的虚拟形式", 5, SUBJECT, G10, 166003),
    (166049, "eng_x3_point_asif", "Unit 2 as if/as though 引导的虚拟比较", 6, SUBJECT, G10, 166003),
    (166050, "eng_x3_point_hightime", "Unit 2 It is (high) time that... 句型中的虚拟", 7, SUBJECT, G10, 166003),

    # 现在完成进行时
    (166051, "eng_x3_point_ppc_form", "Unit 3 现在完成进行时的构成 have/has been doing 与句式变化", 1, SUBJECT, G10, 166004),
    (166052, "eng_x3_point_ppc_meaning", "Unit 3 现在完成进行时表示动作持续至今并可能延续", 2, SUBJECT, G10, 166004),
    (166053, "eng_x3_point_ppc_for", "Unit 3 for 与 since 引导的持续时间状语辨析", 3, SUBJECT, G10, 166004),
    (166054, "eng_x3_point_ppc_vs", "Unit 3 现在完成进行时与现在完成时的语义差别", 4, SUBJECT, G10, 166004),
    (166055, "eng_x3_point_ppc_report", "Unit 3 环保报道中现在完成进行时的复现与强调", 5, SUBJECT, G10, 166004),
    (166056, "eng_x3_point_ppc_stative", "Unit 3 状态动词用于现在完成进行时的限制", 6, SUBJECT, G10, 166004),
    (166057, "eng_x3_point_ppc_past", "Unit 3 现在完成进行时与一般过去时的叙述视角", 7, SUBJECT, G10, 166004),

    # 倒装
    (166058, "eng_x3_point_inv_basic", "Unit 4 倒装的界定：完全倒装与部分倒装", 1, SUBJECT, G10, 166005),
    (166059, "eng_x3_point_inv_negative", "Unit 4 否定词置于句首引起部分倒装（never, seldom, rarely）", 2, SUBJECT, G10, 166005),
    (166060, "eng_x3_point_inv_hardly", "Unit 4 Hardly...when 与 No sooner...than 的倒装与时态", 3, SUBJECT, G10, 166005),
    (166061, "eng_x3_point_inv_notuntil", "Unit 4 Not until 置于句首时的主句倒装", 4, SUBJECT, G10, 166005),
    (166062, "eng_x3_point_inv_only", "Unit 4 Only + 状语置于句首引起倒装", 5, SUBJECT, G10, 166005),
    (166063, "eng_x3_point_inv_so", "Unit 4 so/neither/nor 引导的倒装表示呼应", 6, SUBJECT, G10, 166005),
    (166064, "eng_x3_point_inv_place", "Unit 4 地点介词短语置于句首的完全倒装", 7, SUBJECT, G10, 166005),
    (166065, "eng_x3_point_inv_concession", "Unit 4 让步状语从句中 as/though 引导的倒装", 8, SUBJECT, G10, 166005),

    # 虚拟语气与倒装综合复习
    (166066, "eng_x3_point_rev_hadit", "Unit 5 Had it not been for 等虚拟倒装的交叉结构", 1, SUBJECT, G10, 166006),
    (166067, "eng_x3_point_rev_implicit", "Unit 5 含蓄虚拟与倒装结构的综合辨析", 2, SUBJECT, G10, 166006),
    (166068, "eng_x3_point_rev_emphasis", "Unit 5 否定倒装与强调句的结构区分", 3, SUBJECT, G10, 166006),
    (166069, "eng_x3_point_rev_noun", "Unit 5 虚拟语气在 suggest、demand、insist 后从句中的复习", 4, SUBJECT, G10, 166006),
    (166070, "eng_x3_point_rev_poetry", "Unit 5 倒装在诗歌与演讲语篇中的修辞效果", 5, SUBJECT, G10, 166006),
    (166071, "eng_x3_point_rev_path", "Unit 5 虚拟与倒装混合填空题的判定路径", 6, SUBJECT, G10, 166006),
    (166072, "eng_x3_point_rev_style", "Unit 5 语篇改写中虚拟与倒装的语体适配", 7, SUBJECT, G10, 166006),

    # 阅读策略与语篇分析
    (166073, "eng_x3_point_read_painting", "Unit 1 西方绘画史说明文的时间顺序与流派对照", 1, SUBJECT, G10, 166007),
    (166074, "eng_x3_point_read_review", "Unit 1 阅读中辨识艺术评论的客观描述与主观评价", 2, SUBJECT, G10, 166007),
    (166075, "eng_x3_point_read_health", "Unit 2 健康科普文本的问题—原因—建议结构", 3, SUBJECT, G10, 166007),
    (166076, "eng_x3_point_read_evidence", "Unit 2 阅读中区分科学证据与个人经验", 4, SUBJECT, G10, 166007),
    (166077, "eng_x3_point_read_climate", "Unit 3 气候变化语篇的因果链与数据支撑", 5, SUBJECT, G10, 166007),
    (166078, "eng_x3_point_read_survival", "Unit 4 生存叙事的时间线、悬念与人物心理", 6, SUBJECT, G10, 166007),
    (166079, "eng_x3_point_read_poem", "Unit 5 诗歌阅读中的意象、韵律与情感基调", 7, SUBJECT, G10, 166007),
    (166080, "eng_x3_point_read_predict", "本册跨单元：标题、图表与首末段的预测与验证", 8, SUBJECT, G10, 166007),

    # 写作体裁与过程
    (166081, "eng_x3_point_write_artreview", "Unit 1 艺术评论：作品信息、形式分析与评价结构", 1, SUBJECT, G10, 166008),
    (166082, "eng_x3_point_write_describe", "Unit 1 艺术评论中描述性形容词与评价句型的运用", 2, SUBJECT, G10, 166008),
    (166083, "eng_x3_point_write_survey", "Unit 2 健康调查报告：目的、数据呈现与结论建议", 3, SUBJECT, G10, 166008),
    (166084, "eng_x3_point_write_data", "Unit 2 报告中数据表述与图表说明句式", 4, SUBJECT, G10, 166008),
    (166085, "eng_x3_point_write_proposal", "Unit 3 环保倡议书：问题陈述、呼吁与行动方案", 5, SUBJECT, G10, 166008),
    (166086, "eng_x3_point_write_appeal", "Unit 3 倡议书呼吁语与情态动词的说服力", 6, SUBJECT, G10, 166008),
    (166087, "eng_x3_point_write_story", "Unit 4 生存故事：背景、冲突、高潮与结局的叙事弧", 7, SUBJECT, G10, 166008),
    (166088, "eng_x3_point_write_poem", "Unit 5 诗歌创作：意象选取、分行与押韵的尝试", 8, SUBJECT, G10, 166008),

    # 听力、语音与口语策略
    (166089, "eng_x3_point_listen_art", "Unit 1 艺术话题听力：作品描述与导览信息捕捉", 1, SUBJECT, G10, 166009),
    (166090, "eng_x3_point_listen_health", "Unit 2 健康建议听力：建议、警告与理由的辨识", 2, SUBJECT, G10, 166009),
    (166091, "eng_x3_point_listen_env", "Unit 3 环境新闻听力：数字、时间与因果信号词", 3, SUBJECT, G10, 166009),
    (166092, "eng_x3_point_listen_adversity", "Unit 4 探险访谈听力：逆境经历与情感态度", 4, SUBJECT, G10, 166009),
    (166093, "eng_x3_point_recite", "Unit 5 诗歌朗诵：节奏、重音与语调的模仿", 5, SUBJECT, G10, 166009),
    (166094, "eng_x3_point_phonetic", "本册语音：弱读、同化与意群停顿的辨听", 6, SUBJECT, G10, 166009),

    # 文化意识与主题探究
    (166095, "eng_x3_point_culture_painting", "Unit 1 中西方绘画传统的比较与审美差异", 1, SUBJECT, G10, 166010),
    (166096, "eng_x3_point_culture_health", "Unit 2 中外健康观念与生活方式的文化解读", 2, SUBJECT, G10, 166010),
    (166097, "eng_x3_point_culture_env", "Unit 3 全球环境治理与可持续发展的共同责任", 3, SUBJECT, G10, 166010),
    (166098, "eng_x3_point_culture_explore", "Unit 4 探险精神与团队领导力的文化价值", 4, SUBJECT, G10, 166010),
    (166099, "eng_x3_point_culture_poem", "Unit 5 中英诗歌互译中的意象转换与文化传递", 5, SUBJECT, G10, 166010),
)

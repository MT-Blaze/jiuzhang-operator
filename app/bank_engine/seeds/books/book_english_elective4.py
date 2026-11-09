"""人教版（2019）高中英语选择性必修第四册：单元板块目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G10 = 10
BOOK_ID = 1207

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中英语选择性必修第四册",
    "eng_x4",
    4,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (120701, "Unit 1 Science Fiction", "eng_x4_u01", 1, BOOK_ID, None),
    (120702, "Unit 2 Iconic Attractions", "eng_x4_u02", 2, BOOK_ID, None),
    (120703, "Unit 3 Sea Exploration", "eng_x4_u03", 3, BOOK_ID, None),
    (120704, "Unit 4 Sharing", "eng_x4_u04", 4, BOOK_ID, None),
    (120705, "Unit 5 Launching Your Career", "eng_x4_u05", 5, BOOK_ID, None),
    # Unit 1 板块
    (120711, "Listening and Speaking: Science Fiction", "eng_x4_s01", 1, BOOK_ID, 120701),
    (120712, "Reading and Thinking: Satisfaction Guaranteed", "eng_x4_s02", 2, BOOK_ID, 120701),
    (120713, "Discovering Useful Structures: Review of the Passive Voice", "eng_x4_s03", 3, BOOK_ID, 120701),
    (120714, "Reading for Writing: A Science Fiction Story", "eng_x4_s04", 4, BOOK_ID, 120701),
    # Unit 2 板块
    (120715, "Listening and Speaking: Iconic Attractions", "eng_x4_s05", 1, BOOK_ID, 120702),
    (120716, "Reading and Thinking: Iconic Attractions of Australia", "eng_x4_s06", 2, BOOK_ID, 120702),
    (120717, "Discovering Useful Structures: Review of Relative Clauses", "eng_x4_s07", 3, BOOK_ID, 120702),
    (120718, "Reading for Writing: A Travel Brochure", "eng_x4_s08", 4, BOOK_ID, 120702),
    # Unit 3 板块
    (120719, "Listening and Speaking: Sea Exploration", "eng_x4_s09", 1, BOOK_ID, 120703),
    (120720, "Reading and Thinking: The Deep Sea", "eng_x4_s10", 2, BOOK_ID, 120703),
    (120721, "Discovering Useful Structures: Review of Adverbial Clauses", "eng_x4_s11", 3, BOOK_ID, 120703),
    (120722, "Reading for Writing: An Ocean Exploration Report", "eng_x4_s12", 4, BOOK_ID, 120703),
    # Unit 4 板块
    (120723, "Listening and Speaking: Voluntary Work", "eng_x4_s13", 1, BOOK_ID, 120704),
    (120724, "Reading and Thinking: A Letter Home", "eng_x4_s14", 2, BOOK_ID, 120704),
    (120725, "Discovering Useful Structures: Review of Noun Clauses", "eng_x4_s15", 3, BOOK_ID, 120704),
    (120726, "Reading for Writing: A Volunteer Application Letter", "eng_x4_s16", 4, BOOK_ID, 120704),
    # Unit 5 板块
    (120727, "Listening and Speaking: Career Planning", "eng_x4_s17", 1, BOOK_ID, 120705),
    (120728, "Reading and Thinking: Working Out What You Want to Do", "eng_x4_s18", 2, BOOK_ID, 120705),
    (120729, "Discovering Useful Structures: Emphatic Structures", "eng_x4_s19", 3, BOOK_ID, 120705),
    (120730, "Reading for Writing: A Personal Statement", "eng_x4_s20", 4, BOOK_ID, 120705),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 167001-167010 为册域能力层，167011-167099 为单元细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (167001, "eng_x4_domain_vocab", "选必四·单元核心词汇与短语", 1, SUBJECT, G10, None),
    (167002, "eng_x4_domain_passive", "选必四·语法：被动语态复习", 2, SUBJECT, G10, None),
    (167003, "eng_x4_domain_relative", "选必四·语法：定语从句复习", 3, SUBJECT, G10, None),
    (167004, "eng_x4_domain_adverbial", "选必四·语法：状语从句复习", 4, SUBJECT, G10, None),
    (167005, "eng_x4_domain_nounclause", "选必四·语法：名词性从句复习", 5, SUBJECT, G10, None),
    (167006, "eng_x4_domain_emphatic", "选必四·语法：强调句", 6, SUBJECT, G10, None),
    (167007, "eng_x4_domain_reading", "选必四·阅读策略与语篇分析", 7, SUBJECT, G10, None),
    (167008, "eng_x4_domain_writing", "选必四·写作体裁与过程", 8, SUBJECT, G10, None),
    (167009, "eng_x4_domain_listening", "选必四·听力、语音与口语策略", 9, SUBJECT, G10, None),
    (167010, "eng_x4_domain_culture", "选必四·文化意识与主题探究", 10, SUBJECT, G10, None),

    # 单元核心词汇与短语
    (167011, "eng_x4_point_u1_robot", "Unit 1 科幻与机器人名词（fiction, android, artificial intelligence, spacecraft, clone）", 1, SUBJECT, G10, 167001),
    (167012, "eng_x4_point_u1_story", "Unit 1 小说叙事要素词块（plot, character, setting, narrator, climax, twist）", 2, SUBJECT, G10, 167001),
    (167013, "eng_x4_point_u1_action", "Unit 1 科幻情节动词（satisfy, obey, rebel, transmit, transform, threaten）", 3, SUBJECT, G10, 167001),
    (167014, "eng_x4_point_u1_adj", "Unit 1 机器与未来形容词（intelligent, mechanical, humanlike, artificial, futuristic）", 4, SUBJECT, G10, 167001),
    (167015, "eng_x4_point_u1_phrases", "Unit 1 科幻叙事短语（be programmed to, come to life, take over, be capable of）", 5, SUBJECT, G10, 167001),
    (167016, "eng_x4_point_u2_site", "Unit 2 景点与遗产名词（attraction, landmark, monument, heritage, icon, site）", 6, SUBJECT, G10, 167001),
    (167017, "eng_x4_point_u2_land", "Unit 2 自然与人文景观词块（landscape, wildlife, reef, harbour, bridge, scenery）", 7, SUBJECT, G10, 167001),
    (167018, "eng_x4_point_u2_visit", "Unit 2 游览与体验动词（explore, admire, witness, preserve, represent, symbolise）", 8, SUBJECT, G10, 167001),
    (167019, "eng_x4_point_u2_adj", "Unit 2 目的地特征形容词（indigenous, iconic, spectacular, remote, tropical）", 9, SUBJECT, G10, 167001),
    (167020, "eng_x4_point_u2_phrases", "Unit 2 地标介绍短语（be famous for, date back to, be home to, off the beaten track）", 10, SUBJECT, G10, 167001),
    (167021, "eng_x4_point_u3_voyage", "Unit 3 海洋探索名词（exploration, expedition, voyage, submarine, diver, depth）", 11, SUBJECT, G10, 167001),
    (167022, "eng_x4_point_u3_marine", "Unit 3 海洋环境与生物词块（current, tide, coral, whale, habitat, ecosystem）", 12, SUBJECT, G10, 167001),
    (167023, "eng_x4_point_u3_explore", "Unit 3 探测与保护动词（dive, discover, map, survey, observe, conserve）", 13, SUBJECT, G10, 167001),
    (167024, "eng_x4_point_u3_adj", "Unit 3 深海与未知形容词（marine, underwater, deep-sea, uncharted, vast, mysterious）", 14, SUBJECT, G10, 167001),
    (167025, "eng_x4_point_u3_phrases", "Unit 3 海洋探索短语（plunge into, at the mercy of, a wealth of, in the depths of）", 15, SUBJECT, G10, 167001),
    (167026, "eng_x4_point_u4_service", "Unit 4 志愿与公益名词（volunteer, charity, donation, community, project, clinic）", 16, SUBJECT, G10, 167001),
    (167027, "eng_x4_point_u4_support", "Unit 4 援助与共享动词（share, contribute, donate, assist, support, participate）", 17, SUBJECT, G10, 167001),
    (167028, "eng_x4_point_u4_adj", "Unit 4 公益情境形容词（generous, grateful, rewarding, challenging, deprived）", 18, SUBJECT, G10, 167001),
    (167029, "eng_x4_point_u4_social", "Unit 4 社会议题词块（education, healthcare, resource, opportunity, poverty）", 19, SUBJECT, G10, 167001),
    (167030, "eng_x4_point_u4_phrases", "Unit 4 志愿服务短语（make a difference, give back, reach out to, be committed to）", 20, SUBJECT, G10, 167001),
    (167031, "eng_x4_point_u5_job", "Unit 5 职业与求职名词（career, profession, occupation, employer, interview, resume）", 21, SUBJECT, G10, 167001),
    (167032, "eng_x4_point_u5_self", "Unit 5 自我认知词块（strength, weakness, passion, ambition, potential, qualification）", 22, SUBJECT, G10, 167001),
    (167033, "eng_x4_point_u5_action", "Unit 5 求职与发展动词（apply, recruit, employ, pursue, achieve, specialise）", 23, SUBJECT, G10, 167001),
    (167034, "eng_x4_point_u5_adj", "Unit 5 职业素养形容词（qualified, motivated, ambitious, capable, competitive）", 24, SUBJECT, G10, 167001),
    (167035, "eng_x4_point_u5_phrases", "Unit 5 生涯规划短语（apply for, be suited to, stand out, set a goal）", 25, SUBJECT, G10, 167001),

    # 被动语态复习
    (167036, "eng_x4_point_pas_form", "Unit 1 被动语态的构成 be + 过去分词及各时态形式", 1, SUBJECT, G10, 167002),
    (167037, "eng_x4_point_pas_present", "Unit 1 一般现在时与一般过去时被动语态的使用场景", 2, SUBJECT, G10, 167002),
    (167038, "eng_x4_point_pas_perfect", "Unit 1 现在完成时与过去完成时被动语态", 3, SUBJECT, G10, 167002),
    (167039, "eng_x4_point_pas_modal", "Unit 1 含情态动词的被动语态（can be done, must be done）", 4, SUBJECT, G10, 167002),
    (167040, "eng_x4_point_pas_by", "Unit 1 被动语态中 by 短语的取舍与信息焦点", 5, SUBJECT, G10, 167002),
    (167041, "eng_x4_point_pas_double", "Unit 1 双宾语与复合宾语的被动转换（give sb sth, make sb do）", 6, SUBJECT, G10, 167002),
    (167042, "eng_x4_point_pas_activeform", "Unit 1 主动形式表被动意义（sell well, need doing）", 7, SUBJECT, G10, 167002),
    (167043, "eng_x4_point_pas_function", "Unit 1 科幻语篇中被动语态客观化叙述的功能", 8, SUBJECT, G10, 167002),

    # 定语从句复习
    (167044, "eng_x4_point_rel_pronoun", "Unit 2 关系代词 who/whom/whose/which/that 的选择", 1, SUBJECT, G10, 167003),
    (167045, "eng_x4_point_rel_adverb", "Unit 2 关系副词 when/where/why 与先行词的对应", 2, SUBJECT, G10, 167003),
    (167046, "eng_x4_point_rel_restrictive", "Unit 2 限制性与非限制性定语从句的逗号与语义差别", 3, SUBJECT, G10, 167003),
    (167047, "eng_x4_point_rel_prep", "Unit 2 介词 + 关系代词（in which, of whom, to which）", 4, SUBJECT, G10, 167003),
    (167048, "eng_x4_point_rel_as", "Unit 2 as 引导的定语从句与 such/the same 结构", 5, SUBJECT, G10, 167003),
    (167049, "eng_x4_point_rel_agreement", "Unit 2 定语从句中的主谓一致与关系词的省略", 6, SUBJECT, G10, 167003),
    (167050, "eng_x4_point_rel_merge", "Unit 2 旅游介绍语篇中用定语从句合并短句", 7, SUBJECT, G10, 167003),

    # 状语从句复习
    (167051, "eng_x4_point_adv_time", "Unit 3 时间状语从句中 when/while/as 的辨析", 1, SUBJECT, G10, 167004),
    (167052, "eng_x4_point_adv_condition", "Unit 3 条件状语从句与 if/unless/as long as 的使用", 2, SUBJECT, G10, 167004),
    (167053, "eng_x4_point_adv_cause", "Unit 3 原因、结果与目的状语从句（because, so...that, so that）", 3, SUBJECT, G10, 167004),
    (167054, "eng_x4_point_adv_concession", "Unit 3 让步状语从句（although, even if, no matter how）", 4, SUBJECT, G10, 167004),
    (167055, "eng_x4_point_adv_comparison", "Unit 3 比较状语从句与 as...as、than 结构", 5, SUBJECT, G10, 167004),
    (167056, "eng_x4_point_adv_omit", "Unit 3 状语从句的省略与 before/after 的非谓语化", 6, SUBJECT, G10, 167004),
    (167057, "eng_x4_point_adv_report", "Unit 3 海洋报道中状语从句组织因果与时间关系", 7, SUBJECT, G10, 167004),

    # 名词性从句复习
    (167058, "eng_x4_point_nc_subject", "Unit 4 主语从句的 that 与 whether 选择及形式主语 it", 1, SUBJECT, G10, 167005),
    (167059, "eng_x4_point_nc_object", "Unit 4 宾语从句的语序、时态呼应与连接词", 2, SUBJECT, G10, 167005),
    (167060, "eng_x4_point_nc_predicative", "Unit 4 表语从句与同位语从句的判定", 3, SUBJECT, G10, 167005),
    (167061, "eng_x4_point_nc_that", "Unit 4 that 在同位语从句与定语从句中的区别", 4, SUBJECT, G10, 167005),
    (167062, "eng_x4_point_nc_wh", "Unit 4 疑问词引导的名词性从句（what, how, why）", 5, SUBJECT, G10, 167005),
    (167063, "eng_x4_point_nc_formalit", "Unit 4 名词性从句中 it 作形式宾语的结构", 6, SUBJECT, G10, 167005),
    (167064, "eng_x4_point_nc_volunteer", "Unit 4 志愿者叙述中用名词性从句表达愿望与观点", 7, SUBJECT, G10, 167005),

    # 强调句
    (167065, "eng_x4_point_emp_basic", "Unit 5 It is/was...that... 强调句的基本构成与识别", 1, SUBJECT, G10, 167006),
    (167066, "eng_x4_point_emp_parts", "Unit 5 强调主语、宾语与状语的还原检验", 2, SUBJECT, G10, 167006),
    (167067, "eng_x4_point_emp_distinguish", "Unit 5 强调句与定语从句、主语从句的结构区分", 3, SUBJECT, G10, 167006),
    (167068, "eng_x4_point_emp_notuntil", "Unit 5 not...until 句型的强调式 It was not until...that...", 4, SUBJECT, G10, 167006),
    (167069, "eng_x4_point_emp_question", "Unit 5 强调句的一般疑问句与特殊疑问句形式", 5, SUBJECT, G10, 167006),
    (167070, "eng_x4_point_emp_do", "Unit 5 do/does/did 强调谓语动词的用法", 6, SUBJECT, G10, 167006),
    (167071, "eng_x4_point_emp_statement", "Unit 5 个人陈述中用强调结构突显优势与经历", 7, SUBJECT, G10, 167006),

    # 阅读策略与语篇分析
    (167072, "eng_x4_point_read_scifi", "Unit 1 科幻小说要素（人物、设定、冲突、结局）的梳理", 1, SUBJECT, G10, 167007),
    (167073, "eng_x4_point_read_fact", "Unit 1 区分科幻文本中的科学事实与虚构想象", 2, SUBJECT, G10, 167007),
    (167074, "eng_x4_point_read_travel", "Unit 2 旅游宣传文本的事实信息与评价语言", 3, SUBJECT, G10, 167007),
    (167075, "eng_x4_point_read_visual", "Unit 2 图文结合获取目的地信息与行程线索", 4, SUBJECT, G10, 167007),
    (167076, "eng_x4_point_read_ocean", "Unit 3 海洋探索说明文的定义—举例—数据结构", 5, SUBJECT, G10, 167007),
    (167077, "eng_x4_point_read_letter", "Unit 4 书信体裁的称呼、目的段与情感表达", 6, SUBJECT, G10, 167007),
    (167078, "eng_x4_point_read_career", "Unit 5 职业规划文本中观点与论据的对应", 7, SUBJECT, G10, 167007),
    (167079, "eng_x4_point_read_clause", "本册跨单元：长难句主干提取与从句切分", 8, SUBJECT, G10, 167007),

    # 写作体裁与过程
    (167080, "eng_x4_point_write_scifi", "Unit 1 科幻故事：设定、冲突与出人意料的结尾", 1, SUBJECT, G10, 167008),
    (167081, "eng_x4_point_write_tense", "Unit 1 科幻叙事中的时态一致与描写性语言", 2, SUBJECT, G10, 167008),
    (167082, "eng_x4_point_write_brochure", "Unit 2 旅游手册：目的地介绍、亮点与实用信息", 3, SUBJECT, G10, 167008),
    (167083, "eng_x4_point_write_appeal", "Unit 2 旅游手册中祈使句与评价形容词的吸引力", 4, SUBJECT, G10, 167008),
    (167084, "eng_x4_point_write_report", "Unit 3 海洋探索报告：目的、方法、发现与结论", 5, SUBJECT, G10, 167008),
    (167085, "eng_x4_point_write_apply", "Unit 4 志愿者申请信：动机、经历与能力匹配", 6, SUBJECT, G10, 167008),
    (167086, "eng_x4_point_write_formal", "Unit 4 申请信正式语体与结尾期待回复的表达", 7, SUBJECT, G10, 167008),
    (167087, "eng_x4_point_write_statement", "Unit 5 个人陈述：自我认知、经历支撑与职业目标", 8, SUBJECT, G10, 167008),

    # 听力、语音与口语策略
    (167088, "eng_x4_point_listen_scifi", "Unit 1 科幻话题听力：预测情节与观点态度", 1, SUBJECT, G10, 167009),
    (167089, "eng_x4_point_listen_guide", "Unit 2 景点导览听力：方位、顺序与时间信息", 2, SUBJECT, G10, 167009),
    (167090, "eng_x4_point_listen_lecture", "Unit 3 海洋讲座听力：数字、单位与比较信息", 3, SUBJECT, G10, 167009),
    (167091, "eng_x4_point_listen_interview", "Unit 4 志愿项目访谈听力：任务分工与感受", 4, SUBJECT, G10, 167009),
    (167092, "eng_x4_point_listen_job", "Unit 5 求职面试听力：问题意图与应答策略", 5, SUBJECT, G10, 167009),
    (167093, "eng_x4_point_phonetic", "本册语音：连读、弱读与语调在态度表达中的作用", 6, SUBJECT, G10, 167009),

    # 文化意识与主题探究
    (167094, "eng_x4_point_culture_scifi", "Unit 1 中外科幻文学传统与科技伦理思考", 1, SUBJECT, G10, 167010),
    (167095, "eng_x4_point_culture_au", "Unit 2 澳大利亚原住民文化与地标遗产保护", 2, SUBJECT, G10, 167010),
    (167096, "eng_x4_point_culture_ocean", "Unit 3 海洋探索史与海洋生态保护的全球责任", 3, SUBJECT, G10, 167010),
    (167097, "eng_x4_point_culture_volunteer", "Unit 4 中外志愿服务精神与社区参与", 4, SUBJECT, G10, 167010),
    (167098, "eng_x4_point_culture_career", "Unit 5 中外职业观与生涯规划的文化差异", 5, SUBJECT, G10, 167010),
    (167099, "eng_x4_point_culture_theme", "本册主题：科技、自然与人文的交汇表达", 6, SUBJECT, G10, 167010),
)

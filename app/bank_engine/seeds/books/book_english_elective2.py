"""人教版（2019）高中英语选择性必修第二册：单元板块目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G10 = 10
BOOK_ID = 1205

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中英语选择性必修第二册",
    "eng_x2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (120501, "Unit 1 Science and Scientists", "eng_x2_u01", 1, BOOK_ID, None),
    (120502, "Unit 2 Bridging Cultures", "eng_x2_u02", 2, BOOK_ID, None),
    (120503, "Unit 3 Food and Culture", "eng_x2_u03", 3, BOOK_ID, None),
    (120504, "Unit 4 Journey Across a Vast Land", "eng_x2_u04", 4, BOOK_ID, None),
    (120505, "Unit 5 First Aid", "eng_x2_u05", 5, BOOK_ID, None),
    # Unit 1 板块
    (120511, "Listening and Speaking: Scientific Discoveries", "eng_x2_s01", 1, BOOK_ID, 120501),
    (120512, "Reading and Thinking: John Snow Defeats King Cholera", "eng_x2_s02", 2, BOOK_ID, 120501),
    (120513, "Discovering Useful Structures: Predicative Clauses", "eng_x2_s03", 3, BOOK_ID, 120501),
    (120514, "Reading for Writing: A Report on a Scientific Experiment", "eng_x2_s04", 4, BOOK_ID, 120501),
    # Unit 2 板块
    (120515, "Listening and Speaking: Studying Abroad", "eng_x2_s05", 1, BOOK_ID, 120502),
    (120516, "Reading and Thinking: Welcome, Xie Lei!", "eng_x2_s06", 2, BOOK_ID, 120502),
    (120517, "Discovering Useful Structures: Object Clauses", "eng_x2_s07", 3, BOOK_ID, 120502),
    (120518, "Reading for Writing: A Letter of Application", "eng_x2_s08", 4, BOOK_ID, 120502),
    # Unit 3 板块
    (120519, "Listening and Speaking: Food and Health", "eng_x2_s09", 1, BOOK_ID, 120503),
    (120520, "Reading and Thinking: Culture and Cuisine", "eng_x2_s10", 2, BOOK_ID, 120503),
    (120521, "Discovering Useful Structures: Appositive Clauses", "eng_x2_s11", 3, BOOK_ID, 120503),
    (120522, "Reading for Writing: A Description of a Dish", "eng_x2_s12", 4, BOOK_ID, 120503),
    # Unit 4 板块
    (120523, "Listening and Speaking: Travel in Canada", "eng_x2_s13", 1, BOOK_ID, 120504),
    (120524, "Reading and Thinking: Seeing the True North via Rail", "eng_x2_s14", 2, BOOK_ID, 120504),
    (120525, "Discovering Useful Structures: The Past Perfect Tense", "eng_x2_s15", 3, BOOK_ID, 120504),
    (120526, "Reading for Writing: A Travel Journal", "eng_x2_s16", 4, BOOK_ID, 120504),
    # Unit 5 板块
    (120527, "Listening and Speaking: First Aid", "eng_x2_s17", 1, BOOK_ID, 120505),
    (120528, "Reading and Thinking: First Aid for Burns", "eng_x2_s18", 2, BOOK_ID, 120505),
    (120529, "Discovering Useful Structures: Review of Verb Tenses", "eng_x2_s19", 3, BOOK_ID, 120505),
    (120530, "Reading for Writing: A First Aid Instruction", "eng_x2_s20", 4, BOOK_ID, 120505),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 165001-165010 为册域能力层，165011-165099 为单元细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (165001, "eng_x2_domain_vocab", "选必二·单元核心词汇与短语", 1, SUBJECT, G10, None),
    (165002, "eng_x2_domain_predicative", "选必二·语法：表语从句", 2, SUBJECT, G10, None),
    (165003, "eng_x2_domain_object", "选必二·语法：宾语从句", 3, SUBJECT, G10, None),
    (165004, "eng_x2_domain_appositive", "选必二·语法：同位语从句", 4, SUBJECT, G10, None),
    (165005, "eng_x2_domain_pastperfect", "选必二·语法：过去完成时", 5, SUBJECT, G10, None),
    (165006, "eng_x2_domain_tense", "选必二·语法：时态复习与综合运用", 6, SUBJECT, G10, None),
    (165007, "eng_x2_domain_reading", "选必二·阅读策略与语篇分析", 7, SUBJECT, G10, None),
    (165008, "eng_x2_domain_writing", "选必二·写作体裁与过程", 8, SUBJECT, G10, None),
    (165009, "eng_x2_domain_listening", "选必二·听力、语音与口语策略", 9, SUBJECT, G10, None),
    (165010, "eng_x2_domain_culture", "选必二·文化意识与主题探究", 10, SUBJECT, G10, None),

    # 单元核心词汇与短语
    (165011, "eng_x2_point_u1_science", "Unit 1 科学与科学家名词（scientist, research, experiment, theory, evidence）", 1, SUBJECT, G10, 165001),
    (165012, "eng_x2_point_u1_disease", "Unit 1 疾病与防疫词块（cholera, outbreak, infection, cure, vaccine）", 2, SUBJECT, G10, 165001),
    (165013, "eng_x2_point_u1_verify", "Unit 1 科研论证动词（prove, confirm, suspect, analyse, conclude）", 3, SUBJECT, G10, 165001),
    (165014, "eng_x2_point_u1_rigour", "Unit 1 严谨与怀疑形容词（rigorous, sceptical, convincing, reliable）", 4, SUBJECT, G10, 165001),
    (165015, "eng_x2_point_u1_inquiry", "Unit 1 科学探究短语（carry out, come down with, be to blame, in conclusion）", 5, SUBJECT, G10, 165001),
    (165016, "eng_x2_point_u2_exchange", "Unit 2 留学与文化交流名词（exchange, adaptation, orientation, culture shock）", 6, SUBJECT, G10, 165001),
    (165017, "eng_x2_point_u2_admission", "Unit 2 申请与录取词块（application, admission, scholarship, reference）", 7, SUBJECT, G10, 165001),
    (165018, "eng_x2_point_u2_adapt", "Unit 2 适应与融入动词（adapt, adjust, integrate, participate）", 8, SUBJECT, G10, 165001),
    (165019, "eng_x2_point_u2_emotion", "Unit 2 心理与情绪形容词（homesick, overwhelmed, confident, independent）", 9, SUBJECT, G10, 165001),
    (165020, "eng_x2_point_u2_phrases", "Unit 2 跨文化适应短语（settle in, fit in, get used to, reach out to）", 10, SUBJECT, G10, 165001),
    (165021, "eng_x2_point_u3_cuisine", "Unit 3 饮食与烹饪名词（cuisine, ingredient, flavour, recipe）", 11, SUBJECT, G10, 165001),
    (165022, "eng_x2_point_u3_cook", "Unit 3 烹饪方式动词（boil, roast, fry, steam, season）", 12, SUBJECT, G10, 165001),
    (165023, "eng_x2_point_u3_taste", "Unit 3 味道与口感形容词（spicy, savoury, crispy, tender）", 13, SUBJECT, G10, 165001),
    (165024, "eng_x2_point_u3_regional", "Unit 3 地域饮食词块（regional speciality, staple food, food culture, eating habit）", 14, SUBJECT, G10, 165001),
    (165025, "eng_x2_point_u3_phrases", "Unit 3 饮食文化短语（be made of, be famous for, go with, take pride in）", 15, SUBJECT, G10, 165001),
    (165026, "eng_x2_point_u4_travel", "Unit 4 旅行与交通名词（journey, railway, route, scenery）", 16, SUBJECT, G10, 165001),
    (165027, "eng_x2_point_u4_canada", "Unit 4 加拿大地理词块（province, coast, prairie, wilderness）", 17, SUBJECT, G10, 165001),
    (165028, "eng_x2_point_u4_move", "Unit 4 旅途动身动词（depart, board, cross, wander, arrive）", 18, SUBJECT, G10, 165001),
    (165029, "eng_x2_point_u4_scenery", "Unit 4 景观与天气形容词（vast, remote, spectacular, freezing）", 19, SUBJECT, G10, 165001),
    (165030, "eng_x2_point_u4_phrases", "Unit 4 旅行经历短语（set off, on board, in the distance, be surrounded by）", 20, SUBJECT, G10, 165001),
    (165031, "eng_x2_point_u5_aid", "Unit 5 急救与伤情名词（first aid, injury, burn, wound, symptom）", 21, SUBJECT, G10, 165001),
    (165032, "eng_x2_point_u5_treat", "Unit 5 急救处理动词（bandage, apply, cool, cover, press）", 22, SUBJECT, G10, 165001),
    (165033, "eng_x2_point_u5_tissue", "Unit 5 人体部位与组织词块（skin, tissue, nerve, organ, layer）", 23, SUBJECT, G10, 165001),
    (165034, "eng_x2_point_u5_severity", "Unit 5 伤情描述形容词（swollen, blistered, infected, severe）", 24, SUBJECT, G10, 165001),
    (165035, "eng_x2_point_u5_phrases", "Unit 5 急救操作短语（give first aid, in case of, take action, call for help）", 25, SUBJECT, G10, 165001),

    # 表语从句
    (165036, "eng_x2_point_pred_define", "Unit 1 表语从句的句法位置与系动词后的名词性成分", 1, SUBJECT, G10, 165002),
    (165037, "eng_x2_point_pred_that", "Unit 1 表语从句 that 的引导与陈述语序", 2, SUBJECT, G10, 165002),
    (165038, "eng_x2_point_pred_whether", "Unit 1 表语从句 whether 与 if 的使用限制", 3, SUBJECT, G10, 165002),
    (165039, "eng_x2_point_pred_asif", "Unit 1 表语从句 as if/as though 与虚拟语气", 4, SUBJECT, G10, 165002),
    (165040, "eng_x2_point_pred_pron", "Unit 1 表语从句 what/who/which 连接代词作主语或表语", 5, SUBJECT, G10, 165002),
    (165041, "eng_x2_point_pred_adv", "Unit 1 表语从句 when/where/why/how 连接副词", 6, SUBJECT, G10, 165002),
    (165042, "eng_x2_point_pred_reason", "Unit 1 The reason is that... 与 because 的误用辨析", 7, SUBJECT, G10, 165002),
    (165043, "eng_x2_point_pred_conclusion", "Unit 1 表语从句在科学结论表述中的语序与语气", 8, SUBJECT, G10, 165002),

    # 宾语从句
    (165044, "eng_x2_point_obj_order", "Unit 2 宾语从句的陈述语序与疑问句转换", 1, SUBJECT, G10, 165003),
    (165045, "eng_x2_point_obj_that", "Unit 2 宾语从句 that 的省略条件", 2, SUBJECT, G10, 165003),
    (165046, "eng_x2_point_obj_whether", "Unit 2 宾语从句 whether/if 的选用与介词后限制", 3, SUBJECT, G10, 165003),
    (165047, "eng_x2_point_obj_what", "Unit 2 宾语从句 what/whatever 的语义差别", 4, SUBJECT, G10, 165003),
    (165048, "eng_x2_point_obj_sequence", "Unit 2 宾语从句的时态呼应与客观真理例外", 5, SUBJECT, G10, 165003),
    (165049, "eng_x2_point_obj_past", "Unit 2 主句过去时下宾语从句的时态调整", 6, SUBJECT, G10, 165003),
    (165050, "eng_x2_point_obj_it", "Unit 2 find it necessary that 等形式宾语句型", 7, SUBJECT, G10, 165003),
    (165051, "eng_x2_point_obj_letter", "Unit 2 申请信与转述中宾语从句的使用", 8, SUBJECT, G10, 165003),

    # 同位语从句
    (165052, "eng_x2_point_appo_define", "Unit 3 同位语从句对抽象名词的解释关系（fact, idea, news, belief）", 1, SUBJECT, G10, 165004),
    (165053, "eng_x2_point_appo_that", "Unit 3 同位语从句 that 的引导与不可省略", 2, SUBJECT, G10, 165004),
    (165054, "eng_x2_point_appo_vs_rel", "Unit 3 同位语从句与定语从句 that 的功能辨析", 3, SUBJECT, G10, 165004),
    (165055, "eng_x2_point_appo_whether", "Unit 3 同位语从句 whether 与 how/why 的用法", 4, SUBJECT, G10, 165004),
    (165056, "eng_x2_point_appo_separated", "Unit 3 同位语从句与中心名词被谓语分隔的现象", 5, SUBJECT, G10, 165004),
    (165057, "eng_x2_point_appo_nouns", "Unit 3 同位语从句常见名词搭配（the news that, the belief that）", 6, SUBJECT, G10, 165004),
    (165058, "eng_x2_point_appo_food", "Unit 3 同位语从句在饮食文化说明中的解释功能", 7, SUBJECT, G10, 165004),
    (165059, "eng_x2_point_appo_cohesion", "Unit 3 同位语从句与插入语的语篇衔接作用", 8, SUBJECT, G10, 165004),

    # 过去完成时
    (165060, "eng_x2_point_pastp_form", "Unit 4 过去完成时的构成 had done 及否定、疑问形式", 1, SUBJECT, G10, 165005),
    (165061, "eng_x2_point_pastp_reference", "Unit 4 过去完成时表达“过去的过去”的时间参照", 2, SUBJECT, G10, 165005),
    (165062, "eng_x2_point_pastp_order", "Unit 4 过去完成时与一般过去时在叙事中的先后关系", 3, SUBJECT, G10, 165005),
    (165063, "eng_x2_point_pastp_clause", "Unit 4 过去完成时在宾语从句中的时态呼应", 4, SUBJECT, G10, 165005),
    (165064, "eng_x2_point_pastp_time", "Unit 4 过去完成时与 when/before/after 引导的时间状语", 5, SUBJECT, G10, 165005),
    (165065, "eng_x2_point_pastp_cont", "Unit 4 过去完成进行时 had been doing 的持续含义", 6, SUBJECT, G10, 165005),
    (165066, "eng_x2_point_pastp_travel", "Unit 4 过去完成时在旅行叙事倒叙中的使用", 7, SUBJECT, G10, 165005),
    (165067, "eng_x2_point_pastp_vs_present", "Unit 4 过去完成时与现在完成时的视角差异", 8, SUBJECT, G10, 165005),

    # 时态复习与综合运用
    (165068, "eng_x2_point_tense_present", "Unit 5 一般现在时与现在进行时的语义分工", 1, SUBJECT, G10, 165006),
    (165069, "eng_x2_point_tense_past", "Unit 5 一般过去时与现在完成时的界限", 2, SUBJECT, G10, 165006),
    (165070, "eng_x2_point_tense_continuous", "Unit 5 过去进行时与过去完成进行时的对比", 3, SUBJECT, G10, 165006),
    (165071, "eng_x2_point_tense_future", "Unit 5 将来表达：will、be going to 与现在进行时", 4, SUBJECT, G10, 165006),
    (165072, "eng_x2_point_tense_clause", "Unit 5 时间状语从句与条件句中的时态呼应", 5, SUBJECT, G10, 165006),
    (165073, "eng_x2_point_tense_instruction", "Unit 5 急救说明文中的祈使句与一般现在时", 6, SUBJECT, G10, 165006),
    (165074, "eng_x2_point_tense_chain", "Unit 5 语篇中时态链的一致性与切换", 7, SUBJECT, G10, 165006),

    # 阅读策略与语篇分析
    (165075, "eng_x2_point_read_argument", "Unit 1 科学论证语篇“问题—假设—证据—结论”结构", 1, SUBJECT, G10, 165007),
    (165076, "eng_x2_point_read_fact", "Unit 1 阅读中区分事实、推论与作者评价", 2, SUBJECT, G10, 165007),
    (165077, "eng_x2_point_read_narrative", "Unit 2 留学生叙事语篇的情节线与情感变化", 3, SUBJECT, G10, 165007),
    (165078, "eng_x2_point_read_conflict", "Unit 2 阅读中识别跨文化冲突与解决策略", 4, SUBJECT, G10, 165007),
    (165079, "eng_x2_point_read_cuisine", "Unit 3 饮食文化说明文的举例与对比结构", 5, SUBJECT, G10, 165007),
    (165080, "eng_x2_point_read_journey", "Unit 4 旅行游记的空间移动与时间线索", 6, SUBJECT, G10, 165007),
    (165081, "eng_x2_point_read_map", "Unit 4 借助地图与路线信息定位文本细节", 7, SUBJECT, G10, 165007),
    (165082, "eng_x2_point_read_instruction", "Unit 5 急救说明文的步骤顺序与条件警示解读", 8, SUBJECT, G10, 165007),

    # 写作体裁与过程
    (165083, "eng_x2_point_write_report", "Unit 1 实验报告：目的、方法、结果、结论四段结构", 1, SUBJECT, G10, 165008),
    (165084, "eng_x2_point_write_passive", "Unit 1 实验报告中被动语态与数据的客观表述", 2, SUBJECT, G10, 165008),
    (165085, "eng_x2_point_write_apply", "Unit 2 申请信：自我介绍、申请理由与结尾期待", 3, SUBJECT, G10, 165008),
    (165086, "eng_x2_point_write_register", "Unit 2 申请信正式语气与礼貌句型的选用", 4, SUBJECT, G10, 165008),
    (165087, "eng_x2_point_write_dish", "Unit 3 菜品描写：食材、做法、味道与情感的层次", 5, SUBJECT, G10, 165008),
    (165088, "eng_x2_point_write_sensory", "Unit 3 菜品描写中感官形容词与连接词的使用", 6, SUBJECT, G10, 165008),
    (165089, "eng_x2_point_write_journal", "Unit 4 旅行日志：日期、地点、见闻与感受的组织", 7, SUBJECT, G10, 165008),
    (165090, "eng_x2_point_write_firstaid", "Unit 5 急救说明：标题、步骤编号与警示语写作", 8, SUBJECT, G10, 165008),

    # 听力、语音与口语策略
    (165091, "eng_x2_point_listen_interview", "Unit 1 科学发现访谈听力的关键信息与数字速记", 1, SUBJECT, G10, 165009),
    (165092, "eng_x2_point_listen_abroad", "Unit 2 留学话题听力的态度与建议辨识", 2, SUBJECT, G10, 165009),
    (165093, "eng_x2_point_listen_route", "Unit 4 旅行路线描述听力的方向与地点定位", 3, SUBJECT, G10, 165009),
    (165094, "eng_x2_point_phonetic", "本册语音：连读、弱读与句子重音的辨听", 4, SUBJECT, G10, 165009),
    (165095, "eng_x2_point_speak_aid", "Unit 5 急救情境口语：描述伤情与请求帮助的功能句型", 5, SUBJECT, G10, 165009),

    # 文化意识与主题探究
    (165096, "eng_x2_point_culture_science", "Unit 1 中外科学家精神与科学伦理的文化解读", 1, SUBJECT, G10, 165010),
    (165097, "eng_x2_point_culture_identity", "Unit 2 留学潮与跨文化身份认同的探讨", 2, SUBJECT, G10, 165010),
    (165098, "eng_x2_point_culture_cuisine", "Unit 3 中国饮食文化的地域差异与对外传播", 3, SUBJECT, G10, 165010),
    (165099, "eng_x2_culture_safety", "Unit 5 急救常识普及与公共安全意识的跨文化比较", 4, SUBJECT, G10, 165010),
)

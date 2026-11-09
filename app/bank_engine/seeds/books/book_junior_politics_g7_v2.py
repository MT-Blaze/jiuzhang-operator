"""统编版（2016）初中道德与法治七年级下册：单元课题目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G7 = 7
BOOK_ID = 1314

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版七年级道德与法治下册",
    "jpol_g7b",
    14,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 青春时光
    (131401, "第一单元 青春时光", "jpol_g7b_u01", 1, BOOK_ID, None),
    (131411, "第一课 青春的邀约", "jpol_g7b_l01", 1, BOOK_ID, 131401),
    (131412, "第二课 青春的心弦", "jpol_g7b_l02", 2, BOOK_ID, 131401),
    (131413, "第三课 青春的证明", "jpol_g7b_l03", 3, BOOK_ID, 131401),

    # 第二单元 做情绪情感的主人
    (131402, "第二单元 做情绪情感的主人", "jpol_g7b_u02", 2, BOOK_ID, None),
    (131414, "第四课 揭开情绪的面纱", "jpol_g7b_l04", 1, BOOK_ID, 131402),
    (131415, "第五课 品出情感的韵味", "jpol_g7b_l05", 2, BOOK_ID, 131402),

    # 第三单元 在集体中成长
    (131403, "第三单元 在集体中成长", "jpol_g7b_u03", 3, BOOK_ID, None),
    (131416, "第六课 “我”和“我们”", "jpol_g7b_l06", 1, BOOK_ID, 131403),
    (131417, "第七课 共奏和谐乐章", "jpol_g7b_l07", 2, BOOK_ID, 131403),
    (131418, "第八课 美好集体有我在", "jpol_g7b_l08", 3, BOOK_ID, 131403),

    # 第四单元 走进法治天地
    (131404, "第四单元 走进法治天地", "jpol_g7b_u04", 4, BOOK_ID, None),
    (131419, "第九课 法律在我们身边", "jpol_g7b_l09", 1, BOOK_ID, 131404),
    (131420, "第十课 法律伴我们成长", "jpol_g7b_l10", 2, BOOK_ID, 131404),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 214001-214016 为册域层，214017-214082 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (214001, "jpol_g7b_domain_body", "初中七下·青春期身体变化与自我悦纳", 1, SUBJECT, G7, None),
    (214002, "jpol_g7b_domain_mind", "初中七下·青春期心理矛盾与思维发展", 2, SUBJECT, G7, None),
    (214003, "jpol_g7b_domain_gender", "初中七下·男生女生的差异与优势互补", 3, SUBJECT, G7, None),
    (214004, "jpol_g7b_domain_hetero", "初中七下·异性交往与青春萌动", 4, SUBJECT, G7, None),
    (214005, "jpol_g7b_domain_confidence", "初中七下·青春飞扬与自信自强", 5, SUBJECT, G7, None),
    (214006, "jpol_g7b_domain_shame", "初中七下·行己有耻与止于至善", 6, SUBJECT, G7, None),
    (214007, "jpol_g7b_domain_emotion", "初中七下·情绪的类型与青春情绪特点", 7, SUBJECT, G7, None),
    (214008, "jpol_g7b_domain_emotion_manage", "初中七下·情绪管理与情绪调节方法", 8, SUBJECT, G7, None),
    (214009, "jpol_g7b_domain_feeling", "初中七下·情感的种类与情感作用", 9, SUBJECT, G7, None),
    (214010, "jpol_g7b_domain_feeling_beauty", "初中七下·美好情感的体验与传递", 10, SUBJECT, G7, None),
    (214011, "jpol_g7b_domain_collective", "初中七下·集体生活的力量与个人成长", 11, SUBJECT, G7, None),
    (214012, "jpol_g7b_domain_rule", "初中七下·个人意愿与集体规则", 12, SUBJECT, G7, None),
    (214013, "jpol_g7b_domain_small_group", "初中七下·小群体与集体和谐", 13, SUBJECT, G7, None),
    (214014, "jpol_g7b_domain_good_collective", "初中七下·美好集体的特征与共建", 14, SUBJECT, G7, None),
    (214015, "jpol_g7b_domain_law", "初中七下·法律的特征与法治意义", 15, SUBJECT, G7, None),
    (214016, "jpol_g7b_domain_minor", "初中七下·未成年人特殊保护与依法办事", 16, SUBJECT, G7, None),

    # 青春期身体变化与自我悦纳
    (214017, "jpol_g7b_point_body_change", "青春期身体外形、内部器官与性机能的成熟", 1, SUBJECT, G7, 214001),
    (214018, "jpol_g7b_point_body_confuse", "青春期生理变化带来的困惑与正确态度", 2, SUBJECT, G7, 214001),
    (214019, "jpol_g7b_point_body_accept", "悦纳生理变化与外在美、内在美的统一", 3, SUBJECT, G7, 214001),
    (214020, "jpol_g7b_point_body_health", "青春期卫生保健与健康生活方式养成", 4, SUBJECT, G7, 214001),

    # 青春期心理矛盾与思维发展
    (214021, "jpol_g7b_point_mind_conflict", "青春期独立与依赖、闭锁与开放等心理矛盾", 1, SUBJECT, G7, 214002),
    (214022, "jpol_g7b_point_mind_solve", "调控青春期心理矛盾的常用方法", 2, SUBJECT, G7, 214002),
    (214023, "jpol_g7b_point_mind_think", "青春期思维的独立性、批判性与创造性", 3, SUBJECT, G7, 214002),
    (214024, "jpol_g7b_point_mind_create", "培养批判性思维与开发创造潜力", 4, SUBJECT, G7, 214002),

    # 男生女生的差异与优势互补
    (214025, "jpol_g7b_point_gender_diff", "男生女生在生理特征与心理特征上的差异", 1, SUBJECT, G7, 214003),
    (214026, "jpol_g7b_point_gender_stereotype", "正确认识性别刻板印象", 2, SUBJECT, G7, 214003),
    (214027, "jpol_g7b_point_gender_complement", "男生女生优势互补与相互欣赏", 3, SUBJECT, G7, 214003),
    (214028, "jpol_g7b_point_gender_meaning", "与异性正常交往对个人成长的积极意义", 4, SUBJECT, G7, 214003),

    # 异性交往与青春萌动
    (214029, "jpol_g7b_point_hetero_rule", "青春期异性交往的原则与尺度", 1, SUBJECT, G7, 214004),
    (214030, "jpol_g7b_point_hetero_feel", "正确对待青春期的朦胧情感与好感", 2, SUBJECT, G7, 214004),
    (214031, "jpol_g7b_point_hetero_boundary", "异性交往中的边界意识与自我保护", 3, SUBJECT, G7, 214004),
    (214032, "jpol_g7b_point_hetero_friend", "建立健康异性友谊、避免早恋误区", 4, SUBJECT, G7, 214004),

    # 青春飞扬与自信自强
    (214033, "jpol_g7b_point_youth_vitality", "青春的渴望、活力与飞扬姿态", 1, SUBJECT, G7, 214005),
    (214034, "jpol_g7b_point_youth_confidence", "自信的作用与增强自信的方法", 2, SUBJECT, G7, 214005),
    (214035, "jpol_g7b_point_youth_selfstrong", "自强精神的内涵与主要表现", 3, SUBJECT, G7, 214005),
    (214036, "jpol_g7b_point_youth_will", "磨砺意志、战胜自我与自强不息", 4, SUBJECT, G7, 214005),

    # 行己有耻与止于至善
    (214037, "jpol_g7b_point_shame_define", "“行己有耻”的含义与底线意识", 1, SUBJECT, G7, 214006),
    (214038, "jpol_g7b_point_shame_rule", "遵守道德与法律、做到有所不为", 2, SUBJECT, G7, 214006),
    (214039, "jpol_g7b_point_perfect_define", "“止于至善”的精神追求与境界", 3, SUBJECT, G7, 214006),
    (214040, "jpol_g7b_point_perfect_way", "榜样示范、自我省察与慎独修身", 4, SUBJECT, G7, 214006),

    # 情绪的类型与青春情绪特点
    (214041, "jpol_g7b_point_emotion_type", "情绪的基本类型与复合情绪", 1, SUBJECT, G7, 214007),
    (214042, "jpol_g7b_point_emotion_element", "情绪的成分与影响情绪的主要因素", 2, SUBJECT, G7, 214007),
    (214043, "jpol_g7b_point_emotion_youth", "青春期情绪的特点", 3, SUBJECT, G7, 214007),
    (214044, "jpol_g7b_point_emotion_effect", "情绪对身心健康和行为的影响", 4, SUBJECT, G7, 214007),

    # 情绪管理与情绪调节方法
    (214045, "jpol_g7b_point_emotion_goal", "情绪管理的目标与必要性", 1, SUBJECT, G7, 214008),
    (214046, "jpol_g7b_point_emotion_cognition", "改变认知评价与转移注意的调节方法", 2, SUBJECT, G7, 214008),
    (214047, "jpol_g7b_point_emotion_release", "合理宣泄、放松训练与恰当表达情绪", 3, SUBJECT, G7, 214008),
    (214048, "jpol_g7b_point_emotion_care", "关心他人情绪与传递情绪正能量", 4, SUBJECT, G7, 214008),

    # 情感的种类与情感作用
    (214049, "jpol_g7b_point_feeling_diff", "情感与情绪的区别和联系", 1, SUBJECT, G7, 214009),
    (214050, "jpol_g7b_point_feeling_type", "情感的丰富类型与层级", 2, SUBJECT, G7, 214009),
    (214051, "jpol_g7b_point_feeling_role", "情感对个人成长与发展的作用", 3, SUBJECT, G7, 214009),
    (214052, "jpol_g7b_point_feeling_negative", "负面情感的正面意义与合理转化", 4, SUBJECT, G7, 214009),

    # 美好情感的体验与传递
    (214053, "jpol_g7b_point_beauty_experience", "体味美好情感与创造正面情感体验", 1, SUBJECT, G7, 214010),
    (214054, "jpol_g7b_point_beauty_way", "通过阅读、艺术和自然获得美好情感", 2, SUBJECT, G7, 214010),
    (214055, "jpol_g7b_point_beauty_pass", "传递情感正能量与形成情感共鸣", 3, SUBJECT, G7, 214010),
    (214056, "jpol_g7b_point_beauty_care", "学会关心他人、在挫折中丰富情感", 4, SUBJECT, G7, 214010),

    # 集体生活的力量与个人成长
    (214057, "jpol_g7b_point_collective_define", "集体的含义与集体联结度", 1, SUBJECT, G7, 214011),
    (214058, "jpol_g7b_point_collective_warm", "集体生活带来的温暖与归属感", 2, SUBJECT, G7, 214011),
    (214059, "jpol_g7b_point_collective_power", "集体力量的来源与团结协作", 3, SUBJECT, G7, 214011),
    (214060, "jpol_g7b_point_collective_grow", "集体生活涵养品格、发展个性", 4, SUBJECT, G7, 214011),

    # 个人意愿与集体规则
    (214061, "jpol_g7b_point_rule_role", "集体规则的作用与自觉遵守规则", 1, SUBJECT, G7, 214012),
    (214062, "jpol_g7b_point_rule_conflict", "个人意愿与集体规则冲突的原因", 2, SUBJECT, G7, 214012),
    (214063, "jpol_g7b_point_rule_interest", "个人利益与集体利益的正确处理", 3, SUBJECT, G7, 214012),
    (214064, "jpol_g7b_point_rule_collectivism", "集体主义原则与正当个人利益的维护", 4, SUBJECT, G7, 214012),

    # 小群体与集体和谐
    (214065, "jpol_g7b_point_small_group_form", "小群体的形成与双重影响", 1, SUBJECT, G7, 214013),
    (214066, "jpol_g7b_point_small_group_relation", "小群体与集体的关系及正确引导", 2, SUBJECT, G7, 214013),
    (214067, "jpol_g7b_point_small_group_role", "集体中的角色冲突与协调", 3, SUBJECT, G7, 214013),
    (214068, "jpol_g7b_point_small_group_sect", "反对小团体主义与江湖义气", 4, SUBJECT, G7, 214013),

    # 美好集体的特征与共建
    (214069, "jpol_g7b_point_good_vision", "美好集体的愿景与共同目标", 1, SUBJECT, G7, 214014),
    (214070, "jpol_g7b_point_good_fair", "美好集体的民主、公正与包容", 2, SUBJECT, G7, 214014),
    (214071, "jpol_g7b_point_good_cooperate", "美好集体的关怀友爱与合作氛围", 3, SUBJECT, G7, 214014),
    (214072, "jpol_g7b_point_good_build", "在集体共建中尽责与担当成长", 4, SUBJECT, G7, 214014),

    # 法律的特征与法治意义
    (214073, "jpol_g7b_point_law_life", "法律与生活的关系及法律的产生", 1, SUBJECT, G7, 214015),
    (214074, "jpol_g7b_point_law_feature", "法律的三个基本特征", 2, SUBJECT, G7, 214015),
    (214075, "jpol_g7b_point_law_diff", "法律与道德、纪律的区别", 3, SUBJECT, G7, 214015),
    (214076, "jpol_g7b_point_law_role", "法律的规范作用与保护作用", 4, SUBJECT, G7, 214015),
    (214077, "jpol_g7b_point_law_rule", "法治的含义与全面依法治国", 5, SUBJECT, G7, 214015),

    # 未成年人特殊保护与依法办事
    (214078, "jpol_g7b_point_minor_reason", "未成年人需要特殊保护的原因", 1, SUBJECT, G7, 214016),
    (214079, "jpol_g7b_point_minor_family", "家庭保护、学校保护与社会保护", 2, SUBJECT, G7, 214016),
    (214080, "jpol_g7b_point_minor_net", "网络保护、政府保护与司法保护", 3, SUBJECT, G7, 214016),
    (214081, "jpol_g7b_point_minor_right", "依法办事与依法维护自身合法权益", 4, SUBJECT, G7, 214016),
    (214082, "jpol_g7b_point_minor_aware", "树立法治意识、做尊法学法守法用法公民", 5, SUBJECT, G7, 214016),
)

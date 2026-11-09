"""统编版初中道德与法治八年级上册：单元课题目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G8 = 8
BOOK_ID = 1315

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版八年级道德与法治上册",
    "jpol_g8a",
    15,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 走进社会生活
    (131501, "第一单元 走进社会生活", "jpol_g8a_u01", 1, BOOK_ID, None),
    (131511, "第一课 丰富的社会生活", "jpol_g8a_l01", 1, BOOK_ID, 131501),
    (131512, "第二课 网络生活新空间", "jpol_g8a_l02", 2, BOOK_ID, 131501),

    # 第二单元 遵守社会规则
    (131502, "第二单元 遵守社会规则", "jpol_g8a_u02", 2, BOOK_ID, None),
    (131513, "第三课 社会生活离不开规则", "jpol_g8a_l03", 1, BOOK_ID, 131502),
    (131514, "第四课 社会生活讲道德", "jpol_g8a_l04", 2, BOOK_ID, 131502),
    (131515, "第五课 做守法的公民", "jpol_g8a_l05", 3, BOOK_ID, 131502),

    # 第三单元 勇担社会责任
    (131503, "第三单元 勇担社会责任", "jpol_g8a_u03", 3, BOOK_ID, None),
    (131516, "第六课 责任与角色同在", "jpol_g8a_l06", 1, BOOK_ID, 131503),
    (131517, "第七课 积极奉献社会", "jpol_g8a_l07", 2, BOOK_ID, 131503),

    # 第四单元 维护国家利益
    (131504, "第四单元 维护国家利益", "jpol_g8a_u04", 4, BOOK_ID, None),
    (131518, "第八课 国家利益至上", "jpol_g8a_l08", 1, BOOK_ID, 131504),
    (131519, "第九课 树立总体国家安全观", "jpol_g8a_l09", 2, BOOK_ID, 131504),
    (131520, "第十课 建设美好祖国", "jpol_g8a_l10", 3, BOOK_ID, 131504),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 215001-215016 为册域层，215017-215084 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (215001, "jpol_g8a_domain_society", "初中八上·个人与社会的关系", 1, SUBJECT, G8, None),
    (215002, "jpol_g8a_domain_prosocial", "初中八上·亲社会行为与社会课堂", 2, SUBJECT, G8, None),
    (215003, "jpol_g8a_domain_net_change", "初中八上·网络改变世界", 3, SUBJECT, G8, None),
    (215004, "jpol_g8a_domain_net_life", "初中八上·理性参与网络生活", 4, SUBJECT, G8, None),
    (215005, "jpol_g8a_domain_order", "初中八上·社会秩序与社会规则", 5, SUBJECT, G8, None),
    (215006, "jpol_g8a_domain_rule_aware", "初中八上·遵守规则与规则意识", 6, SUBJECT, G8, None),
    (215007, "jpol_g8a_domain_morality", "初中八上·社会生活讲道德", 7, SUBJECT, G8, None),
    (215008, "jpol_g8a_domain_illegal", "初中八上·违法行为与法律责任", 8, SUBJECT, G8, None),
    (215009, "jpol_g8a_domain_crime", "初中八上·犯罪与刑罚", 9, SUBJECT, G8, None),
    (215010, "jpol_g8a_domain_law_use", "初中八上·善用法律与依法维权", 10, SUBJECT, G8, None),
    (215011, "jpol_g8a_domain_duty", "初中八上·责任与角色同在", 11, SUBJECT, G8, None),
    (215012, "jpol_g8a_domain_devotion", "初中八上·积极奉献社会", 12, SUBJECT, G8, None),
    (215013, "jpol_g8a_domain_interest", "初中八上·国家利益至上", 13, SUBJECT, G8, None),
    (215014, "jpol_g8a_domain_security", "初中八上·总体国家安全观", 14, SUBJECT, G8, None),
    (215015, "jpol_g8a_domain_security_duty", "初中八上·维护国家安全的义务与行动", 15, SUBJECT, G8, None),
    (215016, "jpol_g8a_domain_motherland", "初中八上·建设美好祖国", 16, SUBJECT, G8, None),

    # 个人与社会的关系
    (215017, "jpol_g8a_point_society_mutual", "个人与社会相互依存、相互制约", 1, SUBJECT, G8, 215001),
    (215018, "jpol_g8a_point_society_relation", "血缘关系、地缘关系与业缘关系", 2, SUBJECT, G8, 215001),
    (215019, "jpol_g8a_point_society_role", "个人身份与社会角色的确定", 3, SUBJECT, G8, 215001),
    (215020, "jpol_g8a_point_society_support", "社会为个人成长提供物质支持和精神滋养", 4, SUBJECT, G8, 215001),
    (215021, "jpol_g8a_point_society_socialize", "人的成长是不断社会化的过程", 5, SUBJECT, G8, 215001),

    # 亲社会行为与社会课堂
    (215022, "jpol_g8a_point_prosocial_show", "亲社会行为的主要表现", 1, SUBJECT, G8, 215002),
    (215023, "jpol_g8a_point_prosocial_way", "亲社会行为的养成途径", 2, SUBJECT, G8, 215002),
    (215024, "jpol_g8a_point_prosocial_value", "亲社会行为对个人成长与社会发展的意义", 3, SUBJECT, G8, 215002),
    (215025, "jpol_g8a_point_prosocial_practice", "在社会实践中培养亲社会行为", 4, SUBJECT, G8, 215002),

    # 网络改变世界
    (215026, "jpol_g8a_point_net_life", "网络丰富日常生活：信息传递与生活便利", 1, SUBJECT, G8, 215003),
    (215027, "jpol_g8a_point_net_progress", "网络推动经济、政治、文化领域进步", 2, SUBJECT, G8, 215003),
    (215028, "jpol_g8a_point_net_negative", "沉迷网络与信息良莠不齐的消极影响", 3, SUBJECT, G8, 215003),
    (215029, "jpol_g8a_point_net_feature", "网络交往的虚拟性、平等性与自主性", 4, SUBJECT, G8, 215003),

    # 理性参与网络生活
    (215030, "jpol_g8a_point_net_literacy", "提高媒介素养、合理利用网络", 1, SUBJECT, G8, 215004),
    (215031, "jpol_g8a_point_net_diet", "学会“信息节食”、避免沉迷网络", 2, SUBJECT, G8, 215004),
    (215032, "jpol_g8a_point_net_rumor", "辨析网络信息、抵制网络谣言", 3, SUBJECT, G8, 215004),
    (215033, "jpol_g8a_point_net_privacy", "保护个人隐私、防范网络诈骗", 4, SUBJECT, G8, 215004),
    (215034, "jpol_g8a_point_net_positive", "遵守网络道德与法律、传播网络正能量", 5, SUBJECT, G8, 215004),

    # 社会秩序与社会规则
    (215035, "jpol_g8a_point_order_define", "社会秩序的含义与社会生活秩序的分类", 1, SUBJECT, G8, 215005),
    (215036, "jpol_g8a_point_order_role", "社会秩序对社会正常运行的作用", 2, SUBJECT, G8, 215005),
    (215037, "jpol_g8a_point_rule_type", "社会规则的含义与道德、纪律、法律等类型", 3, SUBJECT, G8, 215005),
    (215038, "jpol_g8a_point_rule_order", "社会规则与社会秩序的关系", 4, SUBJECT, G8, 215005),

    # 遵守规则与规则意识
    (215039, "jpol_g8a_point_rule_freedom", "自由与规则不可分", 1, SUBJECT, G8, 215006),
    (215040, "jpol_g8a_point_rule_obey", "自觉遵守规则：他律与自律", 2, SUBJECT, G8, 215006),
    (215041, "jpol_g8a_point_rule_improve", "维护规则与积极改进规则", 3, SUBJECT, G8, 215006),
    (215042, "jpol_g8a_point_rule_awe", "规则意识与敬畏规则", 4, SUBJECT, G8, 215006),

    # 社会生活讲道德
    (215043, "jpol_g8a_point_respect_define", "尊重他人的含义与具体表现", 1, SUBJECT, G8, 215007),
    (215044, "jpol_g8a_point_respect_reason", "尊重他人的原因与基本要求", 2, SUBJECT, G8, 215007),
    (215045, "jpol_g8a_point_polite", "文明有礼的意义与基本要求", 3, SUBJECT, G8, 215007),
    (215046, "jpol_g8a_point_honest_value", "诚实守信的意义与践行要求", 4, SUBJECT, G8, 215007),
    (215047, "jpol_g8a_point_honest_wisdom", "树立诚信意识与运用诚信智慧", 5, SUBJECT, G8, 215007),

    # 违法行为与法律责任
    (215048, "jpol_g8a_point_illegal_type", "违法行为的含义与民事、行政、刑事违法分类", 1, SUBJECT, G8, 215008),
    (215049, "jpol_g8a_point_illegal_diff", "一般违法行为与犯罪的区别和联系", 2, SUBJECT, G8, 215008),
    (215050, "jpol_g8a_point_illegal_duty", "民事责任、行政责任与刑事责任的承担", 3, SUBJECT, G8, 215008),
    (215051, "jpol_g8a_point_illegal_bad", "不良行为与严重不良行为的辨别", 4, SUBJECT, G8, 215008),

    # 犯罪与刑罚
    (215052, "jpol_g8a_point_crime_feature", "犯罪的三个基本特征", 1, SUBJECT, G8, 215009),
    (215053, "jpol_g8a_point_crime_punish", "刑罚的种类：主刑与附加刑", 2, SUBJECT, G8, 215009),
    (215054, "jpol_g8a_point_crime_reason", "未成年人犯罪的原因与自我防范", 3, SUBJECT, G8, 215009),
    (215055, "jpol_g8a_point_crime_prevent", "杜绝不良行为、防患于未然", 4, SUBJECT, G8, 215009),

    # 善用法律与依法维权
    (215056, "jpol_g8a_point_law_help", "遇到侵害时依法求助的途径", 1, SUBJECT, G8, 215010),
    (215057, "jpol_g8a_point_law_litigation", "民事诉讼、行政诉讼与刑事诉讼", 2, SUBJECT, G8, 215010),
    (215058, "jpol_g8a_point_law_brave", "有勇有谋应对违法犯罪", 3, SUBJECT, G8, 215010),
    (215059, "jpol_g8a_point_law_minor", "依法维护未成年人合法权益", 4, SUBJECT, G8, 215010),
    (215060, "jpol_g8a_point_law_aware", "树立法治意识、做守法公民", 5, SUBJECT, G8, 215010),

    # 责任与角色同在
    (215061, "jpol_g8a_point_duty_define", "责任的含义与责任来源", 1, SUBJECT, G8, 215011),
    (215062, "jpol_g8a_point_duty_role", "责任与角色的对应关系", 2, SUBJECT, G8, 215011),
    (215063, "jpol_g8a_point_duty_cost", "承担责任的代价与回报", 3, SUBJECT, G8, 215011),
    (215064, "jpol_g8a_point_duty_responsible", "做负责任的人：不言代价与回报", 4, SUBJECT, G8, 215011),

    # 积极奉献社会
    (215065, "jpol_g8a_point_care_meaning", "关爱他人的意义", 1, SUBJECT, G8, 215012),
    (215066, "jpol_g8a_point_care_way", "关爱他人的要求与艺术", 2, SUBJECT, G8, 215012),
    (215067, "jpol_g8a_point_serve_value", "服务社会、奉献社会的意义", 3, SUBJECT, G8, 215012),
    (215068, "jpol_g8a_point_serve_action", "参加社会公益活动与志愿服务", 4, SUBJECT, G8, 215012),

    # 国家利益至上
    (215069, "jpol_g8a_point_interest_define", "国家利益的含义与主要内容", 1, SUBJECT, G8, 215013),
    (215070, "jpol_g8a_point_interest_core", "国家核心利益的内涵", 2, SUBJECT, G8, 215013),
    (215071, "jpol_g8a_point_interest_person", "国家利益与个人利益的关系", 3, SUBJECT, G8, 215013),
    (215072, "jpol_g8a_point_interest_uphold", "坚持国家利益至上的要求", 4, SUBJECT, G8, 215013),

    # 总体国家安全观
    (215073, "jpol_g8a_point_security_define", "国家安全的内涵与重要性", 1, SUBJECT, G8, 215014),
    (215074, "jpol_g8a_point_security_view", "总体国家安全观的内容", 2, SUBJECT, G8, 215014),
    (215075, "jpol_g8a_point_security_field", "传统安全与非传统安全领域", 3, SUBJECT, G8, 215014),
    (215076, "jpol_g8a_point_security_people", "国家安全与人民幸福的关系", 4, SUBJECT, G8, 215014),

    # 维护国家安全的义务与行动
    (215077, "jpol_g8a_point_security_duty", "维护国家安全是公民的基本义务", 1, SUBJECT, G8, 215015),
    (215078, "jpol_g8a_point_security_law", "履行维护国家安全的法律义务", 2, SUBJECT, G8, 215015),
    (215079, "jpol_g8a_point_security_risk", "识别和抵制危害国家安全的行为", 3, SUBJECT, G8, 215015),
    (215080, "jpol_g8a_point_security_teen", "青少年维护国家安全的实际行动", 4, SUBJECT, G8, 215015),

    # 建设美好祖国
    (215081, "jpol_g8a_point_mother_achievement", "关心国家发展、感受国家建设成就", 1, SUBJECT, G8, 215016),
    (215082, "jpol_g8a_point_mother_problem", "正视国家发展中的问题与挑战", 2, SUBJECT, G8, 215016),
    (215083, "jpol_g8a_point_mother_labor", "劳动创造价值、实干成就梦想", 3, SUBJECT, G8, 215016),
    (215084, "jpol_g8a_point_mother_teen", "青少年为国家发展贡献力量", 4, SUBJECT, G8, 215016),
)

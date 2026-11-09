"""统编版初中道德与法治八年级下册：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G8 = 8
BOOK_ID = 1316

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版八年级道德与法治下册",
    "jpol_g8b",
    16,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 坚持宪法至上
    (131601, "第一单元 坚持宪法至上", "jpol_g8b_u01", 1, BOOK_ID, None),
    (131611, "第一课 维护宪法权威", "jpol_g8b_l01", 1, BOOK_ID, 131601),
    (131612, "第二课 保障宪法实施", "jpol_g8b_l02", 2, BOOK_ID, 131601),

    # 第二单元 理解权利义务
    (131602, "第二单元 理解权利义务", "jpol_g8b_u02", 2, BOOK_ID, None),
    (131613, "第三课 公民权利", "jpol_g8b_l03", 1, BOOK_ID, 131602),
    (131614, "第四课 公民义务", "jpol_g8b_l04", 2, BOOK_ID, 131602),

    # 第三单元 人民当家作主
    (131603, "第三单元 人民当家作主", "jpol_g8b_u03", 3, BOOK_ID, None),
    (131615, "第五课 我国的政治和经济制度", "jpol_g8b_l05", 1, BOOK_ID, 131603),
    (131616, "第六课 我国国家机构", "jpol_g8b_l06", 2, BOOK_ID, 131603),

    # 第四单元 崇尚法治精神
    (131604, "第四单元 崇尚法治精神", "jpol_g8b_u04", 4, BOOK_ID, None),
    (131617, "第七课 尊重自由平等", "jpol_g8b_l07", 1, BOOK_ID, 131604),
    (131618, "第八课 维护公平正义", "jpol_g8b_l08", 2, BOOK_ID, 131604),
)

# id / code / name / sort_order / subject_id / parent_id
# 216001-216008 为册域层，216009-216077 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (216001, "jpol_g8b_domain_constitution_power", "初中八下·宪法权威与治国安邦总章程", 1, SUBJECT, None),
    (216002, "jpol_g8b_domain_constitution_rule", "初中八下·依宪治国与宪法监督实施", 2, SUBJECT, None),
    (216003, "jpol_g8b_domain_rights", "初中八下·公民基本权利与依法行使", 3, SUBJECT, None),
    (216004, "jpol_g8b_domain_duties", "初中八下·公民基本义务与依法履行", 4, SUBJECT, None),
    (216005, "jpol_g8b_domain_systems", "初中八下·我国政治制度与经济制度", 5, SUBJECT, None),
    (216006, "jpol_g8b_domain_organs", "初中八下·我国国家机构与职权", 6, SUBJECT, None),
    (216007, "jpol_g8b_domain_freedom_equality", "初中八下·自由平等的真谛与追求", 7, SUBJECT, None),
    (216008, "jpol_g8b_domain_fairness_justice", "初中八下·公平正义的价值与守护", 8, SUBJECT, None),

    # 宪法权威与治国安邦总章程
    (216009, "jpol_g8b_point_const_essence", "宪法的本质：党的主张和人民意志的统一", 1, SUBJECT, 216001),
    (216010, "jpol_g8b_point_const_charter", "宪法是治国安邦的总章程", 2, SUBJECT, 216001),
    (216011, "jpol_g8b_point_const_nature", "宪法确认我国的国家性质与根本制度", 3, SUBJECT, 216001),
    (216012, "jpol_g8b_point_const_org_principle", "宪法确立国家机构的民主集中制原则", 4, SUBJECT, 216001),
    (216013, "jpol_g8b_point_const_limit_power", "宪法规范国家权力运行以保障公民权利", 5, SUBJECT, 216001),
    (216014, "jpol_g8b_point_const_supreme", "宪法作为根本法的最高法律地位与法律效力", 6, SUBJECT, 216001),
    (216015, "jpol_g8b_point_const_oath", "维护宪法权威与宪法宣誓制度", 7, SUBJECT, 216001),

    # 依宪治国与宪法监督实施
    (216016, "jpol_g8b_point_rule_law_core", "依法治国的核心是依宪治国", 1, SUBJECT, 216002),
    (216017, "jpol_g8b_point_const_guideline", "宪法是一切组织和个人的根本活动准则", 2, SUBJECT, 216002),
    (216018, "jpol_g8b_point_const_effect", "宪法具有最高法律地位、法律权威和法律效力", 3, SUBJECT, 216002),
    (216019, "jpol_g8b_point_const_procedure", "宪法与其他法律的制定和修改程序差异", 4, SUBJECT, 216002),
    (216020, "jpol_g8b_point_const_review", "合宪性审查与法规备案审查制度", 5, SUBJECT, 216002),
    (216021, "jpol_g8b_point_const_supervise", "全国人大及其常委会行使宪法监督职权", 6, SUBJECT, 216002),
    (216022, "jpol_g8b_point_const_awareness", "增强宪法意识、维护宪法尊严", 7, SUBJECT, 216002),

    # 公民基本权利与依法行使
    (216023, "jpol_g8b_point_right_citizen", "公民与人民的区别及公民权利的含义", 1, SUBJECT, 216003),
    (216024, "jpol_g8b_point_right_vote", "选举权和被选举权的条件与意义", 2, SUBJECT, 216003),
    (216025, "jpol_g8b_point_right_political_free", "言论、出版、集会、结社、游行、示威的政治自由", 3, SUBJECT, 216003),
    (216026, "jpol_g8b_point_right_supervise", "监督权与获得国家赔偿权", 4, SUBJECT, 216003),
    (216027, "jpol_g8b_point_right_person_free", "人身自由不受侵犯：禁止非法拘禁与搜查", 5, SUBJECT, 216003),
    (216028, "jpol_g8b_point_right_dignity", "人格尊严与住宅不受侵犯", 6, SUBJECT, 216003),
    (216029, "jpol_g8b_point_right_communication", "通信自由和通信秘密受法律保护", 7, SUBJECT, 216003),
    (216030, "jpol_g8b_point_right_economic", "财产权、劳动权与物质帮助权", 8, SUBJECT, 216003),
    (216031, "jpol_g8b_point_right_education", "受教育权与文化权利", 9, SUBJECT, 216003),
    (216032, "jpol_g8b_point_right_exercise", "依法行使权利：有界限、守程序", 10, SUBJECT, 216003),

    # 公民基本义务与依法履行
    (216033, "jpol_g8b_point_duty_define", "公民基本义务的含义与主要内容", 1, SUBJECT, 216004),
    (216034, "jpol_g8b_point_duty_constitution", "遵守宪法法律、保守国家秘密的义务", 2, SUBJECT, 216004),
    (216035, "jpol_g8b_point_duty_public", "爱护公共财产、遵守劳动纪律与公共秩序、尊重社会公德", 3, SUBJECT, 216004),
    (216036, "jpol_g8b_point_duty_unity", "维护国家统一和全国各民族团结的义务", 4, SUBJECT, 216004),
    (216037, "jpol_g8b_point_duty_security", "维护国家安全、荣誉和利益的义务", 5, SUBJECT, 216004),
    (216038, "jpol_g8b_point_duty_army_tax", "依法服兵役与依法纳税的义务", 6, SUBJECT, 216004),
    (216039, "jpol_g8b_point_duty_unity_right", "公民行使权利与履行义务的统一关系", 7, SUBJECT, 216004),
    (216040, "jpol_g8b_point_duty_liability", "违反法定义务须承担相应法律责任", 8, SUBJECT, 216004),

    # 我国政治制度与经济制度
    (216041, "jpol_g8b_point_sys_npc", "人民代表大会制度是我国的根本政治制度", 1, SUBJECT, 216005),
    (216042, "jpol_g8b_point_sys_deputy", "人大代表的产生方式、职权与义务", 2, SUBJECT, 216005),
    (216043, "jpol_g8b_point_sys_multiparty", "中国共产党领导的多党合作和政治协商制度", 3, SUBJECT, 216005),
    (216044, "jpol_g8b_point_sys_cppcc", "中国人民政治协商会议的性质与职能", 4, SUBJECT, 216005),
    (216045, "jpol_g8b_point_sys_autonomy", "民族区域自治制度与自治机关", 5, SUBJECT, 216005),
    (216046, "jpol_g8b_point_sys_grassroots", "基层群众自治制度：村民委员会与居民委员会", 6, SUBJECT, 216005),
    (216047, "jpol_g8b_point_sys_ownership", "公有制为主体、多种所有制经济共同发展", 7, SUBJECT, 216005),
    (216048, "jpol_g8b_point_sys_ownership_status", "国有经济、集体经济与非公有制经济的地位", 8, SUBJECT, 216005),
    (216049, "jpol_g8b_point_sys_distribution", "按劳分配为主体、多种分配方式并存", 9, SUBJECT, 216005),
    (216050, "jpol_g8b_point_sys_market", "社会主义市场经济体制与市场配置资源的决定性作用", 10, SUBJECT, 216005),
    (216051, "jpol_g8b_point_sys_two_unswerving", "坚持“两个毫不动摇”与激发市场主体活力", 11, SUBJECT, 216005),

    # 我国国家机构与职权
    (216052, "jpol_g8b_point_org_system", "国家机构的含义与组织体系", 1, SUBJECT, 216006),
    (216053, "jpol_g8b_point_org_npc", "全国人民代表大会是最高国家权力机关", 2, SUBJECT, 216006),
    (216054, "jpol_g8b_point_org_npcsc", "全国人大常委会与地方各级人大的职权", 3, SUBJECT, 216006),
    (216055, "jpol_g8b_point_org_president", "国家主席的产生与职权", 4, SUBJECT, 216006),
    (216056, "jpol_g8b_point_org_government", "国家行政机关：国务院与地方各级人民政府", 5, SUBJECT, 216006),
    (216057, "jpol_g8b_point_org_admin_law", "行政机关依法行政与政府职能的履行", 6, SUBJECT, 216006),
    (216058, "jpol_g8b_point_org_supervision", "国家监察机关：监察委员会的性质与职责", 7, SUBJECT, 216006),
    (216059, "jpol_g8b_point_org_court", "人民法院的性质与审判权", 8, SUBJECT, 216006),
    (216060, "jpol_g8b_point_org_procuratorate", "人民检察院的性质与法律监督权", 9, SUBJECT, 216006),
    (216061, "jpol_g8b_point_org_democratic", "国家机构实行民主集中制原则", 10, SUBJECT, 216006),
    (216062, "jpol_g8b_point_org_supervise_power", "国家机关依法行使权力并接受监督", 11, SUBJECT, 216006),

    # 自由平等的真谛与追求
    (216063, "jpol_g8b_point_free_define", "自由的含义：有限制的、相对的自由", 1, SUBJECT, 216007),
    (216064, "jpol_g8b_point_free_law", "法治与自由的关系", 2, SUBJECT, 216007),
    (216065, "jpol_g8b_point_equal_define", "平等的含义：同等情况同等对待、不同情况差别对待", 3, SUBJECT, 216007),
    (216066, "jpol_g8b_point_equal_law", "法律面前人人平等的表现", 4, SUBJECT, 216007),
    (216067, "jpol_g8b_point_free_treasure", "珍视自由、依法行使自由", 5, SUBJECT, 216007),
    (216068, "jpol_g8b_point_equal_practice", "践行平等：反对特权、平等对待他人的合法权利", 6, SUBJECT, 216007),
    (216069, "jpol_g8b_point_equal_discrimination", "反对歧视、敢于抵制不平等的行为", 7, SUBJECT, 216007),

    # 公平正义的价值与守护
    (216070, "jpol_g8b_point_fair_define", "公平的含义与内涵", 1, SUBJECT, 216008),
    (216071, "jpol_g8b_point_fair_value", "公平对个人发展与社会稳定的价值", 2, SUBJECT, 216008),
    (216072, "jpol_g8b_point_justice_define", "正义的含义与正义行为的识别", 3, SUBJECT, 216008),
    (216073, "jpol_g8b_point_justice_value", "正义对社会制度与社会秩序的意义", 4, SUBJECT, 216008),
    (216074, "jpol_g8b_point_fair_person", "个人守护公平：面对利益冲突坚持公平原则", 5, SUBJECT, 216008),
    (216075, "jpol_g8b_point_fair_state", "国家保障公平：制度保障与司法公正", 6, SUBJECT, 216008),
    (216076, "jpol_g8b_point_justice_person", "个人守护正义：见义勇为与见义智为", 7, SUBJECT, 216008),
    (216077, "jpol_g8b_point_justice_state", "司法是捍卫社会公平正义的最后一道防线", 8, SUBJECT, 216008),
)

"""统编版（2019）高中思想政治选择性必修第一册（当代国际政治与经济）：课框目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G10 = 10
BOOK_ID = 7105

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中思想政治选择性必修第一册（当代国际政治与经济）",
    "pol_e1",
    5,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (750101, "第一单元 各具特色的国家", "pol_e1_u01", 1, BOOK_ID, None),
    (750102, "第二单元 世界多极化", "pol_e1_u02", 2, BOOK_ID, None),
    (750103, "第三单元 经济全球化", "pol_e1_u03", 3, BOOK_ID, None),
    (750104, "第四单元 国际组织", "pol_e1_u04", 4, BOOK_ID, None),
    (750111, "第一课 国体与政体", "pol_e1_l01", 1, BOOK_ID, 750101),
    (750112, "第二课 国家的结构形式", "pol_e1_l02", 2, BOOK_ID, 750101),
    (750113, "第三课 多极化趋势", "pol_e1_l03", 1, BOOK_ID, 750102),
    (750114, "第四课 和平与发展", "pol_e1_l04", 2, BOOK_ID, 750102),
    (750115, "第五课 中国的外交", "pol_e1_l05", 3, BOOK_ID, 750102),
    (750116, "第六课 走进经济全球化", "pol_e1_l06", 1, BOOK_ID, 750103),
    (750117, "第七课 经济全球化与中国", "pol_e1_l07", 2, BOOK_ID, 750103),
    (750118, "第八课 主要的国际组织", "pol_e1_l08", 1, BOOK_ID, 750104),
    (750119, "第九课 中国与国际组织", "pol_e1_l09", 2, BOOK_ID, 750104),
    (750121, "第一框 国家是什么", "pol_e1_l01_s01", 1, BOOK_ID, 750111),
    (750122, "第二框 国家的政权组织形式", "pol_e1_l01_s02", 2, BOOK_ID, 750111),
    (750123, "第三框 政党和利益集团", "pol_e1_l01_s03", 3, BOOK_ID, 750111),
    (750124, "第一框 主权统一与政权分层", "pol_e1_l02_s01", 1, BOOK_ID, 750112),
    (750125, "第二框 单一制和复合制", "pol_e1_l02_s02", 2, BOOK_ID, 750112),
    (750126, "第一框 世界多极化的发展", "pol_e1_l03_s01", 1, BOOK_ID, 750113),
    (750127, "第二框 国际关系", "pol_e1_l03_s02", 2, BOOK_ID, 750113),
    (750128, "第三框 国际关系民主化", "pol_e1_l03_s03", 3, BOOK_ID, 750113),
    (750129, "第一框 时代的主题", "pol_e1_l04_s01", 1, BOOK_ID, 750114),
    (750130, "第二框 挑战与应对", "pol_e1_l04_s02", 2, BOOK_ID, 750114),
    (750131, "第一框 中国外交政策的形成与发展", "pol_e1_l05_s01", 1, BOOK_ID, 750115),
    (750132, "第二框 构建人类命运共同体", "pol_e1_l05_s02", 2, BOOK_ID, 750115),
    (750133, "第一框 认识经济全球化", "pol_e1_l06_s01", 1, BOOK_ID, 750116),
    (750134, "第二框 日益开放的世界经济", "pol_e1_l06_s02", 2, BOOK_ID, 750116),
    (750135, "第一框 开放是当代中国的鲜明标识", "pol_e1_l07_s01", 1, BOOK_ID, 750117),
    (750136, "第二框 做全球发展的贡献者", "pol_e1_l07_s02", 2, BOOK_ID, 750117),
    (750137, "第一框 日益重要的国际组织", "pol_e1_l08_s01", 1, BOOK_ID, 750118),
    (750138, "第二框 联合国", "pol_e1_l08_s02", 2, BOOK_ID, 750118),
    (750139, "第三框 区域性国际组织", "pol_e1_l08_s03", 3, BOOK_ID, 750118),
    (750140, "第一框 中国与联合国", "pol_e1_l09_s01", 1, BOOK_ID, 750119),
    (750141, "第二框 中国与新兴国际组织", "pol_e1_l09_s02", 2, BOOK_ID, 750119),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (750001, "pol_e1_domain_state", "各具特色的国家：国体、政体与结构形式", 1, SUBJECT, None),
    (750002, "pol_e1_domain_multipolarity", "世界多极化：国际关系与时代主题", 2, SUBJECT, None),
    (750003, "pol_e1_domain_globalization", "经济全球化：开放型世界经济与中国贡献", 3, SUBJECT, None),
    (750004, "pol_e1_domain_intl_org", "国际组织：全球治理与多边合作", 4, SUBJECT, None),

    # 单元域层
    (750005, "pol_e1_unit01_state", "第一单元 各具特色的国家", 1, SUBJECT, 750001),
    (750006, "pol_e1_unit02_multipolarity", "第二单元 世界多极化", 1, SUBJECT, 750002),
    (750007, "pol_e1_unit03_globalization", "第三单元 经济全球化", 1, SUBJECT, 750003),
    (750008, "pol_e1_unit04_intl_org", "第四单元 国际组织", 1, SUBJECT, 750004),

    # 课域层
    (750009, "pol_e1_lesson01", "第一课 国体与政体", 1, SUBJECT, 750005),
    (750010, "pol_e1_lesson02", "第二课 国家的结构形式", 2, SUBJECT, 750005),
    (750011, "pol_e1_lesson03", "第三课 多极化趋势", 1, SUBJECT, 750006),
    (750012, "pol_e1_lesson04", "第四课 和平与发展", 2, SUBJECT, 750006),
    (750013, "pol_e1_lesson05", "第五课 中国的外交", 3, SUBJECT, 750006),
    (750014, "pol_e1_lesson06", "第六课 走进经济全球化", 1, SUBJECT, 750007),
    (750015, "pol_e1_lesson07", "第七课 经济全球化与中国", 2, SUBJECT, 750007),
    (750016, "pol_e1_lesson08", "第八课 主要的国际组织", 1, SUBJECT, 750008),
    (750017, "pol_e1_lesson09", "第九课 中国与国际组织", 2, SUBJECT, 750008),

    # 框域层
    (750018, "pol_e1_sec_state_what", "第一框 国家是什么", 1, SUBJECT, 750009),
    (750019, "pol_e1_sec_regime_form", "第二框 国家的政权组织形式", 2, SUBJECT, 750009),
    (750020, "pol_e1_sec_party_interest", "第三框 政党和利益集团", 3, SUBJECT, 750009),
    (750021, "pol_e1_sec_sovereignty_layers", "第一框 主权统一与政权分层", 1, SUBJECT, 750010),
    (750022, "pol_e1_sec_unitary_federal", "第二框 单一制和复合制", 2, SUBJECT, 750010),
    (750023, "pol_e1_sec_multipolarity_dev", "第一框 世界多极化的发展", 1, SUBJECT, 750011),
    (750024, "pol_e1_sec_intl_relations", "第二框 国际关系", 2, SUBJECT, 750011),
    (750025, "pol_e1_sec_ir_democratization", "第三框 国际关系民主化", 3, SUBJECT, 750011),
    (750026, "pol_e1_sec_era_theme", "第一框 时代的主题", 1, SUBJECT, 750012),
    (750027, "pol_e1_sec_challenges_response", "第二框 挑战与应对", 2, SUBJECT, 750012),
    (750028, "pol_e1_sec_china_diplomacy", "第一框 中国外交政策的形成与发展", 1, SUBJECT, 750013),
    (750029, "pol_e1_sec_community_future", "第二框 构建人类命运共同体", 2, SUBJECT, 750013),
    (750030, "pol_e1_sec_understand_global", "第一框 认识经济全球化", 1, SUBJECT, 750014),
    (750031, "pol_e1_sec_open_world_econ", "第二框 日益开放的世界经济", 2, SUBJECT, 750014),
    (750032, "pol_e1_sec_opening_mark", "第一框 开放是当代中国的鲜明标识", 1, SUBJECT, 750015),
    (750033, "pol_e1_sec_global_contributor", "第二框 做全球发展的贡献者", 2, SUBJECT, 750015),
    (750034, "pol_e1_sec_intl_org_growing", "第一框 日益重要的国际组织", 1, SUBJECT, 750016),
    (750035, "pol_e1_sec_united_nations", "第二框 联合国", 2, SUBJECT, 750016),
    (750036, "pol_e1_sec_regional_org", "第三框 区域性国际组织", 3, SUBJECT, 750016),
    (750037, "pol_e1_sec_china_un", "第一框 中国与联合国", 1, SUBJECT, 750017),
    (750038, "pol_e1_sec_china_emerging_org", "第二框 中国与新兴国际组织", 2, SUBJECT, 750017),

    # 1.1 国家是什么
    (750039, "pol_e1_state_origin_essence", "国家的产生、本质与阶级性", 1, SUBJECT, 750018),
    (750040, "pol_e1_state_elements", "国家构成要素：人口、领土、政权与主权", 2, SUBJECT, 750018),
    (750041, "pol_e1_state_nature_functions", "国家性质与国家职能：政治统治与社会管理", 3, SUBJECT, 750018),
    (750042, "pol_e1_state_form_regime_relation", "国体与政体的关系：内容与形式", 4, SUBJECT, 750018),

    # 1.2 国家的政权组织形式
    (750043, "pol_e1_republic_monarchy", "民主共和制与君主立宪制", 1, SUBJECT, 750019),
    (750044, "pol_e1_parliamentary_presidential", "议会制与总统制的比较", 2, SUBJECT, 750019),
    (750045, "pol_e1_semi_presidential_committee", "半总统制与委员会制的特点", 3, SUBJECT, 750019),
    (750046, "pol_e1_socialist_state_form", "社会主义国家的政权组织形式：人民代表大会制度", 4, SUBJECT, 750019),

    # 1.3 政党和利益集团
    (750047, "pol_e1_party_nature_function", "政党的含义、特征与基本功能", 1, SUBJECT, 750020),
    (750048, "pol_e1_party_system_types", "政党制度的类型：一党制、两党制与多党制", 2, SUBJECT, 750020),
    (750049, "pol_e1_interest_group", "利益集团的含义、类型与政治作用", 3, SUBJECT, 750020),

    # 2.1 主权统一与政权分层
    (750050, "pol_e1_sovereignty_connotation", "国家主权的含义、特征与作用", 1, SUBJECT, 750021),
    (750051, "pol_e1_central_local", "中央与地方关系：政权分层与权力配置", 2, SUBJECT, 750021),
    (750052, "pol_e1_state_structure_factors", "国家结构形式的含义与影响因素", 3, SUBJECT, 750021),

    # 2.2 单一制和复合制
    (750053, "pol_e1_unitary_state", "单一制国家的特征与类型", 1, SUBJECT, 750022),
    (750054, "pol_e1_federal_state", "联邦制国家的特征与类型", 2, SUBJECT, 750022),
    (750055, "pol_e1_confederation_compare", "邦联制与国家结构形式比较", 3, SUBJECT, 750022),

    # 3.1 世界多极化的发展
    (750056, "pol_e1_multipolarization_process", "世界多极化的形成与发展进程", 1, SUBJECT, 750023),
    (750057, "pol_e1_power_centers", "当今世界力量中心的多元化", 2, SUBJECT, 750023),
    (750058, "pol_e1_multipolarity_significance", "世界多极化的意义与影响", 3, SUBJECT, 750023),

    # 3.2 国际关系
    (750059, "pol_e1_ir_connotation_forms", "国际关系的含义、内容与基本形式", 1, SUBJECT, 750024),
    (750060, "pol_e1_national_interest_decisive", "国家利益是国际关系的决定性因素", 2, SUBJECT, 750024),
    (750061, "pol_e1_national_power", "国家实力对国际关系的影响", 3, SUBJECT, 750024),
    (750062, "pol_e1_competition_cooperation", "国际关系中的竞争、合作与冲突", 4, SUBJECT, 750024),

    # 3.3 国际关系民主化
    (750063, "pol_e1_ir_democratization_connotation", "国际关系民主化的内涵与基本要求", 1, SUBJECT, 750025),
    (750064, "pol_e1_ir_democratization_significance", "推动国际关系民主化的意义", 2, SUBJECT, 750025),

    # 4.1 时代的主题
    (750065, "pol_e1_peace_development_theme", "和平与发展是当今时代的主题", 1, SUBJECT, 750026),
    (750066, "pol_e1_peace_development_relation", "和平与发展的相互关系", 2, SUBJECT, 750026),
    (750067, "pol_e1_maintain_peace_paths", "维护和平、促进发展的有效途径", 3, SUBJECT, 750026),

    # 4.2 挑战与应对
    (750068, "pol_e1_hegemonism_power_politics", "霸权主义和强权政治", 1, SUBJECT, 750027),
    (750069, "pol_e1_global_issues_governance", "全球性问题与全球治理", 2, SUBJECT, 750027),

    # 5.1 中国外交政策的形成与发展
    (750070, "pol_e1_foreign_policy_position", "我国外交政策的基本立场、宗旨与目标", 1, SUBJECT, 750028),
    (750071, "pol_e1_five_principles", "和平共处五项原则", 2, SUBJECT, 750028),
    (750072, "pol_e1_foreign_policy_development", "中国外交政策的形成与发展", 3, SUBJECT, 750028),

    # 5.2 构建人类命运共同体
    (750073, "pol_e1_community_proposal", "人类命运共同体的提出与核心内涵", 1, SUBJECT, 750029),
    (750074, "pol_e1_community_five_worlds", "构建人类命运共同体的目标：五个世界", 2, SUBJECT, 750029),
    (750075, "pol_e1_belt_road", "共建“一带一路”的实践与意义", 3, SUBJECT, 750029),
    (750076, "pol_e1_community_significance", "构建人类命运共同体的世界意义", 4, SUBJECT, 750029),

    # 6.1 认识经济全球化
    (750077, "pol_e1_globalization_connotation", "经济全球化的含义与主要表现", 1, SUBJECT, 750030),
    (750078, "pol_e1_globalization_causes", "经济全球化的形成原因", 2, SUBJECT, 750030),
    (750079, "pol_e1_globalization_impacts", "经济全球化的机遇与挑战", 3, SUBJECT, 750030),

    # 6.2 日益开放的世界经济
    (750080, "pol_e1_open_world_economy", "开放型世界经济的特征与要求", 1, SUBJECT, 750031),
    (750081, "pol_e1_global_value_chain", "国际分工、全球产业链与供应链", 2, SUBJECT, 750031),

    # 7.1 开放是当代中国的鲜明标识
    (750082, "pol_e1_opening_policy_history", "对外开放基本国策的确立与发展", 1, SUBJECT, 750032),
    (750083, "pol_e1_high_level_opening", "推进高水平对外开放与全面开放新格局", 2, SUBJECT, 750032),

    # 7.2 做全球发展的贡献者
    (750084, "pol_e1_china_beneficiary_contributor", "中国是经济全球化的受益者与贡献者", 1, SUBJECT, 750033),
    (750085, "pol_e1_trade_investment_liberalization", "推动贸易和投资自由化便利化", 2, SUBJECT, 750033),
    (750086, "pol_e1_global_economic_governance", "积极参与全球经济治理", 3, SUBJECT, 750033),

    # 8.1 日益重要的国际组织
    (750087, "pol_e1_intl_org_connotation_types", "国际组织的含义、分类与作用", 1, SUBJECT, 750034),
    (750088, "pol_e1_intl_org_status", "国际组织在国际社会中的地位", 2, SUBJECT, 750034),

    # 8.2 联合国
    (750089, "pol_e1_un_purposes_principles", "联合国的宗旨与原则", 1, SUBJECT, 750035),
    (750090, "pol_e1_un_organs", "联合国主要机构与职能", 2, SUBJECT, 750035),
    (750091, "pol_e1_un_role_limits", "联合国的作用与局限性", 3, SUBJECT, 750035),

    # 8.3 区域性国际组织
    (750092, "pol_e1_eu", "欧洲联盟的性质、机构与作用", 1, SUBJECT, 750036),
    (750093, "pol_e1_apec_asean", "亚太经合组织与东南亚国家联盟", 2, SUBJECT, 750036),
    (750094, "pol_e1_au_others", "非洲联盟及其他区域性国际组织", 3, SUBJECT, 750036),

    # 9.1 中国与联合国
    (750095, "pol_e1_china_un_position", "中国在联合国的地位与作用", 1, SUBJECT, 750037),
    (750096, "pol_e1_china_un_practice", "中国与联合国合作的实践", 2, SUBJECT, 750037),

    # 9.2 中国与新兴国际组织
    (750097, "pol_e1_brics", "金砖国家合作机制", 1, SUBJECT, 750038),
    (750098, "pol_e1_sco", "上海合作组织", 2, SUBJECT, 750038),
    (750099, "pol_e1_g20", "二十国集团与全球经济治理", 3, SUBJECT, 750038),
)

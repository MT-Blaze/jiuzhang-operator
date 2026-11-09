"""人教版（2019）高中地理选择性必修第三册（资源、环境与国家安全）：章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 9
G10 = 10
BOOK_ID = 9205

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中地理选择性必修第三册（资源、环境与国家安全）",
    "geo_e3",
    5,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (950101, "第一章 自然环境与人类社会", "geo_e3_u01", 1, BOOK_ID, None),
    (950102, "第二章 资源安全与国家安全", "geo_e3_u02", 2, BOOK_ID, None),
    (950103, "第三章 环境安全与国家安全", "geo_e3_u03", 3, BOOK_ID, None),
    (950104, "第四章 保障国家安全的资源、环境战略与行动", "geo_e3_u04", 4, BOOK_ID, None),
    (950111, "第一节 自然环境的服务功能", "geo_e3_l01", 1, BOOK_ID, 950101),
    (950112, "第二节 自然资源及其利用", "geo_e3_l02", 2, BOOK_ID, 950101),
    (950113, "第三节 环境问题及其危害", "geo_e3_l03", 3, BOOK_ID, 950101),
    (950114, "第一节 资源安全对国家安全的影响", "geo_e3_l04", 1, BOOK_ID, 950102),
    (950115, "第二节 中国的能源安全", "geo_e3_l05", 2, BOOK_ID, 950102),
    (950116, "第三节 中国的耕地资源与粮食安全", "geo_e3_l06", 3, BOOK_ID, 950102),
    (950117, "第四节 海洋空间资源开发与国家安全", "geo_e3_l07", 4, BOOK_ID, 950102),
    (950118, "第一节 环境安全对国家安全的影响", "geo_e3_l08", 1, BOOK_ID, 950103),
    (950119, "第二节 环境污染与国家安全", "geo_e3_l09", 2, BOOK_ID, 950103),
    (950120, "第三节 生态保护与国家安全", "geo_e3_l10", 3, BOOK_ID, 950103),
    (950121, "第四节 全球气候变化与国家安全", "geo_e3_l11", 4, BOOK_ID, 950103),
    (950122, "第一节 走向生态文明", "geo_e3_l12", 1, BOOK_ID, 950104),
    (950123, "第二节 国家战略与政策", "geo_e3_l13", 2, BOOK_ID, 950104),
    (950124, "第三节 国际合作", "geo_e3_l14", 3, BOOK_ID, 950104),
)

# id / code / name / sort_order / subject_id / parent_id
# 95 00 01-04 为册域，95 00 05-08 为章域，95 00 09-22 为节域；95 00 23-99 为考点层。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (950001, "geo_e3_domain_natural_human", "自然环境与人类社会：服务功能、资源利用与环境问题", 1, SUBJECT, None),
    (950002, "geo_e3_domain_resource_security", "资源安全与国家安全：资源安全、能源、耕地粮食与海洋空间", 2, SUBJECT, None),
    (950003, "geo_e3_domain_env_security", "环境安全与国家安全：环境安全、污染防治、生态保护与气候变化", 3, SUBJECT, None),
    (950004, "geo_e3_domain_strategy_action", "资源环境战略与行动：生态文明、国家战略政策与国际合作", 4, SUBJECT, None),

    # 章域层
    (950005, "geo_e3_chapter01", "第一章 自然环境与人类社会", 1, SUBJECT, 950001),
    (950006, "geo_e3_chapter02", "第二章 资源安全与国家安全", 1, SUBJECT, 950002),
    (950007, "geo_e3_chapter03", "第三章 环境安全与国家安全", 1, SUBJECT, 950003),
    (950008, "geo_e3_chapter04", "第四章 保障国家安全的资源、环境战略与行动", 1, SUBJECT, 950004),

    # 节域层
    (950009, "geo_e3_section01", "第一节 自然环境的服务功能", 1, SUBJECT, 950005),
    (950010, "geo_e3_section02", "第二节 自然资源及其利用", 2, SUBJECT, 950005),
    (950011, "geo_e3_section03", "第三节 环境问题及其危害", 3, SUBJECT, 950005),
    (950012, "geo_e3_section04", "第一节 资源安全对国家安全的影响", 1, SUBJECT, 950006),
    (950013, "geo_e3_section05", "第二节 中国的能源安全", 2, SUBJECT, 950006),
    (950014, "geo_e3_section06", "第三节 中国的耕地资源与粮食安全", 3, SUBJECT, 950006),
    (950015, "geo_e3_section07", "第四节 海洋空间资源开发与国家安全", 4, SUBJECT, 950006),
    (950016, "geo_e3_section08", "第一节 环境安全对国家安全的影响", 1, SUBJECT, 950007),
    (950017, "geo_e3_section09", "第二节 环境污染与国家安全", 2, SUBJECT, 950007),
    (950018, "geo_e3_section10", "第三节 生态保护与国家安全", 3, SUBJECT, 950007),
    (950019, "geo_e3_section11", "第四节 全球气候变化与国家安全", 4, SUBJECT, 950007),
    (950020, "geo_e3_section12", "第一节 走向生态文明", 1, SUBJECT, 950008),
    (950021, "geo_e3_section13", "第二节 国家战略与政策", 2, SUBJECT, 950008),
    (950022, "geo_e3_section14", "第三节 国际合作", 3, SUBJECT, 950008),

    # 第一章第一节考点：自然环境的服务功能
    (950023, "geo_e3_point_service_concept", "自然环境服务功能的内涵：自然环境为人类生存发展提供的条件与效用，含四大类型", 1, SUBJECT, 950009),
    (950024, "geo_e3_point_provisioning", "供给服务：提供食物、淡水、木材、纤维与矿产等物质产品，具有数量与速率限制", 2, SUBJECT, 950009),
    (950025, "geo_e3_point_regulating", "调节服务：调节气候、涵养水源、净化环境、固碳释氧与减轻自然灾害", 3, SUBJECT, 950009),
    (950026, "geo_e3_point_cultural", "文化服务：提供审美、教育、科研、康养与精神文化价值，具有非消耗性", 4, SUBJECT, 950009),
    (950027, "geo_e3_point_supporting", "支撑服务：土壤形成、养分循环、初级生产与生物多样性维持，是其他服务的基础", 5, SUBJECT, 950009),
    (950028, "geo_e3_point_service_tradeoff", "服务功能之间的权衡与人类活动影响：过度利用供给服务会削弱调节与支撑服务，需可持续利用", 6, SUBJECT, 950009),

    # 第一章第二节考点：自然资源及其利用
    (950029, "geo_e3_point_resource_concept", "自然资源的概念与属性：自然性、可用性、有限性、地域性与整体性", 1, SUBJECT, 950010),
    (950030, "geo_e3_point_renewable", "可再生资源：太阳能、风能、水能、生物质等，利用强度须低于其再生速度", 2, SUBJECT, 950010),
    (950031, "geo_e3_point_nonrenewable", "非可再生资源：煤炭、石油、天然气与金属矿产，储量有限，需节约、替代与循环利用", 3, SUBJECT, 950010),
    (950032, "geo_e3_point_resource_evaluation", "自然资源的评价与利用：从数量、质量、分布、组合与开发条件评价，走集约高效利用道路", 4, SUBJECT, 950010),
    (950033, "geo_e3_point_china_resource_endowment", "我国自然资源基本特征：总量丰富、人均不足、时空分布不均、资源组合不匹配", 5, SUBJECT, 950010),

    # 第一章第三节考点：环境问题及其危害
    (950034, "geo_e3_point_env_problem_concept", "环境问题的概念与类型：环境污染、生态破坏与资源短缺三大类", 1, SUBJECT, 950011),
    (950035, "geo_e3_point_env_problem_cause", "环境问题的成因：人口增长与消费扩大、经济增长方式粗放、技术局限与自然条件脆弱", 2, SUBJECT, 950011),
    (950036, "geo_e3_point_env_pollution_harm", "环境污染的危害：危害人体健康、破坏生态系统、造成经济损失与社会矛盾", 3, SUBJECT, 950011),
    (950037, "geo_e3_point_eco_damage_harm", "生态破坏的危害：生物多样性减少、土地退化、水源涵养下降与生态服务功能衰退", 4, SUBJECT, 950011),
    (950038, "geo_e3_point_env_problem_feature", "环境问题的地域差异与特点：城乡差异、南北差异，具有综合性、区域性、全球性与滞后性", 5, SUBJECT, 950011),

    # 第二章第一节考点：资源安全对国家安全的影响
    (950039, "geo_e3_point_resource_security_concept", "资源安全的概念与内涵：稳定、持续、及时、经济地获取所需资源，且不损害生态环境", 1, SUBJECT, 950012),
    (950040, "geo_e3_point_resource_security_measure", "资源安全的衡量维度：数量安全、质量安全、结构安全、空间安全与价格安全", 2, SUBJECT, 950012),
    (950041, "geo_e3_point_resource_security_factors", "资源安全的影响因素：资源禀赋、供需格局、对外依存度、运输通道与国际市场", 3, SUBJECT, 950012),
    (950042, "geo_e3_point_resource_security_national", "资源安全对国家安全的意义：是经济安全、军事安全与社会稳定的基础保障", 4, SUBJECT, 950012),
    (950043, "geo_e3_point_resource_risk", "资源供给中断的风险：价格剧烈波动、出口禁运、运输通道受阻与地缘冲突", 5, SUBJECT, 950012),
    (950044, "geo_e3_point_resource_strategy", "保障资源安全的战略：开源、节流、储备、替代与进口多元化，提升资源保障能力", 6, SUBJECT, 950012),

    # 第二章第二节考点：中国的能源安全
    (950045, "geo_e3_point_energy_types", "能源的分类与我国能源禀赋：常规与新能源，煤炭丰富、油气不足、水风光潜力大", 1, SUBJECT, 950013),
    (950046, "geo_e3_point_energy_structure", "我国能源消费结构与空间错位：以煤炭为主、非化石能源比重上升，生产西多东少、北多南少", 2, SUBJECT, 950013),
    (950047, "geo_e3_point_oil_security", "石油安全：对外依存度高、进口来源与通道集中，需建设战略储备与多元进口通道", 3, SUBJECT, 950013),
    (950048, "geo_e3_point_coal_clean", "煤炭清洁高效利用：超低排放改造、煤电灵活性调峰与现代煤化工", 4, SUBJECT, 950013),
    (950049, "geo_e3_point_new_energy", "新能源发展：风电光伏基地、核电、水电与新型电力系统建设", 5, SUBJECT, 950013),
    (950050, "geo_e3_point_energy_transition", "能源安全战略与“双碳”转型：节能提效、非化石能源替代、科技创新与体制机制改革", 6, SUBJECT, 950013),

    # 第二章第三节考点：中国的耕地资源与粮食安全（高频）
    (950051, "geo_e3_point_farmland_quantity", "我国耕地数量与质量：人均耕地少、中低产田比例高，坚守18亿亩耕地红线", 1, SUBJECT, 950014),
    (950052, "geo_e3_point_farmland_distribution", "耕地资源分布与粮食生产格局：集中东北、华北与长江中下游，生产重心北移、北粮南运", 2, SUBJECT, 950014),
    (950053, "geo_e3_point_food_security_concept", "粮食安全的概念与内涵：数量充足、质量安全、供应稳定、获取有保障", 3, SUBJECT, 950014),
    (950054, "geo_e3_point_farmland_loss", "耕地减少的原因：建设占用、生态退耕、灾害损毁与撂荒，以及耕地非粮化", 4, SUBJECT, 950014),
    (950055, "geo_e3_point_farmland_protection", "耕地保护制度：耕地红线、占补平衡、永久基本农田特殊保护与田长制", 5, SUBJECT, 950014),
    (950056, "geo_e3_point_high_standard_farmland", "高标准农田建设：田块整治、灌排配套、地力提升与机械化，落实藏粮于地", 6, SUBJECT, 950014),
    (950057, "geo_e3_point_food_strategy", "国家粮食安全战略：藏粮于地、藏粮于技、种业振兴、储备调节与进口多元化", 7, SUBJECT, 950014),

    # 第二章第四节考点：海洋空间资源开发与国家安全
    (950058, "geo_e3_point_marine_concept", "海洋空间资源的概念与类型：海域、海岸带、海岛、海底与海洋上空", 1, SUBJECT, 950015),
    (950059, "geo_e3_point_marine_feature", "海洋空间资源的特点：立体性、流动性、复合性、开放性与开发难度大", 2, SUBJECT, 950015),
    (950060, "geo_e3_point_marine_development", "海洋空间资源的开发方式：港口航运、围填海、海上牧场、海上风电与油气平台", 3, SUBJECT, 950015),
    (950061, "geo_e3_point_marine_rights", "海洋权益与国家安全：领海、毗连区、专属经济区与大陆架的制度安排", 4, SUBJECT, 950015),
    (950062, "geo_e3_point_marine_eco_management", "海洋开发中的生态问题与管理：滨海湿地破坏、海洋污染，需功能区划、生态红线与有偿使用", 5, SUBJECT, 950015),

    # 第三章第一节考点：环境安全对国家安全的影响
    (950063, "geo_e3_point_env_security_concept", "环境安全的概念与层次：环境状况不对人类生存发展构成威胁，含局地、区域与全球尺度", 1, SUBJECT, 950016),
    (950064, "geo_e3_point_env_security_national", "环境安全与国家安全的关系：关系公众健康、经济安全、社会稳定与国家形象", 2, SUBJECT, 950016),
    (950065, "geo_e3_point_env_security_threat", "环境安全的主要威胁：环境污染、生态退化、气候变化与突发环境事件", 3, SUBJECT, 950016),
    (950066, "geo_e3_point_env_security_assessment", "环境安全评价与监测：环境质量标准、生态红线、风险源排查与预警机制", 4, SUBJECT, 950016),
    (950067, "geo_e3_point_env_security_governance", "环境安全治理体系：法治保障、标准约束、监管执法、应急处置与公众参与", 5, SUBJECT, 950016),

    # 第三章第二节考点：环境污染与国家安全
    (950068, "geo_e3_point_pollution_types", "环境污染的主要类型：大气、水、土壤、固体废弃物与噪声污染", 1, SUBJECT, 950017),
    (950069, "geo_e3_point_pollution_transfer", "污染跨境转移的形式与原因：污染产业转移、废物越境转移与污染物输送，源于标准与成本差异", 2, SUBJECT, 950017),
    (950070, "geo_e3_point_pollution_transfer_harm", "污染跨境转移的危害：输入国生态与健康受损，引发国际环境纠纷与外交摩擦", 3, SUBJECT, 950017),
    (950071, "geo_e3_point_basel_convention", "危险废物越境转移的国际管制：《巴塞尔公约》与事先知情同意程序", 4, SUBJECT, 950017),
    (950072, "geo_e3_point_pollution_battle", "污染防治攻坚战：蓝天、碧水、净土三大保卫战与排污许可制度", 5, SUBJECT, 950017),
    (950073, "geo_e3_point_pollution_prevention", "污染综合防治：源头削减、过程控制、末端治理与区域联防联控", 6, SUBJECT, 950017),

    # 第三章第三节考点：生态保护与国家安全
    (950074, "geo_e3_point_eco_protection_concept", "生态保护的概念与意义：维护生态系统结构与功能，保障国家生态安全", 1, SUBJECT, 950018),
    (950075, "geo_e3_point_eco_redline", "生态保护红线与自然保护地体系：国家公园、自然保护区与自然公园", 2, SUBJECT, 950018),
    (950076, "geo_e3_point_eco_restoration", "生态修复工程：退耕还林还草、三北防护林与山水林田湖草沙一体化保护修复", 3, SUBJECT, 950018),
    (950077, "geo_e3_point_biodiversity", "生物多样性保护：就地保护、迁地保护与外来物种入侵防控", 4, SUBJECT, 950018),
    (950078, "geo_e3_point_eco_compensation", "生态补偿与生态产品价值实现：纵向转移支付、横向补偿与生态产业化", 5, SUBJECT, 950018),

    # 第三章第四节考点：全球气候变化与国家安全
    (950079, "geo_e3_point_climate_evidence", "全球气候变化的证据与趋势：气温上升、海平面上升、冰川退缩与极端天气增多", 1, SUBJECT, 950019),
    (950080, "geo_e3_point_climate_cause", "全球气候变化的成因：自然因素与人为温室气体排放增强温室效应", 2, SUBJECT, 950019),
    (950081, "geo_e3_point_climate_natural_impact", "气候变化对自然系统的影响：冰川冻土消融、海平面上升、生态系统与生物多样性改变", 3, SUBJECT, 950019),
    (950082, "geo_e3_point_climate_human_impact", "气候变化对人类社会与国家安全的影响：农业、水资源、健康、基础设施与气候移民", 4, SUBJECT, 950019),
    (950083, "geo_e3_point_climate_mitigation", "减缓气候变化的措施：节能提效、发展非化石能源、增加碳汇与碳捕集封存", 5, SUBJECT, 950019),
    (950084, "geo_e3_point_climate_adaptation", "适应措施与国际气候治理：防灾减灾、海岸带防护，《巴黎协定》与共同但有区别的责任", 6, SUBJECT, 950019),

    # 第四章第一节考点：走向生态文明
    (950085, "geo_e3_point_man_land_evolution", "人地关系思想的演变：崇拜自然—改造自然—征服自然—人地协调发展", 1, SUBJECT, 950020),
    (950086, "geo_e3_point_sustainability", "可持续发展的内涵：生态、经济、社会三维协调，兼顾代内公平与代际公平", 2, SUBJECT, 950020),
    (950087, "geo_e3_point_eco_civilization", "生态文明的内涵：尊重自然、顺应自然、保护自然，实现人与自然和谐共生", 3, SUBJECT, 950020),
    (950088, "geo_e3_point_green_development", "绿色发展方式与生活方式：绿色低碳循环发展、清洁生产、垃圾分类与低碳出行", 4, SUBJECT, 950020),
    (950089, "geo_e3_point_eco_civilization_institution", "生态文明制度建设：自然资源资产产权、生态保护补偿与生态环境损害责任追究", 5, SUBJECT, 950020),

    # 第四章第二节考点：国家战略与政策
    (950090, "geo_e3_point_national_security_strategy", "总体国家安全观与资源环境保障：统筹发展与安全，守住资源环境安全底线", 1, SUBJECT, 950021),
    (950091, "geo_e3_point_main_function_zone", "主体功能区战略：优化开发、重点开发、限制开发与禁止开发四类区域", 2, SUBJECT, 950021),
    (950092, "geo_e3_point_resource_conservation", "资源节约战略：节约优先、总量与强度双控、循环利用与综合利用", 3, SUBJECT, 950021),
    (950093, "geo_e3_point_territorial_planning", "国土空间规划体系：多规合一、三条控制线与国土空间用途管制", 4, SUBJECT, 950021),
    (950094, "geo_e3_point_reserve_and_policy", "国家储备体系与政策工具：能源、粮食、矿产储备，以及法规、财税与市场化机制", 5, SUBJECT, 950021),

    # 第四章第三节考点：国际合作
    (950095, "geo_e3_point_intl_cooperation_need", "国际合作的必要性与全球治理机制：资源环境问题跨国界，需联合国等平台协同应对", 1, SUBJECT, 950022),
    (950096, "geo_e3_point_intl_resource_cooperation", "资源领域国际合作：能源贸易、矿产投资、运输通道安全与资源开发技术合作", 2, SUBJECT, 950022),
    (950097, "geo_e3_point_intl_env_cooperation", "环境领域国际合作：跨境污染治理、生态保护与《生物多样性公约》履约", 3, SUBJECT, 950022),
    (950098, "geo_e3_point_intl_climate_cooperation", "气候领域国际合作：减排承诺、碳市场衔接与绿色技术转移", 4, SUBJECT, 950022),
    (950099, "geo_e3_point_china_responsibility", "中国的责任与担当：推动构建人类命运共同体，深化南南合作与绿色“一带一路”", 5, SUBJECT, 950022),
)

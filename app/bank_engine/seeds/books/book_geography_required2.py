"""人教版（2019）高中地理必修第二册：章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 9
G10 = 10
BOOK_ID = 9202

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中地理必修第二册",
    "geo_r2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (920101, "第一章 人口", "geo_r2_u01", 1, BOOK_ID, None),
    (920102, "第二章 乡村和城镇", "geo_r2_u02", 2, BOOK_ID, None),
    (920103, "第三章 产业区位因素", "geo_r2_u03", 3, BOOK_ID, None),
    (920104, "第四章 交通运输布局与区域发展", "geo_r2_u04", 4, BOOK_ID, None),
    (920105, "第五章 环境与发展", "geo_r2_u05", 5, BOOK_ID, None),
    (920111, "第一节 人口分布", "geo_r2_l01", 1, BOOK_ID, 920101),
    (920112, "第二节 人口迁移", "geo_r2_l02", 2, BOOK_ID, 920101),
    (920113, "第三节 人口容量", "geo_r2_l03", 3, BOOK_ID, 920101),
    (920114, "第一节 乡村和城镇空间结构", "geo_r2_l04", 1, BOOK_ID, 920102),
    (920115, "第二节 城镇化", "geo_r2_l05", 2, BOOK_ID, 920102),
    (920116, "第三节 地域文化与城乡景观", "geo_r2_l06", 3, BOOK_ID, 920102),
    (920117, "第一节 农业区位因素及其变化", "geo_r2_l07", 1, BOOK_ID, 920103),
    (920118, "第二节 工业区位因素及其变化", "geo_r2_l08", 2, BOOK_ID, 920103),
    (920119, "第三节 服务业区位因素及其变化", "geo_r2_l09", 3, BOOK_ID, 920103),
    (920120, "第一节 区域发展对交通运输布局的影响", "geo_r2_l10", 1, BOOK_ID, 920104),
    (920121, "第二节 交通运输布局对区域发展的影响", "geo_r2_l11", 2, BOOK_ID, 920104),
    (920122, "第一节 人类面临的主要环境问题", "geo_r2_l12", 1, BOOK_ID, 920105),
    (920123, "第二节 走向人地协调——可持续发展", "geo_r2_l13", 2, BOOK_ID, 920105),
    (920124, "第三节 中国国家发展战略举例", "geo_r2_l14", 3, BOOK_ID, 920105),
)

# id / code / name / sort_order / subject_id / parent_id
# 92 00 01-05 为册域，92 00 06-10 为章域，92 00 11-24 为节域；92 00 31-99 为考点层。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (920001, "geo_r2_domain_population", "人口与人地：分布、迁移与容量", 1, SUBJECT, None),
    (920002, "geo_r2_domain_settlement", "聚落与城乡：空间结构、城镇化与地域文化", 2, SUBJECT, None),
    (920003, "geo_r2_domain_industry", "产业区位：农业、工业与服务业的布局选择", 3, SUBJECT, None),
    (920004, "geo_r2_domain_transport", "交通与区域：运输布局与区域发展", 4, SUBJECT, None),
    (920005, "geo_r2_domain_environment", "环境与发展：环境问题、可持续发展与国家战略", 5, SUBJECT, None),

    # 章域层
    (920006, "geo_r2_chapter01", "第一章 人口", 1, SUBJECT, 920001),
    (920007, "geo_r2_chapter02", "第二章 乡村和城镇", 1, SUBJECT, 920002),
    (920008, "geo_r2_chapter03", "第三章 产业区位因素", 1, SUBJECT, 920003),
    (920009, "geo_r2_chapter04", "第四章 交通运输布局与区域发展", 1, SUBJECT, 920004),
    (920010, "geo_r2_chapter05", "第五章 环境与发展", 1, SUBJECT, 920005),

    # 节域层
    (920011, "geo_r2_section01", "第一节 人口分布", 1, SUBJECT, 920006),
    (920012, "geo_r2_section02", "第二节 人口迁移", 2, SUBJECT, 920006),
    (920013, "geo_r2_section03", "第三节 人口容量", 3, SUBJECT, 920006),
    (920014, "geo_r2_section04", "第一节 乡村和城镇空间结构", 1, SUBJECT, 920007),
    (920015, "geo_r2_section05", "第二节 城镇化", 2, SUBJECT, 920007),
    (920016, "geo_r2_section06", "第三节 地域文化与城乡景观", 3, SUBJECT, 920007),
    (920017, "geo_r2_section07", "第一节 农业区位因素及其变化", 1, SUBJECT, 920008),
    (920018, "geo_r2_section08", "第二节 工业区位因素及其变化", 2, SUBJECT, 920008),
    (920019, "geo_r2_section09", "第三节 服务业区位因素及其变化", 3, SUBJECT, 920008),
    (920020, "geo_r2_section10", "第一节 区域发展对交通运输布局的影响", 1, SUBJECT, 920009),
    (920021, "geo_r2_section11", "第二节 交通运输布局对区域发展的影响", 2, SUBJECT, 920009),
    (920022, "geo_r2_section12", "第一节 人类面临的主要环境问题", 1, SUBJECT, 920010),
    (920023, "geo_r2_section13", "第二节 走向人地协调——可持续发展", 2, SUBJECT, 920010),
    (920024, "geo_r2_section14", "第三节 中国国家发展战略举例", 3, SUBJECT, 920010),

    # 第一章考点：人口分布、人口迁移与人口容量
    (920031, "geo_r2_point_population_pattern", "世界人口分布规律：北半球中低纬沿海平原及东亚、南亚、欧洲、北美稠密区", 1, SUBJECT, 920011),
    (920032, "geo_r2_point_population_nature", "影响人口分布的自然因素：气候、地形、水源、土壤与矿产资源", 2, SUBJECT, 920011),
    (920033, "geo_r2_point_population_society", "影响人口分布的社会经济因素：生产力水平、交通条件、开发历史与政策", 3, SUBJECT, 920011),
    (920034, "geo_r2_point_hu_line", "中国人口分布：胡焕庸线及东南半壁稠密、西北半壁稀疏的格局", 4, SUBJECT, 920011),
    (920035, "geo_r2_point_population_density", "人口密度与分布差异：密度计算、稠密区与稀疏区的对比分析", 5, SUBJECT, 920011),
    (920036, "geo_r2_point_population_environment", "人口分布与地理环境：适宜区开发强度与生态脆弱区人口调控", 6, SUBJECT, 920011),
    (920037, "geo_r2_point_migration_concept", "人口迁移的判定：居住地变更、时间跨度与空间跨越三个条件", 1, SUBJECT, 920012),
    (920038, "geo_r2_point_migration_international", "国际人口迁移：二战前后流向变化、劳务输出与难民问题", 2, SUBJECT, 920012),
    (920039, "geo_r2_point_migration_china", "中国国内人口迁移：闯关东、改革开放民工潮与就近城镇化", 3, SUBJECT, 920012),
    (920040, "geo_r2_point_push_pull", "推拉理论：迁出地推力、迁入地拉力、中间障碍与个人因素", 4, SUBJECT, 920012),
    (920041, "geo_r2_point_migration_factors", "影响人口迁移的因素：经济、政治、社会文化、生态环境与个人决策", 5, SUBJECT, 920012),
    (920042, "geo_r2_point_migration_impact", "人口迁移的影响：对迁出地与迁入地的社会经济和资源环境双重效应", 6, SUBJECT, 920012),
    (920043, "geo_r2_point_carrying_capacity", "资源环境承载力：概念、资源短板效应与生态阈值", 1, SUBJECT, 920013),
    (920044, "geo_r2_point_environment_capacity", "环境人口容量：概念、影响因素与估算的不确定性", 2, SUBJECT, 920013),
    (920045, "geo_r2_point_reasonable_capacity", "人口合理容量：定义及其与环境人口容量的区别", 3, SUBJECT, 920013),
    (920046, "geo_r2_point_capacity_factors", "影响人口容量的因素：自然资源、科技水平、消费水平与对外开放程度", 4, SUBJECT, 920013),
    (920047, "geo_r2_point_capacity_pressure", "人口容量与区域发展：人口压力、资源短缺与适度人口调控", 5, SUBJECT, 920013),
    (920048, "geo_r2_point_china_population_policy", "我国人口政策与人口容量：计划生育、三孩政策与人口长期均衡发展", 6, SUBJECT, 920013),

    # 第二章考点：城乡空间结构、城镇化与地域文化景观
    (920049, "geo_r2_point_rural_landuse", "乡村土地利用与功能空间：居住、生产、公共服务与生态空间", 1, SUBJECT, 920014),
    (920050, "geo_r2_point_rural_form", "乡村空间形态：团块状、带状、分散状聚落及其影响因素", 2, SUBJECT, 920014),
    (920051, "geo_r2_point_urban_function", "城镇内部功能分区：商业区、住宅区、工业区的区位特征", 3, SUBJECT, 920014),
    (920052, "geo_r2_point_urban_model", "城镇空间结构模式：同心圆模式、扇形模式与多核心模式", 4, SUBJECT, 920014),
    (920053, "geo_r2_point_urban_structure_change", "城镇空间结构的形成与变化：地租、交通、历史与环境因素", 5, SUBJECT, 920014),
    (920054, "geo_r2_point_urbanization_concept", "城镇化的概念与标志：城镇人口比重、用地扩张与生活方式转变", 1, SUBJECT, 920015),
    (920055, "geo_r2_point_urbanization_stage", "世界城镇化进程：起步、加速与成熟阶段的S形曲线", 2, SUBJECT, 920015),
    (920056, "geo_r2_point_urbanization_compare", "发达国家与发展中国家城镇化差异：水平、速度、郊区化与逆城市化", 3, SUBJECT, 920015),
    (920057, "geo_r2_point_china_urbanization", "中国城镇化道路：新型城镇化、城市群与城乡融合发展", 4, SUBJECT, 920015),
    (920058, "geo_r2_point_urbanization_impact", "城镇化对地理环境的影响：热岛效应、内涝、污染与耕地占用", 5, SUBJECT, 920015),
    (920059, "geo_r2_point_urban_problems", "城镇化问题与对策：交通拥堵、住房紧张、环境污染与智慧城市建设", 6, SUBJECT, 920015),
    (920060, "geo_r2_point_regional_culture", "地域文化的内涵：物质文化、制度文化与精神文化的地域差异", 1, SUBJECT, 920016),
    (920061, "geo_r2_point_rural_landscape", "地域文化在乡村景观中的体现：民居、聚落形态与农业生产方式", 2, SUBJECT, 920016),
    (920062, "geo_r2_point_urban_landscape", "地域文化在城镇景观中的体现：建筑风格、街区格局与公共空间", 3, SUBJECT, 920016),
    (920063, "geo_r2_point_landscape_protection", "城乡景观保护与开发：历史文化名城、传统村落与活化利用", 4, SUBJECT, 920016),

    # 第三章考点：农业、工业与服务业区位
    (920064, "geo_r2_point_agriculture_nature", "农业自然区位因素：气候、地形、土壤与水源对农业类型的制约", 1, SUBJECT, 920017),
    (920065, "geo_r2_point_agriculture_society", "农业社会经济区位因素：市场、交通、政策、劳动力与技术", 2, SUBJECT, 920017),
    (920066, "geo_r2_point_agriculture_choice", "农业区位选择：因地制宜原则与主导区位因素分析", 3, SUBJECT, 920017),
    (920067, "geo_r2_point_agriculture_change", "农业区位因素的变化：市场需求、交通条件、科技与冷链保鲜", 4, SUBJECT, 920017),
    (920068, "geo_r2_point_agriculture_types", "主要农业地域类型：季风水田、商品谷物、大牧场放牧与混合农业", 5, SUBJECT, 920017),
    (920069, "geo_r2_point_agriculture_sustainable", "农业可持续发展：生态农业、循环农业与专业化规模化经营", 6, SUBJECT, 920017),
    (920070, "geo_r2_point_industry_factors", "工业区位因素：原料、动力、劳动力、市场与交通运输", 1, SUBJECT, 920018),
    (920071, "geo_r2_point_industry_orientation", "工业区位选择：原料导向、市场导向、动力导向、劳动力导向与技术导向", 2, SUBJECT, 920018),
    (920072, "geo_r2_point_industry_change", "工业区位因素的变化：交通技术进步、原料替代与信息网络", 3, SUBJECT, 920018),
    (920073, "geo_r2_point_industry_cluster", "工业集聚与分散：规模效益、产业链协作与污染治理", 4, SUBJECT, 920018),
    (920074, "geo_r2_point_industry_sustainable", "工业可持续发展：清洁生产、循环经济与产业转型升级", 5, SUBJECT, 920018),
    (920075, "geo_r2_point_service_types", "服务业类型与区位因素：生产性服务业、生活性服务业与公共服务", 1, SUBJECT, 920019),
    (920076, "geo_r2_point_commerce_location", "商业服务业区位：市场最优、交通最优与集聚效应", 2, SUBJECT, 920019),
    (920077, "geo_r2_point_service_change", "服务业区位变化：电子商务、网络平台与现代物流的影响", 3, SUBJECT, 920019),

    # 第四章考点：交通运输布局与区域发展
    (920078, "geo_r2_point_transport_principles", "交通运输布局原则：适应需求、因地制宜、尽量直达与少占耕地", 1, SUBJECT, 920020),
    (920079, "geo_r2_point_transport_economy", "区域发展水平对交通布局的影响：经济实力、资金技术与运输需求", 2, SUBJECT, 920020),
    (920080, "geo_r2_point_transport_nature", "自然条件对交通布局的制约：地形、地质、气候与水文", 3, SUBJECT, 920020),
    (920081, "geo_r2_point_transport_modes", "五种交通运输方式比较：铁路、公路、水运、航空与管道", 4, SUBJECT, 920020),
    (920082, "geo_r2_point_transport_hub", "交通枢纽与网络：港口、机场、铁路枢纽与综合立体交通网", 5, SUBJECT, 920020),
    (920083, "geo_r2_point_transport_growth", "交通运输对区域经济的促进：降低运费、扩大市场与产业集聚", 1, SUBJECT, 920021),
    (920084, "geo_r2_point_transport_settlement", "交通运输对聚落形态的影响：沿河沿路布局与交通轴线发展", 2, SUBJECT, 920021),
    (920085, "geo_r2_point_transport_commerce", "交通运输对商业网点与人口流动的影响：市场范围与通勤出行", 3, SUBJECT, 920021),
    (920086, "geo_r2_point_transport_coordination", "交通运输与区域协调发展：扶贫公路、一带一路与枢纽经济", 4, SUBJECT, 920021),

    # 第五章考点：环境问题、可持续发展与国家发展战略
    (920087, "geo_r2_point_environment_cause", "环境问题的产生：人类活动超过环境承载力与资源过度消耗", 1, SUBJECT, 920022),
    (920088, "geo_r2_point_environment_pollution", "环境污染问题：大气污染、水污染、土壤污染与固体废弃物污染", 2, SUBJECT, 920022),
    (920089, "geo_r2_point_environment_ecology", "生态破坏问题：森林减少、土地荒漠化、水土流失与生物多样性减少", 3, SUBJECT, 920022),
    (920090, "geo_r2_point_environment_resource", "资源枯竭问题：矿产资源、水资源与耕地资源紧张", 4, SUBJECT, 920022),
    (920091, "geo_r2_point_environment_difference", "环境问题的地域差异与全球性：城乡差异、南北差异与跨国界影响", 5, SUBJECT, 920022),
    (920092, "geo_r2_point_sustainability_concept", "可持续发展内涵：生态持续、经济持续与社会持续三个维度", 1, SUBJECT, 920023),
    (920093, "geo_r2_point_sustainability_principles", "可持续发展原则：公平性、持续性、共同性与阶段性", 2, SUBJECT, 920023),
    (920094, "geo_r2_point_human_nature_view", "人地关系思想演变：地理环境决定论、可能论与人地协调论", 3, SUBJECT, 920023),
    (920095, "geo_r2_point_sustainability_practice", "可持续发展实践：清洁生产、绿色消费、低碳生活与国际合作", 4, SUBJECT, 920023),
    (920096, "geo_r2_point_functional_zones", "主体功能区战略：优化开发、重点开发、限制开发与禁止开发区域", 1, SUBJECT, 920024),
    (920097, "geo_r2_point_regional_coordination", "区域协调发展战略：西部开发、东北振兴、中部崛起与东部率先", 2, SUBJECT, 920024),
    (920098, "geo_r2_point_rural_revitalization", "乡村振兴与新型城镇化战略：城乡融合、产业兴旺与生态宜居", 3, SUBJECT, 920024),
    (920099, "geo_r2_point_major_regions", "国家重大区域战略：京津冀协同、长江经济带、粤港澳大湾区与黄河流域生态保护", 4, SUBJECT, 920024),
)

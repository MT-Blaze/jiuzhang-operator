"""人教版（2019）高中地理选择性必修第二册（区域发展）：章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 9
G10 = 10
BOOK_ID = 9204

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中地理选择性必修第二册（区域发展）",
    "geo_e2",
    4,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (940101, "第一章 区域与区域发展", "geo_e2_u01", 1, BOOK_ID, None),
    (940102, "第二章 资源、环境与区域发展", "geo_e2_u02", 2, BOOK_ID, None),
    (940103, "第三章 城市、产业与区域发展", "geo_e2_u03", 3, BOOK_ID, None),
    (940104, "第四章 区际联系与区域协调发展", "geo_e2_u04", 4, BOOK_ID, None),
    (940111, "第一节 多种多样的区域", "geo_e2_l01", 1, BOOK_ID, 940101),
    (940112, "第二节 区域整体性和关联性", "geo_e2_l02", 2, BOOK_ID, 940101),
    (940113, "第一节 区域发展的自然环境基础", "geo_e2_l03", 1, BOOK_ID, 940102),
    (940114, "第二节 生态脆弱区的综合治理", "geo_e2_l04", 2, BOOK_ID, 940102),
    (940115, "第三节 资源枯竭型城市的转型发展", "geo_e2_l05", 3, BOOK_ID, 940102),
    (940116, "第一节 城市的辐射功能", "geo_e2_l06", 1, BOOK_ID, 940103),
    (940117, "第二节 地区产业结构变化", "geo_e2_l07", 2, BOOK_ID, 940103),
    (940118, "第一节 流域内协调发展", "geo_e2_l08", 1, BOOK_ID, 940104),
    (940119, "第二节 资源跨区域调配", "geo_e2_l09", 2, BOOK_ID, 940104),
    (940120, "第三节 产业转移", "geo_e2_l10", 3, BOOK_ID, 940104),
    (940121, "第四节 国际合作", "geo_e2_l11", 4, BOOK_ID, 940104),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 94 00 01-04 为册域，94 00 05-08 为章域，94 00 09-19 为节域；94 00 21-97 为考点层。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (940001, "geo_e2_domain_region", "区域与区域发展：区域划分、整体性与关联性", 1, SUBJECT, G10, None),
    (940002, "geo_e2_domain_resource", "资源、环境与区域发展：自然基础、生态治理与城市转型", 2, SUBJECT, G10, None),
    (940003, "geo_e2_domain_city_industry", "城市、产业与区域发展：辐射功能与产业结构升级", 3, SUBJECT, G10, None),
    (940004, "geo_e2_domain_interregional", "区际联系与区域协调发展：流域、资源调配、产业转移与国际合作", 4, SUBJECT, G10, None),

    # 章域层
    (940005, "geo_e2_chapter01", "第一章 区域与区域发展", 1, SUBJECT, G10, 940001),
    (940006, "geo_e2_chapter02", "第二章 资源、环境与区域发展", 1, SUBJECT, G10, 940002),
    (940007, "geo_e2_chapter03", "第三章 城市、产业与区域发展", 1, SUBJECT, G10, 940003),
    (940008, "geo_e2_chapter04", "第四章 区际联系与区域协调发展", 1, SUBJECT, G10, 940004),

    # 节域层
    (940009, "geo_e2_section01", "第一节 多种多样的区域", 1, SUBJECT, G10, 940005),
    (940010, "geo_e2_section02", "第二节 区域整体性和关联性", 2, SUBJECT, G10, 940005),
    (940011, "geo_e2_section03", "第一节 区域发展的自然环境基础", 1, SUBJECT, G10, 940006),
    (940012, "geo_e2_section04", "第二节 生态脆弱区的综合治理", 2, SUBJECT, G10, 940006),
    (940013, "geo_e2_section05", "第三节 资源枯竭型城市的转型发展", 3, SUBJECT, G10, 940006),
    (940014, "geo_e2_section06", "第一节 城市的辐射功能", 1, SUBJECT, G10, 940007),
    (940015, "geo_e2_section07", "第二节 地区产业结构变化", 2, SUBJECT, G10, 940007),
    (940016, "geo_e2_section08", "第一节 流域内协调发展", 1, SUBJECT, G10, 940008),
    (940017, "geo_e2_section09", "第二节 资源跨区域调配", 2, SUBJECT, G10, 940008),
    (940018, "geo_e2_section10", "第三节 产业转移", 3, SUBJECT, G10, 940008),
    (940019, "geo_e2_section11", "第四节 国际合作", 4, SUBJECT, G10, 940008),

    # 第一章第一节考点：区域的内涵、类型与尺度
    (940021, "geo_e2_point_region_concept", "区域的内涵与基本特征：一定空间范围、可度量边界、内部相对一致性与层级性", 1, SUBJECT, G10, 940009),
    (940022, "geo_e2_point_region_division", "区域划分的目的与依据：因地制宜、便于管理与研究，按自然与人文要素差异划分", 2, SUBJECT, G10, 940009),
    (940023, "geo_e2_point_natural_region", "自然区域的划分：气候、地形、水文、植被、土壤等自然要素的地域分异", 3, SUBJECT, G10, 940009),
    (940024, "geo_e2_point_admin_region", "行政区域的划分与层级：省—市—县—乡四级，边界明确、具有管理职能", 4, SUBJECT, G10, 940009),
    (940025, "geo_e2_point_economic_region", "经济区域的划分：以经济联系和产业分工为基础，边界具有过渡性与开放性", 5, SUBJECT, G10, 940009),
    (940026, "geo_e2_point_cultural_region", "文化区域的划分：语言、宗教、风俗与建筑等文化要素的空间差异", 6, SUBJECT, G10, 940009),
    (940027, "geo_e2_point_region_scale", "区域的空间尺度与层级：全球—大洲—国家—地区—地方，尺度不同关注重点不同", 7, SUBJECT, G10, 940009),

    # 第一章第二节考点：整体性与关联性
    (940028, "geo_e2_point_integrity_concept", "区域整体性的含义：区域内各要素相互联系、相互制约，构成统一整体", 1, SUBJECT, G10, 940010),
    (940029, "geo_e2_point_integrity_expression", "区域整体性的表现：要素变化牵一发而动全身，如植被破坏引发水土流失", 2, SUBJECT, G10, 940010),
    (940030, "geo_e2_point_linkage_concept", "区域关联性的含义与基础：区域间物质、能量、信息交流，源于差异与互补", 3, SUBJECT, G10, 940010),
    (940031, "geo_e2_point_linkage_forms", "区域关联的主要形式：人口迁移、货物贸易、资本与技术流动、信息传播", 4, SUBJECT, G10, 940010),
    (940032, "geo_e2_point_region_complement", "区域差异与区域互补：资源禀赋与产业优势不同，形成分工与协作基础", 5, SUBJECT, G10, 940010),
    (940033, "geo_e2_point_coordinated_governance", "区域协调发展与协同治理：打破行政壁垒，共建基础设施与生态治理", 6, SUBJECT, G10, 940010),

    # 第二章第一节考点：区域发展的自然环境基础
    (940034, "geo_e2_point_natural_resource_base", "自然资源对区域发展的基础作用：提供物质与能量，影响产业类型与布局", 1, SUBJECT, G10, 940011),
    (940035, "geo_e2_point_natural_env_impact", "自然环境对区域发展的影响：气候、地形、水文决定农业、交通与聚落格局", 2, SUBJECT, G10, 940011),
    (940036, "geo_e2_point_natural_evaluation", "区域自然条件评价：从光热水土、地形、资源组合与灾害风险综合评判", 3, SUBJECT, G10, 940011),
    (940037, "geo_e2_point_endowment_structure", "资源禀赋与区域产业结构：资源富集区易形成资源型产业与单一结构", 4, SUBJECT, G10, 940011),
    (940038, "geo_e2_point_carrying_capacity", "区域生态环境承载力：资源环境对人口与经济规模的支撑与约束", 5, SUBJECT, G10, 940011),
    (940039, "geo_e2_point_man_land_coordination", "人地关系协调与区域可持续发展：开发强度不超过资源环境承载力", 6, SUBJECT, G10, 940011),

    # 第二章第二节考点：生态脆弱区的综合治理（高频）
    (940040, "geo_e2_point_fragile_concept", "生态脆弱区的概念与特征：生态系统稳定性差、抗干扰能力弱、易退化难恢复", 1, SUBJECT, G10, 940012),
    (940041, "geo_e2_point_fragile_distribution", "我国生态脆弱区的分布：干旱半干旱区、黄土高原、西南喀斯特、南方红壤丘陵", 2, SUBJECT, G10, 940012),
    (940042, "geo_e2_point_fragile_cause", "生态脆弱区的形成原因：自然因素（气候干旱、地形起伏、土质疏松）与人为因素", 3, SUBJECT, G10, 940012),
    (940043, "geo_e2_point_desertification_concept", "荒漠化的概念与类型：土地退化现象，含风蚀、水蚀、盐渍化与冻融荒漠化", 4, SUBJECT, G10, 940012),
    (940044, "geo_e2_point_desertification_cause", "我国西北荒漠化的成因：深居内陆干旱多风、过度开垦放牧樵采与水资源利用不当", 5, SUBJECT, G10, 940012),
    (940045, "geo_e2_point_desertification_harm", "荒漠化的危害：土地生产力下降、沙尘暴频发、生态退化与经济损失", 6, SUBJECT, G10, 940012),
    (940046, "geo_e2_point_desertification_control", "荒漠化综合治理措施：生物措施（植树种草、草方格沙障）、工程措施与合理用水", 7, SUBJECT, G10, 940012),
    (940047, "geo_e2_point_soil_erosion_loess", "黄土高原水土流失的成因与治理：土质疏松暴雨集中，修梯田、打坝淤地、退耕还林", 8, SUBJECT, G10, 940012),
    (940048, "geo_e2_point_rocky_salinization", "石漠化与盐碱化的治理：喀斯特地区封山育林、盐碱地排灌洗盐与生物改良", 9, SUBJECT, G10, 940012),

    # 第二章第三节考点：资源枯竭型城市转型
    (940049, "geo_e2_point_exhausted_concept", "资源枯竭型城市的概念与判定：主导资源趋于枯竭、开采成本上升、经济衰退", 1, SUBJECT, G10, 940013),
    (940050, "geo_e2_point_resource_city_lifecycle", "资源型城市的发展生命周期：兴起—成长—成熟—衰退（或转型）四阶段", 2, SUBJECT, G10, 940013),
    (940051, "geo_e2_point_exhausted_problems", "资源枯竭型城市面临的问题：产业单一、失业增加、生态破坏与财政困难", 3, SUBJECT, G10, 940013),
    (940052, "geo_e2_point_exhausted_path", "资源枯竭型城市的转型路径：延长产业链、培育接续替代产业、发展第三产业", 4, SUBJECT, G10, 940013),
    (940053, "geo_e2_point_substitute_industry", "接续替代产业的选择原则：立足本地优势、市场需求导向、就业容量与生态友好", 5, SUBJECT, G10, 940013),
    (940054, "geo_e2_point_exhausted_restoration", "资源枯竭型城市的生态修复与民生保障：矿山地质环境治理、棚户区改造与再就业", 6, SUBJECT, G10, 940013),
    (940055, "geo_e2_point_exhausted_cases", "典型资源枯竭型城市转型案例：阜新煤炭、焦作煤炭、大庆石油、个旧锡矿", 7, SUBJECT, G10, 940013),

    # 第三章第一节考点：城市的辐射功能
    (940056, "geo_e2_point_city_radiate_concept", "城市功能与辐射功能的含义：集聚与扩散，向周边提供产品、服务、技术与就业", 1, SUBJECT, G10, 940014),
    (940057, "geo_e2_point_radiate_factors", "城市辐射范围与强度的影响因素：经济实力、产业层次、交通通信与开放程度", 2, SUBJECT, G10, 940014),
    (940058, "geo_e2_point_city_hierarchy", "城市等级与服务范围：等级越高服务种类越多、门槛人口越大、服务范围越广", 3, SUBJECT, G10, 940014),
    (940059, "geo_e2_point_hinterland", "城市腹地与经济联系：腹地为城市提供原料市场，城市向腹地输出服务与产品", 4, SUBJECT, G10, 940014),
    (940060, "geo_e2_point_transport_radiate", "交通通信条件对城市辐射的影响：缩短时空距离、扩大市场与要素流动范围", 5, SUBJECT, G10, 940014),
    (940061, "geo_e2_point_metropolitan_area", "都市圈与城市群的辐射带动：核心城市引领、圈层分工与基础设施互联互通", 6, SUBJECT, G10, 940014),
    (940062, "geo_e2_point_radiate_cases", "城市辐射功能典型案例：上海对长三角、纽约对全球金融与生产性服务辐射", 7, SUBJECT, G10, 940014),

    # 第三章第二节考点：地区产业结构变化
    (940063, "geo_e2_point_structure_concept", "产业结构的含义与分类：三次产业划分及各产业内部结构", 1, SUBJECT, G10, 940015),
    (940064, "geo_e2_point_structure_evolution", "区域产业结构的演进规律：由第一产业为主向二、三产业为主，向高级化演进", 2, SUBJECT, G10, 940015),
    (940065, "geo_e2_point_structure_factors", "影响区域产业结构变化的因素：资源禀赋、市场需求、技术进步、政策与交通", 3, SUBJECT, G10, 940015),
    (940066, "geo_e2_point_structure_upgrade", "产业结构升级的表现：主导产业更替、技术含量提高、附加值提升与就业结构变化", 4, SUBJECT, G10, 940015),
    (940067, "geo_e2_point_structure_transform", "区域产业转型的路径：传统产业改造、新兴产业发展、现代服务业培育", 5, SUBJECT, G10, 940015),
    (940068, "geo_e2_point_structure_evaluation", "区域产业结构优化的评价：合理化（比例协调）与高级化（技术层次提升）", 6, SUBJECT, G10, 940015),
    (940069, "geo_e2_point_structure_cases", "地区产业结构变化案例：珠三角加工贸易升级、温州模式与东北老工业基地调整", 7, SUBJECT, G10, 940015),

    # 第四章第一节考点：流域内协调发展
    (940070, "geo_e2_point_basin_integrity", "流域的整体性与流域开发：以分水岭为界，上中下游相互影响、需统一规划", 1, SUBJECT, G10, 940016),
    (940071, "geo_e2_point_basin_evaluation", "流域开发条件的综合评价：地形、气候、水文、资源与区位交通", 2, SUBJECT, G10, 940016),
    (940072, "geo_e2_point_basin_coordination", "流域上中下游的协调开发：上游生态保护、中游防洪治沙、下游航运与湿地保护", 3, SUBJECT, G10, 940016),
    (940073, "geo_e2_point_water_dispatch", "流域水资源的统一调度：统筹生活生产生态用水、跨区域调水与水量分配", 4, SUBJECT, G10, 940016),
    (940074, "geo_e2_point_eco_compensation", "流域生态补偿机制：受益区对保护区的资金、技术与产业补偿", 5, SUBJECT, G10, 940016),
    (940075, "geo_e2_point_basin_management", "流域综合管理的体制与措施：流域管理机构、河长制、法律法规与监测预警", 6, SUBJECT, G10, 940016),
    (940076, "geo_e2_point_basin_cases", "流域内协调发展案例：田纳西河流域综合开发、黄河流域生态保护和高质量发展", 7, SUBJECT, G10, 940016),

    # 第四章第二节考点：资源跨区域调配
    (940077, "geo_e2_point_allocation_reason", "资源跨区域调配的原因：资源分布与需求空间不匹配、区域发展不平衡", 1, SUBJECT, G10, 940017),
    (940078, "geo_e2_point_allocation_meaning", "资源跨区域调配的意义：优化资源配置、缓解供需矛盾、促进区域协调发展", 2, SUBJECT, G10, 940017),
    (940079, "geo_e2_point_west_gas", "西气东输工程：一线二线三线走向、塔里木盆地气源与东部消费市场", 3, SUBJECT, G10, 940017),
    (940080, "geo_e2_point_west_electricity", "西电东送工程：北中南三通道、火电水电基地与东部负荷中心", 4, SUBJECT, G10, 940017),
    (940081, "geo_e2_point_south_water", "南水北调工程：东线、中线、西线方案，缓解华北西北缺水及其生态影响", 5, SUBJECT, G10, 940017),
    (940082, "geo_e2_point_allocation_source_impact", "资源调配对调出区的影响：资源开发带动经济，但可能加剧生态压力与资源耗竭", 6, SUBJECT, G10, 940017),
    (940083, "geo_e2_point_allocation_target_impact", "资源调配对调入区的影响：缓解资源短缺，需配套节约利用与污染防治", 7, SUBJECT, G10, 940017),

    # 第四章第三节考点：产业转移（高频）
    (940084, "geo_e2_point_transfer_concept", "产业转移的概念与类型：企业将生产环节迁至他地，含国际转移与区际转移", 1, SUBJECT, G10, 940018),
    (940085, "geo_e2_point_transfer_forces", "产业转移的推力与拉力：转出地成本上升、市场饱和；转入地成本低、政策优惠", 2, SUBJECT, G10, 940018),
    (940086, "geo_e2_point_transfer_pattern", "产业转移的规律与方向：劳动密集型由发达向欠发达、由沿海向内陆梯次转移", 3, SUBJECT, G10, 940018),
    (940087, "geo_e2_point_transfer_out_impact", "产业转移对转出区的影响：腾出空间发展高端产业，但可能产业空心化与失业", 4, SUBJECT, G10, 940018),
    (940088, "geo_e2_point_transfer_in_impact", "产业转移对转入区的影响：增加就业与税收、促进工业化，但资源环境压力加大", 5, SUBJECT, G10, 940018),
    (940089, "geo_e2_point_transfer_division", "产业转移与区域分工协作：形成研发—制造—销售的地域分工与产业链协同", 6, SUBJECT, G10, 940018),
    (940090, "geo_e2_point_transfer_trend", "国际产业转移的趋势：由制造业转移向服务业与研发环节转移、本地化布局", 7, SUBJECT, G10, 940018),
    (940091, "geo_e2_point_transfer_cases", "我国产业转移的典型案例：珠三角向粤东西北、长三角向中西部转移", 8, SUBJECT, G10, 940018),

    # 第四章第四节考点：国际合作
    (940092, "geo_e2_point_cooperation_background", "国际合作的背景与意义：经济全球化与资源环境问题跨国界，需共同应对", 1, SUBJECT, G10, 940019),
    (940093, "geo_e2_point_cooperation_forms", "国际经济合作的主要形式：贸易、投资、技术合作、工程承包与劳务合作", 2, SUBJECT, G10, 940019),
    (940094, "geo_e2_point_belt_road", "“一带一路”倡议与区域合作：政策沟通、设施联通、贸易畅通、资金融通、民心相通", 3, SUBJECT, G10, 940019),
    (940095, "geo_e2_point_integration", "区域经济一体化组织：欧盟、东盟、北美自贸区等关税同盟与共同市场", 4, SUBJECT, G10, 940019),
    (940096, "geo_e2_point_global_value_chain", "全球产业链与价值链分工：发达国家占据研发品牌、发展中国家承担加工制造", 5, SUBJECT, G10, 940019),
    (940097, "geo_e2_point_cooperation_challenge", "国际合作中的挑战与共赢：发展差距、贸易摩擦与规则协调，坚持互利共赢", 6, SUBJECT, G10, 940019),
)

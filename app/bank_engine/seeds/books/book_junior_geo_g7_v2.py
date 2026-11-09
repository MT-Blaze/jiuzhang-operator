"""人教版初中地理七年级下册：亚洲、邻近地区和国家、东半球与西半球国家、极地地区。"""

from __future__ import annotations

SUBJECT = 9
G7 = 7
BOOK_ID = 1340

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版七年级地理下册",
    "jgeo_g7b",
    40,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (134001, "人教版七年级地理下册", "jgeo_g7b_root", 1, BOOK_ID, None),

    (134002, "第六章 我们生活的大洲——亚洲", "jgeo_g7b_c06", 6, BOOK_ID, 134001),
    (134011, "第一节 位置和范围", "jgeo_g7b_c06_s01", 1, BOOK_ID, 134002),
    (134012, "第二节 地形与河流", "jgeo_g7b_c06_s02", 2, BOOK_ID, 134002),
    (134013, "第三节 复杂的气候", "jgeo_g7b_c06_s03", 3, BOOK_ID, 134002),
    (134014, "第四节 人口与文化", "jgeo_g7b_c06_s04", 4, BOOK_ID, 134002),

    (134003, "第七章 我们邻近的地区和国家", "jgeo_g7b_c07", 7, BOOK_ID, 134001),
    (134021, "第一节 日本", "jgeo_g7b_c07_s01", 1, BOOK_ID, 134003),
    (134022, "第二节 东南亚", "jgeo_g7b_c07_s02", 2, BOOK_ID, 134003),
    (134023, "第三节 印度", "jgeo_g7b_c07_s03", 3, BOOK_ID, 134003),
    (134024, "第四节 俄罗斯", "jgeo_g7b_c07_s04", 4, BOOK_ID, 134003),

    (134004, "第八章 东半球其他的地区和国家", "jgeo_g7b_c08", 8, BOOK_ID, 134001),
    (134031, "第一节 中东", "jgeo_g7b_c08_s01", 1, BOOK_ID, 134004),
    (134032, "第二节 欧洲西部", "jgeo_g7b_c08_s02", 2, BOOK_ID, 134004),
    (134033, "第三节 撒哈拉以南非洲", "jgeo_g7b_c08_s03", 3, BOOK_ID, 134004),
    (134034, "第四节 澳大利亚", "jgeo_g7b_c08_s04", 4, BOOK_ID, 134004),

    (134005, "第九章 西半球的国家", "jgeo_g7b_c09", 9, BOOK_ID, 134001),
    (134041, "第一节 美国的自然环境与农业", "jgeo_g7b_c09_s01", 1, BOOK_ID, 134005),
    (134042, "第二节 美国的工业、城市与高新技术产业", "jgeo_g7b_c09_s02", 2, BOOK_ID, 134005),
    (134043, "第三节 巴西的自然环境与热带雨林", "jgeo_g7b_c09_s03", 3, BOOK_ID, 134005),
    (134044, "第四节 巴西的人口、城市与经济", "jgeo_g7b_c09_s04", 4, BOOK_ID, 134005),

    (134006, "第十章 极地地区", "jgeo_g7b_c10", 10, BOOK_ID, 134001),
    (134051, "第一节 极地地区的自然环境", "jgeo_g7b_c10_s01", 1, BOOK_ID, 134006),
    (134052, "第二节 极地科学考察与环境保护", "jgeo_g7b_c10_s02", 2, BOOK_ID, 134006),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 240001 册域顶层，240002-240099 为章、节锚点与细颗粒考点；父节点全部先于子节点登记。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    (240001, "jgeo_g7b_domain", "初中七下·地理·亚洲·邻近的地区和国家·东半球其他的地区和国家·西半球的国家·极地地区", 1, SUBJECT, G7, None),

    # 第六章 我们生活的大洲——亚洲
    (240002, "jgeo_g7b_c06", "初中七下·地理·第六章 我们生活的大洲——亚洲", 6, SUBJECT, G7, 240001),
    (240003, "jgeo_g7b_c06_s01", "第一节 位置和范围", 1, SUBJECT, G7, 240002),
    (240004, "jgeo_g7b_asia_hemisphere", "亚洲的半球位置：主要位于东半球和北半球", 1, SUBJECT, G7, 240003),
    (240005, "jgeo_g7b_asia_latitude", "亚洲的纬度位置：地跨寒、温、热三带", 2, SUBJECT, G7, 240003),
    (240006, "jgeo_g7b_asia_area", "亚洲是世界第一大洲：面积约4400万平方千米", 3, SUBJECT, G7, 240003),
    (240007, "jgeo_g7b_asia_regions", "亚洲的六大分区与不同区域的自然人文差异", 4, SUBJECT, G7, 240003),
    (240008, "jgeo_g7b_c06_s02", "第二节 地形与河流", 2, SUBJECT, G7, 240002),
    (240009, "jgeo_g7b_asia_terrain", "亚洲地形特点：以高原、山地为主，中间高、四周低", 1, SUBJECT, G7, 240008),
    (240010, "jgeo_g7b_asia_relief", "亚洲主要地形区：青藏高原、喜马拉雅山脉、西西伯利亚平原", 2, SUBJECT, G7, 240008),
    (240011, "jgeo_g7b_asia_river", "亚洲河流呈放射状分布及长江、黄河、湄公河的水文特点", 3, SUBJECT, G7, 240008),
    (240012, "jgeo_g7b_asia_lake", "亚洲主要湖泊：里海、贝加尔湖、死海的特征", 4, SUBJECT, G7, 240008),
    (240013, "jgeo_g7b_c06_s03", "第三节 复杂的气候", 3, SUBJECT, G7, 240002),
    (240014, "jgeo_g7b_asia_climate", "亚洲气候复杂多样与温带大陆性气候分布广", 1, SUBJECT, G7, 240013),
    (240015, "jgeo_g7b_asia_monsoon", "亚洲季风气候显著：热带、亚热带和温带季风", 2, SUBJECT, G7, 240013),
    (240016, "jgeo_g7b_asia_climate_agri", "亚洲气候对农业生产与人口分布的影响", 3, SUBJECT, G7, 240013),
    (240017, "jgeo_g7b_c06_s04", "第四节 人口与文化", 4, SUBJECT, G7, 240002),
    (240018, "jgeo_g7b_asia_population_culture", "亚洲人口最多、增长快及多样的地域文化", 1, SUBJECT, G7, 240017),

    # 第七章 我们邻近的地区和国家
    (240019, "jgeo_g7b_c07", "初中七下·地理·第七章 我们邻近的地区和国家", 7, SUBJECT, G7, 240001),
    (240020, "jgeo_g7b_c07_s01", "第一节 日本", 1, SUBJECT, G7, 240019),
    (240021, "jgeo_g7b_japan_location", "日本的位置、领土组成与北海道、本州、四国、九州四大岛", 1, SUBJECT, G7, 240020),
    (240022, "jgeo_g7b_japan_terrain", "日本山地丘陵广布、平原狭小、海岸线曲折的地形特点", 2, SUBJECT, G7, 240020),
    (240023, "jgeo_g7b_japan_quake", "日本多火山地震的原因及防震减灾措施", 3, SUBJECT, G7, 240020),
    (240024, "jgeo_g7b_japan_industry", "日本进口原料、出口工业制成品的加工贸易经济与工业集中分布", 4, SUBJECT, G7, 240020),
    (240025, "jgeo_g7b_japan_culture", "日本东西方兼容的文化与东京等主要城市", 5, SUBJECT, G7, 240020),
    (240026, "jgeo_g7b_c07_s02", "第二节 东南亚", 2, SUBJECT, G7, 240019),
    (240027, "jgeo_g7b_sea_crossroad", "东南亚“十字路口”位置与马六甲海峡的重要性", 1, SUBJECT, G7, 240026),
    (240028, "jgeo_g7b_sea_range", "东南亚的范围：中南半岛与马来群岛", 2, SUBJECT, G7, 240026),
    (240029, "jgeo_g7b_sea_terrain", "中南半岛山河相间、纵列分布的地形特点", 3, SUBJECT, G7, 240026),
    (240030, "jgeo_g7b_sea_climate_crop", "东南亚热带雨林与热带季风气候及稻米生产", 4, SUBJECT, G7, 240026),
    (240031, "jgeo_g7b_sea_cash_crop", "东南亚热带经济作物：天然橡胶、油棕、椰子、蕉麻", 5, SUBJECT, G7, 240026),
    (240032, "jgeo_g7b_sea_city_tourism", "东南亚城市沿河分布的特点与丰富的旅游资源", 6, SUBJECT, G7, 240026),
    (240033, "jgeo_g7b_c07_s03", "第三节 印度", 3, SUBJECT, G7, 240019),
    (240034, "jgeo_g7b_india_location", "印度的位置、邻国与南亚面积最大的国家", 1, SUBJECT, G7, 240033),
    (240035, "jgeo_g7b_india_terrain", "印度三大地形区：北部山地、中部平原、南部高原", 2, SUBJECT, G7, 240033),
    (240036, "jgeo_g7b_india_monsoon", "印度热带季风气候与西南季风的不稳定性", 3, SUBJECT, G7, 240033),
    (240037, "jgeo_g7b_india_disaster", "印度水旱灾害频繁的原因及对农业生产的影响", 4, SUBJECT, G7, 240033),
    (240038, "jgeo_g7b_india_outsourcing", "印度服务外包产业的特点、发展条件与班加罗尔", 5, SUBJECT, G7, 240033),
    (240039, "jgeo_g7b_c07_s04", "第四节 俄罗斯", 4, SUBJECT, G7, 240019),
    (240040, "jgeo_g7b_russia_location", "俄罗斯跨亚欧两洲、世界面积最大的国家", 1, SUBJECT, G7, 240039),
    (240041, "jgeo_g7b_russia_terrain", "俄罗斯以平原和高原为主、地势东高西低的地形特点", 2, SUBJECT, G7, 240039),
    (240042, "jgeo_g7b_russia_river", "俄罗斯主要河流与伏尔加河的水运价值", 3, SUBJECT, G7, 240039),
    (240043, "jgeo_g7b_russia_climate", "俄罗斯温带大陆性气候显著与冬季漫长寒冷", 4, SUBJECT, G7, 240039),
    (240044, "jgeo_g7b_russia_industry", "俄罗斯丰富的自然资源与主要工业区分布", 5, SUBJECT, G7, 240039),
    (240045, "jgeo_g7b_russia_transport_city", "俄罗斯以铁路为主的交通运输与莫斯科、圣彼得堡等城市", 6, SUBJECT, G7, 240039),

    # 第八章 东半球其他的地区和国家
    (240046, "jgeo_g7b_c08", "初中七下·地理·第八章 东半球其他的地区和国家", 8, SUBJECT, G7, 240001),
    (240047, "jgeo_g7b_c08_s01", "第一节 中东", 1, SUBJECT, G7, 240046),
    (240048, "jgeo_g7b_me_location", "中东“两洋三洲五海之地”的位置", 1, SUBJECT, G7, 240047),
    (240049, "jgeo_g7b_me_oil", "中东石油资源的分布、主要产油国与输出路线", 2, SUBJECT, G7, 240047),
    (240050, "jgeo_g7b_me_water", "中东水资源匮乏的原因及水资源争夺", 3, SUBJECT, G7, 240047),
    (240051, "jgeo_g7b_me_culture", "中东文化差异与宗教、民族矛盾", 4, SUBJECT, G7, 240047),
    (240052, "jgeo_g7b_c08_s02", "第二节 欧洲西部", 2, SUBJECT, G7, 240046),
    (240053, "jgeo_g7b_eu_location", "欧洲西部的位置、范围与发达国家集中", 1, SUBJECT, G7, 240052),
    (240054, "jgeo_g7b_eu_climate", "欧洲西部温带海洋性气候的成因与特点", 2, SUBJECT, G7, 240052),
    (240055, "jgeo_g7b_eu_terrain", "欧洲西部以平原为主的地形与冰川作用地貌", 3, SUBJECT, G7, 240052),
    (240056, "jgeo_g7b_eu_husbandry", "欧洲西部畜牧业发达的原因", 4, SUBJECT, G7, 240052),
    (240057, "jgeo_g7b_eu_tourism", "欧洲西部发达的旅游业与主要旅游资源", 5, SUBJECT, G7, 240052),
    (240058, "jgeo_g7b_c08_s03", "第三节 撒哈拉以南非洲", 3, SUBJECT, G7, 240046),
    (240059, "jgeo_g7b_africa_location", "撒哈拉以南非洲的位置、范围与居民", 1, SUBJECT, G7, 240058),
    (240060, "jgeo_g7b_africa_terrain", "撒哈拉以南非洲以高原为主的地形", 2, SUBJECT, G7, 240058),
    (240061, "jgeo_g7b_africa_climate", "撒哈拉以南非洲热带草原气候与降水分布", 3, SUBJECT, G7, 240058),
    (240062, "jgeo_g7b_africa_river", "撒哈拉以南非洲的尼罗河、刚果河与赞比西河", 4, SUBJECT, G7, 240058),
    (240063, "jgeo_g7b_africa_economy", "单一商品经济的特点与弊端", 5, SUBJECT, G7, 240058),
    (240064, "jgeo_g7b_africa_problem", "非洲人口、粮食与环境问题", 6, SUBJECT, G7, 240058),
    (240065, "jgeo_g7b_c08_s04", "第四节 澳大利亚", 4, SUBJECT, G7, 240046),
    (240066, "jgeo_g7b_au_location", "澳大利亚的位置、领土组成与特有动物", 1, SUBJECT, G7, 240065),
    (240067, "jgeo_g7b_au_terrain", "澳大利亚三大地形区：西部高原、中部平原、东部山地", 2, SUBJECT, G7, 240065),
    (240068, "jgeo_g7b_au_climate", "澳大利亚半环状气候分布特点与成因", 3, SUBJECT, G7, 240065),
    (240069, "jgeo_g7b_au_sheep", "澳大利亚“骑在羊背上的国家”及养羊业发达的条件", 4, SUBJECT, G7, 240065),
    (240070, "jgeo_g7b_au_mineral_city", "澳大利亚矿产资源出口与东南沿海人口城市分布", 5, SUBJECT, G7, 240065),

    # 第九章 西半球的国家
    (240071, "jgeo_g7b_c09", "初中七下·地理·第九章 西半球的国家", 9, SUBJECT, G7, 240001),
    (240072, "jgeo_g7b_c09_s01", "第一节 美国的自然环境与农业", 1, SUBJECT, G7, 240071),
    (240073, "jgeo_g7b_us_location", "美国的位置、领土组成与阿拉斯加、夏威夷", 1, SUBJECT, G7, 240072),
    (240074, "jgeo_g7b_us_terrain", "美国三大南北纵列带的地形特点", 2, SUBJECT, G7, 240072),
    (240075, "jgeo_g7b_us_river_lake", "美国主要河流与五大湖群", 3, SUBJECT, G7, 240072),
    (240076, "jgeo_g7b_us_agri_belt", "美国农业地区专业化与主要农业带的分布", 4, SUBJECT, G7, 240072),
    (240077, "jgeo_g7b_c09_s02", "第二节 美国的工业、城市与高新技术产业", 2, SUBJECT, G7, 240071),
    (240078, "jgeo_g7b_us_industry", "美国东北部传统工业区与工业分布特点", 1, SUBJECT, G7, 240077),
    (240079, "jgeo_g7b_us_high_tech", "美国高新技术产业与硅谷的发展", 2, SUBJECT, G7, 240077),
    (240080, "jgeo_g7b_us_population_city", "美国人口构成、分布与华盛顿、纽约等主要城市", 3, SUBJECT, G7, 240077),
    (240081, "jgeo_g7b_c09_s03", "第三节 巴西的自然环境与热带雨林", 3, SUBJECT, G7, 240071),
    (240082, "jgeo_g7b_brazil_location", "巴西的位置、领土组成与拉丁美洲面积最大的国家", 1, SUBJECT, G7, 240081),
    (240083, "jgeo_g7b_brazil_terrain", "巴西北部亚马孙平原、南部巴西高原的地形", 2, SUBJECT, G7, 240081),
    (240084, "jgeo_g7b_brazil_climate_river", "巴西热带雨林气候与亚马孙河的水文特征", 3, SUBJECT, G7, 240081),
    (240085, "jgeo_g7b_brazil_rainforest", "巴西热带雨林的开发、生态价值与保护", 4, SUBJECT, G7, 240081),
    (240086, "jgeo_g7b_c09_s04", "第四节 巴西的人口、城市与经济", 4, SUBJECT, G7, 240071),
    (240087, "jgeo_g7b_brazil_population", "巴西人口分布不均与东南沿海人口集中", 1, SUBJECT, G7, 240086),
    (240088, "jgeo_g7b_brazil_city", "巴西首都巴西利亚与圣保罗、里约热内卢", 2, SUBJECT, G7, 240086),
    (240089, "jgeo_g7b_brazil_economy", "巴西的工农业特点与主要出口产品", 3, SUBJECT, G7, 240086),

    # 第十章 极地地区
    (240090, "jgeo_g7b_c10", "初中七下·地理·第十章 极地地区", 10, SUBJECT, G7, 240001),
    (240091, "jgeo_g7b_c10_s01", "第一节 极地地区的自然环境", 1, SUBJECT, G7, 240090),
    (240092, "jgeo_g7b_polar_location", "北极地区与南极地区的位置、范围与海陆差异", 1, SUBJECT, G7, 240091),
    (240093, "jgeo_g7b_polar_climate", "极地地区酷寒、多风、干燥的气候特征", 2, SUBJECT, G7, 240091),
    (240094, "jgeo_g7b_polar_life", "极地地区的代表性动物：北极熊与企鹅", 3, SUBJECT, G7, 240091),
    (240095, "jgeo_g7b_c10_s02", "第二节 极地科学考察与环境保护", 2, SUBJECT, G7, 240090),
    (240096, "jgeo_g7b_polar_research", "我国南极长城站、中山站与北极黄河站的科考价值", 1, SUBJECT, G7, 240095),
    (240097, "jgeo_g7b_polar_protect", "极地环境保护与《南极条约》", 2, SUBJECT, G7, 240095),
)

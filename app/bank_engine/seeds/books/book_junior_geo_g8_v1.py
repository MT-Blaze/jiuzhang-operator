"""人教版初中地理八年级上册：从世界看中国、自然环境、自然资源、经济发展。"""

from __future__ import annotations

SUBJECT = 9
G8 = 8
BOOK_ID = 1341

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级地理上册",
    "jgeo_g8a",
    41,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (134101, "人教版八年级地理上册", "jgeo_g8a_root", 1, BOOK_ID, None),

    (134102, "第一章 从世界看中国", "jgeo_g8a_c01", 1, BOOK_ID, 134101),
    (134111, "第一节 疆域", "jgeo_g8a_c01_s01", 1, BOOK_ID, 134102),
    (134112, "第二节 行政区划", "jgeo_g8a_c01_s02", 2, BOOK_ID, 134102),
    (134113, "第三节 人口", "jgeo_g8a_c01_s03", 3, BOOK_ID, 134102),
    (134114, "第四节 民族", "jgeo_g8a_c01_s04", 4, BOOK_ID, 134102),

    (134103, "第二章 中国的自然环境", "jgeo_g8a_c02", 2, BOOK_ID, 134101),
    (134121, "第一节 地形和地势", "jgeo_g8a_c02_s01", 1, BOOK_ID, 134103),
    (134122, "第二节 气温与降水", "jgeo_g8a_c02_s02", 2, BOOK_ID, 134103),
    (134123, "第三节 气候特征与季风气候", "jgeo_g8a_c02_s03", 3, BOOK_ID, 134103),
    (134124, "第四节 河流", "jgeo_g8a_c02_s04", 4, BOOK_ID, 134103),
    (134125, "第五节 长江与黄河", "jgeo_g8a_c02_s05", 5, BOOK_ID, 134103),
    (134126, "第六节 自然灾害", "jgeo_g8a_c02_s06", 6, BOOK_ID, 134103),

    (134104, "第三章 中国的自然资源", "jgeo_g8a_c03", 3, BOOK_ID, 134101),
    (134131, "第一节 自然资源的基本特征", "jgeo_g8a_c03_s01", 1, BOOK_ID, 134104),
    (134132, "第二节 土地资源的类型与分布", "jgeo_g8a_c03_s02", 2, BOOK_ID, 134104),
    (134133, "第三节 土地资源的问题与国策", "jgeo_g8a_c03_s03", 3, BOOK_ID, 134104),
    (134134, "第四节 水资源的时空分布", "jgeo_g8a_c03_s04", 4, BOOK_ID, 134104),
    (134135, "第五节 南水北调与节约用水", "jgeo_g8a_c03_s05", 5, BOOK_ID, 134104),

    (134105, "第四章 中国的经济发展", "jgeo_g8a_c04", 4, BOOK_ID, 134101),
    (134141, "第一节 交通运输方式与枢纽", "jgeo_g8a_c04_s01", 1, BOOK_ID, 134105),
    (134142, "第二节 主要铁路干线", "jgeo_g8a_c04_s02", 2, BOOK_ID, 134105),
    (134143, "第三节 农业部门与分布", "jgeo_g8a_c04_s03", 3, BOOK_ID, 134105),
    (134144, "第四节 因地制宜发展农业", "jgeo_g8a_c04_s04", 4, BOOK_ID, 134105),
    (134145, "第五节 工业基地与工业分布", "jgeo_g8a_c04_s05", 5, BOOK_ID, 134105),
    (134146, "第六节 高新技术产业", "jgeo_g8a_c04_s06", 6, BOOK_ID, 134105),
)

# id / code / name / sort_order / subject_id / parent_id
# 241001 册域顶层，241002-241099 为章、节锚点与细颗粒考点；父节点全部先于子节点登记。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    (241001, "jgeo_g8a_domain", "初中八上·地理·从世界看中国·自然环境·自然资源·经济发展", 1, SUBJECT, None),

    # 第一章 从世界看中国
    (241002, "jgeo_g8a_c01", "初中八上·地理·第一章 从世界看中国", 1, SUBJECT, 241001),
    (241006, "jgeo_g8a_c01_s01", "第一节 疆域", 1, SUBJECT, 241002),
    (241007, "jgeo_g8a_c01_s02", "第二节 行政区划", 2, SUBJECT, 241002),
    (241008, "jgeo_g8a_c01_s03", "第三节 人口", 3, SUBJECT, 241002),
    (241009, "jgeo_g8a_c01_s04", "第四节 民族", 4, SUBJECT, 241002),
    (241027, "jgeo_g8a_hemisphere", "中国的半球位置：位于东半球和北半球", 1, SUBJECT, 241006),
    (241028, "jgeo_g8a_sea_land", "中国的海陆位置：亚欧大陆东部、太平洋西岸，海陆兼备", 2, SUBJECT, 241006),
    (241029, "jgeo_g8a_latitude", "中国的纬度位置：大部分位于北温带，南部部分位于热带，没有寒带", 3, SUBJECT, 241006),
    (241030, "jgeo_g8a_territory_ends", "领土四至：漠河以北黑龙江主航道中心线、曾母暗沙、黑龙江与乌苏里江主航道中心线汇合处、帕米尔高原", 4, SUBJECT, 241006),
    (241031, "jgeo_g8a_land_area", "陆地面积约960万平方千米，居世界第三位，海洋国土辽阔、岛屿众多", 5, SUBJECT, 241006),
    (241032, "jgeo_g8a_neighbors", "陆上邻国14个、隔海相望国家6个及陆海边界特点", 6, SUBJECT, 241006),
    (241033, "jgeo_g8a_admin_levels", "三级行政区划：省（自治区、直辖市）、县（自治县、市）、乡（镇）", 1, SUBJECT, 241007),
    (241034, "jgeo_g8a_provinces", "34个省级行政区：23个省、5个自治区、4个直辖市、2个特别行政区", 2, SUBJECT, 241007),
    (241035, "jgeo_g8a_province_code", "省级行政区简称、行政中心与面积最大、邻省最多的省级行政区", 3, SUBJECT, 241007),
    (241036, "jgeo_g8a_population_growth", "人口数量与新中国成立以来人口增长的特点", 1, SUBJECT, 241008),
    (241037, "jgeo_g8a_population_distribution", "人口分布东多西少与黑河—腾冲线（胡焕庸线）", 2, SUBJECT, 241008),
    (241038, "jgeo_g8a_population_density", "人口密度差异的自然原因、社会经济原因与人口政策", 3, SUBJECT, 241008),
    (241039, "jgeo_g8a_ethnic_groups", "56个民族及汉族人口约占91%的民族构成", 1, SUBJECT, 241009),
    (241040, "jgeo_g8a_ethnic_distribution", "少数民族分布特点：大散居、小聚居、交错杂居", 2, SUBJECT, 241009),
    (241041, "jgeo_g8a_ethnic_autonomy", "民族区域自治制度与壮族、回族、满族、维吾尔族等主要少数民族分布", 3, SUBJECT, 241009),
    (241042, "jgeo_g8a_ethnic_culture", "民族风情、民族文化与民族平等团结政策", 4, SUBJECT, 241009),

    # 第二章 中国的自然环境
    (241003, "jgeo_g8a_c02", "初中八上·地理·第二章 中国的自然环境", 2, SUBJECT, 241001),
    (241010, "jgeo_g8a_c02_s01", "第一节 地形和地势", 1, SUBJECT, 241003),
    (241011, "jgeo_g8a_c02_s02", "第二节 气温与降水", 2, SUBJECT, 241003),
    (241012, "jgeo_g8a_c02_s03", "第三节 气候特征与季风气候", 3, SUBJECT, 241003),
    (241013, "jgeo_g8a_c02_s04", "第四节 河流", 4, SUBJECT, 241003),
    (241014, "jgeo_g8a_c02_s05", "第五节 长江与黄河", 5, SUBJECT, 241003),
    (241015, "jgeo_g8a_c02_s06", "第六节 自然灾害", 6, SUBJECT, 241003),
    (241043, "jgeo_g8a_relief_steps", "地势西高东低、呈三级阶梯分布", 1, SUBJECT, 241010),
    (241044, "jgeo_g8a_step_lines", "三级阶梯分界线：昆仑山—祁连山—横断山；大兴安岭—太行山—巫山—雪峰山", 2, SUBJECT, 241010),
    (241045, "jgeo_g8a_step_elevation", "三级阶梯的海拔范围与各阶梯主要地形区", 3, SUBJECT, 241010),
    (241046, "jgeo_g8a_mountain_area", "地形复杂多样、山区面积约占三分之二及其对生产生活的影响", 4, SUBJECT, 241010),
    (241047, "jgeo_g8a_mountains_basins", "主要山脉走向与四大高原、四大盆地、三大平原的分布特征", 5, SUBJECT, 241010),
    (241048, "jgeo_g8a_winter_temp", "冬季气温分布：南北温差大，1月0℃等温线大致沿秦岭—淮河一线", 1, SUBJECT, 241011),
    (241049, "jgeo_g8a_summer_temp", "夏季气温分布：普遍高温，青藏高原等地气温较低", 2, SUBJECT, 241011),
    (241050, "jgeo_g8a_temp_zones", "温度带划分与不同温度带的作物熟制", 3, SUBJECT, 241011),
    (241051, "jgeo_g8a_precip_space", "年降水量自东南沿海向西北内陆递减及800毫米、400毫米、200毫米等降水量线", 4, SUBJECT, 241011),
    (241052, "jgeo_g8a_precip_time", "降水的季节分配：夏秋多、冬春少，年际变化大", 5, SUBJECT, 241011),
    (241053, "jgeo_g8a_climate_types", "气候类型复杂多样与主要气候类型的分布", 1, SUBJECT, 241012),
    (241054, "jgeo_g8a_monsoon", "季风气候显著及冬夏季风的源地、风向与性质", 2, SUBJECT, 241012),
    (241055, "jgeo_g8a_monsoon_line", "季风区与非季风区分界线：大兴安岭—阴山—贺兰山—巴颜喀拉山—冈底斯山", 3, SUBJECT, 241012),
    (241056, "jgeo_g8a_rainbelt", "锋面雨带推移规律、夏季风强弱与旱涝灾害的关系", 4, SUBJECT, 241012),
    (241057, "jgeo_g8a_drainage_divide", "外流区与内流区的划分及主要外流河、内流河", 1, SUBJECT, 241013),
    (241058, "jgeo_g8a_river_north_south", "外流河水文特征的南北差异：汛期、流量、含沙量与结冰期", 2, SUBJECT, 241013),
    (241059, "jgeo_g8a_inland_river", "内流河水文特征、京杭运河与鄱阳湖、青海湖等主要湖泊", 3, SUBJECT, 241013),
    (241060, "jgeo_g8a_yangtze_source", "长江的源地、长度约6300千米、注入东海与流经的省级行政区", 1, SUBJECT, 241014),
    (241061, "jgeo_g8a_yangtze_reaches", "长江上中下游的划分（宜昌、湖口）与各河段水文特征", 2, SUBJECT, 241014),
    (241062, "jgeo_g8a_yangtze_power", "长江水能资源、三峡工程与“黄金水道”的航运价值", 3, SUBJECT, 241014),
    (241063, "jgeo_g8a_yangtze_flood", "长江洪涝灾害的成因与综合治理措施", 4, SUBJECT, 241014),
    (241064, "jgeo_g8a_yellow_source", "黄河的源地、长度约5464千米、注入渤海与流经的地形区", 5, SUBJECT, 241014),
    (241065, "jgeo_g8a_yellow_reaches", "黄河上中下游划分（河口、桃花峪）、“地上河”成因、水土流失治理与凌汛断流", 6, SUBJECT, 241014),
    (241066, "jgeo_g8a_disaster_types", "我国自然灾害种类多、分布广的特点与成因", 1, SUBJECT, 241015),
    (241067, "jgeo_g8a_weather_disaster", "主要气象灾害：洪涝、干旱、寒潮、台风的分布与危害", 2, SUBJECT, 241015),
    (241068, "jgeo_g8a_geo_disaster", "主要地质灾害：地震、滑坡、泥石流及防灾减灾措施", 3, SUBJECT, 241015),

    # 第三章 中国的自然资源
    (241004, "jgeo_g8a_c03", "初中八上·地理·第三章 中国的自然资源", 3, SUBJECT, 241001),
    (241016, "jgeo_g8a_c03_s01", "第一节 自然资源的基本特征", 1, SUBJECT, 241004),
    (241017, "jgeo_g8a_c03_s02", "第二节 土地资源的类型与分布", 2, SUBJECT, 241004),
    (241018, "jgeo_g8a_c03_s03", "第三节 土地资源的问题与国策", 3, SUBJECT, 241004),
    (241019, "jgeo_g8a_c03_s04", "第四节 水资源的时空分布", 4, SUBJECT, 241004),
    (241020, "jgeo_g8a_c03_s05", "第五节 南水北调与节约用水", 5, SUBJECT, 241004),
    (241069, "jgeo_g8a_resource_types", "自然资源的分类：可再生资源与非可再生资源", 1, SUBJECT, 241016),
    (241070, "jgeo_g8a_resource_status", "我国自然资源总量丰富、人均不足的基本国情", 2, SUBJECT, 241016),
    (241071, "jgeo_g8a_resource_problem", "自然资源开发利用中的浪费、破坏问题与节约保护", 3, SUBJECT, 241016),
    (241072, "jgeo_g8a_land_types", "土地利用类型：耕地、林地、草地与建设用地", 1, SUBJECT, 241017),
    (241073, "jgeo_g8a_land_farm_forest", "耕地与林地主要分布在东部季风区的平原、盆地和山地", 2, SUBJECT, 241017),
    (241074, "jgeo_g8a_land_grass", "草地、荒漠与难以利用土地主要分布在西部内陆", 3, SUBJECT, 241017),
    (241075, "jgeo_g8a_land_problems", "土地资源利用中的耕地减少、质量下降、水土流失与荒漠化问题", 1, SUBJECT, 241018),
    (241076, "jgeo_g8a_land_policy", "基本国策：十分珍惜、合理利用土地和切实保护耕地", 2, SUBJECT, 241018),
    (241077, "jgeo_g8a_land_redline", "耕地红线与土地资源的可持续利用", 3, SUBJECT, 241018),
    (241078, "jgeo_g8a_water_distribution", "水资源的时空分布：南丰北缺、夏秋多冬春少", 1, SUBJECT, 241019),
    (241079, "jgeo_g8a_water_shortage", "华北地区水资源短缺的自然与社会经济原因", 2, SUBJECT, 241019),
    (241080, "jgeo_g8a_south_north_water", "南水北调工程东、中、西三线的主要路线与意义", 1, SUBJECT, 241020),
    (241081, "jgeo_g8a_water_saving", "节约用水、防治水污染与建设节水型社会", 2, SUBJECT, 241020),

    # 第四章 中国的经济发展
    (241005, "jgeo_g8a_c04", "初中八上·地理·第四章 中国的经济发展", 4, SUBJECT, 241001),
    (241021, "jgeo_g8a_c04_s01", "第一节 交通运输方式与枢纽", 1, SUBJECT, 241005),
    (241022, "jgeo_g8a_c04_s02", "第二节 主要铁路干线", 2, SUBJECT, 241005),
    (241023, "jgeo_g8a_c04_s03", "第三节 农业部门与分布", 3, SUBJECT, 241005),
    (241024, "jgeo_g8a_c04_s04", "第四节 因地制宜发展农业", 4, SUBJECT, 241005),
    (241025, "jgeo_g8a_c04_s05", "第五节 工业基地与工业分布", 5, SUBJECT, 241005),
    (241026, "jgeo_g8a_c04_s06", "第六节 高新技术产业", 6, SUBJECT, 241005),
    (241082, "jgeo_g8a_transport_modes", "五种交通运输方式的特点比较与合理选择", 1, SUBJECT, 241021),
    (241083, "jgeo_g8a_transport_network", "我国交通运输网的分布格局：东部密集、西部稀疏", 2, SUBJECT, 241021),
    (241084, "jgeo_g8a_transport_hubs", "北京、郑州、徐州、株洲等主要交通枢纽的区位优势", 3, SUBJECT, 241021),
    (241085, "jgeo_g8a_transport_modern", "高速公路、航空运输与水运的发展", 4, SUBJECT, 241021),
    (241086, "jgeo_g8a_rail_north_south", "南北向主要铁路干线：京广线、京沪线、京哈—京九线", 1, SUBJECT, 241022),
    (241087, "jgeo_g8a_rail_east_west", "东西向主要铁路干线：陇海—兰新线、沪昆线、京包—包兰线", 2, SUBJECT, 241022),
    (241088, "jgeo_g8a_rail_qinghai", "青藏铁路与我国高速铁路网建设", 3, SUBJECT, 241022),
    (241089, "jgeo_g8a_agriculture_sectors", "农业的主要部门与我国农业大国的地位", 1, SUBJECT, 241023),
    (241090, "jgeo_g8a_crop_difference", "种植业的南北差异：以秦岭—淮河一线为界的水田与旱地", 2, SUBJECT, 241023),
    (241091, "jgeo_g8a_animal_forest_fish", "畜牧业、林业与渔业的主要分布区", 3, SUBJECT, 241023),
    (241092, "jgeo_g8a_local_conditions", "因地制宜发展农业的自然条件与社会经济条件", 1, SUBJECT, 241024),
    (241093, "jgeo_g8a_agri_regions", "主要农业区与水稻、小麦、棉花、油料等农作物的分布", 2, SUBJECT, 241024),
    (241094, "jgeo_g8a_agri_challenge", "我国农业面临的挑战与发展方向", 3, SUBJECT, 241024),
    (241095, "jgeo_g8a_industry_layout", "工业在国民经济中的地位与我国工业分布特点", 1, SUBJECT, 241025),
    (241096, "jgeo_g8a_industry_bases", "四大工业基地：辽中南、京津唐、沪宁杭、珠江三角洲", 2, SUBJECT, 241025),
    (241097, "jgeo_g8a_industry_sectors", "主要工业部门与鞍山、大庆、攀枝花等资源型工业城市", 3, SUBJECT, 241025),
    (241098, "jgeo_g8a_high_tech", "高新技术产业的特点与主要分布地区", 1, SUBJECT, 241026),
    (241099, "jgeo_g8a_high_tech_park", "高新技术产业开发区与创新驱动发展", 2, SUBJECT, 241026),
)

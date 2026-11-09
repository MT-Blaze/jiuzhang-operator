"""人教版初中地理七年级上册：地球与地图、陆地和海洋、天气与气候、居民与聚落、发展与合作。"""

from __future__ import annotations

SUBJECT = 9
G7 = 7
BOOK_ID = 1339

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版七年级地理上册",
    "jgeo_g7a",
    39,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133901, "人教版七年级地理上册", "jgeo_g7a_root", 1, BOOK_ID, None),

    (133902, "第一章 地球和地图", "jgeo_g7a_c01", 1, BOOK_ID, 133901),
    (133911, "第一节 地球和地球仪", "jgeo_g7a_c01_s01", 1, BOOK_ID, 133902),
    (133912, "第二节 地球的运动", "jgeo_g7a_c01_s02", 2, BOOK_ID, 133902),
    (133913, "第三节 地图的阅读", "jgeo_g7a_c01_s03", 3, BOOK_ID, 133902),
    (133914, "第四节 地形图的判读", "jgeo_g7a_c01_s04", 4, BOOK_ID, 133902),

    (133903, "第二章 陆地和海洋", "jgeo_g7a_c02", 2, BOOK_ID, 133901),
    (133921, "第一节 大洲和大洋", "jgeo_g7a_c02_s01", 1, BOOK_ID, 133903),
    (133922, "第二节 海陆的变迁", "jgeo_g7a_c02_s02", 2, BOOK_ID, 133903),

    (133904, "第三章 天气与气候", "jgeo_g7a_c03", 3, BOOK_ID, 133901),
    (133931, "第一节 多变的天气", "jgeo_g7a_c03_s01", 1, BOOK_ID, 133904),
    (133932, "第二节 气温的变化与分布", "jgeo_g7a_c03_s02", 2, BOOK_ID, 133904),
    (133933, "第三节 降水的变化与分布", "jgeo_g7a_c03_s03", 3, BOOK_ID, 133904),
    (133934, "第四节 世界的气候", "jgeo_g7a_c03_s04", 4, BOOK_ID, 133904),

    (133905, "第四章 居民与聚落", "jgeo_g7a_c04", 4, BOOK_ID, 133901),
    (133941, "第一节 人口与人种", "jgeo_g7a_c04_s01", 1, BOOK_ID, 133905),
    (133942, "第二节 世界的语言和宗教", "jgeo_g7a_c04_s02", 2, BOOK_ID, 133905),
    (133943, "第三节 人类的聚居地——聚落", "jgeo_g7a_c04_s03", 3, BOOK_ID, 133905),

    (133906, "第五章 发展与合作", "jgeo_g7a_c05", 5, BOOK_ID, 133901),
    (133951, "第一节 地域发展差异", "jgeo_g7a_c05_s01", 1, BOOK_ID, 133906),
    (133952, "第二节 发达国家和发展中国家的分布", "jgeo_g7a_c05_s02", 2, BOOK_ID, 133906),
    (133953, "第三节 国际经济合作", "jgeo_g7a_c05_s03", 3, BOOK_ID, 133906),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 239001 册域顶层，239002-239099 为章、节锚点与细颗粒考点；父节点全部先于子节点登记。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    (239001, "jgeo_g7a_domain", "初中七上·地球与地图·陆地和海洋·天气与气候·居民与聚落·发展与合作", 1, SUBJECT, G7, None),

    # 第一章 地球和地图
    (239002, "jgeo_g7a_c01", "初中七上·第一章 地球和地图", 1, SUBJECT, G7, 239001),
    (239003, "jgeo_g7a_c01_s01", "第一节 地球和地球仪", 1, SUBJECT, G7, 239002),
    (239004, "jgeo_g7a_earth_shape", "地球的形状和大小：平均半径6371千米、赤道周长约4万千米", 1, SUBJECT, G7, 239003),
    (239005, "jgeo_g7a_globe_axis", "地球仪上的地轴、南极和北极及经线纬线的绘制", 2, SUBJECT, G7, 239003),
    (239006, "jgeo_g7a_latitude", "纬线的特点与纬度的划分：赤道0°、南北纬各90°", 3, SUBJECT, G7, 239003),
    (239007, "jgeo_g7a_longitude", "经线的特点与本初子午线：东西经各180°的划分", 4, SUBJECT, G7, 239003),
    (239008, "jgeo_g7a_low_mid_high", "低、中、高纬度的划分与南北半球的判断", 5, SUBJECT, G7, 239003),
    (239009, "jgeo_g7a_hemisphere_grid", "东西半球分界线20°W和160°E及经纬网定位", 6, SUBJECT, G7, 239003),
    (239010, "jgeo_g7a_c01_s02", "第二节 地球的运动", 2, SUBJECT, G7, 239002),
    (239011, "jgeo_g7a_rotation", "地球自转的方向、周期和绕转中心：自西向东、约24小时", 1, SUBJECT, G7, 239010),
    (239012, "jgeo_g7a_rotation_effect", "地球自转产生的地理现象：昼夜交替与时间差异", 2, SUBJECT, G7, 239010),
    (239013, "jgeo_g7a_revolution", "地球公转的方向、周期和特点：自西向东、约一年、地轴倾斜", 3, SUBJECT, G7, 239010),
    (239014, "jgeo_g7a_revolution_effect", "地球公转产生的地理现象：四季变化与昼夜长短变化", 4, SUBJECT, G7, 239010),
    (239015, "jgeo_g7a_solstice", "二分二至日与太阳直射点的回归运动", 5, SUBJECT, G7, 239010),
    (239016, "jgeo_g7a_five_zones", "五带的划分依据及各带获得太阳热量的差异", 6, SUBJECT, G7, 239010),
    (239017, "jgeo_g7a_c01_s03", "第三节 地图的阅读", 3, SUBJECT, G7, 239002),
    (239018, "jgeo_g7a_map_elements", "地图的三要素：比例尺、方向、图例和注记", 1, SUBJECT, G7, 239017),
    (239019, "jgeo_g7a_scale_form", "比例尺的三种表示形式与大小比较", 2, SUBJECT, G7, 239017),
    (239020, "jgeo_g7a_scale_detail", "比例尺大小与地图范围、内容详略的关系", 3, SUBJECT, G7, 239017),
    (239021, "jgeo_g7a_map_direction", "地图方向的判断：一般定向法、指向标定向法和经纬网定向法", 4, SUBJECT, G7, 239017),
    (239022, "jgeo_g7a_legend", "常用图例与注记的识别和填绘", 5, SUBJECT, G7, 239017),
    (239023, "jgeo_g7a_map_choice", "根据需要选择地图与电子地图的实际应用", 6, SUBJECT, G7, 239017),
    (239024, "jgeo_g7a_c01_s04", "第四节 地形图的判读", 4, SUBJECT, G7, 239002),
    (239025, "jgeo_g7a_elevation", "海拔和相对高度的概念与计算", 1, SUBJECT, G7, 239024),
    (239026, "jgeo_g7a_contour_line", "等高线、等高距与等高线地形图的基本判读", 2, SUBJECT, G7, 239024),
    (239027, "jgeo_g7a_contour_features", "山峰、山脊、山谷、鞍部和陡崖的等高线特征", 3, SUBJECT, G7, 239024),
    (239028, "jgeo_g7a_slope_river", "等高线疏密与坡度陡缓、河流流向的判断", 4, SUBJECT, G7, 239024),
    (239029, "jgeo_g7a_landform_types", "分层设色地形图与山地、丘陵、高原、平原、盆地", 5, SUBJECT, G7, 239024),
    (239030, "jgeo_g7a_profile", "地形剖面图的绘制与地形起伏判读", 6, SUBJECT, G7, 239024),

    # 第二章 陆地和海洋
    (239031, "jgeo_g7a_c02", "初中七上·第二章 陆地和海洋", 2, SUBJECT, G7, 239001),
    (239032, "jgeo_g7a_c02_s01", "第一节 大洲和大洋", 1, SUBJECT, G7, 239031),
    (239033, "jgeo_g7a_land_sea_ratio", "地球表面海陆面积比例：海洋约占71%、陆地约占29%", 1, SUBJECT, G7, 239032),
    (239034, "jgeo_g7a_seven_continents", "七大洲的名称、面积大小排序与分布", 2, SUBJECT, G7, 239032),
    (239035, "jgeo_g7a_four_oceans", "四大洋的名称、面积大小排序与位置", 3, SUBJECT, G7, 239032),
    (239036, "jgeo_g7a_continent_boundary", "大洲分界线：乌拉尔山、苏伊士运河、巴拿马运河等", 4, SUBJECT, G7, 239032),
    (239037, "jgeo_g7a_land_units", "大陆、岛屿、半岛、海峡和大洋边缘海的概念", 5, SUBJECT, G7, 239032),
    (239038, "jgeo_g7a_land_distribution", "陆地主要集中在北半球、海洋主要分布在南半球的格局", 6, SUBJECT, G7, 239032),
    (239039, "jgeo_g7a_c02_s02", "第二节 海陆的变迁", 2, SUBJECT, G7, 239031),
    (239040, "jgeo_g7a_change_cause", "海陆变迁的实例与原因：地壳变动、海平面升降和人类活动", 1, SUBJECT, G7, 239039),
    (239041, "jgeo_g7a_drift", "大陆漂移假说与魏格纳的科学探索", 2, SUBJECT, G7, 239039),
    (239042, "jgeo_g7a_plate_theory", "板块构造学说的基本观点：岩石圈由六大板块拼合", 3, SUBJECT, G7, 239039),
    (239043, "jgeo_g7a_plate_motion", "板块运动方式：碰撞挤压形成山脉、张裂拉伸形成裂谷和海洋", 4, SUBJECT, G7, 239039),
    (239044, "jgeo_g7a_volcano_quake", "板块交界地带多火山和地震及世界两大火山地震带", 5, SUBJECT, G7, 239039),
    (239045, "jgeo_g7a_quake_safety", "火山、地震的分布规律与防震减灾常识", 6, SUBJECT, G7, 239039),

    # 第三章 天气与气候
    (239046, "jgeo_g7a_c03", "初中七上·第三章 天气与气候", 3, SUBJECT, G7, 239001),
    (239047, "jgeo_g7a_c03_s01", "第一节 多变的天气", 1, SUBJECT, G7, 239046),
    (239048, "jgeo_g7a_weather_climate", "天气与气候的区别与联系：短时间多变与多年稳定", 1, SUBJECT, G7, 239047),
    (239049, "jgeo_g7a_weather_forecast", "天气预报的主要内容与常用天气符号的识别", 2, SUBJECT, G7, 239047),
    (239050, "jgeo_g7a_weather_elements", "风向、风力和气温、降水的描述与记录", 3, SUBJECT, G7, 239047),
    (239051, "jgeo_g7a_air_quality", "空气质量指数与大气环境保护", 4, SUBJECT, G7, 239047),
    (239052, "jgeo_g7a_c03_s02", "第二节 气温的变化与分布", 2, SUBJECT, G7, 239046),
    (239053, "jgeo_g7a_temp_average", "气温的观测与日平均、月平均、年平均气温的计算", 1, SUBJECT, G7, 239052),
    (239054, "jgeo_g7a_temp_daily", "一天中最高气温和最低气温出现的时间及气温日变化", 2, SUBJECT, G7, 239052),
    (239055, "jgeo_g7a_temp_range", "气温日较差与气温年较差的概念和计算", 3, SUBJECT, G7, 239052),
    (239056, "jgeo_g7a_temp_latitude", "世界气温分布的基本规律：由低纬向高纬递减", 4, SUBJECT, G7, 239052),
    (239057, "jgeo_g7a_temp_isotherm", "同纬度海陆气温差异与等温线的弯曲判读", 5, SUBJECT, G7, 239052),
    (239058, "jgeo_g7a_temp_altitude", "山地气温随海拔升高而降低及气温垂直变化", 6, SUBJECT, G7, 239052),
    (239059, "jgeo_g7a_c03_s03", "第三节 降水的变化与分布", 3, SUBJECT, G7, 239046),
    (239060, "jgeo_g7a_precip_form", "降水的主要形式与降水量的测量方法", 1, SUBJECT, G7, 239059),
    (239061, "jgeo_g7a_precip_change", "降水的季节变化和年际变化及降水柱状图的判读", 2, SUBJECT, G7, 239059),
    (239062, "jgeo_g7a_precip_equator", "世界降水分布规律：赤道多雨、两极少雨", 3, SUBJECT, G7, 239059),
    (239063, "jgeo_g7a_precip_latitude", "回归线附近大陆东岸多雨、西岸少雨及中纬度沿海与内陆差异", 4, SUBJECT, G7, 239059),
    (239064, "jgeo_g7a_precip_mountain", "山地迎风坡降水多、背风坡降水少及地形雨", 5, SUBJECT, G7, 239059),
    (239065, "jgeo_g7a_precip_types", "对流雨、地形雨、锋面雨的成因与分布", 6, SUBJECT, G7, 239059),
    (239066, "jgeo_g7a_c03_s04", "第四节 世界的气候", 4, SUBJECT, G7, 239046),
    (239067, "jgeo_g7a_climate_elements", "气候的两大要素：气温和降水", 1, SUBJECT, G7, 239066),
    (239068, "jgeo_g7a_climate_tropical", "热带气候类型：热带雨林、热带草原、热带季风、热带沙漠气候", 2, SUBJECT, G7, 239066),
    (239069, "jgeo_g7a_climate_subtropical", "亚热带气候类型：亚热带季风和湿润气候、地中海气候", 3, SUBJECT, G7, 239066),
    (239070, "jgeo_g7a_climate_temperate", "温带气候类型：温带海洋性、温带大陆性、温带季风气候", 4, SUBJECT, G7, 239066),
    (239071, "jgeo_g7a_climate_cold", "寒带气候与高原山地气候的分布和特征", 5, SUBJECT, G7, 239066),
    (239072, "jgeo_g7a_climate_judge", "气候类型判读方法：以温定带、以水定型与影响气候的因素", 6, SUBJECT, G7, 239066),

    # 第四章 居民与聚落
    (239073, "jgeo_g7a_c04", "初中七上·第四章 居民与聚落", 4, SUBJECT, G7, 239001),
    (239074, "jgeo_g7a_c04_s01", "第一节 人口与人种", 1, SUBJECT, G7, 239073),
    (239075, "jgeo_g7a_population_growth", "世界人口增长的特点与人口自然增长率", 1, SUBJECT, G7, 239074),
    (239076, "jgeo_g7a_population_rate", "人口出生率、死亡率和自然增长率的计算", 2, SUBJECT, G7, 239074),
    (239077, "jgeo_g7a_population_distribution", "世界人口分布特点及人口稠密区与稀疏区", 3, SUBJECT, G7, 239074),
    (239078, "jgeo_g7a_population_density", "人口密度与影响人口分布的自然、社会经济因素", 4, SUBJECT, G7, 239074),
    (239079, "jgeo_g7a_population_problem", "人口增长过快或过慢带来的问题及对策", 5, SUBJECT, G7, 239074),
    (239080, "jgeo_g7a_three_races", "三大人种的特征与主要分布地区", 6, SUBJECT, G7, 239074),
    (239081, "jgeo_g7a_c04_s02", "第二节 世界的语言和宗教", 2, SUBJECT, G7, 239073),
    (239082, "jgeo_g7a_languages", "世界主要语言的种类与分布", 1, SUBJECT, G7, 239081),
    (239083, "jgeo_g7a_un_languages", "联合国六种工作语言及其使用地区", 2, SUBJECT, G7, 239081),
    (239084, "jgeo_g7a_religions", "世界三大宗教：基督教、伊斯兰教、佛教的起源与分布", 3, SUBJECT, G7, 239081),
    (239085, "jgeo_g7a_religion_building", "不同宗教的建筑特色与文化景观差异", 4, SUBJECT, G7, 239081),
    (239086, "jgeo_g7a_c04_s03", "第三节 人类的聚居地——聚落", 3, SUBJECT, G7, 239073),
    (239087, "jgeo_g7a_settlement_type", "聚落的概念、类型与乡村、城市的区别", 1, SUBJECT, G7, 239086),
    (239088, "jgeo_g7a_settlement_condition", "聚落形成与发展的有利条件：水源、地形、交通、资源", 2, SUBJECT, G7, 239086),
    (239089, "jgeo_g7a_settlement_landscape", "乡村聚落与城市聚落的景观差异及生产活动差异", 3, SUBJECT, G7, 239086),
    (239090, "jgeo_g7a_settlement_protect", "聚落与自然环境的关系及传统聚落的保护", 4, SUBJECT, G7, 239086),

    # 第五章 发展与合作
    (239091, "jgeo_g7a_c05", "初中七上·第五章 发展与合作", 5, SUBJECT, G7, 239001),
    (239092, "jgeo_g7a_c05_s01", "第一节 地域发展差异", 1, SUBJECT, G7, 239091),
    (239093, "jgeo_g7a_country_divide", "发达国家与发展中国家的划分依据和分布特点", 1, SUBJECT, G7, 239092),
    (239094, "jgeo_g7a_country_gap", "发达国家与发展中国家的发展差异及原因", 2, SUBJECT, G7, 239092),
    (239095, "jgeo_g7a_c05_s02", "第二节 发达国家和发展中国家的分布", 2, SUBJECT, G7, 239091),
    (239096, "jgeo_g7a_south_talk", "南北差异、“南北对话”与“南南合作”", 1, SUBJECT, G7, 239095),
    (239097, "jgeo_g7a_c05_s03", "第三节 国际经济合作", 3, SUBJECT, G7, 239091),
    (239098, "jgeo_g7a_globalization", "国际经济合作的重要性与经济全球化", 1, SUBJECT, G7, 239097),
    (239099, "jgeo_g7a_wto", "世界贸易组织等国际组织在国际合作中的作用", 2, SUBJECT, G7, 239097),
)

"""人教版（2019）高中地理必修第一册：章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 9
G10 = 10
BOOK_ID = 9201

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中地理必修第一册",
    "geo_r1",
    1,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (910101, "第一章 宇宙中的地球", "geo_r1_u01", 1, BOOK_ID, None),
    (910102, "第二章 地球上的大气", "geo_r1_u02", 2, BOOK_ID, None),
    (910103, "第三章 地球上的水", "geo_r1_u03", 3, BOOK_ID, None),
    (910104, "第四章 地貌", "geo_r1_u04", 4, BOOK_ID, None),
    (910105, "第五章 植被与土壤", "geo_r1_u05", 5, BOOK_ID, None),
    (910106, "第六章 自然灾害", "geo_r1_u06", 6, BOOK_ID, None),
    (910111, "第一节 地球的宇宙环境", "geo_r1_l01", 1, BOOK_ID, 910101),
    (910112, "第二节 太阳对地球的影响", "geo_r1_l02", 2, BOOK_ID, 910101),
    (910113, "第三节 地球的历史", "geo_r1_l03", 3, BOOK_ID, 910101),
    (910114, "第四节 地球的圈层结构", "geo_r1_l04", 4, BOOK_ID, 910101),
    (910115, "第一节 大气的组成和垂直分层", "geo_r1_l05", 1, BOOK_ID, 910102),
    (910116, "第二节 大气受热过程和大气运动", "geo_r1_l06", 2, BOOK_ID, 910102),
    (910117, "第一节 水循环", "geo_r1_l07", 1, BOOK_ID, 910103),
    (910118, "第二节 海水的性质", "geo_r1_l08", 2, BOOK_ID, 910103),
    (910119, "第三节 海水的运动", "geo_r1_l09", 3, BOOK_ID, 910103),
    (910120, "第一节 常见地貌类型", "geo_r1_l10", 1, BOOK_ID, 910104),
    (910121, "第二节 地貌的观察", "geo_r1_l11", 2, BOOK_ID, 910104),
    (910122, "第一节 植被", "geo_r1_l12", 1, BOOK_ID, 910105),
    (910123, "第二节 土壤", "geo_r1_l13", 2, BOOK_ID, 910105),
    (910124, "第一节 气象灾害", "geo_r1_l14", 1, BOOK_ID, 910106),
    (910125, "第二节 地质灾害", "geo_r1_l15", 2, BOOK_ID, 910106),
    (910126, "第三节 防灾减灾", "geo_r1_l16", 3, BOOK_ID, 910106),
    (910127, "第四节 地理信息技术在防灾减灾中的应用", "geo_r1_l17", 4, BOOK_ID, 910106),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 91 00 xx 为册域、章域、节域结构层，91 01 xx 为考点层；父节点全部先于子节点登记。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (910001, "geo_r1_domain_universe", "浩瀚宇宙：地球的宇宙环境与圈层", 1, SUBJECT, G10, None),
    (910002, "geo_r1_domain_atmosphere", "大气运动：组成、受热与环流", 2, SUBJECT, G10, None),
    (910003, "geo_r1_domain_hydrosphere", "水润地球：水循环与海水运动", 3, SUBJECT, G10, None),
    (910004, "geo_r1_domain_landform", "千姿地貌：常见地貌与观察", 4, SUBJECT, G10, None),
    (910005, "geo_r1_domain_biosphere", "植被土壤：生命载体与地表基础", 5, SUBJECT, G10, None),
    (910006, "geo_r1_domain_hazard", "防灾减灾：自然灾害与地理信息技术", 6, SUBJECT, G10, None),

    # 章域层
    (910007, "geo_r1_chapter01", "第一章 宇宙中的地球", 1, SUBJECT, G10, 910001),
    (910008, "geo_r1_chapter02", "第二章 地球上的大气", 1, SUBJECT, G10, 910002),
    (910009, "geo_r1_chapter03", "第三章 地球上的水", 1, SUBJECT, G10, 910003),
    (910010, "geo_r1_chapter04", "第四章 地貌", 1, SUBJECT, G10, 910004),
    (910011, "geo_r1_chapter05", "第五章 植被与土壤", 1, SUBJECT, G10, 910005),
    (910012, "geo_r1_chapter06", "第六章 自然灾害", 1, SUBJECT, G10, 910006),

    # 节域层
    (910013, "geo_r1_section01", "第一节 地球的宇宙环境", 1, SUBJECT, G10, 910007),
    (910014, "geo_r1_section02", "第二节 太阳对地球的影响", 2, SUBJECT, G10, 910007),
    (910015, "geo_r1_section03", "第三节 地球的历史", 3, SUBJECT, G10, 910007),
    (910016, "geo_r1_section04", "第四节 地球的圈层结构", 4, SUBJECT, G10, 910007),
    (910017, "geo_r1_section05", "第一节 大气的组成和垂直分层", 1, SUBJECT, G10, 910008),
    (910018, "geo_r1_section06", "第二节 大气受热过程和大气运动", 2, SUBJECT, G10, 910008),
    (910019, "geo_r1_section07", "第一节 水循环", 1, SUBJECT, G10, 910009),
    (910020, "geo_r1_section08", "第二节 海水的性质", 2, SUBJECT, G10, 910009),
    (910021, "geo_r1_section09", "第三节 海水的运动", 3, SUBJECT, G10, 910009),
    (910022, "geo_r1_section10", "第一节 常见地貌类型", 1, SUBJECT, G10, 910010),
    (910023, "geo_r1_section11", "第二节 地貌的观察", 2, SUBJECT, G10, 910010),
    (910024, "geo_r1_section12", "第一节 植被", 1, SUBJECT, G10, 910011),
    (910025, "geo_r1_section13", "第二节 土壤", 2, SUBJECT, G10, 910011),
    (910026, "geo_r1_section14", "第一节 气象灾害", 1, SUBJECT, G10, 910012),
    (910027, "geo_r1_section15", "第二节 地质灾害", 2, SUBJECT, G10, 910012),
    (910028, "geo_r1_section16", "第三节 防灾减灾", 3, SUBJECT, G10, 910012),
    (910029, "geo_r1_section17", "第四节 地理信息技术在防灾减灾中的应用", 4, SUBJECT, G10, 910012),

    # 第一章考点：宇宙环境、太阳、地球历史与圈层
    (910031, "geo_r1_point_celestial_system", "天体与天体系统层级：地月系、太阳系、银河系与可观测宇宙", 1, SUBJECT, G10, 910013),
    (910032, "geo_r1_point_solar_planets", "太阳系八大行星：类地行星、巨行星与远日行星分类及公转特征", 2, SUBJECT, G10, 910013),
    (910033, "geo_r1_point_life_conditions", "地球存在生命的条件：适宜温度、液态水、大气与安全宇宙环境", 3, SUBJECT, G10, 910013),
    (910034, "geo_r1_point_moon_phase", "月相变化与月球潮汐：日地月相对位置、观测方法与月食日食", 4, SUBJECT, G10, 910013),
    (910035, "geo_r1_point_solar_radiation", "太阳辐射：能量来源、太阳常数与纬度海拔天气对辐射的影响", 1, SUBJECT, G10, 910014),
    (910036, "geo_r1_point_solar_activity", "太阳大气分层与太阳活动：黑子、耀斑、日珥与太阳风", 2, SUBJECT, G10, 910014),
    (910037, "geo_r1_point_solar_impact", "太阳活动对地球的影响：磁暴、极光、电离层扰动与气候异常", 3, SUBJECT, G10, 910014),
    (910038, "geo_r1_point_strata_fossil", "地层与化石：岩层新老关系、化石判定与地球历史记录", 1, SUBJECT, G10, 910015),
    (910039, "geo_r1_point_geologic_time", "地质年代表：宙代纪世单位、寒武纪生命大爆发与生物演化阶段", 2, SUBJECT, G10, 910015),
    (910040, "geo_r1_point_paleozoic_mesozoic", "古生代与中生代：海生无脊椎动物、鱼类两栖爬行动物与重要成煤期", 3, SUBJECT, G10, 910015),
    (910041, "geo_r1_point_cenozoic", "新生代：哺乳动物繁荣、人类起源、喜马拉雅运动与第四纪冰期", 4, SUBJECT, G10, 910015),
    (910042, "geo_r1_point_seismic_wave", "地震波与不连续面：纵波横波差异、莫霍界面与古登堡界面", 1, SUBJECT, G10, 910016),
    (910043, "geo_r1_point_inner_layers", "地球内部圈层：地壳、地幔、地核的厚度、物质组成与物理状态", 2, SUBJECT, G10, 910016),
    (910044, "geo_r1_point_lithosphere", "岩石圈与软流层：范围界定、板块运动与地表形态塑造基础", 3, SUBJECT, G10, 910016),
    (910045, "geo_r1_point_outer_spheres", "外部圈层：大气圈、水圈、生物圈的特点及圈层相互作用", 4, SUBJECT, G10, 910016),

    # 第二章考点：大气组成、垂直分层、受热过程与大气运动
    (910046, "geo_r1_point_dry_air", "干洁空气组成：氮氧主体、二氧化碳保温与臭氧吸收紫外线", 1, SUBJECT, G10, 910017),
    (910047, "geo_r1_point_water_dust", "水汽与杂质：成云致雨、凝结核作用与大气污染影响", 2, SUBJECT, G10, 910017),
    (910048, "geo_r1_point_vertical_layers", "大气垂直分层：对流层、平流层与高层大气的温度运动特征", 3, SUBJECT, G10, 910017),
    (910049, "geo_r1_point_atmosphere_weakens", "大气对太阳辐射的削弱作用：吸收、反射与散射的选择性", 1, SUBJECT, G10, 910018),
    (910050, "geo_r1_point_greenhouse", "地面辐射、大气逆辐射与大气保温作用：温室效应的形成", 2, SUBJECT, G10, 910018),
    (910051, "geo_r1_point_temperature_factors", "影响气温的因素：纬度、海陆位置、下垫面、天气与人类活动", 3, SUBJECT, G10, 910018),
    (910052, "geo_r1_point_thermal_circulation", "热力环流原理：冷热不均引起垂直运动、水平气压差与气流闭合", 4, SUBJECT, G10, 910018),
    (910053, "geo_r1_point_circulation_cases", "常见热力环流：海陆风、山谷风与城市热岛环流的形成与影响", 5, SUBJECT, G10, 910018),
    (910054, "geo_r1_point_wind", "风的形成：水平气压梯度力、地转偏向力、摩擦力与高空近地面风向", 6, SUBJECT, G10, 910018),

    # 第三章考点：水循环、海水性质与海水运动
    (910055, "geo_r1_point_water_cycle_types", "水循环类型：海陆间循环、陆地内循环与海上内循环的路径差异", 1, SUBJECT, G10, 910019),
    (910056, "geo_r1_point_water_cycle_links", "水循环环节：蒸发、水汽输送、降水、径流、下渗与植物蒸腾", 2, SUBJECT, G10, 910019),
    (910057, "geo_r1_point_water_cycle_meaning", "水循环的地理意义：物质迁移、能量交换、水资源更新与地貌塑造", 3, SUBJECT, G10, 910019),
    (910058, "geo_r1_point_human_water_cycle", "人类活动对水循环的影响：修水库、跨流域调水、城市化与植被恢复", 4, SUBJECT, G10, 910019),
    (910059, "geo_r1_point_sea_temperature", "海水温度：随纬度与深度变化的规律及洋流、季节的影响", 1, SUBJECT, G10, 910020),
    (910060, "geo_r1_point_temperature_effect", "海水温度的影响：调节气候、制约海洋生物分布与影响航运", 2, SUBJECT, G10, 910020),
    (910061, "geo_r1_point_sea_salinity", "海水盐度：副热带海区最高、赤道偏低与近岸径流稀释的分布规律", 3, SUBJECT, G10, 910020),
    (910062, "geo_r1_point_salinity_factors", "影响海水盐度的因素：蒸发量、降水量、径流注入、洋流与海冰", 4, SUBJECT, G10, 910020),
    (910063, "geo_r1_point_sea_density", "海水密度：温度盐度深度的影响、密度跃层与潜艇航行安全", 5, SUBJECT, G10, 910020),
    (910064, "geo_r1_point_waves", "海浪：风浪、涌浪与海啸的成因、传播及对海岸工程的影响", 1, SUBJECT, G10, 910021),
    (910065, "geo_r1_point_tides", "潮汐：月球太阳引潮力、大潮小潮、潮汐表与潮汐能利用", 2, SUBJECT, G10, 910021),
    (910066, "geo_r1_point_current_types", "洋流分类：暖流与寒流、风海流与补偿流、密度流的形成", 3, SUBJECT, G10, 910021),
    (910067, "geo_r1_point_current_pattern", "洋流分布规律：中低纬副热带环流、中高纬环流与南半球西风漂流", 4, SUBJECT, G10, 910021),
    (910068, "geo_r1_point_current_impact", "洋流对地理环境的影响：气候、渔场、航海与海洋污染扩散", 5, SUBJECT, G10, 910021),

    # 第四章考点：常见地貌类型与地貌观察
    (910069, "geo_r1_point_karst_erosion", "喀斯特溶蚀地貌：石灰岩溶蚀形成的峰林、峰丛、溶洞与天坑", 1, SUBJECT, G10, 910022),
    (910070, "geo_r1_point_karst_deposition", "喀斯特沉积地貌：石钟乳、石笋、石柱与钙华的形成过程", 2, SUBJECT, G10, 910022),
    (910071, "geo_r1_point_river_erosion", "河流侵蚀地貌：V形谷、峡谷、瀑布与河流阶地的形成", 3, SUBJECT, G10, 910022),
    (910072, "geo_r1_point_river_deposition", "河流堆积地貌：冲积扇、河漫滩、三角洲与冲积平原", 4, SUBJECT, G10, 910022),
    (910073, "geo_r1_point_aeolian", "风沙地貌：风蚀蘑菇、雅丹、沙丘与沙垄的形态与移动", 5, SUBJECT, G10, 910022),
    (910074, "geo_r1_point_coastal_glacial", "海岸与冰川地貌：海蚀崖、沙滩、潟湖、冰斗、角峰与U形谷", 6, SUBJECT, G10, 910022),
    (910075, "geo_r1_point_landform_observation", "地貌观察：由宏观到微观的顺序及高度、坡度、坡向、形态记录", 1, SUBJECT, G10, 910023),
    (910076, "geo_r1_point_contour_map", "等高线地形图：山峰、鞍部、陡崖、山脊、山谷与坡度判读", 2, SUBJECT, G10, 910023),
    (910077, "geo_r1_point_landform_human", "地貌与人类活动：聚落选址、农业生产、交通线路与工程布局", 3, SUBJECT, G10, 910023),

    # 第五章考点：植被与土壤
    (910078, "geo_r1_point_vegetation_environment", "植被与环境：气候、土壤、地形与水分条件对植被类型的塑造", 1, SUBJECT, G10, 910024),
    (910079, "geo_r1_point_forest_types", "森林植被：热带雨林、常绿阔叶林、落叶阔叶林与针叶林特征", 2, SUBJECT, G10, 910024),
    (910080, "geo_r1_point_grass_desert", "草原与荒漠植被：温带草原、热带草原及旱生植物的适应特征", 3, SUBJECT, G10, 910024),
    (910081, "geo_r1_point_vegetation_function", "植被垂直分异、生态功能与保护：涵养水源、固碳与防治荒漠化", 4, SUBJECT, G10, 910024),
    (910082, "geo_r1_point_soil_composition", "土壤组成：矿物质、有机质、水分与空气的理想比例", 1, SUBJECT, G10, 910025),
    (910083, "geo_r1_point_soil_texture", "土壤质地与颜色：砂土、壤土、黏土的性状与土壤肥力差异", 2, SUBJECT, G10, 910025),
    (910084, "geo_r1_point_soil_formation", "土壤形成因素：成土母质、气候、生物、地形与时间的共同作用", 3, SUBJECT, G10, 910025),
    (910085, "geo_r1_point_soil_profile", "土壤剖面与改良：有机层、淋溶层、淀积层、母质层及盐碱地治理", 4, SUBJECT, G10, 910025),

    # 第六章考点：气象灾害、地质灾害、防灾减灾与地理信息技术
    (910086, "geo_r1_point_flood", "洪涝灾害：降水集中、地势低洼等成因、分布地区与危害", 1, SUBJECT, G10, 910026),
    (910087, "geo_r1_point_drought", "干旱灾害：降水异常偏少、蒸发强烈成因、区域分布与危害", 2, SUBJECT, G10, 910026),
    (910088, "geo_r1_point_typhoon", "台风：热带气旋结构、移动路径、狂风暴雨与风暴潮危害", 3, SUBJECT, G10, 910026),
    (910089, "geo_r1_point_cold_wave", "寒潮与沙尘暴：强冷空气南下、大风降温及沙尘天气的防御", 4, SUBJECT, G10, 910026),
    (910090, "geo_r1_point_earthquake", "地震：板块构造与断层成因、震级、烈度、次生灾害与危害", 1, SUBJECT, G10, 910027),
    (910091, "geo_r1_point_landslide_debris", "滑坡与泥石流：地形、岩性、降水与植被条件及成灾过程", 2, SUBJECT, G10, 910027),
    (910092, "geo_r1_point_volcano", "火山喷发与地质灾害防御：喷发类型、火山灰影响与监测避让", 3, SUBJECT, G10, 910027),
    (910093, "geo_r1_point_monitoring", "灾害监测预警：气象水文监测、预警信号发布与应急预案", 1, SUBJECT, G10, 910028),
    (910094, "geo_r1_point_engineering", "防灾工程措施：堤坝、护坡、拦挡坝、排导槽与避让搬迁", 2, SUBJECT, G10, 910028),
    (910095, "geo_r1_point_self_rescue", "自救互救与社会参与：应急避险、演练、志愿者与灾害保险", 3, SUBJECT, G10, 910028),
    (910096, "geo_r1_point_rs", "遥感（RS）：电磁波成像原理、灾害范围监测与灾情动态评估", 1, SUBJECT, G10, 910029),
    (910097, "geo_r1_point_gnss", "全球卫星导航系统（GNSS）：北斗、GPS定位与救援路径引导", 2, SUBJECT, G10, 910029),
    (910098, "geo_r1_point_gis", "地理信息系统（GIS）：图层叠加、空间分析、风险区划与制图", 3, SUBJECT, G10, 910029),
    (910099, "geo_r1_point_3s", "“3S”技术集成与数字地球：灾害全流程监测、评估与决策支持", 4, SUBJECT, G10, 910029),
)

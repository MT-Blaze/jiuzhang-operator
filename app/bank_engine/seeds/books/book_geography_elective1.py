"""人教版（2019）高中地理选择性必修第一册（自然地理基础）：章节目录与知识点树。"""

from __future__ import annotations

SUBJECT = 9
G10 = 10
BOOK_ID = 9203

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中地理选择性必修第一册（自然地理基础）",
    "geo_e1",
    3,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (930101, "第一章 地球的运动", "geo_e1_u01", 1, BOOK_ID, None),
    (930102, "第二章 地表形态的塑造", "geo_e1_u02", 2, BOOK_ID, None),
    (930103, "第三章 大气的运动", "geo_e1_u03", 3, BOOK_ID, None),
    (930104, "第四章 水的运动", "geo_e1_u04", 4, BOOK_ID, None),
    (930105, "第五章 自然环境的整体性与差异性", "geo_e1_u05", 5, BOOK_ID, None),
    (930111, "第一节 地球的自转和公转", "geo_e1_l01", 1, BOOK_ID, 930101),
    (930112, "第二节 地球运动的地理意义", "geo_e1_l02", 2, BOOK_ID, 930101),
    (930113, "第一节 塑造地表形态的力量", "geo_e1_l03", 1, BOOK_ID, 930102),
    (930114, "第二节 构造地貌的形成", "geo_e1_l04", 2, BOOK_ID, 930102),
    (930115, "第三节 河流地貌的发育", "geo_e1_l05", 3, BOOK_ID, 930102),
    (930116, "第一节 常见天气系统", "geo_e1_l06", 1, BOOK_ID, 930103),
    (930117, "第二节 气压带和风带", "geo_e1_l07", 2, BOOK_ID, 930103),
    (930118, "第三节 气压带和风带对气候的影响", "geo_e1_l08", 3, BOOK_ID, 930103),
    (930119, "第一节 陆地水体及其相互关系", "geo_e1_l09", 1, BOOK_ID, 930104),
    (930120, "第二节 洋流", "geo_e1_l10", 2, BOOK_ID, 930104),
    (930121, "第三节 海—气相互作用", "geo_e1_l11", 3, BOOK_ID, 930104),
    (930122, "第一节 自然环境的整体性", "geo_e1_l12", 1, BOOK_ID, 930105),
    (930123, "第二节 自然环境的地域差异性", "geo_e1_l13", 2, BOOK_ID, 930105),
)

# id / code / name / sort_order / subject_id / parent_id
# 93 00 01-05 为册域，93 00 06-10 为章域，93 00 11-23 为节域；93 00 31-92 为考点层。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (930001, "geo_e1_domain_motion", "地球运动：自转公转与时空意义", 1, SUBJECT, None),
    (930002, "geo_e1_domain_landform", "地表形态：内外力作用、构造与河流地貌", 2, SUBJECT, None),
    (930003, "geo_e1_domain_atmosphere", "大气运动：天气系统、环流与气候成因", 3, SUBJECT, None),
    (930004, "geo_e1_domain_hydrosphere", "水的运动：陆地水体、洋流与海气相互作用", 4, SUBJECT, None),
    (930005, "geo_e1_domain_differentiation", "自然环境：整体性与地域分异规律", 5, SUBJECT, None),

    # 章域层
    (930006, "geo_e1_chapter01", "第一章 地球的运动", 1, SUBJECT, 930001),
    (930007, "geo_e1_chapter02", "第二章 地表形态的塑造", 1, SUBJECT, 930002),
    (930008, "geo_e1_chapter03", "第三章 大气的运动", 1, SUBJECT, 930003),
    (930009, "geo_e1_chapter04", "第四章 水的运动", 1, SUBJECT, 930004),
    (930010, "geo_e1_chapter05", "第五章 自然环境的整体性与差异性", 1, SUBJECT, 930005),

    # 节域层
    (930011, "geo_e1_section01", "第一节 地球的自转和公转", 1, SUBJECT, 930006),
    (930012, "geo_e1_section02", "第二节 地球运动的地理意义", 2, SUBJECT, 930006),
    (930013, "geo_e1_section03", "第一节 塑造地表形态的力量", 1, SUBJECT, 930007),
    (930014, "geo_e1_section04", "第二节 构造地貌的形成", 2, SUBJECT, 930007),
    (930015, "geo_e1_section05", "第三节 河流地貌的发育", 3, SUBJECT, 930007),
    (930016, "geo_e1_section06", "第一节 常见天气系统", 1, SUBJECT, 930008),
    (930017, "geo_e1_section07", "第二节 气压带和风带", 2, SUBJECT, 930008),
    (930018, "geo_e1_section08", "第三节 气压带和风带对气候的影响", 3, SUBJECT, 930008),
    (930019, "geo_e1_section09", "第一节 陆地水体及其相互关系", 1, SUBJECT, 930009),
    (930020, "geo_e1_section10", "第二节 洋流", 2, SUBJECT, 930009),
    (930021, "geo_e1_section11", "第三节 海—气相互作用", 3, SUBJECT, 930009),
    (930022, "geo_e1_section12", "第一节 自然环境的整体性", 1, SUBJECT, 930010),
    (930023, "geo_e1_section13", "第二节 自然环境的地域差异性", 2, SUBJECT, 930010),

    # 第一章考点：自转、公转与地球运动的地理意义
    (930031, "geo_e1_point_rotation", "地球自转的方向、周期与速度：自西向东、恒星日与太阳日、角速度与线速度纬度变化", 1, SUBJECT, 930011),
    (930032, "geo_e1_point_revolution", "地球公转的轨道、方向与周期：椭圆轨道、近日点与远日点、恒星年与回归年", 2, SUBJECT, 930011),
    (930033, "geo_e1_point_obliquity", "黄赤交角及其影响：23°26′交角、地轴倾斜与太阳直射点回归运动", 3, SUBJECT, 930011),
    (930034, "geo_e1_point_subsolar", "太阳直射点的回归运动：南北回归线之间的移动规律与二分二至日位置", 4, SUBJECT, 930011),
    (930035, "geo_e1_point_orbit_speed", "地球公转速度的变化：近日点较快、远日点较慢及其对季节长度的影响", 5, SUBJECT, 930011),
    (930036, "geo_e1_point_day_night", "昼夜交替与晨昏线：昼夜半球划分、晨昏线判读及其移动规律", 1, SUBJECT, 930012),
    (930037, "geo_e1_point_local_time", "地方时与区时：经度每15°相差1小时、中央经线与时区换算", 2, SUBJECT, 930012),
    (930038, "geo_e1_point_date_line", "国际日界线与日期变更：180°经线附近、东十二区与西十二区、日期早晚判断", 3, SUBJECT, 930012),
    (930039, "geo_e1_point_coriolis", "沿地表水平运动物体的偏转：地转偏向力、北半球右偏南半球左偏、赤道不偏", 4, SUBJECT, 930012),
    (930040, "geo_e1_point_day_length", "昼夜长短的时空变化：二分二至日昼夜长短规律、极昼极夜范围与纬度关系", 5, SUBJECT, 930012),
    (930041, "geo_e1_point_solar_altitude", "正午太阳高度的变化：纬度分布规律、季节变化与H=90°−纬度差的计算", 6, SUBJECT, 930012),
    (930042, "geo_e1_point_solar_apparent", "太阳视运动与日出日落方位：不同季节与纬度的日出日落方位、影长与影子朝向", 7, SUBJECT, 930012),

    # 第二章考点：内外力作用、构造地貌与河流地貌
    (930043, "geo_e1_point_endogenic", "内力作用与外力作用的对比：能量来源、表现形式与对地表形态的不同影响", 1, SUBJECT, 930013),
    (930044, "geo_e1_point_magmatism", "岩浆活动与火山地貌：喷出型与侵入型岩浆岩、火山锥、熔岩台地与火山口", 2, SUBJECT, 930013),
    (930045, "geo_e1_point_crustal_movement", "地壳运动与地质构造：水平挤压张裂、垂直升降及其对地表形态的影响", 3, SUBJECT, 930013),
    (930046, "geo_e1_point_weathering", "风化作用与风化壳：物理风化、化学风化、生物风化及风化壳的形成", 4, SUBJECT, 930013),
    (930047, "geo_e1_point_erosion_transport", "侵蚀、搬运与堆积作用：流水、风力、冰川、海浪的作用方式与地貌结果", 5, SUBJECT, 930013),
    (930048, "geo_e1_point_fold", "褶皱与背斜向斜：岩层弯曲形态、背斜成山向斜成谷与地形倒置", 1, SUBJECT, 930014),
    (930049, "geo_e1_point_fault", "断层的组成与地貌：断层面、上升岩块与下降岩块、地垒与地堑", 2, SUBJECT, 930014),
    (930050, "geo_e1_point_plate_tectonics", "板块构造学说：六大板块、生长边界与消亡边界、全球火山地震带", 3, SUBJECT, 930014),
    (930051, "geo_e1_point_plate_landform", "板块运动与宏观地貌：碰撞挤压形成高大山脉、张裂形成裂谷与海洋", 4, SUBJECT, 930014),
    (930052, "geo_e1_point_structure_use", "地质构造的实践意义：找水找油、隧道选址、工程建设避让断层", 5, SUBJECT, 930014),
    (930053, "geo_e1_point_river_erosion", "河流侵蚀类型与河谷发育：溯源侵蚀、下蚀、侧蚀与上游V形谷", 1, SUBJECT, 930015),
    (930054, "geo_e1_point_river_deposition", "河流堆积地貌：冲积扇、河漫滩、三角洲的形成条件与分布位置", 2, SUBJECT, 930015),
    (930055, "geo_e1_point_river_terrace", "河流阶地及其成因：地壳抬升、河流下切与多级阶地序列", 3, SUBJECT, 930015),
    (930056, "geo_e1_point_river_settlement", "河流地貌对聚落的影响：河谷平原、冲积扇与河口三角洲的聚落分布", 4, SUBJECT, 930015),
    (930057, "geo_e1_point_river_profile", "河流地貌的观察与剖面分析：河谷横剖面、纵剖面与地貌发育阶段", 5, SUBJECT, 930015),

    # 第三章考点：天气系统、气压带风带与气候
    (930058, "geo_e1_point_front", "锋与天气：冷锋、暖锋、准静止锋的天气特征与过境前后变化", 1, SUBJECT, 930016),
    (930059, "geo_e1_point_cyclone", "低压（气旋）与高压（反气旋）：气流运动、天气现象与典型实例", 2, SUBJECT, 930016),
    (930060, "geo_e1_point_frontal_cyclone", "锋面气旋：低压槽中锋面的形成、温带气旋结构与天气变化", 3, SUBJECT, 930016),
    (930061, "geo_e1_point_weather_map", "天气系统判读：等压线图、锋面符号、风向风力与天气状况判断", 4, SUBJECT, 930016),
    (930062, "geo_e1_point_weather_disaster", "我国主要气象灾害的天气系统成因：寒潮、梅雨、台风与伏旱", 5, SUBJECT, 930016),
    (930063, "geo_e1_point_three_cell", "三圈环流的形成：高低纬受热不均、地转偏向力与七个气压带六个风带", 1, SUBJECT, 930017),
    (930064, "geo_e1_point_belt_shift", "气压带风带的季节移动：随太阳直射点移动，北半球夏季北移、冬季南移", 2, SUBJECT, 930017),
    (930065, "geo_e1_point_land_sea", "海陆分布对气压带的影响：亚洲高压、印度低压与气压带被切断", 3, SUBJECT, 930017),
    (930066, "geo_e1_point_monsoon", "季风环流：东亚季风与南亚季风的成因、盛行风向与降水差异", 4, SUBJECT, 930017),
    (930067, "geo_e1_point_single_control", "单一气压带风带控制的气候：热带雨林、热带沙漠与温带海洋性气候", 1, SUBJECT, 930018),
    (930068, "geo_e1_point_alternating_control", "气压带风带交替控制的气候：地中海气候与热带草原气候的成因特征", 2, SUBJECT, 930018),
    (930069, "geo_e1_point_climate_types", "世界主要气候类型：热带、亚热带、温带与寒带气候的分布与特征", 3, SUBJECT, 930018),
    (930070, "geo_e1_point_climate_cause", "气候类型的成因分析：纬度、大气环流、海陆位置、地形与洋流", 4, SUBJECT, 930018),
    (930071, "geo_e1_point_climate_impact", "气候对自然景观与人类活动的影响：植被类型、农业熟制与民居建筑", 5, SUBJECT, 930018),

    # 第四章考点：陆地水体、洋流与海气相互作用
    (930072, "geo_e1_point_water_types", "陆地水体的类型与作用：河流、湖泊、沼泽、冰川与地下水", 1, SUBJECT, 930019),
    (930073, "geo_e1_point_river_recharge", "河流的补给类型：雨水补给、冰雪融水补给、地下水补给与湖泊水补给", 2, SUBJECT, 930019),
    (930074, "geo_e1_point_river_hydrology", "河流水文特征：流量、汛期、含沙量、结冰期与水位变化", 3, SUBJECT, 930019),
    (930075, "geo_e1_point_lake_river", "湖泊与河流的相互补给：吞吐湖调蓄、内流湖咸化与水位高低决定的流向", 4, SUBJECT, 930019),
    (930076, "geo_e1_point_groundwater", "地下水及其与地表水的转化：潜水、承压水、补给排泄与人类活动影响", 5, SUBJECT, 930019),
    (930077, "geo_e1_point_current_types", "洋流的成因与分类：风海流、密度流、补偿流与寒流暖流", 1, SUBJECT, 930020),
    (930078, "geo_e1_point_current_pattern", "世界洋流分布规律：中低纬副热带环流、北半球中高纬环流与西风漂流", 2, SUBJECT, 930020),
    (930079, "geo_e1_point_current_climate", "洋流对气候的影响：暖流增温增湿、寒流降温减湿与沿岸气候差异", 3, SUBJECT, 930020),
    (930080, "geo_e1_point_current_fishery", "洋流对海洋生物与航行的影响：寒暖流交汇与上升流渔场、顺流逆流航行", 4, SUBJECT, 930020),
    (930081, "geo_e1_point_current_pollution", "洋流对污染物的影响：加快污染物扩散净化、扩大污染范围", 5, SUBJECT, 930020),
    (930082, "geo_e1_point_air_sea_exchange", "海气间的热量与水汽交换：海洋蒸发、潜热释放与大气降水返回海洋", 1, SUBJECT, 930021),
    (930083, "geo_e1_point_walker", "沃克环流与赤道太平洋水温异常：东西太平洋气压与水温的跷跷板关系", 2, SUBJECT, 930021),
    (930084, "geo_e1_point_el_nino", "厄尔尼诺现象：东南信风减弱、赤道逆流增强与全球气候异常", 3, SUBJECT, 930021),
    (930085, "geo_e1_point_la_nina", "拉尼娜现象及其影响：东南信风增强、东太平洋水温偏低与气候响应", 4, SUBJECT, 930021),

    # 第五章考点：自然环境整体性与地域差异性
    (930086, "geo_e1_point_elements_link", "自然地理要素的相互联系：气候、地貌、水文、生物、土壤相互作用", 1, SUBJECT, 930022),
    (930087, "geo_e1_point_holistic_function", "自然环境的整体功能：生产功能、稳定功能与自我调节能力", 2, SUBJECT, 930022),
    (930088, "geo_e1_point_holistic_application", "整体性原理的应用：生态修复、区域开发与工程建设的环境影响评估", 3, SUBJECT, 930022),
    (930089, "geo_e1_point_latitude_zone", "纬度地带性：以热量为基础、自然带由赤道向两极有规律更替", 1, SUBJECT, 930023),
    (930090, "geo_e1_point_longitude_zone", "干湿度地带性：以水分为基础、自然带由沿海向内陆有规律更替", 2, SUBJECT, 930023),
    (930091, "geo_e1_point_vertical_zone", "垂直地域分异：海拔引起的热量水分变化、垂直带谱与雪线高低", 3, SUBJECT, 930023),
    (930092, "geo_e1_point_azonal", "地方性分异与非地带性现象：地形、洋流、海陆分布与局部环境差异", 4, SUBJECT, 930023),
)

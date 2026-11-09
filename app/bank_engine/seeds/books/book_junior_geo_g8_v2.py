"""人教版初中地理八年级下册：中国的地理差异与四大地理区域。"""

from __future__ import annotations

SUBJECT = 9
G8 = 8
BOOK_ID = 1342

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级地理下册",
    "jgeo_g8b",
    42,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (134201, "人教版八年级地理下册", "jgeo_g8b_root", 1, BOOK_ID, None),

    (134202, "第五章 中国的地理差异", "jgeo_g8b_c05", 1, BOOK_ID, 134201),
    (134211, "第一节 四大地理区域的划分", "jgeo_g8b_c05_s01", 1, BOOK_ID, 134202),
    (134212, "第二节 北方地区和南方地区", "jgeo_g8b_c05_s02", 2, BOOK_ID, 134202),
    (134213, "第三节 西北地区和青藏地区", "jgeo_g8b_c05_s03", 3, BOOK_ID, 134202),

    (134203, "第六章 北方地区", "jgeo_g8b_c06", 2, BOOK_ID, 134201),
    (134221, "第一节 自然特征与农业", "jgeo_g8b_c06_s01", 1, BOOK_ID, 134203),
    (134222, "第二节 东北三省", "jgeo_g8b_c06_s02", 2, BOOK_ID, 134203),
    (134223, "第三节 黄土高原", "jgeo_g8b_c06_s03", 3, BOOK_ID, 134203),
    (134224, "第四节 北京", "jgeo_g8b_c06_s04", 4, BOOK_ID, 134203),

    (134204, "第七章 南方地区", "jgeo_g8b_c07", 3, BOOK_ID, 134201),
    (134231, "第一节 自然特征与农业", "jgeo_g8b_c07_s01", 1, BOOK_ID, 134204),
    (134232, "第二节 长江三角洲地区", "jgeo_g8b_c07_s02", 2, BOOK_ID, 134204),
    (134233, "第三节 香港和澳门", "jgeo_g8b_c07_s03", 3, BOOK_ID, 134204),
    (134234, "第四节 台湾省", "jgeo_g8b_c07_s04", 4, BOOK_ID, 134204),

    (134205, "第八章 西北地区", "jgeo_g8b_c08", 4, BOOK_ID, 134201),
    (134241, "第一节 自然特征与农业", "jgeo_g8b_c08_s01", 1, BOOK_ID, 134205),
    (134242, "第二节 塔里木盆地", "jgeo_g8b_c08_s02", 2, BOOK_ID, 134205),

    (134206, "第九章 青藏地区", "jgeo_g8b_c09", 5, BOOK_ID, 134201),
    (134251, "第一节 自然特征与农业", "jgeo_g8b_c09_s01", 1, BOOK_ID, 134206),
    (134252, "第二节 三江源地区", "jgeo_g8b_c09_s02", 2, BOOK_ID, 134206),

    (134207, "第十章 中国在世界中", "jgeo_g8b_c10", 6, BOOK_ID, 134201),
    (134261, "第一节 中国的世界地位", "jgeo_g8b_c10_s01", 1, BOOK_ID, 134207),
    (134262, "第二节 中国的发展与国际责任", "jgeo_g8b_c10_s02", 2, BOOK_ID, 134207),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 242001 册域顶层，242002-242024 为章、节锚点，242025-242099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    (242001, "jgeo_g8b_domain", "初中八下·地理·中国的地理差异·四大地理区域·中国在世界中", 1, SUBJECT, G8, None),

    # 第五章 中国的地理差异
    (242002, "jgeo_g8b_c05", "初中八下·地理·第五章 中国的地理差异", 1, SUBJECT, G8, 242001),
    (242008, "jgeo_g8b_c05_s01", "第一节 四大地理区域的划分", 1, SUBJECT, G8, 242002),
    (242009, "jgeo_g8b_c05_s02", "第二节 北方地区和南方地区", 2, SUBJECT, G8, 242002),
    (242010, "jgeo_g8b_c05_s03", "第三节 西北地区和青藏地区", 3, SUBJECT, G8, 242002),
    (242025, "jgeo_g8b_region_basis", "四大地理区域的划分依据：地理位置、自然地理与人文地理特点的差异", 1, SUBJECT, G8, 242008),
    (242026, "jgeo_g8b_region_four", "四大地理区域：北方地区、南方地区、西北地区、青藏地区", 2, SUBJECT, G8, 242008),
    (242027, "jgeo_g8b_qinling_line", "秦岭—淮河一线的位置与地理意义", 3, SUBJECT, G8, 242008),
    (242028, "jgeo_g8b_qinling_climate", "秦岭—淮河线南北气候差异：气温、降水与干湿地区", 4, SUBJECT, G8, 242008),
    (242029, "jgeo_g8b_qinling_agri", "秦岭—淮河线南北农业差异：耕地类型、主要作物与作物熟制", 5, SUBJECT, G8, 242008),
    (242030, "jgeo_g8b_qinling_other", "秦岭—淮河线南北河流水文、植被与交通运输差异", 6, SUBJECT, G8, 242008),
    (242031, "jgeo_g8b_north_south_natural", "北方地区与南方地区自然环境的差异及成因", 1, SUBJECT, G8, 242009),
    (242032, "jgeo_g8b_north_south_human", "北方地区与南方地区人文活动的差异：农业、交通与聚落", 2, SUBJECT, G8, 242009),
    (242033, "jgeo_g8b_north_south_boundary", "北方地区与南方地区的分界线及划分主导因素", 3, SUBJECT, G8, 242009),
    (242034, "jgeo_g8b_nw_qh_boundary", "西北地区与青藏地区的界线及划分主导因素", 1, SUBJECT, G8, 242010),
    (242035, "jgeo_g8b_nw_qh_natural", "西北地区干旱与青藏地区高寒的自然特征对比", 2, SUBJECT, G8, 242010),

    # 第六章 北方地区
    (242003, "jgeo_g8b_c06", "初中八下·地理·第六章 北方地区", 2, SUBJECT, G8, 242001),
    (242011, "jgeo_g8b_c06_s01", "第一节 自然特征与农业", 1, SUBJECT, G8, 242003),
    (242012, "jgeo_g8b_c06_s02", "第二节 东北三省", 2, SUBJECT, G8, 242003),
    (242013, "jgeo_g8b_c06_s03", "第三节 黄土高原", 3, SUBJECT, G8, 242003),
    (242014, "jgeo_g8b_c06_s04", "第四节 北京", 4, SUBJECT, G8, 242003),
    (242036, "jgeo_g8b_north_location", "北方地区的位置、范围与主要地形区", 1, SUBJECT, G8, 242011),
    (242037, "jgeo_g8b_north_climate", "温带季风气候：冬季寒冷干燥、夏季高温多雨", 2, SUBJECT, G8, 242011),
    (242038, "jgeo_g8b_north_land", "以旱地为主的耕地类型与黑土地、黄土地的分布", 3, SUBJECT, G8, 242011),
    (242039, "jgeo_g8b_north_crop", "小麦、玉米、大豆等旱作农作物与一年一熟至两年三熟", 4, SUBJECT, G8, 242011),
    (242040, "jgeo_g8b_north_drought", "华北平原春旱的成因、水资源短缺与节水农业", 5, SUBJECT, G8, 242011),
    (242041, "jgeo_g8b_north_cash_crop", "温带水果、棉花与花生等经济作物的分布", 6, SUBJECT, G8, 242011),
    (242042, "jgeo_g8b_ne_location", "东北三省的位置、范围与“白山黑水”", 1, SUBJECT, G8, 242012),
    (242043, "jgeo_g8b_ne_terrain", "山环水绕、沃野千里的地形与冷湿气候特征", 2, SUBJECT, G8, 242012),
    (242044, "jgeo_g8b_ne_grain", "商品粮基地：松嫩平原、三江平原与人均耕地多的优势", 3, SUBJECT, G8, 242012),
    (242045, "jgeo_g8b_ne_industry", "重工业基地：辽中南工业基地与哈大工业走廊", 4, SUBJECT, G8, 242012),
    (242046, "jgeo_g8b_ne_revitalize", "东北老工业基地面临的问题与振兴措施", 5, SUBJECT, G8, 242012),
    (242047, "jgeo_g8b_ne_ecology", "东北湿地保护、黑土流失与生态环境修复", 6, SUBJECT, G8, 242012),
    (242048, "jgeo_g8b_loess_range", "黄土高原的范围、位置与主要跨越的省级行政区", 1, SUBJECT, G8, 242013),
    (242049, "jgeo_g8b_loess_origin", "黄土高原黄土的来源与深厚黄土层的形成", 2, SUBJECT, G8, 242013),
    (242050, "jgeo_g8b_loess_erosion_natural", "水土流失的自然原因：土质疏松、降水集中、植被稀少", 3, SUBJECT, G8, 242013),
    (242051, "jgeo_g8b_loess_erosion_human", "水土流失的人为原因与对生产生活的严重危害", 4, SUBJECT, G8, 242013),
    (242052, "jgeo_g8b_loess_control", "水土保持治理：生物措施、工程措施与农业技术措施", 5, SUBJECT, G8, 242013),
    (242053, "jgeo_g8b_beijing_location", "北京的位置、地形与气候特征", 1, SUBJECT, G8, 242014),
    (242054, "jgeo_g8b_beijing_function", "北京的城市职能：政治中心、文化中心、国际交往中心与科技创新中心", 2, SUBJECT, G8, 242014),
    (242055, "jgeo_g8b_beijing_history", "北京作为历史文化名城的名胜古迹与保护", 3, SUBJECT, G8, 242014),
    (242056, "jgeo_g8b_beijing_transport", "北京的综合交通枢纽地位与城市功能区布局", 4, SUBJECT, G8, 242014),

    # 第七章 南方地区
    (242004, "jgeo_g8b_c07", "初中八下·地理·第七章 南方地区", 3, SUBJECT, G8, 242001),
    (242015, "jgeo_g8b_c07_s01", "第一节 自然特征与农业", 1, SUBJECT, G8, 242004),
    (242016, "jgeo_g8b_c07_s02", "第二节 长江三角洲地区", 2, SUBJECT, G8, 242004),
    (242017, "jgeo_g8b_c07_s03", "第三节 香港和澳门", 3, SUBJECT, G8, 242004),
    (242018, "jgeo_g8b_c07_s04", "第四节 台湾省", 4, SUBJECT, G8, 242004),
    (242057, "jgeo_g8b_south_location", "南方地区的位置、范围与主要地形区", 1, SUBJECT, G8, 242015),
    (242058, "jgeo_g8b_south_climate", "亚热带、热带季风气候与湿热的气候特征", 2, SUBJECT, G8, 242015),
    (242059, "jgeo_g8b_south_farming", "水田农业与水稻、油菜、茶、甘蔗的分布", 3, SUBJECT, G8, 242015),
    (242060, "jgeo_g8b_south_terrain", "长江中下游平原、东南丘陵与云贵高原的地形差异", 4, SUBJECT, G8, 242015),
    (242061, "jgeo_g8b_south_red_soil", "红壤的特性、改良措施与丘陵山区农业开发", 5, SUBJECT, G8, 242015),
    (242062, "jgeo_g8b_yd_location", "长江三角洲地区的位置、范围与江海交汇的区位优势", 1, SUBJECT, G8, 242016),
    (242063, "jgeo_g8b_yd_city", "以上海为核心的城市群与同城效应", 2, SUBJECT, G8, 242016),
    (242064, "jgeo_g8b_yd_shanghai", "上海的国际金融、贸易与航运中心地位及辐射带动作用", 3, SUBJECT, G8, 242016),
    (242065, "jgeo_g8b_yd_tourism", "水乡文化与长江三角洲旅游业的发展", 4, SUBJECT, G8, 242016),
    (242066, "jgeo_g8b_hm_location", "香港、澳门的位置、组成与领土范围", 1, SUBJECT, G8, 242017),
    (242067, "jgeo_g8b_hm_economy", "香港国际金融贸易航运中心与澳门博彩旅游业", 2, SUBJECT, G8, 242017),
    (242068, "jgeo_g8b_hm_land", "港澳人多地少、填海造地与高层建筑的发展", 3, SUBJECT, G8, 242017),
    (242069, "jgeo_g8b_hm_mainland", "港澳与祖国内地的密切联系：优势互补与港珠澳大桥", 4, SUBJECT, G8, 242017),
    (242070, "jgeo_g8b_tw_location", "台湾省的位置、范围与台湾岛多山的地形", 1, SUBJECT, G8, 242018),
    (242071, "jgeo_g8b_tw_natural", "台湾的气候、河流特征与森林、矿产等自然资源", 2, SUBJECT, G8, 242018),
    (242072, "jgeo_g8b_tw_economy", "台湾出口导向型经济与主要工业部门", 3, SUBJECT, G8, 242018),
    (242073, "jgeo_g8b_tw_population", "台湾人口、城市分布与两岸文化渊源", 4, SUBJECT, G8, 242018),
    (242074, "jgeo_g8b_tw_territory", "台湾自古以来是中国领土不可分割的一部分", 5, SUBJECT, G8, 242018),

    # 第八章 西北地区
    (242005, "jgeo_g8b_c08", "初中八下·地理·第八章 西北地区", 4, SUBJECT, G8, 242001),
    (242019, "jgeo_g8b_c08_s01", "第一节 自然特征与农业", 1, SUBJECT, G8, 242005),
    (242020, "jgeo_g8b_c08_s02", "第二节 塔里木盆地", 2, SUBJECT, G8, 242005),
    (242075, "jgeo_g8b_nw_location", "西北地区的位置、范围与深居内陆的地理位置", 1, SUBJECT, G8, 242019),
    (242076, "jgeo_g8b_nw_arid", "西北地区干旱的自然特征及其成因", 2, SUBJECT, G8, 242019),
    (242077, "jgeo_g8b_nw_landscape", "草原—荒漠草原—荒漠的景观东西变化", 3, SUBJECT, G8, 242019),
    (242078, "jgeo_g8b_nw_herding", "畜牧业基地与灌溉农业、绿洲农业的分布", 4, SUBJECT, G8, 242019),
    (242079, "jgeo_g8b_nw_oasis", "绿洲分布与水源条件、坎儿井的作用", 5, SUBJECT, G8, 242019),
    (242080, "jgeo_g8b_nw_desertification", "土地荒漠化的成因、危害与生态治理措施", 6, SUBJECT, G8, 242019),
    (242081, "jgeo_g8b_tarim_location", "塔里木盆地的位置与“三山夹两盆”的地形格局", 1, SUBJECT, G8, 242020),
    (242082, "jgeo_g8b_tarim_oil", "塔里木盆地丰富的油气资源与西气东输工程", 2, SUBJECT, G8, 242020),
    (242083, "jgeo_g8b_tarim_oasis", "塔里木盆地绿洲、城镇与交通线的分布", 3, SUBJECT, G8, 242020),
    (242084, "jgeo_g8b_tarim_ecology", "塔里木河流域生态保护与胡杨林修复", 4, SUBJECT, G8, 242020),

    # 第九章 青藏地区
    (242006, "jgeo_g8b_c09", "初中八下·地理·第九章 青藏地区", 5, SUBJECT, G8, 242001),
    (242021, "jgeo_g8b_c09_s01", "第一节 自然特征与农业", 1, SUBJECT, G8, 242006),
    (242022, "jgeo_g8b_c09_s02", "第二节 三江源地区", 2, SUBJECT, G8, 242006),
    (242085, "jgeo_g8b_qh_location", "青藏地区的位置、范围与“世界屋脊”", 1, SUBJECT, G8, 242021),
    (242086, "jgeo_g8b_qh_cold", "青藏地区高寒的自然特征及其成因", 2, SUBJECT, G8, 242021),
    (242087, "jgeo_g8b_qh_landscape", "雪山、冰川、湖泊与高寒草甸的分布", 3, SUBJECT, G8, 242021),
    (242088, "jgeo_g8b_qh_valley_agri", "河谷农业：雅鲁藏布江谷地、湟水谷地与青稞、小麦", 4, SUBJECT, G8, 242021),
    (242089, "jgeo_g8b_qh_herding", "高寒牧业与牦牛、藏绵羊、藏山羊", 5, SUBJECT, G8, 242021),
    (242090, "jgeo_g8b_qh_railway", "青藏铁路的建设意义与沿线生态环境保护", 6, SUBJECT, G8, 242021),
    (242091, "jgeo_g8b_sjy_location", "三江源地区的位置与“中华水塔”的含义", 1, SUBJECT, G8, 242022),
    (242092, "jgeo_g8b_sjy_fragile", "三江源生态环境的脆弱性及退化问题", 2, SUBJECT, G8, 242022),
    (242093, "jgeo_g8b_sjy_park", "三江源国家公园建设与生态保护措施", 3, SUBJECT, G8, 242022),
    (242094, "jgeo_g8b_sjy_significance", "三江源生态保护对江河下游与全国的意义", 4, SUBJECT, G8, 242022),

    # 第十章 中国在世界中
    (242007, "jgeo_g8b_c10", "初中八下·地理·第十章 中国在世界中", 6, SUBJECT, G8, 242001),
    (242023, "jgeo_g8b_c10_s01", "第一节 中国的世界地位", 1, SUBJECT, G8, 242007),
    (242024, "jgeo_g8b_c10_s02", "第二节 中国的发展与国际责任", 2, SUBJECT, G8, 242007),
    (242095, "jgeo_g8b_china_status", "中国在世界中的地位：世界第二大经济体与最大的发展中国家", 1, SUBJECT, G8, 242023),
    (242096, "jgeo_g8b_china_trade", "中国对外贸易的发展与“一带一路”倡议", 2, SUBJECT, G8, 242023),
    (242097, "jgeo_g8b_china_responsibility", "中国在国际事务中的责任与大国担当", 1, SUBJECT, G8, 242024),
    (242098, "jgeo_g8b_china_climate", "应对全球气候变化与可持续发展合作", 2, SUBJECT, G8, 242024),
    (242099, "jgeo_g8b_china_peace", "维护世界和平与构建人类命运共同体", 3, SUBJECT, G8, 242024),
)

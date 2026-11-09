"""统编版（2019）高中历史必修中外历史纲要（下）：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 8
G10 = 10
BOOK_ID = 8102

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中历史必修中外历史纲要（下）",
    "hist_r2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (820101, "第一单元 古代文明的产生与发展", "hist_r2_u01", 1, BOOK_ID, None),
    (820102, "第二单元 中古时期的世界", "hist_r2_u02", 2, BOOK_ID, None),
    (820103, "第三单元 走向整体的世界", "hist_r2_u03", 3, BOOK_ID, None),
    (820104, "第四单元 资本主义制度的确立", "hist_r2_u04", 4, BOOK_ID, None),
    (820105, "第五单元 工业革命与马克思主义的诞生", "hist_r2_u05", 5, BOOK_ID, None),
    (820106, "第六单元 世界殖民体系与亚非拉民族独立运动", "hist_r2_u06", 6, BOOK_ID, None),
    (820107, "第七单元 两次世界大战、十月革命与国际秩序的演变", "hist_r2_u07", 7, BOOK_ID, None),
    (820108, "第八单元 20世纪下半叶世界的新变化", "hist_r2_u08", 8, BOOK_ID, None),
    (820109, "第九单元 当代世界发展的特点与主要趋势", "hist_r2_u09", 9, BOOK_ID, None),
    (820111, "第1课 文明的产生与早期发展", "hist_r2_l01", 1, BOOK_ID, 820101),
    (820112, "第2课 古代世界的帝国与文明的交流", "hist_r2_l02", 2, BOOK_ID, 820101),
    (820113, "第3课 中古时期的欧洲", "hist_r2_l03", 1, BOOK_ID, 820102),
    (820114, "第4课 中古时期的亚洲", "hist_r2_l04", 2, BOOK_ID, 820102),
    (820115, "第5课 古代非洲与美洲", "hist_r2_l05", 3, BOOK_ID, 820102),
    (820116, "第6课 全球航路的开辟", "hist_r2_l06", 1, BOOK_ID, 820103),
    (820117, "第7课 全球联系的初步建立与世界格局的演变", "hist_r2_l07", 2, BOOK_ID, 820103),
    (820118, "第8课 欧洲的思想解放运动", "hist_r2_l08", 1, BOOK_ID, 820104),
    (820119, "第9课 资产阶级革命与资本主义制度的确立", "hist_r2_l09", 2, BOOK_ID, 820104),
    (820120, "第10课 影响世界的工业革命", "hist_r2_l10", 1, BOOK_ID, 820105),
    (820121, "第11课 马克思主义的诞生与传播", "hist_r2_l11", 2, BOOK_ID, 820105),
    (820122, "第12课 资本主义世界殖民体系的形成", "hist_r2_l12", 1, BOOK_ID, 820106),
    (820123, "第13课 亚非拉民族独立运动", "hist_r2_l13", 2, BOOK_ID, 820106),
    (820124, "第14课 第一次世界大战与战后国际秩序", "hist_r2_l14", 1, BOOK_ID, 820107),
    (820125, "第15课 十月革命的胜利与苏联的社会主义实践", "hist_r2_l15", 2, BOOK_ID, 820107),
    (820126, "第16课 亚非拉民族民主运动的高涨", "hist_r2_l16", 3, BOOK_ID, 820107),
    (820127, "第17课 第二次世界大战与战后国际秩序的形成", "hist_r2_l17", 4, BOOK_ID, 820107),
    (820128, "第18课 冷战与国际格局的演变", "hist_r2_l18", 1, BOOK_ID, 820108),
    (820129, "第19课 资本主义国家的新变化", "hist_r2_l19", 2, BOOK_ID, 820108),
    (820130, "第20课 社会主义国家的发展与变化", "hist_r2_l20", 3, BOOK_ID, 820108),
    (820131, "第21课 世界殖民体系的瓦解与新兴国家的发展", "hist_r2_l21", 4, BOOK_ID, 820108),
    (820132, "第22课 世界多极化与经济全球化", "hist_r2_l22", 1, BOOK_ID, 820109),
    (820133, "第23课 和平发展合作共赢的时代潮流", "hist_r2_l23", 2, BOOK_ID, 820109),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 82 00 xx 为册域、单元域与课域结构层，82 02 xx 为考点层，避开章节 82 01 xx 段。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (820001, "hist_r2_domain_ancient", "上古文明：早期文明、古代帝国与区域交流", 1, SUBJECT, G10, None),
    (820002, "hist_r2_domain_medieval", "中古世界：欧洲封建、亚洲帝国与非洲美洲文明", 2, SUBJECT, G10, None),
    (820003, "hist_r2_domain_global_turn", "走向整体：新航路开辟与全球联系的建立", 3, SUBJECT, G10, None),
    (820004, "hist_r2_domain_capitalist", "资本主义确立：思想解放与资产阶级革命", 4, SUBJECT, G10, None),
    (820005, "hist_r2_domain_industry_marxism", "工业革命与马克思主义：技术变革与科学社会主义", 5, SUBJECT, G10, None),
    (820006, "hist_r2_domain_colonial", "殖民体系与民族独立：世界殖民体系与亚非拉觉醒", 6, SUBJECT, G10, None),
    (820007, "hist_r2_domain_wars_revolution", "两次大战与十月革命：战争、革命与国际秩序", 7, SUBJECT, G10, None),
    (820008, "hist_r2_domain_cold_war", "冷战与新变化：两极格局、资本主义调整与社会主义演变", 8, SUBJECT, G10, None),
    (820009, "hist_r2_domain_contemporary", "当代世界：多极化、全球化与和平发展", 9, SUBJECT, G10, None),

    # 单元域层
    (820010, "hist_r2_unit01", "第一单元 古代文明的产生与发展", 1, SUBJECT, G10, 820001),
    (820011, "hist_r2_unit02", "第二单元 中古时期的世界", 1, SUBJECT, G10, 820002),
    (820012, "hist_r2_unit03", "第三单元 走向整体的世界", 1, SUBJECT, G10, 820003),
    (820013, "hist_r2_unit04", "第四单元 资本主义制度的确立", 1, SUBJECT, G10, 820004),
    (820014, "hist_r2_unit05", "第五单元 工业革命与马克思主义的诞生", 1, SUBJECT, G10, 820005),
    (820015, "hist_r2_unit06", "第六单元 世界殖民体系与亚非拉民族独立运动", 1, SUBJECT, G10, 820006),
    (820016, "hist_r2_unit07", "第七单元 两次世界大战、十月革命与国际秩序的演变", 1, SUBJECT, G10, 820007),
    (820017, "hist_r2_unit08", "第八单元 20世纪下半叶世界的新变化", 1, SUBJECT, G10, 820008),
    (820018, "hist_r2_unit09", "第九单元 当代世界发展的特点与主要趋势", 1, SUBJECT, G10, 820009),

    # 课域层
    (820019, "hist_r2_lesson01", "第1课 文明的产生与早期发展", 1, SUBJECT, G10, 820010),
    (820020, "hist_r2_lesson02", "第2课 古代世界的帝国与文明的交流", 2, SUBJECT, G10, 820010),
    (820021, "hist_r2_lesson03", "第3课 中古时期的欧洲", 1, SUBJECT, G10, 820011),
    (820022, "hist_r2_lesson04", "第4课 中古时期的亚洲", 2, SUBJECT, G10, 820011),
    (820023, "hist_r2_lesson05", "第5课 古代非洲与美洲", 3, SUBJECT, G10, 820011),
    (820024, "hist_r2_lesson06", "第6课 全球航路的开辟", 1, SUBJECT, G10, 820012),
    (820025, "hist_r2_lesson07", "第7课 全球联系的初步建立与世界格局的演变", 2, SUBJECT, G10, 820012),
    (820026, "hist_r2_lesson08", "第8课 欧洲的思想解放运动", 1, SUBJECT, G10, 820013),
    (820027, "hist_r2_lesson09", "第9课 资产阶级革命与资本主义制度的确立", 2, SUBJECT, G10, 820013),
    (820028, "hist_r2_lesson10", "第10课 影响世界的工业革命", 1, SUBJECT, G10, 820014),
    (820029, "hist_r2_lesson11", "第11课 马克思主义的诞生与传播", 2, SUBJECT, G10, 820014),
    (820030, "hist_r2_lesson12", "第12课 资本主义世界殖民体系的形成", 1, SUBJECT, G10, 820015),
    (820031, "hist_r2_lesson13", "第13课 亚非拉民族独立运动", 2, SUBJECT, G10, 820015),
    (820032, "hist_r2_lesson14", "第14课 第一次世界大战与战后国际秩序", 1, SUBJECT, G10, 820016),
    (820033, "hist_r2_lesson15", "第15课 十月革命的胜利与苏联的社会主义实践", 2, SUBJECT, G10, 820016),
    (820034, "hist_r2_lesson16", "第16课 亚非拉民族民主运动的高涨", 3, SUBJECT, G10, 820016),
    (820035, "hist_r2_lesson17", "第17课 第二次世界大战与战后国际秩序的形成", 4, SUBJECT, G10, 820016),
    (820036, "hist_r2_lesson18", "第18课 冷战与国际格局的演变", 1, SUBJECT, G10, 820017),
    (820037, "hist_r2_lesson19", "第19课 资本主义国家的新变化", 2, SUBJECT, G10, 820017),
    (820038, "hist_r2_lesson20", "第20课 社会主义国家的发展与变化", 3, SUBJECT, G10, 820017),
    (820039, "hist_r2_lesson21", "第21课 世界殖民体系的瓦解与新兴国家的发展", 4, SUBJECT, G10, 820017),
    (820040, "hist_r2_lesson22", "第22课 世界多极化与经济全球化", 1, SUBJECT, G10, 820018),
    (820041, "hist_r2_lesson23", "第23课 和平发展合作共赢的时代潮流", 2, SUBJECT, G10, 820018),

    # 第一单元考点
    (820201, "hist_r2_point_agrarian_revolution", "农业革命与文明产生：农耕畜牧、剩余产品与阶级国家出现", 1, SUBJECT, G10, 820019),
    (820202, "hist_r2_point_river_civilizations", "古代大河文明：两河、埃及与印度的早期国家及文字", 2, SUBJECT, G10, 820019),
    (820203, "hist_r2_point_greek_polis", "古希腊城邦政治：雅典民主制度与斯巴达寡头政治", 3, SUBJECT, G10, 820019),
    (820204, "hist_r2_point_rome_origin", "古罗马的兴起：从共和国到帝国与罗马法的发展", 4, SUBJECT, G10, 820019),
    (820205, "hist_r2_point_persian_empire", "波斯帝国：行省制度、君主专制与驿道体系", 1, SUBJECT, G10, 820020),
    (820206, "hist_r2_point_hellenistic", "亚历山大帝国与希腊化时代：东西方文化交汇", 2, SUBJECT, G10, 820020),
    (820207, "hist_r2_point_roman_empire", "罗马帝国的统治：“罗马和平”、基督教兴起与帝国分裂", 3, SUBJECT, G10, 820020),
    (820208, "hist_r2_point_silk_road_ancient", "丝绸之路与古代东西方文明交流", 4, SUBJECT, G10, 820020),

    # 第二单元考点
    (820209, "hist_r2_point_feudal_lords", "封君封臣制度与封建等级：土地封赐、契约关系与骑士", 1, SUBJECT, G10, 820021),
    (820210, "hist_r2_point_manor_serfdom", "庄园与农奴制：自给自足的庄园经济与领主法庭", 2, SUBJECT, G10, 820021),
    (820211, "hist_r2_point_medieval_city", "中古城市兴起：自治斗争、市民阶层与行会经济", 3, SUBJECT, G10, 820021),
    (820212, "hist_r2_point_church_kingship", "中古西欧教会与王权：教权王权之争与等级君主制", 4, SUBJECT, G10, 820021),
    (820213, "hist_r2_point_byzantium_rus", "拜占庭帝国与俄罗斯：查士丁尼法典、基辅罗斯与莫斯科公国", 5, SUBJECT, G10, 820021),
    (820214, "hist_r2_point_arab_empire", "阿拉伯帝国：伊斯兰教创立、哈里发制度与东西文化交流", 1, SUBJECT, G10, 820022),
    (820215, "hist_r2_point_ottoman", "奥斯曼帝国：攻陷君士坦丁堡、苏丹专制与跨三洲统治", 2, SUBJECT, G10, 820022),
    (820216, "hist_r2_point_india_sultanates", "笈多帝国与德里苏丹国：印度中古政权的更替", 3, SUBJECT, G10, 820022),
    (820217, "hist_r2_point_east_asia_medieval", "东亚中古文明：日本大化改新、幕府政治与朝鲜王朝", 4, SUBJECT, G10, 820022),
    (820218, "hist_r2_point_africa_ancient", "古代非洲文明：班图人迁徙、东非城邦与西非加纳马里桑海", 1, SUBJECT, G10, 820023),
    (820219, "hist_r2_point_aksum_zimbabwe", "阿克苏姆与津巴布韦：非洲基督教文明与石头城遗址", 2, SUBJECT, G10, 820023),
    (820220, "hist_r2_point_america_ancient", "古代美洲文明：玛雅、阿兹特克与印加及其独立发展", 3, SUBJECT, G10, 820023),

    # 第三单元考点
    (820221, "hist_r2_point_age_discovery_bg", "新航路开辟背景：经济动因、商路受阻、精神动力与技术条件", 1, SUBJECT, G10, 820024),
    (820222, "hist_r2_point_portugal_route", "葡萄牙东方航线：迪亚士、达·伽马与好望角航线", 2, SUBJECT, G10, 820024),
    (820223, "hist_r2_point_columbus_magellan", "西班牙跨洋航行：哥伦布到达美洲与麦哲伦船队环球", 3, SUBJECT, G10, 820024),
    (820224, "hist_r2_point_other_routes", "其他航路探索：北大西洋、南太平洋航线与世界海路联网", 4, SUBJECT, G10, 820024),
    (820225, "hist_r2_point_columbian_exchange", "人口迁移与物种交换：哥伦布大交换与美洲人口剧变", 1, SUBJECT, G10, 820025),
    (820226, "hist_r2_point_triangle_trade", "商品世界性流动：三角贸易、马尼拉大帆船与白银东流", 2, SUBJECT, G10, 820025),
    (820227, "hist_r2_point_early_colonization", "早期殖民扩张：葡西荷英法的争夺与东印度公司", 3, SUBJECT, G10, 820025),
    (820228, "hist_r2_point_price_commercial_revolution", "价格革命与商业革命：欧洲社会转型与世界格局演变", 4, SUBJECT, G10, 820025),

    # 第四单元考点
    (820229, "hist_r2_point_renaissance", "文艺复兴：人文主义内涵、代表作品与思想解放意义", 1, SUBJECT, G10, 820026),
    (820230, "hist_r2_point_reformation", "宗教改革：马丁·路德因信称义、加尔文宗与英国国教", 2, SUBJECT, G10, 820026),
    (820231, "hist_r2_point_scientific_revolution", "近代科学革命：哥白尼日心说、伽利略实验与牛顿力学", 3, SUBJECT, G10, 820026),
    (820232, "hist_r2_point_enlightenment", "启蒙运动：理性主义、三权分立、社会契约与人民主权", 4, SUBJECT, G10, 820026),
    (820233, "hist_r2_point_english_revolution", "英国资产阶级革命与君主立宪：《权利法案》与议会主权", 1, SUBJECT, G10, 820027),
    (820234, "hist_r2_point_us_constitution", "美国独立战争与1787年宪法：联邦制与三权分立", 2, SUBJECT, G10, 820027),
    (820235, "hist_r2_point_french_revolution", "法国大革命与拿破仑帝国：《人权宣言》与《拿破仑法典》", 3, SUBJECT, G10, 820027),
    (820236, "hist_r2_point_capitalism_expansion", "资本主义制度扩展：俄国农奴制改革、日本明治维新与德意统一", 4, SUBJECT, G10, 820027),

    # 第五单元考点
    (820237, "hist_r2_point_industrial_bg", "工业革命前提：资本积累、自由劳动力、海外市场与技术", 1, SUBJECT, G10, 820028),
    (820238, "hist_r2_point_first_industrial", "第一次工业革命：珍妮机、瓦特蒸汽机与英国世界工厂", 2, SUBJECT, G10, 820028),
    (820239, "hist_r2_point_second_industrial", "第二次工业革命：电力、内燃机、化学工业与垄断组织", 3, SUBJECT, G10, 820028),
    (820240, "hist_r2_point_industrial_impact", "工业革命影响：生产力飞跃、社会分化与世界市场形成", 4, SUBJECT, G10, 820028),
    (820241, "hist_r2_point_marxism_conditions", "马克思主义诞生条件：工业革命、工人运动与三大理论来源", 1, SUBJECT, G10, 820029),
    (820242, "hist_r2_point_communist_manifesto", "《共产党宣言》：唯物史观、阶级斗争与无产阶级使命", 2, SUBJECT, G10, 820029),
    (820243, "hist_r2_point_surplus_value", "剩余价值学说：资本主义剥削秘密与马克思主义科学性", 3, SUBJECT, G10, 820029),
    (820244, "hist_r2_point_first_international", "第一国际、巴黎公社与马克思主义的世界传播", 4, SUBJECT, G10, 820029),

    # 第六单元考点
    (820245, "hist_r2_point_latin_colonization", "拉丁美洲殖民地化：西葡统治、种植园经济与奴隶贸易", 1, SUBJECT, G10, 820030),
    (820246, "hist_r2_point_asia_colonization", "亚洲殖民地半殖民地化：印度、东南亚与西亚的沦陷", 2, SUBJECT, G10, 820030),
    (820247, "hist_r2_point_scramble_africa", "瓜分非洲：柏林会议、有效占领与列强殖民争夺", 3, SUBJECT, G10, 820030),
    (820248, "hist_r2_point_colonial_system_formed", "资本主义世界殖民体系的形成与历史影响", 4, SUBJECT, G10, 820030),
    (820249, "hist_r2_point_latin_independence", "拉美独立运动：玻利瓦尔、圣马丁与海地革命", 1, SUBJECT, G10, 820031),
    (820250, "hist_r2_point_asia_awakening", "亚洲的觉醒：印度国大党、伊朗立宪革命与辛亥革命", 2, SUBJECT, G10, 820031),
    (820251, "hist_r2_point_africa_resistance", "非洲抗争：阿拉比抗英与埃塞俄比亚抗意战争", 3, SUBJECT, G10, 820031),
    (820252, "hist_r2_point_national_movement_feature", "亚非拉民族独立运动的特点与历史意义", 4, SUBJECT, G10, 820031),

    # 第七单元考点
    (820253, "hist_r2_point_ww1_background", "一战背景：帝国主义矛盾激化与两大军事集团对峙", 1, SUBJECT, G10, 820032),
    (820254, "hist_r2_point_ww1_process", "一战进程与性质：马恩河、凡尔登、索姆河与美国参战", 2, SUBJECT, G10, 820032),
    (820255, "hist_r2_point_versailles_washington", "凡尔赛—华盛顿体系：巴黎和会、国际联盟与华盛顿会议", 3, SUBJECT, G10, 820032),
    (820256, "hist_r2_point_ww1_impact", "一战影响：欧洲衰落、民族觉醒与俄国革命契机", 4, SUBJECT, G10, 820032),
    (820257, "hist_r2_point_october_revolution", "十月革命进程：二月革命、《四月提纲》与彼得格勒起义", 1, SUBJECT, G10, 820033),
    (820258, "hist_r2_point_soviet_power", "苏维埃政权建立：和平法令、土地法令与战时共产主义", 2, SUBJECT, G10, 820033),
    (820259, "hist_r2_point_nep", "新经济政策：粮食税、市场调节与国民经济恢复", 3, SUBJECT, G10, 820033),
    (820260, "hist_r2_point_soviet_model", "苏联模式：工业化、农业集体化与高度集中体制评价", 4, SUBJECT, G10, 820033),
    (820261, "hist_r2_point_gandhi", "印度非暴力不合作运动：甘地、食盐进军与民族觉醒", 1, SUBJECT, G10, 820034),
    (820262, "hist_r2_point_kemal", "土耳其凯末尔革命：民族独立与世俗化改革", 2, SUBJECT, G10, 820034),
    (820263, "hist_r2_point_egypt_latin_movement", "埃及华夫脱运动与拉美民族民主运动：卡德纳斯改革等", 3, SUBJECT, G10, 820034),
    (820264, "hist_r2_point_interwar_national_feature", "一战后亚非拉民族民主运动高涨的特点与影响", 4, SUBJECT, G10, 820034),
    (820265, "hist_r2_point_ww2_background", "二战背景：经济大危机、法西斯专政与绥靖政策", 1, SUBJECT, G10, 820035),
    (820266, "hist_r2_point_ww2_process", "二战进程：全面爆发、苏德战争、太平洋战争与战略转折", 2, SUBJECT, G10, 820035),
    (820267, "hist_r2_point_anti_fascist_alliance", "世界反法西斯同盟：《联合国家宣言》、第二战场与胜利", 3, SUBJECT, G10, 820035),
    (820268, "hist_r2_point_yalta_un", "雅尔塔体系与联合国：战后国际秩序的两重性", 4, SUBJECT, G10, 820035),

    # 第八单元考点
    (820269, "hist_r2_point_cold_war_origin", "冷战起源：铁幕演说、杜鲁门主义与马歇尔计划", 1, SUBJECT, G10, 820036),
    (820270, "hist_r2_point_cold_war_events", "冷战表现：德国分裂、柏林危机与古巴导弹危机", 2, SUBJECT, G10, 820036),
    (820271, "hist_r2_point_multipolarity_trend", "多极化趋势：欧共体、日本崛起与不结盟运动", 3, SUBJECT, G10, 820036),
    (820272, "hist_r2_point_bipolar_collapse", "两极格局瓦解：东欧剧变与苏联解体", 4, SUBJECT, G10, 820036),
    (820273, "hist_r2_point_state_macro_control", "国家宏观调控：凯恩斯主义、罗斯福新政与混合经济", 1, SUBJECT, G10, 820037),
    (820274, "hist_r2_point_welfare_state", "福利国家：社会保障体系建立、发展与弊端", 2, SUBJECT, G10, 820037),
    (820275, "hist_r2_point_third_tech_revolution", "第三次科技革命：原子能、计算机与航天技术", 3, SUBJECT, G10, 820037),
    (820276, "hist_r2_point_social_structure_change", "社会结构与政策新变化：中间阶层、第三产业与新自由主义", 4, SUBJECT, G10, 820037),
    (820277, "hist_r2_point_soviet_reforms", "战后苏联改革：赫鲁晓夫、勃列日涅夫与戈尔巴乔夫", 1, SUBJECT, G10, 820038),
    (820278, "hist_r2_point_eastern_europe_reform", "东欧社会主义改革：南斯拉夫自治、匈牙利与捷克斯洛伐克", 2, SUBJECT, G10, 820038),
    (820279, "hist_r2_point_soviet_collapse_reason", "东欧剧变与苏联解体的原因及历史教训", 3, SUBJECT, G10, 820038),
    (820280, "hist_r2_point_china_socialism", "中国社会主义道路：改革开放与中国特色社会主义成就", 4, SUBJECT, G10, 820038),
    (820281, "hist_r2_point_asia_independence", "亚洲民族独立：印巴分治、印度独立与东南亚国家独立", 1, SUBJECT, G10, 820039),
    (820282, "hist_r2_point_africa_independence", "非洲独立浪潮：1960年非洲年与纳米比亚独立", 2, SUBJECT, G10, 820039),
    (820283, "hist_r2_point_latin_sovereignty", "拉美捍卫主权：古巴革命与巴拿马运河主权收回", 3, SUBJECT, G10, 820039),
    (820284, "hist_r2_point_emerging_nations", "新兴国家发展：不结盟运动、南南合作与面临的挑战", 4, SUBJECT, G10, 820039),

    # 第九单元考点
    (820285, "hist_r2_point_multipolar_world", "世界多极化：一超多强与欧盟、俄罗斯、中国等力量中心", 1, SUBJECT, G10, 820040),
    (820286, "hist_r2_point_economic_globalization", "经济全球化：世界贸易组织、区域集团化与跨国资本", 2, SUBJECT, G10, 820040),
    (820287, "hist_r2_point_information_society", "社会信息化：互联网、数字经济与信息安全", 3, SUBJECT, G10, 820040),
    (820288, "hist_r2_point_cultural_diversity", "文化多样性与全球性问题：文明互鉴与全球治理挑战", 4, SUBJECT, G10, 820040),
    (820289, "hist_r2_point_peace_development", "和平与发展是时代主题：两大问题的内涵与相互关系", 1, SUBJECT, G10, 820041),
    (820290, "hist_r2_point_global_governance", "全球治理体系：联合国、二十国集团与金砖国家合作", 2, SUBJECT, G10, 820041),
    (820291, "hist_r2_point_community_shared_future", "构建人类命运共同体：一带一路与共商共建共享", 3, SUBJECT, G10, 820041),
    (820292, "hist_r2_point_china_responsibility", "中国的大国担当：多边主义、全球发展倡议与南南合作", 4, SUBJECT, G10, 820041),
)

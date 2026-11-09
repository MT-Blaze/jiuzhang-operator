"""统编版世界历史九年级上册：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 8
G9 = 9
BOOK_ID = 1323

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版世界历史九年级上册",
    "jhis_g9a",
    23,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 古代亚非文明
    (132301, "第一单元 古代亚非文明", "jhis_g9a_u01", 1, BOOK_ID, None),
    (132311, "第1课 古代埃及", "jhis_g9a_l01", 1, BOOK_ID, 132301),
    (132312, "第2课 古代两河流域", "jhis_g9a_l02", 2, BOOK_ID, 132301),
    (132313, "第3课 古代印度", "jhis_g9a_l03", 3, BOOK_ID, 132301),

    # 第二单元 古代欧洲文明
    (132302, "第二单元 古代欧洲文明", "jhis_g9a_u02", 2, BOOK_ID, None),
    (132321, "第4课 希腊城邦和亚历山大帝国", "jhis_g9a_l04", 1, BOOK_ID, 132302),
    (132322, "第5课 罗马城邦和罗马帝国", "jhis_g9a_l05", 2, BOOK_ID, 132302),
    (132323, "第6课 希腊罗马古典文化", "jhis_g9a_l06", 3, BOOK_ID, 132302),

    # 第三单元 封建时代的欧洲
    (132303, "第三单元 封建时代的欧洲", "jhis_g9a_u03", 3, BOOK_ID, None),
    (132331, "第7课 基督教的兴起和法兰克王国", "jhis_g9a_l07", 1, BOOK_ID, 132303),
    (132332, "第8课 西欧庄园", "jhis_g9a_l08", 2, BOOK_ID, 132303),
    (132333, "第9课 中世纪城市和大学的兴起", "jhis_g9a_l09", 3, BOOK_ID, 132303),
    (132334, "第10课 拜占庭帝国和《查士丁尼法典》", "jhis_g9a_l10", 4, BOOK_ID, 132303),

    # 第四单元 封建时代的亚洲国家
    (132304, "第四单元 封建时代的亚洲国家", "jhis_g9a_u04", 4, BOOK_ID, None),
    (132341, "第11课 古代日本", "jhis_g9a_l11", 1, BOOK_ID, 132304),
    (132342, "第12课 阿拉伯帝国", "jhis_g9a_l12", 2, BOOK_ID, 132304),

    # 第五单元 步入近代
    (132305, "第五单元 步入近代", "jhis_g9a_u05", 5, BOOK_ID, None),
    (132351, "第13课 西欧经济和社会的发展", "jhis_g9a_l13", 1, BOOK_ID, 132305),
    (132352, "第14课 文艺复兴运动", "jhis_g9a_l14", 2, BOOK_ID, 132305),
    (132353, "第15课 探寻新航路", "jhis_g9a_l15", 3, BOOK_ID, 132305),
    (132354, "第16课 早期殖民掠夺", "jhis_g9a_l16", 4, BOOK_ID, 132305),

    # 第六单元 资本主义制度的初步确立
    (132306, "第六单元 资本主义制度的初步确立", "jhis_g9a_u06", 6, BOOK_ID, None),
    (132361, "第17课 君主立宪制的英国", "jhis_g9a_l17", 1, BOOK_ID, 132306),
    (132362, "第18课 美国的独立", "jhis_g9a_l18", 2, BOOK_ID, 132306),
    (132363, "第19课 法国大革命和拿破仑帝国", "jhis_g9a_l19", 3, BOOK_ID, 132306),

    # 第七单元 工业革命和工人运动的兴起
    (132307, "第七单元 工业革命和工人运动的兴起", "jhis_g9a_u07", 7, BOOK_ID, None),
    (132371, "第20课 第一次工业革命", "jhis_g9a_l20", 1, BOOK_ID, 132307),
    (132372, "第21课 马克思主义的诞生和国际共产主义运动的兴起", "jhis_g9a_l21", 2, BOOK_ID, 132307),
)

# id / code / name / sort_order / subject_id / parent_id
# 223001-223021 为册域层，223022-223093 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (223001, "jhis_g9a_domain_egypt", "初中九上·古代埃及", 1, SUBJECT, None),
    (223002, "jhis_g9a_domain_mesopotamia", "初中九上·古代两河流域", 2, SUBJECT, None),
    (223003, "jhis_g9a_domain_india", "初中九上·古代印度", 3, SUBJECT, None),
    (223004, "jhis_g9a_domain_greece", "初中九上·希腊城邦和亚历山大帝国", 4, SUBJECT, None),
    (223005, "jhis_g9a_domain_rome", "初中九上·罗马城邦和罗马帝国", 5, SUBJECT, None),
    (223006, "jhis_g9a_domain_classical_culture", "初中九上·希腊罗马古典文化", 6, SUBJECT, None),
    (223007, "jhis_g9a_domain_franks", "初中九上·基督教的兴起和法兰克王国", 7, SUBJECT, None),
    (223008, "jhis_g9a_domain_manor", "初中九上·西欧庄园", 8, SUBJECT, None),
    (223009, "jhis_g9a_domain_medieval_city", "初中九上·中世纪城市和大学的兴起", 9, SUBJECT, None),
    (223010, "jhis_g9a_domain_byzantium", "初中九上·拜占庭帝国和《查士丁尼法典》", 10, SUBJECT, None),
    (223011, "jhis_g9a_domain_japan", "初中九上·古代日本", 11, SUBJECT, None),
    (223012, "jhis_g9a_domain_arab", "初中九上·阿拉伯帝国", 12, SUBJECT, None),
    (223013, "jhis_g9a_domain_economy", "初中九上·西欧经济和社会的发展", 13, SUBJECT, None),
    (223014, "jhis_g9a_domain_renaissance", "初中九上·文艺复兴运动", 14, SUBJECT, None),
    (223015, "jhis_g9a_domain_new_route", "初中九上·探寻新航路", 15, SUBJECT, None),
    (223016, "jhis_g9a_domain_colonization", "初中九上·早期殖民掠夺", 16, SUBJECT, None),
    (223017, "jhis_g9a_domain_britain", "初中九上·君主立宪制的英国", 17, SUBJECT, None),
    (223018, "jhis_g9a_domain_america", "初中九上·美国的独立", 18, SUBJECT, None),
    (223019, "jhis_g9a_domain_france", "初中九上·法国大革命和拿破仑帝国", 19, SUBJECT, None),
    (223020, "jhis_g9a_domain_industry", "初中九上·第一次工业革命", 20, SUBJECT, None),
    (223021, "jhis_g9a_domain_marxism", "初中九上·马克思主义的诞生和国际共产主义运动的兴起", 21, SUBJECT, None),

    # 古代埃及
    (223022, "jhis_g9a_point_nile_civilization", "尼罗河与古埃及文明：尼罗河定期泛滥形成肥沃河谷，公元前3500年出现小国，公元前3100年初步统一", 1, SUBJECT, 223001),
    (223023, "jhis_g9a_point_pyramid", "金字塔：法老陵墓，胡夫金字塔规模最大，是古埃及文明的象征，体现王权至上和劳动人民智慧", 2, SUBJECT, 223001),
    (223024, "jhis_g9a_point_pharaoh_rule", "法老的统治：法老集军政大权于一身，被视为神，掌握全国土地和财富；象形文字、太阳历和木乃伊", 3, SUBJECT, 223001),

    # 古代两河流域
    (223025, "jhis_g9a_point_two_rivers", "两河流域文明：幼发拉底河与底格里斯河孕育苏美尔文明，约公元前3500年出现城市国家，楔形文字产生", 1, SUBJECT, 223002),
    (223026, "jhis_g9a_point_hammurabi_code", "《汉谟拉比法典》：公元前18世纪古巴比伦国王汉谟拉比颁布，是迄今已知世界上第一部较为完整的成文法典", 2, SUBJECT, 223002),
    (223027, "jhis_g9a_point_babylon_society", "古巴比伦社会等级：拥有公民权的自由民、无公民权的自由民和奴隶三个等级，法典维护奴隶主阶级利益", 3, SUBJECT, 223002),

    # 古代印度
    (223028, "jhis_g9a_point_indus_civilization", "印度河流域文明：哈拉帕等早期城市遗址，公元前1500年左右雅利安人进入印度，逐渐建立新的国家", 1, SUBJECT, 223003),
    (223029, "jhis_g9a_point_caste_system", "种姓制度：婆罗门、刹帝利、吠舍、首陀罗四个等级，贵贱分明、职业世袭、内部联姻，等级间不得通婚", 2, SUBJECT, 223003),
    (223030, "jhis_g9a_point_buddhism", "佛教创立：公元前6世纪乔达摩·悉达多创立，反对种姓制度，宣扬众生平等；公元前3世纪阿育王时期对外传播", 3, SUBJECT, 223003),

    # 希腊城邦和亚历山大帝国
    (223031, "jhis_g9a_point_polis", "希腊城邦：公元前8世纪出现，斯巴达崇尚武力、雅典民主政治发达，具有小国寡民和公民政治的特点", 1, SUBJECT, 223004),
    (223032, "jhis_g9a_point_athenian_democracy", "雅典民主政治：伯里克利时期达到高峰，公民大会是最高权力机构，抽签产生公职人员并发放津贴", 2, SUBJECT, 223004),
    (223033, "jhis_g9a_point_democracy_limit", "雅典民主的局限：成年男性公民才享有政治权利，妇女、外邦人和奴隶被排斥在外，本质是奴隶主阶级的民主", 3, SUBJECT, 223004),
    (223034, "jhis_g9a_point_alexander", "亚历山大帝国：公元前4世纪马其顿亚历山大东征，建立地跨欧亚非三洲的帝国，促进东西方文化交流", 4, SUBJECT, 223004),

    # 罗马城邦和罗马帝国
    (223035, "jhis_g9a_point_roman_republic", "罗马共和国：公元前509年建立，元老院掌握决策权，执政官主持日常政务，保民官维护平民利益", 1, SUBJECT, 223005),
    (223036, "jhis_g9a_point_twelve_tables", "《十二铜表法》：公元前450年左右颁布，罗马第一部成文法，使量刑定罪有法可依，限制贵族曲解法律", 2, SUBJECT, 223005),
    (223037, "jhis_g9a_point_punic_wars", "罗马扩张：公元前3世纪至前2世纪通过布匿战争击败迦太基，公元前2世纪成为地中海霸主", 3, SUBJECT, 223005),
    (223038, "jhis_g9a_point_roman_empire", "罗马帝国：公元前27年屋大维建立元首制，2世纪帝国地跨欧亚非三洲；395年分裂，476年西罗马帝国灭亡", 4, SUBJECT, 223005),

    # 希腊罗马古典文化
    (223039, "jhis_g9a_point_homeric_epics", "《荷马史诗》：包括《伊利亚特》和《奥德赛》，是古希腊最早的文学成就，希腊神话具有神人同形同性的特点", 1, SUBJECT, 223006),
    (223040, "jhis_g9a_point_greek_philosophy", "古希腊哲学：德谟克利特提出原子论，苏格拉底主张“认识你自己”，柏拉图与亚里士多德建立系统哲学体系", 2, SUBJECT, 223006),
    (223041, "jhis_g9a_point_roman_architecture", "罗马建筑：万神庙、大竞技场、凯旋门和引水道工程，体现罗马建筑的宏伟与实用", 3, SUBJECT, 223006),
    (223042, "jhis_g9a_point_roman_law_calendar", "罗马法与传统：从《十二铜表法》到万民法形成完整体系；凯撒时期制定儒略历，成为今天公历的基础", 4, SUBJECT, 223006),

    # 基督教的兴起和法兰克王国
    (223043, "jhis_g9a_point_christianity_origin", "基督教的兴起：1世纪产生于巴勒斯坦地区，耶稣是创始人；4世纪末罗马皇帝将基督教定为国教", 1, SUBJECT, 223007),
    (223044, "jhis_g9a_point_clovis", "法兰克王国：481年克洛维建立，皈依基督教并获得教会支持，通过土地分封和军事征服扩大疆域", 2, SUBJECT, 223007),
    (223045, "jhis_g9a_point_feudalism", "封君封臣制度：8世纪查理·马特改革后形成，以土地封赐为纽带，封臣效忠服兵役，封君提供保护", 3, SUBJECT, 223007),
    (223046, "jhis_g9a_point_charlemagne", "查理曼帝国：800年查理被教皇加冕为“罗马人的皇帝”，843年帝国一分为三，形成德意志、法兰西、意大利雏形", 4, SUBJECT, 223007),

    # 西欧庄园
    (223047, "jhis_g9a_point_manor_land", "庄园的土地：9世纪开始流行，11世纪遍布西欧；土地分为领主自营地和佃户份地，佃户须为领主服劳役", 1, SUBJECT, 223008),
    (223048, "jhis_g9a_point_manor_court", "庄园法庭：维护领主利益，审理佃户之间的纠纷，主持庄园公共事务，拥有有限的司法审判权", 2, SUBJECT, 223008),
    (223049, "jhis_g9a_point_manor_economy", "庄园经济：自给自足的自然经济单位，生产满足领主和佃户基本生活需要，很少与市场发生联系", 3, SUBJECT, 223008),

    # 中世纪城市和大学的兴起
    (223050, "jhis_g9a_point_city_revival", "西欧城市的兴起：10世纪起手工业和商业发展，意大利、法兰西、英格兰等地出现自由和自治的城市", 1, SUBJECT, 223009),
    (223051, "jhis_g9a_point_guilds", "城市居民与行会：手工业者组成行会保护行业利益，市民阶层形成，富裕商人和银行家成为早期资产阶级", 2, SUBJECT, 223009),
    (223052, "jhis_g9a_point_university", "大学的兴起：12世纪西欧大学兴起，巴黎大学、牛津大学等享有免赋税、司法特权和教育自主权", 3, SUBJECT, 223009),

    # 拜占庭帝国和《查士丁尼法典》
    (223053, "jhis_g9a_point_byzantine_empire", "拜占庭帝国：395年罗马帝国分裂后的东罗马帝国，都城君士坦丁堡，7世纪起受到外族入侵", 1, SUBJECT, 223010),
    (223054, "jhis_g9a_point_justinian_code", "《查士丁尼法典》：529年编成，与《法学汇纂》《法理概要》《新法典》合称《罗马民法大全》，奠定欧洲民法基础", 2, SUBJECT, 223010),
    (223055, "jhis_g9a_point_byzantium_fall", "拜占庭帝国的灭亡：1453年奥斯曼土耳其攻破君士坦丁堡，拜占庭帝国灭亡，其文化影响东西方", 3, SUBJECT, 223010),

    # 古代日本
    (223056, "jhis_g9a_point_yamato", "6世纪前的日本：5世纪初大和政权基本统一日本，实行部民制，最高统治者称天皇", 1, SUBJECT, 223011),
    (223057, "jhis_g9a_point_taika_reform", "大化改新：646年孝德天皇推行，政治上建立中央集权，经济上实行班田收授法和租庸调，日本发展为中央集权封建国家", 2, SUBJECT, 223011),
    (223058, "jhis_g9a_point_shogunate", "幕府统治：12世纪末源赖朝建立镰仓幕府，武士集团掌握国家大权，天皇成为名义上的最高统治者", 3, SUBJECT, 223011),

    # 阿拉伯帝国
    (223059, "jhis_g9a_point_islam", "伊斯兰教的创立：7世纪初穆罕默德在麦加创立，622年迁往麦地那建立穆斯林公社", 1, SUBJECT, 223012),
    (223060, "jhis_g9a_point_arab_empire", "阿拉伯帝国：8世纪中期形成地跨欧亚非三洲的大帝国，哈里发掌握政治、军事和宗教大权", 2, SUBJECT, 223012),
    (223061, "jhis_g9a_point_arab_culture", "阿拉伯文化：翻译保存大量古希腊典籍，《医典》《天方夜谭》影响深远，阿拉伯数字传入欧洲", 3, SUBJECT, 223012),

    # 西欧经济和社会的发展
    (223062, "jhis_g9a_point_rent_farm", "租地农场：11世纪后垦殖运动发展，14世纪中叶农村出现租地农场，雇佣工人经营，产品面向市场", 1, SUBJECT, 223013),
    (223063, "jhis_g9a_point_manual_workshop", "手工工场：从分散的手工生产走向集中的手工工场，工人与雇主形成雇佣关系，资本主义萌芽产生", 2, SUBJECT, 223013),
    (223064, "jhis_g9a_point_new_classes", "富裕农民和市民阶层：农村富裕农民、骑士经营租地农场，城市市民阶层发展壮大，成为早期资产阶级", 3, SUBJECT, 223013),

    # 文艺复兴运动
    (223065, "jhis_g9a_point_renaissance_origin", "文艺复兴的兴起：14世纪兴起于意大利，借助复兴古希腊罗马文化宣传人文主义，反对神权束缚", 1, SUBJECT, 223014),
    (223066, "jhis_g9a_point_dante", "但丁与《神曲》：但丁是文艺复兴的先驱，《神曲》分《地狱》《炼狱》《天堂》三部分，抨击教会的贪婪腐化", 2, SUBJECT, 223014),
    (223067, "jhis_g9a_point_da_vinci", "达·芬奇：意大利文艺复兴代表，代表作《蒙娜丽莎》《最后的晚餐》，体现人物个性与人文精神", 3, SUBJECT, 223014),
    (223068, "jhis_g9a_point_shakespeare", "莎士比亚：英国文艺复兴时期戏剧家，代表作《罗密欧与朱丽叶》《哈姆雷特》，反映人文主义思想", 4, SUBJECT, 223014),
    (223069, "jhis_g9a_point_renaissance_meaning", "文艺复兴的影响：一场思想解放运动，冲破神学束缚，为欧洲资本主义的产生和发展奠定思想文化基础", 5, SUBJECT, 223014),

    # 探寻新航路
    (223070, "jhis_g9a_point_route_causes", "新航路开辟的原因：欧洲商品经济发展和资本主义萌芽，追求财富，传播宗教；地圆说、指南针和造船技术进步", 1, SUBJECT, 223015),
    (223071, "jhis_g9a_point_dias_dagama", "迪亚士与达·伽马：1488年迪亚士到达非洲好望角，1498年达·伽马绕过好望角到达印度", 2, SUBJECT, 223015),
    (223072, "jhis_g9a_point_columbus", "哥伦布：1492年在西班牙王室支持下横渡大西洋，到达美洲，开辟了通往美洲的新航路", 3, SUBJECT, 223015),
    (223073, "jhis_g9a_point_magellan", "麦哲伦船队：1519—1522年完成人类首次环球航行，证明地圆学说，新航路开辟完成", 4, SUBJECT, 223015),
    (223074, "jhis_g9a_point_route_impact", "新航路开辟的影响：世界开始连为一个整体，促进欧洲资本主义发展，同时开启殖民掠夺和奴隶贸易", 5, SUBJECT, 223015),

    # 早期殖民掠夺
    (223075, "jhis_g9a_point_iberian_colony", "葡萄牙与西班牙的殖民扩张：16世纪葡萄牙在亚洲、非洲建立据点，西班牙在美洲建立广阔殖民地", 1, SUBJECT, 223016),
    (223076, "jhis_g9a_point_triangular_trade", "三角贸易：欧洲殖民者从欧洲运工业品到非洲换取黑奴，再把黑奴运往美洲，返程运回金银和原料", 2, SUBJECT, 223016),
    (223077, "jhis_g9a_point_british_colony", "英国殖民扩张：17世纪下半叶起打败荷兰和法国，18世纪下半叶成为最大的殖民国家，号称“日不落帝国”", 3, SUBJECT, 223016),
    (223078, "jhis_g9a_point_colony_impact", "殖民掠夺的影响：客观上有助于欧洲资本原始积累，给亚非拉人民带来深重灾难，造成当地长期落后", 4, SUBJECT, 223016),

    # 君主立宪制的英国
    (223079, "jhis_g9a_point_britain_causes", "英国资产阶级革命原因：斯图亚特王朝推行专制统治，议会传统深厚，资本主义发展与专制王权矛盾激化", 1, SUBJECT, 223017),
    (223080, "jhis_g9a_point_britain_process", "革命进程：1640年议会重新召开，1649年处死查理一世，1688年“光荣革命”推翻詹姆士二世统治", 2, SUBJECT, 223017),
    (223081, "jhis_g9a_point_bill_of_rights", "《权利法案》：1689年议会通过，限制国王权力，确立议会至上原则，英国君主立宪制逐步确立", 3, SUBJECT, 223017),

    # 美国的独立
    (223082, "jhis_g9a_point_lexington", "独立战争爆发：1775年来克星顿枪声打响，华盛顿任大陆军总司令，第二届大陆会议决定组建军队", 1, SUBJECT, 223018),
    (223083, "jhis_g9a_point_declaration", "《独立宣言》：1776年7月4日颁布，宣告北美13个殖民地脱离英国独立，提出天赋人权和主权在民", 2, SUBJECT, 223018),
    (223084, "jhis_g9a_point_constitution_1787", "1787年宪法：确立联邦制和三权分立原则，是世界上第一部资产阶级成文宪法，但保留奴隶制", 3, SUBJECT, 223018),
    (223085, "jhis_g9a_point_independence_meaning", "独立战争的意义：摆脱英国殖民统治，实现民族独立，为美国资本主义发展开辟道路，推动欧洲革命", 4, SUBJECT, 223018),

    # 法国大革命和拿破仑帝国
    (223086, "jhis_g9a_point_france_causes", "法国大革命原因：封建专制统治阻碍资本主义发展，三级制度激化矛盾，启蒙思想提供理论准备", 1, SUBJECT, 223019),
    (223087, "jhis_g9a_point_bastille", "革命爆发：1789年7月14日巴黎人民攻占巴士底狱，制宪议会通过《人权宣言》，宣告自由平等和私有财产神圣不可侵犯", 2, SUBJECT, 223019),
    (223088, "jhis_g9a_point_republic_1792", "法兰西第一共和国：1792年建立，1793年处死路易十六，雅各宾派专政把革命推向高潮", 3, SUBJECT, 223019),
    (223089, "jhis_g9a_point_napoleon_code", "《拿破仑法典》：1804年颁布，体现自由平等和私有财产神圣不可侵犯，成为许多国家民法的参照", 4, SUBJECT, 223019),
    (223090, "jhis_g9a_point_napoleon_empire", "拿破仑帝国：1804年拿破仑称帝建立法兰西第一帝国，对外战争打击欧洲封建势力，1815年滑铁卢战败", 5, SUBJECT, 223019),

    # 第一次工业革命
    (223091, "jhis_g9a_point_industrial_start", "工业革命的兴起：18世纪60年代从英国棉纺织业开始，哈格里夫斯发明珍妮机，标志工业革命开始", 1, SUBJECT, 223020),
    (223092, "jhis_g9a_point_steam_engine", "蒸汽机的改进：瓦特改良蒸汽机并广泛应用于生产，人类进入“蒸汽时代”，为工厂提供强大动力", 2, SUBJECT, 223020),
    (223093, "jhis_g9a_point_factory_railway", "工厂制度与铁路：现代工厂制度确立，1825年斯蒂芬森设计的蒸汽机车试车成功，铁路时代到来", 3, SUBJECT, 223020),
    (223094, "jhis_g9a_point_industrial_impact", "工业革命的影响：生产力极大提高，社会面貌发生巨变，形成工业资产阶级和工业无产阶级，也带来环境污染", 4, SUBJECT, 223020),

    # 马克思主义的诞生和国际共产主义运动的兴起
    (223095, "jhis_g9a_point_manifesto", "《共产党宣言》：1848年马克思、恩格斯为共产主义者同盟起草，标志马克思主义诞生，国际共产主义运动兴起", 1, SUBJECT, 223021),
    (223096, "jhis_g9a_point_paris_commune", "巴黎公社：1871年巴黎人民起义建立，是无产阶级建立政权的第一次伟大尝试，丰富马克思主义学说", 2, SUBJECT, 223021),
    (223097, "jhis_g9a_point_internationale", "《国际歌》：欧仁·鲍狄埃作词、皮埃尔·狄盖特作曲，号召全世界无产者联合起来，成为国际无产阶级的战歌", 3, SUBJECT, 223021),
)

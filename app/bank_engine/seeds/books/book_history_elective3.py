"""统编版（2019）高中历史选择性必修第三册（文化交流与传播）：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 8
G10 = 10
BOOK_ID = 8105

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中历史选择性必修第三册（文化交流与传播）",
    "hist_e3",
    5,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (850101, "第一单元 源远流长的中华文化", "hist_e3_u01", 1, BOOK_ID, None),
    (850102, "第二单元 丰富多样的世界文化", "hist_e3_u02", 2, BOOK_ID, None),
    (850103, "第三单元 人口迁徙、文化交融与认同", "hist_e3_u03", 3, BOOK_ID, None),
    (850104, "第四单元 商路、贸易与文化交流", "hist_e3_u04", 4, BOOK_ID, None),
    (850105, "第五单元 战争与文化交锋", "hist_e3_u05", 5, BOOK_ID, None),
    (850106, "第六单元 文化的传承与保护", "hist_e3_u06", 6, BOOK_ID, None),
    (850111, "第1课 中华优秀传统文化的内涵与特点", "hist_e3_l01", 1, BOOK_ID, 850101),
    (850112, "第2课 中华文化的世界意义", "hist_e3_l02", 2, BOOK_ID, 850101),
    (850113, "第3课 古代西亚、非洲文化", "hist_e3_l03", 1, BOOK_ID, 850102),
    (850114, "第4课 欧洲文化的形成", "hist_e3_l04", 2, BOOK_ID, 850102),
    (850115, "第5课 南亚、东亚与美洲的文化", "hist_e3_l05", 3, BOOK_ID, 850102),
    (850116, "第6课 古代人类的迁徙和区域文化的形成", "hist_e3_l06", 1, BOOK_ID, 850103),
    (850117, "第7课 近代殖民活动和人口的跨地域转移", "hist_e3_l07", 2, BOOK_ID, 850103),
    (850118, "第8课 现代社会的移民和多元文化", "hist_e3_l08", 3, BOOK_ID, 850103),
    (850119, "第9课 古代的商路、贸易与文化交流", "hist_e3_l09", 1, BOOK_ID, 850104),
    (850120, "第10课 近代以来的世界贸易与文化交流的扩展", "hist_e3_l10", 2, BOOK_ID, 850104),
    (850121, "第11课 古代战争与地域文化的演变", "hist_e3_l11", 1, BOOK_ID, 850105),
    (850122, "第12课 近代战争与西方文化的扩张", "hist_e3_l12", 2, BOOK_ID, 850105),
    (850123, "第13课 现代战争与不同文化的碰撞和交流", "hist_e3_l13", 3, BOOK_ID, 850105),
    (850124, "第14课 文化传承的多种载体及其发展", "hist_e3_l14", 1, BOOK_ID, 850106),
    (850125, "第15课 文化遗产：全人类共同的财富", "hist_e3_l15", 2, BOOK_ID, 850106),
)

# id / code / name / sort_order / subject_id / parent_id
# 85 00 xx 为册域、单元域与课域结构层，85 02 xx 为考点层，避开章节 85 01 xx 段。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (850001, "hist_e3_domain_chinese", "文脉绵延：中华文化的内涵与世界意义", 1, SUBJECT, None),
    (850002, "hist_e3_domain_world", "多元共生：世界区域文化的形成", 2, SUBJECT, None),
    (850003, "hist_e3_domain_migration", "迁徙往来：人口流动与文化认同", 3, SUBJECT, None),
    (850004, "hist_e3_domain_trade", "商路联通：贸易往来与文化交流", 4, SUBJECT, None),
    (850005, "hist_e3_domain_war", "战火淬炼：战争冲突与文化交锋", 5, SUBJECT, None),
    (850006, "hist_e3_domain_heritage", "薪火相传：文化传承与遗产保护", 6, SUBJECT, None),

    # 单元域层
    (850007, "hist_e3_unit01", "第一单元 源远流长的中华文化", 1, SUBJECT, 850001),
    (850008, "hist_e3_unit02", "第二单元 丰富多样的世界文化", 1, SUBJECT, 850002),
    (850009, "hist_e3_unit03", "第三单元 人口迁徙、文化交融与认同", 1, SUBJECT, 850003),
    (850010, "hist_e3_unit04", "第四单元 商路、贸易与文化交流", 1, SUBJECT, 850004),
    (850011, "hist_e3_unit05", "第五单元 战争与文化交锋", 1, SUBJECT, 850005),
    (850012, "hist_e3_unit06", "第六单元 文化的传承与保护", 1, SUBJECT, 850006),

    # 课域层
    (850013, "hist_e3_lesson01", "第1课 中华优秀传统文化的内涵与特点", 1, SUBJECT, 850007),
    (850014, "hist_e3_lesson02", "第2课 中华文化的世界意义", 2, SUBJECT, 850007),
    (850015, "hist_e3_lesson03", "第3课 古代西亚、非洲文化", 1, SUBJECT, 850008),
    (850016, "hist_e3_lesson04", "第4课 欧洲文化的形成", 2, SUBJECT, 850008),
    (850017, "hist_e3_lesson05", "第5课 南亚、东亚与美洲的文化", 3, SUBJECT, 850008),
    (850018, "hist_e3_lesson06", "第6课 古代人类的迁徙和区域文化的形成", 1, SUBJECT, 850009),
    (850019, "hist_e3_lesson07", "第7课 近代殖民活动和人口的跨地域转移", 2, SUBJECT, 850009),
    (850020, "hist_e3_lesson08", "第8课 现代社会的移民和多元文化", 3, SUBJECT, 850009),
    (850021, "hist_e3_lesson09", "第9课 古代的商路、贸易与文化交流", 1, SUBJECT, 850010),
    (850022, "hist_e3_lesson10", "第10课 近代以来的世界贸易与文化交流的扩展", 2, SUBJECT, 850010),
    (850023, "hist_e3_lesson11", "第11课 古代战争与地域文化的演变", 1, SUBJECT, 850011),
    (850024, "hist_e3_lesson12", "第12课 近代战争与西方文化的扩张", 2, SUBJECT, 850011),
    (850025, "hist_e3_lesson13", "第13课 现代战争与不同文化的碰撞和交流", 3, SUBJECT, 850011),
    (850026, "hist_e3_lesson14", "第14课 文化传承的多种载体及其发展", 1, SUBJECT, 850012),
    (850027, "hist_e3_lesson15", "第15课 文化遗产：全人类共同的财富", 2, SUBJECT, 850012),

    # 第一单元考点
    (850201, "hist_e3_point_origin", "中华文化起源：黄河、长江、辽河与珠江流域多元区域文化交汇", 1, SUBJECT, 850013),
    (850202, "hist_e3_point_hundred_schools", "先秦诸子百家：儒道墨法争鸣与中华思想体系的奠基", 2, SUBJECT, 850013),
    (850203, "hist_e3_point_confucian", "儒家思想：仁与礼、民本德治、修齐治平与教育伦理", 3, SUBJECT, 850013),
    (850204, "hist_e3_point_taoist", "道家思想：道法自然、无为而治与朴素辩证法", 4, SUBJECT, 850013),
    (850205, "hist_e3_point_legalist_mohist", "法家集权法治与墨家兼爱非攻：治理主张与社会理想", 5, SUBJECT, 850013),
    (850206, "hist_e3_point_features", "中华文化特点：连续性、包容性、统一性、创新性与和平性", 6, SUBJECT, 850013),
    (850207, "hist_e3_point_script", "汉字演变：甲骨文、金文、小篆、隶楷与汉字文化纽带", 1, SUBJECT, 850014),
    (850208, "hist_e3_point_confucian_sphere", "儒学东传：汉字文化圈与朝鲜、日本、越南的礼制教育", 2, SUBJECT, 850014),
    (850209, "hist_e3_point_buddhism", "佛教东传与本土化：汉传佛教、禅宗与中国思想融合", 3, SUBJECT, 850014),
    (850210, "hist_e3_point_four_inventions", "四大发明外传：造纸、印刷、火药、指南针与欧洲社会转型", 4, SUBJECT, 850014),
    (850211, "hist_e3_point_west_learning", "西学东渐：明末清初传教士、近代译书与新式学堂", 5, SUBJECT, 850014),
    (850212, "hist_e3_point_global_significance", "中华文化的世界意义：东方智慧、和平理念与文明互鉴", 6, SUBJECT, 850014),

    # 第二单元考点
    (850213, "hist_e3_point_mesopotamia_writing", "两河流域文明：楔形文字、泥板文书与《汉谟拉比法典》", 1, SUBJECT, 850015),
    (850214, "hist_e3_point_mesopotamia_culture", "古代西亚文学科技：《吉尔伽美什》、六十进制与天文历法", 2, SUBJECT, 850015),
    (850215, "hist_e3_point_egypt_writing", "古埃及文字：象形文字、纸莎草与罗塞塔石碑的破译", 3, SUBJECT, 850015),
    (850216, "hist_e3_point_egypt_culture", "古埃及文化：太阳神信仰、金字塔建筑与木乃伊医学", 4, SUBJECT, 850015),
    (850217, "hist_e3_point_africa_northeast", "东北非文明：努比亚库施王国与阿克苏姆王国的文字贸易", 5, SUBJECT, 850015),
    (850218, "hist_e3_point_africa_west_east", "西非与东非文化：加纳马里桑海帝国、斯瓦希里城邦与伊斯兰融合", 6, SUBJECT, 850015),
    (850219, "hist_e3_point_greek_philosophy", "古希腊哲学：苏格拉底、柏拉图、亚里士多德与人文理性精神", 1, SUBJECT, 850016),
    (850220, "hist_e3_point_greek_arts", "古希腊文艺史学：《荷马史诗》、戏剧、帕特农神庙与希罗多德", 2, SUBJECT, 850016),
    (850221, "hist_e3_point_roman_law", "古罗马文化：十二铜表法、万民法与共和帝国政治传统", 3, SUBJECT, 850016),
    (850222, "hist_e3_point_medieval_church", "中古西欧文化：基督教会、经院哲学与中世纪大学的兴起", 4, SUBJECT, 850016),
    (850223, "hist_e3_point_byzantine", "拜占庭文化：东正教、查士丁尼法典与圣索菲亚大教堂", 5, SUBJECT, 850016),
    (850224, "hist_e3_point_renaissance", "文艺复兴：人文主义、但丁彼特拉克、达·芬奇与莎士比亚", 6, SUBJECT, 850016),
    (850225, "hist_e3_point_india_caste", "古印度种姓制度：婆罗门、刹帝利、吠舍、首陀罗与婆罗门教", 1, SUBJECT, 850017),
    (850226, "hist_e3_point_india_buddhism", "佛教产生与传播：释迦牟尼、四谛与南传北传路径", 2, SUBJECT, 850017),
    (850227, "hist_e3_point_india_epic", "印度史诗与科学：《摩诃婆罗多》《罗摩衍那》、数字零与医学", 3, SUBJECT, 850017),
    (850228, "hist_e3_point_japan", "古代日本文化：大化改新、遣唐使、和歌与武士道", 4, SUBJECT, 850017),
    (850229, "hist_e3_point_korea", "古代朝鲜文化：汉字儒学、科举制度与谚文创制", 5, SUBJECT, 850017),
    (850230, "hist_e3_point_america", "美洲印第安文化：玛雅历法文字、阿兹特克与印加帝国", 6, SUBJECT, 850017),

    # 第三单元考点
    (850231, "hist_e3_point_indo_european", "印欧人迁徙：战车游牧、畜牧经济与语言文化扩散", 1, SUBJECT, 850018),
    (850232, "hist_e3_point_indo_european_regions", "印欧人迁徙影响：西亚赫梯、南亚雅利安与欧洲希腊罗马格局", 2, SUBJECT, 850018),
    (850233, "hist_e3_point_nomad_migration", "亚欧游牧民族大迁徙：匈奴西迁、日耳曼南下的连锁反应", 3, SUBJECT, 850018),
    (850234, "hist_e3_point_germanic", "日耳曼人迁徙：西罗马灭亡与西欧封建制度的形成", 4, SUBJECT, 850018),
    (850235, "hist_e3_point_arab_expansion", "阿拉伯人扩张：伊斯兰教传播与阿拉伯文化圈的形成", 5, SUBJECT, 850018),
    (850236, "hist_e3_point_migration_effect", "古代迁徙影响：族群融合、语言宗教传播与区域文化重塑", 6, SUBJECT, 850018),
    (850237, "hist_e3_point_columbian_exchange", "哥伦布交换：美洲人口锐减、物种流动与族群结构改变", 1, SUBJECT, 850019),
    (850238, "hist_e3_point_triangle_slave", "三角贸易：黑奴贸易、种植园经济与非洲人口流失", 2, SUBJECT, 850019),
    (850239, "hist_e3_point_chinese_labor", "华工出国：苦力贸易、修建铁路与东南亚美洲华人社会", 3, SUBJECT, 850019),
    (850240, "hist_e3_point_european_emigration", "欧洲移民：美洲、大洋洲开发与移民国家的形成", 4, SUBJECT, 850019),
    (850241, "hist_e3_point_indigenous_destruction", "殖民扩张后果：原住民文化破坏、语言宗教替代与人口灾难", 5, SUBJECT, 850019),
    (850242, "hist_e3_point_creole_culture", "文化交融：克里奥尔语、混血族群与美洲新文化形态", 6, SUBJECT, 850019),
    (850243, "hist_e3_point_postwar_labor", "二战后劳动力移民：西欧客籍工人、海湾劳务与全球化流动", 1, SUBJECT, 850020),
    (850244, "hist_e3_point_refugee", "难民问题：战争政治迫害、联合国难民署与国际人道援助", 2, SUBJECT, 850020),
    (850245, "hist_e3_point_american_mosaic", "美国移民社会：熔炉到马赛克、族群构成与多元文化主义", 3, SUBJECT, 850020),
    (850246, "hist_e3_point_europe_migration", "欧洲移民问题：穆斯林移民、文化冲突与融入政策争论", 4, SUBJECT, 850020),
    (850247, "hist_e3_point_identity", "移民与文化认同：双重认同、代际差异与母国文化延续", 5, SUBJECT, 850020),
    (850248, "hist_e3_point_singapore", "新加坡多元文化：族群和谐、组屋政策与共同价值观", 6, SUBJECT, 850020),

    # 第四单元考点
    (850249, "hist_e3_point_silk_road_open", "丝绸之路开通：张骞通西域、河西四郡与西域都护府", 1, SUBJECT, 850021),
    (850250, "hist_e3_point_silk_road_goods", "丝路物质交流：丝绸瓷器、葡萄苜蓿、良马与玻璃器", 2, SUBJECT, 850021),
    (850251, "hist_e3_point_silk_road_religion", "丝路宗教艺术：佛教东传、敦煌莫高窟与克孜尔石窟", 3, SUBJECT, 850021),
    (850252, "hist_e3_point_maritime_road", "海上丝绸之路：广州泉州明州、市舶司与瓷器香料贸易", 4, SUBJECT, 850021),
    (850253, "hist_e3_point_steppe_teahorse", "草原丝路与茶马古道：游牧农耕互补、皮毛马匹与茶叶交换", 5, SUBJECT, 850021),
    (850254, "hist_e3_point_road_culture", "商路的文化功能：技术信仰艺术传播与沿线城市文明繁荣", 6, SUBJECT, 850021),
    (850255, "hist_e3_point_age_of_discovery", "新航路开辟：全球航线、商业革命与世界市场雏形", 1, SUBJECT, 850022),
    (850256, "hist_e3_point_commodity_culture", "商品文化传播：茶咖啡可可、瓷器丝绸与消费风尚", 2, SUBJECT, 850022),
    (850257, "hist_e3_point_missionary", "传教士与文化交流：西学东渐、东学西传与科学知识移植", 3, SUBJECT, 850022),
    (850258, "hist_e3_point_industrial_transport", "工业革命与交通通讯：铁路轮船电报与全球文化联系", 4, SUBJECT, 850022),
    (850259, "hist_e3_point_global_culture", "20世纪全球化：电影广播互联网与大众文化产业", 5, SUBJECT, 850022),
    (850260, "hist_e3_point_diversity", "文化多样性：保护本土文化、反对文化霸权与文明交流互鉴", 6, SUBJECT, 850022),

    # 第五单元考点
    (850261, "hist_e3_point_alexander", "亚历山大东征：希腊化时代、亚历山大里亚与东西文化融合", 1, SUBJECT, 850023),
    (850262, "hist_e3_point_rome_expansion", "罗马扩张：地中海统一、罗马法传播与行省文化整合", 2, SUBJECT, 850023),
    (850263, "hist_e3_point_mongol", "蒙古西征：欧亚通道打通、驿站体系与技术文化传播", 3, SUBJECT, 850023),
    (850264, "hist_e3_point_war_fusion", "战争与文化融合：征服者与被征服者的制度宗教艺术互渗", 4, SUBJECT, 850023),
    (850265, "hist_e3_point_war_destruction", "战争的文化破坏：城市焚毁、典籍散佚与人口文化断层", 5, SUBJECT, 850023),
    (850266, "hist_e3_point_ancient_war_eval", "古代战争评价：破坏性与客观文化交流作用的辩证认识", 6, SUBJECT, 850023),
    (850267, "hist_e3_point_napoleon", "拿破仑战争：启蒙思想传播、法典输出与民族意识觉醒", 1, SUBJECT, 850024),
    (850268, "hist_e3_point_colonial_war", "殖民战争：西方制度宗教语言在亚非拉的强制扩张", 2, SUBJECT, 850024),
    (850269, "hist_e3_point_american_revolution", "美国独立战争：天赋人权、三权分立与共和政治文化", 3, SUBJECT, 850024),
    (850270, "hist_e3_point_latin_america", "拉美独立运动：玻利瓦尔圣马丁、民族认同与考迪罗政治", 4, SUBJECT, 850024),
    (850271, "hist_e3_point_nationalism", "近代战争与民族主义：民族国家建构、民族优越论与扩张", 5, SUBJECT, 850024),
    (850272, "hist_e3_point_western_expansion", "西方文化扩张双重性：现代文明传播与殖民文化霸权", 6, SUBJECT, 850024),
    (850273, "hist_e3_point_ww1", "第一次世界大战：民族自决思潮、殖民体系松动与文化反思", 1, SUBJECT, 850025),
    (850274, "hist_e3_point_ww2", "第二次世界大战：反法西斯文化、联合国与《世界人权宣言》", 2, SUBJECT, 850025),
    (850275, "hist_e3_point_cold_war", "冷战文化竞争：意识形态宣传、科技竞赛与不结盟运动", 3, SUBJECT, 850025),
    (850276, "hist_e3_point_decolonization_culture", "战后民族解放：文化复兴、本土语言教育与去殖民化", 4, SUBJECT, 850025),
    (850277, "hist_e3_point_war_technology", "现代战争与科技：核技术、信息技术与战后民用转化", 5, SUBJECT, 850025),
    (850278, "hist_e3_point_war_reflection", "战争与文化反思：和平主义、记忆政治与人类共同价值", 6, SUBJECT, 850025),

    # 第六单元考点
    (850279, "hist_e3_point_school", "学校教育：太学国子监、书院讲学与近代大学制度", 1, SUBJECT, 850026),
    (850280, "hist_e3_point_library_museum", "图书馆与博物馆：藏书传承、公共文化服务与文物收藏展示", 2, SUBJECT, 850026),
    (850281, "hist_e3_point_print_media", "印刷与传媒：雕版活字、报刊出版与大众文化传播", 3, SUBJECT, 850026),
    (850282, "hist_e3_point_digital", "数字技术传承：古籍数字化、虚拟博物馆与在线教育", 4, SUBJECT, 850026),
    (850283, "hist_e3_point_oral_intangible", "口头传统与非遗：史诗说唱、传统技艺与活态传承", 5, SUBJECT, 850026),
    (850284, "hist_e3_point_carrier_evolution", "传承载体演变：从口传到文字、印刷再到数字媒介", 6, SUBJECT, 850026),
    (850285, "hist_e3_point_concept", "文化遗产概念：物质与非物质、文化景观与自然遗产分类", 1, SUBJECT, 850027),
    (850286, "hist_e3_point_convention", "世界遗产公约：1972年公约、世界遗产委员会与申遗机制", 2, SUBJECT, 850027),
    (850287, "hist_e3_point_china_heritage", "中国世界遗产：长城故宫莫高窟、泰山黄山与保护实践", 3, SUBJECT, 850027),
    (850288, "hist_e3_point_intangible_protection", "非物质文化遗产保护：名录制度、传承人认定与生产性保护", 4, SUBJECT, 850027),
    (850289, "hist_e3_point_threats", "文化遗产威胁：战争盗掘、过度开发、城市化与气候变化", 5, SUBJECT, 850027),
    (850290, "hist_e3_point_cooperation", "遗产保护意义：文化认同、国际合作与人类文明共同财富", 6, SUBJECT, 850027),
)

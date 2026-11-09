"""统编版世界历史九年级下册：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 8
G9 = 9
BOOK_ID = 1324

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版世界历史九年级下册",
    "jhis_g9b",
    24,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 殖民地人民的反抗与资本主义制度的扩展
    (132401, "第一单元 殖民地人民的反抗与资本主义制度的扩展", "jhis_g9b_u01", 1, BOOK_ID, None),
    (132411, "第1课 殖民地人民的反抗斗争", "jhis_g9b_l01", 1, BOOK_ID, 132401),
    (132412, "第2课 俄国的改革", "jhis_g9b_l02", 2, BOOK_ID, 132401),
    (132413, "第3课 美国内战", "jhis_g9b_l03", 3, BOOK_ID, 132401),
    (132414, "第4课 日本明治维新", "jhis_g9b_l04", 4, BOOK_ID, 132401),

    # 第二单元 第二次工业革命和近代科学文化
    (132402, "第二单元 第二次工业革命和近代科学文化", "jhis_g9b_u02", 2, BOOK_ID, None),
    (132421, "第5课 第二次工业革命", "jhis_g9b_l05", 1, BOOK_ID, 132402),
    (132422, "第6课 工业化国家的社会变化", "jhis_g9b_l06", 2, BOOK_ID, 132402),
    (132423, "第7课 近代科学与文化", "jhis_g9b_l07", 3, BOOK_ID, 132402),

    # 第三单元 第一次世界大战和战后初期的世界
    (132403, "第三单元 第一次世界大战和战后初期的世界", "jhis_g9b_u03", 3, BOOK_ID, None),
    (132431, "第8课 第一次世界大战", "jhis_g9b_l08", 1, BOOK_ID, 132403),
    (132432, "第9课 列宁与十月革命", "jhis_g9b_l09", 2, BOOK_ID, 132403),
    (132433, "第10课 《凡尔赛条约》和《九国公约》", "jhis_g9b_l10", 3, BOOK_ID, 132403),
    (132434, "第11课 苏联的社会主义建设", "jhis_g9b_l11", 4, BOOK_ID, 132403),
    (132435, "第12课 亚非拉民族民主运动的高涨", "jhis_g9b_l12", 5, BOOK_ID, 132403),

    # 第四单元 经济大危机和第二次世界大战
    (132404, "第四单元 经济大危机和第二次世界大战", "jhis_g9b_u04", 4, BOOK_ID, None),
    (132441, "第13课 罗斯福新政", "jhis_g9b_l13", 1, BOOK_ID, 132404),
    (132442, "第14课 法西斯国家的侵略扩张", "jhis_g9b_l14", 2, BOOK_ID, 132404),
    (132443, "第15课 第二次世界大战", "jhis_g9b_l15", 3, BOOK_ID, 132404),

    # 第五单元 二战后的世界变化
    (132405, "第五单元 二战后的世界变化", "jhis_g9b_u05", 5, BOOK_ID, None),
    (132451, "第16课 冷战", "jhis_g9b_l16", 1, BOOK_ID, 132405),
    (132452, "第17课 战后资本主义的新变化", "jhis_g9b_l17", 2, BOOK_ID, 132405),
    (132453, "第18课 社会主义的发展与挫折", "jhis_g9b_l18", 3, BOOK_ID, 132405),
    (132454, "第19课 亚非拉国家的新发展", "jhis_g9b_l19", 4, BOOK_ID, 132405),

    # 第六单元 走向和平发展的世界
    (132406, "第六单元 走向和平发展的世界", "jhis_g9b_u06", 6, BOOK_ID, None),
    (132461, "第20课 联合国与世界贸易组织", "jhis_g9b_l20", 1, BOOK_ID, 132406),
    (132462, "第21课 冷战后的世界格局", "jhis_g9b_l21", 2, BOOK_ID, 132406),
    (132463, "第22课 不断发展的现代社会", "jhis_g9b_l22", 3, BOOK_ID, 132406),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 224001-224022 为册域层，224023-224088 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (224001, "jhis_g9b_domain_latin_america", "初中九下·殖民地人民的反抗斗争", 1, SUBJECT, G9, None),
    (224002, "jhis_g9b_domain_russia_reform", "初中九下·俄国的改革", 2, SUBJECT, G9, None),
    (224003, "jhis_g9b_domain_american_civil_war", "初中九下·美国内战", 3, SUBJECT, G9, None),
    (224004, "jhis_g9b_domain_meiji", "初中九下·日本明治维新", 4, SUBJECT, G9, None),
    (224005, "jhis_g9b_domain_second_industrial", "初中九下·第二次工业革命", 5, SUBJECT, G9, None),
    (224006, "jhis_g9b_domain_industrial_society", "初中九下·工业化国家的社会变化", 6, SUBJECT, G9, None),
    (224007, "jhis_g9b_domain_science_culture", "初中九下·近代科学与文化", 7, SUBJECT, G9, None),
    (224008, "jhis_g9b_domain_ww1", "初中九下·第一次世界大战", 8, SUBJECT, G9, None),
    (224009, "jhis_g9b_domain_october_revolution", "初中九下·列宁与十月革命", 9, SUBJECT, G9, None),
    (224010, "jhis_g9b_domain_versailles_washington", "初中九下·《凡尔赛条约》和《九国公约》", 10, SUBJECT, G9, None),
    (224011, "jhis_g9b_domain_soviet_build", "初中九下·苏联的社会主义建设", 11, SUBJECT, G9, None),
    (224012, "jhis_g9b_domain_asia_africa_latin", "初中九下·亚非拉民族民主运动的高涨", 12, SUBJECT, G9, None),
    (224013, "jhis_g9b_domain_new_deal", "初中九下·罗斯福新政", 13, SUBJECT, G9, None),
    (224014, "jhis_g9b_domain_fascism", "初中九下·法西斯国家的侵略扩张", 14, SUBJECT, G9, None),
    (224015, "jhis_g9b_domain_ww2", "初中九下·第二次世界大战", 15, SUBJECT, G9, None),
    (224016, "jhis_g9b_domain_cold_war", "初中九下·冷战", 16, SUBJECT, G9, None),
    (224017, "jhis_g9b_domain_postwar_capitalism", "初中九下·战后资本主义的新变化", 17, SUBJECT, G9, None),
    (224018, "jhis_g9b_domain_socialism_setback", "初中九下·社会主义的发展与挫折", 18, SUBJECT, G9, None),
    (224019, "jhis_g9b_domain_postwar_asia_africa", "初中九下·亚非拉国家的新发展", 19, SUBJECT, G9, None),
    (224020, "jhis_g9b_domain_un_wto", "初中九下·联合国与世界贸易组织", 20, SUBJECT, G9, None),
    (224021, "jhis_g9b_domain_post_cold_war", "初中九下·冷战后的世界格局", 21, SUBJECT, G9, None),
    (224022, "jhis_g9b_domain_modern_society", "初中九下·不断发展的现代社会", 22, SUBJECT, G9, None),

    # 殖民地人民的反抗斗争
    (224023, "jhis_g9b_point_bolivar_san_martin", "玻利瓦尔与圣马丁：19世纪初领导西属拉美独立运动，玻利瓦尔解放委内瑞拉、哥伦比亚等地，被誉为“南美的解放者”", 1, SUBJECT, G9, 224001),
    (224024, "jhis_g9b_point_india_rebellion", "印度民族大起义：1857—1859年士兵、农民和手工业者反抗英国殖民统治，章西女王英勇抗敌，沉重打击英国殖民者", 2, SUBJECT, G9, 224001),
    (224025, "jhis_g9b_point_latin_independence_impact", "拉美独立运动的影响：19世纪20年代除巴西外拉美国家基本独立，奠定民族国家格局，但保留大地产制和考迪罗政治", 3, SUBJECT, G9, 224001),

    # 俄国的改革
    (224026, "jhis_g9b_point_peter_reform", "彼得一世改革：18世纪初学习西方，建立中央集权、扩军备战、发展工商业与教育，开启俄国近代化进程", 1, SUBJECT, G9, 224002),
    (224027, "jhis_g9b_point_1861_emancipation", "1861年农奴制改革：亚历山大二世颁布废除农奴制法令，农奴获得人身自由，可通过赎买获得份地", 2, SUBJECT, G9, 224002),
    (224028, "jhis_g9b_point_russia_reform_impact", "1861年改革的评价：俄国走上发展资本主义的道路，是俄国历史上的重要转折点，但保留大量封建残余", 3, SUBJECT, G9, 224002),

    # 美国内战
    (224029, "jhis_g9b_point_civil_war_cause", "美国内战的原因：南北两种经济制度矛盾激化，奴隶制存废成为焦点，1861年南方挑起战争", 1, SUBJECT, G9, 224003),
    (224030, "jhis_g9b_point_homestead_emancipation", "《宅地法》与《解放黑人奴隶宣言》：1862年林肯颁布，调动农民和黑人积极性，成为战争转折点", 2, SUBJECT, G9, 224003),
    (224031, "jhis_g9b_point_civil_war_meaning", "美国内战的意义：维护国家统一，废除奴隶制，为资本主义发展扫清障碍，奠定美国经济起飞基础", 3, SUBJECT, G9, 224003),

    # 日本明治维新
    (224032, "jhis_g9b_point_bakumatsu", "倒幕运动：19世纪中期美国等西方国家叩关，幕府统治危机加深，1868年倒幕派推翻幕府，明治政府成立", 1, SUBJECT, G9, 224004),
    (224033, "jhis_g9b_point_meiji_measures", "明治维新的措施：废藩置县加强中央集权，殖产兴业发展近代工业，文明开化学习西方，实行征兵制", 2, SUBJECT, G9, 224004),
    (224034, "jhis_g9b_point_meiji_impact", "明治维新的影响：日本迅速走上资本主义道路，成为亚洲强国，但保留大量封建残余，走上对外侵略扩张道路", 3, SUBJECT, G9, 224004),

    # 第二次工业革命
    (224035, "jhis_g9b_point_electric_age", "电力时代：19世纪六七十年代第二次工业革命兴起，发电机、电动机和电灯广泛应用，人类进入“电气时代”", 1, SUBJECT, G9, 224005),
    (224036, "jhis_g9b_point_combustion_engine", "内燃机与新交通工具：内燃机以石油为燃料，推动汽车和飞机问世，石油成为重要新能源", 2, SUBJECT, G9, 224005),
    (224037, "jhis_g9b_point_monopoly", "垄断组织：生产与资本集中产生垄断，卡特尔、辛迪加、托拉斯出现，主要资本主义国家进入垄断资本主义阶段", 3, SUBJECT, G9, 224005),

    # 工业化国家的社会变化
    (224038, "jhis_g9b_point_population_urbanization", "人口增长与城市化：工业革命推动人口迅速增长，农村人口涌入城市，城市化进程加快", 1, SUBJECT, G9, 224006),
    (224039, "jhis_g9b_point_social_structure", "社会结构变化：工业资产阶级和工业无产阶级队伍壮大，妇女走出家庭参加社会生产，地位提高", 2, SUBJECT, G9, 224006),
    (224040, "jhis_g9b_point_industrial_problems", "工业化带来的社会问题：贫富分化加剧，工人阶级生活困苦，环境污染和公共卫生问题日益严重", 3, SUBJECT, G9, 224006),

    # 近代科学与文化
    (224041, "jhis_g9b_point_newton", "牛顿与经典力学：1687年发表《自然哲学的数学原理》，提出万有引力定律和三大运动定律，建立经典力学体系", 1, SUBJECT, G9, 224007),
    (224042, "jhis_g9b_point_darwin", "达尔文与进化论：1859年发表《物种起源》，提出生物进化论，冲击神创论和物种不变论", 2, SUBJECT, G9, 224007),
    (224043, "jhis_g9b_point_literature_art", "近代文学艺术：巴尔扎克《人间喜剧》、托尔斯泰《战争与和平》、贝多芬《英雄交响曲》、梵高《向日葵》", 3, SUBJECT, G9, 224007),

    # 第一次世界大战
    (224044, "jhis_g9b_point_two_alliances", "两大军事集团：德国、奥匈帝国、意大利组成三国同盟，英国、法国、俄国组成三国协约，列强争夺霸权", 1, SUBJECT, G9, 224008),
    (224045, "jhis_g9b_point_sarajevo", "萨拉热窝事件与一战爆发：1914年奥匈帝国皇储遇刺，成为战争导火索，同年第一次世界大战全面爆发", 2, SUBJECT, G9, 224008),
    (224046, "jhis_g9b_point_verdun", "凡尔登战役与战争结束：1916年凡尔登战役被称为“凡尔登绞肉机”，1918年同盟国战败，一战结束", 3, SUBJECT, G9, 224008),

    # 列宁与十月革命
    (224047, "jhis_g9b_point_february_revolution", "俄国二月革命：1917年3月推翻沙皇专制统治，形成资产阶级临时政府和工兵代表苏维埃两个政权并存的局面", 1, SUBJECT, G9, 224009),
    (224048, "jhis_g9b_point_october_revolution", "十月革命：1917年11月列宁领导彼得格勒武装起义，推翻临时政府，建立世界上第一个无产阶级专政国家", 2, SUBJECT, G9, 224009),
    (224049, "jhis_g9b_point_soviet_power", "苏维埃政权的措施与意义：废除土地私有制，没收地主土地，退出第一次世界大战；开辟人类历史新纪元", 3, SUBJECT, G9, 224009),

    # 凡尔赛—华盛顿体系
    (224050, "jhis_g9b_point_paris_conference", "巴黎和会与《凡尔赛条约》：1919年战胜国召开巴黎和会，签订对德和约，重划德国疆界并限制其军备", 1, SUBJECT, G9, 224010),
    (224051, "jhis_g9b_point_washington_conference", "华盛顿会议与《九国公约》：1921—1922年召开，公约宣称尊重中国主权，实际使中国回到几个帝国主义国家共同支配的局面", 2, SUBJECT, G9, 224010),
    (224052, "jhis_g9b_point_versailles_system", "凡尔赛—华盛顿体系的实质：帝国主义重新瓜分世界的国际新秩序，暂时缓和列强矛盾，埋下新的冲突隐患", 3, SUBJECT, G9, 224010),

    # 苏联的社会主义建设
    (224053, "jhis_g9b_point_nep", "新经济政策：1921年列宁实施，以粮食税代替余粮收集制，允许多种经济成分并存，利用市场和商品货币关系发展经济", 1, SUBJECT, G9, 224011),
    (224054, "jhis_g9b_point_ussr_industry", "苏联成立与工业化：1922年苏联成立，实施两个五年计划，重点发展重工业，迅速实现国家工业化", 2, SUBJECT, G9, 224011),
    (224055, "jhis_g9b_point_stalin_model", "苏联模式：高度集中的计划经济体制和高度集权的政治体制，1936年宪法标志其形成，短期内成效显著但弊端深远", 3, SUBJECT, G9, 224011),

    # 亚非拉民族民主运动的高涨
    (224056, "jhis_g9b_point_gandhi", "印度非暴力不合作运动：甘地领导，以和平方式抵制英国殖民统治，打击殖民势力，增强印度民族自尊心", 1, SUBJECT, G9, 224012),
    (224057, "jhis_g9b_point_egypt_wafd", "埃及华夫脱运动：1918年后扎格鲁尔领导争取民族独立，1922年英国被迫有条件承认埃及独立", 2, SUBJECT, G9, 224012),
    (224058, "jhis_g9b_point_cardenas", "墨西哥卡德纳斯改革：20世纪30年代推行土地改革、石油国有化和发展教育，捍卫民族利益", 3, SUBJECT, G9, 224012),

    # 罗斯福新政
    (224059, "jhis_g9b_point_great_depression", "经济大危机：1929—1933年从美国爆发并波及世界，表现为生产下降、企业破产、失业激增、金融崩溃", 1, SUBJECT, G9, 224013),
    (224060, "jhis_g9b_point_new_deal_measures", "罗斯福新政的措施：整顿金融体系，调整工业生产（《国家工业复兴法》），调整农业政策，推行以工代赈", 2, SUBJECT, G9, 224013),
    (224061, "jhis_g9b_point_new_deal_impact", "罗斯福新政的实质与影响：国家干预经济，缓解经济危机，开创国家垄断资本主义，维护了美国资本主义制度", 3, SUBJECT, G9, 224013),

    # 法西斯国家的侵略扩张
    (224062, "jhis_g9b_point_italy_fascism", "意大利法西斯政权：1922年墨索里尼建立法西斯专政，对内独裁统治，对外侵略扩张", 1, SUBJECT, G9, 224014),
    (224063, "jhis_g9b_point_germany_nazi", "德国纳粹专政：1933年希特勒出任总理，建立法西斯专政，迫害犹太人，疯狂扩军备战", 2, SUBJECT, G9, 224014),
    (224064, "jhis_g9b_point_japan_militarism", "日本法西斯化：1936年军部法西斯专政建立，发动全面侵华战争，成为亚洲战争策源地", 3, SUBJECT, G9, 224014),

    # 第二次世界大战
    (224065, "jhis_g9b_point_ww2_outbreak", "二战爆发与扩大：1939年德国突袭波兰，英法对德宣战；1941年苏德战争和太平洋战争爆发，战争达到全球规模", 1, SUBJECT, G9, 224015),
    (224066, "jhis_g9b_point_anti_fascist_alliance", "世界反法西斯同盟：1942年26国签署《联合国家宣言》，标志同盟正式形成，为战胜法西斯奠定基础", 2, SUBJECT, G9, 224015),
    (224067, "jhis_g9b_point_stalingrad", "战争转折与胜利：斯大林格勒保卫战是转折点，1944年诺曼底登陆开辟第二战场，1945年德国、日本先后投降", 3, SUBJECT, G9, 224015),

    # 冷战
    (224068, "jhis_g9b_point_truman_doctrine", "冷战开始：1947年杜鲁门主义出台，标志着美苏冷战的开始，核心是遏制苏联和共产主义", 1, SUBJECT, G9, 224016),
    (224069, "jhis_g9b_point_marshall_nato", "马歇尔计划与北约华约：美国推行马歇尔计划援助西欧，1949年成立北约，1955年苏联等成立华约，两极格局形成", 2, SUBJECT, G9, 224016),
    (224070, "jhis_g9b_point_cold_war_end", "冷战的表现与结束：德国分裂、古巴导弹危机、越南战争等对抗；1991年苏联解体，冷战结束", 3, SUBJECT, G9, 224016),

    # 战后资本主义的新变化
    (224071, "jhis_g9b_point_european_union", "欧洲的联合：20世纪50年代西欧六国建立欧洲经济共同体，1967年成立欧洲共同体，推动欧洲一体化", 1, SUBJECT, G9, 224017),
    (224072, "jhis_g9b_point_us_japan", "美国与日本经济发展：美国战后经济繁荣并出现“新经济”，日本在美国扶持下迅速崛起为资本主义世界第二经济大国", 2, SUBJECT, G9, 224017),
    (224073, "jhis_g9b_point_welfare_state", "社会保障制度：战后主要资本主义国家建立福利国家制度，缓和阶级矛盾，但也带来财政负担", 3, SUBJECT, G9, 224017),

    # 社会主义的发展与挫折
    (224074, "jhis_g9b_point_socialist_camp", "社会主义阵营：二战后欧亚一系列国家走上社会主义道路，形成以苏联为首的社会主义阵营", 1, SUBJECT, G9, 224018),
    (224075, "jhis_g9b_point_soviet_reforms", "苏联的改革：赫鲁晓夫批判斯大林个人崇拜，勃列日涅夫改革集中于重工业，戈尔巴乔夫改革背离社会主义方向", 2, SUBJECT, G9, 224018),
    (224076, "jhis_g9b_point_eastern_europe", "东欧剧变与苏联解体：20世纪80年代末东欧各国社会制度剧变，1991年苏联解体，两极格局终结", 3, SUBJECT, G9, 224018),

    # 亚非拉国家的新发展
    (224077, "jhis_g9b_point_bandung", "万隆会议：1955年亚非国家在印度尼西亚万隆召开，提出和平共处十项原则，形成“万隆精神”", 1, SUBJECT, G9, 224019),
    (224078, "jhis_g9b_point_africa_independence", "非洲独立年：1960年17个非洲国家独立，1990年纳米比亚独立，标志帝国主义在非洲殖民体系最终崩溃", 2, SUBJECT, G9, 224019),
    (224079, "jhis_g9b_point_cuba_panama", "拉美捍卫主权斗争：1959年卡斯特罗领导古巴革命胜利，1999年巴拿马收回运河区全部主权", 3, SUBJECT, G9, 224019),

    # 联合国与世界贸易组织
    (224080, "jhis_g9b_point_united_nations", "联合国：1945年成立，宗旨是维护国际和平与安全，安理会是维护和平与安全的主要机构，中国是安理会常任理事国", 1, SUBJECT, G9, 224020),
    (224081, "jhis_g9b_point_wto", "世界贸易组织：1995年成立，与关贸总协定一脉相承，制定国际贸易规则，推动世界贸易自由化", 2, SUBJECT, G9, 224020),
    (224082, "jhis_g9b_point_globalization", "经济全球化：生产、贸易和资本跨国流动加强，跨国公司作用突出，既带来机遇也加剧发展不平衡", 3, SUBJECT, G9, 224020),

    # 冷战后的世界格局
    (224083, "jhis_g9b_point_hegemonism", "霸权主义与地区冲突：冷战后美国推行单边主义，插手地区事务，科索沃战争等局部冲突频发", 1, SUBJECT, G9, 224021),
    (224084, "jhis_g9b_point_multipolarity", "世界多极化趋势：欧盟、日本、中国、俄罗斯等力量中心崛起，多极化趋势加强，有利于世界和平", 2, SUBJECT, G9, 224021),
    (224085, "jhis_g9b_point_new_order", "建立国际新秩序：发展中国家呼吁建立公正合理的国际政治经济新秩序，中国倡导构建人类命运共同体", 3, SUBJECT, G9, 224021),

    # 不断发展的现代社会
    (224086, "jhis_g9b_point_information_age", "计算机网络与信息时代：20世纪90年代互联网商业化普及，人类进入信息时代，深刻改变生产生活方式", 1, SUBJECT, G9, 224022),
    (224087, "jhis_g9b_point_population_issue", "人口问题：世界人口快速增长，带来资源、就业和教育压力，人口老龄化成为发达国家面临的问题", 2, SUBJECT, G9, 224022),
    (224088, "jhis_g9b_point_ecology", "生态与环境污染：工业化导致环境污染和生态破坏，可持续发展理念兴起，各国加强环境治理合作", 3, SUBJECT, G9, 224022),
)

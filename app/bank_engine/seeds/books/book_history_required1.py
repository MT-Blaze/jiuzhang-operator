"""统编版（2019）高中历史必修中外历史纲要（上）：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 8
G10 = 10
BOOK_ID = 8101

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中历史必修中外历史纲要（上）",
    "hist_r1",
    8,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (810101, "第一单元 从中华文明起源到秦汉统一多民族封建国家的建立与巩固", "hist_r1_u01", 1, BOOK_ID, None),
    (810102, "第二单元 三国两晋南北朝的民族交融与隋唐统一多民族封建国家的发展", "hist_r1_u02", 2, BOOK_ID, None),
    (810103, "第三单元 辽宋夏金多民族政权的并立与元朝的统一", "hist_r1_u03", 3, BOOK_ID, None),
    (810104, "第四单元 明清中国版图的奠定与面临的挑战", "hist_r1_u04", 4, BOOK_ID, None),
    (810105, "第五单元 晚清时期的内忧外患与救亡图存", "hist_r1_u05", 5, BOOK_ID, None),
    (810106, "第六单元 辛亥革命与中华民国的建立", "hist_r1_u06", 6, BOOK_ID, None),
    (810107, "第七单元 中国共产党成立与新民主主义革命兴起", "hist_r1_u07", 7, BOOK_ID, None),
    (810108, "第八单元 中华民族的抗日战争和人民解放战争的胜利", "hist_r1_u08", 8, BOOK_ID, None),
    (810109, "第九单元 中华人民共和国成立和社会主义革命与建设", "hist_r1_u09", 9, BOOK_ID, None),
    (810110, "第十单元 改革开放与社会主义现代化建设新时期", "hist_r1_u10", 10, BOOK_ID, None),
    (810111, "第1课 中华文明的起源与早期国家", "hist_r1_l01", 1, BOOK_ID, 810101),
    (810112, "第2课 诸侯纷争与变法运动", "hist_r1_l02", 2, BOOK_ID, 810101),
    (810113, "第3课 秦统一多民族封建国家的建立", "hist_r1_l03", 3, BOOK_ID, 810101),
    (810114, "第4课 西汉与东汉——统一多民族封建国家的巩固", "hist_r1_l04", 4, BOOK_ID, 810101),
    (810115, "第5课 三国两晋南北朝的政权更迭与民族交融", "hist_r1_l05", 1, BOOK_ID, 810102),
    (810116, "第6课 从隋唐盛世到五代十国", "hist_r1_l06", 2, BOOK_ID, 810102),
    (810117, "第7课 隋唐制度的变化与创新", "hist_r1_l07", 3, BOOK_ID, 810102),
    (810118, "第8课 三国至隋唐的文化", "hist_r1_l08", 4, BOOK_ID, 810102),
    (810119, "第9课 两宋的政治和军事", "hist_r1_l09", 1, BOOK_ID, 810103),
    (810120, "第10课 辽夏金元的统治", "hist_r1_l10", 2, BOOK_ID, 810103),
    (810121, "第11课 辽宋夏金元的经济、社会与文化", "hist_r1_l11", 3, BOOK_ID, 810103),
    (810122, "第12课 从明朝建立到清军入关", "hist_r1_l12", 1, BOOK_ID, 810104),
    (810123, "第13课 清朝前中期的鼎盛与危机", "hist_r1_l13", 2, BOOK_ID, 810104),
    (810124, "第14课 明至清中叶的经济与文化", "hist_r1_l14", 3, BOOK_ID, 810104),
    (810125, "第15课 两次鸦片战争", "hist_r1_l15", 1, BOOK_ID, 810105),
    (810126, "第16课 国家出路的探索与列强侵略的加剧", "hist_r1_l16", 2, BOOK_ID, 810105),
    (810127, "第17课 挽救民族危亡的斗争", "hist_r1_l17", 3, BOOK_ID, 810105),
    (810128, "第18课 辛亥革命", "hist_r1_l18", 1, BOOK_ID, 810106),
    (810129, "第19课 北洋军阀统治时期的政治、经济与文化", "hist_r1_l19", 2, BOOK_ID, 810106),
    (810130, "第20课 五四运动与中国共产党的诞生", "hist_r1_l20", 1, BOOK_ID, 810107),
    (810131, "第21课 南京国民政府的统治和中国共产党开辟革命新道路", "hist_r1_l21", 2, BOOK_ID, 810107),
    (810132, "第22课 从局部抗战到全国抗战", "hist_r1_l22", 1, BOOK_ID, 810108),
    (810133, "第23课 全民族浴血奋战与抗日战争的胜利", "hist_r1_l23", 2, BOOK_ID, 810108),
    (810134, "第24课 人民解放战争", "hist_r1_l24", 3, BOOK_ID, 810108),
    (810135, "第25课 中华人民共和国成立和向社会主义的过渡", "hist_r1_l25", 1, BOOK_ID, 810109),
    (810136, "第26课 社会主义建设在探索中曲折发展", "hist_r1_l26", 2, BOOK_ID, 810109),
    (810137, "第27课 中国特色社会主义道路的开辟与发展", "hist_r1_l27", 1, BOOK_ID, 810110),
    (810138, "第28课 改革开放和社会主义现代化建设的巨大成就", "hist_r1_l28", 2, BOOK_ID, 810110),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (810001, "hist_r1_domain_pre_qin_han", "先秦秦汉：文明起源、诸侯争霸与大一统奠基", 1, SUBJECT, G10, None),
    (810002, "hist_r1_domain_wei_jin_sui_tang", "魏晋隋唐：民族交融与制度创新的盛世格局", 2, SUBJECT, G10, None),
    (810003, "hist_r1_domain_liao_song_yuan", "辽宋夏金元：多民族政权并立与经济文化高峰", 3, SUBJECT, G10, None),
    (810004, "hist_r1_domain_ming_qing", "明清：版图奠定、君主专制强化与社会转型挑战", 4, SUBJECT, G10, None),
    (810005, "hist_r1_domain_late_qing", "晚清：内忧外患与救亡图存的艰难探索", 5, SUBJECT, G10, None),
    (810006, "hist_r1_domain_republic", "民国初年：辛亥革命与北洋时期的政治文化", 6, SUBJECT, G10, None),
    (810007, "hist_r1_domain_cpc_revolution", "中共革命：五四觉醒与革命新道路的开辟", 7, SUBJECT, G10, None),
    (810008, "hist_r1_domain_resistance_liberation", "抗战解放：全民族抗战与人民解放战争的胜利", 8, SUBJECT, G10, None),
    (810009, "hist_r1_domain_new_china", "新中国：社会主义革命和建设的艰辛探索", 9, SUBJECT, G10, None),
    (810010, "hist_r1_domain_reform", "改革开放：中国特色社会主义道路的开辟与成就", 10, SUBJECT, G10, None),

    # 单元域层
    (810011, "hist_r1_unit01", "第一单元 从中华文明起源到秦汉统一多民族封建国家的建立与巩固", 1, SUBJECT, G10, 810001),
    (810012, "hist_r1_unit02", "第二单元 三国两晋南北朝的民族交融与隋唐统一多民族封建国家的发展", 1, SUBJECT, G10, 810002),
    (810013, "hist_r1_unit03", "第三单元 辽宋夏金多民族政权的并立与元朝的统一", 1, SUBJECT, G10, 810003),
    (810014, "hist_r1_unit04", "第四单元 明清中国版图的奠定与面临的挑战", 1, SUBJECT, G10, 810004),
    (810015, "hist_r1_unit05", "第五单元 晚清时期的内忧外患与救亡图存", 1, SUBJECT, G10, 810005),
    (810016, "hist_r1_unit06", "第六单元 辛亥革命与中华民国的建立", 1, SUBJECT, G10, 810006),
    (810017, "hist_r1_unit07", "第七单元 中国共产党成立与新民主主义革命兴起", 1, SUBJECT, G10, 810007),
    (810018, "hist_r1_unit08", "第八单元 中华民族的抗日战争和人民解放战争的胜利", 1, SUBJECT, G10, 810008),
    (810019, "hist_r1_unit09", "第九单元 中华人民共和国成立和社会主义革命与建设", 1, SUBJECT, G10, 810009),
    (810020, "hist_r1_unit10", "第十单元 改革开放与社会主义现代化建设新时期", 1, SUBJECT, G10, 810010),

    # 课域层
    (810021, "hist_r1_lesson01", "第1课 中华文明的起源与早期国家", 1, SUBJECT, G10, 810011),
    (810022, "hist_r1_lesson02", "第2课 诸侯纷争与变法运动", 2, SUBJECT, G10, 810011),
    (810023, "hist_r1_lesson03", "第3课 秦统一多民族封建国家的建立", 3, SUBJECT, G10, 810011),
    (810024, "hist_r1_lesson04", "第4课 西汉与东汉——统一多民族封建国家的巩固", 4, SUBJECT, G10, 810011),
    (810025, "hist_r1_lesson05", "第5课 三国两晋南北朝的政权更迭与民族交融", 1, SUBJECT, G10, 810012),
    (810026, "hist_r1_lesson06", "第6课 从隋唐盛世到五代十国", 2, SUBJECT, G10, 810012),
    (810027, "hist_r1_lesson07", "第7课 隋唐制度的变化与创新", 3, SUBJECT, G10, 810012),
    (810028, "hist_r1_lesson08", "第8课 三国至隋唐的文化", 4, SUBJECT, G10, 810012),
    (810029, "hist_r1_lesson09", "第9课 两宋的政治和军事", 1, SUBJECT, G10, 810013),
    (810030, "hist_r1_lesson10", "第10课 辽夏金元的统治", 2, SUBJECT, G10, 810013),
    (810031, "hist_r1_lesson11", "第11课 辽宋夏金元的经济、社会与文化", 3, SUBJECT, G10, 810013),
    (810032, "hist_r1_lesson12", "第12课 从明朝建立到清军入关", 1, SUBJECT, G10, 810014),
    (810033, "hist_r1_lesson13", "第13课 清朝前中期的鼎盛与危机", 2, SUBJECT, G10, 810014),
    (810034, "hist_r1_lesson14", "第14课 明至清中叶的经济与文化", 3, SUBJECT, G10, 810014),
    (810035, "hist_r1_lesson15", "第15课 两次鸦片战争", 1, SUBJECT, G10, 810015),
    (810036, "hist_r1_lesson16", "第16课 国家出路的探索与列强侵略的加剧", 2, SUBJECT, G10, 810015),
    (810037, "hist_r1_lesson17", "第17课 挽救民族危亡的斗争", 3, SUBJECT, G10, 810015),
    (810038, "hist_r1_lesson18", "第18课 辛亥革命", 1, SUBJECT, G10, 810016),
    (810039, "hist_r1_lesson19", "第19课 北洋军阀统治时期的政治、经济与文化", 2, SUBJECT, G10, 810016),
    (810040, "hist_r1_lesson20", "第20课 五四运动与中国共产党的诞生", 1, SUBJECT, G10, 810017),
    (810041, "hist_r1_lesson21", "第21课 南京国民政府的统治和中国共产党开辟革命新道路", 2, SUBJECT, G10, 810017),
    (810042, "hist_r1_lesson22", "第22课 从局部抗战到全国抗战", 1, SUBJECT, G10, 810018),
    (810043, "hist_r1_lesson23", "第23课 全民族浴血奋战与抗日战争的胜利", 2, SUBJECT, G10, 810018),
    (810044, "hist_r1_lesson24", "第24课 人民解放战争", 3, SUBJECT, G10, 810018),
    (810045, "hist_r1_lesson25", "第25课 中华人民共和国成立和向社会主义的过渡", 1, SUBJECT, G10, 810019),
    (810046, "hist_r1_lesson26", "第26课 社会主义建设在探索中曲折发展", 2, SUBJECT, G10, 810019),
    (810047, "hist_r1_lesson27", "第27课 中国特色社会主义道路的开辟与发展", 1, SUBJECT, G10, 810020),
    (810048, "hist_r1_lesson28", "第28课 改革开放和社会主义现代化建设的巨大成就", 2, SUBJECT, G10, 810020),

    # 第一单元考点
    (810049, "hist_r1_point_civilization_origin", "中华文明起源：多元一体的文化遗存与早期国家曙光", 1, SUBJECT, G10, 810021),
    (810050, "hist_r1_point_early_state", "夏商西周：王位世袭、内外服与分封宗法礼乐", 2, SUBJECT, G10, 810021),
    (810051, "hist_r1_point_spring_autumn_transition", "春秋战国争霸兼并：华夏认同与社会大转型", 1, SUBJECT, G10, 810022),
    (810052, "hist_r1_point_iron_plough_land", "铁犁牛耕推广、井田制瓦解与土地私有制确立", 2, SUBJECT, G10, 810022),
    (810053, "hist_r1_point_hundred_schools_reform", "百家争鸣与商鞅变法：思想解放与制度变革", 3, SUBJECT, G10, 810022),
    (810054, "hist_r1_point_qin_unification", "秦的统一：历史条件、统一过程与大一统意义", 1, SUBJECT, G10, 810023),
    (810055, "hist_r1_point_central_bureaucracy", "皇帝制度、三公九卿与郡县制：专制主义中央集权确立", 2, SUBJECT, G10, 810023),
    (810056, "hist_r1_point_qin_measures_fall", "秦朝巩固统一的措施、暴政与陈胜吴广起义", 3, SUBJECT, G10, 810023),
    (810057, "hist_r1_point_han_recovery", "汉初休养生息、文景之治与王国问题", 1, SUBJECT, G10, 810024),
    (810058, "hist_r1_point_han_wudi_unification", "汉武帝大一统：推恩令、盐铁官营、尊崇儒术与丝绸之路", 2, SUBJECT, G10, 810024),

    # 第二单元考点
    (810059, "hist_r1_point_three_kingdoms", "三国鼎立、西晋统一与东晋南朝门阀政治", 1, SUBJECT, G10, 810025),
    (810060, "hist_r1_point_northern_wei_reform", "北魏孝文帝改革与民族交融的历史影响", 2, SUBJECT, G10, 810025),
    (810061, "hist_r1_point_sui_unification", "隋朝统一、大运河开通与科举制创立", 1, SUBJECT, G10, 810026),
    (810062, "hist_r1_point_tang_prosperity", "贞观之治、开元盛世与唐朝开明的民族政策", 2, SUBJECT, G10, 810026),
    (810063, "hist_r1_point_three_departments", "三省六部制：决策、审议与执行的权力分工", 1, SUBJECT, G10, 810027),
    (810064, "hist_r1_point_tax_reform", "租庸调制到两税法：赋税标准由人丁转向资产", 2, SUBJECT, G10, 810027),
    (810065, "hist_r1_point_sui_tang_culture", "三教并存、唐诗书画与玄奘西行、鉴真东渡", 1, SUBJECT, G10, 810028),

    # 第三单元考点
    (810066, "hist_r1_point_song_centralization", "北宋加强中央集权：收精兵、削实权、制钱谷", 1, SUBJECT, G10, 810029),
    (810067, "hist_r1_point_wang_anshi_reform", "王安石变法与宋代“三冗”危机、庆历新政", 2, SUBJECT, G10, 810029),
    (810068, "hist_r1_point_liao_xi_xia_jin", "辽南北面官制、西夏制度与金朝猛安谋克制", 1, SUBJECT, G10, 810030),
    (810069, "hist_r1_point_yuan_province", "元朝行省制度与宣政院、澎湖巡检司的边疆治理", 2, SUBJECT, G10, 810030),
    (810070, "hist_r1_point_song_economy", "宋代商品经济繁荣、交子出现与经济重心南移", 1, SUBJECT, G10, 810031),
    (810071, "hist_r1_point_song_yuan_culture", "程朱理学、宋词元曲话本与辽宋夏金元科技", 2, SUBJECT, G10, 810031),

    # 第四单元考点
    (810072, "hist_r1_point_ming_abolish_chancellor", "明朝废丞相、设内阁与宦官专权", 1, SUBJECT, G10, 810032),
    (810073, "hist_r1_point_ming_frontier", "郑和下西洋、戚继光抗倭与明朝经略边疆", 2, SUBJECT, G10, 810032),
    (810074, "hist_r1_point_qing_autocracy", "清朝君主专制强化：军机处、密折制度与文字狱", 1, SUBJECT, G10, 810033),
    (810075, "hist_r1_point_qing_territory", "清朝前中期疆域奠定与统一多民族国家的巩固", 2, SUBJECT, G10, 810033),
    (810076, "hist_r1_point_ming_qing_economy", "明至清中叶商品经济、白银流通与小说戏曲繁荣", 1, SUBJECT, G10, 810034),

    # 第五单元考点
    (810077, "hist_r1_point_opium_war", "鸦片战争背景、《南京条约》与半殖民地化开端", 1, SUBJECT, G10, 810035),
    (810078, "hist_r1_point_second_opium_war", "第二次鸦片战争与列强侵略的加深", 2, SUBJECT, G10, 810035),
    (810079, "hist_r1_point_taiping_self_strengthening", "太平天国运动与洋务运动：农民抗争与自强求富", 1, SUBJECT, G10, 810036),
    (810080, "hist_r1_point_jiawu_crisis", "甲午中日战争、瓜分狂潮与民族危机加深", 2, SUBJECT, G10, 810036),
    (810081, "hist_r1_point_reform_boxer", "戊戌变法与义和团运动：维新探索与反帝斗争", 1, SUBJECT, G10, 810037),

    # 第六单元考点
    (810082, "hist_r1_point_revolution_1911", "武昌起义、中华民国成立与《中华民国临时约法》", 1, SUBJECT, G10, 810038),
    (810083, "hist_r1_point_revolution_significance", "辛亥革命的历史意义与局限性", 2, SUBJECT, G10, 810038),
    (810084, "hist_r1_point_beiyang_politics", "北洋军阀统治、军阀割据与府院之争", 1, SUBJECT, G10, 810039),
    (810085, "hist_r1_point_beiyang_culture", "北洋时期民族工业发展、新文化运动与移风易俗", 2, SUBJECT, G10, 810039),

    # 第七单元考点
    (810086, "hist_r1_point_new_culture_may_fourth", "新文化运动与五四运动：思想解放与爱国高潮", 1, SUBJECT, G10, 810040),
    (810087, "hist_r1_point_cpc_founding", "中国共产党的诞生与中共二大民主革命纲领", 2, SUBJECT, G10, 810040),
    (810088, "hist_r1_point_national_revolution", "国民大革命、国共合作与北伐战争", 1, SUBJECT, G10, 810041),
    (810089, "hist_r1_point_jinggangshan_path", "南京国民政府统治与中国共产党开辟井冈山革命新道路", 2, SUBJECT, G10, 810041),

    # 第八单元考点
    (810090, "hist_r1_point_local_resistance", "九一八事变、局部抗战与抗日民族统一战线形成", 1, SUBJECT, G10, 810042),
    (810091, "hist_r1_point_full_resistance", "全国抗战爆发：正面战场与敌后战场的抗战", 2, SUBJECT, G10, 810042),
    (810092, "hist_r1_point_war_victory", "抗日战争的胜利：全民族浴血奋战与历史意义", 1, SUBJECT, G10, 810043),
    (810093, "hist_r1_point_liberation_defense", "重庆谈判、战略防御与战略进攻", 1, SUBJECT, G10, 810044),
    (810094, "hist_r1_point_liberation_victory", "三大战役、渡江战役与解放战争的胜利", 2, SUBJECT, G10, 810044),

    # 第九单元考点
    (810095, "hist_r1_point_prc_founding", "中华人民共和国成立与人民政权的巩固", 1, SUBJECT, G10, 810045),
    (810096, "hist_r1_point_transition_socialism", "过渡时期总路线、一五计划与三大改造", 2, SUBJECT, G10, 810045),
    (810097, "hist_r1_point_exploration", "社会主义建设在探索中曲折发展：中共八大、大跃进与调整", 1, SUBJECT, G10, 810046),

    # 第十单元考点
    (810098, "hist_r1_point_third_plenum", "十一届三中全会与改革开放的伟大转折", 1, SUBJECT, G10, 810047),
    (810099, "hist_r1_point_reform_achievements", "改革开放进程、理论创新与社会主义现代化建设成就", 1, SUBJECT, G10, 810048),
)

"""统编版中国历史七年级下册：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 8
G7 = 7
BOOK_ID = 1320

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版中国历史七年级下册",
    "jhis_g7b",
    20,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 隋唐时期：繁荣与开放的时代
    (132001, "第一单元 隋唐时期：繁荣与开放的时代", "jhis_g7b_u01", 1, BOOK_ID, None),
    (132011, "第1课 隋朝的统一与灭亡", "jhis_g7b_l01", 1, BOOK_ID, 132001),
    (132012, "第2课 从“贞观之治”到“开元盛世”", "jhis_g7b_l02", 2, BOOK_ID, 132001),
    (132013, "第3课 盛唐气象", "jhis_g7b_l03", 3, BOOK_ID, 132001),
    (132014, "第4课 唐朝的中外文化交流", "jhis_g7b_l04", 4, BOOK_ID, 132001),
    (132015, "第5课 安史之乱与唐朝衰亡", "jhis_g7b_l05", 5, BOOK_ID, 132001),

    # 第二单元 辽宋夏金元时期：民族关系发展和社会变化
    (132002, "第二单元 辽宋夏金元时期：民族关系发展和社会变化", "jhis_g7b_u02", 2, BOOK_ID, None),
    (132021, "第6课 北宋的政治", "jhis_g7b_l06", 1, BOOK_ID, 132002),
    (132022, "第7课 辽、西夏与北宋的并立", "jhis_g7b_l07", 2, BOOK_ID, 132002),
    (132023, "第8课 金与南宋的对峙", "jhis_g7b_l08", 3, BOOK_ID, 132002),
    (132024, "第9课 宋代经济的发展", "jhis_g7b_l09", 4, BOOK_ID, 132002),
    (132025, "第10课 蒙古族的兴起与元朝的建立", "jhis_g7b_l10", 5, BOOK_ID, 132002),
    (132026, "第11课 元朝的统治", "jhis_g7b_l11", 6, BOOK_ID, 132002),
    (132027, "第12课 宋元时期的都市和文化", "jhis_g7b_l12", 7, BOOK_ID, 132002),
    (132028, "第13课 宋元时期的科技与中外交通", "jhis_g7b_l13", 8, BOOK_ID, 132002),

    # 第三单元 明清时期：统一多民族国家的巩固与发展
    (132003, "第三单元 明清时期：统一多民族国家的巩固与发展", "jhis_g7b_u03", 3, BOOK_ID, None),
    (132031, "第14课 明朝的统治", "jhis_g7b_l14", 1, BOOK_ID, 132003),
    (132032, "第15课 明朝的对外关系", "jhis_g7b_l15", 2, BOOK_ID, 132003),
    (132033, "第16课 明朝的科技、建筑与文学", "jhis_g7b_l16", 3, BOOK_ID, 132003),
    (132034, "第17课 明朝的灭亡", "jhis_g7b_l17", 4, BOOK_ID, 132003),
    (132035, "第18课 统一多民族国家的巩固和发展", "jhis_g7b_l18", 5, BOOK_ID, 132003),
    (132036, "第19课 清朝前期社会经济的发展", "jhis_g7b_l19", 6, BOOK_ID, 132003),
    (132037, "第20课 清朝君主专制的强化", "jhis_g7b_l20", 7, BOOK_ID, 132003),
    (132038, "第21课 清朝前期的文学艺术", "jhis_g7b_l21", 8, BOOK_ID, 132003),
)

# id / code / name / sort_order / subject_id / parent_id
# 220001-220021 为册域层，220022-220094 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (220001, "jhis_g7b_domain_sui", "初中七下·隋朝的统一与大运河", 1, SUBJECT, None),
    (220002, "jhis_g7b_domain_keju", "初中七下·科举制的创立与完善", 2, SUBJECT, None),
    (220003, "jhis_g7b_domain_zhenguan", "初中七下·贞观之治与开元盛世", 3, SUBJECT, None),
    (220004, "jhis_g7b_domain_tang_prosperity", "初中七下·盛唐气象与唐朝民族交往", 4, SUBJECT, None),
    (220005, "jhis_g7b_domain_tang_exchange", "初中七下·唐朝的中外文化交流", 5, SUBJECT, None),
    (220006, "jhis_g7b_domain_anlushan", "初中七下·安史之乱与唐朝衰亡", 6, SUBJECT, None),
    (220007, "jhis_g7b_domain_northern_song", "初中七下·北宋的政治与重文轻武", 7, SUBJECT, None),
    (220008, "jhis_g7b_domain_liao_xia_jin", "初中七下·辽宋夏金民族政权并立", 8, SUBJECT, None),
    (220009, "jhis_g7b_domain_song_economy", "初中七下·宋代经济与重心南移", 9, SUBJECT, None),
    (220010, "jhis_g7b_domain_mongol_yuan", "初中七下·蒙古兴起与元朝统一", 10, SUBJECT, None),
    (220011, "jhis_g7b_domain_yuan_rule", "初中七下·元朝的行省制度与边疆管理", 11, SUBJECT, None),
    (220012, "jhis_g7b_domain_song_yuan_culture", "初中七下·宋元都市文化与文学", 12, SUBJECT, None),
    (220013, "jhis_g7b_domain_song_yuan_tech", "初中七下·宋元科技与中外交通", 13, SUBJECT, None),
    (220014, "jhis_g7b_domain_ming_autocracy", "初中七下·明朝君主专制的强化", 14, SUBJECT, None),
    (220015, "jhis_g7b_domain_ming_foreign", "初中七下·明朝的对外关系", 15, SUBJECT, None),
    (220016, "jhis_g7b_domain_ming_culture", "初中七下·明朝的科技建筑与文学", 16, SUBJECT, None),
    (220017, "jhis_g7b_domain_ming_fall", "初中七下·明朝的灭亡与清军入关", 17, SUBJECT, None),
    (220018, "jhis_g7b_domain_qing_unify", "初中七下·清朝统一多民族国家的巩固", 18, SUBJECT, None),
    (220019, "jhis_g7b_domain_qing_economy", "初中七下·清朝前期社会经济与闭关锁国", 19, SUBJECT, None),
    (220020, "jhis_g7b_domain_qing_autocracy", "初中七下·清朝君主专制的顶峰", 20, SUBJECT, None),
    (220021, "jhis_g7b_domain_qing_arts", "初中七下·明清文学艺术与京剧", 21, SUBJECT, None),

    # 隋朝的统一与大运河
    (220022, "jhis_g7b_point_sui_founding", "隋朝建立与统一：581年杨坚定都长安，589年灭陈结束分裂", 1, SUBJECT, 220001),
    (220023, "jhis_g7b_point_grand_canal", "大运河：605年起开凿，以洛阳为中心，北抵涿郡、南至余杭，沟通五大水系", 2, SUBJECT, 220001),
    (220024, "jhis_g7b_point_sui_fall", "隋朝灭亡：隋炀帝暴政、三征辽东与农民起义，618年隋朝覆灭", 3, SUBJECT, 220001),

    # 科举制的创立与完善
    (220025, "jhis_g7b_point_keju_origin", "科举制创立：隋文帝分科考试选官，隋炀帝设进士科标志正式确立", 1, SUBJECT, 220002),
    (220026, "jhis_g7b_point_keju_tang", "唐朝完善科举：唐太宗扩充科目，武则天创立殿试，进士科最受重视", 2, SUBJECT, 220002),
    (220027, "jhis_g7b_point_keju_song", "宋朝科举发展：殿试成为定制，实行糊名、誊录，录取名额大幅增加", 3, SUBJECT, 220002),

    # 贞观之治与开元盛世
    (220028, "jhis_g7b_point_zhenguan", "贞观之治：唐太宗纳谏如流、任用房玄龄杜如晦、轻徭薄赋、完善三省六部制", 1, SUBJECT, 220003),
    (220029, "jhis_g7b_point_wu_zetian", "武则天：我国历史上唯一的女皇帝，改国号为周，创立殿试，史称“政启开元，治宏贞观”", 2, SUBJECT, 220003),
    (220030, "jhis_g7b_point_kaiyuan", "开元盛世：唐玄宗任用姚崇宋璟、整顿吏治、发展经济，唐朝进入鼎盛时期", 3, SUBJECT, 220003),
    (220031, "jhis_g7b_point_tang_farm_tools", "唐朝农业生产工具：曲辕犁与筒车，推动农业效率提高", 4, SUBJECT, 220003),

    # 盛唐气象与唐朝民族交往
    (220032, "jhis_g7b_point_tiankehan", "“天可汗”：唐太宗实行开明民族政策，被北方和西北各族首领尊奉", 1, SUBJECT, 220004),
    (220033, "jhis_g7b_point_wencheng", "文成公主入藏：641年嫁给松赞干布，唐蕃和亲促进吐蕃经济文化发展", 2, SUBJECT, 220004),
    (220034, "jhis_g7b_point_xiyu_protectorate", "安西都护府与北庭都护府：唐朝管理西域、保障丝绸之路畅通的军政机构", 3, SUBJECT, 220004),
    (220035, "jhis_g7b_point_tang_poetry", "唐诗：李白“诗仙”、杜甫“诗圣”、白居易，反映盛唐气象与社会现实", 4, SUBJECT, 220004),
    (220036, "jhis_g7b_point_tang_art", "唐朝书法绘画：颜真卿、柳公权与阎立本、吴道子，敦煌莫高窟艺术宝库", 5, SUBJECT, 220004),

    # 唐朝的中外文化交流
    (220037, "jhis_g7b_point_japanese_envoys", "遣唐使：日本派使团学习唐朝制度与文化，阿倍仲麻吕在华任职", 1, SUBJECT, 220005),
    (220038, "jhis_g7b_point_jianzhen", "鉴真东渡：六次东渡日本，传播佛法、建筑与医药技术", 2, SUBJECT, 220005),
    (220039, "jhis_g7b_point_xuanzang", "玄奘西行：前往天竺取经，著《大唐西域记》记录中亚南亚见闻", 3, SUBJECT, 220005),

    # 安史之乱与唐朝衰亡
    (220040, "jhis_g7b_point_anlushan", "安史之乱：755年安禄山、史思明起兵，是唐朝由盛转衰的转折点", 1, SUBJECT, 220006),
    (220041, "jhis_g7b_point_fanzhen", "藩镇割据与宦官专权：中央集权削弱，875年黄巢起义沉重打击唐朝", 2, SUBJECT, 220006),
    (220042, "jhis_g7b_point_tang_end", "唐朝灭亡：907年朱温建立后梁，中国进入五代十国时期", 3, SUBJECT, 220006),

    # 北宋的政治与重文轻武
    (220043, "jhis_g7b_point_chenqiao", "陈桥兵变：960年赵匡胤建立北宋，定都开封，“杯酒释兵权”", 1, SUBJECT, 220007),
    (220044, "jhis_g7b_point_civil_rule", "重文轻武：文臣任知州、设通判与转运使，分割相权，防止武将专权", 2, SUBJECT, 220007),
    (220045, "jhis_g7b_point_wang_anshi", "王安石变法：1069年推行青苗法、募役法、方田均税法、保甲法，成效与弊端并存", 3, SUBJECT, 220007),

    # 辽宋夏金民族政权并立
    (220046, "jhis_g7b_point_chanyuan", "澶渊之盟：1005年宋辽议和，宋给辽岁币，此后保持长期和平", 1, SUBJECT, 220008),
    (220047, "jhis_g7b_point_western_xia", "西夏：1038年党项族元昊称帝，宋夏议和，元昊称臣、宋给岁币", 2, SUBJECT, 220008),
    (220048, "jhis_g7b_point_jin_song", "金与南宋对峙：1127年靖康之变北宋灭亡，岳飞抗金，1141年宋金以淮水—大散关为界", 3, SUBJECT, 220008),

    # 宋代经济与重心南移
    (220049, "jhis_g7b_point_champa_rice", "占城稻推广：水稻产量跃居粮食作物首位，“苏湖熟，天下足”", 1, SUBJECT, 220009),
    (220050, "jhis_g7b_point_song_handicraft", "宋代手工业：景德镇成为瓷都，南宋后期棉纺织业在南方兴起", 2, SUBJECT, 220009),
    (220051, "jhis_g7b_point_jiaozi", "交子与市舶司：四川出现世界最早纸币，广州泉州设市舶司管理海外贸易", 3, SUBJECT, 220009),
    (220052, "jhis_g7b_point_economy_south", "经济重心南移：南宋时南方经济超过北方，经济重心南移完成", 4, SUBJECT, 220009),

    # 蒙古兴起与元朝统一
    (220053, "jhis_g7b_point_genghis_khan", "成吉思汗：1206年铁木真统一蒙古草原，建立蒙古政权", 1, SUBJECT, 220010),
    (220054, "jhis_g7b_point_yuan_founding", "元朝建立：1271年忽必烈定国号元、定都大都，1276年攻占临安", 2, SUBJECT, 220010),
    (220055, "jhis_g7b_point_yuan_unify", "元朝统一：1279年完成全国统一，促进民族交融，回族逐渐形成", 3, SUBJECT, 220010),

    # 元朝的行省制度与边疆管理
    (220056, "jhis_g7b_point_xingsheng", "行省制度：中央设中书省，地方设行中书省，是我国省级行政区划的开端", 1, SUBJECT, 220011),
    (220057, "jhis_g7b_point_xuanzheng_yuan", "宣政院：管理西藏军民事务，西藏正式成为中央直接管辖的地方行政区域", 2, SUBJECT, 220011),
    (220058, "jhis_g7b_point_penghu", "澎湖巡检司：管辖澎湖和琉球，是中央政府首次在台湾地区正式建立行政机构", 3, SUBJECT, 220011),

    # 宋元都市文化与文学
    (220059, "jhis_g7b_point_wazi", "瓦子与勾栏：开封、临安市民文化繁荣，早市夜市与节日活动丰富", 1, SUBJECT, 220012),
    (220060, "jhis_g7b_point_song_ci", "宋词：苏轼、辛弃疾豪放派，李清照婉约派，词成为宋代文学主流", 2, SUBJECT, 220012),
    (220061, "jhis_g7b_point_yuan_qu", "元曲：关汉卿《窦娥冤》与马致远等元曲四大家，通俗文学兴盛", 3, SUBJECT, 220012),

    # 宋元科技与中外交通
    (220062, "jhis_g7b_point_movable_type", "活字印刷术：北宋毕昇发明泥活字，元代出现木活字与转轮排字法", 1, SUBJECT, 220013),
    (220063, "jhis_g7b_point_compass_powder", "指南针与火药：北宋指南针用于航海，宋元火药广泛用于军事", 2, SUBJECT, 220013),
    (220064, "jhis_g7b_point_shenkuo", "沈括《梦溪笔谈》与郭守敬《授时历》：一年365.2425天，科技成就突出", 3, SUBJECT, 220013),
    (220065, "jhis_g7b_point_marco_polo", "元朝驿站与海上丝绸之路：交通发达，马可·波罗来华并留下游记", 4, SUBJECT, 220013),

    # 明朝君主专制的强化
    (220066, "jhis_g7b_point_abolish_chancellor", "废除丞相：1380年明太祖废丞相和中书省，权分六部、直接对皇帝负责", 1, SUBJECT, 220014),
    (220067, "jhis_g7b_point_three_commissions", "三司与厂卫：地方设布政使司、按察使司、都指挥使司，锦衣卫与东厂监察臣民", 2, SUBJECT, 220014),
    (220068, "jhis_g7b_point_eight_legged", "八股取士：明朝科举限“四书”“五经”命题、答卷用八股文，禁锢思想", 3, SUBJECT, 220014),
    (220069, "jhis_g7b_point_beijing_capital", "明成祖迁都北京并设立内阁，北京城布局体现皇权至上", 4, SUBJECT, 220014),

    # 明朝的对外关系
    (220070, "jhis_g7b_point_zheng_he", "郑和下西洋：1405—1433年七下西洋，最远到达非洲东海岸和红海沿岸", 1, SUBJECT, 220015),
    (220071, "jhis_g7b_point_qi_jiguang", "戚继光抗倭：组建“戚家军”，台州九战九捷，东南沿海倭患基本平息", 2, SUBJECT, 220015),
    (220072, "jhis_g7b_point_macau", "葡萄牙攫取澳门：1553年葡萄牙殖民者获得在澳门的居住权", 3, SUBJECT, 220015),

    # 明朝的科技建筑与文学
    (220073, "jhis_g7b_point_bencao", "李时珍《本草纲目》：总结古代药物学成就，被誉为“东方医药巨典”", 1, SUBJECT, 220016),
    (220074, "jhis_g7b_point_tiangong", "宋应星《天工开物》：总结农业和手工业生产技术，“中国17世纪的工艺百科全书”", 2, SUBJECT, 220016),
    (220075, "jhis_g7b_point_nongzheng", "徐光启《农政全书》：总结我国古代农业生产经验，吸收西方水利技术", 3, SUBJECT, 220016),
    (220076, "jhis_g7b_point_great_wall", "明长城与北京城：长城东起鸭绿江、西至嘉峪关，紫禁城为皇家宫殿", 4, SUBJECT, 220016),
    (220077, "jhis_g7b_point_ming_novels", "明代小说：《三国演义》《水浒传》《西游记》，长篇白话小说走向成熟", 5, SUBJECT, 220016),

    # 明朝的灭亡与清军入关
    (220078, "jhis_g7b_point_ming_corruption", "明末政治腐败：皇帝昏庸、宦官专权、土地兼并严重，天灾不断", 1, SUBJECT, 220017),
    (220079, "jhis_g7b_point_li_zicheng", "李自成起义：提出“均田免赋”，1644年攻入北京，明朝灭亡", 2, SUBJECT, 220017),
    (220080, "jhis_g7b_point_qing_entry", "清军入关：1644年吴三桂引清军入关，清朝逐步统一全国", 3, SUBJECT, 220017),

    # 清朝统一多民族国家的巩固
    (220081, "jhis_g7b_point_zheng_chenggong", "郑成功收复台湾：1661—1662年驱逐荷兰殖民者，1684年清朝设台湾府", 1, SUBJECT, 220018),
    (220082, "jhis_g7b_point_nerchinsk", "雅克萨之战与《尼布楚条约》：1689年签订，划定中俄东段边界", 2, SUBJECT, 220018),
    (220083, "jhis_g7b_point_xinjiang", "平定准噶尔与大小和卓叛乱：设伊犁将军管辖新疆地区", 3, SUBJECT, 220018),
    (220084, "jhis_g7b_point_tibet", "驻藏大臣与金瓶掣签：1727年设驻藏大臣，1793年颁布《钦定藏内善后章程》", 4, SUBJECT, 220018),
    (220085, "jhis_g7b_point_qing_territory", "清朝疆域：西跨葱岭、北接西伯利亚、东临太平洋、南至南海诸岛", 5, SUBJECT, 220018),

    # 清朝前期社会经济与闭关锁国
    (220086, "jhis_g7b_point_qing_agriculture", "清朝农业恢复：垦荒兴修水利，推广玉米、甘薯等高产作物，人口快速增长", 1, SUBJECT, 220019),
    (220087, "jhis_g7b_point_qing_commerce", "清朝手工业与商业：丝织棉织瓷业发展，晋商、徽商等商帮活跃", 2, SUBJECT, 220019),
    (220088, "jhis_g7b_point_seclusion", "闭关锁国：严格限制对外贸易，仅留广州一口，由十三行统一经营", 3, SUBJECT, 220019),

    # 清朝君主专制的顶峰
    (220089, "jhis_g7b_point_grand_council", "军机处：雍正帝设立，军机大臣跪受笔录，君主专制达到顶峰", 1, SUBJECT, 220020),
    (220090, "jhis_g7b_point_literary_inquisition", "文字狱：康熙、雍正、乾隆三朝大兴文字狱，禁锢思想、摧残文化", 2, SUBJECT, 220020),
    (220091, "jhis_g7b_point_memorial", "奏折制度：官员密折奏事，皇帝直接掌控地方，强化对官僚机构的控制", 3, SUBJECT, 220020),

    # 明清文学艺术与京剧
    (220092, "jhis_g7b_point_dream_red_chamber", "《红楼梦》：曹雪芹著，以宝黛爱情悲剧为线索，我国古典小说的高峰", 1, SUBJECT, 220021),
    (220093, "jhis_g7b_point_kunqu", "昆曲：明朝末年成为全国性剧种，代表作《牡丹亭》《长生殿》《桃花扇》", 2, SUBJECT, 220021),
    (220094, "jhis_g7b_point_peking_opera", "京剧：1790年徽班进京，吸收昆曲秦腔等，道光年间形成，被誉为“国粹”", 3, SUBJECT, 220021),
)

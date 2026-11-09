"""统编版（2019）高中历史选择性必修第二册（经济与社会生活）：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 8
G10 = 10
BOOK_ID = 8104

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中历史选择性必修第二册（经济与社会生活）",
    "hist_e2",
    4,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (840101, "第一单元 食物生产与社会生活", "hist_e2_u01", 1, BOOK_ID, None),
    (840102, "第二单元 生产工具与劳作方式", "hist_e2_u02", 2, BOOK_ID, None),
    (840103, "第三单元 商业贸易与日常生活", "hist_e2_u03", 3, BOOK_ID, None),
    (840104, "第四单元 村落、城镇与居住环境", "hist_e2_u04", 4, BOOK_ID, None),
    (840105, "第五单元 交通与社会变迁", "hist_e2_u05", 5, BOOK_ID, None),
    (840106, "第六单元 医疗与公共卫生", "hist_e2_u06", 6, BOOK_ID, None),
    (840111, "第1课 从食物采集到食物生产", "hist_e2_l01", 1, BOOK_ID, 840101),
    (840112, "第2课 新航路开辟后的食物物种交流", "hist_e2_l02", 2, BOOK_ID, 840101),
    (840113, "第3课 现代食物的生产、储备与食品安全", "hist_e2_l03", 3, BOOK_ID, 840101),
    (840114, "第4课 古代的生产工具与劳作", "hist_e2_l04", 1, BOOK_ID, 840102),
    (840115, "第5课 工业革命与工厂制度", "hist_e2_l05", 2, BOOK_ID, 840102),
    (840116, "第6课 现代科技进步与人类社会发展", "hist_e2_l06", 3, BOOK_ID, 840102),
    (840117, "第7课 古代的商业贸易", "hist_e2_l07", 1, BOOK_ID, 840103),
    (840118, "第8课 世界市场与商业贸易", "hist_e2_l08", 2, BOOK_ID, 840103),
    (840119, "第9课 20世纪以来人类的经济与生活", "hist_e2_l09", 3, BOOK_ID, 840103),
    (840120, "第10课 古代的村落、集镇和城市", "hist_e2_l10", 1, BOOK_ID, 840104),
    (840121, "第11课 近代以来的城市化进程", "hist_e2_l11", 2, BOOK_ID, 840104),
    (840122, "第12课 水陆交通的变迁", "hist_e2_l12", 1, BOOK_ID, 840105),
    (840123, "第13课 现代交通运输的新变化", "hist_e2_l13", 2, BOOK_ID, 840105),
    (840124, "第14课 历史上的疫病与医学成就", "hist_e2_l14", 1, BOOK_ID, 840106),
    (840125, "第15课 现代医疗卫生体系与社会生活", "hist_e2_l15", 2, BOOK_ID, 840106),
)

# id / code / name / sort_order / subject_id / parent_id
# 84 00 xx 为册域、单元域与课域结构层，84 02 xx 为考点层，避开章节 84 01 xx 段。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (840001, "hist_e2_domain_food", "食为民天：食物生产与社会生活", 1, SUBJECT, None),
    (840002, "hist_e2_domain_tools", "器利工巧：生产工具与劳作方式", 2, SUBJECT, None),
    (840003, "hist_e2_domain_trade", "市通有无：商业贸易与日常生活", 3, SUBJECT, None),
    (840004, "hist_e2_domain_settlement", "聚落营建：村落、城镇与居住环境", 4, SUBJECT, None),
    (840005, "hist_e2_domain_transport", "舟车千里：交通与社会变迁", 5, SUBJECT, None),
    (840006, "hist_e2_domain_health", "疫病防治：医疗与公共卫生", 6, SUBJECT, None),

    # 单元域层
    (840007, "hist_e2_unit01", "第一单元 食物生产与社会生活", 1, SUBJECT, 840001),
    (840008, "hist_e2_unit02", "第二单元 生产工具与劳作方式", 1, SUBJECT, 840002),
    (840009, "hist_e2_unit03", "第三单元 商业贸易与日常生活", 1, SUBJECT, 840003),
    (840010, "hist_e2_unit04", "第四单元 村落、城镇与居住环境", 1, SUBJECT, 840004),
    (840011, "hist_e2_unit05", "第五单元 交通与社会变迁", 1, SUBJECT, 840005),
    (840012, "hist_e2_unit06", "第六单元 医疗与公共卫生", 1, SUBJECT, 840006),

    # 课域层
    (840013, "hist_e2_lesson01", "第1课 从食物采集到食物生产", 1, SUBJECT, 840007),
    (840014, "hist_e2_lesson02", "第2课 新航路开辟后的食物物种交流", 2, SUBJECT, 840007),
    (840015, "hist_e2_lesson03", "第3课 现代食物的生产、储备与食品安全", 3, SUBJECT, 840007),
    (840016, "hist_e2_lesson04", "第4课 古代的生产工具与劳作", 1, SUBJECT, 840008),
    (840017, "hist_e2_lesson05", "第5课 工业革命与工厂制度", 2, SUBJECT, 840008),
    (840018, "hist_e2_lesson06", "第6课 现代科技进步与人类社会发展", 3, SUBJECT, 840008),
    (840019, "hist_e2_lesson07", "第7课 古代的商业贸易", 1, SUBJECT, 840009),
    (840020, "hist_e2_lesson08", "第8课 世界市场与商业贸易", 2, SUBJECT, 840009),
    (840021, "hist_e2_lesson09", "第9课 20世纪以来人类的经济与生活", 3, SUBJECT, 840009),
    (840022, "hist_e2_lesson10", "第10课 古代的村落、集镇和城市", 1, SUBJECT, 840010),
    (840023, "hist_e2_lesson11", "第11课 近代以来的城市化进程", 2, SUBJECT, 840010),
    (840024, "hist_e2_lesson12", "第12课 水陆交通的变迁", 1, SUBJECT, 840011),
    (840025, "hist_e2_lesson13", "第13课 现代交通运输的新变化", 2, SUBJECT, 840011),
    (840026, "hist_e2_lesson14", "第14课 历史上的疫病与医学成就", 1, SUBJECT, 840012),
    (840027, "hist_e2_lesson15", "第15课 现代医疗卫生体系与社会生活", 2, SUBJECT, 840012),

    # 第一单元考点
    (840201, "hist_e2_point_paleolithic", "旧石器时代采集渔猎经济：打制石器、群体协作与迁徙生活", 1, SUBJECT, 840013),
    (840202, "hist_e2_point_agri_origin", "新石器时代农业起源：西亚小麦大麦、中国南稻北粟与中美洲玉米", 2, SUBJECT, 840013),
    (840203, "hist_e2_point_agri_revolution", "农业革命的历史意义：定居聚落、人口增长与社会分工扩大", 3, SUBJECT, 840013),
    (840204, "hist_e2_point_pastoral", "畜牧业的产生：动物驯化与游牧、农耕两种生产方式的分化", 4, SUBJECT, 840013),
    (840205, "hist_e2_point_agri_regions", "古代农业区域类型：大河灌溉农业、地中海农业与美洲梯田农业", 5, SUBJECT, 840013),
    (840206, "hist_e2_point_surplus_class", "剩余产品与社会分层：私有制、阶级与国家起源的经济基础", 6, SUBJECT, 840013),
    (840207, "hist_e2_point_food_process", "古代食物加工与储存：陶器炊煮、窖藏腌制与谷物酿造", 7, SUBJECT, 840013),
    (840208, "hist_e2_point_columbian_to_eurasia", "美洲作物传入欧亚：玉米、马铃薯、甘薯、番茄与辣椒的全球扩散", 1, SUBJECT, 840014),
    (840209, "hist_e2_point_eurasia_to_america", "欧亚作物传入美洲：小麦、水稻、甘蔗、葡萄与牲畜的移植", 2, SUBJECT, 840014),
    (840210, "hist_e2_point_europe_diet", "物种交流与欧洲社会：马铃薯玉米缓解饥荒、人口增长与饮食结构变化", 3, SUBJECT, 840014),
    (840211, "hist_e2_point_china_crops", "物种交流与中国：明清高产作物推广、人口激增与山地丘陵开发", 4, SUBJECT, 840014),
    (840212, "hist_e2_point_plantation_slave", "物种交流与美洲非洲：甘蔗种植园、奴隶贸易与单一作物经济", 5, SUBJECT, 840014),
    (840213, "hist_e2_point_exchange_duality", "物种交流的双重影响：食物结构丰富与生态破坏、疫病传播并存", 6, SUBJECT, 840014),
    (840214, "hist_e2_point_modern_agri_tech", "现代农业技术：机械化、化学化、良种化与绿色革命", 1, SUBJECT, 840015),
    (840215, "hist_e2_point_food_industry", "现代食品加工与保藏：工业化生产、冷冻冷藏与无菌包装", 2, SUBJECT, 840015),
    (840216, "hist_e2_point_grain_reserve", "现代粮食储备：国家储备体系、粮仓技术与国际粮食援助", 3, SUBJECT, 840015),
    (840217, "hist_e2_point_food_risk", "食品安全风险：农药残留、添加剂滥用、微生物污染与造假事件", 4, SUBJECT, 840015),
    (840218, "hist_e2_point_food_governance", "食品安全治理：标准体系、检验检疫、追溯制度与《食品安全法》", 5, SUBJECT, 840015),
    (840219, "hist_e2_point_global_food_security", "全球粮食安全：饥饿与营养不良、耕地水资源约束与粮食危机", 6, SUBJECT, 840015),

    # 第二单元考点
    (840220, "hist_e2_point_stone_tools", "旧石器与新石器工具：打制石器、磨制石器、骨角器与陶器", 1, SUBJECT, 840016),
    (840221, "hist_e2_point_bronze_farming", "青铜农具与青铜时代：商周青铜工具与井田制下的集体劳作", 2, SUBJECT, 840016),
    (840222, "hist_e2_point_iron_plow", "铁犁牛耕的推广：春秋战国铁农具、汉代耦犁与代田法", 3, SUBJECT, 840016),
    (840223, "hist_e2_point_irrigation_tools", "古代灌溉工具：翻车、筒车、渴乌与西域坎儿井", 4, SUBJECT, 840016),
    (840224, "hist_e2_point_textile_tools", "古代纺织工具：纺轮、织机、黄道婆与棉纺织业兴起", 5, SUBJECT, 840016),
    (840225, "hist_e2_point_farming_evolution", "耕作方式演进：刀耕火种、石器锄耕、铁犁牛耕与精耕细作", 6, SUBJECT, 840016),
    (840226, "hist_e2_point_labor_forms", "劳作组织形态：集体劳作、个体小农、家庭手工业与官营作坊", 7, SUBJECT, 840016),
    (840227, "hist_e2_point_industrial_tech", "工业革命的技术突破：珍妮纺纱机、改良蒸汽机与机器大生产", 1, SUBJECT, 840017),
    (840228, "hist_e2_point_factory_birth", "工厂制度的产生：生产集中、机器分工与严格劳动纪律", 2, SUBJECT, 840017),
    (840229, "hist_e2_point_factory_features", "工厂制度的特点：雇佣劳动、固定工时与生产流水线化", 3, SUBJECT, 840017),
    (840230, "hist_e2_point_factory_impact", "工厂制度的社会影响：城市化加速、工人阶级形成与劳资矛盾", 4, SUBJECT, 840017),
    (840231, "hist_e2_point_china_factory", "中国近代工厂：洋务军事民用企业、民族资本工厂与实业救国", 5, SUBJECT, 840017),
    (840232, "hist_e2_point_factory_modern", "工厂制度的现代演变：科学管理、流水线与自动化智能工厂", 6, SUBJECT, 840017),
    (840233, "hist_e2_point_third_revolution", "第三次科技革命：原子能、电子计算机、航天与生物技术", 1, SUBJECT, 840018),
    (840234, "hist_e2_point_internet", "计算机与互联网：信息时代、网络经济与数字化生活", 2, SUBJECT, 840018),
    (840235, "hist_e2_point_ai_automation", "人工智能与自动化：智能制造、机器人替代与新就业形态", 3, SUBJECT, 840018),
    (840236, "hist_e2_point_biotech", "生物技术与医药：基因工程、疫苗研发与器官移植", 4, SUBJECT, 840018),
    (840237, "hist_e2_point_tech_production", "科技进步与生产方式：生产率提高、产业结构升级与全球化分工", 5, SUBJECT, 840018),
    (840238, "hist_e2_point_tech_problems", "科技发展的社会问题：数字鸿沟、隐私安全与科技伦理", 6, SUBJECT, 840018),

    # 第三单元考点
    (840239, "hist_e2_point_trade_origin", "古代商业起源：剩余产品交换、商朝贝币与专业商人出现", 1, SUBJECT, 840019),
    (840240, "hist_e2_point_spring_trade", "春秋战国商业繁荣：工商食官瓦解、货币流通与都会兴起", 2, SUBJECT, 840019),
    (840241, "hist_e2_point_han_tang_trade", "秦汉至隋唐商业：丝绸之路、坊市制度与邸店柜坊", 3, SUBJECT, 840019),
    (840242, "hist_e2_point_song_trade_rev", "宋元商业革命：坊市界限打破、交子纸币与市舶司海外贸易", 4, SUBJECT, 840019),
    (840243, "hist_e2_point_ming_qing_trade", "明清商业发展：商帮、票号、白银流通与工商业市镇", 5, SUBJECT, 840019),
    (840244, "hist_e2_point_trade_policy", "古代商业政策：重农抑商、盐铁官营与明清海禁闭关", 6, SUBJECT, 840019),
    (840245, "hist_e2_point_commercial_rev", "新航路开辟与商业革命：贸易中心转移、价格革命与经营方式变革", 1, SUBJECT, 840020),
    (840246, "hist_e2_point_triangle_trade", "早期殖民扩张与三角贸易：奴隶贸易、种植园与资本原始积累", 2, SUBJECT, 840020),
    (840247, "hist_e2_point_world_market", "工业革命与世界市场：商品输出、交通通讯改善与国际分工", 3, SUBJECT, 840020),
    (840248, "hist_e2_point_monopoly", "第二次工业革命与垄断：资本输出、垄断组织与世界市场最终形成", 4, SUBJECT, 840020),
    (840249, "hist_e2_point_business_forms", "近代商业经营方式：股份公司、证券交易所、百货公司与广告", 5, SUBJECT, 840020),
    (840250, "hist_e2_point_china_market", "近代中国卷入世界市场：通商口岸、协定关税与民族工商业兴衰", 6, SUBJECT, 840020),
    (840251, "hist_e2_point_early_20c", "20世纪前期世界经济：一战冲击、1929年大危机与罗斯福新政", 1, SUBJECT, 840021),
    (840252, "hist_e2_point_postwar_capitalism", "二战后资本主义调整：国家干预、福利国家与科技革命", 2, SUBJECT, 840021),
    (840253, "hist_e2_point_socialist_economy", "社会主义经济实践：苏联模式、新经济政策与计划经济体制", 3, SUBJECT, 840021),
    (840254, "hist_e2_point_globalization", "经济全球化：关贸总协定、世界贸易组织与跨国公司", 4, SUBJECT, 840021),
    (840255, "hist_e2_point_regional_bloc", "区域经济集团化：欧洲联盟、北美自由贸易区与亚太经合组织", 5, SUBJECT, 840021),
    (840256, "hist_e2_point_new_economy", "当代经济新形态：电子商务、移动支付与共享经济", 6, SUBJECT, 840021),
    (840257, "hist_e2_point_developing_economy", "发展中国家经济：民族独立后的工业化、南北差距与新兴市场", 7, SUBJECT, 840021),
    (840258, "hist_e2_point_village_birth", "村落的产生：农业定居、半坡与河姆渡聚落形态", 1, SUBJECT, 840022),
    (840259, "hist_e2_point_village_function", "古代村落功能：居住生产、防卫自卫与宗族组织", 2, SUBJECT, 840022),
    (840260, "hist_e2_point_town_market", "集镇的出现：商品交换、草市墟市与工商业市镇", 3, SUBJECT, 840022),
    (840261, "hist_e2_point_china_city", "中国古代城市：坊市制、长安洛阳与明清北京城", 4, SUBJECT, 840022),
    (840262, "hist_e2_point_greek_roman_city", "古希腊罗马城市：雅典卫城、罗马城与公共设施", 5, SUBJECT, 840022),
    (840263, "hist_e2_point_medieval_city", "中古西欧城市：自治城市、行会组织与市民阶层", 6, SUBJECT, 840022),
    (840264, "hist_e2_point_urban_rural", "城乡关系与差异：人口规模、功能分工与治理方式", 7, SUBJECT, 840022),

    # 第四单元考点
    (840265, "hist_e2_point_urbanization_start", "工业革命与城市化启动：英国城市人口增长与曼彻斯特", 1, SUBJECT, 840023),
    (840266, "hist_e2_point_urban_problems", "城市化问题：贫民窟、环境污染、交通拥堵与公共卫生危机", 2, SUBJECT, 840023),
    (840267, "hist_e2_point_urban_infrastructure", "城市基础设施：供水排水、燃气照明、公共交通与城市规划", 3, SUBJECT, 840023),
    (840268, "hist_e2_point_china_modern_city", "中国近代城市化：通商口岸城市、上海天津与租界", 4, SUBJECT, 840023),
    (840269, "hist_e2_point_china_urbanization", "新中国城市化：计划经济工业城市、改革开放与户籍制度", 5, SUBJECT, 840023),
    (840270, "hist_e2_point_modern_city", "现代城市发展：郊区化、卫星城、生态城市与智慧城市", 6, SUBJECT, 840023),

    # 第五单元考点
    (840271, "hist_e2_point_ancient_road", "古代陆路交通：驿道驰道、丝绸之路与驿站制度", 1, SUBJECT, 840024),
    (840272, "hist_e2_point_ancient_waterway", "古代水路交通：灵渠、大运河、造船技术与漕运", 2, SUBJECT, 840024),
    (840273, "hist_e2_point_railway", "近代铁路兴起：史蒂芬孙火车、铁路建设与工业革命", 3, SUBJECT, 840024),
    (840274, "hist_e2_point_steamship_canal", "近代航运发展：轮船、苏伊士运河与巴拿马运河", 4, SUBJECT, 840024),
    (840275, "hist_e2_point_china_modern_transport", "近代中国交通：铁路修建、轮船招商局与交通主权", 5, SUBJECT, 840024),
    (840276, "hist_e2_point_automobile", "汽车与公路：内燃机汽车、高速公路与公路运输网", 6, SUBJECT, 840024),
    (840277, "hist_e2_point_aviation", "航空运输：莱特兄弟试飞、喷气式飞机与民航业", 1, SUBJECT, 840025),
    (840278, "hist_e2_point_high_speed_rail", "高速铁路：日本新干线、中国高铁与磁悬浮列车", 2, SUBJECT, 840025),
    (840279, "hist_e2_point_container_logistics", "集装箱与物流：集装箱运输、多式联运与现代物流", 3, SUBJECT, 840025),
    (840280, "hist_e2_point_urban_transit", "城市公共交通：地铁、公交与共享出行", 4, SUBJECT, 840025),
    (840281, "hist_e2_point_intelligent_transport", "交通智能化：卫星导航、自动驾驶与智能交通系统", 5, SUBJECT, 840025),
    (840282, "hist_e2_point_transport_impact", "交通发展的影响：时空观念改变、城市化与全球化加速", 6, SUBJECT, 840025),

    # 第六单元考点
    (840283, "hist_e2_point_ancient_plague", "古代重大疫病：雅典瘟疫、罗马瘟疫、黑死病与天花", 1, SUBJECT, 840026),
    (840284, "hist_e2_point_plague_impact", "疫病的历史影响：人口锐减、社会动荡与制度变革", 2, SUBJECT, 840026),
    (840285, "hist_e2_point_tcm", "中国古代医学：《黄帝内经》《伤寒杂病论》、华佗与《本草纲目》", 3, SUBJECT, 840026),
    (840286, "hist_e2_point_western_medicine", "西方医学发展：希波克拉底、解剖学、巴斯德与细菌学", 4, SUBJECT, 840026),
    (840287, "hist_e2_point_vaccination", "疫苗接种与免疫：牛痘接种、巴斯德疫苗与免疫学建立", 5, SUBJECT, 840026),
    (840288, "hist_e2_point_modern_china_medicine", "近代中国医学：西医传入、协和医学院与中西医汇通", 6, SUBJECT, 840026),
    (840289, "hist_e2_point_modern_health_system", "现代医疗卫生体系：英国国民健康服务体系与医疗保险制度", 1, SUBJECT, 840027),
    (840290, "hist_e2_point_china_health_system", "中国医疗卫生体系：赤脚医生、合作医疗与分级诊疗", 2, SUBJECT, 840027),
    (840291, "hist_e2_point_public_health", "公共卫生制度：传染病防治、计划免疫与卫生监督", 3, SUBJECT, 840027),
    (840292, "hist_e2_point_medical_tech", "现代医学技术：抗生素、器官移植、影像诊断与基因治疗", 4, SUBJECT, 840027),
    (840293, "hist_e2_point_medical_insurance", "医疗保障制度：城镇职工医保、新农合与全民医保", 5, SUBJECT, 840027),
    (840294, "hist_e2_point_health_lifestyle", "健康观念与生活方式：预防为主、全民健身与心理健康", 6, SUBJECT, 840027),
)

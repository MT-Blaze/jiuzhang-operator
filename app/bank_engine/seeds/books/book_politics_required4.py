"""统编版（2019）高中思想政治必修第四册（哲学与文化）：课框目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G10 = 10
BOOK_ID = 7104

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中思想政治必修第四册（哲学与文化）",
    "pol_r4",
    4,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (740101, "第一单元 探索世界与把握规律", "pol_r4_u01", 1, BOOK_ID, None),
    (740102, "第二单元 认识社会与价值选择", "pol_r4_u02", 2, BOOK_ID, None),
    (740103, "第三单元 文化传承与文化创新", "pol_r4_u03", 3, BOOK_ID, None),
    (740111, "第一课 时代精神的精华", "pol_r4_l01", 1, BOOK_ID, 740101),
    (740112, "第二课 探究世界的本质", "pol_r4_l02", 2, BOOK_ID, 740101),
    (740113, "第三课 把握世界的规律", "pol_r4_l03", 3, BOOK_ID, 740101),
    (740114, "第四课 探索认识的奥秘", "pol_r4_l04", 1, BOOK_ID, 740102),
    (740115, "第五课 寻觅社会的真谛", "pol_r4_l05", 2, BOOK_ID, 740102),
    (740116, "第六课 实现人生的价值", "pol_r4_l06", 3, BOOK_ID, 740102),
    (740117, "第七课 继承发展中华优秀传统文化", "pol_r4_l07", 1, BOOK_ID, 740103),
    (740118, "第八课 学习借鉴外来文化的有益成果", "pol_r4_l08", 2, BOOK_ID, 740103),
    (740119, "第九课 发展中国特色社会主义文化", "pol_r4_l09", 3, BOOK_ID, 740103),
    (740121, "第一框 追求智慧的学问", "pol_r4_l01_s01", 1, BOOK_ID, 740111),
    (740122, "第二框 哲学的基本问题", "pol_r4_l01_s02", 2, BOOK_ID, 740111),
    (740123, "第三框 科学的世界观和方法论", "pol_r4_l01_s03", 3, BOOK_ID, 740111),
    (740124, "第一框 世界的物质性", "pol_r4_l02_s01", 1, BOOK_ID, 740112),
    (740125, "第二框 运动的规律性", "pol_r4_l02_s02", 2, BOOK_ID, 740112),
    (740126, "第一框 世界是普遍联系的", "pol_r4_l03_s01", 1, BOOK_ID, 740113),
    (740127, "第二框 世界是永恒发展的", "pol_r4_l03_s02", 2, BOOK_ID, 740113),
    (740128, "第三框 唯物辩证法的实质与核心", "pol_r4_l03_s03", 3, BOOK_ID, 740113),
    (740129, "第一框 人的认识从何而来", "pol_r4_l04_s01", 1, BOOK_ID, 740114),
    (740130, "第二框 在实践中追求和发展真理", "pol_r4_l04_s02", 2, BOOK_ID, 740114),
    (740131, "第一框 社会历史的本质", "pol_r4_l05_s01", 1, BOOK_ID, 740115),
    (740132, "第二框 社会历史的发展", "pol_r4_l05_s02", 2, BOOK_ID, 740115),
    (740133, "第三框 社会历史的主体", "pol_r4_l05_s03", 3, BOOK_ID, 740115),
    (740134, "第一框 价值与价值观", "pol_r4_l06_s01", 1, BOOK_ID, 740116),
    (740135, "第二框 价值判断与价值选择", "pol_r4_l06_s02", 2, BOOK_ID, 740116),
    (740136, "第三框 价值的创造和实现", "pol_r4_l06_s03", 3, BOOK_ID, 740116),
    (740137, "第一框 文化的内涵与功能", "pol_r4_l07_s01", 1, BOOK_ID, 740117),
    (740138, "第二框 正确认识中华传统文化", "pol_r4_l07_s02", 2, BOOK_ID, 740117),
    (740139, "第三框 弘扬中华优秀传统文化与民族精神", "pol_r4_l07_s03", 3, BOOK_ID, 740117),
    (740140, "第一框 文化的民族性与多样性", "pol_r4_l08_s01", 1, BOOK_ID, 740118),
    (740141, "第二框 文化交流与文化交融", "pol_r4_l08_s02", 2, BOOK_ID, 740118),
    (740142, "第三框 正确对待外来文化", "pol_r4_l08_s03", 3, BOOK_ID, 740118),
    (740143, "第一框 文化发展的必然选择", "pol_r4_l09_s01", 1, BOOK_ID, 740119),
    (740144, "第二框 文化发展的基本路径", "pol_r4_l09_s02", 2, BOOK_ID, 740119),
    (740145, "第三框 文化强国与文化自信", "pol_r4_l09_s03", 3, BOOK_ID, 740119),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (740001, "pol_r4_domain_dialectical_materialism", "辩证唯物论：世界的本质与物质统一性", 1, SUBJECT, None),
    (740002, "pol_r4_domain_materialist_dialectics", "唯物辩证法：联系、发展与矛盾", 2, SUBJECT, None),
    (740003, "pol_r4_domain_epistemology", "认识论：实践、认识与真理", 3, SUBJECT, None),
    (740004, "pol_r4_domain_historical_materialism", "历史唯物主义：社会历史与人生价值", 4, SUBJECT, None),
    (740005, "pol_r4_domain_culture", "文化传承与文化创新", 5, SUBJECT, None),

    # 单元域层
    (740006, "pol_r4_unit01_materialism", "第一单元 探索世界与把握规律（唯物论部分）", 1, SUBJECT, 740001),
    (740007, "pol_r4_unit01_dialectics", "第一单元 探索世界与把握规律（辩证法部分）", 1, SUBJECT, 740002),
    (740008, "pol_r4_unit02_epistemology", "第二单元 认识社会与价值选择（认识论部分）", 1, SUBJECT, 740003),
    (740009, "pol_r4_unit02_history", "第二单元 认识社会与价值选择（唯物史观部分）", 1, SUBJECT, 740004),
    (740010, "pol_r4_unit03_culture", "第三单元 文化传承与文化创新", 1, SUBJECT, 740005),

    # 课域层
    (740011, "pol_r4_lesson01", "第一课 时代精神的精华", 1, SUBJECT, 740006),
    (740012, "pol_r4_lesson02", "第二课 探究世界的本质", 2, SUBJECT, 740006),
    (740013, "pol_r4_lesson03", "第三课 把握世界的规律", 1, SUBJECT, 740007),
    (740014, "pol_r4_lesson04", "第四课 探索认识的奥秘", 1, SUBJECT, 740008),
    (740015, "pol_r4_lesson05", "第五课 寻觅社会的真谛", 1, SUBJECT, 740009),
    (740016, "pol_r4_lesson06", "第六课 实现人生的价值", 2, SUBJECT, 740009),
    (740017, "pol_r4_lesson07", "第七课 继承发展中华优秀传统文化", 1, SUBJECT, 740010),
    (740018, "pol_r4_lesson08", "第八课 学习借鉴外来文化的有益成果", 2, SUBJECT, 740010),
    (740019, "pol_r4_lesson09", "第九课 发展中国特色社会主义文化", 3, SUBJECT, 740010),

    # 框域层
    (740020, "pol_r4_sec_wisdom_study", "第一框 追求智慧的学问", 1, SUBJECT, 740011),
    (740021, "pol_r4_sec_basic_question", "第二框 哲学的基本问题", 2, SUBJECT, 740011),
    (740022, "pol_r4_sec_scientific_worldview", "第三框 科学的世界观和方法论", 3, SUBJECT, 740011),
    (740023, "pol_r4_sec_materiality_world", "第一框 世界的物质性", 1, SUBJECT, 740012),
    (740024, "pol_r4_sec_movement_law", "第二框 运动的规律性", 2, SUBJECT, 740012),
    (740025, "pol_r4_sec_universal_connection", "第一框 世界是普遍联系的", 1, SUBJECT, 740013),
    (740026, "pol_r4_sec_eternal_development", "第二框 世界是永恒发展的", 2, SUBJECT, 740013),
    (740027, "pol_r4_sec_contradiction_core", "第三框 唯物辩证法的实质与核心", 3, SUBJECT, 740013),
    (740028, "pol_r4_sec_where_knowledge_from", "第一框 人的认识从何而来", 1, SUBJECT, 740014),
    (740029, "pol_r4_sec_truth_in_practice", "第二框 在实践中追求和发展真理", 2, SUBJECT, 740014),
    (740030, "pol_r4_sec_social_history_essence", "第一框 社会历史的本质", 1, SUBJECT, 740015),
    (740031, "pol_r4_sec_social_history_development", "第二框 社会历史的发展", 2, SUBJECT, 740015),
    (740032, "pol_r4_sec_social_history_subject", "第三框 社会历史的主体", 3, SUBJECT, 740015),
    (740033, "pol_r4_sec_value_values", "第一框 价值与价值观", 1, SUBJECT, 740016),
    (740034, "pol_r4_sec_value_judgment", "第二框 价值判断与价值选择", 2, SUBJECT, 740016),
    (740035, "pol_r4_sec_value_creation", "第三框 价值的创造和实现", 3, SUBJECT, 740016),
    (740036, "pol_r4_sec_culture_connotation", "第一框 文化的内涵与功能", 1, SUBJECT, 740017),
    (740037, "pol_r4_sec_traditional_culture", "第二框 正确认识中华传统文化", 2, SUBJECT, 740017),
    (740038, "pol_r4_sec_national_spirit", "第三框 弘扬中华优秀传统文化与民族精神", 3, SUBJECT, 740017),
    (740039, "pol_r4_sec_national_diversity", "第一框 文化的民族性与多样性", 1, SUBJECT, 740018),
    (740040, "pol_r4_sec_exchange_blending", "第二框 文化交流与文化交融", 2, SUBJECT, 740018),
    (740041, "pol_r4_sec_foreign_culture", "第三框 正确对待外来文化", 3, SUBJECT, 740018),
    (740042, "pol_r4_sec_culture_development_choice", "第一框 文化发展的必然选择", 1, SUBJECT, 740019),
    (740043, "pol_r4_sec_culture_development_path", "第二框 文化发展的基本路径", 2, SUBJECT, 740019),
    (740044, "pol_r4_sec_culture_power_confidence", "第三框 文化强国与文化自信", 3, SUBJECT, 740019),

    # 1.1 追求智慧的学问
    (740045, "pol_r4_philosophy_and_science", "哲学与具体科学的关系：共性与个性、基础与指导", 1, SUBJECT, 740020),
    (740046, "pol_r4_worldview_methodology", "哲学是世界观与方法论的统一", 2, SUBJECT, 740020),

    # 1.2 哲学的基本问题
    (740047, "pol_r4_basic_question_content", "哲学基本问题的两方面内容及其理论地位", 1, SUBJECT, 740021),
    (740048, "pol_r4_materialism_idealism", "唯物主义与唯心主义的基本形态及划分标准", 2, SUBJECT, 740021),
    (740049, "pol_r4_dialectics_metaphysics", "辩证法与形而上学、可知论与不可知论的对立", 3, SUBJECT, 740021),

    # 1.3 科学的世界观和方法论
    (740050, "pol_r4_marxist_philosophy_conditions", "马克思主义哲学的产生条件与基本特征", 1, SUBJECT, 740022),
    (740051, "pol_r4_sinicization_achievements", "马克思主义中国化时代化的理论成果与当代价值", 2, SUBJECT, 740022),

    # 2.1 世界的物质性
    (740052, "pol_r4_matter_unity", "物质概念与世界的物质统一性原理", 1, SUBJECT, 740023),
    (740053, "pol_r4_consciousness_origin", "意识的起源、生理基础与内容", 2, SUBJECT, 740023),
    (740054, "pol_r4_matter_determines_consciousness", "物质决定意识与意识能动作用的辩证统一", 3, SUBJECT, 740023),

    # 2.2 运动的规律性
    (740055, "pol_r4_law_objectivity", "规律的含义、客观性与普遍性", 1, SUBJECT, 740024),
    (740056, "pol_r4_objective_law_initiative", "尊重客观规律与发挥主观能动性相结合、一切从实际出发", 2, SUBJECT, 740024),

    # 3.1 世界是普遍联系的
    (740057, "pol_r4_connection_features", "联系的普遍性、客观性与多样性", 1, SUBJECT, 740025),
    (740058, "pol_r4_whole_part_system", "整体与部分的辩证关系及系统优化的方法", 2, SUBJECT, 740025),

    # 3.2 世界是永恒发展的
    (740059, "pol_r4_development_essence", "发展的实质与新事物必然战胜旧事物", 1, SUBJECT, 740026),
    (740060, "pol_r4_quantitative_qualitative", "量变与质变的辩证关系及其方法论", 2, SUBJECT, 740026),
    (740061, "pol_r4_forward_tortuous", "事物发展是前进性与曲折性的统一", 3, SUBJECT, 740026),

    # 3.3 唯物辩证法的实质与核心
    (740062, "pol_r4_contradiction_identity", "矛盾的含义、基本属性与同一性斗争性的关系", 1, SUBJECT, 740027),
    (740063, "pol_r4_contradiction_universal_particular", "矛盾的普遍性与特殊性及其辩证关系", 2, SUBJECT, 740027),
    (740064, "pol_r4_principal_contradiction_method", "主要矛盾与次要矛盾、矛盾主要方面与次要方面及矛盾分析法", 3, SUBJECT, 740027),

    # 4.1 人的认识从何而来
    (740065, "pol_r4_practice_connotation", "实践的含义、特征与基本形式", 1, SUBJECT, 740028),
    (740066, "pol_r4_practice_basis", "实践是认识的基础：来源、动力、检验标准与目的", 2, SUBJECT, 740028),

    # 4.2 在实践中追求和发展真理
    (740067, "pol_r4_truth_objectivity", "真理的客观性、具体性与条件性", 1, SUBJECT, 740029),
    (740068, "pol_r4_truth_fallacy", "真理与谬误的辩证关系及真理的检验标准", 2, SUBJECT, 740029),
    (740069, "pol_r4_knowledge_process", "认识的反复性、无限性与在实践中追求和发展真理", 3, SUBJECT, 740029),

    # 5.1 社会历史的本质
    (740070, "pol_r4_social_being_consciousness", "社会存在与社会意识的辩证关系", 1, SUBJECT, 740030),
    (740071, "pol_r4_social_consciousness_independence", "社会意识的相对独立性及其表现", 2, SUBJECT, 740030),

    # 5.2 社会历史的发展
    (740072, "pol_r4_productive_forces_relations", "生产力与生产关系的矛盾运动", 1, SUBJECT, 740031),
    (740073, "pol_r4_economic_base_superstructure", "经济基础与上层建筑的矛盾运动", 2, SUBJECT, 740031),
    (740074, "pol_r4_history_trend_reform", "社会历史发展的总趋势、改革与阶级社会的演进", 3, SUBJECT, 740031),

    # 5.3 社会历史的主体
    (740075, "pol_r4_masses_create_history", "人民群众是历史的创造者", 1, SUBJECT, 740032),
    (740076, "pol_r4_mass_view_line", "群众观点与群众路线", 2, SUBJECT, 740032),

    # 6.1 价值与价值观
    (740077, "pol_r4_value_human_value", "哲学意义上的价值与人的价值", 1, SUBJECT, 740033),
    (740078, "pol_r4_values_guidance", "价值观的导向作用", 2, SUBJECT, 740033),

    # 6.2 价值判断与价值选择
    (740079, "pol_r4_value_judgment_basis", "价值判断与价值选择的客观依据与社会历史性", 1, SUBJECT, 740034),
    (740080, "pol_r4_people_standpoint", "自觉遵循社会发展规律、站在最广大人民立场", 2, SUBJECT, 740034),

    # 6.3 价值的创造和实现
    (740081, "pol_r4_create_value_labor", "在劳动和奉献中创造价值", 1, SUBJECT, 740035),
    (740082, "pol_r4_realize_value_self", "在个人与社会的统一中实现价值、在砥砺自我中走向成功", 2, SUBJECT, 740035),

    # 7.1 文化的内涵与功能
    (740083, "pol_r4_culture_connotation", "文化的内涵、载体与本质", 1, SUBJECT, 740036),
    (740084, "pol_r4_culture_function", "文化的功能：引领风尚、教育人民、服务社会、推动发展", 2, SUBJECT, 740036),

    # 7.2 正确认识中华传统文化
    (740085, "pol_r4_traditional_content", "中华优秀传统文化的主要内容与特点", 1, SUBJECT, 740037),
    (740086, "pol_r4_traditional_value_innovation", "中华优秀传统文化的当代价值与创造性转化、创新性发展", 2, SUBJECT, 740037),

    # 7.3 弘扬中华优秀传统文化与民族精神
    (740087, "pol_r4_national_spirit_content", "中华民族精神的基本内涵与时代特征", 1, SUBJECT, 740038),
    (740088, "pol_r4_national_spirit_promote", "弘扬中华民族精神的意义与要求", 2, SUBJECT, 740038),

    # 8.1 文化的民族性与多样性
    (740089, "pol_r4_national_world_culture", "文化的民族性与世界性", 1, SUBJECT, 740039),
    (740090, "pol_r4_cultural_diversity", "文化多样性的表现与尊重文化多样性的原则", 2, SUBJECT, 740039),

    # 8.2 文化交流与文化交融
    (740091, "pol_r4_cultural_exchange", "文化交流互鉴的意义与正确态度", 1, SUBJECT, 740040),
    (740092, "pol_r4_cultural_blending_innovation", "文化交融与文化创新的关系", 2, SUBJECT, 740040),

    # 8.3 正确对待外来文化
    (740093, "pol_r4_foreign_culture_attitude", "正确对待外来文化：面向世界、博采众长、以我为主为我所用", 1, SUBJECT, 740041),

    # 9.1 文化发展的必然选择
    (740094, "pol_r4_culture_path_necessity", "文化发展道路的历史必然性与中国特色社会主义文化", 1, SUBJECT, 740042),

    # 9.2 文化发展的基本路径
    (740095, "pol_r4_culture_path_basic", "文化发展的基本路径：立足时代、人民立场、融通资源", 1, SUBJECT, 740043),
    (740096, "pol_r4_marxism_ideology", "坚持马克思主义在意识形态领域指导地位", 2, SUBJECT, 740043),
    (740097, "pol_r4_core_values", "培育和践行社会主义核心价值观", 3, SUBJECT, 740043),

    # 9.3 文化强国与文化自信
    (740098, "pol_r4_culture_power_tasks", "建设文化强国的主要任务", 1, SUBJECT, 740044),
    (740099, "pol_r4_culture_confidence", "坚定文化自信与增强中华文明传播力影响力", 2, SUBJECT, 740044),
)

"""统编版（2019）高中思想政治选择性必修第三册（逻辑与思维）：课框目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G10 = 10
BOOK_ID = 7107

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中思想政治选择性必修第三册（逻辑与思维）",
    "pol_e3",
    7,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (770101, "第一单元 树立科学思维观念", "pol_e3_u01", 1, BOOK_ID, None),
    (770102, "第二单元 遵循逻辑思维规则", "pol_e3_u02", 2, BOOK_ID, None),
    (770103, "第三单元 运用辩证思维方法", "pol_e3_u03", 3, BOOK_ID, None),
    (770104, "第四单元 提高创新思维能力", "pol_e3_u04", 4, BOOK_ID, None),
    (770111, "第一课 走进思维世界", "pol_e3_l01", 1, BOOK_ID, 770101),
    (770112, "第二课 把握逻辑要义", "pol_e3_l02", 2, BOOK_ID, 770101),
    (770113, "第三课 领会科学思维", "pol_e3_l03", 3, BOOK_ID, 770101),
    (770114, "第四课 准确把握概念", "pol_e3_l04", 1, BOOK_ID, 770102),
    (770115, "第五课 正确运用判断", "pol_e3_l05", 2, BOOK_ID, 770102),
    (770116, "第六课 掌握演绎推理方法", "pol_e3_l06", 3, BOOK_ID, 770102),
    (770117, "第七课 学会归纳与类比推理", "pol_e3_l07", 4, BOOK_ID, 770102),
    (770118, "第八课 把握辩证分合", "pol_e3_l08", 1, BOOK_ID, 770103),
    (770119, "第九课 理解质量互变", "pol_e3_l09", 2, BOOK_ID, 770103),
    (770120, "第十课 推动认识发展", "pol_e3_l10", 3, BOOK_ID, 770103),
    (770121, "第十一课 创新思维要善于联想", "pol_e3_l11", 1, BOOK_ID, 770104),
    (770122, "第十二课 创新思维要多路探索", "pol_e3_l12", 2, BOOK_ID, 770104),
    (770123, "第十三课 创新思维要力求超前", "pol_e3_l13", 3, BOOK_ID, 770104),
    (770131, "第一框 思维的含义与特征", "pol_e3_l01_s01", 1, BOOK_ID, 770111),
    (770132, "第二框 思维形态及其特征", "pol_e3_l01_s02", 2, BOOK_ID, 770111),
    (770133, "第一框 “逻辑”的多种含义", "pol_e3_l02_s01", 1, BOOK_ID, 770112),
    (770134, "第二框 逻辑思维的基本要求", "pol_e3_l02_s02", 2, BOOK_ID, 770112),
    (770135, "第一框 科学思维的含义与特征", "pol_e3_l03_s01", 1, BOOK_ID, 770113),
    (770136, "第二框 学习科学思维的意义", "pol_e3_l03_s02", 2, BOOK_ID, 770113),
    (770137, "第一框 概念的概述", "pol_e3_l04_s01", 1, BOOK_ID, 770114),
    (770138, "第二框 明确概念的方法", "pol_e3_l04_s02", 2, BOOK_ID, 770114),
    (770139, "第一框 判断的概述", "pol_e3_l05_s01", 1, BOOK_ID, 770115),
    (770140, "第二框 正确运用简单判断", "pol_e3_l05_s02", 2, BOOK_ID, 770115),
    (770141, "第三框 正确运用复合判断", "pol_e3_l05_s03", 3, BOOK_ID, 770115),
    (770142, "第一框 推理与演绎推理概述", "pol_e3_l06_s01", 1, BOOK_ID, 770116),
    (770143, "第二框 简单判断的演绎推理方法", "pol_e3_l06_s02", 2, BOOK_ID, 770116),
    (770144, "第三框 复合判断的演绎推理方法", "pol_e3_l06_s03", 3, BOOK_ID, 770116),
    (770145, "第一框 归纳推理及其方法", "pol_e3_l07_s01", 1, BOOK_ID, 770117),
    (770146, "第二框 类比推理及其方法", "pol_e3_l07_s02", 2, BOOK_ID, 770117),
    (770147, "第一框 辩证思维的含义与特征", "pol_e3_l08_s01", 1, BOOK_ID, 770118),
    (770148, "第二框 分析与综合及其辩证关系", "pol_e3_l08_s02", 2, BOOK_ID, 770118),
    (770149, "第一框 认识质量互变规律", "pol_e3_l09_s01", 1, BOOK_ID, 770119),
    (770150, "第二框 把握适度原则", "pol_e3_l09_s02", 2, BOOK_ID, 770119),
    (770151, "第一框 不作简单肯定或否定", "pol_e3_l10_s01", 1, BOOK_ID, 770120),
    (770152, "第二框 体会认识发展的历程", "pol_e3_l10_s02", 2, BOOK_ID, 770120),
    (770153, "第一框 创新思维的含义与特征", "pol_e3_l11_s01", 1, BOOK_ID, 770121),
    (770154, "第二框 联想思维的含义与方法", "pol_e3_l11_s02", 2, BOOK_ID, 770121),
    (770155, "第一框 发散思维与聚合思维的方法", "pol_e3_l12_s01", 1, BOOK_ID, 770122),
    (770156, "第二框 逆向思维的含义与作用", "pol_e3_l12_s02", 2, BOOK_ID, 770122),
    (770157, "第一框 超前思维的含义与特征", "pol_e3_l13_s01", 1, BOOK_ID, 770123),
    (770158, "第二框 超前思维的方法与意义", "pol_e3_l13_s02", 2, BOOK_ID, 770123),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (770001, "pol_e3_domain_scientific_thinking", "科学思维观念：思维、逻辑与科学思维", 1, SUBJECT, None),
    (770002, "pol_e3_domain_logic_rules", "逻辑思维规则：概念、判断与推理", 2, SUBJECT, None),
    (770003, "pol_e3_domain_dialectical_thinking", "辩证思维方法：分合、质量互变与认识发展", 3, SUBJECT, None),
    (770004, "pol_e3_domain_innovative_thinking", "创新思维能力：联想、多路与超前思维", 4, SUBJECT, None),

    # 单元域层
    (770005, "pol_e3_unit01", "第一单元 树立科学思维观念", 1, SUBJECT, 770001),
    (770006, "pol_e3_unit02", "第二单元 遵循逻辑思维规则", 1, SUBJECT, 770002),
    (770007, "pol_e3_unit03", "第三单元 运用辩证思维方法", 1, SUBJECT, 770003),
    (770008, "pol_e3_unit04", "第四单元 提高创新思维能力", 1, SUBJECT, 770004),

    # 课域层
    (770009, "pol_e3_lesson01", "第一课 走进思维世界", 1, SUBJECT, 770005),
    (770010, "pol_e3_lesson02", "第二课 把握逻辑要义", 2, SUBJECT, 770005),
    (770011, "pol_e3_lesson03", "第三课 领会科学思维", 3, SUBJECT, 770005),
    (770012, "pol_e3_lesson04", "第四课 准确把握概念", 1, SUBJECT, 770006),
    (770013, "pol_e3_lesson05", "第五课 正确运用判断", 2, SUBJECT, 770006),
    (770014, "pol_e3_lesson06", "第六课 掌握演绎推理方法", 3, SUBJECT, 770006),
    (770015, "pol_e3_lesson07", "第七课 学会归纳与类比推理", 4, SUBJECT, 770006),
    (770016, "pol_e3_lesson08", "第八课 把握辩证分合", 1, SUBJECT, 770007),
    (770017, "pol_e3_lesson09", "第九课 理解质量互变", 2, SUBJECT, 770007),
    (770018, "pol_e3_lesson10", "第十课 推动认识发展", 3, SUBJECT, 770007),
    (770019, "pol_e3_lesson11", "第十一课 创新思维要善于联想", 1, SUBJECT, 770008),
    (770020, "pol_e3_lesson12", "第十二课 创新思维要多路探索", 2, SUBJECT, 770008),
    (770021, "pol_e3_lesson13", "第十三课 创新思维要力求超前", 3, SUBJECT, 770008),

    # 框域层
    (770022, "pol_e3_sec_thinking_meaning", "第一框 思维的含义与特征", 1, SUBJECT, 770009),
    (770023, "pol_e3_sec_thinking_forms", "第二框 思维形态及其特征", 2, SUBJECT, 770009),
    (770024, "pol_e3_sec_logic_meanings", "第一框 “逻辑”的多种含义", 1, SUBJECT, 770010),
    (770025, "pol_e3_sec_logic_requirements", "第二框 逻辑思维的基本要求", 2, SUBJECT, 770010),
    (770026, "pol_e3_sec_scientific_thinking", "第一框 科学思维的含义与特征", 1, SUBJECT, 770011),
    (770027, "pol_e3_sec_scientific_thinking_value", "第二框 学习科学思维的意义", 2, SUBJECT, 770011),
    (770028, "pol_e3_sec_concept_overview", "第一框 概念的概述", 1, SUBJECT, 770012),
    (770029, "pol_e3_sec_concept_clarification", "第二框 明确概念的方法", 2, SUBJECT, 770012),
    (770030, "pol_e3_sec_judgment_overview", "第一框 判断的概述", 1, SUBJECT, 770013),
    (770031, "pol_e3_sec_simple_judgment", "第二框 正确运用简单判断", 2, SUBJECT, 770013),
    (770032, "pol_e3_sec_compound_judgment", "第三框 正确运用复合判断", 3, SUBJECT, 770013),
    (770033, "pol_e3_sec_inference_overview", "第一框 推理与演绎推理概述", 1, SUBJECT, 770014),
    (770034, "pol_e3_sec_simple_inference", "第二框 简单判断的演绎推理方法", 2, SUBJECT, 770014),
    (770035, "pol_e3_sec_compound_inference", "第三框 复合判断的演绎推理方法", 3, SUBJECT, 770014),
    (770036, "pol_e3_sec_induction", "第一框 归纳推理及其方法", 1, SUBJECT, 770015),
    (770037, "pol_e3_sec_analogy", "第二框 类比推理及其方法", 2, SUBJECT, 770015),
    (770038, "pol_e3_sec_dialectical_thinking", "第一框 辩证思维的含义与特征", 1, SUBJECT, 770016),
    (770039, "pol_e3_sec_analysis_synthesis", "第二框 分析与综合及其辩证关系", 2, SUBJECT, 770016),
    (770040, "pol_e3_sec_mass_interchange", "第一框 认识质量互变规律", 1, SUBJECT, 770017),
    (770041, "pol_e3_sec_moderation", "第二框 把握适度原则", 2, SUBJECT, 770017),
    (770042, "pol_e3_sec_dialectical_negation", "第一框 不作简单肯定或否定", 1, SUBJECT, 770018),
    (770043, "pol_e3_sec_cognitive_development", "第二框 体会认识发展的历程", 2, SUBJECT, 770018),
    (770044, "pol_e3_sec_innovative_thinking", "第一框 创新思维的含义与特征", 1, SUBJECT, 770019),
    (770045, "pol_e3_sec_association", "第二框 联想思维的含义与方法", 2, SUBJECT, 770019),
    (770046, "pol_e3_sec_divergent_convergent", "第一框 发散思维与聚合思维的方法", 1, SUBJECT, 770020),
    (770047, "pol_e3_sec_reverse_thinking", "第二框 逆向思维的含义与作用", 2, SUBJECT, 770020),
    (770048, "pol_e3_sec_forward_thinking", "第一框 超前思维的含义与特征", 1, SUBJECT, 770021),
    (770049, "pol_e3_sec_forward_methods", "第二框 超前思维的方法与意义", 2, SUBJECT, 770021),

    # 1.1 思维的含义与特征
    (770050, "pol_e3_thinking_meaning", "思维的含义：人脑对客观事物的间接、概括的反映", 1, SUBJECT, 770022),
    (770051, "pol_e3_thinking_features", "思维的特征：间接性、概括性与能动性", 2, SUBJECT, 770022),
    (770052, "pol_e3_thinking_practice", "思维与实践的关系：实践是思维的基础和检验标准", 3, SUBJECT, 770022),

    # 1.2 思维形态及其特征
    (770053, "pol_e3_thinking_forms", "思维形态的分类标准与主要类型", 1, SUBJECT, 770023),
    (770054, "pol_e3_abstract_image_thinking", "抽象思维与形象思维的特征、区别与联系", 2, SUBJECT, 770023),

    # 2.1 “逻辑”的多种含义
    (770055, "pol_e3_logic_meanings", "“逻辑”的多重含义与逻辑学的研究对象", 1, SUBJECT, 770024),

    # 2.2 逻辑思维的基本要求
    (770056, "pol_e3_logic_laws", "同一律、矛盾律与排中律的基本内容", 1, SUBJECT, 770025),
    (770057, "pol_e3_logic_requirements", "逻辑思维的基本要求：确定性、一致性与明确性", 2, SUBJECT, 770025),

    # 3.1 科学思维的含义与特征
    (770058, "pol_e3_scientific_thinking", "科学思维的含义与追求真理、实事求是等特征", 1, SUBJECT, 770026),

    # 3.2 学习科学思维的意义
    (770059, "pol_e3_scientific_thinking_value", "学习科学思维对思维品质与认识能力的意义", 1, SUBJECT, 770027),

    # 4.1 概念的概述
    (770060, "pol_e3_concept_meaning", "概念的含义：反映事物本质属性的思维形式", 1, SUBJECT, 770028),
    (770061, "pol_e3_concept_intension_extension", "概念的基本特征：内涵与外延及其反变关系", 2, SUBJECT, 770028),

    # 4.2 明确概念的方法
    (770062, "pol_e3_definition", "定义的方法：种差加属概念与定义规则", 1, SUBJECT, 770029),
    (770063, "pol_e3_division", "划分的方法与规则：母项、子项与划分标准", 2, SUBJECT, 770029),

    # 5.1 判断的概述
    (770064, "pol_e3_judgment_overview", "判断的含义、基本特征与类型", 1, SUBJECT, 770030),

    # 5.2 正确运用简单判断
    (770065, "pol_e3_categorical_judgment", "性质判断的类型、主谓项周延性与真假", 1, SUBJECT, 770031),
    (770066, "pol_e3_relational_judgment", "关系判断：对称性、传递性与关系性质", 2, SUBJECT, 770031),

    # 5.3 正确运用复合判断
    (770067, "pol_e3_conjunctive_disjunctive", "联言判断与选言判断的结构及真值条件", 1, SUBJECT, 770032),
    (770068, "pol_e3_hypothetical_judgment", "假言判断：充分条件、必要条件与充要条件", 2, SUBJECT, 770032),

    # 6.1 推理与演绎推理概述
    (770069, "pol_e3_inference_overview", "推理的含义、结构、分类与演绎推理的有效性", 1, SUBJECT, 770033),
    (770070, "pol_e3_inference_types", "演绎推理与归纳推理、类比推理的区别", 2, SUBJECT, 770033),

    # 6.2 简单判断的演绎推理方法
    (770071, "pol_e3_obversion_conversion", "性质判断的换质推理、换位推理与变形推理", 1, SUBJECT, 770034),
    (770072, "pol_e3_syllogism_rules", "三段论的结构、一般规则与常见逻辑错误", 2, SUBJECT, 770034),
    (770073, "pol_e3_syllogism_figures", "三段论的格与式及其有效推理形式", 3, SUBJECT, 770034),

    # 6.3 复合判断的演绎推理方法
    (770074, "pol_e3_compound_inference", "联言推理与选言推理的有效式", 1, SUBJECT, 770035),
    (770075, "pol_e3_conditional_inference", "假言推理规则：肯定前件式与否定后件式", 2, SUBJECT, 770035),

    # 7.1 归纳推理及其方法
    (770076, "pol_e3_induction_types", "完全归纳推理与不完全归纳推理", 1, SUBJECT, 770036),
    (770077, "pol_e3_causal_methods", "探求因果联系的方法：求同法、求异法与共变法", 2, SUBJECT, 770036),

    # 7.2 类比推理及其方法
    (770078, "pol_e3_analogy", "类比推理的含义、方法、作用与局限性", 1, SUBJECT, 770037),

    # 8.1 辩证思维的含义与特征
    (770079, "pol_e3_dialectical_meaning", "辩证思维的含义及其客观基础", 1, SUBJECT, 770038),
    (770080, "pol_e3_dialectical_features", "辩证思维的整体性与动态性特征", 2, SUBJECT, 770038),

    # 8.2 分析与综合及其辩证关系
    (770081, "pol_e3_analysis_synthesis", "分析的方法与综合的方法", 1, SUBJECT, 770039),
    (770082, "pol_e3_analysis_synthesis_relation", "分析与综合的辩证关系及其实际运用", 2, SUBJECT, 770039),

    # 9.1 认识质量互变规律
    (770083, "pol_e3_quantitative_qualitative", "量变与质变的含义及辩证关系", 1, SUBJECT, 770040),
    (770084, "pol_e3_mass_interchange_law", "质量互变规律的普遍性与方法论意义", 2, SUBJECT, 770040),

    # 9.2 把握适度原则
    (770085, "pol_e3_moderation", "适度原则：把握分寸、防止过犹不及", 1, SUBJECT, 770041),

    # 10.1 不作简单肯定或否定
    (770086, "pol_e3_dialectical_negation", "辩证否定观：扬弃与不作简单肯定或否定", 1, SUBJECT, 770042),

    # 10.2 体会认识发展的历程
    (770087, "pol_e3_cognitive_development", "认识发展：从感性具体到思维抽象再到思维具体", 1, SUBJECT, 770043),

    # 11.1 创新思维的含义与特征
    (770088, "pol_e3_innovative_thinking", "创新思维的含义、特征与基本路径", 1, SUBJECT, 770044),

    # 11.2 联想思维的含义与方法
    (770089, "pol_e3_associative_thinking", "联想思维的含义、特点与类型", 1, SUBJECT, 770045),
    (770090, "pol_e3_association_methods", "联想思维的方法：迁移、想象与幻想", 2, SUBJECT, 770045),

    # 12.1 发散思维与聚合思维的方法
    (770091, "pol_e3_divergent_thinking", "发散思维的方法：头脑风暴、检核表与信息交合", 1, SUBJECT, 770046),
    (770092, "pol_e3_convergent_thinking", "聚合思维的方法及其与发散思维的结合", 2, SUBJECT, 770046),

    # 12.2 逆向思维的含义与作用
    (770093, "pol_e3_reverse_thinking", "逆向思维的含义、方法（反其道而行之）与作用", 1, SUBJECT, 770047),

    # 13.1 超前思维的含义与特征
    (770094, "pol_e3_forward_thinking", "超前思维的含义、特征与预测方法", 1, SUBJECT, 770048),

    # 13.2 超前思维的方法与意义
    (770095, "pol_e3_forward_methods", "超前思维的方法与意义：调查研究、矛盾分析", 1, SUBJECT, 770049),
)

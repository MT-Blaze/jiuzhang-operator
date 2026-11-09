"""统编版（2019）高中思想政治必修第二册（经济与社会）：课框目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G10 = 10
BOOK_ID = 7102

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中思想政治必修第二册（经济与社会）",
    "pol_r2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (720101, "第一单元 生产资料所有制与经济体制", "pol_r2_u01", 1, BOOK_ID, None),
    (720102, "第二单元 经济发展与社会进步", "pol_r2_u02", 2, BOOK_ID, None),
    (720111, "第一课 我国的生产资料所有制", "pol_r2_lesson01", 1, BOOK_ID, 720101),
    (720112, "第二课 我国的社会主义市场经济体制", "pol_r2_lesson02", 2, BOOK_ID, 720101),
    (720113, "第三课 我国的经济发展", "pol_r2_lesson03", 1, BOOK_ID, 720102),
    (720114, "第四课 我国的个人收入分配与社会保障", "pol_r2_lesson04", 2, BOOK_ID, 720102),
    (720121, "第一框 公有制为主体 多种所有制经济共同发展", "pol_r2_lesson01_s01", 1, BOOK_ID, 720111),
    (720122, "第二框 坚持“两个毫不动摇”", "pol_r2_lesson01_s02", 2, BOOK_ID, 720111),
    (720123, "第一框 使市场在资源配置中起决定性作用", "pol_r2_lesson02_s01", 1, BOOK_ID, 720112),
    (720124, "第二框 更好发挥政府作用", "pol_r2_lesson02_s02", 2, BOOK_ID, 720112),
    (720125, "第一框 贯彻新发展理念", "pol_r2_lesson03_s01", 1, BOOK_ID, 720113),
    (720126, "第二框 推动高质量发展", "pol_r2_lesson03_s02", 2, BOOK_ID, 720113),
    (720127, "第一框 我国的个人收入分配", "pol_r2_lesson04_s01", 1, BOOK_ID, 720114),
    (720128, "第二框 我国的社会保障", "pol_r2_lesson04_s02", 2, BOOK_ID, 720114),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (720001, "pol_r2_domain_ownership_market", "生产资料所有制与社会主义市场经济体制", 1, SUBJECT, G10, None),
    (720002, "pol_r2_domain_development_livelihood", "经济发展与收入分配社会保障", 2, SUBJECT, G10, None),

    # 单元域层
    (720003, "pol_r2_unit01", "第一单元 生产资料所有制与经济体制", 1, SUBJECT, G10, 720001),
    (720004, "pol_r2_unit02", "第二单元 经济发展与社会进步", 1, SUBJECT, G10, 720002),

    # 课域层
    (720005, "pol_r2_lesson01", "第一课 我国的生产资料所有制", 1, SUBJECT, G10, 720003),
    (720006, "pol_r2_lesson02", "第二课 我国的社会主义市场经济体制", 2, SUBJECT, G10, 720003),
    (720007, "pol_r2_lesson03", "第三课 我国的经济发展", 1, SUBJECT, G10, 720004),
    (720008, "pol_r2_lesson04", "第四课 我国的个人收入分配与社会保障", 2, SUBJECT, G10, 720004),

    # 框域层
    (720009, "pol_r2_sec_public_ownership", "第一框 公有制为主体 多种所有制经济共同发展", 1, SUBJECT, G10, 720005),
    (720010, "pol_r2_sec_two_unshakable", "第二框 坚持“两个毫不动摇”", 2, SUBJECT, G10, 720005),
    (720011, "pol_r2_sec_market_decisive", "第一框 使市场在资源配置中起决定性作用", 1, SUBJECT, G10, 720006),
    (720012, "pol_r2_sec_government_role", "第二框 更好发挥政府作用", 2, SUBJECT, G10, 720006),
    (720013, "pol_r2_sec_new_philosophy", "第一框 贯彻新发展理念", 1, SUBJECT, G10, 720007),
    (720014, "pol_r2_sec_high_quality", "第二框 推动高质量发展", 2, SUBJECT, G10, 720007),
    (720015, "pol_r2_sec_income_distribution", "第一框 我国的个人收入分配", 1, SUBJECT, G10, 720008),
    (720016, "pol_r2_sec_social_security", "第二框 我国的社会保障", 2, SUBJECT, G10, 720008),

    # 1.1 公有制为主体 多种所有制经济共同发展
    (720017, "pol_r2_basic_economic_system", "我国基本经济制度的内涵与确立依据", 1, SUBJECT, G10, 720009),
    (720018, "pol_r2_ownership_status", "生产资料所有制的地位与作用", 2, SUBJECT, G10, 720009),
    (720019, "pol_r2_public_ownership_scope", "公有制经济的构成与实现形式", 3, SUBJECT, G10, 720009),
    (720020, "pol_r2_public_ownership_dominant", "公有制主体地位的体现", 4, SUBJECT, G10, 720009),
    (720021, "pol_r2_soe_leading_role", "国有经济的主导作用及其体现", 5, SUBJECT, G10, 720009),
    (720022, "pol_r2_collective_economy", "集体经济的地位、形式与作用", 6, SUBJECT, G10, 720009),
    (720023, "pol_r2_non_public_scope", "非公有制经济的构成与主要形式", 7, SUBJECT, G10, 720009),
    (720024, "pol_r2_non_public_status", "非公有制经济的地位与作用", 8, SUBJECT, G10, 720009),
    (720025, "pol_r2_ownership_relationship", "公有制经济与非公有制经济的辩证关系", 9, SUBJECT, G10, 720009),
    (720026, "pol_r2_basic_system_necessity", "坚持我国基本经济制度的必然性", 10, SUBJECT, G10, 720009),

    # 1.2 坚持“两个毫不动摇”
    (720027, "pol_r2_consolidate_public_ownership", "毫不动摇巩固和发展公有制经济", 1, SUBJECT, G10, 720010),
    (720028, "pol_r2_soe_reform", "深化国有企业改革与做强做优做大国有资本", 2, SUBJECT, G10, 720010),
    (720029, "pol_r2_soe_layout", "推进国有经济布局优化和结构调整", 3, SUBJECT, G10, 720010),
    (720030, "pol_r2_mixed_ownership", "积极发展混合所有制经济", 4, SUBJECT, G10, 720010),
    (720031, "pol_r2_rural_collective_reform", "农村集体经济与农村土地制度改革", 5, SUBJECT, G10, 720010),
    (720032, "pol_r2_encourage_non_public", "毫不动摇鼓励、支持、引导非公有制经济发展", 6, SUBJECT, G10, 720010),
    (720033, "pol_r2_private_business_environment", "优化民营企业发展环境与产权保护", 7, SUBJECT, G10, 720010),
    (720034, "pol_r2_clean_government_business", "构建亲清政商关系", 8, SUBJECT, G10, 720010),
    (720035, "pol_r2_entrepreneur_spirit", "弘扬企业家精神", 9, SUBJECT, G10, 720010),
    (720036, "pol_r2_non_public_healthy_growth", "促进非公有制经济健康发展和非公有制经济人士健康成长", 10, SUBJECT, G10, 720010),

    # 2.1 使市场在资源配置中起决定性作用
    (720037, "pol_r2_resource_allocation_means", "资源配置的基本手段与市场经济", 1, SUBJECT, G10, 720011),
    (720038, "pol_r2_market_mechanism", "市场配置资源的机制：价格、供求与竞争", 2, SUBJECT, G10, 720011),
    (720039, "pol_r2_market_advantages", "市场调节的优点与有效性", 3, SUBJECT, G10, 720011),
    (720040, "pol_r2_unified_market", "市场体系的构成与全国统一大市场建设", 4, SUBJECT, G10, 720011),
    (720041, "pol_r2_market_rules_order", "市场规则与市场秩序", 5, SUBJECT, G10, 720011),
    (720042, "pol_r2_market_limitations", "市场调节的局限性：自发性、盲目性、滞后性", 6, SUBJECT, G10, 720011),
    (720043, "pol_r2_market_failure", "市场失灵的主要表现", 7, SUBJECT, G10, 720011),
    (720044, "pol_r2_credit_system", "社会信用体系与诚信建设", 8, SUBJECT, G10, 720011),

    # 2.2 更好发挥政府作用
    (720045, "pol_r2_socialist_market_features", "社会主义市场经济体制的基本特征", 1, SUBJECT, G10, 720012),
    (720046, "pol_r2_government_economic_functions", "政府的经济职能", 2, SUBJECT, G10, 720012),
    (720047, "pol_r2_macro_control_targets", "宏观调控的主要目标", 3, SUBJECT, G10, 720012),
    (720048, "pol_r2_fiscal_policy", "财政政策的作用与工具", 4, SUBJECT, G10, 720012),
    (720049, "pol_r2_monetary_policy", "货币政策的作用与工具", 5, SUBJECT, G10, 720012),
    (720050, "pol_r2_macro_control_means", "宏观调控的手段及其配合", 6, SUBJECT, G10, 720012),
    (720051, "pol_r2_effective_market_government", "有效市场与有为政府更好结合", 7, SUBJECT, G10, 720012),
    (720052, "pol_r2_socialist_market_advantages", "社会主义市场经济体制的显著优势", 8, SUBJECT, G10, 720012),

    # 3.1 贯彻新发展理念
    (720053, "pol_r2_people_centered_development", "以人民为中心的发展思想", 1, SUBJECT, G10, 720013),
    (720054, "pol_r2_new_philosophy_holistic", "新发展理念的提出背景与整体性", 2, SUBJECT, G10, 720013),
    (720055, "pol_r2_innovation_development", "创新是引领发展的第一动力", 3, SUBJECT, G10, 720013),
    (720056, "pol_r2_coordinated_development", "协调是持续健康发展的内在要求", 4, SUBJECT, G10, 720013),
    (720057, "pol_r2_green_development", "绿色是永续发展的必要条件", 5, SUBJECT, G10, 720013),
    (720058, "pol_r2_open_development", "开放是国家繁荣发展的必由之路", 6, SUBJECT, G10, 720013),
    (720059, "pol_r2_shared_development", "共享是中国特色社会主义的本质要求", 7, SUBJECT, G10, 720013),
    (720060, "pol_r2_new_philosophy_practice", "新发展理念的内在联系与实践要求", 8, SUBJECT, G10, 720013),

    # 3.2 推动高质量发展
    (720061, "pol_r2_high_quality_connotation", "高质量发展的内涵与必然要求", 1, SUBJECT, G10, 720014),
    (720062, "pol_r2_modern_economic_system", "现代化经济体系的构成", 2, SUBJECT, G10, 720014),
    (720063, "pol_r2_real_economy", "实体经济是经济发展的立身之本", 3, SUBJECT, G10, 720014),
    (720064, "pol_r2_innovation_driven", "实施创新驱动发展战略与科技自立自强", 4, SUBJECT, G10, 720014),
    (720065, "pol_r2_rural_revitalization", "全面推进乡村振兴与城乡融合发展", 5, SUBJECT, G10, 720014),
    (720066, "pol_r2_regional_coordination", "区域协调发展战略", 6, SUBJECT, G10, 720014),
    (720067, "pol_r2_modern_industrial_system", "建设现代化产业体系", 7, SUBJECT, G10, 720014),
    (720068, "pol_r2_new_development_pattern", "构建以国内大循环为主体的新发展格局", 8, SUBJECT, G10, 720014),

    # 4.1 我国的个人收入分配
    (720069, "pol_r2_income_distribution_system", "我国个人收入分配制度", 1, SUBJECT, G10, 720015),
    (720070, "pol_r2_distribution_by_labor", "按劳分配的地位、内容与实行原因", 2, SUBJECT, G10, 720015),
    (720071, "pol_r2_factor_distribution", "按生产要素分配及其具体形式", 3, SUBJECT, G10, 720015),
    (720072, "pol_r2_resident_income_sources", "居民收入的四种来源", 4, SUBJECT, G10, 720015),
    (720073, "pol_r2_three_distributions", "初次分配、再分配与第三次分配", 5, SUBJECT, G10, 720015),
    (720074, "pol_r2_efficiency_fairness", "效率与公平的关系", 6, SUBJECT, G10, 720015),
    (720075, "pol_r2_income_order", "规范收入分配秩序与扩大中等收入群体", 7, SUBJECT, G10, 720015),
    (720076, "pol_r2_common_prosperity", "共同富裕的目标与实现路径", 8, SUBJECT, G10, 720015),

    # 4.2 我国的社会保障
    (720077, "pol_r2_social_security_function", "社会保障的功能与意义", 1, SUBJECT, G10, 720016),
    (720078, "pol_r2_social_insurance", "社会保险的构成与作用", 2, SUBJECT, G10, 720016),
    (720079, "pol_r2_social_assistance", "社会救助的对象与主要内容", 3, SUBJECT, G10, 720016),
    (720080, "pol_r2_social_welfare", "社会福利的内涵与项目", 4, SUBJECT, G10, 720016),
    (720081, "pol_r2_social_preference", "社会优抚的对象与内容", 5, SUBJECT, G10, 720016),
    (720082, "pol_r2_security_principles", "社会保障体系建设的基本原则", 6, SUBJECT, G10, 720016),
    (720083, "pol_r2_multi_level_security", "多层次社会保障体系", 7, SUBJECT, G10, 720016),
    (720084, "pol_r2_security_economy_match", "社会保障与经济社会发展水平相适应", 8, SUBJECT, G10, 720016),
)

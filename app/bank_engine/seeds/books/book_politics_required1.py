"""统编版（2019）高中思想政治必修第一册（中国特色社会主义）：课框目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G10 = 10
BOOK_ID = 7101

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中思想政治必修第一册（中国特色社会主义）",
    "pol_r1",
    1,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (710101, "第一课 社会主义从空想到科学、从理论到实践的发展", "pol_r1_ch01", 1, BOOK_ID, None),
    (710102, "第二课 只有社会主义才能救中国", "pol_r1_ch02", 2, BOOK_ID, None),
    (710103, "第三课 只有中国特色社会主义才能发展中国", "pol_r1_ch03", 3, BOOK_ID, None),
    (710104, "第四课 只有坚持和发展中国特色社会主义才能实现中华民族伟大复兴", "pol_r1_ch04", 4, BOOK_ID, None),
    (710111, "第一框 原始社会的解体和阶级社会的演进", "pol_r1_ch01_s01", 1, BOOK_ID, 710101),
    (710112, "第二框 科学社会主义的理论与实践", "pol_r1_ch01_s02", 2, BOOK_ID, 710101),
    (710121, "第一框 新民主主义革命的胜利", "pol_r1_ch02_s01", 1, BOOK_ID, 710102),
    (710122, "第二框 社会主义制度在中国的确立", "pol_r1_ch02_s02", 2, BOOK_ID, 710102),
    (710131, "第一框 伟大的改革开放", "pol_r1_ch03_s01", 1, BOOK_ID, 710103),
    (710132, "第二框 中国特色社会主义的创立、发展和完善", "pol_r1_ch03_s02", 2, BOOK_ID, 710103),
    (710141, "第一框 中国特色社会主义进入新时代", "pol_r1_ch04_s01", 1, BOOK_ID, 710104),
    (710142, "第二框 实现中华民族伟大复兴的中国梦", "pol_r1_ch04_s02", 2, BOOK_ID, 710104),
    (710143, "第三框 习近平新时代中国特色社会主义思想", "pol_r1_ch04_s03", 3, BOOK_ID, 710104),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (710001, "pol_r1_domain_human_society", "人类社会形态更替与发展规律", 1, SUBJECT, None),
    (710002, "pol_r1_domain_socialism_saves_china", "社会主义救中国的历史逻辑", 2, SUBJECT, None),
    (710003, "pol_r1_domain_socialism_develops_china", "中国特色社会主义的发展逻辑", 3, SUBJECT, None),
    (710004, "pol_r1_domain_national_rejuvenation", "新时代与中华民族伟大复兴", 4, SUBJECT, None),

    # 课域层
    (710005, "pol_r1_lesson01", "第一课 社会主义从空想到科学、从理论到实践的发展", 1, SUBJECT, 710001),
    (710006, "pol_r1_lesson02", "第二课 只有社会主义才能救中国", 1, SUBJECT, 710002),
    (710007, "pol_r1_lesson03", "第三课 只有中国特色社会主义才能发展中国", 1, SUBJECT, 710003),
    (710008, "pol_r1_lesson04", "第四课 只有坚持和发展中国特色社会主义才能实现中华民族伟大复兴", 1, SUBJECT, 710004),

    # 框域层
    (710009, "pol_r1_sec_primitive_class_society", "第一框 原始社会的解体和阶级社会的演进", 1, SUBJECT, 710005),
    (710010, "pol_r1_sec_scientific_socialism", "第二框 科学社会主义的理论与实践", 2, SUBJECT, 710005),
    (710011, "pol_r1_sec_new_democratic_revolution", "第一框 新民主主义革命的胜利", 1, SUBJECT, 710006),
    (710012, "pol_r1_sec_socialist_system_established", "第二框 社会主义制度在中国的确立", 2, SUBJECT, 710006),
    (710013, "pol_r1_sec_reform_opening", "第一框 伟大的改革开放", 1, SUBJECT, 710007),
    (710014, "pol_r1_sec_css_creation", "第二框 中国特色社会主义的创立、发展和完善", 2, SUBJECT, 710007),
    (710015, "pol_r1_sec_new_era", "第一框 中国特色社会主义进入新时代", 1, SUBJECT, 710008),
    (710016, "pol_r1_sec_chinese_dream", "第二框 实现中华民族伟大复兴的中国梦", 2, SUBJECT, 710008),
    (710017, "pol_r1_sec_xi_thought", "第三框 习近平新时代中国特色社会主义思想", 3, SUBJECT, 710008),

    # 1.1 原始社会的解体和阶级社会的演进
    (710018, "pol_r1_primitive_productivity_relations", "原始社会的生产力水平与生产关系特点", 1, SUBJECT, 710009),
    (710019, "pol_r1_primitive_disintegration", "原始社会解体的过程与私有制的产生", 2, SUBJECT, 710009),
    (710020, "pol_r1_slave_relations", "奴隶社会的生产关系与奴隶主阶级剥削", 3, SUBJECT, 710009),
    (710021, "pol_r1_slave_state_civilization", "奴隶制国家的产生与人类进入文明时代", 4, SUBJECT, 710009),
    (710022, "pol_r1_feudal_relations", "封建社会的生产关系与地主阶级剥削方式", 5, SUBJECT, 710009),
    (710023, "pol_r1_feudal_rule_revolt", "封建国家的专制统治与农民阶级的反抗", 6, SUBJECT, 710009),
    (710024, "pol_r1_capitalism_rise", "资本主义生产关系的产生与工业革命", 7, SUBJECT, 710009),
    (710025, "pol_r1_economic_crisis", "资本主义经济危机的基本特征与根源", 8, SUBJECT, 710009),
    (710026, "pol_r1_capitalism_basic_contradiction", "资本主义基本矛盾与社会主义代替资本主义的历史趋势", 9, SUBJECT, 710009),

    # 1.2 科学社会主义的理论与实践
    (710027, "pol_r1_utopian_socialism", "空想社会主义的产生、代表人物与历史局限", 1, SUBJECT, 710010),
    (710028, "pol_r1_scientific_socialism_conditions", "科学社会主义诞生的历史条件与阶级基础", 2, SUBJECT, 710010),
    (710029, "pol_r1_two_discoveries", "唯物史观和剩余价值学说的两大发现", 3, SUBJECT, 710010),
    (710030, "pol_r1_communist_manifesto", "《共产党宣言》的发表及其历史意义", 4, SUBJECT, 710010),
    (710031, "pol_r1_scientific_socialism_principles", "科学社会主义的基本原则与理论特质", 5, SUBJECT, 710010),
    (710032, "pol_r1_paris_commune", "巴黎公社的实践尝试与经验教训", 6, SUBJECT, 710010),
    (710033, "pol_r1_october_revolution", "十月革命的胜利与社会主义从一国到多国的发展", 7, SUBJECT, 710010),
    (710034, "pol_r1_socialism_road_twists", "社会主义发展道路的曲折性与光明前途", 8, SUBJECT, 710010),

    # 2.1 新民主主义革命的胜利
    (710035, "pol_r1_semi_colonial_society", "近代中国半殖民地半封建社会的基本国情", 1, SUBJECT, 710011),
    (710036, "pol_r1_modern_main_contradiction", "近代中国社会的主要矛盾与两大历史任务", 2, SUBJECT, 710011),
    (710037, "pol_r1_capitalist_road_fails", "资本主义道路在中国走不通的原因", 3, SUBJECT, 710011),
    (710038, "pol_r1_new_democratic_nature", "新民主主义革命的性质、对象与任务", 4, SUBJECT, 710011),
    (710039, "pol_r1_new_democratic_forces", "新民主主义革命的领导力量与依靠力量", 5, SUBJECT, 710011),
    (710040, "pol_r1_new_democratic_prospect", "新民主主义革命的前途与两步走战略", 6, SUBJECT, 710011),
    (710041, "pol_r1_cpc_founding", "中国共产党的成立及其对中国革命的深远影响", 7, SUBJECT, 710011),
    (710042, "pol_r1_three_magic_weapons", "新民主主义革命时期的统一战线、武装斗争与党的建设", 8, SUBJECT, 710011),
    (710043, "pol_r1_new_democratic_victory", "新民主主义革命胜利的标志与历史意义", 9, SUBJECT, 710011),
    (710044, "pol_r1_prc_founding", "中华人民共和国成立的重大意义", 10, SUBJECT, 710011),

    # 2.2 社会主义制度在中国的确立
    (710045, "pol_r1_transition_general_line", "从新民主主义向社会主义过渡的总路线", 1, SUBJECT, 710012),
    (710046, "pol_r1_socialist_transformation", "社会主义改造的完成与社会主义制度的确立", 2, SUBJECT, 710012),
    (710047, "pol_r1_socialist_system_significance", "社会主义基本制度确立的历史意义", 3, SUBJECT, 710012),
    (710048, "pol_r1_eighth_congress", "党的八大对社会主义建设道路的探索", 4, SUBJECT, 710012),
    (710049, "pol_r1_socialist_construction_achievements", "社会主义建设时期的成就与曲折历程", 5, SUBJECT, 710012),
    (710050, "pol_r1_only_socialism_saves_china", "只有社会主义才能救中国的历史结论", 6, SUBJECT, 710012),
    (710051, "pol_r1_construction_experience", "社会主义建设探索的宝贵经验与教训", 7, SUBJECT, 710012),

    # 3.1 伟大的改革开放
    (710052, "pol_r1_third_plenary_session", "党的十一届三中全会与伟大历史转折", 1, SUBJECT, 710013),
    (710053, "pol_r1_rural_reform", "农村改革与家庭联产承包责任制", 2, SUBJECT, 710013),
    (710054, "pol_r1_urban_reform", "城市经济体制改革与国有企业改革", 3, SUBJECT, 710013),
    (710055, "pol_r1_opening_pattern", "对外开放格局的形成与加入世界贸易组织", 4, SUBJECT, 710013),
    (710056, "pol_r1_market_economy_target", "社会主义市场经济体制改革目标的确立", 5, SUBJECT, 710013),
    (710057, "pol_r1_comprehensive_deepening", "全面深化改革与党的十八届三中全会的部署", 6, SUBJECT, 710013),
    (710058, "pol_r1_reform_opening_nature", "改革开放的性质、地位与鲜明特点", 7, SUBJECT, 710013),
    (710059, "pol_r1_reform_opening_significance", "改革开放的历史意义、宝贵经验与“关键一招”地位", 8, SUBJECT, 710013),

    # 3.2 中国特色社会主义的创立、发展和完善
    (710060, "pol_r1_deng_theory", "邓小平理论的形成与核心问题", 1, SUBJECT, 710014),
    (710061, "pol_r1_three_represents", "“三个代表”重要思想的形成与内涵", 2, SUBJECT, 710014),
    (710062, "pol_r1_scientific_outlook", "科学发展观的形成与内涵", 3, SUBJECT, 710014),
    (710063, "pol_r1_css_road", "中国特色社会主义道路的内涵与要求", 4, SUBJECT, 710014),
    (710064, "pol_r1_css_theory_system", "中国特色社会主义理论体系的构成", 5, SUBJECT, 710014),
    (710065, "pol_r1_css_system", "中国特色社会主义制度的构成与优势", 6, SUBJECT, 710014),
    (710066, "pol_r1_css_culture", "中国特色社会主义文化的内涵与作用", 7, SUBJECT, 710014),
    (710067, "pol_r1_css_overall_basis_layout", "中国特色社会主义的总依据、总布局与总任务", 8, SUBJECT, 710014),
    (710068, "pol_r1_four_confidences", "坚定道路自信、理论自信、制度自信、文化自信", 9, SUBJECT, 710014),

    # 4.1 中国特色社会主义进入新时代
    (710069, "pol_r1_new_era_connotation", "中国特色社会主义新时代的科学内涵", 1, SUBJECT, 710015),
    (710070, "pol_r1_main_contradiction_shift", "我国社会主要矛盾的历史性转化", 2, SUBJECT, 710015),
    (710071, "pol_r1_main_contradiction_basis", "新时代社会主要矛盾转化的依据与意义", 3, SUBJECT, 710015),
    (710072, "pol_r1_basic_strategy", "新时代坚持和发展中国特色社会主义的基本方略", 4, SUBJECT, 710015),
    (710073, "pol_r1_new_historical_position", "新时代我国发展新的历史方位与“变”与“不变”", 5, SUBJECT, 710015),
    (710074, "pol_r1_party_mission", "新时代中国共产党的历史使命", 6, SUBJECT, 710015),
    (710075, "pol_r1_four_greats", "伟大斗争、伟大工程、伟大事业、伟大梦想及其关系", 7, SUBJECT, 710015),
    (710076, "pol_r1_two_step_strategy", "新时代中国特色社会主义发展的两步走战略安排", 8, SUBJECT, 710015),

    # 4.2 实现中华民族伟大复兴的中国梦
    (710077, "pol_r1_chinese_dream_essence", "中国梦的本质内涵：国家富强、民族振兴、人民幸福", 1, SUBJECT, 710016),
    (710078, "pol_r1_chinese_dream_path", "实现中国梦必须走中国道路、弘扬中国精神、凝聚中国力量", 2, SUBJECT, 710016),
    (710079, "pol_r1_dream_and_personal_dream", "中国梦与个人梦的辩证关系", 3, SUBJECT, 710016),
    (710080, "pol_r1_well_off_society", "全面建成小康社会与打赢脱贫攻坚战", 4, SUBJECT, 710016),
    (710081, "pol_r1_modernization_deployment", "全面建设社会主义现代化国家的战略部署", 5, SUBJECT, 710016),
    (710082, "pol_r1_youth_responsibility", "青年学生在实现中国梦中的责任担当", 6, SUBJECT, 710016),

    # 4.3 习近平新时代中国特色社会主义思想
    (710083, "pol_r1_xi_thought_conditions", "习近平新时代中国特色社会主义思想创立的历史条件", 1, SUBJECT, 710017),
    (710084, "pol_r1_xi_thought_system", "习近平新时代中国特色社会主义思想的主题与科学体系", 2, SUBJECT, 710017),
    (710085, "pol_r1_ten_clear_points", "“十个明确”的核心内容", 3, SUBJECT, 710017),
    (710086, "pol_r1_six_must_persist", "“六个必须坚持”的世界观和方法论", 4, SUBJECT, 710017),
    (710087, "pol_r1_xi_thought_status", "习近平新时代中国特色社会主义思想的历史地位与理论贡献", 5, SUBJECT, 710017),
    (710088, "pol_r1_party_leadership", "坚持和加强党的全面领导", 6, SUBJECT, 710017),
    (710089, "pol_r1_people_centered", "坚持以人民为中心的发展思想", 7, SUBJECT, 710017),
    (710090, "pol_r1_chinese_modernization", "以中国式现代化全面推进中华民族伟大复兴", 8, SUBJECT, 710017),
)

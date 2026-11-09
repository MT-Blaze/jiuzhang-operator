"""人教版（2019）高中生物选择性必修第一册（稳态与调节）：章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 6
G10 = 10
BOOK_ID = 6103

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中生物选择性必修第一册（稳态与调节）",
    "bio_e1",
    3,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (630101, "第1章 人体的内环境与稳态", "bio_e1_ch01", 1, BOOK_ID, None),
    (630102, "第2章 神经调节", "bio_e1_ch02", 2, BOOK_ID, None),
    (630103, "第3章 体液调节", "bio_e1_ch03", 3, BOOK_ID, None),
    (630104, "第4章 免疫调节", "bio_e1_ch04", 4, BOOK_ID, None),
    (630105, "第5章 植物生命活动的调节", "bio_e1_ch05", 5, BOOK_ID, None),
    (630111, "第1节 细胞生活的环境", "bio_e1_ch01_s01", 1, BOOK_ID, 630101),
    (630112, "第2节 内环境的稳态", "bio_e1_ch01_s02", 2, BOOK_ID, 630101),
    (630121, "第1节 神经调节的结构基础", "bio_e1_ch02_s01", 1, BOOK_ID, 630102),
    (630122, "第2节 神经调节的基本方式", "bio_e1_ch02_s02", 2, BOOK_ID, 630102),
    (630123, "第3节 神经冲动的产生和传导", "bio_e1_ch02_s03", 3, BOOK_ID, 630102),
    (630124, "第4节 神经系统的分级调节", "bio_e1_ch02_s04", 4, BOOK_ID, 630102),
    (630125, "第5节 人脑的高级功能", "bio_e1_ch02_s05", 5, BOOK_ID, 630102),
    (630131, "第1节 激素与内分泌系统", "bio_e1_ch03_s01", 1, BOOK_ID, 630103),
    (630132, "第2节 激素调节的过程", "bio_e1_ch03_s02", 2, BOOK_ID, 630103),
    (630133, "第3节 体液调节与神经调节的关系", "bio_e1_ch03_s03", 3, BOOK_ID, 630103),
    (630141, "第1节 免疫系统的组成和功能", "bio_e1_ch04_s01", 1, BOOK_ID, 630104),
    (630142, "第2节 特异性免疫", "bio_e1_ch04_s02", 2, BOOK_ID, 630104),
    (630143, "第3节 免疫失调", "bio_e1_ch04_s03", 3, BOOK_ID, 630104),
    (630144, "第4节 免疫学的应用", "bio_e1_ch04_s04", 4, BOOK_ID, 630104),
    (630151, "第1节 植物生长素", "bio_e1_ch05_s01", 1, BOOK_ID, 630105),
    (630152, "第2节 其他植物激素", "bio_e1_ch05_s02", 2, BOOK_ID, 630105),
    (630153, "第3节 植物生长调节剂的应用", "bio_e1_ch05_s03", 3, BOOK_ID, 630105),
    (630154, "第4节 环境因素参与调节植物的生命活动", "bio_e1_ch05_s04", 4, BOOK_ID, 630105),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (630001, "bio_e1_domain_internal_environment", "内环境与稳态", 1, SUBJECT, G10, None),
    (630002, "bio_e1_domain_neural_regulation", "神经调节", 2, SUBJECT, G10, None),
    (630003, "bio_e1_domain_humoral_regulation", "体液调节", 3, SUBJECT, G10, None),
    (630004, "bio_e1_domain_immune_regulation", "免疫调节", 4, SUBJECT, G10, None),
    (630005, "bio_e1_domain_plant_regulation", "植物生命活动调节", 5, SUBJECT, G10, None),

    # 章域层
    (630006, "bio_e1_ch01", "人体的内环境与稳态", 1, SUBJECT, G10, 630001),
    (630007, "bio_e1_ch02", "神经调节", 1, SUBJECT, G10, 630002),
    (630008, "bio_e1_ch03", "体液调节", 1, SUBJECT, G10, 630003),
    (630009, "bio_e1_ch04", "免疫调节", 1, SUBJECT, G10, 630004),
    (630010, "bio_e1_ch05", "植物生命活动的调节", 1, SUBJECT, G10, 630005),

    # 节域层
    (630011, "bio_e1_s01_cell_environment", "第1节 细胞生活的环境", 1, SUBJECT, G10, 630006),
    (630012, "bio_e1_s02_homeostasis", "第2节 内环境的稳态", 2, SUBJECT, G10, 630006),
    (630013, "bio_e1_s03_neural_basis", "第1节 神经调节的结构基础", 1, SUBJECT, G10, 630007),
    (630014, "bio_e1_s04_reflex", "第2节 神经调节的基本方式", 2, SUBJECT, G10, 630007),
    (630015, "bio_e1_s05_nerve_impulse", "第3节 神经冲动的产生和传导", 3, SUBJECT, G10, 630007),
    (630016, "bio_e1_s06_hierarchical", "第4节 神经系统的分级调节", 4, SUBJECT, G10, 630007),
    (630017, "bio_e1_s07_brain_function", "第5节 人脑的高级功能", 5, SUBJECT, G10, 630007),
    (630018, "bio_e1_s08_hormone_endocrine", "第1节 激素与内分泌系统", 1, SUBJECT, G10, 630008),
    (630019, "bio_e1_s09_hormone_process", "第2节 激素调节的过程", 2, SUBJECT, G10, 630008),
    (630020, "bio_e1_s10_humoral_neural", "第3节 体液调节与神经调节的关系", 3, SUBJECT, G10, 630008),
    (630021, "bio_e1_s11_immune_composition", "第1节 免疫系统的组成和功能", 1, SUBJECT, G10, 630009),
    (630022, "bio_e1_s12_specific_immunity", "第2节 特异性免疫", 2, SUBJECT, G10, 630009),
    (630023, "bio_e1_s13_immune_disorder", "第3节 免疫失调", 3, SUBJECT, G10, 630009),
    (630024, "bio_e1_s14_immune_application", "第4节 免疫学的应用", 4, SUBJECT, G10, 630009),
    (630025, "bio_e1_s15_auxin", "第1节 植物生长素", 1, SUBJECT, G10, 630010),
    (630026, "bio_e1_s16_other_hormones", "第2节 其他植物激素", 2, SUBJECT, G10, 630010),
    (630027, "bio_e1_s17_regulator_application", "第3节 植物生长调节剂的应用", 3, SUBJECT, G10, 630010),
    (630028, "bio_e1_s18_environment_factor", "第4节 环境因素参与调节植物的生命活动", 4, SUBJECT, G10, 630010),

    # 1.1 细胞生活的环境
    (630029, "bio_e1_body_fluid", "体内细胞生活在细胞外液中", 1, SUBJECT, G10, 630011),
    (630030, "bio_e1_extracellular_fluid", "血浆、组织液与淋巴液的比较", 2, SUBJECT, G10, 630011),
    (630031, "bio_e1_internal_env_composition", "内环境的组成成分与物质交换", 3, SUBJECT, G10, 630011),
    (630032, "bio_e1_osmotic_pressure_ph", "细胞外液的渗透压与酸碱度", 4, SUBJECT, G10, 630011),
    (630033, "bio_e1_internal_env_medium", "内环境是细胞与外界环境进行物质交换的媒介", 5, SUBJECT, G10, 630011),

    # 1.2 内环境的稳态
    (630034, "bio_e1_homeostasis_concept", "内环境稳态的概念与实质", 1, SUBJECT, G10, 630012),
    (630035, "bio_e1_homeostasis_mechanism", "内环境稳态的调节机制", 2, SUBJECT, G10, 630012),
    (630036, "bio_e1_homeostasis_ability", "人体维持稳态的能力与稳态失调", 3, SUBJECT, G10, 630012),
    (630037, "bio_e1_plasma_ph_experiment", "探究血浆pH维持稳定的机制", 4, SUBJECT, G10, 630012),

    # 2.1 神经调节的结构基础
    (630038, "bio_e1_nervous_system", "神经系统的组成与中枢神经系统", 1, SUBJECT, G10, 630013),
    (630039, "bio_e1_neuron_structure", "神经元的结构与功能", 2, SUBJECT, G10, 630013),
    (630040, "bio_e1_glial_cell", "神经胶质细胞的功能", 3, SUBJECT, G10, 630013),
    (630041, "bio_e1_autonomic_nervous", "自主神经系统与内脏运动", 4, SUBJECT, G10, 630013),

    # 2.2 神经调节的基本方式
    (630042, "bio_e1_reflex_arc", "反射与反射弧的组成", 1, SUBJECT, G10, 630014),
    (630043, "bio_e1_conditioned_reflex", "非条件反射与条件反射", 2, SUBJECT, G10, 630014),
    (630044, "bio_e1_reflex_arc_damage", "反射弧各部分受损的症状分析", 3, SUBJECT, G10, 630014),

    # 2.3 神经冲动的产生和传导
    (630045, "bio_e1_resting_potential", "静息电位与K+外流", 1, SUBJECT, G10, 630015),
    (630046, "bio_e1_action_potential", "动作电位与Na+内流", 2, SUBJECT, G10, 630015),
    (630047, "bio_e1_nerve_fiber_conduction", "局部电流与兴奋在神经纤维上的传导", 3, SUBJECT, G10, 630015),
    (630048, "bio_e1_synapse_structure", "突触的结构与类型", 4, SUBJECT, G10, 630015),
    (630049, "bio_e1_synaptic_transmission", "兴奋在神经元之间的传递过程", 5, SUBJECT, G10, 630015),
    (630050, "bio_e1_neurotransmitter", "神经递质的类型与兴奋性、抑制性突触", 6, SUBJECT, G10, 630015),

    # 2.4 神经系统的分级调节
    (630051, "bio_e1_hierarchical_control", "神经系统的分级调节与中枢分布", 1, SUBJECT, G10, 630016),
    (630052, "bio_e1_cortex_low_center", "大脑皮层对低级中枢的调控与排尿反射", 2, SUBJECT, G10, 630016),

    # 2.5 人脑的高级功能
    (630053, "bio_e1_speech_area", "大脑皮层的言语区与功能分区", 1, SUBJECT, G10, 630017),
    (630054, "bio_e1_learning_memory", "学习与记忆的过程与机制", 2, SUBJECT, G10, 630017),
    (630055, "bio_e1_emotion", "情绪与大脑皮层的关系", 3, SUBJECT, G10, 630017),
    (630056, "bio_e1_drug_addiction", "神经系统疾病与毒品成瘾", 4, SUBJECT, G10, 630017),

    # 3.1 激素与内分泌系统
    (630057, "bio_e1_secretin_discovery", "促胰液素的发现与激素概念", 1, SUBJECT, G10, 630018),
    (630058, "bio_e1_gland_hormone_type", "内分泌腺、外分泌腺与激素的化学本质", 2, SUBJECT, G10, 630018),
    (630059, "bio_e1_endocrine_glands", "人体主要内分泌腺及其激素", 3, SUBJECT, G10, 630018),
    (630060, "bio_e1_hormone_features", "激素调节的特点", 4, SUBJECT, G10, 630018),

    # 3.2 激素调节的过程
    (630061, "bio_e1_blood_glucose_source", "血糖的来源与去路", 1, SUBJECT, G10, 630019),
    (630062, "bio_e1_insulin_glucagon", "胰岛素与胰高血糖素的作用", 2, SUBJECT, G10, 630019),
    (630063, "bio_e1_blood_glucose_regulation", "血糖平衡的神经—体液调节", 3, SUBJECT, G10, 630019),
    (630064, "bio_e1_thyroid_axis_feedback", "甲状腺激素分泌的分级调节与反馈调节", 4, SUBJECT, G10, 630019),
    (630065, "bio_e1_hormone_synergy_antagonism", "激素间的协同作用与拮抗作用", 5, SUBJECT, G10, 630019),
    (630066, "bio_e1_hormone_experiment", "激素调节的实例分析与实验设计", 6, SUBJECT, G10, 630019),

    # 3.3 体液调节与神经调节的关系
    (630067, "bio_e1_humoral_neural_compare", "体液调节与神经调节的比较", 1, SUBJECT, G10, 630020),
    (630068, "bio_e1_temperature_regulation", "体温调节的过程与机制", 2, SUBJECT, G10, 630020),
    (630069, "bio_e1_water_salt_balance", "水盐平衡调节与抗利尿激素", 3, SUBJECT, G10, 630020),

    # 4.1 免疫系统的组成和功能
    (630070, "bio_e1_immune_composition", "免疫系统的组成", 1, SUBJECT, G10, 630021),
    (630071, "bio_e1_immune_cells", "免疫细胞的来源与功能", 2, SUBJECT, G10, 630021),
    (630072, "bio_e1_three_defense_lines", "免疫系统的三道防线", 3, SUBJECT, G10, 630021),
    (630073, "bio_e1_immune_function", "免疫系统的防卫、监控与清除功能", 4, SUBJECT, G10, 630021),

    # 4.2 特异性免疫
    (630074, "bio_e1_antigen_antibody", "抗原与抗体的特性", 1, SUBJECT, G10, 630022),
    (630075, "bio_e1_humoral_immunity", "体液免疫的过程", 2, SUBJECT, G10, 630022),
    (630076, "bio_e1_cellular_immunity", "细胞免疫的过程", 3, SUBJECT, G10, 630022),
    (630077, "bio_e1_secondary_immunity", "二次免疫与记忆细胞", 4, SUBJECT, G10, 630022),
    (630078, "bio_e1_humoral_cellular_compare", "体液免疫与细胞免疫的关系与比较", 5, SUBJECT, G10, 630022),

    # 4.3 免疫失调
    (630079, "bio_e1_allergy", "过敏反应与过敏原", 1, SUBJECT, G10, 630023),
    (630080, "bio_e1_autoimmune_immunodeficiency", "自身免疫病与免疫缺陷病", 2, SUBJECT, G10, 630023),
    (630081, "bio_e1_immune_disorder_case", "免疫失调疾病实例与预防", 3, SUBJECT, G10, 630023),

    # 4.4 免疫学的应用
    (630082, "bio_e1_vaccine", "疫苗的种类与作用原理", 1, SUBJECT, G10, 630024),
    (630083, "bio_e1_organ_transplant", "器官移植与免疫排斥", 2, SUBJECT, G10, 630024),
    (630084, "bio_e1_immunology_application", "免疫学在诊断与治疗中的应用", 3, SUBJECT, G10, 630024),

    # 5.1 植物生长素
    (630085, "bio_e1_auxin_discovery", "生长素的发现历程", 1, SUBJECT, G10, 630025),
    (630086, "bio_e1_auxin_transport", "生长素的产生、运输与分布", 2, SUBJECT, G10, 630025),
    (630087, "bio_e1_auxin_function", "生长素的生理作用与两重性", 3, SUBJECT, G10, 630025),
    (630088, "bio_e1_auxin_curve_cases", "生长素作用曲线与顶端优势、向性运动", 4, SUBJECT, G10, 630025),
    (630089, "bio_e1_auxin_rooting_experiment", "探究生长素类似物促进插条生根的最适浓度", 5, SUBJECT, G10, 630025),

    # 5.2 其他植物激素
    (630090, "bio_e1_gibberellin", "赤霉素的生理作用与应用", 1, SUBJECT, G10, 630026),
    (630091, "bio_e1_cytokinin_abscisic", "细胞分裂素与脱落酸的生理作用", 2, SUBJECT, G10, 630026),
    (630092, "bio_e1_ethylene", "乙烯的生理作用与果实催熟", 3, SUBJECT, G10, 630026),
    (630093, "bio_e1_phytohormone_interaction", "植物激素间的相互作用", 4, SUBJECT, G10, 630026),

    # 5.3 植物生长调节剂的应用
    (630094, "bio_e1_growth_regulator", "植物生长调节剂的概念与类型", 1, SUBJECT, G10, 630027),
    (630095, "bio_e1_regulator_application", "植物生长调节剂的应用实例与注意事项", 2, SUBJECT, G10, 630027),
    (630096, "bio_e1_regulator_experiment", "探索植物生长调节剂的应用实验", 3, SUBJECT, G10, 630027),

    # 5.4 环境因素参与调节植物的生命活动
    (630097, "bio_e1_light_regulation", "光对植物生命活动的调节与光敏色素", 1, SUBJECT, G10, 630028),
    (630098, "bio_e1_temperature_gravity", "温度与重力对植物生命活动的调节", 2, SUBJECT, G10, 630028),
    (630099, "bio_e1_plant_growth_integration", "植物生长发育的整体调控", 3, SUBJECT, G10, 630028),
)

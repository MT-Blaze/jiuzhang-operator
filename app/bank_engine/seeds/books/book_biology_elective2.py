"""人教版（2019）高中生物选择性必修第二册（生物与环境）：章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 6
G10 = 10
BOOK_ID = 6104

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中生物选择性必修第二册（生物与环境）",
    "bio_e2",
    4,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (640101, "第1章 种群及其动态", "bio_e2_ch01", 1, BOOK_ID, None),
    (640102, "第2章 群落及其演替", "bio_e2_ch02", 2, BOOK_ID, None),
    (640103, "第3章 生态系统及其稳定性", "bio_e2_ch03", 3, BOOK_ID, None),
    (640104, "第4章 人与环境", "bio_e2_ch04", 4, BOOK_ID, None),
    (640111, "第1节 种群的数量特征", "bio_e2_ch01_s01", 1, BOOK_ID, 640101),
    (640112, "第2节 种群数量的变化", "bio_e2_ch01_s02", 2, BOOK_ID, 640101),
    (640113, "第3节 影响种群数量变化的因素", "bio_e2_ch01_s03", 3, BOOK_ID, 640101),
    (640121, "第1节 群落的结构", "bio_e2_ch02_s01", 1, BOOK_ID, 640102),
    (640122, "第2节 群落的主要类型", "bio_e2_ch02_s02", 2, BOOK_ID, 640102),
    (640123, "第3节 群落的演替", "bio_e2_ch02_s03", 3, BOOK_ID, 640102),
    (640131, "第1节 生态系统的结构", "bio_e2_ch03_s01", 1, BOOK_ID, 640103),
    (640132, "第2节 生态系统的能量流动", "bio_e2_ch03_s02", 2, BOOK_ID, 640103),
    (640133, "第3节 生态系统的物质循环", "bio_e2_ch03_s03", 3, BOOK_ID, 640103),
    (640134, "第4节 生态系统的信息传递", "bio_e2_ch03_s04", 4, BOOK_ID, 640103),
    (640135, "第5节 生态系统的稳定性", "bio_e2_ch03_s05", 5, BOOK_ID, 640103),
    (640141, "第1节 人类活动对生态环境的影响", "bio_e2_ch04_s01", 1, BOOK_ID, 640104),
    (640142, "第2节 生物多样性及其保护", "bio_e2_ch04_s02", 2, BOOK_ID, 640104),
    (640143, "第3节 生态工程", "bio_e2_ch04_s03", 3, BOOK_ID, 640104),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (640001, "bio_e2_domain_population", "种群动态", 1, SUBJECT, None),
    (640002, "bio_e2_domain_community", "群落与环境", 2, SUBJECT, None),
    (640003, "bio_e2_domain_ecosystem", "生态系统的结构与功能", 3, SUBJECT, None),
    (640004, "bio_e2_domain_human_environment", "人与环境的协调", 4, SUBJECT, None),

    # 章域层
    (640005, "bio_e2_ch01", "种群及其动态", 1, SUBJECT, 640001),
    (640006, "bio_e2_ch02", "群落及其演替", 1, SUBJECT, 640002),
    (640007, "bio_e2_ch03", "生态系统及其稳定性", 1, SUBJECT, 640003),
    (640008, "bio_e2_ch04", "人与环境", 1, SUBJECT, 640004),

    # 节域层
    (640009, "bio_e2_s01_population_features", "第1节 种群的数量特征", 1, SUBJECT, 640005),
    (640010, "bio_e2_s02_population_change", "第2节 种群数量的变化", 2, SUBJECT, 640005),
    (640011, "bio_e2_s03_population_factors", "第3节 影响种群数量变化的因素", 3, SUBJECT, 640005),
    (640012, "bio_e2_s04_community_structure", "第1节 群落的结构", 1, SUBJECT, 640006),
    (640013, "bio_e2_s05_community_types", "第2节 群落的主要类型", 2, SUBJECT, 640006),
    (640014, "bio_e2_s06_succession", "第3节 群落的演替", 3, SUBJECT, 640006),
    (640015, "bio_e2_s07_ecosystem_structure", "第1节 生态系统的结构", 1, SUBJECT, 640007),
    (640016, "bio_e2_s08_energy_flow", "第2节 生态系统的能量流动", 2, SUBJECT, 640007),
    (640017, "bio_e2_s09_material_cycle", "第3节 生态系统的物质循环", 3, SUBJECT, 640007),
    (640018, "bio_e2_s10_information_transfer", "第4节 生态系统的信息传递", 4, SUBJECT, 640007),
    (640019, "bio_e2_s11_stability", "第5节 生态系统的稳定性", 5, SUBJECT, 640007),
    (640020, "bio_e2_s12_human_impact", "第1节 人类活动对生态环境的影响", 1, SUBJECT, 640008),
    (640021, "bio_e2_s13_biodiversity", "第2节 生物多样性及其保护", 2, SUBJECT, 640008),
    (640022, "bio_e2_s14_ecological_engineering", "第3节 生态工程", 3, SUBJECT, 640008),

    # 1.1 种群的数量特征
    (640023, "bio_e2_population_concept", "种群的概念与判定", 1, SUBJECT, 640009),
    (640024, "bio_e2_population_density", "种群密度的概念与单位", 2, SUBJECT, 640009),
    (640025, "bio_e2_quadrat_method", "样方法调查种群密度", 3, SUBJECT, 640009),
    (640026, "bio_e2_mark_recapture", "标记重捕法及其误差分析", 4, SUBJECT, 640009),
    (640027, "bio_e2_birth_death_rate", "出生率与死亡率", 5, SUBJECT, 640009),
    (640028, "bio_e2_immigration_emigration", "迁入率与迁出率", 6, SUBJECT, 640009),
    (640029, "bio_e2_age_structure", "年龄结构及其三种类型", 7, SUBJECT, 640009),
    (640030, "bio_e2_sex_ratio", "性别比例与种群数量", 8, SUBJECT, 640009),

    # 1.2 种群数量的变化
    (640031, "bio_e2_mathematical_model", "种群增长数学模型的构建", 1, SUBJECT, 640010),
    (640032, "bio_e2_j_shaped_growth", "J型增长的条件与公式", 2, SUBJECT, 640010),
    (640033, "bio_e2_s_shaped_growth", "S型增长与K值", 3, SUBJECT, 640010),
    (640034, "bio_e2_carrying_capacity", "K值在渔业捕捞与保护中的应用", 4, SUBJECT, 640010),
    (640035, "bio_e2_population_fluctuation", "种群数量的波动与下降", 5, SUBJECT, 640010),
    (640036, "bio_e2_yeast_population_experiment", "培养液中酵母菌种群数量的变化实验", 6, SUBJECT, 640010),

    # 1.3 影响种群数量变化的因素
    (640037, "bio_e2_density_independent", "非密度制约因素", 1, SUBJECT, 640011),
    (640038, "bio_e2_density_dependent", "密度制约因素", 2, SUBJECT, 640011),
    (640039, "bio_e2_intraspecific_competition", "种内竞争与领域行为", 3, SUBJECT, 640011),
    (640040, "bio_e2_population_application", "种群数量规律在捕捞与防治中的应用", 4, SUBJECT, 640011),

    # 2.1 群落的结构
    (640041, "bio_e2_community_concept", "群落的概念与物种组成", 1, SUBJECT, 640012),
    (640042, "bio_e2_species_richness", "物种丰富度与优势种", 2, SUBJECT, 640012),
    (640043, "bio_e2_predation", "种间关系之捕食", 3, SUBJECT, 640012),
    (640044, "bio_e2_competition", "种间关系之竞争", 4, SUBJECT, 640012),
    (640045, "bio_e2_parasitism", "种间关系之寄生", 5, SUBJECT, 640012),
    (640046, "bio_e2_mutualism", "种间关系之互利共生", 6, SUBJECT, 640012),
    (640047, "bio_e2_spatial_structure", "群落的垂直结构与水平结构", 7, SUBJECT, 640012),
    (640048, "bio_e2_ecological_niche", "生态位", 8, SUBJECT, 640012),

    # 2.2 群落的主要类型
    (640049, "bio_e2_desert_community", "荒漠生物群落", 1, SUBJECT, 640013),
    (640050, "bio_e2_grassland_community", "草原生物群落", 2, SUBJECT, 640013),
    (640051, "bio_e2_forest_community", "森林生物群落", 3, SUBJECT, 640013),
    (640052, "bio_e2_wetland_community", "湿地与水生生物群落", 4, SUBJECT, 640013),

    # 2.3 群落的演替
    (640053, "bio_e2_succession_concept", "群落演替的概念与类型", 1, SUBJECT, 640014),
    (640054, "bio_e2_primary_succession", "初生演替", 2, SUBJECT, 640014),
    (640055, "bio_e2_secondary_succession", "次生演替", 3, SUBJECT, 640014),
    (640056, "bio_e2_human_succession", "人类活动对群落演替的影响", 4, SUBJECT, 640014),

    # 3.1 生态系统的结构
    (640057, "bio_e2_ecosystem_concept", "生态系统的概念与范围", 1, SUBJECT, 640015),
    (640058, "bio_e2_abiotic_component", "非生物的物质和能量", 2, SUBJECT, 640015),
    (640059, "bio_e2_producer", "生产者", 3, SUBJECT, 640015),
    (640060, "bio_e2_consumer", "消费者", 4, SUBJECT, 640015),
    (640061, "bio_e2_decomposer", "分解者", 5, SUBJECT, 640015),
    (640062, "bio_e2_food_chain_web", "食物链与食物网", 6, SUBJECT, 640015),

    # 3.2 生态系统的能量流动
    (640063, "bio_e2_energy_flow_process", "能量流动的过程与途径", 1, SUBJECT, 640016),
    (640064, "bio_e2_energy_flow_features", "单向流动与逐级递减", 2, SUBJECT, 640016),
    (640065, "bio_e2_energy_transfer_efficiency", "能量传递效率与能量金字塔", 3, SUBJECT, 640016),
    (640066, "bio_e2_energy_flow_application", "研究能量流动的实践意义", 4, SUBJECT, 640016),

    # 3.3 生态系统的物质循环
    (640067, "bio_e2_material_cycle_concept", "物质循环的概念与特点", 1, SUBJECT, 640017),
    (640068, "bio_e2_carbon_cycle", "碳循环的过程与途径", 2, SUBJECT, 640017),
    (640069, "bio_e2_nitrogen_cycle", "氮循环", 3, SUBJECT, 640017),
    (640070, "bio_e2_material_energy_relation", "物质循环与能量流动的关系", 4, SUBJECT, 640017),

    # 3.4 生态系统的信息传递
    (640071, "bio_e2_physical_information", "物理信息的传递", 1, SUBJECT, 640018),
    (640072, "bio_e2_chemical_information", "化学信息的传递", 2, SUBJECT, 640018),
    (640073, "bio_e2_behavioral_information", "行为信息的传递", 3, SUBJECT, 640018),
    (640074, "bio_e2_information_function", "信息传递的作用与农业应用", 4, SUBJECT, 640018),

    # 3.5 生态系统的稳定性
    (640075, "bio_e2_ecological_balance", "生态平衡", 1, SUBJECT, 640019),
    (640076, "bio_e2_resistance_stability", "抵抗力稳定性", 2, SUBJECT, 640019),
    (640077, "bio_e2_resilience_stability", "恢复力稳定性", 3, SUBJECT, 640019),
    (640078, "bio_e2_stability_measures", "稳定性影响因素与提高措施", 4, SUBJECT, 640019),

    # 4.1 人类活动对生态环境的影响
    (640079, "bio_e2_population_pressure", "人口增长对生态环境的影响", 1, SUBJECT, 640020),
    (640080, "bio_e2_global_warming", "全球气候变化与温室效应", 2, SUBJECT, 640020),
    (640081, "bio_e2_ozone_acid_rain", "臭氧层破坏与酸雨", 3, SUBJECT, 640020),
    (640082, "bio_e2_water_pollution", "水体污染与富营养化", 4, SUBJECT, 640020),
    (640083, "bio_e2_desertification", "土地荒漠化与可持续发展", 5, SUBJECT, 640020),

    # 4.2 生物多样性及其保护
    (640084, "bio_e2_biodiversity_levels", "生物多样性的三个层次", 1, SUBJECT, 640021),
    (640085, "bio_e2_direct_value", "生物多样性的直接价值", 2, SUBJECT, 640021),
    (640086, "bio_e2_indirect_value", "生物多样性的间接价值", 3, SUBJECT, 640021),
    (640087, "bio_e2_potential_value", "生物多样性的潜在价值", 4, SUBJECT, 640021),
    (640088, "bio_e2_biodiversity_loss", "生物多样性丧失的原因", 5, SUBJECT, 640021),
    (640089, "bio_e2_in_situ_conservation", "就地保护", 6, SUBJECT, 640021),
    (640090, "bio_e2_ex_situ_conservation", "易地保护", 7, SUBJECT, 640021),

    # 4.3 生态工程
    (640091, "bio_e2_eco_engineering_concept", "生态工程的概念与特点", 1, SUBJECT, 640022),
    (640092, "bio_e2_self_generation_principle", "自生原理", 2, SUBJECT, 640022),
    (640093, "bio_e2_cycle_principle", "循环原理", 3, SUBJECT, 640022),
    (640094, "bio_e2_coordination_holism", "协调原理与整体原理", 4, SUBJECT, 640022),
    (640095, "bio_e2_eco_engineering_cases", "生态工程实例", 5, SUBJECT, 640022),
)

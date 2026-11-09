"""人教版（2019）高中化学选择性必修第一册：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 5
G10 = 10
BOOK_ID = 5103

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中化学选择性必修第一册（化学反应原理）",
    "chem_e1",
    3,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (530101, "第一章 化学反应的热效应", "chem_e1_ch01", 1, BOOK_ID, None),
    (530102, "第二章 化学反应速率与化学平衡", "chem_e1_ch02", 2, BOOK_ID, None),
    (530103, "第三章 水溶液中的离子反应与平衡", "chem_e1_ch03", 3, BOOK_ID, None),
    (530104, "第四章 化学反应与电能", "chem_e1_ch04", 4, BOOK_ID, None),
    (530111, "第一节 反应热", "chem_e1_ch01_s01", 1, BOOK_ID, 530101),
    (530112, "第二节 反应热的计算", "chem_e1_ch01_s02", 2, BOOK_ID, 530101),
    (530121, "第一节 化学反应速率", "chem_e1_ch02_s01", 1, BOOK_ID, 530102),
    (530122, "第二节 化学平衡", "chem_e1_ch02_s02", 2, BOOK_ID, 530102),
    (530123, "第三节 化学反应的方向", "chem_e1_ch02_s03", 3, BOOK_ID, 530102),
    (530124, "第四节 化学反应的调控", "chem_e1_ch02_s04", 4, BOOK_ID, 530102),
    (530131, "第一节 电离平衡", "chem_e1_ch03_s01", 1, BOOK_ID, 530103),
    (530132, "第二节 水的电离和溶液的pH", "chem_e1_ch03_s02", 2, BOOK_ID, 530103),
    (530133, "第三节 盐类的水解", "chem_e1_ch03_s03", 3, BOOK_ID, 530103),
    (530134, "第四节 沉淀溶解平衡", "chem_e1_ch03_s04", 4, BOOK_ID, 530103),
    (530141, "第一节 原电池", "chem_e1_ch04_s01", 1, BOOK_ID, 530104),
    (530142, "第二节 电解池", "chem_e1_ch04_s02", 2, BOOK_ID, 530104),
    (530143, "第三节 金属的腐蚀与防护", "chem_e1_ch04_s03", 3, BOOK_ID, 530104),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (530001, "chem_e1_heat_effect", "化学反应的热效应", 1, SUBJECT, None),
    (530002, "chem_e1_rate_equilibrium", "反应速率与平衡调控", 2, SUBJECT, None),
    (530003, "chem_e1_ion_balance", "水溶液中的离子平衡专题", 3, SUBJECT, None),
    (530004, "chem_e1_electrochem", "化学能与电能的转化", 4, SUBJECT, None),

    # 章域层
    (530005, "chem_e1_ch01", "化学反应的热效应", 1, SUBJECT, 530001),
    (530006, "chem_e1_ch02", "化学反应速率与化学平衡", 1, SUBJECT, 530002),
    (530007, "chem_e1_ch03", "水溶液中的离子反应与平衡", 1, SUBJECT, 530003),
    (530008, "chem_e1_ch04", "化学反应与电能", 1, SUBJECT, 530004),

    # 节域层
    (530009, "chem_e1_section_reaction_heat", "第一节 反应热", 1, SUBJECT, 530005),
    (530010, "chem_e1_section_heat_calc", "第二节 反应热的计算", 2, SUBJECT, 530005),
    (530011, "chem_e1_section_rate", "第一节 化学反应速率", 1, SUBJECT, 530006),
    (530012, "chem_e1_section_equilibrium", "第二节 化学平衡", 2, SUBJECT, 530006),
    (530013, "chem_e1_section_direction", "第三节 化学反应的方向", 3, SUBJECT, 530006),
    (530014, "chem_e1_section_regulation", "第四节 化学反应的调控", 4, SUBJECT, 530006),
    (530015, "chem_e1_section_ionization", "第一节 电离平衡", 1, SUBJECT, 530007),
    (530016, "chem_e1_section_water_ph", "第二节 水的电离和溶液的pH", 2, SUBJECT, 530007),
    (530017, "chem_e1_section_hydrolysis", "第三节 盐类的水解", 3, SUBJECT, 530007),
    (530018, "chem_e1_section_precipitation", "第四节 沉淀溶解平衡", 4, SUBJECT, 530007),
    (530019, "chem_e1_section_galvanic", "第一节 原电池", 1, SUBJECT, 530008),
    (530020, "chem_e1_section_electrolysis", "第二节 电解池", 2, SUBJECT, 530008),
    (530021, "chem_e1_section_corrosion", "第三节 金属的腐蚀与防护", 3, SUBJECT, 530008),

    # 1.1 反应热
    (530022, "chem_e1_system_internal_energy", "体系、环境与内能", 1, SUBJECT, 530009),
    (530023, "chem_e1_reaction_enthalpy", "反应热与焓变的概念", 2, SUBJECT, 530009),
    (530024, "chem_e1_exo_endo", "放热反应与吸热反应的判断", 3, SUBJECT, 530009),
    (530025, "chem_e1_enthalpy_symbol", "焓变的符号与热化学含义", 4, SUBJECT, 530009),
    (530026, "chem_e1_bond_energy", "键能与反应热的定性关系", 5, SUBJECT, 530009),
    (530027, "chem_e1_energy_profile", "能量变化图与活化能", 6, SUBJECT, 530009),
    (530028, "chem_e1_thermochemical_equation", "热化学方程式的书写规范", 7, SUBJECT, 530009),

    # 1.2 反应热的计算
    (530029, "chem_e1_combustion_neutralization", "燃烧热与中和热", 1, SUBJECT, 530010),
    (530030, "chem_e1_hess_law", "盖斯定律的内容与理解", 2, SUBJECT, 530010),
    (530031, "chem_e1_hess_application", "盖斯定律的解题步骤", 3, SUBJECT, 530010),
    (530032, "chem_e1_enthalpy_compare", "反应热大小比较", 4, SUBJECT, 530010),
    (530033, "chem_e1_neutralization_measure", "中和反应反应热的测定", 5, SUBJECT, 530010),

    # 2.1 化学反应速率
    (530034, "chem_e1_rate_expression", "化学反应速率的表达式", 1, SUBJECT, 530011),
    (530035, "chem_e1_average_instant_rate", "平均速率与瞬时速率", 2, SUBJECT, 530011),
    (530036, "chem_e1_rate_stoichiometry", "速率之比与化学计量数之比", 3, SUBJECT, 530011),
    (530037, "chem_e1_rate_concentration_pressure", "浓度与压强对速率的影响", 4, SUBJECT, 530011),
    (530038, "chem_e1_rate_temperature_catalyst", "温度与催化剂对速率的影响", 5, SUBJECT, 530011),
    (530039, "chem_e1_rate_variables", "控制变量法探究速率影响因素", 6, SUBJECT, 530011),
    (530040, "chem_e1_rate_graph", "速率图像与数据分析", 7, SUBJECT, 530011),

    # 2.2 化学平衡
    (530041, "chem_e1_reversible_equilibrium", "可逆反应与化学平衡状态", 1, SUBJECT, 530012),
    (530042, "chem_e1_equilibrium_feature", "化学平衡状态的特征", 2, SUBJECT, 530012),
    (530043, "chem_e1_equilibrium_judge", "化学平衡状态的判断", 3, SUBJECT, 530012),
    (530044, "chem_e1_equilibrium_constant_expr", "化学平衡常数的表达式", 4, SUBJECT, 530012),
    (530045, "chem_e1_equilibrium_constant_meaning", "平衡常数的意义与影响因素", 5, SUBJECT, 530012),
    (530046, "chem_e1_conversion_calc", "转化率与平衡计算", 6, SUBJECT, 530012),
    (530047, "chem_e1_shift_concentration_pressure", "浓度、压强对平衡的影响", 7, SUBJECT, 530012),
    (530048, "chem_e1_shift_temperature", "温度对平衡的影响与勒夏特列原理", 8, SUBJECT, 530012),

    # 2.3 化学反应的方向
    (530049, "chem_e1_spontaneous_enthalpy", "自发反应与焓判据", 1, SUBJECT, 530013),
    (530050, "chem_e1_entropy", "熵与熵变", 2, SUBJECT, 530013),
    (530051, "chem_e1_entropy_criterion", "熵判据", 3, SUBJECT, 530013),
    (530052, "chem_e1_gibbs_criterion", "吉布斯自由能判据", 4, SUBJECT, 530013),
    (530053, "chem_e1_direction_temperature", "温度对反应方向的影响", 5, SUBJECT, 530013),

    # 2.4 化学反应的调控
    (530054, "chem_e1_ammonia_synthesis", "合成氨反应的特点", 1, SUBJECT, 530014),
    (530055, "chem_e1_ammonia_condition", "合成氨条件的选择", 2, SUBJECT, 530014),
    (530056, "chem_e1_industry_tradeoff", "工业生产中速率与平衡的统筹", 3, SUBJECT, 530014),
    (530057, "chem_e1_catalyst_select", "催化剂的选择与使用", 4, SUBJECT, 530014),

    # 3.1 电离平衡
    (530058, "chem_e1_strong_weak_electrolyte", "强电解质与弱电解质", 1, SUBJECT, 530015),
    (530059, "chem_e1_weak_ionization", "弱电解质的电离平衡", 2, SUBJECT, 530015),
    (530060, "chem_e1_ionization_constant", "电离平衡常数", 3, SUBJECT, 530015),
    (530061, "chem_e1_ionization_degree", "电离度与浓度关系", 4, SUBJECT, 530015),
    (530062, "chem_e1_ionization_factor", "影响电离平衡的因素", 5, SUBJECT, 530015),
    (530063, "chem_e1_ionization_application", "电离平衡的应用与比较", 6, SUBJECT, 530015),

    # 3.2 水的电离和溶液的pH
    (530064, "chem_e1_water_ionization", "水的电离与离子积常数", 1, SUBJECT, 530016),
    (530065, "chem_e1_water_factor", "影响水电离的因素", 2, SUBJECT, 530016),
    (530066, "chem_e1_ph_definition", "pH的定义与计算", 3, SUBJECT, 530016),
    (530067, "chem_e1_ph_strong", "强酸强碱溶液的pH计算", 4, SUBJECT, 530016),
    (530068, "chem_e1_ph_mixing", "酸碱混合的pH计算", 5, SUBJECT, 530016),
    (530069, "chem_e1_ph_measure", "pH的测定与试纸使用", 6, SUBJECT, 530016),

    # 3.3 盐类的水解
    (530070, "chem_e1_hydrolysis_essence", "盐类水解的实质", 1, SUBJECT, 530017),
    (530071, "chem_e1_hydrolysis_type", "强酸弱碱盐与强碱弱酸盐", 2, SUBJECT, 530017),
    (530072, "chem_e1_hydrolysis_factor", "影响盐类水解的因素", 3, SUBJECT, 530017),
    (530073, "chem_e1_hydrolysis_equation", "盐类水解的离子方程式", 4, SUBJECT, 530017),
    (530074, "chem_e1_hydrolysis_application", "盐类水解的应用", 5, SUBJECT, 530017),
    (530075, "chem_e1_ion_concentration_order", "离子浓度大小比较", 6, SUBJECT, 530017),

    # 3.4 沉淀溶解平衡
    (530076, "chem_e1_precipitation_equilibrium", "沉淀溶解平衡的建立", 1, SUBJECT, 530018),
    (530077, "chem_e1_solubility_product", "溶度积常数", 2, SUBJECT, 530018),
    (530078, "chem_e1_ksp_rule", "溶度积规则与沉淀生成", 3, SUBJECT, 530018),
    (530079, "chem_e1_precipitation_conversion", "沉淀的溶解与转化", 4, SUBJECT, 530018),
    (530080, "chem_e1_precipitation_application", "沉淀溶解平衡的应用", 5, SUBJECT, 530018),

    # 4.1 原电池
    (530081, "chem_e1_galvanic_principle", "原电池的工作原理", 1, SUBJECT, 530019),
    (530082, "chem_e1_galvanic_condition", "原电池的构成条件", 2, SUBJECT, 530019),
    (530083, "chem_e1_electrode_judge", "电极判断与电子流向", 3, SUBJECT, 530019),
    (530084, "chem_e1_battery_equation", "电极反应式与电池总反应", 4, SUBJECT, 530019),
    (530085, "chem_e1_chemical_power", "常见化学电源", 5, SUBJECT, 530019),
    (530086, "chem_e1_galvanic_application", "原电池原理的应用", 6, SUBJECT, 530019),

    # 4.2 电解池
    (530087, "chem_e1_electrolysis_principle", "电解池的工作原理", 1, SUBJECT, 530020),
    (530088, "chem_e1_electrolysis_structure", "电解池的构成与电极判断", 2, SUBJECT, 530020),
    (530089, "chem_e1_discharge_order", "惰性电极的放电顺序", 3, SUBJECT, 530020),
    (530090, "chem_e1_electrolysis_application", "电解原理的应用", 4, SUBJECT, 530020),
    (530091, "chem_e1_electroplating_refining", "电镀与电解精炼", 5, SUBJECT, 530020),
    (530092, "chem_e1_electro_calculation", "电化学计算", 6, SUBJECT, 530020),

    # 4.3 金属的腐蚀与防护
    (530093, "chem_e1_corrosion_type", "化学腐蚀与电化学腐蚀", 1, SUBJECT, 530021),
    (530094, "chem_e1_hydrogen_oxygen_corrosion", "析氢腐蚀与吸氧腐蚀", 2, SUBJECT, 530021),
    (530095, "chem_e1_metal_protection", "金属防护的方法", 3, SUBJECT, 530021),
    (530096, "chem_e1_cathodic_protection", "牺牲阳极法与外加电流法", 4, SUBJECT, 530021),
)

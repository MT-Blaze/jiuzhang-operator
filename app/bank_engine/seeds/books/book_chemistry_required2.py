"""人教版（2019）高中化学必修第二册：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 5
G10 = 10
BOOK_ID = 5102

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中化学必修第二册",
    "chem_r2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (520101, "第五章 化工生产中的重要非金属元素", "chem_r2_ch05", 1, BOOK_ID, None),
    (520102, "第六章 化学反应与能量", "chem_r2_ch06", 2, BOOK_ID, None),
    (520103, "第七章 有机化合物", "chem_r2_ch07", 3, BOOK_ID, None),
    (520104, "第八章 化学与可持续发展", "chem_r2_ch08", 4, BOOK_ID, None),
    (520111, "第一节 硫及其化合物", "chem_r2_ch05_s01", 1, BOOK_ID, 520101),
    (520112, "第二节 氮及其化合物", "chem_r2_ch05_s02", 2, BOOK_ID, 520101),
    (520113, "第三节 无机非金属材料", "chem_r2_ch05_s03", 3, BOOK_ID, 520101),
    (520121, "第一节 化学反应与能量变化", "chem_r2_ch06_s01", 1, BOOK_ID, 520102),
    (520122, "第二节 化学反应的速率与限度", "chem_r2_ch06_s02", 2, BOOK_ID, 520102),
    (520131, "第一节 认识有机化合物", "chem_r2_ch07_s01", 1, BOOK_ID, 520103),
    (520132, "第二节 乙烯与有机高分子材料", "chem_r2_ch07_s02", 2, BOOK_ID, 520103),
    (520133, "第三节 乙醇与乙酸", "chem_r2_ch07_s03", 3, BOOK_ID, 520103),
    (520134, "第四节 基本营养物质", "chem_r2_ch07_s04", 4, BOOK_ID, 520103),
    (520141, "第一节 自然资源的开发利用", "chem_r2_ch08_s01", 1, BOOK_ID, 520104),
    (520142, "第二节 化学品的合理使用", "chem_r2_ch08_s02", 2, BOOK_ID, 520104),
    (520143, "第三节 环境保护与绿色化学", "chem_r2_ch08_s03", 3, BOOK_ID, 520104),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (520001, "chem_r2_nonmetal_industry", "非金属元素化工", 1, SUBJECT, None),
    (520002, "chem_r2_energy_rate", "反应能量与限度", 2, SUBJECT, None),
    (520003, "chem_r2_organic_intro", "有机化合物入门", 3, SUBJECT, None),
    (520004, "chem_r2_sustainable", "化学与可持续发展", 4, SUBJECT, None),

    (520005, "chem_r2_ch05", "化工生产中的重要非金属元素", 1, SUBJECT, 520001),
    (520006, "chem_r2_ch06", "化学反应与能量", 1, SUBJECT, 520002),
    (520007, "chem_r2_ch07", "有机化合物", 1, SUBJECT, 520003),
    (520008, "chem_r2_ch08", "化学与可持续发展", 1, SUBJECT, 520004),

    (520009, "chem_r2_s_sulfur", "硫及其化合物", 1, SUBJECT, 520005),
    (520010, "chem_r2_s_nitrogen", "氮及其化合物", 2, SUBJECT, 520005),
    (520011, "chem_r2_s_inorganic_material", "无机非金属材料", 3, SUBJECT, 520005),
    (520012, "chem_r2_s_energy_change", "化学反应与能量变化", 1, SUBJECT, 520006),
    (520013, "chem_r2_s_rate_limit", "化学反应的速率与限度", 2, SUBJECT, 520006),
    (520014, "chem_r2_s_organic_basic", "认识有机化合物", 1, SUBJECT, 520007),
    (520015, "chem_r2_s_ethylene_polymer", "乙烯与有机高分子材料", 2, SUBJECT, 520007),
    (520016, "chem_r2_s_ethanol_acetic", "乙醇与乙酸", 3, SUBJECT, 520007),
    (520017, "chem_r2_s_nutrients", "基本营养物质", 4, SUBJECT, 520007),
    (520018, "chem_r2_s_resources", "自然资源的开发利用", 1, SUBJECT, 520008),
    (520019, "chem_r2_s_chemical_use", "化学品的合理使用", 2, SUBJECT, 520008),
    (520020, "chem_r2_s_green_chemistry", "环境保护与绿色化学", 3, SUBJECT, 520008),

    (520021, "chem_r2_sulfur_property", "硫的存在与物理性质", 1, SUBJECT, 520009),
    (520022, "chem_r2_sulfur_reaction", "硫的化学性质与氧化还原", 2, SUBJECT, 520009),
    (520023, "chem_r2_so2_acidic", "二氧化硫的物理性质与酸性氧化物通性", 3, SUBJECT, 520009),
    (520024, "chem_r2_so2_bleach_reduce", "二氧化硫的漂白性与还原性", 4, SUBJECT, 520009),
    (520025, "chem_r2_so2_prepare_test", "二氧化硫的实验室制法与检验", 5, SUBJECT, 520009),
    (520026, "chem_r2_contact_process", "接触法制硫酸与三氧化硫的吸收", 6, SUBJECT, 520009),
    (520027, "chem_r2_conc_sulfuric_property", "浓硫酸的吸水性、脱水性与强氧化性", 7, SUBJECT, 520009),
    (520028, "chem_r2_conc_sulfuric_reaction", "浓硫酸与铜、碳的反应及产物检验", 8, SUBJECT, 520009),
    (520029, "chem_r2_sulfate_test", "硫酸根离子的检验与常见硫酸盐", 9, SUBJECT, 520009),
    (520030, "chem_r2_sulfur_network_acid_rain", "硫的价态转化与酸雨防治", 10, SUBJECT, 520009),

    (520031, "chem_r2_nitrogen_structure", "氮气的分子结构与化学性质", 1, SUBJECT, 520010),
    (520032, "chem_r2_nitrogen_fixation", "氮的固定与人工固氮途径", 2, SUBJECT, 520010),
    (520033, "chem_r2_no_no2_property", "一氧化氮与二氧化氮的性质", 3, SUBJECT, 520010),
    (520034, "chem_r2_nox_water_calc", "氮氧化物溶于水的计算", 4, SUBJECT, 520010),
    (520035, "chem_r2_ammonia_fountain", "氨的物理性质与喷泉实验", 5, SUBJECT, 520010),
    (520036, "chem_r2_ammonia_water_acid", "氨与水、酸的反应及氨水成分", 6, SUBJECT, 520010),
    (520037, "chem_r2_ammonia_catalytic_oxidation", "氨的催化氧化", 7, SUBJECT, 520010),
    (520038, "chem_r2_ammonia_prepare", "氨的实验室制法", 8, SUBJECT, 520010),
    (520039, "chem_r2_ammonium_salt", "铵盐的性质与铵根离子检验", 9, SUBJECT, 520010),
    (520040, "chem_r2_nitric_property", "硝酸的物理性质与强氧化性", 10, SUBJECT, 520010),
    (520041, "chem_r2_nitric_metal_calc", "硝酸与金属反应的计算", 11, SUBJECT, 520010),
    (520042, "chem_r2_nitrogen_network", "氮及其化合物的转化网络", 12, SUBJECT, 520010),

    (520043, "chem_r2_silicate_products", "硅酸盐产品与水泥、玻璃、陶瓷", 1, SUBJECT, 520011),
    (520044, "chem_r2_silicon_prepare", "硅单质的性质与工业制备", 2, SUBJECT, 520011),
    (520045, "chem_r2_sio2_property", "二氧化硅的性质与用途", 3, SUBJECT, 520011),
    (520046, "chem_r2_silicic_acid", "硅酸与硅酸钠的性质", 4, SUBJECT, 520011),
    (520047, "chem_r2_new_inorganic_material", "新型无机非金属材料", 5, SUBJECT, 520011),

    (520048, "chem_r2_energy_essence", "化学反应中能量变化的本质", 1, SUBJECT, 520012),
    (520049, "chem_r2_exo_endo", "放热反应与吸热反应的判断", 2, SUBJECT, 520012),
    (520050, "chem_r2_reaction_heat", "反应热与化学能、热能的转化", 3, SUBJECT, 520012),
    (520051, "chem_r2_neutralization_heat", "中和反应反应热的测定", 4, SUBJECT, 520012),
    (520052, "chem_r2_galvanic_principle", "原电池的工作原理", 5, SUBJECT, 520012),
    (520053, "chem_r2_galvanic_condition", "原电池的构成条件与电极判断", 6, SUBJECT, 520012),
    (520054, "chem_r2_electrode_equation", "电极反应式与电池总反应式", 7, SUBJECT, 520012),
    (520055, "chem_r2_chemical_power", "常见化学电源及其应用", 8, SUBJECT, 520012),

    (520056, "chem_r2_rate_definition", "化学反应速率的表示与计算", 1, SUBJECT, 520013),
    (520057, "chem_r2_rate_ratio", "反应速率之比与化学计量数之比", 2, SUBJECT, 520013),
    (520058, "chem_r2_rate_concentration", "浓度与压强对反应速率的影响", 3, SUBJECT, 520013),
    (520059, "chem_r2_rate_temperature", "温度与催化剂对反应速率的影响", 4, SUBJECT, 520013),
    (520060, "chem_r2_rate_control_variable", "控制变量法探究速率影响因素", 5, SUBJECT, 520013),
    (520061, "chem_r2_reversible_equilibrium", "可逆反应与化学平衡状态", 6, SUBJECT, 520013),
    (520062, "chem_r2_equilibrium_judge", "化学平衡状态的判断标志", 7, SUBJECT, 520013),
    (520063, "chem_r2_limit_control", "化学反应限度与条件控制", 8, SUBJECT, 520013),

    (520064, "chem_r2_organic_feature", "有机化合物的特点与碳原子成键", 1, SUBJECT, 520014),
    (520065, "chem_r2_methane_structure", "甲烷的分子结构与正四面体", 2, SUBJECT, 520014),
    (520066, "chem_r2_methane_combustion", "甲烷的物理性质、燃烧与检验", 3, SUBJECT, 520014),
    (520067, "chem_r2_methane_substitution", "甲烷的取代反应", 4, SUBJECT, 520014),
    (520068, "chem_r2_alkane_structure", "烷烃的结构与通式", 5, SUBJECT, 520014),
    (520069, "chem_r2_isomer", "同分异构现象与同分异构体", 6, SUBJECT, 520014),
    (520070, "chem_r2_organic_formula", "有机化合物结构的表示与命名", 7, SUBJECT, 520014),

    (520071, "chem_r2_ethylene_structure", "乙烯的分子结构与碳碳双键", 1, SUBJECT, 520015),
    (520072, "chem_r2_ethylene_addition", "乙烯的加成反应", 2, SUBJECT, 520015),
    (520073, "chem_r2_ethylene_oxidation", "乙烯的氧化反应与用途", 3, SUBJECT, 520015),
    (520074, "chem_r2_ethylene_prepare", "乙烯的实验室制法", 4, SUBJECT, 520015),
    (520075, "chem_r2_addition_polymer", "加成聚合反应与聚乙烯", 5, SUBJECT, 520015),
    (520076, "chem_r2_polymer_class", "有机高分子材料的分类与结构", 6, SUBJECT, 520015),
    (520077, "chem_r2_polymer_application", "常见高分子材料与白色污染", 7, SUBJECT, 520015),

    (520078, "chem_r2_ethanol_structure", "乙醇的分子结构与物理性质", 1, SUBJECT, 520016),
    (520079, "chem_r2_ethanol_sodium", "乙醇与钠的反应及燃烧", 2, SUBJECT, 520016),
    (520080, "chem_r2_ethanol_catalytic", "乙醇的催化氧化", 3, SUBJECT, 520016),
    (520081, "chem_r2_ethanol_dehydration", "乙醇的脱水反应与强氧化剂氧化", 4, SUBJECT, 520016),
    (520082, "chem_r2_acetic_structure", "乙酸的分子结构与酸性", 5, SUBJECT, 520016),
    (520083, "chem_r2_esterification", "酯化反应的原理与实验", 6, SUBJECT, 520016),
    (520084, "chem_r2_ester_property", "酯的性质、水解与官能团反应类型", 7, SUBJECT, 520016),

    (520085, "chem_r2_sugar", "糖类的组成、分类与性质", 1, SUBJECT, 520017),
    (520086, "chem_r2_glucose_test", "葡萄糖的还原性与淀粉检验", 2, SUBJECT, 520017),
    (520087, "chem_r2_oil_fat", "油脂的组成、性质与皂化", 3, SUBJECT, 520017),
    (520088, "chem_r2_protein", "蛋白质的组成、变性、盐析与检验", 4, SUBJECT, 520017),
    (520089, "chem_r2_nutrient_balance", "基本营养物质的检验与合理膳食", 5, SUBJECT, 520017),

    (520090, "chem_r2_metal_smelting", "金属矿物的开发利用与冶炼", 1, SUBJECT, 520018),
    (520091, "chem_r2_sea_water", "海水资源的综合利用", 2, SUBJECT, 520018),
    (520092, "chem_r2_fossil_fuel", "煤、石油、天然气的综合利用", 3, SUBJECT, 520018),
    (520093, "chem_r2_biomass_energy", "生物质资源与新能源开发", 4, SUBJECT, 520018),

    (520094, "chem_r2_fertilizer_pesticide", "化肥、农药的合理施用", 1, SUBJECT, 520019),
    (520095, "chem_r2_medicine", "合理用药与药物合成", 2, SUBJECT, 520019),
    (520096, "chem_r2_food_additive", "食品添加剂与食品安全", 3, SUBJECT, 520019),

    (520097, "chem_r2_pollution", "环境污染的来源与危害", 1, SUBJECT, 520020),
    (520098, "chem_r2_pollution_control", "污染治理与清洁生产", 2, SUBJECT, 520020),
    (520099, "chem_r2_green_chemistry", "绿色化学与原子经济性", 3, SUBJECT, 520020),
)

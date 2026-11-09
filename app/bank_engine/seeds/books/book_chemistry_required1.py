"""人教版（2019）高中化学必修第一册：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 5
G10 = 10
BOOK_ID = 5101

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中化学必修第一册",
    "chem_r1",
    1,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (510101, "第一章 物质及其变化", "chem_r1_ch01", 1, BOOK_ID, None),
    (510102, "第二章 海水中的重要元素——钠和氯", "chem_r1_ch02", 2, BOOK_ID, None),
    (510103, "第三章 铁 金属材料", "chem_r1_ch03", 3, BOOK_ID, None),
    (510104, "第四章 物质结构 元素周期律", "chem_r1_ch04", 4, BOOK_ID, None),
    (510111, "第一节 物质的分类及转化", "chem_r1_ch01_s01", 1, BOOK_ID, 510101),
    (510112, "第二节 离子反应", "chem_r1_ch01_s02", 2, BOOK_ID, 510101),
    (510113, "第三节 氧化还原反应", "chem_r1_ch01_s03", 3, BOOK_ID, 510101),
    (510121, "第一节 钠及其化合物", "chem_r1_ch02_s01", 1, BOOK_ID, 510102),
    (510122, "第二节 氯及其化合物", "chem_r1_ch02_s02", 2, BOOK_ID, 510102),
    (510123, "第三节 物质的量", "chem_r1_ch02_s03", 3, BOOK_ID, 510102),
    (510131, "第一节 铁及其化合物", "chem_r1_ch03_s01", 1, BOOK_ID, 510103),
    (510132, "第二节 金属材料", "chem_r1_ch03_s02", 2, BOOK_ID, 510103),
    (510141, "第一节 原子结构与元素周期表", "chem_r1_ch04_s01", 1, BOOK_ID, 510104),
    (510142, "第二节 元素周期律", "chem_r1_ch04_s02", 2, BOOK_ID, 510104),
    (510143, "第三节 化学键", "chem_r1_ch04_s03", 3, BOOK_ID, 510104),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    (510001, "chem_r1_matter_reaction", "物质分类与反应原理", 1, SUBJECT, G10, None),
    (510002, "chem_r1_sodium_chlorine_mole", "钠氯与化学计量", 2, SUBJECT, G10, None),
    (510003, "chem_r1_iron_metal", "铁与金属材料", 3, SUBJECT, G10, None),
    (510004, "chem_r1_structure_periodic", "物质结构与周期律", 4, SUBJECT, G10, None),

    (510005, "chem_r1_ch01", "物质及其变化", 1, SUBJECT, G10, 510001),
    (510006, "chem_r1_ch02", "海水中的重要元素——钠和氯", 1, SUBJECT, G10, 510002),
    (510007, "chem_r1_ch03", "铁 金属材料", 1, SUBJECT, G10, 510003),
    (510008, "chem_r1_ch04", "物质结构 元素周期律", 1, SUBJECT, G10, 510004),

    (510009, "chem_r1_s_classification", "物质的分类及转化", 1, SUBJECT, G10, 510005),
    (510010, "chem_r1_s_ion_reaction", "离子反应", 2, SUBJECT, G10, 510005),
    (510011, "chem_r1_s_redox", "氧化还原反应", 3, SUBJECT, G10, 510005),
    (510012, "chem_r1_s_sodium", "钠及其化合物", 1, SUBJECT, G10, 510006),
    (510013, "chem_r1_s_chlorine", "氯及其化合物", 2, SUBJECT, G10, 510006),
    (510014, "chem_r1_s_mole", "物质的量", 3, SUBJECT, G10, 510006),
    (510015, "chem_r1_s_iron", "铁及其化合物", 1, SUBJECT, G10, 510007),
    (510016, "chem_r1_s_metal_material", "金属材料", 2, SUBJECT, G10, 510007),
    (510017, "chem_r1_s_atomic_table", "原子结构与元素周期表", 1, SUBJECT, G10, 510008),
    (510018, "chem_r1_s_periodic_law", "元素周期律", 2, SUBJECT, G10, 510008),
    (510019, "chem_r1_s_chemical_bond", "化学键", 3, SUBJECT, G10, 510008),

    (510021, "chem_r1_class_tree_cross", "树状分类法与交叉分类法", 1, SUBJECT, G10, 510009),
    (510022, "chem_r1_pure_mixture", "纯净物与混合物的判断", 2, SUBJECT, G10, 510009),
    (510023, "chem_r1_acidic_basic_oxide", "酸性氧化物与碱性氧化物的性质", 3, SUBJECT, G10, 510009),
    (510024, "chem_r1_dispersion_system", "分散系及其分类依据", 4, SUBJECT, G10, 510009),
    (510025, "chem_r1_colloid_tyndall", "胶体的丁达尔效应与聚沉", 5, SUBJECT, G10, 510009),
    (510026, "chem_r1_feoh3_colloid", "氢氧化铁胶体的制备", 6, SUBJECT, G10, 510009),
    (510027, "chem_r1_transformation_types", "物质转化关系与反应类型", 7, SUBJECT, G10, 510009),
    (510028, "chem_r1_allotrope_identity", "同素异形体与同种物质辨析", 8, SUBJECT, G10, 510009),

    (510029, "chem_r1_electrolyte_judge", "电解质与非电解质的判断", 1, SUBJECT, G10, 510010),
    (510030, "chem_r1_strong_weak_electrolyte", "强电解质与弱电解质", 2, SUBJECT, G10, 510010),
    (510031, "chem_r1_ionization_equation", "电离方程式的书写", 3, SUBJECT, G10, 510010),
    (510032, "chem_r1_ion_reaction_condition", "离子反应发生的条件", 4, SUBJECT, G10, 510010),
    (510033, "chem_r1_ion_equation_split", "离子方程式书写中的拆分原则", 5, SUBJECT, G10, 510010),
    (510034, "chem_r1_ion_equation_judge", "离子方程式正误判断", 6, SUBJECT, G10, 510010),
    (510035, "chem_r1_ion_coexistence", "离子共存与隐含条件", 7, SUBJECT, G10, 510010),
    (510036, "chem_r1_ion_purify_test", "离子反应在除杂与检验中的应用", 8, SUBJECT, G10, 510010),

    (510037, "chem_r1_redox_essence", "氧化还原反应的本质与特征", 1, SUBJECT, G10, 510011),
    (510038, "chem_r1_oxidant_reductant", "氧化剂与还原剂及其产物判断", 2, SUBJECT, G10, 510011),
    (510039, "chem_r1_electron_bridge", "双线桥与单线桥表示电子转移", 3, SUBJECT, G10, 510011),
    (510040, "chem_r1_redox_strength", "氧化性与还原性强弱比较", 4, SUBJECT, G10, 510011),
    (510041, "chem_r1_redox_balance_valence", "化合价升降法配平", 5, SUBJECT, G10, 510011),
    (510042, "chem_r1_redox_balance_ion", "缺项配平与离子型氧化还原方程式", 6, SUBJECT, G10, 510011),
    (510043, "chem_r1_electron_conservation", "电子守恒法的计算", 7, SUBJECT, G10, 510011),
    (510044, "chem_r1_common_redox_agents", "常见氧化剂与还原剂归纳", 8, SUBJECT, G10, 510011),

    (510045, "chem_r1_sodium_property", "钠的物理性质与保存", 1, SUBJECT, G10, 510012),
    (510046, "chem_r1_sodium_reactions", "钠与氧气、水的反应", 2, SUBJECT, G10, 510012),
    (510047, "chem_r1_sodium_oxides", "氧化钠与过氧化钠的比较", 3, SUBJECT, G10, 510012),
    (510048, "chem_r1_sodium_peroxide", "过氧化钠的强氧化性与用途", 4, SUBJECT, G10, 510012),
    (510049, "chem_r1_sodium_carbonates", "碳酸钠与碳酸氢钠的性质比较", 5, SUBJECT, G10, 510012),
    (510050, "chem_r1_carbonate_identify", "碳酸钠与碳酸氢钠的鉴别与转化", 6, SUBJECT, G10, 510012),
    (510051, "chem_r1_flame_test", "焰色试验与钠钾元素检验", 7, SUBJECT, G10, 510012),
    (510052, "chem_r1_sodium_network", "钠及其化合物的转化网络", 8, SUBJECT, G10, 510012),

    (510053, "chem_r1_chlorine_prepare", "氯气的物理性质与实验室制法", 1, SUBJECT, G10, 510013),
    (510054, "chem_r1_chlorine_reactions", "氯气与金属、非金属的反应", 2, SUBJECT, G10, 510013),
    (510055, "chem_r1_chlorine_water_alkali", "氯气与水和碱的反应", 3, SUBJECT, G10, 510013),
    (510056, "chem_r1_chlorine_water", "氯水的成分与性质", 4, SUBJECT, G10, 510013),
    (510057, "chem_r1_hypochlorous_acid", "次氯酸的性质与漂白原理", 5, SUBJECT, G10, 510013),
    (510058, "chem_r1_bleaching_powder", "漂白粉的制备、成分与失效", 6, SUBJECT, G10, 510013),
    (510059, "chem_r1_chloride_test", "氯离子的检验", 7, SUBJECT, G10, 510013),
    (510060, "chem_r1_chlorine_leak", "氯气泄漏的应急处理", 8, SUBJECT, G10, 510013),

    (510061, "chem_r1_amount_unit", "物质的量的含义与单位", 1, SUBJECT, G10, 510014),
    (510062, "chem_r1_avogadro_number", "阿伏加德罗常数与微粒数计算", 2, SUBJECT, G10, 510014),
    (510063, "chem_r1_molar_mass", "摩尔质量与质量换算", 3, SUBJECT, G10, 510014),
    (510064, "chem_r1_molar_volume", "气体摩尔体积与标准状况", 4, SUBJECT, G10, 510014),
    (510065, "chem_r1_avogadro_law", "阿伏加德罗定律及其推论", 5, SUBJECT, G10, 510014),
    (510066, "chem_r1_molar_concentration", "物质的量浓度的定义与计算", 6, SUBJECT, G10, 510014),
    (510067, "chem_r1_solution_preparation", "一定物质的量浓度溶液的配制", 7, SUBJECT, G10, 510014),
    (510068, "chem_r1_preparation_error", "溶液配制的误差分析", 8, SUBJECT, G10, 510014),
    (510069, "chem_r1_equation_stoichiometry", "物质的量在化学方程式计算中的应用", 9, SUBJECT, G10, 510014),

    (510070, "chem_r1_iron_occurrence", "铁的存在、物理性质与冶炼", 1, SUBJECT, G10, 510015),
    (510071, "chem_r1_iron_oxygen_steam", "铁与氧气、水蒸气的反应", 2, SUBJECT, G10, 510015),
    (510072, "chem_r1_iron_acid_salt", "铁与酸、盐溶液的反应", 3, SUBJECT, G10, 510015),
    (510073, "chem_r1_iron_ion_test", "亚铁离子与铁离子的检验", 4, SUBJECT, G10, 510015),
    (510074, "chem_r1_iron_hydroxides", "氢氧化亚铁与氢氧化铁的制备与性质", 5, SUBJECT, G10, 510015),
    (510075, "chem_r1_iron_ion_conversion", "铁离子与亚铁离子的相互转化", 6, SUBJECT, G10, 510015),
    (510076, "chem_r1_iron_network", "铁及其化合物的转化网络", 7, SUBJECT, G10, 510015),
    (510077, "chem_r1_aluminum_property", "铝的化学性质", 8, SUBJECT, G10, 510015),
    (510078, "chem_r1_aluminum_amphoteric", "氧化铝与氢氧化铝的两性", 9, SUBJECT, G10, 510015),
    (510079, "chem_r1_thermit_reaction", "铝热反应及其应用", 10, SUBJECT, G10, 510015),

    (510080, "chem_r1_alloy_structure", "合金的结构与性质", 1, SUBJECT, G10, 510016),
    (510081, "chem_r1_cast_iron_steel", "生铁与钢的比较", 2, SUBJECT, G10, 510016),
    (510082, "chem_r1_aluminum_alloy", "铝及铝合金的性能与用途", 3, SUBJECT, G10, 510016),
    (510083, "chem_r1_copper_new_alloy", "铜合金与新型合金", 4, SUBJECT, G10, 510016),
    (510084, "chem_r1_metal_selection", "金属材料的选用与防护", 5, SUBJECT, G10, 510016),

    (510085, "chem_r1_atom_composition", "原子的构成与质量数", 1, SUBJECT, G10, 510017),
    (510086, "chem_r1_isotope", "核素、同位素与相对原子质量", 2, SUBJECT, G10, 510017),
    (510087, "chem_r1_electron_config", "核外电子排布规律", 3, SUBJECT, G10, 510017),
    (510088, "chem_r1_periodic_table_structure", "元素周期表的结构", 4, SUBJECT, G10, 510017),
    (510089, "chem_r1_alkali_metal_trend", "碱金属元素性质的递变", 5, SUBJECT, G10, 510017),
    (510090, "chem_r1_halogen_trend", "卤族元素性质的递变", 6, SUBJECT, G10, 510017),

    (510091, "chem_r1_periodic_law_content", "元素周期律的内容与实质", 1, SUBJECT, G10, 510018),
    (510092, "chem_r1_radius_trend", "原子半径与离子半径的递变", 2, SUBJECT, G10, 510018),
    (510093, "chem_r1_metal_nonmetal_judge", "金属性与非金属性的判断依据", 3, SUBJECT, G10, 510018),
    (510094, "chem_r1_valence_rule", "最高正价与最低负价规律", 4, SUBJECT, G10, 510018),
    (510095, "chem_r1_position_structure_property", "位—构—性关系及其应用", 5, SUBJECT, G10, 510018),

    (510096, "chem_r1_ionic_bond", "离子键与离子化合物", 1, SUBJECT, G10, 510019),
    (510097, "chem_r1_covalent_bond", "共价键与共价化合物", 2, SUBJECT, G10, 510019),
    (510098, "chem_r1_polar_bond", "极性键与非极性键", 3, SUBJECT, G10, 510019),
    (510099, "chem_r1_electron_formula", "电子式的书写", 4, SUBJECT, G10, 510019),
)

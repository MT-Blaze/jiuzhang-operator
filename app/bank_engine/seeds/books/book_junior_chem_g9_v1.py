"""人教版初中化学九年级上册：第一单元—第七单元目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 5
G9 = 9
BOOK_ID = 1333

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版九年级化学上册",
    "jchem_g9a",
    33,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133301, "第一单元 走进化学世界", "jchem_g9a_u1", 1, BOOK_ID, None),
    (133311, "课题1 物质的变化和性质", "jchem_g9a_u1_s01", 1, BOOK_ID, 133301),
    (133312, "课题2 化学是一门以实验为基础的科学", "jchem_g9a_u1_s02", 2, BOOK_ID, 133301),
    (133313, "课题3 走进化学实验室", "jchem_g9a_u1_s03", 3, BOOK_ID, 133301),

    (133302, "第二单元 我们周围的空气", "jchem_g9a_u2", 2, BOOK_ID, None),
    (133314, "课题1 空气", "jchem_g9a_u2_s01", 1, BOOK_ID, 133302),
    (133315, "课题2 氧气", "jchem_g9a_u2_s02", 2, BOOK_ID, 133302),
    (133316, "课题3 制取氧气", "jchem_g9a_u2_s03", 3, BOOK_ID, 133302),

    (133303, "第三单元 物质构成的奥秘", "jchem_g9a_u3", 3, BOOK_ID, None),
    (133317, "课题1 分子和原子", "jchem_g9a_u3_s01", 1, BOOK_ID, 133303),
    (133318, "课题2 原子的结构", "jchem_g9a_u3_s02", 2, BOOK_ID, 133303),
    (133319, "课题3 元素", "jchem_g9a_u3_s03", 3, BOOK_ID, 133303),

    (133304, "第四单元 自然界的水", "jchem_g9a_u4", 4, BOOK_ID, None),
    (133320, "课题1 爱护水资源", "jchem_g9a_u4_s01", 1, BOOK_ID, 133304),
    (133321, "课题2 水的净化", "jchem_g9a_u4_s02", 2, BOOK_ID, 133304),
    (133322, "课题3 水的组成", "jchem_g9a_u4_s03", 3, BOOK_ID, 133304),
    (133323, "课题4 化学式与化合价", "jchem_g9a_u4_s04", 4, BOOK_ID, 133304),

    (133305, "第五单元 化学方程式", "jchem_g9a_u5", 5, BOOK_ID, None),
    (133324, "课题1 质量守恒定律", "jchem_g9a_u5_s01", 1, BOOK_ID, 133305),
    (133325, "课题2 如何正确书写化学方程式", "jchem_g9a_u5_s02", 2, BOOK_ID, 133305),
    (133326, "课题3 利用化学方程式的简单计算", "jchem_g9a_u5_s03", 3, BOOK_ID, 133305),

    (133306, "第六单元 碳和碳的氧化物", "jchem_g9a_u6", 6, BOOK_ID, None),
    (133327, "课题1 金刚石、石墨和C60", "jchem_g9a_u6_s01", 1, BOOK_ID, 133306),
    (133328, "课题2 二氧化碳制取的研究", "jchem_g9a_u6_s02", 2, BOOK_ID, 133306),
    (133329, "课题3 二氧化碳和一氧化碳", "jchem_g9a_u6_s03", 3, BOOK_ID, 133306),

    (133307, "第七单元 燃料及其利用", "jchem_g9a_u7", 7, BOOK_ID, None),
    (133330, "课题1 燃烧和灭火", "jchem_g9a_u7_s01", 1, BOOK_ID, 133307),
    (133331, "课题2 燃料的合理利用与开发", "jchem_g9a_u7_s02", 2, BOOK_ID, 133307),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 233001-233007 为册域层，233008-233072 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (233001, "jchem_g9a_domain_u1", "初中九上·第一单元 走进化学世界：物质变化、科学探究与实验基本操作", 1, SUBJECT, G9, None),
    (233002, "jchem_g9a_domain_u2", "初中九上·第二单元 我们周围的空气：空气组成、氧气性质与制取", 2, SUBJECT, G9, None),
    (233003, "jchem_g9a_domain_u3", "初中九上·第三单元 物质构成的奥秘：分子原子、原子结构与元素", 3, SUBJECT, G9, None),
    (233004, "jchem_g9a_domain_u4", "初中九上·第四单元 自然界的水：水资源、净化、水的组成与化学式", 4, SUBJECT, G9, None),
    (233005, "jchem_g9a_domain_u5", "初中九上·第五单元 化学方程式：质量守恒定律与化学方程式计算", 5, SUBJECT, G9, None),
    (233006, "jchem_g9a_domain_u6", "初中九上·第六单元 碳和碳的氧化物：碳单质、二氧化碳与一氧化碳", 6, SUBJECT, G9, None),
    (233007, "jchem_g9a_domain_u7", "初中九上·第七单元 燃料及其利用：燃烧条件、灭火与能源利用", 7, SUBJECT, G9, None),

    # 第一单元 走进化学世界
    (233008, "jchem_g9a_u1_change_type", "物理变化与化学变化的本质区别及实例判断", 1, SUBJECT, G9, 233001),
    (233009, "jchem_g9a_u1_change_energy", "化学变化中伴随的现象观察与能量变化", 2, SUBJECT, G9, 233001),
    (233010, "jchem_g9a_u1_inquiry", "科学探究的基本环节与实验现象的规范描述", 3, SUBJECT, G9, 233001),
    (233011, "jchem_g9a_u1_candle", "蜡烛燃烧实验：现象、产物检验与白烟成分", 4, SUBJECT, G9, 233001),
    (233012, "jchem_g9a_u1_breath", "吸入空气与呼出气体成分差异的探究方法", 5, SUBJECT, G9, 233001),
    (233013, "jchem_g9a_u1_instruments", "常用化学仪器的识别、用途与使用禁忌", 6, SUBJECT, G9, 233001),
    (233014, "jchem_g9a_u1_operations", "药品的取用、加热与仪器洗涤操作规范", 7, SUBJECT, G9, 233001),
    (233015, "jchem_g9a_u1_safety", "实验安全规则、意外事故处理与废液处置", 8, SUBJECT, G9, 233001),

    # 第二单元 我们周围的空气
    (233016, "jchem_g9a_u2_air_composition", "空气的组成及各成分的体积分数", 1, SUBJECT, G9, 233002),
    (233017, "jchem_g9a_u2_oxygen_content_exp", "测定空气中氧气含量的实验原理、现象与误差分析", 2, SUBJECT, G9, 233002),
    (233018, "jchem_g9a_u2_air_pollution", "空气污染物的来源、危害与防治措施", 3, SUBJECT, G9, 233002),
    (233019, "jchem_g9a_u2_oxygen_property", "氧气的物理性质、检验方法与用途", 4, SUBJECT, G9, 233002),
    (233020, "jchem_g9a_u2_combustion_phenomena", "硫、木炭、铁丝在氧气中燃烧的现象与产物", 5, SUBJECT, G9, 233002),
    (233021, "jchem_g9a_u2_oxidation", "化合反应、氧化反应与缓慢氧化的辨析", 6, SUBJECT, G9, 233002),
    (233022, "jchem_g9a_u2_kmno4_prepare", "加热高锰酸钾制取氧气的装置、步骤与注意事项", 7, SUBJECT, G9, 233002),
    (233023, "jchem_g9a_u2_h2o2_catalyst", "过氧化氢分解制氧气与催化剂、催化作用", 8, SUBJECT, G9, 233002),
    (233024, "jchem_g9a_u2_collection", "排水法与排空气法收集气体的选择与验满", 9, SUBJECT, G9, 233002),
    (233025, "jchem_g9a_u2_industry_oxygen", "工业分离液态空气制氧气的原理与过程", 10, SUBJECT, G9, 233002),

    # 第三单元 物质构成的奥秘
    (233026, "jchem_g9a_u3_particles", "物质由微观粒子构成及粒子的基本性质", 1, SUBJECT, G9, 233003),
    (233027, "jchem_g9a_u3_molecular_theory", "用分子、原子观点解释物理变化与化学变化", 2, SUBJECT, G9, 233003),
    (233028, "jchem_g9a_u3_atom_structure", "原子的构成及质子数、中子数、核外电子数的关系", 3, SUBJECT, G9, 233003),
    (233029, "jchem_g9a_u3_electron_shell", "核外电子分层排布与原子结构示意图的书写", 4, SUBJECT, G9, 233003),
    (233030, "jchem_g9a_u3_ion", "离子的形成、离子符号及阴、阳离子的判断", 5, SUBJECT, G9, 233003),
    (233031, "jchem_g9a_u3_relative_atomic_mass", "相对原子质量的概念、计算与应用", 6, SUBJECT, G9, 233003),
    (233032, "jchem_g9a_u3_element", "元素的概念、元素符号的书写与意义", 7, SUBJECT, G9, 233003),
    (233033, "jchem_g9a_u3_periodic_table", "元素周期表的结构与单元格信息的读取", 8, SUBJECT, G9, 233003),
    (233034, "jchem_g9a_u3_substance_class", "单质、化合物、氧化物与混合物、纯净物的分类", 9, SUBJECT, G9, 233003),
    (233035, "jchem_g9a_u3_formula_write", "化学式的书写、读法及化学式中数字的意义", 10, SUBJECT, G9, 233003),

    # 第四单元 自然界的水
    (233036, "jchem_g9a_u4_water_resource", "水资源状况与爱护水资源的措施", 1, SUBJECT, G9, 233004),
    (233037, "jchem_g9a_u4_purification_flow", "自来水厂净水流程与沉淀、过滤、吸附、蒸馏", 2, SUBJECT, G9, 233004),
    (233038, "jchem_g9a_u4_filtration", "过滤操作的“一贴二低三靠”与仪器选用", 3, SUBJECT, G9, 233004),
    (233039, "jchem_g9a_u4_hard_soft_water", "硬水与软水的鉴别、危害与软化方法", 4, SUBJECT, G9, 233004),
    (233040, "jchem_g9a_u4_electrolysis", "电解水实验的现象、产物检验与结论", 5, SUBJECT, G9, 233004),
    (233041, "jchem_g9a_u4_water_composition", "水的组成推导与水的化学式", 6, SUBJECT, G9, 233004),
    (233042, "jchem_g9a_u4_valence", "化合价的原则与常见元素、原子团的化合价", 7, SUBJECT, G9, 233004),
    (233043, "jchem_g9a_u4_formula_by_valence", "根据化合价书写并检验化学式", 8, SUBJECT, G9, 233004),
    (233044, "jchem_g9a_u4_relative_mass_calc", "相对分子质量、元素质量比与元素质量分数的计算", 9, SUBJECT, G9, 233004),
    (233045, "jchem_g9a_u4_formula_meaning", "化学式的宏观、微观意义与物质的定量表示", 10, SUBJECT, G9, 233004),

    # 第五单元 化学方程式
    (233046, "jchem_g9a_u5_conservation_law", "质量守恒定律的内容与微观解释", 1, SUBJECT, G9, 233005),
    (233047, "jchem_g9a_u5_conservation_exp", "质量守恒定律的实验验证、适用范围与常见误区", 2, SUBJECT, G9, 233005),
    (233048, "jchem_g9a_u5_equation_meaning", "化学方程式的意义、读法与提供的信息", 3, SUBJECT, G9, 233005),
    (233049, "jchem_g9a_u5_equation_write", "化学方程式的书写原则与最小公倍数法配平", 4, SUBJECT, G9, 233005),
    (233050, "jchem_g9a_u5_equation_condition", "化学方程式中的反应条件、↑↓与“点燃”标注", 5, SUBJECT, G9, 233005),
    (233051, "jchem_g9a_u5_mass_ratio", "化学方程式中各物质的质量比计算", 6, SUBJECT, G9, 233005),
    (233052, "jchem_g9a_u5_equation_calc_steps", "利用化学方程式进行简单计算的规范步骤", 7, SUBJECT, G9, 233005),
    (233053, "jchem_g9a_u5_impurity_calc", "含杂质与溶质质量分数问题的化学方程式计算", 8, SUBJECT, G9, 233005),

    # 第六单元 碳和碳的氧化物
    (233054, "jchem_g9a_u6_carbon_allotrope", "金刚石、石墨、C60 的结构差异与性质用途", 1, SUBJECT, G9, 233006),
    (233055, "jchem_g9a_u6_carbon_chemistry", "碳单质的可燃性与还原性", 2, SUBJECT, G9, 233006),
    (233056, "jchem_g9a_u6_carbon_reduce_cuo", "木炭还原氧化铜的实验装置、现象与注意事项", 3, SUBJECT, G9, 233006),
    (233057, "jchem_g9a_u6_co2_prepare", "实验室制取二氧化碳的药品选择、装置与检验", 4, SUBJECT, G9, 233006),
    (233058, "jchem_g9a_u6_co2_property", "二氧化碳的物理性质、溶解性与验满方法", 5, SUBJECT, G9, 233006),
    (233059, "jchem_g9a_u6_co2_reaction", "二氧化碳与水、澄清石灰水的反应及现象", 6, SUBJECT, G9, 233006),
    (233060, "jchem_g9a_u6_co2_environment", "二氧化碳对生活和环境的影响与温室效应", 7, SUBJECT, G9, 233006),
    (233061, "jchem_g9a_u6_co_toxicity", "一氧化碳的毒性、可燃性与还原性", 8, SUBJECT, G9, 233006),
    (233062, "jchem_g9a_u6_co_reduce_iron", "一氧化碳还原氧化铁的实验与尾气处理", 9, SUBJECT, G9, 233006),
    (233063, "jchem_g9a_u6_carbon_cycle", "碳循环与碳及其氧化物性质的综合对比", 10, SUBJECT, G9, 233006),

    # 第七单元 燃料及其利用
    (233064, "jchem_g9a_u7_combustion_condition", "燃烧的条件与探究燃烧条件的实验", 1, SUBJECT, G9, 233007),
    (233065, "jchem_g9a_u7_extinguishing", "灭火的原理与常见灭火方法的选择", 2, SUBJECT, G9, 233007),
    (233066, "jchem_g9a_u7_explosion", "爆炸的条件、安全防范与易燃易爆物标识", 3, SUBJECT, G9, 233007),
    (233067, "jchem_g9a_u7_fossil_fuel", "化石燃料的种类、组成与不可再生性", 4, SUBJECT, G9, 233007),
    (233068, "jchem_g9a_u7_complete_combustion", "燃料充分燃烧的条件与能源利用率", 5, SUBJECT, G9, 233007),
    (233069, "jchem_g9a_u7_energy_change", "化学反应中的能量变化与放热、吸热判断", 6, SUBJECT, G9, 233007),
    (233070, "jchem_g9a_u7_new_energy", "氢气等新能源的制取、优点与开发利用", 7, SUBJECT, G9, 233007),
    (233071, "jchem_g9a_u7_fuel_environment", "燃料使用对环境的影响与酸雨、尾气治理", 8, SUBJECT, G9, 233007),
    (233072, "jchem_g9a_u7_sustainable_energy", "能源的合理利用与可持续发展", 9, SUBJECT, G9, 233007),
)

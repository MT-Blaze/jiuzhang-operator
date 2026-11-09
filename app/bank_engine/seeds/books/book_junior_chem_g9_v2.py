"""人教版初中化学九年级下册：第八单元—第十二单元目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 5
G9 = 9
BOOK_ID = 1334

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版九年级化学下册",
    "jchem_g9b",
    34,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133401, "第八单元 金属和金属材料", "jchem_g9b_u8", 8, BOOK_ID, None),
    (133411, "课题1 金属材料", "jchem_g9b_u8_s01", 1, BOOK_ID, 133401),
    (133412, "课题2 金属的化学性质", "jchem_g9b_u8_s02", 2, BOOK_ID, 133401),
    (133413, "课题3 金属资源的利用和保护", "jchem_g9b_u8_s03", 3, BOOK_ID, 133401),

    (133402, "第九单元 溶液", "jchem_g9b_u9", 9, BOOK_ID, None),
    (133414, "课题1 溶液的形成", "jchem_g9b_u9_s01", 1, BOOK_ID, 133402),
    (133415, "课题2 溶解度", "jchem_g9b_u9_s02", 2, BOOK_ID, 133402),
    (133416, "课题3 溶液的浓度", "jchem_g9b_u9_s03", 3, BOOK_ID, 133402),

    (133403, "第十单元 酸和碱", "jchem_g9b_u10", 10, BOOK_ID, None),
    (133417, "课题1 常见的酸和碱", "jchem_g9b_u10_s01", 1, BOOK_ID, 133403),
    (133418, "课题2 酸和碱的中和反应", "jchem_g9b_u10_s02", 2, BOOK_ID, 133403),
    (133419, "课题3 溶液的酸碱度（pH）", "jchem_g9b_u10_s03", 3, BOOK_ID, 133403),

    (133404, "第十一单元 盐 化肥", "jchem_g9b_u11", 11, BOOK_ID, None),
    (133420, "课题1 生活中常见的盐", "jchem_g9b_u11_s01", 1, BOOK_ID, 133404),
    (133421, "课题2 化学肥料", "jchem_g9b_u11_s02", 2, BOOK_ID, 133404),

    (133405, "第十二单元 化学与生活", "jchem_g9b_u12", 12, BOOK_ID, None),
    (133422, "课题1 人类重要的营养物质", "jchem_g9b_u12_s01", 1, BOOK_ID, 133405),
    (133423, "课题2 化学元素与人体健康", "jchem_g9b_u12_s02", 2, BOOK_ID, 133405),
    (133424, "课题3 有机合成材料", "jchem_g9b_u12_s03", 3, BOOK_ID, 133405),
)

# id / code / name / sort_order / subject_id / parent_id
# 234001-234005 为册域层，234006-234065 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (234001, "jchem_g9b_domain_u8", "初中九下·第八单元 金属和金属材料：金属性质、活动性顺序与冶炼防腐", 1, SUBJECT, None),
    (234002, "jchem_g9b_domain_u9", "初中九下·第九单元 溶液：溶解现象、溶解度曲线与溶质质量分数", 2, SUBJECT, None),
    (234003, "jchem_g9b_domain_u10", "初中九下·第十单元 酸和碱：常见酸碱性质、中和反应与溶液 pH", 3, SUBJECT, None),
    (234004, "jchem_g9b_domain_u11", "初中九下·第十一单元 盐 化肥：常见盐的性质、复分解反应与化肥", 4, SUBJECT, None),
    (234005, "jchem_g9b_domain_u12", "初中九下·第十二单元 化学与生活：营养物质、必需元素与有机合成材料", 5, SUBJECT, None),

    # 第八单元 金属和金属材料
    (234006, "jchem_g9b_u8_metal_property", "金属的物理通性（导电、导热、延展性）与性质决定用途", 1, SUBJECT, 234001),
    (234007, "jchem_g9b_u8_alloy_concept", "合金的概念、组成特征及合金性能优于纯金属的原因", 2, SUBJECT, 234001),
    (234008, "jchem_g9b_u8_alloy_common", "生铁与钢的含碳量差异及黄铜、硬铝、钛合金的用途", 3, SUBJECT, 234001),
    (234009, "jchem_g9b_u8_metal_oxygen", "镁、铝、铁、铜与氧气反应的现象与难易比较", 4, SUBJECT, 234001),
    (234010, "jchem_g9b_u8_metal_acid", "金属与稀盐酸、稀硫酸反应的现象及氢气检验", 5, SUBJECT, 234001),
    (234011, "jchem_g9b_u8_metal_salt", "金属与盐溶液的置换反应及“前换后”规律", 6, SUBJECT, 234001),
    (234012, "jchem_g9b_u8_activity_series", "金属活动性顺序表的记忆、含义与反应能否发生的判断", 7, SUBJECT, 234001),
    (234013, "jchem_g9b_u8_displacement", "置换反应的定义、通式及与化合、分解反应的区分", 8, SUBJECT, 234001),
    (234014, "jchem_g9b_u8_activity_experiment", "探究金属活动性顺序的实验方案设计与现象推理", 9, SUBJECT, 234001),
    (234015, "jchem_g9b_u8_ore", "常见金属矿物（赤铁矿、磁铁矿、铝土矿）的主要成分", 10, SUBJECT, 234001),
    (234016, "jchem_g9b_u8_smelting", "一氧化碳还原氧化铁与高炉炼铁的原理、装置及尾气处理", 11, SUBJECT, 234001),
    (234017, "jchem_g9b_u8_smelting_calc", "含杂质矿石炼铁的化学方程式计算与产率分析", 12, SUBJECT, 234001),
    (234018, "jchem_g9b_u8_rust_condition", "铁生锈的条件探究及对照实验的变量控制", 13, SUBJECT, 234001),
    (234019, "jchem_g9b_u8_anti_rust", "防锈原理与刷漆、涂油、镀层、制成合金等具体方法", 14, SUBJECT, 234001),
    (234020, "jchem_g9b_u8_resource_protect", "金属资源的合理开采、回收利用与保护措施", 15, SUBJECT, 234001),
    (234021, "jchem_g9b_u8_filtrate_residue", "金属与盐溶液反应后滤液、滤渣成分的推理与检验", 16, SUBJECT, 234001),

    # 第九单元 溶液
    (234022, "jchem_g9b_u9_solution_concept", "溶液、溶质、溶剂的概念及溶液均一性、稳定性的判断", 1, SUBJECT, 234002),
    (234023, "jchem_g9b_u9_dissolve_heat", "溶解时吸热与放热现象（硝酸铵、氢氧化钠、氯化钠）", 2, SUBJECT, 234002),
    (234024, "jchem_g9b_u9_emulsion", "乳浊液、乳化现象及洗涤剂去油污的乳化原理", 3, SUBJECT, 234002),
    (234025, "jchem_g9b_u9_saturated", "饱和溶液与不饱和溶液的概念及相互转化方法", 4, SUBJECT, 234002),
    (234026, "jchem_g9b_u9_saturated_dilute", "饱和溶液与浓溶液、不饱和溶液与稀溶液的关系辨析", 5, SUBJECT, 234002),
    (234027, "jchem_g9b_u9_solubility_concept", "固体溶解度的概念、四要素及溶解度与溶解性的区别", 6, SUBJECT, 234002),
    (234028, "jchem_g9b_u9_curve_read", "溶解度曲线的点、线、交点含义与曲线陡缓的比较", 7, SUBJECT, 234002),
    (234029, "jchem_g9b_u9_crystallization", "降温结晶与蒸发结晶的选择依据及操作要点", 8, SUBJECT, 234002),
    (234030, "jchem_g9b_u9_gas_solubility", "气体溶解度的表示方法及压强、温度的影响", 9, SUBJECT, 234002),
    (234031, "jchem_g9b_u9_mass_fraction", "溶质质量分数的定义、变形公式与基本计算", 10, SUBJECT, 234002),
    (234032, "jchem_g9b_u9_dilution", "溶液加水稀释、加溶质浓缩的守恒计算", 11, SUBJECT, 234002),
    (234033, "jchem_g9b_u9_reaction_calc", "溶质质量分数与化学方程式结合的综合计算", 12, SUBJECT, 234002),
    (234034, "jchem_g9b_u9_prepare_solution", "配制一定溶质质量分数溶液的步骤、仪器与误差分析", 13, SUBJECT, 234002),
    (234035, "jchem_g9b_u9_solubility_vs_fraction", "溶解度与溶质质量分数的区别、联系及饱和溶液换算", 14, SUBJECT, 234002),

    # 第十单元 酸和碱
    (234036, "jchem_g9b_u10_indicator", "紫色石蕊与无色酚酞在酸、碱溶液中的颜色变化", 1, SUBJECT, 234003),
    (234037, "jchem_g9b_u10_hcl_h2so4", "浓盐酸的挥发性、浓硫酸的吸水性及试剂瓶与保存方法", 2, SUBJECT, 234003),
    (234038, "jchem_g9b_u10_dilute_h2so4", "浓硫酸稀释的正确操作与沾到皮肤上的应急处理", 3, SUBJECT, 234003),
    (234039, "jchem_g9b_u10_acid_common", "酸的化学通性：与指示剂、金属、金属氧化物、碱、盐反应", 4, SUBJECT, 234003),
    (234040, "jchem_g9b_u10_acid_derust", "稀盐酸、稀硫酸除铁锈的现象、方程式与过量后果", 5, SUBJECT, 234003),
    (234041, "jchem_g9b_u10_naoh_caoh2", "氢氧化钠、氢氧化钙的物理性质、俗名与用途", 6, SUBJECT, 234003),
    (234042, "jchem_g9b_u10_naoh_deliquesce", "氢氧化钠潮解、变质原因及是否变质的检验方案", 7, SUBJECT, 234003),
    (234043, "jchem_g9b_u10_base_common", "碱的化学通性：与非金属氧化物、酸、盐反应及现象", 8, SUBJECT, 234003),
    (234044, "jchem_g9b_u10_neutralization", "中和反应的定义、实质（H⁺+OH⁻）及放热现象", 9, SUBJECT, 234003),
    (234045, "jchem_g9b_u10_neutralization_use", "中和反应改良酸性土壤、处理废水与生活应用", 10, SUBJECT, 234003),
    (234046, "jchem_g9b_u10_neutralization_exp", "中和反应是否恰好完全反应的探究与指示剂选择", 11, SUBJECT, 234003),
    (234047, "jchem_g9b_u10_ph_curve", "酸碱中和过程中 pH 变化曲线的分段分析与离子判断", 12, SUBJECT, 234003),
    (234048, "jchem_g9b_u10_ph_concept", "溶液酸碱度与 pH 的对应关系及 pH 试纸的使用规范", 13, SUBJECT, 234003),
    (234049, "jchem_g9b_u10_ph_life", "常见物质的 pH 范围及酸碱性对农业、人体与生活的影响", 14, SUBJECT, 234003),

    # 第十一单元 盐 化肥
    (234050, "jchem_g9b_u11_nacl", "氯化钠的用途及粗盐提纯中溶解、过滤、蒸发的操作", 1, SUBJECT, 234004),
    (234051, "jchem_g9b_u11_na2co3", "碳酸钠、碳酸氢钠的俗名、性质与用途辨析", 2, SUBJECT, 234004),
    (234052, "jchem_g9b_u11_caco3", "碳酸钙的性质、用途及碳酸盐的检验方法", 3, SUBJECT, 234004),
    (234053, "jchem_g9b_u11_double_decomp", "复分解反应的定义、通式及发生条件的判断", 4, SUBJECT, 234004),
    (234054, "jchem_g9b_u11_solubility_table", "酸、碱、盐溶解性规律及复分解反应能否进行的判断", 5, SUBJECT, 234004),
    (234055, "jchem_g9b_u11_salt_property", "盐的化学性质：与金属、酸、碱、盐的反应及现象", 6, SUBJECT, 234004),
    (234056, "jchem_g9b_u11_fertilizer_type", "氮肥、磷肥、钾肥的作用与常见化肥品种识别", 7, SUBJECT, 234004),
    (234057, "jchem_g9b_u11_ammonium_test", "铵态氮肥的检验方法与与碱性物质混用的禁忌", 8, SUBJECT, 234004),
    (234058, "jchem_g9b_u11_fertilizer_use", "化肥、农药的合理施用与过量使用对环境的影响", 9, SUBJECT, 234004),

    # 第十二单元 化学与生活
    (234059, "jchem_g9b_u12_nutrients", "六大营养素的种类、食物来源与生理功能", 1, SUBJECT, 234005),
    (234060, "jchem_g9b_u12_protein", "蛋白质的组成、食物来源、变性及甲醛危害", 2, SUBJECT, 234005),
    (234061, "jchem_g9b_u12_carbohydrate", "糖类与油脂的供能作用、来源及淀粉的检验", 3, SUBJECT, 234005),
    (234062, "jchem_g9b_u12_vitamin", "维生素、无机盐和水的作用及缺乏症对应关系", 4, SUBJECT, 234005),
    (234063, "jchem_g9b_u12_elements", "人体必需元素的分类、常量元素与微量元素的作用", 5, SUBJECT, 234005),
    (234064, "jchem_g9b_u12_health", "缺铁、缺碘、缺钙、硒过量等元素与人体健康的关系", 6, SUBJECT, 234005),
    (234065, "jchem_g9b_u12_organic", "有机物与无机物的区分及有机高分子化合物的判断", 7, SUBJECT, 234005),
    (234066, "jchem_g9b_u12_synthetic", "塑料、合成纤维、合成橡胶的性能、用途与鉴别", 8, SUBJECT, 234005),
    (234067, "jchem_g9b_u12_plastic_pollution", "热塑性与热固性塑料的区别及“白色污染”的防治", 9, SUBJECT, 234005),
)

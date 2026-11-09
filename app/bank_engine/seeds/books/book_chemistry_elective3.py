"""人教版（2019）高中化学选择性必修第三册：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 5
G10 = 10
BOOK_ID = 5105

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中化学选择性必修第三册（有机化学基础）",
    "chem_e3",
    5,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (550101, "第一章 有机化合物的结构特点与研究方法", "chem_e3_ch01", 1, BOOK_ID, None),
    (550102, "第二章 烃", "chem_e3_ch02", 2, BOOK_ID, None),
    (550103, "第三章 烃的衍生物", "chem_e3_ch03", 3, BOOK_ID, None),
    (550104, "第四章 生物大分子", "chem_e3_ch04", 4, BOOK_ID, None),
    (550105, "第五章 合成高分子", "chem_e3_ch05", 5, BOOK_ID, None),
    (550111, "第一节 有机化合物的结构特点", "chem_e3_ch01_s01", 1, BOOK_ID, 550101),
    (550112, "第二节 研究有机化合物的一般方法", "chem_e3_ch01_s02", 2, BOOK_ID, 550101),
    (550121, "第一节 烷烃", "chem_e3_ch02_s01", 1, BOOK_ID, 550102),
    (550122, "第二节 烯烃 炔烃", "chem_e3_ch02_s02", 2, BOOK_ID, 550102),
    (550123, "第三节 芳香烃", "chem_e3_ch02_s03", 3, BOOK_ID, 550102),
    (550131, "第一节 卤代烃", "chem_e3_ch03_s01", 1, BOOK_ID, 550103),
    (550132, "第二节 醇 酚", "chem_e3_ch03_s02", 2, BOOK_ID, 550103),
    (550133, "第三节 醛 酮", "chem_e3_ch03_s03", 3, BOOK_ID, 550103),
    (550134, "第四节 羧酸 羧酸衍生物", "chem_e3_ch03_s04", 4, BOOK_ID, 550103),
    (550135, "第五节 有机合成", "chem_e3_ch03_s05", 5, BOOK_ID, 550103),
    (550141, "第一节 糖类", "chem_e3_ch04_s01", 1, BOOK_ID, 550104),
    (550142, "第二节 蛋白质", "chem_e3_ch04_s02", 2, BOOK_ID, 550104),
    (550143, "第三节 核酸", "chem_e3_ch04_s03", 3, BOOK_ID, 550104),
    (550151, "第一节 合成高分子的基本方法", "chem_e3_ch05_s01", 1, BOOK_ID, 550105),
    (550152, "第二节 高分子材料", "chem_e3_ch05_s02", 2, BOOK_ID, 550105),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (550001, "chem_e3_organic_probe", "有机结构探微", 1, SUBJECT, G10, None),
    (550002, "chem_e3_hydrocarbon_probe", "烃类探微", 2, SUBJECT, G10, None),
    (550003, "chem_e3_derivative_probe", "烃的衍生物探微", 3, SUBJECT, G10, None),
    (550004, "chem_e3_biomacromolecule_probe", "生物大分子探微", 4, SUBJECT, G10, None),
    (550005, "chem_e3_polymer_probe", "合成高分子探微", 5, SUBJECT, G10, None),

    # 章域层
    (550006, "chem_e3_ch01", "有机化合物的结构特点与研究方法", 1, SUBJECT, G10, 550001),
    (550007, "chem_e3_ch02", "烃", 1, SUBJECT, G10, 550002),
    (550008, "chem_e3_ch03", "烃的衍生物", 1, SUBJECT, G10, 550003),
    (550009, "chem_e3_ch04", "生物大分子", 1, SUBJECT, G10, 550004),
    (550010, "chem_e3_ch05", "合成高分子", 1, SUBJECT, G10, 550005),

    # 节域层
    (550011, "chem_e3_section_structure", "第一节 有机化合物的结构特点", 1, SUBJECT, G10, 550006),
    (550012, "chem_e3_section_research", "第二节 研究有机化合物的一般方法", 2, SUBJECT, G10, 550006),
    (550013, "chem_e3_section_alkane", "第一节 烷烃", 1, SUBJECT, G10, 550007),
    (550014, "chem_e3_section_alkene_alkyne", "第二节 烯烃 炔烃", 2, SUBJECT, G10, 550007),
    (550015, "chem_e3_section_arene", "第三节 芳香烃", 3, SUBJECT, G10, 550007),
    (550016, "chem_e3_section_halide", "第一节 卤代烃", 1, SUBJECT, G10, 550008),
    (550017, "chem_e3_section_alcohol_phenol", "第二节 醇 酚", 2, SUBJECT, G10, 550008),
    (550018, "chem_e3_section_aldehyde_ketone", "第三节 醛 酮", 3, SUBJECT, G10, 550008),
    (550019, "chem_e3_section_carboxylic", "第四节 羧酸 羧酸衍生物", 4, SUBJECT, G10, 550008),
    (550020, "chem_e3_section_synthesis", "第五节 有机合成", 5, SUBJECT, G10, 550008),
    (550021, "chem_e3_section_carbohydrate", "第一节 糖类", 1, SUBJECT, G10, 550009),
    (550022, "chem_e3_section_protein", "第二节 蛋白质", 2, SUBJECT, G10, 550009),
    (550023, "chem_e3_section_nucleic_acid", "第三节 核酸", 3, SUBJECT, G10, 550009),
    (550024, "chem_e3_section_polymer_method", "第一节 合成高分子的基本方法", 1, SUBJECT, G10, 550010),
    (550025, "chem_e3_section_polymer_material", "第二节 高分子材料", 2, SUBJECT, G10, 550010),

    # 1.1 有机化合物的结构特点
    (550026, "chem_e3_carbon_skeleton", "有机物的碳骨架与成键特征", 1, SUBJECT, G10, 550011),
    (550027, "chem_e3_class_skeleton", "按碳骨架分类有机物", 2, SUBJECT, G10, 550011),
    (550028, "chem_e3_functional_group", "官能团与按官能团分类", 3, SUBJECT, G10, 550011),
    (550029, "chem_e3_homolog", "同系物与同分异构现象", 4, SUBJECT, G10, 550011),
    (550030, "chem_e3_chain_position_isomer", "碳链异构与位置异构", 5, SUBJECT, G10, 550011),
    (550031, "chem_e3_functional_isomer", "官能团异构与顺反异构", 6, SUBJECT, G10, 550011),
    (550032, "chem_e3_chiral", "手性碳与对映异构", 7, SUBJECT, G10, 550011),

    # 1.2 研究有机化合物的一般方法
    (550033, "chem_e3_research_steps", "研究有机化合物的基本步骤", 1, SUBJECT, G10, 550012),
    (550034, "chem_e3_distillation_recrystallization", "蒸馏与重结晶", 2, SUBJECT, G10, 550012),
    (550035, "chem_e3_extraction_chromatography", "萃取与色谱分离", 3, SUBJECT, G10, 550012),
    (550036, "chem_e3_element_analysis", "元素分析与实验式确定", 4, SUBJECT, G10, 550012),
    (550037, "chem_e3_mass_spectrum", "质谱法测定相对分子质量", 5, SUBJECT, G10, 550012),
    (550038, "chem_e3_ir_nmr", "红外光谱与核磁共振氢谱", 6, SUBJECT, G10, 550012),

    # 2.1 烷烃
    (550039, "chem_e3_alkane_naming", "烷烃的通式与系统命名", 1, SUBJECT, G10, 550013),
    (550040, "chem_e3_alkane_property", "烷烃的物理性质递变", 2, SUBJECT, G10, 550013),
    (550041, "chem_e3_methane_structure", "甲烷的结构与稳定性", 3, SUBJECT, G10, 550013),
    (550042, "chem_e3_alkane_substitution", "烷烃的卤代反应", 4, SUBJECT, G10, 550013),
    (550043, "chem_e3_alkane_combustion", "烷烃的燃烧与裂化", 5, SUBJECT, G10, 550013),

    # 2.2 烯烃 炔烃
    (550044, "chem_e3_alkene_structure", "烯烃的结构与顺反异构", 1, SUBJECT, G10, 550014),
    (550045, "chem_e3_alkene_addition", "烯烃的加成反应", 2, SUBJECT, G10, 550014),
    (550046, "chem_e3_alkene_polymerization", "烯烃的加聚反应", 3, SUBJECT, G10, 550014),
    (550047, "chem_e3_alkene_oxidation", "烯烃的氧化反应", 4, SUBJECT, G10, 550014),
    (550048, "chem_e3_acetylene", "乙炔的结构与实验室制法", 5, SUBJECT, G10, 550014),
    (550049, "chem_e3_alkyne_property", "炔烃的加成与氧化", 6, SUBJECT, G10, 550014),

    # 2.3 芳香烃
    (550050, "chem_e3_benzene_structure", "苯的结构与芳香性", 1, SUBJECT, G10, 550015),
    (550051, "chem_e3_benzene_substitution", "苯的取代反应", 2, SUBJECT, G10, 550015),
    (550052, "chem_e3_arene_side_chain", "苯的同系物与侧链氧化", 3, SUBJECT, G10, 550015),
    (550053, "chem_e3_arene_directing", "苯环上取代基的定位效应", 4, SUBJECT, G10, 550015),
    (550054, "chem_e3_arene_source", "芳香烃的来源与煤焦油", 5, SUBJECT, G10, 550015),

    # 3.1 卤代烃
    (550055, "chem_e3_halide_naming", "卤代烃的分类与命名", 1, SUBJECT, G10, 550016),
    (550056, "chem_e3_halide_hydrolysis", "卤代烃的水解反应", 2, SUBJECT, G10, 550016),
    (550057, "chem_e3_halide_elimination", "卤代烃的消去反应", 3, SUBJECT, G10, 550016),
    (550058, "chem_e3_halide_bridge", "卤代烃在有机合成中的桥梁作用", 4, SUBJECT, G10, 550016),

    # 3.2 醇 酚
    (550059, "chem_e3_alcohol_naming", "醇的分类、命名与物理性质", 1, SUBJECT, G10, 550017),
    (550060, "chem_e3_alcohol_active_h", "醇与钠、卤化氢的反应", 2, SUBJECT, G10, 550017),
    (550061, "chem_e3_alcohol_elimination", "醇的消去反应", 3, SUBJECT, G10, 550017),
    (550062, "chem_e3_alcohol_oxidation", "醇的催化氧化与酯化", 4, SUBJECT, G10, 550017),
    (550063, "chem_e3_phenol_acidity", "苯酚的结构与弱酸性", 5, SUBJECT, G10, 550017),
    (550064, "chem_e3_phenol_substitution", "苯酚的取代与显色反应", 6, SUBJECT, G10, 550017),

    # 3.3 醛 酮
    (550065, "chem_e3_carbonyl_structure", "醛酮的结构与命名", 1, SUBJECT, G10, 550018),
    (550066, "chem_e3_silver_mirror", "醛的银镜反应", 2, SUBJECT, G10, 550018),
    (550067, "chem_e3_aldehyde_oxidation", "醛的氧化与还原", 3, SUBJECT, G10, 550018),
    (550068, "chem_e3_carbonyl_addition", "羰基的加成反应", 4, SUBJECT, G10, 550018),
    (550069, "chem_e3_carbonyl_identification", "醛酮的检验与鉴别", 5, SUBJECT, G10, 550018),

    # 3.4 羧酸 羧酸衍生物
    (550070, "chem_e3_carboxylic_acidity", "羧酸的结构与酸性", 1, SUBJECT, G10, 550019),
    (550071, "chem_e3_esterification", "羧酸的酯化反应", 2, SUBJECT, G10, 550019),
    (550072, "chem_e3_ester_hydrolysis", "酯的水解反应", 3, SUBJECT, G10, 550019),
    (550073, "chem_e3_saponification", "油脂的皂化反应", 4, SUBJECT, G10, 550019),
    (550074, "chem_e3_amide_acyl_halide", "酰胺与酰卤", 5, SUBJECT, G10, 550019),
    (550075, "chem_e3_derivative_conversion", "羧酸衍生物的相互转化", 6, SUBJECT, G10, 550019),

    # 3.5 有机合成
    (550076, "chem_e3_synthesis_skeleton", "有机合成的碳骨架构建", 1, SUBJECT, G10, 550020),
    (550077, "chem_e3_synthesis_functional", "官能团的引入与转化", 2, SUBJECT, G10, 550020),
    (550078, "chem_e3_retrosynthesis", "逆合成分析法", 3, SUBJECT, G10, 550020),
    (550079, "chem_e3_synthesis_route", "有机合成路线设计与评价", 4, SUBJECT, G10, 550020),

    # 4.1 糖类
    (550080, "chem_e3_carbohydrate_class", "糖类的组成与分类", 1, SUBJECT, G10, 550021),
    (550081, "chem_e3_glucose", "葡萄糖的结构与还原性", 2, SUBJECT, G10, 550021),
    (550082, "chem_e3_fructose", "果糖与酮糖", 3, SUBJECT, G10, 550021),
    (550083, "chem_e3_disaccharide", "蔗糖与麦芽糖", 4, SUBJECT, G10, 550021),
    (550084, "chem_e3_polysaccharide", "淀粉与纤维素的水解", 5, SUBJECT, G10, 550021),

    # 4.2 蛋白质
    (550085, "chem_e3_amino_acid", "氨基酸的结构与性质", 1, SUBJECT, G10, 550022),
    (550086, "chem_e3_peptide_bond", "肽键与多肽", 2, SUBJECT, G10, 550022),
    (550087, "chem_e3_protein_structure", "蛋白质的结构层次", 3, SUBJECT, G10, 550022),
    (550088, "chem_e3_protein_denaturation", "蛋白质的变性与盐析", 4, SUBJECT, G10, 550022),

    # 4.3 核酸
    (550089, "chem_e3_nucleic_acid_class", "核酸的分类与组成", 1, SUBJECT, G10, 550023),
    (550090, "chem_e3_nucleotide", "核苷酸与核苷", 2, SUBJECT, G10, 550023),
    (550091, "chem_e3_dna_rna", "DNA与RNA的结构差异", 3, SUBJECT, G10, 550023),
    (550092, "chem_e3_nucleic_acid_function", "核酸的生物学功能", 4, SUBJECT, G10, 550023),

    # 5.1 合成高分子的基本方法
    (550093, "chem_e3_addition_polymerization", "加聚反应与加聚物", 1, SUBJECT, G10, 550024),
    (550094, "chem_e3_condensation_polymerization", "缩聚反应与缩聚物", 2, SUBJECT, G10, 550024),
    (550095, "chem_e3_monomer_judge", "高分子单体的判断", 3, SUBJECT, G10, 550024),

    # 5.2 高分子材料
    (550096, "chem_e3_plastic", "塑料与树脂", 1, SUBJECT, G10, 550025),
    (550097, "chem_e3_fiber_rubber", "合成纤维与合成橡胶", 2, SUBJECT, G10, 550025),
    (550098, "chem_e3_functional_polymer", "功能高分子材料", 3, SUBJECT, G10, 550025),
)

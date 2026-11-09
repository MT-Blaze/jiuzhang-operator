"""人教版（2019）高中生物必修第一册（分子与细胞）：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 6
G10 = 10
BOOK_ID = 6101

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中生物必修第一册（分子与细胞）",
    "bio_r1",
    1,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (610101, "第一章 走近细胞", "bio_r1_ch01", 1, BOOK_ID, None),
    (610102, "第二章 组成细胞的分子", "bio_r1_ch02", 2, BOOK_ID, None),
    (610103, "第三章 细胞的基本结构", "bio_r1_ch03", 3, BOOK_ID, None),
    (610104, "第四章 细胞的物质输入和输出", "bio_r1_ch04", 4, BOOK_ID, None),
    (610105, "第五章 细胞的能量供应和利用", "bio_r1_ch05", 5, BOOK_ID, None),
    (610106, "第六章 细胞的生命历程", "bio_r1_ch06", 6, BOOK_ID, None),
    (610111, "第1节 细胞是生命活动的基本单位", "bio_r1_ch01_s01", 1, BOOK_ID, 610101),
    (610112, "第2节 细胞的多样性和统一性", "bio_r1_ch01_s02", 2, BOOK_ID, 610101),
    (610121, "第1节 细胞中的元素和化合物", "bio_r1_ch02_s01", 1, BOOK_ID, 610102),
    (610122, "第2节 细胞中的无机物", "bio_r1_ch02_s02", 2, BOOK_ID, 610102),
    (610123, "第3节 细胞中的糖类和脂质", "bio_r1_ch02_s03", 3, BOOK_ID, 610102),
    (610124, "第4节 蛋白质是生命活动的主要承担者", "bio_r1_ch02_s04", 4, BOOK_ID, 610102),
    (610125, "第5节 核酸是遗传信息的携带者", "bio_r1_ch02_s05", 5, BOOK_ID, 610102),
    (610131, "第1节 细胞膜的结构和功能", "bio_r1_ch03_s01", 1, BOOK_ID, 610103),
    (610132, "第2节 细胞器之间的分工合作", "bio_r1_ch03_s02", 2, BOOK_ID, 610103),
    (610133, "第3节 细胞核的结构和功能", "bio_r1_ch03_s03", 3, BOOK_ID, 610103),
    (610141, "第1节 被动运输", "bio_r1_ch04_s01", 1, BOOK_ID, 610104),
    (610142, "第2节 主动运输与胞吞、胞吐", "bio_r1_ch04_s02", 2, BOOK_ID, 610104),
    (610151, "第1节 降低化学反应活化能的酶", "bio_r1_ch05_s01", 1, BOOK_ID, 610105),
    (610152, "第2节 细胞的能量“货币”ATP", "bio_r1_ch05_s02", 2, BOOK_ID, 610105),
    (610153, "第3节 细胞呼吸的原理和应用", "bio_r1_ch05_s03", 3, BOOK_ID, 610105),
    (610154, "第4节 光合作用与能量转化", "bio_r1_ch05_s04", 4, BOOK_ID, 610105),
    (610161, "第1节 细胞的增殖", "bio_r1_ch06_s01", 1, BOOK_ID, 610106),
    (610162, "第2节 细胞的分化", "bio_r1_ch06_s02", 2, BOOK_ID, 610106),
    (610163, "第3节 细胞的衰老和死亡", "bio_r1_ch06_s03", 3, BOOK_ID, 610106),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (610001, "bio_r1_cell_foundation", "细胞基础", 1, SUBJECT, G10, None),
    (610002, "bio_r1_molecule_composition", "分子组成", 2, SUBJECT, G10, None),
    (610003, "bio_r1_cell_architecture", "细胞结构", 3, SUBJECT, G10, None),
    (610004, "bio_r1_material_transport", "物质运输", 4, SUBJECT, G10, None),
    (610005, "bio_r1_energy_metabolism", "能量代谢", 5, SUBJECT, G10, None),
    (610006, "bio_r1_life_course", "生命历程", 6, SUBJECT, G10, None),

    # 章域层
    (610007, "bio_r1_ch01", "走近细胞", 1, SUBJECT, G10, 610001),
    (610008, "bio_r1_ch02", "组成细胞的分子", 1, SUBJECT, G10, 610002),
    (610009, "bio_r1_ch03", "细胞的基本结构", 1, SUBJECT, G10, 610003),
    (610010, "bio_r1_ch04", "细胞的物质输入和输出", 1, SUBJECT, G10, 610004),
    (610011, "bio_r1_ch05", "细胞的能量供应和利用", 1, SUBJECT, G10, 610005),
    (610012, "bio_r1_ch06", "细胞的生命历程", 1, SUBJECT, G10, 610006),

    # 节域层
    (610013, "bio_r1_s01_cell_unit", "第1节 细胞是生命活动的基本单位", 1, SUBJECT, G10, 610007),
    (610014, "bio_r1_s02_diversity", "第2节 细胞的多样性和统一性", 2, SUBJECT, G10, 610007),
    (610015, "bio_r1_s03_elements", "第1节 细胞中的元素和化合物", 1, SUBJECT, G10, 610008),
    (610016, "bio_r1_s04_inorganic", "第2节 细胞中的无机物", 2, SUBJECT, G10, 610008),
    (610017, "bio_r1_s05_sugar_lipid", "第3节 细胞中的糖类和脂质", 3, SUBJECT, G10, 610008),
    (610018, "bio_r1_s06_protein", "第4节 蛋白质是生命活动的主要承担者", 4, SUBJECT, G10, 610008),
    (610019, "bio_r1_s07_nucleic_acid", "第5节 核酸是遗传信息的携带者", 5, SUBJECT, G10, 610008),
    (610020, "bio_r1_s08_membrane", "第1节 细胞膜的结构和功能", 1, SUBJECT, G10, 610009),
    (610021, "bio_r1_s09_organelle", "第2节 细胞器之间的分工合作", 2, SUBJECT, G10, 610009),
    (610022, "bio_r1_s10_nucleus", "第3节 细胞核的结构和功能", 3, SUBJECT, G10, 610009),
    (610023, "bio_r1_s11_passive", "第1节 被动运输", 1, SUBJECT, G10, 610010),
    (610024, "bio_r1_s12_active", "第2节 主动运输与胞吞、胞吐", 2, SUBJECT, G10, 610010),
    (610025, "bio_r1_s13_enzyme", "第1节 降低化学反应活化能的酶", 1, SUBJECT, G10, 610011),
    (610026, "bio_r1_s14_atp", "第2节 细胞的能量“货币”ATP", 2, SUBJECT, G10, 610011),
    (610027, "bio_r1_s15_respiration", "第3节 细胞呼吸的原理和应用", 3, SUBJECT, G10, 610011),
    (610028, "bio_r1_s16_photosynthesis", "第4节 光合作用与能量转化", 4, SUBJECT, G10, 610011),
    (610029, "bio_r1_s17_proliferation", "第1节 细胞的增殖", 1, SUBJECT, G10, 610012),
    (610030, "bio_r1_s18_differentiation", "第2节 细胞的分化", 2, SUBJECT, G10, 610012),
    (610031, "bio_r1_s19_aging_death", "第3节 细胞的衰老和死亡", 3, SUBJECT, G10, 610012),

    # 1.1 细胞是生命活动的基本单位
    (610032, "bio_r1_life_hierarchy", "生命系统的结构层次", 1, SUBJECT, G10, 610013),
    (610033, "bio_r1_cell_theory", "细胞学说的建立与主要内容", 2, SUBJECT, G10, 610013),
    (610034, "bio_r1_cell_as_unit", "细胞是生命活动的基本单位", 3, SUBJECT, G10, 610013),

    # 1.2 细胞的多样性和统一性
    (610035, "bio_r1_prokaryote_eukaryote", "原核细胞与真核细胞的比较", 1, SUBJECT, G10, 610014),
    (610036, "bio_r1_microbe_groups", "常见原核生物与真核生物类群", 2, SUBJECT, G10, 610014),
    (610037, "bio_r1_diversity_unity", "细胞的多样性与统一性", 3, SUBJECT, G10, 610014),
    (610038, "bio_r1_microscope_use", "高倍显微镜的使用方法", 4, SUBJECT, G10, 610014),
    (610039, "bio_r1_temp_mount", "临时装片制作与显微观察实验", 5, SUBJECT, G10, 610014),

    # 2.1 细胞中的元素和化合物
    (610040, "bio_r1_elements", "组成细胞的化学元素", 1, SUBJECT, G10, 610015),
    (610041, "bio_r1_compounds", "细胞中化合物的种类与含量", 2, SUBJECT, G10, 610015),
    (610042, "bio_r1_detection_experiment", "检测生物组织中的糖类、脂肪和蛋白质", 3, SUBJECT, G10, 610015),

    # 2.2 细胞中的无机物
    (610043, "bio_r1_water", "水的存在形式与生理作用", 1, SUBJECT, G10, 610016),
    (610044, "bio_r1_inorganic_salt", "无机盐的存在形式与生理功能", 2, SUBJECT, G10, 610016),

    # 2.3 细胞中的糖类和脂质
    (610045, "bio_r1_sugar_class", "糖类的种类与功能", 1, SUBJECT, G10, 610017),
    (610046, "bio_r1_lipid_class", "脂质的种类与功能", 2, SUBJECT, G10, 610017),
    (610047, "bio_r1_sugar_lipid_relation", "糖类与脂质的相互转化", 3, SUBJECT, G10, 610017),

    # 2.4 蛋白质
    (610048, "bio_r1_amino_acid", "氨基酸的结构特点与种类", 1, SUBJECT, G10, 610018),
    (610049, "bio_r1_dehydration", "脱水缩合与肽键的形成", 2, SUBJECT, G10, 610018),
    (610050, "bio_r1_protein_diversity", "蛋白质结构多样性的原因", 3, SUBJECT, G10, 610018),
    (610051, "bio_r1_protein_function", "蛋白质的功能与变性", 4, SUBJECT, G10, 610018),

    # 2.5 核酸
    (610052, "bio_r1_nucleic_acid_class", "核酸的种类、分布与组成", 1, SUBJECT, G10, 610019),
    (610053, "bio_r1_nucleotide", "核苷酸与生物大分子的单体", 2, SUBJECT, G10, 610019),
    (610054, "bio_r1_dna_rna_compare", "DNA与RNA的比较及核酸的功能", 3, SUBJECT, G10, 610019),

    # 3.1 细胞膜的结构和功能
    (610055, "bio_r1_membrane_preparation", "细胞膜的制备与成分", 1, SUBJECT, G10, 610020),
    (610056, "bio_r1_fluid_mosaic", "流动镶嵌模型的基本内容", 2, SUBJECT, G10, 610020),
    (610057, "bio_r1_membrane_function", "细胞膜的功能与信息交流", 3, SUBJECT, G10, 610020),
    (610058, "bio_r1_cell_wall", "细胞壁的成分与功能", 4, SUBJECT, G10, 610020),

    # 3.2 细胞器之间的分工合作
    (610059, "bio_r1_organelle_overview", "细胞器的分离方法与分类概览", 1, SUBJECT, G10, 610021),
    (610060, "bio_r1_mitochondria_chloroplast", "线粒体与叶绿体的结构与功能", 2, SUBJECT, G10, 610021),
    (610061, "bio_r1_er_golgi_liposome", "内质网、高尔基体与溶酶体", 3, SUBJECT, G10, 610021),
    (610062, "bio_r1_ribosome_centrosome", "核糖体、中心体与细胞骨架", 4, SUBJECT, G10, 610021),
    (610063, "bio_r1_secretory_protein", "分泌蛋白的合成运输与生物膜系统", 5, SUBJECT, G10, 610021),

    # 3.3 细胞核的结构和功能
    (610064, "bio_r1_nucleus_structure", "细胞核的结构", 1, SUBJECT, G10, 610022),
    (610065, "bio_r1_nucleus_function", "细胞核的功能与核孔", 2, SUBJECT, G10, 610022),

    # 4.1 被动运输
    (610066, "bio_r1_osmosis", "渗透作用与渗透装置", 1, SUBJECT, G10, 610023),
    (610067, "bio_r1_animal_cell_osmosis", "动物细胞的吸水和失水", 2, SUBJECT, G10, 610023),
    (610068, "bio_r1_plasmolysis", "植物细胞的质壁分离与复原", 3, SUBJECT, G10, 610023),
    (610069, "bio_r1_passive_transport", "自由扩散与协助扩散", 4, SUBJECT, G10, 610023),

    # 4.2 主动运输与胞吞、胞吐
    (610070, "bio_r1_active_transport", "主动运输的特点与实例", 1, SUBJECT, G10, 610024),
    (610071, "bio_r1_transport_factors", "影响物质跨膜运输的因素", 2, SUBJECT, G10, 610024),
    (610072, "bio_r1_endocytosis_exocytosis", "胞吞与胞吐", 3, SUBJECT, G10, 610024),
    (610073, "bio_r1_transport_compare", "物质跨膜运输方式的比较与判断", 4, SUBJECT, G10, 610024),

    # 5.1 酶
    (610074, "bio_r1_enzyme_discovery", "酶的本质与发现历程", 1, SUBJECT, G10, 610025),
    (610075, "bio_r1_enzyme_property", "酶的高效性与专一性", 2, SUBJECT, G10, 610025),
    (610076, "bio_r1_enzyme_conditions", "酶的作用条件（温度与pH）", 3, SUBJECT, G10, 610025),
    (610077, "bio_r1_enzyme_experiment", "酶促反应的影响因素与实验设计", 4, SUBJECT, G10, 610025),

    # 5.2 ATP
    (610078, "bio_r1_atp_structure_cycle", "ATP的结构与ATP—ADP循环", 1, SUBJECT, G10, 610026),
    (610079, "bio_r1_atp_utilization", "ATP的利用与能量供应", 2, SUBJECT, G10, 610026),

    # 5.3 细胞呼吸
    (610080, "bio_r1_yeast_respiration", "探究酵母菌细胞呼吸的方式", 1, SUBJECT, G10, 610027),
    (610081, "bio_r1_aerobic_stage1", "有氧呼吸第一阶段", 2, SUBJECT, G10, 610027),
    (610082, "bio_r1_aerobic_stage23", "有氧呼吸第二、三阶段与总反应式", 3, SUBJECT, G10, 610027),
    (610083, "bio_r1_anaerobic", "无氧呼吸的类型与产物", 4, SUBJECT, G10, 610027),
    (610084, "bio_r1_respiration_application", "细胞呼吸原理的应用", 5, SUBJECT, G10, 610027),

    # 5.4 光合作用
    (610085, "bio_r1_photosynthesis_history", "光合作用的探究历程", 1, SUBJECT, G10, 610028),
    (610086, "bio_r1_chloroplast_pigment", "叶绿体结构与光合色素的提取分离", 2, SUBJECT, G10, 610028),
    (610087, "bio_r1_light_reaction", "光反应的过程与物质能量变化", 3, SUBJECT, G10, 610028),
    (610088, "bio_r1_dark_reaction", "暗反应与光合作用总反应式", 4, SUBJECT, G10, 610028),
    (610089, "bio_r1_photosynthesis_factors", "影响光合作用的因素及应用", 5, SUBJECT, G10, 610028),

    # 6.1 细胞的增殖
    (610090, "bio_r1_cell_cycle", "细胞周期与有丝分裂间期", 1, SUBJECT, G10, 610029),
    (610091, "bio_r1_mitosis_early", "有丝分裂前期与中期", 2, SUBJECT, G10, 610029),
    (610092, "bio_r1_mitosis_late", "有丝分裂后期与末期", 3, SUBJECT, G10, 610029),
    (610093, "bio_r1_mitosis_compare", "动植物有丝分裂的差异与意义", 4, SUBJECT, G10, 610029),
    (610094, "bio_r1_mitosis_experiment", "观察根尖分生组织细胞的有丝分裂", 5, SUBJECT, G10, 610029),

    # 6.2 细胞的分化
    (610095, "bio_r1_differentiation", "细胞分化与基因的选择性表达", 1, SUBJECT, G10, 610030),
    (610096, "bio_r1_totipotency", "细胞的全能性", 2, SUBJECT, G10, 610030),
    (610097, "bio_r1_stem_cell", "干细胞及其应用", 3, SUBJECT, G10, 610030),

    # 6.3 细胞的衰老和死亡
    (610098, "bio_r1_aging", "细胞衰老的特征与原因", 1, SUBJECT, G10, 610031),
    (610099, "bio_r1_apoptosis", "细胞凋亡、坏死与自噬", 2, SUBJECT, G10, 610031),
)

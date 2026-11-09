"""人教版（2019）高中生物必修第二册（遗传与进化）：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 6
G10 = 10
BOOK_ID = 6102

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中生物必修第二册（遗传与进化）",
    "bio_r2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (620101, "第一章 遗传因子的发现", "bio_r2_ch01", 1, BOOK_ID, None),
    (620102, "第二章 基因和染色体的关系", "bio_r2_ch02", 2, BOOK_ID, None),
    (620103, "第三章 基因的本质", "bio_r2_ch03", 3, BOOK_ID, None),
    (620104, "第四章 基因的表达", "bio_r2_ch04", 4, BOOK_ID, None),
    (620105, "第五章 基因突变及其他变异", "bio_r2_ch05", 5, BOOK_ID, None),
    (620106, "第六章 生物的进化", "bio_r2_ch06", 6, BOOK_ID, None),
    (620111, "第1节 孟德尔的豌豆杂交实验（一）", "bio_r2_ch01_s01", 1, BOOK_ID, 620101),
    (620112, "第2节 孟德尔的豌豆杂交实验（二）", "bio_r2_ch01_s02", 2, BOOK_ID, 620101),
    (620121, "第1节 减数分裂和受精作用", "bio_r2_ch02_s01", 1, BOOK_ID, 620102),
    (620122, "第2节 基因在染色体上", "bio_r2_ch02_s02", 2, BOOK_ID, 620102),
    (620123, "第3节 伴性遗传", "bio_r2_ch02_s03", 3, BOOK_ID, 620102),
    (620131, "第1节 DNA是主要的遗传物质", "bio_r2_ch03_s01", 1, BOOK_ID, 620103),
    (620132, "第2节 DNA的结构", "bio_r2_ch03_s02", 2, BOOK_ID, 620103),
    (620133, "第3节 DNA的复制", "bio_r2_ch03_s03", 3, BOOK_ID, 620103),
    (620134, "第4节 基因通常是有遗传效应的DNA片段", "bio_r2_ch03_s04", 4, BOOK_ID, 620103),
    (620141, "第1节 基因指导蛋白质的合成", "bio_r2_ch04_s01", 1, BOOK_ID, 620104),
    (620142, "第2节 基因表达与性状的关系", "bio_r2_ch04_s02", 2, BOOK_ID, 620104),
    (620151, "第1节 基因突变和基因重组", "bio_r2_ch05_s01", 1, BOOK_ID, 620105),
    (620152, "第2节 染色体变异", "bio_r2_ch05_s02", 2, BOOK_ID, 620105),
    (620153, "第3节 人类遗传病", "bio_r2_ch05_s03", 3, BOOK_ID, 620105),
    (620161, "第1节 生物有共同祖先的证据", "bio_r2_ch06_s01", 1, BOOK_ID, 620106),
    (620162, "第2节 自然选择与适应的形成", "bio_r2_ch06_s02", 2, BOOK_ID, 620106),
    (620163, "第3节 种群基因组成的变化与物种的形成", "bio_r2_ch06_s03", 3, BOOK_ID, 620106),
    (620164, "第4节 协同进化与生物多样性的形成", "bio_r2_ch06_s04", 4, BOOK_ID, 620106),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 主题域层
    (620001, "bio_r2_domain_inheritance_law", "遗传规律", 1, SUBJECT, G10, None),
    (620002, "bio_r2_domain_gene_chromosome", "基因与染色体", 2, SUBJECT, G10, None),
    (620003, "bio_r2_domain_gene_essence", "基因本质", 3, SUBJECT, G10, None),
    (620004, "bio_r2_domain_gene_expression", "基因表达", 4, SUBJECT, G10, None),
    (620005, "bio_r2_domain_variation_breeding", "变异与育种", 5, SUBJECT, G10, None),
    (620006, "bio_r2_domain_evolution", "生物进化", 6, SUBJECT, G10, None),

    # 节域层
    (620007, "bio_r2_s01_pea_separation", "第1节 孟德尔的豌豆杂交实验（一）", 1, SUBJECT, G10, 620001),
    (620008, "bio_r2_s02_pea_free_combination", "第2节 孟德尔的豌豆杂交实验（二）", 2, SUBJECT, G10, 620001),
    (620009, "bio_r2_s03_meiosis_fertilization", "第1节 减数分裂和受精作用", 1, SUBJECT, G10, 620002),
    (620010, "bio_r2_s04_gene_on_chromosome", "第2节 基因在染色体上", 2, SUBJECT, G10, 620002),
    (620011, "bio_r2_s05_sex_linked", "第3节 伴性遗传", 3, SUBJECT, G10, 620002),
    (620012, "bio_r2_s06_dna_main_material", "第1节 DNA是主要的遗传物质", 1, SUBJECT, G10, 620003),
    (620013, "bio_r2_s07_dna_structure", "第2节 DNA的结构", 2, SUBJECT, G10, 620003),
    (620014, "bio_r2_s08_dna_replication", "第3节 DNA的复制", 3, SUBJECT, G10, 620003),
    (620015, "bio_r2_s09_gene_dna_fragment", "第4节 基因通常是有遗传效应的DNA片段", 4, SUBJECT, G10, 620003),
    (620016, "bio_r2_s10_gene_protein", "第1节 基因指导蛋白质的合成", 1, SUBJECT, G10, 620004),
    (620017, "bio_r2_s11_gene_trait", "第2节 基因表达与性状的关系", 2, SUBJECT, G10, 620004),
    (620018, "bio_r2_s12_mutation_recombination", "第1节 基因突变和基因重组", 1, SUBJECT, G10, 620005),
    (620019, "bio_r2_s13_chromosome_variation", "第2节 染色体变异", 2, SUBJECT, G10, 620005),
    (620020, "bio_r2_s14_human_genetic_disease", "第3节 人类遗传病", 3, SUBJECT, G10, 620005),
    (620021, "bio_r2_s15_common_ancestor", "第1节 生物有共同祖先的证据", 1, SUBJECT, G10, 620006),
    (620022, "bio_r2_s16_natural_selection", "第2节 自然选择与适应的形成", 2, SUBJECT, G10, 620006),
    (620023, "bio_r2_s17_population_speciation", "第3节 种群基因组成的变化与物种的形成", 3, SUBJECT, G10, 620006),
    (620024, "bio_r2_s18_coevolution_biodiversity", "第4节 协同进化与生物多样性的形成", 4, SUBJECT, G10, 620006),

    # 1.1 孟德尔的豌豆杂交实验（一）
    (620025, "bio_r2_pea_advantages", "豌豆作为遗传实验材料的优点", 1, SUBJECT, G10, 620007),
    (620026, "bio_r2_artificial_pollination", "人工异花传粉的操作步骤", 2, SUBJECT, G10, 620007),
    (620027, "bio_r2_single_trait_cross", "一对相对性状的杂交实验与性状分离", 3, SUBJECT, G10, 620007),
    (620028, "bio_r2_separation_hypothesis", "分离现象的解释与假说要点", 4, SUBJECT, G10, 620007),
    (620029, "bio_r2_test_cross_separation", "测交实验与分离定律的实质", 5, SUBJECT, G10, 620007),

    # 1.2 孟德尔的豌豆杂交实验（二）
    (620030, "bio_r2_double_trait_cross", "两对相对性状的杂交实验与9:3:3:1", 1, SUBJECT, G10, 620008),
    (620031, "bio_r2_free_combination_hypothesis", "自由组合现象的解释与配子类型", 2, SUBJECT, G10, 620008),
    (620032, "bio_r2_test_cross_free_combination", "自由组合定律的验证与实质", 3, SUBJECT, G10, 620008),
    (620033, "bio_r2_mendel_success", "孟德尔成功的原因与假说—演绎法", 4, SUBJECT, G10, 620008),
    (620034, "bio_r2_ratio_variants", "9:3:3:1变式与遗传概率计算", 5, SUBJECT, G10, 620008),

    # 2.1 减数分裂和受精作用
    (620035, "bio_r2_meiosis_concept", "减数分裂的概念与发生部位", 1, SUBJECT, G10, 620009),
    (620036, "bio_r2_homologous_synapsis", "同源染色体、联会与四分体", 2, SUBJECT, G10, 620009),
    (620037, "bio_r2_meiosis_i", "减数第一次分裂各时期特点", 3, SUBJECT, G10, 620009),
    (620038, "bio_r2_meiosis_ii", "减数第二次分裂各时期特点", 4, SUBJECT, G10, 620009),
    (620039, "bio_r2_meiosis_quantity_change", "减数分裂中染色体与DNA数量变化", 5, SUBJECT, G10, 620009),
    (620040, "bio_r2_gamete_formation", "精子与卵细胞形成的比较", 6, SUBJECT, G10, 620009),
    (620041, "bio_r2_fertilization", "受精作用的过程与意义", 7, SUBJECT, G10, 620009),
    (620042, "bio_r2_division_image_judgement", "减数分裂与有丝分裂的图像判断", 8, SUBJECT, G10, 620009),

    # 2.2 基因在染色体上
    (620043, "bio_r2_sutton_hypothesis", "萨顿假说：基因位于染色体上", 1, SUBJECT, G10, 620010),
    (620044, "bio_r2_morgan_experiment", "摩尔根果蝇杂交实验", 2, SUBJECT, G10, 620010),
    (620045, "bio_r2_gene_linear_arrangement", "基因在染色体上呈线性排列", 3, SUBJECT, G10, 620010),

    # 2.3 伴性遗传
    (620046, "bio_r2_sex_linked_types", "伴性遗传的类型与特点", 1, SUBJECT, G10, 620011),
    (620047, "bio_r2_color_blindness", "红绿色盲的遗传分析", 2, SUBJECT, G10, 620011),
    (620048, "bio_r2_vitamin_d_y_linked", "抗维生素D佝偻病与伴Y遗传", 3, SUBJECT, G10, 620011),
    (620049, "bio_r2_pedigree_analysis", "遗传系谱图分析与概率计算", 4, SUBJECT, G10, 620011),

    # 3.1 DNA是主要的遗传物质
    (620050, "bio_r2_griffith_experiment", "格里菲斯肺炎链球菌体内转化实验", 1, SUBJECT, G10, 620012),
    (620051, "bio_r2_avery_experiment", "艾弗里体外转化实验", 2, SUBJECT, G10, 620012),
    (620052, "bio_r2_phage_experiment_process", "噬菌体侵染细菌实验的原理与过程", 3, SUBJECT, G10, 620012),
    (620053, "bio_r2_phage_experiment_analysis", "噬菌体实验的标记选择与结果分析", 4, SUBJECT, G10, 620012),
    (620054, "bio_r2_tmv_experiment", "烟草花叶病毒实验与DNA是主要遗传物质的结论", 5, SUBJECT, G10, 620012),

    # 3.2 DNA的结构
    (620055, "bio_r2_dna_model_build", "DNA双螺旋结构模型的建立", 1, SUBJECT, G10, 620013),
    (620056, "bio_r2_dna_composition", "DNA的组成与双螺旋结构特点", 2, SUBJECT, G10, 620013),
    (620057, "bio_r2_base_pairing", "碱基互补配对原则与碱基比例计算", 3, SUBJECT, G10, 620013),
    (620058, "bio_r2_dna_diversity", "DNA结构的多样性与特异性", 4, SUBJECT, G10, 620013),

    # 3.3 DNA的复制
    (620059, "bio_r2_replication_hypothesis", "对DNA复制的推测与半保留复制的证据", 1, SUBJECT, G10, 620014),
    (620060, "bio_r2_replication_process", "DNA复制的过程与条件", 2, SUBJECT, G10, 620014),
    (620061, "bio_r2_replication_features", "DNA复制的特点与意义", 3, SUBJECT, G10, 620014),
    (620062, "bio_r2_replication_calculation", "DNA复制的有关计算", 4, SUBJECT, G10, 620014),

    # 3.4 基因通常是有遗传效应的DNA片段
    (620063, "bio_r2_gene_dna_chromosome", "基因、DNA与染色体的关系", 1, SUBJECT, G10, 620015),
    (620064, "bio_r2_gene_genetic_effect", "基因是有遗传效应的DNA片段", 2, SUBJECT, G10, 620015),
    (620065, "bio_r2_prokaryote_eukaryote_gene", "真核基因与原核基因的结构比较", 3, SUBJECT, G10, 620015),

    # 4.1 基因指导蛋白质的合成
    (620066, "bio_r2_rna_types", "RNA的种类与功能", 1, SUBJECT, G10, 620016),
    (620067, "bio_r2_transcription_conditions", "转录的场所、模板、原料与酶", 2, SUBJECT, G10, 620016),
    (620068, "bio_r2_transcription_process", "转录的过程与RNA加工", 3, SUBJECT, G10, 620016),
    (620069, "bio_r2_genetic_code", "遗传密码与密码子表", 4, SUBJECT, G10, 620016),
    (620070, "bio_r2_translation_process", "翻译的过程与tRNA的作用", 5, SUBJECT, G10, 620016),
    (620071, "bio_r2_central_dogma", "中心法则的内容与发展", 6, SUBJECT, G10, 620016),

    # 4.2 基因表达与性状的关系
    (620072, "bio_r2_gene_control_trait", "基因控制性状的两种途径", 1, SUBJECT, G10, 620017),
    (620073, "bio_r2_selective_expression", "基因的选择性表达与细胞分化", 2, SUBJECT, G10, 620017),
    (620074, "bio_r2_epigenetics", "表观遗传的概念、实例与机制", 3, SUBJECT, G10, 620017),
    (620075, "bio_r2_gene_environment_trait", "基因、环境与性状的关系", 4, SUBJECT, G10, 620017),

    # 5.1 基因突变和基因重组
    (620076, "bio_r2_sickle_cell", "基因突变的实例：镰状细胞贫血", 1, SUBJECT, G10, 620018),
    (620077, "bio_r2_mutation_concept", "基因突变的概念、类型与原因", 2, SUBJECT, G10, 620018),
    (620078, "bio_r2_mutation_features", "基因突变的特点与意义", 3, SUBJECT, G10, 620018),
    (620079, "bio_r2_recombination_types", "基因重组的类型与发生时期", 4, SUBJECT, G10, 620018),
    (620080, "bio_r2_mutation_vs_recombination", "基因突变与基因重组的比较", 5, SUBJECT, G10, 620018),

    # 5.2 染色体变异
    (620081, "bio_r2_structure_variation", "染色体结构变异的类型与实例", 1, SUBJECT, G10, 620019),
    (620082, "bio_r2_number_variation", "染色体数目变异与染色体组", 2, SUBJECT, G10, 620019),
    (620083, "bio_r2_ploidy", "二倍体、多倍体与单倍体", 3, SUBJECT, G10, 620019),
    (620084, "bio_r2_low_temp_experiment", "低温诱导染色体数目变化实验与育种应用", 4, SUBJECT, G10, 620019),

    # 5.3 人类遗传病
    (620085, "bio_r2_human_disease_types", "人类遗传病的类型与常见实例", 1, SUBJECT, G10, 620020),
    (620086, "bio_r2_disease_prevention", "遗传病的监测、预防与基因检测", 2, SUBJECT, G10, 620020),
    (620087, "bio_r2_human_genome_project", "人类基因组计划及其意义", 3, SUBJECT, G10, 620020),

    # 6.1 生物有共同祖先的证据
    (620088, "bio_r2_fossil_evidence", "化石证据", 1, SUBJECT, G10, 620021),
    (620089, "bio_r2_anatomy_embryo_evidence", "比较解剖学与胚胎学证据", 2, SUBJECT, G10, 620021),
    (620090, "bio_r2_cell_molecular_evidence", "细胞和分子水平的证据", 3, SUBJECT, G10, 620021),

    # 6.2 自然选择与适应的形成
    (620091, "bio_r2_adaptation", "适应的普遍性与相对性", 1, SUBJECT, G10, 620022),
    (620092, "bio_r2_natural_selection_theory", "自然选择学说的主要内容", 2, SUBJECT, G10, 620022),
    (620093, "bio_r2_modern_evolution_theory", "现代生物进化理论的主要内容", 3, SUBJECT, G10, 620022),

    # 6.3 种群基因组成的变化与物种的形成
    (620094, "bio_r2_population_gene_pool", "种群、基因库与基因频率", 1, SUBJECT, G10, 620023),
    (620095, "bio_r2_hardy_weinberg", "遗传平衡定律与基因频率计算", 2, SUBJECT, G10, 620023),
    (620096, "bio_r2_speciation_isolation", "物种形成与生殖隔离", 3, SUBJECT, G10, 620023),

    # 6.4 协同进化与生物多样性的形成
    (620097, "bio_r2_coevolution", "协同进化的概念与实例", 1, SUBJECT, G10, 620024),
    (620098, "bio_r2_biodiversity_levels", "生物多样性的三个层次", 2, SUBJECT, G10, 620024),
    (620099, "bio_r2_biodiversity_formation", "生物多样性形成与生物进化历程", 3, SUBJECT, G10, 620024),
)

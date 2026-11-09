"""人教版（2019）高中生物选择性必修第三册（生物技术与工程）：章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 6
G10 = 10
BOOK_ID = 6105

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中生物选择性必修第三册（生物技术与工程）",
    "bio_e3",
    6,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (650101, "第1章 发酵工程", "bio_e3_ch01", 1, BOOK_ID, None),
    (650102, "第2章 细胞工程", "bio_e3_ch02", 2, BOOK_ID, None),
    (650103, "第3章 基因工程", "bio_e3_ch03", 3, BOOK_ID, None),
    (650104, "第4章 生物技术的安全性与伦理问题", "bio_e3_ch04", 4, BOOK_ID, None),
    (650111, "第1节 传统发酵技术的应用", "bio_e3_ch01_s01", 1, BOOK_ID, 650101),
    (650112, "第2节 微生物的培养技术及应用", "bio_e3_ch01_s02", 2, BOOK_ID, 650101),
    (650113, "第3节 发酵工程及其应用", "bio_e3_ch01_s03", 3, BOOK_ID, 650101),
    (650121, "第1节 植物细胞工程", "bio_e3_ch02_s01", 1, BOOK_ID, 650102),
    (650122, "第2节 动物细胞工程", "bio_e3_ch02_s02", 2, BOOK_ID, 650102),
    (650123, "第3节 胚胎工程", "bio_e3_ch02_s03", 3, BOOK_ID, 650102),
    (650131, "第1节 重组DNA技术的基本工具", "bio_e3_ch03_s01", 1, BOOK_ID, 650103),
    (650132, "第2节 基因工程的基本操作程序", "bio_e3_ch03_s02", 2, BOOK_ID, 650103),
    (650133, "第3节 基因工程的应用", "bio_e3_ch03_s03", 3, BOOK_ID, 650103),
    (650134, "第4节 蛋白质工程的原理和应用", "bio_e3_ch03_s04", 4, BOOK_ID, 650103),
    (650141, "第1节 转基因产品的安全性", "bio_e3_ch04_s01", 1, BOOK_ID, 650104),
    (650142, "第2节 关注生殖性克隆人", "bio_e3_ch04_s02", 2, BOOK_ID, 650104),
    (650143, "第3节 禁止生物武器", "bio_e3_ch04_s03", 3, BOOK_ID, 650104),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (650001, "bio_e3_domain_fermentation", "发酵工程与微生物培养", 1, SUBJECT, G10, None),
    (650002, "bio_e3_domain_cell_engineering", "细胞工程与克隆技术", 2, SUBJECT, G10, None),
    (650003, "bio_e3_domain_gene_engineering", "基因工程与蛋白质工程", 3, SUBJECT, G10, None),
    (650004, "bio_e3_domain_bioethics", "生物技术安全与伦理", 4, SUBJECT, G10, None),

    # 章域层
    (650005, "bio_e3_ch01", "发酵工程", 1, SUBJECT, G10, 650001),
    (650006, "bio_e3_ch02", "细胞工程", 1, SUBJECT, G10, 650002),
    (650007, "bio_e3_ch03", "基因工程", 1, SUBJECT, G10, 650003),
    (650008, "bio_e3_ch04", "生物技术的安全性与伦理问题", 1, SUBJECT, G10, 650004),

    # 节域层
    (650009, "bio_e3_sec_traditional_fermentation", "第1节 传统发酵技术的应用", 1, SUBJECT, G10, 650005),
    (650010, "bio_e3_sec_microbe_culture", "第2节 微生物的培养技术及应用", 2, SUBJECT, G10, 650005),
    (650011, "bio_e3_sec_fermentation_engineering", "第3节 发酵工程及其应用", 3, SUBJECT, G10, 650005),
    (650012, "bio_e3_sec_plant_cell", "第1节 植物细胞工程", 1, SUBJECT, G10, 650006),
    (650013, "bio_e3_sec_animal_cell", "第2节 动物细胞工程", 2, SUBJECT, G10, 650006),
    (650014, "bio_e3_sec_embryo_engineering", "第3节 胚胎工程", 3, SUBJECT, G10, 650006),
    (650015, "bio_e3_sec_dna_tools", "第1节 重组DNA技术的基本工具", 1, SUBJECT, G10, 650007),
    (650016, "bio_e3_sec_gene_procedure", "第2节 基因工程的基本操作程序", 2, SUBJECT, G10, 650007),
    (650017, "bio_e3_sec_gene_application", "第3节 基因工程的应用", 3, SUBJECT, G10, 650007),
    (650018, "bio_e3_sec_protein_engineering", "第4节 蛋白质工程的原理和应用", 4, SUBJECT, G10, 650007),
    (650019, "bio_e3_sec_gmo_safety", "第1节 转基因产品的安全性", 1, SUBJECT, G10, 650008),
    (650020, "bio_e3_sec_reproductive_cloning", "第2节 关注生殖性克隆人", 2, SUBJECT, G10, 650008),
    (650021, "bio_e3_sec_biological_weapons", "第3节 禁止生物武器", 3, SUBJECT, G10, 650008),

    # 1.1 传统发酵技术的应用
    (650022, "bio_e3_traditional_fermentation_concept", "传统发酵技术的概念与菌种来源", 1, SUBJECT, G10, 650009),
    (650023, "bio_e3_fruit_wine", "果酒制作的原理与条件", 2, SUBJECT, G10, 650009),
    (650024, "bio_e3_fruit_vinegar", "果醋制作的原理与条件", 3, SUBJECT, G10, 650009),
    (650025, "bio_e3_fermented_tofu", "腐乳制作的原理与流程", 4, SUBJECT, G10, 650009),
    (650026, "bio_e3_paocai", "泡菜制作的原理与条件", 5, SUBJECT, G10, 650009),
    (650027, "bio_e3_nitrite_determination", "泡菜中亚硝酸盐含量的测定", 6, SUBJECT, G10, 650009),

    # 1.2 微生物的培养技术及应用
    (650028, "bio_e3_culture_medium", "培养基的营养成分与类型", 1, SUBJECT, G10, 650010),
    (650029, "bio_e3_sterilization_disinfection", "消毒与灭菌的概念及常用方法", 2, SUBJECT, G10, 650010),
    (650030, "bio_e3_aseptic_technique", "无菌技术操作要点", 3, SUBJECT, G10, 650010),
    (650031, "bio_e3_pure_culture", "微生物的纯培养与单菌落", 4, SUBJECT, G10, 650010),
    (650032, "bio_e3_streak_plate", "平板划线法分离微生物", 5, SUBJECT, G10, 650010),
    (650033, "bio_e3_dilution_plate_count", "稀释涂布平板法分离与活菌计数", 6, SUBJECT, G10, 650010),
    (650034, "bio_e3_ureolytic_bacteria", "土壤中分解尿素的细菌的分离与计数", 7, SUBJECT, G10, 650010),
    (650035, "bio_e3_cellulolytic_bacteria", "分解纤维素的微生物的分离", 8, SUBJECT, G10, 650010),

    # 1.3 发酵工程及其应用
    (650036, "bio_e3_fermentation_engineering_concept", "发酵工程的概念与基本环节", 1, SUBJECT, G10, 650011),
    (650037, "bio_e3_strain_selection", "发酵工程菌种的选育", 2, SUBJECT, G10, 650011),
    (650038, "bio_e3_medium_scale_up", "培养基配制与扩大培养", 3, SUBJECT, G10, 650011),
    (650039, "bio_e3_fermentation_control", "发酵过程的条件控制", 4, SUBJECT, G10, 650011),
    (650040, "bio_e3_fermenter", "发酵罐的结构与类型", 5, SUBJECT, G10, 650011),
    (650041, "bio_e3_product_separation", "发酵产物的分离提纯", 6, SUBJECT, G10, 650011),
    (650042, "bio_e3_fermentation_application", "发酵工程的应用领域", 7, SUBJECT, G10, 650011),

    # 2.1 植物细胞工程
    (650043, "bio_e3_cell_engineering_concept", "细胞工程的概念与分类", 1, SUBJECT, G10, 650012),
    (650044, "bio_e3_tissue_culture_principle", "植物组织培养的原理", 2, SUBJECT, G10, 650012),
    (650045, "bio_e3_tissue_culture_process", "植物组织培养的基本流程", 3, SUBJECT, G10, 650012),
    (650046, "bio_e3_tissue_culture_condition", "植物组织培养的条件与应用", 4, SUBJECT, G10, 650012),
    (650047, "bio_e3_somatic_hybrid_concept", "植物体细胞杂交的概念与意义", 5, SUBJECT, G10, 650012),
    (650048, "bio_e3_somatic_hybrid_process", "植物体细胞杂交的流程", 6, SUBJECT, G10, 650012),
    (650049, "bio_e3_protoplast_fusion", "原生质体融合的方法", 7, SUBJECT, G10, 650012),
    (650050, "bio_e3_anther_culture", "花药离体培养与单倍体育种", 8, SUBJECT, G10, 650012),
    (650051, "bio_e3_plant_cell_product", "植物细胞培养与次生代谢产物", 9, SUBJECT, G10, 650012),

    # 2.2 动物细胞工程
    (650052, "bio_e3_animal_cell_culture_condition", "动物细胞培养的条件", 1, SUBJECT, G10, 650013),
    (650053, "bio_e3_animal_cell_culture_process", "动物细胞培养的过程", 2, SUBJECT, G10, 650013),
    (650054, "bio_e3_contact_inhibition", "动物细胞的贴壁生长与接触抑制", 3, SUBJECT, G10, 650013),
    (650055, "bio_e3_cell_fusion", "动物细胞融合的概念与方法", 4, SUBJECT, G10, 650013),
    (650056, "bio_e3_monoclonal_concept", "单克隆抗体的概念与优点", 5, SUBJECT, G10, 650013),
    (650057, "bio_e3_monoclonal_process", "单克隆抗体的制备流程", 6, SUBJECT, G10, 650013),
    (650058, "bio_e3_hybridoma_screening", "杂交瘤细胞的筛选与培养", 7, SUBJECT, G10, 650013),
    (650059, "bio_e3_nuclear_transfer", "核移植的概念与类型", 8, SUBJECT, G10, 650013),
    (650060, "bio_e3_somatic_nuclear_transfer", "体细胞核移植的过程", 9, SUBJECT, G10, 650013),
    (650061, "bio_e3_cloned_animal_application", "克隆动物的应用与局限", 10, SUBJECT, G10, 650013),

    # 2.3 胚胎工程
    (650062, "bio_e3_embryo_engineering_theory", "胚胎工程的理论基础", 1, SUBJECT, G10, 650014),
    (650063, "bio_e3_ivf_early_embryo", "体外受精与早期胚胎培养", 2, SUBJECT, G10, 650014),
    (650064, "bio_e3_embryo_transfer_split", "胚胎移植与胚胎分割", 3, SUBJECT, G10, 650014),
    (650065, "bio_e3_embryonic_stem_cell", "胚胎干细胞及其应用", 4, SUBJECT, G10, 650014),

    # 3.1 重组DNA技术的基本工具
    (650066, "bio_e3_gene_engineering_concept", "基因工程的概念与操作水平", 1, SUBJECT, G10, 650015),
    (650067, "bio_e3_restriction_enzyme", "限制性核酸内切酶", 2, SUBJECT, G10, 650015),
    (650068, "bio_e3_dna_ligase", "DNA连接酶", 3, SUBJECT, G10, 650015),
    (650069, "bio_e3_vector", "基因表达载体的条件与类型", 4, SUBJECT, G10, 650015),
    (650070, "bio_e3_plasmid", "质粒的结构与标记基因", 5, SUBJECT, G10, 650015),
    (650071, "bio_e3_dna_extraction", "DNA的粗提取与鉴定", 6, SUBJECT, G10, 650015),

    # 3.2 基因工程的基本操作程序
    (650072, "bio_e3_target_gene_obtain", "目的基因的获取途径", 1, SUBJECT, G10, 650016),
    (650073, "bio_e3_gene_library", "基因组文库与cDNA文库", 2, SUBJECT, G10, 650016),
    (650074, "bio_e3_pcr_principle", "PCR的原理与条件", 3, SUBJECT, G10, 650016),
    (650075, "bio_e3_pcr_process", "PCR的过程与扩增计算", 4, SUBJECT, G10, 650016),
    (650076, "bio_e3_expression_vector", "基因表达载体的构建", 5, SUBJECT, G10, 650016),
    (650077, "bio_e3_gene_transfer", "目的基因导入受体细胞的方法", 6, SUBJECT, G10, 650016),
    (650078, "bio_e3_gene_detection", "目的基因的检测与鉴定", 7, SUBJECT, G10, 650016),

    # 3.3 基因工程的应用
    (650079, "bio_e3_gene_application_agriculture", "基因工程在农业与畜牧业的应用", 1, SUBJECT, G10, 650017),
    (650080, "bio_e3_gene_application_medicine", "基因工程在医药领域的应用", 2, SUBJECT, G10, 650017),
    (650081, "bio_e3_gene_therapy", "基因诊断与基因治疗", 3, SUBJECT, G10, 650017),
    (650082, "bio_e3_gene_application_industry", "基因工程在工业与环保的应用", 4, SUBJECT, G10, 650017),

    # 3.4 蛋白质工程的原理和应用
    (650083, "bio_e3_protein_engineering_concept", "蛋白质工程的概念与原理", 1, SUBJECT, G10, 650018),
    (650084, "bio_e3_protein_engineering_process", "蛋白质工程的流程", 2, SUBJECT, G10, 650018),
    (650085, "bio_e3_protein_engineering_application", "蛋白质工程的应用与前景", 3, SUBJECT, G10, 650018),

    # 4.1 转基因产品的安全性
    (650086, "bio_e3_gmo_safety_debate", "转基因产品安全性的争议", 1, SUBJECT, G10, 650019),
    (650087, "bio_e3_gmo_risk_assessment", "转基因产品的安全性评价", 2, SUBJECT, G10, 650019),
    (650088, "bio_e3_gmo_ecology_risk", "转基因生物对生态环境的潜在影响", 3, SUBJECT, G10, 650019),
    (650089, "bio_e3_gmo_management", "转基因生物的安全管理", 4, SUBJECT, G10, 650019),

    # 4.2 关注生殖性克隆人
    (650090, "bio_e3_reproductive_cloning_concept", "生殖性克隆与治疗性克隆", 1, SUBJECT, G10, 650020),
    (650091, "bio_e3_reproductive_cloning_risk", "生殖性克隆人的技术风险", 2, SUBJECT, G10, 650020),
    (650092, "bio_e3_reproductive_cloning_ethics", "生殖性克隆人的伦理问题", 3, SUBJECT, G10, 650020),
    (650093, "bio_e3_cloning_regulation", "我国禁止生殖性克隆人的立场", 4, SUBJECT, G10, 650020),

    # 4.3 禁止生物武器
    (650094, "bio_e3_bioweapon_concept", "生物武器的概念与种类", 1, SUBJECT, G10, 650021),
    (650095, "bio_e3_bioweapon_harm", "生物武器的特点与危害", 2, SUBJECT, G10, 650021),
    (650096, "bio_e3_bioweapon_convention", "《禁止生物武器公约》", 3, SUBJECT, G10, 650021),
    (650097, "bio_e3_biosafety", "生物安全与生物恐怖防范", 4, SUBJECT, G10, 650021),
)

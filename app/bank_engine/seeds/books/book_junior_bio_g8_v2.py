"""人教版初中生物八年级下册：第七、八单元目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 6
G8 = 8
BOOK_ID = 1338

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级生物下册",
    "jbio_g8b",
    38,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133801, "第七单元 生物圈中生命的延续和发展", "jbio_g8b_u7", 1, BOOK_ID, None),

    (133811, "第一章 生物的生殖和发育", "jbio_g8b_u7_c01", 1, BOOK_ID, 133801),
    (133812, "第一节 植物的生殖", "jbio_g8b_u7_c01_s01", 1, BOOK_ID, 133811),
    (133813, "第二节 昆虫的生殖和发育", "jbio_g8b_u7_c01_s02", 2, BOOK_ID, 133811),
    (133814, "第三节 两栖动物的生殖和发育", "jbio_g8b_u7_c01_s03", 3, BOOK_ID, 133811),
    (133815, "第四节 鸟的生殖和发育", "jbio_g8b_u7_c01_s04", 4, BOOK_ID, 133811),

    (133821, "第二章 生物的遗传和变异", "jbio_g8b_u7_c02", 2, BOOK_ID, 133801),
    (133822, "第一节 基因控制生物的性状", "jbio_g8b_u7_c02_s01", 1, BOOK_ID, 133821),
    (133823, "第二节 基因在亲子代间的传递", "jbio_g8b_u7_c02_s02", 2, BOOK_ID, 133821),
    (133824, "第三节 基因的显性和隐性", "jbio_g8b_u7_c02_s03", 3, BOOK_ID, 133821),
    (133825, "第四节 人的性别遗传", "jbio_g8b_u7_c02_s04", 4, BOOK_ID, 133821),
    (133826, "第五节 生物的变异", "jbio_g8b_u7_c02_s05", 5, BOOK_ID, 133821),

    (133831, "第三章 生物的进化", "jbio_g8b_u7_c03", 3, BOOK_ID, 133801),
    (133832, "第一节 地球上生命的起源", "jbio_g8b_u7_c03_s01", 1, BOOK_ID, 133831),
    (133833, "第二节 生物进化的历程", "jbio_g8b_u7_c03_s02", 2, BOOK_ID, 133831),
    (133834, "第三节 生物进化的原因", "jbio_g8b_u7_c03_s03", 3, BOOK_ID, 133831),

    (133841, "第八单元 健康地生活", "jbio_g8b_u8", 2, BOOK_ID, None),
    (133851, "第一章 传染病和免疫", "jbio_g8b_u8_c01", 1, BOOK_ID, 133841),
    (133852, "第一节 传染病及其预防", "jbio_g8b_u8_c01_s01", 1, BOOK_ID, 133851),
    (133853, "第二节 免疫与计划免疫", "jbio_g8b_u8_c01_s02", 2, BOOK_ID, 133851),
    (133861, "第二章 用药和急救", "jbio_g8b_u8_c02", 2, BOOK_ID, 133841),
    (133862, "第一节 安全用药", "jbio_g8b_u8_c02_s01", 1, BOOK_ID, 133861),
    (133863, "第二节 急救", "jbio_g8b_u8_c02_s02", 2, BOOK_ID, 133861),
    (133871, "第三章 了解自己，增进健康", "jbio_g8b_u8_c03", 3, BOOK_ID, 133841),
    (133872, "第一节 评价自己的健康状况", "jbio_g8b_u8_c03_s01", 1, BOOK_ID, 133871),
    (133873, "第二节 选择健康的生活方式", "jbio_g8b_u8_c03_s02", 2, BOOK_ID, 133871),
)

# id / code / name / sort_order / subject_id / parent_id
# 238001 册域顶层，238002-238024 单元、章与节锚点，238025 起为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    (238001, "jbio_g8b_domain", "初中八下·第七、八单元：生物圈中生命的延续和发展与健康地生活", 1, SUBJECT, None),

    # 第七单元 生物圈中生命的延续和发展
    (238002, "jbio_g8b_u7", "初中八下·第七单元 生物圈中生命的延续和发展", 1, SUBJECT, 238001),
    (238003, "jbio_g8b_u7_c01", "初中八下·第一章 生物的生殖和发育：植物、昆虫、两栖动物与鸟", 1, SUBJECT, 238002),
    (238004, "jbio_g8b_u7_c01_s01", "第一节 植物的生殖：有性生殖与无性生殖", 1, SUBJECT, 238003),
    (238005, "jbio_g8b_plant_sexual", "有性生殖与无性生殖的概念及比较：有无两性生殖细胞结合", 1, SUBJECT, 238004),
    (238006, "jbio_g8b_plant_asexual", "无性生殖的常见方式：扦插、嫁接、压条与组织培养", 2, SUBJECT, 238004),
    (238007, "jbio_g8b_graft", "嫁接成活的关键：接穗与砧木的形成层紧密结合", 3, SUBJECT, 238004),
    (238008, "jbio_g8b_plant_application", "植物生殖方式在农业生产中的应用：保持优良性状与快速繁殖", 4, SUBJECT, 238004),
    (238009, "jbio_g8b_u7_c01_s02", "第二节 昆虫的生殖和发育：完全变态与不完全变态", 2, SUBJECT, 238003),
    (238010, "jbio_g8b_insect_reproduce", "昆虫的生殖：体内受精、卵生与受精卵孵化", 1, SUBJECT, 238009),
    (238011, "jbio_g8b_complete_metamorphosis", "完全变态发育：卵→幼虫→蛹→成虫，家蚕与蝴蝶", 2, SUBJECT, 238009),
    (238012, "jbio_g8b_incomplete_metamorphosis", "不完全变态发育：卵→若虫→成虫，蝗虫与蟋蟀", 3, SUBJECT, 238009),
    (238013, "jbio_g8b_insect_human", "昆虫与人类的关系：家蚕吐丝、蝗虫危害与防治", 4, SUBJECT, 238009),
    (238014, "jbio_g8b_u7_c01_s03", "第三节 两栖动物的生殖和发育：抱对、体外受精与变态发育", 3, SUBJECT, 238003),
    (238015, "jbio_g8b_frog_reproduce", "青蛙的生殖行为：雌雄抱对、体外受精、卵生", 1, SUBJECT, 238014),
    (238016, "jbio_g8b_frog_develop", "青蛙的发育过程：受精卵→蝌蚪→幼蛙→成蛙的变态发育", 2, SUBJECT, 238014),
    (238017, "jbio_g8b_tadpole_frog", "蝌蚪与成蛙的形态结构差异：鳃与肺、尾的消失、四肢出现", 3, SUBJECT, 238014),
    (238018, "jbio_g8b_amphibian_water", "两栖动物生殖发育对水环境的依赖与水域保护", 4, SUBJECT, 238014),
    (238019, "jbio_g8b_u7_c01_s04", "第四节 鸟的生殖和发育：繁殖行为、鸟卵结构与发育", 4, SUBJECT, 238003),
    (238020, "jbio_g8b_bird_courtship", "鸟的繁殖行为：求偶、交配、筑巢、产卵、孵卵与育雏", 1, SUBJECT, 238019),
    (238021, "jbio_g8b_egg_structure", "鸟卵的结构：卵壳、卵壳膜、卵白、卵黄、胚盘与气室", 2, SUBJECT, 238019),
    (238022, "jbio_g8b_egg_function", "鸟卵各部分的功能：胚盘含细胞核、卵黄供营养、气室供氧", 3, SUBJECT, 238019),
    (238023, "jbio_g8b_bird_adapt", "鸟卵对陆地生活的适应与早成鸟、晚成鸟的区别", 4, SUBJECT, 238019),

    (238024, "jbio_g8b_u7_c02", "初中八下·第二章 生物的遗传和变异：性状、传递、显隐性与性别", 2, SUBJECT, 238002),
    (238025, "jbio_g8b_u7_c02_s01", "第一节 基因控制生物的性状：遗传变异、相对性状与转基因", 1, SUBJECT, 238024),
    (238026, "jbio_g8b_heredity_variation", "遗传与变异的概念：亲子间的相似性与差异性", 1, SUBJECT, 238025),
    (238027, "jbio_g8b_trait", "性状与相对性状：同种生物同一性状的不同表现形式", 2, SUBJECT, 238025),
    (238028, "jbio_g8b_gene_control", "基因控制生物的性状：转基因鼠实验与转基因技术", 3, SUBJECT, 238025),
    (238029, "jbio_g8b_gene_dna_chromosome", "基因、DNA与染色体的关系：基因是有遗传效应的DNA片段", 4, SUBJECT, 238025),
    (238030, "jbio_g8b_u7_c02_s02", "第二节 基因在亲子代间的传递：配子、染色体减半与成对基因", 2, SUBJECT, 238024),
    (238031, "jbio_g8b_gene_gamete", "基因经精子和卵细胞传递给子代：基因随染色体传递", 1, SUBJECT, 238030),
    (238032, "jbio_g8b_chromosome_meiosis", "生殖过程中染色体数目减半与受精后恢复成对", 2, SUBJECT, 238030),
    (238033, "jbio_g8b_allele_source", "成对基因的来源：一条来自父方、一条来自母方", 3, SUBJECT, 238030),
    (238034, "jbio_g8b_human_chromosome", "人的染色体组成：23对，22对常染色体与1对性染色体", 4, SUBJECT, 238030),
    (238035, "jbio_g8b_u7_c02_s03", "第三节 基因的显性和隐性：孟德尔实验与遗传图解", 3, SUBJECT, 238024),
    (238036, "jbio_g8b_dominant_recessive", "显性基因与隐性基因、显性性状与隐性性状", 1, SUBJECT, 238035),
    (238037, "jbio_g8b_genotype_phenotype", "基因型与表现型：AA、Aa、aa及环境对表现的影响", 2, SUBJECT, 238035),
    (238038, "jbio_g8b_mendel", "孟德尔豌豆杂交实验与遗传图解的规范书写", 3, SUBJECT, 238035),
    (238039, "jbio_g8b_dominance_judge", "显隐性的判断方法：有中生无与无中生有", 4, SUBJECT, 238035),
    (238040, "jbio_g8b_u7_c02_s04", "第四节 人的性别遗传：性染色体、性别决定与概率", 4, SUBJECT, 238024),
    (238041, "jbio_g8b_sex_chromosome", "人的性染色体组成：男性XY、女性XX", 1, SUBJECT, 238040),
    (238042, "jbio_g8b_sex_ratio", "生男生女机会均等及原因：精子含X或Y染色体", 2, SUBJECT, 238040),
    (238043, "jbio_g8b_sex_pedigree", "人的性别决定遗传图解与正确看待性别比例", 3, SUBJECT, 238040),
    (238044, "jbio_g8b_u7_c02_s05", "第五节 生物的变异：类型、意义与育种应用", 5, SUBJECT, 238024),
    (238045, "jbio_g8b_variation_concept", "变异的概念、普遍性与类型划分", 1, SUBJECT, 238044),
    (238046, "jbio_g8b_heritable_variation", "可遗传变异与不可遗传变异：遗传物质改变与环境影响", 2, SUBJECT, 238044),
    (238047, "jbio_g8b_favorable_variation", "有利变异与不利变异及对生物生存的意义", 3, SUBJECT, 238044),
    (238048, "jbio_g8b_breeding", "变异在育种中的应用：选择育种、杂交育种与诱变育种", 4, SUBJECT, 238044),

    (238049, "jbio_g8b_u7_c03", "初中八下·第三章 生物的进化：起源、历程与自然选择", 3, SUBJECT, 238002),
    (238050, "jbio_g8b_u7_c03_s01", "第一节 地球上生命的起源：化学进化说与米勒实验", 1, SUBJECT, 238049),
    (238051, "jbio_g8b_chemical_evolution", "生命起源的化学进化说：无机物→有机小分子→有机大分子→原始生命", 1, SUBJECT, 238050),
    (238052, "jbio_g8b_primitive_earth", "原始地球条件与原始大气成分：无游离氧、高温雷电", 2, SUBJECT, 238050),
    (238053, "jbio_g8b_miller", "米勒实验：模拟原始大气条件合成有机小分子", 3, SUBJECT, 238050),
    (238054, "jbio_g8b_primitive_ocean", "原始生命诞生于原始海洋及生命起源假说的局限", 4, SUBJECT, 238050),
    (238055, "jbio_g8b_u7_c03_s02", "第二节 生物进化的历程：比较法、化石与进化趋势", 2, SUBJECT, 238049),
    (238056, "jbio_g8b_evolution_method", "研究生物进化的方法：比较法、化石与解剖胚胎学证据", 1, SUBJECT, 238055),
    (238057, "jbio_g8b_fossil", "化石是研究生物进化最直接、最重要的证据", 2, SUBJECT, 238055),
    (238058, "jbio_g8b_evolution_trend", "生物进化的总体趋势：由简单到复杂、由低等到高等、由水生到陆生", 3, SUBJECT, 238055),
    (238059, "jbio_g8b_evolution_path", "植物与动物进化的主要历程：藻类到种子植物、鱼类到哺乳类", 4, SUBJECT, 238055),
    (238060, "jbio_g8b_u7_c03_s03", "第三节 生物进化的原因：自然选择学说及其应用", 3, SUBJECT, 238049),
    (238061, "jbio_g8b_natural_selection", "自然选择学说的主要内容：过度繁殖、生存斗争、遗传变异、适者生存", 1, SUBJECT, 238060),
    (238062, "jbio_g8b_darwin", "达尔文与《物种起源》及进化学说的意义", 2, SUBJECT, 238060),
    (238063, "jbio_g8b_selection_example", "自然选择的实例：长颈鹿进化、抗药性与保护色", 3, SUBJECT, 238060),

    # 第八单元 健康地生活
    (238064, "jbio_g8b_u8", "初中八下·第八单元 健康地生活", 2, SUBJECT, 238001),
    (238065, "jbio_g8b_u8_c01", "初中八下·第一章 传染病和免疫：流行环节、预防与免疫防线", 1, SUBJECT, 238064),
    (238066, "jbio_g8b_u8_c01_s01", "第一节 传染病及其预防：病原体、三个环节与预防措施", 1, SUBJECT, 238065),
    (238067, "jbio_g8b_infectious_concept", "传染病的概念、特点与病原体的种类", 1, SUBJECT, 238066),
    (238068, "jbio_g8b_three_links", "传染病流行的三个环节：传染源、传播途径与易感人群", 2, SUBJECT, 238066),
    (238069, "jbio_g8b_prevention", "预防传染病的三项措施与常见传染病实例", 3, SUBJECT, 238066),
    (238070, "jbio_g8b_aids", "艾滋病的传播途径与预防：血液、性接触与母婴传播", 4, SUBJECT, 238066),
    (238071, "jbio_g8b_u8_c01_s02", "第二节 免疫与计划免疫：三道防线、抗原抗体与疫苗", 2, SUBJECT, 238065),
    (238072, "jbio_g8b_three_defenses", "人体的三道防线及其组成", 1, SUBJECT, 238071),
    (238073, "jbio_g8b_nonspecific", "第一、二道防线与非特异性免疫：皮肤黏膜、杀菌物质与吞噬细胞", 2, SUBJECT, 238071),
    (238074, "jbio_g8b_specific", "第三道防线与特异性免疫：免疫器官和免疫细胞", 3, SUBJECT, 238071),
    (238075, "jbio_g8b_antigen_antibody", "抗原与抗体的概念及对应关系", 4, SUBJECT, 238071),
    (238076, "jbio_g8b_immunity_compare", "非特异性免疫与特异性免疫的比较", 5, SUBJECT, 238071),
    (238077, "jbio_g8b_planned_immunity", "计划免疫的概念、疫苗的作用与意义", 6, SUBJECT, 238071),
    (238078, "jbio_g8b_immunity_function", "免疫的功能与免疫异常：过敏反应与器官移植排斥", 7, SUBJECT, 238071),

    (238079, "jbio_g8b_u8_c02", "初中八下·第二章 用药和急救：安全用药与急救技能", 2, SUBJECT, 238064),
    (238080, "jbio_g8b_u8_c02_s01", "第一节 安全用药：处方药、非处方药与用药常识", 1, SUBJECT, 238079),
    (238081, "jbio_g8b_safe_medication", "安全用药与处方药、非处方药的区别", 1, SUBJECT, 238080),
    (238082, "jbio_g8b_medication_notice", "用药注意事项：按说明书、剂量、有效期与家庭小药箱", 2, SUBJECT, 238080),
    (238083, "jbio_g8b_u8_c02_s02", "第二节 急救：呼救、心肺复苏与常见意外处理", 2, SUBJECT, 238079),
    (238084, "jbio_g8b_emergency_call", "紧急呼救120与急救的基本原则", 1, SUBJECT, 238083),
    (238085, "jbio_g8b_cpr", "人工呼吸与胸外心脏按压的操作要点", 2, SUBJECT, 238083),
    (238086, "jbio_g8b_bleeding_fracture", "出血、骨折与溺水的急救处理", 3, SUBJECT, 238083),

    (238087, "jbio_g8b_u8_c03", "初中八下·第三章 了解自己，增进健康：健康评价与生活方式", 3, SUBJECT, 238064),
    (238088, "jbio_g8b_u8_c03_s01", "第一节 评价自己的健康状况：健康含义与情绪调节", 1, SUBJECT, 238087),
    (238089, "jbio_g8b_health_definition", "健康的定义：身体、心理和社会适应良好", 1, SUBJECT, 238088),
    (238090, "jbio_g8b_health_evaluate", "健康评价的方法与心理健康的标准", 2, SUBJECT, 238088),
    (238091, "jbio_g8b_emotion", "调节情绪的方法：转移注意力、宣泄与自我安慰", 3, SUBJECT, 238088),
    (238092, "jbio_g8b_u8_c03_s02", "第二节 选择健康的生活方式：影响因素与健康行为", 2, SUBJECT, 238087),
    (238093, "jbio_g8b_lifestyle_effect", "生活方式对健康的影响与慢性病的发生", 1, SUBJECT, 238092),
    (238094, "jbio_g8b_healthy_lifestyle", "健康的生活方式：合理膳食、适量运动与规律作息", 2, SUBJECT, 238092),
    (238095, "jbio_g8b_bad_habits", "吸烟、酗酒、吸毒与网络成瘾的危害及拒绝方法", 3, SUBJECT, 238092),
)

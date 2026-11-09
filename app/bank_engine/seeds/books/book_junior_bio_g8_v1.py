"""人教版初中生物八年级上册：第五、六单元目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 6
G8 = 8
BOOK_ID = 1337

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级生物上册",
    "jbio_g8a",
    37,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133701, "第五单元 生物圈中的其他生物", "jbio_g8a_u5", 1, BOOK_ID, None),

    (133711, "第一章 动物的主要类群", "jbio_g8a_u5_c01", 1, BOOK_ID, 133701),
    (133712, "第一节 腔肠动物和扁形动物", "jbio_g8a_u5_c01_s01", 1, BOOK_ID, 133711),
    (133713, "第二节 线形动物和环节动物", "jbio_g8a_u5_c01_s02", 2, BOOK_ID, 133711),
    (133714, "第三节 软体动物和节肢动物", "jbio_g8a_u5_c01_s03", 3, BOOK_ID, 133711),
    (133715, "第四节 鱼", "jbio_g8a_u5_c01_s04", 4, BOOK_ID, 133711),
    (133716, "第五节 两栖动物和爬行动物", "jbio_g8a_u5_c01_s05", 5, BOOK_ID, 133711),
    (133717, "第六节 鸟", "jbio_g8a_u5_c01_s06", 6, BOOK_ID, 133711),
    (133718, "第七节 哺乳动物", "jbio_g8a_u5_c01_s07", 7, BOOK_ID, 133711),

    (133721, "第二章 动物的运动和行为", "jbio_g8a_u5_c02", 2, BOOK_ID, 133701),
    (133722, "第一节 动物的运动", "jbio_g8a_u5_c02_s01", 1, BOOK_ID, 133721),
    (133723, "第二节 先天性行为和学习行为", "jbio_g8a_u5_c02_s02", 2, BOOK_ID, 133721),
    (133724, "第三节 社会行为", "jbio_g8a_u5_c02_s03", 3, BOOK_ID, 133721),

    (133731, "第三章 动物在生物圈中的作用", "jbio_g8a_u5_c03", 3, BOOK_ID, 133701),

    (133741, "第四章 细菌和真菌", "jbio_g8a_u5_c04", 4, BOOK_ID, 133701),
    (133742, "第一节 细菌和真菌的分布", "jbio_g8a_u5_c04_s01", 1, BOOK_ID, 133741),
    (133743, "第二节 细菌", "jbio_g8a_u5_c04_s02", 2, BOOK_ID, 133741),
    (133744, "第三节 真菌", "jbio_g8a_u5_c04_s03", 3, BOOK_ID, 133741),
    (133745, "第四节 细菌和真菌在自然界中的作用", "jbio_g8a_u5_c04_s04", 4, BOOK_ID, 133741),
    (133746, "第五节 人类对细菌和真菌的利用", "jbio_g8a_u5_c04_s05", 5, BOOK_ID, 133741),

    (133751, "第五章 病毒", "jbio_g8a_u5_c05", 5, BOOK_ID, 133701),

    (133761, "第六单元 生物的多样性及其保护", "jbio_g8a_u6", 2, BOOK_ID, None),
    (133771, "第一章 根据生物的特征进行分类", "jbio_g8a_u6_c01", 1, BOOK_ID, 133761),
    (133772, "第一节 尝试对生物进行分类", "jbio_g8a_u6_c01_s01", 1, BOOK_ID, 133771),
    (133773, "第二节 从种到界", "jbio_g8a_u6_c01_s02", 2, BOOK_ID, 133771),
    (133781, "第二章 认识生物的多样性", "jbio_g8a_u6_c02", 2, BOOK_ID, 133761),
    (133791, "第三章 保护生物的多样性", "jbio_g8a_u6_c03", 3, BOOK_ID, 133761),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 237001 册域顶层，237002-237011 单元与章锚点，237012-237028 节锚点，237029 起为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    (237001, "jbio_g8a_domain", "初中八上·第五、六单元：生物圈中的其他生物与生物的多样性及其保护", 1, SUBJECT, G8, None),

    # 第五单元 生物圈中的其他生物
    (237002, "jbio_g8a_u5", "初中八上·第五单元 生物圈中的其他生物", 1, SUBJECT, G8, 237001),
    (237003, "jbio_g8a_u5_c01", "初中八上·第一章 动物的主要类群：无脊椎动物与脊椎动物", 1, SUBJECT, G8, 237002),
    (237012, "jbio_g8a_u5_c01_s01", "第一节 腔肠动物和扁形动物：辐射对称、刺细胞与寄生适应", 1, SUBJECT, G8, 237003),
    (237029, "jbio_g8a_cnidarian", "腔肠动物的主要特征：辐射对称、刺细胞、有口无肛门", 1, SUBJECT, G8, 237012),
    (237030, "jbio_g8a_platyhelminth", "扁形动物的主要特征：两侧对称、背腹扁平、有口无肛门", 2, SUBJECT, G8, 237012),
    (237031, "jbio_g8a_parasite", "寄生虫的寄生生活：华枝睾吸虫、猪肉绦虫与预防感染", 3, SUBJECT, G8, 237012),
    (237013, "jbio_g8a_u5_c01_s02", "第二节 线形动物和环节动物：角质层、体节与刚毛", 2, SUBJECT, G8, 237003),
    (237032, "jbio_g8a_nematode", "线形动物的主要特征：蛔虫体表角质层、有口有肛门", 1, SUBJECT, G8, 237013),
    (237033, "jbio_g8a_annelid", "环节动物的主要特征：蚯蚓身体分节、刚毛与湿润体壁呼吸", 2, SUBJECT, G8, 237013),
    (237034, "jbio_g8a_earthworm", "观察蚯蚓的实验与环节动物和人类生活的关系", 3, SUBJECT, G8, 237013),
    (237014, "jbio_g8a_u5_c01_s03", "第三节 软体动物和节肢动物：外套膜、外骨骼与分节附肢", 3, SUBJECT, G8, 237003),
    (237035, "jbio_g8a_mollusk", "软体动物的主要特征：外套膜、贝壳、足与鳃", 1, SUBJECT, G8, 237014),
    (237036, "jbio_g8a_arthropod", "节肢动物的主要特征：外骨骼、身体分部、分节附肢与蜕皮现象", 2, SUBJECT, G8, 237014),
    (237037, "jbio_g8a_insect", "昆虫的主要特征：三对足、两对翅、气门与气管呼吸", 3, SUBJECT, G8, 237014),
    (237015, "jbio_g8a_u5_c01_s04", "第四节 鱼：鳃呼吸、鳍游泳与水中生活", 4, SUBJECT, G8, 237003),
    (237038, "jbio_g8a_fish_feature", "鱼的主要特征：体表鳞片与黏液、鳃呼吸、鳍游泳、侧线感知", 1, SUBJECT, G8, 237015),
    (237039, "jbio_g8a_fish_fins", "鱼鳍的组成与作用：尾鳍控制方向、胸鳍腹鳍保持平衡", 2, SUBJECT, G8, 237015),
    (237040, "jbio_g8a_gill", "鳃的结构与气体交换：鳃丝密布毛细血管", 3, SUBJECT, G8, 237015),
    (237016, "jbio_g8a_u5_c01_s05", "第五节 两栖动物和爬行动物：变态发育与陆生适应", 5, SUBJECT, G8, 237003),
    (237041, "jbio_g8a_amphibian", "两栖动物的主要特征：幼体水生鳃呼吸、成体肺和皮肤辅助呼吸、变态发育", 1, SUBJECT, G8, 237016),
    (237042, "jbio_g8a_reptile", "爬行动物的主要特征：角质鳞片、肺呼吸、卵生且卵有坚韧卵壳", 2, SUBJECT, G8, 237016),
    (237017, "jbio_g8a_u5_c01_s06", "第六节 鸟：羽毛、翼与双重呼吸", 6, SUBJECT, G8, 237003),
    (237043, "jbio_g8a_bird_feature", "鸟的主要特征：体表羽毛、前肢变成翼、有喙无齿、体温恒定、卵生", 1, SUBJECT, G8, 237017),
    (237044, "jbio_g8a_bird_flight", "家鸽适于飞行的特点：流线型体形、骨骼轻、胸肌发达、食量大消化快", 2, SUBJECT, G8, 237017),
    (237045, "jbio_g8a_double_breathing", "双重呼吸与气囊的作用：一次吸气完成两次气体交换", 3, SUBJECT, G8, 237017),
    (237018, "jbio_g8a_u5_c01_s07", "第七节 哺乳动物：胎生哺乳与牙齿分化", 7, SUBJECT, G8, 237003),
    (237046, "jbio_g8a_mammal_feature", "哺乳动物的主要特征：体表被毛、胎生哺乳、牙齿分化、体温恒定", 1, SUBJECT, G8, 237018),
    (237047, "jbio_g8a_teeth_diff", "牙齿分化：门齿、犬齿、臼齿与食性适应", 2, SUBJECT, G8, 237018),
    (237048, "jbio_g8a_viviparous", "胎生哺乳的意义与哺乳动物的多样性", 3, SUBJECT, G8, 237018),

    (237004, "jbio_g8a_u5_c02", "初中八上·第二章 动物的运动和行为：运动系统、行为类型与社会行为", 2, SUBJECT, G8, 237002),
    (237019, "jbio_g8a_u5_c02_s01", "第一节 动物的运动：运动系统、关节与骨骼肌", 1, SUBJECT, G8, 237004),
    (237049, "jbio_g8a_motion_system", "运动系统的组成：骨、关节与骨骼肌", 1, SUBJECT, G8, 237019),
    (237050, "jbio_g8a_joint", "关节的结构与牢固灵活：关节面、关节囊、关节腔与关节软骨", 2, SUBJECT, G8, 237019),
    (237051, "jbio_g8a_muscle_action", "骨骼肌的结构与运动的产生：骨骼肌收缩牵拉骨绕关节活动", 3, SUBJECT, G8, 237019),
    (237052, "jbio_g8a_flexion", "屈肘与伸肘的肌肉配合：肱二头肌与肱三头肌协调", 4, SUBJECT, G8, 237019),
    (237020, "jbio_g8a_u5_c02_s02", "第二节 先天性行为和学习行为：概念、实例与比较", 2, SUBJECT, G8, 237004),
    (237053, "jbio_g8a_innate_behavior", "先天性行为的概念与实例：蜘蛛结网、蜜蜂采蜜、鸟育雏", 1, SUBJECT, G8, 237020),
    (237054, "jbio_g8a_learned_behavior", "学习行为的概念与实例：蚯蚓走迷宫、大山雀喝牛奶、黑猩猩钓白蚁", 2, SUBJECT, G8, 237020),
    (237055, "jbio_g8a_behavior_compare", "先天性行为与学习行为的比较：遗传决定与环境经验", 3, SUBJECT, G8, 237020),
    (237056, "jbio_g8a_behavior_method", "研究动物行为的方法：观察法与实验法", 4, SUBJECT, G8, 237020),
    (237021, "jbio_g8a_u5_c02_s03", "第三节 社会行为：特征、信息交流与意义", 3, SUBJECT, G8, 237004),
    (237057, "jbio_g8a_social_behavior", "社会行为的主要特征：群体分工、等级次序与共同维持群体", 1, SUBJECT, G8, 237021),
    (237058, "jbio_g8a_communication", "动物群体的信息交流方式：声音、气味与动作及社会行为的意义", 2, SUBJECT, G8, 237021),

    (237005, "jbio_g8a_u5_c03", "初中八上·第三章 动物在生物圈中的作用：生态平衡、物质循环与传粉", 3, SUBJECT, G8, 237002),
    (237059, "jbio_g8a_balance", "动物维持生态平衡并促进生态系统物质循环", 1, SUBJECT, G8, 237005),
    (237060, "jbio_g8a_pollination", "动物帮助植物传粉和传播种子", 2, SUBJECT, G8, 237005),
    (237061, "jbio_g8a_animal_human", "动物与人类生活的关系：仿生、生物反应器与生态旅游", 3, SUBJECT, G8, 237005),

    (237006, "jbio_g8a_u5_c04", "初中八上·第四章 细菌和真菌：分布、结构、作用与利用", 4, SUBJECT, G8, 237002),
    (237022, "jbio_g8a_u5_c04_s01", "第一节 细菌和真菌的分布：菌落、培养与生存条件", 1, SUBJECT, G8, 237006),
    (237062, "jbio_g8a_colony", "菌落与培养细菌和真菌的一般方法：配制培养基、灭菌、接种、恒温培养", 1, SUBJECT, G8, 237022),
    (237063, "jbio_g8a_microbe_condition", "细菌和真菌的生存条件、广泛分布与探究实验设计", 2, SUBJECT, G8, 237022),
    (237023, "jbio_g8a_u5_c04_s02", "第二节 细菌：形态、结构、营养与繁殖", 2, SUBJECT, G8, 237006),
    (237064, "jbio_g8a_bacteria_shape", "细菌的形态类型：球菌、杆菌与螺旋菌", 1, SUBJECT, G8, 237023),
    (237065, "jbio_g8a_bacteria_structure", "细菌的结构特点：有细胞壁但无成形细胞核，部分有荚膜和鞭毛", 2, SUBJECT, G8, 237023),
    (237066, "jbio_g8a_bacteria_reproduce", "细菌的营养方式与分裂生殖", 3, SUBJECT, G8, 237023),
    (237067, "jbio_g8a_spore", "芽孢的形成与意义：细菌的休眠体而非生殖细胞", 4, SUBJECT, G8, 237023),
    (237024, "jbio_g8a_u5_c04_s03", "第三节 真菌：类型、结构与孢子生殖", 3, SUBJECT, G8, 237006),
    (237068, "jbio_g8a_fungi_type", "真菌的类型：单细胞酵母菌与多细胞霉菌、蘑菇", 1, SUBJECT, G8, 237024),
    (237069, "jbio_g8a_fungi_structure", "真菌的结构特点：有细胞核、无叶绿体", 2, SUBJECT, G8, 237024),
    (237070, "jbio_g8a_fungi_reproduce", "真菌的孢子生殖与异养营养方式", 3, SUBJECT, G8, 237024),
    (237025, "jbio_g8a_u5_c04_s04", "第四节 细菌和真菌在自然界中的作用：分解、致病与共生", 4, SUBJECT, G8, 237006),
    (237071, "jbio_g8a_decomposer", "细菌和真菌作为分解者参与物质循环", 1, SUBJECT, G8, 237025),
    (237072, "jbio_g8a_pathogen", "细菌和真菌引起动植物和人患病", 2, SUBJECT, G8, 237025),
    (237073, "jbio_g8a_symbiosis", "细菌和真菌与动植物共生：根瘤菌、地衣与肠道菌群", 3, SUBJECT, G8, 237025),
    (237026, "jbio_g8a_u5_c04_s05", "第五节 人类对细菌和真菌的利用：食品、保存、医药与环保", 5, SUBJECT, G8, 237006),
    (237074, "jbio_g8a_food_making", "细菌和真菌在食品制作中的应用：酵母菌、乳酸菌与醋酸菌", 1, SUBJECT, G8, 237026),
    (237075, "jbio_g8a_food_preserve", "食品腐败的原因与食品保存的原理和方法", 2, SUBJECT, G8, 237026),
    (237076, "jbio_g8a_antibiotic", "抗生素与细菌和真菌在疾病防治中的应用", 3, SUBJECT, G8, 237026),
    (237077, "jbio_g8a_bio_environment", "细菌在环境保护中的应用：沼气发酵与污水处理", 4, SUBJECT, G8, 237026),

    (237007, "jbio_g8a_u5_c05", "初中八上·第五章 病毒：结构、类型与人类关系", 5, SUBJECT, G8, 237002),
    (237078, "jbio_g8a_virus_structure", "病毒的结构特征：无细胞结构，由蛋白质外壳和内部遗传物质组成", 1, SUBJECT, G8, 237007),
    (237079, "jbio_g8a_virus_type", "病毒的类型：动物病毒、植物病毒与细菌病毒（噬菌体）", 2, SUBJECT, G8, 237007),
    (237080, "jbio_g8a_virus_reproduce", "病毒的寄生生活与增殖方式：依靠寄主细胞自我复制", 3, SUBJECT, G8, 237007),
    (237081, "jbio_g8a_virus_human", "病毒与人类的关系：致病、疫苗、转基因载体与生物防治", 4, SUBJECT, G8, 237007),

    # 第六单元 生物的多样性及其保护
    (237008, "jbio_g8a_u6", "初中八上·第六单元 生物的多样性及其保护", 2, SUBJECT, G8, 237001),
    (237009, "jbio_g8a_u6_c01", "初中八上·第一章 根据生物的特征进行分类：分类依据与等级", 1, SUBJECT, G8, 237008),
    (237027, "jbio_g8a_u6_c01_s01", "第一节 尝试对生物进行分类：分类依据与方法", 1, SUBJECT, G8, 237009),
    (237082, "jbio_g8a_classify_basis", "生物分类的依据：形态结构、生理功能与生活习性", 1, SUBJECT, G8, 237027),
    (237083, "jbio_g8a_classify_plant", "尝试对植物进行分类：藻类、苔藓、蕨类与种子植物", 2, SUBJECT, G8, 237027),
    (237084, "jbio_g8a_classify_animal", "尝试对动物进行分类：无脊椎动物与脊椎动物", 3, SUBJECT, G8, 237027),
    (237028, "jbio_g8a_u6_c01_s02", "第二节 从种到界：分类等级与双名法", 2, SUBJECT, G8, 237009),
    (237085, "jbio_g8a_taxonomy_rank", "生物分类的等级：界、门、纲、目、科、属、种", 1, SUBJECT, G8, 237028),
    (237086, "jbio_g8a_species_unit", "种是最基本的分类单位与同种生物的共同特征", 2, SUBJECT, G8, 237028),
    (237087, "jbio_g8a_binomial", "双名法：属名加种加词，由林奈提出", 3, SUBJECT, G8, 237028),

    (237010, "jbio_g8a_u6_c02", "初中八上·第二章 认识生物的多样性：三个层次", 2, SUBJECT, G8, 237008),
    (237088, "jbio_g8a_diversity_species", "生物种类的多样性：物种丰富程度", 1, SUBJECT, G8, 237010),
    (237089, "jbio_g8a_diversity_gene", "基因的多样性：种内基因差异与遗传基础", 2, SUBJECT, G8, 237010),
    (237090, "jbio_g8a_diversity_ecosystem", "生态系统的多样性：生态系统类型与结构差异", 3, SUBJECT, G8, 237010),
    (237091, "jbio_g8a_diversity_relation", "生物多样性三个层次之间的关系", 4, SUBJECT, G8, 237010),
    (237092, "jbio_g8a_diversity_china", "我国生物多样性的特点：物种丰富、特有种类多", 5, SUBJECT, G8, 237010),

    (237011, "jbio_g8a_u6_c03", "初中八上·第三章 保护生物的多样性：威胁与保护措施", 3, SUBJECT, G8, 237008),
    (237093, "jbio_g8a_diversity_threat", "生物多样性面临的威胁：栖息地破坏、滥捕滥采与环境污染", 1, SUBJECT, G8, 237011),
    (237094, "jbio_g8a_in_situ", "就地保护：建立自然保护区", 2, SUBJECT, G8, 237011),
    (237095, "jbio_g8a_ex_situ", "迁地保护：动物园、植物园、水族馆与种质库", 3, SUBJECT, G8, 237011),
    (237096, "jbio_g8a_law_education", "保护生物多样性的法律保障与宣传教育", 4, SUBJECT, G8, 237011),
    (237097, "jbio_g8a_diversity_significance", "保护生物多样性的意义", 5, SUBJECT, G8, 237011),
    (237098, "jbio_g8a_sustainable", "可持续发展与生物资源的合理利用", 6, SUBJECT, G8, 237011),
    (237099, "jbio_g8a_invasive", "外来物种入侵的危害与生态安全", 7, SUBJECT, G8, 237011),
)

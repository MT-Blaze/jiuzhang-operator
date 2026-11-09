"""人教版（2019）高中化学选择性必修第二册：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 5
G10 = 10
BOOK_ID = 5104

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中化学选择性必修第二册（物质结构与性质）",
    "chem_e2",
    4,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (540101, "第一章 原子结构与性质", "chem_e2_ch01", 1, BOOK_ID, None),
    (540102, "第二章 分子结构与性质", "chem_e2_ch02", 2, BOOK_ID, None),
    (540103, "第三章 晶体结构与性质", "chem_e2_ch03", 3, BOOK_ID, None),
    (540111, "第一节 原子结构", "chem_e2_ch01_s01", 1, BOOK_ID, 540101),
    (540112, "第二节 原子结构与元素的性质", "chem_e2_ch01_s02", 2, BOOK_ID, 540101),
    (540121, "第一节 共价键", "chem_e2_ch02_s01", 1, BOOK_ID, 540102),
    (540122, "第二节 分子的空间结构", "chem_e2_ch02_s02", 2, BOOK_ID, 540102),
    (540123, "第三节 分子结构与物质的性质", "chem_e2_ch02_s03", 3, BOOK_ID, 540102),
    (540131, "第一节 物质的聚集状态与晶体的常识", "chem_e2_ch03_s01", 1, BOOK_ID, 540103),
    (540132, "第二节 分子晶体与共价晶体", "chem_e2_ch03_s02", 2, BOOK_ID, 540103),
    (540133, "第三节 金属晶体与离子晶体", "chem_e2_ch03_s03", 3, BOOK_ID, 540103),
    (540134, "第四节 配合物与超分子", "chem_e2_ch03_s04", 4, BOOK_ID, 540103),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (540001, "chem_e2_atom_probe", "原子结构探微", 1, SUBJECT, G10, None),
    (540002, "chem_e2_molecule_probe", "分子结构探微", 2, SUBJECT, G10, None),
    (540003, "chem_e2_crystal_probe", "晶体结构探微", 3, SUBJECT, G10, None),

    # 章域层
    (540004, "chem_e2_ch01", "原子结构与性质", 1, SUBJECT, G10, 540001),
    (540005, "chem_e2_ch02", "分子结构与性质", 1, SUBJECT, G10, 540002),
    (540006, "chem_e2_ch03", "晶体结构与性质", 1, SUBJECT, G10, 540003),

    # 节域层
    (540007, "chem_e2_section_atom_structure", "第一节 原子结构", 1, SUBJECT, G10, 540004),
    (540008, "chem_e2_section_atom_property", "第二节 原子结构与元素的性质", 2, SUBJECT, G10, 540004),
    (540009, "chem_e2_section_covalent", "第一节 共价键", 1, SUBJECT, G10, 540005),
    (540010, "chem_e2_section_molecule_shape", "第二节 分子的空间结构", 2, SUBJECT, G10, 540005),
    (540011, "chem_e2_section_molecule_property", "第三节 分子结构与物质的性质", 3, SUBJECT, G10, 540005),
    (540012, "chem_e2_section_crystal_basic", "第一节 物质的聚集状态与晶体的常识", 1, SUBJECT, G10, 540006),
    (540013, "chem_e2_section_molecular_covalent", "第二节 分子晶体与共价晶体", 2, SUBJECT, G10, 540006),
    (540014, "chem_e2_section_metal_ionic", "第三节 金属晶体与离子晶体", 3, SUBJECT, G10, 540006),
    (540015, "chem_e2_section_complex_supramolecule", "第四节 配合物与超分子", 4, SUBJECT, G10, 540006),

    # 1.1 原子结构
    (540016, "chem_e2_atom_composition", "原子的构成与同位素", 1, SUBJECT, G10, 540007),
    (540017, "chem_e2_electron_cloud", "核外电子运动与电子云", 2, SUBJECT, G10, 540007),
    (540018, "chem_e2_energy_level", "能层、能级与构造原理", 3, SUBJECT, G10, 540007),
    (540019, "chem_e2_electron_config", "电子排布式与简化电子排布式", 4, SUBJECT, G10, 540007),
    (540020, "chem_e2_orbital_diagram", "轨道表示式", 5, SUBJECT, G10, 540007),
    (540021, "chem_e2_excited_spectrum", "基态、激发态与原子光谱", 6, SUBJECT, G10, 540007),
    (540022, "chem_e2_atomic_orbital", "原子轨道的形状与数目", 7, SUBJECT, G10, 540007),
    (540023, "chem_e2_build_rules", "泡利原理、洪特规则与能量最低原理", 8, SUBJECT, G10, 540007),
    (540024, "chem_e2_config_exception", "价电子排布与铬、铜的排布例外", 9, SUBJECT, G10, 540007),

    # 1.2 原子结构与元素的性质
    (540025, "chem_e2_atomic_radius", "原子半径的递变规律", 1, SUBJECT, G10, 540008),
    (540026, "chem_e2_ionization_energy", "电离能的概念与逐级电离能", 2, SUBJECT, G10, 540008),
    (540027, "chem_e2_first_ionization", "第一电离能的周期性变化", 3, SUBJECT, G10, 540008),
    (540028, "chem_e2_electronegativity", "电负性的概念与递变", 4, SUBJECT, G10, 540008),
    (540029, "chem_e2_electronegativity_application", "电负性与化合价、金属性和非金属性", 5, SUBJECT, G10, 540008),
    (540030, "chem_e2_diagonal_rule", "对角线规则", 6, SUBJECT, G10, 540008),
    (540031, "chem_e2_element_block", "价电子与元素分区", 7, SUBJECT, G10, 540008),
    (540032, "chem_e2_position_structure", "原子结构与周期表位置的关系", 8, SUBJECT, G10, 540008),
    (540033, "chem_e2_periodic_application", "元素性质递变规律的综合应用", 9, SUBJECT, G10, 540008),

    # 2.1 共价键
    (540034, "chem_e2_covalent_essence", "共价键的本质与形成条件", 1, SUBJECT, G10, 540009),
    (540035, "chem_e2_covalent_saturation", "共价键的饱和性与方向性", 2, SUBJECT, G10, 540009),
    (540036, "chem_e2_sigma_bond", "σ键的形成与特征", 3, SUBJECT, G10, 540009),
    (540037, "chem_e2_pi_bond", "π键的形成与特征", 4, SUBJECT, G10, 540009),
    (540038, "chem_e2_multiple_bond", "单键、双键、三键的成键组成", 5, SUBJECT, G10, 540009),
    (540039, "chem_e2_bond_parameters", "键能、键长与键角", 6, SUBJECT, G10, 540009),
    (540040, "chem_e2_bond_energy_application", "键能与分子稳定性、反应热", 7, SUBJECT, G10, 540009),
    (540041, "chem_e2_polar_bond", "极性键与非极性键", 8, SUBJECT, G10, 540009),
    (540042, "chem_e2_coordinate_bond", "配位键的形成与表示", 9, SUBJECT, G10, 540009),

    # 2.2 分子的空间结构
    (540043, "chem_e2_vsepr_model", "价层电子对互斥模型的基本要点", 1, SUBJECT, G10, 540010),
    (540044, "chem_e2_vsepr_count", "价层电子对数的计算", 2, SUBJECT, G10, 540010),
    (540045, "chem_e2_lone_pair_repulsion", "孤电子对的排斥作用", 3, SUBJECT, G10, 540010),
    (540046, "chem_e2_shape_judge", "常见分子的空间构型判断", 4, SUBJECT, G10, 540010),
    (540047, "chem_e2_hybridization_basic", "杂化轨道理论的基本观点", 5, SUBJECT, G10, 540010),
    (540048, "chem_e2_hybrid_types", "sp、sp²、sp³杂化轨道", 6, SUBJECT, G10, 540010),
    (540049, "chem_e2_hybrid_shape", "杂化类型与空间构型的对应", 7, SUBJECT, G10, 540010),
    (540050, "chem_e2_isoelectronic", "等电子体的概念与判断", 8, SUBJECT, G10, 540010),
    (540051, "chem_e2_shape_method", "空间结构判断的综合方法", 9, SUBJECT, G10, 540010),

    # 2.3 分子结构与物质的性质
    (540052, "chem_e2_molecule_polarity", "分子极性的判断", 1, SUBJECT, G10, 540011),
    (540053, "chem_e2_polar_molecule", "极性分子与非极性分子", 2, SUBJECT, G10, 540011),
    (540054, "chem_e2_vdw_force", "范德华力的本质与特点", 3, SUBJECT, G10, 540011),
    (540055, "chem_e2_vdw_property", "范德华力对物质性质的影响", 4, SUBJECT, G10, 540011),
    (540056, "chem_e2_hydrogen_bond", "氢键的形成条件与本质", 5, SUBJECT, G10, 540011),
    (540057, "chem_e2_hydrogen_bond_effect", "氢键对物质性质的影响", 6, SUBJECT, G10, 540011),
    (540058, "chem_e2_hydrogen_bond_type", "分子内氢键与分子间氢键", 7, SUBJECT, G10, 540011),
    (540059, "chem_e2_like_dissolves_like", "相似相溶原理", 8, SUBJECT, G10, 540011),
    (540060, "chem_e2_chirality", "手性分子与手性异构", 9, SUBJECT, G10, 540011),

    # 3.1 物质的聚集状态与晶体的常识
    (540061, "chem_e2_aggregate_state", "物质的聚集状态与等离子体", 1, SUBJECT, G10, 540012),
    (540062, "chem_e2_crystal_feature", "晶体的特征与各向异性", 2, SUBJECT, G10, 540012),
    (540063, "chem_e2_unit_cell", "晶胞的概念与均摊法", 3, SUBJECT, G10, 540012),
    (540064, "chem_e2_unit_cell_count", "晶胞中微粒数目的计算", 4, SUBJECT, G10, 540012),
    (540065, "chem_e2_coordination_number", "配位数与晶胞参数", 5, SUBJECT, G10, 540012),
    (540066, "chem_e2_xrd", "晶体的X射线衍射", 6, SUBJECT, G10, 540012),
    (540067, "chem_e2_crystal_type_judge", "晶体类型的判断方法", 7, SUBJECT, G10, 540012),
    (540068, "chem_e2_amorphous", "非晶体与准晶", 8, SUBJECT, G10, 540012),
    (540069, "chem_e2_crystal_density", "晶体密度的计算", 9, SUBJECT, G10, 540012),

    # 3.2 分子晶体与共价晶体
    (540070, "chem_e2_molecular_crystal", "分子晶体的构成与性质", 1, SUBJECT, G10, 540013),
    (540071, "chem_e2_molecular_crystal_melting", "分子晶体熔沸点的比较", 2, SUBJECT, G10, 540013),
    (540072, "chem_e2_dry_ice_ice", "干冰与冰的晶体结构", 3, SUBJECT, G10, 540013),
    (540073, "chem_e2_covalent_crystal", "共价晶体的构成与性质", 4, SUBJECT, G10, 540013),
    (540074, "chem_e2_diamond_silicon", "金刚石与晶体硅的结构", 5, SUBJECT, G10, 540013),
    (540075, "chem_e2_silica", "二氧化硅的晶体结构", 6, SUBJECT, G10, 540013),
    (540076, "chem_e2_covalent_melting", "共价晶体熔点与硬度的比较", 7, SUBJECT, G10, 540013),
    (540077, "chem_e2_crystal_distinguish", "分子晶体与共价晶体的鉴别", 8, SUBJECT, G10, 540013),
    (540078, "chem_e2_graphite", "石墨的结构与混合型晶体", 9, SUBJECT, G10, 540013),

    # 3.3 金属晶体与离子晶体
    (540079, "chem_e2_electron_gas", "金属晶体的电子气理论", 1, SUBJECT, G10, 540014),
    (540080, "chem_e2_metal_packing", "金属晶体的堆积方式", 2, SUBJECT, G10, 540014),
    (540081, "chem_e2_packing_efficiency", "配位数与空间利用率", 3, SUBJECT, G10, 540014),
    (540082, "chem_e2_metal_property", "金属晶体物理性质的解释", 4, SUBJECT, G10, 540014),
    (540083, "chem_e2_ionic_crystal", "离子晶体的构成与性质", 5, SUBJECT, G10, 540014),
    (540084, "chem_e2_ionic_coordination", "离子晶体的配位数与半径比", 6, SUBJECT, G10, 540014),
    (540085, "chem_e2_nacl_cscl", "NaCl与CsCl晶型分析", 7, SUBJECT, G10, 540014),
    (540086, "chem_e2_lattice_energy", "晶格能及其影响因素", 8, SUBJECT, G10, 540014),
    (540087, "chem_e2_ionic_melting", "离子晶体熔沸点的比较", 9, SUBJECT, G10, 540014),

    # 3.4 配合物与超分子
    (540088, "chem_e2_complex_composition", "配合物的组成与配位键", 1, SUBJECT, G10, 540015),
    (540089, "chem_e2_complex_naming", "配合物的命名", 2, SUBJECT, G10, 540015),
    (540090, "chem_e2_complex_shape", "配合物的空间构型与异构", 3, SUBJECT, G10, 540015),
    (540091, "chem_e2_complex_examples", "常见配合物实例", 4, SUBJECT, G10, 540015),
    (540092, "chem_e2_complex_experiment", "配合物形成的实验探究", 5, SUBJECT, G10, 540015),
    (540093, "chem_e2_complex_application", "配合物的应用", 6, SUBJECT, G10, 540015),
    (540094, "chem_e2_supramolecule", "超分子的概念与特征", 7, SUBJECT, G10, 540015),
    (540095, "chem_e2_supramolecule_assembly", "超分子自组装与分子识别", 8, SUBJECT, G10, 540015),
    (540096, "chem_e2_supramolecule_application", "超分子化学的应用", 9, SUBJECT, G10, 540015),
)

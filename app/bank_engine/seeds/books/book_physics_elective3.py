"""人教版·选择性必修第三册：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 4
G11 = 11
BOOK_ID = 4106

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版·选择性必修第三册",
    "phys_e3",
    6,
    "人民教育出版社",
    SUBJECT,
    G11,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (460101, "第一章 分子动理论", "phys_e3_ch01", 1, BOOK_ID, None),
    (460102, "第二章 气体、固体和液体", "phys_e3_ch02", 2, BOOK_ID, None),
    (460103, "第三章 热力学定律", "phys_e3_ch03", 3, BOOK_ID, None),
    (460104, "第四章 原子结构和波粒二象性", "phys_e3_ch04", 4, BOOK_ID, None),
    (460105, "第五章 原子核", "phys_e3_ch05", 5, BOOK_ID, None),
    (460111, "1. 分子动理论的基本内容", "phys_e3_ch01_s01", 1, BOOK_ID, 460101),
    (460112, "2. 实验：用油膜法估测油酸分子的大小", "phys_e3_ch01_s02", 2, BOOK_ID, 460101),
    (460113, "3. 分子运动速率分布规律", "phys_e3_ch01_s03", 3, BOOK_ID, 460101),
    (460114, "4. 分子动能和分子势能", "phys_e3_ch01_s04", 4, BOOK_ID, 460101),
    (460121, "1. 温度和温标", "phys_e3_ch02_s01", 1, BOOK_ID, 460102),
    (460122, "2. 气体的等温变化", "phys_e3_ch02_s02", 2, BOOK_ID, 460102),
    (460123, "3. 气体的等压变化和等容变化", "phys_e3_ch02_s03", 3, BOOK_ID, 460102),
    (460124, "4. 固体", "phys_e3_ch02_s04", 4, BOOK_ID, 460102),
    (460125, "5. 液体", "phys_e3_ch02_s05", 5, BOOK_ID, 460102),
    (460131, "1. 功、热和内能的改变", "phys_e3_ch03_s01", 1, BOOK_ID, 460103),
    (460132, "2. 热力学第一定律", "phys_e3_ch03_s02", 2, BOOK_ID, 460103),
    (460133, "3. 能量守恒定律", "phys_e3_ch03_s03", 3, BOOK_ID, 460103),
    (460134, "4. 热力学第二定律", "phys_e3_ch03_s04", 4, BOOK_ID, 460103),
    (460141, "1. 普朗克黑体辐射理论", "phys_e3_ch04_s01", 1, BOOK_ID, 460104),
    (460142, "2. 光电效应", "phys_e3_ch04_s02", 2, BOOK_ID, 460104),
    (460143, "3. 原子的核式结构模型", "phys_e3_ch04_s03", 3, BOOK_ID, 460104),
    (460144, "4. 氢原子光谱和玻尔的原子模型", "phys_e3_ch04_s04", 4, BOOK_ID, 460104),
    (460145, "5. 粒子的波动性和量子力学的建立", "phys_e3_ch04_s05", 5, BOOK_ID, 460104),
    (460151, "1. 原子核的组成", "phys_e3_ch05_s01", 1, BOOK_ID, 460105),
    (460152, "2. 放射性元素的衰变", "phys_e3_ch05_s02", 2, BOOK_ID, 460105),
    (460153, "3. 核力与结合能", "phys_e3_ch05_s03", 3, BOOK_ID, 460105),
    (460154, "4. 核裂变与核聚变", "phys_e3_ch05_s04", 4, BOOK_ID, 460105),
    (460155, "5. “基本”粒子", "phys_e3_ch05_s05", 5, BOOK_ID, 460105),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (460001, "phys_e3_molecular_theory", "分子动理论", 1, SUBJECT, None),
    (460002, "phys_e3_gas_solid_liquid", "气体、固体和液体", 2, SUBJECT, None),
    (460003, "phys_e3_thermodynamics", "热力学定律", 3, SUBJECT, None),
    (460004, "phys_e3_atomic_structure", "原子结构与波粒二象性", 4, SUBJECT, None),
    (460005, "phys_e3_nucleus", "原子核", 5, SUBJECT, None),

    (460006, "phys_e3_ch01", "分子动理论", 1, SUBJECT, 460001),
    (460007, "phys_e3_ch02", "气体、固体和液体", 1, SUBJECT, 460002),
    (460008, "phys_e3_ch03", "热力学定律", 1, SUBJECT, 460003),
    (460009, "phys_e3_ch04", "原子结构和波粒二象性", 1, SUBJECT, 460004),
    (460010, "phys_e3_ch05", "原子核", 1, SUBJECT, 460005),

    (460011, "phys_e3_s_molecular_basic", "分子动理论的基本内容", 1, SUBJECT, 460006),
    (460012, "phys_e3_s_oil_film", "用油膜法估测油酸分子的大小", 2, SUBJECT, 460006),
    (460013, "phys_e3_s_speed_distribution", "分子运动速率分布规律", 3, SUBJECT, 460006),
    (460014, "phys_e3_s_kinetic_potential", "分子动能和分子势能", 4, SUBJECT, 460006),
    (460015, "phys_e3_s_temperature", "温度和温标", 1, SUBJECT, 460007),
    (460016, "phys_e3_s_isothermal", "气体的等温变化", 2, SUBJECT, 460007),
    (460017, "phys_e3_s_isobaric_isochoric", "气体的等压变化和等容变化", 3, SUBJECT, 460007),
    (460018, "phys_e3_s_solid", "固体", 4, SUBJECT, 460007),
    (460019, "phys_e3_s_liquid", "液体", 5, SUBJECT, 460007),
    (460020, "phys_e3_s_work_heat", "功、热和内能的改变", 1, SUBJECT, 460008),
    (460021, "phys_e3_s_first_law", "热力学第一定律", 2, SUBJECT, 460008),
    (460022, "phys_e3_s_energy_conservation", "能量守恒定律", 3, SUBJECT, 460008),
    (460023, "phys_e3_s_second_law", "热力学第二定律", 4, SUBJECT, 460008),
    (460024, "phys_e3_s_blackbody", "普朗克黑体辐射理论", 1, SUBJECT, 460009),
    (460025, "phys_e3_s_photoelectric", "光电效应", 2, SUBJECT, 460009),
    (460026, "phys_e3_s_nuclear_model", "原子的核式结构模型", 3, SUBJECT, 460009),
    (460027, "phys_e3_s_bohr", "氢原子光谱和玻尔的原子模型", 4, SUBJECT, 460009),
    (460028, "phys_e3_s_wave_particle", "粒子的波动性和量子力学的建立", 5, SUBJECT, 460009),
    (460029, "phys_e3_s_nucleus_composition", "原子核的组成", 1, SUBJECT, 460010),
    (460030, "phys_e3_s_decay", "放射性元素的衰变", 2, SUBJECT, 460010),
    (460031, "phys_e3_s_nuclear_force_binding", "核力与结合能", 3, SUBJECT, 460010),
    (460032, "phys_e3_s_fission_fusion", "核裂变与核聚变", 4, SUBJECT, 460010),
    (460033, "phys_e3_s_elementary", "基本粒子", 5, SUBJECT, 460010),

    (460034, "phys_e3_molecular_size", "分子大小的数量级与分子模型", 1, SUBJECT, 460011),
    (460035, "phys_e3_avogadro_estimate", "阿伏加德罗常数与微观量估算", 2, SUBJECT, 460011),
    (460036, "phys_e3_diffusion", "扩散现象及其影响因素", 3, SUBJECT, 460011),
    (460037, "phys_e3_brownian", "布朗运动的特点与成因", 4, SUBJECT, 460011),
    (460038, "phys_e3_molecular_force_curve", "分子间作用力与分子力曲线", 5, SUBJECT, 460011),
    (460039, "phys_e3_molecular_theory_view", "分子动理论的基本观点", 6, SUBJECT, 460011),

    (460040, "phys_e3_oil_film_principle", "油膜法估测分子直径的实验原理", 1, SUBJECT, 460012),
    (460041, "phys_e3_oil_film_steps", "油膜法实验步骤与油酸溶液配制", 2, SUBJECT, 460012),
    (460042, "phys_e3_oil_film_error", "油膜法实验误差分析与注意事项", 3, SUBJECT, 460012),

    (460043, "phys_e3_speed_distribution", "气体分子速率分布曲线与统计规律", 1, SUBJECT, 460013),
    (460044, "phys_e3_speed_temperature", "温度对分子速率分布的影响", 2, SUBJECT, 460013),
    (460045, "phys_e3_speed_statistics", "分子速率的最概然值、平均值与方均根值", 3, SUBJECT, 460013),

    (460046, "phys_e3_molecular_kinetic", "分子平均动能与温度的微观意义", 1, SUBJECT, 460014),
    (460047, "phys_e3_molecular_potential", "分子势能曲线与物体的内能", 2, SUBJECT, 460014),

    (460048, "phys_e3_thermal_equilibrium", "平衡态与热平衡", 1, SUBJECT, 460015),
    (460049, "phys_e3_temperature_scale", "摄氏温标与热力学温标", 2, SUBJECT, 460015),

    (460050, "phys_e3_boyle_experiment", "玻意耳定律的实验探究", 1, SUBJECT, 460016),
    (460051, "phys_e3_boyle_law", "玻意耳定律的内容与表达式", 2, SUBJECT, 460016),
    (460052, "phys_e3_boyle_graph", "气体等温变化的 p-V 图像", 3, SUBJECT, 460016),
    (460053, "phys_e3_pressure_micro", "气体压强的微观解释", 4, SUBJECT, 460016),

    (460054, "phys_e3_charles_law", "查理定律与等容变化", 1, SUBJECT, 460017),
    (460055, "phys_e3_gay_lussac_law", "盖—吕萨克定律与等压变化", 2, SUBJECT, 460017),
    (460056, "phys_e3_ideal_gas_equation", "理想气体状态方程", 3, SUBJECT, 460017),
    (460057, "phys_e3_gas_law_application", "气体实验定律的综合应用", 4, SUBJECT, 460017),

    (460058, "phys_e3_crystal_amorphous", "晶体与非晶体的区别", 1, SUBJECT, 460018),
    (460059, "phys_e3_crystal_structure", "晶体的微观结构", 2, SUBJECT, 460018),

    (460060, "phys_e3_surface_tension", "液体的表面张力", 1, SUBJECT, 460019),
    (460061, "phys_e3_wetting_capillary_lcd", "浸润、毛细现象与液晶", 2, SUBJECT, 460019),

    (460062, "phys_e3_work_internal_energy", "做功改变物体的内能", 1, SUBJECT, 460020),
    (460063, "phys_e3_heat_internal_energy", "热传递改变物体的内能", 2, SUBJECT, 460020),
    (460064, "phys_e3_work_heat_equivalence", "做功与热传递的等效性与区别", 3, SUBJECT, 460020),

    (460065, "phys_e3_first_law_content", "热力学第一定律的内容与表达式", 1, SUBJECT, 460021),
    (460066, "phys_e3_first_law_sign", "热力学第一定律的符号规则", 2, SUBJECT, 460021),
    (460067, "phys_e3_first_law_process", "理想气体状态变化中的功、热与内能", 3, SUBJECT, 460021),
    (460068, "phys_e3_first_law_calc", "热力学第一定律的综合计算", 4, SUBJECT, 460021),

    (460069, "phys_e3_energy_conservation_law", "能量守恒定律的建立与表述", 1, SUBJECT, 460022),
    (460070, "phys_e3_first_kind_machine", "第一类永动机不可能制成", 2, SUBJECT, 460022),

    (460071, "phys_e3_clausius_statement", "热力学第二定律的克劳修斯表述", 1, SUBJECT, 460023),
    (460072, "phys_e3_kelvin_statement", "热力学第二定律的开尔文表述与第二类永动机", 2, SUBJECT, 460023),
    (460073, "phys_e3_entropy_dissipation", "熵增原理与能量耗散", 3, SUBJECT, 460023),

    (460074, "phys_e3_blackbody_radiation", "热辐射、黑体与黑体辐射规律", 1, SUBJECT, 460024),
    (460075, "phys_e3_energy_quantum", "能量子假说与普朗克常量", 2, SUBJECT, 460024),

    (460076, "phys_e3_photoelectric_law", "光电效应的实验规律", 1, SUBJECT, 460025),
    (460077, "phys_e3_stopping_voltage", "遏止电压与截止频率", 2, SUBJECT, 460025),
    (460078, "phys_e3_photoelectric_equation", "爱因斯坦光电效应方程", 3, SUBJECT, 460025),
    (460079, "phys_e3_photon_image", "光子说与光电效应的图像分析", 4, SUBJECT, 460025),

    (460080, "phys_e3_electron_discovery", "电子的发现与汤姆孙原子模型", 1, SUBJECT, 460026),
    (460081, "phys_e3_alpha_scattering", "α 粒子散射实验", 2, SUBJECT, 460026),
    (460082, "phys_e3_rutherford_model", "卢瑟福核式结构模型", 3, SUBJECT, 460026),

    (460083, "phys_e3_hydrogen_spectrum", "氢原子光谱与巴耳末系", 1, SUBJECT, 460027),
    (460084, "phys_e3_bohr_postulates", "玻尔原子模型的三个假设", 2, SUBJECT, 460027),
    (460085, "phys_e3_energy_level", "能级跃迁与氢原子能级图", 3, SUBJECT, 460027),

    (460086, "phys_e3_de_broglie", "德布罗意物质波与电子衍射", 1, SUBJECT, 460028),
    (460087, "phys_e3_wave_particle", "波粒二象性与量子力学的建立", 2, SUBJECT, 460028),

    (460088, "phys_e3_radioactivity", "天然放射性与三种射线", 1, SUBJECT, 460029),
    (460089, "phys_e3_nucleus_composition", "原子核的组成与同位素", 2, SUBJECT, 460029),

    (460090, "phys_e3_decay_law", "α 衰变与 β 衰变的规律", 1, SUBJECT, 460030),
    (460091, "phys_e3_half_life", "半衰期及其统计意义", 2, SUBJECT, 460030),
    (460092, "phys_e3_radioisotope_use", "放射性同位素的应用与防护", 3, SUBJECT, 460030),

    (460093, "phys_e3_nuclear_force_binding", "核力与结合能、比结合能", 1, SUBJECT, 460031),
    (460094, "phys_e3_mass_defect", "质量亏损与质能方程", 2, SUBJECT, 460031),

    (460095, "phys_e3_fission_reactor", "核裂变、链式反应与核反应堆", 1, SUBJECT, 460032),
    (460096, "phys_e3_fusion", "核聚变与受控热核反应", 2, SUBJECT, 460032),

    (460097, "phys_e3_elementary_particles", "基本粒子的分类与夸克模型", 1, SUBJECT, 460033),
    (460098, "phys_e3_four_interactions", "四种基本相互作用", 2, SUBJECT, 460033),
)

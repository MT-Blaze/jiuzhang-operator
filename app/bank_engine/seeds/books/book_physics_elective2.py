"""人教版·选择性必修第二册：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 4
G11 = 11
BOOK_ID = 4105

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版·选择性必修第二册",
    "phys_e2",
    5,
    "人民教育出版社",
    SUBJECT,
    G11,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (450101, "第一章 安培力与洛伦兹力", "phys_e2_ch01", 1, BOOK_ID, None),
    (450102, "第二章 电磁感应", "phys_e2_ch02", 2, BOOK_ID, None),
    (450103, "第三章 交变电流", "phys_e2_ch03", 3, BOOK_ID, None),
    (450104, "第四章 电磁振荡与电磁波", "phys_e2_ch04", 4, BOOK_ID, None),
    (450105, "第五章 传感器", "phys_e2_ch05", 5, BOOK_ID, None),
    (450111, "1. 磁场对通电导线的作用力", "phys_e2_ch01_s01", 1, BOOK_ID, 450101),
    (450112, "2. 磁场对运动电荷的作用力", "phys_e2_ch01_s02", 2, BOOK_ID, 450101),
    (450113, "3. 带电粒子在匀强磁场中的运动", "phys_e2_ch01_s03", 3, BOOK_ID, 450101),
    (450114, "4. 质谱仪与回旋加速器", "phys_e2_ch01_s04", 4, BOOK_ID, 450101),
    (450121, "1. 楞次定律", "phys_e2_ch02_s01", 1, BOOK_ID, 450102),
    (450122, "2. 法拉第电磁感应定律", "phys_e2_ch02_s02", 2, BOOK_ID, 450102),
    (450123, "3. 涡流、电磁阻尼和电磁驱动", "phys_e2_ch02_s03", 3, BOOK_ID, 450102),
    (450124, "4. 互感和自感", "phys_e2_ch02_s04", 4, BOOK_ID, 450102),
    (450131, "1. 交变电流", "phys_e2_ch03_s01", 1, BOOK_ID, 450103),
    (450132, "2. 交变电流的描述", "phys_e2_ch03_s02", 2, BOOK_ID, 450103),
    (450133, "3. 变压器", "phys_e2_ch03_s03", 3, BOOK_ID, 450103),
    (450134, "4. 电能的输送", "phys_e2_ch03_s04", 4, BOOK_ID, 450103),
    (450141, "1. 电磁振荡", "phys_e2_ch04_s01", 1, BOOK_ID, 450104),
    (450142, "2. 电磁场与电磁波", "phys_e2_ch04_s02", 2, BOOK_ID, 450104),
    (450143, "3. 无线电波的发射和接收", "phys_e2_ch04_s03", 3, BOOK_ID, 450104),
    (450144, "4. 电磁波谱", "phys_e2_ch04_s04", 4, BOOK_ID, 450104),
    (450151, "1. 认识传感器", "phys_e2_ch05_s01", 1, BOOK_ID, 450105),
    (450152, "2. 常见传感器的工作原理及应用", "phys_e2_ch05_s02", 2, BOOK_ID, 450105),
    (450153, "3. 利用传感器制作简单的自动控制装置", "phys_e2_ch05_s03", 3, BOOK_ID, 450105),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (450001, "phys_e2_magnetic_force", "磁场力", 1, SUBJECT, None),
    (450002, "phys_e2_em_induction", "电磁感应", 2, SUBJECT, None),
    (450003, "phys_e2_ac", "交变电流", 3, SUBJECT, None),
    (450004, "phys_e2_em_wave", "电磁振荡与电磁波", 4, SUBJECT, None),
    (450005, "phys_e2_sensor", "传感器", 5, SUBJECT, None),

    (450006, "phys_e2_ch01", "安培力与洛伦兹力", 1, SUBJECT, 450001),
    (450007, "phys_e2_ch02", "电磁感应", 1, SUBJECT, 450002),
    (450008, "phys_e2_ch03", "交变电流", 1, SUBJECT, 450003),
    (450009, "phys_e2_ch04", "电磁振荡与电磁波", 1, SUBJECT, 450004),
    (450010, "phys_e2_ch05", "传感器", 1, SUBJECT, 450005),

    (450011, "phys_e2_s_ampere", "磁场对通电导线的作用力", 1, SUBJECT, 450006),
    (450012, "phys_e2_s_lorentz", "磁场对运动电荷的作用力", 2, SUBJECT, 450006),
    (450013, "phys_e2_s_charged_motion", "带电粒子在匀强磁场中的运动", 3, SUBJECT, 450006),
    (450014, "phys_e2_s_mass_cyclotron", "质谱仪与回旋加速器", 4, SUBJECT, 450006),
    (450015, "phys_e2_s_lenz", "楞次定律", 1, SUBJECT, 450007),
    (450016, "phys_e2_s_faraday", "法拉第电磁感应定律", 2, SUBJECT, 450007),
    (450017, "phys_e2_s_eddy", "涡流、电磁阻尼和电磁驱动", 3, SUBJECT, 450007),
    (450018, "phys_e2_s_mutual_self", "互感和自感", 4, SUBJECT, 450007),
    (450019, "phys_e2_s_ac_form", "交变电流", 1, SUBJECT, 450008),
    (450020, "phys_e2_s_ac_desc", "交变电流的描述", 2, SUBJECT, 450008),
    (450021, "phys_e2_s_transformer", "变压器", 3, SUBJECT, 450008),
    (450022, "phys_e2_s_transmission", "电能的输送", 4, SUBJECT, 450008),
    (450023, "phys_e2_s_lc_oscillation", "电磁振荡", 1, SUBJECT, 450009),
    (450024, "phys_e2_s_em_field_wave", "电磁场与电磁波", 2, SUBJECT, 450009),
    (450025, "phys_e2_s_radio", "无线电波的发射和接收", 3, SUBJECT, 450009),
    (450026, "phys_e2_s_em_spectrum", "电磁波谱", 4, SUBJECT, 450009),
    (450027, "phys_e2_s_sensor_intro", "认识传感器", 1, SUBJECT, 450010),
    (450028, "phys_e2_s_sensor_types", "常见传感器的工作原理及应用", 2, SUBJECT, 450010),
    (450029, "phys_e2_s_auto_control", "利用传感器制作简单的自动控制装置", 3, SUBJECT, 450010),

    (450030, "phys_e2_ampere_direction", "安培力的方向与左手定则", 1, SUBJECT, 450011),
    (450031, "phys_e2_ampere_size", "安培力大小的计算", 2, SUBJECT, 450011),
    (450032, "phys_e2_ampere_effective_length", "安培力公式中的有效长度", 3, SUBJECT, 450011),
    (450033, "phys_e2_ampere_balance", "通电导线在磁场中的平衡与运动", 4, SUBJECT, 450011),

    (450034, "phys_e2_lorentz_direction", "洛伦兹力的方向与左手定则", 1, SUBJECT, 450012),
    (450035, "phys_e2_lorentz_size", "洛伦兹力的大小与适用条件", 2, SUBJECT, 450012),
    (450036, "phys_e2_lorentz_no_work", "洛伦兹力不做功的特点", 3, SUBJECT, 450012),
    (450037, "phys_e2_lorentz_ampere_link", "洛伦兹力与安培力的联系", 4, SUBJECT, 450012),

    (450038, "phys_e2_charge_circle", "带电粒子在匀强磁场中的圆周运动", 1, SUBJECT, 450013),
    (450039, "phys_e2_charge_radius_period", "圆周运动半径与周期的计算", 2, SUBJECT, 450013),
    (450040, "phys_e2_charge_trajectory", "带电粒子运动轨迹的作图方法", 3, SUBJECT, 450013),
    (450041, "phys_e2_charge_boundary", "有界磁场中的临界与多解问题", 4, SUBJECT, 450013),

    (450042, "phys_e2_mass_spectrometer", "质谱仪的工作原理", 1, SUBJECT, 450014),
    (450043, "phys_e2_mass_spectrum_calc", "质谱仪的分析与计算", 2, SUBJECT, 450014),
    (450044, "phys_e2_cyclotron", "回旋加速器的工作原理与加速条件", 3, SUBJECT, 450014),
    (450045, "phys_e2_cyclotron_energy", "回旋加速器的最大动能与加速次数", 4, SUBJECT, 450014),

    (450046, "phys_e2_lenz_explore", "探究感应电流方向的影响因素", 1, SUBJECT, 450015),
    (450047, "phys_e2_lenz_content", "楞次定律的内容与阻碍的含义", 2, SUBJECT, 450015),
    (450048, "phys_e2_right_hand_rule", "右手定则判断感应电流方向", 3, SUBJECT, 450015),
    (450049, "phys_e2_lenz_extend", "楞次定律的推广与综合应用", 4, SUBJECT, 450015),

    (450050, "phys_e2_faraday_law", "感应电动势与法拉第电磁感应定律", 1, SUBJECT, 450016),
    (450051, "phys_e2_cut_emf", "导体切割磁感线产生的感应电动势", 2, SUBJECT, 450016),
    (450052, "phys_e2_rotating_emf", "导体转动切割磁感线的电动势", 3, SUBJECT, 450016),
    (450053, "phys_e2_average_emf_charge", "平均感应电动势与感应电荷量", 4, SUBJECT, 450016),
    (450054, "phys_e2_induction_circuit", "电磁感应中的电路与图像问题", 5, SUBJECT, 450016),
    (450055, "phys_e2_induction_energy", "电磁感应中的能量转化", 6, SUBJECT, 450016),

    (450056, "phys_e2_eddy_cause", "涡流现象及其成因", 1, SUBJECT, 450017),
    (450057, "phys_e2_eddy_use", "涡流的利用与防止", 2, SUBJECT, 450017),
    (450058, "phys_e2_damping_drive", "电磁阻尼与电磁驱动", 3, SUBJECT, 450017),

    (450059, "phys_e2_mutual", "互感现象", 1, SUBJECT, 450018),
    (450060, "phys_e2_self", "自感现象与自感系数", 2, SUBJECT, 450018),
    (450061, "phys_e2_self_on_off", "通电自感与断电自感的分析", 3, SUBJECT, 450018),

    (450062, "phys_e2_ac_generation", "交变电流的产生与正弦式交变电流", 1, SUBJECT, 450019),
    (450063, "phys_e2_neutral_plane", "中性面与线圈转动的特征", 2, SUBJECT, 450019),
    (450064, "phys_e2_ac_expression", "交变电流的瞬时值表达式与图像", 3, SUBJECT, 450019),

    (450065, "phys_e2_ac_period", "周期、频率与角速度", 1, SUBJECT, 450020),
    (450066, "phys_e2_ac_peak", "峰值与有效值", 2, SUBJECT, 450020),
    (450067, "phys_e2_ac_rms", "有效值的定义与计算方法", 3, SUBJECT, 450020),
    (450068, "phys_e2_ac_average", "交流电的平均值与有效值的区别", 4, SUBJECT, 450020),

    (450069, "phys_e2_transformer_principle", "变压器的构造与工作原理", 1, SUBJECT, 450021),
    (450070, "phys_e2_transformer_relation", "理想变压器的电压、电流与功率关系", 2, SUBJECT, 450021),
    (450071, "phys_e2_transformer_dynamic", "理想变压器的动态分析", 3, SUBJECT, 450021),

    (450072, "phys_e2_line_loss", "远距离输电的功率损耗与电压损耗", 1, SUBJECT, 450022),
    (450073, "phys_e2_high_voltage", "高压输电的原理与电路模型", 2, SUBJECT, 450022),
    (450074, "phys_e2_transmission_choice", "输电电压、输电电流与输送功率的选择", 3, SUBJECT, 450022),

    (450075, "phys_e2_lc_process", "LC 振荡电路的形成与振荡过程", 1, SUBJECT, 450023),
    (450076, "phys_e2_lc_period", "电磁振荡的周期与频率", 2, SUBJECT, 450023),
    (450077, "phys_e2_lc_energy", "振荡过程中的能量转化与阻尼振荡", 3, SUBJECT, 450023),

    (450078, "phys_e2_maxwell", "麦克斯韦电磁场理论", 1, SUBJECT, 450024),
    (450079, "phys_e2_em_wave_form", "电磁波的形成与传播特点", 2, SUBJECT, 450024),
    (450080, "phys_e2_em_vs_mechanical", "电磁波与机械波的比较", 3, SUBJECT, 450024),

    (450081, "phys_e2_radio_transmit", "无线电波的发射与调制", 1, SUBJECT, 450025),
    (450082, "phys_e2_radio_receive", "无线电波的接收、调谐与解调", 2, SUBJECT, 450025),
    (450083, "phys_e2_em_propagation", "电磁波的传播方式", 3, SUBJECT, 450025),

    (450084, "phys_e2_spectrum_order", "电磁波谱的组成与排列顺序", 1, SUBJECT, 450026),
    (450085, "phys_e2_spectrum_apply", "各波段电磁波的特性与应用", 2, SUBJECT, 450026),

    (450086, "phys_e2_sensor_define", "传感器的定义与基本组成", 1, SUBJECT, 450027),
    (450087, "phys_e2_sensor_principle", "传感器的一般工作原理", 2, SUBJECT, 450027),

    (450088, "phys_e2_sensor_force", "力传感器与位移传感器", 1, SUBJECT, 450028),
    (450089, "phys_e2_sensor_temp_light", "温度传感器与光敏传感器", 2, SUBJECT, 450028),
    (450090, "phys_e2_sensor_hall", "霍尔元件与磁传感器", 3, SUBJECT, 450028),

    (450091, "phys_e2_auto_circuit", "传感器实验电路的设计与连接", 1, SUBJECT, 450029),
    (450092, "phys_e2_auto_build", "简单自动控制装置的制作与调试", 2, SUBJECT, 450029),
    (450093, "phys_e2_auto_error", "传感器实验的数据处理与误差分析", 3, SUBJECT, 450029),
)

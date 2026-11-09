"""人教版（2019）高中物理选择性必修第一册：完整章节目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 4
G10 = 10
BOOK_ID = 4104

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版（2019）高中物理选择性必修第一册",
    "phys_e1",
    4,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (440101, "第一章 动量守恒定律", "phys_e1_ch01", 1, BOOK_ID, None),
    (440102, "第二章 机械振动", "phys_e1_ch02", 2, BOOK_ID, None),
    (440103, "第三章 机械波", "phys_e1_ch03", 3, BOOK_ID, None),
    (440104, "第四章 光", "phys_e1_ch04", 4, BOOK_ID, None),
    (440111, "1. 动量", "phys_e1_ch01_s01", 1, BOOK_ID, 440101),
    (440112, "2. 动量定理", "phys_e1_ch01_s02", 2, BOOK_ID, 440101),
    (440113, "3. 动量守恒定律", "phys_e1_ch01_s03", 3, BOOK_ID, 440101),
    (440114, "4. 实验：验证动量守恒定律", "phys_e1_ch01_s04", 4, BOOK_ID, 440101),
    (440115, "5. 弹性碰撞和非弹性碰撞", "phys_e1_ch01_s05", 5, BOOK_ID, 440101),
    (440116, "6. 反冲现象 火箭", "phys_e1_ch01_s06", 6, BOOK_ID, 440101),
    (440121, "1. 简谐运动", "phys_e1_ch02_s01", 1, BOOK_ID, 440102),
    (440122, "2. 简谐运动的描述", "phys_e1_ch02_s02", 2, BOOK_ID, 440102),
    (440123, "3. 简谐运动的回复力和能量", "phys_e1_ch02_s03", 3, BOOK_ID, 440102),
    (440124, "4. 单摆", "phys_e1_ch02_s04", 4, BOOK_ID, 440102),
    (440125, "5. 实验：用单摆测量重力加速度", "phys_e1_ch02_s05", 5, BOOK_ID, 440102),
    (440126, "6. 受迫振动 共振", "phys_e1_ch02_s06", 6, BOOK_ID, 440102),
    (440131, "1. 波的形成", "phys_e1_ch03_s01", 1, BOOK_ID, 440103),
    (440132, "2. 波的描述", "phys_e1_ch03_s02", 2, BOOK_ID, 440103),
    (440133, "3. 波的反射、折射和衍射", "phys_e1_ch03_s03", 3, BOOK_ID, 440103),
    (440134, "4. 波的干涉", "phys_e1_ch03_s04", 4, BOOK_ID, 440103),
    (440135, "5. 多普勒效应", "phys_e1_ch03_s05", 5, BOOK_ID, 440103),
    (440141, "1. 光的折射", "phys_e1_ch04_s01", 1, BOOK_ID, 440104),
    (440142, "2. 全反射", "phys_e1_ch04_s02", 2, BOOK_ID, 440104),
    (440143, "3. 光的干涉", "phys_e1_ch04_s03", 3, BOOK_ID, 440104),
    (440144, "4. 实验：用双缝干涉测量光的波长", "phys_e1_ch04_s04", 4, BOOK_ID, 440104),
    (440145, "5. 光的衍射", "phys_e1_ch04_s05", 5, BOOK_ID, 440104),
    (440146, "6. 光的偏振 激光", "phys_e1_ch04_s06", 6, BOOK_ID, 440104),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    (440001, "phys_e1_momentum", "动量与碰撞", 1, SUBJECT, G10, None),
    (440002, "phys_e1_vibration", "机械振动", 2, SUBJECT, G10, None),
    (440003, "phys_e1_wave", "机械波", 3, SUBJECT, G10, None),
    (440004, "phys_e1_optics", "光与光学", 4, SUBJECT, G10, None),

    (440005, "phys_e1_ch01", "动量守恒定律", 1, SUBJECT, G10, 440001),
    (440006, "phys_e1_ch02", "机械振动", 1, SUBJECT, G10, 440002),
    (440007, "phys_e1_ch03", "机械波", 1, SUBJECT, G10, 440003),
    (440008, "phys_e1_ch04", "光", 1, SUBJECT, G10, 440004),

    (440009, "phys_e1_s_momentum", "动量", 1, SUBJECT, G10, 440005),
    (440010, "phys_e1_s_momentum_theorem", "动量定理", 2, SUBJECT, G10, 440005),
    (440011, "phys_e1_s_conservation", "动量守恒定律", 3, SUBJECT, G10, 440005),
    (440012, "phys_e1_s_verify_conservation", "实验：验证动量守恒定律", 4, SUBJECT, G10, 440005),
    (440013, "phys_e1_s_collision", "弹性碰撞和非弹性碰撞", 5, SUBJECT, G10, 440005),
    (440014, "phys_e1_s_recoil", "反冲现象 火箭", 6, SUBJECT, G10, 440005),

    (440015, "phys_e1_s_shm", "简谐运动", 1, SUBJECT, G10, 440006),
    (440016, "phys_e1_s_shm_desc", "简谐运动的描述", 2, SUBJECT, G10, 440006),
    (440017, "phys_e1_s_shm_force", "简谐运动的回复力和能量", 3, SUBJECT, G10, 440006),
    (440018, "phys_e1_s_pendulum", "单摆", 4, SUBJECT, G10, 440006),
    (440019, "phys_e1_s_pendulum_exp", "实验：用单摆测量重力加速度", 5, SUBJECT, G10, 440006),
    (440020, "phys_e1_s_forced", "受迫振动 共振", 6, SUBJECT, G10, 440006),

    (440021, "phys_e1_s_wave_form", "波的形成", 1, SUBJECT, G10, 440007),
    (440022, "phys_e1_s_wave_desc", "波的描述", 2, SUBJECT, G10, 440007),
    (440023, "phys_e1_s_wave_phenomena", "波的反射、折射和衍射", 3, SUBJECT, G10, 440007),
    (440024, "phys_e1_s_interference", "波的干涉", 4, SUBJECT, G10, 440007),
    (440025, "phys_e1_s_doppler", "多普勒效应", 5, SUBJECT, G10, 440007),

    (440026, "phys_e1_s_refraction", "光的折射", 1, SUBJECT, G10, 440008),
    (440027, "phys_e1_s_total_reflection", "全反射", 2, SUBJECT, G10, 440008),
    (440028, "phys_e1_s_light_interference", "光的干涉", 3, SUBJECT, G10, 440008),
    (440029, "phys_e1_s_double_slit", "实验：用双缝干涉测量光的波长", 4, SUBJECT, G10, 440008),
    (440030, "phys_e1_s_diffraction", "光的衍射", 5, SUBJECT, G10, 440008),
    (440031, "phys_e1_s_polarization", "光的偏振 激光", 6, SUBJECT, G10, 440008),

    (440032, "phys_e1_momentum_def", "动量的定义与矢量性", 1, SUBJECT, G10, 440009),
    (440033, "phys_e1_momentum_change", "动量变化量的计算", 2, SUBJECT, G10, 440009),
    (440034, "phys_e1_momentum_energy", "动量与动能的区别和联系", 3, SUBJECT, G10, 440009),
    (440035, "phys_e1_momentum_frame", "动量中的参考系选择", 4, SUBJECT, G10, 440009),

    (440036, "phys_e1_impulse_def", "冲量的定义与计算", 1, SUBJECT, G10, 440010),
    (440037, "phys_e1_theorem_content", "动量定理的内容与表达式", 2, SUBJECT, G10, 440010),
    (440038, "phys_e1_theorem_vector", "动量定理的矢量性与方向处理", 3, SUBJECT, G10, 440010),
    (440039, "phys_e1_theorem_apply", "动量定理的应用（缓冲与平均作用力）", 4, SUBJECT, G10, 440010),

    (440040, "phys_e1_system_force", "系统、内力与外力的区分", 1, SUBJECT, G10, 440011),
    (440041, "phys_e1_conservation_content", "动量守恒定律的内容与表达式", 2, SUBJECT, G10, 440011),
    (440042, "phys_e1_conservation_condition", "动量守恒的适用条件", 3, SUBJECT, G10, 440011),
    (440043, "phys_e1_conservation_direction", "动量守恒的方向性与参考系", 4, SUBJECT, G10, 440011),
    (440044, "phys_e1_man_boat", "人船模型", 5, SUBJECT, G10, 440011),

    (440045, "phys_e1_verify_principle", "实验原理与方案设计", 1, SUBJECT, G10, 440012),
    (440046, "phys_e1_verify_airtrack", "气垫导轨与光电门测速方案", 2, SUBJECT, G10, 440012),
    (440047, "phys_e1_verify_groove", "斜槽小球碰撞方案与误差分析", 3, SUBJECT, G10, 440012),

    (440048, "phys_e1_collision_kind", "碰撞的分类与过程特征", 1, SUBJECT, G10, 440013),
    (440049, "phys_e1_elastic_collision", "弹性碰撞的规律与结论", 2, SUBJECT, G10, 440013),
    (440050, "phys_e1_inelastic_collision", "完全非弹性碰撞与能量损失", 3, SUBJECT, G10, 440013),
    (440051, "phys_e1_collision_judge", "碰撞的合理性判断与一维碰撞模型", 4, SUBJECT, G10, 440013),

    (440052, "phys_e1_recoil_principle", "反冲现象及其原理", 1, SUBJECT, G10, 440014),
    (440053, "phys_e1_rocket", "火箭的工作原理与反冲速度", 2, SUBJECT, G10, 440014),

    (440054, "phys_e1_spring_oscillator", "弹簧振子模型", 1, SUBJECT, G10, 440015),
    (440055, "phys_e1_shm_dynamics", "简谐运动的动力学特征", 2, SUBJECT, G10, 440015),
    (440056, "phys_e1_shm_kinematics", "简谐运动的位移—时间图像与运动学特征", 3, SUBJECT, G10, 440015),

    (440057, "phys_e1_amplitude_period", "振幅、周期与频率", 1, SUBJECT, G10, 440016),
    (440058, "phys_e1_phase", "相位与初相位", 2, SUBJECT, G10, 440016),
    (440059, "phys_e1_shm_equation", "简谐运动的表达式", 3, SUBJECT, G10, 440016),
    (440060, "phys_e1_shm_graph", "简谐运动图像的信息读取与相位差", 4, SUBJECT, G10, 440016),

    (440061, "phys_e1_restoring_force", "回复力与胡克定律", 1, SUBJECT, G10, 440017),
    (440062, "phys_e1_shm_energy", "简谐运动的能量转化与对称性", 2, SUBJECT, G10, 440017),
    (440063, "phys_e1_shm_acceleration", "简谐运动中加速度与速度的变化分析", 3, SUBJECT, G10, 440017),

    (440064, "phys_e1_pendulum_model", "单摆模型与摆长", 1, SUBJECT, G10, 440018),
    (440065, "phys_e1_pendulum_condition", "单摆做简谐运动的条件", 2, SUBJECT, G10, 440018),
    (440066, "phys_e1_pendulum_period", "单摆的周期公式与应用", 3, SUBJECT, G10, 440018),

    (440067, "phys_e1_pendulum_exp_principle", "实验原理与摆长、周期的测量", 1, SUBJECT, G10, 440019),
    (440068, "phys_e1_pendulum_exp_error", "数据处理与误差分析", 2, SUBJECT, G10, 440019),

    (440069, "phys_e1_damped_forced", "阻尼振动与受迫振动", 1, SUBJECT, G10, 440020),
    (440070, "phys_e1_resonance", "共振与共振曲线", 2, SUBJECT, G10, 440020),

    (440071, "phys_e1_wave_formation", "波的形成与传播特点", 1, SUBJECT, G10, 440021),
    (440072, "phys_e1_transverse_longitudinal", "横波与纵波", 2, SUBJECT, G10, 440021),
    (440073, "phys_e1_wave_medium", "机械波的传播条件与介质", 3, SUBJECT, G10, 440021),

    (440074, "phys_e1_wave_relation", "波长、频率与波速的关系", 1, SUBJECT, G10, 440022),
    (440075, "phys_e1_wave_graph", "波的图像与振动图像的区别", 2, SUBJECT, G10, 440022),
    (440076, "phys_e1_wave_direction", "波的传播方向与质点振动方向判断", 3, SUBJECT, G10, 440022),
    (440077, "phys_e1_wave_multi", "波的多解问题与图像应用", 4, SUBJECT, G10, 440022),

    (440078, "phys_e1_wave_reflect_refract", "波的反射与折射", 1, SUBJECT, G10, 440023),
    (440079, "phys_e1_wave_diffraction", "波的衍射现象与明显衍射条件", 2, SUBJECT, G10, 440023),

    (440080, "phys_e1_superposition", "波的叠加原理", 1, SUBJECT, G10, 440024),
    (440081, "phys_e1_interference_condition", "波的干涉条件与稳定干涉图样", 2, SUBJECT, G10, 440024),
    (440082, "phys_e1_interference_point", "振动加强点与减弱点的判断", 3, SUBJECT, G10, 440024),

    (440083, "phys_e1_doppler_cause", "多普勒效应及其成因", 1, SUBJECT, G10, 440025),
    (440084, "phys_e1_doppler_apply", "多普勒效应的应用", 2, SUBJECT, G10, 440025),

    (440085, "phys_e1_refraction_law", "光的折射定律与折射率", 1, SUBJECT, G10, 440026),
    (440086, "phys_e1_refractive_index", "折射率与光速的关系", 2, SUBJECT, G10, 440026),
    (440087, "phys_e1_refraction_diagram", "光的折射作图与视深问题", 3, SUBJECT, G10, 440026),

    (440088, "phys_e1_total_reflection_phenomenon", "全反射现象与临界角", 1, SUBJECT, G10, 440027),
    (440089, "phys_e1_total_reflection_condition", "全反射的条件与计算", 2, SUBJECT, G10, 440027),
    (440090, "phys_e1_total_reflection_apply", "全反射的应用（光导纤维、棱镜）", 3, SUBJECT, G10, 440027),

    (440091, "phys_e1_light_interference_condition", "光的干涉条件与双缝干涉", 1, SUBJECT, G10, 440028),
    (440092, "phys_e1_fringe_spacing", "双缝干涉条纹间距公式", 2, SUBJECT, G10, 440028),

    (440093, "phys_e1_double_slit_principle", "实验原理与装置", 1, SUBJECT, G10, 440029),
    (440094, "phys_e1_double_slit_error", "波长测量与误差分析", 2, SUBJECT, G10, 440029),

    (440095, "phys_e1_light_diffraction", "光的衍射现象与明显条件", 1, SUBJECT, G10, 440030),
    (440096, "phys_e1_diffraction_pattern", "单缝衍射与圆孔衍射图样", 2, SUBJECT, G10, 440030),

    (440097, "phys_e1_polarization_phenomenon", "光的偏振现象", 1, SUBJECT, G10, 440031),
    (440098, "phys_e1_polarization_apply", "偏振的应用", 2, SUBJECT, G10, 440031),
    (440099, "phys_e1_laser", "激光的特性与应用", 3, SUBJECT, G10, 440031),
)

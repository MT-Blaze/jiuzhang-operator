"""人教版初中物理八年级上册：第一章—第六章目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 4
G8 = 8
BOOK_ID = 1330

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级物理上册",
    "jphy_g8a",
    30,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133001, "第一章 机械运动", "jphy_g8a_ch01", 1, BOOK_ID, None),
    (133011, "第1节 长度和时间的测量", "jphy_g8a_ch01_s01", 1, BOOK_ID, 133001),
    (133012, "第2节 运动的描述", "jphy_g8a_ch01_s02", 2, BOOK_ID, 133001),
    (133013, "第3节 运动的快慢", "jphy_g8a_ch01_s03", 3, BOOK_ID, 133001),
    (133014, "第4节 测量平均速度", "jphy_g8a_ch01_s04", 4, BOOK_ID, 133001),

    (133002, "第二章 声现象", "jphy_g8a_ch02", 2, BOOK_ID, None),
    (133021, "第1节 声音的产生与传播", "jphy_g8a_ch02_s01", 1, BOOK_ID, 133002),
    (133022, "第2节 声音的特性", "jphy_g8a_ch02_s02", 2, BOOK_ID, 133002),
    (133023, "第3节 声的利用", "jphy_g8a_ch02_s03", 3, BOOK_ID, 133002),
    (133024, "第4节 噪声的危害和控制", "jphy_g8a_ch02_s04", 4, BOOK_ID, 133002),

    (133003, "第三章 物态变化", "jphy_g8a_ch03", 3, BOOK_ID, None),
    (133031, "第1节 温度", "jphy_g8a_ch03_s01", 1, BOOK_ID, 133003),
    (133032, "第2节 熔化和凝固", "jphy_g8a_ch03_s02", 2, BOOK_ID, 133003),
    (133033, "第3节 汽化和液化", "jphy_g8a_ch03_s03", 3, BOOK_ID, 133003),
    (133034, "第4节 升华和凝华", "jphy_g8a_ch03_s04", 4, BOOK_ID, 133003),

    (133004, "第四章 光现象", "jphy_g8a_ch04", 4, BOOK_ID, None),
    (133041, "第1节 光的直线传播", "jphy_g8a_ch04_s01", 1, BOOK_ID, 133004),
    (133042, "第2节 光的反射", "jphy_g8a_ch04_s02", 2, BOOK_ID, 133004),
    (133043, "第3节 平面镜成像", "jphy_g8a_ch04_s03", 3, BOOK_ID, 133004),
    (
        133044,
        "第4节 光的折射",
        "jphy_g8a_ch04_s04",
        4,
        BOOK_ID,
        133004,
    ),
    (133045, "第5节 光的色散", "jphy_g8a_ch04_s05", 5, BOOK_ID, 133004),

    (133005, "第五章 透镜及其应用", "jphy_g8a_ch05", 5, BOOK_ID, None),
    (133051, "第1节 透镜", "jphy_g8a_ch05_s01", 1, BOOK_ID, 133005),
    (133052, "第2节 生活中的透镜", "jphy_g8a_ch05_s02", 2, BOOK_ID, 133005),
    (
        133053,
        "第3节 凸透镜成像的规律",
        "jphy_g8a_ch05_s03",
        3,
        BOOK_ID,
        133005,
    ),
    (133054, "第4节 眼睛和眼镜", "jphy_g8a_ch05_s04", 4, BOOK_ID, 133005),
    (
        133055,
        "第5节 显微镜和望远镜",
        "jphy_g8a_ch05_s05",
        5,
        BOOK_ID,
        133005,
    ),

    (133006, "第六章 质量与密度", "jphy_g8a_ch06", 6, BOOK_ID, None),
    (133061, "第1节 质量", "jphy_g8a_ch06_s01", 1, BOOK_ID, 133006),
    (133062, "第2节 密度", "jphy_g8a_ch06_s02", 2, BOOK_ID, 133006),
    (
        133063,
        "第3节 测量物质的密度",
        "jphy_g8a_ch06_s03",
        3,
        BOOK_ID,
        133006,
    ),
    (
        133064,
        "第4节 密度与社会生活",
        "jphy_g8a_ch06_s04",
        4,
        BOOK_ID,
        133006,
    ),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 230001-230006 为册域层，230007-230060 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (230001, "jphy_g8a_domain_ch01", "初中八上·第一章 机械运动：参照物、速度与测量", 1, SUBJECT, G8, None),
    (230002, "jphy_g8a_domain_ch02", "初中八上·第二章 声现象：产生、特性与利用", 2, SUBJECT, G8, None),
    (230003, "jphy_g8a_domain_ch03", "初中八上·第三章 物态变化：温度与三态互变", 3, SUBJECT, G8, None),
    (230004, "jphy_g8a_domain_ch04", "初中八上·第四章 光现象：直线传播、反射与折射", 4, SUBJECT, G8, None),
    (230005, "jphy_g8a_domain_ch05", "初中八上·第五章 透镜及其应用：成像规律与光学仪器", 5, SUBJECT, G8, None),
    (230006, "jphy_g8a_domain_ch06", "初中八上·第六章 质量与密度：测量与密度应用", 6, SUBJECT, G8, None),

    # 第一章 机械运动
    (230007, "jphy_g8a_ch01_ruler_reading", "刻度尺的分度值、估读位与长度单位换算", 1, SUBJECT, G8, 230001),
    (230008, "jphy_g8a_ch01_error", "误差与错误的区别及多次测量求平均值减小误差", 2, SUBJECT, G8, 230001),
    (230009, "jphy_g8a_ch01_stopwatch", "停表的读数方法与时间单位换算", 3, SUBJECT, G8, 230001),
    (230010, "jphy_g8a_ch01_reference_body", "参照物的选取原则与运动状态的判断", 4, SUBJECT, G8, 230001),
    (230011, "jphy_g8a_ch01_relativity", "运动和静止的相对性及相对运动方向判断", 5, SUBJECT, G8, 230001),
    (230012, "jphy_g8a_ch01_speed_formula", "速度定义式 v=s/t 及 m/s 与 km/h 换算", 6, SUBJECT, G8, 230001),
    (230013, "jphy_g8a_ch01_uniform_average", "匀速直线运动与变速运动平均速度的计算", 7, SUBJECT, G8, 230001),
    (230014, "jphy_g8a_ch01_average_experiment", "测量平均速度实验：斜面坡度、金属片与时间测量", 8, SUBJECT, G8, 230001),
    (230015, "jphy_g8a_ch01_motion_graph", "s-t 图像与 v-t 图像的判读及信息提取", 9, SUBJECT, G8, 230001),

    # 第二章 声现象
    (230016, "jphy_g8a_ch02_vibration", "声音由物体振动产生与振动停止发声停止", 1, SUBJECT, G8, 230002),
    (230017, "jphy_g8a_ch02_medium", "声的传播需要介质与真空不能传声", 2, SUBJECT, G8, 230002),
    (230018, "jphy_g8a_ch02_sound_speed", "声速与介质种类、温度的关系及回声测距", 3, SUBJECT, G8, 230002),
    (230019, "jphy_g8a_ch02_pitch", "音调由频率决定及超声波、次声波的界定", 4, SUBJECT, G8, 230002),
    (230020, "jphy_g8a_ch02_loudness", "响度与振幅、距声源远近的关系", 5, SUBJECT, G8, 230002),
    (230021, "jphy_g8a_ch02_timbre", "音色由发声体材料结构决定及波形图辨别", 6, SUBJECT, G8, 230002),
    (230022, "jphy_g8a_ch02_sound_info_energy", "声传递信息与声传递能量的实例辨析", 7, SUBJECT, G8, 230002),
    (230023, "jphy_g8a_ch02_noise_control", "噪声等级、噪声来源与三条控制途径", 8, SUBJECT, G8, 230002),

    # 第三章 物态变化
    (230024, "jphy_g8a_ch03_thermometer", "温度计工作原理、量程分度值与读数规范", 1, SUBJECT, G8, 230003),
    (230025, "jphy_g8a_ch03_clinical", "体温计的缩口结构与使用、消毒前甩动", 2, SUBJECT, G8, 230003),
    (230026, "jphy_g8a_ch03_crystal_graph", "晶体与非晶体熔化图像及熔点、凝固点", 3, SUBJECT, G8, 230003),
    (230027, "jphy_g8a_ch03_melt_freeze", "熔化吸热、凝固放热与晶体熔化的两个条件", 4, SUBJECT, G8, 230003),
    (230028, "jphy_g8a_ch03_evaporation", "蒸发现象、影响蒸发快慢的三个因素", 5, SUBJECT, G8, 230003),
    (230029, "jphy_g8a_ch03_boiling", "沸腾图像、沸点与气压关系及沸腾条件", 6, SUBJECT, G8, 230003),
    (230030, "jphy_g8a_ch03_evap_cooling", "蒸发致冷及其在降温、保鲜中的应用", 7, SUBJECT, G8, 230003),
    (230031, "jphy_g8a_ch03_liquefy", "液化的两种方式与“白气”的成因分析", 8, SUBJECT, G8, 230003),
    (230032, "jphy_g8a_ch03_sublimation", "升华吸热、凝华放热与霜、雾凇、干冰现象", 9, SUBJECT, G8, 230003),

    # 第四章 光现象
    (230033, "jphy_g8a_ch04_light_source", "光源分类与光沿直线传播的条件", 1, SUBJECT, G8, 230004),
    (230034, "jphy_g8a_ch04_shadow_pinhole", "影子、日食月食与小孔成像的特点", 2, SUBJECT, G8, 230004),
    (230035, "jphy_g8a_ch04_light_speed", "光速、光年及光在不同介质中的速度比较", 3, SUBJECT, G8, 230004),
    (230036, "jphy_g8a_ch04_reflection_law", "光的反射定律：三线共面、两角相等、光路可逆", 4, SUBJECT, G8, 230004),
    (230037, "jphy_g8a_ch04_specular_diffuse", "镜面反射与漫反射的成因及共同遵守反射定律", 5, SUBJECT, G8, 230004),
    (230038, "jphy_g8a_ch04_mirror_image", "平面镜成像特点：等大、等距、虚像、左右相反", 6, SUBJECT, G8, 230004),
    (230039, "jphy_g8a_ch04_mirror_experiment", "平面镜成像实验：玻璃板替代与像的位置确定", 7, SUBJECT, G8, 230004),
    (230040, "jphy_g8a_ch04_mirror_drawing", "平面镜成像作图与钟表镜像读数", 8, SUBJECT, G8, 230004),
    (230041, "jphy_g8a_ch04_refraction_law", "光的折射规律与入射角、折射角大小关系", 9, SUBJECT, G8, 230004),
    (230042, "jphy_g8a_ch04_refraction_phenomena", "筷子弯折、池水变浅与海市蜃楼的折射解释", 10, SUBJECT, G8, 230004),
    (230043, "jphy_g8a_ch04_dispersion", "光的色散、色光三原色与红外线紫外线", 11, SUBJECT, G8, 230004),

    # 第五章 透镜及其应用
    (230044, "jphy_g8a_ch05_lens_types", "凸透镜会聚、凹透镜发散与三条特殊光线", 1, SUBJECT, G8, 230005),
    (230045, "jphy_g8a_ch05_focal_length", "焦点、焦距概念与平行光法粗测焦距", 2, SUBJECT, G8, 230005),
    (230046, "jphy_g8a_ch05_camera_projector", "照相机、投影仪、放大镜的成像原理", 3, SUBJECT, G8, 230005),
    (230047, "jphy_g8a_ch05_imaging_far", "凸透镜成像规律：u>2f 与 u=2f 的情形", 4, SUBJECT, G8, 230005),
    (230048, "jphy_g8a_ch05_imaging_middle", "凸透镜成像规律：f<u<2f 与 u=f 的情形", 5, SUBJECT, G8, 230005),
    (230049, "jphy_g8a_ch05_imaging_near", "凸透镜成像规律：u<f 及物近像远像变大", 6, SUBJECT, G8, 230005),
    (230050, "jphy_g8a_ch05_imaging_experiment", "凸透镜成像实验：光具座共线与像的清晰判定", 7, SUBJECT, G8, 230005),
    (230051, "jphy_g8a_ch05_eye_structure", "眼球结构、成像位置与明视距离", 8, SUBJECT, G8, 230005),
    (230052, "jphy_g8a_ch05_myopia_hyperopia", "近视眼与远视眼的成因及矫正透镜选择", 9, SUBJECT, G8, 230005),
    (230053, "jphy_g8a_ch05_microscope_telescope", "显微镜、望远镜的物镜目镜组合与成像特点", 10, SUBJECT, G8, 230005),

    # 第六章 质量与密度
    (230054, "jphy_g8a_ch06_mass_attribute", "质量是物体属性及 t、kg、g、mg 换算", 1, SUBJECT, G8, 230006),
    (230055, "jphy_g8a_ch06_balance", "天平使用规范、称量步骤与误差分析", 2, SUBJECT, G8, 230006),
    (230056, "jphy_g8a_ch06_volume_measure", "量筒读数与排水法测不规则固体体积", 3, SUBJECT, G8, 230006),
    (230057, "jphy_g8a_ch06_density_formula", "密度定义式 ρ=m/V 与 g/cm³、kg/m³ 换算", 4, SUBJECT, G8, 230006),
    (230058, "jphy_g8a_ch06_density_meaning", "密度的物理意义、物质鉴别与图像分析", 5, SUBJECT, G8, 230006),
    (230059, "jphy_g8a_ch06_liquid_density", "测量液体密度的步骤顺序与误差分析", 6, SUBJECT, G8, 230006),
    (230060, "jphy_g8a_ch06_solid_density", "测量固体密度的实验设计：排水法与针压法", 7, SUBJECT, G8, 230006),
    (230061, "jphy_g8a_ch06_density_temperature", "密度与温度的关系、水的反常膨胀", 8, SUBJECT, G8, 230006),
    (230062, "jphy_g8a_ch06_density_application", "密度在选材、空心判断与合金计算中的应用", 9, SUBJECT, G8, 230006),
)

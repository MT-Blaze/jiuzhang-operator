"""人教版初中物理八年级下册：第七章—第十二章目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 4
G8 = 8
BOOK_ID = 1331

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版八年级物理下册",
    "jphy_g8b",
    31,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133101, "第七章 力", "jphy_g8b_ch07", 7, BOOK_ID, None),
    (133111, "第1节 力", "jphy_g8b_ch07_s01", 1, BOOK_ID, 133101),
    (133112, "第2节 弹力", "jphy_g8b_ch07_s02", 2, BOOK_ID, 133101),
    (133113, "第3节 重力", "jphy_g8b_ch07_s03", 3, BOOK_ID, 133101),

    (133102, "第八章 运动和力", "jphy_g8b_ch08", 8, BOOK_ID, None),
    (133121, "第1节 牛顿第一定律", "jphy_g8b_ch08_s01", 1, BOOK_ID, 133102),
    (133122, "第2节 二力平衡", "jphy_g8b_ch08_s02", 2, BOOK_ID, 133102),
    (133123, "第3节 摩擦力", "jphy_g8b_ch08_s03", 3, BOOK_ID, 133102),

    (133103, "第九章 压强", "jphy_g8b_ch09", 9, BOOK_ID, None),
    (133131, "第1节 压强", "jphy_g8b_ch09_s01", 1, BOOK_ID, 133103),
    (133132, "第2节 液体的压强", "jphy_g8b_ch09_s02", 2, BOOK_ID, 133103),
    (133133, "第3节 大气压强", "jphy_g8b_ch09_s03", 3, BOOK_ID, 133103),
    (
        133134,
        "第4节 流体压强与流速的关系",
        "jphy_g8b_ch09_s04",
        4,
        BOOK_ID,
        133103,
    ),

    (133104, "第十章 浮力", "jphy_g8b_ch10", 10, BOOK_ID, None),
    (133141, "第1节 浮力", "jphy_g8b_ch10_s01", 1, BOOK_ID, 133104),
    (133142, "第2节 阿基米德原理", "jphy_g8b_ch10_s02", 2, BOOK_ID, 133104),
    (
        133143,
        "第3节 物体的浮沉条件及应用",
        "jphy_g8b_ch10_s03",
        3,
        BOOK_ID,
        133104,
    ),

    (133105, "第十一章 功和机械能", "jphy_g8b_ch11", 11, BOOK_ID, None),
    (133151, "第1节 功", "jphy_g8b_ch11_s01", 1, BOOK_ID, 133105),
    (133152, "第2节 功率", "jphy_g8b_ch11_s02", 2, BOOK_ID, 133105),
    (133153, "第3节 动能和势能", "jphy_g8b_ch11_s03", 3, BOOK_ID, 133105),
    (
        133154,
        "第4节 机械能及其转化",
        "jphy_g8b_ch11_s04",
        4,
        BOOK_ID,
        133105,
    ),

    (133106, "第十二章 简单机械", "jphy_g8b_ch12", 12, BOOK_ID, None),
    (133161, "第1节 杠杆", "jphy_g8b_ch12_s01", 1, BOOK_ID, 133106),
    (133162, "第2节 滑轮", "jphy_g8b_ch12_s02", 2, BOOK_ID, 133106),
    (133163, "第3节 机械效率", "jphy_g8b_ch12_s03", 3, BOOK_ID, 133106),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 231001-231006 为册域层，231007-231068 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (231001, "jphy_g8b_domain_ch07", "初中八下·第七章 力：力的三要素、弹力与重力", 1, SUBJECT, G8, None),
    (231002, "jphy_g8b_domain_ch08", "初中八下·第八章 运动和力：牛顿第一定律、二力平衡与摩擦", 2, SUBJECT, G8, None),
    (231003, "jphy_g8b_domain_ch09", "初中八下·第九章 压强：固体、液体与大气压强", 3, SUBJECT, G8, None),
    (231004, "jphy_g8b_domain_ch10", "初中八下·第十章 浮力：阿基米德原理与浮沉条件", 4, SUBJECT, G8, None),
    (231005, "jphy_g8b_domain_ch11", "初中八下·第十一章 功和机械能：功、功率与能量转化", 5, SUBJECT, G8, None),
    (231006, "jphy_g8b_domain_ch12", "初中八下·第十二章 简单机械：杠杆、滑轮与机械效率", 6, SUBJECT, G8, None),

    # 第七章 力
    (231007, "jphy_g8b_ch07_effect", "力的作用效果与运动状态改变的判断", 1, SUBJECT, G8, 231001),
    (231008, "jphy_g8b_ch07_elements", "力的三要素及其对作用效果的影响", 2, SUBJECT, G8, 231001),
    (231009, "jphy_g8b_ch07_diagram", "力的示意图与力的图示规范画法", 3, SUBJECT, G8, 231001),
    (231010, "jphy_g8b_ch07_mutual", "力的相互性与施力物体、受力物体辨析", 4, SUBJECT, G8, 231001),
    (231011, "jphy_g8b_ch07_elastic", "弹力、弹性形变与弹力产生的条件", 5, SUBJECT, G8, 231001),
    (231012, "jphy_g8b_ch07_spring_scale", "弹簧测力计的原理、使用规范与读数", 6, SUBJECT, G8, 231001),
    (231013, "jphy_g8b_ch07_gravity_size", "重力的大小 G=mg 与 g=9.8 N/kg 的物理意义", 7, SUBJECT, G8, 231001),
    (231014, "jphy_g8b_ch07_gravity_direction", "重力的方向竖直向下与重垂线的应用", 8, SUBJECT, G8, 231001),
    (231015, "jphy_g8b_ch07_center", "重心位置与稳度、重力示意图作图", 9, SUBJECT, G8, 231001),

    # 第八章 运动和力
    (231016, "jphy_g8b_ch08_inertia_experiment", "阻力对运动影响的斜面实验与科学推理", 1, SUBJECT, G8, 231002),
    (231017, "jphy_g8b_ch08_first_law", "牛顿第一定律的内容、成立条件与理解", 2, SUBJECT, G8, 231002),
    (231018, "jphy_g8b_ch08_inertia", "惯性概念与惯性现象的解释", 3, SUBJECT, G8, 231002),
    (231019, "jphy_g8b_ch08_inertia_mass", "惯性大小只由质量决定及相关误区", 4, SUBJECT, G8, 231002),
    (231020, "jphy_g8b_ch08_balance_condition", "二力平衡的四个条件与平衡状态判断", 5, SUBJECT, G8, 231002),
    (231021, "jphy_g8b_ch08_balance_vs_interaction", "平衡力与相互作用力的区别", 6, SUBJECT, G8, 231002),
    (231022, "jphy_g8b_ch08_balance_experiment", "探究二力平衡条件的实验设计与评估", 7, SUBJECT, G8, 231002),
    (231023, "jphy_g8b_ch08_friction_measure", "滑动摩擦力的测量与影响因素的探究", 8, SUBJECT, G8, 231002),
    (231024, "jphy_g8b_ch08_friction_adjust", "增大与减小摩擦的常用方法", 9, SUBJECT, G8, 231002),
    (231025, "jphy_g8b_ch08_friction_static", "静摩擦、滚动摩擦与摩擦力方向的判断", 10, SUBJECT, G8, 231002),

    # 第九章 压强
    (231026, "jphy_g8b_ch09_pressure_concept", "压力与重力的区别及压力示意图", 1, SUBJECT, G8, 231003),
    (231027, "jphy_g8b_ch09_pressure_formula", "压强定义式 p=F/S 与帕斯卡单位换算", 2, SUBJECT, G8, 231003),
    (231028, "jphy_g8b_ch09_pressure_change", "增大和减小压强的方法及应用", 3, SUBJECT, G8, 231003),
    (231029, "jphy_g8b_ch09_liquid_feature", "液体压强的特点与压强计实验探究", 4, SUBJECT, G8, 231003),
    (231030, "jphy_g8b_ch09_liquid_formula", "液体压强公式 p=ρgh 及深度 h 的理解", 5, SUBJECT, G8, 231003),
    (231031, "jphy_g8b_ch09_communicating", "连通器原理与船闸、茶壶等应用", 6, SUBJECT, G8, 231003),
    (231032, "jphy_g8b_ch09_atmosphere_exist", "大气压的存在与马德堡半球实验", 7, SUBJECT, G8, 231003),
    (231033, "jphy_g8b_ch09_torricelli", "托里拆利实验与标准大气压的数值", 8, SUBJECT, G8, 231003),
    (231034, "jphy_g8b_ch09_atmosphere_height", "大气压随高度变化及与沸点的关系", 9, SUBJECT, G8, 231003),
    (231035, "jphy_g8b_ch09_flow_pressure", "流体压强与流速的关系及飞机升力", 10, SUBJECT, G8, 231003),
    (231036, "jphy_g8b_ch09_pressure_calc", "固体与液体压强的综合计算及容器问题", 11, SUBJECT, G8, 231003),

    # 第十章 浮力
    (231037, "jphy_g8b_ch10_concept", "浮力的方向、施力物体与产生原因", 1, SUBJECT, G8, 231004),
    (231038, "jphy_g8b_ch10_weighing", "称重法测浮力 F浮=G-F示", 2, SUBJECT, G8, 231004),
    (231039, "jphy_g8b_ch10_factors", "决定浮力大小的因素与探究实验", 3, SUBJECT, G8, 231004),
    (231040, "jphy_g8b_ch10_archimedes", "阿基米德原理的内容与 F浮=ρ液gV排", 4, SUBJECT, G8, 231004),
    (231041, "jphy_g8b_ch10_displaced", "V排 与物体体积、浸入深度的关系", 5, SUBJECT, G8, 231004),
    (231042, "jphy_g8b_ch10_floating_condition", "物体浮沉的受力条件与密度条件", 6, SUBJECT, G8, 231004),
    (231043, "jphy_g8b_ch10_float_suspend", "漂浮与悬浮的区别及受力分析", 7, SUBJECT, G8, 231004),
    (231044, "jphy_g8b_ch10_ship_densimeter", "轮船、密度计的浮力应用原理", 8, SUBJECT, G8, 231004),
    (231045, "jphy_g8b_ch10_submarine_balloon", "潜水艇与气球的浮沉控制", 9, SUBJECT, G8, 231004),
    (231046, "jphy_g8b_ch10_buoyancy_calc", "浮力综合计算与液面升降判断", 10, SUBJECT, G8, 231004),
    (231047, "jphy_g8b_ch10_buoyancy_pressure", "浮力与容器底压强、压力的综合", 11, SUBJECT, G8, 231004),

    # 第十一章 功和机械能
    (231048, "jphy_g8b_ch11_work_factors", "做功的两个必要因素与不做功的三种情况", 1, SUBJECT, G8, 231005),
    (231049, "jphy_g8b_ch11_work_calc", "功的计算 W=Fs 与焦耳单位", 2, SUBJECT, G8, 231005),
    (231050, "jphy_g8b_ch11_power_formula", "功率定义式 P=W/t 与瓦特单位", 3, SUBJECT, G8, 231005),
    (231051, "jphy_g8b_ch11_power_fv", "功率推导式 P=Fv 及机车牵引问题", 4, SUBJECT, G8, 231005),
    (231052, "jphy_g8b_ch11_power_measure", "功率的估测与爬楼功率测量", 5, SUBJECT, G8, 231005),
    (231053, "jphy_g8b_ch11_kinetic", "动能的影响因素与探究实验", 6, SUBJECT, G8, 231005),
    (231054, "jphy_g8b_ch11_potential", "重力势能与弹性势能的影响因素", 7, SUBJECT, G8, 231005),
    (231055, "jphy_g8b_ch11_mechanical", "机械能的概念与机械能守恒条件", 8, SUBJECT, G8, 231005),
    (231056, "jphy_g8b_ch11_conversion", "动能与势能相互转化的实例分析", 9, SUBJECT, G8, 231005),
    (231057, "jphy_g8b_ch11_friction_loss", "阻力存在时的机械能转化与损失", 10, SUBJECT, G8, 231005),

    # 第十二章 简单机械
    (231058, "jphy_g8b_ch12_lever_elements", "杠杆的五要素与力臂的画法", 1, SUBJECT, G8, 231006),
    (231059, "jphy_g8b_ch12_lever_balance", "杠杆平衡条件 F1l1=F2l2 与探究实验", 2, SUBJECT, G8, 231006),
    (231060, "jphy_g8b_ch12_lever_types", "省力、费力、等臂杠杆的分类判断", 3, SUBJECT, G8, 231006),
    (231061, "jphy_g8b_ch12_lever_min_force", "杠杆最小动力与动态平衡分析", 4, SUBJECT, G8, 231006),
    (231062, "jphy_g8b_ch12_fixed_pulley", "定滑轮的特点与等臂杠杆实质", 5, SUBJECT, G8, 231006),
    (231063, "jphy_g8b_ch12_moving_pulley", "动滑轮的特点与省力杠杆实质", 6, SUBJECT, G8, 231006),
    (231064, "jphy_g8b_ch12_pulley_group", "滑轮组的绕线方式与承担物重的绳子段数 n", 7, SUBJECT, G8, 231006),
    (231065, "jphy_g8b_ch12_efficiency_formula", "机械效率 η=W有/W总 与有用功、额外功", 8, SUBJECT, G8, 231006),
    (231066, "jphy_g8b_ch12_efficiency_experiment", "测量滑轮组机械效率的实验设计", 9, SUBJECT, G8, 231006),
    (231067, "jphy_g8b_ch12_efficiency_factors", "影响滑轮组机械效率的因素", 10, SUBJECT, G8, 231006),
    (231068, "jphy_g8b_ch12_incline", "斜面省力分析与斜面的机械效率", 11, SUBJECT, G8, 231006),
)

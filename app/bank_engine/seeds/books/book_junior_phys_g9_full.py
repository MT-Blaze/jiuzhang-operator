"""人教版初中物理九年级全一册：第十三章—第二十二章目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 4
G9 = 9
BOOK_ID = 1332

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版九年级物理全一册",
    "jphy_g9",
    32,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133201, "第十三章 内能", "jphy_g9_ch13", 13, BOOK_ID, None),
    (133211, "第1节 分子热运动", "jphy_g9_ch13_s01", 1, BOOK_ID, 133201),
    (133212, "第2节 内能", "jphy_g9_ch13_s02", 2, BOOK_ID, 133201),
    (133213, "第3节 比热容", "jphy_g9_ch13_s03", 3, BOOK_ID, 133201),

    (133202, "第十四章 内能的利用", "jphy_g9_ch14", 14, BOOK_ID, None),
    (133214, "第1节 热机", "jphy_g9_ch14_s01", 1, BOOK_ID, 133202),
    (133215, "第2节 热机的效率", "jphy_g9_ch14_s02", 2, BOOK_ID, 133202),
    (133216, "第3节 能量的转化和守恒", "jphy_g9_ch14_s03", 3, BOOK_ID, 133202),

    (133203, "第十五章 电流和电路", "jphy_g9_ch15", 15, BOOK_ID, None),
    (133217, "第1节 两种电荷", "jphy_g9_ch15_s01", 1, BOOK_ID, 133203),
    (133218, "第2节 电流和电路", "jphy_g9_ch15_s02", 2, BOOK_ID, 133203),
    (133219, "第3节 串联和并联", "jphy_g9_ch15_s03", 3, BOOK_ID, 133203),
    (133220, "第4节 电流的测量", "jphy_g9_ch15_s04", 4, BOOK_ID, 133203),
    (133221, "第5节 串、并联电路中电流的规律", "jphy_g9_ch15_s05", 5, BOOK_ID, 133203),

    (133204, "第十六章 电压 电阻", "jphy_g9_ch16", 16, BOOK_ID, None),
    (133222, "第1节 电压", "jphy_g9_ch16_s01", 1, BOOK_ID, 133204),
    (133223, "第2节 串、并联电路中电压的规律", "jphy_g9_ch16_s02", 2, BOOK_ID, 133204),
    (133224, "第3节 电阻", "jphy_g9_ch16_s03", 3, BOOK_ID, 133204),
    (133225, "第4节 变阻器", "jphy_g9_ch16_s04", 4, BOOK_ID, 133204),

    (133205, "第十七章 欧姆定律", "jphy_g9_ch17", 17, BOOK_ID, None),
    (133226, "第1节 电流与电压和电阻的关系", "jphy_g9_ch17_s01", 1, BOOK_ID, 133205),
    (133227, "第2节 欧姆定律", "jphy_g9_ch17_s02", 2, BOOK_ID, 133205),
    (133228, "第3节 电阻的测量", "jphy_g9_ch17_s03", 3, BOOK_ID, 133205),
    (133229, "第4节 欧姆定律在串、并联电路中的应用", "jphy_g9_ch17_s04", 4, BOOK_ID, 133205),

    (133206, "第十八章 电功率", "jphy_g9_ch18", 18, BOOK_ID, None),
    (133230, "第1节 电能 电功", "jphy_g9_ch18_s01", 1, BOOK_ID, 133206),
    (133231, "第2节 电功率", "jphy_g9_ch18_s02", 2, BOOK_ID, 133206),
    (133232, "第3节 测量小灯泡的电功率", "jphy_g9_ch18_s03", 3, BOOK_ID, 133206),
    (133233, "第4节 焦耳定律", "jphy_g9_ch18_s04", 4, BOOK_ID, 133206),

    (133207, "第十九章 生活用电", "jphy_g9_ch19", 19, BOOK_ID, None),
    (133234, "第1节 家庭电路", "jphy_g9_ch19_s01", 1, BOOK_ID, 133207),
    (133235, "第2节 家庭电路中电流过大的原因", "jphy_g9_ch19_s02", 2, BOOK_ID, 133207),
    (133236, "第3节 安全用电", "jphy_g9_ch19_s03", 3, BOOK_ID, 133207),

    (133208, "第二十章 电与磁", "jphy_g9_ch20", 20, BOOK_ID, None),
    (133237, "第1节 磁现象 磁场", "jphy_g9_ch20_s01", 1, BOOK_ID, 133208),
    (133238, "第2节 电生磁", "jphy_g9_ch20_s02", 2, BOOK_ID, 133208),
    (133239, "第3节 电磁铁 电磁继电器", "jphy_g9_ch20_s03", 3, BOOK_ID, 133208),
    (133240, "第4节 电动机", "jphy_g9_ch20_s04", 4, BOOK_ID, 133208),
    (133241, "第5节 磁生电", "jphy_g9_ch20_s05", 5, BOOK_ID, 133208),

    (133209, "第二十一章 信息的传递", "jphy_g9_ch21", 21, BOOK_ID, None),
    (133242, "第1节 现代顺风耳——电话", "jphy_g9_ch21_s01", 1, BOOK_ID, 133209),
    (133243, "第2节 电磁波的海洋", "jphy_g9_ch21_s02", 2, BOOK_ID, 133209),
    (133244, "第3节 广播、电视和移动通信", "jphy_g9_ch21_s03", 3, BOOK_ID, 133209),
    (133245, "第4节 越来越宽的信息之路", "jphy_g9_ch21_s04", 4, BOOK_ID, 133209),

    (133210, "第二十二章 能源与可持续发展", "jphy_g9_ch22", 22, BOOK_ID, None),
    (133246, "第1节 能源", "jphy_g9_ch22_s01", 1, BOOK_ID, 133210),
    (133247, "第2节 核能", "jphy_g9_ch22_s02", 2, BOOK_ID, 133210),
    (133248, "第3节 太阳能", "jphy_g9_ch22_s03", 3, BOOK_ID, 133210),
    (133249, "第4节 能源与可持续发展", "jphy_g9_ch22_s04", 4, BOOK_ID, 133210),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 232001-232010 为册域层，232011-232076 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    # 册域层
    (232001, "jphy_g9_domain_ch13", "初中九全·第十三章 内能：分子热运动、内能与比热容", 13, SUBJECT, G9, None),
    (232002, "jphy_g9_domain_ch14", "初中九全·第十四章 内能的利用：热机、热机效率与能量守恒", 14, SUBJECT, G9, None),
    (232003, "jphy_g9_domain_ch15", "初中九全·第十五章 电流和电路：电荷、电路连接与电流规律", 15, SUBJECT, G9, None),
    (232004, "jphy_g9_domain_ch16", "初中九全·第十六章 电压 电阻：电压规律、电阻与变阻器", 16, SUBJECT, G9, None),
    (232005, "jphy_g9_domain_ch17", "初中九全·第十七章 欧姆定律：电流电压电阻关系与电阻测量", 17, SUBJECT, G9, None),
    (232006, "jphy_g9_domain_ch18", "初中九全·第十八章 电功率：电功、电功率与焦耳定律", 18, SUBJECT, G9, None),
    (232007, "jphy_g9_domain_ch19", "初中九全·第十九章 生活用电：家庭电路、过载原因与安全用电", 19, SUBJECT, G9, None),
    (232008, "jphy_g9_domain_ch20", "初中九全·第二十章 电与磁：磁场、电生磁、电动机与磁生电", 20, SUBJECT, G9, None),
    (232009, "jphy_g9_domain_ch21", "初中九全·第二十一章 信息的传递：电话、电磁波与通信方式", 21, SUBJECT, G9, None),
    (232010, "jphy_g9_domain_ch22", "初中九全·第二十二章 能源与可持续发展：能源分类、核能与太阳能", 22, SUBJECT, G9, None),

    # 第十三章 内能
    (232011, "jphy_g9_ch13_diffusion", "物质的构成与扩散现象：分子热运动的证据", 1, SUBJECT, G9, 232001),
    (232012, "jphy_g9_ch13_molecular_force", "分子间引力和斥力并存与分子动理论要点", 2, SUBJECT, G9, 232001),
    (232013, "jphy_g9_ch13_internal_energy", "内能的概念及一切物体都具有内能", 3, SUBJECT, G9, 232001),
    (232014, "jphy_g9_ch13_change_ways", "做功和热传递改变内能的两种方式及等效性", 4, SUBJECT, G9, 232001),
    (232015, "jphy_g9_ch13_heat_transfer", "热传递的条件、方向与热量概念的辨析", 5, SUBJECT, G9, 232001),
    (232016, "jphy_g9_ch13_specific_heat", "比热容的物理意义与水的比热容大的应用", 6, SUBJECT, G9, 232001),
    (232017, "jphy_g9_ch13_heat_calc", "热量计算 Q=cmΔt 与热平衡方程的应用", 7, SUBJECT, G9, 232001),

    # 第十四章 内能的利用
    (232018, "jphy_g9_ch14_engine_cycle", "热机的工作原理与汽油机四个冲程的判定", 1, SUBJECT, G9, 232002),
    (232019, "jphy_g9_ch14_diesel", "柴油机与汽油机在构造和点火方式上的区别", 2, SUBJECT, G9, 232002),
    (232020, "jphy_g9_ch14_fuel_value", "燃料的热值及完全燃烧放热 Q=qm 的计算", 3, SUBJECT, G9, 232002),
    (232021, "jphy_g9_ch14_efficiency", "热机效率的定义、计算与提高途径", 4, SUBJECT, G9, 232002),
    (232022, "jphy_g9_ch14_energy_law", "能量守恒定律与能量转化转移的方向性", 5, SUBJECT, G9, 232002),

    # 第十五章 电流和电路
    (232023, "jphy_g9_ch15_charges", "两种电荷、电荷间相互作用与摩擦起电实质", 1, SUBJECT, G9, 232003),
    (232024, "jphy_g9_ch15_electroscope", "验电器原理及导体、绝缘体的导电差异", 2, SUBJECT, G9, 232003),
    (232025, "jphy_g9_ch15_current_direction", "电流的形成、方向规定与电源的作用", 3, SUBJECT, G9, 232003),
    (232026, "jphy_g9_ch15_circuit_states", "电路组成与通路、断路、短路三种状态", 4, SUBJECT, G9, 232003),
    (232027, "jphy_g9_ch15_circuit_diagram", "电路图的规范画法与实物图的对应连接", 5, SUBJECT, G9, 232003),
    (232028, "jphy_g9_ch15_series_parallel", "串联电路和并联电路的特点与识别方法", 6, SUBJECT, G9, 232003),
    (232029, "jphy_g9_ch15_ammeter", "电流表的使用规范、量程选择与读数", 7, SUBJECT, G9, 232003),
    (232030, "jphy_g9_ch15_current_rule", "串、并联电路中电流规律及实验结论", 8, SUBJECT, G9, 232003),

    # 第十六章 电压 电阻
    (232031, "jphy_g9_ch16_voltage", "电压的作用、单位与电压表的使用规范", 1, SUBJECT, G9, 232004),
    (232032, "jphy_g9_ch16_voltage_rule", "串、并联电路中电压规律及探究实验", 2, SUBJECT, G9, 232004),
    (232033, "jphy_g9_ch16_resistance", "电阻的概念、单位与影响电阻大小的因素", 3, SUBJECT, G9, 232004),
    (232034, "jphy_g9_ch16_rheostat", "滑动变阻器的构造、原理与接线柱接法", 4, SUBJECT, G9, 232004),
    (232035, "jphy_g9_ch16_resistance_box", "电阻箱读数与变阻器在电路中的调节作用", 5, SUBJECT, G9, 232004),

    # 第十七章 欧姆定律
    (232036, "jphy_g9_ch17_experiment", "探究电流与电压、电阻关系的控制变量实验", 1, SUBJECT, G9, 232005),
    (232037, "jphy_g9_ch17_law", "欧姆定律 I=U/R 的内容、理解与简单计算", 2, SUBJECT, G9, 232005),
    (232038, "jphy_g9_ch17_measure_r", "伏安法测电阻的电路设计、步骤与误差分析", 3, SUBJECT, G9, 232005),
    (232039, "jphy_g9_ch17_series_apply", "欧姆定律在串联电路中的分压规律与应用", 4, SUBJECT, G9, 232005),
    (232040, "jphy_g9_ch17_parallel_apply", "欧姆定律在并联电路中的分流规律与应用", 5, SUBJECT, G9, 232005),
    (232041, "jphy_g9_ch17_dynamic_fault", "滑动变阻器引起的动态电路分析与故障判断", 6, SUBJECT, G9, 232005),

    # 第十八章 电功率
    (232042, "jphy_g9_ch18_work", "电功的实质、单位与 W=UIt 的计算", 1, SUBJECT, G9, 232006),
    (232043, "jphy_g9_ch18_meter", "电能表的参数含义、读数与转数法测电功", 2, SUBJECT, G9, 232006),
    (232044, "jphy_g9_ch18_power", "电功率的定义式 P=W/t 与计算式 P=UI", 3, SUBJECT, G9, 232006),
    (232045, "jphy_g9_ch18_rated", "额定功率与实际功率的区别及灯泡亮度判断", 4, SUBJECT, G9, 232006),
    (232046, "jphy_g9_ch18_measure_bulb", "测量小灯泡电功率的实验电路与数据处理", 5, SUBJECT, G9, 232006),
    (232047, "jphy_g9_ch18_joule", "焦耳定律 Q=I²Rt 及纯电阻电路的电热计算", 6, SUBJECT, G9, 232006),
    (232048, "jphy_g9_ch18_power_safety", "电功率与电能、时间结合的综合计算", 7, SUBJECT, G9, 232006),

    # 第十九章 生活用电
    (232049, "jphy_g9_ch19_home_circuit", "家庭电路的组成、连接顺序与各元件作用", 1, SUBJECT, G9, 232007),
    (232050, "jphy_g9_ch19_live_neutral", "火线、零线的辨别与试电笔的正确使用", 2, SUBJECT, G9, 232007),
    (232051, "jphy_g9_ch19_grounding", "三线插头、三孔插座与漏电保护器的接地保护", 3, SUBJECT, G9, 232007),
    (232052, "jphy_g9_ch19_overcurrent", "家庭电路中电流过大的短路和过载原因", 4, SUBJECT, G9, 232007),
    (232053, "jphy_g9_ch19_fuse", "保险丝、空气开关的选型与保护原理", 5, SUBJECT, G9, 232007),
    (232054, "jphy_g9_ch19_safety", "触电类型、触电急救与安全用电原则", 6, SUBJECT, G9, 232007),

    # 第二十章 电与磁
    (232055, "jphy_g9_ch20_magnet", "磁体、磁极、磁化与磁极间相互作用", 1, SUBJECT, G9, 232008),
    (232056, "jphy_g9_ch20_field", "磁场的基本性质与磁感线的描述方法", 2, SUBJECT, G9, 232008),
    (232057, "jphy_g9_ch20_geomagnetic", "地磁场分布与指南针指向原理", 3, SUBJECT, G9, 232008),
    (232058, "jphy_g9_ch20_oersted", "电流的磁效应与奥斯特实验现象", 4, SUBJECT, G9, 232008),
    (232059, "jphy_g9_ch20_solenoid", "通电螺线管的磁场与安培定则的应用", 5, SUBJECT, G9, 232008),
    (232060, "jphy_g9_ch20_electromagnet", "影响电磁铁磁性强弱的因素与探究方法", 6, SUBJECT, G9, 232008),
    (232061, "jphy_g9_ch20_relay", "电磁继电器的结构、工作原理与控制电路", 7, SUBJECT, G9, 232008),
    (232062, "jphy_g9_ch20_motor", "磁场对通电导线的作用与电动机的转动原理", 8, SUBJECT, G9, 232008),
    (232063, "jphy_g9_ch20_induction", "电磁感应现象、感应电流条件与发电机原理", 9, SUBJECT, G9, 232008),
    (232064, "jphy_g9_ch20_motor_generator", "电动机与发电机在原理和能量转化上的对比", 10, SUBJECT, G9, 232008),

    # 第二十一章 信息的传递
    (232065, "jphy_g9_ch21_telephone", "电话话筒与听筒的声电信号转换过程", 1, SUBJECT, G9, 232009),
    (232066, "jphy_g9_ch21_wave", "电磁波的产生、传播与波速公式 c=λf", 2, SUBJECT, G9, 232009),
    (232067, "jphy_g9_ch21_broadcast", "无线电广播与电视的信号发射和接收过程", 3, SUBJECT, G9, 232009),
    (232068, "jphy_g9_ch21_mobile", "移动电话的工作原理与基站的中继作用", 4, SUBJECT, G9, 232009),
    (232069, "jphy_g9_ch21_microwave_satellite", "微波通信、卫星通信与光纤通信的特点", 5, SUBJECT, G9, 232009),
    (232070, "jphy_g9_ch21_network", "网络通信与信息传递方式的发展趋势", 6, SUBJECT, G9, 232009),

    # 第二十二章 能源与可持续发展
    (232071, "jphy_g9_ch22_classification", "能源分类：一次能源与二次能源、可再生与不可再生", 1, SUBJECT, G9, 232010),
    (232072, "jphy_g9_ch22_nuclear", "核能、核裂变链式反应与核聚变的条件", 2, SUBJECT, G9, 232010),
    (232073, "jphy_g9_ch22_nuclear_plant", "核电站的能量转化过程与核安全防护", 3, SUBJECT, G9, 232010),
    (232074, "jphy_g9_ch22_solar", "太阳能的来源及光热、光电两种利用方式", 4, SUBJECT, G9, 232010),
    (232075, "jphy_g9_ch22_environment", "能源消耗带来的环境问题与节能减排", 5, SUBJECT, G9, 232010),
    (232076, "jphy_g9_ch22_sustainable", "能量转化方向性与能源可持续发展策略", 6, SUBJECT, G9, 232010),
)

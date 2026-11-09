"""人教版初中生物七年级下册：第四单元 生物圈中的人目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 6
G7 = 7
BOOK_ID = 1336

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版七年级生物下册",
    "jbio_g7b",
    36,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (133601, "第四单元 生物圈中的人", "jbio_g7b_u4", 1, BOOK_ID, None),

    (133611, "第一章 人的由来", "jbio_g7b_u4_c01", 1, BOOK_ID, 133601),
    (133612, "第一节 人类的起源和发展", "jbio_g7b_u4_c01_s01", 1, BOOK_ID, 133611),
    (133613, "第二节 人的生殖", "jbio_g7b_u4_c01_s02", 2, BOOK_ID, 133611),
    (133614, "第三节 青春期", "jbio_g7b_u4_c01_s03", 3, BOOK_ID, 133611),

    (133621, "第二章 人体的营养", "jbio_g7b_u4_c02", 2, BOOK_ID, 133601),
    (133622, "第一节 食物中的营养物质", "jbio_g7b_u4_c02_s01", 1, BOOK_ID, 133621),
    (133623, "第二节 消化和吸收", "jbio_g7b_u4_c02_s02", 2, BOOK_ID, 133621),
    (133624, "第三节 合理营养与食品安全", "jbio_g7b_u4_c02_s03", 3, BOOK_ID, 133621),

    (133631, "第三章 人体的呼吸", "jbio_g7b_u4_c03", 3, BOOK_ID, 133601),
    (133632, "第一节 呼吸道对空气的处理", "jbio_g7b_u4_c03_s01", 1, BOOK_ID, 133631),
    (133633, "第二节 发生在肺内的气体交换", "jbio_g7b_u4_c03_s02", 2, BOOK_ID, 133631),
    (133634, "第三节 空气质量与健康", "jbio_g7b_u4_c03_s03", 3, BOOK_ID, 133631),

    (133641, "第四章 人体内物质的运输", "jbio_g7b_u4_c04", 4, BOOK_ID, 133601),
    (133642, "第一节 流动的组织——血液", "jbio_g7b_u4_c04_s01", 1, BOOK_ID, 133641),
    (133643, "第二节 血流的管道——血管", "jbio_g7b_u4_c04_s02", 2, BOOK_ID, 133641),
    (133644, "第三节 输送血液的泵——心脏", "jbio_g7b_u4_c04_s03", 3, BOOK_ID, 133641),
    (133645, "第四节 输血与血型", "jbio_g7b_u4_c04_s04", 4, BOOK_ID, 133641),

    (133651, "第五章 人体内废物的排出", "jbio_g7b_u4_c05", 5, BOOK_ID, 133601),
    (133652, "第一节 泌尿系统", "jbio_g7b_u4_c05_s01", 1, BOOK_ID, 133651),
    (133653, "第二节 尿的形成与排出", "jbio_g7b_u4_c05_s02", 2, BOOK_ID, 133651),
    (133654, "第三节 其他排泄途径", "jbio_g7b_u4_c05_s03", 3, BOOK_ID, 133651),

    (133661, "第六章 人体生命活动的调节", "jbio_g7b_u4_c06", 6, BOOK_ID, 133601),
    (133662, "第一节 人体对外界环境的感知", "jbio_g7b_u4_c06_s01", 1, BOOK_ID, 133661),
    (133663, "第二节 神经系统的组成", "jbio_g7b_u4_c06_s02", 2, BOOK_ID, 133661),
    (133664, "第三节 神经调节的基本方式", "jbio_g7b_u4_c06_s03", 3, BOOK_ID, 133661),
    (133665, "第四节 激素调节", "jbio_g7b_u4_c06_s04", 4, BOOK_ID, 133661),

    (133671, "第七章 人类活动对生物圈的影响", "jbio_g7b_u4_c07", 7, BOOK_ID, 133601),
    (133672, "第一节 分析人类活动对生态环境的影响", "jbio_g7b_u4_c07_s01", 1, BOOK_ID, 133671),
    (133673, "第二节 探究环境污染对生物的影响", "jbio_g7b_u4_c07_s02", 2, BOOK_ID, 133671),
    (133674, "第三节 拟定保护生态环境的计划", "jbio_g7b_u4_c07_s03", 3, BOOK_ID, 133671),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 236001 为册域顶层，236002-236008 章锚点，236011-236033 节锚点，236034 起为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int, int | None], ...] = (
    (236001, "jbio_g7b_domain_u4", "初中七下·第四单元 生物圈中的人：由来、营养、呼吸、运输、排泄、调节与环境影响", 1, SUBJECT, G7, None),

    # 第一章 人的由来
    (236002, "jbio_g7b_u4_c01", "第一章 人的由来：起源与发展、生殖系统与青春期", 1, SUBJECT, G7, 236001),
    (236011, "jbio_g7b_u4_c01_s01", "第一节 人类的起源和发展：森林古猿、进化阶段与证据", 1, SUBJECT, G7, 236002),
    (236034, "jbio_g7b_human_origin", "人类的起源：森林古猿下地直立行走", 1, SUBJECT, G7, 236011),
    (236035, "jbio_g7b_human_stages", "人类进化的四个阶段：南方古猿、能人、直立人、智人", 2, SUBJECT, G7, 236011),
    (236036, "jbio_g7b_human_evidence", "人类进化的证据：化石、脑容量增大、语言与工具制造", 3, SUBJECT, G7, 236011),
    (236012, "jbio_g7b_u4_c01_s02", "第二节 人的生殖：生殖系统、受精、胚胎发育与分娩", 2, SUBJECT, G7, 236002),
    (236037, "jbio_g7b_male_reproductive", "男性生殖系统：睾丸产生精子并分泌雄性激素", 1, SUBJECT, G7, 236012),
    (236038, "jbio_g7b_female_reproductive", "女性生殖系统：卵巢产生卵细胞并分泌雌性激素", 2, SUBJECT, G7, 236012),
    (236039, "jbio_g7b_fertilization", "受精与胚胎发育：输卵管受精、子宫着床", 3, SUBJECT, G7, 236012),
    (236040, "jbio_g7b_placenta", "胎盘和脐带：胚胎与母体进行物质交换", 4, SUBJECT, G7, 236012),
    (236041, "jbio_g7b_childbirth_ivf", "分娩过程与试管婴儿技术", 5, SUBJECT, G7, 236012),
    (236013, "jbio_g7b_u4_c01_s03", "第三节 青春期：身体变化、第二性征与心理卫生", 3, SUBJECT, G7, 236002),
    (236042, "jbio_g7b_puberty_body", "青春期的身体变化：身高突增与神经、心肺功能增强", 1, SUBJECT, G7, 236013),
    (236043, "jbio_g7b_puberty_sex", "性器官迅速发育与第二性征的出现", 2, SUBJECT, G7, 236013),
    (236044, "jbio_g7b_puberty_mind", "青春期的心理变化与卫生保健", 3, SUBJECT, G7, 236013),

    # 第二章 人体的营养
    (236003, "jbio_g7b_u4_c02", "第二章 人体的营养：营养物质、消化吸收与食品安全", 2, SUBJECT, G7, 236001),
    (236014, "jbio_g7b_u4_c02_s01", "第一节 食物中的营养物质：供能物质、无机盐、维生素与能量测定", 1, SUBJECT, G7, 236003),
    (236045, "jbio_g7b_nutrients_energy", "糖类、脂肪、蛋白质的作用与食物来源", 1, SUBJECT, G7, 236014),
    (236046, "jbio_g7b_water_mineral", "水与无机盐的作用及钙、铁、碘缺乏症", 2, SUBJECT, G7, 236014),
    (236047, "jbio_g7b_vitamins", "维生素 A、B1、C、D 的作用与缺乏症", 3, SUBJECT, G7, 236014),
    (236048, "jbio_g7b_energy_measure", "测定食物中的能量与膳食纤维的作用", 4, SUBJECT, G7, 236014),
    (236015, "jbio_g7b_u4_c02_s02", "第二节 消化和吸收：消化道、消化腺、消化酶与小肠", 2, SUBJECT, G7, 236003),
    (236049, "jbio_g7b_digestive_system", "消化系统的组成：消化道与消化腺", 1, SUBJECT, G7, 236015),
    (236050, "jbio_g7b_teeth", "牙齿的结构与龋齿的预防", 2, SUBJECT, G7, 236015),
    (236051, "jbio_g7b_enzyme_digestion", "淀粉、蛋白质、脂肪的消化过程与消化酶", 3, SUBJECT, G7, 236015),
    (236052, "jbio_g7b_small_intestine", "小肠适于消化和吸收的结构特点", 4, SUBJECT, G7, 236015),
    (236053, "jbio_g7b_absorption_sites", "营养物质的吸收部位与吸收过程", 5, SUBJECT, G7, 236015),
    (236016, "jbio_g7b_u4_c02_s03", "第三节 合理营养与食品安全：平衡膳食与食品安全", 3, SUBJECT, G7, 236003),
    (236054, "jbio_g7b_balanced_diet", "合理营养与平衡膳食宝塔", 1, SUBJECT, G7, 236016),
    (236055, "jbio_g7b_food_safety", "食品安全常识与预防食物中毒", 2, SUBJECT, G7, 236016),

    # 第三章 人体的呼吸
    (236004, "jbio_g7b_u4_c03", "第三章 人体的呼吸：呼吸道、肺内气体交换与空气质量", 3, SUBJECT, G7, 236001),
    (236017, "jbio_g7b_u4_c03_s01", "第一节 呼吸道对空气的处理：呼吸系统组成与呼吸运动", 1, SUBJECT, G7, 236004),
    (236056, "jbio_g7b_respiratory_system", "呼吸系统的组成：呼吸道与肺", 1, SUBJECT, G7, 236017),
    (236057, "jbio_g7b_airway_conditioning", "呼吸道对空气的处理：温暖、湿润、清洁", 2, SUBJECT, G7, 236017),
    (236058, "jbio_g7b_breathing_mechanism", "呼吸运动的原理：呼吸肌与胸廓容积变化", 3, SUBJECT, G7, 236017),
    (236018, "jbio_g7b_u4_c03_s02", "第二节 发生在肺内的气体交换：肺泡结构与两次交换", 2, SUBJECT, G7, 236004),
    (236059, "jbio_g7b_alveoli_structure", "肺泡适于气体交换的结构特点", 1, SUBJECT, G7, 236018),
    (236060, "jbio_g7b_gas_exchange", "肺泡与血液、血液与组织细胞的气体交换过程", 2, SUBJECT, G7, 236018),
    (236061, "jbio_g7b_breath_composition", "吸入气体与呼出气体成分的比较", 3, SUBJECT, G7, 236018),
    (236019, "jbio_g7b_u4_c03_s03", "第三节 空气质量与健康：影响因素与防治措施", 3, SUBJECT, G7, 236004),
    (236062, "jbio_g7b_air_quality", "空气质量影响健康的因素与防治措施", 1, SUBJECT, G7, 236019),

    # 第四章 人体内物质的运输
    (236005, "jbio_g7b_u4_c04", "第四章 人体内物质的运输：血液、血管、心脏与输血", 4, SUBJECT, G7, 236001),
    (236020, "jbio_g7b_u4_c04_s01", "第一节 流动的组织——血液：血浆、血细胞与血红蛋白", 1, SUBJECT, G7, 236005),
    (236063, "jbio_g7b_blood_composition", "血液的组成：血浆与血细胞", 1, SUBJECT, G7, 236020),
    (236064, "jbio_g7b_blood_cells", "红细胞、白细胞、血小板的形态结构与功能", 2, SUBJECT, G7, 236020),
    (236065, "jbio_g7b_hemoglobin", "血红蛋白与贫血", 3, SUBJECT, G7, 236020),
    (236021, "jbio_g7b_u4_c04_s02", "第二节 血流的管道——血管：动脉、静脉与毛细血管", 2, SUBJECT, G7, 236005),
    (236066, "jbio_g7b_vessel_types", "动脉、静脉、毛细血管的结构与功能比较", 1, SUBJECT, G7, 236021),
    (236067, "jbio_g7b_capillary", "毛细血管适于物质交换的特点", 2, SUBJECT, G7, 236021),
    (236022, "jbio_g7b_u4_c04_s03", "第三节 输送血液的泵——心脏：四腔、瓣膜与血液循环", 3, SUBJECT, G7, 236005),
    (236068, "jbio_g7b_heart_chambers", "心脏四腔及其与血管的连接", 1, SUBJECT, G7, 236022),
    (236069, "jbio_g7b_heart_valves", "心脏瓣膜的作用与血液流动方向", 2, SUBJECT, G7, 236022),
    (236070, "jbio_g7b_cardiac_output", "心率、心输出量与心脏的锻炼", 3, SUBJECT, G7, 236022),
    (236023, "jbio_g7b_u4_c04_s04", "第四节 输血与血型：ABO 血型与安全输血", 4, SUBJECT, G7, 236005),
    (236071, "jbio_g7b_blood_type", "ABO 血型系统与安全输血原则", 1, SUBJECT, G7, 236023),
    (236072, "jbio_g7b_blood_donation", "无偿献血的意义与献血量", 2, SUBJECT, G7, 236023),

    # 第五章 人体内废物的排出
    (236006, "jbio_g7b_u4_c05", "第五章 人体内废物的排出：泌尿系统、尿的形成与其他排泄", 5, SUBJECT, G7, 236001),
    (236024, "jbio_g7b_u4_c05_s01", "第一节 泌尿系统：组成、肾单位与滤过重吸收", 1, SUBJECT, G7, 236006),
    (236073, "jbio_g7b_urinary_system", "泌尿系统的组成与各器官功能", 1, SUBJECT, G7, 236024),
    (236074, "jbio_g7b_nephron", "肾单位的结构：肾小球、肾小囊、肾小管", 2, SUBJECT, G7, 236024),
    (236025, "jbio_g7b_u4_c05_s02", "第二节 尿的形成与排出：原尿、尿液与排出途径", 2, SUBJECT, G7, 236006),
    (236075, "jbio_g7b_filtration", "肾小球的滤过作用与原尿的形成", 1, SUBJECT, G7, 236025),
    (236076, "jbio_g7b_reabsorption", "肾小管的重吸收作用与尿液的形成", 2, SUBJECT, G7, 236025),
    (236077, "jbio_g7b_urine_compare", "血浆、原尿与尿液成分的差异比较", 3, SUBJECT, G7, 236025),
    (236078, "jbio_g7b_urination", "尿的排出途径与排尿的意义", 4, SUBJECT, G7, 236025),
    (236026, "jbio_g7b_u4_c05_s03", "第三节 其他排泄途径：皮肤汗腺与呼气", 3, SUBJECT, G7, 236006),
    (236079, "jbio_g7b_skin_excretion", "皮肤的结构与汗腺的排泄功能", 1, SUBJECT, G7, 236026),
    (236080, "jbio_g7b_co2_excretion", "呼气排出二氧化碳和水", 2, SUBJECT, G7, 236026),

    # 第六章 人体生命活动的调节
    (236007, "jbio_g7b_u4_c06", "第六章 人体生命活动的调节：感觉器官、神经系统与激素", 6, SUBJECT, G7, 236001),
    (236027, "jbio_g7b_u4_c06_s01", "第一节 人体对外界环境的感知：眼、耳与其他感觉器官", 1, SUBJECT, G7, 236007),
    (236081, "jbio_g7b_eye_structure", "眼球的结构与视觉的形成", 1, SUBJECT, G7, 236027),
    (236082, "jbio_g7b_myopia", "近视的成因、矫正与用眼卫生", 2, SUBJECT, G7, 236027),
    (236083, "jbio_g7b_ear_structure", "耳的结构与听觉的形成", 3, SUBJECT, G7, 236027),
    (236084, "jbio_g7b_other_senses", "鼻、舌、皮肤等其他感觉器官", 4, SUBJECT, G7, 236027),
    (236028, "jbio_g7b_u4_c06_s02", "第二节 神经系统的组成：中枢神经、周围神经与神经元", 2, SUBJECT, G7, 236007),
    (236085, "jbio_g7b_cns", "中枢神经系统：脑与脊髓", 1, SUBJECT, G7, 236028),
    (236086, "jbio_g7b_neuron", "周围神经系统与神经元的结构功能", 2, SUBJECT, G7, 236028),
    (236029, "jbio_g7b_u4_c06_s03", "第三节 神经调节的基本方式：反射与反射弧", 3, SUBJECT, G7, 236007),
    (236087, "jbio_g7b_reflex_arc", "反射与反射弧的五个环节", 1, SUBJECT, G7, 236029),
    (236088, "jbio_g7b_reflex_types", "简单反射与复杂反射及人类特有的条件反射", 2, SUBJECT, G7, 236029),
    (236030, "jbio_g7b_u4_c06_s04", "第四节 激素调节：内分泌腺、生长激素、甲状腺激素与胰岛素", 4, SUBJECT, G7, 236007),
    (236089, "jbio_g7b_endocrine_glands", "内分泌腺与外分泌腺的区别及主要内分泌腺", 1, SUBJECT, G7, 236030),
    (236090, "jbio_g7b_growth_thyroid", "生长激素、甲状腺激素的作用与分泌异常", 2, SUBJECT, G7, 236030),
    (236091, "jbio_g7b_insulin", "胰岛素与血糖调节、糖尿病", 3, SUBJECT, G7, 236030),

    # 第七章 人类活动对生物圈的影响
    (236008, "jbio_g7b_u4_c07", "第七章 人类活动对生物圈的影响：生态影响、污染探究与保护计划", 7, SUBJECT, G7, 236001),
    (236031, "jbio_g7b_u4_c07_s01", "第一节 分析人类活动对生态环境的影响：正负效应与外来物种", 1, SUBJECT, G7, 236008),
    (236092, "jbio_g7b_human_impact", "人类活动对生态环境的正负面影响", 1, SUBJECT, G7, 236031),
    (236093, "jbio_g7b_invasive_species", "外来物种入侵的危害与生物多样性丧失", 2, SUBJECT, G7, 236031),
    (236032, "jbio_g7b_u4_c07_s02", "第二节 探究环境污染对生物的影响：酸雨、温室效应与实验设计", 2, SUBJECT, G7, 236008),
    (236094, "jbio_g7b_acid_rain", "酸雨的形成、危害与探究实验", 1, SUBJECT, G7, 236032),
    (236095, "jbio_g7b_greenhouse", "温室效应与重金属、固体废弃物污染", 2, SUBJECT, G7, 236032),
    (236096, "jbio_g7b_pollution_experiment", "探究环境污染对生物影响的实验设计", 3, SUBJECT, G7, 236032),
    (236033, "jbio_g7b_u4_c07_s03", "第三节 拟定保护生态环境的计划：具体措施与可持续发展", 3, SUBJECT, G7, 236008),
    (236097, "jbio_g7b_eco_protection", "保护生态环境的具体措施与低碳生活", 1, SUBJECT, G7, 236033),
    (236098, "jbio_g7b_sustainable", "退耕还林还草、垃圾分类与可持续发展", 2, SUBJECT, G7, 236033),
)

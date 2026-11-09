"""统编版（2019）高中思想政治选择性必修第二册（法律与生活）：课框目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G10 = 10
BOOK_ID = 7106

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中思想政治选择性必修第二册（法律与生活）",
    "pol_e2",
    6,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (760101, "第一单元 民事权利与义务", "pol_e2_u01", 1, BOOK_ID, None),
    (760102, "第二单元 家庭与婚姻", "pol_e2_u02", 2, BOOK_ID, None),
    (760103, "第三单元 就业与创业", "pol_e2_u03", 3, BOOK_ID, None),
    (760104, "第四单元 社会争议解决", "pol_e2_u04", 4, BOOK_ID, None),
    (760111, "第一课 在生活中学民法用民法", "pol_e2_l01", 1, BOOK_ID, 760101),
    (760112, "第二课 依法有效保护财产权", "pol_e2_l02", 2, BOOK_ID, 760101),
    (760113, "第三课 订约履约 诚信为本", "pol_e2_l03", 3, BOOK_ID, 760101),
    (760114, "第四课 侵权责任与权利界限", "pol_e2_l04", 4, BOOK_ID, 760101),
    (760115, "第五课 在和睦家庭中成长", "pol_e2_l05", 1, BOOK_ID, 760102),
    (760116, "第六课 珍惜婚姻关系", "pol_e2_l06", 2, BOOK_ID, 760102),
    (760117, "第七课 做个明白的劳动者", "pol_e2_l07", 1, BOOK_ID, 760103),
    (760118, "第八课 自主创业与诚信经营", "pol_e2_l08", 2, BOOK_ID, 760103),
    (760119, "第九课 纠纷的多元解决方式", "pol_e2_l09", 1, BOOK_ID, 760104),
    (760120, "第十课 诉讼实现公平正义", "pol_e2_l10", 2, BOOK_ID, 760104),
    (760121, "第一框 认真对待民事权利与义务", "pol_e2_l01_s01", 1, BOOK_ID, 760111),
    (760122, "第二框 积极维护人身权利", "pol_e2_l01_s02", 2, BOOK_ID, 760111),
    (760123, "第一框 保障各类物权", "pol_e2_l02_s01", 1, BOOK_ID, 760112),
    (760124, "第二框 尊重知识产权", "pol_e2_l02_s02", 2, BOOK_ID, 760112),
    (760125, "第一框 订立合同学问大", "pol_e2_l03_s01", 1, BOOK_ID, 760113),
    (760126, "第二框 有约必守 违约有责", "pol_e2_l03_s02", 2, BOOK_ID, 760113),
    (760127, "第一框 权利保障 于法有据", "pol_e2_l04_s01", 1, BOOK_ID, 760114),
    (760128, "第二框 权利行使 注意界限", "pol_e2_l04_s02", 2, BOOK_ID, 760114),
    (760129, "第一框 家和万事兴", "pol_e2_l05_s01", 1, BOOK_ID, 760115),
    (760130, "第二框 薪火相传有继承", "pol_e2_l05_s02", 2, BOOK_ID, 760115),
    (760131, "第一框 法律保护下的婚姻", "pol_e2_l06_s01", 1, BOOK_ID, 760116),
    (760132, "第二框 夫妻地位平等", "pol_e2_l06_s02", 2, BOOK_ID, 760116),
    (760133, "第一框 立足职场有法宝", "pol_e2_l07_s01", 1, BOOK_ID, 760117),
    (760134, "第二框 心中有数上职场", "pol_e2_l07_s02", 2, BOOK_ID, 760117),
    (760135, "第一框 自主创业 公平竞争", "pol_e2_l08_s01", 1, BOOK_ID, 760118),
    (760136, "第二框 诚信经营 依法纳税", "pol_e2_l08_s02", 2, BOOK_ID, 760118),
    (760137, "第一框 认识调解与仲裁", "pol_e2_l09_s01", 1, BOOK_ID, 760119),
    (760138, "第二框 解析三大诉讼", "pol_e2_l09_s02", 2, BOOK_ID, 760119),
    (760139, "第一框 正确行使诉讼权利", "pol_e2_l10_s01", 1, BOOK_ID, 760120),
    (760140, "第二框 严格遵守诉讼程序", "pol_e2_l10_s02", 2, BOOK_ID, 760120),
    (760141, "第三框 依法收集运用证据", "pol_e2_l10_s03", 3, BOOK_ID, 760120),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (760001, "pol_e2_domain_civil", "民事权利与义务：人身权、物权与知识产权", 1, SUBJECT, None),
    (760002, "pol_e2_domain_family", "家庭与婚姻：亲属、继承与夫妻关系", 2, SUBJECT, None),
    (760003, "pol_e2_domain_employment", "就业与创业：劳动、竞争与纳税", 3, SUBJECT, None),
    (760004, "pol_e2_domain_dispute", "社会争议解决：调解、仲裁与诉讼", 4, SUBJECT, None),

    # 单元域层
    (760005, "pol_e2_unit01_civil", "第一单元 民事权利与义务", 1, SUBJECT, 760001),
    (760006, "pol_e2_unit02_family", "第二单元 家庭与婚姻", 1, SUBJECT, 760002),
    (760007, "pol_e2_unit03_employment", "第三单元 就业与创业", 1, SUBJECT, 760003),
    (760008, "pol_e2_unit04_dispute", "第四单元 社会争议解决", 1, SUBJECT, 760004),

    # 课域层
    (760009, "pol_e2_lesson01", "第一课 在生活中学民法用民法", 1, SUBJECT, 760005),
    (760010, "pol_e2_lesson02", "第二课 依法有效保护财产权", 2, SUBJECT, 760005),
    (760011, "pol_e2_lesson03", "第三课 订约履约 诚信为本", 3, SUBJECT, 760005),
    (760012, "pol_e2_lesson04", "第四课 侵权责任与权利界限", 4, SUBJECT, 760005),
    (760013, "pol_e2_lesson05", "第五课 在和睦家庭中成长", 1, SUBJECT, 760006),
    (760014, "pol_e2_lesson06", "第六课 珍惜婚姻关系", 2, SUBJECT, 760006),
    (760015, "pol_e2_lesson07", "第七课 做个明白的劳动者", 1, SUBJECT, 760007),
    (760016, "pol_e2_lesson08", "第八课 自主创业与诚信经营", 2, SUBJECT, 760007),
    (760017, "pol_e2_lesson09", "第九课 纠纷的多元解决方式", 1, SUBJECT, 760008),
    (760018, "pol_e2_lesson10", "第十课 诉讼实现公平正义", 2, SUBJECT, 760008),

    # 框域层
    (760019, "pol_e2_sec_civil_basics", "第一框 认真对待民事权利与义务", 1, SUBJECT, 760009),
    (760020, "pol_e2_sec_personality_rights", "第二框 积极维护人身权利", 2, SUBJECT, 760009),
    (760021, "pol_e2_sec_property_rights", "第一框 保障各类物权", 1, SUBJECT, 760010),
    (760022, "pol_e2_sec_intellectual_property", "第二框 尊重知识产权", 2, SUBJECT, 760010),
    (760023, "pol_e2_sec_contract_formation", "第一框 订立合同学问大", 1, SUBJECT, 760011),
    (760024, "pol_e2_sec_contract_performance", "第二框 有约必守 违约有责", 2, SUBJECT, 760011),
    (760025, "pol_e2_sec_tort_liability", "第一框 权利保障 于法有据", 1, SUBJECT, 760012),
    (760026, "pol_e2_sec_rights_boundary", "第二框 权利行使 注意界限", 2, SUBJECT, 760012),
    (760027, "pol_e2_sec_family_harmony", "第一框 家和万事兴", 1, SUBJECT, 760013),
    (760028, "pol_e2_sec_inheritance", "第二框 薪火相传有继承", 2, SUBJECT, 760013),
    (760029, "pol_e2_sec_marriage_protection", "第一框 法律保护下的婚姻", 1, SUBJECT, 760014),
    (760030, "pol_e2_sec_spousal_equality", "第二框 夫妻地位平等", 2, SUBJECT, 760014),
    (760031, "pol_e2_sec_labor_rights", "第一框 立足职场有法宝", 1, SUBJECT, 760015),
    (760032, "pol_e2_sec_workplace_practice", "第二框 心中有数上职场", 2, SUBJECT, 760015),
    (760033, "pol_e2_sec_entrepreneurship", "第一框 自主创业 公平竞争", 1, SUBJECT, 760016),
    (760034, "pol_e2_sec_honest_operation", "第二框 诚信经营 依法纳税", 2, SUBJECT, 760016),
    (760035, "pol_e2_sec_mediation_arbitration", "第一框 认识调解与仲裁", 1, SUBJECT, 760017),
    (760036, "pol_e2_sec_three_litigations", "第二框 解析三大诉讼", 2, SUBJECT, 760017),
    (760037, "pol_e2_sec_litigation_rights", "第一框 正确行使诉讼权利", 1, SUBJECT, 760018),
    (760038, "pol_e2_sec_litigation_procedure", "第二框 严格遵守诉讼程序", 2, SUBJECT, 760018),
    (760039, "pol_e2_sec_evidence", "第三框 依法收集运用证据", 3, SUBJECT, 760018),

    # 1.1 认真对待民事权利与义务
    (760040, "pol_e2_civil_object_principles", "民法的调整对象与基本原则", 1, SUBJECT, 760019),
    (760041, "pol_e2_civil_relation_elements", "民事法律关系的主体、客体与内容", 2, SUBJECT, 760019),
    (760042, "pol_e2_civil_capacity_facts", "民事权利能力、民事行为能力与民事法律事实", 3, SUBJECT, 760019),

    # 1.2 积极维护人身权利
    (760043, "pol_e2_personality_identity", "人身权的类型：人格权与身份权", 1, SUBJECT, 760020),
    (760044, "pol_e2_specific_personality", "生命健康权、姓名权、肖像权、名誉权与隐私权", 2, SUBJECT, 760020),

    # 2.1 保障各类物权
    (760045, "pol_e2_property_change_rules", "物权法定、公示公信与物权变动规则", 1, SUBJECT, 760021),
    (760046, "pol_e2_ownership_bona_fide", "所有权、共有与善意取得", 2, SUBJECT, 760021),
    (760047, "pol_e2_usufruct_security", "用益物权与担保物权", 3, SUBJECT, 760021),

    # 2.2 尊重知识产权
    (760048, "pol_e2_ip_scope_features", "知识产权的范围与法律特征", 1, SUBJECT, 760022),
    (760049, "pol_e2_copyright", "著作权的主体、内容与保护期限", 2, SUBJECT, 760022),
    (760050, "pol_e2_patent_trademark", "专利权的取得条件与商标注册、侵权认定", 3, SUBJECT, 760022),

    # 3.1 订立合同学问大
    (760051, "pol_e2_offer_acceptance", "合同订立：要约与承诺", 1, SUBJECT, 760023),
    (760052, "pol_e2_contract_validity_terms", "合同成立、生效与格式条款规制", 2, SUBJECT, 760023),
    (760053, "pol_e2_culpa_in_contrahendo", "缔约过失责任与合同主要条款", 3, SUBJECT, 760023),

    # 3.2 有约必守 违约有责
    (760054, "pol_e2_performance_defenses", "合同履行原则与同时履行、先履行、不安抗辩权", 1, SUBJECT, 760024),
    (760055, "pol_e2_breach_remedies", "违约责任：继续履行、赔偿损失、违约金与定金", 2, SUBJECT, 760024),
    (760056, "pol_e2_force_majeure_termination", "不可抗力免责与合同变更、转让、解除", 3, SUBJECT, 760024),

    # 4.1 权利保障 于法有据
    (760057, "pol_e2_tort_elements", "侵权责任的一般构成要件", 1, SUBJECT, 760025),
    (760058, "pol_e2_tort_fault_principles", "过错责任、过错推定与无过错责任", 2, SUBJECT, 760025),
    (760059, "pol_e2_special_tort", "特殊侵权责任：监护人、用人单位、饲养动物与高空抛物", 3, SUBJECT, 760025),
    (760060, "pol_e2_tort_remedies", "侵权责任的承担方式与损害赔偿", 4, SUBJECT, 760025),

    # 4.2 权利行使 注意界限
    (760061, "pol_e2_no_abuse_neighbor", "禁止权利滥用与相邻关系", 1, SUBJECT, 760026),
    (760062, "pol_e2_self_defense_necessity", "正当防卫、紧急避险与自助行为", 2, SUBJECT, 760026),
    (760063, "pol_e2_limitation_period", "诉讼时效与除斥期间", 3, SUBJECT, 760026),

    # 5.1 家和万事兴
    (760064, "pol_e2_parent_child_duties", "父母子女关系与抚养、教育、保护义务", 1, SUBJECT, 760027),
    (760065, "pol_e2_support_maintenance", "赡养义务与家庭成员间扶养", 2, SUBJECT, 760027),
    (760066, "pol_e2_guardianship_domestic_violence", "监护制度与家庭暴力防治", 3, SUBJECT, 760027),

    # 5.2 薪火相传有继承
    (760067, "pol_e2_inheritance_start_estate", "继承开始、遗产范围与继承权丧失", 1, SUBJECT, 760028),
    (760068, "pol_e2_statutory_inheritance", "法定继承顺序与遗产分配原则", 2, SUBJECT, 760028),
    (760069, "pol_e2_testate_legacy_agreement", "遗嘱继承、遗赠与遗赠扶养协议", 3, SUBJECT, 760028),

    # 6.1 法律保护下的婚姻
    (760070, "pol_e2_marriage_conditions", "结婚条件与结婚登记", 1, SUBJECT, 760029),
    (760071, "pol_e2_invalid_voidable_marriage", "无效婚姻与可撤销婚姻", 2, SUBJECT, 760029),
    (760072, "pol_e2_divorce_custody_property", "离婚方式及子女抚养、财产分割", 3, SUBJECT, 760029),

    # 6.2 夫妻地位平等
    (760073, "pol_e2_spousal_personal_relation", "夫妻人身关系与地位平等", 1, SUBJECT, 760030),
    (760074, "pol_e2_marital_property", "夫妻共同财产与个人财产", 2, SUBJECT, 760030),
    (760075, "pol_e2_marital_property_agreement", "夫妻约定财产制与共同债务", 3, SUBJECT, 760030),

    # 7.1 立足职场有法宝
    (760076, "pol_e2_labor_law_rights", "劳动法调整对象与劳动者基本权利义务", 1, SUBJECT, 760031),
    (760077, "pol_e2_labor_contract", "劳动合同的订立、必备条款与效力", 2, SUBJECT, 760031),
    (760078, "pol_e2_probation_noncompete", "试用期、服务期与竞业限制", 3, SUBJECT, 760031),

    # 7.2 心中有数上职场
    (760079, "pol_e2_working_time_pay", "工作时间、休息休假与劳动报酬", 1, SUBJECT, 760032),
    (760080, "pol_e2_labor_safety_insurance", "劳动安全卫生、社会保险与女职工特殊保护", 2, SUBJECT, 760032),
    (760081, "pol_e2_labor_termination_dispute", "劳动合同解除、终止与劳动争议解决", 3, SUBJECT, 760032),

    # 8.1 自主创业 公平竞争
    (760082, "pol_e2_business_forms_registration", "创业组织形式与市场主体登记", 1, SUBJECT, 760033),
    (760083, "pol_e2_unfair_competition", "反不正当竞争法禁止的行为", 2, SUBJECT, 760033),
    (760084, "pol_e2_monopoly_review", "垄断行为规制与公平竞争审查", 3, SUBJECT, 760033),

    # 8.2 诚信经营 依法纳税
    (760085, "pol_e2_consumer_product_liability", "消费者权利、经营者义务与产品质量责任", 1, SUBJECT, 760034),
    (760086, "pol_e2_tax_law", "税收特征、主要税种与依法纳税", 2, SUBJECT, 760034),

    # 9.1 认识调解与仲裁
    (760087, "pol_e2_dispute_resolution_mechanisms", "纠纷多元解决机制：和解、调解、仲裁、诉讼", 1, SUBJECT, 760035),
    (760088, "pol_e2_people_mediation", "人民调解与调解协议效力", 2, SUBJECT, 760035),
    (760089, "pol_e2_arbitration", "仲裁协议、仲裁程序与裁决效力", 3, SUBJECT, 760035),

    # 9.2 解析三大诉讼
    (760090, "pol_e2_civil_procedure", "民事诉讼：受案范围、管辖与当事人", 1, SUBJECT, 760036),
    (760091, "pol_e2_administrative_procedure", "行政诉讼：受案范围与被告确定", 2, SUBJECT, 760036),
    (760092, "pol_e2_criminal_procedure", "刑事诉讼：专门机关与基本流程", 3, SUBJECT, 760036),

    # 10.1 正确行使诉讼权利
    (760093, "pol_e2_litigation_rights_duties", "当事人的诉讼权利与诉讼义务", 1, SUBJECT, 760037),
    (760094, "pol_e2_defense_agency_aid", "辩护、代理制度与法律援助", 2, SUBJECT, 760037),

    # 10.2 严格遵守诉讼程序
    (760095, "pol_e2_filing_first_instance", "起诉、受理与第一审程序", 1, SUBJECT, 760038),
    (760096, "pol_e2_appeal_retrial_execution", "第二审、审判监督与执行程序", 2, SUBJECT, 760038),

    # 10.3 依法收集运用证据
    (760097, "pol_e2_evidence_types_burden", "证据种类、证据能力与证明标准", 1, SUBJECT, 760039),
    (760098, "pol_e2_burden_illegal_exclusion", "举证责任分配与非法证据排除", 2, SUBJECT, 760039),
    (760099, "pol_e2_evidence_collection_review", "证据的收集、保全与审查判断", 3, SUBJECT, 760039),
)

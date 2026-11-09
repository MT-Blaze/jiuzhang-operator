"""统编版（2016）初中道德与法治七年级上册：单元课题目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G7 = 7
BOOK_ID = 1313

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版七年级道德与法治上册",
    "jpol_g7a",
    13,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 成长的节拍
    (131301, "第一单元 成长的节拍", "jpol_g7a_u01", 1, BOOK_ID, None),
    (131311, "第一课 中学时代", "jpol_g7a_l01", 1, BOOK_ID, 131301),
    (131312, "第二课 学习新天地", "jpol_g7a_l02", 2, BOOK_ID, 131301),
    (131313, "第三课 发现自己", "jpol_g7a_l03", 3, BOOK_ID, 131301),

    # 第二单元 友谊的天空
    (131302, "第二单元 友谊的天空", "jpol_g7a_u02", 2, BOOK_ID, None),
    (131314, "第四课 友谊与成长同行", "jpol_g7a_l04", 1, BOOK_ID, 131302),
    (131315, "第五课 交友的智慧", "jpol_g7a_l05", 2, BOOK_ID, 131302),

    # 第三单元 师长情谊
    (131303, "第三单元 师长情谊", "jpol_g7a_u03", 3, BOOK_ID, None),
    (131316, "第六课 师生之间", "jpol_g7a_l06", 1, BOOK_ID, 131303),
    (131317, "第七课 亲情之爱", "jpol_g7a_l07", 2, BOOK_ID, 131303),

    # 第四单元 生命的思考
    (131304, "第四单元 生命的思考", "jpol_g7a_u04", 4, BOOK_ID, None),
    (131318, "第八课 探问生命", "jpol_g7a_l08", 1, BOOK_ID, 131304),
    (131319, "第九课 珍视生命", "jpol_g7a_l09", 2, BOOK_ID, 131304),
    (131320, "第十课 绽放生命之花", "jpol_g7a_l10", 3, BOOK_ID, 131304),
)

# id / code / name / sort_order / subject_id / parent_id
# 213001-213011 为册域层，213012-213099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (213001, "jpol_g7a_domain_new_stage", "初中七上·中学时代新起点", 1, SUBJECT, None),
    (213002, "jpol_g7a_domain_study", "初中七上·学习新天地与学习观", 2, SUBJECT, None),
    (213003, "jpol_g7a_domain_self", "初中七上·发现自己与自我认识", 3, SUBJECT, None),
    (213004, "jpol_g7a_domain_friendship", "初中七上·友谊的力量与特质", 4, SUBJECT, None),
    (213005, "jpol_g7a_domain_friend_skill", "初中七上·交友的智慧与友谊维护", 5, SUBJECT, None),
    (213006, "jpol_g7a_domain_teacher", "初中七上·师生之间与教学相长", 6, SUBJECT, None),
    (213007, "jpol_g7a_domain_family", "初中七上·亲情之爱与亲子沟通", 7, SUBJECT, None),
    (213008, "jpol_g7a_domain_life_ask", "初中七上·探问生命与生命特性", 8, SUBJECT, None),
    (213009, "jpol_g7a_domain_life_value", "初中七上·珍视生命与守护生命", 9, SUBJECT, None),
    (213010, "jpol_g7a_domain_resilience", "初中七上·增强生命韧性与挫折应对", 10, SUBJECT, None),
    (213011, "jpol_g7a_domain_life_bloom", "初中七上·绽放生命之花与生命价值", 11, SUBJECT, None),

    # 中学时代新起点
    (213012, "jpol_g7a_point_new_stage_change", "中学生活的新变化与新环境适应", 1, SUBJECT, 213001),
    (213013, "jpol_g7a_point_new_stage_meaning", "中学时代对个人成长的意义与人生新阶段定位", 2, SUBJECT, 213001),
    (213014, "jpol_g7a_point_new_stage_goal", "中学生活的新目标与自我期待的确立", 3, SUBJECT, 213001),
    (213015, "jpol_g7a_point_new_stage_adapt", "适应中学生活的策略与角色转变方法", 4, SUBJECT, 213001),
    (213016, "jpol_g7a_point_new_stage_dream", "编织人生梦想与少年梦想的时代性", 5, SUBJECT, 213001),

    # 学习新天地与学习观
    (213017, "jpol_g7a_point_study_scope", "学习的含义、范围与多样化学习途径", 1, SUBJECT, 213002),
    (213018, "jpol_g7a_point_study_feature", "中学学习的特点与学习方式转变", 2, SUBJECT, 213002),
    (213019, "jpol_g7a_point_study_meaning", "学习对个人成长与发展的意义", 3, SUBJECT, 213002),
    (213020, "jpol_g7a_point_study_bitter_sweet", "学习中的苦与乐及正确对待学习压力", 4, SUBJECT, 213002),
    (213021, "jpol_g7a_point_study_method", "学会学习的方法与终身学习意识", 5, SUBJECT, 213002),

    # 发现自己与自我认识
    (213022, "jpol_g7a_point_self_way", "认识自己的途径：自我观察、他人评价与社会实践", 1, SUBJECT, 213003),
    (213023, "jpol_g7a_point_self_evaluate", "自我评价的方法与客观对待他人评价", 2, SUBJECT, 213003),
    (213024, "jpol_g7a_point_self_accept", "接纳自己的内涵与接纳不完美的自我", 3, SUBJECT, 213003),
    (213025, "jpol_g7a_point_self_appreciate", "欣赏自己的独特与发掘自身优点", 4, SUBJECT, 213003),
    (213026, "jpol_g7a_point_self_better", "做更好的自己：扬长避短与主动改正缺点", 5, SUBJECT, 213003),
    (213027, "jpol_g7a_point_self_potential", "激发自身潜能与理想自我、现实自我的统一", 6, SUBJECT, 213003),

    # 友谊的力量与特质
    (213028, "jpol_g7a_point_friend_meaning", "友谊对个人成长的意义与朋友的影响", 1, SUBJECT, 213004),
    (213029, "jpol_g7a_point_friend_trait", "友谊的特质：亲密、平等双向与心灵相遇", 2, SUBJECT, 213004),
    (213030, "jpol_g7a_point_friend_myth", "澄清友谊误区：功利化、哥们义气与一味索取", 3, SUBJECT, 213004),
    (213031, "jpol_g7a_point_friend_build", "建立友谊的方法：开放自己、主动表达与持续行动", 4, SUBJECT, 213004),
    (213032, "jpol_g7a_point_friend_compete", "朋友间竞争与友谊的辩证关系", 5, SUBJECT, 213004),

    # 交友的智慧与友谊维护
    (213033, "jpol_g7a_point_friend_care", "呵护友谊：用心关怀与尊重对方边界", 1, SUBJECT, 213005),
    (213034, "jpol_g7a_point_friend_conflict", "正确处理朋友间的冲突与矛盾", 2, SUBJECT, 213005),
    (213035, "jpol_g7a_point_friend_self", "友谊中保持独立人格与自我原则", 3, SUBJECT, 213005),
    (213036, "jpol_g7a_point_friend_hurt", "正确对待交友中受到的伤害", 4, SUBJECT, 213005),
    (213037, "jpol_g7a_point_net_friend_trait", "网上交友的特点与虚拟交往的开放性", 5, SUBJECT, 213005),
    (213038, "jpol_g7a_point_net_friend_risk", "网络交友的风险识别与自我保护", 6, SUBJECT, 213005),
    (213039, "jpol_g7a_point_net_friend_real", "网上朋友转化为现实朋友的谨慎态度", 7, SUBJECT, 213005),

    # 师生之间与教学相长
    (213040, "jpol_g7a_point_teacher_role", "教师职业的特点、作用与新时代教师角色", 1, SUBJECT, 213006),
    (213041, "jpol_g7a_point_teacher_relation", "新型师生关系：教学相长与亦师亦友", 2, SUBJECT, 213006),
    (213042, "jpol_g7a_point_teacher_praise", "正确对待老师的表扬与批评", 3, SUBJECT, 213006),
    (213043, "jpol_g7a_point_teacher_communicate", "与老师沟通的方法与技巧", 4, SUBJECT, 213006),
    (213044, "jpol_g7a_point_teacher_respect", "尊重老师与构建和谐师生关系", 5, SUBJECT, 213006),

    # 亲情之爱与亲子沟通
    (213045, "jpol_g7a_point_family_meaning", "家的意义与家庭的功能", 1, SUBJECT, 213007),
    (213046, "jpol_g7a_point_family_love", "亲情的表现形式与孝亲敬长的传统美德", 2, SUBJECT, 213007),
    (213047, "jpol_g7a_point_family_conflict", "亲子冲突的原因、表现与影响", 3, SUBJECT, 213007),
    (213048, "jpol_g7a_point_family_communicate", "与父母沟通的技巧与化解冲突的方法", 4, SUBJECT, 213007),
    (213049, "jpol_g7a_point_family_empathy", "理解父母的爱与换位思考", 5, SUBJECT, 213007),
    (213050, "jpol_g7a_point_family_build", "建设和谐家庭的责任与具体行动", 6, SUBJECT, 213007),

    # 探问生命与生命特性
    (213051, "jpol_g7a_point_life_unique", "生命的独特性与不可逆性", 1, SUBJECT, 213008),
    (213052, "jpol_g7a_point_life_limited", "生命有时尽与生命短暂性的认识", 2, SUBJECT, 213008),
    (213053, "jpol_g7a_point_life_continue", "生命有接续：个体生命与人类生命的延续", 3, SUBJECT, 213008),
    (213054, "jpol_g7a_point_life_awe", "敬畏生命的内涵与尊重关怀他人生命", 4, SUBJECT, 213008),
    (213055, "jpol_g7a_point_life_supreme", "生命至上与珍爱自己及他人生命", 5, SUBJECT, 213008),

    # 珍视生命与守护生命
    (213056, "jpol_g7a_point_life_body", "守护生命首先要关注身体健康", 1, SUBJECT, 213009),
    (213057, "jpol_g7a_point_life_habit", "养成健康生活方式与爱护身体", 2, SUBJECT, 213009),
    (213058, "jpol_g7a_point_life_spirit", "养护精神与丰富精神世界", 3, SUBJECT, 213009),
    (213059, "jpol_g7a_point_life_culture", "中华优秀传统文化对精神养护的意义", 4, SUBJECT, 213009),
    (213060, "jpol_g7a_point_life_safety", "增强安全防范意识与掌握自救自护方法", 5, SUBJECT, 213009),

    # 增强生命韧性与挫折应对
    (213061, "jpol_g7a_point_frustration_define", "挫折的含义与产生原因", 1, SUBJECT, 213010),
    (213062, "jpol_g7a_point_frustration_effect", "挫折的双重影响与正确挫折观", 2, SUBJECT, 213010),
    (213063, "jpol_g7a_point_frustration_face", "面对挫折的情绪调节与理性应对", 3, SUBJECT, 213010),
    (213064, "jpol_g7a_point_resilience", "发掘生命力量与增强生命韧性", 4, SUBJECT, 213010),
    (213065, "jpol_g7a_point_support", "寻求他人支持与建立社会支持系统", 5, SUBJECT, 213010),

    # 绽放生命之花与生命价值
    (213066, "jpol_g7a_point_meaning_explore", "探索生命意义与人生价值", 1, SUBJECT, 213011),
    (213067, "jpol_g7a_point_meaning_ordinary", "在平凡生活中创造生命价值", 2, SUBJECT, 213011),
    (213068, "jpol_g7a_point_meaning_country", "将个人生命与国家社会发展相联系", 3, SUBJECT, 213011),
    (213069, "jpol_g7a_point_meaning_attitude", "活出生命精彩与积极人生态度", 4, SUBJECT, 213011),
    (213070, "jpol_g7a_point_meaning_care", "拒绝冷漠、关切他人生命与传递温暖", 5, SUBJECT, 213011),
)

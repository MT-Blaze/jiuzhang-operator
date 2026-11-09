"""统编版初中道德与法治九年级下册：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G9 = 9
BOOK_ID = 1318

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版九年级道德与法治下册",
    "jpol_g9b",
    18,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 我们共同的世界
    (131801, "第一单元 我们共同的世界", "jpol_g9b_u01", 1, BOOK_ID, None),
    (131811, "第一课 同住地球村", "jpol_g9b_l01", 1, BOOK_ID, 131801),
    (131812, "第二课 构建人类命运共同体", "jpol_g9b_l02", 2, BOOK_ID, 131801),

    # 第二单元 世界舞台上的中国
    (131802, "第二单元 世界舞台上的中国", "jpol_g9b_u02", 2, BOOK_ID, None),
    (131813, "第三课 与世界深度互动", "jpol_g9b_l03", 1, BOOK_ID, 131802),
    (131814, "第四课 与世界共发展", "jpol_g9b_l04", 2, BOOK_ID, 131802),

    # 第三单元 走向未来的少年
    (131803, "第三单元 走向未来的少年", "jpol_g9b_u03", 3, BOOK_ID, None),
    (131815, "第五课 少年的担当", "jpol_g9b_l05", 1, BOOK_ID, 131803),
    (131816, "第六课 我的毕业季", "jpol_g9b_l06", 2, BOOK_ID, 131803),
    (131817, "第七课 从这里出发", "jpol_g9b_l07", 3, BOOK_ID, 131803),
)

# id / code / name / sort_order / subject_id / parent_id
# 218001-218010 为册域层，218011-218084 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (218001, "jpol_g9b_domain_globalization", "初中九下·经济全球化与开放互动", 1, SUBJECT, None),
    (218002, "jpol_g9b_domain_multipolar", "初中九下·世界多极化与国际关系", 2, SUBJECT, None),
    (218003, "jpol_g9b_domain_community", "初中九下·人类命运共同体与全球治理", 3, SUBJECT, None),
    (218004, "jpol_g9b_domain_china_duty", "初中九下·中国担当与国际责任", 4, SUBJECT, None),
    (218005, "jpol_g9b_domain_civilization", "初中九下·文明交流互鉴", 5, SUBJECT, None),
    (218006, "jpol_g9b_domain_opportunity", "初中九下·中国的机遇与挑战", 6, SUBJECT, None),
    (218007, "jpol_g9b_domain_win_win", "初中九下·携手促发展与合作共赢", 7, SUBJECT, None),
    (218008, "jpol_g9b_domain_youth_duty", "初中九下·少年担当与走向世界", 8, SUBJECT, None),
    (218009, "jpol_g9b_domain_career", "初中九下·毕业季与生涯规划", 9, SUBJECT, None),
    (218010, "jpol_g9b_domain_future", "初中九下·回望成长与走向未来", 10, SUBJECT, None),

    # 经济全球化与开放互动
    (218011, "jpol_g9b_point_global_production", "经济全球化的表现：生产、贸易、资本全球化", 1, SUBJECT, 218001),
    (218012, "jpol_g9b_point_global_value_chain", "商品生产在全球范围内完成的分工与协作", 2, SUBJECT, 218001),
    (218013, "jpol_g9b_point_global_trade", "商品贸易在全球范围内进行与生产要素跨境流动", 3, SUBJECT, 218001),
    (218014, "jpol_g9b_point_global_opportunity", "经济全球化带来的发展机遇", 4, SUBJECT, 218001),
    (218015, "jpol_g9b_point_global_risk", "经济全球化带来的风险与挑战", 5, SUBJECT, 218001),
    (218016, "jpol_g9b_point_global_attitude", "面对经济全球化应有的态度与应对策略", 6, SUBJECT, 218001),
    (218017, "jpol_g9b_point_culture_diversity", "文化多样性：各民族文化异彩纷呈", 7, SUBJECT, 218001),
    (218018, "jpol_g9b_point_culture_respect", "正确对待文化差异、尊重文化多样性", 8, SUBJECT, 218001),

    # 世界多极化与国际关系
    (218019, "jpol_g9b_point_multipolar_trend", "世界多极化的表现与发展趋势", 1, SUBJECT, 218002),
    (218020, "jpol_g9b_point_emerging_powers", "新兴市场国家和发展中国家群体性崛起", 2, SUBJECT, 218002),
    (218021, "jpol_g9b_point_multipolar_impact", "世界多极化对国际格局与国际关系的影响", 3, SUBJECT, 218002),
    (218022, "jpol_g9b_point_competition_essence", "国际竞争的实质是以经济和科技实力为基础的综合国力较量", 4, SUBJECT, 218002),
    (218023, "jpol_g9b_point_relation_forms", "国际关系的基本形式：竞争、合作与冲突", 5, SUBJECT, 218002),
    (218024, "jpol_g9b_point_relation_principles", "国家间交往应遵循相互尊重、公平正义、合作共赢原则", 6, SUBJECT, 218002),
    (218025, "jpol_g9b_point_hegemonism", "反对霸权主义、强权政治与冷战思维", 7, SUBJECT, 218002),

    # 人类命运共同体与全球治理
    (218026, "jpol_g9b_point_community_connotation", "人类命运共同体的内涵：建设五个世界", 1, SUBJECT, 218003),
    (218027, "jpol_g9b_point_global_problems", "全球性问题的表现与构建人类命运共同体的必要性", 2, SUBJECT, 218003),
    (218028, "jpol_g9b_point_peace_development", "和平与发展仍是当今时代的主题", 3, SUBJECT, 218003),
    (218029, "jpol_g9b_point_peace_threats", "威胁世界和平与发展的主要因素", 4, SUBJECT, 218003),
    (218030, "jpol_g9b_point_peace_ways", "维护世界和平、促进共同发展的途径", 5, SUBJECT, 218003),
    (218031, "jpol_g9b_point_global_governance", "全球治理体系变革与共商共建共享原则", 6, SUBJECT, 218003),
    (218032, "jpol_g9b_point_community_significance", "中国首倡人类命运共同体理念的世界意义", 7, SUBJECT, 218003),

    # 中国担当与国际责任
    (218033, "jpol_g9b_point_china_responsibility", "中国在国际事务中积极主动的责任担当", 1, SUBJECT, 218004),
    (218034, "jpol_g9b_point_china_governance", "中国参与全球治理体系改革和建设的主张", 2, SUBJECT, 218004),
    (218035, "jpol_g9b_point_china_poverty", "中国为全球减贫与发展事业作出的贡献", 3, SUBJECT, 218004),
    (218036, "jpol_g9b_point_china_climate", "中国应对气候变化的承诺与行动", 4, SUBJECT, 218004),
    (218037, "jpol_g9b_point_china_peacekeeping", "中国在国际维和与人道主义救援中的作为", 5, SUBJECT, 218004),
    (218038, "jpol_g9b_point_china_limit", "中国担当的底线：量力而行、尽力而为", 6, SUBJECT, 218004),
    (218039, "jpol_g9b_point_china_open", "中国坚持对外开放、与世界共享发展机遇", 7, SUBJECT, 218004),

    # 文明交流互鉴
    (218040, "jpol_g9b_point_civilization_exchange", "文明因多样而交流、因交流而互鉴", 1, SUBJECT, 218005),
    (218041, "jpol_g9b_point_civilization_learn", "学习借鉴人类文明的一切优秀成果", 2, SUBJECT, 218005),
    (218042, "jpol_g9b_point_civilization_confidence", "在交流互鉴中增强文化自信", 3, SUBJECT, 218005),
    (218043, "jpol_g9b_point_civilization_principle", "以我为主、兼收并蓄的交流原则", 4, SUBJECT, 218005),
    (218044, "jpol_g9b_point_culture_going_out", "推动中华文化走向世界的意义与路径", 5, SUBJECT, 218005),
    (218045, "jpol_g9b_point_civilization_barrier", "尊重差异、包容多样，消除文明隔阂", 6, SUBJECT, 218005),
    (218046, "jpol_g9b_point_civilization_dialogue", "开展文明对话、促进民心相通", 7, SUBJECT, 218005),

    # 中国的机遇与挑战
    (218047, "jpol_g9b_point_strategic_period", "我国发展仍处于重要战略机遇期", 1, SUBJECT, 218006),
    (218048, "jpol_g9b_point_china_advantages", "我国经济社会发展积累的成就与优势", 2, SUBJECT, 218006),
    (218049, "jpol_g9b_point_internal_challenge", "中国发展面临的内部挑战", 3, SUBJECT, 218006),
    (218050, "jpol_g9b_point_external_challenge", "中国发展面临的外部风险与挑战", 4, SUBJECT, 218006),
    (218051, "jpol_g9b_point_dialectical", "辩证看待机遇与挑战：危中有机、化危为机", 5, SUBJECT, 218006),
    (218052, "jpol_g9b_point_seize_opportunity", "抓住机遇、迎接挑战的实践要求", 6, SUBJECT, 218006),
    (218053, "jpol_g9b_point_transformation", "转变发展方式、优化经济结构的紧迫性", 7, SUBJECT, 218006),
    (218054, "jpol_g9b_point_risk_awareness", "增强风险意识与树立底线思维", 8, SUBJECT, 218006),

    # 携手促发展与合作共赢
    (218055, "jpol_g9b_point_new_pattern", "构建新发展格局与推动高质量发展", 1, SUBJECT, 218007),
    (218056, "jpol_g9b_point_new_opportunity", "以中国新发展为世界提供新机遇", 2, SUBJECT, 218007),
    (218057, "jpol_g9b_point_belt_road", "共建“一带一路”的实践与成果", 3, SUBJECT, 218007),
    (218058, "jpol_g9b_point_mutual_benefit", "坚持互利共赢的开放战略", 4, SUBJECT, 218007),
    (218059, "jpol_g9b_point_two_way_opening", "坚持引进来和走出去并重", 5, SUBJECT, 218007),
    (218060, "jpol_g9b_point_open_economy", "推动建设开放型世界经济", 6, SUBJECT, 218007),
    (218061, "jpol_g9b_point_against_unilateral", "反对单边主义与贸易保护主义", 7, SUBJECT, 218007),

    # 少年担当与走向世界
    (218062, "jpol_g9b_point_world_stage", "走向世界大舞台：个人与世界的关系", 1, SUBJECT, 218008),
    (218063, "jpol_g9b_point_youth_image", "在对外交往中展现中国青少年的风采", 2, SUBJECT, 218008),
    (218064, "jpol_g9b_point_youth_fate", "个人命运与国家命运、世界命运紧密相连", 3, SUBJECT, 218008),
    (218065, "jpol_g9b_point_youth_nation", "青年兴则国家兴，青年强则国家强", 4, SUBJECT, 218008),
    (218066, "jpol_g9b_point_youth_ideal", "树立远大理想、担当时代责任", 5, SUBJECT, 218008),
    (218067, "jpol_g9b_point_youth_ability", "锤炼品德修为、练就过硬本领", 6, SUBJECT, 218008),
    (218068, "jpol_g9b_point_global_view", "增强全球视野与人类命运共同体意识", 7, SUBJECT, 218008),

    # 毕业季与生涯规划
    (218069, "jpol_g9b_point_lifelong_study", "学无止境：学习是终身的过程", 1, SUBJECT, 218009),
    (218070, "jpol_g9b_point_learning_habit", "树立终身学习理念、养成主动学习习惯", 2, SUBJECT, 218009),
    (218071, "jpol_g9b_point_study_pressure", "九年级学习压力的来源与缓解方式", 3, SUBJECT, 218009),
    (218072, "jpol_g9b_point_learning_method", "改进学习方式、提升学习能力", 4, SUBJECT, 218009),
    (218073, "jpol_g9b_point_career_meaning", "职业的含义与影响职业选择的因素", 5, SUBJECT, 218009),
    (218074, "jpol_g9b_point_career_view", "树立正确的职业观与择业观", 6, SUBJECT, 218009),
    (218075, "jpol_g9b_point_career_plan", "职业生涯规划的基本步骤", 7, SUBJECT, 218009),
    (218076, "jpol_g9b_point_dedication", "敬业精神与劳动创造价值", 8, SUBJECT, 218009),
    (218077, "jpol_g9b_point_choice_plan", "升学与就业两种去向的合理规划", 9, SUBJECT, 218009),

    # 回望成长与走向未来
    (218078, "jpol_g9b_point_growth_review", "回望初中三年的成长与收获", 1, SUBJECT, 218010),
    (218079, "jpol_g9b_point_self_accept", "正确认识自我、接纳自我", 2, SUBJECT, 218010),
    (218080, "jpol_g9b_point_gratitude", "感恩师长、感恩集体与社会", 3, SUBJECT, 218010),
    (218081, "jpol_g9b_point_new_start", "初中毕业是人生新的起点", 4, SUBJECT, 218010),
    (218082, "jpol_g9b_point_future_choice", "面向未来的人生选择与责任", 5, SUBJECT, 218010),
    (218083, "jpol_g9b_point_dream_unity", "个人梦与中国梦的统一", 6, SUBJECT, 218010),
    (218084, "jpol_g9b_point_struggle", "在奋斗中创造精彩人生", 7, SUBJECT, 218010),
)

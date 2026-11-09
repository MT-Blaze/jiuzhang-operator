"""统编版（2019）高中思想政治必修第三册（政治与法治）：课框目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G10 = 10
BOOK_ID = 7103

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中思想政治必修第三册（政治与法治）",
    "pol_r3",
    3,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (730101, "第一单元 中国共产党的领导", "pol_r3_u01", 1, BOOK_ID, None),
    (730102, "第二单元 人民当家作主", "pol_r3_u02", 2, BOOK_ID, None),
    (730103, "第三单元 全面依法治国", "pol_r3_u03", 3, BOOK_ID, None),
    (730111, "第一课 历史和人民的选择", "pol_r3_l01", 1, BOOK_ID, 730101),
    (730112, "第二课 中国共产党的先进性", "pol_r3_l02", 2, BOOK_ID, 730101),
    (730113, "第三课 坚持和加强党的全面领导", "pol_r3_l03", 3, BOOK_ID, 730101),
    (730114, "第四课 人民民主专政的社会主义国家", "pol_r3_l04", 1, BOOK_ID, 730102),
    (730115, "第五课 我国的根本政治制度", "pol_r3_l05", 2, BOOK_ID, 730102),
    (730116, "第六课 我国的基本政治制度", "pol_r3_l06", 3, BOOK_ID, 730102),
    (730117, "第七课 治国理政的基本方式", "pol_r3_l07", 1, BOOK_ID, 730103),
    (730118, "第八课 法治中国建设", "pol_r3_l08", 2, BOOK_ID, 730103),
    (730119, "第九课 全面推进依法治国的基本要求", "pol_r3_l09", 3, BOOK_ID, 730103),
    (730121, "第一框 中华人民共和国成立前各种政治力量", "pol_r3_l01_s01", 1, BOOK_ID, 730111),
    (730122, "第二框 中国共产党领导人民站起来、富起来、强起来", "pol_r3_l01_s02", 2, BOOK_ID, 730111),
    (730123, "第一框 始终坚持以人民为中心", "pol_r3_l02_s01", 1, BOOK_ID, 730112),
    (730124, "第二框 始终走在时代前列", "pol_r3_l02_s02", 2, BOOK_ID, 730112),
    (730125, "第一框 坚持党的领导", "pol_r3_l03_s01", 1, BOOK_ID, 730113),
    (730126, "第二框 巩固党的执政地位", "pol_r3_l03_s02", 2, BOOK_ID, 730113),
    (730127, "第一框 人民民主专政的本质：人民当家作主", "pol_r3_l04_s01", 1, BOOK_ID, 730114),
    (730128, "第二框 坚持人民民主专政", "pol_r3_l04_s02", 2, BOOK_ID, 730114),
    (730129, "第一框 人民代表大会：我国的国家权力机关", "pol_r3_l05_s01", 1, BOOK_ID, 730115),
    (730130, "第二框 人民代表大会制度：我国的根本政治制度", "pol_r3_l05_s02", 2, BOOK_ID, 730115),
    (730131, "第一框 中国共产党领导的多党合作和政治协商制度", "pol_r3_l06_s01", 1, BOOK_ID, 730116),
    (730132, "第二框 民族区域自治制度", "pol_r3_l06_s02", 2, BOOK_ID, 730116),
    (730133, "第三框 基层群众自治制度", "pol_r3_l06_s03", 3, BOOK_ID, 730116),
    (730134, "第一框 我国法治建设的历程", "pol_r3_l07_s01", 1, BOOK_ID, 730117),
    (730135, "第二框 全面推进依法治国的总目标与原则", "pol_r3_l07_s02", 2, BOOK_ID, 730117),
    (730136, "第一框 法治国家", "pol_r3_l08_s01", 1, BOOK_ID, 730118),
    (730137, "第二框 法治政府", "pol_r3_l08_s02", 2, BOOK_ID, 730118),
    (730138, "第三框 法治社会", "pol_r3_l08_s03", 3, BOOK_ID, 730118),
    (730139, "第一框 科学立法", "pol_r3_l09_s01", 1, BOOK_ID, 730119),
    (730140, "第二框 严格执法", "pol_r3_l09_s02", 2, BOOK_ID, 730119),
    (730141, "第三框 公正司法", "pol_r3_l09_s03", 3, BOOK_ID, 730119),
    (730142, "第四框 全民守法", "pol_r3_l09_s04", 4, BOOK_ID, 730119),
)

# id / code / name / sort_order / subject_id / parent_id
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (730001, "pol_r3_domain_party_leadership", "中国共产党的领导：历史选择与执政优势", 1, SUBJECT, None),
    (730002, "pol_r3_domain_people_sovereignty", "人民当家作主：国家性质与政治制度", 2, SUBJECT, None),
    (730003, "pol_r3_domain_law_based_governance", "全面依法治国：法治体系与法治中国", 3, SUBJECT, None),

    # 单元域层
    (730004, "pol_r3_unit01", "第一单元 中国共产党的领导", 1, SUBJECT, 730001),
    (730005, "pol_r3_unit02", "第二单元 人民当家作主", 1, SUBJECT, 730002),
    (730006, "pol_r3_unit03", "第三单元 全面依法治国", 1, SUBJECT, 730003),

    # 课域层
    (730007, "pol_r3_lesson01", "第一课 历史和人民的选择", 1, SUBJECT, 730004),
    (730008, "pol_r3_lesson02", "第二课 中国共产党的先进性", 2, SUBJECT, 730004),
    (730009, "pol_r3_lesson03", "第三课 坚持和加强党的全面领导", 3, SUBJECT, 730004),
    (730010, "pol_r3_lesson04", "第四课 人民民主专政的社会主义国家", 1, SUBJECT, 730005),
    (730011, "pol_r3_lesson05", "第五课 我国的根本政治制度", 2, SUBJECT, 730005),
    (730012, "pol_r3_lesson06", "第六课 我国的基本政治制度", 3, SUBJECT, 730005),
    (730013, "pol_r3_lesson07", "第七课 治国理政的基本方式", 1, SUBJECT, 730006),
    (730014, "pol_r3_lesson08", "第八课 法治中国建设", 2, SUBJECT, 730006),
    (730015, "pol_r3_lesson09", "第九课 全面推进依法治国的基本要求", 3, SUBJECT, 730006),

    # 框域层
    (730016, "pol_r3_sec_pre_founding_forces", "第一框 中华人民共和国成立前各种政治力量", 1, SUBJECT, 730007),
    (730017, "pol_r3_sec_party_leads_three_leaps", "第二框 中国共产党领导人民站起来、富起来、强起来", 2, SUBJECT, 730007),
    (730018, "pol_r3_sec_people_centered", "第一框 始终坚持以人民为中心", 1, SUBJECT, 730008),
    (730019, "pol_r3_sec_advance_with_times", "第二框 始终走在时代前列", 2, SUBJECT, 730008),
    (730020, "pol_r3_sec_uphold_party_leadership", "第一框 坚持党的领导", 1, SUBJECT, 730009),
    (730021, "pol_r3_sec_consolidate_governing", "第二框 巩固党的执政地位", 2, SUBJECT, 730009),
    (730022, "pol_r3_sec_people_democracy_essence", "第一框 人民民主专政的本质：人民当家作主", 1, SUBJECT, 730010),
    (730023, "pol_r3_sec_uphold_dictatorship", "第二框 坚持人民民主专政", 2, SUBJECT, 730010),
    (730024, "pol_r3_sec_npc_power_organ", "第一框 人民代表大会：我国的国家权力机关", 1, SUBJECT, 730011),
    (730025, "pol_r3_sec_npc_system", "第二框 人民代表大会制度：我国的根本政治制度", 2, SUBJECT, 730011),
    (730026, "pol_r3_sec_multiparty_cppcc", "第一框 中国共产党领导的多党合作和政治协商制度", 1, SUBJECT, 730012),
    (730027, "pol_r3_sec_ethnic_autonomy", "第二框 民族区域自治制度", 2, SUBJECT, 730012),
    (730028, "pol_r3_sec_grassroots_autonomy", "第三框 基层群众自治制度", 3, SUBJECT, 730012),
    (730029, "pol_r3_sec_law_building_course", "第一框 我国法治建设的历程", 1, SUBJECT, 730013),
    (730030, "pol_r3_sec_general_goal_principles", "第二框 全面推进依法治国的总目标与原则", 2, SUBJECT, 730013),
    (730031, "pol_r3_sec_law_state", "第一框 法治国家", 1, SUBJECT, 730014),
    (730032, "pol_r3_sec_law_government", "第二框 法治政府", 2, SUBJECT, 730014),
    (730033, "pol_r3_sec_law_society", "第三框 法治社会", 3, SUBJECT, 730014),
    (730034, "pol_r3_sec_scientific_legislation", "第一框 科学立法", 1, SUBJECT, 730015),
    (730035, "pol_r3_sec_strict_enforcement", "第二框 严格执法", 2, SUBJECT, 730015),
    (730036, "pol_r3_sec_impartial_justice", "第三框 公正司法", 3, SUBJECT, 730015),
    (730037, "pol_r3_sec_universal_law_abiding", "第四框 全民守法", 4, SUBJECT, 730015),

    # 1.1 中华人民共和国成立前各种政治力量
    (730038, "pol_r3_modern_national_conditions", "近代中国的基本国情与半殖民地半封建社会性质", 1, SUBJECT, 730016),
    (730039, "pol_r3_two_historical_tasks", "近代中国两大历史任务及其相互关系", 2, SUBJECT, 730016),
    (730040, "pol_r3_other_forces_attempts", "农民阶级、地主阶级与资产阶级各派救国方案的探索及局限", 3, SUBJECT, 730016),

    # 1.2 中国共产党领导人民站起来、富起来、强起来
    (730041, "pol_r3_cpc_founding", "中国共产党的诞生条件与伟大建党精神", 1, SUBJECT, 730017),
    (730042, "pol_r3_new_democratic_victory", "党领导新民主主义革命胜利与新中国成立", 2, SUBJECT, 730017),
    (730043, "pol_r3_three_great_leaps", "社会主义革命、建设、改革开放与新时代的伟大飞跃", 3, SUBJECT, 730017),

    # 2.1 始终坚持以人民为中心
    (730044, "pol_r3_party_nature_purpose", "中国共产党的性质、根本宗旨与初心使命", 1, SUBJECT, 730018),
    (730045, "pol_r3_governing_philosophy", "党的执政理念：立党为公、执政为民", 2, SUBJECT, 730018),
    (730046, "pol_r3_mass_line", "党的群众路线与保持党同人民群众的血肉联系", 3, SUBJECT, 730018),

    # 2.2 始终走在时代前列
    (730047, "pol_r3_guiding_theory_advance", "党的指导思想与时俱进及其理论体系", 1, SUBJECT, 730019),
    (730048, "pol_r3_ideological_line", "解放思想、实事求是、与时俱进、求真务实", 2, SUBJECT, 730019),
    (730049, "pol_r3_pioneer_role_self_reform", "共产党员的先锋模范作用与党的自我革命", 3, SUBJECT, 730019),

    # 3.1 坚持党的领导
    (730050, "pol_r3_party_leadership_essence", "党的领导是中国特色社会主义最本质的特征", 1, SUBJECT, 730020),
    (730051, "pol_r3_three_leaderships", "党的政治领导、思想领导与组织领导", 2, SUBJECT, 730020),
    (730052, "pol_r3_overall_leadership", "坚持党对一切工作的领导与做到“两个维护”", 3, SUBJECT, 730020),

    # 3.2 巩固党的执政地位
    (730053, "pol_r3_three_governing_ways", "科学执政、民主执政、依法执政的内涵与关系", 1, SUBJECT, 730021),
    (730054, "pol_r3_full_strict_governance", "全面从严治党与新时代党的建设总要求", 2, SUBJECT, 730021),
    (730055, "pol_r3_governing_capacity", "提高党的执政能力和领导水平", 3, SUBJECT, 730021),

    # 4.1 人民民主专政的本质：人民当家作主
    (730056, "pol_r3_state_nature", "我国的国家性质与人民民主专政的国体", 1, SUBJECT, 730022),
    (730057, "pol_r3_whole_process_democracy", "全过程人民民主的内涵、环节与显著优势", 2, SUBJECT, 730022),
    (730058, "pol_r3_democracy_features", "我国人民民主的广泛性、真实性与管用性", 3, SUBJECT, 730022),

    # 4.2 坚持人民民主专政
    (730059, "pol_r3_persist_dictatorship", "坚持人民民主专政的必要性", 1, SUBJECT, 730023),
    (730060, "pol_r3_state_functions", "国家政权的对内对外职能与专政职能", 2, SUBJECT, 730023),

    # 5.1 人民代表大会：我国的国家权力机关
    (730061, "pol_r3_npc_status_powers", "全国人民代表大会的性质、地位与职权", 1, SUBJECT, 730024),
    (730062, "pol_r3_npc_standing_committee", "全国人大常委会的性质与职权", 2, SUBJECT, 730024),
    (730063, "pol_r3_deputies", "人大代表的产生方式、权利与义务", 3, SUBJECT, 730024),

    # 5.2 人民代表大会制度：我国的根本政治制度
    (730064, "pol_r3_democratic_centralism", "人民代表大会制度的组织和活动原则：民主集中制", 1, SUBJECT, 730025),
    (730065, "pol_r3_npc_system_content", "人民代表大会制度的基本内容与制度优势", 2, SUBJECT, 730025),
    (730066, "pol_r3_improve_npc_system", "坚持和完善人民代表大会制度的要求", 3, SUBJECT, 730025),

    # 6.1 中国共产党领导的多党合作和政治协商制度
    (730067, "pol_r3_new_party_system", "我国新型政党制度的基本方针与政党关系", 1, SUBJECT, 730026),
    (730068, "pol_r3_cppcc", "人民政协的性质、主题与三大职能", 2, SUBJECT, 730026),
    (730069, "pol_r3_consultative_democracy", "社会主义协商民主的渠道体系与独特优势", 3, SUBJECT, 730026),

    # 6.2 民族区域自治制度
    (730070, "pol_r3_ethnic_relations", "我国新型民族关系与民族区域自治制度的地位", 1, SUBJECT, 730027),
    (730071, "pol_r3_ethnic_autonomy_content", "民族区域自治制度的内容、自治地方与自治机关", 2, SUBJECT, 730027),
    (730072, "pol_r3_improve_ethnic_autonomy", "坚持和完善民族区域自治制度的要求", 3, SUBJECT, 730027),

    # 6.3 基层群众自治制度
    (730073, "pol_r3_grassroots_autonomy", "基层群众自治制度的地位与组织形式", 1, SUBJECT, 730028),
    (730074, "pol_r3_villager_resident_autonomy", "村民自治与城市居民自治的主要内容", 2, SUBJECT, 730028),
    (730075, "pol_r3_grassroots_democracy", "发展基层民主、扩大公民有序政治参与的意义", 3, SUBJECT, 730028),

    # 7.1 我国法治建设的历程
    (730076, "pol_r3_legal_tradition", "中华法系的传统与近代中国法治的探索", 1, SUBJECT, 730029),
    (730077, "pol_r3_new_china_rule_of_law", "新中国法治建设的历程与中国特色社会主义法律体系", 2, SUBJECT, 730029),
    (730078, "pol_r3_law_based_governance", "全面依法治国的提出与习近平法治思想", 3, SUBJECT, 730029),

    # 7.2 全面推进依法治国的总目标与原则
    (730079, "pol_r3_general_goal", "全面推进依法治国的总目标与工作布局", 1, SUBJECT, 730030),
    (730080, "pol_r3_legal_system", "建设中国特色社会主义法治体系的内容", 2, SUBJECT, 730030),
    (730081, "pol_r3_basic_principles", "全面推进依法治国的基本原则", 3, SUBJECT, 730030),

    # 8.1 法治国家
    (730082, "pol_r3_rule_of_law_state", "法治国家的内涵与基本特征", 1, SUBJECT, 730031),
    (730083, "pol_r3_build_law_state", "建设法治国家的具体任务与意义", 2, SUBJECT, 730031),

    # 8.2 法治政府
    (730084, "pol_r3_rule_of_law_government", "法治政府的内涵、特征与基本要求", 1, SUBJECT, 730032),
    (730085, "pol_r3_law_based_administration", "依法行政与政府职能的法定化", 2, SUBJECT, 730032),
    (730086, "pol_r3_build_law_government", "建设法治政府的措施与意义", 3, SUBJECT, 730032),

    # 8.3 法治社会
    (730087, "pol_r3_rule_of_law_society", "法治社会的内涵与基本特征", 1, SUBJECT, 730033),
    (730088, "pol_r3_integrated_law_building", "法治国家、法治政府、法治社会一体建设", 2, SUBJECT, 730033),

    # 9.1 科学立法
    (730089, "pol_r3_scientific_legislation", "科学立法的内涵、原则与要求", 1, SUBJECT, 730034),
    (730090, "pol_r3_legislative_system", "我国的立法体制与立法程序", 2, SUBJECT, 730034),
    (730091, "pol_r3_legislation_quality", "提高立法质量、以良法促进发展保障善治", 3, SUBJECT, 730034),

    # 9.2 严格执法
    (730092, "pol_r3_strict_enforcement", "严格执法的内涵、主体与基本要求", 1, SUBJECT, 730035),
    (730093, "pol_r3_enforcement_reform", "深化行政执法体制改革与规范公正文明执法", 2, SUBJECT, 730035),
    (730094, "pol_r3_enforcement_significance", "严格执法对建设法治政府与维护法律权威的意义", 3, SUBJECT, 730035),

    # 9.3 公正司法
    (730095, "pol_r3_judicial_fairness", "公正司法的内涵、地位与基本要求", 1, SUBJECT, 730036),
    (730096, "pol_r3_judicial_reform", "司法体制改革、司法责任制与司法公开", 2, SUBJECT, 730036),
    (730097, "pol_r3_judicial_guarantee", "保障司法公正、维护社会公平正义的制度安排", 3, SUBJECT, 730036),

    # 9.4 全民守法
    (730098, "pol_r3_law_abiding", "全民守法的内涵、要求与主体范围", 1, SUBJECT, 730037),
    (730099, "pol_r3_legal_culture", "增强全民法治观念、培育法治文化与建设法治社会", 2, SUBJECT, 730037),
)

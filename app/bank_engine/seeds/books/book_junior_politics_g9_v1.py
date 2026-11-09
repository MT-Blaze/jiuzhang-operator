"""统编版初中道德与法治九年级上册：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 7
G9 = 9
BOOK_ID = 1317

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版九年级道德与法治上册",
    "jpol_g9a",
    17,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 富强与创新
    (131701, "第一单元 富强与创新", "jpol_g9a_u01", 1, BOOK_ID, None),
    (131711, "第一课 踏上强国之路", "jpol_g9a_l01", 1, BOOK_ID, 131701),
    (131712, "第二课 创新驱动发展", "jpol_g9a_l02", 2, BOOK_ID, 131701),

    # 第二单元 民主与法治
    (131702, "第二单元 民主与法治", "jpol_g9a_u02", 2, BOOK_ID, None),
    (131713, "第三课 追求民主价值", "jpol_g9a_l03", 1, BOOK_ID, 131702),
    (131714, "第四课 建设法治中国", "jpol_g9a_l04", 2, BOOK_ID, 131702),

    # 第三单元 文明与家园
    (131703, "第三单元 文明与家园", "jpol_g9a_u03", 3, BOOK_ID, None),
    (131715, "第五课 守望精神家园", "jpol_g9a_l05", 1, BOOK_ID, 131703),
    (131716, "第六课 建设美丽中国", "jpol_g9a_l06", 2, BOOK_ID, 131703),

    # 第四单元 和谐与梦想
    (131704, "第四单元 和谐与梦想", "jpol_g9a_u04", 4, BOOK_ID, None),
    (131717, "第七课 中华一家亲", "jpol_g9a_l07", 1, BOOK_ID, 131704),
    (131718, "第八课 中国人 中国梦", "jpol_g9a_l08", 2, BOOK_ID, 131704),
)

# id / code / name / sort_order / subject_id / parent_id
# 217001-217008 为册域层，217009-217065 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (217001, "jpol_g9a_domain_reform", "初中九上·改革开放与共同富裕", 1, SUBJECT, None),
    (217002, "jpol_g9a_domain_innovation", "初中九上·创新驱动发展战略", 2, SUBJECT, None),
    (217003, "jpol_g9a_domain_democracy", "初中九上·社会主义新型民主", 3, SUBJECT, None),
    (217004, "jpol_g9a_domain_rule_law", "初中九上·全面依法治国", 4, SUBJECT, None),
    (217005, "jpol_g9a_domain_culture", "初中九上·中华文化与民族精神", 5, SUBJECT, None),
    (217006, "jpol_g9a_domain_ecology", "初中九上·生态文明与美丽中国", 6, SUBJECT, None),
    (217007, "jpol_g9a_domain_unity", "初中九上·民族团结与祖国统一", 7, SUBJECT, None),
    (217008, "jpol_g9a_domain_china_dream", "初中九上·中国梦与自信中国人", 8, SUBJECT, None),

    # 改革开放与共同富裕
    (217009, "jpol_g9a_point_reform_status", "改革开放是决定当代中国命运的关键一招", 1, SUBJECT, 217001),
    (217010, "jpol_g9a_point_reform_achievement", "改革开放以来我国经济社会发展的巨大成就", 2, SUBJECT, 217001),
    (217011, "jpol_g9a_point_reform_road", "改革开放是强国之路、富民之路", 3, SUBJECT, 217001),
    (217012, "jpol_g9a_point_reform_deepen", "全面深化改革的总目标与重点领域", 4, SUBJECT, 217001),
    (217013, "jpol_g9a_point_people_center", "以人民为中心的发展思想", 5, SUBJECT, 217001),
    (217014, "jpol_g9a_point_common_prosperity", "共同富裕是社会主义的本质要求", 6, SUBJECT, 217001),
    (217015, "jpol_g9a_point_coordination", "城乡区域协调发展与乡村振兴战略", 7, SUBJECT, 217001),
    (217016, "jpol_g9a_point_livelihood", "保障和改善民生的举措及其意义", 8, SUBJECT, 217001),

    # 创新驱动发展战略
    (217017, "jpol_g9a_point_innovation_define", "创新的内涵：知识创新、技术创新与制度创新", 1, SUBJECT, 217002),
    (217018, "jpol_g9a_point_innovation_life", "创新对个人生活与社会发展的影响", 2, SUBJECT, 217002),
    (217019, "jpol_g9a_point_innovation_drive", "创新是引领发展的第一动力", 3, SUBJECT, 217002),
    (217020, "jpol_g9a_point_innovation_gap", "我国科技创新的成就与关键核心技术短板", 4, SUBJECT, 217002),
    (217021, "jpol_g9a_point_innovation_strategy", "科教兴国、人才强国与创新驱动发展战略", 5, SUBJECT, 217002),
    (217022, "jpol_g9a_point_education", "教育是民族振兴、社会进步的基石", 6, SUBJECT, 217002),
    (217023, "jpol_g9a_point_innovation_spirit", "弘扬创新精神与保护知识产权", 7, SUBJECT, 217002),

    # 社会主义新型民主
    (217024, "jpol_g9a_point_democracy_essence", "民主的价值内涵与我国民主的本质", 1, SUBJECT, 217003),
    (217025, "jpol_g9a_point_democracy_new", "我国社会主义民主是新型的民主", 2, SUBJECT, 217003),
    (217026, "jpol_g9a_point_democracy_whole_process", "全过程人民民主的特点与优势", 3, SUBJECT, 217003),
    (217027, "jpol_g9a_point_democracy_forms", "选举民主与协商民主两种重要形式", 4, SUBJECT, 217003),
    (217028, "jpol_g9a_point_democracy_channels", "公民参与民主生活的主要途径", 5, SUBJECT, 217003),
    (217029, "jpol_g9a_point_democracy_practice", "民主选举、民主决策、民主管理、民主监督", 6, SUBJECT, 217003),
    (217030, "jpol_g9a_point_democracy_awareness", "增强民主意识与依法有序参与", 7, SUBJECT, 217003),

    # 全面依法治国
    (217031, "jpol_g9a_point_law_meaning", "法治的意义：良法之治与善治", 1, SUBJECT, 217004),
    (217032, "jpol_g9a_point_law_goal", "全面依法治国的总目标", 2, SUBJECT, 217004),
    (217033, "jpol_g9a_point_law_requirements", "科学立法、严格执法、公正司法、全民守法", 3, SUBJECT, 217004),
    (217034, "jpol_g9a_point_law_government", "法治政府建设与依法行政", 4, SUBJECT, 217004),
    (217035, "jpol_g9a_point_law_citizen", "厉行法治对公民行为的要求", 5, SUBJECT, 217004),
    (217036, "jpol_g9a_point_law_morality", "法治与德治相结合", 6, SUBJECT, 217004),
    (217037, "jpol_g9a_point_law_youth", "青少年尊法学法守法用法的实践", 7, SUBJECT, 217004),

    # 中华文化与民族精神
    (217038, "jpol_g9a_point_culture_feature", "中华文化源远流长、博大精深的特点", 1, SUBJECT, 217005),
    (217039, "jpol_g9a_point_culture_value", "中华优秀传统文化的价值与文化自信", 2, SUBJECT, 217005),
    (217040, "jpol_g9a_point_culture_virtue", "中华传统美德的地位与主要内容", 3, SUBJECT, 217005),
    (217041, "jpol_g9a_point_spirit_content", "中华民族精神的内涵与核心", 4, SUBJECT, 217005),
    (217042, "jpol_g9a_point_spirit_period", "民族精神在不同历史时期的具体表现", 5, SUBJECT, 217005),
    (217043, "jpol_g9a_point_spirit_promote", "弘扬民族精神与践行社会主义核心价值观", 6, SUBJECT, 217005),
    (217044, "jpol_g9a_point_culture_inherit", "传承文化基因、坚定文化自信的实践要求", 7, SUBJECT, 217005),

    # 生态文明与美丽中国
    (217045, "jpol_g9a_point_population", "我国人口现状与生育政策的调整", 1, SUBJECT, 217006),
    (217046, "jpol_g9a_point_resource", "我国资源环境形势的严峻性", 2, SUBJECT, 217006),
    (217047, "jpol_g9a_point_sustainable", "可持续发展战略与绿色发展理念", 3, SUBJECT, 217006),
    (217048, "jpol_g9a_point_harmony", "人与自然和谐共生的理念", 4, SUBJECT, 217006),
    (217049, "jpol_g9a_point_green_gold", "绿水青山就是金山银山", 5, SUBJECT, 217006),
    (217050, "jpol_g9a_point_conservation", "节约资源和保护环境的基本国策", 6, SUBJECT, 217006),
    (217051, "jpol_g9a_point_low_carbon", "践行绿色低碳生活方式", 7, SUBJECT, 217006),

    # 民族团结与祖国统一
    (217052, "jpol_g9a_point_multi_ethnic", "我国是统一的多民族国家", 1, SUBJECT, 217007),
    (217053, "jpol_g9a_point_autonomy", "民族区域自治制度与民族团结", 2, SUBJECT, 217007),
    (217054, "jpol_g9a_point_ethnic_principle", "民族平等、民族团结、各民族共同繁荣", 3, SUBJECT, 217007),
    (217055, "jpol_g9a_point_community", "铸牢中华民族共同体意识", 4, SUBJECT, 217007),
    (217056, "jpol_g9a_point_reunification", "维护国家统一与“一国两制”方针", 5, SUBJECT, 217007),
    (217057, "jpol_g9a_point_against_split", "反对分裂、维护国家主权和领土完整", 6, SUBJECT, 217007),
    (217058, "jpol_g9a_point_taiwan", "解决台湾问题的基本方针与两岸关系", 7, SUBJECT, 217007),

    # 中国梦与自信中国人
    (217059, "jpol_g9a_point_two_centenary", "“两个一百年”奋斗目标与战略安排", 1, SUBJECT, 217008),
    (217060, "jpol_g9a_point_dream_essence", "中国梦的本质：国家富强、民族振兴、人民幸福", 2, SUBJECT, 217008),
    (217061, "jpol_g9a_point_modernization", "全面建成社会主义现代化强国的战略安排", 3, SUBJECT, 217008),
    (217062, "jpol_g9a_point_china_road", "实现中国梦必须走中国道路", 4, SUBJECT, 217008),
    (217063, "jpol_g9a_point_china_spirit", "实现中国梦必须弘扬中国精神", 5, SUBJECT, 217008),
    (217064, "jpol_g9a_point_china_strength", "实现中国梦必须凝聚中国力量", 6, SUBJECT, 217008),
    (217065, "jpol_g9a_point_confidence", "做自信的中国人：自信的来源与表现", 7, SUBJECT, 217008),
)

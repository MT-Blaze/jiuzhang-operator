"""统编版（2019）高中语文选择性必修上册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G10 = 10
BOOK_ID = 1103

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中语文选择性必修上册",
    "chn_x1",
    1,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (110301, "第一单元 中国革命传统作品研习", "chn_x1_u01", 1, BOOK_ID, None),
    (110302, "第二单元 先秦诸子散文", "chn_x1_u02", 2, BOOK_ID, None),
    (110303, "第三单元 外国作家作品研习", "chn_x1_u03", 3, BOOK_ID, None),
    (110304, "第四单元 逻辑的力量", "chn_x1_u04", 4, BOOK_ID, None),
    (110305, "古诗词诵读", "chn_x1_u05", 5, BOOK_ID, None),
    (110311, "第1课 中国人民站起来了", "chn_x1_l01", 1, BOOK_ID, 110301),
    (110312, "第2课 长征胜利万岁／大战中的插曲", "chn_x1_l02", 2, BOOK_ID, 110301),
    (110313, "第3课 别了，“不列颠尼亚”／县委书记的榜样——焦裕禄", "chn_x1_l03", 3, BOOK_ID, 110301),
    (110314, "第4课 《论语》十二章／大学之道／人皆有不忍人之心", "chn_x1_l04", 1, BOOK_ID, 110302),
    (110315, "第5课 《老子》四章／五石之瓠", "chn_x1_l05", 2, BOOK_ID, 110302),
    (110316, "第6课 兼爱", "chn_x1_l06", 3, BOOK_ID, 110302),
    (110317, "第7课 大卫·科波菲尔（节选）", "chn_x1_l07", 1, BOOK_ID, 110303),
    (110318, "第8课 复活（节选）", "chn_x1_l08", 2, BOOK_ID, 110303),
    (110319, "第9课 老人与海（节选）", "chn_x1_l09", 3, BOOK_ID, 110303),
    (110320, "第10课 百年孤独（节选）", "chn_x1_l10", 4, BOOK_ID, 110303),
    (110321, "发现潜藏的逻辑谬误／运用有效的推理形式／采用合理的论证方法", "chn_x1_l11", 1, BOOK_ID, 110304),
    (110322, "无衣／春江花月夜／将进酒／江城子·乙卯正月二十日夜记梦", "chn_x1_l12", 1, BOOK_ID, 110305),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 130001-130010 为册域与文体能力层，130011-130099 为逐课细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (130001, "chn_x1_domain_revolution", "中国革命传统作品研习：革命叙事、演讲与纪实文体", 1, SUBJECT, G10, None),
    (130002, "chn_x1_domain_preqin_thought", "先秦诸子散文：儒道墨的思想范畴与说理方式", 2, SUBJECT, G10, None),
    (130003, "chn_x1_domain_foreign_fiction", "外国作家作品研习：成长、救赎、硬汉与魔幻叙事", 3, SUBJECT, G10, None),
    (130004, "chn_x1_domain_logic", "逻辑的力量：概念、推理、谬误与论证", 4, SUBJECT, G10, None),
    (130005, "chn_x1_domain_poetry", "古诗词诵读：军旅、春江、劝酒与悼亡的抒情路径", 5, SUBJECT, G10, None),
    (130006, "chn_x1_domain_narrative", "中外小说叙事艺术：视角、时间与人物塑造", 6, SUBJECT, G10, None),
    (130007, "chn_x1_domain_practical", "演讲辞与新闻通讯：现场感、真实性与信息筛选", 7, SUBJECT, G10, None),
    (130008, "chn_x1_domain_classical", "文言实词句法与古代文化常识", 8, SUBJECT, G10, None),
    (130009, "chn_x1_domain_language", "名句默写与语言积累运用", 9, SUBJECT, G10, None),
    (130010, "chn_x1_domain_task", "读写任务与比较阅读：札记、短评与议题设计", 10, SUBJECT, G10, None),

    # 第一单元 中国革命传统作品研习
    (130011, "chn_x1_point_zhancilai_style", "《中国人民站起来了》政论演讲的庄严语体与历史现场感", 1, SUBJECT, G10, 130001),
    (130012, "chn_x1_point_zhancilai_symbol", "《中国人民站起来了》“站起来了”的象征意涵与民族自信宣告", 2, SUBJECT, G10, 130001),
    (130013, "chn_x1_point_zhancilai_structure", "《中国人民站起来了》回顾、宣告、展望的三段式推进", 3, SUBJECT, G10, 130001),
    (130014, "chn_x1_point_changzheng_detail", "《长征胜利万岁》回忆录的现场细节与长征精神提炼", 4, SUBJECT, G10, 130001),
    (130015, "chn_x1_point_changzheng_metaphor", "《长征胜利万岁》“宣言书、宣传队、播种机”的比喻系统", 5, SUBJECT, G10, 130001),
    (130016, "chn_x1_point_dazhan_humanity", "《大战中的插曲》战火中的人道主义叙事与情感温度", 6, SUBJECT, G10, 130001),
    (130017, "chn_x1_point_dazhan_perspective", "《大战中的插曲》第一人称回忆视角与史料互证", 7, SUBJECT, G10, 130001),
    (130018, "chn_x1_point_buliedian_scene", "《别了，“不列颠尼亚”》新闻特写的场景剪辑与殖民终结", 8, SUBJECT, G10, 130001),
    (130019, "chn_x1_point_buliedian_time", "《别了，“不列颠尼亚”》时间标记与“雨”的象征意味", 9, SUBJECT, G10, 130001),
    (130020, "chn_x1_point_jiaoyulu_detail", "《县委书记的榜样——焦裕禄》人物通讯的典型事例与细节白描", 10, SUBJECT, G10, 130001),
    (130021, "chn_x1_point_jiaoyulu_image", "《县委书记的榜样——焦裕禄》“三害”治理叙事与公仆形象", 11, SUBJECT, G10, 130001),
    (130022, "chn_x1_point_revolution_source", "革命传统作品的史料意识与革命文化的当代传承", 12, SUBJECT, G10, 130001),
    (130023, "chn_x1_point_revolution_genre", "回忆录、新闻特写与人物通讯的文体差异", 13, SUBJECT, G10, 130001),

    # 第二单元 先秦诸子散文
    (130024, "chn_x1_point_lunyu_renli", "《论语》十二章“仁”与“礼”的核心范畴辨析", 1, SUBJECT, G10, 130002),
    (130025, "chn_x1_point_lunyu_junzi", "《论语》十二章“君子”人格与修身条目梳理", 2, SUBJECT, G10, 130002),
    (130026, "chn_x1_point_lunyu_style", "《论语》十二章语录体的对话情境与格言表达", 3, SUBJECT, G10, 130002),
    (130027, "chn_x1_point_daxue_structure", "《大学之道》“三纲领”“八条目”的逻辑层次", 4, SUBJECT, G10, 130002),
    (130028, "chn_x1_point_daxue_path", "《大学之道》修齐治平的推演路径与现实指向", 5, SUBJECT, G10, 130002),
    (130029, "chn_x1_point_buren_four_ends", "《人皆有不忍人之心》“四端”说与性善论论证", 6, SUBJECT, G10, 130002),
    (130030, "chn_x1_point_buren_example", "《人皆有不忍人之心》“孺子将入于井”的例证与类比", 7, SUBJECT, G10, 130002),
    (130031, "chn_x1_point_laozi_dialectic", "《老子》四章“有无相生”的辩证思维", 8, SUBJECT, G10, 130002),
    (130032, "chn_x1_point_laozi_usefulness", "《老子》四章“有之以为利，无之以为用”的辩证智慧", 9, SUBJECT, G10, 130002),
    (130033, "chn_x1_point_laozi_reverse", "《老子》四章反向言说与“自见者不明”的处世警诫", 10, SUBJECT, G10, 130002),
    (130034, "chn_x1_point_wushi_useless", "《五石之瓠》“大瓠之用”的寓言与无用之用", 11, SUBJECT, G10, 130002),
    (130035, "chn_x1_point_wushi_dialogue", "《五石之瓠》庄子与惠子对话的机锋与价值观分歧", 12, SUBJECT, G10, 130002),
    (130036, "chn_x1_point_jianai_thesis", "《兼爱》“兼相爱、交相利”的论证起点", 13, SUBJECT, G10, 130002),
    (130037, "chn_x1_point_jianai_reasoning", "《兼爱》由“不相爱”致乱的归因推理与墨家文风", 14, SUBJECT, G10, 130002),
    (130038, "chn_x1_point_schools_compare", "儒道墨三家治世方案与义利观的比较", 15, SUBJECT, G10, 130002),

    # 第三单元 外国作家作品研习
    (130039, "chn_x1_point_david_bildung", "《大卫·科波菲尔（节选）》第一人称成长叙事与童年视角", 1, SUBJECT, G10, 130003),
    (130040, "chn_x1_point_david_micawber", "《大卫·科波菲尔（节选）》米考伯夫妇的喜剧形象与辛酸底色", 2, SUBJECT, G10, 130003),
    (130041, "chn_x1_point_david_setting", "《大卫·科波菲尔（节选）》环境描写与人物处境的互文", 3, SUBJECT, G10, 130003),
    (130042, "chn_x1_point_resurrection_awaken", "《复活（节选）》聂赫留朵夫的精神觉醒与忏悔主题", 4, SUBJECT, G10, 130003),
    (130043, "chn_x1_point_resurrection_maslova", "《复活（节选）》玛丝洛娃形象转变与“复活”的双重含义", 5, SUBJECT, G10, 130003),
    (130044, "chn_x1_point_resurrection_dialogue", "《复活（节选）》对话交锋中的心理揭示与道德审视", 6, SUBJECT, G10, 130003),
    (130045, "chn_x1_point_oldman_hero", "《老人与海（节选）》桑地亚哥的硬汉形象与“重压下的优雅”", 7, SUBJECT, G10, 130003),
    (130046, "chn_x1_point_oldman_iceberg", "《老人与海（节选）》“冰山原则”与简洁叙事的张力", 8, SUBJECT, G10, 130003),
    (130047, "chn_x1_point_oldman_symbol", "《老人与海（节选）》大马林鱼与鲨鱼的象征系统", 9, SUBJECT, G10, 130003),
    (130048, "chn_x1_point_solitude_time", "《百年孤独（节选）》魔幻现实主义的时间循环与家族谱系叙事", 10, SUBJECT, G10, 130003),
    (130049, "chn_x1_point_solitude_history", "《百年孤独（节选）》马孔多的孤独症候与拉美历史隐喻", 11, SUBJECT, G10, 130003),
    (130050, "chn_x1_point_solitude_defamiliar", "《百年孤独（节选）》神奇细节的陌生化效果与叙事语调", 12, SUBJECT, G10, 130003),
    (130051, "chn_x1_point_foreign_perspective", "四部外国小说的人称、视角与叙事节奏比较", 13, SUBJECT, G10, 130003),
    (130052, "chn_x1_point_foreign_psychology", "心理描写在四部作品中的不同形态", 14, SUBJECT, G10, 130003),
    (130053, "chn_x1_point_foreign_genre", "批判现实主义与现代主义小说的文体分野", 15, SUBJECT, G10, 130003),

    # 第四单元 逻辑的力量
    (130054, "chn_x1_point_logic_concept", "概念的内涵、外延与偷换概念的辨误", 1, SUBJECT, G10, 130004),
    (130055, "chn_x1_point_logic_judgment", "判断的类型及量项、联项的准确使用", 2, SUBJECT, G10, 130004),
    (130056, "chn_x1_point_logic_syllogism", "三段论推理的格与式及有效性检验", 3, SUBJECT, G10, 130004),
    (130057, "chn_x1_point_logic_conditions", "充分条件、必要条件与充要条件的区分", 4, SUBJECT, G10, 130004),
    (130058, "chn_x1_point_logic_induction", "归纳推理的或然性与样本代表性", 5, SUBJECT, G10, 130004),
    (130059, "chn_x1_point_logic_analogy", "类比推理的可靠性与相似性限度", 6, SUBJECT, G10, 130004),
    (130060, "chn_x1_point_fallacy_partial", "潜藏的逻辑谬误：以偏概全与循环论证", 7, SUBJECT, G10, 130004),
    (130061, "chn_x1_point_fallacy_contradiction", "潜藏的逻辑谬误：自相矛盾与两不可", 8, SUBJECT, G10, 130004),
    (130062, "chn_x1_point_fallacy_cause", "潜藏的逻辑谬误：强加因果与因果倒置", 9, SUBJECT, G10, 130004),
    (130063, "chn_x1_point_logic_hypothetical", "假言推理与选言推理的有效形式", 10, SUBJECT, G10, 130004),
    (130064, "chn_x1_point_logic_methods", "举例、引用、对比等论证方法的合理使用", 11, SUBJECT, G10, 130004),
    (130065, "chn_x1_point_logic_premise", "论证的隐含前提与前提补全", 12, SUBJECT, G10, 130004),
    (130066, "chn_x1_point_logic_refute", "驳论中的归谬法与反例法", 13, SUBJECT, G10, 130004),

    # 古诗词诵读
    (130067, "chn_x1_point_wuyi_repetition", "《无衣》重章叠句与同仇敌忾的战斗动员", 1, SUBJECT, G10, 130005),
    (130068, "chn_x1_point_wuyi_style", "《无衣》“岂曰无衣”问答体与《诗经》军旅诗风貌", 2, SUBJECT, G10, 130005),
    (130069, "chn_x1_point_chunjiang_moon", "《春江花月夜》月升月落的时空结构", 3, SUBJECT, G10, 130005),
    (130070, "chn_x1_point_chunjiang_philosophy", "《春江花月夜》“月”意象的哲思与宇宙意识", 4, SUBJECT, G10, 130005),
    (130071, "chn_x1_point_chunjiang_status", "《春江花月夜》情景理交融与“孤篇横绝”的艺术地位", 5, SUBJECT, G10, 130005),
    (130072, "chn_x1_point_jiangjinjiu_emotion", "《将进酒》豪放中的悲慨与情感起伏曲线", 6, SUBJECT, G10, 130005),
    (130073, "chn_x1_point_jiangjinjiu_language", "《将进酒》夸张、呼告与劝酒诗的语言气势", 7, SUBJECT, G10, 130005),
    (130074, "chn_x1_point_jiangchengzi_dream", "《江城子·乙卯正月二十日夜记梦》悼亡梦境虚实相生的结构", 8, SUBJECT, G10, 130005),
    (130075, "chn_x1_point_jiangchengzi_time", "《江城子·乙卯正月二十日夜记梦》“十年生死”的时空对照与白描", 9, SUBJECT, G10, 130005),

    # 小说叙事艺术
    (130076, "chn_x1_point_narrative_person", "叙述人称与视角选择的表达效果", 1, SUBJECT, G10, 130006),
    (130077, "chn_x1_point_narrative_time", "叙事时间：顺叙、倒叙、插叙与预叙", 2, SUBJECT, G10, 130006),
    (130078, "chn_x1_point_narrative_setting", "环境描写的氛围营造与人物塑造功能", 3, SUBJECT, G10, 130006),
    (130079, "chn_x1_point_narrative_character", "人物形象分析的言行细节与心理依据", 4, SUBJECT, G10, 130006),
    (130080, "chn_x1_point_narrative_theme", "小说主题的多义性与时代背景的关联", 5, SUBJECT, G10, 130006),
    (130081, "chn_x1_point_narrative_excerpt", "长篇小说节选阅读的上下文衔接策略", 6, SUBJECT, G10, 130006),

    # 演讲辞与新闻通讯
    (130082, "chn_x1_point_speech_audience", "演讲辞的对象意识与现场感营造", 1, SUBJECT, G10, 130007),
    (130083, "chn_x1_point_speech_rhetoric", "演讲辞的排比、反复与呼告修辞", 2, SUBJECT, G10, 130007),
    (130084, "chn_x1_point_feature_scene", "新闻特写的现场描写与细节选取", 3, SUBJECT, G10, 130007),
    (130085, "chn_x1_point_communication_model", "人物通讯的典型事例与主题提炼", 4, SUBJECT, G10, 130007),
    (130086, "chn_x1_point_practical_info", "实用类文本的信息筛选与观点提取", 5, SUBJECT, G10, 130007),

    # 文言实词句法与古代文化常识
    (130087, "chn_x1_point_classical_variants", "通假字与古今异义的辨析", 1, SUBJECT, G10, 130008),
    (130088, "chn_x1_point_classical_flexion", "词类活用：名词作状语、使动与意动", 2, SUBJECT, G10, 130008),
    (130089, "chn_x1_point_classical_judgment", "文言特殊句式：判断句与被动句", 3, SUBJECT, G10, 130008),
    (130090, "chn_x1_point_classical_inversion", "文言特殊句式：宾语前置与状语后置", 4, SUBJECT, G10, 130008),
    (130091, "chn_x1_point_classical_function", "虚词“之、其、而、以”的用法辨析", 5, SUBJECT, G10, 130008),
    (130092, "chn_x1_point_classical_culture", "古代文化常识：称谓、礼制与典籍", 6, SUBJECT, G10, 130008),

    # 名句默写与语言积累
    (130093, "chn_x1_point_recitation_scope", "本册名句默写的范围与高频易错字", 1, SUBJECT, G10, 130009),
    (130094, "chn_x1_point_idiom_usage", "成语与熟语的语境运用辨析", 2, SUBJECT, G10, 130009),
    (130095, "chn_x1_point_sentence_error", "病句辨析：搭配不当与成分残缺", 3, SUBJECT, G10, 130009),
    (130096, "chn_x1_point_language_coherence", "语言表达的简明、连贯与得体", 4, SUBJECT, G10, 130009),

    # 读写任务与比较阅读
    (130097, "chn_x1_point_task_thematic_note", "单元研习任务：革命传统与诸子思想的札记写作", 1, SUBJECT, G10, 130010),
    (130098, "chn_x1_point_task_short_review", "文学短评的选题、角度与论证", 2, SUBJECT, G10, 130010),
    (130099, "chn_x1_point_task_comparison", "跨文本比较阅读的议题设计与材料组织", 3, SUBJECT, G10, 130010),
)

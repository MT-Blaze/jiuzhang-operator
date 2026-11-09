"""统编版（2019）高中语文必修下册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G10 = 10
BOOK_ID = 1102

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中语文必修下册",
    "chn_r2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (110201, "第一单元 中华文明之光", "chn_r2_u01", 1, BOOK_ID, None),
    (110202, "第二单元 良知与悲悯", "chn_r2_u02", 2, BOOK_ID, None),
    (110203, "第三单元 探索与创新", "chn_r2_u03", 3, BOOK_ID, None),
    (110204, "第四单元 信息时代的语文生活", "chn_r2_u04", 4, BOOK_ID, None),
    (110205, "第五单元 抱负与使命", "chn_r2_u05", 5, BOOK_ID, None),
    (110206, "第六单元 观察与批判", "chn_r2_u06", 6, BOOK_ID, None),
    (110207, "第七单元 责任与担当", "chn_r2_u07", 7, BOOK_ID, None),
    (110208, "第八单元 家国天下", "chn_r2_u08", 8, BOOK_ID, None),
    (110209, "古诗词诵读", "chn_r2_u09", 9, BOOK_ID, None),
    (110211, "第1课 子路、曾皙、冉有、公西华侍坐／齐桓晋文之事／庖丁解牛", "chn_r2_l01", 1, BOOK_ID, 110201),
    (110212, "第2课 烛之武退秦师", "chn_r2_l02", 2, BOOK_ID, 110201),
    (110213, "第3课 鸿门宴", "chn_r2_l03", 3, BOOK_ID, 110201),
    (110214, "第4课 窦娥冤（节选）", "chn_r2_l04", 1, BOOK_ID, 110202),
    (110215, "第5课 雷雨（节选）", "chn_r2_l05", 2, BOOK_ID, 110202),
    (110216, "第6课 哈姆莱特（节选）", "chn_r2_l06", 3, BOOK_ID, 110202),
    (110217, "第7课 青蒿素：人类征服疾病的一小步／一名物理学家的教育历程", "chn_r2_l07", 1, BOOK_ID, 110203),
    (110218, "第8课 中国建筑的特征", "chn_r2_l08", 2, BOOK_ID, 110203),
    (110219, "第9课 说“木叶”", "chn_r2_l09", 3, BOOK_ID, 110203),
    (110220, "信息时代的语文生活：跨媒介阅读与交流", "chn_r2_l10", 1, BOOK_ID, 110204),
    (110221, "第10课 在《人民报》创刊纪念会上的演说／在马克思墓前的讲话", "chn_r2_l11", 1, BOOK_ID, 110205),
    (110222, "第11课 谏逐客书／与妻书", "chn_r2_l12", 2, BOOK_ID, 110205),
    (110223, "第12课 祝福", "chn_r2_l13", 1, BOOK_ID, 110206),
    (110224, "第13课 林教头风雪山神庙／装在套子里的人", "chn_r2_l14", 2, BOOK_ID, 110206),
    (110225, "第14课 促织／变形记（节选）", "chn_r2_l15", 3, BOOK_ID, 110206),
    (110226, "第15课 谏太宗十思疏／答司马谏议书", "chn_r2_l16", 1, BOOK_ID, 110207),
    (110227, "第16课 阿房宫赋／六国论", "chn_r2_l17", 1, BOOK_ID, 110208),
    (110228, "登岳阳楼／桂枝香·金陵怀古", "chn_r2_l18", 1, BOOK_ID, 110209),
    (110229, "念奴娇·过洞庭／游园（皂罗袍）", "chn_r2_l19", 2, BOOK_ID, 110209),
)

# id / code / name / sort_order / subject_id / parent_id
# 120001-120010 为册域与文体能力层，120011-120099 为逐课细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (120001, "chn_r2_domain_preqin", "先秦诸子与史传散文：对话说理、寓言与叙事", 1, SUBJECT, None),
    (120002, "chn_r2_domain_drama", "戏剧与悲剧鉴赏：冲突、潜台词与舞台呈现", 2, SUBJECT, None),
    (120003, "chn_r2_domain_science", "科普与学术随笔：知识转化、概念辨析与科学思维", 3, SUBJECT, None),
    (120004, "chn_r2_domain_media", "跨媒介阅读与交流：信息辨识、表达与媒介素养", 4, SUBJECT, None),
    (120005, "chn_r2_domain_speech", "演讲辞与书信：场合意识、情感力量与论证策略", 5, SUBJECT, None),
    (120006, "chn_r2_domain_critical_fiction", "社会批判小说：典型人物、叙事视角与讽刺艺术", 6, SUBJECT, None),
    (120007, "chn_r2_domain_memorial", "奏疏与书信体政论：谏议逻辑、驳论分寸与文体差异", 7, SUBJECT, None),
    (120008, "chn_r2_domain_history_argument", "史论与赋：史实剪裁、铺陈讽喻与借古论今", 8, SUBJECT, None),
    (120009, "chn_r2_domain_poetry_recitation", "古诗词诵读：登临怀古、意象组合与风格比较", 9, SUBJECT, None),
    (120010, "chn_r2_domain_language", "语言积累与整本书阅读：文言现象、名著研读与写作", 10, SUBJECT, None),

    # 第一单元 中华文明之光
    (120011, "chn_r2_point_shizuo_ambition", "《侍坐》四子言志的差异与孔子“吾与点也”的深意", 1, SUBJECT, 120001),
    (120012, "chn_r2_point_shizuo_dialogue", "《侍坐》对话场景、人物神态与孔子因材施教", 2, SUBJECT, 120001),
    (120013, "chn_r2_point_qihuan_persuasion", "《齐桓晋文之事》迂回诱导的论辩策略与“保民而王”", 3, SUBJECT, 120001),
    (120014, "chn_r2_point_qihuan_rhetoric", "《齐桓晋文之事》比喻、反问与层层推进的说理", 4, SUBJECT, 120001),
    (120015, "chn_r2_point_paoding_allegory", "《庖丁解牛》“依乎天理”的寓言寓意与养生之道", 5, SUBJECT, 120001),
    (120016, "chn_r2_point_paoding_skill", "《庖丁解牛》解牛动作的层次描写与“道进乎技”", 6, SUBJECT, 120001),
    (120017, "chn_r2_point_zhuzhi_persuasion", "《烛之武退秦师》利害分析型游说与秦晋联盟瓦解", 7, SUBJECT, 120001),
    (120018, "chn_r2_point_zhuzhi_narrative", "《烛之武退秦师》伏笔照应、详略安排与叙事节奏", 8, SUBJECT, 120001),
    (120019, "chn_r2_point_hongmen_characters", "《鸿门宴》项羽、刘邦人物形象对比与叙事张力", 9, SUBJECT, 120001),
    (120020, "chn_r2_point_hongmen_detail", "《鸿门宴》座次、称谓与细节中的权力关系", 10, SUBJECT, 120001),
    (120021, "chn_r2_point_preqin_genre", "先秦诸子散文与史传散文的文体差异及本单元文言现象", 11, SUBJECT, 120001),

    # 第二单元 良知与悲悯
    (120022, "chn_r2_point_doue_vows", "《窦娥冤》三桩誓愿的浪漫手法与冤情控诉", 1, SUBJECT, 120002),
    (120023, "chn_r2_point_doue_zaju", "《窦娥冤》曲词、宾白、科介与元杂剧体制", 2, SUBJECT, 120002),
    (120024, "chn_r2_point_doue_character", "《窦娥冤》窦娥形象由顺从到反抗的转变", 3, SUBJECT, 120002),
    (120025, "chn_r2_point_leiyu_recognition", "《雷雨》周朴园与鲁侍萍相认的潜台词与戏剧张力", 4, SUBJECT, 120002),
    (120026, "chn_r2_point_leiyu_stage", "《雷雨》舞台说明、人物上下场与封闭空间结构", 5, SUBJECT, 120002),
    (120027, "chn_r2_point_leiyu_tragedy", "《雷雨》繁漪、周萍人物关系的悲剧性", 6, SUBJECT, 120002),
    (120028, "chn_r2_point_hamlet_soliloquy", "《哈姆莱特》“生存还是毁灭”独白的哲思与延宕", 7, SUBJECT, 120002),
    (120029, "chn_r2_point_hamlet_hesitation", "《哈姆莱特》复仇犹豫与人文主义困境", 8, SUBJECT, 120002),
    (120030, "chn_r2_point_drama_language", "戏剧语言的动作性、个性化与潜台词", 9, SUBJECT, 120002),
    (120031, "chn_r2_point_tragedy_compare", "中外悲剧比较：命运悲剧、社会悲剧与性格悲剧", 10, SUBJECT, 120002),

    # 第三单元 探索与创新
    (120032, "chn_r2_point_qinghaosu_process", "《青蒿素》科研历程叙述与“一小步”的谦逊表达", 1, SUBJECT, 120003),
    (120033, "chn_r2_point_qinghaosu_spirit", "《青蒿素》科学精神：探索、协作与担当", 2, SUBJECT, 120003),
    (120034, "chn_r2_point_physicist_childhood", "《一名物理学家的教育历程》童年好奇与科学想象", 3, SUBJECT, 120003),
    (120035, "chn_r2_point_physicist_method", "《一名物理学家的教育历程》探究方法与证据意识", 4, SUBJECT, 120003),
    (120036, "chn_r2_point_architecture_structure", "《中国建筑的特征》总分结构与九大特征梳理", 5, SUBJECT, 120003),
    (120037, "chn_r2_point_architecture_metaphor", "《中国建筑的特征》“词汇”“文法”比喻与术语通俗化", 6, SUBJECT, 120003),
    (120038, "chn_r2_point_muye_suggestion", "《说“木叶”》诗歌语言的暗示性与概念辨析", 7, SUBJECT, 120003),
    (120039, "chn_r2_point_muye_compare", "《说“木叶”》“木”与“树”的艺术特征比较", 8, SUBJECT, 120003),
    (120040, "chn_r2_point_science_essay", "科普文与学术随笔：知识性、趣味性与思辨性", 9, SUBJECT, 120003),

    # 第四单元 信息时代的语文生活
    (120041, "chn_r2_point_cross_media", "跨媒介阅读：文字、图像、音频、视频的信息互补", 1, SUBJECT, 120004),
    (120042, "chn_r2_point_info_verify", "媒介信息辨识：来源核实、事实核查与谣言辨析", 2, SUBJECT, 120004),
    (120043, "chn_r2_point_net_language", "网络语言规范与新媒体表达边界", 3, SUBJECT, 120004),
    (120044, "chn_r2_point_new_media_copy", "新媒体文案的标题、配图与传播效果分析", 4, SUBJECT, 120004),
    (120045, "chn_r2_point_media_presentation", "跨媒介成果呈现：图表、短视频与解说词", 5, SUBJECT, 120004),
    (120046, "chn_r2_point_media_literacy", "媒介素养：算法推荐、信息茧房与批判性接收", 6, SUBJECT, 120004),

    # 第五单元 抱负与使命
    (120047, "chn_r2_point_peoples_paper_context", "《在〈人民报〉创刊纪念会上的演说》历史语境与无产阶级使命", 1, SUBJECT, 120005),
    (120048, "chn_r2_point_peoples_paper_style", "《在〈人民报〉创刊纪念会上的演说》比喻、反讽与磅礴气势", 2, SUBJECT, 120005),
    (120049, "chn_r2_point_marx_grave_structure", "《在马克思墓前的讲话》悼词结构与“两点发现”的概括", 3, SUBJECT, 120005),
    (120050, "chn_r2_point_marx_grave_emotion", "《在马克思墓前的讲话》含蓄抒情与评价分寸", 4, SUBJECT, 120005),
    (120051, "chn_r2_point_speech_skills", "演讲辞的针对性、鼓动性与节奏控制", 5, SUBJECT, 120005),
    (120052, "chn_r2_point_zhuke_argument", "《谏逐客书》铺陈事实与“逐客”之非的论证逻辑", 6, SUBJECT, 120005),
    (120053, "chn_r2_point_zhuke_language", "《谏逐客书》铺排、对比与骈散结合的语言气势", 7, SUBJECT, 120005),
    (120054, "chn_r2_point_yuqi_love_country", "《与妻书》儿女情与家国义的统一", 8, SUBJECT, 120005),
    (120055, "chn_r2_point_yuqi_letter", "《与妻书》书信体的倾诉语气与细节追忆", 9, SUBJECT, 120005),

    # 第六单元 观察与批判
    (120056, "chn_r2_point_zhufu_fate", "《祝福》祥林嫂三次到鲁镇的遭遇与命运轨迹", 1, SUBJECT, 120006),
    (120057, "chn_r2_point_zhufu_narrative", "《祝福》倒叙结构、“我”的叙述视角与反讽", 2, SUBJECT, 120006),
    (120058, "chn_r2_point_zhufu_scene", "《祝福》祝福场景的反复出现与礼教批判", 3, SUBJECT, 120006),
    (120059, "chn_r2_point_zhufu_minor", "《祝福》鲁四老爷、柳妈等次要人物的社会意义", 4, SUBJECT, 120006),
    (120060, "chn_r2_point_linchong_change", "《林教头风雪山神庙》林冲性格转变与“逼上梁山”", 5, SUBJECT, 120006),
    (120061, "chn_r2_point_linchong_snow", "《林教头风雪山神庙》风雪描写与情节推进", 6, SUBJECT, 120006),
    (120062, "chn_r2_point_linchong_foreshadow", "《林教头风雪山神庙》伏笔、巧合与细节链", 7, SUBJECT, 120006),
    (120063, "chn_r2_point_chameleon_symbol", "《装在套子里的人》别里科夫的“套子”象征", 8, SUBJECT, 120006),
    (120064, "chn_r2_point_chameleon_satire", "《装在套子里的人》夸张、讽刺与叙述者视角", 9, SUBJECT, 120006),
    (120065, "chn_r2_point_cuzhi_absurd", "《促织》成名一家命运与“人不如虫”的荒诞", 10, SUBJECT, 120006),
    (120066, "chn_r2_point_cuzhi_plot", "《促织》情节起伏与幻想手法的批判性", 11, SUBJECT, 120006),
    (120067, "chn_r2_point_metamorphosis_alienation", "《变形记》格里高尔变形的荒诞设定与异化主题", 12, SUBJECT, 120006),
    (120068, "chn_r2_point_metamorphosis_detail", "《变形记》细节写实与家庭关系的冷峻揭示", 13, SUBJECT, 120006),
    (120069, "chn_r2_point_critical_fiction", "社会批判小说：典型环境、典型人物与批判锋芒", 14, SUBJECT, 120006),

    # 第七单元 责任与担当
    (120070, "chn_r2_point_shisi_content", "《谏太宗十思疏》“十思”的具体内容与为君之道", 1, SUBJECT, 120007),
    (120071, "chn_r2_point_shisi_argument", "《谏太宗十思疏》比喻论证、正反对比与“固本思源”", 2, SUBJECT, 120007),
    (120072, "chn_r2_point_shisi_language", "《谏太宗十思疏》骈偶句式与恳切劝谏的语气", 3, SUBJECT, 120007),
    (120073, "chn_r2_point_simajian_rebuttal", "《答司马谏议书》逐条驳斥“侵官、生事、征利、拒谏”", 4, SUBJECT, 120007),
    (120074, "chn_r2_point_simajian_tone", "《答司马谏议书》柔中带刚的论辩分寸与书信体驳论", 5, SUBJECT, 120007),
    (120075, "chn_r2_point_memorial_genre", "奏疏与书信体政论的文体差异及写作目的", 6, SUBJECT, 120007),
    (120076, "chn_r2_point_remonstrance_culture", "古代谏议文化：直谏、讽谏与君臣关系的表达策略", 7, SUBJECT, 120007),

    # 第八单元 家国天下
    (120077, "chn_r2_point_epanggong_structure", "《阿房宫赋》铺陈排比与卒章显志的讽喻结构", 1, SUBJECT, 120008),
    (120078, "chn_r2_point_epanggong_description", "《阿房宫赋》建筑、歌舞、珍宝的层递描写", 2, SUBJECT, 120008),
    (120079, "chn_r2_point_epanggong_argument", "《阿房宫赋》骈散结合、夸张与“后人哀之”的议论", 3, SUBJECT, 120008),
    (120080, "chn_r2_point_epanggong_satire", "《阿房宫赋》借古讽今的现实指向", 4, SUBJECT, 120008),
    (120081, "chn_r2_point_liuguo_thesis", "《六国论》“弊在赂秦”的中心论点与论证结构", 5, SUBJECT, 120008),
    (120082, "chn_r2_point_liuguo_method", "《六国论》对比、假设与史实结合的论证方法", 6, SUBJECT, 120008),
    (120083, "chn_r2_point_liuguo_intent", "《六国论》借六国讽北宋的写作意图", 7, SUBJECT, 120008),
    (120084, "chn_r2_point_fu_vs_history", "赋与史论的文体差异：铺采摛文与据事说理", 8, SUBJECT, 120008),
    (120085, "chn_r2_point_history_argument", "史论写作：观点提炼、史实筛选与逻辑推演", 9, SUBJECT, 120008),

    # 古诗词诵读
    (120086, "chn_r2_point_yueyang_scene", "《登岳阳楼》洞庭气象与身世家国之悲", 1, SUBJECT, 120009),
    (120087, "chn_r2_point_yueyang_craft", "《登岳阳楼》颔联写景的时空张力与炼字", 2, SUBJECT, 120009),
    (120088, "chn_r2_point_guizhixiang_scene", "《桂枝香·金陵怀古》登临所见与六朝兴亡之叹", 3, SUBJECT, 120009),
    (120089, "chn_r2_point_guizhixiang_allusion", "《桂枝香·金陵怀古》用典、对比与“商女”讽喻", 4, SUBJECT, 120009),
    (120090, "chn_r2_point_dongting_scene", "《念奴娇·过洞庭》洞庭青草的自然境界与人格自况", 5, SUBJECT, 120009),
    (120091, "chn_r2_point_dongting_character", "《念奴娇·过洞庭》物我交融与“肝肺皆冰雪”的胸襟", 6, SUBJECT, 120009),
    (120092, "chn_r2_point_youyuan_awakening", "《游园（皂罗袍）》园林春色与杜丽娘的青春觉醒", 7, SUBJECT, 120009),
    (120093, "chn_r2_point_recitation_compare", "古诗词诵读四首比较：登临、怀古与抒情的不同路径", 8, SUBJECT, 120009),

    # 语言积累与整本书阅读
    (120094, "chn_r2_point_classical_words", "文言实词一词多义与词类活用的梳理方法", 1, SUBJECT, 120010),
    (120095, "chn_r2_point_classical_patterns", "文言特殊句式：判断、被动、倒装与省略", 2, SUBJECT, 120010),
    (120096, "chn_r2_point_culture_common", "古代文化常识：称谓、礼俗、科举与地理", 3, SUBJECT, 120010),
    (120097, "chn_r2_point_red_chamber", "《红楼梦》整本书阅读：人物关系图谱与专题研读", 4, SUBJECT, 120010),
    (120098, "chn_r2_point_task_writing", "任务驱动型写作：材料审读、情境任务与观点表达", 5, SUBJECT, 120010),
    (120099, "chn_r2_point_recitation_dictation", "全册名句默写与易错字词整理", 6, SUBJECT, 120010),
)

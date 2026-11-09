"""统编版（2019）高中语文选择性必修中册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G10 = 10
BOOK_ID = 1104

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中语文选择性必修中册",
    "chn_x2",
    2,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (110401, "第一单元 理论与经典", "chn_x2_u01", 1, BOOK_ID, None),
    (110402, "第二单元 中国革命传统作品研习", "chn_x2_u02", 2, BOOK_ID, None),
    (110403, "第三单元 史传与史论", "chn_x2_u03", 3, BOOK_ID, None),
    (110404, "第四单元 外国戏剧与诗歌", "chn_x2_u04", 4, BOOK_ID, None),
    (110405, "古诗词诵读", "chn_x2_u05", 5, BOOK_ID, None),
    (110411, "第1课 社会历史的决定性基础", "chn_x2_l01", 1, BOOK_ID, 110401),
    (110412, "第2课 改造我们的学习／人的正确思想是从哪里来的？", "chn_x2_l02", 2, BOOK_ID, 110401),
    (110413, "第3课 实践是检验真理的唯一标准", "chn_x2_l03", 3, BOOK_ID, 110401),
    (110414, "第4课 修辞立其诚／怜悯是人的天性", "chn_x2_l04", 4, BOOK_ID, 110401),
    (110415, "第5课 人应当坚持正义", "chn_x2_l05", 5, BOOK_ID, 110401),
    (110416, "第6课 记念刘和珍君", "chn_x2_l06", 1, BOOK_ID, 110402),
    (110417, "第7课 包身工", "chn_x2_l07", 2, BOOK_ID, 110402),
    (110418, "第8课 荷花淀／小二黑结婚（节选）／党费", "chn_x2_l08", 3, BOOK_ID, 110402),
    (110419, "第9课 屈原列传", "chn_x2_l09", 1, BOOK_ID, 110403),
    (110420, "第10课 苏武传", "chn_x2_l10", 2, BOOK_ID, 110403),
    (110421, "第11课 过秦论", "chn_x2_l11", 3, BOOK_ID, 110403),
    (110422, "第12课 五代史伶官传序", "chn_x2_l12", 4, BOOK_ID, 110403),
    (110423, "第13课 玩偶之家（节选）", "chn_x2_l13", 1, BOOK_ID, 110404),
    (110424, "第14课 迷娘（之一）／致大海／自己之歌（节选）／树和天空", "chn_x2_l14", 2, BOOK_ID, 110404),
    (110425, "燕歌行并序／李凭箜篌引", "chn_x2_l15", 1, BOOK_ID, 110405),
    (110426, "锦瑟／书愤", "chn_x2_l16", 2, BOOK_ID, 110405),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 140001-140010 为册域与文体能力层，140011-140099 为逐课细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (140001, "chn_x2_domain_theory", "第一单元 理论与经典：社会科学论文与思想随笔的论证品格", 1, SUBJECT, G10, None),
    (140002, "chn_x2_domain_revolution", "第二单元 中国革命传统作品研习：杂文、报告文学与革命叙事", 2, SUBJECT, G10, None),
    (140003, "chn_x2_domain_history", "第三单元 史传与史论：人物传记与史论散文", 3, SUBJECT, G10, None),
    (140004, "chn_x2_domain_foreign", "第四单元 外国戏剧与诗歌：社会问题剧与浪漫主义抒情", 4, SUBJECT, G10, None),
    (140005, "chn_x2_domain_poetry", "古诗词诵读：边塞、音乐与咏怀的抒情传统", 5, SUBJECT, G10, None),
    (140006, "chn_x2_domain_classical", "文言实词、特殊句式与古代文化常识", 6, SUBJECT, G10, None),
    (140007, "chn_x2_domain_argument", "论述类文本：论点、论据与论证结构", 7, SUBJECT, G10, None),
    (140008, "chn_x2_domain_narrative", "叙事类文本：人物、视角与情节组织", 8, SUBJECT, G10, None),
    (140009, "chn_x2_domain_language", "语言积累运用与名句默写", 9, SUBJECT, G10, None),
    (140010, "chn_x2_domain_task", "单元研习任务与读写转化", 10, SUBJECT, G10, None),

    # 第一单元 理论与经典
    (140011, "chn_x2_point_base_superstructure", "《社会历史的决定性基础》中经济基础与上层建筑的辩证关系论证", 1, SUBJECT, G10, 140001),
    (140012, "chn_x2_point_base_letter", "《社会历史的决定性基础》恩格斯致博尔吉乌斯书信的论辩对象与反驳策略", 2, SUBJECT, G10, 140001),
    (140013, "chn_x2_point_base_force", "《社会历史的决定性基础》“历史合力”与偶然性、必然性的关系", 3, SUBJECT, G10, 140001),
    (140014, "chn_x2_point_base_term", "《社会历史的决定性基础》科学术语的通俗化与举例论证", 4, SUBJECT, G10, 140001),
    (140015, "chn_x2_point_gaizao_subjective", "《改造我们的学习》主观主义三种表现与“有的放矢”的对照论证", 5, SUBJECT, G10, 140001),
    (140016, "chn_x2_point_gaizao_style", "《改造我们的学习》政论文的破立结合与整散句式节奏", 6, SUBJECT, G10, 140001),
    (140017, "chn_x2_point_gaizao_title", "《改造我们的学习》标题的针对性与“认识—现状—建议”结构层次", 7, SUBJECT, G10, 140001),
    (140018, "chn_x2_point_zhengque_leap", "《人的正确思想是从哪里来的？》认识论“两次飞跃”的推理链条", 8, SUBJECT, G10, 140001),
    (140019, "chn_x2_point_zhengque_question", "《人的正确思想是从哪里来的？》设问开篇与层层追问的说理节奏", 9, SUBJECT, G10, 140001),
    (140020, "chn_x2_point_shijian_thesis", "《实践是检验真理的唯一标准》三个分论点的递进与标题的论断性", 10, SUBJECT, G10, 140001),
    (140021, "chn_x2_point_shijian_evidence", "《实践是检验真理的唯一标准》引用经典与回应现实的双重论据", 11, SUBJECT, G10, 140001),
    (140022, "chn_x2_point_shijian_refute", "《实践是检验真理的唯一标准》驳论中澄清前提、逐层辩难的方法", 12, SUBJECT, G10, 140001),
    (140023, "chn_x2_point_xiuci_sincerity", "《修辞立其诚》“诚”的多层含义与立诚的为文之道", 13, SUBJECT, G10, 140001),
    (140024, "chn_x2_point_xiuci_style", "《修辞立其诚》引用与训释结合的学术随笔笔法", 14, SUBJECT, G10, 140001),
    (140025, "chn_x2_point_lianmin_nature", "《怜悯是人的天性》卢梭对人类怜悯心的经验论证", 15, SUBJECT, G10, 140001),
    (140026, "chn_x2_point_lianmin_critique", "《怜悯是人的天性》“天性”命题与文明批判的关联", 16, SUBJECT, G10, 140001),
    (140027, "chn_x2_point_lianmin_tone", "《怜悯是人的天性》比较论证与自我辩驳的语调", 17, SUBJECT, G10, 140001),
    (140028, "chn_x2_point_zhengyi_elenchus", "《人应当坚持正义》苏格拉底诘问法的对话推进", 18, SUBJECT, G10, 140001),
    (140029, "chn_x2_point_zhengyi_concept", "《人应当坚持正义》“正义”与“善”的概念辨析", 19, SUBJECT, G10, 140001),
    (140030, "chn_x2_point_zhengyi_dialogue", "《人应当坚持正义》对话体哲理论证的逻辑层次", 20, SUBJECT, G10, 140001),
    (140031, "chn_x2_point_theory_evidence", "理论文章的观点提炼与材料支撑关系", 21, SUBJECT, G10, 140001),
    (140032, "chn_x2_point_theory_genre", "社会科学论文与思想随笔的文体差异", 22, SUBJECT, G10, 140001),
    (140033, "chn_x2_point_theory_language", "本单元论证语言的准确性与思辨性", 23, SUBJECT, G10, 140001),

    # 第二单元 中国革命传统作品研习
    (140034, "chn_x2_point_liuhezhen_emotion", "《记念刘和珍君》悲愤情感与议论抒情交织的语体特征", 1, SUBJECT, G10, 140002),
    (140035, "chn_x2_point_liuhezhen_scene", "《记念刘和珍君》三一八惨案叙述中的细节与控诉", 2, SUBJECT, G10, 140002),
    (140036, "chn_x2_point_liuhezhen_repetition", "《记念刘和珍君》“沉默呵，沉默呵”反复中的情感节制", 3, SUBJECT, G10, 140002),
    (140037, "chn_x2_point_liuhezhen_warrior", "《记念刘和珍君》“真的猛士”与庸人世界的对比", 4, SUBJECT, G10, 140002),
    (140038, "chn_x2_point_baoshengong_genre", "《包身工》报告文学新闻性与文学性的统一", 5, SUBJECT, G10, 140002),
    (140039, "chn_x2_point_baoshengong_figure", "《包身工》芦柴棒等典型人物的细节刻画", 6, SUBJECT, G10, 140002),
    (140040, "chn_x2_point_baoshengong_structure", "《包身工》说明、描写、议论交织的结构方式", 7, SUBJECT, G10, 140002),
    (140041, "chn_x2_point_baoshengong_data", "《包身工》数字统计与实地调查材料的实证力量", 8, SUBJECT, G10, 140002),
    (140042, "chn_x2_point_hehuadian_scene", "《荷花淀》诗化小说的意境与白洋淀风情", 9, SUBJECT, G10, 140002),
    (140043, "chn_x2_point_hehuadian_women", "《荷花淀》水生嫂等妇女形象与含蓄的对话描写", 10, SUBJECT, G10, 140002),
    (140044, "chn_x2_point_hehuadian_war", "《荷花淀》战争叙事的淡化处理与抒情笔调", 11, SUBJECT, G10, 140002),
    (140045, "chn_x2_point_erhei_language", "《小二黑结婚》赵树理乡土叙事与农民语言的通俗化", 12, SUBJECT, G10, 140002),
    (140046, "chn_x2_point_erhei_comedy", "《小二黑结婚》二诸葛、三仙姑的喜剧形象与迷信批判", 13, SUBJECT, G10, 140002),
    (140047, "chn_x2_point_dangfei_symbol", "《党费》黄新形象与咸菜、党证等细节的象征意味", 14, SUBJECT, G10, 140002),
    (140048, "chn_x2_point_dangfei_plot", "《党费》革命历史题材小说的情节压缩与情感张力", 15, SUBJECT, G10, 140002),
    (140049, "chn_x2_point_revolution_value", "革命传统作品的史料意识与革命文化的当代传承", 16, SUBJECT, G10, 140002),

    # 第三单元 史传与史论
    (140050, "chn_x2_point_quyuan_tragedy", "《屈原列传》屈原“信而见疑，忠而被谤”的悲剧逻辑", 1, SUBJECT, G10, 140003),
    (140051, "chn_x2_point_quyuan_style", "《屈原列传》司马迁评传结合、“发愤著书”的笔法", 2, SUBJECT, G10, 140003),
    (140052, "chn_x2_point_quyuan_lisao", "《屈原列传》评价《离骚》段落中的文学批评观", 3, SUBJECT, G10, 140003),
    (140053, "chn_x2_point_quyuan_text", "《屈原列传》“其文约，其辞微”的文本细读", 4, SUBJECT, G10, 140003),
    (140054, "chn_x2_point_suwu_integrity", "《苏武传》苏武牧羊十九年的志节叙事", 5, SUBJECT, G10, 140003),
    (140055, "chn_x2_point_suwu_contrast", "《苏武传》卫律、李陵劝降的对比与烘托", 6, SUBJECT, G10, 140003),
    (140056, "chn_x2_point_suwu_detail", "《苏武传》啮雪吞毡、杖汉节等细节的人物塑造", 7, SUBJECT, G10, 140003),
    (140057, "chn_x2_point_suwu_narrative", "《苏武传》班固史传的叙事剪裁与篇末评赞", 8, SUBJECT, G10, 140003),
    (140058, "chn_x2_point_guoqin_logic", "《过秦论》铺陈对比与“仁义不施而攻守之势异也”的史论逻辑", 9, SUBJECT, G10, 140003),
    (140059, "chn_x2_point_guoqin_contrast", "《过秦论》九国与秦、陈涉与六国的层递对比", 10, SUBJECT, G10, 140003),
    (140060, "chn_x2_point_guoqin_style", "《过秦论》排比夸张的语言气势与赋体笔法", 11, SUBJECT, G10, 140003),
    (140061, "chn_x2_point_guoqin_structure", "《过秦论》中心论点在文末的卒章显志结构", 12, SUBJECT, G10, 140003),
    (140062, "chn_x2_point_lingguan_theory", "《五代史伶官传序》盛衰之理与“人事”决定论", 13, SUBJECT, G10, 140003),
    (140063, "chn_x2_point_lingguan_warning", "《五代史伶官传序》“忧劳可以兴国，逸豫可以亡身”的警策", 14, SUBJECT, G10, 140003),
    (140064, "chn_x2_point_lingguan_zhuangzong", "《五代史伶官传序》庄宗得失天下的叙事与议论结合", 15, SUBJECT, G10, 140003),
    (140065, "chn_x2_point_lingguan_genre", "《五代史伶官传序》序体史论的文体特征与论证层次", 16, SUBJECT, G10, 140003),
    (140066, "chn_x2_point_history_genre", "史传与史论：叙事剪裁与观点表达的差异", 17, SUBJECT, G10, 140003),
    (140067, "chn_x2_point_history_language", "史传语言的简洁凝练与人物语言的个性化", 18, SUBJECT, G10, 140003),
    (140068, "chn_x2_point_history_chain", "史论中“史实—推论—结论”的论证链条", 19, SUBJECT, G10, 140003),

    # 第四单元 外国戏剧与诗歌
    (140069, "chn_x2_point_doll_awaken", "《玩偶之家》娜拉觉醒的三幕推进", 1, SUBJECT, G10, 140004),
    (140070, "chn_x2_point_doll_power", "《玩偶之家》海尔茂与娜拉对话中的权力关系", 2, SUBJECT, G10, 140004),
    (140071, "chn_x2_point_doll_symbol", "《玩偶之家》“玩偶”意象与社会问题剧的批判指向", 3, SUBJECT, G10, 140004),
    (140072, "chn_x2_point_doll_stage", "《玩偶之家》舞台说明与戏剧冲突的呈现", 4, SUBJECT, G10, 140004),
    (140073, "chn_x2_point_doll_ending", "《玩偶之家》娜拉出走的开放式结局", 5, SUBJECT, G10, 140004),
    (140074, "chn_x2_point_mina_image", "《迷娘（之一）》迷娘形象与对意大利南方的向往", 6, SUBJECT, G10, 140004),
    (140075, "chn_x2_point_mina_refrain", "《迷娘（之一）》复沓句式与民歌风韵", 7, SUBJECT, G10, 140004),
    (140076, "chn_x2_point_ocean_symbol", "《致大海》自由主题与大海意象的象征", 8, SUBJECT, G10, 140004),
    (140077, "chn_x2_point_ocean_monologue", "《致大海》呼告与抒情主人公的精神独白", 9, SUBJECT, G10, 140004),
    (140078, "chn_x2_point_self_freeverse", "《自己之歌（节选）》惠特曼自由体与“自我”的扩张", 10, SUBJECT, G10, 140004),
    (140079, "chn_x2_point_self_catalog", "《自己之歌（节选）》列举式铺排与万物平等的民主精神", 11, SUBJECT, G10, 140004),
    (140080, "chn_x2_point_tree_image", "《树和天空》特朗斯特罗姆的意象并置与静观姿态", 12, SUBJECT, G10, 140004),
    (140081, "chn_x2_point_foreign_compare", "四首外国诗的抒情主体与意象方式比较", 13, SUBJECT, G10, 140004),

    # 古诗词诵读
    (140082, "chn_x2_point_yange_contrast", "《燕歌行并序》边塞征戍叙事与“战士军前半死生”的对比", 1, SUBJECT, G10, 140005),
    (140083, "chn_x2_point_yange_rhythm", "《燕歌行并序》七言歌行的声情与四句一转的章法", 2, SUBJECT, G10, 140005),
    (140084, "chn_x2_point_konghou_synesthesia", "《李凭箜篌引》通感与神话意象构筑的音乐境界", 3, SUBJECT, G10, 140005),
    (140085, "chn_x2_point_konghou_imagine", "《李凭箜篌引》“石破天惊逗秋雨”的想象与夸张", 4, SUBJECT, G10, 140005),
    (140086, "chn_x2_point_jinse_ambiguity", "《锦瑟》意象叠加与“此情可待成追忆”的多义性", 5, SUBJECT, G10, 140005),
    (140087, "chn_x2_point_jinse_structure", "《锦瑟》首联“无端”与尾联呼应的结构经营", 6, SUBJECT, G10, 140005),
    (140088, "chn_x2_point_shufen_anger", "《书愤》陆游“愤”的三层内涵与今昔对照", 7, SUBJECT, G10, 140005),
    (140089, "chn_x2_point_shufen_image", "《书愤》颔联“楼船夜雪瓜洲渡”的意象组合", 8, SUBJECT, G10, 140005),

    # 文言实词、特殊句式与古代文化常识
    (140090, "chn_x2_point_classical_word", "本册文言通假、古今异义与词类活用辨析", 1, SUBJECT, G10, 140006),
    (140091, "chn_x2_point_classical_pattern", "本册文言判断句、被动句与宾语前置句式", 2, SUBJECT, G10, 140006),
    (140092, "chn_x2_point_classical_culture", "史传文中的文化常识：官职、礼制与纪年", 3, SUBJECT, G10, 140006),

    # 论述类文本
    (140093, "chn_x2_point_argument_structure", "论述类文本的论点定位与论证结构梳理", 1, SUBJECT, G10, 140007),
    (140094, "chn_x2_point_argument_evidence", "论据类型（事实、引用、对比）与论证效果分析", 2, SUBJECT, G10, 140007),

    # 叙事类文本
    (140095, "chn_x2_point_narrative_figure", "小说与报告文学中人物形象的细节分析", 1, SUBJECT, G10, 140008),
    (140096, "chn_x2_point_narrative_view", "叙事视角、场景转换与情节节奏的表达功能", 2, SUBJECT, G10, 140008),

    # 语言积累运用
    (140097, "chn_x2_point_recitation", "本册名句默写范围与易错字形整理", 1, SUBJECT, G10, 140009),

    # 单元研习任务与读写转化
    (140098, "chn_x2_point_task_note", "单元研习任务：理论文章的读书笔记与观点摘录", 1, SUBJECT, G10, 140010),
    (140099, "chn_x2_point_task_review", "文学短评与比较阅读：戏剧冲突与史论逻辑的写作", 2, SUBJECT, G10, 140010),
)

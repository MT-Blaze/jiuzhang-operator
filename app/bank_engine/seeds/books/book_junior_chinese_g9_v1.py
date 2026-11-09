"""统编版（2016）初中语文九年级上册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G9 = 9
BOOK_ID = 1305

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版九年级语文上册",
    "jchn_g9a",
    5,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (130501, "第一单元 活动·探究（诗歌）", "jchn_g9a_u01", 1, BOOK_ID, None),
    (130502, "第二单元 思辨性阅读", "jchn_g9a_u02", 2, BOOK_ID, None),
    (130503, "第三单元 文言文", "jchn_g9a_u03", 3, BOOK_ID, None),
    (130504, "第四单元 小说", "jchn_g9a_u04", 4, BOOK_ID, None),
    (130505, "第五单元 议论性文章", "jchn_g9a_u05", 5, BOOK_ID, None),
    (130506, "第六单元 古典小说", "jchn_g9a_u06", 6, BOOK_ID, None),

    # 第一单元 活动·探究（诗歌）
    (130511, "第1课 沁园春·雪", "jchn_g9a_l01", 1, BOOK_ID, 130501),
    (130512, "第2课 我爱这土地", "jchn_g9a_l02", 2, BOOK_ID, 130501),
    (130513, "第3课 乡愁", "jchn_g9a_l03", 3, BOOK_ID, 130501),
    (130514, "第4课 你是人间的四月天", "jchn_g9a_l04", 4, BOOK_ID, 130501),
    (130515, "第5课 我看", "jchn_g9a_l05", 5, BOOK_ID, 130501),

    # 第二单元 思辨性阅读
    (130516, "第6课 敬业与乐业", "jchn_g9a_l06", 1, BOOK_ID, 130502),
    (130517, "第7课 就英法联军远征中国致巴特勒上尉的信", "jchn_g9a_l07", 2, BOOK_ID, 130502),
    (130518, "第8课 论教养", "jchn_g9a_l08", 3, BOOK_ID, 130502),
    (130519, "第9课 精神的三间小屋", "jchn_g9a_l09", 4, BOOK_ID, 130502),

    # 第三单元 文言文
    (130520, "第10课 岳阳楼记", "jchn_g9a_l10", 1, BOOK_ID, 130503),
    (130521, "第11课 醉翁亭记", "jchn_g9a_l11", 2, BOOK_ID, 130503),
    (130522, "第12课 湖心亭看雪", "jchn_g9a_l12", 3, BOOK_ID, 130503),
    (130523, "第13课 诗词三首（行路难（其一）／酬乐天扬州初逢席上见赠／水调歌头·明月几时有）", "jchn_g9a_l13", 4, BOOK_ID, 130503),

    # 第四单元 小说
    (130524, "第14课 故乡", "jchn_g9a_l14", 1, BOOK_ID, 130504),
    (130525, "第15课 我的叔叔于勒", "jchn_g9a_l15", 2, BOOK_ID, 130504),
    (130526, "第16课 孤独之旅", "jchn_g9a_l16", 3, BOOK_ID, 130504),

    # 第五单元 议论性文章
    (130527, "第17课 中国人失掉自信力了吗", "jchn_g9a_l17", 1, BOOK_ID, 130505),
    (130528, "第18课 怀疑与学问", "jchn_g9a_l18", 2, BOOK_ID, 130505),
    (130529, "第19课 谈创造性思维", "jchn_g9a_l19", 3, BOOK_ID, 130505),
    (130530, "第20课 创造宣言", "jchn_g9a_l20", 4, BOOK_ID, 130505),

    # 第六单元 古典小说
    (130531, "第21课 智取生辰纲", "jchn_g9a_l21", 1, BOOK_ID, 130506),
    (130532, "第22课 范进中举", "jchn_g9a_l22", 2, BOOK_ID, 130506),
    (130533, "第23课 三顾茅庐", "jchn_g9a_l23", 3, BOOK_ID, 130506),
    (130534, "第24课 刘姥姥进大观园", "jchn_g9a_l24", 4, BOOK_ID, 130506),

    # 名著导读与课外古诗词诵读（单列）
    (130541, "名著导读《艾青诗选》：如何读诗", "jchn_g9a_l25", 7, BOOK_ID, None),
    (130542, "名著导读《水浒传》：古典小说的阅读", "jchn_g9a_l26", 8, BOOK_ID, None),
    (130543, "课外古诗词诵读（一）：月夜忆舍弟／长沙过贾谊宅／左迁至蓝关示侄孙湘／商山早行", "jchn_g9a_l27", 9, BOOK_ID, None),
    (130544, "课外古诗词诵读（二）：咸阳城东楼／无题／行香子·树绕村庄／丑奴儿·书博山道中壁", "jchn_g9a_l28", 10, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / parent_id
# 205001-205009 为册域层，205011-205091 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (205001, "jchn_g9a_domain_poetry", "初中九上·诗歌鉴赏与活动探究", 1, SUBJECT, None),
    (205002, "jchn_g9a_domain_speculative", "初中九上·思辨性阅读与说理", 2, SUBJECT, None),
    (205003, "jchn_g9a_domain_classical", "初中九上·文言文阅读", 3, SUBJECT, None),
    (205004, "jchn_g9a_domain_ancient_poem", "初中九上·古代诗词鉴赏", 4, SUBJECT, None),
    (205005, "jchn_g9a_domain_fiction", "初中九上·小说阅读与叙事", 5, SUBJECT, None),
    (205006, "jchn_g9a_domain_argument", "初中九上·议论性文章阅读", 6, SUBJECT, None),
    (205007, "jchn_g9a_domain_classic_novel", "初中九上·古典小说阅读", 7, SUBJECT, None),
    (205008, "jchn_g9a_domain_classics", "初中九上·名著阅读", 8, SUBJECT, None),
    (205009, "jchn_g9a_domain_writing", "初中九上·写作与语言运用", 9, SUBJECT, None),

    # 诗歌鉴赏与活动探究
    (205011, "jchn_g9a_point_poem_qinyuan_structure", "《沁园春·雪》上阕写景、下阕论史的结构", 1, SUBJECT, 205001),
    (205012, "jchn_g9a_point_poem_qinyuan_dynamic", "《沁园春·雪》“山舞银蛇，原驰蜡象”的化静为动", 2, SUBJECT, 205001),
    (205013, "jchn_g9a_point_poem_qinyuan_theme", "《沁园春·雪》“俱往矣”的豪迈与人民史观", 3, SUBJECT, 205001),
    (205014, "jchn_g9a_point_poem_land_hypothesis", "《我爱这土地》以鸟自比的假设与象征", 4, SUBJECT, 205001),
    (205015, "jchn_g9a_point_poem_land_tears", "《我爱这土地》“常含泪水”的直抒胸臆", 5, SUBJECT, 205001),
    (205016, "jchn_g9a_point_poem_xiangchou_images", "《乡愁》按时间推进的邮票、船票、坟墓、海峡四个意象", 6, SUBJECT, 205001),
    (205017, "jchn_g9a_point_poem_xiangchou_repetition", "《乡愁》重章叠句与“小小”“窄窄”等叠词的音韵", 7, SUBJECT, 205001),
    (205018, "jchn_g9a_point_poem_april_images", "《你是人间的四月天》的春日意象群与“你是”呼告", 8, SUBJECT, 205001),
    (205019, "jchn_g9a_point_poem_woqu", "《我看》由自然之景走向生命哲思的层进", 9, SUBJECT, 205001),
    (205020, "jchn_g9a_point_poem_recite", "诗歌朗诵：重音、停连、语气与节奏的设计", 10, SUBJECT, 205001),
    (205021, "jchn_g9a_point_poem_create", "活动·探究：尝试创作诗歌的意象选择与分行", 11, SUBJECT, 205001),

    # 思辨性阅读与说理
    (205022, "jchn_g9a_point_spec_jingye_thesis", "《敬业与乐业》“敬业乐业”的中心论点与总分总结构", 1, SUBJECT, 205002),
    (205023, "jchn_g9a_point_spec_jingye_methods", "《敬业与乐业》道理论证与百丈禅师、佝偻丈人等事例", 2, SUBJECT, 205002),
    (205024, "jchn_g9a_point_spec_jingye_language", "《敬业与乐业》演讲口语特点与“不二法门”“强聒不舍”", 3, SUBJECT, 205002),
    (205025, "jchn_g9a_point_spec_hugo_irony", "《就英法联军远征中国致巴特勒上尉的信》的反语与讽刺", 4, SUBJECT, 205002),
    (205026, "jchn_g9a_point_spec_hugo_value", "《就英法联军远征中国致巴特勒上尉的信》对圆明园艺术价值的评价", 5, SUBJECT, 205002),
    (205027, "jchn_g9a_point_spec_jiaoyang_contrast", "《论教养》“教养”的内涵与正反对比论证", 6, SUBJECT, 205002),
    (205028, "jchn_g9a_point_spec_jiaoyang_order", "《论教养》由现象到本质的递进式说理", 7, SUBJECT, 205002),
    (205029, "jchn_g9a_point_spec_xiaowu_metaphor", "《精神的三间小屋》比喻论证与“三间小屋”的象征义", 8, SUBJECT, 205002),
    (205030, "jchn_g9a_point_spec_xiaowu_structure", "《精神的三间小屋》层层推进的结构与人生思考", 9, SUBJECT, 205002),

    # 文言文阅读
    (205031, "jchn_g9a_point_cls_yueyang_contrast", "《岳阳楼记》览物之情与“古仁人之心”的对比", 1, SUBJECT, 205003),
    (205032, "jchn_g9a_point_cls_yueyang_ideal", "《岳阳楼记》“先天下之忧而忧，后天下之乐而乐”的抱负", 2, SUBJECT, 205003),
    (205033, "jchn_g9a_point_cls_yueyang_form", "《岳阳楼记》骈散结合与叙事、写景、议论的结构", 3, SUBJECT, 205003),
    (205034, "jchn_g9a_point_cls_zuiweng_joy", "《醉翁亭记》“乐”字贯穿全文的四层乐趣", 4, SUBJECT, 205003),
    (205035, "jchn_g9a_point_cls_zuiweng_language", "《醉翁亭记》骈散相间与“也”字句的从容语调", 5, SUBJECT, 205003),
    (205036, "jchn_g9a_point_cls_zuiweng_people", "《醉翁亭记》“与民同乐”的政治理想", 6, SUBJECT, 205003),
    (205037, "jchn_g9a_point_cls_huxinting_baomiao", "《湖心亭看雪》白描与“一痕、一点、一芥、两三粒”的量词", 7, SUBJECT, 205003),
    (205038, "jchn_g9a_point_cls_huxinting_chi", "《湖心亭看雪》“痴”字品评与故国之思", 8, SUBJECT, 205003),
    (205039, "jchn_g9a_point_cls_words_polysemy", "文言实词：谪、属、具、微、翳、酣等一词多义", 9, SUBJECT, 205003),
    (205040, "jchn_g9a_point_cls_sentence_types", "文言句式：判断句、倒装句与省略句的辨析", 10, SUBJECT, 205003),

    # 古代诗词鉴赏
    (205041, "jchn_g9a_point_poem_xinglu_symbol", "《行路难（其一）》“冰塞川”“雪满山”的象征与情感起伏", 1, SUBJECT, 205004),
    (205042, "jchn_g9a_point_poem_xinglu_confidence", "《行路难（其一）》“长风破浪会有时”的乐观自信", 2, SUBJECT, 205004),
    (205043, "jchn_g9a_point_poem_choule_tian_philosophy", "《酬乐天扬州初逢席上见赠》“沉舟侧畔千帆过”的哲理", 3, SUBJECT, 205004),
    (205044, "jchn_g9a_point_poem_shuidiao_open", "《水调歌头·明月几时有》“千里共婵娟”的旷达", 4, SUBJECT, 205004),
    (205045, "jchn_g9a_point_poem_shuidiao_structure", "《水调歌头》上阕问天、下阕问月的结构", 5, SUBJECT, 205004),
    (205046, "jchn_g9a_point_poem_reading1", "课外古诗词（一）：月夜忆舍弟／长沙过贾谊宅／左迁至蓝关示侄孙湘／商山早行", 6, SUBJECT, 205004),
    (205047, "jchn_g9a_point_poem_reading2", "课外古诗词（二）：咸阳城东楼／无题／行香子·树绕村庄／丑奴儿·书博山道中壁", 7, SUBJECT, 205004),
    (205048, "jchn_g9a_point_poem_appreciation", "古诗词鉴赏方法：意象、意境与炼字", 8, SUBJECT, 205004),

    # 小说阅读与叙事
    (205049, "jchn_g9a_point_fic_guxiang_frame", "《故乡》“回乡—离乡”的叙事框架与“变化”主题", 1, SUBJECT, 205005),
    (205050, "jchn_g9a_point_fic_guxiang_figures", "《故乡》闰土、杨二嫂前后对比与人物悲剧", 2, SUBJECT, 205005),
    (205051, "jchn_g9a_point_fic_guxiang_ending", "《故乡》结尾“走的人多了，也便成了路”的哲理", 3, SUBJECT, 205005),
    (205052, "jchn_g9a_point_fic_yule_couple", "《我的叔叔于勒》菲利普夫妇态度前后变化的对比", 4, SUBJECT, 205005),
    (205053, "jchn_g9a_point_fic_yule_viewpoint", "《我的叔叔于勒》“我”的叙事视角与金钱关系批判", 5, SUBJECT, 205005),
    (205054, "jchn_g9a_point_fic_gudu_growth", "《孤独之旅》杜小康的成长与景物描写的烘托", 6, SUBJECT, 205005),
    (205055, "jchn_g9a_point_fic_gudu_psychology", "《孤独之旅》“孤独”的心理刻画与暴风雨中的蜕变", 7, SUBJECT, 205005),
    (205056, "jchn_g9a_point_fic_elements", "小说三要素：人物、情节、环境与主题的关系", 8, SUBJECT, 205005),
    (205057, "jchn_g9a_point_fic_viewpoint", "小说叙事视角：第一人称与第三人称的表达效果", 9, SUBJECT, 205005),

    # 议论性文章阅读
    (205058, "jchn_g9a_point_arg_zixin_refute", "《中国人失掉自信力了吗》树靶、批驳、立论的驳论结构", 1, SUBJECT, 205006),
    (205059, "jchn_g9a_point_arg_zixin_backbone", "《中国人失掉自信力了吗》“中国的脊梁”与比喻论证", 2, SUBJECT, 205006),
    (205060, "jchn_g9a_point_arg_huaiyi_thesis", "《怀疑与学问》“治学必须有怀疑精神”的中心论点", 3, SUBJECT, 205006),
    (205061, "jchn_g9a_point_arg_huaiyi_methods", "《怀疑与学问》举例论证与道理论证的结合", 4, SUBJECT, 205006),
    (205062, "jchn_g9a_point_arg_creative_answer", "《谈创造性思维》“正确答案不止一个”的思维导向", 5, SUBJECT, 205006),
    (205063, "jchn_g9a_point_arg_creative_factors", "《谈创造性思维》创造性思维的要素与论证层次", 6, SUBJECT, 205006),
    (205064, "jchn_g9a_point_arg_declaration_parallel", "《创造宣言》“处处是创造之地”的排比与号召", 7, SUBJECT, 205006),
    (205065, "jchn_g9a_point_arg_methods", "议论文论证方法：举例、道理、对比、比喻、引用", 8, SUBJECT, 205006),
    (205066, "jchn_g9a_point_arg_structure", "议论文结构：提出问题、分析问题、解决问题", 9, SUBJECT, 205006),

    # 古典小说阅读
    (205067, "jchn_g9a_point_cnovel_shengchen_dual", "《智取生辰纲》“智”与“力”的较量及双线叙事", 1, SUBJECT, 205007),
    (205068, "jchn_g9a_point_cnovel_shengchen_weather", "《智取生辰纲》天气与环境描写在情节中的作用", 2, SUBJECT, 205007),
    (205069, "jchn_g9a_point_cnovel_shengchen_figures", "《智取生辰纲》杨志与吴用的人物形象对比", 3, SUBJECT, 205007),
    (205070, "jchn_g9a_point_cnovel_fanjin_change", "《范进中举》中举前后境遇变化与世态炎凉", 4, SUBJECT, 205007),
    (205071, "jchn_g9a_point_cnovel_fanjin_satire", "《范进中举》的夸张讽刺与胡屠户形象", 5, SUBJECT, 205007),
    (205072, "jchn_g9a_point_cnovel_sangu_layers", "《三顾茅庐》“三顾”的层次递进与刘备的求贤诚意", 6, SUBJECT, 205007),
    (205073, "jchn_g9a_point_cnovel_sangu_foreshadow", "《三顾茅庐》诸葛亮出场前的铺垫与侧面烘托", 7, SUBJECT, 205007),
    (205074, "jchn_g9a_point_cnovel_liulaolao_contrast", "《刘姥姥进大观园》以乡村视角对照贾府繁华", 8, SUBJECT, 205007),
    (205075, "jchn_g9a_point_cnovel_liulaolao_comedy", "《刘姥姥进大观园》笑剧场面与人物群像刻画", 9, SUBJECT, 205007),
    (205076, "jchn_g9a_point_cnovel_zhanghui", "古典白话小说：章回体、回目与说书人痕迹", 10, SUBJECT, 205007),

    # 名著阅读
    (205077, "jchn_g9a_point_classic_aiqing_images", "《艾青诗选》“土地”与“太阳”的核心意象", 1, SUBJECT, 205008),
    (205078, "jchn_g9a_point_classic_aiqing_tone", "《艾青诗选》忧郁基调与深沉的爱国情", 2, SUBJECT, 205008),
    (205079, "jchn_g9a_point_classic_aiqing_method", "《艾青诗选》如何读诗：意象、形式与情感", 3, SUBJECT, 205008),
    (205080, "jchn_g9a_point_classic_shuihu_theme", "《水浒传》“官逼民反”的主题与梁山聚义", 4, SUBJECT, 205008),
    (205081, "jchn_g9a_point_classic_shuihu_figures", "《水浒传》林冲、武松、鲁智深的性格塑造", 5, SUBJECT, 205008),
    (205082, "jchn_g9a_point_classic_shuihu_method", "《水浒传》链式结构与回目提示的阅读策略", 6, SUBJECT, 205008),

    # 写作与语言运用
    (205083, "jchn_g9a_point_write_thesis", "观点要明确：提炼中心论点与拟写标题", 1, SUBJECT, 205009),
    (205084, "jchn_g9a_point_write_evidence", "议论要言之有据：论据的选择与剪裁", 2, SUBJECT, 205009),
    (205085, "jchn_g9a_point_write_reasoning", "论证要合理：论证结构与逻辑严密", 3, SUBJECT, 205009),
    (205086, "jchn_g9a_point_write_abridge", "学习缩写：保留主干与概括要点", 4, SUBJECT, 205009),
    (205087, "jchn_g9a_point_write_rewrite", "学习改写：文体转换与叙述视角改写", 5, SUBJECT, 205009),
    (205088, "jchn_g9a_point_lang_pinyin", "九上字音字形：妖娆、风骚、亵渎、聒噪、诓骗", 6, SUBJECT, 205009),
    (205089, "jchn_g9a_point_lang_idiom", "成语积累：断章取义、强聒不舍、自吹自擂、前仆后继", 7, SUBJECT, 205009),
    (205090, "jchn_g9a_point_lang_sentence", "病句辨析：搭配不当与成分残缺", 8, SUBJECT, 205009),
    (205091, "jchn_g9a_point_lang_activity", "综合性学习“君子自强不息”与“走进小说天地”", 9, SUBJECT, 205009),
)

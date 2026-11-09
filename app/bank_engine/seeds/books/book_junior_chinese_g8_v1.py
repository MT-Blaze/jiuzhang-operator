"""统编版（2016）初中语文八年级上册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G8 = 8
BOOK_ID = 1303

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版八年级语文上册",
    "jchn_g8a",
    3,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (130301, "第一单元 新闻阅读（活动·探究）", "jchn_g8a_u01", 1, BOOK_ID, None),
    (130302, "第二单元 生活记忆", "jchn_g8a_u02", 2, BOOK_ID, None),
    (130303, "第三单元 山川美景", "jchn_g8a_u03", 3, BOOK_ID, None),
    (130304, "第四单元 情感哲思", "jchn_g8a_u04", 4, BOOK_ID, None),
    (130305, "第五单元 文明印记", "jchn_g8a_u05", 5, BOOK_ID, None),
    (130306, "第六单元 情操志趣", "jchn_g8a_u06", 6, BOOK_ID, None),

    # 第一单元 新闻阅读
    (130311, "第1课 消息二则（我三十万大军胜利南渡长江／人民解放军百万大军横渡长江）", "jchn_g8a_l01", 1, BOOK_ID, 130301),
    (130312, "第2课 首届诺贝尔奖颁发", "jchn_g8a_l02", 2, BOOK_ID, 130301),
    (130313, "第3课 “飞天”凌空——跳水姑娘吕伟夺魁记", "jchn_g8a_l03", 3, BOOK_ID, 130301),
    (130314, "第4课 一着惊海天——目击我国航母舰载战斗机首架次成功着舰", "jchn_g8a_l04", 4, BOOK_ID, 130301),

    # 第二单元 生活记忆
    (130315, "第5课 藤野先生", "jchn_g8a_l05", 1, BOOK_ID, 130302),
    (130316, "第6课 回忆我的母亲", "jchn_g8a_l06", 2, BOOK_ID, 130302),
    (130317, "第7课 列夫·托尔斯泰", "jchn_g8a_l07", 3, BOOK_ID, 130302),
    (130318, "第8课 美丽的颜色", "jchn_g8a_l08", 4, BOOK_ID, 130302),

    # 第三单元 山川美景与名著、诵读
    (130319, "第9课 三峡", "jchn_g8a_l09", 1, BOOK_ID, 130303),
    (130320, "第10课 短文两篇（答谢中书书／记承天寺夜游）", "jchn_g8a_l10", 2, BOOK_ID, 130303),
    (130321, "第11课 与朱元思书", "jchn_g8a_l11", 3, BOOK_ID, 130303),
    (130322, "第12课 唐诗五首（野望／黄鹤楼／使至塞上／渡荆门送别／钱塘湖春行）", "jchn_g8a_l12", 4, BOOK_ID, 130303),
    (130323, "名著导读《红星照耀中国》：纪实作品的阅读", "jchn_g8a_l13", 5, BOOK_ID, 130303),
    (130324, "课外古诗词诵读（一）：庭中有奇树／龟虽寿／赠从弟（其二）／梁甫行", "jchn_g8a_l14", 6, BOOK_ID, 130303),

    # 第四单元 情感哲思
    (130325, "第13课 背影", "jchn_g8a_l15", 1, BOOK_ID, 130304),
    (130326, "第14课 白杨礼赞", "jchn_g8a_l16", 2, BOOK_ID, 130304),
    (130327, "第15课 散文二篇（永久的生命／我为什么而活着）", "jchn_g8a_l17", 3, BOOK_ID, 130304),
    (130328, "第16课 昆明的雨", "jchn_g8a_l18", 4, BOOK_ID, 130304),

    # 第五单元 文明印记与名著
    (130329, "第17课 中国石拱桥", "jchn_g8a_l19", 1, BOOK_ID, 130305),
    (130330, "第18课 苏州园林", "jchn_g8a_l20", 2, BOOK_ID, 130305),
    (130331, "第19课 蝉", "jchn_g8a_l21", 3, BOOK_ID, 130305),
    (130332, "第20课 梦回繁华", "jchn_g8a_l22", 4, BOOK_ID, 130305),
    (130333, "名著导读《昆虫记》：科普作品的阅读", "jchn_g8a_l23", 5, BOOK_ID, 130305),

    # 第六单元 情操志趣与诵读
    (130334, "第21课 《孟子》二章（富贵不能淫／生于忧患，死于安乐）", "jchn_g8a_l24", 1, BOOK_ID, 130306),
    (130335, "第22课 愚公移山", "jchn_g8a_l25", 2, BOOK_ID, 130306),
    (130336, "第23课 周亚夫军细柳", "jchn_g8a_l26", 3, BOOK_ID, 130306),
    (130337, "第24课 诗词五首（饮酒（其五）／春望／雁门太守行／赤壁／渔家傲）", "jchn_g8a_l27", 4, BOOK_ID, 130306),
    (130338, "课外古诗词诵读（二）：浣溪沙／采桑子／相见欢／如梦令", "jchn_g8a_l28", 5, BOOK_ID, 130306),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 203001-203008 为册域层，203011-203099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (203001, "jchn_g8a_domain_news", "初中八上·新闻阅读与活动探究", 1, SUBJECT, G8, None),
    (203002, "jchn_g8a_domain_prose", "初中八上·写人记事与抒情散文", 2, SUBJECT, G8, None),
    (203003, "jchn_g8a_domain_classical", "初中八上·文言文阅读", 3, SUBJECT, G8, None),
    (203004, "jchn_g8a_domain_poetry", "初中八上·古代诗歌鉴赏", 4, SUBJECT, G8, None),
    (203005, "jchn_g8a_domain_expository", "初中八上·说明文阅读", 5, SUBJECT, G8, None),
    (203006, "jchn_g8a_domain_classics", "初中八上·名著阅读", 6, SUBJECT, G8, None),
    (203007, "jchn_g8a_domain_writing", "初中八上·写作训练", 7, SUBJECT, G8, None),
    (203008, "jchn_g8a_domain_language", "初中八上·语言运用与综合性学习", 8, SUBJECT, G8, None),

    # 新闻阅读与活动探究
    (203011, "jchn_g8a_point_news_structure", "消息的标题、导语、主体、背景与结语", 1, SUBJECT, G8, 203001),
    (203012, "jchn_g8a_point_news_dateline", "《消息二则》的电头与新闻时效性", 2, SUBJECT, G8, 203001),
    (203013, "jchn_g8a_point_news_language", "《消息二则》语言准确简洁与磅礴气势", 3, SUBJECT, G8, 203001),
    (203014, "jchn_g8a_point_news_elements", "新闻六要素与关键信息的快速提取", 4, SUBJECT, G8, 203001),
    (203015, "jchn_g8a_point_news_feature", "新闻特写《“飞天”凌空》的现场感与动作分解", 5, SUBJECT, G8, 203001),
    (203016, "jchn_g8a_point_news_report", "通讯《一着惊海天》的叙事节奏与细节还原", 6, SUBJECT, G8, 203001),
    (203017, "jchn_g8a_point_news_genre", "消息与通讯、特写的文体差异", 7, SUBJECT, G8, 203001),
    (203018, "jchn_g8a_point_news_title", "新闻标题的比较与拟写", 8, SUBJECT, G8, 203001),
    (203019, "jchn_g8a_point_news_interview", "新闻采访提纲的设计与提问技巧", 9, SUBJECT, G8, 203001),
    (203020, "jchn_g8a_point_news_inverted", "倒金字塔结构与新闻写作的客观立场", 10, SUBJECT, G8, 203001),

    # 写人记事与抒情散文
    (203021, "jchn_g8a_point_prose_tengye_lines", "《藤野先生》双线结构与鲁迅的爱国情感", 1, SUBJECT, G8, 203002),
    (203022, "jchn_g8a_point_prose_tengye_image", "《藤野先生》典型事例与人物形象刻画", 2, SUBJECT, G8, 203002),
    (203023, "jchn_g8a_point_prose_mother_event", "《回忆我的母亲》以事写人与平实质朴的语言", 3, SUBJECT, G8, 203002),
    (203024, "jchn_g8a_point_prose_mother_comment", "《回忆我的母亲》夹叙夹议与情感升华", 4, SUBJECT, G8, 203002),
    (203025, "jchn_g8a_point_prose_tolstoy_praise", "《列夫·托尔斯泰》欲扬先抑与外貌描写", 5, SUBJECT, G8, 203002),
    (203026, "jchn_g8a_point_prose_tolstoy_rhetoric", "《列夫·托尔斯泰》比喻夸张的语言张力", 6, SUBJECT, G8, 203002),
    (203027, "jchn_g8a_point_prose_curie_quote", "《美丽的颜色》引用传主原话与人物精神", 7, SUBJECT, G8, 203002),
    (203028, "jchn_g8a_point_prose_biography", "传记的真实性与文学性", 8, SUBJECT, G8, 203002),
    (203029, "jchn_g8a_point_prose_back_line", "《背影》以“背影”为线索与四次流泪", 9, SUBJECT, G8, 203002),
    (203030, "jchn_g8a_point_prose_back_verb", "《背影》白描手法与动词的锤炼", 10, SUBJECT, G8, 203002),
    (203031, "jchn_g8a_point_prose_poplar", "《白杨礼赞》象征手法与托物言志", 11, SUBJECT, G8, 203002),
    (203032, "jchn_g8a_point_prose_kunming", "《昆明的雨》形散神聚与凡人小事的韵味", 12, SUBJECT, G8, 203002),
    (203033, "jchn_g8a_point_prose_essays", "散文二篇的哲思：《永久的生命》《我为什么而活着》", 13, SUBJECT, G8, 203002),

    # 文言文阅读
    (203041, "jchn_g8a_point_cls_sanxia_order", "《三峡》四季景物的描写顺序与特点", 1, SUBJECT, G8, 203003),
    (203042, "jchn_g8a_point_cls_sanxia_form", "《三峡》骈散结合与夸张映衬", 2, SUBJECT, G8, 203003),
    (203043, "jchn_g8a_point_cls_xieshu", "《答谢中书书》总—分—总结构与山川之美", 3, SUBJECT, G8, 203003),
    (203044, "jchn_g8a_point_cls_chengtian", "《记承天寺夜游》“闲人”内涵与月色比喻", 4, SUBJECT, G8, 203003),
    (203045, "jchn_g8a_point_cls_zhuyuan", "《与朱元思书》奇山异水的分层描写", 5, SUBJECT, G8, 203003),
    (203046, "jchn_g8a_point_cls_zhuyuan_form", "《与朱元思书》骈文对偶与动静结合", 6, SUBJECT, G8, 203003),
    (203047, "jchn_g8a_point_cls_mencius", "《富贵不能淫》大丈夫的标准与对比论证", 7, SUBJECT, G8, 203003),
    (203048, "jchn_g8a_point_cls_hardship", "《生于忧患，死于安乐》举例论证与正反对比", 8, SUBJECT, G8, 203003),
    (203049, "jchn_g8a_point_cls_yugong_theme", "《愚公移山》对比衬托与寓言寓意", 9, SUBJECT, G8, 203003),
    (203050, "jchn_g8a_point_cls_yugong_words", "《愚公移山》实词：惩、迂、亡、厝、惠", 10, SUBJECT, G8, 203003),
    (203051, "jchn_g8a_point_cls_zhou_figure", "《周亚夫军细柳》正面描写与侧面烘托", 11, SUBJECT, G8, 203003),
    (203052, "jchn_g8a_point_cls_zhou_words", "《周亚夫军细柳》实词：军、劳、被、介胄、揖", 12, SUBJECT, G8, 203003),

    # 古代诗歌鉴赏
    (203056, "jchn_g8a_point_poem_yewang", "《野望》秋景中的彷徨与隐逸之思", 1, SUBJECT, G8, 203004),
    (203057, "jchn_g8a_point_poem_huanghelou", "《黄鹤楼》虚实结合与吊古思乡", 2, SUBJECT, G8, 203004),
    (203058, "jchn_g8a_point_poem_shizhisaishang", "《使至塞上》“大漠孤烟直”的画面与心境", 3, SUBJECT, G8, 203004),
    (203059, "jchn_g8a_point_poem_dujingmen", "《渡荆门送别》移步换景与“故乡水”", 4, SUBJECT, G8, 203004),
    (203060, "jchn_g8a_point_poem_qiantanghu", "《钱塘湖春行》早春意象与游踪线索", 5, SUBJECT, G8, 203004),
    (203061, "jchn_g8a_point_poem_tingzhong", "《庭中有奇树》折枝寄远与相思之情", 6, SUBJECT, G8, 203004),
    (203062, "jchn_g8a_point_poem_guisuisou", "《龟虽寿》老骥伏枥与积极进取的哲理", 7, SUBJECT, G8, 203004),
    (203063, "jchn_g8a_point_poem_zengcongdi", "《赠从弟（其二）》托物言志与松柏品格", 8, SUBJECT, G8, 203004),
    (203064, "jchn_g8a_point_poem_liangfuxing", "《梁甫行》白描手法与民生疾苦", 9, SUBJECT, G8, 203004),
    (203065, "jchn_g8a_point_poem_yinjiu", "《饮酒（其五）》“心远地自偏”与物我两忘", 10, SUBJECT, G8, 203004),
    (203066, "jchn_g8a_point_poem_chunwang", "《春望》意象组合与家国之痛", 11, SUBJECT, G8, 203004),
    (203067, "jchn_g8a_point_poem_yanmen", "《雁门太守行》色彩铺陈与战争场面", 12, SUBJECT, G8, 203004),
    (203068, "jchn_g8a_point_poem_chibi", "《赤壁》以小见大与咏史抒怀", 13, SUBJECT, G8, 203004),
    (203069, "jchn_g8a_point_poem_yujiaao", "《渔家傲》记梦与豪放词风", 14, SUBJECT, G8, 203004),
    (203070, "jchn_g8a_point_poem_chanting2", "课外古诗词诵读（二）：浣溪沙／采桑子／相见欢／如梦令", 15, SUBJECT, G8, 203004),

    # 说明文阅读
    (203072, "jchn_g8a_point_exp_arch_structure", "《中国石拱桥》说明对象与总分结构", 1, SUBJECT, G8, 203005),
    (203073, "jchn_g8a_point_exp_arch_methods", "《中国石拱桥》举例子、列数字等说明方法", 2, SUBJECT, G8, 203005),
    (203074, "jchn_g8a_point_exp_garden_structure", "《苏州园林》总说与分说的结构", 3, SUBJECT, G8, 203005),
    (203075, "jchn_g8a_point_exp_garden_language", "《苏州园林》摹状貌与语言的准确性", 4, SUBJECT, G8, 203005),
    (203076, "jchn_g8a_point_exp_cicada", "《蝉》科学观察与文艺性说明", 5, SUBJECT, G8, 203005),
    (203077, "jchn_g8a_point_exp_painting", "《梦回繁华》说明顺序与《清明上河图》", 6, SUBJECT, G8, 203005),
    (203078, "jchn_g8a_point_exp_order", "说明对象特征与时间、空间、逻辑顺序", 7, SUBJECT, G8, 203005),
    (203079, "jchn_g8a_point_exp_language", "说明文语言准确性与生动性的辨析", 8, SUBJECT, G8, 203005),

    # 名著阅读
    (203081, "jchn_g8a_point_classic_red_route", "《红星照耀中国》的采访路线与纪实立场", 1, SUBJECT, G8, 203006),
    (203082, "jchn_g8a_point_classic_red_figures", "《红星照耀中国》领袖人物群像与长征叙述", 2, SUBJECT, G8, 203006),
    (203083, "jchn_g8a_point_classic_insect_science", "《昆虫记》科学性与文学性的融合", 3, SUBJECT, G8, 203006),
    (203084, "jchn_g8a_point_classic_insect_world", "法布尔的观察精神与《昆虫记》的昆虫世界", 4, SUBJECT, G8, 203006),
    (203085, "jchn_g8a_point_classic_documentary", "纪实作品的阅读：梳理事实、辨识立场", 5, SUBJECT, G8, 203006),
    (203086, "jchn_g8a_point_classic_popular", "科普作品的阅读：科学概念与文学表达", 6, SUBJECT, G8, 203006),
    (203087, "jchn_g8a_point_classic_plan", "名著阅读的计划制定与读书笔记", 7, SUBJECT, G8, 203006),

    # 写作训练
    (203089, "jchn_g8a_point_write_biography", "学写传记：真实选材与典型事件", 1, SUBJECT, G8, 203007),
    (203090, "jchn_g8a_point_write_scenery", "学习描写景物：抓住特征与调动感官", 2, SUBJECT, G8, 203007),
    (203091, "jchn_g8a_point_write_coherence", "语言要连贯：话题统一与顺序合理", 3, SUBJECT, G8, 203007),
    (203092, "jchn_g8a_point_write_feature", "说明事物要抓住特征", 4, SUBJECT, G8, 203007),
    (203093, "jchn_g8a_point_write_propriety", "表达要得体：对象、场合与目的", 5, SUBJECT, G8, 203007),
    (203094, "jchn_g8a_point_write_revise", "作文审题立意与修改升格", 6, SUBJECT, G8, 203007),

    # 语言运用与综合性学习
    (203095, "jchn_g8a_point_lang_pinyin", "八上字音字形：溃退、锐不可当、屏息敛声", 1, SUBJECT, G8, 203008),
    (203096, "jchn_g8a_point_lang_idiom", "成语积累：藏污纳垢、鹤立鸡群、正襟危坐", 2, SUBJECT, G8, 203008),
    (203097, "jchn_g8a_point_lang_sentence", "病句辨析：成分残缺与搭配不当", 3, SUBJECT, G8, 203008),
    (203098, "jchn_g8a_point_lang_integrity", "综合性学习“人无信不立”与“我们的互联网时代”", 4, SUBJECT, G8, 203008),
    (203099, "jchn_g8a_point_lang_heritage", "综合性学习“身边的文化遗产”与口语交际", 5, SUBJECT, G8, 203008),
)

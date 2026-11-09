"""统编版（2016）初中语文七年级下册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G7 = 7
BOOK_ID = 1302

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版七年级语文下册",
    "jchn_g7b",
    2,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (130201, "第一单元 群星闪耀", "jchn_g7b_u01", 1, BOOK_ID, None),
    (130202, "第二单元 家国情怀", "jchn_g7b_u02", 2, BOOK_ID, None),
    (130203, "第三单元 凡人小事", "jchn_g7b_u03", 3, BOOK_ID, None),
    (130204, "第四单元 修身正己", "jchn_g7b_u04", 4, BOOK_ID, None),
    (130205, "第五单元 生活哲理", "jchn_g7b_u05", 5, BOOK_ID, None),
    (130206, "第六单元 科幻探险", "jchn_g7b_u06", 6, BOOK_ID, None),

    # 第一单元 课文
    (130211, "第1课 邓稼先", "jchn_g7b_l01", 1, BOOK_ID, 130201),
    (130212, "第2课 说和做——记闻一多先生言行片段", "jchn_g7b_l02", 2, BOOK_ID, 130201),
    (130213, "第3课 回忆鲁迅先生（节选）", "jchn_g7b_l03", 3, BOOK_ID, 130201),
    (130214, "第4课 孙权劝学", "jchn_g7b_l04", 4, BOOK_ID, 130201),

    # 第二单元 课文
    (130215, "第5课 黄河颂", "jchn_g7b_l05", 1, BOOK_ID, 130202),
    (130216, "第6课 老山界", "jchn_g7b_l06", 2, BOOK_ID, 130202),
    (130217, "第7课 谁是最可爱的人", "jchn_g7b_l07", 3, BOOK_ID, 130202),
    (130218, "第8课 土地的誓言", "jchn_g7b_l08", 4, BOOK_ID, 130202),
    (130219, "第9课 木兰诗", "jchn_g7b_l09", 5, BOOK_ID, 130202),

    # 第三单元 课文与名著、诵读
    (130220, "第10课 阿长与《山海经》", "jchn_g7b_l10", 1, BOOK_ID, 130203),
    (130221, "第11课 老王", "jchn_g7b_l11", 2, BOOK_ID, 130203),
    (130222, "第12课 台阶", "jchn_g7b_l12", 3, BOOK_ID, 130203),
    (130223, "第13课 卖油翁", "jchn_g7b_l13", 4, BOOK_ID, 130203),
    (130224, "名著导读《骆驼祥子》：圈点与批注", "jchn_g7b_l14", 5, BOOK_ID, 130203),
    (130225, "课外古诗词诵读（一）：竹里馆／春夜洛城闻笛／逢入京使／晚春", "jchn_g7b_l15", 6, BOOK_ID, 130203),

    # 第四单元 课文
    (130226, "第14课 叶圣陶先生二三事", "jchn_g7b_l16", 1, BOOK_ID, 130204),
    (130227, "第15课 驿路梨花", "jchn_g7b_l17", 2, BOOK_ID, 130204),
    (130228, "第16课 最苦与最乐", "jchn_g7b_l18", 3, BOOK_ID, 130204),
    (130229, "第17课 短文两篇（陋室铭／爱莲说）", "jchn_g7b_l19", 4, BOOK_ID, 130204),

    # 第五单元 课文
    (130230, "第18课 紫藤萝瀑布", "jchn_g7b_l20", 1, BOOK_ID, 130205),
    (130231, "第19课 一棵小桃树", "jchn_g7b_l21", 2, BOOK_ID, 130205),
    (130232, "第20课 外国诗二首（假如生活欺骗了你／未选择的路）", "jchn_g7b_l22", 3, BOOK_ID, 130205),
    (130233, "第21课 古代诗歌五首（登幽州台歌／望岳／登飞来峰／游山西村／己亥杂诗）", "jchn_g7b_l23", 4, BOOK_ID, 130205),

    # 第六单元 课文与名著、诵读
    (130234, "第22课 伟大的悲剧", "jchn_g7b_l24", 1, BOOK_ID, 130206),
    (130235, "第23课 太空一日", "jchn_g7b_l25", 2, BOOK_ID, 130206),
    (130236, "第24课 带上她的眼睛", "jchn_g7b_l26", 3, BOOK_ID, 130206),
    (130237, "第25课 活板", "jchn_g7b_l27", 4, BOOK_ID, 130206),
    (130238, "名著导读《海底两万里》：快速阅读", "jchn_g7b_l28", 5, BOOK_ID, 130206),
    (130239, "课外古诗词诵读（二）：泊秦淮／贾生／过松源晨炊漆公店／约客", "jchn_g7b_l29", 6, BOOK_ID, 130206),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 202001-202007 为册域层，202011-202097 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (202001, "jchn_g7b_domain_language", "初中七下·字词积累与语言运用", 1, SUBJECT, G7, None),
    (202002, "jchn_g7b_domain_modern", "初中七下·现代文阅读", 2, SUBJECT, G7, None),
    (202003, "jchn_g7b_domain_classical", "初中七下·文言文阅读", 3, SUBJECT, G7, None),
    (202004, "jchn_g7b_domain_poetry", "初中七下·古代诗歌鉴赏", 4, SUBJECT, G7, None),
    (202005, "jchn_g7b_domain_classics", "初中七下·名著阅读", 5, SUBJECT, G7, None),
    (202006, "jchn_g7b_domain_writing", "初中七下·写作训练", 6, SUBJECT, G7, None),
    (202007, "jchn_g7b_domain_scifi", "初中七下·科幻科普作品", 7, SUBJECT, G7, None),

    # 字词积累与语言运用
    (202011, "jchn_g7b_point_word_pinyin", "七下重点字音：元勋、选聘、挚友、殷红、锲而不舍", 1, SUBJECT, G7, 202001),
    (202012, "jchn_g7b_point_word_glyph", "七下重点字形：筹划、仰慕、家喻户晓、鲜为人知", 2, SUBJECT, G7, 202001),
    (202013, "jchn_g7b_point_word_polyphone", "多音字与形近字：殷红／殷切、斗笠／斗争、哽咽／咽下", 3, SUBJECT, G7, 202001),
    (202014, "jchn_g7b_point_word_idiom", "成语积累：鞠躬尽瘁、锋芒毕露、妇孺皆知、苛捐杂税", 4, SUBJECT, G7, 202001),
    (202015, "jchn_g7b_point_sentence_error", "病句辨析：成分残缺、搭配不当与语序不当", 5, SUBJECT, G7, 202001),
    (202016, "jchn_g7b_point_punctuation", "标点符号：引号、破折号与省略号的规范使用", 6, SUBJECT, G7, 202001),
    (202017, "jchn_g7b_point_activity_country", "综合性学习“天下国家”：爱国主题活动的策划与表达", 7, SUBJECT, G7, 202001),
    (202018, "jchn_g7b_point_activity_filial", "综合性学习“孝亲敬老，从我做起”：活动方案与口语交际", 8, SUBJECT, G7, 202001),
    (202019, "jchn_g7b_point_activity_life", "综合性学习“我的语文生活”：广告语、对联与用字规范", 9, SUBJECT, G7, 202001),

    # 现代文阅读
    (202021, "jchn_g7b_point_modern_deng_subtitle", "《邓稼先》小标题结构与对比手法的运用", 1, SUBJECT, G7, 202002),
    (202022, "jchn_g7b_point_modern_deng_spirit", "《邓稼先》中“民族感情”与人物精神的把握", 2, SUBJECT, G7, 202002),
    (202023, "jchn_g7b_point_modern_shuohezuo", "《说和做》选取言行片段刻画闻一多", 3, SUBJECT, G7, 202002),
    (202024, "jchn_g7b_point_modern_luxun", "《回忆鲁迅先生》生活细节中的鲁迅形象", 4, SUBJECT, G7, 202002),
    (202025, "jchn_g7b_point_modern_huanghe", "《黄河颂》歌词体式与反复呼告的抒情效果", 5, SUBJECT, G7, 202002),
    (202026, "jchn_g7b_point_modern_laoshanjie", "《老山界》翻山过程的叙事顺序与红军精神", 6, SUBJECT, G7, 202002),
    (202027, "jchn_g7b_point_modern_zuikeai", "《谁是最可爱的人》三个事例的选择与组合", 7, SUBJECT, G7, 202002),
    (202028, "jchn_g7b_point_modern_tudi", "《土地的誓言》呼告、排比与故土之恋", 8, SUBJECT, G7, 202002),
    (202029, "jchn_g7b_point_modern_achang", "《阿长与〈山海经〉》欲扬先抑与童年视角", 9, SUBJECT, G7, 202002),
    (202030, "jchn_g7b_point_modern_laowang", "《老王》结尾“愧怍”的多层意蕴", 10, SUBJECT, G7, 202002),
    (202031, "jchn_g7b_point_modern_taijie", "《台阶》父亲形象与细节描写", 11, SUBJECT, G7, 202002),
    (202032, "jchn_g7b_point_modern_yeshengtao", "《叶圣陶先生二三事》选材的“小”与“深”", 12, SUBJECT, G7, 202002),
    (202033, "jchn_g7b_point_modern_yilu", "《驿路梨花》悬念与误会的情节构思", 13, SUBJECT, G7, 202002),
    (202034, "jchn_g7b_point_modern_zuiku", "《最苦与最乐》对比论证与责任观", 14, SUBJECT, G7, 202002),
    (202035, "jchn_g7b_point_modern_ziteng", "《紫藤萝瀑布》由景入理与生命感悟", 15, SUBJECT, G7, 202002),
    (202036, "jchn_g7b_point_modern_xiaotao", "《一棵小桃树》托物言志与双线结构", 16, SUBJECT, G7, 202002),
    (202037, "jchn_g7b_point_modern_character", "记叙文人物形象分析的答题路径", 17, SUBJECT, G7, 202002),
    (202038, "jchn_g7b_point_modern_keysentence", "散文关键句子的含义与作用分析", 18, SUBJECT, G7, 202002),
    (202039, "jchn_g7b_point_modern_technique", "欲扬先抑、伏笔照应等表现手法的辨识", 19, SUBJECT, G7, 202002),
    (202040, "jchn_g7b_point_modern_setting", "环境描写的作用与叙事节奏", 20, SUBJECT, G7, 202002),

    # 文言文阅读
    (202042, "jchn_g7b_point_cls_sunquan_words", "《孙权劝学》实词：卿、孤、孰若、及", 1, SUBJECT, G7, 202003),
    (202043, "jchn_g7b_point_cls_sunquan_skill", "《孙权劝学》侧面烘托与“刮目相待”的启示", 2, SUBJECT, G7, 202003),
    (202044, "jchn_g7b_point_cls_maiyou_words", "《卖油翁》实词：矜、睨、颔、酌", 3, SUBJECT, G7, 202003),
    (202045, "jchn_g7b_point_cls_maiyou_theme", "《卖油翁》“熟能生巧”的寓意与对比手法", 4, SUBJECT, G7, 202003),
    (202046, "jchn_g7b_point_cls_loushi_theme", "《陋室铭》“斯是陋室，惟吾德馨”的托物言志", 5, SUBJECT, G7, 202003),
    (202047, "jchn_g7b_point_cls_loushi_form", "《陋室铭》骈散结合与比兴开篇", 6, SUBJECT, G7, 202003),
    (202048, "jchn_g7b_point_cls_lian_theme", "《爱莲说》托物言志与“出淤泥而不染”", 7, SUBJECT, G7, 202003),
    (202049, "jchn_g7b_point_cls_lian_contrast", "《爱莲说》正衬反衬与莲的君子品格", 8, SUBJECT, G7, 202003),
    (202050, "jchn_g7b_point_cls_huoban_order", "《活板》程序说明顺序：刻字、排版、印刷", 9, SUBJECT, G7, 202003),
    (202051, "jchn_g7b_point_cls_huoban_words", "《活板》实词：板、炀、砥、更互", 10, SUBJECT, G7, 202003),
    (202052, "jchn_g7b_point_cls_mulan_rhetoric", "《木兰诗》铺排、对偶与互文的运用", 11, SUBJECT, G7, 202003),
    (202053, "jchn_g7b_point_cls_mulan_image", "《木兰诗》木兰形象与北朝民歌特色", 12, SUBJECT, G7, 202003),
    (202054, "jchn_g7b_point_cls_function_words", "文言虚词“之、其、以、于”的常见用法", 13, SUBJECT, G7, 202003),
    (202055, "jchn_g7b_point_cls_translate", "文言翻译：留、替、调、补、删的落实", 14, SUBJECT, G7, 202003),

    # 古代诗歌鉴赏
    (202057, "jchn_g7b_point_poem_zhuli", "《竹里馆》以动衬静与诗人雅趣", 1, SUBJECT, G7, 202004),
    (202058, "jchn_g7b_point_poem_luocheng", "《春夜洛城闻笛》“折柳”与思乡之情", 2, SUBJECT, G7, 202004),
    (202059, "jchn_g7b_point_poem_fengru", "《逢入京使》口语化的传神细节", 3, SUBJECT, G7, 202004),
    (202060, "jchn_g7b_point_poem_wanchun", "《晚春》拟人手法与惜春哲理", 4, SUBJECT, G7, 202004),
    (202061, "jchn_g7b_point_poem_youzhou", "《登幽州台歌》时空对照与孤独感", 5, SUBJECT, G7, 202004),
    (202062, "jchn_g7b_point_poem_wangyue", "《望岳》“会当凌绝顶”的豪情与哲理", 6, SUBJECT, G7, 202004),
    (202063, "jchn_g7b_point_poem_feilai", "《登飞来峰》借景说理与政治抱负", 7, SUBJECT, G7, 202004),
    (202064, "jchn_g7b_point_poem_shanxi", "《游山西村》山重水复的理趣", 8, SUBJECT, G7, 202004),
    (202065, "jchn_g7b_point_poem_jihai", "《己亥杂诗（其五）》“落红”意象与奉献精神", 9, SUBJECT, G7, 202004),
    (202066, "jchn_g7b_point_poem_boqinhuai", "《泊秦淮》借古讽今与忧患意识", 10, SUBJECT, G7, 202004),
    (202067, "jchn_g7b_point_poem_jiasheng", "《贾生》托古讽今的讽喻手法", 11, SUBJECT, G7, 202004),
    (202068, "jchn_g7b_point_poem_guosongyuan", "《过松源晨炊漆公店》下山之难与人生哲理", 12, SUBJECT, G7, 202004),
    (202069, "jchn_g7b_point_poem_yueke", "《约客》细节描写与等待心境", 13, SUBJECT, G7, 202004),
    (202070, "jchn_g7b_point_poem_appreciate", "古诗鉴赏：意象、意境与情感基调的把握", 14, SUBJECT, G7, 202004),

    # 名著阅读
    (202072, "jchn_g7b_point_classic_xiangzi_plot", "《骆驼祥子》三起三落的情节脉络", 1, SUBJECT, G7, 202005),
    (202073, "jchn_g7b_point_classic_xiangzi_image", "祥子由勤劳到堕落的形象变化", 2, SUBJECT, G7, 202005),
    (202074, "jchn_g7b_point_classic_xiangzi_women", "《骆驼祥子》中虎妞与小福子的形象作用", 3, SUBJECT, G7, 202005),
    (202075, "jchn_g7b_point_classic_xiangzi_language", "《骆驼祥子》京味语言与旧北京社会图景", 4, SUBJECT, G7, 202005),
    (202076, "jchn_g7b_point_classic_annotation", "圈点与批注的阅读方法", 5, SUBJECT, G7, 202005),
    (202077, "jchn_g7b_point_classic_sea_route", "《海底两万里》航行路线与主要险情", 6, SUBJECT, G7, 202005),
    (202078, "jchn_g7b_point_classic_nemo", "尼摩船长形象的多面性", 7, SUBJECT, G7, 202005),
    (202079, "jchn_g7b_point_classic_sea_science", "《海底两万里》科学幻想与科学知识的融合", 8, SUBJECT, G7, 202005),
    (202080, "jchn_g7b_point_classic_fastread", "快速阅读的方法与要点", 9, SUBJECT, G7, 202005),

    # 写作训练
    (202082, "jchn_g7b_point_write_spirit", "写出人物的精神：以典型细节凸显内在品格", 1, SUBJECT, G7, 202006),
    (202083, "jchn_g7b_point_write_lyric", "学习抒情：直接抒情与间接抒情", 2, SUBJECT, G7, 202006),
    (202084, "jchn_g7b_point_write_detail", "抓住细节：让描写具体可感", 3, SUBJECT, G7, 202006),
    (202085, "jchn_g7b_point_write_material", "怎样选材：围绕中心取舍与详略安排", 4, SUBJECT, G7, 202006),
    (202086, "jchn_g7b_point_write_smooth", "文从字顺：语句衔接与修改润色", 5, SUBJECT, G7, 202006),
    (202087, "jchn_g7b_point_write_concise", "语言简明：去除冗余与消除歧义", 6, SUBJECT, G7, 202006),
    (202088, "jchn_g7b_point_write_upgrade", "作文升格：伏笔、照应与首尾呼应", 7, SUBJECT, G7, 202006),
    (202089, "jchn_g7b_point_write_title", "命题作文的审题与立意", 8, SUBJECT, G7, 202006),

    # 科幻科普作品
    (202091, "jchn_g7b_point_scifi_tragedy_truth", "《伟大的悲剧》传记的真实性与悲剧力量", 1, SUBJECT, G7, 202007),
    (202092, "jchn_g7b_point_scifi_tragedy_detail", "《伟大的悲剧》细节描写与人物心理", 2, SUBJECT, G7, 202007),
    (202093, "jchn_g7b_point_scifi_space", "《太空一日》航天员视角与科学精神", 3, SUBJECT, G7, 202007),
    (202094, "jchn_g7b_point_scifi_eyes", "《带上她的眼睛》科幻设定与人文关怀", 4, SUBJECT, G7, 202007),
    (202095, "jchn_g7b_point_scifi_reading", "科幻作品的阅读路径：设定、情节与主题", 5, SUBJECT, G7, 202007),
    (202096, "jchn_g7b_point_scifi_method", "说明方法辨识：举例子、列数字、作比较、打比方", 6, SUBJECT, G7, 202007),
    (202097, "jchn_g7b_point_scifi_language", "说明文语言的准确性与信息筛选", 7, SUBJECT, G7, 202007),
)

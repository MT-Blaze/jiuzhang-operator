"""统编版（2016）初中语文七年级上册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G7 = 7
BOOK_ID = 1301

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版七年级语文上册",
    "jchn_g7a",
    1,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (130101, "第一单元 四季美景", "jchn_g7a_u01", 1, BOOK_ID, None),
    (130102, "第二单元 至爱亲情", "jchn_g7a_u02", 2, BOOK_ID, None),
    (130103, "第三单元 学习生活", "jchn_g7a_u03", 3, BOOK_ID, None),
    (130104, "第四单元 人生之舟", "jchn_g7a_u04", 4, BOOK_ID, None),
    (130105, "第五单元 动物与人", "jchn_g7a_u05", 5, BOOK_ID, None),
    (130106, "第六单元 想象之翼", "jchn_g7a_u06", 6, BOOK_ID, None),

    # 第一单元 课文
    (130111, "第1课 春", "jchn_g7a_l01", 1, BOOK_ID, 130101),
    (130112, "第2课 济南的冬天", "jchn_g7a_l02", 2, BOOK_ID, 130101),
    (130113, "第3课 雨的四季", "jchn_g7a_l03", 3, BOOK_ID, 130101),
    (130114, "第4课 古代诗歌四首（观沧海／闻王昌龄左迁龙标遥有此寄／次北固山下／天净沙·秋思）", "jchn_g7a_l04", 4, BOOK_ID, 130101),

    # 第二单元 课文
    (130115, "第5课 秋天的怀念", "jchn_g7a_l05", 1, BOOK_ID, 130102),
    (130116, "第6课 散步", "jchn_g7a_l06", 2, BOOK_ID, 130102),
    (130117, "第7课 散文诗二首（金色花／荷叶·母亲）", "jchn_g7a_l07", 3, BOOK_ID, 130102),
    (130118, "第8课 《世说新语》二则（咏雪／陈太丘与友期行）", "jchn_g7a_l08", 4, BOOK_ID, 130102),

    # 第三单元 课文与名著、诵读
    (130119, "第9课 从百草园到三味书屋", "jchn_g7a_l09", 1, BOOK_ID, 130103),
    (130120, "第10课 再塑生命的人", "jchn_g7a_l10", 2, BOOK_ID, 130103),
    (130121, "第11课 《论语》十二章", "jchn_g7a_l11", 3, BOOK_ID, 130103),
    (130122, "名著导读《朝花夕拾》：消除与经典的隔膜", "jchn_g7a_l12", 4, BOOK_ID, 130103),
    (130123, "课外古诗词诵读（一）：峨眉山月歌／江南逢李龟年／行军九日思长安故园／夜上受降城闻笛", "jchn_g7a_l13", 5, BOOK_ID, 130103),

    # 第四单元 课文
    (130124, "第12课 纪念白求恩", "jchn_g7a_l14", 1, BOOK_ID, 130104),
    (130125, "第13课 植树的牧羊人", "jchn_g7a_l15", 2, BOOK_ID, 130104),
    (130126, "第14课 走一步，再走一步", "jchn_g7a_l16", 3, BOOK_ID, 130104),
    (130127, "第15课 诫子书", "jchn_g7a_l17", 4, BOOK_ID, 130104),

    # 第五单元 课文
    (130128, "第16课 猫", "jchn_g7a_l18", 1, BOOK_ID, 130105),
    (130129, "第17课 动物笑谈", "jchn_g7a_l19", 2, BOOK_ID, 130105),
    (130130, "第18课 狼", "jchn_g7a_l20", 3, BOOK_ID, 130105),

    # 第六单元 课文与名著、诵读
    (130131, "第19课 皇帝的新装", "jchn_g7a_l21", 1, BOOK_ID, 130106),
    (130132, "第20课 天上的街市", "jchn_g7a_l22", 2, BOOK_ID, 130106),
    (130133, "第21课 女娲造人", "jchn_g7a_l23", 3, BOOK_ID, 130106),
    (130134, "第22课 寓言四则（赫耳墨斯和雕像者／蚊子和狮子／穿井得一人／杞人忧天）", "jchn_g7a_l24", 4, BOOK_ID, 130106),
    (130135, "名著导读《西游记》：精读和跳读", "jchn_g7a_l25", 5, BOOK_ID, 130106),
    (130136, "课外古诗词诵读（二）：秋词（其一）／夜雨寄北／十一月四日风雨大作（其二）／潼关", "jchn_g7a_l26", 6, BOOK_ID, 130106),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 201001-201009 为册域层，201010-201099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (201001, "jchn_g7a_domain_readaloud", "初中七上·朗读与字词积累", 1, SUBJECT, G7, None),
    (201002, "jchn_g7a_domain_prose", "初中七上·现代散文阅读", 2, SUBJECT, G7, None),
    (201003, "jchn_g7a_domain_narrative", "初中七上·记叙文阅读与写人记事", 3, SUBJECT, G7, None),
    (201004, "jchn_g7a_domain_classical", "初中七上·文言文阅读", 4, SUBJECT, G7, None),
    (201005, "jchn_g7a_domain_poetry", "初中七上·古代诗歌鉴赏", 5, SUBJECT, G7, None),
    (201006, "jchn_g7a_domain_writing", "初中七上·写作训练", 6, SUBJECT, G7, None),
    (201007, "jchn_g7a_domain_classics", "初中七上·名著阅读", 7, SUBJECT, G7, None),
    (201008, "jchn_g7a_domain_language", "初中七上·语言运用与综合性学习", 8, SUBJECT, G7, None),
    (201009, "jchn_g7a_domain_imagination", "初中七上·童话寓言与想象作品", 9, SUBJECT, G7, None),

    # 朗读与字词积累
    (201010, "jchn_g7a_point_read_chun", "《春》朗读中的重音与停连设计", 1, SUBJECT, G7, 201001),
    (201011, "jchn_g7a_point_read_jinan", "《济南的冬天》舒缓语调与语气把握", 2, SUBJECT, G7, 201001),
    (201012, "jchn_g7a_point_word_pinyin", "七上重点字音：酝酿、抖擞、贮蓄、粗犷", 3, SUBJECT, G7, 201001),
    (201013, "jchn_g7a_point_word_glyph", "七上重点字形：分歧、憔悴、絮叨、沉寂", 4, SUBJECT, G7, 201001),
    (201014, "jchn_g7a_point_word_polyphone", "多音字与形近字辨析：应和／和平、棱镜／棱角", 5, SUBJECT, G7, 201001),
    (201015, "jchn_g7a_point_word_color", "词语感情色彩与语境义：花枝招展、咄咄逼人", 6, SUBJECT, G7, 201001),
    (201016, "jchn_g7a_point_read_four", "朗读四要素：停连、重音、语气、节奏的综合运用", 7, SUBJECT, G7, 201001),

    # 现代散文阅读
    (201020, "jchn_g7a_point_prose_chun", "《春》中比喻与拟人的层次化景物描写", 1, SUBJECT, G7, 201002),
    (201021, "jchn_g7a_point_prose_jinan", "《济南的冬天》山水意象与“温晴”基调", 2, SUBJECT, G7, 201002),
    (201022, "jchn_g7a_point_prose_rain", "《雨的四季》四季雨景的感官描写与情感线索", 3, SUBJECT, G7, 201002),
    (201023, "jchn_g7a_point_prose_order", "写景散文的观察顺序与视角转换", 4, SUBJECT, G7, 201002),
    (201024, "jchn_g7a_point_prose_clue", "散文“形散神聚”的线索识别与主旨概括", 5, SUBJECT, G7, 201002),
    (201025, "jchn_g7a_point_prose_scene", "借景抒情与情景交融的表达效果分析", 6, SUBJECT, G7, 201002),

    # 记叙文阅读与写人记事
    (201030, "jchn_g7a_point_narr_qiutian", "《秋天的怀念》细节描写与深沉母爱", 1, SUBJECT, G7, 201003),
    (201031, "jchn_g7a_point_narr_sanbu", "《散步》以小儿大的家庭伦理表达", 2, SUBJECT, G7, 201003),
    (201032, "jchn_g7a_point_narr_elements", "记叙文六要素与行文线索梳理", 3, SUBJECT, G7, 201003),
    (201033, "jchn_g7a_point_narr_character", "人物描写五法：外貌、语言、动作、心理、神态", 4, SUBJECT, G7, 201003),
    (201034, "jchn_g7a_point_narr_setting", "记叙文中环境描写的作用分析", 5, SUBJECT, G7, 201003),
    (201035, "jchn_g7a_point_narr_title", "标题含义与作用的多角度分析", 6, SUBJECT, G7, 201003),

    # 文言文阅读
    (201040, "jchn_g7a_point_cls_yongxue", "《咏雪》中“撒盐”与“柳絮”比喻的高下比较", 1, SUBJECT, G7, 201004),
    (201041, "jchn_g7a_point_cls_qixing", "《陈太丘与友期行》实词“期、委、引”与诚信主题", 2, SUBJECT, G7, 201004),
    (201042, "jchn_g7a_point_cls_lunyu_wang", "《论语》十二章“学而不思则罔”的实词与观点理解", 3, SUBJECT, G7, 201004),
    (201043, "jchn_g7a_point_cls_lunyu_method", "《论语》十二章学习方法类章句的归类与启示", 4, SUBJECT, G7, 201004),
    (201044, "jchn_g7a_point_cls_jiezishu", "《诫子书》“静以修身，俭以养德”的论证思路", 5, SUBJECT, G7, 201004),
    (201045, "jchn_g7a_point_cls_lang", "《狼》实词“止、缀、弛、眈眈”与情节推进", 6, SUBJECT, G7, 201004),
    (201046, "jchn_g7a_point_cls_translate", "文言翻译五字法：留、替、调、补、删", 7, SUBJECT, G7, 201004),

    # 古代诗歌鉴赏
    (201050, "jchn_g7a_point_poem_guanchang", "《观沧海》虚实结合与诗人胸襟", 1, SUBJECT, G7, 201005),
    (201051, "jchn_g7a_point_poem_longbiao", "《闻王昌龄左迁龙标遥有此寄》寄情明月的拟人手法", 2, SUBJECT, G7, 201005),
    (201052, "jchn_g7a_point_poem_beigu", "《次北固山下》“海日生残夜”的哲理与乡愁", 3, SUBJECT, G7, 201005),
    (201053, "jchn_g7a_point_poem_tianjingsha", "《天净沙·秋思》意象组合与羁旅之思", 4, SUBJECT, G7, 201005),
    (201054, "jchn_g7a_point_poem_extra1", "课外古诗词诵读（一）：《峨眉山月歌》《江南逢李龟年》", 5, SUBJECT, G7, 201005),
    (201055, "jchn_g7a_point_poem_extra2", "课外古诗词诵读（二）：《秋词》《夜雨寄北》的对比与想象", 6, SUBJECT, G7, 201005),

    # 写作训练
    (201060, "jchn_g7a_point_write_topic", "写人记事：选取典型事例表现人物特点", 1, SUBJECT, G7, 201006),
    (201061, "jchn_g7a_point_write_detail", "写人记事：用细节描写让叙事具体可感", 2, SUBJECT, G7, 201006),
    (201062, "jchn_g7a_point_write_sense", "观察与描写：调动多种感官写景", 3, SUBJECT, G7, 201006),
    (201063, "jchn_g7a_point_write_feature", "观察与描写：抓住景物特征与变化", 4, SUBJECT, G7, 201006),
    (201064, "jchn_g7a_point_write_outline", "思路清晰：围绕中心选材与安排详略", 5, SUBJECT, G7, 201006),
    (201065, "jchn_g7a_point_write_imagine", "联想与想象：在写景叙事中合理展开", 6, SUBJECT, G7, 201006),
    (201066, "jchn_g7a_point_write_smooth", "文从字顺：病句修改与语句衔接", 7, SUBJECT, G7, 201006),
    (201067, "jchn_g7a_point_write_upgrade", "作文升格：开头结尾与前后照应", 8, SUBJECT, G7, 201006),

    # 名著阅读
    (201070, "jchn_g7a_point_read_zhaohua", "《朝花夕拾》篇目内容与鲁迅的童年记忆", 1, SUBJECT, G7, 201007),
    (201071, "jchn_g7a_point_read_zhaohua_view", "《朝花夕拾》双重视角下的温情与批判", 2, SUBJECT, G7, 201007),
    (201072, "jchn_g7a_point_read_zhaohua_figure", "《朝花夕拾》人物形象：长妈妈、藤野先生、范爱农", 3, SUBJECT, G7, 201007),
    (201073, "jchn_g7a_point_read_xiyou", "《西游记》取经故事脉络与主要情节", 4, SUBJECT, G7, 201007),
    (201074, "jchn_g7a_point_read_wukong", "《西游记》孙悟空形象与反抗精神", 5, SUBJECT, G7, 201007),
    (201075, "jchn_g7a_point_read_method", "名著阅读方法：精读与跳读、圈点批注", 6, SUBJECT, G7, 201007),

    # 语言运用与综合性学习
    (201080, "jchn_g7a_point_lang_friend", "综合性学习“有朋自远方来”：交友之道与活动策划", 1, SUBJECT, G7, 201008),
    (201081, "jchn_g7a_point_lang_tribe", "综合性学习“文学部落”：文学社团与阅读分享", 2, SUBJECT, G7, 201008),
    (201082, "jchn_g7a_point_lang_oral", "口语交际：自我介绍与邀请语的得体表达", 3, SUBJECT, G7, 201008),
    (201083, "jchn_g7a_point_lang_slogan", "对联、标语与广告语的拟写", 4, SUBJECT, G7, 201008),
    (201084, "jchn_g7a_point_lang_rhetoric", "比喻、拟人、排比、夸张的辨识与表达效果", 5, SUBJECT, G7, 201008),

    # 童话寓言与想象作品
    (201090, "jchn_g7a_point_imag_emperor", "《皇帝的新装》夸张手法与讽刺意味", 1, SUBJECT, G7, 201009),
    (201091, "jchn_g7a_point_imag_street", "《天上的街市》联想想象与美好意境的营造", 2, SUBJECT, G7, 201009),
    (201092, "jchn_g7a_point_imag_nuwa", "《女娲造人》的想象逻辑与人文精神", 3, SUBJECT, G7, 201009),
    (201093, "jchn_g7a_point_imag_fable", "《寓言四则》寓意概括与生活启示", 4, SUBJECT, G7, 201009),
    (201094, "jchn_g7a_point_imag_contrast", "寓言中对比与反复手法的表达作用", 5, SUBJECT, G7, 201009),
    (201095, "jchn_g7a_point_imag_reading", "想象类作品的阅读路径：从虚构世界到现实关照", 6, SUBJECT, G7, 201009),
)

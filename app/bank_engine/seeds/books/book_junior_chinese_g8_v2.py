"""统编版（2016）初中语文八年级下册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G8 = 8
BOOK_ID = 1304

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版八年级语文下册",
    "jchn_g8b",
    4,
    "人民教育出版社",
    SUBJECT,
    G8,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (130401, "第一单元 民俗风情", "jchn_g8b_u01", 1, BOOK_ID, None),
    (130402, "第二单元 科学探究", "jchn_g8b_u02", 2, BOOK_ID, None),
    (130403, "第三单元 文言山水", "jchn_g8b_u03", 3, BOOK_ID, None),
    (130404, "第四单元 演讲活动（活动·探究）", "jchn_g8b_u04", 4, BOOK_ID, None),
    (130405, "第五单元 游记", "jchn_g8b_u05", 5, BOOK_ID, None),
    (130406, "第六单元 经典对话", "jchn_g8b_u06", 6, BOOK_ID, None),

    # 第一单元 民俗风情
    (130411, "第1课 社戏", "jchn_g8b_l01", 1, BOOK_ID, 130401),
    (130412, "第2课 回延安", "jchn_g8b_l02", 2, BOOK_ID, 130401),
    (130413, "第3课 安塞腰鼓", "jchn_g8b_l03", 3, BOOK_ID, 130401),
    (130414, "第4课 灯笼", "jchn_g8b_l04", 4, BOOK_ID, 130401),

    # 第二单元 科学探究
    (130415, "第5课 大自然的语言", "jchn_g8b_l05", 1, BOOK_ID, 130402),
    (130416, "第6课 阿西莫夫短文两篇（恐龙无处不有／被压扁的沙子）", "jchn_g8b_l06", 2, BOOK_ID, 130402),
    (130417, "第7课 大雁归来", "jchn_g8b_l07", 3, BOOK_ID, 130402),
    (130418, "第8课 时间的脚印", "jchn_g8b_l08", 4, BOOK_ID, 130402),

    # 第三单元 文言山水与名著、诵读
    (130419, "第9课 桃花源记", "jchn_g8b_l09", 1, BOOK_ID, 130403),
    (130420, "第10课 小石潭记", "jchn_g8b_l10", 2, BOOK_ID, 130403),
    (130421, "第11课 核舟记", "jchn_g8b_l11", 3, BOOK_ID, 130403),
    (130422, "第12课 《诗经》二首（关雎／蒹葭）", "jchn_g8b_l12", 4, BOOK_ID, 130403),
    (130423, "名著导读《傅雷家书》：选择性阅读", "jchn_g8b_l13", 5, BOOK_ID, 130403),
    (130424, "课外古诗词诵读（一）：式微／子衿／送杜少府之任蜀州／望洞庭湖赠张丞相", "jchn_g8b_l14", 6, BOOK_ID, 130403),

    # 第四单元 演讲活动
    (130425, "第13课 最后一次讲演", "jchn_g8b_l15", 1, BOOK_ID, 130404),
    (130426, "第14课 应有格物致知精神", "jchn_g8b_l16", 2, BOOK_ID, 130404),
    (130427, "第15课 我一生中的重要抉择", "jchn_g8b_l17", 3, BOOK_ID, 130404),
    (130428, "第16课 庆祝奥林匹克运动复兴25周年", "jchn_g8b_l18", 4, BOOK_ID, 130404),

    # 第五单元 游记
    (130429, "第17课 壶口瀑布", "jchn_g8b_l19", 1, BOOK_ID, 130405),
    (130430, "第18课 在长江源头各拉丹冬", "jchn_g8b_l20", 2, BOOK_ID, 130405),
    (130431, "第19课 登勃朗峰", "jchn_g8b_l21", 3, BOOK_ID, 130405),
    (130432, "第20课 一滴水经过丽江", "jchn_g8b_l22", 4, BOOK_ID, 130405),

    # 第六单元 经典对话与名著、诵读
    (130433, "第21课 《庄子》二则（北冥有鱼／庄子与惠子游于濠梁之上）", "jchn_g8b_l23", 1, BOOK_ID, 130406),
    (130434, "第22课 《礼记》二则（虽有嘉肴／大道之行也）", "jchn_g8b_l24", 2, BOOK_ID, 130406),
    (130435, "第23课 马说", "jchn_g8b_l25", 3, BOOK_ID, 130406),
    (130436, "第24课 唐诗三首（石壕吏／茅屋为秋风所破歌／卖炭翁）", "jchn_g8b_l26", 4, BOOK_ID, 130406),
    (130437, "名著导读《钢铁是怎样炼成的》：摘抄和做笔记", "jchn_g8b_l27", 5, BOOK_ID, 130406),
    (130438, "课外古诗词诵读（二）：题破山寺后禅院／送友人／卜算子·黄州定慧院寓居作／卜算子·咏梅", "jchn_g8b_l28", 6, BOOK_ID, 130406),
)

# id / code / name / sort_order / subject_id / parent_id
# 204001-204008 为册域层，204011-204099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (204001, "jchn_g8b_domain_folk", "初中八下·民俗散文与抒情", 1, SUBJECT, None),
    (204002, "jchn_g8b_domain_science", "初中八下·说明文与科学探究", 2, SUBJECT, None),
    (204003, "jchn_g8b_domain_classical", "初中八下·文言文阅读", 3, SUBJECT, None),
    (204004, "jchn_g8b_domain_poetry", "初中八下·《诗经》与古代诗歌鉴赏", 4, SUBJECT, None),
    (204005, "jchn_g8b_domain_speech", "初中八下·演讲词与活动探究", 5, SUBJECT, None),
    (204006, "jchn_g8b_domain_travel", "初中八下·游记散文", 6, SUBJECT, None),
    (204007, "jchn_g8b_domain_classics", "初中八下·名著阅读", 7, SUBJECT, None),
    (204008, "jchn_g8b_domain_writing", "初中八下·写作与语言运用", 8, SUBJECT, None),

    # 民俗散文与抒情
    (204011, "jchn_g8b_point_folk_shexi_structure", "《社戏》双线结构与“乐土”的儿童视角", 1, SUBJECT, 204001),
    (204012, "jchn_g8b_point_folk_shexi_scenery", "《社戏》月夜行船与归航偷豆的景物描写", 2, SUBJECT, 204001),
    (204013, "jchn_g8b_point_folk_shexi_figures", "《社戏》平桥村人物群像与淳朴民风", 3, SUBJECT, 204001),
    (204014, "jchn_g8b_point_folk_yanan_form", "《回延安》信天游形式与比兴复叠", 4, SUBJECT, 204001),
    (204015, "jchn_g8b_point_folk_yanan_emotion", "《回延安》延安意象与革命情感的表达", 5, SUBJECT, 204001),
    (204016, "jchn_g8b_point_folk_yaogu_rhythm", "《安塞腰鼓》排比反复与鼓点般的语言节奏", 6, SUBJECT, 204001),
    (204017, "jchn_g8b_point_folk_yaogu_symbol", "《安塞腰鼓》动静对比与生命力量的象征", 7, SUBJECT, 204001),
    (204018, "jchn_g8b_point_folk_lantern_thread", "《灯笼》以灯笼为线索的民俗记忆", 8, SUBJECT, 204001),
    (204019, "jchn_g8b_point_folk_lantern_style", "《灯笼》自由笔法与其中的家国情怀", 9, SUBJECT, 204001),

    # 说明文与科学探究
    (204021, "jchn_g8b_point_sci_language_factors", "《大自然的语言》物候现象与决定物候的因素", 1, SUBJECT, 204002),
    (204022, "jchn_g8b_point_sci_language_order", "《大自然的语言》生动说明与逻辑顺序", 2, SUBJECT, 204002),
    (204023, "jchn_g8b_point_sci_asimov_reason", "《阿西莫夫短文两篇》板块构造与恐龙灭绝的推理链", 3, SUBJECT, 204002),
    (204024, "jchn_g8b_point_sci_asimov_method", "《阿西莫夫短文两篇》由现象到结论的科学论证", 4, SUBJECT, 204002),
    (204025, "jchn_g8b_point_sci_goose_ecology", "《大雁归来》观察笔记的抒情性与生态伦理", 5, SUBJECT, 204002),
    (204026, "jchn_g8b_point_sci_goose_personify", "《大雁归来》拟人手法与雁群行为描写", 6, SUBJECT, 204002),
    (204027, "jchn_g8b_point_sci_time_rock", "《时间的脚印》岩石记录时间的说明顺序", 7, SUBJECT, 204002),
    (204028, "jchn_g8b_point_sci_methods", "说明方法辨析：举例子、列数字、作比较、打比方", 8, SUBJECT, 204002),
    (204029, "jchn_g8b_point_sci_language_exact", "说明文语言：准确严密与生动形象的统一", 9, SUBJECT, 204002),

    # 文言文阅读
    (204031, "jchn_g8b_point_cls_taohua_ideal", "《桃花源记》叙事线索与虚实相生的理想社会", 1, SUBJECT, 204003),
    (204032, "jchn_g8b_point_cls_taohua_words", "《桃花源记》古今异义与“豁然开朗”“俨然”等词义", 2, SUBJECT, 204003),
    (204033, "jchn_g8b_point_cls_xiaoshitan_order", "《小石潭记》移步换景与景物描写的层次", 3, SUBJECT, 204003),
    (204034, "jchn_g8b_point_cls_xiaoshitan_emotion", "《小石潭记》寓情于景与“凄神寒骨”的情感转折", 4, SUBJECT, 204003),
    (204035, "jchn_g8b_point_cls_hezhou_space", "《核舟记》空间顺序与总—分—总结构", 5, SUBJECT, 204003),
    (204036, "jchn_g8b_point_cls_hezhou_detail", "《核舟记》数字说明与雕刻技艺的细节还原", 6, SUBJECT, 204003),
    (204037, "jchn_g8b_point_cls_zhuangzi_kun", "《北冥有鱼》鲲鹏寓言的想象与夸张", 7, SUBJECT, 204003),
    (204038, "jchn_g8b_point_cls_zhuangzi_hao", "《庄子与惠子游于濠梁之上》濠梁之辩的逻辑", 8, SUBJECT, 204003),
    (204039, "jchn_g8b_point_cls_liji_jia", "《虽有嘉肴》教学相长与类比论证", 9, SUBJECT, 204003),
    (204040, "jchn_g8b_point_cls_liji_datong", "《大道之行也》大同社会的理想图景", 10, SUBJECT, 204003),
    (204041, "jchn_g8b_point_cls_ma_shuo_metaphor", "《马说》托物寓意与“千里马”的人才隐喻", 11, SUBJECT, 204003),
    (204042, "jchn_g8b_point_cls_ma_shuo_tone", "《马说》反问排比与不平之鸣", 12, SUBJECT, 204003),
    (204043, "jchn_g8b_point_cls_words_polysemy", "文言实词：缘、俨然、属、诎、食、策等一词多义", 13, SUBJECT, 204003),
    (204044, "jchn_g8b_point_cls_function_words", "文言虚词：之、其、以、于的用法辨析", 14, SUBJECT, 204003),
    (204045, "jchn_g8b_point_cls_translate_rules", "文言翻译：留、替、调、补、删的原则", 15, SUBJECT, 204003),

    # 《诗经》与古代诗歌鉴赏
    (204051, "jchn_g8b_point_poem_guanju_form", "《关雎》重章叠句与“兴”的手法", 1, SUBJECT, 204004),
    (204052, "jchn_g8b_point_poem_guanju_emotion", "《关雎》君子好逑的情感与礼乐节制", 2, SUBJECT, 204004),
    (204053, "jchn_g8b_point_poem_jianjia", "《蒹葭》朦胧意境与追寻主题", 3, SUBJECT, 204004),
    (204054, "jchn_g8b_point_poem_shijing_common", "《诗经》常识：风雅颂与赋比兴", 4, SUBJECT, 204004),
    (204055, "jchn_g8b_point_poem_shihaoli", "《石壕吏》对话叙事与差役之凶", 5, SUBJECT, 204004),
    (204056, "jchn_g8b_point_poem_maowu", "《茅屋为秋风所破歌》推己及人的博大情怀", 6, SUBJECT, 204004),
    (204057, "jchn_g8b_point_poem_maitanweng", "《卖炭翁》外貌心理描写与宫市之弊", 7, SUBJECT, 204004),
    (204058, "jchn_g8b_point_poem_reading1", "课外古诗词（一）：式微／子衿／送杜少府之任蜀州／望洞庭湖赠张丞相", 8, SUBJECT, 204004),
    (204059, "jchn_g8b_point_poem_reading2", "课外古诗词（二）：题破山寺后禅院／送友人／卜算子·黄州定慧院寓居作／卜算子·咏梅", 9, SUBJECT, 204004),

    # 演讲词与活动探究
    (204061, "jchn_g8b_point_speech_last_scene", "《最后一次讲演》即兴演讲的现场感与爱憎情感", 1, SUBJECT, 204005),
    (204062, "jchn_g8b_point_speech_last_rhetoric", "《最后一次讲演》设问反问与人称转换的鼓动性", 2, SUBJECT, 204005),
    (204063, "jchn_g8b_point_speech_gewu", "《应有格物致知精神》观点提出与事例论证", 3, SUBJECT, 204005),
    (204064, "jchn_g8b_point_speech_choice", "《我一生中的重要抉择》现身说法的演讲策略", 4, SUBJECT, 204005),
    (204065, "jchn_g8b_point_speech_olympic", "《庆祝奥林匹克运动复兴25周年》庄重典雅的演讲语言", 5, SUBJECT, 204005),
    (204066, "jchn_g8b_point_speech_features", "演讲词特点：针对性、鲜明观点与情感感染力", 6, SUBJECT, 204005),
    (204067, "jchn_g8b_point_speech_activity", "演讲活动：撰写演讲稿与临场表达", 7, SUBJECT, 204005),

    # 游记散文
    (204071, "jchn_g8b_point_travel_hukou_observe", "《壶口瀑布》定点观察与雨季、枯水期的对比", 1, SUBJECT, 204006),
    (204072, "jchn_g8b_point_travel_hukou_theme", "《壶口瀑布》由景及理与民族精神的升华", 2, SUBJECT, 204006),
    (204073, "jchn_g8b_point_travel_dandong_route", "《在长江源头各拉丹冬》游记的时空线索与雪山奇景", 3, SUBJECT, 204006),
    (204074, "jchn_g8b_point_travel_dandong_body", "《在长江源头各拉丹冬》身体感受与景物描写的融合", 4, SUBJECT, 204006),
    (204075, "jchn_g8b_point_travel_montblanc_style", "《登勃朗峰》散文笔法与小说笔法的转换", 5, SUBJECT, 204006),
    (204076, "jchn_g8b_point_travel_water_person", "《一滴水经过丽江》拟人视角与水的行踪线索", 6, SUBJECT, 204006),
    (204077, "jchn_g8b_point_travel_elements", "游记要素：游踪、见闻与感受的统一", 7, SUBJECT, 204006),
    (204078, "jchn_g8b_point_travel_writing", "游记写作：抓住景物特征与情景交融", 8, SUBJECT, 204006),

    # 名著阅读
    (204081, "jchn_g8b_point_classic_fulei_letter", "《傅雷家书》家书体例与父爱中的教育智慧", 1, SUBJECT, 204007),
    (204082, "jchn_g8b_point_classic_fulei_select", "《傅雷家书》选择性阅读与专题探究", 2, SUBJECT, 204007),
    (204083, "jchn_g8b_point_classic_pavel_growth", "《钢铁是怎样炼成的》保尔成长与革命理想", 3, SUBJECT, 204007),
    (204084, "jchn_g8b_point_classic_pavel_notes", "《钢铁是怎样炼成的》摘抄与做笔记的阅读方法", 4, SUBJECT, 204007),
    (204085, "jchn_g8b_point_classic_figures", "名著阅读：人物关系梳理与主题归纳", 5, SUBJECT, 204007),

    # 写作与语言运用
    (204091, "jchn_g8b_point_write_reading", "学写读后感：引、议、联、结的结构", 1, SUBJECT, 204008),
    (204092, "jchn_g8b_point_write_youji", "学写游记：游踪清晰与详略得当", 2, SUBJECT, 204008),
    (204093, "jchn_g8b_point_write_speech", "学写演讲词：观点鲜明与情理交融", 3, SUBJECT, 204008),
    (204094, "jchn_g8b_point_write_story", "学写故事：情节设计与人物塑造", 4, SUBJECT, 204008),
    (204095, "jchn_g8b_point_lang_pinyin", "八下字音字形：归省、惮、撺掇、亢奋、羁绊", 5, SUBJECT, 204008),
    (204096, "jchn_g8b_point_lang_idiom", "成语积累：叹为观止、大彻大悟、周而复始、销声匿迹", 6, SUBJECT, 204008),
    (204097, "jchn_g8b_point_lang_sentence", "病句辨析：语序不当与成分赘余", 7, SUBJECT, 204008),
    (204098, "jchn_g8b_point_lang_integrity", "综合性学习“倡导低碳生活”与“以和为贵”", 8, SUBJECT, 204008),
    (204099, "jchn_g8b_point_lang_poetry_walk", "综合性学习“古诗苑漫步”：别出心裁品古诗", 9, SUBJECT, 204008),
)

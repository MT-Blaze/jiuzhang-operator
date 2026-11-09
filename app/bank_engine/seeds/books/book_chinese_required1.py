"""统编版（2019）高中语文必修上册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G10 = 10
BOOK_ID = 1101

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中语文必修上册",
    "chn_r1",
    1,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (110101, "第一单元 青春激扬", "chn_r1_u01", 1, BOOK_ID, None),
    (110102, "第二单元 劳动光荣", "chn_r1_u02", 2, BOOK_ID, None),
    (110103, "第三单元 生命的诗意", "chn_r1_u03", 3, BOOK_ID, None),
    (110104, "第四单元 家乡文化生活", "chn_r1_u04", 4, BOOK_ID, None),
    (110105, "第五单元 整本书阅读《乡土中国》", "chn_r1_u05", 5, BOOK_ID, None),
    (110106, "第六单元 学习之道", "chn_r1_u06", 6, BOOK_ID, None),
    (110107, "第七单元 自然情怀", "chn_r1_u07", 7, BOOK_ID, None),
    (110108, "第八单元 词语积累与词语解释", "chn_r1_u08", 8, BOOK_ID, None),
    (110109, "古诗词诵读", "chn_r1_u09", 9, BOOK_ID, None),
    (110111, "第1课 沁园春·长沙", "chn_r1_l01", 1, BOOK_ID, 110101),
    (110112, "第2课 立在地球边上放号／红烛／峨日朵雪峰之侧／致云雀", "chn_r1_l02", 2, BOOK_ID, 110101),
    (110113, "第3课 百合花／哦，香雪", "chn_r1_l03", 3, BOOK_ID, 110101),
    (110114, "第4课 喜看稻菽千重浪／心有一团火，温暖众人心／“探界者”钟扬", "chn_r1_l04", 1, BOOK_ID, 110102),
    (110115, "第5课 以工匠精神雕琢时代品质", "chn_r1_l05", 2, BOOK_ID, 110102),
    (110116, "第6课 芣苢／插秧歌", "chn_r1_l06", 3, BOOK_ID, 110102),
    (110117, "第7课 短歌行／归园田居（其一）", "chn_r1_l07", 1, BOOK_ID, 110103),
    (110118, "第8课 梦游天姥吟留别／登高／琵琶行并序", "chn_r1_l08", 2, BOOK_ID, 110103),
    (110119, "第9课 念奴娇·赤壁怀古／永遇乐·京口北固亭怀古／声声慢（寻寻觅觅）", "chn_r1_l09", 3, BOOK_ID, 110103),
    (110120, "家乡文化生活：记录家乡的人和物、现状调查、参与家乡文化建设", "chn_r1_l10", 1, BOOK_ID, 110104),
    (110121, "《乡土中国》整本书阅读：概念梳理与专题研讨", "chn_r1_l11", 1, BOOK_ID, 110105),
    (110122, "第10课 劝学／师说", "chn_r1_l12", 1, BOOK_ID, 110106),
    (110123, "第11课 反对党八股（节选）", "chn_r1_l13", 2, BOOK_ID, 110106),
    (110124, "第12课 拿来主义", "chn_r1_l14", 3, BOOK_ID, 110106),
    (110125, "第13课 读书：目的和前提／上图书馆", "chn_r1_l15", 4, BOOK_ID, 110106),
    (110126, "第14课 故都的秋／荷塘月色", "chn_r1_l16", 1, BOOK_ID, 110107),
    (110127, "第15课 我与地坛（节选）", "chn_r1_l17", 2, BOOK_ID, 110107),
    (110128, "第16课 赤壁赋／登泰山记", "chn_r1_l18", 3, BOOK_ID, 110107),
    (110129, "词语积累与词语解释", "chn_r1_l19", 1, BOOK_ID, 110108),
    (110130, "静女／涉江采芙蓉", "chn_r1_l20", 1, BOOK_ID, 110109),
    (110131, "虞美人（春花秋月何时了）／鹊桥仙（纤云弄巧）", "chn_r1_l21", 2, BOOK_ID, 110109),
)

# id / code / name / sort_order / subject_id / parent_id
# 110001-110009 为册域，110010-110024 为课域，110025-110099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (110001, "chn_r1_domain_modern_poetry", "现代诗歌鉴赏：青春意象、抒情主人公与自由诗形式", 1, SUBJECT, None),
    (110002, "chn_r1_domain_fiction", "小说叙事鉴赏：人物、环境、情节与叙述视角", 2, SUBJECT, None),
    (110003, "chn_r1_domain_news", "新闻通讯与评论：真实性、典型性与舆论表达", 3, SUBJECT, None),
    (110004, "chn_r1_domain_poetry", "古诗词鉴赏：意象意境、表达技巧与情感基调", 4, SUBJECT, None),
    (110005, "chn_r1_domain_classical", "文言文研读：实词虚词、句式翻译与文化意蕴", 5, SUBJECT, None),
    (110006, "chn_r1_domain_argument", "论述文思辨：论证结构、论证方法与批判性阅读", 6, SUBJECT, None),
    (110007, "chn_r1_domain_prose", "现代散文鉴赏：形散神聚、情景交融与语言品味", 7, SUBJECT, None),
    (110008, "chn_r1_domain_whole_book", "整本书阅读《乡土中国》：概念图谱与研究方法", 8, SUBJECT, None),
    (110009, "chn_r1_domain_language", "语言积累与语文实践：词义系统、调查访谈与表达", 9, SUBJECT, None),

    # 课域层
    (110010, "chn_r1_lesson_modern_poetry", "第一单元 现代诗歌：沁园春·长沙等五首", 1, SUBJECT, 110001),
    (110011, "chn_r1_lesson_fiction", "第一单元 小说：百合花／哦，香雪", 2, SUBJECT, 110002),
    (110012, "chn_r1_lesson_news", "第二单元 人物通讯与新闻评论：袁隆平／张秉贵／钟扬／工匠精神", 1, SUBJECT, 110003),
    (110013, "chn_r1_lesson_labor_poetry", "第二单元 古代劳动诗歌：芣苢／插秧歌", 2, SUBJECT, 110004),
    (110014, "chn_r1_lesson_hanwei", "第三单元 汉魏诗歌：短歌行／归园田居（其一）", 1, SUBJECT, 110004),
    (110015, "chn_r1_lesson_tang", "第三单元 唐诗：梦游天姥吟留别／登高／琵琶行并序", 2, SUBJECT, 110004),
    (110016, "chn_r1_lesson_song", "第三单元 宋词：念奴娇·赤壁怀古／永遇乐／声声慢", 3, SUBJECT, 110004),
    (110017, "chn_r1_lesson_hometown", "第四单元 家乡文化生活实践：调查、访谈与文化表达", 1, SUBJECT, 110009),
    (110018, "chn_r1_lesson_rural_china", "第五单元 《乡土中国》整本书阅读与专题研讨", 1, SUBJECT, 110008),
    (110019, "chn_r1_lesson_classical_argument", "第六单元 文言议论：劝学／师说", 1, SUBJECT, 110005),
    (110020, "chn_r1_lesson_modern_argument", "第六单元 现代论述与随笔：反对党八股／拿来主义／读书随笔", 2, SUBJECT, 110006),
    (110021, "chn_r1_lesson_modern_prose", "第七单元 现代散文：故都的秋／荷塘月色／我与地坛", 1, SUBJECT, 110007),
    (110022, "chn_r1_lesson_travel", "第七单元 古代游记与赋：赤壁赋／登泰山记", 2, SUBJECT, 110005),
    (110023, "chn_r1_lesson_words", "第八单元 词语积累与词语解释", 1, SUBJECT, 110009),
    (110024, "chn_r1_lesson_recitation", "古诗词诵读：静女／涉江采芙蓉／虞美人／鹊桥仙", 1, SUBJECT, 110004),

    # 现代诗歌考点
    (110025, "chn_r1_point_qinyuanchun_imagery", "沁园春·长沙：湘江秋景的意象组合与“谁主沉浮”的青春抱负", 1, SUBJECT, 110010),
    (110026, "chn_r1_point_qinyuanchun_structure", "沁园春·长沙：上下阕结构、领字运用与情景交融", 2, SUBJECT, 110010),
    (110027, "chn_r1_point_fanghao_romantic", "立在地球边上放号：宏阔想象、呼告与“力的绘画”式浪漫抒情", 3, SUBJECT, 110010),
    (110028, "chn_r1_point_red_candle", "红烛：以烛为象的象征体系与奉献精神的层层推进", 4, SUBJECT, 110010),
    (110029, "chn_r1_point_snow_peak_skylark", "峨日朵雪峰之侧／致云雀：困境中的坚守与自由欢欣的象征", 5, SUBJECT, 110010),
    (110030, "chn_r1_point_free_verse", "自由诗形式：分行跨行、内在节奏、复沓与抒情主人公形象", 6, SUBJECT, 110010),

    # 小说考点
    (110031, "chn_r1_point_lily_character", "百合花：小通讯员与新媳妇的形象塑造及细节描写", 1, SUBJECT, 110011),
    (110032, "chn_r1_point_lily_symbol", "百合花：百合花被的物象象征与军民鱼水情", 2, SUBJECT, 110011),
    (110033, "chn_r1_point_xiangxue_psychology", "哦，香雪：香雪的心理变化与山村少女对现代文明的向往", 3, SUBJECT, 110011),
    (110034, "chn_r1_point_poetic_fiction", "诗化小说：环境描写、散文化叙事与抒情氛围的营造", 4, SUBJECT, 110011),

    # 新闻通讯与评论考点
    (110035, "chn_r1_point_news_truth", "人物通讯的真实性：典型事例、现场细节与人物语言", 1, SUBJECT, 110012),
    (110036, "chn_r1_point_yuan_longping", "喜看稻菽千重浪：袁隆平的形象与科学家精神", 2, SUBJECT, 110012),
    (110037, "chn_r1_point_zhang_binggui", "心有一团火，温暖众人心：张秉贵在平凡岗位上的服务精神", 3, SUBJECT, 110012),
    (110038, "chn_r1_point_zhong_yang", "“探界者”钟扬：标题含义、小标题结构与人物精神品质", 4, SUBJECT, 110012),
    (110039, "chn_r1_point_craftsmanship", "新闻评论：以工匠精神雕琢时代品质的论点、论据与论证", 5, SUBJECT, 110012),
    (110040, "chn_r1_point_news_genre", "通讯与评论的文体差异：叙述事实与评说事理", 6, SUBJECT, 110012),

    # 古代劳动诗歌考点
    (110041, "chn_r1_point_fuyi", "芣苢：重章叠句、动词变换与劳动欢歌", 1, SUBJECT, 110013),
    (110042, "chn_r1_point_planting", "插秧歌：白描、比喻与繁忙紧张的劳动场景", 2, SUBJECT, 110013),
    (110043, "chn_r1_point_labor_poetry", "古代劳动诗：劳动主题、民歌风味与生活气息", 3, SUBJECT, 110013),

    # 汉魏诗歌考点
    (110044, "chn_r1_point_duangexing_theme", "短歌行：宴饮起兴、比兴与求贤若渴的主题", 1, SUBJECT, 110014),
    (110045, "chn_r1_point_duangexing_allusion", "短歌行：用典（周公吐哺等）与人生忧思的多重内涵", 2, SUBJECT, 110014),
    (110046, "chn_r1_point_guiyuantianju_imagery", "归园田居（其一）：田园意象、“尘网”对比与归隐之乐", 3, SUBJECT, 110014),
    (110047, "chn_r1_point_guiyuantianju_style", "归园田居（其一）：平淡自然的语言风格与真淳情感", 4, SUBJECT, 110014),

    # 唐诗考点
    (110048, "chn_r1_point_tianmu_imagination", "梦游天姥吟留别：瑰奇想象、夸张与浪漫主义手法", 1, SUBJECT, 110015),
    (110049, "chn_r1_point_tianmu_reality", "梦游天姥吟留别：梦境与现实的反差及“安能摧眉折腰”的人格寄托", 2, SUBJECT, 110015),
    (110050, "chn_r1_point_denggao_imagery", "登高：风急天高、落木长江等意象与沉郁顿挫的风格", 3, SUBJECT, 110015),
    (110051, "chn_r1_point_denggao_craft", "登高：对仗工整、语言凝练与家国之悲", 4, SUBJECT, 110015),
    (110052, "chn_r1_point_pipa_music", "琵琶行并序：音乐描写的比喻、通感与侧面烘托", 5, SUBJECT, 110015),
    (110053, "chn_r1_point_pipa_resonance", "琵琶行并序：“同是天涯沦落人”的身世之感与情感共鸣", 6, SUBJECT, 110015),
    (110054, "chn_r1_point_tang_comparison", "唐诗三首比较：李白飘逸、杜甫沉郁与白居易通俗", 7, SUBJECT, 110015),

    # 宋词考点
    (110055, "chn_r1_point_chibi_scenery", "念奴娇·赤壁怀古：赤壁江景、周瑜形象与豪放词风", 1, SUBJECT, 110016),
    (110056, "chn_r1_point_chibi_emotion", "念奴娇·赤壁怀古：怀古与自伤的交织及旷达人生态度", 2, SUBJECT, 110016),
    (110057, "chn_r1_point_beiguting_allusion", "永遇乐·京口北固亭怀古：多处用典与抗金报国情怀", 3, SUBJECT, 110016),
    (110058, "chn_r1_point_beiguting_contrast", "永遇乐·京口北固亭怀古：今昔对比、讽今与壮志难酬", 4, SUBJECT, 110016),
    (110059, "chn_r1_point_shengshengman", "声声慢：叠字开篇、意象叠加与婉约愁情", 5, SUBJECT, 110016),
    (110060, "chn_r1_point_song_comparison", "宋词三首比较：豪放与婉约的风格差异", 6, SUBJECT, 110016),

    # 家乡文化生活考点
    (110061, "chn_r1_point_hometown_survey", "家乡文化生活调查：主题确定、问卷设计与实地走访", 1, SUBJECT, 110017),
    (110062, "chn_r1_point_interview", "访谈法：提纲拟定、追问记录与材料核实", 2, SUBJECT, 110017),
    (110063, "chn_r1_point_hometown_writing", "家乡文化志与建议书：材料整理、观点提炼与表达", 3, SUBJECT, 110017),

    # 《乡土中国》考点
    (110064, "chn_r1_point_rural_nature", "乡土本色：从“土”出发的熟人社会与地方性限制", 1, SUBJECT, 110018),
    (110065, "chn_r1_point_literacy", "文字下乡：面对面社群中文字传情的局限与空间阻隔", 2, SUBJECT, 110018),
    (110066, "chn_r1_point_differential_mode", "差序格局：以己为中心、可伸缩的波纹式社会关系", 3, SUBJECT, 110018),
    (110067, "chn_r1_point_ritual_order", "礼治秩序与无讼：传统乡土社会的规范与纠纷解决", 4, SUBJECT, 110018),
    (110068, "chn_r1_point_elder_rule", "长老统治：教化权力与乡土社会秩序的维系", 5, SUBJECT, 110018),
    (110069, "chn_r1_point_blood_geo", "血缘与地缘：身份网络、社区边界与社会流动", 6, SUBJECT, 110018),
    (110070, "chn_r1_point_name_reality", "名实的分离与社会变迁：注释经典、时势权力与乡土转型", 7, SUBJECT, 110018),

    # 文言议论考点
    (110071, "chn_r1_point_quanxue_argument", "劝学：比喻论证、正反对比与“学不可以已”的中心论点", 1, SUBJECT, 110019),
    (110072, "chn_r1_point_quanxue_attitude", "劝学：积累、坚持、专一的层进说理与学习态度", 2, SUBJECT, 110019),
    (110073, "chn_r1_point_shishuo_argument", "师说：对比论证、破立结合与师道沦丧的现实批判", 3, SUBJECT, 110019),
    (110074, "chn_r1_point_shishuo_view", "师说：“道之所存，师之所存”的师道观与辩证色彩", 4, SUBJECT, 110019),
    (110075, "chn_r1_point_classical_language", "劝学／师说：通假、词类活用、古今异义与宾语前置等文言现象", 5, SUBJECT, 110019),
    (110076, "chn_r1_point_classical_argument_art", "文言议论的说理艺术：比喻、对比与气势", 6, SUBJECT, 110019),

    # 现代论述与随笔考点
    (110077, "chn_r1_point_party_stereotype", "反对党八股：八条罪状的空洞说理与破立结合的批驳", 1, SUBJECT, 110020),
    (110078, "chn_r1_point_party_language", "反对党八股：群众语言、俗语与生动活泼的文风", 2, SUBJECT, 110020),
    (110079, "chn_r1_point_takeism_metaphor", "拿来主义：大宅子比喻与“占有、挑选”的批判继承", 3, SUBJECT, 110020),
    (110080, "chn_r1_point_takeism_structure", "拿来主义：破“闭关主义”“送去主义”与立“拿来主义”", 4, SUBJECT, 110020),
    (110081, "chn_r1_point_reading_purpose", "读书：目的和前提：读书目的与经典阅读", 5, SUBJECT, 110020),
    (110082, "chn_r1_point_library", "上图书馆：图书馆记忆与阅读成长体验", 6, SUBJECT, 110020),

    # 现代散文考点
    (110083, "chn_r1_point_gudu_autumn", "故都的秋：南北秋景对比与“清、静、悲凉”的审美选择", 1, SUBJECT, 110021),
    (110084, "chn_r1_point_gudu_scene", "故都的秋：寻常景物细描与情景交融的抒情方式", 2, SUBJECT, 110021),
    (110085, "chn_r1_point_hetang_senses", "荷塘月色：月下荷塘的多感官描写与通感", 3, SUBJECT, 110021),
    (110086, "chn_r1_point_hetang_emotion", "荷塘月色：“淡淡的喜悦”与“淡淡的哀愁”及行文线索", 4, SUBJECT, 110021),
    (110087, "chn_r1_point_ditan_life", "我与地坛：地坛景物与对生命的沉思", 5, SUBJECT, 110021),
    (110088, "chn_r1_point_ditan_mother", "我与地坛：母亲形象与“活”的追问", 6, SUBJECT, 110021),

    # 古代游记与赋考点
    (110089, "chn_r1_point_chibiao_philosophy", "赤壁赋：主客问答、水月之喻与“变与不变”的哲思", 1, SUBJECT, 110022),
    (110090, "chn_r1_point_chibiao_blend", "赤壁赋：景、情、理交融与旷达超脱的人生态度", 2, SUBJECT, 110022),
    (110091, "chn_r1_point_taishan_route", "登泰山记：登山路线、泰山日出与冬日景物的写实笔法", 3, SUBJECT, 110022),
    (110092, "chn_r1_point_taishan_style", "登泰山记：桐城派“雅洁”文风与考据、辞章的结合", 4, SUBJECT, 110022),

    # 词语积累考点
    (110093, "chn_r1_point_word_change", "词义演变：古今异义、词义扩大缩小转移与感情色彩变化", 1, SUBJECT, 110023),
    (110094, "chn_r1_point_context_meaning", "语境义：词语在具体语境中的临时义、修辞义与褒贬转换", 2, SUBJECT, 110023),
    (110095, "chn_r1_point_word_method", "词语积累方法：分类梳理、工具书查检与易混词辨析", 3, SUBJECT, 110023),

    # 古诗词诵读考点
    (110096, "chn_r1_point_jingnv", "静女：细节动作、双关与纯真爱情", 1, SUBJECT, 110024),
    (110097, "chn_r1_point_shejiang", "涉江采芙蓉：采撷意象、悬想手法与相思之苦", 2, SUBJECT, 110024),
    (110098, "chn_r1_point_yumeiren", "虞美人：春花秋月的永恒对比与亡国之痛", 3, SUBJECT, 110024),
    (110099, "chn_r1_point_queqiaoxian", "鹊桥仙：议论入词、翻案笔法与“两情久长”的爱情观", 4, SUBJECT, 110024),
)

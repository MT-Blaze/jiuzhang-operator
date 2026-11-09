"""统编版小学语文一年级上册：入学准备、识字、汉语拼音与课文的知识点树。"""

from __future__ import annotations

SUBJECT = 1
G1 = 1
BOOK_ID = 1401

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版小学语文一年级上册",
    "pchn_g1a",
    1,
    "人民教育出版社",
    SUBJECT,
    G1,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元与入学准备
    (140101, "我上学了", "pchn_g1a_u00", 1, BOOK_ID, None),
    (140102, "第一单元 识字（一）", "pchn_g1a_u01", 2, BOOK_ID, None),
    (140103, "第二单元 汉语拼音（一）", "pchn_g1a_u02", 3, BOOK_ID, None),
    (140104, "第三单元 汉语拼音（二）", "pchn_g1a_u03", 4, BOOK_ID, None),
    (140105, "第四单元 课文（一）", "pchn_g1a_u04", 5, BOOK_ID, None),
    (140106, "第五单元 识字（二）", "pchn_g1a_u05", 6, BOOK_ID, None),
    (140107, "第六单元 课文（二）", "pchn_g1a_u06", 7, BOOK_ID, None),
    (140108, "第七单元 课文（三）", "pchn_g1a_u07", 8, BOOK_ID, None),
    (140109, "第八单元 课文（四）", "pchn_g1a_u08", 9, BOOK_ID, None),

    # 我上学了
    (140110, "我是中国人", "pchn_g1a_l00", 1, BOOK_ID, 140101),
    (140111, "我是小学生", "pchn_g1a_l01", 2, BOOK_ID, 140101),
    (140112, "我爱学语文", "pchn_g1a_l02", 3, BOOK_ID, 140101),

    # 第一单元 识字（一）
    (140113, "识字1 天地人", "pchn_g1a_l03", 1, BOOK_ID, 140102),
    (140114, "识字2 金木水火土", "pchn_g1a_l04", 2, BOOK_ID, 140102),
    (140115, "识字3 口耳目", "pchn_g1a_l05", 3, BOOK_ID, 140102),
    (140116, "识字4 日月水火", "pchn_g1a_l06", 4, BOOK_ID, 140102),
    (140117, "识字5 对韵歌", "pchn_g1a_l07", 5, BOOK_ID, 140102),
    (140118, "口语交际·我说你做", "pchn_g1a_l08", 6, BOOK_ID, 140102),
    (140119, "语文园地一", "pchn_g1a_l09", 7, BOOK_ID, 140102),

    # 第二单元 汉语拼音（一）
    (140120, "汉语拼音1 a o e", "pchn_g1a_l10", 1, BOOK_ID, 140103),
    (140121, "汉语拼音2 i u ü y w", "pchn_g1a_l11", 2, BOOK_ID, 140103),
    (140122, "汉语拼音3 b p m f", "pchn_g1a_l12", 3, BOOK_ID, 140103),
    (140123, "汉语拼音4 d t n l", "pchn_g1a_l13", 4, BOOK_ID, 140103),
    (140124, "汉语拼音5 g k h", "pchn_g1a_l14", 5, BOOK_ID, 140103),
    (140125, "汉语拼音6 j q x", "pchn_g1a_l15", 6, BOOK_ID, 140103),
    (140126, "汉语拼音7 z c s", "pchn_g1a_l16", 7, BOOK_ID, 140103),
    (140127, "汉语拼音8 zh ch sh r", "pchn_g1a_l17", 8, BOOK_ID, 140103),
    (140128, "语文园地二", "pchn_g1a_l18", 9, BOOK_ID, 140103),

    # 第三单元 汉语拼音（二）
    (140129, "汉语拼音9 ai ei ui", "pchn_g1a_l19", 1, BOOK_ID, 140104),
    (140130, "汉语拼音10 ao ou iu", "pchn_g1a_l20", 2, BOOK_ID, 140104),
    (140131, "汉语拼音11 ie üe er", "pchn_g1a_l21", 3, BOOK_ID, 140104),
    (140132, "汉语拼音12 an en in un ün", "pchn_g1a_l22", 4, BOOK_ID, 140104),
    (140133, "汉语拼音13 ang eng ing ong", "pchn_g1a_l23", 5, BOOK_ID, 140104),
    (140134, "语文园地三", "pchn_g1a_l24", 6, BOOK_ID, 140104),

    # 第四单元 课文（一）
    (140135, "课文1 秋天", "pchn_g1a_l25", 1, BOOK_ID, 140105),
    (140136, "课文2 小小的船", "pchn_g1a_l26", 2, BOOK_ID, 140105),
    (140137, "课文3 江南", "pchn_g1a_l27", 3, BOOK_ID, 140105),
    (140138, "课文4 四季", "pchn_g1a_l28", 4, BOOK_ID, 140105),
    (140139, "口语交际·我们做朋友", "pchn_g1a_l29", 5, BOOK_ID, 140105),
    (140140, "语文园地四", "pchn_g1a_l30", 6, BOOK_ID, 140105),

    # 第五单元 识字（二）
    (140141, "识字6 画", "pchn_g1a_l31", 1, BOOK_ID, 140106),
    (140142, "识字7 大小多少", "pchn_g1a_l32", 2, BOOK_ID, 140106),
    (140143, "识字8 小书包", "pchn_g1a_l33", 3, BOOK_ID, 140106),
    (140144, "识字9 日月明", "pchn_g1a_l34", 4, BOOK_ID, 140106),
    (140145, "识字10 升国旗", "pchn_g1a_l35", 5, BOOK_ID, 140106),
    (140146, "语文园地五", "pchn_g1a_l36", 6, BOOK_ID, 140106),

    # 第六单元 课文（二）
    (140147, "课文5 影子", "pchn_g1a_l37", 1, BOOK_ID, 140107),
    (140148, "课文6 比尾巴", "pchn_g1a_l38", 2, BOOK_ID, 140107),
    (140149, "课文7 青蛙写诗", "pchn_g1a_l39", 3, BOOK_ID, 140107),
    (140150, "课文8 雨点儿", "pchn_g1a_l40", 4, BOOK_ID, 140107),
    (140151, "语文园地六", "pchn_g1a_l41", 5, BOOK_ID, 140107),

    # 第七单元 课文（三）
    (140152, "课文9 明天要远足", "pchn_g1a_l42", 1, BOOK_ID, 140108),
    (140153, "课文10 大还是小", "pchn_g1a_l43", 2, BOOK_ID, 140108),
    (140154, "课文11 项链", "pchn_g1a_l44", 3, BOOK_ID, 140108),
    (140155, "语文园地七", "pchn_g1a_l45", 4, BOOK_ID, 140108),

    # 第八单元 课文（四）
    (140156, "课文12 雪地里的小画家", "pchn_g1a_l46", 1, BOOK_ID, 140109),
    (140157, "课文13 乌鸦喝水", "pchn_g1a_l47", 2, BOOK_ID, 140109),
    (140158, "课文14 小蜗牛", "pchn_g1a_l48", 3, BOOK_ID, 140109),
    (140159, "语文园地八", "pchn_g1a_l49", 4, BOOK_ID, 140109),
)

# id / code / name / sort_order / subject_id / parent_id
# 243001-243009 为册域层，243010-243099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (243001, "pchn_g1a_domain_school", "小学一上·入学适应与学习习惯", 1, SUBJECT, None),
    (243002, "pchn_g1a_domain_literacy1", "小学一上·识字（一）字理与笔画", 2, SUBJECT, None),
    (243003, "pchn_g1a_domain_pinyin1", "小学一上·汉语拼音（一）声母与单韵母", 3, SUBJECT, None),
    (243004, "pchn_g1a_domain_pinyin2", "小学一上·汉语拼音（二）复韵母与鼻韵母", 4, SUBJECT, None),
    (243005, "pchn_g1a_domain_text1", "小学一上·课文（一）朗读与背诵", 5, SUBJECT, None),
    (243006, "pchn_g1a_domain_literacy2", "小学一上·识字（二）结构与量词", 6, SUBJECT, None),
    (243007, "pchn_g1a_domain_text2", "小学一上·课文（二）问答与标点", 7, SUBJECT, None),
    (243008, "pchn_g1a_domain_text3", "小学一上·课文（三）情感与表达", 8, SUBJECT, None),
    (243009, "pchn_g1a_domain_text4", "小学一上·课文（四）观察与看图写话", 9, SUBJECT, None),

    # 入学适应与学习习惯
    (243010, "pchn_g1a_point_china_flag", "我是中国人：认识国旗国徽，产生爱国情感", 1, SUBJECT, 243001),
    (243011, "pchn_g1a_point_pupil_rule", "我是小学生：课堂坐姿、举手发言与课间安全", 2, SUBJECT, 243001),
    (243012, "pchn_g1a_point_reading_posture", "我爱学语文：读书姿势与“三个一”写字姿势", 3, SUBJECT, 243001),
    (243013, "pchn_g1a_point_follow_order", "口语交际“我说你做”：听清指令并做动作", 4, SUBJECT, 243001),
    (243014, "pchn_g1a_point_listen_turn", "学习习惯：课前准备、认真倾听与轮流发言", 5, SUBJECT, 243001),

    # 识字（一）
    (243015, "pchn_g1a_point_tiandi", "《天地人》：认读“天、地、人”，体会人与自然", 1, SUBJECT, 243002),
    (243016, "pchn_g1a_point_wuxing", "《金木水火土》：五行汉字与“一二三四五”", 2, SUBJECT, 243002),
    (243017, "pchn_g1a_point_kouermu", "《口耳目》：身体部位字与象形字特点", 3, SUBJECT, 243002),
    (243018, "pchn_g1a_point_xiangxing", "《日月水火》：日、月、水、火的象形演变", 4, SUBJECT, 243002),
    (243019, "pchn_g1a_point_duiyun", "《对韵歌》：韵语识字与“云对雨、雪对风”", 5, SUBJECT, 243002),
    (243020, "pchn_g1a_point_stroke_basic", "基本笔画：横、竖、撇、捺、点、提的书写", 6, SUBJECT, 243002),
    (243021, "pchn_g1a_point_stroke_order", "笔顺规则：先横后竖、先撇后捺、从上到下、从左到右", 7, SUBJECT, 243002),
    (243022, "pchn_g1a_point_tianzige", "田字格：认识横中线竖中线，把字写在格子中间", 8, SUBJECT, 243002),
    (243023, "pchn_g1a_point_radical_basic", "成字偏旁初步：口字旁、日字旁、月字旁", 9, SUBJECT, 243002),
    (243024, "pchn_g1a_point_antonym_basic", "反义词：天—地、上—下、大—小", 10, SUBJECT, 243002),

    # 汉语拼音（一）
    (243025, "pchn_g1a_point_pinyin_aoe", "单韵母 a、o、e 的发音与四声读法", 1, SUBJECT, 243003),
    (243026, "pchn_g1a_point_pinyin_iuu", "单韵母 i、u、ü 的发音与四声读法", 2, SUBJECT, 243003),
    (243027, "pchn_g1a_point_pinyin_bpmf", "声母 b、p、m、f 的发音与两拼音节", 3, SUBJECT, 243003),
    (243028, "pchn_g1a_point_pinyin_dtnl", "声母 d、t、n、l 的发音与两拼音节", 4, SUBJECT, 243003),
    (243029, "pchn_g1a_point_pinyin_gkh", "声母 g、k、h 的发音与两拼音节", 5, SUBJECT, 243003),
    (243030, "pchn_g1a_point_pinyin_jqx", "声母 j、q、x：与 ü 相拼时去掉两点", 6, SUBJECT, 243003),
    (243031, "pchn_g1a_point_pinyin_zcs", "声母 z、c、s 与平舌音的发音要点", 7, SUBJECT, 243003),
    (243032, "pchn_g1a_point_pinyin_zhchshr", "声母 zh、ch、sh、r 与翘舌音的发音要点", 8, SUBJECT, 243003),
    (243033, "pchn_g1a_point_pinyin_yiwuyu", "整体认读音节 yi、wu、yu 的识记", 9, SUBJECT, 243003),
    (243034, "pchn_g1a_point_pinyin_spell", "两拼音节：声母轻短、韵母响亮，快速连读", 10, SUBJECT, 243003),
    (243035, "pchn_g1a_point_pinyin_tone", "四声调号：一声平、二声扬、三声拐弯、四声降", 11, SUBJECT, 243003),
    (243036, "pchn_g1a_point_pinyin_tone_mark", "标调规则：有 a 不放过，没 a 找 o e，i u 并列标在后", 12, SUBJECT, 243003),
    (243037, "pchn_g1a_point_pinyin_grid", "四线三格：声母韵母与调号的书写位置", 13, SUBJECT, 243003),

    # 汉语拼音（二）
    (243038, "pchn_g1a_point_pinyin_aieiui", "复韵母 ai、ei、ui 的发音与标调", 1, SUBJECT, 243004),
    (243039, "pchn_g1a_point_pinyin_aoouiu", "复韵母 ao、ou、iu 的发音与标调", 2, SUBJECT, 243004),
    (243040, "pchn_g1a_point_pinyin_ieueer", "复韵母 ie、üe 与特殊韵母 er，整体认读 ye、yue", 3, SUBJECT, 243004),
    (243041, "pchn_g1a_point_pinyin_front_nasal", "前鼻韵母 an、en、in、un、ün 的发音", 4, SUBJECT, 243004),
    (243042, "pchn_g1a_point_pinyin_back_nasal", "后鼻韵母 ang、eng、ing、ong 的发音", 5, SUBJECT, 243004),
    (243043, "pchn_g1a_point_pinyin_sanpin", "三拼音节：声母、介母、韵母的连续拼读", 6, SUBJECT, 243004),
    (243044, "pchn_g1a_point_pinyin_word", "带调音节拼读词语，如“白兔”“乌龟”“菊花”", 7, SUBJECT, 243004),
    (243045, "pchn_g1a_point_pinyin_light", "轻声与儿化的初步感知，如“妈妈”“花儿”", 8, SUBJECT, 243004),

    # 课文（一）
    (243046, "pchn_g1a_point_text_qiutian", "《秋天》：天气、树叶、大雁的变化与背诵", 1, SUBJECT, 243005),
    (243047, "pchn_g1a_point_text_boat", "《小小的船》：弯月比小船，体会想象之美", 2, SUBJECT, 243005),
    (243048, "pchn_g1a_point_text_jiangnan", "《江南》：鱼戏莲叶东、西、南、北的方位", 3, SUBJECT, 243005),
    (243049, "pchn_g1a_point_text_siji", "《四季》：草芽、荷叶、谷穗、雪人的季节特征", 4, SUBJECT, 243005),
    (243050, "pchn_g1a_point_text_pause", "朗读停顿与问句语气：读出疑问与感叹", 5, SUBJECT, 243005),
    (243051, "pchn_g1a_point_text_word1", "课文（一）生字：秋、气、了、树、叶、片、大、飞", 6, SUBJECT, 243005),
    (243052, "pchn_g1a_point_text_friend", "口语交际“我们做朋友”：自我介绍与主动询问", 7, SUBJECT, 243005),
    (243053, "pchn_g1a_point_text_imitate", "仿说句式“弯弯的月儿小小的船”", 8, SUBJECT, 243005),

    # 识字（二）
    (243054, "pchn_g1a_point_hua", "《画》：远看山有色、近听水无声的反衬", 1, SUBJECT, 243006),
    (243055, "pchn_g1a_point_daxiao", "《大小多少》：一头牛、一只猫等量词搭配", 2, SUBJECT, 243006),
    (243056, "pchn_g1a_point_schoolbag", "《小书包》：文具名称与爱护学习用品", 3, SUBJECT, 243006),
    (243057, "pchn_g1a_point_riming", "《日月明》：日月明、田力男等会意字", 4, SUBJECT, 243006),
    (243058, "pchn_g1a_point_flag", "《升国旗》：升旗礼仪与“立正、敬礼”", 5, SUBJECT, 243006),
    (243059, "pchn_g1a_point_radical_more", "偏旁积累：单人旁、三点水、木字旁、提手旁", 6, SUBJECT, 243006),
    (243060, "pchn_g1a_point_structure", "汉字结构：独体字、左右结构、上下结构", 7, SUBJECT, 243006),
    (243061, "pchn_g1a_point_measure", "量词选用：个、只、头、条、把、片", 8, SUBJECT, 243006),
    (243062, "pchn_g1a_point_antonym_more", "反义词积累：多—少、大—小、来—去", 9, SUBJECT, 243006),

    # 课文（二）
    (243063, "pchn_g1a_point_shadow", "《影子》：前、后、左、右方位词与生活观察", 1, SUBJECT, 243007),
    (243064, "pchn_g1a_point_tail", "《比尾巴》：问答句式与动物尾巴的特点", 2, SUBJECT, 243007),
    (243065, "pchn_g1a_point_frog_poem", "《青蛙写诗》：逗号、句号、省略号的形象认识", 3, SUBJECT, 243007),
    (243066, "pchn_g1a_point_rain", "《雨点儿》：分角色对话与“数不清”的表达", 4, SUBJECT, 243007),
    (243067, "pchn_g1a_point_punctuation", "标点初步：句号、问号、感叹号的用法与朗读", 5, SUBJECT, 243007),
    (243068, "pchn_g1a_point_recite2", "背诵《影子》《比尾巴》，做到不加字不漏字", 6, SUBJECT, 243007),
    (243069, "pchn_g1a_point_picture_speak", "看图说话：按顺序说清人物、动作与地点", 7, SUBJECT, 243007),

    # 课文（三）
    (243070, "pchn_g1a_point_faraway", "《明天要远足》：翻来覆去睡不着，读出盼望", 1, SUBJECT, 243008),
    (243071, "pchn_g1a_point_bigsmall", "《大还是小》：成长体验中的对比与自豪", 2, SUBJECT, 243008),
    (243072, "pchn_g1a_point_necklace", "《项链》：浪花、沙滩与“彩色项链”的比喻", 3, SUBJECT, 243008),
    (243073, "pchn_g1a_point_emotion_read", "情感朗读：读出盼望、惊喜与自豪的语气", 4, SUBJECT, 243008),
    (243074, "pchn_g1a_point_collocation", "词语搭配：雪白的浪花、黄黄的沙滩、小小的海螺", 5, SUBJECT, 243008),
    (243075, "pchn_g1a_point_youde", "写话起步：用“有的……有的……”说完整句子", 6, SUBJECT, 243008),
    (243076, "pchn_g1a_point_life_literacy", "生活识字：从招牌、包装、广告中主动认字", 7, SUBJECT, 243008),

    # 课文（四）
    (243077, "pchn_g1a_point_painter", "《雪地里的小画家》：动物脚印与课文背诵", 1, SUBJECT, 243009),
    (243078, "pchn_g1a_point_crow", "《乌鸦喝水》：仔细观察、动脑想办法", 2, SUBJECT, 243009),
    (243079, "pchn_g1a_point_snail", "《小蜗牛》：四季变化与蜗牛妈妈的对话", 3, SUBJECT, 243009),
    (243080, "pchn_g1a_point_picture_write", "看图写话四要素：时间、地点、人物、事情", 4, SUBJECT, 243009),
    (243081, "pchn_g1a_point_full_sentence", "写完整句子：谁＋在哪里＋做什么", 5, SUBJECT, 243009),
    (243082, "pchn_g1a_point_long_sentence", "长句停顿：用逗号把意思说清楚", 6, SUBJECT, 243009),
    (243083, "pchn_g1a_point_final_review", "期末复习：拼音拼读、生字书写与课文背诵综合", 7, SUBJECT, 243009),
)

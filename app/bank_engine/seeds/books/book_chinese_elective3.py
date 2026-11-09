"""统编版（2019）高中语文选择性必修下册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G10 = 10
BOOK_ID = 1105

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版（2019）高中语文选择性必修下册",
    "chn_x3",
    3,
    "人民教育出版社",
    SUBJECT,
    G10,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    (110501, "第一单元 中华传统文化经典研习", "chn_x3_u01", 1, BOOK_ID, None),
    (110502, "第二单元 中国现当代作家作品研习", "chn_x3_u02", 2, BOOK_ID, None),
    (110503, "第三单元 古代散文", "chn_x3_u03", 3, BOOK_ID, None),
    (110504, "第四单元 科学与文化论著研习", "chn_x3_u04", 4, BOOK_ID, None),
    (110505, "古诗词诵读", "chn_x3_u05", 5, BOOK_ID, None),
    (110511, "第1课 氓／离骚（节选）", "chn_x3_l01", 1, BOOK_ID, 110501),
    (110512, "第2课 孔雀东南飞并序", "chn_x3_l02", 2, BOOK_ID, 110501),
    (110513, "第3课 蜀道难／蜀相", "chn_x3_l03", 3, BOOK_ID, 110501),
    (110514, "第4课 望海潮（东南形胜）／扬州慢（淮左名都）", "chn_x3_l04", 4, BOOK_ID, 110501),
    (110515, "第5课 阿Q正传（节选）", "chn_x3_l05", 1, BOOK_ID, 110502),
    (110516, "第6课 边城（节选）", "chn_x3_l06", 2, BOOK_ID, 110502),
    (110517, "第7课 大堰河——我的保姆／再别康桥", "chn_x3_l07", 3, BOOK_ID, 110502),
    (110518, "第8课 茶馆（节选）", "chn_x3_l08", 4, BOOK_ID, 110502),
    (110519, "第9课 陈情表", "chn_x3_l09", 1, BOOK_ID, 110503),
    (110520, "第10课 项脊轩志", "chn_x3_l10", 2, BOOK_ID, 110503),
    (110521, "第11课 归去来兮辞并序", "chn_x3_l11", 3, BOOK_ID, 110503),
    (110522, "第12课 兰亭集序", "chn_x3_l12", 4, BOOK_ID, 110503),
    (110523, "第13课 自然选择的证明／宇宙的边疆", "chn_x3_l13", 1, BOOK_ID, 110504),
    (110524, "第14课 天文学上的旷世之争", "chn_x3_l14", 2, BOOK_ID, 110504),
    (110525, "拟行路难（其四）／客至", "chn_x3_l15", 1, BOOK_ID, 110505),
    (110526, "临安春雨初霁／贺新郎·国脉微如缕", "chn_x3_l16", 2, BOOK_ID, 110505),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 150001-150010 为册域与文体能力层，150011-150099 为逐课细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (150001, "chn_x3_domain_classic_poetry", "第一单元 中华传统文化经典研习：诗骚传统与乐府歌行", 1, SUBJECT, G10, None),
    (150002, "chn_x3_domain_modern", "第二单元 中国现当代作家作品研习：国民性批判与乡土诗学", 2, SUBJECT, G10, None),
    (150003, "chn_x3_domain_prose", "第三单元 古代散文：抒情言志与情理兼胜", 3, SUBJECT, G10, None),
    (150004, "chn_x3_domain_science", "第四单元 科学与文化论著研习：科学论证与科学精神", 4, SUBJECT, G10, None),
    (150005, "chn_x3_domain_chant", "古诗词诵读：魏晋至南宋的诗心词境", 5, SUBJECT, G10, None),
    (150006, "chn_x3_domain_classical", "文言实词、虚词、特殊句式与古代文化常识", 6, SUBJECT, G10, None),
    (150007, "chn_x3_domain_argument", "论述类与说明类文本：概念、证据与推理", 7, SUBJECT, G10, None),
    (150008, "chn_x3_domain_narrative", "小说与戏剧：人物、结构、语言", 8, SUBJECT, G10, None),
    (150009, "chn_x3_domain_language", "本册语言积累、诵读与默写训练", 9, SUBJECT, G10, None),
    (150010, "chn_x3_domain_task", "本册单元研习任务与文学短评写作", 10, SUBJECT, G10, None),

    # 第一单元 中华传统文化经典研习
    (150011, "chn_x3_point_meng_narrative", "《氓》从“氓之蚩蚩”到“士贰其行”的叙事线索与弃妇情感变化", 1, SUBJECT, G10, 150001),
    (150012, "chn_x3_point_meng_bixing", "《氓》“桑之未落／桑之落矣”的比兴与自然意象映射", 2, SUBJECT, G10, 150001),
    (150013, "chn_x3_point_meng_resolve", "《氓》女主人公“反是不思，亦已焉哉”的决绝与自省", 3, SUBJECT, G10, 150001),
    (150014, "chn_x3_point_lisao_symbol", "《离骚（节选）》香草美人象征体系与高洁人格的自塑", 4, SUBJECT, G10, 150001),
    (150015, "chn_x3_point_lisao_ideal", "《离骚（节选）》“长太息以掩涕兮”的忧民情怀与美政理想", 5, SUBJECT, G10, 150001),
    (150016, "chn_x3_point_lisao_rhythm", "《离骚（节选）》楚辞体“兮”字句与回环往复的抒情节奏", 6, SUBJECT, G10, 150001),
    (150017, "chn_x3_point_kongque_structure", "《孔雀东南飞》叙事诗的双线结构与悲剧意蕴", 7, SUBJECT, G10, 150001),
    (150018, "chn_x3_point_kongque_figure", "《孔雀东南飞》刘兰芝、焦仲卿形象与封建家长制的冲突", 8, SUBJECT, G10, 150001),
    (150019, "chn_x3_point_kongque_pufu", "《孔雀东南飞》“十三能织素”铺陈排比与乐府民歌的夸饰笔法", 9, SUBJECT, G10, 150001),
    (150020, "chn_x3_point_kongque_ending", "《孔雀东南飞》结尾化鸟的浪漫主义处理与民间叙事传统", 10, SUBJECT, G10, 150001),
    (150021, "chn_x3_point_shudao_refrain", "《蜀道难》“蜀道之难，难于上青天”三叠反复与情感层递", 11, SUBJECT, G10, 150001),
    (150022, "chn_x3_point_shudao_imagine", "《蜀道难》神话传说、夸张想象与奇崛的语言气势", 12, SUBJECT, G10, 150001),
    (150023, "chn_x3_point_shuxiang_allusion", "《蜀相》“三顾频烦天下计”的用典与诸葛亮形象塑造", 13, SUBJECT, G10, 150001),
    (150024, "chn_x3_point_shuxiang_emotion", "《蜀相》“出师未捷身先死”的沉郁顿挫与咏史怀古之情", 14, SUBJECT, G10, 150001),
    (150025, "chn_x3_point_wanghai_praise", "《望海潮（东南形胜）》铺叙杭州形胜繁华与干谒词的颂美策略", 15, SUBJECT, G10, 150001),
    (150026, "chn_x3_point_yangzhou_contrast", "《扬州慢（淮左名都）》今昔对照与“黍离之悲”的化用", 16, SUBJECT, G10, 150001),
    (150027, "chn_x3_point_yangzhou_manci", "《扬州慢（淮左名都）》自度曲小序与慢词长调的声情", 17, SUBJECT, G10, 150001),

    # 第二单元 中国现当代作家作品研习
    (150028, "chn_x3_point_aq_victory", "《阿Q正传》精神胜利法的讽刺叙事与国民性批判", 1, SUBJECT, G10, 150002),
    (150029, "chn_x3_point_aq_irony", "《阿Q正传》“优胜记略”式反讽与叙述者的冷峻语调", 2, SUBJECT, G10, 150002),
    (150030, "chn_x3_point_aq_society", "《阿Q正传》未庄社会结构、看客心理与革命误读", 3, SUBJECT, G10, 150002),
    (150031, "chn_x3_point_aq_style", "《阿Q正传》白描漫画笔法与“哀其不幸，怒其不争”", 4, SUBJECT, G10, 150002),
    (150032, "chn_x3_point_biancheng_custom", "《边城（节选）》茶峒风俗画与湘西世界的牧歌情调", 5, SUBJECT, G10, 150002),
    (150033, "chn_x3_point_biancheng_love", "《边城（节选）》翠翠与傩送、天保情感纠葛的含蓄表达", 6, SUBJECT, G10, 150002),
    (150034, "chn_x3_point_biancheng_scene", "《边城（节选）》景物描写与人物心理融合的抒情化叙事", 7, SUBJECT, G10, 150002),
    (150035, "chn_x3_point_biancheng_ideal", "《边城（节选）》“边城”意象与沈从文的乡土理想", 8, SUBJECT, G10, 150002),
    (150036, "chn_x3_point_dayanhe_parallel", "《大堰河——我的保姆》排比复沓中的深情追怀与阶级意识", 9, SUBJECT, G10, 150002),
    (150037, "chn_x3_point_dayanhe_detail", "《大堰河——我的保姆》“乌黑的酱碗”等细节白描与苦难书写", 10, SUBJECT, G10, 150002),
    (150038, "chn_x3_point_kangqiao_beauty", "《再别康桥》音乐美、绘画美、建筑美的“三美”实践", 11, SUBJECT, G10, 150002),
    (150039, "chn_x3_point_kangqiao_echo", "《再别康桥》“轻轻的／悄悄的”首尾呼应与人景合一", 12, SUBJECT, G10, 150002),
    (150040, "chn_x3_point_chaguan_structure", "《茶馆（节选）》三幕剧结构与“葬送三个时代”的史诗构想", 13, SUBJECT, G10, 150002),
    (150041, "chn_x3_point_chaguan_language", "《茶馆（节选）》王利发等人物群像与京味语言", 14, SUBJECT, G10, 150002),

    # 第三单元 古代散文
    (150042, "chn_x3_point_chenqing_persuade", "《陈情表》以情动人的层递说理与骈散结合语言", 1, SUBJECT, G10, 150003),
    (150043, "chn_x3_point_chenqing_origin", "《陈情表》“臣以险衅，夙遭闵凶”的身世叙述与孤苦铺陈", 2, SUBJECT, G10, 150003),
    (150044, "chn_x3_point_chenqing_filial", "《陈情表》“圣朝以孝治天下”的立论依据与委婉抗旨", 3, SUBJECT, G10, 150003),
    (150045, "chn_x3_point_chenqing_gratitude", "《陈情表》“生当陨首，死当结草”的感恩表态与分寸把握", 4, SUBJECT, G10, 150003),
    (150046, "chn_x3_point_xiangji_rise", "《项脊轩志》以轩为线索的今昔盛衰与家族变迁", 5, SUBJECT, G10, 150003),
    (150047, "chn_x3_point_xiangji_loquat", "《项脊轩志》“庭有枇杷树”的细节收束与悼亡深情", 6, SUBJECT, G10, 150003),
    (150048, "chn_x3_point_xiangji_detail", "《项脊轩志》平淡笔墨中的生活细节与至情表达", 7, SUBJECT, G10, 150003),
    (150049, "chn_x3_point_xiangji_supplement", "《项脊轩志》补记的叙事时间与情感层次", 8, SUBJECT, G10, 150003),
    (150050, "chn_x3_point_guiqulai_call", "《归去来兮辞并序》“归去来兮”的反复呼告与归田决绝", 9, SUBJECT, G10, 150003),
    (150051, "chn_x3_point_guiqulai_image", "《归去来兮辞并序》云、鸟、松、菊等田园意象与精神自由", 10, SUBJECT, G10, 150003),
    (150052, "chn_x3_point_guiqulai_genre", "《归去来兮辞并序》“序”与“辞”的文体分工和互文关系", 11, SUBJECT, G10, 150003),
    (150053, "chn_x3_point_guiqulai_rhythm", "《归去来兮辞并序》骈偶句式、六字句节奏与陶渊明自然文风", 12, SUBJECT, G10, 150003),
    (150054, "chn_x3_point_lanting_turn", "《兰亭集序》由乐转悲的情感转折与“死生亦大矣”的哲思", 13, SUBJECT, G10, 150003),
    (150055, "chn_x3_point_lanting_critique", "《兰亭集序》“固知一死生为虚诞”对玄学虚无论的批判", 14, SUBJECT, G10, 150003),
    (150056, "chn_x3_point_lanting_structure", "《兰亭集序》骈散相间、俯仰今昔的章法与书序文体特征", 15, SUBJECT, G10, 150003),
    (150057, "chn_x3_point_lanting_scene", "《兰亭集序》“崇山峻岭，茂林修竹”的景物描写与雅集氛围", 16, SUBJECT, G10, 150003),

    # 第四单元 科学与文化论著研习
    (150058, "chn_x3_point_selection_argument", "《自然选择的证明》达尔文进化论的核心论证与归纳推理", 1, SUBJECT, G10, 150004),
    (150059, "chn_x3_point_selection_evidence", "《自然选择的证明》观察事实、数据材料与假说—验证结构", 2, SUBJECT, G10, 150004),
    (150060, "chn_x3_point_selection_language", "《自然选择的证明》限定语与逻辑关联词构筑的严密表述", 3, SUBJECT, G10, 150004),
    (150061, "chn_x3_point_universe_order", "《宇宙的边疆》空间尺度递进的说明顺序与解说词文体", 4, SUBJECT, G10, 150004),
    (150062, "chn_x3_point_universe_rhetoric", "《宇宙的边疆》比喻、设问与第二人称的科普表达效果", 5, SUBJECT, G10, 150004),
    (150063, "chn_x3_point_universe_humanism", "《宇宙的边疆》科学理性与人文关怀交融的抒情议论", 6, SUBJECT, G10, 150004),
    (150064, "chn_x3_point_astronomy_debate", "《天文学上的旷世之争》日心说与地心说之争的论证梳理", 7, SUBJECT, G10, 150004),
    (150065, "chn_x3_point_astronomy_method", "《天文学上的旷世之争》“摆事实、讲道理”的科学史论辩方法", 8, SUBJECT, G10, 150004),
    (150066, "chn_x3_point_astronomy_spirit", "《天文学上的旷世之争》科学假说的可证伪性与科学精神", 9, SUBJECT, G10, 150004),
    (150067, "chn_x3_point_science_genre", "科学与文化论著的文体特征：术语准确、逻辑严密与可读性", 10, SUBJECT, G10, 150004),

    # 古诗词诵读
    (150068, "chn_x3_point_nixing_metaphor", "《拟行路难（其四）》“泻水置平地”的起兴与门第压抑之愤", 1, SUBJECT, G10, 150005),
    (150069, "chn_x3_point_nixing_rhythm", "《拟行路难（其四）》长短句错落与“吞声踯躅”的情感节制", 2, SUBJECT, G10, 150005),
    (150070, "chn_x3_point_kezhi_scene", "《客至》“舍南舍北皆春水”的闲适情境与待客真情", 3, SUBJECT, G10, 150005),
    (150071, "chn_x3_point_kezhi_detail", "《客至》“花径不曾缘客扫”等家常细节中的生活诗意", 4, SUBJECT, G10, 150005),
    (150072, "chn_x3_point_linan_rain", "《临安春雨初霁》“小楼一夜听春雨”的听觉意象与客居无聊", 5, SUBJECT, G10, 150005),
    (150073, "chn_x3_point_linan_tired", "《临安春雨初霁》“素衣莫起风尘叹”的京华倦意与归隐之思", 6, SUBJECT, G10, 150005),
    (150074, "chn_x3_point_hexinjin_politics", "《贺新郎·国脉微如缕》“国脉微如缕”的时局忧思与用典", 7, SUBJECT, G10, 150005),
    (150075, "chn_x3_point_hexinjin_style", "《贺新郎·国脉微如缕》豪放词风、散文化句法与议论入词", 8, SUBJECT, G10, 150005),

    # 文言实词、虚词、特殊句式与古代文化常识
    (150076, "chn_x3_point_classical_word", "本册通假字、古今异义与一词多义的语境辨析", 1, SUBJECT, G10, 150006),
    (150077, "chn_x3_point_classical_flex", "本册词类活用：名词作状语、使动与意动用法", 2, SUBJECT, G10, 150006),
    (150078, "chn_x3_point_classical_pattern", "本册特殊句式：判断句、被动句、宾语前置与状语后置", 3, SUBJECT, G10, 150006),
    (150079, "chn_x3_point_classical_function", "本册虚词“以、之、其、于、而”的用法辨析", 4, SUBJECT, G10, 150006),
    (150080, "chn_x3_point_classical_culture", "古代文化常识：科举、官职、礼制与纪年纪时", 5, SUBJECT, G10, 150006),
    (150081, "chn_x3_point_classical_honorific", "《陈情表》《兰亭集序》中的敬辞谦辞与表章书序体例", 6, SUBJECT, G10, 150006),
    (150082, "chn_x3_point_classical_translate", "文言翻译的留、删、换、调、补原则与得分点意识", 7, SUBJECT, G10, 150006),

    # 论述类与说明类文本
    (150083, "chn_x3_point_argument_chain", "论述类文本中心论点的定位与论据—论证—结论链条梳理", 1, SUBJECT, G10, 150007),
    (150084, "chn_x3_point_argument_concept", "自然科学论著中概念界定与逻辑推理的严密性分析", 2, SUBJECT, G10, 150007),
    (150085, "chn_x3_point_argument_explain", "科普说明文的说明顺序、说明方法与语言特点", 3, SUBJECT, G10, 150007),
    (150086, "chn_x3_point_argument_method", "论证方法辨析：举例、引用、对比、类比与归谬", 4, SUBJECT, G10, 150007),
    (150087, "chn_x3_point_argument_option", "文本信息筛选整合与选项设误（偷换概念、以偏概全）辨识", 5, SUBJECT, G10, 150007),
    (150088, "chn_x3_point_argument_doubt", "科学与文化论著阅读中的质疑、求证与跨学科视野", 6, SUBJECT, G10, 150007),

    # 小说与戏剧
    (150089, "chn_x3_point_narrative_figure", "小说人物形象的典型化与细节、语言、心理描写分析", 1, SUBJECT, G10, 150008),
    (150090, "chn_x3_point_narrative_view", "叙事视角（限知／全知）与叙述者语调的表达功能", 2, SUBJECT, G10, 150008),
    (150091, "chn_x3_point_narrative_conflict", "戏剧冲突的类型（性格、阶级、命运）与舞台说明的作用", 3, SUBJECT, G10, 150008),
    (150092, "chn_x3_point_narrative_poetry", "诗歌意象、意境与抒情手法的鉴赏路径", 4, SUBJECT, G10, 150008),
    (150093, "chn_x3_point_narrative_region", "现当代作品的京味、湘西风情等地域文化书写", 5, SUBJECT, G10, 150008),

    # 语言积累运用与名句默写
    (150094, "chn_x3_point_language_dictation", "本册名句默写范围与易错字形（《离骚》《陈情表》等）", 1, SUBJECT, G10, 150009),
    (150095, "chn_x3_point_language_recite", "诗歌诵读的节奏、重音与情感基调把握", 2, SUBJECT, G10, 150009),
    (150096, "chn_x3_point_language_use", "语言运用：修辞辨析、句式变换与语病修改", 3, SUBJECT, G10, 150009),

    # 单元研习任务与读写转化
    (150097, "chn_x3_point_task_note", "单元研习任务：古典诗歌的意象梳理与比较阅读笔记", 1, SUBJECT, G10, 150010),
    (150098, "chn_x3_point_task_review", "文学短评写作：从人物、结构、语言切入的评论方法", 2, SUBJECT, G10, 150010),
    (150099, "chn_x3_point_task_reading", "整本书阅读《红楼梦》与单元主题的读写转化", 3, SUBJECT, G10, 150010),
)

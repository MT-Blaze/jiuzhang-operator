"""统编版小学语文一年级下册：八个单元课文、识字与语文园地的知识点树。"""

from __future__ import annotations

SUBJECT = 1
G1 = 1
BOOK_ID = 1402

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版小学语文一年级下册",
    "pchn_g1b",
    2,
    "人民教育出版社",
    SUBJECT,
    G1,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 八个单元
    (140201, "第一单元 识字（一）", "pchn_g1b_u01", 1, BOOK_ID, None),
    (140202, "第二单元 课文（一）", "pchn_g1b_u02", 2, BOOK_ID, None),
    (140203, "第三单元 课文（二）", "pchn_g1b_u03", 3, BOOK_ID, None),
    (140204, "第四单元 课文（三）", "pchn_g1b_u04", 4, BOOK_ID, None),
    (140205, "第五单元 识字（二）", "pchn_g1b_u05", 5, BOOK_ID, None),
    (140206, "第六单元 课文（四）", "pchn_g1b_u06", 6, BOOK_ID, None),
    (140207, "第七单元 课文（五）", "pchn_g1b_u07", 7, BOOK_ID, None),
    (140208, "第八单元 课文（六）", "pchn_g1b_u08", 8, BOOK_ID, None),

    # 第一单元 识字（一）
    (140211, "识字1 春夏秋冬", "pchn_g1b_l01", 1, BOOK_ID, 140201),
    (140212, "识字2 姓氏歌", "pchn_g1b_l02", 2, BOOK_ID, 140201),
    (140213, "识字3 小青蛙", "pchn_g1b_l03", 3, BOOK_ID, 140201),
    (140214, "识字4 猜字谜", "pchn_g1b_l04", 4, BOOK_ID, 140201),
    (140215, "口语交际·听故事，讲故事", "pchn_g1b_l05", 5, BOOK_ID, 140201),
    (140216, "语文园地一", "pchn_g1b_l06", 6, BOOK_ID, 140201),

    # 第二单元 课文（一）
    (140221, "课文1 吃水不忘挖井人", "pchn_g1b_l07", 1, BOOK_ID, 140202),
    (140222, "课文2 我多想去看看", "pchn_g1b_l08", 2, BOOK_ID, 140202),
    (140223, "课文3 一个接一个", "pchn_g1b_l09", 3, BOOK_ID, 140202),
    (140224, "课文4 四个太阳", "pchn_g1b_l10", 4, BOOK_ID, 140202),
    (140225, "语文园地二", "pchn_g1b_l11", 5, BOOK_ID, 140202),

    # 第三单元 课文（二）
    (140231, "课文5 小公鸡和小鸭子", "pchn_g1b_l12", 1, BOOK_ID, 140203),
    (140232, "课文6 树和喜鹊", "pchn_g1b_l13", 2, BOOK_ID, 140203),
    (140233, "课文7 怎么都快乐", "pchn_g1b_l14", 3, BOOK_ID, 140203),
    (140234, "语文园地三", "pchn_g1b_l15", 4, BOOK_ID, 140203),

    # 第四单元 课文（三）
    (140241, "课文8 静夜思", "pchn_g1b_l16", 1, BOOK_ID, 140204),
    (140242, "课文9 夜色", "pchn_g1b_l17", 2, BOOK_ID, 140204),
    (140243, "课文10 端午粽", "pchn_g1b_l18", 3, BOOK_ID, 140204),
    (140244, "课文11 彩虹", "pchn_g1b_l19", 4, BOOK_ID, 140204),
    (140245, "语文园地四", "pchn_g1b_l20", 5, BOOK_ID, 140204),

    # 第五单元 识字（二）
    (140251, "识字5 动物儿歌", "pchn_g1b_l21", 1, BOOK_ID, 140205),
    (140252, "识字6 古对今", "pchn_g1b_l22", 2, BOOK_ID, 140205),
    (140253, "识字7 操场上", "pchn_g1b_l23", 3, BOOK_ID, 140205),
    (140254, "识字8 人之初", "pchn_g1b_l24", 4, BOOK_ID, 140205),
    (140255, "语文园地五", "pchn_g1b_l25", 5, BOOK_ID, 140205),

    # 第六单元 课文（四）
    (140261, "课文12 古诗二首（池上／小池）", "pchn_g1b_l26", 1, BOOK_ID, 140206),
    (140262, "课文13 荷叶圆圆", "pchn_g1b_l27", 2, BOOK_ID, 140206),
    (140263, "课文14 要下雨了", "pchn_g1b_l28", 3, BOOK_ID, 140206),
    (140264, "语文园地六", "pchn_g1b_l29", 4, BOOK_ID, 140206),

    # 第七单元 课文（五）
    (140271, "课文15 文具的家", "pchn_g1b_l30", 1, BOOK_ID, 140207),
    (140272, "课文16 一分钟", "pchn_g1b_l31", 2, BOOK_ID, 140207),
    (140273, "课文17 动物王国开大会", "pchn_g1b_l32", 3, BOOK_ID, 140207),
    (140274, "课文18 小猴子下山", "pchn_g1b_l33", 4, BOOK_ID, 140207),
    (140275, "语文园地七", "pchn_g1b_l34", 5, BOOK_ID, 140207),

    # 第八单元 课文（六）
    (140281, "课文19 棉花姑娘", "pchn_g1b_l35", 1, BOOK_ID, 140208),
    (140282, "课文20 咕咚", "pchn_g1b_l36", 2, BOOK_ID, 140208),
    (140283, "课文21 小壁虎借尾巴", "pchn_g1b_l37", 3, BOOK_ID, 140208),
    (140284, "语文园地八", "pchn_g1b_l38", 4, BOOK_ID, 140208),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 244001-244008 为册域层，244011-244099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (244001, "pchn_g1b_domain_literacy1", "小学一下·识字（一）四季姓氏与字谜", 1, SUBJECT, G1, None),
    (244002, "pchn_g1b_domain_text1", "小学一下·课文（一）感恩与愿望", 2, SUBJECT, G1, None),
    (244003, "pchn_g1b_domain_text2", "小学一下·课文（二）伙伴与快乐", 3, SUBJECT, G1, None),
    (244004, "pchn_g1b_domain_text3", "小学一下·课文（三）思乡与传统节日", 4, SUBJECT, G1, None),
    (244005, "pchn_g1b_domain_literacy2", "小学一下·识字（二）对韵与蒙学", 5, SUBJECT, G1, None),
    (244006, "pchn_g1b_domain_text4", "小学一下·课文（四）古诗与自然观察", 6, SUBJECT, G1, None),
    (244007, "pchn_g1b_domain_text5", "小学一下·课文（五）习惯与做事条理", 7, SUBJECT, G1, None),
    (244008, "pchn_g1b_domain_text6", "小学一下·课文（六）科普童话与互助", 8, SUBJECT, G1, None),

    # 识字（一）
    (244011, "pchn_g1b_point_seasons_words", "《春夏秋冬》：春风、夏雨、秋霜、冬雪四季词语搭配", 1, SUBJECT, G1, 244001),
    (244012, "pchn_g1b_point_seasons_chars", "《春夏秋冬》生字：霜、吹、落、降、飘的偏旁与书写", 2, SUBJECT, G1, 244001),
    (244013, "pchn_g1b_point_surname_reading", "《姓氏歌》：常见姓氏认读与“木子李、弓长张”拆字介绍", 3, SUBJECT, G1, 244001),
    (244014, "pchn_g1b_point_surname_qa", "《姓氏歌》问答句式：“你姓什么？我姓……”", 4, SUBJECT, G1, 244001),
    (244015, "pchn_g1b_point_qing_family", "《小青蛙》：“青”字家族清、晴、情、请、睛的形声规律", 5, SUBJECT, G1, 244001),
    (244016, "pchn_g1b_point_qing_radicals", "青字家族偏旁辨析：三点水、日字旁、竖心旁、言字旁、目字旁", 6, SUBJECT, G1, 244001),
    (244017, "pchn_g1b_point_riddle_method", "《猜字谜》：合体法与会意法猜字，如“一加一”为“王”", 7, SUBJECT, G1, 244001),
    (244018, "pchn_g1b_point_riddle_text", "《猜字谜》“言来互相尊重，心至令人感动”的字谜理解", 8, SUBJECT, G1, 244001),
    (244019, "pchn_g1b_point_literacy1_duoyin", "多音字：落（luò／là）、降（jiàng／xiáng）", 9, SUBJECT, G1, 244001),
    (244020, "pchn_g1b_point_literacy1_antonym", "反义词：春—秋、夏—冬、出—入、古—今", 10, SUBJECT, G1, 244001),
    (244021, "pchn_g1b_point_literacy1_measure", "量词与叠词：一阵风、一片雪花、一朵花", 11, SUBJECT, G1, 244001),
    (244022, "pchn_g1b_point_listen_story", "口语交际“听故事，讲故事”：听清内容并借图画复述", 12, SUBJECT, G1, 244001),

    # 课文（一）
    (244023, "pchn_g1b_point_well_water", "《吃水不忘挖井人》：毛主席带领挖井与饮水思源", 1, SUBJECT, G1, 244002),
    (244024, "pchn_g1b_point_well_words", "《吃水不忘挖井人》生字：忘、井、村、叫、主、席、乡、亲", 2, SUBJECT, G1, 244002),
    (244025, "pchn_g1b_point_want_see", "《我多想去看看》：北京城与天山两个孩子的愿望", 3, SUBJECT, G1, 244002),
    (244026, "pchn_g1b_point_one_after_another", "《一个接一个》：“正……就……”句式与心情转换", 4, SUBJECT, G1, 244002),
    (244027, "pchn_g1b_point_four_suns", "《四个太阳》：四季太阳的颜色与美好心愿", 5, SUBJECT, G1, 244002),
    (244028, "pchn_g1b_point_text1_duoyin", "多音字：着（zhe／zháo）、觉（jué／jiào）", 6, SUBJECT, G1, 244002),
    (244029, "pchn_g1b_point_text1_ba", "把字句：把井挖好、把太阳画成彩色", 7, SUBJECT, G1, 244002),
    (244030, "pchn_g1b_point_text1_punct", "感叹号与句号：读出愿望、惊喜与肯定的语气", 8, SUBJECT, G1, 244002),
    (244031, "pchn_g1b_point_text1_collocation", "词语搭配：弯弯的小路、宽宽的公路、美丽的天山", 9, SUBJECT, G1, 244002),
    (244032, "pchn_g1b_point_text1_wish", "写话：用“我多想……”说清自己的愿望", 10, SUBJECT, G1, 244002),

    # 课文（二）
    (244033, "pchn_g1b_point_rooster_duck", "《小公鸡和小鸭子》：伙伴互助与“偷偷地、飞快地”", 1, SUBJECT, G1, 244003),
    (244034, "pchn_g1b_point_tree_bird", "《树和喜鹊》：从孤单到快乐，有邻居才有快乐", 2, SUBJECT, G1, 244003),
    (244035, "pchn_g1b_point_how_happy", "《怎么都快乐》：一人、两人、三人、许多人玩的快乐", 3, SUBJECT, G1, 244003),
    (244036, "pchn_g1b_point_text2_words", "课文（二）生字：块、捉、急、直、河、行、死、信", 4, SUBJECT, G1, 244003),
    (244037, "pchn_g1b_point_text2_duoyin", "多音字：乐（lè／yuè）、只（zhī／zhǐ）", 5, SUBJECT, G1, 244003),
    (244038, "pchn_g1b_point_text2_aabb", "AABB叠词：叽叽喳喳、安安静静、快快乐乐", 6, SUBJECT, G1, 244003),
    (244039, "pchn_g1b_point_text2_de", "“地”字短语：偷偷地跟、飞快地游、大声地叫", 7, SUBJECT, G1, 244003),
    (244040, "pchn_g1b_point_text2_synonym", "近义词：孤单—孤独、快乐—高兴、忽然—突然", 8, SUBJECT, G1, 244003),
    (244041, "pchn_g1b_point_text2_read", "感叹句朗读：“你帮我，我帮你”读出互助的温暖", 9, SUBJECT, G1, 244003),

    # 课文（三）
    (244042, "pchn_g1b_point_jingyesi_homesick", "《静夜思》：李白望月思乡与“疑是地上霜”的比喻", 1, SUBJECT, G1, 244004),
    (244043, "pchn_g1b_point_jingyesi_recite", "《静夜思》背诵与四句诗的停顿节奏", 2, SUBJECT, G1, 244004),
    (244044, "pchn_g1b_point_night_brave", "《夜色》：从怕黑到勇敢，爸爸带“我”散步", 3, SUBJECT, G1, 244004),
    (244045, "pchn_g1b_point_duanwu", "《端午粽》：端午节包粽子、纪念屈原与外婆的粽子", 4, SUBJECT, G1, 244004),
    (244046, "pchn_g1b_point_rainbow", "《彩虹》：把彩虹想象成桥，为家人做事的心愿", 5, SUBJECT, G1, 244004),
    (244047, "pchn_g1b_point_text3_words", "课文（三）生字：思、床、前、光、低、故、乡", 6, SUBJECT, G1, 244004),
    (244048, "pchn_g1b_point_text3_duoyin", "多音字：分（fēn／fèn）、觉（jué／jiào）", 7, SUBJECT, G1, 244004),
    (244049, "pchn_g1b_point_text3_yijiu", "“一……就……”句式：我一回到家就写作业", 8, SUBJECT, G1, 244004),
    (244050, "pchn_g1b_point_duanwu_custom", "传统节日：端午节的时间、习俗与粽子的样子味道", 9, SUBJECT, G1, 244004),

    # 识字（二）
    (244051, "pchn_g1b_point_animal_song", "《动物儿歌》：蜻蜓、蝴蝶、蚯蚓、蚂蚁、蝌蚪、蜘蛛", 1, SUBJECT, G1, 244005),
    (244052, "pchn_g1b_point_animal_chong", "虫字旁形声字：蚂、蚁、蜻、蜓、蜘、蛛的音形义", 2, SUBJECT, G1, 244005),
    (244053, "pchn_g1b_point_gudui", "《古对今》：“古对今、圆对方、严寒对酷暑”对韵", 3, SUBJECT, G1, 244005),
    (244054, "pchn_g1b_point_gudui_antonym", "反义词：古—今、圆—方、严寒—酷暑、春暖—秋凉", 4, SUBJECT, G1, 244005),
    (244055, "pchn_g1b_point_playground", "《操场上》：打球、跑步、跳高等体育活动词语", 5, SUBJECT, G1, 244005),
    (244056, "pchn_g1b_point_hand_foot", "提手旁与足字旁动作字：打、拍、跑、跳、踢", 6, SUBJECT, G1, 244005),
    (244057, "pchn_g1b_point_sanzijing", "《人之初》：《三字经》节选与“人之初，性本善”", 7, SUBJECT, G1, 244005),
    (244058, "pchn_g1b_point_sanzijing_rhythm", "《三字经》诵读节奏与“苟不教，性乃迁”的含义", 8, SUBJECT, G1, 244005),
    (244059, "pchn_g1b_point_literacy2_duoyin", "多音字：朝（zhāo／cháo）、教（jiāo／jiào）", 9, SUBJECT, G1, 244005),
    (244060, "pchn_g1b_point_literacy2_phrase", "词语积累：蜻蜓展翅、蝴蝶飞舞、蚂蚁搬家", 10, SUBJECT, G1, 244005),

    # 课文（四）
    (244061, "pchn_g1b_point_chishang", "《池上》：小娃偷采白莲的天真与“不解藏踪迹”", 1, SUBJECT, G1, 244006),
    (244062, "pchn_g1b_point_xiaochi", "《小池》：泉眼、树阴、小荷、蜻蜓的初夏景色", 2, SUBJECT, G1, 244006),
    (244063, "pchn_g1b_point_ancient_recite", "《池上》《小池》背诵与白居易、杨万里两位诗人", 3, SUBJECT, G1, 244006),
    (244064, "pchn_g1b_point_lotus_roles", "《荷叶圆圆》：荷叶是小水珠的摇篮、小蜻蜓的停机坪等", 4, SUBJECT, G1, 244006),
    (244065, "pchn_g1b_point_rain_signs", "《要下雨了》：燕子低飞、小鱼透气、蚂蚁搬家预示下雨", 5, SUBJECT, G1, 244006),
    (244066, "pchn_g1b_point_metaphor", "比喻句：荷叶圆圆的、绿绿的，像一个大圆盘", 6, SUBJECT, G1, 244006),
    (244067, "pchn_g1b_point_text4_words", "课文（四）生字：珠、摇、躺、晶、停、机、展、透", 7, SUBJECT, G1, 244006),
    (244068, "pchn_g1b_point_text4_duoyin", "多音字：荷（hé／hè）、空（kōng／kòng）", 8, SUBJECT, G1, 244006),
    (244069, "pchn_g1b_point_text4_adj", "叠词与形容词：圆圆的、绿绿的、亮晶晶", 9, SUBJECT, G1, 244006),

    # 课文（五）
    (244070, "pchn_g1b_point_stationery", "《文具的家》：贝贝从乱丢文具到整理文具的好习惯", 1, SUBJECT, G1, 244007),
    (244071, "pchn_g1b_point_one_minute", "《一分钟》：元元多睡一分钟，结果迟到二十分钟", 2, SUBJECT, G1, 244007),
    (244072, "pchn_g1b_point_notice_story", "《动物王国开大会》：狗熊四次发通知逐步补全要素", 3, SUBJECT, G1, 244007),
    (244073, "pchn_g1b_point_notice_four", "通知四要素：时间、地点、人物、事情", 4, SUBJECT, G1, 244007),
    (244074, "pchn_g1b_point_monkey", "《小猴子下山》：掰玉米、摘桃子、抱西瓜、追兔子", 5, SUBJECT, G1, 244007),
    (244075, "pchn_g1b_point_monkey_verbs", "动词搭配：掰玉米、摘桃子、抱西瓜、追兔子", 6, SUBJECT, G1, 244007),
    (244076, "pchn_g1b_point_text5_words", "课文（五）生字：具、次、丢、哪、新、每、平、钟", 7, SUBJECT, G1, 244007),
    (244077, "pchn_g1b_point_text5_duoyin", "多音字：背（bēi／bèi）、种（zhǒng／zhòng）", 8, SUBJECT, G1, 244007),
    (244078, "pchn_g1b_point_text5_moral", "道理归纳：做事有始有终、专心专一、珍惜时间", 9, SUBJECT, G1, 244007),

    # 课文（六）
    (244079, "pchn_g1b_point_cotton_doctor", "《棉花姑娘》：燕子、啄木鸟、青蛙、七星瓢虫各捉什么害虫", 1, SUBJECT, G1, 244008),
    (244080, "pchn_g1b_point_gudong", "《咕咚》：听到“咕咚”盲目逃跑，遇事要弄清真相", 2, SUBJECT, G1, 244008),
    (244081, "pchn_g1b_point_gecko_tail", "《小壁虎借尾巴》：小鱼、老牛、燕子尾巴的作用", 3, SUBJECT, G1, 244008),
    (244082, "pchn_g1b_point_gecko_regen", "壁虎断尾再生：尾巴不是借来的，而是自己长出来的", 4, SUBJECT, G1, 244008),
    (244083, "pchn_g1b_point_text6_words", "课文（六）生字：病、医、别、干、奇、星、吓、怕", 5, SUBJECT, G1, 244008),
    (244084, "pchn_g1b_point_text6_duoyin", "多音字：干（gān／gàn）、转（zhuǎn／zhuàn）", 6, SUBJECT, G1, 244008),
    (244085, "pchn_g1b_point_tail_function", "动物尾巴功能：小鱼拨水、老牛赶蝇子、燕子掌握方向", 7, SUBJECT, G1, 244008),
    (244086, "pchn_g1b_point_text6_read", "问号与感叹号朗读：读出请求、害怕与惊喜的语气", 8, SUBJECT, G1, 244008),
    (244087, "pchn_g1b_point_text6_picture", "看图写话：按“谁—向谁借—结果”的顺序写清经过", 9, SUBJECT, G1, 244008),
)

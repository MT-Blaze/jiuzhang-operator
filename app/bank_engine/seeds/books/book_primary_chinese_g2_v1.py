"""统编版小学语文二年级上册：七个课文单元、一个识字单元与语文园地的知识点树。"""

from __future__ import annotations

SUBJECT = 1
G2 = 2
BOOK_ID = 1403

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版小学语文二年级上册",
    "pchn_g2a",
    3,
    "人民教育出版社",
    SUBJECT,
    G2,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 八个单元
    (140301, "第一单元 识字", "pchn_g2a_u01", 1, BOOK_ID, None),
    (140302, "第二单元 课文（一）", "pchn_g2a_u02", 2, BOOK_ID, None),
    (140303, "第三单元 课文（二）", "pchn_g2a_u03", 3, BOOK_ID, None),
    (140304, "第四单元 课文（三）", "pchn_g2a_u04", 4, BOOK_ID, None),
    (140305, "第五单元 课文（四）", "pchn_g2a_u05", 5, BOOK_ID, None),
    (140306, "第六单元 课文（五）", "pchn_g2a_u06", 6, BOOK_ID, None),
    (140307, "第七单元 课文（六）", "pchn_g2a_u07", 7, BOOK_ID, None),
    (140308, "第八单元 课文（七）", "pchn_g2a_u08", 8, BOOK_ID, None),

    # 第一单元 识字
    (140311, "识字1 场景歌", "pchn_g2a_l01", 1, BOOK_ID, 140301),
    (140312, "识字2 树之歌", "pchn_g2a_l02", 2, BOOK_ID, 140301),
    (140313, "识字3 拍手歌", "pchn_g2a_l03", 3, BOOK_ID, 140301),
    (140314, "识字4 田家四季歌", "pchn_g2a_l04", 4, BOOK_ID, 140301),
    (140315, "语文园地一", "pchn_g2a_l05", 5, BOOK_ID, 140301),

    # 第二单元 课文（一）
    (140321, "课文1 小蝌蚪找妈妈", "pchn_g2a_l06", 1, BOOK_ID, 140302),
    (140322, "课文2 我是什么", "pchn_g2a_l07", 2, BOOK_ID, 140302),
    (140323, "课文3 植物妈妈有办法", "pchn_g2a_l08", 3, BOOK_ID, 140302),
    (140324, "语文园地二", "pchn_g2a_l09", 4, BOOK_ID, 140302),

    # 第三单元 课文（二）
    (140331, "课文4 曹冲称象", "pchn_g2a_l10", 1, BOOK_ID, 140303),
    (140332, "课文5 玲玲的画", "pchn_g2a_l11", 2, BOOK_ID, 140303),
    (140333, "课文6 一封信", "pchn_g2a_l12", 3, BOOK_ID, 140303),
    (140334, "课文7 妈妈睡了", "pchn_g2a_l13", 4, BOOK_ID, 140303),
    (140335, "语文园地三", "pchn_g2a_l14", 5, BOOK_ID, 140303),

    # 第四单元 课文（三）
    (140341, "课文8 古诗二首（登鹳雀楼／望庐山瀑布）", "pchn_g2a_l15", 1, BOOK_ID, 140304),
    (140342, "课文9 黄山奇石", "pchn_g2a_l16", 2, BOOK_ID, 140304),
    (140343, "课文10 日月潭", "pchn_g2a_l17", 3, BOOK_ID, 140304),
    (140344, "课文11 葡萄沟", "pchn_g2a_l18", 4, BOOK_ID, 140304),
    (140345, "语文园地四", "pchn_g2a_l19", 5, BOOK_ID, 140304),

    # 第五单元 课文（四）
    (140351, "课文12 坐井观天", "pchn_g2a_l20", 1, BOOK_ID, 140305),
    (140352, "课文13 寒号鸟", "pchn_g2a_l21", 2, BOOK_ID, 140305),
    (140353, "课文14 我要的是葫芦", "pchn_g2a_l22", 3, BOOK_ID, 140305),
    (140354, "语文园地五", "pchn_g2a_l23", 4, BOOK_ID, 140305),

    # 第六单元 课文（五）
    (140361, "课文15 大禹治水", "pchn_g2a_l24", 1, BOOK_ID, 140306),
    (140362, "课文16 朱德的扁担", "pchn_g2a_l25", 2, BOOK_ID, 140306),
    (140363, "课文17 难忘的泼水节", "pchn_g2a_l26", 3, BOOK_ID, 140306),
    (140364, "语文园地六", "pchn_g2a_l27", 4, BOOK_ID, 140306),

    # 第七单元 课文（六）
    (140371, "课文18 古诗二首（夜宿山寺／敕勒歌）", "pchn_g2a_l28", 1, BOOK_ID, 140307),
    (140372, "课文19 雾在哪里", "pchn_g2a_l29", 2, BOOK_ID, 140307),
    (140373, "课文20 雪孩子", "pchn_g2a_l30", 3, BOOK_ID, 140307),
    (140374, "语文园地七", "pchn_g2a_l31", 4, BOOK_ID, 140307),

    # 第八单元 课文（七）
    (140381, "课文21 狐假虎威", "pchn_g2a_l32", 1, BOOK_ID, 140308),
    (140382, "课文22 狐狸分奶酪", "pchn_g2a_l33", 2, BOOK_ID, 140308),
    (140383, "课文23 纸船和风筝", "pchn_g2a_l34", 3, BOOK_ID, 140308),
    (140384, "课文24 风娃娃", "pchn_g2a_l35", 4, BOOK_ID, 140308),
    (140385, "语文园地八", "pchn_g2a_l36", 5, BOOK_ID, 140308),
)

# id / code / name / sort_order / subject_id / parent_id
# 245001-245008 为册域层，245011-245099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (245001, "pchn_g2a_domain_literacy", "小学二上·识字 量词树木与农事儿歌", 1, SUBJECT, None),
    (245002, "pchn_g2a_domain_text1", "小学二上·课文（一）动物变化与自然常识", 2, SUBJECT, None),
    (245003, "pchn_g2a_domain_text2", "小学二上·课文（二）智慧、亲情与生活", 3, SUBJECT, None),
    (245004, "pchn_g2a_domain_text3", "小学二上·课文（三）古诗与祖国山河", 4, SUBJECT, None),
    (245005, "pchn_g2a_domain_text4", "小学二上·课文（四）寓言故事与道理", 5, SUBJECT, None),
    (245006, "pchn_g2a_domain_text5", "小学二上·课文（五）奉献与革命传统", 6, SUBJECT, None),
    (245007, "pchn_g2a_domain_text6", "小学二上·课文（六）古诗与想象童话", 7, SUBJECT, None),
    (245008, "pchn_g2a_domain_text7", "小学二上·课文（七）狐狸故事与友情", 8, SUBJECT, None),

    # 第一单元 识字
    (245011, "pchn_g2a_point_scene_measure1", "《场景歌》数量词：一只海鸥、一片沙滩、一艘军舰、一条帆船", 1, SUBJECT, 245001),
    (245012, "pchn_g2a_point_scene_measure2", "《场景歌》数量词：一方鱼塘、一块稻田、一行垂柳、一座花园", 2, SUBJECT, 245001),
    (245013, "pchn_g2a_point_scene_measure3", "《场景歌》量词辨析：条、匹、只、座、面、群的搭配对象", 3, SUBJECT, 245001),
    (245014, "pchn_g2a_point_tree_feature", "《树之歌》树木特点：杨树高、榕树壮、梧桐树叶像手掌", 4, SUBJECT, 245001),
    (245015, "pchn_g2a_point_tree_names", "《树之歌》树木名称：松柏、枫树、木棉、桦树、银杏、水杉、桂花", 5, SUBJECT, 245001),
    (245016, "pchn_g2a_point_tree_similar", "《树之歌》形近字：杨—场、桐—铜、枫—风、柏—伯", 6, SUBJECT, 245001),
    (245017, "pchn_g2a_point_clap_animals", "《拍手歌》动物名称：孔雀、锦鸡、雄鹰、雁群、老虎、黄鹂、百灵、熊猫", 7, SUBJECT, 245001),
    (245018, "pchn_g2a_point_clap_protect", "《拍手歌》主题：人和动物是朋友，保护动物是大事", 8, SUBJECT, 245001),
    (245019, "pchn_g2a_point_farm_seasons", "《田家四季歌》四季农事：春采桑养蚕、夏插秧、秋收稻、冬积肥", 9, SUBJECT, 245001),
    (245020, "pchn_g2a_point_farm_words", "《田家四季歌》农事词语：播种、插秧、耕田、采桑、养蚕、割麦", 10, SUBJECT, 245001),
    (245021, "pchn_g2a_point_literacy_duoyin", "多音字：场（chǎng／cháng）、了（le／liǎo）、柏（bǎi／bó）", 11, SUBJECT, 245001),
    (245022, "pchn_g2a_point_bushou_lookup", "部首查字法：定部首、数部首笔画、再数剩余笔画查字", 12, SUBJECT, 245001),

    # 第二单元 课文（一）
    (245023, "pchn_g2a_point_tadpole_growth", "《小蝌蚪找妈妈》生长顺序：长后腿、长前腿、尾巴变短、尾巴不见", 1, SUBJECT, 245002),
    (245024, "pchn_g2a_point_tadpole_clues", "《小蝌蚪找妈妈》找妈妈线索：四条腿宽嘴巴、大眼睛绿衣裳", 2, SUBJECT, 245002),
    (245025, "pchn_g2a_point_tadpole_verbs", "《小蝌蚪找妈妈》动词辨析：迎上去、追上去、游过去", 3, SUBJECT, 245002),
    (245026, "pchn_g2a_point_water_change", "《我是什么》水的形态变化：汽、云、雨、雹子、雪", 4, SUBJECT, 245002),
    (245027, "pchn_g2a_point_water_use", "《我是什么》水的利弊：灌溉田地、发动机器与淹没庄稼、冲毁房屋", 5, SUBJECT, 245002),
    (245028, "pchn_g2a_point_seed_spread", "《植物妈妈有办法》传播方式：蒲公英靠风、苍耳靠动物、豌豆靠太阳", 6, SUBJECT, 245002),
    (245029, "pchn_g2a_point_seed_rhyme", "《植物妈妈有办法》句式仿写：“……的孩子，……就得告别妈妈，四海为家”", 7, SUBJECT, 245002),
    (245030, "pchn_g2a_point_text1_words", "课文（一）生字：塘、脑、袋、灰、捕、迎、阿、姨、宽、龟、顶、披、鼓", 8, SUBJECT, 245002),
    (245031, "pchn_g2a_point_text1_duoyin", "多音字：没（méi／mò）、得（dé／de／děi）、为（wéi／wèi）", 9, SUBJECT, 245002),
    (245032, "pchn_g2a_point_text1_collocation", "词语搭配：雪白的衣裳、碧绿的衣裳、黑灰色的身子、大大的脑袋", 10, SUBJECT, 245002),
    (245033, "pchn_g2a_point_text1_personify", "拟人自述：以“我是什么”的口吻介绍水，读出自豪与调皮", 11, SUBJECT, 245002),

    # 第三单元 课文（二）
    (245034, "pchn_g2a_point_elephant_steps", "《曹冲称象》称象步骤：赶象上船画线、赶象上岸装石头、称石头算重量", 1, SUBJECT, 245003),
    (245035, "pchn_g2a_point_elephant_quality", "《曹冲称象》人物品质：曹冲善于观察、爱动脑筋、敢于表达", 2, SUBJECT, 245003),
    (245036, "pchn_g2a_point_lingling_moral", "《玲玲的画》道理：坏事往往能变成好事，遇事肯动脑筋", 3, SUBJECT, 245003),
    (245037, "pchn_g2a_point_lingling_mood", "《玲玲的画》心情变化词语：得意、伤心、满意", 4, SUBJECT, 245003),
    (245038, "pchn_g2a_point_letter_compare", "《一封信》两封信对比：第一封抱怨爸爸不在，第二封报喜不添愁", 5, SUBJECT, 245003),
    (245039, "pchn_g2a_point_letter_character", "《一封信》露西的人物形象：懂事、体贴妈妈、乐观", 6, SUBJECT, 245003),
    (245040, "pchn_g2a_point_mother_sleep", "《妈妈睡了》睡梦中的妈妈：美丽、慈祥、劳累", 7, SUBJECT, 245003),
    (245041, "pchn_g2a_point_mother_detail", "《妈妈睡了》细节描写：观察顺序与“弯弯的眉毛”等叠词", 8, SUBJECT, 245003),
    (245042, "pchn_g2a_point_text2_duoyin", "多音字：称（chēng／chèn）、发（fā／fà）、觉（jué／jiào）", 9, SUBJECT, 245003),
    (245043, "pchn_g2a_point_text2_similar", "形近字：称—秤、候—侯、园—圆、做—作", 10, SUBJECT, 245003),
    (245044, "pchn_g2a_point_text2_measure", "量词搭配：一杆秤、一头大象、一堵墙、一封信", 11, SUBJECT, 245003),

    # 第四单元 课文（三）
    (245045, "pchn_g2a_point_guanque_poem", "《登鹳雀楼》：白日依山尽，黄河入海流；欲穷千里目，更上一层楼", 1, SUBJECT, 245004),
    (245046, "pchn_g2a_point_guanque_moral", "《登鹳雀楼》哲理：站得高才能看得远，要不断进取", 2, SUBJECT, 245004),
    (245047, "pchn_g2a_point_lushan_poem", "《望庐山瀑布》：日照香炉生紫烟，遥看瀑布挂前川；飞流直下三千尺，疑是银河落九天", 3, SUBJECT, 245004),
    (245048, "pchn_g2a_point_lushan_rhetoric", "《望庐山瀑布》修辞：夸张“三千尺”与比喻“疑是银河”", 4, SUBJECT, 245004),
    (245049, "pchn_g2a_point_poem_recite", "古诗背诵与作者：王之涣《登鹳雀楼》、李白《望庐山瀑布》及朗读节奏", 5, SUBJECT, 245004),
    (245050, "pchn_g2a_point_huangshan_rocks", "《黄山奇石》奇石名称：仙桃石、猴子观海、仙人指路、金鸡叫天都", 6, SUBJECT, 245004),
    (245051, "pchn_g2a_point_huangshan_imagine", "《黄山奇石》想象仿写：“好像”“每当……就……”句式", 7, SUBJECT, 245004),
    (245052, "pchn_g2a_point_sunmoon_name", "《日月潭》位置与得名：台湾中部，北半湖如太阳、南半湖如月亮", 8, SUBJECT, 245004),
    (245053, "pchn_g2a_point_sunmoon_scene", "《日月潭》景色：清晨薄雾、中午清晰、雨中朦胧", 9, SUBJECT, 245004),
    (245054, "pchn_g2a_point_grape_raisin", "《葡萄沟》葡萄干制作：阴房四面留孔、利用流动的热空气", 10, SUBJECT, 245004),
    (245055, "pchn_g2a_point_grape_people", "《葡萄沟》维吾尔族老乡热情好客与“葡萄沟真是个好地方”", 11, SUBJECT, 245004),
    (245056, "pchn_g2a_point_text3_duoyin", "多音字：都（dōu／dū）、好（hǎo／hào）、干（gān／gàn）", 12, SUBJECT, 245004),
    (245057, "pchn_g2a_point_text3_collocation", "词语搭配：陡峭的山峰、翻滚的云海、茂密的枝叶、鲜红的葡萄", 13, SUBJECT, 245004),

    # 第五单元 课文（四）
    (245058, "pchn_g2a_point_well_frog_talk", "《坐井观天》三次对话：青蛙与小鸟争论天有多大", 1, SUBJECT, 245005),
    (245059, "pchn_g2a_point_well_moral", "《坐井观天》寓意：看问题要全面，不能像青蛙那样目光短浅", 2, SUBJECT, 245005),
    (245060, "pchn_g2a_point_bird_advice", "《寒号鸟》两次劝告与结局：不听劝告，最后冻死在崖缝里", 3, SUBJECT, 245005),
    (245061, "pchn_g2a_point_bird_moral", "《寒号鸟》寓意：不能懒惰拖延，要及早做准备", 4, SUBJECT, 245005),
    (245062, "pchn_g2a_point_gourd_link", "《我要的是葫芦》事物联系：叶子被虫咬，葫芦也长不好", 5, SUBJECT, 245005),
    (245063, "pchn_g2a_point_gourd_moral", "《我要的是葫芦》寓意：不能只看结果，要重视事物之间的联系", 6, SUBJECT, 245005),
    (245064, "pchn_g2a_point_text4_duoyin", "多音字：哪（nǎ／na）、种（zhǒng／zhòng）、还（hái／huán）", 7, SUBJECT, 245005),
    (245065, "pchn_g2a_point_text4_similar", "形近字：渴—喝、抬—治、邻—领、葫—胡", 8, SUBJECT, 245005),
    (245066, "pchn_g2a_point_text4_rhetoric", "反问句与感叹句：“叶子上的虫还用治？”读出不相信的语气", 9, SUBJECT, 245005),

    # 第六单元 课文（五）
    (245067, "pchn_g2a_point_yu_flood", "《大禹治水》治水方法：改堵为疏，开凿河道引水入海", 1, SUBJECT, 245006),
    (245068, "pchn_g2a_point_yu_home", "《大禹治水》三过家门而不入，大公无私、为民造福", 2, SUBJECT, 245006),
    (245069, "pchn_g2a_point_zhu_pole", "《朱德的扁担》挑粮故事与扁担上“朱德的扁担”五个字", 3, SUBJECT, 245006),
    (245070, "pchn_g2a_point_zhu_quality", "《朱德的扁担》人物品质：以身作则、与战士同甘共苦", 4, SUBJECT, 245006),
    (245071, "pchn_g2a_point_water_splash", "《难忘的泼水节》周总理与傣族人民共度泼水节", 5, SUBJECT, 245006),
    (245072, "pchn_g2a_point_splash_scene", "《难忘的泼水节》场面描写与“一手……一手……”句式", 6, SUBJECT, 245006),
    (245073, "pchn_g2a_point_text5_duoyin", "多音字：难（nán／nàn）、担（dān／dàn）、发（fā／fà）", 7, SUBJECT, 245006),
    (245074, "pchn_g2a_point_text5_collocation", "词语搭配：火红的凤凰花、敬爱的周总理、鲜红的地毯", 8, SUBJECT, 245006),

    # 第七单元 课文（六）
    (245075, "pchn_g2a_point_temple_poem", "《夜宿山寺》：危楼高百尺，手可摘星辰；不敢高声语，恐惊天上人", 1, SUBJECT, 245007),
    (245076, "pchn_g2a_point_temple_exaggerate", "《夜宿山寺》夸张手法：“百尺”“摘星辰”写楼之高", 2, SUBJECT, 245007),
    (245077, "pchn_g2a_point_chile_poem", "《敕勒歌》：敕勒川，阴山下；天似穹庐，笼盖四野；天苍苍，野茫茫，风吹草低见牛羊", 3, SUBJECT, 245007),
    (245078, "pchn_g2a_point_chile_scene", "《敕勒歌》草原画面想象与“见”读 xiàn 的含义", 4, SUBJECT, 245007),
    (245079, "pchn_g2a_point_fog_hide", "《雾在哪里》雾藏起大海、天空、太阳、海岸与城市", 5, SUBJECT, 245007),
    (245080, "pchn_g2a_point_fog_personify", "《雾在哪里》拟人写法：把雾当作淘气的孩子", 6, SUBJECT, 245007),
    (245081, "pchn_g2a_point_snowboy_save", "《雪孩子》雪孩子冲进火海救小白兔，化成水汽变成白云", 7, SUBJECT, 245007),
    (245082, "pchn_g2a_point_text6_duoyin", "多音字：似（sì／shì）、宿（sù／xiǔ）、笼（lóng／lǒng）", 8, SUBJECT, 245007),

    # 第八单元 课文（七）
    (245083, "pchn_g2a_point_fox_tiger_meaning", "《狐假虎威》成语意思：借别人的威势吓唬人", 1, SUBJECT, 245008),
    (245084, "pchn_g2a_point_fox_tiger_words", "《狐假虎威》词语：神气活现、摇头摆尾、半信半疑、东张西望", 2, SUBJECT, 245008),
    (245085, "pchn_g2a_point_cheese_trick", "《狐狸分奶酪》狐狸借“分得公平”之名把奶酪吃光", 3, SUBJECT, 245008),
    (245086, "pchn_g2a_point_cheese_moral", "《狐狸分奶酪》寓意：同伴之间要谦让，不要被坏人挑拨", 4, SUBJECT, 245008),
    (245087, "pchn_g2a_point_kite_friend", "《纸船和风筝》松鼠与小熊吵架后用纸船和风筝和好", 5, SUBJECT, 245008),
    (245088, "pchn_g2a_point_kite_mood", "《纸船和风筝》心情变化：快乐、难过、激动与友谊的珍贵", 6, SUBJECT, 245008),
    (245089, "pchn_g2a_point_wind_good_bad", "《风娃娃》风娃娃做好事与帮倒忙：吹动风车、吹跑风筝", 7, SUBJECT, 245008),
    (245090, "pchn_g2a_point_wind_moral", "《风娃娃》道理：做好事要看是否真的对别人有用", 8, SUBJECT, 245008),
    (245091, "pchn_g2a_point_text7_duoyin", "多音字：转（zhuǎn／zhuàn）、假（jiǎ／jià）、骨（gǔ／gū）", 9, SUBJECT, 245008),
    (245092, "pchn_g2a_point_picture_write", "语文园地八看图写话：按“时间—地点—谁—做什么”写清图意", 10, SUBJECT, 245008),
)

"""统编版小学语文二年级下册：七个课文单元、一个识字单元与语文园地的知识点树。"""

from __future__ import annotations

SUBJECT = 1
G2 = 2
BOOK_ID = 1404

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版小学语文二年级下册",
    "pchn_g2b",
    4,
    "人民教育出版社",
    SUBJECT,
    G2,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 八个单元
    (140401, "第一单元 课文（一）", "pchn_g2b_u01", 1, BOOK_ID, None),
    (140402, "第二单元 课文（二）", "pchn_g2b_u02", 2, BOOK_ID, None),
    (140403, "第三单元 识字", "pchn_g2b_u03", 3, BOOK_ID, None),
    (140404, "第四单元 课文（三）", "pchn_g2b_u04", 4, BOOK_ID, None),
    (140405, "第五单元 课文（四）", "pchn_g2b_u05", 5, BOOK_ID, None),
    (140406, "第六单元 课文（五）", "pchn_g2b_u06", 6, BOOK_ID, None),
    (140407, "第七单元 课文（六）", "pchn_g2b_u07", 7, BOOK_ID, None),
    (140408, "第八单元 课文（七）", "pchn_g2b_u08", 8, BOOK_ID, None),

    # 第一单元 课文（一）
    (140411, "课文1 古诗二首（村居／咏柳）", "pchn_g2b_l01", 1, BOOK_ID, 140401),
    (140412, "课文2 找春天", "pchn_g2b_l02", 2, BOOK_ID, 140401),
    (140413, "课文3 开满鲜花的小路", "pchn_g2b_l03", 3, BOOK_ID, 140401),
    (140414, "课文4 邓小平爷爷植树", "pchn_g2b_l04", 4, BOOK_ID, 140401),
    (140415, "语文园地一", "pchn_g2b_l05", 5, BOOK_ID, 140401),

    # 第二单元 课文（二）
    (140421, "课文5 雷锋叔叔，你在哪里", "pchn_g2b_l06", 1, BOOK_ID, 140402),
    (140422, "课文6 千人糕", "pchn_g2b_l07", 2, BOOK_ID, 140402),
    (140423, "课文7 一匹出色的马", "pchn_g2b_l08", 3, BOOK_ID, 140402),
    (140424, "语文园地二", "pchn_g2b_l09", 4, BOOK_ID, 140402),

    # 第三单元 识字
    (140431, "识字1 神州谣", "pchn_g2b_l10", 1, BOOK_ID, 140403),
    (140432, "识字2 传统节日", "pchn_g2b_l11", 2, BOOK_ID, 140403),
    (140433, "识字3 “贝”的故事", "pchn_g2b_l12", 3, BOOK_ID, 140403),
    (140434, "识字4 中国美食", "pchn_g2b_l13", 4, BOOK_ID, 140403),
    (140435, "语文园地三", "pchn_g2b_l14", 5, BOOK_ID, 140403),

    # 第四单元 课文（三）
    (140441, "课文8 彩色的梦", "pchn_g2b_l15", 1, BOOK_ID, 140404),
    (140442, "课文9 枫树上的喜鹊", "pchn_g2b_l16", 2, BOOK_ID, 140404),
    (140443, "课文10 沙滩上的童话", "pchn_g2b_l17", 3, BOOK_ID, 140404),
    (140444, "课文11 我是一只小虫子", "pchn_g2b_l18", 4, BOOK_ID, 140404),
    (140445, "语文园地四", "pchn_g2b_l19", 5, BOOK_ID, 140404),

    # 第五单元 课文（四）
    (140451, "课文12 寓言二则（亡羊补牢／揠苗助长）", "pchn_g2b_l20", 1, BOOK_ID, 140405),
    (140452, "课文13 画杨桃", "pchn_g2b_l21", 2, BOOK_ID, 140405),
    (140453, "课文14 小马过河", "pchn_g2b_l22", 3, BOOK_ID, 140405),
    (140454, "语文园地五", "pchn_g2b_l23", 4, BOOK_ID, 140405),

    # 第六单元 课文（五）
    (140461, "课文15 古诗二首（晓出净慈寺送林子方／绝句）", "pchn_g2b_l24", 1, BOOK_ID, 140406),
    (140462, "课文16 雷雨", "pchn_g2b_l25", 2, BOOK_ID, 140406),
    (140463, "课文17 要是你在野外迷了路", "pchn_g2b_l26", 3, BOOK_ID, 140406),
    (140464, "课文18 太空生活趣事多", "pchn_g2b_l27", 4, BOOK_ID, 140406),
    (140465, "语文园地六", "pchn_g2b_l28", 5, BOOK_ID, 140406),

    # 第七单元 课文（六）
    (140471, "课文19 大象的耳朵", "pchn_g2b_l29", 1, BOOK_ID, 140407),
    (140472, "课文20 蜘蛛开店", "pchn_g2b_l30", 2, BOOK_ID, 140407),
    (140473, "课文21 青蛙卖泥塘", "pchn_g2b_l31", 3, BOOK_ID, 140407),
    (140474, "课文22 小毛虫", "pchn_g2b_l32", 4, BOOK_ID, 140407),
    (140475, "语文园地七", "pchn_g2b_l33", 5, BOOK_ID, 140407),

    # 第八单元 课文（七）
    (140481, "课文23 祖先的摇篮", "pchn_g2b_l34", 1, BOOK_ID, 140408),
    (140482, "课文24 当世界年纪还小的时候", "pchn_g2b_l35", 2, BOOK_ID, 140408),
    (140483, "课文25 羿射九日", "pchn_g2b_l36", 3, BOOK_ID, 140408),
    (140484, "语文园地八", "pchn_g2b_l37", 4, BOOK_ID, 140408),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 246001-246008 为册域层，246011-246099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (246001, "pchn_g2b_domain_text1", "小学二下·第一单元 春天与古诗（课文一）", 1, SUBJECT, G2, None),
    (246002, "pchn_g2b_domain_text2", "小学二下·第二单元 关爱与亲情（课文二）", 2, SUBJECT, G2, None),
    (246003, "pchn_g2b_domain_literacy", "小学二下·第三单元 识字 祖国与传统", 3, SUBJECT, G2, None),
    (246004, "pchn_g2b_domain_text3", "小学二下·第四单元 想象与童话（课文三）", 4, SUBJECT, G2, None),
    (246005, "pchn_g2b_domain_text4", "小学二下·第五单元 寓言与道理（课文四）", 5, SUBJECT, G2, None),
    (246006, "pchn_g2b_domain_text5", "小学二下·第六单元 自然与科学（课文五）", 6, SUBJECT, G2, None),
    (246007, "pchn_g2b_domain_text6", "小学二下·第七单元 改变与成长（课文六）", 7, SUBJECT, G2, None),
    (246008, "pchn_g2b_domain_text7", "小学二下·第八单元 神话与想象（课文七）", 8, SUBJECT, G2, None),

    # 第一单元 课文（一）
    (246011, "pchn_g2b_point_cunju", "《村居》背诵：草长莺飞二月天，拂堤杨柳醉春烟；儿童散学归来早，忙趁东风放纸鸢", 1, SUBJECT, G2, 246001),
    (246012, "pchn_g2b_point_yongliu_poem", "《咏柳》背诵：碧玉妆成一树高，万条垂下绿丝绦；不知细叶谁裁出，二月春风似剪刀", 2, SUBJECT, G2, 246001),
    (246013, "pchn_g2b_point_yongliu_metaphor", "《咏柳》比喻：柳条如绿丝绦，春风似剪刀，写出柳树的柔美", 3, SUBJECT, G2, 246001),
    (246014, "pchn_g2b_point_text1_duoyin", "多音字：长（cháng／zhǎng）、散（sàn／sǎn）、似（sì／shì）", 4, SUBJECT, G2, 246001),
    (246015, "pchn_g2b_point_spring_find", "《找春天》春景：小草探出头、野花早开、树木吐嫩芽、小溪丁丁冬冬", 5, SUBJECT, G2, 246001),
    (246016, "pchn_g2b_point_spring_personify", "《找春天》比喻拟人：春天像害羞的小姑娘，遮遮掩掩、躲躲藏藏", 6, SUBJECT, G2, 246001),
    (246017, "pchn_g2b_point_flower_path", "《开满鲜花的小路》情节：长颈鹿大叔寄来花籽，春天小路开满鲜花", 7, SUBJECT, G2, 246001),
    (246018, "pchn_g2b_point_flower_gift", "《开满鲜花的小路》“美好的礼物”：花籽带来鲜花，也带来快乐与分享", 8, SUBJECT, G2, 246001),
    (246019, "pchn_g2b_point_deng_plant", "《邓小平爷爷植树》：天坛公园、83岁高龄，精心挑选并扶正树苗", 9, SUBJECT, G2, 246001),
    (246020, "pchn_g2b_point_text1_measure", "量词与搭配：一棵树苗、一条小路、一片花海、一处风景", 10, SUBJECT, G2, 246001),

    # 第二单元 课文（二）
    (246021, "pchn_g2b_point_leifeng_form", "《雷锋叔叔，你在哪里》形式：一问一答的儿童诗，沿小溪、小路寻找足迹", 1, SUBJECT, G2, 246002),
    (246022, "pchn_g2b_point_leifeng_spirit", "雷锋精神：乐于助人、无私奉献，平凡小事中见伟大", 2, SUBJECT, G2, 246002),
    (246023, "pchn_g2b_point_cake_make", "《千人糕》制作：大米磨粉加糖蒸成米糕，凝聚许多人的劳动", 3, SUBJECT, G2, 246002),
    (246024, "pchn_g2b_point_cake_moral", "《千人糕》道理：珍惜劳动成果，尊重普通劳动者", 4, SUBJECT, G2, 246002),
    (246025, "pchn_g2b_point_horse_plot", "《一匹出色的马》情节：爸爸折柳枝当马，妹妹自己“骑”着回家", 5, SUBJECT, G2, 246002),
    (246026, "pchn_g2b_point_horse_title", "《一匹出色的马》题意：童年的想象与父爱的智慧", 6, SUBJECT, G2, 246002),
    (246027, "pchn_g2b_point_text2_duoyin", "多音字：的（de／dí／dì）、奔（bēn／bèn）、舍（shě／shè）", 7, SUBJECT, G2, 246002),
    (246028, "pchn_g2b_point_text2_collocation", "词语搭配：蒙蒙的细雨、弯弯的小路、碧绿的田野、温暖的春风", 8, SUBJECT, G2, 246002),

    # 第三单元 识字
    (246031, "pchn_g2b_point_shenzhou_names", "《神州谣》祖国称谓与山川：神州、中华、九州；黄河、长江、长城、珠峰", 1, SUBJECT, G2, 246003),
    (246032, "pchn_g2b_point_shenzhou_unity", "《神州谣》民族团结：各民族情谊浓，齐奋发，共繁荣", 2, SUBJECT, G2, 246003),
    (246033, "pchn_g2b_point_festival_order", "《传统节日》时间顺序：春节、元宵、清明、端午、七夕、中秋、重阳", 3, SUBJECT, G2, 246003),
    (246034, "pchn_g2b_point_festival_custom", "《传统节日》习俗：贴窗花、看花灯、赛龙舟、吃月饼、登高插茱萸", 4, SUBJECT, G2, 246003),
    (246035, "pchn_g2b_point_shell_origin", "《“贝”的故事》：贝壳作钱币，带贝字旁的字多与钱财有关", 5, SUBJECT, G2, 246003),
    (246036, "pchn_g2b_point_food_cook", "《中国美食》烹饪方法：煎、烤、煮、爆、炖、蒸、炸、炒", 6, SUBJECT, G2, 246003),
    (246037, "pchn_g2b_point_food_names", "《中国美食》食物名称：菠菜、蘑菇、蒸饺、小米粥、蛋炒饭、红烧肉", 7, SUBJECT, G2, 246003),
    (246038, "pchn_g2b_point_literacy_similar", "形近字：州—洲、舟—丹、币—巾、贝—见", 8, SUBJECT, G2, 246003),

    # 第四单元 课文（三）
    (246041, "pchn_g2b_point_dream_content", "《彩色的梦》内容：彩色铅笔画出草坪、野花、天空与森林", 1, SUBJECT, G2, 246004),
    (246042, "pchn_g2b_point_dream_imitate", "《彩色的梦》句式仿写：“脚尖滑过的地方，大块的草坪，绿了”", 2, SUBJECT, G2, 246004),
    (246043, "pchn_g2b_point_magpie_favorite", "《枫树上的喜鹊》喜欢的事物：枫树、喜鹊窝、喜鹊阿姨和喜鹊弟弟", 3, SUBJECT, G2, 246004),
    (246044, "pchn_g2b_point_magpie_personify", "《枫树上的喜鹊》拟人：把喜鹊一家当作人，想象它们的对话", 4, SUBJECT, G2, 246004),
    (246045, "pchn_g2b_point_beach_plot", "《沙滩上的童话》情节：孩子们编故事救公主，挖地道、炸城堡", 5, SUBJECT, G2, 246004),
    (246046, "pchn_g2b_point_beach_theme", "《沙滩上的童话》主题：想象与合作带来的快乐", 6, SUBJECT, G2, 246004),
    (246047, "pchn_g2b_point_bug_life", "《我是一只小虫子》内容：小虫子的烦恼与快乐，乐观面对生活", 7, SUBJECT, G2, 246004),
    (246048, "pchn_g2b_point_words_aabb", "AABB 式词语：蹦蹦跳跳、摇摇晃晃、躲躲藏藏、安安静静", 8, SUBJECT, G2, 246004),
    (246049, "pchn_g2b_point_words_abab", "ABAB 式词语：讨论讨论、打扫打扫、商量商量、研究研究", 9, SUBJECT, G2, 246004),

    # 第五单元 课文（四）
    (246051, "pchn_g2b_point_sheep_plot", "《亡羊补牢》情节：两次丢羊，不听劝告后修补羊圈", 1, SUBJECT, G2, 246005),
    (246052, "pchn_g2b_point_sheep_moral", "《亡羊补牢》寓意：出了问题及时补救，还不算晚", 2, SUBJECT, G2, 246005),
    (246053, "pchn_g2b_point_seedling_plot", "《揠苗助长》情节：农夫拔高禾苗，禾苗全部枯死", 3, SUBJECT, G2, 246005),
    (246054, "pchn_g2b_point_seedling_moral", "《揠苗助长》寓意：违反规律、急于求成，反而把事情弄坏", 4, SUBJECT, G2, 246005),
    (246055, "pchn_g2b_point_star_fruit_plot", "《画杨桃》情节：把杨桃画成五角星，老师让同学坐到“我”的位置观察", 5, SUBJECT, G2, 246005),
    (246056, "pchn_g2b_point_star_fruit_moral", "《画杨桃》道理：角度不同看到的不同，要实事求是", 6, SUBJECT, G2, 246005),
    (246057, "pchn_g2b_point_horse_river_plot", "《小马过河》情节：老牛说水浅、松鼠说水深，妈妈让小马自己试", 7, SUBJECT, G2, 246005),
    (246058, "pchn_g2b_point_horse_river_moral", "《小马过河》道理：遇事要动脑筋，亲自实践才能得出结论", 8, SUBJECT, G2, 246005),
    (246059, "pchn_g2b_point_text4_duoyin", "多音字：圈（juàn／quān）、坊（fāng／fáng）、倒（dǎo／dào）", 9, SUBJECT, G2, 246005),
    (246060, "pchn_g2b_point_fable_feature", "寓言文体：用短小故事讲明一个道理，读懂故事与寓意", 10, SUBJECT, G2, 246005),

    # 第六单元 课文（五）
    (246061, "pchn_g2b_point_jingci_poem", "《晓出净慈寺送林子方》：毕竟西湖六月中，风光不与四时同；接天莲叶无穷碧，映日荷花别样红", 1, SUBJECT, G2, 246006),
    (246062, "pchn_g2b_point_jueju_poem", "《绝句》：两个黄鹂鸣翠柳，一行白鹭上青天；窗含西岭千秋雪，门泊东吴万里船", 2, SUBJECT, G2, 246006),
    (246063, "pchn_g2b_point_jueju_color", "古诗色彩与对仗：黄鹂对白鹭、翠柳对青天、西岭对东吴", 3, SUBJECT, G2, 246006),
    (246064, "pchn_g2b_point_thunder_order", "《雷雨》写作顺序：雷雨前、雷雨中、雷雨后", 4, SUBJECT, G2, 246006),
    (246065, "pchn_g2b_point_thunder_scene", "《雷雨》景物变化：乌云压顶、大风、闪电雷声、雨停彩虹", 5, SUBJECT, G2, 246006),
    (246066, "pchn_g2b_point_compass", "《要是你在野外迷了路》天然指南针：太阳、北极星、大树、沟渠积雪", 6, SUBJECT, G2, 246006),
    (246067, "pchn_g2b_point_space_fun", "《太空生活趣事多》太空趣事：绑睡袋睡觉、带吸管喝水、穿带钩鞋走路、密封浴桶洗澡", 7, SUBJECT, G2, 246006),
    (246068, "pchn_g2b_point_text5_duoyin", "多音字：行（xíng／háng）、压（yā／yà）、露（lù／lòu）", 8, SUBJECT, G2, 246006),
    (246069, "pchn_g2b_point_thunder_metaphor", "比喻句：“满天的乌云，黑沉沉地压下来”“闪电像一把把利剑”", 9, SUBJECT, G2, 246006),

    # 第七单元 课文（六）
    (246071, "pchn_g2b_point_elephant_ears", "《大象的耳朵》情节：耳朵耷拉被嘲笑，撑起竹竿难受又放下", 1, SUBJECT, G2, 246007),
    (246072, "pchn_g2b_point_elephant_moral", "《大象的耳朵》道理：人家是人家，我是我，正确对待别人意见", 2, SUBJECT, G2, 246007),
    (246073, "pchn_g2b_point_spider_shop", "《蜘蛛开店》三次开店：卖口罩遇河马、卖围巾遇长颈鹿、卖袜子遇蜈蚣", 3, SUBJECT, G2, 246007),
    (246074, "pchn_g2b_point_spider_moral", "《蜘蛛开店》结局与启示：吓得逃回网上，做事要考虑周全", 4, SUBJECT, G2, 246007),
    (246075, "pchn_g2b_point_frog_pond", "《青蛙卖泥塘》改造过程：种草、引水、栽树、种花、修路、盖房", 5, SUBJECT, G2, 246007),
    (246076, "pchn_g2b_point_frog_moral", "《青蛙卖泥塘》道理：劳动能创造美好环境", 6, SUBJECT, G2, 246007),
    (246077, "pchn_g2b_point_caterpillar_grow", "《小毛虫》成长过程：小毛虫结茧变成蝴蝶", 7, SUBJECT, G2, 246007),
    (246078, "pchn_g2b_point_caterpillar_moral", "《小毛虫》道理：每个人都有该做的事，尽心竭力做好自己", 8, SUBJECT, G2, 246007),

    # 第八单元 课文（七）
    (246081, "pchn_g2b_point_cradle_theme", "《祖先的摇篮》主题：原始森林是祖先的摇篮", 1, SUBJECT, G2, 246008),
    (246082, "pchn_g2b_point_cradle_life", "《祖先的摇篮》想象祖先生活：摘野果、掏鹊蛋、逗松鼠、采野蔷薇", 2, SUBJECT, G2, 246008),
    (246083, "pchn_g2b_point_world_young", "《当世界年纪还小的时候》万物学习：太阳学上山下山、月亮学变化、水学流动", 3, SUBJECT, G2, 246008),
    (246084, "pchn_g2b_point_world_imagine", "《当世界年纪还小的时候》想象写法：赋予万物学习与成长", 4, SUBJECT, G2, 246008),
    (246085, "pchn_g2b_point_houyi_plot", "《羿射九日》神话情节：十个太阳炙烤大地，羿射下九个，留下一个", 5, SUBJECT, G2, 246008),
    (246086, "pchn_g2b_point_houyi_feature", "《羿射九日》神话特点：想象神奇，塑造勇敢为民的英雄形象", 6, SUBJECT, G2, 246008),
    (246087, "pchn_g2b_point_text7_duoyin", "多音字：觉（jué／jiào）、重（zhòng／chóng）、发（fā／fà）", 7, SUBJECT, G2, 246008),
    (246088, "pchn_g2b_point_picture_write", "看图写话：按“时间—地点—谁—做什么—怎么样”有序观察并表达", 8, SUBJECT, G2, 246008),
)

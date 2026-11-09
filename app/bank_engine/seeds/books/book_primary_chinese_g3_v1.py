"""统编版小学语文三年级上册：八个单元的课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G3 = 3
BOOK_ID = 1405

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版小学语文三年级上册",
    "pchn_g3a",
    5,
    "人民教育出版社",
    SUBJECT,
    G3,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 八个单元
    (140501, "第一单元 校园生活", "pchn_g3a_u01", 1, BOOK_ID, None),
    (140502, "第二单元 金秋时节", "pchn_g3a_u02", 2, BOOK_ID, None),
    (140503, "第三单元 童话世界", "pchn_g3a_u03", 3, BOOK_ID, None),
    (140504, "第四单元 预测与续写", "pchn_g3a_u04", 4, BOOK_ID, None),
    (140505, "第五单元 留心观察", "pchn_g3a_u05", 5, BOOK_ID, None),
    (140506, "第六单元 祖国山河", "pchn_g3a_u06", 6, BOOK_ID, None),
    (140507, "第七单元 自然之声", "pchn_g3a_u07", 7, BOOK_ID, None),
    (140508, "第八单元 美好品质", "pchn_g3a_u08", 8, BOOK_ID, None),

    # 第一单元 校园生活
    (140511, "课文1 大青树下的小学", "pchn_g3a_l01", 1, BOOK_ID, 140501),
    (140512, "课文2 花的学校", "pchn_g3a_l02", 2, BOOK_ID, 140501),
    (140513, "课文3 不懂就要问", "pchn_g3a_l03", 3, BOOK_ID, 140501),
    (140514, "语文园地一", "pchn_g3a_l04", 4, BOOK_ID, 140501),

    # 第二单元 金秋时节
    (140521, "课文4 古诗三首（山行／赠刘景文／夜书所见）", "pchn_g3a_l05", 1, BOOK_ID, 140502),
    (140522, "课文5 铺满金色巴掌的水泥道", "pchn_g3a_l06", 2, BOOK_ID, 140502),
    (140523, "课文6 秋天的雨", "pchn_g3a_l07", 3, BOOK_ID, 140502),
    (140524, "课文7 听听，秋的声音", "pchn_g3a_l08", 4, BOOK_ID, 140502),
    (140525, "语文园地二", "pchn_g3a_l09", 5, BOOK_ID, 140502),

    # 第三单元 童话世界
    (140531, "课文8 卖火柴的小女孩", "pchn_g3a_l10", 1, BOOK_ID, 140503),
    (140532, "课文9 那一定会很好", "pchn_g3a_l11", 2, BOOK_ID, 140503),
    (140533, "课文10 在牛肚子里旅行", "pchn_g3a_l12", 3, BOOK_ID, 140503),
    (140534, "课文11 一块奶酪", "pchn_g3a_l13", 4, BOOK_ID, 140503),
    (140535, "语文园地三", "pchn_g3a_l14", 5, BOOK_ID, 140503),

    # 第四单元 预测与续写
    (140541, "课文12 总也倒不了的老屋", "pchn_g3a_l15", 1, BOOK_ID, 140504),
    (140542, "课文13 胡萝卜先生的长胡子", "pchn_g3a_l16", 2, BOOK_ID, 140504),
    (140543, "课文14 小狗学叫", "pchn_g3a_l17", 3, BOOK_ID, 140504),
    (140544, "语文园地四", "pchn_g3a_l18", 4, BOOK_ID, 140504),

    # 第五单元 留心观察
    (140551, "课文15 搭船的鸟", "pchn_g3a_l19", 1, BOOK_ID, 140505),
    (140552, "课文16 金色的草地", "pchn_g3a_l20", 2, BOOK_ID, 140505),
    (140553, "交流平台·初试身手与习作例文", "pchn_g3a_l21", 3, BOOK_ID, 140505),

    # 第六单元 祖国山河
    (140561, "课文17 古诗三首（望天门山／饮湖上初晴后雨／望洞庭）", "pchn_g3a_l22", 1, BOOK_ID, 140506),
    (140562, "课文18 富饶的西沙群岛", "pchn_g3a_l23", 2, BOOK_ID, 140506),
    (140563, "课文19 海滨小城", "pchn_g3a_l24", 3, BOOK_ID, 140506),
    (140564, "课文20 美丽的小兴安岭", "pchn_g3a_l25", 4, BOOK_ID, 140506),
    (140565, "语文园地六", "pchn_g3a_l26", 5, BOOK_ID, 140506),

    # 第七单元 自然之声
    (140571, "课文21 大自然的声音", "pchn_g3a_l27", 1, BOOK_ID, 140507),
    (140572, "课文22 读不完的大书", "pchn_g3a_l28", 2, BOOK_ID, 140507),
    (140573, "课文23 父亲、树林和鸟", "pchn_g3a_l29", 3, BOOK_ID, 140507),
    (140574, "语文园地七", "pchn_g3a_l30", 4, BOOK_ID, 140507),

    # 第八单元 美好品质
    (140581, "课文24 司马光", "pchn_g3a_l31", 1, BOOK_ID, 140508),
    (140582, "课文25 灰雀", "pchn_g3a_l32", 2, BOOK_ID, 140508),
    (140583, "课文26 手术台就是阵地", "pchn_g3a_l33", 3, BOOK_ID, 140508),
    (140584, "语文园地八", "pchn_g3a_l34", 4, BOOK_ID, 140508),
)

# id / code / name / sort_order / subject_id / parent_id
# 247001-247008 为册域层，247011-247089 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (247001, "pchn_g3a_domain_u01", "小学三上·第一单元 校园生活与勤学好问", 1, SUBJECT, None),
    (247002, "pchn_g3a_domain_u02", "小学三上·第二单元 金秋时节与古诗", 2, SUBJECT, None),
    (247003, "pchn_g3a_domain_u03", "小学三上·第三单元 童话世界与想象", 3, SUBJECT, None),
    (247004, "pchn_g3a_domain_u04", "小学三上·第四单元 预测阅读与续写", 4, SUBJECT, None),
    (247005, "pchn_g3a_domain_u05", "小学三上·第五单元 留心观察与习作起步", 5, SUBJECT, None),
    (247006, "pchn_g3a_domain_u06", "小学三上·第六单元 祖国山河与古诗", 6, SUBJECT, None),
    (247007, "pchn_g3a_domain_u07", "小学三上·第七单元 自然之声与珍爱生命", 7, SUBJECT, None),
    (247008, "pchn_g3a_domain_u08", "小学三上·第八单元 美好品质与文言启蒙", 8, SUBJECT, None),

    # 第一单元 校园生活
    (247011, "pchn_g3a_point_school_scene", "《大青树下的小学》校园场景：傣族、景颇族、阿昌族、德昂族和汉族学生同校学习、跳孔雀舞、摔跤、读课文", 1, SUBJECT, 247001),
    (247012, "pchn_g3a_point_school_center", "《大青树下的小学》中心句：“这就是我们的学校，一所可爱的边疆小学”，体会民族团结与自豪", 2, SUBJECT, 247001),
    (247013, "pchn_g3a_point_u01_duoyin", "多音字：干（gān／gàn）、好（hǎo／hào）、当（dāng／dàng）、晃（huàng／huǎng）", 3, SUBJECT, 247001),
    (247014, "pchn_g3a_point_flower_author", "《花的学校》作者与出处：印度诗人泰戈尔《新月集》，以儿童视角想象", 4, SUBJECT, 247001),
    (247015, "pchn_g3a_point_flower_personify", "《花的学校》拟人想象：花孩子在地下学校上学，下雨放假便冲出来玩耍", 5, SUBJECT, 247001),
    (247016, "pchn_g3a_point_flower_metaphor", "《花的学校》比喻句：“湿润的东风走过荒野，在竹林中吹着口笛”，把东风当作人写", 6, SUBJECT, 247001),
    (247017, "pchn_g3a_point_ask_reason", "《不懂就要问》孙中山勤学好问：“学问学问，不懂就要问”，宁可挨打也要弄明白", 7, SUBJECT, 247001),
    (247018, "pchn_g3a_point_u01_punct", "标点符号：提示语在前用冒号，提示语在后用句号，提示语在中间用逗号", 8, SUBJECT, 247001),
    (247019, "pchn_g3a_point_u01_words", "词语积累：摇头晃脑、披头散发、张牙舞爪、提心吊胆、面红耳赤、手忙脚乱、眼疾手快、口干舌燥", 9, SUBJECT, 247001),
    (247020, "pchn_g3a_point_u01_similar", "形近字：扮—纷、静—净、停—亭、粗—组，注意偏旁与部件区别", 10, SUBJECT, 247001),

    # 第二单元 金秋时节
    (247021, "pchn_g3a_point_shanxing_recite", "《山行》背诵默写：远上寒山石径斜，白云生处有人家；停车坐爱枫林晚，霜叶红于二月花", 1, SUBJECT, 247002),
    (247022, "pchn_g3a_point_shanxing_read", "《山行》理解：斜指山路弯弯，生指白云形成之处，坐意为因为，霜叶红于二月花写枫叶胜过春花", 2, SUBJECT, 247002),
    (247023, "pchn_g3a_point_liujingwen_recite", "《赠刘景文》背诵默写：荷尽已无擎雨盖，菊残犹有傲霜枝；一年好景君须记，最是橙黄橘绿时", 3, SUBJECT, 247002),
    (247024, "pchn_g3a_point_liujingwen_read", "《赠刘景文》理解：擎雨盖指荷叶，傲霜枝写菊的坚韧，橙黄橘绿指初冬丰收景色", 4, SUBJECT, 247002),
    (247025, "pchn_g3a_point_yeshu_recite", "《夜书所见》背诵默写：萧萧梧叶送寒声，江上秋风动客情；知有儿童挑促织，夜深篱落一灯明", 5, SUBJECT, 247002),
    (247026, "pchn_g3a_point_yeshu_read", "《夜书所见》理解：萧萧写风声，客情指思乡之情，挑促织即捉蟋蟀，篱落指篱笆", 6, SUBJECT, 247002),
    (247027, "pchn_g3a_point_cement_metaphor", "《铺满金色巴掌的水泥道》比喻：梧桐叶像金色小巴掌，水泥道像铺上彩色地毯，写出秋景之美", 7, SUBJECT, 247002),
    (247028, "pchn_g3a_point_autumn_rain_key", "《秋天的雨》借助关键语句概括段意：秋雨是钥匙，从颜色、气味、声音三方面写秋天", 8, SUBJECT, 247002),
    (247029, "pchn_g3a_point_autumn_rain_center", "《秋天的雨》中心句：“秋天的雨，是一把钥匙”，各段开头句提示段落内容", 9, SUBJECT, 247002),
    (247030, "pchn_g3a_point_autumn_sound", "《听听，秋的声音》拟声与拟人：大树抖抖手臂“刷刷”，蟋蟀振动翅膀“㘗㘗”，大雁撒下叮咛", 10, SUBJECT, 247002),
    (247031, "pchn_g3a_point_u02_duoyin", "多音字：挑（tiāo／tiǎo）、扇（shàn／shān）、铺（pū／pù）", 11, SUBJECT, 247002),
    (247032, "pchn_g3a_point_u02_words", "词语积累：秋高气爽、天高云淡、秋风习习、一叶知秋、金桂飘香、层林尽染、五谷丰登、果实累累、春华秋实", 12, SUBJECT, 247002),

    # 第三单元 童话世界
    (247033, "pchn_g3a_point_match_girl_author", "《卖火柴的小女孩》作者：丹麦作家安徒生；大年夜街头卖火柴的悲惨遭遇", 1, SUBJECT, 247003),
    (247034, "pchn_g3a_point_match_girl_illusion", "五次擦火柴幻象：暖和的火炉、喷香的烤鹅、美丽的圣诞树、慈爱的奶奶、奶奶抱着她飞走", 2, SUBJECT, 247003),
    (247035, "pchn_g3a_point_match_girl_contrast", "虚实对比：现实寒冷、饥饿、孤独，幻象温暖、富足、幸福，突出人物命运", 3, SUBJECT, 247003),
    (247036, "pchn_g3a_point_seed_transform", "《那一定会很好》种子变形记：种子→大树→手推车→椅子→木地板，乐观面对每次变化", 4, SUBJECT, 247003),
    (247037, "pchn_g3a_point_cow_stomach", "《在牛肚子里旅行》科学知识：牛有四个胃会反刍，红头从牛嘴到胃再回到嘴里", 5, SUBJECT, 247003),
    (247038, "pchn_g3a_point_cow_friends", "《在牛肚子里旅行》人物：青头机智勇敢、沉着相助，红头紧张害怕后脱险", 6, SUBJECT, 247003),
    (247039, "pchn_g3a_point_cheese_leader", "《一块奶酪》蚂蚁队长：以身作则、遵守纪律、关爱弱小，赢得大家信任", 7, SUBJECT, 247003),
    (247040, "pchn_g3a_point_fairy_feature", "童话文体特点：拟人化形象、大胆想象、反复结构，用故事寄托道理", 8, SUBJECT, 247003),
    (247041, "pchn_g3a_point_u03_duoyin", "多音字：几（jī／jǐ）、答（dā／dá）、应（yīng／yìng）、骨（gǔ／gū）", 9, SUBJECT, 247003),
    (247042, "pchn_g3a_point_u03_similar", "形近字：旅—族、偷—愉、救—球、流—统，注意形旁表义", 10, SUBJECT, 247003),

    # 第四单元 预测与续写
    (247043, "pchn_g3a_point_predict_method", "预测方法：依据题目、插图、课文内容和生活经验，边读边猜想后续情节", 1, SUBJECT, 247004),
    (247044, "pchn_g3a_point_old_house_repeat", "《总也倒不了的老屋》三次答应：小猫借宿、老母鸡孵蛋、小蜘蛛结网，反复结构推进故事", 2, SUBJECT, 247004),
    (247045, "pchn_g3a_point_carrot_beard", "《胡萝卜先生的长胡子》预测与验证：长胡子被男孩放风筝、鸟太太晾尿布，体会情节合理", 3, SUBJECT, 247004),
    (247046, "pchn_g3a_point_dog_endings", "《小狗学叫》三种结局：学小公鸡叫、学杜鹃叫、遇见同类，开放式结尾留想象空间", 4, SUBJECT, 247004),
    (247047, "pchn_g3a_point_continue_write", "续写要求：情节合理、人物性格一致、与原文自然衔接，可加入对话与动作", 5, SUBJECT, 247004),
    (247048, "pchn_g3a_point_ellipsis", "省略号用法：表示话未说完、语意未尽或列举省略，朗读时适当停顿", 6, SUBJECT, 247004),
    (247049, "pchn_g3a_point_u04_duoyin", "多音字：吗（ma／má）、担（dān／dàn）、压（yā／yà）", 7, SUBJECT, 247004),
    (247050, "pchn_g3a_point_u04_similar", "形近字：备—各、壁—璧、饿—俄、访—防，注意同音形近辨析", 8, SUBJECT, 247004),

    # 第五单元 留心观察
    (247051, "pchn_g3a_point_kingfisher_look", "《搭船的鸟》翠鸟外形：红色长嘴、翠绿色羽毛、蓝色翅膀，观察细致", 1, SUBJECT, 247005),
    (247052, "pchn_g3a_point_kingfisher_action", "《搭船的鸟》捕鱼动作：冲、飞、衔、站、吞，动词连用写出敏捷连贯", 2, SUBJECT, 247005),
    (247053, "pchn_g3a_point_meadow_change", "《金色的草地》蒲公英变化：早晨绿色、中午金色、傍晚绿色，草地颜色随花开放变化", 3, SUBJECT, 247005),
    (247054, "pchn_g3a_point_meadow_reason", "《金色的草地》变化原因：蒲公英花瓣张开时金色、合拢时绿色，要留心观察才能发现", 4, SUBJECT, 247005),
    (247055, "pchn_g3a_point_observe_method", "观察方法：调动眼耳鼻等多种感官，抓住事物特点，按一定顺序持续观察", 5, SUBJECT, 247005),
    (247056, "pchn_g3a_point_observe_diary", "观察日记起步：记录时间、地点、景物变化与自己的感受，内容真实具体", 6, SUBJECT, 247005),
    (247057, "pchn_g3a_point_u05_duoyin", "多音字：盛（shèng／chéng）、朝（zhāo／cháo）、觉（jué／jiào）", 7, SUBJECT, 247005),
    (247058, "pchn_g3a_point_meadow_metaphor", "比喻句：“蒲公英的花就像我们的手掌，可以张开、合上”，形象写出花瓣形态", 8, SUBJECT, 247005),

    # 第六单元 祖国山河
    (247059, "pchn_g3a_point_tianmen_recite", "《望天门山》背诵默写：天门中断楚江开，碧水东流至此回；两岸青山相对出，孤帆一片日边来", 1, SUBJECT, 247006),
    (247060, "pchn_g3a_point_tianmen_read", "《望天门山》理解：中断、楚江、回写江水回旋，孤帆与日边写出壮阔画面", 2, SUBJECT, 247006),
    (247061, "pchn_g3a_point_xihu_recite", "《饮湖上初晴后雨》背诵默写：水光潋滟晴方好，山色空蒙雨亦奇；欲把西湖比西子，淡妆浓抹总相宜", 3, SUBJECT, 247006),
    (247062, "pchn_g3a_point_xihu_read", "《饮湖上初晴后雨》理解：潋滟写波光，空蒙写雨雾，西子指西施，相宜指都合适", 4, SUBJECT, 247006),
    (247063, "pchn_g3a_point_dongting_recite", "《望洞庭》背诵默写：湖光秋月两相和，潭面无风镜未磨；遥望洞庭山水翠，白银盘里一青螺", 5, SUBJECT, 247006),
    (247064, "pchn_g3a_point_dongting_read", "《望洞庭》理解：相和写湖光月色交融，潭面如未磨铜镜，青螺比喻君山", 6, SUBJECT, 247006),
    (247065, "pchn_g3a_point_xisha_center", "《富饶的西沙群岛》中心句：“风景优美，物产丰富”，按海面、海底、海滩、海岛总分结构写", 7, SUBJECT, 247006),
    (247066, "pchn_g3a_point_seaside_order", "《海滨小城》地点顺序：大海→沙滩→庭院→公园→街道，移步换景条理清楚", 8, SUBJECT, 247006),
    (247067, "pchn_g3a_point_xinganling_season", "《美丽的小兴安岭》季节顺序：春、夏、秋、冬；结尾称其为花园和宝库", 9, SUBJECT, 247006),
    (247068, "pchn_g3a_point_key_sentence", "借助关键语句概括段意：找中心句、总起句、过渡句，用简洁语言归纳段落内容", 10, SUBJECT, 247006),
    (247069, "pchn_g3a_point_u06_duoyin", "多音字：参（shēn／cān）、划（huá／huà）、兴（xīng／xìng）、舍（shě／shè）", 11, SUBJECT, 247006),
    (247070, "pchn_g3a_point_u06_words", "词语积累：风景优美、物产丰富、五光十色、瑰丽无比、成群结队、各种各样", 12, SUBJECT, 247006),
    (247071, "pchn_g3a_point_u06_similar", "形近字：饶—绕、滨—宾、岭—铃、渔—鱼，结合词义辨字形", 13, SUBJECT, 247006),

    # 第七单元 自然之声
    (247072, "pchn_g3a_point_nature_center", "《大自然的声音》中心句：“大自然有许多美妙的声音”，总起全文", 1, SUBJECT, 247007),
    (247073, "pchn_g3a_point_nature_structure", "《大自然的声音》结构：风是大自然的音乐家、水也是音乐家、动物是歌手，分层写声音", 2, SUBJECT, 247007),
    (247074, "pchn_g3a_point_nature_onomatopoeia", "拟声词积累：淙淙、潺潺、哗啦啦、唧哩哩，摹写风声水声与鸟鸣", 3, SUBJECT, 247007),
    (247075, "pchn_g3a_point_big_book", "《读不完的大书》“大书”指大自然：花草树木、飞鸟昆虫都值得读，观察中长知识", 4, SUBJECT, 247007),
    (247076, "pchn_g3a_point_father_bird", "《父亲、树林和鸟》主题：父亲爱鸟、懂鸟，“我真高兴，父亲不是猎人”表达护鸟心愿", 5, SUBJECT, 247007),
    (247077, "pchn_g3a_point_parallel", "排比句：三个或以上结构相似的句子连用，增强语势，如写风、水、动物的段落", 6, SUBJECT, 247007),
    (247078, "pchn_g3a_point_personify", "拟人句：把景物当作人来写，如“风，是大自然的音乐家”，使表达生动亲切", 7, SUBJECT, 247007),
    (247079, "pchn_g3a_point_u07_duoyin", "多音字：呢（ne／ní）、扎（zhā／zhá／zā）、朝（zhāo／cháo）", 8, SUBJECT, 247007),
    (247080, "pchn_g3a_point_u07_punct", "标点符号：破折号表示解释说明或声音延长，引号表示特殊含义或引用", 9, SUBJECT, 247007),

    # 第八单元 美好品质
    (247081, "pchn_g3a_point_simaguang_text", "《司马光》原文背诵：群儿戏于庭，一儿登瓮，足跌没水中。众皆弃去，光持石击瓮破之，水迸，儿得活。", 1, SUBJECT, 247008),
    (247082, "pchn_g3a_point_simaguang_words", "《司马光》文言字词：庭指庭院，瓮指口小肚大的陶器，皆指都，弃去指逃走，迸指涌出", 2, SUBJECT, 247008),
    (247083, "pchn_g3a_point_simaguang_read", "文言文朗读：读准停顿“群儿／戏于庭”，借助注释和插图理解句意并复述故事", 3, SUBJECT, 247008),
    (247084, "pchn_g3a_point_grey_bird", "《灰雀》列宁与小男孩：男孩知错就改放回灰雀，列宁用爱心保护孩子自尊", 4, SUBJECT, 247008),
    (247085, "pchn_g3a_point_bethune", "《手术台就是阵地》白求恩：战火中坚守手术台，环境描写衬托救死扶伤的高尚品质", 5, SUBJECT, 247008),
    (247086, "pchn_g3a_point_diary_format", "日记格式：第一行写日期、星期、天气，正文另起行，内容真实、有重点", 6, SUBJECT, 247008),
    (247087, "pchn_g3a_point_u08_punct", "标点符号：顿号用于并列词语之间，冒号提示下文，引号引用人物原话", 7, SUBJECT, 247008),
    (247088, "pchn_g3a_point_u08_duoyin", "多音字：没（mò／méi）、斗（dòu／dǒu）、大（dà／dài）", 8, SUBJECT, 247008),
    (247089, "pchn_g3a_point_u08_similar", "形近字：司—同、庭—廷、弃—充、术—木，注意部件与笔画的细微差别", 9, SUBJECT, 247008),
)

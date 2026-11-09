"""统编版中国历史七年级上册：单元课目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 8
G7 = 7
BOOK_ID = 1319

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版中国历史七年级上册",
    "jhis_g7a",
    19,
    "人民教育出版社",
    SUBJECT,
    G7,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 第一单元 史前时期：中国境内早期人类与文明的起源
    (131901, "第一单元 史前时期：中国境内早期人类与文明的起源", "jhis_g7a_u01", 1, BOOK_ID, None),
    (131911, "第1课 中国境内早期人类的代表——北京人", "jhis_g7a_l01", 1, BOOK_ID, 131901),
    (131912, "第2课 原始农耕生活", "jhis_g7a_l02", 2, BOOK_ID, 131901),
    (131913, "第3课 远古的传说", "jhis_g7a_l03", 3, BOOK_ID, 131901),

    # 第二单元 夏商周时期：早期国家与社会变革
    (131902, "第二单元 夏商周时期：早期国家与社会变革", "jhis_g7a_u02", 2, BOOK_ID, None),
    (131921, "第4课 夏商周的更替", "jhis_g7a_l04", 1, BOOK_ID, 131902),
    (131922, "第5课 青铜器与甲骨文", "jhis_g7a_l05", 2, BOOK_ID, 131902),
    (131923, "第6课 动荡的春秋时期", "jhis_g7a_l06", 3, BOOK_ID, 131902),
    (131924, "第7课 战国时期的社会变化", "jhis_g7a_l07", 4, BOOK_ID, 131902),
    (131925, "第8课 百家争鸣", "jhis_g7a_l08", 5, BOOK_ID, 131902),

    # 第三单元 秦汉时期：统一多民族国家的建立和巩固
    (131903, "第三单元 秦汉时期：统一多民族国家的建立和巩固", "jhis_g7a_u03", 3, BOOK_ID, None),
    (131931, "第9课 秦统一中国", "jhis_g7a_l09", 1, BOOK_ID, 131903),
    (131932, "第10课 秦末农民大起义", "jhis_g7a_l10", 2, BOOK_ID, 131903),
    (131933, "第11课 西汉建立和“文景之治”", "jhis_g7a_l11", 3, BOOK_ID, 131903),
    (131934, "第12课 汉武帝巩固大一统王朝", "jhis_g7a_l12", 4, BOOK_ID, 131903),
    (131935, "第13课 东汉的兴衰", "jhis_g7a_l13", 5, BOOK_ID, 131903),
    (131936, "第14课 沟通中外文明的“丝绸之路”", "jhis_g7a_l14", 6, BOOK_ID, 131903),
    (131937, "第15课 两汉的科技和文化", "jhis_g7a_l15", 7, BOOK_ID, 131903),

    # 第四单元 三国两晋南北朝时期：政权分立与民族交融
    (131904, "第四单元 三国两晋南北朝时期：政权分立与民族交融", "jhis_g7a_u04", 4, BOOK_ID, None),
    (131941, "第16课 三国鼎立", "jhis_g7a_l16", 1, BOOK_ID, 131904),
    (131942, "第17课 西晋的短暂统一和北方各族的内迁", "jhis_g7a_l17", 2, BOOK_ID, 131904),
    (131943, "第18课 东晋南朝时期江南地区的开发", "jhis_g7a_l18", 3, BOOK_ID, 131904),
    (131944, "第19课 北魏政治和北方民族大交融", "jhis_g7a_l19", 4, BOOK_ID, 131904),
    (131945, "第20课 魏晋南北朝的科技与文化", "jhis_g7a_l20", 5, BOOK_ID, 131904),
)

# id / code / name / sort_order / subject_id / parent_id
# 219001-219014 为册域层，219015-219098 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (219001, "jhis_g7a_domain_prehistory", "初中七上·史前时期：早期人类与文明起源", 1, SUBJECT, None),
    (219002, "jhis_g7a_domain_xia_shang_zhou", "初中七上·夏商周的更替与早期国家", 2, SUBJECT, None),
    (219003, "jhis_g7a_domain_bronze_oracle", "初中七上·青铜器与甲骨文", 3, SUBJECT, None),
    (219004, "jhis_g7a_domain_spring_autumn", "初中七上·春秋战国的社会变革", 4, SUBJECT, None),
    (219005, "jhis_g7a_domain_hundred_schools", "初中七上·百家争鸣", 5, SUBJECT, None),
    (219006, "jhis_g7a_domain_qin_unification", "初中七上·秦的统一与中央集权", 6, SUBJECT, None),
    (219007, "jhis_g7a_domain_han_founding", "初中七上·秦末起义与西汉初建", 7, SUBJECT, None),
    (219008, "jhis_g7a_domain_han_wudi", "初中七上·汉武帝大一统与东汉兴衰", 8, SUBJECT, None),
    (219009, "jhis_g7a_domain_silk_road", "初中七上·丝绸之路与中外交流", 9, SUBJECT, None),
    (219010, "jhis_g7a_domain_han_culture", "初中七上·两汉的科技与文化", 10, SUBJECT, None),
    (219011, "jhis_g7a_domain_three_kingdoms", "初中七上·三国鼎立与西晋统一", 11, SUBJECT, None),
    (219012, "jhis_g7a_domain_eastern_jin", "初中七上·东晋南朝与江南开发", 12, SUBJECT, None),
    (219013, "jhis_g7a_domain_northern_wei", "初中七上·北魏政治与民族交融", 13, SUBJECT, None),
    (219014, "jhis_g7a_domain_wei_jin_culture", "初中七上·魏晋南北朝的科技与文化", 14, SUBJECT, None),

    # 史前时期：早期人类与文明起源
    (219015, "jhis_g7a_point_yuanmou", "元谋人：我国境内目前已确认的最早古人类之一", 1, SUBJECT, 219001),
    (219016, "jhis_g7a_point_peking_man", "北京人：距今约70万—20万年，周口店，保留猿的若干特征", 2, SUBJECT, 219001),
    (219017, "jhis_g7a_point_peking_fire", "北京人使用打制石器、会使用火并长时间保存火种", 3, SUBJECT, 219001),
    (219018, "jhis_g7a_point_hemudu", "河姆渡人：长江流域，干栏式建筑，种植水稻", 4, SUBJECT, 219001),
    (219019, "jhis_g7a_point_banpo", "半坡人：黄河流域，半地穴式圆形房屋，种植粟", 5, SUBJECT, 219001),
    (219020, "jhis_g7a_point_agriculture_origin", "原始农业兴起的重要标志：农作物种植、家畜饲养、聚落与磨制石器", 6, SUBJECT, 219001),
    (219021, "jhis_g7a_point_abdication", "禅让制：尧舜禹时期通过推举产生部落联盟首领", 7, SUBJECT, 219001),

    # 夏商周的更替与早期国家
    (219022, "jhis_g7a_point_xia_founding", "夏朝建立：约公元前2070年，禹建立我国历史上第一个王朝", 1, SUBJECT, 219002),
    (219023, "jhis_g7a_point_hereditary", "王位世袭制取代禅让制：“公天下”变为“家天下”", 2, SUBJECT, 219002),
    (219024, "jhis_g7a_point_shang_founding", "商汤灭夏、盘庚迁殷与商朝统治的稳定", 3, SUBJECT, 219002),
    (219025, "jhis_g7a_point_zhou_founding", "武王伐纣、牧野之战与西周建立（公元前1046年）", 4, SUBJECT, 219002),
    (219026, "jhis_g7a_point_fengjian_content", "西周分封制的目的、对象及诸侯的权利与义务", 5, SUBJECT, 219002),
    (219027, "jhis_g7a_point_fengjian_effect", "分封制的作用与后期诸侯割据的弊端", 6, SUBJECT, 219002),
    (219028, "jhis_g7a_point_zhou_fall", "西周灭亡与平王东迁（公元前771年、公元前770年）", 7, SUBJECT, 219002),

    # 青铜器与甲骨文
    (219029, "jhis_g7a_point_bronze_types", "青铜器的种类与礼器功能：鼎、簋等礼器象征等级", 1, SUBJECT, 219003),
    (219030, "jhis_g7a_point_bronze_craft", "青铜铸造工艺：泥范铸造法与合金配比", 2, SUBJECT, 219003),
    (219031, "jhis_g7a_point_bronze_masterpiece", "司母戊鼎与四羊方尊的工艺成就", 3, SUBJECT, 219003),
    (219032, "jhis_g7a_point_oracle_bones", "甲骨文的发现、记载内容与造字方法", 4, SUBJECT, 219003),
    (219033, "jhis_g7a_point_oracle_status", "甲骨文：我国已发现年代最早、体系较为完整的文字", 5, SUBJECT, 219003),

    # 春秋战国的社会变革
    (219034, "jhis_g7a_point_iron_plow", "春秋时期铁制农具和牛耕的出现与推广", 1, SUBJECT, 219004),
    (219035, "jhis_g7a_point_qi_hegemony", "齐桓公首霸：管仲改革与“尊王攘夷”", 2, SUBJECT, 219004),
    (219036, "jhis_g7a_point_hegemony_effect", "春秋争霸战争的影响：统一趋势与民族交融", 3, SUBJECT, 219004),
    (219037, "jhis_g7a_point_seven_states", "战国七雄的形成与兼并战争的特点", 4, SUBJECT, 219004),
    (219038, "jhis_g7a_point_shangyang_background", "商鞅变法的背景与秦孝公的支持", 5, SUBJECT, 219004),
    (219039, "jhis_g7a_point_shangyang_politics", "商鞅变法的政治措施：推行县制、奖励军功、编制户籍", 6, SUBJECT, 219004),
    (219040, "jhis_g7a_point_shangyang_economy", "商鞅变法的经济措施：废除井田制、鼓励耕织、统一度量衡", 7, SUBJECT, 219004),
    (219041, "jhis_g7a_point_shangyang_effect", "商鞅变法的作用：秦国国力大增，为统一奠定基础", 8, SUBJECT, 219004),
    (219042, "jhis_g7a_point_dujiangyan", "都江堰：李冰主持修建，成都平原成为“天府之国”", 9, SUBJECT, 219004),

    # 百家争鸣
    (219043, "jhis_g7a_point_laozi", "老子与道家：道法自然、无为而治", 1, SUBJECT, 219005),
    (219044, "jhis_g7a_point_laozi_dialectic", "老子的辩证法思想：对立统一、以柔克刚", 2, SUBJECT, 219005),
    (219045, "jhis_g7a_point_confucius_ren", "孔子与儒家：核心思想“仁”，主张“为政以德”", 3, SUBJECT, 219005),
    (219046, "jhis_g7a_point_confucius_edu", "孔子的教育主张：有教无类、因材施教、学思结合", 4, SUBJECT, 219005),
    (219047, "jhis_g7a_point_mozi", "墨子与墨家：兼爱、非攻、尚贤、节俭", 5, SUBJECT, 219005),
    (219048, "jhis_g7a_point_mengzi_xunzi", "孟子与荀子：仁政、民贵君轻与礼治主张", 6, SUBJECT, 219005),
    (219049, "jhis_g7a_point_hanfei", "韩非与法家：以法治国、树立君主权威、加强中央集权", 7, SUBJECT, 219005),
    (219050, "jhis_g7a_point_hundred_schools_effect", "百家争鸣的意义：思想文化繁荣，奠定中华传统文化基础", 8, SUBJECT, 219005),

    # 秦的统一与中央集权
    (219051, "jhis_g7a_point_qin_unify", "秦灭六国：公元前230—前221年，秦始皇完成统一", 1, SUBJECT, 219006),
    (219052, "jhis_g7a_point_emperor_system", "皇帝制度的确立：皇帝独尊、皇权至上", 2, SUBJECT, 219006),
    (219053, "jhis_g7a_point_central_office", "中央官制：丞相、太尉、御史大夫分工牵制", 3, SUBJECT, 219006),
    (219054, "jhis_g7a_point_commandery", "地方推行郡县制：郡县长官由朝廷直接任免", 4, SUBJECT, 219006),
    (219055, "jhis_g7a_point_unify_standard", "统一文字为小篆、统一货币与度量衡", 5, SUBJECT, 219006),
    (219056, "jhis_g7a_point_great_wall", "北筑长城、南征百越与开凿灵渠", 6, SUBJECT, 219006),
    (219057, "jhis_g7a_point_qin_tyranny", "秦朝暴政：赋税徭役沉重、刑罚严苛、焚书坑儒", 7, SUBJECT, 219006),
    (219058, "jhis_g7a_point_qin_significance", "秦统一的历史意义：建立统一多民族国家，奠定疆域基础", 8, SUBJECT, 219006),

    # 秦末起义与西汉初建
    (219059, "jhis_g7a_point_chen_sheng", "陈胜吴广起义：公元前209年大泽乡，我国历史上第一次大规模农民起义", 1, SUBJECT, 219007),
    (219060, "jhis_g7a_point_qin_fall", "巨鹿之战、刘邦攻入咸阳与秦朝灭亡", 2, SUBJECT, 219007),
    (219061, "jhis_g7a_point_chu_han", "楚汉之争与西汉建立：公元前202年，刘邦定都长安", 3, SUBJECT, 219007),
    (219062, "jhis_g7a_point_rest_recovery", "汉初休养生息政策：轻徭薄赋、减轻刑罚、释放奴婢", 4, SUBJECT, 219007),
    (219063, "jhis_g7a_point_wen_jing", "“文景之治”：以农为本、勤俭治国，社会经济恢复发展", 5, SUBJECT, 219007),

    # 汉武帝大一统与东汉兴衰
    (219064, "jhis_g7a_point_tuien", "汉武帝“推恩令”：削弱诸侯王势力，加强中央集权", 1, SUBJECT, 219008),
    (219065, "jhis_g7a_point_revere_confucian", "汉武帝“罢黜百家，尊崇儒术”，设太学", 2, SUBJECT, 219008),
    (219066, "jhis_g7a_point_salt_iron", "汉武帝盐铁官营与统一铸造五铢钱", 3, SUBJECT, 219008),
    (219067, "jhis_g7a_point_xiongnu", "汉武帝北击匈奴：卫青、霍去病与漠北战役", 4, SUBJECT, 219008),
    (219068, "jhis_g7a_point_eastern_han_founding", "王莽夺权与东汉建立：公元25年刘秀定都洛阳", 5, SUBJECT, 219008),
    (219069, "jhis_g7a_point_guangwu", "“光武中兴”：释放奴婢、减轻赋税、整顿吏治", 6, SUBJECT, 219008),
    (219070, "jhis_g7a_point_eunuch_yellow_turban", "外戚宦官交替专权与黄巾起义（184年）", 7, SUBJECT, 219008),

    # 丝绸之路与中外交流
    (219071, "jhis_g7a_point_zhang_qian", "张骞出使西域（公元前138年、公元前119年）", 1, SUBJECT, 219009),
    (219072, "jhis_g7a_point_silk_route", "丝绸之路路线：长安—河西走廊—西域—中亚—西亚—欧洲", 2, SUBJECT, 219009),
    (219073, "jhis_g7a_point_silk_exchange", "丝绸之路上的物产与技术交流", 3, SUBJECT, 219009),
    (219074, "jhis_g7a_point_west_regions_protectorate", "西域都护的设置：公元前60年，西域正式归属中央政权", 4, SUBJECT, 219009),
    (219075, "jhis_g7a_point_sea_silk_road", "海上丝绸之路与班超经营西域", 5, SUBJECT, 219009),

    # 两汉的科技与文化
    (219076, "jhis_g7a_point_papermaking", "蔡伦改进造纸术与“蔡侯纸”的推广", 1, SUBJECT, 219010),
    (219077, "jhis_g7a_point_zhang_zhongjing", "张仲景与《伤寒杂病论》，“医圣”", 2, SUBJECT, 219010),
    (219078, "jhis_g7a_point_hua_tuo", "华佗：麻沸散与五禽戏", 3, SUBJECT, 219010),
    (219079, "jhis_g7a_point_sima_qian", "司马迁与《史记》：我国第一部纪传体通史", 4, SUBJECT, 219010),
    (219080, "jhis_g7a_point_buddhism_taoism", "佛教传入与道教兴起", 5, SUBJECT, 219010),

    # 三国鼎立与西晋统一
    (219081, "jhis_g7a_point_guandu", "官渡之战：200年曹操击败袁绍，奠定统一北方的基础", 1, SUBJECT, 219011),
    (219082, "jhis_g7a_point_red_cliffs", "赤壁之战：208年孙刘联军击败曹操，奠定三国鼎立的基础", 2, SUBJECT, 219011),
    (219083, "jhis_g7a_point_three_kingdoms", "三国鼎立：220年魏、221年蜀汉、229年吴", 3, SUBJECT, 219011),
    (219084, "jhis_g7a_point_three_kingdoms_economy", "三国时期的经济发展：屯田、蜀锦、造船与卫温到达夷洲", 4, SUBJECT, 219011),
    (219085, "jhis_g7a_point_western_jin", "西晋建立与统一：266年司马炎建晋，280年灭吴", 5, SUBJECT, 219011),
    (219086, "jhis_g7a_point_eight_princes", "八王之乱、西晋灭亡与北方各族内迁", 6, SUBJECT, 219011),

    # 东晋南朝与江南开发
    (219087, "jhis_g7a_point_eastern_jin_founding", "东晋建立：317年司马睿定都建康，“王与马，共天下”", 1, SUBJECT, 219012),
    (219088, "jhis_g7a_point_feishui", "淝水之战：383年东晋击败前秦，保存江南开发成果", 2, SUBJECT, 219012),
    (219089, "jhis_g7a_point_southern_dynasties", "南朝更替：宋、齐、梁、陈", 3, SUBJECT, 219012),
    (219090, "jhis_g7a_point_jiangnan_develop", "江南地区开发的原因、表现与影响", 4, SUBJECT, 219012),

    # 北魏政治与民族交融
    (219091, "jhis_g7a_point_northern_wei_unify", "北魏统一北方：439年鲜卑拓跋部统一黄河流域", 1, SUBJECT, 219013),
    (219092, "jhis_g7a_point_move_capital", "北魏孝文帝迁都洛阳及其目的", 2, SUBJECT, 219013),
    (219093, "jhis_g7a_point_xiaowen_reform", "孝文帝改革措施：说汉语、穿汉服、改汉姓、通婚姻", 3, SUBJECT, 219013),
    (219094, "jhis_g7a_point_ethnic_blend", "孝文帝改革的作用与北方地区民族交融的表现", 4, SUBJECT, 219013),

    # 魏晋南北朝的科技与文化
    (219095, "jhis_g7a_point_qimin_yaoshu", "贾思勰与《齐民要术》：我国现存最早的一部完整农书", 1, SUBJECT, 219014),
    (219096, "jhis_g7a_point_zu_chongzhi", "祖冲之：圆周率精确到小数点后第七位与《大明历》", 2, SUBJECT, 219014),
    (219097, "jhis_g7a_point_wang_xizhi", "王羲之与《兰亭集序》，“书圣”", 3, SUBJECT, 219014),
    (219098, "jhis_g7a_point_grottoes", "顾恺之的绘画与云冈石窟、龙门石窟", 4, SUBJECT, 219014),
)

"""人教版（PEP）小学英语二年级下册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G2 = 2
BOOK_ID = 1428

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语二年级下册",
    "peng_g2b",
    28,
    "人民教育出版社",
    SUBJECT,
    G2,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 My day
    (142801, "Unit 1 My day", "peng_g2b_u01", 1, BOOK_ID, None),
    (142802, "Part A", "peng_g2b_u01_a", 1, BOOK_ID, 142801),
    (142803, "Part B", "peng_g2b_u01_b", 2, BOOK_ID, 142801),
    (142804, "Part C", "peng_g2b_u01_c", 3, BOOK_ID, 142801),

    # Unit 2 Weather
    (142810, "Unit 2 Weather", "peng_g2b_u02", 2, BOOK_ID, None),
    (142811, "Part A", "peng_g2b_u02_a", 1, BOOK_ID, 142810),
    (142812, "Part B", "peng_g2b_u02_b", 2, BOOK_ID, 142810),
    (142813, "Part C", "peng_g2b_u02_c", 3, BOOK_ID, 142810),

    # Unit 3 Seasons
    (142820, "Unit 3 Seasons", "peng_g2b_u03", 3, BOOK_ID, None),
    (142821, "Part A", "peng_g2b_u03_a", 1, BOOK_ID, 142820),
    (142822, "Part B", "peng_g2b_u03_b", 2, BOOK_ID, 142820),
    (142823, "Part C", "peng_g2b_u03_c", 3, BOOK_ID, 142820),

    # Unit 4 My home
    (142830, "Unit 4 My home", "peng_g2b_u04", 4, BOOK_ID, None),
    (142831, "Part A", "peng_g2b_u04_a", 1, BOOK_ID, 142830),
    (142832, "Part B", "peng_g2b_u04_b", 2, BOOK_ID, 142830),
    (142833, "Part C", "peng_g2b_u04_c", 3, BOOK_ID, 142830),

    # Unit 5 My room
    (142840, "Unit 5 My room", "peng_g2b_u05", 5, BOOK_ID, None),
    (142841, "Part A", "peng_g2b_u05_a", 1, BOOK_ID, 142840),
    (142842, "Part B", "peng_g2b_u05_b", 2, BOOK_ID, 142840),
    (142843, "Part C", "peng_g2b_u05_c", 3, BOOK_ID, 142840),

    # Unit 6 My week
    (142850, "Unit 6 My week", "peng_g2b_u06", 6, BOOK_ID, None),
    (142851, "Part A", "peng_g2b_u06_a", 1, BOOK_ID, 142850),
    (142852, "Part B", "peng_g2b_u06_b", 2, BOOK_ID, 142850),
    (142853, "Part C", "peng_g2b_u06_c", 3, BOOK_ID, 142850),

    # Revision
    (142860, "Revision 1", "peng_g2b_rev1", 7, BOOK_ID, None),
    (142870, "Revision 2", "peng_g2b_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 270001-270008 为册域层，270010-270099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (270001, "peng_g2b_domain_u01", "小学英语二下·Unit 1 My day", 1, SUBJECT, G2, None),
    (270002, "peng_g2b_domain_u02", "小学英语二下·Unit 2 Weather", 2, SUBJECT, G2, None),
    (270003, "peng_g2b_domain_u03", "小学英语二下·Unit 3 Seasons", 3, SUBJECT, G2, None),
    (270004, "peng_g2b_domain_u04", "小学英语二下·Unit 4 My home", 4, SUBJECT, G2, None),
    (270005, "peng_g2b_domain_u05", "小学英语二下·Unit 5 My room", 5, SUBJECT, G2, None),
    (270006, "peng_g2b_domain_u06", "小学英语二下·Unit 6 My week", 6, SUBJECT, G2, None),
    (270007, "peng_g2b_domain_rev1", "小学英语二下·Revision 1", 7, SUBJECT, G2, None),
    (270008, "peng_g2b_domain_rev2", "小学英语二下·Revision 2", 8, SUBJECT, G2, None),

    # Unit 1 My day
    (270010, "peng_g2b_point_daily_get_up", "日常活动 get up：认读起床短语，并搭配时间构成 I get up at seven.", 1, SUBJECT, G2, 270001),
    (270011, "peng_g2b_point_daily_breakfast", "日常活动 have breakfast：认读吃早饭，have 在此表示“吃”而不是“有”", 2, SUBJECT, G2, 270001),
    (270012, "peng_g2b_point_daily_school", "日常活动 go to school：认读去上学，school 前不加 the", 3, SUBJECT, G2, 270001),
    (270013, "peng_g2b_point_daily_lunch", "日常活动 have lunch：认读吃午饭，三餐名词前一般不加冠词", 4, SUBJECT, G2, 270001),
    (270014, "peng_g2b_point_daily_home_bed", "日常活动 go home／go to bed：认读回家与上床睡觉，home 前不加 to", 5, SUBJECT, G2, 270001),
    (270015, "peng_g2b_point_time_question", "句型 What time is it? 与 It's seven o'clock.：整点时间问答", 6, SUBJECT, G2, 270001),
    (270016, "peng_g2b_point_time_at", "时间介词 at：at seven o'clock 表示在某一时刻，与 in／on 区分", 7, SUBJECT, G2, 270001),
    (270017, "peng_g2b_point_present_simple_i", "一般现在时第一人称：I get up at seven. 用动词原形表达日常习惯", 8, SUBJECT, G2, 270001),
    (270018, "peng_g2b_point_daily_sequence", "作息顺序表达：I get up and then I go to school. 用 then 串联活动", 9, SUBJECT, G2, 270001),

    # Unit 2 Weather
    (270020, "peng_g2b_point_weather_sunny", "天气词汇 sunny：认读晴朗的，由 sun 加 y 并双写 n 构成", 1, SUBJECT, G2, 270002),
    (270021, "peng_g2b_point_weather_rainy", "天气词汇 rainy：认读下雨的，rain 加 y，注意 ai 的读音", 2, SUBJECT, G2, 270002),
    (270022, "peng_g2b_point_weather_cloudy", "天气词汇 cloudy：认读多云的，cloud 加 y 构成形容词", 3, SUBJECT, G2, 270002),
    (270023, "peng_g2b_point_weather_windy", "天气词汇 windy：认读有风的，wind 加 y 构成形容词", 4, SUBJECT, G2, 270002),
    (270024, "peng_g2b_point_weather_snowy", "天气词汇 snowy：认读下雪的，snow 加 y，ow 读 /əʊ/", 5, SUBJECT, G2, 270002),
    (270025, "peng_g2b_point_how_weather", "句型 How's the weather? 与 It's sunny.：询问并回答天气状况", 6, SUBJECT, G2, 270002),
    (270026, "peng_g2b_point_weather_yes_no", "句型 Is it rainy? 与 Yes, it is.／No, it isn't.：天气的一般疑问句", 7, SUBJECT, G2, 270002),
    (270027, "peng_g2b_point_weather_y_suffix", "名词加 y 变形容词：sun→sunny, rain→rainy, wind→windy 的构词规律", 8, SUBJECT, G2, 270002),
    (270028, "peng_g2b_point_weather_action", "天气与活动匹配：It's snowy. Let's make a snowman. 按天气选择活动", 9, SUBJECT, G2, 270002),

    # Unit 3 Seasons
    (270030, "peng_g2b_point_season_spring", "季节词汇 spring：认读春天，注意 spr 辅音连缀的发音", 1, SUBJECT, G2, 270003),
    (270031, "peng_g2b_point_season_summer", "季节词汇 summer：认读夏天，注意双写 m 的拼写", 2, SUBJECT, G2, 270003),
    (270032, "peng_g2b_point_season_autumn", "季节词汇 autumn：认读秋天，英式 autumn 对应美式 fall", 3, SUBJECT, G2, 270003),
    (270033, "peng_g2b_point_season_winter", "季节词汇 winter：认读冬天，重音在首音节", 4, SUBJECT, G2, 270003),
    (270034, "peng_g2b_point_what_season", "句型 What season do you like? 与 I like spring.：询问并回答喜欢的季节", 5, SUBJECT, G2, 270003),
    (270035, "peng_g2b_point_season_why", "句型 Why? 与 Because I can fly a kite.：用 because 说明喜欢的原因", 6, SUBJECT, G2, 270003),
    (270036, "peng_g2b_point_season_activity", "季节活动搭配：fly kites in spring／swim in summer／pick apples in autumn／make a snowman in winter", 7, SUBJECT, G2, 270003),
    (270037, "peng_g2b_point_season_in", "季节介词 in：in spring 表示在某个季节，季节前不加冠词", 8, SUBJECT, G2, 270003),
    (270038, "peng_g2b_point_season_climate", "四季气候特征：spring warm／summer hot／autumn cool／winter cold", 9, SUBJECT, G2, 270003),

    # Unit 4 My home
    (270040, "peng_g2b_point_home_living_room", "房间词汇 living room：认读客厅，living 表示生活起居", 1, SUBJECT, G2, 270004),
    (270041, "peng_g2b_point_home_bedroom", "房间词汇 bedroom：认读卧室，由 bed 与 room 合成", 2, SUBJECT, G2, 270004),
    (270042, "peng_g2b_point_home_kitchen", "房间词汇 kitchen：认读厨房，注意 tch 字母组合的读音", 3, SUBJECT, G2, 270004),
    (270043, "peng_g2b_point_home_bathroom", "房间词汇 bathroom：认读浴室，由 bath 与 room 合成", 4, SUBJECT, G2, 270004),
    (270044, "peng_g2b_point_home_study", "房间词汇 study：认读书房，作名词时重音在首音节", 5, SUBJECT, G2, 270004),
    (270045, "peng_g2b_point_home_where", "句型 Where is the cat? 与 It's in the kitchen.：询问人物所在的房间", 6, SUBJECT, G2, 270004),
    (270046, "peng_g2b_point_home_prep", "方位介词 in／on／under／near：描述人与物在房间中的位置关系", 7, SUBJECT, G2, 270004),
    (270047, "peng_g2b_point_home_there_is", "There is／There are 句型：There is a bed.／There are two chairs.", 8, SUBJECT, G2, 270004),
    (270048, "peng_g2b_point_home_is_she", "句型 Is she in the study? 与 Yes, she is.：确认某人在某个房间", 9, SUBJECT, G2, 270004),

    # Unit 5 My room
    (270050, "peng_g2b_point_room_bed", "房间物品 bed：认读床，区分 in bed 与 on the bed", 1, SUBJECT, G2, 270005),
    (270051, "peng_g2b_point_room_desk_chair", "房间物品 desk／chair：认读书桌与椅子，desk 特指书桌", 2, SUBJECT, G2, 270005),
    (270052, "peng_g2b_point_room_sofa", "房间物品 sofa：认读沙发，重音在首音节", 3, SUBJECT, G2, 270005),
    (270053, "peng_g2b_point_room_lamp_clock", "房间物品 lamp／clock：认读台灯与时钟，ck 读 /k/", 4, SUBJECT, G2, 270005),
    (270054, "peng_g2b_point_room_window_door", "房间物品 window／door：认读窗户与门，并指认实物", 5, SUBJECT, G2, 270005),
    (270055, "peng_g2b_point_room_where_ball", "句型 Where is my ball? 与 It's under the bed.：询问物品位置", 6, SUBJECT, G2, 270005),
    (270056, "peng_g2b_point_room_prep", "方位介词 on／in／under／behind／near：按图示判断物品方位", 7, SUBJECT, G2, 270005),
    (270057, "peng_g2b_point_room_number", "房间物品单复数：a bed／two beds，this is 与 these are 对应", 8, SUBJECT, G2, 270005),
    (270058, "peng_g2b_point_room_introduce", "介绍自己的房间：This is my room. There is a desk near the window.", 9, SUBJECT, G2, 270005),

    # Unit 6 My week
    (270060, "peng_g2b_point_week_monday", "星期词汇 Monday：认读星期一，缩写为 Mon.", 1, SUBJECT, G2, 270006),
    (270061, "peng_g2b_point_week_tuesday", "星期词汇 Tuesday：认读星期二，缩写为 Tue.", 2, SUBJECT, G2, 270006),
    (270062, "peng_g2b_point_week_wednesday", "星期词汇 Wednesday：认读星期三，注意第一个 d 不发音，缩写 Wed.", 3, SUBJECT, G2, 270006),
    (270063, "peng_g2b_point_week_thursday", "星期词汇 Thursday：认读星期四，th 为咬舌音，缩写 Thu.", 4, SUBJECT, G2, 270006),
    (270064, "peng_g2b_point_week_friday", "星期词汇 Friday：认读星期五，缩写为 Fri.", 5, SUBJECT, G2, 270006),
    (270065, "peng_g2b_point_week_saturday", "星期词汇 Saturday：认读星期六，缩写为 Sat.", 6, SUBJECT, G2, 270006),
    (270066, "peng_g2b_point_week_sunday", "星期词汇 Sunday：认读星期日，缩写为 Sun.", 7, SUBJECT, G2, 270006),
    (270067, "peng_g2b_point_week_capital", "星期名称首字母大写：Monday 不可写成 monday", 8, SUBJECT, G2, 270006),
    (270068, "peng_g2b_point_week_question", "句型 What day is it today? 与 It's Monday.：询问并回答星期", 9, SUBJECT, G2, 270006),
    (270069, "peng_g2b_point_week_on", "星期介词 on：on Monday 表示在星期一，与 at／in 区分", 10, SUBJECT, G2, 270006),
    (270070, "peng_g2b_point_week_routine", "一般现在时描述一周安排：I play football on Saturday.", 11, SUBJECT, G2, 270006),
    (270071, "peng_g2b_point_week_day_suffix", "字母组合 -day 读音：Monday／Tuesday 等词尾 day 读 /deɪ/", 12, SUBJECT, G2, 270006),

    # Revision 1
    (270080, "peng_g2b_point_review_daily", "作息与时间复习：What time is it? 问答与日常活动短语连线", 1, SUBJECT, G2, 270007),
    (270081, "peng_g2b_point_review_weather", "天气词汇与问答复习：How's the weather? 看图回答并匹配活动", 2, SUBJECT, G2, 270007),
    (270082, "peng_g2b_point_review_season", "季节与活动复习：What season do you like? 问答与替换练习", 3, SUBJECT, G2, 270007),
    (270083, "peng_g2b_point_review_phonics_sh_ch", "字母组合复习 sh／ch／th：ship, chair, three 的发音辨别", 4, SUBJECT, G2, 270007),

    # Revision 2
    (270090, "peng_g2b_point_review_home", "房间词汇与方位介词复习：Where is ...? 看图找位置", 1, SUBJECT, G2, 270008),
    (270091, "peng_g2b_point_review_room", "房间物品与 There is／There are 复习：描述房间陈设", 2, SUBJECT, G2, 270008),
    (270092, "peng_g2b_point_review_week", "星期词汇与 What day is it today? 复习：星期排序与问答", 3, SUBJECT, G2, 270008),
    (270093, "peng_g2b_point_review_phonics_vowel", "元音字母组合 ee／ea／oo 拼读：see, tea, book 的发音", 4, SUBJECT, G2, 270008),
    (270094, "peng_g2b_point_review_week_plan", "作息与一周安排综合表达：I get up at seven on Monday.", 5, SUBJECT, G2, 270008),
)

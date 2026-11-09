"""人教版（PEP）小学英语五年级下册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G5 = 5
BOOK_ID = 1434

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语五年级下册",
    "peng_g5b",
    34,
    "人民教育出版社",
    SUBJECT,
    G5,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 My day
    (143401, "Unit 1 My day", "peng_g5b_u01", 1, BOOK_ID, None),
    (143402, "Part A", "peng_g5b_u01_a", 1, BOOK_ID, 143401),
    (143403, "Part B", "peng_g5b_u01_b", 2, BOOK_ID, 143401),
    (143404, "Part C", "peng_g5b_u01_c", 3, BOOK_ID, 143401),

    # Unit 2 My favourite season
    (143405, "Unit 2 My favourite season", "peng_g5b_u02", 2, BOOK_ID, None),
    (143406, "Part A", "peng_g5b_u02_a", 1, BOOK_ID, 143405),
    (143407, "Part B", "peng_g5b_u02_b", 2, BOOK_ID, 143405),
    (143408, "Part C", "peng_g5b_u02_c", 3, BOOK_ID, 143405),

    # Unit 3 My school calendar
    (143409, "Unit 3 My school calendar", "peng_g5b_u03", 3, BOOK_ID, None),
    (143410, "Part A", "peng_g5b_u03_a", 1, BOOK_ID, 143409),
    (143411, "Part B", "peng_g5b_u03_b", 2, BOOK_ID, 143409),
    (143412, "Part C", "peng_g5b_u03_c", 3, BOOK_ID, 143409),

    # Unit 4 When is the art show?
    (143413, "Unit 4 When is the art show?", "peng_g5b_u04", 4, BOOK_ID, None),
    (143414, "Part A", "peng_g5b_u04_a", 1, BOOK_ID, 143413),
    (143415, "Part B", "peng_g5b_u04_b", 2, BOOK_ID, 143413),
    (143416, "Part C", "peng_g5b_u04_c", 3, BOOK_ID, 143413),

    # Unit 5 Whose dog is it?
    (143417, "Unit 5 Whose dog is it?", "peng_g5b_u05", 5, BOOK_ID, None),
    (143418, "Part A", "peng_g5b_u05_a", 1, BOOK_ID, 143417),
    (143419, "Part B", "peng_g5b_u05_b", 2, BOOK_ID, 143417),
    (143420, "Part C", "peng_g5b_u05_c", 3, BOOK_ID, 143417),

    # Unit 6 Work quietly!
    (143421, "Unit 6 Work quietly!", "peng_g5b_u06", 6, BOOK_ID, None),
    (143422, "Part A", "peng_g5b_u06_a", 1, BOOK_ID, 143421),
    (143423, "Part B", "peng_g5b_u06_b", 2, BOOK_ID, 143421),
    (143424, "Part C", "peng_g5b_u06_c", 3, BOOK_ID, 143421),

    # Revision
    (143425, "Revision 1", "peng_g5b_rev1", 7, BOOK_ID, None),
    (143426, "Revision 2", "peng_g5b_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / parent_id
# 276001-276008 为册域层，276010-276060 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (276001, "peng_g5b_domain_u01", "小学英语五下·Unit 1 My day", 1, SUBJECT, None),
    (276002, "peng_g5b_domain_u02", "小学英语五下·Unit 2 My favourite season", 2, SUBJECT, None),
    (276003, "peng_g5b_domain_u03", "小学英语五下·Unit 3 My school calendar", 3, SUBJECT, None),
    (276004, "peng_g5b_domain_u04", "小学英语五下·Unit 4 When is the art show?", 4, SUBJECT, None),
    (276005, "peng_g5b_domain_u05", "小学英语五下·Unit 5 Whose dog is it?", 5, SUBJECT, None),
    (276006, "peng_g5b_domain_u06", "小学英语五下·Unit 6 Work quietly!", 6, SUBJECT, None),
    (276007, "peng_g5b_domain_rev1", "小学英语五下·Revision 1", 7, SUBJECT, None),
    (276008, "peng_g5b_domain_rev2", "小学英语五下·Revision 2", 8, SUBJECT, None),

    # Unit 1 My day
    (276010, "peng_g5b_point_routine_phrases", "日常作息短语 do morning exercises／eat breakfast／have ... class／play sports／eat dinner", 1, SUBJECT, 276001),
    (276011, "peng_g5b_point_when_do_you", "句型 When do you get up? 与 I get up at 6:30.：询问并回答作息时间", 2, SUBJECT, 276001),
    (276012, "peng_g5b_point_at_clock", "介词 at + 具体时刻 at 7 o'clock／at 6:30：时间点表达", 3, SUBJECT, 276001),
    (276013, "peng_g5b_point_frequency_routine", "频度副词 always／usually／often／sometimes／never 的语义强弱与句中位置", 4, SUBJECT, 276001),
    (276014, "peng_g5b_point_weekend_routine", "句型 What do you do on the weekend? 与 I often play football with my friends.", 5, SUBJECT, 276001),
    (276015, "peng_g5b_point_present_first_second", "一般现在时第一、二人称及复数主语用动词原形：I eat breakfast at 7.", 6, SUBJECT, 276001),
    (276016, "peng_g5b_point_present_third_routine", "第三人称单数 gets up／eats／plays／has：描述他人一天的作息", 7, SUBJECT, 276001),
    (276017, "peng_g5b_point_phonics_cl_pl", "语音 cl 读 /kl/、pl 读 /pl/：clean, clock, class, play, plate 的读音归类", 8, SUBJECT, 276001),

    # Unit 2 My favourite season
    (276018, "peng_g5b_point_season_weather_words", "季节词汇 spring／summer／autumn／winter 与天气词 warm／hot／cool／cold 搭配", 1, SUBJECT, 276002),
    (276019, "peng_g5b_point_which_season_best", "句型 Which season do you like best? 与 I like spring best.", 2, SUBJECT, 276002),
    (276020, "peng_g5b_point_why_because", "原因问答 Why do you like it? 与 Because I can go swimming.", 3, SUBJECT, 276002),
    (276021, "peng_g5b_point_season_activities", "季节活动短语 go swimming／pick apples／make a snowman／go on a picnic", 4, SUBJECT, 276002),
    (276022, "peng_g5b_point_weather_like", "句型 What's the weather like? 与 It's warm and sunny.：描述天气", 5, SUBJECT, 276002),
    (276023, "peng_g5b_point_in_season", "介词 in + 季节与月份：in spring／in summer／in May", 6, SUBJECT, 276002),
    (276024, "peng_g5b_point_phonics_br_gr", "语音 br 读 /br/、gr 读 /gr/：brown, bread, green, grapes 的读音归类", 7, SUBJECT, 276002),

    # Unit 3 My school calendar
    (276025, "peng_g5b_point_month_words", "月份词汇 January—December 认读、拼写与缩写 Jan.—Dec.", 1, SUBJECT, 276003),
    (276026, "peng_g5b_point_school_events", "校园活动词汇 sports meet／Easter party／school trip／English test／art show", 2, SUBJECT, 276003),
    (276027, "peng_g5b_point_when_is_month", "句型 When is the sports meet? 与 It's in April.：询问活动所在月份", 3, SUBJECT, 276003),
    (276028, "peng_g5b_point_in_month_on_date", "介词辨析 in + 月份／年份，on + 具体日期：in April 与 on April 5th", 4, SUBJECT, 276003),
    (276029, "peng_g5b_point_ordinal_1_12", "序数词 first—twelfth 的构成、缩写 1st—12th 与不规则变化", 5, SUBJECT, 276003),
    (276030, "peng_g5b_point_will_plan", "一般将来时 will 表活动安排：We will have an English test next week.", 6, SUBJECT, 276003),
    (276031, "peng_g5b_point_phonics_sh_ch", "语音 sh 读 /ʃ/、ch 读 /tʃ/：sheep, ship, chair, lunch 的读音归类", 7, SUBJECT, 276003),

    # Unit 4 When is the art show?
    (276032, "peng_g5b_point_ordinal_13_31", "序数词 thirteenth—thirty-first 的构成规则与整十数变化 twentieth／thirtieth", 1, SUBJECT, 276004),
    (276033, "peng_g5b_point_festival_dates", "节日日期表达 Christmas／New Year's Day／Children's Day／Mid-Autumn Festival", 2, SUBJECT, 276004),
    (276034, "peng_g5b_point_when_art_show", "句型 When is the art show? 与 It's on May 1st.：询问并回答具体日期", 3, SUBJECT, 276004),
    (276035, "peng_g5b_point_on_date_weekday", "介词 on 表具体日期与星期：on May 1st／on Monday morning", 4, SUBJECT, 276004),
    (276036, "peng_g5b_point_birthday_date", "句型 When is your birthday? 与 It's on October 1st.：谈生日日期", 5, SUBJECT, 276004),
    (276037, "peng_g5b_point_ordinal_reading", "序数词前加 the 与日期读法：May 1st 读作 May first，the first of May", 6, SUBJECT, 276004),
    (276038, "peng_g5b_point_phonics_th", "语音 th 的清音 /θ/ 与浊音 /ð/：three, birthday, this, that 的读音区分", 7, SUBJECT, 276004),

    # Unit 5 Whose dog is it?
    (276039, "peng_g5b_point_possessive_pronouns", "名词性物主代词 mine／yours／his／hers／ours／theirs 的认读与用法", 1, SUBJECT, 276005),
    (276040, "peng_g5b_point_whose_is_it", "句型 Whose dog is it? 与 It's mine.／It's Zhang Peng's.", 2, SUBJECT, 276005),
    (276041, "peng_g5b_point_noun_possessive_s", "名词所有格 's：Mike's book／the dog's tail；以 s 结尾加 '", 3, SUBJECT, 276005),
    (276042, "peng_g5b_point_my_vs_mine", "形容词性物主代词与名词性物主代词对比：my book = mine", 4, SUBJECT, 276005),
    (276043, "peng_g5b_point_present_continuous_form", "现在进行时构成 be + 动词-ing：He is playing with the dog.", 5, SUBJECT, 276005),
    (276044, "peng_g5b_point_ing_spelling", "现在分词拼写规则 running／swimming／having／making／writing", 6, SUBJECT, 276005),
    (276045, "peng_g5b_point_phonics_ng_nk", "语音 ng 读 /ŋ/、nk 读 /ŋk/：sing, long, think, pink 的读音归类", 7, SUBJECT, 276005),

    # Unit 6 Work quietly!
    (276046, "peng_g5b_point_public_rules", "公共场所规则短语 keep to the right／keep your desk clean／talk quietly／take turns", 1, SUBJECT, 276006),
    (276047, "peng_g5b_point_imperatives_rules", "祈使句表规则：Work quietly!／Keep your room clean.／Don't run in the hall.", 2, SUBJECT, 276006),
    (276048, "peng_g5b_point_what_are_they_doing", "句型 What are they doing? 与 They're eating lunch.：询问正在进行的行为", 3, SUBJECT, 276006),
    (276049, "peng_g5b_point_present_cont_question", "现在进行时一般疑问句 Are you ...? 与 Yes, I am.／No, I'm not.", 4, SUBJECT, 276006),
    (276050, "peng_g5b_point_present_cont_markers", "现在进行时标志词 now／look／listen 与句首提示语", 5, SUBJECT, 276006),
    (276051, "peng_g5b_point_present_cont_vs_simple", "现在进行时与一般现在时对比：He is reading now. 与 He reads every day.", 6, SUBJECT, 276006),
    (276052, "peng_g5b_point_phonics_wh_qu", "语音 wh 读 /w/ 或 /h/、qu 读 /kw/：what, where, queen, quiet 的读音", 7, SUBJECT, 276006),

    # Revision 1
    (276053, "peng_g5b_point_review_units_1_3_words", "Units 1—3 词汇复习：作息活动、季节天气、月份与校园活动分类认读", 1, SUBJECT, 276007),
    (276054, "peng_g5b_point_review_units_1_3_sentences", "句型复习 When do you ...?／Which season do you like best?／When is ...?", 2, SUBJECT, 276007),
    (276055, "peng_g5b_point_review_units_1_3_grammar", "语法复习：一般现在时三单、in／on／at 时间介词、序数词 1st—12th", 3, SUBJECT, 276007),
    (276056, "peng_g5b_point_review_units_1_3_dialogue", "情景对话：谈一天的作息、谈最喜欢的季节、谈学校活动日历", 4, SUBJECT, 276007),

    # Revision 2
    (276057, "peng_g5b_point_review_units_4_6_words", "Units 4—6 词汇复习：节日日期、物主代词、公共场所行为规则", 1, SUBJECT, 276008),
    (276058, "peng_g5b_point_review_units_4_6_sentences", "句型复习 When is the art show?／Whose ... is it?／What are they doing?", 2, SUBJECT, 276008),
    (276059, "peng_g5b_point_review_units_4_6_grammar", "语法复习：名词所有格、现在进行时构成与标志词、祈使句表规则", 3, SUBJECT, 276008),
    (276060, "peng_g5b_point_review_units_4_6_project", "综合任务：制作节日日历，并用现在进行时描述校园里的实时场景", 4, SUBJECT, 276008),
)

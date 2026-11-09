"""人教版（PEP）小学英语六年级上册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G6 = 6
BOOK_ID = 1435

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语六年级上册",
    "peng_g6a",
    35,
    "人民教育出版社",
    SUBJECT,
    G6,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 How can I get there?
    (143501, "Unit 1 How can I get there?", "peng_g6a_u01", 1, BOOK_ID, None),
    (143502, "Part A", "peng_g6a_u01_a", 1, BOOK_ID, 143501),
    (143503, "Part B", "peng_g6a_u01_b", 2, BOOK_ID, 143501),
    (143504, "Part C", "peng_g6a_u01_c", 3, BOOK_ID, 143501),

    # Unit 2 Ways to go to school
    (143505, "Unit 2 Ways to go to school", "peng_g6a_u02", 2, BOOK_ID, None),
    (143506, "Part A", "peng_g6a_u02_a", 1, BOOK_ID, 143505),
    (143507, "Part B", "peng_g6a_u02_b", 2, BOOK_ID, 143505),
    (143508, "Part C", "peng_g6a_u02_c", 3, BOOK_ID, 143505),

    # Unit 3 My weekend plan
    (143509, "Unit 3 My weekend plan", "peng_g6a_u03", 3, BOOK_ID, None),
    (143510, "Part A", "peng_g6a_u03_a", 1, BOOK_ID, 143509),
    (143511, "Part B", "peng_g6a_u03_b", 2, BOOK_ID, 143509),
    (143512, "Part C", "peng_g6a_u03_c", 3, BOOK_ID, 143509),

    # Unit 4 I have a pen pal
    (143513, "Unit 4 I have a pen pal", "peng_g6a_u04", 4, BOOK_ID, None),
    (143514, "Part A", "peng_g6a_u04_a", 1, BOOK_ID, 143513),
    (143515, "Part B", "peng_g6a_u04_b", 2, BOOK_ID, 143513),
    (143516, "Part C", "peng_g6a_u04_c", 3, BOOK_ID, 143513),

    # Unit 5 What does he do?
    (143517, "Unit 5 What does he do?", "peng_g6a_u05", 5, BOOK_ID, None),
    (143518, "Part A", "peng_g6a_u05_a", 1, BOOK_ID, 143517),
    (143519, "Part B", "peng_g6a_u05_b", 2, BOOK_ID, 143517),
    (143520, "Part C", "peng_g6a_u05_c", 3, BOOK_ID, 143517),

    # Unit 6 How do you feel?
    (143521, "Unit 6 How do you feel?", "peng_g6a_u06", 6, BOOK_ID, None),
    (143522, "Part A", "peng_g6a_u06_a", 1, BOOK_ID, 143521),
    (143523, "Part B", "peng_g6a_u06_b", 2, BOOK_ID, 143521),
    (143524, "Part C", "peng_g6a_u06_c", 3, BOOK_ID, 143521),

    # Revision
    (143525, "Revision 1", "peng_g6a_rev1", 7, BOOK_ID, None),
    (143526, "Revision 2", "peng_g6a_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / parent_id
# 277001-277008 为册域层，277010-277080 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (277001, "peng_g6a_domain_u01", "小学英语六上·Unit 1 How can I get there?", 1, SUBJECT, None),
    (277002, "peng_g6a_domain_u02", "小学英语六上·Unit 2 Ways to go to school", 2, SUBJECT, None),
    (277003, "peng_g6a_domain_u03", "小学英语六上·Unit 3 My weekend plan", 3, SUBJECT, None),
    (277004, "peng_g6a_domain_u04", "小学英语六上·Unit 4 I have a pen pal", 4, SUBJECT, None),
    (277005, "peng_g6a_domain_u05", "小学英语六上·Unit 5 What does he do?", 5, SUBJECT, None),
    (277006, "peng_g6a_domain_u06", "小学英语六上·Unit 6 How do you feel?", 6, SUBJECT, None),
    (277007, "peng_g6a_domain_rev1", "小学英语六上·Revision 1", 7, SUBJECT, None),
    (277008, "peng_g6a_domain_rev2", "小学英语六上·Revision 2", 8, SUBJECT, None),

    # Unit 1 How can I get there?
    (277010, "peng_g6a_point_place_words", "地点词汇 science museum／post office／bookstore／cinema／hospital／crossing／Italian restaurant 认读与分类", 1, SUBJECT, 277001),
    (277011, "peng_g6a_point_direction_phrases", "指路短语 turn left／turn right／go straight／at the first crossing／walk for five minutes", 2, SUBJECT, 277001),
    (277012, "peng_g6a_point_where_is", "句型 Where is the science museum? 与 It's next to the bookstore.／It's near the hospital.", 3, SUBJECT, 277001),
    (277013, "peng_g6a_point_location_prepositions", "方位介词 next to／near／behind／in front of／between ... and ... 的空间关系辨析", 4, SUBJECT, 277001),
    (277014, "peng_g6a_point_how_can_i_get", "句型 How can I get there? 与 Turn left at the bookstore.：问路与答路完整对话", 5, SUBJECT, 277001),
    (277015, "peng_g6a_point_is_there_near_here", "句型 Is there a cinema near here? 与 Yes, there is.／No, there isn't.：存在句询问", 6, SUBJECT, 277001),
    (277016, "peng_g6a_point_where_vs_how", "疑问词 where 问地点、how 问方式：Where is it? 与 How can I get there? 的区别", 7, SUBJECT, 277001),
    (277017, "peng_g6a_point_place_verb_collocation", "地点与动词搭配 see a film at the cinema／buy books at the bookstore／see a doctor at the hospital／send a letter at the post office", 8, SUBJECT, 277001),
    (277018, "peng_g6a_point_imperative_route", "指路祈使句 Go straight.／Turn right at the cinema.／Walk along this street.：动词原形开头", 9, SUBJECT, 277001),
    (277019, "peng_g6a_point_can_could_request", "情态动词 can／could 表请求：Can you tell me the way?／Could you help me, please?", 10, SUBJECT, 277001),

    # Unit 2 Ways to go to school
    (277020, "peng_g6a_point_transport_words", "交通方式词汇 by bus／by train／by subway／by ship／by plane／by taxi／by bike／on foot", 1, SUBJECT, 277002),
    (277021, "peng_g6a_point_by_plus_transport", "by + 交通工具（不加冠词）：by bus／by subway；on foot 为固定搭配，不用 by", 2, SUBJECT, 277002),
    (277022, "peng_g6a_point_how_do_you_come", "句型 How do you come to school? 与 Usually I come on foot.／Sometimes I come by bus.", 3, SUBJECT, 277002),
    (277023, "peng_g6a_point_frequency_transport", "频度副词 usually／often／sometimes／never 与出行方式的搭配表达", 4, SUBJECT, 277002),
    (277024, "peng_g6a_point_third_person_transport", "第三人称单数句型 How does he come to school? 与 He comes by bike.", 5, SUBJECT, 277002),
    (277025, "peng_g6a_point_traffic_lights", "交通灯规则 Stop and wait at a red light.／Slow down and stop at a yellow light.／Go at a green light.", 6, SUBJECT, 277002),
    (277026, "peng_g6a_point_must_traffic", "情态动词 must 表必须：We must pay attention to the traffic lights.／You must look left and right.", 7, SUBJECT, 277002),
    (277027, "peng_g6a_point_can_go_by_bus", "交通建议句型 How can I get to the park? 与 You can go by the No. 15 bus.", 8, SUBJECT, 277002),
    (277028, "peng_g6a_point_left_right_driving", "中外交通文化：In China, people drive on the right side. 与 In the UK, people drive on the left side.", 9, SUBJECT, 277002),

    # Unit 3 My weekend plan
    (277030, "peng_g6a_point_weekend_activity_words", "周末活动短语 visit my grandparents／see a film／take a trip／go to the supermarket／clean my room", 1, SUBJECT, 277003),
    (277031, "peng_g6a_point_what_are_you_going_to_do", "句型 What are you going to do? 与 I'm going to visit my grandparents.", 2, SUBJECT, 277003),
    (277032, "peng_g6a_point_be_going_to_structure", "一般将来时 be going to + 动词原形：am／is／are 随主语变化", 3, SUBJECT, 277003),
    (277033, "peng_g6a_point_where_are_you_going", "句型 Where are you going? 与 I'm going to the cinema.：询问计划目的地", 4, SUBJECT, 277003),
    (277034, "peng_g6a_point_when_are_you_going", "句型 When are you going? 与 Next week.／This evening.：询问计划时间", 5, SUBJECT, 277003),
    (277035, "peng_g6a_point_future_time_words", "将来时间状语 this morning／this afternoon／this evening／tonight／tomorrow／next week／next month", 6, SUBJECT, 277003),
    (277036, "peng_g6a_point_going_to_negative", "be going to 否定句 I'm not going to see a film.／He isn't going to take a trip.", 7, SUBJECT, 277003),
    (277037, "peng_g6a_point_going_to_question", "be going to 一般疑问句 Are you going to ...? 与 Yes, I am.／No, I'm not.", 8, SUBJECT, 277003),
    (277038, "peng_g6a_point_third_person_plan", "第三人称计划问答 What is he going to do? 与 He is going to play football.", 9, SUBJECT, 277003),
    (277039, "peng_g6a_point_plan_sequence", "计划顺序表达 first／then／next／finally 串联周末安排，形成连贯短文", 10, SUBJECT, 277003),

    # Unit 4 I have a pen pal
    (277040, "peng_g6a_point_hobby_words", "爱好词汇 dancing／singing／reading stories／playing football／doing kung fu／swimming", 1, SUBJECT, 277004),
    (277041, "peng_g6a_point_what_are_your_hobbies", "句型 What are your hobbies? 与 I like reading stories.／I also like singing.", 2, SUBJECT, 277004),
    (277042, "peng_g6a_point_like_doing", "动词 like + 动名词：like reading／like playing football／like doing kung fu", 3, SUBJECT, 277004),
    (277043, "peng_g6a_point_does_he_like", "句型 Does he like singing? 与 Yes, he does.／No, he doesn't.", 4, SUBJECT, 277004),
    (277044, "peng_g6a_point_pen_pal_intro", "笔友介绍 I have a pen pal in Australia. He lives in Sydney. He likes reading stories.", 5, SUBJECT, 277004),
    (277045, "peng_g6a_point_third_person_s_verbs", "第三人称单数动词变化 lives／likes／studies／goes／does／watches 的构成规则", 6, SUBJECT, 277004),
    (277046, "peng_g6a_point_where_does_he_live", "句型 Where does he live? 与 He lives in Sydney, Australia.：询问居住地", 7, SUBJECT, 277004),
    (277047, "peng_g6a_point_his_her_hobbies", "句型 What are his／her hobbies? 与 He likes playing football.／She likes dancing.", 8, SUBJECT, 277004),
    (277048, "peng_g6a_point_ing_form_spelling", "动名词拼写 dance→dancing／swim→swimming／read→reading／do→doing 的变化规律", 9, SUBJECT, 277004),
    (277049, "peng_g6a_point_pen_pal_poster", "制作笔友信息卡：姓名、国家、城市、爱好、上学方式五要素归类表达", 10, SUBJECT, 277004),

    # Unit 5 What does he do?
    (277050, "peng_g6a_point_job_words", "职业词汇 factory worker／postman／businessman／police officer／fisherman／scientist／pilot／coach", 1, SUBJECT, 277005),
    (277051, "peng_g6a_point_what_does_he_do", "句型 What does he do? 与 He is a businessman.：询问职业", 2, SUBJECT, 277005),
    (277052, "peng_g6a_point_what_do_you_do", "句型 What do you do? 与 I'm a student.：第一人称职业问答", 3, SUBJECT, 277005),
    (277053, "peng_g6a_point_where_does_he_work", "句型 Where does he work? 与 He works at sea.／He works in a factory.", 4, SUBJECT, 277005),
    (277054, "peng_g6a_point_job_workplace", "职业与工作地点搭配 scientist→university／postman→post office／factory worker→factory／fisherman→sea", 5, SUBJECT, 277005),
    (277055, "peng_g6a_point_job_third_person", "职业问答中的第三人称单数 works／teaches／studies／goes 的用法", 6, SUBJECT, 277005),
    (277056, "peng_g6a_point_how_does_he_go_to_work", "句型 How does he go to work? 与 He goes to work by bus.：职业与出行方式整合", 7, SUBJECT, 277005),
    (277057, "peng_g6a_point_job_word_formation", "职业名词构词 work→worker／teach→teacher／science→scientist／business→businessman", 8, SUBJECT, 277005),
    (277058, "peng_g6a_point_parents_jobs", "句型 What does your father／mother do? 与 He／She is a police officer.：谈论父母职业", 9, SUBJECT, 277005),
    (277059, "peng_g6a_point_dream_job", "理想职业表达 What do you want to be? 与 I want to be a scientist.：结合兴趣说明理由", 10, SUBJECT, 277005),

    # Unit 6 How do you feel?
    (277060, "peng_g6a_point_feeling_words", "情绪词汇 angry／afraid／sad／worried／happy 的认读、拼写与表情匹配", 1, SUBJECT, 277006),
    (277061, "peng_g6a_point_how_do_you_feel", "句型 How do you feel? 与 I feel happy.／I'm sad.：询问并表达情绪", 2, SUBJECT, 277006),
    (277062, "peng_g6a_point_whats_wrong", "句型 What's wrong? 与 I'm ill.／My leg hurts.：询问他人状况", 3, SUBJECT, 277006),
    (277063, "peng_g6a_point_should_advice", "情态动词 should 表建议：You should see a doctor.／You should wear warm clothes.", 4, SUBJECT, 277006),
    (277064, "peng_g6a_point_shouldnt_advice", "shouldn't 表劝阻：You shouldn't be angry.／You shouldn't go out at night.", 5, SUBJECT, 277006),
    (277065, "peng_g6a_point_comfort_phrases", "安慰用语 Don't be sad.／Don't worry.／Take a deep breath.／Count to ten.", 6, SUBJECT, 277006),
    (277066, "peng_g6a_point_why_feel_because", "情绪原因问答 Why are you sad? 与 Because I lost my book.：because 引导原因", 7, SUBJECT, 277006),
    (277067, "peng_g6a_point_show_care", "关心他人 Are you OK?／What's the matter?／You look tired.：语气与回应", 8, SUBJECT, 277006),
    (277068, "peng_g6a_point_advice_phrases", "建议短语 see a doctor／wear warm clothes／do more exercise／take a deep breath／count to ten", 9, SUBJECT, 277006),
    (277069, "peng_g6a_point_feel_look_adjective", "系动词 feel／look + 形容词：I feel happy.／You look sad.／It sounds good.", 10, SUBJECT, 277006),

    # Revision 1
    (277070, "peng_g6a_point_review_units_1_3_words", "Units 1—3 词汇复习：地点方位、交通方式、周末活动短语归类认读", 1, SUBJECT, 277007),
    (277071, "peng_g6a_point_review_units_1_3_sentences", "句型复习 Where is ...?／How can I get there?／How do you come to school?／What are you going to do?", 2, SUBJECT, 277007),
    (277072, "peng_g6a_point_review_units_1_3_grammar", "语法复习：方位介词、by + 交通工具、be going to 结构与将来时间状语", 3, SUBJECT, 277007),
    (277073, "peng_g6a_point_review_units_1_3_dialogue", "情景对话：为游客指路、调查同学上学方式、制订并陈述周末计划", 4, SUBJECT, 277007),

    # Revision 2
    (277074, "peng_g6a_point_review_units_4_6_words", "Units 4—6 词汇复习：爱好动名词、职业名词、情绪形容词分类认读", 1, SUBJECT, 277008),
    (277075, "peng_g6a_point_review_units_4_6_sentences", "句型复习 What are your hobbies?／What does he do?／How do you feel? 及相应答语", 2, SUBJECT, 277008),
    (277076, "peng_g6a_point_review_units_4_6_grammar", "语法复习：第三人称单数与 does 提问、like + 动名词、should 建议句", 3, SUBJECT, 277008),
    (277077, "peng_g6a_point_review_units_4_6_project", "综合任务：制作笔友介绍卡与职业调查表，并用 should 给出健康与情绪建议", 4, SUBJECT, 277008),
)

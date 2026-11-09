"""人教版（PEP）小学英语六年级下册：Unit 1—4 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G6 = 6
BOOK_ID = 1436

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语六年级下册",
    "peng_g6b",
    36,
    "人民教育出版社",
    SUBJECT,
    G6,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 How tall are you?
    (143601, "Unit 1 How tall are you?", "peng_g6b_u01", 1, BOOK_ID, None),
    (143602, "Part A", "peng_g6b_u01_a", 1, BOOK_ID, 143601),
    (143603, "Part B", "peng_g6b_u01_b", 2, BOOK_ID, 143601),
    (143604, "Part C", "peng_g6b_u01_c", 3, BOOK_ID, 143601),

    # Unit 2 Last weekend
    (143605, "Unit 2 Last weekend", "peng_g6b_u02", 2, BOOK_ID, None),
    (143606, "Part A", "peng_g6b_u02_a", 1, BOOK_ID, 143605),
    (143607, "Part B", "peng_g6b_u02_b", 2, BOOK_ID, 143605),
    (143608, "Part C", "peng_g6b_u02_c", 3, BOOK_ID, 143605),

    # Unit 3 Where did you go?
    (143609, "Unit 3 Where did you go?", "peng_g6b_u03", 3, BOOK_ID, None),
    (143610, "Part A", "peng_g6b_u03_a", 1, BOOK_ID, 143609),
    (143611, "Part B", "peng_g6b_u03_b", 2, BOOK_ID, 143609),
    (143612, "Part C", "peng_g6b_u03_c", 3, BOOK_ID, 143609),

    # Unit 4 Then and now
    (143613, "Unit 4 Then and now", "peng_g6b_u04", 4, BOOK_ID, None),
    (143614, "Part A", "peng_g6b_u04_a", 1, BOOK_ID, 143613),
    (143615, "Part B", "peng_g6b_u04_b", 2, BOOK_ID, 143613),
    (143616, "Part C", "peng_g6b_u04_c", 3, BOOK_ID, 143613),

    # Revision
    (143617, "Revision 1", "peng_g6b_rev1", 5, BOOK_ID, None),
    (143618, "Revision 2", "peng_g6b_rev2", 6, BOOK_ID, None),

    # 总复习
    (143619, "总复习", "peng_g6b_final", 7, BOOK_ID, None),
    (143620, "语音", "peng_g6b_final_phonics", 1, BOOK_ID, 143619),
    (143621, "词汇", "peng_g6b_final_words", 2, BOOK_ID, 143619),
    (143622, "句型", "peng_g6b_final_sentences", 3, BOOK_ID, 143619),
    (143623, "语篇", "peng_g6b_final_passage", 4, BOOK_ID, 143619),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 278001-278007 为册域层，278010-278091 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (278001, "peng_g6b_domain_u01", "小学英语六下·Unit 1 How tall are you?", 1, SUBJECT, G6, None),
    (278002, "peng_g6b_domain_u02", "小学英语六下·Unit 2 Last weekend", 2, SUBJECT, G6, None),
    (278003, "peng_g6b_domain_u03", "小学英语六下·Unit 3 Where did you go?", 3, SUBJECT, G6, None),
    (278004, "peng_g6b_domain_u04", "小学英语六下·Unit 4 Then and now", 4, SUBJECT, G6, None),
    (278005, "peng_g6b_domain_rev1", "小学英语六下·Revision 1", 5, SUBJECT, G6, None),
    (278006, "peng_g6b_domain_rev2", "小学英语六下·Revision 2", 6, SUBJECT, G6, None),
    (278007, "peng_g6b_domain_final", "小学英语六下·总复习", 7, SUBJECT, G6, None),

    # Unit 1 How tall are you?
    (278010, "peng_g6b_point_comparative_words", "比较级形容词 taller／shorter／older／younger／stronger／longer／bigger 的认读", 1, SUBJECT, G6, 278001),
    (278011, "peng_g6b_point_how_tall_are_you", "句型 How tall are you? 与 I'm 1.65 metres.：询问并回答身高", 2, SUBJECT, G6, 278001),
    (278012, "peng_g6b_point_how_heavy_are_you", "句型 How heavy are you? 与 I'm 48 kilograms.：询问并回答体重", 3, SUBJECT, G6, 278001),
    (278013, "peng_g6b_point_comparative_formation", "比较级构成规则：一般加 -er，以 e 结尾加 -r，重读闭音节双写末尾字母，辅音字母 + y 变 i 加 -er", 4, SUBJECT, G6, 278001),
    (278014, "peng_g6b_point_than_structure", "比较级 + than 结构：I'm taller than you.／My hair is longer than yours.", 5, SUBJECT, G6, 278001),
    (278015, "peng_g6b_point_how_tall_is_he", "第三人称询问 How tall is he?／How heavy is she? 与 He is 1.7 metres tall.", 6, SUBJECT, G6, 278001),
    (278016, "peng_g6b_point_measure_units", "长度与重量单位 metre／centimetre／kilogram 及小数读法 1.65 metres／48 kilograms", 7, SUBJECT, G6, 278001),
    (278017, "peng_g6b_point_comparative_question", "比较级一般疑问句 Are you taller than me? 与 Yes, I am.／No, I'm not.", 8, SUBJECT, G6, 278001),
    (278018, "peng_g6b_point_comparative_spelling", "比较级特殊拼写 big→bigger／thin→thinner／heavy→heavier／funny→funnier 的规律", 9, SUBJECT, G6, 278001),
    (278019, "peng_g6b_point_yours_mine_compare", "比较句中名词性物主代词 yours／mine：Your feet are bigger than mine.", 10, SUBJECT, G6, 278001),
    (278020, "peng_g6b_point_comparative_reading", "比较级句子的重音与语调：重读比较级形容词与 than 后的对比信息", 11, SUBJECT, G6, 278001),

    # Unit 2 Last weekend
    (278030, "peng_g6b_point_weekend_past_phrases", "周末活动过去式短语 washed my clothes／stayed at home／watched TV／cleaned my room／slept", 1, SUBJECT, G6, 278002),
    (278031, "peng_g6b_point_what_did_you_do", "句型 What did you do last weekend? 与 I washed my clothes.：询问并叙述周末活动", 2, SUBJECT, G6, 278002),
    (278032, "peng_g6b_point_past_simple_ed", "一般过去时构成：主语 + 动词过去式，表示过去发生的动作", 3, SUBJECT, G6, 278002),
    (278033, "peng_g6b_point_regular_past_spelling", "规则动词过去式拼写：直接加 -ed，以 e 结尾加 -d，辅音字母 + y 变 i 加 -ed，重读闭音节双写加 -ed", 4, SUBJECT, G6, 278002),
    (278034, "peng_g6b_point_irregular_past_verbs", "不规则动词过去式 went／saw／ate／had／did／read／slept 的认读与记忆", 5, SUBJECT, G6, 278002),
    (278035, "peng_g6b_point_past_time_words", "过去时间状语 last weekend／last night／yesterday／two days ago／last Monday", 6, SUBJECT, G6, 278002),
    (278036, "peng_g6b_point_did_you_question", "一般过去时一般疑问句 Did you ...? 与 Yes, I did.／No, I didn't.", 7, SUBJECT, G6, 278002),
    (278037, "peng_g6b_point_past_negative", "一般过去时否定句 didn't + 动词原形：I didn't watch TV last night.", 8, SUBJECT, G6, 278002),
    (278038, "peng_g6b_point_present_past_contrast", "一般现在时与一般过去时对比：He watches TV every day.／He watched TV yesterday.", 9, SUBJECT, G6, 278002),
    (278039, "peng_g6b_point_how_was_weekend", "句型 How was your weekend? 与 It was great.／It was OK.／It was not good.", 10, SUBJECT, G6, 278002),
    (278040, "peng_g6b_point_ed_pronunciation", "动词过去式 -ed 的三种读音 /t/／/d/／/ɪd/：watched／played／visited 的归类", 11, SUBJECT, G6, 278002),

    # Unit 3 Where did you go?
    (278050, "peng_g6b_point_trip_past_phrases", "旅行活动过去式短语 went camping／went fishing／rode a horse／took pictures／ate fresh food／bought gifts", 1, SUBJECT, G6, 278003),
    (278051, "peng_g6b_point_where_did_you_go", "句型 Where did you go? 与 I went to Xinjiang.：询问并回答旅行地点", 2, SUBJECT, G6, 278003),
    (278052, "peng_g6b_point_trip_irregular_verbs", "旅行主题不规则动词过去式 go→went／ride→rode／take→took／eat→ate／buy→bought", 3, SUBJECT, G6, 278003),
    (278053, "peng_g6b_point_how_did_you_go", "句型 How did you go there? 与 We went there by plane.：询问出行方式", 4, SUBJECT, G6, 278003),
    (278054, "peng_g6b_point_what_happened", "句型 What happened? 与 I fell off my bike and hurt my foot.：叙述意外事件", 5, SUBJECT, G6, 278003),
    (278055, "peng_g6b_point_wh_did_questions", "过去时特殊疑问句 What／Where／How／Who + did + 主语 + 动词原形", 6, SUBJECT, G6, 278003),
    (278056, "peng_g6b_point_trip_narration", "用一般过去时按时间顺序叙述旅行经历：first／then／after that／finally", 7, SUBJECT, G6, 278003),
    (278057, "peng_g6b_point_hurt_fell_usage", "hurt／fell／rode／took 等不规则动词的过去式形式与句中搭配", 8, SUBJECT, G6, 278003),
    (278058, "peng_g6b_point_trip_feelings", "旅行见闻与感受表达 It was beautiful.／We had a good time.／I was tired but happy.", 9, SUBJECT, G6, 278003),
    (278059, "peng_g6b_point_travel_diary", "旅行日记语篇结构：时间、地点、人物、活动、感受五要素", 10, SUBJECT, G6, 278003),

    # Unit 4 Then and now
    (278070, "peng_g6b_point_then_now_words", "今昔对比时间词 ago／before／then／now／nowadays 的语义与位置", 1, SUBJECT, G6, 278004),
    (278071, "peng_g6b_point_there_was_were", "There be 句型过去式 There was a small building.／There were many trees.", 2, SUBJECT, G6, 278004),
    (278072, "peng_g6b_point_there_was_no", "There was no ...／There were no ... 否定式：There was no library in my school.", 3, SUBJECT, G6, 278004),
    (278073, "peng_g6b_point_before_now_compare", "过去与现在对比句型 Before, I was quiet. Now, I'm very active.", 4, SUBJECT, G6, 278004),
    (278074, "peng_g6b_point_past_present_compare", "一般过去时与一般现在时对比：描述过去状态与现在状态的变化", 5, SUBJECT, G6, 278004),
    (278075, "peng_g6b_point_was_were_adjective", "was／were + 形容词描述过去状态：I was short.／The desks were old.", 6, SUBJECT, G6, 278004),
    (278076, "peng_g6b_point_place_change", "学校与城市变化描述 There was only one small building. Now there are many tall buildings.", 7, SUBJECT, G6, 278004),
    (278077, "peng_g6b_point_ago_usage", "ago 的用法 two years ago／many years ago：时间段 + ago 表过去", 8, SUBJECT, G6, 278004),
    (278078, "peng_g6b_point_could_couldnt", "could／couldn't 表过去能力：I couldn't ride a bike before. Now I can.", 9, SUBJECT, G6, 278004),
    (278079, "peng_g6b_point_then_now_writing", "Then and now 主题短文写作：用过去与现在两组句子对照描述变化", 10, SUBJECT, G6, 278004),

    # Revision 1
    (278080, "peng_g6b_point_review_units_1_2_words", "Units 1—2 词汇复习：比较级形容词、身高体重单位、周末活动过去式短语", 1, SUBJECT, G6, 278005),
    (278081, "peng_g6b_point_review_units_1_2_sentences", "句型复习 How tall are you?／How heavy are you?／What did you do last weekend?", 2, SUBJECT, G6, 278005),
    (278082, "peng_g6b_point_review_units_1_2_grammar", "语法复习：比较级构成与 than 结构、一般过去时规则动词与 did 提问", 3, SUBJECT, G6, 278005),
    (278083, "peng_g6b_point_review_units_1_2_dialogue", "情景对话：比较身高体重、谈论并转述上周末的活动", 4, SUBJECT, G6, 278005),

    # Revision 2
    (278084, "peng_g6b_point_review_units_3_4_words", "Units 3—4 词汇复习：旅行活动过去式短语、今昔对比词汇与时间状语", 1, SUBJECT, G6, 278006),
    (278085, "peng_g6b_point_review_units_3_4_sentences", "句型复习 Where did you go?／How did you go there?／There was／There were", 2, SUBJECT, G6, 278006),
    (278086, "peng_g6b_point_review_units_3_4_grammar", "语法复习：不规则动词过去式、过去时与现在时对比、There be 过去式", 3, SUBJECT, G6, 278006),
    (278087, "peng_g6b_point_review_units_3_4_project", "综合任务：写旅行日记与今昔对比短文，并用 could 描述过去能力", 4, SUBJECT, G6, 278006),

    # 总复习
    (278088, "peng_g6b_point_final_phonics", "语音复习：常见字母组合发音、-ed 结尾三种读音、比较级与过去时句子重音语调", 1, SUBJECT, G6, 278007),
    (278089, "peng_g6b_point_final_vocabulary", "词汇复习：小学核心词汇按比较、活动、旅行、变化四大主题归类", 2, SUBJECT, G6, 278007),
    (278090, "peng_g6b_point_final_sentences", "句型复习：比较级问答、过去时特殊疑问句与 There be 过去式", 3, SUBJECT, G6, 278007),
    (278091, "peng_g6b_point_final_passage", "语篇复习：小学毕业英语短文结构与衔接词，完成读写综合任务", 4, SUBJECT, G6, 278007),
)

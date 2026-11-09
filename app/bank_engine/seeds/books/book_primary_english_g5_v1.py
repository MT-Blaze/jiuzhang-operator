"""人教版（PEP）小学英语五年级上册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G5 = 5
BOOK_ID = 1433

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语五年级上册",
    "peng_g5a",
    33,
    "人民教育出版社",
    SUBJECT,
    G5,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 What's he like?
    (143301, "Unit 1 What's he like?", "peng_g5a_u01", 1, BOOK_ID, None),
    (143302, "Part A", "peng_g5a_u01_a", 1, BOOK_ID, 143301),
    (143303, "Part B", "peng_g5a_u01_b", 2, BOOK_ID, 143301),
    (143304, "Part C", "peng_g5a_u01_c", 3, BOOK_ID, 143301),

    # Unit 2 My week
    (143305, "Unit 2 My week", "peng_g5a_u02", 2, BOOK_ID, None),
    (143306, "Part A", "peng_g5a_u02_a", 1, BOOK_ID, 143305),
    (143307, "Part B", "peng_g5a_u02_b", 2, BOOK_ID, 143305),
    (143308, "Part C", "peng_g5a_u02_c", 3, BOOK_ID, 143305),

    # Unit 3 What would you like?
    (143309, "Unit 3 What would you like?", "peng_g5a_u03", 3, BOOK_ID, None),
    (143310, "Part A", "peng_g5a_u03_a", 1, BOOK_ID, 143309),
    (143311, "Part B", "peng_g5a_u03_b", 2, BOOK_ID, 143309),
    (143312, "Part C", "peng_g5a_u03_c", 3, BOOK_ID, 143309),

    # Unit 4 What can you do?
    (143313, "Unit 4 What can you do?", "peng_g5a_u04", 4, BOOK_ID, None),
    (143314, "Part A", "peng_g5a_u04_a", 1, BOOK_ID, 143313),
    (143315, "Part B", "peng_g5a_u04_b", 2, BOOK_ID, 143313),
    (143316, "Part C", "peng_g5a_u04_c", 3, BOOK_ID, 143313),

    # Unit 5 There is a big bed
    (143317, "Unit 5 There is a big bed", "peng_g5a_u05", 5, BOOK_ID, None),
    (143318, "Part A", "peng_g5a_u05_a", 1, BOOK_ID, 143317),
    (143319, "Part B", "peng_g5a_u05_b", 2, BOOK_ID, 143317),
    (143320, "Part C", "peng_g5a_u05_c", 3, BOOK_ID, 143317),

    # Unit 6 In a nature park
    (143321, "Unit 6 In a nature park", "peng_g5a_u06", 6, BOOK_ID, None),
    (143322, "Part A", "peng_g5a_u06_a", 1, BOOK_ID, 143321),
    (143323, "Part B", "peng_g5a_u06_b", 2, BOOK_ID, 143321),
    (143324, "Part C", "peng_g5a_u06_c", 3, BOOK_ID, 143321),

    # Revision
    (143325, "Revision 1", "peng_g5a_rev1", 7, BOOK_ID, None),
    (143326, "Revision 2", "peng_g5a_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / parent_id
# 275001-275008 为册域层，275010-275091 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (275001, "peng_g5a_domain_u01", "小学英语五上·Unit 1 What's he like?", 1, SUBJECT, None),
    (275002, "peng_g5a_domain_u02", "小学英语五上·Unit 2 My week", 2, SUBJECT, None),
    (275003, "peng_g5a_domain_u03", "小学英语五上·Unit 3 What would you like?", 3, SUBJECT, None),
    (275004, "peng_g5a_domain_u04", "小学英语五上·Unit 4 What can you do?", 4, SUBJECT, None),
    (275005, "peng_g5a_domain_u05", "小学英语五上·Unit 5 There is a big bed", 5, SUBJECT, None),
    (275006, "peng_g5a_domain_u06", "小学英语五上·Unit 6 In a nature park", 6, SUBJECT, None),
    (275007, "peng_g5a_domain_rev1", "小学英语五上·Revision 1", 7, SUBJECT, None),
    (275008, "peng_g5a_domain_rev2", "小学英语五上·Revision 2", 8, SUBJECT, None),

    # Unit 1 What's he like?
    (275010, "peng_g5a_point_personality_words", "性格与品质词汇 old／young／funny／kind／strict／polite／hard-working／helpful／clever／shy：认读并分类", 1, SUBJECT, 275001),
    (275011, "peng_g5a_point_who_is_teacher", "句型 Who's your music teacher? 与 Mr Jones.／Miss White.：询问任课教师", 2, SUBJECT, 275001),
    (275012, "peng_g5a_point_what_is_he_like", "句型 What's he like?／What's she like? 与 He's strict.／She's kind.：询问并描述性格", 3, SUBJECT, 275001),
    (275013, "peng_g5a_point_is_he_young", "一般疑问句 Is he young?／Is she funny? 与 Yes, he is.／No, he isn't.", 4, SUBJECT, 275001),
    (275014, "peng_g5a_point_be_person_agreement", "be 动词与人称搭配 I am ...／He is ...／They are ...：am／is／are 的选择", 5, SUBJECT, 275001),
    (275015, "peng_g5a_point_and_but_adjectives", "形容词并列与转折 tall and strong／short but strong：and 表并列，but 表转折", 6, SUBJECT, 275001),
    (275016, "peng_g5a_point_job_words", "身份职业词汇 head teacher／principal／university student／robot：认读并匹配人物", 7, SUBJECT, 275001),
    (275017, "peng_g5a_point_appearance_words", "外貌描述 tall／short／strong／thin／long hair／short hair：He is tall.／She has long hair.", 8, SUBJECT, 275001),
    (275018, "peng_g5a_point_be_negative_person", "be 动词否定 He isn't strict.／She isn't shy.：isn't = is not", 9, SUBJECT, 275001),
    (275019, "peng_g5a_point_introduce_teacher", "介绍他人 He is our maths teacher.／She is very kind.：our 与形容词性物主代词", 10, SUBJECT, 275001),
    (275020, "peng_g5a_point_old_young_contrast", "反义形容词配对 old—young／tall—short／strict—kind／hard-working—lazy：对比记忆", 11, SUBJECT, 275001),
    (275021, "peng_g5a_point_phonics_ee_ea", "语音 ee／ea 发 /iː/：see, meet, tea, read, teacher 的读音归类", 12, SUBJECT, 275001),

    # Unit 2 My week
    (275022, "peng_g5a_point_weekday_words", "星期词汇 Monday／Tuesday／Wednesday／Thursday／Friday／Saturday／Sunday：认读与拼写", 1, SUBJECT, 275002),
    (275023, "peng_g5a_point_what_have_on", "句型 What do you have on Mondays? 与 I have Chinese, maths and English.", 2, SUBJECT, 275002),
    (275024, "peng_g5a_point_subject_words", "课程词汇 Chinese／maths／English／music／art／PE／science／computer class：认读并搭配星期", 3, SUBJECT, 275002),
    (275025, "peng_g5a_point_on_weekdays", "介词 on + 星期：on Monday 指某一天，on Mondays 指每周一（复数表习惯）", 4, SUBJECT, 275002),
    (275026, "peng_g5a_point_what_do_weekend", "句型 What do you do on the weekend? 与 I often play football.", 5, SUBJECT, 275002),
    (275027, "peng_g5a_point_weekend_phrases", "周末活动短语 wash my clothes／watch TV／do homework／read books／play sports／clean my room", 6, SUBJECT, 275002),
    (275028, "peng_g5a_point_frequency_adverbs", "频度副词 always／usually／often／sometimes／never：位于实义动词前、be 动词后", 7, SUBJECT, 275002),
    (275029, "peng_g5a_point_present_i_third", "一般现在时人称对比 I have ...／He has ...；I play ...／She plays ...：三单变化", 8, SUBJECT, 275002),
    (275030, "peng_g5a_point_do_you_often", "句型 Do you often read books? 与 Yes, I do.／No, I don't.", 9, SUBJECT, 275002),
    (275031, "peng_g5a_point_time_prepositions", "时间介词 on／in／at：on Monday／in the morning／at eight o'clock", 10, SUBJECT, 275002),
    (275032, "peng_g5a_point_has_third_person", "第三人称单数动词变化 has／does／goes／watches：描述他人一周安排", 11, SUBJECT, 275002),
    (275033, "peng_g5a_point_phonics_day_ur", "语音 -day 读 /deɪ/（Monday, Tuesday）；Thursday 中 ur 读 /ɜː/", 12, SUBJECT, 275002),

    # Unit 3 What would you like?
    (275034, "peng_g5a_point_food_words", "食物词汇 sandwich／salad／hamburger／ice cream／noodles／rice／bread：认读并分类", 1, SUBJECT, 275003),
    (275035, "peng_g5a_point_drink_words", "饮品词汇 tea／water／juice／milk／coffee：认读并区分冷热饮", 2, SUBJECT, 275003),
    (275036, "peng_g5a_point_what_like_to_eat", "句型 What would you like to eat? 与 I'd like a sandwich, please.", 3, SUBJECT, 275003),
    (275037, "peng_g5a_point_what_like_to_drink", "句型 What would you like to drink? 与 I'd like some tea.", 4, SUBJECT, 275003),
    (275038, "peng_g5a_point_would_like_short", "I'd like = I would like 的缩略形式与 would like 后接名词或 to do", 5, SUBJECT, 275003),
    (275039, "peng_g5a_point_countable_food", "可数与不可数：hamburger／sandwich／egg 可数；milk／juice／bread／rice 不可数", 6, SUBJECT, 275003),
    (275040, "peng_g5a_point_food_quantifiers", "量词表达 a glass of water／a cup of tea／a bottle of juice／a bowl of noodles", 7, SUBJECT, 275003),
    (275041, "peng_g5a_point_favourite_food", "句型 What's your favourite food? 与 My favourite food is ...／I love ...", 8, SUBJECT, 275003),
    (275042, "peng_g5a_point_taste_adjectives", "味道形容词 sweet／sour／hot／fresh／healthy／delicious：描述食物特征", 9, SUBJECT, 275003),
    (275043, "peng_g5a_point_would_like_vs_like", "would like 与 like 的区别：would like 表具体想要，like 表喜好", 10, SUBJECT, 275003),
    (275044, "peng_g5a_point_ordering_polite", "点餐礼貌用语 Can I help you?／Here you are.／Thank you.／Anything else?", 11, SUBJECT, 275003),
    (275045, "peng_g5a_point_phonics_oo", "语音 oo 发 /uː/（food, noodles, spoon）与 /ʊ/（book, look）：读音区分", 12, SUBJECT, 275003),

    # Unit 4 What can you do?
    (275046, "peng_g5a_point_talent_phrases", "才艺短语 sing English songs／dance／do kung fu／play the pipa／cook／draw cartoons", 1, SUBJECT, 275004),
    (275047, "peng_g5a_point_what_can_you_do", "句型 What can you do? 与 I can sing English songs.", 2, SUBJECT, 275004),
    (275048, "peng_g5a_point_can_you", "一般疑问句 Can you dance? 与 Yes, I can.／No, I can't.", 3, SUBJECT, 275004),
    (275049, "peng_g5a_point_can_bare_verb", "情态动词 can 后接动词原形，无人称与数的变化：He can swim.／They can swim.", 4, SUBJECT, 275004),
    (275050, "peng_g5a_point_cant_negative", "can 的否定 can't = cannot：I can't play the pipa.", 5, SUBJECT, 275004),
    (275051, "peng_g5a_point_play_instrument_ball", "play 的搭配：play the pipa／play the piano 加 the；play football／play basketball 不加 the", 6, SUBJECT, 275004),
    (275052, "peng_g5a_point_party_words", "活动词汇 party／English party／next Tuesday／show：认读并理解通知信息", 7, SUBJECT, 275004),
    (275053, "peng_g5a_point_we_will_party", "邀请与应答 We'll have an English party next Tuesday. 与 Great!", 8, SUBJECT, 275004),
    (275054, "peng_g5a_point_do_play_go", "活动动词搭配 do kung fu／play sports／go swimming：do／play／go 的选择", 9, SUBJECT, 275004),
    (275055, "peng_g5a_point_will_future", "一般将来时 will 表计划 We will have a party.／She will sing at the party.", 10, SUBJECT, 275004),
    (275056, "peng_g5a_point_show_talent", "介绍才艺 I can ... but I can't ...：用 but 对比能力，完成自我介绍", 11, SUBJECT, 275004),
    (275057, "peng_g5a_point_phonics_ow", "语音 ow 发 /əʊ/：show, know, snow, window 的读音归类", 12, SUBJECT, 275004),

    # Unit 5 There is a big bed
    (275058, "peng_g5a_point_room_object_words", "房间物品词汇 bed／desk／chair／clock／photo／bike／plant／water bottle：认读并指认", 1, SUBJECT, 275005),
    (275059, "peng_g5a_point_there_is_are_room", "There is a big bed.／There are two chairs.：be 动词随其后名词单复数变化", 2, SUBJECT, 275005),
    (275060, "peng_g5a_point_position_prepositions", "方位介词 in front of／beside／between／behind／above：描述物品位置", 3, SUBJECT, 275005),
    (275061, "peng_g5a_point_where_is_it", "句型 Where is the ball? 与 It's under the desk.／They're on the bed.", 4, SUBJECT, 275005),
    (275062, "peng_g5a_point_there_negative", "There be 否定 There isn't a clock.／There aren't any pictures.", 5, SUBJECT, 275005),
    (275063, "peng_g5a_point_is_there_question", "句型 Is there a ...? 与 Yes, there is.／No, there isn't.", 6, SUBJECT, 275005),
    (275064, "peng_g5a_point_there_quantity", "数量表达 many／a lot of／lots of 与可数名词复数：There are lots of books.", 7, SUBJECT, 275005),
    (275065, "peng_g5a_point_describe_room", "描述房间 My room is small but clean.／There is a photo on the wall.", 8, SUBJECT, 275005),
    (275066, "peng_g5a_point_there_be_vs_have", "There be 与 have／has 的区别：There is a bed in my room.／I have a bed.", 9, SUBJECT, 275005),
    (275067, "peng_g5a_point_preposition_contrast", "介词辨析 in／on／under／near／behind：in the box 与 on the box", 10, SUBJECT, 275005),
    (275068, "peng_g5a_point_room_pronouns", "物品指代 it／they：单数用 it，复数用 they 回答 Where 问句", 11, SUBJECT, 275005),
    (275069, "peng_g5a_point_phonics_e_short", "语音元音字母 e 的短音 /e/：bed, desk, red, pen 的读音归类", 12, SUBJECT, 275005),

    # Unit 6 In a nature park
    (275070, "peng_g5a_point_nature_words", "自然景物词汇 forest／river／lake／mountain／hill／tree／bridge／building／village／house", 1, SUBJECT, 275006),
    (275071, "peng_g5a_point_is_there_park", "句型 Is there a river in the park? 与 Yes, there is.／No, there isn't.", 2, SUBJECT, 275006),
    (275072, "peng_g5a_point_are_there_park", "句型 Are there any lakes? 与 Yes, there are.／No, there aren't.", 3, SUBJECT, 275006),
    (275073, "peng_g5a_point_there_be_park", "There is／There are 描述自然公园：There are many trees in the forest.", 4, SUBJECT, 275006),
    (275074, "peng_g5a_point_some_any", "some 与 any 的用法：肯定句用 some，否定句与疑问句用 any", 5, SUBJECT, 275006),
    (275075, "peng_g5a_point_nature_prepositions", "方位介词 above／beside／in front of／between：描述景物相对位置", 6, SUBJECT, 275006),
    (275076, "peng_g5a_point_what_in_park", "句型 What's in the park? 与 There is a lake and there are many trees.", 7, SUBJECT, 275006),
    (275077, "peng_g5a_point_nature_adjectives", "景物形容词 high／long／big／small／quiet／beautiful：The mountain is high.", 8, SUBJECT, 275006),
    (275078, "peng_g5a_point_present_nature", "一般现在时描述自然景观 The river is long.／Many birds live in the forest.", 9, SUBJECT, 275006),
    (275079, "peng_g5a_point_city_village", "城市与乡村对比 city／village／building／house：There are tall buildings in the city.", 10, SUBJECT, 275006),
    (275080, "peng_g5a_point_protect_nature", "保护自然表达 We should keep the park clean.／Don't litter in the park.", 11, SUBJECT, 275006),
    (275081, "peng_g5a_point_phonics_ar", "语音 ar 发 /ɑː/：park, farm, car, garden 的读音归类", 12, SUBJECT, 275006),

    # Revision 1
    (275082, "peng_g5a_point_review_units_1_3_words", "Units 1—3 词汇复习：性格外貌、星期课程、食物饮品分类认读", 1, SUBJECT, 275007),
    (275083, "peng_g5a_point_review_units_1_3_sentences", "句型复习 What's he like?／What do you have on Mondays?／What would you like?", 2, SUBJECT, 275007),
    (275084, "peng_g5a_point_review_units_1_3_grammar", "语法复习：be 动词与人称、一般现在时三单、可数与不可数名词", 3, SUBJECT, 275007),
    (275085, "peng_g5a_point_review_units_1_3_dialogue", "情景对话：介绍老师、谈论课程表、在餐厅点餐", 4, SUBJECT, 275007),
    (275086, "peng_g5a_point_review_units_1_3_phonics", "语音复习：ee／ea、-day／ur、oo 等字母组合发音归类", 5, SUBJECT, 275007),

    # Revision 2
    (275087, "peng_g5a_point_review_units_4_6_words", "Units 4—6 词汇复习：才艺活动、房间物品、自然景物分类认读", 1, SUBJECT, 275008),
    (275088, "peng_g5a_point_review_units_4_6_sentences", "句型复习 What can you do?／There is a ...／Is there a ...?", 2, SUBJECT, 275008),
    (275089, "peng_g5a_point_review_units_4_6_grammar", "语法复习：情态动词 can、There be 句型、方位介词与 some／any", 3, SUBJECT, 275008),
    (275090, "peng_g5a_point_review_units_4_6_dialogue", "情景对话：介绍才艺、描述房间、介绍自然公园", 4, SUBJECT, 275008),
    (275091, "peng_g5a_point_review_units_4_6_project", "项目展示：制作“我的房间／自然公园”图文介绍并用 There be 口头描述", 5, SUBJECT, 275008),
)

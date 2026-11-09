"""人教版（PEP 2024）小学英语四年级下册：Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G4 = 4
BOOK_ID = 1432

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语四年级下册",
    "peng_g4b",
    32,
    "人民教育出版社",
    SUBJECT,
    G4,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Unit 1 Class rules
    (143201, "Unit 1 Class rules", "peng_g4b_u01", 1, BOOK_ID, None),
    (143202, "Part A", "peng_g4b_u01_a", 1, BOOK_ID, 143201),
    (143203, "Part B", "peng_g4b_u01_b", 2, BOOK_ID, 143201),
    (143204, "Part C", "peng_g4b_u01_c", 3, BOOK_ID, 143201),

    # Unit 2 Family rules
    (143205, "Unit 2 Family rules", "peng_g4b_u02", 2, BOOK_ID, None),
    (143206, "Part A", "peng_g4b_u02_a", 1, BOOK_ID, 143205),
    (143207, "Part B", "peng_g4b_u02_b", 2, BOOK_ID, 143205),
    (143208, "Part C", "peng_g4b_u02_c", 3, BOOK_ID, 143205),

    # Unit 3 Time for school
    (143209, "Unit 3 Time for school", "peng_g4b_u03", 3, BOOK_ID, None),
    (143210, "Part A", "peng_g4b_u03_a", 1, BOOK_ID, 143209),
    (143211, "Part B", "peng_g4b_u03_b", 2, BOOK_ID, 143209),
    (143212, "Part C", "peng_g4b_u03_c", 3, BOOK_ID, 143209),

    # Unit 4 Going shopping
    (143213, "Unit 4 Going shopping", "peng_g4b_u04", 4, BOOK_ID, None),
    (143214, "Part A", "peng_g4b_u04_a", 1, BOOK_ID, 143213),
    (143215, "Part B", "peng_g4b_u04_b", 2, BOOK_ID, 143213),
    (143216, "Part C", "peng_g4b_u04_c", 3, BOOK_ID, 143213),

    # Unit 5 Farms and us
    (143217, "Unit 5 Farms and us", "peng_g4b_u05", 5, BOOK_ID, None),
    (143218, "Part A", "peng_g4b_u05_a", 1, BOOK_ID, 143217),
    (143219, "Part B", "peng_g4b_u05_b", 2, BOOK_ID, 143217),
    (143220, "Part C", "peng_g4b_u05_c", 3, BOOK_ID, 143217),

    # Unit 6 From farm to table
    (143221, "Unit 6 From farm to table", "peng_g4b_u06", 6, BOOK_ID, None),
    (143222, "Part A", "peng_g4b_u06_a", 1, BOOK_ID, 143221),
    (143223, "Part B", "peng_g4b_u06_b", 2, BOOK_ID, 143221),
    (143224, "Part C", "peng_g4b_u06_c", 3, BOOK_ID, 143221),

    # Revision
    (143225, "Revision 1", "peng_g4b_rev1", 7, BOOK_ID, None),
    (143226, "Revision 2", "peng_g4b_rev2", 8, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / parent_id
# 274001-274008 为册域层，274010-274091 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (274001, "peng_g4b_domain_u01", "小学英语四下·Unit 1 Class rules", 1, SUBJECT, None),
    (274002, "peng_g4b_domain_u02", "小学英语四下·Unit 2 Family rules", 2, SUBJECT, None),
    (274003, "peng_g4b_domain_u03", "小学英语四下·Unit 3 Time for school", 3, SUBJECT, None),
    (274004, "peng_g4b_domain_u04", "小学英语四下·Unit 4 Going shopping", 4, SUBJECT, None),
    (274005, "peng_g4b_domain_u05", "小学英语四下·Unit 5 Farms and us", 5, SUBJECT, None),
    (274006, "peng_g4b_domain_u06", "小学英语四下·Unit 6 From farm to table", 6, SUBJECT, None),
    (274007, "peng_g4b_domain_rev1", "小学英语四下·Revision 1", 7, SUBJECT, None),
    (274008, "peng_g4b_domain_rev2", "小学英语四下·Revision 2", 8, SUBJECT, None),

    # Unit 1 Class rules
    (274010, "peng_g4b_point_imperative_affirmative", "肯定祈使句 Listen carefully.／Look at the blackboard.／Open your books.：动词原形开头，省略主语 you", 1, SUBJECT, 274001),
    (274011, "peng_g4b_point_imperative_negative", "否定祈使句 Don't run in the classroom.／Don't talk in class.：Don't + 动词原形", 2, SUBJECT, 274001),
    (274012, "peng_g4b_point_class_rule_words", "课堂规则词汇 rule／listen／talk／run／shout／share／raise your hand：认读并分类", 3, SUBJECT, 274001),
    (274013, "peng_g4b_point_must_class_rules", "情态动词 must 表必须 We must follow the class rules.／We must listen to the teacher.", 4, SUBJECT, 274001),
    (274014, "peng_g4b_point_mustnt_class_rules", "情态动词 mustn't 表禁止 You mustn't eat in class.／We mustn't be late for school.", 5, SUBJECT, 274001),
    (274015, "peng_g4b_point_can_permission_class", "情态动词 can 表许可 Can I go to the toilet? 与 Yes, you can.／No, you can't.", 6, SUBJECT, 274001),
    (274016, "peng_g4b_point_may_i_request", "礼貌请求 May I come in?／May I ask a question?：may 比 can 更正式", 7, SUBJECT, 274001),
    (274017, "peng_g4b_point_lets_suggestion", "建议句型 Let's listen to the teacher.／Let's keep the classroom clean.：Let's 后接动词原形", 8, SUBJECT, 274001),
    (274018, "peng_g4b_point_please_polite", "礼貌用语 Please be quiet.／Please share your book.：please 位置与语气", 9, SUBJECT, 274001),
    (274019, "peng_g4b_point_class_plural_nouns", "规则名词复数 rules／hands／books／pens：一般加 -s，词尾读音 /s/ 或 /z/", 10, SUBJECT, 274001),
    (274020, "peng_g4b_point_class_prepositions", "课堂地点介词 in class／in the classroom／on the playground／at school", 11, SUBJECT, 274001),
    (274021, "peng_g4b_point_phonics_ay_ai", "字母组合 ay／ai 发 /eɪ/：play, day, say, rain 的读音归类", 12, SUBJECT, 274001),

    # Unit 2 Family rules
    (274022, "peng_g4b_point_family_rule_words", "家庭规则词汇 rule／help／tidy／share／homework／bedtime／chores：认读并搭配", 1, SUBJECT, 274002),
    (274023, "peng_g4b_point_must_family", "情态动词 must 表义务 You must do your homework first.／We must help our parents.", 2, SUBJECT, 274002),
    (274024, "peng_g4b_point_mustnt_family", "情态动词 mustn't 表禁止 You mustn't watch TV too late.／We mustn't play with fire.", 3, SUBJECT, 274002),
    (274025, "peng_g4b_point_what_family_rules", "句型 What are the family rules? 与 We must ...／We mustn't ...：询问并陈述家规", 4, SUBJECT, 274002),
    (274026, "peng_g4b_point_have_to_need", "have to 表客观需要 I have to go to bed at nine.／I have to walk the dog.", 5, SUBJECT, 274002),
    (274027, "peng_g4b_point_has_to_third", "第三人称 has to：He has to tidy his room.／She has to do her homework first.", 6, SUBJECT, 274002),
    (274028, "peng_g4b_point_frequency_family", "频度副词 always／usually／often／sometimes／never：位于实义动词前、be 动词后", 7, SUBJECT, 274002),
    (274029, "peng_g4b_point_chore_phrases", "家务短语 do the dishes／sweep the floor／take out the rubbish／make the bed／feed the cat", 8, SUBJECT, 274002),
    (274030, "peng_g4b_point_present_i_he", "一般现在时人称对比 I help my mum.／He helps his dad.：三单动词加 -s", 9, SUBJECT, 274002),
    (274031, "peng_g4b_point_could_please", "礼貌请求 Could you please ...? 与 Sure.／Sorry, I can't.：could 使语气更委婉", 10, SUBJECT, 274002),
    (274032, "peng_g4b_point_do_vs_must", "do 与 must 的分工：do 表日常习惯，must 表必须遵守的规则", 11, SUBJECT, 274002),
    (274033, "peng_g4b_point_phonics_ea", "字母组合 ea 发 /iː/ 或 /e/：eat, read 与 bread, head 的读音区分", 12, SUBJECT, 274002),

    # Unit 3 Time for school
    (274034, "peng_g4b_point_time_words", "时间词汇 o'clock／half past／a quarter past／a quarter to：认读并理解含义", 1, SUBJECT, 274003),
    (274035, "peng_g4b_point_oclock", "整点表达 It's seven o'clock.／It's eight o'clock.：o'clock 只用于整点", 2, SUBJECT, 274003),
    (274036, "peng_g4b_point_half_quarter", "半点与刻钟 It's half past six.／It's a quarter past seven.／It's a quarter to eight.", 3, SUBJECT, 274003),
    (274037, "peng_g4b_point_what_time_is_it", "句型 What time is it? 与 It's seven thirty.：询问并回答时间", 4, SUBJECT, 274003),
    (274038, "peng_g4b_point_what_time_do_you", "句型 What time do you get up? 与 I get up at six thirty.：at 后接具体时刻", 5, SUBJECT, 274003),
    (274039, "peng_g4b_point_time_for_noun", "It's time for + 名词：It's time for school.／It's time for lunch.／It's time for bed.", 6, SUBJECT, 274003),
    (274040, "peng_g4b_point_time_to_verb", "It's time to + 动词：It's time to go to school.／It's time to have lunch.", 7, SUBJECT, 274003),
    (274041, "peng_g4b_point_daily_routine_phrases", "作息短语 get up／wash my face／brush my teeth／have breakfast／go to school／go to bed", 8, SUBJECT, 274003),
    (274042, "peng_g4b_point_prep_at_in_on_time", "时间介词 at／in／on：at seven o'clock／in the morning／on Monday", 9, SUBJECT, 274003),
    (274043, "peng_g4b_point_routine_present", "一般现在时描述作息 I usually get up at six thirty.／He goes to school at seven.", 10, SUBJECT, 274003),
    (274044, "peng_g4b_point_frequency_routine", "频度副词在作息表达中的位置与含义 always／usually／often／sometimes／never", 11, SUBJECT, 274003),
    (274045, "peng_g4b_point_phonics_ir_ur", "字母组合 ir／ur 发 /ɜː/：bird, girl, nurse, turn 的读音归类", 12, SUBJECT, 274003),

    # Unit 4 Going shopping
    (274046, "peng_g4b_point_shop_words", "商店与商品词汇 shop／supermarket／mall／clothes／shoes／toy／book：认读并分类", 1, SUBJECT, 274004),
    (274047, "peng_g4b_point_can_i_help_you", "购物交际 Can I help you? 与 Yes, I'd like ...／I'm just looking.：应答与拒绝", 2, SUBJECT, 274004),
    (274048, "peng_g4b_point_how_much_is_it", "句型 How much is it? 与 It's twenty yuan.：询问并回答单件价格", 3, SUBJECT, 274004),
    (274049, "peng_g4b_point_how_much_are_they", "句型 How much are they? 与 They're fifty yuan.：be 动词随主语复数变化", 4, SUBJECT, 274004),
    (274050, "peng_g4b_point_price_reading", "价格表达 yuan／dollars／cents 与数字读法 twenty-five yuan／one hundred yuan", 5, SUBJECT, 274004),
    (274051, "peng_g4b_point_id_like", "I'd like ... 表达购买意愿 I'd like a pair of shoes.／I'd like two notebooks.", 6, SUBJECT, 274004),
    (274052, "peng_g4b_point_possessive_singular", "名词所有格单数加 's：the boy's bag／Lucy's dress／my mother's coat", 7, SUBJECT, 274004),
    (274053, "peng_g4b_point_possessive_plural", "名词所有格复数：以 s 结尾加 '（the students' books），不规则复数加 's（children's）", 8, SUBJECT, 274004),
    (274054, "peng_g4b_point_countable_uncountable", "可数与不可数名词：apples／books 可数，milk／juice／bread 不可数", 9, SUBJECT, 274004),
    (274055, "peng_g4b_point_quantifier_containers", "量词表达 a bottle of milk／a cup of tea／a piece of bread／two kilos of apples", 10, SUBJECT, 274004),
    (274056, "peng_g4b_point_shopping_polite", "购物礼貌用语 Here you are.／Thank you.／You're welcome.／How about this one?", 11, SUBJECT, 274004),
    (274057, "peng_g4b_point_phonics_ow", "字母组合 ow 发 /aʊ/ 或 /əʊ/：how, cow 与 show, know 的读音区分", 12, SUBJECT, 274004),

    # Unit 5 Farms and us
    (274058, "peng_g4b_point_farm_animal_words", "农场动物词汇 cow／horse／sheep／pig／duck／chicken／goat：认读并分类", 1, SUBJECT, 274005),
    (274059, "peng_g4b_point_animal_plural_irregular", "动物名词复数：cows／ducks 加 -s；sheep 单复数同形；goose—geese 不规则", 2, SUBJECT, 274005),
    (274060, "peng_g4b_point_crop_words", "农作物词汇 rice／wheat／corn／vegetable／tomato／potato／carrot：认读并分类", 3, SUBJECT, 274005),
    (274061, "peng_g4b_point_what_can_see_farm", "句型 What can you see on the farm? 与 I can see ...：can 后接动词原形", 4, SUBJECT, 274005),
    (274062, "peng_g4b_point_there_be_farm", "There be 句型 There is a cow on the farm.／There are many ducks.", 5, SUBJECT, 274005),
    (274063, "peng_g4b_point_these_those", "句型 What are these?／What are those? 与 They're ...：these 近指、those 远指", 6, SUBJECT, 274005),
    (274064, "peng_g4b_point_this_these_qa", "单复数问答 What's this? 与 It's a ...／What are these? 与 They're ...", 7, SUBJECT, 274005),
    (274065, "peng_g4b_point_farm_actions", "农场动作 feed the chickens／milk the cow／pick tomatoes／plant rice", 8, SUBJECT, 274005),
    (274066, "peng_g4b_point_farm_present", "一般现在时描述农场 Farmers grow rice.／My grandpa feeds the cows.", 9, SUBJECT, 274005),
    (274067, "peng_g4b_point_farm_frequency", "频度副词与农场活动 We often go to the farm on Sundays.／I sometimes help on the farm.", 10, SUBJECT, 274005),
    (274068, "peng_g4b_point_farm_prepositions", "农场地点介词 on the farm／in the field／near the river／behind the house", 11, SUBJECT, 274005),
    (274069, "peng_g4b_point_phonics_ar", "字母组合 ar 发 /ɑː/：farm, car, park, farmer 的读音归类", 12, SUBJECT, 274005),

    # Unit 6 From farm to table
    (274070, "peng_g4b_point_food_source_words", "食物来源词汇 farm／field／market／factory／kitchen／table：认读并排序", 1, SUBJECT, 274006),
    (274071, "peng_g4b_point_where_food_come", "句型 Where does food come from? 与 It comes from the farm.：does 提问，comes 三单", 2, SUBJECT, 274006),
    (274072, "peng_g4b_point_food_process_verbs", "加工动词 wash／cut／cook／bake／pack：认读并匹配食物处理步骤", 3, SUBJECT, 274006),
    (274073, "peng_g4b_point_made_into", "来源与加工表达 Milk is made into cheese.／Wheat is made into bread.", 4, SUBJECT, 274006),
    (274074, "peng_g4b_point_how_is_it_made", "句型 How is it made? 与 First ... Then ... Finally ...：询问并描述制作过程", 5, SUBJECT, 274006),
    (274075, "peng_g4b_point_sequence_words", "顺序副词 first／next／then／finally 在食物制作流程中的衔接作用", 6, SUBJECT, 274006),
    (274076, "peng_g4b_point_countable_food", "可数与不可数食物：bread／rice／milk 不可数；egg／apple／tomato 可数", 7, SUBJECT, 274006),
    (274077, "peng_g4b_point_quantity_food", "量词与容器 a bag of rice／a bottle of milk／a box of eggs／a piece of bread", 8, SUBJECT, 274006),
    (274078, "peng_g4b_point_healthy_eating", "健康饮食表达 We should eat more vegetables.／We mustn't waste food.", 9, SUBJECT, 274006),
    (274079, "peng_g4b_point_third_person_food", "一般现在时三单变化 comes／grows／makes／goes：描述食物来源与加工", 10, SUBJECT, 274006),
    (274080, "peng_g4b_point_food_fact_statements", "食物链事实表达 Cows eat grass. We drink milk.：用一般现在时陈述普遍事实", 11, SUBJECT, 274006),
    (274081, "peng_g4b_point_phonics_or", "字母组合 or 发 /ɔː/：corn, horse, fork, pork 的读音归类", 12, SUBJECT, 274006),

    # Revision 1
    (274082, "peng_g4b_point_review_units_1_3_words", "Units 1—3 词汇复习：课堂规则、家庭规则、时间与作息分类认读", 1, SUBJECT, 274007),
    (274083, "peng_g4b_point_review_units_1_3_sentences", "句型复习 Don't ...／We must ...／What time is it?／It's time for ...", 2, SUBJECT, 274007),
    (274084, "peng_g4b_point_review_units_1_3_grammar", "语法复习：祈使句、must 与 mustn't、一般现在时与频度副词综合运用", 3, SUBJECT, 274007),
    (274085, "peng_g4b_point_review_units_1_3_dialogue", "情景对话：说明班规家规并介绍自己一天的时间安排", 4, SUBJECT, 274007),
    (274086, "peng_g4b_point_review_units_1_3_phonics", "语音复习：ay／ai、ea、ir／ur 等字母组合发音归类", 5, SUBJECT, 274007),

    # Revision 2
    (274087, "peng_g4b_point_review_units_4_6_words", "Units 4—6 词汇复习：购物、农场动物与农作物、食物来源分类认读", 1, SUBJECT, 274008),
    (274088, "peng_g4b_point_review_units_4_6_sentences", "句型复习 How much is it?／What can you see on the farm?／Where does food come from?", 2, SUBJECT, 274008),
    (274089, "peng_g4b_point_review_units_4_6_grammar", "语法复习：名词所有格、可数与不可数名词、量词表达", 3, SUBJECT, 274008),
    (274090, "peng_g4b_point_review_units_4_6_dialogue", "情景对话：购物问价、介绍农场、讲述食物从农场到餐桌的过程", 4, SUBJECT, 274008),
    (274091, "peng_g4b_point_review_units_4_6_project", "项目展示：制作食物来源海报并用一般现在时介绍", 5, SUBJECT, 274008),
)

"""人教版（PEP）小学英语一年级上册：Starter unit 与 Unit 1—6 目录及细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 3
G1 = 1
BOOK_ID = 1425

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "人教版PEP小学英语一年级上册",
    "peng_g1a",
    25,
    "人民教育出版社",
    SUBJECT,
    G1,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # Starter unit
    (142501, "Starter unit Hello!", "peng_g1a_starter", 1, BOOK_ID, None),
    (142502, "Part A", "peng_g1a_starter_a", 1, BOOK_ID, 142501),
    (142503, "Part B", "peng_g1a_starter_b", 2, BOOK_ID, 142501),
    (142504, "Part C", "peng_g1a_starter_c", 3, BOOK_ID, 142501),

    # Unit 1 Hello!
    (142510, "Unit 1 Hello!", "peng_g1a_u01", 2, BOOK_ID, None),
    (142511, "Part A", "peng_g1a_u01_a", 1, BOOK_ID, 142510),
    (142512, "Part B", "peng_g1a_u01_b", 2, BOOK_ID, 142510),
    (142513, "Part C", "peng_g1a_u01_c", 3, BOOK_ID, 142510),

    # Unit 2 Colours
    (142520, "Unit 2 Colours", "peng_g1a_u02", 3, BOOK_ID, None),
    (142521, "Part A", "peng_g1a_u02_a", 1, BOOK_ID, 142520),
    (142522, "Part B", "peng_g1a_u02_b", 2, BOOK_ID, 142520),
    (142523, "Part C", "peng_g1a_u02_c", 3, BOOK_ID, 142520),

    # Unit 3 Look at me!
    (142530, "Unit 3 Look at me!", "peng_g1a_u03", 4, BOOK_ID, None),
    (142531, "Part A", "peng_g1a_u03_a", 1, BOOK_ID, 142530),
    (142532, "Part B", "peng_g1a_u03_b", 2, BOOK_ID, 142530),
    (142533, "Part C", "peng_g1a_u03_c", 3, BOOK_ID, 142530),

    # Unit 4 We love animals
    (142540, "Unit 4 We love animals", "peng_g1a_u04", 5, BOOK_ID, None),
    (142541, "Part A", "peng_g1a_u04_a", 1, BOOK_ID, 142540),
    (142542, "Part B", "peng_g1a_u04_b", 2, BOOK_ID, 142540),
    (142543, "Part C", "peng_g1a_u04_c", 3, BOOK_ID, 142540),

    # Unit 5 Let's eat!
    (142550, "Unit 5 Let's eat!", "peng_g1a_u05", 6, BOOK_ID, None),
    (142551, "Part A", "peng_g1a_u05_a", 1, BOOK_ID, 142550),
    (142552, "Part B", "peng_g1a_u05_b", 2, BOOK_ID, 142550),
    (142553, "Part C", "peng_g1a_u05_c", 3, BOOK_ID, 142550),

    # Unit 6 Happy birthday!
    (142560, "Unit 6 Happy birthday!", "peng_g1a_u06", 7, BOOK_ID, None),
    (142561, "Part A", "peng_g1a_u06_a", 1, BOOK_ID, 142560),
    (142562, "Part B", "peng_g1a_u06_b", 2, BOOK_ID, 142560),
    (142563, "Part C", "peng_g1a_u06_c", 3, BOOK_ID, 142560),

    # Revision
    (142570, "Revision 1", "peng_g1a_rev1", 8, BOOK_ID, None),
    (142580, "Revision 2", "peng_g1a_rev2", 9, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / grade_id / parent_id
# 267001-267009 为册域层，267010-267099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None, int | None], ...] = (
    # 册域层
    (267001, "peng_g1a_domain_starter", "小学英语一上·Starter unit Hello!", 1, SUBJECT, G1, None),
    (267002, "peng_g1a_domain_u01", "小学英语一上·Unit 1 Hello!", 2, SUBJECT, G1, None),
    (267003, "peng_g1a_domain_u02", "小学英语一上·Unit 2 Colours", 3, SUBJECT, G1, None),
    (267004, "peng_g1a_domain_u03", "小学英语一上·Unit 3 Look at me!", 4, SUBJECT, G1, None),
    (267005, "peng_g1a_domain_u04", "小学英语一上·Unit 4 We love animals", 5, SUBJECT, G1, None),
    (267006, "peng_g1a_domain_u05", "小学英语一上·Unit 5 Let's eat!", 6, SUBJECT, G1, None),
    (267007, "peng_g1a_domain_u06", "小学英语一上·Unit 6 Happy birthday!", 7, SUBJECT, G1, None),
    (267008, "peng_g1a_domain_rev1", "小学英语一上·Revision 1", 8, SUBJECT, G1, None),
    (267009, "peng_g1a_domain_rev2", "小学英语一上·Revision 2", 9, SUBJECT, G1, None),

    # Starter unit Hello!
    (267010, "peng_g1a_point_hello_hi", "问候语 Hello!／Hi!：见面打招呼的基本用语，Hello 较正式、Hi 更随意，对方可用相同用语回应", 1, SUBJECT, G1, 267001),
    (267011, "peng_g1a_point_good_morning", "早上问候 Good morning!：用于中午前的问候，回答同样用 Good morning!，注意 morning 的读音", 2, SUBJECT, G1, 267001),
    (267012, "peng_g1a_point_im_intro", "自我介绍 I'm ...：I'm 是 I am 的缩略形式，后接自己的名字，如 I'm Lily.", 3, SUBJECT, G1, 267001),
    (267013, "peng_g1a_point_whats_your_name", "What's your name? 与 My name is ...：询问对方姓名并作完整回答，也可简答 I'm ...", 4, SUBJECT, G1, 267001),
    (267014, "peng_g1a_point_goodbye", "告别用语 Goodbye!／Bye!：分别时使用，Goodbye 较正式、Bye 更口语化", 5, SUBJECT, G1, 267001),
    (267015, "peng_g1a_point_polite_words", "礼貌用语 Please／Thank you／Sorry：请求、致谢与道歉的基本表达，需配合具体情景使用", 6, SUBJECT, G1, 267001),

    # Unit 1 Hello!
    (267020, "peng_g1a_point_letters_af_read", "字母 Aa–Ff 的大小写认读：认清每个字母的大写与小写形态及字母名称音", 1, SUBJECT, G1, 267002),
    (267021, "peng_g1a_point_letters_af_write", "字母 Aa–Ff 的书写：在四线三格中按笔顺规范书写，大写占上两格、小写按字母占格", 2, SUBJECT, G1, 267002),
    (267022, "peng_g1a_point_school_things", "文具词汇 ruler／eraser／pencil／crayon／bag／pen：认读并能指认常见文具", 3, SUBJECT, G1, 267002),
    (267023, "peng_g1a_point_i_have", "句型 I have a ...：表达自己拥有某物，a 用在辅音音素开头的单数名词前", 4, SUBJECT, G1, 267002),
    (267024, "peng_g1a_point_whats_this", "What's this? 与 It's a ...：询问近处物品并用 It's a ... 回答", 5, SUBJECT, G1, 267002),
    (267025, "peng_g1a_point_stand_sit", "课堂指令 Stand up.／Sit down.：听懂指令并做出相应动作，加 please 语气更礼貌", 6, SUBJECT, G1, 267002),
    (267026, "peng_g1a_point_lets_school", "句型 Let's go to school!：Let's 表示提议一起做某事，后接动词原形", 7, SUBJECT, G1, 267002),
    (267027, "peng_g1a_point_how_are_you", "How are you? 与 I'm fine, thank you.：问候对方近况并礼貌回应", 8, SUBJECT, G1, 267002),

    # Unit 2 Colours
    (267030, "peng_g1a_point_colours_basic", "颜色词汇 red／yellow／blue／green：认读四种基本颜色并能指认相应物品", 1, SUBJECT, G1, 267003),
    (267031, "peng_g1a_point_colours_more", "颜色词汇 black／white／brown／orange／pink：扩展认读常见颜色，注意 orange 兼指橙子", 2, SUBJECT, G1, 267003),
    (267032, "peng_g1a_point_what_colour", "What colour is it? 与 It's ...：询问物品颜色并作答，colour 在美式英语中写作 color", 3, SUBJECT, G1, 267003),
    (267033, "peng_g1a_point_colour_adj", "颜色词作定语：放在名词前修饰物品，如 a red apple、a blue bag", 4, SUBJECT, G1, 267003),
    (267034, "peng_g1a_point_show_me", "指令 Show me ...／Point to ...：听懂颜色或物品指令并快速指认", 5, SUBJECT, G1, 267003),
    (267035, "peng_g1a_point_letters_gl_read", "字母 Gg–Ll 的大小写认读：区分 Gg 与 Cc、Ii 与 Ll 等形近字母的字形", 6, SUBJECT, G1, 267003),
    (267036, "peng_g1a_point_letters_gl_write", "字母 Gg–Ll 的书写：在四线三格中规范书写并注意占格与笔顺", 7, SUBJECT, G1, 267003),
    (267037, "peng_g1a_point_lets_paint", "句型 Let's paint／Colour it ...：用 Let's 提议活动，并用颜色词补全涂色指令", 8, SUBJECT, G1, 267003),

    # Unit 3 Look at me!
    (267040, "peng_g1a_point_body_face", "身体部位 eye／ear／nose／mouth／face：认读五官词汇并准确指认", 1, SUBJECT, G1, 267004),
    (267041, "peng_g1a_point_body_limbs", "身体部位 head／arm／hand／leg／foot／body：认读身体部位词汇，注意 foot 的复数为 feet", 2, SUBJECT, G1, 267004),
    (267042, "peng_g1a_point_look_at_me", "句型 Look at me!／This is my ...：引起他人注意并介绍自己的身体部位", 3, SUBJECT, G1, 267004),
    (267043, "peng_g1a_point_touch_your", "指令 Touch your ...：听懂身体部位指令并做出相应动作", 4, SUBJECT, G1, 267004),
    (267044, "peng_g1a_point_clap_hands", "动作指令 Clap your hands／Wave your arms／Stamp your feet：跟做动作，理解名词复数与动作的搭配", 5, SUBJECT, G1, 267004),
    (267045, "peng_g1a_point_letters_mr_read", "字母 Mm–Rr 的大小写认读：注意 Mm 与 Nn、Pp 与 Rr 的字形区别", 6, SUBJECT, G1, 267004),
    (267046, "peng_g1a_point_letters_mr_write", "字母 Mm–Rr 的书写：按笔顺在四线三格中规范书写，m 与 n 的小写占格相同", 7, SUBJECT, G1, 267004),
    (267047, "peng_g1a_point_i_have_body", "句型 I have a ... 描述身体特征：如 I have a big nose.，形容词放在名词前", 8, SUBJECT, G1, 267004),

    # Unit 4 We love animals
    (267050, "peng_g1a_point_animals_farm", "动物词汇 cat／dog／duck／pig／bird：认读农场常见动物名称", 1, SUBJECT, G1, 267005),
    (267051, "peng_g1a_point_animals_wild", "动物词汇 bear／elephant／monkey／panda／tiger：认读野生动物名称，注意 elephant 以元音音素开头", 2, SUBJECT, G1, 267005),
    (267052, "peng_g1a_point_animal_whats_this", "What's this? 与 It's a ...：结合动物图片问答，a 与 an 的选择依据首音", 3, SUBJECT, G1, 267005),
    (267053, "peng_g1a_point_act_like", "指令 Act like a ...：听指令模仿动物动作，理解 like 在此表示“像”", 4, SUBJECT, G1, 267005),
    (267054, "peng_g1a_point_i_like_animals", "句型 I like ...：表达对动物的喜爱，后可接名词复数表示一类", 5, SUBJECT, G1, 267005),
    (267055, "peng_g1a_point_letters_sz_read", "字母 Ss–Zz 的大小写认读：完成 26 个字母的整体认读，注意 Ss 与 Zz 的发音区别", 6, SUBJECT, G1, 267005),
    (267056, "peng_g1a_point_letters_sz_write", "字母 Ss–Zz 的书写：在四线三格中规范书写，注意 z 的小写笔顺", 7, SUBJECT, G1, 267005),
    (267057, "peng_g1a_point_animal_sounds", "动物与叫声的匹配：如 duck—quack、cat—meow，在歌谣中巩固动物词汇", 8, SUBJECT, G1, 267005),

    # Unit 5 Let's eat!
    (267060, "peng_g1a_point_food_staple", "食物词汇 bread／milk／water／cake：认读常见食物与饮品", 1, SUBJECT, G1, 267006),
    (267061, "peng_g1a_point_food_more", "食物词汇 fish／rice／egg／juice：扩展认读食物词汇，注意 fish 单复数同形", 2, SUBJECT, G1, 267006),
    (267062, "peng_g1a_point_hungry_thirsty", "句型 I'm hungry.／I'm thirsty.：表达饥饿与口渴，为提出饮食需求作铺垫", 3, SUBJECT, G1, 267006),
    (267063, "peng_g1a_point_have_some", "句型 Have some ...：招待他人吃喝，some 后接不可数名词或复数名词", 4, SUBJECT, G1, 267006),
    (267064, "peng_g1a_point_can_i_have", "Can I have some ...? 与 Here you are.：礼貌请求食物并回应递送", 5, SUBJECT, G1, 267006),
    (267065, "peng_g1a_point_letters_order", "字母表顺序 Aa–Zz：按顺序背诵并快速认读，为查字典打基础", 6, SUBJECT, G1, 267006),
    (267066, "peng_g1a_point_some_uncountable", "some 与不可数名词：milk／water／juice 等不可数名词前用 some，词尾不加 s", 7, SUBJECT, G1, 267006),
    (267067, "peng_g1a_point_food_like", "句型 I like ...／I don't like ...：表达对食物的喜好与不喜欢", 8, SUBJECT, G1, 267006),

    # Unit 6 Happy birthday!
    (267070, "peng_g1a_point_numbers_1_5", "数字 one／two／three／four／five：认读并书写英文数字 1–5", 1, SUBJECT, G1, 267007),
    (267071, "peng_g1a_point_numbers_6_10", "数字 six／seven／eight／nine／ten：认读并书写英文数字 6–10", 2, SUBJECT, G1, 267007),
    (267072, "peng_g1a_point_how_many", "How many ...? 与数量回答：询问可数物品数量并用数字作答", 3, SUBJECT, G1, 267007),
    (267073, "peng_g1a_point_happy_birthday", "生日祝福 Happy birthday!：向他人送上生日祝福，接受祝福方回应 Thank you.", 4, SUBJECT, G1, 267007),
    (267074, "peng_g1a_point_how_old", "How old are you? 与 I'm ...：询问年龄并用数字回答", 5, SUBJECT, G1, 267007),
    (267075, "peng_g1a_point_this_for_you", "句型 This is for you.：赠送礼物时的表达，接受方说 Thank you.", 6, SUBJECT, G1, 267007),
    (267076, "peng_g1a_point_birthday_things", "生日场景词汇 gift／card／balloon／party：认读生日聚会中的常见物品", 7, SUBJECT, G1, 267007),
    (267077, "peng_g1a_point_letters_match", "字母大小写配对与排序：Aa–Zz 大小写连线、缺字母补全与顺序排列", 8, SUBJECT, G1, 267007),

    # Revision 1
    (267080, "peng_g1a_point_review_greeting", "情景对话复习：问候、自我介绍、告别在真实情景中的连贯运用", 1, SUBJECT, G1, 267008),
    (267081, "peng_g1a_point_review_words1", "词汇归类复习：文具、颜色、身体部位三类词汇的听音指认与分类", 2, SUBJECT, G1, 267008),
    (267082, "peng_g1a_point_review_letters_am", "字母 Aa–Mm 综合复习：认读、书写与大小写配对", 3, SUBJECT, G1, 267008),
    (267083, "peng_g1a_point_review_commands", "课堂指令综合：Stand up／Sit down／Show me／Touch your ... 的听做反应", 4, SUBJECT, G1, 267008),

    # Revision 2
    (267085, "peng_g1a_point_review_words2", "词汇归类复习：动物、食物、生日场景词汇的听音指认与分类", 1, SUBJECT, G1, 267009),
    (267086, "peng_g1a_point_review_numbers", "数字 one–ten 复习：认读、排序与数量问答", 2, SUBJECT, G1, 267009),
    (267087, "peng_g1a_point_review_letters_nz", "字母 Nn–Zz 综合复习：认读、书写与字母表顺序", 3, SUBJECT, G1, 267009),
    (267088, "peng_g1a_point_review_birthday", "生日情景对话：祝福、询问年龄、赠送礼物的完整交流", 4, SUBJECT, G1, 267009),
    (267089, "peng_g1a_point_review_sentences", "全册核心句型综合：What's this?／What colour is it?／How many?／I have ... 的灵活运用", 5, SUBJECT, G1, 267009),
)

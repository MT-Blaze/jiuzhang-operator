"""统编版（2016）初中语文九年级下册：单元课文目录与细颗粒知识点树。"""

from __future__ import annotations

SUBJECT = 1
G9 = 9
BOOK_ID = 1306

# id / name / code / sort_order / publisher / subject_id / grade_id
BOOK_ROW: tuple[int, str, str, int, str, int, int] = (
    BOOK_ID,
    "统编版九年级语文下册",
    "jchn_g9b",
    6,
    "人民教育出版社",
    SUBJECT,
    G9,
)

# id / name / code / sort_order / textbook_id / parent_id
CHAPTER_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 单元
    (130601, "第一单元 诗歌", "jchn_g9b_u01", 1, BOOK_ID, None),
    (130602, "第二单元 小说", "jchn_g9b_u02", 2, BOOK_ID, None),
    (130603, "第三单元 文言文", "jchn_g9b_u03", 3, BOOK_ID, None),
    (130604, "第四单元 文艺论文", "jchn_g9b_u04", 4, BOOK_ID, None),
    (130605, "第五单元 戏剧", "jchn_g9b_u05", 5, BOOK_ID, None),
    (130606, "第六单元 文言文", "jchn_g9b_u06", 6, BOOK_ID, None),

    # 第一单元 诗歌
    (130611, "第1课 祖国啊，我亲爱的祖国", "jchn_g9b_l01", 1, BOOK_ID, 130601),
    (130612, "第2课 梅岭三章", "jchn_g9b_l02", 2, BOOK_ID, 130601),
    (130613, "第3课 短诗五首（月夜／萧红墓畔口占／断章／风雨／统一）", "jchn_g9b_l03", 3, BOOK_ID, 130601),
    (130614, "第4课 海燕", "jchn_g9b_l04", 4, BOOK_ID, 130601),

    # 第二单元 小说
    (130621, "第5课 孔乙己", "jchn_g9b_l05", 1, BOOK_ID, 130602),
    (130622, "第6课 变色龙", "jchn_g9b_l06", 2, BOOK_ID, 130602),
    (130623, "第7课 溜索", "jchn_g9b_l07", 3, BOOK_ID, 130602),
    (130624, "第8课 蒲柳人家（节选）", "jchn_g9b_l08", 4, BOOK_ID, 130602),

    # 第三单元 文言文
    (130631, "第9课 鱼我所欲也", "jchn_g9b_l09", 1, BOOK_ID, 130603),
    (130632, "第10课 唐雎不辱使命", "jchn_g9b_l10", 2, BOOK_ID, 130603),
    (130633, "第11课 送东阳马生序", "jchn_g9b_l11", 3, BOOK_ID, 130603),
    (130634, "第12课 词四首（渔家傲·秋思／江城子·密州出猎／破阵子·为陈同甫赋壮词以寄之／满江红（小住京华））", "jchn_g9b_l12", 4, BOOK_ID, 130603),

    # 第四单元 文艺论文
    (130641, "第13课 短文两篇（谈读书／不求甚解）", "jchn_g9b_l13", 1, BOOK_ID, 130604),
    (130642, "第14课 山水画的意境", "jchn_g9b_l14", 2, BOOK_ID, 130604),
    (130643, "第15课 无言之美", "jchn_g9b_l15", 3, BOOK_ID, 130604),
    (130644, "第16课 驱遣我们的想象", "jchn_g9b_l16", 4, BOOK_ID, 130604),

    # 第五单元 戏剧
    (130651, "第17课 屈原（节选）", "jchn_g9b_l17", 1, BOOK_ID, 130605),
    (130652, "第18课 天下第一楼（节选）", "jchn_g9b_l18", 2, BOOK_ID, 130605),
    (130653, "第19课 枣儿", "jchn_g9b_l19", 3, BOOK_ID, 130605),

    # 第六单元 文言文
    (130661, "第20课 曹刿论战", "jchn_g9b_l20", 1, BOOK_ID, 130606),
    (130662, "第21课 邹忌讽齐王纳谏", "jchn_g9b_l21", 2, BOOK_ID, 130606),
    (130663, "第22课 出师表", "jchn_g9b_l22", 3, BOOK_ID, 130606),
    (130664, "第23课 诗词曲五首（十五从军征／白雪歌送武判官归京／南乡子·登京口北固亭有怀／过零丁洋／山坡羊·潼关怀古）", "jchn_g9b_l23", 4, BOOK_ID, 130606),

    # 名著导读与课外古诗词诵读（单列）
    (130671, "名著导读《儒林外史》：讽刺作品的阅读", "jchn_g9b_l24", 7, BOOK_ID, None),
    (130672, "名著导读《简·爱》：外国小说的阅读", "jchn_g9b_l25", 8, BOOK_ID, None),
    (130681, "课外古诗词诵读（一）：定风波·莫听穿林打叶声／临江仙·夜登小阁，忆洛中旧游／太常引·建康中秋夜为吕叔潜赋／浣溪沙·身向云山那畔行", "jchn_g9b_l26", 9, BOOK_ID, None),
    (130682, "课外古诗词诵读（二）：南安军／别云间／山坡羊·骊山怀古／朝天子·咏喇叭", "jchn_g9b_l27", 10, BOOK_ID, None),
)

# id / code / name / sort_order / subject_id / parent_id
# 206001-206008 为册域层，206011-206099 为细颗粒考点。
KNOWLEDGE_ROWS: tuple[tuple[int, str, str, int, int, int | None], ...] = (
    # 册域层
    (206001, "jchn_g9b_domain_poetry", "初中九下·诗歌鉴赏与朗诵", 1, SUBJECT, None),
    (206002, "jchn_g9b_domain_fiction", "初中九下·小说阅读与讽刺艺术", 2, SUBJECT, None),
    (206003, "jchn_g9b_domain_classical", "初中九下·文言文阅读（理想与劝谏）", 3, SUBJECT, None),
    (206004, "jchn_g9b_domain_ancient_poem", "初中九下·古代诗词曲鉴赏", 4, SUBJECT, None),
    (206005, "jchn_g9b_domain_essay", "初中九下·文艺论文阅读", 5, SUBJECT, None),
    (206006, "jchn_g9b_domain_drama", "初中九下·戏剧阅读与演出", 6, SUBJECT, None),
    (206007, "jchn_g9b_domain_classics", "初中九下·名著阅读", 7, SUBJECT, None),
    (206008, "jchn_g9b_domain_writing", "初中九下·写作与语言运用", 8, SUBJECT, None),

    # 诗歌鉴赏与朗诵
    (206011, "jchn_g9b_point_poem_zu_guo_structure", "《祖国啊，我亲爱的祖国》四节意象群与情感递进", 1, SUBJECT, 206001),
    (206012, "jchn_g9b_point_poem_zu_guo_dash", "《祖国啊，我亲爱的祖国》“我是……”句式与破折号的抒情节奏", 2, SUBJECT, 206001),
    (206013, "jchn_g9b_point_poem_zu_guo_images", "《祖国啊，我亲爱的祖国》从破旧老水车到簇新理想的意象转换", 3, SUBJECT, 206001),
    (206014, "jchn_g9b_point_poem_meiling_preface", "《梅岭三章》小序的作用与绝笔诗背景", 4, SUBJECT, 206001),
    (206015, "jchn_g9b_point_poem_meiling_banner", "《梅岭三章》“旌旗十万斩阎罗”的豪情与浪漫想象", 5, SUBJECT, 206001),
    (206016, "jchn_g9b_point_poem_meiling_layers", "《梅岭三章》三章诗的情感层次与革命信念", 6, SUBJECT, 206001),
    (206017, "jchn_g9b_point_poem_yueye", "《月夜》“我”与霜风明月的意象对照", 7, SUBJECT, 206001),
    (206018, "jchn_g9b_point_poem_xiaohong", "《萧红墓畔口占》简短含蓄中的悼亡深情", 8, SUBJECT, 206001),
    (206019, "jchn_g9b_point_poem_duanzhang", "《断章》主客相对与哲思留白", 9, SUBJECT, 206001),
    (206020, "jchn_g9b_point_poem_fengyu", "《风雨》《统一》的象征与凝练表达", 10, SUBJECT, 206001),
    (206021, "jchn_g9b_point_poem_haiyan_symbol", "《海燕》中海燕、暴风雨与海鸥海鸭企鹅的象征体系", 11, SUBJECT, 206001),
    (206022, "jchn_g9b_point_poem_haiyan_contrast", "《海燕》对比烘托与反复呼告的抒情效果", 12, SUBJECT, 206001),

    # 小说阅读与讽刺艺术
    (206023, "jchn_g9b_point_fic_kong_scene", "《孔乙己》咸亨酒店的空间设置与看客群像", 1, SUBJECT, 206002),
    (206024, "jchn_g9b_point_fic_kong_money", "《孔乙己》“排出九文大钱”与“摸出四文大钱”的细节", 2, SUBJECT, 206002),
    (206025, "jchn_g9b_point_fic_kong_laugh", "《孔乙己》“笑”的多重意蕴与悲剧内核", 3, SUBJECT, 206002),
    (206026, "jchn_g9b_point_fic_kong_viewpoint", "《孔乙己》小伙计第一人称视角的叙事作用", 4, SUBJECT, 206002),
    (206027, "jchn_g9b_point_fic_chameleon_changes", "《变色龙》奥楚蔑洛夫五次变化的语言与动作", 5, SUBJECT, 206002),
    (206028, "jchn_g9b_point_fic_chameleon_coat", "《变色龙》“军大衣”细节与反复手法的讽刺效果", 6, SUBJECT, 206002),
    (206029, "jchn_g9b_point_fic_chameleon_society", "《变色龙》夸张变形下的沙皇专制社会", 7, SUBJECT, 206002),
    (206030, "jchn_g9b_point_fic_liusuo_scene", "《溜索》怒江峡谷环境描写与冒险氛围", 8, SUBJECT, 206002),
    (206031, "jchn_g9b_point_fic_liusuo_contrast", "《溜索》马帮汉子的从容与“我”的心理对比", 9, SUBJECT, 206002),
    (206032, "jchn_g9b_point_fic_liusuo_verbs", "《溜索》白描手法与动词锤炼", 10, SUBJECT, 206002),
    (206033, "jchn_g9b_point_fic_puliu_figures", "《蒲柳人家（节选）》何满子与一丈青大娘的形象", 11, SUBJECT, 206002),
    (206034, "jchn_g9b_point_fic_puliu_language", "《蒲柳人家（节选）》说书体叙述与京东北运河语言", 12, SUBJECT, 206002),

    # 文言文阅读（理想与劝谏）
    (206035, "jchn_g9b_point_cls_yu_metaphor", "《鱼我所欲也》以鱼与熊掌设喻引出“舍生取义”", 1, SUBJECT, 206003),
    (206036, "jchn_g9b_point_cls_yu_contrast", "《鱼我所欲也》正反对比论证与“不食嗟来之食”", 2, SUBJECT, 206003),
    (206037, "jchn_g9b_point_cls_yu_benxin", "《鱼我所欲也》“本心”的内涵与失其本心的批判", 3, SUBJECT, 206003),
    (206038, "jchn_g9b_point_cls_tangju_anger", "《唐雎不辱使命》“天子之怒”与“布衣之怒”的对比", 4, SUBJECT, 206003),
    (206039, "jchn_g9b_point_cls_tangju_debate", "《唐雎不辱使命》唐雎的语言交锋与凛然正气", 5, SUBJECT, 206003),
    (206040, "jchn_g9b_point_cls_tangju_sword", "《唐雎不辱使命》“挺剑而起”的戏剧性场面", 6, SUBJECT, 206003),
    (206041, "jchn_g9b_point_cls_song_hardship", "《送东阳马生序》现身说法与自身求学的艰辛", 7, SUBJECT, 206003),
    (206042, "jchn_g9b_point_cls_song_contrast", "《送东阳马生序》与太学生优越条件的对比", 8, SUBJECT, 206003),
    (206043, "jchn_g9b_point_cls_song_joy", "《送东阳马生序》“以中有足乐者”的求学境界", 9, SUBJECT, 206003),
    (206044, "jchn_g9b_point_cls_cao_trust", "《曹刿论战》取信于民与“小大之狱”的判断", 10, SUBJECT, 206003),
    (206045, "jchn_g9b_point_cls_cao_drums", "《曹刿论战》“一鼓作气”与详略安排的用意", 11, SUBJECT, 206003),
    (206046, "jchn_g9b_point_cls_zou_answers", "《邹忌讽齐王纳谏》三问三答与妻妾客的不同用心", 12, SUBJECT, 206003),
    (206047, "jchn_g9b_point_cls_zou_analogy", "《邹忌讽齐王纳谏》由家事到国事的类比讽谏", 13, SUBJECT, 206003),
    (206048, "jchn_g9b_point_cls_shibiao_advice", "《出师表》广开言路、赏罚分明、亲贤远佞三条建议", 14, SUBJECT, 206003),
    (206049, "jchn_g9b_point_cls_shibiao_loyalty", "《出师表》“报先帝、忠陛下”的知遇之情", 15, SUBJECT, 206003),
    (206050, "jchn_g9b_point_cls_words_patterns", "文言实词虚词与句式：得、患、蹴、鄙、间、之、以", 16, SUBJECT, 206003),

    # 古代诗词曲鉴赏
    (206051, "jchn_g9b_point_poem_yujiaoyi_scene", "《渔家傲·秋思》塞下秋景之“异”与边塞意象", 1, SUBJECT, 206004),
    (206052, "jchn_g9b_point_poem_yujiaoyi_homesick", "《渔家傲·秋思》“浊酒一杯家万里”的思乡报国", 2, SUBJECT, 206004),
    (206053, "jchn_g9b_point_poem_jiangchengzi_wild", "《江城子·密州出猎》“老夫聊发少年狂”的豪放气概", 3, SUBJECT, 206004),
    (206054, "jchn_g9b_point_poem_jiangchengzi_bow", "《江城子·密州出猎》“会挽雕弓如满月”的自我形象", 4, SUBJECT, 206004),
    (206055, "jchn_g9b_point_poem_pozhenzi_dream", "《破阵子·为陈同甫赋壮词以寄之》壮阔梦境与军营生活", 5, SUBJECT, 206004),
    (206056, "jchn_g9b_point_poem_pozhenzi_reality", "《破阵子》“可怜白发生”的梦境现实反差", 6, SUBJECT, 206004),
    (206057, "jchn_g9b_point_poem_manjianghong_qiu", "《满江红（小住京华）》秋瑾的巾帼豪情与身世之感", 7, SUBJECT, 206004),
    (206058, "jchn_g9b_point_poem_manjianghong_contrast", "《满江红》“身不得，男儿列；心却比，男儿烈”的对比", 8, SUBJECT, 206004),
    (206059, "jchn_g9b_point_poem_shiwu_bai", "《十五从军征》老兵归家的白描与老病孤苦", 9, SUBJECT, 206004),
    (206060, "jchn_g9b_point_poem_baixue_snow", "《白雪歌送武判官归京》奇丽雪景与送别之情", 10, SUBJECT, 206004),
    (206061, "jchn_g9b_point_poem_nanxiangzi_hero", "《南乡子·登京口北固亭有怀》怀古与英雄赞颂", 11, SUBJECT, 206004),
    (206062, "jchn_g9b_point_poem_lingding_integrity", "《过零丁洋》“人生自古谁无死”的民族气节", 12, SUBJECT, 206004),
    (206063, "jchn_g9b_point_poem_tongguan_people", "《山坡羊·潼关怀古》“兴，百姓苦；亡，百姓苦”的民本情怀", 13, SUBJECT, 206004),
    (206064, "jchn_g9b_point_poem_dingfengbo", "《定风波·莫听穿林打叶声》“一蓑烟雨任平生”的旷达", 14, SUBJECT, 206004),
    (206065, "jchn_g9b_point_poem_reading1", "课外诵读（一）：临江仙·夜登小阁／太常引／浣溪沙的今昔之感与行役之苦", 15, SUBJECT, 206004),
    (206066, "jchn_g9b_point_poem_reading2", "课外诵读（二）：南安军／别云间／山坡羊·骊山怀古／朝天子·咏喇叭的家国与讽世", 16, SUBJECT, 206004),

    # 文艺论文阅读
    (206067, "jchn_g9b_point_essay_dushu_uses", "《谈读书》读书的三种功用与经验总结", 1, SUBJECT, 206005),
    (206068, "jchn_g9b_point_essay_dushu_language", "《谈读书》比喻论证与格言式语言", 2, SUBJECT, 206005),
    (206069, "jchn_g9b_point_essay_buqiu_refute", "《不求甚解》驳论思路与“不求甚解”的真义", 3, SUBJECT, 206005),
    (206070, "jchn_g9b_point_essay_buqiu_methods", "《不求甚解》举例论证与引用论证", 4, SUBJECT, 206005),
    (206071, "jchn_g9b_point_essay_shanshui_yijing", "《山水画的意境》意境的界定与情景交融", 5, SUBJECT, 206005),
    (206072, "jchn_g9b_point_essay_shanshui_poem", "《山水画的意境》以诗证画与“景”“情”关系", 6, SUBJECT, 206005),
    (206073, "jchn_g9b_point_essay_wuyan_meaning", "《无言之美》“无言”的美学内涵", 7, SUBJECT, 206005),
    (206074, "jchn_g9b_point_essay_wuyan_examples", "《无言之美》文学、音乐、雕塑中的含蓄之美", 8, SUBJECT, 206005),
    (206075, "jchn_g9b_point_essay_xiangxiang", "《驱遣我们的想象》文字与想象的相互成就", 9, SUBJECT, 206005),
    (206076, "jchn_g9b_point_essay_reading", "文艺论文阅读：把握概念、理清思路与品味语言", 10, SUBJECT, 206005),

    # 戏剧阅读与演出
    (206077, "jchn_g9b_point_drama_quyuan_monologue", "《屈原（节选）》“雷电颂”独白的象征与激情", 1, SUBJECT, 206006),
    (206078, "jchn_g9b_point_drama_quyuan_images", "《屈原（节选）》风、雷、电意象与人物性格", 2, SUBJECT, 206006),
    (206079, "jchn_g9b_point_drama_quyuan_stage", "《屈原（节选）》舞台说明的提示作用", 3, SUBJECT, 206006),
    (206080, "jchn_g9b_point_drama_tianxia_lu", "《天下第一楼（节选）》卢孟实的经营才干与困境", 4, SUBJECT, 206006),
    (206081, "jchn_g9b_point_drama_tianxia_language", "《天下第一楼（节选）》京味语言与人物群像", 5, SUBJECT, 206006),
    (206082, "jchn_g9b_point_drama_tianxia_conflict", "《天下第一楼（节选）》戏剧冲突与福聚德的兴衰", 6, SUBJECT, 206006),
    (206083, "jchn_g9b_point_drama_zaoer_symbol", "《枣儿》老人与男孩的象征意义", 7, SUBJECT, 206006),
    (206084, "jchn_g9b_point_drama_zaoer_theme", "《枣儿》“枣儿”的多重象征与亲情呼唤", 8, SUBJECT, 206006),
    (206085, "jchn_g9b_point_drama_stage", "戏剧文学与排演：冲突、台词与舞台调度", 9, SUBJECT, 206006),

    # 名著阅读
    (206086, "jchn_g9b_point_classic_rulin_satire", "《儒林外史》“戚而能谐，婉而多讽”的讽刺艺术", 1, SUBJECT, 206007),
    (206087, "jchn_g9b_point_classic_rulin_figures", "《儒林外史》范进、周进等士人形象", 2, SUBJECT, 206007),
    (206088, "jchn_g9b_point_classic_rulin_structure", "《儒林外史》“虽云长篇，颇同短制”的结构", 3, SUBJECT, 206007),
    (206089, "jchn_g9b_point_classic_rulin_critic", "《儒林外史》对科举制度与世态人情的批判", 4, SUBJECT, 206007),
    (206090, "jchn_g9b_point_classic_jane_self", "《简·爱》简·爱的自尊与独立人格", 5, SUBJECT, 206007),
    (206091, "jchn_g9b_point_classic_jane_viewpoint", "《简·爱》第一人称叙述与心理描写", 6, SUBJECT, 206007),
    (206092, "jchn_g9b_point_classic_method", "名著阅读方法：精读与跳读、专题探究", 7, SUBJECT, 206007),

    # 写作与语言运用
    (206093, "jchn_g9b_point_write_expand", "学习扩写：抓住中心、合理想象与补充细节", 1, SUBJECT, 206008),
    (206094, "jchn_g9b_point_write_theme", "审题立意：准确理解题意与确立深刻主旨", 2, SUBJECT, 206008),
    (206095, "jchn_g9b_point_write_layout", "布局谋篇：线索、详略与结构安排", 3, SUBJECT, 206008),
    (206096, "jchn_g9b_point_write_polish", "修改润色：内容、结构与语言的打磨", 4, SUBJECT, 206008),
    (206097, "jchn_g9b_point_write_creative", "有创意地表达：选材、角度与语言创新", 5, SUBJECT, 206008),
    (206098, "jchn_g9b_point_lang_words", "九下字音字形与成语：隧洞、干瘪、胚芽、绯红、羼水等", 6, SUBJECT, 206008),
    (206099, "jchn_g9b_point_lang_activity", "综合性学习“岁月如歌——我们的初中生活”", 7, SUBJECT, 206008),
)

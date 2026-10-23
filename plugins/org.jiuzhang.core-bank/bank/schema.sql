-- 九章算子 · core-bank 存储层表结构 v0.8.2（结构冻结版）
--
-- 设计原则：存储层只存事实，不存输入校验与查重指纹一类的过程态字段。
-- 全部 DDL 为本仓库原创表达；题目标准结构见 schemas/question.json，
-- 表与契约的对应关系在出参适配层完成，不在存储层另造字段方言。
--
-- 落地顺序即依赖顺序：schools / textbooks / topics 先建，sources 与 questions 居中，
-- 多对多关联表与版本映射表收尾。外键全部 ON DELETE CASCADE，题目删除不留孤儿。
--
-- ★多版本大纲的三条地基规则（主公 2026-10-24 定调，详见 PLUGIN_SPEC §2.7）：
--   1. **考向是并集**：``topics`` 里层别为 ``tp_kx`` 的考向节点**不属于任何教材版本**
--      （``textbook_id`` 必须为 NULL），谁有新考向就往池子里加；
--   2. **大纲树是子集视图**：册/章/节是**版本目录节点**，带 ``textbook_id``；
--      左侧树按版本取，取的就是该版本目录节点 + 映射表落出来的子集；
--   3. **一道题跨版本靠映射表**：``node_topic_map`` 是「版本目录节点 → 考向」的多对多，
--      同一考向可同时出现在人教A版的第三章和苏教版的第五章下，题目本身不复制。
--   现网只有人教A版一份数据，但架子必须先立住；苏教版导入时只新增 textbooks 一行
--   与它自己的目录节点 + 映射行，**绝不复制考向**。

PRAGMA foreign_keys = ON;

-- 1) 学校表：只登记办学实体本身，与「哪张卷子」无关。
CREATE TABLE schools (
    id          TEXT    NOT NULL,
    full_name   TEXT    NOT NULL,
    short_name  TEXT    NOT NULL DEFAULT '',
    province    TEXT    NOT NULL DEFAULT '',
    city        TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    CONSTRAINT pk_schools         PRIMARY KEY (id),
    CONSTRAINT ck_schools_id      CHECK (id GLOB 'sch_[0-9a-f]*' AND length(id) BETWEEN 7 AND 32),
    CONSTRAINT ck_schools_full    CHECK (length(trim(full_name)) BETWEEN 1 AND 120),
    CONSTRAINT ck_schools_short   CHECK (length(short_name) <= 60),
    CONSTRAINT ck_schools_region  CHECK (length(province) <= 40 AND length(city) <= 40)
);
CREATE UNIQUE INDEX uq_schools_full_name ON schools (full_name);
CREATE INDEX idx_schools_short_name ON schools (short_name);

-- 1b) 教材版本表：一行一个「教材版本」（人教A版 / 人教B版 / 苏教版 / 北师大版…）。
--     考向并集与它无关，它只给目录节点与映射行提供版本身份。
--     id 定长 11：tb_ + 8 位十六进制摘要（与 sch_/tp_ 同族口径，底座签发）。
CREATE TABLE textbooks (
    id          TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    publisher   TEXT    NOT NULL DEFAULT '',
    edition     TEXT    NOT NULL DEFAULT '',
    is_default  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    CONSTRAINT pk_textbooks         PRIMARY KEY (id),
    CONSTRAINT ck_textbooks_id      CHECK (length(id) = 11 AND substr(id, 1, 3) = 'tb_'
                                                   AND substr(id, 4, 8) GLOB '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'),
    CONSTRAINT ck_textbooks_name    CHECK (length(trim(name)) BETWEEN 1 AND 60),
    CONSTRAINT ck_textbooks_pub     CHECK (length(publisher) <= 60),
    CONSTRAINT ck_textbooks_edition CHECK (length(edition) <= 40),
    CONSTRAINT ck_textbooks_flag    CHECK (is_default IN (0, 1)),
    CONSTRAINT ck_textbooks_updated CHECK (updated_at >= created_at)
);
CREATE UNIQUE INDEX uq_textbooks_name ON textbooks (name);
-- 默认版本至多一个：读路径据此决定「打开工作台先看哪版大纲」，不靠代码写死教材名。
CREATE UNIQUE INDEX uq_textbooks_default ON textbooks (is_default) WHERE is_default = 1;

-- 2) 大纲表：教材/章/节/考向单表物化路径，parent_id 自引用成树。
--    id 定长 13：tp_ + 两位层别码（bo 册 / ch 章 / se 节 / kx 考向）+ 8 位十六进制摘要；
--    层别不另设冗余列，看 id 前缀即知。path 存 id 序列，sort_order 定同父兄弟序。
--    textbook_id：版本目录节点（bo/ch/se）填所属版本，**考向（kx）必须留 NULL**——
--    考向是所有教材版本的并集，绑版本就等于把考向私有化。
--    本列不加内联外键：SQLite 的 ALTER TABLE 无法给既有表追加 FK，加了会让
--    「新建库」与「迁移库」两种结构分叉；引用完整性由 node_topic_map 的 FK、
--    适配层校验与契约测试三处共同守住（同一口径见 bank.py 的 TOPIC_LAYER）。
CREATE TABLE topics (
    id           TEXT    NOT NULL,
    parent_id    TEXT    NULL,
    textbook_id  TEXT    NULL,
    name         TEXT    NOT NULL,
    path         TEXT    NOT NULL,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    status       TEXT    NOT NULL DEFAULT 'active',
    created_at   TEXT    NOT NULL,
    updated_at   TEXT    NOT NULL,
    CONSTRAINT pk_topics        PRIMARY KEY (id),
    CONSTRAINT ck_topics_id     CHECK (length(id) = 13 AND substr(id, 1, 5) IN ('tp_bo', 'tp_ch', 'tp_se', 'tp_kx')
                                               AND substr(id, 6, 8) GLOB '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'),
    CONSTRAINT ck_topics_name   CHECK (length(trim(name)) BETWEEN 1 AND 120),
    CONSTRAINT ck_topics_path   CHECK (path GLOB 'tp_*' AND length(path) <= 512),
    CONSTRAINT ck_topics_status CHECK (status IN ('active', 'archived', 'draft')),
    CONSTRAINT ck_topics_sort   CHECK (sort_order >= 0),
    CONSTRAINT ck_topics_acyclic CHECK (parent_id IS NULL OR parent_id <> id),
    CONSTRAINT ck_topics_textbook CHECK (textbook_id IS NULL OR (textbook_id GLOB 'tb_*' AND length(textbook_id) = 11)),
    -- 并集不变量：考向节点不绑版本。违反它就是把考向私有化，跨版本复用立刻失效。
    CONSTRAINT ck_topics_taxonomy_shared CHECK (substr(id, 1, 5) <> 'tp_kx' OR textbook_id IS NULL),
    CONSTRAINT fk_topics_parent FOREIGN KEY (parent_id) REFERENCES topics (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_topics_path      ON topics (path);
CREATE UNIQUE INDEX uq_topics_sibling   ON topics (parent_id, sort_order);
CREATE INDEX      idx_topics_parent_id  ON topics (parent_id);
CREATE INDEX      idx_topics_name       ON topics (name);
CREATE INDEX      idx_topics_textbook   ON topics (textbook_id);

-- 3) 题目主表：纯题目内容。
--    选项/扩展为 JSON 数组，答案与解析为正文；无选项题型强制 options = '[]'。
--    extensions 留给教师自己的单题备注（有序数组），不再承接查重、校验过程态。
CREATE TABLE questions (
    id          TEXT    NOT NULL,
    type        TEXT    NOT NULL,
    stem        TEXT    NOT NULL,
    options     TEXT    NOT NULL DEFAULT '[]',
    answer      TEXT    NULL,
    solution    TEXT    NULL,
    extensions  TEXT    NOT NULL DEFAULT '[]',
    difficulty  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    CONSTRAINT pk_questions            PRIMARY KEY (id),
    CONSTRAINT ck_questions_id         CHECK (id GLOB 'q_[A-Za-z0-9]*' AND length(id) BETWEEN 3 AND 80),
    CONSTRAINT ck_questions_type       CHECK (type IN ('single_choice', 'multiple_choice', 'fill_blank', 'solution')),
    CONSTRAINT ck_questions_difficulty CHECK (difficulty IN ('L1', 'L2', 'L3', 'L4')),
    CONSTRAINT ck_questions_stem       CHECK (length(trim(stem)) >= 1),
    CONSTRAINT ck_questions_options    CHECK (json_valid(options) = 1 AND json_type(options) = 'array'),
    CONSTRAINT ck_questions_ext        CHECK (json_valid(extensions) = 1 AND json_type(extensions) = 'array'),
    CONSTRAINT ck_questions_answer     CHECK (answer IS NULL OR length(answer) <= 20000),
    CONSTRAINT ck_choices_have_options CHECK (
        type NOT IN ('single_choice', 'multiple_choice') OR json_array_length(options) >= 2
    ),
    CONSTRAINT ck_nonchoices_no_options CHECK (
        type IN ('single_choice', 'multiple_choice') OR json_array_length(options) = 0
    ),
    CONSTRAINT ck_questions_updated     CHECK (updated_at >= created_at)
);
CREATE INDEX idx_questions_type       ON questions (type);
CREATE INDEX idx_questions_difficulty ON questions (difficulty);
CREATE INDEX idx_questions_updated_at ON questions (updated_at);

-- 4) 考向教研笔记表：方法、易错点一类的教研正文挂在考向节点上，不属于单题。
CREATE TABLE topic_notes (
    id          INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    topic_id    TEXT    NOT NULL,
    note_type   TEXT    NOT NULL,
    content     TEXT    NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    CONSTRAINT ck_topic_notes_type CHECK (note_type IN ('method', 'pitfall', 'knowledge', 'insight')),
    CONSTRAINT ck_topic_notes_sort CHECK (sort_order >= 0),
    CONSTRAINT fk_topic_notes_topic FOREIGN KEY (topic_id) REFERENCES topics (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_topic_notes_slot   ON topic_notes (topic_id, note_type, sort_order);
CREATE INDEX      idx_topic_notes_lookup  ON topic_notes (topic_id, note_type);

-- 5) 来源表：一张试卷一行；题号与「本校本题」的关系不属于来源本身。
--    school_id 可空：源卷未登记办学实体时留 NULL。
--    实测 SQLite 只在「可空 + ON DELETE SET NULL」下才能在撤档学校时保住这张卷；
--    NOT NULL DEFAULT '' 配 SET DEFAULT 会被外键检查拦死，RESTRICT 则连卷一起删不掉。
--    grade（高一/高二/高三）是主公 2026-10-23 裁定的年级落位：与 year/exam_type 同级，
--    不塞进 exam_type（那会让一列两套语义）。本轮结构解冻只补这一列，其余列名与约束不动。
CREATE TABLE sources (
    id          TEXT    NOT NULL PRIMARY KEY,
    school_id   TEXT    NULL,
    year        INTEGER NULL,
    exam_type   TEXT    NOT NULL DEFAULT '',
    grade       TEXT    NOT NULL DEFAULT '',
    paper_name  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    CONSTRAINT ck_sources_school CHECK (school_id IS NULL OR (school_id GLOB 'sch_[0-9a-f]*' AND length(school_id) BETWEEN 7 AND 32)),
    CONSTRAINT ck_sources_year  CHECK (year IS NULL OR (year BETWEEN 1990 AND 2100)),
    CONSTRAINT ck_sources_exam  CHECK (length(exam_type) <= 40),
    CONSTRAINT ck_sources_grade CHECK (length(grade) <= 20),
    CONSTRAINT ck_sources_paper CHECK (length(trim(paper_name)) BETWEEN 1 AND 200),
    CONSTRAINT uq_sources_paper UNIQUE (school_id, year, exam_type, grade, paper_name),
    CONSTRAINT fk_sources_school FOREIGN KEY (school_id) REFERENCES schools (id) ON DELETE SET NULL
);
CREATE INDEX idx_sources_school_id ON sources (school_id);
CREATE INDEX idx_sources_year      ON sources (year);
CREATE INDEX idx_sources_grade     ON sources (grade);

-- 6) 题目-考向多对多：出同类题直接按 topic_id 反查此表，不再另建同类题关联表。
CREATE TABLE question_topics (
    question_id  TEXT    NOT NULL,
    topic_id     TEXT    NOT NULL,
    is_primary   INTEGER NOT NULL DEFAULT 0,
    sort_order   INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL,
    CONSTRAINT pk_question_topics  PRIMARY KEY (question_id, topic_id),
    CONSTRAINT ck_question_topics_primary CHECK (is_primary IN (0, 1)),
    CONSTRAINT fk_qt_question FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
    CONSTRAINT fk_qt_topic    FOREIGN KEY (topic_id)    REFERENCES topics (id)    ON DELETE CASCADE
);
CREATE INDEX idx_question_topics_topic  ON question_topics (topic_id);
CREATE UNIQUE INDEX uq_question_topics_primary
    ON question_topics (question_id) WHERE is_primary = 1;

-- 7) 题目-来源多对多：同一题被不同学校不同年份考过，就各占一行，原卷题号随行保存。
CREATE TABLE question_sources (
    id           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    question_id  TEXT    NOT NULL,
    source_id    TEXT    NOT NULL,
    question_no  TEXT    NOT NULL DEFAULT '',
    created_at   TEXT    NOT NULL,
    CONSTRAINT ck_qs_question_no   CHECK (length(question_no) <= 20),
    CONSTRAINT uq_question_sources_slot UNIQUE (question_id, source_id, question_no),
    CONSTRAINT fk_qs_question FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
    CONSTRAINT fk_qs_source   FOREIGN KEY (source_id)  REFERENCES sources (id)   ON DELETE CASCADE
);
CREATE INDEX idx_question_sources_question ON question_sources (question_id);
CREATE INDEX idx_question_sources_source  ON question_sources (source_id);

-- 8) 版本目录节点 → 考向 的映射表：多版本大纲的唯一桥。
--    一行 = 「某版本的某个目录节点（册/章/节）下出现某考向」。
--    同一考向可以被任意多个版本的任意多个节点引用，于是：
--      · 苏教版导入时只新增它自己的 textbooks 行 + 目录节点 + 映射行，考向零复制；
--      · 左侧大纲树按 textbook_id 取子集，题目仍按 question_topics 反查考向，
--        换版本不改题目、不改考向、不改题-考向关联。
--    outline_node_id 只许指版本目录节点（bo/ch/se），topic_id 只许指考向（kx）——
--    两条 CHECK 把「映射」钉死成「目录 → 考向」，防止有人拿它挂章挂章、节挂节。
--    sort_order 只是**该考向在自己父节点下的兄弟序快照**，用于同版本内稳定展示；
--    跨节点的展示序一律回读 topics.sort_order，这里不设唯一约束——
--    曾经设过 (textbook_id, outline_node_id, sort_order) 唯一索引，迁移时把一半映射行
--    静默 IGNORE 掉了（同节下两个考向兄弟序相同），纯关系表不该替被引用方记账。
CREATE TABLE node_topic_map (
    outline_node_id  TEXT    NOT NULL,
    topic_id         TEXT    NOT NULL,
    textbook_id      TEXT    NOT NULL,
    sort_order       INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL,
    CONSTRAINT pk_node_topic_map     PRIMARY KEY (outline_node_id, topic_id),
    CONSTRAINT ck_ntm_outline_layer  CHECK (substr(outline_node_id, 1, 5) IN ('tp_bo', 'tp_ch', 'tp_se')),
    CONSTRAINT ck_ntm_topic_layer    CHECK (substr(topic_id, 1, 5) = 'tp_kx'),
    CONSTRAINT ck_ntm_textbook       CHECK (textbook_id GLOB 'tb_*' AND length(textbook_id) = 11),
    CONSTRAINT ck_ntm_sort           CHECK (sort_order >= 0),
    CONSTRAINT fk_ntm_outline  FOREIGN KEY (outline_node_id) REFERENCES topics (id)     ON DELETE CASCADE,
    CONSTRAINT fk_ntm_topic    FOREIGN KEY (topic_id)       REFERENCES topics (id)     ON DELETE CASCADE,
    CONSTRAINT fk_ntm_textbook FOREIGN KEY (textbook_id)    REFERENCES textbooks (id)  ON DELETE CASCADE
);
-- 按版本取大纲子集、按考向反查它在哪些版本出现过，都靠这两条索引。
CREATE INDEX idx_ntm_textbook ON node_topic_map (textbook_id, outline_node_id);
CREATE INDEX idx_ntm_topic    ON node_topic_map (topic_id);

-- 题库元信息：来源说明、结构版本等键值对，不参与业务查询。
CREATE TABLE bank_meta (
    key    TEXT NOT NULL,
    value  TEXT NOT NULL,
    CONSTRAINT pk_bank_meta PRIMARY KEY (key)
);

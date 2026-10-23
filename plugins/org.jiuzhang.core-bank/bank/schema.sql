-- 九章算子 · core-bank 存储层表结构 v0.6.3（结构冻结版）
--
-- 设计原则：存储层只存事实，不存输入校验与查重指纹一类的过程态字段。
-- 全部 DDL 为本仓库原创表达；题目标准结构见 schemas/question.json，
-- 表与契约的对应关系在出参适配层完成，不在存储层另造字段方言。
--
-- 落地顺序即依赖顺序：schools / topics 先建，sources 与 questions 居中，
-- 两张多对多关联表收尾。外键全部 ON DELETE CASCADE，题目删除不留孤儿。

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

-- 2) 考向大纲表：教材/章/节/考向单表物化路径，parent_id 自引用成树。
--    id 定长 13：tp_ + 两位层别码（bo 册 / ch 章 / se 节 / kx 考向）+ 8 位十六进制摘要；
--    层别不另设冗余列，看 id 前缀即知。path 存 id 序列，sort_order 定同父兄弟序。
CREATE TABLE topics (
    id          TEXT    NOT NULL,
    parent_id   TEXT    NULL,
    name        TEXT    NOT NULL,
    path        TEXT    NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    status      TEXT    NOT NULL DEFAULT 'active',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    CONSTRAINT pk_topics        PRIMARY KEY (id),
    CONSTRAINT ck_topics_id     CHECK (length(id) = 13 AND substr(id, 1, 5) IN ('tp_bo', 'tp_ch', 'tp_se', 'tp_kx')
                                               AND substr(id, 6, 8) GLOB '[0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]'),
    CONSTRAINT ck_topics_name   CHECK (length(trim(name)) BETWEEN 1 AND 120),
    CONSTRAINT ck_topics_path   CHECK (path GLOB 'tp_*' AND length(path) <= 512),
    CONSTRAINT ck_topics_status CHECK (status IN ('active', 'archived', 'draft')),
    CONSTRAINT ck_topics_sort   CHECK (sort_order >= 0),
    CONSTRAINT ck_topics_acyclic CHECK (parent_id IS NULL OR parent_id <> id),
    CONSTRAINT fk_topics_parent FOREIGN KEY (parent_id) REFERENCES topics (id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX uq_topics_path      ON topics (path);
CREATE UNIQUE INDEX uq_topics_sibling   ON topics (parent_id, sort_order);
CREATE INDEX      idx_topics_parent_id  ON topics (parent_id);
CREATE INDEX      idx_topics_name       ON topics (name);

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
CREATE TABLE sources (
    id          TEXT    NOT NULL PRIMARY KEY,
    school_id   TEXT    NULL,
    year        INTEGER NULL,
    exam_type   TEXT    NOT NULL DEFAULT '',
    paper_name  TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    CONSTRAINT ck_sources_school CHECK (school_id IS NULL OR (school_id GLOB 'sch_[0-9a-f]*' AND length(school_id) BETWEEN 7 AND 32)),
    CONSTRAINT ck_sources_year  CHECK (year IS NULL OR (year BETWEEN 1990 AND 2100)),
    CONSTRAINT ck_sources_exam  CHECK (length(exam_type) <= 40),
    CONSTRAINT ck_sources_paper CHECK (length(trim(paper_name)) BETWEEN 1 AND 200),
    CONSTRAINT uq_sources_paper UNIQUE (school_id, year, exam_type, paper_name),
    CONSTRAINT fk_sources_school FOREIGN KEY (school_id) REFERENCES schools (id) ON DELETE SET NULL
);
CREATE INDEX idx_sources_school_id ON sources (school_id);
CREATE INDEX idx_sources_year      ON sources (year);

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

-- 题库元信息：来源说明、结构版本等键值对，不参与业务查询。
CREATE TABLE bank_meta (
    key    TEXT NOT NULL,
    value  TEXT NOT NULL,
    CONSTRAINT pk_bank_meta PRIMARY KEY (key)
);

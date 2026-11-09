-- 九章题库结构（沙盒终极定稿，schema version 2）
-- 31 张纯正关系表：所有嵌套结构拆为关系行，文本字段只存 Markdown/LaTeX 原文。
-- SQLite 外键开关按连接生效，读写前必须先执行 PRAGMA foreign_keys = ON。
-- 外键动作全部收敛为 RESTRICT（保护被引用数据）或 CASCADE（随父行清理从表）。
-- 命名规范：平铺字典 dict_，业务维度 dim_（树状维度与强绑定学科年级的维度一律 dim_），
--           题目从表 question_，多对多桥接 _map。

PRAGMA foreign_keys = ON;

BEGIN;
-- [功能注释] 学科字典：存学科名称与编码，是教材、知识点等学科维度的根
CREATE TABLE dict_subjects (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 学科名称，展示给用户看的业务词汇，全局唯一
    name       TEXT NOT NULL UNIQUE,
    -- [字段注释] 学科编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order INTEGER NOT NULL DEFAULT 0
);
-- [功能注释] 年级字典：存年级名称、编码与学段，供教材与题目来源定位年级
CREATE TABLE dict_grades (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 年级名称，展示给用户看的业务词汇，全局唯一
    name       TEXT NOT NULL UNIQUE,
    -- [字段注释] 年级编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 学段，标记年级所属的小学 / 初中 / 高中等学段，可为空
    stage      TEXT
);
-- [功能注释] 题型字典：存选择题、填空题等题型枚举
CREATE TABLE dict_question_types (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 题型名称，如选择题、填空题，全局唯一
    name       TEXT NOT NULL UNIQUE,
    -- [字段注释] 题型编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order INTEGER NOT NULL DEFAULT 0
);
-- [功能注释] 难度字典：存认知五阶名称、编码、等级、说明与 AI 判定提示词，供题目难度定位
CREATE TABLE dict_difficulties (
    id          INTEGER PRIMARY KEY,
    -- [字段注释] 难度名称，展示给用户看的业务词汇，全局唯一
    name        TEXT NOT NULL UNIQUE,
    -- [字段注释] 难度编码，系统底层唯一标识，不随名称更改
    code        TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order  INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 难度等级，固定 1-5 的整数刻度，全局唯一，供难度排序与筛选
    level       INTEGER NOT NULL UNIQUE CHECK (level BETWEEN 1 AND 5),
    -- [字段注释] 难度说明，用于详细解释该认知层级的考查侧重点
    description TEXT,
    -- [字段注释] AI 判定提示词，提供给流水线大模型进行难度打标的专属量化指令
    ai_prompt   TEXT
);
-- [功能注释] 题目质量字典：存经典题、普通题、烂题的质量分档，供题目质量定位
CREATE TABLE dict_question_qualities (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 质量分档名称，经典题 / 普通题 / 烂题，全局唯一
    name       TEXT NOT NULL UNIQUE,
    -- [字段注释] 质量分档编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order INTEGER NOT NULL DEFAULT 0
);
-- 学校字典：textbook_id 表示该校主用教材版本，与题目来源章节版本互通
-- [功能注释] 学校字典：存学校全称、简称、地区及主用教材版本，供题目来源标注学校
CREATE TABLE dim_schools (
    id          INTEGER PRIMARY KEY,
    -- [字段注释] 学校全称，展示给用户看的完整业务名称，全局唯一
    name        TEXT NOT NULL UNIQUE,
    -- [字段注释] 学校简称，用于题目来源等场景的快捷展示，同一地区内唯一
    short_name  TEXT NOT NULL,
    -- [字段注释] 学校编码，系统底层唯一标识，不随名称更改
    code        TEXT NOT NULL UNIQUE,
    -- [字段注释] 所属地区（只填核心地名，严禁带省/市/自治区后缀），用于题目来源的时空标注，可为空
    region      TEXT,
    textbook_id INTEGER REFERENCES dim_textbooks(id) ON DELETE RESTRICT,
    UNIQUE (region, short_name)
);
-- [功能注释] 教材版本字典：存版本名称、出版社，并归属学科与年级
CREATE TABLE dim_textbooks (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 教材版本名称，如人教版、北师大版，同一学科内唯一
    name       TEXT NOT NULL,
    -- [字段注释] 教材版本编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 出版社名称，记录教材的出版机构，可为空
    publisher  TEXT,
    subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    grade_id   INTEGER REFERENCES dict_grades(id) ON DELETE RESTRICT,
    UNIQUE (subject_id, name)
);
-- 教材章节字典：parent_id 自关联，父节点为章，子节点为节
-- [功能注释] 教材章节字典：parent_id 自关联成“章 -> 节”，供题目来源定位章节
CREATE TABLE dim_textbook_chapters (
    id          INTEGER PRIMARY KEY,
    -- [字段注释] 章节名称，同一教材同一父节点下唯一
    name        TEXT NOT NULL,
    -- [字段注释] 章节编码，系统底层唯一标识，不随名称更改
    code        TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于同级章节的展示顺序，数值越小越靠前
    sort_order  INTEGER NOT NULL DEFAULT 0,
    textbook_id INTEGER NOT NULL REFERENCES dim_textbooks(id) ON DELETE CASCADE,
    parent_id   INTEGER REFERENCES dim_textbook_chapters(id) ON DELETE RESTRICT,
    CHECK (parent_id IS NULL OR parent_id <> id)
);

CREATE UNIQUE INDEX ux_dim_textbook_chapters_sibling_name
    ON dim_textbook_chapters (textbook_id, COALESCE(parent_id, 0), name);
-- [功能注释] 题目来源字典：存题目出处名称（试卷、教辅、导学案等）、考试类型、年份与地区，并挂接年级、章节、学校等时空属性
CREATE TABLE dim_sources (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 题目来源名称，如某年某卷、某教辅，展示给用户看的业务词汇
    name       TEXT NOT NULL,
    -- [字段注释] 题目来源编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 考试类型：固定为 11 种考试场景之一——高考题 / 联考题 / 区域统考题 / 校考题 / 机构题 / 汇编题 / 自编题 / 强基题 / 竞赛题 / 自主招生题 / 外国题
    exam_type  TEXT NOT NULL CHECK (exam_type IN ('高考题', '联考题', '区域统考题', '校考题', '机构题', '汇编题', '自编题', '强基题', '竞赛题', '自主招生题', '外国题')),
    -- [字段注释] 来源年份，限定 1900-2100，可为空
    year       INTEGER CHECK (year IS NULL OR year BETWEEN 1900 AND 2100),
    -- [字段注释] 来源地区，标注试卷或教辅的适用区域，可为空
    region     TEXT,
    -- [字段注释] 该记录的创建时间，默认取当前 UTC 时间
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    grade_id   INTEGER REFERENCES dict_grades(id) ON DELETE RESTRICT,
    chapter_id INTEGER REFERENCES dim_textbook_chapters(id) ON DELETE RESTRICT,
    school_id  INTEGER REFERENCES dim_schools(id) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX ux_dim_sources_natural_key
    ON dim_sources (name, COALESCE(year, 0), COALESCE(region, ''));
-- [功能注释] 知识点字典：parent_id 自关联成“函数 -> 性质 -> 奇偶性”层级，供题目绑定底层概念
CREATE TABLE dim_knowledge_points (
    id          INTEGER PRIMARY KEY,
    -- [字段注释] 知识点名称，展示给用户看的业务词汇，同一学科同一父节点下唯一
    name        TEXT NOT NULL,
    -- [字段注释] 知识点编码，系统底层唯一标识，不随名称更改，全局唯一
    code        TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于同级知识点的展示顺序，数值越小越靠前
    sort_order  INTEGER NOT NULL DEFAULT 0,
    subject_id  INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    grade_id    INTEGER REFERENCES dict_grades(id) ON DELETE RESTRICT,
    parent_id   INTEGER REFERENCES dim_knowledge_points(id) ON DELETE RESTRICT,
    CHECK (parent_id IS NULL OR parent_id <> id)
);

-- 唯一性按学科隔离：不同学科允许出现同名知识点
CREATE UNIQUE INDEX ux_dim_knowledge_points_sibling_name
    ON dim_knowledge_points (subject_id, COALESCE(parent_id, 0), name);
-- [功能注释] 考向字典：存讲义标题与组卷抓手，一个考向可跨多个知识点
CREATE TABLE dim_exam_directions (
    id          INTEGER PRIMARY KEY,
    -- [字段注释] 考向名称，展示给用户看的业务词汇，同一学科内唯一
    name        TEXT NOT NULL,
    -- [字段注释] 考向编码，系统底层唯一标识，不随名称更改，全局唯一
    code        TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于讲义与组卷列表的展示顺序，数值越小越靠前
    sort_order  INTEGER NOT NULL DEFAULT 0,
    subject_id  INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    grade_id    INTEGER REFERENCES dict_grades(id) ON DELETE RESTRICT,
    -- [字段注释] 考向所属教材节次，精确锚定考向在教材中的位置，可为空
    chapter_id  INTEGER REFERENCES dim_textbook_chapters(id) ON DELETE RESTRICT,
    -- [字段注释] 考向说明，用于前端展示讲义标题与考查边界，可为空
    description TEXT,
    UNIQUE (subject_id, name)
);
-- [功能注释] 知识点与考向关联表：一个考向可串联多个知识点，二者多对多
CREATE TABLE knowledge_exam_map (
    knowledge_point_id INTEGER NOT NULL
                       REFERENCES dim_knowledge_points(id) ON DELETE RESTRICT,
    exam_direction_id  INTEGER NOT NULL
                       REFERENCES dim_exam_directions(id) ON DELETE RESTRICT,
    PRIMARY KEY (knowledge_point_id, exam_direction_id)
) WITHOUT ROWID;
-- [功能注释] 导入批次表：记录每次入库的流水线版本、起止时间与状态
CREATE TABLE ingest_batches (
    id               INTEGER PRIMARY KEY,
    -- [字段注释] 入库流水线的版本号，用于追溯本次导入所用的解析器版本
    pipeline_version TEXT NOT NULL,
    -- [字段注释] 本批次开始导入的时间，默认取当前 UTC 时间
    started_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- [字段注释] 本批次结束导入的时间，仍未结束时为空
    finished_at      TEXT,
    -- [字段注释] 批次状态，限定 pending / running / completed / failed
    status           TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    -- [字段注释] 批次备注，记录本次导入的补充说明，可为空
    note             TEXT
);
-- [功能注释] 原始题目表：保留导入原文与内容哈希，是题目溯源链的起点
CREATE TABLE raw_questions (
    id           TEXT PRIMARY KEY,
    batch_id     INTEGER NOT NULL REFERENCES ingest_batches(id) ON DELETE RESTRICT,
    -- [字段注释] 导入时的原始题目文本，保持原样不做清洗
    raw_content  TEXT NOT NULL,
    -- [字段注释] 原文内容的哈希值，用于查重与溯源比对
    content_hash TEXT NOT NULL,
    -- [字段注释] 解析状态，限定 pending / parsed / failed
    status       TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'parsed', 'failed')),
    -- [字段注释] 解析失败时的错误信息，解析成功时为空
    error        TEXT,
    -- [字段注释] 该记录的创建时间，默认取当前 UTC 时间
    created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
-- [功能注释] 题目主表：存题干、题型、难度等固有属性，不含答案、解析和时空外键
CREATE TABLE questions (
    id               TEXT PRIMARY KEY
                     CHECK (length(id) > 2 AND substr(id, 1, 2) = 'q_'),
    -- [字段注释] 题干原文，只存 Markdown/LaTeX 原文
    stem             TEXT NOT NULL,
    subject_id       INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    question_type_id INTEGER NOT NULL REFERENCES dict_question_types(id) ON DELETE RESTRICT,
    difficulty_id    INTEGER NOT NULL REFERENCES dict_difficulties(id) ON DELETE RESTRICT,
    -- [字段注释] 题目质量分档外键，无数据库默认值，写入时必须由调用方显式提供
    quality_id       INTEGER NOT NULL
                     REFERENCES dict_question_qualities(id) ON DELETE RESTRICT,
    raw_id           TEXT REFERENCES raw_questions(id) ON DELETE RESTRICT,
    -- [字段注释] 软删除时间，为空表示题目有效，非空表示已标记删除
    deleted_at       TEXT DEFAULT NULL,
    -- [字段注释] 该记录的创建时间，默认取当前 UTC 时间
    created_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    -- [字段注释] 该记录最近一次更新的时间
    updated_at       TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);
-- [功能注释] 选项从表：存选项标号、内容与正确标记，随题目级联清理
CREATE TABLE question_options (
    id           INTEGER PRIMARY KEY,
    question_id  TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    -- [字段注释] 选项标号，如 A / B / C / D，同一题内唯一
    option_label TEXT NOT NULL,
    -- [字段注释] 选项内容原文，允许 Markdown/LaTeX
    content      TEXT NOT NULL,
    -- [字段注释] 是否正确选项，1 表示正确，0 表示错误
    is_correct   INTEGER NOT NULL DEFAULT 0 CHECK (is_correct IN (0, 1)),
    UNIQUE (question_id, option_label),
    UNIQUE (question_id, id)
);
-- [功能注释] 图片从表：存图片路径与归属（题干/答案/解析/选项），选项图绑定具体选项
CREATE TABLE question_images (
    id          INTEGER PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    -- [字段注释] 图片归属位置，限定题干 / 答案 / 解析 / 选项
    belongs_to  TEXT NOT NULL
                CHECK (belongs_to IN ('stem', 'answer', 'solution', 'option')),
    option_id   INTEGER,
    -- [字段注释] 图片文件路径，指向项目资源目录
    path        TEXT NOT NULL,
    -- [字段注释] 图片替代文本（无障碍/防裂图用，可为空）
    alt         TEXT,
    -- [字段注释] 图片在所属位置内的展示排序，数值越小越靠前
    sort_order  INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 该记录的创建时间，默认取当前 UTC 时间
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    CHECK (
        (belongs_to = 'option' AND option_id IS NOT NULL)
        OR (belongs_to <> 'option' AND option_id IS NULL)
    ),
    FOREIGN KEY (question_id, option_id)
        REFERENCES question_options (question_id, id) ON DELETE CASCADE
);
-- 答案从表：答案彻底脱离主表，is_primary 标记主答案
-- [功能注释] 答案从表：存答案原文与主答案标记，一道题可有多条答案
CREATE TABLE question_answers (
    id             INTEGER PRIMARY KEY,
    question_id    TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    -- [字段注释] 答案原文，允许 Markdown/LaTeX
    answer_content TEXT NOT NULL,
    -- [字段注释] 是否主答案，1 表示主答案，同一题最多一条
    is_primary     INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    -- [字段注释] 多条答案的展示排序，数值越小越靠前
    sort_order     INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 该记录的创建时间，默认取当前 UTC 时间
    created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE UNIQUE INDEX ux_question_answers_primary
    ON question_answers (question_id) WHERE is_primary = 1;
-- 备注：1 对 1，只存 remark 原文
-- [功能注释] 题目备注从表：与题目 1 对 1，只存备注原文
CREATE TABLE question_remarks (
    question_id TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
    -- [字段注释] 备注原文，与题目 1 对 1，只存 Markdown/LaTeX 原文
    remark      TEXT NOT NULL
);
-- 解析从表：完整解析原文，不再写入主表；方法/思想/素养统一由解析侧关联表承载
-- [功能注释] 解析从表：存完整解析原文，支持一题多解
CREATE TABLE question_solutions (
    id          INTEGER PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    -- [字段注释] 解析原文，允许 Markdown/LaTeX
    content     TEXT NOT NULL,
    -- [字段注释] 是否主解析，1 表示主解析，同一题最多一条
    is_primary  INTEGER NOT NULL DEFAULT 0 CHECK (is_primary IN (0, 1)),
    -- [字段注释] 多种解法的展示排序，数值越小越靠前
    sort_order  INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 该记录的创建时间，默认取当前 UTC 时间
    created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE UNIQUE INDEX ux_question_solutions_primary
    ON question_solutions (question_id) WHERE is_primary = 1;
-- 题目补充从表：思路、分析、易错点、点睛等教研杂项，按命名空间行存储，不使用嵌套格式
-- [功能注释] 题目补充从表：存思路、分析、易错点、点睛等教研杂项，不写入主表
CREATE TABLE question_supplements (
    id          INTEGER PRIMARY KEY,
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    -- [字段注释] 补充内容的命名空间，如思路 / 分析 / 易错点 / 点睛
    namespace   TEXT NOT NULL,
    -- [字段注释] 命名空间内的字段名，同一题目同一命名空间内唯一
    field_key   TEXT NOT NULL,
    -- [字段注释] 补充字段的原文内容，允许 Markdown/LaTeX
    field_value TEXT NOT NULL,
    -- [字段注释] 同一题目补充内容的展示排序，数值越小越靠前
    sort_order  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (question_id, namespace, field_key)
);
-- [功能注释] 题目统计从表：与题目 1 对 1，记录被题目来源引用的次数，由触发器自动记账
CREATE TABLE question_statistics (
    question_id     TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE,
    -- [字段注释] 被题目来源引用的次数，由触发器在来源关系增删时自动加减
    reference_count INTEGER NOT NULL DEFAULT 0
);
-- [功能注释] 题目与考向关联表：题目直接挂靠考向，支撑按考向一键组卷与生成讲义
CREATE TABLE question_exam_map (
    question_id       TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    exam_direction_id INTEGER NOT NULL
                      REFERENCES dim_exam_directions(id) ON DELETE RESTRICT,
    PRIMARY KEY (question_id, exam_direction_id)
) WITHOUT ROWID;
-- [功能注释] 题目与知识点关联表：题目直接绑定底层概念，支撑概念级检索与统计
CREATE TABLE question_knowledge_map (
    question_id        TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    knowledge_point_id INTEGER NOT NULL
                       REFERENCES dim_knowledge_points(id) ON DELETE RESTRICT,
    PRIMARY KEY (question_id, knowledge_point_id)
) WITHOUT ROWID;
-- [功能注释] 题目来源关系：题目与题目来源多对多，承载题号与分值
CREATE TABLE question_source_map (
    question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
    source_id   INTEGER NOT NULL REFERENCES dim_sources(id) ON DELETE RESTRICT,
    -- [字段注释] 题目在该来源中的题号，可为空
    question_no TEXT,
    -- [字段注释] 该题在该来源中的分值，非负，默认 0
    score       REAL NOT NULL DEFAULT 0 CHECK (score >= 0),
    PRIMARY KEY (question_id, source_id)
) WITHOUT ROWID;
-- [功能注释] 学科思想字典：存学科思想名称与编码，供解析思想关联引用
CREATE TABLE dict_subject_thoughts (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 学科思想名称，展示给用户看的业务词汇，全局唯一
    name       TEXT NOT NULL UNIQUE,
    -- [字段注释] 学科思想编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 所属学科外键，区分数学思想、物理守恒思想、化学平衡思想等
    subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    -- [字段注释] 所属年级外键，全学段通用时留空，初高中特有思想填入对应年级
    grade_id   INTEGER REFERENCES dict_grades(id) ON DELETE RESTRICT
);
-- [功能注释] 解题方法字典：存解题方法名称与编码，供解析方法关联引用
CREATE TABLE dict_solution_methods (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 解题方法名称，展示给用户看的业务词汇，全局唯一
    name       TEXT NOT NULL UNIQUE,
    -- [字段注释] 解题方法编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 所属学科外键，区分数学、物理、化学等学科的方法体系
    subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    -- [字段注释] 所属年级外键，全学段通用时留空，初高中特有方法填入对应年级
    grade_id   INTEGER REFERENCES dict_grades(id) ON DELETE RESTRICT
);
-- [功能注释] 核心素养字典：存核心素养名称与编码，供解析素养关联引用
CREATE TABLE dict_core_competencies (
    id         INTEGER PRIMARY KEY,
    -- [字段注释] 核心素养名称，展示给用户看的业务词汇，全局唯一
    name       TEXT NOT NULL UNIQUE,
    -- [字段注释] 核心素养编码，系统底层唯一标识，不随名称更改
    code       TEXT NOT NULL UNIQUE,
    -- [字段注释] 排序序号，用于前端下拉框或列表的展示顺序，数值越小越靠前
    sort_order INTEGER NOT NULL DEFAULT 0,
    -- [字段注释] 所属学科外键，区分各学科核心素养体系
    subject_id INTEGER NOT NULL REFERENCES dict_subjects(id) ON DELETE RESTRICT,
    -- [字段注释] 所属年级外键，全学段通用时留空，初高中特有素养填入对应年级
    grade_id   INTEGER REFERENCES dict_grades(id) ON DELETE RESTRICT
);
-- [功能注释] 解析与学科思想关联表：解析与学科思想多对多，解析删除时级联清理
CREATE TABLE solution_thought_map (
    solution_id INTEGER NOT NULL
                REFERENCES question_solutions(id) ON DELETE CASCADE,
    thought_id  INTEGER NOT NULL
                REFERENCES dict_subject_thoughts(id) ON DELETE RESTRICT,
    PRIMARY KEY (solution_id, thought_id)
) WITHOUT ROWID;
-- [功能注释] 解析与解题方法关联表：解析与解题方法多对多，解析删除时级联清理
CREATE TABLE solution_method_map (
    solution_id INTEGER NOT NULL
                REFERENCES question_solutions(id) ON DELETE CASCADE,
    method_id   INTEGER NOT NULL
                REFERENCES dict_solution_methods(id) ON DELETE RESTRICT,
    PRIMARY KEY (solution_id, method_id)
) WITHOUT ROWID;
-- [功能注释] 解析与核心素养关联表：解析与核心素养多对多，解析删除时级联清理
CREATE TABLE solution_competency_map (
    solution_id   INTEGER NOT NULL
                  REFERENCES question_solutions(id) ON DELETE CASCADE,
    competency_id INTEGER NOT NULL
                  REFERENCES dict_core_competencies(id) ON DELETE RESTRICT,
    PRIMARY KEY (solution_id, competency_id)
) WITHOUT ROWID;

CREATE INDEX ix_dim_textbooks_subject ON dim_textbooks (subject_id);
CREATE INDEX ix_dim_textbooks_grade ON dim_textbooks (grade_id);
CREATE INDEX ix_dim_textbook_chapters_textbook
    ON dim_textbook_chapters (textbook_id);
CREATE INDEX ix_dim_textbook_chapters_parent ON dim_textbook_chapters (parent_id);
CREATE INDEX ix_dim_schools_short ON dim_schools (short_name);
CREATE INDEX ix_dim_schools_textbook ON dim_schools (textbook_id);
CREATE INDEX ix_dim_sources_grade ON dim_sources (grade_id);
CREATE INDEX ix_dim_sources_chapter ON dim_sources (chapter_id);
CREATE INDEX ix_dim_sources_school ON dim_sources (school_id);
CREATE INDEX ix_dim_knowledge_points_subject
    ON dim_knowledge_points (subject_id);
CREATE INDEX ix_dim_knowledge_points_grade
    ON dim_knowledge_points (grade_id);
CREATE INDEX ix_dim_knowledge_points_parent
    ON dim_knowledge_points (parent_id);
CREATE INDEX ix_dim_exam_directions_subject
    ON dim_exam_directions (subject_id);
CREATE INDEX ix_dim_exam_directions_grade
    ON dim_exam_directions (grade_id);
CREATE INDEX ix_dim_exam_directions_chapter
    ON dim_exam_directions (chapter_id);
CREATE INDEX ix_dict_subject_thoughts_subject
    ON dict_subject_thoughts (subject_id);
CREATE INDEX ix_dict_subject_thoughts_grade
    ON dict_subject_thoughts (grade_id);
CREATE INDEX ix_dict_solution_methods_subject
    ON dict_solution_methods (subject_id);
CREATE INDEX ix_dict_solution_methods_grade
    ON dict_solution_methods (grade_id);
CREATE INDEX ix_dict_core_competencies_subject
    ON dict_core_competencies (subject_id);
CREATE INDEX ix_dict_core_competencies_grade
    ON dict_core_competencies (grade_id);
CREATE INDEX ix_ingest_batches_status ON ingest_batches (status);
CREATE INDEX ix_raw_questions_batch ON raw_questions (batch_id);
CREATE INDEX ix_raw_questions_status ON raw_questions (status);
CREATE INDEX ix_raw_questions_content_hash ON raw_questions (content_hash);
CREATE INDEX ix_questions_subject ON questions (subject_id);
CREATE INDEX ix_questions_type ON questions (question_type_id);
CREATE INDEX ix_questions_difficulty ON questions (difficulty_id);
CREATE INDEX ix_questions_quality ON questions (quality_id);
CREATE INDEX ix_questions_raw ON questions (raw_id);
CREATE INDEX ix_questions_deleted ON questions (deleted_at);
CREATE INDEX ix_question_options_question ON question_options (question_id);
CREATE INDEX ix_question_images_question ON question_images (question_id);
CREATE INDEX ix_question_images_option ON question_images (option_id);
CREATE INDEX ix_question_answers_question ON question_answers (question_id);
CREATE INDEX ix_question_solutions_question ON question_solutions (question_id);
CREATE INDEX ix_question_supplements_question ON question_supplements (question_id);
CREATE INDEX ix_knowledge_exam_map_exam_direction
    ON knowledge_exam_map (exam_direction_id);
CREATE INDEX ix_question_exam_map_exam_direction
    ON question_exam_map (exam_direction_id);
CREATE INDEX ix_question_knowledge_map_knowledge_point
    ON question_knowledge_map (knowledge_point_id);
CREATE INDEX ix_question_source_map_source ON question_source_map (source_id);
CREATE INDEX ix_solution_thought_map_thought
    ON solution_thought_map (thought_id);
CREATE INDEX ix_solution_method_map_method
    ON solution_method_map (method_id);
CREATE INDEX ix_solution_competency_map_competency
    ON solution_competency_map (competency_id);

-- 外部内容 FTS5：仅索引题干；答案与解析位于从表，查重由 Python 层复核
CREATE VIRTUAL TABLE questions_fts USING fts5(
    stem,
    content = 'questions',
    content_rowid = 'rowid',
    tokenize = 'unicode61'
);

CREATE TRIGGER trg_questions_fts_insert AFTER INSERT ON questions BEGIN
    INSERT INTO questions_fts (rowid, stem)
    VALUES (new.rowid, new.stem);
END;

CREATE TRIGGER trg_questions_fts_delete AFTER DELETE ON questions BEGIN
    INSERT INTO questions_fts (questions_fts, rowid, stem)
    VALUES ('delete', old.rowid, old.stem);
END;

CREATE TRIGGER trg_questions_fts_update AFTER UPDATE OF stem ON questions BEGIN
    INSERT INTO questions_fts (questions_fts, rowid, stem)
    VALUES ('delete', old.rowid, old.stem);
    INSERT INTO questions_fts (rowid, stem)
    VALUES (new.rowid, new.stem);
END;

-- 统计从表自动记账：题目落库即初始化计数，来源关系增删即同步增减
CREATE TRIGGER trg_questions_statistics_init AFTER INSERT ON questions BEGIN
    INSERT INTO question_statistics (question_id, reference_count)
    VALUES (new.id, 0);
END;

CREATE TRIGGER trg_question_source_map_statistics_insert
AFTER INSERT ON question_source_map BEGIN
    UPDATE question_statistics
    SET reference_count = reference_count + 1
    WHERE question_id = new.question_id;
END;

CREATE TRIGGER trg_question_source_map_statistics_delete
AFTER DELETE ON question_source_map BEGIN
    UPDATE question_statistics
    SET reference_count = reference_count - 1
    WHERE question_id = old.question_id;
END;

PRAGMA user_version = 2;

COMMIT;

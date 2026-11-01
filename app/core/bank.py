"""插件题库服务：core-bank v0.6.3 七张关系表的读写适配层（对外唯一入口）。

为什么放在底座（而不是插件 JS 里）：
- 插件运行在沙箱 iframe 中，拿不到文件系统与数据库（AGENTS §2）；
- 插件又需要真题列表、年级/难度过滤与组卷取数，因此由底座提供一条
  **受控 Host API**，插件经舞台消息协议申请数据，宿主代为查询并回传。

存储层是 7 张关系表（schools / topics / questions / topic_notes / sources /
question_topics / question_sources + bank_meta），对外仍然只给
``schemas/question.json`` 的标准文档结构。两者的差异全部在 ``bank_codec.py`` 里抹平：

- ``extensions``：库内是有序数组 ``[{key,label,value}]``，契约是反向域名对象；
- ``answer``：库内是单个文本列（选择题存 "A,C"，非选择题存答案正文），契约是
  ``{kind, choice_keys/content, final}`` 对象；库内为 ``NULL`` 时出参**省略**该字段，
  不拿任何字母冒充答案；
- ``grade``：库内在 ``sources.grade``（主公 2026-10-23 裁定的落位），出参仍给顶层
  ``grade``，与 v0.6.2 的前端口径保持一致；
- ``taxonomy``：库内是 ``question_topics`` → ``topics`` 的物化路径树，出参按祖先名还原；
- ``images``：库内寄生在 ``extensions`` 的 core-bank 配图条目，出参回到顶层数组。

实现按域切成六块（PLUGIN_SPEC §2.8 的单文件上限口径，Python 侧同理）：

- ``bank_schema.py``    —— 库文件落点、建库与结构守卫、v0.8.2 升级、通用编解码原语与常量；
- ``bank_codec.py``     —— 表结构 ⇄ 契约文档的编解码与出参装配；
- ``bank_query.py``     —— 过滤装配、分页检索、大纲树、统计与 FTS 索引维护；
- ``bank_write.py``     —— 收题、落库、批量导入与建题；
- ``bank_dashboard.py`` —— 数据看板的只读聚合；
- ``bank_review.py``    —— 人工审核、改题与删题。

本文件只把六块的名字汇总成 ``app.core.bank`` 这一个入口：调用方（HTTP 路由、
其它 core 模块、测试）一律 ``from app.core import bank``，不需要知道里面切了几刀。

安全边界：
- 插件 ID 必须匹配反向域名；数据库文件路径由底座拼装，插件传不了任意路径；
- 全部过滤条件走参数绑定；表名、列名与层别码只从常量取，不接受插件输入；
- 单页最多 100 条，搜索词最多 100 字，避免一次把 456 题全倒进 iframe。

数据库随插件包分发：``plugins/<id>/bank/bank.db``。首次访问时由底座原子复制到
当前工作区的 ``data/banks/<id>.db``，之后只读取这份工作区副本。
"""

from __future__ import annotations

from app.core.bank_schema import (
    ASSEMBLE_CHUNK,
    BLOCKING_ISSUES,
    BankConflict,
    BankError,
    BankImportError,
    BankNotFound,
    CHOICE_TYPES,
    EXTENSION_LABELS,
    EXTENSION_ORDER,
    EXT_GRADE_KEY,
    EXT_IMAGES_KEY,
    EXT_MIGRATION_KEY,
    EXT_TAGS_KEY,
    EXT_TAXONOMY_KEY,
    LAYER_TAXONOMY_KEY,
    LOCAL_TZ,
    MAX_BASKET,
    MAX_PAGE_SIZE,
    MAX_QUESTION_SOURCES,
    MAX_SEARCH,
    MAX_SEARCH_NODES,
    MAX_TOPIC_IDS,
    PLUGIN_ID_RE,
    REQUIRED_TABLES,
    REVIEW_FLAGS,
    SCHEMA_VERSION,
    STORAGE_TYPES,
    STORAGE_YEAR_MAX,
    STORAGE_YEAR_MIN,
    TEXTBOOK_ID_RE,
    TOPIC_ID_RE,
    V082_NEW_TABLES,
    V082_NEW_TABLE_INDEXES,
    V082_TEXTBOOK_NAME,
    V082_TOPICS_DDL,
    V082_TOPICS_INDEXES,
    _asset_dirs,
    _check_structure,
    _copy_legacy_bank,
    _decode,
    _encode,
    _escape_like,
    _legacy_bank_path,
    _like,
    _new_table_ddl,
    _now,
    _placeholders,
    _schema_path,
    _seed_assets,
    _seed_lock,
    _seed_path,
    _structure_cache,
    _upgrade_if_older,
    _v082_verify,
    bank_db_path,
    connect,
    default_textbook_id,
    ensure_bank,
    init_bank,
    textbook_id_of,
    textbooks,
    upgrade_structure,
    validate_plugin_id,
)
from app.core.bank_codec import (
    _assemble,
    _document_from,
    _extension_value,
    _grade_from,
    _source_index,
    _taxonomy_from_links,
    _topic_index,
    answer_from_storage,
    answer_to_storage,
    extensions_to_array,
    extensions_to_object,
)
from app.core.bank_query import (
    _build_where,
    _flag_clause,
    _fts_clear,
    _fts_ready,
    _fts_remove,
    _fts_upsert,
    _grouped_counts,
    _search_extra_clause,
    _topic_name_match,
    _topic_subtree_sql,
    assemble_ids,
    export_documents,
    get_many,
    get_question,
    import_count,
    list_questions,
    metadata,
    question_sources,
    random_question,
    stats,
    topic_notes,
    topics,
)
from app.core.bank_write import (
    SOURCE_FIELDS,
    _clean_source_entry,
    _ensure_school,
    _ensure_source,
    _grade_of,
    _intake_document,
    _link_sources,
    _link_topics,
    _normalize_sources,
    _question_row,
    _remount_topics,
    _storage_ready,
    _wipe,
    _with_default_meta,
    _write_document,
    create_question,
    import_documents,
    import_questions,
    prepare_import_documents,
    upsert_school,
)
from app.core.bank_dashboard import (
    daily_counts,
    dashboard_stats,
)
from app.core.bank_review import (
    _strip_flags,
    delete_question,
    review_summary,
    update_question,
)

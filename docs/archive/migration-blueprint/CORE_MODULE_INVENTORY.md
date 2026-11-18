# app/core 现状清单（侦查底稿）

- 侦查日期：2026-11-17
- 代码基线：`main` @ `478b3ac`，以**当前工作树**为准（工作树有在途改动：`app/core/page_furniture.py`、`docs/AGENTS.md`、`tests/test_page_render.py`、`tools/textlayer_probe.py`，另有未跟踪的 `tools/onnx_probe.py`；本文未 stage、未改动任何 `.py`）。
- 规范依据：[AGENTS.md](AGENTS.md) §4 分层铁律（2026-11-17 主公裁最新版）。
- 扫描口径：对全仓 `app/`、`tests/`、`tools/`、`scripts/`、`examples/` 的 `.py` 做 AST 解析，统计 `app.core.<模块>` 的**去重引用文件数**；`from app.core import x` 与 `import app.core.x` 都计入。引用分布顺序为 **app / core / test / tools / scripts / examples**，其中 `core` 指 core 内部互相引用，`app` 指 core 之外的底座文件（`app/main.py`、`app/api/*`、`app/bank_engine/*`、`app/__init__.py`）。
- 行数口径与 `tests/test_file_size_contract.py` 一致：`len(text.splitlines())`。

## 1. 数字总览

| 指标 | 数量 | 说明 |
|---|---:|---|
| `app/core` 顶层 `.py` | 95 | 含 `__init__.py` |
| 顶层业务模块 | **94** | 不含 `__init__.py`，即本卡所说的「94 个模块」 |
| 已有子包业务模块 | 13 | `layout/` 6、`recognize/` 5、`providers/` 2；另有 2 个 `__init__.py` |
| 合计业务模块 | **107** | 94 顶层 + 13 子包 |
| 直接引用 core 的测试文件 | 93 / 111 | `tests/` 共 111 个文件 |
| 直接引用 core 的工具文件 | 44 / 58 | `tools/` 共 58 个 `.py` |
| 直接引用 core 的脚本文件 | 2 / 13 | `scripts/` 共 13 个 `.py` |
| core 之外的底座引用文件 | 24 | `app/main.py`、`app/api/*`、`app/bank_engine/*`、`app/__init__.py` |
| core 内部有互相引用的文件 | 83 / 94 | 其余 11 个顶层模块是叶子或仅被外部引用 |

引用枢纽 Top 20（入度 = 去重引用文件数）：

| 排名 | 模块 | 入度 | 分布 app/core/test/tools/scripts/examples | 角色 |
|---:|---|---:|---|---|
| 1 | `config` | 125 | 6/25/59/33/2/0 | 路径与配置唯一来源 |
| 2 | `wire` | 104 | 1/35/33/33/1/1 | JSON 文本唯一出入口 |
| 3 | `toml_io` | 77 | 2/7/29/37/1/1 | TOML 唯一出入口 |
| 4 | `bank` | 36 | 4/11/17/4/0/0 | 主库读写门面 |
| 5 | `manifests` | 28 | 1/4/19/2/2/0 | 插件/套件清单 |
| 6 | `plugins` | 24 | 2/5/16/1/0/0 | 插件发现与校验 |
| 7 | `pending_db` | 22 | 1/13/7/1/0/0 | 中转站库层 |
| 8 | `questions` | 21 | 5/11/3/2/0/0 | 题目仓储 |
| 9 | `security` | 18 | 14/0/4/0/0/0 | 写操作令牌 |
| 10 | `pending_bank` | 16 | 4/3/9/0/0/0 | 中转站门面 |
| 11 | `pending_assets` | 15 | 0/12/3/0/0/0 | 中转站物理文件层 |
| 12 | `bank_provider` | 13 | 3/7/2/1/0/0 | 活跃题库 provider 路由 |
| 13 | `pending_batches` | 13 | 0/6/7/0/0/0 | 批次与条目读写 |
| 14 | `pending_dedupe` | 13 | 1/4/8/0/0/0 | 中转站查重 |
| 15 | `ai_center` | 10 | 1/5/4/0/0/0 | AI 密钥池与任务指派 |
| 16 | `state_store` | 10 | 1/9/0/0/0/0 | 运行时状态读写 |
| 17 | `bank_schema` | 9 | 0/6/2/1/0/0 | 主库结构地基 |
| 18 | `contract` | 9 | 0/9/0/0/0/0 | 题目契约版本/难度 |
| 19 | `backup` | 7 | 1/2/4/0/0/0 | 备份组合根 |
| 20 | `bank_dedupe` / `plugin_state` / `plugin_update` / `question_contract` | 7 | — | 各自领域入口 |

## 2. 94 个顶层模块逐项清单

> 「职责」取模块 docstring 首行；「主要外部引用者」最多列 3 个（不含 core 内部），其余以「等 N 个」省略。

| 模块 | 行数 | 一句话职责 | 入度 | 分布 app/core/test/tools/scripts/examples | 主要外部引用者 |
|---|---:|---|---:|---|---|
| `ai_center` | 459 | AI 配置中心：多厂商密钥池 + 四任务指派。 | 10 | 1/5/4/0/0/0 | `app/api/ai_center.py`, `tests/test_ai_center.py`, `tests/test_ai_recognize.py` 等 5 个 |
| `ai_client` | 371 | OpenAI 兼容的大模型客户端（Provider 实现）。 | 5 | 1/4/0/0/0/0 | `app/api/agents.py` |
| `ai_recognize` | 362 | 单题 AI 识别（人机共驾 · 方案 A）。 | 3 | 1/1/1/0/0/0 | `app/api/ai_center.py`, `tests/test_ai_recognize.py` |
| `backup` | 102 | 当前工作区备份子系统：对外接口（组合根）。 | 7 | 1/2/4/0/0/0 | `app/api/settings.py`, `tests/test_backup_package.py`, `tests/test_backup_snapshot.py` 等 5 个 |
| `backup_codec` | 84 | 备份包压缩后端的兼容层：同一份包在 Python 3.10 ~ 3.14 之间都要能读写。 | 5 | 0/3/2/0/0/0 | `tests/test_backup_codec.py`, `tests/test_backup_package.py` |
| `backup_files` | 277 | 备份子系统的「路径与文件清单」层：什么该进包、什么绝不。 | 6 | 0/5/1/0/0/0 | `tests/test_backup_codec.py` |
| `backup_manifest` | 302 | 备份子系统的一致性快照与 manifest。 | 3 | 0/2/1/0/0/0 | `tests/test_backup_snapshot.py` |
| `backup_package` | 230 | 备份子系统的成品层：压缩打包、本地保留策略与清单读取。 | 1 | 0/1/0/0/0/0 | — |
| `backup_settings` | 112 | 备份子系统的本机配置：开关、本地目录、WebDAV 凭据。 | 2 | 0/2/0/0/0/0 | — |
| `bank` | 177 | 插件题库服务：core-bank v0.6.3 七张关系表的读写适配层（对外唯一入口）。 | 36 | 4/11/17/4/0/0 | `app/api/bank.py`, `app/api/pending.py`, `app/api/pending_approve_errors.py` 等 25 个 |
| `bank_codec` | 248 | core-bank 引擎的编解码层：七张关系表 ⇄ `app/core/question_contract.py` 标准文档。 | 5 | 0/5/0/0/0/0 | — |
| `bank_dashboard` | 84 | core-bank 引擎的看板口径：题数、录入节奏与近 N 日曲线。 | 1 | 0/1/0/0/0/0 | — |
| `bank_dedupe` | 455 | core-bank 查重引擎：只读扫描 + 收敛合并事务（军令 #18-终 阶段四）。 | 7 | 0/4/3/0/0/0 | `tests/test_bank_dedupe.py`, `tests/test_dedupe_fingerprint.py`, `tests/test_pending_dedupe_candidates.py` |
| `bank_fts` | 152 | 题干全文检索预研：SQLite FTS5 虚拟表 + 中文逐字切分。 | 6 | 0/2/3/1/0/0 | `tests/test_bank_dedupe.py`, `tests/test_bank_fts.py`, `tests/test_bank_search.py` 等 4 个 |
| `bank_provider` | 131 | 题库 provider 路由：底座认「当前活跃的题库插件」，不认死某个 ID。 | 13 | 3/7/2/1/0/0 | `app/api/bank.py`, `app/api/pending.py`, `app/api/workspaces.py` 等 6 个 |
| `bank_query` | 593 | core-bank 引擎的读路径：过滤条件装配、分页检索、大纲树与统计。 | 4 | 0/3/1/0/0/0 | `tests/test_plugin_suite.py` |
| `bank_review` | 182 | core-bank 引擎的审核与改删：待审标记、打标、改题与删题。 | 1 | 0/1/0/0/0/0 | — |
| `bank_schema` | 624 | core-bank 引擎的地基：库文件从哪来、结构怎么建怎么升、以及通用编解码原语。 | 9 | 0/6/2/1/0/0 | `tests/test_db_transaction_atomicity.py`, `tests/test_pending_api.py`, `tools/clear_all_questions.py` |
| `bank_transfer` | 127 | 题库批量导入导出：`.json` / `.zip` 题目包 ⇄ 题目标准结构。 | 2 | 1/0/1/0/0/0 | `app/api/bank.py`, `tests/test_bank_batch_io.py` |
| `bank_write` | 623 | core-bank 引擎的写路径：收题、落库、批量导入与建题。 | 2 | 0/2/0/0/0/0 | — |
| `basket` | 119 | 题篮：跨插件共享的组卷选题集合（宿主托管）。 | 2 | 1/0/0/1/0/0 | `app/api/bank.py`, `tools/bank_stress.py` |
| `commands` | 329 | 能力路由字典（Command Registry）：清单声明 → 宿主内存字典。 | 3 | 0/1/2/0/0/0 | `tests/test_command_hardening.py`, `tests/test_command_registry.py` |
| `config` | 182 | 全局配置。所有路径以仓库根目录为锚点，不依赖当前工作目录。 | 125 | 6/25/59/33/2/0 | `app/api/assets.py`, `app/api/plugins.py`, `app/api/workspace_rename.py` 等 100 个 |
| `contract` | 41 | 题目契约的版本与难度口径（叶子模块，不依赖 app.core 任何其他模块）。 | 9 | 0/9/0/0/0/0 | — |
| `contract_fields` | 93 | 契约字段校验原语：题目契约与来源契约共用，只产出可读错误、不抛异常。 | 1 | 0/1/0/0/0/0 | — |
| `db` | 184 | SQLite 连接与结构自举。 | 4 | 2/1/1/0/0/0 | `app/api/workspaces.py`, `app/main.py`, `tests/test_db_transaction_atomicity.py` |
| `dedupe_signature` | 540 | 查重判据的纯函数层：归一、四要素指纹、正文骨架、公式签名、置信度档位（军令 #32 · S5b 拆出）。 | 1 | 0/1/0/0/0/0 | — |
| `docx_classify` | 416 | Word 预分拣：只用标准库看清 docx 里到底有什么，不让内容静默消失。 | 2 | 0/1/1/0/0/0 | `tests/test_docx_classify.py` |
| `docx_omml` | 319 | OMML（Office Math Markup Language）→ LaTeX，只用标准库 ElementTree。 | 2 | 0/1/1/0/0/0 | `tests/test_docx_omml.py` |
| `exam_name` | 84 | 试卷名称拼装：只由 exams 的属性动态算出，任何表都不存冗余试卷名。 | 4 | 3/1/0/0/0/0 | `app/bank_engine/dao_questions.py`, `app/bank_engine/entry.py`, `app/bank_engine/migrate_v10.py` |
| `exam_source` | 72 | 结构化题目 → exam-zh 源码（方案 A 的底座侧套壳）。 | 2 | 0/1/1/0/0/0 | `tests/test_ai_recognize.py` |
| `host_restart` | 118 | 切库重启：让底座在新工作区的插件与配置下重新起来。 | 3 | 2/0/1/0/0/0 | `app/api/health.py`, `app/api/workspaces.py`, `tests/test_workspace_restart.py` |
| `ingest` | 376 | 拖入文件的分拣与解析：PDF / Word / TeX / MD / 图片 → 中转站里的一批待审题。 | 5 | 1/3/1/0/0/0 | `app/api/ingest.py`, `tests/test_ingest_scan.py` |
| `ingest_media` | 115 | OCR 与单文件分拣：图片认字、Word 取文本，PDF 只交原卷大图。 | 2 | 0/1/1/0/0/0 | `tests/test_ingest_scan.py` |
| `ingest_quality` | 94 | 本地极速提取的坏题体检：五特征判定，只报不改。 | 2 | 0/1/1/0/0/0 | `tests/test_ingest_triage.py` |
| `ingest_route` | 221 | 解析路由账本与自动切图（从 `ingest` 拆出；具体引擎在 layout/ 与 recognize/）。 | 5 | 0/1/4/0/0/0 | `tests/test_ingest_routing.py`, `tests/test_ingest_scan.py`, `tests/test_ingest_triage.py` 等 4 个 |
| `ingest_text` | 390 | 文本、Word 与题号切分：从字节到契约题目文档，不碰批次与网络。 | 2 | 0/2/0/0/0/0 | — |
| `latex_style_dict` | 506 | LaTeX 写法字典与两把尺子（军令 #32 · S1，底座纯函数，无 IO 无网络）。 | 4 | 0/3/1/0/0/0 | `tests/test_latex_style_dict.py` |
| `manifests` | 83 | 插件清单与套件清单的落点与读取。 | 28 | 1/4/19/2/2/0 | `app/api/plugins.py`, `scripts/check_plugin_index_parity.py`, `scripts/check_plugin_package.py` 等 24 个 |
| `meta_dict` | 389 | 工作区级元数据字典：学校、主场景与带权重的交叉标签。 | 4 | 1/3/0/0/0/0 | `app/api/meta.py` |
| `mineru_extract` | 157 | MinerU 兜底通道：纯扫描件没有文本层时，试一次云端 OCR。 | 2 | 0/1/1/0/0/0 | `tests/test_ingest_routing.py` |
| `models` | 64 | Pydantic 响应模型：题目单题与分页列表。 | 1 | 1/0/0/0/0/0 | `app/api/questions.py` |
| `page_furniture` | 218 | 全卷页眉页脚剥离：同一位置、同一文字跨页反复出现，才整行剔除。 | 2 | 0/1/1/0/0/0 | `tests/test_page_render.py` |
| `page_render` | 127 | 原卷页面图：把拖进来的每一份卷子变成审核台左栏能看的页面。 | 4 | 0/3/1/0/0/0 | `tests/test_page_render.py` |
| `page_render_common` | 48 | 页面渲染的共享常量与条目标签（page_render 家族内部使用）。 | 4 | 0/3/0/1/0/0 | `tools/textlayer_probe.py` |
| `page_render_cross` | 352 | 跨页题：续页归属与同题纵向拼接（决策台账 D15）。 | 1 | 0/0/1/0/0/0 | `tests/test_page_render.py` |
| `page_render_pdf` | 436 | PDF → 原卷页图、自动切图与词级文字兜底。 | 1 | 0/1/0/0/0/0 | — |
| `page_render_regions` | 466 | PDF 文本层 → 题块坐标：自动切分框的底账。 | 5 | 0/4/0/1/0/0 | `tools/textlayer_probe.py` |
| `page_render_text` | 146 | Word / 纯文本 → 一页页 SVG 文本还原图（纯标准库，不联网）。 | 1 | 0/1/0/0/0/0 | — |
| `pending_assets` | 396 | 中转站的物理文件层：暂存配图、原文件只读副本与入库时的搬迁。 | 15 | 0/12/3/0/0/0 | `tests/test_page_render.py`, `tests/test_pending_batch_delete.py`, `tests/test_pending_pool.py` |
| `pending_bank` | 639 | 中转站（待审核池）：录题端与主库之间的**批次制**物理隔离暂存。 | 16 | 4/3/9/0/0/0 | `app/api/ingest.py`, `app/api/meta.py`, `app/api/pending.py` 等 13 个 |
| `pending_bank_batches` | 475 | 中转站里「批次」这一层的生命周期：立批、挂原卷页图、整批删、剔重后收口。 | 4 | 0/2/2/0/0/0 | `tests/test_pending_batch_delete.py`, `tests/test_pending_purge.py` |
| `pending_batches` | 268 | 中转站的批次与条目读写：`batches` / `pending_questions` 两张表的账。 | 13 | 0/6/7/0/0/0 | `tests/test_page_render.py`, `tests/test_pending_api.py`, `tests/test_pending_batch_delete.py` 等 7 个 |
| `pending_compare` | 396 | 中转站的比对口径：四要素指纹、单条命中与软查重置信度（军令 #32 · S5b 拆出）。 | 2 | 0/2/0/0/0/0 | — |
| `pending_db` | 676 | 中转站的库层：独立 SQLite、号段、结构版本与字典基线。 | 22 | 1/13/7/1/0/0 | `app/api/pending.py`, `tests/test_page_render.py`, `tests/test_pending_api.py` 等 9 个 |
| `pending_dedupe` | 783 | 中转站的查重口径：与 core-bank 指纹引擎同源，但配图按**内容哈希**比。 | 13 | 1/4/8/0/0/0 | `app/api/pending.py`, `tests/test_dedupe_fingerprint.py`, `tests/test_pending_api.py` 等 9 个 |
| `pending_engine` | 47 | 中转站 → 题库引擎 v2 的入库分支：只做新题落库，旧主库的查重/覆盖不参与。 | 1 | 0/1/0/0/0/0 | — |
| `pending_finish` | 36 | 批次收尾：删掉池子里的那一条、批次记一笔、未审数归零就物理清理。 | 2 | 0/2/0/0/0/0 | — |
| `pending_groups` | 149 | 批次查重清单的归并与剔除计划（军令 #32 · S5b 拆出）。 | 1 | 0/1/0/0/0/0 | — |
| `pending_meta` | 496 | 中转站的公共元数据规则：标准名拼接、场景与学校 ID、以及向题目文档的同步。 | 4 | 0/4/0/0/0/0 | — |
| `pending_pool` | 773 | 重题池（军令 #32 · 第四步）：跨批次存活的重题候选，与四个裁决动作。 | 5 | 1/2/2/0/0/0 | `app/api/pending.py`, `tests/test_pending_api.py`, `tests/test_pending_pool.py` |
| `pinyin` | 74 | 汉字拼音首字母：给数据字典补一条「敲 J 出集合」的路。 | 4 | 0/3/1/0/0/0 | `tests/test_pinyin.py` |
| `plugin_download` | 120 | 按需下载单个插件 zip 包（在线安装的下载半步）。 | 3 | 1/1/1/0/0/0 | `app/api/plugins.py`, `tests/test_plugin_install_url.py` |
| `plugin_index` | 378 | 插件索引（本地 plugins.toml / 远端 TOML 或 JSON）的解析与按需拉取。 | 5 | 1/2/2/0/0/0 | `app/api/plugins.py`, `tests/test_plugin_index.py`, `tests/test_plugin_install_url.py` |
| `plugin_install` | 343 | 插件 zip 包的本机安装：校验、解压、落地 plugins/。 | 6 | 1/2/3/0/0/0 | `app/api/plugins.py`, `tests/test_plugin_install_url.py`, `tests/test_plugin_suite.py` 等 4 个 |
| `plugin_lifecycle` | 156 | 插件卸载：删代码目录；可选地连本地数据一起物理销毁。 | 2 | 1/0/1/0/0/0 | `app/api/plugins.py`, `tests/test_plugin_console.py` |
| `plugin_search` | 470 | 半自主插件扩展：在**用户已拉取的索引缓存**里搜索插件，并生成安装建议卡。 | 2 | 1/0/1/0/0/0 | `app/api/plugins.py`, `tests/test_plugin_index.py` |
| `plugin_sources` | 51 | 官方插件索引的国内可达镜像（2026-10-24 v0.5.2 军令）。 | 3 | 0/1/2/0/0/0 | `tests/test_plugin_index.py`, `tests/test_plugin_install_url.py` |
| `plugin_state` | 232 | 插件主机状态：启停、停用时间、自定义昵称与左栏文件夹树。 | 7 | 1/2/4/0/0/0 | `app/api/plugins.py`, `tests/test_host_prefs.py`, `tests/test_plugin_console.py` 等 5 个 |
| `plugin_suite` | 151 | 插件套件（suite.toml）与插件依赖声明（requires）的契约。 | 4 | 0/2/1/1/0/0 | `tests/test_plugin_suite.py`, `tools/build_plugin.py` |
| `plugin_update` | 741 | 双轨更新（PLUGIN_SPEC §1.7 / ADR-006）：插件热更新 + 底座自更新。 | 7 | 2/2/2/1/0/0 | `app/api/plugins.py`, `app/main.py`, `tests/test_plugin_update.py` 等 5 个 |
| `plugins` | 729 | 插件发现、清单校验与只读资产解析。 | 24 | 2/5/16/1/0/0 | `app/api/plugins.py`, `app/main.py`, `tests/test_bank_split.py` 等 19 个 |
| `pool_meta` | 131 | 重题池的元数据差异账（军令·查重三栏）。 | 1 | 0/1/0/0/0/0 | — |
| `pool_source` | 172 | 重题池的源码回写：老师在新题源码区的编辑只改题面四件。 | 1 | 0/1/0/0/0/0 | — |
| `provider` | 63 | AI Provider 抽象接口规范。 | 1 | 0/1/0/0/0/0 | — |
| `pwa` | 54 | PWA 可安装清单：数据类定义，路由按浏览器要求以 `application/manifest+json` 下发。 | 2 | 1/0/1/0/0/0 | `app/main.py`, `tests/test_pwa_contract.py` |
| `question_contract` | 450 | 题目交换契约：dataclass 是唯一事实来源。 | 7 | 0/1/4/0/1/1 | `examples/build_demo_plugin.py`, `scripts/check_plugin_index_parity.py`, `tests/test_editor_contract.py` 等 6 个 |
| `question_images` | 39 | 配图引用的安全判定与读路径派生字段的清洗。 | 1 | 0/1/0/0/0/0 | — |
| `question_parser` | 481 | 录题文本的纯逻辑清洗与解析（无 IO、无网络、无数据库）。 | 11 | 1/7/3/0/0/0 | `app/api/agents.py`, `tests/test_latex_style_dict.py`, `tests/test_question_parser.py` 等 4 个 |
| `questions` | 340 | 题目仓储：契约校验、行 ↔ 标准结构转换与 SQLite 读写。 | 21 | 5/11/3/2/0/0 | `app/api/bank.py`, `app/api/ingest.py`, `app/api/pending.py` 等 10 个 |
| `restore` | 532 | 当前工作区恢复：校验、覆盖前备份与可回滚落盘（军令 #17 第四步 + #34）。 | 4 | 1/0/3/0/0/0 | `app/api/settings.py`, `tests/test_backup_package.py`, `tests/test_backup_snapshot.py` 等 4 个 |
| `scan_text` | 378 | 扫描卷文字层 → 可渲染的 Markdown + LaTeX（纯函数，无 IO）。 | 2 | 0/1/1/0/0/0 | `tests/test_scan_text.py` |
| `security` | 109 | 本地写操作令牌。 | 18 | 14/0/4/0/0/0 | `app/api/ai_center.py`, `app/api/assets.py`, `app/api/bank.py` 等 18 个 |
| `startup_prefs` | 162 | 启动行为：老师选「打开软件先落在哪个界面」，选择落盘在当前工作区目录。 | 4 | 1/1/2/0/0/0 | `app/api/settings.py`, `tests/test_startup_prefs.py`, `tests/test_workspace_isolation.py` |
| `state_store` | 62 | 运行时状态的统一读写：新文件一律 TOML，旧 `.json` 首次读取即迁移。 | 10 | 1/9/0/0/0/0 | `app/api/workspaces.py` |
| `text_health` | 24 | 纯代码提取的文字体检：只判断「像不像乱码」，绝不自动调 AI。 | 2 | 0/1/1/0/0/0 | `tests/test_ingest_routing.py` |
| `tikz_render` | 257 | TikZ 源码 → 矢量 SVG：本地 LaTeX 引擎的受控渲染器。 | 5 | 2/2/1/0/0/0 | `app/api/bank_engine.py`, `app/api/tikz.py`, `tests/test_tikz_render.py` |
| `toml_io` | 147 | TOML 读写：全仓配置文件与运行时状态的唯一格式出入口。 | 77 | 2/7/29/37/1/1 | `app/api/settings.py`, `app/bank_engine/service.py`, `examples/build_demo_plugin.py` 等 70 个 |
| `ui_cards` | 137 | ui_json 富卡片契约：底座生成结构化卡片，前端负责渲染。 | 1 | 0/1/0/0/0/0 | — |
| `webdav` | 234 | WebDAV 备份客户端：整包 PUT，不做分片与断点续传。 | 2 | 1/0/1/0/0/0 | `app/api/settings.py`, `tests/test_webdav_backup.py` |
| `wire` | 47 | 对外 JSON 适配层：全仓唯一允许接触 JSON 文本的入口。 | 104 | 1/35/33/33/1/1 | `app/api/agents.py`, `examples/build_demo_plugin.py`, `scripts/check_plugin_index_parity.py` 等 69 个 |
| `workspace_bootstrap` | 164 | 工作区布局自举（军令 #34：插件全局化）。 | 3 | 2/0/1/0/0/0 | `app/api/workspaces.py`, `app/main.py`, `tests/test_workspace_isolation.py` |
| `workspace_paths` | 91 | 工作区物理路径与当前工作区指针（军令 #18 第三步）。 | 4 | 1/2/1/0/0/0 | `app/__init__.py`, `tests/test_workspace_isolation.py` |
| `workspace_removal` | 157 | 工作区删除兜底：整目录进系统回收站，并写审计日志（军令 #17 第五步）。 | 3 | 1/0/2/0/0/0 | `app/api/workspaces.py`, `tests/test_workspace_delete.py`, `tests/test_workspace_isolation.py` |

## 3. 已有子包 13 个模块

这三个子包是现有目录约定的先例，不是本次新增。

| 模块 | 行数 | 一句话职责 | 入度 | 主要外部引用者 |
|---|---:|---|---:|---|
| `layout.layout_cloud` | 144 | 云端版面兜底：把页图交给视觉模型，只换回题块坐标。 | 1 | — |
| `layout.layout_model_store` | 264 | 本地 YOLO 模型仓库：配置、硬件探底与后台镜像下载。 | 3 | `app/api/layout.py`, `tests/test_layout_models.py` |
| `layout.layout_python` | 178 | 纯本地版面探路：文本层坐标 → 单栏 / 双栏题块。 | 2 | `tests/test_layout_router.py` |
| `layout.layout_router` | 100 | 版面引擎总调度：只按顺序分发，不实现任何一种探测。 | 6 | `app/api/ingest.py`, `tests/test_ingest_triage.py`, `tests/test_layout_models.py` |
| `layout.layout_yolo` | 170 | 本地 YOLO 版面探路：本机 ONNX 瀑布（满血 > 量化 > 云端）。 | 2 | `tests/test_layout_models.py` |
| `layout.layout_yolo_runtime` | 245 | 本地 YOLO 的 ONNX 运行时：解码页图、前处理、推理与后处理。 | 2 | `tests/test_layout_models.py` |
| `providers.builtin` | 43 | 内置 Provider 配置档。 | 0 | 动态注册表扫描，无静态 import |
| `providers.local` | 26 | 本地模型 Provider 配置档（Ollama 等，预留位）。 | 0 | 动态注册表扫描，无静态 import |
| `recognize.recognize_ai` | 70 | 大模型识别：单题截图并发交给视觉模型，按局部或全量两种口径回填。 | 2 | `tests/test_ingest_triage.py` |
| `recognize.recognize_local` | 63 | 纯本地识别：题块文字 → 契约题目，外加一份坏题体检。 | 2 | — |
| `recognize.recognize_mineru` | 84 | MinerU 云端识别：一张单题截图一次请求，回填只动那一道。 | 2 | `tests/test_ingest_triage.py` |
| `recognize.recognize_router` | 97 | 识别引擎总调度：本地永远第一，之后按选择逐级降级。 | 5 | `app/api/ingest.py`, `tests/test_ingest_triage.py`, `tests/test_recognize_router.py` |
| `recognize.recognize_shared` | 163 | 识别引擎共用的小零件：取题图、拼契约题目、单题回填。 | 3 | — |

> 注：`app/core/recognize/` 当前**没有 `__init__.py`**（隐式命名空间包）；`layout/` 与 `providers/` 有 `__init__.py`。这是现状，不是建议。

## 4. 引用结构观察（只陈述现状）

1. **真正的全仓枢纽只有 3 个**：`config`（125）、`wire`（104）、`toml_io`（77）。它们服务于所有流程，任何迁移都必须先把它们钉死在基座。
2. **单点内部模块（入度 1，且只被 core 自己引用）**：`backup_package`、`bank_dashboard`、`bank_review`、`contract_fields`、`dedupe_signature`、`pending_engine`、`pending_groups`、`pool_meta`、`pool_source`、`provider`、`question_images`、`ui_cards`。这些模块移动时外部影响极小，但要注意其父模块的导入。
3. **只有测试在用的生产模块**：`page_render_cross`（入度 1，引用者是 `tests/test_page_render.py`，生产代码没有调用）。它是跨页拼接的存量实现，本次只记录，不判定去留。
4. **只被单个 app 文件引用的模块**：`models`（`app/api/questions.py`）、`pwa`（`app/main.py`）、`plugin_lifecycle`（`app/api/plugins.py`）、`plugin_search`（`app/api/plugins.py`）、`webdav`（`app/api/settings.py`）、`host_restart`（`app/api/health.py` / `app/api/workspaces.py`）。这些是「接口薄层」，移动时改一处 import 即可。
5. **被 core 之外反向引用的模块**：`exam_name` 被 `app/bank_engine/dao_questions.py`、`entry.py`、`migrate_v10.py` 直接引用；`config` / `toml_io` 被 `app/bank_engine/paths.py` / `service.py` 引用；`question_contract` / `toml_io` 被 `examples/` 与 `scripts/` 引用。移动这些模块必须同步改兄弟目录。
6. **12 个文件超过 500 行**（与 `test_file_size_contract.py` 的冻结台账逐字一致）：`pending_dedupe` 783、`pending_pool` 773、`plugin_update` 741、`plugins` 729、`pending_db` 676、`pending_bank` 639、`bank_schema` 624、`bank_write` 623、`bank_query` 593、`dedupe_signature` 540、`restore` 532、`latex_style_dict` 506。本次只记录，不拆。

## 5. 本次侦查的边界

- 没有修改任何 `.py`，没有移动文件，没有改 import，没有新建空目录，没有提交。
- 现状表基于当前工作树；工作树里 `page_furniture.py` 已被他人改动（行数由基线 201 变为当前 218），迁移时应以当次实测为准，不要沿用本文行数做冻结依据。
- 目标树与风险清单见 `CORE_TARGET_TREE.md`、`CORE_REFACTOR_RISKS.md`。

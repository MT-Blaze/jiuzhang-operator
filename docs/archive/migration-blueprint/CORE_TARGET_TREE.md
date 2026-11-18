# app/core 目标目录树（流程 → 类）

- 编制日期：2026-11-18
- 规范依据：[AGENTS.md](AGENTS.md) §4 分层铁律（2026-11-17 主公裁最终版）。
- 覆盖范围：`app/core` 现有 **107 个业务模块**（94 个顶层 + `layout/` 6 + `recognize/` 5 + `providers/` 2），全部映射，无一遗漏。
- 本文只是归位蓝图：**没有移动任何文件、没有改任何 import、没有建任何目录**。

---

## 0. 先划地基：必须留在 `app/core` 的模块

> 地基划错，后面全白干。所以先把「不管怎么分流程都不许动」的部分钉死。

### 0.1 判定标准（三条同时满足才算底座）

1. **横切**：不止一个流程在用，且不是「碰巧被抄了一次」，而是架构上必须共用。
2. **无业务语义**：不表达题目、批次、插件、备份等任何一条业务流的概念；换掉业务需求它仍然存在。
3. **被依赖方向干净**：它自己不反向依赖业务模块（允许依赖同层底座）。

三条缺一，就不进底座。宁可在流程里多一个文件，也不把业务塞进 core 根。

### 0.2 留在 `app/core/` 根目录的 10 个模块

| 模块 | 行数 | 底座类别 | 为什么必须留 | 关键证据 |
|---|---:|---|---|---|
| `config.py` | 182 | 配置 / 路径 | 全仓路径唯一锚点，禁止依赖当前工作目录（AGENTS §4） | 入度 125，覆盖 app/core/test/tools/scripts |
| `workspace_paths.py` | 91 | 路径 | 当前工作区指针；`app/__init__.py` 在加载 `app.main` 之前就要用它找 `.env` | 启动链最前置依赖 |
| `db.py` | 184 | 存储 | 主库 SQLite 连接与结构自举 | `app/main.py`、`app/api/workspaces.py` |
| `security.py` | 109 | 安全 | 本地写操作令牌，所有写接口共用 | 14 个 `app/api/*` 直接引用 |
| `wire.py` | 47 | 序列化边界 | 全仓唯一允许接触 JSON 文本的入口 | 入度 104 |
| `toml_io.py` | 147 | 序列化边界 | 全仓 TOML 读写唯一出入口 | 入度 77 |
| `state_store.py` | 62 | 运行时状态 | 跨流程的运行时状态读写（AI 指派、题库 provider、插件搜索、工作区） | 入度 10，分布在 4 条以上流程 |
| `contract.py` | 41 | 契约 | 题目契约版本与难度口径，叶子模块 | 入度 9，全是 core 内部契约/引擎 |
| `contract_fields.py` | 93 | 契约 | 契约字段校验原语，题目契约与来源契约共用 | `question_contract` 直接依赖 |
| `question_contract.py` | 450 | 契约 | 题目在底座、插件、导入导出之间流转的唯一标准结构（AGENTS §3） | `bank_codec`、示例、脚本、测试 |

**`__init__.py` 原地不动。** 目标树里的 `app/core/` 根仍只放这 10 个业务模块，不建 `base/`、`common/`、`shared/` 之类目录——那会把「底座」本身变成垃圾桶。

### 0.3 底座内部依赖 DAG（无环）

```
workspace_paths   wire   toml_io   contract   contract_fields     ← L0 叶子
      ↑             ↑        ↑          ↑            ↑
    config          └── state_store ────┘      question_contract
      ↑
  security / db
```

逐条核实过的边（全部是顶层导入）：

- `config.py` → `workspace_paths.py`
- `security.py` → `config.py`
- `db.py` → `config.py`、`contract.py`
- `state_store.py` → `toml_io.py`、`wire.py`
- `question_contract.py` → `contract.py`、`contract_fields.py`
- `wire.py`、`toml_io.py`、`contract.py`、`contract_fields.py`、`workspace_paths.py` 不导入任何 core 模块

底座**没有任何一条边指向业务模块**，这是它成立的前提。

### 0.4 被拒绝的底座候选（看似该留，其实该归流程）

| 候选 | 看似底座的理由 | 为什么不留 | 去向 |
|---|---|---|---|
| `models.py` | Pydantic 响应模型，像通用模型 | 只服务题目单题/分页响应，唯一外部引用是 `app/api/questions.py` | `bank/models.py` |
| `pwa.py` | 应用级 manifest | 只服务启动与工作区入口，外部只有 `app/main.py` | `workspace/startup/pwa.py` |
| `ui_cards.py` | UI 卡片契约，像通用协议 | 只被插件搜索用于生成安装建议卡 | `plugins/contract/cards.py` |
| `provider.py` | AI Provider 抽象接口 | 只被 `ai_client` 使用，是 AI 流程内部抽象 | `ai/platform/provider.py` |
| `commands.py` | 能力路由字典，像宿主级注册表 | 只服务插件清单声明的命令 | `plugins/contract/commands.py` |
| `manifests.py` / `plugin_suite.py` | 清单契约，像跨流程协议 | 只服务插件与套件 | `plugins/contract/` |
| `exam_name.py` | 命名规则，像通用工具 | 只由 exams 属性拼试卷名，服务题库 | `bank/exam_name.py` |
| `meta_dict.py` | 工作区级字典，像基础数据 | 依赖 `pending_db`、`ai_client`、`questions`，是业务数据字典 | `pending/meta/dictionary.py` |
| `basket.py` | 跨插件共享，像总线 | 本质是组卷选题集合，归题库宿主服务 | `bank/basket.py` |
| `question_images.py` / `pinyin.py` / `question_parser.py` / `latex_style_dict.py` / `scan_text.py` / `text_health.py` / `tikz_render.py` | 纯函数、无 IO，像工具库 | 全是题目内容领域能力（配图、拼音、解析、写法、扫描文本、体检、TikZ），不是基础设施 | `content/` |
| `backup_settings.py` | 配置，像全局配置 | 只属于备份子系统 | `backup/settings.py` |
| `startup_prefs.py` | 启动行为，像宿主配置 | 只服务「打开软件落在哪个界面」，归工作区启动 | `workspace/startup/` |

### 0.5 明确不建 `logging.py`

全仓日志统一用标准库 `logging.getLogger(__name__)`。core 里再加一层日志模块只会制造新的横切依赖和循环风险，不列入底座，也不允许新模块以「方便打日志」为由新增。

---

## 1. 流程划分总表

第一层按**流程**分：一条流程 = 老师的一次完整业务动作，有明确起点与终点。共 8 条流程 + 1 个底座层。

| 流程 | 一句话边界 | 模块数 | 主要入口（core 之外） |
|---|---|---:|---|
| **底座（core 根）** | 配置、路径、存储、安全、序列化、契约 | 10 | 全仓 |
| `content/` | 题目内容的纯逻辑：解析、清洗、写法、拼音、配图、TikZ、文字体检 | 7 | `app/api/agents.py`、bank/pending/ingest |
| `ai/` | AI 配置与单题识别：密钥池、任务指派、Provider、识别回填 | 7 | `app/api/ai_center.py`、`app/api/agents.py` |
| `ingest/` | 文件进站：分拣、取样、出页图、版面、识别，产出中转站待审题 | 26 | `app/api/ingest.py` |
| `pending/` | 中转站：批次暂存、查重、重题池、元数据，直到入库或删除 | 15 | `app/api/ingest.py`、`app/api/pending.py`、`app/api/meta.py` |
| `bank/` | 主库：core-bank v0.6.3 七张表的读写、审核、查重、导入导出 | 16 | `app/api/bank.py`、`app/api/questions.py`、`app/bank_engine/*` |
| `plugins/` | 插件宿主：发现、契约、安装/更新/卸载、索引与搜索 | 13 | `app/api/plugins.py`、`app/main.py` |
| `backup/` | 工作区备份与恢复：打包、清单、WebDAV、回滚落盘 | 8 | `app/api/settings.py` |
| `workspace/` | 工作区：启动落点、切库重启、PWA、布局自举、删除兜底 | 5 | `app/api/workspaces.py`、`app/api/health.py`、`app/main.py` |

**计数核对：10 + 7 + 7 + 26 + 15 + 16 + 13 + 8 + 5 = 107。**

流程之间**不是随便画的**：每条流程都能在 `app/api/` 找到对应的对外入口，且流程内模块只为这条入口服务。反过来，`app/api/` 的一个路由文件可能调用多条流程（如 `ingest.py` 同时调 `ingest` 与 `pending`），这属于流程编排，不改变模块归属。

### 1.1 流程依赖方向（已逐条核实）

```
content ──→ 底座
ai      ──→ content, 底座
bank    ──→ content, 底座, plugins        （bank_provider → plugins.discover_plugins，顶层）
pending ──→ bank, ai, content, 底座       （meta_dict → ai_client；pending_db → bank）
ingest  ──→ pending, content, 底座        （page_render → pending_assets）
workspace ─→ bank, plugins, 底座          （workspace_bootstrap → bank_provider/plugin_*）
backup  ──→ 底座
plugins ⇢  bank                            （仅 plugins.py:593 函数内导入 bank_provider）
```

唯一需要盯住的环是 `bank ↔ plugins`：`bank_provider` 顶层导入 `plugins`，`plugins` 只在函数体内导入 `bank_provider`。**迁移时必须保持这个局部导入**，不许「顺手」提到文件顶部。

---

## 2. 目标树全图

注释 `←` 表示现有文件来源；同名移动不额外标注。每个包都带 `__init__.py`（内容只放模块 docstring，不做 re-export）。

```
app/core/
├── __init__.py
│
├── config.py                    ← 原地
├── workspace_paths.py           ← 原地
├── db.py                        ← 原地
├── security.py                  ← 原地
├── wire.py                      ← 原地
├── toml_io.py                   ← 原地
├── state_store.py               ← 原地
├── contract.py                  ← 原地
├── contract_fields.py           ← 原地
├── question_contract.py         ← 原地
│
├── content/                     （7）
│   ├── __init__.py
│   ├── question_parser.py
│   ├── question_images.py
│   ├── latex_style_dict.py
│   ├── scan_text.py
│   ├── text_health.py
│   ├── pinyin.py
│   └── tikz_render.py
│
├── ai/                          （7）
│   ├── __init__.py
│   ├── platform/
│   │   ├── __init__.py
│   │   ├── center.py            ← ai_center.py
│   │   ├── client.py            ← ai_client.py
│   │   └── provider.py          ← provider.py
│   ├── recognition/
│   │   ├── __init__.py
│   │   ├── recognize.py         ← ai_recognize.py
│   │   └── exam_source.py
│   └── providers/
│       ├── __init__.py          ← providers/__init__.py（动态注册表，原样搬）
│       ├── builtin.py           ← providers/builtin.py
│       └── local.py             ← providers/local.py
│
├── ingest/                      （26）
│   ├── __init__.py
│   ├── service.py               ← ingest.py
│   ├── route.py                 ← ingest_route.py
│   ├── quality.py               ← ingest_quality.py
│   ├── intake/
│   │   ├── __init__.py
│   │   ├── media.py             ← ingest_media.py
│   │   ├── text.py              ← ingest_text.py
│   │   ├── docx_classify.py
│   │   └── docx_omml.py
│   ├── render/
│   │   ├── __init__.py
│   │   ├── service.py           ← page_render.py
│   │   ├── common.py            ← page_render_common.py
│   │   ├── pdf.py               ← page_render_pdf.py
│   │   ├── text.py              ← page_render_text.py
│   │   ├── regions.py           ← page_render_regions.py
│   │   ├── cross.py             ← page_render_cross.py
│   │   └── furniture.py         ← page_furniture.py
│   ├── layout/
│   │   ├── __init__.py
│   │   ├── router.py            ← layout/layout_router.py
│   │   ├── python.py            ← layout/layout_python.py
│   │   ├── yolo.py              ← layout/layout_yolo.py
│   │   ├── yolo_runtime.py      ← layout/layout_yolo_runtime.py
│   │   ├── cloud.py             ← layout/layout_cloud.py
│   │   └── model_store.py       ← layout/layout_model_store.py
│   └── recognize/
│       ├── __init__.py          （现有 recognize/ 无 __init__.py，迁移时补）
│       ├── router.py            ← recognize/recognize_router.py
│       ├── local.py             ← recognize/recognize_local.py
│       ├── ai.py                ← recognize/recognize_ai.py
│       ├── mineru.py            ← recognize/recognize_mineru.py
│       ├── mineru_extract.py
│       └── shared.py            ← recognize/recognize_shared.py
│
├── pending/                     （15）
│   ├── __init__.py
│   ├── service.py               ← pending_bank.py
│   ├── db.py                    ← pending_db.py
│   ├── assets.py                ← pending_assets.py
│   ├── batch/
│   │   ├── __init__.py
│   │   ├── batches.py           ← pending_batches.py
│   │   ├── bank_batches.py      ← pending_bank_batches.py
│   │   ├── finish.py            ← pending_finish.py
│   │   └── engine.py            ← pending_engine.py
│   ├── dedupe/
│   │   ├── __init__.py
│   │   ├── engine.py            ← pending_dedupe.py
│   │   ├── compare.py           ← pending_compare.py
│   │   └── groups.py            ← pending_groups.py
│   ├── pool/
│   │   ├── __init__.py
│   │   ├── service.py           ← pending_pool.py
│   │   ├── meta.py              ← pool_meta.py
│   │   └── source.py            ← pool_source.py
│   └── meta/
│       ├── __init__.py
│       ├── rules.py             ← pending_meta.py
│       └── dictionary.py        ← meta_dict.py
│
├── bank/                        （16）
│   ├── __init__.py
│   ├── service.py               ← bank.py
│   ├── provider.py              ← bank_provider.py
│   ├── questions.py
│   ├── basket.py
│   ├── exam_name.py
│   ├── models.py
│   └── engine/
│       ├── __init__.py
│       ├── schema.py            ← bank_schema.py
│       ├── codec.py             ← bank_codec.py
│       ├── query.py             ← bank_query.py
│       ├── write.py             ← bank_write.py
│       ├── review.py            ← bank_review.py
│       ├── dashboard.py         ← bank_dashboard.py
│       ├── fts.py               ← bank_fts.py
│       ├── dedupe.py            ← bank_dedupe.py
│       ├── dedupe_signature.py
│       └── transfer.py          ← bank_transfer.py
│
├── plugins/                     （13）
│   ├── __init__.py
│   ├── registry.py              ← plugins.py
│   ├── state.py                 ← plugin_state.py
│   ├── contract/
│   │   ├── __init__.py
│   │   ├── manifests.py
│   │   ├── suite.py             ← plugin_suite.py
│   │   ├── commands.py
│   │   └── cards.py             ← ui_cards.py
│   ├── lifecycle/
│   │   ├── __init__.py
│   │   ├── install.py           ← plugin_install.py
│   │   ├── download.py          ← plugin_download.py
│   │   ├── update.py            ← plugin_update.py
│   │   └── uninstall.py         ← plugin_lifecycle.py
│   └── index/
│       ├── __init__.py
│       ├── catalog.py           ← plugin_index.py
│       ├── sources.py           ← plugin_sources.py
│       └── search.py            ← plugin_search.py
│
├── backup/                      （8）
│   ├── __init__.py
│   ├── service.py               ← backup.py
│   ├── settings.py              ← backup_settings.py
│   ├── restore.py
│   ├── webdav.py
│   └── package/
│       ├── __init__.py
│       ├── codec.py             ← backup_codec.py
│       ├── files.py             ← backup_files.py
│       ├── manifest.py          ← backup_manifest.py
│       └── package.py           ← backup_package.py
│
└── workspace/                   （5）
    ├── __init__.py
    ├── startup/
    │   ├── __init__.py
    │   ├── startup_prefs.py
    │   ├── host_restart.py
    │   └── pwa.py
    └── lifecycle/
        ├── __init__.py
        ├── bootstrap.py         ← workspace_bootstrap.py
        └── removal.py           ← workspace_removal.py
```

> 目标树中的 `__init__.py` 是迁移时需要补的包标记文件，不计入 107 个业务模块。
> `ingest/recognize/` 目标上补 `__init__.py`：现有 `app/core/recognize/` 是隐式命名空间包，补普通空包标记更稳；迁移后必须跑识别链路单测确认动态/相对导入无变化。

---

## 3. 改名对照表（只列文件名发生变化者）

同路径同名的文件不列；按目标树即可核对。

| 现路径 | 目标路径 | 行数 |
|---|---|---:|
| `ai_center.py` | `ai/platform/center.py` | 459 |
| `ai_client.py` | `ai/platform/client.py` | 371 |
| `ai_recognize.py` | `ai/recognition/recognize.py` | 362 |
| `ingest.py` | `ingest/service.py` | 376 |
| `ingest_route.py` | `ingest/route.py` | 221 |
| `ingest_quality.py` | `ingest/quality.py` | 94 |
| `ingest_media.py` | `ingest/intake/media.py` | 115 |
| `ingest_text.py` | `ingest/intake/text.py` | 390 |
| `page_render.py` | `ingest/render/service.py` | 127 |
| `page_render_common.py` | `ingest/render/common.py` | 48 |
| `page_render_pdf.py` | `ingest/render/pdf.py` | 436 |
| `page_render_text.py` | `ingest/render/text.py` | 146 |
| `page_render_regions.py` | `ingest/render/regions.py` | 466 |
| `page_render_cross.py` | `ingest/render/cross.py` | 352 |
| `page_furniture.py` | `ingest/render/furniture.py` | 218 |
| `layout/layout_router.py` | `ingest/layout/router.py` | 100 |
| `layout/layout_python.py` | `ingest/layout/python.py` | 178 |
| `layout/layout_yolo.py` | `ingest/layout/yolo.py` | 170 |
| `layout/layout_yolo_runtime.py` | `ingest/layout/yolo_runtime.py` | 245 |
| `layout/layout_cloud.py` | `ingest/layout/cloud.py` | 144 |
| `layout/layout_model_store.py` | `ingest/layout/model_store.py` | 264 |
| `recognize/recognize_router.py` | `ingest/recognize/router.py` | 97 |
| `recognize/recognize_local.py` | `ingest/recognize/local.py` | 63 |
| `recognize/recognize_ai.py` | `ingest/recognize/ai.py` | 70 |
| `recognize/recognize_mineru.py` | `ingest/recognize/mineru.py` | 84 |
| `recognize/recognize_shared.py` | `ingest/recognize/shared.py` | 163 |
| `pending_bank.py` | `pending/service.py` | 639 |
| `pending_db.py` | `pending/db.py` | 676 |
| `pending_assets.py` | `pending/assets.py` | 396 |
| `pending_batches.py` | `pending/batch/batches.py` | 268 |
| `pending_bank_batches.py` | `pending/batch/bank_batches.py` | 475 |
| `pending_finish.py` | `pending/batch/finish.py` | 36 |
| `pending_engine.py` | `pending/batch/engine.py` | 47 |
| `pending_dedupe.py` | `pending/dedupe/engine.py` | 783 |
| `pending_compare.py` | `pending/dedupe/compare.py` | 396 |
| `pending_groups.py` | `pending/dedupe/groups.py` | 149 |
| `pending_pool.py` | `pending/pool/service.py` | 773 |
| `pool_meta.py` | `pending/pool/meta.py` | 131 |
| `pool_source.py` | `pending/pool/source.py` | 172 |
| `pending_meta.py` | `pending/meta/rules.py` | 496 |
| `meta_dict.py` | `pending/meta/dictionary.py` | 389 |
| `bank.py` | `bank/service.py` | 177 |
| `bank_provider.py` | `bank/provider.py` | 131 |
| `bank_schema.py` | `bank/engine/schema.py` | 624 |
| `bank_codec.py` | `bank/engine/codec.py` | 248 |
| `bank_query.py` | `bank/engine/query.py` | 593 |
| `bank_write.py` | `bank/engine/write.py` | 623 |
| `bank_review.py` | `bank/engine/review.py` | 182 |
| `bank_dashboard.py` | `bank/engine/dashboard.py` | 84 |
| `bank_fts.py` | `bank/engine/fts.py` | 152 |
| `bank_dedupe.py` | `bank/engine/dedupe.py` | 455 |
| `bank_transfer.py` | `bank/engine/transfer.py` | 127 |
| `plugins.py` | `plugins/registry.py` | 729 |
| `plugin_state.py` | `plugins/state.py` | 232 |
| `plugin_suite.py` | `plugins/contract/suite.py` | 151 |
| `ui_cards.py` | `plugins/contract/cards.py` | 137 |
| `plugin_install.py` | `plugins/lifecycle/install.py` | 343 |
| `plugin_download.py` | `plugins/lifecycle/download.py` | 120 |
| `plugin_update.py` | `plugins/lifecycle/update.py` | 741 |
| `plugin_lifecycle.py` | `plugins/lifecycle/uninstall.py` | 156 |
| `plugin_index.py` | `plugins/index/catalog.py` | 378 |
| `plugin_sources.py` | `plugins/index/sources.py` | 51 |
| `plugin_search.py` | `plugins/index/search.py` | 470 |
| `backup.py` | `backup/service.py` | 102 |
| `backup_settings.py` | `backup/settings.py` | 112 |
| `backup_codec.py` | `backup/package/codec.py` | 84 |
| `backup_files.py` | `backup/package/files.py` | 277 |
| `backup_manifest.py` | `backup/package/manifest.py` | 302 |
| `backup_package.py` | `backup/package/package.py` | 230 |
| `workspace_bootstrap.py` | `workspace/lifecycle/bootstrap.py` | 164 |
| `workspace_removal.py` | `workspace/lifecycle/removal.py` | 157 |

同名移动（不在此表）共 **26** 个，逐个点名以便核对：

- `content/` 7 个（全部同名）
- `bank/questions.py`、`bank/basket.py`、`bank/exam_name.py`、`bank/models.py`（4）
- `backup/restore.py`、`backup/webdav.py`（2）
- `workspace/startup/startup_prefs.py`、`host_restart.py`、`pwa.py`（3）
- `ai/platform/provider.py`、`ai/recognition/exam_source.py`、`ai/providers/builtin.py`、`ai/providers/local.py`（4）
- `ingest/intake/docx_classify.py`、`docx_omml.py`、`ingest/recognize/mineru_extract.py`（3）
- `plugins/contract/manifests.py`、`plugins/contract/commands.py`（2）
- `bank/engine/dedupe_signature.py`（1）

核对等式：**底座原地 10 + 改名移动 71 + 同名移动 26 = 107**。

---

## 4. 每一层为什么这么切（按最终 2×2 规则逐目录过一遍）

规则复述：**每一层用同一个标准——问「这一层里的东西，还能按什么差异分开」。按某个维度能分出 ≥2 组、且每组 ≥2 个，才有资格继续开层；只要出现「一格只有一个文件」，就不切，平铺。** 另外：一个模块只能归一个流程，不许设「公共」目录。

### 4.1 `app/core` 根层

- 先按「流程 vs 底座」分：8 条流程（每组 ≥2 个模块）+ 1 个底座组（10 个）。
- 有人会问：底座这 10 个为什么不按「配置 / 存储 / 安全 / 契约」再分？试切结果：配置路径 2、存储序列化 4、安全 **1**、契约 3——安全出现单格，不切，平铺。
- 也不设 `app/core/base/`：底座留在 core 根，语义就是「这一层是地基」；再套一层目录只会让 core 根变成流程目录 + 一个巨型公共桶，正是要避免的东西。

### 4.2 `content/`（7 个，平铺）

候选维度是「处理环节」：

| 候选组 | 文件 | 个数 |
|---|---|---:|
| 解析/清洗 | `question_parser`, `scan_text` | 2 |
| 写法 | `latex_style_dict` | 1 |
| 文字体检 | `text_health` | 1 |
| 配图 | `question_images` | 1 |
| 拼音 | `pinyin` | 1 |
| 渲染 | `tikz_render` | 1 |

六组里四组是单文件，按规则不切，平铺。`pinyin` 虽然被 bank 和 pending 同时使用，但它是内容领域的基础函数，不是跨流程基础设施；它的使用者都指向 content，方向干净。

### 4.3 `ai/`（7 个，切 3 组）

| 类 | 文件 | 个数 | 差异 |
|---|---|---:|---|
| `platform/` | center, client, provider | 3 | AI 运行平台：密钥池/任务指派、客户端、Provider 接口 |
| `recognition/` | recognize, exam_source | 2 | 单题识别与 exam-zh 源码套壳 |
| `providers/` | builtin, local（+ 动态注册表 `__init__`） | 2 | 两种 Provider 配置档，多实现并存 |

3/2/2，全部 ≥2，切分成立。

**红线：`providers/` 的 `__init__.py` 用 `pkgutil.iter_modules` 扫描同目录并逐个 `import_module`，再调用 `profiles()`。** 因此：

- `providers/` 里**只能**放实现了 `profiles()` 的配置档；
- `provider.py`（抽象接口）绝不能放进 `providers/`，否则会被注册表当成配置档导入；
- 迁移后目录名变了，但注册表用的是 `__name__`，逻辑不用改。

### 4.4 `ingest/`（26 个，切 5 组）

| 类 | 文件 | 个数 | 差异 |
|---|---|---:|---|
| 根（流程入口） | service, route, quality | 3 | 进站总调度、解析路由账本、坏题体检 |
| `intake/` | media, text, docx_classify, docx_omml | 4 | 取样：图片/Word 取文本、docx 分拣、OMML 转 LaTeX |
| `render/` | service, common, pdf, text, regions, cross, furniture | 7 | 原卷出图：页面图、PDF/文本两种来源、题块坐标、跨页、页眉页脚 |
| `layout/` | router, python, yolo, yolo_runtime, cloud, model_store | 6 | 版面探测：多种实现并存（纯文本层 / 本地 YOLO / 云端）+ 模型仓库 |
| `recognize/` | router, local, ai, mineru, mineru_extract, shared | 6 | 识别：本地 / 视觉大模型 / MinerU 三种实现 + 兜底 + 共用零件 |

3/4/7/6/6，全部 ≥2，切分成立。

**为什么根层不再拆？** 试按「编排 / 质检」切：service+route = 2，quality = 1，出现单格，按规则平铺。

**为什么 `render/` 不再拆？** 试按「PDF / Word 文本 / 跨页 / 页眉页脚 / 共用」切：pdf+regions = 2，text = 1，cross = 1，furniture = 1，common = 1，四个单格，平铺。注意 `regions` 虽然服务 PDF，但它是「文本层 → 题块坐标」的独立底账，和 `pdf` 放同一层即可。

**为什么 `layout/`、`recognize/` 可以单独成类？** 它们正是「同一件事有多实现」的典型：版面有纯本地/ONNX/云端，识别有本地/大模型/MinerU；2×2 规则和主公举的「页眉页脚多格式」是同一个道理。

### 4.5 `pending/`（15 个，切 5 组）

| 类 | 文件 | 个数 | 差异 |
|---|---|---:|---|
| 根（流程入口） | service, db, assets | 3 | 中转站门面、独立库层、物理文件层 |
| `batch/` | batches, bank_batches, finish, engine | 4 | 批次读写、批次生命周期、收尾、入库 |
| `dedupe/` | engine, compare, groups | 3 | 查重引擎、比对口径、归并计划 |
| `pool/` | service, meta, source | 3 | 重题池、元数据差异账、源码回写 |
| `meta/` | rules, dictionary | 2 | 中转站元数据规则、工作区字典 |

3/4/3/3/2，全部 ≥2，切分成立。

**根层为什么不拆？** service / db / assets 各是一种职责，任一组都是单文件，平铺。
**`batch/` 为什么不按「读写 / 收尾」再切？** 试切 2/2，虽然满足 2×2，但这是同一条批次生命周期的前后半步，拆开会让「立批 → 收口」的调用链跨目录；本卡判为同一类，平铺。
**`dedupe/` 为什么不再切？** 试切 engine+compare = 2，groups = 1，出现单格，平铺。
**`meta/` 为什么是 2 个？** `rules.py` 是中转站自己的元数据规则，`dictionary.py` 是被中转站库承载的工作区字典（学校/场景/标签）；两者都围绕「收题时的元数据」，但职责不同，2 个刚好成群。`meta_dict` 依赖 `pending_db`，所以它不能留在底座。

### 4.6 `bank/`（16 个，切 2 组）

| 类 | 文件 | 个数 | 差异 |
|---|---|---:|---|
| 根（流程入口） | service, provider, questions, basket, exam_name, models | 6 | 对外门面、活跃 provider、题目仓储、题篮、试卷名、响应模型 |
| `engine/` | schema, codec, query, write, review, dashboard, fts, dedupe, dedupe_signature, transfer | 10 | core-bank v0.6.3 引擎本体 |

6/10，切分成立。

**根层为什么不拆？** 试按「入口 / 仓储 / 领域规则」切：service+provider = 2，questions+basket+models = 3，exam_name = 1，出现单格，平铺。

**`engine/` 为什么平铺（这是全树唯一的边界判断）？** 按字面 2×2 还能再切：地基 schema+codec = 2、读 query+fts = 2、写 write+review+transfer = 3、统计查重 dashboard+dedupe+dedupe_signature = 3。本卡仍判平铺，理由有三：

1. 这是**同一个引擎的顺序阶段**，不是并行实现或多种格式；`codec` 双向服务读写，`schema` 被所有阶段共用，任何切法都会让「地基组」同时被多组依赖，边界不干净。
2. 这些模块共享同一个连接、事务和七张表上下文，拆目录不会降低耦合，只会增加跨目录相对导入。
3. 主公给三级的例子是「同一件事多实现/多格式」；`engine/` 没有第二套实现并存。

如果复审坚持字面执行 2×2，这里只需再开 `store/ read/ write/ analysis/` 四个子目录；另外 `pending/batch/`（2/2）与 `plugins/lifecycle/`（2/2）按字面也够格，但本卡同样以「同一条生命周期」判平铺。若要求严格字面执行，**这三处一起复议**，不影响其他流程。

### 4.7 `plugins/`（13 个，切 4 组）

| 类 | 文件 | 个数 | 差异 |
|---|---|---:|---|
| 根 | registry, state | 2 | 插件发现/清单校验、主机状态 |
| `contract/` | manifests, suite, commands, cards | 4 | 插件/套件清单、命令注册表、UI 卡片契约 |
| `lifecycle/` | install, download, update, uninstall | 4 | 安装、下载、更新、卸载 |
| `index/` | catalog, sources, search | 3 | 索引解析、镜像源、索引内搜索 |

2/4/4/3，全部 ≥2，切分成立。

**`lifecycle/` 不再切**：试切 install+download = 2、update+uninstall = 2，满足 2×2，但四步共享同一套包校验与落地逻辑，属于同一条生命周期；拆开会让「下载半步」和「安装半步」分居两处，反而难读。
**`index/` 不再切**：catalog+sources = 2、search = 1，出现单格，平铺。

### 4.8 `backup/`（8 个，切 2 组）

| 类 | 文件 | 个数 | 差异 |
|---|---|---:|---|
| 根 | service, settings, restore, webdav | 4 | 组合根、本机配置、恢复、WebDAV 客户端 |
| `package/` | codec, files, manifest, package | 4 | 包格式：压缩兼容层、文件清单、快照、成品打包 |

4/4，切分成立。
**根层不再切**：备份（service/settings/webdav）与恢复（restore）试切是 3/1，出现单格，平铺。
**`package/` 不再切**：codec/files/manifest/package 是同一份包格式的四个面，任一维度切下去都是单格，平铺。

### 4.9 `workspace/`（5 个，切 2 组）

| 类 | 文件 | 个数 | 差异 |
|---|---|---:|---|
| `startup/` | startup_prefs, host_restart, pwa | 3 | 启动落点、切库重启、PWA 清单 |
| `lifecycle/` | bootstrap, removal | 2 | 布局自举、删除兜底 |

3/2，切分成立。两组都是「工作区」这条流程的不同阶段，且各自 ≥2。

---

## 5. 新模块以后怎么放（决策顺序）

1. **先问：它是不是在定义跨流程的路径 / 配置 / 存储 / 安全 / 序列化 / 题目契约原语？**
   是 → 才考虑 `app/core` 根；并且必须能说明「不止一条流程在用 + 无业务语义 + 不反向依赖业务」。
2. **再问：它属于哪条流程？** 能答出来 → 进对应流程根或类目录。
3. **再问：它是不是某类东西的第二种实现 / 第二种格式？** 是 → 进那个类目录（如 `ingest/layout/`、`ingest/recognize/`、`ai/providers/`）。
4. **答不出来 → 不许进 `app/core`。** 先证明它值得单开一条流程，或者把它做成插件。
5. **禁止**：`common/`、`shared/`、`utils/`、`helpers/`、`misc/` 这类垃圾桶目录；禁止按文件个数开目录；禁止 `__init__.py` 做 re-export 门面（会制造隐式耦合与循环）。
6. **日志**：直接用标准库 `logging.getLogger(__name__)`，不新增 `app/core/logging.py`。
7. **包标记**：每个新包放一个只含 docstring 的 `__init__.py`；`app/core/ai/providers/__init__.py` 例外，它是动态注册表，原样保留逻辑。

### 5.1 几个容易放错的例子

| 新东西 | 错误放法 | 正确放法 | 理由 |
|---|---|---|---|
| 新增一个 OCR 引擎 | `app/core/ocr.py` | `ingest/recognize/xxx.py` | 是识别的另一种实现 |
| 新增一种备份压缩格式 | `app/core/zip_utils.py` | `backup/package/` | 是包格式的实现细节 |
| 新增题目字段校验 | `app/core/validators.py` | `question_contract.py` / `contract_fields.py` | 题目契约原语 |
| 新增插件安装源 | `app/core/downloader.py` | `plugins/index/sources.py` 或 `plugins/lifecycle/download.py` | 属于插件索引/下载 |
| 新增一个跨流程的 JSON 工具 | `app/core/json_utils.py` | **不许**（`wire.py` 是唯一 JSON 边界） | 破坏序列化边界 |
| 新增一个业务统计 | `app/core/stats.py` | 对应流程的看板模块，或插件 | 有业务语义 |
| 想把 `pinyin` 提到 core 根 | `app/core/pinyin.py` | 留在 `content/pinyin.py` | 不是横切基础设施，只是内容函数 |

---

## 6. 本次不做什么

- 不移动、不改名、不建目录、不补 `__init__.py`、不改任何 import。
- 不拆 12 个超 500 行文件（`pending_dedupe` 783、`pending_pool` 773、`plugin_update` 741、`plugins` 729、`pending_db` 676、`pending_bank` 639、`bank_schema` 624、`bank_write` 623、`bank_query` 593、`dedupe_signature` 540、`restore` 532、`latex_style_dict` 506）；本树只决定它们去哪，不决定怎么拆。
- 不合并 `contract_fields.py` 等小模块，不调整底座 10 个模块的内部实现。
- 不提交、不 push、不动 `LICENSE`、不动 `docs/AGENTS.md`。
- 风险与迁移顺序见 `CORE_REFACTOR_RISKS.md`；现状与引用数据见 `CORE_MODULE_INVENTORY.md`。

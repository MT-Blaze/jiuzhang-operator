# biz 记录 · 查重拦截收尾 · 批次批量剔除 · LaTeX 清洗预览

- 需求名：`dedupe-batch-purge-latex-preview`
- 发起日期：2026-11-02（文件名日期取需求发起日，落盘后不改）
- 状态：进行中（REQ 已立；PLAN / DESIGN / IMPL / VERIFY / RELEASE 待各角色交付后由 recorder 汇编）
- 当前工序：01 意图已由主会话收敛，等 architect 出 [PLAN] / [DESIGN]
- 本文件纪律：只由 recorder-agent 写入；除 [REQ] 外只搬运各角色交付的结构化内容，不改数字、不补写未出现过的结论，历史章节不回头编辑
- 证据口径：对外交付证据是 `docs/PROJECT_MEMORY.md` §5.6 机械证据回传单五项；本文件是工序内过程稿，不做双写

## [REQ] 2026-11-02

### 1 背景

上一轮（军令#31）已把查重拦截做成「可裁决拦截」（`d18574f`：画布红灯 + 渲染对比 + 辅助栏三选一），并把年级回批次、文案归「存为待审」、底座兼容面收到 Python 3.10（`299bea9`）。本轮是收尾欠账：批次级批量剔除、全库查重清洗下架、LaTeX 清洗强制预览，外加 README 门面。任务卡第一项另要求先抢救工作树里 DSH 工具留下的未提交现场。

### 2 任务卡原文（主公 2026-11-02 下发，逐条抄录）

**任务一（本地代码抢救与基础维护，最高优先级）：**

1. 检查 DSH 工具是否在工作区留下未提交的烂摊子（git status），不干净则代码比对，保留合理修改、剔除错误修改后 commit。
2. 修复群友报错：`app/core/plugin_update.py` 的 f-string 嵌套引号改为兼容 Python 3.10+；`app/core/backup_package.py` 的 `from compression import zstd` 加 try-except 降级。
3. README.md 明确写明支持 Python 3.10+。

**任务二（UI 瘦身收尾）：**

1. 「年级」字段加回右侧辅助栏「批次公共元数据」区（控件 id `#epMetaGrade`），并同步补齐后端 `pending_meta.py` 四处白名单。
2. 全局把「存为待办」统一改为「存为待审」。

**任务三（核心业务——查重拦截机制）：**

1. 双重防线：外部题库导入批次时后台自动初查；点【存入主库】时终局强校验。
2. 命中提示：左侧原图亮红色双闪呼吸灯，底部信息栏红字警告「主库已存在高度相似题目」。
3. 对比弹窗：纯渲染对比（不比源码，左旧题右新题）。
4. 处置动作：答案不一致→红字拦截禁止入库；解析不同→追加合并为「解析二」；完全一样→覆盖主库或放弃新题。
5. 批量去重：批次列表提供【一键剔除本批次重复题】按钮，直接物理删除。
6. 彻底下架真题题库（bank-ui）原有的「全库查重清洗」功能。

**任务四（安全重构——LaTeX 清洗降级）：**

1. 物理删除底座和前端任何「全库批量清洗」的按钮、路由和脚本入口。
2. 只在录题辅助栏保留【清洗当前题 LaTeX】按钮。
3. 强制预览防呆：点击清洗后先弹窗预览改动，用户点【采用替换】后才允许覆盖中栏源码。

**任务五（门面与文档更新）：**

1. README.md 显眼位置补官方插件仓库超链接 https://github.com/MT-Blaze/jiuzhang-plugins

### 3 验收标准

判据用词一律取自任务卡条目本身，未增补新指标。

| 编号 | 条目 | 验收判据（可核验形式） |
|---|---|---|
| 1.1 | 工作树抢救 | `git status` 已收口；保留的合理修改已 commit，错误修改已剔除 |
| 1.2a | `plugin_update.py` | f-string 不出现嵌套同类引号，Python 3.10 语法可通过 |
| 1.2b | `backup_package.py` | `from compression import zstd` 有 try-except 降级，缺 zstd 时不崩 |
| 1.3 | README Python 版本 | README.md 明确写明支持 Python 3.10+ |
| 2.1 | 年级回辅助栏 | 辅助栏有 `#epMetaGrade`；`pending_meta.py` 四处白名单收 `grade` |
| 2.2 | 文案统一 | 全仓界面与代码不再出现「存为待办」，统一为「存为待审」 |
| 3.1a | 导入自动初查 | 导入批次后后台自动初查，无需人工点按 |
| 3.1b | 终局强校验 | 点【存入主库】时强校验，命中即拦 |
| 3.2 | 命中提示 | 画布红灯双闪呼吸 + 底部信息栏红字「主库已存在高度相似题目」 |
| 3.3 | 对比弹窗 | 左旧题右新题，纯渲染对比，不显示源码 |
| 3.4 | 三种处置 | 答案不一致拦、解析不同并入「解析二」、完全一样可覆盖或放弃 |
| 3.5 | 一键剔除 | 批次列表有【一键剔除本批次重复题】，物理删除 |
| 3.6 | 查重清洗下架 | bank-ui 的「全库查重清洗」按钮、端点、中继入口、探针、文档段落全部下架 |
| 4.1 | 全库批量清洗 | 底座与前端无「全库批量清洗」的按钮、路由、脚本入口（现状见 §4.3 口径） |
| 4.2 | 单题清洗按钮 | 录题辅助栏保留清洗按钮，文案「清洗当前题 LaTeX」，id 保持 `#epAiClean` |
| 4.3 | 强制预览 | 点击清洗先弹预览改动，点【采用替换】才允许覆盖中栏源码 |
| 5.1 | 官方插件仓库链接 | README.md 显眼位置有 https://github.com/MT-Blaze/jiuzhang-plugins |

### 4 现状核定（2026-11-02 主会话实地核对）

#### 4.1 已达成

证据来源栏为 commit 或 `文件#符号`；本轮未重跑测试与门禁，基线与实跑见 §4.4。

| 条目 | 已达成事实 | 证据来源 |
|---|---|---|
| 任务 1.2 | `app/core/backup_codec.py` 已实现「标准库 `compression.zstd` → pip `zstandard` → 标准库 `gzip`」三级降级，`_load_stdlib_zstd` / `_load_pip_zstd` / `ZSTD_MODULE` / `BACKEND`，读侧按魔数分辨；`tests/test_backup_codec.py` 6 测 | `299bea9`；`app/core/backup_codec.py#_load_stdlib_zstd`、`#_load_pip_zstd`、`ZSTD_MODULE`、`BACKEND` |
| 任务 1.3 | README.md:12 与 :49-55 已写 Python 3.10+，并说明 zstd/gzip 降级 | `299bea9`；`README.md:12`、`README.md:49-55` |
| 任务 2.1 | 前端 `plugins/org.jiuzhang.editor/dist/index.html:267` 有 `#epMetaGrade`；后端四处为 `app/core/pending_meta.py:118`（指纹键）、`:167`（normalize 收 grade）、`:223-227`（写根字段 `document["grade"]`）、`:322`（批次同步 patch 键白名单） | `299bea9`；`plugins/org.jiuzhang.editor/dist/index.html:267`；`app/core/pending_meta.py:118,167,223-227,322` |
| 任务 2.2 | 全仓「存为待办」0 命中（代码与界面侧；字面残留见 §4.5 复核注） | `299bea9`；全仓 grep |
| 任务 3.1 后半（终局强校验） | `app/core/pending_bank.py#approve`（:504-541）调 `find_duplicate`，未带 action 时抛 `PendingDuplicate`；`_refuse_different_answer`（:421）抛 `PendingDuplicateAnswer`；`app/api/pending.py#pending_approve`（:160-192）翻译为 409 且 detail 带 `duplicate` / `answer_mismatch` / `code` | `app/core/pending_bank.py#approve`、`#_refuse_different_answer`；`app/api/pending.py#pending_approve` |
| 任务 3.2 | 画布红灯 `plugins/org.jiuzhang.editor/dist/layout_canvas.css:620` 的 `.ed-root[data-dup="on"]::after` + `dist/ui_dup.js#paintLamp`；辅助栏红字 `dist/index.html:384` 的 `#epDupWarn`（`role="alert"`）；底部信息栏 `dist/ui_approve.js:285,342` 的 `batchNote("主库已存在高度相似题目，等老师拍板。")` | `d18574f`；`dist/layout_canvas.css:620`；`dist/ui_dup.js#paintLamp`；`dist/index.html:384`；`dist/ui_approve.js:285,342` |
| 任务 3.3 | `dist/ui_dup.js` 渲染对比浮层（左右两份标准文档渲染，不显示源码），跨帧走 `editor.dup_review` | `d18574f`；`dist/ui_dup.js`、`editor.dup_review` |
| 任务 3.4 | 三种处置已具备——答案不一致拦（`_refuse_different_answer`）、解析不同并入「解析二」（`_merge_solution`，`bank_dedupe.append_solution`）、覆盖（`action=overwrite`） | `d18574f`；`app/core/pending_bank.py#_refuse_different_answer`、`#_merge_solution` |

#### 4.2 欠账（本轮范围）

| 条目 | 欠账事实 | 证据源 |
|---|---|---|
| 任务 3.5 | 全仓「一键剔除」0 命中，批次级批量物理删除未实现 | 全仓 grep |
| 任务 3.6 | bank-ui 全库查重清洗仍在：`plugins/org.jiuzhang.bank-ui/dist/ui_review.js:169`、`dist/plugin.js:294` 页签、`app/api/bank.py:405,437` 两条端点、`static/js/stage_relay_bank.js:215`、`tools/dedupe_probe.py`、`docs/API_REFERENCE.md §2.17` | 同上六处；端点定位见 §4.5 |
| 任务 3.1 前半 | `app/core/pending_bank.py#save_draft`（:121-260）逐行确认全程无查重，导入批次自动初查缺失；按主公排序留下一轮 | `app/core/pending_bank.py#save_draft` |
| 任务 4.3 | `plugins/org.jiuzhang.editor/dist/ui_ai.js:233-294` 的 `cleanViaHost` 在 `Promise.all` 成功后直接回填，无预览、无「采用替换」 | `dist/ui_ai.js:233-294` |
| 任务 5 | README.md 全文无 `jiuzhang-plugins` 链接 | `README.md` 全文 grep |

#### 4.3 口径与偏离（原样记入）

- 任务 4.1：经全仓检索（`clean_all|clean_bank|bank.clean|latex_clean_all|批量清洗|全库清洗|clean_dirty_latex`）核实，本仓不存在「全库批量 LaTeX 清洗」的按钮、路由或脚本入口，只有单条确定性清洗 `app/core/question_parser.py#clean_dirty_latex`（:206）与端点 `app/api/agents.py#clean_latex`（:393，能力 `text.clean_latex`）。该子项无可删项，如实记为**「不适用」**，不得记为已完成。
- 任务 4.2：主公裁决——按钮文案改「清洗当前题 LaTeX」，id 保持 `#epAiClean` 不变。
- 任务 3.6：主公裁决力度——拆前端 + 路由，保留 `app/core/bank_dedupe.py` 的归一与 `append_solution` 等共用引擎（`app/core/pending_dedupe.py:40,41,193,196` 与 `pending_bank._merge_solution:455` 仍依赖）。
- 任务一.1：主公裁决——工作树里 4 支 demo 插件删除态、`Morning_Report.md`、`docs/pipeline-workflow.md`（桌面副本与 HEAD 逐字节一致）、`.dsh-acl-recovery/`、`docs/handoff/` + `tools/handoff.py` + `tests/test_handoff.py` 全部不 stage、不恢复；仅 `eval-agent.md` 配色回写已提交 `c31fe6b`。

#### 4.4 本轮基线（主会话 2026-11-02 当次实测输出，recorder 本轮未复跑）

| 项 | 命令 | 当次输出 |
|---|---|---|
| 全量回归 | `tools/run_all_tests.py` | 模块 75 个，用例 1451 个，失败模块 0 个 |
| 快门禁 | `bash scripts/check-quick-gate.sh` | PASS（6 项全过） |
| 静态审计 | `tools/audit_code.py` | ERROR 0 / WARN 36 / INFO 4 |

#### 4.5 recorder 落盘时只读复核（仅确认引证定位，未改动任何一条结论）

| 复核项 | 结论 |
|---|---|
| `299bea9` 存在性 | `git cat-file -t 299bea9` → `commit`，标题「feat: 年级回批次、文案归『存为待审』，底座兼容面收到 Python 3.10」 |
| 工作树现状 | `git status --porcelain` 与任务一.1 裁决清单一致：4 支 demo 插件为 `D` 态、`Morning_Report.md` / `docs/pipeline-workflow.md` 为 `D`，`.dsh-acl-recovery/`、`docs/handoff/`、`tests/test_handoff.py`、`tools/handoff.py` 为未跟踪 |
| 3.6 两条端点 | `app/api/bank.py:402` 为 `GET /api/bank/plugins/{plugin_id}/duplicates`（查重扫描），`:418` 为 `POST /api/bank/plugins/{plugin_id}/duplicates/merge`；主会话记的 `:405,437` 落在两个端点的函数体内，指向一致 |
| 3.1 前半 | `sed -n '121,262p' app/core/pending_bank.py` 内 `duplicate` / `find_duplicate` 命中 0，与「save_draft 全程无查重」一致 |
| 4.1 | 以给定七个模式全仓检索，命中全部落在 `clean_dirty_latex` 的定义/调用/测试与 `agents.py:398-402` 注释，未见「全库批量清洗」入口，与「不适用」一致 |
| 1.2 | `ast.parse(..., feature_version=(3, 10))`：`app/core/plugin_update.py`、`app/core/backup_package.py`、`app/core/backup_codec.py` 三个文件均通过 |
| 2.2 注 | 代码与界面侧 0 命中；字面残留 6 处全在过程稿里——`docs/handoff/orders/030.md:15,21`、`.system_generated/handoff_order_030.md`、`.system_generated/review_pack_030.md`，且这些命中本身是在引用「命中 0」这条旧结论。是否清理由主公裁决，recorder 不改 |

### 5 本轮待交付产物（各角色产出，recorder 只等不写）

| 角色 | 应交付 | 落笔章节 |
|---|---|---|
| architect-agent | 方案与取舍（含 3.6 拆解边界、3.5 物理删除的鉴权与事务边界） | [PLAN]、[DESIGN] |
| coder-agent | 涉及文件清单 + 使用的 skill | [IMPL] |
| test-agent | 测试与探针实跑输出、门禁结果 | [VERIFY] |
| eval-agent / reviewer-agent | 判定与门禁结论清单 | [VERIFY] 引用 |
| recorder-agent | 汇编、状态流转、发版后归档报告 | 全部章节 |

## [PLAN] 2026-11-02

### 2 [PLAN]

| 步 | 内容 | 产物 | 不绿不往下走的门禁 |
|---|---|---|---|
| P1 | 3.6 下架（独立 commit） | 删除清单落地 + `plugin.json`/两份 `plugins.json` 同步 + zip 重打 | `bash scripts/check-quick-gate.sh`（第 33 步 `check_plugin_index_parity.py`，脚本 `:5`/`:83-88` 校验「索引 version == 清单 version」）+ `tools/run_all_tests.py` 全绿 + `tools/audit_code.py` 基线复跑 |
| P2 | 3.5 后端 | `pending_dedupe.py` 分组函数 + `pending_bank.purge_batch_duplicates` + 两条路由 + `tests/test_pending_purge.py` | 单模块 `unittest tests.test_pending_purge` 全绿 + quick gate |
| P3 | 3.5 前端 | editor 列表行改造 + `#epBatchPurgeModal` + relay 两法 + editor `plugin.json` 预置 2.10.0 + 两仓索引同步 | 真机探针（点剔除 → 执行 → 卡片 total 减 N）+ quick gate |
| P4 | 4.3 | 两主题 + 预览浮层 + 逐段采用按钮 | 真机像素探针 + quick gate |
| P5 | 封版 | `tools/build_plugin.py --all` 重打 zip（editor 版本已在 P3 预置，P4 不再改版本号） | `bash scripts/check-release-gate.sh` |

**实施顺序**：P1 → P2 → P3 → P4，串行。P1 先做（删路由/命令，越早冲突面越小）；P2 与 P4 技术上可并行（改的是 `app/` 与 editor 两份互不相交的文件），但 P3/P4 共用 editor 一个版本号，故 P3、P4 必须连着做完再封版。

**能力绑定（建议，需 recorder 与 `.qoder/skill-bank.json` 核对后落定）**：P1 `add-plugin` + `build-release`；P2 `add-host-api` + `run-regression`；P4 `prove-visual-change`。

> 来源：architect-agent [PLAN] 第 2 版，逐字搬运；第 3/4 轮勘误只动 [DESIGN] 契约细节，不改本计划的五步顺序与门禁绑定。

## [DESIGN] 2026-11-02

### 0 裁决落地值

| 裁决 | 取值 | 对契约的影响 | 对测试的影响 |
|---|---|---|---|
| ① 剔除集合 | 「批内互相重复」∪「与主库命中」两组都剔，按 `reason:"batch"\|"bank"` 区分；删除集**只吃指纹全等**，相似度只进预览报告；弹窗内 `batch` 组默认勾选、`bank` 组默认不勾选；**执行集合 = 老师勾选集，允许是全集真子集** | dry-run 出参必须有 `groups[].reason`；执行口按勾选集逐条判重（见 §3.4 S5）；`drop_ids` = 勾选集，不再是两组无条件并集 | 新增用例覆盖「只勾 batch 组」「勾选已失效 → 409」「重算后新增重复 → 200 只报 `new_redundant`」各一条；相似但指纹不等的两条**不得**进 `drop_ids` |
| ② bank-ui 去留 | 只摘前端 + 路由，`app/core/bank_dedupe.py` 一行不删；只删 `tests/test_bank_dedupe.py` 的 test_22~test_26 | 后端删除面只到 `app/api/bank.py` 两条路由；引擎函数与 `bank.view` 能力保留 | 前 21 条引擎单测保留；静态审计基线维持 ERROR 0 / WARN 36 / INFO 4（主源 `bank_dedupe.py:482` 的 sql-fstring 未触碰，此行按裁决②给定，本轮未复读） |
| ③ 采用替换粒度 | 按段独立点：题干段、解析段各一个按钮，`editor.apply_patch` 每段各一次 | 辅助栏按钮不是一对而是两对（4 个 id）；未变段不出按钮、只显示「未改动」 | 用例必须断言「只点题干段 → apply_patch 恰好 1 次且 field=="stem"」 |

清洗按钮 id 固定 `#epAiClean`（`dist/index.html:353` 实读确认），文案不改，本设计不动它。

---

### 1 问题定性（R05 §5）

- **3.5 = 类问题**。剔除器按 `reason` 参数化，不写死一种判定口径。
  - **泛化点**：`app/core/pending_dedupe.py` 新增 `DUPLICATE_REASONS = ("batch", "bank")` 常量 + `batch_duplicate_groups(batch_id, provider_id)` 内部按 reason 分支产出组；出参与删除集都由该常量驱动，API 与前端只认枚举值，不认识具体判定。
  - **扩展成本声明**：新增第三类口径（例如「与题篮命中」）需改 **7 处 / 4 个文件**、零表改（不加列、不加表）——`pending_dedupe.py` 的 `DUPLICATE_REASONS` 枚举 + 分组分支（1、2）、`app/api/pending.py` 的响应 docstring `reason` 说明（3）、editor `dist/ui_batches.js` 的 reason 徽标表（4）、弹窗分组标题/说明文案（5）、默认勾选策略映射（6）、`tests/test_pending_purge.py` 加 1 组用例（7）。单位：「处」= 编辑点，「文件」= 落点文件（`pending_dedupe.py` 占两处、`ui_batches.js` 占三处，故 7 处落在 4 个文件）。判定口径变化不触发表结构与迁移。
- **3.6 = 点问题**（删减法）。纯摘除，不新增抽象层，禁止借机把引擎改造成通用「清洗器注册表」。
- **4.3 = 点问题**。一个预览浮窗前置于既有回填通道（`ui_ai.js#cleanViaHost` 现直填）；逐段循环由 `sections` 数组驱动，不引入段落注册表或清洗插件体系。

---

### 3 [DESIGN] ① 3.5 — 批次「一键剔除本批次重复题」

#### 3.1 现状证据（本轮实读）

- `app/core/pending_bank.py#delete_pending` :576-603：`BEGIN IMMEDIATE`(:585) → `DELETE FROM pending_questions WHERE id=?`(:586) → `UPDATE batches SET total = MAX(total - 1, 0), updated_at=?`(:589-593) → `refresh_batch(con, batch_id)`(:594) → `commit`(:595) → 关连接(:600) → `drop_assets`(:601) → `_settle_batch`(:602)。
- `#_settle_batch` :606-633：`live` 计数(:618-620)；`if live: return batch_card(row, live)`(:621-622)；`drop_assets` 本批残留切图(:626)；`backup_paths(row["source_backup"])` 逐个 `unlink`(:627-632)；批次行保留。
- `#duplicate_report` :397-418 已能回主库同题两侧文档；`#approve` :533 `existing = find_duplicate(provider_id, document, assets)` 是终局闸门。
- `app/core/pending_dedupe.py`：`_text_key`(:32-42)、`_fingerprint`(:45-53)、`_bank_image_hashes`(:73-90)、`_pending_image_hashes`(:93-115)、`find_duplicate`(:118-144)、`similarity_report`(:232-298，全表读 `SELECT id,type,stem,options,extensions,answer` :261-263)。**无任何分组函数**（def 清单至 :298 无 group 类）。
- `app/core/pending_batches.py#batch_card` :63-79，`total` 取 `row["total"]`(:76)、`pending_count=live`(:77)；`refresh_batch` :111-122（只写 `pending_count`）；`next_seq` :125-135（`COALESCE(MAX(seq),0)+1` 证明 seq 即录入序）。
- 端点口径：`app/api/pending.py` 读口无鉴权（:25、:37-48），写口 `dependencies=[Depends(require_write_token)]`（:63-66、:88-92、:155-159、:209-213）；provider 由服务端解析（:145、:177）。既有 detail.code 为 snake_case（:184 `"duplicate_answer_mismatch"`）。
- relay：`static/js/stage_command.js` `RELAY_METHODS` :29-68（`pending.*` 在 :43-44/:47）；`static/js/stage_relay_io.js` 读口 :144-147，写口 `questions:write` 闸 :169-179。
- 前端：editor `dist/ui_batches.js#renderBatchList` :97-135，每行是 `<button class="ed-batch-row">`(:111)，`done` 时 `row.disabled=true`(:116)；`#epDelModal` 形状见 `dist/index.html:400`（`role="dialog" aria-modal="true"`）；弹窗取焦/还焦与 Esc/Tab 圈在 `dist/ui_modal.js#openModal` :25-31、`#closeModal` :33-40、键盘 :42-62，但 `#openModalNode` :20-23 只认 `delModalEl`。

#### 3.2 契约

**读**：`GET /api/pending/batches/{batch_id}/duplicates`（无鉴权，与 :25 同口径）

```json
{
  "batch_id": "B-001", "provider_id": "org.jiuzhang.core-bank",
  "scanned": 42, "redundant": 4, "live_after": 41, "will_empty": false,
  "main_snapshot_at": "2026-11-05T10:00:00", "main_scanned": 1203,
  "groups": [
    {"reason": "batch", "keep": "p_ab12...", "drop": ["p_cd34..."], "fingerprint": "9f2e...", "seq_keep": 3},
    {"reason": "bank",  "keep": "",          "drop": ["p_ef56..."], "fingerprint": "7a11...", "existing_id": "q_777"},
    {"reason": "bank",  "keep": "",          "drop": ["p_gh78..."], "fingerprint": "5c02...", "existing_id": "q_901"},
    {"reason": "bank",  "keep": "",          "drop": ["p_ij90..."], "fingerprint": "0b33...", "existing_id": "q_145"}
  ],
  "drop_ids": ["p_cd34..."]
}
```

- `keep` 语义统一：保留者 id——`reason:"batch"` 指池内 seq 最小的那条；`reason:"bank"` 指主库那条（`existing_id`，此时 `keep` 为空串）。
- **两个计数口径分开写死**（G6）：`redundant` = 两组 `drop` 的并集条数（示例 = 1 + 3 = 4，与 `groups` 逐条对得上）；`drop_ids` = **默认勾选集** = `batch` 组 `drop` 的并集，升序（示例只有 1 条，故与 `redundant:4` 不等是正常的）；`live_after` = `scanned - |drop_ids|`、`will_empty` = `live_after == 0`，两者都按默认勾选集算。老师改勾选后，前端按 `scanned - 勾选数` 实时重算剩余并即时更新红字。
- `drop_ids` 升序排序。相似度**不进** `groups[].drop`、不进 `drop_ids`。
- `main_scanned` = S0 主库行快照的**实读行数**（`SELECT` 返回几行就写几），不估算、不设上限字段。理由：S0 是全表一次读，没有截断分支，留 `main_truncated` 就是一个永不置真的死字段；将来真要截断，再单独加字段并同步改 `groups` 语义，本设计不预留。

**写**：`POST /api/pending/batches/{batch_id}/purge-duplicates`，`dependencies=[Depends(require_write_token)]`

请求体：`{"drop_ids": ["p_..."], "expected_drop_ids": ["p_..."], "allow_empty": false}`（`drop_ids`/`expected_drop_ids` 必填；`allow_empty` 可选、缺省 `false`，不填就按"不允许剔空"处理）。
- `drop_ids` = **用户勾选集**（将被删除的），升序。默认 = 各 `batch` 组的 `drop` 并集；`bank` 组默认不勾（裁决①），老师可手动加。
- `expected_drop_ids` = 同一勾选集的服务端回显，只做载荷自洽校验（防截断/改写）；`sorted(drop_ids) != expected_drop_ids` → 400 `batch_purge_expected_mismatch_client`。
- **不再有 `digest`**（G7 勘误）：`expected_drop_ids` 已是对同一集合的完整回显，再叠一层摘要不增加任何保护，而沙箱 iframe 内没有可靠的 sha256 实现（`crypto.subtle` 依赖安全上下文，不能写死可用）。载荷自洽只由 `expected_drop_ids` 承担，真正的护栏仍是 §3.4 S5 的逐条判重与保留者保护。
- `allow_empty` = 服务端硬闸：当 `scanned - len(drop_ids) == 0` 时必为 `true`，否则 400 `batch_purge_empty_not_confirmed`。**不信任前端文案**——持有 `questions:write` 的插件绕过弹窗直接打接口时，剔空批次（连带删原卷副本）必须显式表态。

响应：`{"batch_id", "deleted": [], "skipped": [{"id","why"}], "files_failed": [{"name","why"}], "batch": {卡片}, "settled": bool, "backup_removed": bool, "new_redundant": 0}`。
- `new_redundant` = **事务内重算重复全集 \ 勾选集**的条数（定义为差集大小，不是「本次新出现」的条数）：既覆盖老师主动没勾的 `bank` 组，也覆盖执行前新长出来的重复。`batch` 组的 `keep` 不进入重算全集（G5：保留者是「要留的那条」，不可能成为剔除项），因此 `new_redundant` 在执行「只勾 batch 组」的正常路径上必然清零。前端据它提示「还有 n 道重复未剔除，可重扫」，**不阻断**本次执行。
- 语义边界：本次调用只会删 `drop_ids` 里的条目；`new_redundant` 里的条目一条都不动、只报数。

#### 3.3 错误码表

| HTTP | `detail.code` | 触发 | retryable |
|---|---|---|---|
| 400 | `batch_purge_bad_pending_id` | `drop_ids` 中有不合 `^p_[A-Za-z0-9_-]{8,64}$` 的项（`new_pending_id` 产 24 位十六进制，必然合规） | false |
| 400 | `batch_purge_empty_drop_ids` | `drop_ids` 为空数组 | false |
| 400 | `batch_purge_expected_mismatch_client` | `sorted(drop_ids) != expected_drop_ids`（客户端自相矛盾 / 载荷被中间层改写） | false |
| 400 | `batch_purge_pending_not_in_batch` | 某个 id 格式合法但**不属于该批**（存在但属别批，或池内不存在） | false |
| 400 | `batch_purge_empty_not_confirmed` | 本次执行会把批次剔空，而 `allow_empty !== true` | false |
| 400 | `batch_purge_bank_unavailable` | 主库连接失败：`bank.connect` 抛 `bank.BankError`（主库文件不可用/被占用） | **true**（稍后重试） |
| 404 | `batch_purge_batch_not_found` | 批次号格式不合法**或**批次不存在（对齐 `list_batch_questions:140-141` 的既有惯例：格式错也走 404，不另设 400） | false |
| 404 | `batch_purge_bank_not_found` | provider 未注册/未启用：`bank.connect` 抛 `bank.BankNotFound` | false |
| 409 | `batch_purge_selection_stale` | 勾选集里某条在事务内重算后**已不再重复**（口径见 §3.4 S5） | **true**（重扫即可） |
| 409 | `batch_purge_keep_selected` | 勾选集命中某个 `reason:"batch"` 组的 `keep`（保留者） | false |
| 401/403 | 由 `require_write_token` 产出 | 无令牌 / 令牌错 | false |

**主库不可用不降级**：`bank_fingerprint_map` 侧吞异常**不成立**——吞掉会让清单假装「本批没有与主库重复的题」，老师按清单执行后直接漏剔。口径对齐既有惯例 `app/api/pending.py:201-204`（`BankNotFound→404`、`BankError→400`）。反例说明：`app/core/pending_dedupe.py#find_duplicate` `:128-131` 的 `except bank.BankError: return ""` 是**单条实时判定**的吞异常写法，不适用于本 dry-run 的清单出参。

**口径定死（四个错误码的分工）**：路径上的 `batch_id` 格式不合法或不存在 → 404 `batch_purge_batch_not_found`（与 `list_batch_questions:140-141` 同口径）；provider 不存在/未启用 → 404 `batch_purge_bank_not_found`；`drop_ids` 里的 id 不存在或属别批 → 400 `batch_purge_pending_not_in_batch`（它是 `batch_id` 下的子资源参数，不是寻址路径）；**id 合法且属于本批、但执行时已不重复 → 409 `batch_purge_selection_stale`**（这是事实判定，只有进事务后才算得出，不能塞进 400）。命名归入既有 `detail.code` 的 snake_case 域（对齐 `:184`），统一前缀 `batch_purge_`。

#### 3.4 事务时序（逐条）

```
S0  事务外 · 主库行快照一次（只读一次 SELECT，不碰图；连接异常按 §3.3 抛 404/400，不吞）
    provider_id = provider.resolve()["plugin_id"]           # 对齐 :145/:177
    main_rows = bank_rows_snapshot(provider_id)             # 只返回行，不返回指纹
        con = bank.connect(provider_id); SELECT id, type, stem, options, extensions FROM questions
        → rows（全表一次；连接/查询异常在此处按 §3.3 映射，不吞）
    main_snapshot_at = now_iso()
S1  事务外 · 批次存在性
    con = connect()                                        # 池库连接在此打开，S1 与 S2 共用同一条
    row = batch_row(con, batch_id) → None ⇒ 404           # 与 list_batch_questions :140-146 同口径；异常时 con.close() 后再抛
S2  con.execute("BEGIN IMMEDIATE")                         # 只锁中转站库，锁不住主库（已声明的边界）
S3  池内全量一次取
    SELECT id, doc_json, assets_json, seq FROM pending_questions
      WHERE batch_id = ? ORDER BY seq ASC, id ASC
    → 逐条 _text_key/_fingerprint 算 pool 指纹（O(N)）
S4  分组（两阶段；主库一次 SELECT 已在 S0 完成，此处不再碰主库连接）
    # 4a 池内分组：O(N)，池内指纹在 S3 已算好
    for 指纹 in pool：同指纹多条 ⇒ 一条 reason:"batch" 组，keep=seq 最小，drop=其余
    # 4b 主库候选筛选：先比文字键，只对命中行算配图哈希
    text_keys = {池内每条的 _text_key}
    main_map = bank_fingerprint_map(main_rows, text_keys)
        → 只对 row 的 _text_key ∈ text_keys 的主库行调 _bank_image_hashes(row["extensions"])
        → {指纹: [q_id...]}（同指纹多行取 id 升序首项，保证清单稳定）
    成本：M 行全部走 _text_key 归一（O(M)，纯字符串）；图哈希**只对文字键命中的主库行**做，命中行数 ≤ N 组
    先例：find_duplicate:138-143 就是「先比文字键、row_key != text_key 直接 continue、键相等才读图哈希」
    # 4c 建 bank 组
    for 指纹 in pool 且 指纹 in main_map ⇒ 一条 reason:"bank" 组，drop=[该 p_id]，existing_id=main_map[指纹][0]
    一条 p_id 只进一个组；**batch 组的所有成员（keep 与 drop）都不再单列 bank 组**（G5）：
    落选者已被批内去重覆盖；keep 是「要留的那条」，若再按主库命中列成删除项，
    老师勾它会撞 S5c 的 keep 保护、不勾它又会永久计入 new_redundant（永不清零）。
    批内去重后仍与主库重复的 keep，交给 approve 时的 :533 终局闸门处理，不在本清单重复报。
S5  校验勾选集（子集语义；这是裁决①补丁的正面对价）
    recompute = 事务内重算的重复全集（batch 组 drop ∪ bank 组 drop，升序；不含任何 keep）
    # 5a 载荷自洽（§3.3 的两条 400 在进事务前已拦过一次，此处只作防御性复核，不再重复报码）
    # 5b 逐条判重：drop_ids 里任一条 ∉ recompute
    → ROLLBACK + 409 batch_purge_selection_stale（整批不动，零删除）
       含义：老师勾的这条在执行时已不再与任何对象指纹全等（主库那条被删/题被改/池内同组已被剔）
    # 5c 保留者保护：drop_ids 里任一条 == 某个 batch 组的 keep
    → ROLLBACK + 409 batch_purge_keep_selected（整批不动）
    # 5d 允许的差异：recompute \ drop_ids 非空（执行集合是全集真子集）
    → 放行，响应回 new_redundant = |recompute \ drop_ids|
    注：**不再有「集合 ≠ 期望即 409」**。旧口径 `batch_purge_duplicates_changed` 与「默认不勾 bank 组」直接冲突（每次不勾都必 409），已由 5b 的逐条判重取代并删除该码。
    # 5e 剔空硬闸：scanned - len(drop_ids) == 0 且 allow_empty !== true
    → ROLLBACK + 400 batch_purge_empty_not_confirmed（正文见 §3.2 写口）
S6  逐条删除（只处理 S5 已放行的勾选集；此后单条失败只记账不整体否决）
    DELETE FROM pending_questions WHERE id = ? AND batch_id = ?
    rowcount == 1 → deleted.push(id)；rowcount == 0 → skipped.push({id, why:"row_gone"})
S7  账目回写（delete_pending 的 :589-594 两步同构）
    UPDATE batches SET total = MAX(total - ?, 0), updated_at = ? WHERE batch_id = ?   # ? = len(deleted)
    refresh_batch(con, batch_id)                            # pending_count = 真实行数
S8  COMMIT；任何异常 → ROLLBACK 并原样抛出（整批仍在）；`finally: con.close()`
S9  文件层（提交之后，顺序与 :601-602 一致）
    drop_assets(被删条目的 assets)  逐条；失败记入 files_failed，不回滚数据
    finished = _settle_batch(batch_id)                       # 只调一次
    backup_removed = finished.get("done") is True and 原 source_backup 非空
```

**`reason:"bank"` 的判定时点与竞态窗口（G10 勘误）**：主库判定只发生在**本次执行请求的 S0 快照**上；S0 之后到 S8 之间**不再读主库**，这段残窗是毫秒级。真正暴露给老师的窗口是 `[dry-run 请求时刻, 本次执行 S0]`——老师看清单、勾选、点执行可能隔着几分钟，这期间主库若删题，S5b 会以 409 `selection_stale` 拦下；主库若新增同题，则本次清单不含它（少剔），下一轮 dry-run 会报出，`new_redundant` 也会在本次响应里如实报数。两段窗口的最坏结果都只影响池内副本的取舍，**不碰主库一行**。窗口起点由 `main_snapshot_at` 如实暴露。

**`source_backup` 连带**：不逐条触发；仅当本批被剔空时，`_settle_batch`(:621-633) 会一并删原卷副本与本批残留切图。二次确认文案**当且仅当** `will_empty` 为真时明写这一句；响应回 `backup_removed`。

**与墓碑的关系**：主库 `questions` 一行不动（`:577` 原文「主库一个字节都不碰」）；物理删只发生在 `pending_questions` 与 `pending_assets/`，即「主库留墓碑、池子物理删」，与手册 §10.5 同向。

#### 3.5 前端交互

- `renderBatchList` :97-135：行从 `<button class="ed-batch-row">`(:111) 改为 `<div class="ed-batch-row" data-batch data-done>`，内部两个真按钮：
  - 主按钮 `<button class="ed-batch-open">`，承接现有 `openBatch`(:121) 与 `aria-label`(:120)，`done` 时 `disabled`（沿用 :116 语义）；
  - 次按钮 `<button class="ed-batch-purge">剔除重复</button>`，`pending_count >= 1` 时渲染（`done` 行走 :116 的 `disabled` 分支，其 `pending_count` 恒为 0，自然不渲染）。
    - 为何不是 `>= 2`：§3.2 的 `reason:"bank"` 组是「池内单条 vs 主库命中」，典型场景恰是批内只有 1 条待审题（`pending_count == 1`）。写 `>= 2` 会让这类批次永远不出按钮，`reason:"bank"` 契约在真机上不可达，本任务卡对该类批次等于不存在。
    - `pending_count` 只回答「池里有没有东西可查」；「查出来有没有重复」一律由 dry-run 的 `groups`/`redundant` 回答，不由行数推断。
  - 无障碍：两键各自 ≥44px、`focus-visible` 可见；主按钮文案保持「未审 n / N」读屏串不变。
- 点次按钮 → `hostCall("pending.batch_duplicates", {batch_id})` → 打开 `#epBatchPurgeModal`（新增，DOM 形状照 `dist/index.html:400` 的 `role="dialog" aria-modal="true"`）。
  - **dry-run 得 0 组**（`groups` 为空）：弹窗只显示一行「本批没有重复题」（后附 `scanned` / `main_scanned` 两个实读数字），**不出执行按钮**，只留「关闭」。
  - 有组：分两块渲染 `batch` / `bank`（reason 徽标 + 保留者 + 将删条数 + 指纹前 8 位）；`batch` 组默认勾选，`bank` 组**默认不勾选**（裁决①，老师可自行勾）；底部「执行剔除（当前勾选 N 道）」随勾选实时改数，N=0 时 `disabled`；「取消」恒可点。
  - **勾选粒度定死（G12）**：checkbox 落在**每一条 `drop` 条目**上（不是整组一个），每组标题栏另给「全选 / 全不选」快捷勾；`keep` 行只显示「保留」徽标、**没有 checkbox**（它就是 S5c 要保护的那条，前端不给任何可勾入口）。选中集合 = 所有已勾 `drop` 的 id 并集，始终升序提交。
- **剩余数实时重算**：弹窗持有 `scanned` 与当前勾选数，`remain = scanned - selected.length`；`remain == 0` 时立刻显示红字「本批将归零：原卷副本与残留切图会被一并删除，不可恢复」，并把 `allow_empty` 置 `true`；`remain > 0` 时该红字隐藏、`allow_empty` 恒 `false`。服务端 `will_empty` 只用于打开弹窗时按默认勾选预置这句文案（默认勾选可能已归零）。
- 执行 → `hostCall("pending.purge_duplicates", {batch_id, drop_ids, expected_drop_ids, allow_empty})`；口径见 §3.2：`drop_ids` = **当前勾选集**升序，`expected_drop_ids` = 同一集合回显，`allow_empty` = `remain == 0`。执行中按钮 `disabled` + `aria-busy="true"`。
- 200 → `refreshBatches()`(:158-175) 重拉卡片并 `dock` 报账「已剔 N 道」；若 `new_redundant > 0` 追加一句「还有 M 道重复未剔除（主库组默认不勾），可重扫复核」，次按钮保持可点。
- 409 `batch_purge_selection_stale` → 关弹窗并提示「清单已变，已重新扫描」，自动重跑 dry-run。
- 409 `batch_purge_keep_selected` → 关弹窗并提示「清单已变，已重新扫描」，自动重跑 dry-run（与 `selection_stale` 同一条处置路径；正常 UI 勾不到 keep，出现该码只可能是 API 直投或清单已漂移，重扫是唯一正确的收敛动作）。
- 400 `batch_purge_empty_not_confirmed` → 弹窗保持打开、按当前勾选重算并显示归零红字（前端状态与服务端判定不一致时的兜底）。
- `ui_modal.js`：`#openModalNode` :20-23 由「只认 `delModalEl`」改为「返回当前打开的模态节点」（`delModalEl` + 新 `batchPurgeModalEl`），Esc/还焦/Tab 圈逻辑 :33-62 直接复用，不改。

#### 3.6 改动面清单

| 文件 | 位置 |
|---|---|
| `app/core/pending_dedupe.py` | 新增 `DUPLICATE_REASONS`、`bank_rows_snapshot(provider_id)`（S0 全表行快照，连异常口径）、`bank_fingerprint_map(main_rows, text_keys)`（两阶段：先字键后图哈希）、`batch_duplicate_groups(batch_id, provider_id)`（复用 `_text_key`:32 / `_fingerprint`:45 / `_pending_image_hashes`:93） |
| `app/core/pending_bank.py` | 新增 `purge_batch_duplicates(batch_id, provider_id, drop_ids, expected_drop_ids, allow_empty)`（复用 `batch_row`/`refresh_batch`/`drop_assets`/`_settle_batch`） |
| `app/api/pending.py` | 两条新路由（读口无 token；写口对齐 :212） |
| `static/js/stage_command.js` | `RELAY_METHODS` :29-68 加 `pending.batch_duplicates`、`pending.purge_duplicates` |
| `static/js/stage_relay_io.js` | 读口分支（对齐 :144-147）；写口归入 :169-179 的 `questions:write` 组，body 走 `withWriteToken` |
| editor `dist/ui_batches.js` | `renderBatchList` :97-135 行结构改造 + 弹窗宿主调用 |
| editor `dist/index.html` | 新增 `#epBatchPurgeModal`（照 :400 形状） |
| editor `dist/ui_modal.js` | :20-23 多模态扩展 |
| editor `dist/ui_dom.js` | `:91` 附近增 `var batchPurgeModalEl = document.getElementById("epBatchPurgeModal");`，并在 `:200` 的 dom 导出表加 `batchPurgeModalEl: batchPurgeModalEl`（证据：`:91` `delModalEl = document.getElementById("epDelModal")`、`:200` `delModalEl: delModalEl`；`ui_modal.js:13` 取的就是 `deps.dom.delModalEl`，故新句柄必须经 `ui_dom.js` 注入，**不在 `ui_modal.js` 里就地 `getElementById`**） |
| editor `dist/panel.css` / `dist/layout.css` | `.ed-batch-row` 由按钮转容器的样式规则，按类名定位（V1 记 `layout.css:131/187`，本轮未复核） |
| editor `plugin.json` + 根 `plugins.json`（:71-85）+ 兄弟仓 `E:/jiuzhang-plugins/plugins.json` | version 2.9.0(:73) → 2.10.0 |

#### 3.7 测试判据

单测（新增 `tests/test_pending_purge.py`，`.venv` 解释器逐模块跑）：

1. dry-run 后池内行数、`batches.total`、`pending_count` 三项全部不变。
2. `reason:"batch"` 组 keep 为 seq 最小者（造 3 条同指纹、seq 1/2/3，断言 keep.seq=1）。
3. `reason:"bank"` 组只删池内行：主库预置一条同指纹，执行后 `questions` 行数不变、`existing_id` 原样在库。
4. **F2**：剔 3 道后 `batch.total == 原 total - 3`，`pending_count == SELECT COUNT(*)`，`done` 与 `live_after` 一致。
5. **F3-a**：只把 `expected_drop_ids` 里某一项换成同长度、同数量的另一个合法 `p_` id（`drop_ids` 不动）→ 400 `batch_purge_expected_mismatch_client`，零删除。
6. **F3-b**：把 `drop_ids` 与 `expected_drop_ids` **同步**换成一条本批真实存在、但指纹不等于任何同批/主库题的 id（同长度同数量）→ 409 `batch_purge_selection_stale`，池内行数与 `total` 均不变（证明「长度相等也拦得住」）。
7. `expected_drop_ids` 与 `drop_ids` 元素相同但顺序颠倒 → 200（服务端按升序比较，顺序不敏感）；`expected_drop_ids` 少一项 → 400 `batch_purge_expected_mismatch_client`，零删除。
8. `drop_ids` 含一条格式合法但**属于别批**（或池内不存在）的 id → 400 `batch_purge_pending_not_in_batch`，零删除；「本批存在但非冗余」的情形归第 13 条的 409，码分工见 §3.3 口径段。
9. 在 `refresh_batch` 上注入异常 → `rollback`，池内行数与 `total` 全部保持原值。
10. 无令牌 401；`pending.purge_duplicates` 只认 `questions:write`，不认 `bank.view`（视图插件调用 → FORBIDDEN，对齐 :173）。
11. 相似但指纹不等（题干差一字、`similarity` ≥ 0.92）的两条**不出现**在 `drop_ids`。
12. **子集执行**：dry-run 出 1 个 `batch` 组 + 1 个 `bank` 组；只勾 `batch` 组提交 → 200，`deleted` 只含 `batch` 组的 `drop`，`bank` 组那条仍在 `pending_questions`、主库 `questions` 行数不变，`new_redundant == 1`（那条未勾的 bank 组）。
13. **勾选失效**：取到 dry-run 的 `drop_ids` 后、提交前把主库目标题删掉（或改其题干使指纹不等）→ 409 `batch_purge_selection_stale`，零删除，`total` 与 `pending_count` 保持原值。
14. **重算后新增重复**：dry-run 之后、提交之前再插入一条与已勾选条同指纹的池内题 → 200，`deleted` 恰好等于提交的勾选集（新那条不删），`new_redundant == 1`。
15. **保留者保护**：勾选集里放进某个 `batch` 组的 `keep` id → 409 `batch_purge_keep_selected`，零删除。
16. **G5 回归**：某条 `keep` 同时与主库指纹全等 → dry-run 里它**只出现在 `batch` 组的 `keep`**，不出现在任何 `drop`/`bank` 组；只勾 batch 组执行 → 200 且 `new_redundant == 0`（不会永不清零）。
17. **剔空硬闸**：勾选后 `scanned - len(drop_ids) == 0` 而 `allow_empty=false`（含缺省）→ 400 `batch_purge_empty_not_confirmed`、零删除、原卷副本仍在；同一载荷把 `allow_empty=true` → 200 且 `backup_removed == true`。

真机：editor 打开批次列表 → 点「剔除重复」→ 弹窗 → 执行 → 卡片 `total` 从 N 变 N-k、`pending_count` 同步；`.system_generated/pending_purge_probe/<tag>/probe.json` + 截图（弹窗态、执行后卡片态各一张）。`probe.json` 按 `clean_for_release` 可识别的 ① `checks[]` + `passed/total` schema 落盘。

#### 3.8 风险与回滚

- 误剔不可逆 → 四重闸：只吃指纹全等 + 清单必须人看（`batch` 默认勾 / `bank` 默认不勾）+ 勾选集逐条判重（`expected_drop_ids` 只保证载荷自洽，真正的护栏是 S5 的逐条判重与保留者保护）+ 剔空必须 `allow_empty=true`（服务端硬闸，绕开前端文案也拦得住）。
- 主库竞态窗口已声明（§3.4 末），最坏是多剔/少剔一条池内题，不会碰主库。
- 回滚：撤掉 relay 两个方法即前端不可达，无 schema 变更、无数据迁移，回滚零成本。

---

### 4 [DESIGN] ② 3.6 — 下架 bank-ui「全库查重清洗」

#### 4.1 删除清单（逐文件，含保留边界）

**`plugins/org.jiuzhang.bank-ui/dist/ui_review.js`**
- 删：查重整段——`DUPE_FIELD_LABELS` :173-181、`loadDedupe` :183-205、`dupeChips` :207-228、`markDupeKept` :230-248、`buildDupeCard` :250 起，直到该模块 `renderDedupePanel` 出口为止（V1 记 :297-303 的合并逻辑与 :362-372 的「确认合并」，本轮实读到 :279，其余**按符号定位**，实施前先 grep `dupe` 把行号打齐）。
- 保留：review 视图整段（`loadReview`/`renderReviewPanel`/分页装配，与 :138-167 邻接）以及被 review 复用的 `el`/`appendRich`/`migrationFlags`/`mountPager` 依赖注入（`plugin.js:206-222` 传参）。

**`plugins/org.jiuzhang.bank-ui/dist/plugin.js`**（本轮逐行实读）
- 删 `:292-300` 整块（`:292` dupeCount、`:293-294` 按钮、`:295-297` role/aria、`:298` `data-dupe-tab`、`:299` `addEventListener`、`:300` `appendChild`）。
- 删 `:264` 的 `else if (state.view === "dedupe") loadDedupe();`。
- 删 `:303` `hintLabels` 的 `dedupe:` 键（对象只留 `review`）。
- 删 `:309` `wide` 里的 `|| state.view === "dedupe"`。
- 删 `:313-314` `else if (state.view === "dedupe") renderDedupePanel(body);`。
- 删 `:367` `if (state.view === "dedupe") return;`，并把 :368 的注释改述为「合并后宿主广播本题更新，去重成一次刷新」。
- 删 `:516-536`（`dedupe_scan` 命令）、`:538-584`（`dedupe_merge` 命令）。
- 删 `:225-226` 的 `loadDedupe`/`renderDedupePanel` 解构；删 `state` 里 `dupe*` 字段 `:55-67`（含 :55-56 注释）。
- **保留（明确不动）**：`state.view` 默认值 `"list"`(:46)——三视图收为 list/review 后默认落地页仍是列表，改成别的会改掉老师进插件的首屏；`:169` `applyBankQuery` 的 `if (state.view !== "list") state.view = "list";`（二值域下仍成立）；`:277` 列表页签的 `if (state.view !== "list")`；`:471` filter 命令的 `state.view = "list";`；`:232-234` 的标题与副标题/计数（F7：它们就在 `plugin.js`，不在 `index.html`）。
- **G9 勘误（原设计写错）**：`bank-ui` 内**没有** `hasCapability`；`plugin.js:219` 实为 `sourceLine: sourceLine,`（review 模块的依赖注入表一行，与能力判定无关）。`hasCapability` 是宿主侧 `static/js/stage_command.js:86`，由 `stage_relay_bank.js:17` 取用、`:219` 调用；`stage_relay_bank.js:219` 在 §4.1 要删的 `:214-255` 块内，删块即删该调用点，但 `stage_command.js:86` 的函数本体保留（`stage_inbound.js:185` 仍在用）。

**`plugins/org.jiuzhang.bank-ui/dist/index.html`**：**不改**。该文件 18 行、无标题与计数区、无 dedupe 命中；标题在 `plugin.js:232-234`（F7）。

**`plugins/org.jiuzhang.bank-ui/dist/plugin.css`**：**只删 `.cb-dupe*` 前缀规则块**（V1 记 :667 的 `.cb-dupe-merge-tip` 起，本轮未复核该文件，实施时按 `.cb-dupe` 前缀 grep 定位）。理由：`.cb-chip`（`:209`/`:210`/`:217` 等在 ui_review 中使用）被 review 段复用，`.cb-toast`/`.cb-body-review`（`plugin.js:310`）也被 review 或列表复用，一律保留；不按「整块删」处理，避免误伤。

**`plugins/org.jiuzhang.bank-ui/plugin.json`**（本轮逐行实读）
- 删 `contributes.commands` 的 `:199-209`（`org.jiuzhang.action.data.dedupe_scan`）与 `:210-241`（`...dedupe_merge`）。
- `capabilities` :19-22 保留（`bank.view` 在 :21，`bank.review`/`bank.topics` 仍靠它）。
- `permissions` :23-25 保留。
- `:8` description 去「与查重双栏审查」；`:5` version `1.0.1` → `1.0.2`。

**`app/api/bank.py`**
- 删 `GET /api/bank/plugins/{plugin_id}/duplicates` :402-416、`POST .../duplicates/merge` :418-452。
- 删文件头 `bank_dedupe` 别名导入（V1 记 `:21`，本轮未复核 → 按符号 grep）。删除后必须 grep `dedupe` 清零（`bank.py` 内不得留孤儿引用）。

**`static/js/stage_relay_bank.js`**：删 `:214-255` 整块（实读确认含 :219 的 `bank.view` 守卫、:225-229 scan、:240-254 merge 与 :246 的 `system.question_updated` 广播），并删 `:17` 的 `var hasCapability = deps.hasCapability;`（实读确认该文件内仅 :219 使用，删块后成死变量）。`hasCapability` 函数本体仍由 `stage_command.js:86` 提供、`stage_inbound.js:21,185` 使用，**不删**。删块后 `grep hasCapability static/js/stage_relay_bank.js` 必须归零。

**`static/js/stage_command.js`**：`:34` 删 `"bank.dedupe_scan", "bank.dedupe_merge",` 两项。

**`tests/`**
- `test_bank_dedupe.py`：删 `test_22` :580-589、`test_23` :591-594、`test_24` :596-601、`test_25` :603-617、`test_26` :619-633（五条，实读确认行界）。前 21 条引擎单测与 `_request`(:555-574)/`_total`(:575-578) **原样保留**——裁决②字面就是「只删五条 HTTP 测」，顺手清理辅助函数会扩大 diff，不做。
- `test_bank_split.py:251`：`assertIn('method === "bank.dedupe_scan" || method === "bank.dedupe_merge"', source)` → 改 `assertNotIn`（保留为回归护栏：防止有人把 relay 分支加回来却不加命令声明）。
- `test_stage_canvas.py:285-296`（`test_05_dedupe_is_provider_only_and_copys_are_bounded` **整段重写**为 `test_05_dedupe_channels_retired`）：本测三条命门全绑在被删代码上，**不是只改两行**。
  - `:287` `assertIn('"bank.dedupe_scan", "bank.dedupe_merge"', STAGE, ...)` → `assertNotIn`。
  - `:288-289` 的 `block = STAGE[STAGE.index('if (method === "bank.dedupe_scan"'):STAGE.index('if (method === "bank.stats"')]` 这个 `block` **就是从待删的 `stage_relay_bank.js:214-255` 切出来的**（实读：该分支只在 `stage_relay_bank.js:214/:225`，不在 `stage.js`）；该块删掉后 `.index()` 直接抛 `ValueError`，故依赖 `block` 的 `:290`(provider 守卫) / `:291`(FORBIDDEN) / `:292`(`/duplicates`) / `:293`(20 副本上限) / `:294`(ID_RE) / `:295`(withWriteToken) / `:296`(merge 广播) **七条断言随 `block` 整块删除**。
  - 替代护栏（三条，全文件口径）：`assertNotIn('"bank.dedupe_scan"', STAGE)`、`assertNotIn('"bank.dedupe_merge"', STAGE)`、`assertNotIn('method === "bank.dedupe_scan"', STAGE)`。实证：`bank.dedupe_scan|bank.dedupe_merge` 在 `static/js/` 里只命中 `stage_command.js:34` 与 `stage_relay_bank.js:214/225`，删后应为 0。
  - **禁止**写成 `assertNotIn("/duplicates", STAGE)`：3.5 新增的 `pending.batch_duplicates` 会合法地把 `/duplicates` 带回 `static/js/stage_relay_io.js`，该断言必误伤。
- `test_command_registry.py:453-454` 期望表去两 id；`:456` 的 `requires_user` 列表去 `dedupe_merge`。
- `test_agent_command_tools.py:35` 删 `MERGE = "org.jiuzhang.action.data.dedupe_merge"` 并清掉全部引用（`grep MERGE` 归零）。

**`tools/`**
- `tools/dedupe_probe.py` 整文件删（本轮未核文件存在，按名定位）；**替代**：新增 `tools/bank_ui_smoke_probe.py`（F9）——打开 bank-ui、断言页签只剩「题目列表」「待审任务」、两面切换无错误、`/api/bank/plugins/*/duplicates` 请求计数为 0、`/api/plugins` 返回的 bank-ui `commands` 不含两 id，出 `probe.json` + 截图。
- `tools/command_contract_probe.py`、`tools/command_ai_probe.py`：删两 id 的期望项（V1 记 `:54-55/:70/:336` 与 `:55`，本轮未复核，按字符串定位）。

**文档**
- `docs/API_REFERENCE.md` §2.17 两节删除（V1 记 :314-332、:427-428，本轮未复核）。
- `docs/PLUGIN_SPEC.md` 去 dedupe 命令示例（V1 记 :1225-1234 等，未复核）。
- `docs/PROJECT_MEMORY.md` 历史章节不改，仅在章节头加一行「已于 2026-11-05 下架，代码见 git 历史」。

#### 4.2 版本与索引同步时序（消解 F4）

1. **同一次 commit** 内改三处版本：`plugins/org.jiuzhang.bank-ui/plugin.json:5` → `1.0.2`、根 `plugins.json:25` → `1.0.2`（描述 `:28` 同步去查重）、兄弟仓 `E:/jiuzhang-plugins/plugins.json` 同条目 → `1.0.2` 且与其镜像逐字节一致。
2. 跑 `tools/sync_plugin_index.py`（要求 `E:/jiuzhang-plugins` 存在），保证两份 `plugins.json` 逐字节全等（L0 红线 4）。
3. 跑 `tools/build_plugin.py --all` 重打 zip（写 `dist/`）。
4. 跑 `bash scripts/check-quick-gate.sh`：第 33 步 `check_plugin_index_parity.py` 会校验「索引 version == 清单 version」（脚本 `:5` 与 `:83-88` 实读），**先改版本再跑门禁**，绿了才 commit。
5. 版本号取值理由：删两条命令与两个页签属向后兼容的能力删减，补丁位 +1 → `1.0.2`；`min_host_version` 不动（`plugin.json:11` = 1.0.0）。

#### 4.3 改动面清单（汇总）

`plugins/org.jiuzhang.bank-ui/{dist/ui_review.js, dist/plugin.js, dist/plugin.css, plugin.json}`、`app/api/bank.py`、`static/js/stage_relay_bank.js`、`static/js/stage_command.js`、`tests/{test_bank_dedupe.py, test_bank_split.py, test_stage_canvas.py, test_command_registry.py, test_agent_command_tools.py}`、`tools/{dedupe_probe.py(删), 新增 bank_ui_smoke_probe.py, command_contract_probe.py, command_ai_probe.py}`、`docs/{API_REFERENCE.md, PLUGIN_SPEC.md, PROJECT_MEMORY.md}`、根 `plugins.json`、`E:/jiuzhang-plugins/plugins.json`。

#### 4.4 测试判据

单测/契约：
1. `test_bank_split.py:251` 反转后通过；`test_stage_canvas.py:285-296` 整段重写后通过（见 §4.1 三条替代护栏）；`test_command_registry.py` 期望表不含两 id；`test_agent_command_tools.py` 全绿。
2. `tests/test_bank_dedupe.py` 保留的 21 条全绿（引擎未被触碰的实证）。
3. `tools/audit_code.py` 复跑：ERROR 0 / WARN 36 / INFO 4。若实跑低于 36（删除的代码里原本带 WARN 项），**不改基线、不造假数**，按 R05 在回传单记偏离并说明是哪一项消失。
4. `tools/run_all_tests.py` 全绿。

真机（F9）：
5. `tools/bank_ui_smoke_probe.py`：bank-ui 打开后只有两个页签；点「题目列表」「待审任务」各一次无报错、无空白；`GET .../duplicates` 请求数 0；`/api/plugins` 里 bank-ui 的 `commands` 数组长度 2。`probe.json` 按 ① `checks[]` + `passed/total` schema 落盘。
6. 页面控制台无 404/500；截图两张落 `probe.json`。

#### 4.5 风险与回滚

- 删掉的是成熟能力：需求回来要重写前端。缓解=引擎（`bank_dedupe.py` 全文件）与前 21 条单测都在，重建只差前端 + 两条路由。
- 静默失去后端兜底：删路由后旧版 bank-ui 若仍装着并调用 `bank.dedupe_*`，会拿到 `COMMAND_NOT_FOUND`（`stage_command.js` 的白名单已无该法）。这一条属预期行为，`bank-ui` 1.0.2 与底座同轮发布即可覆盖。
- 回滚：单 commit 整体还原；无 schema 变更、无数据迁移。

---

### 5 [DESIGN] ③ 4.3 — 录题辅助栏 LaTeX 清洗强制预览防呆

#### 5.1 现状证据（本轮实读）

- `dist/ui_ai.js#cleanViaHost` :234-296：`:241-245` 组段 → `:252-254` `Promise.all` 调 `text.clean_latex` → `:255-263` 拼 patches（`ok` 由插件侧算）→ `:264-272` 有不可用段就整体中止 → `:274-281` 逐段 `hostCall("editor.apply_patch", {id, field, value})` **直接回填** → `:283-288` 只报账。**全程无预览**。
- 段边界：`dist/core_ai_fields.js#fieldRanges` :33-52，题干段止于 `choices.beginAt`(:39-41)，解析段跳过「答案：」首行(:44-49)；`fieldLabel` :54。
- 出参：`app/core/question_parser.py#clean_dirty_latex` :206-240，返回 `{text, changed, rules, options}`(:235-240)，**无 `ok` 字段**；`rules` 是去重后的规则名列表，**无位置、无计数**；`options` 非空表示原文里剥出了 `\begin{choices}` 块。
- 跨帧：`dist/ui_approve.js:164` publish `editor.dup_review`；`dist/core_protocol.js:90` 收 `editor.canvas_state`、`:114` 收 `editor.dup_review`；`static/js/core_bus.js` `PUBLISH_ALLOW` :14-27 已含 `editor.canvas_state`(:22) 与 `editor.dup_review`(:26)；`static/js/stage.js` :51 `EDITOR_PLUGIN_ID`，:522-523 按 `payload.pluginId !== EDITOR_PLUGIN_ID` 找画布页签。
- 弹窗范式：`dist/ui_modal.js` :25-31 取首钮焦点、:33-40 还焦、:42-62 Esc/Tab 圈。

#### 5.2 事件契约（含回执与降级）

- **辅助栏 → 画布**：`editor.clean_review`
  ```json
  {"open": true, "key": "<patch 目标 id>",
   "sections": [{"field":"stem","label":"题干","before":"...","after":"...","changed":true,"rules":["delimiter","fullwidth"]}]}
  ```
  `open:false` 只带 `key`，用于收浮层。
- **画布 → 辅助栏（回执，新增）**：`editor.clean_review_state`
  ```json
  {"key":"<同 key>", "phase":"opened" | "closed" | "tab_not_live", "reason":"user_esc|user_close|replaced"}
  ```
- **落点**：仍走 `editor.apply_patch`（不改方法名、不改载荷形状），逐段 `{id, field:"stem"|"solution", value}`。
- **宿主中继**：`static/js/stage.js` 新增 `editor.clean_review` 路由（仿 :522-523 按 `EDITOR_PLUGIN_ID` 找画布页签）。**找不到 live 画布页签时，宿主直接向发起页签回投 `editor.clean_review_state{phase:"tab_not_live"}`，不发请求**（消解 F8「非 live 在协议上不可判」）。画布侧收到后回 `opened`；Esc/关闭时回 `closed`。
- **降级（定死）**：2 秒内未收到 `opened`，或收到 `tab_not_live` → 面板置 `panel.clean.degraded=true`，只显示纯文字摘要（段名 + `rules` 标签 + 字符数变化），**四个按钮全部 `disabled`**，摘要行标注「画布未打开，无法替换」。理由：`apply_patch` 的落点在画布，画布不在时按下按钮必然是死键，比「不阻断」更诚实。
- `editor.clean_review` 只投 `EDITOR_PLUGIN_ID` 的另一个页签，**不进 `system.*` 广播**。

#### 5.3 交互时序

1. 老师点 `#epAiClean`（`dist/index.html:353`，id 与文案不动）→ `cleanViaHost` 照旧调 `text.clean_latex`（:252），**不再** 调 `editor.apply_patch`。
2. patches 收进 `panel.clean = {key, sections, state:"reviewing"}`；任一段 `options` 非空 → 该段 `disabled=true`。
3. 面板段三渲染摘要：每段一行，`changed:true` 的段出两个按钮——`#epCleanApplyStem` + `#epCleanDropStem`，或 `#epCleanApplySolution` + `#epCleanDropSolution`；`changed:false` 的段只显示「未改动」，**不出按钮**。
4. publish `editor.clean_review`；画布扩展 `dist/ui_dup.js`（:11 注释里那套「由宿主事件驱动、无按钮」的浮层）同时认 `editor.clean_review`，逐段渲染两张卡（左「现在」右「清洗后」），逐字高亮由插件侧自算 LCS（`rules` 只当类别标签，因为它无位置无计数）。开成回 `opened`，关时回 `closed`。
5. 老师点某段的「采用替换」→ 仅该段 `hostCall("editor.apply_patch", {id, field, value: after})` **一次**；该段按钮变为「已替换」，另一段按钮照旧可用（裁决③：分段落，互不牵连）。
6. 两段都进入终态（已替换 / 已放弃）→ publish `editor.clean_review{open:false}` 收浮层，`panel.clean.state="done"`，`panelSay` 报账。
7. 「放弃」只改本地态，不发 `apply_patch`。
8. 回执 `closed` 到达 → 面板把焦点还到 `#epAiClean`（`focus()` 在面板帧内执行；跨 iframe 不可行，因此**只以回执为触发**，不以画布 DOM 为准）。

#### 5.4 无源码泄露

- `before`/`after` 只在宿主中继与画布 iframe 之间传递，主题固定投 `EDITOR_PLUGIN_ID`，不进 `system.*` 广广播、不落盘、不写 `extensions`、不改题目结构。
- 辅助栏摘要只渲染段名/规则标签/字符数，不把清洗前后正文写进面板 DOM。
- 预览态纯内存，保存动作仍由老师按既有存库路径发起。

#### 5.5 改动面清单

| 文件 | 位置 |
|---|---|
| `dist/ui_ai.js` | `cleanViaHost` :234-296 改为「清洗→预览→逐段采用」；新增 `onCleanApply(field)` / `onCleanDrop(field)`；`panel.clean` 状态 |
| `dist/index.html` | :353 `#epAiClean` 下方新增段三摘要容器与四按钮（`epCleanApplyStem`/`epCleanDropStem`/`epCleanApplySolution`/`epCleanDropSolution`） |
| `dist/ui_dom.js` | :66 附近补这五个节点的取句柄 |
| `dist/ui_dup.js` | 扩展为同时服务 `editor.dup_review` 与 `editor.clean_review`；新增 LCS 逐字高亮；发 `editor.clean_review_state` |
| `dist/core_protocol.js` | :114 旁并列分派 `editor.clean_review`；:90 旁并列处理 `editor.clean_review_state` |
| `dist/panel.css` / `dist/panel_dialog.css` | 摘要行与预览浮层样式（按类名定位） |
| `dist/core_ai_fields.js` | `fieldRanges` :33-52 复用，**不改** |
| `static/js/core_bus.js` | `PUBLISH_ALLOW` :14-27 加两主题（紧邻 :22/:26 的既有 `editor.*` 项） |
| `static/js/stage.js` | 新增 `editor.clean_review` 路由 + `tab_not_live` 回投 |
| `plugins/org.jiuzhang.editor/plugin.json` | `bus.publish`/`subscribe` 两处（实读 grep 到 :79-80、:88-89 均列 `editor.canvas_state`/`editor.dup_review`）同步加两主题；version → `2.10.0`（与 3.5 共用一次升版）+ 根 `plugins.json:73` + 兄弟仓索引 |

#### 5.6 测试判据

单元/静态：
1. `text.clean_latex` 出参键集合仍为 `{text, changed, rules, options}`（清洗端一行未改）。
2. `dist/ui_ai.js` 内 `editor.apply_patch` 的调用点只出现在 `onCleanApply` 内；`cleanViaHost` 函数体内调用数为 0（grep 断言）。
3. `core_bus.js` `PUBLISH_ALLOW` 含两主题；editor `plugin.json` 两处 bus 列表含两主题。

真机/像素（`prove-visual-change` 口径）：
4. 点 `#epAiClean` 后：画布浮层出现、左右两栏各一张卡；探针监听 request，`editor.apply_patch` **计数 0**；两栏截图落 `probe.json`，像素扫描左右区域差异比 > 0。
5. 点 `#epCleanApplyStem` 后：画布源码快照中 stem 段 == `after`；`choices` 块与「答案：」行与前一快照**逐字节相等**；`apply_patch` 计数恰好 1 且 `field=="stem"`。
6. 再点 `#epCleanApplySolution` → 计数变 2 且 `field=="solution"`，stem 段不再变动。
7. 喂一段已规范文本 → 该段无按钮、显示「未改动」，该段 `apply_patch` 计数 0。
8. 喂带 `\begin{choices}` 的段（`options` 非空）→ 该段按钮 `disabled`，`apply_patch` 计数 0。
9. Esc 关预览 → 面板收到 `phase:"closed"`，`document.activeElement.id === "epAiClean"`（面板帧内断言）。
10. 关闭画布页签后点清洗 → 面板收到 `tab_not_live`，四按钮 `disabled`，摘要可见。

#### 5.7 风险与回滚

- 多一跳 `editor.clean_review` 引入新失败面 → 兜底为「2 秒超时 / `tab_not_live` 即降级为纯摘要 + 按钮禁用」，**绝不静默直填**（这是本次防呆的全部意义）。
- 逐字高亮由插件侧 LCS 自算，长段（>20k 字，`CLEAN_TEXT_MAX` 上限）会拖慢渲染 → 超过 8000 字只做整段左右对照、不出逐字高亮。
- 回滚：删两主题与四个按钮、`cleanViaHost` 退回直填，单 commit 还原；无 schema、无数据影响。

---

### 6 F1~F12 消解对照表

| F | 改在哪节 | 具体改了什么 | 残余风险 |
|---|---|---|---|
| F1 | §0 | 三条裁决写成唯一取值表（取值/契约影响/测试影响），全文无「待裁决」字样；V1 结尾的三个待裁决问题整段删除 | 无 |
| F2 | §3.4 S7、§3.7-4 | 事务清单补 `UPDATE batches SET total = MAX(total-?,0)` + `refresh_batch`，与 `delete_pending:589-594` 同构；新增「剔 3 道后 total 减 3、pending_count = 真实行数」判据 | 无 |
| F3 | §3.2、§3.3、§3.4 S5、§3.7-5~8/12~17 | 期望值定死为 `expected_drop_ids` 回显校验；按裁决①补丁改为**勾选集子集语义**：逐条判重（`batch_purge_selection_stale`）+ 保留者保护（`batch_purge_keep_selected`）+ 差集报数（`new_redundant`），删除「集合不等即 409」的旧码；第 4 轮勘误再删冗余 `digest`、加 `allow_empty` 剔空硬闸 | 「同长度换人」若换成两条都真重复的 id，删的仍是真重复题，属勾错而非数据风险 |
| F4 | §4.2、§3.6 末行、§5.5 末行 | 补两仓 `plugins.json` + `sync_plugin_index.py` + `build_plugin.py --all`；定死 bank-ui `1.0.2`、editor `2.10.0`（3.5+4.3 共用一次升），并写清「先改版本再跑 parity 门禁」时序 | zip 产物不进 git，封版时需重打一次（属流程） |
| F5 | §0 裁决②、§4.1 tests 段 | 写死只删 test_22~test_26（实读行界 :580-589/:591-594/:596-601/:603-617/:619-633），21 条引擎单测与 `_request`/`_total` 保留；WARN 维持 36 | 若实跑 WARN 掉到 35，按 R05 记偏离（§4.4-3） |
| F6 | §4.1 plugin.js 段 | 改为「删 :292-300 整块 + :264/:303/:309/:313-314/:367/:516-584」，`state.view` 三值域收为 list/review，**默认 `"list"`(:46) 不动**；逐条列出 :46/:169/:277/:471 四处复位行的去留 | V1 漏掉的 :298/:299 已补 |
| F7 | §4.1 index.html 段 | 改为「`index.html` 不改；标题与计数在 `plugin.js:232-234`，不在 ② 范围」 | 无 |
| F8 | §5.2、§5.3-8、§5.6-9/10 | 加 `editor.clean_review_state` 回执（`opened`/`closed`/`tab_not_live`，由宿主在无 live 画布时直接回投）；「焦点回 `#epAiClean`」改写为「回执 `closed` 触发、面板帧内 focus()」；`options` 非空 → 按钮 disabled 且 `apply_patch` 计数 0 写成判据 | 2 秒超时阈值是拍的，可调 |
| F9 | §4.4-5/6、§5.6-4/5 | ② 补 `bank_ui_smoke_probe.py`（替代被删的 `dedupe_probe`）；③ 补像素证据与「未点采用时源码快照逐字节相等」判据 | playwright 未进 `requirements.txt`，探针只能本机跑（§7） |
| F10 | §1 | 3.5 写「泛化点 + 扩展成本声明」（`DUPLICATE_REASONS` 枚举落点、新增第三类改 **7 处 / 4 个文件**、零表改），与 §1 用同一数字、同一单位定义 | 无 |
| F11 | §3.3、§3.4 S1 | 错误码表给 HTTP 状态 / `detail.code` / retryable 三列；定死「batch 不存在→404，drop 中的 id 不存在或属别批→400」；409 `retryable:true` | 无 |
| F12 | §3.4 S0/S4 | S0 只做一次主库行快照（不读图）；S4 两阶段——全表只走 `_text_key` 归一，图哈希只对文字键命中的行做；分组成 O(N+M) | 万行主库整表入内存未实测（`similarity_report:261-263` 已是同款读法） |

#### 6.1 第 3 轮 G1~G12 勘误（errata，未重启设计全链）

| G | 改在哪节 | 改法 |
|---|---|---|
| G1（第 3 轮已修） | §3.5 | 次按钮阈值 `pending_count >= 1`，单条批次 + 主库命中场景可达 |
| G2（第 3 轮已修） | §4.1、§3.6 | `test_stage_canvas.py` 整段重写 + `ui_dom.js` 句柄落点 |
| G3（第 3 轮已修） | §3.2/§3.3/§3.4 | 删死字段 `main_truncated`，补主库侧 404/400 |
| G4（第 3 轮已修） | §1、§6 | 处数统一（本轮再改为 7 处 / 4 个文件） |
| G5 | §3.4 S4-4c、§3.2 响应、§3.7-16 | `batch` 组的 **keep 也不再列进 `bank` 组**；`new_redundant` 的重算全集不含任何 keep；新增 G5 回归用例 |
| G6 | §3.2 出参、§3.5 | `redundant`（全集条数）与 `drop_ids`（默认勾选集）口径分开写死，示例四组与 `redundant:4` 自洽；`live_after`/`will_empty` 明确按默认勾选集算 |
| G7 | §3.2 写口、§3.3、§3.7-7、§3.5 | **删 `digest`**：与 `expected_drop_ids` 完全冗余，且沙箱无可靠 sha256；错误码只留 `expected_drop_ids` 不一致 |
| G8 | §3.4 S0/S4 | S0 只调 `bank_rows_snapshot(provider_id)`；`bank_fingerprint_map(main_rows, text_keys)` 只在 S4 调，签名与 §3.6 一致 |
| G9 | §4.1 保留段与 relay 段 | 删掉虚构的 `plugin.js:219 hasCapability`；`plugin.js:219` 实为 `sourceLine`，`hasCapability` 在宿主 `stage_command.js:86`；relay 的 `:17` 死变量一并删 |
| G10 | §3.4 S6、竞态段 | S6 去掉「集合已相等」；竞态主窗口改为 `[dry-run, 本次 S0]`，S0→S8 标为毫秒级残窗 |
| G11 | §1、§6-F10 | 扩展成本由 5 处改为 **7 处 / 4 个文件**（逐点列出） |
| G12 | §3.5、§3.3、§3.7-17 | 勾选粒度定死为**逐 `drop` 条目**、`keep` 无 checkbox；补 `keep_selected` 与 `empty_not_confirmed` 的前端处置；新增 `allow_empty` 服务端硬闸与用例 |
| 400/404 冲突 | §3.3 | `batch_id` 格式不合法与不存在统一 404（对齐 `list_batch_questions:140-141`），删除 400 `batch_purge_bad_batch_id` |
| 探针 schema | §3.7 真机、§4.4-5 | `probe.json` 定死走 ① `checks[]` + `passed/total` schema（WARN 收尾门禁可识别） |
| 判据 10 可达性（本轮 4.3 勘误，工序 06 · Eval-06 回环） | §5.6-10、§5.2 降级、§5.4、§5.7 | ①原判据（:543）写「关闭画布页签后点清洗 → 面板收到 tab_not_live，四按钮 disabled，摘要可见」，即要求降级界面在真机主路径可达。②实测（tools/latex_clean_probe.py tag 20261102-4.3e，判据 18，probe.json:161-169 与 metrics.canvas_closed:219-225）：关掉 editor 画布页签后宿主把右栏插槽改判给 AI 助手（docs/PLUGIN_SPEC.md:768「切走该页签，右栏立刻归还助手插件」、:786-787 助手是默认住户 reclaim），辅助栏插槽整体退场（panel_alive=false），「四按钮 disabled＋摘要可见」界面在真机主路径不可达——属既有装配行为，非 4.3 引入；命门仍守住：画布不在场时 apply_patch 计数不新增（patches=2，与关页签前两次采用持平），绝不产生回填。③修正后最终判据（可执行一句话）：画布不在场时点清洗，editor.apply_patch 计数不新增、绝不产生回填（必过项）；界面可达性二选一——辅助栏插槽在场时必按「2 秒超时 / tab_not_live → 纯摘要＋四按钮 disabled＋标注画布未打开，无法替换」降级（:494 原文照旧，此时仍须满足 AGENTS §6 键盘可达与状态不靠颜色），插槽随装配整体退场时退场本身即降级（发起键随插槽离开），不再另行要求界面可达。④探针「要么降级锁四键、要么辅助栏一并退场」的或口径自此由设计追认，追认日期 2026-11-02，依据 Eval-06 判 L2 不合格之回环（探针单边放宽未回写设计，现由设计追认收编，此后本条为该判据唯一勘误出处）。⑤约束：tab_not_live 回投（宿主 static/js/stage.js:530-546）与 2 秒超时降级（插件 dist/ui_ai.js:66 CLEAN_OPEN_TIMEOUT_MS、:176-182 降级、:202-207 tab_not_live 处置、:167 摘要文案）两支此后必须有单测钉住（Eval-06 已记「降级分支零单测」）；将来任何人改动右栏插槽的装配/归还条件，必须重开本场景复验。同处定性（§5.4，判表述歧义应勘误澄清、不立独立缺陷挂待办）：点【采用替换】后点【返回列表】经军令 #25 既有落盘路径把清洗结果写回中转池（probe.json:116-121 采用瞬间 same:true、:226 pool_after_leave 离场后被覆盖），该行为符合 §5.4「保存动作仍由老师按既有存库路径发起」——返回即老师本人发起既有存库动作、采用即明示改意，写入的恰是老师刚采用过的 stem/solution，未违军令 #25「静默写入不许抹老师没碰过的字段」（记忆卡 order25），且属既有机制非本轮引入。澄清口径：§5.6-12「池内仍与入池时逐字节相同」仅在【采用→未离场】窗口内成立，离场后池被清洗后文本覆盖属预期，探针判据 12 已在采用瞬间取证。若日后要「采用后仍可不留存离场」，另立新需求提案，不入本勘误。

---

### 7 遗留欠账与主公需知

1. **版本号已由主公认可**：`bank-ui` `1.0.1→1.0.2`（补丁位，删能力）、`editor` `2.9.0→2.10.0`（次版本位，加两个 relay 方法与两个事件）。由 coder 落，两仓索引必须同 commit。
2. **探针环境（主公已裁决口径）**：`playwright` 未写进 `requirements.txt`（AGENTS §9.6 环境坑⑥），4.4-5 与 5.6 的真机/像素证据只能在本机有 chromium 的环境出；本机有就跑，跑不了如实记「未验证」，不作设计阻塞、不得用单测顶替。
3. **死代码是有意保留的**：`bank_dedupe.duplicate_groups` / `merge_questions` 在删路由后零业务引用，仅由前 21 条单测覆盖（裁决②）。`bank_dedupe.py` 的 sql-fstring（裁决②给定 `:482`）继续贡献 WARN，静态基线维持 36。
4. **本轮未复核、实施时必须现场打行号**的位置（防行号漂移）：`bank_dedupe.py:482`、`ui_review.js` 的 :297-303/:362-372 与 `renderDedupePanel` 出口、`plugin.css` 的 `.cb-dupe*` 块、`app/api/bank.py` 的 dedupe 导入行、`tools/*_probe.py` 的 dedupe 引用行、`docs/*.md` 的相关段落、editor `layout.css` 的 `.ed-batch-row` 规则。本设计对这些一律按符号定位，未编造行号。
5. **3.1 前半（导入批次后台自动初查）本轮不做**，不在本设计的改动面内。
6. **3.5 是不可逆删除（主公已裁决接受）**：虽有三重闸（指纹全等 / 清单先看 / 勾选集逐条判重），剔空时仍会连带删原卷副本（`pending_bank.py:627-632`），弹窗文案必须在 `will_empty` 为真时明写；主公已知情并接受。

> 来源：architect-agent 第 2 版设计（Eval-04 第 1 轮回环后修订），逐字搬运；第 3 轮 P01~P25 与第 4 轮 errata（G5~G12 + 400/404 + 探针 schema）为勘误性修补，改动均登记在 §6.1，判定结论未改。

### 8 Eval-04 判定（外挂质检，只判不改）

> 以下为 eval-agent 原文摘录（第 1 轮结论只留状态，第 2 轮全文结构化部分），未改写。

**第 1 轮（F1~F12）**：四态 = 回环。L0 过、L1 否、L2 否，结构化失败清单 F1~F12 共 12 条；architect 已出第 2 版逐条消解。

**第 2 轮四态：回环** —— L0 证据核验全过（抽查 26 处行号断言无一处虚构），但 L1 有 1 处不可达路径、L2 有 1 处改动面漏项 + 1 处文档内自相矛盾、1 处口径缺口；均为小改，不需重做设计。

| 工序 | 层 | 过否 | 原因 |
|---|---|---|---|
| 04 设计 | G0 Shell Gate | N/A | 本工序不产码，无编译/测试/门禁可跑；PLAN P1~P5 已把每步门禁绑定到 `check-quick-gate.sh` / `run_all_tests.py` / `check-release-gate.sh` |
| 04 设计 | L0 证据核验 | 过 | 27 条抽查中 24 条精确、2 条标签/起行微偏（行界正确）、1 条为文档内数字不符；未发现编造行号或伪造输出 |
| 04 设计 | L1 公共语义 | **否** | G1：「一键剔除」在「单条批次 + 主库命中」场景下按钮不渲染，reason:"bank" 契约不可达；G3：主库不可用的错误口径与 `main_truncated` 取值规则缺失，边界异常未覆盖 |
| 04 设计 | L2 模块专属 | **否** | G2：3.6 改动面漏 `test_stage_canvas.py:292`（以及 `batchPurgeModalEl` 句柄落点）；G4：文档内 4 处 / 5 处自相矛盾 |

**F1~F12 复核**：F1 是、F2 是、F3 是、F4 是、F5 是、F6 是、F7 是、F8 是、F9 是、**F10 部分**（声明结构已具备，但 §1 写「4 处」、§6 F10 行写「5 处」）、F11 是（主项，残余转 G3）、F12 是（主项，残余为图哈希 I/O 成本建议）。

**结构化失败清单（回环）**

| # | 节号 | 层 | 原因 | 建议改法 |
|---|---|---|---|---|
| 1 | §3.5 前端交互 | L1 | 次按钮 `pending_count >= 2` 与 §3.2 `reason:"bank"` 单条场景互斥，契约不可达 | 改为 `>= 1`，空清单弹窗文案补一句 |
| 2 | §4.1 tests 段 / §3.6 | L2 | 漏 `test_stage_canvas.py:292`（及 block 变量）；`batchPurgeModalEl` 句柄落点未列 | 三条断言写全；改动面补 `dist/ui_dom.js` 或写明就地 `getElementById` |
| 3 | §3.2 / §3.3 / §3.4 S0 | L1 | 主库不可用无错误码；`main_truncated` 无触发规则（死字段） | 删字段或补截断规则；错误码表补 bank 侧 404/400 两行 |
| 4 | §1（:172）vs §6 F10（:507） | L2 | 同一数量写「4 处」与「5 处」，无单位定义，声明不可核验 | 统一为「5 处 / 4 个文件」 |
| 5 | §3.4 S4（建议级） | L2 | 「O(N+M)」只覆盖归一，未覆盖全表图哈希读盘 | 补两阶段筛选一句（可并入第 3 项同轮修） |

**放行前必须由主公知情的事项**
1. **裁决①的实际杀伤面**：把「与主库指纹全等」的池内题也纳入物理删除集，会让「一键剔除」一键删掉与主库重复的池内题。任务卡 3.5 的字面是「剔除本批次重复题」，与主库的重复本属 3.1/3.4 的裁决流。裁决已定、执行不质疑，只标注风险：建议弹窗把 `batch` / `bank` 两组分块显示、`bank` 组默认不勾选、执行按钮上明写将删条数——否则老师按任务卡理解点下去会多删。
2. **不可逆连带**：`will_empty` 为真时 `_settle_batch`（`pending_bank.py:627-632`）会一并删原卷副本与本批残留切图，设计已把这句话写进二次确认文案，但这是本轮唯一「删了找不回来」的路径，需主公确认接受。
3. **3.6 删的是成熟能力**：后端引擎与前 21 条单测保留，重建只差前端 + 两条路由；但删后 `bank_dedupe.duplicate_groups` / `merge_questions` 成零业务引用死代码，静态基线 WARN 36 里仍靠它占位（§7-3 已声明）。
4. **环境依赖**：§4.2 的索引同步要求兄弟仓 `E:/jiuzhang-plugins` 存在，缺失时 `check_plugin_index_parity.py` 直接 fail；`playwright` 未进 `requirements.txt`，3.5 的真机判据与 4.3 的像素证据只能在本机有 chromium 时出，CI 记「未验证」不得用单测顶替。
5. **探针报告格式**：新增的 `bank_ui_smoke_probe.py` 与 `pending_purge_probe` 的 `probe.json` 必须落在 `tools/clean_for_release.py` 能归一的三种历史 schema 之一（首选 ① `checks[]` + `passed/total`）；识别不了的 schema 收尾门禁会判不通过，这一条设计未写，需在实施前定死。
6. **未抽样项（本轮预算外）**：`drop_ids` 正则 `^p_[A-Za-z0-9_-]{8,64}$` 未与现有 `p_` id 生成规则对照 —— 若生成器产出更短的后缀，执行口会把所有 id 判 400；`ui_modal.js:20-23`、`ui_review.js:250-372`、`plugin.css .cb-dupe*` 三处行号未复核（设计已在 §7-4 声明按符号定位）。
7. **版本号取值**：bank-ui `1.0.1→1.0.2`、editor `2.9.0→2.10.0`（3.5 与 4.3 共用一次升版），待主公认可后可落。

**门禁四态结论**：工序 04 已连续 2 轮回环 → 按 `docs/AGENTS.md` §9 的「转人工」条，停止流水线，等主公裁决后决定是否开第 3 轮修订。

**第 3 轮四态：回环** —— 主公裁决「按推荐走，开第 3 轮」后复检：L0 抽查 34 条，33 条精确、1 条「查无此物」；L1 两条阻断、L2 五条可带病，全部为 3~6 行可订正项。

| 工序 | 层 | 过否 | 原因 |
|---|---|---|---|
| 04 设计 | L0 证据核验 | **否（1 条）** | G9：`plugins/org.jiuzhang.bank-ui/dist/` 全目录 `hasCapability` 0 命中，`plugin.js:219` 实为 `sourceLine: sourceLine,`；同一 `:219` 在 §4.1 一处写「保留」、一处落在待删块内，自相矛盾 |
| 04 设计 | L1 公共语义 | **否** | G5：batch 组的 `keep` 被再列进 bank 组当删除项 → `new_redundant` 永不清零 + 可勾却永 409 + 整批被拦；G6：dry-run 出参 `drop_ids`/`digest` 口径未与勾选集对齐，示例 2 条 vs `redundant` 5 条不自洽 |
| 04 设计 | L2 模块专属 | **否** | G7 客户端无 sha256（沙箱 `crypto.subtle` 未核）；G8 `S0` 仍写单参 `bank_fingerprint_map(provider_id)`，与 §3.6 两参签名矛盾；G10 S6「集合已相等」旧措辞、竞态窗口标 `[S0,S8]` 应为 `[dry-run,S0]`；G11「5 处/4 个文件」偏乐观（实为 6~7 处）；G12 勾选粒度未定死、`keep_selected` 无前端处置；400 `batch_purge_bad_batch_id` 与 `list_batch_questions:140-141` 的 404 惯例冲突 |

**eval 建议（原文要点）**：「不值得跑完整第 4 轮」——两道阻断都是 3~6 行订正，建议授权 errata 直通：architect 出 ≤10 行订正，reviewer 过一眼即交 coder 进 05；G5 的补法还需在 §3.7 增 1 条用例。另提醒：不可逆删除仍无服务端 `confirm_empty` 硬闸，持 `questions:write` 的插件可绕过前端文案清空批次。

**第 4 轮处置：errata 直通（主公已授权「按推荐走」）** —— 按 G5~G12、400/404 口径、探针 schema 逐条落笔，改动登记在 §6.1；未重启 01/03 调研，未改 PLAN 五步顺序。另采纳 eval 提醒，新增 `allow_empty` 服务端硬闸（§3.2 写口、§3.3、§3.4 S5e、§3.7-17）。

**reviewer-agent 复核（errata 后）**：Critical 0；7 项自洽检查全部通过（出参计数、digest 残留、G5 三处一致、allow_empty 五处闭环、404 口径、hasCapability 矛盾、7 处/4 文件）。3 条 Suggestion 已当场收口：`allow_empty` 改可选默认 false；`keep_selected` 前端改为重扫（keep 无 checkbox，原处置不可达）；S1 明确 `con = connect()` 与 S1/S2 共用连接、`finally close()`。

## [IMPL] 2026-11-02

<!-- 待 architect/coder/test 交付后由 recorder 汇编 -->

## [VERIFY] 2026-11-02

<!-- 待 architect/coder/test 交付后由 recorder 汇编 -->

## [VERIFY] 2026-11-02 (2)

> 工序 06 汇编（recorder-agent）。以下内容逐字搬运主会话本轮实测与 reviewer/eval 两份独立结论，recorder 未自行复跑门禁、未改写任何数字、未补写未出现过的结论；:659 的 `[VERIFY]` 空占位保留未动，本 `(2)` 为同阶段的正式交付。

### 1 工序 06 机械证据（主会话本轮实跑原文）

| 项 | 命令 | 当次输出 |
|---|---|---|
| 收尾门禁 | `bash scripts/check-release-gate.sh` | RC=0，「三大块全绿」 |
| 快门禁 | `bash scripts/check-quick-gate.sh` | PASS（6 项全过） |
| 插件索引一致性 | `check-plugin-index-parity` | PASS（两份索引全等、条目版本一致、Schema 示例自校验通过） |
| 静态审计 | `tools/audit_code.py` | ERROR 0 / WARN 36 / INFO 4（基线持平） |
| 全量回归 | `tools/run_all_tests.py` | 模块 76 个，用例 1469 个，失败模块 0 个 |
| 插件侧三查 | `fetch(` / `parent.document` / `localStorage` | 0 / 0 / 0 |
| 插件目录纯净 | `plugins/` 内 Python 文件 | 无 |
| 体系资产命名 | `.qoder` 资产（R00） | 合规 |

### 2 六支真机探针最新跑批与 tag

| 探针 | tag | passed/total | 时间 |
|---|---|---|---|
| editor_probe | 20261102-31h | 207/207 | @17:07 |
| latex_clean_probe | 20261102-4.3f | 22/22 | @17:40 |
| pending_purge_probe | 20261102-3.5d | 12/12 | @17:40 |
| command_contract_probe | 20261102-l2fix | 19/19 | — |
| command_ai_probe | 20261102-l2fix | 17/17 | @17:41 |
| bank_ui_smoke_probe | task36-smoke | 13/13 | @15:06 |

重跑理由：最后一次产品改动 `ui_batches.js` 16:44:45、`core_bus.js` 14:54:51、`app/core/plugins.py` 15:25:05，早于这些改动的跑批一律作废重取；`bank_ui_smoke` 未重跑（其 bank-ui 侧产品文件最晚 14:31，早于其 15:06 跑批）。

### 3 两道独立结论（原文要点，标注角色与轮次）

**`reviewer-31r3-focus`（工序 05，22 次调用内完成）**：Critical 0；S1~S4 四条 Suggestion——文件层删除在 commit 之后可能留残留切图、`bank_rows_snapshot` 全表读 I/O、`_BUS_PUBLISH` 全局集合可被任意插件发 `editor.clean_review`、`edCleanModal` 用 `aria-modal="false"`；自报因预算未核到 5 个测试模块与探针 diff 逐行、文档同步性仅 grep 级。

**`eval-31r3`（Eval-06 第 1 轮）**：L0/G0/L1 过、L2 否两条 → 回环（① 3.5 两条新路由未入 `docs/API_REFERENCE.md` pending 路由表；② §5.6-10 判据未按原文落地、探针自行放宽「或」口径未登记勘误且两支降级分支零单测）。

**`eval-31-r2`（Eval-06 第 2 轮，独立复跑）**：L0/G0/L1/L2 全过 → 放行；两条 L2 销账；两支 `test_06` 经只读破坏性推演确认非永真式；400 纠偏判对。

### 4 主会话对角色结论的两处纠正（如实记，属过程质量）

1. eval 第 2 轮称「行级点击兜底没有任何判据直接触发」——不采纳。`tools/editor_probe.py:652-663` 取行包围盒后打在 `x+4`（左内边距空白处，非按钮）并断言三栏起来，该判据在 `20261102-31h` 为 OK（detail `{"mode":"review"}`），且晚于 16:44 修复。
2. eval 第 2 轮请主会话复查「过程稿是否残留 409」——已复查：`:221/:235/:292/:329/:368` 五处均为 400 `batch_purge_empty_not_confirmed`，设计正文无残留；409 出自主会话派单转述错误，coder 按代码纠正为 400。

### 5 回环修补台账（本轮新增，逐条带文件:行号）

- `docs/API_REFERENCE.md:469-470` 两条路由行 + `:470` 入参类 400 `batch_purge_*` 收口句。
- `tests/test_stage_canvas.py:292-310` 与 `tests/test_clean_latex.py:166-199` 两支降级分支单测（后经复核把缩进字面量改为 `:305` 的先后关系正则、把写死 `= 2000` 改为 `:178/:181` 的「具名常量声明 + 被定时器引用」正则，阈值数值不再钉死；两支均无后行断言）。
- 过程稿 `:588` 判据 10 可达性勘误。

### 6 四条上报项的最终定性与去向

1. §5.6-10 已由设计追认收编（见 :588）。
2. 【跳到第 N 题】被滚动跟随抢走当前题 → eval 判探针锚点选错，非产品缺陷，教训建议沉淀到探针编写规范。
3. 31g 那次「【合并为解析二】」点击无后端动作（135/136、控制台零报错、后续 31h 与新增预检判据均绿、未复现）→ eval 记警告级观察项：根因线索是对比浮层 `edDupModal`（`aria-modal=false`）滞留拦截 pointer events，若复发应立独立 bug。
4. 采用后【返回列表】静默存回中转池 → architect 与 reviewer、eval 三方一致判表述歧义已勘误澄清、不立独立缺陷（返回列表即老师本人发起的既有存库路径，写回的是刚采用内容，不违军令 #25）。

### 7 R04 计数过时（待办登记，本条只登记不改文件）

`.qoder/rules/R04-test-workflow.md:29` 仍写「现 25 支 `tools/*_probe.py`」，本轮新增 `bank_ui_smoke_probe.py`/`pending_purge_probe.py`/`latex_clean_probe.py` 后该数字已失真——记为待办（改规则文件需另走 sys 记录，本条只登记）。

### 8 未 commit、未封版、未 push 的当前状态

工作树带全部在途改动；版本 editor `2.10.0` / bank-ui `1.0.2` 与两份 `plugins.json` 逐字节全等已就位，只剩 `tools/build_plugin.py --all` 重打 zip（含插件仓侧 zip 更新），`git commit`/`git push` 与封版均候主公明示授权。

### 9 未验证项（不得写成已验）

- 真机 JS 运行时行为（项目无 JS 执行器，两支新用例是源码静态断言）。
- `tab_not_live`/超时降级的界面可达性本身（按 :588 勘误，画布不在场时辅助栏插槽整体退场）。
- `latex_clean_probe` 判据「池内逐字节相同」仅在【采用→未离场】窗口成立。
- 覆盖率工具缺项。
- 铁律一逐字比对需旧项目访问权未做。

### 10 记录完整性核对（recorder 只核对，不代笔）

- REQ / PLAN / DESIGN / §6.1 勘误：均已存在，未改动。
- IMPL（:655）与 RELEASE（本节后）仍为空占位（`<!-- 待… -->`），应由 coder 出 IMPL 涉及文件清单、发版后由 recorder 补 RELEASE；recorder 不代写。
- 状态字段（文件头 :5）保持「进行中」：本轮未发布、未封版，不流转为「已发布」。

## [DESIGN-2] 2026-11-02 (3.1a 导入批次后台自动初查)

> 本节为军令 #31 任务卡 3.1 前半的工序 03/04 产物，纯追加，不改写任何既有行。本轮行号均经 Read/Grep 实读；标「需实施时现场核对」的为本轮未读实文。

### ① 现状证据（本轮全部实读）

- 初查缺失（本体）：`app/core/pending_bank.py#save_draft` 全函数体本轮通读（:121-255），全程无 `find_duplicate` / `batch_duplicate_groups` 调用；返回体只有 `batch_id / batch / saved_ids / saved_assets`（:233-255）。
- 两条入池路由：`app/api/pending.py#pending_save_draft`（:95-130，原样返回 save_draft 体）；`app/api/ingest.py#ingest_files`（:30-58，拖文件第二动线，落 `app/core/ingest.py#stage_ingest` :608 / `#_stage_one_batch` :676——**是否经 save_draft 未读实文，需实施时现场核对**）。
- 终局强校验已在位（复用不重做）：`pending_dedupe.find_duplicate`（:124）、`pending_bank.approve`（函数头定位 :504，本轮未复读函数体，任务卡 :504-541 区间按待核引用）、`duplicate_report`（:397）、`_refuse_different_answer`（:421）、`pending_approve` 的 409 翻译（:189-193）。
- 可复用引擎（只读幂等可重算）：`pending_dedupe.batch_duplicate_groups` :433-470——一次 `bank_rows_snapshot`（:314）全库快照 + `group_duplicates`（:363）批池遍历，返回 `groups/redundant/drop_ids/live_after/will_empty/main_scanned/main_snapshot_at`；成本 O(批+主库)，:434 原文明写「只读不写」。
- 「人工按钮」正是 3.1a 要消灭的：`GET /api/pending/batches/{id}/duplicates`（api :225-273）已存在，但只由老师点【剔除重复】触发（`plugins/org.jiuzhang.editor/dist/ui_batches.js:302` `hostCall("pending.batch_duplicates", ...)`）。降级口径先例：主库读不通 404/400、「不降级成没有重复」（:237-239）。
- 端侧逐题预检（边界另一侧）：`ui_approve.js#precheck` :138（注释 :137「后台查重：命中就把红字亮起来」），切题与 approve 路径调用（:289、:335）——只扫「当前一道」，且须切到那道题才扫，不满足「导入即扫」。
- 链路动线：`static/js/stage_command.js` pending 命令族 :42-50（`pending.batch_duplicates` 在读族 :50）；relay `static/js/stage_relay_io.js#relayPending` :138-183（batch_duplicates→GET :177-181）。
- 后台任务先例：路由层 `BackgroundTasks` 两段式 = `ingest.py:30/:54`（占位题响应后就地替换，`app/core/ingest.py` :608/:676/:701 函数头本轮 Grep 实读）；core 层 daemon 线程 = `app/main.py:143`；模块级 `threading.Lock`+进程内状态 = `app/core/basket.py:14/:23`、`plugin_state.py:20/:27`。
- 批次卡片路由 `pending_batches` :26-37 在位；**卡片字段构成本轮未读，需实施时现场核对**。
- 错误码风格：`BatchPurgeError` 默认 `status=400`、小写前缀码 `batch_purge_*`（api :244-271 示范）；R02 §2 不许开第三套命名域。
- editor「解析完成→批次列表刷新」的确切机制：**未验证，需实施时现场核对**（决定 ⑦R1 回投挂点）。

### ② 需求定性与泛化评估

**类问题**（R05 §5）：诉求是「任何入池动线落池即产批次级初判并回投界面」，非 editor 专属。
- 泛化方案：触发参数化为 `(batch_id, provider_id)`，挂在 `pending_bank.save_draft` commit 成功后的 core 层——editor `pending.save_draft`、拖拽 `ingest`、未来任何走 save_draft 的插件共享一处实现，无 editor 专属分支。
- 泛化点：批次卡片 `dedupe` 字段是通用批次级注解，任何读 `pending.batch_list` 的界面可自取。
- 扩展成本声明：新增入池入口 0 改动（core 挂点自动覆盖）；新界面要显示初查 = 一处渲染。
- 不强行泛化声明：初查结果不落库、不做状态机——它是可重算派生物，维持「缓存非事实源」定位。

### ③ 方案（时序 / 数据流）

**采纳 A：core 层后台初查 + 进程内缓存 + 批次卡片状态增量**（零新表零迁移）。

1. **谁触发（无人工点按）**：`save_draft` 事务 commit（:225）且 `con.close()`（:232）后，起一个 daemon 线程任务 `pending_dedupe.warm_batch_scan(batch_id, provider_id)`；活跃 provider 由调用方在路由层 `provider.resolve()` 后作参数传入（core 不发 resolve，守分层）。响应体加键 `dedupe_queued: true`（只增不改，向后兼容）。
2. **在哪跑**：底座进程内线程，响应发出之后——导入 HTTP 时长与主库行数解耦（沿 `ingest.py:7-9` 两段式先例与话术）。不新增 pip 依赖，标准库 `threading` 足够；全链路零出网（出网铁律无恙），功能自足装配符合主公长期偏好 1。
3. **算什么**：任务体就调既有 `batch_duplicate_groups`（不新写任何判重逻辑）。成功 → `_scan_cache[batch_id]={status:"done", scanned, redundant, main_scanned, at}`；异常（BankNotFound/BankError 等）→ `{status:"failed", code:"dedupe_scan_bank_unavailable", retryable:true, at}`。异常在任务内接住，绝不回传导入请求。
4. **幂等与并发**：缓存以 batch_id 为键覆盖写；同批重复触发即重复扫（纯只读、后写覆盖先写，**无双倍副作用**——池/主库字节初查一律不写）；同批并发按「后发覆盖」处理，末边沿单飞列为可选优化、不预造。跨批并发数=人手导入节奏，456 题主库量级无风险。
5. **怎么回投**：`GET /api/pending/batches` 每卡片附 `dedupe: {status,...}`（无缓存= `{status:"pending"}`）；editor 批次卡片渲染「本批 N 题疑似重复」红字（纯文本增量，不弹窗、不加占位页——尊重 2026-10-31 画布裁决与 R02 §5.3/A6 可访问性），刷新沿用导入完成后刷批次列表的既有路径（挂点行号实施时现场补）。**判据口径：「无需人工点按」= 不需要点任何专门的查重/剔除按钮；不要求导入完成瞬间必须在场，回到批次列表即自动在亮。**
6. **失败与降级**：初查失败 → 卡片显示「初查未完成（主库读不通），存入前仍会强校验」，绝不显示「没有重复」（与既有路由 :237-239 口径同向）；导入本身照常 201。底座重启 → 缓存失、回 `pending`，下次导入自然重温；**不做启动时自动全量扫描**。
7. **职责边界一刀切**：服务端批次初查＝「整批哪几题疑似重复」→ 批次卡片总提示（数据源 `batch_duplicate_groups`，导入即扫，3.1a 本体）；端侧切题预检＝「这一题怎么裁」→ 红灯/红字/对比浮层（数据源 `pending.duplicate` 逐题报告，切题触发，维持现状）。两者不互替、不共享缓存、不互相传导判定；终局裁决永远在 `approve` 强校验。

**否决 B：初查结果落库（新表/新字段）**——结果是「池内容+主库快照」的纯函数，幂等可重算、无历史语义；落库要迁移（pending_db `user_version` 6→7 + 备份 + 回滚 + 全套降级用例）却零正确性收益。**「为何不能只在响应体里带回」的正面回答**：响应体带回＝同步扫描，直接违反「导入不被长任务阻塞」硬约束，故响应体只带 queued 标记、结果走批次卡片异步回投。
**否决 C：导入后客户端逐题 `pending.duplicate` 预检**——O(批) 次 HTTP 往返、每次单题全表读（把前轮 G4「全表读」顾虑放大数百倍），且语义仍是「客户端驱动」，不是「后台自动初查」。

**错误码归域**：不新增 HTTP 状态码；进程内状态码 `dedupe_scan_*` 沿用 `batch_purge_*` 小写前缀风格与 `retryable` 语义（R02 §2 既有两套命名域之内）。

### ④ 非目标（范围一刀切）

- 不自动剔除/剔减：初查只显形；删题动作仍走 3.5【剔除重复】弹窗与老师拍板。
- 不改 `approve` 终局强校验、409 语义、overwrite/merge_solution 一行。
- 不加新表/新字段/缓存文件；`data/` 写入范围零扩张（不越 R03 §3.5 白名单）。
- 不做全库查重扫描、不做启动自动扫描、不新增定时器轮询机制。
- 不动 bank-ui；本轮不执行版本号与两份 `plugins.json` 逐字节全等（只在⑤点名）。
- 不改宿主信封结构、请求 id 口径、命令白名单（既有 `pending.*` 命令已够用）。

### ⑤ 改动面清单（文件级）

| 文件 | 改哪 |
|---|---|
| `app/core/pending_dedupe.py` | 新增模块级 `_scan_cache`/`_scan_lock`、`warm_batch_scan(batch_id, provider_id)`、`scan_state(batch_id)` |
| `app/core/pending_bank.py#save_draft` | :225-232 之后挂 daemon 线程任务；:233-255 返回体加 `dedupe_queued`；签名加 provider 参数（带默认值保内调兼容） |
| `app/api/pending.py#pending_save_draft` | resolve 活跃 provider 传入；返回体向后兼容 |
| `app/api/pending.py#pending_batches` | 卡片附 `dedupe` 字段（字段构造实施时现场核对后定） |
| `app/api/ingest.py#ingest_files` | 核实 `#_stage_one_batch` 是否经 save_draft：是则自动覆盖、**不得双挂**；否则在其两处入池点同挂 |
| `plugins/org.jiuzhang.editor/dist/ui_batches.js` | 批次卡片渲染 `dedupe` 三态文案（带文字不只靠颜色、加载态 `aria-busy`）；【剔除重复】弹窗不动 |
| `plugins/org.jiuzhang.editor/plugin.json` + 根 `plugins.json` + `E:/jiuzhang-plugins/plugins.json` | editor 2.10.0→2.11.0，三份逐字节全等（本轮点名不执行） |
| `tests/test_pending_dedupe_scan.py` | 新增模块；若起服务必带 `JZO_RESTART_DISABLED=1`（R04 §1.6） |
| `tools/editor_probe.py` | 新增 `3.1a` 场景；`probe.json` 维持 `checks[]+passed/total` 可归一 schema（R04 §2） |
| `docs/API_REFERENCE.md` | pending 路由/卡片字段表补 `dedupe`（前轮 Eval-06 第 1 轮拒收教训） |

能力绑定（coder 可用 domain skill）：`add-host-api`、`run-regression`、`prove-visual-change`；base：`sync-biz-record`。

### ⑥ 可执行验收判据

1. 单测：一批含 1 道「与主库指纹全等」的题调 `save_draft`，返回后短 join 完成，`scan_state(batch)` 为 `done` 且 `redundant>=1`——除 save_draft 本身外无任何触发方（「无需人工点按」本体判据）。
2. 单测：`save_draft` 返回时刻 `scan_state(batch).status ∈ {pending, running}`（判重不在请求同步路径上——导入不被长任务阻塞）。
3. 单测：同批次连续两次 `save_draft` 追加题，`scan_state` 该批次仍仅一条、`scanned` 与第二次后的池数一致；池与主库行数差值=入池题数（初查零写字节——幂等无双倍副作用）。
4. 单测：mock `bank_rows_snapshot` 抛 `BankError` → `scan_state` 为 `failed` + `code="dedupe_scan_bank_unavailable"` + `retryable=true`；`save_draft` 仍成功（主库不可用不拦导入）。
5. 单测：`GET /api/pending/batches` 无缓存时卡片含 `dedupe.status="pending"` 且既有键零缺失（向后兼容）。
6. 单测：`test_pending_dedupe`（既有引擎用例）与 `test_pending_api` 保持全绿；`audit_code.py` ERROR 0；插件三查（`fetch(`/`parent.document`/`localStorage`）命中 0。
7. 真机探针（editor_probe 新增场景；隔离 `JZO_DATA_DIR`/`JZO_PLUGINS_DIR` 落 `.system_generated/editor_probe/<tag>/`、`free_port()`、`JZO_RESTART_DISABLED=1`、判据不写死插件版本、计数用差值）：导入一批含重复题，此后**不点任何按钮**，批次列表内 ≤15 秒批次卡片自动亮起含「疑似重复」字样的红字，且无自动弹窗出现。
8. 真机探针（同场景续）：打开【剔除重复】弹窗，默认勾选集条数与初查显形条数同源一致（界面显形与 dry-run 清单同一把引擎，不许两套口径并存）。
9. 降级判据（界面不可达则记「仅单测」并写明）：主库不可用场景下批次卡片显示「初查未完成」字样，任何路径不显示「没有重复」。
10. 真机性能：导入 50 题一批（主库 ~456 题），`save_draft` 往返 < 2s；与未挂初查基线做差值断言，不写死绝对数。

### ⑦ 风险 / 回滚 / 与既有裁决的冲突点

- R1 回投挂点（最大不确定）：editor「导入→批次列表刷新」既有机制本轮未验证（ingest 占位题机制证明底座两段式在跑，插件侧刷新入口待现场取证）。若既有机制是「回到批次页才刷新」，判据 7 落在「批次列表在场即自动亮」；主公若要求「导入完当场瞬间在亮」即回到开放问题 1。
- R2 缓存易失：重启丢初查显形。接受——它是显形增强不是判定事实，终局裁决仍在 approve。
- R3 扫描风暴：连续多批导入 × 每批一次全表读。缓解：每批仅一次快照 O(批+主库)、触发频率=人手动作；实测偏贵再加同批末边沿单飞，不预造。
- R4 与剔除/审批竞态：初查快照与老师操作交错，红字可能滞后一轮刷新——展示层最终一致，写路径不动；`main_snapshot_at`（引擎出参 :440-441 已备）可溯源。
- R5 冲突自查：不动画布占位裁决（只在批次卡片加文案）；全链路本机零出网；不碰 `data/`、`LICENSE`、铁律一/二；过程稿不做双写（§9.7），对外证据仍走 §7.1 回传单。
- 回滚：改动全为只增不改 + 一个新测试模块 + 探针一个场景；回滚=revert 三处代码 + 删新文件，**无数据迁移即无回滚成本**（不落库的第四重收益）。版本号回退 2.10.0、三份 plugins.json 重对齐。

### ⑧ 开放问题（需主公拍板，按优先级）

1. **提示可见性强度（先拍这个）**：批次列表卡片红字 + 导入落点底栏 batchNote 一笔，够不够？还是要「导入完成界面当场自动刷新亮出」（需扩改动面去核/补 editor 刷新机制）。推荐：前者——满足「无需人工点按」且对既有刷新动线零侵入；选后者则加 R1 取证与两条判据。
2. **红字 N 的口径**：含「主库已有同题」(bank 组) 吗？推荐：含且文案拆开（「批内重复 N 题、主库已有 M 题」），与 3.5 弹窗两栏同源，老师不用点进去就知道该不该管；只显批内组则改展示取数、引擎不动。
3. **要不要持久化**（推荐不要）：若主公要求「重启后批次列表仍见上次初查结论」，才加表——走 `add-data-store` 的 4+1 动线（pending_db `user_version` 6→7、逐句 execute 迁移、`.pre-v07.bak` 备份优先、回滚=读侧忽略字段、`user_version` 高版本拒绝打开按 R03 §2.2 处理），代价是一份迁移与全套降级用例。主公不点名即按不落库执行。

### ⑨ 落文后记忆对账（同轮追加，2026-11-02，不改上文一字）

- 对账「别动批次元数据、别把简单事做复杂」：本方案的 `dedupe` / `dedupe_queued` 是**响应体派生注解 + 进程内缓存**，不写 batches 表、不碰公共元数据、不加配置与环境变量——与主公既有裁决零冲突；若主公仍嫌三态字段重，最小变体是只回 `dedupe.redundant` 一个数 + `status` 两态（pending/done），引擎与判据不变。
- 对账「一轮只问一个问题」：⑧ 名义三条，**本轮实际只抛第 1 条**（提示可见性强度）；第 2、3 条按推荐口径先行生效，主公不否决即照此实施，答完第 1 条下轮再追。
- 对账「拍板即落文」：本 [DESIGN-2] 即唯一台账；后续任何口径变更继续以追加勘误方式进行，既有行不动。

### ⑩ 主会话核对记录（2026-11-02，本节后补）

- **预算偏离如实记**：architect 本轮实用约 27 次工具调用，超我给定的 22 次硬上限（首次整段写入因命令过大被截断、未落盘，改分块追加多用 5 次）。角色自报了原因并优先保结论落盘，产物完整、`:588` 等既有行零改写，故不判作废、不重派；此偏离计入本轮回传单第 5 项。
- **章节序修正**：`[DESIGN-2]` 原本追加在空占位 `[RELEASE]` 之后，不合 `sync-biz-record` 的 REQ/PLAN/DESIGN/IMPL/VERIFY/RELEASE 序；主会话把 3 行空占位下移到文件末尾（内容逐字不变，仅位置）。
- **本轮未验证项（照角色原文）**：`app/core/ingest.py#_stage_one_batch` 是否经 `save_draft`（决定防双挂）、批次卡片字段构成、editor「解析完成→批次列表刷新」挂点、`approve` :504-541 函数体——四条均标「需实施时现场核对」，不得当成已验。

## [DESIGN-2 勘误] 2026-11-02 (Eval-04 第 1 轮回环修补)

> 本轮只修 Eval-04 点名的 F1（provider 传参链断裂）与 F2（改动表不实），外加 L1/L2 措辞与主公拍板登记。方案骨架不变（A：core 挂点 + daemon 线程 + 进程内缓存 + 批次卡片 `dedupe` 回投）。既有行一字未动，勘误一律以「原口径 → 修正后口径」对照。本轮行号均经 Read/Grep 实读；未读者一律标「未验证」。

### ① F1 修正：provider 获取口径定稿「daemon 线程内 resolve」

**断裂实证（本轮实读）**：两条 `save_draft` 调用点都在 core —— `app/core/ingest.py:683`（`_stage_one_batch` 建占位题，函数头 :676）与 `app/core/ingest.py:729`（`run_ingest_jobs` 真题替换，函数头 :700）；而 `app/api/ingest.py:54` 只有 `background.add_task(ingest.run_ingest_jobs, group["batch_id"], group["jobs"])`（函数体 :30-58 本轮通读），既不 resolve 也不传参。故 [DESIGN-2] ③.1「路由层 `provider.resolve()` 后作参数传入、core 不发 resolve」在拖拽动线上无人可满足，与 ②「新增入池入口 0 改动自动覆盖」直接矛盾。

**修正后口径（写死，不留「实施时定」）**：
- `pending_bank.save_draft` **签名不加 provider 参数**；commit（`app/core/pending_bank.py:225`）+ `con.close()`（:232）之后起的 daemon 任务体内自行 `from app.core import bank_provider` → `provider.resolve()["plugin_id"]` → 传入 `pending_dedupe.warm_batch_scan(batch_id, provider_id)`。
- 传参链闭合：`resolve()` 定义 `app/core/bank_provider.py:80`，返回体 `plugin_id` 见 :101；消费端 `batch_duplicate_groups(batch_id: str, provider_id: str)`（`app/core/pending_dedupe.py:433`）→ `bank_rows_snapshot(provider_id)`（:314）→ `bank.connect(provider_id)`（:322）。入参就是 provider id 字符串，与 `resolve()` 出参同型。

**R03 / R02 合规论证**：R03 §1 的 L0 原文（`.qoder/rules/R03-layer-data-config.md:26`）只禁三件事——「路由层不写 SQL、core 不发 HTTP、插件不越 relay」。`bank_provider` 与 `pending_bank` / `pending_dedupe` 同在 `app/core/`，core→core 同层调用是既有常态（`app/core/ingest.py:678` `from app.core import pending_bank`；`app/core/pending_batches.py:65` 函数内延迟 import `meta_dict`）；`resolve()` 只读本机状态文件（`app/core/bank_provider.py:61-73` `configured_id()`）与已装插件清单（:82 `_installed()`），零出网、零写库，不触 R03 §3.5 白名单以外的路径。函数内延迟 import 与 `pending_batches.py:65` 同款，顺带规避 core 层循环依赖。

**为什么否掉「参数透传」**：透传要同时改三处（`app/api/pending.py:114-120` 传、`app/core/ingest.py:683`/`:729` 传），而 `:729` 已在 background 任务里、拿不到路由层任何上下文，只能把 provider 再塞进 job 字典或给 `run_ingest_jobs` 加参数——为一次展示型初查给底座私有流转结构扩容，正是主公「别把简单事做复杂」的反面。

**⑤ 表修正汇总（覆盖 [DESIGN-2] ⑤ 对应行）**：

| 文件 | 原口径 | 修正后 |
|---|---|---|
| `app/core/pending_bank.py#save_draft` | 挂任务 + 返回体加 `dedupe_queued` + 签名加 provider 参数 | 挂任务（占位轮跳过，见 ①b）+ 返回体加 `dedupe_queued`；**签名零改动** |
| `app/api/pending.py#pending_save_draft` | resolve 活跃 provider 传入 | **零改动**（:114-120 现调形态即最终形态） |
| `app/api/ingest.py` / `app/core/ingest.py` | 「核实是否经 save_draft，是则自动覆盖」 | **零改动**。真实理由：两处入池点（`core/ingest.py:683`、`:729`）本轮已证实都经 `pending_bank.save_draft`，core 挂点天然覆盖；红线是**不得再在 ingest 侧各挂一次钩子**（双挂） |
| `app/api/pending.py#pending_batches` | 卡片附 `dedupe`，构造点实施时定 | **零改动**，字段改在 `batch_card()` 产出（见 ②） |
| `app/core/pending_batches.py` | （原表无此行） | 新增一行：`batch_card()` :67-79 返回体加 `"dedupe": pending_dedupe.scan_state(...)` |

### ①b F1 附带：拖拽两段式——占位轮不扫，识别依据已实读

- 占位轮事实：`app/core/ingest.py:683-688` 传 `_placeholder(...)` + `source_backup` + `source_name` + `origin="ingest"`，**不传 `batch_id`**（即本次调用新建批次，见 `pending_bank.py:153-167` 分支）；替换轮 `app/core/ingest.py:729` 传 `batch_id=batch_id, origin="ingest"`，且首条 item 带 `pending_id`（job 由 :692-696 携带，:721 组装）。
- **`origin` 不能用来区分两轮**（两轮都是 `"ingest"`）——[DESIGN-2] 里若隐含「按 origin 识别占位题」的想当然，本轮明确作废。可用口径只有一条：`origin == "ingest"` **且** 本次调用未传 `batch_id` ⇒ 判为占位轮，跳过初查。
- 占位题本体（作背景，不作判据依据）：`_placeholder` 定义 `app/core/ingest.py:525-532`，返回 `{"type": "solution", "stem": label, "difficulty": DEFAULT_DIFFICULTY, "tags": ["待识别"]}`。
- 不误伤 editor 的取证：editor 首屏 seed 的 origin 是 `"editor.recognize"`（`plugins/org.jiuzhang.editor/dist/ui_batches.js:413-416`），单题暂存 `stashOne` 的 payload 不带 origin（:494-502），两者都不满足「origin=="ingest" 且无 batch_id」，照扫不误 → 判据 1 仍然成立。
- 解析失败的兜底占位题（`app/core/ingest.py:724-727`）带 `batch_id`，会被扫一次；其题干是明写的「（待识别：…）」，与主库指纹相撞概率极低，扫出的 `scanned/redundant` 也如实反映池内此刻内容，故**不加特判**（按 `tags` 语义在 core 钩子里做判断属预造机制）。
- 红字不闪 0 的机理：占位轮不挂任务 ⇒ `_scan_cache` 里没有该批次条目 ⇒ 卡片按「无缓存 = `{status:"pending"}`」渲染（[DESIGN-2] ③.5），不会出现 `done + redundant==0` 的「没有重复」假象；初查只在替换轮扫完后一次性显形。

### ② F2 修正：批次卡片 `dedupe` 合并点点名写死

**存量事实（本轮实读，不再「实施时现场核对」）**：卡片字段唯一构造点 = `app/core/pending_batches.py:63 def batch_card(row, live)`，返回体 :67-79，既有 11 键 `batch_id / label / created_at / updated_at / source_backup / source_name / meta / approved_count / total / pending_count / done`；列表装配点 = `:82 def batch_list()`（:90 `SELECT * FROM batches`、:91-93 现算 live 数、:96 逐行调 `batch_card`、:97-98 排序、:99 回 `{"batches": cards}`）；路由出口 = `app/api/pending.py:26-33`，其中 :33 `return pending_bank.batch_list()` 是纯转口。`batch_card` 的其余调用点：`app/core/pending_bank.py:224`（save_draft 回执 `batch` 字段）、`:371`、`:786`、`:797`（后三处所属函数头本轮未读 → **未验证**）。

**修正后口径**：改 `batch_card()` 产出——:67-79 返回体新增一键 `"dedupe": pending_dedupe.scan_state(str(row["batch_id"]))`（函数内延迟 import）；`batch_list()` 与 `app/api/pending.py` **零改动**。

**选它的三条理由**：
1. 一处改动两处受益：`save_draft` 回执里的 `batch` 卡片（`pending_bank.py:224`）与 `pending.batch_list` 出自同一函数，天然同构，不会出现「列表带 `dedupe`、暂存回执不带」两套口径（正是 F2 想消灭的东西）。
2. 若在 api 层把 `dedupe` 拼进 `batch_list()` 返回值，卡片字段就拆成两处构造点，违反「字段唯一构造点」的存量口径，也让 `save_draft` 回执那条永远缺字段。
3. `scan_state(batch_id)` 是进程内 dict + 锁的纯读（[DESIGN-2] ③.1/③.4 定义），不需要 provider、不读库，放在 `batch_card` 里不引入任何新的 IO 跳站；延迟 import 写法在 `pending_batches.py:65` 已是既有先例。

**向后兼容判据落点**：兼容风险只集中在 `batch_card` 的四个调用点，故判据从「只测 `GET /api/pending/batches`」改为**两处同测**（见本节 ⑤ 第 5 条）。

### ③ L1 / L2 建议吸收（只补措辞与落点，不新增方案）

1. **异常不静默**：[DESIGN-2] ③.3 的 `failed` 分支之后补一条日志——`logging.getLogger("uvicorn.error").warning("待审批次初查失败 batch=%s err=%r", batch_id, error)`。依据 R02 §4.1（`.qoder/rules/R02-coding-error.md:36`）：只复用 `uvicorn.error` 这一支 logger，**不自建 logger、不加 FileHandler**；日志内容只带批次号与异常表示，不带密钥、不带题目原文。
2. **判据 8 锚前置条件**：见本节 ⑤ 第 8 条——「引擎同源 + 两次读取之间池内容不变」写成判据的前置条件，前置条件被破坏时记「不适用」而非失败。
3. **`_scan_cache` 批次删除后不清理 = 定为展示层小疵，不判失败**：`batch_list()` 只对现存 `batches` 行产卡片（`app/core/pending_batches.py:90`），批次一旦删除再无渲染路径，残留只值一条 dict 内存；不做「按池内批次数裁剪缓存」的额外机制（无先例、属预造）。若实施期顺手要清，挂点是删批次那条路径末尾调 `pending_dedupe.forget_batch(batch_id)`——该函数所在行本轮只由 grep 命中（`app/core/pending_bank.py:786`/`:797` 附近），**函数头未读，属未验证，不作判据、不进 ⑤ 表**。
4. **editor 刷新挂点由「未验证」改为已取证**：`refreshBatches` 定义 `plugins/org.jiuzhang.editor/dist/ui_batches.js:389`（内部 :390 `hostCall("pending.batch_list", {})` → :392 存 `state.batches` → :393 `renderBatchList()` → :394 `renderBatchBar()`）；调用点四处：`ui_batches.js:477`（`backToList` 回列表即刷）、`ui_batches.js:613`（`onPendingUpdated`）、`dist/ui_intake.js:320`（`basketGo` 解析请求返回后当场刷一次）、`dist/core_protocol.js:161`（首屏）与 :163（seed 后补刷）。批次卡片的红字渲染点因此落在 `renderBatchList()`（:393 的被调方，函数体本轮未读 → 未验证，coder 现场定位）。
5. **[DESIGN-2] ⑦R1 结清**：`ui_intake.js:320` 证明「拖完当场确实刷了一次」，但那一刻替换轮（`app/core/ingest.py:729`）多半还没跑完，卡片只能是 `pending`；总线广播 `onPendingUpdated`（`ui_batches.js:598`）是否覆盖 core 内部（非 HTTP 路由）发起的 `save_draft`——**未验证**。故本方案不承诺「导入完成当场自动亮」，与主公 ⑧.1 拍板一致（见 ④）。

### ④ 主公拍板登记（2026-11-02，拍板即落文；[DESIGN-2] ⑧ 三条开放问题自此关闭，不得再抛回）

- **⑧.1 定稿：「回批次列表就亮」**。批次卡片红字 + 底栏 `batchNote` 一笔即达标；**不扩**「导入完成当场自动刷新亮出」，**不加弹窗**（与 2026-10-31 画布无占位裁决、军令 #23「只点灯不开窗」一致）。⑦R1 随之关闭，不再作为风险项要求补取证。
- **⑧.2 生效**：红字 N **含** bank 组（主库已有同题），文案拆开成「批内重复 N 题、主库已有 M 题」；取数仍出自 `batch_duplicate_groups` 的 `groups`（`app/core/pending_dedupe.py:433`），展示层拆栏、不做第二次读取、不加新引擎。
- **⑧.3 生效**：**不落库**。`dedupe` / `dedupe_queued` 维持「响应体派生注解 + 进程内缓存」，零表零迁移；R2（重启缓存失、回 `pending`）为已接受的代价，终局裁决仍在 `approve` 强校验。
- **长期铁律照旧不变**：功能自足装配、零外部软件依赖；全链路零出网（不新增定时器轮询、不在启动时顺手拉）；不动 `data/`；插件三查（`fetch(` / `parent.document` / `localStorage`）命中必须为 0；三份索引逐字节全等（主仓根 `plugins.json`、`plugins/org.jiuzhang.editor/plugin.json`、`E:/jiuzhang-plugins/plugins.json`）；本轮只点名 editor 2.10.0→2.11.0，不执行版本号写入。

### ⑤ 修正后的受影响判据全文（**以本节为准，覆盖 [DESIGN-2] ⑥ 第 3/5/7/8 条**；第 1/2/4/6/9/10 条不变，仍按原文执行。前文 ② 末行所指标点即本 ⑤ 第 5 条）

3. 单测（两段式重写，覆盖原第 3 条）：
   - 3a 同批次连续两次 `save_draft` 都传 `batch_id` 追加题 → `_scan_cache` 中该批次仍仅一条，`scanned` 等于第二次扫完后的池内行数，且「池行数 − 主库行数」差值恰为入池题数（初查零写字节、幂等无双倍副作用）。
   - 3b 拖拽两段式只产生一次有效初查：经 `ingest.stage_ingest`（`app/core/ingest.py:608`）落一批含 1 道「与主库指纹全等」的题，`stage_ingest` 返回后立即读 `scan_state(batch)` 必须是 `pending`（占位轮不挂任务，`app/core/ingest.py:683` 被跳过）；等 `run_ingest_jobs` 跑完（`app/core/ingest.py:729` 挂载点生效）后 `scan_state(batch)` 为 `done` 且 `redundant >= 1`；**全程观测序列只允许 `pending → done`，不得出现 `done 且 redundant == 0` 的中间态**（即红字不因占位轮次闪 0）。
4. （沿用原文，不重述。）
5. 单测（向后兼容，按 F2 精确化）：对 `GET /api/pending/batches`（`app/api/pending.py:33`）与 `save_draft` 回执的 `batch` 卡片（`app/core/pending_bank.py:224`）**两处同时**断言：既有 11 键（`batch_id/label/created_at/updated_at/source_backup/source_name/meta/approved_count/total/pending_count/done`，见 `app/core/pending_batches.py:67-79`）零缺失、零改名、零换型，且新增键 `dedupe` 为 dict；无缓存时 `dedupe.status == "pending"`。
7. 真机探针（挂点写实，覆盖原第 7 条）：editor 动线——`ui_intake.js:320` 那次刷新时批次卡片应为「初查进行中/无红字」；随后老师【返回列表】走 `ui_batches.js:477 backToList()` → `:389 refreshBatches()`（**这是判据 7 的显形挂点**），此后不点任何查重/剔除按钮，≤15 秒内卡片出现含「疑似重复」字样的红字（批内 / 主库两栏拆开，按 ⑧.2），且无任何自动弹窗。**禁止把「导入完成当场自动亮」写进判据**（主公 ⑧.1 已裁）。
8. 真机探针（同场景续，锚前置条件，覆盖原第 8 条）：前置条件两条——(a) 引擎同源：初查与【剔除重复】弹窗都调 `pending_dedupe.batch_duplicate_groups`（`app/core/pending_dedupe.py:433`），无第二条判重路径；(b) 两次读取之间池内容不变：同一进程内、老师未做任何删题/入库/再入池动作、探针不并发触发。满足前置条件时，弹窗默认勾选集条数（`drop_ids`，口径见 :436-438）与卡片红字的批内组条数必须一致；若不等，先复核 (a)(b)——前置条件被破坏 → 记「判据不适用」并写明原因，不算失败；前置条件成立而不等 → 失败（两套口径并存的直接证据）。

### ⑥ 本轮实读新增证据（`文件:行号`；未读者已就地标注）

- `app/core/ingest.py:525-532`（`_placeholder`）、`:608-622`（`stage_ingest` 头）、`:652-673`（逐文件建批）、`:676-697`（`_stage_one_batch`，含 :683 的 save_draft 调用形态与 :692-696 的 job 结构）、`:700-731`（`run_ingest_jobs`，含 :721/:724-727/:729）。
- `app/api/ingest.py:30-58`（:54 仅 `background.add_task(ingest.run_ingest_jobs, ...)`，无 resolve、无传参）。
- `app/core/pending_bank.py:121-255`（`save_draft` 签名与函数体，:153-167 新建批次分支、:191-196 `pending_id` 就地更新、:224 `card = batch_card(...)`、:225 commit、:232 close、:233-255 返回体）；`app/api/pending.py:114-120`（save_draft 入参形态：只传 items/batch_id/source_backup/source_name/origin）、`:26-33`（批次列表路由）。
- `app/core/pending_batches.py:63-79`（`batch_card` 返回体 11 键）、`:82-99`（`batch_list`：:90 SELECT、:91-93 live 现算、:96 调 `batch_card`、:97-98 排序、:99 回 `{"batches": cards}`）。
- `app/core/bank_provider.py:61-73`（`configured_id` 读本机状态文件）、`:76-77`（`eligible`）、`:80-109`（`resolve()` 全貌，:101 `plugin_id`）。
- `app/core/pending_dedupe.py:314-324`（`bank_rows_snapshot(provider_id)` → :322 `bank.connect(provider_id)`，连接异常一条不吞）、`:433-443`（`batch_duplicate_groups(batch_id, provider_id)`，:443 首行即调快照）。
- `.qoder/rules/R03-layer-data-config.md:26`（L0「路由层不写 SQL、core 不发 HTTP、插件不越 relay」）、`:12`（动线原文）；`.qoder/rules/R02-coding-error.md:36`（logger 口径）。
- `plugins/org.jiuzhang.editor/dist/ui_batches.js:389-406`（`refreshBatches`）、`:413-416`（`seedBatch` 的 `origin: "editor.recognize"`）、`:471-479`（`backToList` → :477 刷新）、`:485-503`（`stashOne` payload 无 origin）、`:598-613`（`onPendingUpdated` → :613 刷新）；`dist/ui_intake.js:308-333`（`basketGo` → :320 刷新）；`dist/core_protocol.js:161-163`（首屏刷新与 seed 后补刷）。
- **未验证（照实记，不得当成已验）**：`app/core/pending_bank.py:371` / `:786` / `:797` 三处 `batch_card` 调用点所属函数头；删批次路径函数名与可挂 `forget_batch` 的确切位置；`renderBatchList()` 函数体（红字 DOM 插入点）；`onPendingUpdated` 的总线广播是否覆盖 core 内部发起的 `save_draft`；`approve` 函数体（沿用 [DESIGN-2] ① 的待核引用）。
- 本节位置：插在 [DESIGN-2] ⑩ 之后、[RELEASE] 之前，[RELEASE] 仍是文件最后一节。

## [DESIGN-2 勘误·二] 2026-11-02（工序 05 reviewer 三条设计级 Suggestion：逐条裁定与追认）

> 触发：工序 05 reviewer 输出 Critical 0 / Suggestion 6，其中 S1（pending 文案的承诺）、S2（同批并发后发覆盖）、S6（改动面清单漏登 layout.css）属设计层，需本角色追认。本轮**不重设计、不新增方案、不改任何码**，只对三条逐条裁定并落文；既有行一字未动，[RELEASE] 仍是文件最后一节（其空占位整体下移到本节之后，内容逐字不变，先例见 [DESIGN-2] ⑩「章节序修正」）。本节行号全部本轮实读；未读者就地标「未验证」。预算 14 次工具调用，实用 14 次。

### ① S1 pending 态文案：裁定「采纳，但表述由本角色改判定稿」

- **原口径**：`plugins/org.jiuzhang.editor/dist/ui_batches.js:126` 的 `text = "后台初查进行中，稍后自动更新"`。
- **「承诺」确实兑现不了（实证）**：缓存是模块级进程内 dict（`app/core/pending_dedupe.py:481`），无缓存一律回 `pending`（:532-536），其上方注释自认「底座重启即回 pending，下次入池自然重温」（:476-477）；重扫的唯一入口是 `save_draft` 尾部再起一支 `daemon=True` 线程且不保存句柄（`app/core/pending_bank.py:241-243`）——进程退出即失，没有任何机制保证跑完，也没有兜底定时器（[DESIGN-2] ③.4/④⑧.3 明文「不做启动时自动全量扫描」；`docs/AGENTS.md` §2 出网铁律禁定时器轮询）。「稍后自动更新」把「本会话内大概率会更新」写成了必然承诺，判**必须改**。
- **reviewer 建议文案不采纳**：「尚未初查，存入前仍会强校验」对「已排队未跑完」这一支是反方向的假话，而拖拽动线 `dist/ui_intake.js:320` 那次刷新正好落在这一支（替换轮 `app/core/ingest.py:729` 的 `save_draft` 已起线程、此刻多半没扫完）。pending 态唯一说得出口的只有「结论还没出」这一件事。
- **定稿文案（coder 逐字落地，不加不减不改标点）**：把 `plugins/org.jiuzhang.editor/dist/ui_batches.js` 第 **126** 行的赋值改为
  `text = "初查结果未出，存入前仍会强校验";`
  该行上下一律不动：`loading = true`（:127）、`data-dedupe-status` 属性（:130）、`aria-busy`（:131）全部保留——新文案不再宣称「进行中」，`aria-busy` 只表「本元素内容待更新」，不构成时限承诺（AGENTS.md §6 的 aria-busy 硬要求针对按钮，此处是 span）。done 两栏（:119-122）与 failed（:124）**零改动**。函数头注释 :106「加载态（aria-busy），底座还没扫完」属描述性注释、不是判据，coder 可顺手把「还没扫完」之外的时限意味留给文案本身，注释不作要求。
- **「不作免检承诺」红线仍守住**：`redundant <= 0` 时整行不渲染（`ui_batches.js:118`），终局裁决永远在老师点【存入主库】那次强校验（[DESIGN-2] ③.7）。
- **判据同步追认（覆盖勘误 ⑤ 第 7 条中「初查进行中」四字口径；旧行 920 不动，以本条为准）**：`ui_intake.js:320` 那次刷新时，批次卡片的初查行判据从「文案为初查进行中／无红字」改为——DOM 属性 `data-dedupe-status == "pending"`（**取属性不取文案**，`ui_batches.js:130`），且文案逐字为「初查结果未出，存入前仍会强校验」；「无红字」定义为**不含「疑似重复」字样**，不得按颜色判（failed 与 done 共用 `.ed-batch-dedupe` 的 danger 配色，`dist/layout.css:442-452`，只有 pending 被 :454-458 覆写成灰）。判据 7 的后半段（`ui_batches.js:477 backToList` → `:389 refreshBatches` 显形挂点、≤15 秒出「疑似重复」两栏红字、无任何自动弹窗）不变。
- **顺带裁定 reviewer 的观察（pending 混装两语义，要不要拆两态）：不采纳拆态。** 理由三条：(a) 拆出的两态对老师**行为差为零**——无论「排队未跑完」还是「从未排队」，唯一动作都是照常走 approve 强校验，而 ⑧.1 已裁不加按钮、不弹窗、不加手动重扫入口，多出来的 `queued` 无处可点；(b) 代价不成比例——三态契约（[DESIGN-2] ③.3/:773、③.5/:775、③.6/:776）升四态，勘误 ⑤ 第 5 条「无缓存时 `dedupe.status == "pending"`」的字面断言要重订，core/响应体/client 三侧同步扩容，正是 R05/R03 反对的无先例额外机制；(c) `queued` 需由 `save_draft` 预写缓存，反而新增一个「写了 queued 但线程起不来或进程退出 ⇒ 永停 queued」的悬挂态，比现状更难看。**文案改掉承诺，即已闭合混装语义的实际危害**；重启不回扫本身是 ④⑧.3（第 910 行）已接受的代价 R2，不重开。

### ② S2 同批次并发初查「后发覆盖」：裁定「采纳，加发起世代号」

- **风险实证**：每次 `save_draft` 都无条件新起一支线程，不排队、不合并、不留句柄（`app/core/pending_bank.py:241-243`）；`warm_batch_scan` 两处写缓存都是无条件覆盖——done 支 `app/core/pending_dedupe.py:520-529`、failed 支 :511-517。同批两次读取并发时，**先发起那支可能后完成**，卡片上 `scanned/redundant` 会倒退成旧快照。
- **危害不止「数字难看」（这是采纳的实质理由）**：旧快照 `redundant == 0` 覆盖新快照 `redundant > 0` 时整行干脆不渲染（`ui_batches.js:118`），老师看到的是「卡片上没有任何初查提示」——显形层的实质假阴性。复现不需要罕见条件：editor 逐题暂存 `stashOne`（`ui_batches.js:494-502`，勘误 ①b :881 已证它满足「照扫不误」）每暂存一题就是一次**全池 + 全主库**只读扫描（`pending_dedupe.py:507` → :433 → `bank_rows_snapshot` :314/:322），连点两道互为重复的题即可能撞上。
- **与已放行判据冲突（决定性理由）**：勘误 ⑤ 第 3a 条（第 916 行）要求「同批次连续两次 `save_draft` ⇒ `scanned` 等于第二次扫完后的池内行数」。现实现下这条断言过不过取决于两支线程谁后完成，是偶发红；而 daemon 无线程句柄可 join（`pending_bank.py:242-243`），本项目既有纪律亦不许单测 sleep 等 daemon。工序 06 的 3a/3b 此刻尚未落盘（本轮 grep `warm_batch_scan|scan_state|dedupe_queued` 在 `tests/` 命中 0），本轮追认正好赶在断言写死之前。
- **最小实现口径（交主会话另派 coder；本角色不动码）**：全部改动落在 `app/core/pending_dedupe.py` 一个文件、三个点，`app/core/pending_bank.py` 与插件侧**零改动**。
  1. 紧邻 `_scan_cache`（:481）新增模块级 `_scan_seq = 0`，只在 `_scan_lock` 内读写；写法对齐同文件 :478-479 自引的先例（`app/core/basket.py:23`、`app/core/plugin_state.py:20`）。
  2. `warm_batch_scan`（:497）在 `key` 非空校验之后（:503-505 之后）、`try`（:506）之前取号：函数内 `global _scan_seq`，`with _scan_lock: _scan_seq += 1`，同锁内把值赋给局部 `seq`。取号必须早于 `batch_duplicate_groups`（:507）——世代按「读取发起时刻」排序，这是本条唯一依赖的语义。
  3. 两个写缓存点（failed :511-517、done :520-529）各在 `with _scan_lock:` 之内、写之前加同一道闸门：`old = _scan_cache.get(key)`；若 `old is not None and int(old.get("seq") or 0) > seq` 则**整段不写、直接 return**；否则照旧写入，并在写入的 dict 里多带一个内部键 `"seq": seq`。规则一句话：「只允许世代更大者覆盖」，**与 status 无关**——后发起的读取若连不通主库，如实把 `failed` 盖在旧 `done` 上，比留一张过期绿字诚实。
  4. `scan_state`（:532-536）回投前剥掉内部键：命中缓存时 `out = dict(cached)`、`out.pop("seq", None)`、回 `out`；无缓存仍回 `{"status": "pending"}` **一字不改**。如此批次卡片 `dedupe` 的对外键集与 [DESIGN-2] ③.3/③.5 定稿完全一致（done：status/scanned/redundant/batch_redundant/bank_redundant/main_scanned/at；failed：status/code/retryable/at），世代号不外溢到响应契约，`ui_batches.js` 与勘误 ⑤ 第 5 条的键集断言都不受影响。
- **红线自查**：`seq` 只是进程内 dict 的一个整数键——不落库、零新表零迁移、纯只读引擎照旧一支、零出网、不动 `data/`、不新增错误码与 logger、不改鉴权（R01/R02/R03 与 [DESIGN-2] ④ 非目标区零扩张）。
- **与 [DESIGN-2] ③.4（第 774 行）的关系：不作废，属实现口径精化。** 该条否掉的是「末边沿单飞／合并去抖」那套额外机制，本条补的只是同一份覆盖写里的一行世代比较，不是新机制、不加线程、不加队列。**复验条件**：日后若把初查改成任务队列、或给卡片加了「重扫／取消」类交互、或 `save_draft` 的挂载点改为去抖触发，本 ② 的 seq 规则必须重新裁定。
- **勘误 ⑤ 第 3a 条口径补充（旧行 916 不动，以本条为准）**：断言本体不变，追认其成立前提为「同批两线程写缓存受世代号闸门约束」；单测可据此构造确定性场景——连续两次 `save_draft` 传同一 `batch_id`，无论两支线程以何序完成，最终 `scan_state` 必须等于**第二次**（世代更大）那次读取的结果；`seq` 属内部键，测只能通过行为断言，**禁止**断言里出现 `"seq"` 键名或 `_scan_seq`。

### ③ S6 改动面清单漏登 `layout.css`：裁定「确认属清单漏登，不是越界改动，追认入表」

- **实证两条规则的当前形态**（本轮 Read `plugins/org.jiuzhang.editor/dist/layout.css:441-458`）：`:442-452` `.ed-batch-dedupe` —— `border: 1px solid var(--danger, #d33)`、`background: var(--danger-soft, #fdecec)`、`color: var(--danger, #9b3b2d)`、`font-size: 13px`、`line-height: 1.5`、`flex: 0 1 auto`、`overflow-wrap: anywhere`；`:454-458` `.ed-batch-dedupe[data-dedupe-status="pending"]` —— `border-color: #b9b3a8`、`background: transparent`、`color: #6b6459`。选择器与 `ui_batches.js:129-130` 所建 class 及 `data-dedupe-status` 属性一一对应，:441 的行内注释已写明「带文字，不只靠颜色」。
- **定性**：两条都在 editor 插件自己的 `dist/` 内，是 [DESIGN-2] ③.5「卡片渲染一行文字」的必要配套，未新增能力、未碰底座与契约、未越 relay —— 属 **⑤ 改动面清单（第 793 行起）漏登一行**，非范围外改动。
- **追认口径（只追加，旧行不动）**：勘误 ⑤ 表视为增补一行 —— 文件 `plugins/org.jiuzhang.editor/dist/layout.css`，改点 `:442-452`（`.ed-batch-dedupe` danger 态）与 `:454-458`（`[data-dedupe-status="pending"]` 灰态），纯表现层，插件版本仍按 ④ 记 2.10.0→2.11.0。
- **回答 reviewer 附带疑问（pending 与 failed 视觉有没有区分）：有，且不只靠颜色。** pending 为灰字／灰边／透明底（:454-458 覆写）；failed 与 done 落回默认规则（:442-452）呈红字／红边／浅红底。文字层三态文案各不相同（`ui_batches.js:119-122`、:124、本节 ① 新定稿），满足 AGENTS.md §6「状态不得只靠颜色传达」。
- **给 coder 的连带提醒（防止本节 ① 落地时把区分抹平）**：新文案「初查结果未出，存入前仍会强校验」必须仍是**灰字**，不得为它加 danger 配色或新增属性规则，否则与 failed 态视觉同形，勘误 ⑤ 第 7 条（经本节 ① 修订）的「无红字」判据会被推翻。

### ④ 本轮实读证据与未验证项（照实记）

- 本轮实读定位：`app/core/pending_dedupe.py:476-536`；`app/core/pending_bank.py:222-286`（含 :240-243 挂载点与 :272-286 `_warm_dedupe_scan` 线程体）；`plugins/org.jiuzhang.editor/dist/ui_batches.js:100-144`；`dist/ui_intake.js:306-333`；`dist/layout.css:428-458`；本过程稿 :766-801（[DESIGN-2] ③/④/⑤）与 :840-934（勘误全文）；`tests/` 目录清单 + 关键词 grep。
- **未验证（不得当成已验）**：① `app/api/pending.py` 出口与 `approve` 强校验函数体本轮未重读（沿用 [DESIGN-2] ① 的待核引用；S1/S2 结论不依赖它们，但「终局裁决在 approve」这一前提本身仍未二次取证）；② `app/core/pending_batches.py:63-99` 本轮未重读，沿用勘误 ② 的 :887 取证；③ 插件三查 `fetch(` / `parent.document` / `localStorage` 命中数本轮未重跑 grep（工序 06 正在同一工作树跑，以门禁实际输出为准）；④ `warm_batch_scan` 单次耗时量级与同批并发窗口宽窄未实测——本 ② 的采纳理由只依赖「写缓存无闸门」这一代码事实，不依赖概率估计。
- **裁定去向**：①（文案 1 行）与 ②（世代号 3 点，全在 `pending_dedupe.py`）**均需主会话另派 coder**，本角色未改任何码；③ 无码可改，只是台账追认。三条裁定均不新增方案、不改骨架（仍是「core 挂点 + daemon 线程 + 进程内缓存 + 批次卡片 `dedupe` 回投」）。
- 本节位置：插在 [DESIGN-2 勘误] ⑥ 之后、[RELEASE] 之前，[RELEASE] 仍是文件最后一节。

## [RELEASE] 2026-11-02

<!-- 待 architect/coder/test 交付后由 recorder 汇编 -->


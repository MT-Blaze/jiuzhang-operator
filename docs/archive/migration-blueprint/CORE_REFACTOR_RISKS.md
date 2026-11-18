# app/core 改造风险清单

- 编制日期：2026-11-18
- 依据：当前工作树（`main` @ `478b3ac`，含在途改动）+ `docs/AGENTS.md` §4 目标树（`CORE_TARGET_TREE.md`）。
- 口径：只做静态证据与文件核对，**没有执行任何迁移**；凡未实跑的都标「未验证」。

## 0. 风险总表（先看这个）

| # | 风险 | 等级 | 触发条件 | 后果 |
|---:|---|---|---|---|
| 1 | 把函数内导入「顺手」提到文件顶部 | **高** | 迁移时清理 import | 三个 SCC 变成顶层环，启动/导入直接 `ImportError` 或半初始化模块 |
| 2 | 测试里的打桩/日志字符串没跟着改 | **高** | 模块改名后只改生产代码 | `mock.patch` 打空、`assertLogs` 抓不到，测试假绿或直接红 |
| 3 | 500 行冻结台账的路径键失效 | **高** | 移动 12 个超限文件 | `test_file_size_contract` 把新路径当「新超限文件」，门禁红 |
| 4 | 启动链半迁移 | **高** | `app/main.py` 的依赖分两次搬 | 底座起不来，`/healthz` 失败，所有测试连带失败 |
| 5 | `providers/` 动态注册表混入非配置档 | **中高** | 把 `provider.py` 或工具文件放进 `ai/providers/` | 注册表逐个 `import_module` 后调用 `profiles()`，直接 `AttributeError` |
| 6 | 硬编码旧路径的探针 | **中** | 移动 `page_render_regions.py` | `tools/textlayer_probe.py` 取基线源码失败 |
| 7 | 跨流程新增反向导入 | **中** | 迁移时「就近」引用 | 制造新的顶层环（尤其 AI ↔ pending、bank ↔ ingest） |
| 8 | 同名/近义文件混淆 | **低** | 人工或脚本按短名批量替换 | 改错文件、patch 错模块 |
| 9 | 存量异常被误当成迁移问题 | **低** | 迁移后跑测试发现旧红 | 误判回归，浪费时间 |

---

## 1. 导入环：3 个强连通分量，顶层环为 0

### 1.1 结论

- 当前代码共 **3 个 SCC**，全部依靠**函数内导入**闭合；**只算顶层导入时，环数为 0**。
- 这是本次迁移最重要的不变量：**只要所有函数内导入原样保留，目标树仍然可以按任意顺序导入。**
- 迁移只改模块路径，不改导入位置；一旦有人把 `local` 导入提到顶部，环立刻变成真的。

### 1.2 SCC 明细（AST 实测）

**SCC 2：bank ↔ plugins**

| 方向 | 导入位置 |
|---|---|
| `app.core.bank_provider` → `app.core.plugins` | 顶层（`discover_plugins`） |
| `app.core.plugins` → `app.core.bank_provider` | 函数内（`plugins.py:593`，`DEFAULT_PROVIDER_ID` / `LEGACY_PROVIDER_IDS`） |

目标树：`bank/provider.py` → `plugins/registry.py` 仍是顶层；`plugins/registry.py` → `bank/provider.py` 必须仍是函数内。**这是唯一跨流程的 SCC**，目标树没有把它收进单条流程。

**SCC 11：中转站主体**

成员（11）：`meta_dict`、`pending_assets`、`pending_batches`、`pending_compare`、`pending_db`、`pending_dedupe`、`pending_groups`、`pending_meta`、`pending_pool`、`pool_meta`、`pool_source`。

关键闭环边（只列形成 SCC 的）：

| 方向 | 位置 |
|---|---|
| `meta_dict` → `pending_db` | 顶层 |
| `pending_assets` → `pending_db` | 顶层 |
| `pending_batches` → `meta_dict` | 函数内 |
| `pending_batches` → `pending_dedupe` | 函数内 |
| `pending_db` → `pending_meta` | 函数内 |
| `pending_dedupe` → `pending_batches` | 顶层 |
| `pending_dedupe` → `pending_pool` | 函数内 |
| `pending_meta` → `meta_dict` | 函数内 |
| `pool_source` → `pending_pool` | 函数内 |

目标树把这 11 个模块全部收进 `pending/`（`db`、`assets`、`batch/`、`dedupe/`、`pool/`、`meta/`），所以**环被限制在一条流程内部**，不会污染其他流程。但这也意味着：`pending/` 的子目录不能按「独立包」来理解，它们是同一个 SCC 的不同切片；拆包/拆仓前必须先解环。

**SCC 7：进站 + 识别**

成员（7）：`ingest`、`ingest_route`、`recognize.recognize_ai`、`recognize.recognize_local`、`recognize.recognize_mineru`、`recognize.recognize_router`、`recognize.recognize_shared`。

关键闭环边：

| 方向 | 位置 |
|---|---|
| `ingest` → `ingest_route` / `recognize_router` | 顶层 |
| `ingest_route` → `recognize_local` / `recognize_router` | 顶层 |
| `recognize_local` → `ingest` | 函数内 |
| `recognize_mineru` → `ingest` | 函数内 |
| `recognize_shared` → `ingest` | 函数内 |
| `recognize_router` → 三个识别实现 + `shared` | 顶层 |

目标树把这 7 个模块全部收进 `ingest/`（`service.py`、`route.py`、`recognize/`），环同样被限制在一条流程内。**注意：`ingest/recognize/local.py`、`mineru.py`、`shared.py` 对 `ingest/service.py` 的导入必须留在函数内。**

### 1.3 迁移硬约束

1. **不许把任何函数内导入改成顶层导入**，包括「看起来只是挪个位置」的清理。
2. 目标树的 `__init__.py` 一律只放 docstring，**不做 re-export**。一旦 `app/core/pending/__init__.py` 里 `from .service import *`，就会在包初始化阶段提前触发 SCC，环立刻变真。
3. 新增模块不得为了「少写一行」直接导入父包 `__init__`；一律导入具体模块。
4. 迁移后重新跑一次 AST SCC 检查，验收标准：**SCC 数量仍为 3，成员按目标路径一一对应，顶层环仍为 0**。

---

## 2. 动态导入与扫描点

### 2.1 `app/core/providers/__init__.py`（最高优先级）

现状：用 `pkgutil.iter_modules(__path__)` 扫描同目录，对每个模块 `importlib.import_module(f"{__name__}.{name}")`，然后调用 `profiles()` 收集配置档。

目标：`app/core/ai/providers/__init__.py`，逻辑原样搬。

风险：

- `providers/` 目录里**只能**有实现 `profiles()` 的配置档（`builtin.py`、`local.py`）。
- **`provider.py`（抽象接口）绝对不能放进 `ai/providers/`**，否则扫描时会被当成配置档，`profiles` 不存在 → `AttributeError`。目标树把它放在 `ai/platform/provider.py` 就是为了避开这个坑。
- 以后新增 Provider 配置档，必须放在 `ai/providers/` 且实现 `profiles()`；新增抽象/工具，放 `ai/platform/`。
- 注册表用的是 `__name__`，模块路径从 `app.core.providers` 变成 `app.core.ai.providers` 不需要改逻辑；但**测试里若写死了 `app.core.providers` 字符串**（搜索、mock、断言），要一并改。

### 2.2 `app/bank_engine/seeds/books/registry.py`

这是 `app/` 层的动态加载器，不在 core 内。实测 `app/bank_engine/seeds/` 对 `app.core` 的引用为 **0**，所以移动 core 模块不会直接打断 seed 加载。但 `app/bank_engine/{dao_questions.py, entry.py, migrate_v10.py}` 顶层导入 `app.core.exam_name`，`paths.py` 导入 `config`，`service.py` 导入 `toml_io`；移动 `exam_name` 时必须同步改这三处。

### 2.3 `tools/textlayer_probe.py:147`

```python
["git", "show", BASELINE_COMMIT + ":app/core/page_render_regions.py"]
```

这是写死的 git 对象路径。`page_render_regions.py` 迁到 `ingest/render/regions.py` 后，探针取不到基线。迁移时必须改这一行，或者在探针里改成「按目标路径取，失败再按旧路径取」——但后者属于兼容逻辑，本卡不建议，直接改死路径更干净。

### 2.4 文件大小冻结台账

`tests/test_file_size_contract.py` 的 `LEGACY_OVER_CEILING` 用**精确路径**做键，目前 12 条：

```
app/core/pending_dedupe.py      783
app/core/pending_pool.py        773
app/core/plugin_update.py       741
app/core/plugins.py             729
app/core/pending_db.py          676
app/core/pending_bank.py        639
app/core/bank_schema.py         624
app/core/bank_write.py          623
app/core/bank_query.py          593
app/core/dedupe_signature.py    540
app/core/restore.py             532
app/core/latex_style_dict.py    506
```

移动任何一个，旧键失效、新路径变成「未登记的超限文件」，测试直接红。处理原则：

- 移动与台账改名**必须在同一个提交**里完成；
- 本卡只归位、不拆文件；拆文件会让行数变化，另行立项；
- 注意工作树里 `page_furniture.py` 已由基线 201 行变为当前 218 行（在途改动），它不在台账里；迁移时以当次实测为准，不要拿本文行数当冻结依据。

### 2.5 其他动态/字符串耦合

| 位置 | 当前字符串 | 迁移后 |
|---|---|---|
| `tests/test_ingest_triage.py:289` | `assertLogs("app.core.recognize.recognize_mineru", ...)` | logger 名变为 `app.core.ingest.recognize.mineru` |
| `tests/test_pending_dedupe_scan.py:490` | `mock.patch("app.core.bank_provider.resolve", ...)` | `app.core.bank.provider.resolve` |
| `tests/test_restore.py:213` | `mock.patch("app.core.restore._atomic_copy", ...)` | `app.core.backup.restore._atomic_copy` |
| `tests/test_restore.py:336` | 同上 | 同上 |
| `tests/test_workspace_restart.py:172` | `mock.patch("app.core.host_restart.subprocess.Popen")` | `app.core.workspace.startup.host_restart.subprocess.Popen` |
| `tests/test_pending_dedupe_scan.py` 等 | 若还有 `app.core.pending_*` 字符串 | 按目标路径全量 grep 一遍，不能只改已知 5 处 |

> 行号是编制时实测；在途改动可能让行号漂移，迁移时以 grep 结果为准。

---

## 3. 测试与工具的耦合面

### 3.1 数量

| 范围 | 引用 core 的文件数 | 说明 |
|---|---:|---|
| `tests/` | 93 / 111 | 绝大多数测试直接 `from app.core import ...` |
| `tools/` | 44 / 58 | 探针、压测、建包工具 |
| `scripts/` | 2 / 13 | `check_plugin_index_parity.py`、`check_plugin_package.py` |
| `app/`（core 之外） | 24 | `main.py`、`api/*`、`bank_engine/*`、`__init__.py` |

移动一条流程，就要把这条流程的**全部静态引用**一次改完，包括测试、工具、脚本、`app/` 外层；不能只改生产代码。

### 3.2 测试运行口径（不要踩旧坑）

- 必须用 `.venv\Scripts\python.exe`；系统 Python 会把全部模块打成假报错。
- 单模块：`python -m unittest tests.test_xxx`。
- 全量：`python tools\run_all_tests.py`。
- **禁止 pytest**；**禁止 `unittest discover`**（`tests/` 无 `__init__.py`，会 0 用例假通过）。
- `tests/` 目录本身不需要动；迁移只改测试里的导入字符串与 patch 字符串。

### 3.3 会同时被多条流程影响的测试

例如 `tests/test_ingest_scan.py` 同时引用 `ingest` 与 `pending`，`tests/test_pending_api.py` 同时引用 `pending_bank`、`pending_db`、`pending_dedupe`。按流程迁移时，这些测试会被多次触碰；每次都只改本次流程相关的那几行，避免顺手重排。

### 3.4 工作树里的在途改动

当前工作树有他人未提交改动：`app/core/page_furniture.py`、`docs/AGENTS.md`、`tests/test_page_render.py`、`tools/textlayer_probe.py`，以及未跟踪的 `tools/onnx_probe.py`。

- 迁移时不得 stage / revert 这些改动；
- `page_furniture.py` 与 `textlayer_probe.py` 正好都在迁移路径上，动它们之前先确认在途改动的归属；
- `docs/AGENTS.md` 是铁律来源，不得改。

---

## 4. 插件侧

- 兄弟仓库 `E:/jiuzhang/jiuzhang-plugins` 对 `app.core` 的引用实测为 **0**。
- 插件通过 Host API / 请求族工作，不 import 底座 Python 模块；core 内部文件搬家对插件**不可见**。
- 前提是：**不改 Host API 路由、不改请求 id 规则、不改命令族名、不改插件 zip 结构**。本次目标树只动 core 内部，满足这个前提。
- 迁移时不要顺手改 `app/api/plugins.py` 的对外行为；只改它对 core 模块的导入路径。
- 插件侧的 `fetch(` / `parent.document` / `localStorage` 三项红线与本次迁移无关，但迁移后仍应保持 0 命中。

---

## 5. 启动链

### 5.1 现有链路

```
start.bat
  → .venv python -m uvicorn app.main:app
      → app/__init__.py（导入 app.core.workspace_paths 找 .env）
      → app/main.py
          from app.core import plugin_update, pwa, workspace_bootstrap
          from app.core.config import ...
          from app.core.db import init_db
          from app.core.plugins import discover_plugins
          from app.core.security import local_write_token
```

### 5.2 风险点

`app/main.py` 直接导入的 5 个 core 模块里，**4 个会移动**：

| 现模块 | 目标 |
|---|---|
| `plugin_update` | `plugins/lifecycle/update.py` |
| `pwa` | `workspace/startup/pwa.py` |
| `workspace_bootstrap` | `workspace/lifecycle/bootstrap.py` |
| `plugins` | `plugins/registry.py` |

`config`、`db`、`security` 留原地。

因此：

- **`plugins` 流程与 `workspace` 流程的迁移必须各自保证 `app/main.py` 同步改完**；任何一次提交后都必须能 `start.bat` 起服并通过 `/healthz`。
- 不要用「旧路径留一个 `from new import *` 的兼容壳」过渡。兼容壳会新增文件、掩盖漏改、并在删除时制造第二次改动；本卡建议**按流程原子迁移**：移动 + 改导入 + 改测试字符串 + 改台账，一次提交完成。
- 迁移 `workspace_paths` 是禁止项（它留在原地），所以 `app/__init__.py` 不需要动。
- 切库重启（`host_restart` → `plugin_update._write_batch_script`）在目标树里是 `workspace/startup/host_restart.py` → `plugins/lifecycle/update.py`；迁移 plugins 时先改这条，迁移 workspace 时再改自身路径。

### 5.3 验收

每次迁移提交后至少：

1. `.venv\Scripts\python.exe -m unittest tests.test_<受影响模块>` 全绿；
2. `bash scripts/check-quick-gate.sh` 绿；
3. `start.bat` 起服，`GET /healthz` 正常；
4. 再跑 `tools\run_all_tests.py`。

---

## 6. 命名冲突与语义混淆

| 冲突/近义 | 具体 | 风险 | 处理 |
|---|---|---|---|
| `bank.py` vs `bank/` | 模块变成包 | 包会遮蔽同名模块；不能并存 | 一次提交内把 `bank.py` 改成 `bank/service.py`，同时改所有导入 |
| `plugins.py` vs `plugins/` | 同上 | 同上 | 同上，`plugins.py` → `plugins/registry.py` |
| `backup.py` vs `backup/` | 同上 | 同上 | 同上，`backup.py` → `backup/service.py` |
| `app/core/bank/engine/` vs `app/bank_engine/` | 两个「bank engine」 | 改错文件 | 文档/提交说明写清：前者是 core-bank v0.6.3 七表适配层内部，后者是 `app/` 层 v2 引擎；本次不动后者 |
| `pending/db.py` vs `app/core/db.py` | 两个 `db` | 误导入 | Python 3 默认绝对导入；统一写 `app.core.pending.db`，禁止 `from . import db` 之外的短路径猜测 |
| 多个 `service.py` | `ingest/service.py`、`ingest/render/service.py`、`pending/service.py`、`pending/pool/service.py`、`bank/service.py`、`backup/service.py` | patch/日志字符串打错 | 所有 mock/assertLogs 用全路径；代码审查时按全路径核对 |
| 两个 `text.py` | `ingest/intake/text.py`（源文本取样） vs `ingest/render/text.py`（Word/纯文本出 SVG 页图） | 语义混淆 | 保持现名，用目录区分；注释里写清输入输出 |
| `recognize/ai.py` vs `ai/` 流程 | 识别里的 AI 实现 vs AI 配置流程 | 误以为同一件事 | `ingest/recognize/ai.py` 只负责「视觉模型识别」；`ai/` 负责密钥池/指派/客户端 |
| `provider.py` vs `providers/` | 单数接口 vs 复数配置档 | 动态扫描失败 | 接口放 `ai/platform/provider.py`，配置档才放 `ai/providers/` |
| `plugins/state.py` vs `state_store.py` | 插件主机状态 vs 通用运行时状态 | 误用 | `state.py` 管插件启停/昵称/文件夹树；`state_store.py` 管状态文件读写 |
| `plugins/contract/` vs `contract.py` | 插件契约包 vs 题目契约版本 | 语义混淆 | 目录名保留，文档写清；导入全路径 |

---

## 7. 500 行红线与台账

- 12 个文件在冻结台账里（见 §2.4），全部会移动；移动必须同步改台账键。
- 台账测试通常同时校验两件事：①台账内文件行数不超过登记值；②台账外没有新的超限文件。旧键失效会同时触发两条。
- 本卡**不拆**这些文件。拆文件会改变行数与模块数，属于另一个任务；先归位、再拆分，避免一次改动同时承担两种风险。
- `page_furniture.py` 当前 218 行（在途改动），不在台账；迁移时不要把它登记成超限文件。
- 迁移后若某文件因路径变化被误判，优先修台账键，不要为了过测试去删代码/压行。

---

## 8. 存量异常（只记录，不在本次处理）

| 异常 | 现状 | 对迁移的影响 |
|---|---|---|
| `app/core/recognize/` 无 `__init__.py` | 隐式命名空间包 | 目标 `ingest/recognize/` 建议补普通 `__init__.py`；补后必须跑识别链路单测 |
| `page_render_cross` 只被测试引用 | 入度 1，引用者 `tests/test_page_render.py`，生产无调用 | 目标 `ingest/render/cross.py`；不要因为「没人用」在迁移时顺手删，先确认决策台账 D15 |
| core-bank v0.6.3 与 `app/bank_engine` v2 并存 | 两套引擎 | 目标 `app/core/bank/engine/` 只装 v0.6.3 适配层；不要混入 v2 |
| `providers/builtin.py` / `local.py` 静态入度 0 | 只被动态注册表扫描 | 迁移后仍应为 0 静态导入；不要为了「有人用」而加静态导入 |
| `contract_fields.py` 入度 1 | 只被 `question_contract` 使用 | 底座内保留，不合并、不下沉 |
| `backup_package`、`bank_dashboard`、`bank_review`、`pending_engine`、`pending_groups`、`pool_meta`、`pool_source`、`provider`、`question_images`、`ui_cards` 入度 1 | 都是父模块/单测在用 | 迁移时只改父模块导入，不需大范围搜索 |
| `meta_dict` 依赖 `pending_db` + `ai_client` + `questions` | 业务字典，不是底座 | 目标 `pending/meta/dictionary.py`；不要因为名字像「meta」就留在 core 根 |
| 过渡期双引擎/双入口 | `app/bank_engine` 与 `app/core/bank/engine` | 提交说明必须写清本次只动哪一个 |

---

## 9. 建议迁移顺序（本次不执行）

原则：**按目标依赖的下游优先**，让每一步移动后的模块只依赖已经到位的路径，减少同一行被改两次；每条流程一个提交，测试不绿不提交。

| 批次 | 流程 | 为什么这个顺序 | 同批必须改的外围 |
|---:|---|---|---|
| 1 | `backup/` | 只依赖底座，外部引用少（7 个文件），适合做第一次演练 | `app/api/settings.py`、4 个备份测试 |
| 2 | `content/` | 是 ai/bank/pending/ingest 的共同下游；先搬它，后续流程可以直接指向新路径 | `app/api/agents.py`、bank/pending/ingest/ai 的导入、`tests/test_pinyin.py` 等 |
| 3 | `plugins/` | 只依赖底座；`bank_provider` 依赖它，所以要在 bank 之前 | `app/main.py`、`app/api/plugins.py`、旧 `bank_provider` 的导入、`host_restart` 的 `plugin_update` 导入、插件相关测试/工具 |
| 4 | `bank/` | 依赖 content + plugins；是 pending 的下游 | `app/api/{bank,questions,ingest,pending}.py`、`app/bank_engine/{dao_questions,entry,migrate_v10}.py`、旧 `pending_*` 的导入、bank 测试/工具 |
| 5 | `ai/` | 依赖 content；是 pending 的下游（`meta_dict` → `ai_client`） | `app/api/{ai_center,agents}.py`、`ai_recognize` 相关测试、`providers` 动态扫描验证 |
| 6 | `pending/` | 依赖 bank + ai + content；SCC 11 在这一步整体搬入 | `app/api/{ingest,pending,meta}.py`、pending 全量测试、`meta_dict` 的 `ai_client/pending_db` 导入 |
| 7 | `ingest/` | 依赖 pending + content；SCC 7 在这一步整体搬入 | `app/api/ingest.py`、`ingest_route` / `recognize` 测试、`tools/textlayer_probe.py:147`、`page_furniture` 在途改动 |
| 8 | `workspace/` | 依赖 bank + plugins；`app/main.py` 最后收口 | `app/main.py`、`app/api/{workspaces,health}.py`、`workspace_bootstrap`/`host_restart` 测试 |

补充：

- `plugins` 与 `bank` 之间的局部导入在批次 3、4 各改一次：批次 3 改「旧 `bank_provider` 指向新 `plugins.registry`」，批次 4 改「新 `bank/provider` 指向新 `plugins.registry`」。两次都必须保留 `plugins.registry` 内部对 `bank/provider` 的**函数内**导入。
- `workspace` 放最后，是因为它同时依赖 bank 与 plugins，且 `app/main.py` 的启动链要在最后一次提交里完整收口。
- 每个批次完成后：单模块测试 → 快门禁 → `start.bat` + `/healthz` → 全量回归；任何一项红都不进入下一批。
- 不建议「一次性全搬再修」：出问题时无法判断是环、是路径、还是台账；分批能把故障面压到一条流程。

---

## 10. 未验证与偏离（如实声明）

1. **未执行迁移**：本文所有路径结论来自 AST 静态分析、grep 与文件读取；没有实际移动文件后跑导入/启动/测试。
2. **未在浏览器验证**：本次是后端目录规划，无前端改动；不涉及 UI。
3. **三处「字面够格但判平铺」**：`bank/engine/`（2/2/3/3）、`pending/batch/`（2/2）、`plugins/lifecycle/`（2/2）。本卡以「同一事务/同一条生命周期、无并行实现」为由判平铺；若复审要求严格字面执行，只改这三处，不影响其他流程。
4. **`ingest/recognize/` 补 `__init__.py`**：这是迁移动作，未实跑；补后必须验证 `pkgutil`/相对导入/识别单测。
5. **`page_furniture.py` 218 行**：来自当前工作树，含他人在途改动；冻结/拆分口径以迁移当次实测为准。
6. **行号可能漂移**：§2.5 的测试行号是编制时实测，迁移时以 grep 为准。
7. **插件仓库引用 0**：基于当前 `E:/jiuzhang/jiuzhang-plugins` 的 grep 结果；若插件仓库有未拉取分支，需在迁移前重查。
8. **未处理存量异常**：`page_render_cross` 只被测试引用、`recognize/` 无 `__init__.py`、双引擎并存等，均只记录，不在本次归位中清理。

---

## 11. 未来迁移的验收清单（照单打勾）

- [ ] 目标树 107 个业务模块全部有唯一归属，无「公共」目录，无空目录。
- [ ] 底座 10 个模块仍在 `app/core` 根，未改名、未移动。
- [ ] `grep -r "app\.core\.<旧模块名>"` 在 `app/ tests/ tools/ scripts/ examples/` 命中为 0（按批次逐条核）。
- [ ] 5 处已知 patch/assertLogs 字符串已改；全量 grep 无遗漏。
- [ ] `tools/textlayer_probe.py:147` 的 git 路径已改。
- [ ] `tests/test_file_size_contract.py` 的 12 个台账键已同步；台账外无新超限。
- [ ] AST SCC 复核：SCC 数仍为 3，顶层环仍为 0；3 个 SCC 的目标成员与本文一致。
- [ ] `providers/` 目录内只有实现 `profiles()` 的配置档；`provider.py` 不在其中。
- [ ] `start.bat` 起服成功，`/healthz` 正常；`app/main.py` 的 5 个 core 导入全部指向新路径。
- [ ] `.venv\Scripts\python.exe tools\run_all_tests.py` 全绿（不是 `discover`，不是 pytest）。
- [ ] `bash scripts/check-quick-gate.sh` 绿。
- [ ] 插件仓库 `app.core` 引用仍为 0；Host API 路由/请求 id/命令族未变。
- [ ] 提交信息写清「为什么搬」与批次；未修改 `LICENSE`、`docs/AGENTS.md` 铁律、用户 `data/`。
- [ ] 回传单按 `AGENTS.md` §7.1 五项给机械证据，不用「全绿」「已完成」代替数字。

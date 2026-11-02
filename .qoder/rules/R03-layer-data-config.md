---
trigger: model_decision
description: 九章算子分层动线、SQLite 数据访问与配置开关约束。新增表或库、写迁移、改 app/core 存储、动 config.py/.env/令牌或状态文件时必须遵守
---

# R03 分层·数据·配置约束（九章算子）

> 覆盖域：服务分层（域3）+ 数据访问（域4）+ 配置与开关（域5）。结论来自 2026-11-02 实探，证据格式 `路径:行号`。

## 1. 分层动线（L0）

**一句话动线**：插件 iframe → `static/js/stage_inbound.js`(id 校验) → `static/js/stage.js` relay(白名单/限流/权限) → `static/js/stage_relay_*.js`(HTTP) → `app/api/*`(鉴权) → `app/core/*`(Schema 校验) → SQLite。

`bank.create` 逐跳（改动前照抄这条链定位）：

| 跳 | 位置 |
|---|---|
| 1 入口 id 校验 | `static/js/stage_inbound.js:52-65` |
| 2 白名单/限流后分派，bank 族交 `relayBank` | `static/js/stage.js:330-356`、`:259` |
| 3 HTTP 转发 `POST /api/bank/plugins/<id>/questions` | `static/js/stage_relay_bank.js:89-113` |
| 4 路由鉴权 `Depends(require_write_token)` | `app/api/bank.py:290-296` |
| 5 core 写入转口 | `app/core/bank.py:162` → `app/core/bank_write.py:564` |
| 6 **Schema 校验跳** | `bank_write.py:580` → `app/core/questions.py:93`（`Draft202012Validator` 载 `schemas/question.json`，`questions.py:16,87-90`） |
| 7 SQLite 落地 | `bank_write.py:583` `connect(plugin_id)`，库路径 `data/banks/<plugin_id>.db`（`app/core/bank_schema.py:143-148`），`BEGIN IMMEDIATE`/`commit`（`bank_write.py:585-590`） |

- **[L0] 分层不得跳站**：路由层不写 SQL、core 不发 HTTP、插件不越 relay。命令面注册在 `app/core/commands.py:1-27`（只认清单、命名空间闸、先到先得），派发在 `static/js/stage.js:366-372` → `stage_command.js:305 executeCommand`。
- **[L1] bus 层在前端不在后端**：跨插件协作走数据总线（`static/js/bus.js`），以题目标准结构为载荷（`docs/AGENTS.md:26`）。

## 2. 数据访问（L0）

### 2.1 连接三件套同口径

新库必须复刻现有口径 `sqlite3.connect(timeout=10.0)` + `row_factory` + `foreign_keys=ON` + `busy_timeout=5000`：
- 主库 `app/core/db.py:82-89`（结构不合即 close 再抛）
- 题库 `app/core/bank_schema.py:328-340`
- 待审中转站 `app/core/pending_db.py:221-234`

WAL 只在建库/初始化时设且静默回退，`connect()` 不设（`db.py:162-166`、`bank_schema.py:352-355`）；pending 是每次 connect 都设（`pending_db.py:228-232`）——**新库要选边并写明理由**。

### 2.2 迁移三律（版本化 / 备份优先 / 可回滚）

| 律 | 落地位置 |
|---|---|
| 版本化分派 | `db.py:173-176`（`PRAGMA user_version`：主库 2 / 题库 2 / pending 6，`db.py:21,168-178`、`bank_schema.py:57,357-362,521-529`、`pending_db.py:37,243-249`） |
| 备份优先 | `db.py:118-132`（`.pre-v2.bak`，幂等）、`bank_schema.py:532-534`（`.pre-v082.bak`） |
| 可回滚 | `db.py:104-116`、`bank_schema.py:591-594` |
| 不变量自检 | 行数/结构自检 `db.py:149-151`、`bank_schema.py:458-485` |

- **[L0] 禁止 `executescript`**：隐式提交会留下半套库，必须逐句 `execute`（`db.py:92-101`、`bank_schema.py:429-434`）。
- **[L0] user_version 高于程序版本即拒绝打开**（`db.py:168-178`）——降级场景要显式处理，不许静默容忍。

### 2.3 表结构现状（两套并存，别混）

- 主库只有 2 张：18 列旧宽表 `questions` + `question_tombstones`（`db.py:23-67`），读写走 `app/core/questions.py:28-56` + `app/api/questions.py:12,16`。
- 题库是**七表 + 两版本表**，唯一口径在 `app/core/bank_schema.py:71-77`；DDL 真身在 `plugins/org.jiuzhang.bank-engine/bank/schema.sql`（已核实在盘）；建库/自检脚本 `tools/build_bank_schema.py:26-43`。
- v0.6.2 的 `bank_questions` 宽表被守卫拒绝并指向 `tools/migrate_bank_v063.py --promote`（`bank_schema.py:316-321`）。**对外题数口径是 456，不是 457。**

### 2.4 契约校验与 extensions

- **[L0] 唯一校验器**：`app/core/questions.py:86-101`（`Draft202012Validator` + `lru_cache`，失败抛带路径的 `QuestionValidationError`，截 20 条）。调用点：`bank_write.py:441,501,580`、`bank_review.py:129`、`pending_bank.py:327`、`pending_meta.py:238`。
- **[L0] extensions 双向映射坑**：库内是有序数组、契约是反向域名对象，转换在 `app/core/bank_codec.py:34-46`（写）/`:49-58`（读）；label 与顺序表 `bank_schema.py:96-109`；`images`/`tags`/`taxonomy`/`grade` 在库里**寄生于 extensions**、出参还原顶层（写 `bank_write.py:77-115`，读 `bank_codec.py:66-72`，口径说明 `app/core/bank.py:12-19`、`bank_codec.py:1-9`）。查重会把 extensions 拼进指纹（`bank_dedupe.py:100-128`），合并时同名键保留项赢（`:287-298,479-480`）——改这几处任一个都要连带验证查重与并集行为。
- **[L1] 保存期阻断体检白名单**：`bank_schema.py:40-55`。
- **[L1] 新增一类数据读写的先例**（中转站批次，commit `fd049b9`）＝ **4+1 处**：路径 property `app/core/config.py:79-86` → 建表+版本+连接 `app/core/pending_db.py:37,109-165,221-234` → 路由 `app/api/pending.py` → 挂载 `app/main.py:166-167` → 测试 `tests/test_pending_api.py`。次近先例＝数据字典 `6f855a1`（`app/core/meta_dict.py` + `app/api/meta.py`）。少一处即为半成品。

## 3. 配置与开关（L0）

1. **[L0] 路径唯一来源 `app/core/config.py`**（`:55-96` 提供路径常量/property + host/port），禁止依赖 cwd 拼路径（`docs/AGENTS.md:46`）。已知反面样本：`tools/verify_bank_empty.py:8` 写死 `E:\jiuzhang-operator`。
2. **[L1] 没有 feature flag 机制（无先例）**；唯一布尔闸是重启总闸 `app/core/host_restart.py:36-42`（`JZO_RESTART_DISABLED`）。需要开关就明说"要新造机制"，交 architect 评估，别偷偷加环境变量当 flag。
3. **[L1] `.env` 装载用 `os.environ.setdefault`**（进程已有值优先，`app/__init__.py:31-52`，口径同 `docs/STACK.md:42`）；切库后重载 `app/core/workspace_bootstrap.py:143-163`。
4. **密钥与令牌口径**：键名清单见 `.env.example:10-52`（AI 三件 `JZO_AI_{API_KEY,BASE_URL,MODEL}`、可选档 `JZO_{BAILIAN,SILICONFLOW}_*`、`JZO_AI_PROVIDER`、`JZO_LOCAL_TOKEN`、`JZO_DATA_DIR`、`JZO_HOST/PORT`、`JZO_AI_TIMEOUT_SECONDS`）。`JZO_LOCAL_TOKEN` 非空即整套轮换失效（`security.py:55-57,79-86`）；provider 面板写回只写 `{BASE_URL,API_KEY,MODEL}` 并同步 environ 热生效（`app/core/provider_config.py:90-118`、`app/core/providers/__init__.py:24-37,88-96`）。
5. **[L0] `data/` 是用户财产，更新严禁触碰**（`docs/AGENTS.md:30`）。底座允许写进 `data/` 的只有：`data/update_state.json`（`app/api/plugins.py:270,355`）与按工作区落盘的 `data/workspaces/<id>/{plugin_state.json,startup.json,bank_provider.json,update_state.json}`（`app/core/workspace_paths.py:6-16`、`plugin_state.py:26`、`startup_prefs.py:32`、`bank_provider.py:34`、`plugin_update.py:69,399`）；备份白名单同 `backup_files.py:37-71`。可写配置仅 `data/config.json`（`config.py:89-90` + `providers/__init__.py:63-82`）。
6. **[L1] 写状态一律临时文件 + `os.replace` 原子替换**；指针损坏回落 default（`workspace_paths.py:74-83,65-71`、`security.py:38-50`）。
7. **[L0] 文件访问必须校验路径边界**，拒绝 `..`、符号链接逃逸与任意扩展名（`docs/AGENTS.md:62`）。
8. **[L1] 全量环境变量口径**（实测 grep）：底座侧 `JZO_{DATA_DIR,PLUGINS_DIR,ENV_FILE,LOCAL_TOKEN,RESTART_DISABLED,HOST,PORT,AI_PROVIDER,AI_TIMEOUT_SECONDS}` + `JZO_{AI,BAILIAN,SILICONFLOW,OLLAMA}_{API_KEY,BASE_URL,MODEL}`；探针侧 `JZO_STATE_FILE`（`tools/probe_paths.py:26`）、`SECRET`、`PROBE_KEY`、`STAGE`；`JZO_ROOT/JZO_PID/JZO_ALIVE` 只是 bat 内部变量（`host_restart.py:51-56`）。

## 4. 自检清单

- [ ] 新库/新表走 4+1 处先例清单，无半成品挂载点
- [ ] 迁移有版本号 + `.pre-vN.bak` 备份 + 回滚路径，且逐句 execute
- [ ] 未用 `executescript`；未把 `user_version` 高版本当正常态放行
- [ ] extensions 双向映射与寄生字段还原未被破坏（含查重指纹、并集行为）
- [ ] 路径全部来自 `config.py`；写入范围不越 `data/` 白名单
- [ ] 没有新增静默 flag、没有把密钥写进代码/日志/插件上下文

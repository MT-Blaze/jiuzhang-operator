# 减税第一刀：文档减负与口径改正（纯文档，零代码改动）

- 日期: 2026-11-18
- 类型: doc
- 执行者: 派单执行会话（讨论枢纽 4a0d74c0-fab6-4b8b-90c5-7ad497491b81 派单；任务卡 `E:\jiuzhang\减税-第一刀任务卡.md`，证据基础 `E:\jiuzhang\减税-税基侦查报告.md`）
- 等级: L0（改必读链与现行口径，但零代码改动）

## 变更内容

### 0. 背景与中断登记

- 税基：侦查报告账六，典型交付会话强制/惯例必读 ≈3,648 行（根 17 + docs/AGENTS 178 + PLUGIN_SPEC 1,663 + PROJECT_MEMORY 1,539 + R02/R03/R04 ≈216 + 一支 skill ≈35）；PLUGIN_SPEC + PROJECT_MEMORY 占 88%。
- **403 中断与续跑**：执行中途内置模型被账户策略拦截（403 计费拦截），改完 add-host-api SKILL.md 后中断；主公手动切自定义模型后由枢纽续派，本会话续跑完成。另一会话（显性化卡 fc683014）同样 403 中断后续跑，其在途改动全程未碰。
- 基线快照：开工 HEAD `65c16ca830335a3faae6b05d95b899cfb40d8b3f`；在途（永不 stage）：`app/core/ingest/route.py`、`app/core/ingest/service.py`、`app/core/pending/batch/batches.py`、`app/core/pending/service.py`、`plugins.toml`、`static/css/workspace_overlay.css`、`static/js/core_log.js`、`static/js/workspace.js`、`static/js/ws_dock.js`、未跟踪 `tests/test_ingest_failure_surface.py`、`tools/onnx_probe.py`；插件兄弟仓改动与 models/ 遗留目录亦不碰。

### 1. 新建与模板抽出

- **新建 `docs/RECEIPT_TEMPLATE.md`**（62 行）：机械证据回传单模板唯一事实源，自 PROJECT_MEMORY §5.6（含 §5.3 回执抬头）抽出。逐字搬移，仅三处口径改正：两处 `probe.json`→`probe.toml`（代码 `tools/clean_for_release.py` `probe_verdict`:75-78 读 toml）；一处禁改区 `schemas/`→`app/core/question_contract.py` 契约（与 AGENTS:106 改正同源，**申报偏离**：卡说只改 probe 两处）。
- **PROJECT_MEMORY §5.6 整节替换为 3 行存根**（保留编号，指 RECEIPT_TEMPLATE.md 唯一事实源）；全仓模板引用改指：`docs/AGENTS.md` §7.1、`.qoder/rules/R04-test-workflow.md` §4.5（grep 确认真正引用仅此两处；build-release:21/:33 实为 §一大扫除与进度更新引用，**保留不改，申报偏离**）。

### 2. 必读链减负

- **docs/AGENTS.md §8.1**：开工必读改「本文件 + PLUGIN_SPEC §1 红线；其余章节按改动面查顶部章节导航按需读；契约以 question_contract.py dataclass 为准」。
- **docs/PLUGIN_SPEC.md**：标题后插「章节导航」表（14 行章节 + 实测行号 + 适用会话），**21 行插入、0 删除**（git diff --numstat 21/0），契约本体一字未动。
- **PROJECT_MEMORY 退出每会话必读**（历史与 ADR 按需查）。
- 必读量实测（同侦查 :344 口径）：17（根）+177（docs/AGENTS）+202（PLUGIN_SPEC §1，24–225 行）+62（RECEIPT_TEMPLATE）+216（R02 63+R03 83+R04 70）+36（add-plugin）= **710 行**，落卡预期 750±100，减税 ≈80.5%。

### 3. 口径改正（每处附当次代码侧证据）

**docs/PROJECT_MEMORY.md（5 处）**：:32 铁律4 契约→dataclass+CONTRACT_VERSION 2.1（`app/core/contract.py:12`）；:41 update_state.json→.toml；:970 ADR-008 内 discover「会直接报错」→「零用例绿色假通过」（保留历史框架，只改口径子句，**申报**：该处在 ADR 历史节，卡明令改）；:1474-1476 discover 推荐段→逐模块 unittest + run_all_tests + 禁 pytest/discover。不动：:589/:793 ADR 历史、:1330 悬置 TODO、:901/:1225 别照抄补丁、:1535 历史 probe.json。

**docs/AGENTS.md（6 处）**：:102 模板引用→RECEIPT_TEMPLATE.md；:106 禁改区 schemas/→question_contract.py 契约；:90-91 删失效补丁（STACK:91 已改正）；:122 §8.1 必读口径（卡给逐字）；:141 插件仓路径 E:/jiuzhang-plugins→E:/jiuzhang/jiuzhang-plugins；:170⑥ 「STACK §7 第 92 行」→「STACK §7」。铁律一/二逐字未动。

**docs/STACK.md（6 处）**：:7 依赖四项钉版如实写（fastapi/jsonschema/pypdfium2/uvicorn，requirements.txt:5-10）+ jsonschema 零引用待裁决；:13 Python 3.11+→3.10+（requirements.txt:1、AGENTS §4 同口径）；:18/:21 response_model 强制→混合现状（裸 dict 多数 + 4 端点 response_model 先例 questions.py/plugins.py，模型 bank/models.py；R02:12 本就涵盖两者，**不反改 R02，申报**）；:26/:74 question.json→dataclass 校验（question_contract.py validate:444）；§4 标题改「数据契约 · Question dataclass」（全仓 grep 无引「STACK §4」处）；:90 uvicorn→start.bat 唯一官方启动器（AGENTS §9.3）。:19-20/:91 不动。

**.qoder/rules/R01–R04（逐条）**：头部加「2026-11-18 校正」注；搬家后新路径全部 ls/grep 核实（映射：questions→bank/questions.py、bank_write→bank/engine/write.py、bank_schema→bank/engine/schema.py、bank_codec→bank/engine/codec.py、bank_dedupe→bank/engine/dedupe.py、bank_review→bank/engine/review.py、pending_db→pending/db.py、plugins→plugins/registry.py、plugin_update/install/download→plugins/lifecycle/*、commands→plugins/contract/commands.py、host_restart→workspace/startup/host_restart.py、meta_dict→pending/meta/dictionary.py、bank→bank/service.py、workspace_bootstrap→workspace/lifecycle/bootstrap.py、provider_config→ai/platform/center.py、providers→ai/providers/、plugin_state→plugins/state.py、startup_prefs→workspace/startup/startup_prefs.py、bank_provider→bank/provider.py、backup_files→backup/package/files.py）；未当次核实行号一律去掉；文档引文档改章节锚点（PM §六「Windows 批处理三大坑」「切表轮新增的环境坑（2026-10-23）」、AGENTS §2–§9 等）。关键改正：
- 契约校验跳：question_contract.py validate:444 + bank/questions.py:82（QuestionError:60 / ValidationError:72，旧名 QuestionValidationError 已正）；调用点 write/review/pending/service.py:381。
- pending user_version 6→**11**（pending/db.py:51；主库 2 db.py:21、题库 2 bank/engine/schema.py:56）。
- 两份索引「逐字节全等」→「语义一致」：主仓 plugins.toml vs 远端 plugins.json，sync 只改写主仓 toml 不代写远端（AGENTS §9.1 L0 第 4 条；check_plugin_index_parity.py:7 按 dataclass 校验 example）。
- plugin.json→plugin.toml；14 必需键不变（check_plugin_package.py:28 REQUIRED_FIELDS）；bus 为 [bus] 节。
- data/ 白名单 TOML 化（AGENTS §9.1 L0 第 6 条；workspace_paths.py docstring；config.toml config.py:100）；state_store 只读写 TOML（代码明言不再识别同名旧 .json，**卡说「首读即迁」与代码不符，按代码写，申报**）。
- 计数：tests 75→**109 入库**（git ls-files；在途 +1 不计）；探针 25→**32 入库**（ls 33 含他人未跟踪 onnx_probe.py）；写死端口探针 5→**4 支**（console_panel/fold/split/tab_group）、令牌 2 支；audit 基线 ERROR 0/WARN 36/INFO 4→**ERROR 0/WARN 34/INFO 3**（2026-11-18 复跑）。
- probe.json 三种历史 schema 段→probe.toml 统一（probe_verdict:75-78，不认判不通过）；R04:48 模板引用→RECEIPT_TEMPLATE.md；R04:51 禁改区 schemas→契约+CONTRACT_VERSION。
- R04 §1.6「22 个起 uvicorn 模块」清单与实测 grep（19 文件）有漂移——**计数不动只登记**（见 §5）。

**6 支 skills**：add-plugin（description+步骤 plugin.toml 化、14 键以 REQUIRED_FIELDS 为证、registry.py:452 禁 backend、兄弟仓 src 路径、sync 语义一致不代写）；add-host-api（契约校验跳、bank/questions.py 异常、security.py:69、install.py 新路径、[contributes] commands）；add-data-store（pending/db.py 三段、dataclass 契约+CONTRACT_VERSION、parity 按 dataclass 校验 example、DDL 兄弟仓 src 路径）；build-release（plugin.toml、update.py、gc:166、sync 语义一致、AGENTS §7；:21/:33 保留申报）；run-regression（:20 过期工作树快照句→通用在途纪律、probe.toml、:37 不认 schema 判不通过）；sync-sys-record（description 与步骤3：原 .qoder/AGENTS.md 资产索引不存在、docs/AGENTS.md 无索引节，改「在本 sys 记录内登记变更清单」，自检同步改）。

**识别线**：台账 :5 日期→2026-11-18、:22 提交号→搬家收口（批7 641bbc8 / 批8 d6a2893+65c16ca，此后以 git log 为准）、:24 依赖→onnxruntime 1.32.0 已装 .venv 与 engines/rapidocr/ 双处（后者另有 rapidocr 3.10.0）、无 torch/paddle、:25 产物→app/core/ingest/intake/（text.py extract_docx_document:163）；D6 状态「尚未记入」→「已回写」；T3 标完成；§八追加变更记录。**D6 回写 pipeline**：第 17 条（:43）按 D6/D7/D8 重写（先切题再逐题送模型、整页压缩 1024 宽公式糊、本地 OCR+题号链、0/1/≥2 判据），§10.1⑤ 头部加覆盖注记、原文保留作历史（**申报**：卡只说改第 17 条，⑤ 注记为配套最小动作）。**README:23**：「公开的 JSON Schema」→「公开的 dataclass 契约（app/core/question_contract.py）」（对齐 AGENTS §3）。

### 4. 申报偏离汇总（与卡不符处，均按铁律停下报告口径处理）

1. **editor-v2-progress 不改**：卡 §3.9 指 `docs/editor-v2-progress:4`，实体不存在于 docs/，真身 `.qoder/records/biz/2026-10/20261031_editor-v2-progress.md`:3-4 归档注记（引 plugin.json 与旧路径）。biz 记录 append-only（卡 §3.10 自身重申、sync-biz-record 明禁编辑历史章节）→ 内部冲突，**不改**，在此登记。
2. **sys 记录路径守 R00**：卡给 `.qoder/records/sys/20261118_tax-cut-first-blade.md` 不合 R00（须 {YYYY-MM}/{YYYYMMDD}_{类型}_{主题}.md）→ 用本路径，类型 doc。
3. build-release:21/:33 非模板引用，保留（grep 证实）。
4. RECEIPT_TEMPLATE 第三处改正（schemas→契约）超出卡「只改 probe 两处」，与 AGENTS:106 同源，做了并申报。
5. state_store「首读即迁」与代码不符，按代码写「只读写 TOML」。
6. response_model 并非零使用（4 端点），R02:12 本就准确，改 STACK 对齐而非反改 R02。
7. PM:970 在 ADR 历史节，卡明令改→只改口径子句保留历史框架。
8. pipeline §10.1⑤ 覆盖注记为第 17 条回写的配套最小动作，原文零删。

### 5. 不动项与新税登记（只登记，不扩面）

- ** requirements 裁决项**：jsonschema 移除、playwright 补入，均待主公拍板，只登记不动 requirements.txt。
- **死重 ~2,450 行属第二刀**：不归档不删除任何文件。
- AGENTS §9.3⑦「5 支探针」漂移（实 4）——在 AGENTS 现行节但非卡列六处之一，登记。
- AGENTS §3「变更 Schema 必须升 schema_version」句残留 Schema 字样——非卡列处，登记。
- R04 §1.6「22 个起 uvicorn 模块」清单 vs grep 19 文件漂移——计数不动，登记。
- run-regression:16 / R04:58「工序 06」退役术语（六工序 2026-11-05 已退役）——登记。
- PM:1330 悬置 TODO（schemas 与存储层对齐）、PM:1535 历史 probe.json、PM:901/:1225 别照抄补丁——历史/悬置，不动。
- editor-v2 归档注记 plugin.json 与旧路径（见 §4.1）——append-only，不动。
- **pipeline:159/:167 现行口径仍引 schemas/question.json（含旧盘符 file:///E:/jiuzhang-operator 链接）**——卡 §3.8 只列第 17 条与 §10.1⑤，此两处属清单外新发现 stale 指针，**只登记不顺手改**，建议第二刀或识别线会话处理。
- 台账 §五未决问题 1（onnxruntime 能否装 3.14）实测已可装（1.32.0），非卡列三处状态节之一，只在 §八变更记录带一句，正式收口待拍板。
- check-naming.sh 死查、456 题数未当次核实、CORE 三件套漂移——第二刀范围。
- **承接销账**：`.qoder/records/biz/2026-11/20261102_dedupe-batch-purge-latex-preview.md` §7（:719 附近）登记「R04:29 探针 25 支计数过时，改规则需另走 sys 记录」——本记录即该 sys 记录，R04 已改 32 支入库口径，销账。

## 涉及文件

新增：`docs/RECEIPT_TEMPLATE.md`、本记录。
修改（18 份，全 Markdown）：`docs/AGENTS.md`、`docs/PLUGIN_SPEC.md`（仅插导航表）、`docs/PROJECT_MEMORY.md`、`docs/STACK.md`、`docs/question-cutting-pipeline.md`、`docs/识别引擎-决策台账.md`、`README.md`、`.qoder/rules/R01-module-build.md`、`R02-coding-error.md`、`R03-layer-data-config.md`、`R04-test-workflow.md`、`.qoder/skills/domain/add-plugin/SKILL.md`、`add-host-api/SKILL.md`、`add-data-store/SKILL.md`、`build-release/SKILL.md`、`run-regression/SKILL.md`、`.qoder/skills/base/sync-sys-record/SKILL.md`。
零代码改动：app/ static/ tests/ tools/ scripts/ requirements.txt、插件兄弟仓、data/、LICENSE、根 agents.md 均未碰；docs/AGENTS.md 铁律一/二逐字未动；PLUGIN_SPEC 契约本体 0 删除。

## 验证结果

- **旧指针清零 grep（当次）**：rules/skills 内 `plugin.json` 0 命中、`probe.json` 0 命中、旧平铺模块路径 0 命中、「逐字节全等」0 命中、§5.6 模板引用 0 残留；`discover` 残留全部为禁令句（无推荐）；`schemas/question.json` 残留仅 PM 历史/悬置（:590/:794/:1332，豁免）与 pipeline:159/:167（清单外，登记）。
- **必读量**：before ≈3,648（侦查 :344）→ after **710 行**（当次 wc -l，组成见 §2），减税 ≈80.5%。
- **PLUGIN_SPEC 零删改**：git diff --numstat = 21 插入 / 0 删除。
- **快门禁**：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**（体积 WARN 23 份为既有排队项，非门禁失败）。
- **全量回归**：`.venv/Scripts/python.exe tools/run_all_tests.py` → 模块 110 个（109 入库 + 在途未跟踪 test_ingest_failure_surface.py）、用例 2090 个、失败模块 1 个：`test_command_registry`（test_29，editor 版本 2.13.0 ≠ 期望 2.12.2）。**基线 worktree 对照**：`git worktree add --detach E:/jiuzhang/.tax-cut-baseline 65c16ca` 同输入跑同模块 → 同样失败同样断言（2.13.0 ≠ 2.12.2）→ 判**在途/既有问题非本卡回归**（插件仓 editor 已被另一会话 bump 2.13.0，测试期望表未同步）；如实报，不修他人代码。临时 worktree 已清理（git worktree remove + prune + rmdir）。
- **audit 复跑**：ERROR 0 / WARN 34 / INFO 3（R02 基线已同步）。
- **并行安全**：stage 逐个点名本卡 19 份 MD（含本记录），严禁 git add -A；plugins.toml 与全部在途代码文件、tools/onnx_probe.py、tests/test_ingest_failure_surface.py 未 stage；单 commit、中文信息说为什么、不 push 不 amend（hash 见回传单与 git log）。
- **命名偏离**：本记录路径按 R00 纠正（卡给路径不合 R00），见 §4.2。
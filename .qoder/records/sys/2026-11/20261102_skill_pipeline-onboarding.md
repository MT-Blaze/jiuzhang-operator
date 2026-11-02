# sys 记录 · 六工序流水线入驻九章算子

- 类型：skill（体系资产整体入驻，含 rule/agent/skill/script/doc）
- 日期：2026-11-02
- 来源：Qoder 插件 `six-stage-pipeline@qoder-marketplace` 1.0.0（框架层 pipeline-v1.0）
- 执行人：主对话（编排）+ 4 路 Explore 子代理（八领域实探）
- 状态：已落地并验收（复验见 §10），欠账 5 条见 §7

## 1. 为什么入驻

主公裁决：本项目此后**每个新会话默认按多智能体协作执行**，权限全放开，所需 skill/插件/功能由代理自行安排。原话约束的落地口径见 §3 四项确认。

## 2. 八领域实探结论（全部带证据，详版已固化进 R01~R04）

| 域 | 一句话结论 | 关键证据 |
|---|---|---|
| 1 模块与依赖 | 底座 `app/`（main + 12 api + 60 core）与 7 支插件之间零代码依赖，依赖只有三项钉版 | `app/core/plugins.py:571,579`、`requirements.txt:6-8` |
| 2 编码与错误处理 | 统一返回体在宿主 postMessage 层而非 HTTP 层；后端无 ErrorCode 表、无全局 handler | `static/js/stage_command.js:443-468`、`app/api/bank.py:310-320` |
| 3 服务分层 | 七跳动线：插件 iframe→stage_inbound→stage relay→stage_relay_bank→api→core 校验→SQLite | `stage_relay_bank.js:89-113`、`app/core/bank_write.py:580` |
| 4 数据访问 | 三处建连同口径 + 迁移三律；主库旧宽表与题库七表并存 | `app/core/db.py:82-89,118-132`、`app/core/bank_schema.py:71-77` |
| 5 配置与开关 | `config.py` 唯一路径源，无 feature flag 机制；写盘白名单极窄 | `app/core/config.py:55-96`、`app/core/workspace_paths.py:6-16` |
| 6 测试 | 75 个 unittest 模块、无 `__init__.py`、22 个真起 uvicorn；25 支探针无统一 runner | `tools/run_all_tests.py:38`、`tools/clean_for_release.py:69-98` |
| 7 构建与发布 | 版本单源 `app/__init__.py:8`；打包只读校验弱，红线靠装载侧 | `tests/test_version_consistency.py:64-81`、`app/core/plugins.py:396,420,421` |
| 8 流程与文档 | 无 CI；`.qoder/` 未被 ignore；工作树有他人在途改动 | `git status --short`（26 项）、`.gitignore`（原无 .qoder 条目） |

## 3. 主公四项裁决（阶段二）

1. **触发范围**：分级触发——全链 / coder+reviewer+快门禁 / 纯查询不起子代理。
2. **账本归属**：机械证据回传单是唯一对外交付证据，`records/biz` 只作工序内过程稿，不双写。
3. **门禁档位**：快门禁每阶段跑（秒级），全量单测 + 探针只在工序 06 与发版前跑。
4. **铁律文件动法**：`docs/AGENTS.md` 新增 §9，并修正 §7 的 discover 口径；铁律一/二逐字未动，根 `AGENTS.md` 只加会话入口块。

## 4. 本次落地资产

- **框架层原样拷入**：`.qoder/agents/`（6）、`.qoder/rules/R00,R05`、`.qoder/skills/process/`（feature-dev、init-pipeline）、`.qoder/skills/base/`（sync-biz-record、sync-sys-record、archive-tech-report）、`scripts/check-naming.sh`、`.qoder/templates/`、`records/{biz,sys,reports}` 骨架。
- **角色卡升级**：6 张卡各补 Qoder agent frontmatter（name/description/tools/disallowedTools/permissionMode/model/maxTurns/timeoutMins/color，test-agent 额外绑 `mcpServers: ["browser-use"]`）+ 新增「本项目落地（九章算子）」节；architect/reviewer/eval 用 `disallowedTools: [Write, Edit]` 从机制上保证只读，落实"做判分离"。
- **项目层 rules**：`.qoder/rules/R01-module-build.md`、`R02-coding-error.md`、`R03-layer-data-config.md`、`R04-test-workflow.md`（全部逐条带 `路径:行号` 证据）。
- **domain skills（6）**：`add-plugin`、`add-host-api`、`add-data-store`、`run-regression`、`build-release`、`prove-visual-change`。
- **门禁**：`scripts/check-plugin-boundary.sh`、`check-plugin-package.sh`+`.py`、`check-plugin-index-parity.sh`+`.py`、`check-probe-reports.sh`+`.py`、`check-quick-gate.sh`、`check-release-gate.sh`；`tools/sync_agents.py`（角色卡镜像）。
- **索引与配置**：`.qoder/skill-bank.json`；`docs/AGENTS.md` §9（入口/L0 红线/门禁/资产索引/常用命令与环境坑/证据口径）；根 `AGENTS.md` 会话默认工作流块；`.gitignore` 加 `.qoder/repowiki/*`（放行 `wiki_plan.yaml`）。

## 5. 验证证据（当次实跑，非转述）

| 项 | 命令 | 结果 |
|---|---|---|
| 命名门禁 | `bash scripts/check-naming.sh` | `[PASS] check-naming: .qoder 资产命名合规（R00）` rc=0 |
| 三查与依赖方向 | `bash scripts/check-plugin-boundary.sh` | 三查各 0 命中、`plugins/` 内无 .py；[INFO] 宿主侧带 `fetch(` 文件 16 个，rc=0 |
| 插件包结构 | `bash scripts/check-plugin-package.sh` | `PASS（官方插件 7 支，结构红线全部通过）` rc=0 |
| 索引全等 + Schema 自校验 | `bash scripts/check-plugin-index-parity.sh` | `PASS（两份索引全等、条目版本一致、Schema 示例自校验通过）` rc=0 |
| 静态审计 | `.venv/Scripts/python.exe tools/audit_code.py` | `检查完成：ERROR 0 · WARN 36 · INFO 4` rc=0 |
| 版本与 bat 编码 | `.venv/Scripts/python.exe -m unittest tests.test_version_consistency` | `Ran 14 tests in 0.024s / OK` |
| **快门禁总入口** | `bash scripts/check-quick-gate.sh` | `check-quick-gate: PASS（6 项全过）` rc=0 |
| 探针归一 | `bash scripts/check-probe-reports.sh` | `[PASS] editor_probe（dup31e）：205/205 判据通过 @ 2026-11-02 11:07`，`1 支探针最新跑批全部全绿` rc=0 |
| 单测命令可用性 | 4 个纯逻辑模块实跑 | `test_clean_latex` Ran 10 OK、`test_pinyin` Ran 5 OK、`test_backup_codec` Ran 6 OK、`test_version_consistency` Ran 14 OK |
| 假通过取证 | `.venv/Scripts/python.exe -m unittest discover` | `Ran 0 tests in 0.000s / NO TESTS RAN`（文档旧口径"直接报错"已按实跑修正） |

## 6. 关键发现：角色卡生效条件（对照实验）

- `.qoder/skills/**/SKILL.md` 落盘**当次会话即被识别**为可用 skill（11 个 skill 即时进清单，含 6 个新建 domain skill）。
- 子智能体清单**不动态刷新**：项目级 `.qoder/agents/eval-agent.md` 与用户级 `~/.qoder/agents/jiuzhang-pipeline/coder-agent.md` 在当次会话都报 `Unknown agent type`（可用清单仍只有 general-purpose/Explore/Plan + 3 支【示例】）。
- 结论：**角色卡可调用性只能在"新会话"验证**，与目录层级无关。对策三件——① 仓库为唯一事实源；② `tools/sync_agents.py` 镜像到用户级（本机已证明用户级 sample 目录会被扫描）；③ 当次会话兜底用 `general-purpose` + 令其先 Read 角色卡。

## 7. 已知欠账（不藏）

1. **新会话未验证**：六个角色名是否真的进入可调用清单，须主公重开会话后由首次编排实测；若仍不可用，兜底路径已写进根 `AGENTS.md` 与 §9.2。
2. **探针无统一 runner**：`check-probe-reports.sh` 只归一已有报告，探针执行仍靠 test-agent 按改动面手跑（25 支，且需 playwright）。
3. **`playwright` 未进 `requirements.txt`**：与 `STACK.md` §7 第 92 行"锁定版本、禁止隐式安装"冲突，但补入会影响离线首发（chromium 二进制仍需单独安装），属主公裁决项，本次未动。
4. **收尾门禁全量未实跑**：本次只跑快门禁与归一探针；`bash scripts/check-release-gate.sh`（含 75 模块）留待第一个真实需求工序 06。
5. **兜底路径无硬隔离**（§9 详述）：`general-purpose` 兜底子代理不继承角色卡的工具白名单，"只读角色不许写文件"仅靠指令自律；若要机制级隔离，需把"对子代理交付做 diff 复核"写成脚本。

## 8. 偏离说明

- 框架层 `architect-agent.md` 禁区一节保留原句「不修改任何 Java/配置文件」（框架层资产项目内不得私改，README §升级约定），本项目实际是 Python/前端；已用 `disallowedTools: [Write, Edit, NotebookEdit]` 从机制上兜住，并建议上游模板去项目化此句。
## 9. 补充（同日晚些时候的兜底实测）

- 兜底路径已实测可用：`general-purpose` 子代理先 `Read` `.qoder/agents/architect-agent.md` 后，能完整复述该角色的单一职责、skill 白名单、禁区前两条与「本项目落地」5 条 bullet，无截断。
- **由此暴露一个新缺口（已列为 §7 欠账 5）**：兜底路径起的 `general-purpose` **不继承角色卡 frontmatter 的工具白名单**（`tools`/`disallowedTools`/`permissionMode` 只对原生角色生效），所以"architect/reviewer/eval 不许写文件"在兜底时只靠指令自律，不是硬隔离。真全链需求应尽量用原生角色名（新会话），兜底只作过渡；若要硬隔离，需在主会话侧对子代理交付做 diff 复核（reviewer 已能覆盖，但未写成脚本）。
- 本次提交：`52e8352`（44 文件，+2124/−1），未 push（`docs/AGENTS.md:83`）。他人的在途改动（22 项删除态文件、handoff 未跟踪文件）未 stage、未 stash、未恢复。

## 10. 入驻验收补录（同日 12:00 前后，第二次取证）

**注册表侧已认，会话侧未认——两侧状态分开记。**

| 项 | 取证方式 | 结果 |
|---|---|---|
| 六角色是否进 Desktop 注册表 | `mcp__qoder-settings__manage_app_agent list` | 6 条全部在册：`enabled:true`、`definitionStatus:"ready"`、`usageScopes:["main","subagent"]`，各带 agentId 与 definitionRevision；与 3 支【示例】同一清单 |
| 运行时可派发角色 | `mcp__builtin__list_agents` | 6 条 `enabled:true / ready:true`（`model:null` 即继承） |
| 当次会话能否派发 | `Agent(subagent_type="architect-agent")` | 报错原文：`Error: Unknown agent type: 'architect-agent'. Available types: general-purpose, Explore, Plan, 【示例】代码审查员, 【示例】实现规划师, 【示例】研究助手` |
| 快照假说的时间线证据 | 会话首行 timestamp / 两处 agents 目录 mtime | 会话起于 11:28:54；【示例】目录 11:26:49（会话前，故可调用）；`jiuzhang-pipeline` 目录 11:55:09（会话后，故本会话不可调用） |
| 快门禁复跑 | `bash scripts/check-quick-gate.sh` | `check-quick-gate: PASS（6 项全过）`，静态审计 `ERROR 0 · WARN 36 · INFO 4` |

- **纠一条本记录早前的错话**：§6 末原写「实验用的用户级临时副本已删除」——现 `~/.qoder/agents/jiuzhang-pipeline/` 六张卡是 `tools/sync_agents.py` 镜像出的**正式注册表条目**，不是临时副本，后续不得再随手删。
- **新机制结论**：用户级目录放文件即可被注册表收编（本机 `manage_app_agent action=create` 零次调用，注册表已出现六条 ready 条目，故无需走 Settings 表单）；卡住的一直是 Agent 工具的类型清单快照。
- **漂移风险（新增约束）**：注册表条目一旦生成，Settings → Agents 里编辑会改写用户级镜像；因此每次改角色卡必须**先改仓库 `.qoder/agents/` 再跑镜像**，反向不可。`docs/AGENTS.md` §9.2 生效条件一节已按上述证据重写。
- **欠账 1 相应收窄**：不再是"能不能识别"，只剩"新会话里六个名字是否真进清单"，须主公重开会话由首次编排实测；本会话继续按 §9 的 general-purpose 兜底跑。


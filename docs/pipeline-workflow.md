# 六工序多智能体工作流 · 跨产品自足执行手册

> **用途**：把本文件整份喂给**任何一个新 AI 会话**——国际版/国内版 Qoder、Desktop/IDE，或任何带文件读写与命令执行能力的 agent——它就能按九章算子的流水线直接开工。
> **不依赖**：产品专属的 Agent 注册表、slash 命令、rules 自动加载、插件市场。这些有就用（更好），没有就按本文件的降级路走。
> **上位约束**：`docs/AGENTS.md`（铁律一/二、§7.1 回传单、§9 工作流）。本文件是它的**可移植投影**，两者冲突时以 `docs/AGENTS.md` 为准并当场报告冲突。
> 版本：pipeline-v1.0 · 2026-11-02 · 与 `.qoder/`（6 角色卡 + R00~R05 + 11 skills + 6 门禁脚本）同批落地。

---

## 0. 冷启动：新会话按序做这 4 步，不要跳

1. **读铁律**：`docs/AGENTS.md` 全文，重点 §1 铁律一（干净房间）、§2 铁律二（插件化）、§7.1（机械证据回传单）、§9（本节工作流的上位条文）。
2. **取基线**：`bash scripts/check-quick-gate.sh`。当前基线 = `PASS（6 项全过）`，静态审计 `ERROR 0 · WARN 36 · INFO 4`。**跑不绿先如实报告，不许动代码**。
3. **定档**：按 §1 判断这次任务走哪一档，按 §2 选一条派发路，并**把选定的路和理由一句话告知主公**。
4. **收尾**：每阶段跑快门禁 → 补记录（§7）→ `git commit`（中文信息，说明"为什么"）。**不绿不 commit；push 需主公当场授权**。

判档口诀：**纯查询与解释 → 不起子智能体，直接答**；**单点缺陷/文案样式 → 三角色短链**；**新功能/多阶段需求 → 六工序全链**。判错档位即返工。

---

## 1. 触发分级（2026-11-02 主公裁决）

| 档 | 场景 | 走法 | Eval |
|---|---|---|---|
| 全链 | 新功能、跨模块改动、多阶段需求 | `/feature-dev` 六工序：意图→编排→调研→设计→编码→验证 | 01/04/05/06 各挂一道独立 Eval |
| 短链 | 单点缺陷、小改文案与样式 | `coder-agent` → `reviewer-agent` → `eval-agent` + 快门禁 | 只挂 05 |
| 直答 | 查询、解释、读代码 | 主对话自己答，**不起子智能体、不落记录** | 无 |

**主对话（编排位）铁律**：只做调度与四态决策，**禁止自行设计、自行写码、自行评审、产出计划文档或改他人产物**。需求开发的技术内容必须出自 architect/coder/test 之口。

---

## 2. 六个角色与三条派发路

### 2.1 角色契约（一张表说完；详版在 `.qoder/agents/{角色}-agent.md`）

| 角色 | 工序 | 只做这一件事 | 绝不做的 | 工具面（硬隔离） |
|---|---|---|---|---|
| `architect-agent` | 01/03/04 | 调研 + 出 `[PLAN]`/`[DESIGN]`、问题定性（点/类）与泛化评估 | 写代码、评审、测试；不跳过调研直接拍方案 | 禁 Write/Edit（**只读**） |
| `coder-agent` | 05 | 严格按 `[PLAN]`/`[DESIGN]` 实现，串行 | 改方案（发现缺陷停下反馈 architect）、顺手重构、自写测试、调用白名单外 skill | 可写；禁 NotebookEdit |
| `test-agent` | 06（做） | 生成并**实跑** unittest/探针/像素证据 | 自判质量；为过测试改业务逻辑 | 可写 + 浏览器 MCP（browser-use） |
| `reviewer-agent` | 05 外挂门禁 | 逐条过 L0 红线与 R00~R04 自检清单，出 Critical/Suggestion | 动手修复；评审方案合理性 | 禁 Write/Edit（**只读**） |
| `eval-agent` | 01/04/05/06 外挂（判） | 先 L0 证据核验，再 G0/L1/L2 三层判定，出结构化结论 | 修改任何产物（改卷即失效）；参与编排决策 | 禁 Write/Edit（**只读**） |
| `recorder-agent` | 聚合 | 汇编各角色产物进 biz/sys 记录、发布后存档报告 | 补写他人产物；加工决策；编辑历史章节 | 可写 |

**做判分离**是本流水线的骨架：生产者和批卷者必须是不同角色，`architect`/`reviewer`/`eval` 的只读是机制约束而非自律。

### 2.2 三条派发路（按本产品能力从强到弱选，选不到就降级并说明）

**路 A · 原生子智能体**（最优）。本产品有自定义 Agent 注册表，且六个名字出现在可派发清单里 → 直接按角色名派发。
- 角色卡源文件在仓库 `.qoder/agents/`；若注册表只认用户级目录，跑 `.venv\Scripts\python.exe tools\sync_agents.py` 镜像一份再**重开会话**（已实测：Agent 清单在会话启动时快照，中途注册当次会话不认）。

**路 B · 兜底子代理读角色卡**（当次会话可用）。派一个通用子代理，**提示首行**命令它先完整读角色卡，再干活：

```
你是 architect-agent。开工前必须先 Read E:\jiuzhang-operator\.qoder\agents\architect-agent.md 全文，
把它当作你自己的系统指令（含上下文白名单、职责、禁区、产出契约），并在回复首行确认已读到"本项目落地"一节。
```

⚠️ 路 B **不继承**角色卡的 `tools/disallowedTools/permissionMode`，只读隔离退化为指令自律。补偿两条，缺一条即视为未做隔离：
1. 派发给只读角色（architect/reviewer/eval）时，在提示里明令"禁止任何写文件与 git 写操作，只输出结论"；
2. 主会话对该角色交付**做一次 diff 复核**（`git status --porcelain` 必须与上一轮一致），有越界写入即整批作废重派。

**路 C · 单会话串行扮演**（本产品完全没有子代理能力时）。六道工序在同一会话内顺序执行，用**落盘产物**替代角色隔离：

- 每道工序结束立刻把结构化产物写进 biz 记录对应章节（`[REQ]`/`[PLAN]`/`[DESIGN]`/`[IMPL]`/`[VERIFY]`），工序之间**只允许读文件，不允许凭会话记忆推进**；
- "批卷"（Eval/reviewer 段）必须重新 Read 产物文件 + 实跑门禁命令，并逐条引用原文行号给结论；禁止"我记得上面写的是……"；
- 判定与执行之间明写一行 `── 角色切换：coder → eval ──`，让读者能核到边界。

路 C 是降级，不是等价：它消不掉"自己批自己的卷"，因此**全链需求坚持要主公确认后才走路 C**。

### 2.3 产品差异兜底

| 依赖 | 有则 | 无则（本文件已覆盖） |
|---|---|---|
| 项目级 `.qoder/rules/` 自动加载 | 自动生效 | 开工前手动 Read R00~R05 全文（细则见 §4/§6 摘要） |
| `skills/` 落盘即用 + `/feature-dev` | 用 slash 起编排 | 按 §3 清单手工驱动六道工序 |
| Agent 注册表 | 走路 A | 走路 B / 路 C |
| 浏览器 MCP（browser-use） | 前端改动真人路径 + 截图 | **明确写「未验证」**，不得用"几何达标"代替 |

---

## 3. 六道工序与门禁四态

```
- [ ] 01 意图识别  architect 读懂真实诉求 → checklist-01 → Eval-01 → 四态
- [ ] 02 编排规划  主对话：调度与能力预绑定（无外挂 Eval）
- [ ] 03 代码调研  architect 探索现有实现（可并行，结论并入 [PLAN]）
- [ ] 04 领域设计  architect 出 [DESIGN] → checklist-04 → Eval-04 → 四态
- [ ] 05 编码实现  coder 按绑定清单写码 → checklist-05 → Eval-05 + reviewer → 四态
- [ ] 06 自动化验证 test 五步验证环（做）→ checklist-06 → Eval-06（判）→ 四态
- [ ] 收尾        沉淀评估 → recorder 汇总 [IMPL]/[VERIFY]/[RELEASE] → 状态流转「已发布」→ 报告存档
```

**送检 checklist（送 Eval 前逐项核，任一不过就地打回，不消耗 Eval 轮次）**

| 工序 | 核对项 |
|---|---|
| 01 | 验收标准每条可回溯到主公原话或追问确认，无自行补充的需求 |
| 04 | 引用的存量接口/类/表/配置均带 `文件路径#符号`；分层动线与兼容性结论有代码定位；含问题定性（点/类），类问题有泛化方案 + 泛化点 + 扩展成本声明 |
| 05 | diff 涉及文件清单与实际变更一致；引用的错误码/枚举/参考实现均已验证存在 |
| 06 | 每条执行结论（编译/测试/覆盖）附**命令 + 原始输出**，禁止转述 |
| 通用 | 无"应该/一般来说/通常"式表述；每条事实断言带三类证据之一（代码定位 / 命令输出 / 记录引用） |

**门禁四态（唯一决策点，读 Eval 结果决定）**

| 态 | 条件 | 动作 |
|---|---|---|
| 过 | L0 证据核验 + 三层全过 + reviewer 无 Critical | 下一道工序 |
| 警告 | L2 建议项 / Suggestion | 记录理由后放行 |
| 回环 | 任一层 fail / Critical | 打回执行角色，**只传结构化失败清单**（不传情绪、不传解释） |
| 转人工 | 同工序回环 2 轮仍不过 | 停流水线，recorder 留痕，报告主公 |

**回环路由**：Eval-01 意图不清 → architect（缺哪条验收标准）；Eval-04 设计缺陷 → architect（缺陷层 + 原因）；Eval-05 / reviewer Critical → coder（失败清单 + 原因）；Eval-06 不及格 → test（断言问题）或 coder（实现缺陷），按 eval 归因走。

**转述即背书**：向 Eval 或门禁转交结论时必须同时转交证据；发现上游产物含无证据断言，就地打回，**不要替它补圆**。

---

## 4. L0 红线 9 条（逐条可判，能脚本化的都挂在门禁里）

1. **干净房间**：diff 中不得有任何来自旧项目（`E:\math-question-bank*` 等）的逐字内容。
2. **插件化**：插件侧 `fetch(` / `parent.document` / `localStorage` 命中必须为 **0**；插件不得直连 SQLite、文件系统、环境变量；插件间不得直接调用。
3. **出网**：任何出网必须由用户在界面**当场点击**发起，禁止定时器轮询与启动时顺手拉。
4. **两份 `plugins.json` 逐字节全等**；官方插件清单以 `tools/sync_plugin_index.py` 的 `PLUGIN_DIRS` 为准。
5. **版本单源** `app/__init__.py`；`plugin.json` 顶层 `id` == 目录名、无 `backend` 字段、必带 Apache-2.0 `LICENSE`。
6. **`data/` 是用户财产**：底座可写范围仅 `data/update_state.json` 与 `data/workspaces/<id>/*.json`。
7. **测试只能用 `.venv` 解释器逐模块跑**；禁止 pytest；禁止 `python -m unittest discover`（实测零用例假通过）。
8. **`.bat` 必须纯 ASCII + CRLF**；禁止正则后行断言 `(?<!...)` / `(?<=...)`；写接口必须挂 `Depends(require_write_token)`。
9. **`LICENSE` 与 `docs/AGENTS.md` 铁律一/二不得删改**。

---

## 5. 命令表

| 命令 | 用途 / 时机 |
|---|---|
| `bash scripts/check-quick-gate.sh` | **快门禁**（秒级只读，6 项）：每阶段收尾必跑；不绿不 commit |
| `bash scripts/check-release-gate.sh` | **收尾门禁**（分钟级，含全模块单测）：工序 06 与发版前 |
| `bash scripts/check-naming.sh` | 体系资产命名（R00） |
| `bash scripts/check-plugin-boundary.sh` | 插件三查 + 依赖方向 |
| `bash scripts/check-plugin-package.sh` / `check-plugin-index-parity.sh` | 插件包结构 / 两份索引全等 + Schema 自校验 |
| `.venv\Scripts\python.exe -m unittest tests.<模块名>` | 单模块测试（**系统 Python 会把所有模块打成假报错**） |
| `.venv\Scripts\python.exe tools\run_all_tests.py` | 全模块回归，失败模块 → rc=1 |
| `.venv\Scripts\python.exe tools\audit_code.py` | 静态红线（基线 ERROR 0 / WARN 36 / INFO 4） |
| `.venv\Scripts\python.exe tools\<名>_probe.py` | 真机探针 → `.system_generated/<名>/<tag>/probe.json` + 截图 |
| `.venv\Scripts\python.exe tools\pixel_scan.py <png>` | 像素证据行段结论（视觉改动必交） |
| `.venv\Scripts\python.exe tools\build_plugin.py --all` / `build_release.bat` | 打插件 zip / 打底座包 |
| `.venv\Scripts\python.exe tools\sync_agents.py` | 角色卡镜像到用户级（路 A 需要） |
| `.venv\Scripts\python.exe tools\clean_for_release.py --dry-run` | 发版前大扫除**预演**；不带 `--dry-run` 会真删并 `git gc`，须主公当场授权 |

---

## 6. 证据口径

**唯一对外交付证据 = 机械证据回传单五项**（`docs/AGENTS.md` §7.1，缺一不可，严禁只写"全绿/已完成"）：

1. **【改动清单】** 新增/修改/删除逐个点名（带行号或函数名）+ 禁改区自查（`LICENSE`、铁律一/二、`schemas/` 破坏性变更、用户 `data/`）。
2. **【包结构自检】**（涉插件才填）目录名 == `plugin.json.id`、无 `backend`、附 LICENSE、版本关系如实写明。
3. **【三查结果】** `fetch(` / `parent.document` / `localStorage` 命中数（必须 0）；请求 id 全符合 `^[A-Za-z0-9_-]{1,80}$` 且不含点号。
4. **【测试与探针】** 跑了哪些模块各自 N/N 绿、探针 passed/total、截图与 `probe.json` 路径、前端是否真人路径走过。
5. **【未决问题与偏离】** 欠账、与契约的偏离及理由、口径歧义采的解释、因环境限制**未验证**的部分——一律如实报。

`.qoder/records/biz/` 只是工序内过程稿，**不与回传单双写同步**。Eval 与门禁的结构化结论（`{工序号, 层, 过/否, 原因}`）作为第 4 项的证据来源抄录，数字必须来自当次实测。

**假通过黑名单**（撞到即判 G0 fail）：`unittest discover`；系统 Python 跑测试；只写"全绿"而无 `Ran N tests` 原文；用程序化 `focus` 冒充人手点击；探针端口/令牌写死（现存 5 支依 8765/8777、2 支写死 `dev-token-2026`，是历史坑，不许扩散）；只报"几何达标"不给截图。

---

## 7. 记录与命名（三件套缺一视为未完成）

- **biz**：`.qoder/records/biz/{YYYY-MM}/{YYYYMMDD}_{需求名}.md`，章节 `[REQ][PLAN][DESIGN][IMPL][VERIFY][RELEASE]`，append-only；日期 = 需求发起日，落盘不改。
- **sys**：`.qoder/records/sys/{YYYY-MM}/{YYYYMMDD}_{类型}_{主题}.md`（类型 ∈ rule/agent/skill/script/doc）——**任何 `.qoder/` 或 `scripts/` 资产变更都要一条**。
- **reports**：`.qoder/records/reports/{YYYY-MM}/{YYYYMMDD}_{需求名}.md`，与 biz 同名同月，只在状态流转「已发布」后生成。
- 新增资产必须同步三处：**磁盘存在 + sys 记录 + `docs/AGENTS.md` §9.5 索引表**（skill 还要进 `.qoder/skill-bank.json` 的角色白名单）。
- 命名：文件名英文 kebab-case，小写 a-z/数字/`-`，records 额外允许 `_`；禁止空格、大写、中文、`-v2/-new/-final/-bak`；角色卡一律 `{角色}-agent.md`；门禁脚本一律 `check-{对象}.sh` 放 `scripts/`。
- **工作树纪律**：评审只看本次 diff；主公已人为删除的文件（当前有 4 支 demo 插件处于未提交删除态、`docs/handoff/` 未跟踪）判为"主公的在途工作"，**不 stage、不 stash、不恢复**；提交用 `git add <点名文件>`，禁止 `git add -A`。

---

## 8. 环境坑（每条都返过工）

① `unittest discover` 零用例假通过；② `.bat` 非 ASCII 或非 CRLF 会哑弹；③ Git Bash 的 `find.exe` 抢占 PATH 会中断批处理；④ 无控制台时 `timeout`/`echo` 不可靠；⑤ `tools/verify_bank_empty.py` 写死 `E:\jiuzhang-operator` 盘符；⑥ 探针需 playwright + chromium，而 `playwright` **未写进 `requirements.txt`**（与 `docs/STACK.md` §7"锁定版本、禁止隐式安装"冲突，是否补入待主公裁决）；⑦ 底座令牌一次性轮换，`JZO_LOCAL_TOKEN` 非空即令整套轮换失效；⑧ 禁止 `taskkill /F /IM python.exe`；⑨ 触碰切库/重启端点的用例必须显式 `JZO_RESTART_DISABLED=1`，否则服务被自己重启带走；⑩ 22 个测试模块会真起 uvicorn，跑全量前先确认端口未被占。

---

## 9. 换产品核对清单（已验事实 vs 未知项）

**国际版 Qoder Desktop 已实测（2026-11-02，可当基线用）**：

- `.qoder/skills/**/SKILL.md` 落盘**当次会话即被识别**，`/feature-dev` 立刻可用。
- 六张角色卡放 `~/.qoder/agents/jiuzhang-pipeline/` 后被注册表收编（`enabled:true`、`definitionStatus:"ready"`、`usageScopes:["main","subagent"]`），**无需走 Settings 表单**（`manage_app_agent action=create` 零次调用即在册）。
- 但 **Agent 工具的可派发类型清单在会话启动时快照**：中途注册的角色当次会话报 `Unknown agent type`（时间线证据——会话起于 11:28:54、【示例】目录 11:26 可用、`jiuzhang-pipeline` 目录 11:55 不可用）。所以**换产品/换机器后第一件事是重开会话再验清单**，别在旧会话里反复试。
- 角色卡一旦进注册表，产品侧编辑会改写用户级镜像 → **唯一事实源永远是仓库 `.qoder/agents/`**：改角色先改仓库，再跑 `tools/sync_agents.py`，反向不可。

**国内版 Qoder 未知项（不要凭猜，按序实测并把结论回写本节）**：① 项目级 `.qoder/agents/` 是否被扫描（Desktop 只认用户级目录）；② rules 的 `trigger: model_decision` 是否生效；③ 子代理派发能力与工具白名单字段是否兼容；④ `permissionMode` 取值名是否一致。实测顺序：先跑 §0 步骤 2 取基线 → 派一次只读角色验 §2.2 路 A → 不行退路 B → 记录写 sys。

---

## 10. 不许做的事

1. 不越档：纯查询不起子代理；小改不上全链。
2. 主对话不产出技术方案与代码（那是 architect/coder 的产物）。
3. 不吞异常、不硬编码版本/开关/环境、不为过测试改业务逻辑、不顺手重构无关代码。
4. 不引前端框架（React/Vue）、不引第二语言（Go 等）、不加 pytest 依赖——除非主公明令。
5. 不物理删除题目记录（墓碑机制）；不动 `LICENSE` 与铁律一/二。
6. 不把长日志贴进战报；结论只给可核对的行段与数字。
7. 不静默绕过冲突：发现规范与实现打架，先停下来说明。
8. 不擅自 push、不擅自跑不带 `--dry-run` 的清理脚本。

---

九章算术，算子至简。

# AGENTS.md — 九章算子开发与 AI 代理铁律

本文件是九章算子仓库面向开发者与 AI 代理的唯一开发规范来源。任何代码、文档、资源或配置变更都必须先满足本文件；与本文冲突的局部约定一律无效。

项目身份：**九章算子 (Jiuzhang Operator)**，为独立教师打造的模块化数学题库底座。
许可：**Apache License 2.0**（全文见 `LICENSE`，不得替换或删改）。

## 1. 铁律一：干净房间开发（Clean Room）

**所有代码从零手写，严禁从原项目复制粘贴。**

- 禁止从 `E:\math-question-bank-main`、`E:\math-question-bank` 或任何其他历史目录复制源码、样式、脚本、注释、测试、文档、图片、字体、数据或目录结构。
- 禁止通过“改名、换变量、删注释、拆函数”等方式变相搬运旧实现。
- 可以阅读公开标准（JSON Schema、HTTP、Apache 2.0、Markdown、LaTeX 等）、通用算法描述与公开语言文档；落笔必须是原创表达。
- 设计思想可以讨论，代码与文档表述必须独立完成。若确实需要引用第三方片段，必须同时满足：许可与 Apache 2.0 兼容、在 `NOTICE` / 文件头注明来源与许可、经过评审；默认答案是“不引入”。
- 依赖许可白名单：Apache-2.0、MIT、BSD、ISC。**禁止 AGPL / GPL**；LGPL 及其他弱 copyleft 依赖必须逐项评审后才能引入。
- 提交前自查：本次 diff 中是否存在任何来自旧项目的逐字内容？存在即停止提交。

## 2. 铁律二：插件化架构（Harness 模式）

**本项目采用微前端与插件化设计。主底座仅负责鉴权、导航和数据总线。**

- 底座（`app/` 与 `static/` 中的宿主壳）只承担：身份与权限、全局导航、题目/资产/设置的数据总线、插件发现与生命周期、统一安全边界与错误隔离。
- 业务能力一律插件化：题目渲染、录入、导入、组卷、讲义、导出、AI 辅助、统计等，均以插件形式提供。新增需求先问“能否作为插件实现”，只有底座级能力才允许进入 `app/`。
- 插件不得直接访问数据库、文件系统、环境变量或模型密钥；只能通过 Host API 读写被授权范围内的数据。
- 插件之间不得直接调用或共享全局状态；跨插件协作必须经数据总线，且以题目标准结构为载荷。
- 前端插件必须运行在沙箱 iframe 中；宿主负责 HTML 净化、资源解析、公式渲染与降级。插件不得假设自己与宿主同源。
- 底座必须做到“插件坏了，底座还能用”：加载失败、渲染超时、连续报错都要有兜底渲染与隔离记录，不得让单个插件拖垮整个界面。
- 插件契约的唯一事实来源是 [PLUGIN_SPEC.md](PLUGIN_SPEC.md)；实现与契约不一致时，以契约为准并修正实现。
- **白嫖不可撤销**：个人版永久开源免费，底座与所有插件一律免注册、免卡密、无签名/摘要校验、无联网回连校验、无远程禁用（PLUGIN_SPEC §1.1）。插件格式统一为主流**纯 zip，解压即用**，禁止 `.jzo` 之类专属后缀（PLUGIN_SPEC §1.2）。底座也不得新增授权校验类 Host API。**出网铁律（2026-10-23 主公裁决，逐字生效）：底座严禁后台静默自动拉取。但允许用户手动点击【一键更新全部】按钮后，触发单次批量下载。** 换言之：任何一次出网都必须由界面上的当场点击发起，绝不做定时器轮询、绝不在启动时顺手拉、绝不跨条目批量抓取（「一键」只覆盖用户勾选/清单上明示有更新的条目）。允许的出网口子只有三个，且都必须由用户当场点击发起：①「插件索引」页（`static/plugins.html`）的索引拉取——输入框默认预填官方插件仓库 `jiuzhang-plugins` 的 `plugins.json` 的 gh-proxy 国内可达镜像直链，该次拉取失败时按 ghfast → jsDelivr → fastly.jsDelivr → Raw 的官方序列自动换源重试（仅限官方地址，用户改过的自定义地址不自动换源）；用户可当场改掉，点【拉取清单】才发只读 GET，不解压、不执行（PLUGIN_SPEC §1.3）；② 用户点某条目【在线安装】时，按该条目 `zip_url`（失败时按该条目 `mirrors`）只下载那一个 zip，走与本机拖装完全同款的校验落地，失败零残留（PLUGIN_SPEC §1.4）；③ 更新双轨（PLUGIN_SPEC §1.5）——用户点【检查更新】才拉清单比对版本号，用户点【更新】/【一键更新全部插件】才下载对应 zip；插件更新只解压覆盖 `plugins/<id>/` 代码目录，**严禁触碰 `data/` 目录**（工作区的物理题库是老师的财产），底座自更新走 `update.bat` 临时脚本（结束自身 → 覆盖文件并保护 `data/`、`.venv/`、`.git/` → 重启），重启后若仍有待更新插件则接着自动补齐（此续更只消费本机状态文件里用户上一轮亲手点选的清单，不再新增出网口子以外的下载源）。

## 3. 数据契约

- `schemas/question.json` 是题目在底座、插件、导入导出之间流转的**唯一标准结构**。
- 文本字段统一为 Markdown + LaTeX：行内公式 `$...$`，独立公式 `$$...$$`。不得另造公式方言。
- 题目全局身份只有 `id`（`q_` 前缀的稳定字符串）。原卷题号只属于来源关系（`source.question_no`），不得当作全局身份。
- 变更 Schema 必须：升 `schema_version`、同步更新示例、说明迁移方式、补充校验测试。破坏性变更升主版本。
- 插件私有数据只能写入 `extensions`，键使用反向域名前缀（如 `org.example.handwriting`），底座不得解释或改写这些数据。
- 不得把展示态内容（渲染后的 HTML、缓存、UI 状态）写回题目结构。

## 4. 技术栈与目录

- 后端：Python 3.10+、FastAPI、Uvicorn。
- 前端：原生 HTML + CSS + JavaScript，无打包器、无 Node 运行时依赖；资源必须本地化，可完全离线运行。
- 数据库：SQLite（`app/core/db.py`，标准库 `sqlite3`，WAL 优先）；结构版本写入 `PRAGMA user_version`，升级必须版本化、可回滚、备份优先；题目写入按 `schemas/question.json` 校验。
- 路径唯一来源：`app/core/config.py`。禁止依赖当前工作目录拼路径。
- 目录约定：
  - `app/api/`：底座级 HTTP 路由（健康检查、鉴权、导航、总线）。
  - `app/core/`：配置、路径、安全、日志等基础能力。
  - `schemas/`：跨边界数据契约。
  - `plugins/`：插件包（每个插件一个目录，含 `plugin.json`）。
  - `static/`：宿主壳静态资源。
- 禁止在根目录堆放业务模块。

## 5. 安全规范

- 所有不可信输入（题目文本、答案、标签、来源、OCR/AI 输出、插件返回值、图片属性）在进入 DOM 前必须净化。
- 插件返回的 HTML 禁止 `<script>`、内联事件属性、`javascript:` URL、远程样式与 `@import`；宿主必须使用白名单净化。
- 图片只允许底座托管路径或 `asset://` 逻辑地址；禁止远程 URL、`data:`、`file:`。
- 修改类接口必须鉴权；写操作不得只靠前端隐藏按钮来保护。
- 密钥只从环境变量或本地 `.env` 读取，永不入库、永不写日志、永不进入插件上下文。
- 文件访问必须校验路径边界，拒绝 `..`、符号链接逃逸与任意扩展名。

## 6. 前端与可访问性

- 所有交互控件必须可用键盘操作，焦点可见；弹窗具备焦点陷阱、`Esc` 关闭与关闭后焦点恢复。
- 触控目标不小于 44px；在 375px 宽度下不得横向溢出。
- 状态不得只靠颜色传达；加载中的按钮必须同步 `disabled` / `aria-busy`。
- 尊重 `prefers-reduced-motion`；动画只用于反馈，不阻塞操作。
- 禁止使用正则后行断言（`(?<!...)`、`(?<=...)`），避免旧浏览器直接语法失败。

## 7. 验证与提交

- 修改后端后至少运行：`python -m json.tool schemas/question.json`（涉及 Schema 时）、启动服务并请求 `/healthz`。
- 有测试后必须运行 `unittest`（**不许引入 pytest**，见 `STACK.md` §6）：单模块用
  `.venv\Scripts\python.exe -m unittest tests.test_plugin_install_url`；全量回归逐模块跑
  `for /f %f in ('dir /b tests\test_*.py') do .venv\Scripts\python.exe -m unittest tests.%~nf`。
  `python -m unittest discover` 会因 `tests/` 无 `__init__.py` 收集到零个用例——2026-11-02 实跑是
  `Ran 0 tests in 0.000s / NO TESTS RAN`，**绿色假通过，比直接报错更危险**，别用（`STACK.md` §7 第 91 行的
  discover 写法是旧口径，见到别照抄）。全量回归用 `.venv\Scripts\python.exe tools\run_all_tests.py`。
  必须用 `.venv` 里的解释器——系统 Python 缺依赖，会把全部模块打成假报错。
- 新增契约必须带测试。
- 修改前端后必须在浏览器中实际打开页面验证，不得只依赖静态检查。
- 提交信息使用中文，说明“为什么”而不只是“改了什么”；需要时附时间戳。
- **AI 代理不得执行 `git push`、创建远端、改写历史或发布 Release，除非用户明确要求。**
- 不得修改 `LICENSE`；不得删除本文件中的铁律一与铁律二。

## 7.1 机械证据回传单（军令 #12，2026-10-23 起长期铁律）

主线工作流固定为三段闭环：**军令任务卡（下行）→ 机械证据回传单（上行）→ 云端复审**。
每次交付必须按 `PROJECT_MEMORY.md` §5.6 的单子逐项给证据，**严禁只写「全绿」「已完成」**。
五项缺一不可：

1. **【改动清单】**：新增/修改/删除了哪些文件（逐个点名，修改带行号或函数名）；
   并自查有没有动到禁改区——`LICENSE`、本文件铁律一与铁律二、`schemas/` 破坏性变更、用户 `data/` 目录。
2. **【包结构自检】**（涉及插件才填）：顶层目录名 == `plugin.json` 的 `id`；无 `backend` 字段；
   附 Apache-2.0 `LICENSE` 全文；`min_host_version` / `engine.host_version` 与当前底座版本的关系如实写明。
3. **【三查结果】**：`fetch(`、`parent.document`、`localStorage` 三项 grep 命中数（插件侧必须为 0）；
   请求 id 全部符合 `^[A-Za-z0-9_-]{1,80}$` 且不含点号（含点号必被宿主 `BAD_REQUEST_ID` 拒发）。
4. **【测试与探针】**：跑了哪些单测模块、各自 N/N 绿（解释器必须是 `.venv/Scripts/python.exe`）；
   真机探针跑没跑、判据 passed/total、截图与 `probe.json` 的落盘路径；前端改动是否在浏览器里真人路径走过。
5. **【未决问题与偏离】**：欠账、与契约的偏离及处理理由、军令用词歧义时采的解释性口径、
   因环境限制**未验证**的部分——一律如实汇报，不用推测代替证据。

配套执行铁律：每完成一个大阶段立即 `git commit`（提交信息标注阶段），**测试不绿绝不许 commit**；
多阶段军令严禁一口气写完再提交，全部阶段干完后按授权统一 `git push`。回传单里的数字必须来自当次实测输出，
沿用旧证据要注明轮次。

## 8. AI 代理工作方式

1. 开工前先读本文件、`PLUGIN_SPEC.md` 与相关 Schema。
2. 先确认范围，再动手；不擅自扩大改动面。
3. 严格遵守干净房间原则，不参考旧项目实现细节。
4. 如实报告验证结果；没有验证就明确说“未验证”，不得用推测代替证据。
5. 发现规范与实现冲突时，先停下来说明，不得静默绕过。
6. 变更影响契约、架构或验证方式时，同步更新文档。

---

## 9. 六工序多智能体工作流（2026-11-02 入驻，每会话默认生效）

> 本节只放**入口、红线与索引**，细则一律按索引加载，禁止在此堆积细节。
> 体系资产随仓库走：`.qoder/`（agents / rules / skills / records / skill-bank.json）+ `scripts/check-*`。
> 流水线只管"允许 / 禁止 / 怎么做"；事实性背景知识查 RepoWiki 与 knowledge cards。

### 9.1 触发分级（主公 2026-11-02 裁决）

| 请求类型 | 工作流 | 必跑门禁 |
|---|---|---|
| 新功能、多阶段需求、跨底座与插件的改动 | 六工序全链（`/feature-dev`，工序 01→06 + 四道 Eval） | 快门禁每阶段 + 收尾门禁 |
| 单点缺陷修复、小改文案与样式 | coder → reviewer → eval（跳过 01/03/04 的独立 Eval） | 快门禁 |
| 纯查询、解释、读代码 | 不起子智能体，直接答 | 无 |
| 发版、封版、出包 | 走 `domain/build-release` 动线 | 收尾门禁 |

命中前两类时，主对话只做编排与透传，**不自行设计或写代码**；判定结果每轮告知主公，主公可随时说"升级成全链"或"停下"。

### 9.2 六个角色（`.qoder/agents/`，做判分离）

| 角色 | 工序 | 职责边界 | 调用名 |
|---|---|---|---|
| architect-agent | 01/03/04 | 调研与方案，只出 [PLAN]/[DESIGN]，禁写代码 | `architect-agent` |
| coder-agent | 05 | 按方案串行实现，不改方案、不自评 | `coder-agent` |
| test-agent | 06（做） | 生成并实跑测试/探针/像素证据，不自判质量 | `test-agent` |
| eval-agent | 判 | L0 证据核验 + G0/L1/L2 三层判定，只判不做 | `eval-agent` |
| reviewer-agent | 门禁 | L0/L1 符合性，输出 Critical/Suggestion，不动手 | `reviewer-agent` |
| recorder-agent | 聚合 | 汇编 biz/sys 记录与报告，不补写他人产物 | `recorder-agent` |

**生效条件**：子智能体清单在会话启动时快照，**新开会话才会认得这六个名字**（`.qoder/skills/` 则落盘即用）。角色不可调用时按序兜底：① `.venv\Scripts\python.exe tools\sync_agents.py` 把角色卡镜像到用户级后重开会话；② 当次会话用 `general-purpose` 起子代理，并在提示首行命令其先 `Read` 对应角色卡全文当作自己的指令。

### 9.3 L0 红线（能脚本化的都挂在门禁里）

1. 铁律一干净房间：diff 中不得有任何来自旧项目的逐字内容。
2. 铁律二插件化：插件侧 `fetch(` / `parent.document` / `localStorage` 命中必须为 0；插件不得直连数据库、文件系统、环境变量；插件间不得直接调用。
3. 出网铁律：任何出网必须由界面当场点击发起，禁止定时器轮询与启动时顺手拉。
4. 两份 `plugins.json` 必须逐字节全等；官方插件清单以 `tools/sync_plugin_index.py` 的 `PLUGIN_DIRS` 为准。
5. 版本单一事实源 `app/__init__.py`；`plugin.json` 顶层 `id` == 目录名、无 `backend`、必带 Apache-2.0 `LICENSE`。
6. `data/` 是用户财产，底座可写范围仅 `data/update_state.json` 与 `data/workspaces/<id>/*.json`。
7. 测试只能用 `.venv` 解释器逐模块跑；禁止 pytest、禁止 `unittest discover`（零用例假通过）。
8. `.bat` 必须纯 ASCII + CRLF；禁止正则后行断言；写接口必须鉴权。
9. `LICENSE` 与本文件铁律一、铁律二不得删改。

### 9.4 门禁命令

| 档 | 命令 | 时机 |
|---|---|---|
| 快门禁（秒级，只读） | `bash scripts/check-quick-gate.sh` | 每个阶段收尾；**不绿 = 未完成，不绿不 commit** |
| 收尾门禁（分钟级） | `bash scripts/check-release-gate.sh` | 工序 06、发版前 |

### 9.5 资产索引（新增资产必须在此登记 + 写 sys 记录 + 进 `skill-bank.json`，三件套缺一视为未完成）

| 资产 | 路径 | 触发 |
|---|---|---|
| R00 命名规范 | `.qoder/rules/R00-naming.md` | 新建/重命名任何体系文件前 |
| R01 模块与构建发布 | `.qoder/rules/R01-module-build.md` | 改结构、加依赖、动版本字段与 `.bat` |
| R02 编码与错误处理 | `.qoder/rules/R02-coding-error.md` | 写路由/core、写宿主壳与插件 JS、加错误码 |
| R03 分层·数据·配置 | `.qoder/rules/R03-layer-data-config.md` | 加表加库、写迁移、动 config/.env/令牌 |
| R04 测试与流程 | `.qoder/rules/R04-test-workflow.md` | 写测试、跑回归、提交、更新项目记忆 |
| R05 流水线与 Eval | `.qoder/rules/R05-pipeline-eval.md` | 执行流水线、质检判定、四态决策 |
| skill-bank.json | `.qoder/skill-bank.json` | 三层 skill 清单 + 角色白名单 |
| 六角色卡 | `.qoder/agents/` | 见 §9.2 |
| process skills | `.qoder/skills/process/`（`feature-dev`、`init-pipeline`） | `/feature-dev` 编排 |
| domain skills | `.qoder/skills/domain/`（`add-plugin`、`add-host-api`、`add-data-store`、`run-regression`、`build-release`、`prove-visual-change`） | 对应重复操作 |
| base skills | `.qoder/skills/base/`（`sync-biz-record`、`sync-sys-record`、`archive-tech-report`） | 记录与归档 |
| 操作记录 | `.qoder/records/{biz,sys,reports}/` | 按月分层，文件名含日期 |
| 脚本门禁 | `scripts/check-*.{sh,py}`、`tools/audit_code.py`、`tools/run_all_tests.py` | §9.4 |
| 角色卡镜像 | `tools/sync_agents.py` | 角色不可调用时 |

### 9.6 常用命令与环境坑

| 命令 | 用途 / 坑 |
|---|---|
| `start.bat` | 建 venv + 装依赖 + 起服务；默认端口 8000，被占自动顺延到 8009，全占则 rc=1 |
| `.venv\Scripts\python.exe -m unittest tests.<模块>` | 单模块测试；**系统 Python 会把全部模块打成假报错** |
| `.venv\Scripts\python.exe tools\run_all_tests.py` | 全模块回归，失败模块 → rc=1 |
| `bash scripts/check-quick-gate.sh` / `check-release-gate.sh` | 两档门禁 |
| `.venv\Scripts\python.exe tools\audit_code.py` | 静态红线（基线 ERROR 0 / WARN 36 / INFO 4） |
| `.venv\Scripts\python.exe tools\<名>_probe.py` | 真机探针，产物 `.system_generated/<探针名>/<tag>/probe.json` + 截图 |
| `.venv\Scripts\python.exe tools\build_plugin.py --all` | 打插件 zip（写 `dist/`） |
| `build_release.bat` | 打底座包（写 `dist/`，包内 `bank.db` 是 0 题空基线） |
| `.venv\Scripts\python.exe tools\clean_for_release.py --dry-run` | 发版前大扫除预演；**不带 `--dry-run` 会真删并跑 `git gc`，须主公当场授权** |
| `.venv\Scripts\python.exe tools\sync_plugin_index.py` | 同步两份插件索引（需兄弟仓库 `E:/jiuzhang-plugins` 存在） |

环境坑（每条都有过返工）：① `unittest discover` 零用例假通过；② `.bat` 非 ASCII 或非 CRLF 会哑弹；③ Git Bash 的 `find.exe` 抢占 PATH 会中断批处理；④ 无控制台时 `timeout`/`echo` 不可靠；⑤ `tools/verify_bank_empty.py` 写死 `E:\jiuzhang-operator` 盘符；⑥ 探针需 playwright + chromium，而 **`playwright` 未写进 `requirements.txt`**（`STACK.md` §7 第 92 行要求"锁定版本、禁止隐式安装"，是否补入待主公裁决）；⑦ 5 支探针手依 8765/8777、2 支写死 `dev-token-2026`，而底座令牌是一次性轮换——新探针禁止写死端口与令牌；⑧ 禁止 `taskkill /F /IM python.exe`；⑨ `JZO_LOCAL_TOKEN` 非空即令整套轮换失效；⑩ 工作树里 4 支 demo 插件的删除态与 handoff 未跟踪文件是他人在途工作，不得 stage/恢复。

### 9.7 交付证据口径

**唯一对外交付证据仍是 §7.1 机械证据回传单**（五项缺一不可）；`.qoder/records/biz/` 只作流水线工序内的过程稿，不做双写同步。Eval 与门禁的结构化结论（工序号/层/过否/原因）作为回传单第 4 项的证据来源抄录，数字必须来自当次实测输出。

---

九章算术，算子至简。以此为碑，铭记今日。

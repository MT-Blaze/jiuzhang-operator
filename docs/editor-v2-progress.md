# editor 录题界面改造 · 进度记忆清单

军令 #23（2026-10-31 发令）· 改造对象 `plugins/org.jiuzhang.editor`，不新建插件。
本文件是跨阶段唯一记忆清单：每阶段开工前先读它 + 军令对应条款，读完把「当前阶段」改成「进行中」再动手。

## 当前阶段
- 阶段 1：已验收并提交（三栏骨架 + 单题静态渲染）
- 阶段 2：已验收并提交（辅助栏表单 + 源码双格式 + 单题保存/更新/变式）
- 阶段 3：未开始（下一步：AI 帮改档 1）
- 阶段 4：未开始

### 阶段 1 收口摘要（2026-10-31）
- 画布实例只有三栏：`#edImageBody` | `#edSourceBody` | `#edRenderBody`，中间两条 `#edSplitImage` /
  `#edSplitSource` 拖手；`--pane-min: 28px` + `clampValue()` 保证拖不归零，只留极窄缝。
- 中栏 textarea 装**整段** `\begin{question}…\end{solution}`（`readOnly`，阶段 2 打开编辑）；
  画布内没有任何 `select` / `input`，元数据一律留给辅助栏。
- 右栏按内容实际高度渲染（题干 / 选项 / 答案 / 解析），A4 固定几何（794×1123、`PAGE_W/PAGE_H`、
  `fitPreview`）随「渲染不固定 A4」这条已定决策整体撤除。
- 三栏共用一条滚动：`alignRows()` 把每题行高取三栏最大者，短栏余高即 `--void: #fafafa` 淡底留白；
  `syncScroll()` 单向同步并带 `scrollLock` 防回路；`growTextarea()` 让源码区自撑高、无内部滚动条。
- 阶段 2 直接复用、**不要重写**这一批实现：`parseExamSource()` / `buildExamSource()` /
  `cleanExamSource()` / `matchEnv()` / `splitChoices()` / `detectType()`。
- 版本 `1.0.0 → 1.1.0`，清单描述与根 `plugins.json` 索引条目逐字同步（`tests/test_clean_latex.py::test_03`）。
- 沙箱三查（`fetch(` / `parent.document` / `localStorage`）在 `dist/*.js|html|css` 命中 0；
  请求 id 形如 `edv2<seq>-<base36>`，无点号。

### 阶段 2 收口摘要（2026-10-31）
- 清单：`version 1.2.0`、`slots: ["stage.center","sidebar.right"]`、权限加 `ai:invoke`、新增 `ui.controls`
  的 `format` select（格式一/格式二）——`ui.params.set` 只认清单声明过的 select 键，没这一步格式切换就无通道；
  `bus.subscribe` 5 条（+ `stage.selection` / `system.question_updated`）；根 `plugins.json` 版本与描述逐字同步。
- 辅助栏（`#epRoot`）四段：**进度与状态**（第 N/M 题、● 待审核/已入库、置信度标「假数据占位」）
  → **元数据表单**（题型 AI 预填且注明「可人工改」/难度 L1–L4/年级/来源随手填/考向懒展开树/标签）
  → **审核动作**（【保存本题】【另存为新题】真可用，【通过入库】【打回修改】【跳过】disabled + `aria-disabled`
  + 话术「下一军令」）→ 双格式切换按钮。辅助栏里 **0 个 textarea、0 个 `.ed-q-block`**（源码与预览一律不回右栏）。
- 画布：中栏 textarea 打开 `readOnly`；格式二按环境拆框（`.ed-box` / `.ed-box-env` 锁死 `\begin{…}`、`\item`、
  「首行」「内」文本标签，只暴露 `.ed-box-area` 改内容），改动即时经 `boxesToQuestion()` → `buildExamSource()`
  重组格式一，切回格式一看骨架不坏。
- 写库：`saveItem()` 只走 `bank.create`（新建）/ `bank.update`（编辑，**载荷不带 `sources`**，
  否则会把一题多卷的原卷清单整组覆盖掉）；保存前 `validateForSave()` 出中文话术（`LOCAL_INVALID`），
  失败码 `FORBIDDEN`/`PERMISSION_DENIED`/`RATE_LIMITED`/`NOT_READY`/`HOST_409`/`HOST_422`/`HOST_404` 各有可读提示。
- **两帧通信补的两处硬伤**：
  1. 宿主 `publish` 是即投不缓存（`stage.js:287`），面板帧挂载可能错过 `stage.selection`——
     面板冷启动改为从 `draft.load("editor:v2:worklist")` 用 `applyDraftSelection()` 还原当前题，
     并带 900ms 二次读取；画布挂载链路补 `saveWorklist(); publishSelection();` 让草稿先有内容；
  2. 落库回执 `system.question_updated` 由宿主**先广播、后把应答送回面板**（`stage.js:1461`），
     画布第一次 `draft.load` 常读不到回执——`consumeReceipts()` 加 350ms×4 次重试；认领后画布自己
     调 `showSaved()` 把题号回显到顶栏（面板那句「已入库」画布看不见），派生变式的题号另存进
     `#epMetrics` 的 `data-variant-id`（话术区会被随后回投的选区盖掉，只靠文本没法复查）。
- **年级必须双写**：底座 create 路径只从 extensions 认年级（`bank.py:687` `_grade_from`，顺序
  `org.jiuzhang.core-bank.grade` → `org.jiuzhang.editor` → `org.jiuzhang.legacy`），契约根字段 `grade`
  在写路径上没人读，只交根字段老师填的年级静默丢失。插件保留根字段（契约）并补写
  `extensions["org.jiuzhang.editor"].grade`，与 v1 录题插件同键。
- 无障碍：考向行/展开钮触控目标 ≥44px，`.ep-chip-x` 用 `::after` 扩热区；写库中按钮 `disabled` + `aria-busy` 同步。
- 证据：`tests/test_editor_contract.py` 56 条全绿；`test_clean_latex` 9（2 skip）、`test_command_registry` 33、
  `test_plugin_bus_parity` 5、`test_stage_canvas` 27 全绿；真机探针 `tools/editor_probe.py` 重写为 v2 判据，
  **45/45 通过**（`.system_generated/editor_probe/s2-4/probe.json`，控制台与页面错误 0），
  新建题 `q_0d871fe002139195875325f9`、更新走同 ID、派生变式 `q_b784b69c7ba6ad22d15f4c0c`、题库画布搜得到。
- 交给阶段 3：`tests/test_clean_latex.py::EditorAiCleanerTest` 仍有 2 条 skip（旧画布 AI 清洗按钮已随表单退场），
  辅助栏「AI 帮改」重写后要在档 1 路径上恢复判据；`editor.apply_patch` 通道与命令面已就位，画布收到
  `field=stem|solution` 只回「军令 #23 阶段 3 接入」的 toast。

## 已定设计决策（不可改，改需主公批准）
- 三栏布局：左原图 | 中 LaTeX 源码 | 右渲染，全在画布内
- 辅助栏：元数据表单 + AI 帮改 + 审核动作，不占源码/预览
- 源码只用 exam-zh 标准环境：question / problem / choices / solution；填空用 \fillin
- 答案只写 \begin{solution} 开头「答案：X」；\fillin 不带答案
- 选择题题干末尾加（  ）
- 源码双格式：格式一标准 LaTeX；格式二框框视图，框里是 LaTeX 代码，只能改内容不能改环境，改完自动重组
- AI 帮改档 1：选中 → 辅助栏输入框 → 发送 → 辅助栏预览 → 点【采用】才替换
- 单题 + 批量同一界面，只是题目数量不同
- 渲染不固定 A4，按内容实际高度
- 单题保存 + 底部【保存全部】；保存全部只提交脏题
- 批量新建进 pending 池，不直接入主库（本期只做界面，pending 存储层留待下一军令）

## 架构口径（阶段 1 探明，后续阶段沿用）
- 宿主右栏是**第二个沙箱 iframe**（`static/js/context_panel.js`）：editor 声明 `slots: ["sidebar.right"]` 后，
  画布实例与辅助栏实例是**同一插件的两个独立帧**，彼此拿不到对方的 DOM 与内存。
- 两帧之间只有底座已开好的四条合法通道（阶段 2 起使用）：
  1. 画布 → 辅助栏：插件发布 `stage.selection` 通知（发布白名单内），宿主只投递给面板帧
     （`static/js/stage.js:2532`），载荷在 `payload.raw` 原样送达；
  2. 辅助栏 → 画布：`ui.params.set` 请求 → 宿主广播 `ui.params.changed`（`static/js/workspace.js:364`），
     只认清单 `ui.controls` 里声明过的 select 键值，AI/面板永远赢不过人的手改；
  3. 辅助栏 → 画布：`editor.apply_patch` 请求 → 宿主 `broadcast`（`static/js/stage.js:1241`），
     载荷 `{id, field(stem|solution), value≤20000}`，画布用它做「AI 采用替换选区」；
  4. 共享态：`draft.save` / `draft.load` 按 `plugin.id` 分命名空间，两帧读的是同一份宿主代持草稿，
     用于辅助栏挂载时补历史状态（插件侧绝不出现 `localStorage`）。
- 假数据单一事实来源：`plugins/org.jiuzhang.editor/dev/fixtures.json`；
  `dist/plugin.js` 里 `//# FIXTURES-BEGIN/END` 之间内嵌同一份 JSON（沙箱 CSP `connect-src 'none'`，
  插件不能 fetch 本地文件，只能内嵌）。契约测试逐字段比对两处，防漂移。
- `dev/` 目录不进发行包（`tools/build_plugin.py` 的 `DENY_DIRS` 增加 `dev`）。

## 本阶段已改动文件（阶段 1）
- `plugins/org.jiuzhang.editor/dist/index.html`：重写为三栏画布 + 辅助栏空根节点 `#epRoot`。
- `plugins/org.jiuzhang.editor/dist/plugin.css`：重写（三栏网格、拖手、`--void` 留白、`.ed-src-area` 自撑高）。
- `plugins/org.jiuzhang.editor/dist/plugin.js`：重写（约 919 行，解析 / 重组 / 清洗 / 三栏渲染 / 拖宽 / 共滚动）。
- `plugins/org.jiuzhang.editor/plugin.json`：`version 1.1.0` + 新描述；slots / 权限 / 命令暂不动。
- `plugins/org.jiuzhang.editor/dev/fixtures.json`：新增，1 道合法 2.0 单选题（假数据唯一来源，不进包）。
- `tools/sync_editor_fixtures.py`：新增，把 `dev/fixtures.json` 同步进 `plugin.js` 标记块。
- `tools/build_plugin.py`：`DENY_DIRS` 增加 `dev`（开发期文件一律不进发行包）。
- `plugins.json`：editor 条目版本与描述随清单更新。
- `tests/test_editor_contract.py`：按 v2 三栏契约重写（36 条）。
- `tests/test_clean_latex.py`：`EditorAiCleanerTest` 前两条判据 skip（画布 AI 清洗按钮随旧表单退场，
  阶段 3 在辅助栏重写）；第三条不再写死版本号，改为「索引 == 清单」。
- `tests/test_command_registry.py`：EXPECTED 里 editor 版本改 1.1.0（这张表按设计写死版本）。

## 本阶段已改动文件（阶段 2）
- `plugins/org.jiuzhang.editor/plugin.json`：1.2.0、描述、`ai:invoke`、`ui.controls.format`、subscribe 5 条、三条命令描述改 v2 口径。
- `plugins/org.jiuzhang.editor/dist/plugin.js`：面板实例整段（表单/考向树/审核动作/状态位）、格式二拆框与重组、
  `saveItem()` 写库分支、`validateForSave()`、`explainHostError()`、`applyDraftSelection()` 冷启动兜底、
  `consumeReceipts()` 重试 + 画布回显、变式 `data-variant-id`、`questionFromParsed()` 年级双写。
- `plugins/org.jiuzhang.editor/dist/index.html`：`#epRoot` 辅助栏表单结构（进度/元数据/审核/格式切换）。
- `plugins/org.jiuzhang.editor/dist/plugin.css`：面板样式 + 44px 触控热区 + `.ed-box*` 框框视图。
- `plugins.json`：editor 条目 1.2.0 + 描述与清单逐字对齐。
- `tests/test_editor_contract.py`：36 → 56 条（新增 `EditorPanelTest`、`EditorBoxedFormatTest`，
  写库通道白名单、冷启动兜底、回执重试、年级双写、变式状态位）。
- `tests/test_command_registry.py` / `tests/test_plugin_bus_parity.py`：版本 1.2.0、editor 订阅集补两条主题。
- `tools/editor_probe.py`：整体重写为 v2 三栏 + 辅助栏判据（45 项），隔离数据目录、`JZO_RESTART_DISABLED=1`、
  题数一律用 before/after 差值，不写死 456。

## 本阶段未决 / 待主公复核
1. **探针：`editor_probe.py` 已跟上，`editor_crop_probe.py` 仍待裁**：前者阶段 2 整体重写为 v2 判据并跑到
   45/45；后者驱动的「原图框选切图」军令 #23 已明确本期不做，建议直接退役删除（要留可从 git 历史找回）——
   等主公点头再删，本次没动它。
2. **A4 判据消失**：旧 `tests` 里 794×1123 那组红线随「渲染不固定 A4」撤除，`paper-gen` / `handout`
   仍各自守 A4 几何，不受影响；如主公认为录题也该留一份分页证据，请裁决。
3. **`safeAssetUri` 放宽**：为让假数据的原图占位可渲染，新增放行 `/static/icons/`、`/static/assets/`
   两个底座本地前缀（仍禁远程 URL / `data:` / `file:`）。若认为过宽，阶段 2 收回到只认 `/static/uploads/`。
4. **假数据解析自相矛盾**：军令《格式宪法》示例的题干是 `$f(x)=x^2+1$`，解析却写「配方得
   $f(x)=(x-1)^2+1$」——两者不等价（答案 B 倒都成立）。当前逐字保留军令原文，等主公决定改题干还是改解析。
5. **审核动作只做了两个**：【通过入库】【打回修改】【跳过】三键本期 disabled（话术写明下一军令），
   底座也没有 `bank.review` 通道给插件用；【另存为新题（派生变式）】已可用，但它只是「新建一题」，
   与契约里的派生关系（parent_id）无关——真要记派生链，得先定 schema 落位。
6. **底座 update 不推进修订号**：`app/core/bank.py` 的 `update_question()` 只改 `meta.updated_at`，
   `meta.revision` 恒为 1（全仓无自增路径）。探针按「修订号 +1」判据会打成假红，已改成如实记录
   `updated_at` 前进 + `revision == 1`。若认为修订号该前进，这是底座改动，超出本军令「只改 editor」的范围。
7. **运行中的工作区仍是旧 editor**：`app/core/config.py:93 plugins_dir()` 指向
   `data/workspaces/default/plugins/`，那是用户数据区，军令红线禁碰，所以本次没有覆盖它。
   主公回来看新界面的两条路：插件控制台里重装 / 更新，或用 `JZO_PLUGINS_DIR=E:\jiuzhang-operator\plugins`
   起一个开发实例（探针走的就是后者，不写用户目录）。

## 下次开工先读
1. 本文件
2. 本军令对应阶段条款
3. AGENTS.md §7

# editor 录题界面改造 · 进度记忆清单

军令 #23（2026-10-31 发令）· 改造对象 `plugins/org.jiuzhang.editor`，不新建插件。
本文件是跨阶段唯一记忆清单：每阶段开工前先读它 + 军令对应条款，读完把「当前阶段」改成「进行中」再动手。

## 当前阶段
- 阶段 1：已验收并提交（三栏骨架 + 单题静态渲染）
- 阶段 2：已验收并提交（辅助栏表单 + 源码双格式 + 单题保存/更新/变式）
- 阶段 3：已验收并提交（辅助栏 AI 帮改档 1 + 宿主规则清洗回填）
- 阶段 4：未开始（下一步：批量无缝滚动 + 左栏联动 + 底部【保存全部】）

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
- 交给阶段 3 的两件都已清：`test_clean_latex.py::EditorAiCleanerTest` 两条 skip 按辅助栏新契约重写（现 4 条），
  画布对 `editor.apply_patch` 的「阶段 3 接入」占位 toast 换成真的分段回填。

### 阶段 3 收口摘要（2026-10-31）
- 辅助栏新增「AI 帮改（档 1）」一节：字段提示 `#epAiField` → 指令框 `#epAiAsk` →【发送改写请求】
  【AI 清洗公式】→ 状态徽标 `#epAiState`（未发起 / 等模型回话 / 清洗中 / 待老师裁决 / 改写失败）
  + 纯文本预览 `#epAiPreview` →【采用并回填画布】【放弃】。预览一律 `textContent`，模型回什么都不进 DOM 结构。
- **可改范围由源码结构算出，不靠人选**：`envSpan()` + `fieldRanges()` 把「题干段」定为题干环境正文里
  choices 之前那一段、「解析段」定为 solution 正文剥掉「答案：」首行之后那一段；
  `fieldAtOffset()` 判不出字段一律回 `""`（选项、答案行、环境名外都不许 AI 伸手）。
  画布 textarea 与格式二的题干/解析框都补 `click/keyup/select` → `publishSelectionSoon`，选区载荷多一个 `caret`。
- **采用门**：`renderAi()` 只在 `panel.ai.state === "ready"` 才放开【采用】；发送前必须「有字段 + 有指令」，
  请求中三个动作按钮同步 `disabled` + `aria-disabled` + `aria-busy`。
- **目标题回认**：宿主只把 `{id, field, value}` 广播给各帧，所以当前题的键经 `patchIdFor()`
  规范化（非 `[A-Za-z0-9_-]` 换 `-`、前缀 `ai1-`、截 80）编进 `id`；画布 `applyAiPatch()` 认不出键就
  拒收并 toast「AI 回填的目标不是当前题，源码没动」，面板 `onAiApply()` 换题后也不许把上一题的改写发出去。
  面板收到自己发出的 `editor.apply_patch` 广播保持静默（只有 `state.slot === "stage.center"` 动手），一次采用不会改两遍。
- **话术诚实**：宿主摊平 `/api/agent/refine` 时把 `mock` 标记丢了（`stage.js:1157`），插件只能用
  「新值与原文逐字相同」近似判定回显，话术写「多半是回显（本机还没配 Provider）」；
  面板说「已发给画布…保存才入库」，绝不把「请求成功」说成「已入库」。
- **超时对齐**：宿主给模型的额度是 60s（`stage.js:399 AGENT_TIMEOUT_MS`），插件默认 20s 会把慢回答误报成失败，
  故 `hostCall()` 支持逐请求超时、AI 改写走 `AI_REQUEST_TIMEOUT_MS = 65000`；规则清洗不经模型，仍按 20s。
- **清洗回填**：【AI 清洗公式】对题干段与解析段并发 `text.clean_latex`，`Promise.all` 全成功且每段非空
  才逐段 `editor.apply_patch`；任一失败或洗成空就一个字都不动，话术报出中止原因（`test_clean_latex` 钉住）。
- 模型上下文只交 `type/difficulty/stem/options/answer/solution`（`refineContext()`），与底座
  `build_refine_user_message` 同口径；extensions、题号、令牌一律不上桥。
- 无障碍与样式：`.ep-ai` 预览区 `white-space: pre-wrap` + `overflow-wrap: anywhere`（长公式不撑破右栏）、
  状态徽标按 `data-ai-state` 换色但文字同时变（不只靠颜色）、按钮沿用 `.ep-btn` 44px。
- 证据：`test_editor_contract.py` 56 → 64 条、`test_clean_latex.py` 9（含 2 skip）→ 10 条（0 skip）全绿；
  `test_command_registry` 33、`test_plugin_bus_parity` 5 同步绿；
  真机探针 `tools/editor_probe.py` 加 20 项阶段 3 判据，**65/65 通过**
  （`.system_generated/editor_probe/s3-1/probe.json`，页面/控制台错误 0）。
  探针自带本机 OpenAI 兼容桩（`StubProvider`，`JZO_AI_BASE_URL` 指向 `127.0.0.1`，环境变量优先于仓库 `.env`），
  两次改写请求真走到桩（`metrics.ai.fields == ["stem","solution"]`），全程零出网、不碰老师密钥。
- 交给阶段 4：批量无缝滚动 + 左栏联动 + 底部【保存全部】只提交脏题 + pending 池界面。

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

## 本阶段已改动文件（阶段 3）
- `plugins/org.jiuzhang.editor/plugin.json`：1.2.0 → **1.3.0**，描述补「AI 帮改（档 1）：只改题干段与解析段，
  预览后点采用才回填画布」；slots / 权限 / 命令面不动（`ai:invoke` 阶段 2 已申请）。
- `plugins/org.jiuzhang.editor/dist/plugin.js`：常量 `AI_REQUEST_TIMEOUT_MS` / `AI_ASK_MAX`；
  分段工具 `envSpan()` `fieldRanges()` `fieldAtOffset()` `replaceField()` `patchIdFor()` `keyFromPatchId()`；
  画布侧 `applyAiPatch()` `writeBackSourceText()` `caretOfActive()` 与 `selectionPayload().caret`、
  源码框/框框视图的 `click|keyup|select` 上桥、通知分支只让画布执行回填；
  面板侧 `setEpEnabled()` `renderAi()` `aiClear()` `refineContext()` `segmentOf()` `onAiSend()`
  `onAiApply()` `onAiDiscard()` `cleanViaHost()` 与 9 个新 DOM 引用、`panel.ai` 状态位、换题作废。
- `plugins/org.jiuzhang.editor/dist/index.html`：`#epRoot` 内新增「AI 帮改」一节（9 个 `epAi*` 节点，
  【采用】【放弃】【发送】【清洗】出厂全 disabled + `aria-disabled`）。
- `plugins/org.jiuzhang.editor/dist/plugin.css`：`.ep-ask` `.ep-ai` `.ep-ai-head` `.ep-ai-body`
  与 `[data-ai-state=…]` 四态配色、`[data-ai-mock="true"]` 回显话术色。
- `plugins.json` **与** `E:/jiuzhang-plugins/plugins.json`：由 `tools/sync_plugin_index.py` 同步为 1.3.0，两份逐字全等。
- `tests/test_editor_contract.py`：56 → 64 条（新增 `EditorAiAssistTest` 8 条；`EditorPanelTest.test_01`
  补 9 个 `epAi*` 节点、`test_02` 的 `<textarea` 禁令改为「只允许指令框一个，且禁 `ed-src-area`/`ed-box-area`」）。
- `tests/test_clean_latex.py`：`EditorAiCleanerTest` 两条 skip 清零并按辅助栏新契约重写（按钮位置、宿主通道、
  全成功才回填、`aria-busy`），另加清洗话术与 `renderAi` 忙态判据；`test_06` 的本地清洗取段改用 `fn_body()`
  （新增分段工具落在 `cleanExamSource` 之后，旧切片会把它一起扫进来打成假红）。
- `tests/test_command_registry.py`：EXPECTED 里 editor 版本 1.3.0（这张表按设计写死版本）。
- `tools/editor_probe.py`：45 → 65 项；新增 `StubProvider`（本机 OpenAI 兼容桩 + 4 个 `JZO_AI_*` 环境变量）、
  `wait_value()` / `wait_text()`；「辅助栏不放源码框」判据从 `textarea` 计数改为按 `.ed-src-area/.ed-box-area`
  类名判定（`#epAiAsk` 本身就是 textarea，旧判据会把合规的面板打成红字）。

## 本阶段未决 / 待主公复核
1. **探针：`editor_probe.py` 已跟上，`editor_crop_probe.py` 仍待裁**：前者阶段 2 重写为 v2 判据、阶段 3 加
   AI 判据后跑到 65/65；后者驱动的「原图框选切图」军令 #23 已明确本期不做，建议直接退役删除（要留可从 git 历史找回）——
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
8. **档 1 只按「整段」改写**：老师哪怕只选中题干里几个字，回填换掉的仍是整段题干正文
   （预览话术已写明「改写整段」）。要改成「只替换选中片段」得让宿主载荷多带一个选区偏移，
   属底座改动——请主公裁决是否留到下一军令。
9. **回显只能近似判定**：宿主摊平 `/api/agent/refine` 时把 `mock` 字段丢了（`stage.js:1157`），
   插件只能靠「新值与原文逐字相同」推断是回显，所以话术用「多半」。真要精确，得让宿主透传 `mock`。
10. **插件仓库 zip 尚未重打**：两份 `plugins.json` 已写 1.3.0，但 `E:/jiuzhang-plugins/plugins/org.jiuzhang.editor.zip`
    还是旧包；发版前要 `tools/build_plugin.py` 重打并核对两份索引全等（`dev/` 由 DENY_DIRS 排除，不进包）。
11. **清洗是「两段一起」**：`cleanViaHost()` 一次并发洗题干段与解析段，任一失败整题不动。
    若老师希望「只洗其中一段」，需要分段按钮——本期界面没做，等下一军令。

## 下次开工先读
1. 本文件
2. 本军令对应阶段条款
3. AGENTS.md §7

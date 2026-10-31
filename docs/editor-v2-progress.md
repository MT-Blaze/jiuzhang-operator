# editor 录题界面改造 · 进度记忆清单

军令 #23（2026-10-31 发令）· 改造对象 `plugins/org.jiuzhang.editor`，不新建插件。
本文件是跨阶段唯一记忆清单：每阶段开工前先读它 + 军令对应条款，读完把「当前阶段」改成「进行中」再动手。

## 当前阶段
- 阶段 1：已验收并提交（三栏骨架 + 单题静态渲染）
- 阶段 2：未开始（下一步）
- 阶段 3：未开始
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

## 本阶段未决 / 待主公复核
1. **真机探针还没跟上**：`tools/editor_probe.py` 与 `tools/editor_crop_probe.py` 驱动的是已删除的旧 DOM
   （`edStem` / `edSave` / `edPreview` / `edSourceCanvas`…），本次提交后它们必红。
   下一步：`editor_probe.py` 改写为 v2 三栏判据（三栏在场 / 拖不归零 / KaTeX 计数 / 右栏高度=内容高 /
   共滚动 / 0 控制台报错）；`editor_crop_probe.py` 对应的「原图框选切图」军令 #23 已明确本期不做，
   建议直接退役删除（要留可从 git 历史找回）——等主公点头再删。
2. **A4 判据消失**：旧 `tests` 里 794×1123 那组红线随「渲染不固定 A4」撤除，`paper-gen` / `handout`
   仍各自守 A4 几何，不受影响；如主公认为录题也该留一份分页证据，请裁决。
3. **`safeAssetUri` 放宽**：为让假数据的原图占位可渲染，新增放行 `/static/icons/`、`/static/assets/`
   两个底座本地前缀（仍禁远程 URL / `data:` / `file:`）。若认为过宽，阶段 2 收回到只认 `/static/uploads/`。
4. **假数据解析自相矛盾**：军令《格式宪法》示例的题干是 `$f(x)=x^2+1$`，解析却写「配方得
   $f(x)=(x-1)^2+1$」——两者不等价（答案 B 倒都成立）。当前逐字保留军令原文，等主公决定改题干还是改解析。
5. **`sidebar.right` 实例的分支已留但没铺内容**：阶段 1 只把清单留在 `["stage.center"]`，
   宿主右栏仍归 `org.jiuzhang.chat`；阶段 2 声明插槽后，同一插件会出现两个 iframe，
   届时按「架构口径」那四条通道对接，不要试图跨帧直接取 DOM。
6. **运行中的工作区仍显示 v0.6.1**：`app/core/config.py:93 plugins_dir()` 指向
   `data/workspaces/default/plugins/`，那是用户数据区，军令红线禁碰，所以本次没有覆盖它。
   主公回来看新界面的两条路：插件控制台里重装 / 更新，或用 `JZO_PLUGINS_DIR=E:\jiuzhang-operator\plugins`
   起一个开发实例（探针走的就是后者，不写用户目录）。

## 下次开工先读
1. 本文件
2. 本军令对应阶段条款
3. AGENTS.md §7

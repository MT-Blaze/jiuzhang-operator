# 施工进度（无人值守长任务）

记录四个阶段的完成情况与可复核证据。每阶段以「单测全绿 + check-quick-gate 通过 + 一次提交」收口。

## 阶段一：底座大瘦身与多用户空壳隔离（2026-11-05）

### 1. 彻底砍掉 AI 助手

- 物理删除 `plugins/org.jiuzhang.chat/`，两份 `plugins.json` 同步移除条目并保持逐字节一致。
- 宿主侧清除助手特权：`workspace.js` 不再认领助手插件；`ws_panel.js` / `ws_rail.js` /
  `context_panel.js` 不再有「归还助手」分支；`stage_relay_agent.js` / `stage_command.js`
  删除 `agent.chat` 转发与常驻对话历史。
- 后端删除 `/api/agent/chat`、`/split`、`/review` 与 `command_tools.py`、`plugin_tools.py`；
  `assistant.chat` 能力从清单白名单移除。保留 `/api/agent/refine`、`/clean_latex`
  ——录题插件的「AI 帮改」仍走 Host API 转发。
- 删除只服务于对话的测试与探针；改写边界测试，钉住「宿主壳不得直连 AI 后端」。

### 2. 右栏折叠策略

- 启动一律 `setCtx(false)`：没有插件占据就不展开。
- 只有「当前画布页签的插件声明了 `sidebar.right`」才自动展开；手动折叠是粘性的，
  `ctxTouched && !ctxUserWantsOpen` 阻止自动弹开；切走/关闭页签只收起自己自动打开的那一次。
- 移动端断点不自动展开。

### 3. 多用户空壳

- 左栏顶部改为【切换用户】卡片，打开用户弹窗（列表 / 新建）。
- 切换与新建复用 `POST /api/workspaces/switch`、`POST /api/workspaces` 的重启机制：
  全屏遮罩 + 轮询 `/healthz` 的 `boot_id` 变化后才重载，超时如实报错并给手动刷新。
- 新工作区绝对纯净：`ensure_workspace_layout` 只建空 `plugins/` 与空 `plugin_state.json`，
  不复制任何插件、题库或 `.env` 密钥；非 default 工作区建空库（0 题）。
- 该能力独立成 `static/js/ws_users.js` + `static/css/ws_users.css`，可整块移除。

### 验证证据

- `python tools/run_all_tests.py`：模块 84 个，用例 1641 个，失败模块 0 个。
- `bash scripts/check-quick-gate.sh`：PASS（6 项全过）。

## 阶段二：API 配置中心（2026-11-05）

### 入口与布局

- 批次列表右上角新增【API 配置】（`.ed-batches-head` 行布局，标题与说明归入 `.ed-batches-headtext`），
  点击直接打开同帧的双栏弹窗；辅助栏顶部原入口保留，两处都能进。
- 弹窗 `#epAiConfigModal` 住在画布帧：左栏密钥池（名称 / Base URL / API Key，Key 用 password 输入、
  列表只显示后端掩码），右栏四任务指派（视觉识别 OCR、解题、元数据、TikZ）。

### 数据与安全

- 后端 `app/core/ai_center.py`：非密钥字段落当前工作区 `config.json`，Key 只写工作区 `.env`
  与环境变量，读接口只回 `api_key_masked`。
- 每个任务可选账号 + 模型：支持【拉取模型】写入 datalist，也允许直接手填模型名后【保存指派】。
- 写接口与出网（拉模型）全部过 `X-JZO-Token`；插件只经宿主 `ai.*` 中继，不碰 localStorage、不直连网络。

### 验证证据

- `python tools/run_all_tests.py`：模块 84 个，用例 1642 个，失败模块 0 个。
- `bash scripts/check-quick-gate.sh`：PASS（6 项全过）。

## 阶段三：AI 识别与解析闭环（2026-11-05）

### 单题与批量入口

- 渲染区只读条右侧两组按钮：【✨ AI 识别本题】（视觉 OCR）与【✨ 解析本题】（解题档）；
  解析不需要题图，题干来自当前源码，题干与选项原样保留，只补答案与解析。
- 辅助栏底部新增【✨ 批量解析全卷】，与【✨ 批量 AI 识别全卷】并列；发令走
  `editor.batch_review` 的 `ai_batch_solve` 分支。

### 防连点与静默保存

- 单题按钮点击即 `disabled + aria-busy`；批量按钮点击即变灰，画布回执 done 后才恢复。
- 识别/解析成功后调用 `stashQuietly()`：按当前题解析源码 + 元数据组卷，直接
  `pending.save_draft` 写入待审池；成功后清掉脏标记，失败如实提示并进报错诊断。

### 通知

- Toast 移到右下角：成功 3s、失败 8s；鼠标悬停暂停倒计时，本身没有任何点击行为。
- 批量任务只弹一枚总气泡（成功 / 跳过 / 失败计数），逐题失败详情只进报错诊断。
- 宿主中继 `ai.recognize` 接受 `task=solve`：只有 ocr 强制题图，解析不再被题图卡住。

### 验证证据

- `python tools/run_all_tests.py`：模块 84 个，用例 1655 个，失败模块 0 个。
- `bash scripts/check-quick-gate.sh`：PASS（6 项全过）。

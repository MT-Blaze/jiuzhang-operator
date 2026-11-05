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

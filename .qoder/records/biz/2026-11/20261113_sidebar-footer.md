# 侧边栏底部栏与工作区管理浮层 · 真机回传单（2026-11-13）

## 改动清单

- `static/workspace.html`：删除顶部「当前用户 / 默认工作区 / 切换」大块；底部固定 footer，
  左侧工作区名 + 首字头像（过长省略号），右侧切换图标 + 齿轮；
  新 Modal 三段式（切换 / 新建 / 重命名）。
- `static/js/ws_users.js`：工作区名绘制、列表渲染、新建、切换（boot_id 轮询 + 遮罩）、
  重命名；保留焦点陷阱 / Esc / 点遮罩关闭。
- `static/css/ws_users.css`：footer 与 Modal 全部样式，44px 热区，420px 以下纵向堆叠。
- `app/api/workspace_rename.py`（新增）：`POST /api/workspaces/rename`，写令牌鉴权，
  名称 1–40 字，只改显示名不建目录不重启。
- `app/api/workspaces.py`：抽出重命名端点后回到 494 行（500 行红线内）。
- `static/js/workspace.js` + `static/css/workspace_overlay.css`：齿轮角标改为小圆点数字，
  不再占满整行。
- 测试：`tests/test_workspace_sidebar.py`、`tests/test_splitpane_layout.py` 改锚点，
  新增 `tests/test_workspace_rename.py`（6 例）。

## 真机数据（视口内容宽 349px ≈ 375px 窄屏）

| 项 | 值 |
| --- | --- |
| footer 宽度 | 279px |
| footer 横向溢出 | 0 |
| body 横向溢出 | 0 |
| 工作区按钮热区 | 165 × 44 |
| 切换图标热区 | 44 × 44 |
| 齿轮热区 | 44 × 44 |

- 重命名「默认工作区」→「高一数学」：footer 与头像即时更新（高），`workspaces.toml` 落盘；
- 新建「高二备课」：创建后自动切换为当前并刷新；
- 切回默认：页面重载后 footer 显示「高一数学」；
- 齿轮：打开「设置与控制台」tab，iframe `src=/settings?embedded=1`。

截图：`20261113_sidebar-footer/desktop.png`、`20261113_sidebar-footer/narrow-sidebar.png`、
`20261113_sidebar-footer/narrow-modal.png`。

## 门禁

- `tools/run_all_tests.py`：模块 106 个，用例 2023 个，失败模块 0 个。
- `scripts/check-quick-gate.sh`：PASS（6 项全过）。
- `tools/audit_code.py`：ERROR 0 · WARN 34 · INFO 3。

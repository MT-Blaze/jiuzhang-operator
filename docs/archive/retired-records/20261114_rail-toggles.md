# 侧栏开合图标化：钉在页签栏两端 · 真机回传单（2026-11-14）

## 改动清单

- `static/workspace.html`：页签栏外包一层 `.ws-tabs-wrap`，两端各钉一枚 44×44 图标钮
  `#wsOpenSidebar`（方块带左竖线）与 `#wsOpenCtx`（镜像方块带右竖线）；
  两钮常驻可见，`aria-controls` 分别指向 `#wsSidebar` / `#wsContext`；
  删除中栏头部「入口」「辅助栏」两处纯文字开关；资源版本统一升到 `v=20261114`。
- `static/css/workspace.css`：删旧的页签形 `.ws-drawer-btn` / `.ws-ctx-btn` 规则，
  换 `.ws-rail-toggle`——透明底、8px 圆角、`flex: none`、44×44 热区，
  hover/focus 用 `::after` + `data-tip` 在按钮下方浮出黑底提示气泡（右钮右对齐）。
- `static/css/workspace_canvas.css`：`.ws-tabs-wrap` 左内距 12→8px；`.ws-tabs` 改
  `flex: 1 1 auto`，页签在中间自己横向滚动，右钮被顶到贴右端。
- `static/css/workspace_controls.css`：新增侧栏折叠动画——`.ws-page` 的
  `grid-template-columns` 200ms 插值；`[data-resizing]` 时 `transition: none`，
  拖拽调宽手感不变。
- `static/css/workspace_overlay.css`：`prefers-reduced-motion` 块补 `.ws-page`、
  `.ws-rail-toggle`、`.ws-rail-toggle::after`，减动效下近乎瞬切。
- `static/js/ws_rail.js`：`setSide` / `setCtx` 各自调 `paintRailButton`，同步
  `aria-expanded`、`aria-label`、`data-tip` 的「隐藏 / 显示」措辞；右钮点击从
  「只见收起」改成双向 `manualCtx(!ctxOpen())`。
- 测试：`test_stage_canvas` 的 `test_05` 改为断言图标开关（无「入口/辅助栏」文字、
  44px、`flex:none`）；`test_workspace_fold_state` 重写 `ReopenEntryTest`（两钮在
  `.ws-tabs-wrap`、永远 inline-flex、热区分层、两态文案同步、无快捷键）并新增
  `test_08` 动画契约；`test_file_size_contract` 摘掉 `workspace.css: 504` 的旧账。

## 真机数据（CDP 驱动 Edge，127.0.0.1:65496/workspace）

桌面 1440×900：

| 项 | 值 |
| --- | --- |
| 两钮热区 | 44×44（左 x=8、右贴右端） |
| 初始 | side=open · ctx=open · 中栏 890px |
| 点左钮隐藏侧栏 | 中栏 890 → 1135px，左钮提示「显示侧边栏」 |
| 再点左钮 | 中栏回到 890px，提示「隐藏侧边栏」 |
| 点右钮收起辅助栏 | 中栏 890 → 1195px |
| 再点右钮 | 中栏回到 890px |
| 提示气泡 | hover 时 opacity=1；左钮气泡在按钮下方左对齐，右钮右对齐 |
| 快捷键 | HTML/JS 无 `aria-keyshortcuts`，无 `Ctrl+B` / `Ctrl+J` 字样 |
| 页面横向溢出 | 0px |

动画（`getComputedStyle` + 逐帧采样）：

| 项 | 值 |
| --- | --- |
| `transitionProperty` | `grid-template-columns` |
| `transitionDuration` | `0.2s` |
| 展开采样（中栏宽） | 890 → 944 → 1031 → 1104 → 1131 → 1135 |
| 拖拽中 | `.ws-page[data-resizing]` 的 duration = `0s` |
| 减动效 | duration = `1e-06s` |

窄屏 375×812：

| 项 | 值 |
| --- | --- |
| 默认 | side/ctx 收为抽屉，中栏 375px，两钮 44×44（x=8 / x=331） |
| 页面横向溢出 | 0px |
| 抽屉展开态 | 左钮按既有移动端规则让位隐藏，栏内「折叠」钮（51×44）仍在 |

截图：`20261114_rail-toggles/desktop-tooltip-left.png`、`desktop-side-hidden.png`、
`desktop-ctx-closed.png`、`desktop-tooltip-right.png`、`narrow-default.png`、`narrow-drawer.png`。

## 门禁

- `scripts/check-quick-gate.sh`：PASS（6 项全过）。
- `tools/run_all_tests.py`：模块 106 个，用例 2025 个，失败模块 0 个。

## 未决问题与偏离

- 按用户更正，键盘快捷键整体撤销：不加 `Ctrl+B` / `Ctrl+J`，提示气泡也不提快捷键，
  只保留图标点击与 hover 提示；测试已反锚定其缺席。
- 移动端抽屉展开时左钮隐藏是既有 CSS 行为（抽屉本身要靠栏内折叠钮收回），本次未改；
  如需常驻可与后续移动端改版一并处理。
- 本机 uvicorn 一度无响应（`/healthz` 超时），用 `start.bat --stop` 后重启，
  新 `boot_id=5bb76b2e1dfb4b9cb5c55be99473b382`；证据全部采自重启后实例。
- 证据脚本在 `.system_generated/footer-strip/`（`rail.mjs`、`tip.mjs`、`anim.mjs` 等），
  随 `.system_generated/` 忽略，不入库。

# 侧栏头「折叠」文字钮下线 · 真机回传单（2026-11-14）

## 改动清单

- `static/workspace.html`：删除左栏 `#wsToggleSidebar`、右栏 `#wsToggleCtx` 两枚文字折叠钮；
  栏头只留标题（左「插件」、右「辅助栏」/插件标题与徽标）；同步清理相关注释；
  `workspace.js` 资源版本升到 `v=20261114`。
- `static/js/workspace.js`：去掉两个文字钮的 DOM 引用与 `JzoWsRail.create` 入参。
- `static/js/ws_rail.js`：`setSide` / `setCtx` 不再回写文字钮 `aria-expanded` 与
  「折叠 / 展开」文案；删除两枚文字钮的 click 监听；开合只保留页签栏两端图标。
- `static/css/workspace.css`：更新两处围绕文字折叠钮的过时注释；48px 栏头定高不变。
- `static/css/workspace_overlay.css`：删除「抽屉展开时隐藏两端图标」的旧规则
  （栏内已无第二枚折叠钮，再藏就收不回来）；窄屏把 `.ws-rail-toggle` 提到
  `z-index: 120` 压在抽屉（110）之上，并给抽屉抬头留 56px 图标位。
- 测试：`test_workspace_fold_state` 反锚定两个旧 id 的缺席、`setSide`/`setCtx` 不再写文案，
  新增窄屏「图标压抽屉、抬头留位」契约；`test_stage_canvas` 与 `test_stage_tab_group`
  同步收口；`fold_probe` / `stage_probe` / `tab_group_probe` 改点 `#wsOpenSidebar`，
  `stage_probe` 的「入口与页签同形」旧判据换成图标 44×44/无文字/旧钮缺席。

## 真机数据（CDP 驱动 Edge，127.0.0.1:65496/workspace）

桌面 1440×900：

| 项 | 值 |
| --- | --- |
| 旧文字钮 | `#wsToggleSidebar` / `#wsToggleCtx` 均不在 DOM |
| 左右栏头按钮数 | 0 / 0 |
| 两端图标 | 44×44，`elementFromPoint` 命中自身 |
| 基线（左开右收） | 中栏 x=245、宽 1195 |
| 点左图标收起 | 中栏 x=0、宽 1440（画布铺满） |
| 再点左图标 | 中栏回到 x=245、宽 1195 |
| 点右图标展开 | 中栏宽 890；再点收回 1195 |
| 页面横向溢出 | 0px |

窄屏 375×812：

| 项 | 值 |
| --- | --- |
| 初始 | 左右抽屉均收起，中栏 375px，横向溢出 0px |
| 左图标展开抽屉 | `data-side=open`，图标仍命中 `wsOpenSidebar`（压抽屉），抬头 `padding-left:56px` |
| 再点左图标 | 抽屉收回 |
| 右图标展开辅助栏 | `data-ctx=open`，图标仍命中 `wsOpenCtx`，抬头 `padding-right:56px` |
| 再点右图标 | 辅助栏收回 |

截图与原始度量：`20261114_sidebar-text-toggle-removal/` 下
`desktop-baseline.png`、`desktop-side-hidden.png`、`narrow-side-open.png`、
`narrow-ctx-open.png`、`verify.json`。

## 门禁与回归

- `scripts/check-quick-gate.sh`：PASS（6 项全过，审计 ERROR 0）。
- `tools/run_all_tests.py`：模块 106 个，用例 2026 个，失败模块 0 个（全绿）。
- 真机判据：15/15 PASS，pageerror 0。

## 未决问题与偏离

- 本轮只删左右侧栏头文字钮；输出日志区（底栏）的「折叠 / 展开」属于另一区，
  按需求范围保留。
- 窄屏需新增图标提层与抬头留位：否则抽屉展开后会盖住唯一开合图标，形成「打不开也关不上」；
  该调整仅窄屏生效，桌面布局不变。
- 证据脚本与浏览器 profile 在 `.system_generated/sidebar-text-toggle-removal/`，
  按仓库约定不入库；入库副本只保留截图与 `verify.json`。
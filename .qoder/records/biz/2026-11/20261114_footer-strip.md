# 底栏瘦身：工作区名 + 齿轮 · 真机回传单（2026-11-14）

## 改动清单

- `static/workspace.html`：删除工作区胶囊里的上箭头 SVG；删除栏底右侧【切换工作区】图标及其按钮节点；
  栏底只剩 `#wsWorkspaceBtn`（首字头像 + 工作区名）与 `#wsConsoleBtn`（设置齿轮）；
  `ws_users.css` / `ws_users.js` 缓存参数升到 `v=20261114`。
- `static/css/ws_users.css`：删 `.ws-ws-chevron`、`.ws-foot-actions` 两条失效规则；
  `.ws-foot-btn` 补 `flex: none`，齿轮直接成为 footer 的第二个 flex 子项。
- `static/js/ws_users.js`：删 `switchBtn` 取节点与点击绑定；切工作区只走工作区名弹窗。
- `tests/test_workspace_sidebar.py`、`tests/test_splitpane_layout.py`：反锚定——
  断言两个已删节点不再出现、栏底可点目标恰好两个，名称与齿轮仍死锁在栏底。
- `.qoder/records/biz/2026-11/20261113_sidebar-footer.md`：上一张回传单从
  `20261113_sidebar-footer/receipt.md` 上移为合规文件名（R00 门禁红项），截图仍留在同名目录。

## 真机数据（CDP 驱动 Edge，127.0.0.1:65496/workspace）

窄屏 375×812（抽屉态）：

| 项 | 值 |
| --- | --- |
| 栏底可点目标 | `["wsWorkspaceBtn", "wsConsoleBtn"]` |
| 上箭头 / 切换图标 | `chevron: false` · `switchBtn: false` |
| 栏底盒 | x=0 · y=751 · 279×61 |
| 齿轮热区 | 44×44（x=225, y=760） |
| 页面横向溢出 | 0px |
| 点工作区名 | 弹窗打开，含「切换工作区 / 数学（当前）/ 物理 / 切换 / 新建工作区 / 重命名当前工作区」 |
| Esc | 弹窗关闭 |
| 点齿轮 | 画布新增/切到「设置与控制台」页签，iframe `src=/settings?embedded=1` |

桌面 1440×900：栏底同样只有 `wsWorkspaceBtn` + `wsConsoleBtn`，盒 239×61。

截图：`20261114_footer-strip/narrow-footer.png`、`narrow-modal.png`、`narrow-console.png`、`desktop-footer.png`。
`pixel_scan.py narrow-footer.png`：y=450/700 行 `P[0-278]` 连续纸色，280px 后为画布卡色，
说明栏底通宽无断裂，也没有第三枚图标占据行段。

## 门禁

- `scripts/check-quick-gate.sh`：PASS（6 项全过）。
- `tools/run_all_tests.py`：模块 106 个，用例 2023 个，失败模块 0 个。

## 未决问题与偏离

- 上一张回传单的文件名不合 R00（`.../receipt.md`），本次顺手上移修复；截图目录名未动。
- `tools/workspace_ui_probe.py`、`tools/fold_probe.py` 不引用被删的切换图标，无需改动；
  本次真机证据用 CDP 脚本产出（`.system_generated/footer-strip/shot.mjs`，随 `.system_generated/` 忽略）。

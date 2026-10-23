# Morning Report · 军令 #13「彻夜模块化全自动生态与旧库移植」

日期：2026-10-24（Asia/Shanghai）
执行方式：彻夜静默连轴转，逐任务 commit；本轮最后统一 `git push`。
版本状态：**仍为 0.8.2，未升版、未出包、未发布 Release**（本轮只做代码与验证）。

---

## 一、任务完成

四大模块、11 个任务全部交付。任务 1 沿用 #11 第三阶段成果，未重复改动；其余逐项独立提交。

| # | 交付 | 提交 | 关键证据 |
|---|---|---|---|
| 1 | 启动行为：老师可选开机落在工作台/设置 | `882e56b`（#11 第三阶段） | 单测 `test_startup_prefs` 32/32 |
| 2 | 左栏 48px 顶线、三视图底栏、插件拖拽排序 | `511bd1e` | `tools/workspace_ui_probe.py` 20/20 |
| 3 | 右栏 `sidebar.right` 动态插槽与插件化契约 | `38031b0` | 真机探针 12/12（`sidebar-slot-probe/task3b`），PLUGIN_SPEC §2.9 |
| 4 | `question_parser` 录题清洗与解析地基 | `22b350f` | 单测 34/34 |
| 5 | FTS5 中文检索预研 | `bee3d61` | 单测 16/16；万题压测 p50 0.12ms |
| 6 | `org.jiuzhang.exam-paper` 组卷排版与答题卡 | `1bdaba1` | 单测 26/26；真机 23/23 |
| 7 | `org.jiuzhang.lecture` 讲义工作台 | `db250b7` | 单测 24/24；真机 24/24 |
| 8 | `org.jiuzhang.bank-browser` 浏览与编辑跳转 | `7041728` | 单测 27/27；真机 22/22 |
| 9 | editor 三栏对比 + Canvas 框选切图 | `54d40c1` | 单测 25/25；真机 16/16 |
| 10 | 双轨更新运行时 + 真机探针 + 文档对齐 | `b40e816` | 探针 21/21；全量 752 测绿 |
| 11 | 死代码/过期样式清理、晨报、统一推送 | 本次 commit | 全量 749 测绿；样式回归 13/13 |

任务 10 顺带修复一个真缺陷：`update.bat` 的 `robocopy /XD` 传目标绝对路径在「阶段→根」方向不生效，
`data/`、`.git/`、`dist/`、`.system_generated/` 会被新包覆盖。改为只写目录名，并在单测中加反向断言锁死。
这是沙箱真跑抓出来的，不是推断。

---

## 二、移植纪要

军令中的「移植旧库」一律按**能力对齐**执行，遵守 AGENTS 铁律一：

- 未从 `E:\math-question-bank-main`、`E:\math-question-bank` 或任何历史目录复制源码、样式、模板、注释、测试或目录结构。
- 只参考公开标准（JSON Schema、HTTP、A4 纸面尺寸、Markdown/LaTeX）与 `schemas/question.json`、`PLUGIN_SPEC.md` 的契约。
- 任务 4 的字面要求是「从旧库提取」，与铁律一冲突；按铁律一改为从契约独立实现，偏离已在当时回传单登记。

要点：

- **录题解析（任务 4）**：LaTeX 定界符/等价记号归一、选项剥离、填空答案提取、题干体检；纯函数地基。
- **组卷（任务 6）**：按题型分卷一/二/三/四，「日常小练」与「标准答题卡」两套 A4；隐藏测量台分页，超页整题顺延。
- **讲义（任务 7）**：题篮按考向归堆，三块（知识点/方法/易错点）逐条编辑与原生预览；草稿宿主代持。
- **题库浏览（任务 8）**：左树懒展开、按子树筛题、跨当前活跃题库搜索；编辑只发 `system.open_editor` 意图，插件不直连。
- **框选切图（任务 9）**：原生 Canvas 框选 → `asset.upload`（PNG/JPEG/WebP、魔数校验、≤8 MiB、原子替换）→ `\includegraphics{路径}`。
- **双轨更新（任务 10）**：插件热更只覆盖 `plugins/<id>/`，绝不触碰 `data/`；底座自更新走一次性 `update.bat`，
  保护 `data/`、`.venv/`、`.git/`；开发工作树拒绝覆盖与重启。

---

## 三、瘦身数据

本轮 10 个文件：**+18 行 / −365 行**（`git diff HEAD --shortstat`）。

| 文件 | 清理前 | 清理后 | 净变化 |
|---|---|---|---|
| `app/core/seed_plugin.py` | 55 行 / 1,882 B | 删除 | −55 行 / −1,882 B |
| `static/css/questions.css` | 259 行 / 4,171 B | 106 行 / 1,851 B | −153 行 / −2,320 B |
| `static/css/workspace.css` | 1,667 行 / 36,062 B | 1,584 行 / 34,500 B | −83 行 / −1,562 B |
| `static/css/settings.css` | 463 行 / 10,354 B | 461 行 / 10,261 B | −2 行 / −93 B |
| `tests/test_seed_plugin.py` → `test_routes_and_demo_zip.py` | 176 行 / 7,218 B | 132 行 / 5,285 B | −44 行 / −1,933 B |
| 其余（PLUGIN_SPEC / README / tools / 折叠测试） | — | — | −10 行 |

删除的 26 个死 CSS 类：

- **questions.css**：旧题库列表页的 `questions-main`、`q-head`、`q-lede`、`q-toolbar`、`q-field-small`、
  `q-renderer-note`、`q-state`、`q-list`、`qcard`、`fallback-card/meta/stem/note`、`pager`、`pager-info`、`plugin-runtime`；
- **workspace.css**：已删模型胶囊/弹窗/提示留下的 `ws-chip`、`ws-chip-dot`、`ws-btn-block`、`ws-btn-icon`、
  `ws-provider-hint`、`ws-provider-test-result`、`ws-dock-tag`；
- **settings.css**：已删导入区与页头页脚留下的 `st-import`、`site-head`、`site-foot`。

判定口径：历史提交证明对应 DOM 已删除（如 `511bd1e` 删模型胶囊、`9734ba2` 删 Provider 弹窗、`ad2fd30` 删题库列表页），
且全仓 HTML/JS 与插件内均无引用；`ws-msg-sys`/`ws-msg-user` 是动态拼接、`katex-display` 由 KaTeX 运行时生成，均保留。

**未删任何安全检查**：路径守卫、zip 安检、令牌校验、HTML 净化、`/XD` 排除逻辑原样保留；
`LICENSE`、AGENTS 铁律一/二、用户 `data/` 均未触碰。`tools/audit_code.py` 结果仍为 **ERROR 0 · WARN 33 · INFO 3**，
33 条 WARN 逐条看过，均为固定标识符 SQL 与已净化的 `innerHTML`，属既有已知项。

退役说明：`seed_plugin` 自 v0.8.0 起已无调用方（lifespan 不再自动装 demo-bank）。本轮删除模块与安装测例，
PLUGIN_SPEC 改为「种子插件首启静默安装已退役」，README 同步；`examples/demo_plugin.zip` 仅作示例/测试夹具保留。

---

## 四、测试结果

解释器：`.venv/Scripts/python.exe`（系统 Python 缺依赖，不用）。

全量逐模块（`tests/test_*.py`）：

```
MODULES=39 TESTS=749 FAILED=0
```

所有 39 个模块均 `OK`。测试数较上轮 752 少 3，恰为退役的 3 条种子安装测例；
同文件中的默认路由测试与 demo_plugin.zip 契约测试全部保留，模块改名为 `tests.test_routes_and_demo_zip`（11/11）。

真机回归（本轮 CSS 改动）：

```
.system_generated/task11_css_probe/probe.json   RESULT 13/13
```

覆盖 `/workspace`、`/settings`、`/plugins` 三页：桌面截图、375px 截图、零控制台错误、零未捕获异常、
`scrollWidth ≤ 375`；另验 `.q-field` 仍存在、`.q-button` 仍 ≥44px。截图在 `.system_generated/task11_css_probe/shots/`。

历史任务证据（未重跑，沿用当时落盘）：

- 更新探针 21/21：`.system_generated/update_probe/task10h/probe.json`
- 框选切图 16/16：`.system_generated/editor_crop_probe/task9c/probe.json`
- 组卷 23/23：`.system_generated/exam-paper-probe/task6/probe.json`
- 讲义 24/24：`.system_generated/lecture-probe/task7/probe.json`
- 题库浏览 22/22：`.system_generated/bank-browser-probe/task8/probe.json`
- 右栏插槽 12/12：`.system_generated/sidebar-slot-probe/task3b/probe.json`
- 工作台 UI 20/20：`.system_generated/workspace-ui-probe/task2/probe.json`（任务 2 轮次）

---

## 五、未解决坑

1. **任务 4/5 仍是地基，未接生产路径**：`question_parser` 尚未接入录题插件写入链路；`bank_fts` 尚未替换题库搜索（当前仍走 LIKE）。
   两者均有单测，但“可用”不等于“已接线”，已在任务 4/5 回传单登记。
2. **底座自更新未在真实安装版上做过整包替换**：探针用合成 host zip 验证了校验、暂存、`update.bat` 沙箱行为与开发工作树拒绝；
   真实安装目录的覆盖与重启会结束本进程，只能由人亲手点，未自动验证。`data/`、`.venv/`、`.git/` 保护已在沙箱实测。
3. **版本与发布**：版本仍 0.8.2，本轮未运行 `build_release.bat`、未生成发行包、未发布 Release。按军令只做最后一次统一 `git push`。
4. **v0.8.2 旧欠账仍在**：控制台内部「左树右二级菜单」、工作台顶栏 Provider 配置弹窗迁移、大纲树按教材版本过滤，均未在本轮处理。
5. **一处既有样式遮蔽**：`questions.css` 的 600px 媒体查询里 `.q-field { flex: 1 1 100% }` 在设置页被后加载的 `settings.css`
   覆盖为 `0 0 auto`。这是本轮之前就存在的状态，不是清理引入；因三页均无横向溢出，未改动以免扩大范围。
6. **示例包仍随仓**：`examples/demo_plugin.zip` 作为测试夹具保留；若未来要求发行包更瘦，可评估只保留构建脚本、运行时再生成。

# 查重 UI 交付回执

【回执时间】 2026-11-06（无人值守长任务）
【提交】 `484c971`（main，已推送 origin）
【执行结果】 完成：单测全绿、快门禁 PASS、真机探针 7/7
【采集方式】 数字全部来自当次实测输出，截图与机器可读结果同时落盘

## 【改动清单】

### 新增

| 文件 | 行数 | 职责 |
| --- | --- | --- |
| `plugins/org.jiuzhang.editor/dist/ui_dup_compare.js` | 221 | 第四模式 `compare`：三栏变身、原图淡出、第三栏滑出、源码/渲染/原题绘制 |
| `plugins/org.jiuzhang.editor/dist/ui_dup_judge.js` | 399 | 裁判台展示层：差异清单、二选一冲突弹窗、四件套按钮状态 |
| `plugins/org.jiuzhang.editor/dist/ui_dup_judge_flow.js` | 138 | 裁决动作层：`run/act/confirmDelete/advance/busyNow`，错误码兜底 |
| `plugins/org.jiuzhang.editor/dist/ui_dup_wiring.js` | 41 | compare/judge 装配，规避 `plugin.js` 创建顺序问题 |
| `plugins/org.jiuzhang.editor/dist/dup_compare.css` | 299 | 三栏网格、横滑动画、裁判台整栏变脸、44px 按钮、reduced-motion |
| `app/core/pool_meta.py` | 131 | 纯计算差异账：`source_view/source_key/meta_value/meta_diff/resolutions` |
| `tools/dup_compare_probe.py` | 482 | Playwright 真机探针（隔离端口/数据目录，真实鼠标点击与像素量测） |

### 修改

- `app/core/pending_pool.py`
  - L164 `get_entry` 增加 `meta_diff`；
  - L475 `merge_metadata(..., resolutions=None)`，L492 冲突未决抛 `PoolActionRefused(code="meta_conflict")`；
  - L669 `act(..., resolutions=None)` 把二选一透传给合并；
  - 内联差异常量删除，改为从 `app/core/pool_meta.py` 导入。
- `app/api/pending.py`：`pending_pool_act` 把 `resolutions` 传入 `pending_pool.act`，409 文案补 `meta_conflict`。
- `app/core/plugins.py`：`_BUS_PUBLISH` / `_BUS_SUBSCRIBE` 均加入 `editor.dup_compare`。
- `static/js/core_bus.js`：`PUBLISH_ALLOW` 加入 `editor.dup_compare`。
- `static/js/stage.js` L592：`bus.on("editor.dup_compare")` 按 panel/canvas 来源转发。
- `static/js/stage_relay_io.js`：新增 `poolResolutions()`，`pending.pool_act` 请求体带 `resolutions`。
- `plugins/org.jiuzhang.editor/plugin.json`：`bus.subscribe/publish` 均加入 `editor.dup_compare`。
- `plugins/org.jiuzhang.editor/dist/index.html`：引入 `dup_compare.css` 与四支新脚本（`ui_dup_compare` → `flow` → `judge` → `wiring`）；新增 `#edPaneOriginal`、`#edCmpSource` 等三栏与裁判台 DOM。
- `plugins/org.jiuzhang.editor/dist/core_protocol.js` L171：`editor.dup_compare` 的 open/update/closed 路由与 `onDupCompareClosed()`。
- `plugins/org.jiuzhang.editor/dist/ui_batches.js`：`setMode` 支持 `compare`，`#edCols` 在 review/compare 之外的显隐口径。
- `plugins/org.jiuzhang.editor/dist/ui_columns.js` L522/L567：`renderAll/refreshRow` 在 `compare` 模式早退，保证渲染冻结。
- `plugins/org.jiuzhang.editor/dist/ui_dom.js` L139：接线 `#epPoolCompare` 入口。
- `plugins/org.jiuzhang.editor/dist/ui_panel_boot.js`：裁判台开关 `data-judge`。
- `plugins/org.jiuzhang.editor/dist/ui_pool_panel.js` L412-L436：`setCompareActive/setSelectionListener/setPoolStateListener`，对比模式不再推旧两栏屏、不擅自收窗。
- `plugins/org.jiuzhang.editor/dist/plugin.js` L117-L125：装配 `uiDupWiring`；`__jzoEditorV2` 暴露 `uiDupCompare/uiDupJudge`（799 行）。
- `plugins/org.jiuzhang.editor/dist/dev_probe_api.js`：探针面新增 `uiDupCompare/uiDupJudge`，不参与业务分支。
- `tests/test_pending_pool.py`、`tests/test_plugin_bus_parity.py`、`tests/test_editor_contract.py`：新契约、新总线话题、四栏结构与渲染冻结断言。
- `docs/PROGRESS.md`：追加“阶段五：查重 UI 三栏变身与裁判台”。

### 禁改区自查

未触碰 `LICENSE`、`AGENTS.md` 铁律一/二、`schemas/` 破坏性变更、用户 `data/` 内容；本次只读运行态工作区用于同步。

## 【包结构自检】

- 顶层目录名 `org.jiuzhang.editor` == `plugin.json.id`。
- `backend` 字段不存在；插件 `LICENSE` 为 Apache-2.0 全文。
- `plugin.json.version = 2.12.0`；`min_host_version = 1.0.0`，当前底座 `app.__version__ = 1.1.0`（满足 ≥）。
- 新增前端文件均在 `dist/` 下，随插件整包分发；无新增宿主依赖。

## 【三查结果】

```
grep -rn "fetch(\|parent\.document\|localStorage" plugins/org.jiuzhang.editor/dist --include=*.js --include=*.html --include=*.css
→ 0 命中
```

新增请求仅 `pending.pool_act`（`ui_dup_judge_flow.js:66`）与既有 `pending.pool_get/pending.list`，均符合
`^[A-Za-z0-9_-]{1,80}$` 且不含点号之外的非法字符（命名空间分隔点由宿主请求族解析，非请求 id）。

## 【测试与探针】

解释器：`.venv/Scripts/python.exe`

1. 目标单测：`tests.test_pending_pool tests.test_plugin_bus_parity tests.test_editor_contract tests.test_file_size_contract`
   → `Ran 214 tests ... OK`
2. 全量回归：`tools/run_all_tests.py`
   → 模块 89 个，用例 1750 个，失败模块 0 个（全绿）
3. 快门禁：`bash scripts/check-quick-gate.sh`
   → `check-quick-gate: PASS（6 项全过）`（ERROR 0）
4. 真机探针：`tools/dup_compare_probe.py dc9`
   → 7/7 通过：
   - 造现场：主库 2 道原题，重题批自动抽 2 条进池；
   - 任务一：`mode=compare`、原图栏 `hidden` 且 0 宽、第三栏宽 267、源码栏宽 267；
   - 任务二：辅助栏 `data-judge=on`、审核表单让位、只列差异 chips、四个按钮齐；
   - 任务三：【不重复】后池内 2→1，当前 `pool_id` 与源码文本都变了，仍处 `compare`；
   - 渲染冻结：`#edRenderBody` / `#edCmpIncoming` 节点身份保持不变，容器移除计数 0；
   - 全程零 `pageerror` / 零 console error。

证据目录：`.qoder/records/biz/2026-11/20261106_dup-compare-evidence/`
（`dc9-result.json`、`dc9-01-compare-canvas.png`、`dc9-01-compare-panel.png`、
`dc9-02-after-decision.png`、`dc9-02-after-decision-panel.png`；dc1-dc8 排查轮次的中间产物已清理。）

前端改动已在真浏览器走完“入口点击 → 三栏变身 → 裁决 → 自动下一题”的完整用户路径，非仅静态检查。

## 【未决问题与偏离】

1. ~~左栏【新题源码】可编辑但未回写池内~~ —— 已于同日补漏（见下节「源码回写补漏」），
   现在 500ms 防抖静默保存 + 裁决前跨帧强保存，两处均有真机证据。
2. `compare` 模式下 `renderAll/refreshRow` 主动早退，这是渲染冻结的既定代价：对比期间其它订阅式刷新
   不会重排画布；退出对比后回到 `pool` 屏仍走原刷新链路。
3. 探针的“当前题已换”同时以 `pool_id` 与源码文本变化判定；`window.__jzoEditorV2` 已补齐
   `uiDupCompare/uiDupJudge`，此前 dc6-dc8 的 `current=null` 是探针面漏暴露，不是业务分支问题。
4. 未做真机发版包（`build-release`）；本轮交付按源码工作树验收，运行态工作区在提交后已强制同步。

---

# 源码回写补漏回执（2026-11-06 补）

【问题】左栏【新题源码】可编辑但未回写池：老师改完代码直接点裁决，改动丢失。
【方案】A + B 双保险：输入停止 500ms 静默保存；点【合并】/【不重复】/【删除】/【新增解析】前强制保存，
存不进去就拦下裁决，一题都不动库。

## 【七跳落点】

| 跳 | 位置 | 说明 |
| --- | --- | --- |
| 插件发令 | `ui_dup_compare.js:131` | `hostCall("pending.pool_save", {pool_id, patch})`；`sourceToPatch` 把 exam-zh 源码转题面四件 |
| 输入触发 | `ui_dup_compare.js:185` | `input` → `data-dirty=true`，500ms 防抖后 `saveNow()` |
| 强保存握手 | `ui_dup_judge.js:209` | 裁判台发 `editor.dup_compare {phase:"save_request", requestId}`，4s 无回执即拦下 |
| 画布执行 | `ui_dup_wiring.js:42` | 画布帧 `compare.saveNow()` 落盘后回 `phase:"save_done"` |
| 协议路由 | `core_protocol.js:184-188` | 画布帧接 `save_request`，辅助栏帧接 `save_done` |
| 宿主白名单 | `stage_command.js:54`、`stage_relay_io.js:392` | 登记 `pending.pool_save`，要 `questions:write`，校验 pool_id/补丁体积 |
| 底座 | `app/api/pending.py:401`、`app/core/pool_source.py:105` | `POST /api/pending/pool/{pool_id}/doc`，写入令牌 + 字段白名单 |
| 存储 | `pool_source.py:105` | 只改 `type/stem/options/answer/solution`；越权字段 400，不静默丢弃 |

`pending_pool.py` 从 932 行瘦到 774 行（源码回写整块移入 `pool_source.py` 173 行），
`plugin.js` 796 行，均在 800 行舱位线以内。

## 【测试与探针】

1. 目标单测：`tests.test_pending_pool`（43）· `tests.test_pending_api`（35）· `tests.test_editor_contract`（164）· `tests.test_file_size_contract` → OK
2. 全量回归：`tools/run_all_tests.py` → 模块 89 个，用例 1756 个，失败模块 0 个（全绿）
3. 快门禁：`bash scripts/check-quick-gate.sh` → PASS（6 项全过，ERROR 0）
4. 真机探针：`tools/dup_compare_probe.py dc12` → 10/10 通过
   - 任务四：改源码后不点任何按钮，500ms 后池内 `stem/solution` 已含标记甲；
   - 任务四续：点【不重复】入库的题干/解析是标记甲（`q_2f7eda21a29537dc7e6c4a4a`）；
   - 任务五：改完立刻点【不重复】（`data-dirty=true`），入库题干/解析是标记乙（`q_ebf2ca5c5eb2d176490026ef`），
     证明强保存跨帧握手生效；
   - 全程零 `pageerror` / 零 console error。

证据：`.qoder/records/biz/2026-11/20261106_dup-compare-evidence/dc12-result.json` 及同批截图
（dc10/dc11 排查轮次产物已清理）。

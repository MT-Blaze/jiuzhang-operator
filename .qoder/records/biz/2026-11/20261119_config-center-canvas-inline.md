# 配置中心画布内联展开 · 模型/API 配置不做弹窗改画布整屏视图

- 状态：待核验
- 发起日期：2026-11-19
- 执行会话：93638b10（委托任务卡《配置中心画布内联展开任务卡.md》）
- 回执编号：#CV-01
- 基线：底座 519e5fe ／ 插件 d89e9d5（2.17.0），坐在其上施工，不卷动不 amend 不 push

## [REQ] 2026-11-19

主公原话：「这俩配置中心，不做弹窗，直接在画布展开。」卡六节：两模态容器改画布内联
视图段（无遮罩/无居中卡片/无 aria-modal/无焦点陷阱，内联铺画布帧随画布滚动，批次列表
期间隐藏、返回原样恢复含选中批次与滚动位置）；开合改视图切换、两视图互斥、再点同按钮
或返回不丢状态；全 Tab 可达、打开焦点落标题或首控件、返回焦点还原触发按钮、Esc 不再关
这两处（别误伤真模态）；整块下架注释更新；375px 不溢出、窄画布双栏折单栏、触控≥44px、
reduced-motion 沿用；2.18.0 四处 parity＋sync_plugin_index＋parity PASS＋zip 重打。
不动面：底座 app/、static/ 零改动，relay 零改动，其余真模态保持，ui_model_config.js
数据驱动渲染不改只改容器开合，catalog/prefs/三态零改动，T6 全禁。红线：禁改区、台账
只减不增、冻结行数不增、分层≤3、unittest 逐模块、快门禁、三查=0、biz append-only、
回单五项；无人值守铁律（不许问主公、界面点击由探针程序化真点、偏离记回单不静默）。

## [IMPL] 2026-11-19

插件仓（commit a8c800e，13 文件）：
- `dist/index.html`（898 行回基线）：两 `.ep-modal` 容器改 `<section class="ed-config-view">`
  视图段，视图顶【返回批次】＋标题（tabindex=-1），内容原样搬进吃满画布帧的卡片；
  删卡内旧标题与【关闭】钮；五处下架注释改视图段口径。
- `dist/panel_dialog.css`：新增 `.ed-config-view` 兄弟规则段（flex 纵排、height:100%、
  overflow-y:auto、head/title/卡片去投影吃满宽）＋返回钮命中区 scoped 补 44px。
- `dist/ai_copilot.css`／`dist/panel_model_config.css`：视图内覆盖旧弹窗限宽限高
  （`.ed-config-view .ep-ai-card`／`.ep-model-config-list`），表单控件 min-height 44px；
  契约字面（900px 限宽等）保留作旧口径基规则。
- `dist/ui_modal.js`（117→172）：openModalNode 焦点圈名单摘除两配置节点（五真模态照旧）；
  新增 openView/closeView：开＝记账（先前屏＋六处滚动位置＋触发钮）后 setMode 进配置屏、
  焦点落标题；返＝还原屏/滚动/焦点；跨视图跳转不重记账。
- `dist/ui_batches.js`（780 行回基线）：setMode 扩六屏（＋model_config/ai_config），
  两视图 hidden 随 mode 切换，互斥由构造保证。
- `dist/ui_model_config.js`／`dist/ui_ai_copilot.js`（800 行回基线）／`dist/plugin.js`
  （828 行回基线）／`dist/ui_dom.js`：开合改 openView/closeView 接线，入口同屏再点＝收，
  【返回批次】接 closeView；数据驱动渲染/relay/prefs 逻辑零改。
- `plugin.toml`／`plugins.json`：2.18.0＋changelog 重写。
底座仓（commit f9cb2d5）：`plugins.toml`、`tests/test_command_registry.py:487` 升 2.18.0；
新增 `tools/canvas_inline_config_probe.py`（425 行，隔离副本＋随机令牌＋动态端口，
Playwright 穿沙箱 23 判据）。zip 重打双份同哈希
d1473892dd6ec68af860120c1433fbf6e7bb3bb51809a293f00fb7d2ddb5905f。
使用 skill：prove-visual-change、sync-biz-record。

## [VERIFY] 2026-11-19

- 定向 unittest 逐模块（.venv 解释器）：test_editor_contract 174/174、
  test_command_registry 34/34、test_models_registry 43/43、test_model_prefs 14/14、
  test_ai_copilot_contract 33/33、test_ingest_triage 21/21、test_file_size_contract 13/13、
  test_interaction_contracts 21/21，合 353/353 绿（CSS 命中区修补后四模块复跑同绿）。
- 快门禁 `bash scripts/check-quick-gate.sh` PASS（6 项）；索引 parity PASS（editor@2.18.0）。
- JS 语法 `tools/js_syntax_check.py *.js` 60/60 OK。
- 真机探针 `tools/canvas_inline_config_probe.py run1` 23/23 PASS：内联形状（无遮罩/
  无 aria-modal/非 fixed/批次隐藏）、焦点落标题、Esc 不关、Tab 十步视图内全控件、
  键盘改默认与停用落隔离插件目录（data/ 全树无 model_prefs.toml）、返回还原批次屏
  ＋400px 非零滚动＋入口焦点、跨视图返回仍落批次、辅助栏同入口再点收、375px 不溢出
  ＋双栏折单栏＋控件/命中区≥44px、零 JS 异常、零 HTTP 失败、三查=0、收口端口复验关闭。
  证据：`.system_generated/canvas-inline-config/run1/`（probe.toml＋7 截图）。
- 冻结行数复核：ui_ai_copilot.js 800／plugin.js 828／ui_batches.js 780／index.html 898／
  layout.css 746／layout_canvas.css 791，全部回基线不增。
- 偏离与欠账见回单 `docs/handoff/receipts/canvas-inline-config.md`（模型入口随批次屏
  隐藏故同钮收只对辅助栏 API 入口成立；底座两 commit；选中批次带数据还原未实测等）。
# 回传单 · 配置中心画布内联展开卡

【回执编号】 #CV-01
【回执时间】 2026-11-19T03:49:28+08:00
【实际耗时】 30 分 55 秒（会话转录文件创建 03:18:33 → 收口读数 03:49:28，系统钟实测）
【执行结果】 成功：定向 8 模块 353/353 绿、快门禁 6 项 PASS、索引 parity PASS、真机探针 23/23 PASS、JS 语法 60/60 OK、两仓 commit 不 push（插件 a8c800e ／ 底座 f9cb2d5＋三笔 docs：1898c65 biz＋回单、fe9ab82 补证、本笔回单定稿）

正文逐条对齐卡§改法 1–6 与不动面；biz 记录
`.qoder/records/biz/2026-11/20261119_config-center-canvas-inline.md`；
基线：底座 519e5fe ／ 插件 d89e9d5（2.17.0），坐在其上施工，不卷动、不 amend、不 push。

## 【改动清单】

插件仓（E:\jiuzhang\jiuzhang-plugins，commit a8c800e，13 文件）：
- 修改：`src/org.jiuzhang.editor/dist/index.html`（898 行，回基线）——两 `.ep-modal`
  模态容器改 `<section class="ed-config-view" id="epAiConfigModal"/"edModelConfigModal">`
  内联视图段：视图顶 `.ed-config-view-head` 内【返回批次】（epAiConfigBack/edModelConfigBack）
  ＋标题（tabindex=-1）；卡内旧 h3 与【关闭】钮删除；内容（双栏/清单/消息行）原样保留。
  五处整块下架注释改「视图段」口径（批次入口、模型入口、panel API 注释、两 script 注释）。
- 修改：`dist/panel_dialog.css`（311→314）——新增 `.ed-config-view` 共享段（flex 纵排、
  height:100%、overflow-y:auto、head/title、卡片吃满宽去投影）＋
  `.ed-config-view-head .ep-mini-btn::after { inset: -11px 0; }`（返回钮命中区 44px）。
- 修改：`dist/ai_copilot.css`（350）——`.ed-config-view .ep-ai-card` 覆盖旧 900px 限宽/
  限高/内滚；表单 input/select min-height 32→44px；契约字面基规则保留。
- 修改：`dist/panel_model_config.css`（173）——`.ed-config-view .ep-model-config-list`
  去 52vh 内滚；默认下拉 min-height 44px；头注释改内联视图口径。
- 修改：`dist/ui_modal.js`（117→172）——openModalNode 焦点圈/Esc 名单摘除两配置节点
  （del/batchPurge/poolDel/aiOverwrite/modelModal 五真模态照旧）；新增 openView/closeView：
  开＝记账先前屏＋六处 scrollTop＋触发钮（activeElement，body 时兜底画布入口）后
  setMode 进配置屏、焦点落 `.ed-config-view-title`；返＝setMode 还原＋scrollTop 回写＋
  触发钮可见才还焦；viewReturn 只记一次，跨视图跳转不覆盖。
- 修改：`dist/ui_batches.js:495-504`（780 行回基线）——setMode 扩六屏
  （＋model_config/ai_config），两视图 hidden 随 mode 切，互斥由构造保证。
- 修改：`dist/ui_model_config.js`（311→315）——deps 换 openView/closeView/coreState，
  open() 同屏再点＝closeView，wire() 接 backEl；数据驱动渲染/refresh/prefs/install 零改。
- 修改：`dist/ui_ai_copilot.js`（800 行回基线）——openConfig 同屏再点＝closeView、
  openModal→openView("ai_config")；wireCanvas 关闭钮改 backEl→closeView；
  openModal/closeModal deps 保留（覆盖确认真模态仍用）。
- 修改：`dist/plugin.js`（828 行回基线）——uiModal create 注入 setMode 闭包；
  uiAiCopilot/uiModelConfig deps 换 openView/closeView；注释改视图口径。
- 修改：`dist/ui_dom.js`（441→443）——＋aiConfigListEl、modelConfigCloseEl→modelConfigBackEl。
- 修改：`src/org.jiuzhang.editor/plugin.toml:4`、`plugins.json:68,72`——2.18.0＋changelog。
- 修改：`plugins/org.jiuzhang.editor.zip`——重打，sha256
  d1473892dd6ec68af860120c1433fbf6e7bb3bb51809a293f00fb7d2ddb5905f（与底座 dist/plugins 同哈希）。
底座仓（E:\jiuzhang\jiuzhang-operator，commit f9cb2d5）：
- 修改：`plugins.toml:51`、`tests/test_command_registry.py:487`——2.18.0 parity。
- 新增：`tools/canvas_inline_config_probe.py`（425 行≤450，隔离副本＋随机令牌＋动态端口，
  Playwright 穿沙箱 23 判据；tools/ 属 DEV_ONLY 豁免体积三档）。
- 新增：本回单与 biz 记录（docs commit，见偏离②）。
删除：无整文件删除；index.html 删两【关闭】钮与卡内旧 h3（视图 head 取代，零引用残留：
  grep epAiConfigClose/edModelConfigClose 全仓 0 命中）。
禁改区自查：LICENSE／根 agents.md／AGENTS 铁律一二／app/core/question_contract.py／
用户 data/ —— 否。依据：两仓 `git show --stat` 仅上述点名文件；探针 JZO_DATA_DIR 指
隔离副本，用户 data/ 零写入；底座 app/、static/ 零改动（git status 无条目）。

## 【包结构自检】

- 顶层目录名 == plugin.toml id：是（zip namelist 顶层仅 `org.jiuzhang.editor/`）。
- backend 字段：无（toml 解析 backend=None，kind=tool）。
- Apache-2.0 LICENSE 全文：有（zip 内 `org.jiuzhang.editor/LICENSE`，本次未改）。
- min_host_version 1.0.0 ≤ 当前 app.__version__ 1.2.0：满足。
- 索引 parity：`scripts/check_plugin_index_parity.py` PASS（两份索引一致、五条目版本一致，
  editor@2.18.0）；`tools/sync_plugin_index.py` 已跑（本地版本变化已改写）。

## 【三查结果】

命令（插件 dist 全量 js＋html）：
`grep -r -c 'fetch(' *.js *.html` 非零文件数 0；
`grep -r -l 'parent\.document' *.js *.html` 0；
`grep -r -l 'localStorage' *.js *.html` 0。
探针内独立复核（隔离副本 dist 全 js 逐串计数）：fetch(=0、parent.document=0、localStorage=0。
请求 id：本次未新增总线主题/请求 id（复用 editor.batch_review 的 ai_config 分支），无含点号新 id。

## 【测试与探针】

- 单测（`.venv/Scripts/python.exe -m unittest tests.<模块>` 逐模块，禁 pytest/discover）：
  test_editor_contract 174/174、test_command_registry 34/34、test_models_registry 43/43、
  test_model_prefs 14/14、test_ai_copilot_contract 33/33、test_ingest_triage 21/21、
  test_file_size_contract 13/13、test_interaction_contracts 21/21 —— 合 353/353 绿。
  CSS 命中区修补后复跑 editor/ai_copilot/file_size/interaction 四模块同绿。
- 快门禁：`bash scripts/check-quick-gate.sh` → check-quick-gate: PASS（6 项全过）；
  体积 WARN 23 份皆存量（451–550 区间），本次冻结文件全部回基线不增：
  ui_ai_copilot.js 800／plugin.js 828／ui_batches.js 780／index.html 898／
  layout.css 746／layout_canvas.css 791。
- JS 语法：`tools/js_syntax_check.py *.js` → 60/60 OK。
- 真机探针：`tools/canvas_inline_config_probe.py run1` → 23/23 PASS，ok=True。
  证据绝对路径：E:\jiuzhang\jiuzhang-operator\.system_generated\canvas-inline-config\run1\
  （probe.toml＋shots 7 张：01 批次滚动态／02 模型内联／03 停用态／04 返回还原／
  05 API 内联／06 375 模型／07 375 API）。视口 1440x900 与 375x720 两档记录在 probe.toml。
  隔离：JZO_DATA_DIR/JZO_PLUGINS_DIR 指 run1 下副本、动态空闲端口、随机令牌
  probe-<16hex>；收口 terminate＋端口 connect_ex 复验关闭（PASS）。
- 浏览器真人路径（全工具驱动，Playwright locator.click/keyboard 真输入事件穿沙箱 iframe）：
  点模型配置→画布整屏切视图（截图 02：无暗遮罩、内容在画布流内、批次列表不见、辅助栏照旧）；
  Esc 视图不关；Tab 十步全在视图内摸到钮与下拉；键盘 ArrowDown+Enter 改默认落
  model_prefs.toml；点停用→解析下拉 YOLO 消失＋prefs 落隔离插件目录；【返回批次】→
  批次屏回来、400px 滚动位置分毫不差、焦点回【模型配置】钮（截图 04）；模型视图
  【去 API 配置指派】→互斥切 API 视图（截图 05 双栏内联）→返回仍落批次屏；辅助栏
  【API 配置】同钮再点＝收；375px 双栏折单栏、scrollWidth-clientWidth=0（截图 06/07）。
  真人抽检：未做（2026-11-18 换装裁决降为可选）。

## 【未决问题与偏离】

- 偏离①（口径）：模型配置入口住批次屏头部，视图打开时批次屏整块隐藏（卡「批次列表期间
  隐藏」的必然结果），故「再点同按钮收」只对辅助栏常驻的 API 入口成立（探针实测 PASS）；
  模型视图收走【返回批次】。open()/openConfig() 的同屏 toggle 语义保留（探针 API 可达）。
  未新增顶栏/辅助栏钮（卡「按钮不动」）。
- 偏离②：底座多笔 commit（f9cb2d5 施工＋探针，另三笔 docs 见补证节）。卡「底座单
  commit」前提是「仅 parity 两文件」，本次交付含探针与记录资产；不 amend 铁律优先，故拆笔。
- 偏离③（修补披露）：迷你钮 ::after 外扩按 padding box 算实测命中区 42px（24 本体扣 2 边框
  ＋20），不足 44；在 panel_dialog.css 加 scoped 规则 `.ed-config-view-head .ep-mini-btn::after
  { inset: -11px 0; }` 补到 44px，只影响两视图返回钮，全局迷你钮约定未动。
- 解释性口径：跨 iframe 焦点还原——辅助栏开视图时触发钮在另一帧，返回焦点兜底落画布入口
  钮（offsetParent 可见才还焦），探针实测 PASS；同帧开视图则精确还原触发钮。
- 欠账：无阻塞项。冻结文件行数已回基线，台账无需登记新增。
- 未验证：①选中批次/三栏审核态带数据跨配置开合的还原——setMode 只切 hidden、state.items/
  active 不动（机制在案），探针只实测批次列表屏 400px 非零滚动还原，未进批次再开配置；
  ②触控真机（触摸屏）未摸，只量命中区几何≥44px；③reduced-motion 无新增动画（ep-ai-spin
  存量规则未动），未单独实测；④真人抽检未做（全工具驱动）。

## 补证 · 内联前后对比截图结论（2026-11-19 03:53 追加）

「前」用 git archive 基线 d89e9d5 解出隔离副本起服真点取证（脚本
`.system_generated/canvas-inline-config/before_shot.py`，住证据目录不进 git；
隔离口径同主探针，收口端口复验关闭 PASS，读数 `before/before.toml`）：
- 00-before-model-modal.png／00-before-api-modal.png：旧形态＝画布上压 rgba(42,36,29,0.42)
  暗遮罩＋居中浮卡，computed position=fixed、aria-modal=true、role=dialog，批次列表在遮罩后仍可见。
- 02-model-config-inline.png／05-api-config-inline.png：新形态＝无遮罩（可见 .ep-modal 计数 0）、
  position 非 fixed、无 aria-modal/role，视图顶【返回批次】＋标题，内容铺满画布帧随画布滚动，
  批次列表整块隐藏，辅助栏与顶栏原样。
结论：两配置中心已从浮层模态变为画布内联整屏视图，前后对比截图与 computed 形状读数互证。
本补证与回单定稿各随独立 docs commit 入库（底座共四笔：施工＋探针／biz＋回单／
补证／回单定稿；偏离②「单 commit」前提不成立，不 amend 铁律优先）。
# 记号标准字典·平表化＋砍头＋缓存版本号小卡

- 状态：已发布（本地全绿收口；两仓 push 待主公授权 hold）
- 发起日期：2026-11-19（主公点头「对的，你的建议是对的」＝批准三刀）
- 任务卡：E:\jiuzhang\记号字典平表砍头小卡.md
- 基线：底座 ad7a149 ／ 插件 51776cf（2.22.0 PP-M 收口）；插件零改＝parity 持 2.22.0、zip 不重打

## [REQ] 2026-11-19

背景：主公在数据看板右栏找不到「记号标准」按钮，根因＝浏览器吃旧 catalog.js 缓存
（版本号漏升，65496 旧进程启发式缓存时代遗留）；Ctrl+F5 后见过 2.21.0 卡片版，
斥其太高占空间。本卡三刀：①砍头（面板 h2/整机徽章/说明段＋单枚二级标签条不渲染）
②卡片改六列平表（一行一变体、名称/操作格 rowspan 合并、行高约 36px）
③catalog.js 两处缓存版本号升派卡当日戳。

验收标准（卡 §0–§8）：
- 右栏「记号标准」真点→画布原地平表；六列＝名称/代码/来源/渲染/默认/操作；
  全过滤行数＝/api/norm/entries 变体总数；radio/恢复出厂复用 norm.* 写库路径一字不动。
- chips/搜索/norm_inbox/其余字典分类/插件全族/API/relay/整机库层一字不动；
  单标签隐藏不得弄坏多标签分类与独立 /dict 页。
- 375px 表容器横滚不溢画布；宽屏＋窄屏截图；写库两次回执留 wire。
- 探针隔离副本 git archive HEAD、动态端口随机令牌、零引擎零出网、65496 零接触；
  收口点杀＋端口复验＋孤儿零。norm_dict.js/css ≤450 正常 >550 硬停。
- 两仓不 push（主公明确不授权别再问）；无人值守不许问主公，偏离记回单；不绿不 commit。

## [IMPL] 2026-11-19

底座四笔（不 push、不 amend、stage 逐个点名）：
- 阶段1 fa5a065：norm_dict.js 原 58-63 head 块整删；subtabs.js:24-56 solo 单枚不渲染
  标签条（pane 照铺、aria-label 回落、钉死串 :79 保留）；css 摘 machine-badge 一段
  （.dc-norm-head/.dc-panel-hint 共用类保留）。
- 阶段2 4a55a32：norm_dict.js（271）renderList():109 真 table 六列、entryRows():175
  一行一变体＋rowspan 合并、syncDefault/choose/reset group 对象（写库路径与 DcDialog 一字未动）、
  matches():99 不动；css（246）list overflow-x auto＋table min-width 760＋td height 36＋
  渲染格 180-280 内部横滚，删旧卡片族选择器。
- 阶段3 fe7bc9a：workspace.html:250 与 dict_console.html:116 catalog ?v=20261119（卡面两处）；
  偏离加升三枚改过资产 ?v=20261119b（dict_console.html:25,138,150——主公已 Ctrl+F5 取过
  今日戳卡片版，URL 不变则 returning 缓存吃改形，重演找不到按钮同根因）。
- 阶段4 f7823e3：tools/norm_dict_table_probe.py（399，新建，git archive HEAD 隔离＋
  dashboard＋bank-engine 双插件）＋tools/latex_norm_ui_probe.py（371，断言随 UI 改形同步，
  AGENTS §8.6）＋证据 16 文件扁平落 docs/handoff/evidence/norm-dict-table/（分层≤3）。

宿主升版自判不升（app/__init__.py=1.2.0 单源，UI 改形非封版，先例各卡未动宿主版）。
插件仓零写入（HEAD 51776cf 不动）。

使用的 skill：prove-visual-change（探针真浏览器取证口径）、sync-biz-record（本记录）。

## [VERIFY] 2026-11-19

单测逐模块（.venv 解释器，禁 pytest/discover）：test_norm_api 8/8、test_latex_norm 37/37、
test_dict_console_subtabs 17/17（钉死串保留实证）、test_dict_console 14/14。
JS 语法全量逐文件 node --check 82/82；快门禁 PASS（6 项）；体积预警 23＝基线
（norm_dict 271/css 246/subtabs 113/探针 399/371 均≤450）；三查 0/0/0 PASS。

双探针全绿（Playwright 自驱 chromium，零引擎零出网）：
- 新探针 t6 工作台右栏真人路径 16/16（head=fe7bc9a 隔离副本）：271 行/223 rowspan/六列/
  砍头四断言（面板范围）/radio 真点 le→43 写库＋choose 200 wire/恢复出厂对话框确认→
  chosen NULL＋reset 200 wire/chips 关系不等＋搜索 leqslant 真点对账/375px doc=375
  listScroll=400 tableMin=760 host_doc=375/零 JS/HTTP/console；port_closed=true、孤儿 0、
  65496 零接触。
- 旧探针 t6-standalone 独立 /dict 页 18/18（不回归证据：多标签/独立页/对话框 Esc 归位/
  开集收编驳回全路径照旧）。
- 调试轮次如实记：t1 红（bank-engine schema 缺＋孤儿自匹配）→t2–t4 headless lazy 帧诊断
  （探针侧 scroll 规避，产品零改）→t5 4/5（h2 断言过严＋radio selector bug）→t6 双绿。

证据：docs/handoff/evidence/norm-dict-table/（probe.toml/wire.toml/standalone-probe.toml＋13 截图）。
回单：docs/handoff/receipts/norm-dict-table.md（NDT-01，五项＋偏离十条）。
收口：两仓不 push（底座 ahead 46 含他卡 42／插件 ahead 13 零写入）；
tools/onnx_probe.py 与 plugins models/＋model_prefs.toml 豁免不碰不 stage。
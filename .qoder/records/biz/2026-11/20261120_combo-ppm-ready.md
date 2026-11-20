# 组合座 combo_pp_m 就绪恒真修复（combo-ppm-ready）

状态：收口全绿（真看权重；底座产线零改；两仓 commit 不 push）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达 #COMBO-PPM-READY-01（主公 2026-11-20 裁决「第二个组合座，那得修啊」）
基线：operator 68ad244（ahead 87）／plugins 0841ccd（ahead 22）；收口后 plugins 93e4686（ahead 23）、operator 收口笔（ahead 88）
回单：docs/handoff/receipts/combo-ppm-ready.md（#COMBO-PPM-READY-01）

## [REQ] 2026-11-20

病灶：catalog.toml:219-233 combo_pp_m 走 import_probe，模块永远能导入 → PP-M 权重没装
本组合也恒"就绪"，老师选了公式标待核却不自知。
卡令：改 weight_present＋store=formula（同 formula_pp_m/combo_pp_l 口径），degraded_detail
与 summary_usage 改真话；ready_detail/plan_recognize/combo_seat/route_note 不动；
底座零改；测试转正不删案；版本 2.25.1 出包双建同哈希＋parity/package；UI 隔离真测；
定向七模块＋快门禁；两仓各 1 笔不 push；65496 零接触；禁 JSON 落盘。

## [PLAN] 2026-11-20

先复核：两仓 HEAD/脏件与卡§0 一致；registry.py:111-152 确认 store="formula" 走
_formula_verdict(variant="m")、action 自动 install_formula、route 层 gate 按就绪筛选——
底座零改成立。测试面逐处：last_used_engine:160-164 案名保留转正；models_registry
全组合表加 pp_m、原"恒 ready"案拆两半；recognize_router 只走 fill_batch 不设门，跑绿即可。
UI 取舍：四栏表按设计不列组合路（ui_model_table.js:177-179），老师可见落点是识别下拉，
故证据做 baseline/fixed 两跑（下拉列不列＋registry 三态），并以公式座行【安装】承接引导。
出包先双建验哈希再落两处；索引走 sync_plugin_index。

## [IMPL] 2026-11-20

- 插件仓 93e4686（MT-Blaze 瞬态身份）：catalog combo_pp_m 一条（rule/store/degraded_detail/
  summary_usage）；plugin.toml 2.25.1；zip 重打；plugins.json version+changelog。
- 底座仓：plugins.toml 同步 editor 2.25.1；test_last_used_engine 两案转正
  （combo_pp_m 口径＋texify 预建陈旧红）；test_models_registry 两处转正；回单＋本记录。
- 底座 app/ 全树零改；UI 结构零改；未新增探针工具入仓（探针落 .system_generated，git 忽略）。
- 偏离：①UI 表不列组合路（按设计，下拉承接就绪态）；②texify 断言跨仓陈旧红顺带转正；
  ③combo_pp_m 不显式写 degraded_action（由 _formula_verdict 推导，与同族一致）。

## [VERIFY] 2026-11-20

- 定向七模块全绿：models_registry 79／last_used_engine 15／recognize_router 26／
  formula_route 39／formula_setup 63／vlm_setup 33／file_size_contract 13。
- 快门禁 PASS（6 项全过）；体积警报 23 份与基线相同；parity/package PASS。
- 出包双建同哈希 e1cd31ac909f544d8ef2eef7e4acaafe7fd8fffd434be45ee98f5170e8baba91。
- UI 隔离两跑：baseline combo_pp_m ready＋下拉列出（恒绿复现）；fixed degraded/
  install_formula＋下拉不列（与 combo_pp_l 一致）；两次零 JS 异常、零 HTTP 失败、
  端口 63363/63394 收口已关；未点安装零出网。证据 .system_generated/combo-ppm-ready/。
- 红线：65496 零接触；未 taskkill /F /IM python.exe；禁改区零改；两仓不 push；
  插件仓未跟踪 models/＋model_prefs.toml 原地保留未 stage。
- 收口后 tasklist 只读复核产品进程仍在（65496／PID 2700 照旧）。

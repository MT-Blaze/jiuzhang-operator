# 模型配置界面与识别下拉同字（model-name-align）

状态：收口全绿（插件 2.26.2＋底座测试/探针/索引；两仓不 push；生效需主公重启一次）
发起日期：2026-11-20
需求来源：主公 2026-11-20「模型配置界面和这个下拉列表，他们的文字一定是一致的。」（#MODEL-NAME-ALIGN-01）
基线：operator 7f264f1（ahead 95）／plugins 332202c（editor 2.26.1，ahead 25）
回单：docs/handoff/receipts/model-name-align.md（#MODEL-NAME-ALIGN-01）

## [REQ] 2026-11-20

模型配置表（读 catalog.toml 的 name）与识别下拉（短名，2.26.0 已拍板）同一模型两处不同字。
现 4 对不一致：combo_cloud「云端 AI OCR」vs 座「云端视觉」；combo_pp_m/l、combo_p2t、combo_texify
短名 vs 座名带「（公式专科）」后缀。口径：下拉短名为准，座名跟随；id/规则/链路不动。
另加护栏测试防再漂移，随名同步测试/探针，升版本重打发行包。

## [PLAN] 2026-11-20

开工复核与卡§0一致（plugins 6 件改动面、operator 脏件仅 `?? tools/onnx_probe.py`）。关键决策：

- 只改展示 name 与用户可见散文；内部 id/task/plan/rule/store 零改。
- 散文里叙事性「公式专科」保留，只 name 去后缀；README 同一文档口径一起同步。
- 护栏测试挂底座 `CatalogDataTest`：组合条目 name 必须与 combo_seat 座条目逐字相等。
- 探针随名改；模型表行定位从 has_text 改 data-id（同名后去歧义）。
- 打包沿用 `tools/build_plugin.py`，先建两遍比哈希再覆盖插件仓 `plugins/`。
- UI 取证走隔离宿主（copy 源码＋动态端口＋假视觉账号），不重启/不杀 65496 PID 16992。

## [IMPL] 2026-11-20

- plugins commit `135666d`：catalog.toml（4 座名＋12 处散文）、README.md（8 处）、
  dist/ui_intake.js:70 tooltip、plugin.toml 2.26.2、plugins.json 2.26.2＋changelog、
  重打 `plugins/org.jiuzhang.editor.zip`（双建同哈希 19237b6c，328.5 KB，90 条目）。
- operator `901eb53`：tests/test_models_registry.py（新护栏＋两处断言）、
  tests/test_ingest_routing.py、tests/test_formula_route.py、tests/test_command_registry.py、
  tools/texify_live_probe.py、tools/t6_route_probe.py、plugins.toml（editor 2.26.2）。
- operator 回单笔：本 biz＋docs/handoff/receipts/model-name-align.md。

## [VERIFY] 2026-11-20

- 定向 4 模块 144/144 OK（含新护栏）。
- 快门禁 PASS（6 项）；体积预警 23 份与基线相同。
- 索引 parity rc0；包结构 rc0；zip 双建同哈希，in-zip catalog 与源 MATCH。
- 隔离宿主 UI 取证 14/14：7 对「下拉↔模型表座行↔registry」逐字相等，两处名单无旧称；
  4 张截图落 .system_generated/model-name-align/shots/。
- 偏离：combo_texify 本机权重未装不入下拉（表名＋护栏双证）；app/core 运行期错误/步骤文案
  仍用旧称，不在本卡两面范围；live 65496 未动，生效需重启一次。

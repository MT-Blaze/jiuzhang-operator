# 识别下拉改名与分组小刀（engine-dropdown）

状态：收口全绿（插件 2.26.0＋底座测试/探针；两仓不 push；生效需主公重启一次）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达 #ENGINE-DROPDOWN-01（主公裁决：云端 AI OCR 短名／本机激活几座 VLM 就列几条／
「组合路」三字不要／禁用表头行对齐／自动是分流不归图片组）
基线：operator 9bf3f45（ahead 91）／plugins 93e4686（editor 2.25.1，ahead 23）
回单：docs/handoff/receipts/engine-dropdown.md（#ENGINE-DROPDOWN-01）

## [REQ] 2026-11-20

组合条目文案去「组合路」、改短名；`combo_cloud` 叫「云端 AI OCR」；旧 `combo_vlm` 按本机激活的
千问/书生/面壁逐条拆开；识别下拉改「自动单独置顶＋禁用表头行（—— 整题OCR ——／—— 文字直取＋公式 ——）
全平铺」，不再用 optgroup；版面下拉保持扁平；纯图卷置灰与归 auto 语义不动。
插件 2.25.1→2.26.0，发行包双建同哈希；底座只动测试与探针；定向回归＋快门禁；两仓 push hold；
65496 零接触；禁用 JSON 落盘；stage 点名、不 amend。

## [PLAN] 2026-11-20

开工复核与卡§0一致。关键决策：
- 下拉用禁用 option 当表头（文档流天然左对齐），auto 在两组之外单独置顶，组合归属仍由 `comboIds` 判定。
- 三条 VLM 组合沿用 `rule = "vlm_local"`＋`combo_seat`，registry 既有逻辑按 `combo_seat` 取座、
  按座出 `install_vlm[_intern/_minicpm]`，产线零代码改。
- 探针组头定位改「禁用 option 文本」；底组不写死，按 registry 就绪组合集合断言；
  选座/停用步骤动态挑一条就绪组合。
- 实际产物路径按现状：`dist/plugins/*.zip`＋主仓 `plugins.toml`＋插件仓 `plugins.json`。

## [IMPL] 2026-11-20

- plugins commit `3b45428`：catalog.toml（19→21 条目、组合 6→8；短名与去「组合路」；combo_vlm 拆三座）、
  dist/ui_intake.js（groupHead＋自动置顶＋两禁用表头平铺）、plugin.toml 2.26.0、plugins.json 2.26.0＋changelog、
  重打 zip（双建同哈希 dbea4a6b）。
- operator 笔1：tests/test_models_registry.py（按座权重 mock、8 条期望、三座分别随座）、
  tests/test_recognize_router.py（改指 qwen＋补 intern 透传）、tests/test_last_used_engine.py（平铺与表头契约）、
  tests/test_command_registry.py（版本表 2.26.0）、tools/last_used_engine_probe.py（组头/动态组合/浮层截图）、
  tools/vlm_live_probe.py（旧 id 同义改名）、plugins.toml 2.26.0。
- operator 笔2：本回单＋本 biz。

## [VERIFY] 2026-11-20

- 定向 10 模块 305/305 OK（79/26/16/16/39/21/35/27/33/13）。
- 快门禁 PASS；体积预警 23 份与基线相同；索引 parity PASS；包结构 PASS。
- UI 真机探针 38/38 PASS：21 条目、8 条组合声明，本机就绪 7 条（texify 未就绪不出现）；
  自动置顶、两条禁用表头、零 optgroup、底组==registry 就绪集合、纯图卷组合 disabled、auto 可回退；
  截图 8 张落 `.system_generated/engine-dropdown/`。
- 红线：禁改区零改；未跟踪运行产物未 stage；65496 零接触；零真引擎/安装/出网；未 taskkill。

## [RELEASE] 2026-11-20

两仓 commit 全 hold。plugins ahead 23→24（3b45428）；operator ahead 91→93（测试＋探针笔，回单＋biz 笔）。
偏离：产物路径与索引文件按现状（dist/plugins＋plugins.toml／插件仓 plugins.json）；zip 入插件仓笔；
追加同义修 vlm_live_probe 的旧 combo_vlm；原生下拉展开层截不到，用同内容 listbox 浮层截图，
置灰以 DOM disabled 为证。生效需主公重启一次（与在途重启债合并）。

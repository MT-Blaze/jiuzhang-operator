# 「组合路」用户可见字样清理（combo-label-cleanup）

状态：收口全绿（插件 2.26.1＋底座测试/索引；两仓不 push；生效需主公重启一次）
发起日期：2026-11-20
需求来源：主公 2026-11-20「『组合路』三个字就不要了」的收尾刀（#COMBO-LABEL-CLEANUP-01）；
上一卡 #ENGINE-DROPDOWN-01 已清条目短名与分组
基线：operator 63acf83（ahead 93）／plugins 3b45428（editor 2.26.0，ahead 24）
回单：docs/handoff/receipts/combo-label-cleanup.md（#COMBO-LABEL-CLEANUP-01）

## [REQ] 2026-11-20

清掉插件里剩下 5 处老师能看到的「组合路」：catalog `formula_pp_m.degraded_detail`、
识别下拉纯图卷灰项 title（连同同行注释）、纯图卷打回自动分流的 dock、
公式座安装确认（PP-FormulaNet·M／Texify）。编辑器 2.26.0→2.26.1，重打发行包双建同哈希，
两份索引同步；底座只动测试与 `plugins.toml`；不扩面——内部注释与算子 app 的技术口径不碰。

## [PLAN] 2026-11-20

开工复核与卡§0一致（plugins 6 件改动面、operator 脏件仅 `?? tools/onnx_probe.py`）。关键决策：

- 5 处按卡面逐字替换，一个标点不加不减；同段注释按卡面点名的原文一并改。
- 打包沿用 `tools/build_plugin.py`（校验清单→白名单→zip），先建两遍到
  `.system_generated/combo-label-cleanup/build1|build2/` 比哈希，通过后覆盖插件仓 `plugins/`。
- `plugins.json` 只改 editor 的 version 与 changelog（新段前置＋旧段保留），description 不动。
- 版本升了必带 `test_command_registry` 手工表同步，否则假红；`test_last_used_engine` 按其新文案收窄断言。

## [IMPL] 2026-11-20

- plugins commit `332202c`：catalog.toml（degraded_detail）、dist/ui_intake.js（title＋同段注释、dock）、
  dist/ui_model_install.js（两条安装确认）、plugin.toml 2.26.1、plugins.json 2.26.1＋changelog、
  重打 `plugins/org.jiuzhang.editor.zip`（双建同哈希 192f9731，328.5 KB，90 条目）。
- operator `2ead5a4`：tests/test_last_used_engine.py（assertIn「只支持文字卷」，自动分流断言保留）、
  tests/test_command_registry.py（editor 2.26.1）、plugins.toml（editor 2.26.1）。
- operator 回单笔：本 biz＋docs/handoff/receipts/combo-label-cleanup.md。

## [VERIFY] 2026-11-20

- 定向 4 模块 143/143 OK（16／79／35／13）。
- 快门禁 PASS（6 项）；体积预警 23 份与基线相同。
- 索引 parity PASS；包结构 PASS（官方 5 支）；zip 内三文件与源逐字节 MATCH。
- grep 收口：插件源码里「组合路」只剩 `ui_model_table.js:177`、`ui_reidentify.js:149` 两条内部注释。
- 红线：禁改区零改；未跟踪运行产物未 stage；两仓未 amend／未 push；65496 零接触；零真引擎／安装／出网。
- 本卡无 UI 真测（纯文案、控件结构未动），如实登记在回单桶五。

## [RELEASE] 2026-11-20

两仓 commit 全 hold。plugins ahead 24→25（332202c）；operator ahead 93→95（测试＋索引笔，回单＋biz 笔）。
偏离：多改 `test_command_registry` 版本表（版本升必红的连带）；changelog 沿用累积写法；
「组合路」在算子 `app/core/ingest/recognize/router.py` 的 docstring／route note／异常文案按卡面不碰。
生效需主公重启一次（与在途重启债合并）。

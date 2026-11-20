# 组合名从座继承（model-name-inherit）

状态：收口全绿（插件 2.26.3＋底座 registry/测试/索引；两仓不 push；生效需主公重启一次）
发起日期：2026-11-20
需求来源：主公 2026-11-20「他俩不应该改一个，另一个是引用的一个状态吗」（#MODEL-NAME-INHERIT-01）
基线：operator b419dd4（ahead 97）／plugins 135666d（editor 2.26.2，ahead 26）
回单：docs/handoff/receipts/model-name-inherit.md（#MODEL-NAME-INHERIT-01）

## [REQ] 2026-11-20

2.26.2 只把组合条目与座条目的 name 抄一致并加护栏，治标不治本：改一处忘一处仍会漂移。
主公要求组合名直接引用座名。定案：catalog 8 条 combo_* 删除自写 name；底座在
status() 组装时单源继承，_judge 之前生效；缺座/空名显性 blocked，不静默空名。

## [PLAN] 2026-11-20

- 继承只落 registry 一处：新增 resolve_entries()，status() 先继承后 _judge；
  下游（{name} 占位、错误文案、下拉、模型表、entry_state、闸口）零改。
- 无条件覆盖：旧包残留 combo name 也以座为准。
- 测试升级不删判据：catalog 无 name＋status 跟随＋注入式改座名跟随＋缺座 blocked。
- 打包双建同哈希；UI 沿用隔离宿主探针，截图落 inherit/。

## [IMPL] 2026-11-20

- plugins commit df3fd6c：catalog.toml 删 8 行 combo name、plugin.toml 2.26.3、
  plugins.json 2.26.3＋changelog 前置、重打 zip（双建同哈希 742d0b58，328.5 KB）。
- operator 622a5ec：registry.resolve_entries()＋status 顺序、test_models_registry 4 项新判据、
  test_last_used_engine VLM 组合断言改新契约、plugins.toml editor 2.26.3。
- operator 回单笔：本 biz＋docs/handoff/receipts/model-name-inherit.md。

## [VERIFY] 2026-11-20

- 定向 4 模块 147/147 OK。
- 快门禁 PASS（6 项）；体积预警 23 份与基线相同。
- 索引 parity rc0；包结构 rc0；zip 双建同哈希。
- 隔离宿主 UI 15/15：API 组合名==座名==2.26.2 原字 8 条全覆盖；下拉/模型表逐字不变；
  零 JS 异常、零 HTTP 失败；4 张截图落 .system_generated/model-name-align/inherit/。
- 偏离：combo_texify 未装权重不入下拉（三处核座行名）；router.py 旧名文案按卡另议未动；
  live 65496 未动，生效需重启一次。

## 补记（枢纽复核）

- 原 147/147 为升 2.26.3 前所跑；EXPECTED 版本表漏升（test_command_registry.py:519 仍 2.26.2），
  已改 2.26.3 并复跑 147/147 OK，commit f4a1c8d（底座 ahead 100）；快门禁 PASS（6 项）。
- 作废 stash cancelled-seat-removal-20261120 已取证（底座 29 文件、插件 6 文件）后各 drop 一次，
  两仓 stash list 均为空。

# 配置归插件重构 · 模型目录/三态规则数据化/勾选代笔通用化

- 状态：待核验
- 发起日期：2026-11-18
- 执行会话：f07bfb73（委托任务卡《配置归插件重构任务卡.md》）
- 回执编号：#CTP-01
- 基线：底座 8852be1 ／ 插件 ebbc9e5（2.15.0），坐在其上施工，不卷动不 amend 不 push

## [REQ] 2026-11-18

主公架构令：底座只留通用接口（探针/安装/存储各插件自目录/relay/录题路由＝公共管道）；
模型清单 toml＋大白话说明＋启用停用是录题插件财产，搬回插件。卡六节：目录搬家
（catalog.toml 随 zip 发行、更新覆盖＝清单可更新；prefs 教师财产 carried）＋models.catalog
能力枚举（bank.provider 先例）；三态通用化（六规则解释器，未知规则 blocked＋提示更新底座，
人话全归 catalog）；prefs 通用化（删 PLUGIN_ID 硬编码，按 tab.plugin.id 代笔，未声明能力
FORBIDDEN，data/ 全树禁 model_prefs.toml）；不动面（hardware/mineru_setup/relay 方法名与
返回形/UI 零改/index.html 零改/T6 全禁）；红线（禁改区、台账只减不增、新模块≤450 引擎≤400、
定向 unittest、快门禁、Playwright 隔离取证禁写死端口令牌、三查=0、2.16.0 三处 parity）；
交付（两仓各单 commit 不 push＋biz＋回传单五项）。

## [PLAN] 2026-11-18

- 口径披露：三态规则＝通用契约留底座（Python ingest 路由同步要用，问不了 iframe）；
  模型清单/说明/门槛/勾选全归插件 catalog＋prefs。
- 包 B 决策：卡要求 app/ 下模型 id grep=0，而旧 id 还住在 layout/recognize router 的
  调度常量与 route.py 注记分支里——把两条 router 与路由注记也改成 catalog 数据驱动
  （plan_layout/plan_recognize、aliases_*、route_note_*），底座只认步骤实现名
  （python/yolo/cloud/ocr/local/ai/mineru＝公共管道实现名），不认模型。
- 循环导入 avoidance：registry 闸口懒导入 router；router 懒导入 registry.catalog()。
- 夹具：tests/catalog_fixture.py 造最小 headless 目录提供者插件（声明 models.catalog、
  拷真实 catalog.toml），JZO_PLUGINS_DIR/JZO_DATA_DIR 进临时区（bank.provider 夹具先例）。

## [DESIGN] 2026-11-18

- catalog.toml 搬插件根并扩展：16 条原字段逐字保留（程序化子集证明 missing=[]），
  每条加 rule＋参数＋人话模板（{name}/{model}/{version}/{message}/{vram_label}/{min_vram}/{fits}
  由底座填，填不上原样念）＋plan/aliases/route_note；vram_note＋7 档逐字保留。
- registry.py 重写 253 行：catalog_provider() 按能力发现启用插件；_document 缺失/损坏＝{}；
  六规则 handler 签名统一 (item, ctx, hw, tiers)；_judge 未知规则→blocked「底座不认识这条
  规则「X」，请更新底座后再用该条目。」；status() 每次现算（D3b）；_gate 语义不变（D3a）。
- model_prefs.py 72 行：path/load/save 全带 plugin_id，_PLUGIN_ID 正则封口防路径穿越；
  api/models.py 73 行：_catalog_plugin 三查（未声明/停用/未安装→403），prefs 带 Query plugin_id。
- relay（stage_relay_io.js）：prefs_save 增 models.catalog 能力闸（FORBIDDEN），URL 带
  plugin_id=tab.plugin.id；方法名与返回形不变；行数净零 773。
- 更新语义单测钉死：新包无 prefs→carried；新包带 catalog→覆盖（.toml 不在 DATA_SUFFIXES）；
  新包无 catalog→carried（降级不停摆）。

## [IMPL] 2026-11-19

- 底座：app/core/ingest/{registry.py 重写, model_prefs.py 重写, catalog.toml 删,
  layout/router.py 135 行, recognize/router.py 170 行, route.py 399 行}、
  app/api/{models.py 重写, ingest.py docstring 去 id}、app/core/plugins/registry.py
  _CAPABILITIES＋models.catalog（731 行净零）、static/js/stage_relay_io.js、
  docs/PLUGIN_SPEC.md §2.6.2 新节＋能力表行、plugins.toml（sync 工具改写）。
- 测试：tests/catalog_fixture.py 新增；test_models_registry/test_model_prefs 重写；
  test_layout_router/test_recognize_router/test_ingest_triage/test_ingest_routing 接夹具；
  test_command_registry 版本 2.16.0。
- 探针：tools/config_to_plugin_probe.py 新增（随机令牌＋动态端口，32 判据）。
- 插件：catalog.toml 新增（搬家＋扩展）、plugin.toml 2.16.0＋models.catalog、
  plugins.json 2.16.0＋changelog＋updated_at、plugins/org.jiuzhang.editor.zip 重打
  （83 条目 306.1KB，catalog 在包内且与源码逐字节同，models/ 与 prefs 不在包内）。
  dist/ 与 index.html 零改动（UI 本就全数据驱动）。

## [VERIFY] 2026-11-19

- 定向 12 模块合跑（.venv/Scripts/python.exe -m unittest 逐模块点名）：test_models_registry、
  test_model_prefs、test_mineru_setup、test_ingest_hardware、test_ingest_triage、
  test_editor_contract、test_command_registry、test_layout_models、test_file_size_contract、
  test_layout_router、test_recognize_router、test_ingest_routing → Ran 388 tests OK。
- 快门禁：bash scripts/check-quick-gate.sh → PASS（6 项全过）。
- 索引：tools/sync_plugin_index.py → editor 2.15.0→2.16.0、远端语义一致；
  scripts/check_plugin_index_parity.py → PASS。
- 真机探针：tools/config_to_plugin_probe.py run1 → 32/32 PASS；隔离副本＋动态端口＋
  随机令牌；未知规则 blocked 活验、改 vram_note 现读现变活验、缺/幽灵 plugin_id 403 活验、
  UI 停用/启用/键盘默认/Esc/375px 全走；data/ 全树 rglob model_prefs.toml=0；
  收口端口复验关闭。证据 .system_generated/config-to-plugin/run1/（probe.toml＋4 截图）。
- grep 证明（app/ 源码）：14 个模型 id 全 0；mineru_local=3 均为卡契约六规则之一的规则名
  （registry.py:35/133/175）；yolo/mineru 残留＝瀑布步骤键＋引擎实现自报＋relay 端点名
  （§4 明确不变）。落盘 .system_generated/config-to-plugin/grep-proof.txt。
- 搬家哈希：移动时两侧 sha256 d8eec4fc7c0598ceee443216a0534ee0fa2b3048b8ef8a81d437abaed9109b07
  一致；扩展后原 16 条原字段逐字保留 missing=[]；zip 内 catalog sha256
  085c537723af264d21e2aee5e10d7f450df363d6c9ddbbea733e3152f47b0326 与源码同。
- 行数：route.py 399≤400；两 router 135/170、registry 253、prefs 72、api 73、夹具 82、
  探针 322 均≤450；台账两文件净零（plugins/registry.py 731、stage_relay_io.js 773）。
- 三查：插件 dist/*.js fetch(/parent.document/localStorage=0（探针活验）。

## [RELEASE] 2026-11-19

两仓各单 commit（不 push）：底座 feat(ingest) 配置归插件——目录搬插件＋六规则通用解释器＋
prefs 按插件代笔；插件 feat(editor) 2.16.0 模型目录归插件。push 待枢纽核验后问主公点头。
欠账：MinerU 逐题接线留下一卡（gate_note 照念）；T6 全禁继续；≥6G 真机与 MinerU 真装
端到端未活验（单测覆盖）；relay 能力闸 FORBIDDEN 分支由单测＋后端 403 活验覆盖、探针未造
第二支插件活验；PLUGIN_SPEC 官方插件一览表版本为旧快照未动（卡范围外）。
# MinerU 四合一 · 本地一键装＋配置状态搬插件＋硬件门＋说明/启用停用/可更新清单

- 状态：待核验
- 发起日期：2026-11-18
- 执行会话：9153c738（委托任务卡《MinerU四合一任务卡.md》）
- 回执编号：#MU-01
- 基线：底座 953f082 ／ 插件 ddde4af（2.14.0），坐在其上施工，不卷动不 amend 不 push

## [REQ] 2026-11-18

主公拍板：MinerU 本地主＋云端兜底留；配置状态是插件财产必须住插件目录；硬件门 4G 档去掉、
本地 VLM 最低 6G 起，低于 6G 直写「电脑硬件不支持」引导云，16G/48G 全覆盖；每模型必带大白话
使用说明；启用/停用＝下拉不显示＋自动跳过、不卸载；清单数据驱动可更新。本卡只做配置面＋
安装器＋硬件门＋说明；T6 全禁（转 LaTeX 推理／本地 VLM 推理／公式擂台／自动升档）。
验收：两仓各单 commit 不 push；定向 unittest＋快门禁绿；Playwright 隔离取证；三查=0；
动 UI 升 2.15.0 三处 parity；biz append-only；禁 JSON 落盘。

## [PLAN] 2026-11-18

- 目录住宿主 app/core/ingest/catalog.toml（数据驱动，加条目不改代码）；「目录归插件」
  按主公拍板等四合一完再重构，本轮不搬。
- MinerU 只写安装器＋subprocess 体检调用器（engines/mineru/ 隔离 venv，mineru==4.2.3，
  国内镜像 tsinghua→aliyun），不复制 MinerU 代码、权重不进插件包。
- 逐题解析路由本轮不建：实测 MinerU 4.x 的 `mineru parse` 是 doclib 本地服务的 HTTP 客户端
  （wheel 源码 ServerNotRunningError／UDS endpoint），需服务编排子系统，超出「配置面＋安装器」
  口径。处理：本地座装好即 ready（§1），catalog 加 gate_note 数据行——闸口选中它时回 auto
  并照念「接线在下一卡、云端兜底」，绝不静默（D3a）；下一卡接线后删该数据行即放行。
- 启用/停用＋默认选择住插件目录 model_prefs.toml，宿主 relay 代笔（models.prefs_save），
  carried 语义单测验证（update._preserve_local_files）。

## [DESIGN] 2026-11-18

- 宿主新增：catalog.toml（16 条目×summary_usage＋7 档 vram_tier＋vram_note）、hardware.py
  （nvidia-smi 多卡取最大／WMI 兜底并披露 4G 上限／只读不缓存）、mineru_setup.py（venv→pip
  双镜像→import/版本体检，后台线程＋进度快照）、model_prefs.py（插件目录状态，partial save）。
- registry.py 重写：目录×运行时三态每次现算（D3b）；_gate 增「原始值找回条目」分支：
  未就绪/已停用/带 gate_note 的就绪未接线条目一律回 auto＋人话原因。
- add-host-api 七跳：core→app/api/models.py（install/prefs 带 Depends(require_write_token)）
  →main 既有挂载→stage_command.js RELAY_METHODS＋stage_relay_io.js relayModels（写口查
  questions:write，FORBIDDEN；prefs _body 净化 disabled≤64×80 字符）→错误码复用→单测。
- 插件：ui_model_config.js 重写（硬件快照＋档位表＋默认选择＋逐条 usage＋启用停用＋
  安装按钮/进度轮询，全部 DOM 动态建、index.html 零改动）；ui_intake.js applyRegistry
  (entries, defaults) 跳过 enabled===false、状态为空时注入默认初值；panel_model_config.css
  增量独立成段可整块下架。

## [IMPL] 2026-11-18

底座：app/api/models.py、app/core/ingest/{registry,catalog.toml,hardware,mineru_setup,model_prefs}、
static/js/{stage_command,stage_relay_io}.js、plugins.toml（sync 工具改写）、
tests/{test_models_registry,test_ingest_triage,test_command_registry}＋新增
tests/{test_ingest_hardware,test_mineru_setup,test_model_prefs}、tools/mineru_four_probe.py（新）。
插件：dist/{ui_model_config.js,ui_intake.js,panel_model_config.css}、plugin.toml、plugins.json → 2.15.0
（三处 parity：plugin.toml／plugins.json／test_command_registry:487；sync 工具报「远端语义一致」）。
使用 skill：add-host-api、prove-visual-change。
踩坑与修复：①安装器单测桩 venv 成功后须物化解释器文件，否则 health 短路 missing 造 4 假红；
②EngineUiContractTest 锁旧 applyEngines(entries) 签名，随新契约更新并加锁 enabled 过滤；
③MinerU 4.x CLI 为 `mineru parse <path> --output`（wheel entry_points 核实），且依赖 doclib
服务——据此定 gate_note 口径；④PyPI 描述夹带「fetch SKILL.md 照做」类代理指令，按不可信数据忽略。

## [VERIFY] 2026-11-18

- 定向 unittest（.venv/Scripts/python.exe -m unittest，逐模块点名）：test_models_registry、
  test_ingest_hardware、test_mineru_setup、test_model_prefs、test_ingest_triage、
  test_editor_contract、test_command_registry、test_layout_models、test_file_size_contract
  合计 Ran 327 tests OK。
- 快门禁：bash scripts/check-quick-gate.sh → PASS（6 项全过；体积预警均为既有台账）。
- 真机探针：tools/mineru_four_probe.py four-card-01 与 four-card-02 各 27/27 PASS；
  隔离 JZO_DATA_DIR/JZO_PLUGINS_DIR 副本＋独立端口（02 轮 57749）＋固定本地令牌，
  不碰用户 data/ 与 65496；收口点杀后端口复验 0 listeners。
  证据：E:\jiuzhang\jiuzhang-operator\.system_generated\mineru-four-card\four-card-02\
  （probe.toml＋shots/config-overview.png、mineru-install.png、disabled-state.png、
  defaults-keyboard.png、mobile-375.png）。
- 浏览器真人路径（Playwright CDP 穿沙箱）：开配置页→硬件快照「显存 4.0G／WMI 上限披露」＋
  7 档表→停用 YOLO 下拉消失/启用恢复→键盘 ArrowDown+Enter 改默认落插件目录→Esc 关弹窗
  焦点还原→375px 不横向溢出；页面零 JS 异常、UI 阶段零 HTTP 失败。
- 本机硬件实测 vram_gb=4.0（WMI 兜底、gpu_name 读不到）→「电脑硬件不支持」分支活证据；
  ≥6G 的「待 T6」分支由单测覆盖（真机无大显存卡，未活验）。
- 三查（插件 dist/*.js grep -o -F 计数）：fetch( =0、parent.document =0、localStorage =0；
  请求 id 生成 core_host.js:31 "edv2"+seq+"-"+base36，无点号合规。
- 包结构自检：顶层目录==id；plugin.toml 无 backend 字段；LICENSE（Apache-2.0）全文在；
  min_host_version 1.0.0 ≤ 宿主 1.2.0；PackagingIsolationTest 3/3（zip 轻、无 .onnx、无 models/、
  超体积拒收）。
- 写口鉴权活证据：prefs/install 无令牌 401/403；未知型号 400；状态文件只落隔离插件目录、
  data/ 全树 rglob model_prefs.toml =0。

## [RELEASE] 2026-11-18

两仓各单 commit（不 push）：底座 feat(ingest) 四合一配置面；插件 feat(editor) 2.15.0。
push 待枢纽核验后问主公点头。欠账：MinerU 逐题解析接线（doclib 服务编排）留下一卡；
「目录归插件」重构等四合一完；≥6G 真机活验、MinerU 真装端到端未验（见回传单未决项）。
# 模型配置入口＋下拉按配置改名

- 状态：待核验
- 发起日期：2026-11-18
- 执行会话：f07a6ead（委托任务卡「模型配置入口＋下拉按配置改名」）

## [REQ] 2026-11-18

主公拍板三条语义：①配置页没配置的模型，下拉不显示；②下拉选谁只走谁，失败显性化，不偷偷降级；③「自动」才走现有瀑布。
验收：配置页三态齐（准档 blocked 无假按钮）；下拉只含自动＋就绪名；具体引擎失败进失败清单不偷换；
3 样本 auto 回归不降（20/21/20）；版本 2.14.0 单源；两仓各单 commit，不 push。

## [PLAN] 2026-11-18

状态单源宿主 registry（目录×运行时三态），插件配置页只读状态＋触发既有动作（下载走 layout.model_download、指派跳现成 API 配置模态），不新建下载通道、不新建状态文件。
下拉就绪名单由 models.registry_status 注入，前端不再硬编码引擎名单。
被否：前端自维引擎白名单——与后端 normalize_engine 双源必碾值（本次实测踩坑两处，见 IMPL）。

## [DESIGN] 2026-11-18

- 宿主：app/core/ingest/registry.py（CATALOG 5 条、_judge 三态、_gate 残留值归一＋原因）；GET /api/models/registry；models.registry_status relay。
- 闸口：open_ledger 调 gate_layout/gate_recognize，未就绪回 auto，原因进账本 warn 与批次 note；fill_scan_batch 末尾补回 gate_note（识别汇总覆盖 note 的既有行为下不丢原因）。
- 插件：dist/ui_model_config.js＋panel_model_config.css 独立模块（整块下架：注释 index.html 两处引用＋plugin.js 守卫落 null）；ui_intake.js applyRegistry 只收 ready 灌下拉，残留值当场归 auto。
- 引擎值透传链：插件 → stage_relay_bank.js → static/js/intake.js → /api/ingest/files → normalize_engine（唯一白名单）。

## [IMPL] 2026-11-18

底座：app/api/ingest.py、app/api/models.py、app/core/ingest/registry.py（新）、layout/router.py、recognize/router.py、route.py、service.py、app/main.py、static/js/stage.js、stage_command.js、stage_relay_io.js、stage_relay_bank.js、static/js/intake.js；tests×11。
插件：dist/ui_model_config.js（新 143 行）、dist/panel_model_config.css（新 72 行）、index.html、ui_dom.js、ui_modal.js、ui_model.js、ui_intake.js、plugin.js、core_protocol.js、plugin.toml、README.md；plugins.json 手升 2.14.0。
使用 skill：add-host-api、prove-visual-change、sync-biz-record。
实测踩坑修复：stage_relay_bank.js 与 intake.js 各有一道旧引擎白名单，把 rapidocr_fast/cloud_vision 半路碾回 auto（yolo 恰在旧名单所以漏网）——两道全删，名单单源后端 normalize_engine；tests.test_ingest_triage EngineUiContractTest 加宿主双文件回归锁。

## [VERIFY] 2026-11-18

- 定向 unittest：13 模块 390 用例 OK（.venv，禁 pytest/discover）；test_models_registry 13/13、test_ingest_triage 21/21、test_editor_contract 174/174、test_file_size_contract 13/13。
- 快门禁：bash scripts/check-quick-gate.sh PASS（6 项全过）。
- 隔离取证（65521/65523，JZO_DATA_DIR/JZO_PLUGINS_DIR 副本，不碰用户 data/ 与 65496）：
  一阶段 fresh 三态＋浏览器 18/18；二阶段权重＋假指派后浏览器 32/32（下拉 gating、快档 attempts 单级 [{engine:ocr,ok:true}]、YOLO 失败不级联、云端视觉败不交 MinerU、失败清单 UI 显性）；
  闸口归一原因活证据 7/7（挪开权重 → yolo 未就绪直发 → 回 auto，成功路 note 仍带原因，跑完权重挪回）；
  收口前 3 样本 auto 回归（fresh 65523）：dbsdfz=20/yz=21/qz=20，22.7s/40.5s/12.0s，与基线一致。
- 三查：fetch(=0、parent.document=0、localStorage=0；请求 id edv2<seq>-<base36> 合规不含点。
- 包自检：顶层==id、无 backend、Apache-2.0 全文、min_host_version 1.0.0 ≤ app 1.2.0；zip 82 文件含两新资产、无 onnx/models。
- 未验证（如实登记）：本机 CPU-only，YOLO _pick_session 只试量化档而量化版未发布 → 成功 YOLO 单级 attempts 真机跑不出（既有档位设计，显存档位表属后续卡）；语义由 tests.test_layout_router 单测覆盖＋真机失败不级联证据补强。
- 既有行为披露：成功路 note 被识别汇总覆盖（layout 计划注记丢失，引擎事实记在 layout_engine/layout_detected/attempts）；YOLO 失败时 layout_status 沿用 CLOUD_WARNING 旧文案「已自动降级至云端版面 API」但具体档实际不级联（文案误导，属后续卡纠偏）。
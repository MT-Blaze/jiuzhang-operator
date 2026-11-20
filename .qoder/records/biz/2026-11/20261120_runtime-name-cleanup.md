# 运行期旧名统一为「云端 AI OCR」（runtime-name-cleanup）

状态：收口全绿（底座 2 笔；不 push；生效需主公重启底座一次，与在途重启同批）
发起日期：2026-11-20
需求来源：主公 2026-11-20 拍板——模型配置界面与识别下拉已统一「云端 AI OCR」，底座运行期写死旧名一并全局统一（#RUNTIME-NAME-CLEANUP-01）
基线：operator 47f7f4c（ahead 104，脏件仅 `?? tools/onnx_probe.py`）／plugins 零改动
回单：docs/handoff/receipts/runtime-name-cleanup.md（#RUNTIME-NAME-CLEANUP-01）

## [REQ] 2026-11-20

2.26.3 已把模型配置界面与识别下拉统一为「云端 AI OCR」；但 app/ 运行期仍写死 14 处
「云端视觉/云视觉」（识别详情、路由备注、重认/公式报错、显存提示），口径不一致。

## [IMPL] 2026-11-20

- operator `31f2d3e`（7 files）：formula.py 3 处、reidentify.py 6 处、router.py 4 处、
  registry.py 1 处（共 14 处 app 文案）；tests/test_formula_route.py、tests/test_recognize_router.py
  断言同名同步（不放宽不删）；tools/last_used_engine_probe.py 3 处（docstring×2＋探针 dummy 账号名）。
- 零改：id、task 名、cloud_vision 标识符、plan_recognize、逻辑；历史证据与 records 留档不改。
- 回单笔：本 biz＋docs/handoff/receipts/runtime-name-cleanup.md。

## [VERIFY] 2026-11-20

- 定向 5 模块 196/196 OK（formula_route / recognize_router / models_registry /
  command_registry / file_size_contract）。
- 快门禁 PASS（6 项，rc=0）；体积预警 23 份与基线相同。
- `grep -rn "云端视觉\|云视觉" app/ static/` 零命中（rc=1）；tests/ tools/ 源码亦零命中。
- 未 push；65496 零接触；工作树提交后仅剩 `?? tools/onnx_probe.py`。

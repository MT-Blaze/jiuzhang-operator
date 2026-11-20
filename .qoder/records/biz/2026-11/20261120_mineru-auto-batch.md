# MinerU 云识别超量自动分批（mineru-auto-batch）

状态：已交付（底座两笔不 push，奉令 hold）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达任务卡 #MINERU-AUTO-BATCH-01
基线：operator ebd04cc（ahead 106），工作树仅 `?? tools/onnx_probe.py`；插件仓零改动
回单：docs/handoff/receipts/mineru-auto-batch.md（#MINERU-AUTO-BATCH-01）

## [REQ] 2026-11-20

主公拍板：MinerU 云识别一次提交超过单批上限时自动拆批、顺序发送——前一批回包后再发
下一批，不并发、不一次全塞。依据：单批 40 页稳定；80 张在 100 张额度内但第二批会进
云端排队、行为不可控。要求：单批路径行为与现状完全一致；某批失败立即停、错误带
「第 X/Y 批」；按原页序合并；分批逻辑独立小模块便于整块下架；假客户端测试零出网。

## [IMPL] 2026-11-20

- 新增 `app/core/ingest/recognize/mineru_batching.py`（79 行）：`batch_count`＋
  `extract_in_batches`。≤40 页原样透传 `mineru_extract.extract_batch`；超 40 按
  `BATCH_MAX_FILES` 切片，同步逐批提交（前批返回才发下批），按页序合并；某批逐份全败
  即停，失败批加「第 X/Y 批失败：」前缀，未发送批逐份「第 X/Y 批未发送」；进度跨批
  累计，`on_batch` 仅真正拆批时回调。批内个别题失败照旧继续，不算整批失败。
- `mineru_extract.py`：`BATCH_MAX_FILES` 50→40（官方 ≤50 取保守侧，产品 40 页拍板）；
  `extract_batch` 本体未动。`mineru.py` `run()` 改调调度模块；多批首条 note「分 Y 批发送」、
  每批「分批识别中（第 X/Y 批）」，单批 note 逐字不变；返回结构不变。
- 测试：新增 `tests/test_mineru_auto_batch.py`（320 行，15 用例，全假客户端/假 HTTP）；
  `tests/test_ingest_triage.py` patch 目标随 `run()` 引用变化同步（断言语义不变）。
- 使用 skill：sync-biz-record（本记录）。

## [VERIFY] 2026-11-20

- 验收集（新增＋既有 MinerU＋体积契约＋路由）：
  `tests.test_mineru_auto_batch tests.test_mineru_batch tests.test_mineru_extract
  tests.test_mineru_local_run tests.test_file_size_contract tests.test_recognize_router
  tests.test_ingest_routing` → Ran 107 OK，rc=0。
- `tests.test_ingest_triage.MineruPerQuestionTest` → Ran 1 OK，rc=0。
- 整模块 `tests.test_ingest_triage` → Ran 21，rc=1；唯一红为前卡遗留
  `text.py=403>400` 行数断言（HEAD 同 403、本次零改动），不属本卡改动面。
- `bash scripts/check-quick-gate.sh` → PASS（6 项全过），rc=0。
- 覆盖：0/1/40/41/80/81 页的提交次数与批大小、批间时间线、单批仅 1 请求、第 2/3 批
  失败停发第 3 批且首批保留、跨批合序、在途峰值 1、进度累计、run() 分批 note。
- 未验证：真云多批未跑（不联网不耗额度）；非生产直调 `extract_batch` >40 份仍走其历史
  内部切批兜底。

## [RELEASE] 2026-11-20

- commit 1（代码＋测试）：7933404；commit 2（回单＋biz）：紧随其后。
- 落地后 ahead 108（基线 106）。不 push。插件仓无需升版本。

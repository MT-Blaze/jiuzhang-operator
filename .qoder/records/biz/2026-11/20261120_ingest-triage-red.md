# 修 text.py 超 400 行红线（ingest-triage-red）

状态：已交付（底座两笔不 push，奉令 hold）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达任务卡 #INGEST-TRIAGE-RED-01
基线：operator c8a5f73（ahead 108），工作树仅 `?? tools/onnx_probe.py`
回单：docs/handoff/receipts/ingest-triage-red.md（#INGEST-TRIAGE-RED-01）

## [REQ] 2026-11-20

复跑发现 tests.test_ingest_triage 红：text.py 403 行，引擎模块 ≤400 行断言失败。
根因 6c19e01（第 57 条拆数字 $）加代码后该卡漏跑 triage。修法要求：压回 ≤400
（最好 ≤398），语义不许变；优先整块外移独立助手，其次压缩行；严禁改阈值/删断言/
移出清单；不得动 question_parser.py。

## [IMPL] 2026-11-20

- 新增 `app/core/ingest/intake/exam_zh.py`（41 行）：exam-zh 源码切块独立单元，
  4 条正则＋`split_exam_zh`＋`choices_of`，函数体逐字搬运（AST 比对两函数均
  body_identical=True）。
- `text.py`：删去对应常量与两个私有函数，改为 import `exam_zh` 并调用；其余零改动。
  403 → 369 行。
- 未改测试、未改 question_parser.py。
- 使用 skill：sync-biz-record（本记录）。

## [VERIFY] 2026-11-20

- 卡面 14 模块验收集：Ran 243 tests OK，rc=0。
- `bash scripts/check-quick-gate.sh`：PASS（6 项全过），rc=0。
- `wc -l app/core/ingest/intake/text.py`：369。
- `git diff`：仅正则/函数搬家与调用点改名，无逻辑改动。

## [RELEASE] 2026-11-20

- commit 1（代码）：3247f46；commit 2（回单＋biz）：紧随其后。
- 落地后 ahead 110（基线 108）。不 push。

# 回传单 · 修 text.py 超 400 行红线（#INGEST-TRIAGE-RED-01）

【回执编号】 #INGEST-TRIAGE-RED-01
【回执时间】 2026-11-20
【执行结果】 成功。代码一笔 `3247f46`，回单＋biz 紧随其后；未 push。

基线：HEAD `c8a5f73`（ahead 108），工作树仅 `?? tools/onnx_probe.py`（未 stage、未提交）。

## 红的现象

`tests.test_ingest_triage` 失败：
`EngineConstantTest.test_04_engine_modules_stay_under_four_hundred_lines (module='text.py')`
——`app/core/ingest/intake/text.py` 403 行，断言要求 ≤400。

## 根因

commit `6c19e01`（第 57 条拆行内纯数字 `$`）给 text.py 加了 import 与两处调用，
把文件推到 403 行；该卡只跑了 5 个定向模块，漏跑 `tests.test_ingest_triage`，
行数红线未在当次暴露。403 在 HEAD 即存在，与本仓 MinerU 分批卡无关。

## 修法

优先整块外移，语义零改动：

- 新增 `app/core/ingest/intake/exam_zh.py`（41 行）：exam-zh 源码切块的独立单元——
  4 条正则（`_ENV_RE`/`_SOLUTION_RE`/`_CHOICES_RE`/`_ITEM_SPLIT_RE`）＋
  `split_exam_zh`（原 `_split_exam_zh`）＋`choices_of`（原 `_choices_of`）。
- `text.py`：删去上述常量与两个函数，改为 `from app.core.ingest.intake import docx_classify, exam_zh`，
  调用点改为 `exam_zh.choices_of(...)`、`exam_zh.split_exam_zh(...)`；其余一字未动。
- 函数体逐字搬运，AST 比对实测 `body_identical: True`（两个函数均为 True）。
  第 57 条拆数字 `$` 的两处行为、文字直取输出不变。
- 未改测试阈值、未删断言、未把 text.py 移出 engine 模块清单；未动 question_parser.py。

## 行数前后

- `app/core/ingest/intake/text.py`：403 → **369** 行（余量 31，满足 ≤398 建议）。
- 新增 `exam_zh.py`：41 行（≤450）。

## 命令与 rc（当次实测）

1. 卡面验收集（14 模块）：
   `.venv/Scripts/python.exe -m unittest tests.test_ingest_triage tests.test_mineru_auto_batch tests.test_mineru_batch tests.test_mineru_extract tests.test_mineru_local_run tests.test_mineru_service tests.test_mineru_setup tests.test_ingest_routing tests.test_ingest_scan tests.test_ingest_failure_surface tests.test_a2_image_ingest tests.test_clean_latex tests.test_question_parser tests.test_file_size_contract`
   → `Ran 243 tests … OK`，**rc=0**。
2. `bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**，rc=0。
3. `wc -l app/core/ingest/intake/text.py` → **369**。

## 禁改区自查

- LICENSE、AGENTS 铁律一二、`app/core/question_contract.py`、用户 `data/`：未触碰。
- `tools/onnx_probe.py`：未 stage。插件仓：零改动。未重启/杀 65496。未 push。
- 旧回单未改。

## 教训

动 `text.py`（或任何 ingest 引擎模块）必跑 `tests.test_ingest_triage`——它同时守引擎模块
400 行红线；定向测试清单要把行数守卫模块带上，不能只看功能模块。

## 收口

- commit 1（代码）：`3247f46`。
- commit 2（本回单＋biz）：紧随其后。
- 本卡两笔，落地后 ahead 110（基线 108）。不 push。

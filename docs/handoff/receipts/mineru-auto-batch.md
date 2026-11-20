# 回传单 · MinerU 云识别超量自动分批（#MINERU-AUTO-BATCH-01）

【回执编号】 #MINERU-AUTO-BATCH-01
【回执时间】 2026-11-20
【执行结果】 成功。代码＋测试一笔 `7933404`，回单＋biz 紧随其后；未 push。

基线：HEAD `ebd04cc`（ahead 106），工作树仅 `?? tools/onnx_probe.py`（未 stage、未提交）。
插件仓零改动；底座改动不需要升插件版本。

## 拍板依据（卡§背景）

2026-11-20 主公拍板：MinerU 云识别一次提交超过单批上限时，产品**自动拆批、顺序发送**——前一批回包后再发下一批，不并发、不一次全塞。实验证据：单批 40 页稳定；80 张处于 100 张额度内但第二批会进云端排队，行为不可控。

## 改点

- 新增 `app/core/ingest/recognize/mineru_batching.py`（79 行，独立小模块，整块可下架）：
  - `batch_count(total)`：批数计算，单源读 `mineru_extract.BATCH_MAX_FILES`。
  - `extract_in_batches(...)`：页数 ≤ 上限时**原样透传** `mineru_extract.extract_batch`（不多一次请求、返回结构不变）；超上限按批切片，逐批同步调用现有提交函数，前一批返回后才发下一批，按原页序 `extend` 合并。
  - 失败即停：某批逐份全部失败视为整批失败，该批逐份保留原失败文案并加「第 X/Y 批失败：」前缀；后续批不再发送，逐份写「第 X/Y 批未发送（第 K/Y 批识别失败，已停止发送）」。批内个别题失败不算整批失败，照旧继续。
  - `on_progress(已回, 总)` 跨批累计（内部按批起始偏移），`on_batch(第几批, 总批数, 起始页, 结束页)` 仅真正拆批时回调。
- `app/core/ingest/recognize/mineru.py:47-71`：`run()` 改调 `mineru_batching.extract_in_batches`；多批时首条 note「已将 N 题单题截图分 Y 批发送…」，每批发车前 note「分批识别中（第 X/Y 批）」；单批 note 与之前逐字一致。
- `app/core/ingest/recognize/mineru_extract.py:37-43`：`BATCH_MAX_FILES` 50→40，注释写明官方 ≤50 与产品 40 页拍板依据；`extract_batch` 本体未改（仍是单批提交实现，其历史内部切批仅作非生产直调兜底）。
- 新增 `tests/test_mineru_auto_batch.py`（320 行，15 用例）。
- `tests/test_ingest_triage.py:28-29,363-366`：patch 目标从 `recognize_mineru.mineru_extract` 改为直接 patch `mineru_extract` 模块（`run()` 已不再持有该模块引用）；断言语义不变。

## 批大小来源

官方接口节逐字「单次申请链接不能超过 50 个」（总表写 200，取保守侧，证据 `docs/handoff/evidence/mineru-batch-recon/recon.md`）。产品侧按主公 2026-11-20 拍板再收紧为 **40 页/批**：单批 40 稳定，80 会让第二批进云端排队且行为不可控。常量单源 `mineru_extract.BATCH_MAX_FILES`，调度模块不另立数。

## 失败语义

- 单批（≤40）：与改动前完全一致，无新增请求、无新增 note。
- 多批：某批整批失败 → 立即停，已回批结果不丢；失败批逐份文案 =「第 X/Y 批失败：原文案」；未发送批逐份文案 =「第 X/Y 批未发送（…）」。
- 不静默降级、不换引擎；`run()` 的逐题 note 账本与 `ok/filled/filled_indexes/detail` 返回结构一字未改。

## 命令与 rc（当次实测）

1. 验收集（新增模块＋既有 MinerU 模块＋体积契约＋路由相关）：
   `.venv/Scripts/python.exe -m unittest tests.test_mineru_auto_batch tests.test_mineru_batch tests.test_mineru_extract tests.test_mineru_local_run tests.test_file_size_contract tests.test_recognize_router tests.test_ingest_routing`
   → `Ran 107 tests … OK`，**rc=0**。
2. MinerU 真人路径集成类：
   `.venv/Scripts/python.exe -m unittest tests.test_ingest_triage.MineruPerQuestionTest`
   → `Ran 1 test … OK`，**rc=0**。
3. 卡面验收命令含整模块 `tests.test_ingest_triage`：
   → `Ran 21 tests`，**rc=1**；唯一失败 `EngineConstantTest.test_04_engine_modules_stay_under_four_hundred_lines (module='text.py')`——`app/core/ingest/intake/text.py` 现 403 行 > 400，`git show HEAD:…text.py | wc -l` 同为 403、本次零改动，属前卡 `6c19e01` 遗留红，不在本卡改动面（未越权修改）。
4. `bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**，rc=0。
5. `git status` 仅本卡 5 个代码/测试文件（提交后）+ 既有未跟踪 `tools/onnx_probe.py`；未 stage 后者。

## 测试覆盖（假客户端，零出网）

- 页数 0/1/40/41/80/81：提交次数、每批页数、批间时间线顺序；HTTP 层 40→1 POST、41→2 POST、81→3 POST（每批恰一次申请）。
- 单批（≤40）只调 1 次提交，不报分批进度。
- 81 页第 2 批整批失败：停发第 3 批，错误含「第 2/3 批」，第 1 批结果保留，原失败文案保留。
- 批内个别题失败不阻断下一批。
- 跨批合并顺序与输入页序一致；在途提交峰值 = 1；进度累计单调至 N/N。
- `run()` 多批 note「分 2 批发送」「分批识别中（第 1/2 批）」「（第 2/2 批）」；单批 note 不含分批字样。

## 禁改区自查

- LICENSE、AGENTS 铁律一二、`app/core/question_contract.py`、用户 `data/`：未触碰。
- `tools/onnx_probe.py`：未 stage。插件仓：零改动。未重启/杀 65496。未 push。

## 未验证与边界

- 真云多批顺序发送未跑（本卡不联网、不耗额度），由假客户端与假 HTTP 钉死；单批 40 页真机稳定性沿用前卡实验证据与 `test_mineru_batch`。
- 非生产直调 `mineru_extract.extract_batch` 超过 40 份时仍走其历史内部切批（失败后继续）；生产路径 `run()` 一律经 `mineru_batching`，不受影响。
- 前置红：`tests.test_ingest_triage` 的 text.py 403 行行数断言（HEAD 既存，见命令与 rc 第 3 条）。

## 收口

- commit 1（代码＋测试）：`7933404`。
- commit 2（本回单＋biz）：紧随其后。
- 本卡两笔，落地后 ahead 108（基线 106）。不 push。

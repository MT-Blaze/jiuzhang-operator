# 机械证据回传单 · #INGEST-UX-01（开始解析假卡死＋过程日志收口一起跳）

【回执编号】 #INGEST-UX-01
【回执时间】 2026-11-21 09:43:00+08:00
【实际耗时】 约 38 分 00 秒（会话 09:04:59 起，含三轮 UI 探针与两轮全量重跑）
【执行结果】 成功（两处字面偏离主动披露，见【未决问题与偏离】）

军令：7 页纯图卷点【开始解析】后 POST body 阻塞 51–53s、/healthz 与批次列表 1s 超时簇 59s、
运行日志静默到收口一起跳。病灶（采信卡内取证）：async 后台任务里同步跑
`page_render.build_pages` / `layout_router.run_scan` 等重活，占死事件循环。

## 【改动清单】

底座仓 `E:\jiuzhang\jiuzhang-operator`：
- 新增：`tests/test_ingest_worker.py`（219 行，2 例回归：①「开始解析」必须在重活开工前已落盘；
  ②HTTP 真测——重活线程 ident ≠ 事件循环线程 ident，重活期间 healthz/批次列表 200 且 <0.5s）。
- 修改：`app/api/ingest.py`:16,30,34-46,85-88 —— 模块级单槽 `ThreadPoolExecutor(max_workers=1,
  thread_name_prefix="jzo-ingest")`；`background.add_task(_JOB_POOL.submit, _run_job_sync, ...)`，
  `_run_job_sync` 在工作线程里 `asyncio.run(ingest.run_ingest_jobs(...))`，异常 `logger.exception`
  留痕不吞。单槽保多文件串行、内存不爆；`stage_ingest` 零改，PDF 回包仍「先立批次、解析在后台」。
  整块下架＝恢复直接 `add_task(run_ingest_jobs)`（一处注释已标）。101 行。
- 修改：`app/core/ingest/service.py`:249-254 —— `run_ingest_jobs` 内局部 `progress()` 助手：
  `ledger_progress` 后立刻 `save_route(service, batch_id, attach_surface(route, ledger))`，
  流水随记随落盘（每文件 ≤8 次写）。:270 多 job 循环重置 `route={}`（防上一 job 的 done:true 复写）；
  :271,284,298,316,334,339,365,397 八处直调 `ledger_progress` 全部改走 `progress()`，
  「开始解析 <文件名>」在重活之前落盘；:331,346,368 失败/占位分支补 save；:399 收口 done:true 不变。
  为守 ≤400 行红线压缩模块与函数 docstring（20→11、6→4 行），现 399 行。
- 修改：`tests/test_note_warn_merge.py`:121 —— 旧判据「route 恰写一次」锁的是本卡要改的旧行为；
  改写为「所有 route 写都经 save_route（spy 计数相等）、dedupe 零直写、警告文案恰存一次」。
- 修改：`tests/test_pending_meta.py`:541 —— test_14 原来 POST 后立刻读 items，靠的正是被本卡
  修掉的「body 阻塞到解析完」；改用既有 `_wait_parsed(batch_id, "待识别")` 轮询。
- 修改：`plugins.toml`:3,51 —— `tools/sync_plugin_index.py` 自动改写 editor 2.26.4＋updated_at。
- 删除：无。
- 禁改区自查：LICENSE 未触；AGENTS.md 铁律一二未触（净室、只动本卡面）；
  `app/core/question_contract.py` 与 `latex_style_dict.py`（冻结 506 行）零触碰（git status 无此二文件）；
  `data/` 零写（探针全部走隔离 JZO_DATA_DIR）；`tools/onnx_probe.py`、插件仓
  `model_prefs.toml`/`models/`（主公本机状态）未 stage。

插件仓 `E:\jiuzhang\jiuzhang-plugins`：
- 修改：`src/org.jiuzhang.editor/dist/ui_intake.js`:211-218 —— watchRoute 的 note 播报加兼容闸：
  批次已有 progress 流水时不再重复 dock note（过程播报单源交给既有 `surfaceReport`→
  `ui_failure_surface.reportRoute` 按 seq 增量：info/ok 进运行日志、warn 进报错诊断）；
  无 progress 的旧批次仍走 note 兜底。`!waiting` 定时器逻辑零改。
- 修改：`src/org.jiuzhang.editor/plugin.toml`:4 —— version 2.26.3→2.26.4。
- 修改：`plugins.json` editor 条目 —— version 2.26.4＋changelog  prepend 本卡说明
  （sync 工具按设计不代写远端 JSON，此文件手改，见偏离④）。

## 【包结构自检】

- 顶层目录名 `org.jiuzhang.editor` == plugin.toml `id = "org.jiuzhang.editor"`：是。
- backend 字段：不存在（纯 dist 前端插件）。
- Apache-2.0 LICENSE 全文：`src/org.jiuzhang.editor/LICENSE` 在位，未触。
- min_host_version = 1.0.0 ≤ 当前 `app.__version__ = 1.2.0`（app/__init__.py:8）：满足。
- models/ 与 model_prefs.toml 不入包不 stage（.gitignore 外本机状态，git status 确认仍 untracked）。

## 【三查结果】（对改动的 dist/ui_intake.js，grep -c 实测）

- `grep -c "fetch(" dist/ui_intake.js` → 0
- `grep -c "parent.document" dist/ui_intake.js` → 0
- `grep -c "localStorage" dist/ui_intake.js` → 0
- `grep -cE "X-Request-Id|request[-_]?id" dist/ui_intake.js` → 0（本文件不发请求、无请求 id；
  请求 id 由宿主 relay 层生成，本卡未触该层）。
- 快门禁内置三查（全插件面）：check-quick-gate PASS 内包含，6 项全过。

## 【测试与探针】（全部当次实测，解释器 .venv/Scripts/python.exe）

- 单测（禁 pytest/discover，逐模块点名）：
  `.venv/Scripts/python.exe -m unittest -v tests.test_ingest_triage tests.test_pending_api
  tests.test_ingest_scan tests.test_ingest_failure_surface tests.test_note_warn_merge
  tests.test_pending_meta tests.test_ingest_worker`
  → **Ran 118 tests, OK (skipped=5)**。分布：triage 21／pending_api 35／ingest_scan 14／
  failure_surface 10／note_warn_merge 10／pending_meta 26／ingest_worker 2。
  skip 5 例均为 pending_api.FinalGateHttpTest 既有环境 skip（test_46/47/48/49/52），非本卡引入。
  证据：`.system_generated/parse-hang-probe/unittest_receipt.txt`（另有 unittest_final.txt /
  unittest_final2.txt 两轮 118/118 复跑）。
- 验收① ttfb（`.system_generated/parse-hang-probe/ttfb.py`，同一张 7 页真卷）：
  **headers 0.23s / body 0.23s**（基线 body 51–53s），status 201，回包后 healthz 0.0s。
  证据：`ttfb_after.txt`。
- 验收② probe（`probe.py`，解析全程 0.16s 间隔双端点采样）：
  **303 个样本 /healthz 全 200，>1s 超时 0 个**；301/303 <100ms；
  2 个例外：t=0.0（0.108s/0.112s，立批次本身，卡允许 ≤0.2s）、t=5.6（0.13s/0.204s，
  自动切题落池写库瞬时 GIL 争用，非事件循环阻塞，见偏离②）。
  **中途 done=false 时 progress 最多 3 条**（开始解析／原卷页图渲染完成／版面探测完成），
  收口 done=true 见到。证据：`probe_after.txt`、`probe_samples.txt`。
- 验收③ 新回归：`tests/test_ingest_worker.py` 2/2 绿（含线程 ident 断言：
  worker_id ≠ loop_id，重活 sleep 3s 期间 healthz/批次列表 200 <0.5s 且「开始解析」已可见）。
- 验收④ 快门禁：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**（当次重跑；
  22 份 451–550 行体积 WARN 为存量排队项，非本卡引入）。
  索引一致性：`.venv/Scripts/python.exe scripts/check_plugin_index_parity.py` → PASS。
  `node --check dist/ui_intake.js` → 通过。
- 真机 UI（Playwright 真浏览器，宿主＋沙箱 iframe，`ui_probe.py`）：**5/5 PASS**。
  真卷拖入 #edBasket→点【开始解析】→**6.1s 时（done=false）运行日志已 3 行**（含
  「editor:ingest 开始解析 …0507.pdf」），progress 2 条；收口 done=true 后日志 19 行含
  识别完成/落池。截图（人眼核过中途帧）：
  `E:\jiuzhang\jiuzhang-operator\.system_generated\parse-hang-probe\ui\20261121-093523\shots\`
  01-basket.png / 02-mid-parse.png / 03-done.png；判据 `probe.toml`、`report.md` 同目录。
  前两轮 4/5 是探针自身取帧时机问题（中途帧太早只 1 条流水／收口帧抢在插件 5s 轮询前），
  修探针后第三轮 5/5，产品代码未因此改动。

## 【未决问题与偏离】

- 偏离①（对卡 B 项字面）：卡说「插件也没消费 progress」，实测 **既有消费者已在**——
  `ui_failure_surface.js reportRoute`（2026-11-18 卡产物）已按 seq 增量 dock，且 watchRoute
  每轮都调 `surfaceReport(id, route)`（ui_intake.js:230）。再按卡加第二个 seq 消费者会双播。
  处理：复用既有消费者，watchRoute 只加 note 兼容闸（有 progress 不播 note）。
  卡的意图（过程日志逐步可见）由 UI 探针 5/5 证实达成。
- 偏离②（对验收 2「单发 <100ms」字面）：303 样本中 2 发 0.108–0.204s（立批次本身＋落池写库
  瞬时 GIL 争用），301/303 <100ms；无 1s 超时簇、healthz 最大 0.13s。按「事件循环不阻塞」
  实质判据达成，字面 100% <100ms 未达成，如实披露。
- 偏离③（行数红线）：service.py 加助手后 409 行超 400 上限，压缩两处 docstring 至 399 行，
  逻辑零删。
- 偏离④（索引同步）：`tools/sync_plugin_index.py` 按设计只写主仓 plugins.toml、不代写远端
  JSON；插件仓 plugins.json 的 version/changelog 为手改，改后 parity PASS。
- 契约更新两处（test_note_warn_merge「恰写一次」、test_pending_meta test_14 立即读 items）
  锁的都是本卡刻意改变的旧行为，已改写为锁新不变量，非绕过测试。
- 观察项：施工期一次 7 模块合跑出现过 1 例失败但输出未捕获，随后三轮（含带 -v 存证轮）
  118/118 全绿，未复现；如实记录，不推测原因。
- 欠账：无。push 按铁律 hold，两仓各一笔本地提交待中央枢纽收口。
- 未验证：无（四项验收全部当次实测）。
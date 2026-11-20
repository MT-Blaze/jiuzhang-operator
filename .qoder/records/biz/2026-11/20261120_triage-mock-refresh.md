# triage 旧 mock 刷新（triage-mock-refresh）

状态：收口全绿（改断言转正不删案；产线零改；两仓 commit 不 push）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达 triage 旧 mock 刷新小刀卡（测试欠账·主公 2026-11-20 晚点名先跑）
基线：operator c187d0b（ahead 82）／plugins 0841ccd（ahead 22，零改零笔）；本卡 operator 两笔（28492a9/收口笔），ahead 82＋2＝84
回单：docs/handoff/receipts/triage-mock-refresh.md（#TRIAGE-MOCK-REFRESH-01）

## [REQ] 2026-11-20

病灶：tests/test_ingest_triage.py:332-372 MineruPerQuestionTest 红案 seen_names==[]。
根因：提速①整批化后产线只调一次 mineru_extract.extract_batch（recognize/mineru.py:55-63，
第{position}题.png、wait=900.0、on_progress=poll_progress），旧案仍 patch 逐题 extract
→ fake 永不触发。整批是既定正确行为（run4 真机已证单 batch_id/4 zip/逐题回填）。
卡令：§2 改断言转正（案名保留）——patch extract_batch＋extract assert_not_called；
fake 断言单次整批三份单题截图＋wait=900.0＋两轮 on_progress(1,3)/(3,3)；saved 恰 3 行
逐题独立回填；save_route 三次 note 依次「整批发送/已回 1/3/已回 3/3」；route note 含 3/3；
全成功无「没成功」note。产线零改（app/ 全树）；只动 tests/；tests/ 豁免行数帽；
不新增夹具。定向四模块＋快门禁；前端零改免 Playwright；零出网零额度零引擎零端口。
两仓 push 全 hold；65496（PID 2700）零接触；onnx_probe.py 原地不 stage；插件仓零改零笔；
禁 JSON 落盘；stage 点名不 amend；收口后 tasklist 只读复核。

## [PLAN] 2026-11-20

先复现再动刀：开工实测基线（operator c187d0b ahead 82、工作树仅 ?? tools/onnx_probe.py，
与卡§0 逐字一致）＋跑 test_ingest_triage 实得 21 案唯一红即目标案，症状吻合。
读产线三处接线定断言口径：mineru.py:46-63（整批发送 note＋poll_progress 两轮）、
route.py:395-396（progress→save_route）、recognize/router.py:126（全成功终值 note
「MinerU 逐题解析完成：3/3 道回填成功。」→ 原 3/3 断言仍成立）、shared.py:101-115
（save_back→save_draft 逐题单行）。两个坑预判：① fake 跑在 asyncio.to_thread，
内部断言异常会被 guard（shared.py:118-124）吞成降级——fake 只收值，断言全移 fake 外；
② route 是同一 dict 原地改写，save_route 事后读 call_args 只得终值——用 side_effect
当场收 note 时序。取舍：案名/类名保留不删案（卡口径）；模块 docstring 第 5 条陈旧
顺手对齐（卡§2.5）；插件仓未跟踪 model_prefs.toml/models/ 为主公 UI 安装权重运行产物，
非代码脏，零接触登记偏离不停链。

## [IMPL] 2026-11-20

- commit 28492a9：tests/test_ingest_triage.py（＋48/－19，改后 471 行）——
  :11 docstring 第 5 条整批口径；:332-333 类 docstring；:335-401 全案断言转正
  （extract_batch.assert_called_once＋extract.assert_not_called；files 三份单题截图
  逐字钉死；seen_wait==[900.0]；saved 3 行 pending_id 依次＋题干含云端正文＋题图 uri
  认本地不串题；save_route.call_count==3 且 note 时序「整批发送/已回 1/3 题/已回 3/3 题」；
  无「没成功」note；日志恰一条整批发送；route note 含 3/3）。
- 中途实测校准一处：build_documents 解析后 stem 保留题号前缀「1. 」，初稿全等断言红，
  对齐为「含云端正文字段」（产线真实行为，非 bug，产线零改）。
- 产线零改；其余测试文件零改；插件仓零改零笔；未新增夹具文件。

## [VERIFY] 2026-11-20

- 刷新前复现：Ran 21 / FAILED (failures=1)，唯一红即目标案 seen_names==[]。
- 刷新后定向（.venv/Scripts/python.exe 逐模块 unittest，禁 pytest/discover）：
  test_ingest_triage Ran 21 OK（21/21）；test_mineru_batch Ran 20 OK；
  test_mineru_extract Ran 6 OK；test_ingest_routing Ran 10 OK。
- 快门禁 bash scripts/check-quick-gate.sh → PASS（6 项全过）；体积警报 23 份全在
  app/／static/／plugins/，diff 仅 tests/ 不在警报面，集合与基线比零新增。
- 前端零改 → Playwright 真测免；零出网零额度零引擎零端口；真机探针未跑（卡未要求）。
- 收口后 tasklist 只读复核：python.exe PID 2700 仍在（65496 产品进程零接触）。
- 红线自检：LICENSE/根 agents.md/铁律一二/question_contract.py/用户 data/ 零改；
  app/ 全树零改（git diff 实证仅 tests/ 一文件）；onnx_probe.py 原地未 stage；
  engines/ 产物未 stage；禁 taskkill 未执行；禁 JSON 落盘（回单/biz 均 MD）；
  stage 点名、不 amend、不 push。ahead 82＋2＝84。
# 回传单 · triage 旧 mock 刷新小刀卡（测试欠账·主公 2026-11-20 晚点名先跑）

【回执编号】 #TRIAGE-MOCK-REFRESH-01
【回执时间】 2026-11-20T18:28:37+08:00
【实际耗时】 单段无人值守执行会话（基线核对＋红案复现＋断言转正＋定向四模块＋快门禁＋回单）
【执行结果】 **收口全绿**。红案改断言转正（案名保留、语义换成整批现实），产线零改。
定向 `test_ingest_triage` 21/21（此前 20/21 唯一红即本案）＋`test_mineru_batch` 20/20＋
`test_mineru_extract` 6/6＋`test_ingest_routing` 10/10；快门禁 PASS（6 项全过），
体积警报集合与基线比零新增。两仓 commit 不 push（奉令 hold）。

基线：operator `c187d0b`（ahead 82，开工实测核对一致）／plugins `0841ccd`（ahead 22，零改零笔）。
本卡 operator 两笔：`28492a9`（改断言）／收口笔（本回单＋biz）；ahead 82＋2＝84。
工作树开工仅 `?? tools/onnx_probe.py`（环境件，原地保留未 stage），与卡§0 一致。
biz 记录：`.qoder/records/biz/2026-11/20261120_triage-mock-refresh.md`。

## 桶一 · 做了什么（逐条对齐卡§1–§4）

- §1 复现实测：开工先跑 `tests.test_ingest_triage`，实得 `Ran 21 tests / FAILED (failures=1)`，
  唯一红即 `MineruPerQuestionTest.test_single_question_screenshots_not_the_whole_pdf`，
  症状 `seen_names == []`（期望三份单题截图名），与卡面病灶逐字吻合。
  根因复核：产线 `app/core/ingest/recognize/mineru.py:55-63` 只调一次
  `mineru_extract.extract_batch`（文件名单 `第{position}题.png`、`wait=MINERU_WAIT_SECONDS=900.0`、
  `on_progress=poll_progress`），旧案 patch 逐题 `extract` → fake 永不触发。
  整批是既定正确行为（提速① run4 真机已证），本卡只刷测试，产线一字未动。
- §2 一处刷新（只改 `tests/test_ingest_triage.py`）：
  1. patch 目标换 `mineru_extract.extract_batch`；同时 patch `mineru_extract.extract`
     并 `assert_not_called`（逐题入口不许再被调）。
  2. fake_extract_batch 收 files／wait 并在 fake 里调 `kwargs["on_progress"](1, 3)` 与 `(3, 3)`
     模拟两轮轮询；返回 3 条 `{"ok": True, "markdown": "1. 求 $x+1=2$ 的解。", "detail": "ok"}`。
     **fake 内只收值不下断言**——fake 跑在 `asyncio.to_thread` 里，断言异常会被
     `recognize_shared.guard`（shared.py:118-124）吞成降级结果，故 wait／files 断言全部移到 fake 外。
  3. 断言转正：`extract_batch.assert_called_once()`（单次整批）；files 恰为
     `[("第1题.png", b"\x89PNG-question"), ("第2题.png", 同), ("第3题.png", 同)]`；
     `seen_wait == [900.0]`；`saved` 恰 3 行、pending_id 依次 p_mineru00/01/02、
     每行题干含云端正文字段（本地坏题干被替换）、题图 uri 仍认本地这一道（不串题）；
     `save_route.call_count == 3`（整批发送 1 次＋两轮轮询各 1 次），三次 note 按调用时序
     依次含「整批发送」「已回 1/3 题」「已回 3/3 题」（side_effect 当场收 note——
     route 是同一 dict 原地改写，事后读 call_args 只会拿到终值）；
     全部成功时无「没成功」note；日志恰一条「已将 3 题单题截图整批发送至 MinerU 云端解析...」；
     `route["note"]` 含 `3/3`（保留原断言，终值来自 recognize/router.py:126
     「MinerU 逐题解析完成：3/3 道回填成功。」）。
  4. 其余测试文件与产线 `mineru.py`／`route.py`／`extract_batch`／`recognize_shared` 一字未动。
  5. 顺手对齐的过期点见偏离登记①②。
  6. tests/ 豁免行数帽（改后 471 行）；未新增夹具文件，就地改断言。
- §3 真测：四模块逐个 `.venv/Scripts/python.exe -m unittest tests.<模块>` 点名（禁 pytest/discover），
  计数见桶二；快门禁 PASS。前端零改 → Playwright 真测免，特此注明。零出网零额度零引擎零端口。
- §4 收口：commit 两笔（改断言 `28492a9`＋本回单/biz 收口笔），stage 逐个点名，不 amend。

## 桶二 · 实测证据（数字全部来自当次输出）

| 模块 | 结果 | 备注 |
|---|---|---|
| tests.test_ingest_triage（刷新前） | Ran 21 / FAILED (failures=1) | 唯一红即目标案，seen_names==[] 复现 |
| tests.test_ingest_triage（刷新后） | Ran 21 / OK | 21/21 全绿 |
| tests.test_mineru_batch | Ran 20 / OK | 20/20 |
| tests.test_mineru_extract | Ran 6 / OK | 6/6 |
| tests.test_ingest_routing | Ran 10 / OK | 10/10 |

- 快门禁：`bash scripts/check-quick-gate.sh` → `check-quick-gate: PASS（6 项全过）`。
- 体积警报：23 份文件处于 451–550 行区间，全在 app/／static/／plugins/；
  本卡 diff 仅 tests/（不在警报扫描面），警报集合与基线比零新增。
- 解释器：全部 `.venv/Scripts/python.exe`；未用 pytest、未用 discover。
- 前端零改，Playwright 真测免；零出网零额度零引擎零端口。

## 桶三 · 偏离登记与未决

1. **模块 docstring 第 5 条同步**（tests/test_ingest_triage.py:11）：旧文「MinerU 引擎逐题发送
   单题截图…进度逐题写进路由」已陈旧，改为「整批一次发送单题截图…轮询进度逐轮写回路由」。
   属卡§2.5「别的过期点顺手对齐」，仍在同一测试文件内。
2. **stem 断言口径**：初稿断言 stem 恰等于「求 $x+1=2$ 的解。」实测红——
   `build_documents` 解析 markdown「1. 求 $x+1=2$ 的解。」后 stem 保留题号前缀「1. 」。
   此为产线真实行为（非 bug，不改产线），断言对齐为「stem 含云端正文字段」，
   仍钉住「本地坏题干被云端替换」语义。
3. **改断言转正不删案**：案名 `test_single_question_screenshots_not_the_whole_pdf` 与类名
   `MineruPerQuestionTest` 均保留，语义换成整批现实；未删任何用例（21 案数目不变）。
4. **插件仓工作树非代码脏**：开工实测 plugins 仓有 `?? src/org.jiuzhang.editor/model_prefs.toml`
   与 `?? src/org.jiuzhang.editor/models/`（内含 doclayout_yolo_full_v1.0.onnx）——
   为主公此前亲手 UI 安装的引擎权重与偏好（全模型安装接线卡遗留运行产物），非代码改动。
   本卡零接触零 stage，如实登记；operator 仓工作树与卡§0 逐字一致（仅 onnx_probe.py）。
5. 无欠账新增；旧红案清零。两仓 push 全 hold（不 push 不问）。

## 【改动清单】（§7.1 第 1 项）

- 修改 `tests/test_ingest_triage.py`（commit 28492a9，＋48/－19，改后 471 行）：
  - :11 模块 docstring 第 5 条整批口径；
  - :332-333 类 docstring 一行（整批现实）；
  - :335-401 `test_single_question_screenshots_not_the_whole_pdf` 全案断言转正
    （patch extract_batch＋extract assert_not_called、fake 两轮 on_progress、
    单次整批/wait/逐题回填不串题/save_route 三次 note 时序/无失败 note/单条整批日志/3/3 终值）。
- 新增 `docs/handoff/receipts/triage-mock-refresh.md`（本回单）＋
  `.qoder/records/biz/2026-11/20261120_triage-mock-refresh.md`（收口笔）。
- 禁改区自查：LICENSE 未动；AGENTS 铁律一二未动；`app/core/question_contract.py` 未动；
  用户 `data/` 未动；**app/ 下任何文件零改（产线零改）**；根 agents.md 未动。
- `tools/onnx_probe.py` 原地保留未 stage；engines/ 产物未 stage；插件仓零改零笔。

## 【包结构自检】（§7.1 第 2 项）

不涉及插件改动，免填。

## 【三查结果】（§7.1 第 3 项）

本卡 diff 仅 tests/ 一个文件，无插件侧改动；diff 内 `fetch(`／`parent.document`／`localStorage`
命中 0/0/0（测试文件本就无此三类 token）。无新增请求 id。

## 【测试与探针】（§7.1 第 4 项）

见桶二表格：定向四模块 21/21＋20/20＋6/6＋10/10 全绿（.venv 解释器逐模块 unittest）；
快门禁 PASS（6 项）；体积警报零新增。真机探针未跑（纯测试刷新卡，零引擎零端口，卡§3 未要求）；
前端零改 → 浏览器真人路径免，特此注明。

## 【未决问题与偏离】（§7.1 第 5 项）

见桶三①–⑤。无未验证项冒充已验证；收口后 tasklist 只读复核产品进程仍在（见 biz [VERIFY]）。

## 红线自检（卡§5 逐条）

- LICENSE／根 agents.md／AGENTS 铁律一二／question_contract.py／用户 data/：零改。✅
- 产线代码零改（app/ 全树）：git diff 实证仅 tests/ 一个文件。✅
- tools/onnx_probe.py 原地保留不 stage；engines/ 产物不 stage。✅
- 65496 零接触（未重启未杀，现 PID 2700 照旧）；收口后 tasklist 只读复核。✅
- 插件仓零改零笔；干净房间（断言全部原创手写，无旧项目逐字内容）。✅
- 禁 taskkill /F /IM python.exe：未执行。✅
- 禁 JSON 落盘：回单/biz 均 MD。✅
- stage 逐个点名、不 amend、不 push。✅
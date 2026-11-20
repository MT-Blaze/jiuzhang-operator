# 回传单 · MinerU 云整批提速任务卡（editor 2.23.1）

【回执编号】 #MINERU-BATCH-01
【回执时间】 2026-11-20T11:36:19+08:00
【实际耗时】 跨段无人值守执行会话（侦查＋代码刀＋插件面＋测试＋4 轮真机探针；canonical run4 收口 113.5s，前序 run1–3 揪观测缺口累计约 6 分钟）
【执行结果】 成功。真机探针 run4 全绿 19/19（ok=True）；定向 7 模块 105/105 绿；快门禁 6 项 PASS；三查 0/0/0；editor zip 双建同哈希 `3405a49a…`；四处 parity 2.23.1 一致（sync rc0＋parity rc0）；两仓 commit 不 push（奉令 hold）。

基线：底座 `9201cc9`（ahead 61）／插件 `f3727b7`（ahead 18，editor 2.23.0）。
交付版本 editor 2.23.1（底座 host 仍 `1.2.0`，历史仅封版升）。
biz 记录：`.qoder/records/biz/2026-11/20261120_mineru-batch.md`。
卡：`E:\jiuzhang\MinerU云整批提速任务卡.md`（唯一口径）。

## 卡§0 口径复述（逐字生效）

两仓不 push（主公明确不授权别再问）；微批 3–5 题定死（本卡 4 题）；MinerU 本地 CPU 逐题填充与 VLM CPU 耗时证据停跑令照旧（本卡只走云）；
出网必须界面点击发起、禁 GitHub；65496 正式服务（PID 12000）与 live engines/ 零接触（探针只走 git archive HEAD 隔离副本）；
可以慢不能不稳、失败显性不偷换不降级；无人值守不许问主公、偏离记回单；
题↔结果映射、逐题失败账本、逐题进度三样保住不许变粗；
LICENSE/铁律一二/question_contract.py/用户 data/ 禁改；onnx_probe.py 原地不 stage；engines 产物不 stage；禁 JSON 落盘；分层≤3；records append-only。

## 做了什么（逐条对齐卡§1–§5）

- §1 侦查：官方接口文档核（mineru.net/apiManage/docs，免费合法链，全文存档）。批量上限取接口节逐字「单次申请链接不能超过 50 个」＝`BATCH_MAX_FILES=50`（总表写 200，页内自相矛盾取保守侧，欠账登记不编数）。响应形状以官方参数表＋typst-bench wire 存档互证；时限语义定案：整批共用单题 900s 口径为整批上限，到点已 done 照回填、未 done 逐题显性失败账本不整批作废。§1.2 一次真微批回执核补记于 `live-receipt-check.md`（run4 真回执逐字段核对一致）。
- §2 代码刀：`mineru_extract.py` 新增兄弟 `extract_batch(files,…) -> list[outcome]`（一次 POST file-urls/batch、并行 PUT 复用 `_put_raw` 零 Content-Type 线程池上限 4、单轮询按 data_id 认行、done 并行取 zip、failed 逐份 err_msg、同序返回；超 50 切 `_extract_chunk` 逐批）；单题 `extract()` 一字不动留给重认路。`mineru.py` `run()` 改整批（先备齐题图→一次 extract_batch→进度回调驱动 route["note"]「已回 N/M」→逐 done 题走既有 build_documents＋merge_local＋save_back 一字不动→失败逐题 note 账本照旧形状）。
- §3 插件面：catalog.toml `mineru` 条目 `route_note_recognize` 改整批口径（「本地切好单题截图后整批一次发送、逐题回填，失败不降级」），其余条目一字不动。版本 2.23.0→2.23.1（AGENTS 单源自判，配套文案升修订号）。
- §4 测试：新增 `tests/test_mineru_batch.py`（mock 钉死映射同序/部分 failed 账本/到点部分回填/并行 PUT 零 Content-Type 回环实收头/51 份切批/单题 extract 回归）。
- §5 真测：Playwright 穿沙箱微批 4 题，隔离副本 git archive HEAD＋动态端口随机令牌＋只读复制 MinerU 绑定进隔离 data；真人路径收集框投纯图夹具→选 MinerU 云座→解析；wiretap 录四段真_wire；失败注入坏图最后一份。

## 【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator）

- `a162fd3` docs(recon)：新增 `docs/handoff/evidence/mineru-batch-recon/official-docs-excerpt.md`（官方文档关键节逐字存档）＋`recon.md`（上限/形状/时限定案＋欠账）。
- `657a21b` feat(ingest)：
  - 修改 `app/core/ingest/recognize/mineru_extract.py`（+181 行，359 行≤450）—— 新增 `extract_batch`＋`_extract_chunk`；常量 `BATCH_MAX_FILES=50`/`UPLOAD_WORKERS=4`；单题 `extract` 不动。
  - 修改 `app/core/ingest/recognize/mineru.py`（95 行）—— `run()` 改整批发送＋「已回 N/M」进度＋逐题失败 note 账本。
  - 新增 `tests/test_mineru_batch.py`（497 行，20 用例）。
- `8cd8b20` chore(index)：`plugins.toml` 同步 editor 2.23.1（sync_plugin_index rc0）。
- `24375c1` test(ingest)：新增 `tools/mineru_batch_live_probe.py`（414 行真机探针）＋`docs/handoff/evidence/mineru-batch-live/{make_fixture.py,wiretap_sitecustomize.py,run4/(probe.toml,wireA.toml,wireB.toml,shots×10)}`＋`docs/handoff/evidence/mineru-batch-recon/live-receipt-check.md`（§1.2 回执核）。
- `121d4a7` docs(receipt)：本回单 `docs/handoff/receipts/mineru-batch.md`＋biz 记录 `.qoder/records/biz/2026-11/20261120_mineru-batch.md`（收口笔）。
- 本勘误笔：回单 ahead 计数勘误（按笔数记，免随 commit 漂移）。

### 插件仓（E:\jiuzhang\jiuzhang-plugins）

- `1083f4a` chore(editor)：`src/org.jiuzhang.editor/catalog.toml:113`（mineru 一条文案）＋`plugin.toml` version 2.23.1＋`plugins.json`（版本/changelog）＋`plugins/org.jiuzhang.editor.zip` 重打（90 条目，models/＋model_prefs.toml 不入包）。

### 禁改区自查

- LICENSE：否（未触碰）。
- AGENTS.md 铁律一二：否（未改）。
- `app/core/question_contract.py` 契约破坏性变更：否（未触碰）。
- 用户 `data/`：否（探针只读复制 MinerU 绑定进隔离 `.system_generated/` data 副本，禁碰用户 data/；live engines/ 与 65496 PID 12000 零接触）。
- `tools/onnx_probe.py`：原地未 stage（git status 仍 untracked）。
- engines 产物：未 stage。
- 禁 JSON 落盘：交付证据 wire 转 TOML（`[[exchanges]]`，循 norm-dict-table/wire.toml 先例）；运行时 JSONL 仅落 `.system_generated/`（gitignore），不进 git。

## 【包结构自检】（editor 2.23.1）

- 顶层目录名 == plugin.toml id：是（`org.jiuzhang.editor`）。
- backend 字段：无（底座不支持，包内不存在）。
- Apache-2.0 LICENSE 全文：有（包内 LICENSE）。
- min_host_version（1.0.0）≤ 当前 app.__version__（1.2.0）：满足。
- zip 双建同哈希：`3405a49a7cf7788d01512c4f4d993a15d2ed4a622e9565a2725b5e37a20841bf`（确定性打包，两次构建逐字节一致）。
- models/＋model_prefs.toml：不入包（DENY 排除，包内零命中）。

## 【三查结果】（grep 实测，editor dist/）

- `fetch(` 命中 **0**（`grep -rn "fetch(" dist/ | wc -l`）。
- `parent.document` 命中 **0**。
- `localStorage` 命中 **0**。
- 请求 id 符合 `^[A-Za-z0-9_-]{1,80}$` 且不含点号：是（插件走 postMessage 命令族，id 无点号；本卡未新增请求族）。

## 【测试与探针】

- 单测（`.venv/Scripts/python.exe -m unittest`，逐模块点名，禁 pytest/discover）：
  `tests.test_mineru_batch`（20）＋`tests.test_mineru_extract`（6）＋`tests.test_recognize_router`＋`tests.test_ingest_routing`＋`tests.test_mineru_local_run`＋`tests.test_vlm_local_run`＋`tests.test_ingest_failure_surface`（后五合 79）＝**7 模块 105/105 绿**（当次实测 `Ran 105 tests … OK`）。
- 快门禁：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**；体积预警 23 份均既存文件（451–550 区间），本卡新增/修改文件 mineru_extract.py 359 行、mineru.py 95 行、探针 414 行均≤450。
- 真机探针：`tools/mineru_batch_live_probe.py run4` → **19/19 passed（ok=True，113.5s）**。
  - 隔离副本 git archive HEAD：operator `8cd8b208`／plugins `1083f4a3`；动态端口 44466＋随机令牌；云账号 acc_7ae191d903 只读复制绑定。
  - Run A 顺风：一次 POST file-urls/batch files=4（batch `30ca2ccc-9cd6-47d4-9b69-8ee6a5cef22d`，data_ids jzo-0-d4e2e522…jzo-3-6406626a，model_version vlm）；4 PUT 全 ok（OSS 200⇒零 Content-Type，body_len 294305/254821/429342/143466）；单 batch_id 轮询；4 份 zip（cdn-mineru.openxlab.org.cn，59064/118056/101242/173735 字节）→full.md 映射回填；路由「4/4 道回填成功」＋failures 空；4 题题干 157/142/112/133 均非空；进度「已回 0/4→3/4」截图。
  - Run B 失败注入：corrupt_last 把最后一份 PUT body 换坏字节（body_len=23，file_index 3，OSS 仍 200）→MinerU 真返 `failed`（data_id jzo-3-33b9eed9，err_msg「unsupported file type」）→3/4 回填＋1 逐题失败账本显性（failures 1 条 retryable）；逐题 transient 注记「第 4/4 题 MinerU 没成功（…unsupported file type），继续下一题。」（wiretap 录 _progress，progress_writes=24）；失败不级联不偷换（其余 3 题照回填）；失败清单 UI 徽标＋点开 ed-fail-item 可见。
  - 页面零 JS 异常、全程零 HTTP 失败；收口端口 44466 复验关闭＋副本孤儿零。
  - 截图绝对路径：`E:\jiuzhang\jiuzhang-operator\docs\handoff\evidence\mineru-batch-live\run4\shots\`（runA-uploaded/done/progress-0/progress-3、runB-done/progress-0/1/2/3/failure-list 共 10 张）；probe.toml/wireA.toml/wireB.toml 同目录。运行时产物另在 `.system_generated/mineru-batch-live/run4/`（gitignore，备查）。
- 前端改动：本卡插件面仅 catalog 一条文案（数据，非 JS）；真人路径在 Playwright 真浏览器走过——收集框投卷→选 MinerU 云座→解析→底部日志「已回 N/M」→失败批次徽标点开失败清单，均亲眼可见（截图为证）。

## 【未决问题与偏离】

- 欠账①：官方文档页内「≤50（接口节）vs ≤200（总表）」矛盾，取 50 保守实现；待官方澄清后可放宽，不阻塞本卡（recon.md §4 登记）。
- 欠账②：二手来源（CSDN/博客）「600 页/200 个/2000 页日」与官方现行页不符，一律不采不引为据。
- 偏离①（观测手法，非产品改）：Run B 逐题失败 transient 注记在整批结算后毫秒级闪过，2s 轮询抓不到——wiretap 增录 `mineru._progress` 注记写（只观测＋委托原函数）确定性取证；失败批次徽标只在 refreshBatches 重渲染时挂上，解析完成后用插件调试面 `window.__jzoEditorV2.refreshBatches()`（dev_probe_api 既有探针口子）真刷一次列表再核徽标＋点开清单。产品代码一字未改。
- 偏离②（证据格式）：探针运行时 wire 落 JSONL（.system_generated，gitignore）；交付证据按卡§6「禁 JSON 落盘」转 TOML（`[[exchanges]]`，循 norm-dict-table/wire.toml 先例），探针亦直接吐 wireA.toml/wireB.toml 保证可复现。
- 解释性口径：整批 deadline＝整批上限（非每题各 900s）；「已回 N/M」的 N＝done＋failed 已结算份数；失败账本最终为 1 条聚合 entry（router `_surface` 按 step 去重，既有形状），逐题粒度由 transient note「第 X/N 题没成功」保住。
- 额度实耗如实披露：每份单题截图＝1 页。canonical run4 提交 8 页、成功解析 7 页（坏图 1 页 failed）；前序调试 run1（RunA 4 页）/run2（8 页）/run3（8 页）亦真耗云额度，本卡真测累计提交约 28 页、成功解析约 24 页，远低于官方每日 1000 页最高优先级额度。
- 未验证：到点（900s）部分回填分支真机未触发（两批均远小于 900s 全结算），由 test_mineru_batch 假时钟钉死；超 50 份切批真机未跑（微批定死 4 题），由 test_mineru_batch 51 份切批用例钉死。
- 停链核对（卡§7）：官方上限核到（50 保守）＋保守上限真测绿＋映射对得上＋真测绿＋冻结面接得进＝**无停链触发，全卡成功**。

## 需主公点什么

- 两仓 push 授权（本卡奉令 hold，未 push；operator 本卡六笔＝侦查/代码/同步/探针证据/回单/本勘误，基线 ahead 61→现 ahead 67／plugins 一笔，基线 ahead 18→现 ahead 19）。
- 正式产品（65496 PID 12000）若要享受整批提速，需主公重启加载新码（本卡零接触正式服务，新码已在隔离副本真测验证）；editor 2.23.1 zip 已就绪（`3405a49a…`），按既有安装链落地即可。
- 官方 50 vs 200 上限矛盾：若主公愿意，可向 MinerU 官方澄清后放宽 BATCH_MAX_FILES（现保守 50 不影响任何≤50 题批次）。
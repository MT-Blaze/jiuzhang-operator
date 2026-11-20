# MinerU 云整批提速（mineru-batch）

状态：已发布（editor 2.23.1；两仓 commit 不 push，奉令 hold）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达 MinerU云整批提速任务卡（E:\jiuzhang\MinerU云整批提速任务卡.md）
基线：operator 9201cc9（ahead 61）／plugins f3727b7（ahead 18，editor 2.23.0）；交付 editor 2.23.1（host 仍 1.2.0）
回单：docs/handoff/receipts/mineru-batch.md（#MINERU-BATCH-01）

## [REQ] 2026-11-20

病根：MinerU v4 接口天生批量（POST file-urls/batch 一次申请整批地址），旧码却一次塞一份，
20 题 20 个来回，慢。卡令：新增兄弟 extract_batch 整批一次发送、逐题回填，单题 extract 保留不动；
mineru.run 改整批；保住题↔结果映射、逐题失败账本、逐题进度三样不许变粗；失败显性不偷换不降级。
约束：微批 3–5 定死；只走云（本地 CPU 停跑令照旧）；出网界面点击发起禁 GitHub；65496（PID 12000）与
live engines/ 零接触（探针 git archive HEAD 隔离副本）；两仓不 push；禁 JSON 落盘； LICENSE/铁律一二/
question_contract.py/用户 data/ 禁改；onnx_probe.py 原地不 stage；分层≤3；records append-only。
验收：官方批量上限文档核（核不到按保守上限＋登记欠账）；批量响应形状复核（wire 存档＋一次真微批回执核）；
整批 900s 上限到点 done 照回填、未 done 逐题显性失败；定向单测＋快门禁绿；Playwright 真测微批整批＋失败注入一例。

## [IMPL] 2026-11-20

- §1 侦查（commit a162fd3）：官方 mineru.net/apiManage/docs 接口节逐字「单次申请链接不能超过 50 个」
  →BATCH_MAX_FILES=50（总表 200，页内矛盾取保守侧，欠账登记）；响应形状官方参数表＋typst-bench wire 互证；
  时限整批共用 900s。证据 docs/handoff/evidence/mineru-batch-recon/{official-docs-excerpt.md,recon.md}。
- §2 代码刀（commit 657a21b）：mineru_extract.py +extract_batch/_extract_chunk（一次 POST、并行 PUT≤4
  复用 _put_raw 零 Content-Type、单轮询 data_id 认行、done 并行取 zip、failed 逐份 err_msg、同序返回、超 50 切批）；
  单题 extract 一字不动。mineru.py run() 改整批（备齐题图→一次 extract_batch→「已回 N/M」进度→逐 done 题
  build_documents+merge_local+save_back 不动→失败逐题 note 账本）。mineru_extract.py 359 行≤450。
- §3 插件面（plugins commit 1083f4a）：catalog.toml mineru 一条 route_note_recognize 改整批口径；
  版本 2.23.0→2.23.1；parity 四处一致＋zip 双建同哈希 3405a49a…＋sync rc0；models/+model_prefs.toml 不入包。
  底座 plugins.toml 同步（commit 8cd8b20）。
- §4 测试（commit 657a21b）：tests/test_mineru_batch.py 20 用例（映射同序/部分 failed 账本/到点部分回填/
  回环并行 PUT 零头实收/51 份切批/单题回归）。
- §5 真测（commit 24375c1）：tools/mineru_batch_live_probe.py（414 行）＋make_fixture.py（A1 纯图真卷第 2 页
  管线题块裁 4 道成 4 页纯图 PDF，ocr.detect 复核 4 题）＋wiretap_sitecustomize.py（导入钩子包
  mineru_extract._request/_put_raw 与 mineru._progress，只观测＋委托 HEAD 原函数）。
- 使用 skill：sync-biz-record（本记录）；真测循 prove-visual-change/run-regression 隔离副本动线。

## [VERIFY] 2026-11-20

- 定向 7 模块 105/105 绿（当次实测 Ran 105 tests OK）：test_mineru_batch 20＋test_mineru_extract 6＋
  test_recognize_router/test_ingest_routing/test_mineru_local_run/test_vlm_local_run/test_ingest_failure_surface 79。
- 快门禁 bash scripts/check-quick-gate.sh PASS（6 项）；三查 fetch(/parent.document/localStorage 0/0/0。
- 真机探针 run4 全绿 19/19（ok=True，113.5s）：隔离副本 git archive HEAD 8cd8b208/1083f4a3＋动态端口 44466＋
  随机令牌＋只读复制 MinerU 绑定 acc_7ae191d903。Run A 顺风 4/4（一次 POST files=4 batch 30ca2ccc…、
  4 PUT 零 Content-Type OSS 200、单 batch_id 轮询、4 份 full.md 映射、题干 157/142/112/133、进度 0/4→3/4 截图）；
  Run B 失败注入坏图最后一份（body_len=23 OSS 仍 200）→MinerU failed「unsupported file type」→3/4＋逐题账本＋
  逐题 transient 注记「第 4/4 题没成功」＋失败清单 UI 徽标点开可见，不级联不偷换。零 JS 异常零 HTTP 失败；
  收口端口闭＋孤儿零。证据 docs/handoff/evidence/mineru-batch-live/run4/（probe.toml/wireA.toml/wireB.toml/shots×10）。
- §1.2 真微批回执核 live-receipt-check.md：批量响应形状逐字段与官方参数表＋示例核对一致。
- 额度实耗：run4 提交 8 页解析 7 页；全卡累计（run1–4）提交约 28 页解析约 24 页，远低于每日 1000 页额度。
- 红线：LICENSE/铁律一二/question_contract.py/用户 data/ 未触碰；onnx_probe.py 原地未 stage；engines 未 stage；
  禁 JSON 落盘（wire 证据转 TOML，运行时 JSONL 仅 .system_generated gitignore）；分层≤3。
- 观测手法偏离（产品零改）：逐题 transient 注记毫秒闪过→wiretap 录 _progress 取证；失败徽标需 refreshBatches→
  用 dev_probe_api window.__jzoEditorV2.refreshBatches() 真刷再核。

## [RELEASE] 2026-11-20

- editor 2.23.1（host 1.2.0 不动）；zip sha256 3405a49a7cf7788d01512c4f4d993a15d2ed4a622e9565a2725b5e37a20841bf（90 条目）。
- 底座 commit：a162fd3（侦查）/657a21b（代码＋测试）/8cd8b20（索引同步）/24375c1（探针＋证据）＋收口笔（回单＋biz）。
- 插件 commit：1083f4a（2.23.1 封版）。
- 两仓不 push（主公明确不授权）；正式产品 65496 零接触，新码需主公重启加载（隔离副本已真测验证）。
- 欠账：官方 50 vs 200 上限矛盾取保守 50，待澄清可放宽；二手来源不采。
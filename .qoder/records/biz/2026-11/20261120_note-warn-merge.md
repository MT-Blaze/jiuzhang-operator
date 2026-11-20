# 剥图警告保合并（note-warn-merge）

状态：停链收口（§2 刀不下；侦查证据＋回归钉死已 commit 不 push；真根因 CRLF 待主公拍板另卡）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达剥图警告保合并小刀卡（E:\jiuzhang\剥图警告保合并小刀卡.md，排队③，MinerU 整批提速卡链派下一棒）
基线：operator 2d744b8（ahead 67）／plugins 1083f4a（ahead 19，editor 2.23.1）；本卡 operator 三笔（5a5be0d/db34eb3/收口笔），plugins 零改
回单：docs/handoff/receipts/note-warn-merge.md（#NOTE-WARN-MERGE-01）

## [REQ] 2026-11-20

病根（BDP-01 收口披露观察项）：intake/shapes.py 剥卷首图片行如实产 warnings，
但落池后 dedupe 重写 route.note 把警告冲掉＝老师看不见「卷首图被剥」提示。
卡令：§1 grep 定位冲掉点带行号；§2 note 重写改合并保警告（既有注记保留＋warnings
追加，人话去重不超长，无警告时逐字一致）；§3 全接线夹具用例＋定向单测＋快门禁＋三查；
§4 shapes.py/text.py 解析逻辑/契约/字典/上传链/其余 note 语义/插件全族一字不动；
§5 冲掉点找不到＝停链报枢纽。两仓不 push；无人值守不许问主公；65496（PID 12000）
与 live engines/ 零接触；禁 JSON 落盘；分层≤3；records append-only；stage 点名不 amend。

## [PLAN] 2026-11-20

侦查先行：grep route_json 全仓写点＋note 赋值点全录，再给 set_batch_route 打桩
全接线离线回放（dedupe 抽走启用态）。实证结论推翻卡面前提：dedupe 族零 route 写，
LF 夹具警告完整存活；BDP-01 观察到的丢失真根因是 CRLF 行尾（decode_text 不归一＋
shapes._IMAGE_LINE 行尾不认 \r → 警告根本没产，不是产了被冲）。
取舍：① §2 刀不下——无冲掉点可治，触发§5停链；② 被否方案：save_route 通用 note
合并——会改扫描路按阶段重写 note 的既有设计（§4「其余 note 语义」冻结），弄坏回归；
③ CRLF 修复（decode_text 归一或 shapes 正则容 \r）全在冻结面，不擅自解冻，登记建议
交枢纽拍板；④ 交付回归钉死四案（LF 存活/无警告逐字/单笔写盘/CRLF Canary）锁住卡面
要的语义，生产码零改。

## [IMPL] 2026-11-20

- 侦查证据（commit 5a5be0d）：docs/handoff/evidence/note-warn-merge/{recon.md（note
  重写点全录带行号＋证伪链＋停链依据＋下一棒建议）, replay_note_warn.py（132 行自包含
  打桩探针，三路全接线＋边界对照）, replay_report.md（当次实测：LF 警告存活/CRLF 空/
  无图空，每批 route 单笔写盘，栈帧全 save_route 无 dedupe）}。
- 回归钉死（commit db34eb3）：tests/test_note_warn_merge.py（143 行 4 用例，隔离
  data/plugins＋目录夹具插件，循 test_ingest_failure_surface/catalog_fixture 先例）。
- 生产代码零改；插件零改（parity 持现版 2.23.1，zip 不重打）；前端零改（免真测）。
- 使用 skill：sync-biz-record（本记录）；侦查/测试循 run-regression 定向口径（AGENTS §7
  2026-11-18 拍板：定向＋门禁为主，全量免跑）。

## [VERIFY] 2026-11-20

- 单测（.venv/Scripts/python.exe -m unittest 逐模块）：test_note_warn_merge 4/4＋
  test_ingest_routing 10/10＋test_ingest_failure_surface 10/10＋
  test_build_documents_shapes 23/23＋test_bank_dedupe 21/21＝5 模块 68/68 绿。
- 快门禁：bash scripts/check-quick-gate.sh → PASS（6 项全过）；体积预警 23 份均既存，
  本卡新文件 143/132/100/54 行均≤450。
- 三查：editor dist（现版 2.23.1，本卡零改）fetch( 0／parent.document 0／localStorage 0。
- 离线回放探针：replay_note_warn.py 三路＋边界对照（零出网零引擎零端口，隔离
  .system_generated/note-warn-merge/e2e）；Playwright 真测免（前端零改，回单注明）。
- 禁改区自查：LICENSE/铁律一二/question_contract.py/用户 data/ 未触碰；onnx_probe.py
  与 plugins 仓 models//model_prefs.toml 原地未 stage；engines 产物未 stage；禁 JSON
  落盘（证据全 MD）；65496 PID 12000 与 live engines/ 零接触；暖驻留 16892 未杀。
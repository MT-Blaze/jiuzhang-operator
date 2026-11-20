# 回传单 · 剥图警告保合并小刀卡（排队③·停链收口）

【回执编号】 #NOTE-WARN-MERGE-01
【回执时间】 2026-11-20T12:06:53+08:00
【实际耗时】 单段无人值守执行会话（侦查打桩回放＋证伪定案＋回归钉死＋门禁三查＋回单）
【执行结果】 **停链（卡§5 触发：冲掉点找不到）**。侦查实证卡面病根不成立：dedupe 族零 route 写，LF 卷首图警告全接线存活到池内 note；BDP-01 观察到的丢失真根因是 CRLF 行尾致警告根本没产（落点全在§4冻结面）。§2 刀不下，生产代码零改；交付侦查证据＋回归钉死四案＋本回单。定向 5 模块 68/68 绿；快门禁 PASS（6 项）；三查 0/0/0；两仓 commit 不 push（奉令 hold）。

基线：operator `2d744b8`（ahead 67）／plugins `1083f4a`（ahead 19，editor 2.23.1）。
本卡 operator 三笔：`5a5be0d`（侦查证据）／`db34eb3`（回归钉死）／收口笔（本回单＋biz）；
ahead 按笔数记：67＋3＝70（免随 commit 漂移）。plugins 零改零笔，ahead 仍 19。
biz 记录：`.qoder/records/biz/2026-11/20261120_note-warn-merge.md`。
卡：`E:\jiuzhang\剥图警告保合并小刀卡.md`（唯一口径）。

## 卡§0 口径复述（逐字生效）

两仓不 push（主公明确不授权别再问）；无人值守不许问主公；65496 正式服务（PID 12000）
与 live engines/ 零接触；产品暖驻留 llama-server 16892 不杀；微批口径不适用（零引擎
零出网，离线回放）；shapes.py/text.py 解析逻辑/契约/字典/上传链/其余 note 语义/插件全族
一字不动（插件零改＝parity 持现版 2.23.1 zip 不重打）；LICENSE/铁律一二/question_contract.py/
用户 data/ 禁改；onnx_probe.py/models//model_prefs.toml 原地不 stage；engines 产物不 stage；
禁 JSON 落盘；分层≤3；records append-only；stage 点名；不 amend。并行会话 862041d1
只读两仓＋.system_generated 证据不 commit，与本卡 commit 无涉。

## 做了什么（逐条对齐卡§1–§5）

- §1 侦查（先 grep 再动刀）：route_json 全仓写点仅两处——`save_route`
  （app/core/ingest/route.py:49-64，写盘 :62）与 reidentify（recognize/reidentify.py:39，
  非本卡路）；note 赋值点全录（route.py:45/168/329-339/390、recognize/router.py:104-247、
  mineru.py:48-66、mineru_local.py:194-203、vlm_local.py:135-144、formula.py:356）。
  **pending dedupe 族对 note/route_json 零写**（grep 实证＋打桩回放栈帧证）。
  全录带行号落 `docs/handoff/evidence/note-warn-merge/recon.md`。
- §2 刀：**不下（停链）**。打桩回放（dedupe 抽走启用态、jzo-dedupe-warm 线程 join 后读）：
  LF 带卷首图夹具 note＝`题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/header_photo.jpg`
  完整存活，每批 route 写盘**只有一笔**（service.py:400→route.py:62），无 dedupe 栈帧；
  CRLF 同文 note 空——警告根本没产。冲掉点不存在，触发§5「冲掉点找不到＝停链报枢纽」。
  真根因：decode_text（text.py:117-124）不做换行归一，\r 原样进解析；
  shapes._IMAGE_LINE（shapes.py:37）行尾 `[ \t]*$` 不认 \r → CRLF 图片行不匹配、不剥、
  不产警告（随后被切段器静默丢掉）。BDP-01 e2e 落池路用 read_bytes（CRLF）、边界对照用
  read_text（转 LF），口径差一个换行归一，差距被误归因到 dedupe。
- §3 测试：新增 tests/test_note_warn_merge.py 四案——LF 带卷首图全接线
  ingest_files→落池→dedupe 后 note 含警告且只一条；无警告夹具 note 逐字不变（空串）；
  抽走启用态 route 单笔写盘警告不丢；CRLF 现状 Canary（有意钉死，另卡治时变红提醒）。
  离线回放充分（自包含探针三路＋边界对照，BDP 先例隔离动线）。**前端 note 展示零改→
  Playwright 真测免，特此注明**。
- §4 不动面：生产代码零改（shapes.py/text.py/契约/字典/上传链/其余 note 语义/插件全族
  一字未动）；禁改区自查见下。
- §5 停链与回单：本回单＋biz append；直白回复枢纽。

## 【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator）

- `5a5be0d` docs(recon)：新增 `docs/handoff/evidence/note-warn-merge/recon.md`（100 行，
  note 重写点全录带行号＋证伪链＋BDP 误归因还原＋停链依据＋下一棒建议）、
  `replay_note_warn.py`（132 行自包含打桩探针）、`replay_report.md`（54 行当次实测）。
- `db34eb3` test(ingest)：新增 `tests/test_note_warn_merge.py`（143 行 4 用例，
  NoteWarnMergeTest：test_lf_header_image_warning_survives_full_wiring /
  test_no_warning_note_verbatim / test_dedupe_enabled_single_route_write_keeps_warning /
  test_crlf_current_behavior_canary）。
- 收口笔：本回单 `docs/handoff/receipts/note-warn-merge.md`＋biz 记录
  `.qoder/records/biz/2026-11/20261120_note-warn-merge.md`。
- **生产代码（app/、static/）：零改。**

### 插件仓（E:\jiuzhang\jiuzhang-plugins）

- 零改零笔。parity 持现版 editor 2.23.1，zip 不重打。

### 禁改区自查

- LICENSE：否（未触碰）。AGENTS.md 铁律一二：否（未改）。
- app/core/question_contract.py 契约破坏性变更：否（未触碰）。
- 用户 data/：否（回放隔离 .system_generated/note-warn-merge/e2e，JZO_DATA_DIR/
  JZO_PLUGINS_DIR 临时区＋最小目录夹具插件）；65496 PID 12000 与 live engines/ 零接触；
  暖驻留 llama-server 16892 未杀。
- tools/onnx_probe.py：原地未 stage（git status 仍 untracked）。
- plugins 仓 models/＋model_prefs.toml：原地未 stage（仍 untracked）。
- engines 产物：未 stage。禁 JSON 落盘：证据全 MD。分层≤3：证据目录循
  build-documents-shapes 既存先例（卡§3 点名路径）。records append-only：biz 新建。
- stage 点名（三笔各点名文件）；不 amend；不 push。

## 【包结构自检】

不适用——插件零改（卡§4：parity 持现版 2.23.1，zip 不重打）。现版自检沿用
mineru-batch 回单（#MINERU-BATCH-01）：zip 双建同哈希 `3405a49a…`，models/＋
model_prefs.toml 不入包。

## 【三查结果】（grep 实测，editor dist 现版 2.23.1，本卡零改）

- `fetch(` 命中 **0**（Grep count，jiuzhang-plugins/src/org.jiuzhang.editor/dist）。
- `parent.document` 命中 **0**。
- `localStorage` 命中 **0**。
- 请求 id：本卡未新增请求族，无涉。

## 【测试与探针】

- 单测（`.venv/Scripts/python.exe -m unittest`，逐模块点名，禁 pytest/discover）：
  `tests.test_note_warn_merge` 4/4＋`tests.test_ingest_routing` 10/10＋
  `tests.test_ingest_failure_surface` 10/10＋`tests.test_build_documents_shapes` 23/23＋
  `tests.test_bank_dedupe` 21/21＝**5 模块 68/68 绿**（当次实测各模块 `Ran N tests … OK`）。
- 快门禁：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**；体积预警 23 份均
  既存文件（451–550 区间），本卡新文件 143/132/100/54 行均≤450，冻结台账只减不增。
- 离线回放探针：`docs/handoff/evidence/note-warn-merge/replay_note_warn.py` →
  三路全接线（LF 带图/CRLF 同文/LF 无图）＋shapes 边界对照；dedupe 抽走启用态、
  后台线程 join 后读；set_batch_route 打桩录笔数与栈帧。实测：LF 警告存活（note 逐字
  含「题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/header_photo.jpg」，
  见 replay_report.md）／CRLF note 空／无图 note 空；三批各 route 单笔写盘，栈帧全
  service.py:400→route.py:62，零 dedupe 帧。零出网零引擎零端口。
- Playwright 真测：**免**（前端 note 展示零改，卡§3 豁免条款，特此注明）。
- 全量回归：免（AGENTS §7 2026-11-18 拍板，定向＋门禁为主；本卡生产码零改）。

## 【未决问题与偏离】

1. **停链声明（卡§5）**：§2「note 重写改合并保警告」刀不下——冲掉点经打桩回放证伪
   （dedupe 族零 route 写，LF 警告全接线存活）。无冲掉点可治；若在 save_route 做通用
   note 合并，会改扫描路按阶段重写 note 的既有设计（§4「其余 note 语义」冻结面），
   弄坏既有回归，故不擅自下刀。
2. **真欠账·需主公拍板另卡**：CRLF 卷首图行不剥不警告（老师拖 Windows 记事本存的
   .md/.txt 中招，图片行被切段器静默丢）。修复落点二选一，均在本卡冻结面，须解冻：
   ① **推荐** decode_text 边界归一换行（text.py:117-124，CRLF→LF 单源，一处治全部
   行尾敏感正则；但改 CRLF 文件解析行为，属解析逻辑变更，需契约级回归）；
   ② shapes._IMAGE_LINE 行尾容 \r（shapes.py:37，只治剥图一行，其余行尾敏感形状仍漏，
   不推荐）。详见 recon.md「停链依据与下一棒建议」。
3. **BDP-01 误归因勘误（登记不 retro-edit）**：build-documents-shapes 回单 :108 与
   e2e_ingest.py :132-133 注释把池内警告丢失归因「dedupe 用新快照重写 route」——
   本卡打桩实证该归因不成立，真因是 CRLF（边界 read_text vs 落池 read_bytes 口径差）。
   records/回单 append-only，不回改历史；以本回单与 recon.md 为准。
4. **相邻观察（登记不动）**：扫描路 fill_scan_batch 内 scan_route 重建（route.py:379）
   会丢 service.py:310 先 append 的 notes，但 PDF page_only 分支 notes 恒为空
   （service.py:274-275），今日无实际损失；属其余 note 语义冻结面，本卡不碰。
5. push 奉令 hold（两仓不 push，主公明确不授权别再问）；ahead 按笔数记 67→70。
# 回传单 · CRLF 换行归一小刀卡（排队⑤·剥图②停链真欠账·主公拍板①）

【回执编号】 #CRLF-NORMALIZE-01
【回执时间】 2026-11-20（午拍板①「解码口归一换行」当日收口）
【实际耗时】 单段无人值守执行会话（基线复核＋侦查盘点＋一处刀＋canary 转正＋定向回归＋门禁＋离线回放＋回单）
【执行结果】 **成**。decode_text 返回前单源归一 CRLF→LF、lone \r→LF（一处治全部行尾敏感正则）；CRLF/lone \r 卷首图行现在也剥也警告且只一条，与 LF 同文逐字同语义；LF 现状逐字不变、无警告夹具 note 逐字不变。定向 7 模块 101/101 绿＋triage 20/21（已知红一案照挂）；快门禁 PASS（6 项）；三查发行面 0/0/0；离线回放 15/15。两仓不 push（奉令 hold）；插件零改零笔。**新码生效需主公再重启一次**（65496 现 PID 17136 仍跑旧码，本卡零接触）。

基线（开工实测零偏离）：operator `d0842569`（ahead 78）／plugins `0841ccd1`（ahead 22，editor 2.25.0）。
本卡 operator 两笔：`b2ede7f`（刀＋测试转正＋回放证据）／收口笔（本回单＋biz）；ahead 78＋2＝80。
plugins 零改零笔，ahead 仍 22（parity 持现版 2.25.0，zip 不重打）。
biz 记录：`.qoder/records/biz/2026-11/20261120_crlf-normalize.md`。
前情：剥图② #NOTE-WARN-MERGE-01 打桩实证真根因（docs/handoff/evidence/note-warn-merge/），
dedupe 冲掉警告系 BDP-01 误归因已证伪——本卡不治 dedupe，只治解码口。

## 1.【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator）

- `b2ede7f` 修改 `app/core/ingest/intake/text.py:117-127` decode_text：逐编码尝试
  改为 break/else 收口到局部变量，返回前 `text.replace("\r\n", "\n").replace("\r", "\n")`
  单源归一；编码兜底顺序 utf-8→utf-8-sig→gb18030→replace 一字未动。文件 398→400 行
  （引擎模块 400 行帽内，见偏离①）。
- `b2ede7f` 修改 `tests/test_note_warn_merge.py`（143→204 行，tests/ 豁免行数帽）：
  第四案 CRLF canary **改断言转正**（test_crlf_header_image_warning_normalized：CRLF
  也剥也警告且只一条、题号仍由题干头号承载、图片行不入题干），未删案；新增
  test_crlf_lf_same_semantics_verbatim（同名夹具 note 与题目文档除 id 逐字一致）、
  test_lone_cr_old_mac_header_image_warning（老 Mac lone \r）、
  test_crlf_plain_note_still_empty（无警告 CRLF 版 note 仍空串）、
  DecodeTextNormalizeTest 三案（LF 逐字不变／CRLF 与 lone \r 归一／编码兜底顺序不变
  含 GBK CRLF 与 BOM 现状钉死）。原 LF 三案与无警告逐字案原样保留。
- `b2ede7f` 新增 `docs/handoff/evidence/crlf-normalize/replay_crlf.py`（157 行自包含
  离线回放：真 CRLF/lone \r/LF 字节夹具落盘→read_bytes→data_url→ingest_files 全接线，
  dedupe 抽走启用态真跑）、`replay_report.md`（当次实测）、`probe.toml`（15 判据）。
- 收口笔：本回单＋biz 记录。

### 插件仓（E:\jiuzhang\jiuzhang-plugins）

零改零 commit。未跟踪件 `src/org.jiuzhang.editor/models/`＋`model_prefs.toml` 原地保留未 stage。

### 受益面盘点（卡§1 要求：只登记不改）

归一后一处治全部行尾敏感正则，全仓 grep 登记：
- `intake/shapes.py:37` `_IMAGE_LINE`（`[ \t]*$` 不认 \r）——**主受益**：CRLF/lone \r
  卷首图行从不剥不警告变为剥且警告（本卡治的病根）。
- `intake/text.py:57` `_ANSWER_HEAD_RE`（`([^\n]*)`）——答案组原先吞行尾 \r，归一后干净。
- `intake/text.py` `_split_numbered`/`_split_paragraphs`——split("\n") 不再留 \r 尾巴，
  题干与选项文本不再夹带 \r。
- `intake/media.py:81`——zip 内文本文件同走 decode_text，同步受益。
- `intake/shapes.py:38` `_DISPLAY_WRAP`、`render/regions.py:31` `_PDF_BARE_PAGE`——
  `\s` 本就认 \r，归一前后行为无差（登记无变化）。
- `api/agents.py:58` `_FENCE_RE`——显式认 `\r?\n` 且不走 decode_text 路，不受影响。
- 全仓 ID/semver/哈希族单 token `$` 锚正则——与行尾无关，不受影响。
- shapes.py 一字未动（警告来源口径不变）；其余解析逻辑/形状正则/契约一字未动。

## 2.【真测与证据】

- 单测（`.venv/Scripts/python.exe -m unittest tests.<模块>` 逐个点名，禁 pytest/discover）：
  - test_note_warn_merge **10/10**（含转正 canary＋lone \r＋CRLF/LF 逐字对照＋纯函数钉死）
  - test_build_documents_shapes **23/23**
  - test_ingest_routing **10/10**（含 zip 内 full.md 解码路）
  - test_ingest_failure_surface **10/10**
  - test_bank_dedupe **21/21**
  - test_ingest_scan **14/14**（grep 沾到族补全）
  - test_file_size_contract **13/13**（grep 沾到族补全；体积硬拦判定）
  - 合计 7 模块 **101/101 绿**。
  - test_ingest_triage **20/21**：唯一红案＝卡§9 点名照挂的
    MineruPerQuestionTest.test_single_question_screenshots_not_the_whole_pdf
    （提速①旧 mock 陈旧，非本卡回归，零触 MinerU 路）。其 400 行帽案
    test_04 初红（text.py 402）已施工自查压回 400 转绿（偏离①）。
- 快门禁：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**；体积预警 23 份
  全是基线既有文件（text.py 400 行不在预警区），冻结台账只减不增（未新增）。
- 三查（插件发行面，本卡零改）：fetch( **0**／parent.document **0**／localStorage **0**；
  唯一 fetch( 命中在 `src/org.jiuzhang.editor/dev/preview.html:165` 调试页，打包排除
  dev/，门禁明文豁免，基线既有）。门禁「插件三查与依赖方向」步 PASS。
- 离线回放：`docs/handoff/evidence/crlf-normalize/replay_crlf.py` 当次实跑
  **15/15 PASS**（probe.toml）——真 CRLF/lone \r 字节夹具走 read_bytes 落池路
  （BDP e2e:67 同款）全接线 ingest_files→落池→dedupe 启用态真跑：CRLF/lone \r/LF
  三批 note 逐字相同且各含且仅含一条剥图警告，题目文档除 id 逐字一致；CRLF 无警告
  夹具 note 空串；decode_text(CRLF/lone \r 字节) 逐字等于 LF 原文；归一后
  shapes.normalize 警告 1 条图片行被剥。零出网零额度零引擎零端口，隔离
  `.system_generated/crlf-normalize/e2e`（data/plugins/fixtures 全隔离），不碰本机 data/。
- **前端零改→Playwright 真测免，特此注明**（note 展示链路一字未动，回放已证池内
  note 内容正确）。无需起服务，无端口无令牌无截图。
- 65496 只读复核：PID 17136 python.exe 仍在（tasklist 只读），本卡零接触零重启。

## 3.【偏离登记】

1. text.py 初版 402 行触发 test_ingest_triage.test_04 引擎模块 400 行帽红——施工自查
   发现，把归一注释并入 docstring 压回 400 行转绿；docstring 原文「老师的卷子多是
   GBK 存的」随之换为归一口径描述。**编码兜底顺序与解码语义零偏离**，属行数帽内
   自查修正，非卡面偏离。
2. BOM 钉死案按现状口径断言（utf-8 优先把 BOM 解成 \ufeff 字符保留）——不顺手改
   BOM 语义（超卡面），只钉现状。
3. 其余零偏离：解冻范围仅 decode_text 一处；shapes.py/其余解析/契约/字典/上传链/
   其余 note 语义/插件全族一字未动；canary 未删案改断言转正。

## 4.【遗留欠账】

- triage 已知红一案（提速①旧 mock 陈旧）照挂不治，归提速链欠账，非本卡。
- 两仓 push 全 hold（主公明确不授权）：operator ahead 80／plugins ahead 22。
- **新码生效需主公再重启一次**：65496（PID 17136）仍跑旧码，重启后老师拖 CRLF 卷
  才见剥图警告。本卡无人值守零接触，不擅自重启。
- 剥图②回单所记「选项并段口径微变」风险已被 CRLF/LF 逐字对照案覆盖（归一后同语义，
  无微变）；无新增欠账。

## 5.【红线自检与不动面】

- LICENSE／根 agents.md／AGENTS 铁律一二／question_contract.py／用户 data/：**未触碰**。
- shapes.py／其余解析逻辑／形状正则／契约／字典／上传链／其余 note 语义／插件全族：
  **一字未动**（git diff 实证只 text.py decode_text＋tests＋证据/回单/biz）。
- onnx_probe.py（底座）／models/＋model_prefs.toml（插件）原地保留未 stage；engines
  产物未 stage；禁 JSON 落盘（证据全 MD/TOML/py）；分层≤3（证据目录循 note-warn-merge
  既有先例平铺）；records append-only（biz 新建四阶段，未改历史）；stage 逐个点名；
  不 amend 不改写历史；两仓不 push。
- 零出网零额度零引擎真跑：只离线回放＋定向回归；未起任何识别引擎、未下载权重。
- 行数红线：text.py 400≤450（且≤引擎 400 帽）；replay_crlf.py 157；tests/ 豁免；
  冻结台账只减不增。
- 干净房间自查：diff 全部原创表达，无旧项目逐字内容。
# CRLF 换行归一（crlf-normalize）

状态：收口（刀＋测试＋证据已 commit 不 push；新码生效需主公再重启一次）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 派 CRLF 换行归一小刀卡（排队⑤，剥图②停链真欠账，主公 2026-11-20 午拍板①「解码口归一换行」）
基线：operator d0842569（ahead 78）／plugins 0841ccd1（ahead 22，editor 2.25.0）；本卡 operator 两笔（b2ede7f/收口笔），plugins 零改
回单：docs/handoff/receipts/crlf-normalize.md（#CRLF-NORMALIZE-01）

## [REQ] 2026-11-20

病根（剥图② #NOTE-WARN-MERGE-01 打桩实证）：decode_text 不做换行归一，\r 原样进
解析；shapes._IMAGE_LINE 行尾 `[ \t]*$` 不认 \r → CRLF 卷首图片行不剥、不产警告、
被切段器静默丢（老师 Windows 记事本存的 .md/.txt 中招）。dedupe 冲掉警告系 BDP-01
误归因已证伪，本卡不治 dedupe。主公拍板①＝唯一口径：解冻范围仅 intake/text.py
decode_text 一处，CRLF→LF、lone \r→LF 单源归一，编码兜底顺序不变；shapes.py 与
其余解析/契约一字不动；LF 现状逐字不变；canary 第四案治后改断言转正不许删案。
两仓不 push；65496（PID 17136）零接触；零出网零额度零引擎真跑；无人值守不许问主公。

## [PLAN] 2026-11-20

刀落 decode_text 返回前单源归一（一处治全部行尾敏感正则），优于被否方案「shapes
正则容 \r」（只治剥图一行，其余行尾敏感形状仍漏——剥图②侦查已论证）。受益面全仓
grep 盘点只登记不改（_IMAGE_LINE 主受益；_ANSWER_HEAD_RE 答案组吞 \r、切段留 \r
尾巴、zip 内文本同路受益；_DISPLAY_WRAP/_PDF_BARE_PAGE 的 \s 本就认 \r 无差；
agents.py _FENCE_RE 显式认 \r 且不走此路不受影响）。测试：canary 转正＋CRLF/LF
同名夹具逐字对照＋lone \r 老 Mac 案＋无警告 CRLF 版＋decode_text 纯函数钉死
（LF 逐字/编码顺序/BOM 现状）。取证循 BDP read_bytes 落池路先例：真 CRLF 字节夹具
全接线离线回放，dedupe 启用态真跑。

## [IMPL] 2026-11-20

- 刀（commit b2ede7f）：app/core/ingest/intake/text.py:117-127 decode_text 返回前
  `replace("\r\n","\n").replace("\r","\n")`；break/else 收口保编码顺序；398→400 行
  （初版 402 触引擎 400 行帽，注释并入 docstring 压回——施工自查修正）。
- 测试（同笔）：tests/test_note_warn_merge.py 143→204 行，canary 转正＋4 新案＋
  DecodeTextNormalizeTest 3 案，共 10 案；原 LF 三案原样保留。
- 证据（同笔）：docs/handoff/evidence/crlf-normalize/{replay_crlf.py（157 行）,
  replay_report.md, probe.toml}，当次实跑 15/15。
- 插件零改（parity 持现版 2.25.0 zip 不重打）；前端零改（免 Playwright，回单注明）。
- 使用 skill：sync-biz-record（本记录）；定向回归循 AGENTS §7 2026-11-18 拍板
  （定向＋门禁为主，全量免跑）。

## [VERIFY] 2026-11-20

- 单测（.venv 逐模块点名）：test_note_warn_merge 10/10＋test_build_documents_shapes
  23/23＋test_ingest_routing 10/10＋test_ingest_failure_surface 10/10＋
  test_bank_dedupe 21/21＋test_ingest_scan 14/14＋test_file_size_contract 13/13
  ＝7 模块 101/101 绿；test_ingest_triage 20/21（唯一红＝卡§9 点名照挂的提速①
  旧 mock 案，非本卡回归；400 行帽案自查压回转绿）。
- 快门禁 PASS（6 项全过）；体积预警 23 份均基线既有；冻结台账只减不增。
- 三查（插件发行面零改）：fetch( 0／parent.document 0／localStorage 0（唯一命中
  dev/preview.html 调试页打包排除，门禁明文豁免）。
- 离线回放 15/15：真 CRLF/lone \r 字节 read_bytes 落池路全接线，三批 note 逐字相同
  各含一条剥图警告，题目文档除 id 逐字一致，无警告夹具 note 空串；零端口零引擎。
- 禁改区自查：LICENSE/铁律一二/question_contract.py/用户 data/ 未触碰；shapes.py
  一字未动；onnx_probe.py 与 plugins 仓 models//model_prefs.toml 原地未 stage；
  禁 JSON 落盘（证据 MD/TOML）；65496 PID 17136 只读复核仍在，零接触零重启。
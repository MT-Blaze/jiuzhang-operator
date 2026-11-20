# MathType 私有区符号映射（pua-symbol-map）

状态：已收口（代码＋测试＋真卷探针；不 push）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达任务卡 #PUA-MAP-01
基线：operator HEAD 87dadb7（ahead 112）；本卡两笔（976d8a3／收口笔）
回单：docs/handoff/receipts/pua-symbol-map.md（#PUA-MAP-01）

## [REQ] 2026-11-20

文字直取在 MathType 生成的试卷里把 SymbolMT/MT-Extra 符号抽成 U+F0xx 私有区
字符，正文乱码。只读侦查已完成（`.system_generated/private-use-recon/report.toml`，
I3 实测 175 次、25 码位；旧记 452 未复现）。本卡要求在清洗层落一张
(字体族, 码位) 确定性映射，只解 MathType，其他家族不套表；F072 向量箭头
重音需按实际字符顺序定夺。

## [PLAN] 2026-11-20

- 入口：`render/regions.py:_pdf_text_lines` 逐字符循环（文字直取唯一字符级组装点）；
  PUA 此前原样流入题块文字。
- 取字体名：pypdfium2 raw `FPDFText_GetTextObject` → `FPDFTextObj_GetFont` →
  `FPDFFont_GetBaseFontName`，仅对 U+F000–F0FF 字符调用。
- 新建 `app/core/content/pua_symbols.py`（独立可下架）；`read_char` 作为唯一生产调用点。
- F072 先实测顺序：I3 第 1 页基字符 a/b 在前、重音 F072 在换行之后成批出现，
  配对不可靠 → 保留原字符，不输出裸 `\vec`。
- regions.py 基线 460 行，加油前先把页底裸页码判定挪进同目录 furniture。

## [IMPL] 2026-11-20

- commit 976d8a3：新增 pua_symbols（25 条表＋族门控＋map_char/map_text/read_char）
  与 tests/test_pua_symbols（14 例）；regions.py 唯一调用点改为 `pua_symbols.read_char`；
  页底裸页码判定（含 _PDF_BARE_PAGE 正则、zone/height 常量、_has_hanzi）搬入
  furniture.py 并由 regions 引用；service.py 旧路径再导出改源。
- 收口笔：回单 docs/handoff/receipts/pua-symbol-map.md＋本 biz 记录（新建）。

## [VERIFY] 2026-11-20

- 真卷探针（`.system_generated/pua-map/probe_corpus.py`，rc=0）：
  I3 175→5（仅 F072×5，原始字体 SymbolMT×169/MT-Extra×6）；
  I1 1228→294（44→24 码位，23 个未解码码位不猜，卡面「I1→0」前提不成立）；
  A2 2130→2130、A3 88→88、I2 56→56（逐字不变）；A1/C3 普通卷前后逐字一致。
- 定向：pua_symbols＋ingest_triage＋clean_latex＋question_parser＋ingest_routing＋
  ingest_scan＋ingest_failure_surface＋file_size_contract → Ran 149 / OK / rc=0；
  page_render＋layout_router → Ran 83 / OK(4 skipped) / rc=0。
- 快门禁：PASS（6 项全过），rc=0；体积预警 22 份（基线 23，regions 423 行移出预警带）。
- 禁改区自查：LICENSE/铁律一二/question_contract/normalize_latex/dedupe_signature/
  用户 data 未触碰；onnx_probe.py 未 stage；禁 JSON 落盘；records 只新建；不 amend 不 push。
- 边界：只解 MathType 两族；Kingsoft/PMExtra 不套表；F072 保留原字符；
  新码生效需服务重启一次（65496 未接触）。

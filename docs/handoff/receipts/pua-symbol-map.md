# 回传单 · MathType 私有区符号映射（#PUA-MAP-01）

【回执编号】 #PUA-MAP-01
【回执时间】 2026-11-20 22:30:55+08:00
【执行结果】 **成**。文字直取在逐字符读取处按「字体族 + 码位」查 25 条表：
MathType 两族（SymbolMT / MT-Extra）换 Unicode 同义字符，其他家族原样保留；
F072 向量箭头重音实测排在整行之后、与基字符隔着换行，字符流内定不了基字符，
保留原字符。I3 探针 175→5（仅剩 F072×5），A2/A3/I2 前后逐字不变。
基线 operator `87dadb7`（ahead 112）；本卡两笔：`976d8a3`（代码＋测试）／
收口笔（本回单＋biz）→ ahead 114。不 push；65496 零接触；证据与验证脚本落在
`.system_generated/pua-map/`（不进 git）。

## 1. 入口与取字体名

- 入口：`app/core/ingest/render/regions.py:_pdf_text_lines` 的逐字符循环
  （`:124-125`）。这是 PDF 文字直取唯一的字符级组装点：页图题块文字
  （`_question_regions` 的 label/text）、`pdf_text_health`、版面探路都吃它的行清单。
- PUA 去向：此前原样进入行文本，题块文字里显示为乱码；不丢弃、不替换。
- 字体名怎么拿：pypdfium2 raw API，仅对命中 U+F000–U+F0FF 的字符才查——
  `FPDFText_GetTextObject(textpage.raw, i)` → `FPDFTextObj_GetFont` →
  `FPDFFont_GetBaseFontName`，得到形如 `TZCMBP+SymbolMT` 的基名。
  普通字符走原 `get_text_range`，不触发 raw 调用，普通卷逐字不变。
- 该路径与侦查脚本 `.system_generated/private-use-recon/enumerate.py` 同一套 raw 调用。

## 2.【改动清单】

- 新增 `app/core/content/pua_symbols.py`（115 行）：25 条表、族门控、
  `map_char` / `map_text`（返回映射计数）/ `read_char`（生产入口）/ `_font_name`。
  整块可下架：删文件并把 `regions.py:125` 换回 `textpage.get_text_range(index, 1)`。
- 修改 `app/core/ingest/render/regions.py`（460→423 行）：
  - `:14-16` 引入 `pua_symbols` 与 furniture 的页脚判定；
  - `:125` `char = pua_symbols.read_char(textpage, index)`（唯一生产调用点）；
  - 把页底裸页码判定 `_bare_page_footer_lines` 及 3 个常量、`_has_hanzi`
    整块挪进同目录 furniture（基线 460 行已超本卡 ≤450 要求，先腾空间）。
- 修改 `app/core/ingest/render/furniture.py`（229→266 行）：接收页底裸页码判定；
  `_PDF_BARE_PAGE` 只在此定义一份，regions 直接引用（不抄两份规则）。
- 修改 `app/core/ingest/render/service.py`：`_bare_page_footer_lines` 的旧路径
  再导出改从 furniture 取，测试仍可按 `page_render._bare_page_footer_lines` 调用。
- 新增 `tests/test_pua_symbols.py`（14 例）：25 码位逐条、族门控、F072 两序、
  非 PUA 不变、幂等、假「字符+字体名」序列、`read_char` 入口。
- 禁改区自查：LICENSE / AGENTS 铁律一二 / `question_contract.py` /
  `normalize_latex` / `dedupe_signature.py` / 用户 `data/` —— 均未触碰（否）；
  `tools/onnx_probe.py` 原地未 stage。

## 3. 表来源、族门控、F072 定案

- 表来源：`.system_generated/private-use-recon/report.toml` 的 25 个候选，
  键＝(族, 码位)，值＝报告 `candidate_unicode`（输出 Unicode 字符，不加 `$`/LaTeX）。
  SymbolMT 23 条 + MT-Extra 2 条；F04C=⋯(U+22EF)、F0D7=⋅(U+22C5) 与现有
  `scan_text` 的 `\cdots`/`\cdot` 口径一致，未另立写法。
- 族门控：字体基名（大小写不敏感）含 `SymbolMT` / `MT-Extra` 才查表；字体名缺失、
  未知族、非 U+F000–U+F0FF 一律不动。WPS-Kingsoft(A2)、PMExtra(A3/I2) 本次不解码、
  不套表。
- F072 定案：**保留原字符**。I3 第 1 页实测基字符 `a`(784.1) / `b`(801.2) 在前，
  重音 F072(784.4) / F072(801.5) 在 `\r\n` 之后成批出现，字符流内无法确定
  「基字符+重音」配对；按卡不输出裸 `\vec`，也不猜组合顺序。

## 4. 真卷探针（只读；脚本 `.system_generated/pua-map/probe_corpus.py`）

方法：同一 PDF 走两次 `_pdf_text_lines`——先把 `read_char` 换成原样读取（映射前），
再恢复生产实现（映射后），统计行文本里的 U+E000–F8FF。输出存
`.system_generated/pua-map/probe_output.txt`。

| 卷 | 家族 | PUA 前 | PUA 后 | F072 前 | F072 后 | 去重码位 前->后 |
|---|---|---|---|---|---|---|
| I3 | MathType | 175 | **5** | 5 | 5 | 25→1 |
| I1 | MathType | 1228 | 294 | 4 | 4 | 44→24 |
| A2 | Kingsoft | 2130 | 2130 | 47 | 47 | 54→54 |
| A3 | PMExtra | 88 | 88 | 0 | 0 | 14→14 |
| I2 | PMExtra | 56 | 56 | 0 | 0 | 14→14 |

- I3 原始字体归属：SymbolMT×169、MT-Extra×6（与报告一致；452 旧数未复现）。
  映射后仅剩 U+F072×5，单独列数。
- I1 实际含 44 个不同码位，本表只覆盖与 I3 重叠的 21 个（含 F072）；
  剩余 24 个码位（F072 + 23 个未解码码位）不在表内，**不猜、原样保留**，
  因此 I1 不可能归零——卡面「I1→0」的前提（两卷同 25 码）与实测不符，如实披露。
- 普通文字卷对照：A1（381 行）/ C3（112 行）PUA=0，映射前后行文本**逐字一致**。
- I3 含 PUA 正文前 5 行对照（节选）：
  - 前 `B．若 ，则 x  y  z  0` → 后 `B．若 ，则 x + y + z = 0`
  - 前 `D．若 … 则  β ≤α` → 后 `D．若 … 则 β ≤α`（原样输出映射结果）
  - 前 `q :“cos 0 ”` → 后 `q :“cosα > 0 ”`
  - 前 `B．若 为第一象限角` → 后 `B．若α 为第一象限角`
  - 前 ` `（两个不可见 PUA）→ 后 `α α`

## 5. 命令与 rc

```
.venv/Scripts/python.exe -m unittest tests.test_pua_symbols tests.test_ingest_triage \
  tests.test_clean_latex tests.test_question_parser tests.test_ingest_routing \
  tests.test_ingest_scan tests.test_ingest_failure_surface tests.test_file_size_contract
→ Ran 149 tests / OK / rc=0

.venv/Scripts/python.exe -m unittest tests.test_page_render tests.test_layout_router
→ Ran 83 tests / OK (skipped=4) / rc=0   # 沾边模块（页脚判定搬家）

bash scripts/check-quick-gate.sh
→ check-quick-gate: PASS（6 项全过）/ rc=0；体积预警 22 份（基线 23，regions 移出预警带）

PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe .system_generated/pua-map/probe_corpus.py
→ rc=0（表见 §4）
```

## 6. 未决问题与偏离

- 偏离①：`regions.py` 开工实测 460 行，已超本卡「≤450」要求；为只加一条调用又
  不越线，把页底裸页码判定整块搬进同目录 `furniture.py`（语义零改，service 旧路径
  再导出保留）。实测 `regions.py` 423 行、furniture 266 行。
- 偏离②：卡面验收「I1 映射后 PUA→0」不成立：I1 有 44 个不同码位，报告表只有 25 条，
  23 个码位身份未解码；未解码的不猜，保留原字符（见 §4）。
- 边界：只解 MathType 两族；Kingsoft/PMExtra 本次不套表。F072 保持原字符，
  其上方重音与基字符的合成留给后续结构化方案。
- 未验证：前端界面真人路径未走（本次是后端清洗层，无 UI 改动）；
  新码生效需服务重启一次（65496 未接触，仍跑旧码）。

## 7. 收口

- commit 1 `976d8a3`（代码＋测试，点名 stage）；commit 2 收口笔（本回单＋biz）。
- 身份用瞬态 `-c user.name=MT-Blaze -c user.email=tianxiulaoshi@163.com`，未写 git config。
- `git log --oneline -3` / `git status` / `git rev-list --count origin/main..HEAD` 见回传。
- 不 push（奉令 hold）。

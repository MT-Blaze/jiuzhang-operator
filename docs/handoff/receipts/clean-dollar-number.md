# 回传单 · 第 57 条落清洗器（#CLEAN-DOLLAR-NUMBER-01）

【回执编号】 #CLEAN-DOLLAR-NUMBER-01
【回执时间】 2026-11-20
【执行结果】 **成**。第 57 条「`$` 只圈表达式，不圈数字」落到清洗器三处，同一实现零复制；
`$$`、未闭合/转义 `$`、带字母/运算符/命令的段一律不动。

基线：operator `63ca1bd`（ahead 101）；本卡两笔——`6c19e01`（模块＋接入＋测试＋文档）／
收口笔（本回单＋biz）；ahead 101→103。两仓不 push；插件仓零改零升版零重打 zip；
65496 零接触；工作树脏件仅 `?? tools/onnx_probe.py`，原地保留不 stage。

## 1. 规则（A）

新增 `app/core/content/dollar_number.py`（33 行，独立可整块下架）：
`unwrap_bare_number_dollars(text) -> (新文本, 拆掉个数)`。
只拆行内 `$...$`，段内去首尾空白后整体为纯数字才拆：可选正负号（含 U+2212 `−`）、
小数、百分号（`%` 或 `\%`）、度数 `°`。拆下后数字原样输出（`\%` 维持 `\%`），不转全角、不补空格。
`$$...$$` 整段跳过（第一支正则先整段吞掉，含未闭合 `$$` 到行尾）；转义 `\$` 不误认；
未闭合 `$` 与空段原样返回。行内支 `(?<![\\$])\$(?!\$)` 两头挡住连接/转义/成对双币符。

## 2. 接入三处（B，同一实现）

| 位置 | 接点 | 记录 |
|---|---|---|
| `question_parser._clean_fragment`（编辑器【清洗当前题 LaTeX】→ `clean_dirty_latex`） | `normalize_latex` 之后、`latex_norm.clean` 之前 | 每拆一次向 `rules` 记 `dollar_number`（沿用 `dict.fromkeys` 去重） |
| `question_parser.clean_question`（保存前） | stem／solution／options[].content／answer.content／answer.final 各自 `normalize_latex` 之后 | 经 `_without_bare_number_dollars` 小包装，只取新文本 |
| `ingest/intake/text.py._document`（文字直取，:234/:238 原行） | stem 与选项 content 的 `normalize_latex` 之后 | 同函数 `[0]` |

`question_parser.py` 481→488 行，未越 500（卡面「越过 500 就停手」未触发）；
`dollar_number.py` 21 行，不在 451–550 预警区。`clean_exam_source` 未接（见 §3）。

## 3. 明确不动（C）

- `normalize_latex` 本体（查重指纹 `dedupe_signature.py:48` 复用，改了会漂移存量签名）；
- `latex_norm.py` / `latex_style_dict.py` / 第 50 条查重口径；
- `clean_exam_source`（exam-zh 源码＝格式宪法载体，不拆）；
- 「`$3\text{ cm}$`」这类带单位且含命令的段（含字母/命令，保守保留），记为已知边界。

## 4. 测试（E，第 49 条回归表全绿）

`tests/test_clean_latex.py` 新增 `DollarNumberCleanerTest` 5 案；`tests/test_question_parser.py`
`CleanQuestionTest` 增 `test_06`（五字段同时生效＋入参不被就地改）。

| 用例 | 输入 | 期望 |
|---|---|---|
| 四例① | `已知有 $3$ 个` | `已知有 3 个` |
| 四例② | `$3$` | `3` |
| 四例③ | `当 $n=3$ 时`／`$x=3.5$` | 原样（$ 保留） |
| 四例④ | `3 cm` | 原样 |
| 反例 | `$2x$`、`$a_1$`、`$\frac{1}{2}$`、`$1.5\times10^3$` | 模块层逐字不变、`$` 保留 |
| 反例 | `$$3$$`、`\$3\$`、未闭合 `$3` | 原样 |
| 反例 | `$$a $3$ b$$`、未闭合 `$$…$3$` | 整段原样（`$$` 段内不拆） |
| 百分号 | `$50\%$` | `50\%` |

说明：`$a_1$`、`$1.5\times10^3$` 经 `clean_dirty_latex` 仍会按第 49 条既有字典补上标括号
（`a_{1}`、`10^{3}`）——那是旧规则，本卡只保证不解 `$`；模块层用逐字相等钉死「本刀不动」。

定向五模块（禁 discover/pytest）：

```
.venv/Scripts/python.exe -m unittest tests.test_clean_latex tests.test_question_parser \
  tests.test_latex_norm tests.test_latex_style_dict tests.test_file_size_contract
Ran 146 tests ... OK  rc=0
```

`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**；体积预警 **23 份**（与基线相同），
新模块不在预警区。

## 5. 文档（D）

`docs/question-cutting-pipeline.md:83` 第 57 条末尾追加一句（原句未改）：
「2026-11-20 小卡 #CLEAN-DOLLAR-NUMBER-01 已落清洗器：clean_dirty_latex、保存前 clean_question、
文字直取 intake 三处拆行内纯数字 $；$$、exam-zh 源码路与查重指纹归一不动。」

## 6. 已知边界与偏离

- 已知边界：`$3\text{ cm}$`（带单位＋命令）不拆，卡面即定保守；`$ 3 $`（段内留白）会拆成 `3`，
  符合「去首尾空白后整体是纯数字」；未闭合 `$$` 整段原样。
- 偏离：无代码面偏离。仅一处 commit 组合偏离：首笔 `6c19e01` 落模块初版后，发现 `$$` 段内
  非法嵌套 `$3$` 会被行内支拆掉，补了「先整段跳过 `$$`」的边界补丁（模块 21→33 行）；因卡面
  「不 amend」未改写首笔，该补丁随本收口笔一并提交（本笔含 `dollar_number.py` 一处代码改动），
  两笔合计仍为 ahead 101→103。三处接入、插件、版本号均无额外改动。
- 补测（#CLEAN-DOLLAR-NUMBER-01T）：`tests/test_question_parser.py` 新增 `DollarNumberCleanQuestionTest`，
  断言 `clean_question` 对 stem/solution/options/answer 拆纯数字 `$`（`$2x$` 保留）且不就地修改入参；
  commit hash 见本笔。

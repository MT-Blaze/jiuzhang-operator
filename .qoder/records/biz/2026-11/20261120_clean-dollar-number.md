# 第 57 条落清洗器（clean-dollar-number）

状态：收口（两笔已 commit 不 push；生效需主公重启一次）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达小卡 #CLEAN-DOLLAR-NUMBER-01（主公 2026-11-20 点头出卡）
基线：operator 63ca1bd（ahead 101）；本卡 operator 两笔（6c19e01／收口笔），ahead 101→103；plugins 零改
回单：docs/handoff/receipts/clean-dollar-number.md

## [REQ] 2026-11-20

规则第 57 条已成文（docs/question-cutting-pipeline.md:83）：`$` 只圈数学表达式，不圈数字本身；
原文预留「将来若要清洗器自动拆数字的 `$`，须另开卡并用第 49 条正反例回归表证明不误伤
`$x=3$`」。本卡即该刀：新建独立模块拆行内纯数字 `$`，接入编辑器清洗、保存前清洗、文字直取
三处；`$$`、exam-zh 源码路、查重指纹归一、latex_norm/写法字典/第 50 条口径一律不动。
卡面禁令：question_parser 过 500 行即停手；禁 discover/pytest；1 笔代码＋1 笔收口；
身份用 -c 瞬态；不 amend；红即停；65496 禁动；两仓不 push。

## [IMPL] 2026-11-20

- 新增 app/core/content/dollar_number.py：`unwrap_bare_number_dollars(text) -> (text, count)`。
  正则第一支整段吞 `$$…$$`（含未闭合到行尾），第二支匹配行内纯数字
  `(?<![\\$])\$(?!\$)\s*(NUMBER)\s*\$(?!\$)`；NUMBER＝可选 ±/−、小数、`%`/`\%`、`°`。
- 接入三处（同一函数，零复制）：
  1. question_parser._clean_fragment：normalize_latex 之后、latex_norm.clean 之前；
     拆了才向 rules 记 "dollar_number"（沿用 dict.fromkeys 去重）。
  2. clean_question：stem/solution/options[].content/answer.content/answer.final，
     经 `_without_bare_number_dollars` 小包装（只取文本）。
  3. ingest/intake/text.py._document：stem 与选项 content。
  question_parser 481→488 行，未越 500；dollar_number.py 33 行，不在预警区。
- 文档：第 57 条末尾追加一句小卡落点，原句未改。
- 测试：tests/test_clean_latex.py 新增 DollarNumberCleanerTest（四例钉死＋反例＋百分号/符号/度数＋
  幂等）；tests/test_question_parser.py CleanQuestionTest.test_06 五字段同时生效＋入参不改。

## [VERIFY] 2026-11-20

- 定向五模块（禁 discover）：clean_latex/question_parser/latex_norm/latex_style_dict/
  file_size_contract → Ran 146 tests, OK, rc=0。
- bash scripts/check-quick-gate.sh → PASS（6 项全过）；体积预警 23 份与基线相同。
- 实测边界：`$$a $3$ b$$`、`$$unclosed $3$` 整段不动；`$a_1$`/`$1.5\times10^3$` 的 `$` 保留
  （上标括号属第 49 条既有字典行为，非本卡），模块层逐字相等钉「本刀不动」。

## [RELEASE] 2026-11-20

两笔：6c19e01（模块＋三处接入＋测试＋文档）／收口笔（`$$` 段跳过边界补丁＋本回单＋本记录）。
偏离：边界补丁因「不 amend」并入收口笔，未改写首笔；其余零偏离。push 全 hold；
65496 零接触；生效需主公重启一次。

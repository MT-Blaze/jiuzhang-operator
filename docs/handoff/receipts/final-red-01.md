# 回单 · FINAL-RED-01 修第 57 条卡引入的两处存量红（定向）

【任务卡】#FINAL-RED-01
【日期】2026-11-20
【基线】HEAD `c3fa6fc`，ahead 118；开工时工作树仅 `?? tools/onnx_probe.py`（未 stage、未提交）
【结论】两处存量红全绿；根因确认为枢纽怀疑项（比对尺子未同步第 57 条）；守卫 11 模块＋快门禁 PASS。

## 1. 根因证据（改前后最小复现）

**确认**：`6c19e01`（#CLEAN-DOLLAR-NUMBER-01）只在**写路**拆纯数字 `$`，查重的**比对尺子**没同步：

- 写路：`app/core/bank/engine/write.py:364` 入库前 `question_parser.clean_question`，其
  `_clean_fragment`/`clean_question` 调 `dollar_number.unwrap_bare_number_dollars`（`$3$`→`3`）；
  中转站池内文档则照存原文（`$1$`…`$4$`）。
- 比对路：`latex_style_dict.normalize_for_compare`（→ `_rewrite(compare=True)`）与
  `dedupe_signature._compare_form` 仍按 `$` 切段，导致同一道题在主库清洗稿与待审原文两侧
  指纹/骨架/签名互不相等。

最小复现（用 `git show c3fa6fc:app/core/content/latex_style_dict.py` 载入旧模块，不动工作树）：

```
OLD normalize_for_compare("则 $0$ ____") -> '则$0$____'
OLD normalize_for_compare("则 0 ____")   -> '则 0 ____'      # 不相等
NEW 两者均 -> '则 0 ____'
NEW normalize_text/skeleton/formula_signature/number_sequence 两侧均相等（sig='0'、nums=['0']）
```

红一现场：`则 $0$ ____` vs 产品 `则 0 ____`（快照陈旧，产品方向正确）。
红二现场（修前 `tests.test_pending_api`）：
- precheck `hit=False, similarity=0.875, level=''`；信号明细
  `签名差异：… 6 1 2 3 4 ↔ … 6`、`数字差异：2 1 5 1 2 3 4 ↔ 2 1 5`——选项 `$1$…$4$`
  只在待审侧进签名；
- `PoolEvictionHttpTest` pooled 1≠4 / 1≠2、done 帧 pending_count 1≠0；
- 合并文档 id 断言不符；直调 approve 409 期望实得 200。
9 案失败簇全部落在指纹/答案闸门，与「两侧指纹不等」一致。

## 2. 修法（单源一把尺子）

1. `app/core/content/latex_style_dict.py:210` `_rewrite`：比对态（compare=True）**在切数学段之前**
   调 `dollar_number.unwrap_bare_number_dollars`，与写路同一正则、同一函数；命中记规则名
   `dollar_number`；`changed` 仍对原文计算。写库态（compare=False）一字未动。
2. `app/core/bank/engine/dedupe_signature.py:275` `_scan_runs`：第 57 条后数字住在正文里，
   签名与数字序列按原顺序同时扫数学段与正文裸数字（`_BARE_NUMBER`，:190），使 `$3$` 与 `3`
   在指纹、骨架、公式签名、数字序列上逐路相等。
3. 快照随第 57 条转正（不反向改产品）：
   - `tests/fixtures/bdp01/before.toml:236`：q16 的 `则 $0$ ____` → `则 0 ____`；
     已核实该 `0` 在 `full_md_fix_16.md` 里独立于任何数学表达式（前后为中文与下划线空位）。
   - `tests/test_pending_api.py:1077`：test_52 原断言要求主库题面与池内原文逐字相同；
     核实 `keep_separate` 走主库写路（按第 57 条清洗），产品正确，故改比**拆后**题面
     （复用生产函数 `unwrap_bare_number_dollars`，不另立口径）。

未改：`data/`、SQLite 结构、依赖、`app/core/question_contract.py`、LICENSE、根 agents.md、65496 进程。

## 3. 逐模块数字（`.venv/Scripts/python.exe -m unittest tests.<模块>`，逐个独立进程）

| 模块 | 结果 |
|---|---|
| tests.test_build_documents_shapes | Ran 23, OK |
| tests.test_pending_api | Ran 35, OK (skipped=5) |
| tests.test_clean_latex | Ran 18, OK |
| tests.test_question_parser | Ran 49, OK |
| tests.test_bank_dedupe | Ran 21, OK |
| tests.test_dedupe_fingerprint | Ran 38, OK |
| tests.test_pending_dedupe | Ran 14, OK |
| tests.test_pending_dedupe_candidates | Ran 20, OK |
| tests.test_pending_dedupe_scan | Ran 18, OK |
| tests.test_pending_pool | Ran 44, OK |
| tests.test_latex_style_dict | Ran 30, OK |
| tests.test_latex_norm | Ran 37, OK |
| tests.test_ingest_triage | Ran 21, OK |

守卫断言零修改（`test_dedupe_fingerprint` 的 `number_sequence($0.5$)==['0.5']`、
`$0.5$`↔`1/2` 签名不等、`$3!$`↔`$3$` 指纹不等均原样绿）。

## 4. 门禁

```
bash scripts/check-quick-gate.sh
check-quick-gate: PASS（6 项全过）   rc=0
体积预警 22 份（均为既有文件，无本卡新增越线）；静态审计 ERROR 0
```

行数自查：`dedupe_signature.py` 549 行（冻结台账老文件，原 540；≤550）、
`latex_style_dict.py` 518 行（冻结台账老文件，原 506）。未跑全量 138 模块。

## 5. 是否改断言及理由

- 改 1 处测试期望（test_52）+ 改 1 处基线快照（bdp01 q16），均为「产品行为确实正确」：
  第 57 条让写路把只圈数字的 `$` 拆成裸数字，主库稿与快照必须先于该规则，属陈旧基线。
- 未放宽/删除任何查重断言，未调阈值。

## 6. 提交

- commit 1（产品/快照）：`6c5cb15` 查重比对归一同步第 57 条：纯数字 $ 拆成裸数字（#FINAL-RED-01）
  —— 4 files, +35 −11。
- commit 2（本回单＋biz）：见收口段。
- 未 push；未 `git add -A`；未 amend；未写 git config（瞬态 `-c user.name=MT-Blaze -c user.email=tianxiulaoshi@163.com`）；
  `tools/onnx_probe.py` 保持未暂存。

## 7. 遗留

1. 签名/数字序列现在会收正文里的裸数字（含题号式数字，如「16.」）。这是第 57 条把数字
   移出数学段后的必然口径；跨来源同题若题号不同，置信档可能从「很像」落到「较像」
   （默认宽档仍召回）。列为观察项，若实测降档影响召回，另开卡在切段层去题号。
2. `dedupe_signature._math_runs` 本模块内已无调用，仍由 `dedupe.py` re-export；
   待 `engine/dedupe.py` 下一次拆分时一并退休。
3. 中转站池内文档仍存清洗前原文（`$1$`），入库那刻由主库写路清洗——设计如此，
   比对尺子已保证两侧相等；若将来要求池内也提前规范化，另开卡。
4. push hold。

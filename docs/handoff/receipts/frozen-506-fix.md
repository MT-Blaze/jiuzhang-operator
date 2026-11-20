# 回单 · FROZEN-506-01 比对归一搬出冻结模块，恢复 latex_style_dict 506 行（定向）

【任务卡】#FROZEN-506-01
【日期】2026-11-20
【基线】HEAD `84d46dc`，ahead 120；开工时工作树仅 `?? tools/onnx_probe.py`（未 stage、未提交）
【结论】冻结模块复原 506 行；第 56 条红线复位；比对行为等价；必绿 2 模块＋守卫 11 模块全绿；快门禁 PASS。

## 1. 红线出处

`docs/question-cutting-pipeline.md:82` 第 56 条（2026-11-19 主公点头）：
「老模块冻结 **506 行只减不增**、只改『字典从参数取』原地接线」。
上一卡 #FINAL-RED-01（`6c5cb15`）把比对态拆纯数字 `$` 的代码写进
`app/core/content/latex_style_dict.py`，506→518 行，越线；本卡把它搬出冻结模块。

## 2. 复原前后 wc

| 时点 | `wc -l app/core/content/latex_style_dict.py` |
|---|---|
| 完工前（HEAD `84d46dc`） | 518 |
| 复原后 | **506** |

复原方式：`git show 6c5cb15^:app/core/content/latex_style_dict.py` 整文件写回；
残留核查 `grep -c "dollar_number\|unwrapped\|source"` = 0。该文件其余内容零改
（相对 HEAD 仅回退 3+/15−，即上一卡那一整段）。

## 3. 新入口与接线

- 新建 `app/core/content/latex_compare.py`（27 行 ≤60）：`normalize_for_compare(text, aliases=None)`
  先 `dollar_number.unwrap_bare_number_dollars`（仅 str；非 str 原样交冻结模块），再走
  `latex_style_dict.normalize_for_compare`；命中拆包补 `rules += dollar_number` 且
  `changed=True`（相对调用方原文），未命中原样返回。docstring 写明第 56 条与「比对态 $ 拆包
  与写路同口径，所以入口住这里」。
- 接线 `app/core/content/latex_norm.py:446`：`clean(compare=True)` 改走
  `latex_compare.normalize_for_compare`（lazy import 与 `style` 合并同一行，文件仍 449 行）。
- `app/core/bank/engine/dedupe_signature.py` 的 `_compare_form` 走 `latex_norm.clean(compare=True)`
  自动覆盖；`_scan_runs` 裸数字扫描一字未动（549 行）。

## 4. 行为等价证据（三条）

```
$ python -c "from app.core.content import latex_compare, latex_style_dict; ..."
latex_compare("则 $0$ ____")["text"] == latex_style_dict("则 0 ____")["text"]   -> True
    text='则 0 ____'  rules=['dollar_number']  changed=True
latex_compare("$1$ $2$")["text"]      == latex_style_dict("1 2")["text"]        -> True
    text='1 2'  rules=['dollar_number']
latex_compare(None) / latex_compare(3) -> {'text': '', 'changed': False, 'rules': [], 'unknown': []}（不炸）
```

（`则` 在 GBK 控制台显示为乱码属终端编码，断言在 Python 内部按 str 比较通过。）

## 5. 逐模块数字（`.venv/Scripts/python.exe -m unittest tests.<模块>`，逐个独立进程）

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
| tests.test_latex_style_dict | Ran 32, OK（原 30，+2 本卡等价测试） |
| tests.test_latex_norm | Ran 37, OK |
| tests.test_ingest_triage | Ran 21, OK |

新增测试 `CompareEntryTest`（`tests/test_latex_style_dict.py`）钉两件事：
`$0$ ____` ↔ `0 ____`、`$1$ $2$` ↔ `1 2` 比对后逐字相等且 `rules` 含 `dollar_number`；
`None/3/b"$1$"` 非字符串不炸。未加「本文件必须 506 行」护栏测试（纸面单源，靠 wc 核）。

## 6. 门禁

```
bash scripts/check-quick-gate.sh
check-quick-gate: PASS（6 项全过）   rc=0
体积预警 22 份（与基线持平，无本卡新增越线）；静态审计 ERROR 0
```

行数：`latex_norm.py` 449（≤450）、`latex_compare.py` 27（≤60）、`dedupe_signature.py` 549（≤550）。
未跑全量 138 模块。

## 7. 提交

- commit 1（复原＋新入口＋接线＋测试）：`4680b45`，4 files, +56 −18。
- commit 2（本回单＋biz）：随本文件提交。
- 未 push；未 `git add -A`；未 amend；未写 git config（瞬态 `-c user.name=MT-Blaze -c user.email=tianxiulaoshi@163.com`）；
  `tools/onnx_probe.py` 保持未暂存。

## 8. 遗留

1. 上一卡已改正的 bdp01 q16 快照与 `test_pending_api` test_52 断言原样保留，未回退。
2. `dedupe_signature._math_runs` 已无模块内调用（仍由 `dedupe.py` re-export），待 `engine/dedupe.py`
   下次拆分时一并退休。
3. push hold。

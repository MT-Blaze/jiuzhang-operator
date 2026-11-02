---
name: run-regression
description: 九章算子的全量回归与证据采集动线：快门禁 → 逐模块单测 → 真机探针 → 像素证据，并把原始输出整理成可交付证据。当需要跑回归、验证一次大改动、复现"到底哪几绿哪几红"或出回传单测试项时使用。
---

# run-regression：跑回归并采集机械证据

> 原子范围：只跑验证与取证，不改业务代码。发现的缺陷结构化交回 coder，不顺手修。
> 前提：R04 全文。**测新规则/新改动必须先做差集**——同一份判据在改动前后各跑一次。

## 档位

| 档 | 命令 | 耗时 | 用在 |
|---|---|---|---|
| 快门禁 | `bash scripts/check-quick-gate.sh` | 秒级 | 每个阶段收尾 |
| 收尾门禁 | `bash scripts/check-release-gate.sh` | 分钟级 | 工序 06、发版前 |

## 步骤

1. **先看在途状态**：`git status --short`——分清「已完成未提交」与真欠账。当前基线里 4 支 demo 插件是用户人为删除（不恢复不暂存），4 个 handoff 文件是别人的在途工作（**不要 stage**）。
2. **快门禁**：`bash scripts/check-quick-gate.sh`，记录 6 项里哪项红。
3. **逐模块单测**：
   - 单模块：`.venv/Scripts/python.exe -m unittest tests.<模块名>`
   - 全量：`.venv/Scripts/python.exe tools/run_all_tests.py`（末行给「模块 N 个，用例 N 个，失败模块 N 个」）
   - **[L0] 禁止**：系统 `python`（实测导入即崩）、`python -m unittest discover`（实测 `Ran 0 tests / NO TESTS RAN`，绿色假通过）、pytest（未装且违反 STACK §6）
   - 22 个起 uvicorn 的模块清单见 R04 §1.6；触碰切库/重启端点的用例要 `JZO_RESTART_DISABLED=1`，否则服务把自己重启带走。
4. **真机探针**：按改动面挑对应 `tools/*_probe.py` 跑（**无统一 runner，属已知欠账**）；产物落 `.system_generated/<探针名>/<tag>/probe.json` + 截图；跑完用 `bash scripts/check-probe-reports.sh` 归一判最新跑批。
   - 探针判据可能跑在死代码上：涉及滚动/布局的改动，先确认被测路径真在生效（行高不锁 → 滚动逻辑全是死代码）。
   - 程序化 `focus()` 不算人手操作；假时钟推不动 `setTimeout` 链。
5. **前端真人路径**：browser-use 打开底座（默认 8000，被占自动顺延到 8009），点/拖/滚/键盘走一遍用户路径，截图存档。
6. **像素证据**（视觉类必做）：`.venv/Scripts/python.exe tools/pixel_scan.py <png>` 取行段归类结论——注意它无判定恒 rc=0，属于素材不是门禁。
7. **计数复核**：自报的任何数字（模块数、用例数、题数、判据数）都要来自当次输出；扫描前先确认没被 junction/ignore 静默跳过。

## 自检

- [ ] 每个数字都有当次原始输出可回溯（`Ran N tests`、`passed/total` 原样粘贴）
- [ ] 探针报告能被 `check-probe-reports.sh` 识别（三种历史 schema 之一）
- [ ] 未验证项显式写「未验证」，不用推测代替证据
- [ ] 回传单第 4 项（测试与探针）已填全：跑了哪些模块、各自 N/N、探针 passed/total、截图与 probe.json 落盘路径

# 回单 · NDT-CLAUSE-AUDIT-01 记号标准条款级审计（只动文档）

【任务卡】#NDT-CLAUSE-AUDIT-01
【日期】2026-11-20
【范围】`docs/question-cutting-pipeline.md` 仅追加两节：57 条条款级判定表、标准条款出处复核。未碰题库数据、未改清洗器/解析代码、未改铁律冻结面。

## 1. 正文落点

在 `docs/question-cutting-pipeline.md` 末尾追加（原 57 条正文一字未改）：

- `## 条款级判定表（NDT-01 条款级审计）`：57 行，列＝条号｜规则一句话｜判定条件（输入→判据→输出）｜正例｜反例｜落点（模块/函数或「纸面」）｜状态。
- `### 标准条款出处复核（限时 15 分钟）`：GB/T 3102.11-1993 与 ISO 80000-2:2019 公开可读性结论。

落点全部按实际代码 grep/read 核验；核不到函数的记「缺口」，未编函数名。判定条件均写成可落单测的输入/判据/输出。

## 2. 条数核对（命令与结果）

```
awk 'NR>=20 && NR<=84' docs/question-cutting-pipeline.md | grep -cE '^[0-9]+\. '
57

awk '/^## 条款级判定表/{f=1;next} f && /^\| [0-9]+ \|/{n++} END{print n}' docs/question-cutting-pipeline.md
57

awk -F'|' '/^\| [0-9]+ \|/{gsub(/ /,"",$8); c[$8]++} END{for(k in c) print k, c[k]}' docs/question-cutting-pipeline.md
纸面 3
缺口 22
已落 32
```

覆盖：57/57。状态分布：已落 32 / 纸面 3 / 缺口 22。

## 3. 缺口清单（22 条，落点未找到实现）

条 6（答案 role：`IMAGE_ROLES` 仅 stem/option/solution）、8（tikz 专属插件）、14（pending.approve 后端占位校验）、15（按 role 插图位）、16（`%` 注释渲染）、19（`% AI生成` 标记）、20（思考档位）、21（Ctrl+Z 快照）、22（四类答案形态）、23（格式样本库）、24（封面/目录/答题卡清理）、27（未完成批次续跑）、29（通过后自动删批）、31（从解答抽取答案）、32（解题位选择器）、33（三槽拆分）、34（自动考试方向）、35（主题树下沉）、37（思考档位基准）、38（成品库）、40（样例题收集按钮）、46（去掉【存为待审】）。

纸面 3 条：10（不动老题库）、12（不做跨文件答案配对）、39（成品只引用 q_ ID）。

## 4. 标准条款出处复核结论

- GB/T 3102.11-1993：官方页（openstd.samr.gov.cn）现行，「采」ISO 标准；页面明示「由于涉及版权保护问题，本系统暂不提供在线阅读服务」，全文不可公开阅读 → **条款号未核 0 条**。
- ISO 80000-2:2019：`iso.org/standard/64973.html` 与 OBP 公开页本轮均 HTTP 403（访问策略拦截）；历史 2026-11-19 有头浏览器证据仅证明标准存在/36 页/ISO/TC 12，全文付费 → **本轮未复核，条款号未核 0 条**。
- 现有标签只到族级（关系与不等、运算与算子、集合与逻辑、几何与向量、微积分、上下标与根式、特殊常数、文本与间距），符合 2.21.0 已定口径。
- 结论：57 条判定表不引用任何标准条款号；NDT-01 仍为条款级欠账（不编条款号）。

证据：`.system_generated/ndt-clause/standards-2026-11-20.toml`（页面摘录 TOML，非 JSON）。该目录被 `.gitignore:18` 忽略，仅本机留档，不随提交入库。

## 5. 验收命令与 rc

```
bash scripts/check-quick-gate.sh
...
check-quick-gate: PASS（6 项全过）
RC=0
```

- 静态红线审计 ERROR 0 / WARN 35 / INFO 3（存量，非本卡引入）。
- `git diff --stat`（提交 1 前）：仅 `docs/question-cutting-pipeline.md` 1 文件 +87 行。
- 未 push；未 `git add -A`；未 amend；未写 git config；`tools/onnx_probe.py` 保持未暂存。

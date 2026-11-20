# 业务记录 · NDT-01 记号标准条款级审计（只动文档）

【状态】 已发布
【发起日期】 2026-11-20
【需求名】 ndt-clause-audit
【交付版本】 底座文档追加（c4c3afd→010afe3 ／ 回单提交随后，不 push hold）

## [REQ] 2026-11-20

背景：2.21.0 已落第 57 条记号清洗规则，但标准出处只核到族级；GB 采用 ISO 涉版权、
ISO 全文付费，逐条条款号从未核过。主公拍板（2026-11-20）NDT-01 只做条款级：不批量回写
存量、不碰 data/。规矩：核不到＝欠账，不编。
验收：57 条拍板清单逐条给判定条件/正反例/落点/状态；落点 grep 实证；标准公开页限时 15 分钟
复核（不买不登录不绕墙）；快门禁全过；只动文档。

## [IMPL] 2026-11-20

- `010afe3` `docs/question-cutting-pipeline.md` 末尾追加「条款级判定表」（57 行，含每条的
  输入→判据→输出、正反例、模块/函数落点、已落/纸面/缺口）与「标准条款出处复核」；原文 57 条一字未改。
- 落点逐条 read/grep 核验：answer role（question_contract.py:30）、重题四要素
  （dedupe_signature.py / pending/dedupe/compare.py）、清洗闭集（latex_norm.py:428 clean）、
  `$` 数字（dollar_number.py / question_parser.py:416）、扫卷摄入（ingest/service.py:187）、
  框选题区（render/regions.py:165）、家具过滤（render/furniture.py:43）等。
- 缺口 22 条按实登记（答案 role、tikz 插件、占位校验、思考档位、Ctrl+Z、成品库等），不编函数名；
  纸面 3 条（不动老库、不做跨文件配对、成品只引 q_ ID）。
- 标准复核证据 `.system_generated/ndt-clause/standards-2026-11-20.toml`（TOML，非 JSON；
  `.gitignore:18` 忽略，仅本机留档）。
- 使用 skill：无（纯文档任务）。

## [VERIFY] 2026-11-20

- 条数核对：原清单 grep `^[0-9]+\. ` = 57；表内数据行 57；状态 已落 32 / 纸面 3 / 缺口 22。
- `bash scripts/check-quick-gate.sh` rc=0（6 项全过；静态红线 ERROR 0 / WARN 35 存量）。
- `git diff --stat` 仅 docs 1 文件 +87 行；未 push、未 -A、未 amend、未写 git config、
  `tools/onnx_probe.py` 未暂存。
- 标准：GB 官方页明示版权不提供在线阅读；ISO 两入口 HTTP 403。条款号可核 0 条，如实记欠账。

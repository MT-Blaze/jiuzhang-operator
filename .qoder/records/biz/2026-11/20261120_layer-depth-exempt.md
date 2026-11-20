# 证据目录豁免目录≤3 层约束（layer-depth-exempt）

状态：已收口（纸面落条款，零脚本改动；不 push）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达任务卡 #LAYER-DEPTH-EXEMPT-01
基线：operator HEAD 49756b3（ahead 110）；本卡两笔（af5980a／收口笔）
回单：docs/handoff/receipts/layer-depth-exempt.md（#LAYER-DEPTH-EXEMPT-01）

## [REQ] 2026-11-20

主公 2026-11-20 拍板：目录≤3 层约束对 `.system_generated/` 探针与证据产物豁免——
证据目录按产物自身结构组织，天然会更深；代码与文档目录仍守 ≤3 层。
落地要求：AGENTS §4 深度封顶四句后追加一句豁免条款，原四句不重排、铁律条目不碰；
先 grep 确认有无脚本硬校验深度，有则只给 `.system_generated` 加豁免并补单测，无则回单写明。

## [PLAN] 2026-11-20

先侦查后落笔：grep scripts/tools/tests 的层/depth/layer 命中，逐一排除伪命中
（audit_code.py:172 是规则作用域判断、clean_for_release.py:159 是打包路径判据），
并核 check-quick-gate.sh 六项确无深度检查 → 判定「纸面约束、无脚本门禁」，
按卡令分支零脚本改动，只落 AGENTS.md 条款。措辞沿用「（YYYY-MM-DD 主公裁）」署名格式。

## [IMPL] 2026-11-20

- commit af5980a：docs/AGENTS.md §4 深度封顶 ④ 之后（第 74–76 行）新增 3 行豁免条款；
  原 ①②③④ 四句一字未动；根 agents.md、铁律一/二、其余章节未触碰。
- 脚本/测试/生产代码零改（无脚本门禁）。
- 收口笔：回单 docs/handoff/receipts/layer-depth-exempt.md＋本 biz 记录（新建）。

## [VERIFY] 2026-11-20

- 快门禁：bash scripts/check-quick-gate.sh → PASS（6 项全过），rc=0；
  静态红线 ERROR 0 · WARN 35 · INFO 3（WARN 全既存落点）；体积预警 23 份均既存。
- git diff --stat：仅 docs/AGENTS.md「1 file changed, 3 insertions(+)」（收口笔前实测）。
- 全量回归免：AGENTS §7 2026-11-18 拍板（定向＋门禁为主），本卡零代码改动无沾边模块。
- 禁改区自查：LICENSE/铁律一二/根 agents.md/question_contract.py/用户 data/ 未触碰；
  onnx_probe.py 原地未 stage；65496 零接触；禁 JSON 落盘；records 只新建；点名 stage 不 amend 不 push。
- 边界：豁免仅限 `.system_generated/` 证据产物；代码与文档目录（app/static/plugins/docs/tests/scripts/tools、
  插件 src/<id>/、.qoder/）仍守 ≤3 层。

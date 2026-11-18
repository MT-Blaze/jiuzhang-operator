# 减税第二刀：归档已收口死重文档 + 落地三裁决 + 全量回归口径变更

- 日期: 2026-11-18
- 类型: doc
- 执行者: 执行子会话（减税第二刀，讨论枢纽 4a0d74c0 接力）
- 等级: L1

## 变更内容

### 一、归档 33 个文件（只挪位置，一字不改；非删除）

原样备份：`E:\jiuzhang\归档备份-20261118\<原相对路径>`（33 份）。全部 `git mv`，git 判 R100（相似度 100%），
备份↔新位逐文件 diff 33/33 全等。各组映射表（唯一事实源）见各归档位 README：

| 组 | 原位置 → 新位置 | 映射表 |
|---|---|---|
| CORE 三件套（MODULE_INVENTORY / REFACTOR_RISKS / TARGET_TREE） | `docs/` → `docs/archive/migration-blueprint/` | 该目录 README（D15→台账本体；瘦身卡→`tests/test_file_size_contract.py`） |
| handover_summary、两份验收报告、PROGRESS.md | 根目录 / `docs/` → `docs/archive/` | `docs/archive/README.md` |
| 模板 2 份（AGENTS.md.tmpl、skill-bank.json.tmpl） | `.qoder/templates/` → `docs/archive/retired-templates/` | 该目录 README |
| 回执 033/034/035（036 留守） | `docs/handoff/receipts/` → 同目录 `archive/` | 该目录 README |
| 记录 5 份 + 证据目录 3 个（15 png + 1 verify.json） | `.qoder/records/{biz,sys}/2026-11/` → `docs/archive/retired-records/` | 该目录 README |

记录 5 份：20261102_doc_pipeline-workflow、20261106_dup-compare-ui-receipt、20261114_footer-strip、
20261114_rail-toggles、20261114_sidebar-text-toggle-removal。
`20261106_dup-compare-evidence/` **留原地**（`tools/dup_compare_probe.py` 代码写入点）。

### 二、三裁决落地（主公 2026-11-18 拍板）

1. **requirements.txt**：删 `jsonschema==4.26.0`，补 `playwright  # 2026-11-18 主公拍板补入；首次安装时钉版`（diff 恰 1+/1−，未安装任何包）。配套 `docs/STACK.md` §0 钉版口径、§7 playwright 例外括注。
2. **456 题 → 历史示例口径**（2026-11-18 实测现网空库）：R03、add-data-store SKILL、build-release SKILL、`docs/API_REFERENCE.md`（3 处示例后注记）、`docs/PLUGIN_SPEC.md` §2.6（示例后注记，契约正文零触碰）、`docs/PROJECT_MEMORY.md`（3 处注记）、`docs/question-cutting-pipeline.md` §开头括注。历史叙述中的 456（旧记录/旧回执/批次史料）不改，逐条豁免。
3. **全量回归豁免**统一口径写入三处：`docs/AGENTS.md` §7、`.qoder/rules/R04-test-workflow.md` §1.5、`.qoder/skills/domain/run-regression/SKILL.md` 步骤3——「默认只跑改动沾到的测试模块（逐个 unittest）＋快门禁；全量 `tools/run_all_tests.py` 仅在大面积/契约级改动、发版收口、或主公点名时跑。不绿不 commit 不变（绿＝定向＋门禁绿）。」discover/pytest 禁令原样保留。

### 三、小漂移扫（第一刀欠账）

- `docs/question-cutting-pipeline.md`：schemas/question.json→`app/core/question_contract.py` 契约（IMAGE_ROLES）；bank_schema.py→`app/core/bank/engine/schema.py`；「工序06」→「发版收口前」；退役注记。
- `docs/AGENTS.md`：§3 契约变更须升 `app/core/contract.py` 的 CONTRACT_VERSION；§9.3⑥ playwright 已补入；⑦ 官方插件 4 支口径。
- `.qoder/rules/R04-test-workflow.md`：§1.6 测试模块 22→19（实测 uvicorn 起服模块清单）；§4.5「只是过程稿」；§5/§6 回归口径合流。
- `docs/RECEIPT_TEMPLATE.md` 抽出单源时的两处旧口径已在第一刀修正，本次未再触碰。

### 四、偏离申报（均已获主公当场点头或按卡 §6 处置）

1. 卡列 5 份记录路径缺月份层（写成 `records/biz/20261106_...`），实际在 `2026-11/` 下，按真实路径执行。
2. **归档位改迁**：卡定 `.qoder/records/archive/`，但 `scripts/check-naming.sh` R00 正则只认 `records/{biz|sys|reports}/{YYYY-MM}/` 直下，records 树内归档目录必判红。主公拍板改迁 `docs/archive/retired-records/`（门禁只扫 `.qoder/`），与 retired-templates 同款先例。
3. **3 个证据目录随记录归档**（卡清单外扩面，主公点头「随记录一起归档」）。
4. `docs/STACK.md` §7 playwright 括注、`docs/PLUGIN_SPEC.md` §2.6 注记为裁决配套最小落点，超出卡字面清单，在此申报。
5. 卡要求单 commit；收口复核发现本记录欠账节一条失实，按「不 amend、不改写历史」铁律以**第二个修正 commit** 落地（主 fc81b14 + 修正），偏离单 commit 字面，回传单同步申报。

### 五、欠账登记（本次不动，留给后续；逐条当次实测核过）

- `.gitignore:56` 注释仍提已退役资产 `skill-bank.json` 与 `.qoder/agents/`（2026-11-05 已删，非本次归档件；只登记）。
- `scripts/check-naming.sh` 的 agents 检查项扫的 `.qoder/agents/` 已不存在（死检查，零代码不改）。
- `docs/question-cutting-pipeline.md` 史料条目内多处 `file:///E:/jiuzhang-operator/` 旧仓库根链接（2026-11-02 批次历史叙述，清单外只登记）。
- `.system_generated/footer-strip/probe.py:10` 探针产物仍写旧证据目录路径（非 git 资产、一次性已跑完，只登记）。
- 台账「未决问题1」待主公拍板（只登记）。
- 空目录壳 `.qoder/templates/`、`.qoder/records/archive/` 留在原地（git 不追踪空目录，无门禁影响）。
- 后续瘦身卡若引 CORE_TARGET_TREE，改指 `tests/test_file_size_contract.py`（冻结台账 35 条）。

> 更正注：本节初版曾误记「cross.py D15 注释指已归档 CORE_TARGET_TREE」。收口复核实测：
> `app/core/ingest/render/cross.py` 的 D15 注释指向**活台账** `docs/识别引擎-决策台账.md` D15 行，
> 全仓代码对 CORE 三件套零引用，无悬空。初版永存 git 历史（主 commit fc81b14），本版为修正 commit。

## 涉及文件

- 移动：33 个（见上表，git R100）
- 修改：requirements.txt、docs/{STACK,AGENTS,API_REFERENCE,PLUGIN_SPEC,PROJECT_MEMORY,question-cutting-pipeline}.md、.qoder/rules/{R03-layer-data-config,R04-test-workflow}.md、.qoder/skills/domain/{add-data-store,build-release,run-regression}/SKILL.md
- 新增：5 份归档映射 README + 本记录
- 禁改区自查：LICENSE / 根 agents.md / docs/AGENTS 铁律一二正文 / question_contract.py / data 目录——均未触碰；并行在途 10 文件与 tools/onnx_probe.py 未 stage 未改

## 验证结果

- 快门禁 `bash scripts/check-quick-gate.sh`：**6 项全 PASS**（含 R00 命名；静态审计 ERROR 0 · WARN 34 · INFO 3，均既有；版本单源 Ran 29 OK；体积 WARN 23 份既有）
- 定向单测（`.venv/Scripts/python.exe -m unittest`，逐模块）：`tests.test_file_size_contract` **Ran 13 OK**；`tests.test_plugin_install_url` **Ran 21 OK**
- 备份对账：33/33 diff 全等，mismatch 0；备份目录实数 33 份
- 悬空引用：`records/archive` 旧路径全仓 grep 命中 0（除 retired-records README 的偏离申报叙述）；各归档文件活引用 grep 0，历史豁免逐条见回传单
- 命名自检：本记录符合 R00（`sys/2026-11/{YYYYMMDD}_doc_{主题}.md`）；归档位偏离 R00 的原因见「偏离申报 2」，已获主公拍板
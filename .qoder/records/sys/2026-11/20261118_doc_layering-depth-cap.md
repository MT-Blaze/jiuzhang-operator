# 分层封顶：把「≤3 层」四句裁决写进 AGENTS §4

- 日期: 2026-11-18
- 类型: doc
- 执行者: 执行子会话（分层封顶纯文档小卡，讨论枢纽 4a0d74c0 接力）
- 等级: L1

## 变更内容

### 一、四句裁决（主公 2026-11-18 拍板「OK，按你说的来吧」）

1. **深度封顶 3 层**：从 `app/`、插件 `src/<id>/`、`docs/`、`.qoder/` 起算，目录最多 3 级；第 3 层一律平铺，不许开第 4 层（`__pycache__` 等生成物不算结构）。
2. **文件夹只按流程/功能分类开**，不按文件数量开、不按流程步骤开；超 500 行拆分＝同目录兄弟文件（靠文件名区分），不加层；体积口径沿用 §9 门禁与根 `agents.md` 500 行红线，不另立规则。
3. **两类独立功能开两个文件夹**（封顶内）；同一子组里长出两类 → 回第 2 层升格为兄弟流程文件夹，不在第 3 层下套第 4 层。
4. **既有生命周期例外明文承认（不新增例外）**：三处「字面够格 2×2 但判平铺」属已裁生命周期例外，照归档判例保留。

### 二、追加位置

`docs/AGENTS.md` §4 分层铁律块续段：原 :63「先例」行之后、原 :64「禁止在根目录堆放业务模块」之前，
标注「**深度封顶（2026-11-18 主公裁）**」。既有 :56-63 分层铁律原文逐字未动（diff 自查纯追加）。
追加后「禁止在根目录堆放业务模块」移至 :74。

### 三、例外出处（归档判例，只读未改）

`docs/archive/migration-blueprint/CORE_TARGET_TREE.md` §4：

| 例外 | 实际路径 | 判例位置 |
|---|---|---|
| batch（2/2 判平铺） | `app/core/pending/batch/` | :467「同一条批次生命周期的前后半步」；:488 复议条款 |
| bank-engine（字面 2×2 判平铺） | `app/core/bank/engine/` | :482「全树唯一的边界判断」三条理由；:488 复议条款 |
| plugins-lifecycle（2/2 判平铺） | `app/core/plugins/lifecycle/` | :488、:501「四步共享同一套包校验与落地逻辑」 |

三处路径当次 `ls -d` 实测均存在。

### 四、实测深度（当次 find 复核，排除 __pycache__/node_modules）

- `app/`：最深 3 层 `app/core/<流程>/<子组>`（如 `app/core/ingest/render`）；第 4 层仅 `__pycache__` 生成物（如 `app/core/ai/platform/__pycache__`），不算结构。
- `docs/`：最深 3 层（`docs/handoff/receipts/archive`、`docs/archive/retired-records/<记录>`）。
- `static/`：无第 4 层。
- 插件兄弟仓 `../jiuzhang-plugins/src/<id>/`：最深 3 层（`dist/`、`models/`、`dev/`、`bank/`），只读复核未碰。
- `.qoder/`：结构目录（records/sys/2026-11 等）封顶 3 层；**发现超层证据目录 3 个**，见下节登记。

### 五、清单外发现（只登记不动）

`.qoder/records/biz/2026-11/` 下两个证据目录超 3 层：
`20261106_dup-compare-evidence/`（第 4 层，内仅 `shots/` 第 5 层）与 `20261113_sidebar-footer/`（第 4 层，内仅 3 张 png）。
均为探针截图证据产物，非结构目录；前者是 `tools/dup_compare_probe.py` 代码写入点（减税第二刀记录已注明留原地）。
枢纽口径「第 4 层只出现在 __pycache__ 生成物」在 .qoder 证据产物上略有出入，按卡 §5「清单外新税只登记不动」处理，不新增例外、不挪目录。

## 涉及文件

- 修改：`docs/AGENTS.md` §4（纯追加 10 行，:64-73；既有正文零改动）
- 新增：本记录
- 禁改区自查：LICENSE / 根 agents.md / AGENTS 铁律一二 / question_contract.py / data/ / .qoder/rules/ / tests/test_file_size_contract.py / tools/onnx_probe.py / 插件仓——均未触碰；onnx_probe.py 保持 untracked 未 stage

## 验证结果

- 快门禁 `bash scripts/check-quick-gate.sh`：6 项全 PASS（当次实测，见回传单）
- 定向单测 `.venv/Scripts/python.exe -m unittest tests.test_file_size_contract`：Ran 13 OK（当次实测）
- diff 自查：`git diff docs/AGENTS.md` 纯追加，:56-63 原文逐字未动
- 命名自检：本记录符合 R00（`sys/2026-11/{YYYYMMDD}_doc_{主题}.md`）
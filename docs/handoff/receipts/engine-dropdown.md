# 回传单 · 识别下拉改名与分组小刀卡（短名＋自动置顶＋三条本地 VLM 组合）

【回执编号】 #ENGINE-DROPDOWN-01
【回执时间】 2026-11-20
【主公裁决】 2026-11-20：①「把后面的『云端视觉加组合路』删掉，写成『云端 AI OCR』」；
②「我激活了几个，我就写几个」——本地 VLM 组合按座逐条列；③「『组合路』三个字就不要了」；
④对齐统一按禁用表头行方案；⑤「自动是自动分流的，为什么能放在这个图片组」——自动移出分组、单独置顶。
【执行结果】 **收口全绿**。插件仓 1 笔（editor 2.26.0）＋底座仓 2 笔；定向 10 模块 305/305 绿；
快门禁 PASS；UI 真机探针 38/38 绿；发行包双建同哈希 `dbea4a6b`。两仓不 push。
**65496 零接触；未起真引擎、未点安装、零出网。插件 2.26.0 生效需主公重启一次（与在途重启债合并）。**

基线：operator `9bf3f45`（ahead 91，脏件仅 `?? tools/onnx_probe.py`）／plugins `93e4686`
（editor 2.25.1，ahead 23，未跟踪 `model_prefs.toml` 与 `models/` 原地未 stage），与卡§0 一致。
本卡：plugins 1 笔 `3b45428`（ahead 23→24）；operator 收口后 ahead 91→93。

## 桶一 · 改了什么（逐条对齐卡§1/§2）

### 插件仓（commit 3b45428，5 files）

- `src/org.jiuzhang.editor/catalog.toml`
  - `combo_cloud`：`name = "云端 AI OCR"`；summary/summary_usage/ready/degraded/route 去「组合路」，
    ready 改为「已指派：{name}（{model}）。正文文字直取，公式裁图送云端视觉。」；
    summary_usage 保留「文字层取」「纯图卷」。
  - `combo_vlm` 删除，拆三条（`rule = "vlm_local"`、`plan_recognize = ["combo"]`，各自 `combo_seat`）：
    `combo_vlm_qwen` 千问 Qwen2.5-VL（本地）／`combo_vlm_intern` 书生 InternVL3-2B（本地）／
    `combo_vlm_minicpm` 面壁 MiniCPM-V-2.6（本地）；模型名按座写，旧 `id = "combo_vlm"` 不再存在。
  - 其余组合短名：`combo_pp_m`→PP-FormulaNet·M、`combo_pp_l`→PP-FormulaNet·L、
    `combo_p2t`→Pix2Text·MFR、`combo_texify`→Texify；`combo_seat`/`plan_recognize`/`rule`/`store` 未动。
  - 全部组合的 name/summary/summary_usage/ready/degraded/missing/route 去「组合路」，「文字直取」保留；
    8 条 summary_usage 均含「文字层取」「纯图卷」（测试断言）。条目总数 19→21、组合 6→8。
- `src/org.jiuzhang.editor/dist/ui_intake.js`
  - 新增 `groupHead(text)`：`option.value=""`、`option.disabled=true`、文本 `—— … ——`。
  - `paintEngineOptions()` 的 `edRecognizeEngine` 分支改为：`自动`单独置顶（显式排除出两组）→
    禁用表头 `—— 整题OCR ——`＋非组合座 → 禁用表头 `—— 文字直取＋公式 ——`＋组合座；
    不建 optgroup；某组为空不出该表头；版面下拉保持扁平。
  - `engineOption` 的 title 逻辑、纯图卷置灰/人话、`select.value` 归 auto 兜底原样保留。
- `plugin.toml`：2.25.1 → **2.26.0**。
- `plugins.json`：editor version 2.26.0＋changelog（与主仓 `plugins.toml` 语义一致）。
- `plugins/org.jiuzhang.editor.zip`：`tools/build_plugin.py` 重建（双建同哈希 `dbea4a6b6e02…`，
  in-zip `catalog.toml` sha256 == 源文件 `c18998fe1bc9…` MATCH）；`dist/plugins/` 同步副本（git 忽略）。

### 底座仓（测试与探针，不动产线）

- `tests/test_models_registry.py`：`_runtime` 增 `vlm_weights_by_seat`（weights_ready 按座）；
  组合期望表 6→8；`test_combo_vlm_follows_local_vlm_health` 改按三座分别断言
  （action＝install_vlm／install_vlm_intern／install_vlm_minicpm，且只装本座不连带他座）；
  combo 就绪 detail 断言随新文案改为「正文文字直取」。
- `tests/test_recognize_router.py`：`combo_vlm` 全部改 `combo_vlm_qwen`；
  seat 透传循环补 `combo_vlm_intern → vlm_intern`。
- `tests/test_last_used_engine.py`：docstring 第 4/5 条改口径；分组测试改为
  「自动置顶＋两条禁用表头＋全平铺、不建 optgroup、auto 在表头前、归属仍按 comboIds、空组不出表头」；
  catalog 名称断言改新短名，并新增「旧 combo_vlm 不存在、三座组合在」。
- `tests/test_command_registry.py`：官方插件手工表 editor version 2.25.0 → 2.26.0。
- `tools/last_used_engine_probe.py`：组头改按「禁用 option 文本」定位；底组＝registry 实际就绪组合
  （不写死 5 条）；顶组＝registry 就绪整题座；重选/停用步骤动态挑一条就绪组合（本机 pick＝combo_pp_l）；
  条目文本断言无「组合路」「文字直取＋公式·」；新增展开浮层截图。
- `tools/vlm_live_probe.py`：陈旧 `combo_vlm` 判定改 `combo_vlm_qwen`（保持「千问组合未装→degraded」语义）。
- `plugins.toml`：editor version 2.26.0（与插件清单、插件仓索引三方一致）。

## 桶二 · 新旧名对照

| id | 旧 name | 新 name | combo_seat | rule |
|---|---|---|---|---|
| combo_cloud | 文字直取＋公式·云端视觉（组合路） | 云端 AI OCR | cloud_vision | task_assign |
| combo_vlm_qwen | （旧 combo_vlm 合体） | 千问 Qwen2.5-VL（本地） | vlm_qwen | vlm_local |
| combo_vlm_intern | （旧 combo_vlm 合体） | 书生 InternVL3-2B（本地） | vlm_intern | vlm_local |
| combo_vlm_minicpm | （旧 combo_vlm 合体） | 面壁 MiniCPM-V-2.6（本地） | vlm_minicpm | vlm_local |
| combo_pp_m | 文字直取＋公式·PP-FormulaNet·M（组合路） | PP-FormulaNet·M | formula_pp_m | weight_present/store=formula |
| combo_pp_l | 文字直取+公式·PP-FormulaNet·L | PP-FormulaNet·L | formula_pp_l | weight_present/store=formula_l |
| combo_p2t | 文字直取+公式·Pix2Text·MFR | Pix2Text·MFR | formula_p2t | weight_present/store=formula_p2t |
| combo_texify | 文字直取+公式·Texify | Texify | formula_texify | weight_present/store=formula_texify |

8 条组合期望（单测逐条钉）：capability=recognize、plan_recognize=["combo"]、combo_seat 如上、
summary_usage 含「文字层取」「纯图卷」；公式组合随本座权重，VLM 组合随本座健康＋权重。

## 桶三 · 实测证据（数字来自当次输出）

### 单测（`.venv/Scripts/python.exe -m unittest tests.<模块>`）

| 模块 | 结果 |
|---|---|
| tests.test_models_registry | Ran 79 / OK |
| tests.test_recognize_router | Ran 26 / OK |
| tests.test_last_used_engine | Ran 16 / OK |
| tests.test_model_prefs | Ran 16 / OK |
| tests.test_formula_route | Ran 39 / OK |
| tests.test_ingest_triage | Ran 21 / OK |
| tests.test_command_registry | Ran 35 / OK |
| tests.test_vlm_service | Ran 27 / OK |
| tests.test_vlm_setup | Ran 33 / OK |
| tests.test_file_size_contract | Ran 13 / OK |
| 合计 | 305 / OK |

- 快门禁：`bash scripts/check-quick-gate.sh` → rc=0（含包结构、索引全等、静态审计、版本单源）。
- 体积预警：23 份，与基线集合相同（`ui_intake.js` 691 行属冻结台账老文件，未新增警报）。
- 索引门禁：`check-plugin-index-parity` PASS；`check-plugin-package` PASS（5 支）。

### UI 真机探针（隔离副本＋动态端口）

`tools/last_used_engine_probe.py engine-dropdown` → **ok=True，38/38 PASS**：
复制自 plugins 仓 HEAD（`git archive`，未跟踪 models/prefs 天然不入）、独立 JZO_DATA_DIR/JZO_PLUGINS_DIR、
随机本地令牌、零安装请求、收口端口关闭、孤儿零。registry 事实：21 条目、8 条组合声明，
本机就绪组合 7 条＝`combo_cloud/qwen/intern/minicpm/pp_m/pp_l/p2t`（texify 权重未就绪，故不出现）。
下拉 DOM：自动第 0 项且在任何表头之前；两条禁用表头文本精确匹配；零 optgroup；底组==registry 就绪组合；
顶组==就绪整题座且不含 auto/组合；条目文本无「组合路」「文字直取＋公式·」；纯图卷进筐后组合项
`disabled=true` 且自动仍可选。

截图（探测产物 `.system_generated/last-used-engine/engine-dropdown/shots/`，另拷
`.system_generated/engine-dropdown/engine-dropdown/`；git 忽略）：

| 文件 | 内容 |
|---|---|
| 01-config-auto-seats.png | 配置页①自动设置、②默认引擎整行已砍 |
| 02-recognize-flat.png | 识别下拉全展开：自动置顶＋两条表头＋7 条就绪组合，左基线一致，无前缀 |
| 02b-layout-flat.png | 版面下拉展开：扁平无表头 |
| 03-pure-image-gray.png | 纯图卷进筐后展开：组合项 disabled，自动可选 |
| 03-crop.png | 03 的 2× 放大（人工核对用） |
| 03-combo-disabled.png | 停用组合项后下拉摘除 |
| 04-last-used.png | 选座→回写上次→刷新初值＝上次 |
| 05-stored-disabled.png | 存过座被停用→归自动但不擦 prefs→启用恢复 |

## 桶四 · 偏离与欠账

- **偏离①（路径按现状）**：卡面写 `jiuzhang-operator\plugins\*.zip` 与 `plugins.json`；实际底座仓产物是
  `dist/plugins/org.jiuzhang.editor.zip`（git 忽略），官方索引是 `plugins.toml`，远端索引 `plugins.json`
  在插件仓。按现状执行：zip 入插件仓 commit，主仓只改 `plugins.toml` 版本；parity/package 双绿。
- **偏离②（提交拆分）**：卡面 operator 收口笔含 zip＋index；zip 已在插件仓笔里，operator 第 2 笔为
  回单＋biz；`plugins.toml` 版本提前并入第 1 笔，保证中间提交也过索引门禁。
- **偏离③（多改一个探针）**：`tools/vlm_live_probe.py` 仍引用旧 `combo_vlm`，不修会让该探针下次必红；
  只做同义改名 `combo_vlm→combo_vlm_qwen`，未改判据。
- **口径（同名靠分组区分）**：千问/书生/面壁三座在「整题OCR」与「文字直取＋公式」两组同名出现，
  这是按座的事实（各自既是整题座也是组合座），靠表头分组区分；卡面已认可。
- **证据限制**：原生 select 展开层属浏览器 UI，Playwright 截不到；证据用「同内容克隆成 listbox 浮层」截图，
  置灰结论以 DOM `disabled=true` 为准。
- **历史证据未动**：`docs/handoff/evidence/last-used-engine/probe.toml` 等旧轮证据保留原样（append-only）。
- **重启提示**：插件 2.26.0 生效需主公重启一次；本卡未重启、未 push。

## 桶五 · 红线自检

- LICENSE／根 `agents.md`／`docs/AGENTS.md` 铁律一二／`app/core/question_contract.py`／用户 `data/`：零改。
- 未 stage 插件仓未跟踪的 `model_prefs.toml`／`models/`；底座 `?? tools/onnx_probe.py` 原地未动。
- 两仓均未 amend、未 push；无 JSON 落盘（回单/biz 均为 MD；`plugins.json` 是既有索引文件，非新增落盘）。
- 65496（PID 2700）零接触；探针只起隔离副本 uvicorn；零真引擎、零安装、零出网；未执行任何 `taskkill`。

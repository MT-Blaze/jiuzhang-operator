# 回传单 · 组合座 combo_pp_m 就绪恒真修复（真看权重，不再"能 import 就绿"）

【回执编号】 #COMBO-PPM-READY-01
【回执时间】 2026-11-20
【执行结果】 **收口全绿**。combo_pp_m 由 `import_probe`（模块能导入就恒绿）改
`weight_present＋store=formula`，就绪真跟 PP-FormulaNet·M 权重走；底座产线零改；
定向七模块全绿＋快门禁 PASS；隔离副本 Playwright 两跑对照拿到"修前恒绿／修后未就绪"真证。
插件仓 1 笔 `93e4686`（ahead 22→23，editor 2.25.1），底座仓 1 笔（本回单＋biz＋测试转正）。
两仓 push 全 hold；65496（PID 2700）零接触。

基线：operator `68ad244`（ahead 87，工作树仅 `?? tools/onnx_probe.py`）／
plugins `0841ccd`（ahead 22，工作树仅 `?? model_prefs.toml`＋`?? models/`，原地保留未 stage）。

## 桶一 · 做了什么（逐条对齐卡§1–§4）

- §1 根因复核成立：`src/org.jiuzhang.editor/catalog.toml:219-233` 的 combo_pp_m 用
  `rule = "import_probe"`＋`probe = "app.core.ingest.recognize.formula"`；
  底座 `_rule_import_probe`（app/core/ingest/registry.py:103-108）只看模块能 import，
  模块永远在 → 即便 PP-M 权重没装本组合恒"就绪"，老师选了掉进"公式标待核"暗坑。
  同族 combo_pp_l/combo_p2t/combo_texify 均已 `weight_present`＋对应 store，combo_pp_m 是唯一漏网。
- §2.1 插件目录一处：`catalog.toml` combo_pp_m
  `rule = "import_probe"`→`weight_present`、删 `probe`、加 `store = "formula"`；
  `degraded_detail` 改同公式座 M 口径真话（596MB 沿用 :296，不编尺寸）；
  `summary_usage` 现状句改"未装显示未就绪＋一键安装；装好后正文直取、公式裁图交 PP-M"；
  `ready_detail`／`plan_recognize`／`combo_seat`／`route_note` 一字不动。
- §2.2 版本与出包：`plugin.toml` 2.25.0→**2.25.1**；`tools/build_plugin.py` 重打
  `plugins/org.jiuzhang.editor.zip`；`plugins.json` 与底座 `plugins.toml` 索引同步
  （`tools/sync_plugin_index.py`，远端语义一致）。
- §2.3 底座零改：`_rule_weight_present` 已认 `store="formula"`→`_formula_verdict(variant="m")`，
  自动给出 `action=install_formula`；route 层 `gate_recognize` 按就绪筛选，无需新代码。
- §2.4 测试转正（不删案，逐处）：
  - `tests/test_last_used_engine.py:160-164`：案名保留，断言转正为
    `rule = "weight_present"`＋`store = "formula"`＋无 `probe =`＋`combo_seat = "formula_pp_m"`；
  - `tests/test_models_registry.py:535-546`：全组合表加入 combo_pp_m→formula_pp_m→store `formula`，
    docstring 同步（import_probe 恒绿的反面口径）；
  - `tests/test_models_registry.py:624-632`：原"恒 ready"案转正为两半——
    权重不在→`degraded`＋`action=install_formula`；权重在（mock `formula_weights=True`）→
    `ready` 且与 formula_pp_m 同步；
  - `tests/test_recognize_router.py:237,263` 与注册表其余用例跑绿未改。
  - 额外陈旧红见偏离②（texify 预建断言）。
- §3 UI 真测：隔离副本（两仓 git archive HEAD＋覆盖待提交两件）＋Playwright 穿沙箱，
  动态端口＋随机令牌，不点安装不出网；证据见桶二/桶三。

## 桶二 · 实测证据（数字全部来自当次输出）

| 模块 | 结果 |
|---|---|
| tests.test_models_registry | Ran 79 / OK |
| tests.test_last_used_engine | Ran 15 / OK |
| tests.test_recognize_router | Ran 26 / OK |
| tests.test_formula_route | Ran 39 / OK |
| tests.test_formula_setup | Ran 63 / OK |
| tests.test_vlm_setup | Ran 33 / OK |
| tests.test_file_size_contract | Ran 13 / OK |

- 快门禁：`bash scripts/check-quick-gate.sh` → `PASS（6 项全过）`；
  体积预警 23 份（与基线相同，本卡未新增警报文件）。
- 出包：双建 `sha256 = e1cd31ac909f544d8ef2eef7e4acaafe7fd8fffd434be45ee98f5170e8baba91`
  （临时目录连打两次相同）；`check-plugin-index-parity` PASS；`check-plugin-package` PASS（5 支）。
- UI 两跑（`.system_generated/combo-ppm-ready/probe.toml`＋截图，git 忽略）：

| 跑次 | registry combo_pp_m | 识别下拉 combo 项 | JS 异常 | HTTP 失败 | 端口收口 |
|---|---|---|---|---|---|
| baseline（插件 0841ccd 原样） | `state=ready`、`action=""`、rule=`import_probe` | `["combo_pp_m"]`（权重没装却可选） | 0 | 0 | 63363 已关 |
| fixed（覆盖 2.25.1 两件） | `state=degraded`、`action=install_formula`、rule=`weight_present`、store=`formula` | `[]`（与 combo_pp_l 一致，未就绪不进下拉） | 0 | 0 | 63394 已关 |

- fixed 跑 registry 详情原文：
  `degraded_detail = "PP-FormulaNet·M 权重未安装（约 596MB，国内镜像），点【安装】一键下；装好本组合路随公式座就绪。"`
- 四栏表两次均正常渲染（表头 名称/简要（点击展开）/状态/操作），公式座 PP-M 行
  徽章"未就绪"＋【安装】钮；两次运行均未点安装、零出网安装请求。

## 桶三 · 偏离登记与未决

1. **卡§3 的 UI 落点与现设计不同**：四栏模型表按设计**不列组合路**
   （dist/ui_model_table.js:177-179「组合路是链路不是模型：进识别下拉，不进模型表」）。
   因此老师可见的 combo_pp_m 就绪态落点是**识别下拉**：修前恒列、修后未装即不列；
   安装引导落在同权的公式座 PP-M 行（未就绪＋【安装】，action 同为 install_formula）。
   未改 UI 结构（不扩权），证据以上述两跑为准。
2. **跨仓陈旧红顺带转正**：`test_texify_combo_not_prebuilt` 断言组合 texify"不预建"，
   但插件仓 0841ccd（卡④ 2.25.0）已预建 combo_texify——该案在开工前即为红，与本案无关，
   但会阻断"不绿不 commit"。按真值转正为 `test_texify_combo_prebuilt_with_seat`
   （weight_present＋store=formula_texify＋combo_seat），如实登记。
3. **degraded_action 未显式写**：combo_pp_m 与公式座同口径由 `_formula_verdict` 推导
   `install_formula`，catalog 不重复声明（与 combo_pp_l/p2t/texify 写法一致）。
4. 插件仓 `?? models/`＋`?? model_prefs.toml` 为主公 UI 安装权重与偏好运行产物，
   非代码脏，零接触零 stage。
5. 无欠账新增；两仓 push hold（不问不推）。

## 【改动清单】

- 插件仓 `93e4686`（ahead 22→23）：
  - `src/org.jiuzhang.editor/catalog.toml`（combo_pp_m 一条，4 行）；
  - `src/org.jiuzhang.editor/plugin.toml`（2.25.0→2.25.1）；
  - `plugins/org.jiuzhang.editor.zip`（重打，sha256 e1cd31ac…）；
  - `plugins.json`（editor version＋changelog）。
- 底座仓收口笔：
  - `tests/test_last_used_engine.py`（combo_pp_m 转正＋texify 预建转正）；
  - `tests/test_models_registry.py`（全组合表＋pp_m 两半案）；
  - `plugins.toml`（editor 2.25.1 同步）；
  - 本回单＋`.qoder/records/biz/2026-11/20261120_combo-ppm-ready.md`。
- 禁改区自查：LICENSE 未动；根 agents.md 未动；AGENTS 铁律一二未动；
  `app/core/question_contract.py` 未动；用户 `data/` 未动；`app/` 全树零改。
- 证据目录 `.system_generated/combo-ppm-ready/`（截图＋probe.toml＋probe 脚本）git 忽略，未进仓。

## 【包结构自检】

`check-plugin-package` PASS（官方插件 5 支，结构红线全过）；`check-plugin-index-parity` PASS
（两份索引语义一致、条目版本一致）；重复打包同哈希 e1cd31ac…。

## 【三查结果】

插件侧 diff 未引入 `fetch(`／`parent.document`／`localStorage` 新用法（catalog/清单/索引纯数据）；
未新增请求 id。UI 探针运行日志零 console error、零 pageerror、零 HTTP≥400。

## 【测试与探针】

见桶二七模块表＋快门禁＋两跑 UI 证据；逐模块 `.venv/Scripts/python.exe -m unittest tests.<模块>`，
禁 discover；前端真测已做（隔离副本），未点真实安装。

## 【未决问题与偏离】

见桶三①–⑤。无"未验证冒充已验证"；配方座权重"已装→ready"由单测 mock 覆盖，
UI 层未造伪权重（真装须主公亲手）。

## 红线自检（卡§5 逐条）

- LICENSE／根 agents.md／AGENTS 铁律一二／question_contract.py／用户 data/：零改。✅
- 底座产线代码零改（app/ 全树）：git diff 实证仅 tests/＋plugins.toml＋docs/biz。✅
- 65496（PID 2700）零接触；未执行 `taskkill /F /IM python.exe`；探针只按 PID 杀自起树。✅
- 插件仓 1 笔（MT-Blaze 瞬态身份，未写 git config）、底座仓 1 笔；stage 逐个点名、不 amend。✅
- 两仓不 push；禁 JSON 落盘（回单/biz 均 MD）。✅
- 行数红线：本次新增/改动测试均不在警报扫描面（tests/），警报集合 23 份与基线相同。✅

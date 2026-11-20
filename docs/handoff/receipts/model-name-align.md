# 回传单 · 模型配置界面与识别下拉同字（editor 2.26.2）

【回执编号】 #MODEL-NAME-ALIGN-01
【回执时间】 2026-11-20
【主公裁决】 2026-11-20：「模型配置界面和这个下拉列表，他们的文字一定是一致的。」
口径：识别下拉短名（#ENGINE-DROPDOWN-01 已拍板）为准，catalog 座名跟随。
【执行结果】 **收口全绿**。插件仓 1 笔（editor 2.26.2）＋底座仓 2 笔；定向 4 模块 144/144 绿；
快门禁 PASS（体积预警 23 份，与基线相同）；索引 parity / 包结构 rc0；发行包双建同哈希
`19237b6c1e76…`（328.5 KB，90 条目）。**65496（PID 16992）零接触；零真引擎、零安装、零出网。**
UI 证据用隔离宿主（动态端口 5459）真浏览器取证 14/14 绿。两仓不 push；
**65496 生效需主公重启一次（与在途重启债合并）。**

基线：plugins `332202c`（editor 2.26.1，ahead 25，未跟踪 `model_prefs.toml` 与 `models/` 原地未 stage）；
operator `7f264f1`（ahead 95，脏件仅 `?? tools/onnx_probe.py`），与卡一致。
本卡：plugins 1 笔 `135666d`（ahead 25→26）；operator `901eb53`（测试＋探针＋索引）＋本回单笔（ahead 95→97）。

## 桶一 · 改了什么

### 插件仓（commit 135666d，6 files）

- `src/org.jiuzhang.editor/catalog.toml`
  - 座名跟随组合短名（只动展示 name）：`cloud_vision` 云端视觉→**云端 AI OCR**；
    `formula_pp_m`/`formula_pp_l`/`formula_p2t`/`formula_texify` 去「（公式专科）」后缀。
  - 用户可见散文「云端视觉」→「云端 AI OCR」共 12 处（vram_note、cloud_vision 自身
    summary_usage/route_note_*、三座 VLM summary_usage「改云端 AI OCR 或 MinerU」、
    combo_cloud 的 summary/summary_usage/ready_detail/route_note_recognize）。
  - `id`/`rule`/`plan_*`/`combo_seat`/`store`/内部标识符零改；公式座散文里的叙事性
    「公式专科」保留（只 name 去后缀）。
- `src/org.jiuzhang.editor/README.md`：用户可见的「云端视觉」8 处同步为「云端 AI OCR」。
- `src/org.jiuzhang.editor/dist/ui_intake.js:70`：纯图卷灰项 tooltip「MinerU/本地VLM/云端 AI OCR」。
- `plugin.toml`：2.26.1 → **2.26.2**。
- `plugins.json`：editor version 2.26.2；changelog 新段前置、旧段原样保留。
- `plugins/org.jiuzhang.editor.zip`：`tools/build_plugin.py` 重建，双建同哈希
  `19237b6c1e76997be34af80f55d5d2e6b58e0044947e5fe5c75c5745d8057502`；in-zip catalog sha256 ==
  源文件 MATCH；无 `models/`、无 `model_prefs.toml`、顶层目录==id、版本 2.26.2。

### 底座仓（commit 901eb53，7 files）

- `tests/test_models_registry.py`：
  - 新增 `test_combo_names_match_their_seat`：遍历 `plan_recognize` 含 `combo` 的条目，
    断言 name 与 `combo_seat` 指向的座条目 name 逐字相等；缺 seat/缺条目直接红。
  - `test_p2t_renamed_to_pix2text` 期望名改「Pix2Text·MFR」；
    `test_legacy_alias_gates_by_new_entry` 闸口 note 期望改「云端 AI OCR」。
- `tests/test_ingest_routing.py`：catalog 驱动的 route_note 断言改「只交云端 AI OCR」。
- `tests/test_formula_route.py`：两处 cloud_vision 夹具 name 改「云端 AI OCR」。
- `tests/test_command_registry.py`：官方插件手工表 editor 2.26.1 → 2.26.2。
- `tools/texify_live_probe.py`：`TEXIFY_ROW` 改「Texify」、docstring 去后缀；模型表行改用
  `.ep-mt-name[data-id=formula_texify|formula_p2t]` 定位（同名后按 data-id 去歧义）。
- `tools/t6_route_probe.py`：重认席位 has_text 改「云端 AI OCR」。
- `plugins.toml`：editor version 2.26.2（与插件清单、插件仓索引三方一致）。

## 桶二 · 新旧名对照

| id | 旧 name（座） | 新 name（＝组合短名） |
|---|---|---|
| cloud_vision | 云端视觉 | 云端 AI OCR |
| formula_pp_m | PP-FormulaNet·M（公式专科） | PP-FormulaNet·M |
| formula_pp_l | PP-FormulaNet·L（公式专科） | PP-FormulaNet·L |
| formula_p2t | Pix2Text·MFR（公式专科） | Pix2Text·MFR |
| formula_texify | Texify（公式专科） | Texify |

VLM 三对（combo_vlm_* ↔ vlm_*）原名已一致，未动。改后识别下拉会同时出现两个「云端 AI OCR」
（整题OCR 与 文字直取＋公式 各一）、两个同名 VLM——既定口径「同一模型同一名字、由分组表意」，不加后缀。

## 桶三 · 实测证据

### 单测（`.venv/Scripts/python.exe -m unittest tests.<模块>`）

`tests.test_models_registry tests.test_last_used_engine tests.test_command_registry tests.test_file_size_contract`
→ **Ran 144 tests, OK**（护栏新测试含在内）。

### 门禁与包

- `bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**，体积预警 23 份。
- `bash scripts/check-plugin-index-parity.sh` → rc0 PASS（两份索引语义/版本一致）。
- `bash scripts/check-plugin-package.sh` → rc0 PASS（官方插件 5 支，结构红线全过）。
- zip 双建：`.system_generated/model-name-align/zip-build1|build2/` 哈希一致（见上）。

### UI 真浏览器取证（隔离宿主，不碰 65496）

`.system_generated/model-name-align/probe.py`（被 .gitignore 忽略）＋动态端口 5459：
隔离 `JZO_DATA_DIR/JZO_PLUGINS_DIR`，插件从当前源码拷入，假视觉账号只让 combo_cloud 就绪
（零出网）；Playwright 打开【模型配置】与识别下拉，读 DOM 逐字比对并截图。

- 结果：**14/14 PASS**；零 JS 异常、零 HTTP 失败、收口端口已关。
- 逐字对照：combo_cloud／combo_vlm_qwen／intern／minicpm／combo_pp_m／l／p2t 共 7 对
  「下拉项名 == 模型表座行名 == registry name」全相等；两个名单里均无「云端视觉」「（公式专科）」。
- 截图：`01-model-table-top.png`、`02-model-cloud.png`（模型表「云端 AI OCR」行、
  vram_note 已改）、`03-model-formula.png`（PP-M/L、Pix2Text·MFR、Texify 无后缀）、
  `04-dropdown-flat.png`（下拉整表，短名，无旧称）。

## 偏离

1. **combo_texify 未就绪不入下拉**：本机 engines/formula 无 texify 六件权重（未装），
   下拉按设计只列就绪条目，故该组合项不出现在下拉。已核：模型表座行名「Texify」== registry name，
   且护栏测试锁「组合 name == 座 name」、下拉文本取自同一条目 name 单源。未伪造共享权重文件。
2. **README 同步范围**：除用户可见表格外，README 正文/源码表里的「云端视觉」也一并同步
   （同一文档口径统一）；doc 历史证据与 receipts 未改。
3. **底座运行期错误/步骤文案未动**：`识别·云端视觉`、`云端视觉公式识别失败` 等 app/core 硬编码串
   仍是旧称——不在本卡「模型配置界面＋识别下拉」两面范围，配套断言保持原样；如需全站统一另开卡。
4. **UI 证据走隔离宿主**：live 65496 现加载旧包且禁重启；隔离实例加载当前源码/同哈希 zip 取证，
   未动 PID 16992。live 生效仍需主公重启一次。
5. **探针脚本与证据**：`.system_generated/` 全忽略，不入任何 commit；`tools/onnx_probe.py` 仍未跟踪未 stage。

## 收口清单

- 插件仓：`135666d`（ahead 25→26），未 push；`model_prefs.toml`/`models/` 未 stage。
- 底座仓：`901eb53`（测试/探针/索引）＋本回单笔（ahead 95→97），未 push；`tools/onnx_probe.py` 未 stage。
- 两仓 commit 均 `-c user.name=MT-Blaze -c user.email=tianxiulaoshi@163.com` 瞬态身份，未写 git config；未 amend。
- 用户 data/、LICENSE、根 agents.md、AGENTS 铁律一二、app/core/question_contract.py 零改动。

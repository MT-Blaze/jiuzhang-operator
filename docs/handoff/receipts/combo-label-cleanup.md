# 回传单 · 「组合路」用户可见字样清理（editor 2.26.1）

【回执编号】 #COMBO-LABEL-CLEANUP-01
【回执时间】 2026-11-20
【主公裁决】 沿用 2026-11-20：「『组合路』三个字就不要了」。上一卡 #ENGINE-DROPDOWN-01 已清条目短名，
本卡只补剩下 5 处老师能看到的字，纯文案，控件结构不动。
【执行结果】 **收口全绿**。插件仓 1 笔（editor 2.26.1）＋底座仓 2 笔；定向 4 模块 143/143 绿；
快门禁 PASS（体积预警 23 份，与基线相同）；索引 parity / 包结构 rc0；发行包双建同哈希 `192f9731`。
两仓不 push。**65496 零接触；零真引擎、零安装、零出网；本卡无 UI 真测（纯文案，控件结构未动）。**

基线：plugins `3b45428`（editor 2.26.0，ahead 24，未跟踪 `model_prefs.toml` 与 `models/` 原地未 stage）；
operator `63acf83`（ahead 93，脏件仅 `?? tools/onnx_probe.py`），与卡一致。
本卡：plugins 1 笔 `332202c`（ahead 24→25）；operator `2ead5a4`（测试＋索引）＋本回单笔（ahead 93→95）。

## 桶一 · 改了什么（逐条对齐卡§改动清单）

### 插件仓（commit 332202c，6 files）

| # | 文件:行 | 改动 |
|---|---|---|
| 1 | `src/org.jiuzhang.editor/catalog.toml:330` | `degraded_detail` 尾句「装好公式专科与组合路公式步生效」→「装好公式专科与文字卷公式识别生效」 |
| 2 | `dist/ui_intake.js:70` | 纯图卷灰项 `option.title` 去前缀「组合路」→「只支持文字卷：筐里这份是纯图卷…」；同行尾注释 `// §2 组合路对纯图卷灰＋人话（筐里全纯图才灰）` → `// §2 纯图卷置灰＋人话（筐里全纯图才灰）` |
| 3 | `dist/ui_intake.js:106` | dock 文案 → `dock("只支持文字卷：筐里是纯图卷，识别已回到自动分流。");` |
| 4 | `dist/ui_model_install.js:83` | PP-FormulaNet·M 安装确认尾句 →「装好后公式专科与文字卷公式识别生效。仍要安装？」 |
| 5 | `dist/ui_model_install.js:96` | Texify 安装确认尾句 →「装好后公式专科 Texify 档与文字卷公式识别生效。仍要安装？」 |

- `plugin.toml`：2.26.0 → **2.26.1**。
- `plugins.json`：editor version 2.26.1＋changelog 前置 2.26.1 段（旧 2.26.0/2.25.1/2.25.0 段原文保留），
  description 未动（本就不含「组合路」）；`updated_at` 2026-11-20。
- `plugins/org.jiuzhang.editor.zip`：`tools/build_plugin.py` 重建，双建同哈希
  `192f9731527ae60312c2a1a3e72b7344cdafe4b9ca05d16b5d56f16dee592dfe`（328.5 KB，90 条目，
  全部以 `org.jiuzhang.editor/` 开头）；in-zip `catalog.toml`/`ui_intake.js`/`ui_model_install.js`/`plugin.toml`
  与源文件逐字节 MATCH（sha256 前 16：31409865a2a9b9d4 / 45f2daefd47e5f40 / 96d6e04387512720 / 022c9bd054e5ce84）。

### 底座仓（commit 2ead5a4 + 本回单笔）

- `tests/test_last_used_engine.py:140`：`assertIn("组合路只支持文字卷", helper)` → `assertIn("只支持文字卷", helper)`；
  同测试的 `识别已回到自动分流` 断言（:143）原样保留，判据未放宽。
- `tests/test_command_registry.py:519`：官方插件手工表 editor `2.26.0` → `2.26.1`（版本单一事实源随清单）。
- `plugins.toml:51`：editor `2.26.1`（与插件清单、插件仓索引三方一致）；description 未动。
- 本回单笔：本文件＋`biz/2026-11/20261120_combo-label-cleanup.md`。

### 一字未动

`ui_model_table.js`（:177 注释）、`ui_reidentify.js`（:149 注释）——内部代码注释，不进界面；
算子 `app/` 里「组合路」技术口径（`app/core/ingest/recognize/router.py:10/170/173` 的 docstring、
route note、异常文案）本卡按令不碰；`tests/test_formula_route.py`、`tests/test_ingest_triage.py`、
`tests/test_recognize_router.py` 里对 route note 含「组合路」的断言因源侧未变而照旧全绿。

## 桶二 · 新旧文案对照（5 处，逐字）

| # | 位置 | 旧 | 新 |
|---|---|---|---|
| 1 | catalog `formula_pp_m.degraded_detail` | 点【安装】一键下；装好公式专科与**组合路公式步**生效。 | 点【安装】一键下；装好公式专科与**文字卷公式识别**生效。 |
| 2 | ui_intake:70 `option.title` | **组合路**只支持文字卷：筐里这份是纯图卷，… | 只支持文字卷：筐里这份是纯图卷，… |
| 2b | ui_intake:70 尾注释 | // §2 **组合路对纯图卷灰**＋人话（筐里全纯图才灰） | // §2 **纯图卷置灰**＋人话（筐里全纯图才灰） |
| 3 | ui_intake:106 `dock()` | **组合路**只支持文字卷：筐里是纯图卷，识别已回到自动分流。 | 只支持文字卷：筐里是纯图卷，识别已回到自动分流。 |
| 4 | ui_model_install:83 | 装好后公式专科与**组合路公式步**生效。 | 装好后公式专科与**文字卷公式识别**生效。 |
| 5 | ui_model_install:96 | 装好后公式专科 Texify 档与**组合路公式步**生效。 | 装好后公式专科 Texify 档与**文字卷公式识别**生效。 |

## 桶三 · grep 收口证据

命令：`grep -rn "组合路" src/org.jiuzhang.editor --include=*.js --include=*.toml`
（插件仓，提交后实跑）命中 2 条，全为内部代码注释，不进界面：

| 命中 | 文本 | 判定 |
|---|---|---|
| `dist/ui_model_table.js:177` | `// 组合路是链路不是模型：进识别下拉，不进模型表（它的座已在表里）。` | 内部注释，按令保留 |
| `dist/ui_reidentify.js:149` | `… // 组合路是整批链路，单题/单块重认不列` | 内部注释，按令保留 |

- 5 处目标文案已零命中；`grep -c` 结果为 0（catalog.toml / ui_intake.js / ui_model_install.js 三文件）。
- 算子仓 `app/core/ingest/recognize/router.py:10/170/173` 仍含「组合路」，属技术口径（docstring/route note/异常），
  按卡面不碰；对应测试（test_ingest_triage:274、test_recognize_router:146/253/273）断言源侧不变，未改。
- 插件包内已无这 5 处旧字（in-zip 三文件与源逐字节 MATCH 即为证）。

## 桶四 · 实测证据（数字来自当次输出）

### 单测（逐模块，`.venv/Scripts/python.exe -m unittest tests.<模块>`，禁 discover/pytest）

| 模块 | 结果 |
|---|---|
| tests.test_last_used_engine | Ran 16 / OK |
| tests.test_models_registry | Ran 79 / OK |
| tests.test_command_registry | Ran 35 / OK |
| tests.test_file_size_contract | Ran 13 / OK |
| 合计（同批一次跑） | Ran 143 / OK，rc=0 |

### 门禁（底座仓）

| 项 | 结果 |
|---|---|
| `bash scripts/check-quick-gate.sh` | **PASS（6 项全过）**，rc=0 |
| 体积预警 | **23 份**（451–550 行区间），份数与基线相同，未新增 |
| `bash scripts/check-plugin-index-parity.sh` | PASS（两份索引语义一致、条目版本一致、示例题过契约校验），rc=0 |
| `bash scripts/check-plugin-package.sh` | PASS（官方插件 5 支，结构红线全部通过），rc=0 |

### 包结构自检（§7.1 第 2 项）

- zip 顶层目录名 == `plugin.toml` 的 `id` = `org.jiuzhang.editor`（90/90 条目同前缀）。
- 无 `backend` 字段；`license = Apache-2.0`，包内带 LICENSE 全文（package 门禁实检通过）。
- `min_host_version = 1.0.0`，底座当前 `app/__init__.py __version__ = 1.2.0` / 索引 host 1.2.0 —— 满足，未动。
- `models/` 与 `model_prefs.toml` 不入包（build_plugin DENY 生效）。

### 三查

`fetch(` / `parent.document` / `localStorage` 插件侧命中 0（快门禁 check-plugin-boundary 实跑输出）。本卡未新增请求。

## 桶五 · 偏离与欠账

- **偏离①（多改一个测试文件）**：卡面只点名 `test_last_used_engine`；`test_command_registry` 的官方插件手工表
  写死 editor 版本，版本一升必红，按「红了就按新文案/新事实改断言，不放宽判据」的口径同步到 2.26.1。
- **口径②（版本号入桌）**：卡面 operator 第 1 笔写「测试＋plugins.toml」，本卡照办，未把 zip 放底座仓
  （底座 `dist/plugins/` 是 git 忽略副本，发行 zip 唯一 tracked 位置是插件仓 `plugins/`）。
- **口径③（changelog）**：`plugins.json` 现有 changelog 是「新段前置＋旧段保留」的累积写法，本卡沿用，
  未删历史段；只改 version/changelog 两处（`git diff` 2 行），description 与 mirrors 未动。
- **证据限制**：本卡**未做 UI 真机探针**——改动是纯字符串文案，控件结构、id、下拉分组、置灰逻辑、
  registry/router 零变化，卡面亦注明不需要 UI 真测；文案生效以 in-zip 逐字节 MATCH＋单测断言为证。
  若需像素证据，可在下次重启后复用 `tools/last_used_engine_probe.py`。
- **重启提示**：插件 2.26.1 生效需主公重启一次（与在途重启债合并）；本卡未重启、未 push。
- **历史证据未动**：`docs/handoff/evidence/`、旧回单按 append-only 保留原样。

## 桶六 · 红线自检

- LICENSE／根 `agents.md`／`docs/AGENTS.md` 铁律一二／`app/core/question_contract.py`／用户 `data/`：零改。
- 插件仓未跟踪的 `model_prefs.toml`／`models/` 原地未 stage；底座 `?? tools/onnx_probe.py` 原地未动。
- 两仓均未 amend、未 push、未改 git config（插件仓用 `git -c user.name/user.email` 瞬态身份）。
- 无新建 JSON 落盘（回单与 biz 均为 MD；`plugins.json` 是既有索引文件，非新增）。
- 65496（PID 2700）零接触；未起服务、未杀 python 进程、零出网。

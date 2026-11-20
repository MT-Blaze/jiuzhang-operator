# 回传单 · 默认引擎记上次＋识别下拉分组全组合小刀卡（识别引擎线·排队③·合并卡，2.24.0）

【回执编号】 #LUE-01
【回执时间】 2026-11-20T13:06:00+08:00
【实际耗时】 单段无人值守执行会话（复核锚点→plugins 刀→operator catalog→JS 单测＋门禁三查→封版 parity＋zip 双建→Playwright 八项真测→命名探针同步→回单；含一次上下文压缩接力，收口段补做 zip 重打落仓）
【执行结果】 **成功**（卡§0–§5 全范围落地；§4 八项真测全绿；§6 停链条款均未触发）。定向 6 模块 184/184 绿；快门禁 PASS（6 项）；三查 0/0/0；新探针 last_used_engine_probe run2 **35/35**（ok=true）；canvas_inline_config_probe **23/23**、model_table_probe **35/35** 收口复跑皆绿。两仓 commit 不 push（奉令 hold）。

基线（开工实测，与派卡 prompt 写死值一致）：operator `4a61e60`（ahead 70）／plugins `1083f4a`（ahead 19，editor 2.23.1）。
本卡 operator 三笔：`224b2df`（配套测试＋索引 parity）／`3dcb456`（真机探针＋命名探针同步＋证据）／收口笔（本回单＋biz）；ahead 按笔数记 70＋3＝**73**（免随 commit 漂移）。
plugins 两笔：`5ede547`（记上次＋分组＋两组合代码，5 文件）／`e6569ce`（发行包重打）；ahead 19＋2＝**21**。
biz 记录：`.qoder/records/biz/2026-11/20261120_last-used-engine.md`。
卡：`E:\jiuzhang\默认引擎记上次小刀卡.md`（唯一口径）。
交付版本 **editor 2.24.0**（四处 parity 一致）；底座单源 `app/__init__.py:8` `__version__="1.2.0"` 未动。

## 卡§0 口径复述（逐字生效）

默认改「记上次」（last-used）：默认＝老师上一次选什么、新批次初值就什么；②手动默认行整砍；①改名「自动设置」；首回无历史＝自动。**自动**＝按卷型分流（①保留）；**默认**＝last-used 记忆，无可见配置项（②删）。识别下拉分两组：optgroup「整题OCR」＝auto＋就绪整题座；optgroup「文字直取+公式·X」＝组合路；版面下拉不分组保持原样。全组合＝按就绪公式座枚举，补 catalog `combo_pp_l`/`combo_p2t`；texify 组合本卡不预建（卡④接线时补）。隐藏＝未配置/未就绪/停用不进下拉（现状 applyRegistry 保持）。
两仓不 push（主公明确不授权别再问）；65496 零接触（探针隔离副本，现 PID 17136 禁擅自重启/杀）；**零出网零额度零引擎真跑**（纯 UI/prefs/catalog）；失败显性不偷换不降级；无人值守不许问主公，偏离记回单，真卡死＝停链登记。tests 一律 `.venv/Scripts/python.exe -m unittest tests.<模块>` 逐模块（禁 pytest/discover）；Playwright 穿沙箱真浏览器；新探针禁写死端口/令牌；plugins commit MT-Blaze 瞬态身份绝不写 git config；隔离副本 `git archive HEAD` 禁抄工作树；LICENSE/铁律一二/question_contract.py/用户 data/ 禁改；onnx_probe.py 原地不 stage；engines 不 stage；禁 JSON 落盘；分层≤3；records append-only；冻结台账只减不增；models/＋model_prefs.toml 不入包不碰。

## 做了什么（逐条对齐卡§1–§5）

- §2.1 记上次回写：`ui_intake.js` bindSelect change 内按 kind 走 `hostCall("models.prefs_save", {default_layout:key})`/`{default_recognize:key}`（复用既有两键，不新增键不迁移）。**仅显式 change 回写**；加载期兜底落 auto 不回写（卸座不擦记忆）；回写失败显性 dock 提示不静默不阻塞解析。读口 applyRegistry 一字未动。
- §2.2 砍②行：`ui_model_config.js` renderDefaults 整函数＋调用点＋「默认引擎」标签串全删（39 行净减）。
- §2.3 改名①：renderAutoSeats 头部标签改「自动设置（按卷型分流走哪座；默认座未就绪会显性提示，不偷换）：」，class 加 `ep-model-config-auto-seats`，两下拉（auto_image_seat/auto_text_formula_seat）保留。
- §2.4 分组：`ui_intake.js` paintEngineOptions 对 edRecognizeEngine 用 optgroup——「整题OCR」放 auto＋非 combo 的 recognizeAllowed；「文字直取+公式·X」放 comboIds（选项文案沿用 catalog name）。edLayoutEngine 保持扁平。纯图卷筐 combo 置灰＋归自动逻辑保留（renderBasket 末尾重绘）。
- §2.5 全组合：`catalog.toml` 增 `combo_pp_l`（store=formula_l，combo_seat=formula_pp_l，name「文字直取+公式·PP-FormulaNet·L」）/`combo_p2t`（store=formula_p2t，combo_seat=formula_p2t，name「文字直取+公式·Pix2Text·MFR」），capability=recognize、plan_recognize=["combo"]。**就绪 rule 用 weight_present 随本座公式权重**（见偏离①）。registry/router 代码零改（通用 combo_seat 取座）。现 5 组合：combo_cloud/combo_vlm/combo_pp_m/combo_pp_l/combo_p2t。
- §3 测试：新增 `tests/test_last_used_engine.py`（15 案 JS 结构契约）；`test_model_prefs.py` 增记上次两键独立往返例；`test_models_registry.py` 增五组合声明＋weight 规则随座例；`test_command_registry.py` EXPECTED editor 版随升 2.24.0。命名探针同步：canvas_inline_config_probe ②键盘默认段改记上次回写取证（23/23 绿）；t6_route_probe/config_to_plugin_probe/mineru_four_probe registry 计数 16→18（三者基线已陈旧，见偏离④）。
- §4 真测：新增 `tools/last_used_engine_probe.py`（411 行，隔离副本 git archive HEAD＋动态端口随机令牌＋data/plugins 全隔离＋云账号本地种 .invalid 域零出网＋真实公式/VLM 权重），八项 35 判据 run2 全绿；证据落 `docs/handoff/evidence/last-used-engine/`（probe.toml/wire.toml/shots 6 张）。
- §5 封版：parity 四处 2.24.0＋zip 双建同哈希 `3a453c7c…`＋sync_plugin_index rc0；models/＋model_prefs.toml 不入包。

## 【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator，基线 4a61e60 → 3dcb456＋收口笔）

施工笔（每大阶段一笔，不 push）：
- `224b2df` 记上次＋全组合配套测试与索引同步（5 文件）：`tests/test_last_used_engine.py`（新增 171 行 15 案）／`tests/test_model_prefs.py`（+14）／`tests/test_models_registry.py`（+52）／`tests/test_command_registry.py`（EXPECTED :515 → 2.24.0）／`plugins.toml`（editor 2.24.0，sync_plugin_index 改写）。
- `3dcb456` 真机探针与命名探针同步（13 文件 +622/-13）：`tools/last_used_engine_probe.py`（新增 411 行）／`tools/canvas_inline_config_probe.py`（②段改记上次，+20/-…）／`tools/t6_route_probe.py`／`tools/config_to_plugin_probe.py`／`tools/mineru_four_probe.py`（各 registry 计数 16→18）／`docs/handoff/evidence/last-used-engine/`（probe.toml 190 行＋wire.toml＋shots 6 png）。
- 收口笔：本回单 `docs/handoff/receipts/last-used-engine.md`＋biz 记录。
- **生产代码（app/、static/）：零改。** registry/router/model_prefs/契约/字典/上传链/单题重认路全未触碰。

### 插件仓（E:\jiuzhang\jiuzhang-plugins，基线 1083f4a → e6569ce，MT-Blaze 瞬态身份）

- `5ede547` editor 2.24.0 代码（5 文件 +72/-43）：`dist/ui_intake.js`（记上次回写＋optgroup 分组，678 行冻结台账内）／`dist/ui_model_config.js`（砍 renderDefaults＋①改名，316 行≤450）／`catalog.toml`（+combo_pp_l/combo_p2t 两条，18 条目 5 组合）／`plugin.toml`（:4 version 2.24.0）／`plugins.json`（:68 version 2.24.0＋changelog）。
- `e6569ce` 发行包重打：`plugins/org.jiuzhang.editor.zip`（335275→335895 字节，2.24.0 内容）。
- `src/org.jiuzhang.editor/models/`＋`model_prefs.toml` 保持 untracked 未 stage（卡面点名不碰）。

### 禁改区自查

- LICENSE：未触碰。AGENTS.md 铁律一二：未改。app/core/question_contract.py：未触碰。
- 用户 data/：零字节改动（探针全走隔离副本 .system_generated/last-used-engine/，JZO_DATA_DIR/JZO_PLUGINS_DIR 临时区）；65496 正式服务（PID 17136）与 live engines/ 零接触（探针 engines/ 只读体检本机真实权重，不起服务不跑推理）。
- tools/onnx_probe.py：原地未 stage（git status 仍 untracked）。engines 产物：未 stage。
- 禁 JSON 落盘：证据全 TOML/MD/PNG。分层≤3：新模块全在既有 tests/、tools/、docs/handoff/ 层内，无新层。records append-only：biz 新建。冻结台账只减不增：LEGACY_OVER_CEILING 名单未删项（ui_intake.js 595→678 属冻结老文件行数可涨可落，只记录不判红）。
- stage 点名（各笔点名文件，禁 add -A）；不 amend；不 push。plugins 两笔均 `-c user.name=MT-Blaze -c user.email=tianxiulaoshi@163.com` 瞬态身份，绝不写 git config。

## 【包结构自检】

`tools/build_plugin.py` 实跑双建（`.system_generated/last-used-engine/zip-build1|build2/`）：
- 顶层目录名 == `org.jiuzhang.editor` == plugin.toml id ✓
- 无 `backend` 字段 ✓；Apache-2.0 `LICENSE` 全文在包内 ✓
- `models/` 未入包（DENY_DIRS）✓；`model_prefs.toml` 未入包（DENY_NAMES）✓；无 .db/.zip/.pyc/dev/ ✓
- 包内 plugin.toml `version = "2.24.0"` ✓；`min_host_version = "1.0.0"` ≤ 当前底座 `1.2.0`（app/__init__.py:8 单源）✓；无 [engine] 节
- 包内 catalog.toml 含 combo_pp_l/combo_p2t ✓；共 90 条目
- **zip 确定性双建哈希一致**：`3a453c7c2b4a60b215f9f9f5c3fbdab9d06d506938b65905978b467d45ea271c`（build1 == build2，落 plugins/org.jiuzhang.editor.zip 同哈希）
- **四处 parity 2.24.0**：插件 plugin.toml:4 ／ plugins.json:68 ／ 主仓 plugins.toml:51 ／ test_command_registry EXPECTED:515；`tools/sync_plugin_index.py` **rc=0**「远端索引一致」（editor@2.24.0）
- 版本一致性 `tests.test_version_consistency` 29/29 绿

## 【三查结果】（bash scripts/check-plugin-boundary.sh 当次实跑）

- 插件侧 `fetch(` 命中 **0** ✓
- 插件侧 `parent.document` 命中 **0** ✓
- 插件侧 `localStorage` 命中 **0** ✓
- 插件源码零 Python ✓；宿主侧 static/js 带 fetch( 文件 17（出网全由界面点击发起；本卡探针 install_requests 全程空数组实证零出网）
- 请求 id 全合规（test_command_registry 35/35 钉死）；本卡未新增请求族（复用 models.prefs_save）

## 【测试与探针】

解释器一律 `.venv/Scripts/python.exe -m unittest tests.<模块>`（逐模块点名，禁 pytest/discover）。

### 定向单测（收口当次复跑，6 模块 184/184 绿）

| 模块 | N/N |
|---|---|
| test_last_used_engine（新增） | 15/15 |
| test_model_prefs | 16/16 |
| test_models_registry | 76/76 |
| test_command_registry | 35/35 |
| test_version_consistency | 29/29 |
| test_file_size_contract | 13/13 |

快门禁 `bash scripts/check-quick-gate.sh` **PASS（6 项全过）**；体积预警 23 份均既存文件（451–550 区间），本卡新文件 test_last_used_engine 171／last_used_engine_probe 411／ui_model_config 316 均≤450；ui_intake.js 678 属冻结台账老文件（只记录不判红）。冻结台账只减不增。

### 真机探针（Playwright 穿沙箱，隔离副本 git archive HEAD＋动态端口＋随机令牌，收口点杀＋端口复验＋孤儿零）

| 探针 | 绿轮 | 判据 | 证据路径 |
|---|---|---|---|
| last_used_engine_probe（新增） | run2 | **35/35**（ok=true） | docs/handoff/evidence/last-used-engine/probe.toml＋wire.toml＋shots 6 |
| canvas_inline_config_probe（②段同步） | lue-verify | **23/23** | .system_generated/canvas-inline-config/lue-verify/probe.toml |
| model_table_probe（无改，复验无回归） | lue-verify | **35/35** | .system_generated/model-table/lue-verify/probe.toml |

§4 八项真人路径走过（工具经 CDP 发真实输入事件）：
1. 配置页①「自动设置」两下拉在、②行不在、全页无「默认引擎」字样（shot 01）；
2. 识别下拉两 optgroup 头＝「整题OCR」「文字直取+公式·X」，底组 5 组合全列（combo_cloud/vlm/pp_m/pp_l/p2t，就绪前提），顶组 auto＋就绪整题座不含组合，版面下拉平铺无 optgroup（shot 02）；
3. 停用组合座（代笔 prefs disabled）→刷新下拉摘除 combo_pp_l→启用恢复；data/ 全树无 model_prefs.toml（shot 03-combo-disabled）；
4. 画布选识别座→回写 default_recognize→刷新初值＝上次；版面另选 yolo 互不串；归自动回写 auto 不擦版面记忆（shot 04）；
5. 存过座停用→刷新初值 auto 且 prefs 未擦（default_recognize 仍 combo_pp_l）→启用恢复（shot 05）；
6. 首回干净 data 识别/版面皆 auto、prefs 未落盘；
7. 纯图卷（1×1 PNG）入筐→combo 置灰＋人话 title「组合路只支持文字卷：筐里这份是纯图卷，文字直取无从谈起…」，整题座不受置灰（shot 03-pure-image-gray）；
8. 零 JS 异常/零 HTTP 失败/三查 0/零安装请求（零出网）/收口端口复验闭/孤儿进程零。

云视觉座就绪由宿主写口本地种 dummy 账号（base_url=https://probe.invalid/v1，.invalid 域零出网）＋指派 ocr 任务；公式 M/L/p2t＋VLM 三座读本机真实权重就绪；YOLO 假权重隔离副本内预置。**不跑识别/不出网/不耗额度**。

### 基线红（非本卡回归，见偏离③）

`tests.test_ingest_triage` 21 案 1 红：MineruPerQuestionTest.test_single_question_screenshots_not_the_whole_pdf（seen_names 空）。本卡 operator 两笔零触 app/ 生产码、零触该测试文件、零触 MinerU 逐题路；前段已用可逆 catalog 交换实证基线 plugins HEAD catalog 同样红＝预存基线病，与本卡无涉。

## 【未决问题与偏离】

### 偏离（全如实披露）

1. **组合就绪 rule 用 weight_present 而非照抄 combo_pp_m 的 import_probe**：卡§2.5 字面「镜像 combo_pp_m 全字段…rule 照抄改座」，但 combo_pp_m 用 `import_probe`（probe="app.core.ingest.recognize.formula" 宿主模块恒在＝恒就绪），照抄会使 combo_pp_l/combo_p2t 不论公式权重在不在都恒就绪，**违反§0「按就绪公式座枚举」/§4.2「就绪前提下」/§6「组合就绪判定不随座＝停链」**。故新两组合改用 `weight_present`（store=formula_l/formula_p2t，与对应公式专科座同 rule 同 store），就绪真随本座权重——满足占主导的「随座」语义。combo_pp_m 本身保持 import_probe 不动（不动面）。此为卡面内部字面矛盾，按占主导的「随座」语义定夺并登记。
2. **parity ④ 基线不齐**：开工实测 test_command_registry EXPECTED editor 版＝2.23.0，而①②③＝2.23.1（基线即不齐）。本卡四处统一升 2.24.0 修齐。
3. **MineruPerQuestionTest 基线红**：test_ingest_triage 1 红（seen_names 空），前段可逆 catalog 交换实证基线 HEAD 同样红＝预存病，非本卡回归（本卡零触该路）。登记不 retro-edit，另卡治。
4. **三命名探针基线已陈旧**：t6_route_probe／config_to_plugin_probe／mineru_four_probe 仍断言旧 fallback 配置 UI（.ep-model-config-row／默认引擎键盘段），该 UI 早在 2.20.0 已被四栏表取代——config_to_plugin_probe 实证 .ep-model-config-row 解析 0、mineru_four_probe 同病；t6_route_probe 另含真识别＋真安装出网（重）。本卡只同步其 registry 计数 16→18（不跑），**陈旧断言刷新建议另卡**（与本卡记上次/分组无涉，不硬闯）。现 UI 探针 canvas_inline_config_probe（23/23）/model_table_probe（35/35）已验证绿。
5. **组头字面「文字直取+公式·X」**：optgroup 标签按卡§0 末令用 ASCII「+」逐字「文字直取+公式·X」（探针 GROUP_HEADS 同）；选项文案沿用 catalog name——新两组合 name 用 ASCII「+」（卡§2.5 点名），旧 combo_cloud/vlm/pp_m name 仍全角「＋」（基线不动）。组头与选项文案全角/半角并存属基线遗留，本卡只保证组头逐字合末令。
6. **§4.3「停用某公式座→其组合消失」取证落在组合条目本身**：组合条目不进配置四栏表（ui_model_table.js:177-178 滤 combo），老师无 UI 勾选可停组合；且 registry enabled 按条目判（registry.py:299 不传播，不动面），停公式座不会停其组合（weight_present 随权重非随座 enabled）。故探针经代笔 prefs `disabled=["combo_pp_l"]` 停**组合条目本身**＋刷新证 applyRegistry enabled 过滤摘除/恢复＝§0「隐藏＝停用不进下拉」真证。此为对卡面「停座」措辞的忠实落地（隐藏语义按条目，就绪语义随座权重），非停链。

### 欠账清单

1. **combo_pp_m 就绪恒真（基线遗留）**：import_probe 恒就绪，公式 M 权重缺时组合仍显示——本卡不动面未治，与偏离①同源，建议另卡统一改 weight_present 随座。
2. **三命名探针陈旧断言**：t6/config_to_plugin/mineru_four 旧 fallback UI 断言待另卡刷新（偏离④）。
3. **MineruPerQuestionTest 基线红**：待另卡治（偏离③）。
4. **texify 组合未预建**：卡④接线时补 combo_texify（本卡按令不预建）。
5. **新码生效需主公再重启一次**：插件 2.24.0 已落仓打 zip，但 65496 正式服务（PID 17136）仍跑旧码；**主公需再重启一次正式服务**方能在真界面看到记上次/分组/两组合。本卡奉令零接触 65496，未擅自重启。

### 需主公点什么

- **新码生效需主公再重启一次**（65496 正式服务，本卡零接触未擅动）。
- 两仓 **push 授权**（现 hold：operator 73 ahead／plugins 21 ahead，主公明确不授权别再问，奉令 hold）。
- 偏离①组合 rule weight_present 是否认可（已按「随座」语义落地并钉测试）；combo_pp_m 是否另卡统一随座。
- 三命名探针陈旧刷新是否排卡。

## 收口复验

- 探针收口端口复验关闭（last_used_engine run2／canvas_inline lue-verify／model_table lue-verify 各 probe.toml「收口端口复验关闭」PASS）；孤儿进程零（last_used_engine run2 count=0）；65496 正式服务全程未碰；用户 data/ 零字节改动；零出网（install_requests=[]）。
- 两仓 git status：底座仅 `?? tools/onnx_probe.py`（卡面点名保持 untracked）；插件仅 `?? src/org.jiuzhang.editor/model_prefs.toml`＋`?? src/org.jiuzhang.editor/models/`（卡面点名保持 untracked）。无未提交施工改动。
- zip 双建同哈希 3a453c7c…落 plugins/org.jiuzhang.editor.zip；sync_plugin_index rc0；四处 parity 2.24.0。
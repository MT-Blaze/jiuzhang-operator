# 默认引擎记上次＋识别下拉分组全组合（last-used-engine）

状态：成功收口（editor 2.24.0 封版，四处 parity＋zip 双建同哈希；两仓 commit 不 push 奉令 hold；新码生效需主公再重启一次 65496）
发起日期：2026-11-20
需求来源：主公 2026-11-20 两次点头合并（「对的，出卡吧」＝默认改记上次；「整题OCR／文字直取+公式·X 这个显示挺好…能合并的卡就合并」＝识别下拉分组＋全组合并入），枢纽转达默认引擎记上次小刀卡（E:\jiuzhang\默认引擎记上次小刀卡.md，识别引擎线·排队③·合并卡）
基线：operator 4a61e60（ahead 70）／plugins 1083f4a（ahead 19，editor 2.23.1）；本卡 operator 三笔（224b2df/3dcb456/收口笔，ahead 73），plugins 两笔（5ede547/e6569ce，ahead 21）
回单：docs/handoff/receipts/last-used-engine.md（#LUE-01）

## [REQ] 2026-11-20

默认改「记上次」（last-used）：默认＝老师上一次选什么、新批次初值就什么；②手动默认行整砍；①改名「自动设置」；首回无历史＝自动。自动＝按卷型分流（①保留）；默认＝last-used 记忆，无可见配置项（②删）。识别下拉分两组：optgroup「整题OCR」＝auto＋就绪整题座；optgroup「文字直取+公式·X」＝组合路；版面下拉不分组保持原样。全组合＝按就绪公式座枚举，补 catalog combo_pp_l/combo_p2t（镜像 combo_pp_m，combo_seat 对应）；texify 组合本卡不预建（卡④补）。隐藏＝未配置/未就绪/停用不进下拉（applyRegistry 现状保持）。
红线：两仓不 push（主公明确不授权别再问）；65496 零接触（PID 17136 禁擅自重启/杀）；零出网零额度零引擎真跑（纯 UI/prefs/catalog）；失败显性不偷换；无人值守不许问主公，偏离记回单，真卡死＝停链登记；tests 逐模块 unittest 禁 pytest/discover；Playwright 穿沙箱；新探针禁写死端口/令牌；plugins commit MT-Blaze 瞬态身份绝不写 git config；隔离副本 git archive HEAD 禁抄工作树；LICENSE/铁律一二/question_contract.py/用户 data/ 禁改；onnx_probe.py/engines 不 stage；禁 JSON 落盘；分层≤3；records append-only；冻结台账只减不增；models/＋model_prefs.toml 不入包不碰。

## [PLAN] 2026-11-20

同文件同下拉合并施工免两次串行：ui_intake.js 加分组＋记上次回写（bindSelect change 走 models.prefs_save 复用 default_layout/default_recognize 两键，仅显式 change 回写、加载兜底 auto 不落盘＝卸座不擦记忆）；ui_model_config.js 砍 renderDefaults 整块＋①改名自动设置；catalog.toml 增两组合条目，registry/router 零代码改（通用 combo_seat 取座）。
取舍：① 组合就绪 rule——卡§2.5 字面「照抄 combo_pp_m rule」，但 combo_pp_m 用 import_probe（宿主模块恒在＝恒就绪）不随座权重，照抄违反§0「按就绪公式座枚举」/§6「就绪不随座＝停链」；故新两组合用 weight_present（store 与公式专科座同）真随座，combo_pp_m 保持不动（不动面），登记偏离。② §4.3「停公式座→组合消失」——组合不进配置四栏表（ui_model_table 滤 combo）且 enabled 按条目不传播（registry.py:299 不动面），停座不停组合；故取证落组合条目本身（代笔 prefs disabled）证 applyRegistry 隐藏语义，登记偏离。③ 被否方案：改 registry 让 enabled 座→组合传播——属冻结读口，不擅自解冻。

## [IMPL] 2026-11-20

- plugins（commit 5ede547，5 文件 +72/-43，MT-Blaze 瞬态身份）：dist/ui_intake.js（记上次回写＋optgroup 分组，678 行冻结台账内）／dist/ui_model_config.js（砍 renderDefaults＋①改名，316 行≤450）／catalog.toml（+combo_pp_l store=formula_l/combo_p2t store=formula_p2t，18 条目 5 组合）／plugin.toml:4＋plugins.json:68（2.24.0＋changelog）。
- plugins 发行包（commit e6569ce）：plugins/org.jiuzhang.editor.zip 重打，双建同哈希 3a453c7c2b4a60b215f9f9f5c3fbdab9d06d506938b65905978b467d45ea271c；顶层==id，models/＋model_prefs.toml 不入包，LICENSE 在包，min_host_version 1.0.0≤底座 1.2.0。
- operator 测试＋索引（commit 224b2df，5 文件）：tests/test_last_used_engine.py（新增 171 行 15 案 JS 结构契约）／test_model_prefs.py（+记上次两键独立往返）／test_models_registry.py（+五组合声明＋weight 随座）／test_command_registry.py（EXPECTED:515→2.24.0）／plugins.toml（sync_plugin_index 改写 editor 2.24.0，rc0）。
- operator 探针＋证据（commit 3dcb456，13 文件 +622/-13）：tools/last_used_engine_probe.py（新增 411 行，git archive HEAD 隔离＋动态端口随机令牌＋云账号 .invalid 本地种零出网＋真实公式/VLM 权重，八项 35 判据）／canvas_inline_config_probe.py（②键盘默认段改记上次回写取证）／t6_route_probe/config_to_plugin_probe/mineru_four_probe（registry 计数 16→18，三者基线陈旧只同步不跑）／docs/handoff/evidence/last-used-engine/（probe.toml＋wire.toml＋shots 6）。
- 生产代码（app/、static/）零改；registry/router/model_prefs/契约/字典/上传链/单题重认路/版面下拉一字未动。
- 使用 skill：build-release（封版 parity＋zip 双建＋sync_plugin_index）；prove-visual-change/run-regression（Playwright 穿沙箱真测＋定向单测口径，AGENTS §7 定向＋门禁为主全量免）；sync-biz-record（本记录）。

## [VERIFY] 2026-11-20

- 定向单测（.venv/Scripts/python.exe -m unittest 逐模块，收口复跑）：test_last_used_engine 15/15＋test_model_prefs 16/16＋test_models_registry 76/76＋test_command_registry 35/35＋test_version_consistency 29/29＋test_file_size_contract 13/13＝6 模块 184/184 绿。
- 快门禁 bash scripts/check-quick-gate.sh → PASS（6 项全过）；体积预警 23 份均既存（451–550），本卡新文件 171/411/316 均≤450；ui_intake.js 678 冻结老文件只记录不判红；冻结台账只减不增。
- 三查 bash scripts/check-plugin-boundary.sh → fetch( 0／parent.document 0／localStorage 0；插件零 Python；请求 id 全合规（复用 models.prefs_save 无新增族）。
- Playwright 真测（穿沙箱，隔离副本＋动态端口＋随机令牌，零出网）：last_used_engine_probe run2 35/35 ok=true（八项：①自动设置在②砍/两组 5 组合/停用摘除启用恢复/记上次刷新初值＝上次版面独立归自动/存座停用归自动 prefs 不擦启用恢复/首回 auto/纯图卷 combo 灰＋人话/零异常零 HTTP 失败收口端口闭孤儿零）；canvas_inline_config_probe lue-verify 23/23；model_table_probe lue-verify 35/35（无回归）。证据 docs/handoff/evidence/last-used-engine/。
- 包结构自检：zip 双建同哈希 3a453c7c…；四处 parity 2.24.0（plugin.toml:4/plugins.json:68/operator plugins.toml:51/test_command_registry:515）；sync_plugin_index rc0 远端索引一致。
- 基线红（非本卡回归）：test_ingest_triage 21 案 1 红 MineruPerQuestionTest（seen_names 空），前段可逆 catalog 交换实证基线 HEAD 同样红＝预存病；本卡 operator 零触 app/ 生产码/该测试/MinerU 逐题路。
- 禁改区自查：LICENSE/铁律一二/question_contract.py/用户 data/ 未触碰；onnx_probe.py 与 plugins 仓 models//model_prefs.toml 原地未 stage；engines 产物未 stage；禁 JSON 落盘（证据全 TOML/MD/PNG）；65496 PID 17136 与 live engines/ 零接触；零出网（install_requests=[]）。

## [RELEASE] 2026-11-20

- 交付 editor 2.24.0（底座单源 app/__init__.py:8 __version__=1.2.0 未动）；zip 落 plugins/org.jiuzhang.editor.zip（3a453c7c…），两份索引语义一致（sync_plugin_index rc0）。
- 两仓 commit 不 push（奉令 hold：operator ahead 73／plugins ahead 21，主公明确不授权别再问）。
- **新码生效需主公再重启一次**：65496 正式服务（PID 17136）仍跑旧码，本卡零接触未擅自重启；主公重启后方能在真界面看到记上次/分组/两组合。
- 遗留待另卡：combo_pp_m import_probe 恒就绪（建议统一 weight_present 随座）；t6/config_to_plugin/mineru_four 三命名探针陈旧 fallback UI 断言刷新；MineruPerQuestionTest 基线红；texify 组合卡④补。
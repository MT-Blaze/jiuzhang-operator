# 回传单 · 公式专科 PP-FormulaNet·M 单座安装与推理接线卡（2.22.0）

【回执编号】 #PP-M-01
【回执时间】 2026-11-19T22:43:37+08:00
【实际耗时】 跨段执行会话（含侦查/安装链/推理/6 轮真机探针，探针累计约 38 分钟；run6 收口 450.2s）
【执行结果】 成功。真机探针 run6 全绿 32/32（ok=True）；定向 17 模块 575/575 绿；快门禁 6 项 PASS；JS 153/153；三查 0/0/0；zip 双建同哈希 23de1670…；四处 parity 2.22.0 一致；两仓 commit 不 push（奉令 hold）。

主公 2026-11-19 点头原话：「PP-FormulaNet·M（公式专科）先把这个写了，其他的先不动」＝只做 PP-M 单座。
基线：底座 33161f6 ／ 插件 87e1729（2.21.0）；交付版本 2.22.0。
biz 记录：`.qoder/records/biz/2026-11/20261119_formula-pp-m.md`。

## 卡§0 口径复述（逐字生效）

两仓不 push；微批 3–5 公式裁图；MinerU 本地 CPU 逐题填充与 VLM CPU 耗时证据停跑令；
出网必须界面点击发起、禁 GitHub；65496 正式服务零接触（探针 git archive 隔离副本＋动态端口＋随机令牌）；
可以慢不能不稳、失败显性不偷换不降级；其余五座（PP-L/P2T-MFR/Texify/书生/面壁）catalog 一字不动、擂台留 D 卡。

## 【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator，施工六笔＋收口笔）

- `71088de` docs：侦查证据——Apache-2.0 白名单／国内源可达＋sha256 登记／官方 ONNX＋底座现成
  onnxruntime 零新依赖／I/O 形状（x[B,1,384,384] float32 灰度→int64 seq，yml 内嵌 BPE 50000 词表）／
  CPU 0.76–1.20s/块放行。证据 `docs/handoff/evidence/pp-m-recon/`。
- `5350ebd` feat：安装链——`app/core/ingest/formula_setup.py`（188）复用 mirrors.race＋ocr_setup 先例，
  权重落 `engines/formula/models/`（onnx 593908338B/sha 52afa60f…＋yml 2244564B/sha 87b5f3d7…）；
  `app/core/ingest/recognize/formula_pp_m.py`（199）引擎适配器：懒加载 session＋weights_ready 闸口＋
  预处理（crop_margin→短边384→居中补黑→(x/255−0.7931)/0.1738）＋图内贪心解码（eos 截断/特词跳/
  ByteLevel 拼字节/\text{中文}解包/空白压缩三规则保护占位）＋出口 latex_norm.clean 闭集清洗；
  registry formula 三态（weight_present）＋API/relay 三口子（install/status/uninstall）＋test_15b。
- `488f6d5` feat：推理接线——`recognize/formula.py` dispatch 接 formula_pp_m 步（394→398 行守帽）；
  `recognize/reidentify.py`（188）整题选 PP-M 显性拒绝（公式专科座只认裁图，引导整题座）；
  combo_pp_m 组合文字卷公式步真跑；＋test_formula_route 5 用例＋test_reidentify 3 用例。
- `bec8870` fix：D12 文字层归一题面匹配——文字直取经 scan_text.text_to_latex 归一后数学串已是
  $latex$，文字层 span 的 PDF 原字符不再现于题面→原串匹配与空 latex 双落空（run3 微批 0/5 现场）。
  replace_fragment 补文字层分支：_run_to_latex 同规则推已知片段走既有已知 LaTeX 匹配，不裸拼口径不变；
  ＋3 用例（含 scan_text 归一往返一致性）。修后组合路 14/14 原位回填（修前仅 3）。
- `8ac177f` fix：题库引擎空库首启并发懒建库竞态（存量缺陷，run4 探针 500 现场）——dao_base.connect
  进程锁双检串行化懒建库；＋8 线程并发首连回归用例。
- `9843f53` fix：建库期预设 WAL（存量缺陷，run5 探针 500/400 现场）——建库锁只串行化了建库，
  落成库仍 DELETE 日志模式，首启并发连接各切 WAL 抢排它锁；_build_into 建库期即落 WAL，
  回归用例加钉 journal_mode=wal。
- 收口笔（本回单所在 commit）：`tools/build_plugin.py` DENY_NAMES 补 model_prefs.toml（老师勾选
  运行时财产，carried 语义绝不随包发行；包自检门禁驱动）＋test_layout_models 2 用例；
  `tools/pp_m_live_probe.py`（448）真机探针；`plugins.toml` sync 2.22.0；
  `tests/test_command_registry.py` test_29 基线 2.22.0（顺带修 2.21.0 封版漏更红）；
  回单＋证据＋biz 记录。

### 插件仓（E:\jiuzhang\jiuzhang-plugins，两笔＋收口笔，MT-Blaze 瞬态身份）

- `635ccef` feat：catalog 只改 PP-M 一条（blocked→weight_present 三态＋store=formula＋
  plan_recognize=[formula_pp_m]＋安装引导活字）；ui_model_install.js formula 工种（596MB 确认弹窗
  活字/卸载引导）＋ui_model_table.js 本地判定。其余五座一字不动（diff 87e1729..HEAD 可验）。
- `66591d1` fix：panel_reidentify.css 席名 span 补 white-space:normal 一行——压住 ep-mini-btn
  继承的 nowrap，375px 长席名换行不横向溢出（T6 存量缺陷，run1 现场）。
- 收口笔：plugin.toml 2.22.0＋plugins.json editor 块 version/changelog＋plugins/org.jiuzhang.editor.zip
  （双建同哈希 23de1670ac4b63a94564cf6a3f2a2388649311742f6ce7d5863f9a789e487209，333921B/326.1KB）。

## 【包结构自检】

- 顶层目录名 == plugin.toml id（org.jiuzhang.editor）；包内 version 2.22.0；条目 90。
- Apache-2.0 LICENSE 全文 202 行；无 backend 字段、无 [engine] 段。
- min_host_version 1.0.0，当前底座 1.2.0 满足（host.version 1.2.0，plugins.json 已登记）。
- 违禁条目零：models/ 零、model_prefs.toml 零、.onnx/.db/.pyc/dev/ 零（DENY_NAMES 本次补 prefs 名）。
- 双建同哈希：build1/build2 均 23de1670…；发行位 ../jiuzhang-plugins/plugins/org.jiuzhang.editor.zip 同哈希。
- sync_plugin_index rc0，远端语义一致；四处 parity（plugin.toml/plugins.json/主仓 plugins.toml/包内）2.22.0。

## 【三查结果】

插件 dist JS grep：fetch(=0、parent.document=0、localStorage=0（探针内同判据复验 0/0/0）。
请求 id 均走宿主 relay 白名单既有口径（pending.reidentify/pending.reidentify_spans/models.* 无点号）。

## 【测试与探针】

解释器一律 `.venv/Scripts/python.exe -m unittest tests.<模块>`（禁 pytest/discover），收口总账 17 模块 575/575：
test_formula_route 32／test_reidentify 25／test_models_registry 67／test_model_prefs 15／test_auto_split 9／
test_command_registry 35／test_layout_models 22／test_latex_norm 37／test_clean_latex 13／test_latex_style_dict 30／
test_editor_contract 174／test_plugin_suite 11／test_workspace_pure_release 10／test_bank_engine_v2 24／
test_bank_api 51／test_bank_dashboard 6／test_bank_provider 14。
快门禁 `bash scripts/check-quick-gate.sh` PASS（6 项；23 份体积预警原班无新增）；JS node --check 153/153。

真机探针 `tools/pp_m_live_probe.py` run6 全绿 32/32（450.2s）：
git archive 两仓 HEAD（operator 9843f53／plugins 66591d1）隔离副本、动态端口 14261、随机令牌、
JZO_DATA_DIR/JZO_PLUGINS_DIR 全隔离，65496 零接触。判据链：
初始 degraded＋五座不动→未安装三态＋375px overflow 0→原串批次（自动文字卷＋默认公式座未装→
显性标待核零回填，零 MinerU/VLM 引擎零出网）→安装真证（596MB 弹窗活字 accept→POST 确由界面点击→
done→双件 sha256 逐字一致→就绪＋卸载钮→375px overflow 0）→combo_pp_m 文字卷真路（mode/text_layer、
14 道公式裁图 14 道原位回填、无坐标兜底云未指派显性失败）→重认微批 5 块真 dispatch 4 块原位替换
（before/after stem 比对实证）→整题选 PP-M 显性拒绝→375px 工具行 overflow 0→卸载真证（弹窗 accept→
engines/formula 删净→未就绪＋安装钮）→三查 0/零 JS 异常/零 HTTP 失败/零 console 错→端口复验闭＋孤儿零。
证据：`docs/handoff/evidence/pp-m-live/`（probe.toml＋shots 01–09＋02b＋server.log）。
前端改动在真浏览器用户路径全程走过（安装/卸载/选席/重认/窄屏皆真人路径点击）。

## 【偏离与欠账】

偏离（探针口径，均登记 probe.toml deviations）：
1. prefs auto_image_seat=cloud_vision（未指派）：无坐标整题兜底走显性失败，避 MinerU 本地 CPU 停跑令；
   公式步真跑不受影响。
2. 原串批次经自动分流默认公式座（PP-M 未装）显性标待核产出、先于安装跑——引擎下拉只列就绪且启用座
   （ui_intake applyRegistry），未装座无从直选；run2 选 ai 超时即此因。
3. 探针判据修实：数 $ 不算回填实证（scan_text 归一自带 $），改按路由注记「N 道原位回填」。

欠账（照挂不硬闯）：
1. 跨行公式 span D12 匹配不上（微批第 5 块量子存储题，span 跨行、题面是多个单行 $ 片段）——
   已知局限，判据 ≥3 满足（4/5）；改进归 D 卡/后续。
2. combo_pp_m 条目 D 卡文案陈旧（按令不动，登记待 D 卡）。
3. 其余五座（PP-L/P2T-MFR/Texify/书生/面壁）安装＋推理＋擂台全留 D 卡；默认座口径不变。
4. MinerU/VLM CPU 耗时证据奉停跑令未跑（既有欠账照挂）。
5. 两仓 push 奉令 hold，待主公授权。
6. 存量缺陷两笔（8ac177f/9843f53 题库引擎首启竞态）非本卡引入，卡「零 HTTP 失败」判据驱动修实，
   只影响空库首启并发场景；旧库（已是 WAL）不受影响。
7. run1–run5 红史：run1 微批选题错（combo 已回填题）＋375px 席名溢出＋卸载入口隐藏→CSS/探针修实；
   run2 选 ai 不存在→原串批次前置；run3 D12 归一缺口→bec8870；run4/run5 首启竞态→8ac177f/9843f53；
   run6 全绿收口。原始现场留 .system_generated/pp-m-live/run1–run5（不入 commit）。

需主公点：push 授权（两仓）；D 卡擂台与其余五座开工令。
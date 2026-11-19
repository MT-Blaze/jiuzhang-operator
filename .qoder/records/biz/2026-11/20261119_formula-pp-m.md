# 公式专科 PP-FormulaNet·M 单座安装与推理接线

状态：已发布（本地封版 2.22.0，两仓 push 奉令 hold）
发起日期：2026-11-19
需求来源：主公 2026-11-19 点头「PP-FormulaNet·M（公式专科）先把这个写了，其他的先不动」＋《公式专科PP-M单座接线任务卡.md》（中央枢纽 4a0d74c0 委派，执行会话 54c57168）
基线：底座 33161f6 ／ 插件 87e1729（2.21.0）；交付版本 2.22.0

## [REQ] 2026-11-19

背景：T6 卡（2.19.0）已立七链路单道与审核重认，专科三族当时只登记 blocked「下一卡开」。
主公拍板先做 PP-M 单座：一键安装＋公式裁图推理＋重认/组合路真跑，其余五座与擂台不动。

验收标准（卡§1–§6）：
- 侦查先行：许可证白名单（Apache/MIT/BSD/ISC）、国内源可达＋sha256 登记、优先官方 ONNX＋
  底座现成 onnxruntime 零新依赖；证据落盘再动刀。
- 安装链：engines/formula/ 隔离不碰底座；确认弹窗成本活字；卸载确认；catalog 只改 PP-M 一条。
- 推理：dispatch 接 PP-M；输出过记号标准字典闭集清洗；重认公式块原位替换（D12 不裸拼）；
  combo_pp_m 文字卷公式步真跑；纯图卷显性拒绝；失败显性进失败账本；未安装显性引导；默认座口径不变。
- 真测：Playwright 隔离副本（git archive HEAD）安装点击真证＋微批 3–5＋组合一卷＋三态截图＋
  375px＋零 JS/零 HTTP＋端口闭＋孤儿零；MinerU/VLM CPU 停跑令；65496 零接触；出网必须界面点击。
- 2.22.0 四处 parity＋双建同哈希＋包自检（models/ 不入包）；定向单测＋快门禁＋三查；两仓不 push。

## [PLAN] 2026-11-19

- 权重源：PaddleX 官方 ONNX（pp_formulanet_plus_m.onnx 594MB＋inference.yml 2.2MB），国内镜像
  mirrors.race 复用 ocr_setup 先例；被否：HF 直连（404/不稳）、gitcode 假可达（侦查识破）。
- 运行栈：底座现成 onnxruntime CPU，零新依赖（侦查实测 0.76–1.20s/块，秒级放行）；
  被否：独立 venv/Paddle 全家桶（重且慢，违「零新依赖优先」）。
- 解码：yml 内嵌 BPE（vocab 50000，eos=</s> id2）图内自回归贪心 max 2560；ByteLevel 拼字节＋
  \text{中文}解包＋空白压缩三规则（保护占位 XXXXXXX）；出口 latex_norm.clean 闭集清洗。
- 探针隔离：git archive 两仓 HEAD＋cwd 副本（PROJECT_ROOT __file__ 锚）＋动态端口随机令牌；
  prefs auto_image_seat=cloud_vision（未指派）避 MinerU CPU 停跑令——无坐标兜底显性失败零引擎。
- 被否方案：探针直选未就绪云座产原串批次——下拉只列就绪且启用座（applyRegistry），未装座无从直选；
  改自动分流默认公式座闸口产出（先于安装跑）。

## [DESIGN] 2026-11-19

- formula_setup.py：WEIGHT_FILES 双件（bytes,sha256）常量；engine_dir()=PROJECT_ROOT/engines/formula；
  weights_ready() 双件逐字校验；install/status/uninstall 三口子复用 ocr_setup 状态机。
- formula_pp_m.py：_session() 锁内懒加载，weights_ready False→RuntimeError 显性引导；
  recognize(png)→{ok,latex,detail}；预处理 crop_margin→短边384→thumbnail→居中补黑→
  (x/255−0.7931)/0.1738；解码 eos 截断→特词跳→ByteLevel→\text 解包→空白压缩→latex_norm.clean。
- catalog PP-M 一条：rule=weight_present、store=formula、plan_recognize=[formula_pp_m]、
  degraded_action=install_formula；[auto] text_formula_seat=formula_pp_m 沿用 T6 不动。
- dispatch formula_pp_m 步直通引擎；reidentify 整题选 PP-M 显性拒绝（只认裁图）；
  replace_fragment D12：原串匹配→已知 LaTeX 匹配→（本次新增）文字层归一题面按 _run_to_latex
  同规则推已知片段；不裸拼口径不变。
- 题库引擎首启竞态修：dao_base._BUILD_LOCK 双检串行懒建库＋_build_into 建库期预设 WAL。
- build_plugin DENY_NAMES 补 model_prefs.toml（carried 运行时财产不随包发行）。

## [IMPL] 2026-11-19

底座仓六笔＋收口笔：71088de（侦查 docs）→5350ebd（安装链＋引擎适配器＋registry/API/relay）→
488f6d5（dispatch/重认/combo 接线＋8 用例）→bec8870（D12 文字层归一匹配＋3 用例）→
8ac177f（懒建库锁＋并发用例）→9843f53（建库期 WAL＋断言）→收口笔（build_plugin 契约修＋2 用例、
pp_m_live_probe.py 448 行、plugins.toml sync、test_29 基线 2.22.0、回单＋证据＋本记录）。
插件仓（MT-Blaze 瞬态身份，绝不写 git config）：635ccef（catalog 单条＋UI formula 工种）→
66591d1（席名窄屏换行一行）→收口笔（plugin.toml/plugins.json/zip 2.22.0）。
使用 skill：sync-biz-record（本记录）；动线参照 add-host-api/build-release/prove-visual-change/run-regression。
涉及文件清单与行数详见回单 `docs/handoff/receipts/formula-pp-m.md`。

## [VERIFY] 2026-11-19

- 定向 17 模块 575/575 绿（.venv\Scripts\python.exe -m unittest 逐模块，禁 pytest/discover）：
  formula_route 32／reidentify 25／models_registry 67／model_prefs 15／auto_split 9／
  command_registry 35／layout_models 22／latex_norm 37／clean_latex 13／latex_style_dict 30／
  editor_contract 174／plugin_suite 11／workspace_pure_release 10／bank_engine_v2 24／
  bank_api 51／bank_dashboard 6／bank_provider 14。
- 快门禁 PASS（6 项，23 份体积预警原班无新增）；JS node --check 153/153；三查 0/0/0。
- 真机探针 run6 全绿 32/32（450.2s，隔离副本 operator 9843f53／plugins 66591d1，端口 14261）：
  安装真证（596MB 弹窗 accept→界面点击 POST→done→双件 sha256 逐字一致）；combo_pp_m 14 道裁图
  14 道原位回填；重认微批 5 块 4 块原位替换（第 5 块跨行 span 已知局限）；整题选 PP-M 显性拒绝；
  卸载删净回未就绪；375px 三处 overflow 0；零 JS/零 HTTP/零 console；端口闭＋孤儿零。
  证据 docs/handoff/evidence/pp-m-live/（probe.toml＋10 截图＋server.log）。
- 红线检查：两仓不 push；65496 零接触；MinerU/VLM CPU 停跑令未违；出网皆界面点击（安装/卸载）；
  其余五座 catalog 一字不动（diff 87e1729..HEAD 验证）；LICENSE/铁律一二/question_contract/用户 data/ 未动；
  tools/onnx_probe.py＋plugins models/＋model_prefs.toml 原地未 stage；engines 产物未 stage；
  禁 JSON 落盘（toml/md）；stage 点名；不 amend；records append-only。
- run1–run5 红史与修实：选题错/席名溢出/卸载入口（run1）→选 ai 不存在（run2）→D12 归一缺口（run3）
  →首启懒建库竞态（run4）→WAL 切换争锁（run5）→run6 全绿。

## [RELEASE] 2026-11-19

- 交付 2.22.0：四处 parity 一致（plugin.toml/plugins.json/主仓 plugins.toml/包内），
  sync_plugin_index rc0 远端语义一致；min_host_version 1.0.0（底座 1.2.0 满足）。
- zip 双建同哈希 23de1670ac4b63a94564cf6a3f2a2388649311742f6ce7d5863f9a789e487209（333921B/326.1KB，
  90 条目）；包自检违禁零（models/、model_prefs.toml、权重后缀全排除）；LICENSE Apache-2.0 202 行。
- 两仓 commit 不 push（奉令 hold）；push 授权与 D 卡擂台/其余五座开工令待主公点。
- 回单 #PP-M-01：docs/handoff/receipts/formula-pp-m.md（五项齐）。
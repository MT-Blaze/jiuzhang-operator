# 回传单 · T6 转码七链路路由与审核重认卡

【回执编号】 #T6-01
【回执时间】 2026-11-19T11:00:31+08:00
【实际耗时】 6 小时 56 分（会话转录创建 04:03:46 → 收口读数 11:00:31，系统钟实测；含多轮探针真机逐题填充等待）
【执行结果】 部分成功（奉主公 2026-11-19 ~10:57 明令停跑收口，不再重跑探针/20 题整批）：定向单测 16 模块 296/296 绿、快门禁 6 项 PASS、索引 parity PASS、JS 61/61、zip 双仓哈希一致 a37a4ce9…；两仓 commit 不 push（底座施工 46fcdbc＋本 docs 笔／插件 54aadc3 MT-Blaze 瞬态身份）。已绿面：auto 按卷型分流（纯图→mineru_local／文字→组合路）、公式待核显性、本地 VLM 座装成＋显存门披露、审核重认三席显性＋整题真回填、375px 双视图 overflow=0、键盘 prefs/焦点还原、失败清单 UI、三查 0/零 JS 异常/零 HTTP 失败、收口端口闭＋孤儿零。欠账：20 题整批回填绿证未留存、本地 VLM 视觉真测缺（显存门 blocked）、公式 bbox 整批活验缺（只 repro 侦查＋单测）、云 VLM 真回填缺（无账号）——详见【欠账清单】。

正文逐条对齐卡§0–§7 与不动面；biz 记录
`.qoder/records/biz/2026-11/20261119_t6-route.md`；
基线：底座 b00f77d ／ 插件 a8c800e（2.18.0），坐在其上施工，不卷动、不 amend、不 push。
交付版本 2.19.0（四处 parity 一致）。

## 卡§0 拍板口径复述（逐字生效）

七链路＝整题直转 4 条（MinerU 本地［B 卡已接］／MinerU 云［既有］／本地 VLM［本卡］／
云 VLM［既有 cloud_vision］）＋组合路 3 条（仅文字卷：文字直取正文＋公式按坐标裁图送
专科／本地 VLM／云 VLM）。文字直取是半条路，必须搭伙；正则只是清洁工，不是流派。
自动＝按卷类型分流＋擂台定默认，不挨个试：有文字层→组合路；纯图→默认整题座
（初值 MinerU 本地）。默认哪条由 D 擂台实测定、老师可改；失败显性不偷换。
公式精修＝审核界面老师手动点选重认，不后台自动三级瀑布。
钱/时间排序＝先免费后花钱、免费里先快后慢；专科＝免费快 CPU 可；本地 VLM＝免费慢吃卡；
云 VLM＝花小钱快。选择权在老师：每座大白话定位说明，不排名不替选。
专科三族（PP-FormulaNet_plus M/L／Pix2Text-MFR／Texify）安装＋推理＋擂台同在 D 卡；
本卡专科座＝catalog 登记＋三态 blocked＋重认席可见但选中显性「专科推理通道下一卡开」，
不造假按钮。

## 【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator，23 改＋14 新＝37 文件，施工笔 46fcdbc；biz＋本回单另走 docs 笔）

新增模块（行数均守红线：引擎≤400、新模块≤450）：
- `app/core/ingest/recognize/formula.py`（387）——组合路公式裁图分派＋坐标侦查
  （pypdfium2 文字层 charbox／MinerU middle_json bbox）＋crop_png 按归一化坐标从同张题图
  裁块＋replace_fragment 原位替换（D12 不裸拼）＋mark_pending 待核标记。
- `app/core/ingest/recognize/reidentify.py`（182）——审核重认：选席→裁块/整题→送席→
  原位替换→save_back 来源 review.reidentify；失败进批次失败清单 retryable；
  专科 blocked 选中显性「下一卡开」；list_spans 只读坐标清单。
- `app/core/ingest/recognize/vlm_local.py`（168）——整题/公式图→OpenAI 兼容
  chat completions（image base64）→Markdown+LaTeX，提示词钉题目契约（行内 $...$、
  独立 $$...$$）；单题 900s；失败显性。
- `app/core/ingest/recognize/vlm_service.py`（190）——懒起 llama-server：动态端口／
  随机令牌／健康轮询／并发锁／杀树＋端口复验／lifespan shutdown，镜像 mineru_service。
- `app/core/ingest/vlm_setup.py`（276）——engines/vlm 独立 venv 装 llama-cpp-python
  （国内镜像点击发起，不装 torch）＋GGUF Qwen2.5-VL-3B-Instruct Q4_K_M＋mmproj
  预取（modelscope）；health 每次现算。
- `app/api/pending_reidentify.py`（60）——重认/坐标清单两端点（add-host-api 动线，
  鉴权＋错误码）。
- `static/js/stage_relay_t6.js`（86）——宿主 relay 白名单扩 pending.reidentify／
  pending.reidentify_spans／models.install_vlm／models.install_status。
- `tools/t6_route_probe.py`（450）——真机探针：隔离副本＋动态端口＋随机令牌，
  六步取证＋VLM 安装加演；预态断言＋杀全清收口＋孤儿零。
- 定向单测 6 份：test_auto_split（215）／test_formula_route（298）／test_reidentify（306）／
  test_vlm_local_run（190）／test_vlm_service（227）／test_vlm_setup（210）。

修改：
- `app/core/ingest/router.py`（242）——auto 语义改按卷型分流：纯图→[auto]image_seat、
  文字→文字直取＋公式裁图送 [auto]text_formula_seat；_AUTO_PLAN 删；具体档「选谁只走谁」
  不变；默认座未就绪显性失败＋人话引导绝不静默换座；公式座失败→该题公式标待核、
  正文保留不整题降级；本地服务不可用措辞修正（显示名不再叠「MinerU本地」）。
- `app/core/ingest/registry.py`——RULES 六→七（vlm_local）；公式四条加 capability="formula"；
  vlm_qwen rule=vlm_local＋install 声明＋文案按事实（6G 起、3B int4、CPU 不可）；
  各座 summary_usage 补免不免费/快慢事实句；[auto] 段默认座。
- `app/core/ingest/model_prefs.py`——新键 auto_image_seat／auto_text_formula_seat，
  落插件 prefs（data/ 全树无 model_prefs.toml）。
- `app/core/ingest/recognize/mineru_local.py`——run 逐题回填写 extensions formula_boxes
  （坐标资产）；语义不改。
- `app/core/ingest/recognize/mineru_service.py`（201）——三处 logger.warning
  （在跑不健康杀旧起新／提前退出／超时杀树，均带 pid＋端口），供探针收口与排障定位。
- `app/core/ingest/recognize/shared.py`——merge_local 等复用资产（语义不改）。
- `app/core/ingest/route.py`、`app/api/models.py`、`app/main.py`——分流字段／install 端点／
  lifespan 挂 vlm_service shutdown。
- `docs/PLUGIN_SPEC.md`——七链路＋重认端点＋install 能力同步。
- `plugins.toml`——2.19.0。
- `static/js/stage.js`（776 冻结不增）／`stage_command.js`（545 冻结不增）／
  `stage_relay_io.js`／`static/workspace.html`——relay 接线（只减不增或新增兄弟）。
- 既有单测更新 8 份：test_recognize_router／test_models_registry／test_model_prefs／
  test_ingest_routing／test_ingest_triage／test_command_registry／test_ai_plugin_boundary／
  test_mineru_local_run（＋EquationBoxesTest 3 例）；test_mineru_service 仅复跑未改。

### 插件仓（E:\jiuzhang\jiuzhang-plugins，10 改＋2 新，commit 瞬态身份 MT-Blaze）

- 新增 `dist/ui_reidentify.js`（255）——审核渲染列重认工具行：【整题重认】＋有坐标时
  块级【公式重认（N 块）】；点开＝内联席位选择行（三态照念）；选中送底座原位替换；
  失败成因照念；aria-busy＋按钮锁死；回填复用 replaceField→writeBackSourceText→refreshRow。
  整块下架注释齐备。
- 新增 `dist/panel_reidentify.css`（128）——重认工具行样式；375px 全 flex 容器
  min-width:0/max-width:100%＋seat-name overflow-wrap:anywhere（不横向溢出）。
- 修改 `catalog.toml`——[auto] 段＋公式条 capability="formula"＋vlm_qwen 规则/文案＋
  各座 summary_usage 事实句；不新增座。
- 修改 `dist/index.html`（898 冻结不增）——两行引用 ui_reidentify.js／panel_reidentify.css。
- 修改 `dist/plugin.js`（828 冻结不增）——uiReidentify 创建＋uiColumns deps reidentify 一行。
- 修改 `dist/ui_columns.js`（788 冻结不增）——deps.reidentify＋renderQuestionBlock 末尾
  decorate 钩子。
- 修改 `dist/ui_model_config.js`——「自动分流默认」两下拉（只列就绪座＋自动）＋
  install_vlm 动作按钮（安装本地 VLM/重试安装）。
- 修改 `dist/ui_intake.js`——识别自动档文案＝按卷型分流。
- 修改 `dist/panel_model_config.css`（177）——默认下拉 min-width:0/max-width:100%
  （375px 不溢出）。
- 修改 `plugin.toml`／`plugins.json`——2.19.0。
- 重打 `plugins/org.jiuzhang.editor.zip`——确定性排序 zip，DENY_DIRS models/；
  双建哈希一致 sha256 a37a4ce9f752485b6413795e94f2dc52f384d43264b05fb9b2a79c01f48d8a2c。

不动面核验：切题链全冻结零改；MinerU 本地/云既有通道语义不改；relay 既有方法名/返回形
不变；question_contract.py 禁改未动；T6 之外擂台/bench 全禁未碰。
冻结行数复核：index.html 898／plugin.js 828／ui_columns.js 788／ui_approve.js 454／
stage.js 776／stage_command.js 545／app/api/pending.py 485 均不增。

## 【证据】

### llama-cpp 视觉实测结论

engines/vlm 独立 venv 真点【安装本地 VLM】装成：llama-cpp-python 0.3.36（import 体检
ok=True／state=ready／version=0.3.36），GGUF Q4_K_M 权重 1,929,901,408 字节＋
mmproj-F16 1,338,428,256 字节预取就绪（weights_ready=True）。安装收账 state=done、
message「本地 VLM 已就绪（llama-cpp 0.3.36），GGUF 权重已预取。」
（证据：run1-failed-claim/probe.toml vlm_install／llama_cpp_health／weights_ready＋
shots 安装步骤截图。）
**视觉推理未实测**：本机显存门 blocked（见下），逐题推理通道虽已接线（T6），
但本机不满足 6G 门槛，未起 llama-server 做真图推理→列欠账，不硬闯（卡§3/§7）。

### AMD 显存判定口径

本机 AMD RX 5600 XT 物理 6GB，但 WMI AdapterRAM 读数上限约 4G→hardware.probe
vram_gb=4.0／vram_label=4.0G／vram_source=wmi。vlm_qwen 据 min_vram=6 判 blocked，
low_detail 人话披露全文（已取证）：
「电脑硬件不支持：本机显存 4.0G，本地 VLM 最低 6G 起。请用云端视觉或 MinerU 兜底。
（WMI 的 AdapterRAM 读数上限约 4G，大显存可能被低估；NVIDIA 卡以 nvidia-smi 为准。）」
老师可云兜底，不静默换座（卡§3 AMD 口径）。

### 坐标来源实测

文字层坐标：B-002 文字卷 14 道公式裁图待核实证（pypdfium2 charbox），
formula_spans origin 含文字层；公式裁块 dispatch/replace_fragment/crop_png 单测绿。
repro_formula_crop.py（B-002 文字层坐标裁块→MinerU→原位替换真解析取证）备而未跑
（奉停跑令不再起引擎）→公式裁块真回填整批活验列欠账。
MinerU middle_json.json bbox 坐标源已接线并实测校准：真实结果包含
middle_json.json（output_formats=default 产出），bbox 为归一化 0–1（引擎
normalize_bbox 口径）。**实测发现并修复 type 名 bug**：原 _equation_boxes 只匹配
"type==equation"，而 MinerU 显示公式块实际 type=interline_equation（另有
equation/equation_interline），致显示公式块坐标漏取→已改匹配三型＋单测钉
（test_mineru_local_run EquationBoxesTest 3 例）。B-001 样本（集合/不等式卷）
公式全为行内 equation_inline span（无 bbox，不可裁），MinerU 无显示公式块坐标→
该卷公式裁块走「无坐标只给题级」兜底（设计如此，不猜坐标）；显示公式块裁块
真回填待含显示公式卷样补测（欠账）。

### 分流两卷型注记证据

B-002 文字卷 auto→组合路注记全文（run1-failed-claim/probe.toml txt_route.note）：
「自动分流（文字卷）→组合路：文字直取正文。 公式裁图 14 道交「formula_pp_m」，
0 道原位回填。 14 道题公式标待核（公式座「PP-FormulaNet·M（公式专科）」未就绪
（专科推理通道下一卡开（D 卡：安装＋推理＋擂台同在），本卡只登记说明；重认席可见，
选中会如实提示。）。），正文保留文字直取、不整题降级。 3 道无公式坐标或坏题，
走整题重认兜底并明示。 整题兜底→默认座「MinerU·本地」。」
mode=auto_combo／text_layer=True／stats total=17 bad=3。
B-001 纯图卷 auto→默认整题座 MinerU 本地：分流字段多轮探针 PASS（text_layer=False、
recognize_engine=auto、auto_image_seat=mineru_local、mode=mineru_local），注记
「自动分流（纯图卷）→默认座「MinerU·本地」。」实证。整批回填账：b4fuswog3 轮注记
实证「MinerU本地 解析未全部成功（只有 17/20 道回来了）…3 道保持本地切图」（产品真回填
17 道、失败显性不偷换；该轮探针正则未兼容部分成功格式致 check FAIL，已修）。
**完整 20 题整批绿证未留存于持久证据目录**：多轮 run1 被后续轮 rmtree 覆盖，17/20
仅见于 b4fuswog3 任务输出；b4eflv7sk 轮 IMG_CAP 超时止于 19/20、b7dd0jhva 轮奉令中止
（审计留存 run1-abort-stop-order/）→20 题整批证据列欠账，微批 3–5 题复测归后续卡。

### 重认真回填或显性证据

云 VLM 无账号显性失败（不偷换）：note「席位「云端视觉」未就绪：未指派视觉识别账号。」
（run1-failed-claim shots/reidentify-cloud-fail.png）。
本地 VLM 显存门显性披露：note 含「未就绪」＋「显存」（shots/reidentify-vlm-gate.png）。
MinerU 本地整题重认真回填：b4fuswog3／b4eflv7sk 两轮均 PASS（原位替换 round-trip，
stem_before/after 取证「1. 已知集合 $A = \{x \in \mathrm{N}^{*} \mid -\sqrt{3} \le x
\le \sqrt{3}\}$，则必有（ ）」，shots/reidentify-backfill.png）；重认失败不偷换（批次
路由仍 mineru_local 完成态）多轮 PASS。公式裁块重认真回填：**未整批活验**——B-001 样本
全行内公式（equation_inline 无 bbox）无显示块坐标，走「无坐标只给题级」兜底（多轮 PASS）；
repro_formula_crop.py（B-002 文字层坐标裁块→MinerU→replace_fragment）备而未跑（奉停跑令
不起引擎）；公式裁块 dispatch/replace_fragment/crop_png 单测绿（test_formula_route 24／
test_reidentify 20）→公式 bbox 整批活验列欠账。

### 门禁与单测

定向单测全绿（16 模块 296/296：新增 6 模块 96＋更新 8 模块 176＋复跑 mineru_service 11／
file_size_contract 13；逐模块 .venv unittest）；快门禁 6 项 PASS；索引 parity PASS；
JS 语法 61/61 OK；zip 双建哈希一致 a37a4ce9f752485b6413795e94f2dc52f384d43264b05fb9b2a79c01f48d8a2c。
探针多轮取证（奉令停跑，未取齐 20 题整批绿证）：
- run1-failed-claim（35 checks，claim 竞态 5 FAIL，审计留存）：VLM 真点装成 done、
  AMD 显存门披露全文、B-002 组合路注记全文、云/VLM 席显性失败、键盘 prefs、焦点还原。
- b4fuswog3（40 checks 38 PASS，2 FAIL 皆探针 bug 已修）：整题重认真回填、375px 工具行
  overflow=0、失败清单 UI、收口端口闭＋孤儿零、纯图卷 17/20 真回填注记。
- b4eflv7sk（40 checks 38 PASS，2 FAIL 皆 IMG_CAP 超时伪影已修）：install idle 收账、
  整题重认/375px/失败清单/收口复证。
- b7dd0jhva：奉主公停跑令中止（run1-abort-stop-order/ 留存），杀树端口复验 0＋孤儿零、
  65496 主应用未动。
已过项覆盖：registry 16 条目／auto 默认座 mineru_local+formula_pp_m／专科 blocked＋下一卡开／
VLM 显存门 blocked 人话披露／识别自动档分流文案／两卷各立批次／硬件快照上页／自动分流
默认两下拉（只列就绪座＋自动）／键盘改默认座落插件 prefs＋改回自动沿用 catalog／data/ 全树
无 model_prefs.toml／返回批次焦点还原／375px 配置视图＋重认工具行 overflow=0／文字卷
auto_combo＋组合路注记＋公式待核 14 显性＋文字直取正文非空／纯图卷分流字段／云 VLM 无账号
显性失败不偷换／本地 VLM 显存门显性披露／整题重认真回填／无坐标只给题级／失败清单 UI 可见／
三查 fetch(/parent.document/localStorage=0／页面零 JS 异常／UI 阶段零 HTTP 失败／收口端口闭＋孤儿零。

## 【欠账清单】

1. 本地 VLM 视觉推理未实测：本机 WMI 显存 4.0G＜6G 门槛 blocked，llama-server 逐题
   真图推理未跑（装成＋import 体检过、通道已接线）。须在大显存机（≥6G，NVIDIA 以
   nvidia-smi 为准）或云端补测；卡§7 停链规则＝gate_note 显性＋欠账，其余面绿即成功。
2. 云 VLM 真回填未实测：本机无视觉识别账号，只取显性失败证据；须指派账号后补测。
3. 专科三族（PP-FormulaNet_plus M/L／Pix2Text-MFR／Texify）安装＋推理＋擂台＝D 卡，
   本卡只 catalog 登记＋blocked＋重认席可见选中显性「下一卡开」。
4. MinerU claim 竞态：run1 首轮曾现孤儿树持锁致后续启动 claim-failed（已杀清＋
   warning 日志 instrumentation＋探针预态断言＋杀全清收口）；后续三轮（b4fuswog3/
   b4eflv7sk/b7dd0jhva）预态干净、收口孤儿零、未再现竞态；停跑收口复验 25228 端口闭、
   引擎/探针孤儿零、65496 主应用未动。
5. 公式裁块显示公式块真回填：B-001 样本全行内公式（equation_inline 无 bbox），
   MinerU 显示公式块（interline_equation）裁块真回填待含显示公式卷样补测；
   文字层坐标裁块真解析取证脚本 repro_formula_crop.py 备而未跑（停跑令）；
   type 修复已单测钉（EquationBoxesTest 3 例）、dispatch/replace 单测绿。
6. 20 题整批回填绿证缺（主公明令停跑、不再跑 20 题整批）：b4fuswog3 轮产品真回填
   17/20 仅见任务输出、持久 run1 数据被后续轮覆盖；微批 3–5 题复测归后续卡，本卡不做。

## 【偏离记录】（偏离卡面记回单不静默）

1. 决策台账§9/§10/§11 不存在→以卡§0 拍板口径为准。
2. llama_cpp.server fork 缺失→engines/vlm 独立 venv（不复用 mineru venv，不装 torch）。
3. GGUF 源用 ModelScope unsloth 仓（国内镜像点击发起）；llama-cpp-python 用 abetlen CPU 轮。
4. MinerU 坐标源用 middle_json.json bbox（非卡面举例 middle.json，引擎实际产物名）。
5. 重认端点住新兄弟 app/api/pending_reidentify.py（pending.py 485 冻结不增）；
   新增 pending.reidentify_spans 只读端点（add-host-api 动线）。
6. test_ai_plugin_boundary 切片边界修正、test_ingest_triage 阈值测试改分流语义
   （auto 不再挨个试，旧瀑布断言随之更新）。
7. B-001 样本不在 test_papers/manifest→用 A2 取证留存同卷副本（沿 B 卡口径）。
8. 席位未就绪类重认失败只进 UI 显性提示（未动引擎）；识别/替换/存回失败才进失败清单
   （单测已钉）——与卡§4「失败进失败清单」的边界澄清。
9. 旧瀑布文案 6 处修正（auto 语义改分流后残留措辞）。
10. mineru_service 三处 warning 日志＋router 本地服务不可用措辞修正（排障定位＋显示名）。
11. 两处 375px CSS 修复（panel_model_config.css 默认下拉／panel_reidentify.css 工具行）。
12. 探针加固：预态断言＋杀全清收口＋VLM 已装复验路径＋TXT_CAP 排队宽限（单并发服务
    两卷交错）＋公式裁块重认先于整题（整题经 merge_local 丢 formula_boxes，坐标证据须先取）。
13. run1 三轮中断审计留存：run1-failed-claim（claim 竞态 5 FAIL）／
    run1-abort-vlm-install（已装态误点 install 中止）／run1-abort-txtcap（TXT_CAP 时序缺陷中止）。
14. _equation_boxes type 名修复：实测 MinerU 显示公式块 type=interline_equation
    （非 equation），原只匹配 equation 漏取坐标→改匹配 equation/interline_equation/
    equation_interline 三型＋EquationBoxesTest 3 例钉；行内 equation_inline 无 bbox 不裁（不猜）。
15. 探针两处自纠：已装态 install_status=idle（无安装作业）收账改「done 或已装 idle」
    并即断轮询（省 40 分钟空转）；纯图卷部分成功注记「只有 X/Y 道回来了」与全成功
    「X/Y 道回填成功」双格式正则兼容（17/20 真回填得以计账）。
16. 探针填充宽限再校准：idle 即断去掉前轮意外 40 分钟 head start 后，IMG_CAP 须覆盖
    完整逐题填充（单并发约 300s/题×20≈6000s+）→IMG_CAP 4800→7200、TXT_CAP 2400→3600；
    wait_done 就绪即返，宽限只防 premature timeout 不拖慢 happy path。
17. 奉主公 2026-11-19 ~10:57 明令停跑收口：杀 b7dd0jhva 探针进程树＋隔离服务（端口
    25228 复验闭、孤儿零、65496 未动），不再重跑探针/20 题整批；按现状（单测＋门禁绿）
    收口 commit，执行结果定为部分成功，整批/视觉/公式 bbox 活验缺证逐条列欠账；
    微批 3–5 题复测归后续卡。run1 中止审计留存 run1-abort-stop-order/。

## 【需拍板】

1. 本地 VLM 视觉补测机：是否安排≥6G 显存机（或云）跑真图推理收欠账 1。
2. 云 VLM 账号：是否指派视觉识别账号补欠账 2 真回填。
3. D 卡擂台默认座：auto 默认座初值 MinerU 本地／formula_pp_m 待 D 擂台实测后老师可改，
   本卡只落初值＋两下拉。
4. 微批 3–5 题复测归后续卡（主公明令本卡不做）：20 题整批回填绿证（欠账 6）与公式裁块
   显示公式真回填（欠账 5）改用 3–5 题微批在后续卡活验，是否单开一张微批复测卡承接。
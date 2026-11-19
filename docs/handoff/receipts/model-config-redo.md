# 回传单 · 模型配置中心重做＋重新识别＋安装链修实卡（2.20.0）

【回执编号】 #MCR-01
【回执时间】 2026-11-19T15:31:05+08:00
【实际耗时】 约 3 小时 18 分（执行会话 0424f554 转录创建 12:12:57 → 收口读数 15:31:05，系统钟实测；含多轮探针真机安装/下载/GPU 逐题等待与两次上下文压缩接力）
【执行结果】 成功（卡§0–§8 全范围落地；真测腿按卡面口径完成：VLM 小题图 3 题产品路径 GPU 秒级＋OCR 3 样本 bench；MinerU 本地 CPU 逐题填充奉停跑令未跑，归验收）

正文逐条对齐卡§0–§9 与不动面；biz 记录见 `.qoder/records/biz/2026-11/`（sync-biz-record append）。
基线：底座 `5195d28` ／ 插件 `54aadc3`（2.19.0），坐在其上施工，不卷动、不 amend、**两仓均不 push（hold）**。
交付版本 **2.20.0**（四处 parity 一致）。

## 卡§0 拍板口径复述（逐字生效）

重做＝模型配置中心一页，**API 配置页不动**。四栏表（名称/简要/状态/操作）按工种分组
（切题定位/整题转写/公式专科），自动分流默认组置顶；硬件检测只在点进配置中心那一刻跑
（启动下拉 probe=0 复用快照）；微批 3–5 题；**MinerU 本地 CPU 逐题填充任何探针禁跑（停跑令）**。
本卡真测＝VLM 小题图 3 题产品路径 GPU 秒级＋OCR 3 样本 bench。**出网必须界面点击发起**。
【重新识别】住批次行（删除旁）：确认弹窗摆明账→整批打回文件收集框（源文件＋元数据原样）→
识别下拉选链路（7 链路＋自动；组合路对纯图卷灰＋人话原因）→只跑一条；未入库随批作废、
已入库留库不动；跨库查重已证存在→不补刀记回单。

## 【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator，基线 5195d28 → 375f4f7，45 文件）

施工笔（每大阶段一笔，不 push）：
- `3338b1a` §3 注册表 64 位显存刀
- `0148dcd` §4+§7 安装链修实＋多镜像测速选路
- `dc60386` §1/§5 配置页重做后端＋探针
- `7e9d103` §6 名单六→三＋Pix2Text 改名＋准档解锁
- `cdd7817` §2 整批打回重新识别（18 文件）
- `c4d6b16` 真测修实三 bug＋两条真测探针（6 文件）
- `8b6f8e2` 主仓索引 parity 2.20.0
- `ea11dd8` 命令面手册字典期望版随升（test_29 夹具）
- `375f4f7` vlm_setup 压回引擎≤400（418→400，纯排版）
- 本回单＋biz 另走 docs 笔

新增（点名）：
- `app/core/ingest/mirrors.py`（66）：pip 四家/权重三源点击内并行测速选路＋pick_note 人话
- `app/core/ingest/ocr_setup.py`（188）：准档两件 medium 权重一键装（三源测速、按件重解析链接、
  同源重试一次、sha256 逐件校验、原子改名、卸载先丢引擎缓存）
- `app/core/pending/return_batch.py`（69）：整批打回（原卷字节先读后删＋元数据/text_layer 原样交回）
- `app/api/pending_return.py`：打回 HTTP 口子（鉴权＋形状校验，404/400 分域）
- `tools/vlm_micro_probe.py`（340）/`tools/ocr_install_probe.py`/`tools/ocr_medium_bench.py`（100）/
  `tools/return_batch_probe.py`（372）/`tools/recon_2200.py`（92）
- `tests/test_mirrors.py`/`test_ocr_setup.py`/`test_return_batch.py`＋既有模块增例
- `docs/handoff/evidence/2200-recon/`（recon.md/toml/txt 侦查证据）

修改（点名带函数）：
- `app/core/ingest/registry.py`：64 位显存读取（WMI 低估如实披露）＋weight_present 准档三态＋
  vlm 徽章/简要活字现算（未安装/已安装·就绪(Vulkan)/显存不足·CPU 慢兜底）
- `app/core/ingest/hardware.py`：probe 现测口径
- `app/core/ingest/vlm_setup.py`（276→400）：改包 mineru-llama-cpp==0.2.3（Vulkan 真发动机）、
  pip 四家测速、全败离线迁移 engines/mineru 栈（_migrate_engine）、GGUF 三源预取、体检现算
- `app/core/ingest/recognize/vlm_service.py`：动态空闲端口起 llama-server（-ngl 999 Vulkan）、
  stop() taskkill /PID /T 树杀
- `app/core/ingest/recognize/ocr.py`（283）：detect 加 tier 参（**small 行为逐字不变**）＋
  medium 分支 ModelType.MEDIUM（钉版 rapidocr 只认 Enum）
- `app/core/ingest/recognize/router.py`：ocr_medium 步骤＋组合路三席
- `app/core/ingest/recognize/reidentify.py`/`formula.py`：重认拒组合路显性
- `app/core/ingest/service.py`（**恰 400**）：_image_shell 图 id 改 `img_` 前缀过契约＋
  PNG 壳→fill_scan_batch；stage_ingest 收打回元数据原样落新批
- `app/core/ingest/mineru_setup.py`/`layout/router.py`：安装链接入测速选路（语义不改）
- `app/api/models.py`：vlm/ocr 安装·状态·三卸载口子（写令牌）
- `app/main.py`：lifespan shutdown 调 vlm_service.stop
- `static/js/stage_command.js`（**545 持线**）：RELAY_METHODS 白名单原地补
  models.vlm_install/vlm_status/ocr_install/ocr_status/uninstall_vlm/uninstall_mineru/uninstall_ocr/
  pending.reidentify/reidentify_spans/return_batch（:65 一行，行数不增）
- `static/js/stage_relay_bank.js`/`stage_relay_io.js`/`stage_relay_t6.js`/`intake.js`：原地接线
- `tests/test_command_registry.py`：test_15b 白名单＋dispatch 字面量回归钉死；test_29 手册期望版随升
- `tools/model_table_probe.py`/`canvas_inline_config_probe.py`：状态自适应（本机已装分支）＋选中器同步
- `plugins.toml`：editor 2.20.0

冻结面台账（行数只减不增，原地接线，收口实测）：
stage_command.js **545**／stage.js **776**／app/api/pending.py **485**（持基线）。
引擎≤400：service.py **400**／vlm_setup.py **400**／ocr_setup.py 188／return_batch.py 69。
分层≤3：新模块全在既有 app/core/ingest/、app/core/pending/、app/api/ 层内，无新层。

禁改区自查：LICENSE 未动；docs/agents.md 铁律一二未动；app/core/question_contract.py 未动；
用户 data/ 未动（探针全走隔离副本）；API 配置页未动；tools/onnx_probe.py 保持 untracked 未 stage；
engines/ 产物未 stage；禁 JSON 落盘（状态全 TOML/内存）。

### 插件仓（E:\jiuzhang\jiuzhang-plugins，基线 54aadc3 → af7884d，14 文件，MT-Blaze 瞬态身份）

施工笔：`d1df4f4`（§1/§5）→ `73b08c8`（§6）→ `cc23f8f`（§2，9 文件）→ `af7884d`（parity）。

新增兄弟（整块下架：删 index.html 两行引用＋对应文件即可）：
- `dist/ui_model_table.js`（212）＋`dist/ui_model_install.js`（141）＋`dist/panel_model_table.css`（185）
- `dist/ui_batch_return.js`（116）＋`dist/panel_batch_return.css`（36）

修改：`dist/ui_model_config.js`（编排 **341≤450**）／`dist/ui_intake.js`／`dist/ui_reidentify.js`／
`dist/index.html`（**898 持线**）／`dist/plugin.js`（**828 持线**）／`dist/ui_columns.js`（**788 持线**）／
`dist/ui_approve.js`（**454 持线**）／`dist/ui_batches.js`（**780 持线**，【重新识别】住删除旁）／
`catalog.toml`（VLM 六→三＋Pix2Text·MFR 改名＋准档座＋组合路三席）／`plugin.toml`（2.20.0）／
`plugins.json`（2.20.0＋changelog）／`plugins/org.jiuzhang.editor.zip`（重打）。
`src/org.jiuzhang.editor/models/` 保持 untracked 未 stage（卡面点名不碰）。

## 【包结构自检】

`tools/build_plugin.py` 实跑产出（`.system_generated/zip-parity/build1|build2/`）：
- 顶层目录名 == `org.jiuzhang.editor` == plugin.toml id ✓
- 无 `backend` 字段 ✓；Apache-2.0 `LICENSE` 全文在包内 ✓
- `models/` 未入包（排除校验 True）✓；无 .db/.zip/.pyc/dev/ ✓
- `min_host_version = "1.0.0"` ≤ 当前底座 `1.2.0`（app/__init__.py:8 单源）✓；无 [engine] 节
- **zip 确定性双建哈希一致**：
  `2ca17477bc9a6e444bd2f2516e42685cace7798ab23f3effc6e5f69ab354c954`（build1 == build2，
  落 plugins/org.jiuzhang.editor.zip 同哈希）
- **四处 parity 2.20.0**：插件 plugin.toml:4 ／ plugins.json:68 ／ 主仓 plugins.toml:51 ／
  包内 plugin.toml；`tools/sync_plugin_index.py` rc=0「远端索引一致」
- 版本一致性 `tests.test_version_consistency` 29/29 绿

## 【三查结果】

`bash scripts/check-plugin-boundary.sh` 当次实跑：
- 插件侧 `fetch(` 命中 **0** ✓
- 插件侧 `parent.document` 命中 **0** ✓
- 插件侧 `localStorage` 命中 **0** ✓
- 插件源码零 Python ✓；宿主侧 static/js 带 fetch( 文件 17（出网全由界面点击发起，探针
  install_requests/uninstall_requests 全程空数组实证 dismiss 零出网）
- 请求 id 全合规 `^[A-Za-z0-9_-]{1,80}$` 不含点号（test_command_registry 35/35 钉死）

## 【测试与探针】

解释器一律 `.venv/Scripts/python.exe -m unittest tests.<模块>`（逐模块，禁 pytest/discover）。

### 定向单测（收口当次复跑，13 模块 307/307 绿）

| 模块 | N/N |
|---|---|
| test_command_registry | 35/35 |
| test_ingest_hardware | 15/15 |
| test_ingest_triage | 21/21 |
| test_mineru_setup | 19/19 |
| test_mirrors | 6/6 |
| test_models_registry | 66/66 |
| test_ocr_setup | 15/15 |
| test_recognize_router | 24/24 |
| test_reidentify | 22/22 |
| test_return_batch | 15/15 |
| test_vlm_service | 13/13 |
| test_vlm_setup | 27/27 |
| test_version_consistency | 29/29 |

压线刀后复验 test_vlm_setup＋test_models_registry＋test_vlm_service 106/106 绿。
快门禁 `bash scripts/check-quick-gate.sh` **PASS（6 项全过）**（23 份 451–550 _warn_ 台账系基线
既有排队拆项，本卡未新增 warn；冻结面全持线）。JS 语法全量 **139/139 OK**
（static/js 全量＋editor dist 全量，tools/js_syntax_check.py）。

### 真机探针（Playwright 穿沙箱，隔离副本＋动态端口＋随机令牌，收口点杀＋端口复验）

| 探针 | 绿轮 | 判据 | 证据路径 |
|---|---|---|---|
| 侦查 recon_2200 | — | 冻结面/源可达/查重语义 | docs/handoff/evidence/2200-recon/ |
| model_table_probe | run2 | **35/35** | .system_generated/model-table/run2/probe.toml＋shots |
| return_batch_probe | run3 | **27/27** | .system_generated/return-batch/run3/probe.toml＋shots 01–03 |
| vlm_micro_probe | run3 | **13/13** | .system_generated/vlm-micro/run3/probe.toml＋shots 01–03 |
| ocr_install_probe | run4 | **7/7** | .system_generated/ocr-install/run4/probe.toml＋shot 01 |

浏览器真人路径（工具经 CDP 发真实输入事件）走过：点进配置中心那一刻 probe=1 真测、
四栏表/三工种/默认组置顶、点名称出详情先简要再点开、键盘 Enter 展开收起＋焦点还原、
375px 零横溢＋窄屏详情内联行下、安装/卸载确认弹窗 dismiss 零出网零删、停用/启用经 relay
落隔离插件目录、批次行【重新识别】→确认摆账→打回收集框（元数据挂身）→纯图卷组合路灰＋
人话 title→选链路再入库、aria-busy＋disabled。零 JS 异常/零 HTTP 失败/三查 0/收口端口闭。

### 卡§0 真测腿（产品路径，出网全由界面点击发起）

**VLM 小题图 3 题 GPU 秒级**（vlm_micro_probe）：
- run1＝安装点击实证：真点【安装】→3.3GB 确认弹窗 accept→`/api/models/vlm/install` 真请求→
  pip 测速选源→Vulkan 发动机落地（engines/vlm/llama-bin 迁移栈）→GGUF 两件预取 sha 校验。
  该轮 14/15（孤儿收口 FAIL，见偏离⑤）；逐题累计墙 36.6/41.6/45.7s（首题含起服＋模型加载）。
- run3＝**13/13 绿**：engine=vulkan；逐题累计墙 **13.2/18.4/22.4s**（稳态增量 13.2/5.2/4.0s，
  即首题含加载 ~13s、后续 **~4–5s/题**）；3 题文档非占位（含真实解方程文本）；
  CTRL_BREAK 优雅收口＋**llama-server 零孤儿**（before=[] orphans=[]）。

**OCR 3 样本 bench**（ocr_install_probe＋ocr_medium_bench）：
- run3＝安装点击实证：真点【安装】→139MB 确认弹窗 accept→`/api/models/ocr/install` 真请求→
  两件 medium 权重落地（det 62119454＋rec 76629984 字节，sha256 逐件校验通过）。
  该轮 ok=false 系 bench 撞 Enum bug（见偏离③），修后 run4 复绿。
- run4＝**7/7 绿**（权重已在＝安装跳过分支，徽章就绪＋bench 真跑）。
- bench 事实（`.system_generated/ocr-medium-bench/bench.toml`，各卷第 1 页，CPU，只摆事实不排座）：

| 样本 | 快 small（rows/均分/链分/秒） | 准 medium（rows/均分/链分/秒） |
|---|---|---|
| 东北师大附中月考 | 68 / 0.9574 / 8 / 5.81 | 71 / 0.9613 / 8 / 80.83 |
| 一中期末 | 72 / 0.915 / 5 / 5.15 | 89 / 0.9013 / 5 / 84.65 |
| 蜜蜂试卷期中 | 98 / 0.9535 / 11 / 5.65 | 108 / 0.9553 / 11 / 98.63 |

事实归纳：medium 切题行数更多（+3/+17/+10），均分两升一降，耗时约 14–16×。
**升默认与否待主公点头**，本卡不替选。

## 【未决问题与偏离】

### 偏离（全如实披露，均已修＋回归钉死）

1. **白名单漏项（宿主静默拒发）**：§5/§6 施工时 models.ocr_install/ocr_status/三卸载与
   pending.return_batch 未进 RELAY_METHODS——relay 分支存在但白名单缺＝宿主 UNSUPPORTED_METHOD
   静默拒发（return-batch run1 超时实证）。cdd7817 原地补 :65 一行（545 持线）＋
   test_15b 回归（白名单成员＋stage_source dispatch 字面量双钉）。
2. **准档 rec 收错文件**：测速只探首件（det）链接，sources 复用给 rec 时拿 det URL 下 rec，
   实收 62119454 字节＝det 大小（run2 诊断实证）。c4d6b16 改按件重解析链接
   （`urls = dict(_weight_urls(task, name))`）＋同源重试一次再换家＋实收字节诊断；
   回归 test_each_file_resolves_its_own_url_not_the_raced_one／截断重试例钉死。
3. **钉版 rapidocr model_type 只认 Enum**：字符串 "medium" 被 ParseParams 拒
   （bench TypeError 实证）。改 `ModelType.MEDIUM`（ocr.py medium 分支；small 逐字不变）；
   单测改真 Enum import＋assertIs。
4. **PNG 占位壳图 id 违契约**：pimg_*.png 原样当 images[].id 被 `^img_…` 正则拒，壳落不了池
   识别开不了工（探针实证）。service.py _image_shell 改 `img_` 前缀（400 行持线）；
   test_return_batch.ImageShellReentryTest 钉死落池。
5. **探针收口孤儿**：Windows Popen.terminate()＝TerminateProcess 硬杀，lifespan stop 不跑，
   llama-server 留孤儿（vlm run1 FAIL 实证）。探针收口改 CREATE_NEW_PROCESS_GROUP＋
   CTRL_BREAK_EVENT 优雅停＋20s 等待＋PID 点杀安全网；run3 零孤儿。**产品侧 vlm_service.stop
   仍 taskkill /T 树杀不变**（main.py lifespan 正常停服路径已接）。
6. **vlm_setup 超引擎红线**：本卡重写后 418>400（基线 276），收口自查发现，375f4f7 纯排版
   压回 400（docstring/标记表/多行字典并句），行为零变化，106 测试复绿。
7. **test_29 手册期望版写死**：封版后必红一例（'2.20.0'!='2.19.0'），ea11dd8 夹具随升。
8. **model_table_probe 状态自适应**：真测装成后本机 VLM/准档已装，原「未安装/未就绪」断言
   必红——改按 vlm_setup.health()/ocr_setup.weights_ready() 现状分支（run2 35/35 两态皆覆盖）。
9. **ocr-install run4 系安装跳过分支**：安装点击真证据在 run3（真请求＋弹窗＋权重 sha 落地），
   run3 ok=false 仅因 bench Enum 红（偏离③），run4 权重已在复绿——两轮合并为完整安装链证据。

### 欠账清单（逐条，卡§9 点名）

1. **大图 mtmd ErrorDeviceLost**：Vulkan 后端大图（整页）仍崩，本卡只治小题图路径（3 题绿）；
   大图治法待另卡（继承上一卡欠账，未静默）。
2. **CPU 耗时证据缺（奉令）**：停跑令禁 MinerU 本地 CPU 逐题填充任何探针；VLM 纯 CPU 兜底
   （-ngl 0）耗时亦未真测——本卡 GPU 秒级证据仅 Vulkan 路径，CPU 慢兜底只有文案无数字。
3. **CUDA 专轮国内镜像无货**：mineru-llama-cpp CUDA 轮国内不可达＝显性欠账（安装失败人话
   如实报），本机走 Vulkan 通用轮；N 卡用户 CUDA 加速待源可达。
4. **准档升默认待点头**：bench 事实已备（上表），medium 慢 ~14–16×、均分两升一降，
   切题默认仍是快档 small，升不升由主公拍板。
5. **MinerU 真填充归验收**：奉停跑令本卡未跑 MinerU 本地逐题填充探针；验收时真机抽检。
6. **云 VLM 真回填缺（无账号）**：继承欠账，cloud_vision 链路代码在、真测无账号未跑。

### 需主公点什么

- 两仓 **push 授权**（现 hold：底座 375f4f7＋docs 笔／插件 af7884d，ahead 待推）。
- **准档升默认**点头与否（bench 事实已摆，不替选）。
- 大图 mtmd 治法是否排卡；验收 MinerU 真填充＋真人点抽检。

## 收口复验

- 探针收口端口复验关闭（各 probe.toml「收口端口复验关闭」PASS）；llama-server 零孤儿
  （vlm run3 before=[] orphans=[]）；65496 正式服务全程未碰；用户 data/ 零字节改动。
- 两仓 git status：底座仅 `?? tools/onnx_probe.py`（卡面点名保持 untracked）；
  插件仅 `?? src/org.jiuzhang.editor/models/`（卡面点名保持 untracked）。无未提交施工改动。
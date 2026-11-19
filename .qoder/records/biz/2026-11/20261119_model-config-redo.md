# 模型配置中心重做＋重新识别＋安装链修实（2.20.0）

状态：已发布
发起日期：2026-11-19
需求来源：主公 2026-11-19 点头全范围授权（「OK，你的建议很好，然后你开干吧」）＋《模型配置中心重做与重新识别任务卡.md》
基线：底座 5195d28 ／ 插件 54aadc3（2.19.0）；交付版本 2.20.0（四处 parity）
回单：docs/handoff/receipts/model-config-redo.md #MCR-01

## [REQ] 2026-11-19

背景：配置中心旧面是弹窗长列表，工种不分、硬件检测启动就跑、安装链国内源装不实
（llama-cpp-python 国内只有 sdist 装完纯 CPU）；批次识别错了没有整批打回重来的通道；
VLM 名单六座冗余、准档 OCR 锁死。主公拍板：重做四栏表按工种分组＋自动分流默认组置顶、
硬件只在点进那一刻测、【重新识别】住批次行整批打回文件收集框选链路再入库、
安装链修实（Vulkan 真发动机＋国内镜像测速选路）、VLM 六→三＋准档解锁。
验收：定向单测＋快门禁 6 项＋parity 四处＋zip 双建哈希＋JS 全量；真测＝VLM 小题图 3 题
产品路径 GPU 秒级＋OCR 3 样本 bench；MinerU 本地 CPU 逐题填充奉停跑令禁跑归验收；
出网必须界面点击发起；两仓不 push。

## [IMPL] 2026-11-19

底座 45 文件（3338b1a→375f4f7 九笔）：registry 64 位显存＋活字徽章；mirrors 测速选路；
vlm_setup 改包 mineru-llama-cpp（Vulkan）＋pip 四家＋离线迁移兜底＋GGUF 三源 sha 校验；
ocr_setup 准档两件 medium 权重（按件重解析链接＋同源重试＋sha）；ocr.py tier 参
（small 逐字不变）＋ModelType.MEDIUM；return_batch 整批打回（字节先读后删＋元数据原样）；
service.py _image_shell img_ 前缀过契约（恰 400 行）；stage_command.js 白名单原地补（545 持线）；
vlm_setup 压回 400。插件 14 文件（d1df4f4→af7884d 四笔，MT-Blaze 瞬态身份）：
新兄弟 ui_model_table/ui_model_install/panel_model_table＋ui_batch_return/panel_batch_return
（整块下架）；编排 ui_model_config 341≤450；冻结面八份全持线原地接线；catalog 六→三＋
Pix2Text·MFR＋准档座＋组合路三席。使用 skill：build-release／prove-visual-change／
add-host-api／sync-biz-record。

## [VERIFY] 2026-11-19

定向单测 13 模块 307/307 绿（逐模块 .venv 解释器）；快门禁 PASS 6 项；三查 0/0/0；
JS 139/139；版本一致性 29/29。探针（Playwright 穿沙箱隔离副本）：model-table run2 35/35、
return-batch run3 27/27、vlm-micro run3 13/13、ocr-install run4 7/7。真测腿：VLM 安装
点击实证（run1 真请求＋3.3GB 弹窗）→GPU Vulkan 3 题稳态 ~4–5s/题（run3 累计 13.2/18.4/22.4s）
零孤儿；准档安装点击实证（run3 真请求＋139MB 弹窗＋sha 落地）→bench 3 样本×2 档
（medium rows +3/+17/+10、均分两升一降、耗时 ~14–16×，只摆事实不排座）。
修实三 bug（白名单漏项静默拒发／rec 拿 det 链接收错文件／rapidocr Enum）＋PNG 壳 id＋
探针孤儿收口 CTRL_BREAK，均回归钉死。偏离九条全披露见回单。

## [RELEASE] 2026-11-19

2.20.0 四处 parity（plugin.toml/plugins.json/主仓 plugins.toml/包内）；
sync_plugin_index rc=0 远端一致；zip 确定性双建 sha256
2ca17477bc9a6e444bd2f2516e42685cace7798ab23f3effc6e5f69ab354c954。
两仓 commit 不 push（hold 待主公授权）：底座 375f4f7＋docs 笔／插件 af7884d。
欠账：大图 mtmd ErrorDeviceLost／CPU 耗时证据奉令缺／CUDA 专轮国内无货／
准档升默认待点头／MinerU 真填充归验收／云 VLM 无账号。
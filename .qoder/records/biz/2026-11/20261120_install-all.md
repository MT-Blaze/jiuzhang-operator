# 全模型安装接线（六座：yolo / PP-L / P2T-MFR / Texify / 书生 / 面壁）

状态：已发布（本地封版 editor 2.23.0，两仓 push 奉令 hold；新码新座需主公自重启生效）
发起日期：2026-11-20
需求来源：《全模型安装接线卡.md》（中央枢纽 4a0d74c0 委派，独立执行会话 8058810e，无人值守）
基线：底座 a10e277 ／ 插件 51776cf（2.22.0）；交付版本 editor 2.23.0（host 仍 1.2.0）
回单：docs/handoff/receipts/install-all.md（#INSTALL-ALL-01）

## [REQ] 2026-11-20

背景：T6（2.19.0）立七链路单道，PP-M（2.22.0）开公式专科单座；其余五座 catalog 登记 blocked「下一卡开」。
本卡按串行优先级把六座一次接线：yolo → formula_pp_l → formula_p2t/formula_texify（recon 门：torch 重依赖＝登记跳过，绝不装 torch 进底座）→ vlm_intern/vlm_minicpm（GGUF＋mmproj 复用 engines/vlm llama.cpp Vulkan 栈，T6 推理通道由千问单座泛化多座，大活最后）。已装不动：rapidocr fast/accurate、mineru cloud/local、vlm_qwen、formula_pp_m、cloud_vision。

验收标准（卡§0–§9）：
- 每座独立里程碑，卡了＝登记跳过继续下一座，绝不卡死全链；偏离/跳过全记回单。
- 侦查先行（证据 docs/handoff/evidence/install-all/<seat>/）→安装链→适配器/接线→catalog 只改本座→冒烟 3–5→定向 unittest 逐模块（禁 pytest/discover）＋快门禁＋三查0→不绿不 commit→每座一笔点名 stage 禁 add -A 不 amend。
- 出网隔离副本 UI 真点发起（git archive HEAD＋动态端口随机令牌＋JZO_DATA_DIR/JZO_PLUGINS_DIR 全隔离，禁抄工作树），国内镜像禁 GitHub，sha256 逐件校验。
- 65496 正式服务与暖驻留 llama-server（15024，父 11720）零接触；GPU 独占锁 gpu-seat.lock（查锁＋查显存，活锁等≤60s，锁龄>30min 夺登记，用完删，擂台 fa69fcbf 互让）。
- 微批 3–5；不赌参数；失败显性不偷换不降级；MinerU/VLM CPU 耗时基准停跑令照旧（冒烟非基准）。
- 行数帽沾到≤450 正常 >550 硬停、引擎适配器≤400；LICENSE/铁律一二/question_contract.py/用户 data/ 禁改；records append-only；禁 JSON 落盘（toml/md）；分层≤3。
- 插件有改＝parity 四处＋zip 双建同哈希＋sync rc0，版本按单源自判（六座大改升 2.23.0）；models//model_prefs.toml 不入包不碰；插件 commit 瞬态身份 MT-Blaze 绝不写 git config；两仓不 push。

## [PLAN] 2026-11-20

- yolo：满血档纯 CPU 接线＋下载 sha256 逐字校验（对齐安装铁律）。
- PP-L：formula_setup 泛化 M/L 双变体，薄引擎复用 M 预处理/解码（768 输入），按件装拆互不误删；被否：独立引擎栈（重，复用 M 即可）。
- P2T-MFR：官方 ONNX 三件（encoder/decoder/tokenizer）＋干净房间 TrOCR 引擎（DeiT 384＋无 KV cache 贪心环＋ByteLevel 解码），零新依赖不装 torch；被否：torch 全家桶（违红线）。
- Texify：官方权重仅 .pt 无 ONNX，recon 门早判登记跳过（catalog blocked 文案改实，可后补条件写明）；被否：强装 torch（触底座零 torch 红线）。
- VLM 多座：发动机共享 engines/vlm/、权重按座住 models/、单活座切座先停旧座、按件卸载（各座全空才连发动机目录删）；被否：每座独立发动机（重复占盘、违共享纪律）。
- 发动机安装现实：py3.14 无 mineru-llama-cpp 0.2.3 cp314 轮 → pip 必败 → engines/mineru 离线迁移兜底（真机同款）；隔离副本预置迁移源复现前置（非抄代码、不算出网）。

## [IMPL] 2026-11-20

涉及文件（底座）：app/core/ingest/{vlm_weights,vlm_setup,formula_setup,mirrors}.py、app/core/ingest/recognize/{vlm_service,formula_pp_m,formula,reidentify}.py、registry/API/relay/白名单/分发、tools/{vlm_live_probe,p2t_live_probe,pp_l_live_probe}.py、tests/*、plugins.toml。
涉及文件（插件）：src/org.jiuzhang.editor/{plugin.toml,catalog.toml,dist/ui_model_install.js,dist/ui_model_table.js}、plugins.json。
使用 skill：build-release（封版动线）、sync-biz-record（本记录）、prove-visual-change/run-regression（探针证据口径）。
commit 链（底座）：0072dcc/2df2542（yolo）、63bb985（PP-L）、a1248c8/4339820/c1adb9e/8bd11c9（P2T＋texify 文案）、1af3979/1380758/d745a18/8645514（VLM 多座＋重试＋URL 修复＋探针）、a7200c0/a6eb652（收口索引/期望表）。
commit 链（插件，瞬态 MT-Blaze）：601531d/e1f9cf4/4f0d63c/b730a7e/f3727b7。
根因加固：hf-mirror 脚本 UA 403→浏览器 WEIGHT_UA；测速 2s 丢冷启动源→RACE_TIMEOUT 6s；权重单次尝试一断即败→每源重试 3 次；第二件误下首件（run4 实证 mmproj 实收主 GGUF 字节数）→按件名重建 URL。

## [VERIFY] 2026-11-20

- 真机探针：座1 yolo 16/16、座2 PP-L 28/28、座3 P2T run3 28/28（run1/run2 揪 UA403＋测速丢源两真 bug 已修）、座5/6 VLM run5 40/40 全绿（run1–4 揪徽章口径/迁移源/重试/URL 四问题已修）。
- VLM run5 绿证：书生/面壁两件 GGUF sha256 逐字一致＋共享目录共存；720×160 小题 GPU 冒烟各 3 题零失败（书生 66.9s 行内 LaTeX 正确、面壁 375.4s）；切座进程级真证（19288 停→22900 起，单活座）；按件卸载互不误删→全空目录删净；三查0＋零 JS/零 HTTP＋端口闭＋GPU 锁删＋llama/python 零孤儿；暖驻留 15024 零接触。
- 收口定向 14 模块 395/395 绿；快门禁 6 项 PASS；三查 0/0/0；包结构自检 5 支红线全过。
- 质量观察（登记非失败）：P2T 重认 4/5 原位替换＋D12 拒替换；面壁 8B Q3 简单方程输出纯文本未包 $...$（书生正确包裹），记号规范性留另卡。
- 欠账另卡：py3.14 无 cp314 轮（未装 mineru 机器无法装 VLM 发动机）；vlm_service sticky _health_ok 复用死设备实例缺陷（vlm_service.py:48-54/:117，枢纽侦查卡 71380533 挖出，本卡不改超范围）。

## [RELEASE] 2026-11-20

- 版本：editor plugin.toml 2.22.0→2.23.0（六座大改授权）；host app/__init__.py 1.2.0 不动；min_host_version 1.0.0（host 满足）。
- 四处 parity 2.23.0 一致：plugin.toml／远端 plugins.json（手工对齐 version/changelog/updated_at）／主仓 plugins.toml（sync_plugin_index rc0）／test_command_registry manual 期望表；check_plugin_index_parity rc0 PASS。
- zip 双建同哈希：dist/plugins/org.jiuzhang.editor.zip sha256 18f6235df3fdb94cd556d03ca38d02c639488c6987f6074a3c3aae6194d6bd72；包内无 models//model_prefs.toml、顶层==id、有 Apache-2.0 LICENSE、90 条目。
- 两仓 commit 不 push（奉令 hold）；新码新座需主公明早自重启生效（65496 仍暖驻留旧码）。
- 面壁商用须遵 MiniCPM Model License（弹窗已告知）；Texify 待官方/社区 ONNX 另卡零新依赖后补。
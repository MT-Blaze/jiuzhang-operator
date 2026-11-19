# 回传单 · 全模型安装接线卡（六座：yolo / PP-L / P2T-MFR / Texify / 书生 / 面壁，2.23.0）

【回执编号】 #INSTALL-ALL-01
【回执时间】 2026-11-20T03:02:13+08:00
【实际耗时】 跨段无人值守执行会话（侦查＋六座安装链/接线＋多轮真机探针；VLM 双座探针 run5 收口 1945.2s，前序 run1–4 揪 bug 累计约 20 分钟）
【执行结果】 成功（五座装成接线、一座登记跳过）。VLM 双座真机探针 run5 全绿 40/40（ok=True）；收口定向 14 模块 395/395 绿；快门禁 6 项 PASS；三查 0/0/0；包结构自检 5 支红线全过；editor zip 双建同哈希 `18f6235d…`；四处 parity 2.23.0 一致（sync rc0＋parity rc0）；两仓 commit 不 push（奉令 hold）。

基线：底座 `a10e277` ／ 插件 `51776cf`（2.22.0）；交付版本 editor 2.23.0（底座 host 仍 1.2.0）。
biz 记录：`.qoder/records/biz/2026-11/20261120_install-all.md`。
卡：`E:\jiuzhang\全模型安装接线卡.md`（唯一口径）。

## 卡§0 口径复述（逐字生效）

两仓不 push（主公明确不授权别再问）；65496 正式服务与活产品暖驻留 llama-server（PID 15024，父 11720）零接触、不杀不重启、不算占锁；
GPU 独占锁 `.system_generated/gpu-seat.lock`（起本地 VLM 前查锁＋查显存，他人活锁等≤60s，锁龄>30min 夺登记，用完删，擂台卡 fa69fcbf 互让）；
出网必须隔离副本 UI 真点发起（git archive HEAD＋动态端口随机令牌＋JZO_DATA_DIR/JZO_PLUGINS_DIR 全隔离，禁抄工作树），国内镜像禁 GitHub，sha256 逐件校验；
每座独立里程碑，卡了＝登记跳过继续下一座，绝不卡死全链；微批 3–5；不赌参数；失败显性不偷换不降级；
MinerU 本地 CPU 逐题填充与 VLM CPU 耗时基准停跑令照旧（本卡冒烟非耗时基准）；
torch/new 重依赖＝登记跳过，绝不装 torch 进底座；LICENSE/铁律一二/question_contract.py/用户 data/ 禁改；
行数帽沾到文件≤450 正常 >550 硬停、引擎适配器≤400；records append-only；禁 JSON 落盘（证据/记录用 toml/md，模型权重资产住 engines/ 不算）；分层≤3。

## 逐座交付总览

| 座 | catalog id | 结果 | 权重 sha256 逐字 | 冒烟 | 底座 commit | 插件 commit |
|---|---|---|---|---|---|---|
| 1 yolo 满血 | `yolo`（布局） | 装成接线 | ✓（下载逐字校验） | 探针 16/16 | `0072dcc`/`2df2542` | `601531d` |
| 2 PP-FormulaNet·L | `formula_pp_l` | 装成接线 | ✓（737MB 双件） | 探针 28/28 | `63bb985` | `e1f9cf4` |
| 3 Pix2Text·MFR | `formula_p2t` | 装成接线 | ✓（118MB 三件） | 探针 run3 28/28 | `a1248c8`/`4339820`/`c1adb9e`/`8bd11c9` | `4f0d63c` |
| 4 Texify | `formula_texify` | **登记跳过** | —（torch 重依赖门） | — | `a1248c8`（文案改实） | `4f0d63c` |
| 5 书生 InternVL3-2B | `vlm_intern` | 装成接线 | ✓（1.74GB 双件） | run5 3 题零失败 66.9s | `1af3979`/`1380758`/`d745a18`/`8645514` | `b730a7e`/`f3727b7` |
| 6 面壁 MiniCPM-V-2.6 | `vlm_minicpm` | 装成接线 | ✓（4.85GB 双件） | run5 3 题零失败 375.4s | 同上（多座泛化） | 同上 |

收口笔：底座 `a7200c0`（主仓 plugins.toml 对齐 2.23.0）/`a6eb652`（manual 期望表对齐）；插件 `f3727b7`（封版 2.23.0）。

## 【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator）

- `0072dcc` feat 座1：yolo 下载 sha256 校验＋纯 CPU 满血档接线＋六座侦查证据（`docs/handoff/evidence/install-all/<seat>/recon.md`）。
- `2df2542` test 座1：探针断言修正（满血档证从路由状态文取「满血版」）。
- `63bb985` feat 座2：`formula_setup` 泛化 M/L 双变体（按件装拆互不误删），薄引擎复用 M 预处理/解码（768 输入），registry/API/relay/白名单/分发/重认全链；定向 203 绿＋快门禁 PASS；`pp_l_live_probe` 随附（共享目录按件卸载真证）。
- `a1248c8` feat 座3：`formula_setup` 增 p2t 三件变体（encoder/decoder/tokenizer，hf-mirror 主源），干净房间 TrOCR 引擎（DeiT 384 预处理＋无 KV cache 贪心环＋ByteLevel 词表解码，**零新依赖不装 torch**），全链接线；texify 侦查门判跳过（官方无 ONNX）catalog 文案改实；定向 223 绿＋快门禁 PASS，引擎预冒烟 5/5 裁图 CPU 0.5–1.9s。
- `4339820` fix 座3：探针 run1 揪出 hf-mirror 非 LFS 小件脚本 UA 403——mirrors 测速与公式权重下载同用浏览器 `WEIGHT_UA`；UA 回归钉死，定向 245 绿。
- `c1adb9e` fix 座3：探针 run2 揪出测速 2 秒超时丢 hf-mirror 冷启动源——`RACE_TIMEOUT` 放宽 6 秒；定向 122 绿。
- `8bd11c9` test 座3：`p2t_live_probe` 随附 run3 28/28 绿（118MB 三件 UI 真点装、sha256 逐字、重认微批 4/5 原位替换＋D12 拒替换、整题显性拒绝、M/p2t 五件共存按件卸载、三查0＋端口闭＋孤儿零）。
- `1af3979` feat 座5/6：本地 VLM 多座泛化——`vlm_weights.SEATS`{qwen,intern,minicpm} 权重按座住 `engines/vlm/models/`、发动机共享 `engines/vlm/`；`vlm_setup`/`vlm_service` 按座起停（单活座切座先停旧座）、按件卸载（各座全空才连发动机目录删）；registry/API/relay 三口子按座泛化；T6 推理通道由千问单座泛化多座。vlm 模块 66/66＋registry 72/72＋command/router 61/61＋auto_split/formula_route/reidentify 131 绿。
- `1380758` fix：权重下载每源有限重试 `DOWNLOAD_ATTEMPTS=3`（网络中断重试，sha 不符即换源），扛 hf-mirror 中途重置；sha256/原子改名/显性失败契约不变。
- `d745a18` fix：**权重按件名重建下载 URL**——`prefetch` 把首件测速排序的 sources 原样传每件，`download_gguf` 误用 `row["url"]`（指向首件）致第二件 mmproj 实下主 GGUF（run4 实证实收 1116759488＝主件字节数）；改按 `weight_urls(seat,name)` 以源标签取本件 URL，保留测速排序；补回归断言。
- `8645514` test：`tools/vlm_live_probe.py` 双座真机探针 run5 全绿 40/40＋绿证归档（`vlm_intern/live-run.md`、`vlm_minicpm/live-run.md`、`vlm-live-run5.toml`）。
- `a7200c0` chore：主仓 `plugins.toml` 对齐 editor 2.23.0（sync rc0）。
- `a6eb652` test：`test_command_registry` manual 期望表对齐 2.23.0（test_29 版本钉死）。

### 插件仓（E:\jiuzhang\jiuzhang-plugins，瞬态身份 MT-Blaze，绝不写 git config）

- `601531d` 座1：yolo 满血版配置补 sha256（下载逐字校验对齐安装铁律）。
- `e1f9cf4` 座2：catalog `formula_pp_l` 改 weight_present 就绪口径（store formula_l/install_formula_l，737MB 成本活字＋共享目录按件卸载确认）；combo_pp_m 陈旧「D卡才开」文案修实。
- `4f0d63c` 座3/4：catalog `formula_p2t` 就绪口径（118MB 三件）；`formula_texify` 保持 blocked 登记跳过文案改实（官方无 ONNX、底座零 torch 红线、可后补条件写明）。
- `b730a7e` 座5/6：catalog 书生/面壁 vram_gate→vlm_local 已接线＋安装 UI 按座（`ui_model_install.js` 成本活字：书生 1.74GB/面壁 4.85GB＋共享发动机＋面壁 MiniCPM Model License 告知；`ui_model_table.js` 本地判定）。
- `f3727b7` chore：封版 2.23.0（plugin.toml＋plugins.json 版本/changelog/updated_at 对齐）。

## 【真机探针绿证（VLM 双座 run5）】

隔离副本 operator `d745a187`／plugins `b730a7e5`（git archive，非工作树）；动态端口 26646＋随机令牌；暖驻留 15024 全程零接触。

- **书生安装**：UI 真点 POST `/api/models/vlm_intern/install`，弹窗「1.74GB＋共享发动机」accept；state=done（mineru-llama-cpp 0.2.1 Vulkan）；两件 sha256 逐字一致：
  - `InternVL3-2B.Q4_K_M.gguf` 1116759488 `201270a0982bdd0d246040c9aef46f35456f0cb1e60c2a96280b0c706052b7e8`
  - `InternVL3-2B.mmproj-f16.gguf` 628237888 `99bc7344acdafbe38c908ee14439cfb68475aefbbd692cb7436cb80f0b8fef6b`
- **书生冒烟**（持 GPU 锁，720×160 小题绿区，显式选 vlm_intern）：三批各 1 道非占位待审题＋零失败，66.9s；行内 LaTeX 正确（`$x + 3 = 7$` 等）；llama-server PID 19288 挂书生权重 `-ngl 999`。
- **面壁安装**：弹窗「4.85GB＋MiniCPM Model License」accept；state=done；两件 sha256 逐字一致且书生两件仍在（共享目录共存）：
  - `ggml-model-Q3_K_M.gguf` 3806596448 `5a050acc927498ca4e05d38207bbd89d013154a7b9b24ac9ff4e45c870bc7f62`
  - `mmproj-model-f16.gguf` 1044425152 `4485f68a0f1aa404c391e788ea88ea653c100d8e98fe572698f701e5809711fd`
- **面壁冒烟＋切座真证**：三批零失败 375.4s；llama-server PID 22900 挂面壁权重；**书生 PID 19288 已停（单活座，进程级真证）**。
- **按件卸载**：卸书生只删两件、面壁两件＋发动机目录原样保留、面壁仍就绪书生回未安装；再卸面壁两件删净后 `engines/vlm` 整体删（各座全空）＋在跑服务已停。
- **收口**：三查 0/0/0、零 JS 异常、零 HTTP 失败、端口复验闭、GPU 锁用完删、llama-server 零孤儿、python 孤儿零。
- 原始件：`docs/handoff/evidence/install-all/vlm-live-run5.toml`；截图 `.system_generated/vlm-live/run5/shots/`（gitignore）。

## 【测试总账】

- 收口定向 14 模块汇总 **395/395 绿**（test_vlm_setup/vlm_service/vlm_local_run/formula_setup/models_registry/command_registry/command_hardening/recognize_router/formula_route/reidentify/auto_split/layout_models/layout_router/installer_layout）。
- 逐座施工期定向（commit 内记录）：座2 203 绿、座3 223→245→122 绿、座5/6 vlm 66＋registry 72＋command/router 61＋auto_split/formula_route/reidentify 131 绿。
- 快门禁 6 项 PASS（多次）；三查 0/0/0；包结构自检 5 支红线全过。
- 真机探针：座1 16/16、座2 28/28、座3 run3 28/28、座5/6 run5 40/40。
- 全量回归奉令免（2026-11-18 拍板，定向＋门禁为主）。

## 【parity / zip / 版本】

- 版本单源：底座 `app/__init__.py:8` `__version__="1.2.0"`（不动）；editor `plugin.toml` 2.22.0→**2.23.0**（六座大改授权升版）。
- 四处 parity：① editor plugin.toml 2.23.0 ② 远端 plugins.json 2.23.0（手工对齐 version/changelog/updated_at=2026-11-20）③ 主仓 plugins.toml 2.23.0（sync_plugin_index rc0 改写）④ test_command_registry manual 期望表 2.23.0。`check_plugin_index_parity.py` rc0 PASS。
- zip 双建同哈希：`dist/plugins/org.jiuzhang.editor.zip` sha256 `18f6235df3fdb94cd556d03ca38d02c639488c6987f6074a3c3aae6194d6bd72`（两次 build_plugin --all 一致）；包内无 `models/`、无 `model_prefs.toml`、顶层目录==id、有 Apache-2.0 LICENSE 全文、90 条目；min_host_version 1.0.0（host 1.2.0 满足）。
- `models/` 与 `model_prefs.toml` 不入包不碰（插件仓 untracked 留原位）。

## 【跳过账本】

| 座 | 原因 | 证据 | 可否后补 |
|---|---|---|---|
| 4 Texify（`formula_texify`） | 官方权重仅 PyTorch（.pt），无官方 ONNX；装它须 torch 重依赖＝触底座零 torch 红线，recon 门早判跳过 | `docs/handoff/evidence/install-all/formula_texify/recon.md`；catalog blocked 文案改实（`a1248c8`/`4f0d63c`） | **可**：官方若出 ONNX 导出或社区转 ONNX，可零新依赖复用底座 onnxruntime 另卡接线（条件已写进 catalog 文案） |

## 【修复账（本卡新码根因加固）】

- hf-mirror 非 LFS 小件脚本 UA 403 → 浏览器 `WEIGHT_UA`（`4339820`，座3 run1 实证）。
- 测速 2 秒超时丢 hf-mirror 冷启动源 → `RACE_TIMEOUT` 6 秒（`c1adb9e`，座3 run2 实证）。
- 权重下载单次尝试一断即败 → 每源有限重试 3 次（`1380758`，座5 run3 表面现象）。
- **第二件权重误下首件**（run4 实证 mmproj 实收主 GGUF 字节数）→ 按件名重建 URL（`d745a18`，根因；run3 的 10054 亦是重下 1.1GB 主件中途断）。

## 【质量观察（登记，非失败，不在本卡改）】

- 座3 P2T-MFR：重认微批 4/5 原位替换、D12 拒替换（记号规范性观察，留记号标准字典条款级回写另卡）。
- 座6 面壁 8B Q3：三道简单方程输出**纯文本**（`x + 3 = 7`）未自动包行内 `$...$`，书生 2B 同题正确包裹；内容识别正确零失败，LaTeX 记号规范性弱于书生座——同类留另卡，不在本安装卡改 prompt/后处理（超范围）。

## 【偏离登记 / 欠账（另卡候选）】

1. **迁移源偏离（已登记，合规）**：py3.14 无 mineru-llama-cpp 0.2.3 预编译轮，pip 四家测速全败后走 `engines/mineru` 离线迁移（真机同款，engine.toml origin=迁移，不算出网）。隔离副本预置同款迁移源复现真机前置（mineru 本地座已装），**非抄工作树代码**；UI 点击仍真跑 pip 测速→全败→迁移链，GGUF 权重照旧由点击真下载＋sha256 校验。
2. **py3.14 轮欠账（另卡）**：本机 Python 3.14.6，mineru-llama-cpp 0.2.3 国内镜像无 cp314 轮 → 纯 pip 路径必败、全靠 mineru 离线迁移兜底。**未装 mineru 本地座的机器无法装 VLM 发动机**——欠账另卡（补 cp314 轮或独立发动机包）。
3. **vlm_service sticky 缺陷（另卡候选，本卡不改超范围）**：`app/core/ingest/recognize/vlm_service.py:48-54` `_health_ok` 只探 `/health`；`:117` 同座复用闸口。RDNA1 掉设备后实例返 mtmd-500 但 `/health` 仍 200 → 复用死实例一直红。枢纽侦查卡 71380533 已挖出，**本安装卡不改它**，回单登记。探针已含枢纽规则②杀自起实例重试兜底（run5 绿区未触发）。
4. **测试污染事故已清**：前序段单测曾误触真机权重，已 patch 双 engine_dir 路径隔离，本卡定向全绿无残留。

## 【需主公点】

- **新码新座生效需主公明早自重启**：本卡所有底座/插件改动已 commit，但 65496 正式服务仍在旧码暖驻留；书生/面壁新座与多座泛化要主公重启后才在正式产品生效（探针在隔离副本已真证）。
- **面壁商用许可**：MiniCPM Model License——个人/学术研究免费，商用须遵官方条款（按要求登记）；安装弹窗已告知。
- **push 奉令 hold**：两仓本卡 commit 均未 push（主公明确不授权别再问）。
- **Texify 后补**：待官方/社区 ONNX 导出，另卡零新依赖接线。
- **py3.14 发动机轮欠账**＋**vlm_service sticky 缺陷**：另卡候选，请主公排期。

## 【自检】

- [x] 每座独立里程碑，卡了登记跳过（Texify）继续下一座，全链未卡死
- [x] 出网隔离副本 UI 真点发起、国内镜像禁 GitHub、sha256 逐件校验
- [x] 65496 暖驻留 15024 零接触；GPU 锁查/持/删、用完零孤儿
- [x] 不装 torch 进底座（p2t 零新依赖、texify 跳过）
- [x] 失败显性不偷换不降级；微批 3；不赌参数（绿区小题）
- [x] 行数帽：vlm_weights 186、探针 537（双座预警区<550）、引擎适配器≤400
- [x] parity 四处 2.23.0 一致 rc0；zip 双建同哈希；models//model_prefs.toml 不入包不碰
- [x] 两仓 commit 不 push；插件瞬态身份不写 git config
- [x] 回单数字来自当次实跑（run5 40/40、定向 395/395、zip 18f6235d…）
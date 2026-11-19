# 面壁 MiniCPM-V-2.6（vlm_minicpm）真机安装＋冒烟绿证

- 探针：`tools/vlm_live_probe.py run5`（双座共一轮）
- 时间：2026-11-20，本轮 40/40 全绿 failed=0
- 隔离副本：operator HEAD `d745a187`、plugins HEAD `b730a7e5`（git archive，非工作树）
- 原始件：`../vlm-live-run5.toml`、`../vlm-live-run5.log`；截图 `.system_generated/vlm-live/run5/shots/`（gitignore）

## 安装链（UI 真点发起）

- 确认弹窗：「安装要下约 4.85GB（权重 3.81G＋视觉部件 1.04G）占磁盘，走国内镜像。发动机与千问座共享 engines/vlm/，已装过则只下本座权重。权重许可为 MiniCPM Model License：个人/研究免费，商用须遵官方条款。仍要安装？」accept
- POST `/api/models/vlm_minicpm/install` 真发
- 收口 state=done：「面壁 MiniCPM-V-2.6 已就绪（mineru-llama-cpp 0.2.1，Vulkan 发动机），GGUF 权重已预取。」
- 两件 GGUF 落地 sha256 逐字一致，且书生两件仍在（共享目录共存）：
  - `ggml-model-Q3_K_M.gguf` 3806596448 字节 `5a050acc927498ca4e05d38207bbd89d013154a7b9b24ac9ff4e45c870bc7f62`
  - `mmproj-model-f16.gguf` 1044425152 字节 `4485f68a0f1aa404c391e788ea88ea653c100d8e98fe572698f701e5809711fd`
- 徽章：未安装 → 已安装·就绪（Vulkan）

## GPU 冒烟＋切座真证（持 gpu-seat.lock，720×160 小题绿区）

- 识别下拉显式选 `vlm_minicpm`；三图各立独立批次（解析请求 201）
- 三批全收口 375.4s，各批 1 道非占位待审题＋零失败清单：
  - 面壁小题1：`解方程：x + 3 = 7，求 x 的值。`（139.4s）
  - 面壁小题2：`解方程：2x - 5 = 9，求 x 的值。`（258.4s）
  - 面壁小题3：`3. 若 3x = 12，求 x 的值。`（375.4s）
- llama-server PID 22900 挂 `ggml-model-Q3_K_M.gguf`＋`mmproj-model-f16.gguf`，`-ngl 999`
- **切座真证（单活座）**：书生 PID 19288 已停、面壁 PID 22900 起（进程级证明，强于日志）；`switch_log` 文本 grep 为空（logger.info 路由未落 uvicorn stdout，不影响进程真证）
- 无 mtmd-500/掉设备（绿区小题），未触发杀实例重试
- 8B Q3 逐题明显慢于书生 2B（~125s/题 vs ~22s/题），6G 卡稳进、零掉设备

## 按件卸载（全空才连发动机删）

- 卸书生后面壁两件＋发动机目录原样保留、面壁仍就绪
- 再卸面壁：弹窗摆明「在跑本座会先停服」；两件删净后 engines/vlm 目录整体删（各座全空）＋在跑服务已停（servers=[]）

## 质量观察（登记，非失败）

- 面壁 8B Q3 对这三道简单方程输出**纯文本**（`x + 3 = 7`），未自动包行内 `$...$`；书生 2B 同题则正确包裹。内容识别正确、零失败，但 LaTeX 记号规范性弱于书生座——与 p2t 质量观察同类，留待记号标准字典条款级回写另卡，不在本安装卡改 prompt/后处理（超范围）。
- 许可：MiniCPM Model License，个人/学术研究免费，商用须遵官方条款（弹窗已告知）。
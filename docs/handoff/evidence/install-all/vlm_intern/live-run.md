# 书生 InternVL3-2B（vlm_intern）真机安装＋冒烟绿证

- 探针：`tools/vlm_live_probe.py run5`（双座共一轮）
- 时间：2026-11-20，elapsed 1945.2s（含面壁座），本轮 40/40 全绿 failed=0
- 隔离副本：operator HEAD `d745a187`、plugins HEAD `b730a7e5`（git archive，非工作树）
- 原始件：`../vlm-live-run5.toml`、`../vlm-live-run5.log`；截图 `.system_generated/vlm-live/run5/shots/`（gitignore）

## 安装链（UI 真点发起）

- 确认弹窗：「安装要下约 1.74GB（权重 1.12G＋视觉部件 0.63G）占磁盘，走国内镜像。发动机与千问座共享 engines/vlm/，已装过则只下本座权重。仍要安装？」accept
- POST `/api/models/vlm_intern/install` 真发
- 收口 state=done：「书生 InternVL3-2B 已就绪（mineru-llama-cpp 0.2.1，Vulkan 发动机），GGUF 权重已预取。」
- 发动机：py3.14 无 0.2.3 预编译轮 → pip 四家测速全败 → engines/mineru 离线迁移（真机同款，副本预置迁移源复现前置，非抄代码、不算出网）；副本内 `ggml-vulkan.dll`＋`llama-server.exe` 现算＝Vulkan
- 两件 GGUF 落地 sha256 逐字一致：
  - `InternVL3-2B.Q4_K_M.gguf` 1116759488 字节 `201270a0982bdd0d246040c9aef46f35456f0cb1e60c2a96280b0c706052b7e8`
  - `InternVL3-2B.mmproj-f16.gguf` 628237888 字节 `99bc7344acdafbe38c908ee14439cfb68475aefbbd692cb7436cb80f0b8fef6b`
- 徽章：未安装 → 已安装·就绪（Vulkan）＋【卸载】钮

## GPU 冒烟（持 gpu-seat.lock，720×160 小题绿区）

- 起 llama-server 前自持 GPU 锁；暖驻留 15024（父 11720＝65496 产品）全程零接触
- 识别下拉显式选 `vlm_intern`；三图各立独立批次（解析请求 201）
- 三批全收口 66.9s，各批 1 道非占位待审题＋零失败清单：
  - 书生小题1：`1. 解方程：$x + 3 = 7$，求 $x$ 的值。`（30.5s）
  - 书生小题2：`2. 解方程：$2x - 5 = 9$，求 $x$ 的值。`（48.7s）
  - 书生小题3：`3. 若 $3x = 12$，求 $x$ 的值。`（66.9s）
- 行内 LaTeX `$...$` 包裹正确；llama-server PID 19288 挂 `InternVL3-2B.Q4_K_M.gguf`＋`InternVL3-2B.mmproj-f16.gguf`，`-ngl 999`（显卡加速）
- 无 mtmd-500/掉设备（绿区小题），未触发杀实例重试

## 按件卸载（互不误删）

- 卸书生弹窗摆明「本座两件权重（其他座不受影响；各座全卸空才连发动机目录一起删）」
- 只删书生两件；面壁两件＋发动机目录原样保留；面壁仍就绪、书生回未安装＋【安装】钮

## 质量观察

- 2B Q4_K_M 日常印刷小题够用，行内数学自动 `$...$` 包裹；复杂公式未测（超冒烟范围）
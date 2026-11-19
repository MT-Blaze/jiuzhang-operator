# 座5 vlm_intern（书生 InternVL3-2B 本地）侦查

## 结论：GGUF＋mmproj 走 engines/vlm 现成 llama.cpp Vulkan 栈，mtmd 支持 internvl，约 1.74GB 稳进 6G

- 栈核实：`engines/vlm/llama-bin/`（mineru-llama-cpp 0.2.1 迁移，llama-server 0.6.0-dev build 1
  commit 86a2835）；`mtmd.dll` 二进制串扫描确认含 `clip_graph_internvl`（＋minicpmv/qwen2vl/qwen3vl 等）。
- 权重仓 hf-mirror `mradermacher/InternVL3-2B-GGUF`（apache-2.0；上游 OpenGVLab/InternVL3-2B 亦 apache-2.0）：
  - `InternVL3-2B.Q4_K_M.gguf` size = 1,116,759,488
    sha256 = `201270a0982bdd0d246040c9aef46f35456f0cb1e60c2a96280b0c706052b7e8`
  - `InternVL3-2B.mmproj-f16.gguf` size = 628,237,888
    sha256 = `99bc7344acdafbe38c908ee14439cfb68475aefbbd692cb7436cb80f0b8fef6b`
  - 备选省显存：`InternVL3-2B.mmproj-Q8_0.gguf` size = 337,012,288
    sha256 = `d7083116b6a6d76f5b17d9157aeedbc13eb071136dca620f81a8e4919d3d0e37`
- 显存预算（RX 5600 XT 6G）：Q4_K_M 1.12G＋mmproj-f16 0.63G ≈ 1.75G 权重＋KV(8192 ctx)＋compute buffer，
  2B 模型远低于 6G，**稳进**。min_vram=6 门槛满足。
- 国内镜像：hf-mirror.com（禁 GitHub 直连）。

## 接线方案（T6 多座泛化，大活）

- `vlm_setup.py`（现 400 行 AT CAP，Qwen 硬编码）→ SEATS 表（qwen/intern/minicpm），
  weights_ready()/status()/start_install() 按 seat；GGUF_FILES/MODEL_REPO 按座。守帽≤450，超则拆。
- `vlm_service.py` 单活座泛化：ensure_ready(seat)/start(seat)/stop()，切座先显式停旧座。
- `vlm_local.py` run() 注记「本地千问 VLM」泛化按座名。
- registry `_rule_vlm_local` 传 seat=item.id；catalog vlm_intern vram_gate→vlm_local＋store＋plan_recognize＋install 动作。
- api/models.py vlm install/status 带 seat body 参；relay T6＋stage_command 白名单＋UI install 按座。

## 冒烟约束（GPU 锁§3＋大图 hang 教训）

- 起 llama-server 前查 `gpu-seat.lock`＋查无其他探针 llama-server；暖驻留实例（父=65496）零接触。
- **大图 hang 根因**（记忆 project-vulkan-driver-closeout）：RDNA1 批宽阈值 hang（llama.cpp #28808 未修），
  单图 >≈245–400 token 红。冒烟用**小裁图**（≤~245 token），避开大图；sticky 死实例/health 复用缺陷另卡。
- 冒烟 3–5 小题图，原位回填/显性失败如实。
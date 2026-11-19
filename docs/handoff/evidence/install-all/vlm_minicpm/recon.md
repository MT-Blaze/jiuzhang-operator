# 座6 vlm_minicpm（面壁 MiniCPM-V-2_6 本地）侦查

## 结论：GGUF＋mmproj 走 engines/vlm Vulkan 栈，mtmd 支持 minicpmv；6G 显存定 Q3_K_M 档

- 栈核实：同 vlm_intern，`mtmd.dll` 含 `clip_graph_minicpmv`（＋minicpmv4_6）。
- 权重仓 ModelScope `OpenBMB/MiniCPM-V-2_6-gguf`（国内镜像，禁 GitHub）。权威 Sha256（ModelScope LFS）：
  - **选定档** `ggml-model-Q3_K_M.gguf` size = 3,806,596,448
    sha256 = `5a050acc927498ca4e05d38207bbd89d013154a7b9b24ac9ff4e45c870bc7f62`
  - `mmproj-model-f16.gguf` size = 1,044,425,152
    sha256 = `4485f68a0f1aa404c391e788ea88ea653c100d8e98fe572698f701e5809711fd`
  - 参考档（超 6G 不选）：Q4_K_M 4,681,089,344 / Q4_K_S 4,455,784,768
    sha `6f8e13697c94a6ffdd485d4054b493a43640d5220303ee9600dd8dab4c3da564` / IQ4_XS 4,248,358,752。

## 显存预算（RX 5600 XT 6G，8B 模型）

| 档 | 权重 | ＋mmproj 1.04G | ＋KV(8192)＋compute | 结论 |
|---|---|---|---|---|
| Q4_K_M | 4.68G | 5.72G | ≈6.5G+ | 超 6G，不选 |
| Q4_K_S | 4.46G | 5.50G | ≈6.3G | 超 6G，不选 |
| IQ4_XS | 4.25G | 5.29G | ≈6.1G | 临界偏超，不选 |
| **Q3_K_M** | 3.81G | 4.85G | ≈5.7G | **稳进 6G，选定** |

- 按卡§1「超 6G 选更小档」定 **Q3_K_M**。min_vram=6 门槛满足。

## license 登记（告知，非阻断）

- 代码 Apache-2.0；**权重为自定义 MiniCPM Model License**（上游 README 模型许可条款，
  商用需遵守其条款）。回单作为告知项登记，不阻断接入。

## 接线方案

- 同 vlm_intern 的 T6 多座泛化（vlm_setup SEATS 表增 minicpm 座，GGUF_FILES=Q3_K_M＋mmproj-f16）。
- catalog vlm_minicpm vram_gate→vlm_local＋store＋plan_recognize＋install 动作＋min_vram=6。

## 冒烟约束

- 同 vlm_intern：GPU 锁§3＋暖驻留零接触＋**小裁图**（RDNA1 大图 hang #28808，单图 >≈245–400 token 红）。
- MiniCPM 显存更紧，冒烟先确认 llama-server 加载不 OOM；若 Q3_K_M 仍 OOM 则降 Q3_K_S（3.49G）并登记。
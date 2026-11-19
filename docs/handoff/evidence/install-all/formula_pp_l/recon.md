# 座2 formula_pp_l（PP-FormulaNet_plus-L）侦查

## 结论：PP-M 同族 ONNX，仅输入分辨率 384→768，零新依赖，薄兄弟引擎复用 M 纯助手

- 算法 provenance 与 PP-M 完全同族（UniMERNet ONNX，自回归环**在图内**）：
  - 预处理 mean=0.7931 std=0.1738（与 M 同），GPT-2 ByteLevel 解码，eos id=2，latex_norm.clean 出口。
  - **唯一差异**：输入 `[B,1,768,768]`（M 是 `[B,1,384,384]`）。tokenizer/解码/归一全同（已从 L yml 核实）。
- 权重两件套（国内镜像 ModelScope `RapidAI/RapidDoc` resolve/master/formula/PP-FormulaNet_plus-L/）：
  - `pp_formulanet_plus_l_inference.onnx`
    - size = 735,058,717 bytes
    - sha256 = `f6686782c2bb5f84000ff9da4788ac672e736fa2d0652f483a140fa8401b3d32`
  - `pp_formulanet_plus_l_inference.yml`（**已下载留证**，本目录）
    - size = 2,244,564 bytes
    - sha256 = `afc92a2737268da0499c37b0b6741da268c369fd7424667fcfeb8fa6c7b22d30`（与远端一致）
    - 注：RapidDoc 的 L 文件夹只有 onnx，yml 取自官方 PaddlePaddle 仓同名配置。
- license：Apache-2.0（PP-FormulaNet 官方）。
- 显存：onnxruntime CPU 推理，无 6G 门槛。

## 接线方案

- `formula_pp_m.py` 参数化纯助手：`_preprocess(png, size)`、`_decode(ids, dec)`，M 自身调用不变。
- 新增薄兄弟 `formula_pp_l.py`（≤400 行）：_SIZE=768，复用 M 的 session/decoder/预处理/解码纯函数，
  懒加载＋weights_ready 闸＋latex_norm.clean 出口。
- `formula_setup.py` 从 M-only 泛化到变体表（m/l），install/status/uninstall 按变体；
  **uninstall 必须改按变体文件删**（L 与 M 共享 engines/formula/ 目录，不能整目录 rmtree 误删 M）。
- registry `_rule_weight_present` 增 formula_l store 分支；dispatch/reidentify 增 formula_pp_l 分支。
- catalog 只改 formula_pp_l 条目（blocked→weight_present＋store=formula_l＋plan＋安装活字）。

## 冒烟复用

- 复用 `docs/handoff/evidence/pp-m-recon/fixtures/f1–f5.png`（5 张真实公式裁图）。
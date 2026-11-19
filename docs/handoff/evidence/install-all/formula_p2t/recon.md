# 座3 formula_p2t（Pix2Text·MFR）侦查 —— recon 门：通过

## 结论：官方 ONNX 在位，底座 onnxruntime 零新依赖可跑，手写贪心解码环＋词表解析

- 官方仓 hf-mirror `breezedeus/pix2text-mfr`（VisionEncoderDecoderModel，TrOCR 系）：
  - `encoder_model.onnx` size = 87,496,990 bytes（DeiT 编码器）
  - `decoder_model.onnx` size = 30,114,937 bytes（TrOCR 解码器，**无 decoder_with_past**＝无 KV cache，
    解码环每步重喂全序列，简单）
  - `tokenizer.json`（BPE，vocab 1200，piece→id 字典可逆）＋config/preprocessor/generation 等小件（**已下载留证**，本目录）
  - 合计权重约 118MB。license：Apache-2.0（pix2text-mfr）。
- 底座依赖核实：onnxruntime 1.32.0 / numpy 2.5.5 / PIL 13.0.0 **均已在底座**，零新依赖。
  （pix2text 库本身依赖 torch，但**不装库**，只取 ONNX 权重＋手写推理，绕开 torch。）

## I/O 与解码（已从 config/preprocessor 核实）

- 编码器输入：`[B,3,384,384]` float32；DeiT 预处理 resize 384×384（bicubic resample=3）＋
  rescale 1/255＋normalize mean=[0.5,0.5,0.5] std=[0.5,0.5,0.5]。
- 解码器：d_model=256，vocab=1200，decoder_start_token_id=2，eos_token_id=2，pad=0，
  max_position_embeddings=512，use_cache=false。
- 贪心解码环（clean-room）：ids=[2] 起步 → encoder_hidden_states 喂解码器 → 取末位 logits argmax →
  append → 遇 eos=2 或达 512 止 → id→piece（反转 tokenizer.json model.vocab）拼接，
  ▁(U+2581)→空格，剥特殊 token → latex_norm.clean 出口。

## 接线方案

- 新增 `formula_p2t.py`（≤400 行）：DeiT 预处理＋encoder run＋贪心解码环＋词表解码＋weights_ready 闸＋latex_norm.clean。
- formula_setup 变体表增 p2t（encoder/decoder/tokenizer/config 多件 sha256 校验）；store=formula_p2t。
- registry weight_present 增 formula_p2t；dispatch/reidentify 增 formula_p2t；catalog 只改本座条目。

## 待核（安装链阶段）

- encoder/decoder 实际输入/输出张量名与形状（下载 onnx 后用 onnxruntime 探）。
- 远端 sha256（hf-mirror lfs.oid）逐字校验。
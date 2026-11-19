# 座4 formula_texify（Texify）侦查 —— recon 门：登记跳过

## 结论：跳过。官方仅 torch safetensors，无官方 ONNX，跑起来必须 torch/transformers 新重依赖

- 官方仓 hf-mirror `vikp/texify`（VikParuchuri/texify 的 HF 镜像）文件清单：
  - `model.safetensors` size = 625,067,248 bytes
    sha256(lfs.oid) = `c4eed27b2bbeb493d7fbba31feda6af5c7527246a35a96d49eaa1010f9c7e9af`
  - 其余全是 torch 生态配置：config.json / tokenizer.json / sentencepiece.bpe.model /
    preprocessor_config.json / training_args.bin。**无任何 .onnx 文件**。
- 架构：Donut/Nougat 系 vision-encoder-decoder，官方推理走 transformers＋torch。
- 社区 ONNX 导出：WebSearch（texify ONNX export / onnxruntime）未找到可用官方或社区 ONNX 权重仓；
  hf-mirror 搜索 API 不返回结构化结果，单仓 tree 核实官方仓确无 onnx。
- 底座红线：**绝不往底座装 torch**（卡§1 recon 门＋agents 铁律）。safetensors 无法用底座
  onnxruntime 直接加载；自行转换需 torch＋transformers＋optimum，属新重依赖，且转换本身要出网装包。

## 跳过账本

- 座：formula_texify
- 原因：无官方 ONNX，运行/转换必须 torch/transformers 新重依赖，触底座红线。
- 证据：本文件＋官方仓 tree 清单（仅 safetensors）。
- 可否后补：可。若日后出现官方/可信社区 ONNX 导出（encoder+decoder+tokenizer），
  可按 formula_p2t 同套路（底座 onnxruntime＋手写解码环）零新依赖接入，届时另卡。
- catalog 处理：formula_texify 条目**保持 blocked**，文案改实为「需 torch 重依赖，底座红线暂不接入」口径，
  不宣称已就绪。
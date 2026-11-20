# Texify 社区 ONNX 侦查＋CPU 早判门（接线卡④§2）

日期：2026-11-20。执行：独立执行会话（零委托）。
基线实测：operator `d2f9b269923fba29dc95de75644b7916bd258222`（ahead 73）／
plugins `e6569ced03208efe526c316d3a287cfcbf12cb8f`（ahead 21，editor 2.24.0）——与派卡一致，零偏离。
权重源：hf-mirror.com（国内镜像，禁 GitHub），侦查下载用 curl＋Mozilla UA；
产品安装链沿用 formula_setup 既有 WEIGHT_UA／mirrors.race 测速口径。
侦查产物住 `.system_generated/texify-recon/`（gitignore 内，不 stage）；
本文件与 probe/shots/wire 住 `docs/handoff/evidence/texify-onnx/`。

## 1 许可

- `Spedon/texify-quantized-onnx`：cc-by-sa-4.0（仓库页标注）。
- `Spedon/texify-fp16-onnx`：cc-by-sa-4.0（同）。
- 口径：权重资产的内容许可＝署名＋相同方式共享（ShareAlike），**非**代码 GPL/AGPL 红线；
  底座代码干净房间手写（只读公开 config/标准，不抄 texify/Surya 任何代码，Surya GPL 不追不装）。
- 告知三处：安装弹窗（ui_model_install.js）＋catalog 文案（summary_usage/ready_detail）＋回单。
- 不碰 Xenova/texify（无许可证标注）。

## 2 架构与小件实探（int8 仓 resolve 下载实测）

config.json：VisionEncoderDecoderModel；encoder＝donut-swin（image_size 420×420、3 通道、
patch 4、window 5、hidden 1024）；decoder＝mbart（8 层、d_model 1024、16 头×64、
vocab 50000、max_position_embeddings 1536、scale_embedding）。
decoder_start_token_id=0、eos=2、pad=1、bos=0（generation_config.json 同）。
**generation_config.json 无 max_new_tokens/max_length 字段**——生成帽取
config.json decoder.max_position_embeddings=1536（位置编码硬上限，非赌参数）。

preprocessor_config.json：DonutImageProcessor，size/max_size 420×420、resample=2（bilinear）、
rescale 1/255、ImageNet mean [0.485,0.456,0.406] std [0.229,0.224,0.225]、
do_resize/do_thumbnail/do_pad 均 true。实测两解释（见§4）：resize 420² 直缩吐字正确，
thumbnail 保比例＋补黑边反而乱码——**采 resize 420×420 直缩＋ImageNet 归一**（config 字面序）。

tokenizer.json（2140041 字节）：BPE vocab 50000＋merges；**decoder＝ByteLevel
（add_prefix_space=true），不是卡文假设的 ▁ metaspace**——vocab 含 Ġ 件 31928 个、
▁ 件 0 个（实测）。解码口径＝p2t 同族：id→piece→GPT-2 字节逆映射→utf-8，
added_tokens 23 个（id 0–22：`<s>/<pad>/</s>/<unk>/[START_REF]`…）全跳过。
normalizer NFKC／pre_tokenizer Split+Digits 只影响编码侧，解码不需要。零新依赖成立
（不装 tokenizers/sentencepiece/torch）。

ort_config.json（仅 int8 仓有）：QOperator 动态量化，Conv/MatMul/Attention 等 QUInt8。

decoder_merged I/O 实探（ort 1.32.0 CPUExecutionProvider session.get_inputs/outputs）：
- encoder：pixel_values [B,3,H,W] float → last_hidden_state [B,196,1024]。
- decoder_merged：input_ids [B,seq] int64＋encoder_hidden_states [B,196,1024]＋
  past_key_values.{0..7}.{decoder,encoder}.{key,value} [B,16,past,64]＋use_cache_branch [1] bool
  → logits [B,seq,50000]＋present.{0..7}.{decoder,encoder}.{key,value}。
- 首步 use_cache_branch=False＋past 空张量 [1,16,0,64]；后续 True＋单 token＋present 回喂。

## 3 权重校验钉（施工复核，sha256 逐字实测）

int8（Spedon/texify-quantized-onnx，~319MB）：
- encoder_model_quantized.onnx 79294829 字节
  sha256 `302452c132a82b1c70389f0f646952586afa20c3f9a16b517e40600c49eb8f23` ✓==卡钉
- decoder_model_merged_quantized.onnx 239901134 字节
  sha256 `ed067534a996c818708d0d377b94ace32b9738f0d7a0c4ef635e4fa3d28653ce` ✓==卡钉

fp16（Spedon/texify-fp16-onnx，~628MB）：
- encoder_model.onnx 151072055 字节
  sha256 `6083149d64fb17dcfacf85b6137c2cf316b33eb1c80a3fde58fcb869c3f17f46` ✓==卡钉
- decoder_model_merged.onnx 477396232 字节
  sha256 `4b9241793ee344c754944e79049f310173bf87902be6f3e85aeb4a538a5ae83f` ✓==卡钉

小件（非 LFS，无权威预哈希；侦查下载后算 sha256 钉进 catalog 作一致性校验，
authenticity 锚＝上面两件 LFS oid）：

| 件 | int8 仓字节/sha256 | fp16 仓字节/sha256 |
|---|---|---|
| config.json | 4890 / `e1f358f06180ef9533c188f39b46554ccd68d52b2de89ea47a999f52dda4e375` | 4890 / 同左 |
| tokenizer.json | 2140041 / `06506d8033a4080bba741ed86b416ef238cae52b169cb0045404d6032fd657c2` | 2140041 / 同左 |
| preprocessor_config.json | 615 / `b2fc6ff0098ac8e6af6e688bfc28188db883c99a48afa60e8555faeedc0c45e4` | 523 / `07bbb730a28a5a37d70fd9530ef1a2a367b11852bc1f2881acb83933f867e478` |
| generation_config.json | 191 / `0fb8980236d664d2851ed5939b435ecc6fe0e32ee08b83e75cb1743db0cfe10e` | 200 / `aa08c04e00a1d384bee28e0a56d465d65442625459917002e1686cb15aed94c6` |
| ort_config.json | 764 / `62a98e992faf1b0af04e290a749ee1ea087cef9cd758615fc7b3cebf2446da1d` | **仓里无此件**（404） |

fp16 仓 preprocessor/generation 与 int8 仓只差 legacy 键/transformers_version 字符串，
预处理与生成语义逐字相同（diff 实测）。

## 4 CPU 早判冒烟门（金标裁图 f01/f03/f10，arena/golden 只读复用）

脚本 `.system_generated/texify-recon/smoke.py`（侦查脚本，非引擎成品）。

### int8＋past KV＝坏（显性登记）

- resize 420² 与 thumbnail 两预处理都吐重复乱码：f01 767 token 循环
  （`\frac{1}{2}\left(...\right)^{2}+` 复读）、f10 767 token `\Gamma_0=` 复读；
  f03 两预处理输出逐字相同（35 token 退化 array）——当时疑量化退化，
  后经 fp16 同症＋present 对比钉死为 merged 导出共有病灶（见下节）。
- **无 KV 对照（use_cache_branch=False 每步重喂全序列）f01 完美命中金标**：
  `$$\frac{a^{2}-b^{2}}{a+b}=a-b$$`（26 token，1.7s）——权重与预处理本身没错。
- 逐步对照定位：step2 cache/no-cache logits argmax 一致（cosine 0.9998），
  **step5 分歧**（cache=39 vs no-cache=87）——当时归因量化漂移，fp16 同症后改判
  merged 导出 cache 分支 present 接线损坏（下节实锤）。
  结论：int8＋§3 规定的 past KV 贪心环＝不可用。

### fp16＋past KV＝同症（不是量化漂移，是导出结构病灶）

fp16 权重两件 sha256 逐字==卡钉（§3）。fp16 导出为真 float16 I/O（全部张量，
首跑 float32 喂入报 InvalidArgument，改 float16 后正常）。KV 贪心冒烟吐与 int8
**逐字相同**的乱码（f01/f10 767 token 复读、f03 35 token 退化 array）——fp16 无量化
误差却同症，说明病灶不在量化，在 merged 图本身。

### 根因钉死（fp16 逐步对照＋present 张量对比，debug_fp16.py / pin_fp16.py / pin2_fp16.py）

- no-cache 对照（use_cache_branch=False 每步重喂全序列）：**f01 完美命中金标**
  `$$\frac{a^{2}-b^{2}}{a+b}=a-b$$`（26 token，6.0s）。
- cache 环逐步对照：step0/1 argmax 一致 cos=1.0，**step2 cos 崩到 0.625**，step4 分歧
  （cache=39 vs nocache=87）——与 int8 分歧步完全一致。
- 交叉喂实验：cache 分支＋**no-cache 分支吐的 present**＋单 token → logits 与全量
  no-cache cos=1.00000 argmax 一致（cache 分支**消费**正确 past 没问题）。
- present 对比实锤：同前缀同空 past，use_cache_branch=True 吐的 present 与 False 吐的
  **encoder KV 形状都不一样**（True→(1,16,196,64)，False→(0,16,1,64) 空张量），
  decoder KV 数值 maxdiff 1.8；首步（1 token 空 past，两分支都应现算）同样差。
  → **merged 导出的 present 输出选择接线损坏**：cache 分支吐的 present 不可自喂，
  自喂必崩；no-cache 分支的 present 才是对的。int8/fp16 同一导出管线同一病灶。
- int8 no-cache 三题旁证：f01/f03/f10 全命中金标（2.1s/1.4s/1.7s）——两档权重与
  预处理本身都无错，错的只是 cache 分支 present。

### no-cache 全量重喂贪心＝两档全绿（施工口径）

| 题 | 金标 | int8 no-cache | fp16 no-cache |
|---|---|---|---|
| f01 | `\frac{a^2-b^2}{a+b}=a-b` | ✓ 26tok 2.1s | ✓ 26tok 6.8s |
| f03 | `\sqrt{12}=2\sqrt{3}` | ✓ 15tok 1.4s | ✓ 15tok 4.6s |
| f10 | `\sin^2\alpha+\cos^2\alpha=1` | ✓ 21tok 1.7s | ✓ 21tok 5.6s |

输出均带 `$$…$$` 包裹（texify 训练口径），引擎尾部 latex_norm.clean 归一。

## 5 早判结论与选档

- int8＋卡§3 规定的 past KV 贪心＝坏（早判门红）→ 按卡准显性换 fp16 一次。
- fp16＋past KV＝同症坏；根因＝两档 merged 导出共有的 cache 分支 present 接线损坏
  （上节实锤），非本机环境/非量化/非预处理/非解码。
- **选档 fp16（~628MB 六件）＋no-cache 全量重喂贪心**：encoder 一次，decoder 每步
  use_cache_branch=False＋空 past＋全前缀重喂，argmax 到 eos/帽。公式裁图 token 短
  （实测 15–26），fp16 CPU 单题 4.6–6.8s，可以慢不能不稳。
- 不偷换不降级：输出与正解逐字一致，只是放弃损坏的 cache 加速路径；偏离显性登记（§6）。
- catalog/UI 成本活字随选档改 ~628MB（fp16 六件），许可告知三处不变。

## 6 偏离登记

1. 卡文「▁ metaspace 还原空格」与实物不符：tokenizer.json decoder＝ByteLevel（Ġ 件
   31928／▁ 件 0 实测），解码照实物 ByteLevel 口径（p2t 同族），零新依赖不变。
2. generation_config 无 max_new_tokens：生成帽取 config decoder.max_position_embeddings=1536。
3. **int8 早判红→换 fp16（卡准路径）**；且 fp16 的 past KV 也坏（merged 导出共有
   结构病灶，present 对比实锤），施工改 **no-cache 全量重喂贪心**——偏离卡§3「past KV」
   字面规定，但两档 KV 均不可用、no-cache 两档全绿，属卡§8 之外的可施工偏离，显性登记不偷换。
4. fp16 仓无 ort_config.json（404 实测）：fp16 变体＝六件（两 onnx＋四小件），
   卸载确认文案「六件」。
5. store 命名取 `formula_texify`（卡字面 store=texify）：照 registry formula_ 前缀
   先例（formula_l/formula_p2t），removeprefix 后 variant=texify，就绪真跟座权重走，
   卡意图满足。
6. 基线已知红一案（tests.test_ingest_triage 单题截图 seen_names 空）非本卡回归，
   零触 MinerU 路，不治不混，回单照挂。
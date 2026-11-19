# 2.20.0 侦查结论（人话版）

侦查时间 2026-11-19，本机实测。机读结论 recon.toml；原始读数 recon-run.txt；
Vulkan wheel 与 llama-server --help 全文同目录。**未发起任何安装，出网只读取证。**

## 结论一句话

无停链条件：冻结面有原地接线先例、国内源非全不可达、注册表显存真值可取。
唯一硬欠账＝llama-cpp-python CUDA/CPU 轮国内零 wheel（GitHub 独有）→ 按卡§4/§9
显性 gate_note＋欠账；A 卡 Vulkan 路与 CPU 路都有国内可达替代（mineru-llama-cpp wheel）。

## §3 显存真值（已核实）

- 注册表 HKLM\...\Class\{4d36e968-...}\0003「AMD Radeon RX 5600 XT」
  HardwareInformation.qwMemorySize = 6,425,673,728（64 位）→ 5.98G → 标签 6.0G。
- 同卡 WMI AdapterRAM = 4,293,918,720（32 位上限约 4G）——现 probe 读 4.0G 的成因。
- 其余适配器（0000/0002 OrayIddDriver/0004+0005 远程显示）全无 qw 值 →
  多卡取主卡＝有 qw 值的物理卡优先，虚拟适配器跳过，全缺回 WMI 不报错。
- 修后 vlm_qwen min_vram=6 门转就绪；registry 源不再叠「WMI 上限约 4G」句；不加 override。

## §4/§7 安装链（已核实）

- pip 四镜像今日全 200：阿里 90ms／清华 157ms／腾讯 375ms／中科大 465ms
  （延迟现算，安装点击内并行测速选最快，不写死名次）。
- **llama-cpp-python 四家全只有 sdist、零 wheel** → CUDA 轮国内不可达（卡面预料之中）；
  CPU 轮也 GitHub-only。处置：CUDA 轮显性 gate_note＋欠账；CPU 路径改走
  mineru-llama-cpp 自带 llama-server `-ngl 0`（偏离记回单）。禁 GitHub 静默兜底。
- A 卡路稳：mineru-llama-cpp==0.2.3 win_amd64 wheel 国内可下（19,547,120B，
  sha256 78adc79a…已核），自带 Vulkan llama-server 0.6.0-dev build 86a2835，
  --mmproj/-ngl/--api-key/--jinja/--ctx-size 全支持；engines/mineru 已有 0.2.1
  现成 Vulkan 栈可迁移（engines 内迁移不算出网）。
- vlm_service.py:106-113 现用 `python -m llama_cpp.server --n_gpu_layers 0`＝
  纯 CPU 陷阱本体 → 改起 llama-server.exe（Vulkan -ngl 999／CPU -ngl 0）。
- 权重源：modelscope 386ms／hf-mirror 1339ms／gitcode 首页 788ms；GGUF 两文件
  modelscope 200 可达（T6 已装成，字节数/sha256 沿用 vlm_setup 现值）。

## §6 RapidOCR 准档（已核实）

- rapidocr 3.10.0 在底座 .venv；engines/rapidocr 是无人引用的平铺副本，不用它。
- medium 档包原生支持：params Det/Rec.model_type='medium'（ocr_version 默认 PP-OCRv6）。
- 权重 modelscope 国内源（包内置通道同款 URL）：det_medium 62,119,454B／
  rec_medium 76,629,984B，各带 SHA256；GET Range 206，310ms/256ms。
- 落点 engines/ocr/models/（不污染 .venv），RapidOCR 以 model_path 指入；
  catalog rapidocr_accurate blocked→weight_present＋安装钮；3 样本 bench
  安装走 UI 点击、bench 离线跑。升默认不在本卡。

## §2 重新识别（已核实）

- **跨库查重已存在**（dedupe/engine.py DUPLICATE_REASONS=batch+bank，
  bank_rows_snapshot＋group_duplicates 升级库命中）→「只批内则补跨库一小刀」
  条件不成立，不补刀，结论记回单。
- 打回动线：批次行新按钮（组合进 plugin.js:291 renderDeleteBatchButton 注入点，
  ui_batches.js 零改）→ 确认 → 新 API 兄弟读 source_backup＋meta → 未入库题随批
  作废、已入库留库 → 文件回收集框 → 老师重选链路（7 链路＋自动）→ ingest.files
  只跑一条。新按钮 stopPropagation（行点击白名单在 ui_batches 265-271）。
- 组合路三选项进识别下拉：catalog 新条目 plan_recognize=["combo"]＋combo_seat；
  纯图卷灰＋人话（ui_intake.js 656 台账冻结，经 applyRegistry/decorate 接线）。

## §1 冻结面接线点（已核实先例）

- index.html 870 行单 script → 同行挂兄弟（先例 895 行两 script 一行）；
  CSS 18 行同理（先例 27 行两 link 一行）。898 帽不增。
- plugin.js 325 行追加创建先例；291 行组合注入先例。828 帽不增。
- PluginAssetWiringTest 正则按行扫，多 script 一行可过；命名空间先建后用须守序。

## 停链判定

卡§9 四条停链条件逐条对：冻结面接得进（先例在）／国内源非全不可达（pip 四家＋
modelscope 全绿，仅 CUDA 轮单点不可达＝卡面预料的 gate_note＋欠账，非停链）／
registry 刀可绿（真值已取）／打回语义可接线（source_backup 资产在）。**继续动刀。**
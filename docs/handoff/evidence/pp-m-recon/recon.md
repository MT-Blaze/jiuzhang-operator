# PP-FormulaNet·M 单座侦查证据（2.22.0 卡 §1）

日期：2026-11-19 ｜ 会话：54c57168（枢纽 4a0d74c0 委派）｜ 基线：operator 33161f6 ／ plugins 87e1729（2.21.0）

**结论：放行（GO）。** 许可证白名单内、国内源可达、零新依赖 ONNX 路、CPU 秒级（0.76–1.20s/块），无停链条件。

## 1. 许可证链（白名单 Apache/MIT/BSD/ISC 内）

| 件 | 出处 | 许可证逐字 | 取证方式 |
|---|---|---|---|
| 原始权重 | ModelScope `PaddlePaddle/PP-FormulaNet_plus-M` | `"License":"apache-2.0"` | modelscope API `/api/v1/models/PaddlePaddle/PP-FormulaNet_plus-M` |
| ONNX 转换件＋yml | ModelScope `RapidAI/RapidDoc` | `"License":"Apache License 2.0"` | modelscope API `/api/v1/models/RapidAI/RapidDoc` |

RapidDoc 为 RapidAI 官方托管仓（与 2.20.0 准档 RapidOCR ONNX 同先例）。GitHub 禁足未直读，项目 Apache-2.0 由搜索摘要佐证。

## 2. 国内三源实测（curl range GET 验内容，非只看状态码）

- **modelscope：可达。** resolve 302→CDN LFS，206＋`Content-Range: bytes 0-15/593908338`，ONNX protobuf 魔数 `080a` 真文件。两件 sha256 与远端登记逐字一致（见 weights.toml）。
- **hf-mirror：不可用。** `RapidAI/RapidDoc` 无此仓库（resolve 真 404）；对照 `RapidAI/RapidOCR` det 得 429 限流，证明站本身活着、非网络问题。
- **gitcode：不可用。** 无 RapidDoc 仓库；resolve/raw 返回 200 但 `Content-Type: text/html`（3575 字节页面），range GET 识破「200 假可达」。

唯一可达≠全不可达，不停链。安装链复用 `mirrors.race`，单源退化。

## 3. 运行栈选型：ONNX 路，零新依赖

- 官方 ONNX 存在（RapidAI 转换官方权重）→ 按卡优先 ONNX＋底座现成 `onnxruntime==1.32.0`，**无需环境轮子、无需 paddlepaddle CPU 轮侦查**。
- 权重两件一键落 `engines/formula/models/`：onnx 593,908,338 字节＋yml 2,244,564 字节（合计约 596MB，确认弹窗成本活字现算）。
- yml 内嵌完整 tokenizer（`fast_tokenizer_file`：BPE vocab 50000、merges 49721、byte_fallback=False、ByteLevel 解码器、NFKC 归一化、TemplateProcessing `<s>A</s>`；`tokenizer_config_file`：eos `</s>` pad `<pad>` bos `<s>`），**无需另下词表**。

## 4. I/O 形状（onnxruntime 实测）

- 输入 `x`：`[B,1,384,384]` float32（灰度单通道）。
- 输出 `fetch_name_0`：`[B,seq]` int64 token ids；自回归循环已在图内，贪心解码，max tokens 2560。
- 加载 3.0s；大量 `Removing initializer … not used` 警告为 paddle2onnx 导出残留，无害。

## 5. 预处理口径（paddlex 3.7.2 Apache-2.0 源码侦查，只读算法口径、落笔原创实现，守干净房间）

源码：`.system_generated/pp-m-recon/wheels/paddlex_src/paddlex/inference/models/formula_recognition/`（predictor.py:105-107 PP-M 走 UniMERNetImgDecode→UniMERNetTestTransform→LatexImageFormat）。

1. `crop_margin`（processors.py:425-443）：灰度 min-max 拉伸→阈值 `<200` 取墨迹→`cv2.boundingRect` 裁边。
2. 短边 resize 到 384（processors.py:498-517，BILINEAR resample=2）→`thumbnail((384,384))` 只缩。
3. `ImageOps.expand` 居中补边 fill=0（黑）到 384×384（processors.py:535-549）。
4. 归一化 `(x/255−0.7931)/0.1738`（processors.py:954-960）；三通道等值→取灰度通道。
5. `LatexImageFormat`（processors.py:210-227）：补 16 倍数边 constant 1（384 已整除无操作）→`[1,1,384,384]`。

## 6. 解码口径（processors.py:812-899）

1. 截断首个 `id==2`（`</s>`）含尾（token2str:823-826）。
2. `skip_special_tokens`：added_tokens id 0–22 全跳过。
3. ByteLevel 解码：GPT-2 字节逆映射→拼字节→UTF-8。
4. 后处理：`remove_chinese_text_wrapping`（`\text{中文}` 解包＋去引号，:876-883）→`normalize` 空白压缩正则循环（noletter=`[\W_^\d]`、letter=`[a-zA-Z]` 三条规则迭代至稳定，`\operatorname/\mathrm/\text/\mathbf` 保护，:833-874）。
5. **ftfy `fix_text` 不引入**（偏离登记：底座无此依赖、零新依赖优先； mojibake 修复缺位，真实公式输出未见受影响）。

## 7. 夹具（5 块真卷公式裁图，fixtures/）

来源：东北师大附中2023-2024高一上学期第一次月考（纯图卷，`.system_generated/model-config-card/data_final/pending_sources/`）。三份候选真卷均无文字层（chars 0/1），改走 RapidOCR·快行框＠300dpi 裁数学密度≥0.95 的纯公式行。清单见 fixtures/fixtures.toml，裁取脚本 make_fixtures.py、推理脚本 recon_infer.py 同目录可复跑。

## 8. CPU 耗时真测（timing.toml）

5 块全 eos 正常、LaTeX 合理：**0.76–1.20s/块，秒级**，非分钟级，按卡 §0 继续。f5 模型认出 OCR 丢掉的 `\frac{1}{2}`——专科比通用 OCR 稳的实证。

## 9. 偏离与风险登记

- ftfy 不引入（见 §6.5）。
- 基线 test_command_registry test_29 先存红：EXPECTED editor "2.20.0" 实际 "2.21.0"（2.21.0 封版漏更测试）；parity 阶段改 "2.22.0" 顺带修实。
- `recognize/formula.py` 已 390 行近 400 帽：PP-M 引擎适配器放新兄弟文件 `recognize/formula_pp_m.py`（≤400），formula.py 只补 dispatch 分支数行。
- 纯图卷组合路显性拒绝口径已在 router.py:165-169 就位，本卡不动。

## 10. 接线方案（下一步）

- 安装链：新兄弟 `app/core/ingest/formula_setup.py`（仿 ocr_setup 188 行先例）；API `/api/models/formula/{status,install,uninstall}`；relay `models.formula_install/formula_status/uninstall_formula` 补 stage_command.js:65 一行＋分发分支；catalog 只改 formula_pp_m 一条（rule=weight_present store="formula" 三态，仿 _ocr_medium_verdict）。
- 推理：`recognize/formula_pp_m.py` 引擎（_ENGINES 缓存＋reset，仿 ocr.py）；formula.py dispatch 补 `formula_pp_m` 步骤分支；catalog PP-M 补 plan_recognize=["formula_pp_m"]；输出过记号标准字典闭集口径。
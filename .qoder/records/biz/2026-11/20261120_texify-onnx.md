# 业务记录 · Texify 社区 ONNX 接线卡④（公式专科 formula_texify＋combo_texify）

【状态】 已发布
【发起日期】 2026-11-20
【需求名】 texify-onnx
【交付版本】 editor 2.25.0（底座 11e8b97→863f746 ／ 插件 0841ccd，两仓不 push hold）

## [REQ] 2026-11-20

背景：公式专科第四座 Texify 社区 ONNX 干净房间接线（零 torch/tokenizers/sentencepiece
新依赖），复用底座 onnxruntime；int8 主档早判红→卡准 fallback fp16（Spedon/texify-fp16-onnx，
cc-by-sa-4.0 权重内容许可＝署名＋相同方式共享，告知三处：安装弹窗＋catalog 文案＋回单）。
验收：catalog formula_texify blocked→ready＋combo_texify（weight_present 真随座权重）；
隔离副本 UI 真点安装六件 sha256 逐字；微批 3–5 公式裁图原位替换＋整题显性拒绝；
与 pp_m/p2t 共享目录按件卸载互不误删；擂台补腿主口径出数；零 JS 异常零 HTTP 失败收口孤儿零。
红线：65496 零接触、出网只 UI 真点＋国内镜像禁 GitHub、失败显性不偷换不降级、
MinerU/VLM CPU 停跑令、冻结面（LICENSE/铁律/question_contract/用户 data/）零触。
## [IMPL] 2026-11-20

涉及文件（底座仓，施工笔不 push）：
- `00cc547` §2 侦查＋CPU 早判门（recon.md：int8 KV 红换 fp16，merged 导出 cache 分支
  present 病灶钉死，no-cache 两档全绿定案）。
- `1e61cf2` §3/§4 引擎＋全链接线：`app/core/ingest/recognize/formula_texify.py`（≤400 行，
  ort CPU fp16 no-cache 贪心＋手写 ByteLevel 解码＋latex_norm.clean 闭集清洗）、
  `formula_setup.py` texify 变体六件按件装/卸、registry/API/relay/白名单/dispatch/reidentify
  照 p2t 先例接线；catalog formula_texify ready＋combo_texify；插件面 parity 四处＋zip 双建
  同哈希＋sync_plugin_index rc0，editor 2.24.0→2.25.0（插件笔 `0841ccd`，瞬态身份 MT-Blaze）。
- `11e8b97` 真测期三修：预处理改官方 do_thumbnail+do_pad（直缩压毁宽扁真裁图）、
  生成帽 _MAX_NEW=256＋达帽未收敛显性 ok=False（1536 是位置天花板非预算，no-cache 漫环
  约70分钟挂死）、探针微批换 C3 样卷＋`tools/texify_span_select.py` 只读公式形选块器。
- `863f746` §6 真测收口证据（probe run3 全绿＋run1/run2 trail＋擂台补腿 wire/渲染页/预处理擂台）。
使用 skill：sync-biz-record（本记录）、run-regression 口径（定向逐模块＋快门禁）、
prove-visual-change 口径（Playwright 穿沙箱真点）。

## [VERIFY] 2026-11-20

- 定向逐模块 unittest（禁 pytest/discover）7 模块 289 例全绿：test_formula_texify 18、
  test_formula_setup 63、test_models_registry 79、test_command_registry 35、
  test_recognize_router 26、test_formula_route 39、test_reidentify 29。
- 快门禁 check-quick-gate PASS（6 项全过，三查 fetch(/parent.document/localStorage=0）；
  体积 WARN 皆基线既有文件，本卡新增/触碰均≤450（引擎199/探针450/选块器40）。
- 真机探针 run3 全绿 ok=True checks=32 failed=0 elapsed=177.2s：UI 真点安装六件 sha256
  逐字、combo 随座双向、微批 3/5 原位替换、整题选 texify 显性拒绝、p2t 九件共存→按件卸载
  互不误删、零 JS 异常零 HTTP 失败、收口端口闭＋孤儿零。run1（微批挂死）/run2（hf-mirror
  读超时）trail 照挂 evidence/wire，run3 重下成功＝瞬态网络非代码缺陷。
- 擂台补腿（零出网 cloud_calls=0）：合成裁图 30/30 收敛、渲染 30/30、主口径精确 5/30=16.7%
  （f03/f04/f11/f14/f17，与 PP-M 5/30 同档）、参考口径 16/30=53.3%、sim_mean 0.7894；
  合成整题 4 题 ok=2 exact=0（公式座无整题契约，2 题达256帽显性失败）；真实印刷裁图 0/3
  达256帽显性失败＝能力欠账挂起非接线缺陷；跨座一致性无 ok 配对不编数。
- 红线自检：65496 零接触（探针隔离副本动态端口随机令牌）；出网只 UI 真点＋hf-mirror 禁
  GitHub；sha256 逐件校验；冻结面零触；onnx_probe.py 原地不 stage；engines 产物不 stage；
  两仓不 push；plugins 瞬态身份不写 git config。
- 基线已知红一案照挂：tests.test_ingest_triage MineruPerQuestionTest
  test_single_question_screenshots_not_the_whole_pdf（seen_names 空）＝提速①旧 mock，
  非本卡回归、零触 MinerU 路、不治不混。

## [RELEASE] 2026-11-20

- 交付版本 editor **2.25.0**：parity 四处一致＋zip 双建同哈希＋sync_plugin_index rc0；
  models/ 与 model_prefs.toml 不打包不触碰。
- 底座笔 00cc547→1e61cf2→11e8b97→863f746；插件笔 0841ccd。**两仓均不 push（主公明确
  不授权，hold）**；65496 现网零接触。
- **新座生效需主公再重启一次**（现网进程仍载旧引擎缓存/旧 catalog）；重启后模型配置中心
  见「Texify（公式专科）」与「文字直取+公式·Texify」，点【安装】下约 628MB fp16 六件。
- 许可告知：权重 cc-by-sa-4.0（署名＋相同方式共享）——个人/教研免费用，**商用或二次分发
  须遵官方相同方式共享条款**；安装弹窗＋catalog 文案＋回单三处已摆明。
- 遗留欠账：真实印刷裁图 0/3（达256帽显性失败）＝texify 能力边界挂起；中文 \text 弱
  （f20 sim 0.19）；基线已知红一案照挂；push hold 待主公授权。

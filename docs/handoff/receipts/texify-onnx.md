# 回传单 · Texify 社区 ONNX 接线卡④（公式专科 formula_texify＋combo_texify，2.25.0）

【回执编号】 #TEX-01
【回执时间】 2026-11-20T16:21:03+08:00
【实际耗时】 约 2 小时 40 分（§2 侦查收口 13:41:25 → 本回单 16:21:03，系统钟实测；含两次上下文压缩接力、三轮真机探针与擂台补腿真测）
【执行结果】 成功（卡§0–§9 全范围落地；§6 真测探针 run3 全绿 32/32＋擂台补腿出数；真实印刷裁图能力欠账显性挂起，非接线缺陷）

正文逐条对齐卡§0–§9 与不动面；biz 记录见 `.qoder/records/biz/2026-11/20261120_texify-onnx.md`
（sync-biz-record：REQ/IMPL/VERIFY/RELEASE 四阶段 append-only）。
基线：底座 `d2f9b26` ／ 插件 `e6569ce`（editor 2.24.0），坐在其上施工，不卷动、不 amend、
**两仓均不 push（主公明确不授权，hold）**；65496 现网（PID 17136）零接触。
交付版本 **2.25.0**（parity 四处一致＋zip 双建同哈希＋sync_plugin_index rc0）。

## 一 【改动清单】

底座仓（E:\jiuzhang\jiuzhang-operator，d2f9b26 → 863f746，四笔不 push）：
- `00cc547` §2 侦查＋CPU int8 早判门：int8 KV 红→卡准 fallback fp16；merged 导出 cache
  分支 present 接线病灶钉死（自喂必崩），no-cache 两档全绿定案；recon.md 存档。
- `1e61cf2` §3/§4 引擎＋全链接线（15 文件）：`recognize/formula_texify.py`（199 行≤400，
  ort CPU fp16、encoder 一次＋decoder no-cache 全前缀重喂贪心、手写 ByteLevel 解码、
  latex_norm.clean 闭集清洗、未安装/坏图/推理失败全显性）；`formula_setup.py` texify 变体
  六件按件装/卸共享 engines/formula/models/；registry/API/relay/白名单/dispatch/reidentify
  照 p2t 先例接线（registry/router 零代码改）；catalog formula_texify blocked→ready＋
  combo_texify（capability=recognize、plan=["combo"]、combo_seat=formula_texify、
  rule=weight_present 真随座权重）；名称「Texify（公式专科）」「文字直取+公式·Texify」。
- `11e8b97` 真测期三修（5 文件）：预处理改官方 do_thumbnail+do_pad；生成帽 _MAX_NEW=256＋
  达帽未收敛显性 ok=False；探针微批换 C3 样卷＋新增 `tools/texify_span_select.py`（40 行
  只读公式形选块器）＋`tools/texify_live_probe.py`（450 行）；recon.md §7 append 改正。
- `863f746` §6 真测收口证据（19 文件）：probe run3 全绿 toml＋10 截图＋run1/run2 trail＋
  预处理五解释擂台输出＋擂台 texify_synth.toml＋渲染页×2。

插件仓（E:\jiuzhang\jiuzhang-plugins，e6569ce → 0841ccd，一笔瞬态身份不 push）：
- `0841ccd` §4 插件面（6 文件）：catalog/parity 四处＋zip 双建同哈希＋索引同步，
  editor 2.24.0→2.25.0；commit 用 `-c user.name=MT-Blaze -c user.email=tianxiulaoshi@163.com`
  瞬态身份，绝不写 git config。models/ 与 model_prefs.toml 不打包不触碰。

## 二 【真测与擂台证据】

真机探针（Playwright 穿沙箱，隔离副本 git archive HEAD＋动态端口随机令牌＋data/plugins
全隔离；出网只配置中心【安装】真点＋确认弹窗 accept 发起，hf-mirror 主源禁 GitHub）：
- **run3 全绿 ok=True checks=32 failed=0 elapsed=177.2s**：未安装三态＋375px 不溢出；
  628MB＋cc-by-sa-4.0 弹窗 accept→POST 真请求→六件 sha256 逐字落地→就绪＋【卸载】＋
  combo_texify 随座就绪；微批 5 目标真跑 **3/5 原位替换存回**（2 块坐标保护显性拒裁
  「坐标落在题图外或太小」、1 块 CJK 混裁幻觉替换——能力 finding 非接线缺陷）；整题选
  texify 显性拒绝（「公式专科座只认裁图…请选整题座」）；p2t 118MB 顺带装→九件共存→
  卸 texify 只删六件保 p2t 三件与就绪态→卸 p2t 目录删净→combo 随座回未就绪；
  三查 0、零 JS 异常、零 HTTP 失败、收口端口复验闭＋孤儿零。
- 过程账：run1 微批挂死（直缩压毁宽裁图＋1536 漫环约70分钟＋宿主写串行排队）→引擎三修；
  run2 hf-mirror 读超时（encoder 151MB 两次）→run3 重下成功＝瞬态网络非代码缺陷。
  trail 存 evidence/wire/probe_run1_microbatch_hang.toml、probe_run2_mirror_timeout.toml。

擂台补腿（直调引擎零出网 cloud_calls=0；权重＝侦查 sha256 核过 fp16 六件入隔离副本；
latex_norm.db 复制补腿四座同源副本保主口径字典一致）：
- 合成裁图 30：**30/30 收敛、渲染 30/30**；主口径（双方 latex_norm.clean(compare=True)
  逐字）精确 **5/30=16.7%**（f03/f04/f11/f14/f17，与 PP-M 主口径 5/30 同档）；参考口径
  （supp_norm，非主口径）16/30=53.3%；sim_mean=0.7894。弱项：中文 \text（f20 sim 0.19）、
  分段/矩阵多行结构。
- 合成整题 4：ok=2、exact=0、sim_mean=0.4024（公式座无整题 JSON 契约；q1/q4 达256帽
  显性失败＝整题图非公式裁图预期红）。
- 真实印刷裁图 3（vlm-micro 存档同源）：**0/3 产出，三块皆达256帽未收敛显性失败**＝
  texify 真实印刷能力边界，欠账挂起非接线缺陷；跨座一致性无 ok 配对 consistency=[] 不编数。
- 明细：evidence/wire/texify_synth.toml、render_texify_crops.html、render_texify_whole.html；
  报告 append「texify 补腿」章节于 .system_generated/arena/report.md（主卡正文零触）。

测试与门禁：定向逐模块 unittest 7 模块 **289 例全绿**（formula_texify 18／formula_setup 63／
models_registry 79／command_registry 35／recognize_router 26／formula_route 39／reidentify 29）；
快门禁 check-quick-gate **PASS（6 项全过，三查 0）**；体积 WARN 皆基线既有文件，本卡
新增/触碰均≤450（引擎199／探针450／选块器40／单测283）。

## 三 【偏离登记】（显性，不偷换不降级）

1. **no-cache 全前缀重喂贪心**（偏离卡§3「past KV」字面）：int8 与 fp16 两档 merged 导出
   cache 分支 present 接线均损坏（自喂必崩，recon 实锤），no-cache 两档全绿；输出与正路
   逐字一致，只是放弃损坏的 cache 加速路径。可以慢不能不稳。
2. **int8 早判红→换 fp16 主档**（卡§1 显式 fallback 条款触发，一次换定不反复）。
3. **ByteLevel 解码**（卡文「▁ metaspace」与实物不符）：tokenizer.json decoder＝ByteLevel
   （Ġ 件 31928／▁ 件 0 实测），照实物口径手写解码，零新依赖不变。
4. **fp16 六件无 ort_config.json**（404 实测）：卸载确认文案「六件」。
5. **store=formula_texify**（卡字面 store=texify）：照 registry formula_ 前缀先例，
   removeprefix 后 variant=texify，就绪真跟座权重走，卡意图满足。
6. **生成帽 256＋达帽未收敛显性失败**（改正 recon §6 偏离2 的 1536）：1536 是位置嵌入
   天花板非生成预算；no-cache 步耗随序列线性涨（step250=113s，1536 漫环约70分钟挂死
   单题重认）；256 最坏约2分钟＜UI 15分钟窗；旧版达帽静默返回漫环＝隐性失败已修。
7. **预处理改官方 do_thumbnail+do_pad**（改正 recon §2「直缩吐字正确」）：直缩只在近方形
   金标成立，真宽扁裁图字形压毁吐 \bigstar 漫环；五解释×9图擂台实证保比例补0左上真图
   收敛吐字正确且金标 f01/f03/f10 零回归。
8. **微批样卷换 C3＋公式形选块器**（A3 charbox 退化整行 6120×30px 长条不是公式图）：
   C3 全页普查 54 个公式形 span；选块器按单行/无汉字/宽60–700/高≥20/宽高比1–12 滤。
9. **p2t 118MB 顺带装拆**：只为共享目录按件卸载互不误删真证，非 p2t 座重复验收。
10. **prefs auto_image_seat=cloud_vision（未指派）**：组合路无坐标整题兜底走显性失败，
    避 MinerU/VLM CPU 停跑令；零引擎零出网。

## 四 【遗留欠账】

- **真实印刷裁图 0/3**（达256帽显性失败）＝texify 能力边界挂起；干净合成裁图稳、真实
  印刷弱；中文 \text 弱（f20 sim 0.19）。待更强公式档/裁图质量提升再补腿。
- 微批 2/5 坐标保护显性拒裁＋1/5 CJK 混裁幻觉替换＝文字层 charbox 质量与混裁问题，
  非本卡接线缺陷（D12 定位保护照旧显性）。
- **基线已知红一案照挂**：tests.test_ingest_triage MineruPerQuestionTest
  test_single_question_screenshots_not_the_whole_pdf（seen_names 空）＝提速①旧 mock，
  非本卡回归、零触 MinerU 路、不治不混。
- **push hold**：两仓均不 push，待主公授权。
- **新座生效需主公再重启一次**（现网进程仍载旧引擎缓存/旧 catalog）。

## 五 【红线自检与不动面】

- 65496 零接触（现 PID 17136 禁擅自重启/杀）；探针隔离副本动态端口随机令牌，收口端口闭＋孤儿零。
- 出网只隔离副本 UI 真点发起＋国内镜像 hf-mirror 禁 GitHub；sha256 逐件校验逐字一致。
- 零新依赖：不装 torch/tokenizers/sentencepiece；复用底座 onnxruntime；干净房间手写底座
  代码，不抄 texify/Surya（Surya GPL 不追不装）、不碰 Xenova/texify（无许可证）。
- 许可 cc-by-sa-4.0（署名＋相同方式共享）告知三处：安装弹窗＋catalog 文案＋本回单；
  **个人/教研免费用，商用或二次分发须遵官方相同方式共享条款**。
- 失败显性不偷换不降级：未安装/坏图/推理失败/达帽未收敛/坐标拒裁全 ok=False 进失败账本。
- 冻结面零触：LICENSE/铁律一二/question_contract.py/用户 data/ 禁改；onnx_probe.py 原地
  不 stage；engines 产物不 stage；禁 JSON 落盘（证据走 toml/html/png）；分层≤3；
  records append-only；冻结台账只减不增。
- 微批 3–5 定死（run3 真跑 5 目标 3 替换）；不赌参数（预处理/生成帽皆擂台实证后定）。
- 测试只 `.venv\Scripts\python.exe -m unittest tests.<模块>` 逐模块（禁 pytest/discover）；
  Playwright 穿沙箱；新探针禁写死端口/令牌；无官方换算比不编积分数（cloud_calls=0）。
- 无人值守：偏离记回单（§三）、真卡死停链登记（run1 挂死根因三层实证后修实再跑，未偷换）。
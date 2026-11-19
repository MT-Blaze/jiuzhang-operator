# 记号标准字典（闭集＋开集）· 2.21.0

- 状态：已发布（本地封版 2.21.0；两仓 push 待主公授权 hold）
- 发起日期：2026-11-19（主公点头「那这个就开干吧」＋术语纠正「不是B级 是闭集 和开集」）
- 任务卡：E:\jiuzhang\记号标准字典闭集开集任务卡.md
- 基线：底座 830ca19 ／ 插件 af7884d（2.20.0）；交付 2.21.0 四处 parity＋zip 确定性双建同哈希

## [REQ] 2026-11-19

背景：AI 写进源码栏的公式要全局统一写法（pipeline 第 49 条），原写法字典是冻结常量表，
老师不能选默认字形、非标/OCR 误识没有收编入口。本卡把它升成「闭集＋开集」整机字典。

验收标准（卡 §0–§7）：
- 整机级 data/latex_norm.db 三表（norm_entries/norm_variants/norm_corrections），不随工作区漂移；
  闭集出厂冻结、老师只写 chosen_default_variant_id；开集四态人闸只有 confirmed 参与改写。
- 闭集种子 TOML 全量（一符号一条目、单形式也占行），来源标签只到标准族级；导入四保险；
  MathJax 逐条渲染探针，不认显性 render_supported=0 不静默丢。
- 清洗改字典驱动：clean_for_write＝闭集选中默认＋开集 confirmed；normalize_for_compare 同口径；
  三硬规矩（按命令切词/幂等/不认识就不动）保留；老模块 latex_style_dict.py 冻结 506 只减不增。
- 台账第 49 条修订：unknown 进开集待审、老师裁（仍不打印不进日志）。
- norm.* Host API＋字典族 UI 五列＋开集待审区；整机生效徽标；375px 零横溢、键盘可达。
- 学科不分类（唯一轴＝记号族）；字典不进任何模型提示词＝零 token；产品运行时零出网；本卡零引擎跑。
- 稳定性：可以慢不能不稳；微批 3–5；两仓不 push；不绿不 commit。

## [IMPL] 2026-11-19

阶段C：清洗字典驱动接线＋台账第 49 条修订。

台账第 49 条修订（主公已点头）：原硬条件③「不认识就不动，原样保留并记录」配套的
「unknown 清单不落盘不打印不进日志」改为「unknown 候选写 norm_corrections(pending)、
交老师开集裁决」；仍不打印、不进日志。模块 docstring 已同步
（latex_style_dict.py 硬规矩③、latex_norm.record_unknown）。

涉及文件（底座，行号为改后）：
- app/core/content/latex_norm.py（450，≤450）：新增清洗驱动 clean(text, compare=False)——
  闭集 rewrite_aliases()＋开集 confirmed_corrections() 合并、传递闭包保幂等，交老模块切词改写；
  写路 unknown 送 record_unknown(pending)，比对路只归一不登记。按 (库路径, 写代数) 进程内缓存，
  写口全在 transaction() 提交后 bump 代数即失效——查重扫描热路成千上万次比对只首查开库，
  修掉逐次开库拖垮后台初查线程的不稳定（test_pending_dedupe_scan 由 27s+ 超时回 3s 绿）。
- app/core/content/latex_style_dict.py（506 冻结持线）：clean_for_write/normalize_for_compare/
  _rewrite/_rewrite_span 原地「字典从参数取」（aliases 参数，默认 None 回落 SYMBOL_ALIASES 基线）；
  硬规矩③ docstring 同步台账 49 修订。
- app/core/content/question_parser.py（481）：:19 import latex_norm；:166/:243 清洗交 latex_norm.clean。
- app/core/ai/recognition/recognize.py（364）：:25 import；:124 识别后清洗交驱动。
- app/core/bank/engine/dedupe_signature.py（540）：:27 import；:48 _compare_form 交驱动 compare=True（指纹受益）。
- tests/test_latex_norm.py：新增 NormCleanDriverTest 八案（字典驱动/选择翻转缓存常新/normalize 同口径只读/
  三硬规矩/unknown 进待审仅写路/confirmed 改写 pending 不生效/传递闭包幂等/空库回落基线），全模块 37/37。
- tests/test_latex_style_dict.py：HostChainTest 加 JZO_DATA_DIR 未播种隔离，向后兼容断言确定性走基线，30/30。

使用的 skill：add-data-store（阶段A 整机库动线）、sync-biz-record（本记录）。

复跑沾到模块全绿：test_latex_norm 37、test_latex_style_dict 30、test_question_parser 47、
test_clean_latex 13、test_bank_dedupe 21、test_dedupe_fingerprint 38、test_ai_recognize 18、
test_recognize_router 24、test_pending_dedupe 14、test_pending_dedupe_candidates 20、
test_pending_dedupe_scan 18、test_cleanup_tools 15。

## [IMPL] 2026-11-19 (2)

阶段D：norm.* Host API＋宿主 relay 转发族＋字典族 UI 五列＋开集待审区。

Host API 动线（add-host-api 七跳逐跳落点）：
- core 写入函数已在阶段A/B/C 落（app/core/content/latex_norm.py）。
- api 层 app/api/norm.py（98，新建）：GET /api/norm/entries（闭集条目＋变体＋effective_default）、
  GET /api/norm/corrections?status=（开集候选＋四态计数）开放读；POST choose/reset/decide 一律
  Depends(require_write_token)，NormError 翻 HTTPException(400, {code:"norm_error", message})。
- 挂载 app/main.py：include norm_router；lifespan 加 _seed_latex_norm() 启动种子自举（幂等补差、
  失败不挡底座、清洗回落冻结基线），照 _ensure_bank_engine 容错先例。
- 宿主 relay 白名单原地同线补：static/js/stage_command.js（545 冻结持线）L75 dict.* 行尾追加
  norm.list/choose/reset/corrections/decide；static/js/stage.js（776 冻结持线）同线挂
  JzoStageRelayNorm.create＋families 数组追加 relayNorm；新族 static/js/stage_relay_norm.js（120）
  照 stage_relay_io.js relayMeta 先例：读 questions:read、写 questions:write＋withWriteToken，
  错误码复用现有 BAD_REQUEST/FORBIDDEN（不新增码集），HTTP 错走 fail→HOST_<status>。
- workspace.html 挂 stage_relay_norm.js（先于 stage.js，命名空间先定义后使用）。
- 单测 tests/test_norm_api.py（8 案，起 uvicorn 设 JZO_RESTART_DISABLED=1＋隔离 data/plugins＋
  随机端口＋静态令牌）：entries 223/8 族/4 标签/le 默认 leqslant、写 401、choose 翻转＋reset、
  choose 拒外族/缺失/非整、unknown 经 clean_latex 进 pending、confirmed 须目标＋改写、rejected 黑名单、
  decide 只 pending＋合法动作。8/8 绿。

字典族 UI（宿主同源 DcClient，不经沙箱 relay；整块可下架）：
- catalog.js 加第四分类 notation（machine:true，subs mode:"norm-dict"）；panels.js renderSub
  加 norm-dict→DcNormDict.mount 分支、看板卡 machine 分类显「整机生效·闭集＋开集」不显行数；
  sidebar.js 导航按钮 machine 分类挂「整机生效」徽标。
- norm_dict.js（266，≤450）：闭集五列（①记号族筹码过滤 ②名称 ③各来源代码行＋标签筹码
  ④逐行对齐 MathJax 渲染 ⑤默认单选）＋名称/代码搜索＋每条目恢复出厂（DcDialog 确认，焦点陷阱/Esc/归位）。
  公式经 JzoMath.render 取 SVG 串再 DOMParser 落节点，绝不拼 innerHTML（控制台红线）；
  render_supported=0 显性降级源码＋render_note，不静默丢。
- norm_inbox.js（200）：开集待审第二块＋计数徽标，pending 命中倒序（接口已排），原始 vs 收编后
  双渲染对照，目标代码输入即时预览，收编（confirmed 须目标）/驳回（rejected 黑名单，DcDialog 确认）。
- dict_console_norm.css（248，<450）：复用 app.css 主题变量，五列 minmax(0,1fr) 网格防溢出、
  公式格内部横滚、375px 窄屏入口头与对照格堆叠；状态不只靠颜色（筹码加粗＋描边＋aria-pressed）。
- dict_console.html 挂本地 MathJax（jzo_mathjax.js＋tex-svg-full.js，离线）＋norm css＋两 norm 模块。

真浏览器冒烟（隔离自播种服务，动态端口 1320＋随机令牌，browser-use 真 DOM 点击）：
223 条目/8 族筹码/五列头/231 个 mjx-container 渲染、待审徽标「待审 1」＋zqsmoke 行、两处整机生效徽标、
零控制台报错；过滤「关系不等」→19 条全族一致；le 选默认 42→43→恢复出厂回 42（对话框确认）；
开集收编 zqsmoke→leqslant：预览渲染出现、按钮启用、confirmed=1/pending=0、行移除；
clean_latex 实测「$\zqsmoke$ 且 $\le x$」→「$\leqslant$ 且 $\leqslant x$」（changed=true，开集 confirmed＋闭集默认双驱动）。
像素截图与 375px 量测留阶段E 正式探针（in-app 浏览器需可见 surface）。

契约复跑全绿：test_command_registry 35、test_ai_plugin_boundary＋test_clean_latex 21、
test_file_size_contract 13、test_dict_console＋test_dict_console_subtabs 31、test_norm_api 8；快门禁 PASS（6 项，ERROR 0）。
冻结面持线：stage.js 776、stage_command.js 545；新文件均 ≤450（norm_dict 266/inbox 200/css 248/relay 120/api 98）。

使用的 skill：add-host-api（norm.* 动线）、sync-biz-record（本记录）。

## [IMPL] 2026-11-19 (3)

阶段E：测试全案＋三支探针＋2.21.0 封版 parity。

- 修阶段D 真缺陷：norm_dict.js（267，≤450）恢复出厂 onConfirm 旧 `.finally(busy(button,false))`
  把 syncDefault 设的 disabled=true 冲掉，致回出厂后键仍误启用；改为成功交 syncDefault 掌管禁用态、
  catch 才重新启用、finally 只清 aria-busy。探针②「确认恢复出厂键禁用」案钉住。
- 新增探针：tools/latex_norm_ui_probe.py（373）＋tools/latex_norm_clean_probe.py（244），
  动态端口＋随机令牌＋隔离副本，零引擎、零出网；Playwright 自带 chromium 真人路径（CDP 真点击）。
- parity：插件仓 plugin.toml:4／plugins.json editor／主仓 plugins.toml:51（sync rc=0）／包内 plugin.toml
  四处同版 2.21.0；zip 确定性双建同哈希 0982b4c4…691c（build1==build2，325.9KB）。
  插件仓 commit 87e1729 用 MT-Blaze 瞬态身份，只 stage plugin.toml/plugins.json/zip，
  model_prefs.toml＋models/ 原地 untracked 不碰。底座 parity commit d649fdf。

使用的 skill：prove-visual-change（探针②真浏览器取证）、build-release（parity＋双建＋包结构自检）、sync-biz-record（本记录）。

## [VERIFY] 2026-11-19

单测 19 模块 / 419 案全 OK（逐模块 `.venv\Scripts\python.exe -m unittest tests.<模块>`，禁 pytest/discover）：
latex_norm 37／latex_style_dict 30／norm_api 8／question_parser 47／clean_latex 13／bank_dedupe 21／
dedupe_fingerprint 38／ai_recognize 18／recognize_router 24／pending_dedupe 14／pending_dedupe_candidates 20／
pending_dedupe_scan 18／cleanup_tools 15／dict_console 14／dict_console_subtabs 17／file_size_contract 13／
ai_plugin_boundary 8／command_registry 35／version_consistency 29。
证据：docs/handoff/evidence/latex-norm-recon/phase-e-tests.txt。

快门禁 check-quick-gate.sh PASS（6 项全过，ERROR 0）；体积预警 23 份 451–550 行＝基线零新增。
冻结面持线：latex_style_dict 506／stage.js 776／stage_command.js 545／restore.py 532／st_backup.js 537。

三支探针（零引擎、零出网）：①渲染 e1 271/271（unsupported 0，端口 1994 闭合）；
②UI e2 18/18（五列＋整机徽章＋族过滤 19 条＋搜索＋choose＋reset 弹窗 Esc 焦点归位＋键禁用＋
开集收编/驳回＋375px 零横溢 family grid-column 1/-1＋零引擎/零 pageerror/零 4xx5xx/零 console 错；
端口 2416 port_closed=true；8 截图）；③清洗 e1 9/9（5 微批逐字命中＋幂等＋unknown 落 pending＋
choose/reset 往返＋rejected 黑名单永不改写；端口 2680 port_closed=true）。
证据：.system_generated/latex-norm/{render/e1,ui/e2,clean/e1}/。

三查 check-plugin-boundary.sh PASS（fetch(/parent.document/localStorage 各 0 命中、插件零 Python）；
check-plugin-index-parity.sh PASS（两份索引语义一致、版本一致、示例题过契约）。
标准核验浏览器真人路径：GB/T 3102.11-1993＋ISO 80000-2:2019＋前身链三跳全证（standards.toml）。

收口：本卡五端口 1994/2279/2416/2680/63533 复验全闭合、本卡孤儿零；
65496 正式服务与 2889 他会话残留（parent 已死、非本卡端口）未触碰。
两仓不 push（底座 ahead 28／插件 ahead 10）、不 amend、不改写历史。

## [RELEASE] 2026-11-19

本地封版 2.21.0（记号标准字典·闭集＋开集）。
- 四处 parity 同版 2.21.0；zip 确定性双建同哈希 sha256 0982b4c4bb983b5879b7b7500face4be6ce7f32d6f4d174854d180b84657691c
  （325.9KB / 333732 bytes，落 plugins/org.jiuzhang.editor.zip）。
- 包结构自检：顶层目录==id、无 backend、Apache-2.0 LICENSE 全文 202 行、违禁条目零（db/zip/pyc/onnx/data/models/dev）、
  min_host_version 1.0.0≤底座 1.2.0（app/__init__.py:8 单源未改）、无 [engine] 节。
- 底座 commit 链：A 3995984／B 288fa39／C 0ac58ad／D 93a17f2／E ab6f414／parity d649fdf（ahead 28）。
  插件仓 parity 87e1729（MT-Blaze 瞬态身份，ahead 10）。
- 回单：docs/handoff/receipts/latex-norm-dict.md（LND-01，五项＋收口复验）。
- **两仓 push 待主公授权（hold）**；标准标签条款级＝显性欠账（GB 版权不公开全文/ISO 全文付费）；
  存量批量回写＝另案；CUDA/大图 mtmd/CPU 耗时/准档升默认/MinerU 真填充＝继承重做卡欠账不在本卡修。
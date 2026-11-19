# 记号标准字典（闭集＋开集）· 2.21.0

- 状态：进行中
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
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
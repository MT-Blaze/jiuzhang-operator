# 切题解析四形状修实（build-documents-shapes）

状态：已收口（修实全绿；push 待主公授权）
发起日期：2026-11-19
需求来源：枢纽 aa2dcda2（Typst替代LaTeX可行性）；前卡 MPF-01（mineru-put-fix）取证 7 题解析缺口另卡待点头 → BDP-01 任务卡
基线：operator e0d11b7（ahead 33）／ plugins 87e1729（零写入，ahead 10）；修实 commit cb8a82a

## [REQ] 2026-11-19

前卡 MPF-01 上传链修绿后 L2 复测 13/20 回填：MinerU 云转写本身正确，剩余 7 题
（3/6/10/11/13/14/15）损失在产品自己的 markdown→题目解析段——build_documents 对四类
版式形状零解析（选项独立成行／卷首图片行／整题 $$ 包裹＋题号拆字「1 3.」／填空 \_\_\_\_）。
卡令：只治解析覆盖面四形状，不碰上传链/引擎/字典口径/插件仓/题目契约；形状归一做进
parse_question 前的确定性预处理；不伤已绿 13 题与任何存量解析；图片剥行＋warnings 如实
不静默丢；清洗仍走字典驱动 clean_for_write；归一＋解析幂等。验收：7 题→7 文档、20 夹具→
20 文档、对照 13 题逐字段不回归、定向＋门禁绿、离线产品入口回放绿；本卡零出网。

## [IMPL] 2026-11-19

- 新增 `app/core/ingest/intake/shapes.py`（127 行，同层兄弟模块，分层 ≤3）：四形状确定性
  归一纯函数（无 IO 无网络），精确形状谓词守边界，存量逐字不动。
  - 选项独立成行：只并「跑到文末的选项块」（_CHOICE_A 起＋其后全 _CHOICE_HEAD），选项后
    跟节标题（如「三、填空题…」）不并（排除题 12）；并块走 question_parser.split_options 重排。
  - 卷首图片行：整行 markdown 图片剥行＋逐条 warnings（不合契约 Image.uri，题图以本地切图
    为准，merge_local 覆盖，剥行不丢题图）。
  - 整题 $$ 包裹：整段恰一个 display 块且块内有题号头才 unwrap，_SPLIT_NUM 只修块首裂题号
    「1 3.」→「13.」（仅 display 语境，正常数字不碰）。
  - 填空 \_\_\_\_：有转义空＋无发问词（_ASK_RE）＋无选项才还原下划线（排除存量题 16）。
  - normalize 返回 (归一文本, warnings) 2 元组，无题号 hint（保幂等）；没认出形状原样返回。
- 修改 `app/core/ingest/intake/text.py`（391→397 行，≤400；+8/-2）：build_documents 非
  exam-zh 路接 shapes.normalize（:372-374）＋单段带题号接受例外（:381-383，救 13/15 无发问词
  解答题，不赋 source.question_no 保对照同口径＋幂等）；exam-zh 版式路一字未动。
- 新增 `tests/test_build_documents_shapes.py`（23 案）＋`tests/fixtures/bdp01/`（20 夹具逐字＋
  before.toml 基线）。使用 skill：sync-biz-record（本记录）。
- 契约/字典/上传链/question_parser/引擎/插件仓零改动。版本持 1.2.0、parity 持 2.21.0、zip 不重打。
- commit cb8a82a（代码＋测试＋夹具 24 文件 +778/-2，定向 201/201＋门禁 PASS 后 commit）。

## [VERIFY] 2026-11-19

- 定向 8 模块 **201/201 绿**（test_build_documents_shapes 23／question_parser 47／clean_latex 13／
  latex_norm 37／latex_style_dict 30／file_size_contract 13／ingest_triage 21／mineru_local_run 17）；
  快门禁 **PASS（6 项全过）** GATE_EXIT=0；WARN 23 份既有冻结台账，新增两文件均 ≤400 未进带。
- 离线端到端双证（零出网零引擎零端口）：
  - 产品入口直调 verify.py→service.build_documents：20/20 出文档；对照 13 题修前修后逐字段＋
    warnings 一致；7 题形状全对；20 题幂等绿。
  - 全接线 e2e_ingest.py→service.ingest_files（老师拖 .md 同一同步入口）→待审池读回：20/20 文件
    出文档（池内 24 文档）；7 题落池形状全对；对照 13 题落池文档数不回归；剥图警告解析边界如实。
- UI 探针未做（卡 §4 离线回放即充分；修实 confined 解析段，UI 接线未改且单测覆盖，已离线证至
  待审池）；未起服务/端口/浏览器，无孤儿无端口收口负担。
- 红线逐项自查见回单 §七：两仓 push hold／不 amend／stage 逐个点名／onnx_probe.py 与插件未跟踪件
  原样／契约·字典·上传链禁改／禁 JSON 落盘／500 行·分层 ≤3·冻结台账只减不增／零出网／停跑令／
  插件零写／65496 零接触／禁嵌套／key 无明文。
- 题号口径：修实 7 题题号以 stem 头号承载（source.question_no=""，与对照单段题同口径；mineru
  回填路题号由 merge_local 本地切图覆盖，解析段不越权）——三硬约束（幂等＋对照一致＋7 题带号）逻辑必然。
- 回单：docs/handoff/receipts/build-documents-shapes.md（BDP-01，三桶＋改动带行号＋201 表＋门禁＋
  离线双证＋夹具映射＋红线逐项＋ahead 实数）。交付证据 docs/handoff/evidence/build-documents-shapes/。
- ahead 实数（git rev-list --count @{u}..HEAD）：operator 修实后 34（docs commit 后 35）；plugins 10 零写。
- 两仓 push hold 待主公授权；65496 收口后重启属主公另行点头事项，不在本卡。
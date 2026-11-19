# 回执 · 切题解析四形状修实（build-documents-shapes）

【回执编号】BDP-01（build-documents-shapes）
【回执时间】2026-11-19 20:30:06+08:00
【执行结果】成功（全绿）——7 题（3/6/10/11/13/14/15）解析修实，20 夹具→20 文件出文档（24 文档），对照 13 题逐字段不回归，归一＋解析幂等；定向 201/201＋快门禁 PASS＋离线双证（build_documents 直调＋全接线 ingest_files 落池）。无修实欠账；push 待主公授权。
【基线】operator e0d11b7（ahead 33）→ 修实 commit **cb8a82a**（ahead 34）；plugins **87e1729 零写入**（ahead 10）
【枢纽】aa2dcda2-9e43-40d6-82ec-6b82c6cacb03（Typst替代LaTeX可行性；前卡 MPF-01 取证本卡 7 题缺口）
【证据根】`E:\jiuzhang\jiuzhang-operator\.system_generated\build-documents-shapes\`（git-ignored）；交付证据 `docs/handoff/evidence/build-documents-shapes/`（入 git）

---

## 三桶总览

**做了什么**：§0 核基线（两仓 HEAD/ahead 符卡）→ §2 离线复现 7 题＝0 文档（与 fix_l2_diag 逐位吻合）→ 新增 `intake/shapes.py` 四形状确定性预处理＋`text.py` build_documents 接线 → §3 新增 23 案＋定向 8 模块 201/201 绿＋快门禁 PASS → §4 离线端到端双证（产品入口 build_documents 直调 20/20＋全接线 ingest_files 落待审池 20/20）→ 回单＋证据＋biz 收口。

**改了哪些**：operator 代码 commit **cb8a82a**（`text.py` +8/-2、新增 `shapes.py` 127 行、新增 `tests/test_build_documents_shapes.py` 253 行 23 案、新增 `tests/fixtures/bdp01/` 21 份夹具）＋本回单＋biz 记录＋交付证据（docs commit 另计）。**plugins 仓零改动**。宿主版本持 1.2.0、parity 持 2.21.0、zip 不重打。契约/字典/上传链/引擎零改动。

**成没成**：成。7 题→7 文档（stem 非空、题号以头号承载、选项/blanks 按形状）；20 夹具→20 文件出文档（池内 24 文档，17/18 各 2、20 共 3）；对照 13 题修前修后**逐字段一致**（含 warnings）；归一＋解析两遍＝＝一遍；卷首图片剥行＋warnings 如实登记不静默丢。遗留仅 push 待授权（卡面 hold），无修实欠账。

---

## 一、改动清单（带行号）

- 修改：`app/core/ingest/intake/text.py`（391→**397 行**，≤400 ✓；+8/-2）
  - `build_documents` 非 exam-zh 路（:371-394）：
    - :372-374 延迟导入 `shapes`＋`normalize(text)` 归一，`shape_warnings` 并进 `warnings`；
    - :375-377 `_split_numbered(normalized)` 切段，`single = len(segments)==1`；
    - :381-383 **接受例外**：`numbered = bool(number) or (single and bool(_HEAD_NUM_RE.match(segment)))`——整段就一道带题号的题直接认下，不再靠发问词兜底（救 13/15 无发问词的解答题）；**不赋 `source.question_no`**（保单段题 question_no="" 与对照同口径＋幂等）；
    - :388-394 `_document(...)` 落文档，`question_no=number`（多段题号链照旧）。
  - exam-zh 版式路（:360-370）**一字未动**。
- 新增：`app/core/ingest/intake/shapes.py`（**127 行**，≤450 ✓，同层兄弟模块，分层 ≤3 ✓）
  - 顶层反向导入 `text._ASK_RE / _HEAD_NUM_RE`（单源同口径；text.py 延迟导入本模块，无加载环）:30-33；
  - `_strip_image_lines`（:46-60）：整行 markdown 图片剥行＋逐条 warnings「题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：<target>」；
  - `_unwrap_display`（:63-75）：整段恰一个 `$$…$$` 块且块内有题号头才 unwrap，`_SPLIT_NUM` 只修块首裂题号「1 3.」→「13.」；
  - `_rejoin_terminal_options`（:78-100）：只并「跑到文末的选项块」（`_CHOICE_A` 起＋其后全 `_CHOICE_HEAD`），选项后跟节标题（如「三、填空题…」）不并；并块走 `question_parser.split_options` 重排规范形；
  - `_unescape_blanks`（:103-111）：有转义空 `\_`＋无发问词（`_ASK_RE`）＋无选项才还原下划线（排除存量题 16）；
  - `normalize`（:114-128）：纯函数无 IO 无网络；没认出任何形状原样返回 `(text, [])`；认出则返回 `(归一文本, warnings)`。**返回 2 元组，无题号 hint**（保幂等）。
- 新增：`tests/test_build_documents_shapes.py`（253 行，tests 豁免行数；**23 案**）
  - 四形状各 ≥2 案（真实夹具逐字＋变体）：选项独立行（3/6＋变体＋12 不并）／图片行（10/11＋变体＋纯图不静默）／$$ 包裹（13/15＋两位/一位变体＋非 $$ 语境裂题号不修＋正常题号不误伤）／填空（14＋变体＋16 不动）；
  - 7 题→7 文档全量案＋20 夹具→20 文档全量案＋对照 13 题逐字段不回归案（读 before.toml）＋幂等案。
- 新增：`tests/fixtures/bdp01/`（21 份）：`full_md_fix_01..20.md`（与 wire 逐字一致，抽 03/14/20 diff 验证）＋`before.toml`（修前基线快照）。
- 禁改区自查：LICENSE 否／根 agents.md 否／AGENTS 铁律一二 否／`app/core/question_contract.py` 否（契约唯一 dataclass 未触、未新增字段）／字典 `latex_norm`/`latex_style_dict` 否／上传链 `mineru_extract.py` 否／`question_parser.py` 否（git diff 0 命中）／用户 data/ 否。

## 二、包结构自检（§5 版本 parity）

纯底座解析修复，**无插件界面改动** → plugins 仓零写、zip 不重打、四处 parity 持 **2.21.0** 不动。宿主 `__version__` 单源 `app/__init__.py:8` 持 **1.2.0** 不动（修实非发版）。plugins HEAD 仍 87e1729，未跟踪件 `model_prefs.toml`／`models/` 原样未碰。

## 三、三查结果

零插件代码改动，三查不适用。宿主侧改动仅 `text.py`＋新兄弟模块 `shapes.py`＋新测试/夹具，无前端改动、无新请求 id、无新 Host API。

## 四、测试与探针（数字均当次实测）

单测（解释器 `.venv\Scripts\python.exe`，逐模块 `python -m unittest tests.<模块>`，禁 pytest/discover）：

| 模块 | 结果 |
|---|---|
| tests.test_build_documents_shapes（新增） | 23/23 OK |
| tests.test_question_parser | 47/47 OK |
| tests.test_clean_latex | 13/13 OK |
| tests.test_latex_norm | 37/37 OK |
| tests.test_latex_style_dict | 30/30 OK |
| tests.test_file_size_contract | 13/13 OK |
| tests.test_ingest_triage（intake-text 对应） | 21/21 OK |
| tests.test_mineru_local_run（触及解析回填，自查补跑） | 17/17 OK |

合计 **201/201 绿**。快门禁 `bash scripts/check-quick-gate.sh`＝**PASS（6 项全过）**，GATE_EXIT=0；WARN 23 份体积预警均既有基线冻结台账（`question_parser.py`=481 未改），新增 `shapes.py`=127／`text.py`=397 均在 400 下不在列，**冻结台账只减不增 ✓**。全量回归豁免（AGENTS §7 定向＋门禁绿＝绿，2026-11-18 常设裁决）。

离线端到端（**零出网零引擎零端口**，.md 判 text 不碰 OCR/版面/识别引擎）：

1. **产品入口直调**（`verify.py` → `service.build_documents`）：20/20 出文档（0 文档题号=[]）；对照 13 题修前修后**逐字段一致＋warnings 一致**；7 题形状全对（type/选项数/stem 头号/source.question_no=""）；20 题幂等绿。证据 `verify_report.md`／`before_snapshot.toml`／`after_snapshot.toml`。
2. **全接线落池**（`e2e_ingest.py` → `service.ingest_files`，老师拖 .md 的同一同步入口）：ingest_files → stage_ingest → run_ingest_jobs → media._items_from_file → build_documents → pending.save_draft → 待审池读回。**20/20 文件出文档（池内 24 文档）**；7 题落池形状全对；对照 13 题落池文档数不回归（17/18 各 2、20 共 3）；剥图警告解析边界如实（10/11 各 1 条）。隔离底座 `JZO_DATA_DIR`/`JZO_PLUGINS_DIR` 进 .system_generated 临时区＋最小目录夹具插件，绝不碰本机 data/／plugins/。证据 `e2e_report.md`／`e2e_snapshot.toml`。

**UI 探针＝未做（按卡 §4 口径，离线回放即充分）**：卡 §4 明示「真实云识别 20/20 ok 的证据已在 fix_l2.toml，本卡只补解析段，离线回放即充分」。本卡修实 confined 于解析段（build_documents/normalize），UI 接线（static/js 拖拽 → host ingest.files → ingest_files）**未改**，且已被 test_ingest_triage（21）/test_mineru_local_run（17）覆盖；上条全接线探针已离线证至待审池（产品同一入口）。故不另起 Playwright 浏览器探针——**未起服务、未开端口、无孤儿**，无端口收口负担。如实披露：浏览器 UI 层本卡未真点（卡面允许离线直调＋单测为证）。

## 五、夹具→题号映射表

| 夹具 | 题号 | 桶 | 修前文档 | 修后文档 | type | 形状 |
|---|---|---|---|---|---|---|
| full_md_fix_01.md | 1 | 对照 | 1 | 1 | single_choice | — |
| full_md_fix_02.md | 2 | 对照 | 1 | 1 | single_choice | — |
| full_md_fix_03.md | 3 | **修实** | 0 | 1 | single_choice | 选项独立成行 |
| full_md_fix_04.md | 4 | 对照 | 1 | 1 | single_choice | — |
| full_md_fix_05.md | 5 | 对照 | 1 | 1 | single_choice | — |
| full_md_fix_06.md | 6 | **修实** | 0 | 1 | single_choice | 选项独立成行 |
| full_md_fix_07.md | 7 | 对照 | 1 | 1 | single_choice | — |
| full_md_fix_08.md | 8 | 对照 | 1 | 1 | single_choice | — |
| full_md_fix_09.md | 9 | 对照 | 1 | 1 | single_choice | — |
| full_md_fix_10.md | 10 | **修实** | 0 | 1 | single_choice | 卷首图片行（剥行＋warning） |
| full_md_fix_11.md | 11 | **修实** | 0 | 1 | single_choice | 卷首图片行（剥行＋warning） |
| full_md_fix_12.md | 12 | 对照 | 1 | 1 | solution | 节标题作题干（选项块不并） |
| full_md_fix_13.md | 13 | **修实** | 0 | 1 | solution | $$ 包裹＋裂题号 |
| full_md_fix_14.md | 14 | **修实** | 0 | 1 | fill_blank | 填空 \_\_\_\_ 还原 |
| full_md_fix_15.md | 15 | **修实** | 0 | 1 | solution | $$ 包裹＋裂题号 |
| full_md_fix_16.md | 16 | 对照 | 1 | 1 | solution | 有发问词（填空不动） |
| full_md_fix_17.md | 17 | 对照 | 2 | 2 | solution | — |
| full_md_fix_18.md | 18 | 对照 | 2 | 2 | solution | — |
| full_md_fix_19.md | 19 | 对照 | 1 | 1 | solution | — |
| full_md_fix_20.md | 20 | 对照 | 3 | 3 | solution | — |

修实 7 题＝{3,6,10,11,13,14,15}；对照 13 题＝其余。题号口径：修实 7 题题号以 **stem 头号**承载（`source.question_no=""`，与对照单段题同口径；mineru 回填路的 source.question_no 由 `recognize.shared.merge_local` 用本地切题题号覆盖，不在本卡解析段）。

## 六、未决问题与偏离（需拍板）

1. **push 待授权**：两仓 push 均 hold（卡面 §7.1）。operator ahead 实测 **34**（修实 cb8a82a 后；本回单 docs commit 后＝35）；plugins ahead **10** 零写。push 时以 `git rev-list --count @{u}..HEAD` 实数为准。
2. **65496 正式服务**：本卡零接触（未起服务、未重启、未杀）。枢纽备忘「BDP 收口后需再重启一次」属主公另行点头事项，不在本卡。
3. **解释性口径·题号**：修实 7 题不赋 `source.question_no`，是三条硬约束（幂等＋对照逐字段一致＋7 题带题号）的逻辑必然——救回的归一形与对照单段题结构不可区分，题号只能住 stem 头号。mineru 回填路题号由 merge_local 本地切图覆盖，解析段不越权。
4. **解释性口径·剥图警告池内落点**：build_documents 解析边界如实产出剥图 warnings（verify/e2e/单测三证）；产品接线 `append_notes` 把它写进 batch route.note，但落池后 dedupe 用新快照重写 route（既有接线，对所有带 note 的 text 导入一视同仁），致池内 route.note 不再带该警告。**此非本卡解析段回归**，本卡未治、亦超范围；警告不静默丢已在解析边界证死。
5. **未验证**：浏览器 UI 层真点（卡 §4 允许离线直调＋单测为证，已离线证至待审池）；真实云识别整卷回填（前卡 MPF-01 已证 20/20 PUT/extract，本卡零出网不重跑）。
6. 既有欠账沿用：MinerU /models 探针形状 404（前卡登记，本卡未治）；23 份 451–550 体积预警冻结台账（本卡未增）。

## 七、§7 红线自查（逐项）

1. 不 push（两仓 hold）✓／不 amend 不改写历史 ✓／stage 逐个点名（text.py/shapes.py/test/fixtures 四路径，未用 add -A）✓／不绿不 commit（201/201＋门禁 PASS 后才 commit）✓。
2. `tools/onnx_probe.py`（底座）与插件仓 `models/`、`model_prefs.toml` 原地 untracked 不删不挪不 stage ✓（git status 原样）；engines/ 产物不 stage ✓；用户 data/ 禁改 ✓（e2e 隔离 data 进 .system_generated）。
3. LICENSE／根 agents.md／AGENTS 铁律一二／`app/core/question_contract.py` 禁改 ✓（契约未触、未新增字段）。
4. 禁 JSON 落盘 ✓（证据全 TOML/MD/Dataclass；快照/报告/日志均 TOML/MD）；500 行红线 ✓（text.py 397／shapes.py 127）；分层 ≤3 ✓（intake/ 同层兄弟，app/ 零新目录）；冻结台账只减不增 ✓（新增两文件均 ≤400，未进 451–550 带）。
5. 字典口径不动 ✓（latex_norm/latex_style_dict 零改）；清洗仍走字典驱动 clean_for_write 不绕过 ✓（shapes 只做版式归一，清洗交 question_parser 既有路）。
6. 出网铁律本卡零出网 ✓（离线 build_documents/ingest_files，.md 判 text 不碰引擎，无 POST/PUT/GET 外网腿）。
7. MinerU 本地 CPU 逐题填充停跑令 ✓（未跑任何引擎）；微批 3–5 定死 ✓（本卡零引擎腿，无微批）。
8. 插件仓本卡零写 ✓（HEAD 87e1729，零 commit 零 stage）；未用 git config（瞬态身份备而未用）。
9. 65496 禁重启禁杀 ✓（零接触）；他会话进程禁碰 ✓（port 2889 残留未碰）；探针端口收口全闭＋孤儿零 ✓（**本卡未起服务/端口/浏览器**，in-process 隔离，无端口无孤儿）。
10. 委托轮禁嵌套创建子会话 ✓（根会话直跑）；跑一半不交接 ✓（全程本会话收口）；回单到枢纽独立复核后才算收口 ✓（本回单交枢纽 supervise）。
- key 全 mask ✓（本卡零出网零 key；证据为离线解析产物，无 token/签名；wire mineru_wire*.md 含 token 未抄进回单/证据）。

## 八、git

- operator：基线 e0d11b7（ahead 33）→ 修实 **cb8a82a**（代码＋测试＋夹具，24 文件 +778/-2，定向 201/201＋门禁 PASS 后 commit，ahead 34）；回单＋biz＋交付证据 docs commit 另计（见 git log，ahead 35）。stage 逐个点名，未用 add -A；不 amend 不改写历史。
- plugins：零 commit 零 stage 零 push，HEAD **87e1729**（ahead 10），未跟踪件原样。
- 两仓 push 均 hold 待主公授权。ahead 实数锚定 `git rev-list --count @{u}..HEAD`（禁口算）。

## 九、证据索引

交付证据（入 git）`docs/handoff/evidence/build-documents-shapes/`：
- 报告：`verify_report.md`（build_documents 直调 20/20＋对照逐字段＋形状＋幂等）／`e2e_report.md`（全接线 ingest_files 落池 20/20）／`repro_summary.md`（修前 7 题＝0 复现）
- 快照：`before_snapshot.toml`（修前基线）／`after_snapshot.toml`（修后）／`e2e_snapshot.toml`（待审池）
- 日志：`tests_console.md`（8 模块 201/201）／`gate_console.md`（PASS 6 项）
- 脚本：`repro.py`／`verify.py`／`e2e_ingest.py`（可复核）

探针产物（git-ignored）`.system_generated/build-documents-shapes/`：同上原件＋`e2e/`（隔离 data/plugins 临时区）。
夹具（入 git）`tests/fixtures/bdp01/`：20 份 full_md_fix_NN.md（与 wire 逐字一致）＋before.toml。
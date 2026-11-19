# 回执 · 记号标准字典（闭集＋开集）2.21.0

【回执编号】LND-01（latex-norm-dict）
【任务卡】E:\jiuzhang\记号标准字典闭集开集任务卡.md（§0–§7）
【日期】2026-11-19
【基线】底座 830ca19 ／ 插件 af7884d（2.20.0）
【交付】2.21.0 四处 parity＋zip 确定性双建同哈希
【状态】本地封版完成；两仓 push 待主公授权（hold）

---

## 一、改动清单（带行号）

### 底座仓 jiuzhang-operator（基线 830ca19 → HEAD d649fdf，ahead 28）

逐阶段 commit（不 push、不 amend）：
- 阶段A `3995984`：整机级 DB 三表＋迁移回滚＋备份接线
- 阶段B `288fa39`：闭集种子 TOML 全量＋导入四保险＋渲染探针
- 阶段C `0ac58ad`：清洗字典驱动接线＋台账第 49 条修订
- 阶段D `93a17f2`：norm.* Host API＋宿主 relay 转发族＋字典族 UI 五列＋开集待审区
- 阶段E `ab6f414`：测试全案＋三支探针绿＋修恢复出厂键禁用态真缺陷
- parity `d649fdf`：主仓 plugins.toml editor 2.20.0→2.21.0

**§1 整机库（阶段A）**
- `app/core/config.py:85-87` `latex_norm_db_path` property = `root_data_dir()/"latex_norm.db"`（整机一套，不随工作区漂移；禁 cwd 拼路径）。
- `app/core/content/latex_norm.py`（450 行，≤450）：三表 norm_entries/norm_variants/norm_corrections；
  `connect():91`（timeout=10/row_factory/foreign_keys=ON/busy_timeout=5000）、`_ensure_schema():128`（逐句 execute 禁 executescript）、
  `_backup_before_migration():111`（.pre-vN.bak 幂等）、`transaction():146`（单事务）、`_GENERATION:46`（写代数缓存键）。
  闭集出厂冻结、老师只写 `chosen_default_variant_id`：`choose_default():216`/`reset_default():230`（reset=选择回退，出厂内容永不动）。
  开集四态人闸：`record_unknown():242`（unknown→pending，仍不打印不进日志）、`decide_correction():262`（只 pending 可裁；confirmed 须目标参与改写；rejected 黑名单永不生效）、`sweep_stale():285`（陈旧→archived）。
  `FAMILIES:26`（八记号族）、`SOURCE_LABELS:31`（四标签 frozenset）。
- 备份整机层接线：`app/core/backup/package/files.py:36,76-79`（`MACHINE_DB_NAME="latex_norm.db"`，machine/ 前缀进包，工作区扫描不双收、工作区导入不携带）；`service.py`/`restore.py`（532 冻结持线）/`static/js/st_backup.js`（537 冻结持线）同线原地补。

**§2 闭集种子（阶段B）**
- `app/core/content/latex_norm_seed.toml`（2177 行）：223 条目／271 变体／八记号族全量，一符号一条目（单形式也占行），每条出厂自带默认。
- 导入四保险：`load_seed():339`（带清单条目数/变体数/版本号）、`_reconcile():366`（实数逐件对账，不等＝显性失败＋回滚）、`import_seed():384`（单事务＋幂等补差按 entry_key 不覆盖老师选择＋版本对账）。
- MathJax 逐条渲染探针：`apply_render_report():414`（unsupported→render_supported=0＋render_note，绝不静默丢、排除改写）。
- 来源标签只到标准族级（`standards.toml [label_ruling]`）：同码合并「ISO/GB-T」、异码分裂「ISO 80000-2」/「GB 3102.11」、课本「教材版式约定」；每条来源备注写免费合法链出处（码点/表页/brochure 节），不写 ISO 条款号。

**§3 清洗字典驱动（阶段C）**
- `app/core/content/latex_norm.py:428` `clean(text, *, compare=False)`：闭集 `rewrite_aliases():304`＋开集 `confirmed_corrections():326` 合并、传递闭包保幂等，交老模块切词改写；写路 unknown 送 `record_unknown`，比对路只归一不登记；按 (库路径, 写代数) 进程内缓存，写口 transaction 提交后 bump 代数即失效（修掉查重热路逐次开库拖垮后台初查线程：test_pending_dedupe_scan 27s+ 超时回 3s 绿）。
- `app/core/content/latex_style_dict.py`（506 冻结只减不增）：clean_for_write/normalize_for_compare/_rewrite/_rewrite_span 原地「字典从参数取」（aliases 参数默认 None 回落 SYMBOL_ALIASES 基线）；硬规矩③ docstring 同步台账 49 修订。三硬规矩保留：按命令切词（\left 不拆成 \le）、幂等、不认识就不动（\text{} 中文与环境名不动）。
- 三调用点交驱动：`question_parser.py:19,166,243`、`ai/recognition/recognize.py:25,124`、`bank/engine/dedupe_signature.py:27,48`（compare=True 指纹受益）。
- 台账第 49 条修订：`docs/question-cutting-pipeline.md` 第 56 条＋模块 docstring＋biz 记录同步（unknown 由「不落盘不打印不进日志」改「进开集 norm_corrections(pending) 老师裁」，仍不打印不进日志）。

**§4 Host API＋UI（阶段D）**
- `app/api/norm.py`（97 行，新建）：GET /api/norm/entries（闭集条目＋变体＋effective_default）、GET /api/norm/corrections?status=（开集候选＋四态计数）开放读；POST choose/reset/decide 一律 `Depends(require_write_token)`；NormError 翻 HTTPException(400,{code:"norm_error"})。
- `app/main.py:31`（import norm_router）、`:172`（`_seed_latex_norm()` 启动幂等自举，失败不挡底座、清洗回落冻结基线，照 _ensure_bank_engine 容错先例）、`:192`（lifespan 调用）、`:233`（include_router）。
- 宿主 relay 白名单原地同线补（冻结面只减不增）：`static/js/stage_command.js:75`（545 冻结持线，dict.* 行尾追加 norm.list/choose/reset/corrections/decide）；`static/js/stage.js:240,476`（776 冻结持线，挂 JzoStageRelayNorm.create＋families 追加 relayNorm）；新族 `static/js/stage_relay_norm.js`（120，照 stage_relay_io relayMeta 先例，读 questions:read/写 questions:write＋withWriteToken，错误码复用 BAD_REQUEST/FORBIDDEN 不新增码集）；`static/workspace.html` 挂 relay（先于 stage.js）。
- 字典族 UI（宿主同源 DcClient，不经沙箱 relay；整块可下架）：
  - `static/js/dict_console/catalog.js:75-84`（第四分类 notation，machine:true，sub mode:"norm-dict"）；`panels.js`（renderSub norm-dict→DcNormDict.mount，看板 machine 卡显「整机生效·闭集＋开集」不显行数）；`sidebar.js`（machine 分类挂「整机生效」徽标）。
  - `static/js/dict_console/norm_dict.js`（267，≤450）：闭集五列（①记号族筹码过滤 ②名称 ③各来源代码行＋标签筹码 ④逐行对齐 MathJax 渲染 ⑤默认单选）＋名称/代码搜索＋每条目恢复出厂（DcDialog 确认，焦点陷阱/Esc/归位）。公式经 JzoMath.render 取 SVG 串再 DOMParser 落节点，绝不拼 innerHTML；render_supported=0 显性降级源码＋render_note。
  - `static/js/dict_console/norm_inbox.js`（200）：开集待审第二块＋计数徽标，pending 命中倒序，原始 vs 收编后双渲染对照，目标代码即时预览，收编（confirmed 须目标）/驳回（rejected 黑名单，DcDialog 确认）。
  - `static/css/dict_console_norm.css`（248，<450）：复用 app.css 主题变量，五列 minmax(0,1fr) 网格防溢出、公式格内部横滚、375px 入口头与对照格堆叠；状态不只靠颜色（筹码加粗＋描边＋aria-pressed）。
  - `static/dict_console.html`：挂本地 MathJax（jzo_mathjax.js＋tex-svg-full.js 离线）＋norm css＋两 norm 模块。

**§6 测试与探针（阶段E）**
- `tests/test_latex_norm.py`（547，tests/ 豁免红线）：全量计数/对账/注入失败回滚/幂等选择保留/choose/reset/开集四态/唯一键去重 hit+1/黑名单/清洗字典驱动/normalize 同口径/三硬规矩/unknown 进待审，37 案。
- `tests/test_norm_api.py`（225）：8 案契约（起 uvicorn 设 JZO_RESTART_DISABLED=1＋隔离 data/plugins＋随机端口＋静态令牌）。
- `tests/test_latex_style_dict.py`（HostChainTest 加未播种隔离）、`tests/test_restore.py`（备份整机层）同线补。
- 三支探针（动态端口＋随机令牌＋隔离副本，零引擎、零出网）：`tools/latex_norm_render_probe.py`（203）、`tools/latex_norm_ui_probe.py`（373，新建）、`tools/latex_norm_clean_probe.py`（244，新建）；标准核验 `tools/latex_norm_standards_check.py`（240）。
- 修缺陷：`norm_dict.js` 恢复出厂 onConfirm 旧 `.finally(busy(button,false))` 冲掉 syncDefault 设的 disabled=true，致回出厂后键仍误启用；改为成功交 syncDefault 掌管禁用态、catch 才重新启用、finally 只清 aria-busy。

**parity（阶段E 收口）**
- `plugins.toml:51` editor version 2.20.0→2.21.0（sync_plugin_index.py rc=0 改写）。

### 插件仓 jiuzhang-plugins（基线 af7884d → HEAD 87e1729，ahead 10）

- parity commit `87e1729`（MT-Blaze 瞬态身份 `-c user.name=MT-Blaze -c user.email=tianxiulaoshi@163.com`，绝不写 git config）：
  - `src/org.jiuzhang.editor/plugin.toml:4` version 2.20.0→2.21.0
  - `plugins.json` editor 条目 version→2.21.0＋changelog（如实记：本卡功能落底座整机库与宿主字典控制台，编辑器插件沙箱界面无功能改动，包内仅版本号随发布列车前进）
  - `plugins/org.jiuzhang.editor.zip` 重打（确定性双建同哈希）
- 未 stage（原地 untracked，遵卡红线）：`src/org.jiuzhang.editor/model_prefs.toml`（插件运行时状态文件，model_prefs.py:3 口径，内容默认空值，疑枢纽复跑单测所触）、`src/org.jiuzhang.editor/models/`（本地 YOLO 模型按需下载，绝不随包分发）。

---

## 二、包结构自检（四处 parity＋zip 确定性双建）

**四处 parity 同版 2.21.0：**
| # | 位置 | 版本 |
|---|------|------|
| ① | 插件仓 src/org.jiuzhang.editor/plugin.toml:4 | 2.21.0 |
| ② | 插件仓 plugins.json editor 条目 | 2.21.0 |
| ③ | 主仓 plugins.toml:51（sync rc=0「远端索引一致」） | 2.21.0 |
| ④ | zip 包内 org.jiuzhang.editor/plugin.toml | 2.21.0 |

**zip 确定性双建同哈希：**
- `tools/build_plugin.py` 实跑两遍 → `.system_generated/zip-parity/build1/` 与 `build2/`
- sha256（build1==build2）：`0982b4c4bb983b5879b7b7500face4be6ce7f32d6f4d174854d180b84657691c`
- 落 `plugins/org.jiuzhang.editor.zip` 同哈希；325.9 KB（333732 bytes）< 10 MB 上限
- 2.20.0 旧包哈希 `2ca17477…c954` 已被覆盖（重打）

**包结构自检（zip 内实查）：**
- 顶层目录 == id：`org.jiuzhang.editor`（91 条目）✓
- 无 `backend` 字段 ✓
- Apache-2.0 `LICENSE` 全文（202 行，含「Apache License」「Version 2.0」）✓
- 违禁条目零：无 .db/.zip/.pyc/.onnx、无 data/、无 models/、无 dev/ ✓
- `min_host_version="1.0.0"` ≤ 底座 `__version__="1.2.0"`（单一事实源 app/__init__.py:8 未改）✓
- 无 `[engine]` 节 ✓

---

## 三、三查结果（当次实跑）

- `bash scripts/check-plugin-boundary.sh`：**PASS**
  - 插件侧 fetch( 命中 **0**
  - 插件侧 parent.document 命中 **0**
  - 插件侧 localStorage 命中 **0**
  - 插件源码内无 Python 文件 ✓
  - 宿主侧 static/js 带 fetch( 文件 17（出网必须由用户当场点击发起，AGENTS §2）
- `bash scripts/check-plugin-index-parity.sh`：**PASS**（两份索引语义一致、条目版本一致、示例题过契约校验）
- 请求 id 合规：norm.* 族沿用现有 BAD_REQUEST/FORBIDDEN 码集，不新增码、id 无点号。

---

## 四、测试与探针（N/N＋证据路径）

**单测：19 模块 / 419 案 / 全 OK**（`.venv\Scripts\python.exe -m unittest tests.<模块>` 逐模块，禁 pytest/discover）
证据：`docs/handoff/evidence/latex-norm-recon/phase-e-tests.txt`
> test_latex_norm 37、test_latex_style_dict 30、test_norm_api 8、test_question_parser 47、test_clean_latex 13、test_bank_dedupe 21、test_dedupe_fingerprint 38、test_ai_recognize 18、test_recognize_router 24、test_pending_dedupe 14、test_pending_dedupe_candidates 20、test_pending_dedupe_scan 18、test_cleanup_tools 15、test_dict_console 14、test_dict_console_subtabs 17、test_file_size_contract 13、test_ai_plugin_boundary 8、test_command_registry 35、test_version_consistency 29。

**快门禁：** `bash scripts/check-quick-gate.sh` **PASS（6 项全过，ERROR 0）**；体积预警 23 份 451–550 行＝基线零新增（新文件均 ≤450：latex_norm 450/norm_dict 267/inbox 200/css 248/relay 120/api 97）。冻结面持线：latex_style_dict 506、stage.js 776、stage_command.js 545、restore.py 532、st_backup.js 537。

**三支探针（动态端口＋随机令牌＋隔离副本，零引擎跑、产品零出网）：**
| 探针 | 结果 | 端口/闭合 | 证据 |
|------|------|-----------|------|
| ①种子渲染 latex_norm_render_probe e1 | **271/271** 变体 MathJax 实测支持，unsupported 0，零静默丢，零出网，page_errors [] | 1994 闭合 | `.system_generated/latex-norm/render/e1/`（probe.toml＋render-grid.png） |
| ②UI latex_norm_ui_probe e2 | **18/18** | 2416 port_closed_after_kill=true | `.system_generated/latex-norm/ui/e2/`（probe.toml＋shots/01–08） |
| ③清洗端到端 latex_norm_clean_probe e1 | **9/9** | 2680 port_closed_after_kill=true | `.system_generated/latex-norm/clean/e1/probe.toml` |

探针② 18 案覆盖：223 条目/9 筹码/mjx>0；五列头；整机生效徽章（面板＋导航 .dc-cat-machine）；族过滤「关系不等」→19 条全族一致＋aria-pressed；搜索 leqslant 收窄；choose le  upright 单选→状态＋API；reset 弹窗 Esc＋焦点归位（.dc-norm-reset）＋确认回出厂＋**键禁用**；开集待审 2 行/4 对照格；收编 zqprobe→leqslant 预览＋按钮启用＋行移除＋API confirmed；驳回 zqreject 弹窗→待审 0＋API rejected；375px 零横溢（doc≤376/面板/条目/行无溢出＋family grid-column「1 / -1」）；全程零引擎请求/零未捕获 JS 错/零 4xx5xx/零控制台报错。
截图 8 张：01-desktop-five-col / 02-filter-family / 03-chosen-default / 04-reset-dialog / 05-inbox-pending / 06-inbox-confirm-preview / 07-inbox-empty / 08-narrow-375。

探针③ 9 案覆盖：223 自播种；confirm zqclean→leqslant；5 微批样本逐字命中（闭集出厂默认 `$\le x$`→`$\leqslant x$`／开集 confirmed 驱动／硬规矩 left-right 不坏／硬规矩 text 环境不动／unknown 原样不动）＋幂等（清洗两遍==一遍）；unknown zquntouched 落 pending；choose 翻转 le→\le 再 reset→\leqslant；rejected zqblack 黑名单永不改写；零引擎（只 clean_latex 端点）。

**标准核验（§2 施工前置，浏览器真人路径读公开页，禁静默抓取）：**
证据：`docs/handoff/evidence/latex-norm-recon/standards.toml`＋`.system_generated/latex-norm/standards/`（截图＋页面文本）。
- GB/T 3102.11-1993（openstd.samr.gov.cn 真人搜索→点击→详情页；1993 强制 GB，2017 年第 7 号公告转推荐性 GB/T）verified=true。
- ISO 80000-2:2019（iso.org 有头真浏览器过 Cloudflare＋Usercentrics consent→搜索→64973 详情页）verified=true。
- 前身链三跳实证：ISO 31-11:1992→ISO 80000-2:2009→ISO 80000-2:2019 官方页生命周期互指。
- 免费合法链（主公 2026-11-19 点头）：Unicode 官方码表＋Pakin《Comprehensive LaTeX Symbols List》＋BIPM SI brochure＋课本公开电子版＋ISO 官方摘要/Read sample（族级）。

**前端真浏览器走过（prove-visual-change 动线）：** Playwright 驱动自带 chromium（headless），locator.click()/press_key() 经 CDP 发真实输入事件＝真人路径；宿主页 /dict?cat=notation&sub=norm-dict 同源直驱（非沙箱 iframe）；仪表未改动（裸跑取证）。

---

## 五、未决问题与偏离

**偏离（如实披露）：**
1. **修阶段D 真缺陷**：norm_dict.js 恢复出厂按钮禁用态被 `.finally(busy(button,false))` 冲掉（回出厂后键仍误启用）。阶段E 探针②「确认恢复出厂键禁用」案钉住并原地修复（267≤450）。属施工中发现的真 bug 修复，非卡面新增功能。
2. **model_prefs.toml 未 stage**：插件仓 `src/org.jiuzhang.editor/model_prefs.toml` 为插件运行时状态文件（model_prefs.py:3 口径，内容默认空值，疑枢纽复跑单测所触），遵卡红线原地 untracked、不碰不 stage 不删，仅此登记。
3. **他会话残留进程未触碰**：收口时发现 port 2889（PID 2916/19320，parent 19892 已死）uvicorn 残留，**非本卡探针端口**（本卡五端口 1994/2279/2416/2680/63533 全闭合、证据里无 2889），疑并行卡/枢纽会话残留，未触碰（不杀他会话进程）。65496 正式服务（PID 5556/23520，parent 存活） likewise 未碰。

**欠账（预登记，照挂不编）：**
1. **标准标签条款级**：逐符号条款级原文对照未做——GB 采标版权不公开全文、ISO 全文付费（仅摘要＋Read sample）。来源标签只到标准族级，不写条款号；符号集按两标准通行长符号表口径编纂。条款级核对＝显性欠账（卡 §7 预注册：核不到＝欠账不编）。
2. **存量批量回写＝另案**：本卡只做清洗驱动接线，不批量回写存量题目（卡 §3 明确另卡）。
3. **继承重做卡欠账（不在本卡修）**：CUDA／大图 mtmd 掉设备／CPU 耗时证据／准档升默认待点头／MinerU 真填充。

**需主公点头：**
- **两仓 push 授权**（hold：底座封版 parity ahead 28＋回单文档 commit／插件 ahead 10，含本卡新增；push 时以当次 `git rev-list` 实数为准；卡红线两仓不 push，待主公明确授权才推）。
- 标准标签条款级欠账是否另案补齐（需 ISO 全文付费/GB 全文版权许可）。
- 存量批量回写另案是否开卡。

---

## 六、收口复验

- **杀树＋端口复验**：本卡三支探针＋标准核验全部自终止；本卡五端口 1994/2279/2416/2680/63533 复验**全闭合**（netstat 无 LISTENING）；本卡孤儿**零**。（ui/e1 首跑曾 port_closed=false，其端口 2279 现已闭合；e2 起探针加 25×0.2s 端口闭合重试 loop。）
- **他会话进程**：65496 正式服务、2889 他会话残留均未触碰（见偏离③）。
- **git 状态（两仓干净，只余卡红线豁免 untracked）：**
  - 底座：工作树无 M／无新增 ??（`tools/onnx_probe.py` 原地 untracked 遵卡红线不碰）；封版 parity HEAD d649fdf ahead 28（回单及勘误文档 commit 另计，push 时以 `git rev-list` 实数为准）。
  - 插件：只余 `?? src/org.jiuzhang.editor/model_prefs.toml`＋`?? src/org.jiuzhang.editor/models/`（遵卡红线不 stage）；ahead 10。
- **不 push、不 amend、不改写历史**：两仓均未 push；逐阶段新 commit；插件仓 MT-Blaze 瞬态身份未写 git config。
- **本卡零引擎跑、产品运行时零出网、字典不进任何模型提示词（零 token 本地 SQLite）、学科不分类（唯一轴＝记号族）**：探针①②③全程零引擎请求实测钉住。
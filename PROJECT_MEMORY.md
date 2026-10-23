# PROJECT_MEMORY.md — 九章算子外挂大脑

本文件是给 AI 代理与接任者读的**跨会话交接底稿**。只记「不读代码就不知道、且下次会话必须知道」的事；
能从仓库现状推出的（目录结构、函数签名、依赖清单）一律不写在这里，避免与代码各说各话。

最后更新：2026-10-23（v0.6.4 封版出包：P0#3 人工审核页上线，待审队列 209 题）

---

## 一、项目铁律（不可协商，与 `AGENTS.md` 同源）

1. **纯本地、无云端**：底座与所有插件可完全离线运行；资源本地化，无 Node 运行时、无打包器。
   密钥只从环境变量或本地 `.env` 读取，**永不入库、永不写日志、永不进入插件上下文**。
2. **万物皆插件**：业务能力（渲染、录入、导入、组卷、讲义、导出、AI 辅助、统计）一律插件化；
   底座只做鉴权、导航、数据总线、插件生命周期、安全边界与错误隔离。插件不得直连数据库或文件系统，
   只能经 Host API；插件间只能经数据总线协作；沙箱 iframe + 白名单 HTML 净化。
3. **底座极简、坏了能用了**：任一插件加载失败/超时/连续报错，底座必须仍可浏览与导出，走兜底渲染。
4. **数据契约唯一**：`schemas/question.json` 是题目在底座/插件/导入导出之间流转的唯一标准结构；
   文本一律 Markdown + LaTeX（`$...$` / `$$...$$`），不得另造公式方言；题目全局身份只有 `id`（`q_` 前缀），
   原卷题号只属于来源关系；插件私有数据只能写进 `extensions`，键用反向域名前缀。
5. **白嫖不可撤销**：个人版永久开源免费（Apache-2.0），底座与插件免注册、免卡密、无签名校验、
   无远程禁用；插件格式为**纯 zip 解压即用**，禁止专属后缀；底座**禁止自动拉取/自动更新/批量下载**，
   只允许用户当场点击发起的两个出网口子（插件索引拉取、单条目在线安装）。
6. **干净房间（铁律一）**：所有代码与文档原创，严禁从 `E:\math-question-bank-main` 等历史目录复制源码、
   样式、脚本、测试、图片与目录结构。依赖白名单 Apache/MIT/BSD/ISC，**禁止 AGPL/GPL**。
7. **AI 代理不得**执行 `git push`、建远端、改写历史或发布 Release，**除非用户明确要求**。

---

## 二、当前核心进度（v0.6.3）

**数据库微内核重构完成，空库已建，456 题数据已洗入新结构。**

| 事实 | 数值 / 位置 |
|---|---|
| 冻结表结构 | `plugins/org.jiuzhang.core-bank/bank/schema.sql`，7 张业务表 + `bank_meta`，SHA-256 `3ba41e999b4b…`（本轮仅补 `sources.grade`） |
| 空库（0 数据） | `plugins/org.jiuzhang.core-bank/bank/v063.db`，159,744 B，`user_version=1` |
| 灌库产物 | `plugins/org.jiuzhang.core-bank/bank/v063_migrated.db` |
| 入表数据 | 题 456 · 大纲节点 701（册 5 / 章 18 / 节 84 / 考向 594，其中 draft 12）· 学校 347 · 试卷 27 · 题-考向 456 · 题-来源 456 · 教研笔记 150 |
| 难度口径 | 恢复 L1–L4 原码（42 / 140 / 134 / 140），不再折成 basic/medium/hard |
| 自检 | `PRAGMA foreign_key_check` 无违规，`integrity_check=ok`，全量单测 **358/358 OK**（v0.6.3 封版时为 347） |
| 迁移工具 | `tools/build_bank_schema.py`（建空库+自检+报告）、`tools/migrate_bank_v063.py`（灌库）、`tools/verify_bank_empty.py`（逐表 COUNT 核对） |
| 审计报告 | `docs/v0.6.3-题型纠偏清单.md`、`docs/v0.6.3-灌库校验.md`、`data/bank_v063_migration_report.json` |

**现网已切（P0#1 完成）**：`app/core/bank.py` 的读写路径、`app/api/bank.py` 的 HTTP 通道与
`static/js/stage.js` 的数据白名单全部走 7 张关系表；现网工作区库
`data/banks/org.jiuzhang.core-bank.db` 已是新结构（456 题，`user_version=1`）。
旧宽表整套改名为 `data/banks/org.jiuzhang.core-bank.legacy.db`（含 `-wal`/`-shm`）作历史备份，**未覆写**。
两处仍需下一棒当心：① **种子库 `plugins/org.jiuzhang.core-bank/bank/bank.db` 仍是 v0.6.2 宽表**——
新装的机器首次建库会读到宽表，底座 `connect()` 有结构守卫会如实报 `BankError` 并指向
`tools/migrate_bank_v063.py --promote`；封版（P0#4）必须把新结构库换成该种子。
② 前端插件侧还没接新通道：`bank.topics`/`bank.topic_notes` 白名单与端点已开，
但 core-bank 插件的 `ui.controls` 难度下拉、大纲树渲染仍是旧口径（P0#2）。

**字段落位与本轮裁决（主公 2026-10-23 20:00 批复三条 + 追认两处自裁）**：
- **冲突 A → 升契约**：`schemas/question.json` 的 `difficulty` 统一为 `L1/L2/L3/L4`，
  `novel` 彻底废弃并入 `L4`；因属破坏性变更，题目契约升主版本 **2.0**（`$id` 同步为
  `question-2.0.json`）。底座写入端对 1.0 旧值做强制归一（`app/core/contract.py` 的
  `normalize_difficulty`：basic→L1 / medium→L2 / hard→L3 / novel→L4），**出参只发 L 码**。
  连带改了底座 `questions` 表的 CHECK（`app/core/db.py` `user_version` 1→2，带 `.pre-v2.bak` 备份）、
  `plugin_tools.py` 标签与中文意图词、`ui_cards.py`、`agents.py` 提示词、`workspace.js` 题卡标签、
  `examples/demo_plugin` 种子与其 zip。
- **冲突 B → 备份旧库**：见上一段，严禁覆写。
- **冲突 C → 补全 schema.sql**：`sources.grade` 已写进 `bank/schema.sql`（含 `ck_sources_grade`、
  `idx_sources_grade`，并进入 `uq_sources_paper`），迁移脚本里的 `ALTER TABLE` 补丁已删。
  schema.sql 的 SHA-256 由 `43db4ed34725…` 变为 **`3ba41e999b4b…`**——本轮结构解冻**只**动了 sources 这一列。
- **自裁追认**：`type=proof/unknown` 走 422 如实报错（存储 CHECK 只收四类），不折叠成 solution；
  `answer` 出参合成对象、库内 `NULL` 时**整个省略**该字段，不拿字母冒充答案。
- 早前既有的口径不变：`tags`（含「疑似变式#N」查重噪声）丢弃不入新库；章/节、`images`、`tikz`、
  `option_columns` 落 `questions.extensions` 有序数组 `[{key,label,value}]`，
  适配层（`bank.extensions_to_array` / `extensions_to_object`）做「数组 ↔ 反向域名对象」双向映射。

**出参装配的已知损失（下一棒别当 bug 查）**：
- `answer.kind` 在库里不分列：选择题按字母合成 `choice`，非选择题一律 `text`
  （写入时 `content` 优先、退回 `final`；因此录题往返后 `expression/proof` 会变成 `text`，
  `final` 与 `content` 同值）。
- `meta.status` 与 `revision` 新表没有对应列：出参恒为 `published` / `revision=1`（草稿态需要落库时另议）。
- 年级双写：`sources.grade`（权威，筛选与统计走它）+ `extensions` 的 `org.jiuzhang.core-bank.grade`
  （无来源时的回退）。真实库上高一 420 / 高三 36，与旧宽表逐题口径一致。
- `source` 出参只取该题的**首个**来源行（一题多张卷的完整展开留给 P1 录题升级）。

**迁移里必须知道的数据坑**：
- 现库（旧宽表）对 31 道选择题用**硬编码 A** 冒充答案；新库已如实置 `NULL`（18 无答案正文 / 9 标记后空白 / 4 只有解析），别再当真实数据用。
- `answer IS NULL` 共 53 题 = 31 道选择题（无任何字母依据）+ 22 道非选择题（旧库连答案正文都没有）。
- 2 道题（`q_legacy_000421`、`q_legacy_000483`）选项内嵌在题干文字里、拆不出选项，与新表
  「选择题必须 ≥2 选项」的 CHECK 冲突，暂按原判入表并打 `structure_conflict` 标记。
- 26 道题旧库只登记到节、没有考向 id，挂在节层（`topic_unmapped` 标记）；10 个「章名当节名」的
  登记补成 draft 节节点；2 个大纲查无的考向 id 补成 draft 考向节点挂在章下。
- `option_columns` 旧库 456 题**全是 0**，实际无内容，未写入 extensions。
- 教研笔记只入 method/pitfall 共 150 条（覆盖 75 个考向）；10 条 `knowledge` 正文是
  `@mindmap/{...}` 导图 DSL 而非笔记散文，本轮**未入表**（`topic_notes` 的 CHECK 已预留 `knowledge`）。
- 题型纠偏尺子：`答案区 = 第一个【解析】之前` → 剥 `\textbf{}` 壳、去 `$...$` → 取连续 A–H 字母；
  答案区取不到时退到正文尾句「故选/因此选 + 字母」。**旧库声明的题型不可信**，以字母为准。

---

## 三、强制待办清单

### 一、当前冲刺（P0 级）

- [x] **API 切表**（2026-10-23 完成）：后端 API 全部从旧宽表 `bank_questions` 切换到新的 7 张关系表。
      读路径 `list_questions` / `get_question` / `stats` / `random_question` / `get_many` 已重写，
      新增 `topics`（懒展开 + 子树题量）与 `topic_notes`；写路径 `create_question` 与 `import_documents`
      把对象态 `extensions` 落成数组态，并按 `taxonomy.topic_ids` 写 `question_topics`、
      按 `source` upsert `schools`/`sources`/`question_sources`；`app/api/bank.py` 加了
      `/topics`、`/topics/{id}/notes` 与 `topic=` 筛选，`stage.js` 白名单加 `bank.topics`/`bank.topic_notes`。
      真机 HTTP 已验：stats 456 / 大纲四层 / 按考向子树取题 / L4+高一 129 题 / 旧值 hard→L3 / 中文搜索。
      **剩余**：插件侧未接新通道（P0#2），种子库 `bank/bank.db` 仍是旧宽表（P0#4 封版必须换）。
- [x] **前端联动适配**（2026-10-23 完成）：core-bank 画布左栏新增**大纲树**，走 `bank.topics` 按
      `parent_id` + `sort_order` 懒展开（册→章→节→考向），每个节点带子树题量 / 笔记数 / 待补录标记，
      点节点即按子树筛题（真机验证：点「1.1 集合的概念」得 23 题，与后端逐字一致）；
      插件读路径全部改吃新出参（`grade` 顶层、`taxonomy` 来自路径树、`answer` 合成对象、
      `extensions` 对象态）。难度口径：core-bank `plugin.json` 的 `ui.controls`、editor 下拉、
      classic-card / paper-gen / demo 种子与 workspace.js + workspace.css 全部改 L1–L4，
      中文标签按契约 2.0 = **基础 / 中档 / 难 / 压轴**（旧值 basic/medium/hard/novel 只做渲染兜底）。
      **注意一处与军令字面口径的偏离**：发令写的是「基础/中档/压轴/新定义」，但上一道裁决已「彻底废弃
      novel」，且 L4 在数据里是 140 道压轴题——把 L4 标成「新定义」会给最难的一档贴错标签，
      故按已批准的契约 2.0 落地；如主公坚持「新定义」字样，改 `contract.py` 的 `DIFFICULTY_LABELS` 一处即可。
- [x] **人工审核页**（2026-10-23 完成，v0.6.4）：core-bank 画布顶部新增「待审任务」页签（带角标），
      左列按标记筛（全部待审 / 七类标记各自计数），右列逐题给三种修法——
      选择题**点选项字母补答案**、非选择题**填正文补答案**、**改题型**（拆不出选项的改判解答），
      外加「确认无误，只清标记」；保存走 `bank.update` → `PATCH /api/bank/plugins/{id}/questions/{qid}`
      （写令牌留宿主侧，插件必须声明 `questions:write`），清完最后一个标记时**整个迁移条目移出库**，
      不留空壳。现网真队列实测 **209 题**：needs_conclusion 142 · topic_unmapped 26 ·
      solution_absent 22 · answer_absent 18 · answer_region_empty 9 · type_manual_review 4 ·
      structure_conflict 2（合计 223 > 209，因部分题带两个标记）。
      真机闭环在**隔离数据副本**上验过一次（点 C 保存 → 库里 `answer='C'`、迁移条目消失、
      队列 209→208），主公的现网库**未被写入**、副本已删。
      后端为此补了 `bank.update_question`（合并补丁→契约校验→回写→回读）与 `bank.review_summary`；
      改题型时选择题的字母答案会转成 `text` 正文（保事实，不因 kind 约束整条改不动）。
      **仍未做**：`topic_unmapped` 的「挂到哪个考向」不能在审核页里选（要接大纲树选节点），
      这 26 题目前只能「只清标记」或留给录题插件的改题功能。
- [~] **真机压测 + 封版**（2026-10-23 出包，压测口径未全）：
      已做——版本单源升 `0.6.3` + 前端兜底文案同步（版本锁 12 测绿）；core-bank 种子库
      `bank/bank.db` **换成新结构 456 题**（旧宽表种子已废弃，读它会被结构守卫拒掉）；
      插件重出 `org.jiuzhang.core-bank.zip` 0.2.0（1,183,766 B）、`editor` 0.1.1、`paper-gen` 0.1.1
      并落 `E:\jiuzhang-plugins\plugins\`；两份 `plugins.json` 用 `tools/sync_plugin_index.py`
      逐字全等（6 条索引）；`build_release.bat` 出 `dist/jiuzhang-operator-beta-v0.6.3.zip`
      **1,791,623 B / 242 条目 / 0 夹带 / 0 缺失**，包内种子库经解包实测是 7 表 + 456 题 + L1–L4，
      包内契约是 2.0。发放包自 v0.6 起**不入库**（`git ls-files dist` 只到 v0.5.2）。
      未做——`tools/bank_stress.py` 与 `tools/paper_probe.py` 仍直读旧宽表（切表后未跟改，
      跑真机压测前必须先修）；组卷 / 讲义两条链在新表上的回归未跑；
      桌面三栏布局的截图未取到（应用内 Browser 面板的截图面被宿主隐藏，只拿到窄屏两张）。
      人工审核页（上一条 P0）仍未开工。

### 二、核心业务闭环（P1 级）

- [ ] **录题插件升级**：目前的 editor 只有「新增」功能，需补齐「修改」「删除」旧题功能（含编辑态回填），
      并接上新表的多对多（一题挂多张试卷、原卷题号随行）。
- [ ] **考向笔记渲染**：前端需把 `topic_notes` 里那 150 条方法/易错点，在题目详情或考向树侧边展示出来。
- [ ] **A4 排版引擎联动**：确保组卷插件（paper-gen）和讲义插件（handout）能完美读取新表生成 A4 试卷；
      两者当前仍按旧 `bank.*` 出参结构取数，切表后必须回归压测。
- [ ] **P1 重排欠账**（v0.6.2 已登记）：切换答案/紧凑重排的既有性能与体验欠账，与下面 P2 第一条同源。

### 三、性能与体验（P2 级）

- [ ] **解决 3.58s 性能欠账**：针对切换答案/紧凑重排耗时 3.5 秒的问题，引入「虚拟列表」或「分页按需渲染」。
- [ ] **AI 辅助升级**：打通 OCR 乱码整理接口，让 AI 帮老师一键清洗脏 LaTeX 数据
      （A4 组卷链已有脏 LaTeX 归一经验，可复用同一归一器，勿再造第二套）。
- [ ] **图片资产收口**：迁移报告记「引用 52 张、缺 13 张」，新库 `extensions.images` 沿用同一批
      `/static/uploads/` URI；切表时需一并核验种子包 `bank/assets` 与工作区 `uploads` 的落位一致。

### 四、生态与扩张（P3 级）

- [ ] **跨学科插件测试**：用现有底座跑通一个极简的「物理」或「化学」伪题库插件，
      验证四字段独立设计（题干 / 选项 / 答案 / 解析）的普适性。
- [ ] **插件市场完善**：打通在线安装、版本更新、依赖检查等全流程（注意铁律 5：
      只允许用户当场点击发起的单条 zip 下载，禁止批量拉取）。
- [ ] **`schemas/question.json` 与存储层对齐**：决定 `extensions` 是继续「库内数组 / 契约对象」双态，
      还是升 `schema_version` 统一为有序数组（破坏性变更需升主版本 + 迁移说明 + 校验测试）。

---

## 四、标准军令模板

```
【军令】YYYY-MM-DD ｜ 子龙
标题：（不超过 16 字符）

【运行参数建议】
- 【建议模型】：xxx
- 思考强度：xxx

【北京时间：YYYY-MM-DD HH:MM:SS】

（正文内容）

（军令完毕，即刻执行！）
```

发令约定：**标题 ≤16 字符为长期铁律**（2026-10-21 拍板）；代理若发现军令与 `AGENTS.md` 铁律冲突，
必须先停下报告冲突与实测证据、请主公裁决，不得静默绕过，也不得擅自扩大改动面。

---

## 五、环境与工具备忘（省下次会话的摸索时间）

- 解释器：`.venv/Scripts/python.exe`（Python 3.14）。**venv 里没有 pytest**，跑测试一律
  `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"`（`AGENTS.md` 写的
  `python -m pytest` 在本机跑不通）。
- SQLite 3.50：JSON 函数可用（`json_valid` / `json_type` / `json_array_length`）；
  **`ON DELETE SET DEFAULT` 能建表但运行时照样违反外键**，`AUTOINCREMENT` 只能写在列级
  `INTEGER PRIMARY KEY AUTOINCREMENT`；`GLOB` 不支持 `{n}` 量词。
- 本机控制台是 cp936：Python 直接 print 中文会乱码，结果一律写 UTF-8 文件再读；
  中文不要走 argv。正则类原型必须用 Write 落成文件再跑，heredoc 会把 `\\` 折叠成 `\` 产出假阴性。
- 旧库快照：`.scratch-recon-063/legacy.db`（只读复制，含 WAL），现网旧库
  `data/banks/org.jiuzhang.core-bank.db`；两者都不是交付物，`.scratch-recon-063/` 不入 git。
- **接力坑**：`tools/migrate_bank_v063.py` 依赖 `.scratch-recon-063/legacy.db` 与旧项目的
  `schools.json` / `curriculums/A.json`，而该目录已被 `.gitignore` 排除（含第三方数据副本，
  依铁律一不入库）。新会话要重跑灌库，必须先从 `E:\math-question-bank-main\math_question_bank.db`
  **连同 `-wal` 一起**复制出快照（只复制主文件会读到过期数据），复制后先核 `COUNT(*)=456` 再跑。
- **切表轮新增的环境坑（2026-10-23）**：
  ① 底座库 `app/core/db.py` 的 `SCHEMA_VERSION` 已是 **2**，首次打开 v1 库会走「备份
  `jiuzhang.db.pre-v2.bak` → 重建 questions → 难度改值」的迁移；改这个文件的 DDL 必须同步加迁移分支。
  ② `app/core/bank.py` 建库只认 `plugins/<id>/bank/schema.sql`（不再有内嵌 DDL）——
  测试沙箱必须在临时 plugins 目录里放一份 schema.sql，否则 `init_bank` 直接 `BankNotFound`。
  ③ `tests/test_bank_api.py` 里凡是往夹具写题的用例一律取 `test_z*` 前缀（字母序最后跑），
  否则会污染 `test_stats_counts` / `test_sql_injection` 的 120 题硬断言。
  ④ 改 `examples/demo_plugin/seed/questions.json` 或其 `dist/plugin.js` 后**必须重跑**
  `examples/build_demo_plugin.py`，`examples/demo_plugin.zip` 是入库产物、不会自动跟随源目录。
  ⑤ 清理测试遗留服务时**禁止** `taskkill /F /IM python.exe`（会连坐本机其他 python 进程），
  必须记下自己起的 PID 再逐个终止。
  ⑥ `settings.plugins_dir` 是**导入期一次性求值**的类属性（`JZO_PLUGINS_DIR` 只在进程启动前有效），
  而 `settings.data_dir` 每次调用重读 `JZO_DATA_DIR`——所以进程内改环境变量只能换数据目录，
  换插件目录必须走子进程；写「换种子库」类测试要直接铺 `data/banks/<id>.db` 文件。
  ⑦ 真机验证插件 UI 时，宿主舞台的 iframe 是 `sandbox="allow-scripts"`（无 allow-same-origin），
  顶层脚本读不到它的 DOM、a11y 快照也进不去；要驱动真实 `plugin.js` 就在工作台页里挂一个
  **同源无沙箱**的 iframe + 手写 `jzo-plugin/1` 宿主仿真（把 `bank.*` 转发到真实 HTTP 接口），
  本次大纲树的展开/筛题证据就是这么取的。产品行为仍以真实沙箱舞台为准。
  ⑧ `build_release.bat` 自 v0.6.3 起额外排除 `.scratch*`（内含旧项目库的只读副本，铁律一禁止外发）
  与 `bank/v063.db`、`bank/v063_migrated.db`（结构基线与灌库中间产物，运行时只读 `bank.db`）；
  改打包白名单前先跑一次包体审计，别把 1.7 MB 重复库放出去。
  ⑨ **题目 ID 只能用十六进制**：存储层 CHECK 是 `id GLOB 'q_[A-Za-z0-9]*'`，
  而契约允许 `q_[A-Za-z0-9_-]{8,64}`——`secrets.token_urlsafe()` 会吐 `-`/`_`，撞上 CHECK 后
  被 `IntegrityError` 分支误报成「题目 ID 已存在」的 409，是**随机复现的假故障**
  （v0.6.4 审 `q_-t1MhFqK…` 时抓到）。`app/core/questions.py:_new_id` 已改 `token_hex(12)`；
  以后想换 ID 生成式，必须同时过契约与这条 GLOB。

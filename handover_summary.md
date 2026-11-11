# 交接文档：教材版本全量目录 + 三级折叠树 + 学校简称清洗（接力流水线）

> 本文件是三条死命令的唯一交接入口，下一会话**先读本文件再动手**。
> 接力机制：根会话逐个 `create_chat_session` 唤醒下一阶段；被唤醒的阶段会话
> 不能再开新会话。每阶段完成 → 跑测试 + 快门禁 → commit → 更新本文件 → 回报。

## 铁律（违者打回，全程有效）

- 只做当前阶段，绝不提前实现下一阶段；一阶段一闭环一提交。
- 原生 HTML/CSS/JS，**单文件严格 < 500 行**（超了拆独立模块）。
- 后端 **严禁 3 表及以上 JOIN**：分步单表查询，Python 层组装；JS 禁内联事件。
- **严禁写 JSON 文件**；配置用 TOML，报告用 MD/TOML。
- 不 push；`tools/export_schema_to_excel.py` 有他人未提交改动，**任何阶段不许 stage**。
- 提交前 `bash scripts/check-quick-gate.sh` 必须 PASS（ERROR 0；WARN 40 条为存量基线）。
- 测试只用 unittest，逐模块跑，禁止 `discover`（会零用例假绿）、禁止 pytest。
- 数据必须真实细颗粒，严禁占位骨架；新功能要能整块下架。

## 总进度

| 阶段 | 内容 | 状态 | commit |
|---|---|---|---|
| 一 | 全量穷举录入全国教材版本（只写版本，不写目录） | ✅ 2026-11-11 完成 | e447539 |
| 二 | 教材与章节三级折叠树 UI 重构 | ✅ 2026-11-11 完成 | a525854 |
| 三 | 全量学校简称智能清洗与落库 | ✅ 2026-11-11 完成 | c0aaae4 |
| 四 | 阶段二复验 + 梅河口区划挂接修复 | ✅ 2026-11-11 完成 | 见本批提交 |

---

## 阶段一已交付（本批提交）

### 需求与实现口径

- 全量穷举全国 15 个学科、小学/初中/高中三学段的真实教材版本；**只写版本**，
  `dim_textbook_chapters` 一行都不新增（铁律）。
- 版本表没有学段列，学段由「版本下挂的册次年级」反推（`dao_dimensions.version_stages`）。
  因此每个版本在每个学段只补 **1 册真实首册锚点**，例如「西师大版·一年级上册」
  「大象版·一年级上册」「沪粤版·八年级上册」，不造整册目录。
- 新增版本 id 从 201 起、册次 id 从 12001 起；编号确定、可重跑、不与旧种子撞号。

### 代码落点

- `app/bank_engine/seeds/national_catalog.py`（347 行，新增）：
  `SPECS` 共 196 条版本规格（19 条为既有版本复用，169 条新增），覆盖
  语文/数学/英语/物理/化学/生物/政治/历史/地理/科学/信息科技/体育/音乐/美术/劳动。
  `build(existing_versions, covered_stages)` 只产出缺失版本行与每版每学段首册锚点。
  `STAGE_NAMES = {"P": "小学", "J": "初中", "S": "高中"}`。
- `app/bank_engine/seeding.py`：新增 `_stage_coverage()` 与
  `NATIONAL_VERSION_ROWS / NATIONAL_BOOK_ROWS`，并入 `ALL_VERSION_ROWS / ALL_BOOK_ROWS`；
  `EXPECTED_COUNTS` 自动变更为 **版本 196、册次 479**（章节仍 3519）。
- `scripts/load_national_textbook_catalog.py`（186 行，新增）：对存量库幂等落库
  （`INSERT OR IGNORE`，id 取 `max(号段下限, 当前最大+1)`），打印全库版本统计、
  5 类非主流版本抽查、幂等重跑结果与章节目录前后行数。
- 测试：新增 `tests/test_national_textbook_catalog.py`（8 项）；同步修正
  `test_dict_console.py`、`test_dict_console_stage3.py`、`test_dict_console_subtabs.py`
  的硬编码 177/27，以及 `test_hs_textbook_catalog.py` 高中物理版本清单。

### 验收证据（2026-11-11 实跑）

- 存量库 `data/banks/org.jiuzhang.bank-engine.v2.db` 落库：
  **版本 196、册次 479、章节 3519 → 3519（零新增）**；
  重跑新增 0 版本 / 0 册次；落库前备份 `*.pre-national.bak`（gitignored）。
- 学段统计：小学 124、初中 141、高中 67（同一版本跨学科分别计数）。
- 非主流抽查命中：冀教版（语文/数学/英语/信息科技/体育）、大象版（小学科学）、
  湘少版（小学英语）、沪粤版（初中物理）、赣美版（美术）。
- 回归：`test_dict_console + stage2 + stage3 + subtabs + bank_engine_v2 + bank_api +
  file_size_contract + hs_textbook_catalog + national_textbook_catalog` 共 **183 项全绿**。
- 快门禁 PASS（6 项全过，ERROR 0，WARN 40 存量）。

### 关键数据事实

- 引擎库：`data/banks/org.jiuzhang.bank-engine.v2.db`，user_version=10，40 表。
- 教材版本 196、教材册 479、章节 3519、知识点 11388、考向 567、学校 347。
- 版本→学段过滤仍走 `dao_dimensions.list_textbook_versions(stage=...)`，
  数据已保证：每个版本声明的每个学段都有至少一册锚点。

---

## 阶段二已交付（commit a525854）

### 需求与实现口径

「实体维度字典 → 教材与章节」由「版本 → 册次 → 章 → 节」平铺树，重构为
**学段 → 科目 → 教材版本 → 册次 → 章 → 节** 的可折叠树：

- 第一层固定 **高中 / 初中 / 小学** 三节点，顺序恒定，默认全部折叠。
- 第二层按学科分组，科目行文案「数学 · 6个版本」，学段行徽标「8 个科目 · N 个版本」。
- 第三层版本完整保留双击改名（Enter/F2）、悬停删除、新增册次；
  第四层及以下沿用原册次 → 章 → 节渲染与交互，数据口径零改动。
- 搜索是剪枝树而非平铺结果：命中章节自动展开 学段/科目/版本/册次/祖先章节，
  命中行左侧色条 + 「命中」文字双通道标记，并滚动到首个命中。
- 没有学段的版本（新建待挂册次）落在按需出现的「未定学段」节点；无版本的册次
  仍挂「未挂版本」兜底节点；正常种子数据这两类节点都不出现。

### 代码落点

- `static/js/dict_console/textbook_stage_tree.js`（166 行，新增）：
  `DcTextbookStageTree.group/render/renderFallback`，只做 学段/科目 分组与渲染，
  导出 `STAGES / stageKey / subjectKey`；整块下架 = 删本文件 + HTML 一行 + 一行调用。
- `static/js/dict_console/entity_textbooks.js`（483 行，重写）：
  版本/册次/章节渲染 + 命中集合与祖先展开 + 全部既有写操作，仍在 500 行内。
- `static/dict_console.html`：新增 textbook_stage_tree.js 脚本（先于 entity_textbooks）。
- `static/css/dict_console_entities.css`：层级字号重排 + `.det-hit-row/.det-hit-flag` 命中样式。
- `tests/test_dict_console_subtabs.py`：新模块纳入「被加载 / <500 行 / 无 innerHTML·eval」契约。
- 数据源未变：`GET /api/bank/engine/textbook-versions`（stages 字段）+ `/textbooks` +
  `/meta` + `dim_textbook_chapters`；科目→版本数全在前端按 subject_id 聚合，无新表、无 schema 变更。

### 验收证据（2026-11-11 实跑）

- 逐模块回归全绿：test_dict_console 13 / stage2 27 / stage3 31 / subtabs 17 /
  bank_engine_v2 22 / file_size_contract 8。
- 快门禁 `bash scripts/check-quick-gate.sh` PASS（6 项全过，ERROR 0，WARN 40 存量）。
- 真机验证：隔离数据目录（生产库副本）+ uvicorn 8001（未碰用户 8000 进程），
  Playwright 实浏览器 15 项检查全 PASS：
  第一层恰为 高中/初中/小学 且默认折叠；折叠热区 44×44、Enter 可切换；
  科目标签含「· N个版本」；版本→册次→章节逐层展开内容正确；
  双击改名 人教A版→人教A版测 并还原；临时版本下添加册次、删除册次、删除版本；
  搜索「函数」得到 43 个展开行、每行带「命中」标记、祖先链全展开、计数「命中 31 项」；
  375px 无横向溢出；`prefers-reduced-motion` 下展开动画为 none。
  截图：`.system_generated/stage2-ui/shots/01-collapsed.png`、`02-stage-open.png`（gitignored）。

---

## 阶段三已交付（本批提交）

### 口径与结果

- 脚本 `scripts/clean_school_short_names.py`：默认只读 Dry-Run，`--apply` 才写库；
  写前自动备份到 `<db>.pre-school-shortname.bak`（已存在则复用），单事务提交逐行校验。
- 自动规则：去行政区后缀、去「第」、高级中学→高中 / 初级中学→初中 / 中学→中，
  组合为「地名+数字+中/高中」，如「绥化市第二中学」→「绥化二中」。
- 老师指定重名消歧（`OVERRIDES`）：本溪市二中 / 本溪县二中 / 本溪市高中 /
  本溪县高中 / 阜新市高中 / 阜新县高中 / 长春150中。
- 落库 200 条（199 条规则变更 + 1 条「长春市第150中学」老师点名）；
  67 条人工项保持原简称；347 校现有 278 条简称 ≠ 全称；同一地区重名 0 组。
- `school_seed.py` 已同步为清洗后简称（235 行变化），临时库重建后与线上库
  347 行 id/全称/简称逐一相等，保证重建不丢清洗结果。
- 前端学校树实测（Playwright，8001）：本溪四校、阜新两校、长春150中显示正确。
- 遗留（已在本批修复）：id 279「梅河口市第五中学」region_id 曾指向省级节点且库中
  无梅河口市，学校树计 346/347。
- 自动备份文件：`data/banks/org.jiuzhang.bank-engine.v2.db.pre-school-shortname.bak`
  （gitignored，不提交）。

---

## 阶段四已交付（本批提交）

### 阶段二复验结论

- 阶段二代码与提交 a525854 均在 HEAD 历史中，未丢失：`textbook_stage_tree.js`
  已被 `dict_console.html` 以 `?v=20261111c` 加载，线上 8000 返回的也是新版静态资源。
- 真机只读走查 15 项全 PASS：第一层恰为 高中/初中/小学 且默认折叠；科目行
  「数学 · 6个版本」；版本→册次→章逐层正确；搜索「函数」43 个命中行、父级全展开、
  均带「命中」标记；区划树「34 省 · 334 市 · 347 校」。
- 隔离库（8010 + 生产库副本）写交互 15 项全 PASS：版本双击改名并还原、
  新增/删除临时册次、删除临时版本、44px 热区、375px 无横向溢出、reduced-motion
  动画关闭。未触碰用户 8000 进程与正式库的写操作。

### 梅河口区划挂接修复

- 根因：`dim_regions` 只有省 / 地两级，梅河口市是吉林省直管县级市（国标 220581），
  原种子未收录，`match_region_id("吉林梅河口")` 只能回退到吉林省节点（id 55），
  学校 279 因此挂空、区划树少 1 校。
- 修复：`region_seed.EXTRA_CITIES` 增补「梅河口市」220581，按地级节点挂吉林；
  编号追加在末尾（id 368），既有 1-367 的 id 一律不动，避免存量学校 region_id 错位。
- 落库：新增 `scripts/fix_meihekou_region.py`（先备份 `<db>.pre-meihekou.bak`，
  单事务、幂等）。实跑结果：新增区划 1 条、重挂学校 1 条；重跑新增 0 条；
  学校 347 所 region_id 为空 0。
- 数据口径：区划 368（34 省 + 334 地级）、学校 347；期望计数改为 `len(REGION_ROWS)`。
- 回归：`test_bank_engine_v2 + dict_console ×4 + file_size + national + bank_api`
  共 177 项全绿；快门禁 PASS（ERROR 0，WARN 40 存量）。

---

## 环境与协作注意事项（逐条踩过）

- 端口 8000 的 uvicorn 是用户进程（PID 17608，旧代码、无 /dict），**别杀**；
  自测请起 8001 或动态端口，必要时提示用户重启。
- `tools/export_schema_to_excel.py` 持续挂着他人的未提交改动，显式文件清单提交。
- 根目录 `E:\jiuzhang` 不是 git 仓库；仓库在 `E:\jiuzhang\jiuzhang-operator`。
- 写鉴权是一次性轮换令牌：GET `/api/settings` 取 `local_token`，写请求带
  `X-JZO-Token`，每次写成功后轮换；前端 `DcClient.writeJson` 已封装。
- 临时引擎库：`builder.build_engine(db_path=..., schema=SCHEMA)` 自动灌全量真实种子。
- 用户是教研老师：按一线教研口径交付，不确定的版本名先核实再写，不猜。

# 交接文档：九章算子前端控制台与四栏联动字典系统（终极接力版）

> 每阶段结束后由当值会话更新本文件。下一会话**先读本文件再动手**。
> 接力机制：根会话负责逐个唤醒阶段会话；阶段会话**不得自行 create_chat_session**
> （工具约束：被委托会话不能再开新会话）。阶段会话完成 → commit → 更新本文件 →
> 结束回合回报名场面，根会话收到完成通知后唤醒下一阶段。

## 铁律（违者打回，全程有效）

- 原生 HTML/CSS/JS，严禁 React/Vue；**单文件严格 < 500 行**。
- 数据交互用 Dict/Dataclass；**严禁产生任何 JSON 文件**（配置 TOML、报告 MD/TOML）。
- 后端 SQL **严禁 3 表连级 JOIN**：分步单表查询，Python 代码层组装。
- 修改/删除字典必须**防呆拦截**：先查外键引用，被引用 → 409 + 前端「已被引用，禁止删除」。
- 不 push（用户明确暂不 push）；commit 用中文、说清为什么。
- 提交前 `bash scripts/check-quick-gate.sh` 必须 PASS（不绿不 commit）。
- 测试只用 unittest（无 pytest、无 httpx/TestClient），跑法：
  `.venv/Scripts/python.exe -m unittest tests.test_xxx -v`（禁止 discover，会零测试假绿）。

## 总进度

| 阶段 | 内容 | 状态 | commit |
|---|---|---|---|
| 一 | 控制台骨架 + 辅助栏 + 多标签机制 | ✅ 2026-11-10 完成 | `0e4e31d` |
| 二 | 字典渲染与防呆（基础五表 CRUD） | ✅ 2026-11-10 完成 | `c3ae97d` |
| 三 | 四栏联动（章节→知识点→考向→辅助知识点） | ✅ 2026-11-10 完成 | `9cce806` |
| 四 | 全量验收 + 封版 commit | ✅ 2026-11-10 完成 | `d84f9b7` |

## 阶段一已交付（commit 0e4e31d，17 文件 +1777 行）

### 新增文件（全部 dc-* 独立命名，整块可下架）

- `static/dict_console.html`（108 行）：/dict 页面骨架
- `static/css/dict_console.css`（约 345 行）：全部样式，用 app.css 设计变量
- `static/js/dict_console/` 8 个 IIFE 模块（每个 < 180 行）：
  - `catalog.js`：三大分类目录 `DcCatalog.CATEGORIES/byKey`
    - foundation 系统基石字典（6 表：dict_subjects/grades/question_types/difficulties/question_qualities/exam_types）
    - entity 实体维度字典（4 表：dim_regions/dim_schools/dim_textbooks/dim_textbook_chapters）
    - teaching 教研属性字典（5 表：dim_knowledge_points/dim_exam_directions/dict_subject_thoughts/dict_solution_methods/dict_core_competencies）
  - `client.js`：`DcClient.fetchJson` / `writeJson`（写前自动取新鲜令牌）
  - `dialog.js`：`DcDialog.open/alert/isOpen`，焦点陷阱 + Esc + 焦点归位，自包含不依赖 ws-*
  - `globals.js`：`DcGlobals`，localStorage 键 `jzo.dictConsole.globals.v1`，
    事件 `dc:globals-changed`，`query()` 只带已选参数（id 转 int）
  - `tabs.js`：`DcTabs`，open(key,title,render,{pinned}) 存在即激活；
    div.dc-tab 外壳 + button.dc-tab-main[role=tab] + button.dc-tab-close（两按钮都可聚焦）；
    面板 DOM 常驻 hidden 切换、懒渲染一次不重渲；ArrowLeft/Right/Home/End
  - `panels.js`：看板 + 分类总览（真实行数来自 /api/bank/engine/status）
  - `sidebar.js`：导航 + 一键备份（真实 API）+ 导入（如实告知随阶段二交付）
  - `main.js`：装配，`ctx.openCategory(key)` 是分类页签唯一入口
- `tests/test_dict_console.py`：10 项单测
- `tools/dict_console_probe.py`：真机探针，26 项全过

### 修改文件（最小侵入）

- `app/main.py`：+/dict 路由（FileResponse + NO_CACHE_HEADERS，带下架注释）
- `app/api/bank_engine.py`：+GET `/api/bank/engine/textbooks?subject_id=&grade_id=`
- `app/bank_engine/dao_dimensions.py`：**修 bug**——list_textbooks 的 grade_id  previously 被静默忽略
- `static/workspace.html` + `static/css/workspace_overlay.css`：左栏底「数据字典」入口锚点（.ws-dict-entry）

### 阶段一验收证据

- 单测 10/10；引擎回归 tests.test_bank_engine_v2 22/22；快门禁 6 项全过（ERROR 0，WARN 40 全是存量）
- 探针：`.system_generated/dict_console_probe/stage1/probe.toml` + 6 张截图（1440×900 与 375×780）
- 像素证据：05_backup_done.png y=450 行 P[491-948] 居中对话框、两侧 D 遮罩；
  375px 内容 x≤350 无横溢；全部交互热区 ≥44px（关闭叉 min-width/min-height 44）
- 真人路径覆盖：分类新开/激活/不重复、面板状态保留（探针标记验证）、键盘方向键/Home/End、
  关闭焦点归位、全局设置记忆+刷新还原+联动归零、details 折叠、Esc 关对话框、备份真实落盘

## 阶段二已交付（commit c3ae97d，14 文件 +1782 行）

### 新增文件

- `app/bank_engine/dao_console.py`（365 行）：规格驱动通用 CRUD 核心。
  `TableSpec` frozen dataclass（table/label/model/columns/editable/required/search/
  order/int_columns/nullable/global_filters）；`SPECS` 覆盖五表。
  全局参数绑定：subjects←subject_id、grades←stage、schools←textbook_id，
  regions/exam_types 无绑定。异常：`ConsoleLookupError`(404)、`ReferencedError`(.hits,409)、
  `ConflictError`(409)。函数：get_spec/fields_meta/list_rows/get_row/_clean_values/
  _conflict/insert_row/update_row/find_references/delete_row/import_rows。
  **引用发现走 `PRAGMA foreign_key_list` 逐子表 COUNT，全部单表查询，无 JOIN**；
  白名单标识符 + ? 占位，无 f-string 拼 SQL。
- `static/js/dict_console/row_ops.js`（163 行）：`DcRowOps.editCell/addRow/deleteRow`。
  双击/Enter/F2 → input.dc-cell-input，blur → PUT，Esc 放弃，done 标志防重复保存；
  新增行内联 tr.dc-row-new；删除走 DcDialog 确认 → DELETE，409 referenced →
  DcDialog.alert「已被引用，禁止删除」并逐条列出引用来源（label/column/count）。
- `static/js/dict_console/table.js`（210 行）：`DcTable.mount`，PAGE_SIZE=50。
  buildUrl 合并 `ctx.globals.query()`；搜索 debounce 250ms；分页 prev/next；
  globals-changed 监听刷新；可编辑 td tabindex=0 键盘可达。
- `static/js/dict_console/import.js`（84 行）：`DcImport.init`，隐藏 input accept=.toml，
  FileReader.readAsText → DcDialog 确认 → POST /dict/import {content} → 报告新增/跳过/错误。
- `tests/test_dict_console_stage2.py`（331 行）：27 项单测（service 生命周期/搜索/全局过滤/
  分页/重复冲突/被引用删除/CHECK 约束/TOML 导入 + 路由注册 + 写鉴权 + 红线）。
- `tools/dict_console_probe_stage2.py`（294 行）：真机探针 16 项，free_port + 隔离
  JZO_DATA_DIR + secrets 随机令牌；预期 409/400 的原生「Failed to load resource」与
  JzoHttp「[JZO 请求失败]」同归 http_diagnostics，不算页面缺陷。

### 修改文件（最小侵入）

- `app/bank_engine/models.py`：+Region/School/ReferenceHit/ImportReport（frozen dataclass）。
- `app/bank_engine/service.py`：+console_list/row/references/insert/update/delete/import
  薄封装（session contextmanager，dataclass 进出）；console_import 捕 ValueError→「TOML 解析失败」。
- `app/api/bank_engine.py`：+_guard 异常映射（404/409 referenced/409 conflict/400）；
  路由 POST /dict/import（**声明在 {table} 之前**）、GET /dict/{table}（q/stage/subject_id/
  textbook_id/limit/offset）、GET /dict/{table}/{id}/references、GET/POST/PUT/DELETE；
  写路由 dependencies=[Depends(require_write_token)]。
- `static/js/dict_console/catalog.js`：五表加 editable:true。
- `static/js/dict_console/panels.js`：renderCategory 拆分 editable（DcTable.mount）与
  pending（待交付卡片）；基石分类现渲染 3 张表（学科/年级/考试类型）+ 3 张待交付卡。
- `static/js/dict_console/sidebar.js`：导入按钮接 DcImport.init（去掉占位）。
- `static/dict_console.html`：脚本顺序 catalog/client/dialog/globals/tabs/row_ops/table/
  panels/import/sidebar/main/pwa。
- `static/css/dict_console.css`：+表格/搜索/单元格编辑/行按钮/分页/空态样式，
  .dc-table-scroll max-width:100% overflow-x:auto（375px 表格内滚不横溢），热区≥44px，
  prefers-reduced-motion。

### 阶段二验收证据

- 单测 27/27；引擎回归 tests.test_bank_engine_v2 22/22；骨架 tests.test_dict_console 10/10
  ——合计 **59 全绿**（`.venv/Scripts/python.exe -m unittest tests.test_dict_console_stage2
  tests.test_bank_engine_v2 tests.test_dict_console -v`）。
- 快门禁 `bash scripts/check-quick-gate.sh` **PASS（6 项全过，ERROR 0，WARN 40 全是存量）**。
- 真机探针 **PASS · 16 项**：`.system_generated/dict_console_probe_stage2/stage2/probe.toml`
  （ok=true，console_errors=[]，page_errors=[]）+ 7 张截图（01 基石表/02 搜索/03 编辑保存/
  04 被引用 409/05 实体表/06 导入报告/07 375px）。
- 防呆真实证据：删除「数学」(id=2) → 409，引用来源 教材版本 23 / 知识点 1741 / 考向 503 /
  试卷 4 / 学科思想 5 / 解题方法 11 / 核心素养 6 行；对话框逐条列出，Esc 可关。
- 375px overflow=0；全部交互热区（页签/关闭/导航/按钮/搜索/下拉/summary）min=44px。
- 全局联动证据：选「小学」后年级表只剩 6 行小学学段；TOML 导入新增 1 行并可搜索回读。

### 给阶段三的提醒

- **基石分类卡片数变了**：阶段一探针 `tools/dict_console_probe.py` 断言 foundation 6 张卡，
  阶段二把其中 3 张（学科/年级/考试类型）升级成表格，现实是 3 表 + 3 卡。
  阶段一探针属历史快照，**阶段三/四全量验收以 `dict_console_probe_stage2.py` 为准**；
  若要复跑阶段一探针需先放宽该断言（本阶段未改它，避免越界）。
- 实体维度分类的 dim_regions/dim_schools 也已 editable（表格渲染），但 dim_textbooks/
  dim_textbook_chapters 仍是待交付卡——章节树联动属阶段三。
- 五表 CRUD 的规格驱动模式（dao_console.SPECS）可复用：阶段三新增联动表读写时，
  优先考虑扩 SPECS 而非另起炉灶；但 chapter_knowledge_map/knowledge_exam_map 需先做
  schema 迁移补 sort_order 列（见下）。

## 阶段三已交付（commit 9cce806，23 文件 +2457 行）

### 数据层：引擎库 v6→v7

- `app/bank_engine/migrate_v7.py`：两张桥表（chapter_knowledge_map / knowledge_exam_map）
  补 `sort_order INTEGER NOT NULL DEFAULT 0`。
  - `backup_pre_v7` 用 sqlite backup API 落 `<db>.pre-v7.bak`，幂等；
  - 回填按主键序在组内编 0..n-1；`verify_sort_order` 校验每组连续，失败即抛；
  - `upgrade` 单事务（BEGIN/COMMIT/ROLLBACK）+ `PRAGMA user_version = 7`；
  - `rollback` DROP COLUMN 回 v6，测试已覆盖。
- `builder.migrate()` 接受 v6 并接 migrate_v7；全新建库也走同一回填。
- `paths.SCHEMA_VERSION = 7`；插件 schema.sql 同步补列与版本号。

### 后端：dao_linkage（全单表，无 JOIN）

- `app/bank_engine/dao_linkage.py`（251 行）：
  - `LINK_MAPS` 白名单（chapter_points / direction_tags）；
  - `chapter_tree`（章节单表读出，Python 层组树）、`chapter_points`/`direction_tags`
    （桥表按 sort_order 排序，知识点本体另查）、`point_directions`；
  - `reorder`：提交清单必须与现有成员集合完全一致（不多不少不重），executemany 落库；
  - `add_direction`（学科继承知识点、编码 `tp_u`+uuid、自动挂到当前点）、
    `delete_direction`（排除当前点关联后 `find_references`，仍被引用 → ReferencedError）；
  - `add_tag`（重复挂载 ConflictError、末尾追加）/ `remove_tag`（只解关联）。
- `service.py` 薄封装（`db_path` 关键字参数）；`api/bank_engine.py` +10 条联动路由，
  写路由全部 `Depends(require_write_token)`，ReferencedError→409、ValueError→400。

### 前端：四栏联动（全部 IIFE，<500 行，整块可下架）

- `linkage.js`（装配 `.dcl-grid` 四栏与级联选择）、`linkage_tree.js`（全局设置教材驱动，
  未选教材时如实提示；监听 `dc:globals-changed`）、`linkage_points.js`（双击改名 +
  `DcDnd` 拖拽/Alt+方向键排序）、`linkage_directions.js`（行内新增、双击改名、删除防呆）、
  `linkage_tags.js`（全局搜索添加、移除、拖拽排序）、`linkage_dnd.js`（共享拖拽器）。
- `dict_console_linkage.css`：4 栏 → ≤1200px 2 栏 → ≤700px 单列；热区 ≥44px。
- `panels.js` 教研分类挂载联动面板；`catalog.js` 两表标 `linkage:true` 不进待交付卡。

### 测试与证据

- `tests/test_dict_console_stage3.py`：29 项（迁移/备份/回滚/回填、树与桥表顺序、
  排序拒绝不一致、增删考向/标签、409 映射、写鉴权、红线）。
- 目录约定修正：`tests/test_file_size_contract.py` 的 PAGES 补 `static/dict_console.html`，
  否则 `dict_console.css` 会被判成孤儿资源（阶段一/二遗留，非阶段三引入，现已修复）。
- 回归：`tests.test_dict_console + stage2 + stage3 + test_bank_engine_v2 + test_bank_api +
  test_file_size_contract` 共 **147 项全绿**；快门禁 **PASS（6 项，ERROR 0，WARN 40 存量）**。
- 真机探针 **PASS · 22 项**：`.system_generated/dict_console_probe_stage3/stage3/probe.toml`
  （ok=true、console_errors=[]、page_errors=[]、http_diagnostics 2 条为预期 409），
  截图 01 树+知识点 / 02 键盘排序 / 03 新增考向 / 04 标签排序 / 05 被引用 409 /
  06 刷新后顺序 / 07 375px。
- 探针硬证据：改名/排序/标签顺序均经「刷新后重新读取」验证真落库；
  给新考向挂第二个标签再删考向 → 409 对话框列出引用来源；移除标签后删除成功。
- 像素证据：01 y=200 可见四栏色带（左树 / 中两栏 / 右设置栏）；05 y=200、y=700 全宽 D 遮罩
  + y=450 居中对话框；07 375px 内容 x≤350、四栏纵向堆叠（overflow=0）。

### 给阶段四的提醒

- 工作区仍有 `tools/export_schema_to_excel.py` 他人未提交改动：**绝不 stage**。
- 阶段一探针的「基石 6 张卡」断言已过时（阶段二起 3 表 + 3 卡）；
  全量验收以 `dict_console_probe_stage2.py` 与 `dict_console_probe_stage3.py` 为准。
- 封版 commit message 用户钦定：`前端重大升级：完成四栏联动教研字典控制台`；**暂不 push**。
- 最终验收建议：两个探针都复跑绿的 + 单测 147 项 + 快门禁 + 真机走查四阶段主路径 +
  375px + 键盘 + 409 防呆；如端到端无缺陷即可封版。

## 阶段二任务书（已完成，存档备查）

**范围：基础五表的读写与防呆**——学科(dict_subjects)、年级(dict_grades)、
行政区划(dim_regions)、考试类型(dict_exam_types)、学校(dim_schools)。

1. 后端：read（分页/搜索）/ update / insert API。沿用现有分层：
   `dao_base.py`（connect/chunks/in_sql）→ `dao_dictionary.py`/`dao_dimensions.py` →
   `models.py`（frozen dataclass）→ `service.py`（session contextmanager，dataclass 进出）→
   `app/api/bank_engine.py`（asdict 出口）。**只碰单表**。
2. 删除防呆：删任何一行前先查引用它的外键（如学科被教材/知识点/考向引用，
   年级被教材引用，学校被 exam_school_map 引用等），有引用 → HTTP 409 + 明确错误码；
   前端弹「已被引用，禁止删除」对话框（用 DcDialog）。
3. 前端：分类页签从「只读总览」升级为**表格渲染 + 搜索框**；
   **双击单元格 → 变 input，blur → PUT 保存**；新增行入口；删除按钮走防呆。
4. 全局设置三参数要真正带进字典查询（DcGlobals.query() 已就绪）。
5. 【导入数据】按钮本阶段交付真实流程（TOML 批量导入，严禁 JSON 文件）。
6. 完成后：单测 + 探针 + 快门禁 → commit（中文，标「阶段二」）→ 更新本文件 →
   结束回合回报。**不要自行开新会话**。

## 阶段三任务书（已完成，存档备查）

四栏联动：左教材章节树（全局设置驱动）→ 中章节知识点（chapter_knowledge_map，
双击改名、拖拽排序）→ 右知识点考向（knowledge_exam_map，CRUD）→
最右考向辅助知识点标签（全局搜索添加、移除、拖拽排序持久化 sort_order）。
已按 add-data-store 动线完成 v6→v7 迁移（备份/回填/自检/回滚）。

## 阶段四已交付（commit d84f9b7，验收封版）

### 交付内容

- 全量验收通过，未改动任何产品代码；新增 `tools/dict_console_probe_stage4.py`（229 行），
  补齐阶段一旧探针无法再复跑的交互证据：多标签新开/不重复/激活/关闭焦点归位、
  面板 DOM 常驻、Arrow/Home/End 切签、全局设置 localStorage 记忆与刷新还原、
  教材失效归零、辅助栏「字典维护」折叠。旧探针 `tools/dict_console_probe.py`
  的「基石 6 卡」等断言已过时，保留为历史快照，不纳入封版门禁。
- 验收证据统一落 `.system_generated/acceptance_stage4/stage4/`（gitignored，与前几阶段一致）：
  `probe.toml`（stage4 走查 17 项）、`probe_stage2.toml`、`probe_stage3.toml`、
  7+7+5 张截图与 `验收结论.md`。

### 阶段四验收证据

- 单测 **147/147 全绿**（6 模块，8.5s，未改断言）。
- 快门禁 **PASS（6 项全过，ERROR 0，WARN 40 存量）**，新增探针后复跑仍 PASS。
- 真机探针：stage2 **PASS · 16 项**、stage3 **PASS · 22 项**、stage4 走查 **PASS · 17 项**；
  三份 probe.toml 均 `ok=true`、`console_errors=[]`、`page_errors=[]`；
  `http_diagnostics` 仅预期 409（学科引用 7 类表 / 考向被桥表引用）。
- 像素结论：stage2 409 截图 y=200/700 全宽遮罩 + y=450 居中对话框；375px 内容 x≤359 无横溢；
  stage3 四栏截图 y=200 左树 P[19-380]、中栏 C[407-1106]、右栏 C[1124-1403]，
  y=700 三条独立内容带；stage3 375px 四栏纵向堆叠、内容 x≤359；折叠后右栏 y=700
  变连续 P[1117-1439] 与 `open` 断言互证。
- 走查覆盖：页签/全局记忆/折叠（stage4）+ 五表 CRUD/409/导入/375px（stage2）+
  章节树→知识点→考向→标签排序/刷新持久化/409（stage3）。

### 遗留事项

- 未 push（用户要求暂不 push）；`tools/export_schema_to_excel.py` 仍为他人未提交改动，未 stage。
- 本阶段无遗留缺陷；阶段一旧探针的过时断言如需复用，先按阶段二「3 表 + 3 卡」现状放宽。

## 关键技术事实（已核实，可直接用）

- 引擎库：`data/banks/org.jiuzhang.bank-engine.v2.db`，user_version=7（阶段三迁移），40 表。
  真实种子：15 学科、12 年级（小学/初中/高中）、16 考试类型、128 教材、3519 章节
  （2026-11-10 清洗 9 条与父章同名的空节后：3528 → 3519）、
  11388 知识点、567 考向、367 行政区划、347 学校；
  chapter_knowledge_map=74 行、knowledge_exam_map=200 行，均已带 sort_order 且组内 0..n-1。
- 已有引擎路由（`app/api/bank_engine.py`）：/api/bank/engine/meta（subjects/grades 等）、
  /status（table_count/schema_version/integrity/foreign_key_violations/counts 全表行数）、
  /textbooks（本阶段新增）、/exam-directions 等。读接口全部免鉴权。
- **写鉴权**：一次性轮换令牌。GET `/api/settings` → `local_token` → 写请求带
  `X-JZO-Token` 头；**每次写成功后令牌轮换，下次写前必须重新取**。
  DcClient.writeJson 已封装此模式，直接用。
- 备份 API：GET /api/settings/backup（视图）、POST /api/settings/backup/config
  （{local_enabled:true}）、POST /api/settings/backup/run。阶段一已接好。
- 前端报错走 JzoHttp（static/js/http.js）；宿主壳禁 innerHTML 赋值（审计 WARN）；
  JS 禁正则后行断言/eval/new Function；Python 禁 f-string 拼 SQL。
- 可访问性（AGENTS §6）：热区 ≥44px、键盘可达、焦点可见、对话框焦点陷阱+Esc+归位、
  375px 不横溢、prefers-reduced-motion。
- 探针约定：free_port() 动态端口、JZO_DATA_DIR 隔离临时目录、JZO_LOCAL_TOKEN 用
  secrets 随机（运行时从 /api/settings 读，**绝不硬编码端口/令牌**）；
  playwright 已装在 .venv（不在 requirements.txt）；证据落
  `.system_generated/<probe>/<tag>/probe.toml + shots/`；像素扫描 `tools/pixel_scan.py`。
- 临时引擎库：`builder.build_engine(db_path=..., schema=SCHEMA)` 自动落真实种子；
  隔离 JZO_DATA_DIR 首访引擎接口会自动建库（约 10 秒，探针超时已放宽到 60s）。

## 环境注意事项（逐条踩过）

- **端口 8000 的 uvicorn（PID 17608，2026-11-07 启动）跑的是旧代码，没有 /dict**。
  那是用户的进程，别杀；要演示请提示用户重启，或自起实例（阶段一验证用的是 8001）。
  start.bat 默认 8000、被占顺延 8009。
- **`tools/export_schema_to_excel.py` 有他人未提交改动，任何阶段都不许 stage 它**
  （阶段一已用显式文件清单避开；git status 里它会一直挂着）。
- FastAPI 0.141.1 的 include_router 包了一层 `_IncludedRouter`：遍历路由要递归
  `getattr(route, "original_router", None).routes`（见 tests/test_dict_console.py）。
- 审计 WARN 基线 40 条全是存量（test_workspace_restart 绝对路径、插件 dist innerHTML 等），
  新代码必须零新增；ERROR 必须 0。
- 根目录 E:\jiuzhang 不是 git 仓库；仓库在 E:\jiuzhang\jiuzhang-operator（main 分支）。
- 用户是教研老师：数据必须真实细颗粒，严禁占位骨架；功能要能整块下架
  （独立模块/独立 class，删几处锚点即可移除）；开新功能前先掂量 token 成本。
# PROJECT_MEMORY.md — 九章算子外挂大脑

本文件是给 AI 代理与接任者读的**跨会话交接底稿**。只记「不读代码就不知道、且下次会话必须知道」的事；
能从仓库现状推出的（目录结构、函数签名、依赖清单）一律不写在这里，避免与代码各说各话。

最后更新：2026-10-23（v0.6.3 结构冻结 + 首轮灌库完成）

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
| 冻结表结构 | `plugins/org.jiuzhang.core-bank/bank/schema.sql`，7 张业务表 + `bank_meta`，SHA-256 `43db4ed34725…` |
| 空库（0 数据） | `plugins/org.jiuzhang.core-bank/bank/v063.db`，155,648 B，`user_version=1` |
| 灌库产物 | `plugins/org.jiuzhang.core-bank/bank/v063_migrated.db` |
| 入表数据 | 题 456 · 大纲节点 701（册 5 / 章 18 / 节 84 / 考向 594，其中 draft 12）· 学校 347 · 试卷 27 · 题-考向 456 · 题-来源 456 · 教研笔记 150 |
| 难度口径 | 恢复 L1–L4 原码（42 / 140 / 134 / 140），不再折成 basic/medium/hard |
| 自检 | `PRAGMA foreign_key_check` 无违规，`integrity_check=ok`，全量单测 **347/347 OK** |
| 迁移工具 | `tools/build_bank_schema.py`（建空库+自检+报告）、`tools/migrate_bank_v063.py`（灌库）、`tools/verify_bank_empty.py`（逐表 COUNT 核对） |
| 审计报告 | `docs/v0.6.3-题型纠偏清单.md`、`docs/v0.6.3-灌库校验.md`、`data/bank_v063_migration_report.json` |

**现网未切**：`app/core/bank.py` + `app/api/bank.py` + `static/js/stage.js` 仍读旧宽表
`data/banks/org.jiuzhang.core-bank.db`（`bank_questions`，19 列文档表）。种子库
`plugins/org.jiuzhang.core-bank/bank/bank.db` 也仍是旧结构。因此**当前发布的 v0.6.2 包不受本轮影响**，
但新库还没被任何界面读过——「大纲树渲染 / 搜索出题」在新表上的真机验证属于下一阶段的 P0。

**字段落位裁决（主公 2026-10-23 批复）**：`tags`（含「疑似变式#N」查重噪声）丢弃不入新库；
`grade` 落 `sources`；章/节、`images`、`tikz`、`option_columns` 落 `questions.extensions` 有序数组。
两处偏离已如实记录：① 年级是**新增 `sources.grade` 列**（`ALTER TABLE`，未写进冻结的 schema.sql），
理由是塞进 `exam_type` 会让一列两套语义；② `questions.extensions` 在库里是**有序数组**
`[{key,label,value}]`，而 `schemas/question.json` 仍规定它是对象——出参适配层必须做
「数组 ↔ 反向域名对象」双向映射，否则录题插件的写入校验会崩。

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

- [ ] **API 切表**：后端 API 全部从旧宽表 `bank_questions` 切换到新的 7 张关系表上。
      `app/core/bank.py` 需重写读路径（`list_questions` / `get_question` / `stats` / `random_question` /
      `get_many`），写路径 `create_question` 要把 `schemas/question.json` 对象态 `extensions`
      落成数组态；`app/api/bank.py` 与 `static/js/stage.js` 的 `RELAY_METHODS` 需新增
      大纲树与教研笔记通道（如 `bank.topics` / `bank.topic_notes`）。
- [ ] **前端联动适配**：确保左侧大纲树（读取 `topics`，按 `parent_id` + `sort_order` 懒展开）、
      题目列表能正确展示新表数据；`difficulty` 下拉要从 basic/medium/hard 改回 L1–L4，
      `plugin.json` 的 `ui.controls` 与右栏面板同步改。
- [ ] **人工审核页开发**：针对迁移中发现的 **31 题选择题答案为空（18 题旧库连答案正文都没有 /
      9 题有【答案】标记但标记后空白 / 4 题只有通篇解析、无结论标记可依据）、
      2 题结构冲突（选项内嵌正文、拆不出选项）、26 题只挂到节层没有考向**，
      开发专门 UI 让老师一键审核/修复。
      数据入口是 `questions.extensions` 里 `org.jiuzhang.core-bank.migration` 的 flags
      （`answer_absent` / `answer_region_empty` / `type_manual_review` / `structure_conflict` /
      `topic_unmapped` / `needs_conclusion` / `solution_absent`）。
- [ ] **真机压测 + 封版**：新库跑通「大纲树渲染正常 / 右侧列表搜索出题正常」，再出 v0.6.3 包；
      封版需同步 `app/__init__.py` 版本、`index.html` 与 `static/*.html` 兜底文案、
      两份 `plugins.json`（必须全等）、`当前架构与开发进度快照.md`。

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

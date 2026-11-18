# 主项目 bank-engine 插件重构验收报告

- 验收日期：2026-11-09
- 任务代号：沙盒封盘与主项目插件借壳重生
- 结论：**通过**。插件壳已升级至 `2.0.0`，31 表新心脏、全量种子、自动建库与无 JSON DAO 全部落地；主项目快门禁 6/6 通过，全量回归 93 个模块 1797 个用例 0 失败；未 push，等待老师检阅。

---

## 一、封盘与备份

| 项目 | 结果 |
| --- | --- |
| 沙盒仓库 | `schema.sql`、种子脚本、`bank_v2_test.db` 均已入库，封盘提交 `c6d49dc` |
| 旧插件源码备份 | `E:\jiuzhang\_archive\org.jiuzhang.bank-engine.v1.0.1_20261109`（59 个文件） |
| 旧工作区安装副本备份 | `E:\jiuzhang\_archive\org.jiuzhang.bank-engine.workspace_20261109`（59 个文件，含 456 题本地库） |

旧插件目录中的业务代码、旧 schema、JSON 文件已物理清除。当前源插件目录只剩三个文件：

```text
plugins/org.jiuzhang.bank-engine/
├── LICENSE
├── plugin.toml          # version = 2.0.0，headless，bank.provider，uninstallable = false
└── bank/schema.sql      # 31 张纯关系表，PRAGMA user_version = 2
```

工作区内的已安装副本也已同步替换，插件发现实测为：`2.0.0 / headless=True / capabilities=['bank.provider'] / uninstallable=False`，命令声明保持 `bank_stats`、`bank_search`、`bank_topics` 三条不变。

---

## 二、新心脏数据规模

自动建库后逐表实测计数，与沙盒验收库完全一致：

| 表 | 行数 | 说明 |
| --- | ---: | --- |
| `dict_subjects` | 15 | 九大文化课 + 科学、信息科技、体育、音乐、美术、劳动 |
| `dict_grades` | 12 | 小学 6 + 初中 3 + 高中 3 |
| `dict_question_types` | 3 | 选择 / 填空 / 解答 |
| `dict_difficulties` | 5 | L1–L5 认知五阶，含 AI 判定提示词 |
| `dict_question_qualities` | 3 | 经典题 / 普通题 / 烂题 |
| `dict_subject_thoughts` | 22 | 学科思想 |
| `dict_solution_methods` | 34 | 解题方法 |
| `dict_core_competencies` | 47 | 核心素养 |
| `dim_textbooks` | 128 | 123 个教材册模块 + 5 册旧人教 A 版迁移册 |
| `dim_textbook_chapters` | 3528 | 全量章节树，含迁移的 102 个旧章节 |
| `dim_knowledge_points` | 11318 | 全学科细颗粒知识点，保留父子层级 |
| `dim_exam_directions` | 373 | 其中数学 309 条，其余八科各 8 条 |
| `dim_schools` | 347 | 学校字典，含地区与主用教材版本 |

`schema.sql` 含 31 张业务表；加上 FTS5 及其影子表后，SQLite 内共 36 张表。`PRAGMA integrity_check = ok`，`PRAGMA foreign_key_check` 为空。

---

## 三、自动建库机制

新增 `app/bank_engine/` 微内核，全部代码位于底座侧（插件目录不允许 Python，符合插件边界门禁）：

| 文件 | 职责 | 行数 |
| --- | --- | ---: |
| `paths.py` | schema 与数据库路径口径；开发树以仓库插件源码为准，发行包回落工作区安装副本 | 23 |
| `seeding.py` | 种子元组 → 单表 `executemany`，插入后校验 13 张核心表计数 | 148 |
| `builder.py` | 在 `.part` 临时库建表灌种，校验通过后原子替换；坏库先备份为 `.invalid-<时间>.bak` | 161 |
| `models.py` | 题目、考向、知识点、教材、章节等 Dataclass 对象映射 | 172 |
| `dao_base.py` | 连接、分片、`IN` 查询、字典映射、维度批量回表 | 135 |
| `dao_questions.py` | 按考向 / 按知识点分页查题、整题装配 | 309 |
| `dao_dimensions.py` | 考向列表、知识点树、教材与章节 | 305 |
| `service.py` | 短连接服务层、参数校验、Dataclass 出口 | 237 |
| `seeds/` | 全量种子：教材册、章节、知识点、考向、学校、教研字典 | 均低于 500 行 |

启动链路：`app/main.py` 的 `lifespan` 在 `init_db()` 后调用 `_ensure_bank_engine()`。首次启动自动建库灌种，已有合法库 0.05 秒内复用；强制重建约 0.21 秒。也可手工执行：

```bash
.venv/Scripts/python.exe scripts/build_bank_engine.py --force
.venv/Scripts/python.exe scripts/build_bank_engine.py --status
```

新库落在当前工作区的 `data/banks/org.jiuzhang.bank-engine.v2.db`，与旧 v1 库物理隔离，互不影响。

---

## 四、DAO 层与查询铁律

对象映射采用 `@dataclass(frozen=True)`，覆盖：

- 题目：`QuestionSummary`、`QuestionRecord`、`QuestionOption`、`QuestionAnswer`、`QuestionSolution`、`QuestionSupplement`、`QuestionImage`、`QuestionSource`；
- 维度：`ExamDirection`、`KnowledgePoint`、`KnowledgeNode`、`Textbook`、`Chapter`；
- 分页与状态：`QuestionPage`、`BuildReport`、`EngineStatus`。

核心接口：

```python
questions_of_direction(direction_id, limit=20, offset=0) -> QuestionPage
questions_of_point(point_id, limit=20, offset=0) -> QuestionPage
question(question_id) -> QuestionRecord | None
knowledge_tree(subject_id, grade_id=None) -> tuple[KnowledgeNode, ...]
```

实现严格遵循星型切换：

1. 关系表 `question_exam_map` / `question_knowledge_map` 作为唯一驱动表，取 `question_id` 分页；
2. 按 id 分片（每片 300）回 `questions` 主表；
3. 选项、答案、解析、备注、补充、图片、来源、考向、知识点各自单表取回；
4. 全部跨表拼装在 Python 层完成，无 3 表以上 JOIN，无 JSON。

新增代码零 `import json`，插件目录零 `.json` 文件，所有新文件不超过 500 行，已由 `tests/test_bank_engine_v2.py` 固化。

---

## 五、新旧库合并情况

| 库 | 结构 | 题目数 | 处置 |
| --- | --- | ---: | --- |
| `data/banks/org.jiuzhang.bank-engine.db`（旧引擎库） | 17 表 | 0 | 已移入归档目录，不再占用现役数据区 |
| `data/banks/org.jiuzhang.core-bank.db`（退役 core-bank） | 17 表 | 456 | 已移入归档目录；按老师指示确认为历史测试数据，直接丢弃 |
| `data/banks/org.jiuzhang.bank-engine.v2.db`（新心脏） | 31 业务表 + FTS | 0 | 现役唯一题库，承接后续录题与组卷 |

合并结论：

- 旧 `bank-engine` 库本身是空库（0 题），没有可迁移的题目，因此不存在题目复制与查重冲突；
- 真正的 456 道真题是早期测试数据，老师已明确指示**直接丢弃、不做任何迁移**；新旧库之间零搬迁、零改写；
- 全部旧库、旧测试库、旧备份与迁移报告已封存至 `E:\jiuzhang\_archive\legacy-bank-data-20261109`，现役 `data/banks/` 只保留 `org.jiuzhang.bank-engine.v2.db`；
- 旧底座读写链路（录入、待审核、导入导出、看板）继续在 `app/legacy/bank_schema_v1.sql` 上运行，不再读取插件包；插件包 `bank/schema.sql` 专供 v2 引擎；
- 新旧两条链路使用不同物理库，旧功能不回归，新引擎可独立扩展。

旧真题不再导入 v2；待前端录入界面就绪后，由老师直接重新录入新题开展测试。

---

## 六、门禁与测试证据

| 门禁 | 结果 |
| --- | --- |
| `bash scripts/check-quick-gate.sh` | **PASS（6 项全过）**：命名、插件边界、插件包结构、索引全等、静态审计、版本单源 |
| `python -m unittest tests.test_bank_engine_v2` | **16 个用例全部 PASS** |
| `python tools/run_all_tests.py` | **93 个模块 / 1797 个用例 / 失败模块 0 / 全绿** |

v2 契约测试覆盖：建库计数、已有库复用、缺失库按需自建、`integrity_check` 与 `foreign_key_check`、按考向查题、按知识点查题、整题装配、分页边界、知识点树层级、教材章节、无 JSON、500 行红线。

兼容性调整：

- 旧链路 schema 来源改为 `app/legacy/bank_schema_v1.sql`，涉及 11 个旧测试同步改口径；
- 冻结基线 `v063.db`、`v063_migrated.db` 移入 `tests/fixtures/`（旧插件包不再携带物理题库）；
- 旧工具 `build_bank_schema.py`、`verify_bank_empty.py`、`bank_io_probe.py`、`provider_uninstall_probe.py`、`migrate_bank_v063.py` 同步改用 legacy schema；
- `app/core/bank_schema.py` 保持 624 行冻结额度不增长。

---

## 七、未完成事项与风险

1. **456 道旧真题已封存丢弃**：按老师指示不做迁移，新题等录入界面就绪后重新录入。
2. **v2 尚未接入前端录入 / 待审核流程**：当前微内核以 Python 服务层与脚本提供能力，Host API 接线可作为下一阶段。
3. **未 push**：主项目与沙盒均只做本地提交，等待老师最终检阅后统一推送。

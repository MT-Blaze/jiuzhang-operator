# 题目交换契约（Question dataclass）

题目在底座、插件、导入导出之间流转的标准结构，唯一事实来源是
`app/core/question_contract.py` 里的 dataclass。字段定义与校验规则同住一处，
不存在独立的 Schema 文件，也不允许再生成 `.json` 契约文件。

- 结构版本：`2.1`（常量 `app/core/contract.py:CONTRACT_VERSION`）。
- 文本字段：Markdown + LaTeX，行内 `$...$`，独立公式 `$$...$$`。
- 全局身份只有 `id`（`q_` 前缀的稳定字符串）；原卷题号属于 `source.question_no`。
- 插件私有数据只能写进 `extensions`，键用反向域名前缀（如 `org.example.handwriting`）。
- 展示态内容（渲染后 HTML、缓存、UI 状态）不得写回题目结构。

## 入口

| 用途 | 函数 |
| --- | --- |
| 校验并得到 dataclass | `question_contract.validate(document) -> Question` |
| 仓储写入前校验 | `app.core.questions.validate_question(document)` |
| dataclass 转交换文档 | `Question.as_document() -> dict` |

`validate` 失败抛 `ContractError`，`errors` 是逐条可读原因（最多 20 条）。
仓储层再包成 `QuestionValidationError`，HTTP 层映射为 422 / 400。

## 顶层字段

必填：`schema_version`（恒为 `"2.1"`）、`id`、`type`、`stem`、`difficulty`、`meta`。
可选：`options`、`answer`、`solution`、`grade`、`tags`、`taxonomy`、`source`、
`images`、`extensions`。未知字段一律拒绝。

- `type`：`single_choice` / `multiple_choice` / `fill_blank` / `solution` / `proof` / `unknown`。
  选择题必须带 `options`；`proof` / `unknown` 在存储层会被如实拒绝，不折叠成 `solution`。
- `difficulty`：`L1` / `L2` / `L3` / `L4`；旧口径 `basic/medium/hard/novel`
  在写入前由 `contract.normalize_difficulty` 归一。

## 嵌套结构

- `options[]`：`key`（A–H）、`content`、可选 `image_ids`（≤4）。
- `answer`：`kind`（choice/text/expression/proof/unknown）、`choice_keys`、`content`、`final`。
  单选恰好 1 个选项字母，多选 2–8 个；text/expression/proof 必须给 `content`。
- `taxonomy`：`textbook` / `chapter` / `section` / `topic` / `topic_ids`。
- `source`：年份、地区、主体、学校 ID、场景、考试类型、原卷标题与题号；
  学校名不再作为新写入字段，只存 `school_id` / `school_ids`。
- `images[]`：`id`、`role`、`uri`（只收 `asset://img_*` 或 `/static/uploads/`）、
  可选 `option_key` / `alt` / `sha256` / `layout`；`role=option` 必须给 `option_key`。
- `meta`：`created_at`、`updated_at`、`revision`（≥1）、`status`、可选 `author`。

## 变更规矩

改契约必须同时改 `question_contract.py` 的 dataclass 与校验、补测试、更新本文档；
破坏性变更升 `CONTRACT_VERSION` 主版本并说明迁移方式。示例以
`examples/demo_plugin/seed/questions.toml` 为准，索引门禁会逐题校验它。

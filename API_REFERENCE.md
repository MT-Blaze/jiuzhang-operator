# API_REFERENCE.md — 九章算子插件开发接口参考（喂 AI 专用）

> 本文是**插件开发者与 AI 代写插件**的接口速查手册，覆盖三层通道：
> ① 插件 ↔ 宿主的消息协议（postMessage）；② 宿主代转的数据通道（`bank.*` / `basket.*` / `draft.*`）；
> ③ 事件总线（EventBus / JzoBus）与后端 HTTP 端点。
> 契约的唯一事实来源是 [PLUGIN_SPEC.md](PLUGIN_SPEC.md)；本文与它冲突时以 PLUGIN_SPEC 为准。
> 对应底座版本：v0.11.2（军令 #11 起新增 `bank.dashboard_stats` / `bank.dashboard_heatmap` 两个数据看板通道；
> 军令 #19 新增能力路由字典 `command.list` / `command.execute`，见 §2.18）。

---

## 0. 三十秒上手（给 AI 的硬约束）

1. 插件跑在 `sandbox="allow-scripts"` 的 iframe 里：**没有** fetch / XHR / localStorage / 父窗口 DOM。
   一切数据都要经 `window.parent.postMessage` 向宿主申请（协议 `jzo-plugin/1`）。
2. 请求封包的 `id` 必须匹配 `^[A-Za-z0-9_-]{1,80}$`——**不要拿带点号的插件 id 拼请求 id**
   （会被宿主当场拒发 `BAD_REQUEST_ID`）。官方写法：`"p" + 自增序号 + "_" + Date.now().toString(36)`。
3. 写操作（`bank.create` / `bank.update` / `bank.delete` / `basket.*` 写）需要清单里声明
   `permissions: ["questions:write"]`；写令牌由宿主代取代填，插件永远看不到令牌。
4. 只用原生 JS/CSS；公式一律 Markdown + LaTeX（`$...$` / `$$...$$`）；不引 CDN（CSP 会拦死）。
5. 通知（notification）必须幂等；请求（request）必须回响应，不认识的方法回 `UNSUPPORTED_METHOD`。

---

## 1. 消息协议（jzo-plugin/1）

三种封包，字段 `protocol` 恒为 `"jzo-plugin/1"`。

### 1.1 请求（插件 → 宿主，申请数据）

```json
{
  "protocol": "jzo-plugin/1",
  "id": "p1_lz4x8a",
  "kind": "request",
  "method": "bank.list",
  "payload": { "grade": "高一", "page": 1, "page_size": 12 }
}
```

### 1.2 响应（宿主 → 插件，原样带回 id）

成功：

```json
{ "protocol": "jzo-plugin/1", "id": "p1_lz4x8a", "kind": "response", "ok": true,
  "result": { "items": [ ... ], "total": 456, "page": 1, "page_size": 12, "total_pages": 38 } }
```

失败（`code` 常见值见 §1.4）：

```json
{ "protocol": "jzo-plugin/1", "id": "p1_lz4x8a", "kind": "response", "ok": false,
  "error": { "code": "BAD_REQUEST", "message": "缺少待写入的 question 对象", "retryable": false } }
```

### 1.3 通知（双向，单向不等回复，必须幂等）

宿主发给插件的方法/事件：

| method / event | kind | 载荷与义务 |
| --- | --- | --- |
| `plugin.activate` | request | 初始化并回 `{"ready": true}`；`payload.slot === "stage.center"` 表示接管中央画布。**30 秒内必须回** |
| `plugin.deactivate` | request / notification | 请求态回 `{"ready": false}`；通知态（`payload.reason === "lru"`）是休眠前尽力告知，不等回复 |
| `question.render` | request | 按 `payload.slot` 渲染 `payload.question`，回 `{"html": "...", "height": 数字}`；返回的 HTML 会被宿主白名单净化 |
| `ui.params.changed` | notification | `{pluginId, key, values, revisions, by}`；挂载时会补发一次当前值 |
| `theme.changed` / `locale.changed` / `question.updated` | request | 回 `{"accepted": true}` 即可 |
| `system.question_updated` | notification | 有题被创建/修改/删除/合并后宿主广播（`action` 为 `create`/`update`/`delete`/`merge`）；订阅端建议做 260–300ms 去重 |
| `basket.changed` | notification | `{action: "add"/"remove"/"clear", total, pluginId}` |
| `system.open_editor` | notification | 只发给录题插件：`{question_id, from}`，要求全量回填表单 |
| `plugin.updated` | notification | 插件被热更新后宿主广播 `{id, from, to}`；正占画布的插件会被重载 iframe |

插件可以发给宿主的通知（白名单外一律丢弃并在底栏记账）：

| event | 载荷 | 用途 |
| --- | --- | --- |
| `region.dock` | `{text}`（≤200 字，纯文本） | 往底部「输出日志区」写一行 |
| `region.left` / `region.right` | 任意 | 预留：宿主接受但不解释 |
| `stage.selection` | `{question_id, ...}` | 告知宿主当前选中题（AI 副驾感知用） |
| `system.open_editor` | `{question_id, from?}` | 请宿主开录题工作台并注入题号（三端分离的唯一改题入口） |
| `system.return_from_editor` | `{plugin_id}` | 保存后回到来源页签 |
| `system.editor_close` | `{plugin_id}` | 保存成功 1 秒后自动收起编辑页 |

清单里的声明位置：`"bus": {"subscribe": [...], "publish": [...]}`（各 ≤8 条；
`layout.*` 与 `ui.params.*` 永远发不出去）。

### 1.4 常见错误码

| code | 含义 |
| --- | --- |
| `UNSUPPORTED_METHOD` | 方法不在宿主白名单（§2 之外一律拒） |
| `BAD_REQUEST_ID` | 请求 `id` 不匹配 `^[A-Za-z0-9_-]{1,80}$`，本次未转发 |
| `BAD_REQUEST` | 载荷缺字段或形状不对（人话在 `message` 里） |
| `FORBIDDEN` | 写方法未声明 `questions:write` 权限 |
| `RATE_LIMITED` | 每页签 10 秒最多 80 次转发，稍后再试 |
| `HOST_4xx` / `HOST_5xx` | 后端接口拒绝；`retryable` 为真可重试 |
| `INVALID_PAYLOAD` | 插件自己回的载荷错误（插件 → 宿主方向） |
| `COMMAND_NOT_FOUND` / `COMMAND_TARGET_MISSING` / `COMMAND_NOT_READY` / `COMMAND_LOOP` / `COMMAND_FAILED` / `COMMAND_DENIED` / `COMMAND_RESULT_TOO_LARGE` / `COMMAND_RESULT_INVALID` / `COMMAND_BUSY` / `COMMAND_LIMIT` | 能力路由字典的调度失败，逐条含义见 §2.18 |

限流与超时：单页签 80 次 / 10 秒；单次转发 20 秒超时；宿主对插件请求 30 秒超时。

---

## 2. 数据通道（宿主代转的 `bank.*` / `basket.*` / `draft.*`）

插件发 `kind:"request"`，宿主按方法查后端再回 `result`。
**插件在 payload 里自报 `plugin_id` 一律被忽略**——身份只来自页签。

两类题库要分清：

- **插件自带库**（随包放 `bank/schema.sql` 与 `bank/bank.db`）：`bank.list` / `bank.stats` / `bank.random`，按页签自己的 id 路由，天然多库并存；
- **活跃公共题库**（provider，默认 `org.jiuzhang.bank-engine`）：`bank.get` / `bank.topics` / `bank.topic_notes` / `bank.review` / `bank.create` / `bank.update` / `bank.delete` / `bank.dashboard_stats` / `bank.dashboard_heatmap` / `bank.dedupe_scan` / `bank.dedupe_merge`，跨页签共享（查重两件更严，只开放给 provider 自己的页签**或声明 `bank.view` 的视图插件页签**，见 §2.17）。

### 2.1 题目标准结构（出参逐字符合 `schemas/question.json` 2.0）

```json
{
  "schema_version": "2.0",
  "id": "q_1a2b3c...",
  "type": "single_choice | multiple_choice | fill_blank | solution",
  "stem": "题干（Markdown + LaTeX）",
  "difficulty": "L1 | L2 | L3 | L4",
  "options": [{ "key": "A", "content": "$1$", "image_ids": [] }],
  "answer": { "kind": "choice", "choice_keys": ["A"], "final": "A" },
  "solution": "解析（Markdown + LaTeX）",
  "grade": "高一",
  "taxonomy": { "textbook": "...", "chapter": "...", "section": "...", "topic": "...", "topic_ids": ["tp_kx..."] },
  "source": { "paper_title": "...", "question_no": "12", "year": 2024, "exam_type": "...", "school": "...", "region": "..." },
  "images": ["/static/uploads/xxx.png"],
  "extensions": { "org.example.yourplugin": { "...": "私有数据只放这里，键用反向域名" } },
  "meta": { "created_at": "...", "updated_at": "...", "revision": 1, "status": "published" }
}
```

难度口径（契约 2.0）：`L1` 基础 / `L2` 中档 / `L3` 难 / `L4` 压轴。旧值 basic/medium/hard/novel
入参时由底座归一（basic→L1、medium→L2、hard→L3、novel→L4），出参只发 L 码。
`answer` 为 `null` 时出参**整个省略**该字段；非选择题的 `answer.kind` 恒为 `text`。

### 2.2 `bank.list` — 分页取题（插件自带库）

payload：

| 字段 | 类型 | 约束 |
| --- | --- | --- |
| `grade` / `difficulty` / `type` / `chapter` / `textbook` | string | 可选；`"全部"` / `"all"` 视为不过滤 |
| `topic` | string | 可选；大纲节点 id，须匹配 `^tp_(bo|ch|se|kx)[0-9a-f]{8}$` |
| `q` | string | 可选；搜索词 ≤100 字 |
| `page` | int | ≥1，默认 1 |
| `page_size` | int | 1–100，默认 20 |

result：`{items: [题目标准结构...], total, page, page_size, total_pages}`。

### 2.3 `bank.stats` — 计数统计（插件自带库，只读）

payload：无。result：

```json
{ "total": 456,
  "grades":       [{"id": "", "name": "高一", "count": 420}],
  "difficulties": [{"id": "", "name": "L3",   "count": 134}],
  "types":        [{"id": "", "name": "single_choice", "count": 200}],
  "chapters":     [{"id": "tp_ch...", "name": "...", "count": 23}],
  "textbooks":    [{"id": "tp_bo...", "name": "...", "count": 456}],
  "meta": { "...": "bank_meta 表的键值" } }
```

### 2.4 `bank.get` — 单题全文（活跃公共题库）

payload：`{"id": "q_..."}`（须匹配 `^[A-Za-z0-9_-]{1,80}$`）。result：题目标准结构。查无回 `HOST_404`。

### 2.5 `bank.random` — 随机一题（插件自带库）

payload：同 `bank.list` 的筛选字段（无分页）。无匹配回 `HOST_404`。

### 2.6 `bank.create` — 新增题目（活跃公共题库，需 `questions:write`）

payload：`{"question": {题目标准结构}}`。`id` / `meta` 由底座生成，请求里带的会被覆盖。
result：落库后的完整题目。宿主随后广播 `system.question_updated`（`action:"create"`）。
校验失败回 `HOST_422`（`message` 里带逐字段错误）。

### 2.7 `bank.update` — 修改题目（活跃公共题库，需 `questions:write`）

payload：`{"id": "q_...", "question": {补丁字段, "clear_flags": ["answer_absent"]}}`。
只接受题目内容补丁与清除审核标记；大纲挂载与来源关系不在此通道改。
result：更新后的完整题目；宿主广播 `system.question_updated`（`action:"update"`）。

### 2.8 `bank.delete` — 删除题目（活跃公共题库，需 `questions:write`）

payload：`{"id": "q_..."}`。关联表级联摘净，共享的来源/学校/大纲节点保留；删后自动从题篮摘除。
result：`{"id": "...", "deleted": true}`；宿主广播 `system.question_updated`（`action:"delete"`）。

### 2.9 `bank.topics` — 大纲树懒展开（活跃公共题库）

payload：`{"parent_id": "tp_bo...", "q": "搜索词"}`（两者皆可选；不给 `parent_id` 取册层）。
result：

```json
{ "items": [{ "id": "tp_ch...", "parent_id": "tp_bo...", "name": "1. 集合与常用逻辑用语",
              "layer": "chapter", "path": "tp_bo.../tp_ch...", "sort_order": 0, "status": "active",
              "has_children": true, "question_count": 23, "note_count": 2 }],
  "total": 18, "parent_id": "tp_bo..." }
```

`layer` ∈ `textbook`（册）/ `chapter`（章）/ `section`（节）/ `topic`（考向）。

### 2.10 `bank.topic_notes` — 考向教研笔记（活跃公共题库）

payload：`{"topic_id": "tp_kx..."}`。result：

```json
{ "topic": { "id": "...", "name": "...", "path": "...", "status": "active" },
  "notes": [{ "id": 1, "note_type": "method | pitfall | knowledge | insight",
              "content": "...", "sort_order": 0 }] }
```

### 2.11 `bank.review` — 待审队列（活跃公共题库）

payload：`{"flag": "", "page": 1, "page_size": 20}`。`flag` 取 `""`（=any，全部待审）或
`answer_absent` / `answer_region_empty` / `type_manual_review` / `structure_conflict` /
`topic_unmapped` / `needs_conclusion` / `solution_absent` 之一。
result：`{items, total, page, page_size, total_pages, summary: {total, flags: [{name, count}], known_flags}}`。

### 2.12 `bank.dashboard_stats` — 数据看板四数 + 最近录入（军令 #11 新增，只读）

payload：无。result：

```json
{ "plugin_id": "org.jiuzhang.bank-engine",
  "date": "2026-10-23",
  "total_questions": 456,
  "today_added": 5,
  "pending_review": 209,
  "stored_total": 247,
  "recent": [ { "id": "q_...", "type": "single_choice", "difficulty": "L3",
                "stem": "题干前 80 字…", "created_at": "2026-10-23T11:00:00+08:00" } ] }
```

口径：`total_questions` = 题库总行数；`today_added` = 按 `created_at`（东八区本地日）等于今天的入库数；
`pending_review` = 仍带未清审核标记的题数（与 `bank.review` 的 `flag=any` 同判据）；
`stored_total` = `total_questions − pending_review`（已清审正式落库数）；`recent` 恒为最近 5 条摘要。

### 2.13 `bank.dashboard_heatmap` — 365 天入库热力图（军令 #11 新增，只读）

payload：无（HTTP 直连时可带 `?days=N`，1–3650，默认 365）。result 是**裸数组**，含今天、逐日补零：

```json
[ { "date": "2025-10-24", "count": 0 },
  { "date": "2026-10-23", "count": 5 } ]
```

### 2.14 `basket.list` / `basket.add` / `basket.remove` / `basket.clear` — 工作区题篮

题篮是**工作区级**的易失集合（组卷/讲义的取料筐），与具体哪个库无关。

| 方法 | payload | result |
| --- | --- | --- |
| `basket.list` | `{"expand": true}`（可选，附题目全文） | `{items: [{question_id, plugin_id, question?}], total, missing?}` |
| `basket.add` | `{"plugin_id": "自己", "ids": ["q_..."]}` 或 `{"id": "q_..."}` | `{items, total}`；≤200 个 id，全部必须存在于该插件自己的题库，否则整批拒绝 |
| `basket.remove` | `{"question_id": "q_..."}` | `{items, total}` |
| `basket.clear` | 无 | `{items: [], total: 0}` |

写题篮由宿主代取一次性令牌；成功后宿主广播 `basket.changed`。

### 2.15 `draft.save` / `draft.load` — 宿主代持草稿（本地易失态）

沙箱 iframe 是不透明源，插件访问 localStorage 会抛异常；草稿只能交宿主代持，
按 `plugin.id` 分命名空间（A 插件读不到 B 插件的草稿）。**不进库、不出网。**

| 方法 | payload | result |
| --- | --- | --- |
| `draft.save` | `{"key": "form", "value": {...}}`；`value: null` 即清除 | `{ok: true, saved_at}` 或 `{ok: false, reason}`（键不合法 / 超过 200,000 字符 / 配额满） |
| `draft.load` | `{"key": "form"}` | `{ok: true, value}`（没存过则 `value: null`） |

`key` 须匹配 `^[A-Za-z0-9_.:-]{1,80}$`。

### 2.16 `asset.upload` — 上传框选配图（需 `assets:write`）

录题插件把 Canvas 截出的图交给宿主，宿主代取写令牌落进当前工作区 `uploads/`。
**只接受 PNG / JPEG / WebP（按魔数复核），解码后 ≤8 MiB；文件名由底座生成**，
远程 URL、`data:` 直链与 SVG 一律不落盘。

| 方法 | payload | result |
| --- | --- | --- |
| `asset.upload` | `{"data_url": "data:image/png;base64,..."}` | `{id: "img_...", uri: "/static/uploads/img_....png", mime, bytes, sha256}` |

`uri` 可直接写进题干（`\includegraphics{/static/uploads/...}`）和 `images[].uri`；
题目里的 `images[].id` 用返回的 `id`。未声明 `assets:write` 时宿主回 `FORBIDDEN`。

### 2.17 `bank.dedupe_scan` / `bank.dedupe_merge` — 查重清洗（军令 #18-终 阶段五新增）

**只开放给当前活跃题库 provider 自己的页签，或声明 `bank.view` 的视图插件页签**
（军令 #20 起题库视图是独立插件 `org.jiuzhang.bank-ui`，默认 provider 是
`org.jiuzhang.bank-engine`）。扫描要读全库、合并要真删副本行，所以别的插件
哪怕猜对方法名也只拿到 `FORBIDDEN`；两个题库插件都不声明 `questions:write`——
三端分离不破，改题目内容仍然只有录题工作台能干，这条通道只做「同题收敛」的库内清洗。
HTTP 端点、指纹口径与合并语义见 §3.1 的 `duplicates` / `duplicates/merge` 两行，逐字一致。

| 方法 | payload | result |
| --- | --- | --- |
| `bank.dedupe_scan` | 无 | `{plugin_id, scanned, group_count, redundant, truncated, groups[]}`（`groups[]` 形状同 §3.1） |
| `bank.dedupe_merge` | `{"primary_id": "q_x", "copy_ids": ["q_y", ...]}`；`copy_ids` 1–20 条，两端 id 都须匹配 `^[A-Za-z0-9_-]{1,80}$` | 合并出参（`moved` / `solution_appended_from` / `questions_after` / `primary` 等，见 §3.1） |

`bank.dedupe_merge` 的写令牌由宿主代取代填，插件看不到令牌；载荷不合法回 `BAD_REQUEST`，
后端核对不过回 `HOST_4xx` 且**整事务回滚**（不会出现「题删了、挂载还挂着」）。
合并成功后宿主广播一次 `system.question_updated`（`action:"merge"`，`id` 为保留项），
题篮/组卷/讲义等下游视图据此重取；副本 id 同时自动退出题篮。

### 2.18 `command.list` / `command.execute` — 能力路由字典（军令 #19 新增）

插件之间**不直连**：要在清单里公开自己的能力，就用 `contributes.commands` 登记一个命令 id；
想用别人的能力，先查表再请宿主转发。完整规则（命名空间、五大分类、错误码、自动开页语义）见
PLUGIN_SPEC §2.14，这里只给调用形状。

清单声明（顶层，最多 32 条；id 为小写反向域名、至少三段、段内可用 `_`，≤96 字符）：

```json
"contributes": {
  "commands": [
    {"id": "com.zhang.bank.tidy_tags", "title": "整理标签"},
    {"id": "com.zhang.bank.export_word", "title": "导出为 Word", "requires_user": true}
  ]
}
```

`org.jiuzhang.*` 只能由插件 id 同以 `org.jiuzhang.` 开头的官方插件声明；官方命令还须落在
`org.jiuzhang.action.{input,process,output,data,view}.` 之下并通过 `command.list` 自查。
第三方越权声明逐条进 `GET /api/plugins` 的 `commands_rejected`，不拒装、也不生效。
`requires_user: true` 表示**高副作用**：宿主转发前弹一次用户确认，拒绝即回 `COMMAND_DENIED`。

| 方法 | payload | result |
| --- | --- | --- |
| `command.list` | 无 | `{commands: [{id, title, plugin_id, plugin_name, requires_user}]}`（按 id 升序，停用插件不在表里） |
| `command.execute` | `{"command_id": "com.zhang.bank.tidy_tags", "context": {...}}`；`context` 序列化后 ≤16384 字符 | `{command_id, plugin_id, result}`；`result` 是目标插件自己的回包，序列化后 ≤65536 字节 |

目标插件收到的宿主请求：

```js
payload = { command_id, context, from, trace }
// from  = 调用方插件 id（宿主按页签判定，不信自报）
// trace = 宿主盖章的转发链；自己塞的链路会被截断，满 4 跳回 COMMAND_LOOP
```

目标没有页签时宿主**自动开一页**并等 `plugin.activate` 就绪（上限 10 秒，超时回
`COMMAND_NOT_READY`）；休眠页签先唤醒。目标插件只处理清单声明过的 id，其余回
`UNKNOWN_COMMAND`。**`context` 是线索不是授权**：别的插件可以编造任意内容，
要动数据仍走对应 Host API 的权限校验。

宿主侧四道调用安全闸（插件不用配合，但要知道会收到什么）：

- **确认**：`requires_user` 命令在转发前弹用户确认；拒绝/Esc/点遮罩一律 `COMMAND_DENIED`，
  目标插件不会收到请求；
- **结果上限**：>65536 字节回 `COMMAND_RESULT_TOO_LARGE`，无法序列化回 `COMMAND_RESULT_INVALID`；
- **串行排队**：同一目标页签/面板的命令依次执行；排队或执行超过 1 秒先收到
  `notification {event:"command.pending", payload:{command_id, code:"COMMAND_PENDING"}}`，
  这不是失败回执，真实结果随后仍会回来；同一目标挂起超过 8 条回 `COMMAND_BUSY`；
- **自动开页上限**：命令自动开出的画布页签累计最多 5 个（不含老师手动开的），超过回 `COMMAND_LIMIT`。

---

## 3. 后端 HTTP 端点参考（同源页面 / 调试用；沙箱插件**不能**直接访问）

只读接口本机开放；带 ✍ 的必须携带一次性写令牌 `X-JZO-Token`（令牌从 `GET /api/settings` 取，用后即焚、会轮换）。

### 3.1 题库与看板

| 方法与路径 | 说明 |
| --- | --- |
| `GET /api/bank/dashboard/stats` | 看板四数 + 最近 5 题（活跃题库；字段同 §2.12） |
| `GET /api/bank/dashboard/heatmap?days=365` | 按日入库裸数组（`days` 1–3650，默认 365；字段同 §2.13） |
| `GET /api/bank/provider` | 当前活跃题库 provider（含 `fallback_reason`） |
| `GET /api/bank/provider/candidates` | 可被选为题库的已装插件 |
| ✍ `POST /api/bank/provider` | 切换活跃题库：`{"plugin_id": "..."}` |
| `GET /api/bank/textbooks` | 教材版本清单 + 当前工作区生效版本（`active_textbook_id`） |
| `GET /api/bank/plugins/{plugin_id}/stats` | 题库统计 |
| `GET /api/bank/plugins/{plugin_id}/questions?grade=&difficulty=&type=&chapter=&textbook=&topic=&q=&page=&page_size=` | 分页取题 |
| `GET /api/bank/plugins/{plugin_id}/questions/{question_id}` | 单题详情 |
| ✍ `POST /api/bank/plugins/{plugin_id}/questions` | 新增：`{"question": {...}}` → 201 |
| ✍ `PATCH /api/bank/plugins/{plugin_id}/questions/{question_id}` | 审核回写：`{"question": {..., "clear_flags": [...]}}` |
| ✍ `DELETE /api/bank/plugins/{plugin_id}/questions/{question_id}` | 删题（级联摘关联、保留共享节点） |
| `GET /api/bank/plugins/{plugin_id}/topics?parent_id=&q=&textbook_id=` | 大纲树懒展开；根层与搜索按教材版本过滤，考向并集照常出现 |
| `GET /api/bank/plugins/{plugin_id}/topics/{topic_id}/notes` | 考向教研笔记 |
| `GET /api/bank/plugins/{plugin_id}/review?flag=&page=&page_size=` | 待审队列 |
| `GET /api/bank/plugins/{plugin_id}/random?...筛选同 list` | 随机一题（无匹配 404） |
| `GET /api/bank/plugins/{plugin_id}/duplicates` | 查重扫描（**只读、不鉴权**）：全库标准化 → 指纹 → 返回 ≥2 题的重复组。出参 `{plugin_id, scanned, group_count, redundant, truncated, groups[]}`；`groups[]` = `{fingerprint, count, type, ids[], differing_fields[], documents[]}`，`documents` 逐题符合 §2.1（与题库浏览器同源，双栏审查面板不必再逐题取详情）。指纹只吃到排版级归一：定界符、全半角、中文句读、多余空格、选项顺序、配图 URI 参与归一，**答案/解析/难度/年级/考向挂载/来源不参与**，其差异全列进 `differing_fields` 给老师看；ASCII `!`（阶乘）、`:`（比）、`()`（分组）一个都不吞——宁可漏报也不误报，误报的下一站是删数据 |
| ✍ `POST /api/bank/plugins/{plugin_id}/duplicates/merge` | 收敛合并：`{"primary_id": "q_x", "copy_ids": ["q_y", ...]}`，需写令牌。保留项的题干/选项/答案/难度/题型一字不动，只把副本的考向挂载（主挂载不顶替）、来源关系（同卷同题号并一行）、单题备注 `extensions`（副本独有的键搬走；同名键**保留项赢**且只报冲突不合成，AGENTS §3）与不同解析（按「解法二/三…」追加）并过来；副本行随事务真删除（存储层无软删列）。搬完先核对（行数、副本无残留、解析/备注落库、挂载与来源集合、`foreign_key_check`、`integrity_check`）**才提交**，任一不过即整事务回滚。出参 `{primary_id, merged[], same_fingerprint, fingerprint_mismatch[], moved{topics,sources,extensions,conflict_extensions}, solution_appended_from[], questions_before, questions_after, primary}`。一次最多 20 条副本；合并成功后这些 id 自动退出题篮 |
| `GET /api/bank/export` | 导出当前工作区题库为标准交换包 `.json`（`Content-Disposition: attachment`；`{format, format_version, schema_version, exported_at, plugin_id, count, questions}`） |
| ✍ `POST /api/bank/import` | 批量导入题目包：`{"filename", "content_base64", "mode": "upsert"\|"skip"}`；`.json`（单题/数组/`questions` 交换包）或 `.zip`（内含 `.json`）。宿主逐题校验 `schemas/question.json`，一题不过整批回滚并逐题报错（422） |

### 3.2 题篮

| 方法与路径 | 说明 |
| --- | --- |
| `GET /api/basket?expand=true` | 读题篮 |
| ✍ `POST /api/basket` | 加题：`{"plugin_id", "ids": [...], "mode": "append"|"replace"}` |
| ✍ `DELETE /api/basket/{question_id}` | 移除一题 |
| ✍ `DELETE /api/basket` | 清空 |

### 3.3 插件管理

| 方法与路径 | 说明 |
| --- | --- |
| `GET /api/plugins` | 发现已安装插件：`{plugins: [...], rejected: [{id?, reason}], commands: [...], commands_rejected: [...]}`；每个 plugin 带 `protocol` / `entry_url` / `assets` / `min_host_version` / `capabilities` / `commands`（自己在 `contributes.commands` 里声明的命令）等宿主回填字段；顶层 `commands` 是启用插件的全局字典（同 id 先到先得），`commands_rejected` 记越权命名空间与 id 冲突（`capabilities` 是设置页识别题库引擎、置灰「不保留数据」的唯一判据） |
| ✍ `POST /api/plugins/install?replace=false` | 本地 zip 安装（请求体即 zip 二进制，≤50 MB；暂存区校验 + 原子落地；同名默认 409，`replace=true` 才覆盖） |
| ✍ `POST /api/plugins/install-url` | 在线安装单个 zip：`{"url", "mirrors": [...], "replace": false}`（地址守卫同索引拉取） |
| ✍ `POST /api/plugins/index` | 拉取插件索引：`{"url", "allow_mirrors": true}`；只读 GET，不解压不执行；官方地址失败按 gh-proxy → ghfast → jsDelivr → fastly.jsDelivr → Raw 换源 |
| ✍ `POST /api/plugins/{plugin_id}/enabled` | 启用/停用：`{"enabled": true|false}`（只写 `data/plugin_state.json`，绝不碰代码与数据） |
| ✍ `DELETE /api/plugins/{plugin_id}?keep_data=true|false` | 卸载；`keep_data=false` 销毁**当前工作区**内该插件的物理 `.db`（含边车，默认 `true` 只删代码目录）。声明 `capabilities: ["bank.provider"]` 的题库引擎**免死**：无视该参数一律保数据，回包 `provider_guarded=true` |
| ✍ `POST /api/plugins/update/check` | 双轨更新·检查：`{"url"?, "allow_mirrors"?}`；给了 `url` 才出网拉一次索引，否则复用本机缓存。回 `{host, plugins[], summary, index_source}`，每条带 `state`（`update_available` / `incompatible` / `up_to_date` / `not_in_index` / `bad_entry`）与 `reason` |
| ✍ `POST /api/plugins/update/apply` | 双轨更新·下载并热更：`{"all": true}` 或 `{"ids": [...]}`；只处理 `update_available`，其余进 `skipped`；回 `{updated[], failed[], skipped[], host}`。只覆盖 `plugins/<id>/`，新包同名数据文件以本地为准，新包没带的本地文件原地保留 |
| `GET /api/plugins/update/pending` | 重启续更待办：读 `data/update_state.json`，附本次进程 `last_resume` |
| ✍ `POST /api/plugins/update/pending-clear` | 作废续更待办（补齐跑完或用户明确清空） |
| ✍ `POST /api/plugins/update/host-apply` | 底座自更新：`{"launch": false}` 只下载校验并生成 `%TEMP%\jzo_update_<pid>.bat`；`launch=true` 才交接脚本并退出自身（开发工作树有 `.git` 时 409 `dev_worktree`）。回 `{version, current, script_path, staged_at, excluded_dirs, launchable}` |

### 3.4 工作区 / 设置 / 健康

| 方法与路径 | 说明 |
| --- | --- |
| `GET /api/workspaces` | 列工作区（带 `question_count` / `is_active`） |
| ✍ `POST /api/workspaces/switch`、`POST /api/workspaces`、`POST /api/workspaces/import`、`POST /api/workspaces/textbook`、`DELETE /api/workspaces/{id}` | 切换 / 新建 / 导入 .db / 选教材版本 / 删除。**切换、新建、导入都要重启底座**（每个工作区的插件目录、启停状态、`.env` 各自独立，不重启就是拿旧区的插件读新区的库）：回包带 `restarting` 与本次进程 `boot_id`，前端据此轮询 `/healthz`，看到**新** `boot_id` 才重载页面。`POST /api/workspaces` 可带 `textbook_id`（`tb_` + 8 位 hex）随新建一次登记，省掉重启后再补一刀的竞态。单测/受控环境设 `JZO_RESTART_DISABLED=1` 只切指针、不重启 |
| `GET /api/settings` | 系统设置：一次性写令牌 `local_token` 与当前工作区 `workspace_id`（宿主壳据此给草稿箱分箱） |
| `GET /api/startup` | 启动行为：`{target, effective, kind, plugin_id, plugin_name, fallback_reason, candidates[]}`。`candidates` 就是设置页下拉的数据源（**只列已启用插件**）。所配插件被卸载/停用时 `effective` 回落 `chat`、`fallback_reason` 说明原因、`target` 原地保留（军令 #11 阶段三） |
| ✍ `POST /api/startup` | 保存启动行为：`{"target": "chat" \| "plugin:<id>"}`。写入严格——形状非法、插件未安装或已停用一律 400，不落盘 |
| `GET /healthz` | 健康检查：`{status, service, version, boot_id, time}`。`boot_id` 每次进程启动随机换一个，是「新进程真的起来了」的唯一凭据（军令 #18-续4） |

### 3.5 AI Agent（宿主自用，插件不经此通道）

`POST /api/agent/chat`（对话）、`POST /api/agent/refine`（AI 副驾改写题干/解析，只回候选文本不落库）、
`POST /api/agent/split`（拆题）、`POST /api/agent/review`（审题）。缺密钥时 Mock 原样回显、`mock: true`，绝不编造。

### 3.6 题目配图

| 方法与路径 | 说明 |
| --- | --- |
| ✍ `POST /api/assets` | 上传框选配图：`{"data_url": "data:image/png;base64,..."}` → 201 `{id, uri, mime, bytes, sha256}`；只收 PNG / JPEG / WebP，魔数必须与声明一致，解码后 ≤8 MiB，文件名由底座生成 |
| `GET /static/uploads/{path}` | 读取当前工作区配图；拒绝 `..`、符号链接与非图片扩展名 |

---

## 4. 出网铁律（写插件前必读）

- 底座**严禁**后台静默自动拉取：没有定时器、没有启动顺手检查、没有可见性轮询。
- 仅存的出网口子全部由用户**当场点击**发起：【拉取清单】【在线安装】【检查更新】【更新】/【一键更新全部插件】【底座更新并重启】。
- 插件自身 `connect-src 'none'`：**任何**网络请求都发不出去，也别申请——白嫖条款（PLUGIN_SPEC §1.1）禁止联网回连校验。
- 更新只写 `plugins/<id>/` 代码目录与底座程序文件，**严禁触碰 `data/`**（老师的题库是财产；
  唯一例外 `data/update_state.json`，只存版本号与待办 id）。

---

## 5. 最小可用插件骨架

```javascript
(function () {
  "use strict";
  var PROTOCOL = "jzo-plugin/1";
  var seq = 0;
  var pending = new Map();

  function call(method, payload, timeoutMs) {
    return new Promise(function (resolve, reject) {
      seq += 1;
      var id = "p" + seq + "_" + Date.now().toString(36);   // 别用带点号的插件 id！
      var timer = setTimeout(function () {
        pending.delete(id);
        reject(new Error(method + " 超时"));
      }, timeoutMs || 15000);
      pending.set(id, { resolve: resolve, reject: reject, timer: timer });
      window.parent.postMessage({
        protocol: PROTOCOL, id: id, kind: "request", method: method, payload: payload || {}
      }, "*");
    });
  }

  window.addEventListener("message", function (event) {
    var msg = event.data;
    if (!msg || msg.protocol !== PROTOCOL) return;
    if (msg.kind === "response") {
      var waiter = pending.get(msg.id);
      if (!waiter) return;
      pending.delete(msg.id);
      clearTimeout(waiter.timer);
      if (msg.ok) waiter.resolve(msg.result || {});
      else waiter.reject(new Error((msg.error && msg.error.message) || msg.error.code));
      return;
    }
    if (msg.kind !== "request") return;   // notification：按需订阅，幂等处理
    if (msg.method === "plugin.activate") {
      event.source.postMessage({ protocol: PROTOCOL, id: msg.id, kind: "response",
        ok: true, result: { ready: true } }, "*");
      // 接管画布后自己取数：call("bank.dashboard_stats").then(render)
      return;
    }
    if (msg.method === "plugin.deactivate") {
      event.source.postMessage({ protocol: PROTOCOL, id: msg.id, kind: "response",
        ok: true, result: { ready: false } }, "*");
    }
  });
})();
```

配套清单要点（完整字段表见 PLUGIN_SPEC §2.3.2）：目录名 = `id`；`entry.frontend` 必须在 `dist/` 下；
根目录必须有 Apache-2.0 的 `LICENSE`；接管画布要 `"slots": [..., "stage.center"]` + `"stage": {...}`；
zip 顶层目录名即插件 id，纯 zip 解压即用。

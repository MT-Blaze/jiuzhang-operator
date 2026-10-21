# 九章算子插件接入规范（Plugin Spec）

- 规范版本：`1.0`
- 协议标识：`jzo-plugin/1`
- 发布日期：2026-10-21
- 状态：契约先行。底座 `v0.1.0` 尚未实现插件宿主，`v0.2.0` 起按本规范实现。

本规范规定两件事：**底座如何把题目数据递给插件**，以及**插件如何把渲染结果交回底座**。凡与本规范冲突的实现，以本规范为准。

## 1. 边界与角色

| 角色 | 职责 |
| --- | --- |
| Host（底座） | 鉴权、导航、数据总线、题目加载、资产解析、插件生命周期、HTML 净化、公式渲染、错误隔离 |
| Plugin（插件） | 单一领域能力：渲染、导入、导出、工具面板等；只消费授权数据，只返回声明过的结果 |
| Slot（插槽） | 底座预留的 UI 位置，例如 `question.card`、`question.detail` |
| Bus（数据总线） | Host 与插件之间唯一的通信通道，使用本规范的 JSON 信封 |

底座不得把数据库连接、文件路径、环境变量、模型密钥交给插件。插件不得假设自己与宿主同源，也不得直接操作宿主 DOM。

## 2. 插件包结构

```text
plugins/
└── com.example.classic-card/
    ├── plugin.json           # 清单（必需）
    ├── README.md             # 插件说明（建议）
    ├── LICENSE               # 插件自身许可（必需）
    └── dist/
        ├── index.html        # 前端入口（必需）
        ├── plugin.js
        └── plugin.css
```

- 一个目录一个插件，目录名必须等于清单中的 `id`。
- `dist/` 内不得包含符号链接、可执行文件、数据库文件或密钥。
- 插件资源由宿主以只读方式挂载到 `/plugin-assets/<id>/`，插件不得引用外网资源。

## 3. 插件清单 `plugin.json`

```json
{
  "schema_version": "1.0",
  "id": "com.example.classic-card",
  "name": "经典题卡",
  "version": "0.1.0",
  "api_version": "1.0",
  "kind": "renderer",
  "description": "以传统试卷风格渲染题目卡片。",
  "author": "示例作者",
  "license": "Apache-2.0",
  "entry": {
    "frontend": "dist/index.html"
  },
  "slots": ["question.card", "question.detail"],
  "capabilities": ["question.render"],
  "permissions": ["questions:read", "assets:read"],
  "config_schema": "schemas/config.json"
}
```

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `schema_version` | string | 是 | 清单结构版本，当前固定 `"1.0"` |
| `id` | string | 是 | 反向域名格式：`^[a-z0-9]+(\.[a-z0-9-]+)+$`，全局唯一，不可变更 |
| `name` | string | 是 | 展示名称，1–64 字符 |
| `version` | string | 是 | 插件自身语义化版本，如 `0.1.0` |
| `api_version` | string | 是 | 依赖的 Host API 主版本；当前支持 `1.x` |
| `kind` | string | 是 | `renderer` / `importer` / `exporter` / `tool` |
| `description` | string | 是 | 一句话说明，1–200 字符 |
| `author` | string | 否 | 作者或组织 |
| `license` | string | 是 | SPDX 标识；必须与 `LICENSE` 一致 |
| `entry.frontend` | string | 是 | 入口 HTML，相对插件根目录，禁止 `..` |
| `entry.backend` | string | 否 | 后端入口，见第 11 节（保留） |
| `slots` | string[] | 是 | 申请的插槽；渲染类插件至少一个 |
| `capabilities` | string[] | 是 | 声明提供的能力，见第 5 节 |
| `permissions` | string[] | 是 | 申请的权限，见第 9 节；最小权限原则 |
| `config_schema` | string | 否 | 插件配置的 JSON Schema 路径 |
| `integrity` | object | 否 | `{"algorithm":"sha256","digest":"..."}`，发布包建议提供 |

清单校验失败、`api_version` 主版本不兼容、申请未定义权限，均拒绝加载，并记录原因。

## 4. 数据流

```text
用户打开题卡
   │
   ▼
Host：按 id 读取题目 → 校验 schemas/question.json → 深拷贝并冻结
   │
   ├─→ Host：解析 images[].uri 为可访问 URL（仅授权资产）
   │
   ▼
Host → Plugin：question.render（题目快照 + 视图 + 主题 + 资产表）
   │
   ├─→ Plugin → Host：host.asset.resolve（按需，可选）
   │
   ▼
Plugin → Host：{ html, css, height }
   │
   ▼
Host：净化 HTML → 渲染数学 → 注入 CSS → 挂载到插槽
```

### 4.1 Host → Plugin：`question.render`

```json
{
  "protocol": "jzo-plugin/1",
  "id": "01J9Z3K4M5N6P7Q8R9S0T1V2W3",
  "kind": "request",
  "method": "question.render",
  "payload": {
    "question": {
      "schema_version": "1.0",
      "id": "q_01J9Z3K4M5N6P7Q8R9S0T1V2W3",
      "type": "single_choice",
      "stem": "已知集合 $A=\\{1,2\\}$，则 $A$ 中元素的个数为（　　）",
      "options": [
        { "key": "A", "content": "$0$" },
        { "key": "B", "content": "$1$" },
        { "key": "C", "content": "$2$" },
        { "key": "D", "content": "$3$" }
      ],
      "answer": { "kind": "choice", "choice_keys": ["C"] },
      "solution": "由题意得 $A=\\{1,2\\}$，故元素个数为 $2$。",
      "difficulty": "basic",
      "tags": ["集合"],
      "meta": {
        "created_at": "2026-10-21T20:00:00+08:00",
        "updated_at": "2026-10-21T20:00:00+08:00",
        "revision": 1,
        "status": "published"
      }
    },
    "slot": "question.card",
    "view": "card",
    "theme": {
      "mode": "light",
      "accent": "#a63b2b"
    },
    "locale": "zh-CN",
    "render_mode": "math-source",
    "assets": {
      "img_01J9Z3K4M5N6P7Q8R9S0T1V2W3": "http://127.0.0.1:8000/static/uploads/2026/10/example.png"
    }
  }
}
```

载荷约束：

- `question` 必须符合 [schemas/question.json](schemas/question.json)，是**只读快照**。插件不得修改其中任何字段，也不得把渲染态写回。
- `assets` 只包含该题 `images[]` 中声明、且宿主校验通过的资产；插件不得自行拼接文件路径。
- `render_mode` 当前固定为 `"math-source"`：插件返回包含 `$...$` / `$$...$$` 的 HTML，由宿主统一用 KaTeX 渲染。`"html"`（插件自行完成数学排版）为保留模式，`1.x` 内不启用。
- 插件必须对题目文本做 HTML 转义；`stem`、`solution`、选项内容都是不可信输入。

### 4.2 Plugin → Host：渲染成功

```json
{
  "protocol": "jzo-plugin/1",
  "id": "01J9Z3K4M5N6P7Q8R9S0T1V2W3",
  "kind": "response",
  "ok": true,
  "result": {
    "html": "<article class=\"jzp-card\"><p class=\"jzp-stem\">…</p></article>",
    "css": ".jzp-card{padding:16px;border:1px solid rgba(0,0,0,.12)}",
    "height": 220
  }
}
```

- `id` 必须与请求一致；不一致的响应直接丢弃。
- `html`：片段，不得包含 `<script>`、内联事件属性、`<style>`、`<iframe>`、`<object>`、`<form>`。
- `css`：可选，必须全部限定在 `[data-jzo-plugin="<id>"]` 作用域内；禁止 `@import`、`url(http...)`、`position:fixed`。
- `height`：可选像素估值，仅用于减少布局跳动，宿主可以忽略。
- 同一请求只接受一个响应；重复响应按协议错误处理。

### 4.3 Plugin → Host：渲染失败

```json
{
  "protocol": "jzo-plugin/1",
  "id": "01J9Z3K4M5N6P7Q8R9S0T1V2W3",
  "kind": "response",
  "ok": false,
  "error": {
    "code": "RENDER_FAILED",
    "message": "题目缺少必要字段",
    "retryable": false
  }
}
```

宿主收到失败或超时后，使用内置纯文本渲染器兜底，并记录一次插件故障。连续 3 次失败将在当前会话停用该插件。

## 5. 能力与插槽

首版（`api_version 1.x`）支持的能力：

| capability | 说明 | 必需权限 |
| --- | --- | --- |
| `question.render` | 将题目渲染为 HTML 片段 | `questions:read`、`assets:read` |
| `question.export` | 将题目导出为指定格式 | `questions:read`、`assets:read`、`export:file` |
| `question.import` | 将外部文件解析为题目候选 | `questions:write`、`assets:write` |

首版插槽：

| slot | 说明 |
| --- | --- |
| `question.card` | 题库列表中的题卡 |
| `question.detail` | 题目详情面板 |
| `question.paper` | 组卷画布中的题目 |
| `answer.panel` | 解析/答案面板 |

插件只能渲染自己 `slots` 中声明的插槽。同一插槽可以安装多个插件，但同一时刻只有一个处于激活状态；切换由用户在底座中完成。

## 6. 消息信封

所有消息共用一个信封：

```json
{
  "protocol": "jzo-plugin/1",
  "id": "01J9Z3K4M5N6P7Q8R9S0T1V2W3",
  "kind": "request",
  "method": "question.render",
  "payload": {}
}
```

- `protocol`：固定 `"jzo-plugin/1"`。
- `id`：ULID 或 UUID；请求与响应必须一致；事件可省略。
- `kind`：`request` / `response` / `event`。
- `method`：点分命名，见第 7、8 节。
- 时间单位一律毫秒；超时由发起方判定。

### 6.1 Host → Plugin 方法与事件

| 方法/事件 | 方向 | 说明 |
| --- | --- | --- |
| `plugin.activate` | 请求 | 插件激活；载荷含 `plugin_id`、`api_version`、`locale`、`theme` |
| `plugin.deactivate` | 请求 | 插件停用；插件应释放定时器、网络与缓存 |
| `question.render` | 请求 | 渲染题目，见 4.1 |
| `theme.changed` | 事件 | 主题切换 |
| `locale.changed` | 事件 | 语言切换 |
| `question.updated` | 事件 | 题目数据变化，插件应重渲染或失效缓存 |

### 6.2 Plugin → Host 方法

| 方法 | 说明 | 超时 |
| --- | --- | --- |
| `host.asset.resolve` | 将 `asset://img_xxx` 解析为宿主可访问 URL | 1000ms |
| `host.storage.get` | 读取插件命名空间下的值 | 1000ms |
| `host.storage.set` | 写入插件命名空间下的值（≤ 64KB/项） | 1000ms |
| `host.storage.remove` | 删除键 | 1000ms |
| `host.toast` | 显示一条宿主提示 | 500ms |
| `host.log` | 写入插件日志（自动脱敏） | 500ms |
| `host.navigate` | 请求宿主切换视图 | 500ms |
| `host.ai.invoke` | 调用宿主配置的模型（需 `ai:invoke`） | 60000ms |

所有插件发起的请求都必须在宿主登记；未登记的方法返回 `UNSUPPORTED_METHOD`。

## 7. 权限模型

| 权限 | 允许的操作 |
| --- | --- |
| `questions:read` | 通过 Host API 读取授权范围内的题目 |
| `questions:write` | 提交题目草稿或修改建议；实际写入必须经宿主校验与用户确认 |
| `assets:read` | 读取题目关联资产 |
| `assets:write` | 提交新资产；宿主负责转码、校验与去重 |
| `storage:plugin` | 使用插件私有键值存储 |
| `ai:invoke` | 调用宿主配置的模型 |
| `export:file` | 请求宿主生成导出文件 |

- 权限在安装时逐项展示，用户明确同意后才激活。
- 插件不得通过其他插件或全局对象绕过权限。
- 写操作必须可审计：记录插件 id、操作类型、目标题目 id、时间与结果。
- 默认无网络权限；确需联网的插件必须由用户在配置中显式填写域名，宿主以代理方式转发。

## 8. 生命周期

```text
discover → validate → install → enable → activate → active
                                      ↑        │
                                      └─ deactivate
                                                 │
                                            uninstall
```

1. **discover**：宿主扫描 `plugins/*/plugin.json`。
2. **validate**：校验清单、路径边界、许可声明、API 版本、权限白名单。
3. **install**：复制到宿主管理的插件目录，默认停用。
4. **enable**：用户确认权限后启用。
5. **activate**：加载 iframe，发送 `plugin.activate`，收到成功响应后进入 `active`。
6. **deactivate**：卸载 iframe，清理会话态；插件存储保留。
7. **uninstall**：移除代码；默认保留存储，用户可选择一并清除。

任一阶段失败都不得影响底座与其他插件；失败原因写入插件日志并展示给用户。

## 9. 安全与沙箱

- iframe 必须使用 `sandbox="allow-scripts"`，**不得**添加 `allow-same-origin`、`allow-top-navigation`、`allow-forms`、`allow-popups`。
- 插件资源从 `/plugin-assets/<id>/` 只读加载；CSP 至少包含：`default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; connect-src 'none'`。
- 宿主对返回 HTML 使用白名单净化，至少移除：`script`、`style`、`iframe`、`object`、`embed`、`form`、`input`、`link`、`meta`，以及全部 `on*` 属性与 `javascript:` URL。
- 插件返回的 CSS 由宿主校验并加作用域；不得影响底座与其他插件。
- 插件日志自动脱敏：密钥、令牌、绝对路径、邮箱不进入日志。
- 插件不得读取宿主的 LocalStorage、Cookie、IndexedDB 或剪贴板。

## 10. 版本与兼容

- `api_version` 采用 `主.次`。宿主只保证同主版本内的向后兼容。
- 主版本升级时，旧插件进入“兼容模式”并明确提示；跨主版本不保证可加载。
- 插件自身 `version` 使用语义化版本；破坏性变更升主版本。
- 题目结构由 `schemas/question.json` 单独版本化，`schema_version` 与 `api_version` 互不替代。
- 弃用：至少提前一个次版本在宿主日志与插件开发文档中标注。

## 11. 后端插件（保留，`v0.2.0` 起实现）

需要服务端能力的插件（导入器、导出器、AI 工具）可以在清单中声明：

```json
"backend": {
  "entry": "backend/plugin.py",
  "runtime": "python",
  "protocol": "jzo-backend/1"
}
```

- 后端插件由宿主以子进程方式启动，使用 stdin/stdout 上的 JSON-RPC 通信，不继承宿主环境变量。
- 宿主只暴露声明过的能力：`questions.read`、`questions.propose`、`assets.read`、`assets.write`、`ai.invoke`、`export.render`。
- 后端插件不得直接打开数据库、读取项目目录或访问网络；需要联网时走宿主代理。
- 后端插件与前端插件使用相同的插件 `id` 与权限声明。

在 `v0.2.0` 之前，清单中出现 `backend` 字段的插件将被拒绝加载，并提示“当前底座不支持后端插件”。

## 12. 最小示例

`plugin.json`：

```json
{
  "schema_version": "1.0",
  "id": "com.example.classic-card",
  "name": "经典题卡",
  "version": "0.1.0",
  "api_version": "1.0",
  "kind": "renderer",
  "description": "以传统试卷风格渲染题目卡片。",
  "license": "Apache-2.0",
  "entry": { "frontend": "dist/index.html" },
  "slots": ["question.card"],
  "capabilities": ["question.render"],
  "permissions": ["questions:read", "assets:read"]
}
```

`dist/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <link rel="stylesheet" href="./plugin.css">
</head>
<body>
  <div id="root"></div>
  <script src="./plugin.js"></script>
</body>
</html>
```

`dist/plugin.js`：

```js
const PROTOCOL = "jzo-plugin/1";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function render(question) {
  const options = (question.options || [])
    .map((option) => `<li class="jzp-option">${escapeHtml(option.key)}. ${escapeHtml(option.content)}</li>`)
    .join("");

  return [
    '<article class="jzp-card" data-jzo-plugin="com.example.classic-card">',
    `<p class="jzp-stem">${escapeHtml(question.stem)}</p>`,
    options ? `<ol class="jzp-options">${options}</ol>` : "",
    "</article>"
  ].join("");
}

window.addEventListener("message", (event) => {
  const message = event.data;
  if (!message || message.protocol !== PROTOCOL || message.kind !== "request") return;

  if (message.method === "question.render") {
    event.source.postMessage({
      protocol: PROTOCOL,
      id: message.id,
      kind: "response",
      ok: true,
      result: { html: render(message.payload.question), height: 200 }
    }, "*");
    return;
  }

  if (message.method === "plugin.activate") {
    event.source.postMessage({
      protocol: PROTOCOL,
      id: message.id,
      kind: "response",
      ok: true,
      result: { ready: true }
    }, "*");
  }
});
```

`dist/plugin.css`：

```css
.jzp-card { padding: 16px; border: 1px solid rgba(31, 28, 24, 0.14); border-radius: 12px; }
.jzp-stem { margin: 0 0 12px; line-height: 1.8; }
.jzp-options { margin: 0; padding-left: 1.2em; }
.jzp-option { margin: 4px 0; }
```

示例仅用于说明协议，不包含公式渲染、图片布局或错误处理；生产插件必须补齐。

## 13. 验收清单

插件提交评审前逐项确认：

- [ ] `plugin.json` 通过宿主校验，`id` 与目录名一致；
- [ ] 仅申请实际需要的权限；
- [ ] 所有题目文本均经过 HTML 转义；
- [ ] 返回的 HTML 不含脚本、内联事件、表单与外部资源；
- [ ] CSS 全部限定在 `[data-jzo-plugin="<id>"]` 作用域内；
- [ ] 无网络请求，或已在配置中声明域名并由宿主代理；
- [ ] 渲染结果与 `schemas/question.json` 的字段语义一致，不猜测缺失字段；
- [ ] 超时、缺图、字段缺失时有明确降级；
- [ ] 激活、停用、卸载不残留定时器、监听器与临时数据；
- [ ] 许可为 Apache-2.0 兼容，并随包提供 `LICENSE`。

---

九章算术，算子至简。

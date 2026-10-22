# 九章算子插件规范 v1.0

## 1. 设计哲学

**万物皆插件（Harness）**：所有扩展能力（AI 模型、数据源、UI 渲染）均通过统一协议接入，宿主提供沙箱隔离与生命周期管理。

### 核心原则
- **沙箱隔离**：插件运行在 iframe 或独立进程中，不得直接访问宿主内存。
- **统一协议**：所有插件通过 `postMessage` 或标准化接口通信。
- **可插拔**：插件替换无需重启服务，支持热加载。
- **最小权限**：插件仅能访问显式授权的 API 与资源。

### 1.1 白嫖条款（不可撤销）

个人版永久开源免费，本节约束**每一个插件**，是硬约束而非宣传语。

**插件禁止包含或要求以下任何一项**：

| 禁止项 | 说明 |
| --- | --- |
| 注册 / 登录 | 不得要求邮箱、手机号、账号或任何身份信息 |
| 卡密 / 激活码 / 序列号 | 不得有许可证文件、密钥兑换、离线激活码 |
| 试用期 / 到期时间 / 功能开关 | 不得因「授权状态」降级或锁功能 |
| 机器指纹 / 设备绑定 | 不得采集机器标识用于授权 |
| 联网回连校验 | 不得为授权目的发起任何网络请求（业务数据请求不在此列，且必须显式声明权限） |
| 远程禁用 / 心跳 / 遥测催费 | 不得存在云端可关闭功能的通道，不得为催费上报使用状态 |
| 水印 / 导出限制 | 不得在用户产出（试卷、讲义、导出文件）上加水印或数量限制 |

**配套约束**：

- 底座**不提供**任何「授权校验」Host API，也**禁止**将来新增。插件即便想接也无处可接。
- 违反本节的插件在评审阶段直接拒收；已落地的按 [AGENTS.md](AGENTS.md) 铁律二处理并移除。
- 能力不可用（缺密钥、断网、超时）时插件必须**显式降级**并给出可读提示，不得弹窗阻断、不得伪装成「需要激活」。底座对「静默失效」零容忍。

### 1.2 插件分发格式：纯 zip 包，无专属后缀

- **唯一格式**：一个标准 zip 包，**解压即用**。禁止 `.jzo` 或任何自定义后缀/容器格式——对齐主流生态，任何压缩软件、浏览器下载、`unzip` 都能打开它，跑路风险为零。
- zip 只是打包与传输容器，不是运行时格式。安装**永远由用户亲手发起**，共三条等价的路：① 亲手解压后把目录放进 `plugins/`；② 把本地 zip **拖进工作台 / 用文件选择器选中**，由底座校验后落地（`POST /api/plugins/install`，过一次性写令牌）；③ 在「插件索引」页点某条目的**【在线安装】**，由底座按该条目直链下载那一个 zip 后走同款校验落地（`POST /api/plugins/install-url`，见 §1.4，2026-10-24 军令追认）。底座**绝不自动安装、绝不自动拉取任何远程 zip、绝不自动更新**——每一次安装都必须由用户当场亲手发起（交一个本地文件，或点一次【在线安装】）。静默安装的唯一例外见本节末「官方例外：随包种子插件首启静默安装」。
- **底座禁止写死任何插件下载源**（防跑路）：代码与配置里不得出现任何内置的插件市场地址、插件 zip 的 CDN 域名或自动更新 URL。唯一允许内置的是**官方插件仓库索引自身的镜像序列**（`app/core/plugin_sources.py`，只含 `plugins.json` 地址，不含任何插件 zip 地址），且只在用户点【拉取清单】后按序换源。允许的出网口子只有两个，且都由用户当场点击发起：§1.3 的索引拉取（输入框默认预填**官方索引**的 gh-proxy 国内可达镜像直链，用户可当场改成任何自信任地址）与 §1.4 的在线安装（只下用户点选条目的那一个 zip）。除此之外底座不替用户访问任何远程地址。
- **安装接口的安全底线**：上传的 zip 必须先解压到临时暂存区、逐条目过安全校验、再过完 `plugin.json` 全套契约校验，才允许落地 `plugins/`。拒绝加密条目、符号链接、绝对路径、盘符路径、`..` 穿越、嵌套 zip；条目数与解压总量设上限（防 zip 炸弹）；已存在同名插件时默认拒绝（`409 exists`），只有用户显式确认 `replace` 才覆盖。落地目录名以清单 `id` 为唯一事实来源。实现见 `app/core/plugin_install.py`。
- **包结构**：zip 顶层目录名即插件 id，其内含 `plugin.json` 与 `dist/`、`templates/` 等资源：

```text
org.example.card.zip
└── org.example.card/
    ├── plugin.json
    ├── dist/{plugin.js,styles.css}
    └── templates/card.html
```

- **禁止项**：嵌套 zip、加密条目、绝对路径、`..` 路径穿越、符号链接、超出清单声明的可执行文件。底座对插件资源的解析一律拒绝越界路径（`app/core/plugins.py`）。
- **无签名 / 无摘要 / 无授权校验**：底座不验插件包的数字签名、不比对哈希白名单、不检查许可证状态。清单是否可信由用户自行判断（见 §1.3「地址是用户选的，底座只负责读」）。
- **安装**：两条等价的路，都是用户亲手发起——① 把 zip 拖进工作台（或点「安装插件 zip 包」选中），底座校验后落地；② 自己解压，把目录放进 `plugins/`。二者都无需注册、无需联网、无需重启（发现阶段见 §4）。
- **卸载**：删除该目录。底座不得在别处留存插件运行态残留；插件私有数据只能写在题目 `extensions`（反向域名前缀），随题目数据一起被用户拷走或删除。

**官方例外：随包种子插件首启静默安装（2026-10-24 追认）**

首启检测到缺失随包内置种子插件时，系统允许静默安装，**不视为违规**，也不违反本节「安装永远由用户亲手发起」的约定。该例外只对随包内置种子插件成立，且必须同时满足以下全部条件：

- **只装随包本地 zip**：安装源只能是本机随包文件（当前为 `examples/demo_plugin.zip`），不得是任何远程地址、索引条目或用户目录之外的路径；
- **零网络请求**：不打索引、不下载、不回连，全程离线；
- **删除即尊重**：每个数据目录最多自动安装一次，装完写入 `.seed-demo-bank.installed` 标记；用户此后亲手删除该插件，底座不得再装回；
- **失败不阻断**：文件缺失或安装失败一律静默放行，不影响底座在无插件状态下正常启动。

除此之外不存在任何自动安装通道：其余插件仍必须由用户当场亲手发起（见上文与 §1.3）。实现见 `app/core/seed_plugin.py`。

### 1.3 plugins.json 插件索引标准

索引是一份**纯静态 JSON**，任何人（个人 Gitee 仓库、对象存储、局域网 Nginx）都能发布；底座对它只做「拉取 + 结构校验 + 展示」，**不解压、不安装、不执行**。

- **拉取入口**：`POST /api/plugins/index`，请求体 `{"url": "...", "allow_mirrors": true}`。地址来自前端「插件索引」页的输入框（`static/plugins.html`），输入框**默认预填官方插件仓库 `MT-Blaze/jiuzhang-plugins` 的 `plugins.json` 的 gh-proxy 反代直链**（2026-10-24 v0.5.2 军令追认；国内可直连，用户可当场改成任何自信任地址），点【拉取清单】才发起请求——底座不在用户不点击时访问任何地址。
- **官方镜像换源**：请求地址等于官方索引地址时，底座按 `app/core/plugin_sources.py` 的固定序列逐个尝试（gh-proxy → ghfast → jsDelivr → fastly.jsDelivr → Raw），单源 6 秒、备用源各 5 秒；响应里带回 `source_url`、`attempts[]` 与 `fallback_used`，前端如实展示「主源失败、已切到哪一路」。主源选反代而不是 jsDelivr，是因为 jsDelivr 的 `@main` 分支缓存最长可滞后 12 小时，刚推库的新索引可能在首批用户那里仍是旧版。用户改过的自定义地址**只试一次**，不换源——不能把用户的私有地址悄悄换成第三方。全部候选都失败时，错误信息逐源列出失败原因，并提示用户可在输入框手动改填其他索引地址。
- **为什么这个只读接口要带写令牌**：它会替用户向外部发起请求（另一个口子是 §1.4 在线安装），不给令牌等于让浏览器里另一个页面的脚本白嫖本机网络身份。令牌仍是 [`AGENTS.md`](AGENTS.md) 约定的一次性轮换令牌。
- **地址守卫**（`app/core/plugin_index.validate_index_url`）：只接受 `http` / `https`；必须有主机名；**拒绝携带用户名口令**；拒绝 `file:`、`data:` 与相对路径——即不发任何请求前先拒。单次拉取上限 512 KB、条目上限 200。
- **容错口径**：单条写错只让那一条出局并给出可读原因（`rejected[]`），**不得**把整份清单判死；所有镜像都失败、非 JSON、版本不符一律返回 400 + 人话（附每一路的失败原因），不得 500。

结构（JSON Schema 见 [`schemas/plugins-index.json`](schemas/plugins-index.json)，可运行样例见 [`examples/plugins-index.example.json`](examples/plugins-index.example.json)）：

```json
{
  "index_version": "1.0",
  "name": "示例索引",
  "updated_at": "2026-10-21",
  "entries": [
    {
      "id": "org.example.card",
      "name": "经典卡片渲染器",
      "version": "1.0.0",
      "zip_url": "https://example.org/plugins/org.example.card-1.0.0.zip",
      "mirrors": ["https://example.cn/plugins/org.example.card-1.0.0.zip"],
      "kind": "renderer",
      "api_version": "jzo-plugin/1",
      "description": "一句话说明，最长 200 字",
      "homepage": "https://example.org/plugins/card"
    }
  ]
}
```

- **必填**：`index_version`（恒为 `"1.0"`）、`entries`；每条必填 `id`（反向域名，与目录名一致）、`name`、`version`（语义化）、`zip_url`（http(s) 可直达的 zip 地址）。
- **可选**：`mirrors`（≤8 条备用地址，同样必须 http(s) 且不带凭证）、`kind`、`api_version`、`description`、`homepage`。
- **索引不是授权体系**：`updated_at`、`api_version` 只用于展示与人工判断，底座**绝不**据此拒绝加载旧插件、强制升级或远程禁用——那会直接违反 §1.1。

### 1.4 在线安装（按需下载单个 zip，2026-10-24 军令追认）

用户在「插件索引」页拉取清单后，点某条目卡片上的**【在线安装】**，底座才去下载**那一个** zip 并安装。这是主库瘦身（插件本体不随包分发）的配套能力，契约如下：

- **入口**：`POST /api/plugins/install-url`，请求体 `{"url": "...", "mirrors": [...], "replace": false}`，带一次性写令牌。`url` 与 `mirrors` 只能来自用户当场点选条目的同一条目——底座不批量安装、不自动更新、不跨条目借源。用户点一次【在线安装】，底座先试 `zip_url`，失败后按该条目 `mirrors` 顺序各试一次（主源 30 秒、镜像各 20 秒），仍然只下载那一个 zip。
- **地址守卫**：与 §1.3 完全同款（`validate_index_url`）——只收 http(s)、必须有主机名、拒绝凭证、拒绝 `file:` / `data:` / 相对路径，不发请求前先拒；非法地址在联网前整体拒绝（`400 bad_url`）。
- **下载约束**（`app/core/plugin_download.py`）：单包上限 50 MB（与本机上传同口径，超限即掐断）；阻塞 IO 一律放线程池执行，**不得阻塞事件循环**——下载再慢，底座其他页面照常响应。
- **失败回滚**：下载半途失败只是丢弃内存里的字节；安装复用 §1.2 的「暂存区校验 + 原子改名落地」，任何一步失败 `plugins/` 都**零残留**。已存在同名插件默认 `409 exists`，用户显式确认 `replace` 才覆盖。响应回传实际命中的 `source_host`，前端如实展示。
- **校验不降格**：在线安装的 zip 走与本机拖装**完全相同**的全套安全与契约校验（§1.2 禁止项一条不少）；「在线」只改变 zip 的来路，不改变任何门槛。
- **白嫖条款照旧**：在线安装不是授权通道——不注册、不卡密、不签名校验；索引与 zip 地址是否可信由用户自己判断。

### 1.5 插件能力 → 对话工具（Function Calling，v0.5.1）

对话助手可以直接调用已安装插件的**只读能力**，让「拆分第一题」这类指令真正执行，而不是只回一句计划。

- **工具来源**：底座扫描 `plugins/*/plugin.json`，只把清单里显式声明的能力翻译成 OpenAI `tools`：`question.import` → `import_questions`，`question.render` → `render_question`。没有这两类能力的插件不会出现在工具表里，避免给模型假工具。工具名统一为 `plugin_<id 净化>`。
- **参数约束**：`action` 用枚举，`question_no` 限 1–200，`question_id` 必须匹配 `q_` 前缀；模型给的参数一律视为不可信，由底座重新校验后才执行。
- **执行边界**：后端**不执行插件 JS**（前端插件仍只在沙箱 iframe 里跑）。工具只读两处数据：插件自带的 `seed/questions.json`（≤2 MB、≤200 题）与当前工作区题库；不写库、不触网、不读环境变量、不碰插件私有状态。
- **路由**：模型返回 `tool_calls` 时由后端拦截执行；模型漏判或 Provider 不支持工具时，宿主只对**高置信句式**（明确题号 + 拆分/渲染/导入）做兜底路由，响应里 `route=host` 如实标注，绝不把兜底伪装成模型决策。
- **呈现**：插件结果作为自然语言气泡返回，前端在气泡上显式标注「[已调用插件]」，并展示真实执行的插件名。
- **不做**：不开放插件自定义任意函数、不执行工具返回的代码、不把工具结果写回题目结构。

---

## 2. 插件分类

本章分三类：§2.1 的 AI 模型档与 §2.2 的数据源是**底座内部扩展**（Python 模块，随底座一起发布）；只有 §2.3 的 UI 渲染插件是**用户可自己写、以 zip 安装的插件**。只想写插件的人可以直接跳到 §2.3。

### 2.1 AI 模型插件（Provider）
提供大模型对话能力。**新增一家供应商只需在 `app/core/providers/` 放一个模块，不改底座、不改前端。**

> 注意：Provider 是底座内置的 Python 模块，不是 zip 插件。想写可安装的插件，看 §2.3。

**运行时契约**（`app/core/provider.py`）：
```python
class AIProvider(ABC):
    async def chat_completion(...) -> dict[str, Any]   # 返回 {content, usage, model, mock}
    @property
    def provider_name(self) -> str
    @property
    def is_mock(self) -> bool
```

**注册契约**（`app/core/providers/`，已落地）：模块必须导出无参函数 `profiles() -> list[ProviderProfile]`，底座启动时以 `pkgutil.iter_modules` 扫描本目录（文件名以 `_` 开头的模块跳过），名称冲突直接抛错。

```python
@dataclass(frozen=True)
class ProviderProfile:      # app/core/providers/__init__.py
    name: str               # 唯一标识，如 "bailian"
    label: str              # 显示名称
    base_url: str           # 只从环境变量读
    api_key: str            # 只从环境变量读，禁止硬编码
    model: str              # 只从环境变量读，禁止硬编码模型版本
    env_prefix: str = ""    # 该档环境变量前缀（如 "JZO_BAILIAN_"），供配置面板回写 .env 时定位变量名
    is_configured -> bool   # api_key 与 base_url 均非空
```

**活跃档优先级**：环境变量 `JZO_AI_PROVIDER` > 工作区 `config.json` 的 `provider` 键 > 默认档 `openai-compatible`（默认档缺席时取首个已注册档）。切换只写工作区配置，热生效、无需重启。

**降级红线**：`is_configured` 为假时构造出的客户端必须走 Mock 分支并在响应里回 `mock: true`，**不得**抛异常、**不得**假装是真模型产出（对齐 §1.1 的「显式降级」）。对外只暴露「是否已配置 + base_url 的 netloc」，密钥永不下发（见 [STACK.md](STACK.md) §1.6）。

**配置面板契约**（工作台顶部模型徽标打开，已落地）：用户在面板里亲手填入的 Key / Base URL / 模型名，由 `POST /api/providers/config`（写令牌）写回本机 `.env` 并直写环境变量，热生效、不重启；`.env` 已 gitignore，密钥**永不入库、永不写日志、永不下发前端**（AGENTS §5 / STACK §1.6）。`POST /api/providers/test`（写令牌）对该档 Base URL 发一次只读 `GET /models` 做连通性测试，把成功 / 401 / 403 / 404 / 连不上收敛成 `{ok, status_code, host, detail}` 结构化结果——带令牌是因为这是底座替用户出网的口子（同 §1.3 口径）。`.env` 路径可被 `JZO_ENV_FILE` 覆盖（测试 / 启动器专用）。

**内置档**（`app/core/providers/builtin.py` 与 `local.py`，环境变量名即契约的一部分）：
- `openai-compatible` — `JZO_AI_BASE_URL` / `JZO_AI_API_KEY` / `JZO_AI_MODEL`（默认档）
- `bailian` — `JZO_BAILIAN_BASE_URL` / `JZO_BAILIAN_API_KEY` / `JZO_BAILIAN_MODEL`
- `siliconflow` — `JZO_SILICONFLOW_BASE_URL` / `JZO_SILICONFLOW_API_KEY` / `JZO_SILICONFLOW_MODEL`
- `ollama`（本地预留位，`local.py`）— `JZO_OLLAMA_BASE_URL` / `JZO_OLLAMA_API_KEY` / `JZO_OLLAMA_MODEL`；Ollama 自带 OpenAI 兼容接口，无需真密钥，Key 填任意占位（如 `ollama`）即可点亮。

### 2.2 数据源插件（DataSource）——预留，当前不可安装
提供外部数据接入能力（题库同步、OCR 服务、云存储等）。

> 底座当前**没有后端插件运行时**：清单里出现 `backend` 会直接拒装（见 §2.3.2）。本节是留给后续版本的目标契约，现在照着写是装不上的，别踩空。

**接口契约**：
```typescript
interface DataSource {
  id: string;           // 唯一标识，如 "org.jiuzhang.mineru"
  name: string;         // 显示名称
  version: string;      // 语义化版本
  capabilities: string[]; // ["ocr", "sync", "storage"]
  
  init(config: Record<string, string>): Promise<void>;
  query(action: string, params: any): Promise<any>;
  destroy(): Promise<void>;
}
```

**通信协议**：通过 `postMessage` 与宿主交换数据，消息格式：
```json
{
  "type": "jzo-plugin/query",
  "payload": {
    "action": "ocr_page",
    "params": { "image_url": "...", "language": "zh" }
  },
  "requestId": "uuid-v4"
}
```

### 2.3 UI 渲染插件（Renderer）：从零写一个能装上的插件

本节写给第一次写插件的人：照着做，半小时能装上一个自己的插件。可运行的最小样板在 [`examples/placeholder_plugin/`](examples/placeholder_plugin/)，整目录照抄再改名最省事。

#### 2.3.1 五步装上一个自己的插件

1. **建目录**：目录名就是插件 `id`（反向域名，如 `com.example.card`），后面必须与 `plugin.json` 里的 `id` 一字不差。
2. **写 `plugin.json`**：字段逐项见 §2.3.2，直接抄下面的例子。
3. **放 `LICENSE`**：插件根目录必须有 `LICENSE` 文件，内容是 Apache-2.0 全文（复制仓库根目录那份即可）。
4. **写入口页**：`dist/index.html` 是入口，`dist/plugin.js` 写逻辑；样式放 `dist/plugin.css`，在入口页里正常 `<link>` 即可。
5. **打包安装**：把整个插件目录压成 zip（zip 最外层是 `id/` 目录，别只压 `dist/`），然后任选一条路：拖进工作台 / 解压后把目录放进 `plugins/` / 在插件索引页点【在线安装】。装完打开 `/api/plugins`：`plugins[]` 里有你的 id 就成功了；`rejected[]` 会用中文写清哪条不合格。

目录长这样：

```text
com.example.card/
├── plugin.json
├── LICENSE
├── README.md            # 可选
└── dist/
    ├── index.html       # entry.frontend 指向这里
    ├── plugin.js
    └── plugin.css       # 可选，与入口同目录
```

入口页最小写法（和官方占位插件同款）：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>我的题卡</title>
  <link rel="stylesheet" href="./plugin.css">
</head>
<body>
  <div id="root" hidden></div>
  <script src="./plugin.js"></script>
</body>
</html>
```

#### 2.3.2 plugin.json 字段逐项说明

最小可用清单：

```json
{
  "schema_version": "1.0",
  "id": "com.example.card",
  "name": "我的题卡",
  "version": "0.1.0",
  "api_version": "1.0",
  "kind": "renderer",
  "description": "一句话说明这个插件做什么，最多 200 字。",
  "author": "你的名字",
  "license": "Apache-2.0",
  "entry": { "frontend": "dist/index.html" },
  "slots": ["question.card"],
  "capabilities": ["question.render"],
  "permissions": ["questions:read"]
}
```

| 字段 | 必填 | 规则（写错会被拒装） |
| --- | --- | --- |
| `schema_version` | 是 | 固定 `"1.0"` |
| `id` | 是 | 反向域名，全小写，至少两段（如 `com.example.card`）；**必须与目录名一致** |
| `name` | 是 | 1–64 字，给人看的名字 |
| `version` | 是 | 语义化版本，如 `1.0.0` |
| `api_version` | 是 | `"1.x"` 形式；主版本不是 1 一律拒装 |
| `kind` | 是 | `renderer` / `importer` / `exporter` / `tool` |
| `description` | 是 | 1–200 字 |
| `license` | 是 | 只接受 `"Apache-2.0"`；目录里还必须真有 `LICENSE` 文件 |
| `entry` | 是 | 对象，只认 `entry.frontend`：包内相对路径，必须位于 `dist/` 下，且文件真实存在 |
| `slots` | 是 | 非空数组，取值 `question.card` / `question.detail` / `question.paper` / `answer.panel` |
| `capabilities` | 是 | 非空数组，取值 `question.render` / `question.import` / `question.export`；`renderer` 必须含 `question.render` |
| `permissions` | 是 | 数组，可为空；取值 `questions:read` / `questions:write` / `assets:read` / `assets:write` / `storage:plugin` / `ai:invoke` / `export:file` |
| `author` | 否 | 字符串 |
| `backend` | **禁止出现** | 底座当前没有后端插件运行时，声明即拒装——不允许假能力 |

> **最常见的坑**：`protocol`、`entry_url`、`assets` 是**宿主返回**的字段，不是 `plugin.json` 的写法。清单里写它们不会被读取；照老教程写还缺 `schema_version` 和 `entry.frontend`，会被直接拒装。CSS 也不用登记，放 `dist/plugin.css` 并在入口页 `<link>` 即可。
>
> 想写 `importer`（让对话能读你自带的题库）：在插件根目录放 `seed/questions.json`，一个题目数组，最多 200 题、文件不超过 2 MB，每题符合 [`schemas/question.json`](schemas/question.json)，并在 `capabilities` 里声明 `question.import`。

#### 2.3.3 和宿主说话：消息协议

宿主把插件放在沙箱 iframe 里，双方只用 `postMessage` 交换两种消息：**宿主发请求，插件回响应**。

请求（宿主 → 插件）：

```json
{
  "protocol": "jzo-plugin/1",
  "id": "本次请求的随机 id",
  "kind": "request",
  "method": "question.render",
  "payload": { "slot": "question.card", "question": { "id": "q_...", "stem": "题干" } }
}
```

响应（插件 → 宿主）——成功：

```json
{ "protocol": "jzo-plugin/1", "id": "原样带回", "kind": "response", "ok": true, "result": { "html": "<article>...</article>", "height": 96 } }
```

失败：

```json
{ "protocol": "jzo-plugin/1", "id": "原样带回", "kind": "response", "ok": false, "error": { "code": "INVALID_PAYLOAD", "message": "缺少 stem", "retryable": false } }
```

宿主会发来的方法：

| method | 插件要做什么 |
| --- | --- |
| `plugin.activate` | 初始化，回 `{ "ready": true }`（可附 `plugin_id`、`api_version`） |
| `plugin.deactivate` | 清理定时器与监听，回 `{ "ready": false }` |
| `question.render` | 按 `payload.slot` 渲染 `payload.question`，回 `{ "html": "...", "height": 数字 }` |
| `theme.changed` / `locale.changed` / `question.updated` | 记下变化即可，回 `{ "accepted": true }`；不需要可忽略 |

完整的 `dist/plugin.js` 骨架（可以直接用）：

```javascript
(function () {
  "use strict";
  var PROTOCOL = "jzo-plugin/1";

  function reply(target, id, result) {
    target.postMessage(
      { protocol: PROTOCOL, id: id, kind: "response", ok: true, result: result },
      "*"
    );
  }

  function fail(target, id, code, message) {
    target.postMessage(
      {
        protocol: PROTOCOL, id: id, kind: "response", ok: false,
        error: { code: code, message: message, retryable: false }
      },
      "*"
    );
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  window.addEventListener("message", function (event) {
    var msg = event.data;
    if (!msg || msg.protocol !== PROTOCOL || msg.kind !== "request") return;

    if (msg.method === "plugin.activate") {
      return reply(event.source, msg.id, { ready: true, plugin_id: "com.example.card" });
    }
    if (msg.method === "plugin.deactivate") {
      return reply(event.source, msg.id, { ready: false });
    }
    if (msg.method === "question.render") {
      var payload = msg.payload || {};
      var question = payload.question || {};
      if (typeof question.stem !== "string") {
        return fail(event.source, msg.id, "INVALID_PAYLOAD", "题目缺少 stem。");
      }
      return reply(event.source, msg.id, {
        html: '<article class="my-card">' + escapeHtml(question.stem) + "</article>",
        height: 96
      });
    }
    fail(event.source, msg.id, "UNSUPPORTED_METHOD", "未实现的方法：" + String(msg.method));
  });
})();
```

四条硬规则：① 先校验 `protocol` 和 `kind`，不是请求就丢弃；② 响应必须原样带回 `id`；③ 一律回 `event.source`，不要猜父窗口；④ 不认识的方法回 `UNSUPPORTED_METHOD`，不要静默吞掉。

#### 2.3.4 安全边界（宿主兜底，但你别踩线）

- **沙箱**：iframe 带 `sandbox`、无 `allow-same-origin`，插件拿不到宿主 DOM、Cookie、localStorage 或写令牌；与宿主只靠 `postMessage` 说话。
- **只读 `dist/`**：资源只从 `/plugin-assets/<id>/dist/...` 发出，只认 `.html` / `.css` / `.js` / `.svg` / `.png` / `.webp` / `.woff2`；包外路径、`..`、符号链接一律 404。
- **不能联网**：入口页 CSP 为 `default-src 'none'; script-src 'self' <底座源>; style-src 'self' <底座源>; img-src 'self' <底座源>; connect-src 'none'; base-uri 'none'; form-action 'none'`，`fetch` / `XHR` / 远程图片全被拦；图片只能用底座托管路径或 `asset://`。
- **返回值会被净化**：插件回传的 HTML 过宿主白名单，`<script>`、内联事件属性、`javascript:` 链接、远程样式与 `@import` 都会被剥掉。别依赖它们，写了也白写。
- **碰不到密钥与文件**：插件拿不到环境变量、模型密钥、数据库和文件系统；需要数据只能走宿主授权范围内的消息。

#### 2.3.5 当前进度（先说清楚，免得装完找不到）

`v0.5.3` 的界面以对话为主：装好的插件会出现在左栏插件区与 `/api/plugins`，`question.import` / `question.render` 会进入对话工具表（说「拆分第一题」走的就是它）。题库列表页与题卡渲染宿主已在早前版本（废弃题库列表页时）一并下线，**`question.render` 暂时不会在页面上出卡片**，渲染宿主会在后续版本接回；按本节写好的插件届时无需改动。想立刻看到「插件真的被执行」，优先写 `importer`（自带 `seed/questions.json`）。

---

## 3. 多工作区（Workspace）隔离

### 3.1 架构设计
一套前端挂载多个 SQLite 库，每个工作区拥有独立的：
- 数据库文件（`data/workspaces/<id>/questions.db`）
- 上传资源目录（`data/workspaces/<id>/uploads/`）
- 配置快照（`data/workspaces/<id>/config.json`）

### 3.2 切换机制
左栏提供工作区切换下拉框，选择后：
1. 后端重载对应数据库连接
2. 前端清空本地缓存（LocalStorage 键加 workspace 前缀）
3. 刷新令牌（防止跨库写操作）

### 3.3 数据隔离验证
测试用例必须验证：
- 工作区 A 的题目不出现在工作区 B 的列表中
- 删除工作区 A 不影响工作区 B 的数据
- 上传文件路径不跨工作区泄漏

---

## 4. 插件生命周期

| 阶段 | 宿主行为 | 插件义务 |
| --- | --- | --- |
| 发现 | 每次 `GET /api/plugins` 扫描 `plugins/`、读取并校验 `plugin.json`（不合格进 `rejected[]`，不影响其他插件） | 清单合法，目录名与 `id` 一致 |
| 加载 | 在沙箱 iframe 中打开 `entry.frontend`（经 `/plugin-assets/<id>/dist/...` 分发） | 页面能独立加载，不依赖宿主全局变量 |
| 激活 | 发出 `plugin.activate` 请求 | 初始化内部状态并回响应（`ready: true`） |
| 运行 | 按用户操作发出 `question.render` 等请求 | 处理消息并回 `result`，错误回 `error` |
| 停用 | 发出 `plugin.deactivate` 请求 | 清理定时器、事件监听 |
| 卸载 | 移除 iframe；用户删除目录即完成卸载 | 不要在自己目录之外写任何文件 |

发现是「请求时扫描」，改清单或换插件目录无需重启服务；正在运行的 iframe 要刷新页面才会加载新代码。装错的插件会被隔离在 `rejected[]` 里，底座与其他插件照常工作。

---

## 5. 错误处理

### 5.1 超时控制
宿主对插件请求设置 30 秒超时，超时后：
- 记录错误日志
- 向用户显示「插件响应超时」
- 不阻断主流程（降级为默认行为）

### 5.2 异常隔离
插件抛出的未捕获异常不得导致宿主崩溃。处理请求时自己兜住异常，回一条结构化错误，而不是让消息石沉大海：

```javascript
try {
  handleRequest(msg);
} catch (err) {
  console.error("[Plugin " + PLUGIN_ID + "] 处理失败：", err);
  fail(event.source, msg.id, "INTERNAL_ERROR", "插件内部错误，请重试。");
}
```

宿主侧同样兜底：超时、连续报错或 iframe 崩溃时回落到默认展示，并记录隔离日志，不拖垮底板。

---

## 6. 版本兼容

- 宿主当前只认 `api_version` 主版本 **1**（写作 `"1.x"`），主版本不符直接拒装；次版本用于向后兼容的新增能力。
- `version` 是插件自己的语义化版本，只用于展示与人工判断；底座不据此强制升级，也不会远程禁用旧版（对齐 §1.1）。
- 协议标识固定为 `jzo-plugin/1`，出现在消息封包与 `/api/plugins` 响应的 `protocol` 字段；它**不是** `plugin.json` 的字段，别写进清单。

---

## 7. 附录：测试要求

每个插件类型必须提供：
1. **契约测试**：验证接口签名符合规范
2. **隔离测试**：验证沙箱无法逃逸
3. **性能测试**：单次操作耗时 < 500ms（P95）
4. **回归测试**：宿主更新后插件仍能正常工作

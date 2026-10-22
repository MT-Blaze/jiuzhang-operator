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
- zip 只是打包与传输容器，不是运行时格式。安装**永远由用户亲手发起**：可以亲手解压后把目录放进 `plugins/`，也可以把本地 zip **拖进工作台 / 用文件选择器选中**，由底座校验后落地（`POST /api/plugins/install`，过一次性写令牌）。底座**绝不自动安装、绝不自动拉取任何远程 zip、绝不自动更新**——它只在用户当场把一个本地文件交到手里时才动作。
- **底座禁止写死任何远程下载源**（防跑路）：代码与配置里不得出现任何内置的插件市场地址、CDN 域名或自动更新 URL。唯一例外是 §1.3 那条**由用户亲手粘贴地址**的只读拉取（拉回来也只是列清单，下载与安装仍是用户当场亲手发起）。
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

### 1.3 plugins.json 插件索引标准

索引是一份**纯静态 JSON**，任何人（个人 Gitee 仓库、对象存储、局域网 Nginx）都能发布；底座对它只做「拉取 + 结构校验 + 展示」，**不解压、不安装、不执行**。

- **拉取入口**：`POST /api/plugins/index`，请求体 `{"url": "..."}`。地址**只能来自用户**在前端「自定义源地址」输入框里的粘贴（`static/plugins.html`），底座代码里不存在任何默认地址。
- **为什么这个只读接口要带写令牌**：它是底座唯一会替用户向外部发起请求的口子，不给令牌等于让浏览器里另一个页面的脚本白嫖本机网络身份。令牌仍是 [`AGENTS.md`](AGENTS.md) 约定的一次性轮换令牌。
- **地址守卫**（`app/core/plugin_index.validate_index_url`）：只接受 `http` / `https`；必须有主机名；**拒绝携带用户名口令**；拒绝 `file:`、`data:` 与相对路径——即不发任何请求前先拒。单次拉取上限 512 KB、超时 10 秒、条目上限 200。
- **容错口径**：单条写错只让那一条出局并给出可读原因（`rejected[]`），**不得**把整份清单判死；网络失败、非 JSON、版本不符一律返回 400 + 人话，不得 500。

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

---

## 2. 插件分类

### 2.1 AI 模型插件（Provider）
提供大模型对话能力。**新增一家供应商只需在 `app/core/providers/` 放一个模块，不改底座、不改前端。**

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

**配置面板契约**（工作台左侧「配置」按钮，已落地）：用户在面板里亲手填入的 Key / Base URL / 模型名，由 `POST /api/providers/config`（写令牌）写回本机 `.env` 并直写环境变量，热生效、不重启；`.env` 已 gitignore，密钥**永不入库、永不写日志、永不下发前端**（AGENTS §5 / STACK §1.6）。`POST /api/providers/test`（写令牌）对该档 Base URL 发一次只读 `GET /models` 做连通性测试，把成功 / 401 / 403 / 404 / 连不上收敛成 `{ok, status_code, host, detail}` 结构化结果——带令牌是因为这是底座替用户出网的口子（同 §1.3 口径）。`.env` 路径可被 `JZO_ENV_FILE` 覆盖（测试 / 启动器专用）。

**内置档**（`app/core/providers/builtin.py` 与 `local.py`，环境变量名即契约的一部分）：
- `openai-compatible` — `JZO_AI_BASE_URL` / `JZO_AI_API_KEY` / `JZO_AI_MODEL`（默认档）
- `bailian` — `JZO_BAILIAN_BASE_URL` / `JZO_BAILIAN_API_KEY` / `JZO_BAILIAN_MODEL`
- `siliconflow` — `JZO_SILICONFLOW_BASE_URL` / `JZO_SILICONFLOW_API_KEY` / `JZO_SILICONFLOW_MODEL`
- `ollama`（本地预留位，`local.py`）— `JZO_OLLAMA_BASE_URL` / `JZO_OLLAMA_API_KEY` / `JZO_OLLAMA_MODEL`；Ollama 自带 OpenAI 兼容接口，无需真密钥，Key 填任意占位（如 `ollama`）即可点亮。

### 2.2 数据源插件（DataSource）
提供外部数据接入能力（题库同步、OCR 服务、云存储等）。

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

### 2.3 UI 渲染插件（Renderer）
自定义题目卡片、编辑器组件、预览模板等前端渲染逻辑。

**目录结构**：
```
plugins/org.example.card/
├── plugin.json        # 元数据
├── dist/
│   ├── plugin.js      # 入口脚本
│   └── styles.css     # 样式
└── templates/
    └── card.html      # 卡片模板
```

**plugin.json 规范**：
```json
{
  "id": "org.example.card",
  "name": "经典卡片渲染器",
  "version": "1.0.0",
  "protocol": "jzo-plugin/1",
  "entry_url": "/plugin-assets/org.example.card/dist/plugin.js",
  "assets": [
    "/plugin-assets/org.example.card/dist/styles.css"
  ],
  "permissions": ["read:questions", "render:katex"]
}
```

**安全限制**：
- CSP 策略：`default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'`
- 禁止访问 `window.parent` 以外的全局对象
- 网络请求仅限同源 `/api/` 路径

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
|------|---------|---------|
| 发现 | 扫描 `plugins/` 目录读取 `plugin.json`（zip 包由用户解压后放入，见 §1.2） | 提供合法元数据，目录名与 `id` 一致 |
| 加载 | 注入 iframe 并加载 `entry_url` | 监听 `DOMContentLoaded` 后发送 `ready` 消息 |
| 激活 | 调用 `init()` 传入配置 | 初始化内部状态 |
| 运行 | 转发用户操作为 `postMessage` | 处理消息并返回结果 |
| 停用 | 调用 `destroy()` | 清理定时器、事件监听 |
| 卸载 | 移除 iframe DOM 节点 | 无（浏览器自动回收） |

---

## 5. 错误处理

### 5.1 超时控制
宿主对插件请求设置 30 秒超时，超时后：
- 记录错误日志
- 向用户显示「插件响应超时」
- 不阻断主流程（降级为默认行为）

### 5.2 异常隔离
插件抛出的未捕获异常不得导致宿主崩溃：
```javascript
try {
  await plugin.handleAction(action);
} catch (err) {
  console.error(`[Plugin ${plugin.id}] Error:`, err);
  showFallbackUI();
}
```

---

## 6. 版本兼容

- **主版本号变更**：不兼容旧版插件，需用户手动迁移
- **次版本号变更**：向后兼容，新增功能
- **修订号变更**：仅修复 bug

宿主声明最低支持的 `protocol` 版本，插件元数据中的版本低于该值时拒绝加载。

---

## 7. 附录：测试要求

每个插件类型必须提供：
1. **契约测试**：验证接口签名符合规范
2. **隔离测试**：验证沙箱无法逃逸
3. **性能测试**：单次操作耗时 < 500ms（P95）
4. **回归测试**：宿主更新后插件仍能正常工作

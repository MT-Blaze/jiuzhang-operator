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

### 1.2 插件分发格式：纯本地 zip 包

- **唯一格式**：一个 zip 包，**解压即用**。zip 只是打包与传输容器，不是运行时格式：底座**不解析 zip**，也不内置任何远程下载源或插件市场。
- **包结构**：zip 顶层目录名即插件 id，其内含 `plugin.json` 与 `dist/`、`templates/` 等资源：

```text
org.example.card.zip
└── org.example.card/
    ├── plugin.json
    ├── dist/{plugin.js,styles.css}
    └── templates/card.html
```

- **禁止项**：嵌套 zip、加密条目、绝对路径、`..` 路径穿越、符号链接、超出清单声明的可执行文件。底座对插件资源的解析一律拒绝越界路径（`app/core/plugins.py`）。
- **安装**：把解压出的目录放进 `plugins/` 即可，无需注册、无需联网、无需重启（发现阶段见 §4）。
- **卸载**：删除该目录。底座不得在别处留存插件运行态残留；插件私有数据只能写在题目 `extensions`（反向域名前缀），随题目数据一起被用户拷走或删除。

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
    is_configured -> bool   # api_key 与 base_url 均非空
```

**活跃档优先级**：环境变量 `JZO_AI_PROVIDER` > 工作区 `config.json` 的 `provider` 键 > 默认档 `openai-compatible`（默认档缺席时取首个已注册档）。切换只写工作区配置，热生效、无需重启。

**降级红线**：`is_configured` 为假时构造出的客户端必须走 Mock 分支并在响应里回 `mock: true`，**不得**抛异常、**不得**假装是真模型产出（对齐 §1.1 的「显式降级」）。对外只暴露「是否已配置 + base_url 的 netloc」，密钥永不下发（见 [STACK.md](STACK.md) §1.6）。

**内置三档**（`app/core/providers/builtin.py`，环境变量名即契约的一部分）：
- `openai-compatible` — `JZO_AI_BASE_URL` / `JZO_AI_API_KEY` / `JZO_AI_MODEL`（默认档）
- `bailian` — `JZO_BAILIAN_BASE_URL` / `JZO_BAILIAN_API_KEY` / `JZO_BAILIAN_MODEL`
- `siliconflow` — `JZO_SILICONFLOW_BASE_URL` / `JZO_SILICONFLOW_API_KEY` / `JZO_SILICONFLOW_MODEL`

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

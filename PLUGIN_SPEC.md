# 九章算子插件规范 v1.0

## 1. 设计哲学

**万物皆插件（Harness）**：所有扩展能力（AI 模型、数据源、UI 渲染）均通过统一协议接入，宿主提供沙箱隔离与生命周期管理。

### 核心原则
- **沙箱隔离**：插件运行在 iframe 或独立进程中，不得直接访问宿主内存。
- **统一协议**：所有插件通过 `postMessage` 或标准化接口通信。
- **可插拔**：插件替换无需重启服务，支持热加载。
- **最小权限**：插件仅能访问显式授权的 API 与资源。

---

## 2. 插件分类

### 2.1 AI 模型插件（Provider）
实现 `app.core.provider.AIProvider` 抽象基类，提供大模型对话能力。

**接口契约**：
```python
class AIProvider(ABC):
    async def chat_completion(...) -> dict[str, Any]
    @property
    def provider_name(self) -> str
    @property
    def is_mock(self) -> bool
```

**注册方式**：在 `app/core/providers/` 目录下放置实现模块，系统启动时自动扫描。

**示例**：
- `OpenAICompatibleProvider`（默认）
- `BailianProvider`（阿里百炼）
- `SiliconFlowProvider`（硅基流动）

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
| 发现 | 扫描 `plugins/` 目录读取 `plugin.json` | 提供合法元数据 |
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

# 九章算子 · 技术语法规约 (STACK.md)

版本 v0.1.0 ｜ 生效 2026-10-21 ｜ 维护：军师

## 0. 总则
- 轻底座、插件化。不引重型前端框架，不引非必要运行时依赖。
- 新增运行时依赖须报主公批准。当前已批：`jsonschema`。
- 一切写操作必须过 `X-JZO-Token`，AI 不得擅自动手。
- 本文用 RFC 2119 措辞：必须 / 禁止 / 应当 / 可以。

## 1. 后端 · Python
### 1.1 版本与风格
- Python 3.11+。必须用类型注解，函数签名不得缺参类型与返回类型。
- 命名：模块/函数/变量 snake_case，类 CamelCase，常量 UPPER_SNAKE。
- 禁止裸 `except:`；必须捕获具体异常并留上下文。

### 1.2 FastAPI
- 路由应当显式声明 `response_model`，优先使用 Pydantic 模型定义响应结构。
- 依赖注入优先：令牌校验、DB 连接一律走 `Depends()`，禁止在 handler 内手写校验。
- 异步 handler 内禁止阻塞调用；sqlite 同步访问须置于 `def`（非 `async def`）端点或线程池。
- 契约模型优先，dict 返回须限期收敛，禁止新增 dict 返回端点。

### 1.3 Pydantic
- 所有请求/响应模型应当继承 `BaseModel`，字段用 `Field` 标注约束。
- 枚举字段必须用 `Literal` 或 `Enum`，禁止裸 `str` 放任。
- `question.json` 校验必须严格，禁止 `extra="allow"` 放行未知字段。

### 1.4 sqlite3
- 必须开 `PRAGMA journal_mode=WAL` 与 `PRAGMA user_version`。
- 事务应当用 `with conn:` 上下文管理；若需 IMMEDIATE/WAL 等特殊隔离级别，可手动 BEGIN 但必须在 finally 中保证 rollback。
- 删除必须墓碑软删，禁止物理 `DELETE` 导致 ID 复用。
- SQL 禁止字符串拼接用户输入，必须参数化 `?` 占位。

## 2. 前端 · 原生 JavaScript
### 2.1 模块与语法
- 应当使用 ES Module（`import/export`）；无打包链时允许 IIFE 级联加载。
- 禁止新增全局变量，共享助手须收敛至单一命名空间（如 `window.JZO`）。
- 必须 `async/await` 配合 `fetch`，禁止回调地狱。
- 请求头写操作必须带 `X-JZO-Token`，令牌一次性，用后作废。

### 2.2 交互铁律（全局强制）
- 整行可点：列表行必须有整行点击域，禁止仅文字可点。
- 热区放大：可点元素有效热区不小于 44×44px。
- 字给足：不得用缩写/图标替代关键文案。
- 就地展开：详情在当前上下文展开，禁止无谓跳页。
- 键盘可用：所有交互元素必须 `tabindex` 可达，支持 Enter/Space 触发，保留 `:focus-visible`。

### 2.3 插件通信
- 插件必须运行于沙箱 iframe。
- 宿主与插件仅通过 `postMessage` 通信，消息必须含 `type` 字段。
- 渲染入口固定 `question.render`，插件禁止直接访问宿主 DOM。

## 3. 标记与样式 · HTML/CSS
- 布局用 Grid + Flex，禁止 `float` 布局。
- 必须响应式，375px 宽度不塌、不横向溢出。
- 语义标签优先（`nav/main/aside/button`），禁止 `div` 冒充按钮。
- 色彩、间距、圆角必须走 CSS 变量，禁止散落魔法值。

## 4. 数据契约 · JSON / JSON Schema
- `question.json` 必须过 Schema 校验后方可入库。
- 插件清单必须符合 `PLUGIN_SPEC`：发现 → 沙箱 → `question.render`。
- 插件资产仅放行 `dist/`，挂载为「插件根 + dist」，禁止 `dist/dist` 拼接。
- 旧数据标 `待清洗`，用时再洗，禁止入库即清洗。

## 5. 存储 · SQL (SQLite 方言)
- 表名/列名 snake_case。
- 时间戳统一 UTC ISO8601 文本。
- 迁移靠 `PRAGMA user_version` 递增，禁止改历史迁移脚本。

## 6. 测试 · unittest + Playwright
- 后端契约测试必须覆盖：鉴权、Schema 校验、墓碑、分页。
- 前端验收必须含：375px 无溢出、控制台零错误、键盘可走。
- 测试以标准库 `unittest` 为准，不新增 pytest 依赖；测试全绿方可提交。

## 7. 构建与运行 · Shell
- 启动：`uvicorn app.main:app --reload`。
- 测试：`python -m unittest discover tests`。
- 依赖声明于 `requirements.txt`，锁定版本，禁止隐式安装。

## 8. 禁止项（红线）
1. 禁止未经令牌的写操作。
2. 禁止前端框架（React/Vue 等）入主干。
3. 禁止在主干引入 Go 等第二语言，除非主公明令。
4. 禁止物理删除题目记录。
5. 禁止把长日志贴进战报。

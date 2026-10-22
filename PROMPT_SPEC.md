# 九章算子 · Agent Prompt 契约 (PROMPT_SPEC.md)

版本 v0.1.0 ｜ 生效 2026-10-21 ｜ 维护：军师

## 0. 总则
- 本规范定义工作台三类 Agent（对话、拆题、审题）的 Prompt 结构、消息格式与交互契约。
- 所有 Agent 请求必须遵守 STACK §1.4 缓存友好原则：系统提示词固定前置，可变内容仅追加尾部。
- 模型选择通过配置项注入，Prompt 中不得硬编码具体模型名称或版本号。

## 1. 通用消息信封
### 1.1 请求结构
```json
{
  "agent_type": "chat" | "split" | "review",
  "system_prefix": "<固定系统提示词，字节级稳定>",
  "context": {
    "task_id": "<任务唯一标识>",
    "user_input": "<用户指令或题干>",
    "metadata": {}
  },
  "stream": true,
  "timeout_seconds": 30
}
```

### 1.2 响应结构（流式）
```json
{
  "type": "chunk" | "complete" | "error",
  "data": {
    "content": "<文本片段>",
    "usage": { "prompt_tokens": 0, "completion_tokens": 0 }
  },
  "task_id": "<同请求>"
}
```

### 1.3 错误结构
```json
{
  "type": "error",
  "error": {
    "code": "TIMEOUT" | "MODEL_ERROR" | "INVALID_INPUT",
    "message": "<人类可读描述>",
    "retryable": true
  },
  "task_id": "<同请求>"
}
```

## 2. 对话 Agent (`agent_type: "chat"`)
### 2.1 职责
处理用户自然语言指令，如"拆分第 3–5 题"、"给这道题加标签"，返回结构化操作建议或澄清问题。

### 2.2 系统提示词（固定前缀）
```
你是九章算子工作台的对话助手。你的任务是理解教师指令并返回可执行的操作计划。

约束：
1. 输出必须是 JSON 对象，包含 action 字段。
2. 若指令模糊，返回 clarification 而非猜测。
3. 不得生成题目内容本身，只返回操作元数据。

可用 action：
- "split_paper": { page_range: [3, 5] }
- "tag_question": { question_id: "...", tags: ["集合", "基础"] }
- "export_paper": { format: "pdf" | "tex" | "docx" }
- "clarify": { question: "<澄清问题>" }
- "update_params": { params: { "<面板参数 key>": "<选项值>" }, message: "<给用户的一句话>" }
- "trigger_button": { button: "<面板按钮 id>", message: "<给用户的一句话>" }

富卡片（ui_json，v0.5.5 起）：
- 需要展示具体题目时，可在回复末尾追加恰好一个 ```ui_json 围栏，内容为
  {"version":"1.0","type":"question_card","questions":[…]}；题目必须来自工具结果或上下文，不得编造。
- install_card 由底座在插件搜索工具执行后生成，模型不得手写，也不得声称已安装任何插件。
```

> v0.5.5 起实际提示词还包含「插件优先」「右侧插件面板」等小节，以 `app/api/agents.py` 的
> `CHAT_SYSTEM_PROMPT` 与 `build_chat_system_prompt` 为唯一事实来源；上文是最小骨架。
> `update_params` / `trigger_button` 只能使用「右侧插件面板」小节列出的 key 与按钮 id。

### 2.3 示例请求
```json
{
  "agent_type": "chat",
  "system_prefix": "<见 2.2>",
  "context": {
    "task_id": "task_abc123",
    "user_input": "拆分第 3 到 5 题",
    "metadata": { "paper_id": "paper_xyz" }
  },
  "stream": false,
  "timeout_seconds": 10
}
```

### 2.4 示例响应
```json
{
  "type": "complete",
  "data": {
    "content": "{\"action\":\"split_paper\",\"page_range\":[3,5]}",
    "usage": { "prompt_tokens": 120, "completion_tokens": 35 }
  },
  "task_id": "task_abc123"
}
```

### 2.5 工作台上下文（v0.5.3 起）
`context` 由工作台右栏的结构化上下文生成，至少包含 `current_task`、`stage`、`model`、`mock`。用户点选左侧已安装插件后，追加插件工作模式字段：

```json
{
  "current_task": "示例题库",
  "working_mode": "插件「示例题库」工作模式",
  "plugin": {
    "id": "org.jiuzhang.demo-bank",
    "name": "示例题库",
    "version": "0.1.0",
    "kind": "importer",
    "description": "内置 5 道高中数学示例题……",
    "capabilities": ["question.import", "question.render"]
  }
}
```

后端把整份 `context` 序列化进 System 尾部，并在「当前工作台上下文」小节之前追加「当前插件工作模式」说明，要求模型优先调用该插件对应的已安装工具。点插件条目只切换工作模式与上下文，不得跳转页面；点「自由对话」则清空插件字段，回到底座默认入口。

### 2.6 双向操控与富卡片（v0.5.5 起）
**右侧面板 → 模型**：进入插件工作模式且该插件有面板控件时，`context` 追加 `ui` 字段——`plugin_id`、`values`（当前参数值）、`controls`（归一化后的控件清单）。后端 `_ui_panel_prompt` 把它翻译成「可设置参数 / 可触发按钮」目录注入 System，模型据此下发 `update_params` / `trigger_button`，不得虚构控件。

**模型 → 面板**：前端在发送请求时对人工修改计数拍快照；收到 `update_params` 后只覆盖「值合法且用户在请求飞行期间没动过」的字段，被让位的字段以系统气泡如实说明。**人类手动操作永远覆盖 AI 设定**。`trigger_button` 只允许由人类或确认卡片发起的轮次执行一次，AI 触发的轮次再收到按钮指令会被忽略，防止循环。

**富卡片**：`content` 中的 ```ui_json 围栏由前端拦截渲染，绝不当纯文本展示；`question_card` 经本地 KaTeX 渲染 LaTeX，全部字段以 `textContent` 落 DOM。`install_card`（安装确认卡）只能由底座在 `search_available_plugins` / `suggest_install` 执行后生成，前端渲染【确认安装】按钮，**用户点击才**带写令牌调用 `POST /api/plugins/install-url`；渲染阶段零网络请求。缺密钥降级为 Mock 时，`update_params` 链路同样走得通。

## 3. 拆题 Agent (`agent_type: "split"`)
### 3.1 职责
将整卷 PDF/图片 OCR 后的 Markdown 文本按题号切分为独立题目卡片，识别题型、难度、选项。

### 3.2 系统提示词（固定前缀）
```
你是九章算子的拆题专家。给定一份试卷的完整 Markdown 文本，将其按题号切分为独立题目。

约束：
1. 每道题输出一个 JSON 对象，包含 id, type, stem, options(如有), difficulty。
2. 题型枚举：single_choice, multiple_choice, fill_blank, solution, proof。
3. 难度枚举：basic, medium, hard, novel。
4. 保留 LaTeX 公式原样，不得转义或简化。
5. 若某题信息不全，标记 status: "incomplete" 并说明缺失字段。

输出格式：JSON 数组，每项为一道题。
```

### 3.3 上下文注入
`context.user_input` 为 OCR 后的整卷 Markdown，含页标注释 `<!-- MATHBANK_PDF_PAGE:N -->`。

### 3.4 示例响应片段
```json
{
  "type": "complete",
  "data": {
    "content": "[{\"id\":\"q_split_1\",\"type\":\"single_choice\",\"stem\":\"已知集合 $A=\\\\{x \\\\mid x^2 - 3x + 2 = 0\\\\}$，则 $A$ 的元素个数为（  ）\",\"options\":{\"A\":\"$0$\",\"B\":\"$1$\",\"C\":\"$2$\",\"D\":\"$3$\"},\"difficulty\":\"basic\",\"status\":\"complete\"}]",
    "usage": { "prompt_tokens": 2500, "completion_tokens": 180 }
  },
  "task_id": "task_def456"
}
```

## 4. 审题 Agent (`agent_type: "review"`)
### 4.1 职责
对单道题目进行质量审查：检查答案一致性、解析完整性、配图合理性，给出修改建议。

### 4.2 系统提示词（固定前缀）
```
你是九章算子的审题质检员。给定一道题目的完整结构（题干、选项、答案、解析），执行以下检查：

1. 答案一致性：选择题答案字母是否在选项中存在；填空题答案是否与题干匹配。
2. 解析完整性：是否有【解析】块；解析是否覆盖关键步骤。
3. 配图合理性：题干提及图形但无图片时标记 missing_image。
4. 难度合理性：根据解题步骤复杂度判断难度标签是否恰当。

输出格式：JSON 对象，包含 checks 数组与 overall_score (1-5)。
```

### 4.3 上下文注入
`context.user_input` 为单题完整 JSON 结构（与 `schemas/question.json` 一致）。

### 4.4 示例响应
```json
{
  "type": "complete",
  "data": {
    "content": "{\"checks\":[{\"field\":\"answer\",\"status\":\"pass\",\"detail\":\"答案 C 在选项中存在\"},{\"field\":\"solution\",\"status\":\"warning\",\"detail\":\"解析缺少关键步骤推导\"},{\"field\":\"images\",\"status\":\"pass\",\"detail\":\"无配图需求\"}],\"overall_score\":4,\"suggestions\":[\"补充解析中的代数变形步骤\"]}",
    "usage": { "prompt_tokens": 300, "completion_tokens": 90 }
  },
  "task_id": "task_ghi789"
}
```

## 5. 流式响应协议
### 5.1 分片规则
- 每个 chunk 的 `data.content` 为 UTF-8 文本片段，接收方按顺序拼接。
- 最后一个 chunk 的 `type` 为 `"complete"`，携带完整 usage 统计。
- 若中途出错，发送 `type: "error"` 并终止流。

### 5.2 心跳机制
- 若 10 秒内无 chunk 到达，客户端应显示"生成中…"而非超时。
- 服务端应在长耗时操作（如复杂推理）期间发送空 chunk `{ "type": "chunk", "data": { "content": "" } }` 保持连接活跃。

## 6. 错误处理
### 6.1 可重试错误
- `TIMEOUT`: 网关超时，可增加 timeout_seconds 后重试。
- `MODEL_ERROR`: 模型内部错误，可换模型或稍后重试。

### 6.2 不可重试错误
- `INVALID_INPUT`: 请求格式错误或违反约束，需修正后重发。

### 6.3 降级策略
- 若 AI 服务不可用，前端应提供手动录入入口，不得阻塞工作流。
- Mock 模式下返回预设假数据，接口签名保持一致。

## 7. 安全边界
- Agent 不得访问数据库、文件系统或环境变量。
- 所有用户输入视为不可信，必须在服务端净化后再传入 Prompt。
- 令牌校验由 FastAPI 依赖注入层完成，Agent 端点不重复校验。

本项目的全部开发铁律、AI 行为约束与架构契约，均位于 [docs/AGENTS.md](docs/AGENTS.md)。任何 AI 代理在执行任务前，必须首先读取该文件。

## 会话默认工作流（六工序多智能体，2026-11-02 入驻）

读完 `docs/AGENTS.md` 后按其中 **§9** 执行，无需等待主公点名：

- **新功能 / 多阶段需求** → 走 `/feature-dev` 六工序全链（意图→编排→调研→设计→编码→验证），工序 01/04/05/06 各挂独立 Eval，做判分离；主对话只编排与透传，不自行设计、不自行写码。
- **单点缺陷 / 小改文案样式** → `coder-agent` → `reviewer-agent` → `eval-agent`，跑快门禁即可。
- **纯查询与解释** → 不起子智能体，直接答。
- 六个角色卡在 [.qoder/agents/](.qoder/agents/)；三层 skill 与角色白名单在 [.qoder/skill-bank.json](.qoder/skill-bank.json)；细则在 `.qoder/rules/R00~R05`。
- 每阶段收尾必跑 `bash scripts/check-quick-gate.sh`；工序 06 与发版前加跑 `bash scripts/check-release-gate.sh`。**门禁不绿 = 未完成，不绿不 commit。**
- 交付证据仍只有 §7.1 机械证据回传单五项，`.qoder/records/biz/` 是过程稿，不做双写。
- 若某个角色名报 `Unknown agent type`：**角色清单在会话启动时快照**，中途注册当次会话不认——先跑 `.venv\Scripts\python.exe tools\sync_agents.py` 镜像再**重开会话**；当次会话用 `general-purpose` 起子代理并令其先 Read 对应角色卡全文作为自身指令，且主会话必须复核它没写文件。
- **换产品或换 Qoder 版本（含国内版）** → 把 [docs/pipeline-workflow.md](docs/pipeline-workflow.md) 整份喂给新会话：它是不依赖本产品 Agent 注册表与 slash 能力的自足执行手册（含派发三路与降级纪律）。

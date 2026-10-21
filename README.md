> ### 📜 九章算子（Jiuzhang Operator）诞生记
> **公元 2026 年 10 月 21 日**，九章算子正式破壳。
> 这一天，我们彻底摆脱了历史代码的束缚，斩断了旧协议的枷锁。
> 作为一名深耕数学教育十余年的独立教师，我深知教学需要自由，工具需要顺手。因此，我们选择了从零开始，为全天下的独立教师，打造一个真正属于我们自己的、纯粹、自由、无限拼装的模块化数学底座。
> 九章算术，算子至简。以此为碑，铭记今日。

# 九章算子 (Jiuzhang Operator) —— 为独立教师打造的模块化数学题库底座

九章算子是一个本地优先、协议自由、可无限拼装的数学题库底座。它不预设教师应该怎样工作，而是提供一组稳定的契约：题目如何表达、插件如何接入、数据如何流动。其余能力——渲染、导入、组卷、导出、AI 辅助——都由插件完成。

- **协议**：Apache License 2.0，永久自由使用、修改与分发。
- **出身**：干净房间（Clean Room）开发，全部代码从零手写，不复用任何 AGPL 项目代码。
- **架构**：微前端 + 插件化（Harness 模式）。底座只负责鉴权、导航、数据总线与插件生命周期。
- **数据**：题目以 [JSON Schema](schemas/question.json) 为唯一交换格式，Markdown + LaTeX 表达数学内容。
- **运行**：Python 3.10+ / FastAPI；前端为原生 HTML、CSS、JavaScript，无构建链、可完全离线。

## 当前状态

`v0.2.0` 在骨架上落地了题库主干：

- SQLite 持久化（`data/jiuzhang.db`，WAL 优先、`PRAGMA user_version` 版本化、墓碑表防止 ID 复用）；
- 题目 CRUD：`GET/POST /api/questions`、`GET/PUT/DELETE /api/questions/{id}`，写入按 `schemas/question.json` 校验，`meta.revision` 提供乐观并发；
- 写入鉴权：POST/PUT/DELETE 必须携带 `X-JZO-Token`，令牌由 `JZO_LOCAL_TOKEN` 或 `data/.local_token`（首次启动生成，权限 0600）提供；
- 插件宿主最小实现：清单发现与校验、沙箱 iframe、消息封包、HTML 净化、作用域 CSS 校验、连续失败兜底；
- 首个渲染插件 `org.jiuzhang.classic-card`，题库页 `/questions` 支持搜索、筛选与分页。

尚未实现：题目编辑表单、导入/组卷/导出、后端插件与 AI 能力。

## 快速开始

```bash
cd E:\jiuzhang-operator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

打开 <http://127.0.0.1:8000>，题库页位于 <http://127.0.0.1:8000/questions>，健康检查位于 <http://127.0.0.1:8000/healthz>。

写入接口需要本地令牌。可以通过 `JZO_LOCAL_TOKEN` 显式指定，也可以读取首次启动生成在 `data/.local_token` 的令牌：

```bash
curl -X POST http://127.0.0.1:8000/api/questions \
  -H "Content-Type: application/json" \
  -H "X-JZO-Token: $(cat data/.local_token)" \
  -d '{"type":"single_choice","stem":"若 $x+1=2$，则 $x=$（  ）","difficulty":"basic","options":{"A":"$0$","B":"$1$","C":"$2$","D":"$3$"},"answer":{"value":"B"},"meta":{"author":"local"}}'
```

服务端会补齐 `id`、`schema_version` 与 `meta` 时间戳，返回 `201`。

预期响应：

```json
{
  "status": "ok",
  "service": "jiuzhang-operator",
  "version": "0.2.0",
  "time": "2026-10-21T12:00:00+00:00"
}
```

## 目录结构

```text
jiuzhang-operator/
├── app/
│   ├── main.py              # FastAPI 应用装配：路由、静态资源、只读规范入口
│   ├── api/
│   │   ├── health.py        # GET /healthz
│   │   ├── questions.py     # /api/questions CRUD
│   │   └── plugins.py       # /api/plugins 与插件资源分发
│   └── core/
│       ├── config.py        # 路径与环境变量（唯一配置入口）
│       ├── db.py            # SQLite 连接、版本化表结构、事务
│       ├── questions.py     # Schema 校验与题目仓库
│       ├── plugins.py       # 插件发现、清单校验与静态资源解析
│       └── security.py      # 本地写入令牌
├── static/
│   ├── index.html           # 底座首页（无框架、无 CDN）
│   ├── questions.html       # 题库列表页
│   ├── css/{app,questions}.css
│   └── js/{app,questions}.js
├── schemas/
│   └── question.json        # 题目交换格式（唯一事实来源）
├── plugins/
│   ├── README.md            # 插件目录约定
│   └── org.jiuzhang.classic-card/  # 首个题目卡片渲染插件
├── tests/
│   └── test_questions_api.py # 接口契约与安全边界回归
├── AGENTS.md                # 开发与 AI 代理铁律
├── PLUGIN_SPEC.md           # 插件接入规范
├── LICENSE                  # Apache License 2.0 全文
├── README.md
└── requirements.txt
```

## 只读入口

| 路径 | 内容 |
| --- | --- |
| `/healthz` | 健康检查 JSON |
| `/questions` | 题库列表页（插件渲染 + 分页） |
| `/api/questions` | 题目列表（分页、搜索、筛选） |
| `/api/plugins` | 已加载插件清单 |
| `/schemas/question.json` | 题目 JSON Schema |
| `/spec/plugin` | 插件接入规范（Markdown） |
| `/api/openapi.json` | 机器可读的 OpenAPI 接口描述 |

## 设计原则

1. **干净房间**：不复制旧项目代码、样式、文档或数据；只参考公开标准与通用知识。
2. **底座要薄**：底座只承担鉴权、导航、数据总线、插件生命周期与统一安全边界。
3. **契约先行**：题目结构与插件协议先于实现落盘，插件与底座各自独立演进。
4. **本地优先**：数据留在本机，默认不出网；需要联网的能力必须显式配置。
5. **安全默认**：不可信内容一律净化，插件渲染一律在沙箱中完成。
6. **数学优先**：所有文本字段原生支持 Markdown + LaTeX，公式与中文混排是常态而非补丁。

## 许可

本项目以 [Apache License 2.0](LICENSE) 发布。你可以自由使用、修改、分发，包括商业用途；请保留许可证与版权声明。

---

九章算术，算子至简。以此为碑，铭记今日。

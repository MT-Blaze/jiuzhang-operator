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

## 白嫖宣言（个人版永久开源免费）

九章算子个人版**永久免费、永久开源**，并且把这份免费写成不可撤销的承诺：

- **免注册**：不要邮箱、不要手机号、不要账号。下载、启动即可用全部功能。
- **免破解**：不存在需要破解的东西——源码全公开（Apache License 2.0），不分发加密二进制，不埋功能开关。
- **免卡密**：没有激活码、序列号、许可证文件、试用天数、到期时间，也没有机器指纹绑定。代码里**根本没有这一类校验分支**，底座也不给插件提供「授权校验」接口。
- **绝无云端锁喉**：题库、组卷、渲染、导入导出 100% 在本机跑，断网可用。AI 能力只连你自己在 `.env` 里填写的模型网关；不填密钥或关掉网络，AI 那一步显式降级为不可用，底座与全部插件照常工作——**绝不弹窗催费、绝不偷偷上传题目数据、绝不让云端一句话就把功能关掉**。
- **不锁数据**：题目是本机 `data/` 目录里的明文 SQLite + [JSON Schema](schemas/question.json)，随时整目录拷走、任何工具都能读；卸载不销毁、不加密、不留水印。
- **插件同样白嫖**：插件就是**标准 zip 包，解压即用**（没有 `.jzo` 之类专属后缀，也不验签名、不验摘要），规范禁止任何注册、卡密与联网回连激活，详见 [PLUGIN_SPEC.md](PLUGIN_SPEC.md) §1.1、§1.2。
- **插件清单不绑任何厂商**：底座**没有内置插件市场，也绝不写死远程地址**（防跑路）。想做「国内可达的橱窗」，自己发一份 `plugins.json` 静态清单（§1.3），在 `/plugins` 页把它的 http(s) 地址粘进输入框即可拉取列表；底座只读这一份 JSON，下载与解压永远由你亲手做。

## 开箱即用：配一次密钥就能用 AI

底座自带 OpenAI 兼容通道，配好密钥即出真实模型结果；不配则自动降级为 Mock，界面照样能跑。

```bash
# 仓库根目录建 .env（已被 .gitignore 拦住，绝不会进版本库）
JZO_AI_BASE_URL=https://你的网关地址/compatible-mode/v1
JZO_AI_API_KEY=你的密钥
JZO_AI_MODEL=模型名
JZO_LOCAL_TOKEN=自定义一个本地写令牌        # 可选；不填则首启生成 data/.local_token
```

重启服务后，工作台 `/workspace` 左栏的「模型 Provider」状态行会写明当前用的是谁：
绿色「真实模型 · <模型名> · <接口主机>」即已接通；红色「Mock 降级」表示没有密钥。
多厂商切换、注册表扫描与密钥边界见 [PLUGIN_SPEC.md](PLUGIN_SPEC.md) §2.1 与 [STACK.md](STACK.md) §1.6。

## 当前状态

`v0.2.0` 在骨架上落地了题库主干：

- SQLite 持久化（`data/jiuzhang.db`，WAL 优先、`PRAGMA user_version` 版本化、墓碑表防止 ID 复用）；
- 题目 CRUD：`GET/POST /api/questions`、`GET/PUT/DELETE /api/questions/{id}`，写入按 `schemas/question.json` 校验，`meta.revision` 提供乐观并发；
- 写入鉴权：POST/PUT/DELETE 必须携带 `X-JZO-Token`，令牌由 `JZO_LOCAL_TOKEN` 或 `data/.local_token`（首次启动生成，权限 0600）提供；文件令牌为**一次性**——校验通过即轮换，旧令牌第二次使用必被拒（设了 `JZO_LOCAL_TOKEN` 时走环境变量档，不轮换）；
- 插件宿主最小实现：清单发现与校验、沙箱 iframe、消息封包、HTML 净化、作用域 CSS 校验、连续失败兜底；`plugins.json` 索引只按**用户亲手填入**的地址拉取（`/plugins` + `POST /api/plugins/index`），底座零内置源、不解压不安装；
- 首个渲染插件 `org.jiuzhang.classic-card`；种子题库插件 `org.jiuzhang.demo-bank`（首启自动静默安装，内置 5 道示例题）；
- AI 能力：`app/core/providers/` 扫描式 Provider 注册表（密钥只走环境变量）、`/api/agent/chat|split|review` 三个智能体、工作台 `/workspace` 「导入原卷 → 发指令 → 出真卡片 → 确认入库」闭环，以及 `/api/providers` 多厂商切换。

`v0.3.0` 在其上再加两项「极致体验」：

- 插件一键装：把本地 `.zip` 拖到工作台页面任意位置（或点「安装插件 zip 包」选文件），`POST /api/plugins/install`（过一次性写令牌）先解压到临时暂存区、逐条目安检（拒加密 / 符号链接 / 绝对路径 / 盘符 / `..` 穿越 / 嵌套 zip，条目≤2000、解压≤256MB、包体≤50MB 防炸弹）、过完 `plugin.json` 全套契约才落地 `plugins/`；同名已装默认拒绝、确认后才覆盖。**安装永远由用户亲手发起，底座不自动拉远程源、不自动更新**；
- 多模型配置面板：工作台左栏「模型 Provider」区加「配置」按钮，填 Base URL / API Key / 模型名并测试连通性，保存即热生效（不重启）；密钥只写本机 `.env`，永不回显、永不入库；新增 `ollama` 本地档，为本地模型预留座位。

`v0.3.1` 是内测首日的抢修版，只动两处体验硬伤：

- 版本号单一事实来源：页面右上角徽章与页脚一律由 `static/js/version.js` 读 `/healthz` 盖章（`app/__init__.py` 的 `__version__` 为唯一来源），HTML 里写死的版本号只是无 JS 时的兜底，并由 `tests/test_version_consistency.py` 锁死一致；`start.bat` 启动前自检端口，若 8000 已被陈留实例占用则明确提示，不再让人对着旧进程的旧版本号发愣；
- `start.bat` pip 自愈：装依赖前先验 `.venv` 内 pip 是否可用，缺失则自动 `ensurepip` 修复，修不好再重建 venv，最后才报错退出。

`v0.4.0` 把「双击即用」再往前推一步，纯浏览器极简路线：

- 启动器等 `/healthz` 真正应答后再拉起系统默认浏览器，不再靠固定秒数猜启动时间；
- 新增极简 PWA 清单、图标与根作用域 Service Worker：Chrome / Edge 可把本站「安装为应用」，以独立窗口运行；SW 只做网络透传、不缓存，避免装完看到旧页面；
- `static/index.html` 头部加浏览器探针，IE 或缺少 ES Module / CSS 变量支持的老内核直接显示「请使用现代浏览器」，不白屏。

尚未实现：题目编辑表单、导入/组卷/导出、后端插件（清单里的 `backend` 仍按规范拒绝加载）。

## 快速开始

```bash
cd E:\jiuzhang-operator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

打开 <http://127.0.0.1:8000> 直达智能工作台，底座介绍页位于 <http://127.0.0.1:8000/about>，健康检查位于 <http://127.0.0.1:8000/healthz>。

写入接口需要本地令牌。可以通过 `JZO_LOCAL_TOKEN` 显式指定，也可以读取首次启动生成在 `data/.local_token` 的令牌：

```bash
curl -X POST http://127.0.0.1:8000/api/questions \
  -H "Content-Type: application/json" \
  -H "X-JZO-Token: $(cat data/.local_token)" \
  -d '{"type":"single_choice","stem":"若 $x+1=2$，则 $x=$（  ）","difficulty":"basic","options":[{"key":"A","content":"$0$"},{"key":"B","content":"$1$"},{"key":"C","content":"$2$"},{"key":"D","content":"$3$"}],"answer":{"kind":"choice","choice_keys":["B"]},"meta":{"author":"local"}}'
```

服务端会补齐 `id`、`schema_version` 与 `meta` 时间戳，返回 `201`。`options` 是**数组**（每项 `{key, content}`），答案形态由 `answer.kind` 声明——一切以 [schemas/question.json](schemas/question.json) 为准，写法不符会被写入侧拒绝并给出可读原因。

预期响应：

```json
{
  "status": "ok",
  "service": "jiuzhang-operator",
  "version": "0.4.2",
  "time": "2026-10-21T12:00:00+00:00"
}
```

## 目录结构

```text
jiuzhang-operator/
├── app/
│   ├── __init__.py          # 版本号 + 仓库根 .env 装载器（STACK §1.6）
│   ├── main.py              # FastAPI 应用装配：路由、静态资源、只读规范入口
│   ├── api/
│   │   ├── health.py        # GET /healthz
│   │   ├── questions.py     # /api/questions CRUD
│   │   ├── plugins.py       # /api/plugins 与插件资源分发，含 POST /api/plugins/index
│   │   ├── providers.py     # /api/providers 注册表与活跃档切换
│   │   ├── agents.py        # /api/agent/chat|split|review
│   │   └── workspaces.py    # 多工作区列表/新建/切换
│   └── core/
│       ├── config.py        # 路径与环境变量（唯一配置入口）
│       ├── db.py            # SQLite 连接、版本化表结构、事务
│       ├── questions.py     # Schema 校验与题目仓库
│       ├── plugins.py       # 插件发现、清单校验与静态资源解析
│       ├── seed_plugin.py   # 首启静默安装种子题库插件（只装本地 zip，不触网）
│       ├── plugin_index.py  # plugins.json 索引：地址守卫 + 只读拉取（底座无内置源）
│       ├── provider.py      # AIProvider 抽象基类
│       ├── providers/       # Provider 注册表（扫描本目录模块，密钥只走环境变量）
│       ├── ai_client.py     # OpenAI 兼容客户端（标准库 urllib，无额外依赖）
│       └── security.py      # 本地写入令牌
├── static/
│   ├── index.html           # 底座介绍页（挂 /about，无框架、无 CDN）
│   ├── workspace.html       # 智能工作台（三栏：任务 / 对话流 / 上下文），根路径直达
│   ├── plugins.html         # 插件索引页（自定义源地址输入框）
│   ├── css/{app,questions,workspace,plugins}.css
│   └── js/{app,workspace,plugins,pwa,version}.js
├── schemas/
│   ├── question.json        # 题目交换格式（唯一事实来源）
│   └── plugins-index.json   # plugins.json 索引格式
├── examples/
│   ├── plugins-index.example.json  # 示例清单（地址全部不可用，只示范结构）
│   ├── demo_plugin/                # 种子题库插件源码（5 道示例题）
│   ├── demo_plugin.zip             # 构建产物：首启静默安装的种子包
│   └── build_demo_plugin.py        # 重新校验并打包 demo_plugin.zip
├── plugins/
│   ├── README.md            # 插件目录约定
│   └── org.jiuzhang.classic-card/  # 首个题目卡片渲染插件
├── tests/
│   ├── test_questions_api.py       # 接口契约与安全边界回归
│   ├── test_plugin_index.py        # 索引解析、地址守卫与零写死源
│   ├── test_seed_plugin.py         # 默认路由与种子插件安装契约
│   └── test_providers_api.py       # Provider 注册表与切换契约
├── AGENTS.md                # 开发与 AI 代理铁律
├── PLUGIN_SPEC.md           # 插件接入规范（含 §1.1 白嫖条款）
├── STACK.md                 # 技术语法规约（含 §1.6 密钥与环境变量装载）
├── LICENSE                  # Apache License 2.0 全文
├── README.md
└── requirements.txt
```

## 只读入口

| 路径 | 内容 |
| --- | --- |
| `/healthz` | 健康检查 JSON |
| `/` | 智能工作台（根路径直达，对话驱动） |
| `/about` | 底座介绍页（原首页，设计原则与只读契约入口导航） |
| `/workspace` | 智能工作台（导入原卷 → 发指令 → 出真卡片） |
| `/plugins` | 插件索引页（自填 `plugins.json` 地址拉取清单，只读、不安装） |
| `/api/questions` | 题目列表（分页、搜索、筛选） |
| `/api/plugins` | 已加载插件清单 |
| `POST /api/plugins/index` | 按**用户填入**的地址拉取一份插件索引（只读 GET，需一次性写令牌；底座无默认地址） |
| `/plugins/index-example` | 仓库自带的示例索引，给「试一试」按钮一个同源可跑通的地址 |
| `/api/providers` | Provider 注册表（只暴露是否已配置与接口主机名） |
| `/schemas/question.json` | 题目 JSON Schema |
| `/schemas/plugins-index.json` | 插件索引 JSON Schema |
| `/spec/plugin` | 插件接入规范（Markdown） |
| `/api/openapi.json` | 机器可读的 OpenAPI 接口描述 |

## 设计原则

1. **干净房间**：不复制旧项目代码、样式、文档或数据；只参考公开标准与通用知识。
2. **底座要薄**：底座只承担鉴权、导航、数据总线、插件生命周期与统一安全边界。
3. **契约先行**：题目结构与插件协议先于实现落盘，插件与底座各自独立演进。
4. **本地优先**：数据留在本机，默认不出网；需要联网的能力必须显式配置。
5. **安全默认**：不可信内容一律净化，插件渲染一律在沙箱中完成。
6. **数学优先**：所有文本字段原生支持 Markdown + LaTeX，公式与中文混排是常态而非补丁。
7. **白嫖不可撤销**：免费、免注册、免卡密、无云端锁喉是产品底线，已写进 [PLUGIN_SPEC.md](PLUGIN_SPEC.md) §1.1 成为对插件作者的硬约束，而不是 README 上的一句口号。

## 许可

本项目以 [Apache License 2.0](LICENSE) 发布。你可以自由使用、修改、分发，包括商业用途；请保留许可证与版权声明。

个人版的免费与开源承诺见上文「白嫖宣言」：本仓库的代码与全部内置插件不含任何授权校验、激活回连或功能开关。

---

九章算术，算子至简。以此为碑，铭记今日。

# 九章算子 (Jiuzhang Operator) —— 为独立教师打造的模块化数学题库底座

九章算子是一个**纯本地、免注册、插件化**的数学题库底座。下载解压就能用，断网也能用：
不要邮箱、不要手机号、不要激活码，代码里根本没有授权校验那一类分支。
底座只负责四件事——鉴权、导航、数据总线、插件生命周期；题目渲染、录题、导入、组卷、讲义、
导出、AI 辅助一律由插件提供，插件坏了底座照样能用。

- **协议**：Apache License 2.0，永久自由使用、修改与分发。
- **出身**：干净房间（Clean Room）开发，全部代码从零手写，不复用任何历史项目代码。
- **数据**：题目以 [JSON Schema](schemas/question.json) 为唯一交换格式，数学内容用 Markdown + LaTeX；
  题库是本机 `data/` 里的明文 SQLite，随时整目录拷走，卸载不销毁、不加密、不留水印。
- **运行**：Python 3.10+ / FastAPI；前端是原生 HTML、CSS、JavaScript，无构建链、无 Node 依赖、资源全本地。
- **AI**：只连你自己填在 `.env` 里的模型网关；不填密钥就显式降级为 Mock，其余功能照常。
  **绝不后台静默出网**——任何一次联网都必须由界面上的当场点击发起（[PLUGIN_SPEC.md](docs/PLUGIN_SPEC.md) §1.1–§1.5）。

## 快速开始

**方式一：双击启动（推荐给不使用命令行的老师）**

1. 解压发布包到任意目录（路径含中文与空格都没关系，但别放进只读盘）。
2. 想要 AI 能力就在**仓库根目录**建一个 `.env`（该文件已被 `.gitignore` 拦住，绝不会进版本库）：

   ```ini
   JZO_AI_BASE_URL=https://你的网关地址/compatible-mode/v1
   JZO_AI_API_KEY=你的密钥
   JZO_AI_MODEL=模型名
   JZO_LOCAL_TOKEN=自定义一个本地写令牌        # 可选；不填则首启生成 data/.local_token
   ```

   不建 `.env` 也能用，只是 AI 那一步降级为 Mock。密钥永不入库、永不写日志、永不进插件上下文。
3. 双击 `start.bat`。脚本会自检端口（8000 被陈留实例占用会明确提示并另选端口）、
   自愈 pip（缺 pip 先 `ensurepip`，修不好再重建 `.venv`）、装依赖，等 `/healthz` 真正应答后才拉起默认浏览器。
4. 浏览器落在智能工作台 `http://127.0.0.1:8000`；设置与控制页在 `/settings`（左栏底部齿轮）。

工作台顶部的模型徽标会写明当前用的是谁：绿色「真实模型 · <模型名> · <接口主机>」即已接通，
红色「Mock 降级」表示没有密钥。多厂商切换与密钥边界见 [PLUGIN_SPEC.md](docs/PLUGIN_SPEC.md) §2.1、[STACK.md](docs/STACK.md) §1.6。

**方式二：命令行启动**

```bash
cd E:\jiuzhang-operator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

写入类接口需要本地令牌（`JZO_LOCAL_TOKEN`，或首启生成的 `data/.local_token`，权限 0600）：

```bash
curl -X GET http://127.0.0.1:8000/healthz
```

```json
{ "status": "ok", "service": "jiuzhang-operator", "version": "1.0.0", "time": "2026-10-21T12:00:00+00:00" }
```

题目字段（`options` 是 `{key, content}` 数组、答案形态由 `answer.kind` 声明）一律以
[schemas/question.json](schemas/question.json) 为准，写法不符会被写入侧拒绝并给出可读原因。

## 只读入口

| 路径 | 内容 |
| --- | --- |
| `/` 或 `/workspace` | 智能工作台（四区：入口与插件 / 画布 Tabs / 上下文 / 输出） |
| `/settings` | 设置与控制（插件管理、更新、在线索引、手动装 zip、启动行为） |
| `/plugins` | 插件索引页（默认预填官方镜像，可当场改地址；拉清单只读，装包逐条点击） |
| `/about` | 底座介绍页 |
| `/healthz` | 健康检查 JSON（含 `boot_id`，是「新进程真起来了」的唯一凭据） |
| `/api/plugins` | 已加载插件清单（`rejected[]` 列出未通过校验的插件与中文原因） |
| `/schemas/question.json`、`/spec/plugin`、`/api/openapi.json` | 题目 Schema、插件规范、机器可读接口描述 |

## 自己写一个插件

插件就是**一个标准 zip 包**：不需要注册、不需要编译、不用改底座，解压即用。最短路径三步：

1. 复制 [`examples/template-plugin/`](examples/template-plugin/)（成品包
   [`template-plugin.zip`](examples/template-plugin.zip)），改三处——清单里的 `id`/`name`（**目录名与 `id` 一字不差**）、
   `dist/plugin.js` 顶部的 `PLUGIN_ID`、入口页界面；
2. 照最小清单填 `plugin.json`（字段表见 [PLUGIN_SPEC.md §2.3.2](docs/PLUGIN_SPEC.md)）：`entry.frontend` 必须在 `dist/` 下，
   根目录带 Apache-2.0 的 `LICENSE`，禁止 `backend` 字段；要接管中央画布就加 `"slots": ["stage.center"]` 与 `stage` / `bus` 声明（§2.4）；
3. 把 zip 拖进工作台任意位置，或在「设置与控制 → 插件」里装，然后打开 `/api/plugins` 看自己的 id 有没有出现。

消息封包、`bank.*` 白名单、事件总线、能力路由 `command.list` / `command.execute` 与安全边界，
契约唯一事实来源是 [PLUGIN_SPEC.md](docs/PLUGIN_SPEC.md)；接口速查见 [API_REFERENCE.md](docs/API_REFERENCE.md)。
**让 AI 代写插件**的整段提示词、模板用法与装后三查，见 [PLUGIN_SPEC.md §8「如何用 AI 写插件」](docs/PLUGIN_SPEC.md)。

## 开发这个仓库

- 铁律与验证口径：[AGENTS.md](docs/AGENTS.md)（干净房间、插件化、安全、可访问性、提交与回传单）；
  技术语法规约：[STACK.md](docs/STACK.md)。
- 测试**不引入 pytest**，必须用 `.venv` 里的解释器逐模块跑：
  `.venv\Scripts\python.exe -m unittest tests.test_editor_contract`。
- 目录骨架：`app/`（底座路由与核心）、`static/`（宿主壳）、`schemas/`（跨边界契约）、
  `plugins/`（每个插件一个目录）、`examples/`（模板与示例）、`tests/`（契约测试）、`tools/`（打包与真机取证脚本）。

## 许可与社区

本项目以 [Apache License 2.0](LICENSE) 发布，可自由使用、修改、分发（含商业用途），请保留许可证与版权声明。
个人版的免费与开源承诺已写成对插件作者的硬约束（PLUGIN_SPEC §1.1），不是 README 上的一句口号。

欢迎提需求、报 bug、换题库、做插件：QQ 群 `1105273716`，扫码 <https://qm.qq.com/q/WMqM5l8YQc>。

![九章算子官方交流群](static/assets/qq-group.png)

## 文档导航

根目录只留项目门面，核心文档统一收在 [`docs/`](docs/)：

| 文件 | 作用 |
| --- | --- |
| [docs/AGENTS.md](docs/AGENTS.md) | 开发与 AI 代理铁律：干净房间、插件化架构、数据契约、安全、验证与提交 |
| [docs/PLUGIN_SPEC.md](docs/PLUGIN_SPEC.md) | 插件契约唯一事实来源（含 §8「如何用 AI 写插件」） |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | 插件接口速查与宿主 Agent Prompt 契约 |
| [docs/PROJECT_MEMORY.md](docs/PROJECT_MEMORY.md) | 架构决策记录（ADR）与欠账账本 |
| [docs/STACK.md](docs/STACK.md) | 技术栈、语法规约与红线条款 |
| [docs/内测安装与使用指南.md](docs/内测安装与使用指南.md) | 面向零技术基础老师的完整安装与使用步骤 |

---

九章算术，算子至简。以此为碑，铭记今日。

详细更新日志见 Releases 页面；架构决策与开发进度见 docs/ 目录。

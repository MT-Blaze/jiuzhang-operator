# 九章算子 · 第三方插件协作指南

> 正文提取自本仓库 `README.md`《如何用 AI 开发九章算子插件？》一节（2026-10-23 版）。
> 契约的唯一事实来源始终是 `PLUGIN_SPEC.md`；本指南只是把最容易踩的坑摆在最前面。

## 0．这个礼包里有什么

| 文件 | 作用 |
| --- | --- |
| `README_协作指南.md` | 本文件：给 AI 的提示词 + 模板用法 + 协作须知 |
| `template-plugin/` | 第三方插件开发极简模板源码（清单 + 入口页 + 逻辑脚本 + LICENSE） |
| `template-plugin.zip` | 同一个模板的打包产物，解压即用 |
| `PLUGIN_SPEC.md` | 插件接入规范全文（白嫖条款、清单字段、消息协议、Host API 白名单） |
| `PROJECT_MEMORY.md` | 架构决策记录（ADR）与欠账账本，动手前先扫一眼相关 ADR |

## 1．给 AI 的提示词（整段复制，连着你的需求一起发给大模型）

未来的第三方老师不手写代码，而是让 AI 代写。把下面整段发给任何大模型
（DeepSeek / 千问 / GPT / Claude 均可），它生成的代码就不会踩架构红线：

```text
你要为「九章算子」本地数学题库底座开发一个浏览器插件。九章算子是纯本地、离线运行的
FastAPI + 原生前端底座，插件以 zip 包安装，运行在沙箱 iframe（sandbox="allow-scripts"，
不透明源）里。请严格遵守以下【AI 开发铁律】，违反任何一条的代码一律视为错误：

1. 严禁点对点耦合：插件之间不直接调用、不共享全局状态；所有插件间通信必须且只能经过
   底座中转（事件总线）。
2. 数据读写：严禁插件直接访问底座数据库、文件系统、环境变量或密钥；题库数据必须调用
   标准宿主 API——向宿主 postMessage 一条 kind:"request" 消息，方法名只能取自白名单
   （bank.get / bank.review / bank.topics / bank.create / bank.update / bank.delete /
   bank.list / bank.stats / bank.random / basket.list / basket.add / basket.remove /
   basket.clear），宿主查完回同 id 的 response。三类通道别混：bank.get / bank.review /
   bank.topics / bank.create 读的是「公共真题库」（当前活跃 provider，底座自带数据）；
   bank.list / bank.stats / bank.random 按插件自己的 plugin.id 读「插件自带的库」，要用就得随包
   放 bank/schema.sql；basket.* 是工作区题篮，与具体哪个库无关。请求 id 必须匹配 ^[A-Za-z0-9_-]{1,80}$。
3. 状态同步：改状态必须通过事件总线广播（向宿主发 kind:"notification" 消息，事件名必须在
   plugin.json 的 bus.publish 白名单里，如 region.dock）；严禁直接调用其他插件的函数，
   严禁伪造 ui.params.* 或 layout.* 事件。
4. UI 隔离：所有视图封闭在自己专属的 iframe 沙箱内；严禁越权操作父窗口 DOM——与宿主唯一
   的通道是 window.parent.postMessage，拿不到宿主页面、Cookie 和 localStorage
   （草稿只能经宿主 RPC 代持）。
5. 环境依赖：严禁引入 React / Vue / jQuery / Tailwind 等重型前端框架，严禁通过 CDN 加载
   任何远程资源（入口页 CSP 的 connect-src 'none' 会全部拦截）；必须使用原生 HTML + CSS +
   JavaScript（ES2017 以内，禁止正则后行断言），公式文本按 Markdown + LaTeX 约定处理。

插件包结构（zip 顶层目录名 = 插件 id）：
  <id>/plugin.json      # schema_version:"1.0"、id(反向域名)、name、version(语义化)、
                        # api_version:"1.0"、kind(renderer/importer/exporter/tool)、
                        # description、license:"Apache-2.0"、entry.frontend:"dist/index.html"、
                        # slots、capabilities、permissions；可选 stage / bus / ui /
                        # show_in_sidebar / min_host_version / engine.host_version。
                        # 禁止出现 backend 字段。根目录必须有 LICENSE（Apache-2.0 全文）。
  <id>/dist/index.html  # 入口页
  <id>/dist/plugin.js   # 逻辑脚本
消息封包（三个字段缺一不可）：
  请求   {protocol:"jzo-plugin/1", id:"唯一请求id", kind:"request", method:"…", payload:{…}}
  响应   {protocol:"jzo-plugin/1", id:"原样带回", kind:"response", ok:true, result:{…}}
  通知   {protocol:"jzo-plugin/1", kind:"notification", event:"…", payload:{…}}
请求 id 必须匹配 ^[A-Za-z0-9_-]{1,80}$（不要带点号，也别拿插件 id 当 id 前缀——宿主对不上这个
形状的请求会当场拒发并回 ok:false + code:"BAD_REQUEST_ID"，同时在底栏输出日志区记账），
并给每个请求设超时兜底，宿主不回包时给出可读提示。
必须处理宿主的 plugin.activate（30 秒内回 ready:true）与 plugin.deactivate；
通知一律幂等（宿主会重发）；未实现的方法回 UNSUPPORTED_METHOD，不许静默吞掉。
插件不得要求注册/登录/卡密/联网回连/远程禁用（白嫖条款），能力不可用时显式降级并给
可读提示。

现在请以这份结构为基线，实现以下需求：<在这里写你的插件功能>
```

## 2．模板改三处就能变成你的插件

1. `plugin.json` 的 `id` / `name` / `version`——**解压出来的目录名必须与 `id` 一字不差**，否则拒装。
2. `dist/plugin.js` 顶部的 `var PLUGIN_ID = "org.example.template";` 改成你的 `id`。
3. `dist/index.html` 的标题与界面（样式请另存 `dist/plugin.css` 外挂，入口页内联 `<style>` 会被 CSP 拦）。

模板里已经写好两条最常用链路的注释示例：`callHost()`（宿主 API 请求-响应）与
`notifyHost()`（经 `bus.publish` 白名单向底栏广播）。改完把目录丢进底座的 `plugins/`，
或在「设置与控制 → 插件」里拖那个 zip 安装。

## 3．装上去先跑三查

1. 打开 `http://127.0.0.1:8000/api/plugins`，看 `rejected[]` 里有没有你的插件与中文拒收原因。
2. 全文搜索 `fetch(`、`parent.document`、`localStorage`——出现任何一处都说明 AI 违反了铁律，退回重造。
3. 全文搜索 `kind: "request"` 附近那行，看请求 id 是不是带点号的写法（如 `插件id_1`）——
   宿主会当场拒发并回 `BAD_REQUEST_ID`，底栏「输出日志区」同时记一笔 `plugin.error`；
   请改成 `p1_xxxxx` 这类形状（模板用的就是 `"p" + 自增序号 + "_" + Date.now().toString(36)`）。

## 4．协作须知（工程口径，别按自己习惯来）

- **验证口径**：本项目**不引入 pytest**。跑测试用
  `.venv\Scripts\python.exe -m unittest tests.<模块名>`，全量逐模块跑
  `for /f %f in ('dir /b tests\test_*.py') do .venv\Scripts\python.exe -m unittest tests.%~nf`；
  `python -m unittest discover` 因 `tests/` 无 `__init__.py` 会直接报错，别用；
  **必须用 `.venv` 里的解释器**，系统 Python 缺依赖会把所有模块打成假报错。
- **前端改动必须真机验证**，不许只靠静态检查。取证脚本口径见 `tools/template_plugin_probe.py`
  （Playwright + 隔离 `JZO_DATA_DIR` / `JZO_PLUGINS_DIR`，不污染开发者本机数据）。
- **干净房间铁律**：插件与底座代码一律从零手写，禁止从任何历史项目搬运源码、样式、数据或注释。
- **白嫖条款不可撤销**：底座与插件永久免注册、免卡密、无签名校验、无联网回连校验、无远程禁用；
  任何一次出网都必须由用户在界面上当场点击发起，严禁后台静默轮询。
- **数据红线**：`.env`、`data/`、真题库 `*.db` 永不出本机、永不进 git、永不进发行包；
  插件私有数据只能写进题目结构的 `extensions`，键用反向域名前缀。
- **契约优先**：实现与 `PLUGIN_SPEC.md` 冲突时，以契约为准并修正实现；改契约必须升 `schema_version`、
  补示例、说明迁移方式并同步补测试。
- 提交信息用中文，说明「为什么」而不只是「改了什么」。

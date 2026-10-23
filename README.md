> **内测期下载说明**：由于内测期，最新离线包请直接在仓库根目录的 `dist/` 文件夹内下载。

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
- **插件清单不绑任何厂商**：底座**没有内置插件市场，也绝不自动拉取、自动更新任何远程源**（防跑路）。官方插件仓库 `jiuzhang-plugins` 的 `plugins.json` 经 gh-proxy 加速后默认预填在 `/plugins` 页输入框里（可当场改成任何自信任地址），点【拉取清单】只读这一份 JSON；点【在线安装】才按条目直链下载那一个 zip，校验门槛与本机拖装完全相同（PLUGIN_SPEC §1.3、§1.4）。

## 开箱即用：配一次密钥就能用 AI

底座自带 OpenAI 兼容通道，配好密钥即出真实模型结果；不配则自动降级为 Mock，界面照样能跑。

```bash
# 仓库根目录建 .env（已被 .gitignore 拦住，绝不会进版本库）
JZO_AI_BASE_URL=https://你的网关地址/compatible-mode/v1
JZO_AI_API_KEY=你的密钥
JZO_AI_MODEL=模型名
JZO_LOCAL_TOKEN=自定义一个本地写令牌        # 可选；不填则首启生成 data/.local_token
```

重启服务后，工作台 `/workspace` 顶部的模型徽标与右栏「模型」会写明当前用的是谁：
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
- 多模型配置面板：工作台顶部模型徽标打开配置面板，填 Base URL / API Key / 模型名并测试连通性，保存即热生效（不重启）；密钥只写本机 `.env`，永不回显、永不入库；新增 `ollama` 本地档，为本地模型预留座位。

`v0.3.1` 是内测首日的抢修版，只动两处体验硬伤：

- 版本号单一事实来源：页面右上角徽章与页脚一律由 `static/js/version.js` 读 `/healthz` 盖章（`app/__init__.py` 的 `__version__` 为唯一来源），HTML 里写死的版本号只是无 JS 时的兜底，并由 `tests/test_version_consistency.py` 锁死一致；`start.bat` 启动前自检端口，若 8000 已被陈留实例占用则明确提示，不再让人对着旧进程的旧版本号发愣；
- `start.bat` pip 自愈：装依赖前先验 `.venv` 内 pip 是否可用，缺失则自动 `ensurepip` 修复，修不好再重建 venv，最后才报错退出。

`v0.4.0` 把「双击即用」再往前推一步，纯浏览器极简路线：

- 启动器等 `/healthz` 真正应答后再拉起系统默认浏览器，不再靠固定秒数猜启动时间；
- 新增极简 PWA 清单、图标与根作用域 Service Worker：Chrome / Edge 可把本站「安装为应用」，以独立窗口运行；SW 只做网络透传、不缓存，避免装完看到旧页面；
- `static/index.html` 头部加浏览器探针，IE 或缺少 ES Module / CSS 变量支持的老内核直接显示「请使用现代浏览器」，不白屏。

`v0.4.1` 按内测反馈重排首页：介绍页卡片顺序改为 01 工作台、02 插件索引，题目 Schema / 插件规范 / 健康检查 / OpenAPI 依次后延，核心入口不再被埋没。

`v0.4.2` 内测防翻车抢修，让「解压即用」真的有事可做：

- 根路径 `/` 直达智能工作台，原底座介绍页改挂 `/about`；工作台边栏底部保留「关于底座（About）」入口；
- 新增种子题库插件 `org.jiuzhang.demo-bank`：首启且无标记时静默安装**随包本地 zip**（5 道高中示例题，零网络请求，用户删掉后不强行装回），工作台欢迎语随之提示可直接输入「拆分第一题」体验。

`v0.4.3` 折叠状态机抢修，专治「收起左栏后错乱、按钮点不动、再也展不开」：

- 三栏各钉死 `grid-column` / `grid-row`，`display:none` 不再牵连余下两栏；两栏补 `overflow:hidden` + `min-width:0`，展开入口补层级，窄屏收起态留 `visibility:hidden`，死锁从根上解除；
- 折叠状态机把 `data-side` / `data-ctx` 立为唯一事实来源，并支持跨断点重算；顺带修掉 360px 下舞台头标题被压成竖排一列字的问题；
- 新增 `tests/test_workspace_fold_state.py` 22 条契约测试，配套 `tools/fold_probe.py` / `tools/pixel_scan.py` 真机取证脚本（开发期工具，不影响运行时）。

`v0.5.0` 插件生态与按需下载——主库极简、插件在线装：

- 仓库根新增官方索引 `plugins.json`：主仓库只放清单，插件本体不再进发放包；占位演示插件 `org.jiuzhang.placeholder` 以 Raw 直链分发（zip 存 `examples/`，`build_release.bat` 明确排除，不进 dist）；
- 「插件索引」页默认预填官方索引 Raw 直链（可当场改成任何自信任地址），点【拉取清单】渲染插件卡片，卡片带【在线安装】按钮，已装条目自动标注「覆盖安装」；
- 后端新增 `POST /api/plugins/install-url`：只在用户点击安装时下载那一个 zip（50 MB 上限、30 秒超时、线程池执行不阻塞主程序），复用本机拖装同款的暂存校验 + 原子落地，下载或校验失败零残留，409 需用户显式确认覆盖；
- 契约同步：PLUGIN_SPEC §1.2/§1.3 修订、新增 §1.4「在线安装」，AGENTS.md 铁律二出网口径追认——红线不变：不自动拉取、不自动更新、不批量安装。

`v0.5.1` 网络突围与智能体接驳——国内直连、插件真调用：

- 官方索引默认直链改走 gh-proxy 国内反代，拉取失败按 ghfast → jsDelivr → fastly.jsDelivr → Raw 的官方序列自动换源，单源 6 秒 / 备用源 5 秒；换源只对官方地址生效，用户改过的自定义地址仍只试一次；响应回传实际命中源、逐路失败原因与 `fallback_used`。主源不用 jsDelivr，是因为其 `@main` 分支缓存最长滞后 12 小时，刚推库的新索引可能仍是旧版；
- 在线安装同口径：主地址失败时按该条目 `mirrors` 顺序重试（主源 30 秒 / 镜像 20 秒），仍只下载用户点选的那一个 zip，不跨条目、不批量、不自动更新；
- 对话引擎接入 OpenAI Function Calling：扫描已安装插件的 `question.import` / `question.render` 能力生成 `tools`，System Prompt 要求意图匹配时直接发 `tool_calls` 而非反问；后端拦截并真实执行，把结果转成自然语言气泡；
- 模型漏判或 Provider 不支持工具时，宿主按高置信句式（明确题号 + 拆分 / 渲染 / 导入）兜底，响应 `route=host` 如实标注；前端气泡新增「[已调用插件]」标识与来源说明；
- 执行边界：后端不执行插件 JS，工具只读插件自带的 `seed/questions.json` 与工作区题库，不写库、不触网；Mock 模式下输入「拆分第一题」也能走宿主兜底，直接返回第 1 题、答案与解析。

`v0.5.2` 插件仓库独立与索引对接——底座轻装、插件集中：

- 官方索引迁到独立仓库 `MT-Blaze/jiuzhang-plugins`，默认预填其 gh-proxy 加速地址；插件 zip 集中放该仓库 `plugins/`，主仓库只保留底座源码与本地镜像清单；
- 主源失败仍按 ghfast → jsDelivr → fastly.jsDelivr → Raw 自动回退；全部不可用时逐源列出失败原因，并提示用户可在输入框手动改填其他索引地址；
- 插件仓库初始收录 `org.jiuzhang.demo-bank` 与 `org.jiuzhang.placeholder`，zip 顶层目录与 `plugin.json` 的 `id` 一致，可直接在线安装；
- 边界不变：不自动拉取、不自动更新、不批量下载，装包仍由用户逐次点击发起。

`v0.6.0` 拖拽式 IDE 底座定型——四区可拖、画布可接管：

- 工作台改为左栏 / 画布 / 右栏 / 底栏四区骨架，由 CSS Grid 五列三行承载，三条不可见分隔条支持鼠标拖拽改变尺寸；拖拽全程零第三方库，`mousedown` → `mousemove` → `mouseup` 直接改 `--sidebar-width` / `--context-width` / `--dock-height` 三个 CSS 变量，折叠态也只改变量、不重写网格轨道，账本始终只有一本；
- 拖拽期间给所有 iframe 上 `pointer-events: none`：插件沙箱不再吞鼠标，跨区拖动不掉帧、不卡死（纯原生暗坑已封）；键盘可用（方向键微调 8px、Shift 32px、Home 复位、双击回默认），分隔条 `role="separator"` 且可聚焦；
- 布局落 `localStorage`（键 `jzo.workspace.layout.v1`），刷新即还原；栏底新增 44px「恢复默认布局」按钮，一键回到出厂尺寸；数据损坏时静默回落默认值，不白屏；
- 画布区新增 Tabs：对话作为**原生标签页**常驻（不进 iframe，避免为拿同源而凿安全洞），第三方插件按 `plugin.json` 的 `stage` 声明挂载为**沙箱 iframe 标签页**（`sandbox="allow-scripts"`），最多同时存活 3 个，超出按 LRU 休眠（发 `plugin.deactivate` 后摘除 DOM），点回标签自动重挂唤醒；
- 新增最小事件总线 `JzoBus`（话题语法校验、通配订阅、订阅者异常隔离、最近 60 条留痕）：右栏面板参数改动发 `ui.params.changed`，画布以 `notification` 单向广播给插件；插件只能往白名单话题（`region.dock` / `region.left` / `region.right` / `stage.selection`）发布，`layout.*` 与 `ui.params.*` 一律拦下，不许插件反过来改宿主布局；
- 底栏「输出」区承接总线事件与插件回报，纯 `textContent` 落 DOM、上限 120 行、可折叠可清空；窄屏（≤768px）自动收成单列并隐藏分隔条。

`v0.5.5` 双向操控与富卡片——AI 能替你点面板，装插件仍由你点头：

- 对话区新增 `ui_json` 富卡片：题目以可视化数学题卡渲染（本地 KaTeX 排版 LaTeX、题型/难度标签、【查看解析】就地展开），全部字段纯文本组装，零 XSS；
- 右侧上下文面板在插件工作模式下可真人操作（年级/难度下拉、快捷按钮）；对 AI 说「改成高一的题」，AI 下发 `update_params`，前端自动把下拉切到高一——**人类手动改过的字段永远覆盖 AI 设定**，请求飞行期间动过即让位并如实播报；
- AI 可搜索插件：新增宿主工具 `search_available_plugins` / `suggest_install`，只读**用户亲手拉取过**的索引缓存，绝不联网搜索；
- 严禁静默安装：命中插件只渲染【安装确认卡】（含来源主机与理由），用户点【确认安装】才走 `POST /api/plugins/install-url` 的完整校验；卡片渲染阶段零网络请求；
- 缺密钥降级 Mock 时双向链路照样可走：Mock 认面板参数，「换成高三、难度调成压轴」同样回 `update_params`；
- 「随机出一道高一基础题」接入插件工具真实抽题（按年级/难度过滤，题库未标注年级时如实说明不过滤）。

`v0.5.4` 左栏终极极简——低频操作收进「设置与控制」：

- 左栏只剩折叠按钮、自由对话入口与动态插件列表；「安装插件 zip」「插件索引」「关于底座」三处入口全部移出；
- 栏底新增一枚 44px 齿轮图标，直达新页面 `/settings`：在线索引拉取、手动安装 zip（文件选择 + 拖拽区）、关于底座信息集中于此；
- 手动安装复用插件安装器全套校验：只收标准 zip、50 MB 上限、409 需显式确认覆盖、失败零残留；
- 工作台保留全局拖拽兜底：zip 拖进页面任意位置即可安装，不必对准某个按钮；装完左栏插件区即时刷新；
- 旧的 `/plugins` 索引页与 `/about` 底座介绍页保持可直达，设置页复用其实现与内容。

`v0.5.3` 侧栏绝对极简——底座零业务、入口全插件：

- 左栏删除写死的「拆分试卷 / 校对解析 / 组卷导出」，只保留「自由对话」这一底座默认入口；
- 左栏主体改为插件区，按 `/api/plugins` 的发现结果动态渲染已安装插件；没装插件时显示「暂无插件」，装完即时刷新；
- 点击「自由对话」或插件条目只切换工作模式：右侧「当前任务」随之更新，插件模式下把插件身份、能力与「现在处于该插件的工作模式下」注入对话上下文，不跳转、不另开页；
- 底座仍不写死任何业务功能；插件坏了或列表读取失败时，自由对话照常可用。

尚未实现：题目编辑表单、导入/组卷/导出、后端插件（清单里的 `backend` 仍按规范拒绝加载）、宿主逐题调度的 `question.card` 卡片位（画布内的插件是自己接管整块舞台后自渲染，宿主不再逐题下发 `question.render`；对话工具里仍会调用）。

## 快速开始

```bash
cd E:\jiuzhang-operator
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

打开 <http://127.0.0.1:8000> 直达智能工作台，设置与控制页位于 <http://127.0.0.1:8000/settings>（左栏底部齿轮），底座介绍页位于 <http://127.0.0.1:8000/about>，健康检查位于 <http://127.0.0.1:8000/healthz>。

写入接口需要本地令牌。可以通过 `JZO_LOCAL_TOKEN` 显式指定，也可以读取首次启动生成在 `data/.local_token` 的令牌：

```bash
curl -X POST http://127.0.0.1:8000/api/questions \
  -H "Content-Type: application/json" \
  -H "X-JZO-Token: $(cat data/.local_token)" \
  -d '{"type":"single_choice","stem":"若 $x+1=2$，则 $x=$（  ）","difficulty":"L1","options":[{"key":"A","content":"$0$"},{"key":"B","content":"$1$"},{"key":"C","content":"$2$"},{"key":"D","content":"$3$"}],"answer":{"kind":"choice","choice_keys":["B"]},"meta":{"author":"local"}}'
```

服务端会补齐 `id`、`schema_version` 与 `meta` 时间戳，返回 `201`。`options` 是**数组**（每项 `{key, content}`），答案形态由 `answer.kind` 声明——一切以 [schemas/question.json](schemas/question.json) 为准，写法不符会被写入侧拒绝并给出可读原因。

预期响应：

```json
{
  "status": "ok",
  "service": "jiuzhang-operator",
  "version": "0.8.1",
  "time": "2026-10-21T12:00:00+00:00"
}
```

## 自己写一个插件

插件就是**一个 zip 包**，不需要注册、不需要编译，也不用改底座。最短路径：

1. 建目录 `com.example.card/`，放进 `plugin.json`、`LICENSE`（Apache-2.0 全文）和 `dist/index.html` + `dist/plugin.js`；
2. 照抄这份最小清单（字段含义与全部取值见 [PLUGIN_SPEC.md §2.3.2](PLUGIN_SPEC.md)）：

```json
{
  "schema_version": "1.0",
  "id": "com.example.card",
  "name": "我的题卡",
  "version": "0.1.0",
  "api_version": "1.0",
  "kind": "renderer",
  "description": "一句话说明这个插件做什么。",
  "license": "Apache-2.0",
  "entry": { "frontend": "dist/index.html" },
  "slots": ["question.card"],
  "capabilities": ["question.render"],
  "permissions": ["questions:read"]
}
```

3. 把整个目录压成 zip 拖进工作台任意位置，或到「设置与控制」页手动安装（也可解压后放进 `plugins/`），再打开 `/api/plugins`：`plugins[]` 里出现自己的 id 就算装好了，`rejected[]` 会写明没装上的原因。

和宿主通信的完整消息协议（`plugin.activate` / `plugin.deactivate` / `question.render` / `notification`）、可直接照抄的 `plugin.js` 骨架与安全边界，见 [PLUGIN_SPEC.md §2.3](PLUGIN_SPEC.md)；可运行样板见 [`examples/placeholder_plugin/`](examples/placeholder_plugin/)。

想让自己的界面出现在中央画布（而不是只在对话里出卡片），在清单里加两块：`slots` 带上 `"stage.center"`，再声明 `stage`（`mode` / `title` / `priority` / `singleton`）与 `bus`（`subscribe` / `publish` 白名单），字段表见 [PLUGIN_SPEC.md §2.4](PLUGIN_SPEC.md)；可运行样板见 [`examples/demo_plugin/`](examples/demo_plugin/)。

> 当前 `v0.8.1` 的页面是四区工作台：插件会被发现并列在左栏，`question.import` 会被对话工具真实调用；工具返回的题目以 `ui_json` 富卡片在对话区渲染。声明了 `stage` 的插件被点击后，会在画布区开一个沙箱 iframe 标签页接管中央舞台（见 PLUGIN_SPEC §2.4）；宿主逐题下发的 `question.card` 卡片位仍未接回（见 PLUGIN_SPEC §2.3.5）。录题工作台（`org.jiuzhang.editor`）经 `bank.create` 把新题写进真题库，写令牌始终留在宿主侧（见 PLUGIN_SPEC §2.6）。**v0.6.3 的真题库读写已全部落在 7 张关系表上**（题目契约 2.0，难度 `L1–L4`），题库画布左侧新增**大纲树**：按 `parent_id` + `sort_order` 懒展开册/章/节/考向，点任一节点即按子树取题。

## 目录结构

```text
jiuzhang-operator/
├── app/
│   ├── __init__.py          # 版本号 + 仓库根 .env 装载器（STACK §1.6）
│   ├── main.py              # FastAPI 应用装配：路由、静态资源、只读规范入口
│   ├── api/
│   │   ├── health.py        # GET /healthz
│   │   ├── questions.py     # /api/questions CRUD
│   │   ├── plugins.py       # /api/plugins 与插件资源分发，含 index 拉取与 install-url 在线安装
│   │   ├── providers.py     # /api/providers 注册表与活跃档切换
│   │   ├── agents.py        # /api/agent/chat|split|review
│   │   └── workspaces.py    # 多工作区列表/新建/切换
│   └── core/
│       ├── config.py        # 路径与环境变量（唯一配置入口）
│       ├── db.py            # SQLite 连接、版本化表结构、事务
│       ├── models.py        # 领域模型与序列化
│       ├── questions.py     # Schema 校验与题目仓库
│       ├── plugins.py       # 插件发现、清单校验与静态资源解析
│       ├── plugin_install.py # 插件 zip 安检与落地安装
│       ├── plugin_sources.py # 官方插件仓库索引的镜像序列（唯一允许内置的远程索引地址）
│       ├── plugin_download.py # 在线安装：按需下载单个 zip，失败按条目 mirrors 重试（§1.4）
│       ├── plugin_tools.py  # 插件能力 → OpenAI tools，工具执行与宿主意图兜底（§1.5）
│       ├── seed_plugin.py   # 首启静默安装种子题库插件（只装本地 zip，不触网）
│       ├── plugin_index.py  # plugins.json 索引：地址守卫 + 只读拉取 + 官方换源
│       ├── provider.py      # AIProvider 抽象基类
│       ├── provider_config.py # 多模型配置（只写本机 .env，永不回显）
│       ├── providers/       # Provider 注册表（扫描本目录模块，密钥只走环境变量）
│       ├── ai_client.py     # OpenAI 兼容客户端（标准库 urllib，无额外依赖）
│       └── security.py      # 本地写入令牌
├── static/
│   ├── index.html           # 底座介绍页（挂 /about，无框架、无 CDN）
│   ├── workspace.html       # 智能工作台（四区：入口与插件 / 画布 Tabs / 上下文 / 输出），根路径直达
│   ├── settings.html        # 设置与控制（在线索引 / 手动装 zip / 关于底座），左栏齿轮进入
│   ├── plugins.html         # 插件索引页（默认预填官方国内镜像，卡片支持在线安装）
│   ├── css/{app,questions,workspace,plugins,settings}.css
│   ├── icons/               # PWA 图标（本地资源，可离线安装为应用）
│   ├── vendor/katex/        # 本地 KaTeX（MIT）——富卡片 LaTeX 离线渲染，零 CDN
│   └── js/{app,workspace,bus,splitpane,stage,plugins,settings,pwa,version}.js
│                            #   bus.js       ★v0.6.0 最小事件总线（话题校验、通配、异常隔离、留痕）
│                            #   splitpane.js ★v0.6.0 四区原生拖拽 + localStorage 布局记忆
│                            #   stage.js     ★v0.6.0 画布 Tabs、沙箱 iframe 挂载与 LRU 休眠
├── schemas/
│   ├── question.json        # 题目交换格式（唯一事实来源）
│   └── plugins-index.json   # plugins.json 索引格式
├── examples/
│   ├── plugins-index.example.json  # 示例清单（地址全部不可用，只示范结构）
│   ├── demo_plugin/                # 种子题库插件源码（5 道示例题）
│   ├── demo_plugin.zip             # 构建产物：首启静默安装的种子包
│   ├── build_demo_plugin.py        # 重新校验并打包 demo_plugin.zip
│   ├── placeholder_plugin/         # 官方占位插件源码（在线安装闭环演示用）
│   ├── placeholder_plugin.zip      # 构建产物：走 CDN/代理镜像分发，不进 dist 发放包
│   └── build_placeholder_plugin.py # 重新打包 placeholder_plugin.zip
├── plugins/
│   ├── README.md            # 插件目录约定
│   ├── org.jiuzhang.classic-card/  # 首个题目卡片渲染插件
│   ├── org.jiuzhang.core-bank/     # 真题题库（456 道真题 + SQLite 随包分发，v0.6.1）
│   ├── org.jiuzhang.paper-gen/     # 组卷排版（题篮 → A4 分页，v0.6.1）
│   ├── org.jiuzhang.handout/       # 讲义排版（Markdown → A4 实时预览，v0.6.1）
│   └── org.jiuzhang.editor/        # ★v0.6.2 录题工作台（表单 + A4 实时预览 → bank.create 入库）
├── tests/
│   ├── test_questions_api.py       # 接口契约与安全边界回归
│   ├── test_plugin_index.py        # 索引解析、地址守卫与官方镜像换源契约
│   ├── test_plugin_install.py      # 插件 zip 安检与安装契约
│   ├── test_plugin_install_url.py  # 在线安装：下载守卫、失败回滚与端点契约
│   ├── test_seed_plugin.py         # 默认路由与种子插件安装契约
│   ├── test_pwa_contract.py        # PWA 清单、图标与 Service Worker 契约
│   ├── test_workspace_fold_state.py # 工作台四区折叠状态机契约（v0.4.3 死锁锁死，v0.6.0 改四区钉轨）
│   ├── test_workspace_sidebar.py   # 工作台左栏与插件工作模式契约（v0.5.3/v0.5.4）
│   ├── test_splitpane_layout.py    # ★v0.6.0：分隔条拖拽安全（iframe 不吃鼠标）、只改变量、布局持久化
│   ├── test_stage_canvas.py        # ★v0.6.0：画布 Tabs、沙箱边界、LRU 休眠与总线白名单
│   ├── test_plugin_stage_contract.py # ★v0.6.0：清单 stage / bus 字段校验与发现接口口径
│   ├── test_settings_page.py       # 设置与控制页：索引、手动安装与 About 契约
│   ├── test_provider_config.py     # 多模型配置面板契约
│   ├── test_providers_api.py       # Provider 注册表与切换契约
│   ├── test_agent_chat_tuning.py   # 智能体对话调参契约
│   ├── test_agent_plugin_tools.py  # 插件工具桥、意图路由与端到端工具调用契约
│   ├── test_rich_card_ui.py        # 富卡片、右栏双向操控与插件搜索契约（v0.5.5）
│   ├── test_editor_contract.py     # ★v0.6.2：录题工作台清单/表单/清洗/写入通道与包体契约
│   └── test_version_consistency.py # 版本号单一事实来源与启动脚本契约
├── tools/
│   ├── build_plugin.py      # 校验并打单插件 zip（顶层为插件 id，解压即用）
│   ├── editor_probe.py      # ★v0.6.2 取证：真机填表单 → A4 预览 → 清洗 → 入库 → 题库查得到
│   ├── fold_probe.py        # 开发期取证：Playwright 真机跑折叠 5 轮 + 命中测试 + 截图
│   └── pixel_scan.py        # 开发期取证：纯标准库解码 PNG，按调色板归类行像素
├── plugins.json             # 官方插件仓库索引的本地镜像（索引页默认预填其 gh-proxy 加速地址）
├── dist/                    # 内测离线包（仅 v0.4.2 起入库，其余版本本地留存）
├── AGENTS.md                # 开发与 AI 代理铁律
├── PLUGIN_SPEC.md           # 插件接入规范（含 §1.1 白嫖条款）
├── STACK.md                 # 技术语法规约（含 §1.6 密钥与环境变量装载）
├── 内测安装与使用指南.md      # 面向内测用户的图文指引
├── 当前架构与开发进度快照.md  # 交接快照（架构、契约与发版账）
├── build_release.bat        # 出包脚本（剔除 .env / data / venv 后压缩到 dist/）
├── start.bat                # 双击启动（自检端口、自愈 pip、就绪后开浏览器）
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
| `/workspace` | 智能工作台（导入原卷 → 发指令 → 出题目与解析） |
| `/plugins` | 插件索引页（默认预填官方镜像，可当场改地址；拉清单只读，装包需逐条点【在线安装】） |
| `/settings` | 设置与控制（在线索引、手动安装 zip、关于底座；工作台左栏齿轮直达） |
| `/api/questions` | 题目列表（分页、搜索、筛选） |
| `/api/plugins` | 已加载插件清单（`rejected[]` 列出未通过校验的插件与原因） |
| `POST /api/plugins/index` | 按用户填入的地址拉取一份插件索引（只读 GET，需一次性写令牌；官方地址失败时自动换源，不解压、不安装） |
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

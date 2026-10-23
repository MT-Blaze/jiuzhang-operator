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

### 1.2 插件分发格式：纯 zip 包，无专属后缀

- **唯一格式**：一个标准 zip 包，**解压即用**。禁止 `.jzo` 或任何自定义后缀/容器格式——对齐主流生态，任何压缩软件、浏览器下载、`unzip` 都能打开它，跑路风险为零。
- zip 只是打包与传输容器，不是运行时格式。安装**永远由用户亲手发起**，共三条等价的路：① 亲手解压后把目录放进 `plugins/`；② 把本地 zip **拖进工作台任意位置，或到「设置与控制」页（`/settings`）拖入/选中文件**，由底座校验后落地（`POST /api/plugins/install`，过一次性写令牌）；③ 在「插件索引」页点某条目的**【在线安装】**，由底座按该条目直链下载那一个 zip 后走同款校验落地（`POST /api/plugins/install-url`，见 §1.4，2026-10-24 军令追认）。底座**绝不自动安装、绝不自动拉取任何远程 zip、绝不自动更新**——每一次安装都必须由用户当场亲手发起（交一个本地文件，或点一次【在线安装】）。静默安装的唯一例外见本节末「官方例外：随包种子插件首启静默安装」。
- **底座禁止写死任何插件下载源**（防跑路）：代码与配置里不得出现任何内置的插件市场地址、插件 zip 的 CDN 域名或自动更新 URL。唯一允许内置的是**官方插件仓库索引自身的镜像序列**（`app/core/plugin_sources.py`，只含 `plugins.json` 地址，不含任何插件 zip 地址），且只在用户点【拉取清单】后按序换源。允许的出网口子只有两个，且都由用户当场点击发起：§1.3 的索引拉取（输入框默认预填**官方索引**的 gh-proxy 国内可达镜像直链，用户可当场改成任何自信任地址）与 §1.4 的在线安装（只下用户点选条目的那一个 zip）。除此之外底座不替用户访问任何远程地址。
- **安装接口的安全底线**：上传的 zip 必须先解压到临时暂存区、逐条目过安全校验、再过完 `plugin.json` 全套契约校验，才允许落地 `plugins/`。拒绝加密条目、符号链接、绝对路径、盘符路径、`..` 穿越、嵌套 zip；条目数与解压总量设上限（防 zip 炸弹）；已存在同名插件时默认拒绝（`409 exists`），只有用户显式确认 `replace` 才覆盖。落地目录名以清单 `id` 为唯一事实来源。实现见 `app/core/plugin_install.py`。
- **包结构**：zip 顶层目录名即插件 id，其内含 `plugin.json` 与 `dist/`、`templates/` 等资源：

```text
org.example.card.zip
└── org.example.card/
    ├── plugin.json
    ├── dist/{plugin.js,styles.css}
    └── templates/card.html
```

- **禁止项**：嵌套 zip、加密条目、绝对路径、`..` 路径穿越、符号链接、超出清单声明的可执行文件。底座对插件资源的解析一律拒绝越界路径（`app/core/plugins.py`）。
- **无签名 / 无摘要 / 无授权校验**：底座不验插件包的数字签名、不比对哈希白名单、不检查许可证状态。清单是否可信由用户自行判断（见 §1.3「地址是用户选的，底座只负责读」）。
- **安装**：两条等价的路，都是用户亲手发起——① 把 zip 拖进工作台任意位置，或到「设置与控制」页（`/settings`）拖入/选中，底座校验后落地；② 自己解压，把目录放进 `plugins/`。二者都无需注册、无需联网、无需重启（发现阶段见 §4）。
- **卸载**：删除该目录。底座不得在别处留存插件运行态残留；插件私有数据只能写在题目 `extensions`（反向域名前缀），随题目数据一起被用户拷走或删除。

**种子插件首启静默安装已退役**：该官方例外随 v0.8.0 清理 demo-bank 一并撤销，底座不再保留任何自动安装通道。`examples/demo_plugin.zip` 仅作为示例与测试夹具保留，不会被底座自动装入。

除此之外不存在任何自动安装通道：插件必须由用户当场亲手发起（见上文与 §1.3）。

### 1.3 plugins.json 插件索引标准

索引是一份**纯静态 JSON**，任何人（个人 Gitee 仓库、对象存储、局域网 Nginx）都能发布；底座对它只做「拉取 + 结构校验 + 展示」，**不解压、不安装、不执行**。

- **拉取入口**：`POST /api/plugins/index`，请求体 `{"url": "...", "allow_mirrors": true}`。地址来自前端「插件索引」页或「设置与控制」页（`static/plugins.html` / `static/settings.html`，两处复用同一实现）的输入框，输入框**默认预填官方插件仓库 `MT-Blaze/jiuzhang-plugins` 的 `plugins.json` 的 gh-proxy 反代直链**（2026-10-24 v0.5.2 军令追认；国内可直连，用户可当场改成任何自信任地址），点【拉取清单】才发起请求——底座不在用户不点击时访问任何地址。
- **官方镜像换源**：请求地址等于官方索引地址时，底座按 `app/core/plugin_sources.py` 的固定序列逐个尝试（gh-proxy → ghfast → jsDelivr → fastly.jsDelivr → Raw），单源 6 秒、备用源各 5 秒；响应里带回 `source_url`、`attempts[]` 与 `fallback_used`，前端如实展示「主源失败、已切到哪一路」。主源选反代而不是 jsDelivr，是因为 jsDelivr 的 `@main` 分支缓存最长可滞后 12 小时，刚推库的新索引可能在首批用户那里仍是旧版。用户改过的自定义地址**只试一次**，不换源——不能把用户的私有地址悄悄换成第三方。全部候选都失败时，错误信息逐源列出失败原因，并提示用户可在输入框手动改填其他索引地址。
- **为什么这个只读接口要带写令牌**：它会替用户向外部发起请求（另一个口子是 §1.4 在线安装），不给令牌等于让浏览器里另一个页面的脚本白嫖本机网络身份。令牌仍是 [`AGENTS.md`](AGENTS.md) 约定的一次性轮换令牌。
- **地址守卫**（`app/core/plugin_index.validate_index_url`）：只接受 `http` / `https`；必须有主机名；**拒绝携带用户名口令**；拒绝 `file:`、`data:` 与相对路径——即不发任何请求前先拒。单次拉取上限 512 KB、条目上限 200。
- **容错口径**：单条写错只让那一条出局并给出可读原因（`rejected[]`），**不得**把整份清单判死；所有镜像都失败、非 JSON、版本不符一律返回 400 + 人话（附每一路的失败原因），不得 500。

结构（JSON Schema 见 [`schemas/plugins-index.json`](schemas/plugins-index.json)，可运行样例见 [`examples/plugins-index.example.json`](examples/plugins-index.example.json)）：

```json
{
  "index_version": "1.0",
  "name": "示例索引",
  "updated_at": "2026-10-21",
  "entries": [
    {
      "id": "org.example.card",
      "name": "经典卡片渲染器",
      "version": "1.0.0",
      "zip_url": "https://example.org/plugins/org.example.card-1.0.0.zip",
      "mirrors": ["https://example.cn/plugins/org.example.card-1.0.0.zip"],
      "kind": "renderer",
      "api_version": "jzo-plugin/1",
      "description": "一句话说明，最长 200 字",
      "homepage": "https://example.org/plugins/card"
    }
  ]
}
```

- **必填**：`index_version`（恒为 `"1.0"`）、`entries`；每条必填 `id`（反向域名，与目录名一致）、`name`、`version`（语义化）、`zip_url`（http(s) 可直达的 zip 地址）。
- **可选**：`mirrors`（≤8 条备用地址，同样必须 http(s) 且不带凭证）、`kind`、`api_version`、`min_host_version`（该条目所需的最低底座版本，语义化；缺省视为不设限）、`description`、`homepage`。
- **可选的顶层 `host` 块**（底座自更新用，见 §1.7）：`{"version": "x.y.z", "zip_url": "...", "mirrors": [...], "notes": "..."}`；字段非法只让 `host` 块自己出局，不牵连 `entries`。
- **索引不是授权体系**：`updated_at`、`api_version` 只用于展示与人工判断，底座**绝不**据此拒绝加载旧插件、强制升级或远程禁用——那会直接违反 §1.1。

### 1.4 在线安装（按需下载单个 zip，2026-10-24 军令追认）

用户在「插件索引」页拉取清单后，点某条目卡片上的**【在线安装】**，底座才去下载**那一个** zip 并安装。这是主库瘦身（插件本体不随包分发）的配套能力，契约如下：

- **入口**：`POST /api/plugins/install-url`，请求体 `{"url": "...", "mirrors": [...], "replace": false}`，带一次性写令牌。`url` 与 `mirrors` 只能来自用户当场点选条目的同一条目——底座不跨条目借源、不在后台自己装东西。用户点一次【在线安装】，底座先试 `zip_url`，失败后按该条目 `mirrors` 顺序各试一次（主源 30 秒、镜像各 20 秒），仍然只下载那一个 zip。
- **地址守卫**：与 §1.3 完全同款（`validate_index_url`）——只收 http(s)、必须有主机名、拒绝凭证、拒绝 `file:` / `data:` / 相对路径，不发请求前先拒；非法地址在联网前整体拒绝（`400 bad_url`）。
- **下载约束**（`app/core/plugin_download.py`）：单包上限 50 MB（与本机上传同口径，超限即掐断）；阻塞 IO 一律放线程池执行，**不得阻塞事件循环**——下载再慢，底座其他页面照常响应。
- **失败回滚**：下载半途失败只是丢弃内存里的字节；安装复用 §1.2 的「暂存区校验 + 原子改名落地」，任何一步失败 `plugins/` 都**零残留**。已存在同名插件默认 `409 exists`，用户显式确认 `replace` 才覆盖。响应回传实际命中的 `source_host`，前端如实展示。
- **校验不降格**：在线安装的 zip 走与本机拖装**完全相同**的全套安全与契约校验（§1.2 禁止项一条不少）；「在线」只改变 zip 的来路，不改变任何门槛。
- **白嫖条款照旧**：在线安装不是授权通道——不注册、不卡密、不签名校验；索引与 zip 地址是否可信由用户自己判断。

### 1.5 插件能力 → 对话工具（Function Calling，v0.5.1）

对话助手可以直接调用已安装插件的**只读能力**，让「拆分第一题」这类指令真正执行，而不是只回一句计划。

- **工具来源**：底座扫描 `plugins/*/plugin.json`，只把清单里显式声明的能力翻译成 OpenAI `tools`：`question.import` → `import_questions`，`question.render` → `render_question`。没有这两类能力的插件不会出现在工具表里，避免给模型假工具。工具名统一为 `plugin_<id 净化>`。
- **参数约束**：`action` 用枚举，`question_no` 限 1–200，`question_id` 必须匹配 `q_` 前缀；模型给的参数一律视为不可信，由底座重新校验后才执行。
- **执行边界**：后端**不执行插件 JS**（前端插件仍只在沙箱 iframe 里跑）。工具只读两处数据：插件自带的 `seed/questions.json`（≤2 MB、≤200 题）与当前工作区题库；不写库、不触网、不读环境变量、不碰插件私有状态。
- **路由**：模型返回 `tool_calls` 时由后端拦截执行；模型漏判或 Provider 不支持工具时，宿主只对**高置信句式**（明确题号 + 拆分/渲染/导入）做兜底路由，响应里 `route=host` 如实标注，绝不把兜底伪装成模型决策。
- **呈现**：插件结果作为自然语言气泡返回，前端在气泡上显式标注「[已调用插件]」，并展示真实执行的插件名。
- **不做**：不开放插件自定义任意函数、不执行工具返回的代码、不把工具结果写回题目结构。

### 1.6 AI 搜索插件索引与安装确认卡（v0.5.5）

对话助手可以**找插件**，但安装权永远在人手里。

- **宿主工具**：底座额外注册两件自有工具（不属于任何插件）：`search_available_plugins`（按用途关键词搜索）与 `suggest_install`（对已知 id 生成安装建议卡）。
- **零联网搜索**：工具只读**用户亲手点过【拉取清单】之后落盘的索引缓存**（`data/plugin_index_cache.json`）；没有缓存就如实提示先去「设置与控制」拉取，底座与模型都不得替用户发起网络请求。
- **严禁静默安装**：命中后只生成 `install_card`（安装确认卡）渲染在对话区，写明来源主机；**只有用户点击卡片上的【确认安装】**，前端才带一次性写令牌调用 `POST /api/plugins/install-url`，走与手动在线安装完全同款的守卫与校验（§1.4），409 时另行确认覆盖。
- **呈现**：卡片数据是纯 JSON（`ui_json` 围栏），前端 `textContent` 组装；模型不得手写 install_card，也不得声称已安装。
- **红线不变**：模型与工具链不自动更新、不批量下载、不跨条目猜地址——§1.1 白嫖条款与防跑路红线一寸未松。唯一的批量出网例外是人在界面上点的【一键更新全部插件】，其边界见 §1.7。

### 1.7 双轨更新：底座与插件（v0.8.3，2026-10-23 主公裁决）

> **交付状态（2026-10-24 军令 #13 任务 10 补齐并真机验证）**：检查/更新端点（`/api/plugins/update/check`、
> `apply`、`pending`、`pending-clear`、`host-apply`）、设置页按钮、`plugin.updated` 广播、`update.bat` 生成与重启续更
> 均已落地。真机证据见 `tools/update_probe.py`（21/21：单条/一键热更、两层 `min_host_version` 拦截、数据必保、
> 底座包校验、开发工作树拒绝覆盖、`update.bat` 沙箱真跑、工作台控制台广播）；底座版本号仍以 `app/__init__.py` 为准。
> 唯一未验证项：在装好的发行包上真正替换正在运行的底座（开发机执行会覆盖工作树，按 ADR-006 由人手工验收）。

更新能力分两条轨道：**插件热更新**（不重启底座）与**底座自更新**（需重启）。两条轨道共用同一份插件索引文档作为唯一远程事实来源，都不新增内置下载源。

**出网时机（裁决 1，逐字生效）**：底座**严禁后台静默自动拉取**——没有定时器、没有启动时顺手检查、没有页面可见性触发的轮询。唯一入口是用户在「设置与控制台 → 插件」面板亲手点击【检查更新】，这一次点击才发一次只读 GET（复用 §1.3 的地址守卫与官方镜像换源序列，不解压、不执行）。检查成功后，前端才拿到「哪些插件有新版本」这张表。

**批量下载的豁免边界（裁决 2）**：底座**严禁后台静默自动拉取。但允许用户手动点击【一键更新全部插件】按钮后，触发单次批量下载。** 三个限定词都是硬边界——
- **手动**：按钮只能由人点，任何代码路径（含对话工具、`plugin_search`、启动钩子）都不得代为触发；
- **一键**：一次点击对应一次批量任务，任务范围就是本次检查结果里「有更新且兼容」的那些条目，不多不少，不跨条目借源；
- **单次**：任务跑完就结束，不排队、不续跑、不定时重试；失败条目如实逐条列出，由人再点一次。

**版本比较与兼容校验**：本地版本读各插件 `plugin.json` 的 `version`，远端版本读索引条目同名字段，按语义化版本（`主.次.修订`，数字段逐段比大小，非数字段按标识符序）判定「更高」；**版本号写坏、缺字段、id 对不上**的条目只让它自己出局并在界面列出原因，不牵连其他插件。兼容校验：条目或本地清单声明了 `min_host_version` 时，与底座 `app.__version__` 比对，不够则该条目标记为**需先更新底座**，红色按钮变灰提示、更新任务跳过它——**绝不覆盖本地代码**。

**热更新的死命令（裁决 3 的前半）**：更新一个插件 = 下载该条目 `zip_url`（失败按同条目 `mirrors`）→ 走 §1.2/§1.4 **完全同款**的暂存区校验 → 只覆盖 `plugins/<id>/` 下的**代码目录**。**严禁触碰 `data/` 目录**：工作区的物理题库、插件私有数据、启用状态、令牌、日志都不在更新的写范围内；校验不通过的 zip 在落地前就被整体丢弃，失败零残留（与在线安装同一套原子改名语义）。已装插件的更新天然需要 `replace=True`，但只针对同一 `id` 的目录，不得改名换目录。

**更新完成后的广播**：设置页每成功落地一个插件，就把本次结果 `postMessage({jzo:"plugins.updated", updated:[{id, from, to}]})` 给宿主；工作台监听后经事件总线广播 `plugin.updated`（载荷 `{id, from, to}`），刷新插件列表与左栏入口状态；若该插件正占据中央画布，宿主触发它的 iframe 重新水合。**全程无需刷新浏览器、无需重启底座**——旧脚本随 iframe 重载自然退出，不参与新事件。

**底座自更新与重启续更（裁决 3 的后半）**：索引顶层 `host` 块（§1.3）声明底座新版本；用户点击底座【更新并重启】后，底座把新版本 zip 下载到**临时目录**并完整校验，成功后生成一次性临时脚本（`%TEMP%\jzo_update_<pid>.bat`）：脚本等父进程退出 → 用 `robocopy` 覆盖程序文件，**排除并保护** `data/`、`.venv/`、`.git/`、`dist/`、`__pycache__/`、`.system_generated/` → 重新拉起底座 → 删除自身。排除项在 `/XD` 里只写**目录名**（军令 #13 沙箱真跑实测：传目标绝对路径在「阶段 → 根」方向不生效，`data/` 会被覆盖）。重启时底座读取本机待更新状态文件（`data/update_state.json`，唯一允许写进 `data/` 的更新痕迹，只存版本号与待办 id，不含题目数据），若上一轮用户点过「一键更新全部」而其中插件因底座重启没更完，则**接着把剩下的补齐**，补齐只消费这份本机清单，不再额外出网。UI 保持极致静默：全过程只在底部日志区逐行输出更新记录，不弹窗、不遮罩。开发工作树（存在 `.git`）拒绝覆盖重启，只生成脚本供人工执行。

**防跑路红线照旧**：更新提示只是提示——用户可以永远不点；底座不因版本旧而拒绝加载插件、不锁功能、不远程禁用（§1.1）。索引地址由用户当场可改，改过之后不自动换源。

---

## 2. 插件分类

本章分三类：§2.1 的 AI 模型档与 §2.2 的数据源是**底座内部扩展**（Python 模块，随底座一起发布）；只有 §2.3 的 UI 渲染插件是**用户可自己写、以 zip 安装的插件**。只想写插件的人可以直接跳到 §2.3。

### 2.1 AI 模型插件（Provider）
提供大模型对话能力。**新增一家供应商只需在 `app/core/providers/` 放一个模块，不改底座、不改前端。**

> 注意：Provider 是底座内置的 Python 模块，不是 zip 插件。想写可安装的插件，看 §2.3。

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
    env_prefix: str = ""    # 该档环境变量前缀（如 "JZO_BAILIAN_"），供配置面板回写 .env 时定位变量名
    is_configured -> bool   # api_key 与 base_url 均非空
```

**活跃档优先级**：环境变量 `JZO_AI_PROVIDER` > 工作区 `config.json` 的 `provider` 键 > 默认档 `openai-compatible`（默认档缺席时取首个已注册档）。切换只写工作区配置，热生效、无需重启。

**降级红线**：`is_configured` 为假时构造出的客户端必须走 Mock 分支并在响应里回 `mock: true`，**不得**抛异常、**不得**假装是真模型产出（对齐 §1.1 的「显式降级」）。对外只暴露「是否已配置 + base_url 的 netloc」，密钥永不下发（见 [STACK.md](STACK.md) §1.6）。

**配置面板契约**（工作台顶部模型徽标打开，已落地）：用户在面板里亲手填入的 Key / Base URL / 模型名，由 `POST /api/providers/config`（写令牌）写回本机 `.env` 并直写环境变量，热生效、不重启；`.env` 已 gitignore，密钥**永不入库、永不写日志、永不下发前端**（AGENTS §5 / STACK §1.6）。`POST /api/providers/test`（写令牌）对该档 Base URL 发一次只读 `GET /models` 做连通性测试，把成功 / 401 / 403 / 404 / 连不上收敛成 `{ok, status_code, host, detail}` 结构化结果——带令牌是因为这是底座替用户出网的口子（同 §1.3 口径）。`.env` 路径可被 `JZO_ENV_FILE` 覆盖（测试 / 启动器专用）。

**内置档**（`app/core/providers/builtin.py` 与 `local.py`，环境变量名即契约的一部分）：
- `openai-compatible` — `JZO_AI_BASE_URL` / `JZO_AI_API_KEY` / `JZO_AI_MODEL`（默认档）
- `bailian` — `JZO_BAILIAN_BASE_URL` / `JZO_BAILIAN_API_KEY` / `JZO_BAILIAN_MODEL`
- `siliconflow` — `JZO_SILICONFLOW_BASE_URL` / `JZO_SILICONFLOW_API_KEY` / `JZO_SILICONFLOW_MODEL`
- `ollama`（本地预留位，`local.py`）— `JZO_OLLAMA_BASE_URL` / `JZO_OLLAMA_API_KEY` / `JZO_OLLAMA_MODEL`；Ollama 自带 OpenAI 兼容接口，无需真密钥，Key 填任意占位（如 `ollama`）即可点亮。

### 2.2 数据源插件（DataSource）——预留，当前不可安装
提供外部数据接入能力（题库同步、OCR 服务、云存储等）。

> 底座当前**没有后端插件运行时**：清单里出现 `backend` 会直接拒装（见 §2.3.2）。本节是留给后续版本的目标契约，现在照着写是装不上的，别踩空。

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

### 2.3 UI 渲染插件（Renderer）：从零写一个能装上的插件

本节写给第一次写插件的人：照着做，半小时能装上一个自己的插件。可运行的最小样板在 [`examples/placeholder_plugin/`](examples/placeholder_plugin/)，整目录照抄再改名最省事。

#### 2.3.1 五步装上一个自己的插件

1. **建目录**：目录名就是插件 `id`（反向域名，如 `com.example.card`），后面必须与 `plugin.json` 里的 `id` 一字不差。
2. **写 `plugin.json`**：字段逐项见 §2.3.2，直接抄下面的例子。
3. **放 `LICENSE`**：插件根目录必须有 `LICENSE` 文件，内容是 Apache-2.0 全文（复制仓库根目录那份即可）。
4. **写入口页**：`dist/index.html` 是入口，`dist/plugin.js` 写逻辑；样式放 `dist/plugin.css`，在入口页里正常 `<link>` 即可。
5. **打包安装**：把整个插件目录压成 zip（zip 最外层是 `id/` 目录，别只压 `dist/`），然后任选一条路：拖进工作台任意位置 / 到「设置与控制」页手动安装 / 解压后把目录放进 `plugins/` / 在插件索引页点【在线安装】。装完打开 `/api/plugins`：`plugins[]` 里有你的 id 就成功了；`rejected[]` 会用中文写清哪条不合格。

目录长这样：

```text
com.example.card/
├── plugin.json
├── LICENSE
├── README.md            # 可选
└── dist/
    ├── index.html       # entry.frontend 指向这里
    ├── plugin.js
    └── plugin.css       # 可选，与入口同目录
```

入口页最小写法（和官方占位插件同款）：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>我的题卡</title>
  <link rel="stylesheet" href="./plugin.css">
</head>
<body>
  <div id="root" hidden></div>
  <script src="./plugin.js"></script>
</body>
</html>
```

#### 2.3.2 plugin.json 字段逐项说明

最小可用清单：

```json
{
  "schema_version": "1.0",
  "id": "com.example.card",
  "name": "我的题卡",
  "version": "0.1.0",
  "api_version": "1.0",
  "kind": "renderer",
  "description": "一句话说明这个插件做什么，最多 200 字。",
  "author": "你的名字",
  "license": "Apache-2.0",
  "entry": { "frontend": "dist/index.html" },
  "slots": ["question.card"],
  "capabilities": ["question.render"],
  "permissions": ["questions:read"]
}
```

| 字段 | 必填 | 规则（写错会被拒装） |
| --- | --- | --- |
| `schema_version` | 是 | 固定 `"1.0"` |
| `id` | 是 | 反向域名，全小写，至少两段（如 `com.example.card`）；**必须与目录名一致** |
| `name` | 是 | 1–64 字，给人看的名字 |
| `version` | 是 | 语义化版本，如 `1.0.0` |
| `api_version` | 是 | `"1.x"` 形式；主版本不是 1 一律拒装 |
| `kind` | 是 | `renderer` / `importer` / `exporter` / `tool` |
| `description` | 是 | 1–200 字 |
| `license` | 是 | 只接受 `"Apache-2.0"`；目录里还必须真有 `LICENSE` 文件 |
| `entry` | 是 | 对象，只认 `entry.frontend`：包内相对路径，必须位于 `dist/` 下，且文件真实存在 |
| `slots` | 是 | 非空数组，取值 `question.card` / `question.detail` / `question.paper` / `answer.panel` / `stage.center`（v0.6.0，中央画布，见 §2.4）/ `sidebar.right`（右栏辅助面板，见 §2.9） |
| `capabilities` | 是 | 非空数组，取值 `question.render` / `question.import` / `question.export` / `question.edit`（v0.6.2 录题写入）/ `paper.generate` / `handout.render`；`renderer` 必须含 `question.render` |
| `permissions` | 是 | 数组，可为空；取值 `questions:read` / `questions:write` / `assets:read` / `assets:write` / `storage:plugin` / `ai:invoke` / `export:file` |
| `author` | 否 | 字符串 |
| `ui` | 否 | 右侧面板控件声明（v0.5.5，见下）；只允许「文本 + 指令模板」，禁止 HTML/脚本；坏控件逐条丢弃，全坏回落到底座按能力生成的默认面板 |
| `stage` | 否 | 中央画布接管声明（v0.6.0，见 §2.4）；对象。写了 `stage` 就必须同时在 `slots` 里带上 `stage.center`，否则拒装 |
| `bus` | 否 | 事件总线订阅/发布白名单（v0.6.0，见 §2.5）；对象。不写时按 `{"subscribe":["ui.params.changed"],"publish":["region.dock"]}` 兜底 |
| `show_in_sidebar` | 否 | 布尔（v0.8.0）。缺省 `true`：插件在工作台左栏占一个入口。**显式填 `false`** 时不出现在左栏（仍可经对话工具、被其它插件调用或在「设置→插件管理与控制」里管理）——适合纯渲染/后台型插件不抢位。底座对插件的**启用/停用**是另一本账，落在本机 `data/plugin_state.json`，不属于清单 |
| `min_host_version` | 否 | 语义化版本字符串（v0.8.3）。声明本插件能跑的**最低底座版本**；【检查更新】时底座拿它与自身 `__version__` 比对，不够则该插件的更新被标为「需先更新底座」并保持原样不覆盖。**缺省视为不设限**。此字段只用于更新提示，底座**绝不**据此拒绝加载已装插件或远程禁用（§1.1） |
| `backend` | **禁止出现** | 底座当前没有后端插件运行时，声明即拒装——不允许假能力 |

> **最常见的坑**：`protocol`、`entry_url`、`assets` 是**宿主返回**的字段，不是 `plugin.json` 的写法。清单里写它们不会被读取；照老教程写还缺 `schema_version` 和 `entry.frontend`，会被直接拒装。CSS 也不用登记，放 `dist/plugin.css` 并在入口页 `<link>` 即可。
>
> 想写 `importer`（让对话能读你自带的题库）：在插件根目录放 `seed/questions.json`，一个题目数组，最多 200 题、文件不超过 2 MB，每题符合 [`schemas/question.json`](schemas/question.json)，并在 `capabilities` 里声明 `question.import`。

**`ui` 字段（v0.5.5 右侧面板）**：形如 `{"title": "…", "hint": "…", "controls": [...]}`，控件总数 ≤8。
- `select`：`{"type":"select","key":"grade","label":"年级","options":[{"value":"高一","label":"高一"}],"default":"高一"}`；`key` 匹配 `^[a-z][a-z0-9_]{0,15}$`，选项 ≤12，值与标签纯文本。当前值随对话 `context.ui.values` 注入模型，模型可用 `update_params` 代人切换——但人类手动改过的字段以人类为准。
- `button`：`{"type":"button","id":"random_question","label":"随机出题","command":"随机出一道题（年级：{grade}；难度：{difficulty}）"}`；`command` ≤200 字，`{key}` 占位符在点击时替换为面板当前值，点击等于在对话区发送该指令。
- 不写 `ui` 时底座按 `kind`/`capabilities` 生成默认面板（导入类给年级/难度下拉 + 随机出题等按钮），保证右栏永远可操作。

#### 2.3.3 和宿主说话：消息协议

宿主把插件放在沙箱 iframe 里，双方只用 `postMessage` 交换三种消息：**宿主发请求，插件回响应；另外双方都可以发单向通知**。

请求（宿主 → 插件）：

```json
{
  "protocol": "jzo-plugin/1",
  "id": "本次请求的随机 id",
  "kind": "request",
  "method": "question.render",
  "payload": { "slot": "question.card", "question": { "id": "q_...", "stem": "题干" } }
}
```

响应（插件 → 宿主）——成功：

```json
{ "protocol": "jzo-plugin/1", "id": "原样带回", "kind": "response", "ok": true, "result": { "html": "<article>...</article>", "height": 96 } }
```

失败：

```json
{ "protocol": "jzo-plugin/1", "id": "原样带回", "kind": "response", "ok": false, "error": { "code": "INVALID_PAYLOAD", "message": "缺少 stem", "retryable": false } }
```

通知（双向，v0.6.0 新增）——单向、不带 `id`、不需要回复，收到就照做，**必须幂等**（同一事件重发不得产生副作用）。通知用 `event` 字段命名事件，不用 `method`：

```json
{ "protocol": "jzo-plugin/1", "kind": "notification", "event": "ui.params.changed", "payload": { "key": "difficulty", "values": { "grade": "高一", "difficulty": "基础" }, "by": "human" } }
```

宿主会发来的方法：

| method / event | kind | 插件要做什么 |
| --- | --- | --- |
| `plugin.activate` | request | 初始化，回 `{ "ready": true }`（可附 `plugin_id`、`api_version`）；`payload.slot` 为 `stage.center` 时表示接管中央画布，可以开始铺自己的整屏界面（§2.4）。**30 秒内必须回**，超时按插件故障处理 |
| `plugin.deactivate` | request | 清理定时器与监听，回 `{ "ready": false }` |
| `question.render` | request | 按 `payload.slot` 渲染 `payload.question`，回 `{ "html": "...", "height": 数字 }` |
| `theme.changed` / `locale.changed` / `question.updated` | request | 记下变化即可，回 `{ "accepted": true }`；不需要可忽略 |
| `ui.params.changed` | notification | 右栏面板参数变了（人改或 AI 改），按 `payload.values` 重绘自己；挂载时也会补发一次当前值 |
| `plugin.deactivate`（`payload.reason = "lru"`） | notification | 被 LRU 休眠前的尽力通知：宿主不等回复就摘 iframe，插件应把该保存的状态提前存好 |

插件可以发给宿主的通知（只有白名单话题会被转发，见 §2.5）：

```json
{ "protocol": "jzo-plugin/1", "kind": "notification", "event": "region.dock", "payload": { "text": "已按高一 + 基础筛出 3 题" } }
```

完整的 `dist/plugin.js` 骨架（可以直接用）：

```javascript
(function () {
  "use strict";
  var PROTOCOL = "jzo-plugin/1";
  var params = {};           // 右栏面板当前值，由 notification 维护

  function redraw() {
    // 按 params 重绘自己的界面；同参数重复调用必须得到同样结果
  }

  function reply(target, id, result) {
    target.postMessage(
      { protocol: PROTOCOL, id: id, kind: "response", ok: true, result: result },
      "*"
    );
  }

  function fail(target, id, code, message) {
    target.postMessage(
      {
        protocol: PROTOCOL, id: id, kind: "response", ok: false,
        error: { code: code, message: message, retryable: false }
      },
      "*"
    );
  }

  function escapeHtml(text) {
    return String(text == null ? "" : text)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  window.addEventListener("message", function (event) {
    var msg = event.data;
    if (!msg || msg.protocol !== PROTOCOL) return;

    // 单向通知：不回复，但要幂等
    if (msg.kind === "notification") {
      if (msg.event === "ui.params.changed") {
        params = (msg.payload && msg.payload.values) || {};
        redraw();          // 重绘多少次结果都一样，才叫幂等
      }
      return;
    }
    if (msg.kind !== "request") return;

    if (msg.method === "plugin.activate") {
      return reply(event.source, msg.id, { ready: true, plugin_id: "com.example.card" });
    }
    if (msg.method === "plugin.deactivate") {
      return reply(event.source, msg.id, { ready: false });
    }
    if (msg.method === "question.render") {
      var payload = msg.payload || {};
      var question = payload.question || {};
      if (typeof question.stem !== "string") {
        return fail(event.source, msg.id, "INVALID_PAYLOAD", "题目缺少 stem。");
      }
      return reply(event.source, msg.id, {
        html: '<article class="my-card">' + escapeHtml(question.stem) + "</article>",
        height: 96
      });
    }
    fail(event.source, msg.id, "UNSUPPORTED_METHOD", "未实现的方法：" + String(msg.method));
  });
})();
```

五条硬规则：① 先校验 `protocol`，再按 `kind` 分流，不认识的消息直接丢弃；② 响应必须原样带回 `id`；③ 一律回 `event.source`，不要猜父窗口；④ 不认识的**请求**回 `UNSUPPORTED_METHOD`，不要静默吞掉；⑤ **通知**不回复、不报错，但必须幂等（宿主会重发，例如挂载时补发一次面板参数）。

#### 2.3.4 安全边界（宿主兜底，但你别踩线）

- **沙箱**：iframe 带 `sandbox`、无 `allow-same-origin`，插件拿不到宿主 DOM、Cookie、localStorage 或写令牌；与宿主只靠 `postMessage` 说话。
- **只读 `dist/`**：资源只从 `/plugin-assets/<id>/dist/...` 发出，只认 `.html` / `.css` / `.js` / `.svg` / `.png` / `.webp` / `.woff2`；包外路径、`..`、符号链接一律 404。
- **不能联网**：入口页 CSP 为 `default-src 'none'; script-src 'self' <底座源>; style-src 'self' <底座源>; img-src 'self' <底座源>; connect-src 'none'; base-uri 'none'; form-action 'none'`，`fetch` / `XHR` / 远程图片全被拦；图片只能用底座托管路径或 `asset://`。
- **返回值会被净化**：插件回传的 HTML 过宿主白名单，`<script>`、内联事件属性、`javascript:` 链接、远程样式与 `@import` 都会被剥掉。别依赖它们，写了也白写。
- **碰不到密钥与文件**：插件拿不到环境变量、模型密钥、数据库和文件系统；需要数据只能走宿主授权范围内的消息。

#### 2.3.5 当前进度（先说清楚，免得装完找不到）

`v0.6.0` 的工作台是四区 IDE 骨架，插件有两条可见路径：

1. **对话工具**：装好的插件出现在左栏插件区与 `/api/plugins`，`question.import` / `question.render` 进入对话工具表（说「拆分第一题」走的就是它），结果以 `ui_json` 富卡片回显在对话页签里；
2. **中央画布**：清单里声明了 `stage` 的插件（§2.4），被点击后在画布开一个沙箱 iframe 页签，收到 `plugin.activate`（`slot: "stage.center"`）后自己铺整屏界面，并可通过 `bus` 白名单往底栏/左栏/右栏推事件（§2.5）。

仍未接回的是**宿主逐题调度的 `question.card` 卡片位**——即宿主拿到一批题目后逐条下发 `question.render`、把返回的 HTML 净化后插进页面上的卡片位。随包示例 `org.jiuzhang.demo-bank`（v0.2.0）走的是第 2 条路径：它在画布里自己渲染题目列表，不依赖宿主逐题下发。按本节写好的插件届时接回卡片位无需改动。

---

### 2.4 舞台接管（Stage）：让插件占据中央画布（v0.6.0）

底座学 VSCode：**左栏、右栏、底栏永远归宿主**，只有中央画布可以被插件接管。画布顶部是一条 Tabs：

- `对话` 是**原生页签**（宿主的自由对话，不进 iframe），永远存在、不可关闭；
- 声明了 `stage` 的插件默认占**一个页签**（按插件 id 去重，重复点击只是切回）；若清单写 `"singleton": false`，重复点击会开出 `插件名 #2`、`#3`，各页签拥有独立 iframe 与独立 `plugin.activate`；
- 页签可关闭；关闭即停用并摘除 iframe。

清单里这样声明（完整示例见 [`examples/demo_plugin/plugin.json`](examples/demo_plugin/plugin.json)）：

```json
{
  "slots": ["question.card", "stage.center"],
  "stage": {
    "region": "center",
    "mode": "takeover",
    "title": "示例题库",
    "priority": 10,
    "singleton": true
  }
}
```

| 字段 | 必填 | 规则 |
| --- | --- | --- |
| `stage.region` | 否 | 只认 `"center"`；写别的值等于没写（左/右/底栏不接受插件接管） |
| `stage.mode` | 否 | `embed`（默认，与其他页签共存）/ `takeover`（切到该页签即占满画布）/ `fullscreen`（额外隐藏左右栏与底栏，只看插件）。非法值回落 `embed` |
| `stage.title` | 否 | 页签标题，≤24 字，超长截断；缺省用 `name` |
| `stage.priority` | 否 | −100…100，超出被夹紧。**v0.6.1 起真实消费**：插件页签按优先级从高到低排列（同优先级按打开先后），原生「对话」页签永远排第一；左栏插件列表也按同一数值排序。 |
| `stage.singleton` | 否 | 默认 `true`：同一插件只允许一个页签。填 `false` 时允许开多个页签（键为 `plugin:<id>#2`…，标题追加 `#2`），用于对照阅读、双栏组卷等场景。 |

硬约束：

- **写了 `stage` 就必须在 `slots` 里带上 `stage.center`**，否则拒装（报错原文含 `stage.center`），防止「有接管声明却没有插槽授权」这种假能力；
- 反过来只写 `slots: ["stage.center"]` 而不写 `stage`，按 `mode: "embed"`、`title = name` 兜底，不拒装；
- `fullscreen` 只切宿主的全屏标志位，**不会改写用户手动折叠/拖拽的偏好**：退出全屏后左右栏与四区尺寸原样回来；
- 页签数量不设上限，但**同时存活的 iframe 最多 3 个**（LRU）：超出的按「最久未使用」休眠——宿主先发一条 `plugin.deactivate` 通知（不等回复），再摘掉 iframe，页签上标「休眠」。点回页签自动重挂并重新 `plugin.activate`。所以插件必须做到「随时可被摘掉、随时可重新激活」，别把状态只存在内存里指望它长命；
- 激活请求 30 秒不回、iframe 加载失败，页签就地显示故障说明与「底座仍可继续使用对话页」，不影响其他页签（§5.2）。

---

### 2.5 事件总线（HostBus）：跨区通信与发布白名单（v0.6.0）

宿主内置一条最小事件总线（`window.JzoBus`，约 130 行，零依赖）。它的职责只有一句：**让右栏的参数改动能找到中央画布里那个具体的插件，让插件的输出能找到底栏**。

话题语法：`^[a-z][a-z0-9_]*(\.[a-z0-9_*]+){1,3}$`（2–4 段小写点分，支持 `*` 单段通配与 `**` 多段通配）。单话题订阅者上限 32，总线保留最近 60 条事件留痕供排查。

宿主在用的话题：

| 话题 | 方向 | 载荷 |
| --- | --- | --- |
| `ui.params.changed` | 右栏 → 画布/插件 | `{ pluginId, key, values, revisions, by }`；`by` 为 `human` / `ai`，人类手改过的字段永远压过 AI 设定 |
| `layout.changed` | 分隔条 → 全局 | `{ by, pane, value, sizes }`；`by` 为 `drag` / `key` / `reset` / `restore`（刷新还原时发 `restore`，底栏据此不回写日志，免得刷屏） |
| `region.dock` | 插件/宿主 → 底栏 | `{ text, topic?, pluginId? }`；`text` 截断 200 字，纯 `textContent` 落 DOM，不解析 HTML |
| `region.left` / `region.right` / `stage.selection` | 插件 → 宿主区域 | 预留：宿主接受但不解释内容，逐条记录到底栏 |
| `stage.tab.sleep` | 画布 → 内部 | `{ key, pluginId }`，休眠留痕 |
| `basket.changed` | 画布 → 内部 | `{ action, total, pluginId }`；题篮被插件增删后广播，组卷/讲义插件可据此刷新（v0.6.1）。`action` 为 `add` / `remove` / `clear`。 |

插件侧的发布白名单在清单 `bus` 字段里声明：

```json
{ "bus": { "subscribe": ["ui.params.changed", "stage.tab.activated"], "publish": ["region.dock"] } }
```

| 字段 | 规则 |
| --- | --- |
| `bus.subscribe` | 只接受宿主已定义的入站事件（`ui.params.changed` / `layout.changed` / `stage.tab.*` / `theme.changed` / `question.updated`），未定义项逐条丢弃；缺省 `["ui.params.changed"]` |
| `bus.publish` | 只接受 `region.dock` / `region.left` / `region.right` / `stage.selection`；**`layout.*` 与 `ui.params.*` 永远发不出去**——插件不许反过来改宿主布局或伪造面板参数；缺省 `["region.dock"]` |
| 条目总数 | ≤8，超出的截断；整个 `bus` 写坏（不是对象）时按缺省值兜底，不拒装 |

插件发事件的实际写法就是一条通知（见 §2.3.3）：`{ kind: "notification", event: "region.dock", payload: { text: "..." } }`。宿主收到后先查白名单，不在名单里的**丢弃并在底栏写明「想发未授权事件 xxx，已丢弃」**——不静默、不抛错、不断链。

订阅者异常彼此隔离：任何一个处理函数抛错都不会中断其余订阅者，宿主只在底栏记一笔。这条与「插件坏了，底座还能用」是同一件事的两个方向。

---

### 2.6 插件数据通道（Host API 转发，v0.6.1；写入通道 v0.6.2）

插件在沙箱里拿不到数据库、文件系统与写令牌（§2 铁律）。需要题库/题篮数据时，插件向宿主发一条 **request**，宿主查完再回 **response**：

```js
// 插件 → 宿主
{ protocol: "jzo-plugin/1", id: "p1_x8", kind: "request",
  method: "bank.list", payload: { grade: "高一", page: 1, page_size: 12 } }

// 宿主 → 插件
{ protocol: "jzo-plugin/1", id: "p1_x8", kind: "response", ok: true,
  result: { items: [...], total: 456, page: 1, page_size: 12, total_pages: 38 } }
```

| 方法 | 用途 | 关键约束 |
| --- | --- | --- |
| `bank.list` | 分页取题 | `grade` / `difficulty` / `type` / `chapter` / `textbook` / `q` / `page` / `page_size`；`page_size` ≤100，搜索词 ≤100 字；面板的展示值「全部」由宿主翻译为「不过滤」 |
| `bank.stats` | 年级/难度/题型/章节计数 | 只读 |
| `bank.active_list` | 分页取题（**当前活跃题库**） | 参数与 `bank.list` 完全相同；与 `bank.get` / `bank.topics` 同源，供浏览型插件跨库查看，不按页签 id 拼路由 |
| `bank.active_stats` | 活跃题库的年级/难度/题型/章节计数 | 与 `bank.stats` 同口径，数据源为当前活跃 provider |
| `bank.get` | 单题全文 | `id` 必须匹配 `^[A-Za-z0-9_-]{1,80}$` |
| `bank.random` | 按条件随机一题 | 无匹配时返回 404 |
| `bank.create` | 新增一道题（v0.6.2） | 需 `questions:write` 权限；`payload.question` 必须符合 `schemas/question.json`；**只能写入底座公共题库**（`org.jiuzhang.core-bank`），插件自报目标无效；ID / 时间戳由底座生成 |
| `basket.list` | 读题篮 | `expand: true` 时附带题目全文 |
| `basket.add` | 加题（批量） | 最多 200 个 id；全部必须存在于**当前插件自己的题库**，否则整批拒绝 |
| `basket.active_add` | 加题到题篮（记在**当前活跃题库**名下） | 参数与 `basket.add` 相同；供浏览型插件使用，避免题目被记到一个空库名下导致读题篮时取不到全文 |
| `basket.remove` | 移除一题 | 需要题目 id |
| `basket.clear` | 清空 | 无参数 |
| `asset.upload` | 上传框选/切出的题目配图（军令 #13） | 需 `assets:write` 权限；`payload.data_url` 只接受 PNG / JPEG / WebP 的 base64 data URL，解码后 ≤8 MiB；文件名由底座生成，返回 `{id, uri, mime, bytes, sha256}`，`uri` 可直接写进 `\includegraphics{...}` 与 `images[].uri` |

安全边界：

- **插件身份只来自页签**：宿主用 `tab.plugin.id` 拼接口，插件在 payload 里自报 `plugin_id` 一律忽略，防止 A 插件读 B 插件题库；
- 写令牌由宿主代取（`/api/settings`，一次性），只放进宿主发出的请求头，**插件永远看不到令牌**；
- 每次调用限流 80 次 / 10 秒 / 页签，单次转发 20 秒超时；超限回 `RATE_LIMITED`，不会把本机 SQLite 打满；
- 方法白名单之外一律回 `UNSUPPORTED_METHOD`，插件无法借宿主访问任意 URL；
- 写入类方法（`bank.create` / `asset.upload`）在宿主侧先查页签插件的 `permissions`，未声明 `questions:write` / `assets:write` 直接回 `FORBIDDEN`，不进入后端。

当前使用方：[`org.jiuzhang.core-bank`](plugins/org.jiuzhang.core-bank/plugin.json)（SQLite 存储端，纯净发版只随包冻结 `schema.sql`，不携带真题，见 ADR-003）；[`org.jiuzhang.editor`](plugins/org.jiuzhang.editor/plugin.json) 经 `bank.create` 写入新题、经 `asset.upload` 落地框选配图。后续组卷、讲义插件复用同一通道，不新增协议。

#### 2.6.1 题库 provider 可替换（v0.8.2）——底座不写死 `core-bank`

官方 `core-bank` 只是**默认的**题库 provider，不是唯一的。任何第三方插件只要满足三条，就能被底座当作活跃题库使用：

1. **清单声明能力** `capabilities: ["bank.provider"]`，并在 `permissions` 里声明 `questions:read`（要接受写入再加 `questions:write`）；
2. **实现标准读方法**：`bank.list` / `bank.stats` / `bank.get` / `bank.random`（可选 `bank.topics` / `bank.topic_notes` / `bank.review`），出参结构必须逐字符合 `schemas/question.json`（含 `id` 全局身份、Markdown + LaTeX 文本、`extensions` 反向域名键）；
3. **不越界**：数据只经 Host API 与总线进出，插件不得直连数据库、文件系统、环境变量或密钥（AGENTS 铁律二）。

路由口径（缺一即违规）：

- **谁在用**：宿主（`static/js/stage.js`）启动时向 `GET /api/bank/provider` 取「当前活跃 provider」，把 `bank.get` / `bank.topics` / `bank.create` 等**跨页签共享**的通道指向它；`bank.list` / `bank.stats` / `bank.random` 与题篮仍按**页签自己的 plugin.id** 走 `/api/bank/plugins/{plugin_id}/…`，天然多库并存。
- **浏览型插件怎么取题**：像题库浏览视图这种**自己没有题库**的插件，禁止用 `bank.list` / `bank.stats`（那会按它自己的页签 id 去查一个空库），必须用 `bank.active_list` / `bank.active_stats`——这两条与 `bank.get` / `bank.topics` 同源，永远指向当前活跃 provider。
- **谁在选**：活跃 provider 落在本机 `data/bank_provider.json`，由用户在【设置与控制台 → 工作区管理】里选；写入接口需带一次性写令牌。
- **怎么选得上**：被设置的 id 必须**已安装**且**声明了 `bank.provider` 能力**，否则底座拒绝写入并回 400；读取时若配置的 provider 已卸载或不合规，**回退默认 provider 并如实回报 `fallback_reason`**——「插件坏了，底座还能用」（AGENTS §2）。
- **不许写死**：底座与插件代码里不得出现 `org.jiuzhang.core-bank` 字面量作为路由目标（打包/索引/测试夹具除外）。默认值只允许出现在 `app/core/bank_provider.py` 的 `DEFAULT_PROVIDER_ID` 一处。
- **契约不变**：换 provider 不换协议。`question.json` 是唯一标准结构（§2.5 与 AGENTS §3），provider 私有数据只能写进 `extensions`，底座不解释。

> **当前边界（如实说明，别当已交付）**：官方 provider 的存储层仍是 core-bank 的 7 张关系表 + 两张版本表，`app/core/bank.py` 的结构守卫按 `bank/schema.sql` 校验。第三方若要用 JSON / MySQL / 自研结构**服务同一套 `bank.*`**，还缺一个 provider 反向 RPC 运行时（§2.2 数据源插件的预留位，与 §6.1「后端插件运行时」同源）；在那之前，可替换的是**路由与身份**，不是**存储引擎本身**。

### 2.7 多版本教材与考向并集（v0.8.2 地基）

主公定调的终极架构：**一个老师的题库要同时挂多套教材目录**。三条硬规则，存储层已把不变量钉进 CHECK：

1. **考向表是并集**：`topics` 里层别为 `tp_kx` 的考向节点**不属于任何教材版本**——
   `ck_topics_taxonomy_shared CHECK (substr(id,1,5) <> 'tp_kx' OR textbook_id IS NULL)` 直接拒掉「把考向绑版本」。
   谁有新考向，就往这个池子里加；**同一考向全库只有一行**。
2. **大纲树是子集视图**：`textbooks` 一行一个教材版本（人教A版 / 苏教版 / 北师大版…），
   `topics` 里 `tp_bo` / `tp_ch` / `tp_se` 是**版本目录节点**，必须带 `textbook_id`；
   左侧大纲树按版本取，取到的就是该版本的子集，不是全库。
3. **跨版本靠映射表**：`node_topic_map(outline_node_id, topic_id, textbook_id, sort_order)` 是
   「版本目录节点 → 考向」的多对多。同一考向可以同时出现在人教A版第三章和苏教版第五章下；
   题目本身**一行都不复制**——题目只经 `question_topics` 指向考向，换版本不改题目、不改题-考向关联。
   两条 CHECK 把方向钉死：`outline_node_id` 只许 `tp_bo/tp_ch/tp_se`，`topic_id` 只许 `tp_kx`。

**接入第二个教材版本的正确姿势**（苏教版来了该做什么，只此一条路）：

```sql
INSERT INTO textbooks (id, name, publisher, edition, is_default, created_at, updated_at)
     VALUES ('tb_xxxxxxxx', '苏教版', '江苏教育出版社', '', 0, …);   -- ① 只加一行版本
INSERT INTO topics (id, parent_id, textbook_id, name, path, …)              -- ② 只加它自己的
     VALUES ('tp_boYYYYYYYY', NULL, 'tb_xxxxxxxx', '必修第一册', …);        --    目录节点
INSERT INTO node_topic_map (outline_node_id, topic_id, textbook_id, sort_order, created_at)
     VALUES ('tp_boYYYYYYYY', 'tp_kx…', 'tb_xxxxxxxx', 0, …);               -- ③ 指向既有考向
```

**禁止**：复制考向节点、给考向填 `textbook_id`、把题目按版本再录一遍、
在 `node_topic_map` 里挂「章→章」「节→节」这类非考向目标（CHECK 会拒）。

**结构版本与升级**：`PRAGMA user_version = 2`。老库（v0.6.3 七表）由底座首启就地升级
（`app/core/bank.py` 的 `upgrade_structure`），也可离线跑 `tools/migrate_bank_v082.py --apply`；
升级前自动落 `<库名>.pre-v082.bak` 备份，自检（行数 / 外键 / 完整性 / 并集不变量 /
映射可还原原树 / 映射行数对账）不过就整事务回滚。`topics` 用「建新表搬数据」而不是
`ALTER ADD COLUMN`——ALTER 加不上 CHECK，那样新建库有不变量、迁移库没有，一份代码面对两套结构必出错。

**展示口径**：`bank.topics` 目前返回**默认版本**的大纲树（现网只有人教A版）；带 `textbook=` 参数取指定版本
是下一步（provider 反向 RPC 与多版本 UI 一起做），本轮只保证**地基能承载**，不假装 UI 已就绪。

---

### 2.8 AI 开发铁律与第三方插件模板（2026-10-23 军令 #06）

第三方老师将普遍用 AI 代写插件。为让 AI 一次生成**不破坏底座架构**的代码，本节把插件契约压成
五条可逐字转述给大模型的**铁律**，并提供极简模板 [`examples/template-plugin/`](examples/template-plugin/)
（打包产物 `examples/template-plugin.zip`，重打包脚本 `examples/build_template_plugin.py`）。
可直接复制给任何大模型的完整提示词见 [README.md「如何用 AI 开发九章算子插件？」](README.md)。

| # | 铁律 | 契约依据 |
| --- | --- | --- |
| 1 | **严禁点对点耦合**：插件之间不直接调用、不共享全局状态，所有跨插件通信必须且只能经底座事件总线中转 | §2.5、AGENTS 铁律二 |
| 2 | **数据读写走宿主 API**：严禁插件直连底座数据库/文件系统/环境变量/密钥，题库数据只能经 `bank.*` / `basket.*` 请求-响应通道换取；注意**公共真题库**（`bank.get` / `bank.review` / `bank.topics` / `bank.create`）与**插件自带库**（`bank.list` / `bank.stats` / `bank.random`，需随包放 `bank/schema.sql`）是两类通道 | §2.6、§2.3.4 |
| 3 | **状态同步走事件总线**：改状态必须经 `kind:"notification"` 广播，事件名必须在清单 `bus.publish` 白名单内；严禁调用其他插件函数、严禁伪造 `ui.params.*` / `layout.*` | §2.5 |
| 4 | **UI 隔离在沙箱 iframe**：视图封闭在专属沙箱内，严禁越权操作父窗口 DOM/Cookie/localStorage；与宿主唯一通道是 `window.parent.postMessage` | §2.3.4 |
| 5 | **环境依赖只用原生 JS/CSS**：严禁引入重型前端框架与 CDN 资源（CSP `connect-src 'none'` 会拦死远程加载），公式一律 Markdown + LaTeX | §2.3.4、AGENTS §4 |

**请求封包 `id` 的形状（2026-10-23 真机取证补上的硬约束）**：宿主在消息入口用
`^[A-Za-z0-9_-]{1,80}$` 校验 `kind:"request"` 的 `id`，**不匹配的请求不转发到数据通道**，
而是当场回一条 `ok:false` + `code:"BAD_REQUEST_ID"` 的同 id 回执，并在底栏「输出日志区」记一笔
`plugin.error`（v0.8.3 军令 #07 批复 2 之前的旧行为是整体静默丢弃，开发者只能干等插件自己的超时）。
因此插件不得拿带点号的插件 id 当请求 id 前缀（`org.example.template_1` 这类写法历史上一发出海即沉）；
官方插件与模板统一用 `"p" + 自增序号 + "_" + Date.now().toString(36)`。
插件侧仍必须为每个请求设超时并给出可读提示，不得静默吞掉。

**`engine.host_version`（模板新增的可选声明块）**：模板清单带 `"engine": {"host_version": "0.8.2"}`，
表示「本模板按哪一版底座的契约生成」，供 AI 与人工对照用；**底座更新检查消费的仍是顶层
`min_host_version` 字段**（§1.7 裁决 2 的兼容校验，§2.3.2 字段表）。两者值可以相同，但语义不同：
`engine.host_version` 是参照说明，`min_host_version` 是硬约束声明。底座对 `engine` 块不解释、不校验、
不据此拒绝加载（§1.1 防跑路红线同样适用于这个新字段）。

模板 zip 必须与官方占位包一样通过全套 `validate_plugin` 契约（`tests/test_plugin_install_url.py::
OfficialIndexFileTest::test_03c_template_plugin_zip_passes_full_plugin_contract` 钉死），
请求 id 过守卫由 `test_03d_template_request_id_passes_host_message_guard` 钉死，
真机链路（左栏入口→沙箱页签→activate 回执→宿主 API 往返→`region.dock` 落底栏→坏 id 当场回执与底栏记账）由
`tools/template_plugin_probe.py` 取证：2026-10-23 裸装模板 **18/18**，复制官方 `core-bank`
进隔离目录跑黄金路径 **19/19**，沙箱内实测「取到 10 题（共 209 题）」并渲染 10 张卡；
且不进 dist 发放包（`build_release.bat` 的 `/XF` 排除，胖仓库红线同 §placeholder_plugin.zip）。

### 2.9 右栏辅助面板（sidebar.right，2026-10-24 军令 #13）

右栏默认是底座自带的「AI 副驾」。插件声明 `"slots": ["sidebar.right"]` 后，底座会把右栏交给它，
**没有插件认领时整块插槽隐藏、AI 副驾原样回来**——插槽是加法，不替换既有兜底。

```json
{
  "id": "org.example.inspector",
  "slots": ["sidebar.right"],
  "capabilities": ["question.render"],
  "permissions": ["questions:read"],
  "entry": { "frontend": "dist/index.html" }
}
```

契约：

- **同一时刻只挂一个**：多个插件都声明 `sidebar.right` 时，按与画布同一套排序（`stage.priority`
  高者优先，同优先级按名称）取第一个；停用（`enabled=false`）的插件不参与。
- **隔离与协议不变**：面板同样是 `sandbox="allow-scripts"` 的沙箱 iframe（不透明源），
  走 `jzo-plugin/1`；挂载后宿主发 `plugin.activate`，payload 为 `{"slot": "sidebar.right"}`，
  插件照常回 `{ready: true}`。
- **Host API 与画布页签完全一致**：`bank.*` / `basket.*` / `draft.*` 都可用，写操作仍由宿主代持
  一次性令牌，插件看不到令牌；`bus.publish` 白名单同 §2.5（`region.right` 专供向本栏投递文本）。
- **激活失败要能退回**：`plugin.activate` 超时或报错时，宿主记录 `context.panel.error`
  并切回 AI 副驾，绝不把右栏留成白屏。
- **尺寸自适应**：右栏可拖拽、可折叠（宽度 0），面板必须按容器宽度自适应；
  宿主给面板的默认可视高度是 `52vh`（不小于 300px），面板内部自行滚动，禁止撑破右栏。
- **刷新时机**：插件装卸、停用、覆盖升级都会让 `/api/plugins` 清单签名变化，右栏随之重挂；
  运行中的面板 iframe 不热替换代码（§4），与画布页签同规则。

## 3. 多工作区（Workspace）隔离

### 3.1 架构设计
一套前端挂载多个 SQLite 库，每个工作区拥有独立的：
- 数据库文件（`data/workspaces/<id>/questions.db`）
- 上传资源目录（`data/workspaces/<id>/uploads/`）
- 配置快照（`data/workspaces/<id>/config.json`）

### 3.2 切换机制
工作区切换下拉框在「设置与控制台 → 题库工作区」（军令 #13 起左栏不再放题库下拉），选择后：
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
| --- | --- | --- |
| 发现 | 每次 `GET /api/plugins` 扫描 `plugins/`、读取并校验 `plugin.json`（不合格进 `rejected[]`，不影响其他插件） | 清单合法，目录名与 `id` 一致 |
| 加载 | 在沙箱 iframe 中打开 `entry.frontend`（经 `/plugin-assets/<id>/dist/...` 分发） | 页面能独立加载，不依赖宿主全局变量 |
| 激活 | 发出 `plugin.activate` 请求（接管画布时带 `payload.slot = "stage.center"`，30 秒超时） | 初始化内部状态并回响应（`ready: true`） |
| 运行 | 按用户操作发出 `question.render` 等请求；右栏参数变化以 `ui.params.changed` 通知广播 | 处理消息并回 `result`，错误回 `error`；通知按幂等处理 |
| 休眠 | 画布同时存活的 iframe 超过 3 个时，按 LRU 发一条 `plugin.deactivate` **通知**（不等回复）后摘除 iframe，页签标「休眠」（§2.4） | 状态别只存内存；被摘后要能在重新激活时恢复 |
| 停用 | 发出 `plugin.deactivate` 请求 | 清理定时器、事件监听 |
| 卸载 | 移除 iframe；用户删除目录即完成卸载 | 不要在自己目录之外写任何文件 |

发现是「请求时扫描」，改清单或换插件目录无需重启服务；正在运行的 iframe 要刷新页面才会加载新代码。装错的插件会被隔离在 `rejected[]` 里，底座与其他插件照常工作。

---

## 5. 错误处理

### 5.1 超时控制
宿主对插件请求设置 30 秒超时，超时后：
- 记录错误日志
- 向用户显示「插件响应超时」
- 不阻断主流程（降级为默认行为）

### 5.2 异常隔离
插件抛出的未捕获异常不得导致宿主崩溃。处理请求时自己兜住异常，回一条结构化错误，而不是让消息石沉大海：

```javascript
try {
  handleRequest(msg);
} catch (err) {
  console.error("[Plugin " + PLUGIN_ID + "] 处理失败：", err);
  fail(event.source, msg.id, "INTERNAL_ERROR", "插件内部错误，请重试。");
}
```

宿主侧同样兜底：超时、连续报错或 iframe 崩溃时回落到默认展示，并记录隔离日志，不拖垮底板。

---

## 6. 版本兼容

- 宿主当前只认 `api_version` 主版本 **1**（写作 `"1.x"`），主版本不符直接拒装；次版本用于向后兼容的新增能力。
- `version` 是插件自己的语义化版本，只用于展示与人工判断；底座不据此强制升级，也不会远程禁用旧版（对齐 §1.1）。
- 协议标识固定为 `jzo-plugin/1`，出现在消息封包与 `/api/plugins` 响应的 `protocol` 字段；它**不是** `plugin.json` 的字段，别写进清单。

---

## 7. 附录：测试要求

每个插件类型必须提供：
1. **契约测试**：验证接口签名符合规范
2. **隔离测试**：验证沙箱无法逃逸
3. **性能测试**：单次操作耗时 < 500ms（P95）
4. **回归测试**：宿主更新后插件仍能正常工作

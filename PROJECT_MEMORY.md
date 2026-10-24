# PROJECT_MEMORY.md — 九章算子外挂大脑

本文件是给 AI 代理与接任者读的**跨会话交接底稿**。只记「不读代码就不知道、且下次会话必须知道」的事；
能从仓库现状推出的（目录结构、函数签名、依赖清单）一律不写在这里，避免与代码各说各话。

最后更新：2026-10-24（军令 #14「彻夜六阶段闭环与 v0.9.0 封版攻坚」六阶段全部交付并封版：版本升 0.9.0、出 `dist/jiuzhang-operator-beta-v0.9.0.zip`；阶段五真机自更新压测 25/25 绿，钉死 `update.bat` 三类真机根因；另收录官方 QQ 群 1105273716）

---

## 项目基础信息

| 项 | 值 |
| --- | --- |
| 项目 | 九章算子（Jiuzhang Operator）——为独立教师打造的模块化数学题库底座 |
| 仓库 | `https://github.com/MT-Blaze/jiuzhang-operator` |
| 许可 | Apache License 2.0（见 `LICENSE`；铁律，不得修改或删改） |
| 技术栈 | Python 3.10+ / FastAPI / Uvicorn；原生 HTML+CSS+JS（无打包器）；SQLite（WAL，标准库 `sqlite3`） |
| 底座版本唯一事实来源 | `app/__init__.py` 的 `__version__`；页面徽章由 `/healthz` 经 `static/js/version.js` 写入 `[data-app-version]` |
| 官方插件仓库 | `jiuzhang-plugins`（`plugins.json`；界面默认预填 gh-proxy 国内镜像直链） |
| **官方交流群** | **QQ 群 `1105273716`**；扫码加群 <https://qm.qq.com/q/WMqM5l8YQc>；二维码图片 `static/assets/qq-group.png`（README 文末【官方交流群】引用同一张图） |

---

## 一、项目铁律（不可协商，与 `AGENTS.md` 同源）

1. **纯本地、无云端**：底座与所有插件可完全离线运行；资源本地化，无 Node 运行时、无打包器。
   密钥只从环境变量或本地 `.env` 读取，**永不入库、永不写日志、永不进入插件上下文**。
2. **万物皆插件**：业务能力（渲染、录入、导入、组卷、讲义、导出、AI 辅助、统计）一律插件化；
   底座只做鉴权、导航、数据总线、插件生命周期、安全边界与错误隔离。插件不得直连数据库或文件系统，
   只能经 Host API；插件间只能经数据总线协作；沙箱 iframe + 白名单 HTML 净化。
3. **底座极简、坏了能用了**：任一插件加载失败/超时/连续报错，底座必须仍可浏览与导出，走兜底渲染。
4. **数据契约唯一**：`schemas/question.json` 是题目在底座/插件/导入导出之间流转的唯一标准结构；
   文本一律 Markdown + LaTeX（`$...$` / `$$...$$`），不得另造公式方言；题目全局身份只有 `id`（`q_` 前缀），
   原卷题号只属于来源关系；插件私有数据只能写进 `extensions`，键用反向域名前缀。
5. **白嫖不可撤销**：个人版永久开源免费（Apache-2.0），底座与插件免注册、免卡密、无签名校验、
   无远程禁用；插件格式为**纯 zip 解压即用**，禁止专属后缀。**出网铁律（2026-10-23 主公裁决，逐字生效）：
   底座严禁后台静默自动拉取。但允许用户手动点击【一键更新全部】按钮后，触发单次批量下载。**
   三个口子都必须人在界面上当场点击发起：①插件索引拉取；②单条目在线安装；③双轨更新（检查更新 /
   更新 / 一键更新全部插件 / 底座更新并重启）。**无定时器、无启动顺手拉、无后台轮询。**
   更新的写范围只有 `plugins/<id>/` 代码目录与底座程序文件，**严禁触碰 `data/`**（唯一例外：
   `data/update_state.json` 只记版本号与待办 id，不含题目数据）。详见 `PLUGIN_SPEC.md` §1.7。
6. **干净房间（铁律一）**：所有代码与文档原创，严禁从 `E:\math-question-bank-main` 等历史目录复制源码、
   样式、脚本、测试、图片与目录结构。依赖白名单 Apache/MIT/BSD/ISC，**禁止 AGPL/GPL**。
7. **AI 代理不得**执行 `git push`、建远端、改写历史或发布 Release，**除非用户明确要求**。

---

## 二、当前核心进度（v0.9.0）

> **军令 #15（2026-10-24）AI 助手插件化与权限边界重构**：右侧对话框从宿主壳里整体搬出，
> 落为普通插件 [`org.jiuzhang.chat`](plugins/org.jiuzhang.chat/plugin.json)（`slots: ["sidebar.right"]`、
> `capabilities: ["assistant.chat"]`、`permissions: ["ai:invoke"]`）；四项任务全部落地，决策记录见 ADR-009
> （声明取代 ADR-002 第 4 条）。要点：① AI 的每一次动手都是 Host API 请求（`AI_ONLY_METHODS` 七条 +
> 清单授权守卫），插件侧 `fetch`/`parent.document`/`localStorage` 命中为 0；② `trigger_button` 通道从
> 提示词、白名单、前端三侧绝迹，面板按钮只属于人（宿主广播 `panel.button.click`，助手以
> `origin:"panel_button"` 发这一轮）；③ 智能跳转闭环——后端把统计结果装配成 `data.actions`
> （白名单 `open_bank`/`open_editor`、去重 ≤3），老师点【前往题库并搜索】后底座开页签并以
> `system.bank_query` 把检索词送进 core-bank 与 bank-browser 两只插件；④ 右栏主权只认**当前画布页签**，
> 默认住户是助手、无认领者给可读兜底（不再隐藏、不再复活宿主私有副驾）。左栏硬编码「自由对话」入口与
> 宿主对话 DOM 一并清除，中栏兜底改为原生不可关「引导」页签。契约修订：`PLUGIN_SPEC.md` §2.9 重写、
> 新增 §2.10。验证：43 模块 846 测全绿（新增 `tests/test_ai_plugin_boundary.py` 34 测，重锚 7 个既有模块），
> 死样式经审计脚本取证后删除（宿主未引用 token 48 → 3）。底座版本仍为 0.9.0（本军令不发版）。
>
> **军令 #14（2026-10-24 彻夜）六阶段全部交付并封版**：底座版本 **0.8.2 → 0.9.0**，
> 发行包 `dist/jiuzhang-operator-beta-v0.9.0.zip` 已出（包内种子库仍是冻结空壳，0 题）。
> 六个阶段严格按序，每阶段一个 commit：
> ① 阶段一 解析器与 FTS5 接进插件 UI（`8ff3c17`）；② 阶段二 清缴遗留控制台与启动项欠账（`7c02c5b`）；
> ③ 阶段三 A4 试卷与讲义的 PDF 导出（`aa170ac`）；④ 阶段四 题库批量导入与导出（`dd8613d`）；
> ⑤ 阶段五 真机压测自更新全流程（`1ac1224`）；⑥ 阶段六 升版、清 `dist/`、出包、统一推送（本次 commit）。
> **阶段五的收获（三类真机根因，非推断）**：自更新脚本在真机上一直不生效，根因逐条钉死——
> ① `update.bat` 里 `tasklist | find` 会被 **Git Bash 的 `usr/bin/find.exe` 抢占 PATH**，那行让整篇批处理当场终止，
> 改用 `for /f` 读 tasklist 的 CSV + 绝对路径；② 无控制台的 DETACHED_PROCESS 里 `timeout` 不可靠，睡眠换 `ping -n 2`；
> ③ **无控制台时 cmd 的 `echo` 写控制台会失败，整篇批处理停在第一行**——拉起脚本时 stdout/stderr 一律接日志文件。
> 另：`.bat` 必须按控制台 ANSI 码页（mbcs）落盘（UTF-8 中文会被 cp936 误解出引号与管道符），
> 且用 `write_bytes` 落盘避免 `Path.write_text` 的二次换行转换把 CRLF 变成 `\r\r\n`。
> **robocopy 排除清单新增 `plugins/`**：发行包内自带 core-bank 空壳种子库，底座自更新覆盖它等于拿空库换掉老师的真题库；
> 插件版本归插件热更通道（合并语义、保住本机数据文件）管。
> **验证**：全量 42 模块 **809 测全绿**（`.venv/Scripts/python.exe` 逐模块，`tools/run_all_tests.py`）；
> 真机自更新探针 **25/25**（`.system_generated/self_update_probe/stage5-run6/`，含截图与 `result.json`）。
> 详见根目录 `Morning_Report.md`。

> **军令 #14 追加军令「清缴索引漂移与收工」（2026-10-24 收尾）**：
> ① **索引漂移已清**：先重建 `org.jiuzhang.editor` **0.4.0** 包（30,187 B / 5 条目）覆盖插件仓发布件，
> 再跑 `tools/sync_plugin_index.py` 把两份索引（主仓根 `plugins.json` 与 `E:\jiuzhang-plugins\plugins.json`）
> 的 editor 条目由 0.3.0 校准为 0.4.0，两份**逐字节全等**（sha256 前 12 位 `3e4d1faa423d`）；
> 5 条目版本与已发布 zip 逐一相符，**0 漂移**。**顺序不可颠倒**：已发布 zip 若还停在 0.3.0，
> 只改索引等于让索引宣称 0.4.0 而用户下载到 0.3.0。`updated_at` 改为跟随当天，不再写死。
> ② **三条控制台欠账实为已清**：核对代码后确认（勿再照抄旧结论，先读代码）——
> `settings.html` 左树右二级页签已落地、顶栏 Provider 弹窗已退役、
> `bank.topics` 已按 `textbook_id`/工作区偏好过滤并配 `POST /api/workspaces/textbook` 与 3 个契约测试，
> 均由 `7c02c5b` 清缴。上一轮晨报把它们误列为「仍在」，已公开更正。
> ③ **唯一新增活账**：**未在真实安装目录由人手点过「更新并重启」**（探针走的是脚本直调，非真人 GUI 路径）。
> ④ **验证**：全量 42 模块 **809 测全绿**（`tools/run_all_tests.py`，本轮实测 0 失败）。

> **军令 #13（2026-10-24 彻夜）11 项全部交付，版本仍 0.8.2、未发版**：四大模块按序落地并逐项 commit——
> ① 任务 1 启动行为（沿用 #11 第三阶段 `882e56b`）；② 任务 2 左栏 48px 顶线、三视图底栏与插件拖拽排序（`511bd1e`）；
> ③ 任务 3 右栏 `sidebar.right` 动态插槽与插件化契约（`38031b0`）；④ 任务 4 `question_parser` 纯函数地基（`22b350f`）；
> ⑤ 任务 5 FTS5 中文检索预研（`bee3d61`）；⑥ 任务 6 `exam-paper` 组卷/答题卡（`1bdaba1`）；
> ⑦ 任务 7 `lecture` 讲义工作台（`db250b7`）；⑧ 任务 8 `bank-browser` 浏览与编辑跳转（`7041728`）；
> ⑨ 任务 9 editor 三栏对比 + Canvas 框选切图（`54d40c1`）；⑩ 任务 10 双轨更新运行时与 21/21 真机探针（`b40e816`）；
> ⑪ 任务 11 死代码瘦身、晨报与统一推送（本次 commit）。
> **任务 11 清理**：删 `app/core/seed_plugin.py`（v0.8.0 起已无调用方，PLUGIN_SPEC 改为「已退役」）；
> 清掉旧题库列表页与已删控件留下的 26 个 CSS 类（questions/workspace/settings 共 −238 行、−3,975 B），
> 路由与 demo-zip 契约测试改名保留。`tools/audit_code.py` 仍 ERROR 0（WARN 33 均为固定 SQL 标识符/已净化 innerHTML）。
> **验证**：全量 39 模块 **749 测全绿**（`.venv/Scripts/python.exe` 逐模块；较上轮 −3 为退役的种子安装测例）；
> 三页真机回归 13/13（零控制台错误、375px 无横向溢出），截图与 `probe.json` 在 `.system_generated/task11_css_probe/`。
> 详见根目录 `Morning_Report.md`。

> **v0.8.2（2026-10-24）多版本地基 + 题库路由解耦 + 四区通高几何**：三件事一起落。
> ① **考向并集地基**：`schema.sql` 解冻加 `textbooks` 与 `node_topic_map` 两张表、`topics` 加 `textbook_id`，
> 并用 CHECK 钉死「考向（tp_kx）不许绑版本」；`user_version` 1→2，现网 456 题库与本地种子库已无损洗入
> （映射 1780 行可独立还原原树，各落 `.pre-v082.bak`，首启自动升级、自检不过整事务回滚）。
> ② **题库 provider 可替换**：官方 core-bank 降级为默认值，新增 `app/core/bank_provider.py` 与
> `/api/bank/provider` 三端点，宿主 `CANONICAL_BANK_ID` 退役（PLUGIN_SPEC §2.6.1）。
> ③ **UI 定调**：左右两栏上下通高、【输出日志区（Output）】只吃中列且定名（"控制台"三字专属画布页签）、
> 左下角齿轮链接退役换纯图标开【设置与控制台】页签（宿主自有、非可卸载插件），`/settings` 仍可直达防变砖。
> **顺手堵掉一个真泄漏**：升级备份是 456 题整份副本，`build_release.bat` 原先不剔 `*.bak`，会被打进发行包。
> 全量单测 437 全绿；控制台真机探针 14/14、组卷探针 41/41 无回归。详见 ADR-005。
> **明确欠账（别当已交付）**：控制台内部「左树右二级菜单」未做（现仍内嵌既有设置页整页）；
> 工作台顶栏的 Provider 配置弹窗仍在（应迁进控制台 系统设置 面板，只有一个调用点）；
> 大纲树尚未按所选教材版本过滤（`/api/bank/textbooks` 与 `POST /api/workspaces/textbook` 已就绪）。

> **v0.8.1（2026-10-24）A4 视口级虚拟渲染——3.58s 重排欠账清算**：`org.jiuzhang.paper-gen` 排版引擎重写（0.2.0→0.3.0）。
> 铁律改成「肉眼一次只看 2-3 页，就不许让浏览器同步排 72 页」：72 张占位纸先立起来，只有进视口 ±1 的页才挂真实 DOM，
> 离远的页清空回收；分页从「DOM 重排」降级成「纯算术」——每题按 `题目ID+密度+内容签名` 缓存一次量好的落件高度，
> 答案段独立量高（摘下来量、装回去用），于是**切答案不重测题干**。真机同数据同口径对比（50 道长题）：
> 切显示答案 **3904.9ms → 245.8ms**、切紧凑 **3450.0ms → 264.1ms**、切回隐藏 **9.3ms**、首屏 **926.2ms → 400.7ms**；
> 全卷补齐改到空闲片里后台跑（1.4–2.8s，不阻塞交互），打印前同步补齐保证不缺页。
> 探针 41/41 绿（含逐页滚动清点 75 页、答案段清点 48 条吻合、狂拉滚动条 6 次跳页最大 181ms 无白屏），
> 临时放宽的 4s 上限撤回归 300ms 红线并写进契约测试。全量单测 416 全绿。方案与边界见 ADR-004。

> **v0.8.0（2026-10-24）插件管理与控制台**：设置页新增【插件管理与控制】面板，实现三态——**启用/停用**（停用即从工作台左栏消失、代码与数据原地保留，状态落 `data/plugin_state.json`）、**卸载**（二次确认「是否保留数据」：保留=只删 `plugins/<id>/` 代码目录；彻底=连各工作区物理 `.db` 一并销毁，红警）、**安装**（本地拖 zip + 在线索引，复用既有链路）。新增【导入已有题库数据】：选本地 `.db`（base64 上传、无 multipart 依赖）校验七表后挂载为新工作区并切换。清单新增 `show_in_sidebar` 字段（classic-card 置 false 不占左栏）；左栏插件副标题改为直白功能描述。**清理历史包袱**：底座不再首启自动安装 `demo-bank`（移除 lifespan 调用 + 出索引 + 删本地运行时目录），demo-bank 降级为纯 dev/test 样本。底座 0.7.2→0.8.0。单测 410 全绿；base 包 1,027,424 B，本地 456 题完好。

> **v0.7.2（2026-10-24）极简工作区与纯净发版**：对外一切产物（GitHub、`dist`、`core-bank.zip`）改为**纯净空壳**——只发冻结 `schema.sql`，不再携带任何真题 `.db` 与题库配图；`bank.db`/`v063_migrated.db` 已从 git 跟踪移除（本地原样保留、用 `git rm --cached` 不删盘）。左栏顶部新增【当前题库 ▼】物理工作区切换/新建；`ensure_bank` 缺种子退回建空库、新区一律空壳。core-bank 插件 0.4.0→0.5.0，底座 0.7.1→0.7.2。单测 398 全绿。详见 ADR-003。

> **v0.7.1（2026-10-24）极致好用闭环**：录题端补【删除题目】（二次确认，走 `bank.delete`，级联摘关联、保留共享节点）与选项 `image_ids` 回填/保存链路；四条极致好用硬指标落地——宿主代持 `localStorage` 草稿保护、顶部【另存为新题（派生变式）】、保存后 1 秒自动收页 + 静默回流、右栏升级为感知当前题的 AI 副驾（`/api/agent/refine` 改写题干/解析并 `editor.apply_patch` 回填）。editor 升 0.3.0。A4 回归：组卷 25/25、讲义 22/22、录题 19/19（真机探针）；单测 389 全绿。详见 ADR-002。

**数据库微内核重构完成，空库已建，456 题数据已洗入新结构。**

| 事实 | 数值 / 位置 |
|---|---|
| 冻结表结构 | `plugins/org.jiuzhang.core-bank/bank/schema.sql`，7 张业务表 + `bank_meta`，SHA-256 `3ba41e999b4b…`（本轮仅补 `sources.grade`） |
| 空库（0 数据） | `plugins/org.jiuzhang.core-bank/bank/v063.db`，159,744 B，`user_version=1` |
| 灌库产物 | `plugins/org.jiuzhang.core-bank/bank/v063_migrated.db` |
| 入表数据 | 题 456 · 大纲节点 701（册 5 / 章 18 / 节 84 / 考向 594，其中 draft 12）· 学校 347 · 试卷 27 · 题-考向 456 · 题-来源 456 · 教研笔记 150 |
| 难度口径 | 恢复 L1–L4 原码（42 / 140 / 134 / 140），不再折成 basic/medium/hard |
| 自检 | `PRAGMA foreign_key_check` 无违规，`integrity_check=ok`，全量单测 **358/358 OK**（v0.6.3 封版时为 347） |
| 迁移工具 | `tools/build_bank_schema.py`（建空库+自检+报告）、`tools/migrate_bank_v063.py`（灌库）、`tools/verify_bank_empty.py`（逐表 COUNT 核对） |
| 审计报告 | `docs/v0.6.3-题型纠偏清单.md`、`docs/v0.6.3-灌库校验.md`、`data/bank_v063_migration_report.json` |

**现网已切（P0#1 完成）**：`app/core/bank.py` 的读写路径、`app/api/bank.py` 的 HTTP 通道与
`static/js/stage.js` 的数据白名单全部走 7 张关系表；现网工作区库
`data/banks/org.jiuzhang.core-bank.db` 已是新结构（456 题，`user_version=1`）。
旧宽表整套改名为 `data/banks/org.jiuzhang.core-bank.legacy.db`（含 `-wal`/`-shm`）作历史备份，**未覆写**。
两处仍需下一棒当心：① **种子库 `plugins/org.jiuzhang.core-bank/bank/bank.db` 仍是 v0.6.2 宽表**——
新装的机器首次建库会读到宽表，底座 `connect()` 有结构守卫会如实报 `BankError` 并指向
`tools/migrate_bank_v063.py --promote`；封版（P0#4）必须把新结构库换成该种子。
② 前端插件侧还没接新通道：`bank.topics`/`bank.topic_notes` 白名单与端点已开，
但 core-bank 插件的 `ui.controls` 难度下拉、大纲树渲染仍是旧口径（P0#2）。

**字段落位与本轮裁决（主公 2026-10-23 20:00 批复三条 + 追认两处自裁）**：
- **冲突 A → 升契约**：`schemas/question.json` 的 `difficulty` 统一为 `L1/L2/L3/L4`，
  `novel` 彻底废弃并入 `L4`；因属破坏性变更，题目契约升主版本 **2.0**（`$id` 同步为
  `question-2.0.json`）。底座写入端对 1.0 旧值做强制归一（`app/core/contract.py` 的
  `normalize_difficulty`：basic→L1 / medium→L2 / hard→L3 / novel→L4），**出参只发 L 码**。
  连带改了底座 `questions` 表的 CHECK（`app/core/db.py` `user_version` 1→2，带 `.pre-v2.bak` 备份）、
  `plugin_tools.py` 标签与中文意图词、`ui_cards.py`、`agents.py` 提示词、`workspace.js` 题卡标签、
  `examples/demo_plugin` 种子与其 zip。
- **冲突 B → 备份旧库**：见上一段，严禁覆写。
- **冲突 C → 补全 schema.sql**：`sources.grade` 已写进 `bank/schema.sql`（含 `ck_sources_grade`、
  `idx_sources_grade`，并进入 `uq_sources_paper`），迁移脚本里的 `ALTER TABLE` 补丁已删。
  schema.sql 的 SHA-256 由 `43db4ed34725…` 变为 **`3ba41e999b4b…`**——本轮结构解冻**只**动了 sources 这一列。
- **自裁追认**：`type=proof/unknown` 走 422 如实报错（存储 CHECK 只收四类），不折叠成 solution；
  `answer` 出参合成对象、库内 `NULL` 时**整个省略**该字段，不拿字母冒充答案。
- 早前既有的口径不变：`tags`（含「疑似变式#N」查重噪声）丢弃不入新库；章/节、`images`、`tikz`、
  `option_columns` 落 `questions.extensions` 有序数组 `[{key,label,value}]`，
  适配层（`bank.extensions_to_array` / `extensions_to_object`）做「数组 ↔ 反向域名对象」双向映射。

**出参装配的已知损失（下一棒别当 bug 查）**：
- `answer.kind` 在库里不分列：选择题按字母合成 `choice`，非选择题一律 `text`
  （写入时 `content` 优先、退回 `final`；因此录题往返后 `expression/proof` 会变成 `text`，
  `final` 与 `content` 同值）。
- `meta.status` 与 `revision` 新表没有对应列：出参恒为 `published` / `revision=1`（草稿态需要落库时另议）。
- 年级双写：`sources.grade`（权威，筛选与统计走它）+ `extensions` 的 `org.jiuzhang.core-bank.grade`
  （无来源时的回退）。真实库上高一 420 / 高三 36，与旧宽表逐题口径一致。
- `source` 出参只取该题的**首个**来源行（一题多张卷的完整展开留给 P1 录题升级）。

**迁移里必须知道的数据坑**：
- 现库（旧宽表）对 31 道选择题用**硬编码 A** 冒充答案；新库已如实置 `NULL`（18 无答案正文 / 9 标记后空白 / 4 只有解析），别再当真实数据用。
- `answer IS NULL` 共 53 题 = 31 道选择题（无任何字母依据）+ 22 道非选择题（旧库连答案正文都没有）。
- 2 道题（`q_legacy_000421`、`q_legacy_000483`）选项内嵌在题干文字里、拆不出选项，与新表
  「选择题必须 ≥2 选项」的 CHECK 冲突，暂按原判入表并打 `structure_conflict` 标记。
- 26 道题旧库只登记到节、没有考向 id，挂在节层（`topic_unmapped` 标记）；10 个「章名当节名」的
  登记补成 draft 节节点；2 个大纲查无的考向 id 补成 draft 考向节点挂在章下。
- `option_columns` 旧库 456 题**全是 0**，实际无内容，未写入 extensions。
- 教研笔记只入 method/pitfall 共 150 条（覆盖 75 个考向）；10 条 `knowledge` 正文是
  `@mindmap/{...}` 导图 DSL 而非笔记散文，本轮**未入表**（`topic_notes` 的 CHECK 已预留 `knowledge`）。
- 题型纠偏尺子：`答案区 = 第一个【解析】之前` → 剥 `\textbf{}` 壳、去 `$...$` → 取连续 A–H 字母；
  答案区取不到时退到正文尾句「故选/因此选 + 字母」。**旧库声明的题型不可信**，以字母为准。

---

## 三、核心架构决策记录（ADR）

### ADR-001：三端分离架构（主公 2026-10-23 定调，v0.7.0 落地）

**决策**：题库（`org.jiuzhang.core-bank`）是**存储端**、组卷（`paper-gen`）与讲义（`handout`）是**输出端**，
两端一律**只读**；录题工作台（`org.jiuzhang.editor`）是**唯一输入端**，独占读写。
所有涉及修改题目的操作，必须统一经 EventBus 的 `system.open_editor` 跳转到录题插件处理，
处理完毕后由宿主广播 `system.question_updated` 触发各端回流刷新。

**为什么**：改题一旦在多个端各写一份，就会出现「同一道题在题库里改了、组卷里还是旧的」这类
跨端不一致；把写权收敛到单一输入端，配合宿主统一生成事件，任何时刻只有一条写路径、一个真相来源。
这也让权限边界变得可讲：core-bank 清单里连 `questions:write` 都不再声明（v0.6.4 曾短暂给过，本轮收回）。

**协议落点**：
- 事件名登记在 `static/js/stage.js` 的 `PUBLISH_ALLOW`：插件只许发 `system.open_editor`（去编辑）
  与 `system.return_from_editor`（保存后返回来源页）；未授权事件一律丢弃并在底栏记账。
- 跳转由**宿主**完成：`openEditor()` 找/开 editor 页签，唤醒后补发 `system.open_editor` 注入题号；
  插件之间不直连、不共享全局状态（AGENTS §2）。
- 回流广播走 `system.question_updated`；`question.updated` 是 v0.6.x 的旧名，宿主**两个名字各广播一次**，
  老插件不掉队；订阅端一律做 260–300ms 去重，避免一次保存刷两遍。
- 公共真题库的只读通道（`bank.get`/`bank.topics`/`bank.topic_notes`/`bank.review`）与写入通道一样
  固定指向 `CANONICAL_BANK_ID`——录题端要改真题，不能被自己的页签 id 引到别的库上。

**已知边界**：讲义排的是发送过来的那份 HTML，题目被改后它**不能**假装重排，只标脏并提示从组卷端重发；
`topic_unmapped` 的 26 题现在在录题端的大纲树选择器里可挂（v0.7.0 起），题库端不再有行内改题入口。

### ADR-002：极致好用的四条硬指标与「派生变式」（主公 2026-10-24 定调，v0.7.1 落地）

**决策**：录题工作台在「能录能改」之上，永久绑定四条**极致好用**硬指标，并把「派生变式」确立为一等概念：

1. **草稿保护**：编辑内容边写边自动保存，老师改一半关掉 Tab 再打开不丢。
   实现口径：沙箱 iframe 是不透明源（只给 `allow-scripts`，不同源），插件里访问本地存储会直接抛异常，
   所以草稿**只能由同源的宿主代持**——插件经 `draft.save`/`draft.load` 两个宿主 RPC 交存表单态，
   宿主写进 `localStorage` 并按 `plugin.id` 分命名空间（A 插件读不到 B 插件的草稿）。
   **红线**：`org.jiuzhang.editor` 的 `plugin.js` 里永远不许出现 `localStorage` 字样（契约测试钉死）。
2. **另存为派生变式**：顶部【另存为新题（派生变式）】按钮——复制当前表单内容交底座重新签发 ID 新建一题，
   **绝不覆盖原题**；派生后编辑目标自动切到新题，原题保持不动。
3. **自动关闭与静默回流**：点保存后弹 Toast「保存成功」，**1 秒后自动收起编辑 Tab、切回来源列表**；
   列表由宿主广播 `system.question_updated` 在后台静默刷新，无白屏。收页信号是插件发布的
   `system.editor_close`（登记进 `PUBLISH_ALLOW`），由 `closeTab(editor)` + `activate(来源页签)` 落地。
4. **右侧 AI 副驾**：右栏常驻区升级为 AI 对话面板——订阅 `stage.selection` 感知录题端当前题，
   老师一句话让模型改写题干/解析，点【回填到表单】由宿主 `broadcast("editor.apply_patch", …)` 推回录题端。
   **改题主动权始终在老师手里**：副驾只产出候选文本、只回填到表单，不落库；点保存才经写路径入库。
   > **已被 ADR-009 取代（军令 #15，2026-10-24）**：副驾不再住在底座托管的右栏里，而是降格为普通插件
   > `org.jiuzhang.chat`；`stage.selection` 感知与 `editor.apply_patch` 回填两条能力保留，但只能经
   > Host API 与总线发起，「回填到表单」由老师点击触发，AI 不再有代点击能力。

**为什么**：三端分离解决了「一致」，但一个老师真正每天的录改动作里，最怕的是**改一半丢内容**、
**想做同考点变式却只能整题重录**、**保存后还要手动切回列表**、**润色题干要来回复制**。
这四条把这几件高频摩擦一次性抹平，才叫「极致好用」；派生变式是数学教研的刚需——同一考向要出一族
难度递进的题，复制派生远比从零录入省命。AI 副驾放进**底座托管的右栏**而非插件内，
是为了守住「插件碰不到宿主 DOM、跨端协作只走总线」的插件化边界（AGENTS §2）。

**协议落点**：
- 后端新增 `bank.delete`（`DELETE /api/bank/plugins/{core-bank}/questions/{id}`，带写令牌，
  关联表靠 `ON DELETE CASCADE` 摘净，**共享的来源/学校/大纲节点一律保留**，删后同步从题篮摘除）。
- `/api/agent/refine`：只改写 `stem`/`solution` 白名单字段，缺密钥时 **Mock 原样回显、绝不编造**；
  越界字段夹回 `stem`。
- 选项配图（`options[].image_ids` 与顶层 `images`）必须进表单回填与保存链路，改题干不得洗掉配图。
- editor 清单 `bus.subscribe` 增 `editor.apply_patch`，`bus.publish` 增 `system.editor_close`。

**已知边界**：草稿是本地易失态，不进库、不出网、随浏览器存储清理而失；派生变式对**非选择题**
不带选项时按当前表单实际内容派生（不强塞空选项）；AI 副驾回填要求 `id` 与当前编辑题一致，
对不上就拒绝回填，避免把改写贴到错的题上。

### ADR-003：无账号、纯物理文件工作区——本地留真题、打包发空壳（主公 2026-10-24 定调，v0.7.2 落地）

**决策**：九章算子**没有账号、没有云、没有任何远程题库分发**。一个「工作区」就是一个物理 SQLite 文件目录，
底座只认本地磁盘上的 `.db`。对外发布的一切产物（GitHub 仓库、`dist` 发行包、插件仓库里的 `core-bank.zip`）
一律是**纯净空壳**：随包只发冻结的 `schema.sql`，**绝不携带任何真题数据 `.db` 与真题配图**。
用户首次启动即在纯净环境里得到一个空库，靠录题工作台自建自己的题库；可随时在工作区下拉里切换/新建物理库。

**为什么**：
- 真题库是老师的**私有财产与合规边界**——把 456 道（或任何）真题打进公开发行的 zip，等于替用户把
  数据摊到 GitHub，既泄露内容又与「白嫖不可撤销、数据只在本机」的立场冲突。
- 「工作区 = 一个物理 `.db`」是最诚实、零依赖的隔离：不需要用户注册、不需要联网、不怕跑路，
  删一个目录就是一个工作区蒸发，符合 AGENTS 的离线/本机铁律。
- 本地开发又必须能一眼看到真题库跑回归，所以种子机制保留，但**种子只在开发机、只喂 default 工作区**。

**落地口径（三条物理边界，缺一即违规）**：
1. **git 不携带真题**：`plugins/org.jiuzhang.core-bank/bank/bank.db`（456 题种子）与
   `v063_migrated.db`（456 题）已从 git 跟踪移除并写进 `.gitignore`；**本地文件原样保留**（用 `git rm --cached`，绝不删盘）。
   随包仍跟踪的是 `v063.db`（0 题空基线）与 `schema.sql`。
2. **发行包不含真题**：`build_release.bat` 的 robocopy 排除 `bank.db` / `v063_migrated.db` / `bank/assets/`，
   再把空基线 `v063.db` 复制成包内 `bank.db`（约 155 KB、0 题）。`build_plugin` 把 `.db` 后缀与 `bank/assets/`
   列入剔除，所以 `org.jiuzhang.core-bank.zip` 只剩 `schema.sql` + `plugin.json` + `dist/`，在线安装即空壳。
3. **运行期按需建空库**：`ensure_bank` 不再因缺种子报错——
   `default` 工作区有本机种子就复制、没有就退回 `schema.sql` 建空库；
   **非 default 工作区（用户新建的）一律建空库，绝不把 default 的真题复制过去**。
   工作区状态只存在本机 `data/workspaces/<id>/banks/<plugin>.db`，`data/` 整体 gitignore。

**工作区路由**：左栏顶部【当前题库 ▼】下拉列出各工作区（名 + 实时题数），切换/新建即换物理 `.db` 并整页重载，
插件与画布随之读新库。`/api/workspaces` 的 list 带 `question_count`/`is_active`，switch/create 后由
`_provision_core_bank()` 立即落地该区库。这些路由**沿用原有的本机开放设计**（localhost 单用户，
不占用一次性写令牌那套轮换经济——写令牌留给题目增删改的 `bank.create/update/delete`）。

**已知边界 / 欠账**：
- `git push` 不改历史，历史提交里的 456 `bank.db` blob 仍在 GitHub 对象库中；如需彻底抹除要改写历史 + 强推，
  那属 AGENTS §7 明令禁止的高危操作，须主公单独授权。本 ADR 保证的是**当前树与未来一切产物**不带真题。
- 真题配图资产（`bank/assets`）仍留在 operator 仓库跟踪中（本地开发读题需要），只是不进任何 zip；
  如需 GitHub 也彻底无痕，另开一令处理。

### ADR-004：A4 视口级虚拟渲染——分页是算术，不是重排（主公 2026-10-24 定调，v0.8.1 落地）

**决策**：组卷插件（`org.jiuzhang.paper-gen`）的 A4 排版改为**视口级虚拟渲染**，四条硬规则：

1. **占位与虚排**：初始化只生成 N 张固定尺寸（794×1123 按预览缩放）的**空纸**，不挂题干、不挂 KaTeX。
2. **按需物化**：只有进入视口 ±1 页（`MAX_LIVE` 上限 6 页）才把真实 DOM 挂进纸面；
   离视口 3 页以外立刻清空、退化为占位纸（骨架线由 CSS 画，不画就是一片死白）。
3. **高度缓存是唯一真相**：每题按 `题目ID + 密度 + 内容签名` 缓存一次量好的**落件高度**
   （子件到下一子件的距离 + 该子件自身墨迹外溢），分页、拆页、续页标记全部走算术，不再读布局。
4. **答案段独立量高**：答案 + 解析整体包在 `.pg-ansbox`（无外边距、`padding-top` 顶开，
   摘掉它不影响相邻子件的落位高度），隐藏态只量题干、显示态补量答案段，
   于是**切答案永远不重测题干**；整题未超页时答案段随题块走，靠
   `.pg-doc[data-ans="hide"] .pg-ansbox { display: none }` 显隐，不销毁重建节点。

**为什么**：v0.8.0 的实测账是 50 道长题带答案 = **72 页纸、约 4 倍内容量**，
旧引擎把「测量列整卷布局 → 落页 → 整卷复核」三趟全量布局串在一次点击里，
`data-t-measure-blocks 1839ms + data-t-settle 1441ms` 就是 3.58s 的全部来源。
只要还要求「同步把 72 页排完」，任何微优化都越不过 1s——**唯一解是不排看不见的页**。
主公定调的原话即本 ADR 的判据：肉眼一次只能看到 2-3 页，绝不允许浏览器在后台把 72 页全同步渲染。

**落地口径（改动集中在三处）**：
- `plugins/org.jiuzhang.paper-gen/dist/plugin.js`：`measureRecords`/`measureBoxes`（两趟独立量高）、
  `unitsFor`（按缓存高度出落件清单）、`placeQuestion`（纯算术落页，零布局读取）、
  `materialize`/`dematerialize`/`syncViewport`（挂与收）、`advance`/`ensurePages`/`scheduleIdle`（空闲补齐）、
  `completeForPrint`（打印前同步补齐 + `beforeprint` 兜底）。
- `plugin.css`：行距从 `.pg-q > .pg-line` 父选择器迁到 `.pg-line` / `.pg-line-last` 类
  （拆件落页后行会直接成为纸面子节点，父选择器一失效分页就算错）；新增 `.pg-ansbox`、
  占位纸骨架 `.pg-page[data-mat="false"] .pg-page-body`。
- `tools/paper_probe.py`：新增 `sweep_whole_doc`（**逐页滚过全卷**、每页物化后就地量溢出与公式越界，
  并清点答案段/配图）、`scrub_viewport`（6 次随机跳页，测当前页出内容的时间）、`wait_doc_ready`。

**验证口径（必须按这个来读，别拿同步段冒充全卷）**：
- `data-render-ms` = **同步段**耗时（眼前 2-3 页排完挂上），红线 **< 300ms**；
- `data-ready-ms` = 全卷后台补齐完成耗时（1.4–2.8s，期间可正常滚动，不阻塞）；
- `data-doc-ready=1` 才允许做全卷取证；`data-live` 是同时物化页数（实测 2–5，页数 75）。
- 实测（50 道长题、同一份数据、headless Chromium 1440×900）：
  首屏 926.2→**400.7ms**、切答案 3904.9→**245.8ms**、切紧凑 3450.0→**264.1ms**、切回隐藏 **9.3ms**、
  入篮 +1 重排 **1.3ms**、移除 -1 **7.8ms**；跳页最大 **181ms** 无白屏；41 项探针全绿、零 console/page error。

**已知边界（下一棒当心）**：
1. **首屏之后仍有后台补齐**：全卷 75 页在 1.4–2.8s 内陆续到位，期间页脚「共 N 页」会增长；
   这是「不阻塞交互」换来的代价，若主公要求「点一下就必须整卷定稿」，那就得回到同步全量、必然破 1s。
2. **打印/导出前强制补齐**：`completeForPrint` 会同步排完剩余页（可能几百 ms 到 2s），
   否则 PDF 缺页——这条是硬约束，不许为了指标去掉。
3. **版式缓存按内容签名失效**：签名是题干/解析/答案/选项/配图的 djb2（只扫首尾各 4K）；
   若第三方改题目却保持所有字段长度与首尾内容不变，会命中旧缓存（当前底座改题走 `bank.update`
   后必然重发 `system.question_updated` → 重载题篮，实测不会踩到）。
4. **`contain: strict` 是虚排的前提**：纸面 `overflow:hidden` + 尺寸固定，读单页 `scrollHeight`
   不会牵动整份卷子；谁把它改成 `visible`，墨迹复核就会退化成全卷回流。
5. 答案段独立量高的算术前提写在 CSS 注释里：`.pg-ansbox` 必须**无外边距**且首行间距用 `padding`，
   否则子件外边距穿出容器，「隐藏态 = 整题高 - 答案段高」就不成立。

### ADR-005：考向是并集、大纲是子集、题库可换芯（主公 2026-10-24 定调，v0.8.2 落地）

**决策**：
1. **存储层三张表管版本**：`topics` 里 `tp_kx` 考向节点是**全库并集**、`textbook_id` 必须为 NULL
   （CHECK `ck_topics_taxonomy_shared` 直接拒违规）；`tp_bo/tp_ch/tp_se` 是**版本目录节点**、带 `textbook_id`；
   跨版本归属只由 `node_topic_map(版本目录节点 → 考向)` 表达。左侧大纲树因此是**子集视图**，不是全库。
2. **一道题跨版本不复制**：题目只经 `question_topics` 指向考向；换版本不改题目、不改题-考向关联。
   苏教版接入 = 加一行 `textbooks` + 它自己的目录节点 + 指向既有考向的映射行。
3. **题库 provider 可替换**：官方 core-bank 只是默认 provider。第三方装一个声明
   `bank.provider` 能力、按 `schemas/question.json` 出参的插件即可被选为活跃题库；
   解析与回退集中在 `app/core/bank_provider.py`，`DEFAULT_PROVIDER_ID` 是全仓**唯一**出处。
4. **控制台不做成可卸载插件**（主公追认）：系统管理是底座"电源"，做成插件就有被误删变砖的一天；
   且为它单开 `system.*` 宿主中继等于给沙箱多开攻击面。因此它是**宿主自有画布页签**，
   同源内嵌设置面板，`/settings` 独立路由永久保留作防变砖兜底。

**为什么**：多版本教材是产品的长期形状——同一位老师同时教人教A版与苏教版时，
「考向」是教研资产（必须复用），「目录」才是版本资产（必须分开）。
把它们混在一张树表里，第二套大纲进来就只能复制题目。

**落地口径与教训**：
- `topics` 升级走**建新表搬数据**，不用 `ALTER ADD COLUMN`：SQLite 的 ALTER 加不上 CHECK，
  那样"新建库有不变量、迁移库没有"，一份代码面对两套结构必出错。
  契约测试 `test_06_migrated_library_is_structurally_identical_to_fresh` 逐对象比结构锁住这一点。
- 映射表**不设** `(textbook, node, sort_order)` 唯一索引：早期设过，`INSERT OR IGNORE`
  把 1780 行静默吞成 893 行（同一章下不同节的考向兄弟序相同）。
  纯关系表不该替被引用方记账；改为"期望行数对账"自检，丢一行就整事务回滚。
- 升级备份 `*.pre-v082.bak` 是 456 题整份副本，**必须**同时进 `.gitignore` 与
  `build_release.bat` 的 `/XF` 剔除清单（`test_release_script_excludes_structural_backups` 锁死）。
- 宿主 JS 注释里**不许写 `vX.Y.Z`**（版本锁测扫 `static/js/*.js`）——本会话第三次踩同一坑。

**已知边界**：大纲树尚未按所选教材版本过滤（`/api/bank/textbooks` + `POST /api/workspaces/textbook`
已就绪，前端下一棒接）；第三方**自研存储引擎**（JSON/MySQL）仍缺 provider 反向 RPC 运行时，
现在可替换的是路由与身份，不是存储引擎本身——SPEC §2.6.1 已如实写明，不假装已交付。

---

### ADR-006：双轨更新——手动出网、插件热更不碰 data、底座自更新续更（主公 2026-10-23 定调，军令 #13 任务 10 补齐运行时并真机验证）

**交付状态（2026-10-24）**：契约、端点、设置页按钮、`plugin.updated` 广播、`update.bat` 生成与重启续更均已落地；
真机证据 `tools/update_probe.py` 21/21（单条/一键热更、索引层与包内两层 `min_host_version` 拦截、题库与本地文件保全、
底座包三件套校验、开发工作树拒绝覆盖、`update.bat` 沙箱真跑、工作台控制台广播）。底座版本号仍由 `app/__init__.py`
决定（当前 0.8.2），本节标题里原先写的「v0.8.3」是规划版本号，不代表已升版。

**背景**：追加军令要求「底座定期（或手动）拉取远端清单并静默热更新插件」，与 `AGENTS.md` §2 白嫖条款、
`PLUGIN_SPEC.md` §1.1/§1.4/§1.6 的「禁止自动拉取/自动更新/批量下载」正面冲突。代理停下出具冲突表并请裁决，
主公逐条批复如下三条（以下三点是**本项目的永久规范**，已同步进 `AGENTS.md` §2 与 `PLUGIN_SPEC.md` §1.7）。

**裁决 1 · 出网时机**：只手动点击【检查更新】才出网，**绝不做后台轮询**。没有定时器、不在启动时顺手检查、
不因页面可见性变化而触发。检查成功后前端才拿到「哪些插件有新版本」。

**裁决 2 · 批量下载豁免**（逐字入律，已写进 `AGENTS.md`）：
> 底座严禁后台静默自动拉取。但允许用户手动点击【一键更新全部】按钮后，触发单次批量下载。

三个限定词都是硬边界：**手动**（任何代码路径都不得代人点，含对话工具与启动钩子）、
**一键**（一次点击 = 一次批量任务，范围就是本次检查结果里「有更新且兼容」的条目，不跨条目借源）、
**单次**（跑完即止，不排队不续跑不定时重试，失败条目如实逐条列出）。

**裁决 3 · 底座自更新 + 重启续更**：`update.bat` 方案——生成临时脚本 → 结束自身进程 → 覆盖文件（保护 `data/`）→ 重启。

**四条实现死命令**：
1. **严禁触碰 `data/`**：插件更新只解压覆盖 `plugins/<id>/` 代码目录。工作区的物理题库、插件私有数据、
   启用状态、令牌、日志都不在写范围内。唯一例外 `data/update_state.json`（续更状态，只存版本号与待办 id）。
2. **兼容校验用 `min_host_version`**：条目或本地清单声明时与底座 `app.__version__` 比对，不够则标
   「需先更新底座」、灰按钮、跳过覆盖，**绝不覆盖本地代码**。缺省视为不设限。
3. **更新经 EventBus 广播 `plugin.updated`**：载荷 `{id, from, to}`；宿主监听后刷新插件列表与左栏，
   若该插件正占画布则重载其 iframe。全程无需刷新浏览器、无需重启底座。
4. **UI 极致静默**：更新只在底部日志区逐行输出记录，不弹窗、不遮罩。

**为什么这样切**：防跑路红线防的是「云端替老师做主」，不是「老师自己想让软件变新」。把出网时机的发起权
钉死在人的点击上，批量与自更新就都不再是远程管控通道；把写范围钉死在代码目录，更新再坏也伤不到题库资产。

**已知边界（如实记录，不假装已交付）**：底座自更新的「覆盖 + 重启」这一棒在开发机上**不能真机验证**——
它会覆盖正在运行的工作树，代码里对存在 `.git` 的开发工作树直接拒绝执行。军令 #13 任务 10 已把能验的验到底：
zip 下载与校验、临时脚本内容（robocopy 排除清单逐条断言）、**`update.bat` 在一次性沙箱里真跑一遍**
（程序文件被覆盖；`data/`、`.venv/`、`.git/`、`dist/`、`__pycache__/`、`.system_generated/` 全部原样；脚本自删、暂存清理）、
状态机读写与重启续更逻辑。真实替换仍需在装好的发行包上由人手工跑一次才算最终证据。

**实测抓出的缺陷（已修）**：`robocopy /XD` 传目标绝对路径在「阶段 → 根」方向不生效，沙箱真跑时 `data/`、`.git/`、
`dist/`、`.system_generated/` 会被新包覆盖——等于把老师的题库交出去。现改为在 `/XD` 里只写目录名，两侧同时跳过；
`tests/test_plugin_update.py` 增补反向断言，禁止再回退成绝对路径。

---

### ADR-007：插件生命周期只有三态——启用 / 停用 / 卸载（主公 2026-10-23 定调，语义最终版）

**决策**：彻底摒弃任何独立的数据清理工具。「清理孤儿数据」一类的复杂逻辑**不做**——
三态本身已经覆盖全部意图，多余的工具只会给老师多造一个误删入口。

| 态 | 界面语义 | 代码 `plugins/<id>/` | `data/` | 可逆性 |
| --- | --- | --- | --- | --- |
| **启用** | 左栏有入口、可进画布 | 保留 | 保留 | —— |
| **停用** | 「暂时不用」或「侧栏太乱」 | **原地保留** | **原地保留** | 一键恢复，题目与配置零损失 |
| **卸载** | 弹窗问【保留数据】（**默认勾选**） | 删除 | 勾＝**留**；不勾＝物理销毁 | 保留数据时重装同名插件即恢复取数 |

**停用的绝对禁令（代码审查必查项）**：停用**只许**往 `data/plugin_state.json` 里增删一个 id，
**绝不允许**删除、移动、改名 `data/` 下的任何文件，也不许删插件代码目录。
现实现是 `app/core/plugin_state.set_enabled()`，它的写范围有且仅有那一个 JSON（原子写：`.json.tmp` → `replace`）；
`discover_plugins()` 只把 `enabled` 标成 `False`，卸载/清空一类动作根本不在它的调用路径上。
**审查口径**：任何给 `set_enabled` / `POST /api/plugins/{plugin_id}/enabled` 新增的副作用——尤其是出现
`shutil`、`unlink`、`rmtree` 或往 `data/` 里写空文件之类的「顺手清理」——一律视为回归，当场驳回。
`tests/test_plugin_console.py::PluginStateTest::test_disable_never_touches_code_or_data` 是这条禁令的锁。

**为什么这样切**：老师的资产是题库，不是插件代码。停用是**视图层**动作（左栏少一个入口），
卸载是**资产层**决定（要不要连库一起烧）。两者一旦混进同一个函数，就会出现
「我只是想让侧栏清爽一点，结果 456 题没了」这种不可挽回的事故。默认勾选【保留数据】
就是把最坏路径留给人主动选择，而不是让底座替人决定。

**实测纠偏（重要，别照抄措辞）**：定调时说的「数据在 `data/plugins/...`」**与实际落盘路径不符**。
现网真相是插件物理题库按 provider 口径放两处：
`data/banks/<plugin_id>.db`（根 / default 区）与 `data/workspaces/<ws_id>/banks/<plugin_id>.db`（每工作区一份），
外加 WAL/SHM/journal 边车（`_DB_SIDECAR_SUFFIXES`）。**不存在 `data/plugins/` 目录**。
卸载「彻底删除」枚举的就是上面这两族路径，且逐个 `resolve()` 后校验必须落在 `root_data_dir()` 之内（防穿越）。

**已知边界（如实记录，不为它开工具）**：
- 停用后插件的 `.db` 继续占磁盘，这是「随时可恢复」的应付代价，**不是孤儿数据**，不得被任何逻辑顺手删掉。
- 彻底删除只销毁 `banks/` 里的 `.db` 家族；插件私有资产（如 `data/uploads/` 里由它写入的图片）
  **不在**销毁范围内。这与「三态够用、不做清理工具」的定调一致——只要求界面文案不说谎：
  弹窗讲的是「物理题库」，没承诺把所有痕迹清干净。

---

### ADR-008：第三方插件模板与 AI 开发铁律（主公 2026-10-23 军令 #06）

**决策**：未来的第三方老师不手写代码、一律 AI 代写。为让 AI 一次生成不破坏底座架构的插件，
立五条【AI 开发铁律】为第三方开发契约（逐字见 `PLUGIN_SPEC.md` §2.8）：
1. **严禁点对点耦合**——插件间通信只经底座总线中转；
2. **数据读写只走宿主 API**（`bank.*` / `basket.*`）——严禁插件直连数据库/文件系统/密钥；
3. **状态同步只走事件总线广播**（`notification`，`bus.publish` 白名单内）——严禁调用其他插件函数；
4. **UI 封闭在专属沙箱 iframe**——严禁越权操作父窗口 DOM；
5. **只用原生 JS/CSS**——严禁重型框架与 CDN 资源。

**配套交付**：`examples/template-plugin/`（`plugin.json` + `dist/index.html` + `dist/plugin.js` +
`LICENSE`，注释内含宿主 API 调用与总线广播示例）；`examples/build_template_plugin.py` 产
`examples/template-plugin.zip` 供老师下载；README 新增《如何用 AI 开发九章算子插件？》——
一段可复制给任何大模型的提示词（铁律 + 封包格式 + 激活义务 + 自检三查）；
真机取证脚本 `tools/template_plugin_probe.py`。

**两处与军令字面的偏离（均为契约所迫，如实报备）**：
① 军令写模板三文件平铺，但 `validate_plugin` 铁口 `entry.frontend` 必须位于 `dist/` 下，
   且根目录必须有 `LICENSE`——照字面平铺的模板永远装不上，故落为 `dist/` 结构 + LICENSE 共四文件；
② 军令要求 `engine.host_version` 字段，但底座更新检查消费的是顶层 `min_host_version`（§1.7 裁决 2）——
   模板两者都带：`min_host_version` 是硬约束，`engine.host_version` 是「按哪版契约生成」的参照说明，
   底座对 `engine` 块不解释、不校验（§2.8）。

**验证（2026-10-23 实测，非推测）**：`test_03c_template_plugin_zip_passes_full_plugin_contract`
钉死模板 zip 过全套 `validate_plugin`；`test_03d` 钉死模板请求 id 过得了宿主入口守卫；
`test_06` 同时钉 `placeholder_plugin.zip` 与 `template-plugin.zip` 都在 `build_release.bat` 的 `/XF` 外；
全量单测 **441 测全绿**（28 个模块逐个 `.venv\Scripts\python.exe -m unittest tests.<模块>`，
系统 Python 与 `.venv` 都没装 pytest，见 `AGENTS.md` §7 修订）。真机探针
`tools/template_plugin_probe.py`（Playwright + 隔离 `JZO_DATA_DIR`/`JZO_PLUGINS_DIR`，
不碰本机 `data/`、`plugins/`）：裸装模板 **18/18**（左栏入口→画布页签→`allow-scripts` 沙箱→
`plugin.activate` 回 ready→宿主记 `plugin.mounted`→`bank.review` 当场回执→`region.dock` 经白名单
落底栏→坏 id 当场回 `BAD_REQUEST_ID` 且底栏记 `plugin.error`→宿主页零 JS 错误）；
再复制官方 `core-bank` 进隔离目录跑黄金路径 **19/19**，沙箱内实测 **「取到 10 题（共 209 题）」并渲染 10 张卡**。
**模板不进官方 `plugins.json` 索引**——它是开发起点，不是市场条目。
协作礼包由 `tools/build_dev_kit.py` 产 `dist/jiuzhang-dev-kit.zip`（81,163 B / 8 条目：指南 +
两份规范文档 + 模板源码与 zip），脚本内置红线自审：包内出现 `.env`、`*.db`、`data/`
或密钥形态字符串即自动删包并非零退出。

**探针逼出的两处契约事实（模板原写法违反，已修，见 §2.8）**：
① **请求封包 `id` 的守卫**：宿主消息入口用 `^[A-Za-z0-9_-]{1,80}$` 校验 `kind:"request"` 的 `id`。
   模板原先用 `PLUGIN_ID + "_" + seq`（带点号）→ 点演示按钮石沉大海，只能等自己 20s 超时；
   官方插件一律是 `"p"+seq+"_"+Date.now().toString(36)`，模板已对齐，并加 `test_03d` 防回归。
   **AI 生成的插件极易踩这一坑**，已写进 README 提示词与自检第三查。
   **宿主旧行为「不匹配就整体静默丢弃、既不回执也不记账」已由军令 #07 批复 2 修掉**：
   `static/js/stage.js` 现在当场回 `ok:false` + `code:"BAD_REQUEST_ID"` 的同 id 回执，
   并向底栏「输出日志区」记一笔 `plugin.error`（带插件名与正确形状），开发者不再抓瞎。
② **`bank.*` 是三类通道**：`bank.list` / `bank.stats` / `bank.random` 按**页签自己的 plugin.id**
   读插件**自带**的库（要随包放 `bank/schema.sql`），公共真题库走 `bank.get` / `bank.review` /
   `bank.topics` / `bank.create`（活跃 provider），`basket.*` 是工作区题篮、与具体哪个库无关。
   模板演示原先调 `bank.list`，裸装时必然报「缺少表结构定义」，已改成 `bank.review`。
   契约本身 §2.6 早已写清，是模板没照做。

**同步落地的规范修订（军令 #07 批复 1）**：`AGENTS.md` §7 原写 `python -m pytest tests/`，
与本机实况冲突（系统 Python 与 `.venv` 都没装 pytest，`STACK.md` §6 也明令不引入 pytest 依赖），
已整段改为 unittest 口径：单模块 `.venv\Scripts\python.exe -m unittest tests.<模块>`、
全量用 cmd 的 `for /f` 逐模块循环，并点名 `unittest discover` 因 `tests/` 无 `__init__.py` 会直接报错、
必须用 `.venv` 解释器（系统 Python 缺依赖会把所有模块打成假报错）。

### ADR-009：AI 助手降格为普通插件——权限只有 API 一条路（主公 2026-10-24 军令 #15 定调）

**决策**：右侧对话框不再是底座的一部分，它是一只普通 UI 插件
[`org.jiuzhang.chat`](plugins/org.jiuzhang.chat/plugin.json)（`slots: ["sidebar.right"]`，
`capabilities: ["assistant.chat"]`，`permissions: ["ai:invoke"]`），与画布上的插件**众生平等**。
本决策**声明取代 ADR-002 第 4 条**：AI 副驾不住在底座托管的右栏里，它自己就是右栏的住户。

1. **AI 没有任何底层特权**：读题数、开插件、装插件、改面板参数，一律只能发标准 Host API 请求，
   由底座 `relayAgent()` 代为执行；助手插件里 `fetch` / `XMLHttpRequest` / `parent.document` /
   `window.localStorage` 命中数必须为 0（契约测试 `tests/test_ai_plugin_boundary.py` 钉死）。
2. **AI 没有手**：不得模拟鼠标、键盘或系统事件，`trigger_button` 通道从后端提示词、Host API 白名单、
   插件三侧同时绝迹。面板按钮只属于人：人点按钮 → 宿主广播 `panel.button.click` → 助手以
   `origin:"panel_button"` 自己发这一轮；AI 反向只能请求 `ui.params.set` 设值。
3. **智能跳转代替越权操作**：统计/检索类结果由后端装配成 `data.actions`（白名单 `open_bank`/`open_editor`，
   去重后 ≤3 条），助手渲染成气泡下方按钮；老师点击后底座开页签并把检索词以 `system.bank_query`
   通知送达，题库插件自己回填搜索态重查。
4. **右栏主权跟着画布走**：右栏默认不折叠、默认住户是助手；只有**当前画布页签**所属插件声明了
   `sidebar.right` 才暂时接管，切走即 `reclaim()` 归还；无认领者时显示可读兜底，不隐藏、不白屏。
5. **左栏不再有硬编码「自由对话」入口**：找插件、找题目全部通过右栏助手下达；中栏兜底是底座自己的
   原生「引导」页签（不可关闭），示例提示语也交给助手现场查清单后再说——**插件被删了底座不许替它说谎**。

**为什么**：AI 住在宿主壳里时，它天然能碰宿主 DOM、天然能读全局变量，铁律二（插件不得直接访问数据库、
文件系统、模型密钥）对它形同虚设；「AI 说一句话就能改面板、开页签、装插件」一旦实现成宿主代点击，
等于给模型装上手，权限边界全靠自觉。把它降格成插件后，**特权问题变成白名单问题**：它要的每一条能力
都必须出现在 `AI_ONLY_METHODS` 里、都必须带 `ai:invoke` 授权、都可被 grep 与测试机械取证。
顺带把「AI 占着中栏最好的位置」这一体验债清掉——中栏还给插件与老师的作品，右栏才是助手的落脚点。

**协议落点**：`static/js/stage.js` 的 `AI_ONLY_METHODS` 扩至
`agent.chat` / `agent.refine` / `plugin.install_url` / `ui.params.set` / `editor.apply_patch` /
`stage.open_bank` / `stage.open_editor`；`app/core/plugins.py` 白名单加 `assistant.chat` 能力、
`ai:invoke` 权限与 `stage.selection` / `panel.button.click` 总线订阅；`PLUGIN_SPEC.md` §2.9 重写主权交替、
新增 §2.10 助手插件边界。

**已知边界**：宿主壳 `static/workspace.html` 仍挂着 KaTeX 的 `<link>`/`<script>`（宿主 JS 已零引用，
摘除牵动 PWA 预缓存清单，本轮不动）；助手插件尚未进官方 `plugins.json` 索引，误删后只能靠发版包带回。


## 四、强制待办清单

### 一、当前冲刺（P0 级）

- [x] **官方插件索引漂移（军令 #14 追加，2026-10-24）**：根 `plugins.json` 与 `E:\jiuzhang-plugins\plugins.json`
      原先非逐字节相同，且都把 `org.jiuzhang.editor` 标成 0.3.0——**而已发布的 editor zip 也才是 0.3.0**
      （本地插件目录早就是 0.4.0，发布件没跟上）。
      **修法顺序不能反**：先用 `tools/build_plugin.py` 重建 0.4.0 包覆盖插件仓库的发布件，
      再跑 `tools/sync_plugin_index.py` 校准索引；只改索引会让索引宣称 0.4.0 而用户下载到 0.3.0，比漂移更坏。
      现在两份索引**逐字节相同**（sha256 前 12 位 `3e4d1faa423d`）、`updated_at` 2026-10-24，
      5 个条目的索引版本与已发布 zip 实际版本**逐一相符（0 漂移）**。
      顺手修了 `tools/sync_plugin_index.py` 里写死的 `updated_at: "2026-10-23"`（改为跟随当天日期）。
- [x] **v0.8.2 的三条控制台欠账（阶段二 `7c02c5b` 已清缴，别再当活账）**：
      ① 控制台「左树右二级菜单」——`static/settings.html` 左侧 4 个 nav（工作区/插件/模型配置/系统设置）+
      插件区右侧 4 个二级页签（管理/更新/索引/安装），键盘可切且保留深链；
      ② 顶栏 Provider 配置弹窗——模型胶囊与弹窗节点彻底退役，模型配置只留控制台「模型配置」面板一份
      （`workspace.js`/`workspace.html` 已搜不到 `openProviderModal`/`wsModelBtn`）；
      ③ 大纲树按教材版本过滤——`GET /api/bank/plugins/{id}/topics` 支持 `textbook_id` 并默认取
      `workspace_api.active_textbook_id`，设置页可登记版本（`POST /api/workspaces/textbook`），
      改活跃工作区会刷新宿主让大纲树重建，契约测试 `tests/test_workspace_textbook_scope.py` 3 测。
      **注意**：v0.9.0 晨报初稿曾把这三条误列为「仍在」，已公开更正——下次别照抄旧结论，先读代码。
- [ ] **未在真实安装目录由人手点过「更新并重启」**（2026-10-24 登记）：沙箱安装副本上已真跑全流程
      （真下载 → 真自杀 → 真覆盖 → 真重启到 v99.0.0，`data/` 与本地插件逐字节未变，探针 25/25），
      但真实安装目录的**人点按钮**路径未经人手验证——按下会结束当前进程，只能由人亲手做。
      下一步建议：拿 `dist/jiuzhang-operator-beta-v0.9.0.zip` 解压到独立目录，进去点一次【更新并重启】，
      确认覆盖的是程序文件、`data/` 与 `plugins/` 原地不动、重启后版本号正确。
- [x] **军令 #14 六阶段闭环与 v0.9.0 封版**（2026-10-24 彻夜）：解析器/FTS5 接进插件 UI → 清缴控制台与启动项欠账 →
      A4 试卷与讲义 PDF 导出 → 题库批量导入与导出 → 真机自更新全流程压测 → 升版出包统一推送。
      底座 **0.8.2 → 0.9.0**，`dist/jiuzhang-operator-beta-v0.9.0.zip` 已出；全量 42 模块 **809 测全绿**；
      真机自更新探针 **25/25**（钉死 `update.bat` 三类真机根因：`find` 被 Git Bash 抢占 / 无控制台 `timeout` 不可靠 /
      无控制台 `echo` 写控制台会让整篇批处理终止）。详见 §二 顶部与 `Morning_Report.md`。
- [x] **军令 #13 十一项**（2026-10-24 彻夜）：启动行为 / 侧栏与底栏 / 右栏插槽 / 录题解析 / FTS5 / 组卷 / 讲义 /
      题库浏览 / 框选切图 / 双轨更新 / 瘦身晨报，逐项 commit；全量 749 测绿、更新探针 21/21、样式回归 13/13。
      该轮**未**升版未出包，已由军令 #14 的 v0.9.0 封版补齐，详见 `Morning_Report.md` 与 §二 顶部。
- [x] **API 切表**（2026-10-23 完成）：后端 API 全部从旧宽表 `bank_questions` 切换到新的 7 张关系表。
      读路径 `list_questions` / `get_question` / `stats` / `random_question` / `get_many` 已重写，
      新增 `topics`（懒展开 + 子树题量）与 `topic_notes`；写路径 `create_question` 与 `import_documents`
      把对象态 `extensions` 落成数组态，并按 `taxonomy.topic_ids` 写 `question_topics`、
      按 `source` upsert `schools`/`sources`/`question_sources`；`app/api/bank.py` 加了
      `/topics`、`/topics/{id}/notes` 与 `topic=` 筛选，`stage.js` 白名单加 `bank.topics`/`bank.topic_notes`。
      真机 HTTP 已验：stats 456 / 大纲四层 / 按考向子树取题 / L4+高一 129 题 / 旧值 hard→L3 / 中文搜索。
      **剩余**：插件侧未接新通道（P0#2），种子库 `bank/bank.db` 仍是旧宽表（P0#4 封版必须换）。
- [x] **前端联动适配**（2026-10-23 完成）：core-bank 画布左栏新增**大纲树**，走 `bank.topics` 按
      `parent_id` + `sort_order` 懒展开（册→章→节→考向），每个节点带子树题量 / 笔记数 / 待补录标记，
      点节点即按子树筛题（真机验证：点「1.1 集合的概念」得 23 题，与后端逐字一致）；
      插件读路径全部改吃新出参（`grade` 顶层、`taxonomy` 来自路径树、`answer` 合成对象、
      `extensions` 对象态）。难度口径：core-bank `plugin.json` 的 `ui.controls`、editor 下拉、
      classic-card / paper-gen / demo 种子与 workspace.js + workspace.css 全部改 L1–L4，
      中文标签按契约 2.0 = **基础 / 中档 / 难 / 压轴**（旧值 basic/medium/hard/novel 只做渲染兜底）。
      **注意一处与军令字面口径的偏离**：发令写的是「基础/中档/压轴/新定义」，但上一道裁决已「彻底废弃
      novel」，且 L4 在数据里是 140 道压轴题——把 L4 标成「新定义」会给最难的一档贴错标签，
      故按已批准的契约 2.0 落地；如主公坚持「新定义」字样，改 `contract.py` 的 `DIFFICULTY_LABELS` 一处即可。
- [x] **人工审核页**（2026-10-23 完成，v0.6.4）：core-bank 画布顶部新增「待审任务」页签（带角标），
      左列按标记筛（全部待审 / 七类标记各自计数），右列逐题给三种修法——
      选择题**点选项字母补答案**、非选择题**填正文补答案**、**改题型**（拆不出选项的改判解答），
      外加「确认无误，只清标记」；保存走 `bank.update` → `PATCH /api/bank/plugins/{id}/questions/{qid}`
      （写令牌留宿主侧，插件必须声明 `questions:write`），清完最后一个标记时**整个迁移条目移出库**，
      不留空壳。现网真队列实测 **209 题**：needs_conclusion 142 · topic_unmapped 26 ·
      solution_absent 22 · answer_absent 18 · answer_region_empty 9 · type_manual_review 4 ·
      structure_conflict 2（合计 223 > 209，因部分题带两个标记）。
      真机闭环在**隔离数据副本**上验过一次（点 C 保存 → 库里 `answer='C'`、迁移条目消失、
      队列 209→208），主公的现网库**未被写入**、副本已删。
      后端为此补了 `bank.update_question`（合并补丁→契约校验→回写→回读）与 `bank.review_summary`；
      改题型时选择题的字母答案会转成 `text` 正文（保事实，不因 kind 约束整条改不动）。
      **仍未做**：`topic_unmapped` 的「挂到哪个考向」不能在审核页里选（要接大纲树选节点），
      这 26 题目前只能「只清标记」或留给录题插件的改题功能。
- [~] **真机压测 + 封版**（2026-10-23 出包，压测口径未全）：
      已做——版本单源升 `0.6.3` + 前端兜底文案同步（版本锁 12 测绿）；core-bank 种子库
      `bank/bank.db` **换成新结构 456 题**（旧宽表种子已废弃，读它会被结构守卫拒掉）；
      插件重出 `org.jiuzhang.core-bank.zip` 0.2.0（1,183,766 B）、`editor` 0.1.1、`paper-gen` 0.1.1
      并落 `E:\jiuzhang-plugins\plugins\`；两份 `plugins.json` 用 `tools/sync_plugin_index.py`
      逐字全等（6 条索引）；`build_release.bat` 出 `dist/jiuzhang-operator-beta-v0.6.3.zip`
      **1,791,623 B / 242 条目 / 0 夹带 / 0 缺失**，包内种子库经解包实测是 7 表 + 456 题 + L1–L4，
      包内契约是 2.0。发放包自 v0.6 起**不入库**（`git ls-files dist` 只到 v0.5.2）。
      未做——`tools/bank_stress.py` 与 `tools/paper_probe.py` 仍直读旧宽表（切表后未跟改，
      跑真机压测前必须先修）；组卷 / 讲义两条链在新表上的回归未跑；
      桌面三栏布局的截图未取到（应用内 Browser 面板的截图面被宿主隐藏，只拿到窄屏两张）。
      人工审核页（上一条 P0）仍未开工。

### 二、核心业务闭环（P1 级）

- [x] **双轨静默更新（军令 #13 任务 10 补齐运行时并真机验证）**：完成底座自更新与插件热更新两轨——
      ① 底座 `update.bat` 方案：临时脚本 → 结束自身 → robocopy 覆盖程序文件并**保护 `data/`**（排除
      `.venv .git dist __pycache__ .system_generated`）→ 重启 → 读 `data/update_state.json` 接着补更插件；
      ② 插件热更新：`app/core/plugin_update.py`（semver 比较 + 串行 apply，只覆盖 `plugins/<id>/` 代码目录）；
      ③ **严格的版本兼容性拦截**：条目/清单的 `min_host_version` 与底座 `__version__` 比对，
      不够则标「需先更新底座」、灰按钮、**绝不覆盖本地代码**；
      ④ 五个端点（check / apply / pending / pending-clear / host-apply，全带写令牌）；
      ⑤ 设置页插件面板：【检查更新】【一键更新全部插件】、红色【更新】、底部日志区静默输出。
      **真机证据**：`tools/update_probe.py` 21/21（含 `update.bat` 沙箱真跑与工作台控制台广播）；
      同次实测抓出并修掉 `/XD` 绝对路径不保护 `data/` 的缺陷（改为只写目录名）。
      **出网铁律**：只有用户当场点击才发请求，严禁后台轮询（裁决 1）；批量下载只在
      【一键更新全部】这一次点击里发生（裁决 2）。详见 ADR-006。
- [x] **录题插件升级**：v0.7.0 补「修改」（接 `system.open_editor` 全量回填、按钮【保存并返回】、走
      `bank.update`，新增**考向大纲树选择器**，挂真考向自动清 `topic_unmapped`）；v0.7.1 再补
      **删除题目**（【删除本题】二次确认 → `bank.delete` 带令牌、级联摘关联保留共享节点）与
      **选项 `image_ids` 回填/保存链路**（改题干不洗配图，`images` 数组整体保留）。
      **仍缺**：编辑态下的多来源（一题挂多张试卷、原卷题号随行）——选项配图是回填保留、非在表单内新增上传。
- [ ] **考向笔记渲染**：前端需把 `topic_notes` 里那 150 条方法/易错点，在题目详情或考向树侧边展示出来。
- [ ] **A4 排版引擎联动**：确保组卷插件（paper-gen）和讲义插件（handout）能完美读取新表生成 A4 试卷；
      两者当前仍按旧 `bank.*` 出参结构取数，切表后必须回归压测。
- [ ] **P1 重排欠账**（v0.6.2 已登记）：切换答案/紧凑重排的既有性能与体验欠账，与下面 P2 第一条同源。

### 三、性能与体验（P2 级）

- [ ] **底栏神级交互：报错日志「双击静默复制」**（尚未开工，ARCHITECTURE_SPEC 里作为规格目标写明）：
      悬停时才浮现复制提示、双击后**原位**闪一下绿底变成「已复制」、**严禁弹 Toast**、
      不选中文本、不抢焦点。复制走 `navigator.clipboard` 并在 http/无权限时回落 `execCommand`。
- [ ] **解决 3.58s 性能欠账**：针对切换答案/紧凑重排耗时 3.5 秒的问题，引入「虚拟列表」或「分页按需渲染」。
- [ ] **AI 辅助升级**：打通 OCR 乱码整理接口，让 AI 帮老师一键清洗脏 LaTeX 数据
      （A4 组卷链已有脏 LaTeX 归一经验，可复用同一归一器，勿再造第二套）。
- [ ] **图片资产收口**：迁移报告记「引用 52 张、缺 13 张」，新库 `extensions.images` 沿用同一批
      `/static/uploads/` URI；切表时需一并核验种子包 `bank/assets` 与工作区 `uploads` 的落位一致。

### 四、生态与扩张（P3 级）

- [ ] **终端桌面客户端（PyWebView 封装）**：UI 定型后把底座包成桌面客户端——**无地址栏**、
      绿色免安装 zip（解压即用），解决「小白老师没有 Python 环境」的痛点。
      待议：内嵌解释器与 `data/` 落位（不得写进安装目录，Program Files 需要管理员权限）、
      窗口尺寸与四区几何的映射、以及是否沿用同一份 `update.bat` 自更新通道。
- [ ] **跨学科插件测试**：用现有底座跑通一个极简的「物理」或「化学」伪题库插件，
      验证四字段独立设计（题干 / 选项 / 答案 / 解析）的普适性。
- [ ] **插件市场完善**：打通在线安装、版本更新、依赖检查等全流程——在线安装与更新检测已入律，
      剩下的「依赖检查」按铁律 5 的新口径做（2026-10-23 裁决已把「禁止批量拉取」改为
      「允许用户手动点击【一键更新全部】后触发单次批量下载」，仍严禁后台自动拉取）。
- [ ] **`schemas/question.json` 与存储层对齐**：决定 `extensions` 是继续「库内数组 / 契约对象」双态，
      还是升 `schema_version` 统一为有序数组（破坏性变更需升主版本 + 迁移说明 + 校验测试）。

---

## 五、标准军令模板

### 5.1 下行 · 全新军令

> **第一行只写标题**（平台标题抓取规则所致，见 §5.4）：第一行必须是我们想要的对话标题本身，
> 干净、≤16 字符、不带编号与前缀标签；编号、时间等元信息一律放到第二行之后。

```
（这里只写标题本身，如：v0.8.4 双轨静默更新）

【军令编号】 #XX
【全新军令】 （同上标题）
【发令时间】 YYYY-MM-DD HH:MM:SS+08:00
【建议模型】 xxx
【思考强度】 xxx
【预计时间】 约 XX 分钟（请分步执行，严禁一次性跨文件乱写）

【第一步】…
【第二步】…

（做完一步再做下一步，严禁跳步。军令完毕，即刻执行！）
```

### 5.2 下行 · 追加军令

```
（这里只写标题本身，如：v0.8.4 待办归档）

【军令编号】 #XX
【追加军令】 （同上标题）
【发令时间】 YYYY-MM-DD HH:MM:SS+08:00
【建议模型】 xxx
【思考强度】 xxx
【预计时间】 约 XX 分钟（请分步执行，严禁一次性跨文件乱写）

【任务 1】…
【任务 2】…

（军令完毕，即刻执行！）
```

### 5.3 上行 · 回执抬头（代理必用，四项缺一不可）

```
【回执编号】 #XX
【回执时间】 YYYY-MM-DD HH:MM:SS+08:00
【实际耗时】 XX 分 XX 秒
【执行结果】 成功 / 部分成功 / 失败

正文：逐条对齐军令的任务号，写清「做了什么、验证到什么、没验证什么」；
     欠账、偏离与失败项主动披露，不用推测代替证据。
```

### 5.4 平台侧「对话标题」抓取规则（2026-10-23 实测 19 条历史会话取证）

**一句话规则：标题第一行就是我们想要标题本身——干净、≤16 字符、不带编号与日期，因为 Qoder
的标题默认由模型语义摘要生成（19 条里 15 条如此），只在摘要没跑成时回落成首条消息的原文前缀。**

实测证据（本机 `.qoder/projects/E--jiuzhang-operator/*.jsonl` 逐条与
`list_chat_sessions` 返回的 title 对照，探针 `.system_generated/title_rule_probe.py`）：

| 路径 | 占比 | 现象 | 例 |
| --- | --- | --- | --- |
| 模型语义摘要 | 15/19 | 标题在原文里**找不到逐字对应**，是概括 | 首行「【军令】2026-10-24 ｜ 子龙」→ 标题「A4渲染性能优化」 |
| 原文前缀回落 | 4/19 | 标题就是首条消息的前 N 个字符**逐字照抄** | 「【军令】2026-10-23 ｜ 子龙」（19 字整首行）；另一条照抄到第 77 字符、**连换行都保留** |

由此得出三条可执行结论：

1. **首行必须就是目标标题**，前后不要挂 `【军令编号】`、日期、署名——回落路径会把这些一起照抄进侧栏
   （本项目旧会话「【军令】2026-10-22 ｜ 子龙\n标题：彻夜全栈…」就是活教训：侧栏里换行都还在）。
2. **摘要路径不受我们控制**，所以「完美显示」无法靠格式 100% 保证；但首行短、纯、独立时，
   模型大概率直接沿用它——回落路径则是**逐字**采用。把标题写成第一行是当前唯一有效的抓手。
3. **未取证的部分如实说明**：本代理没有改名类工具，Qoder Desktop 侧栏是否支持手动重命名会话**未验证**；
   标题长度实测到 19 字符仍完整显示、未见截断，但会话元数据落盘是加密的
   （`<sessionId>/state.json` 的 `items.*.p` 为密文），所以平台侧的上限与算法只能靠行为观测，读不到源码。
   若主公在界面上发现改名入口，补一句进本节即可。

发令写法已按本规则改到 §5.1 / §5.2：**第一行只写标题，第二行空行，再写编号与元信息。**

### 5.5 时间与标题的硬约束

1. **时间一律取真实系统本地时间**：执行任务、更新本文件「最后更新」、填写回执【发令/回执时间】时，
   必须先跑一次 `date "+%Y-%m-%d %H:%M:%S+08:00"` 取数。**严禁照抄抬头里的时间、严禁瞎猜。**
   格式统一为 `YYYY-MM-DD HH:MM:SS+08:00`（北京时间）。
2. **耗时用实测**：【实际耗时】按开工与收尾两次真实时间相减，不得估算。
3. **标题 ≤16 字符**（2026-10-21 拍板的长期铁律）；用户自己写超了只提醒、不代改。
4. **冲突先停**：代理发现军令与 `AGENTS.md` 铁律冲突，必须先停下报告冲突与实测证据、请主公裁决，
   不得静默绕过，也不得擅自扩大改动面。

### 5.6 上行 · 机械证据回传单（军令 #12 锁死，2026-10-23 起长期生效）

主线工作流固化为三段闭环：**军令任务卡（下行）→ 机械证据回传单（上行）→ 云端复审**。
回执抬头仍按 §5.3 四项写，正文**必须**换成下面这张单子——**严禁只写「全绿」「已完成」**，
每一项都要能被主公或复审代理照着重跑一遍。证据一律用实测输出（命令 + 数字 + 路径），
测不到就写「未验证」，不许用推测填坑。

```
【改动清单】
- 新增：<路径> ×N（逐个点名，一句话说明它是什么）
- 修改：<路径>:<行号或函数> —— 改了什么、为什么
- 删除：<路径> —— 为什么可以删（零引用证据）
- 禁改区自查：LICENSE / AGENTS.md 铁律一二 / schemas 破坏性变更 / data 目录 —— 是否触碰（是/否 + 依据）

【包结构自检】（涉及插件才填，不涉及就写「本次不涉及插件」）
- 顶层目录名 == plugin.json 的 id？
- 有无 backend 字段（底座不支持，必须为空/不存在）？
- 有无 Apache-2.0 LICENSE 全文？
- min_host_version / engine.host_version 与当前 app.__version__ 的关系？

【三查结果】（grep 实测，逐条给命令与命中数）
- `fetch(` 命中 0？（插件必须走 postMessage，不许自己发 HTTP）
- `parent.document` 命中 0？（沙箱不透明源，摸不到宿主 DOM）
- `localStorage` 命中 0？（插件禁碰浏览器存储）
- 请求 id 是否全部符合 `^[A-Za-z0-9_-]{1,80}$` 且**不含点号**？（含点号必被 BAD_REQUEST_ID 拒）

【测试与探针】
- 单测：跑了哪些模块（逐个点名）、各自 N/N 绿、总用例数；解释器必须是 `.venv/Scripts/python.exe`
- 真机探针：跑没跑、哪个脚本、判据 passed/total、截图落在哪个目录（绝对路径）
- 前端改动：是否在浏览器里真人路径走过一遍（AGENTS §7），走过写清看到了什么

【未决问题与偏离】
- 欠账：没做完的、下次接着干的（写清阻塞原因）
- 偏离：与军令字面或 PLUGIN_SPEC / AGENTS 契约不一致的地方 + 我的处理与理由
- 解释性口径：军令用词有歧义时我采的口径（如「已落库总数 = 总数 − 待审核」）
- 未验证：环境或工具限制导致测不到的部分，直说
```

**执行侧配套铁律**（与 §7 提交口径合流）：

1. 每完成一个【大阶段】立即 `git commit`，提交信息标注阶段（如 `feat(api): #11 第一阶段看板API与接口文档`）；
   **测试不绿绝不许 commit**；多阶段军令严禁一口气写完再提交，全部干完后统一 `git push`（需军令明确授权）。
2. 回传单里的每个数字都必须来自当次实测输出（探针 `probe.json`、unittest 汇总行），
   不许沿用上一轮的数字；引用旧证据必须注明是哪一轮。
3. 探针产物（截图、`probe.json`）落在 `.system_generated/` 下，**不进 git**，但路径要写进回传单备查。

---

## 六、环境与工具备忘（省下次会话的摸索时间）

- 解释器：`.venv/Scripts/python.exe`（Python 3.14）。**venv 里没有 pytest**，跑测试一律
  `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*.py"`（`AGENTS.md` 写的
  `python -m pytest` 在本机跑不通）。
- SQLite 3.50：JSON 函数可用（`json_valid` / `json_type` / `json_array_length`）；
  **`ON DELETE SET DEFAULT` 能建表但运行时照样违反外键**，`AUTOINCREMENT` 只能写在列级
  `INTEGER PRIMARY KEY AUTOINCREMENT`；`GLOB` 不支持 `{n}` 量词。
- 本机控制台是 cp936：Python 直接 print 中文会乱码，结果一律写 UTF-8 文件再读；
  中文不要走 argv。正则类原型必须用 Write 落成文件再跑，heredoc 会把 `\\` 折叠成 `\` 产出假阴性。
- 旧库快照：`.scratch-recon-063/legacy.db`（只读复制，含 WAL），现网旧库
  `data/banks/org.jiuzhang.core-bank.db`；两者都不是交付物，`.scratch-recon-063/` 不入 git。
- **接力坑**：`tools/migrate_bank_v063.py` 依赖 `.scratch-recon-063/legacy.db` 与旧项目的
  `schools.json` / `curriculums/A.json`，而该目录已被 `.gitignore` 排除（含第三方数据副本，
  依铁律一不入库）。新会话要重跑灌库，必须先从 `E:\math-question-bank-main\math_question_bank.db`
  **连同 `-wal` 一起**复制出快照（只复制主文件会读到过期数据），复制后先核 `COUNT(*)=456` 再跑。
- **切表轮新增的环境坑（2026-10-23）**：
  ① 底座库 `app/core/db.py` 的 `SCHEMA_VERSION` 已是 **2**，首次打开 v1 库会走「备份
  `jiuzhang.db.pre-v2.bak` → 重建 questions → 难度改值」的迁移；改这个文件的 DDL 必须同步加迁移分支。
  ② `app/core/bank.py` 建库只认 `plugins/<id>/bank/schema.sql`（不再有内嵌 DDL）——
  测试沙箱必须在临时 plugins 目录里放一份 schema.sql，否则 `init_bank` 直接 `BankNotFound`。
  ③ `tests/test_bank_api.py` 里凡是往夹具写题的用例一律取 `test_z*` 前缀（字母序最后跑），
  否则会污染 `test_stats_counts` / `test_sql_injection` 的 120 题硬断言。
  ④ 改 `examples/demo_plugin/seed/questions.json` 或其 `dist/plugin.js` 后**必须重跑**
  `examples/build_demo_plugin.py`，`examples/demo_plugin.zip` 是入库产物、不会自动跟随源目录。
  ⑤ 清理测试遗留服务时**禁止** `taskkill /F /IM python.exe`（会连坐本机其他 python 进程），
  必须记下自己起的 PID 再逐个终止。
  ⑥ `settings.plugins_dir` 是**导入期一次性求值**的类属性（`JZO_PLUGINS_DIR` 只在进程启动前有效），
  而 `settings.data_dir` 每次调用重读 `JZO_DATA_DIR`——所以进程内改环境变量只能换数据目录，
  换插件目录必须走子进程；写「换种子库」类测试要直接铺 `data/banks/<id>.db` 文件。
  ⑦ 真机验证插件 UI 时，宿主舞台的 iframe 是 `sandbox="allow-scripts"`（无 allow-same-origin），
  顶层脚本读不到它的 DOM、a11y 快照也进不去；要驱动真实 `plugin.js` 就在工作台页里挂一个
  **同源无沙箱**的 iframe + 手写 `jzo-plugin/1` 宿主仿真（把 `bank.*` 转发到真实 HTTP 接口），
  本次大纲树的展开/筛题证据就是这么取的。产品行为仍以真实沙箱舞台为准。
  ⑧ `build_release.bat` 自 v0.6.3 起额外排除 `.scratch*`（内含旧项目库的只读副本，铁律一禁止外发）
  与 `bank/v063.db`、`bank/v063_migrated.db`（结构基线与灌库中间产物，运行时只读 `bank.db`）；
  改打包白名单前先跑一次包体审计，别把 1.7 MB 重复库放出去。
  ⑨ **题目 ID 只能用十六进制**：存储层 CHECK 是 `id GLOB 'q_[A-Za-z0-9]*'`，
  而契约允许 `q_[A-Za-z0-9_-]{8,64}`——`secrets.token_urlsafe()` 会吐 `-`/`_`，撞上 CHECK 后
  被 `IntegrityError` 分支误报成「题目 ID 已存在」的 409，是**随机复现的假故障**
  （v0.6.4 审 `q_-t1MhFqK…` 时抓到）。`app/core/questions.py:_new_id` 已改 `token_hex(12)`；
  以后想换 ID 生成式，必须同时过契约与这条 GLOB。
- **Windows 批处理三大坑（2026-10-24 阶段五实测钉死，改 `update.bat` 前先看这段）**：
  ① **PATH 抢占**：Git Bash 的 `C:\Program Files\Git\usr\bin\find.exe` 排在 System32 前面，
  `tasklist | find "..."` 会让整篇批处理当场终止（底座永不重启、覆盖也没发生）；
  一律用绝对路径 + `for /f "usebackq tokens=2 delims=," %%p in (`"..." tasklist.exe" /FI "PID eq %JZO_PID%" /NH /FO CSV`)`
  读 CSV 再比对 `%%~p`（`usebackq`+反引号下 `2^>nul` 会被当成字面参数传给 tasklist，**不能加**）。
  ② **无控制台不可靠**：DETACHED_PROCESS 里 `timeout` 会失灵，睡眠改 `"%SystemRoot%\System32\ping.exe" -n 2 127.0.0.1 >nul`。
  ③ **无控制台时 `echo` 会中止整篇批处理**：cmd 往控制台写失败即 rc=1 终止（连纯 ASCII 行也照样死），
  所以拉起脚本时 `stdout=日志文件、stderr=STDOUT、stdin=DEVNULL`，cmd 的输出必须落文件。
  ④ `.bat` 文件用 **ANSI 码页**（`locale` 的 `mbcs`，本机 cp936）写盘，UTF-8 里的中文会被 cp936 误解出
  引号与管道符，足以让脚本语法崩掉；用 `Path.write_bytes` 落盘，`Path.write_text` 的 newline 转换会把
  已是 CRLF 的脚本变成 `\r\r\n`。
  ⑤ cmd 的 `/c` 引号剥离：命令行以引号开头时 cmd 剥掉首个与末个引号，需要 `""script" > "log" 2>&1"` 的双引号写法；
  路径无空格时干脆不加引号最稳。cmd 读 `.bat` 用 ANSI，但**无控制台时 cmd 的输出是 UTF-8**（实测日志字节 `e7 ad 89` = 等待）。

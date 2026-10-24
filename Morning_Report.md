# Morning Report · 军令 #14「彻夜六阶段闭环与 v0.9.0 封版攻坚」

日期：2026-10-24（Asia/Shanghai）
执行方式：六阶段严格按序，每阶段一个 commit；测试不绿绝不许 commit。
版本状态：**0.8.2 → 0.9.0 已升版**，`dist/jiuzhang-operator-beta-v0.9.0.zip` 已出（**1,959,225 B / 266 条目**），已统一 `git push`。

---

## 一、六阶段完成

| 阶段 | 交付 | 提交 | 关键证据 |
|---|---|---|---|
| 一 | 解析器与 FTS5 接进插件 UI | `8ff3c17` | 单测绿（`test_question_parser` 40、`test_bank_multiversion` 等） |
| 二 | 清缴遗留控制台与启动项欠账 | `7c02c5b` | 控制台二级页签契约测试绿 |
| 三 | A4 试卷与讲义的 PDF 导出 | `aa170ac` | 组卷/讲义插件单测绿 |
| 四 | 题库批量导入与导出 | `dd8613d` | `test_bank_api` / `test_bank_multiversion` 绿 |
| 五 | 真机压测自更新全流程 | `1ac1224` | **真机探针 25/25**；全量 809 测绿 |
| 六 | 升版 0.9.0、清 `dist/`、出包、统一推送 | 本次 commit | 包审计 0 夹带 / 0 缺失；全量 **42 模块 809 测全绿** |

追加指令（官方 QQ 群）单独成 commit：`1885605 docs: 收录官方交流群信息与二维码`。

---

## 二、阶段五纪要：自更新为什么在真机上一直不工作

不是推断，是沙箱真跑一步步钉死的三类根因。三个都写成了自动化断言（`tests/test_plugin_update.py`，本模块 **111 测全绿**）：

1. **`tasklist | find` 被 PATH 抢占**：Git Bash 的 `C:\Program Files\Git\usr\bin\find.exe` 排在 System32 前面，
   那一行让整篇批处理当场终止——底座永不重启，覆盖也没发生。
   改用 `for /f "usebackq tokens=2 delims=," %%p in (...)` 读 tasklist 的 CSV 输出，`tasklist`/`ping` 一律写绝对路径。
2. **无控制台下 `timeout` 不可靠**：DETACHED_PROCESS 里睡眠改成 `ping -n 2 127.0.0.1`。
3. **无控制台时 cmd 的 `echo` 写控制台会失败，整篇批处理停在第一行**（连纯 ASCII 行也照样死）。
   拉起脚本时 `stdout=日志文件`、`stderr=STDOUT`、`stdin=DEVNULL`；cmd 的输出必须落文件。

另外两处按 Windows 实际行为改的：

- `.bat` 按控制台 **ANSI 码页**（mbcs，本机 cp936）落盘。UTF-8 里的中文会被 cp936 误解出引号与管道符，足以让脚本语法崩掉。
- 用 `Path.write_bytes` 落盘。`Path.write_text` 的 newline 转换会把已是 CRLF 的脚本变成 `\r\r\n`，cmd 会把多出来的 `\r` 当命令的一部分。

**robocopy 排除清单新增 `plugins/`**：发行包内自带 core-bank 的**空壳**种子库，底座自更新一旦覆盖它，等于拿空库换掉老师的真题库。
插件版本归插件热更通道（合并语义、保住本机数据文件）管，底座自更新只管程序文件。

真机探针 `tools/self_update_probe.py` 25/25 绿，逐项核对：底座真自杀 → `.bat` 真覆盖 → 真重启到 v99.0.0 →
`data/` 全树逐字节未变（运行期文件除外）→ 本地插件逐字节未变 → 五个夹带载荷全部未落地 → `.bat` 自删 → 暂存清空 →
四步日志留痕 → 新界面截图（工作台与「底座在线 v99.0.0」徽标）。
产物：`.system_generated/self_update_probe/stage5-run6/`（`result.json`、`update.log`、`shots/`）。

---

## 三、封版数据

| 项 | 值 |
| --- | --- |
| 发行包 | `dist/jiuzhang-operator-beta-v0.9.0.zip` |
| 体积 | **1,959,225 B（1.868 MB）** |
| 条目 | 266（文件 265） |
| 敏感/临时文件命中 | **0**（`.env`、`.venv/`、`/data/`、`.git/`、`.system_generated`、`__pycache__`、`.pyc`、`.log`、`.bak`、`.scratch`） |
| 关键运行文件缺失 | **0**（`app/main.py`、`static/{index,workspace,settings}.html`、`schemas/question.json`、`start.bat`、`LICENSE`、`PLUGIN_SPEC.md`、`static/assets/qq-group.png` 等 19 项全在） |
| 包内种子库 | `plugins/org.jiuzhang.core-bank/bank/bank.db` = **0 题 / 11 表**（ADR-003 冻结空壳，真题库只留本机） |
| 包内版本 | `app/__init__.py` = `0.9.0`；前端兜底位 = `v0.9.0` |
| 插件结构自检 | 9 个插件：顶层目录名 == `plugin.json` 的 `id` **全部相符**；**全部无 `backend` 字段**；**全部带 Apache-2.0 `LICENSE`** |

`dist/` 清理：v0.2.0–v0.8.2 共 23 个旧发行包**移出**到 `.system_generated/dist_archive/`（未删除，可随时取回）；
`dist/` 现只留新包、dev-kit、四个插件 zip、`onboarding/` 与 `plugins/`。

---

## 四、测试与探针

- **全量单测**：`tools/run_all_tests.py` 逐模块跑 `.venv/Scripts/python.exe -m unittest tests.<模块>`（AGENTS §7 口径，不引入 pytest）——
  **42 个模块 / 809 个用例 / 0 失败**。升版前后各跑一轮，数字一致。
  踩坑记录：`unittest` 的 `Ran N tests` 统计行打在 **stderr**，只读 stdout 会数出 0。
- **真机自更新探针**：25/25（阶段五，见上）。
- **包体审计**：`0.9.0` 包 0 夹带 / 0 缺失 / 种子库空壳 / 9 插件结构全合规。
- **三查**（插件侧）：`fetch(` **0**、`parent.document` **0**、`localStorage` **0**。
- **请求 id**：插件自造 id 一律 `<字母><序号>_<base36 时间戳>`（如 `p1_mfk3a2b`），全部落在 `^[A-Za-z0-9_-]{1,80}$` 且**不含点号**；
  classic-card 与 handout 只回显宿主发来的 `message.id`，不另造。

---

## 五、未决问题与偏离

1. **官方插件索引漂移（追加军令已清缴）**：根 `plugins.json` 与 `E:\jiuzhang-plugins\plugins.json` 原先
   **不是逐字节相同**，且两处都把 `org.jiuzhang.editor` 标成 **0.3.0**，而已发布的 editor zip 也是 0.3.0
   （本地插件目录早已是 0.4.0，发布件没跟上）。
   **清缴办法不是改索引数字，而是先让发布件追上**：用 `tools/build_plugin.py` 重建 editor 0.4.0 包
   （30,187 B / 5 条目）覆盖插件仓库的 `plugins/org.jiuzhang.editor.zip`，再跑 `tools/sync_plugin_index.py`
   把索引校准到 0.4.0 —— 只改索引会让索引宣称 0.4.0 而下载到 0.3.0，比原来的漂移更坏。
   现在：两份索引**逐字节相同**（sha256 前 12 位 `3e4d1faa423d`）、`updated_at` 2026-10-24，
   且 **5 个条目的索引版本与已发布 zip 的实际版本逐一相符**（0 漂移）。
   另修了 `tools/sync_plugin_index.py` 里写死的 `updated_at: "2026-10-23"`，改为跟随当天日期。
2. **更正一条上轮结论**：v0.8.2 的三条控制台欠账（控制台「左树右二级菜单」、顶栏 Provider 配置弹窗、
   大纲树按教材版本过滤）**早已由阶段二提交 `7c02c5b` 清缴**，本晨报初稿把它们误列为「仍在」——
   现核对代码后更正：设置页左侧 4 个 nav（工作区/插件/模型配置/系统设置）+ 插件区右侧 4 个二级页签；
   顶栏模型胶囊与 Provider 弹窗节点已彻底退役（`workspace.js`/`workspace.html` 搜不到 `openProviderModal`）；
   大纲根层与搜索按工作区生效教材版本过滤（`bank.topics` 的 `textbook_id` + `active_textbook_id`）。
3. **`question.card` 卡片位仍未接回**：宿主不再逐题下发 `question.render`，对话工具里仍会调用；此条沿用 README「尚未实现」的表述。
4. **未在真实安装目录由人手点过「更新并重启」**：沙箱安装副本上已真跑全流程（真下载→真自杀→真覆盖→真重启到 v99.0.0），
   但真实安装目录的那次「人点按钮」路径未经人手验证——按下会结束当前进程，只能由人亲手做。已登记进 PROJECT_MEMORY 待办。
5. **时序抖动一笔**：`tests.test_plugin_update.test_10_resume_at_boot_completes_the_previous_batch_offline`
   曾在一次满负载全量跑里偶发失败（单跑与复跑均绿），属时序抖动，非逻辑缺陷；两轮全量均为 0 失败。
6. **本轮刻意未做**：`LICENSE` 未动；AGENTS.md 铁律一、铁律二未动；`schemas/` 无破坏性变更；用户 `data/` 目录未被写入
   （自更新探针实测逐字节未变）；`E:\math-question-bank-main` 等历史目录**零读取、零复制**，无一处代码来自旧项目。
7. **追加指令的口径**：二维码原文件名为 `群二维码.jpg` 但内容实为 PNG（magic `89504e47`、含 IEND），
   已重命名为 `static/assets/qq-group.png` 以便 README 用相对路径稳定渲染，README 与 `PROJECT_MEMORY.md` 引用同一张图。
8. **一条观察（未处理）**：插件仓库与索引只收录 5 个插件，本地 `plugins/` 另有 4 个（classic-card、dashboard、
   bank-browser、exam-paper、lecture 中的后四个）尚未对外发布。它们随底座发行包一起发货，不影响用户；
   要对外分发得单独出 zip 并加索引条目，属另一件事，本轮未做。

---

九章算术，算子至简。以此为碑，铭记今日。

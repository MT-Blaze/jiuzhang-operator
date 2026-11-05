---
trigger: model_decision
description: 九章算子测试、探针、像素证据与提交流程约束。写或改单测、跑回归、动探针、做前端验证、提交 commit、更新项目记忆与回传单时必须遵守
---

# R04 测试与流程约束（九章算子）

> 覆盖域：测试（域6）+ 流程与文档（域8）。结论来自 2026-11-02 实探，证据格式 `路径:行号`。

## 1. 单测（L0）

1. **[L0] 位置唯一**：`tests/test_*.py`（现 75 个模块 + 辅助 `core_sources.py`，**无 `__init__.py`**）。禁止在其他目录建测试、禁止建 tests 包。
2. **[L0] 框架只有标准库 `unittest`，不许引入 pytest**（`docs/STACK.md` §6；`.pytest_cache/` 是历史残留，不是在用）。**无覆盖率工具**（实测 grep 无 coverage/pytest-cov 痕迹），因此 G0 的"覆盖"一项按主路径+错误路径+边界清单判定，不报百分比。
3. **[L0] 单用例运行方式（实测可用）**：
   ```
   .venv/Scripts/python.exe -m unittest tests.test_clean_latex
   ```
   实测基线：`test_clean_latex` → `Ran 10 tests / OK`；`test_pinyin` → `Ran 5 tests / OK`；`test_backup_codec` → `Ran 6 tests in 0.057s / OK`；`test_version_consistency` → `Ran 14 tests / OK`。
4. **[L0] 两条禁令**：
   - 不许用系统 `python`：实测 `python -m unittest tests.test_clean_latex` → `Ran 1 test / FAILED (errors=1)`，导入即崩。
   - 不许用 `python -m unittest discover`：实测 `Ran 0 tests in 0.000s / NO TESTS RAN`——**这是绿色假通过，比报错更危险**（`docs/AGENTS.md:78` 原写"直接报错"，2026-11-02 已修正为实跑口径；`docs/STACK.md:91` 仍留旧写法，见到别照抄）。
5. **[L1] 全量回归**：`.venv/Scripts/python.exe tools/run_all_tests.py`（逐模块跑，正则抓 `Ran N tests`，末行 `模块 %d 个，用例 %d 个，失败模块 %d 个` + `全绿`，失败 `sys.exit(1)`，`tools/run_all_tests.py:38`）。等价 bash 版 `tools/sweep_units.sh` 按「退出码 + `grep -q "^OK"`」判定并把日志写入 `.system_generated/sweep/`（`:6-14`，**会落盘，非只读**）。
6. **[L0] 22 个模块会真起 uvicorn**（含 `Popen|uvicorn`）：`agent_plugin_tools`、`assets_api`、`bank_api`、`bank_batch_io`、`bank_dashboard`、`bank_dedupe`、`host_prefs`、`meta_api`、`pending_api`、`pending_meta`、`plugin_console`、`plugin_index`、`plugin_install`、`plugin_install_url`、`plugin_update`、`provider_config`、`providers_api`、`pwa_contract`、`questions_api`、`rich_card_ui`、`startup_prefs`、`workspace_restart`。
   其中显式设 `JZO_RESTART_DISABLED=1` 保住回包链路的：`tests/test_questions_api.py:47`、`test_bank_dedupe.py:522`、`test_plugin_console.py:346`、`test_workspace_isolation.py:56`、`test_workspace_restart.py:151`（总闸 `app/core/host_restart.py:42`）。**新写触碰切库/重启端点的测试必须照加这个闸**，否则测试在跟自己的服务对话。
7. **[L1] 断言纪律**：`Trigger → Action → Effect` 三元组锚业务意图；断言来源四件套 = [REQ] + [DESIGN] + 代码 diff + 存量测试；**测试逻辑必须匹配 HTML 初始态**（Toggle 默认 active 时不许断言切换前为 false——先读 DOM 再写断言）。

## 2. 真机探针（L1）

- 现 25 支 `tools/*_probe.py`，通用结构：`check(name, passed, detail)` 追加进 `checks` 列表（`tools/console_panel_probe.py:70`），产物落 `.system_generated/<探针名>/<tag>/probe.json` + 截图（`console_panel_probe.py:66`、`bank_probe.py:58`、`editor_probe.py:377`）。
- **[L1] `probe.json` 有三种历史 schema**，归一逻辑现成在 `tools/clean_for_release.py:69-98`：① `checks[]` + `passed/total`（`chat_keys_probe.py:180-183`、`self_update_probe.py:564`）② 只有 `checks[]` 无汇总（`command_ai_probe.py:727`）③ 只有 `failures` 计数（`:96`）。识别不了的 schema 一律判不通过。
- **[L0] 新探针禁止写死端口与令牌**：现存 5 支写死 8765/8777（`chat_keys_probe.py:23`、`console_panel_probe.py:26-28`、`fold_probe.py:19`、`split_probe.py:26`、`tab_group_probe.py:40-42`）、2 支写死 `dev-token-2026`（`console_panel_probe.py:28`、`tab_group_probe.py:42`），而底座读 `JZO_LOCAL_TOKEN`（`app/core/security.py:55`）→ 轮换即 401（历史事故 `docs/PROJECT_MEMORY.md:389`）。其余 21 支自起隔离 uvicorn 才是正例；端口/状态文件统一走 `tools/probe_paths.py:26-37`。
- **[L1] 探针预期不许写死题型与插件版本**（军令#24/#21 坑）；**判据可能跑在死代码上**——改动涉及滚动/布局时要先确认被测路径真在生效（行高不锁 → 滚动逻辑全是死代码）。
- **[L1] 无统一 runner**（grep 无命中）。收尾门禁只归一已存在的报告：`bash scripts/check-probe-reports.sh`；**探针执行本身仍由执行者按需求改动面手跑**（这是本次入驻留下的已知欠账）。

## 3. 前端与视觉验证（L0）

1. **[L0] 前端改动必须在浏览器里实际打开验证**，不得只靠静态检查（`docs/AGENTS.md:81`）。优先 browser-use 走真人路径（点、拖、滚、键盘），程序化 `focus()` 不算人手操作。
2. **[L0] 视觉改动要像素证据**：截图 + `.venv/Scripts/python.exe tools/pixel_scan.py <png>`（按 PAPER/CARD/DARK 归类打印行段，`:100-115`）。注意 `pixel_scan.py` **无判定、恒 rc=0**，`check_image_assets.py` 缺失也 `return 0`（`:261`）——两者只能当素材，不能当门禁。
3. **[L1] 量测口径坑**：`render-ms` 只算同步段不许冒充全卷；探针必须逐页滚过再量，否则假阴性；50/50 布局要扣 grid gap。
4. **[L1] 语法检查**：`.venv/Scripts/python.exe tools/js_syntax_check.py <js...>` 有 rc（`:43`），但依赖 playwright 起 chromium——归 L1 快检，不作 L0 门禁。

## 4. 流程与记录（L0/L1）

1. **[L0] 每完成一个大阶段立即 `git commit`（信息标注阶段），测试不绿绝不许 commit**（`docs/AGENTS.md:103`）。
2. **[L1] 提交信息**：中文，Conventional 前缀（`feat/fix/chore/docs/release/test`），说明"为什么"而不只"改了什么"；实测最近 15 条都无前缀外的阶段标注——阶段标注写在 `docs/PROJECT_MEMORY.md`，不在 commit subject 里堆。
3. **[L0] AI 代理不得 `git push`、建远端、改写历史、发 Release**，除非用户明确要求（`docs/AGENTS.md:83`）。多阶段任务按授权统一 push。
4. **[L1] commit trailer**：本机 `.git/hooks/commit-msg` 会剥离 `Co-authored-by` 等 AI trailer（未入库，换机即失效）——别依赖它。作者一律 `MT-Blaze <tianxiulaoshi@163.com>`。
5. **[L0] 交付证据口径（2026-11-02 主公裁决）**：**`docs/PROJECT_MEMORY.md` §5.6 机械证据回传单是唯一的对外交付证据**（五项：改动清单 / 包结构自检 / 三查结果 / 测试与探针 / 未决问题与偏离，模板逐字在 `:1417-1446`）。`.qoder/records/biz/` 只是流水线工序内的过程稿，**不做双写同步**。
6. **[L1] 续做先查在途工作**：动手前 `git status` 分清「已完成未提交」与真欠账；不要 stage/恢复他人的在途改动。`docs/handoff/`、`tools/handoff.py`、`tests/test_handoff.py` 均已入库（2026-11-05 核对），可直接依赖。
7. **[L1] 文档分工**：根 `AGENTS.md`＝1 行路标；`docs/AGENTS.md`＝铁律 + §9 工作流入口；`docs/PLUGIN_SPEC.md`＝插件契约唯一事实源；`docs/STACK.md`＝语言红线；`docs/PROJECT_MEMORY.md`＝进度/ADR/待办/军令模板/环境备忘；`tools/handoff.py`＋`docs/handoff/README.md`＝四席位一轮流程（已入库，2026-11-05 核对）。
8. **[L0] 禁改区**：`LICENSE`、`docs/AGENTS.md` 铁律一与铁律二、`schemas/` 破坏性变更（须升 `schema_version` + 同步示例 + 迁移说明 + 校验测试）、用户 `data/` 目录。

## 5. 门禁档位（L0）

| 档 | 命令 | 何时跑 | 内容 |
|---|---|---|---|
| 快门禁 | `bash scripts/check-quick-gate.sh` | **每个阶段收尾** | 命名 + 插件三查 + 插件包结构只读校验 + 两份 plugins.json 全等 + Schema JSON 合法性 + `audit_code` + `test_version_consistency` |
| 收尾门禁 | `bash scripts/check-release-gate.sh` | **工序 06、发版前** | 快门禁全部 + `tools/run_all_tests.py` 全模块 + `scripts/check-probe-reports.sh` |

- **[L0] 门禁不绿 = 未完成**，不许用"应该能过"的描述代替 rc。
- **[L1] 只读性**：门禁脚本一律不得写 `dist/`、`data/`、`plugins/`；`clean_for_release.py` 在门禁里只允许 `--dry-run`。

## 6. 自检清单

- [ ] 用 `.venv` 解释器逐模块跑过，贴的是当次原始输出
- [ ] 起服务的测试带 `JZO_RESTART_DISABLED=1`；没引入 pytest 或 discover
- [ ] 前端改动有浏览器真人路径 +（视觉类）截图与像素行段结论
- [ ] 新探针无写死端口/令牌；probe.json 能被归一脚本识别
- [ ] 快门禁绿，收尾阶段全量绿；未 stage 别人的在途改动
- [ ] 机械证据回传单五项齐备，未验证项显式写「未验证」

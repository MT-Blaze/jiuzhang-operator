---
trigger: model_decision
description: 九章算子模块结构、依赖与构建发布约束。改动 app/ 或 plugins/ 结构、增删依赖、碰版本字段、动 .bat/打包链路时必须遵守
---

# R01 模块与构建发布约束（九章算子）

> 覆盖域：模块与依赖（域1）+ 构建与发布（域7）。结论来自 2026-11-02 实探；2026-11-18 减税第一刀校正：路径按搬家后新位置更新，未当次核实的行号一律去掉，文档引用改章节锚点。

## 1. 模块与依赖方向（L0）

1. **[L0] 底座与插件之间没有代码依赖**：插件目录下零 `.py` 文件，`app/` 内无 `from plugins` 引入；底座只按目录扫描读插件清单（`app/core/plugins/registry.py:617`），插件静态资源经 `/plugin-assets/{plugin_id}/{asset_path}` 由底座代发（`app/api/plugins.py:453`）。
2. **[L0] 跨层调用只有一条路**：插件 `postMessage` → 宿主代持 HTTP（兄弟仓 `E:/jiuzhang/jiuzhang-plugins/src/org.jiuzhang.editor/dist/core_host.js` → `static/js/stage_inbound.js` → `static/js/stage_relay_bank.js` → `app/api/bank.py`），契约见 `docs/PLUGIN_SPEC.md` §2.6。禁止插件自己发 HTTP、禁止插件间直接调用或共享全局状态。
3. **[L1] 目录约定不可漂**：`app/api/`（底座级路由）、`app/core/`（配置/路径/安全/存储/插件域，已分子包）、题目契约在 `app/core/question_contract.py`（dataclass，无独立 Schema 文件）、插件源码在兄弟仓 `E:/jiuzhang/jiuzhang-plugins/src/`（每插件一目录含 `plugin.toml`）、`static/`（宿主壳）、`tools/`（脚本与探针）、`tests/`（单测）、`docs/`。**禁止在根目录堆放业务模块**（`docs/AGENTS.md` §4）。
4. **[L1] 新业务能力先问能否做成插件**；只有身份与权限、全局导航、数据总线、插件发现与生命周期、安全边界与错误隔离属于底座（`docs/AGENTS.md` §2）。
5. **[L0] 依赖只有四项钉版**：`fastapi==0.141.1`、`jsonschema==4.26.0`、`pypdfium2==5.9.0`、`uvicorn==0.52.1`（`requirements.txt`）。其中 `jsonschema` 代码零引用（2026-11-18 grep 实测），是否移除待主公裁决。新增依赖必须写进 `requirements.txt` 并钉版，禁止隐式安装（`docs/STACK.md` §7）。
   - 已知隐性依赖：`playwright==1.64.0` 实际装在 `.venv` 里但**不在 requirements.txt**，全部 32 支探针（2026-11-18 入库计数）依赖它。动探针前先 `.venv/Scripts/python.exe -c "import playwright"` 确认；是否正式入 requirements 属主公裁决项，不得由 coder 顺手加。
6. **[L1] 无 Node/package.json**：前端是原生 HTML/CSS/JS，`find` 全仓无 `package.json`（`.gitignore` 里预留的 `node_modules/` 是历史遗留）。禁止引入任何打包器或 Node 构建步骤。

## 2. 版本单一事实源（L0）

1. **[L0] 底座版本唯一源**：`app/__init__.py:8` `__version__ = "1.2.0"`；消费点 `app/main.py`、`app/core/plugins/lifecycle/update.py`；`/healthz` 回同一个值（`app/api/health.py`，含 `boot_id`）。前端与文档只许盖章，不许写死（`tests/test_version_consistency.py`）。
2. **[L0] 插件版本三处取更严**：`plugin.toml` 顶层 `version` + `min_host_version` + `[engine]` 节 `host_version`（现仅兄弟仓 `org.jiuzhang.dashboard/plugin.toml:30`），拦截逻辑 `app/core/plugins/lifecycle/update.py`。
3. **[L1] 探针与测试禁止写死插件版本**（`tests/test_version_consistency.py` 会抓），插件升级不得让存量测试变红。
4. **[L0] 两份索引必须语义一致**：主仓 `plugins.toml` 与兄弟仓库 `E:/jiuzhang/jiuzhang-plugins/plugins.json` 逐条语义一致；`tools/sync_plugin_index.py` 只改写主仓 toml，远端 json 只比对不代写。改索引必跑 sync，不许手改其中一份（口径出处 `docs/AGENTS.md` §9.1 L0 第 4 条）。

## 3. 构建与发布命令（L1）

| 动作 | 唯一入口 | 性质 | 备注 |
|---|---|---|---|
| 本地启动 | `start.bat` | 会装依赖、起服务 | 唯一官方启动器：自隐藏；先探 65496–65505 单实例锁（同目录复用、异目录按 PID 清场），身份看 `/healthz` 或 `app.main:app`；固定端口 65496，写 `data/.current_port`，健康后自动开 `/e`；`--stop` 全局停服 |
| 底座发版包 | `build_release.bat` | **写 `dist/`** | 版本名取 `app/__init__.py`；robocopy 排除 `.venv/data/.git/dist/*.scratch*`/demo-bank/core-bank/v063*.db/bank.db；把 `v063.db` 复制成空 `bank.db`（缺则 rc=1） |
| 插件打包 | `.venv/Scripts/python.exe tools/build_plugin.py <目录>` 或 `--all` | **写 `dist/plugins/`** | 打包前调 `validate_plugin`（`app/core/plugins/registry.py:411`），拒符号链接与 `.db/.zip/.pyc/dev/` |
| 开发套件 | `tools/build_dev_kit.py` | **写 `dist/`** | 打包后自审红线：禁名正则 + 密钥形态扫描，违令删包并 rc=1 |
| 插件索引同步 | `tools/sync_plugin_index.py` | **写主仓 `plugins.toml`** | 需兄弟仓库存在；远端 `plugins.json` 只比对不代写；新插件必须进 `PLUGIN_DIRS` |
| 发版前大扫除 | `tools/clean_for_release.py` | **破坏性 + 跑 `git gc --prune=now`（`:166`）** | 门禁只允许 `--dry-run`，真删须主公当场授权 |

- **[L1] 打包只读校验现状**：`build_release.bat` 只判 `errorlevel 8` 与 zip 是否存在，不校验包内 LICENSE；真正的红线校验在装载路径 `app/core/plugins/registry.py`（`validate_plugin`:411、禁 `backend` 字段 :452：id 反向域名格式、目录名==id、license 必须 Apache-2.0、缺 LICENSE 拒装、`min_host_version` 语义化）。所以**插件红线靠 `scripts/check-plugin-package.sh` 前置拦截，不能指望打包脚本**。

## 4. 环境坑（L0，每次跑命令前先对照）

1. **[L0] 必须用 `.venv/Scripts/python.exe`**：系统 Python 缺依赖，实测 `python -m unittest tests.test_clean_latex` → `Ran 1 test / FAILED (errors=1)`，把全部模块打成假报错。
2. **[L0] `python -m unittest discover` 是假通过不是报错**：实测 `Ran 0 tests in 0.000s / NO TESTS RAN`（因 `tests/` 无 `__init__.py`）。旧文档写"会直接报错"口径不准，已修正——**任何脚本或 CI 用 discover 都会得到绿色的零用例**。
3. **[L1] `.bat` 必须纯 ASCII + 全 CRLF**：中文会被 cp936 误解崩掉（`docs/PROJECT_MEMORY.md` §六「Windows 批处理三大坑」），换行由 `.gitattributes:1-2` 钉死（`* text=auto eol=lf` + `*.bat text eol=crlf`），`tests/test_version_consistency.py` 会抓。
4. **[L1] Git Bash 下 `find.exe` 抢占 PATH 会让整篇批处理终止**；无控制台时 `timeout`/`echo` 不可靠（`docs/PROJECT_MEMORY.md` §六「Windows 批处理三大坑」）。
5. **[L1] `tools/verify_bank_empty.py:8` 的 `ROOT` 已改为按 `__file__` 推导**（2026-11-05 仓库迁入 `E:\jiuzhang\` 时修掉旧盘符写死）；`:10` 仍会写 `data/bank_v063_empty_check.md`（属写盘，非只读）。
6. **[L1] 4 支探针写死 8765/8777**（`tools/console_panel_probe.py`、`fold_probe.py`、`split_probe.py`、`tab_group_probe.py`，2026-11-18 实测），其余 28 支自起隔离 uvicorn；生产端口只来自 `JZO_PORT`（默认 65496，`app/core/config.py:104`）。
7. **[L1] 禁止 `taskkill /F /IM python.exe`**；`JZO_PLUGINS_DIR` 仅进程启动前生效（`docs/PROJECT_MEMORY.md` §六「切表轮新增的环境坑（2026-10-23）」⑤⑥）。
8. **无 CI 先例**：`.github/` 不存在，仓内零 `*.yml`。门禁只在本机跑，别假设有流水线兜底。

## 5. 自检清单

- [ ] `bash scripts/check-quick-gate.sh` 绿（含两份索引语义一致、插件包结构只读校验、插件三查）
- [ ] 新增依赖已写入 `requirements.txt` 并钉版；未引入 Node/打包器
- [ ] 版本字段只改单一事实源，前端与测试没有写死版本
- [ ] 破坏性脚本（`clean_for_release.py`、`build_*`、`migrate_*`）没有被当成只读门禁偷偷跑
- [ ] `.bat` 改动保持纯 ASCII + CRLF

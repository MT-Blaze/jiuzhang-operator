---
trigger: model_decision
description: 九章算子模块结构、依赖与构建发布约束。改动 app/ 或 plugins/ 结构、增删依赖、碰版本字段、动 .bat/打包链路时必须遵守
---

# R01 模块与构建发布约束（九章算子）

> 覆盖域：模块与依赖（域1）+ 构建与发布（域7）。全部结论来自 2026-11-02 实探，证据格式 `路径:行号`。

## 1. 模块与依赖方向（L0）

1. **[L0] 底座与插件之间没有代码依赖**：`plugins/` 下零 `.py` 文件，`app/` 内无 `from plugins` 引入；底座只按目录扫描读插件清单（`app/core/plugins.py:571,579,584,596`），插件静态资源经 `/plugin-assets/{plugin_id}/{asset_path}` 由底座代发（`app/api/plugins.py:419`）。
2. **[L0] 跨层调用只有一条路**：插件 `postMessage` → 宿主代持 HTTP（`plugins/org.jiuzhang.editor/dist/core_host.js:37` → `static/js/stage_inbound.js:52` → `static/js/stage_relay_bank.js:87` → `app/api/bank.py:90,102,402`），契约见 `docs/PLUGIN_SPEC.md:558`（§2.6）。禁止插件自己发 HTTP、禁止插件间直接调用或共享全局状态。
3. **[L1] 目录约定不可漂**：`app/api/`（底座级路由）、`app/core/`（配置/路径/安全/存储/插件域）、`schemas/`（跨边界契约）、`plugins/`（每插件一目录含 `plugin.json`）、`static/`（宿主壳）、`tools/`（脚本与探针）、`tests/`（单测）、`docs/`。**禁止在根目录堆放业务模块**（`docs/AGENTS.md:53`）。
4. **[L1] 新业务能力先问能否做成插件**；只有身份与权限、全局导航、数据总线、插件发现与生命周期、安全边界与错误隔离属于底座（`docs/AGENTS.md:23`）。
5. **[L0] 依赖只有三项钉版**：`fastapi==0.141.1`、`jsonschema==4.26.0`、`uvicorn==0.52.1`（`requirements.txt:6-8`）。新增依赖必须写进 `requirements.txt` 并钉版，禁止隐式安装（`docs/STACK.md:92`）。
   - 已知隐性依赖：`playwright==1.64.0` 实际装在 `.venv` 里但**不在 requirements.txt**，全部 25 支探针依赖它。动探针前先 `.venv/Scripts/python.exe -c "import playwright"` 确认；是否正式入 requirements 属主公裁决项，不得由 coder 顺手加。
6. **[L1] 无 Node/package.json**：前端是原生 HTML/CSS/JS，`find` 全仓无 `package.json`（`.gitignore` 里预留的 `node_modules/` 是历史遗留）。禁止引入任何打包器或 Node 构建步骤。

## 2. 版本单一事实源（L0）

1. **[L0] 底座版本唯一源**：`app/__init__.py:8` `__version__ = "1.1.0"`；消费点 `app/main.py:150`、`app/core/plugin_update.py:143-145`；`/healthz` 回同一个值（`app/api/health.py:15-21`，含 `boot_id`）。前端与文档只许盖章，不许写死（`tests/test_version_consistency.py:64-81`）。
2. **[L0] 插件版本三处取更严**：`plugin.json` 顶层 `version`（第 5 行）+ `min_host_version`（第 11 行）+ `engine.host_version`（现仅 `plugins/org.jiuzhang.dashboard/plugin.json:30`），拦截逻辑 `app/core/plugin_update.py:158-161,319-322,341`。
3. **[L1] 探针与测试禁止写死插件版本**（`tests/test_version_consistency.py` 会抓），插件升级不得让存量测试变红。
4. **[L0] 两份 plugins.json 必须逐字节全等**：主仓 `plugins.json` 与兄弟仓库 `E:/jiuzhang/jiuzhang-plugins/plugins.json`，写入方 `tools/sync_plugin_index.py:18-19,60-61`，rc=0 仅当全等（`:68`）。改索引必跑 sync，不许手改其中一份（口径出处 `docs/PROJECT_MEMORY.md:290,294`）。

## 3. 构建与发布命令（L1）

| 动作 | 唯一入口 | 性质 | 备注 |
|---|---|---|---|
| 本地启动 | `start.bat` | 会装依赖、起服务 | 默认端口 8000，被占自动顺延到 8009，全占 rc=1（`:22-23,127-141`）；起 venv + ensurepip + 三源镜像重试（`:38-39,57-83,88-109`） |
| 底座发版包 | `build_release.bat` | **写 `dist/`** | 版本名取 `app/__init__.py`；robocopy 排除 `.venv/data/.git/dist/*.scratch*`/demo-bank/core-bank/v063*.db/bank.db（`:51-53`）；把 `v063.db` 复制成空 `bank.db`（`:67`，缺则 rc=1） |
| 插件打包 | `.venv/Scripts/python.exe tools/build_plugin.py <目录>` 或 `--all` | **写 `dist/plugins/`** | 打包前调 `validate_plugin`（`:81`），拒符号链接（`:67-68`）与 `.db/.zip/.pyc/dev/`（`:36-44`） |
| 开发套件 | `tools/build_dev_kit.py` | **写 `dist/`** | 打包后自审红线：禁名正则（`:67-72`）+ 密钥形态扫描（`:100-103`），违令删包并 rc=1（`:111-112`） |
| 插件索引同步 | `tools/sync_plugin_index.py` | **写两份文件** | 需兄弟仓库存在（`:19`）；新插件必须进 `PLUGIN_DIRS` |
| 发版前大扫除 | `tools/clean_for_release.py` | **破坏性 + 跑 `git gc --prune=now`（`:160`）** | 门禁只允许 `--dry-run`，真删须主公当场授权 |

- **[L1] 打包只读校验现状**：`build_release.bat` 只判 `errorlevel 8` 与 zip 是否存在，不校验包内 LICENSE；真正的红线校验在装载路径 `app/core/plugins.py:392-394,396,419,420,421,519-524`（id 反向域名格式、目录名==id、license 必须 Apache-2.0、缺 LICENSE 拒装、禁 `backend` 字段、`min_host_version` 语义化）。所以**插件红线靠 `scripts/check-plugin-package.sh` 前置拦截，不能指望打包脚本**。

## 4. 环境坑（L0，每次跑命令前先对照）

1. **[L0] 必须用 `.venv/Scripts/python.exe`**：系统 Python 缺依赖，实测 `python -m unittest tests.test_clean_latex` → `Ran 1 test / FAILED (errors=1)`，把全部模块打成假报错。
2. **[L0] `python -m unittest discover` 是假通过不是报错**：实测 `Ran 0 tests in 0.000s / NO TESTS RAN`（因 `tests/` 无 `__init__.py`）。旧文档写"会直接报错"口径不准，已修正——**任何脚本或 CI 用 discover 都会得到绿色的零用例**。
3. **[L1] `.bat` 必须纯 ASCII + 全 CRLF**：中文会被 cp936 误解崩掉（`docs/PROJECT_MEMORY.md:1506-1510`），换行由 `.gitattributes:1-2` 钉死（`* text=auto eol=lf` + `*.bat text eol=crlf`），`tests/test_version_consistency.py:109-110,136-139` 会抓。
4. **[L1] Git Bash 下 `find.exe` 抢占 PATH 会让整篇批处理终止**（`docs/PROJECT_MEMORY.md:1501`）；无控制台时 `timeout`/`echo` 不可靠（`:1503-1505`）。
5. **[L1] `tools/verify_bank_empty.py:8` 的 `ROOT` 已改为按 `__file__` 推导**（2026-11-05 仓库迁入 `E:\jiuzhang\` 时修掉旧盘符写死）；`:10` 仍会写 `data/bank_v063_empty_check.md`（属写盘，非只读）。
6. **[L1] 5 支探针手依 8765/8777**（`tools/split_probe.py:4-6`、`fold_probe.py:19` 等），其余 21 支自起隔离 uvicorn；生产端口只来自 `JZO_PORT`（默认 8000，`app/core/config.py:93`）。
7. **[L1] 禁止 `taskkill /F /IM python.exe`**（`docs/PROJECT_MEMORY.md:1483`）；`JZO_PLUGINS_DIR` 仅进程启动前生效（`:1487`）。
8. **无 CI 先例**：`.github/` 不存在，仓内零 `*.yml`。门禁只在本机跑，别假设有流水线兜底。

## 5. 自检清单

- [ ] `bash scripts/check-quick-gate.sh` 绿（含两份 plugins.json 全等、插件包结构只读校验、插件三查）
- [ ] 新增依赖已写入 `requirements.txt` 并钉版；未引入 Node/打包器
- [ ] 版本字段只改单一事实源，前端与测试没有写死版本
- [ ] 破坏性脚本（`clean_for_release.py`、`build_*`、`migrate_*`）没有被当成只读门禁偷偷跑
- [ ] `.bat` 改动保持纯 ASCII + CRLF

---
name: add-plugin
description: 在九章算子新增一支官方插件（沙箱 iframe UI 插件或 headless 工具插件）的标准动线：建目录、写 plugin.json 契约、装能力、进官方清单、同步两份索引、补测试。当需要新增插件族或复制模板插件起步时使用。
---

# add-plugin：新增一支官方插件

> 原子范围：只负责"把一支新插件做到能被底座发现并在画布跑起来"，不含业务功能实现细节。
> 前提：已读 `docs/PLUGIN_SPEC.md`（契约唯一事实源）与 R01/R02/R03。

## 步骤

1. **起步**：从 `examples/template-plugin/` 复制目录结构（**只复制结构，代码从零手写——铁律一**），目录名 = 反向域名 id，如 `org.jiuzhang.<name>`。
2. **写 `plugin.json`**：必须齐这 14 个键（官方七支的共有键集，缺任一即被快门禁打回）：
   `id / name / version / api_version / schema_version / kind / min_host_version / license / author / description / capabilities / permissions / bus / slots`
   - `license` 固定 `"Apache-2.0"`；`version` 与 `min_host_version` 必须是 `x.y.z`
   - **[L0] 禁止 `backend` 字段**（底座不支持后端插件，`app/core/plugins.py:421`）
   - 需要 `engine.host_version` 时同步写，与 `min_host_version` 取更严（`app/core/plugin_update.py:158-161`）
3. **附 Apache-2.0 `LICENSE` 全文**到插件目录根（`plugins.py:420` 缺文件即拒装）。
4. **实现**：`dist/index.html` + `dist/plugin.js`，私有逻辑按 editor 先例分 `core_*.js`（逻辑）/ `ui_*.js`（视图）。
   - 与宿主通信只走 `postMessage` 请求信封（`plugins/org.jiuzhang.editor/dist/core_host.js:37`）
   - **[L0] 三查必须 0 命中**：`fetch(` / `parent.document` / `localStorage`；私有数据写 `extensions`（反向域名前缀键）
   - 命令面在 `contributes.commands` 声明，派发由宿主 `static/js/stage.js:366-372` → `stage_command.js:305`
5. **接宿主白名单**（若需要新请求族）：改 `static/js/stage.js` 白名单 + 新建/扩展 `static/js/stage_relay_*.js`，错误码走宿主大写蛇形（见 R02 §2）。这属于底座改动，必须单独在 [PLAN] 里说明理由。
6. **进官方清单**：把目录名加进 `tools/sync_plugin_index.py` 的 `PLUGIN_DIRS`（**漏这一步 = 索引永远不含它**，先例：数据看板作为第七支就踩过）。
7. **同步索引**：`.venv/Scripts/python.exe tools/sync_plugin_index.py`（写主仓与 `E:/jiuzhang/jiuzhang-plugins` 两份，rc=0 才代表全等）。
8. **补测试**：`tests/test_<name>_plugin.py`，按 R04 只用 unittest、`.venv` 解释器；起服务的用例设 `JZO_RESTART_DISABLED=1`。
9. **打包**：`.venv/Scripts/python.exe tools/build_plugin.py plugins/org.jiuzhang.<name>`（内部调 `validate_plugin`，不过校验就不产出）。

## 自检

- [ ] `bash scripts/check-plugin-package.sh` 绿（目录名==id、字段齐、无 backend、LICENSE 是 Apache-2.0）
- [ ] `bash scripts/check-plugin-boundary.sh` 绿（三查 0、插件内无 .py）
- [ ] `bash scripts/check-plugin-index-parity.sh` 绿（两份全等 + 条目版本一致 + 已在 PLUGIN_DIRS）
- [ ] 新插件在底座画布里真能打开、报错时页签不拖垮宿主（`stage_frame.js:124-127` 30s 激活超时）

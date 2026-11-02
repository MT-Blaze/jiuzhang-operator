---
name: build-release
description: 九章算子的发版动线：版本号单源、发版前大扫除 dry-run、底座包与插件包产出、两份索引同步、包结构自检。当用户要求"出包/发版/打插件 zip/封版"或要核对发行包结构时使用。
---

# build-release：出包与封版

> 原子范围：只做发版链动作，不改业务代码。
> **[L0] 本 skill 含写盘与破坏性步骤**：任何 `git gc`、真删产物、覆盖 `dist/` 之前必须让用户当场确认。

## 前置（顺序不可换）

1. `bash scripts/check-release-gate.sh` 全绿（快门禁 + 全模块单测 + 探针归一）。
2. 版本号只改单一事实源 `app/__init__.py:8` `__version__`（`/healthz` 与包名都从它取；前端与测试禁止写死，`tests/test_version_consistency.py:64-81`）。
3. 插件版本按需改各 `plugins/*/plugin.json` 的 `version`（必要时 `min_host_version` / `engine.host_version`，二者取更严，`app/core/plugin_update.py:158-161`）。

## 步骤

1. **大扫除先看不动**：`.venv/Scripts/python.exe tools/clean_for_release.py --dry-run`
   - **[L0] 不带 `--dry-run` 会真删产物并跑 `git gc --prune=now`（`clean_for_release.py:160`）——必须用户当场授权**
   - 规矩出处 `docs/PROJECT_MEMORY.md` §一 第 8 条：每次改底座版本号、准备发版前手动跑一次
2. **插件包**：`.venv/Scripts/python.exe tools/build_plugin.py --all`（逐目录改 `plugins/<id>`；内部先 `validate_plugin`，不过校验就不产出；排除 `.db/.zip/.pyc/dev/`，拒符号链接，`build_plugin.py:36-44,67-68,81,101`）→ 产物 `dist/plugins/<id>.zip`，顶层目录名 == `plugin.json` 的 `id`。
3. **底座包**：`build_release.bat`（robocopy 白/黑名单排除 `.venv/data/.git/dist/*.scratch*`/demo-bank/core-bank/v063*.db/bank.db，`:51-53`；把冻结空基线 `v063.db` 复制成空 `bank.db`，`:67`，缺则 rc=1）→ `dist/jiuzhang-operator-v<VER>.zip`。
   - **[L0] 包内绝不能有 `data/`、不能有真实题库**：包内 `bank.db` 是 0 题空基线；456 题只留本机（ADR-003 纯净发版）。
4. **索引同步**：`.venv/Scripts/python.exe tools/sync_plugin_index.py`（需兄弟仓库 `E:/jiuzhang-plugins` 存在，`:19`）→ rc=0 才代表两份逐字节全等。
5. **开发套件**（按需）：`tools/build_dev_kit.py` 出 `dist/jiuzhang-dev-kit.zip`，自带禁名正则与密钥形态扫描，违令删包并 rc=1（`:67-72,100-103,111-112`）。
6. **包结构自检**（回传单第 2 项）：顶层目录名 == id、无 `backend` 字段、有 Apache-2.0 `LICENSE` 全文、`min_host_version`/`engine.host_version` 与当前底座版本关系写明。
7. **三查**（回传单第 3 项）：`bash scripts/check-plugin-boundary.sh` 三项 0 命中 + 请求 id 全部合规。

## 收尾

- 封版提交（中文说明"为什么"）；**`git push` 只在用户明确要求时执行**（`docs/AGENTS.md:83`）。
- 更新 `docs/PROJECT_MEMORY.md` 进度与版本号；如需分享报告，需求状态流转「已发布」后由 recorder 用 `archive-tech-report` 存档。

## 自检

- [ ] 发版前大扫除是以 `--dry-run` 起步、真删经用户授权
- [ ] 包内无 `data/`、无真题库、无 `.venv/`、无 `.git/`
- [ ] `dist/plugins/*.zip` 与索引条目版本一致，两份 plugins.json 全等
- [ ] 回传单【包结构自检】【三查结果】两项数字来自当次实跑

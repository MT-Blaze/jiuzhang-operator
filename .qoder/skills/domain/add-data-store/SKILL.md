---
name: add-data-store
description: 在九章算子新增表/新增一类持久化数据或做一次 SQLite 结构升级的标准动线：路径 property → 建库建表带版本 → 路由 → 挂载 → 测试，外加迁移与回滚。当需要新库新表、加字段、改 user_version 或写 migrate_* 时使用。
---

# add-data-store：加库/加表/结构升级

> 原子范围：只管持久化结构与迁移安全，不碰业务交互。
> 前提：R03 §2（连接三件套、迁移三律）。**任何写 `data/` 的动作都是高危，先确认白名单。**

## 步骤（4+1 处，先例＝待审中转站 commit `fd049b9`）

1. **路径**：在 `app/core/config.py:55-96` 加 property（**禁止 cwd 拼路径**，禁止像 `tools/verify_bank_empty.py:8` 那样写死盘符）。工作区类数据走 `app/core/workspace_paths.py:42-58`（default 住根 `data/`，其余住 `data/workspaces/<id>`）。
2. **建库建表带版本**：新模块照 `app/core/pending_db.py` 的三段结构——建表（`:109-165`）、`user_version`（`:37` + `:243-249`）、连接（`:221-234`，`timeout=10.0` + `row_factory` + `foreign_keys=ON` + `busy_timeout=5000`）。
   - WAL 策略要选边写进注释：主库/题库只在建库时设（`db.py:162-166`），pending 每次 connect 都设（`pending_db.py:228-232`）
   - **[L0] 逐句 `execute`，禁止 `executescript`**（隐式提交会留下半套库，`db.py:92-101`、`bank_schema.py:429-434`）
3. **迁移三律**：版本化分派（`db.py:173-176`）→ 先落 `.pre-vN.bak` 备份（`db.py:118-132`，幂等）→ 写回滚路径（`db.py:104-116`）。`user_version` 高于程序版本即拒绝打开（`db.py:168-178`），降级场景要显式处理。
4. **不变量自检**：迁移后核行数/结构（`db.py:149-151`、`bank_schema.py:458-485`），失败即回滚。
5. **路由 + 挂载**：`app/api/<域>.py`（写接口 `Depends(require_write_token)`）→ `app/main.py:166-167` include。
6. **测试**：`tests/test_<域>_api.py` + `tests/test_db_transaction_atomicity.py` 风格的事务用例。
7. **题目结构相关**：以 `schemas/question.json` 为准，改契约必须升 `schema_version` + 同步 examples + 写迁移说明 + 补校验测试（`docs/AGENTS.md:37`），然后跑 `bash scripts/check-plugin-index-parity.sh`（它会用 jsonschema 自校验每个 example）。

## 特别坑（逐条踩过，别再踩）

- **[L0] extensions 双向映射**：库内有序数组 ↔ 契约反向域名对象（`app/core/bank_codec.py:34-46` 写 / `:49-58` 读），`images`/`tags`/`taxonomy`/`grade` 寄生在 extensions 里、出参要还原顶层（`bank_write.py:77-115`、`bank_codec.py:66-72`）。加字段前先决定它进不进 extensions。
- **[L1] 查重把 extensions 拼进指纹**（`bank_dedupe.py:100-128`），合并时同名键保留项赢（`:287-298,479-480`）——新字段会影响查重命中。
- **[L1] 两套库并存**：主库是 18 列旧宽表 + tombstones（`db.py:23-67`），题库是七表 + 两版本表（`bank_schema.py:71-77`，DDL 在 `plugins/org.jiuzhang.bank-engine/bank/schema.sql`）。写代码前先确认自己在哪套库上；`bank_questions` 宽表已被守卫拒绝（`:316-321`）。
- **[L1] 对外题数口径是 456，不是 457。**

## 自检

- [ ] 4+1 处齐全，路径来自 `config.py`
- [ ] 有版本号、有 `.pre-vN.bak` 备份、有回滚、有不变量自检
- [ ] 无 `executescript`；写盘范围在 `data/` 白名单内（R03 §3.5）
- [ ] 状态写入用临时文件 + `os.replace`
- [ ] `.venv/Scripts/python.exe -m unittest tests.test_db_transaction_atomicity` 与相关模块实跑绿，贴原始输出

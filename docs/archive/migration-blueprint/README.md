# 归档映射：搬家蓝图三件套（2026-11-18 减税第二刀）

搬家已收口（git d6a2893「迁移最后一批」），蓝图使命完成，整体退出日常视野。
**只挪位置，内容一字未改**；原样备份在 `E:\jiuzhang\归档备份-20261118\<原相对路径>`。

| 原路径 | 新路径 | 为什么归档 | 引用方改指哪里 |
|---|---|---|---|
| `docs/CORE_TARGET_TREE.md` | 本目录 `CORE_TARGET_TREE.md` | 搬家目标树，收口后成历史 | 文件体积冻结台账真身是 `tests/test_file_size_contract.py`（35 条）＋根 `agents.md` 红线 4；后续瘦身卡以该测试为准 |
| `docs/CORE_MODULE_INVENTORY.md` | 本目录 `CORE_MODULE_INVENTORY.md` | 搬家前模块快照，数字已漂 | 现状以代码与 `docs/AGENTS.md` §4 目录约定为准 |
| `docs/CORE_REFACTOR_RISKS.md` | 本目录 `CORE_REFACTOR_RISKS.md` | 搬家风险清单，收口后成历史 | 其中「决策台账 D15」指 `docs/识别引擎-决策台账.md` D15 行（台账本体仍在 docs/，未归档） |

- 三件套互引（CORE_TARGET_TREE:557、CORE_MODULE_INVENTORY:184、CORE_REFACTOR_RISKS:4）随整体同迁，目录内相对关系不变。
- 代码注释 `app/core/ingest/render/cross.py` 引「决策台账 D15」——指向台账本体，不受本次归档影响，按零代码改动纪律未碰。
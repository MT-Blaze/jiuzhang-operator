# 归档映射：已收口零引用 records（2026-11-18 减税第二刀）

append-only 纪律：**只挪位置，不改内容不删内容**。
原样备份在 `E:\jiuzhang\归档备份-20261118\<原相对路径>`。

**归档位偏离申报**：卡定 `.qoder/records/archive/`，但快门禁 `scripts/check-naming.sh` 的 R00 正则
只认 `records/{biz|sys|reports}/{YYYY-MM}/` 直下路径，records 树内任何归档子目录必判红。
主公 2026-11-18 拍板改迁本目录（`docs/archive/retired-records/`，门禁只扫 `.qoder/`），
与卡把 `.qoder/templates/` 迁 `docs/archive/retired-templates/` 同款先例。文件名日期前缀不变。

| 原路径 | 新路径 | 为什么归档 | 引用方改指哪里 |
|---|---|---|---|
| `.qoder/records/biz/2026-11/20261106_dup-compare-ui-receipt.md` | 本目录同名 | 查重 UI 过程稿，已收口、零活引用 | 其引用的证据目录 `.qoder/records/biz/2026-11/20261106_dup-compare-evidence/` **留原地**（`tools/dup_compare_probe.py` 代码写入点；记录用全仓相对路径引用，不受移动影响） |
| `.qoder/records/biz/2026-11/20261114_footer-strip.md` | 本目录同名 | 底栏瘦身过程稿，已收口 | 同名截图目录随迁本目录（主公 2026-11-18 点头，清单外扩面已申报），记录内相对链接不断 |
| `.qoder/records/biz/2026-11/20261114_rail-toggles.md` | 本目录同名 | 栏开关过程稿，已收口 | 同上，截图目录随迁 |
| `.qoder/records/biz/2026-11/20261114_sidebar-text-toggle-removal.md` | 本目录同名 | 侧栏文字开关移除过程稿，已收口 | 同上，截图目录（含 verify.json）随迁 |
| `.qoder/records/sys/2026-11/20261102_doc_pipeline-workflow.md` | 本目录同名 | 所述 `docs/pipeline-workflow.md` 已被主公手删退役 | 无活引用；退役始末见 `docs/AGENTS.md` §9 注记 |

随迁证据目录（3 个，15 png + 1 verify.json）：`20261114_footer-strip/`、`20261114_rail-toggles/`、`20261114_sidebar-text-toggle-removal/`。
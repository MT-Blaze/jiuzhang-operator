# 20261104 · MD 清理清单（军令 #32 收尾附棒，PM 执行令）

口径：只动「建议删除」两份＋`.pytest_cache/README.md`；tracked 直接 `rm`（不动索引），非 tracked（含被 ignore 的）**一律移到**
`.system_generated/md_archive_20261104/`（该目录在 `tools/audit_code.py` 的 SKIP_DIRS 内，不进门禁）。
本轮未 commit、未 push，除本文件与上述三个文件外 0 字节改动。

| # | 路径 | 行数 | sha256 | tracked？ | 处置 | 恢复命令 | 理由 |
|---|---|---|---|---|---|---|---|
| 1 | `docs/tauri-assessment.md` | 70 | `4dd4bd6448b6da8c5005f600ab7b1294af3ad3d5b88ff2ec37c28e8a357f4b92` | 是 | 已 `rm`（`git status` 显示 ` D`） | `git checkout -- docs/tauri-assessment.md` | 2026-10-22 一次性 Tauri 选型评估，与现规则/代码无关联，唯一同名引用在 dist 快照内 |
| 2 | `dist/onboarding/当前架构与开发进度快照.md` | 666 | `1ec78500e5767856e2325468559a8ce88344a6deb491f2e809fffec4d45375c3` | 否 | **已回原位、未删**（移动后 grep 发现 `dist/onboarding/README_协作指南.md:16/20/51` 三处活引用，按「停下不删并报」执行） | 无需恢复 | dist 产物快照且中文名违 R00，但被同目录协作指南当「火种」索引，需主公另案裁决 |
| 3 | `.pytest_cache/README.md` | 8 | `420e808d79a6c25d3cda0af33bc4782314a14949866682c68ce8149e89b66b70` | 否，且被 ignore（`git check-ignore -v` → `.gitignore:6 .pytest_cache/`，故 `git status -uall` 不列它） | 移到 `.system_generated/md_archive_20261104/pytest-README.md` | 重跑 pytest 会自生成同款模板件；手工还原用 `mv .system_generated/md_archive_20261104/pytest-README.md .pytest_cache/README.md` | pytest 自动生成的模板件，与项目无关 |

删除后残留引用核验：`docs/tauri-assessment.md` 删后只剩 dist 快照与归档件里的**历史叙述文字**（非入口引用）；快照自身因 `dist/onboarding/README_协作指南.md` 三处活引用而**未删**。

另案登记（本轮未处理）：`AGENTS.md:14` 仍指向已被主公手动删除的 `docs/pipeline-workflow.md`（工作树 ` D`，不恢复），属悬空引用。

## 盘点补充（延迟普查收尾，本轮**未处理、未删**）

- 新增一条**确证死 import**：`tools/tab_group_probe.py:26 import os`（全文件 `os` 仅出现在该行，`os.` 零命中；pyflakes 本机未装，跳过不装）。
- 同文件同轮确证：`app/core/pending_dedupe.py:22 answer_from_storage`（见上一轮）。
- 延迟跑完的穷举普查（1026 条 0-ref）**不可采信为删除清单**：我的扫描器把「同文件内的后续引用」误判为 0-ref（如 `app/api/agents.py:34/39/110/136` 四处，实际 :150/:596/:628/:635 都在用），且路由处理函数按 PM 口径本就算「装饰器旁挂引用」。本轮 ③ 的「零引用符号普查」仍按上一轮结论标**未核实**，建议另棒用 vulture/pylint 复核。

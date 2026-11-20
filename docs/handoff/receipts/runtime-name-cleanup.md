# 回传单 · 运行期旧名统一为「云端 AI OCR」（#RUNTIME-NAME-CLEANUP-01）

【回执编号】 #RUNTIME-NAME-CLEANUP-01
【回执时间】 2026-11-20
【主公裁决】 2026-11-20：模型配置界面与识别下拉已统一「云端 AI OCR」，底座运行期写死旧名一并全局统一。
【执行结果】 **收口全绿**。底座仓 2 笔（代码＋测试 1 笔、回单＋biz 1 笔）；定向 5 模块 196/196 绿；
快门禁 PASS（6 项）；`app/ static/` 旧名零命中；**零 push、零重启、65496 零接触。**

基线：HEAD `47f7f4c`（ahead 104），工作树脏件仅 `?? tools/onnx_probe.py`（未 stage、未提交），与卡一致。
本卡：`31f2d3e`（代码＋测试，7 files）＋本回单笔（ahead 104→106）。
插件仓 jiuzhang-plugins 零改动。

## 桶一 · 背景

模型配置界面与识别下拉的展示名已由 seat 名单一来源＋组合继承统一为「云端 AI OCR」（2.26.3 收口）。
但底座运行期仍写死 14 处旧名「云端视觉/云视觉」，出现在识别详情、路由备注、重认/公式报错与显存提示里，
与界面口径不一致。

## 桶二 · 改点表（14 处 app ＋ 2 处测试断言 ＋ 3 处探针工具，纯文案零逻辑）

| 文件 | 行（改前） | 旧文案 | 新文案 |
|---|---|---|---|
| app/core/ingest/recognize/formula.py | 233 | 云端视觉公式识别失败：%s | 云端 AI OCR 公式识别失败：%s |
| 同上 | 235 | 云端视觉没认出公式 | 云端 AI OCR 没认出公式 |
| 同上 | 238 | 云端视觉返回的公式正文为空 | 云端 AI OCR 返回的公式正文为空 |
| app/core/ingest/recognize/reidentify.py | 54/57/60/63 | 请选整题座（MinerU/云端视觉/本地VLM）。 | 请选整题座（MinerU/云端 AI OCR/本地VLM）。 |
| 同上 | 73 | 云端视觉识别失败：%s | 云端 AI OCR 识别失败：%s |
| 同上 | 75 | 云端视觉没认出这道题 | 云端 AI OCR 没认出这道题 |
| app/core/ingest/recognize/router.py | 104 | 云端视觉逐题识别完成：%d/%d 道回填成功。 | 云端 AI OCR 逐题识别完成：%d/%d 道回填成功。 |
| 同上 | 107 | 云端视觉识别未全部成功（%s）… | 云端 AI OCR 识别未全部成功（%s）… |
| 同上 | 110 | _surface(route, "识别·云端视觉", …) | _surface(route, "识别·云端 AI OCR", …) |
| 同上 | 171 | （MinerU·本地/云端、本地VLM、云端视觉） | （MinerU·本地/云端、本地VLM、云端 AI OCR） |
| app/core/ingest/registry.py | 218 | 也可改云视觉（花小钱、快）。 | 也可改云端 AI OCR（花小钱、快）。 |
| tests/test_formula_route.py | 151 | assertIn("云端视觉公式识别失败", …) | assertIn("云端 AI OCR 公式识别失败", …) |
| tests/test_recognize_router.py | 168 | assertIn("识别·云端视觉", steps) | assertIn("识别·云端 AI OCR", steps) |
| tools/last_used_engine_probe.py | 10 | 云视觉座由宿主写口本地种一个 dummy 账号… | 云端 AI OCR 座由宿主写口本地种一个 dummy 账号… |
| 同上 | 124 | dummy 云视觉账号 | dummy 云端 AI OCR 账号 |
| 同上 | 126 | {"name": "探针云视觉", …} | {"name": "探针云端 AI OCR", …} |

- 零改：id、task 名、`cloud_vision` 标识符、`plan_recognize`、逻辑分支、`步骤`字段结构（仅 step 文案值变新名，测试断言同步）。
- 测试断言只做名称同步，未放宽、未删除。
- 边界说明：卡内 grep 范围为 `app/ tests/ static/`；实际全仓扫描另命中 `tools/last_used_engine_probe.py`
  3 处（docstring×2＋探针 dummy 账号名「探针云视觉」），按同一映射一并改，全仓无外部引用该账号名（已 grep 核实）。
- 未改：`docs/handoff/evidence/**`、`docs/handoff/receipts/**` 历史证据与 `.qoder/records/**` 过程稿（历史留档，不改）。

## 桶三 · 命令与 rc（当次实测）

1. 定向测试：
   `.venv/Scripts/python.exe -m unittest tests.test_formula_route tests.test_recognize_router tests.test_models_registry tests.test_command_registry tests.test_file_size_contract`
   → **rc=0**，`Ran 196 tests … OK`
2. 仓库快门禁：`bash scripts/check-quick-gate.sh` → **rc=0**，`check-quick-gate: PASS（6 项全过）`
   （体积预警 23 份，与基线相同，只看不拦）。
3. 零命中：`grep -rn "云端视觉\|云视觉" app/ static/` → **rc=1（无匹配）**；
   扩到 `tests/ tools/` 源码亦零命中（仅 `__pycache__/*.pyc` 旧缓存二进制命中，非源码，不入库）。
4. `git status`：提交后仅剩 `?? tools/onnx_probe.py`（开工即有，未动）。

## 桶四 · 边界与未决

- 不 push；未执行 `git add -A`；未 amend；未改 LICENSE / 根 agents.md / AGENTS 铁律一二 /
  `app/core/question_contract.py` / 用户 `data/`；未重启、未触碰 65496。
- 单文件行数：改动文件均为文案级替换，行数不变；体积预警与基线一致（23 份）。
- 生效方式：文案随进程加载，主公下次重启底座后全量生效（无重启债新增，与在途重启同批）。

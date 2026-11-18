# A2 图片型卷自动切题·第一刀（T4＋T8）· biz 记录（2026-11-18）

> 卡范围：只做 T4（RapidOCR→行清单+坐标→复用现有题号链切题）＋ T8（跨页题按 D15 纵拼），
> 3 份 A2 样本微闭环＋1 份含答案段 A1 对照测阈值。T5（抠几何图）、T7（答案区起点判定）、
> 59 份批量铺量一律不做。落题口径红线：题图+OCR 正文齐才进待审池；认不出的页只挂批次级
> 原卷页图＋左栏【框选切题】兜底，**不落占位题**（2026-11-05 主公斥「极其反人类」口径）。
> 回传单：`docs/handoff/receipts/a2-image-ingest-first-cut.md`（#A2-01）。

## 一、改动清单

- 新增 `app/core/ingest/recognize/ocr.py`（259 行）：RapidOCR 行清单（文字+坐标）→ 复用
  `render/regions._question_regions` 题号链切题；图片型 PDF 走 OCR 主路，YOLO 降辅助不主导（D7）。
- 新增 `app/core/ingest/recognize/guards.py`（68 行）：题号密度下限 `MIN_QUESTION_DENSITY=1.0`
  块/页；跨页题号回跳守卫（答案区重复编号）→ 丢该页题块＋按页落 `ledger_failure`（步骤名
  `自动切题·P{page}`，与批次级 P0 条目去重共存）。
- 新增 `app/core/ingest/recognize/crosspage.py`（131 行）：T8 编排——单栏卷跨页题续段判定
  （复用 `render/cross.select_continuation`）、D15 四条件纵拼（`stitch_cross_page`）、两段原图
  ＋两段坐标写进题块 `cross_page` 追溯；续段行文字并进题块正文（选项在下一页时题干不再只有一半）；
  纵拼成功不记 failure（调用方按 trace 播 ok，避免成功挂 ⚠ 徽标）。
- 修改 `app/core/ingest/layout/python.py`：`_column_split` / `_column_regions` 参数化
  （gutter_ratio、min_heads、increasing），OCR 路传 (0.015, 1)；原有文字层路默认值不变。
- 修改 `app/core/ingest/layout/router.py`：`run_scan` 接 OCR 行清单入口（116 行）。
- 修改 `app/core/ingest/render/cross.py`：D15 拼接复用/扩展（356 行，四条件与拼缝 8–12px 照旧）。
- 修改 `app/core/ingest/route.py`：删死代码 `scan_layout`（零引用、引用未导入符号，调用即 NameError）；
  跨页纵拼成功按 trace 往过程账本播一条 ok。
- 修改 `app/core/ingest/service.py`：识别瀑布接 OCR 级（保持恰好 400 行）。
- 修改 `app/core/pending/batch/bank_batches.py`：`_page_regions` 白名单加 `cross_page` 校验透传
  （pages≤2 / top_box、bottom_box≤4 / seam_px / stop_kind≤24；坏形状丢弃）——两段原图坐标随批次留存。
  491 行，进 451–550 WARN 拆分队列（登记欠账）。
- 修改 `requirements.txt`：钉版 `rapidocr==3.10.0`（包名偏离见§五）。
- 新增 `tests/test_a2_image_ingest.py`：20 例（坐标旋转、栏切分、回跳守卫、密度下限、纵拼四条件、
  续段文字合并、白名单透传等）。
- 修改 `docs/识别引擎-决策台账.md`：未决 1 收口＋本刀变更记录。

## 二、3+1 样本实测矩阵（隔离实例 65511，ev1/api_result.json，2026-11-18 19:30–19:31）

| 样本 | 批次 | 页 | 落池/应切 | 切题率 | 每页题号 | 密度(块/页) | 坏题 | 用时 | 跨页 |
|---|---|---|---|---|---|---|---|---|---|
| 东北师大附中2023-2024高一上第一次月考 | B-001 | 3 | 20/20 | 100% | 1:[1–8] 2:[9–12] 3:[13–20] | 6.67 | 2 | 26.2s | q8 拼 [1,2] |
| 2023一中高一上期末 | B-002 | 3 | 21/22 | 95.5% | 1:[1–10] 2:[11,12,13,15–18] 3:[19–22] | 7.00 | 2 | 44.7s | 无 |
| 蜜蜂试卷-2023庆中高一下期中 | B-003 | 2 | 20/21 | 95.2% | 1:[1–11] 2:[12–15,17–21] | 10.00 | 1 | 11.6s | 无 |
| 哈九中2024-2025高一上期末（含答案） | B-004 | 5 | 19/19 | 100% | 1:[1–7] 2:[8–14] 3:[15–17] 4:[18,19] 5:[] | 3.80 | 1 | 1.7s | 无（P5 答案区拒切） |

- 占位题 0 / 无图题 0 / 短题干 0（四份全零）；待审池每题有图有字。
- 错切 0；漏切 2：yz 第 14 题、qz 第 16 题（OCR 题头号漏识，正文仍留在邻题块内，可框选补）。
- 坏题＝识别体检报的正文出入（2/2/1/1），照原样切进待审＋日志警告，不弹红窗（既有口径）。
- B-004 P5：题号从 14 回跳（上一页已切到 19）→ 守卫拒切该页，落页级＋批次级失败账；
  左栏 P5 仍挂原卷页图＋【框选切题】，徽标「⚠1 份未自动切出」只在 B-004 行。
- 跨页追溯（B-001 q8）：`cross_page={pages:[1,2], top_box:[29.5,3980.0,2890.8,4295.0],
  bottom_box:[29.5,149.0,2890.8,334.0], seam_px:10, stop_kind:next_section}`；q8 资产 3 件
  （纵拼主图 4291×760 @300dpi＋两段原图）；过程账本 ok「跨页题 1 道已按 D15 纵拼，两段原图随题留存」。

## 三、题号密度下限阈值依据（§4）

实测好卷密度 3.80 / 6.67 / 7.00 / 10.00 块/页；台账§7.2 坏卷（题号链基本取不到）0.1 / 0.4 / 0.6。
取 `MIN_QUESTION_DENSITY=1.0` 块/页：高于坏卷峰值 0.6 留 0.4 裕量，低于好卷谷值 3.8 留 2.8 裕量；
低于下限整批不自动切、只挂页图＋框选兜底。写入 `recognize/guards.py`，依据留本表。
未跑 62/59 全量（卡禁）。

## 四、验收走通与证据（.system_generated/a2_image_ingest/ev1/，不进 git）

- `api_result.json`：上表原始输出（含 failures、progress_tail、cross trace）。
- `01_batch_list.png`：四批列表，仅 B-004 挂 ⚠1 份未自动切出；19/19、20/20、21/21、20/20。
- `02_dbsdfz_review.png`：B-001 三页绿框＋20 题块块块带图；运行日志如实（AI/MinerU 未指派不自动调）。
- `03_dbsdfz_q8_stitched.png`：q8 纵拼主图题干跨页、选项 A–D 全在（图为准）。
- `04_yz_review.png` / `05_qz_review.png`：B-002 21 题 21 图 3 页 / B-003 20 题 20 图 2 页。
- `06_hajz_badge.png` / `07_hajz_fail_list.png`：徽标真点展开失败清单；页级 P5【定位原卷页】启用、
  批次级 P0 同按钮 disabled（无页号不点亮）。
- `08_hajz_located.png`：焦点落启用态按钮＋工具发 Space 真键激活 → 开批跳左栏第 5 页＋琥珀描边
  （computed outline rgb(178,122,48) 3px）＋⚠2 页徽标。**披露**：本页 MCP 往返延迟大（press_key
  单程约 5.7s），裸跑描边只活 174ms，相机追不上；故仅在隔离实例临时 hold 无关的 120ms debounce
  重渲染定时器（截图后立即恢复），拍 locate 自身真实效果。
- `09_hajz_wiped_after_echo_rerender.png`＋`locate_wipe_evidence.json`：裸跑反证——MutationObserver
  记描边 +6613ms 加上、+6786ms 被开批后选区回声的 120ms debounce 全量重渲染抹掉；栈陷阱定位
  `core_selection.js:265 → ui_columns.js:589-591`。**插件侧先于本卡存在的缺陷，按红线只登记不修**。
- 真点方式沿用失败显性化卡键盘取证先例（focus＋press_key Space）；iframe 沙箱运行时加
  allow-same-origin 仅为 DOM 断言（隔离实例、已披露、重载需重加）。

## 五、偏离与欠账（全量披露）

1. **包名偏离**：卡写 `rapidocr_onnxruntime==3.10.0`，PyPI 实际包名 `rapidocr==3.10.0`
   （onnxruntime 为其依赖）；requirements 钉 `rapidocr==3.10.0`，只装这一个包进 `.venv`。
2. **双栏卷跨页跳过**：crosspage 只接单栏（columns!=1 跳过）——登记欠账，不在本刀扩。
3. **漏切 yz14 / qz16**：OCR 题头号漏识；正文在邻块、可框选补——登记欠账（T4 识别率尾巴）。
4. **q8 选项文字顺序乱**：OCR 行序局限（「12 12 3 3 D. A. B. C. …」）；纵拼图完整权威——登记欠账。
5. **T7 未做**：回跳守卫是题号链信任不变量，不是答案区起点判定——卡禁顺手，登记欠账。
6. **bank_batches.py 491 行**：白名单 +13 行进 WARN 拆分队列——登记欠账。
7. **抹边缺陷（新发现）**：locate 描边被开批后选区回声重渲染 ~174ms 抹掉（插件侧、先于本卡）；
   证据§四；按「失败显性化资产不改」红线只登记不修，交枢纽排期。
8. **取证仪表**：sandbox allow-same-origin 运行时加＋120ms debounce hold（仅隔离实例、用后恢复）——披露。
9. **解释性口径**：跨页续段截止复用 `render/cross.py` 既有 criterion-(a) 空白分支；栏切分 OCR 路
   参数 (gutter_ratio=0.015, min_heads=1)；「切题率＝落池/应切（答案区不计应切）」。
10. **git 口径**：分层封顶 4e71bec（ahead 1）不卷进本 commit、不 push；`tools/onnx_probe.py` 与
    插件仓 `models/*.onnx` 原地保留不 stage；单中文 commit 讲为什么。

## 六、禁改区自查

LICENSE / 根 agents.md / AGENTS 铁律一二 / `app/core/question_contract.py` / 用户 `data/` 与工作区：
均未触碰（git status 仅§一名单；取证全程 JZO_DATA_DIR=ev1/data 隔离）。

## 七、测试与门禁（当次实测）

- `.venv/Scripts/python.exe -m unittest tests.test_a2_image_ingest tests.test_bank_batch_io
  tests.test_page_render tests.test_ingest_triage tests.test_ingest_failure_surface
  tests.test_layout_router tests.test_file_size_contract` → **Ran 155 tests, OK (skipped=4)**。
- `bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**；WARN 23 份为既有拆分队列（含 bank_batches 491）。
- 未跑全量回归（2026-11-18 拍板：定向＋门禁为主）。
- 清场：`taskkill //PID 21928 //F`（隔离实例点杀，禁 /IM 口径遵守）。
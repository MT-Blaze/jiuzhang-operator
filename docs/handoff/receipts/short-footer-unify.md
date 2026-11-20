# 回传单 · 短卷页脚统一剥离小刀卡（#SHORT-FOOTER-UNIFY-01·主公 2026-11-20 裁决）

【回执编号】 #SHORT-FOOTER-UNIFY-01
【回执时间】 2026-11-20 19:05:00+08:00
【执行结果】 **成**。页脚剥离不分页数，≤2 页沿用同一套规则：
① `regions._question_regions` 删除 `apply_fallbacks` 开关，`_PDF_FOOTER` 正则＋裸页码
三判据恒开——页脚行既不入题干，也继续借其最高上沿给末题框底定 `+5pt` 限额；
② `furniture.filter_pages` 的 ≤2 页分支只剔 `bottom<0` 不可见水印碎片，页脚行留给切题层统一判；
③ `_PDF_FOOTER` 补认真实写法「第 1页，共 4 页」（全角逗号/空白，卡里点名的
「第 1 页 共 1 页」同形态），否则短卷页脚会整条漏剔。
哈尔滨六中卷离线回放 **7/7**：四页每页 region 的 (x,y,w,h,label,text) 与改动前模块逐字相同，
第 1 页六框 (y,h) 与⑥钉死值逐字同，题号链 [1-6][7-11][12-16][17-19] 与末框底
1829/1845/1563/1565 全对，孤字「2」仍在第 19 题题干内，四页页脚均不在任何题干 text。
定向七模块 152 例全绿（含 4 个环境跳过）；快门禁 PASS（6 项），体积预警 23 份与基线逐文件全同。
两仓不 push（奉令 hold）；插件仓零改零笔。**新码生效需主公重启一次**（65496 现 PID 2700
零接触，仍跑旧码）。

基线（开工实测零偏离）：operator `3f7f3e6`（ahead 84）；plugins `0841ccd1`（ahead 22，
editor 2.25.0）。工作树脏件仅环境件：operator `?? tools/onnx_probe.py`、plugins
`?? src/org.jiuzhang.editor/models/`＋`model_prefs.toml`——原地保留不 stage。
本卡 operator 两笔：`a962c1a`（刀＋canary＋回放证据）／收口笔（本回单＋biz）；ahead 84→86。
biz 记录：`.qoder/records/biz/2026-11/20261120_short-footer-unify.md`。

## 1.【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator）

- `a962c1a` 修改 `app/core/ingest/render/regions.py`（467→460 行，净减 7）：
  - `:31-34` `_PDF_FOOTER` 连接符由「括号/斜杠」扩为「括号/斜杠/逗号/空白」，
    WHY 注释两行（真实素材「第 1页，共 4 页」全角逗号形态）；三条既有形态仍命中。
  - `:198-223` `_question_regions` 删除 `apply_fallbacks` 参数与真假分支：页脚判定
    （`footer_lines`＝正则 ∪ 裸页码三判据）与剔行恒开，`footer_top`→末题框底限额结构不动。
  - `:58-75` `_pdf_page_regions` 同步删参；`:207-213`、`:58-62` docstring 改为
    「不分页数、同一套规则」。
- `a962c1a` 修改 `app/core/ingest/render/furniture.py`（218→229 行）：
  - `:1-14` 模块 docstring 与 `:67-71` `_off_page_lines` docstring 同步新语义
    （≤2 页判不出重复页眉，但不可见行照剔；页脚交切题层统一判）。
  - `:39-57` `filter_pages` ≤2 页分支：只跑 `_off_page_lines`；无剔除时仍返回原列表
    （保持既有 test_01/02 的 `assertIs` 语义），有剔除才重建。≥3 页路径一字未动。
- `a962c1a` 修改 `app/core/ingest/render/pdf.py`（436 行不变）：`:125-126` 注释同步；
  `:157-161` 删 `apply_fallbacks=False`，加 WHY 一行（主公 2026-11-20 裁决）。
- `a962c1a` 修改 `app/core/ingest/recognize/ocr.py`（282 行）：`:153-155` 删
  `apply_fallbacks=True` 实参（卡 grep 清单外调用点，见偏离①）。
- `a962c1a` 修改 `tools/textlayer_probe.py`（798 行）：`_regions` 删 `no_fallback`
  参数与 4 处调用同步（卡 grep 清单外调用点，见偏离①）；文档头链路描述同步。
- `a962c1a` 修改 `tests/test_page_render.py`（1039→1110 行，tests/ 豁免行数帽）：
  - `LastRegionBottomDirectionTest`（:644 起）旧案零删、错断言转正：
    test_01/02 删 `apply_fallbacks=False`（断言值不变）；test_03 转正为「≤2 页页脚已剔、
    题干干净、框底仍停 `footer_top+5pt`、输入行清单不被原地修改」；test_04 断言语义改
    「页脚剔除恒开」，字面坐标值一字未动。
  - 新增 4 案：test_05（1 页 `bottom<0` 水印碎片被 `filter_pages` 剔，框底与题干不受影响）、
    test_06（1 页页脚括号/空白/全角逗号三形态均剔）、test_07（1 页贴底纯数字答案行高≈正文
    不剔、框底盖住）、test_08（2 页两页页脚均剔、题号链 1→2 不受影响）。
  - `PageFurnitureTest.test_12`：两页水印旧断言（「两页仍原样不动」）按新规则①转正为
    「1–2 页也剔」；`test_11` 改为「开关已删、页脚恒剔」并钉 `apply_fallbacks` 传参抛 TypeError。
- `a962c1a` 新增 `docs/handoff/evidence/short-footer-unify/replay_short_footer.py`（251 行，
  自包含、平铺 ≤3 层）：原件只读复制→`_pdf_pages_builtin` 全 4 页→三组判据；
  `JZO_DATA_DIR` 指隔离目录，零碰本机 data/；零出网零额度零识别引擎零端口。
- `a962c1a` 新增 `docs/handoff/evidence/short-footer-unify/probe.toml`＋`replay_report.md`：
  当次实跑 7/7 逐判据 true（副本同步自 `.system_generated/short-footer-unify/`）。
- 收口笔 新增 `docs/handoff/receipts/short-footer-unify.md`（本单）＋
  `.qoder/records/biz/2026-11/20261120_short-footer-unify.md`（四阶段 append-only）。
- 禁改区自查：LICENSE **否**／根 agents.md 与 AGENTS 铁律一二 **否**／
  `app/core/question_contract.py` **否**／用户 `data/` **否**（回放 `JZO_DATA_DIR` 指
  `.system_generated/short-footer-unify/data`，原件只读复制自桌面，sha256 见 probe.toml）。
  卡禁动面 diff 可证零触：`_repeated_furniture`／`_numeric_page_numbers` 阈值与相似度、
  `_longest_number_run`、`_HEAD_PAD_PT`／`_REGION_GAP_PT`、`_trim_to_ink`、框左右宽、
  label/text 截断、`layout/python.py`、`cross.py`、裁图链。

### 插件仓（E:\jiuzhang\jiuzhang-plugins）

零改零 commit（HEAD 仍 `0841ccd1`，ahead 22）。`models/`＋`model_prefs.toml` 环境件原地保留。

## 2.【包结构自检】

本次不涉及插件（插件仓零改，zip 不重打，parity 持现版 2.25.0）。

## 3.【三查结果】

本次不涉及插件侧代码。底座改动面 grep 自查：`regions.py`／`furniture.py`／`pdf.py`／
`ocr.py` diff 内 `fetch(`／`parent.document`／`localStorage` 命中均 **0**（纯 Python
坐标逻辑，无前端）。

## 4.【测试与探针】

解释器一律 `.venv/Scripts/python.exe`，逐模块 unittest（禁 pytest/discover），当次实测：

| 模块 | 结果 |
|---|---|
| tests.test_page_render | Ran 64，OK（skipped=4） |
| tests.test_ingest_scan | Ran 14，OK |
| tests.test_a2_image_ingest | Ran 20，OK |
| tests.test_ingest_failure_surface | Ran 10，OK |
| tests.test_ingest_routing | Ran 10，OK |
| tests.test_ingest_triage | Ran 21，OK |
| tests.test_file_size_contract | Ran 13，OK |

合计 152 例全绿；4 跳过＝`E:\jiuzhang\testdata\20261105\模拟1.pdf` 本机缺席
（test_08b/08c/08d/WordEnrichment test_06 环境 skip，基线同口径）。triage 全绿
（上一卡收口后已清零，本卡未回退）。

真卷离线回放（`.venv/Scripts/python.exe docs/handoff/evidence/short-footer-unify/replay_short_footer.py`）
**7/7 PASS**：

| 判据 | 结果 | 实测 |
|---|---|---|
| sha256_matches_previous_card | true | `a6534786…b0f`（与⑥同卷同件） |
| render_4_pages_no_warning | true | pages=4 warnings=[] |
| J1a_no_coordinate_drift_vs_head | true | p1–p4 全 same（含 label/text 逐字） |
| J1b_page1_boxes_match_previous_evidence | true | 六框 (y,h) 612/196,801/185,984/198,1210/260,1464/179,1638/191 全等 |
| J2a_question_chains_and_last_bottoms | true | [1-6][7-11][12-16][17-19]；末框底 1829/1845/1563/1565 全等 |
| J2b_page4_three_regions_and_lone_two_kept | true | p4_regions=3，q19 题干含孤字「2」 |
| J3_no_footer_text_in_any_region | true | 四页各 1 条「第 N页，共 4 页」regex 命中，题干零泄漏 |

快门禁 `bash scripts/check-quick-gate.sh`：**PASS（6 项全过）**；体积预警 23 份
（regions.py 460 行仍在 451–550 带内，集合与基线逐文件全同，零新增）。
`regions.py` 467→460 净减 7；`furniture.py` 218→229；`pdf.py` 436 不变——均 ≤450 或
保持原警报位，无 >550 硬拦。

## 5.【未决问题与偏离】

① **卡 grep 清单少两处调用点**：§2 写「grep 全部命中点：:60/:64/:77/:205/:213/:226」
仅限 `regions.py` 内部；现场另有 `app/core/ingest/recognize/ocr.py:155`（显式传 True）与
`tools/textlayer_probe.py:166`（探针对 baseline 传 False）。删参后两处已同步改调，
否则 import/运行即炸。已按现场为准登记。
② **`_PDF_FOOTER` 不认真实页脚形态（exec 微调，已报告）**：真卷页脚是
「第 1页，共 4 页」（全角逗号、无括号），卡里 test B 的「第 1 页 共 1 页」同形态，
旧正则只认括号/斜杠 → 短卷页脚会整条漏剔，本卡目的落空。按 §2「允许 exec 微调但必须
报告」把连接符扩为 `[（(]…`／`[/／,，、]?` 两类四形态；既有 test_08a5/08a6/08a7d 仍绿。
③ **判据 1「与⑥已交 probe.toml 逐字相同」的现实缺口**：⑥ `probe.toml` 只落第 1 页六框
(y,h)＋四页链＋末框底，不含 2–4 页逐框坐标。回放改为更强的两路：a) 用
`git show HEAD:…regions.py` 载入改动前模块，对同一 kept 行清单、同 ⑥ 调用口径
（`apply_fallbacks=False`）逐字比对四页全部字段；b) 钉死⑥已录的六框 (y,h)、四页链与
末框底。两路皆 true，漂移为零。附：首次 J1a 曾误报 DRIFT，原因是基线调用没传墨迹、
新流程传了；补齐 ink 后四页全 same（自证非代码漂移）。
④ **test_12 转正不在卡 §3 清单**：`PageFurnitureTest.test_12` 原有「两页水印仍原样不动」
断言与 §2 规则 1（不可见行一律剔）直接冲突，属旧语义钉死；已转正为 1–2 页也剔。
⑤ **test_01/02 的 `assertIs` 保住**：≤2 页分支在「无剔除」时返回原列表对象（fast path），
两案一字未改仍绿；有剔除（test_05/test_12）才重建列表。
⑥ **超范围外改动**：`tools/textlayer_probe.py`（探针文档与调用）随参数删除同步，
非业务链路；`ocr.py` 仅删实参。
⑦ **规则边界（如实登记）**：≤2 页页眉无法凭「跨页重复」证据剥离——一页/两页没有重复
可比。这是规则本身的边界，不是本刀例外；页脚与不可见水印已在所有页数统一处理。

### restart 提示

新码需主公重启一次 65496 才生效。本卡对 65496 零接触：未重启、未杀、
未执行 `taskkill /F /IM python.exe`；收口时 PID 2700 仍监听（本卡未动）。

### 红线自检（逐条）

- LICENSE／根 agents.md／AGENTS 铁律一二／question_contract.py／用户 data/：**零触**。
- 65496 **零接触**。
- 插件仓零改零笔；本卡未写 git config。
- 干净房间：diff 全原创表达，未抄旧项目/texify/Surya。
- 依赖零新增（回放只用 pypdfium2＋标准库，皆现成）。
- 未执行 `taskkill /F /IM python.exe`；禁 JSON 落盘（证据全 MD/TOML/py）；
  stage 逐个点名（未用 `git add -A`）。
- push 全 hold：两仓未 push 不问。

### 未验证

- 真机 UI 拖短卷效果（需主公重启后验证，本卡零接触 65496）。
- `模拟1.pdf` 相关四案（testdata 本机缺席，环境 skip，基线同口径）。

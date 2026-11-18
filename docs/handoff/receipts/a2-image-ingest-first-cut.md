# 回传单 · A2 图片型卷自动切题·第一刀（T4＋T8，3 份样本微闭环）

【回执编号】 #A2-01
【回执时间】 2026-11-18T20:09:26+08:00
【实际耗时】 101 分 30 秒（首件落地 requirements.txt 18:27:56 → 收口 20:09:26，文件 mtime 实测；不含卡前讨论）
【执行结果】 部分成功：T4/T8 主线与 3+1 样本微闭环全部实测走通；【定位原卷页】真点复验发现插件侧先于本卡的抹边缺陷（描边 ~174ms 后被选区回声重渲染抹掉），按「失败显性化资产不改」红线只登记不修，故复验项记「到位但有缺陷披露」而非全绿

正文逐条对齐卡§0–§7；biz 记录 `.qoder/records/biz/2026-11/20261118_a2-image-ingest.md`（矩阵/阈值/欠账全量在那）。

## 【改动清单】

- 新增：`app/core/ingest/recognize/ocr.py`（259 行，RapidOCR 行清单→复用题号链）、
  `app/core/ingest/recognize/guards.py`（68 行，密度下限 1.0＋跨页回跳守卫）、
  `app/core/ingest/recognize/crosspage.py`（131 行，T8 单栏跨页纵拼编排＋续段文字合并＋cross_page 追溯）、
  `tests/test_a2_image_ingest.py`（20 例）
- 修改：`app/core/ingest/layout/python.py`（栏切分参数化，OCR 路 0.015/1，文字层默认不变）、
  `layout/router.py`（run_scan 接 OCR 入口）、`render/cross.py`（D15 复用/扩展）、
  `route.py`（删死代码 scan_layout＋纵拼成功播 ok）、`service.py`（瀑布接 OCR 级，保持 400 行）、
  `pending/batch/bank_batches.py`（_page_regions 白名单加 cross_page 校验透传，491 行 WARN）、
  `requirements.txt`（钉 rapidocr==3.10.0）、`docs/识别引擎-决策台账.md`（未决 1 收口＋两条变更）
- 删除：`route.py` 内 `scan_layout`（零引用 grep 实测；引用未导入符号，调用即 NameError）
- 禁改区自查：LICENSE / 根 agents.md / AGENTS 铁律一二 / `app/core/question_contract.py` / 用户 `data/`
  与工作区 —— **否**，均未触碰（git status 仅上列名单；取证 JZO_DATA_DIR=ev1/data 隔离）
- git 口径：4e71bec（ahead 1）不卷进本 commit、不 push；`tools/onnx_probe.py`、插件仓 `models/` 不 stage

## 【包结构自检】

本次不涉及插件包产出：插件仓 `git status` 仅 `?? src/org.jiuzhang.editor/models/`（照卡原地保留），
零代码改动；取证用插件为 src 副本进隔离实例 plugins/，不改发布件。

## 【三查结果】

插件零改动，三查不适用；为备查仍给隔离副本实测：
- `grep -c "fetch(" src/org.jiuzhang.editor/dist/*.js` → 0（插件走 postMessage）
- `grep -c "parent.document" …` → 0；`grep -c "localStorage" …` → 0
- 请求 id 口径：本刀未新增插件请求族，宿主 relay 白名单未动

## 【测试与探针】

- 单测（`.venv/Scripts/python.exe -m unittest`，逐模块点名）：tests.test_a2_image_ingest(20)、
  test_bank_batch_io、test_page_render、test_ingest_triage、test_ingest_failure_surface、
  test_layout_router、test_file_size_contract → **Ran 155 tests in 5.750s, OK (skipped=4)**（20:05 实测）
- 门禁：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**（20:06 实测；WARN 23 份既有拆分队列）
- 真机：隔离实例 127.0.0.1:65511（PID 21928，已 taskkill //PID 点杀）；4 份 PDF 上传入批→自动 OCR
  切题→待审池有图有字：B-001 20/20、B-002 21/22、B-003 20/21、B-004 19/19（P5 答案区守卫拒切），
  占位/无图/短题干全 0，错切 0；原始输出 `.system_generated/a2_image_ingest/ev1/api_result.json`
- 前端真人路径：浏览器走批次列表→各批评审→q8 纵拼图（4291×760，选项 A–D 全）→B-004 徽标→失败清单
  →焦点+Space 真键【定位原卷页】→跳第 5 页+描边；截图 01–09 落
  `E:\jiuzhang\jiuzhang-operator\.system_generated\a2_image_ingest\ev1\`（不进 git）
- 未跑全量回归（2026-11-18 拍板口径）；未跑 59/62 全量（卡禁）

## 【未决问题与偏离】

- 欠账：①双栏卷跨页跳过；②漏切 yz14/qz16（OCR 题头号漏识，正文在邻块可框选补）；③q8 选项文字序乱
  （图完整权威）；④T7 未做（卡禁顺手）；⑤bank_batches 491 行 WARN 拆分；⑥**抹边缺陷**：locate 描边被
  开批后选区回声 120ms debounce 全量重渲染 ~174ms 抹掉（`core_selection.js:265 → ui_columns.js:589-591`，
  先于本卡存在；MutationObserver +6613ms 加 / +6786ms 抹，栈陷阱实测；证据
  `ev1/locate_wipe_evidence.json`＋反证截图 09）——交枢纽排期，本卡不修
- 偏离：①卡写 rapidocr_onnxruntime==3.10.0，PyPI 实名 rapidocr==3.10.0，钉实名只装这一个包；
  ②取证仪表披露：隔离实例 iframe sandbox 运行时加 allow-same-origin（DOM 断言用）＋临时 hold
  ms===120 的 debounce 重渲染定时器（裸跑描边只活 174ms、MCP 单程延迟 ~5.7s 相机追不上；截图后
  立即恢复；08 拍的是 locate 自身真实效果，抹边缺陷用 09 与日志如实反证，不糊绿）
- 解释性口径：切题率＝落池/应切（答案区不计应切）；跨页续段截止复用 cross.py criterion-(a) 空白分支；
  密度阈值 1.0 依据＝好卷 3.8–10.0 vs 坏卷 0.1/0.4/0.6（台账§7.2）
- 未验证：双栏卷跨页、59 份铺量、T5/T7 —— 卡禁或欠账，直说未做
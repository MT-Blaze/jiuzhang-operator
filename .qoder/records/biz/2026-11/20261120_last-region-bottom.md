# 业务记录 · 末题框底方向修正小刀卡⑥（每页末题识别不全真根因）

【状态】 已收口（待主公重启生效）
【发起日期】 2026-11-20
【需求名】 last-region-bottom
【交付版本】 底座 a42b5f6→af069bf＋收口笔（ahead 80→82，不 push hold）；插件零改（0841ccd1，editor 2.25.0）

## [REQ] 2026-11-20

背景：老师拖哈尔滨六中卷（4 页，515.9×728.5pt→1434×2024px @200dpi）每页末题识别不全。
枢纽离线实证真根因：`render/regions.py:262-263` 无页脚分支
`page_bottom = min(bottom) + _REGION_GAP_PT`——PDF 坐标自页底向上数，「+5pt」是往上挪
5pt（≈14px）切进末行，不是向下留呼吸位。页脚被全卷剥离（furniture ≥3 页）→ 走进加反
分支；`apply_fallbacks=False`（pdf.py:161）又关单页兜底 → 每页末题都中招。第 1 页选项行
charbox bot 72.4/top 79.7→墨迹 1802–1822，region6 bottom 1809 压在选项上半截；
`_trim_to_ink` 只收不扩钉死错限额，裁图链拿框直裁 → 框漏一行识别漏一行。
验收：一处刀（方向修正＋页脚判定与剔行解耦）；canary 四案；定向七模块＋快门禁；
真卷离线回放 15/15（region6 bottom∈[1827,1831]、region1–5 钉死值逐字同、四页末框盖
最低行墨迹且停页脚之上、题号链连续）。
红线：行数≤467、警报集合零新增、text/label/框宽/扩顶/裁边/其余文件一字不动、
65496 零接触、用户 data/ 零触、插件仓零改、两仓 push hold、禁 JSON 落盘。

## [IMPL] 2026-11-20

涉及文件（底座仓，施工笔不 push）：
- `af069bf` 一处刀＋canary＋回放证据：
  `app/core/ingest/render/regions.py`（466→467 行）:221-231 页脚判定移出
  `if apply_fallbacks`（真假都算 footer_top 定框底；剔行仍仅真时做，≤2 页一行不剔）；
  :262-264 无页脚分支 `+5pt`→`max(0.0, min(bottom)-5pt)`，有页脚分支一字不动；
  两处 docstring 同步新语义（行数中性）。
  `tests/test_page_render.py`（957→1039 行）新增 LastRegionBottomDirectionTest 四案
  （限额逐字/合成墨迹全进框/留页脚行不剔且框停页脚上/开兜底旧语义钉死），旧案零删
  （test_11 只钉 text 未钉错方向，原样通过）。
  `docs/handoff/evidence/last-region-bottom/`：replay_last_region.py（自包含离线回放）
  ＋probe.toml＋replay_report.md（当次 15/15，副本同步自 .system_generated 隔离目录）。
- 收口笔：回单 `docs/handoff/receipts/last-region-bottom.md`（#LAST-REGION-BOTTOM-01）
  ＋本记录。
隔离回放：原件只读复制到 `.system_generated/last-region-bottom/source.pdf`，
`JZO_DATA_DIR` 指隔离 data，零碰本机 data/；零出网零额度零识别引擎零端口。

## [VERIFY] 2026-11-20

- 修前基线复核（当次实测，与卡 §1 逐字吻合）：region6 y=1638 h=171 bottom=1809；
  region1–5 (y,h)=(612,196)(801,185)(984,198)(1210,260)(1464,179)；选项行 charbox
  72.38/79.71pt、墨迹 1802–1822；页脚四页全被 furniture 剥离、kept 行页脚正则零命中。
- 定向逐模块 unittest（禁 pytest/discover）7 模块 148 例：test_page_render 60（OK，
  skipped=4＝testdata 模拟1.pdf 本机缺席环境 skip）、test_ingest_scan 14、
  test_a2_image_ingest 20、test_ingest_failure_surface 10、test_ingest_routing 10、
  test_file_size_contract 13 全绿；test_ingest_triage 21 中 1 红＝已知
  MineruPerQuestionTest.test_single_question_screenshots_not_the_whole_pdf
  （提速①旧 mock，卡点名照挂不治）。
- 快门禁 check-quick-gate PASS（6 项全过）；体积警报 23 份与基线逐文件全同
  （regions.py 466→467 原警报位，无新增文件）。
- 离线回放 15/15：p1 region6 bottom 1809→1829∈[1827,1831]（h 171→191）；region1–5
  逐字同；p1–p4 末框底 1829/1845/1563/1565 ≥ 最低 kept 行墨迹底 1823/1839/1557/1559，
  均 ≤ 页脚上沿 1933.5px；题号链 [1-6][7-11][12-16][17-19] 连续且末号＝页最大题号。
- 前端零改 → Playwright 真测免；真机 UI 未验证（需主公重启，65496 零接触）。
- 红线自检：冻结面零触；环境件（onnx_probe.py/models//model_prefs.toml）原地不 stage；
  65496 未重启未杀；插件仓零改；依赖零新增；证据全 MD/TOML/py 禁 JSON；两仓不 push。
- 偏离登记：行数口径基线实测 466（卡言 467），修后 467 满足硬帽、净 +1 如实登记；
  test_11 未触发「改断言转正」分支（只钉 text）；证据副本进 docs 循卡⑤先例；
  docstring 两处微改同步新语义（卡「一字未动」清单未含）。

## [RELEASE] 2026-11-20

- 底座两笔收口 ahead 82（af069bf＋收口笔），push hold 奉令不推。
- 插件仓零改零笔（ahead 仍 22，editor 2.25.0，zip 不重打）。
- 生效条件：主公重启一次 65496（现 PID 2700、16:48 启动早于刀笔，跑旧码；卡列旧 PID
  17136/9732 已不在＝主公 16:48 已自行重启过一轮，本卡零接触）；重启后拖本卷可见末题框包选项。
- 遗留挂号：①邻框 5px 微叠（region5 bottom 1643 < region6 top 1638，gap 5pt >
  head_pad 1.5pt 几何）另刀待拍板；②≤2 页卷末题 text 仍含页脚行另刀待拍板；
  ③triage 已知红照挂；④第 4 页最低 kept 行是孤字「2」分数碎片（现状正确覆盖，
  供后续末行语义刀参考）。
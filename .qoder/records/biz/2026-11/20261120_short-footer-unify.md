# 业务记录 · 短卷页脚统一剥离小刀卡（#SHORT-FOOTER-UNIFY-01）

【状态】 已收口（待主公重启生效）
【发起日期】 2026-11-20
【需求名】 short-footer-unify
【交付版本】 底座 3f7f3e6→a962c1a＋收口笔（ahead 84→86，不 push hold）；插件零改（0841ccd1，editor 2.25.0）

## [REQ] 2026-11-20

主公裁决：「页脚剥离不分几页，多少页都给它剥离，沿用同一套规则。」
背景：上一刀⑥把页脚判定与剔行解耦，但短卷（≤2 页）页脚仍不剥——`furniture.filter_pages`
页数 <3 直接原样返回行清单，`pdf.py` 又传 `apply_fallbacks=False`，于是
「第 N 页 共 M 页」与贴底裸页码留在题干、框内吃页脚墨迹；1 页卷的 `bottom<0`
不可见水印碎片也不剔。
验收：①不可见行一律剔；②页脚行一律剔并继续用于框底限额（正则∪裸页码三判据）；
③≤2 页页眉无法凭重复证据剥离＝规则边界，如实登记；canary 旧案零删、错断言转正＋
新增 4 案；定向七模块＋快门禁；真卷回放零坐标漂移。
红线：regions.py 净减、警报零新增、跨页判据/题号链/呼吸位/裁边/左右宽/label/text
截断/裁图链零改、65496 零接触、用户 data/ 零触、插件仓零改、两仓 push hold、
禁 JSON 落盘、stage 逐个点名。

## [IMPL] 2026-11-20

涉及文件（底座仓，施工笔不 push）：
- `a962c1a` 一处语义统一＋canary＋回放证据：
  `app/core/ingest/render/regions.py`（467→460 行）：`_PDF_FOOTER` 连接符扩为
  括号/斜杠/逗号/空白（真实写法「第 1页，共 4 页」）；`_question_regions` 删
  `apply_fallbacks` 参数与真假分支，页脚判定＋剔行恒开，`footer_top+5pt` 框底线不动；
  `_pdf_page_regions` 同步删参；三处 docstring 改「不分页数、同一套规则」。
  `app/core/ingest/render/furniture.py`（218→229 行）：≤2 页分支只跑 `_off_page_lines`，
  无剔除仍返回原列表；≥3 页路径一字未动。
  `app/core/ingest/render/pdf.py`（436 行）：删 `apply_fallbacks=False`＋WHY 一行。
  `app/core/ingest/recognize/ocr.py`（282 行）、`tools/textlayer_probe.py`（798 行）：
  卡外调用点同步删参。
  `tests/test_page_render.py`（1039→1110 行）：test_03 转正、test_04 断言语义换恒开
  （坐标值不动）、test_11 改恒剔并钉删参、test_12 两页水印转正；新增 test_05–08
  （1 页水印/1 页页脚三形态/贴底数字答案不误吃/2 页双页脚）。
  `docs/handoff/evidence/short-footer-unify/`：replay_short_footer.py（自包含离线回放）
  ＋probe.toml＋replay_report.md（当次 7/7）。
- 收口笔：回单 `docs/handoff/receipts/short-footer-unify.md`＋本记录。
隔离回放：原件只读复制到 `.system_generated/short-footer-unify/source.pdf`，
`JZO_DATA_DIR` 指隔离 data，零碰本机 data/；零出网零额度零识别引擎零端口。

## [VERIFY] 2026-11-20

- 定向逐模块 unittest（禁 pytest/discover）7 模块 152 例全绿：test_page_render 64
  （OK，skipped=4＝testdata 模拟1.pdf 本机缺席环境 skip）、test_ingest_scan 14、
  test_a2_image_ingest 20、test_ingest_failure_surface 10、test_ingest_routing 10、
  test_ingest_triage 21、test_file_size_contract 13。
- 快门禁 check-quick-gate PASS（6 项全过）；体积警报 23 份与基线逐文件全同，
  regions.py 467→460 净减 7、仍在 451–550 带内（原警报位，无新增文件）。
- 离线回放 7/7：四页每页 region (x,y,w,h,label,text) 与 `git show HEAD` 载入的改动前
  模块逐字相同；第 1 页六框 (y,h) 与⑥钉死值全等；题号链 [1-6][7-11][12-16][17-19]；
  末框底 1829/1845/1563/1565 全等；第 4 页 3 块、孤字「2」仍在第 19 题题干；
  四页页脚（「第 N页，共 4 页」）零泄漏进任何题干。
- 前端零改 → Playwright 免；真机 UI 未验证（需主公重启，65496 零接触）。
- 红线自检：冻结面零触；环境件原地不 stage；65496 未重启未杀；插件仓零改；
  依赖零新增；证据全 MD/TOML/py 禁 JSON；stage 逐个点名；两仓不 push。
- 偏离登记：①卡 grep 清单缺 `ocr.py`／`textlayer_probe.py` 两处调用点，已同步；
  ②`_PDF_FOOTER` 不认真实全角逗号形态，按「exec 微调须报告」补齐四形态；
  ③⑥ probe.toml 不含 2–4 页逐框坐标，回放改为「改动前模块逐字比对＋⑥已录值钉死」
  双路；④test_12 两页水印旧断言按规则 1 转正（卡未列）；⑤规则边界：≤2 页页眉
  无法凭重复证据剥离。

## [RELEASE] 2026-11-20

- 底座两笔收口 ahead 86（a962c1a＋收口笔），push hold 奉令不推。
- 插件仓零改零笔（ahead 仍 22，editor 2.25.0，zip 不重打）。
- 生效条件：主公重启一次 65496（现 PID 2700，本卡零接触）；重启后拖短卷（≤2 页）
  可见页脚不再进题干、框底停页脚上沿；1–2 页的不可见水印碎片同步剔除。
- 规则边界：≤2 页页眉无跨页重复证据，仍不剥——这是证据条件所限，不是例外。
- 遗留挂号：①三页卷纯数字页码仍要求同位置三页全中（furniture 既有判据，本卡零改）；
  ②`tools/textlayer_probe.py` 的 baseline 对照仍指向 baa9e56 时代的旧模块路径，
  属工具历史包袱，非本卡回归；③triage 已知红于上一卡已清零，本卡保持全绿。

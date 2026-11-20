# 回传单 · 末题框底方向修正小刀卡（排队⑥·每页末题识别不全真根因·主公 2026-11-20 点头）

【回执编号】 #LAST-REGION-BOTTOM-01
【回执时间】 2026-11-20 18:15:00+08:00
【实际耗时】 约 25 分（单段无人值守执行会话：基线复核＋根因数字复核＋一处刀＋canary 四案＋定向回归＋门禁＋离线回放＋回单）
【执行结果】 **成**。一处刀解冻 `_question_regions` 框底限额：无页脚分支 `min(bottom)+5pt`（往上切进末行）改 `max(0.0, min(bottom)-5pt)`（向下留呼吸位）；页脚判定与 `apply_fallbacks` 解耦——真假都认页脚定框底，剔行仍仅兜底开启时做（≤2 页一行不剔语义一字不动）。哈尔滨六中卷离线回放 **15/15**：第 1 页 region6 bottom **1809→1829**，选项行墨迹 1802–1822 全进框＋6px 呼吸位；region1–5 钉死值逐字同；四页末框均盖最低 kept 行墨迹底且停在页脚上沿（1933.5px）之上。定向七模块 148 例：143 执行绿＋4 环境跳过＋1 已知红照挂；快门禁 PASS（6 项），警报集合与基线全同（23 份）。两仓不 push（奉令 hold）；插件仓零改零笔。**新码生效需主公重启一次**（65496 现 PID 2700、16:48 启动早于本卡刀笔，仍跑旧码；卡列旧 PID 17136/9732 已不在，本卡零接触）。

基线（开工实测零偏离）：operator `a42b5f6`（ahead 80）／plugins `0841ccd1`（ahead 22，editor 2.25.0）。
工作树脏件仅环境件：operator `?? tools/onnx_probe.py`、plugins `?? src/org.jiuzhang.editor/models/`＋`model_prefs.toml`——原地保留不 stage。
本卡 operator 两笔：`af069bf`（刀＋canary＋回放证据）／收口笔（本回单＋biz）；ahead 80＋2＝82。
plugins 零改零笔，ahead 仍 22。
biz 记录：`.qoder/records/biz/2026-11/20261120_last-region-bottom.md`。

## 1.【改动清单】

### 底座仓（E:\jiuzhang\jiuzhang-operator）

- `af069bf` 修改 `app/core/ingest/render/regions.py`（466→467 行，splitlines 口径，见偏离①）：
  - `:221-231` 页脚判定与剔行解耦：`footer_lines`（`_PDF_FOOTER` 命中＋`_bare_page_footer_lines`）
    与 `footer_top` 移出 `if apply_fallbacks`，无论开关真假都计算；剔行（`footer_ids`→`content`）
    仍仅 `apply_fallbacks=True` 时做，`else` 分支 `content = list(lines)` 原样。
  - `:262-264` 方向修正：无页脚分支
    `min(line["bottom"] for line in content) + _REGION_GAP_PT` →
    `max(0.0, min(line["bottom"] for line in content) - _REGION_GAP_PT)`；
    有页脚分支 `footer_top + _REGION_GAP_PT` 一字未动。WHY 注释一行（:262）。
  - `:64-65`、`:213-215` 两处 docstring 同步新语义（「不跑单页兜底」→「不做单页兜底剔行；
    页脚判定仍为末题框底定限额」），行数中性。
  - 行清单、题干 text、label、框左右宽、head 重叠扩顶、`_trim_to_ink`、其余正则、
    `furniture.py`、`cross.py`、`pdf.py`、裁图链：**一字未动**（diff 可证）。
- `af069bf` 修改 `tests/test_page_render.py`（957→1039 行，tests/ 豁免行数帽）：
  新增 `LastRegionBottomDirectionTest`（:645-728）四案，旧案零删：
  - test_01 无页脚＋关兜底＋无墨迹：末题框底逐字等于 `(842-(600-5))×(2339/842)` round 1；
  - test_02 无页脚＋合成墨迹：框底 ≥ 选项墨迹底 728＋6px 且 ≤ 限额像素；
  - test_03 行清单留页脚＋关兜底（≤2 页语义）：框底停 `footer_top+5pt` 换算像素、
    不吃页脚墨迹（含合成页脚墨迹对照）、输入行清单 len 与内容钉死不被剔；
  - test_04 开兜底旧语义钉死：页脚照剔、有页脚限额与修前逐字同。
- `af069bf` 新增 `docs/handoff/evidence/last-region-bottom/replay_last_region.py`（167 行，
  自包含、平铺 ≤3 层）：原件只读复制→`_pdf_pages_builtin` 全 4 页→逐页五判据；
  `JZO_DATA_DIR` 指隔离目录，零碰本机 data/；零出网零额度零识别引擎零端口。
- `af069bf` 新增 `docs/handoff/evidence/last-region-bottom/probe.toml`＋`replay_report.md`：
  当次实跑 15/15 逐判据 true（副本同步自 `.system_generated/last-region-bottom/`，
  先例卡⑤ crlf-normalize 同款证据布局）。
- 收口笔 新增 `docs/handoff/receipts/last-region-bottom.md`（本单）＋
  `.qoder/records/biz/2026-11/20261120_last-region-bottom.md`（四阶段 append-only）。
- 禁改区自查：LICENSE **否**／AGENTS 铁律一二 **否**／`app/core/question_contract.py` **否**／
  用户 `data/` **否**（回放 `JZO_DATA_DIR` 指 `.system_generated/last-region-bottom/data`，
  原件只读复制自桌面，sha256 见 probe.toml）。依据：`git show --stat` 两笔文件清单。

### 插件仓（E:\jiuzhang\jiuzhang-plugins）

零改零 commit。`models/`＋`model_prefs.toml` 环境件原地保留。

## 2.【包结构自检】

本次不涉及插件（插件仓零改，zip 不重打，parity 持现版 2.25.0）。

## 3.【三查结果】

本次不涉及插件侧代码。底座改动面 grep 自查：`regions.py` diff 内
`fetch(`／`parent.document`／`localStorage` 命中均 **0**（纯 Python 坐标逻辑，无前端）。

## 4.【测试与探针】

解释器一律 `.venv/Scripts/python.exe`，逐模块 unittest（禁 pytest/discover），当次实测：

| 模块 | 结果 |
|---|---|
| tests.test_page_render | Ran 60，OK（skipped=4） |
| tests.test_ingest_scan | Ran 14，OK |
| tests.test_a2_image_ingest | Ran 20，OK |
| tests.test_ingest_failure_surface | Ran 10，OK |
| tests.test_ingest_routing | Ran 10，OK |
| tests.test_ingest_triage | Ran 21，FAILED (failures=1)＝已知红照挂 |
| tests.test_file_size_contract | Ran 13，OK |

合计 148 例：143 执行绿＋4 跳过＋1 已知红。
- 4 跳过＝`E:\jiuzhang\testdata\20261105\模拟1.pdf` 本机缺席（test_08b/08c/08d/WordEnrichment
  test_06 环境 skip，基线同口径），非本卡回归。
- 已知红一案：`MineruPerQuestionTest.test_single_question_screenshots_not_the_whole_pdf`
  （提速①旧 mock 陈旧，卡 §4 点名照挂不治，非本卡回归）。
- 快门禁 `bash scripts/check-quick-gate.sh`：**PASS（6 项全过）**；体积警报 23 份与基线
  逐文件全同（regions.py 466→467 仍在原警报位，无新增文件）。
- 离线回放：`docs/handoff/evidence/last-region-bottom/replay_last_region.py` 当次实跑
  **15/15 passed**；产物 `.system_generated/last-region-bottom/probe.toml`＋`replay_report.md`
  （证据副本在 `docs/handoff/evidence/last-region-bottom/`）。逐判据：
  - 修前基线复核（baseline_probe.py 当次实测）：region6 y=1638 h=171 bottom=**1809**；
    region1–5 (y,h)=(612,196)(801,185)(984,198)(1210,260)(1464,179)；选项行 charbox
    bottom=72.38 top=79.71pt；墨迹行 1802–1822；页脚「第 N 页 共 4 页」四页全被
    furniture 剥离（4 页≥3），`_PDF_FOOTER`/裸页码对 kept 行零命中——与卡 §1 逐字吻合。
  - 修后：p1 region6 bottom=**1829.0** ∈ [1827,1831]（h 171→191）；region1–5 逐字同；
    p1–p4 末框底 1829/1845/1563/1565 ≥ 各页最低 kept 行墨迹底 1823/1839/1557/1559；
    四页均 ≤ 页脚上沿 1933.5px；题号链 [1-6][7-11][12-16][17-19] 连续且末号＝页最大题号。
- 前端零改 → Playwright 真测免（卡 §4 明示）。
- 真机 UI 未验证：新码生效需主公重启一次（见未决④），本卡不擅自重启。

## 5.【未决问题与偏离】

### 三桶汇报

**做了什么**：一处刀（框底方向＋页脚判定解耦）＋canary 四案＋真卷离线回放 15/15＋
定向七模块＋快门禁＋两笔 commit＋回单＋biz。

**成没成**：成。回放判据全过、定向绿（已知红除外）、门禁 PASS、邻居坐标零漂移、
行数 ≤467、警报集合零新增、红线零触。

**遗留需拍板**（卡 §8 照挂＋本卡新发现）：
1. 邻框 5px 微叠：region5 bottom 1643 低于 region6 top 1638，吃进第 6 题上标「2 1」
   （gap 5pt > head_pad 1.5pt 几何）——另刀待拍板，本卡不治。
2. ≤2 页卷末题题干 text 仍含页脚行（text 语义本卡不动，canary test_03 钉死现状）——另刀待拍板。
3. triage 已知红一案照挂（提速①旧 mock）。
4. 两仓 push hold；**主公重启一次后**拖本卷可见末题框包选项（65496 现 PID 2700 跑旧码）。
5. 新发现（本卡实测，供下一刀参考）：第 4 页最低 kept 行是孤字「2」（第 19 题分数段碎片，
   bottom=167.20pt），方向修正后末框底 1565 已盖住它；若后续做「末行语义」刀需留意
   分数碎片行与裸页码判据的边界（该行行高与正文同档，未被误判页脚，现状正确）。

### 偏离登记

① **行数口径**：卡 §2 言「regions.py 现 467 行」，开工实测基线 splitlines=466
（快门禁同口径 466）；修后 467，净 +1（方向 WHY 注释一行，页脚解耦注释已折一行抵充）。
硬约束「修后 ≤467」满足；「净不增」按实测基线 466 口径差 1 行，如实登记。
② **test_11 未触发改断言分支**：卡 §3「若既有案钉的是旧错方向：改断言转正」——实测
test_11 legacy/raw 对照只钉 text（页脚剔/留），未钉框底坐标，修后原样通过，无需改断言、未删案。
③ **证据布局**：回放产物按卡 §5 落 `.system_generated/last-region-bottom/`（git 忽略），
另按先例卡⑤（crlf-normalize）把 probe.toml＋replay_report.md 副本提交进
`docs/handoff/evidence/last-region-bottom/`，使证据可随仓复核；修前基线探针
`baseline_probe.py` 留隔离目录（git 忽略），其数字已录进 replay_report.md。
④ **docstring 两处微改**（:64-65、:213-215）：卡 §2「一字未动」清单未含 docstring；
旧句「为假时不跑单页兜底」与新语义（判定照跑、只不剔行）冲突，按 AGENTS §8.6 同步文档，
行数中性。其余注释零新增（仅方向 WHY 一行＋解耦说明一行）。

### 红线自检（逐条）

- LICENSE／根 agents.md／AGENTS 铁律一二／question_contract.py／用户 data/：**零触**。
- `tools/onnx_probe.py`（底座）／plugins `models/`＋`model_prefs.toml`：原地保留未 stage；
  engines/ 产物零触。
- 65496 **零接触**：未重启未杀。收口 tasklist＋netstat 只读复核：卡列 PID 17136/9732
  已不在（主公 16:48 已自行重启过一轮），现 65496 由 PID 2700 监听
  （CreationDate 2026-11-20 16:48:03，早于刀笔 18:10:33，仍跑旧码）；另有 python 16928
  小进程非产品。产品存活，新码待主公再重启一次。
- 插件仓零改零笔；本卡未用 git config 写入（operator 身份现成，plugins 无 commit）。
- 干净房间：diff 全原创表达，未抄旧项目/texify/Surya。
- 依赖零新增（回放只用 pypdfium2＋标准库，皆现成）。
- 未执行 `taskkill /F /IM python.exe`；禁 JSON 落盘（证据全 MD/TOML/py）。
- push 全 hold：两仓未 push 不问。

### 未验证

- 真机 UI 拖卷效果（需主公重启后验证，本卡零接触 65496）。
- `模拟1.pdf` 相关四案（testdata 本机缺席，环境 skip，基线同口径）。
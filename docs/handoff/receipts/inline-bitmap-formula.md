# 回传单 · 文字直取行内位图公式兜底（#INLINE-BITMAP-FORMULA-01 刀 B）

【回执编号】 #INLINE-BITMAP-FORMULA-01
【回执时间】 2026-11-20 22:42:13+08:00
【执行结果】 **成**。新增独立检测模块，把文字层里丢失的行内公式位图认出来并进
公式裁图清单；I3 唯一命中 **85**（p1 71 / p2 14，与侦查一致），5 份靶卷、D1/E2
及另两份普通文字卷均 **0**。只改 `discover_spans` 一处调用；正文文字直取、
`formula.py` 文字层 span 逻辑、`normalize_latex` 与查重指纹均未触碰。
基线 `41546a7`（ahead 114）；commit 1 `389e8af`（代码＋测试），commit 2 收口
（本回单＋biz）→ ahead 116。不 push；65496 零接触；探针落在
`.system_generated/inline-bitmap-formula/`（不进 git，产物仅 `probe.toml`）。

## 1. 接入点（先读后改）

- 公式裁图清单唯一构建处：`app/core/ingest/recognize/formula.py:195 discover_spans()`，
  唯一消费处：`formula.py:355 run_combo()` 的 `spans = discover_spans(...)`。
- 条目字段（现有约定）：`{"bbox": [x, y, w, h], "text": 原串, "latex": 预置 LaTeX,
  "origin": "mineru|textlayer"}`；`bbox` 是**题块左上为原点、300dpi 的像素**坐标，
  `crop_png()` 直接按它从同张题图裁块。
- 文字层来源：`formula.py:118 _textlayer_spans()`（字符 run → PDF 点 → 题块像素，
  `factor = 300/72`）。行内位图不走它。
- 纯图卷停点：triage 的 `text_layer=False` → `router.py:169` 直接显性拒绝组合路，
  整页走整题座；新模块另在 `_text_context()` 里对「无文字层页」直接返回空，
  纯图卷零触发，刀 B 不越过。
- 改动：`discover_spans()` 在文字层 span 之后追加一次
  `inline_formula_images.discover(...)`，再 `merge_spans()` 合并；MinerU 优先路径原样。
  `formula.py` 414 行（基线 411，+3）；新模块 243 行；新测试 212 行。

## 2. 筛选阈值与依据（I3 实测校准）

| 筛选 | 阈值 | 依据 |
|---|---|---|
| 高 | ≤ 45pt | 侦查口径；I3 实测最大 31.8pt |
| 宽 | ≤ 400pt | 侦查口径；I3 实测最大 160.2pt |
| 最小边 | ≥ 3pt | 排除 A2 页眉 0.7×0.7pt 装饰碎片；I3 最小 6.1pt |
| 宽高比 | max(w/h, h/w) ≤ 20 | 排除水印/横线；I3 实测最大 6.33 |
| 题块归属 | 图形中心落在题块矩形内 | 与侦查中心归属一致，避免相邻题块双计 |
| 行重叠 | 中心 y 落在某文字行 `[bottom, top]` 内 | 直接复用 `regions._pdf_text_lines` 的行带 |
| 行内邻接 | 同 y 带、左或右最近文字间隙 ≤ **12pt** | I3 85 张实测：min 0.25 / p50 0.62 / p90 7.74 / **max 7.74pt**；12pt≈1.6 个 10.5pt 汉字宽，兜住空格 |
| 输出最小块 | ≥ 8px（300dpi） | 与 `crop_png` 的 `MIN_SPAN_PX` 一致 |

坐标换算与文字层完全同款：`x=(left-origin_x)*300/72`、
`y=((page_h-top)-origin_y)*300/72`、`w/h` 乘同因子；`origin="inline_bitmap"`。

## 3. 去重规则

- 与已有文字层公式 span **重叠面积 ÷ 候选图面积 ≥ 0.8** 即丢弃，避免同一处既按
  文字 run 又按位图各送一次。
- I3 实测：20 个题块交叉累计 153 个归属，文字层去重 **0** 个（文字 run 与位图不重叠）。
- 与 MinerU 结果不混：MinerU 命中时保持原路径直接返回。

## 4. 真卷探针（只读；`.system_generated/inline-bitmap-formula/probe.toml`）

口径：页图 200dpi 尺寸＋`furniture.filter_pages` 剥页眉页脚＋`_question_regions`
（含墨迹行裁剪）造题块，逐题调用生产 `discover`；唯一命中按页面真实 image object
归属去重（2-up 题块带互相重叠，同一张图会被多个题块各归属一次）。

| 卷 | 页 | 题块 | 唯一命中 | 逐题块归属 |
|---|---|---|---|---|
| **I3** | 2 | 19 | **85**（p1 71 / p2 14） | 153（p1 125 / p2 28） |
| A2 | 12 | 33 | **0** | 0 |
| A3 | 4 | 17 | **0** | 0 |
| D1 | 3 | 0 | **0** | 0 |
| I2 | 2 | 19 | **0** | 0 |
| E2 | 2 | 0 | **0** | 0 |
| C3（普通文字卷对照） | 10 | 18 | **0** | 0 |
| I1（普通文字卷对照） | 12 | 27 | **0** | 0 |

- I3 唯一命中与侦查 85（71/14）完全一致；`attributed=153` 是 2-up 拼版题块带纵向
  互相重叠导致的重复归属（侦查 §5.2 已记录，本卡不修切题）。
- D1/E2 无文字层：模块在 `_text_context` 即返回空；且 triage 根本不会让纯图卷进组合路。

3 个样张（相对题块 bbox / 页图 200dpi 绝对 bbox / 所在行文字）：

| 页 | 题块 | bbox（题块像素@300dpi） | 页 bbox（@200dpi） | 行文字 |
|---|---|---|---|---|
| 1 | p01q01 | [168.6, 0.0, 407.0, 88.0] | [259.7, 388.0, 271.3, 58.7] | 1．集合 ， ，则 （ ） |
| 1 | p01q01 | [619.1, 0.0, 322.5, 132.5] | [560.0, 388.0, 215.0, 88.3] | 1．集合 ， ，则 （ ） |
| 2 | p02q01 | [2409.8, 80.6, 87.5, 75.0] | [1756.0, 262.7, 58.3, 50.0] | 15．在 ΔABC 中，角 A,B,C 所对的边分别为a,b, c ，且 a cos B = b(1+ cos A). |

前两张是题 1 选项里的集合表达式位图（97.7×21.1pt、77.4×31.8pt，与侦查样张同尺寸），
第三张是题 15 题干的行内公式；行文字里公式位置为空白，证明是行内公式而非图片题。

## 5. 失败语义（照旧，未改下游）

- 公式座未就绪 → `mark_pending` 标 `formula_pending`，正文保留文字直取，不整题降级。
- **行内位图没有题干文字锚点**：`replace_fragment()` 既无原串、也无预置 LaTeX，
  即使公式座认出 LaTeX 也无法原位回填；该题最终落「公式待核」并保留文字直取。
  这是「下游不改」的必然结果，回单如实披露；后续若要把 LaTeX 真的插回题面，
  需要按坐标到文字流的定位方案（另卡）。
- 纯图卷：`text_layer=False` 在路由层已拒绝组合路；模块自身也零触发。

## 6. 可下架说明

- 删除 `app/core/ingest/recognize/inline_formula_images.py`；
- 还原 `formula.py:discover_spans()` 末尾两行合并调用与 import 里的一项
  （`_textlayer_spans` 原样返回即可）。
- 无数据库、无配置项、无前端改动；`tools/onnx_probe.py` 原地未 stage。

## 7. 命令与 rc

```
.venv/Scripts/python.exe -m unittest tests.test_inline_formula_images \
  tests.test_ingest_triage tests.test_ingest_routing tests.test_ingest_scan \
  tests.test_ingest_failure_surface tests.test_formula_route \
  tests.test_file_size_contract
→ Ran 127 tests / OK / rc=0

bash scripts/check-quick-gate.sh
→ check-quick-gate: PASS（6 项全过）/ rc=0

.venv/Scripts/python.exe .system_generated/inline-bitmap-formula/probe.py
→ rc=0（计数见 §4，产物 probe.toml）
```

## 8. 未决问题与偏离

- 偏离①：本机 pypdfium2 5.9.0 的 `PdfObject` 无 `.type` 属性、raw
  `FPDFPageObj_GetBounds` 是 5 参数签名。模块主路用高层
  `get_objects(filter=[IMAGE], max_depth=8)`（递归 Form XObject，侦查同款），
  raw `FPDFPage_CountObjects/GetObject/GetObjType` 仅作兜底；I3 实测 raw 顶层与
  deep 枚举例数一致（75/16）。
- 偏离②：I3 的 2-up 题块带纵向重叠，生产按题调用会把同一张图归属给多个题
  （153 次归属 / 85 张唯一图）。修切题超出本卡范围，已在 §4 标明。
- 未验证：任何识别引擎真跑（本卡禁用）、组合路在 I3 上的端到端产物；
  行内位图 LaTeX 目前无法原位回填（见 §5）。

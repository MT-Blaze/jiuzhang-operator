# 文字直取补行内位图公式兜底（inline-bitmap-formula）

状态：收口全绿（底座 2 笔；不 push）
发起日期：2026-11-20
需求来源：主公 2026-11-20 任务卡 #INLINE-BITMAP-FORMULA-01 刀 B——文字直取只拿文字层，行内公式若被做成小位图对象，组合路第二步收不到裁图，公式整体丢失
基线：operator 41546a7（ahead 114，脏件仅 `?? tools/onnx_probe.py`）
依据：`.system_generated/bitmap-formula-recon/`（recon.md / counts.toml / samples）
回单：docs/handoff/receipts/inline-bitmap-formula.md（#INLINE-BITMAP-FORMULA-01）

## [REQ] 2026-11-20

组合路＝文字直取正文＋公式按坐标裁图。文字层里被做成位图对象的行内公式
既无文字、也无公式坐标；侦查实测该盲区只集中在 I3（2 页 85 张，p1 71 / p2 14），
5 份靶卷为 0，D1/E2 是纯图卷（无文字层，本来整页走图像识别）。

## [IMPL] 2026-11-20

- operator `389e8af`（3 files）：
  - 新增 `app/core/ingest/recognize/inline_formula_images.py`（243 行）：image object
    枚举（高层 get_objects 递归＋raw 兜底）、三道筛选（h≤45pt / w≤400pt；中心落
    文字行带；左右邻接 ≤12pt）、排除（最小边 <3pt、宽高比 >20、与文字层 span
    重叠 ≥80%）、pt→题块 300dpi 像素换算、origin=inline_bitmap、稳定排序。
  - 修改 `formula.py:discover_spans`（唯一接入点）：文字层 span 后追加行内位图
    span 并合并；MinerU 优先路径、正文文字直取、`_textlayer_spans` 逻辑不变。
  - 新增 `tests/test_inline_formula_images.py`（20 例）：尺寸边界、行带、邻接、
    四类排除、坐标换算、无文字层、并单与 discover_spans 接入。
- 零改：`normalize_latex`、查重指纹、`question_contract.py`、LICENSE、AGENTS 铁律、
  用户 `data/`；`tools/onnx_probe.py` 未 stage。

## [VERIFY] 2026-11-20

- 定向 7 模块 127/127 OK（inline_formula_images / ingest_triage / ingest_routing /
  ingest_scan / ingest_failure_surface / formula_route / file_size_contract），rc=0。
- 快门禁 PASS（6 项，rc=0）；体积预警与基线相同。
- 真卷探针 `.system_generated/inline-bitmap-formula/probe.toml`：I3 唯一 85
  （71/14）＝侦查值；A2/A3/I2/D1/E2、C3/I1 全 0；3 张样张 bbox＋行文字已回单。
- 已知边界：行内位图在题干里没有文字锚点，识别出的 LaTeX 无法原位回填，落
  「公式待核」并保留文字直取；I3 的 2-up 题块带重叠导致逐题归属 153 次（85 张
  唯一图），修切题另卡。
- 未 push；65496 零接触；工作树提交后仅剩 `?? tools/onnx_probe.py`。

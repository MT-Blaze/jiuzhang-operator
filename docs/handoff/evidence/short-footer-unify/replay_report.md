# 短卷页脚统一卡 #SHORT-FOOTER-UNIFY-01 真卷离线回放报告

- 原件：`E:\15972\Desktop\哈尔滨市第六中学校2026-2027年高三学年阶段性测试（一） 数学.pdf`（只读复制，sha256 `a65347866e545a01cb8633518b907b632ae33bc53582f74328eeaba12f6d6b0f`）
- 隔离目录：`E:\jiuzhang\jiuzhang-operator\.system_generated\short-footer-unify`（JZO_DATA_DIR 同指此处，本机 data/ 零接触）
- 通道：内置 PDFium 渲染＋切框，CPU 离线；零出网零额度零识别引擎零端口
- 判据：**7/7** 通过
- 基线对照：`git show HEAD:app/core/ingest/render/regions.py` 载入改动前模块，同一 kept 行清单、同 ⑥ 调用口径（apply_fallbacks=False）逐字比对

## 逐判据

| 判据 | 结果 | 实测 |
|---|---|---|
| sha256_matches_previous_card | true | a65347866e545a01cb8633518b907b632ae33bc53582f74328eeaba12f6d6b0f |
| render_4_pages_no_warning | true | pages=4 warnings=[] |
| J1a_no_coordinate_drift_vs_head | true | p1:same p2:same p3:same p4:same |
| J1b_page1_boxes_match_previous_evidence | true | r1=(612.0, 196.0)==(612.0,196.0) r2=(801.0, 185.0)==(801.0,185.0) r3=(984.0, 198.0)==(984.0,198.0) r4=(1210.0, 260.0)==(1210.0,260.0) r5=(1464.0, 179.0)==(1464.0,179.0) r6=(1638.0, 191.0)==(1638.0,191.0) |
| J2a_question_chains_and_last_bottoms | true | p1=[1, 2, 3, 4, 5, 6] bottom=1829.0==1829.0 p2=[7, 8, 9, 10, 11] bottom=1845.0==1845.0 p3=[12, 13, 14, 15, 16] bottom=1563.0==1563.0 p4=[17, 18, 19] bottom=1565.0==1565.0 |
| J2b_page4_three_regions_and_lone_two_kept | true | p4_regions=3 q19_tail=['1', '2', 'f s \uf02bt \uf02d \uf03c f s \uf02b f t \uf02d ．'] |
| J3_no_footer_text_in_any_region | true | p1 footers=1 kinds=['regex'] leaked=none p2 footers=1 kinds=['regex'] leaked=none p3 footers=1 kinds=['regex'] leaked=none p4 footers=1 kinds=['regex'] leaked=none |

## 四页全框（新语义）

### 第 1 页

- no=1 x=146.8 y=612.0 w=1137.8 h=196.0 bottom=808.0
- no=2 x=146.8 y=801.0 w=1137.8 h=185.0 bottom=986.0
- no=3 x=146.8 y=984.0 w=1137.8 h=198.0 bottom=1182.0
- no=4 x=146.8 y=1210.0 w=1137.8 h=260.0 bottom=1470.0
- no=5 x=146.8 y=1464.0 w=1137.8 h=179.0 bottom=1643.0
- no=6 x=146.8 y=1638.0 w=1137.8 h=191.0 bottom=1829.0

### 第 2 页

- no=7 x=147.4 y=161.0 w=1138.6 h=251.0 bottom=412.0
- no=8 x=147.4 y=443.0 w=1138.6 h=333.0 bottom=776.0
- no=9 x=147.4 y=811.0 w=1138.6 h=220.0 bottom=1031.0
- no=10 x=147.4 y=1050.0 w=1138.6 h=477.0 bottom=1527.0
- no=11 x=147.4 y=1521.0 w=1138.6 h=324.0 bottom=1845.0

### 第 3 页

- no=12 x=147.5 y=328.0 w=1138.2 h=94.0 bottom=422.0
- no=13 x=147.5 y=475.0 w=1138.2 h=39.0 bottom=514.0
- no=14 x=147.5 y=562.0 w=1138.2 h=337.0 bottom=899.0
- no=15 x=147.5 y=892.0 w=1138.2 h=224.0 bottom=1116.0
- no=16 x=147.5 y=1396.0 w=1138.2 h=167.0 bottom=1563.0

### 第 4 页

- no=17 x=149.7 y=161.0 w=1131.1 h=203.0 bottom=364.0
- no=18 x=149.7 y=691.0 w=1131.1 h=623.0 bottom=1314.0
- no=19 x=149.7 y=1308.0 w=1131.1 h=257.0 bottom=1565.0


# 末题框底方向修正卡⑥ 真卷离线回放报告

- 原件：`E:\15972\Desktop\哈尔滨市第六中学校2026-2027年高三学年阶段性测试（一） 数学.pdf`（只读复制，sha256 `a65347866e545a01cb8633518b907b632ae33bc53582f74328eeaba12f6d6b0f`）
- 隔离目录：`E:\jiuzhang\jiuzhang-operator\.system_generated\last-region-bottom`（JZO_DATA_DIR 同指此处，本机 data/ 零接触）
- 通道：内置 PDFium 渲染＋切框，CPU 离线；零出网零额度零识别引擎零端口
- 判据：**15/15** 通过

## 修前基线（2026-11-20 开工复核，baseline_probe.py 当次实测）

- 第 1 页 region6：y=1638.0 h=171.0 bottom=**1809.0**，压在选项墨迹 1802–1822 上半截
- 选项行「A．13 B．9 C．7 D．3」charbox bottom=72.38 top=79.71（pt）
- 页脚「第 N 页 共 4 页」被全卷剥离（furniture，4 页≥3），单页兜底 apply_fallbacks=False 关闭
- region1–5 (y,h)：(612,196)(801,185)(984,198)(1210,260)(1464,179)

## 修后逐判据

| 判据 | 结果 | 实测 |
|---|---|---|
| render_4_pages_no_warning | true | pages=4 warnings=[] |
| p1_C1_last_bottom_covers_lowest_ink | true | last_bottom=1829.0 ink_bottom=1823 lowest_line='A．13 B．9 C．7 D．3' |
| p1_C2_last_bottom_above_footer | true | last_bottom=1829.0 footer_top_px=1933.5 |
| p1_C5_number_chain | true | regions=[1, 2, 3, 4, 5, 6] max_head=6 |
| p2_C1_last_bottom_covers_lowest_ink | true | last_bottom=1845.0 ink_bottom=1839 lowest_line='\uf02d \uf03c D．设直线 OM 的斜率为k ，则 6' |
| p2_C2_last_bottom_above_footer | true | last_bottom=1845.0 footer_top_px=1933.5 |
| p2_C5_number_chain | true | regions=[7, 8, 9, 10, 11] max_head=11 |
| p3_C1_last_bottom_covers_lowest_ink | true | last_bottom=1563.0 ink_bottom=1557 lowest_line='（2）若sinB \uf02b sinC \uf03d1，求\uf044ABC' |
| p3_C2_last_bottom_above_footer | true | last_bottom=1563.0 footer_top_px=1933.5 |
| p3_C5_number_chain | true | regions=[12, 13, 14, 15, 16] max_head=16 |
| p4_C1_last_bottom_covers_lowest_ink | true | last_bottom=1565.0 ink_bottom=1559 lowest_line='2' |
| p4_C2_last_bottom_above_footer | true | last_bottom=1565.0 footer_top_px=1933.5 |
| p4_C5_number_chain | true | regions=[17, 18, 19] max_head=19 |
| p1_C3_region6_bottom_in_1827_1831 | true | region6 y=1638.0 h=191.0 bottom=1829.0 |
| p1_C4_regions1to5_pinned | true | r1=(612.0,196.0)==(612.0,196.0) r2=(801.0,185.0)==(801.0,185.0) r3=(984.0,198.0)==(984.0,198.0) r4=(1210.0,260.0)==(1210.0,260.0) r5=(1464.0,179.0)==(1464.0,179.0) |

## 修后第 1 页全框

- no=1 y=612.0 h=196.0 bottom=808.0
- no=2 y=801.0 h=185.0 bottom=986.0
- no=3 y=984.0 h=198.0 bottom=1182.0
- no=4 y=1210.0 h=260.0 bottom=1470.0
- no=5 y=1464.0 h=179.0 bottom=1643.0
- no=6 y=1638.0 h=191.0 bottom=1829.0

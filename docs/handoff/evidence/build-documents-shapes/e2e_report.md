# BDP-01 离线端到端报告（产品全接线 service.ingest_files → 待审池）

- 入口：ingest_files（老师拖 .md 的同一同步入口）→ stage → run_jobs → media._items_from_file → build_documents → save_draft → 待审池读回
- 零出网零引擎零端口：.md 判 text，不起服务、不开浏览器、不碰识别/版面引擎
- 隔离底座：data=E:\jiuzhang\jiuzhang-operator\.system_generated\build-documents-shapes\e2e\data plugins=E:\jiuzhang\jiuzhang-operator\.system_generated\build-documents-shapes\e2e\plugins

- 20/20 文件出文档：绿（0 文档题号=[]；池内总文档数=24）

## 7 题修实落池（题号以 stem 头号承载）

| 题号 | 池内文档数 | type | stem 头号 | 选项数 | 形状期望 |
|---|---|---|---|---|---|
| 3 | 1 | single_choice | 3. | 4 | ✓ |
| 6 | 1 | single_choice | 6. | 4 | ✓ |
| 10 | 1 | single_choice | 10. | 4 | ✓ |
| 11 | 1 | single_choice | 11. | 4 | ✓ |
| 13 | 1 | solution | 13. | 0 | ✓ |
| 14 | 1 | fill_blank | 14. | 0 | ✓ |
| 15 | 1 | solution | 15. | 0 | ✓ |

## 对照 13 题落池文档数不回归

| 题号 | 修前文档数 | 池内文档数 | 一致 |
|---|---|---|---|
| 1 | 1 | 1 | ✓ |
| 2 | 1 | 1 | ✓ |
| 4 | 1 | 1 | ✓ |
| 5 | 1 | 1 | ✓ |
| 7 | 1 | 1 | ✓ |
| 8 | 1 | 1 | ✓ |
| 9 | 1 | 1 | ✓ |
| 12 | 1 | 1 | ✓ |
| 16 | 1 | 1 | ✓ |
| 17 | 2 | 2 | ✓ |
| 18 | 2 | 2 | ✓ |
| 19 | 1 | 1 | ✓ |
| 20 | 3 | 3 | ✓ |

## 图片不静默丢（解析边界 warnings 如实登记）

- 题 10 解析边界剥图警告：1 条
  - 题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/8f9fa9825f742e3347e2bf165aee75028af1f50c49ba79e86e6bc348d93f8d50.jpg
- 题 11 解析边界剥图警告：1 条
  - 题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/e68c934ffcac406bbe534e4d4bf67bdc58eaa7e0b70112393d9c425db6d73c7a.jpg
- 池内 route.note 仍带剥图警告的批次数：0（信息性：dedupe 重写 route 为既有接线，非本卡判据）

## 判定

-  failures：无
-  结论：绿（20/20 落池＋7 题形状对＋对照不回归＋剥图如实）

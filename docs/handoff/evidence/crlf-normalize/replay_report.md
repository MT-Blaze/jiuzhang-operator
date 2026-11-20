# crlf-normalize 卡⑤离线回放报告（read_bytes 落池路全接线）

- 入口：夹具真实字节落盘 → read_bytes → data_url → ingest_files →
  media._items_from_file → decode_text（归一 LF）→ build_documents →
  shapes.normalize → 落池 → dedupe（启用态真跑，join 后读回）
- 隔离底座：data=E:\jiuzhang\jiuzhang-operator\.system_generated\crlf-normalize\e2e\data plugins=E:\jiuzhang\jiuzhang-operator\.system_generated\crlf-normalize\e2e\plugins
- 夹具字节：E:\jiuzhang\jiuzhang-operator\.system_generated\crlf-normalize\e2e\fixtures

## 池内 route.note 实测

- lf_warn.md（batch=B-001）：note='题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/header_photo.jpg'；题目数=1
- crlf_warn.md（batch=B-002）：note='题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/header_photo.jpg'；题目数=1
- cr_warn.md（batch=B-003）：note='题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/header_photo.jpg'；题目数=1
- crlf_plain.md（batch=B-004）：note=''；题目数=1

## decode_text 边界对照（治后口径）

- CRLF 字节经 decode_text 逐字等于 LF 原文：True
- lone \r 字节经 decode_text 逐字等于 LF 原文：True
- 归一后 shapes.normalize：警告 1 条，图片行被剥=是

## 判据

- crlf_note_has_warning: PASS
- crlf_warning_exactly_one: PASS
- cr_note_has_warning: PASS
- cr_warning_exactly_one: PASS
- lf_note_has_warning: PASS
- crlf_note_equals_lf: PASS
- cr_note_equals_lf: PASS
- crlf_questions_equal_lf: PASS
- cr_questions_equal_lf: PASS
- plain_note_empty: PASS
- decode_crlf_verbatim_lf: PASS
- decode_cr_verbatim_lf: PASS
- shapes_strips_after_decode: PASS
- crlf_one_question: PASS
- cr_one_question: PASS

**passed/total = 15/15**


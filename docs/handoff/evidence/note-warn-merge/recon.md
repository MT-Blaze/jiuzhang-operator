# note-warn-merge 侦查定案（§1 落点全录＋冲掉点证伪）

日期：2026-11-20 ｜ 基线：operator `2d744b8`（ahead 67）／plugins `1083f4a`（ahead 19，editor 2.23.1）
卡：`E:\jiuzhang\剥图警告保合并小刀卡.md` ｜ 前序：BDP-01（build-documents-shapes）收口披露观察项

## 结论（先说）

**卡面病根「落池后 dedupe 重写 route.note 把警告冲掉」在当前代码里不存在。**
全接线离线回放（dedupe 抽走启用态）实证：LF 带卷首图夹具的剥图警告**完整存活**到池内
route.note；每批 route 写盘**只有一笔**（save_route），dedupe 族零 route 写。
BDP-01 e2e 观察到「池内 route.note 带剥图警告批次数=0」的真根因是**CRLF 行尾**：
那 20 份 wire 夹具是 CRLF，产品 decode_text 不做换行归一，shapes 的卷首图行正则
行尾不认 `\r` → 图片行根本没被剥、警告根本没产——不是产了被冲掉。
BDP 边界对照用的是 `read_text`（通用换行转 LF），所以边界有警告、池内没有，
差距被误记到 dedupe 头上。CRLF 修复落点（decode_text / shapes 正则）全在卡 §4
冻结面（shapes.py/text.py 解析逻辑一字不动）→ **按卡 §5 停链报枢纽，§2 刀不下**。

## §1 要求：note 重写点全录（带行号）

route_json 全仓写点只有两处（grep `set_batch_route|route_json` 实测）：

| 写点 | 位置 | 语义 |
|---|---|---|
| `save_route` | `app/core/ingest/route.py:49-64`（写盘在 :62） | ingest 唯一 route 落盘口；只保全 failures/progress，note 随快照原样写 |
| `reidentify` | `app/core/ingest/recognize/reidentify.py:39` | 打回重认路，非本卡 ingest_files→dedupe 范围 |

note 键的赋值/追加点（grep `["note"] =` 实测，全在 ingest 族）：

- `route.py:45` route_payload 初始 note（扫描件/乱码提示）
- `route.py:168` append_notes——**追加合并**（既有 note＋" "＋新 notes），shapes 警告唯一入口
- `route.py:329-339` scan_route 重建计划 note（版面＋识别＋无文本层＋乱码＋闸口）
- `route.py:390` fill_scan_batch 空批追加「没切出题目」
- `recognize/router.py:104-247` 识别汇总重写 note（扫描路逐题/整批收口）
- `recognize/{mineru.py:48-66, mineru_local.py:194-203, vlm_local.py:135-144, formula.py:356}` 进度 note

**pending dedupe 族（pending/dedupe/{engine,compare,groups}.py、pending/pool/service.py、
pending/batch/{batches,bank_batches}.py）对 note/route_json 零写**：
grep `note|route` 在 pool/ 零命中；dedupe 链 `warm_dedupe_scan → warm_batch_scan →
admit_into_pool → pool.admit_from_scan`（engine.py:717-786、pool/service.py:248-369）
只写 dedupe_scans/dedupe_findings/duplicate_pool 与 refresh_batch 未审数，不碰 route_json。

文本路警告流向（shapes 警告只走这条）：
`shapes.normalize（shapes.py:114-128）→ build_documents（text.py:373-374）→
media._items_from_file（media.py:82-83）→ run_ingest_jobs notes（service.py:284）→
append_notes(route, notes)（service.py:375）→ save_draft（service.py:389，起 dedupe 线程）→
save_route（service.py:400）`。save_draft 与 dedupe 线程都不写 route，note 无第二笔重写。

相邻观察（非本卡范围，登记不动）：扫描路 `fill_scan_batch` 内 `scan_route` 重建
（route.py:379）会丢 service.py:310 先 append 的 notes——但 PDF page_only 分支
notes 恒为空（service.py:274-275 不走 _items_from_file），今日无实际损失；
且属「其余 note 语义」冻结面，本卡不碰。

## 回放实证（replay_note_warn.py ＋ replay_report.md）

自包含探针，三路全接线 `service.ingest_files`（老师拖 .md 同一同步入口），
dedupe 抽走**启用态**（未设 JZO_POOL_ADMIT_DISABLED），后台 jzo-dedupe-warm 线程
join 后再读池；给 `pending.service.set_batch_route` 打桩录每笔写盘 note＋调用栈。
隔离 JZO_DATA_DIR/JZO_PLUGINS_DIR 进 .system_generated/note-warn-merge/e2e＋最小目录夹具插件。

| 夹具 | 池内 route.note | 含剥图警告 | route 写盘笔数 |
|---|---|---|---|
| LF 带卷首图行 | `题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/header_photo.jpg` | 是 | 1 |
| CRLF 同文 | `''` | 否 | 1 |
| LF 无图 | `''` | 否（基线） | 1 |

三笔写盘调用栈全部是 `service.py:400 → route.py:62`，无 dedupe 栈帧。

边界对照：
- `shapes.normalize(LF 文本)` → 警告 1 条，图片行被剥。
- `shapes.normalize(decode_text(CRLF 字节))` → 警告 0 条，图片行原样留存。
- 根因链：`decode_text`（text.py:117-124）逐编码尝试直接 return，不做换行归一 →
  `\r` 原样进解析；`_IMAGE_LINE`（shapes.py:37）`^[ \t]*!\[[^\]]*\]\([^)]*\)[ \t]*$`
  行尾只认空格/Tab，`\r` 不在其中 → CRLF 图片行不匹配 → 不剥、不产警告。
  （normalize 对 CRLF 文本仍有改写，那是文末选项并段 `_rejoin_terminal_options`
  的 `\s` 切段认 `\r`，与剥图无关。）

## BDP-01 误归因还原

BDP e2e（docs/handoff/evidence/build-documents-shapes/e2e_ingest.py）：
- 落池路 :67 用 `read_bytes`（CRLF 原样）→ data_url → 产品 decode_text → 无警告 → note 空；
- 边界对照 :137 用 `read_text`（通用换行转 LF）→ shapes 剥行产警告；
- 两边口径差一个换行归一，观察到的「池内 0 批次带警告」被 :132-133 注释误归因
  为「dedupe 用新快照重写 route」。本探针打桩实证：route 每批只写一笔，dedupe 零写。

## 停链依据与下一棒建议（需主公拍板）

卡 §5：「冲掉点找不到＝停链报枢纽」。本卡 §2 刀（note 重写改合并）**不下**：
无冲掉点可治；若在 save_route 做通用 note 合并反而改「其余 note 语义」（§4 冻结），
且扫描路 note 按阶段重写是既有设计，通用合并会弄坏它。

真欠账＝CRLF 卷首图行不剥不警告（老师拖 Windows 记事本存的 .md/.txt 就中招）。
修复落点二选一，都在本卡冻结面，须另卡解冻：
1. **decode_text 边界归一换行**（text.py:117-124，CRLF→LF 单源）——推荐：一处治全部
   行尾敏感正则，docx/OCR 路不受影响（它们自产 \n）；但会改 CRLF 文件的解析行为
   （图片行开始被剥、选项并段口径微变），属解析逻辑变更，需契约级回归。
2. shapes._IMAGE_LINE 行尾容忍 `\r`（shapes.py:37）——只治剥图一行，其余行尾敏感
   形状（_SPLIT_NUM 等）仍漏；不推荐。

本卡交付：侦查证据（本目录）＋回归钉死用例（tests/test_note_warn_merge.py，
LF 警告存活／无警告 note 逐字不变／dedupe 启用态单笔写盘／CRLF 现状 Canary）＋回单。
生产代码零改；插件零改（parity 持现版 2.23.1，zip 不重打）；前端零改（免真测）。
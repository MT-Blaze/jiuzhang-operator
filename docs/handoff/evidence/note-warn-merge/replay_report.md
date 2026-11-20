# note-warn-merge 侦查回放报告（全接线 service.ingest_files）

- 入口：ingest_files → stage_ingest → run_ingest_jobs → media._items_from_file
  → build_documents → shapes.normalize → pending.save_draft → 待审池读回
- dedupe 抽走**启用态**（未设 JZO_POOL_ADMIT_DISABLED），后台初查线程 join 后再读
- 隔离底座：data=E:\jiuzhang\jiuzhang-operator\.system_generated\note-warn-merge\e2e\data plugins=E:\jiuzhang\jiuzhang-operator\.system_generated\note-warn-merge\e2e\plugins

## 池内 route.note 实测

- LF 带卷首图（batch=B-001）：note='题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/header_photo.jpg'
  - 含剥图警告：是；route 写盘笔数=1
- CRLF 同文（batch=B-002）：note=''
  - 含剥图警告：否；route 写盘笔数=1
- LF 无图（batch=B-003）：note=''；route 写盘笔数=1

## shapes.normalize 边界对照（警告来源口径）

- LF 文本直喂：警告 1 条，图片行被剥=是
- CRLF 经产品 decode_text：警告 0 条，图片行原样留存=是（剥行未生效；normalize 若改写文本只是文末选项并段，与剥图无关）
- 口径：decode_text（text.py:117-124）不做换行归一，\r 原样进解析；
  shapes._IMAGE_LINE（shapes.py:37）行尾只认 `[ \t]*$`，\r 不在其中 → CRLF 图片行不匹配。

## set_batch_route 全部写盘记录（含调用栈）

--- write batch=B-001 note='题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：images/header_photo.jpg'
  File "E:\Python314\Lib\asyncio\events.py", line 94, in _run
    self._context.run(self._callback, *self._args)
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\service.py", line 91, in ingest_files
    await run_ingest_jobs(group["batch_id"], group["jobs"],
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\service.py", line 400, in run_ingest_jobs
    save_route(service, batch_id, attach_surface(route, ledger))
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\route.py", line 62, in save_route
    service.set_batch_route(batch_id, route)

--- write batch=B-002 note=''
  File "E:\Python314\Lib\asyncio\events.py", line 94, in _run
    self._context.run(self._callback, *self._args)
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\service.py", line 91, in ingest_files
    await run_ingest_jobs(group["batch_id"], group["jobs"],
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\service.py", line 400, in run_ingest_jobs
    save_route(service, batch_id, attach_surface(route, ledger))
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\route.py", line 62, in save_route
    service.set_batch_route(batch_id, route)

--- write batch=B-003 note=''
  File "E:\Python314\Lib\asyncio\events.py", line 94, in _run
    self._context.run(self._callback, *self._args)
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\service.py", line 91, in ingest_files
    await run_ingest_jobs(group["batch_id"], group["jobs"],
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\service.py", line 400, in run_ingest_jobs
    save_route(service, batch_id, attach_surface(route, ledger))
  File "E:\jiuzhang\jiuzhang-operator\app\core\ingest\route.py", line 62, in save_route
    service.set_batch_route(batch_id, route)


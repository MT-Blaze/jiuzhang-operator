# MinerU 云端整批提速 · §1 侦查证据（2026-11-20）

## 1. 官方批量上限（文档核，免费合法链）

来源：MinerU 官方接口文档 <https://mineru.net/apiManage/docs>（页面自标 dateModified 2026-04-01；
本会话 2026-11-20 抓取，全文存档见同目录 `official-docs-excerpt.md`）。

逐字关键句：

- 「本地文件批量上传解析」接口说明：**「单次申请链接不能超过 50 个」**。
- 同页「模式对比」总表却写「批量支持 ✅ 支持（≤ 200 个）」——**官方页内自相矛盾**。
- 「文件限制」表：文件大小上限 **200 MB**、文件页数上限 **200 页**（总表与接口节一致；
  二手博客「600 页/200 个/每日 2000 页」口径与官方现行页不符，不采）。
- 单文件接口节：「每个账号每天享有 **1000 页**最高优先级解析额度，超过 1000 页的部分优先级降低」。
- 「上传文件时，**无须设置 Content-Type 请求头**」——与 mineru-put-fix 的线上零 Content-Type 铁口径互证。
- 「文件上传完成后，无须调用提交解析任务接口。系统会自动扫描已上传完成文件自动提交解析任务」。
- 「申请的文件上传链接有效期为 **24 小时**」。
- `data_id`：「由大小写英文字母、数字、下划线（_）、短划线（-）、英文句号（.）组成，不超过 128 个字符」。

**定案**：批量上限取接口节逐字口径 **≤50 份/次 POST**（对总表 200 取保守侧）；
实现常量 `BATCH_MAX_FILES = 50`，超出按 50 切_chunk_ 逐批走同一流程（调用方视角仍是一次整批）。
单题截图 1 页/份，远低于 200MB/200 页，页数帽不构成约束。
官方页内 50 vs 200 矛盾如实登记（见 §4 欠账），不编数。

## 2. 批量响应形状复核（现有 wire 存档）

存档：`.system_generated/typst-bench/wire/mineru_wire_fix.md`（2026-11-19 修复后 20 题逐题真跑，全 ok=True）。

- POST `file-urls/batch` → `data.batch_id`＋`data.file_urls[]`；官方 Python 示例
  `for i in range(0, len(urls)): open(file_path[i])` ＝ **file_urls 与 files 按下标一一对应**（顺序即映射）。
- GET `extract-results/batch/{batch_id}` → `data.extract_result[]`，官方参数表列明每行字段：
  `file_name / state / full_zip_url / err_msg / data_id / extract_progress{extracted_pages,total_pages,start_time}`；
  「如果在解析请求参数中传入了 data_id，则此处返回对应的 data_id」。
- state 枚举（官方逐字）：`done / waiting-file / pending / running / failed / converting`。
  wire 存档实测观察到 `waiting-file → pending → running → done` 完整迁移（如 batch 306a5f0c 行 jzo-49c6b0e8）。
  终态只认 `done` 与 `failed`（兼容旧码的 `error`）；`converting/waiting-file/pending/running` 继续等。
- wire 实证：轮询 URL 里的 batch_id（如 cd93a684-…）与 OSS 上传路径首段 UUID 一致；
  done 行 `full_zip_url` 指向 cdn-mineru.openxlab.org.cn 的 zip，包内 `full.md` 即 Markdown（已逐字落 full_md_fix_01..20.md）。
- **一次真微批回执核**：本卡 §5 真测（3–5 题整批）将录一次 N 份同批回执，逐字段复核后补记于本目录
  `live-receipt-check.md`；侦查阶段先以官方参数表＋单份 wire 实证为据。

## 3. 时限语义定案

- 整批 deadline 沿用单题 **900s** 口径（mineru_extract.MAX_WAIT_SECONDS），从整批轮询起点计时，
  作为**整批上限**而非每题各 900s。
- 到点：**已 done 的行照回填**（含到点前已拿到 zip 的）；未 done 的行**逐题显性失败账本**
  （detail 带最后状态），**不整批作废**。
- 轮询节奏沿用 POLL_SECONDS=2.0；单轮询循环按 data_id 认行，题↔结果映射、逐题失败账本、
  逐题进度三样保住（mineru_extract.py:145-149 现成底子）。
- 轮询请求本身失败（网络/HTTP 错）：整批显性失败返回（与单题 extract 的「查询结果失败」口径一致），
  已到手的 done 行仍先取回填入 outcome，不丢已得结果。

## 4. 欠账登记

- 官方文档页内「≤50（接口节）vs ≤200（总表）」矛盾：取 50 保守实现；待官方澄清后可放宽，不阻塞本卡。
- 二手来源（CSDN/博客）「600 页、200 个、2000 页/日」与官方现行页不一致，一律不采、不引为据。
# MinerU 云整批 · §1.2 一次真微批回执核（2026-11-20）

侦查阶段（`recon.md` §2）以官方参数表＋单份 wire 存档为据；本文件按卡 §1.2 要求，
用 §5 真测的**一次 N 份同批真回执**逐字段复核批量响应形状，核对无误后补记于此。

证据出处：`docs/handoff/evidence/mineru-batch-live/run4/`（probe.toml ok=True，19/19 绿，113.5s）。
- `wireA.toml`：顺风整批 4 题（batch_id `30ca2ccc-9cd6-47d4-9b69-8ee6a5cef22d`）。
- `wireB.toml`：失败注入整批 4 题（坏图最后一份，runB_batch B-002）。
- wiretap＝`wiretap_sitecustomize.py` 导入钩子包 `mineru_extract._request/_put_raw`
  与 `mineru._progress`，**只观测＋委托 HEAD 原函数**，批量逻辑一字不动。
  探针运行时落 JSONL 于 `.system_generated/`（gitignore），交付证据按禁 JSON 落盘口径转 TOML（`[[exchanges]]`）。
- 真机隔离副本 git archive HEAD：operator `8cd8b208`／plugins `1083f4a3`；
  云账号只读复制用户 MinerU 绑定（acc_7ae191d903）进隔离 data，禁碰用户 data/。

## 1. POST file-urls/batch 申请整批上传地址

官方（`official-docs-excerpt.md` lines 146/471）：`code==0` → `data.batch_id`＋`data.file_urls[]`，
官方 Python 示例 `for i in range(0, len(urls)): open(file_path[i])` ⇒ **file_urls 与 files 按下标一一对应**。

真回执（wireA POST 行）：
- url＝`https://mineru.net/api/v4/file-urls/batch`，method＝POST。
- payload.files＝4 份，data_id 逐字 `jzo-0-d4e2e522 / jzo-1-424dd7eb / jzo-2-d3b81193 / jzo-3-6406626a`，
  model_version＝`vlm`，enable_formula＝true，language＝ch。
- 响应 `batch_id＝30ca2ccc-9cd6-47d4-9b69-8ee6a5cef22d`，`file_urls_n＝4`（与 files 数相符）。
- **一次 POST 申请整批 4 份地址**（posts＝1），不是逐题各申请一次。核：与官方形状一致。

## 2. PUT 上传（零 Content-Type 铁口径）

官方（line 139）：「上传文件时，无须设置 Content-Type 请求头」。

真回执（wireA `_put_raw`×4）：四份 PUT 到 `mineru.oss-cn-shanghai.aliyuncs.com/api-upload/extract/2026-11-20/<batch_id>/<uuid>.png`
签名地址，body_len 逐字 294305／254821／429342／143466，file_index 0/1/2/3，**ok 全 true**（puts_ok＝4）。
OSS 签名不含 Content-Type，带任何值都 403 SignatureDoesNotMatch；**OSS 回 200 即证零 Content-Type**。
并行 PUT（线程池上限 4）实收顺序 file_index 3→1→0→2（as_completed），与入参下标映射不错位。核：一致。

## 3. GET extract-results/batch/{batch_id} 单轮询认行

官方参数表（lines 412-467）每行字段：`file_name / state / full_zip_url / err_msg / data_id /
extract_progress{extracted_pages,total_pages,start_time}`；state 枚举（line 418 逐字）：
`done / waiting-file / pending / running / failed / converting`；「传入 data_id 则返回对应 data_id」（line 443）。

真回执（wireA 轮询行）：
- 轮询 url 末段 batch_id 与 POST 返回一致，**全程一个 batch_id**（poll_batch_ids 唯一）。
- 每行带 `data_id`（回显 jzo-N-xxxx）／`state`／`err_msg`；wiretap 录映射三关键字段。
- state 迁移实测计数：`pending`×38 → `running`×3 → `done`×7（4 题各 done，多轮轮询累计），
  与官方枚举一致；终态只认 done/failed，pending/running 继续等。
- `full_zip_url` 由 done 行取回（见 §4）；`file_name/extract_progress` 官方表列明、本探针只录映射关键字段，
  不影响题↔结果对应（按 data_id 认行，不靠 file_name）。核：形状一致，映射按 data_id 钉死。

## 4. done 行取 zip → full.md

官方（line 426）：full_zip_url 指向 zip，包内 `full.md` 为 Markdown 解析结果。

真回执（wireA `_request` GET×4）：四份 zip 自 `cdn-mineru.openxlab.org.cn/pdf/2026-11-20/<uuid>.zip`
取回，resp_bytes 逐字 59064／118056／101242／173735；解包取 full.md → build_documents → merge_local → save_back，
路由注记「MinerU 逐题解析完成：4/4 道回填成功。」，failures 空，4 题题干长度 157/142/112/133 均非空。核：一致。

## 5. failed 行逐份 err_msg（失败注入实证）

官方（line 434）：err_msg「解析失败原因，当 state=failed 时有效」；官方示例值「文件格式不支持，请上传符合要求的文件类型」。

真回执（wireB）：控制文件 corrupt_last 把最后一份 PUT body 换坏字节（body_len＝23，corrupted＝true，
file_index＝3），**OSS 仍回 200**（坏字节照上传）→ MinerU 解析该行返 `state＝failed`，
`data_id＝jzo-3-33b9eed9`，`err_msg＝unsupported file type`（与官方「文件格式不支持」语义一致，英文变体）。
- 该 failed 行**无 full_zip_url**（wireB zip 只有 3 份），逐份 outcome `{ok:False, detail:"MinerU 解析失败：unsupported file type"}`。
- 其余 3 份 done 照回填（3 份 zip），路由「只有 3/4 道回来了…1 道保持本地切图」，failures 1 条聚合账本（retryable）。
- 逐题 transient 注记（mineru._progress 录，progress_writes＝24）：「第 4/4 题 MinerU 没成功（MinerU 解析失败：unsupported file type），继续下一题。」
- 失败不级联不偷换不降级；失败清单 UI 徽标＋点开 ed-fail-item 可见（runB-failure-list.png）。核：一致。

## 6. 时限语义实证

整批共用 900s 上限（MAX_WAIT_SECONDS），单轮询循环按 data_id 认行；到点已 done 照回填、未 done 逐题显性失败。
本次两批均在远小于 900s 内全结算（run4 全程 113.5s），未触到点分支；到点部分回填分支由
`tests/test_mineru_batch.py` 假时钟钉死（§4）。进度「已回 N/M 题」真出现（Run A 0/4→3/4；Run B 0/4→1/4→2/4→3/4 截图）。核：一致。

## 7. 额度实耗如实披露

每份单题截图＝1 页。canonical 绿跑 run4：两批共提交 8 页，成功解析 7 页（坏图 1 页 failed）。
前序调试跑亦真耗云额度（run1 RunA 4 页；run2 两批 8 页；run3 两批 8 页），合计本卡真测共提交约 28 页、成功解析约 24 页，
远低于官方每日 1000 页最高优先级额度（line 114）。坏图注入页计入提交但不计成功解析。

## 结论

批量响应形状（POST batch_id/file_urls 下标映射、PUT 零 Content-Type、单 batch_id 轮询 data_id 认行、
state 枚举迁移、done→full_zip_url→full.md、failed→err_msg 逐份账本）与官方参数表＋示例**逐字段核对一致**；
题↔结果映射、逐题失败账本、逐题进度三样保住不变粗。侦查 §2 形状定案经真微批回执核确认无误。
官方页内「≤50 vs ≤200」矛盾欠账照挂（recon.md §4），不阻塞。
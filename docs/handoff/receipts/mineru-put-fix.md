# 回执 · MinerU 云上传修实＋L2 复测（mineru-put-fix）

【回执编号】MPF-01（mineru-put-fix）
【回执时间】2026-11-19 19:13:00+08:00
【执行结果】部分成功——上传链病根已治并真证（403→200）；L2 复测 13/20 回填＝按卡口径红（部分回填如实报数）；剩余 7 题缺口在解析段，超卡范围停报；§5 双吐按门禁未跑
【基线】operator 0e5f7cc → 修实 commit **e49606a**；plugins **87e1729 零写入**
【枢纽】aa2dcda2-9e43-40d6-82ec-6b82c6cacb03（Typst替代LaTeX可行性）
【证据根】`E:\jiuzhang\jiuzhang-operator\.system_generated\typst-bench\`（git-ignored）

---

## 三桶总览

**做了什么**：§1 同签名 URL 双 PUT 直调真证根因 → §2 修 raw PUT 线上零 Content-Type → §3 新增线上头契约测试＋定向回归＋快门禁 → §4 git archive 隔离宿主 host2 界面真点 L2 复测 → 13/20 红，取证剩余 7 题后按 §8 停 → 收口。

**改了哪些**：operator 两文件（修实＋测试，commit e49606a）＋本回单＋biz 记录（docs commit 另计）。plugins 仓零改动。宿主版本持 1.2.0、parity 持 2.21.0、zip 不重打。

**成没成**：上传链修实＝成（§1 A=403/B=200 真证；L2 产品路 20/20 PUT 200、20/20 extract ok）。L2 整卷绿＝没成（13/20 回填、failures 1 条）。§5 双吐＝未跑（门禁）。遗留与需拍板见第五节。

---

## 一、改动清单（带行号）

- 修改：`app/core/ingest/recognize/mineru_extract.py`
  - :16-23 imports 增 `http.client`、`urllib.parse`；
  - `_request`（:39-52）删 `raw` 参数与 `Content-Type: application/octet-stream` 分支（原 :49-50 病根），POST JSON 分支 `application/json` 原样不动；
  - 新增 `_put_raw`（:55-75）：http.client 直发 PUT，线上零 Content-Type，签名 query 原样透传（urlsplit path+query），非 2xx 抛 HTTPError 复用既有失败口径；
  - `extract` PUT 段（:124-128）改调 `_put_raw`，except 增 `http.client.HTTPException`。
  - 行数 157→178（引擎 ≤400 ✓）。
- 新增：`tests/test_mineru_extract.py` ×1（6 用例：本机回环实收头断言 raw PUT 零 Content-Type／urllib 自动补头可被抓／签名 query 不被污染／POST JSON 仍带 application/json／全流程线上契约／403 失败不泄签名）。
- 新增（证据，git-ignored，不进 git）：`fix_diag.py`、`fix_host2_setup.py`、`fix_host2_launch.py`、`fix_l2_probe.py`、`fix_dual_probe.py`（备未跑）、`fix_render_probe.py`（备未跑）、`probe_instrument2/sitecustomize.py`、`wire/fix_diag.md`、`wire/fix_l2_diag.md`、`wire/mineru_wire_fix.md`、`wire/full_md_fix_01..20.md`、`wire/hook_fix.md`、`fix_l2.toml`、`run2.toml`、`shots/fix_01..03`、`host2/`、`plugins2/`、`data2/`、`server2.*.log`。
- 禁改区自查：LICENSE 否／AGENTS 铁律一二 否／question_contract.py 否／用户 data/ 否（data2 是 bench 隔离 data 的副本，bench data 系 run1 只读复制产物；本卡未触用户 data/ 一字节）。

## 二、包结构自检

本次不涉及插件改动。plugins2 为 plugins 87e1729 `git archive` 只读导出（editor＋bank-engine，补齐 run1 bank-engine 500 缺口）；plugins 仓 HEAD 仍 87e1729，未跟踪件 model_prefs.toml／models/ 原样未碰。parity 持 2.21.0，zip 不重打（哈希持 87e1729 封版值）。

## 三、三查结果

本次零插件代码改动，三查不适用（host2 插件为封版 archive 原样）。宿主侧改动仅 mineru_extract.py＋新测试，无前端改动、无新请求 id。

## 四、测试与探针（数字均当次实测）

单测（解释器 `.venv\Scripts\python.exe`，逐模块 unittest，禁 pytest/discover）：

| 模块 | 结果 |
|---|---|
| tests.test_mineru_extract（新增） | 6/6 OK |
| tests.test_mineru_service | 11/11 OK |
| tests.test_mineru_setup | 19/19 OK |
| tests.test_mineru_local_run | 17/17 OK |
| tests.test_version_consistency | 29/29 OK |
| tests.test_ingest_routing（触及 mineru_extract，自查补跑） | 10/10 OK |
| tests.test_ingest_triage（同上） | 21/21 OK |

合计 **113/113 绿**。快门禁 `bash scripts/check-quick-gate.sh`＝**PASS（6 项全过）**；WARN 23 份体积预警均既有基线，mineru_extract.py 178 行不在列。全量回归豁免（常设裁决，AGENTS §7 点名除外）。

§1 诊断（直调，卡面显性授权）：POST file-urls/batch 1 次 code 0；同 URL PUT A（带 octet-stream）＝**403 SignatureDoesNotMatch EC 0002-00000040**，StringToSign 第三行正是该头；PUT B（http.client 直发）＝**200**，send 钩子逐字录得出网头确无 Content-Type。urllib 自动补头陷阱本机回环实证（无显式头→实收 `application/x-www-form-urlencoded`），零额外外网腿。证据 `wire/fix_diag.md`（签名 query/Signature 值已 mask）。

§4 L2 复测（隔离宿主·界面真点·产品路径）：
- host2＝`git archive e49606a`（禁抄工作树 ✓）；plugins2＝`git archive 87e1729`；data2＝bench data 副本；动态端口 **4863**＋secrets 随机令牌（run2.toml）。
- 钩子 v2 披露：`probe_instrument2/sitecustomize.py` 纯内存包装 `_request/_put_raw/_pick_markdown/extract`＋client，落 wire/*_fix.md；产品文件零改动，宿主杀即恢复。
- Playwright 穿沙箱真点：上传纯图卷3页.pdf → 选 mineru 云席 → 解析。座位确认 Mineru+mineru ready=true（shots/fix_01）。
- 结果：ingest 201；收口墙钟 **422.4s**（1500s 限内）；20/20 POST code 0；**20/20 OSS PUT 200**；20/20 extract ok=True；20 份 full.md 逐字在 wire。
- **路由 note「只有 13/20 道回来了」＋failures 1 条（step=识别·MinerU，retryable=true）＝按卡绿口径红**。回填 stem 与 run1 B-003 本地切图 stem 逐位比对 13 道全不同＝真回填零冒充（fix_l2.toml）。页面零 JS 异常；HTTP 失败仅既有 MinerU /models 探针形状 404。
- 剩余 7 题（3/6/10/11/13/14/15）取证：MinerU 转写正确，本机只读直调 build_documents 复核 7 份全 0 文档（对照题 1/2 各 1 文档）；形状四类见 `wire/fix_l2_diag.md`。**缺口在 markdown→题目解析段，超本卡上传链范围，未修。**
- 截图：`shots/fix_01-seats.png`、`fix_02-l2-batches.png`、`fix_03-l2-review.png`（1920x1080）。

§5 双吐：**未跑**（§4 红门禁）。fix_dual_probe.py／fix_render_probe.py 备好留档，调用 0 次，零新 pip。

## 五、未决问题与偏离（需拍板）

1. **需拍板·另卡**：build_documents 对 MinerU markdown 四类形状零解析（选项独立成行／卷首图片行／整题 $$ 包裹＋题号拆字／填空 \_\_\_\_），致 7/20 保持本地切图。上传链已绿，此为解析覆盖面缺口，建议另卡治（范围 app/core/ingest 解析段）。
2. **需拍板·§5 续跑**：双吐门禁原意是「MinerU 云路修绿」；上传链已修绿但整卷回填未全绿。是否放行 §5（脚本已备），枢纽裁。
3. **偏离·额度账**：卡面「本腿 3 页」按源 PDF 页数计；产品逐题路实传 20 张单题切图各 1 页＝20 页，加 §1 探针 1 页＝**21 页**（1000 页/日额度内）。如实披露，非 3 页。
4. **偏离·§1 额度**：B 腿 200 触发该 1 页解析（8s 时 pending），卡面已预见，计 1 页。
5. **解释性口径·版本**：宿主 `__version__` 历史仅封版升（c1a6ff6 升 1.2.0 后，2.20.0/2.21.0 卡均未动）；本卡修实非发版 → **持 1.2.0**，test_version_consistency 29/29 绿佐证；parity 2.21.0 为插件索引口径，与宿主版本两轨，zip 不重打。
6. **解释性口径·L1**：不重跑（run1 已绿、修不触 OCR 路径），卡面指定。
7. 既有欠账沿用：MinerU /models 探针形状 404（run1 已登记，本卡未治）；65496 旧进程本卡零接触。
8. 未验证：7 题解析缺口的修复方案（超范围未动）；双吐对照事实（门禁未跑）。

## 六、§7 红线自查（逐项）

- 用户 data/ 零字节 ✓（data2 系 bench 隔离副本之副本）
- 65496 只读 GET、禁重启禁杀 ✓（本卡零接触）
- MinerU 本地 CPU 逐题停跑令 ✓（未跑任何本地 MinerU，不装不卸）
- 出网仅列账腿 ✓：§1 POST×1＋PUT×2＋GET×1（额度账）；§4 界面点击发起 POST×20＋PUT×20＋轮询 GET＋zip 下载×20；§5 零；无账外腿
- 微批 3–5 ✓（L2 整卷为卡指定例外；§5 备 3 张未跑）
- 动态端口＋随机令牌 ✓（4863＋secrets.token_urlsafe(24)，未写死）
- Playwright 穿沙箱 ✓（frame_locator 真点）
- 收口 ✓：stop2.signal→CTRL_BREAK（rc=3）；端口 4863 复验 0 监听；孤儿零（python 仅 65496 正式服务，chromium 0）；taskkill /PID /T 安全网备而未用
- tools/onnx_probe.py 与 plugins 未跟踪件不删不挪不 stage ✓（git status 原样）；engines/ 产物不 stage ✓
- LICENSE／根 agents.md／AGENTS 铁律一二／question_contract.py 禁改 ✓
- 500 行红线／引擎 ≤400／分层 ≤3 ✓（178 行；app/ 零新目录）
- 禁嵌套、禁自回用户 ✓（根会话直跑，回单交枢纽 supervise）
- key 全 mask ✓（fix_diag.md 签名 query/Signature/OSSAccessKeyId 已 mask；wire 钩子同口径；.env 只读内存态）
- JSON 禁落盘 ✓（状态/证据全 TOML/MD；API 应答仅内存解析）
- 两仓禁 push ✓（hold；operator ahead 待授权，plugins 零 commit）

## 七、git

- operator：e49606a（修实＋测试，定向 113/113 绿＋快门禁 PASS 后 commit）；回单＋biz docs commit 另计（见 git log）。stage 逐个点名，未用 add -A；不 amend 不改写历史。
- plugins：零 commit 零 stage 零 push，HEAD 87e1729。
- 两仓 push 均 hold 待主公授权。

## 八、证据索引

- 总账：`fix_l2.toml`（L2 九项 check 8 绿 1 红）；`run2.toml`（宿主参数）
- 诊断：`wire/fix_diag.md`（双 PUT 逐字＋出网头＋urllib 陷阱）
- L2 流水：`wire/mineru_wire_fix.md`（20 题全请求＋状态机）；`wire/full_md_fix_01..20.md`（MinerU 返回逐字）；`wire/fix_l2_diag.md`（7 题取证＋build_documents 复核＋额度账）
- 钩子披露：`wire/hook_fix.md`；`probe_instrument2/sitecustomize.py`
- 截图：`shots/fix_01-seats.png`／`fix_02-l2-batches.png`／`fix_03-l2-review.png`
- 脚本：`fix_diag.py`／`fix_host2_setup.py`／`fix_host2_launch.py`／`fix_l2_probe.py`／`fix_dual_probe.py`（备）／`fix_render_probe.py`（备）
- 宿主日志：`server2.out.log`／`server2.err.log`
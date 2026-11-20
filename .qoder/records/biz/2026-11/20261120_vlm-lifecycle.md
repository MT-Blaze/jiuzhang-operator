# VLM 服务生命力小刀（vlm-lifecycle）

状态：收口全绿（死实例复用修复＋20 分钟闲停；两仓 commit 不 push；生效需主公重启一次）
发起日期：2026-11-20
需求来源：枢纽 4a0d74c0 转达本地 VLM 服务生命力小刀卡（主公裁决：「3 的话，这个也处理掉吧，小毛病」「常驻给他修改为 15 分钟或 20 分钟呗」→ 取 20 分钟）
基线：operator 7648599（ahead 88）／plugins 93e4686（editor 2.25.1，ahead 23，零改零笔）；本卡 operator 两笔（06db4db/收口笔），ahead 88＋2＝90
回单：docs/handoff/receipts/vlm-lifecycle.md（#VLM-LIFECYCLE-01）

## [REQ] 2026-11-20

病灶两条（枢纽已定位）：
① 死实例被复用——`vlm_service.start()` 复用条件只有「进程活＋同座＋/health 200」；权重被重装/替换后
旧 llama-server 仍活着回 200 但加载的是旧模型，老师会一直复用一个「能应答但答不对」的实例（sticky 死实例）。
② 永驻不闲停——服务起来后除非切座/退出一直占显存；主公要 20 分钟无活自动停。
卡令：`/props` 自检 model_path 文件名，四条件全真才复用（fail-closed）；`WARM_IDLE_SECONDS=1200`
＋30s 看门狗，touch 划线，不许杀推理；只动 vlm_service.py＋vlm_local.py 触达点；canary 新增五类案、
旧案零删酌情转正；定向七模块＋快门禁；两仓 push hold；65496（PID 2700）零接触；本卡不得起真 VLM、
不得碰现网暖驻留端口；禁 taskkill /F /IM python.exe；禁 JSON 落盘；stage 点名不 amend。

## [PLAN] 2026-11-20

开工复核：operator 7648599 ahead 88、工作树仅 `?? tools/onnx_probe.py`；plugins 93e4686 ahead 23，
工作树仅未跟踪运行产物（model_prefs.toml／models/），与卡§0 一致。
实现决策：
- 自检 `_serves_expected_model(base_url, token, model_path)`：GET /props（Bearer，5s），
  `wire.loads` 解析（全仓唯一对外 JSON 边界），normcase＋basename 比本座主 GGUF 文件名；
  非 200/解析败/缺字段一律 False。`_health_ok` 只探一次存 `healthy`，防既有 side_effect 测试序列被打乱。
- 闲停：`_LAST_USED` 模块级；`touch()` 公开（加锁、没跑静默）＋`_touch_locked()`；
  起服/复用成功划线；vlm_local `_chat` 请求前与 finally 各 `_touch()`（延迟 import 防环，异常吞掉）。
- 看门狗：纯函数 `_idle_expired` 可单测；`_watchdog_tick` 锁内杀服；`_watchdog_loop` 30s 一跳；
  `_start_watchdog` 用 `_WATCHDOG` 防重复；start 持锁调用，线程先睡不抢锁。
- 测试：setUp 统一 mock `_start_watchdog`（防真线程×被 mock 的 sleep 自旋）、复位 `_LAST_USED/_WATCHDOG`；
  三个旧复用案补 mock `_serves_expected_model=True` 转正；新案走真自检函数＋fake `/props`。

## [IMPL] 2026-11-20

- commit 06db4db：`app/core/ingest/recognize/vlm_service.py`（+85）＋`vlm_local.py`（+12）＋
  `tests/test_vlm_service.py`（+150/−5，310→460 行，tests/ 豁免行数帽）。
  - vlm_service：`WARM_IDLE_SECONDS=1200`（:37）；`_serves_expected_model`（:65）；`touch`（:84）＋
    `_touch_locked`（:90）；`_idle_expired`（:96）；`_watchdog_tick`（:101）；`_watchdog_loop`（:114）；
    `_start_watchdog`（:123）；start 复用分支四真判定＋warn（:190-207）；起服成功 touch＋看门狗（:246-247）。
  - vlm_local：`_touch` 延迟 import（:50）；`_chat` 请求前（:81）与 finally（:90）划线。产线其余零改。
- 未真起引擎、未碰暖驻留端口、未执行任何 taskkill；插件仓零改零笔。

## [VERIFY] 2026-11-20

- 定向（.venv/Scripts/python.exe 逐模块 unittest，禁 pytest/discover）：
  test_vlm_service Ran 27 OK（旧 18＋新 9）；test_vlm_setup 33 OK；test_vlm_local_run 16 OK（追加，
  vlm_local 被触达）；test_models_registry 79 OK；test_recognize_router 26 OK；test_formula_route 39 OK；
  test_reidentify 29 OK；test_file_size_contract 13 OK。
- 快门禁 bash scripts/check-quick-gate.sh → PASS（6 项全过）；体积警报 23 份，集合与基线相同。
- 红线自检：LICENSE/根 agents.md/铁律一二/question_contract.py/用户 data/ 零改；app/ 仅两个点名文件；
  onnx_probe.py 原地未 stage；禁 JSON 落盘（回单/biz 均 MD）；stage 点名、不 amend、不 push。
- 前端零改 → Playwright 免测；零出网零额度零真引擎零真端口；65496（PID 2700）零接触。

## [RELEASE] 2026-11-20

两仓 commit 全 hold 不 push。ahead 88＋2＝90（06db4db＋本收口笔）。生效需主公重启底座一次。
偏离登记：vlm_service 实际 +85 行（卡面预计 +40 内，功能必需、远离 450）；404 fail-closed 用
status=404 fake＋URLError/TimeoutError 覆盖，未造 HTTPError 实例（资源告警噪音，语义等价）。
欠账：/props 端点为 llama-server 原生能力，未在本卡真测（禁起真引擎），交主公里程碑实测登记。

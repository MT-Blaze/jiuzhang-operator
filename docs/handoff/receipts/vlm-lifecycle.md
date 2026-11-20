# 回传单 · 本地 VLM 服务生命力小刀卡（死实例复用修复＋20 分钟闲停）

【回执编号】 #VLM-LIFECYCLE-01
【回执时间】 2026-11-20
【主公裁决】 2026-11-20：「3 的话，这个也处理掉吧，小毛病」「常驻给他修改为 15 分钟或 20 分钟呗」→ 取 **20 分钟**。
【执行结果】 **收口全绿**。两处病根按卡面刀法修在 `vlm_service.py`＋`vlm_local.py` 触达点，canary 九案新增、
旧案零删；定向七模块＋vlm_local 全绿，快门禁 PASS（6 项），体积警报 23 份与基线相同。
**未真起 VLM 引擎、未碰现网暖驻留端口；65496（PID 2700）零接触；生效需主公重启一次。**

基线：operator `7648599`（开工实测 ahead 88，与卡§0 一致）／plugins `93e4686`（editor 2.25.1，ahead 23，零改零笔）。
本卡 operator 两笔：`06db4db`（刀＋canary）／收口笔（本回单＋biz）；ahead 88＋2＝90。两仓 push 全 hold。

## 桶一 · 做了什么（逐条对齐卡§2）

- **§2A 复用四条件全真（fail-closed）**
  - 新增 `_serves_expected_model(base_url, token, model_path)`（vlm_service.py:65）：GET `/props`
    （Bearer 令牌，5s 超时），解析 `model_path`，按 `os.path.normcase(os.path.basename(...))` 与本座
    `vlm_setup.model_paths(seat)[0]` 的文件名比对；HTTP 非 200／解析失败／字段缺失一律 False。
    JSON 解析经 `app/core/wire.py`（全仓唯一对外协议边界），基座零 `import json`。
  - `start()` 复用分支（vlm_service.py:190-207）：进程活＋`_SEAT==seat`＋`_health_ok`＋
    `_serves_expected_model` 四真才复用；`_health_ok` 只探一次存 `healthy` 变量（不双探，避免探测序列漂移）；
    同座健康但自检不过 → 一行 `logger.warning`「复用自检不通过：服务装的不是本座当前权重，重启」→
    `_kill_locked()` → 正常起新服。`_health_ok` 原样保留用于启动轮询。
- **§2B 20 分钟闲停（不杀推理）**
  - `WARM_IDLE_SECONDS = 20 * 60`（:37），注释一行钉依据：单题上限 900s（15 分钟）＜ 20 分钟闲停。
  - 模块级 `_LAST_USED`；公开 `touch()`（:84，加锁，服务没跑静默无操作）＋锁内 `_touch_locked()`（:90）；
    起服成功（:246）与复用成功（:197）都划线。
  - `vlm_local._chat` 在发请求前（vlm_local.py:81）与 `finally`（:90）各调 `_touch()`；
    函数内延迟 import vlm_service 防循环依赖，`touch` 抛错被吞、不影响识别。
  - 看门狗（:101-131）：纯函数 `_idle_expired(last_used, now)` 判定（便于单测不睡 20 分钟），
    `_watchdog_tick(now)` 锁内检查（进程活＋超时 → info 日志＋`_kill_locked()`，杀树＋端口复验沿用现实现），
    `_watchdog_loop` 每 30s 一跳，`_start_watchdog` 模块级 `_WATCHDOG` 防重复只起一个 daemon。
    `start()` 持锁调用 `_start_watchdog`，线程先睡 30s 再查，不会抢锁。
- **§3 Canary（tests/test_vlm_service.py，旧案零删）**
  - 新增 9 案：正确权重→复用不杀（走真 `_serves_expected_model`＋fake `/props`）／旧权重→杀旧起新
    （断言 warn 日志、detail 不说复用、popen×2）／`_serves_expected_model` 文件名比对＋Bearer＋5s 超时／
    fail-closed 六路（旧名、status 404、URLError、TimeoutError、坏 JSON、缺字段）／闲停超时停服
    （taskkill 精确 PID＋endpoint 归 None）／未到线不停／`touch()` 后不停／服务没跑 touch 静默／
    看门狗只起一个线程。
  - 三个旧复用案（`test_running_healthy_service_is_reused`／`test_concurrent_starts_spawn_only_one_process`／
    `test_same_seat_healthy_reuse_does_not_kill`）补 mock `_serves_expected_model=True` 转正，
    断言一字未放宽；其余旧案零改。
  - 全部 mock：fake subprocess／fake `/props` 响应，不落真端口、不起真进程、零出网。

## 桶二 · 实测证据（数字全部来自当次输出）

| 模块 | 结果 | 备注 |
|---|---|---|
| tests.test_vlm_service | Ran 27 / OK | 旧 18＋新 9；含 4 条复用/自检案、4 条闲停案 |
| tests.test_vlm_setup | Ran 33 / OK | |
| tests.test_vlm_local_run | Ran 16 / OK | 卡面外追加（vlm_local 被触达，`_touch` 不影响传输层断言） |
| tests.test_models_registry | Ran 79 / OK | |
| tests.test_recognize_router | Ran 26 / OK | |
| tests.test_formula_route | Ran 39 / OK | |
| tests.test_reidentify | Ran 29 / OK | |
| tests.test_file_size_contract | Ran 13 / OK | 体积警报 23 份，与基线相同 |

- 快门禁：`bash scripts/check-quick-gate.sh` → `check-quick-gate: PASS（6 项全过）`，体积预警 23 份。
- 行数：`vlm_service.py` 230→315（+85，卡面预计 +40 以内；离 450 红线尚远，登记为偏离①）；
  `vlm_local.py` 169→181（+12）；`tests/test_vlm_service.py` 310→460（tests/ 豁免行数帽）。
- 零出网、零额度、零真引擎、零真端口；未执行任何 `taskkill`／`tasklist` 实操，未触碰 PID 2700。
- 插件仓零改：工作树仅 `?? src/org.jiuzhang.editor/model_prefs.toml` 与 `?? src/org.jiuzhang.editor/models/`
  （主公 UI 安装权重的运行产物，非代码脏，零接触）。
- 前端零改 → Playwright 免测，特此注明。

## 桶三 · 偏离与欠账

- **偏离①**：vlm_service.py 实际 +85 行，超卡面「预计 +40 行以内」的估算；功能点（自检＋touch＋看门狗）
  全部必需，315 行远离 450 红线，未做压缩改写。
- **偏离②**：fail-closed 的 404 用 `FakePropsResponse(status=404)` 验证「非 200」分支＋`URLError`／
  `TimeoutError` 覆盖网络异常；未真造 `HTTPError` 实例（会触发资源告警噪音），语义等价（HTTPError 是
  URLError 子类，同一 except 分支）。
- **偏离③**：`_health_ok` 结果只探一次存变量，非卡面「四条件」字面写法，避免短路后二次探测打乱现有
  side_effect 测试序列；语义与四真判定一致。
- **生效条件**：本卡未起真服务、未碰现网暖驻留，代码改动需主公**重启底座一次**后生效。
- **欠账（不动）**：/props 自检依赖 llama-server 端点；mineru-llama-cpp 0.2.3 自带版本具备该端点，
  未在本卡真测（禁起真引擎），交主公里程碑实测登记。

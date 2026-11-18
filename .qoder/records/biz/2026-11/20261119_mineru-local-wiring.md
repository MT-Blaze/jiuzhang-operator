# MinerU 本地逐题接线与真装端到端

- 状态：待核验
- 发起日期：2026-11-19
- 执行会话：fc692db9（委托任务卡《MinerU本地逐题接线与真装端到端任务卡.md》，无人值守接力）
- 回执编号：#MU-02
- 基线：底座 90e2b91 ／ 插件 2b100d0（2.16.0），坐在其上施工，不卷动不 amend 不 push

## [REQ] 2026-11-19

四合一留的欠账本卡收：①真装端到端——探针 Playwright 真点【安装本地 MinerU】，隔离环境
（JZO_DATA_DIR/JZO_PLUGINS_DIR 副本＋动态端口＋随机令牌，绝不碰 65496/dev-token），装到
engines/mineru 真实路径，health＋版本＋就绪截图；权重下载优先并入同一次安装点击，否则只在
用户点选的解析作业里懒下载并在 UI 说明，选择记回单。②服务编排 mineru_service.py ≤450 行：
ensure_ready 未装诚实失败引导安装按钮绝不自动装；start 懒起隔离 venv 子进程、动态端口、随机
令牌、健康轮询 300s、并发锁、运行中复用；stop 杀进程树＋端口复验，挂 main.py lifespan 收口，
零孤儿。③逐题引擎 mineru_local.py ≤400 行镜像 mineru.py 逐题循环，本地 API 客户端住本文件，
单题等 900s，失败 ok=False 显性。④router 只走选中引擎不降级，_AUTO_PLAN 不动；catalog 删
gate_note、plan_recognize=["mineru_local"]、文案按事实重写；2.17.0 四处 parity＋zip 重建。
⑤新单测两枚＋更新三枚，定向 unittest＋快门禁绿；探针 3 题回填≥2＋≥1 题 $...$ 公式＋负向显性
失败清单＋收口端口复验零孤儿；三查=0；回单五件。红线：禁改区不碰、onnx_probe.py 与插件
models/ 不 stage、engines 不 stage、点名 stage、不绿不 commit、两仓各单 commit 不 push。

## [PLAN] 2026-11-19

- 侦查 installed mineru==4.2.3 wheel 源码定 API 形状：POST /v1/tasks（JSON files+output_formats）
  →202 task_id+upload url→PUT octet-stream→轮询 GET /v1/tasks/{id}→result_url 取 zip 内
  markdown.md；--api-key 时 Bearer；/v1/health、/v1/tiers 公开。服务入口
  engines/mineru/Scripts/mineru-api.exe --host 127.0.0.1 --port N --api-key TOKEN
  --concurrency 1 --task-timeout 900。
- 权重选择：并入同一次安装点击——mineru-models-download.exe --tier standard --small-backend
  onnx --vlm-engine llama-cpp --source modelscope（本机无 torch，standard 档 llama-cpp GGUF
  小 VLM 不需要 torch）；预取失败不阻断安装，done 文案注明首次解析再下。
- 三态语义不动：_rule_mineru_local 只管安装体检；_gate 不改；服务失败＝作业显性失败清单，
  绝不静默回 auto。

## [IMPL] 2026-11-19

底座：新增 app/core/ingest/recognize/{mineru_service.py 195 行,mineru_local.py 192 行}、
tests/{test_mineru_service.py 11 例,test_mineru_local_run.py 14 例}、tools/mineru_local_probe.py
425 行；修改 mineru_setup.py（预取并入＋weights_ready 只读探查）、router.py:116 mineru_local
分支、main.py:185-187 lifespan 收口 stop、tests/{test_mineru_setup,test_recognize_router,
test_models_registry,test_command_registry:487}、plugins.toml:51。
插件：catalog.toml mineru_local 条目（删 gate_note、plan_recognize、route_note_recognize、
ready_detail/summary_usage 按事实重写含 VLM CPU）、plugin.toml:4／plugins.json:68 → 2.17.0、
zip 重建（in-zip catalog sha256 == 源 MATCH）。
踩坑与修复：①本机 AMD RX 5600 XT llama-cpp Vulkan 推理丢设备（vk::Queue::submit
ErrorDeviceLost，探针 run2 回填 0/3 根因）→ 服务 env MINERU_LLAMA_CPP_BACKEND=cpu 强制
VLM CPU，ONNX 小模型仍 DirectML，单测锁 env、catalog 文案同步；②Playwright sync 主线程
事件循环与 asyncio.run 冲突 → fill_batch 放 worker 线程；③mineru-api 以仓库根为 CWD 落
.mineru-service.lock 杂文件 → Popen cwd=engine_dir()；④就绪态无安装按钮（action=""）无法
二次点击补预取 → 挪开旧装 engines/mineru-prev 全新真装 run4 一次点击 pip+预取 338.6s。

## [VERIFY] 2026-11-19

- 定向 unittest（.venv/Scripts/python.exe -m unittest 逐模块）：test_mineru_setup 19、
  test_mineru_service 11、test_mineru_local_run 14、test_recognize_router 23、
  test_models_registry 43、test_command_registry 34，合计 Ran 144 tests 全 OK。
- 快门禁 bash scripts/check-quick-gate.sh → PASS（6 项；23 份体积预警均既有台账，新文件均 <451 行）。
- 索引 parity scripts/check_plugin_index_parity.py → PASS；sync_plugin_index 远端语义一致。
- 真装 run4：一次真点安装 338.6s 到 done（4.2.3，解析模型已预取），weights_ready True，
  4/4 checks PASS，收口端口 61846 关闭；证据 .system_generated/mineru-local/install-run1/
  install_result.toml（run3 旧代码 1129.1s 归档 run3-evidence/）。
- 服务侦查 live-recon.txt：动态端口 62217＋随机令牌起服；/v1/tiers 四档 flash/basic/standard/
  advanced 均 mineru-4.2.3；/v1/health status ok、device gpu、formats default/docx/html/latex；
  stop port_closed True。
- e2e 探针 run3（tools/mineru_local_probe.py）：12/12 PASS，ok=True，701.8s。隔离副本＋
  动态端口 62535＋随机令牌；扫描切题 20 道→下拉真选 mineru_local→3 题真 fill_batch 回填
  3/3（651.6s）；公式证据 3/3 题含 $...$（stem 长 79/52/122，DB 复核 updated_at
  01:33/01:37/01:40 为回填时刻、seq4 仍 01:29 扫描时刻，LaTeX 为 MinerU 风格 \mathrm/\subseteq/
  \forall，非扫描文本层）；负向挪开 mineru-api.exe→显性失败清单 step 识别·MinerU本地、
  mode mineru_local、不降级、UI failbadge 可见；收口 stop＋端口复验关闭＋tasklist 孤儿零。
  证据 .system_generated/mineru-local/run1/（probe.toml＋shots/ 5 张：mineru-ready、
  scan-batch、engine-selected、fill-result、failure-list）。
- 三查（插件 dist/*.js grep -o -F 计数）：fetch( =0、parent.document =0、localStorage =0；
  请求 id core_host.js:31 "edv2"+seq+"-"+base36 无点号合规。
- 包结构自检：顶层目录==id；无 backend 字段；Apache-2.0 LICENSE 全文在；min_host_version
  1.0.0 ≤ 宿主 1.2.0。

## [RELEASE] 2026-11-19

两仓各单 commit（不 push）：底座 feat(ingest) MinerU 本地逐题接线＋服务编排＋真装预取；
插件 feat(editor) 2.17.0。push 待枢纽核验后问主公点头。
欠账与偏离：①B-001 样本不在 test_papers/manifest.toml，用 A2 取证留存同卷副本（477820 字节）；
②3 题子集由探针进程内驱动真 fill_batch（无逐批重识别端点），全 20 题本地批解析未跑；
③负向用挪开 exe 制造真起服失败（懒起服下单纯 stop 会被复用）；④CPU VLM 单题约 2–4 分钟
（900s 上限未触顶但偏慢），NVIDIA 卡路径本机无硬件未活验；⑤install-run1 驱动复用旧 plugins
副本致 registry 文案陈旧（探针用新副本，生产不受影响）；⑥云端 MinerU 账号路径本轮未动。
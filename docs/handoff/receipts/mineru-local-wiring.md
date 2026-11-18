# 机械证据回传单 · MinerU 本地逐题接线与真装端到端

【回执编号】 #MU-02
【回执时间】 2026-11-19 01:46:48+08:00
【实际耗时】 70 分 20 秒（会话 00:36:28 起 → 回执时刻，无人值守接力含上下文压缩；关键实测段：真装 run4 338.6s、e2e 探针 run3 701.8s、旧代码真装 run3 1129.1s）
【执行结果】 成功

军令：《MinerU本地逐题接线与真装端到端任务卡.md》§1–§7。基线：底座 90e2b91 ／ 插件 2b100d0（2.16.0）。
biz 记录：.qoder/records/biz/2026-11/20261119_mineru-local-wiring.md。

## 【改动清单】

底座（E:\jiuzhang\jiuzhang-operator）：
- 新增：app/core/ingest/recognize/mineru_service.py（195 行）——本地服务编排：ensure_ready（未装诚实失败引导【安装本地 MinerU】，绝不自动装）／start（懒起隔离 venv 子进程、动态端口、随机令牌、健康轮询 300s、并发锁、运行中复用、不健康点杀替换）／stop（taskkill /PID /T /F 杀树＋端口复验 10s）
- 新增：app/core/ingest/recognize/mineru_local.py（192 行）——逐题本地引擎：/v1/tasks 四步 API 客户端（create→PUT→轮询→zip 取 markdown.md，Bearer）住本文件；逐题循环 item_image_bytes→parse_image→build_documents→merge_local→save_back "ingest.mineru_local"；单题等 900s；逐题进度 note；失败 ok=False 显性
- 新增：tests/test_mineru_service.py（11 例）、tests/test_mineru_local_run.py（14 例）
- 新增：tools/mineru_local_probe.py（425 行）——隔离 e2e 探针（env 先于 app import；JZO_DATA_DIR/JZO_PLUGINS_DIR 副本＋动态端口＋随机令牌；Playwright 真点）
- 修改：app/core/ingest/mineru_setup.py（240 行）——权重预取并入同一次安装点击：mineru-models-download.exe --tier standard --small-backend onnx --vlm-engine llama-cpp --source modelscope（WEIGHT_TIMEOUT 1800）；weights_ready() 只读探查；health ok＋权重齐→done 短路；预取失败→done＋「首次解析时会再试下载」文案
- 修改：app/core/ingest/recognize/router.py:116——steps==("mineru_local",) 分支：ensure_ready 不 ok→显性失败「本地 MinerU 服务不可用（…），只走选中引擎，不降级，保留本地切图待人工核对。」＋_surface 识别·MinerU本地；ok→guard(run)；_AUTO_PLAN=("local","ai","mineru") 未动
- 修改：app/main.py:185-187——lifespan finally 挂 mineru_service.stop（asyncio.to_thread）
- 修改：tests/test_mineru_setup.py（19 例，＋权重探查/预取并入/预取失败懒下载注记）、tests/test_recognize_router.py（23 例，＋mineru_local 六例）、tests/test_models_registry.py（43 例，gate 测试改写：ready 直通 ("mineru_local","")、plan 声明、无 gate_note）、tests/test_command_registry.py:487→"2.17.0"
- 修改：plugins.toml:51→"2.17.0"（sync_plugin_index 工具改写，远端语义一致）
- 新增：本回单＋biz 记录（路径见抬头）

插件（E:\jiuzhang\jiuzhang-plugins）：
- 修改：src/org.jiuzhang.editor/catalog.toml——mineru_local 条目：gate_note 删除；plan_recognize=["mineru_local"]；route_note_recognize 新增；ready_detail/summary_usage 按事实重写（预取约 1–3GB 国内镜像、预取没成功首次解析再下、单题最长等 15 分钟、Windows 小模型 DirectML 无需 NVIDIA 卡、standard 档 llama-cpp GGUF 不需要 torch VLM 走 CPU 稳跑、失败显性列清单不偷换）
- 修改：src/org.jiuzhang.editor/plugin.toml:4→"2.17.0"；plugins.json:68→"2.17.0"＋changelog 四条
- 修改：plugins/org.jiuzhang.editor.zip——tools/build_plugin.py 重建（306.2 KB），in-zip catalog.toml sha256 == 源文件 MATCH（a247e639a04e4a61…，文案定稿后重建复验）

禁改区自查：LICENSE 未触碰（两仓 git diff 无）；AGENTS.md 铁律一二未触碰；app/core/question_contract.py 未触碰；用户 data/ 未触碰（探针全程 JZO_DATA_DIR 隔离副本，真实 data/ 零写入）；tools/onnx_probe.py 未 stage（git status 仍 ??）；插件 src/org.jiuzhang.editor/models/ 未 stage（仍 ??）；engines/ 未 stage（gitignore）。

## 【包结构自检】

- 顶层目录名 org.jiuzhang.editor == plugin.toml id ✓
- backend 字段：无 ✓
- Apache-2.0 LICENSE 全文：src/org.jiuzhang.editor/LICENSE 在 ✓
- min_host_version 1.0.0 ≤ 当前 app.__version__ 1.2.0 ✓
- 2.17.0 四处 parity：plugin.toml:4 ／ plugins.json:68 ／ plugins.toml:51 ／ test_command_registry.py:487；scripts/check_plugin_index_parity.py → PASS

## 【三查结果】（grep 实测）

命令：cd jiuzhang-plugins/src/org.jiuzhang.editor/dist && grep -o -F '<pat>' *.js | wc -l
- `fetch(` 命中 0 ✓
- `parent.document` 命中 0 ✓
- `localStorage` 命中 0 ✓
- 请求 id：core_host.js:31 "edv2"+requestSeq+"-"+Date.now().toString(36)，符合 ^[A-Za-z0-9_-]{1,80}$ 且无点号 ✓（点号只出现在 method 字段，非 id）

## 【测试与探针】

单测（解释器 .venv/Scripts/python.exe，逐模块 -m unittest，本轮新鲜数字）：
- tests.test_mineru_setup：Ran 19 tests OK
- tests.test_mineru_service：Ran 11 tests OK（含 env 锁 MINERU_MODEL_SOURCE=modelscope＋MINERU_LLAMA_CPP_BACKEND=cpu）
- tests.test_mineru_local_run：Ran 14 tests OK
- tests.test_recognize_router：Ran 23 tests OK
- tests.test_models_registry：Ran 43 tests OK
- tests.test_command_registry：Ran 34 tests OK
- 合计 144 例全绿。快门禁 bash scripts/check-quick-gate.sh → PASS（6 项全过；23 份体积预警均既有台账，本轮新文件均 <451 行：195/192/240/193/425）。

真装端到端（§1）：
- 磁盘预检 free 127.6 GB ≥8GB ✓
- Playwright 真点【安装本地 MinerU】（隔离宿主）：run4 一次点击完成 pip＋权重预取，install_elapsed_s=338.6，state done「本地 MinerU 已就绪（4.2.3），解析模型已预取。」，4/4 checks PASS，收口端口 61846 复验关闭。证据：E:\jiuzhang\jiuzhang-operator\.system_generated\mineru-local\install-run1\install_result.toml＋shots。
- 旧代码 run3（无预取）1129.1s 归档 install-run1\run3-evidence\；run4 前把旧装挪开 engines/mineru-prev（就绪态 action="" 无按钮可二次点击），全新真装验证新代码，收口后已清理。
- 权重选择（记回单）：**预取并入同一次安装点击**（standard／onnx／llama-cpp／modelscope）；预取失败不阻断安装，done 文案注明首次解析再下（懒下载只发生在用户点选的解析作业内）。
- 只读侦查 installed 包：API 形状 POST /v1/tasks→202 upload→PUT→轮询→result zip markdown.md；live-recon.txt 实测起服（动态端口 62217＋随机令牌）→/v1/tiers 四档 flash/basic/standard/advanced 均 mineru-4.2.3→/v1/health status ok、version 4.2.3、device gpu、formats default/docx/html/latex、sources upload/url→stop port_closed True。证据：.system_generated\mineru-local\live-recon.txt。

e2e 探针（§5，tools/mineru_local_probe.py，run3）：
- 判据 12/12 PASS，ok=True，elapsed 701.8s。证据：E:\jiuzhang\jiuzhang-operator\.system_generated\mineru-local\run1\probe.toml＋shots\（mineru-ready.png、scan-batch.png、engine-selected.png、fill-result.png、failure-list.png 共 5 张）。
- 扫描切题 20 道（auto 路由诚实注记「AI 未成功…MinerU 也没有可用账号：保留本地切图待人工核对」）→下拉真选 mineru_local→3 题真 fill_batch：**filled 3/3**（attempted 3，651.6s，note「MinerU 本地逐题解析完成：3/3 道回填成功。」，failures=[]）。
- 公式证据：3/3 题含 $...$，stem 长 [79,52,122]。**真实性复核**（.system_generated\mineru-local\verify_fill.py 读隔离 pending.db）：seq1–3 stem 为 MinerU 风格 LaTeX（$A = \{x \in \mathrm{N}^{*} \mid -\sqrt{3} \le x \le \sqrt{3}\}$、$\forall x \in R, x^{2}-2x+1 \ge 0$、$M \subseteq \{a_{1},…\}$），meta.updated_at 01:33:28/01:37:49/01:40:11 为回填时刻（间隔 2–4 分钟＝CPU VLM 节奏），seq4 仍 01:29:19 扫描时刻且 stem 为扫描文本层风格（a2+ b^{2}）——run2 的公式污染（扫描层 stem）已排除。
- 负向：stop＋挪开 mineru-api.exe→真起服失败→显性失败清单 step「识别·MinerU本地」、retryable=true、mode mineru_local、note「…只走选中引擎，不降级，保留本地切图待人工核对。」；UI failbadge→.ed-fail-item 可见（failure-list.png）；finally 恢复 exe。
- 收口：显式 stop ok＋端口复验关闭（服务端口 62535）＋tasklist /FI mineru-api.exe 孤儿零（probe.toml orphan_mineru_api=[]，收口后 shell 复核亦零）。

前端改动浏览器真人路径（docs/AGENTS.md §7）：探针 Playwright 穿沙箱真点——配置页就绪态截图、真上传试卷（#edBasketFile/#edBasketGo）、批次列表开批看路由注记、下拉真选引擎、失败清单 failbadge 点开逐条可见；全程隔离宿主，页面零 JS 异常。

## 【未决问题与偏离】

偏离（均已记 probe.toml deviations）：
1. B-001 样本不在 test_papers/manifest.toml——用 A2 取证留存的同卷副本 .system_generated\a2_image_ingest\ev1\data\pending_sources\20261118-193020_220dac_东北师大附中2023-2024高一上学期第一次月考试题.pdf（477820 字节，3 页 20 题）。
2. 3 题子集由探针进程内驱动真 fill_batch（宿主无逐批重识别端点，UI 重传整批会走 20 题全量）；回填/进度/落库走的是生产同一条 recognize_router.fill_batch→save_route 链路。
3. 负向用挪开 mineru-api.exe 制造真起服失败——懒起服语义下单纯 stop 后再选会被复用，无法制造「服务不可用」；挪开 exe 是 ensure_ready 诚实失败分支的真触发。

硬件事实与修复（本轮最重要偏离）：
- 本机 AMD Radeon RX 5600 XT 6GB。探针 run2 回填 0/3，service.log 根因「ServerError: decode() failed: vk::Queue::submit: ErrorDeviceLost」——llama-cpp Vulkan 在 AMD 卡丢设备。修复：mineru_service.start env MINERU_LLAMA_CPP_BACKEND=cpu（installed llama_device.py 核实 cpu→explicit_cpu），ONNX 小模型仍 DmlExecutionProvider；run3 实测日志「llama.cpp device policy: cpu (explicit_cpu)」＋layout DirectML＋3/3 回填。单测锁 env、catalog 文案同步「VLM 走 CPU 稳跑」。
- 代价：CPU VLM 单题约 2–4 分钟（3 题 651.6s），900s 单题上限未触顶但偏慢；NVIDIA 卡路径本机无硬件未活验（单测覆盖 env 分支）。

欠账：
1. 全 20 题本地批解析未跑（只 3 题子集取证）；整批耗时未实测。
2. install-run1 安装驱动复用旧 plugins 副本，其 install_result.toml 里 registry 文案是旧版（「接线在下一卡」）；探针 run3 用新副本已验新文案；生产路径不受影响。
3. 云端 MinerU 账号路径本轮未动（mineru_extract 语义未改，单测覆盖）。
4. push 未做——两仓各单 commit 后待枢纽核验、主公点头。

未验证：
- ≥6G NVIDIA 卡 DirectML/Vulkan 真机路径（无硬件）。
- 预取失败→首次解析懒下载活路径（单测覆盖文案与分支；真机 run4 预取一次成功，未制造失败）。
- 40 分钟安装上限超时分支（真装 338.6s 远低于上限；单测覆盖）。
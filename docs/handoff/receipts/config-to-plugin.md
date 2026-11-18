# 回传单 · 配置归插件重构卡

【回执编号】 #CTP-01
【回执时间】 2026-11-19T00:22:21+08:00
【实际耗时】 24 分 56 秒（首件落地 catalog.toml 搬家 2026-11-18 23:57:25 → 收口读数 00:22:21，文件 mtime/系统钟实测；不含卡前只读侦查）
【执行结果】 成功：定向 12 模块 388/388 绿、快门禁 6 项 PASS、真机探针 32/32 PASS、索引 parity PASS、两仓各单 commit 不 push

正文逐条对齐卡§1–§6；biz 记录 `.qoder/records/biz/2026-11/20261119_config-to-plugin.md`；
基线：底座 8852be1 ／ 插件 ebbc9e5（2.15.0），坐在其上施工，不卷动、不 amend、不 push。

## 【改动清单】

底座（E:\jiuzhang\jiuzhang-operator）：
- 新增：`tests/catalog_fixture.py`（82 行，最小 headless 目录提供者夹具＋隔离环境）；
  `tools/config_to_plugin_probe.py`（322 行，随机令牌＋动态端口真机探针，32 判据）；
  `.qoder/records/biz/2026-11/20261119_config-to-plugin.md`（本卡 biz，append-only）；
  本回传单。
- 修改：`app/core/ingest/registry.py` 重写 253 行——六规则通用解释器，_judge 不再认任何
  模型 id；catalog_provider() 按 models.catalog 能力发现启用插件（bank.provider 先例）；
  缺失/损坏＝空目录；未知规则＝blocked＋「底座不认识这条规则…请更新底座」；_gate 语义不变。
- 修改：`app/core/ingest/model_prefs.py` 重写 72 行——删 PLUGIN_ID 硬编码，path/load/save
  全带 plugin_id，正则封口防路径穿越。
- 修改：`app/api/models.py` 重写 73 行——prefs 带 Query plugin_id；_catalog_plugin 三查
  （未声明能力/已停用/未安装→403）；写令牌 Depends 不变。
- 修改：`app/core/ingest/layout/router.py` 135 行、`recognize/router.py` 170 行——删全部
  模型 id 常量与分支；normalize/plan 改读 catalog（capability 过滤＋plan_*＋aliases_*）；
  auto 瀑布步骤键留底座；未接线 plan 诚实失败。
- 修改：`app/core/ingest/route.py` 399 行——scan_route 具体档注记改读 catalog route_note_*。
- 修改：`app/api/ingest.py:38-39` docstring 去模型 id，改「catalog 声明的引擎 id」。
- 修改：`app/core/plugins/registry.py` _CAPABILITIES 末尾＋`models.catalog`（731 行，净零）。
- 修改：`static/js/stage_relay_io.js` relayModels——prefs_save 增 models.catalog 能力闸
  （FORBIDDEN），URL 带 plugin_id=tab.plugin.id；方法名/返回形不变；773 行净零。
- 修改：`docs/PLUGIN_SPEC.md` 能力表行＋新 §2.6.2「模型目录归插件」五条契约。
- 修改：`plugins.toml`（tools/sync_plugin_index.py 改写：editor 2.16.0＋updated_at）。
- 修改：`tests/test_command_registry.py:487` 2.16.0；`tests/test_models_registry.py`、
  `tests/test_model_prefs.py` 重写；`tests/test_layout_router.py`、`test_recognize_router.py`、
  `test_ingest_triage.py`、`test_ingest_routing.py` 接夹具/去已删常量。
- 删除：`app/core/ingest/catalog.toml`——搬去插件根（哈希证明见下），底座零引用
  （grep CATALOG_PATH/旧路径=0，registry 改读 plugins_dir()/<id>/catalog.toml）。
- 禁改区自查：LICENSE 未碰；根 AGENTS.md 未碰；AGENTS 铁律一二未碰；
  app/core/question_contract.py 未碰；用户 data/ 未碰（探针全隔离）。是/否＝否。
  tools/onnx_probe.py 与插件 models/ 保持 untracked，未 stage。

插件（E:\jiuzhang\jiuzhang-plugins，瞬态身份 -c MT-Blaze 提交，未写 git config）：
- 新增：`src/org.jiuzhang.editor/catalog.toml`（搬家＋规则扩展，随 zip 发行）。
- 修改：`src/org.jiuzhang.editor/plugin.toml` version 2.16.0、capabilities＋models.catalog。
- 修改：`plugins.json` editor 2.16.0＋changelog、updated_at 2026-11-19。
- 修改：`plugins/org.jiuzhang.editor.zip` 重打（build_plugin.py 校验过，83 条目 306.1KB）。
- dist/ 与 index.html **零改动**（git status 实测空；UI 本就全数据驱动，无需适配）。

## 【包结构自检】

- 顶层目录名 == plugin.toml id：是（zip 内 org.jiuzhang.editor/，build 校验）。
- backend 字段：无（清单未声明，validate_plugin 过）。
- Apache-2.0 LICENSE 全文：在（源目录既有，zip 内含）。
- min_host_version 1.0.0 ≤ 宿主 app.__version__ 1.2.0：是。
- zip 内容实测：catalog.toml 在包内且与源码逐字节同；models/ 不在包内；
  model_prefs.toml 不在包内（教师财产不随包发）。

## 【三查结果】（探针 run1 活验，插件 dist/*.js 计数）

- `fetch(` 命中 0 ✔
- `parent.document` 命中 0 ✔
- `localStorage` 命中 0 ✔
- 请求 id：core_host.js "edv2"+seq+"-"+base36，无点号，符合 `^[A-Za-z0-9_-]{1,80}$` ✔
  （本卡未改请求 id 生成器，沿用四合一卡实测口径，探针页面零 BAD_REQUEST_ID）。

## 【测试与探针】

- 单测（.venv/Scripts/python.exe -m unittest，逐模块点名，合跑一次取总数）：
  test_models_registry、test_model_prefs、test_mineru_setup、test_ingest_hardware、
  test_ingest_triage、test_editor_contract、test_command_registry、test_layout_models、
  test_file_size_contract、test_layout_router、test_recognize_router、test_ingest_routing
  → **Ran 388 tests in 9.860s，OK**（当次实测）。
- 快门禁：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**；体积预警 23 份均为
  既有台账/在它卡工作，非本卡引入。
- 索引：`tools/sync_plugin_index.py` → editor 2.15.0→2.16.0、远端语义一致；
  `scripts/check_plugin_index_parity.py` → **PASS**。
- 真机探针：`tools/config_to_plugin_probe.py run1` → **32/32 PASS**（probe.toml 落
  `E:\jiuzhang\jiuzhang-operator\.system_generated\config-to-plugin\run1\probe.toml`，
  截图 shots/config-overview.png、disabled-state.png、defaults-keyboard.png、mobile-375.png）。
  隔离 JZO_DATA_DIR/JZO_PLUGINS_DIR 副本＋动态空闲端口＋每次随机令牌（未写死 65496/
  dev-token-2026）；收口点杀后端口复验关闭 ✔。
- 前端改动浏览器真人路径（Playwright 穿沙箱 iframe）：开配置页→16 行＋逐条说明＋7 档表＋
  硬件快照上页→停用 YOLO 下拉消失/启用恢复（经 relay 代笔落隔离插件目录）→键盘
  ArrowDown+Enter 改默认落插件目录→Esc 关弹窗焦点还原→375px 不横向溢出；页面零 JS 异常、
  UI 阶段零 HTTP 失败。截图目视确认配置面渲染目录数据（4.0G WMI 披露＋7 档表）。
- 活验增量（本卡独有）：未知规则条目→blocked＋「底座不认识这条规则/更新底座」；
  改隔离目录 vram_note→registry 立即生效、还原立即恢复（清单可更新、不缓存）；
  prefs 缺 plugin_id/幽灵 id→403；无令牌→401/403；未知型号→400。

## 【卡点名证据】

1. **catalog 搬家哈希一致**：移动时底座旧文件与插件新文件 sha256 同为
   `d8eec4fc7c0598ceee443216a0534ee0fa2b3048b8ef8a81d437abaed9109b07`
   （`.system_generated/config-to-plugin/catalog-move-hashes.txt`）；规则扩展后程序化
   逐条子集证明：entries=16、vram_note_equal=True、vram_tier_equal=True、missing=[]
   （原 16 条原字段逐字保留）。2.16.0 zip 内 catalog sha256
   `085c537723af264d21e2aee5e10d7f450df363d6c9ddbbea733e3152f47b0326` 与源码同。
2. **carried 单测结论**：tests.test_model_prefs.UpdateSemanticsTest 4/4 绿——
   新包无 prefs→carried 保住老师勾选；新包带 catalog→覆盖（清单可更新，.toml 不在
   DATA_SUFFIXES）；新包无 catalog→carried 降级不停摆；prefs/catalog 均非数据白名单。
   探针活验：UI 停用/默认只落隔离插件目录，data/ 全树 rglob model_prefs.toml=0。
3. **app/ 模型业务硬编码 grep=0**（源码 *.py，当次实测，落盘 grep-proof.txt）：
   rapidocr_fast=0、rapidocr_accurate=0、cloud_vision=0、vlm_qwen/intern/minicpm/
   smolvlm/phi/gemma 各=0、formula_pp_m/pp_l/p2t/texify 各=0。
   mineru_local=3，三处均为**卡契约六规则之一的规则名**（registry.py:35 RULES 元组、
   :133 handler 定义、:175 dispatch 键），是通用契约标识符，不是模型业务分支。
4. **口径披露复述**：三态规则＝通用契约留底座（Python ingest 路由同步要用，问不了
   iframe）；模型清单/说明/门槛/勾选全归插件 catalog＋prefs。grep 口径：yolo/mineru
   残留＝auto 瀑布步骤键（_AUTO_PLAN）＋引擎实现自报（layout/yolo.py "engine":"yolo"、
   recognize/mineru.py）＋ai_center 任务键＋relay 端点名 models.mineru_install/status
   （卡§4 明确方法名不变）——公共管道实现名归底座，模型决策分支归零。
5. **行数红线**：route.py 399≤400；新模块 registry 253/router 135/170/prefs 72/api 73/
   夹具 82/探针 322 均≤450；台账只减不增：plugins/registry.py 731（施工前后净零）、
   stage_relay_io.js 773（净零）。分层≤3 未破（新文件均在既有三层内）。

## 【未决问题与偏离】

- 欠账：① MinerU 逐题解析接线留下一卡（catalog gate_note 照念「接线在下一卡、云端兜底」，
  D3a 不静默）；② T6 全禁继续（推理/擂台/自动升档未建，VLM/公式条目 blocked 待 T6）；
  ③ ≥6G 真机活验未做（本机 4G WMI，「待 T6」分支由单测覆盖）；④ MinerU 真装端到端未验
  （探针不真装）；⑤ relay 能力闸 FORBIDDEN 分支由单测＋后端 403 活验覆盖，探针未造第二支
  插件活验宿主侧闸；⑥ push 待枢纽核验后问主公点头。
- 偏离：① 卡§2 字面只点 registry._judge，但为达成「app/ 模型 id grep=0」把两条 router 与
  route.py 注记也数据化（包 B 决策，biz [PLAN] 披露）——语义不变：auto 瀑布、具体档不降级、
  旧名兼容逐条由单测矩阵钉住；② PLUGIN_SPEC 官方插件一览表版本为旧快照（2.12.2 等），
  非 parity 判据、卡范围外，未动。
- 解释性口径：mineru_local 规则名计入「通用契约」而非「模型硬编码」（卡§2 六规则明文）；
  「已落库/就绪」等沿用四合一卡口径，本卡未改三态语义。
- 未验证：宿主 relay 能力闸在「第二支未声明能力插件页签」下的真人路径（隔离副本只装一支
  插件）；远端 zip 下载链路（不 push，远端仍旧包，属预期）。
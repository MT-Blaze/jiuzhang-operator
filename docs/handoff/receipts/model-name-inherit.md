# 回传单 · 组合名从座继承（editor 2.26.3）

【回执编号】 #MODEL-NAME-INHERIT-01
【回执时间】 2026-11-20
【主公裁决】 2026-11-20：「他俩不应该改一个，另一个是引用的一个状态吗」→ 治本：
组合条目的名字直接引用座名，去掉两份 name 的抄写，从结构上消除漂移。
【执行结果】 **收口全绿**。插件仓 1 笔（editor 2.26.3）；底座仓 1 笔代码/测试/索引＋
1 笔本回单＋biz。定向 4 模块 **147/147 绿**；快门禁 PASS（6 项，体积预警 23 份与基线相同）；
索引 parity / 包结构 rc0；发行包双建同哈希 `742d0b58…`（328.5 KB）。
UI 隔离宿主真浏览器 **15/15 PASS**，4 张截图落底座仓
`.system_generated/model-name-align/inherit/`。**65496（PID 16992）零接触；零真引擎、
零安装、零出网。** 两仓不 push；live 生效需主公重启一次。

基线：plugins `135666d`（editor 2.26.2，ahead 26；未跟踪 `model_prefs.toml`、`models/`，
未 stage）；operator `b419dd4`（ahead 97，脏件仅 `?? tools/onnx_probe.py`）。

## 桶一 · 改了什么

### 继承设计（一处解析、谁吃它）

- 解析只在一处：[app/core/ingest/registry.py:281](file:///E:/jiuzhang/jiuzhang-operator/app/core/ingest/registry.py#L281)
  新增 `resolve_entries(entries)`：先建 `id→name` 映射（取各座条目自身 name），
  对 `plan_recognize` 含 `combo` 的条目**无条件覆盖** `entry["name"] = 座 name`
  （旧包残留的 combo 自带 name 也以座为准）；`combo_seat` 缺失、座不存在或座名为空＝
  写入 `catalog_error`。
- 生效顺序：[registry.py:322](file:///E:/jiuzhang/jiuzhang-operator/app/core/ingest/registry.py#L322)
  `status()` 先 `resolve_entries()` 再 `_judge()`，故 `{name}` 占位符、错误文案、
  `entry_state()`/闸口 note、识别下拉、模型配置表全部吃继承后的同一份名字。
- 异常显性化：`catalog_error` 条目落 `state=blocked`、`action=fix_catalog`，
  人话「组合条目「x」指向的座「y」不存在或没名字，请更新插件目录后再用该条目」，
  绝不静默空名。
- 未动 `router.py` 旧名错误文案（按卡另议）。

### 插件仓（commit df3fd6c，4 files）

- `src/org.jiuzhang.editor/catalog.toml` 删除 8 行组合 name：
  `combo_cloud`云端 AI OCR／`combo_vlm_qwen`千问 Qwen2.5-VL（本地）／
  `combo_vlm_intern`书生 InternVL3-2B（本地）／`combo_vlm_minicpm`面壁 MiniCPM-V-2.6（本地）／
  `combo_pp_m`PP-FormulaNet·M／`combo_pp_l`PP-FormulaNet·L／`combo_p2t`Pix2Text·MFR／
  `combo_texify`Texify。其余字段（id/combo_seat/rule/store/task/plan_recognize/summary…）一字未动；
  13 个座/普通条目的 name 全保留。
- `plugin.toml`：2.26.2 → **2.26.3**。
- `plugins.json`：editor version 2.26.3；changelog 新段前置，2.26.2 旧段原样保留。
- `plugins/org.jiuzhang.editor.zip`：`tools/build_plugin.py` 重建，双建同哈希
  `742d0b582c159c02061f45e3dc286638aa922bb7e53e04ddacf88949f9a6943b`。

### 底座仓（commit 622a5ec，4 files）

- `app/core/ingest/registry.py`：新增 `resolve_entries()`；`status()` 改走先继承后判定。
- `tests/test_models_registry.py`：旧 `test_combo_names_match_their_seat`（两份 name 相等）
  改写升级为 4 项，判据不删：
  1. `test_combo_entries_have_no_name_field`：8 条 combo 均无 `name` 字段；
  2. `test_status_combo_names_match_their_seat`：status() 输出逐条与座 name 逐字相等；
  3. `test_combo_name_follows_seat_injection`：注入式——构造临时条目改座名，
     组合名自动跟随（证明真引用）；
  4. `test_combo_with_missing_seat_is_blocked_not_blank`：缺座显性 blocked＋fix_catalog。
- `tests/test_last_used_engine.py`：`test_vlm_combo_split_into_three_seats` 改新契约——
  combo 段断言无 `name =`，同名的座段保有名字。
- `plugins.toml`：editor version 2.26.3（与插件清单、插件仓索引三方一致）。

## 桶二 · 注入式测试证据

`registry.resolve_entries()` 直接吃条目列表（磁盘 catalog 不动）：

- 把 `cloud_vision.name` 改成「改名后的云座」→ `combo_cloud.name` 同步变为「改名后的云座」；
- 移除 `cloud_vision` → `combo_cloud` 落 `name=""` ＋ `catalog_error`，status 里
  `state=blocked / action=fix_catalog`，文案含「不存在或没名字」。

## 桶三 · 实测证据

- 单测（`.venv/Scripts/python.exe -m unittest tests.test_models_registry
  tests.test_last_used_engine tests.test_command_registry tests.test_file_size_contract`）
  → **Ran 147 tests, OK**。
- `bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**，体积预警 23 份。
- `bash scripts/check-plugin-index-parity.sh` → rc0 PASS；`check-plugin-package.sh` → rc0 PASS。
- UI 真浏览器（隔离宿主，动态端口 6282，假视觉账号零出网）→ **15/15 PASS**：
  - API 组合名 == 座名 == 2.26.2 原字（8 条全覆盖）；
  - 模型表座行名、识别下拉就绪组合项与 2.26.2 原字逐字一致；
  - 7 对就绪组合「下拉↔模型表座行↔registry name」全相等，combo_texify 未装权重不入下拉、
    座行名「Texify」核值通过；
  - 零 JS 异常、零 HTTP 失败、收口端口已关。
- 截图：`.system_generated/model-name-align/inherit/01-model-table-top.png`、
  `02-model-cloud.png`、`03-model-formula.png`、`04-dropdown-flat.png`；判据
  `inherit/probe.toml`。

## 偏离

1. **combo_texify 未就绪不入下拉**：本机无 texify 权重，下拉按设计只列就绪条目；
   已核 API/模型表/测试三处座行名「Texify」，未伪造权重。
2. **`_entries` 过滤空 id**：继承映射只包含有 id 的条目（原逻辑不变），故不会给缺 id
   条目造名字。
3. **UI 证据走隔离宿主**：live 65496 加载旧包且禁重启；隔离实例加载当前源码取证，
   未动 PID 16992。live 生效需主公重启一次（与在途重启债合并）。
4. **探针与证据不入 commit**：`.system_generated/` 全忽略；`tools/onnx_probe.py` 仍未跟踪未 stage。

## 收口清单

- 插件仓：`df3fd6c`（ahead 26→27），未 push；`model_prefs.toml`/`models/` 未 stage。
- 底座仓：`622a5ec`（registry/测试/plugins.toml，ahead 97→98）＋本回单＋biz 笔（ahead 98→99），未 push。
- 两仓 commit 均 `-c user.name=MT-Blaze -c user.email=tianxiulaoshi@163.com` 瞬态身份，
  未写 git config；未 amend；stage 逐个点名。
- 未触碰：LICENSE、根 agents.md、AGENTS 铁律一二、app/core/question_contract.py、用户 data/、
  router.py 旧名错误文案、65496/PID 16992、两仓旧 stash。

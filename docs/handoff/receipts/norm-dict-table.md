# 回执 · 记号标准字典平表化＋砍头＋缓存版本号小卡

【回执编号】NDT-01（norm-dict-table）
【任务卡】E:\jiuzhang\记号字典平表砍头小卡.md（§0–§8）
【日期】2026-11-19
【基线】底座 ad7a149 ／ 插件 51776cf（2.22.0 PP-M 收口）
【交付】底座 HEAD f7823e3（本卡四笔）；插件零改＝parity 持 2.22.0、zip 不重打
【状态】本地完成全绿；两仓 push 待主公授权（hold，不催不问）

---

## 一、改动清单（带行号）

### 底座仓 jiuzhang-operator（ad7a149 → f7823e3，本卡四笔；ahead 46 含他卡在途 42）

逐阶段 commit（不 push、不 amend、stage 逐个点名禁 add -A）：
- 阶段1 `fa5a065`：砍头＋单枚二级标签条不渲染
- 阶段2 `4a55a32`：卡片→六列平表
- 阶段3 `fe7bc9a`：catalog.js 缓存版本号补升（含偏离加升三枚，见§五-1）
- 阶段4 `f7823e3`：双探针真测收口＋证据落盘

**§1 砍头（阶段1）**
- `static/js/dict_console/norm_dict.js`：原 58-63 行 head 块整删——h2「记号标准字典」、
  「整机生效」徽章 span、「闭集出厂冻结…」说明段 p。进页直接见筹码/搜索/表。
- `static/js/dict_console/subtabs.js`（113 行）：`:24` `solo = items.length === 1`；
  `:27-28` 单枚时整条 `.dc-subtabs` 标签条不渲染（`bar = null`），pane 照铺；
  `:40` 单枚不建 button；`:55-56` pane 无障碍回落 `aria-label=item.label`（多枚照旧
  `aria-labelledby`）；`:75-77` activate 里 button 存在才翻 aria-selected/tabIndex；
  `:79` 钉死串 `entry.pane.style.display = on ? "block" : "none"` 一字保留
  （test_dict_console_subtabs 17/17 绿）；`:88` keydown 守卫 `if (bar)`。
  多标签分类与独立 /dict 页不受影响（旧探针 18/18 实证，见§四）。
- `static/css/dict_console_norm.css`：摘 `.dc-norm-machine-badge` 选择器一段；
  `.dc-norm-head`/`.dc-panel-hint` 保留——norm_inbox.js 与看板共用（见§五-3）。
- chips/搜索/norm_inbox.js 一字不动。

**§2 平表（阶段2）**
- `static/js/dict_console/norm_dict.js`（271 行，≤450）：
  - `renderList():109` 重写为真 `<table class="dc-norm-table">` 六列＝名称/代码/来源/渲染/默认/操作；
    空态（闭集为空/没有匹配）提示照旧。
  - `entryRows():175` 一行一变体；同记号名称格（族标＋名称＋entry_key）与操作格
    （恢复出厂键＋状态行）按 `rowSpan=variants.length` 合并；radio
    `name="dc-norm-default-"+entry_key`、`value=variant.id`，change→choose。
  - `syncDefault():135`/`choose():146`/`reset():157`：group 对象（radios/resetBtn/stateLine）
    替代旧 block 查询；DcClient.writeJson 写库路径（/api/norm/choose、/api/norm/reset）与
    DcDialog 确认（焦点陷阱/Esc/归位）一字未动；API/relay 零改。
  - 渲染复用 JzoMath（DOMParser 落节点，绝不 innerHTML）；render_supported=0 显性降级照旧。
  - `matches():99` 过滤/搜索口径一字不动。
- `static/css/dict_console_norm.css`（246 行，≤450）：
  - `:82` `.dc-norm-list{max-width:100%;overflow-x:auto}` 表容器横滚；
  - `:84-86` `.dc-norm-table{width:100%;min-width:760px;border-collapse:collapse}`；
  - `:103-104` `td{height:36px}` 行高约 36px；
  - `:113` 名称格 min-width 140；`:153` 渲染格 min 180/max 280 内部横滚；
  - mjx 选择器改 `.dc-norm-render-cell mjx-container`；删旧卡片族
    dc-norm-entry/entry-top/name-box/vhead/vrow/vcode/vrender/vpick；
    @media 只留开集对照格堆叠。375px 页面零横溢（探针实测 doc=375，见§四）。

**§3 缓存版本号（阶段3）**
- `static/workspace.html:250`：`catalog.js?v=20261113`→`?v=20261119`（卡面点名）。
- `static/dict_console.html:116`：`catalog.js?v=20261113g`→`?v=20261119`（卡面点名）。
- 偏离加升三枚（理由见§五-1）：`:25` norm css `?v=20261119b`、`:138` subtabs.js
  `?v=20261113g`→`?v=20261119b`、`:150` norm_dict.js `?v=20261119`→`?v=20261119b`；
  `:148` 注释「闭集五列」→「六列平表」。

**§4 探针与证据（阶段4）**
- `tools/norm_dict_table_probe.py`（399 行，新建）：git archive HEAD 隔离副本（禁抄工作树）＋
  dashboard＋bank-engine 双插件只读拷入；随机令牌（secrets）＋动态端口（free_port）；
  AI key 全清空＝零引擎零出网；Playwright 自驱 chromium 走真人路径：宿主 /e→沙箱右栏
  真点「记号标准」→宿主同源字典层 iframe 原地平表；断言六列/271 行/rowspan 223/砍头/
  radio＋恢复出厂真点留 wire/chips＋搜索真点对账/375px 零横溢/零 JS/HTTP/console；
  收口点杀＋端口 25×0.2s 复验＋孤儿扫描（排除 PowerShell 自匹配）。
- `tools/latex_norm_ui_probe.py`（371 行，断言随 UI 改形同步，AGENTS §8.6）：
  卡片断言→平表断言（六列/rowspan/族变体数对账/表容器横滚）；radio 定位同修；
  走独立 /dict?cat=notation&sub=norm-dict 路径，兼作独立页不回归证据。
- 证据扁平落 `docs/handoff/evidence/norm-dict-table/`（16 文件）：
  probe.toml、wire.toml、standalone-probe.toml、shot-01~05（工作台宽/表宽/选默认/窄屏×2）、
  shot-standalone-01~08（独立页全路径）。

### 插件仓 jiuzhang-plugins
本卡零写入（HEAD 51776cf 不动，ahead 13 皆他卡）；parity 持 2.22.0、zip 不重打。
右栏「记号标准」入口（dashboard rail.js）原样可用，探针真点实证。

---

## 二、包结构自检

不适用——插件零改，未出包未重打 zip（卡§0：parity 持 2.22.0）。

---

## 三、三查结果（当次实跑）

- `bash scripts/check-plugin-boundary.sh`：**PASS**
  - 插件侧 fetch( 命中 **0**
  - 插件侧 parent.document 命中 **0**
  - 插件侧 localStorage 命中 **0**
  - 插件源码内无 Python 文件 ✓

---

## 四、测试与探针（当次实测数字）

**单测（`.venv/Scripts/python.exe -m unittest` 逐模块，禁 pytest/discover）**
- tests.test_norm_api：**8/8 OK**
- tests.test_latex_norm：**37/37 OK**
- tests.test_dict_console_subtabs：**17/17 OK**（钉死串保留实证）
- tests.test_dict_console：**14/14 OK**

**门禁**
- JS 语法全量逐文件 node --check：**82/82 pass**
- `bash scripts/check-quick-gate.sh`：**PASS（6 项全过）**；体积预警 23 份＝基线持平
  （norm_dict 271/css 246/subtabs 113/新探针 399/旧探针 371，均≤450）

**真机探针（Playwright 自驱 chromium，非内置浏览器）**
- 新探针 t6（工作台右栏真人路径，git-archive-HEAD 隔离，head=fe7bc9a）：**16/16 全绿**
  - 闭源自举 223 条目/271 变体；六列头＝名称/代码/来源/渲染/默认/操作；
    全过滤 rows=271＝/api/norm/entries 变体总数；名称格/恢复出厂键各 223（rowspan）
  - 砍头：面板 h2=0、面板「记号标准字典」文本=0、整机徽章=0、说明段=0、
    单枚标签条=0、pane=1；壳层仅两枚 sr-only 无障碍 h2（不动面，见§五-7）
  - radio 真点 le 组非默认 upright（id=43）：库 chosen=43/effective=43，
    wire choose POST 200（request{entry_key:le,variant_id:43}→response{chosen:43}）
  - 恢复出厂真点：DcDialog 确认→chosen=NULL/effective 回出厂，wire reset POST 200
  - chips 真点「关系不等」行数＝该族变体数＋族标全一致＋aria-pressed=true；
    搜索真点 leqslant 行数＝matches 同口径对账（收窄非空）；清空回 271
  - 开集待审区 h3 在位（norm_inbox 一字不动）
  - 375px：字典帧 doc=375/inner=375、listScroll=400（容器内横滚）、tableMin=760、
    宿主画布 host_doc=375——零横溢
  - 零引擎请求/零未捕获 JS/零 4xx/5xx/零控制台报错
  - 收口：port_closed_after_kill=true、orphan_processes=0、service_65496_untouched=true
- 旧探针 t6-standalone（独立 /dict 页不回归）：**18/18 全绿**，port_closed=true
  （含恢复出厂对话框 Esc 焦点归位、开集收编 zqprobe→leqslant/驳回 zqreject 全路径）
- 证据：`docs/handoff/evidence/norm-dict-table/`（probe.toml/wire.toml/
  standalone-probe.toml＋13 截图）；原始轮次产物 `.system_generated/norm-dict-table/t6/`、
  `.system_generated/latex-norm/ui/t6-standalone/`

**调试轮次如实记（t1–t5 红→t6 绿）**
- t1 红：隔离副本只拷 dashboard，引擎 schema 住 bank-engine 插件→meta/textbook-versions
  500；孤儿扫描 PowerShell 自身命令行含过滤串自匹配。修：copytree 加 bank-engine；
  Where-Object 排除 $PID。
- t2–t4 诊断：层 hidden=false、src 正确但帧文档从未加载——headless chromium 对视口内
  loading=lazy 帧偶不触发加载；探针侧 scroll_into_view_if_needed 即走（产品零改，见§五-5）。
- t5 4/5：①砍头 h2 断言过严（壳层 sr-only 无障碍标题误伤）→断言收口到面板；
  ②radio selector bug：le 组首行只含首个变体 radio，upright 在第二行→按 name+value
  全帧定位（新旧两探针同修）。
- t6 双探针全绿收口。

---

## 五、未决问题与偏离

1. **§3「只这两处」偏离加升三枚**：主公已 Ctrl+F5 取过今日戳（20261119）的卡片版
   norm_dict.js/css，subtabs.js 旧戳 20261113g 也早被缓存——URL 不变则 returning 用户
   缓存吃掉§1/§2 改形，重演「找不到按钮」同根因。故三枚改过资产升 `?v=20261119b`
   （dict_console.html:25,138,150），commit fe7bc9a 信息已登记。卡面点名的两处照升不误。
2. **宿主升版自判不升**：app/__init__.py=1.2.0 单源；本卡是 UI 改形非封版，
   2.21.0/2.22.0 列车号属插件，先例各卡均未动宿主版；test_version_consistency 契约绿。
3. **CSS 共用类保留**：`.dc-norm-head`/`.dc-panel-hint` 被 norm_inbox.js（开集待审 h3 块）
   与看板共用，只摘 `.dc-norm-machine-badge` 一段；删共用类会弄坏不动面。
4. **证据扁平化（分层≤3 解读）**：docs/handoff/evidence/norm-dict-table 已是第 3 层，
   不开 shots/wire 子目录，截图 shot-* 前缀平铺、wire.toml 平铺。
5. **headless lazy 怪癖（探针侧规避，产品零改）**：headless chromium 对视口内
   loading=lazy iframe 偶不触发加载；探针 scroll_into_view_if_needed 后即走。
   stage_dict_view.js 不在本卡改动面，真人浏览器无此问题；不改产品。
6. **旧探针基础设施未改**：latex_norm_ui_probe.py 仍用工作树 cwd（2.21.0 旧设计），
   本卡只同步断言不动基础设施；新探针已按卡§4 git archive HEAD 隔离。
7. **壳层 sr-only h2 属不动面**：dict_console.html:60,95 两枚无障碍标题
   （全局设置/字典分类）非面板标题，砍头断言收口到 `.dc-subpanel` 范围＋壳层 h2
   必须全带 dc-sr-only 类，双向钉死。
8. **push hold**：两仓不 push（主公明确不授权别再问）。operator ahead 46
   （他卡在途 42＋本卡 4），plugins ahead 13（本卡零写入）。
9. **豁免面照旧**：tools/onnx_probe.py untracked 不碰不 stage；plugins 仓
   model_prefs.toml＋models/ 原地保留；65496 正式服务零接触（探针隔离副本＋随机端口）；
   工作树他卡在途改动零 stage 零恢复。
10. **遗留欠账照挂（非本卡面）**：记号字典条款级出处与存量回写欠账（2.21.0 起）不动；
    体积预警 23 份排队拆名单不因本卡增减。
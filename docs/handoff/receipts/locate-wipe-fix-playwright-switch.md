# 回传单 · 抹边修复＋取证换 Playwright 合并卡（A→B→C→D）

【回执编号】 #LWF-01
【回执时间】 2026-11-18T20:55:32+08:00
【实际耗时】 21 分 46 秒（首件落地 requirements.txt 20:33:46 → 收口读数 20:55:32，mtime/系统钟实测；不含卡前读律）
【执行结果】 成功：A 换装冒烟 5/5；B 裸跑复现抹边（Δ162ms）；C 修复行数零增长＋版本 2.13.1；D 描边持久 3217ms≥3s、3 样本切题率不降、定向 262 例全绿、快门禁 6 项 PASS

正文逐条对齐卡§0–§5；biz 记录 `.qoder/records/biz/2026-11/20261118_locate-wipe-fix.md`；
sys 记录 `.qoder/records/sys/2026-11/20261118_skill_playwright-evidence-switch.md`。

## 【改动清单】

底座仓 jiuzhang-operator：
- 修改：`requirements.txt:10-12` —— playwright 不钉版行替换为 `playwright==1.65.2`＋实测口径注释（首次安装钉版，卡授权）
- 修改：`.qoder/skills/domain/prove-visual-change/SKILL.md` —— 取证动线换装重写：Playwright 默认驱动（宿主＋iframe 全工具化）、真人点降可选抽检、仪表规矩成文（隔离副本＋拍完恢复＋回单披露）、browser-use 降备选两坑写明
- 修改：`tests/test_command_registry.py:487` —— 版本断言 2.13.0→2.13.1（卡点名授权这一行）
- 修改：`plugins.toml:51` —— version 2.13.1（tools/sync_plugin_index.py 写入）
- 新增：`.qoder/records/sys/2026-11/20261118_skill_playwright-evidence-switch.md`（R00 sys 记录）
- 新增：`.qoder/records/biz/2026-11/20261118_locate-wipe-fix.md`（R00 biz 记录）
- 新增：本回传单

插件仓 jiuzhang-plugins：
- 修改：`src/org.jiuzhang.editor/dist/ui_columns.js:537-538`（renderAll 清栏前捕获 located 页索引）、`:544-545`（renderScanGallery 重建后按索引补回描边）——抹边修复本体，4 行；删旧 775/778/779 三个值传递死导出（renderTimer/scrollLock/scrollRestore）与旧 146 双空行之一 offsets；**788→788 行零增长**
- 修改：`src/org.jiuzhang.editor/dist/core_selection.js` 删旧 282-283 两个同类死导出（selectionTimer/worklistTimer）；**289→287**
- 修改：`src/org.jiuzhang.editor/plugin.toml:4` —— version 2.13.0→2.13.1
- 修改：`plugins.json:68` —— editor 条目 version 2.13.0→2.13.1（sync 工具不代写远端 JSON，手升保 parity）
- 禁改区自查：LICENSE / 根 agents.md / AGENTS 铁律一二 / `app/core/question_contract.py` / 用户 `data/` —— **否**，均未触碰（git status 仅上列名单；取证全程 JZO_DATA_DIR/JZO_PLUGINS_DIR 隔离副本）
- 不 stage：底座 `tools/onnx_probe.py`、插件仓 `src/org.jiuzhang.editor/models/`（照卡原地保留）
- git 口径：两仓各单 commit、stage 逐个点名；不 push（枢纽推）、不 amend、不改写历史

## 【包结构自检】

- 顶层目录名 `org.jiuzhang.editor` == plugin.toml `id`？是
- 有无 backend 字段？无（grep plugin.toml 命中 0）
- Apache-2.0 LICENSE 全文？在（`src/org.jiuzhang.editor/LICENSE`，首行 Apache License）
- min_host_version / engine.host_version 与底座关系：plugin.toml `min_host_version="1.0.0"`，无 engine.host_version 字段；当前底座 `app.__version__=1.2.0`（/healthz 实测），满足下限

## 【三查结果】

命令：`grep -c "fetch(" dist/*.js`、`grep -c "parent.document" dist/*.js`、`grep -c "localStorage" dist/*.js`（插件 src/org.jiuzhang.editor 下实测）
- `fetch(` 命中 **0**（全部文件 :0，无非零行）
- `parent.document` 命中 **0**
- `localStorage` 命中 **0**
- 请求 id：本刀未新增插件请求族，宿主 relay 白名单未动；既有 id 口径不变（`^[A-Za-z0-9_-]{1,80}$` 不含点号）

## 【测试与探针】

- 单测（`.venv/Scripts/python.exe -m unittest` 逐模块，20:53 实测）：
  tests.test_command_registry **34/34 OK**；tests.test_editor_contract **174/174 OK**；
  tests.test_a2_image_ingest **20/20 OK**；tests.test_ingest_failure_surface **10/10 OK**；
  tests.test_plugin_index **24/24 OK** → 合计 **262 例全绿**
- 门禁：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**（20:54 实测；WARN 23 份既有拆分队列，与 A2 轮同）
- 真机（Playwright 隔离实例，非 browser-use）：
  - ev1=127.0.0.1:65512（修复前插件副本＋A2 数据副本）、ev2=127.0.0.1:65513（修复后副本）；
    收口 `taskkill //PID 21348` / `//PID 13064` 点杀（禁 /IM 口径遵守）；不碰用户 data/ 与 65496
  - Part A 冒烟 **5/5 PASS**：`.system_generated/locate_wipe_fix/smoke/smoke_result.json`
    （sandbox=allow-scripts allow-modals 未加 allow-same-origin；穿 iframe DOM 断言 4 批次卡＋
    徽标「1 份未自动切出」；iframe 内真点击展开失败清单两条、启用态 [True,False]）；截图 smoke_iframe.png
  - Part B 复现 **WIPE REPRODUCED**：`.system_generated/locate_wipe_fix/ev1/repro_result.json`
    ——描边 +110ms 加（page index 4＝原卷第 5 页）→ +272ms 整栏重建 removed 5 抹掉（**Δ162ms**，
    与 A2 ~174ms 同口径）；终态 located=false；截图序列 seq_02_t151ms_located1.png（琥珀描边在场）
    vs seq_04_t369ms_located0.png（同滚动 871 描边消失）＋共 16 帧
  - Part D 描边持久 **PERSIST >=3s PASS**：`.system_generated/locate_wipe_fix/ev2/verify_result.json`
    ——+125ms 加描边；+286ms 回声重建仍发生但**同毫秒描边补回新节点**（修复生效的直接证据）；
    加后全部轮询 located=true；终态 t=3342ms located=true、page=4、scrollTop=871 → **持久 3217ms**；
    截图 fix_seq age 0.5/1.5/3.0s 三帧描边均在＋fix_final_full.png
  - Part D 切题率回归 **3/3 PASS**：`.system_generated/locate_wipe_fix/ev2/api_result.json`
    ——3 份样本只引用不复制、重新入批 B-005/006/007：dbsdfz **20/20**、yz **21 落池/应切 22**
    （漏 yz14 同 A2）、qz **20 落池/应切 21**（漏 qz16 同 A2）；逐页题号集合与 A2 ev1 全等；
    占位/无图/短题干全 0；failures 0。质量判定口径本卡明示：占位＝题干含「待识别」、
    无图＝question.images 空、短题干＝去空白 <8 字符
  - ev2 上 UI 验收与 API 回归曾并行同实例（互不沾改动面：UI 只读 B-004，回归只写新批）；
    首轮 UI goto 超时系 OCR 后台占 CPU，回归跑完后重跑即绿，如实披露
- 前端真人路径：工具经 CDP 发真实输入事件走全 开批→等页图→回列表→徽标→失败清单→【定位原卷页】
  （含键盘可达冒烟外的主路径）；**真人抽检未做**——卡降为可选，直说
- 未跑全量回归（主公 2026-11-18 豁免口径）；未重铺 59（卡禁）

## 【未决问题与偏离】

- 偏离：① 清华 pip 源查无 playwright（`from versions: none`）改阿里云镜像装成；chromium 官方
  CDN 实测 ~90KB/s 过慢改 npmmirror 镜像（`PLAYWRIGHT_DOWNLOAD_HOST`）——仅下载通道替换，
  内核文件与许可（Apache-2.0）不变；② 卡 sys 记录路径缺 R00 类型段，按先例补 `skill_`；
  ③ sync_plugin_index.py 只写本仓 TOML、不代写远端 JSON（工具源码明写），插件仓 plugins.json
  手升同版否则 parity 门禁红；④ 复现首轮 scroll=0（页图未加载时整栏 fit 视口、scrollIntoView
  无处可滚，截图拍不到第 5 页）→ 改为先开批等页图加载再回列表点 locate，属走全用户路径的预热，
  **非仪表改动**（未冻定时器、未破沙箱、未改产品代码）；⑤ 为行数零增长删 5 个值传递死导出
  （导出初始值快照、全仓零引用；test_editor_contract 只断言内部语句不受影响）
- 欠账：T6 未做（卡禁顺手）；23 份 WARN 拆分队列既有；A2 欠账①–⑤ 不在本卡范围照旧
- 解释性口径：切题率＝落池/应切（答案区不计应切），复用 A2 #A2-01；抹边判定＝描边加上后
  整栏 childList 重建（旧节点整块丢弃不发 class 事件）且终态无描边
- 未验证：真人抽检（卡可选未做）；双栏卷跨页/59 铺量（卡禁）；chromium 下载后断网离线复跑
  未专门验证（本轮取证浏览器内核均走本地缓存、服务全本地，无出网依赖）
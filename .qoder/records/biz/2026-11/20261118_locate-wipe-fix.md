# 抹边修复＋取证换 Playwright 合并卡 · biz 记录（2026-11-18）

> 状态：已收口（两仓各单 commit，待枢纽 push）
> 发起日期：2026-11-18
> 卡范围：A 取证换装 Playwright（安装钉版＋穿沙箱冒烟＋SKILL 换装＋sys 记录）；
> B 用新工具裸跑复现抹边；C 修抹边（core_selection.js/ui_columns.js 两文件，版本 2.13.1）；
> D 验收（描边持久 ≥3s＋3 样本切题率不降＋定向 unittest＋快门禁）。T6 不许顺手做。
> 证据底稿：A2 #A2-01 欠账⑥＋偏离②（`.system_generated/a2_image_ingest/ev1/locate_wipe_evidence.json`）。
> 回传单：`docs/handoff/receipts/locate-wipe-fix-playwright-switch.md`。

## [REQ] 2026-11-18

背景：A2 真点复验发现【定位原卷页】描边 `is-fail-located` 加上后 ~174ms 被选区回声的
120ms debounce 全量重渲染抹掉（`core_selection.js:265 → ui_columns.js:589-591`）；
且旧取证靠 browser-use 伸手＋冻定时器/加 allow-same-origin 摆拍，主公拍板换装。
验收标准：① Playwright 穿沙箱 iframe 冒烟（DOM 断言＋真点击，不破沙箱不冻定时器）；
② 追帧裸跑复现抹边（复现不了停下报枢纽）；③ 修后描边持久 ≥3s；④ 3 样本切题率不降
（20/20、21/22、20/21 口径复用）；⑤ 定向 unittest＋快门禁绿；⑥ 行数零增长优先。

## [IMPL] 2026-11-18

- 换装：`playwright==1.65.2` 钉版进 requirements.txt（清华源查无此包改阿里云镜像；
  chromium v1255 官方 CDN ~90KB/s 过慢改 npmmirror 镜像，一次性下载后离线可用）；
  `.qoder/skills/domain/prove-visual-change/SKILL.md` 重写为 Playwright 默认驱动、
  真人点降可选抽检、仪表规矩成文、browser-use 降备选两坑写明；
  sys 记录 `20261118_skill_playwright-evidence-switch.md`（卡路径缺 R00 类型段，补 skill_）。
- 复现（ev1，修复前插件副本＋A2 数据副本，65512）：`repro_wipe.py` 挂 MutationObserver＋
  状态轮询＋连续截图裸跑。先开批等页图加载再回列表点 locate（页图没长高时
  scrollIntoView 无处可滚，截图拍不到第 5 页——预热是走全用户路径，非仪表改动）。
- 修法（ui_columns.js renderAll）：清栏前捕获 `.ed-page-cell.is-fail-located` 的
  data-page-index，renderScanGallery 重建后按索引找回新节点补回描边（4 行）。
  语义不变：描边仍由 locate/页徽标点击唯一授予，重渲染只是不再弄丢它。
  不延长 debounce、不冻定时器、不破沙箱。
- 行数零增长：删 ui_columns.js 三个值传递死导出（renderTimer/scrollLock/scrollRestore，
  导出的是初始值快照、全仓零引用）＋一处双空行；core_selection.js 删两个同类死导出
  （selectionTimer/worklistTimer）。788→788、289→287。
- 版本单源：plugin.toml 2.13.0→2.13.1；tools/sync_plugin_index.py 写本仓 plugins.toml；
  插件仓 plugins.json 手升同版（工具不代写远端 JSON，只报语义漂移）；
  tests/test_command_registry.py:487 断言升 2.13.1（点名授权一行）。
- 使用的 skill：prove-visual-change（换装后首用）、sync-sys-record、sync-biz-record。

## [VERIFY] 2026-11-18

- 冒烟 5/5 PASS（smoke/smoke_result.json）：sandbox=allow-scripts allow-modals 未破；
  穿 iframe DOM 断言 4 批次卡＋徽标文案；iframe 内真点击展开失败清单、启用态 [True,False]。
- 复现（ev1/repro_result.json）：描边 +110ms 加（page index 4）→ +272ms 整栏重建
  removed 5 抹掉（Δ162ms，与 A2 ~174ms 同口径）；终态 located=false；
  截图 seq_02_t151ms（第 5 页琥珀描边在场）vs seq_04_t369ms（同滚动 871 描边消失）。
- 修复验收（ev2/verify_result.json，65513）：+125ms 加描边；+286ms 回声重建仍在发生，
  但同毫秒描边补回新节点；加后全部轮询 located=true；终态 t=3342ms located=true、
  page=4、scrollTop=871 → 持久 3217ms ≥3s；截图 age 0.5/1.5/3.0s 三帧描边均在。
- A2 不回归（ev2/api_result.json，重新入批 B-005/006/007）：20/20、21/21 落池
  （应切 22 漏 yz14 同 A2）、20/20（应切 21 漏 qz16 同 A2）；逐页题号集合与 A2 全等；
  占位/无图/短题干全 0；failures 0。口径：占位＝题干含「待识别」、无图＝images 空、
  短题干＝去空白 <8 字符（本卡明示，A2 轮全零同口径）。
- 定向 unittest（.venv/Scripts/python.exe -m unittest 逐模块）：test_command_registry 34、
  test_editor_contract 174、test_a2_image_ingest 20、test_ingest_failure_surface 10、
  test_plugin_index 24 → 262 例全 OK。快门禁 PASS 6 项（WARN 23 既有拆分队列）。
- 三查：插件 dist fetch(/parent.document/localStorage 全 0；包结构 id==目录名、无 backend、
  Apache-2.0 LICENSE 在；min_host_version 1.0.0 ≤ 底座 1.2.0。
- 隔离与收口：ev1=65512/ev2=65513，JZO_DATA_DIR/JZO_PLUGINS_DIR 全隔离，不碰用户 data/
  与 65496；收口 taskkill //PID 21348/13064 点杀。截图与 json 全留
  `.system_generated/locate_wipe_fix/`（不进 git）。
- 未跑全量回归（主公 2026-11-18 豁免口径）；T6 未做（卡禁）。
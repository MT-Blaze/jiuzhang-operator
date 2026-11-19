# MinerU 云上传修实＋L2 复测（mineru-put-fix）

状态：部分成功（上传链修实绿；L2 13/20 回填红，解析缺口另卡待裁）
发起日期：2026-11-19
需求来源：枢纽 aa2dcda2（Typst替代LaTeX可行性）转达主公点头「先修 MinerU」＋mineru-put-fix 任务卡
基线：operator 0e5f7cc ／ plugins 87e1729（零写入）；修实 commit e49606a

## [REQ] 2026-11-19

typst-bench（b5125849）L2 红：MinerU 云一卷 3 页 20 题，OSS PUT 40 次全 403
SignatureDoesNotMatch（EC 0002-00000040），0/20 回填，额度 0 页。根因候选：
mineru_extract.py:49-50 给 raw PUT 强加 Content-Type: application/octet-stream，
而 MinerU 签名 URL 未把该头签进去（官方文档明说上传无须设置 Content-Type）。
卡令：先真证（同 URL 双 PUT，防 urllib 自动补头陷阱）→ 修实限上传链 → 定向回归 →
隔离宿主界面真点 L2 复测 → 绿才双吐续跑；部分回填如实报数不装绿。

## [IMPL] 2026-11-19

- §1 真证：http.client 直发双腿＋send 钩子录实际出网头。A（带 octet-stream）403、
  B（线上真无头）200，假设证实；urllib 无显式头自动补 x-www-form-urlencoded 本机回环实证。
- §2 修实：_request 删 raw 分支；新增 _put_raw（http.client 直发，零 Content-Type，
  签名 query 原样透传，非 2xx 抛 HTTPError）；extract 改调＋HTTPException 入 except。
  POST JSON 分支不动；178 行 ≤400。
- §3 测试：tests/test_mineru_extract.py 6 用例（本机回环实收头断言，urllib 自动补头
  情形可被抓）；定向 7 模块 113/113 绿＋快门禁 PASS。commit e49606a。
- 版本口径：修实非发版，宿主 __version__ 持 1.2.0（历史仅封版升）；parity 持 2.21.0，
  plugins 零改 zip 不重打。
- §4 host2：git archive e49606a＋plugins archive 87e1729（editor＋bank-engine）＋
  data2 副本；动态端口 4863＋随机令牌；钩子 v2 纯内存（适配 _put_raw 新形状）。

## [VERIFY] 2026-11-19

- L2 界面真点（Playwright 穿沙箱）：201；422.4s 收口；20/20 POST code 0；
  20/20 PUT 200；20/20 extract ok；20 份 full.md 逐字取证。
- **13/20 回填、failures 1 条＝按卡绿口径红**。stem 与 run1 本地切图逐位比对 13 道
  全不同＝真回填零冒充。
- 剩余 7 题（3/6/10/11/13/14/15）：MinerU 转写正确；build_documents 本机只读复核
  7 份全 0 文档（对照 1/2 各 1）。四类形状：选项独立成行／卷首图片行／整题 $$ 包裹＋
  题号拆字／填空 \_\_\_\_。缺口在解析段，超卡范围停报，建议另卡。
- 额度：§1 探针 1 页＋L2 逐题切图 20 页＝21 页（卡面 3 页系源 PDF 页数口径，偏离披露）。
- §5 双吐按门禁未跑（脚本备妥 0 调用）；是否放行待枢纽裁。
- 收口：stop2.signal→CTRL_BREAK rc=3；端口 4863 复验 0；孤儿零。
- 回单：docs/handoff/receipts/mineru-put-fix.md（MPF-01，五项＋红线逐项）。
- 两仓 push hold。

## [VERIFY-2] 2026-11-19 §5 双吐续跑（枢纽复核全过＋放行裁）

- 直调 6/6 PASS 零重试（3 探针×LaTeX/Typst，同席 qwen4-max-preview）：
  latex 合计墙钟 19.8s／token 2768（completion 833 含 reasoning 399）；
  typst 30.2s／3254（1304 含 931）。raw 逐字 wire/fix_dual_calls.md＋raw_fix/。
- 渲染对照（零出网）：MathJax 3/3（0.97/0.74/0.70s）；typst 2/3（0.34/0.30s）。
  失败逐字 TypstError: unknown variable: ABC＝模型 Typst 腿 $ABC$ 多字符数学标识符
  语义差异（LaTeX 腿同处合法），非编译器缺陷。字形目检两腿箭头/分数/中文均正常。
  只摆事实，不排座不写弃用结论。总账 fix_probe.toml＋renders/×5。
- ahead 更正：rev-list 实测 32（原回单 ahead 2 误，只数本卡两笔）；补充节 commit 后 33。
- 范围锁死：零产品改动／零新 pip／出网仅 6 直调／7 题解析缺口未修（另卡待用户点头）／
  65496 零接触／push hold。回单补充节 append（不 amend），新 docs commit。
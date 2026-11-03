# S6d carrier3 收尾对账（2026-11-03 18:2x）

## 载体 s6dcarrier3：14 检 8 过 6 败（上一轮 5/8）
| # | 检查 | 状态 | 归因 | 证据 |
|---|------|------|------|------|
| C1 | 开机链 | PASS | — | s6dcarrier3-browser-result.json |
| C5 | 空池留白 | PASS | — | 同上 |
| C5b | 池列表取数链 | PASS | — | 同上 |
| C6 | 琥珀灯像素 | **PASS** | 修③解锁；bg=outside_above，α≈0.5 | s6b-shots/s6dcarrier3-06-amber-frame-*.png |
| C3 | 池画布 | **PASS** | 修④解锁（不点 #epPoolEntry 全 hidden） | s6dcarrier3-03-pool-canvas.png + dom.json |
| C9 | Esc 二次确认 | PASS | — | — |
| C7 | 全部入库被灯拦 | PASS | — | — |
| C1b | 零 pageerror | PASS | — | counts 0/0/0 |
| 造现场 | certain 档缺失 | FAIL | 夹具考向 t_s6b_probe 未入大纲→approve 被拦→主库未进新行（main_scanned=456）→dup 只剩 possible | s6b-shots/s6dcarrier3-00-seed-and-tiers.json |
| C2×2 | 红灯无/对照有 | FAIL | 探针色带过松：r>=150,g<=110,b<=120 把橙色装饰 (187,106,29)(156,74,29) 判进红族；danger(211,51,51) 像素在两图均不存在 | 离线全图扫（见回传） |
| C4 | 三档 | FAIL | #epPoolTiers 钮 resolved-to-hidden ×23，同「默认收起」行为口径族 | result.json |
| C8 | 清洗双入口 | 部分结案 | HTTP 侧修 URL 后 **200 complete**；钮点击未执行(clicked=[],待查 disabled/时序) | result.json + base_route_body |
| C6b | reduced 两帧全等 | FAIL | 定性未结案：两帧 223,574 字节差、自 y=33（卡顶环带行）起大范围分布；与同轮 s6damber3 ::before anim=none/opacity 0.5 静态互相矛盾，不能下「动画没停」结论也不能排除 | s6dcarrier3-06-reduced-a/b.png |

## 收尾对账（census s6dtab1，未重跑）
- approve 三条：p_d35350a1→422、p_4775155c→**200**(created，q_1e02f46e65a1fd36b74ade77)、p_74395c04→422；
  原始报错行：`题目不符合 Schema / taxonomy.topic_ids: 大纲里没有节点 't_s6b_probe'，请先把考向补进大纲树。`
- 批次 POST 均为 201；「新建题目」的响应码是 200 不是 201（如实报）。
- questions 456→457、main_scanned=457、首读 pool total=4（3×certain/100 全指 q_1e02f46e + 1×possible/33 q_legacy_000074）、终态 duplicate_pool_rows=6（首读与 6 行只差 2 行=后台链在 HTTP 读后才补写；pool_actions_rows=0 行）。
- census 查 dedupe_scans 报 `no such column: updated_at`（普查 SQL 口径错，披露）。

## 本轮四处探针修改（tools/pool_canvas_probe.py，逐 hunk）
1. edge_band `w,h,_ch,buf`→`w,h,ch,buf`（修③ NameError 'ch'）。
2. c3_pool_canvas 前插 #epPoolEntry aria-expanded=false 时点击展开（修④）。
3. best_family 背景参考：盒外上方 14px（outside_above/left，fallback 标注）（第四节授权）。
4. C8 URL `/api/text/clean-latex`→`/api/agent/clean_latex`（404 定论=探针写错；真实路由 agents.py:19+:399，全仓无 /api/text；mode=exam_source 合法 :58/:410，响应 200）。
（①②frame_with/reopen 为前轮已授权修改，本轮未动。）

## 产品未改一字节；未 commit；未碰真 data/。

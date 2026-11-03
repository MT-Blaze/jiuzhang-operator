# S6d 追加事实棒 收尾记录（2026-11-03 18:07）

## ③ 琥珀灯像素 — 结案（两档证据）
- DOM+同轮坐标：`s6d-escamber-s6damber3.json`
  - 选中卡 `data-amber=on`、reasons=「还没挂考向」、computed `::before` =
    `rgb(192,138,46) 0 0 0 2px inset, rgba(192,138,46,0.4) 0 0 22px inset`，opacity 0.5（上下文 reduced_motion=reduce，静态档）
  - iframe 偏移同轮实测 [245,43]，环带 rect [675,76,450,335]
- 像素量化：`s6d-amberchroma-s6dchroma1.json`（纯离线复扫已存 PNG）
  - 整页环带 2003/3124 命中琥珀色度带（R>G>B、R−B≥45），卡内对照 0/30、卡外对照 0/840
  - 元素图环带 1558/3128 命中，环带代表色 (188,168,127)
  - 截图：`s6d-shots-s6damber3/s6damberpx-s6damber3-page.png` / `-element.png`
- 说明：s6d_crop_scan 单层 α 求解 count=0 不是「琥珀不存在」——底座是
  帧米色 (216,204,184) + 卡内 (239,242,241) 两层，0.5 静态琥珀叠上去残差必超 err≤8；
  判据改用色度带后闭环。此口径差异已如实记录，未改生产代码。

## ④ Esc 二次进入 — 结案
- `s6d-reentry-s6drent2.json`：pool→(焦点入画布帧+Esc)→list→再点 trigger→pool(dup=on)→再 Esc→list，pageerror 0，verdict PASS。
- 首跑 s6drent1 FAIL 为探针夹具漏建「同题面第二批入池」（池 0 条 ⇒ 入口按钮 hidden），
  属测试侧缺陷，补夹具后重跑，未动业务代码。

## 3.5 判据（此前棒，复核在案）
- `s6d-proof35` 结果（tag s6dproof2）：approve 200 ×4，池内 4 条全 certain 100%，
  main_id 均为主库新 qid（q_d1f324 / q_9b85b8 / q_92cd57 等），all_main_are_new_ids=true。

## 遗留
- 载体复跑 s6dcarrier2 的 8 FAIL（造现场 NameError 'ch'、隐藏行）仍是探针自身缺陷，未清。
- 全链未 commit（未获授权）。

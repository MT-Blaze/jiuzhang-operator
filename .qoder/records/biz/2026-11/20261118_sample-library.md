# 测试样本库·分类与代表复制（枢纽 promote 自执行回单）

回执编号：#SL-01（枢纽流水）｜执行会话 81b715c9｜2026-11-18
库定位＝本地弹药库（test_papers/，已进 .gitignore:20），非全量验收；manifest 随库本地留存。

## REQ / PLAN
两目录（E:\Math\高中\高三专用\模拟考试 递归＋D:\WeChat\...\2026-11 顶层）335 份 PDF，
优先数学考试卷；分类＋每类代表复制进 test_papers/ 平铺，完善切题规则靶子。
卡令：git 全禁（零 tracked 改动）、压缩包只登记禁解压、几何探针≤80、不硬凑缺口。

## IMPL（产物全在 ignored 区）
- test_papers/ ×19：18 代表 PDF 平铺＋manifest.toml，命名 <类字母><序号>_<原名>.pdf。
- manifest：[meta] 335/317/18/219/98/80/18；[[sample]]×18（class/sha256/pages/median_ratio/avg_chars/geom 量）；
  [[gap]]×4；[[excluded]]×98 逐件理由；[[duplicate]]×18；[[backlog]]×268（zip/rar/7z/docx/xlsx/音视频只登记名）。
- .system_generated/sample_library/：探针脚本＋cheap_probe/rows_*/geom_*/analysis/classes/thumbs 全产物。

## VERIFY
- 阶段一便宜探针 335 全探 0 错 34s；sha256 去重 18（317 唯一）。
- 阶段二几何探针恰 80（70 批＋6 followup＋4 final，未超帽）14m36s；RapidOCR 行＋x 覆盖沟检测。
- 全 80 分布 A27 B0 C34 D2 E3 F0 G3 H1 I10；代表 18＝A3 C3 D2 E3 G3 H1 I3。
- 哈希三重核（copy==source==cheap）＋枢纽独立抽 6 份再核 bad=0；平铺 19 子目录 0。
- 目视缩略图约 30 张（G 斜水印/H 通栏压栏/D 双栏/E,I 摊页双证）。
- 门禁：git diff --cached 空；status 对 test_papers/.system_generated 空；check-ignore 命中 :20/:18；
  任何 tracked 零改动（diff 15 件全为配置卡在途，只登记不卷）。

## 缺口与偏离（登记不硬凑）
- B 双栏文字缺 3、D 双栏扫描缺 1、F 手拍歪斜缺 3、H 通栏压栏缺 2；候选名在 [[gap]]，多压于 268 压缩包 backlog。
- 新增 I 摊页文字型（卡允许实测增减）；G 斜淡水印 OCR 漏检靠目视＋机械足印；H 判据收严"通栏顶带压两栏栏身"。
- 欠账：geom_summary 只覆盖 1–70（71–80 在逐件 geom，manifest 已回落）；B/D/F/H 待后续入库或开包补靶。

## 红线自查
零代码改动、零 tracked 写、未 commit/push（执行会话）；禁改区未碰；无服务无端口；后台批已退出。
枢纽 promote 仅新增本记录，不卷配置卡 b61f902。
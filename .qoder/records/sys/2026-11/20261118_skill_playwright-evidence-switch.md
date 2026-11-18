# 取证默认驱动换 Playwright：宿主＋沙箱 iframe 全工具化

- 日期: 2026-11-18
- 类型: skill
- 执行者: 抹边修复＋取证换装合并卡执行会话（99753adf）
- 等级: L1

## 变更内容

主公拍板（合并卡 Part A）：取证从此默认 Playwright 驱动，不再烦主公伸手真人点、
不再靠冻定时器/破沙箱追截图。

1. **依赖钉版**：`playwright==1.65.2` 进 `.venv`（Python 3.14.6 实测装成，随带
   greenlet 3.5.6）；requirements.txt 原不钉版行替换为钉版＋实测口径注释。
   清华源当时查无此包（`from versions: none`），改阿里云镜像装成；chromium 内核
   官方 CDN 实测 ~90KB/s 过慢，换 npmmirror 镜像（`PLAYWRIGHT_DOWNLOAD_HOST=
   https://cdn.npmmirror.com/binaries/playwright`）下载 chromium/headless-shell
   v1255（Chrome 159.0.8154.6），落地 `%LOCALAPPDATA%/ms-playwright/`，之后离线可用。
   许可 Apache-2.0，过铁律一白名单。
2. **穿沙箱冒烟实证**：隔离实例 65512（ev1 数据副本＋修复前插件副本），
   Playwright `frame_locator` 穿透 `sandbox="allow-scripts allow-modals"` 的
   opaque-origin 插件 iframe：DOM 断言（4 张批次卡、B-004 徽标文案）＋iframe 内
   真点击（失败清单展开、页级启用/批次级禁用）全通。全程未加 allow-same-origin、
   未冻任何定时器。证据 `.system_generated/locate_wipe_fix/smoke/`
   （smoke_iframe.py / smoke_result.json / smoke_iframe.png）。
3. **SKILL 换装**：prove-visual-change 取证默认 Playwright（宿主 page.locator＋
   插件 frame_locator）；真人点降为可选抽检（核心路径一两下口述确认非必须）；
   取证仪表规矩成文——任何仪表改动只许隔离副本＋拍完立即恢复＋回传单披露
   （A2 偏离②先例口径）；内置 browser-use 降为备选，两坑写明（面板隐藏态、
   evaluate_script 穿不透 opaque-origin 沙箱）。

## 涉及文件

- 修改：`requirements.txt`（playwright 钉版 1.65.2＋注释改实测口径）
- 修改：`.qoder/skills/domain/prove-visual-change/SKILL.md`（取证动线换装重写）
- 新增：本记录
- 证据（不进 git）：`.system_generated/locate_wipe_fix/smoke/` 三件

## 验证结果

- 冒烟 5/5 PASS（smoke_result.json 当次实测）：沙箱未开 allow-same-origin、
  批次卡 count=4、徽标「1 份未自动切出」、失败清单两条在场、启用态 [True, False]。
- 命名偏离说明：卡路径写 `20261118_playwright-evidence-switch.md` 缺 R00 类型段，
  按 R00 与既有先例（20261118_doc_layering-depth-cap.md 等）补 `skill_` 段。
- 环境坑登记：Windows GBK 控制台打印 ⚠ 崩（脚本须 stdout.reconfigure utf-8）；
  本机旧内核缓存 chromium-1248 与新钉版所需 1255 不通用，换版须重下内核。
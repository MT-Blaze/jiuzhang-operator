---
name: prove-visual-change
description: 九章算子前端与视觉改动的证据动线：Playwright 全工具驱动真浏览器（宿主＋沙箱 iframe）走用户路径、追帧、截图、像素扫描取行段结论，并处理 A4 分页/画布/布局类量测坑。当改过 CSS、布局、A4 排版、画布、插件界面，或用户说"我要看到效果/像素证据"时使用。
---

# prove-visual-change：视觉改动的像素证据

> 原子范围：只负责"证明界面真的变成想要的样子"，不改逻辑。
> **[L0] 用户已两次拒绝"几何达标"口径**：SVG 几何全对但没设 stroke 会整条不可见。只报"代码改了"不算验证。
> **2026-11-18 换装裁决**：取证默认 Playwright 驱动，宿主＋插件 iframe 全工具化；真人点降为可选抽检。

## 步骤

1. **起隔离实例**：取证一律隔离——`JZO_DATA_DIR` 指证据目录下的 data 副本、`JZO_PLUGINS_DIR` 指插件隔离副本、`JZO_PORT` 独立端口、`JZO_LOCAL_TOKEN` 固定令牌，`.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port <独立端口>` 起服。**不碰用户 `data/`、不碰 65496 正式服务**；收口 `taskkill //PID <pid>` 点杀（禁 `/IM python.exe`）。`start.bat` 只留给真机抽检复用既有实例。
2. **Playwright 驱动真浏览器（默认）**：`.venv` 里钉版 `playwright`（requirements.txt）＋ `playwright install chromium` 内核（一次性下载，之后离线）。
   - 宿主页面用 `page.locator(...)`；插件沙箱 iframe 用 `page.frame_locator('iframe[title="<插件名> 画布"]')` 直接穿透——**CDP 协议层不受 opaque origin 限制**，DOM 断言、真点击、键盘、上传全在工具内完成，不给 iframe 加 `allow-same-origin`、不冻任何定时器（2026-11-18 冒烟实证：sandbox=allow-scripts allow-modals 下断言＋点击全通）。
   - `locator.click()` / `press_key()` 是工具经 CDP 发的真实输入事件，走完整命中测试与焦点链，**算真人路径**；程序化 `focus()`、`dispatchEvent` 仍不算。
   - 毫秒级竞态用**自动追帧**取证：iframe 内挂 MutationObserver 记事件时序＋连续截图序列，相机追得上 ~174ms 的描边抹除这类缺陷，不再靠冻定时器摆拍。
   - Windows GBK 控制台打印 ⚠ 等字符会崩：脚本开头 `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`。
3. **真人点降为可选抽检**：核心路径留一两下主公口述确认即可，非必须；工具驱动走通主路径＋边界（375px 不横向溢出、触控目标 ≥44px）＋键盘可达与焦点可见＋弹窗 `Esc` 与焦点还原。
4. **截图存档**：关键态各截一张，落 `.system_generated/<场景>/<tag>/`；同时记录视口尺寸。
5. **像素证据**：`.venv/Scripts/python.exe tools/pixel_scan.py <png>` 按 PAPER/CARD/DARK 归类打印行段（`:100-115`）——用它证明"某条线/某个框真的在某个 y 区间有色值"。
   - **[L1] `pixel_scan.py` 无判定、恒 rc=0**：它是素材，不是门禁；结论要自己写在证据里。
6. **取证仪表规矩（A2 偏离②先例口径，长期生效）**：任何仪表改动（包装定时器、改沙箱属性、挂栈陷阱等）**只许在隔离副本上做**＋**拍完立即恢复原状**＋**回传单逐项披露**（改了什么、为什么、何时恢复）。Playwright 追帧能裸跑取证的，一律不许再动仪表。
7. **内置 browser-use 降为备选**，两坑写明：①面板隐藏时截图/量测拿到的是隐藏态，先确认目标页签在前台；②`evaluate_script` 穿不透 opaque-origin 沙箱 iframe，做 DOM 断言被迫加 `allow-same-origin`——那属于仪表改动，须按第 6 条披露。能 Playwright 就不必踩这两坑。
8. **性能类改动**：`render-ms` 只算同步渲染段，**不许冒充全卷耗时**；A4 视口级虚排必须**逐页滚过再量**，否则得到假阴性（先例：军令 #18 前 3.58s→245ms）。
9. **布局量测坑**（逐条踩过）：
   - 量 50/50 分栏要扣掉 grid gap，别拿容器宽度对半当结论
   - `ResizeObserver` 重绘会把切图台冲走；canvas 的 border 会让坐标偏移
   - 网格行高不锁 → 依赖滚动的逻辑全是死代码
   - `.pg-q>` 行距别挂错元素、`.pg-ansbox` 别带外边距
10. **沙箱渲染坑**：插件 CSP 会拦 `blob:`/`data:` 的 img，缩略图要画到 canvas 再取 dataURL；宿主壳资源必须 `no-store`（F5 丢功能往往是缓存而不是时序，光加 no-cache 不够）。

## 自检

- [ ] 有截图 + 像素行段结论，且能对应到具体改动点
- [ ] Playwright 工具路径走过（键盘也试一遍），边界与错误态有覆盖；真人抽检做没做如实写
- [ ] 仪表改动（若有）只在隔离副本、拍完已恢复、回传单已披露
- [ ] 数字口径正确（渲染分段、扣 gap、逐页滚过）
- [ ] 证据里写清视口尺寸与页面 URL/端口，未验证部分显式标注
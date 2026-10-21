# 九章算子 · Tauri 套壳技术评估

> 状态：**调研结论，未落地**。本文不改任何主代码，不进主干依赖。
> 评估日期 2026-10-22 ｜ 评估对象：用 Tauri v2 把当前 Web 端打包成桌面程序。
> 结论先行：**与「Node 构建生态」的冲突可规避；与「禁止引入第二语言」的冲突不可规避，属硬冲突，须主公明令豁免方可落地。当前不建议采用。**

---

## 1. Tauri 是什么（事实基线）

- Tauri v2 用**系统自带 WebView** 渲染前端（Windows 上为 Edge WebView2），**不内置 Chromium**，因此壳本身安装包很小（社区实测约 3–8 MB）。
- Windows 上的**开发**前置条件：Microsoft C++ Build Tools（MSVC）+ Microsoft Edge WebView2，二者缺一不可。
- WebView2 在 **Windows 11 预装**；更旧的 Windows 上，Tauri 生成的安装程序会在**安装时联网下载**该运行时。
- Tauri CLI 本身是 Rust 写的，既可走 npm（`@tauri-apps/cli`），也可**纯 cargo 安装**（`cargo install tauri-cli`）。即 Node 并非必需。
- 壳的「后端」与配置用 **Rust**（`src-tauri/`、`tauri.conf.json`、`Cargo.toml`）。

## 2. 与本项目的契合度

当前架构是 **Python FastAPI 后端 + 原生 HTML/CSS/JS 前端**，前端无打包器。Tauri 只能包裹静态资源，**不能承载 Python 后端**。因此只有两种接法：

| 方案 | 内容 | 判定 |
|------|------|------|
| A. 薄壳 + sidecar | WebView 指向 `http://127.0.0.1:8000`，Tauri 以 sidecar 方式拉起 Python 服务（系统 python+venv，或 PyInstaller 冻结产物） | 唯一现实路径 |
| B. 后端移植 Rust | 把 FastAPI/SQLite/AI 通道全部重写为 Rust | **直接否决**：违反干净房间与 Python 技术栈铁律，工作量等同重写 |

### 方案 A 的收益

1. 原生窗口、任务栏图标、托盘、开机自启——对不懂技术的老师，比「黑色窗口 + 浏览器标签」更不容易误关。
2. 单一安装程序，可整体离线分发。
3. 壳体积小，内存占用低于 Electron 一类自带浏览器的方案。

### 方案 A 的代价

1. **双进程生命周期**：壳要负责拉起/等待/回收 Python sidecar，要处理端口被占、sidecar 崩溃、退出残留——这套逻辑本身就是新的复杂度与新的故障面。
2. **安装包体积优势被吃掉**：一旦把 Python 运行时冻结进 sidecar，安装包从几 MB 涨到几十 MB，Tauri 最大的卖点随之消失。
3. **安装期联网**：Win10 机器首装需下载 WebView2，与「可完全离线」的承诺在*安装时刻*产生张力（安装完成后仍可离线）。
4. **WebView ≠ 浏览器**：打印、下载、开发者工具、iframe 沙箱语义都要在 WebView2 上重新验证；Win10 上 WebView2 版本可能滞后，插件沙箱（`postMessage`、净化、兜底渲染）需整轮回归。
5. **第二条构建/打包/CI 流水线**与一门新的维护语言，长期成本远高于一次性收益。

## 3. 与铁律的冲突判定（核心）

| 规范条款 | 原文要点 | Tauri 是否冲突 | 说明 |
|----------|----------|----------------|------|
| AGENTS §4 前端 | 无打包器、**无 Node 运行时依赖** | **可规避** | 前端仍用现有 `static/` 原样作 `frontendDist`，不引打包器；CLI 走 `cargo install tauri-cli` 而非 npm。但若按社区默认套路（npm CLI + Vite 模板）则会**直接违反**，故须在仓内明令禁止该套路 |
| AGENTS §4 离线 | 资源本地化、可完全离线运行 | **部分张力** | 运行期离线可满足；Win10 首装需联网取 WebView2 |
| STACK §0 总则 | 不引非必要运行时依赖；新增须报主公批准 | **需批准** | 壳 + WebView2 属新增运行时依赖 |
| STACK §8.2 | 禁止前端框架（React/Vue 等）入主干 | 不冲突 | Tauri 非前端框架 |
| STACK §8.3 | **禁止在主干引入 Go 等第二语言，除非主公明令** | **硬冲突，不可规避** | Tauri 壳必须是 Rust。只要套壳进主干，就必然引入第二语言 |
| AGENTS 铁律二 | 底座要薄、插件沙箱隔离 | 需回归验证 | WebView2 为 Chromium 系，iframe 沙箱与 postMessage 语义兼容，但插件安全边界须在新渲染器上重测 |

**判定**：军令所问的「禁止引入 Node 构建生态」，在 AGENTS.md 中的准确表述是「无打包器、无 Node 运行时依赖」。这一条**技术上可规避**（cargo-only + 无打包器）。真正的拦路虎是 STACK §8.3 的第二语言红线——**Rust 进主干即违规，无技术手段可绕**，只能靠主公明令豁免。

## 4. 建议

1. **现阶段不采用 Tauri。** 现有 `start.bat` + 浏览器路径已满足「双击即用、可离线、零额外依赖」，且与全部铁律自洽；套壳带来的体验增益不足以抵偿双进程与第二语言的长期成本。
2. 若将来确要桌面壳，**优先放在主干之外**：独立仓库或独立分支持有 `src-tauri/`，主干保持零 Rust、零 Node；主干只继续产出 `static/` 与 Python 服务，壳仓库消费其产物。如此 STACK §8.3 的「主干」口径不被破坏。
3. 若主公决意进主干，则须：明令豁免 §8.3；在仓内立规「CLI 只准 cargo 安装、前端禁止打包器」；补 WebView2 缺失机的安装期降级文案；对插件沙箱做 WebView2 全量回归。
4. 无论走哪条路，**先补多工作区与导入/组卷插件**（见快照 §6.1/§6.2）比套壳更贴近老师真实痛点。

## 5. 证据来源

- [Tauri v2 官方 · Prerequisites（Windows 需 MSVC + WebView2）](https://v2.tauri.app/zh-cn/start/prerequisites/)
- [Tauri v2 官方 · Webview Versions（Win11 预装，旧版安装期下载）](https://v2.tauri.app/reference/webview-versions/)
- [Tauri v2 官方 · Command Line Interface（CLI 可经 cargo 安装）](https://v2.tauri.app/reference/cli/)
- [Tauri 官方 FAQ · Should I use Node or Cargo?（CLI 为 Rust 编写，可走 crates.io）](https://tauri.app/zh-cn/v1/guides/faq/)
- [Tauri v2 官方 · Windows Installer（可配置 WebView2 运行时路径）](https://v2.tauri.app/zh-cn/distribute/windows-installer/)

---

九章算术，算子至简。壳是外衣，契约才是骨。

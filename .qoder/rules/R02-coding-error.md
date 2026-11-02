---
trigger: model_decision
description: 九章算子编码风格、错误处理与日志约束。写后端路由/core、写宿主壳与插件 JS、新增错误码或异常处理、改动日志与鉴权时必须遵守
---

# R02 编码与错误处理约束（九章算子）

> 覆盖域：编码与错误处理（域2）。结论来自 2026-11-02 实探，证据格式 `路径:行号`。

## 1. 返回体：统一结构在宿主总线层，不在 HTTP 层（L0）

1. **[L1] 后端路由直接返回裸 dict / pydantic 结构**，失败靠 `HTTPException`——没有统一 Response 包装（`app/api/bank.py:296-320`、`app/api/settings.py:125`）。**不要自造 `Result`/`ApiResponse` 外壳**，那会让宿主 relay 与插件侧解析双双对不上。
2. **[L0] 真正的统一返回体是 postMessage 回执**：`{protocol, id, kind:"response", ok, result | error{code,message,retryable}}`，定义在 `static/js/stage_command.js:443-468`，插件侧按同结构解析（`static/js/stage_inbound.js:69-78`）。新增任何请求族都必须复用这个信封。
3. **[L0] 请求 id 硬约束**：`^[A-Za-z0-9_-]{1,80}$`（`static/js/stage.js:46`），不合法直接回 `ok:false` 的 `BAD_REQUEST_ID` 并在底栏记 `plugin.error`（`static/js/stage_inbound.js:53-63`）。**带点号的 id 必被拒发**，别指望后端兜。

## 2. 错误码（L1）

| 域 | 命名 | 现有值 | 位置 |
|---|---|---|---|
| 宿主 relay | 大写蛇形 | `BAD_REQUEST_ID`、`UNSUPPORTED_METHOD`、`PERMISSION_DENIED`、`RATE_LIMITED`、`NO_PLUGIN`、兜底 `HOST_ERROR`、透传 `HOST_<httpStatus>` | `static/js/stage_inbound.js:58`、`static/js/stage.js:334,341,348,355,402`、`stage_command.js:450` |
| 插件安装 | 小写 | `too_large`、`bad_url`、`download_failed`、`exists`（挂在 `PluginInstallError`） | `app/core/plugin_install.py:135`、`app/core/plugin_download.py:44` |
| 题目域 | 异常类 | `QuestionError` → `QuestionValidationError` | `app/core/questions.py:64-79` |

- **[L0] 后端没有 ErrorCode 常量表**（全仓 grep `ERR_`/`ErrorCode` 命中 0）。新增错误码就按上述两套既有惯例分域命名，不要新开第三套。
- **[L1] 新码必须同时决定 `retryable`**，插件侧据此决定是否提示重试；不可重试的写入错误一律 `ok:false` 且 `retryable:false`。

## 3. 异常处理与鉴权（L0）

1. **[L1] 没有全局 exception handler**（全仓 grep `exception_handler` 命中 0，`create_app` 只注册路由，`app/main.py:147-169`）。惯例是逐域 try/except，把域异常翻译成 `HTTPException(status_code, detail)`（`app/api/bank.py:310-320`）。新增域异常要在路由入口显式接住，否则会变成 500 裸栈。
2. **[L0] 所有写接口必须挂 `Depends(require_write_token)`**（`app/core/security.py:69-89`）：一次性令牌 + 用后即焚 + 轮换，落 `data/.local_token`（`security.py:19-27,53-66`，`secrets.compare_digest` 比对）。写操作不得只靠前端隐藏按钮保护（`docs/AGENTS.md:60`）。
3. **[L0] 题目写入整批回滚**：Schema 校验失败 → 整批 rollback + 逐题报错 + HTTP 422（`app/core/bank_write.py:427-463,580`、`app/api/bank.py:379-389`）。不许改成"坏题跳过、好题入库"。
4. **[L1] 禁止吞异常**（`except Exception: pass`）；禁止把展示态内容回写题目结构（`docs/AGENTS.md:39`）。

## 4. 日志（L1）

1. **[L1] 只复用 uvicorn 的 logger**：`logging.getLogger("uvicorn.error")`（`app/main.py:108-110`，注释已说明原因）。**不自建 logger 体系、不加 FileHandler**（全仓 grep `FileHandler` 命中 0），日志只进 `start.bat` 控制台窗口，无分级配置。
2. **[L0] 密钥永不入日志、永不入库、永不进插件上下文**（`docs/AGENTS.md:61`）。日志里出现 token 值/AI key 即事故级。
3. **[L1] 前端"日志"是底栏消息档**：`dock(msg, "plugin.error")` 白名单档位（`static/js/stage_inbound.js:61-98`），新增档位要同时改样式与白名单，别 `console.log` 满天飞。

## 5. 前端安全与兜底（L0）

1. **[L0] 一切不可信输入进 DOM 前必须白名单净化**（题目文本/答案/标签/AI 输出/插件返回值/图片属性）。插件返回的 HTML 禁 `<script>`、内联事件、`javascript:`、远程样式与 `@import`（`docs/AGENTS.md:56-58`）。
2. **[L0] 图片只允许底座托管路径或 `asset://`**；禁远程 URL、`data:`、`file:`（`docs/AGENTS.md:59`）。注意插件沙箱 CSP 会拦 `blob:`/`data:` 的 img，缩略图要画到 canvas（先例见军令#27 记录）。
3. **[L1] 沙箱与超时**：插件必须在 iframe 沙箱内（`docs/PLUGIN_SPEC.md:460`）；激活超时 30s 后保留页签不再等待（`static/js/stage_frame.js:124-127`）；**画布允许彻底空着，不许加任何占位/兜底页文案**（`stage_frame.js:333`，2026-10-31 主公裁决）。
4. **[L0] 可访问性红线**（`docs/AGENTS.md:64-70`）：键盘可达 + 焦点可见、弹窗焦点陷阱 + `Esc` + 关闭后还原焦点、触控目标 ≥44px、375px 不横向溢出、状态不只靠颜色、加载按钮同步 `disabled`/`aria-busy`、尊重 `prefers-reduced-motion`。
5. **[L0] 禁止正则后行断言** `(?<!...)`/`(?<=...)`（旧浏览器直接语法失败）。

## 6. 风格约定（L1，从存量代码归纳，非臆造）

| 侧 | 约定 | 证据 |
|---|---|---|
| Python | 全 snake_case、常量大写蛇形（`MAX_PAGE_SIZE`）、`from __future__ import annotations` + 类型注解、异常继承树 | `app/core/questions.py:8,27,64-79` |
| JS | ES5 风格 `var` + IIFE + `"use strict"`、双引号、带分号、模块经 `create(deps)` 依赖注入、不碰全局 | `static/js/stage_inbound.js:7-27` |
| 文本 | Markdown + LaTeX，行内 `$...$`、独立 `$$...$$`，**不得另造公式方言** | `docs/AGENTS.md:35` |

## 7. 自检清单

- [ ] 新请求族复用宿主信封结构，请求 id 合规且不含点号
- [ ] 新错误码归入既有两套命名域之一，且带 `retryable` 判定
- [ ] 写接口有 `require_write_token`；域异常在路由层被显式接住
- [ ] 无新增 logger/FileHandler；日志与 diff 里没有密钥
- [ ] 前端改动键盘可达、净化到位、无后行断言、无占位兜底页
- [ ] `.venv/Scripts/python.exe tools/audit_code.py` 无 ERROR（实测基线：ERROR 0 / WARN 36 / INFO 4）

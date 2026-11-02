---
name: add-host-api
description: 在九章算子新增一条 Host API / 请求族 / 命令面端点的标准动线：core 写入函数 → api 路由鉴权 → 宿主 relay 白名单 → 错误码 → 单测与探针。当插件需要新的读写能力或要扩 bank.*/pending.* 命令族时使用。
---

# add-host-api：新增一条底座代持接口

> 原子范围：只打通一条链路，不做数据迁移、不改插件业务。
> 前提：R02（返回体与错误码）、R03（动线与鉴权）、`docs/PLUGIN_SPEC.md` §2.6 与 §2.14。

## 动线（必须逐跳落点，缺一跳即半成品）

```
插件 postMessage → stage_inbound.js(id 校验) → stage.js(白名单/限流/权限)
→ stage_relay_*.js(HTTP) → app/api/*.py(鉴权) → app/core/*.py(Schema 校验) → SQLite
```

1. **core 层**：在 `app/core/` 对应域写函数；涉及题目必须经 `app/core/questions.py:86-101` 的唯一校验器（`Draft202012Validator`），失败抛域异常（`QuestionError` 子类，`questions.py:64-79`）。
2. **api 层**：`app/api/<域>.py` 加路由，**写接口必须 `Depends(require_write_token)`**（`app/core/security.py:69-89`）；按现有惯例把域异常 try/except 翻成 `HTTPException`（**没有全局 handler**，`app/main.py:147-169`）。返回裸 dict，不要造统一外壳（R02 §1）。
3. **挂载**：若是新路由模块，在 `app/main.py:166-167` 处 include（先例：pending 域）。
4. **宿主 relay**：`static/js/stage.js:330-356` 白名单登记请求族 + `static/js/stage_relay_<域>.js` 发起 `fetchJson`（先例 `stage_relay_bank.js:89-113`）。
5. **错误码**：宿主侧新增码用大写蛇形并放进现有码集（`stage.js:334-402`），必须决定 `retryable`；后端域码沿用小写（`plugin_install.py:135` 式）。
6. **命令面**（对外暴露给 AI/插件的可调用命令）：在插件 `plugin.json` 的 `contributes.commands` 声明，命名空间闸与先到先得规则见 `app/core/commands.py:1-27`；命令必须 64KB/串行/pending 上限约束齐备（军令 #19/#20 的能力字典口径）。
7. **测试**：`tests/test_<域>_api.py`，断言按 `Trigger→Action→Effect`；起 uvicorn 的用例设 `JZO_RESTART_DISABLED=1`；**先读 HTML/初始态再写断言**（Toggle 默认 active 之类会造出假失败）。
8. **探针**：需要真机证据时扩 `tools/<域>_probe.py` 的 `check(name, passed, detail)`，禁止写死端口与令牌（走 `tools/probe_paths.py`）。

## 自检

- [ ] 七跳都有落点且能给出 `路径:行号`
- [ ] 请求 id 合规 `^[A-Za-z0-9_-]{1,80}$` 且不含点号（含点必被 `BAD_REQUEST_ID` 拒发）
- [ ] 写接口有鉴权；不可信输入进 DOM 前已净化
- [ ] `bash scripts/check-quick-gate.sh` 绿；受影响测试模块 `.venv/Scripts/python.exe -m unittest tests.<模块>` 实跑贴原始输出

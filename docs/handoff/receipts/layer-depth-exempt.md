# 回传单 · 证据目录豁免目录≤3 层约束（#LAYER-DEPTH-EXEMPT-01）

【回执编号】 #LAYER-DEPTH-EXEMPT-01
【回执时间】 2026-11-20
【执行结果】 **完成（纸面落条款，零脚本改动）**。docs/AGENTS.md §4 深度封顶 ④ 之后追加豁免条款 3 行；经 grep 实证全仓无目录深度校验脚本，属「纸面约束、无脚本门禁」，故未改任何脚本/测试。快门禁 `bash scripts/check-quick-gate.sh` PASS（6 项全过，rc=0）；两笔 commit 不 push。

基线：operator HEAD `49756b3`（ahead 110）；工作树仅 `?? tools/onnx_probe.py`（未 stage、未提交，现仍在）。
本卡两笔：`af5980a`（AGENTS.md 条款）／收口笔（本回单＋biz）；ahead 按笔数记：110＋2＝112（免随 commit 漂移）。

## 拍板原文（逐字）

「主公 2026-11-20 拍板：目录≤3 层约束对 `.system_generated/` 探针与证据产物**豁免**——证据目录按产物自身结构组织，天然会更深；代码与文档仍守 ≤3 层。」

## 改点（逐个）

### docs/AGENTS.md §4（第 74–76 行新增 3 行，原 ④ 四句一字未动）

在深度封顶 ④（`docs/AGENTS.md:71-73`）之后、`- 禁止在根目录堆放业务模块。`（:77）之前插入：

```
    **证据目录豁免（2026-11-20 主公裁）**：`.system_generated/` 下的探针与证据产物不受层数限制
    （按产物自身结构组织即可）；`app/`、`static/`、`plugins/`、`docs/`、`tests/`、`scripts/`、`tools/`
    等代码与文档目录仍守 ≤3 层。
```

- 位置：贴合 §4「深度封顶」原有语气（沿用「（YYYY-MM-DD 主公裁）」署名格式）。
- 未重排原有 ①②③④ 四句；未动铁律一/二及其余章节。根 `agents.md` 未触碰。

## 是否有脚本门禁：**无（纸面约束）**

按卡令 `grep -rn "层\|depth\|layer" scripts/ tools/ tests/`，逐一核查全部命中：

- `tools/audit_code.py:172`：`path.relative_to(root).parts` 用作规则作用域判断（`test-token-leak` 只看 `app/static/plugins/schemas`），**不判深度**。
- `tools/clean_for_release.py:159`：`len(parts) > 2` 是发版打包路径判据，非目录分层规则。
- 其余命中均为业务语义（考向层别、UI 浮层、图片位深等），与 §4 深度封顶无关。
- `scripts/check-quick-gate.sh` 六项（命名规约／插件三查与依赖方向／插件包结构／索引全等／静态红线／版本单源）**均不含目录深度检查**。

结论：深度封顶≤3 层自始就是纸面铁律，无脚本硬校验；故仅落 AGENTS.md 条款，**不改任何脚本、不补单测**（卡令分支：无脚本即回单写明，不动脚本）。

## 【改动清单】

- commit `af5980a`：`docs/AGENTS.md`（+3 行，§4 深度封顶后追加豁免条款）。
- 收口笔：`docs/handoff/receipts/layer-depth-exempt.md`（本回单）＋
  `.qoder/records/biz/2026-11/20261120_layer-depth-exempt.md`（新建）。
- **脚本/测试/生产代码：零改。**

### 禁改区自查

- LICENSE：否。AGENTS.md 铁律一/二：否（未改）。根 `agents.md`：否（未触碰）。
- `app/core/question_contract.py`：否。用户 `data/`：否。`tools/onnx_probe.py`：原地未 stage（仍 untracked）。
- 65496 服务：零接触，未重启/未杀。未执行 `taskkill /F /IM python.exe`。
- 禁 JSON 落盘：否（全 MD）。records：只新建。stage 点名两笔各点名文件，未 `-A`；未 amend；未 push。

## 【包结构自检】

不适用——不涉插件。

## 【三查结果】

不适用——插件侧零改。

## 【测试与探针】

- 快门禁：`bash scripts/check-quick-gate.sh` → **PASS（6 项全过）**，`GATE_RC=0`（当次实测输出）。
  静态红线审计 ERROR 0 · WARN 35 · INFO 3（WARN 均为既存，逐条落点非本卡文件）；体积预警 23 份均既存文件。
- 文档改动无沾边测试模块；全量回归免（AGENTS §7 2026-11-18 拍板：定向＋门禁为主，本卡零代码改动）。
- 真机探针/Playwright：免（纯文档条款）。

## 【未决问题与偏离】

1. **边界声明**：豁免只针对 `.system_generated/` 下探针与证据产物的目录层数；`app/`、`static/`、`plugins/`、`docs/`、`tests/`、`scripts/`、`tools/` 及插件 `src/<id>/`、`.qoder/` 等代码与文档目录的 ≤3 层约束**原样有效**，不因本条松动。
2. 本卡为纯纸面落条款，无脚本门禁可挂；若日后新增目录深度校验脚本，须按本条同步给 `.system_generated` 加豁免判据（本卡不预设脚本）。
3. push：奉令 hold，未 push；ahead 110→112。

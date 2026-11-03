# 交接protocol：军令 → 施工 → 回传 → 复审

本目录是「人不在传输层」的落地物。主公只做**裁决**，不抄正文。

## 角色

| 席位 | 谁 | 只干什么 |
| --- | --- | --- |
| 主公 | 人 | 拍板、裁决、授权提交；不搬运正文 |
| 军师 | 网页 DeepSeek 或本地网关 | 出军令卡、复审回传单、给下一道军令 |
| 施工 | 本地 Agent | 执行军令、采证据、写回传单、跑单测与探针 |
| 监工 | `tools/handoff.py` | 机械校验，模型说了不算 |

## 文件

```
docs/handoff/
  state.json         当前轮次指针（order_id / status / updated_at）
  orders/            军令卡（下行），手写或粘贴原文
  receipts/          机械证据回传单（上行），由脚本生成
  verdicts/          复审结论与下一道军令（军师写，施工照办）
```

## 一轮怎么走

```bat
:: 1. 军令落地（把网页那段原文直接贴进文件，或本机生成模板）
.venv\Scripts\python.exe tools\handoff.py order --id 31 --title "查重拦截机制"

:: 2. 施工（本地 Agent 按军令改代码）

:: 3. 回传单：证据由脚本采集，不由模型复述
.venv\Scripts\python.exe tools\handoff.py receipt --order 31 ^
    --modules tests.test_pending_dedupe,tests.test_pending_api ^
    --probe .system_generated/editor_probe/s31/probe.json

:: 4. 机械校验：缺项、假绿、数字对不上，一律非零退出
.venv\Scripts\python.exe tools\handoff.py verify docs\handoff\receipts\31.md --rerun

:: 5. 生成一整段可粘贴的复审包（军令 + 回传 + diff 摘要）
.venv\Scripts\python.exe tools\handoff.py pack docs\handoff\receipts\31.md
```

第 4 步的 `--rerun` 会**当场重跑**点名过的单测模块，把「回传单里写的数字」与「这次跑出来的数字」逐条比对；
对不上就是非零退出。这是防「模型自报全绿」的唯一硬办法。

## 四条不妥协

1. **回传单里的数字只能来自脚本采集**。人写的「已完成」「全绿」不算证据，`verify` 会直接判废。
2. **`--rerun` 不一致即判废**，不看理由。要改数字就重跑。
3. **三查由 `verify` 当场重算**，回传单里写的只是「声称值」；对不上就判废。
4. **`data/`、`.env`、`.local_token` 永不进回传单**：`receipt` 与 `pack` 都会把密钥形态的字符串抹成 `***`。

## 缺证据必须显式豁免

没有单测 / 没有探针，**默认判废**。确实不涉及（纯文档轮次）时，由人当场在命令上敲出来：

```bat
python tools\handoff.py verify docs\handoff\receipts\30.md --allow-no-tests --allow-no-probe
```

命令行的豁免是留痕的：复审席一眼看得见「这一轮没证据，而且是人主动放行的」。

## 席位与模型：防「近亲审查」

三席共用一个模型，等于自己给自己判卷——共同盲区永远挑不出来。所以席位与模型必须解耦：

```bat
python tools\handoff.py seats --init      :: 生成 docs/handoff/seats.json
python tools\handoff.py seats --check     :: 逐席探连通性，并点出同族席位
```

`seats.json` 里每个席位独立配 `base_url` / `model` / `api_key_env`，留空的字段回落到 `.env`
的 `JZO_AI_BASE_URL` / `JZO_AI_MODEL`。审查席请填**另一家**的模型：

| 席位 | 职责 | 用谁 |
| --- | --- | --- |
| 主脑 | 出军令、定判据 | 最强的那一个（网页端或旗舰模型） |
| 审查 | 挑证据缺口与契约违背 | **必须异族**，否则盲区重合 |
| 干活 | 改代码、跑测试、采证据 | 与主脑同族可接受 |

第三方模型只要兼容 OpenAI 协议就能接入：把 `base_url` 填进去，密钥写进 `.env` 的
`SEAT_REVIEW_API_KEY`（或你在 `api_key_env` 里指定的名字），再跑 `seats --check`。


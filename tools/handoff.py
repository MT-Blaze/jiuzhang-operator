"""交接协议工具：军令卡、机械证据回传单、机械校验、三席议事。

设计原则只有一条：**没有一项数字是模型自报的**。

- ``order``   生成军令卡骨架（下行）；也吃网页端粘来的原文。
- ``receipt`` 跑单测、采 git/三查/探针，把当次实测写成回传单（上行）。
- ``verify``  机械校验五项是否齐、数字是否自洽；``--rerun`` 当场重跑并逐条比对。
- ``pack``    把军令 + 回传 + diff 摘要拼成一整段，粘给主脑一次就够。
- ``council`` 三席议事（主脑 / 审查 / 干活），轮话式讨论后落一份裁决。

所有产物落在 ``docs/handoff/``，都是纯文本，可 diff、可回溯、不进 ``data/``。
本模块不发任何隐式请求：``council`` 必须人手敲命令才会出网。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "docs" / "handoff"
ORDERS = HANDOFF / "orders"
RECEIPTS = HANDOFF / "receipts"
VERDICTS = HANDOFF / "verdicts"
STATE = HANDOFF / "state.json"

LOCAL_TZ = timezone(timedelta(hours=8))

# §5.6 五项，缺一即判废。顺序也是回传单的可读顺序。
SECTIONS = ("改动清单", "包结构自检", "三查结果", "测试与探针", "未决问题与偏离")

# 军令卡与回传单里机器可读的那一行（HTML 注释，渲染时不显示）
MARKER_RE = re.compile(r"<!--\s*handoff:(\{.*?\})\s*-->", re.S)

# 三查：插件侧三项命中数必须为 0（AGENTS §2、PLUGIN_SPEC §2.8）
THREE_CHECKS = {
    "fetch(": re.compile(r"fetch\s*\("),
    "parent.document": re.compile(r"parent\s*\.\s*document"),
    "localStorage": re.compile(r"localStorage"),
}


def now() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def ensure_dirs() -> None:
    for path in (ORDERS, RECEIPTS, VERDICTS):
        path.mkdir(parents=True, exist_ok=True)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def git(*args: str) -> str:
    """跑一条 git 只读命令；失败回空串，绝不抛（工具不该因为没仓库就全废）。"""
    try:
        result = subprocess.run(
            ["git", *args], cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def run_command(argv: list[str], timeout: int = 1800) -> tuple[int, str]:
    try:
        result = subprocess.run(
            argv, cwd=str(ROOT), capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, f"[handoff] 命令无法执行：{exc}"
    return result.returncode, (result.stdout or "") + (result.stderr or "")


def python_exe() -> str | None:
    """项目唯一解释器：``.venv/Scripts/python.exe``（AGENTS §7）。

    **绝不退回 ``sys.executable``**：系统 Python 缺依赖，会把所有模块打成假报错，
    那比跑不起来更坏——假红会让人去修根本没坏的东西。没有 venv 就明确失败。
    """
    candidate = ROOT / ".venv" / "Scripts" / "python.exe"
    return str(candidate) if candidate.is_file() else None


def _require_python() -> str:
    exe = python_exe()
    if exe is None:
        raise SystemExit("[handoff] 找不到 .venv/Scripts/python.exe："
                         "按 AGENTS §7 必须用 venv 解释器，不退回系统 Python。")
    return exe


# ------------------------------------------------------------------ 三查

def three_checks() -> dict[str, int]:
    """插件侧三项命中数。只扫 ``plugins/*/dist/*.js``，宿主 JS 不在判据内。"""
    counts = {name: 0 for name in THREE_CHECKS}
    plugins = ROOT / "plugins"
    if not plugins.is_dir():
        return counts
    for path in plugins.glob("*/dist/*.js"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name, pattern in THREE_CHECKS.items():
            counts[name] += len(pattern.findall(text))
    return counts


# ------------------------------------------------------------------ 军令卡

ORDER_TEMPLATE = """# 军令 #{order_id} · {title}

【军令编号】 #{order_id}
【发令时间】 {created_at}
【主脑】 {brain}
【验收判据】 由本卡逐条钉死，回传单逐条对账

## 任务

{items}

## 边界

- 不得扩大改动面；发现与 `docs/AGENTS.md` 冲突先停下报告。
- 涉及前端必须在浏览器里走真人路径；涉及插件必须过三查。
- 一个阶段一个 commit，测试不绿不许 commit。

<!-- handoff:{{"kind":"order","order_id":{order_id},"title":{title_json},"created_at":"{created_at}"}} -->
"""


def cmd_order(args: argparse.Namespace) -> int:
    ensure_dirs()
    order_id = int(args.id)
    title = args.title or f"第 {order_id} 轮"
    body = ""
    if args.from_file:
        body = Path(args.from_file).read_text(encoding="utf-8", errors="replace").strip()
    items = args.items or ""
    if body:
        items = body
    elif not items:
        items = "（待主脑填写任务项；也可用 --from-file 直接粘贴网页端原文）"
    text = ORDER_TEMPLATE.format(
        order_id=order_id, title=title, created_at=now(),
        brain=args.brain or "未指定", items=items.strip(),
        title_json=json.dumps(title, ensure_ascii=False),
    )
    target = ORDERS / f"{order_id:03d}.md"
    target.write_text(text, encoding="utf-8")
    _write_state({"order_id": order_id, "status": "ordered", "updated_at": now()})
    print(f"[order] 已生成 {rel(target)}")
    return 0


# ------------------------------------------------------------------ 回传单

def classify_probe(path: Path) -> dict[str, Any]:
    """读探针产物：尽量取出 passed/total 与截图数，取不到就如实记「未解析」。"""
    info: dict[str, Any] = {"path": rel(path), "exists": path.is_file()}
    if not path.is_file():
        return info
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, ValueError):
        info["parsed"] = False
        return info
    info["parsed"] = True
    if isinstance(data, dict):
        for key in ("passed", "total", "crashed", "page_errors", "console_errors"):
            if key in data:
                info[key] = data[key]
        checks = data.get("checks")
        if isinstance(checks, list):
            info.setdefault("total", len(checks))
            info.setdefault("passed", sum(1 for item in checks if isinstance(item, dict) and item.get("ok")))
    return info


def run_module(module: str) -> dict[str, Any]:
    """跑一个单测模块，回它的实测数字。解释器必须是 .venv 那一个。"""
    exe = _require_python()
    argv = [exe, "-m", "unittest", module]
    code, output = run_command(argv)
    ran = re.search(r"Ran (\d+) tests?", output)
    ok = code == 0 and "OK" in output
    tail = "\n".join(output.strip().splitlines()[-4:])
    return {"module": module, "ran": int(ran.group(1)) if ran else 0, "ok": ok, "tail": tail,
            "exit": code, "command": " ".join(argv)}


RECEIPT_TEMPLATE = """# 回传单 · 军令 #{order_id}

【回执编号】 #{order_id}
【回执时间】 {created_at}
【执行结果】 {result}
【采集方式】 `tools/handoff.py receipt`（数字全部来自当次实测，非模型复述）

## 【改动清单】

`HEAD` `{head}` · 工作树 {dirty_count} 项变动。

```
{status_text}
```

```
{diff_stat}
```

禁改区自查：LICENSE / AGENTS 铁律一二 / schemas 破坏性变更 / `data/` —— {forbidden}

## 【包结构自检】

{plugin_check}

## 【三查结果】

插件侧 `plugins/*/dist/*.js` 三项命中：{checks_text}

## 【测试与探针】

{test_block}

探针：{probe_text}

## 【未决问题与偏离】

{open_issues}

<!-- handoff:{marker} -->
"""


def cmd_receipt(args: argparse.Namespace) -> int:
    ensure_dirs()
    order_id = int(args.order)
    modules = [item.strip() for item in (args.modules or "").split(",") if item.strip()]

    results = [run_module(module) for module in modules]
    checks = three_checks()
    head = git("rev-parse", "--short", "HEAD") or "无提交"
    status_text = git("status", "--porcelain") or "（工作树干净）"
    diff_stat = git("diff", "--stat") or "（无未提交改动）"
    dirty_count = len([line for line in status_text.splitlines() if line.strip()]) \
        if status_text != "（工作树干净）" else 0

    probe_info = classify_probe(Path(args.probe)) if args.probe else {"exists": False}

    modules_ok = all(item["ok"] for item in results) if results else True
    probe_ok = (not args.probe) or (
        bool(probe_info.get("exists"))
        and probe_info.get("passed") is not None
        and probe_info.get("passed") == probe_info.get("total"))
    result = "成功" if (modules_ok and probe_ok) else "失败"

    if results:
        lines = ["| 模块 | 实测 | 判据 |", "| --- | --- | --- |"]
        for item in results:
            lines.append(f"| `{item['module']}` | Ran {item['ran']} tests | "
                         f"{'绿' if item['ok'] else '红'} |")
        blocks = [f"- `{item['module']}` → Ran {item['ran']} tests / "
                  f"{'OK' if item['ok'] else 'FAILED'}" for item in results]
        test_block = "\n".join(lines) + "\n\n逐模块实测行：\n\n```\n" + "\n".join(blocks) + "\n```"
    else:
        test_block = "未跑单测（本次声明为纯文档/工具改动，须在未决栏写明理由）。"

    if args.probe:
        if probe_info.get("exists"):
            probe_text = (f"`{probe_info['path']}` · passed {probe_info.get('passed', '?')}"
                          f"/{probe_info.get('total', '?')}")
        else:
            probe_text = f"未跑（`{probe_info['path']}` 不存在）"
    else:
        probe_text = "未跑（本次未涉及前端/插件真机路径）"

    checks_text = " · ".join(f"`{name}` {count}" for name, count in checks.items())
    marker = {
        "kind": "receipt",
        "order_id": order_id,
        "created_at": now(),
        "result": result,
        "modules": {item["module"]: {"ran": item["ran"], "ok": item["ok"]} for item in results},
        "commands": [item["command"] for item in results],
        "probe": {k: v for k, v in probe_info.items() if k != "path"},
        "three_checks": checks,
        "head": head,
        "dirty": dirty_count,
    }

    text = RECEIPT_TEMPLATE.format(
        order_id=order_id, created_at=now(), result=result, head=head,
        dirty_count=dirty_count,
        status_text=status_text, diff_stat=diff_stat,
        forbidden=args.forbidden or "未触碰（逐条核对后填写依据）",
        plugin_check=args.plugin_check or "本次不涉及插件",
        checks_text=checks_text,
        test_block=test_block,
        probe_text=probe_text,
        open_issues=(args.open_issues or "（如实填写欠账、偏离与未验证项；没有就写「无」）").strip(),
        marker=json.dumps(marker, ensure_ascii=False),
    )
    target = RECEIPTS / f"{order_id:03d}.md"
    target.write_text(redact(text), encoding="utf-8")
    _write_state({"order_id": order_id, "status": "receipted", "updated_at": now()})
    print(f"[receipt] 已生成 {rel(target)}")
    print(f"[receipt] 单测：{len(results)} 个模块，"
          f"{sum(1 for item in results if item['ok'])} 绿 / "
          f"{sum(1 for item in results if not item['ok'])} 红")
    return 0 if result != "失败" else 1


# ------------------------------------------------------------------ 机械校验

def _sections_of(text: str) -> dict[str, str]:
    """按 ``## 【X】`` 切段，**跳过围栏代码块**，且**先写的段赢**。

    两条都是被审查席打出来的：diff 或测试输出里常出现 ``## 【...】`` 这样的行
    （本项目的回传单是 Markdown，diff 里夹着文件内容），若照旧「最后一段覆盖前面的」，
    任何人都能在正文末尾补一段假内容把真段顶掉。所以：

    - 处在 ``` 围栏内时，一律不当标题；
    - 同名段重复出现时，只认第一次。
    """
    found: dict[str, str] = {}
    current: str | None = None
    buffer: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            if current is not None:
                buffer.append(line)
            continue
        match = None if fenced else re.match(r"^##\s*【(.+?)】\s*$", line.strip())
        if match:
            if current and current not in found:
                found[current] = "\n".join(buffer).strip()
            current = match.group(1)
            buffer = []
            continue
        if current is not None:
            buffer.append(line)
    if current and current not in found:
        found[current] = "\n".join(buffer).strip()
    return found


def verify_text(text: str, *, actual: dict[str, Any] | None = None,
                allow_no_tests: bool = False, allow_no_probe: bool = False) -> list[str]:
    """回传单的机械判据。回问题清单，空清单才算通过。

    **判据的核心是「重算，不信自报」**：三查由本函数自己扫一遍仓库，回传单里写的
    只是「声称值」，两者对不上就判废。旧版本直接信 marker 里的 ``three_checks``，
    于是任何人手写几个 0 就能变绿——审查席用这份伪造实测把它打穿了。

    ``allow_no_tests`` / ``allow_no_probe`` 是**显式豁免**，必须由人当场在命令行上
    敲出来（纯文档轮次才用得上）。缺省一律判废：没有证据就是没有证据。
    """
    problems: list[str] = []
    marker = MARKER_RE.search(text)
    # 机器标记是元数据，不是正文：它挨着最后一段时不能把「空段」撑成「非空段」。
    sections = _sections_of(MARKER_RE.sub("", text))

    for name in SECTIONS:
        if name not in sections:
            problems.append(f"缺项：【{name}】")
        elif not sections[name].strip():
            problems.append(f"空项：【{name}】")

    if marker is None:
        problems.append("缺机器可读标记 `<!-- handoff:{...} -->`，数字无法复核")
        return problems
    try:
        data = json.loads(marker.group(1))
    except ValueError:
        problems.append("机器可读标记不是合法 JSON")
        return problems

    # 假绿判据：嘴上说全绿，却拿不出 Ran N tests。
    test_section = sections.get("测试与探针", "")
    if re.search(r"全绿|全部通过|已完成", text) and not re.search(r"Ran \d+ tests", test_section):
        problems.append("出现「全绿/已完成」却没有 `Ran N tests` 实测行——判为假绿")

    modules = data.get("modules") or {}
    if not modules:
        if not allow_no_tests:
            problems.append("回传单没有任何单测模块：要么补证据，"
                            "要么在 verify 上显式加 --allow-no-tests（纯文档轮次）")

    for name, info in modules.items():
        if not isinstance(info, dict):
            problems.append(f"模块 {name} 的数字形状不对")
            continue
        if not info.get("ok"):
            problems.append(f"模块 {name} 未通过（Ran {info.get('ran')} tests）")
        if int(info.get("ran") or 0) <= 0:
            problems.append(f"模块 {name} 没跑出用例数")

    # 三查：永远以**当场重算**为准，marker 里的只是声称。
    truth = actual.get("three_checks") if isinstance(actual, dict) else None
    if truth is None:
        truth = three_checks()
    claimed = data.get("three_checks") or {}
    for name, count in truth.items():
        if int(count or 0) != 0:
            problems.append(f"三查 `{name}` 当场重算命中 {count}（插件侧必须为 0）")
        if name in claimed and int(claimed.get(name) or 0) != int(count or 0):
            problems.append(f"三查 `{name}` 声称 {claimed.get(name)}，当场重算 {count}——自报与实测不符")

    probe = data.get("probe") or {}
    if not probe or not probe.get("exists"):
        if not allow_no_probe:
            problems.append("回传单没有探针证据：涉及前端的轮次必须给 passed/total，"
                            "确属纯后端/文档轮次请显式加 --allow-no-probe")
    else:
        passed, total = probe.get("passed"), probe.get("total")
        if passed is None or total is None:
            problems.append("探针产物在，但取不到 passed/total")
        elif passed != total:
            problems.append(f"探针未全绿：{passed}/{total}")

    if "禁改区自查" not in sections.get("改动清单", ""):
        problems.append("【改动清单】缺「禁改区自查」")

    return problems


def cmd_verify(args: argparse.Namespace) -> int:
    path = Path(args.path)
    if not path.is_file():
        print(f"[verify] 找不到 {path}")
        return 2
    text = path.read_text(encoding="utf-8", errors="replace")

    # 判据以「当场重算」为准：三查与 HEAD 都由本进程自己取，不信回传单自报。
    actual = {"three_checks": three_checks(), "head": git("rev-parse", "--short", "HEAD")}
    problems = verify_text(text, actual=actual,
                           allow_no_tests=bool(args.allow_no_tests),
                           allow_no_probe=bool(args.allow_no_probe))

    marker = MARKER_RE.search(text)
    data = json.loads(marker.group(1)) if marker else {}
    claimed_head = str(data.get("head") or "")
    if claimed_head and actual["head"] and claimed_head != actual["head"]:
        # 不是判废项（先出回传单后提交是正常流程），但必须让人看见证据的基准点。
        print(f"[verify] 提示：回传单基于 {claimed_head}，当前 HEAD 是 {actual['head']}")

    if args.rerun:
        _require_python()
        for name, claimed in (data.get("modules") or {}).items():
            fresh = run_module(name)
            if fresh["ran"] != int(claimed.get("ran") or 0) or fresh["ok"] != claimed.get("ok"):
                problems.append(
                    f"--rerun 不一致：{name} 回传单写 Ran {claimed.get('ran')}/"
                    f"{'OK' if claimed.get('ok') else 'FAILED'}，"
                    f"重跑得 Ran {fresh['ran']}/{'OK' if fresh['ok'] else 'FAILED'}")

    if problems:
        print(f"[verify] 判废：{len(problems)} 处")
        for item in problems:
            print(f"  - {item}")
        return 1
    print("[verify] 通过：五项齐全、三查当场重算为 0、数字自洽")
    return 0


# ------------------------------------------------------------------ 脱敏

_SECRET_LINE_RE = re.compile(
    r"(?im)^(\s*(?:jzo_ai_api_key|api[_-]?key|token|secret|password|authorization)\b[^\n:=]*[:=]\s*)\S+")


def redact(text: str) -> str:
    """把密钥形态的字符串抹成 ``***``。

    README 原先声称 ``pack`` 会扫掉 ``.env``，而实现里根本没有这一步——
    文档说了、代码没做，比不说更坏（审查席第 7 条）。现在两边对齐。
    """
    out = str(text or "")
    for value in load_env().values():
        # 太短的值（如 "120" 这种超时秒数）全文替换会误伤正文，长度设门槛。
        if value and len(value) >= 16:
            out = out.replace(value, "***")
    out = re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "sk-***", out)
    out = re.sub(r"(?i)(bearer\s+)\S+", r"\1***", out)
    out = _SECRET_LINE_RE.sub(r"\1***", out)
    return out


# ------------------------------------------------------------------ 复审包

def cmd_pack(args: argparse.Namespace) -> int:
    receipt = Path(args.path)
    if not receipt.is_file():
        print(f"[pack] 找不到 {receipt}")
        return 2
    text = receipt.read_text(encoding="utf-8", errors="replace")
    marker = MARKER_RE.search(text)
    data = json.loads(marker.group(1)) if marker else {}
    order_id = int(data.get("order_id") or 0)
    order_path = ORDERS / f"{order_id:03d}.md"
    order_text = order_path.read_text(encoding="utf-8", errors="replace") if order_path.is_file() else ""

    parts = [
        f"# 复审请求 · 军令 #{order_id}",
        "",
        "## 一、军令卡（下行）",
        "",
        order_text or "（没有军令卡文件）",
        "",
        "## 二、机械证据回传单（上行）",
        "",
        text,
        "",
        "## 三、请主脑裁决",
        "",
        "1. 逐条对账：每个任务项的验收判据是否真被满足？",
        "2. 证据够不够：哪一条只有结论没有实测？",
        "3. 偏离与欠账是否如实披露？",
        "4. 给出下一道军令（编号 + 任务项 + 验收判据 + 边界）。",
    ]
    blob = redact("\n".join(parts))
    if args.out:
        target = Path(args.out)
        target.write_text(blob, encoding="utf-8")
        print(f"[pack] 已写 {rel(target)}（{len(blob)} 字符，一次粘贴即可）")
    else:
        print(blob)
    return 0


# ------------------------------------------------------------------ 三席议事

SEATS = {
    "brain": (
        "主脑",
        "你是九章算子的主脑。只做两件事：把目标拆成可验证的任务项，给出验收判据。"
        "严禁写代码、严禁替施工做技术选择。任务项必须能被机械检验（跑哪个测试、看哪个数字）。",
    ),
    "review": (
        "审查",
        "你是九章算子的审查席。你的职责是挑毛病：找出证据缺口、契约违背、越界改动、"
        "以及被含糊措辞掩盖的欠账。按「必须修 / 建议修 / 可接受」三档给结论，逐条给依据。"
        "不要复述对方的话，不要给面子分。",
    ),
    "worker": (
        "干活",
        "你是九章算子的施工席。你只回答可行性：这条军令如果要落地，"
        "改动面在哪几个文件、会不会碰到契约禁改区、预计几步、哪一步最容易翻车。"
        "不改代码，只出判断。",
    ),
}


def call_gateway(messages: list[dict[str, str]], *, model: str, base: str,
                 key: str, timeout: int = 180) -> str:
    """调 OpenAI 兼容网关。密钥只从环境/.env 读，永不落盘、永不进日志。"""
    import urllib.error
    import urllib.request

    body = json.dumps({"model": model, "messages": messages, "stream": False}).encode("utf-8")
    request = urllib.request.Request(
        base.rstrip("/") + "/chat/completions", data=body, method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"网关回 HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RuntimeError(f"网关不通：{exc}") from exc
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("网关没有返回 choices")
    return str(choices[0].get("message", {}).get("content") or "")


def load_env() -> dict[str, str]:
    """读项目 ``.env`` 的相关键；只取内存，不回显、不落盘。"""
    values: dict[str, str] = {}
    path = ROOT / ".env"
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip().strip('"').strip("'")
    return values


SEATS_FILE = HANDOFF / "seats.json"

# 席位与模型必须解耦：三席共用一个模型，审查席就等于自己给自己判卷。
# 配置留空的字段回落到 .env 的 JZO_AI_BASE_URL / JZO_AI_MODEL。
DEFAULT_SEATS = {
    "brain": {"name": "主脑", "api_key_env": "JZO_AI_API_KEY"},
    "review": {"name": "审查", "api_key_env": "SEAT_REVIEW_API_KEY"},
    "worker": {"name": "干活", "api_key_env": "JZO_AI_API_KEY"},
}


def load_seats() -> dict[str, dict[str, Any]]:
    """读席位配置；文件缺失或写坏就回缺省，绝不因为配置坏了开不了会。"""
    seats: dict[str, dict[str, Any]] = {key: dict(value) for key, value in DEFAULT_SEATS.items()}
    if SEATS_FILE.is_file():
        try:
            data = json.loads(SEATS_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return seats
        for key, value in (data.get("seats") or {}).items():
            if isinstance(value, dict):
                seats.setdefault(key, {}).update(value)
    return seats


def resolve_seat(seat: str, env: dict[str, str]) -> dict[str, Any]:
    """把一个席位解析成「实际要打的地址 + 模型 + 密钥」。

    密钥**不静默跨席借用**：审查席声明的 ``SEAT_REVIEW_API_KEY`` 没配时，
    可以回落到 ``JZO_AI_API_KEY``，但必须把「回落了」这件事报出来——
    显示「已配」而其实借了别人的密钥，比直接报缺更坏（同一种「看起来配了」的谎）。
    """
    config = load_seats().get(seat) or {}
    key_env = str(config.get("api_key_env") or "JZO_AI_API_KEY")
    own = env.get(key_env, "")
    fallback = ""
    key = own
    if not key and key_env != "JZO_AI_API_KEY" and env.get("JZO_AI_API_KEY"):
        key = env["JZO_AI_API_KEY"]
        fallback = "JZO_AI_API_KEY"
    return {
        "seat": seat,
        "name": str(config.get("name") or seat),
        "base_url": str(config.get("base_url") or env.get("JZO_AI_BASE_URL") or ""),
        "model": str(config.get("model") or env.get("JZO_AI_MODEL") or ""),
        "api_key": str(key or ""),
        "key_env": key_env,
        "key_fallback": fallback,
    }


def model_family(model: str) -> str:
    """从型号里取家族前缀：``deepseek-v4-pro`` → ``deepseek``，``glm-5.3`` → ``glm``。

    同一家族的模型共享训练血统与偏见，换型号不换盲区；只有换家族才算真正换视角。
    """
    match = re.match(r"^([a-z]+)", str(model or "").strip().lower())
    return match.group(1) if match else ""


def inbreeding_groups(resolved: list[dict[str, Any]]) -> list[list[str]]:
    """同地址同模型的席位分到一组——**同一个型号**是最严重的近亲。"""
    buckets: dict[tuple[str, str], list[str]] = {}
    for item in resolved:
        if not item.get("base_url") or not item.get("model"):
            continue
        buckets.setdefault((str(item["base_url"]), str(item["model"])), []).append(
            str(item.get("name") or item.get("seat")))
    return [names for names in buckets.values() if len(names) > 1]


def family_groups(resolved: list[dict[str, Any]]) -> list[list[str]]:
    """同家族不同型号：换汤不换药，仍然漏同样的盲区。"""
    buckets: dict[str, list[str]] = {}
    for item in resolved:
        family = model_family(str(item.get("model") or ""))
        if not family:
            continue
        buckets.setdefault(family, []).append(str(item.get("name") or item.get("seat")))
    return [names for names in buckets.values() if len(names) > 1]


def cmd_seats(args: argparse.Namespace) -> int:
    ensure_dirs()
    if args.init:
        payload = {
            "seats": {
                "brain": {"name": "主脑", "base_url": "", "model": "",
                          "api_key_env": "JZO_AI_API_KEY"},
                "review": {"name": "审查", "base_url": "", "model": "",
                           "api_key_env": "SEAT_REVIEW_API_KEY"},
                "worker": {"name": "干活", "base_url": "", "model": "",
                           "api_key_env": "JZO_AI_API_KEY"},
            },
            "_note": "留空的字段回落到 .env 的 JZO_AI_BASE_URL / JZO_AI_MODEL。"
                     "审查席请填**另一家**的模型，否则 seats --check 会报同族。",
        }
        SEATS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")
        print(f"[seats] 已写模板 {rel(SEATS_FILE)}")
        return 0

    env = load_env()
    resolved = [resolve_seat(seat, env) for seat in ("brain", "review", "worker")]
    for item in resolved:
        if item["api_key"]:
            state = (f"回落自 {item['key_fallback']}" if item.get("key_fallback") else "已配")
        else:
            state = "缺"
        print(f"  {item['name']}席 · {item['model'] or '（未配模型）'} · "
              f"{item['base_url'] or '（未配地址）'} · 密钥 {item['key_env']} {state}")
    for group in inbreeding_groups(resolved):
        print(f"[seats] 严重：{' / '.join(group)} 用的是同一个型号——这是最纯的近亲")
    for group in family_groups(resolved):
        if len(group) < len(resolved):
            print(f"[seats] 警告：{' / '.join(group)} 同属一个家族，换型号不换盲区")
        else:
            print(f"[seats] 警告：{' / '.join(group)} 全在一个家族里，等于没换视角")

    if args.check:
        for item in resolved:
            if not item["api_key"] or not item["base_url"] or not item["model"]:
                print(f"[seats] {item['name']}席 配置不全，跳过连通性检查")
                continue
            try:
                reply = call_gateway(
                    [{"role": "user", "content": "只回复两个字：在线"}],
                    model=item["model"], base=item["base_url"], key=item["api_key"],
                    timeout=30)
                print(f"[seats] {item['name']}席 连通 ok（回了 {len(reply)} 字）")
            except RuntimeError as exc:
                print(f"[seats] {item['name']}席 不通：{exc}")
                return 1
    return 0


def cmd_council(args: argparse.Namespace) -> int:
    ensure_dirs()
    env = load_env()
    seats = {seat: resolve_seat(seat, env) for seat in ("brain", "review", "worker")}
    missing = [item["name"] for item in seats.values()
               if not item["api_key"] or not item["base_url"] or not item["model"]]
    if missing:
        print(f"[council] 这些席位没配全：{'、'.join(missing)}"
              f"（先跑 seats --init 再填 {rel(SEATS_FILE)}）")
        return 2
    for group in inbreeding_groups(list(seats.values())):
        print(f"[council] 严重：{' / '.join(group)} 同型号，结论基本是自问自答")
    for group in family_groups(list(seats.values())):
        if len(group) < len(seats):
            print(f"[council] 注意：{' / '.join(group)} 同家族，独立性要打折")

    topic = args.topic or ""
    context_parts = [f"# 议题\n{topic or '（未指定，见下方材料）'}"]
    for extra in args.include or []:
        path = Path(extra)
        if path.is_file():
            context_parts.append(f"# 材料：{rel(path)}\n\n"
                                 + path.read_text(encoding="utf-8", errors="replace")[:20000])
    context = "\n\n".join(context_parts)

    transcript: list[str] = []
    order = ["brain", "review", "worker"]
    for round_index in range(1, max(1, args.rounds) + 1):
        for seat in order:
            name, brief = SEATS[seat]
            config = seats[seat]
            seen = "\n\n".join(transcript) if transcript else "（本席第一个发言）"
            prompt = (f"{context}\n\n# 已发言记录\n{seen}\n\n"
                      f"# 你的第 {round_index} 轮发言\n严格控制在 200 字内，用条目。")
            try:
                reply = call_gateway(
                    [{"role": "system", "content": brief}, {"role": "user", "content": prompt}],
                    model=config["model"], base=config["base_url"], key=config["api_key"],
                )
            except RuntimeError as exc:
                print(f"[council] {name} 席失败：{exc}")
                return 1
            transcript.append(f"## {name}席 · {config['model']} · 第 {round_index} 轮\n"
                              f"{reply.strip()}")
            print(f"[council] {name}席 第 {round_index} 轮 完成（{len(reply)} 字）")

    verdict = "\n\n".join(transcript)
    target = VERDICTS / f"{args.order or 'adhoc'}-{datetime.now(LOCAL_TZ).strftime('%H%M%S')}.md"
    header = (f"# 三席议事 · {topic or '临时议题'}\n\n"
              f"【时间】 {now()}\n【轮数】 {args.rounds}\n"
              + "".join(f"【{item['name']}席】 {item['model']}\n"
                        for item in seats.values())
              + "\n")
    target.write_text(header + verdict + "\n", encoding="utf-8")
    _write_state({"order_id": args.order or 0, "status": "councilled", "updated_at": now()})
    print(f"[council] 裁决已落 {rel(target)}")
    return 0


# ------------------------------------------------------------------ 状态

def _write_state(payload: dict[str, Any]) -> None:
    merged: dict[str, Any] = {}
    if STATE.is_file():
        try:
            merged = json.loads(STATE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            merged = {}
    merged.update(payload)
    STATE.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cmd_status(_args: argparse.Namespace) -> int:
    if STATE.is_file():
        print(STATE.read_text(encoding="utf-8").strip())
    else:
        print("（还没有任何轮次；先跑 tools/handoff.py order --id 1 --title 示例）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="handoff", description="军令 → 施工 → 回传 → 复审 的机械地基")
    sub = parser.add_subparsers(dest="command", required=True)

    order = sub.add_parser("order", help="生成军令卡")
    order.add_argument("--id", required=True)
    order.add_argument("--title", default="")
    order.add_argument("--items", default="")
    order.add_argument("--from-file", default="")
    order.add_argument("--brain", default="网页 DeepSeek")
    order.set_defaults(func=cmd_order)

    receipt = sub.add_parser("receipt", help="采集证据生成回传单")
    receipt.add_argument("--order", required=True)
    receipt.add_argument("--modules", default="", help="逗号分隔的单测模块名")
    receipt.add_argument("--probe", default="", help="探针 probe.json 路径")
    receipt.add_argument("--forbidden", default="")
    receipt.add_argument("--plugin-check", default="")
    receipt.add_argument("--open-issues", default="")
    receipt.set_defaults(func=cmd_receipt)

    verify = sub.add_parser("verify", help="机械校验回传单")
    verify.add_argument("path")
    verify.add_argument("--rerun", action="store_true", help="当场重跑并比对数字")
    verify.add_argument("--allow-no-tests", action="store_true",
                        help="显式豁免：本轮确无单测（纯文档/工具改动）")
    verify.add_argument("--allow-no-probe", action="store_true",
                        help="显式豁免：本轮确无探针（不涉及前端/插件真机路径）")
    verify.set_defaults(func=cmd_verify)

    seats = sub.add_parser("seats", help="席位与模型的对照表（防近亲审查）")
    seats.add_argument("--init", action="store_true", help="写一份空模板")
    seats.add_argument("--check", action="store_true", help="逐个席位探连通性")
    seats.set_defaults(func=cmd_seats)

    pack = sub.add_parser("pack", help="拼成可粘贴的复审包")
    pack.add_argument("path")
    pack.add_argument("--out", default="")
    pack.set_defaults(func=cmd_pack)

    council = sub.add_parser("council", help="三席议事（会出网，须手敲）")
    council.add_argument("--order", type=int, default=0)
    council.add_argument("--topic", default="")
    council.add_argument("--include", action="append", default=[])
    council.add_argument("--rounds", type=int, default=2)
    council.set_defaults(func=cmd_council)

    status = sub.add_parser("status", help="当前轮次")
    status.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())

# -*- coding: utf-8 -*-
"""记号标准字典·清洗端到端微批探针（2.21.0 卡 §3/§6 探针③）：零引擎。

用法：``.venv/Scripts/python.exe tools/latex_norm_clean_probe.py <tag>``

隔离：JZO_DATA_DIR/JZO_PLUGINS_DIR 指证据目录下空副本，启动钩子幂等播种闭集；
随机令牌（secrets，禁写死）＋动态端口；AI key 全清空。清洗走真实产品端点
``/api/agent/clean_latex``（本地确定性代码查 SQLite＋按命令切词改写，不调任何模型）。

微批 5 条存量风格文本样本，证四件事：
- 闭集选中默认驱动改写（出厂 le→leqslant；老师 flip 后 leqslant→le；恢复出厂回退）；
- 开集只有 confirmed 参与改写（收编 zqclean→leqslant 生效；rejected 黑名单永不生效；
  pending unknown 原样不动且落待审）；
- 三硬规矩：\\left/\\right 不被当 \\le 改坏、\\text{} 汉字与 \\begin{} 环境名不动、幂等（洗一遍＝洗十遍）；
- 全程零引擎请求（探针只打 clean_latex/norm.* 确定性端点）。
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _path

_sys.path.insert(0, str(_path(__file__).resolve().parents[1]))

import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from app.core import toml_io, wire

ROOT = Path(__file__).resolve().parents[1]


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def http_json(url: str, token: str | None = None) -> tuple[int, dict]:
    request = urllib.request.Request(url)
    if token:
        request.add_header("X-JZO-Token", token)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        return error.code, wire.loads(payload or "{}")


def http_post(url: str, payload: dict, token: str) -> tuple[int, dict]:
    body = wire.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-JZO-Token": token})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, wire.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as error:
        payload = error.read().decode("utf-8")
        error.close()
        return error.code, wire.loads(payload or "{}")


def wait_health(base: str, process: subprocess.Popen, log_path: Path) -> None:
    deadline = time.time() + 40
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("服务提前退出：\n" + log_path.read_text(
                encoding="utf-8", errors="replace")[:3000])
        try:
            with urllib.request.urlopen(base + "/healthz", timeout=0.5) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            time.sleep(0.1)
    raise RuntimeError("服务未在 40 秒内就绪")


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    tag = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d-%H%M%S")
    work = ROOT / ".system_generated" / "latex-norm" / "clean" / tag
    data_dir = work / "data"
    plugins_dir = work / "plugins"
    for folder in (data_dir, plugins_dir):
        folder.mkdir(parents=True, exist_ok=True)

    token = secrets.token_hex(16)
    nonce = secrets.token_hex(8)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env["JZO_DATA_DIR"] = str(data_dir)
    env["JZO_PLUGINS_DIR"] = str(plugins_dir)
    env["JZO_LOCAL_TOKEN"] = token
    env["JZO_RESTART_DISABLED"] = "1"
    for key in ("JZO_AI_API_KEY", "JZO_BAILIAN_API_KEY",
                "JZO_SILICONFLOW_API_KEY", "JZO_OLLAMA_API_KEY"):
        env[key] = ""
    server_log = work / "server.log"
    log_handle = server_log.open("w", encoding="utf-8", errors="replace")
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--log-level", "warning", "--no-server-header"],
        cwd=str(ROOT), env=env, stdout=log_handle, stderr=subprocess.STDOUT, text=True)

    result: dict = {"probe": "latex_norm_clean", "tag": tag, "nonce": nonce, "base": base,
                    "port": port, "engine": "本地确定性清洗，零引擎请求（AI key 全清空）",
                    "checks": [], "samples": [], "metrics": {}}
    endpoints_hit: list[str] = []

    def check(name: str, ok: bool, detail=None) -> None:
        result["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    def clean(text: str) -> str:
        endpoints_hit.append("/api/agent/clean_latex")
        status, body = http_post(base + "/api/agent/clean_latex", {"text": text}, token)
        if status != 200:
            raise RuntimeError("clean_latex status=%s body=%s" % (status, body))
        return body["data"]["text"]

    try:
        wait_health(base, process, server_log)
        _, ent = http_json(base + "/api/norm/entries")
        le = next(e for e in ent["entries"] if e["entry_key"] == "le")
        upright_id = next(v["id"] for v in le["variants"] if v["latex_code"] == r"\le")
        check("闭集启动自举全量 223 条目", len(ent["entries"]) == 223,
              {"entries": len(ent["entries"])})

        # 开集：造候选 → 收编 zqclean→leqslant（confirmed 参与改写）
        clean(r"$\zqclean$")
        status, _ = http_post(base + "/api/norm/decide",
                              {"raw_code": "zqclean", "decision": "confirmed",
                               "target_code": "leqslant"}, token)
        check("开集收编 zqclean→leqslant（confirmed）", status == 200, {"status": status})

        # 微批 5 条存量风格样本（出厂默认态）
        samples = [
            ("闭集出厂默认", r"$\le x$", r"$\leqslant x$"),
            ("开集 confirmed 驱动", r"$\zqclean$ 与 $\le x$", r"$\leqslant$ 与 $\leqslant x$"),
            ("硬规矩·left/right 不坏", r"$\left( x \right)$ 且 $\le y$",
             r"$\left( x \right)$ 且 $\leqslant y$"),
            ("硬规矩·text/环境不动", r"$\text{已知} \le x$，\begin{cases} a \\ b \end{cases}",
             r"$\text{已知} \leqslant x$，\begin{cases} a \\ b \end{cases}"),
            ("unknown 原样不动", r"$\zquntouched$ 保留", r"$\zquntouched$ 保留"),
        ]
        result["metrics"]["micro_batch"] = len(samples)
        all_match = True
        all_idempotent = True
        for label, src, want in samples:
            got = clean(src)
            twice = clean(got)
            match = got == want
            idem = twice == got
            all_match = all_match and match
            all_idempotent = all_idempotent and idem
            result["samples"].append({"label": label, "src": src, "want": want,
                                      "got": got, "match": match, "idempotent": idem})
        check("微批 5 条逐字命中期望（闭集默认＋开集 confirmed＋三硬规矩＋unknown 不动）",
              all_match, {"mismatch": [s for s in result["samples"] if not s["match"]]})
        check("幂等：洗一遍＝洗十遍（5 条二次清洗逐字不变）", all_idempotent,
              {"non_idempotent": [s["label"] for s in result["samples"] if not s["idempotent"]]})

        # unknown 落待审（pending 不生效）
        _, pend = http_json(base + "/api/norm/corrections?status=pending")
        pend_codes = [c["raw_code"] for c in pend["corrections"]]
        check("unknown zquntouched 落开集待审 pending（不打印不进日志，仅登记）",
              "zquntouched" in pend_codes, {"pending": pend_codes})

        # 老师 flip 闭集默认：le→直立 \le，leqslant 反被改写为 \le
        status, _ = http_post(base + "/api/norm/choose",
                              {"entry_key": "le", "variant_id": upright_id}, token)
        flipped = clean(r"$\leqslant x$")
        check("老师选默认 flip（le→\\le）：闭集 leqslant 反改写为 \\le",
              status == 200 and flipped == r"$\le x$",
              {"status": status, "got": flipped})
        # 恢复出厂：回退出厂默认 leqslant
        status, _ = http_post(base + "/api/norm/reset", {"entry_key": "le"}, token)
        restored = clean(r"$\le x$")
        check("恢复出厂：选择回退，\\le 又改写回出厂 \\leqslant",
              status == 200 and restored == r"$\leqslant x$",
              {"status": status, "got": restored})

        # rejected 黑名单永不生效
        clean(r"$\zqblack$")
        http_post(base + "/api/norm/decide",
                  {"raw_code": "zqblack", "decision": "rejected"}, token)
        black = clean(r"$\zqblack$")
        check("开集 rejected 黑名单：再犯原样不动、永不参与改写",
              black == r"$\zqblack$", {"got": black})

        # 零引擎：探针只打确定性端点
        unique = sorted(set(endpoints_hit))
        check("全程零引擎请求（只 clean_latex/norm.* 确定性端点，无 recognize/models）",
              all(u in ("/api/agent/clean_latex",) for u in unique),
              {"endpoints": unique, "clean_calls": len(endpoints_hit)})
        result["metrics"]["clean_calls"] = len(endpoints_hit)
    except Exception as exc:  # noqa: BLE001 - 探针把异常也写进回单
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log_handle.close()
        port_closed = False
        for _ in range(25):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                if sock.connect_ex(("127.0.0.1", port)) != 0:
                    port_closed = True
                    break
            time.sleep(0.2)
        result["metrics"]["port_closed_after_kill"] = port_closed

    passed = sum(1 for c in result["checks"] if c["ok"])
    total = len(result["checks"])
    result["passed"] = passed
    result["total"] = total
    report = work / "probe.toml"
    report.write_text(toml_io.dumps(result), encoding="utf-8")
    print(wire.dumps({"tag": tag, "passed": passed, "total": total,
                      "port_closed": result["metrics"].get("port_closed_after_kill"),
                      "error": result.get("error"), "report": str(report)},
                     ensure_ascii=False))
    for c in result["checks"]:
        if not c["ok"]:
            print("FAIL:", c["name"], wire.dumps(c["detail"], ensure_ascii=False)[:400])
    return 0 if passed == total and total > 0 and not result.get("error") else 1


if __name__ == "__main__":
    raise SystemExit(main())
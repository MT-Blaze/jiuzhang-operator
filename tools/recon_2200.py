"""侦查脚本（2.20.0 卡§3/§4）：注册表 64 位显存真值＋国内源可达性。只读、不出网安装。

不是交付探针：仅侦查取证，结论抄进回单。跑法：
.venv/Scripts/python.exe tools/recon_2200.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass


def registry_vram() -> list[dict]:
    import winreg
    base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    out = []
    root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base)
    i = 0
    while True:
        try:
            sub = winreg.EnumKey(root, i)
        except OSError:
            break
        i += 1
        if not sub.isdigit():
            continue
        row = {"sub": sub}
        try:
            sk = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base + "\\" + sub)
        except OSError as exc:
            row["error"] = str(exc)
            out.append(row)
            continue
        for field, key in (("name", "DriverDesc"),
                           ("qw", "HardwareInformation.qwMemorySize"),
                           ("mem", "HardwareInformation.MemorySize")):
            try:
                row[field] = winreg.QueryValueEx(sk, key)[0]
            except OSError:
                row[field] = None
        if isinstance(row.get("qw"), int) and row["qw"] > 0:
            row["qw_gb"] = round(row["qw"] / (1024 ** 3), 2)
        out.append(row)
    return out


def reach(url: str, timeout: float = 2.0) -> dict:
    req = urllib.request.Request(url, method="GET",
                                 headers={"User-Agent": "JiuzhangOperator/1.0 recon"})
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(256)
            return {"url": url, "ok": True, "status": resp.status,
                    "ms": int((time.monotonic() - t0) * 1000)}
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "ok": False, "err": str(exc)[:120],
                "ms": int((time.monotonic() - t0) * 1000)}


PIP = {
    "aliyun": "https://mirrors.aliyun.com/pypi/simple/llama-cpp-python/",
    "tsinghua": "https://pypi.tuna.tsinghua.edu.cn/simple/llama-cpp-python/",
    "tencent": "https://mirrors.cloud.tencent.com/pypi/simple/llama-cpp-python/",
    "ustc": "https://pypi.mirrors.ustc.edu.cn/simple/llama-cpp-python/",
}
WEIGHT = {
    "modelscope": "https://modelscope.cn/models/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/resolve/master/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
    "hf-mirror": "https://hf-mirror.com/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/resolve/main/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf",
    "gitcode": "https://gitcode.com/",
}


def main() -> None:
    print("=== REGISTRY_VRAM ===")
    print(json.dumps(registry_vram(), ensure_ascii=False, indent=1))
    print("=== PIP_MIRRORS (llama-cpp-python index) ===")
    for name, url in PIP.items():
        print(name, json.dumps(reach(url), ensure_ascii=False))
    print("=== WEIGHT_SOURCES (HEAD-ish GET 256B) ===")
    for name, url in WEIGHT.items():
        print(name, json.dumps(reach(url, timeout=4.0), ensure_ascii=False))


if __name__ == "__main__":
    main()
"""只读显存探针（四合一卡 §3）：本机显存一次一测，不缓存，换机自动重算（D3b）。

只读两条路：NVIDIA 驱动自带的 nvidia-smi 优先；没有则 Windows WMI
（Win32_VideoController.AdapterRAM）。两条都不在就如实报「读不到」，
绝不猜一个数。WMI 的 AdapterRAM 是 32 位字段，4G 以上会封顶低估，
detail 里必须把这条丑话说在前头。本模块不出网、不写盘、不改任何配置。
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

NVIDIA_TIMEOUT = 10
WMI_TIMEOUT = 20
WMI_SCRIPT = ("(Get-CimInstance Win32_VideoController | "
              "Measure-Object -Property AdapterRAM -Maximum).Maximum")


def _run_text(cmd: list[str], timeout: int) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""
    raw = proc.stdout or b""
    for encoding in ("utf-8", "gbk"):
        try:
            return proc.returncode, raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return proc.returncode, raw.decode("utf-8", "replace")


def _nvidia() -> tuple[float, str] | None:
    """nvidia-smi 读显存总量（MiB）；多卡取最大的一张。"""
    rc, text = _run_text(
        ["nvidia-smi", "--query-gpu=name,memory.total",
         "--format=csv,noheader,nounits"], NVIDIA_TIMEOUT)
    if rc != 0:
        return None
    best_gb, best_name = 0.0, ""
    for line in text.splitlines():
        parts = [item.strip() for item in line.split(",")]
        if len(parts) < 2 or not parts[-1].isdigit():
            continue
        gb = int(parts[-1]) / 1024.0
        if gb > best_gb:
            best_gb, best_name = gb, ", ".join(parts[:-1])
    return (best_gb, best_name) if best_gb > 0 else None


def _wmi() -> tuple[float, str] | None:
    """Windows WMI 兜底：AdapterRAM 字节数；32 位字段，大显存会低估。"""
    if sys.platform != "win32":
        return None
    rc, text = _run_text(["powershell", "-NoProfile", "-Command", WMI_SCRIPT],
                         WMI_TIMEOUT)
    value = text.strip()
    if rc != 0 or not value.isdigit():
        return None
    gb = int(value) / (1024.0 ** 3)
    return (gb, "") if gb > 0 else None


def probe() -> dict[str, Any]:
    """本机显存快照：vram_gb / vram_label / gpu_name / vram_source / detail。"""
    found = _nvidia()
    source, detail = "nvidia-smi", ""
    if found is None:
        found = _wmi()
        source = "wmi"
        if found is not None:
            detail = ("WMI 的 AdapterRAM 读数上限约 4G，大显存可能被低估；"
                      "NVIDIA 卡以 nvidia-smi 为准。")
    if found is None:
        return {"vram_gb": 0.0, "vram_label": "读不到", "gpu_name": "",
                "vram_source": "",
                "detail": "只读显存探针都不可用（nvidia-smi / WMI 均无），按不支持处理。"}
    gb, name = found
    return {"vram_gb": round(gb, 1), "vram_label": "%.1fG" % gb,
            "gpu_name": name, "vram_source": source, "detail": detail}


def tier_for(vram_gb: float, tiers: list[dict[str, Any]]) -> dict[str, Any] | None:
    """显存落在哪一档：取 min_gb 不超过本机显存的最高档；不足最低档返回 None。"""
    picked = None
    for tier in tiers:
        try:
            minimum = float(tier.get("min_gb") or 0)
        except (TypeError, ValueError):
            continue
        if vram_gb >= minimum and (picked is None or minimum >= float(picked["min_gb"])):
            picked = tier
    return picked
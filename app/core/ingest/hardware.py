"""只读显存探针（四合一卡 §3／2.20.0 卡§3）：真测一次一算，不缓存结论（D3b）。

2.20.0 卡§1：真测只在老师点进配置中心那一刻发起；启动注入下拉用 snapshot()
复用上次真测快照（没测过＝中性「未检测」），不在启动/轮询里跑探针。

只读三条路：NVIDIA 驱动自带的 nvidia-smi 优先；其次 Windows 注册表
HardwareInformation.qwMemorySize（64 位真值，大显存不封顶）；最后 WMI
（Win32_VideoController.AdapterRAM，32 位字段 4G 以上会低估，detail 里把
丑话说在前头）。三条都不在就如实报「读不到」，绝不猜一个数，不加 override。
本模块不出网、不写盘、不改任何配置。
"""

from __future__ import annotations

import subprocess
import sys
from typing import Any

NVIDIA_TIMEOUT = 10
WMI_TIMEOUT = 20
WMI_SCRIPT = ("(Get-CimInstance Win32_VideoController | "
              "Measure-Object -Property AdapterRAM -Maximum).Maximum")
REGISTRY_BASE = (r"SYSTEM\CurrentControlSet\Control\Class"
                 r"\{4d36e968-e325-11ce-bfc1-08002be10318}")
# 虚拟/远程适配器不是老师那张卡：有显存值也不取（多卡取主显示卡口径）。
_VIRTUAL_MARKERS = ("remote display", "idd", "virtual", "parsec", "usb display")


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


def _registry_rows() -> list[dict[str, Any]]:
    """注册表显示适配器清单（只读）：DriverDesc＋64 位 qwMemorySize；缺值记 None。"""
    if sys.platform != "win32":
        return []
    import winreg  # noqa: PLC0415 - 仅 Windows 需要，按需导入

    rows: list[dict[str, Any]] = []
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, REGISTRY_BASE)
    except OSError:
        return []
    with root:
        index = 0
        while True:
            try:
                sub = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1
            if not sub.isdigit():
                continue
            row: dict[str, Any] = {"name": "", "qw": None}
            try:
                with winreg.OpenKey(root, sub) as key:
                    for field, value in (("name", "DriverDesc"),
                                         ("qw", "HardwareInformation.qwMemorySize")):
                        try:
                            row[field] = winreg.QueryValueEx(key, value)[0]
                        except OSError:
                            pass
            except OSError:
                continue
            rows.append(row)
    return rows


def _pick_registry(rows: list[dict[str, Any]]) -> tuple[float, str] | None:
    """多卡取主显示卡：跳过虚拟/远程适配器；多张物理卡取显存最大的一张。"""
    best_gb, best_name = 0.0, ""
    for row in rows:
        qw = row.get("qw")
        if not isinstance(qw, int) or qw <= 0:
            continue
        name = str(row.get("name") or "")
        low = name.lower()
        if any(mark in low for mark in _VIRTUAL_MARKERS):
            continue
        gb = qw / (1024.0 ** 3)
        if gb > best_gb:
            best_gb, best_name = gb, name
    return (best_gb, best_name) if best_gb > 0 else None


def _registry() -> tuple[float, str] | None:
    """注册表 64 位真值（2.20.0 卡§3）：读不到一律回 None，交 WMI 兜底，不报错。"""
    try:
        return _pick_registry(_registry_rows())
    except Exception:  # noqa: BLE001 - 注册表残缺/权限异常只该降级
        return None


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
    global _LAST
    found = _nvidia()
    source, detail = "nvidia-smi", ""
    if found is None:
        found = _registry()
        source = "registry"
    if found is None:
        found = _wmi()
        source = "wmi"
        if found is not None:
            detail = ("WMI 的 AdapterRAM 读数上限约 4G，大显存可能被低估；"
                      "NVIDIA 卡以 nvidia-smi 为准。")
    if found is None:
        _LAST = {"vram_gb": 0.0, "vram_label": "读不到", "gpu_name": "",
                 "vram_source": "",
                 "detail": "只读显存探针都不可用（nvidia-smi / 注册表 / WMI 均无），按不支持处理。"}
        return dict(_LAST)
    gb, name = found
    _LAST = {"vram_gb": round(gb, 1), "vram_label": "%.1fG" % gb,
             "gpu_name": name, "vram_source": source, "detail": detail}
    return dict(_LAST)


# 2.20.0 卡§1：硬件检测只在老师点进配置中心那一刻跑；启动注入下拉复用上次快照。
_LAST: dict[str, Any] | None = None


def snapshot() -> dict[str, Any]:
    """上次真测快照（没测过＝中性「未检测」，不猜数）；只供启动下拉，不替代现算。"""
    if _LAST is not None:
        return dict(_LAST)
    return {"vram_gb": 0.0, "vram_label": "未检测", "gpu_name": "",
            "vram_source": "", "detail": ""}


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
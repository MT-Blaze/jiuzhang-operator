"""国内镜像测速选路（2.20.0 卡§7）：安装点击内并行小请求选最快，源健康现算。

只读测速（GET 前 256 字节、2 秒超时），不安装、不写盘、不缓存名次；
pip 四家＋权重三源全走国内，禁 GitHub。今日快的源明日未必快，每次点击重测。
测速在【安装】点击发起的后台作业里跑＝出网合规（卡§0/§7）。
"""

from __future__ import annotations

import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any

RACE_TIMEOUT = 2.0
# hf-mirror 非 LFS 小件（词表/yml）的 CDN 对脚本 UA 回 403（座3 探针实证：
# Python-urllib 与带 JiuzhangOperator 记号的 UA 全拒，浏览器/curl/Wget UA 全通）；
# 测速与下载同用此 UA，测速结果才代表真下载能力。
WEIGHT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
PIP_MIRRORS = (
    ("阿里云", "https://mirrors.aliyun.com/pypi/simple/"),
    ("清华", "https://pypi.tuna.tsinghua.edu.cn/simple"),
    ("腾讯", "https://mirrors.cloud.tencent.com/pypi/simple/"),
    ("中科大", "https://pypi.mirrors.ustc.edu.cn/simple/"),
)
WEIGHT_HOSTS = (
    ("ModelScope", "https://modelscope.cn"),
    ("hf-mirror", "https://hf-mirror.com"),
    ("GitCode", "https://gitcode.com"),
)


def _probe(name: str, url: str) -> dict[str, Any]:
    started = time.monotonic()
    ok = False
    try:
        request = urllib.request.Request(url, headers={"User-Agent": WEIGHT_UA})
        with urllib.request.urlopen(request, timeout=RACE_TIMEOUT) as response:
            response.read(256)
            ok = 200 <= response.status < 400
    except Exception:  # noqa: BLE001 - 测速失败只记不通，绝不抛
        ok = False
    return {"name": name, "url": url, "ok": ok,
            "ms": int((time.monotonic() - started) * 1000)}


def race(candidates: list[tuple[str, str]]) -> list[dict[str, Any]]:
    """并行测速：通的按延迟排前，不通的垫后（调用方只取通的，全败显性）。"""
    if not candidates:
        return []
    with ThreadPoolExecutor(max_workers=min(8, len(candidates))) as pool:
        rows = list(pool.map(lambda item: _probe(*item), candidates))
    rows.sort(key=lambda row: (not row["ok"], row["ms"]))
    return rows


def pip_candidates(package: str) -> list[tuple[str, str]]:
    """pip 包索引页测速地址（四家国内镜像）。"""
    return [(name, base.rstrip("/") + "/" + package + "/")
            for name, base in PIP_MIRRORS]


def pick_note(raced: list[dict[str, Any]]) -> str:
    """人话显示选了哪个源；全不通也如实说，不静默。"""
    good = [row for row in raced if row["ok"]]
    if not good:
        return "国内源测速全不通（%s），安装无法发起。" % "、".join(
            row["name"] for row in raced)
    return "测速选源：%s（实测 %dms，共 %d 家可达）。" % (
        good[0]["name"], good[0]["ms"], len(good))
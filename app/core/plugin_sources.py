"""官方插件索引的国内可达镜像（2026-10-24 v0.5.1 军令）。

背景：raw.githubusercontent.com 在国内大面积不可达，默认直链会把
「点【拉取清单】」变成无限转圈。这里只登记**官方索引本身**的镜像地址，
不登记任何插件 zip 的下载源——插件 zip 的镜像仍由索引条目的 ``mirrors``
字段声明，用户点【在线安装】时才按条目地址取包。

顺序即回退顺序：gh-proxy（GitHub 反代，取到的是分支最新内容）→ ghfast
→ jsDelivr / fastly.jsDelivr（CDN 边缘，分支缓存可能滞后）→ 官方 Raw
（境外网络兜底）。主源放反代而不是 jsDelivr，是因为 jsDelivr 的 ``@main``
分支缓存最长可滞后 12 小时，刚推库的新索引可能在首批用户那里仍是旧版；
需要「点开即新版」时，反代是更稳的第一跳。
所有地址都在用户点击后才访问，且只发只读 GET；底座不自动轮询、
不自动更新、不批量拉取。
"""

from __future__ import annotations

OFFICIAL_INDEX_PRIMARY = (
    "https://gh-proxy.com/https://raw.githubusercontent.com/MT-Blaze/jiuzhang-operator/main/plugins.json"
)

OFFICIAL_INDEX_SOURCES: tuple[str, ...] = (
    OFFICIAL_INDEX_PRIMARY,
    "https://ghfast.top/https://raw.githubusercontent.com/MT-Blaze/jiuzhang-operator/main/plugins.json",
    "https://cdn.jsdelivr.net/gh/MT-Blaze/jiuzhang-operator@main/plugins.json",
    "https://fastly.jsdelivr.net/gh/MT-Blaze/jiuzhang-operator@main/plugins.json",
    "https://raw.githubusercontent.com/MT-Blaze/jiuzhang-operator/main/plugins.json",
)

MAX_INDEX_ATTEMPTS = len(OFFICIAL_INDEX_SOURCES)


def is_official_index_url(url: str) -> bool:
    return str(url or "").strip() in OFFICIAL_INDEX_SOURCES


def index_candidates(requested_url: str, allow_mirrors: bool) -> list[str]:
    """返回本次拉取要依次尝试的地址。

    只有用户填的就是官方主源/官方镜像之一时才追加备用源；用户亲手改成
    第三方索引后，底座只访问那一个地址，不替用户擅自换源。
    """
    requested = str(requested_url or "").strip()
    if not allow_mirrors or not is_official_index_url(requested):
        return [requested]
    ordered = [requested]
    ordered.extend(item for item in OFFICIAL_INDEX_SOURCES if item != requested)
    return ordered[:MAX_INDEX_ATTEMPTS]

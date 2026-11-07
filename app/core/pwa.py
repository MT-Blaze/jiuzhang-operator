"""PWA 可安装清单：数据类定义，路由按浏览器要求以 ``application/manifest+json`` 下发。

清单不再落 ``static/manifest.json`` 文件——浏览器只要求一个 URL，不要求磁盘上
有同名文件。字段在内存中是 dataclass，对外编码由 FastAPI 完成。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

MANIFEST_PATH = "/manifest.webmanifest"
MANIFEST_MEDIA_TYPE = "application/manifest+json"


@dataclass(frozen=True)
class Icon:
    src: str
    sizes: str
    type: str = "image/png"
    purpose: str = "any"


@dataclass(frozen=True)
class WebManifest:
    name: str
    short_name: str
    description: str
    lang: str
    start_url: str
    scope: str
    display: str
    background_color: str
    theme_color: str
    icons: tuple[Icon, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return asdict(self)


MANIFEST = WebManifest(
    name="九章算子 · Jiuzhang Operator",
    short_name="九章算子",
    description="为独立教师打造的模块化数学题库底座。永久免费、完全本地、插件自由。",
    lang="zh-CN",
    start_url="/",
    scope="/",
    display="standalone",
    background_color="#f6f2e9",
    theme_color="#a63b2b",
    icons=(
        Icon(src="/static/icons/icon-192.png", sizes="192x192", purpose="any"),
        Icon(src="/static/icons/icon-512.png", sizes="512x512", purpose="any maskable"),
    ),
)

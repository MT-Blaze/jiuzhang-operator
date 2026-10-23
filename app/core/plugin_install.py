"""插件 zip 包的本机安装：校验、解压、落地 plugins/。

契约来源：PLUGIN_SPEC §1.2。安装永远由用户亲手发起（拖拽或选文件），
底座不拉任何远程源、不自动更新；唯一例外是 §1.2 末追认的随包种子插件首启静默安装。
zip 只是运输容器：

- 拒绝加密条目、符号链接、绝对路径、``..`` 穿越、嵌套 zip；
- 条目数与解压总量设上限，防 zip 炸弹；
- 解压先进临时暂存区，过完 ``plugin.json`` 全套契约校验才落地；
- 已存在同名插件时默认拒绝（409），用户显式确认 ``replace`` 才覆盖。
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import stat
import tempfile
import zipfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any

from app.core.config import settings
from app.core.plugins import _PLUGIN_ID, PluginRejected, validate_plugin

# 上传的 zip 本体上限（50 MB）：个人插件是文本 + 少量图片，用不到更多。
MAX_ZIP_BYTES = 50 * 1024 * 1024
# 解压后总量上限（256 MB）与条目数上限：防 zip 炸弹。
MAX_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_ENTRIES = 2000


class PluginInstallError(Exception):
    """安装被拒绝。``status`` 给 API 层映射 HTTP 状态码。"""

    def __init__(self, message: str, status: int = 400, code: str = "rejected") -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.code = code


def _check_entry(info: zipfile.ZipInfo) -> PurePosixPath:
    """单条目安全校验，返回包内相对路径。"""
    if info.flag_bits & 0x1:
        raise PluginInstallError("zip 内含加密条目，底座拒绝解析（PLUGIN_SPEC §1.2 禁止项）")

    raw = info.filename.replace("\\", "/")
    if not raw or raw.startswith("/"):
        raise PluginInstallError(f"zip 内含绝对路径条目：{info.filename!r}")
    if len(raw) > 1 and raw[1] == ":":
        raise PluginInstallError(f"zip 内含盘符路径条目：{info.filename!r}")

    relative = PurePosixPath(raw)
    if ".." in relative.parts:
        raise PluginInstallError(f"zip 内含路径穿越条目：{info.filename!r}")

    mode = (info.external_attr >> 16) & 0xFFFF
    if mode and stat.S_ISLNK(mode):
        raise PluginInstallError(f"zip 内含符号链接条目：{info.filename!r}")

    if not info.is_dir() and raw.lower().endswith(".zip"):
        raise PluginInstallError(f"zip 内禁止嵌套 zip 包：{info.filename!r}")
    return relative


def _find_plugin_root(entries: list[PurePosixPath]) -> tuple[str, ...]:
    """定位包内插件根目录。

    两种合法结构：zip 顶层就是插件目录内容（plugin.json 在顶层），
    或所有条目都收在唯一一个顶层目录下（该目录名即插件 id）。
    返回插件根的前缀 parts（顶层结构时为空元组）。
    """
    if PurePosixPath("plugin.json") in entries:
        return ()

    # __MACOSX、.DS_Store 之类打包噪音不参与「唯一顶层目录」判定
    tops = {
        parts[0]
        for parts in (entry.parts for entry in entries)
        if parts and parts[0] != "__MACOSX" and not parts[0].startswith(".")
    }
    if len(tops) == 1:
        top = next(iter(tops))
        if PurePosixPath(top) / "plugin.json" in entries:
            return (top,)

    raise PluginInstallError(
        "找不到 plugin.json：zip 顶层目录名必须等于插件 id，其内含 plugin.json；"
        "或把 plugin.json 直接放在 zip 顶层"
    )


def _safe_extract(zf: zipfile.ZipFile, staging: Path, prefix: tuple[str, ...]) -> Path:
    """逐条目解压到暂存区，路径全部重新拼装，不信任 zip 内文件名。"""
    total = 0
    plugin_root = staging.joinpath(*prefix) if prefix else staging
    for info in zf.infolist():
        relative = _check_entry(info)
        parts = relative.parts
        if parts[0] == "__MACOSX" or parts[0].startswith("."):
            continue  # 打包噪音（资源 fork、.DS_Store）不落地
        if prefix and (len(parts) < len(prefix) or parts[: len(prefix)] != prefix):
            continue  # 唯一顶层目录之外的散件直接忽略
        target = staging.joinpath(*parts)
        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        total += info.file_size
        if total > MAX_UNCOMPRESSED_BYTES:
            raise PluginInstallError("解压总量超过上限（256 MB），疑似 zip 炸弹")
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as src, open(target, "wb") as dst:
            shutil.copyfileobj(src, dst, length=1024 * 256)
    if not (plugin_root / "plugin.json").is_file():
        raise PluginInstallError("解压后未找到 plugin.json")
    return plugin_root


@contextlib.contextmanager
def staged_plugin_from_zip(data: bytes) -> Iterator[tuple[Path, dict[str, Any]]]:
    """校验 zip，并在暂存区解出以清单 id 命名的插件根目录。

    **安全校验只有这一份**：本机拖装、在线安装与插件热更新（PLUGIN_SPEC §1.7
    要求「完全同款」的暂存区校验）都走这里，不给第二个实现留机会。
    调用方在 with 块里把目录搬到最终位置；出了 with，暂存区连同里面
    的东西一起消失——校验不通过的包在落地前就被整体丢弃，失败零残留。
    """
    if not data:
        raise PluginInstallError("上传内容为空")
    if len(data) > MAX_ZIP_BYTES:
        raise PluginInstallError("zip 包超过 50 MB 上限", status=413, code="too_large")
    if not zipfile.is_zipfile(io.BytesIO(data)):
        raise PluginInstallError("不是有效的 zip 文件（底座只收标准 zip，解压即用）")

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        infos = zf.infolist()
        if not infos:
            raise PluginInstallError("zip 包是空的")
        if len(infos) > MAX_ENTRIES:
            raise PluginInstallError("zip 条目数超过上限（2000），疑似 zip 炸弹")
        entries = [_check_entry(info) for info in infos]
        prefix = _find_plugin_root(entries)

        with tempfile.TemporaryDirectory(prefix="jzo-plugin-install-") as tmp:
            staging = Path(tmp)
            unpacked = staging / "pkg"
            unpacked.mkdir()
            plugin_root = _safe_extract(zf, unpacked, prefix)

            try:
                manifest = json.loads((plugin_root / "plugin.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise PluginInstallError(f"plugin.json 无法解析：{exc}") from exc

            plugin_id = manifest.get("id") if isinstance(manifest, dict) else None
            if not isinstance(plugin_id, str) or _PLUGIN_ID.fullmatch(plugin_id) is None:
                raise PluginInstallError("plugin.json 的 id 缺失或不是反向域名格式")

            # 落地目录名以清单 id 为唯一事实来源；改名后再过全套契约校验
            named_root = staging / plugin_id
            shutil.move(str(plugin_root), str(named_root))
            try:
                info = validate_plugin(named_root, manifest)
            except PluginRejected as exc:
                raise PluginInstallError(f"plugin.json 未通过契约校验：{exc}") from exc
            except OSError as exc:
                raise PluginInstallError(f"插件包读取失败：{exc}") from exc

            yield named_root, info


def install_plugin_from_zip(data: bytes, replace: bool = False) -> dict[str, Any]:
    """校验并安装一个插件 zip 包，返回发现接口同款的插件信息。

    Raises:
        PluginInstallError: 任何一步不合格；``status`` 为建议的 HTTP 状态码。
    """
    plugins_dir = Path(settings.plugins_dir)
    plugins_dir.mkdir(parents=True, exist_ok=True)

    with staged_plugin_from_zip(data) as (named_root, info):
        destination = plugins_dir / info["id"]
        if destination.exists():
            if not replace:
                raise PluginInstallError(
                    f"插件 {info['id']} 已安装。",
                    status=409,
                    code="exists",
                )
            if destination.is_symlink() or not destination.is_dir():
                raise PluginInstallError(f"plugins/{info['id']} 不是目录，拒绝覆盖")
            shutil.rmtree(destination)

        # 暂存区与 plugins/ 同盘时 move 是原子改名，不会留半装状态
        shutil.move(str(named_root), str(destination))

    return info

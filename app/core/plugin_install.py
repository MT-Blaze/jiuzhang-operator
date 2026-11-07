"""插件 zip 包的本机安装：校验、解压、落地 plugins/。

契约来源：PLUGIN_SPEC §1.2 / §1.8。安装永远由用户亲手发起（拖拽或选文件），
底座不拉任何远程源、不自动更新。zip 只是运输容器：

- 拒绝加密条目、符号链接、绝对路径、``..`` 穿越、嵌套 zip；
- 条目数与解压总量设上限，防 zip 炸弹；
- 解压先进临时暂存区，过完 ``plugin.toml`` 全套契约校验才落地；
- 已存在同名插件时默认拒绝（409），用户显式确认 ``replace`` 才覆盖；
- 套件包（顶层 ``suite.toml``）一次装多个子插件，整包同进同退：
  依赖预检不过整包拒绝，落地中途失败按备份回滚，plugins/ 不留半套。
"""

from __future__ import annotations

import contextlib
import io
import shutil
import stat
import tempfile
import uuid
import zipfile
from collections.abc import Iterator
from pathlib import Path, PurePosixPath
from typing import Any

from app.core import manifests, plugin_suite, toml_io, wire
from app.core.config import plugins_dir
from app.core.plugins import _PLUGIN_ID, PluginRejected, discover_plugins, validate_plugin

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
    """定位单插件包内的插件根目录。

    两种合法结构：zip 顶层就是插件目录内容（``plugin.toml`` 在顶层），
    或所有条目都收在唯一一个顶层目录下（该目录名即插件 id）。
    旧包的 ``plugin.json`` 同样认，落地时统一转成 TOML。
    """
    prefix = manifests.plugin_root_prefix(entries)
    if prefix is not None:
        return prefix
    raise PluginInstallError(
        "找不到 plugin.toml：zip 顶层目录名必须等于插件 id，其内含 plugin.toml；"
        "或把 plugin.toml 直接放在 zip 顶层"
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
    if manifests.manifest_path(plugin_root) is None:
        raise PluginInstallError("解压后未找到 plugin.toml")
    return plugin_root


def _stage_plugin(
    zf: zipfile.ZipFile, staging: Path, prefix: tuple[str, ...], slot: str
) -> tuple[Path, dict[str, Any]]:
    """把一个子插件解到暂存区并以清单 id 命名，过完全套契约校验。"""
    unpacked = staging / ("pkg-" + slot)
    unpacked.mkdir()
    plugin_root = _safe_extract(zf, unpacked, prefix)
    try:
        manifest = manifests.normalize_manifest(plugin_root)
    except (OSError, ValueError) as exc:
        raise PluginInstallError(f"插件清单无法解析：{exc}") from exc

    plugin_id = manifest.get("id") if isinstance(manifest, dict) else None
    if not isinstance(plugin_id, str) or _PLUGIN_ID.fullmatch(plugin_id) is None:
        raise PluginInstallError("插件清单的 id 缺失或不是反向域名格式")

    named_root = staging / plugin_id
    if named_root.exists():
        raise PluginInstallError(f"包里出现了重复的插件 id：{plugin_id}")
    shutil.move(str(plugin_root), str(named_root))
    try:
        info = validate_plugin(named_root, manifest)
    except PluginRejected as exc:
        raise PluginInstallError(f"插件清单未通过契约校验：{exc}") from exc
    except OSError as exc:
        raise PluginInstallError(f"插件包读取失败：{exc}") from exc
    return named_root, info


def _read_suite_manifest(
    zf: zipfile.ZipFile, entries: list[PurePosixPath]
) -> dict[str, Any] | None:
    """顶层有 suite.toml 就是套件包；单插件包返回 None。

    套件版式固定为「顶层 suite.toml + 各子插件目录」；旧包的 ``suite.json``
    只读兼容，落地时不需要它随行。
    """
    names = manifests.suite_entry_names(entries)
    if not names:
        return None
    name = names[0]

    raw_info = zf.getinfo(name)
    if raw_info.file_size > plugin_suite.MAX_SUITE_BYTES:
        raise PluginInstallError("suite.toml 超过 64 KB 上限")
    try:
        text = zf.read(raw_info).decode("utf-8")
        raw = toml_io.loads(text) if name.endswith(".toml") else wire.loads(text)
    except (UnicodeDecodeError, ValueError) as exc:
        raise PluginInstallError(f"suite.toml 无法解析：{exc}") from exc
    try:
        return plugin_suite.parse_suite_manifest(raw)
    except plugin_suite.SuiteRejected as exc:
        raise PluginInstallError(f"suite.toml 未通过契约校验：{exc}") from exc


def _check_suite_layout(entries: list[PurePosixPath], suite: dict[str, Any]) -> None:
    """套件包顶层只许有套件清单与清单里声明的成员目录。"""
    members = set(suite["plugins"])
    tops = {
        parts[0]
        for parts in (entry.parts for entry in entries)
        if parts and parts[0] != "__MACOSX" and not parts[0].startswith(".")
    }
    allowed = set(manifests.SUITE_MANIFESTS)
    extra = sorted(tops - members - allowed)
    if extra:
        raise PluginInstallError(
            "套件包里有套件清单未声明的顶层内容：" + "、".join(extra)
        )
    absent = sorted(members - tops)
    if absent:
        raise PluginInstallError(
            "suite.toml 声明的成员在包里不存在：" + "、".join(absent)
        )


def _check_suite_closure(staged: list[tuple[Path, dict[str, Any]]]) -> None:
    """套件必须自带全部依赖：套件的目的就是一次装完，不能又留一个空壳。"""
    ids = {info["id"] for _, info in staged}
    for _, info in staged:
        missing = [item for item in info.get("requires") or [] if item not in ids]
        if missing:
            raise PluginInstallError(
                f"套件不完整：{info['id']} 依赖的 " + "、".join(missing)
                + " 不在 suite.toml 的 plugins 里（套件必须自带全部依赖）",
                code="incomplete_suite",
            )


@contextlib.contextmanager
def staged_plugins_from_zip(
    data: bytes,
) -> Iterator[tuple[list[tuple[Path, dict[str, Any]]], dict[str, Any] | None]]:
    """校验 zip 并在暂存区解出全部子插件（单插件包 = 一个成员）。

    **安全校验只有这一份**：本机拖装、在线安装、套件安装与插件热更新
    （PLUGIN_SPEC §1.7 要求「完全同款」的暂存区校验）都走这里。
    调用方在 with 块里把目录搬到最终位置；出了 with，暂存区连同里面的
    东西一起消失——校验不通过的包在落地前就被整体丢弃，失败零残留。
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
        if sum(info.file_size for info in infos) > MAX_UNCOMPRESSED_BYTES:
            raise PluginInstallError("解压总量超过上限（256 MB），疑似 zip 炸弹")
        entries = [_check_entry(info) for info in infos]
        suite = _read_suite_manifest(zf, entries)

        with tempfile.TemporaryDirectory(prefix="jzo-plugin-install-") as tmp:
            staging = Path(tmp)
            staged: list[tuple[Path, dict[str, Any]]] = []
            if suite is None:
                prefix = _find_plugin_root(entries)
                staged.append(_stage_plugin(zf, staging, prefix, "root"))
            else:
                _check_suite_layout(entries, suite)
                for position, member in enumerate(suite["plugins"]):
                    staged.append(_stage_plugin(zf, staging, (member,), str(position)))
                _check_suite_closure(staged)
            yield staged, suite


@contextlib.contextmanager
def staged_plugin_from_zip(data: bytes) -> Iterator[tuple[Path, dict[str, Any]]]:
    """单插件暂存视图：热更新只接受单个插件包，套件包走整包安装。"""
    with staged_plugins_from_zip(data) as (staged, suite):
        if suite is not None:
            raise PluginInstallError(
                "这是插件套件包，不能按单个插件热更新；请在设置页整包安装",
                code="suite_package",
            )
        if len(staged) != 1:
            raise PluginInstallError("包里不止一个插件，无法按单个插件处理")
        yield staged[0]


def _installed_plugin_ids() -> set[str]:
    """当前能被发现的插件 id（坏清单不算数，避免把坏依赖当满足）。"""
    return {info["id"] for info in discover_plugins()["plugins"]}


def _precheck_install(
    target_root: Path, staged: list[tuple[Path, dict[str, Any]]], replace: bool
) -> None:
    """落地前的两道闸：同名冲突与依赖缺失，任一不过整包拒绝。"""
    ids = [info["id"] for _, info in staged]
    existing = [plugin_id for plugin_id in ids if (target_root / plugin_id).exists()]
    if existing and not replace:
        raise PluginInstallError(
            ("这些插件已安装：" if len(existing) > 1 else "插件已安装：")
            + "、".join(existing),
            status=409,
            code="exists",
        )

    installed = _installed_plugin_ids()
    package = set(ids)
    for info in (item for _, item in staged):
        missing = [
            item for item in info.get("requires") or []
            if item not in package and item not in installed
        ]
        if missing:
            raise PluginInstallError(
                f"{info['id']} 依赖的插件尚未安装：" + "、".join(missing)
                + "。请安装完整套件，或先单独安装依赖插件",
                code="missing_dependency",
            )


def _commit_plugins(
    target_root: Path, staged: list[tuple[Path, dict[str, Any]]], replace: bool
) -> None:
    """整包落地：先备份旧目录，任何一个失败就按备份回滚，绝不留半套。"""
    backups: list[tuple[Path, Path]] = []
    placed: list[Path] = []
    try:
        for root, info in staged:
            destination = target_root / info["id"]
            if destination.exists():
                if destination.is_symlink() or not destination.is_dir():
                    raise PluginInstallError(f"plugins/{info['id']} 不是目录，拒绝覆盖")
                if not replace:
                    raise PluginInstallError(f"插件 {info['id']} 已安装。",
                                             status=409, code="exists")
                backup = target_root / f".{info['id']}.backup-{uuid.uuid4().hex}"
                destination.rename(backup)
                backups.append((backup, destination))
            shutil.move(str(root), str(destination))
            placed.append(destination)
    except BaseException:
        for destination in reversed(placed):
            shutil.rmtree(destination, ignore_errors=True)
        for backup, destination in reversed(backups):
            if backup.exists() and not destination.exists():
                backup.rename(destination)
        raise
    for backup, _ in backups:
        shutil.rmtree(backup, ignore_errors=True)


def install_plugin_from_zip(data: bytes, replace: bool = False) -> dict[str, Any]:
    """校验并安装一个插件或套件，返回全部落地插件的发现接口同款信息。

    返回 ``{"plugins": [...], "plugin": 第一个, "suite": 套件元信息或 None}``；
    ``plugin`` 保留给单插件调用方，套件安装请读 ``plugins``。

    Raises:
        PluginInstallError: 任何一步不合格；``status`` 为建议的 HTTP 状态码。
    """
    target_root = plugins_dir()
    target_root.mkdir(parents=True, exist_ok=True)

    with staged_plugins_from_zip(data) as (staged, suite):
        _precheck_install(target_root, staged, replace)
        _commit_plugins(target_root, staged, replace)
        infos = [info for _, info in staged]

    return {"plugins": infos, "plugin": infos[0], "suite": suite}

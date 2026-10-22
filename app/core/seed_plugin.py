"""种子插件的首次运行静默安装（2026-10-24 军令任务 2）。

只安装随包自带的 ``examples/demo_plugin.zip``，不触网、不拉远程源
（AGENTS §2：唯一出网口子仍是用户亲手粘贴的插件索引）。触发条件双重保守：

1. ``plugins/org.jiuzhang.demo-bank`` 尚不存在；
2. 根 data 目录里没有安装标记 ``.seed-demo-bank.installed``。

用户亲手删掉示例题库后不会被强行装回（标记还在）；标记只写一次，
失败也不阻断启动——底座必须能在插件缺席时照常工作。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import root_data_dir, settings

SEED_PLUGIN_ID = "org.jiuzhang.demo-bank"
SEED_ZIP_RELPATH = Path("examples") / "demo_plugin.zip"
MARKER_FILENAME = ".seed-demo-bank.installed"


def seed_plugin_installed() -> bool:
    return (Path(settings.plugins_dir) / SEED_PLUGIN_ID / "plugin.json").is_file()


def ensure_seed_plugin() -> bool:
    """首次运行且缺种子插件时静默安装。返回本次是否真的安装了。"""
    if seed_plugin_installed():
        return False

    marker = root_data_dir() / MARKER_FILENAME
    if marker.exists():
        return False

    zip_path = settings.project_root / SEED_ZIP_RELPATH
    if not zip_path.is_file():
        return False

    from app.core.plugin_install import PluginInstallError, install_plugin_from_zip

    try:
        install_plugin_from_zip(zip_path.read_bytes())
    except (PluginInstallError, OSError):
        return False

    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
        marker.write_text(f"installed_at={now}\n", encoding="utf-8")
    except OSError:
        pass
    return True

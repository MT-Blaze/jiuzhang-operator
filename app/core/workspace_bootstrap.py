"""工作区布局自举（军令 #34：插件全局化）。

启动时按顺序做三件事，全部幂等：

1. 从 ``data/current_workspace`` 指针装载当前工作区（缺失/损坏回落 default）；
2. 保证 default 与当前工作区都有 ``banks/`` 与一份空 ``plugin_state.toml``
   （新工作区结构生成也走这里）——**绝不创建 ``plugins/``**，插件代码只认
   全局 ``plugins_dir()``；
3. 把当前工作区的 ``.env`` 载入 ``os.environ``（覆盖旧值），实现「切库重启后
   加载该区自己的凭据」。

旧根 ``plugins/`` 不再迁入工作区：它现在就是全局插件目录，原地生效。
开发工作树把插件源码放在兄弟仓库 ``../jiuzhang-plugins/src``，同样原地直读。

``JZO_PLUGINS_DIR`` 是测试/探针的显式覆盖：一旦设置，全局插件目录就是它。
"""

from __future__ import annotations

import logging
import os
import shutil
import threading
from pathlib import Path
from typing import Any

from app.core import bank_provider, plugin_state, plugin_update, startup_prefs
from app.core.config import (
    DEFAULT_WORKSPACE_ID,
    PROJECT_ROOT,
    env_file_path,
    load_current_workspace,
    root_data_dir,
    workspace_storage_dir,
    write_current_workspace_pointer,
)
from app.core.workspace_paths import read_current_workspace_pointer

logger = logging.getLogger("jzo.workspace")

LEGACY_ENV_FILE = PROJECT_ROOT / ".env"
BANKS_DIRNAME = "banks"

_lock = threading.Lock()


def _is_dev_checkout() -> bool:
    """仓库根存在 ``.git``：开发树的旧状态文件只复制，不破坏工作树。"""
    return (PROJECT_ROOT / ".git").exists()


def _isolated_run() -> bool:
    """测试/探针显式指定数据或插件目录：不得把真实主机数据与凭据搬进临时区。"""
    return bool(
        os.environ.get("JZO_DATA_DIR", "").strip()
        or os.environ.get("JZO_PLUGINS_DIR", "").strip()
    )


def _transfer(source: Path, target: Path) -> str:
    """把 source 搬到 target；开发工作树只复制，发行包移动。返回 "copy"/"move"。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    if _is_dev_checkout():
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
        return "copy"
    shutil.move(str(source), str(target))
    return "move"


def _known_state_files() -> list[tuple[Path, Path]]:
    """旧根 data/ 下的宿主状态 → default 工作区（不含题库与图片）。"""
    data = root_data_dir()
    target = workspace_storage_dir(DEFAULT_WORKSPACE_ID)
    return [
        (data / plugin_state.STATE_FILENAME, target / plugin_state.STATE_FILENAME),
        (data / startup_prefs.STATE_FILENAME, target / startup_prefs.STATE_FILENAME),
        (data / bank_provider.STATE_FILENAME, target / bank_provider.STATE_FILENAME),
        (data / plugin_update.PENDING_FILENAME, target / plugin_update.PENDING_FILENAME),
        (LEGACY_ENV_FILE, target / ".env"),
    ]


def _migrate_legacy_state() -> list[str]:
    moved: list[str] = []
    if _isolated_run():
        return moved
    for source, target in _known_state_files():
        if not source.is_file() or target.exists():
            continue
        try:
            _transfer(source, target)
        except OSError as exc:
            logger.warning("旧状态文件迁移失败（保留原文件）：%s → %s（%s）",
                           source, target, exc)
            continue
        moved.append(source.name)
        logger.info("旧全局状态已迁入 default 工作区：%s", source.name)
    return moved


def ensure_workspace_layout(workspace_id: str) -> Path:
    """保证工作区有 banks/ 与空 plugin_state.toml；返回工作区目录。

    插件代码是全局的一份，这里**不建 plugins/ 目录**——数据与代码彻底分家。
    """
    root = workspace_storage_dir(workspace_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / BANKS_DIRNAME).mkdir(parents=True, exist_ok=True)
    state = root / plugin_state.STATE_FILENAME
    if not state.exists():
        state.write_text("", encoding="utf-8")
    return root


def load_env_file(path: Path, *, override: bool = False) -> dict[str, str]:
    """把 .env 键值载入 os.environ；返回实际载入的键（值绝不回传/记日志）。

    默认 ``setdefault``：命令行/父进程显式给的环境变量永远优先，
    绝不让一个旧文件把测试令牌或部署参数覆盖掉。
    """
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    loaded: dict[str, str] = {}
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if override or key not in os.environ:
            os.environ[key] = value
        loaded[key] = value
    return loaded


def bootstrap() -> dict[str, Any]:
    """启动自举：装载指针、迁移旧宿主状态、生成工作区结构、载入凭据。"""
    with _lock:
        workspace_id = load_current_workspace()

        moved_state = _migrate_legacy_state()

        ensure_workspace_layout(DEFAULT_WORKSPACE_ID)
        ensure_workspace_layout(workspace_id)

        if not read_current_workspace_pointer():
            write_current_workspace_pointer(workspace_id)

        env_path = env_file_path()
        loaded_keys = load_env_file(env_path) if env_path.is_file() else {}

        return {
            "workspace_id": workspace_id,
            "state_moved": moved_state,
            "env_loaded": sorted(loaded_keys),
        }

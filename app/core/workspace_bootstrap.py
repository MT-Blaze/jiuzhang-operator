"""工作区布局自举与旧全局数据迁移（军令 #18 第三步）。

启动时按顺序做四件事，全部幂等：

1. 从 ``data/current_workspace`` 指针装载当前工作区（缺失/损坏回落 default）；
2. 把旧版本的全局插件与宿主状态**移动**进 default 工作区：根 ``plugins/``、
   ``data/plugin_state.json``、``data/startup.json``、``data/bank_provider.json``、
   ``data/update_state.json``、根 ``.env``（凭据）；
3. 保证 default 与当前工作区都有 ``plugins/`` 子目录和一份空
   ``plugin_state.json``（新工作区结构生成也走这里）；
4. 把当前工作区的 ``.env`` 载入 ``os.environ``（覆盖旧值），实现「切库重启后
   加载该区自己的凭据」。

**开发工作树的例外**：仓库根存在 ``.git`` 时，根 ``plugins/`` 是受 git 跟踪的
源码与发行包原料，移动/删除它会把工作树打烂。此时只**复制一次**到 default
工作区（目标已存在则不再覆盖），根目录原样保留；``.env`` 同样只复制。
发行包（无 ``.git``）仍严格按军令移动并在移走后删除根插件文件夹。

``JZO_PLUGINS_DIR`` 是测试/探针的显式覆盖：一旦设置，跳过插件迁移，绝不把
仓库里的插件搬进临时数据目录。
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
LEGACY_PLUGINS_DIR = PROJECT_ROOT / "plugins"
PLUGINS_DIRNAME = "plugins"

_lock = threading.Lock()


def _is_dev_checkout() -> bool:
    """仓库根存在 ``.git``：根 plugins/ 是源码，禁止移走/删除。"""
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


def _migrate_legacy_plugins(target: Path) -> str:
    """旧根 plugins/ → default 工作区。返回实际动作（空串表示没迁）。"""
    if _isolated_run():
        return ""
    legacy = LEGACY_PLUGINS_DIR
    if not legacy.is_dir() or legacy.resolve() == target.resolve():
        return ""
    if target.exists():
        # 目标已有插件（上一次迁移或用户安装过）：只补缺失的目录，绝不覆盖。
        copied = 0
        for child in sorted(legacy.iterdir(), key=lambda item: item.name):
            if child.name.startswith(".") or (target / child.name).exists():
                continue
            _transfer(child, target / child.name)
            copied += 1
        return "merge:%d" % copied if copied else ""
    action = _transfer(legacy, target)
    logger.info("旧全局插件目录已%s到 default 工作区：%s", "复制" if action == "copy" else "移动", target)
    return action


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
    """保证工作区有 plugins/ 与空 plugin_state.json；返回工作区目录。"""
    root = workspace_storage_dir(workspace_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / PLUGINS_DIRNAME).mkdir(parents=True, exist_ok=True)
    state = root / plugin_state.STATE_FILENAME
    if not state.exists():
        state.write_text("{}\n", encoding="utf-8")
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
    """启动自举：装载指针、迁移旧数据、生成结构、载入凭据。"""
    with _lock:
        workspace_id = load_current_workspace()
        default_root = workspace_storage_dir(DEFAULT_WORKSPACE_ID)
        default_root.mkdir(parents=True, exist_ok=True)

        plugins_action = _migrate_legacy_plugins(default_root / PLUGINS_DIRNAME)
        moved_state = _migrate_legacy_state()

        ensure_workspace_layout(DEFAULT_WORKSPACE_ID)
        ensure_workspace_layout(workspace_id)

        if not read_current_workspace_pointer():
            write_current_workspace_pointer(workspace_id)

        env_path = env_file_path()
        loaded_keys = load_env_file(env_path) if env_path.is_file() else {}

        return {
            "workspace_id": workspace_id,
            "plugins_migration": plugins_action,
            "state_moved": moved_state,
            "env_loaded": sorted(loaded_keys),
        }

"""全局配置。所有路径以仓库根目录为锚点，不依赖当前工作目录。

支持多工作区（Workspace）隔离：每个工作区拥有独立的数据库、上传资源、配置
与插件启停状态。**插件代码是全局的一份**（军令 #34）：默认读底座根
``plugins/``，开发工作树没有根插件目录时直读兄弟仓库
``../jiuzhang-plugins/src``，因此改源码刷新浏览器即生效，不再往工作区复制运行副本。
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core.workspace_paths import (
    CURRENT_WORKSPACE_FILENAME,
    DATABASE_FILENAME,
    DEFAULT_WORKSPACE_ID,
    PROJECT_ROOT,
    WORKSPACE_ID_RE,
    current_workspace_pointer_path,
    env_file_path_for,
    read_current_workspace_pointer,
    root_data_dir,
    valid_workspace_id,
    workspace_data_dir,
    workspace_storage_dir,
    write_current_workspace_pointer,
)

__all__ = [
    "CURRENT_WORKSPACE_FILENAME",
    "DATABASE_FILENAME",
    "DEFAULT_WORKSPACE_ID",
    "PROJECT_ROOT",
    "WORKSPACE_ID_RE",
    "Settings",
    "current_workspace_id",
    "current_workspace_pointer_path",
    "default_database_path",
    "env_file_path",
    "load_current_workspace",
    "plugin_source_root",
    "plugins_dir",
    "root_data_dir",
    "settings",
    "switch_workspace",
    "workspace_data_dir",
    "workspace_storage_dir",
]


def default_database_path() -> Path:
    """default 工作区的数据库路径（历史布局：根 data 目录）。"""
    return root_data_dir() / DATABASE_FILENAME


class Settings:
    project_root: Path = PROJECT_ROOT
    static_dir: Path = PROJECT_ROOT / "static"
    docs_dir: Path = PROJECT_ROOT / "docs"

    # 当前工作区 id；None 表示 default。它是指针文件在本进程里的镜像：
    # 启动时由 load_current_workspace() 装载，切库时由 switch_workspace() 同步写回。
    workspace_id: str | None = None

    @property
    def data_dir(self) -> Path:
        """当前工作区的业务数据根（default 是根 data，其余是工作区目录）。"""
        return workspace_data_dir(self.workspace_id or DEFAULT_WORKSPACE_ID)

    @property
    def database_path(self) -> Path:
        return self.data_dir / DATABASE_FILENAME

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def pending_db_path(self) -> Path:
        """中转站（待审核池）的独立库文件：与主库不是一个文件。"""
        return self.data_dir / "pending.db"

    @property
    def pending_assets_dir(self) -> Path:
        """中转站的配图目录：入库前配图只落在这里，不进 uploads/。"""
        return self.data_dir / "pending_assets"

    @property
    def pool_assets_dir(self) -> Path:
        """重题池的成品图目录：抽走时从 pending_assets/ 复制过来，自成一户。

        与 ``pending_assets/`` 分开是判据 4.2/4.7 的落点：批次审完物理清残留切图
        清不到这里，池内条目删图也删不到批次那里。
        """
        return self.data_dir / "pool_assets"

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.toml"

    host: str = os.environ.get("JZO_HOST", "127.0.0.1")
    # 专属端口 65496：避免与本机其他开发服务（8000 段）抢口，一个项目只认一个口。
    port: int = int(os.environ.get("JZO_PORT", "65496"))


settings = Settings()


def current_workspace_id() -> str:
    """当前工作区 id（永不为空）；None 即 default。"""
    return settings.workspace_id or DEFAULT_WORKSPACE_ID


def plugins_dir() -> Path:
    """全局插件代码目录（与当前工作区无关），每次调用重新求值。

    解析顺序：

    1. ``JZO_PLUGINS_DIR`` 显式覆盖（测试与便携部署）；
    2. 底座根 ``plugins/``（旧版单文件夹安装的兼容位置）；
    3. 兄弟仓库 ``../jiuzhang-plugins/src``（开发树与新版双文件夹安装，改源码刷新即生效）；
    4. 仍无则回到底座根 ``plugins/``（安装时由调用方创建）。

    顺序的意义：装了发行包的用户只认包内插件；开发机没有根插件目录时直接读源码，
    两边都不会在 ``data/workspaces/`` 下留运行副本。
    """
    override = os.environ.get("JZO_PLUGINS_DIR", "").strip()
    if override:
        return Path(override)
    bundled = PROJECT_ROOT / "plugins"
    if bundled.is_dir():
        return bundled
    source = plugin_source_root()
    return source if source is not None else bundled


def plugin_source_root() -> Path | None:
    """插件源码根：底座仓库不再存放插件源码，只在开发/发版时跨目录取。

    解析顺序：``JZO_PLUGIN_SOURCE_DIR`` 显式覆盖 → 底座根 ``plugins/``
    （旧版单文件夹安装兼容）→ 同级 ``../jiuzhang-plugins/src``（开发树与
    install.bat 双文件夹布局）。都不在时返回 ``None``，调用方回落到
    :func:`plugins_dir`。
    """
    override = os.environ.get("JZO_PLUGIN_SOURCE_DIR", "").strip()
    if override:
        return Path(override)
    bundled = PROJECT_ROOT / "plugins"
    if bundled.is_dir():
        return bundled
    sibling = PROJECT_ROOT.parent / "jiuzhang-plugins" / "src"
    if sibling.is_dir():
        return sibling
    return None


def env_file_path() -> Path:
    """当前工作区的凭据文件；``JZO_ENV_FILE`` 可整体覆盖（测试/启动器专用）。"""
    override = os.environ.get("JZO_ENV_FILE", "").strip()
    if override:
        return Path(override)
    return env_file_path_for(current_workspace_id())


def load_current_workspace() -> str:
    """从指针装载当前工作区；指针缺失/损坏回落 default。返回解析后的 id。"""
    workspace_id = read_current_workspace_pointer() or DEFAULT_WORKSPACE_ID
    settings.workspace_id = None if workspace_id == DEFAULT_WORKSPACE_ID else workspace_id
    return workspace_id


def switch_workspace(workspace_id: str | None) -> None:
    """切到指定工作区：先原子写指针，再更新进程内镜像。

    指针写失败时内存不变——绝不出现「界面已切、重启后却回旧区」的分裂。
    """
    resolved = workspace_id or DEFAULT_WORKSPACE_ID
    if not valid_workspace_id(resolved):
        raise ValueError("工作区 ID 非法")
    write_current_workspace_pointer(resolved)
    settings.workspace_id = None if resolved == DEFAULT_WORKSPACE_ID else resolved

"""插件卸载：删代码目录；可选地连本地数据一起物理销毁。

两种口径（军令 v0.8.0 任务 2.2、#18-续4 修订）：
- 保留数据：只删 ``plugins/<id>/`` 代码目录；当前工作区的物理 ``.db`` 原样留下，
  以后重装同名插件即恢复取数。
- 彻底删除：代码目录 + **当前工作区**里该插件的物理库（含 WAL/SHM/journal 边车）
  一并销毁，不可恢复——所以前端务必二次确认并给红色警告。

**题库引擎免死金牌**（军令 #18-结 任务三、#20 加固两级）：
- 第一级：清单声明 ``uninstallable: false``（官方引擎）——后端在任何删除动作之前
  直接回 409，连代码目录都不动；
- 第二级：声明了 ``capabilities: ["bank.provider"]`` 的第三方题库，后端**无视**
  ``keep_data`` 一律保数据，回包带 ``provider_guarded`` 供前端如实回显。
理由：换渲染引擎可以，把老师历年攒下的真题库连锅端不行；provider 的
``banks/<id>.db`` 恰恰就是真题本体。前端对第一级把卸载按钮换成「受保护」标签，
对第二级把「不保留数据」置灰。

**绝不跨工作区**（军令 #18-续4）：其他工作区的 ``.db`` 是老师各自的财产，卸载当前区
的插件不能连坐。``uploads/`` 是工作区级扁平命名空间，文件不带插件标记，无法可靠归属，
因此这里一律不删（宁可多留，不可误毁老师的图）——军令 #18-终 阶段一 把这条口径钉成契约：
底座没有资产表也没有引用计数，「图片彻底无引用」判不出来，孤儿清理一律不做
（与 PROJECT_MEMORY 的历史决策一致）。

插件私有数据的物理位置只有当前工作区的 ``banks/<plugin_id>.db`` 一处，删它即彻底清理；
题目行里的 ``extensions.<反向域名>`` 属于老师的题库本体，卸载**不得**顺手改写（PLUGIN_SPEC §3）。
该区 ``plugin_state.json`` / ``startup.json`` / ``bank_provider.json`` 里的残留键由读取侧
按「未安装即忽略」兜底（见 plugins.prune_sidebar 与各 state 模块的校验），卸载不写这些文件。

安全：插件 id 必须先过格式校验；只在本底座 plugins_dir 与当前工作区 data_dir 之内操作，
绝不接受外部路径；被删路径必须落在对应根目录内（防穿越）。
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from app.core.bank_provider import PROVIDER_CAPABILITY
from app.core.config import plugins_dir, settings

_PLUGIN_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,80}$")
_DB_SIDECAR_SUFFIXES = (".db-shm", ".db-wal", ".db-journal")


class PluginUninstallError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def _validate_id(plugin_id: str) -> str:
    if not isinstance(plugin_id, str) or not _PLUGIN_ID.fullmatch(plugin_id):
        raise PluginUninstallError("插件 ID 非法")
    return plugin_id


def _is_within(child: Path, root: Path) -> bool:
    try:
        child.relative_to(root)
        return True
    except ValueError:
        return False


def _db_family(bank_file: Path) -> list[Path]:
    """给定 a.db，收集它和它的边车兄弟（a.db-shm / -wal / -journal）。"""
    paths = [bank_file]
    for suffix in _DB_SIDECAR_SUFFIXES:
        paths.append(bank_file.with_name(bank_file.name.replace(".db", suffix)))
    return paths


def _current_workspace_bank(plugin_id: str) -> Path:
    """当前工作区里该插件的物理题库路径；其他工作区一概不碰。"""
    return Path(settings.data_dir) / "banks" / f"{plugin_id}.db"


def _read_manifest(plugin_dir: Path) -> dict[str, Any]:
    """删代码之前读一眼清单；读坏一律当空清单，后面的判词按保守方向走。"""
    try:
        manifest = json.loads((plugin_dir / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return manifest if isinstance(manifest, dict) else {}


def _declares_provider(manifest: dict[str, Any]) -> bool:
    """声明了 ``bank.provider`` 的插件，本区物理库就是老师的真题本体。

    清单读坏或缺字段一律按「不是 provider」处理——保守方向是照常允许彻底卸载，
    因为误判成 provider 只是多留一份库，误判成非 provider 才会毁数据，所以这里
    只在**明文看到**能力标记时才授权销毁。
    """
    capabilities = manifest.get("capabilities")
    return isinstance(capabilities, list) and PROVIDER_CAPABILITY in capabilities


def uninstall_plugin(plugin_id: str, *, keep_data: bool) -> dict[str, Any]:
    _validate_id(plugin_id)
    plugins_root = plugins_dir().resolve()
    plugin_dir = (plugins_root / plugin_id).resolve()
    if not _is_within(plugin_dir, plugins_root) or plugin_dir == plugins_root:
        raise PluginUninstallError("插件路径越界")

    manifest = _read_manifest(plugin_dir)
    # 军令 #20：题库引擎整包受保护——它不是可换的皮，卸载连代码目录都不删；
    # 前端据实把按钮置灰，后端仍要挡一次（前端隐藏按钮不是安全边界）。
    if manifest.get("uninstallable") is False:
        raise PluginUninstallError(
            f"「{plugin_dir.name}」是题库引擎，受保护不可卸载；如需停用请在插件控制台停用。",
            status=409,
        )
    # 第二级免死金牌（第三方 provider 没有 uninstallable 时的兜底）：前端传什么
    # keep_data 都不算，provider 插件的物理库一律原地保留——换引擎可以，毁真题不行。
    provider_guarded = _declares_provider(manifest)
    keep_data = keep_data or provider_guarded

    removed_code = False
    if plugin_dir.is_dir():
        shutil.rmtree(plugin_dir)
        removed_code = True
    else:
        raise PluginUninstallError(f"插件不存在：{plugin_id}", status=404)

    removed_data: list[str] = []
    if not keep_data:
        data_root = Path(settings.data_dir).resolve()
        for path in _db_family(_current_workspace_bank(plugin_id)):
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if not _is_within(resolved, data_root):
                continue
            if resolved.is_file():
                try:
                    resolved.unlink()
                    removed_data.append(str(resolved.relative_to(data_root)))
                except OSError:
                    pass

    return {
        "id": plugin_id,
        "uninstalled": True,
        "keep_data": keep_data,
        "removed_code": removed_code,
        "removed_data": removed_data,
        # provider 免死金牌：True 表示这轮即便前端要求销毁数据也照样保留，前端据此如实回显
        "provider_guarded": provider_guarded,
        # 共享配图目录：无论是否彻底卸载都不碰（归属判不出，误删即毁老师的图）
        "uploads_kept": True,
    }

"""配置归插件卡的隔离夹具：最小目录提供者插件＋真实 catalog.toml。

底座按「声明了 models.catalog 的启用插件」找目录提供者（同 bank.provider
路由口径），所以夹具不必搬整个录题插件：造一个只声明能力的最小 headless
插件，catalog.toml 从插件源码仓原样拷来。JZO_PLUGINS_DIR / JZO_DATA_DIR
都进临时区，绝不碰本机 plugins/ 与 data/（同 test_bank_provider._Isolated）。

运行：随各测试模块 ``.venv/Scripts/python.exe -m unittest tests.<模块>``。
"""

from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from app.core import toml_io
from app.core.config import plugin_source_root

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
EDITOR = "org.jiuzhang.editor"
CATALOG_CAPABILITY = "models.catalog"


def write_catalog_plugin(plugins_dir: Path, plugin_id: str = EDITOR,
                         catalog_source: Path | None = None,
                         capabilities: list[str] | None = None) -> Path:
    """造一个最小目录提供者插件：清单＋LICENSE＋catalog.toml（可选自定义目录）。"""
    plugin = plugins_dir / plugin_id
    plugin.mkdir(parents=True, exist_ok=True)
    toml_io.write(plugin / "plugin.toml", {
        "schema_version": "1.0",
        "id": plugin_id,
        "name": "目录提供者夹具",
        "version": "1.0.0",
        "api_version": "1.0",
        "kind": "tool",
        "description": "测试夹具：只声明 models.catalog 的最小 headless 插件，不带界面。",
        "author": "tests",
        "license": "Apache-2.0",
        "headless": True,
        "show_in_sidebar": False,
        "slots": [],
        "capabilities": capabilities if capabilities is not None else [CATALOG_CAPABILITY],
        "permissions": ["questions:write"],
    })
    (plugin / "LICENSE").write_text("Apache-2.0（测试夹具占位，非发行包）\n",
                                    encoding="utf-8")
    source = catalog_source or (PLUGIN_SOURCE_DIR / EDITOR / "catalog.toml")
    shutil.copyfile(source, plugin / "catalog.toml")
    return plugin


class CatalogIsolated(unittest.TestCase):
    """临时 plugins/＋data/，装好声明 models.catalog 的夹具插件与真实目录。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.plugins_dir = base / "plugins"
        self.plugins_dir.mkdir()
        self.data_dir = base / "data"
        self._saved = (os.environ.get("JZO_PLUGINS_DIR"),
                       os.environ.get("JZO_DATA_DIR"))
        os.environ["JZO_PLUGINS_DIR"] = str(self.plugins_dir)
        os.environ["JZO_DATA_DIR"] = str(self.data_dir)
        self.addCleanup(self._restore)
        self.plugin = write_catalog_plugin(self.plugins_dir)

    def _restore(self) -> None:
        plugins, data = self._saved
        for key, value in (("JZO_PLUGINS_DIR", plugins), ("JZO_DATA_DIR", data)):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
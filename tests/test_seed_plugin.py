"""种子题库插件与默认路由契约（2026-10-24 军令任务 1/2）。

覆盖三件事：
1. ``/`` 直达工作台、``/about`` 保留底座介绍页、边栏有 About 链接；
2. ``ensure_seed_plugin`` 首启静默安装 examples/demo_plugin.zip，标记防重装；
3. demo_plugin.zip 本体通过插件安装器的全套契约校验，且含 5 道合规题目。

运行：``.venv/Scripts/python.exe -m unittest tests.test_seed_plugin``
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from app import __version__  # noqa: F401  确保包可导入
from app.core.config import settings
from app.core.seed_plugin import MARKER_FILENAME, SEED_PLUGIN_ID, ensure_seed_plugin

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
DEMO_ZIP = ROOT / "examples" / "demo_plugin.zip"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class DefaultRouteTest(unittest.TestCase):
    """/ 直达工作台；/about 挂底座介绍页；/workspace 保留。"""

    def setUp(self) -> None:
        from app.main import app

        self.endpoints = {
            getattr(route, "path", None): getattr(route, "endpoint", None)
            for route in app.routes
        }

    def _served_file(self, path: str) -> Path:
        endpoint = self.endpoints.get(path)
        self.assertIsNotNone(endpoint, f"缺少路由 {path}")
        response = asyncio.run(endpoint())
        return Path(response.path)

    def test_01_root_serves_workspace(self) -> None:
        self.assertEqual(self._served_file("/"), STATIC / "workspace.html")

    def test_02_about_serves_intro_page(self) -> None:
        self.assertEqual(self._served_file("/about"), STATIC / "index.html")

    def test_03_workspace_route_kept(self) -> None:
        self.assertEqual(self._served_file("/workspace"), STATIC / "workspace.html")

    def test_04_sidebar_has_about_link_at_bottom(self) -> None:
        text = _read(STATIC / "workspace.html")
        self.assertIn('href="/about"', text)
        self.assertIn("关于底座（About）", text)
        # 不许再留一个指回 / 的「底座首页」链接（/ 现在就是工作台自己）
        self.assertNotIn(">底座首页</a>", text)

    def test_05_welcome_hint_wired_in_workspace_js(self) -> None:
        text = _read(STATIC / "js" / "workspace.js")
        self.assertIn("系统已为您预置了 5 道示例数学题", text)
        self.assertIn("拆分第一题", text)
        self.assertIn(SEED_PLUGIN_ID, text)


class SeedPluginInstallTest(unittest.TestCase):
    """首启静默安装：装一次、留标记、删了不硬塞回去。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.plugins_dir = Path(self.tmp.name) / "plugins"
        self.data_dir = Path(self.tmp.name) / "data"
        self._saved_plugins_dir = settings.plugins_dir
        self._saved_data_dir = os.environ.get("JZO_DATA_DIR")
        settings.plugins_dir = self.plugins_dir
        os.environ["JZO_DATA_DIR"] = self.data_dir.as_posix()

    def tearDown(self) -> None:
        settings.plugins_dir = self._saved_plugins_dir
        if self._saved_data_dir is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = self._saved_data_dir
        self.tmp.cleanup()

    def test_01_first_run_installs_seed_plugin(self) -> None:
        self.assertTrue(DEMO_ZIP.is_file(), "examples/demo_plugin.zip 不存在，先跑构建脚本")
        self.assertTrue(ensure_seed_plugin())
        manifest = self.plugins_dir / SEED_PLUGIN_ID / "plugin.json"
        self.assertTrue(manifest.is_file())
        self.assertTrue((self.plugins_dir / SEED_PLUGIN_ID / "dist" / "plugin.js").is_file())
        self.assertTrue((self.data_dir / MARKER_FILENAME).is_file())

    def test_02_second_run_is_noop(self) -> None:
        ensure_seed_plugin()
        self.assertFalse(ensure_seed_plugin())

    def test_03_user_removal_is_respected(self) -> None:
        ensure_seed_plugin()
        import shutil

        shutil.rmtree(self.plugins_dir / SEED_PLUGIN_ID)
        self.assertFalse(ensure_seed_plugin(), "标记还在，用户删掉的插件不许装回")


class DemoZipContractTest(unittest.TestCase):
    """demo_plugin.zip 本体：结构、清单与 5 道合规题目。"""

    def setUp(self) -> None:
        self.zf = zipfile.ZipFile(io.BytesIO(DEMO_ZIP.read_bytes()))
        self.names = self.zf.namelist()

    def tearDown(self) -> None:
        self.zf.close()

    def _member(self, relative: str) -> bytes:
        return self.zf.read(f"{SEED_PLUGIN_ID}/{relative}")

    def test_01_single_top_level_dir_named_by_id(self) -> None:
        tops = {name.split("/", 1)[0] for name in self.names}
        self.assertEqual(tops, {SEED_PLUGIN_ID})

    def test_02_required_members_present(self) -> None:
        for relative in ("plugin.json", "LICENSE", "dist/index.html", "dist/plugin.js",
                         "seed/questions.json"):
            self.assertIn(f"{SEED_PLUGIN_ID}/{relative}", self.names)

    def test_03_manifest_matches_contract(self) -> None:
        manifest = json.loads(self._member("plugin.json"))
        self.assertEqual(manifest["id"], SEED_PLUGIN_ID)
        self.assertEqual(manifest["license"], "Apache-2.0")
        self.assertEqual(manifest["api_version"], "1.0")
        self.assertNotIn("backend", manifest)

    def test_04_five_questions_pass_schema(self) -> None:
        from jsonschema import Draft202012Validator

        schema = json.loads(_read(ROOT / "schemas" / "question.json"))
        validator = Draft202012Validator(schema)
        questions = json.loads(self._member("seed/questions.json"))
        self.assertEqual(len(questions), 5)
        for question in questions:
            errors = list(validator.iter_errors(question))
            self.assertEqual(errors, [], f"题目 {question.get('id')} 不合规：{errors}")

    def test_05_plugin_js_has_questions_inlined(self) -> None:
        script = self._member("dist/plugin.js").decode("utf-8")
        self.assertNotIn("/*__SEED_QUESTIONS__*/[]", script, "构建时未内联题目数据")
        self.assertIn("q_demo_bank_0001", script)
        self.assertNotIn("</script", script.lower(), "内联数据不得提前闭合 script")


if __name__ == "__main__":
    unittest.main()

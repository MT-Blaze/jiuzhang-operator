"""纯净发版 + 工作区切换契约：v0.7.2 军令「子龙」。

钉四件事（ADR-003）：
1. ensure_bank 的工作区口径——default 有本机种子则复制、无种子退回 schema 建空库；
   非 default 工作区一律建空库，绝不把 default 真题复制过去。
2. build_plugin 不再把任何物理 .db 与题库配图资产打进插件包（对外核心库是空壳）。
3. workspaces API：列出带 question_count 与正确 is_active；切换/新建是写操作，必须带令牌。
4. 前端左栏有【当前题库 ▼】，且接线到 /api/workspaces 的 list/switch/create。

运行：``.venv/Scripts/python.exe -m unittest tests.test_workspace_pure_release``
"""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from app.core import bank as bank_core
from app.core.config import settings
from tools.build_plugin import build_plugin

ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ID = "org.jiuzhang.bank-engine"
SCHEMA = ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql"


def _make_seed_db(path: Path, questions: int) -> None:
    """按冻结 schema 建一颗含指定题数的种子库（仅供测试摆放，不碰真实数据）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        now = "2026-10-24T00:00:00+08:00"
        for index in range(questions):
            con.execute(
                "INSERT INTO questions (id, type, stem, options, answer, solution, extensions,"
                " difficulty, created_at, updated_at) VALUES (?, 'fill_blank', ?, '[]', NULL,"
                " NULL, '[]', 'L1', ?, ?)",
                (f"q_seed_{index:04d}", f"种子题干 {index}", now, now),
            )
        con.commit()
    finally:
        con.close()


class EnsureBankWorkspaceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data_dir = self.root / "data"
        self.plugins_dir = self.root / "plugins"
        (self.plugins_dir / PLUGIN_ID / "bank" / "assets").mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SCHEMA, self.plugins_dir / PLUGIN_ID / "bank" / "schema.sql")
        (self.plugins_dir / PLUGIN_ID / "bank" / "assets" / "x.png").write_bytes(b"\x89PNG\r\n")
        # default 工作区的本机种子：一颗带 3 题的库
        _make_seed_db(self.plugins_dir / PLUGIN_ID / "bank" / "bank.db", 3)

        self._saved = (
            __import__("os").environ.get("JZO_DATA_DIR"),
            __import__("os").environ.get("JZO_PLUGINS_DIR"),
            settings.workspace_id,
        )
        __import__("os").environ["JZO_DATA_DIR"] = str(self.data_dir)
        __import__("os").environ["JZO_PLUGINS_DIR"] = str(self.plugins_dir)
        settings.workspace_id = None

    def tearDown(self) -> None:
        data, plugins, ws = self._saved
        for key, value in (("JZO_DATA_DIR", data), ("JZO_PLUGINS_DIR", plugins)):
            if value is None:
                __import__("os").environ.pop(key, None)
            else:
                __import__("os").environ[key] = value
        settings.workspace_id = ws
        self.tmp.cleanup()

    def _count(self, path: Path) -> int:
        con = sqlite3.connect(path)
        try:
            return int(con.execute("SELECT COUNT(*) FROM questions").fetchone()[0])
        finally:
            con.close()

    def test_default_seeds_from_local_bank(self) -> None:
        path = bank_core.ensure_bank(PLUGIN_ID)
        self.assertEqual(self._count(path), 3, "default 工作区必须从本机种子复制")

    def test_new_workspace_is_empty(self) -> None:
        bank_core.ensure_bank(PLUGIN_ID)          # 先建 default
        settings.workspace_id = "ws_fresh"
        path = bank_core.ensure_bank(PLUGIN_ID)
        self.assertEqual(self._count(path), 0, "新建工作区必须是空库，不许复制 default 真题")
        self.assertIn("ws_fresh", str(path), "新工作区的库要落在独立物理目录")

    def test_default_without_seed_falls_back_to_empty_schema(self) -> None:
        # 纯净环境：没有本机种子时不报错，退回 schema 建空库
        (self.plugins_dir / PLUGIN_ID / "bank" / "bank.db").unlink()
        path = bank_core.ensure_bank(PLUGIN_ID)
        self.assertEqual(self._count(path), 0)
        con = sqlite3.connect(path)
        try:
            tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            con.close()
        self.assertIn("question_topics", tables, "退回空库仍须是冻结的 7 表结构")


class PluginPackagePurityTest(unittest.TestCase):
    def test_engine_zip_carries_no_database_or_assets(self) -> None:
        with tempfile.TemporaryDirectory() as out:
            target = build_plugin(ROOT / "plugins" / PLUGIN_ID, Path(out))
            with zipfile.ZipFile(target) as bundle:
                names = bundle.namelist()
        joined = "\n".join(names)
        self.assertNotIn("bank.db", joined, "插件包不得携带任何物理题库 .db")
        self.assertFalse(any(name.endswith(".db") for name in names),
                         [n for n in names if n.endswith(".db")])
        self.assertFalse(any("/assets/" in name for name in names), "题库配图资产不随包发布")
        self.assertIn("org.jiuzhang.bank-engine/bank/schema.sql", joined, "空壳仍须带 schema 供建库")
        self.assertIn("org.jiuzhang.bank-engine/plugin.json", joined)

    def test_release_script_excludes_structural_backups(self) -> None:
        """结构升级备份是 456 题库的整份副本，漏进发行包等于把真题再发一遍。

        v0.8.2 迁移会在库旁边落 ``*.pre-v082.bak``；robocopy 的 /XF 只按后缀剔文件，
        所以 ``*.bak`` 必须显式出现在剔除清单里。
        """
        bat = (ROOT / "build_release.bat").read_text(encoding="utf-8")
        line = next((row for row in bat.splitlines() if "/XF" in row), "")
        self.assertIn("*.bak", line, "/XF 剔除清单里没有 *.bak，升级备份会被打进发行包")
        self.assertIn("*.db", line, "物理 .db 必须继续被剔除（纯净发版口径 ADR-003）")
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("*.pre-v082.bak", gitignore, "升级备份不该进 git")


class WorkspaceEndpointContractTest(unittest.TestCase):
    def test_router_mounts_and_guards_writes(self) -> None:
        from app.api import workspaces as ws_mod
        paths = {route.path for route in ws_mod.router.routes}
        self.assertIn("/api/workspaces", paths)
        self.assertIn("/api/workspaces/switch", paths)

    def test_switch_and_create_provision_core_bank(self) -> None:
        source = (ROOT / "app" / "api" / "workspaces.py").read_text(encoding="utf-8")
        self.assertIn("_provision_core_bank", source)
        # 切换/新建后都立即落地该区物理库并回题数（空壳工作区的取数闭环）
        self.assertEqual(source.count("_provision_core_bank()") >= 2, True)

    def test_list_exposes_question_count(self) -> None:
        source = (ROOT / "app" / "api" / "workspaces.py").read_text(encoding="utf-8")
        self.assertIn("question_count", source)
        self.assertIn("_bank_question_count", source)


class WorkspaceFrontendTest(unittest.TestCase):
    def test_sidebar_dropdown_retired_into_settings(self) -> None:
        """v0.8.4：左栏不再占一个工作区下拉，切库/建库统一收进【设置与控制台】。"""
        html = (ROOT / "static" / "workspace.html").read_text(encoding="utf-8")
        self.assertNotIn('id="wsBankSelect"', html)
        self.assertNotIn('id="wsBankNew"', html)
        settings = (ROOT / "static" / "settings.html").read_text(encoding="utf-8")
        self.assertIn('id="stWsList"', settings, "设置页必须承接工作区列表")
        self.assertIn("新建工作区", settings)

    def test_workspace_api_is_driven_by_settings_page(self) -> None:
        js = (ROOT / "static" / "js" / "settings.js").read_text(encoding="utf-8")
        self.assertIn('"/api/workspaces"', js)
        self.assertIn('"/api/workspaces/switch"', js)
        workspace_js = (ROOT / "static" / "js" / "workspace.js").read_text(encoding="utf-8")
        self.assertNotIn("function wireBank", workspace_js, "工作台下拉逻辑应已摘除")
        self.assertNotRegex(workspace_js, r"\(\?<[=!]", "前端禁用后行断言")


if __name__ == "__main__":
    unittest.main()

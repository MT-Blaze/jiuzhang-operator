"""双轨更新契约（PLUGIN_SPEC §1.7 / ADR-006）：版本比较、兼容拦截、数据必保、续更状态机、update.bat。

运行：``.venv/Scripts/python.exe -m unittest tests.test_plugin_update``
"""

from __future__ import annotations

import io
import json
import os
import tempfile
import threading
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from app.core import plugin_update
from app.core.config import Settings
from app.core.plugin_update import (
    HOST_EXCLUDED_DIRS,
    HOST_EXCLUDED_FILES,
    UpdateRejected,
    apply_plugin_update,
    apply_updates,
    build_update_script,
    check_updates,
    clear_pending,
    compare_versions,
    host_satisfies,
    host_version,
    launch_host_update,
    manifest_min_host,
    parse_version,
    prepare_host_update,
    read_pending,
    resume_pending,
    write_pending,
)

PLUGIN_ID = "org.jiuzhang.update-test"
LICENSE_TEXT = "Apache License 2.0 (fixture)"


def manifest(version: str = "1.0.0", min_host: str | None = None,
             engine_host: str | None = None, plugin_id: str = PLUGIN_ID) -> dict:
    body = {
        "schema_version": "1.0",
        "id": plugin_id,
        "name": "更新契约测试插件",
        "version": version,
        "api_version": "1.0",
        "kind": "renderer",
        "description": "仅用于热更新契约测试的最小渲染插件",
        "license": "Apache-2.0",
        "slots": ["question.card"],
        "capabilities": ["question.render"],
        "permissions": ["questions:read"],
        "entry": {"frontend": "dist/plugin.js"},
    }
    if min_host:
        body["min_host_version"] = min_host
    if engine_host:
        body["engine"] = {"host_version": engine_host}
    return body


def build_zip(version: str = "1.0.0", top_dir: str | None = PLUGIN_ID,
              min_host: str | None = None, engine_host: str | None = None,
              extra: dict[str, str] | None = None, plugin_id: str = PLUGIN_ID) -> bytes:
    """按 PLUGIN_SPEC §1.2 的合法结构打一个最小插件 zip。"""
    if top_dir is None:
        top_dir = plugin_id
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        def prefixed(name: str) -> str:
            return f"{top_dir}/{name}" if top_dir else name

        zf.writestr(prefixed("plugin.json"),
                    json.dumps(manifest(version, min_host, engine_host, plugin_id), ensure_ascii=False))
        zf.writestr(prefixed("LICENSE"), LICENSE_TEXT)
        zf.writestr(prefixed("dist/plugin.js"), f"console.log('v{version}');")
        for name, text in (extra or {}).items():
            zf.writestr(prefixed(name), text)
    return buffer.getvalue()


def build_host_zip(version: str = "9.9.9", wrap: str | None = None,
                   drop: tuple[str, ...] = ()) -> bytes:
    """打一个「像底座发行包」的 zip：必须含 app/main.py、static/workspace.html、LICENSE。"""
    files = {
        "app/main.py": "from fastapi import FastAPI\napp = FastAPI()\n",
        "app/__init__.py": f'__version__ = "{version}"\n',
        "static/workspace.html": "<!doctype html><title>九章算子</title>",
        "LICENSE": LICENSE_TEXT,
        "data/should_never_land.db": "if this file appears, data/ was not protected",
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, text in files.items():
            if name in drop:
                continue
            zf.writestr(f"{wrap}/{name}" if wrap else name, text)
    return buffer.getvalue()


def entry(version: str = "2.0.0", min_host: str = "", zip_url: str = "https://example.invalid/p.zip",
          plugin_id: str = PLUGIN_ID, **extra) -> dict:
    row = {"id": plugin_id, "name": "更新契约测试插件", "version": version,
           "zip_url": zip_url, "mirrors": [], "description": "", "homepage": None,
           "kind": "renderer", "api_version": "1.0", "min_host_version": min_host}
    row.update(extra)
    return row


def index(entries: list[dict] | None = None, host: dict | None = None) -> dict:
    return {"index_version": "1.0", "index_name": "测试索引", "updated_at": "2026-10-23T00:00:00+08:00",
            "entries": entries or [], "rejected": [], "entry_count": len(entries or []),
            "rejected_count": 0, "host": host, "host_rejected": ""}


class IsolatedDirsMixin(unittest.TestCase):
    """把 plugins/ 与 data/ 都指到临时目录，绝不在真仓库里覆盖插件。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plugins_dir = self.root / "plugins"
        self.data_dir = self.root / "data"
        self.plugins_dir.mkdir()
        self.data_dir.mkdir()
        self._env = mock.patch.dict(os.environ, {"JZO_DATA_DIR": self.data_dir.as_posix()})
        self._env.start()
        self.addCleanup(self._env.stop)
        self._plugins = mock.patch.object(Settings, "plugins_dir", self.plugins_dir)
        self._plugins.start()
        self.addCleanup(self._plugins.stop)
        self._root = mock.patch.object(Settings, "project_root", self.root)
        self._root.start()
        self.addCleanup(self._root.stop)

    def install_local(self, version: str = "1.0.0", files: dict[str, str] | None = None) -> Path:
        """在临时 plugins/ 里摆一个「已装的旧版本」，可附带数据文件。"""
        destination = self.plugins_dir / PLUGIN_ID
        (destination / "dist").mkdir(parents=True, exist_ok=True)
        (destination / "plugin.json").write_text(
            json.dumps(manifest(version), ensure_ascii=False), encoding="utf-8")
        (destination / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
        (destination / "dist" / "plugin.js").write_text(f"console.log('v{version}');", encoding="utf-8")
        for name, text in (files or {}).items():
            path = destination / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return destination


class SemverTest(unittest.TestCase):
    def test_01_parse_numeric_and_prerelease(self):
        self.assertEqual(parse_version("1.2.3"), (1, 2, 3, ""))
        self.assertEqual(parse_version("0.9.0-rc.1"), (0, 9, 0, "rc.1"))
        self.assertEqual(parse_version("  1.0.0  "), (1, 0, 0, ""))

    def test_02_parse_rejects_garbage(self):
        for bad in ("", None, "1", "1.2", "v1.2.3", "1.2.3.4", "abc", "1.2.x", "0.9.0-"):
            self.assertIsNone(parse_version(bad), f"{bad!r} 不该被当成合法版本号")

    def test_03_compare_numeric_segments(self):
        self.assertEqual(compare_versions("1.0.0", "0.9.9"), 1)
        self.assertEqual(compare_versions("0.9.0", "0.10.0"), -1)
        self.assertEqual(compare_versions("1.2.3", "1.2.3"), 0)
        self.assertEqual(compare_versions("2.0.0", "1.99.99"), 1)

    def test_04_prerelease_is_lower_than_release(self):
        self.assertEqual(compare_versions("1.0.0-rc.1", "1.0.0"), -1)
        self.assertEqual(compare_versions("1.0.0", "1.0.0-rc.1"), 1)
        self.assertEqual(compare_versions("1.0.0-rc.1", "1.0.0-rc.2"), -1)
        self.assertEqual(compare_versions("1.0.0-rc.1", "1.0.0-rc.1"), 0)
        self.assertEqual(compare_versions("1.0.0-alpha", "1.0.0-rc.1"), -1)
        self.assertEqual(compare_versions("1.0.0-rc.2", "1.0.0-rc.10"), -1)

    def test_05_malformed_version_returns_none_not_zero(self):
        """写坏的版本号必须返回 None：不能被当成「一样新」静默跳过。"""
        self.assertIsNone(compare_versions("坏版本", "1.0.0"))
        self.assertIsNone(compare_versions("1.0.0", ""))
        self.assertIsNone(compare_versions(None, None))


class CompatibilityTest(unittest.TestCase):
    def test_01_host_version_is_the_single_baseline(self):
        from app import __version__
        self.assertEqual(host_version(), str(__version__))

    def test_02_empty_min_host_means_unrestricted(self):
        for value in ("", None, "   "):
            self.assertTrue(host_satisfies(value), f"{value!r} 缺省应视为不设限")

    def test_03_malformed_min_host_is_unsatisfied(self):
        """写坏的兼容声明按「不满足」处置——宁可拦住，不许覆盖出砖。"""
        for value in ("随便写", "1.2", "v9.9.9"):
            self.assertFalse(host_satisfies(value), f"{value!r} 写坏应判不满足")

    def test_04_future_requirement_blocks(self):
        self.assertFalse(host_satisfies("99.0.0"))
        self.assertTrue(host_satisfies("0.0.1"))

    def test_05_manifest_takes_the_stricter_of_two_declarations(self):
        self.assertEqual(manifest_min_host({"min_host_version": "0.9.0",
                                            "engine": {"host_version": "1.2.0"}}), "1.2.0")
        self.assertEqual(manifest_min_host({"min_host_version": "1.2.0",
                                            "engine": {"host_version": "0.9.0"}}), "1.2.0")
        self.assertEqual(manifest_min_host({"engine": {"host_version": "0.9.0"}}), "0.9.0")

    def test_06_manifest_ignores_garbage_declarations(self):
        self.assertEqual(manifest_min_host({"min_host_version": "坏", "engine": {"host_version": "0.9.0"}}),
                         "0.9.0")
        self.assertEqual(manifest_min_host({"min_host_version": "坏"}), "")
        self.assertEqual(manifest_min_host({}), "")
        self.assertEqual(manifest_min_host({"engine": "不是对象"}), "")

    def test_07_gate_honours_patched_host_version(self):
        with mock.patch.object(plugin_update, "__version__", "0.9.0"):
            self.assertTrue(host_satisfies("0.9.0"))
            self.assertFalse(host_satisfies("0.9.1"))


class CheckUpdatesTest(IsolatedDirsMixin):
    def installed(self, plugin_id: str = PLUGIN_ID, version: str = "1.0.0") -> list[dict]:
        return [{"id": plugin_id, "name": "更新契约测试插件", "version": version, "enabled": True}]

    def test_01_update_available_when_remote_is_newer(self):
        result = check_updates(index([entry("2.0.0")]), installed=self.installed())
        row = result["plugins"][0]
        self.assertEqual(row["state"], "update_available")
        self.assertTrue(row["compatible"])
        self.assertEqual((row["local_version"], row["remote_version"]), ("1.0.0", "2.0.0"))
        self.assertEqual(result["summary"]["update_available"], 1)

    def test_02_up_to_date_and_no_downgrade(self):
        same = check_updates(index([entry("1.0.0")]), installed=self.installed())
        self.assertEqual(same["plugins"][0]["state"], "up_to_date")
        self.assertIn("已是最新", same["plugins"][0]["reason"])

        older = check_updates(index([entry("0.9.0")]), installed=self.installed())
        self.assertEqual(older["plugins"][0]["state"], "up_to_date")
        self.assertIn("不降级", older["plugins"][0]["reason"])
        self.assertEqual(older["summary"]["update_available"], 0)

    def test_03_incompatible_marks_needs_host_update(self):
        result = check_updates(index([entry("2.0.0", min_host="99.0.0")]), installed=self.installed())
        row = result["plugins"][0]
        self.assertEqual(row["state"], "incompatible")
        self.assertFalse(row["compatible"])
        self.assertIn("需先更新底座", row["reason"])
        self.assertEqual(result["summary"]["incompatible"], 1)

    def test_04_bad_version_only_kills_its_own_row(self):
        result = check_updates(index([entry("不是版本"), entry("3.0.0", plugin_id="org.jiuzhang.other")]),
                               installed=self.installed() + [{"id": "org.jiuzhang.other",
                                                              "name": "另一个", "version": "1.0.0"}])
        states = {row["id"]: row["state"] for row in result["plugins"]}
        self.assertEqual(states[PLUGIN_ID], "bad_entry")
        self.assertEqual(states["org.jiuzhang.other"], "update_available")
        self.assertIn("版本号写坏", [row for row in result["plugins"]
                                  if row["id"] == PLUGIN_ID][0]["reason"])

    def test_05_plugin_missing_from_index_is_not_an_error(self):
        result = check_updates(index([]), installed=self.installed())
        row = result["plugins"][0]
        self.assertEqual(row["state"], "not_in_index")
        self.assertTrue(row["compatible"], "索引没收录不等于不兼容，更不许拦加载")
        self.assertEqual(result["summary"]["not_in_index"], 1)

    def test_06_host_block_newer_version(self):
        result = check_updates(index([], host={"version": "99.0.0", "zip_url": "https://example.invalid/h.zip",
                                               "mirrors": [], "notes": "修复了若干问题"}))
        self.assertTrue(result["host"]["update_available"])
        self.assertEqual(result["host"]["available"], "99.0.0")
        self.assertEqual(result["host"]["notes"], "修复了若干问题")

    def test_07_host_block_same_or_older_never_downgrades(self):
        current = host_version()
        same = check_updates(index([], host={"version": current, "zip_url": "https://example.invalid/h.zip",
                                             "mirrors": [], "notes": ""}))
        self.assertFalse(same["host"]["update_available"])
        self.assertIn("已是最新", same["host"]["reason"])

        older = check_updates(index([], host={"version": "0.0.1", "zip_url": "https://example.invalid/h.zip",
                                              "mirrors": [], "notes": ""}))
        self.assertFalse(older["host"]["update_available"])
        self.assertIn("不降级", older["host"]["reason"])

    def test_08_missing_or_broken_host_block_only_reports_itself(self):
        for payload in (index([]), index([], host=None),
                        index([], host={"version": "坏", "zip_url": "https://example.invalid/h.zip",
                                        "mirrors": [], "notes": ""})):
            result = check_updates(payload)
            self.assertFalse(result["host"]["update_available"])
            self.assertTrue(result["host"]["reason"])

    def test_09_summary_counts_match_rows(self):
        result = check_updates(
            index([entry("2.0.0"), entry("9.9.9", min_host="99.0.0", plugin_id="org.jiuzhang.b"),
                   entry("坏", plugin_id="org.jiuzhang.c")]),
            installed=[{"id": PLUGIN_ID, "name": "a", "version": "1.0.0"},
                       {"id": "org.jiuzhang.b", "name": "b", "version": "1.0.0"},
                       {"id": "org.jiuzhang.c", "name": "c", "version": "1.0.0"},
                       {"id": "org.jiuzhang.d", "name": "d", "version": "1.0.0"}])
        summary = result["summary"]
        self.assertEqual(summary["checked"], 4)
        self.assertEqual(summary["update_available"], 1)
        self.assertEqual(summary["incompatible"], 1)
        self.assertEqual(summary["bad_entry"], 1)
        self.assertEqual(summary["not_in_index"], 1)

    def test_10_installed_defaults_to_real_discovery(self):
        """不给 installed 时必须走真实插件发现，而不是当成「一个都没装」。"""
        self.install_local("1.0.0")
        result = check_updates(index([entry("2.0.0")]))
        rows = {row["id"]: row for row in result["plugins"]}
        self.assertIn(PLUGIN_ID, rows)
        self.assertEqual(rows[PLUGIN_ID]["state"], "update_available")
        self.assertEqual(rows[PLUGIN_ID]["local_version"], "1.0.0")


class ApplyPluginUpdateTest(IsolatedDirsMixin):
    def test_01_update_replaces_code_and_reports_versions(self):
        self.install_local("1.0.0")
        result = apply_plugin_update(entry("2.0.0"), local_version="1.0.0", data=build_zip("2.0.0"))
        self.assertEqual(result["id"], PLUGIN_ID)
        self.assertEqual((result["from"], result["to"]), ("1.0.0", "2.0.0"))
        self.assertEqual((self.plugins_dir / PLUGIN_ID / "dist" / "plugin.js").read_text(encoding="utf-8"),
                         "console.log('v2.0.0');")

    def test_02_data_files_survive_the_overwrite(self):
        """ADR-006 死命令 1：老师的题库、备份与灌库报告住在插件目录里，更新不许动。"""
        self.install_local("1.0.0", files={
            "bank/bank.db": "456 道真题的二进制内容",
            "bank/bank.db.pre-v082.bak": "上一版备份",
            "bank/v063.db": "灌库中间产物",
            "bank/migration_report.json": '{"migrated": 456}',
        })
        result = apply_plugin_update(entry("2.0.0"), local_version="1.0.0", data=build_zip("2.0.0"))
        root = self.plugins_dir / PLUGIN_ID
        self.assertEqual((root / "bank" / "bank.db").read_text(encoding="utf-8"), "456 道真题的二进制内容")
        self.assertEqual((root / "bank" / "bank.db.pre-v082.bak").read_text(encoding="utf-8"), "上一版备份")
        self.assertEqual((root / "bank" / "v063.db").read_text(encoding="utf-8"), "灌库中间产物")
        self.assertEqual(json.loads((root / "bank" / "migration_report.json").read_text(encoding="utf-8")),
                         {"migrated": 456})
        self.assertEqual(sorted(result["preserved"]),
                         ["bank/bank.db", "bank/bank.db.pre-v082.bak", "bank/migration_report.json",
                          "bank/v063.db"])

    def test_03_old_data_wins_over_same_named_new_file(self):
        """新包里带的空壳种子库绝不能顶掉老师的真题库。"""
        self.install_local("1.0.0", files={"bank/bank.db": "真题库"})
        result = apply_plugin_update(entry("2.0.0"), local_version="1.0.0",
                                     data=build_zip("2.0.0", extra={"bank/bank.db": "空库"}))
        self.assertEqual((self.plugins_dir / PLUGIN_ID / "bank" / "bank.db").read_text(encoding="utf-8"),
                         "真题库")
        self.assertEqual(result["data_overridden"], ["bank/bank.db"])

    def test_04_local_only_files_are_carried_over(self):
        """更新是合并语义：分不清「删掉的旧代码」与「老师的数据」时一律按数据办。"""
        self.install_local("1.0.0", files={"dist/old-helper.js": "旧代码",
                                           "bank/assets/figure-1.jpg": "题目配图"})
        result = apply_plugin_update(entry("2.0.0"), local_version="1.0.0", data=build_zip("2.0.0"))
        root = self.plugins_dir / PLUGIN_ID
        self.assertEqual((root / "dist" / "old-helper.js").read_text(encoding="utf-8"), "旧代码")
        self.assertEqual((root / "bank" / "assets" / "figure-1.jpg").read_text(encoding="utf-8"), "题目配图")
        self.assertEqual(sorted(result["preserved"]),
                         ["bank/assets/figure-1.jpg", "dist/old-helper.js"])

    def test_04b_code_files_from_the_new_package_do_replace_the_old_ones(self):
        self.install_local("1.0.0")
        apply_plugin_update(entry("2.0.0"), local_version="1.0.0", data=build_zip("2.0.0"))
        root = self.plugins_dir / PLUGIN_ID
        self.assertEqual((root / "dist" / "plugin.js").read_text(encoding="utf-8"),
                         "console.log('v2.0.0');")
        self.assertEqual(json.loads((root / "plugin.json").read_text(encoding="utf-8"))["version"], "2.0.0")

    def test_05_incompatible_index_entry_never_touches_local_code(self):
        self.install_local("1.0.0")
        before = (self.plugins_dir / PLUGIN_ID / "dist" / "plugin.js").read_text(encoding="utf-8")
        with self.assertRaises(UpdateRejected) as caught:
            apply_plugin_update(entry("2.0.0", min_host="99.0.0"), local_version="1.0.0",
                                data=build_zip("2.0.0"))
        self.assertEqual(caught.exception.code, "incompatible")
        self.assertIn("需先更新底座", caught.exception.message)
        self.assertEqual((self.plugins_dir / PLUGIN_ID / "dist" / "plugin.js").read_text(encoding="utf-8"),
                         before)
        self.assertEqual(json.loads((self.plugins_dir / PLUGIN_ID / "plugin.json").read_text(encoding="utf-8"))["version"],
                         "1.0.0")

    def test_06_incompatible_new_manifest_is_caught_by_the_second_gate(self):
        """索引条目没写 min_host_version，新包清单里写了——第二道闸门必须拦住。"""
        self.install_local("1.0.0")
        with self.assertRaises(UpdateRejected) as caught:
            apply_plugin_update(entry("2.0.0"), local_version="1.0.0",
                                data=build_zip("2.0.0", min_host="99.0.0"))
        self.assertEqual(caught.exception.code, "incompatible")
        self.assertEqual(json.loads((self.plugins_dir / PLUGIN_ID / "plugin.json").read_text(encoding="utf-8"))["version"],
                         "1.0.0")

    def test_07_engine_host_version_also_gates(self):
        self.install_local("1.0.0")
        with self.assertRaises(UpdateRejected):
            apply_plugin_update(entry("2.0.0"), local_version="1.0.0",
                                data=build_zip("2.0.0", engine_host="99.0.0"))
        self.assertEqual(json.loads((self.plugins_dir / PLUGIN_ID / "plugin.json").read_text(encoding="utf-8"))["version"],
                         "1.0.0")

    def test_08_compatible_requirement_passes_and_is_reported(self):
        self.install_local("1.0.0")
        result = apply_plugin_update(entry("2.0.0"), local_version="1.0.0",
                                     data=build_zip("2.0.0", min_host="0.1.0"))
        self.assertEqual(result["to"], "2.0.0")
        self.assertEqual(result["min_host_version"], "0.1.0")

    def test_09_id_mismatch_is_rejected(self):
        self.install_local("1.0.0")
        with self.assertRaises(UpdateRejected) as caught:
            apply_plugin_update(entry("2.0.0", plugin_id="org.jiuzhang.someone-else"),
                                local_version="1.0.0", data=build_zip("2.0.0"))
        self.assertEqual(caught.exception.code, "id_mismatch")
        self.assertFalse((self.plugins_dir / "org.jiuzhang.someone-else").exists(),
                         "不得改名换目录")
        self.assertTrue((self.plugins_dir / PLUGIN_ID / "plugin.json").is_file())

    def test_10_entry_without_id_is_rejected(self):
        with self.assertRaises(UpdateRejected):
            apply_plugin_update({"version": "2.0.0"}, data=build_zip("2.0.0"))

    def test_11_contract_invalid_package_is_rejected(self):
        """包本身不合格（缺 LICENSE / 清单坏）走安装链同款校验，落地前整体丢弃。"""
        from app.core.plugin_install import PluginInstallError
        self.install_local("1.0.0")
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr(f"{PLUGIN_ID}/plugin.json", json.dumps(manifest("2.0.0"), ensure_ascii=False))
        with self.assertRaises(PluginInstallError):
            apply_plugin_update(entry("2.0.0"), local_version="1.0.0", data=buffer.getvalue())
        self.assertEqual(json.loads((self.plugins_dir / PLUGIN_ID / "plugin.json").read_text(encoding="utf-8"))["version"],
                         "1.0.0")

    def test_12_missing_zip_url_without_data_is_rejected(self):
        with self.assertRaises(UpdateRejected) as caught:
            apply_plugin_update({"id": PLUGIN_ID, "version": "2.0.0", "zip_url": ""})
        self.assertIn("zip_url", caught.exception.message)

    def test_13_download_happens_only_when_bytes_are_absent(self):
        """出网铁律：给了字节就绝不下载；要下载也必须只走那一个条目的地址序列。"""
        self.install_local("1.0.0")
        with mock.patch.object(plugin_update, "download_plugin_zip_sources") as fake:
            apply_plugin_update(entry("2.0.0"), local_version="1.0.0", data=build_zip("2.0.0"))
        fake.assert_not_called()

        with mock.patch.object(plugin_update, "download_plugin_zip_sources",
                               return_value=(build_zip("2.0.0"), "https://example.invalid/p.zip")) as fake2:
            row = entry("2.0.0", zip_url="https://example.invalid/p.zip")
            row["mirrors"] = ["https://mirror.invalid/p.zip"]
            apply_plugin_update(row, local_version="1.0.0")
        fake2.assert_called_once_with("https://example.invalid/p.zip", ["https://mirror.invalid/p.zip"])

    def test_14_fresh_install_into_empty_plugins_dir(self):
        result = apply_plugin_update(entry("2.0.0"), local_version="", data=build_zip("2.0.0"))
        self.assertEqual(result["from"], "")
        self.assertEqual(result["preserved"], [])
        self.assertTrue((self.plugins_dir / PLUGIN_ID / "plugin.json").is_file())


class ApplyUpdatesBatchTest(IsolatedDirsMixin):
    def rows(self) -> list[dict]:
        return [
            entry("2.0.0", plugin_id=PLUGIN_ID, state="update_available", local_version="1.0.0"),
            entry("9.9.9", min_host="99.0.0", plugin_id="org.jiuzhang.b",
                  state="incompatible", local_version="1.0.0", reason="需先更新底座"),
            entry("坏", plugin_id="org.jiuzhang.c", state="bad_entry", local_version="1.0.0"),
            entry("1.0.0", plugin_id="org.jiuzhang.d", state="up_to_date", local_version="1.0.0"),
        ]

    def test_01_only_update_available_rows_are_touched(self):
        self.install_local("1.0.0")
        payload = build_zip("2.0.0")
        with mock.patch.object(plugin_update, "download_plugin_zip_sources",
                               return_value=(payload, "https://example.invalid/p.zip")):
            result = apply_updates(self.rows())
        self.assertEqual([row["id"] for row in result["updated"]], [PLUGIN_ID])
        self.assertEqual({row["id"] for row in result["skipped"]},
                         {"org.jiuzhang.b", "org.jiuzhang.c", "org.jiuzhang.d"})
        self.assertEqual(result["failed"], [])

    def test_02_allow_download_false_blocks_every_outbound_call(self):
        """续更只消费本机已下载的包：不允许出网时一条都不许发请求。"""
        self.install_local("1.0.0")
        with mock.patch.object(plugin_update, "download_plugin_zip_sources") as fake:
            result = apply_updates(self.rows(), allow_download=False)
        fake.assert_not_called()
        self.assertEqual(result["updated"], [])
        self.assertEqual(len(result["skipped"]), 4)
        self.assertIn("不允许出网", [row["reason"] for row in result["skipped"]
                                  if row["id"] == PLUGIN_ID][0])

    def test_03_one_failure_does_not_poison_the_batch(self):
        self.install_local("1.0.0")
        good = entry("2.0.0", plugin_id=PLUGIN_ID, state="update_available", local_version="1.0.0")
        bad = entry("2.0.0", plugin_id="org.jiuzhang.broken", state="update_available", local_version="1.0.0")
        calls = {"n": 0}

        def fake_download(url, mirrors=None):
            calls["n"] += 1
            if "broken" in url:
                raise UpdateRejected("所有下载地址均失败")
            return build_zip("2.0.0"), url

        broken_row = dict(bad)
        broken_row["zip_url"] = "https://example.invalid/broken.zip"
        with mock.patch.object(plugin_update, "download_plugin_zip_sources", side_effect=fake_download):
            result = apply_updates([broken_row, good])
        self.assertEqual([row["id"] for row in result["updated"]], [PLUGIN_ID])
        self.assertEqual([row["id"] for row in result["failed"]], ["org.jiuzhang.broken"])
        self.assertEqual(calls["n"], 2, "一次点击 = 一次批量任务，逐条串行，不重试")

    def test_04_non_dict_rows_are_ignored(self):
        result = apply_updates([None, "字符串", 42])
        self.assertEqual(result, {"updated": [], "failed": [], "skipped": []})


class PendingStateTest(IsolatedDirsMixin):
    def test_01_absent_state_reads_as_empty(self):
        self.assertEqual(read_pending(), {"host_version": "", "pending": [], "written_at": ""})

    def test_02_write_then_read_roundtrip(self):
        payload = write_pending("9.9.9", [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0",
                                           "zip_path": str(self.root / "p.zip")}])
        self.assertTrue(payload["written_at"])
        state = read_pending()
        self.assertEqual(state["host_version"], "9.9.9")
        self.assertEqual(state["pending"], [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0",
                                             "zip_path": str(self.root / "p.zip")}])

    def test_03_state_file_lives_in_data_dir_and_holds_no_question_data(self):
        write_pending("9.9.9", [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0", "zip_path": "x"}])
        path = self.data_dir / "update_state.json"
        self.assertTrue(path.is_file(), "续更状态只能落在 data/update_state.json")
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("stem", text)
        self.assertNotIn("questions", text)

    def test_04_corrupt_state_never_blocks_boot(self):
        (self.data_dir / "update_state.json").write_text("{ 这不是 JSON", encoding="utf-8")
        self.assertEqual(read_pending(), {"host_version": "", "pending": [], "written_at": ""})

        (self.data_dir / "update_state.json").write_text('["数组不是对象"]', encoding="utf-8")
        self.assertEqual(read_pending()["pending"], [])

        (self.data_dir / "update_state.json").write_text(
            json.dumps({"host_version": "9.9.9", "pending": [{"no_id": 1}, "坏", {"id": "org.x"}]}),
            encoding="utf-8")
        self.assertEqual(read_pending()["pending"], [{"id": "org.x"}])

    def test_05_clear_is_idempotent(self):
        write_pending("9.9.9", [{"id": PLUGIN_ID}])
        self.assertEqual(clear_pending()["pending"], [])
        self.assertFalse((self.data_dir / "update_state.json").exists())
        self.assertEqual(clear_pending()["pending"], [], "文件不存在也算成功")

    def test_06_resume_applies_local_zip_without_any_network(self):
        self.install_local("1.0.0", files={"bank/bank.db": "真题库"})
        zip_path = self.root / "staged.zip"
        zip_path.write_bytes(build_zip("2.0.0"))
        write_pending("", [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0", "zip_path": str(zip_path)}])

        with mock.patch.object(plugin_update, "download_plugin_zip_sources") as fake:
            result = resume_pending()
        fake.assert_not_called()
        self.assertTrue(result["had_pending"])
        self.assertEqual([row["id"] for row in result["resumed"]], [PLUGIN_ID])
        self.assertEqual(result["failed"], [])
        self.assertEqual(json.loads((self.plugins_dir / PLUGIN_ID / "plugin.json").read_text(encoding="utf-8"))["version"],
                         "2.0.0")
        self.assertEqual((self.plugins_dir / PLUGIN_ID / "bank" / "bank.db").read_text(encoding="utf-8"),
                         "真题库")
        self.assertFalse(zip_path.exists(), "补齐成功后清掉本机临时包")
        self.assertEqual(read_pending()["pending"], [], "补齐跑完就清状态，不排队不续跑")

    def test_07_resume_reports_missing_package_honestly(self):
        write_pending("", [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0",
                            "zip_path": str(self.root / "gone.zip")}])
        result = resume_pending()
        self.assertEqual([row["id"] for row in result["failed"]], [PLUGIN_ID])
        self.assertIn("已不在", result["failed"][0]["reason"])
        self.assertEqual(read_pending()["pending"], [])

    def test_08_resume_with_incompatible_package_keeps_local_code(self):
        self.install_local("1.0.0")
        zip_path = self.root / "staged.zip"
        zip_path.write_bytes(build_zip("2.0.0", min_host="99.0.0"))
        write_pending("", [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0", "zip_path": str(zip_path)}])
        result = resume_pending()
        self.assertEqual([row["id"] for row in result["failed"]], [PLUGIN_ID])
        self.assertEqual(json.loads((self.plugins_dir / PLUGIN_ID / "plugin.json").read_text(encoding="utf-8"))["version"],
                         "1.0.0")

    def test_09_resume_without_pending_is_a_noop(self):
        result = resume_pending()
        self.assertEqual(result["resumed"], [])
        self.assertEqual(result["failed"], [])
        self.assertFalse(result["had_pending"])
        self.assertTrue(result["ran"])
        self.assertTrue(result["at"], "续更结果要带时间戳，供前端如实播报")
        self.assertTrue(plugin_update.last_resume()["ran"])


class UpdateScriptTest(unittest.TestCase):
    ROOT = Path("C:/jzo")
    STAGED = Path("C:/temp/stage")

    def setUp(self) -> None:
        self.script = build_update_script(root=self.ROOT, staged=self.STAGED, pid=4321, port=8123)
        self.lines = self.script.splitlines()
        self.robocopy = [line for line in self.lines if line.startswith("robocopy")][0]

    def rendered(self, *parts: str) -> str:
        return str(self.ROOT.joinpath(*parts))

    def test_01_every_excluded_dir_is_listed_for_robocopy(self):
        self.assertEqual(HOST_EXCLUDED_DIRS,
                         ("data", ".venv", ".git", "dist", "__pycache__", ".system_generated"))
        self.assertIn("/XD", self.robocopy)
        # 传目标绝对路径在「阶段 → 根」方向不生效（update_probe 沙箱真跑抓出），
        # 所以 /XD 只认目录名；裸名会在源与目标两侧同时跳过该目录。
        for name in HOST_EXCLUDED_DIRS:
            self.assertIn(f'"{name}"', self.robocopy, f"{name}/ 必须被排除")
            self.assertNotIn(f'"{self.rendered(name)}"', self.robocopy,
                             f"{name}/ 不能只写绝对路径（robocopy /XD 不生效）")

    def test_02_data_is_the_first_exclusion(self):
        """data/ 是老师的财产，必须排在排除清单最前面、且确实被排除。"""
        positions = [self.robocopy.index(f'"{name}"') for name in HOST_EXCLUDED_DIRS]
        self.assertEqual(positions, sorted(positions), "排除顺序应与 HOST_EXCLUDED_DIRS 一致")
        self.assertEqual(HOST_EXCLUDED_DIRS[0], "data")

    def test_03_bytecode_patterns_excluded(self):
        self.assertIn("/XF", self.robocopy)
        for pattern in HOST_EXCLUDED_FILES:
            self.assertIn(f'"{pattern}"', self.robocopy)

    def test_04_waits_for_the_old_process_before_copying(self):
        self.assertIn('set "JZO_PID=4321"', self.script)
        self.assertIn("tasklist", self.script)
        self.assertIn(":wait_exit", self.script)
        self.assertLess(self.script.index("tasklist"), self.script.index("robocopy"),
                        "必须先等父进程退出，再覆盖文件")

    def test_05_copies_stage_over_root_in_the_right_direction(self):
        self.assertIn('set "JZO_ROOT=%s"' % self.rendered(), self.script)
        self.assertIn('set "JZO_STAGE=%s"' % str(self.STAGED), self.script)
        self.assertIn('robocopy "%JZO_STAGE%" "%JZO_ROOT%" /E', self.robocopy)

    def test_06_robocopy_failure_aborts_before_relaunch(self):
        self.assertIn("if errorlevel 8", self.script)
        self.assertLess(self.script.index("if errorlevel 8"), self.script.index("uvicorn"),
                        "覆盖失败就不许重启，保留原文件")

    def test_07_relaunches_the_host_and_cleans_up_after_itself(self):
        self.assertIn("uvicorn app.main:app", self.script)
        self.assertIn("--port 8123", self.script)
        self.assertIn(self.rendered(".venv", "Scripts", "python.exe"), self.script)
        self.assertIn('rmdir /S /Q "%JZO_STAGE%"', self.script)
        self.assertIn('del "%~f0"', self.script)
        self.assertLess(self.script.index("uvicorn"), self.script.index('del "%~f0"'))

    def test_08_script_is_crlf_batch_text(self):
        self.assertTrue(self.script.startswith("@echo off\r\n"))
        self.assertNotIn("\n", self.script.replace("\r\n", ""), "批处理必须整篇 CRLF")
        self.assertIn("@echo off", self.lines[0])


class HostPackageTest(IsolatedDirsMixin):
    def test_01_valid_host_zip_extracts_and_strips_the_wrapper_dir(self):
        target = self.root / "host"
        target.mkdir()
        plugin_update._extract_host_zip(build_host_zip(wrap="jiuzhang-operator-9.9.9"), target)
        self.assertTrue((target / "app" / "main.py").is_file())
        self.assertTrue((target / "static" / "workspace.html").is_file())
        self.assertTrue((target / "LICENSE").is_file())

    def test_02_package_missing_a_required_file_is_not_the_host(self):
        for required in ("app/main.py", "static/workspace.html", "LICENSE"):
            target = self.root / f"host-{abs(hash(required))}"
            target.mkdir()
            with self.assertRaises(UpdateRejected, msg=required) as caught:
                plugin_update._extract_host_zip(build_host_zip(drop=(required,)), target)
            self.assertIn(required, caught.exception.message)

    def test_03_a_plugin_zip_cannot_masquerade_as_the_host(self):
        target = self.root / "host-plugin"
        target.mkdir()
        with self.assertRaises(UpdateRejected):
            plugin_update._extract_host_zip(build_zip("2.0.0"), target)

    def test_04_garbage_payloads_are_rejected(self):
        target = self.root / "host-bad"
        target.mkdir()
        for payload in (b"", b"this is not a zip", b"PK\x03\x04"):
            with self.assertRaises(UpdateRejected):
                plugin_update._extract_host_zip(payload, target)

    def test_05_path_traversal_entries_are_rejected(self):
        """复用安装链的 _check_entry：``..`` 穿越一律拒。"""
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as zf:
            zf.writestr("app/main.py", "x")
            zf.writestr("static/workspace.html", "x")
            zf.writestr("LICENSE", "x")
            zf.writestr("../evil.bat", "echo pwned")
        target = self.root / "host-traversal"
        target.mkdir()
        with self.assertRaises(Exception):
            plugin_update._extract_host_zip(buffer.getvalue(), target)
        self.assertFalse((self.root / "evil.bat").exists())


class PrepareHostUpdateTest(IsolatedDirsMixin):
    def test_01_prepare_writes_the_script_without_killing_anything(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch("tempfile.gettempdir", return_value=temp):
                with mock.patch.object(plugin_update, "__version__", "0.9.0"):
                    result = prepare_host_update(
                        {"version": "9.9.9", "zip_url": "https://example.invalid/h.zip",
                         "mirrors": [], "notes": "修复了若干问题"},
                        port=8123, data=build_host_zip())
                    script = Path(result["script_path"])
                    self.assertTrue(script.is_file())
                    script_text = script.read_text(encoding="utf-8")
                    staged_main = Path(result["staged_at"], "app", "main.py")
                    self.assertTrue(staged_main.is_file())
        self.assertEqual((result["current"], result["version"]), ("0.9.0", "9.9.9"))
        self.assertEqual(result["notes"], "修复了若干问题")
        self.assertEqual(result["excluded_dirs"], list(HOST_EXCLUDED_DIRS))
        self.assertIn("--port 8123", script_text)
        self.assertTrue(result["launchable"], "临时 project_root 里没有 .git，属发行包形态，可执行")

    def test_02_dev_worktree_is_not_launchable(self):
        (self.root / ".git").mkdir()
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch("tempfile.gettempdir", return_value=temp):
                with mock.patch.object(plugin_update, "__version__", "0.9.0"):
                    result = prepare_host_update(
                        {"version": "9.9.9", "zip_url": "https://example.invalid/h.zip",
                         "mirrors": [], "notes": ""}, data=build_host_zip())
        self.assertFalse(result["launchable"])

    def test_03_older_or_equal_host_version_is_refused(self):
        with mock.patch.object(plugin_update, "__version__", "9.9.9"):
            for available in ("9.9.9", "0.9.0"):
                with self.assertRaises(UpdateRejected, msg=available):
                    prepare_host_update({"version": available,
                                         "zip_url": "https://example.invalid/h.zip",
                                         "mirrors": [], "notes": ""}, data=build_host_zip())

    def test_04_missing_host_block_or_bad_version_is_refused(self):
        for block in ({}, {"zip_url": ""}, {"version": "坏", "zip_url": "https://example.invalid/h.zip"},
                      None, "不是对象"):
            with self.assertRaises(UpdateRejected, msg=repr(block)):
                prepare_host_update(block, data=build_host_zip())

    def test_05_prepare_keeps_the_pending_plugin_list_for_the_resume_pass(self):
        write_pending("", [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0", "zip_path": "x"}])
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch("tempfile.gettempdir", return_value=temp):
                with mock.patch.object(plugin_update, "__version__", "0.9.0"):
                    result = prepare_host_update(
                        {"version": "9.9.9", "zip_url": "https://example.invalid/h.zip",
                         "mirrors": [], "notes": ""}, data=build_host_zip())
        self.assertEqual(result["pending_plugins"], [PLUGIN_ID])
        state = read_pending()
        self.assertEqual(state["host_version"], "9.9.9")
        self.assertEqual([row["id"] for row in state["pending"]], [PLUGIN_ID])

    def test_06_download_only_happens_when_bytes_are_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch("tempfile.gettempdir", return_value=temp):
                with mock.patch.object(plugin_update, "__version__", "0.9.0"):
                    with mock.patch.object(plugin_update, "download_plugin_zip_sources") as fake:
                        prepare_host_update({"version": "9.9.9",
                                             "zip_url": "https://example.invalid/h.zip",
                                             "mirrors": [], "notes": ""}, data=build_host_zip())
                    fake.assert_not_called()
                    with mock.patch.object(plugin_update, "download_plugin_zip_sources",
                                           return_value=(build_host_zip(),
                                                         "https://example.invalid/h.zip")) as fake2:
                        prepare_host_update({"version": "9.9.9",
                                             "zip_url": "https://example.invalid/h.zip",
                                             "mirrors": ["https://mirror.invalid/h.zip"],
                                             "notes": ""})
                    fake2.assert_called_once_with("https://example.invalid/h.zip",
                                                  ["https://mirror.invalid/h.zip"])


class LaunchGuardTest(IsolatedDirsMixin):
    def test_01_missing_script_is_refused(self):
        with self.assertRaises(UpdateRejected) as caught:
            launch_host_update(str(self.root / "nope.bat"))
        self.assertIn("不存在", caught.exception.message)

    def test_02_dev_worktree_refuses_to_self_overwrite(self):
        """robocopy 覆盖正在运行的工作树会抹掉未提交的活儿——必须拒绝。"""
        (self.root / ".git").mkdir()
        script = self.root / "jzo_update.bat"
        script.write_text("@echo off\r\n", encoding="utf-8")
        with self.assertRaises(UpdateRejected) as caught:
            launch_host_update(str(script))
        self.assertEqual(caught.exception.code, "dev_worktree")

    def test_03_installed_release_would_launch_the_script(self):
        script = self.root / "jzo_update.bat"
        script.write_text("@echo off\r\n", encoding="utf-8")
        with mock.patch.object(plugin_update.subprocess, "Popen") as fake:
            result = launch_host_update(str(script))
        self.assertTrue(result["launched"])
        self.assertEqual(fake.call_count, 1)
        args = fake.call_args[0][0]
        self.assertEqual(args[:2], ["cmd.exe", "/c"])
        self.assertEqual(Path(args[2]), script)


class StagePluginZipTest(IsolatedDirsMixin):
    def test_01_downloaded_zip_is_kept_for_the_offline_resume_pass(self):
        payload = build_zip("2.0.0")
        with tempfile.TemporaryDirectory() as temp:
            with mock.patch("tempfile.gettempdir", return_value=temp):
                with mock.patch.object(plugin_update, "download_plugin_zip_sources",
                                       return_value=(payload, "https://example.invalid/p.zip")):
                    result = plugin_update.stage_plugin_zip(entry("2.0.0"))
                self.assertEqual(Path(result["zip_path"]).read_bytes(), payload)
        self.assertEqual(result["id"], PLUGIN_ID)
        self.assertEqual(result["to"], "2.0.0")
        self.assertEqual(result["source"], "https://example.invalid/p.zip")
        self.assertEqual(result["bytes"], len(payload))

    def test_02_entry_without_url_is_refused(self):
        with self.assertRaises(UpdateRejected):
            plugin_update.stage_plugin_zip({"id": PLUGIN_ID, "zip_url": ""})


class NoSilentNetworkTest(unittest.TestCase):
    """出网铁律（AGENTS §2 / PLUGIN_SPEC §1.7 裁决 1、2）的静态守卫。"""

    def setUp(self) -> None:
        self.source = (Path(__file__).resolve().parents[1] / "app" / "core" / "plugin_update.py") \
            .read_text(encoding="utf-8")

    def test_01_module_never_opens_a_socket_itself(self):
        for forbidden in ("urllib.request", "urlopen", "requests.", "httpx", "socket."):
            self.assertNotIn(forbidden, self.source,
                             f"本模块不得自己出网，只能由 API 层在用户点击后递地址进来（{forbidden}）")

    def test_02_no_timer_no_polling_no_startup_pull(self):
        for forbidden in ("threading.Timer", "schedule", "while True", "asyncio.sleep", "time.sleep"):
            self.assertNotIn(forbidden, self.source, f"严禁后台轮询（{forbidden}）")

    def test_03_resume_pass_stays_offline(self):
        body = self.source.split("def resume_pending(", 1)[1].split("\ndef ", 1)[0]
        self.assertNotIn("download", body, "续更只消费本机清单与已下载的包，不再额外出网")

    def test_04_update_write_scope_never_targets_the_data_dir(self):
        """插件更新的写范围只有 plugins/<id>/；data/ 只允许 update_state.json 一处痕迹。"""
        body = self.source.split("def apply_plugin_update(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("settings.plugins_dir", body)
        self.assertNotIn("data_dir", body)
        self.assertNotIn("root_data_dir", body)

    def test_05_pending_state_is_the_only_file_written_under_data(self):
        self.assertEqual(plugin_update.PENDING_FILENAME, "update_state.json")
        body = self.source.split("def write_pending(", 1)[1].split("\ndef ", 1)[0]
        self.assertIn("pending_path()", body)
        self.assertNotIn("data_dir", body.replace("root_data_dir", ""))


class ModuleSurfaceTest(unittest.TestCase):
    def test_01_public_names_are_exported(self):
        for name in ("check_updates", "apply_plugin_update", "apply_updates", "read_pending",
                     "write_pending", "clear_pending", "resume_pending", "prepare_host_update",
                     "launch_host_update", "build_update_script", "stage_plugin_zip",
                     "compare_versions", "host_satisfies", "UpdateRejected"):
            self.assertTrue(hasattr(plugin_update, name), f"缺少 {name}")

    def test_02_constants_are_frozen_tuples(self):
        for name in ("HOST_EXCLUDED_DIRS", "HOST_EXCLUDED_FILES", "DATA_SUFFIXES",
                     "DATA_FILENAMES", "HOST_REQUIRED_FILES"):
            self.assertIsInstance(getattr(plugin_update, name), tuple, f"{name} 必须是元组常量")

    def test_03_every_real_core_bank_file_survives_an_update(self):
        """拿本机 core-bank 目录里的真实文件名跑一遍合并：一个都不许丢。

        官方发行包只含代码（``plugin.json`` / ``LICENSE`` / ``dist/*``），
        题库、备份、灌库报告与几十张题目配图都不在包里，靠合并语义保住；
        万一包里带了同名 ``bank.db``（空壳种子库），则必须以旧的为准。
        """
        bank_dir = Path(__file__).resolve().parents[1] / "plugins" / "org.jiuzhang.core-bank" / "bank"
        if not bank_dir.is_dir():
            self.skipTest("本机没有 core-bank 的 bank/ 目录")
        real_names = sorted(item.relative_to(bank_dir).as_posix()
                            for item in bank_dir.rglob("*") if item.is_file())
        self.assertIn("bank.db", real_names)
        self.assertTrue(any(name.startswith("assets/") for name in real_names),
                        "core-bank 应有题目配图目录")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local = root / "local"
            staged = root / "staged"
            for name in real_names + ["plugin.json", "LICENSE", "dist/plugin.js"]:
                path = local / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("本机内容", encoding="utf-8")
            for name in ("plugin.json", "LICENSE", "dist/plugin.js", "bank.db"):
                path = staged / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("新包内容", encoding="utf-8")

            kept = plugin_update._preserve_local_files(local, staged)

            for name in real_names:
                self.assertTrue((staged / name).is_file(), f"{name} 更新后会丢失")
                self.assertEqual((staged / name).read_text(encoding="utf-8"), "本机内容",
                                 f"{name} 的内容被新包顶掉了")
            self.assertIn("bank.db", kept["data_overridden"])
            self.assertEqual((staged / "plugin.json").read_text(encoding="utf-8"), "新包内容")
            self.assertEqual((staged / "dist" / "plugin.js").read_text(encoding="utf-8"), "新包内容")

    def test_04_data_whitelist_covers_the_database_and_backup_suffixes(self):
        for name in ("bank.db", "bank.db-wal", "bank.db-shm", "jiuzhang.sqlite3",
                     "bank.db.pre-v082.bak", "download.part", "migration_report.json"):
            self.assertTrue(plugin_update._is_data_file(Path(name)), f"{name} 必须按数据文件办")
        for name in ("plugin.json", "dist/plugin.js", "LICENSE", "plugin.css", "schema.sql"):
            self.assertFalse(plugin_update._is_data_file(Path(name)), f"{name} 是代码，不该按数据办")


class UpdateHttpTest(unittest.TestCase):
    """五个更新端点的真机契约：令牌、只读检查、批量热更、数据必保、续更与底座更新守卫。

    索引用本机 127.0.0.1 上的假服务器发（离线、确定），绝不打公网。
    """

    HOST_VERSION = "99.0.0"

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.plugins_dir = cls.root / "plugins"
        cls.data_dir = cls.root / "data"
        cls.plugins_dir.mkdir()
        cls.data_dir.mkdir()

        cls.plugin_zip = build_zip("2.0.0")
        cls.host_zip = build_host_zip(cls.HOST_VERSION)
        cls.bind_index_port()
        cls.index_body = json.dumps({
            "index_version": "1.0",
            "name": "本机测试索引",
            "updated_at": "2026-10-23T00:00:00+08:00",
            "entries": [
                {"id": PLUGIN_ID, "name": "更新契约测试插件", "version": "2.0.0",
                 "zip_url": cls.url_of("/pkg.zip"), "mirrors": [], "description": "",
                 "min_host_version": ""},
                {"id": "org.jiuzhang.future", "name": "要新底座", "version": "3.0.0",
                 "zip_url": cls.url_of("/pkg.zip"), "mirrors": [], "description": "",
                 "min_host_version": "999.0.0"},
            ],
            "host": {"version": cls.HOST_VERSION, "zip_url": cls.url_of("/host.zip"),
                     "mirrors": [], "notes": "测试用底座新版本"},
        }, ensure_ascii=False).encode("utf-8")

        cls.serve()
        cls.boot_server()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.stop_server()
        if cls.httpd is not None:
            cls.httpd.shutdown()
            cls.httpd.server_close()
        cls.tmp.cleanup()

    @classmethod
    def url_of(cls, path: str) -> str:
        return f"http://127.0.0.1:{cls.index_port}{path}"

    @classmethod
    def bind_index_port(cls) -> None:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            cls.index_port = int(sock.getsockname()[1])

    @classmethod
    def serve(cls) -> None:
        import http.server

        payloads = {"/plugins.json": ("application/json", cls.index_body),
                    "/pkg.zip": ("application/zip", cls.plugin_zip),
                    "/host.zip": ("application/zip", cls.host_zip)}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802 - 标准库签名
                item = payloads.get(self.path)
                if item is None:
                    self.send_error(404)
                    return
                media, body = item
                self.send_response(200)
                self.send_header("Content-Type", media)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):  # 静音
                pass

        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", cls.index_port), Handler)
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def boot_server(cls) -> None:
        import subprocess
        import sys
        import time
        import urllib.error
        import urllib.request

        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = cls.data_dir.as_posix()
        env["JZO_PLUGINS_DIR"] = cls.plugins_dir.as_posix()
        env["JZO_LOCAL_TOKEN"] = "update-http-token"
        repo = Path(__file__).resolve().parents[1]
        log_path = cls.root / "server.log"
        cls.log_handle = open(log_path, "wb")
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
             "--port", str(cls.port), "--log-level", "info"],
            cwd=str(repo), env=env, stdout=cls.log_handle, stderr=subprocess.STDOUT,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 25
        while time.time() < deadline:
            if cls.process.poll() is not None:
                raise RuntimeError("服务提前退出：\n" + log_path.read_text(encoding="utf-8", errors="replace"))
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("服务未在 25 秒内就绪")

    @classmethod
    def stop_server(cls) -> None:
        if getattr(cls, "process", None) is not None and cls.process.poll() is None:
            cls.process.terminate()
            try:
                cls.process.wait(timeout=10)
            except Exception:
                cls.process.kill()
        if getattr(cls, "log_handle", None) is not None:
            cls.log_handle.close()

    def call(self, method: str, path: str, body: dict | None = None, token: str = "update-http-token"):
        import urllib.error
        import urllib.request

        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", token)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", "replace")
            exc.close()
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, raw

    def seed_local(self, version: str = "1.0.0", plugin_id: str = PLUGIN_ID,
                   with_data: bool = True) -> Path:
        destination = self.plugins_dir / plugin_id
        if destination.exists():
            import shutil
            shutil.rmtree(destination)
        (destination / "dist").mkdir(parents=True)
        (destination / "plugin.json").write_text(
            json.dumps(manifest(version, plugin_id=plugin_id), ensure_ascii=False), encoding="utf-8")
        (destination / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
        (destination / "dist" / "plugin.js").write_text(f"console.log('v{version}');", encoding="utf-8")
        if with_data:
            (destination / "bank").mkdir(exist_ok=True)
            (destination / "bank" / "bank.db").write_text("老师的真题库", encoding="utf-8")
            (destination / "bank" / "assets").mkdir(exist_ok=True)
            (destination / "bank" / "assets" / "figure.jpg").write_text("题目配图", encoding="utf-8")
        return destination

    def test_01_every_write_endpoint_demands_the_token(self):
        for method, path, body in (("POST", "/api/plugins/update/check", {}),
                                   ("POST", "/api/plugins/update/apply", {"all": True}),
                                   ("GET", "/api/plugins/update/pending", None),
                                   ("POST", "/api/plugins/update/pending-clear", {}),
                                   ("POST", "/api/plugins/update/host-apply", {})):
            status, _ = self.call(method, path, body, token="")
            self.assertEqual(status, 401, f"{method} {path} 没带令牌居然放行了")
            status, _ = self.call(method, path, body, token="wrong-token")
            self.assertEqual(status, 401, f"{method} {path} 令牌错了居然放行了")

    def test_02_check_without_a_cached_index_refuses_to_go_online(self):
        """没有缓存又不给 url 时只能 409：底座绝不自己出网。"""
        status, body = self.call("POST", "/api/plugins/update/check", {})
        self.assertEqual(status, 409)
        self.assertIn("不会自己出网", json.dumps(body, ensure_ascii=False))

    def test_03_check_reports_plugins_and_host(self):
        self.seed_local("1.0.0")
        self.seed_local("1.0.0", "org.jiuzhang.future", with_data=False)
        status, body = self.call("POST", "/api/plugins/update/check",
                                 {"url": self.url_of("/plugins.json")})
        self.assertEqual(status, 200)
        rows = {row["id"]: row for row in body["plugins"]}
        self.assertEqual(rows[PLUGIN_ID]["state"], "update_available")
        self.assertEqual(rows[PLUGIN_ID]["remote_version"], "2.0.0")
        self.assertEqual(rows["org.jiuzhang.future"]["state"], "incompatible")
        self.assertIn("需先更新底座", rows["org.jiuzhang.future"]["reason"])
        self.assertTrue(body["host"]["update_available"])
        self.assertEqual(body["host"]["available"], self.HOST_VERSION)
        self.assertEqual(body["index_source"], "fetched")
        self.assertEqual(body["summary"]["update_available"], 1)
        self.assertEqual(body["summary"]["incompatible"], 1)

    def test_04_second_check_runs_off_the_cache(self):
        status, body = self.call("POST", "/api/plugins/update/check", {})
        self.assertEqual(status, 200)
        self.assertEqual(body["index_source"], "cache")
        self.assertEqual(body["host"]["available"], self.HOST_VERSION,
                         "缓存必须带上 host 块，否则离线检查会漏掉底座更新")

    def test_05_apply_updates_code_and_preserves_the_teachers_data(self):
        destination = self.seed_local("1.0.0")
        status, body = self.call("POST", "/api/plugins/update/apply", {"ids": [PLUGIN_ID]})
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in body["updated"]], [PLUGIN_ID])
        self.assertEqual(body["updated"][0]["to"], "2.0.0")
        self.assertEqual(body["failed"], [])
        self.assertEqual(json.loads((destination / "plugin.json").read_text(encoding="utf-8"))["version"],
                         "2.0.0")
        self.assertEqual((destination / "dist" / "plugin.js").read_text(encoding="utf-8"),
                         "console.log('v2.0.0');")
        self.assertEqual((destination / "bank" / "bank.db").read_text(encoding="utf-8"), "老师的真题库")
        self.assertEqual((destination / "bank" / "assets" / "figure.jpg").read_text(encoding="utf-8"),
                         "题目配图")

    def test_06_incompatible_entries_are_skipped_never_applied(self):
        future_dir = self.plugins_dir / "org.jiuzhang.future"
        status, body = self.call("POST", "/api/plugins/update/apply", {"all": True})
        self.assertEqual(status, 200)
        self.assertEqual(body["updated"], [], "已是最新的没有可更新的")
        skipped = {row["id"]: row for row in body["skipped"]}
        self.assertIn("org.jiuzhang.future", skipped)
        self.assertEqual(skipped["org.jiuzhang.future"]["state"], "incompatible")
        self.assertEqual(json.loads((future_dir / "plugin.json").read_text(encoding="utf-8"))["version"],
                         "1.0.0", "不兼容的条目绝不允许覆盖本地代码")
        self.assertEqual((future_dir / "dist" / "plugin.js").read_text(encoding="utf-8"),
                         "console.log('v1.0.0');")

    def test_07_apply_validates_its_input(self):
        status, _ = self.call("POST", "/api/plugins/update/apply", {})
        self.assertEqual(status, 400)
        status, _ = self.call("POST", "/api/plugins/update/apply", {"ids": "不是数组"})
        self.assertEqual(status, 400)
        status, _ = self.call("POST", "/api/plugins/update/apply", {"ids": ["org.jiuzhang.没装"]})
        self.assertEqual(status, 404)

    def test_08_pending_roundtrip(self):
        status, body = self.call("GET", "/api/plugins/update/pending")
        self.assertEqual(status, 200)
        self.assertEqual(body["pending"], [])
        self.assertIn("last_resume", body)

        (self.data_dir / "update_state.json").write_text(json.dumps(
            {"host_version": "99.0.0", "written_at": "2026-10-23T00:00:00+08:00",
             "pending": [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0", "zip_path": "x"}]}),
            encoding="utf-8")
        status, body = self.call("GET", "/api/plugins/update/pending")
        self.assertEqual([row["id"] for row in body["pending"]], [PLUGIN_ID])

        status, body = self.call("POST", "/api/plugins/update/pending-clear", {})
        self.assertEqual(status, 200)
        self.assertTrue(body["cleared"])
        self.assertFalse((self.data_dir / "update_state.json").exists())

    def test_09_host_apply_prepares_but_refuses_to_launch_on_a_dev_worktree(self):
        status, body = self.call("POST", "/api/plugins/update/host-apply", {})
        self.assertEqual(status, 200)
        self.assertFalse(body["launched"])
        self.assertEqual(body["version"], self.HOST_VERSION)
        self.assertEqual(body["excluded_dirs"], list(HOST_EXCLUDED_DIRS))
        script = Path(body["script_path"])
        self.assertTrue(script.is_file(), "一次性 update.bat 应已生成")
        text = script.read_text(encoding="utf-8")
        for name in HOST_EXCLUDED_DIRS:
            self.assertIn(name, text, f"{name}/ 必须出现在排除清单里")
        self.assertFalse(body["launchable"], "服务端跑在真仓库工作树上，不该允许自动覆盖重启")

        status, body = self.call("POST", "/api/plugins/update/host-apply", {"launch": True})
        self.assertEqual(status, 409)
        detail = json.dumps(body, ensure_ascii=False)
        self.assertIn("dev_worktree", detail)
        self.assertEqual(self.process.poll(), None, "底座进程绝不能被测试杀掉")

    def test_10_resume_at_boot_completes_the_previous_batch_offline(self):
        """重启续更：只吃本机状态文件与已下载的包，不出网。"""
        self.seed_local("1.0.0")
        staged = self.root / "staged-pkg.zip"
        staged.write_bytes(build_zip("2.0.0"))
        (self.data_dir / "update_state.json").write_text(json.dumps(
            {"host_version": "", "written_at": "2026-10-23T00:00:00+08:00",
             "pending": [{"id": PLUGIN_ID, "from": "1.0.0", "to": "2.0.0",
                          "zip_path": staged.as_posix()}]}), encoding="utf-8")

        self.stop_server()
        self.boot_server()

        status, body = self.call("GET", "/api/plugins/update/pending")
        self.assertEqual(status, 200)
        last = body["last_resume"]
        self.assertTrue(last["ran"])
        self.assertTrue(last["had_pending"])
        self.assertEqual([row["id"] for row in last["resumed"]], [PLUGIN_ID])
        self.assertEqual(last["failed"], [])
        self.assertEqual(json.loads((self.plugins_dir / PLUGIN_ID / "plugin.json")
                                    .read_text(encoding="utf-8"))["version"], "2.0.0")
        self.assertEqual((self.plugins_dir / PLUGIN_ID / "bank" / "bank.db").read_text(encoding="utf-8"),
                         "老师的真题库", "续更同样必须保住题库")
        self.assertEqual(body["pending"], [], "补齐跑完就清状态")
        self.assertFalse(staged.exists())

    def test_11_server_log_carries_the_resume_lines(self):
        raw = (self.root / "server.log").read_bytes()
        # 服务端子进程按控制台编码（本机 cp936）写日志，两种编码都试一遍再断言
        text = raw.decode("utf-8", "replace")
        if "续更完成" not in text:
            text = raw.decode("gbk", "replace")
        self.assertIn("续更完成", text, "更新记录必须逐行落在日志里（极致静默、不弹窗）")
        self.assertIn(f"{PLUGIN_ID} 1.0.0", text)
        self.assertIn("2.0.0", text)


class UpdateUiWiringTest(unittest.TestCase):
    """设置页更新面板与宿主回流链路的接线契约（静态断言，真机行为由探针钉住）。"""

    @classmethod
    def setUpClass(cls) -> None:
        static = Path(__file__).resolve().parents[1] / "static"
        cls.html = (static / "settings.html").read_text(encoding="utf-8")
        cls.js = (static / "js" / "settings.js").read_text(encoding="utf-8")
        cls.css = (static / "css" / "settings.css").read_text(encoding="utf-8")
        cls.workspace_js = (static / "js" / "workspace.js").read_text(encoding="utf-8")
        cls.stage_js = (static / "js" / "stage.js").read_text(encoding="utf-8")

    def test_01_panel_has_every_control_the_spec_names(self):
        for element_id in ("upCheckBtn", "upAllBtn", "upStatus", "upList", "upHost",
                           "upHostText", "upHostBtn", "upLog"):
            self.assertIn(f'id="{element_id}"', self.html, f"更新面板缺少 {element_id}")
        self.assertIn('id="upLog" role="log"', self.html, "日志区必须是 aria live 的 log 区")

    def test_02_batch_button_starts_disabled(self):
        """【一键更新全部插件】默认禁用：检查出可更新条目之前一次批量下载都不许发生。"""
        self.assertRegex(self.html, r'id="upAllBtn"[^>]*disabled')

    def test_03_panel_states_the_no_silent_network_rule(self):
        self.assertIn("不会", self.html)
        self.assertIn("原地不动", self.html, "必须写明题库与配图不受更新影响")
        self.assertIn("需先更新底座", self.html)

    def test_04_all_five_endpoints_are_wired_through_the_token_helper(self):
        for path in ("/api/plugins/update/check", "/api/plugins/update/apply",
                     "/api/plugins/update/pending", "/api/plugins/update/host-apply"):
            self.assertIn(path, self.js, f"设置页没有接 {path}")
        # pending-clear 是给用户「作废续更待办」用的后端能力，界面上不给按钮：
        # 底座补齐跑完自己会清，多一个按钮只多一个误点口子。端点本身由下面的
        # 路由断言钉住（见 UpdateHttpTest.test_01 的 401 与 test_08 的清空）。
        self.assertNotIn('apiCall("/api/plugins/update/pending-clear", "POST"', self.js)
        for call in ("apiCall(\"/api/plugins/update/check\"", "apiCall(\"/api/plugins/update/apply\"",
                     "apiCall(\"/api/plugins/update/host-apply\""):
            self.assertIn(call, self.js, f"{call} 必须走带令牌的 apiCall")

    def test_04b_five_update_routes_are_registered_and_token_gated(self):
        from app.main import app

        paths = app.openapi()["paths"]
        for path in ("/api/plugins/update/check", "/api/plugins/update/apply",
                     "/api/plugins/update/pending", "/api/plugins/update/pending-clear",
                     "/api/plugins/update/host-apply"):
            self.assertIn(path, paths, f"缺少路由 {path}")
        source = (Path(__file__).resolve().parents[1] / "app" / "api" / "plugins.py") \
            .read_text(encoding="utf-8")
        update_section = source.split("双轨更新（PLUGIN_SPEC §1.7）", 1)[1]
        self.assertEqual(update_section.count("dependencies=[Depends(require_write_token)]"), 5,
                         "五个更新端点必须全部带写令牌")
        self.assertNotIn("async def check_updates_endpoint", update_section)
        self.assertNotIn("async def apply_updates_endpoint", update_section)
        self.assertNotIn("async def host_update_endpoint", update_section)

    def test_05_no_polling_no_timer_driven_network(self):
        """出网铁律：设置页里一个定时器轮询都不许有。"""
        self.assertNotIn("setInterval", self.js)
        self.assertNotIn("requestIdleCallback", self.js)
        for path in ("/api/plugins/update/check", "/api/plugins/update/apply",
                     "/api/plugins/update/host-apply"):
            self.assertNotIn("setTimeout(function () { apiCall", self.js)

    def test_06_incompatible_rows_render_a_disabled_button(self):
        self.assertIn('row.state === "incompatible"', self.js)
        self.assertIn("blocked.disabled = true", self.js)
        self.assertIn("需先更新底座", self.js)

    def test_07_host_restart_needs_two_explicit_clicks(self):
        """第一下只下载校验并生成脚本，第二下才交接重启——不给误点炸掉会话的机会。"""
        self.assertIn("upHostArmed", self.js)
        self.assertIn('{ launch: true }', self.js)
        self.assertIn("确认：覆盖并重启", self.js)
        self.assertIn("开发工作树不自动重启", self.js)

    def test_08_log_lines_carry_a_tone_and_text_not_only_colour(self):
        self.assertIn('li.setAttribute("data-tone"', self.js)
        self.assertIn(".up-log-line[data-tone=\"ok\"]", self.css)
        self.assertIn(".up-log-line[data-tone=\"down\"]", self.css)
        self.assertIn(".up-log-line[data-tone=\"warn\"]", self.css)
        self.assertIn("max-height", self.css.split(".up-log {", 1)[1].split("}", 1)[0])

    def test_09_settings_page_notifies_the_host_after_an_update(self):
        self.assertIn('jzo: "plugins.updated"', self.js)
        self.assertIn("window.parent.postMessage", self.js)
        self.assertIn("window.location.origin", self.js)

    def test_10_workspace_reloads_plugins_and_publishes_on_the_bus(self):
        self.assertIn('data.jzo !== "plugins.updated"', self.workspace_js)
        self.assertIn('event.origin !== window.location.origin', self.workspace_js)
        self.assertIn('"plugin.updated"', self.workspace_js)
        self.assertIn("window.JzoBus.emit(\"plugin.updated\"", self.workspace_js)
        self.assertIn("window.JzoStage.rehydratePlugin(id)", self.workspace_js)
        self.assertIn("loadPlugins({ announce: false })", self.workspace_js)

    def test_11_stage_rehydrates_only_the_live_canvas_and_forwards_the_event(self):
        self.assertIn("function rehydratePlugin(pluginId)", self.stage_js)
        self.assertIn("rehydratePlugin: rehydratePlugin", self.stage_js, "必须挂到 window.JzoStage 上")
        self.assertIn('hibernate(tab, "plugin.updated")', self.stage_js)
        self.assertIn("tab.key === activeKey", self.stage_js)
        self.assertIn('bus.on("plugin.updated"', self.stage_js)

    def test_12_update_writes_never_touch_the_workspace_database(self):
        """前端也不许出现「更新会改题库」的暗示：日志措辞只讲代码与本机文件。"""
        self.assertIn("保住本机文件", self.js)
        self.assertNotIn("/api/workspaces", self.js.split("双轨更新", 1)[1].split("左菜单", 1)[0])


def _free_port() -> int:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    unittest.main()
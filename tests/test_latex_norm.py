"""记号标准字典整机库（2.21.0 卡 §1/§6）阶段A一案：结构/迁移/四态/备份机器层。

运行：.venv/Scripts/python.exe -m unittest tests.test_latex_norm
隔离：JZO_DATA_DIR 指临时目录，整机库与备份全在副本里，不碰用户 data/。
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.core import config
from app.core.backup import service as backup
from app.core.backup.package.manifest import build_manifest, snapshot_workspace
from app.core.backup.restore import apply_restore, preview_view
from app.core.content import latex_norm


def _seed_entry(con, key="le", name="小于等于", category="关系不等",
                codes=(("\\le", "ISO/GB-T"), ("\\leqslant", "ISO/GB-T")),
                factory_index=0):
    """手插一条闭集条目＋变体行（种子导入是阶段B的活，这里直插测存储语义）。"""
    con.execute(
        "INSERT INTO norm_entries (entry_key, name, category, factory_default_variant_id)"
        " VALUES (?, ?, ?, 0)", (key, name, category))
    ids = []
    for order, (code, label) in enumerate(codes, start=1):
        cur = con.execute(
            "INSERT INTO norm_variants (entry_key, latex_code, source_label, row_order)"
            " VALUES (?, ?, ?, ?)", (key, code, label, order))
        ids.append(cur.lastrowid)
    con.execute("UPDATE norm_entries SET factory_default_variant_id = ? WHERE entry_key = ?",
                (ids[factory_index], key))
    return ids


class NormStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.data.mkdir()
        self._old = os.environ.get("JZO_DATA_DIR")
        os.environ["JZO_DATA_DIR"] = str(self.data)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = self._old
        self.tmp.cleanup()

    def test_01_fresh_schema_version_and_wal(self):
        con = latex_norm.connect()
        try:
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertTrue({"norm_entries", "norm_variants", "norm_corrections"} <= tables)
            self.assertEqual(int(con.execute("PRAGMA user_version").fetchone()[0]), 1)
            self.assertEqual(con.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        finally:
            con.close()
        self.assertEqual(config.settings.latex_norm_db_path, self.data / "latex_norm.db")

    def test_02_higher_version_rejected_and_connection_closed(self):
        con = latex_norm.connect()
        con.execute("PRAGMA user_version = 99")
        con.close()
        with self.assertRaises(latex_norm.NormError):
            latex_norm.connect()
        # 连接已关：Windows 上库文件可删（pending 先例的坑）
        (self.data / "latex_norm.db").unlink()

    def test_03_migration_backup_and_rollback_file(self):
        path = self.data / "latex_norm.db"
        old = sqlite3.connect(path)
        old.execute("CREATE TABLE legacy_marker (x INTEGER)")
        old.execute("INSERT INTO legacy_marker VALUES (42)")
        old.commit()
        old.close()
        con = latex_norm.connect()
        try:
            tables = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertIn("norm_entries", tables)
            self.assertIn("legacy_marker", tables)  # 迁移不删旧对象
        finally:
            con.close()
        bak = Path(str(path) + ".pre-v1.bak")
        self.assertTrue(bak.is_file())
        old = sqlite3.connect(bak)
        try:
            self.assertEqual(old.execute("SELECT x FROM legacy_marker").fetchone()[0], 42)
            names = {r[0] for r in old.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertNotIn("norm_entries", names)  # 备份是迁移前形状，可整库回退
        finally:
            old.close()

    def test_04_transaction_injected_failure_rolls_back(self):
        with self.assertRaises(RuntimeError):
            with latex_norm.transaction() as con:
                _seed_entry(con)
                raise RuntimeError("注入失败")
        self.assertEqual(latex_norm.list_entries(), [])

    def test_05_choose_reset_roundtrip_and_persistence(self):
        with latex_norm.transaction() as con:
            ids = _seed_entry(con)
        entry = latex_norm.get_entry("le")
        self.assertEqual(entry["effective_default_variant_id"], ids[0])
        self.assertIsNone(entry["chosen_default_variant_id"])
        latex_norm.choose_default("le", ids[1])
        entry = latex_norm.get_entry("le")  # 重开连接仍在
        self.assertEqual(entry["chosen_default_variant_id"], ids[1])
        self.assertEqual(entry["effective_default_variant_id"], ids[1])
        self.assertEqual(entry["factory_default_variant_id"], ids[0])  # 出厂永不动
        latex_norm.reset_default("le")
        entry = latex_norm.get_entry("le")
        self.assertIsNone(entry["chosen_default_variant_id"])
        self.assertEqual(entry["effective_default_variant_id"], ids[0])

    def test_06_choose_rejects_foreign_variant_and_missing_entry(self):
        with latex_norm.transaction() as con:
            ids = _seed_entry(con)
            _seed_entry(con, key="ge", name="大于等于", codes=(("\\ge", "ISO/GB-T"),))
        with self.assertRaises(latex_norm.NormError):
            latex_norm.choose_default("le", ids[0] + 100)
        with self.assertRaises(latex_norm.NormError):
            latex_norm.choose_default("nope", ids[0])
        with self.assertRaises(latex_norm.NormError):
            latex_norm.reset_default("nope")

    def test_07_unknown_dedup_hit_plus_one(self):
        first = latex_norm.record_unknown("\\leqq")
        again = latex_norm.record_unknown("\\leqq")
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(again["hit_count"], 2)
        self.assertEqual(again["status"], "pending")
        self.assertEqual(again["first_seen"], first["first_seen"])
        self.assertEqual(len(latex_norm.list_corrections()), 1)
        with self.assertRaises(latex_norm.NormError):
            latex_norm.record_unknown("  ")

    def test_08_rejected_blacklist_never_asks_again(self):
        latex_norm.record_unknown("\\bad")
        latex_norm.decide_correction("\\bad", "rejected")
        row = latex_norm.record_unknown("\\bad")
        self.assertEqual(row["status"], "rejected")
        self.assertEqual(row["hit_count"], 2)
        self.assertEqual(latex_norm.confirmed_corrections(), {})

    def test_09_archived_sink_and_resurrect(self):
        latex_norm.record_unknown("\\stale")
        sunk = latex_norm.sweep_stale("9999-12-31T00:00:00+08:00")
        self.assertEqual(sunk, 1)
        self.assertEqual(latex_norm.list_corrections("archived")[0]["raw_code"], "\\stale")
        row = latex_norm.record_unknown("\\stale")
        self.assertEqual(row["status"], "pending")  # 再犯不再「久未命中」
        self.assertEqual(row["hit_count"], 2)

    def test_10_decide_confirmed_requires_target_and_pending_only(self):
        latex_norm.record_unknown("\\leqq")
        with self.assertRaises(latex_norm.NormError):
            latex_norm.decide_correction("\\leqq", "confirmed", "")
        with self.assertRaises(latex_norm.NormError):
            latex_norm.decide_correction("\\leqq", "archived")
        with self.assertRaises(latex_norm.NormError):
            latex_norm.decide_correction("\\missing", "rejected")
        row = latex_norm.decide_correction("\\leqq", "confirmed", "\\le")
        self.assertEqual(row["status"], "confirmed")
        self.assertEqual(row["target_code"], "\\le")
        self.assertTrue(row["decided_at"])
        with self.assertRaises(latex_norm.NormError):
            latex_norm.decide_correction("\\leqq", "rejected")  # 已裁决不可再翻

    def test_11_pending_sorted_by_hits_and_counts(self):
        latex_norm.record_unknown("\\low")
        for _ in range(3):
            latex_norm.record_unknown("\\high")
        pending = latex_norm.list_corrections("pending")
        self.assertEqual([r["raw_code"] for r in pending], ["\\high", "\\low"])
        latex_norm.decide_correction("\\high", "rejected")
        counts = latex_norm.correction_counts()
        self.assertEqual(counts["pending"], 1)
        self.assertEqual(counts["rejected"], 1)
        self.assertEqual(counts["confirmed"], 0)
        self.assertEqual(counts["archived"], 0)
        with self.assertRaises(latex_norm.NormError):
            latex_norm.list_corrections("bogus")

    def test_12_rewrite_aliases_empty_db_falls_back(self):
        self.assertIsNone(latex_norm.rewrite_aliases())

    def test_13_rewrite_aliases_follow_choice_and_render_flag(self):
        with latex_norm.transaction() as con:
            ids = _seed_entry(con)
            con.execute("UPDATE norm_variants SET render_supported = 0, render_note = 'MathJax 不认'"
                        " WHERE id = ?", (ids[1],))
        self.assertEqual(latex_norm.rewrite_aliases(), {})  # 不可渲染变体不进改写
        with latex_norm.transaction() as con:
            con.execute("UPDATE norm_variants SET render_supported = 1 WHERE id = ?", (ids[1],))
        self.assertEqual(latex_norm.rewrite_aliases(), {"leqslant": "le"})
        latex_norm.choose_default("le", ids[1])
        self.assertEqual(latex_norm.rewrite_aliases(), {"le": "leqslant"})  # 选择驱动方向
        latex_norm.reset_default("le")
        self.assertEqual(latex_norm.rewrite_aliases(), {"leqslant": "le"})

    def test_14_confirmed_only_participates(self):
        latex_norm.record_unknown("\\a")
        latex_norm.record_unknown("\\b")
        latex_norm.record_unknown("\\c")
        latex_norm.decide_correction("\\a", "confirmed", "\\alpha")
        latex_norm.decide_correction("\\b", "rejected")
        latex_norm.sweep_stale("9999-12-31T00:00:00+08:00")  # \c → archived
        self.assertEqual(latex_norm.confirmed_corrections(), {"\\a": "\\alpha"})


class NormBackupMachineLayerTest(unittest.TestCase):
    """备份机器层：进包必选、恢复落根 data、工作区扫描不双收、导入不携带。"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.data.mkdir()
        self._old = os.environ.get("JZO_DATA_DIR")
        os.environ["JZO_DATA_DIR"] = str(self.data)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("JZO_DATA_DIR", None)
        else:
            os.environ["JZO_DATA_DIR"] = self._old
        self.tmp.cleanup()

    def _make_machine_db(self, marker=42):
        with latex_norm.transaction() as con:
            con.execute("CREATE TABLE IF NOT EXISTS marker (x INTEGER)")
            con.execute("DELETE FROM marker")
            con.execute("INSERT INTO marker VALUES (?)", (marker,))

    def test_01_plan_includes_machine_once_and_category_required(self):
        self._make_machine_db()
        plan = backup.backup_file_plan("default")
        rels = [rel for rel, _ in plan]
        self.assertEqual(rels.count("machine/latex_norm.db"), 1)
        self.assertNotIn("latex_norm.db", rels)  # default 根扫描不双收
        self.assertEqual(backup.category_of("machine/latex_norm.db"), ("machine", True))
        walked = [p.name for p in backup.iter_workspace_files("default")]
        self.assertNotIn("latex_norm.db", walked)

    def test_02_machine_target_bounds(self):
        self.assertEqual(backup.machine_target("machine/latex_norm.db"),
                         (self.data / "latex_norm.db").resolve())
        self.assertEqual(backup.overlay_target("machine/latex_norm.db"),
                         (self.data / "latex_norm.db").resolve())
        with self.assertRaises(backup.BackupError):
            backup.machine_target("machine/evil.db")
        with self.assertRaises(backup.BackupError):
            backup.machine_target("ws/latex_norm.db")

    def test_03_snapshot_manifest_preview_groups(self):
        self._make_machine_db()
        stage, _manifest = snapshot_workspace("default")
        self.assertTrue((stage / "machine" / "latex_norm.db").is_file())
        manifest = build_manifest("default", stage)
        entry = next(f for f in manifest["files"] if f["path"] == "machine/latex_norm.db")
        self.assertEqual(entry["category"], "machine")
        self.assertTrue(entry["required"])
        preview = preview_view(manifest)
        self.assertEqual(preview["groups"]["machine"], ["machine/latex_norm.db"])
        self.assertIn("machine/latex_norm.db", preview["required"])

    def test_04_apply_restore_roundtrip_machine_db(self):
        self._make_machine_db(marker=42)
        stage, _ = snapshot_workspace("default")
        manifest = build_manifest("default", stage)
        #  live 库被改坏（模拟误删/旧包覆盖前的状态）
        self._make_machine_db(marker=999)
        selected = [f["path"] for f in manifest["files"] if f["required"]]
        self.assertIn("machine/latex_norm.db", selected)
        result = apply_restore("default", stage, selected, manifest)
        self.assertIn("machine/latex_norm.db", result["restored"])
        con = sqlite3.connect(self.data / "latex_norm.db")
        try:
            self.assertEqual(con.execute("SELECT x FROM marker").fetchone()[0], 42)
        finally:
            con.close()

    def test_05_machine_db_outside_workspace_import_path(self):
        # 工作区导入只落 workspaces/<wsid>/banks/<provider>.db（workspaces.py:363-369），
        # 整机库在根 data，结构上不可能被携带。
        machine = config.settings.latex_norm_db_path
        self.assertEqual(machine.parent, self.data)
        self.assertNotIn("workspaces", machine.parts)


if __name__ == "__main__":
    unittest.main()
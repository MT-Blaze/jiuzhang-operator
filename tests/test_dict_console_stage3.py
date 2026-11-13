"""数据字典控制台 · 阶段三契约：折叠树联动与 v6→v7 迁移。

钉住六件事：
1. 迁移正反向：新建即 v7 且桥表带 sort_order；rollback 降回 v6 丢列，
   再次 build_engine 原地升回 v7，``.pre-v7.bak`` 落盘、行数不变、逐组 0..n-1；
2. 章节树：单表读出 + Python 组装层级，未知教材换 ConsoleLookupError；
3. 关联读：章节知识点 / 知识点考向 / 考向辅助标签都按桥表 sort_order 出参；
4. 关联写：新增考向继承学科、挂标签排末尾、重复冲突、移除只解关联；
5. 拖拽排序：完整清单落库真持久化，集合不一致 / 非整数一律 ValueError；
6. 删除防呆：排除当前知识点关联后仍被引用抛 ReferencedError（API 换 409），
   联动写路由全部带一次性令牌，红线（行数 / innerHTML / f-string SQL）不破。

运行：``.venv/Scripts/python.exe -m unittest tests.test_dict_console_stage3 -v``
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
from app.bank_engine import (  # noqa: E402
    builder,
    dao_console,
    dao_linkage,
    migrate_v10,
    migrate_v11,
    migrate_v12,
    migrate_v13,
    migrate_v14,
    migrate_v7,
    migrate_v8,
    migrate_v9,
    seeding,
    service,
)
from app.bank_engine.models import (  # noqa: E402
    Chapter,
    ChapterNode,
    ExamDirection,
    LinkedKnowledgePoint,
    ReferenceHit,
)

SCHEMA = PLUGIN_SOURCE_DIR / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"
CONSOLE_DIR = ROOT / "static" / "js" / "dict_console"


class MigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="dict-console-s3-mig-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def _columns(self, table: str) -> set[str]:
        with service.session(self.db_path) as conn:
            return {str(row[1]) for row in conn.execute("PRAGMA table_info(" + table + ")")}

    def _version(self) -> int:
        with service.session(self.db_path) as conn:
            return int(conn.execute("PRAGMA user_version").fetchone()[0])

    def test_fresh_build_is_v14_with_versions(self) -> None:
        self.assertEqual(self._version(), 14)
        for table, _, _ in migrate_v7.ORDERED_MAPS:
            self.assertIn("sort_order", self._columns(table))
        self.assertIn("tikz_code", self._columns("question_images"))
        self.assertIn("version_id", self._columns("dim_textbooks"))
        self.assertIn("volume_name", self._columns("dim_textbooks"))
        self.assertNotIn("exam_subject", self._columns("exams"))
        self.assertIn("mock_round", self._columns("exams"))
        with service.session(self.db_path) as conn:
            migrate_v7.verify_sort_order(conn)
            migrate_v9.verify_versions(conn)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM dim_textbook_versions").fetchone()[0],
                seeding.EXPECTED_COUNTS["dim_textbook_versions"])
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM chapter_knowledge_map").fetchone()[0], 74)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM knowledge_exam_map").fetchone()[0], 200)

    def test_rollback_then_rebuild_upgrades_in_place(self) -> None:
        # 幂等备份可能已被其他用例提前落盘（v7 状态）；先清掉，让本次升级备份真正的 v6。
        backup = self.db_path.with_name(self.db_path.name + ".pre-v7.bak")
        if backup.exists():
            backup.unlink()
        with service.session(self.db_path) as conn:
            migrate_v14.rollback(conn)
            migrate_v13.rollback(conn)
            migrate_v12.rollback(conn)
            migrate_v11.rollback(conn)
            migrate_v10.rollback(conn)
            migrate_v9.rollback(conn)
            migrate_v8.rollback(conn)
            migrate_v7.rollback(conn)
        self.assertEqual(self._version(), 6)
        for table, _, _ in migrate_v7.ORDERED_MAPS:
            self.assertNotIn("sort_order", self._columns(table))
        self.assertNotIn("tikz_code", self._columns("question_images"))
        self.assertNotIn("version_id", self._columns("dim_textbooks"))
        report = builder.build_engine(db_path=self.db_path, schema=SCHEMA)
        self.assertFalse(report.created)
        self.assertEqual(self._version(), 14)
        for table, _, _ in migrate_v7.ORDERED_MAPS:
            self.assertIn("sort_order", self._columns(table))
        self.assertIn("tikz_code", self._columns("question_images"))
        self.assertIn("version_id", self._columns("dim_textbooks"))
        with service.session(self.db_path) as conn:
            migrate_v9.verify_versions(conn)
        self.assertTrue(backup.is_file())
        with service.session(backup) as conn:
            self.assertEqual(int(conn.execute("PRAGMA user_version").fetchone()[0]), 6)
        with service.session(self.db_path) as conn:
            migrate_v7.verify_sort_order(conn)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM chapter_knowledge_map").fetchone()[0], 74)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM knowledge_exam_map").fetchone()[0], 200)

    def test_backup_is_idempotent(self) -> None:
        with service.session(self.db_path) as conn:
            first = migrate_v7.backup_pre_v7(conn)
            mtime = first.stat().st_mtime_ns
            second = migrate_v7.backup_pre_v7(conn)
        self.assertEqual(first, second)
        self.assertEqual(first.stat().st_mtime_ns, mtime)

    def test_versions_are_pure_and_books_carry_volume(self) -> None:
        versions = service.textbook_versions(subject_id=2, db_path=self.db_path)
        names = [item.name for item in versions]
        self.assertTrue(
            {"人教A版", "人教版", "人教B版", "北师大版", "苏教版", "湘教版", "沪教版"}
            <= set(names)
        )
        for name in names:
            self.assertNotIn("必修", name)
            self.assertNotIn("选修", name)
            self.assertNotIn("·", name)
        book = next(item for item in versions if item.name == "人教A版")
        books = service.textbooks(version_id=book.id, db_path=self.db_path)
        self.assertEqual(
            [item.volume_name for item in books],
            [
                "必修第一册", "必修第二册", "选择性必修第一册",
                "选择性必修第二册", "选择性必修第三册",
            ],
        )

    def test_version_tree_groups_books_then_chapters(self) -> None:
        book = next(item for item in service.textbook_versions(
            subject_id=2, db_path=self.db_path) if item.name == "人教A版")
        books = service.linkage_version_tree(book.id, db_path=self.db_path)
        self.assertEqual(len(books), 5)
        for node in books:
            self.assertEqual(node.textbook.version_id, book.id)
        with_chapters = [node for node in books if node.chapters]
        self.assertEqual(len(with_chapters), 5)
        for node in with_chapters:
            self.assertTrue(all(
                chapter.chapter.textbook_id == node.textbook.id
                for chapter in node.chapters
            ))

    def test_version_tree_filters_books_by_stage_and_subject(self) -> None:
        version = next(item for item in service.textbook_versions(
            subject_id=2, db_path=self.db_path) if item.name == "人教版")
        all_books = service.linkage_version_tree(version.id, db_path=self.db_path)
        self.assertEqual(len(all_books), 18)
        junior = service.linkage_version_tree(
            version.id, stage="初中", subject_id=2, db_path=self.db_path)
        self.assertEqual({node.textbook.grade_id for node in junior}, {7, 8, 9})
        self.assertEqual(len(junior), 6)
        self.assertEqual(
            service.linkage_version_tree(
                version.id, stage="高中", subject_id=2, db_path=self.db_path), ())
        self.assertEqual(
            service.linkage_version_tree(
                version.id, stage="初中", subject_id=1, db_path=self.db_path), ())
        high = next(item for item in service.textbook_versions(
            subject_id=2, db_path=self.db_path) if item.name == "人教A版")
        high_books = service.linkage_version_tree(
            high.id, stage="高中", subject_id=2, db_path=self.db_path)
        self.assertEqual(len(high_books), 5)
        self.assertEqual(
            service.linkage_version_tree(
                high.id, stage="初中", subject_id=2, db_path=self.db_path), ())

    def test_backfill_matches_primary_key_order(self) -> None:
        with service.session(self.db_path) as conn:
            for table, group_col, member_col in migrate_v7.ORDERED_MAPS:
                rows = conn.execute(
                    "SELECT " + group_col + ", " + member_col + ", sort_order FROM " + table
                    + " ORDER BY " + group_col + ", " + member_col
                ).fetchall()
                seq: dict[int, int] = {}
                for row in rows:
                    group = int(row[0])
                    self.assertEqual(int(row[2]), seq.get(group, 0), table)
                    seq[group] = seq.get(group, 0) + 1


class LinkageServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="dict-console-s3-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)
        with service.session(cls.db_path) as conn:
            cls.chapter_id = int(conn.execute(
                "SELECT chapter_id FROM chapter_knowledge_map "
                "GROUP BY chapter_id HAVING COUNT(*) >= 2 ORDER BY chapter_id LIMIT 1"
            ).fetchone()[0])
            cls.textbook_id = int(conn.execute(
                "SELECT textbook_id FROM dim_textbook_chapters WHERE id = ?",
                (cls.chapter_id,),
            ).fetchone()[0])
            cls.direction_id = int(conn.execute(
                "SELECT exam_direction_id FROM knowledge_exam_map "
                "GROUP BY exam_direction_id HAVING COUNT(*) >= 2 "
                "ORDER BY exam_direction_id LIMIT 1"
            ).fetchone()[0])
            cls.point_id = int(conn.execute(
                "SELECT knowledge_point_id FROM knowledge_exam_map "
                "WHERE exam_direction_id = ? AND sort_order = 0",
                (cls.direction_id,),
            ).fetchone()[0])
            cls.secondary_point_id = int(conn.execute(
                "SELECT knowledge_point_id FROM knowledge_exam_map "
                "WHERE exam_direction_id = ? AND sort_order > 0 ORDER BY sort_order LIMIT 1",
                (cls.direction_id,),
            ).fetchone()[0])
            cls.other_point_id = int(conn.execute(
                "SELECT id FROM dim_knowledge_points WHERE id NOT IN "
                "(SELECT knowledge_point_id FROM knowledge_exam_map WHERE exam_direction_id = ?) "
                "ORDER BY id LIMIT 1",
                (cls.direction_id,),
            ).fetchone()[0])
            cls.empty_chapter_id = int(conn.execute(
                "SELECT id FROM dim_textbook_chapters WHERE id NOT IN "
                "(SELECT chapter_id FROM chapter_knowledge_map) ORDER BY id LIMIT 1"
            ).fetchone()[0])
            cls.empty_point_id = int(conn.execute(
                "SELECT id FROM dim_knowledge_points WHERE id NOT IN "
                "(SELECT knowledge_point_id FROM knowledge_exam_map WHERE sort_order = 0) "
                "ORDER BY id LIMIT 1"
            ).fetchone()[0])

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def _new_direction(self) -> ExamDirection:
        name = "联动测试考向_" + uuid.uuid4().hex[:8]
        direction = service.linkage_add_direction(self.point_id, name, db_path=self.db_path)
        self.addCleanup(self._purge_direction, direction.id)
        return direction

    def _purge_direction(self, direction_id: int) -> None:
        try:
            tags = service.linkage_direction_tags(direction_id, db_path=self.db_path)
        except dao_console.ConsoleLookupError:
            return
        for tag in tags:
            if tag.id != self.point_id:
                service.linkage_remove_tag(direction_id, tag.id, db_path=self.db_path)
        try:
            service.linkage_delete_direction(self.point_id, direction_id, db_path=self.db_path)
        except (dao_console.ConsoleLookupError, dao_console.ReferencedError):
            pass

    def _purge_point(self, chapter_id: int, point_id: int) -> None:
        with service.session(self.db_path) as conn:
            conn.execute(
                "DELETE FROM chapter_knowledge_map "
                "WHERE chapter_id = ? AND knowledge_point_id = ?",
                (chapter_id, point_id),
            )
            conn.execute("DELETE FROM knowledge_exam_map WHERE knowledge_point_id = ?",
                         (point_id,))
            conn.execute("DELETE FROM dim_knowledge_points WHERE id = ?", (point_id,))
            conn.commit()

    def _new_point(self, chapter_id: int | None = None, **kwargs: object) -> LinkedKnowledgePoint:
        target = chapter_id or self.empty_chapter_id
        name = "联动测试知识点_" + uuid.uuid4().hex[:8]
        point = service.linkage_add_point(target, name, db_path=self.db_path, **kwargs)
        self.addCleanup(self._purge_point, target, point.id)
        return point

    # ---- 章节树 ----

    def test_chapter_tree_hierarchy_and_counts(self) -> None:
        nodes = service.linkage_chapter_tree(self.textbook_id, db_path=self.db_path)
        self.assertGreater(len(nodes), 0)
        seen: list[int] = []

        def walk(node: ChapterNode, parent_id: int | None) -> None:
            self.assertIsInstance(node, ChapterNode)
            self.assertEqual(node.chapter.textbook_id, self.textbook_id)
            self.assertEqual(node.chapter.parent_id, parent_id)
            seen.append(node.chapter.id)
            for child in node.children:
                walk(child, node.chapter.id)

        for node in nodes:
            walk(node, None)
        with service.session(self.db_path) as conn:
            total = int(conn.execute(
                "SELECT COUNT(*) FROM dim_textbook_chapters WHERE textbook_id = ?",
                (self.textbook_id,),
            ).fetchone()[0])
        self.assertEqual(len(seen), total)
        self.assertEqual(len(set(seen)), total)

    def test_chapter_tree_unknown_textbook_raises_lookup(self) -> None:
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_chapter_tree(999999, db_path=self.db_path)

    # ---- 关联读 ----

    def test_chapter_points_follow_bridge_order(self) -> None:
        items = service.linkage_chapter_points(self.chapter_id, db_path=self.db_path)
        self.assertGreaterEqual(len(items), 2)
        self.assertTrue(all(isinstance(item, LinkedKnowledgePoint) for item in items))
        self.assertEqual([item.sort_order for item in items], list(range(len(items))))

    def test_point_directions_and_tags(self) -> None:
        directions = service.linkage_point_directions(self.point_id, db_path=self.db_path)
        self.assertGreater(len(directions), 0)
        self.assertTrue(all(isinstance(item, ExamDirection) for item in directions))
        keys = [(item.sort_order, item.id) for item in directions]
        self.assertEqual(keys, sorted(keys))
        self.assertIn(self.direction_id, [item.id for item in directions])
        tags = service.linkage_direction_tags(self.direction_id, db_path=self.db_path)
        self.assertEqual([tag.id for tag in tags], [self.secondary_point_id])
        self.assertEqual([tag.sort_order for tag in tags], [1])
        # 换到辅助知识点视角看同一考向：自己必须被排除，主关联也不出现。
        own = service.linkage_direction_tags(
            self.direction_id, exclude_point_id=self.secondary_point_id, db_path=self.db_path)
        self.assertEqual(own, ())

    def test_unknown_ids_raise_lookup(self) -> None:
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_chapter_points(999999, db_path=self.db_path)
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_point_directions(999999, db_path=self.db_path)
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_direction_tags(999999, db_path=self.db_path)

    # ---- 拖拽排序：真持久化（每次调用新开连接，重读仍在即落库） ----

    def test_reorder_chapter_points_persists(self) -> None:
        ids = [item.id for item in service.linkage_chapter_points(
            self.chapter_id, db_path=self.db_path)]
        reversed_ids = list(reversed(ids))
        service.linkage_reorder("chapter_points", self.chapter_id, reversed_ids,
                                db_path=self.db_path)
        self.addCleanup(service.linkage_reorder, "chapter_points", self.chapter_id, ids,
                        db_path=self.db_path)
        again = service.linkage_chapter_points(self.chapter_id, db_path=self.db_path)
        self.assertEqual([item.id for item in again], reversed_ids)
        self.assertEqual([item.sort_order for item in again], list(range(len(ids))))

    def test_reorder_tags_persists(self) -> None:
        ids = [tag.id for tag in service.linkage_direction_tags(
            self.direction_id, db_path=self.db_path)]
        reversed_ids = list(reversed(ids))
        service.linkage_reorder("direction_tags", self.direction_id, reversed_ids,
                                db_path=self.db_path)
        self.addCleanup(service.linkage_reorder, "direction_tags", self.direction_id, ids,
                        db_path=self.db_path)
        again = service.linkage_direction_tags(self.direction_id, db_path=self.db_path)
        self.assertEqual([tag.id for tag in again], reversed_ids)

    def test_reorder_rejects_mismatched_or_non_integer(self) -> None:
        ids = [item.id for item in service.linkage_chapter_points(
            self.chapter_id, db_path=self.db_path)]
        with self.assertRaises(ValueError):
            service.linkage_reorder("chapter_points", self.chapter_id, ids[:-1],
                                    db_path=self.db_path)
        with self.assertRaises(ValueError):
            service.linkage_reorder("chapter_points", self.chapter_id,
                                    [ids[0], ids[0]], db_path=self.db_path)
        with self.assertRaises(ValueError):
            service.linkage_reorder("chapter_points", self.chapter_id,
                                    [str(value) for value in ids], db_path=self.db_path)
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_reorder("nonsense", self.chapter_id, ids, db_path=self.db_path)
        again = [item.id for item in service.linkage_chapter_points(
            self.chapter_id, db_path=self.db_path)]
        self.assertEqual(again, ids)

    # ---- 考向 CRUD 与删除防呆 ----

    def test_add_direction_inherits_subject_and_links_point(self) -> None:
        direction = self._new_direction()
        point = service.knowledge_point(self.point_id, db_path=self.db_path)
        self.assertEqual(direction.subject_id, point.subject_id)
        self.assertTrue(direction.code.startswith("tp_u"))
        self.assertIn(direction.id, [item.id for item in service.linkage_point_directions(
            self.point_id, db_path=self.db_path)])
        tags = service.linkage_direction_tags(direction.id, db_path=self.db_path)
        self.assertEqual(tags, ())

    def test_add_direction_empty_name_rejected(self) -> None:
        with self.assertRaises(ValueError):
            service.linkage_add_direction(self.point_id, "   ", db_path=self.db_path)

    def test_add_direction_honours_explicit_sort_order(self) -> None:
        name = "联动排序考向_" + uuid.uuid4().hex[:8]
        direction = service.linkage_add_direction(
            self.empty_point_id, name, sort_order=0, db_path=self.db_path
        )
        self.addCleanup(self._purge_direction, direction.id)
        self.assertEqual(direction.sort_order, 0)
        items = service.linkage_point_directions(self.empty_point_id, db_path=self.db_path)
        self.assertEqual([item.id for item in items], [direction.id])
        with self.assertRaises(ValueError):
            service.linkage_add_direction(
                self.point_id, "负排序考向_" + uuid.uuid4().hex[:8],
                sort_order=-1, db_path=self.db_path,
            )
        with self.assertRaises(ValueError):
            service.linkage_add_direction(
                self.point_id, "布尔排序考向_" + uuid.uuid4().hex[:8],
                sort_order=True, db_path=self.db_path,
            )

    def test_add_point_inherits_subject_and_links_chapter(self) -> None:
        point = self._new_point()
        self.assertTrue(point.code.startswith("kp_u"))
        self.assertIsNone(point.parent_id)
        chapter = service.console_row("dim_textbook_chapters", self.empty_chapter_id,
                                      db_path=self.db_path)
        book = service.console_row("dim_textbooks", chapter.textbook_id,
                                   db_path=self.db_path)
        self.assertEqual(point.subject_id, book.subject_id)
        items = service.linkage_chapter_points(self.empty_chapter_id, db_path=self.db_path)
        self.assertEqual([item.id for item in items], [point.id])
        self.assertEqual(items[0].sort_order, 0)
        self.assertEqual(items[0].name, point.name)

    def test_add_point_sort_order_controls_bridge_position(self) -> None:
        first = self._new_point(sort_order=0)
        second = self._new_point(sort_order=1)
        items = service.linkage_chapter_points(self.empty_chapter_id, db_path=self.db_path)
        self.assertEqual([item.id for item in items], [first.id, second.id])
        self.assertEqual([item.sort_order for item in items], [0, 1])

    def test_add_point_rejects_bad_input_and_duplicates(self) -> None:
        with self.assertRaises(ValueError):
            service.linkage_add_point(self.empty_chapter_id, "   ", db_path=self.db_path)
        with self.assertRaises(ValueError):
            service.linkage_add_point(
                self.empty_chapter_id, "负排序知识点", sort_order=-1, db_path=self.db_path
            )
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_add_point(999999, "不存在章节知识点", db_path=self.db_path)
        first = self._new_point()
        with self.assertRaises(dao_console.ConflictError):
            service.linkage_add_point(
                self.empty_chapter_id, first.name, db_path=self.db_path
            )

    # ---- 知识点删除：章节挂载是从属关系，题目引用才拦截 ----

    def test_new_point_without_question_links_deletes_and_clears_bridge(self) -> None:
        point = self._new_point()
        with service.session(self.db_path) as conn:
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM chapter_knowledge_map WHERE knowledge_point_id = ?",
                (point.id,),
            ).fetchone()[0], 1)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM question_knowledge_map WHERE knowledge_point_id = ?",
                (point.id,),
            ).fetchone()[0], 0)
        # 只挂了父章节这一条桥表行，不算外部引用：预览为空、删除不报 409。
        self.assertEqual(
            service.console_references("dim_knowledge_points", point.id, db_path=self.db_path),
            (),
        )
        service.console_delete("dim_knowledge_points", point.id, db_path=self.db_path)
        with service.session(self.db_path) as conn:
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM chapter_knowledge_map WHERE knowledge_point_id = ?",
                (point.id,),
            ).fetchone()[0], 0)
            self.assertEqual(conn.execute(
                "SELECT COUNT(*) FROM dim_knowledge_points WHERE id = ?", (point.id,),
            ).fetchone()[0], 0)
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.console_row("dim_knowledge_points", point.id, db_path=self.db_path)

    def test_point_with_question_link_still_blocked(self) -> None:
        point = self._new_point()
        with service.session(self.db_path) as conn:
            def first(table: str) -> int:
                return int(conn.execute(
                    "SELECT id FROM " + table + " ORDER BY id LIMIT 1").fetchone()[0])
            question_id = "q_" + uuid.uuid4().hex[:12]
            conn.execute(
                "INSERT INTO questions (id, stem, subject_id, question_type_id, "
                "difficulty_id, quality_id) VALUES (?, ?, ?, ?, ?, ?)",
                (question_id, "引用知识点删除防呆用例", first("dict_subjects"),
                 first("dict_question_types"), first("dict_difficulties"),
                 first("dict_question_qualities")),
            )
            conn.execute(
                "INSERT INTO question_knowledge_map (question_id, knowledge_point_id) "
                "VALUES (?, ?)",
                (question_id, point.id),
            )
            conn.commit()
        # 题目关联删除会留下孤儿引用，仍然 409 拦截。
        self.addCleanup(self._drop_question, question_id)
        with self.assertRaises(dao_console.ReferencedError) as ctx:
            service.console_delete("dim_knowledge_points", point.id, db_path=self.db_path)
        self.assertIn(
            "question_knowledge_map", {hit.table for hit in ctx.exception.hits}
        )
        self.assertEqual(
            service.console_row("dim_knowledge_points", point.id, db_path=self.db_path).id,
            point.id,
        )

    def _drop_question(self, question_id: str) -> None:
        with service.session(self.db_path) as conn:
            conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
            conn.commit()

    def test_delete_direction_blocked_while_other_point_references(self) -> None:
        direction = self._new_direction()
        service.linkage_add_tag(direction.id, self.other_point_id, db_path=self.db_path)
        with self.assertRaises(dao_console.ReferencedError) as ctx:
            service.linkage_delete_direction(self.point_id, direction.id, db_path=self.db_path)
        self.assertIn("knowledge_exam_map", {hit.table for hit in ctx.exception.hits})
        tags = service.linkage_direction_tags(direction.id, db_path=self.db_path)
        self.assertEqual([tag.id for tag in tags], [self.other_point_id])
        service.linkage_remove_tag(direction.id, self.other_point_id, db_path=self.db_path)
        service.linkage_delete_direction(self.point_id, direction.id, db_path=self.db_path)
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_direction_tags(direction.id, db_path=self.db_path)

    def test_delete_direction_requires_existing_link(self) -> None:
        direction = self._new_direction()
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_delete_direction(self.other_point_id, direction.id,
                                             db_path=self.db_path)

    # ---- 辅助标签 ----

    def test_add_tag_appends_and_duplicate_conflicts(self) -> None:
        direction = self._new_direction()
        tag = service.linkage_add_tag(direction.id, self.other_point_id, db_path=self.db_path)
        self.assertEqual(tag.sort_order, 1)
        with self.assertRaises(dao_console.ConflictError):
            service.linkage_add_tag(direction.id, self.other_point_id, db_path=self.db_path)
        tags = service.linkage_direction_tags(direction.id, db_path=self.db_path)
        self.assertEqual([item.id for item in tags], [self.other_point_id])

    def test_remove_tag_only_unlinks(self) -> None:
        direction = self._new_direction()
        service.linkage_add_tag(direction.id, self.other_point_id, db_path=self.db_path)
        service.linkage_remove_tag(direction.id, self.other_point_id, db_path=self.db_path)
        tags = service.linkage_direction_tags(direction.id, db_path=self.db_path)
        self.assertEqual([item.id for item in tags], [])
        still = service.knowledge_point(self.other_point_id, db_path=self.db_path)
        self.assertEqual(still.id, self.other_point_id)
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.linkage_remove_tag(direction.id, self.other_point_id, db_path=self.db_path)

    # ---- 双击改名走阶段二规格驱动通道，联动读即时反映 ----

    def test_rename_point_and_direction_via_console_spec(self) -> None:
        point = service.console_row("dim_knowledge_points", self.secondary_point_id,
                                    db_path=self.db_path)
        service.console_update("dim_knowledge_points", self.secondary_point_id,
                               {"name": "联动改名测试知识点"}, db_path=self.db_path)
        self.addCleanup(service.console_update, "dim_knowledge_points", self.secondary_point_id,
                        {"name": point.name}, db_path=self.db_path)
        tags = service.linkage_direction_tags(self.direction_id, db_path=self.db_path)
        self.assertEqual(tags[0].name, "联动改名测试知识点")
        direction = service.console_row("dim_exam_directions", self.direction_id,
                                        db_path=self.db_path)
        service.console_update("dim_exam_directions", self.direction_id,
                               {"name": "联动改名测试考向"}, db_path=self.db_path)
        self.addCleanup(service.console_update, "dim_exam_directions", self.direction_id,
                        {"name": direction.name}, db_path=self.db_path)
        renamed = [item for item in service.linkage_point_directions(
            self.point_id, db_path=self.db_path) if item.id == self.direction_id]
        self.assertEqual(renamed[0].name, "联动改名测试考向")


class LinkageRouteTest(unittest.TestCase):
    def test_chapter_tree_route_shape(self) -> None:
        from app.api import bank_engine

        node = ChapterNode(
            Chapter(id=1, name="第一章", code="c1", sort_order=1, textbook_id=7, parent_id=None),
            (ChapterNode(Chapter(id=2, name="1.1 节", code="c11", sort_order=1,
                                 textbook_id=7, parent_id=1)),),
        )
        with mock.patch.object(bank_engine.service, "linkage_chapter_tree",
                               return_value=(node,)):
            body = bank_engine.engine_linkage_chapter_tree(textbook_id=7)
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["items"][0]["chapter"]["name"], "第一章")
        self.assertEqual(body["items"][0]["children"][0]["chapter"]["parent_id"], 1)

    def test_version_tree_route_forwards_stage_and_subject(self) -> None:
        from app.api import bank_engine

        with mock.patch.object(bank_engine.service, "linkage_version_tree",
                               return_value=()) as spy:
            body = bank_engine.engine_linkage_version_tree(
                version_id=4, stage="初中", subject_id=2)
        spy.assert_called_once_with(4, stage="初中", subject_id=2)
        self.assertEqual(body, {"items": [], "total": 0})

    def test_guard_maps_referenced_to_409_on_direction_delete(self) -> None:
        from app.api import bank_engine

        hit = ReferenceHit(table="knowledge_exam_map", label="知识点考向关联",
                           column="exam_direction_id", count=1)
        with mock.patch.object(bank_engine.service, "linkage_delete_direction",
                               side_effect=dao_console.ReferencedError((hit,))):
            with self.assertRaises(HTTPException) as ctx:
                bank_engine.engine_linkage_delete_direction(1, 2)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail["code"], "referenced")
        self.assertEqual(ctx.exception.detail["message"], "已被引用，无法删除")

    def test_order_route_maps_value_error_to_400(self) -> None:
        from app.api import bank_engine

        with self.assertRaises(HTTPException) as ctx:
            bank_engine.engine_linkage_chapter_points_order(1, {})
        self.assertEqual(ctx.exception.status_code, 400)
        with mock.patch.object(bank_engine.service, "linkage_reorder",
                               side_effect=ValueError("排序清单与现有条目不一致")):
            with self.assertRaises(HTTPException) as ctx2:
                bank_engine.engine_linkage_direction_tags_order(2, {"point_ids": [1, 2]})
        self.assertEqual(ctx2.exception.status_code, 400)

    def test_write_payload_validation(self) -> None:
        from app.api import bank_engine

        with self.assertRaises(HTTPException) as ctx:
            bank_engine.engine_linkage_add_direction(1, {})
        self.assertEqual(ctx.exception.status_code, 400)
        for payload in (
            {"name": "x", "sort_order": True},
            {"name": "x", "sort_order": "1"},
        ):
            with self.assertRaises(HTTPException) as ctx2:
                bank_engine.engine_linkage_add_direction(1, payload)
            self.assertEqual(ctx2.exception.status_code, 400)
        for payload in (
            {}, {"name": 3}, {"name": "x", "code": 3},
            {"name": "x", "sort_order": True},
        ):
            with self.assertRaises(HTTPException) as ctx3:
                bank_engine.engine_linkage_add_point(1, payload)
            self.assertEqual(ctx3.exception.status_code, 400)
        for payload in ({"point_id": "3"}, {"point_id": True}, {}):
            with self.assertRaises(HTTPException) as ctx4:
                bank_engine.engine_linkage_add_tag(1, payload)
            self.assertEqual(ctx4.exception.status_code, 400)

    def test_routes_registered_in_host(self) -> None:
        from app.main import create_app

        def walk(routes):
            for route in routes:
                if hasattr(route, "path"):
                    yield route.path
                original = getattr(route, "original_router", None)
                if original is not None:
                    yield from walk(original.routes)

        paths = set(walk(create_app().routes))
        for path in (
            "/api/bank/engine/linkage/chapter-tree",
            "/api/bank/engine/linkage/chapters/{chapter_id}/points",
            "/api/bank/engine/linkage/points/{point_id}/directions",
            "/api/bank/engine/linkage/directions/{direction_id}/tags",
            "/api/bank/engine/linkage/chapters/{chapter_id}/points/order",
            "/api/bank/engine/linkage/directions/{direction_id}/tags/order",
            "/api/bank/engine/linkage/points/{point_id}/directions/{direction_id}",
            "/api/bank/engine/linkage/directions/{direction_id}/tags/{point_id}",
        ):
            self.assertIn(path, paths)

    def test_write_routes_require_token(self) -> None:
        from app.api import bank_engine

        writes = 0
        for route in bank_engine.router.routes:
            path = getattr(route, "path", "")
            if path.startswith("/api/bank/engine/linkage/") and (
                getattr(route, "methods", set()) & {"POST", "PUT", "DELETE"}
            ):
                writes += 1
                deps = [d.call for d in route.dependant.dependencies]
                self.assertTrue(any(call.__name__ == "require_write_token" for call in deps),
                                path)
        self.assertEqual(writes, 7)


class LinkageRedLineTest(unittest.TestCase):
    def test_stage3_files_under_500_lines(self) -> None:
        paths = [
            ROOT / "app" / "bank_engine" / "dao_linkage.py",
            ROOT / "app" / "bank_engine" / "migrate_v7.py",
            ROOT / "static" / "css" / "dict_console_linkage.css",
            CONSOLE_DIR / "tree_add.js",
        ] + sorted(CONSOLE_DIR.glob("linkage*.js"))
        self.assertGreaterEqual(len(list(CONSOLE_DIR.glob("linkage*.js"))), 4)
        for path in paths:
            lines = len(path.read_text(encoding="utf-8").splitlines())
            self.assertLess(lines, 500, path.name + " 超 500 行：" + str(lines))

    def test_linkage_js_no_innerhtml_eval_or_lookbehind(self) -> None:
        for path in CONSOLE_DIR.glob("linkage*.js"):
            text = path.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\.innerHTML\s*=", path.name)
            self.assertNotRegex(text, r"\beval\s*\(", path.name)
            self.assertNotRegex(text, r"\(\?<[=!]", path.name)

    def test_linkage_python_no_fstring_sql(self) -> None:
        for name in ("dao_linkage.py", "migrate_v7.py"):
            text = (ROOT / "app" / "bank_engine" / name).read_text(encoding="utf-8")
            self.assertNotRegex(text, r"execute(?:script|many)?\(f['\"]", name)

    def test_teaching_category_wires_linkage_modules(self) -> None:
        html = (ROOT / "static" / "dict_console.html").read_text(encoding="utf-8")
        for name in (
            "tree_add", "linkage_dnd", "linkage_tags", "linkage_guide",
            "linkage_tree", "linkage", "linkage_add", "linkage_directions",
        ):
            self.assertIn("dict_console/" + name + ".js", html)
        self.assertIn("dict_console_linkage.css", html)
        catalog = (CONSOLE_DIR / "catalog.js").read_text(encoding="utf-8")
        # 知识点与考向不再各自挂 linkage 标记，统一收进 knowledge-linkage 这张联动子页签
        self.assertIn('{ key: "knowledge-linkage", label: "知识点与考向", mode: "linkage" }', catalog)
        self.assertEqual(catalog.count('sub: "knowledge-linkage"'), 2)

    def test_ghost_row_is_the_only_inline_add_entry(self) -> None:
        tree = (CONSOLE_DIR / "linkage_tree.js").read_text(encoding="utf-8")
        css = (ROOT / "static" / "css" / "dict_console_linkage.css").read_text(encoding="utf-8")
        shared = (CONSOLE_DIR / "entity_textbooks.js").read_text(encoding="utf-8")
        add = (CONSOLE_DIR / "linkage_add.js").read_text(encoding="utf-8")
        tree_add = (CONSOLE_DIR / "tree_add.js").read_text(encoding="utf-8")
        guide = (CONSOLE_DIR / "linkage_guide.js").read_text(encoding="utf-8")
        directions = (CONSOLE_DIR / "linkage_directions.js").read_text(encoding="utf-8")
        # 行内「+」全部下线：版本 / 册次 / 章 / 节 / 知识点都不再挂 plus 按钮
        self.assertNotIn("T.plus(", tree)
        self.assertNotIn("DcTreeAdd.plus", directions)
        self.assertNotIn("function plus", tree_add)
        self.assertNotIn(".node-add", css)
        # 新增入口只剩两处：子节点末尾的幽灵行 + 空状态「＋ 添加」
        self.assertIn("function ghostRow", tree_add)
        self.assertIn("dc-ghost-add", tree_add)
        self.assertIn("G.ghost(", directions)
        self.assertGreaterEqual(tree.count("G.ghost("), 4)
        # 幽灵行必须按直接子级查找：知识点列表里嵌着考向幽灵行，
        # 裸 querySelector 会选中子节点里那个，导致输入框追加到幽灵行之后。
        self.assertIn(':scope > .dc-ghost-item', tree)
        self.assertIn(':scope > .dc-ghost-item', directions)
        self.assertIn("DcTreeAdd.emptyAdd(", guide)
        self.assertIn(".dc-ghost-add", css)
        # 幽灵行热区 ≥44px，低饱和：默认降透明度，悬停提亮
        self.assertIn("min-height: 44px", css)
        self.assertIn("opacity: 0.7", css)
        # 排序芯片保留在右侧
        self.assertIn("G.sort(", tree)
        self.assertIn("DcLinkageSort", guide)
        # 册次与章节树同样只露一个 +，不再带「节 / 章 / 册」后缀文案
        self.assertIn('"det-op det-op-add", "+"', (
            CONSOLE_DIR / "entity_shared.js").read_text(encoding="utf-8"))
        self.assertNotIn("addText", shared)
        # 新增不再弹窗：六级全部走 DcTreeAdd.inlineAdd，编码 custom_* 前端签发
        self.assertIn("inlineAdd", add)
        self.assertIn("timestampCode", add)
        self.assertNotIn("DcDialog.open", add)
        self.assertNotIn("fields:", add)
        self.assertIn("nextOrder", add)
        self.assertIn("points/order", (CONSOLE_DIR / "linkage_sort.js").read_text(encoding="utf-8"))
        # 实体教材树同样改为行内新增
        entity_add = (CONSOLE_DIR / "entity_textbook_add.js").read_text(encoding="utf-8")
        self.assertIn("S.addInline", entity_add)
        self.assertNotIn("S.add(", entity_add)
        self.assertIn("_detAddBox", (CONSOLE_DIR / "entity_shared.js").read_text(encoding="utf-8"))
        self.assertIn("addInline", (CONSOLE_DIR / "entity_shared.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
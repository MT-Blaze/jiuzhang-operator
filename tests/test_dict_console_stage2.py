"""数据字典控制台 · 阶段二契约：基础五表读写、删除防呆与 TOML 导入。

钉住六件事：
1. 五表 read 带搜索与全局设置过滤，Dataclass 出口，行数与种子一致；
2. insert / update 落库并回读，唯一约束冲突换 ConflictError；
3. 删除前查外键引用：被引用抛 ReferencedError（API 换 409），无引用才真删；
4. 区划 CHECK / 学校 exam_school_map 等真实引用都被防呆拦截；
5. TOML 批量导入：新增计数、重复跳过、坏行记错，绝不落 JSON 文件；
6. 控制台路由注册进底座，_guard 把领域异常换成 404 / 409 / 400。

运行：``.venv/Scripts/python.exe -m unittest tests.test_dict_console_stage2 -v``
"""

from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.bank_engine import builder, dao_console, service  # noqa: E402
from app.bank_engine.models import (  # noqa: E402
    ExamType,
    Grade,
    ReferenceHit,
    Region,
    School,
    Subject,
)

SCHEMA = ROOT / "plugins" / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"
CONSOLE_DIR = ROOT / "static" / "js" / "dict_console"


class ConsoleServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = Path(tempfile.mkdtemp(prefix="dict-console-s2-"))
        cls.db_path = cls.tmp / "engine.v2.db"
        builder.build_engine(db_path=cls.db_path, schema=SCHEMA)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, True)

    def _insert_subject(self, code: str) -> Subject:
        item = service.console_insert(
            "dict_subjects", {"name": "测试学科_" + code, "code": code, "sort_order": 99},
            db_path=self.db_path,
        )
        self.addCleanup(self._cleanup_subject, item.id)
        return item

    def _cleanup_subject(self, row_id: int) -> None:
        try:
            service.console_delete("dict_subjects", row_id, db_path=self.db_path)
        except (dao_console.ReferencedError, dao_console.ConsoleLookupError):
            pass

    # ---- read：真实种子 + 搜索 + 全局设置 ----

    def test_list_subjects_matches_seed_and_dataclass(self) -> None:
        items, total = service.console_list("dict_subjects", db_path=self.db_path)
        self.assertEqual(total, 15)
        self.assertEqual(len(items), 15)
        self.assertTrue(all(isinstance(item, Subject) for item in items))

    def test_list_schools_and_regions_dataclass(self) -> None:
        schools, total = service.console_list("dim_schools", limit=200, db_path=self.db_path)
        self.assertEqual(total, 347)
        self.assertTrue(all(isinstance(item, School) for item in schools))
        regions, rtotal = service.console_list("dim_regions", limit=200, db_path=self.db_path)
        self.assertEqual(rtotal, 368)
        self.assertTrue(all(isinstance(item, Region) for item in regions))

    def test_keyword_search_filters(self) -> None:
        items, total = service.console_list(
            "dict_subjects", keyword="数学", db_path=self.db_path
        )
        self.assertEqual(total, 1)
        self.assertEqual(items[0].name, "数学")

    def test_global_stage_filter_on_grades(self) -> None:
        items, total = service.console_list(
            "dict_grades", filters={"stage": "小学"}, db_path=self.db_path
        )
        self.assertGreater(total, 0)
        self.assertTrue(all(item.stage == "小学" for item in items))
        self.assertTrue(all(isinstance(item, Grade) for item in items))

    def test_shared_stage_filter_keeps_all_stage_rows(self) -> None:
        for table in (
            "dict_subject_thoughts",
            "dict_solution_methods",
            "dict_core_competencies",
        ):
            items, total = service.console_list(
                table, filters={"stage": "高中"}, limit=200, db_path=self.db_path
            )
            self.assertGreater(total, 0, table)
            self.assertTrue(all(item.stage in ("高中", "全学段") for item in items), table)

        thoughts, _ = service.console_list(
            "dict_subject_thoughts",
            filters={"stage": "高中", "subject_id": 2},
            limit=200,
            db_path=self.db_path,
        )
        self.assertIn("数形结合", {item.name for item in thoughts})

        primary_methods, _ = service.console_list(
            "dict_solution_methods",
            filters={"stage": "小学", "subject_id": 2},
            limit=200,
            db_path=self.db_path,
        )
        names = {item.name for item in primary_methods}
        self.assertIn("定义法", names)
        self.assertNotIn("导数法", names)
        self.assertNotIn("隐零点法", names)

        senior_methods, senior_total = service.console_list(
            "dict_solution_methods",
            filters={"stage": "高中", "subject_id": 2},
            limit=200,
            db_path=self.db_path,
        )
        self.assertGreaterEqual(senior_total, 30)
        self.assertIn("分离参数法", {item.name for item in senior_methods})
        self.assertIn("极值点偏移法", {item.name for item in senior_methods})

    def test_cross_stage_math_methods_visible_in_high_school(self) -> None:
        methods, total = service.console_list(
            "dict_solution_methods",
            filters={"stage": "高中", "subject_id": 2},
            limit=200,
            db_path=self.db_path,
        )
        names = {item.name for item in methods}
        self.assertGreaterEqual(total, 30)
        self.assertIn("配方法", names)
        self.assertIn("待定系数法", names)

    def test_high_school_physics_teaching_dicts_are_complete(self) -> None:
        methods, method_total = service.console_list(
            "dict_solution_methods",
            filters={"stage": "高中", "subject_id": 4},
            limit=200,
            db_path=self.db_path,
        )
        method_names = {item.name for item in methods}
        self.assertGreaterEqual(method_total, 30)
        for name in ("整体法", "隔离法", "正交分解法", "微元法", "图像法",
                     "控制变量法", "实验探究法", "对称法", "极限思维法"):
            self.assertIn(name, method_names)

        thoughts, thought_total = service.console_list(
            "dict_subject_thoughts",
            filters={"stage": "高中", "subject_id": 4},
            limit=200,
            db_path=self.db_path,
        )
        thought_names = {item.name for item in thoughts}
        self.assertGreaterEqual(thought_total, 10)
        for name in ("守恒思想", "微元思想", "等效替代", "对称思想",
                     "数形结合思想", "系统思想"):
            self.assertIn(name, thought_names)

        competencies, competency_total = service.console_list(
            "dict_core_competencies",
            filters={"stage": "高中", "subject_id": 4},
            limit=200,
            db_path=self.db_path,
        )
        competency_names = {item.name for item in competencies}
        self.assertGreaterEqual(competency_total, 14)
        for name in ("物理观念", "科学思维", "科学探究", "科学态度与责任",
                     "物质观念", "运动与相互作用观念", "能量观念",
                     "模型建构", "科学推理", "科学论证", "质疑创新",
                     "提出问题", "获取证据", "作出解释", "表达交流",
                     "科学本质", "科学态度", "社会责任"):
            self.assertIn(name, competency_names)

    def test_core_names_have_no_subject_suffix(self) -> None:
        items, _ = service.console_list(
            "dict_core_competencies", limit=200, db_path=self.db_path
        )
        dirty = [item.name for item in items if "（生物）" in item.name
                 or "（科学）" in item.name or "（美术）" in item.name]
        self.assertEqual(dirty, [])

    def test_name_is_unique_per_subject_not_globally(self) -> None:
        first = service.console_insert(
            "dict_core_competencies",
            {"name": "验收同名素养", "code": "zz_core_same_a", "subject_id": 1},
            db_path=self.db_path,
        )
        self.addCleanup(
            service.console_delete, "dict_core_competencies", first.id, db_path=self.db_path
        )
        second = service.console_insert(
            "dict_core_competencies",
            {"name": "验收同名素养", "code": "zz_core_same_b", "subject_id": 2},
            db_path=self.db_path,
        )
        self.addCleanup(
            service.console_delete, "dict_core_competencies", second.id, db_path=self.db_path
        )
        with self.assertRaises(dao_console.ConflictError):
            service.console_insert(
                "dict_core_competencies",
                {"name": "验收同名素养", "code": "zz_core_same_c", "subject_id": 1},
                db_path=self.db_path,
            )

    def test_stage_is_never_null_and_enum_only(self) -> None:
        for table in (
            "dict_subject_thoughts",
            "dict_solution_methods",
            "dict_core_competencies",
        ):
            items, _ = service.console_list(table, limit=200, db_path=self.db_path)
            self.assertTrue(items, table)
            self.assertTrue(
                all(item.stage in dao_console.STAGE_VALUES for item in items), table
            )

    def test_stage_insert_defaults_to_all_and_rejects_bad_value(self) -> None:
        row = service.console_insert(
            "dict_subject_thoughts",
            {"name": "验收通用思想", "code": "zz_stage_default", "subject_id": 1},
            db_path=self.db_path,
        )
        self.addCleanup(
            service.console_delete, "dict_subject_thoughts", row.id, db_path=self.db_path
        )
        self.assertEqual(row.stage, "全学段")
        with self.assertRaises(ValueError):
            service.console_update(
                "dict_subject_thoughts", row.id, {"stage": "大学"}, db_path=self.db_path
            )
        cleared = service.console_update(
            "dict_subject_thoughts", row.id, {"stage": ""}, db_path=self.db_path
        )
        self.assertEqual(cleared.stage, "全学段")

    def test_grade_stage_cannot_be_empty(self) -> None:
        with self.assertRaises(ValueError):
            service.console_insert(
                "dict_grades",
                {"name": "验收年级", "code": "zz_stage_grade", "sort_order": 99},
                db_path=self.db_path,
            )

    def test_global_textbook_filter_on_schools(self) -> None:
        # 种子学校未挂教材（textbook_id 全空）：先给一所学校挂上真实教材再验证过滤机制。
        with service.session(self.db_path) as conn:
            book_id = int(conn.execute("SELECT id FROM dim_textbooks LIMIT 1").fetchone()["id"])
        service.console_update("dim_schools", 1, {"textbook_id": book_id}, db_path=self.db_path)
        self.addCleanup(
            service.console_update, "dim_schools", 1, {"textbook_id": None}, db_path=self.db_path
        )
        items, total = service.console_list(
            "dim_schools", filters={"textbook_id": book_id}, limit=200, db_path=self.db_path
        )
        self.assertGreater(total, 0)
        self.assertTrue(all(item.textbook_id == book_id for item in items))

    def test_pagination_bounds(self) -> None:
        items, total = service.console_list(
            "dict_exam_types", limit=5, offset=0, db_path=self.db_path
        )
        self.assertEqual(total, 8)
        self.assertEqual(len(items), 5)
        self.assertTrue(all(isinstance(item, ExamType) for item in items))
        with self.assertRaises(ValueError):
            service.console_list("dict_subjects", limit=0, db_path=self.db_path)

    def test_unknown_table_raises_lookup(self) -> None:
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.console_list("dict_nonsense", db_path=self.db_path)

    # ---- insert / update ----

    def test_insert_update_delete_lifecycle(self) -> None:
        item = self._insert_subject("zz_lifecycle")
        self.assertGreater(item.id, 0)
        updated = service.console_update(
            "dict_subjects", item.id, {"name": "测试学科_改名"}, db_path=self.db_path
        )
        self.assertEqual(updated.name, "测试学科_改名")
        service.console_delete("dict_subjects", item.id, db_path=self.db_path)
        with self.assertRaises(dao_console.ConsoleLookupError):
            service.console_row("dict_subjects", item.id, db_path=self.db_path)

    def test_insert_duplicate_name_conflict(self) -> None:
        with self.assertRaises(dao_console.ConflictError):
            service.console_insert(
                "dict_subjects", {"name": "数学", "code": "zz_dup_code"}, db_path=self.db_path
            )

    def test_update_to_duplicate_conflict(self) -> None:
        item = self._insert_subject("zz_upd_dup")
        with self.assertRaises(dao_console.ConflictError):
            service.console_update(
                "dict_subjects", item.id, {"name": "数学"}, db_path=self.db_path
            )

    def test_insert_missing_required_rejected(self) -> None:
        with self.assertRaises(ValueError):
            service.console_insert("dict_subjects", {"code": "zz_no_name"}, db_path=self.db_path)

    # ---- 删除防呆 ----

    def test_delete_referenced_subject_blocked(self) -> None:
        with self.assertRaises(dao_console.ReferencedError) as ctx:
            service.console_delete("dict_subjects", 2, db_path=self.db_path)
        labels = {hit.table for hit in ctx.exception.hits}
        self.assertIn("dim_textbooks", labels)
        self.assertIn("dim_knowledge_points", labels)
        self.assertTrue(all(hit.count > 0 for hit in ctx.exception.hits))
        # 拦截后行还在
        self.assertEqual(service.console_row("dict_subjects", 2, db_path=self.db_path).name, "数学")

    def test_delete_referenced_school_blocked(self) -> None:
        with self.assertRaises(dao_console.ReferencedError) as ctx:
            service.console_delete("dim_schools", 258, db_path=self.db_path)
        self.assertIn("exam_school_map", {hit.table for hit in ctx.exception.hits})

    def test_delete_referenced_exam_type_blocked(self) -> None:
        with self.assertRaises(dao_console.ReferencedError) as ctx:
            service.console_delete("dict_exam_types", 3, db_path=self.db_path)
        self.assertIn("exams", {hit.table for hit in ctx.exception.hits})

    def test_delete_referenced_region_blocked(self) -> None:
        with service.session(self.db_path) as conn:
            row = conn.execute(
                "SELECT region_id FROM dim_schools WHERE region_id IS NOT NULL LIMIT 1"
            ).fetchone()
        self.assertIsNotNone(row)
        with self.assertRaises(dao_console.ReferencedError) as ctx:
            service.console_delete("dim_regions", int(row["region_id"]), db_path=self.db_path)
        self.assertIn("dim_schools", {hit.table for hit in ctx.exception.hits})

    def test_references_preview(self) -> None:
        hits = service.console_references("dict_subjects", 2, db_path=self.db_path)
        self.assertTrue(hits)
        self.assertTrue(all(isinstance(hit, ReferenceHit) for hit in hits))

    def test_region_check_constraint(self) -> None:
        with self.assertRaises(dao_console.ConflictError):
            service.console_insert(
                "dim_regions", {"name": "测试坏市", "code": "zz9999", "level": 2},
                db_path=self.db_path,
            )
        region = service.console_insert(
            "dim_regions", {"name": "测试省", "code": "zz9998", "level": 1},
            db_path=self.db_path,
        )
        self.addCleanup(service.console_delete, "dim_regions", region.id, db_path=self.db_path)
        self.assertEqual(region.level, 1)
        self.assertIsNone(region.parent_id)

    # ---- TOML 导入 ----

    def test_import_toml_counts_and_errors(self) -> None:
        text = (
            '[[dict_subjects]]\nname = "导入学科甲"\ncode = "zz_import_a"\nsort_order = 90\n\n'
            '[[dict_subjects]]\nname = "数学"\ncode = "zz_import_dup"\n\n'
            '[[dict_nonsense]]\nname = "x"\n\n'
            '[[dict_grades]]\ncode = "zz_no_name"\n'
        )
        report = service.console_import(text, db_path=self.db_path)
        self.assertEqual(report.inserted.get("dict_subjects"), 1)
        self.assertEqual(report.skipped.get("dict_subjects"), 1)
        self.assertGreaterEqual(len(report.errors), 2)
        with service.session(self.db_path) as conn:
            row = conn.execute(
                "SELECT id FROM dict_subjects WHERE code = 'zz_import_a'"
            ).fetchone()
        self.assertIsNotNone(row)
        self.addCleanup(self._cleanup_subject, int(row["id"]))

    def test_import_bad_toml_rejected(self) -> None:
        with self.assertRaises(ValueError):
            service.console_import("这不是 TOML = =", db_path=self.db_path)


class ConsoleRouteTest(unittest.TestCase):
    def test_list_route_shape(self) -> None:
        from app.api import bank_engine

        canned = (Subject(id=1, name="语文", code="chinese", sort_order=1),)
        with mock.patch.object(bank_engine.service, "console_list", return_value=(canned, 1)):
            body = bank_engine.engine_dict_list("dict_subjects", q="")
        self.assertEqual(body["total"], 1)
        self.assertEqual(body["label"], "学科")
        self.assertEqual(body["items"][0]["name"], "语文")
        self.assertEqual(body["fields"][0]["key"], "id")
        name_field = [f for f in body["fields"] if f["key"] == "name"][0]
        self.assertTrue(name_field["editable"])
        self.assertFalse(body["fields"][0]["editable"])

    def test_guard_maps_referenced_to_409(self) -> None:
        from app.api import bank_engine

        hit = ReferenceHit(table="dim_textbooks", label="教材版本", column="subject_id", count=128)
        with mock.patch.object(
            bank_engine.service, "console_delete", side_effect=dao_console.ReferencedError((hit,))
        ):
            with self.assertRaises(HTTPException) as ctx:
                bank_engine.engine_dict_delete("dict_subjects", 2)
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertEqual(ctx.exception.detail["code"], "referenced")
        self.assertEqual(ctx.exception.detail["message"], "已被引用，无法删除")
        self.assertEqual(ctx.exception.detail["references"][0]["label"], "教材版本")

    def test_guard_maps_conflict_and_lookup(self) -> None:
        from app.api import bank_engine

        with mock.patch.object(
            bank_engine.service, "console_insert", side_effect=dao_console.ConflictError("重复")
        ):
            with self.assertRaises(HTTPException) as ctx:
                bank_engine.engine_dict_insert("dict_subjects", {"name": "x"})
        self.assertEqual(ctx.exception.status_code, 409)
        with mock.patch.object(
            bank_engine.service, "console_row", side_effect=dao_console.ConsoleLookupError("无")
        ):
            with self.assertRaises(HTTPException) as ctx2:
                bank_engine.engine_dict_row("dict_subjects", 999)
        self.assertEqual(ctx2.exception.status_code, 404)

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
            "/api/bank/engine/dict/import",
            "/api/bank/engine/dict/{table}",
            "/api/bank/engine/dict/{table}/{row_id}",
            "/api/bank/engine/dict/{table}/{row_id}/references",
        ):
            self.assertIn(path, paths)

    def test_write_routes_require_token(self) -> None:
        from app.api import bank_engine

        for route in bank_engine.router.routes:
            if getattr(route, "path", "") in {
                "/api/bank/engine/dict/import",
                "/api/bank/engine/dict/{table}",
                "/api/bank/engine/dict/{table}/{row_id}",
            } and getattr(route, "methods", set()) & {"POST", "PUT", "DELETE"}:
                deps = [d.call for d in route.dependant.dependencies]
                self.assertTrue(any(call.__name__ == "require_write_token" for call in deps),
                                route.path)


class ConsoleRedLineTest(unittest.TestCase):
    def test_new_backend_files_under_500_lines(self) -> None:
        for path in (
            ROOT / "app" / "bank_engine" / "dao_console.py",
            ROOT / "app" / "bank_engine" / "service.py",
            ROOT / "app" / "bank_engine" / "models.py",
            ROOT / "app" / "api" / "bank_engine.py",
        ):
            lines = len(path.read_text(encoding="utf-8").splitlines())
            self.assertLess(lines, 500, path.name + " 超 500 行：" + str(lines))

    def test_no_json_files_in_console_tree(self) -> None:
        self.assertEqual(list(CONSOLE_DIR.rglob("*.json")), [])

    def test_console_js_never_uses_innerhtml(self) -> None:
        for path in CONSOLE_DIR.glob("*.js"):
            self.assertNotRegex(path.read_text(encoding="utf-8"), r"\.innerHTML\s*=", path.name)


if __name__ == "__main__":
    unittest.main()
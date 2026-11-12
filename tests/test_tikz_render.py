"""图片 TikZ 字段契约：v8 迁移、渲染优先级与安全边界。

守的底线：
1. v7 → v8 只加 ``question_images.tikz_code``，原图 ``path`` 与磁盘文件一概不动；
2. 读路径给图片补 ``tikz_uri`` 时**不改写** ``uri``/``path``，插件回写不会污染原图地址；
3. 渲染失败只记 ``tikz_error``，前端回退原图；危险 LaTeX 命令在编译前就拒掉。

运行：``.venv/Scripts/python.exe -m unittest tests.test_tikz_render``
"""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

from app.api import tikz as tikz_api
from app.bank_engine import builder, migrate_v8, service
from app.core import question_parser, tikz_render

ROOT = Path(__file__).resolve().parents[1]
from app.core.config import plugin_source_root  # noqa: E402

PLUGIN_SOURCE_DIR = plugin_source_root() or (ROOT / "plugins")
SCHEMA = PLUGIN_SOURCE_DIR / "org.jiuzhang.bank-engine" / "bank" / "schema.sql"


class MigrateV8Test(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "engine.v2.db"
        builder.build_engine(db_path=self.db_path, schema=SCHEMA)
        with service.session(self.db_path) as conn:
            migrate_v8.rollback(conn)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _columns(self) -> set[str]:
        with service.session(self.db_path) as conn:
            return {str(row[1]) for row in conn.execute(
                "PRAGMA table_info(question_images)")}

    def _seed_image(self) -> None:
        with service.session(self.db_path) as conn:
            conn.execute(
                "INSERT INTO questions (id, stem, subject_id, question_type_id,"
                " difficulty_id, quality_id) VALUES ('q_tikz001', '题', 2, 1, 2, 2)"
            )
            conn.execute(
                "INSERT INTO question_images (question_id, belongs_to, path)"
                " VALUES ('q_tikz001', 'stem', '/static/uploads/original.png')"
            )
            conn.commit()

    def test_upgrade_adds_column_and_keeps_original_path(self) -> None:
        self._seed_image()
        self.assertNotIn("tikz_code", self._columns())
        with service.session(self.db_path) as conn:
            migrate_v8.upgrade(conn)
        self.assertIn("tikz_code", self._columns())
        with service.session(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 8)
            row = conn.execute(
                "SELECT path, tikz_code FROM question_images WHERE question_id='q_tikz001'"
            ).fetchone()
        self.assertEqual(row[0], "/static/uploads/original.png")
        self.assertIsNone(row[1])
        self.assertTrue(self.db_path.with_name(
            self.db_path.name + ".pre-v8.bak").is_file())

    def test_upgrade_is_idempotent(self) -> None:
        with service.session(self.db_path) as conn:
            migrate_v8.upgrade(conn)
            migrate_v8.upgrade(conn)
            names = [str(row[1]) for row in conn.execute(
                "PRAGMA table_info(question_images)")]
        self.assertEqual(names.count("tikz_code"), 1)

    def test_rollback_drops_only_code_column(self) -> None:
        self._seed_image()
        with service.session(self.db_path) as conn:
            migrate_v8.upgrade(conn)
        self.assertIn("tikz_code", self._columns())
        with service.session(self.db_path) as conn:
            conn.execute(
                "UPDATE question_images SET tikz_code='\\draw (0,0)--(1,1);'"
                " WHERE question_id='q_tikz001'"
            )
            conn.commit()
            migrate_v8.rollback(conn)
        self.assertNotIn("tikz_code", self._columns())
        with service.session(self.db_path) as conn:
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 7)
            path = conn.execute(
                "SELECT path FROM question_images WHERE question_id='q_tikz001'"
            ).fetchone()[0]
        self.assertEqual(path, "/static/uploads/original.png")


class ResolveImageTest(unittest.TestCase):
    def test_no_code_leaves_image_untouched(self) -> None:
        image = {"id": "img1", "uri": "/static/uploads/a.png"}
        self.assertEqual(tikz_render.resolve_image(image), image)
        self.assertNotIn("tikz_uri", image)

    def test_code_prefers_vector_but_keeps_original_uri(self) -> None:
        image = {"id": "img1", "uri": "/static/uploads/a.png",
                 "path": "/static/uploads/a.png", "tikz_code": "\\draw (0,0)--(1,1);"}
        with mock.patch.object(tikz_render, "render",
                               return_value="/static/uploads/tikz/x.svg"):
            tikz_render.resolve_image(image)
        self.assertEqual(image["tikz_uri"], "/static/uploads/tikz/x.svg")
        self.assertEqual(image["uri"], "/static/uploads/a.png")
        self.assertEqual(image["path"], "/static/uploads/a.png")

    def test_render_failure_falls_back_to_original(self) -> None:
        image = {"id": "img1", "uri": "/static/uploads/a.png", "tikz_code": "\\bad"}
        with mock.patch.object(tikz_render, "render",
                               side_effect=tikz_render.TikzError("坏了")):
            tikz_render.resolve_image(image)
        self.assertNotIn("tikz_uri", image)
        self.assertEqual(image["tikz_error"], "坏了")
        self.assertEqual(image["uri"], "/static/uploads/a.png")

    def test_resolve_images_maps_lists(self) -> None:
        images = [{"uri": "/u/a.png"}, {"uri": "/u/b.png", "tikz_code": "x"}]
        with mock.patch.object(tikz_render, "render",
                               return_value="/static/uploads/tikz/y.svg"):
            result = tikz_render.resolve_images(images)
        self.assertNotIn("tikz_uri", result[0])
        self.assertEqual(result[1]["tikz_uri"], "/static/uploads/tikz/y.svg")


class NormalizeTest(unittest.TestCase):
    def test_raw_draw_is_wrapped(self) -> None:
        text = tikz_render._normalize("\\draw (0,0)--(1,1);")
        self.assertTrue(text.startswith("\\begin{tikzpicture}"))
        self.assertTrue(text.endswith("\\end{tikzpicture}"))

    def test_existing_picture_is_kept(self) -> None:
        code = "\\begin{tikzpicture}\\draw (0,0)--(1,1);\\end{tikzpicture}"
        self.assertEqual(tikz_render._normalize(code), code)

    def test_blank_and_document_env_rejected(self) -> None:
        with self.assertRaises(tikz_render.TikzError):
            tikz_render._normalize("   ")
        with self.assertRaises(tikz_render.TikzError):
            tikz_render._normalize("\\begin{document}x\\end{document}")

    def test_dangerous_commands_rejected(self) -> None:
        for code in ("\\input{secret}", "\\openout1=x", "\\usepackage{shellesc}",
                     "\\write18{rm -rf /}"):
            with self.assertRaises(tikz_render.TikzError, msg=code):
                tikz_render._normalize(code)

    def test_status_shape(self) -> None:
        status = tikz_render.status()
        self.assertEqual(set(status), {"available", "engine", "detail"})
        self.assertIsInstance(status["available"], bool)


class TikzApiTest(unittest.TestCase):
    def test_render_returns_uri(self) -> None:
        with mock.patch.object(tikz_render, "render",
                               return_value="/static/uploads/tikz/z.svg"):
            body = tikz_api.tikz_render_code({"code": "\\draw (0,0)--(1,1);"})
        self.assertEqual(body["uri"], "/static/uploads/tikz/z.svg")
        self.assertEqual(body["engine"], tikz_render.ENGINE_LABEL)

    def test_missing_code_is_400(self) -> None:
        with self.assertRaises(HTTPException) as caught:
            tikz_api.tikz_render_code({"code": "  "})
        self.assertEqual(caught.exception.status_code, 400)

    def test_unavailable_is_503(self) -> None:
        with mock.patch.object(tikz_render, "render",
                               side_effect=tikz_render.TikzUnavailable("没有 TeX")):
            with self.assertRaises(HTTPException) as caught:
                tikz_api.tikz_render_code({"code": "\\draw (0,0)--(1,1);"})
        self.assertEqual(caught.exception.status_code, 503)

    def test_rejected_is_422(self) -> None:
        with mock.patch.object(tikz_render, "render",
                               side_effect=tikz_render.TikzError("含不允许的命令")):
            with self.assertRaises(HTTPException) as caught:
                tikz_api.tikz_render_code({"code": "\\input{x}"})
        self.assertEqual(caught.exception.status_code, 422)


class RoundTripTest(unittest.TestCase):
    def test_derived_fields_stripped_but_code_kept(self) -> None:
        document = {
            "stem": "题",
            "images": [{
                "id": "img1",
                "role": "stem",
                "uri": "/static/uploads/a.png",
                "tikz_code": "\\draw (0,0)--(1,1);",
                "tikz_uri": "/static/uploads/tikz/x.svg",
                "tikz_engine": tikz_render.ENGINE_LABEL,
                "tikz_error": "旧错误",
            }],
        }
        cleaned, _ = question_parser.clean_question(document)
        image = cleaned["images"][0]
        self.assertEqual(image["tikz_code"], "\\draw (0,0)--(1,1);")
        self.assertEqual(image["uri"], "/static/uploads/a.png")
        for key in ("tikz_uri", "tikz_engine", "tikz_error"):
            self.assertNotIn(key, image)

    def test_contract_accepts_tikz_code(self) -> None:
        from app.core import question_contract

        document = {
            "schema_version": "2.1",
            "id": "q_rt00000001",
            "type": "solution",
            "stem": "题",
            "difficulty": "L2",
            "meta": {
                "created_at": "2026-11-10T00:00:00Z",
                "updated_at": "2026-11-10T00:00:00Z",
                "revision": 1,
                "status": "draft",
            },
            "images": [{"id": "img_a1", "role": "stem",
                        "uri": "/static/uploads/a.png",
                        "tikz_code": "\\draw (0,0)--(1,1);"}],
        }
        parsed = question_contract.Question.from_document(document)
        self.assertEqual(parsed.images[0].tikz_code, "\\draw (0,0)--(1,1);")
        self.assertEqual(parsed.as_document()["images"][0]["tikz_code"],
                         "\\draw (0,0)--(1,1);")


if __name__ == "__main__":
    unittest.main()

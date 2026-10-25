"""题库批量导入导出：``.json`` / ``.zip`` 题目包的解析、逐题校验、批量写入与导出回灌。

两道关口各守一头：
- 包这一层（``app/core/bank_transfer.py``）：坏 JSON、坏 zip、空包、超限都要拒；
- 题目这一层（``app/core/bank.py`` + ``schemas/question.json``）：逐题校验，一题不过整批回滚。

运行：``.venv/Scripts/python.exe -m unittest tests.test_bank_batch_io``
"""

from __future__ import annotations

import base64
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN = "batch-io-token"
PLUGIN_ID = "org.jiuzhang.bank-engine"


def _question(index: int, *, stem: str | None = None) -> dict:
    return {
        "schema_version": "2.0",
        "id": f"q_pack{index:06d}",
        "type": "fill_blank",
        "stem": stem if stem is not None else f"批量导入第 {index} 题：解方程 $x^{2}-{index}=0$。",
        "answer": {"kind": "expression", "content": f"$x=\\pm\\sqrt{{{index}}}$", "final": "±√n"},
        "difficulty": "L2",
        "tags": ["批量导入"],
        "extensions": {"org.jiuzhang.core-bank.grade": {"grade": "高一"}},
        "meta": {
            "created_at": "2026-10-24T09:00:00+08:00",
            "updated_at": "2026-10-24T09:00:00+08:00",
            "revision": 1,
            "status": "published",
        },
    }


def _zip_bytes(members: dict[str, object]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in members.items():
            archive.writestr(name, json.dumps(payload, ensure_ascii=False))
    return buffer.getvalue()


class BundleParsingTest(unittest.TestCase):
    """包这一层：三种包型都认，坏包一律拒。"""

    def setUp(self) -> None:
        sys.path.insert(0, str(ROOT))
        from app.core import bank_transfer  # noqa: PLC0415

        self.transfer = bank_transfer

    def test_single_question_object(self) -> None:
        documents = self.transfer.parse_bundle(
            json.dumps(_question(1), ensure_ascii=False).encode("utf-8"), "one.json"
        )
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["id"], "q_pack000001")

    def test_question_array(self) -> None:
        raw = json.dumps([_question(1), _question(2)], ensure_ascii=False).encode("utf-8")
        self.assertEqual(len(self.transfer.parse_bundle(raw, "many.json")), 2)

    def test_exchange_bundle(self) -> None:
        payload = {
            "format": "jiuzhang.question.bundle",
            "format_version": "1.0",
            "questions": [_question(1)],
        }
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.assertEqual(len(self.transfer.parse_bundle(raw, "bundle.json")), 1)

    def test_zip_reads_every_json_member(self) -> None:
        raw = _zip_bytes({
            "a.json": _question(1),
            "b.json": [_question(2), _question(3)],
            "readme.txt": "不是题目文件，忽略",
        })
        documents = self.transfer.parse_bundle(raw, "pack.zip")
        self.assertEqual([item["id"] for item in documents],
                         ["q_pack000001", "q_pack000002", "q_pack000003"])

    def test_broken_json_is_rejected(self) -> None:
        with self.assertRaises(self.transfer.TransferError) as ctx:
            self.transfer.parse_bundle(b"{ not json", "bad.json")
        self.assertIn("JSON", str(ctx.exception))

    def test_broken_zip_is_rejected(self) -> None:
        with self.assertRaises(self.transfer.TransferError) as ctx:
            self.transfer.parse_bundle(b"PK\x03\x04 broken", "bad.zip")
        self.assertIn("压缩包", str(ctx.exception))

    def test_zip_without_json_is_rejected(self) -> None:
        raw = _zip_bytes({"readme.txt": "没有题目"})
        with self.assertRaises(self.transfer.TransferError) as ctx:
            self.transfer.parse_bundle(raw, "pack.zip")
        self.assertIn(".json", str(ctx.exception))

    def test_non_object_item_is_rejected(self) -> None:
        raw = json.dumps([_question(1), "不是题目"], ensure_ascii=False).encode("utf-8")
        with self.assertRaises(self.transfer.TransferError) as ctx:
            self.transfer.parse_bundle(raw, "many.json")
        self.assertIn("第 2 项", str(ctx.exception))

    def test_empty_and_oversize_packages_are_rejected(self) -> None:
        with self.assertRaises(self.transfer.TransferError):
            self.transfer.parse_bundle(b"", "empty.json")
        with self.assertRaises(self.transfer.TransferError):
            self.transfer.parse_bundle(b"x" * (self.transfer.MAX_BUNDLE_BYTES + 1), "big.json")

    def test_bundle_builder_round_trips(self) -> None:
        bundle = self.transfer.build_bundle(PLUGIN_ID, [_question(1)], "2026-10-24T09:00:00+08:00")
        self.assertEqual(bundle["format"], "jiuzhang.question.bundle")
        self.assertEqual(bundle["count"], 1)
        self.assertEqual(bundle["schema_version"], "2.0")
        raw = json.dumps(bundle, ensure_ascii=False).encode("utf-8")
        self.assertEqual(len(self.transfer.parse_bundle(raw, "bundle.json")), 1)


class BankBatchIoHttpTest(unittest.TestCase):
    """宿主接口：导入逐题校验后批量写入，导出是标准 .json，且能原样再导回去。"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.tmp_root = Path(cls.tmp.name)
        cls.data_dir = cls.tmp_root / "data"
        cls.plugins_dir = cls.tmp_root / "plugins"
        cls.data_dir.mkdir(parents=True, exist_ok=True)
        cls._saved_plugins_env = os.environ.get("JZO_PLUGINS_DIR")
        os.environ["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        seed_dir = cls.plugins_dir / PLUGIN_ID / "bank"
        seed_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql", seed_dir / "schema.sql")

        sys.path.insert(0, str(ROOT))
        from app.core import bank  # noqa: PLC0415

        cls.bank = bank
        bank.import_documents(
            PLUGIN_ID,
            [_question(index) for index in range(1, 6)],
            reset=True,
            db_path=seed_dir / "bank.db",
        )

        cls.port = _free_port()
        env = os.environ.copy()
        env["JZO_DATA_DIR"] = str(cls.data_dir)
        env["JZO_PLUGINS_DIR"] = str(cls.plugins_dir)
        env["JZO_LOCAL_TOKEN"] = TOKEN
        cls.process = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app.main:app",
                "--host", "127.0.0.1", "--port", str(cls.port), "--log-level", "warning",
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        cls.base = f"http://127.0.0.1:{cls.port}"
        deadline = time.time() + 20
        while time.time() < deadline:
            if cls.process.poll() is not None:
                output = cls.process.stdout.read() if cls.process.stdout else ""
                raise RuntimeError("服务提前退出：\n" + output)
            try:
                with urllib.request.urlopen(cls.base + "/healthz", timeout=0.5) as response:
                    if response.status == 200:
                        return
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                time.sleep(0.1)
        raise RuntimeError("服务未在 20 秒内就绪")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.process.terminate()
        try:
            cls.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            cls.process.kill()
        if cls._saved_plugins_env is None:
            os.environ.pop("JZO_PLUGINS_DIR", None)
        else:
            os.environ["JZO_PLUGINS_DIR"] = cls._saved_plugins_env
        cls.tmp.cleanup()

    # ---------- HTTP 辅助 ----------
    def _request(self, path: str, method: str = "GET", body: dict | None = None,
                 token: bool = False) -> tuple[int, dict]:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("X-JZO-Token", TOKEN)
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                return response.status, json.loads(response.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as error:
            try:
                payload = error.read().decode("utf-8")
            finally:
                error.close()
            try:
                parsed = json.loads(payload or "{}")
            except json.JSONDecodeError:
                parsed = {"raw": payload}
            return error.code, parsed

    def _total(self) -> int:
        status, data = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions?page_size=1"
        )
        self.assertEqual(status, 200, data)
        return int(data["total"])

    def _import(self, raw: bytes, filename: str, mode: str = "upsert",
                token: bool = True) -> tuple[int, dict]:
        payload = {
            "filename": filename,
            "content_base64": base64.b64encode(raw).decode("ascii"),
            "mode": mode,
        }
        return self._request("/api/bank/import", "POST", payload, token=token)

    # ---------- 导入 ----------
    def test_import_requires_token(self) -> None:
        raw = json.dumps([_question(90)], ensure_ascii=False).encode("utf-8")
        status, data = self._import(raw, "pack.json", token=False)
        self.assertEqual(status, 401, data)

    def test_import_json_bundle_writes_questions(self) -> None:
        before = self._total()
        payload = {"questions": [_question(101), _question(102), _question(103)]}
        status, data = self._import(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"), "bundle.json"
        )
        self.assertEqual(status, 200, data)
        self.assertEqual(data["imported"], 3)
        self.assertEqual(data["plugin_id"], PLUGIN_ID)
        self.assertEqual(self._total(), before + 3)

    def test_import_zip_bundle_writes_questions(self) -> None:
        before = self._total()
        raw = _zip_bytes({"one.json": _question(111), "two.json": [_question(112), _question(113)]})
        status, data = self._import(raw, "pack.zip")
        self.assertEqual(status, 200, data)
        self.assertEqual(data["imported"], 3)
        self.assertEqual(self._total(), before + 3)

    def test_import_is_idempotent_for_the_same_ids(self) -> None:
        payload = {"questions": [_question(121)]}
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        status, first = self._import(raw, "again.json")
        self.assertEqual(status, 200, first)
        before = self._total()
        status, second = self._import(raw, "again.json")
        self.assertEqual(status, 200, second)
        self.assertEqual(second["imported"], 1)
        self.assertEqual(second["updated"], 1)
        self.assertEqual(self._total(), before, "同 ID 再导入不得多出题")

    def test_import_skip_mode_keeps_existing_question(self) -> None:
        raw = json.dumps({"questions": [_question(122)]}, ensure_ascii=False).encode("utf-8")
        status, first = self._import(raw, "skip.json")
        self.assertEqual(status, 200, first)
        before = self._total()
        status, second = self._import(raw, "skip.json", mode="skip")
        self.assertEqual(status, 200, second)
        self.assertEqual(second["imported"], 0)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(self._total(), before)

    def test_import_rejects_broken_package(self) -> None:
        status, data = self._import(b"{ not json", "bad.json")
        self.assertEqual(status, 400, data)
        status, data = self._import(b"not base64 at all !!", "bad.json")
        self.assertEqual(status, 400, data)

    def test_import_rejects_invalid_question_and_rolls_back_the_batch(self) -> None:
        before = self._total()
        broken = _question(131)
        broken["stem"] = ""              # 空题干不合契约
        payload = {"questions": [_question(130), broken]}
        status, data = self._import(json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                    "bad-question.json")
        self.assertEqual(status, 422, data)
        self.assertIn("errors", data["detail"])
        self.assertEqual(data["detail"]["errors"][0]["index"], 2)
        self.assertEqual(self._total(), before, "一题不合格必须整批回滚")

    def test_import_ignores_topic_nodes_this_bank_does_not_have(self) -> None:
        """别人的题包带着别人的大纲：硬挂到自己树上才是错挂，忽略并如实计数。"""
        document = _question(140)
        document["taxonomy"] = {"textbook": "人教A版", "topic_ids": ["tp_kxdeadc0de"]}
        raw = json.dumps({"questions": [document]}, ensure_ascii=False).encode("utf-8")
        status, data = self._import(raw, "topic.json")
        self.assertEqual(status, 200, data)
        self.assertEqual(data["dropped_topics"], 1)
        self.assertEqual(data["imported"], 1)
        status, stored = self._request(
            f"/api/bank/plugins/{PLUGIN_ID}/questions/q_pack000140"
        )
        self.assertEqual(status, 200, stored)
        self.assertNotIn("topic_ids", stored.get("taxonomy") or {})

    # ---------- 导出 ----------
    def test_export_returns_a_standard_bundle(self) -> None:
        request = urllib.request.Request(self.base + "/api/bank/export")
        request.add_header("Accept", "application/json")
        with urllib.request.urlopen(request, timeout=15) as response:
            self.assertEqual(response.status, 200)
            self.assertIn("attachment;", response.headers.get("Content-Disposition", ""))
            self.assertIn(".json", response.headers.get("Content-Disposition", ""))
            bundle = json.loads(response.read().decode("utf-8"))
        self.assertEqual(bundle["format"], "jiuzhang.question.bundle")
        self.assertEqual(bundle["plugin_id"], PLUGIN_ID)
        self.assertEqual(bundle["count"], len(bundle["questions"]))
        self.assertEqual(bundle["count"], self._total())

        from app.core.questions import validate_question  # noqa: PLC0415

        for document in bundle["questions"]:
            validate_question(document)

    def test_exported_bundle_can_be_imported_back(self) -> None:
        request = urllib.request.Request(self.base + "/api/bank/export")
        with urllib.request.urlopen(request, timeout=15) as response:
            bundle = json.loads(response.read().decode("utf-8"))
        raw = json.dumps(bundle, ensure_ascii=False).encode("utf-8")
        before = self._total()
        status, data = self._import(raw, "roundtrip.json")
        self.assertEqual(status, 200, data)
        self.assertEqual(data["imported"], bundle["count"])
        self.assertEqual(data["updated"], bundle["count"])
        self.assertEqual(self._total(), before, "导出的包再导入回来不得增删题目")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


if __name__ == "__main__":
    unittest.main()

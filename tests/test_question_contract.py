# -*- coding: utf-8 -*-
"""题目契约：dataclass 是唯一事实来源，磁盘上不再有 JSON Schema。"""

from __future__ import annotations

import unittest
from pathlib import Path

from app.core import question_contract, toml_io

ROOT = Path(__file__).resolve().parents[1]


def _document(**overrides):
    document = {
        "schema_version": "2.1",
        "id": "q_01J9Z3K4M5N6P7Q8R9S0T1V2W3",
        "type": "single_choice",
        "stem": "已知 $x=1$，求 $x+1$。",
        "options": [{"key": "A", "content": "$1$"}, {"key": "B", "content": "$2$"}],
        "answer": {"kind": "choice", "choice_keys": ["B"], "final": "B"},
        "difficulty": "L1",
        "meta": {
            "created_at": "2026-10-21T20:00:00+08:00",
            "updated_at": "2026-10-21T20:00:00+08:00",
            "revision": 1,
            "status": "published",
        },
    }
    document.update(overrides)
    return document


class QuestionContractTest(unittest.TestCase):
    def test_01_valid_document_roundtrips_as_dataclass(self) -> None:
        question = question_contract.validate(_document())
        self.assertEqual(question.id, "q_01J9Z3K4M5N6P7Q8R9S0T1V2W3")
        self.assertEqual(question.options[0].key, "A")
        self.assertEqual(question.as_document(), _document())

    def test_02_seed_questions_satisfy_contract(self) -> None:
        seeds = toml_io.load(
            ROOT / "examples" / "demo_plugin" / "seed" / "questions.toml", {}
        )["questions"]
        self.assertEqual(len(seeds), 5)
        for item in seeds:
            question_contract.validate(item)

    def test_03_missing_required_and_unknown_fields_are_rejected(self) -> None:
        broken = _document()
        del broken["difficulty"]
        broken["render_cache"] = "<article/>"
        with self.assertRaises(question_contract.ContractError) as caught:
            question_contract.validate(broken)
        messages = " ".join(caught.exception.errors)
        self.assertIn("difficulty", messages)
        self.assertIn("render_cache", messages)

    def test_04_choice_answers_are_type_specific(self) -> None:
        with self.assertRaises(question_contract.ContractError):
            question_contract.validate(
                _document(answer={"kind": "choice", "choice_keys": ["A", "B"]})
            )
        with self.assertRaises(question_contract.ContractError):
            question_contract.validate(_document(options=[]))

    def test_05_images_and_extensions_keep_their_guards(self) -> None:
        with self.assertRaises(question_contract.ContractError):
            question_contract.validate(
                _document(images=[{"id": "img_a1", "role": "option",
                                   "uri": "asset://img_a1"}])
            )
        with self.assertRaises(question_contract.ContractError):
            question_contract.validate(
                _document(images=[{"id": "img_a1", "role": "stem",
                                   "uri": "https://example.org/a.png"}])
            )
        with self.assertRaises(question_contract.ContractError):
            question_contract.validate(_document(extensions={"handwriting": {}}))

    def test_06_repo_ships_no_json_schema_files(self) -> None:
        self.assertEqual(list((ROOT / "schemas").glob("*.json")), [])

    def test_07_pages_point_at_the_contract_not_a_json_schema(self) -> None:
        for name in ("index.html", "plugins.html", "settings.html"):
            source = (ROOT / "static" / name).read_text(encoding="utf-8")
            self.assertNotIn("/schemas/", source, name)
        self.assertIn("/spec/question",
                      (ROOT / "static" / "index.html").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

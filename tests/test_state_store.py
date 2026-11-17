"""运行时状态存储只认 TOML：写进去的，读回来必须一字不差。

运行：``.venv/Scripts/python.exe -m unittest tests.test_state_store``
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.core import state_store


class StateStoreTomlRoundTripTest(unittest.TestCase):
    def test_01_table_write_then_read(self) -> None:
        payload = {
            "plugin_id": "org.jiuzhang.bank-engine",
            "workspaces": [{"id": "ws_a", "name": "甲"}, {"id": "ws_b", "name": "乙"}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "state.toml"
            state_store.save(path, payload)
            self.assertEqual(state_store.load_table(path), payload)
            self.assertEqual(state_store.load_records(path, "workspaces"), payload["workspaces"])


if __name__ == "__main__":
    unittest.main()
"""旧题库结构的兼容层：只保留 v1 引擎自建库所需 schema，不再携带旧业务数据。

新引擎的 31 表结构住在插件包 ``bank/schema.sql``；旧底座读写链路仍按 v1 结构
在独立数据库上运行，避免一次切换把录题与待审链路打穿。
"""

from __future__ import annotations

from pathlib import Path

LEGACY_SCHEMA_PATH = Path(__file__).with_name("bank_schema_v1.sql")

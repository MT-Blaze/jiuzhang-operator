"""九章算子底座。"""

from __future__ import annotations

import os
from pathlib import Path

__version__ = "0.5.2"


def _load_local_env() -> None:
    """Load repo-root .env into os.environ before submodules read their config.

    Already-exported variables win, so a shell can always override the file.
    """
    env_file = Path(__file__).resolve().parent.parent / ".env"
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, value = text.split("=", 1)
        key = key.strip()
        if key:
            os.environ.setdefault(key, value.strip())


_load_local_env()

"""构建 examples/placeholder_plugin.zip（官方占位插件包）。

流程与种子包一致：唯一顶层目录名 = 插件 id，满足 PLUGIN_SPEC §1.2 与安装器契约。
zip_url 由仓库根 plugins.json 索引指向本产物的 Raw 直链。

运行：``.venv/Scripts/python.exe examples/build_placeholder_plugin.py``
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "examples" / "placeholder_plugin"
OUTPUT_ZIP = ROOT / "examples" / "placeholder_plugin.zip"

# zip 内的唯一顶层目录名，必须等于 plugin.json 的 id
PLUGIN_ID = "org.jiuzhang.placeholder"

INCLUDED_FILES = (
    "plugin.json",
    "LICENSE",
    "README.md",
    "dist/index.html",
    "dist/plugin.css",
    "dist/plugin.js",
)


def main() -> None:
    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative in INCLUDED_FILES:
            source = SOURCE_DIR / relative
            if not source.is_file():
                raise SystemExit(f"缺少文件：{source}")
            zf.writestr(f"{PLUGIN_ID}/{relative}", source.read_bytes())

    print(f"OK: {OUTPUT_ZIP} ({OUTPUT_ZIP.stat().st_size} bytes, {len(INCLUDED_FILES)} files)")
    return sys.exit(0)


if __name__ == "__main__":
    main()

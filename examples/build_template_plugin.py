"""构建 examples/template-plugin.zip（第三方插件开发极简模板包）。

唯一顶层目录名 = 插件 id，满足 PLUGIN_SPEC §1.2 与安装器契约；
老师解压后改 id/目录名即可开发自己的插件。本包不进 dist 发放包（走仓库直链下载）。

运行：``.venv/Scripts/python.exe examples/build_template_plugin.py``
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "examples" / "template-plugin"
OUTPUT_ZIP = ROOT / "examples" / "template-plugin.zip"

# zip 内的唯一顶层目录名，必须等于 plugin.json 的 id
PLUGIN_ID = "org.example.template"

INCLUDED_FILES = (
    "plugin.json",
    "LICENSE",
    "dist/index.html",
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

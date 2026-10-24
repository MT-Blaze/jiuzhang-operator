"""构建军令 #16 模块三的取证夹具包（light 权重探针插件）。

只服务于 tools/stage_weight_probe.py：装进本机、验完就卸，不进官方插件索引、不进发行包。
zip 最外层目录名 == plugin.json 的 id（PLUGIN_SPEC §1.2），LICENSE 取仓库根那份 Apache-2.0 全文。

运行：``.venv/Scripts/python.exe examples/build_stage_weight_probe_plugin.py``
"""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "examples" / "stage_weight_probe_plugin"
OUTPUT_ZIP = ROOT / "examples" / "stage_weight_probe_plugin.zip"

PLUGIN_ID = "org.example.stage-weight"

INCLUDED_FILES = (
    "plugin.json",
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
            zf.write(source, f"{PLUGIN_ID}/{relative}")
        zf.write(ROOT / "LICENSE", f"{PLUGIN_ID}/LICENSE")
    print(f"OK: {OUTPUT_ZIP} ({OUTPUT_ZIP.stat().st_size} bytes)")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""构建 dist/jiuzhang-dev-kit.zip：发给协助开发老师的协作大礼包。

内容（顶层单目录 jiuzhang-dev-kit/，解压即用）：
  PLUGIN_SPEC.md          —— 插件契约唯一事实来源（源文件已归档在 docs/）（§8 即「如何用 AI 写插件」整段提示词）
  API_REFERENCE.md        —— 接口速查与宿主 Agent Prompt 契约
  PROJECT_MEMORY.md       —— 架构决策与欠账账本
  template-plugin/        —— 第三方插件开发极简模板源码
  template-plugin.zip     —— 同一模板的打包产物（可直接拖进底座安装）

红线自审（打包后立即执行，违令即删包并退出码 1）：
  包内不得出现 .env / 任何密钥载体、*.db 及其 sidecar、data/ 目录、
  真题库导出、.venv、.git、__pycache__、日志与临时产物。

运行：``.venv/Scripts/python.exe tools/build_dev_kit.py``
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "dist" / "jiuzhang-dev-kit.zip"
TOP = "jiuzhang-dev-kit"

SOURCES = (
    ("docs/PLUGIN_SPEC.md", "PLUGIN_SPEC.md"),
    ("docs/API_REFERENCE.md", "API_REFERENCE.md"),
    ("docs/PROJECT_MEMORY.md", "PROJECT_MEMORY.md"),
    ("examples/template-plugin/plugin.json", "template-plugin/plugin.json"),
    ("examples/template-plugin/LICENSE", "template-plugin/LICENSE"),
    ("examples/template-plugin/dist/index.html", "template-plugin/dist/index.html"),
    ("examples/template-plugin/dist/plugin.js", "template-plugin/dist/plugin.js"),
    ("examples/template-plugin.zip", "template-plugin.zip"),
)

FORBIDDEN_NAME = re.compile(
    r"(^|[/-])(\.env|\.git|\.venv|data|__pycache__|node_modules)([/-]|$)"
    r"|\.env(\.|$)|\.(db|db-shm|db-wal|db-journal|log|bak|key|pem)(\.|$)"
    r"|questions?\.json$|seed/questions",
    re.I,
)


def main() -> int:
    missing = [src for src, _ in SOURCES if not (ROOT / src).is_file()]
    if missing:
        print("缺少源文件：" + "、".join(missing))
        return 1

    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src, dest in SOURCES:
            zf.write(ROOT / src, f"{TOP}/{dest}")

    violations: list[str] = []
    with zipfile.ZipFile(OUT) as zf:
        names = zf.namelist()
        for name in names:
            if FORBIDDEN_NAME.search("/" + name):
                violations.append(name)
        # 文本载荷里再扫一遍常见密钥形态：礼包是给外部老师的，宁可误报也不漏报
        for info in zf.infolist():
            if not info.filename.endswith((".md", ".json", ".js", ".html")):
                continue
            body = zf.read(info.filename).decode("utf-8", errors="replace")
            for pattern in (r"sk-[A-Za-z0-9]{12,}", r"JZO_[A-Z_]*API_KEY\s*=\s*\S+",
                            r"Bearer\s+[A-Za-z0-9_\-\.]{20,}"):
                if re.search(pattern, body):
                    violations.append(f"{info.filename} 命中密钥形态 {pattern}")

    size = OUT.stat().st_size
    print(f"OK: {OUT} ({size} bytes, {len(names)} entries)")
    if violations:
        print("[红线自审] 违令条目，已删包：")
        for item in violations:
            print("  -", item)
        OUT.unlink()
        return 1
    print("[红线自审] 无 .env / *.db / data/ / 密钥形态条目")
    for name in names:
        print("  ", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

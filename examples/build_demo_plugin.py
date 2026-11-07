"""构建 examples/demo_plugin.zip（种子题库插件包）。

流程：
1. 用 `app/core/question_contract.py` 的 dataclass 契约逐题校验 seed/questions.toml；
2. 把题目内联进 dist/plugin.js 的构建副本（替换 ``/*__SEED_QUESTIONS__*/[]`` 占位）；
3. 打成 zip：唯一顶层目录名 = 插件 id，满足 PLUGIN_SPEC §1.2 与安装器契约。

运行：``.venv/Scripts/python.exe examples/build_demo_plugin.py``
"""

from __future__ import annotations

from app.core import wire  # noqa: E402
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "examples" / "demo_plugin"
OUTPUT_ZIP = ROOT / "examples" / "demo_plugin.zip"
QUESTIONS_PLACEHOLDER = "/*__SEED_QUESTIONS__*/[]"

# zip 内的唯一顶层目录名，必须等于 plugin.toml 的 id
PLUGIN_ID = "org.jiuzhang.demo-bank"

INCLUDED_FILES = (
    "plugin.toml",
    "LICENSE",
    "README.md",
    "seed/questions.toml",
    "dist/index.html",
    "dist/plugin.css",
    "dist/plugin.js",
)


def load_questions() -> list[dict]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from app.core import toml_io

    document = toml_io.load(SOURCE_DIR / "seed" / "questions.toml", {"questions": []})
    questions = document["questions"]
    if not isinstance(questions, list) or len(questions) != 5:
        raise SystemExit("seed/questions.toml 必须恰好包含 5 道题")

    from app.core import question_contract

    for index, question in enumerate(questions, start=1):
        try:
            question_contract.validate(question)
        except question_contract.ContractError as exc:
            raise SystemExit(
                f"第 {index} 题未通过 Question 契约校验：{'; '.join(exc.errors)}"
            ) from exc
    return questions


def build_plugin_js(questions: list[dict]) -> str:
    template = (SOURCE_DIR / "dist" / "plugin.js").read_text(encoding="utf-8")
    if QUESTIONS_PLACEHOLDER not in template:
        raise SystemExit(f"dist/plugin.js 缺少占位符 {QUESTIONS_PLACEHOLDER}")
    inline = wire.dumps(questions, ensure_ascii=False, indent=2)
    # 内联进 <script> 场景也要安全：杜绝 </script 提前闭合
    inline = inline.replace("</", "<\\/")
    return template.replace(QUESTIONS_PLACEHOLDER, inline)


def main() -> None:
    questions = load_questions()
    plugin_js = build_plugin_js(questions)

    if OUTPUT_ZIP.exists():
        OUTPUT_ZIP.unlink()
    with zipfile.ZipFile(OUTPUT_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for relative in INCLUDED_FILES:
            source = SOURCE_DIR / relative
            if not source.is_file():
                raise SystemExit(f"缺少文件：{source}")
            data = plugin_js.encode("utf-8") if relative == "dist/plugin.js" else source.read_bytes()
            zf.writestr(f"{PLUGIN_ID}/{relative}", data)

    print(f"OK: {OUTPUT_ZIP} ({OUTPUT_ZIP.stat().st_size} bytes, {len(INCLUDED_FILES)} files)")
    return sys.exit(0)


if __name__ == "__main__":
    main()

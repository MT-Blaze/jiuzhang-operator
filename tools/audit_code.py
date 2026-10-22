"""仓库静态审计：内存泄漏 / 死循环 / 危险前端 API / 测试硬编码。

只做“能被证据钉死”的检查，不猜语义。退出码 1 表示有 ERROR 级问题。
- JS 禁止正则后行断言（AGENTS §6：旧浏览器直接语法失败）；
- 宿主壳禁止 innerHTML（插件返回值必须净化后落 DOM）；
- 禁止 eval / new Function / 文档写入；
- 定时器必须有清理或被注释说明为常驻（启发式，报告不阻断）；
- Python 禁止在工作目录拼绝对路径、禁止 f-string 拼 SQL；
- 禁止测试令牌 / 测试临时目录泄漏进 app/ 与 static/。

用法：``.venv/Scripts/python.exe tools/audit_code.py``
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_SUFFIXES = {".py", ".js", ".html", ".css"}
SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache", ".system_generated"}
SKIP_ROOT_DIRS = {"dist", "data"}


@dataclass
class Finding:
    level: str
    rule: str
    path: str
    line: int
    detail: str


RULES: list[tuple[str, str, str, re.Pattern[str]]] = [
    ("ERROR", "js-lookbehind", "js", re.compile(r"\(\?<[=!]")),
    ("ERROR", "eval", "js", re.compile(r"\beval\s*\(")),
    ("ERROR", "new-function", "js", re.compile(r"\bnew\s+Function\s*\(")),
    ("ERROR", "document-write", "js", re.compile(r"document\.write\s*\(")),
    ("WARN", "host-innerhtml", "js", re.compile(r"\.innerHTML\s*=")),
    ("WARN", "outerhtml", "js", re.compile(r"\.outerHTML\s*=")),
    ("WARN", "absolute-windows-path", "any", re.compile(r"[A-Za-z]:\\\\(?!_)")),
    ("WARN", "sql-fstring", "py", re.compile(r"(?:execute|executemany)\s*\(\s*f[\"']")),
    ("WARN", "sql-format", "py", re.compile(r"(?:execute|executemany)\s*\(\s*[\"'][^\"']*(?:%s|\{\})", re.S)),
    ("WARN", "unbounded-while", "js", re.compile(r"while\s*\(\s*true\s*\)")),
    ("WARN", "test-token-leak", "any", re.compile(r"contract-test-token|plugin-install-test-token")),
    ("WARN", "shell-popen", "py", re.compile(r"os\.popen\s*\(")),
]


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TARGET_SUFFIXES:
            continue
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if relative.parts and relative.parts[0] in SKIP_ROOT_DIRS:
            continue
        # 仓库根的手动联调页不是宿主壳，单独人工看，不混进生产审计
        if relative.as_posix() == "test_workspace_integration.html":
            continue
        yield path


def kind_of(path: Path) -> str:
    if path.suffix == ".py":
        return "py"
    if path.suffix in {".js", ".html"}:
        return "js"
    return "css"


def scan(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(root):
        suffix = kind_of(path)
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative_parts = path.relative_to(root).parts
        for line_no, line in enumerate(text.splitlines(), 1):
            for level, rule, scope, pattern in RULES:
                if scope not in {"any", suffix}:
                    continue
                if rule == "test-token-leak" and (
                    not relative_parts
                    or relative_parts[0] not in {"app", "static", "plugins", "schemas"}
                ):
                    continue
                if pattern.search(line):
                    findings.append(
                        Finding(level, rule, str(path.relative_to(root)), line_no, line.strip()[:160])
                    )
        if suffix == "js":
            intervals = len(re.findall(r"setInterval\s*\(", text))
            cleared = len(re.findall(r"clearInterval\s*\(", text))
            if intervals and intervals > cleared and "常驻" not in text:
                findings.append(
                    Finding(
                        "INFO",
                        "interval-without-clear",
                        str(path.relative_to(root)),
                        0,
                        f"setInterval×{intervals}, clearInterval×{cleared}（常驻轮询需人工确认）",
                    )
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="九章算子静态审计")
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--strict", action="store_true", help="WARN 也按失败处理")
    args = parser.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):
        pass
    findings = scan(Path(args.root))

    for finding in findings:
        print(f"[{finding.level}] {finding.rule} {finding.path}:{finding.line}  {finding.detail}")

    errors = sum(1 for f in findings if f.level == "ERROR")
    warns = sum(1 for f in findings if f.level == "WARN")
    print(f"\n检查完成：ERROR {errors} · WARN {warns} · INFO {len(findings) - errors - warns}")
    if errors or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

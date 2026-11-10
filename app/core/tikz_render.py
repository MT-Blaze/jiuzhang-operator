"""TikZ 源码 → 矢量 SVG：本地 LaTeX 引擎的受控渲染器。

产品口径：图片从表里的 ``tikz_code`` 是一等源码，有值就先渲染成矢量图；
``path`` 原图永远保留，渲染失败/引擎缺失时前端照旧显示原图。

安全边界（代码来自 AI 或老师，一律按不可信输入处理）：
- 只接受 ``tikzpicture`` 代码片段，拒绝 ``\\input`` / ``\\write`` / ``\\openout``
  等读写文件或执行外部命令的原语；编译参数固定 ``-no-shell-escape``，
  并设 ``openin_any=p`` / ``openout_any=p``；
- 每次编译在独立临时目录里跑，超时即杀；产物只回传通过白名单检查的 SVG；
- 渲染结果按源码 SHA-256 缓存到当前工作区 ``uploads/tikz/``，只新增缓存文件，
  绝不删除或覆盖任何原图。
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import settings

ENGINE_LABEL = "xelatex+pdftocairo"
MAX_CODE = 20000
TIMEOUT_SECONDS = 25
MAX_SVG_BYTES = 4 * 1024 * 1024

# 只放行画图需要的命令；任何能读写文件、执行命令或改变类别码的写法都拒绝。
_FORBIDDEN = re.compile(
    r"\\(?:"
    r"input|include|includegraphics|openin|openout|closein|closeout|read|write|"
    r"immediate|special|catcode|csname|endcsname|directlua|latelua|"
    r"usepackage|RequirePackage|documentclass|begin\s*\{document\}|end\s*\{document\}|"
    r"pgfdeclareimage|pgfimage|pgfimage|pgfplotstabletypeset|"
    r"write18|ShellEscape|shellescape|IfFileExists|InputIfFileExists"
    r")(?![A-Za-z])",
    re.IGNORECASE,
)
_SAFE_SVG = re.compile(r"^(?:\ufeff)?(?:<\?xml[^>]*>\s*)?<svg[\s>]", re.IGNORECASE)
_UNSAFE_SVG = re.compile(
    r"<script|<foreignObject|\son[a-z]+\s*=|javascript:|<image\b|"
    r"(?:xlink:)?href\s*=\s*[\"'](?:https?:|//|file:)",
    re.IGNORECASE,
)

_TEMPLATE = r"""\documentclass[border=3pt]{standalone}
\usepackage{ctex}
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\usepackage{pgfplots}
\pgfplotsset{compat=1.18}
\usetikzlibrary{arrows.meta,calc,positioning,decorations.pathreplacing,patterns,shapes.geometric,angles,quotes,intersections}
\begin{document}
%s
\end{document}
"""

_lock = threading.Lock()
_failures: dict[str, str] = {}


class TikzError(RuntimeError):
    """渲染失败：路由把它映射成 422，前端收到后回退原图。"""


class TikzUnavailable(TikzError):
    """本机没有可用的 LaTeX 引擎；这是能力缺失，不是代码错误。"""


def _tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    # 开发机上的 TeX Live 不一定进了 PATH；发行包不带外部 TeX，找不到就如实降级。
    for base in ("E:/texlive/2026/bin/windows", "C:/texlive/2026/bin/windows"):
        candidate = Path(base) / (name + ".exe")
        if candidate.is_file():
            return str(candidate)
    return None


def status() -> dict[str, Any]:
    tex = _tool("xelatex")
    svg = _tool("pdftocairo")
    return {
        "available": bool(tex and svg),
        "engine": ENGINE_LABEL,
        "detail": "" if tex and svg else "未找到 xelatex/pdftocairo，TikZ 将回退为原图",
    }


def _normalize(code: str) -> str:
    text = str(code or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise TikzError("tikz_code 为空")
    if len(text) > MAX_CODE:
        raise TikzError("tikz_code 超过 %d 字符" % MAX_CODE)
    if _FORBIDDEN.search(text):
        raise TikzError("tikz_code 含不允许的 LaTeX 命令")
    if "\\begin{document}" in text or "\\end{document}" in text:
        raise TikzError("tikz_code 只接受图片片段，不要带文档环境")
    if "\\begin{tikzpicture}" not in text:
        text = "\\begin{tikzpicture}\n" + text + "\n\\end{tikzpicture}"
    return text


def _cache_dir() -> Path:
    root = Path(settings.uploads_dir) / "tikz"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()[:32]


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    env = os.environ.copy()
    env.update(
        {
            "openin_any": "p",
            "openout_any": "p",
            "shell_escape": "f",
            "TEXMFOUTPUT": str(cwd),
        }
    )
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        return subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=TIMEOUT_SECONDS,
            creationflags=flags,
        )
    except subprocess.TimeoutExpired as exc:
        raise TikzError("编译超时（%d 秒）" % TIMEOUT_SECONDS) from exc


def _compile(code: str) -> bytes:
    tex = _tool("xelatex")
    converter = _tool("pdftocairo")
    if not tex or not converter:
        raise TikzUnavailable("本机未安装 LaTeX/TikZ 引擎")

    work = Path(tempfile.mkdtemp(prefix="jzo-tikz-"))
    try:
        source = work / "figure.tex"
        source.write_text(_TEMPLATE % code, encoding="utf-8")
        result = _run(
            [
                tex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                "-no-shell-escape",
                "figure.tex",
            ],
            work,
        )
        pdf = work / "figure.pdf"
        if result.returncode != 0 or not pdf.is_file():
            tail = result.stdout.decode("utf-8", "replace")[-1200:]
            raise TikzError("LaTeX 编译失败：" + tail.strip().replace("\n", " ")[:300])
        out = work / "figure.svg"
        converted = _run([converter, "-svg", "figure.pdf", "figure.svg"], work)
        if converted.returncode != 0 or not out.is_file():
            raise TikzError("SVG 转换失败")
        data = out.read_bytes()
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if len(data) > MAX_SVG_BYTES:
        raise TikzError("渲染结果过大")
    text = data.decode("utf-8", "replace")
    if not _SAFE_SVG.match(text) or _UNSAFE_SVG.search(text):
        raise TikzError("渲染结果未通过安全校验")
    return data


def render(code: str) -> str:
    """渲染并返回底座托管的 SVG 地址；失败抛 ``TikzError``。"""
    normalized = _normalize(code)
    digest = _digest(normalized)
    target = _cache_dir() / (digest + ".svg")
    uri = "/static/uploads/tikz/" + digest + ".svg"
    if target.is_file() and target.stat().st_size > 0:
        return uri
    with _lock:
        if target.is_file() and target.stat().st_size > 0:
            return uri
        if digest in _failures:
            raise TikzError(_failures[digest])
        try:
            data = _compile(normalized)
        except TikzError as exc:
            if len(_failures) > 256:
                _failures.clear()
            _failures[digest] = str(exc)
            raise
        temp = target.with_name(target.name + ".%d.part" % os.getpid())
        temp.write_bytes(data)
        os.replace(temp, target)
    return uri


def resolve_image(image: dict[str, Any]) -> dict[str, Any]:
    """按「TikZ 矢量 > 原图 path」给一张图片补 ``tikz_uri``，原地返回。

    只新增派生字段，**不改写 ``uri`` / ``path``**：题目被插件读—改—写回传时，
    原图地址必须原样保留。渲染失败只记 ``tikz_error``，前端继续显示原图。
    """
    if not isinstance(image, dict):
        return image
    code = image.get("tikz_code")
    if not isinstance(code, str) or not code.strip():
        return image
    original_uri = image.get("uri")
    if not image.get("path") and isinstance(original_uri, str):
        image["path"] = original_uri
    try:
        uri = render(code)
    except TikzError as exc:
        image["tikz_error"] = str(exc)[:240]
        return image
    image["tikz_uri"] = uri
    image["tikz_engine"] = ENGINE_LABEL
    return image


def resolve_images(images: Any) -> Any:
    if isinstance(images, list):
        return [resolve_image(item) for item in images]
    return images


__all__ = [
    "ENGINE_LABEL",
    "TikzError",
    "TikzUnavailable",
    "render",
    "resolve_image",
    "resolve_images",
    "status",
]

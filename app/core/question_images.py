"""配图引用的安全判定与读路径派生字段的清洗。

题目文档里只保留图片事实（uri / path / tikz_code）；底座渲染出来的
``tikz_uri`` / ``tikz_engine`` / ``tikz_error`` 是派生结果，插件读—改—写
回传时必须摘掉，否则会把某次渲染的缓存地址当成原图存进题库。
"""

from __future__ import annotations

from typing import Any

DERIVED_IMAGE_FIELDS = ("tikz_uri", "tikz_engine", "tikz_error")


def _image_target(reference: str) -> str:
    if "{" in reference and "}" in reference:
        return reference[reference.find("{") + 1 : reference.rfind("}")].strip()
    if "](" in reference and reference.endswith(")"):
        return reference[reference.find("](") + 2 : -1].strip()
    return reference.strip()


def is_remote_image(reference: str) -> bool:
    """只有 http(s)、协议相对、data:、file: 算远程；asset:// 是底座逻辑地址，必须放行。"""
    target = _image_target(reference).strip("\"'")
    lowered = target.lower()
    if lowered.startswith(("asset://", "uploads/", "/static/", "./", "../")):
        return False
    return lowered.startswith(("http://", "https://", "//", "data:", "file:"))


def strip_derived_fields(images: Any) -> None:
    """读路径补的 TikZ 派生字段不落库：只保留原始图片事实。"""
    if not isinstance(images, list):
        return
    for image in images:
        if isinstance(image, dict):
            for key in DERIVED_IMAGE_FIELDS:
                image.pop(key, None)

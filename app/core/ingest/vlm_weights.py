"""本地 VLM 多座权重表与预取（安装接线卡座5/6）：SEATS 三座各自 GGUF＋mmproj。

发动机（llama-server）共享 engines/vlm/，权重按座住 engines/vlm/models/；
装拆按件互不误删（与公式专科共享目录同纪律）。sha256 逐件校验、三源测速选路、
浏览器 UA（hf-mirror 非 LFS 小件脚本 UA 403，座3 探针实证）；禁 GitHub。
座数据出处：docs/handoff/evidence/install-all/vlm_intern|vlm_minicpm/recon.md。
"""

from __future__ import annotations

import hashlib
import logging
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

from app.core import config
from app.core.ingest import mirrors

logger = logging.getLogger(__name__)

# （文件名, 字节数, sha256）：镜像仓 LFS oid 逐字核对（2026-11-19 侦查）。
SEATS: dict[str, dict[str, Any]] = {
    "qwen": {
        "label": "千问 Qwen2.5-VL",
        "repo": "unsloth/Qwen2.5-VL-3B-Instruct-GGUF",
        "size_note": "约 3.3GB",
        "files": (
            ("Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf", 1929901408,
             "c47e8c1f6fb3e8cff6ec58909baff16dbeffb64a5bb3b746b96e05e6334c129f"),
            ("mmproj-F16.gguf", 1338428256,
             "4c1240f514de94c81b70709b0f9a80c7e3297598ea7c83f39dc00b18ee5be60c"),
        )},
    "intern": {
        "label": "书生 InternVL3-2B",
        "repo": "mradermacher/InternVL3-2B-GGUF",
        "size_note": "约 1.74GB",
        "files": (
            ("InternVL3-2B.Q4_K_M.gguf", 1116759488,
             "201270a0982bdd0d246040c9aef46f35456f0cb1e60c2a96280b0c706052b7e8"),
            ("InternVL3-2B.mmproj-f16.gguf", 628237888,
             "99bc7344acdafbe38c908ee14439cfb68475aefbbd692cb7436cb80f0b8fef6b"),
        )},
    "minicpm": {
        "label": "面壁 MiniCPM-V-2.6",
        "repo": "OpenBMB/MiniCPM-V-2_6-gguf",
        "size_note": "约 4.85GB",
        "files": (
            ("ggml-model-Q3_K_M.gguf", 3806596448,
             "5a050acc927498ca4e05d38207bbd89d013154a7b9b24ac9ff4e45c870bc7f62"),
            ("mmproj-model-f16.gguf", 1044425152,
             "4485f68a0f1aa404c391e788ea88ea653c100d8e98fe572698f701e5809711fd"),
        )},
}


class VlmWeightsError(Exception):
    """权重预取失败（人话原因）。"""


def seat_of(entry_id: str) -> str:
    """catalog 条目 id（vlm_qwen/vlm_intern/vlm_minicpm）→ 座键；未知座显性。"""
    seat = str(entry_id).removeprefix("vlm_")
    if seat not in SEATS:
        raise VlmWeightsError("不认识的本地 VLM 座：%s" % entry_id)
    return seat


def _spec(seat: str) -> dict[str, Any]:
    if seat not in SEATS:
        raise VlmWeightsError("不认识的本地 VLM 座：%s" % seat)
    return SEATS[seat]


def engine_dir() -> Path:
    return config.PROJECT_ROOT / "engines" / "vlm"


def model_paths(seat: str = "qwen") -> tuple[Path, Path]:
    """（主题重 GGUF, 视觉投影 mmproj）落地路径；只读，不触发起服。"""
    files = _spec(seat)["files"]
    folder = engine_dir() / "models"
    return folder / files[0][0], folder / files[1][0]


def weights_ready(seat: str = "qwen") -> bool:
    """本座两件在不在本机（只读按字节数核对，不出网）；缺一律当不在。"""
    for path, (_name, size, _digest) in zip(model_paths(seat), _spec(seat)["files"]):
        try:
            if not path.is_file() or path.stat().st_size != size:
                return False
        except OSError:
            return False
    return True


def weight_urls(seat: str, name: str) -> list[tuple[str, str]]:
    """权重三源候选（国内）：仓不存在时测速/下载自然判败，不硬编结论。"""
    repo = _spec(seat)["repo"]
    return [
        ("ModelScope", "https://modelscope.cn/models/%s/resolve/master/%s" % (repo, name)),
        ("hf-mirror", "https://hf-mirror.com/%s/resolve/main/%s" % (repo, name)),
        ("GitCode", "https://gitcode.com/%s/resolve/main/%s" % (repo, name))]


def download_gguf(seat: str, name: str, size: int, digest: str,
                  sources: list[dict[str, Any]],
                  notify: Callable[[str], None]) -> None:
    """单件流式下载＋sha256＋原子改名；中断换下一家；全败抛人话错误。"""
    target = engine_dir() / "models" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    last_error = "没有可达的权重源"
    for row in sources:
        request = urllib.request.Request(
            row["url"], headers={"User-Agent": mirrors.WEIGHT_UA})
        hasher = hashlib.sha256()
        written = 0
        try:
            with urllib.request.urlopen(request, timeout=120) as response, \
                    part.open("wb") as sink:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    sink.write(chunk)
                    hasher.update(chunk)
                    written += len(chunk)
                    notify("正在从 %s 下载 %s（%.1f/%.1fGB）…"
                           % (row["name"], name, written / 1e9, size / 1e9))
            if written != size or hasher.hexdigest() != digest:
                raise OSError("字节数或 sha256 与仓库登记不符（实收 %d/%d 字节）"
                              % (written, size))
            part.replace(target)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            part.unlink(missing_ok=True)
            last_error = "%s → %s" % (row["name"], exc)
            logger.warning("%s 权重源失败：%s", _spec(seat)["label"], last_error)
            notify("权重源失败，换下一家（%s）" % last_error)
    raise VlmWeightsError("权重下载全败（%s）：%s" % (name, last_error))


def prefetch(seat: str, set_state: Callable[..., None]) -> bool:
    """本座 GGUF 预取并入安装点击：三源测速选路，两件逐一校验。"""
    spec = _spec(seat)
    set_state(step="预取权重",
              message="正在测速选权重源（modelscope/hf-mirror/gitcode），随后预取%s。"
                      % spec["size_note"])
    raced = mirrors.race(weight_urls(seat, spec["files"][0][0]))
    sources = [row for row in raced if row["ok"]]
    set_state(message=mirrors.pick_note(raced))
    if not sources:
        set_state(message="权重源全不通，GGUF 无法预取。")
        return False
    try:
        for name, size, digest in spec["files"]:
            target = engine_dir() / "models" / name
            if target.is_file() and target.stat().st_size == size:
                continue
            download_gguf(seat, name, size, digest, sources,
                          lambda message: set_state(message=message))
    except VlmWeightsError as exc:
        logger.warning("[WARN] %s 权重预取失败：%s", spec["label"], exc)
        set_state(message=str(exc))
        return False
    return weights_ready(seat)
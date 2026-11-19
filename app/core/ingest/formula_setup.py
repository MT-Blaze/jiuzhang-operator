"""公式专科权重一键装（PP-FormulaNet M/L＋Pix2Text·MFR，2.22.0 卡§2＋安装接线卡座2/3）。

权重住 engines/formula/models/（各档共享目录，按件落地/按件卸载，互不误删）。
底座 .venv 已带 onnxruntime（零新依赖、不建隔离环境）；PP 每变体只缺 onnx＋yml 两件
（yml 内嵌完整 tokenizer，M/L 词表同源；输入尺寸 M=384/L=768 由引擎硬编码）；
p2t 缺 encoder/decoder/tokenizer 三件（TrOCR 系官方 ONNX，词表 ByteLevel 解码）。
PP 主源 modelscope（onnx 取 RapidAI/RapidDoc 仓、L 的 yml 取 PaddlePaddle/PP-FormulaNet_plus-L
官方仓，字节数＋sha256 已核实，Apache-2.0）；p2t 主源 hf-mirror（breezedeus/pix2text-mfr
官方仓，lfs.oid 逐字核实，Apache-2.0）；其余镜像同路径候选参与点击内测速选路——
侦查实测无仓的家测速/校验自然判不通；下载后 sha256 逐件校验，绝不拿错文件加载。
安装/卸载只由老师界面点击发起；失败显性化，不静默。
"""

from __future__ import annotations

import hashlib
import logging
import shutil
import threading
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from app.core import config
from app.core.ingest import mirrors

logger = logging.getLogger(__name__)

# 每变体件表（文件名, 字节数, sha256, 仓, 仓内相对路径）：仓库页实测核对。
# PP-M 两件同出 RapidAI/RapidDoc；PP-L 的 onnx 出 RapidDoc、yml 出 PaddlePaddle 官方仓
# （RapidDoc 的 L 文件夹只有 onnx 无 yml）；p2t 三件出 hf-mirror breezedeus/pix2text-mfr
# 官方仓（encoder/decoder 的 sha256 取 lfs.oid，tokenizer 非 LFS 按官方 resolve 副本核）。
# 落地文件名统一带变体前/后缀，避免共享目录里相互覆盖。
VARIANTS: dict[str, dict[str, Any]] = {
    "m": {
        "label": "PP-FormulaNet·M",
        "size_note": "约 596MB",
        "files": (
            ("pp_formulanet_plus_m.onnx", 593908338,
             "52afa60ff51ad66cd7840a74188a058fe99081e617d3bd780117a2d67d94f50d",
             "RapidAI/RapidDoc", "formula/PP-FormulaNet_plus-M/pp_formulanet_plus_m.onnx"),
            ("pp_formulanet_plus_m_inference.yml", 2244564,
             "87b5f3d7f2b2fe553627d77b37f496608ca150ebd0ef62d362591edca47b5538",
             "RapidAI/RapidDoc", "formula/PP-FormulaNet_plus-M/pp_formulanet_plus_m_inference.yml"),
        ),
    },
    "l": {
        "label": "PP-FormulaNet·L",
        "size_note": "约 737MB",
        "files": (
            ("pp_formulanet_plus_l.onnx", 735058717,
             "f6686782c2bb5f84000ff9da4788ac672e736fa2d0652f483a140fa8401b3d32",
             "RapidAI/RapidDoc", "formula/PP-FormulaNet_plus-L/pp_formulanet_plus_l.onnx"),
            ("pp_formulanet_plus_l_inference.yml", 2244564,
             "afc92a2737268da0499c37b0b6741da268c369fd7424667fcfeb8fa6c7b22d30",
             "PaddlePaddle/PP-FormulaNet_plus-L", "inference.yml"),
        ),
    },
    "p2t": {
        "label": "Pix2Text·MFR",
        "size_note": "约 118MB",
        "files": (
            ("p2t_encoder.onnx", 87496990,
             "bd8d5c322792e9ec45793af5569e9748f82a3d728a9e00213dbfc56c1486f37d",
             "breezedeus/pix2text-mfr", "encoder_model.onnx"),
            ("p2t_decoder.onnx", 30114937,
             "fd0f92d7a012f3dae41e1ac79421aea0ea888b5a66cb3f9a004e424f82f3daed",
             "breezedeus/pix2text-mfr", "decoder_model.onnx"),
            ("p2t_tokenizer.json", 39161,
             "3e2ab757277d22639bec28c9d7972e352d3d1dba223051fa674002dc5ab64df3",
             "breezedeus/pix2text-mfr", "tokenizer.json"),
        ),
    },
}
WEIGHT_TIMEOUT = 120

_LOCK = threading.Lock()
_STATE: dict[str, dict[str, str]] = {
    v: {"state": "idle", "step": "", "message": ""} for v in VARIANTS}
_THREAD: dict[str, threading.Thread | None] = {v: None for v in VARIANTS}


class FormulaSetupError(Exception):
    """安装前置不满足或安装失败（人话原因）。"""


def _variant(variant: str) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise FormulaSetupError("公式变体只认 %s" % "/".join(VARIANTS))
    return VARIANTS[variant]


def engine_dir() -> Path:
    return config.PROJECT_ROOT / "engines" / "formula"


def model_paths(variant: str = "m") -> tuple[Path, ...]:
    """本变体各件落地路径；只读，不触发下载。"""
    files = _variant(variant)["files"]
    folder = engine_dir() / "models"
    return tuple(folder / spec[0] for spec in files)


def weights_ready(variant: str = "m") -> bool:
    """各件在不在本机（只读按字节数核对，不出网）；缺一律当不在。"""
    files = _variant(variant)["files"]
    for path, (_name, size, _digest, _repo, _rel) in zip(model_paths(variant), files):
        try:
            if not path.is_file() or path.stat().st_size != size:
                return False
        except OSError:
            return False
    return True


def status(variant: str = "m") -> dict[str, str]:
    """安装进度快照（只读）：state=idle/installing/done/error＋step＋人话。"""
    _variant(variant)
    with _LOCK:
        return dict(_STATE[variant])


def _set(variant: str, **fields: str) -> None:
    with _LOCK:
        _STATE[variant].update(fields)


def _weight_urls(repo: str, rel: str) -> list[tuple[str, str]]:
    return [
        ("ModelScope", "https://modelscope.cn/models/%s/resolve/master/%s" % (repo, rel)),
        ("hf-mirror", "https://hf-mirror.com/%s/resolve/main/%s" % (repo, rel)),
        ("GitCode", "https://gitcode.com/%s/resolve/main/%s" % (repo, rel)),
    ]


def _download_one(variant: str, spec: tuple, sources: list[dict[str, Any]]) -> None:
    """单件流式下载＋sha256＋原子改名；中断同源重试一次再换下一家；全败抛人话错误。"""
    name, size, digest, repo, rel = spec
    label = VARIANTS[variant]["label"]
    target = engine_dir() / "models" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    # 测速只探首件链接，各家延迟排序可复用；但每件必须按自己的仓/路径重新解析
    # 链接——拿 onnx 的链接下 yml 会收错文件（2.20.0 探针实证同款坑）。
    urls = dict(_weight_urls(repo, rel))
    last_error = "没有可达的权重源"
    for row in sources:
        url = urls.get(row["name"], row["url"])
        for attempt in (1, 2):
            hasher = hashlib.sha256()
            written = 0
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": mirrors.WEIGHT_UA})
                with urllib.request.urlopen(request, timeout=WEIGHT_TIMEOUT) as response, \
                        part.open("wb") as sink:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        sink.write(chunk)
                        hasher.update(chunk)
                        written += len(chunk)
                        _set(variant, message="正在从 %s 下载 %s（%.1f/%.1fMB）…"
                             % (row["name"], name, written / 1e6, size / 1e6))
                if written != size or hasher.hexdigest() != digest:
                    raise OSError("字节数或 sha256 与仓库登记不符（实收 %d/%d 字节）"
                                  % (written, size))
                part.replace(target)
                return
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                part.unlink(missing_ok=True)
                last_error = "%s → %s" % (row["name"], exc)
                logger.warning("%s 权重源失败（第 %d 次）：%s", label, attempt, last_error)
                if attempt == 1:
                    _set(variant, message="下载中断，同源重试中（%s）" % last_error)
                    continue
                _set(variant, message="权重源失败，换下一家（%s）" % last_error)
    raise FormulaSetupError("权重下载全败（%s）：%s" % (name, last_error))


def start_install(variant: str = "m") -> dict[str, str]:
    """老师点击才走到这里：已装直接 done；在装复用；否则起后台线程。"""
    spec = _variant(variant)
    label, size_note = spec["label"], spec["size_note"]
    if weights_ready(variant):
        _set(variant, state="done", step="体检",
             message="%s 权重已在本机，无需再下。" % label)
        return status(variant)
    with _LOCK:
        if _THREAD[variant] is not None and _THREAD[variant].is_alive():
            return dict(_STATE[variant])
        _STATE[variant].update({"state": "installing", "step": "测速选源",
                                "message": "正在测速选权重源（modelscope/hf-mirror/gitcode），"
                                           "随后下载%s。" % size_note})
        _THREAD[variant] = threading.Thread(
            target=_install, args=(variant,), name="jzo-formula-%s-install" % variant,
            daemon=True)
    _THREAD[variant].start()
    return status(variant)


def _install(variant: str) -> None:
    spec = _variant(variant)
    label = spec["label"]
    try:
        first = spec["files"][0]
        raced = mirrors.race(_weight_urls(first[3], first[4]))
        sources = [row for row in raced if row["ok"]]
        _set(variant, step="下载权重", message=mirrors.pick_note(raced))
        if not sources:
            raise FormulaSetupError("权重源全不通（modelscope/hf-mirror/gitcode），无法下载。")
        for file_spec in spec["files"]:
            target = engine_dir() / "models" / file_spec[0]
            if target.is_file() and target.stat().st_size == file_spec[1]:
                continue
            _download_one(variant, file_spec, sources)
        _set(variant, state="done", step="完成",
             message="%s 已就绪（各件权重 sha256 校验通过）。" % label)
        logger.info("[INFO] %s 安装收口：%s", label, status(variant).get("message"))
    except FormulaSetupError as exc:
        _set(variant, state="error", message=str(exc))
        logger.warning("[WARN] %s 安装失败：%s", label, exc)
    except Exception as exc:  # noqa: BLE001 - 后台线程任何异常都要显性化
        _set(variant, state="error", message="安装异常：%s" % exc)
        logger.warning("[WARN] %s 安装异常：%s", label, exc)


def uninstall(variant: str = "m") -> dict[str, Any]:
    """老师点【卸载】＋确认后才走到这里：只删本变体各件（共享目录互不误删）。"""
    spec = _variant(variant)
    label = spec["label"]
    with _LOCK:
        if _THREAD[variant] is not None and _THREAD[variant].is_alive():
            raise FormulaSetupError("正在安装中，不能同时卸载；等安装收口后再试。")
    folder = engine_dir()
    if folder.parent != config.PROJECT_ROOT / "engines":
        raise FormulaSetupError("卸载路径不对（%s），拒绝动手。" % folder)
    from app.core.ingest.recognize import (  # noqa: PLC0415 - 按需导入防循环
        formula_p2t, formula_pp_l, formula_pp_m,
    )

    {"m": formula_pp_m, "l": formula_pp_l, "p2t": formula_p2t}[variant].reset()
    paths = model_paths(variant)
    if not any(p.is_file() for p in paths):
        _set(variant, state="idle", step="", message="")
        return {"ok": True, "message": "%s 权重本来就没下，无需卸载。" % label}
    try:
        for path in paths:
            path.unlink(missing_ok=True)
        # 共享目录里别的变体还在就保留；全空了才连目录删（保 M 单座卸载删净口径）。
        models_folder = folder / "models"
        if models_folder.is_dir() and not any(models_folder.iterdir()):
            shutil.rmtree(folder)
    except OSError as exc:
        raise FormulaSetupError("卸载删不掉 %s 权重：%s（可能有会话占用，稍后再试）" % (label, exc))
    _set(variant, state="idle", step="", message="")
    logger.info("[INFO] %s 已卸载：%s", label, paths)
    return {"ok": True, "message": "%s 已卸载（本档权重删净，其他公式档与底座 OCR 不受影响）。" % label}
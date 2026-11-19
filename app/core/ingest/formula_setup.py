"""PP-FormulaNet·M 权重一键装（2.22.0 卡§2）：engines/formula/models/ 权重目录。

底座 .venv 已带 onnxruntime（零新依赖、不建隔离环境）；只缺 onnx＋yml 两件权重
（yml 内嵌完整 tokenizer，无需另下词表）。主源 modelscope（RapidAI/RapidDoc 仓
已核实字节数＋sha256，Apache-2.0），hf-mirror/gitcode 同路径候选参与点击内测速
选路——侦查实测两家无此仓库，测速/校验自然判不通；下载后 sha256 逐件校验，
绝不拿错文件加载。安装/卸载只由老师界面点击发起；失败显性化，不静默。
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

# （任务, 文件名, 字节数, sha256）：modelscope RapidAI/RapidDoc 仓库页实测核对（2026-11-19）。
WEIGHT_FILES = (
    ("model", "pp_formulanet_plus_m.onnx", 593908338,
     "52afa60ff51ad66cd7840a74188a058fe99081e617d3bd780117a2d67d94f50d"),
    ("config", "pp_formulanet_plus_m_inference.yml", 2244564,
     "87b5f3d7f2b2fe553627d77b37f496608ca150ebd0ef62d362591edca47b5538"),
)
WEIGHT_TIMEOUT = 120

_LOCK = threading.Lock()
_STATE: dict[str, str] = {"state": "idle", "step": "", "message": ""}
_THREAD: threading.Thread | None = None


class FormulaSetupError(Exception):
    """安装前置不满足或安装失败（人话原因）。"""


def engine_dir() -> Path:
    return config.PROJECT_ROOT / "engines" / "formula"


def model_paths() -> tuple[Path, Path]:
    """（onnx, yml）落地路径；只读，不触发下载。"""
    folder = engine_dir() / "models"
    return folder / WEIGHT_FILES[0][1], folder / WEIGHT_FILES[1][1]


def weights_ready() -> bool:
    """两件在不在本机（只读按字节数核对，不出网）；缺一律当不在。"""
    for path, (_task, _name, size, _digest) in zip(model_paths(), WEIGHT_FILES):
        try:
            if not path.is_file() or path.stat().st_size != size:
                return False
        except OSError:
            return False
    return True


def status() -> dict[str, str]:
    """安装进度快照（只读）：state=idle/installing/done/error＋step＋人话。"""
    with _LOCK:
        return dict(_STATE)


def _set(**fields: str) -> None:
    with _LOCK:
        _STATE.update(fields)


def _weight_urls(task: str, name: str) -> list[tuple[str, str]]:
    rel = "formula/PP-FormulaNet_plus-M/%s" % name
    return [
        ("ModelScope", "https://modelscope.cn/models/RapidAI/RapidDoc/"
                       "resolve/master/" + rel),
        ("hf-mirror", "https://hf-mirror.com/RapidAI/RapidDoc/resolve/main/" + rel),
        ("GitCode", "https://gitcode.com/RapidAI/RapidDoc/resolve/main/" + rel),
    ]


def _download_one(task: str, name: str, size: int, digest: str,
                  sources: list[dict[str, Any]]) -> None:
    """单件流式下载＋sha256＋原子改名；中断同源重试一次再换下一家；全败抛人话错误。"""
    target = engine_dir() / "models" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_suffix(target.suffix + ".part")
    # 测速只探首件链接，各家延迟排序可复用；但每件必须按自己的文件名重新解析
    # 链接——拿 onnx 的链接下 yml 会收错文件（2.20.0 探针实证同款坑）。
    urls = dict(_weight_urls(task, name))
    last_error = "没有可达的权重源"
    for row in sources:
        url = urls.get(row["name"], row["url"])
        for attempt in (1, 2):
            hasher = hashlib.sha256()
            written = 0
            try:
                with urllib.request.urlopen(url, timeout=WEIGHT_TIMEOUT) as response, \
                        part.open("wb") as sink:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        sink.write(chunk)
                        hasher.update(chunk)
                        written += len(chunk)
                        _set(message="正在从 %s 下载 %s（%.1f/%.1fMB）…"
                             % (row["name"], name, written / 1e6, size / 1e6))
                if written != size or hasher.hexdigest() != digest:
                    raise OSError("字节数或 sha256 与仓库登记不符（实收 %d/%d 字节）"
                                  % (written, size))
                part.replace(target)
                return
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                part.unlink(missing_ok=True)
                last_error = "%s → %s" % (row["name"], exc)
                logger.warning("PP-FormulaNet·M 权重源失败（第 %d 次）：%s", attempt, last_error)
                if attempt == 1:
                    _set(message="下载中断，同源重试中（%s）" % last_error)
                    continue
                _set(message="权重源失败，换下一家（%s）" % last_error)
    raise FormulaSetupError("权重下载全败（%s）：%s" % (name, last_error))


def start_install() -> dict[str, str]:
    """老师点击才走到这里：已装直接 done；在装复用；否则起后台线程。"""
    global _THREAD
    if weights_ready():
        _set(state="done", step="体检", message="PP-FormulaNet·M 权重已在本机，无需再下。")
        return status()
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            return dict(_STATE)
        _STATE.update({"state": "installing", "step": "测速选源",
                       "message": "正在测速选权重源（modelscope/hf-mirror/gitcode），"
                                  "随后下载约 596MB。"})
        _THREAD = threading.Thread(target=_install, name="jzo-formula-install", daemon=True)
    _THREAD.start()
    return status()


def _install() -> None:
    try:
        raced = mirrors.race(_weight_urls(*WEIGHT_FILES[0][:2]))
        sources = [row for row in raced if row["ok"]]
        _set(step="下载权重", message=mirrors.pick_note(raced))
        if not sources:
            raise FormulaSetupError("权重源全不通（modelscope/hf-mirror/gitcode），无法下载。")
        for task, name, size, digest in WEIGHT_FILES:
            target = engine_dir() / "models" / name
            if target.is_file() and target.stat().st_size == size:
                continue
            _download_one(task, name, size, digest, sources)
        _set(state="done", step="完成",
             message="PP-FormulaNet·M 已就绪（onnx/yml 两件权重校验通过）。")
        logger.info("[INFO] PP-FormulaNet·M 安装收口：%s", status().get("message"))
    except FormulaSetupError as exc:
        _set(state="error", message=str(exc))
        logger.warning("[WARN] PP-FormulaNet·M 安装失败：%s", exc)
    except Exception as exc:  # noqa: BLE001 - 后台线程任何异常都要显性化
        _set(state="error", message="安装异常：%s" % exc)
        logger.warning("[WARN] PP-FormulaNet·M 安装异常：%s", exc)


def uninstall() -> dict[str, Any]:
    """老师点【卸载】＋确认后才走到这里：整个 engines/formula/ 删掉（含权重）。"""
    with _LOCK:
        if _THREAD is not None and _THREAD.is_alive():
            raise FormulaSetupError("正在安装中，不能同时卸载；等安装收口后再试。")
    folder = engine_dir()
    if folder.parent != config.PROJECT_ROOT / "engines":
        raise FormulaSetupError("卸载路径不对（%s），拒绝动手。" % folder)
    from app.core.ingest.recognize import formula_pp_m  # noqa: PLC0415 - 按需导入防循环

    formula_pp_m.reset()
    if not folder.exists():
        _set(state="idle", step="", message="")
        return {"ok": True, "message": "PP-FormulaNet·M 权重本来就没下，无需卸载。"}
    try:
        shutil.rmtree(folder)
    except OSError as exc:
        raise FormulaSetupError("卸载删不掉 engines/formula/：%s（可能有会话占用，稍后再试）" % exc)
    _set(state="idle", step="", message="")
    logger.info("[INFO] PP-FormulaNet·M 已卸载：%s", folder)
    return {"ok": True, "message": "PP-FormulaNet·M 已卸载（权重全删，底座 OCR 不受影响）。"}
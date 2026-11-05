"""AI 配置中心：多厂商密钥池 + 四任务指派。

与 Provider 注册表的分工：注册表管「系统预置档」，这里管「老师自己加的账号」。
非密钥字段（名称、Base URL、任务指派）落当前工作区 ``config.json``；
API Key 只写当前工作区 ``.env`` 与 ``os.environ``，热生效、永不入库、永不下发明文。

红线（AGENTS §5 / STACK §1.6）：
- 任何读接口只回掩码（``sk-xx••••xx``）或「是否已配置」，不回 Key 原文；
- 写接口一律由 API 层加 ``X-JZO-Token``；
- 模型列表是底座替用户发起的外部请求，必须由用户点击触发，不设定时拉取。
"""

from __future__ import annotations

import json
import os
import re
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.core.provider_config import ProviderConfigError, env_file_path, validate_base_url

STATE_KEY = "ai_center"
ENV_PREFIX = "JZO_AIPOOL_"
ACCOUNT_ID_RE = re.compile(r"^acc_[0-9a-f]{10}$")
NAME_MAX = 40
MODEL_MAX = 128
KEY_MAX = 512
MODEL_LIST_MAX = 300
MODEL_FETCH_TIMEOUT = 10

TASKS: tuple[tuple[str, str], ...] = (
    ("ocr", "视觉识别(OCR)"),
    ("solve", "解题"),
    ("meta", "元数据"),
    ("tikz", "TikZ"),
)
TASK_KEYS = {key for key, _ in TASKS}
TASK_LABELS = dict(TASKS)


@dataclass(frozen=True)
class TaskBinding:
    """一次任务指派解析出的可用配置；``is_configured`` 为假时不许出网。"""

    task: str
    account_id: str
    name: str
    base_url: str
    api_key: str
    model: str

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)


class AiCenterError(ProviderConfigError):
    """配置被拒绝，``message`` 必须是给人看的话。"""


# ---------- 持久化 ----------


def _config_path() -> Path:
    return settings.config_path


def _read_document() -> dict[str, object]:
    try:
        document = json.loads(_config_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return document if isinstance(document, dict) else {}


def _write_document(document: dict[str, object]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def _clean_name(raw: str) -> str:
    name = " ".join(str(raw or "").split())
    if not name:
        raise AiCenterError("名称不能为空")
    if len(name) > NAME_MAX:
        raise AiCenterError(f"名称最长 {NAME_MAX} 个字符")
    return name


def _clean_key(raw: str) -> str:
    key = str(raw or "").strip()
    if len(key) > KEY_MAX:
        raise AiCenterError(f"API Key 最长 {KEY_MAX} 个字符")
    if "\n" in key or "\r" in key:
        raise AiCenterError("API Key 不能包含换行")
    return key


def _clean_model(raw: str) -> str:
    model = str(raw or "").strip()
    if len(model) > MODEL_MAX:
        raise AiCenterError(f"模型名最长 {MODEL_MAX} 个字符")
    if "\n" in model or "\r" in model:
        raise AiCenterError("模型名不能包含换行")
    return model


def _env_names(account_id: str) -> tuple[str, str]:
    prefix = f"{ENV_PREFIX}{account_id[4:].upper()}_"
    return prefix + "BASE_URL", prefix + "API_KEY"


def _load_state() -> dict[str, object]:
    """读当前工作区的账号池；损坏的条目直接丢弃，不拿半截配置去出网。"""
    raw = _read_document().get(STATE_KEY)
    if not isinstance(raw, dict):
        return {"accounts": [], "assignments": {}}
    accounts: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for entry in raw.get("accounts") or []:
        if not isinstance(entry, dict):
            continue
        account_id = str(entry.get("id") or "")
        name = " ".join(str(entry.get("name") or "").split())
        if not ACCOUNT_ID_RE.match(account_id) or account_id in seen_ids or not name:
            continue
        if name.casefold() in seen_names:
            continue
        try:
            base_url = validate_base_url(str(entry.get("base_url") or ""))
        except ProviderConfigError:
            continue
        seen_ids.add(account_id)
        seen_names.add(name.casefold())
        accounts.append({"id": account_id, "name": name, "base_url": base_url})
    assignments: dict[str, dict[str, str]] = {}
    source = raw.get("assignments")
    if isinstance(source, dict):
        for task in TASK_KEYS:
            item = source.get(task)
            if not isinstance(item, dict):
                continue
            account_id = str(item.get("account_id") or "")
            model = str(item.get("model") or "").strip()
            if account_id in seen_ids and model and len(model) <= MODEL_MAX:
                assignments[task] = {"account_id": account_id, "model": model}
    return {"accounts": accounts, "assignments": assignments}


def _save_state(state: dict[str, object]) -> None:
    document = _read_document()
    document[STATE_KEY] = state
    _write_document(document)


def _update_env_file(pairs: dict[str, str], remove: tuple[str, ...] = ()) -> None:
    """写/删工作区 .env：已有键原位替换，删除键整行移除，其余原样保留。"""
    path = env_file_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    dropped = set(remove)
    pending = dict(pairs)
    output: list[str] = []
    for line in lines:
        text = line.strip()
        if text and not text.startswith("#") and "=" in text:
            key = text.split("=", 1)[0].strip()
            if key in dropped:
                continue
            if key in pending:
                output.append(f"{key}={pending.pop(key)}")
                continue
        output.append(line)
    for key, value in pending.items():
        output.append(f"{key}={value}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text("\n".join(output) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ---------- 读接口 ----------


def mask_key(key: str) -> str:
    """只回「看得出来是哪把」的掩码：前 4 后 2，短 Key 一律四点。"""
    text = str(key or "").strip()
    if not text:
        return ""
    if len(text) <= 6:
        return "••••"
    return text[:4] + "••••" + text[-2:]


def _account_key(account_id: str) -> str:
    _, key_name = _env_names(account_id)
    return os.environ.get(key_name, "").strip()


def _account_public(account: dict[str, str]) -> dict[str, object]:
    key = _account_key(account["id"])
    return {
        "id": account["id"],
        "name": account["name"],
        "base_url": account["base_url"],
        "api_key_masked": mask_key(key),
        "configured": bool(key and account["base_url"]),
    }


def cluster() -> dict[str, object]:
    """整块给前端：任务清单、账号（掩码）、当前指派。"""
    state = _load_state()
    accounts = [_account_public(item) for item in state["accounts"]]
    by_id = {item["id"]: item for item in accounts}
    assignments: dict[str, object] = {}
    for task in TASK_KEYS:
        item = state["assignments"].get(task)
        if not item:
            assignments[task] = {"account_id": "", "account_name": "", "model": "", "ready": False}
            continue
        account = by_id.get(item["account_id"])
        assignments[task] = {
            "account_id": item["account_id"],
            "account_name": account["name"] if account else "",
            "model": item["model"],
            "ready": bool(account and account["configured"]),
        }
    return {
        "tasks": [{"key": key, "label": label} for key, label in TASKS],
        "accounts": accounts,
        "assignments": assignments,
    }


def resolve_task(task: str) -> TaskBinding:
    """任务 → 可出网配置；没指派或没填齐时返回空档，调用方自行拒绝。"""
    if task not in TASK_KEYS:
        raise AiCenterError(f"未知任务：{task}")
    state = _load_state()
    assigned = state["assignments"].get(task) or {}
    account = next(
        (item for item in state["accounts"] if item["id"] == assigned.get("account_id")), None
    )
    if not account:
        return TaskBinding(task, "", "", "", "", "")
    return TaskBinding(
        task=task,
        account_id=account["id"],
        name=account["name"],
        base_url=account["base_url"],
        api_key=_account_key(account["id"]),
        model=str(assigned.get("model") or ""),
    )


def find_mineru() -> TaskBinding | None:
    """按名称找 MinerU 账号；没有可用 Key 就当没配，绝不拿空 Key 出网。"""
    for account in _load_state()["accounts"]:
        if "mineru" not in account["name"].casefold():
            continue
        key = _account_key(account["id"])
        if not key:
            continue
        return TaskBinding(
            task="ocr",
            account_id=account["id"],
            name=account["name"],
            base_url=account["base_url"],
            api_key=key,
            model="mineru",
        )
    return None


# ---------- 写接口 ----------


def save_account(
    account_id: str | None = None,
    name: str = "",
    base_url: str = "",
    api_key: str | None = None,
) -> dict[str, object]:
    """新增或修改账号。``api_key=None`` 保留旧 Key；空串表示清掉 Key。"""
    state = _load_state()
    clean_name = _clean_name(name)
    try:
        clean_url = validate_base_url(base_url)
    except ProviderConfigError as exc:
        raise AiCenterError(str(exc)) from exc
    clean_key = _clean_key(api_key) if api_key is not None else None
    accounts = state["accounts"]
    target = None
    if account_id:
        target = next((item for item in accounts if item["id"] == account_id), None)
        if target is None:
            raise AiCenterError("账号不存在，可能已被删除")
    for item in accounts:
        if item["id"] != account_id and item["name"].casefold() == clean_name.casefold():
            raise AiCenterError(f"名称「{clean_name}」已被另一个账号占用")

    if target is None:
        # 先落 .env 再写 config：任何一步失败都不留「有账号、没密钥」的半截状态。
        target = {"id": "acc_" + secrets.token_hex(5), "name": clean_name, "base_url": clean_url}
        accounts.append(target)
    else:
        target["name"] = clean_name
        target["base_url"] = clean_url

    base_name, key_name = _env_names(target["id"])
    if clean_key is not None:
        if clean_key:
            _update_env_file({base_name: clean_url, key_name: clean_key})
            os.environ[base_name] = clean_url
            os.environ[key_name] = clean_key
        else:
            _update_env_file({}, remove=(base_name, key_name))
            os.environ.pop(key_name, None)
            os.environ[base_name] = clean_url
    else:
        _update_env_file({base_name: clean_url})
        os.environ[base_name] = clean_url

    _save_state(state)
    return _account_public(target)


def delete_account(account_id: str) -> dict[str, object]:
    state = _load_state()
    accounts = state["accounts"]
    target = next((item for item in accounts if item["id"] == account_id), None)
    if target is None:
        raise AiCenterError("账号不存在，可能已被删除")
    state["accounts"] = [item for item in accounts if item["id"] != account_id]
    state["assignments"] = {
        task: item
        for task, item in state["assignments"].items()
        if item.get("account_id") != account_id
    }
    base_name, key_name = _env_names(account_id)
    _update_env_file({}, remove=(base_name, key_name))
    os.environ.pop(base_name, None)
    os.environ.pop(key_name, None)
    _save_state(state)
    return cluster()


def assign_task(task: str, account_id: str, model: str) -> dict[str, object]:
    if task not in TASK_KEYS:
        raise AiCenterError(f"未知任务：{task}")
    state = _load_state()
    account = next((item for item in state["accounts"] if item["id"] == account_id), None)
    if account is None:
        raise AiCenterError("指派目标账号不存在")
    clean_model = _clean_model(model)
    if not clean_model:
        raise AiCenterError("模型名不能为空；下拉里没有就手动输入")
    assignments = dict(state["assignments"])
    assignments[task] = {"account_id": account_id, "model": clean_model}
    state["assignments"] = assignments
    _save_state(state)
    return cluster()


# ---------- 出网：模型列表（用户点击触发） ----------


def _models_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/models"


def fetch_models(
    account_id: str = "",
    base_url: str = "",
    api_key: str = "",
) -> dict[str, object]:
    """读一次 ``GET {base}/models``。

    已保存账号按 id 取库中 Key；未保存账号必须把刚填的 Key 一并交来
    （不回显、不落盘），方便老师先看模型再保存。
    """
    if account_id:
        state = _load_state()
        account = next((item for item in state["accounts"] if item["id"] == account_id), None)
        if account is None:
            raise AiCenterError("账号不存在，可能已被删除")
        target_base = account["base_url"]
        target_key = _account_key(account_id)
    else:
        try:
            target_base = validate_base_url(base_url)
        except ProviderConfigError as exc:
            raise AiCenterError(str(exc)) from exc
        target_key = _clean_key(api_key)
    if not target_key:
        raise AiCenterError("先填 API Key，才能拉取模型列表")

    host = urlparse(target_base).netloc
    request = urllib.request.Request(
        _models_url(target_base),
        headers={"Authorization": f"Bearer {target_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=MODEL_FETCH_TIMEOUT) as response:
            body = response.read(512 * 1024).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        hint = {401: "密钥被拒（401）", 403: "无权限（403）", 404: "该地址没有 /models 接口（404）"}.get(
            exc.code, f"HTTP {exc.code}"
        )
        return {"ok": False, "models": [], "host": host, "detail": f"接口可达但报错：{hint}"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return {"ok": False, "models": [], "host": host, "detail": f"连不上：{reason}"}

    try:
        document = json.loads(body)
    except json.JSONDecodeError:
        return {"ok": False, "models": [], "host": host, "detail": "接口返回的不是 JSON"}
    rows = document.get("data") if isinstance(document, dict) else None
    models: list[str] = []
    seen: set[str] = set()
    for row in rows if isinstance(rows, list) else []:
        value = row.get("id") if isinstance(row, dict) else row
        model = str(value or "").strip()
        if model and model not in seen and len(model) <= MODEL_MAX:
            seen.add(model)
            models.append(model)
        if len(models) >= MODEL_LIST_MAX:
            break
    if not models:
        return {"ok": False, "models": [], "host": host, "detail": "接口可达，但没有返回任何模型 id"}
    return {"ok": True, "models": models, "host": host, "detail": f"拉到 {len(models)} 个模型"}

"""Provider 配置面板的后端能力：把用户亲手填的密钥写回本机 .env，并做连通性测试。

红线对齐（AGENTS §5 / STACK §1.6）：
- 密钥只落环境变量与本机 .env（已 gitignore），永不入库、永不写日志、永不下发前端；
- .env 路径可被 ``JZO_ENV_FILE`` 覆盖（测试与启动器专用），默认仓库根；
- 连通性测试是底座替用户发起的外部请求，与索引拉取同一口径：必须带一次性写令牌。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import PROJECT_ROOT
from app.core.providers import ProviderProfile

TEST_TIMEOUT_SECONDS = 10


class ProviderConfigError(Exception):
    """配置被拒绝，``message`` 必须是给人看的话。"""


def env_file_path() -> Path:
    override = os.environ.get("JZO_ENV_FILE", "").strip()
    if override:
        return Path(override)
    return PROJECT_ROOT / ".env"


def validate_base_url(url: str) -> str:
    """只放行 http/https、有主机名、不带用户名口令的地址。"""
    text = (url or "").strip()
    if not text:
        raise ProviderConfigError("Base URL 不能为空")
    parsed = urlparse(text)
    if parsed.scheme not in ("http", "https"):
        raise ProviderConfigError("Base URL 只接受 http 或 https")
    if not parsed.hostname:
        raise ProviderConfigError("Base URL 缺少主机名")
    if parsed.username or parsed.password:
        raise ProviderConfigError("Base URL 禁止携带用户名口令")
    return text.rstrip("/")


def _update_env_file(pairs: dict[str, str]) -> None:
    """把键值写回 .env：已有键原位替换，新键追加；其余行原样保留。"""
    path = env_file_path()
    lines: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []

    pending = dict(pairs)
    output: list[str] = []
    for line in lines:
        text = line.strip()
        if text and not text.startswith("#") and "=" in text:
            key = text.split("=", 1)[0].strip()
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


def save_profile_config(
    profile: ProviderProfile,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> ProviderProfile:
    """保存用户在面板里亲手填的配置，返回热生效后的新配置档。

    只更新交进来的字段；写 .env 的同时直写 ``os.environ``，
    注册表每次调用都重读环境变量，因此无需重启即热生效。
    """
    if not profile.env_prefix:
        raise ProviderConfigError(f"Provider「{profile.name}」未声明环境变量前缀，不可面板配置")

    pairs: dict[str, str] = {}
    if base_url is not None:
        pairs[f"{profile.env_prefix}BASE_URL"] = validate_base_url(base_url)
    if api_key is not None:
        key = api_key.strip()
        if not key:
            raise ProviderConfigError("API Key 不能为空串；本地模型也请填一个占位（如 ollama）")
        pairs[f"{profile.env_prefix}API_KEY"] = key
    if model is not None:
        pairs[f"{profile.env_prefix}MODEL"] = model.strip()
    if not pairs:
        raise ProviderConfigError("api_key / base_url / model 至少要交一项")

    _update_env_file(pairs)
    os.environ.update(pairs)

    # 重新组档：直接读刚写入的环境变量，保证返回值与热生效状态一致
    prefix = profile.env_prefix
    return ProviderProfile(
        name=profile.name,
        label=profile.label,
        base_url=os.environ.get(f"{prefix}BASE_URL", "").strip(),
        api_key=os.environ.get(f"{prefix}API_KEY", "").strip(),
        model=os.environ.get(f"{prefix}MODEL", "").strip(),
        env_prefix=prefix,
    )


def test_connectivity(profile: ProviderProfile) -> dict[str, object]:
    """对配置档的 Base URL 发一次只读 ``GET /models``，回报可读结果。

    这是同步阻塞调用，API 层必须放线程池执行。任何异常都收敛成
    结构化结果，绝不把密钥原文带进 detail。
    """
    if not profile.is_configured:
        return {
            "ok": False,
            "status_code": None,
            "host": "",
            "detail": "该配置档尚未填齐 API Key 与 Base URL，先保存配置再测。",
        }

    host = urlparse(profile.base_url).netloc
    request = urllib.request.Request(
        f"{profile.base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {profile.api_key}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TEST_TIMEOUT_SECONDS) as response:
            body = response.read(64 * 1024).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        hint = {401: "密钥被拒（401）", 403: "无权限（403）", 404: "该地址没有 /models 接口（404）"}.get(
            exc.code, f"HTTP {exc.code}"
        )
        return {"ok": False, "status_code": exc.code, "host": host, "detail": f"接口可达但报错：{hint}"}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return {"ok": False, "status_code": None, "host": host, "detail": f"连不上：{reason}"}

    model_count: int | None = None
    try:
        document = json.loads(body)
        if isinstance(document, dict) and isinstance(document.get("data"), list):
            model_count = len(document["data"])
    except json.JSONDecodeError:
        pass
    detail = "连通正常" + (f"，/models 返回 {model_count} 个模型" if model_count is not None else "")
    return {"ok": True, "status_code": 200, "host": host, "detail": detail}

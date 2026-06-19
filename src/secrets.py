"""Secret handling for runtime config.

Secrets may live in environment variables or a local .env file. They are
overlaid only at runtime so saving normal settings does not write secrets back
into config/config.json.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any, Dict

from src.paths import ROOT

SECRET_PLACEHOLDER = "(da cau hinh)"
SECRET_PLACEHOLDER_VI = "(đã cấu hình)"

_ENV_LOADED = False


def _strip_quotes(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in ("'", '"'):
        return text[1:-1]
    return text


def load_dotenv_once(path: Path | None = None) -> None:
    """Load a simple KEY=value .env file without overriding existing env vars."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True
    env_path = path or (ROOT / ".env")
    if not env_path.is_file():
        return
    try:
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key in os.environ:
                continue
            os.environ[key] = _strip_quotes(value)
    except OSError:
        return


def env_secret(*names: str) -> str:
    load_dotenv_once()
    for name in names:
        val = str(os.environ.get(name) or "").strip()
        if val:
            return val
    return ""


def _read_env_values(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.is_file():
        return values
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if key:
                values[key] = value.strip()
    except OSError:
        return values
    return values


def set_local_secret(name: str, value: str) -> None:
    """Persist a secret to .env and update current process env."""
    key = str(name or "").strip()
    text = str(value or "").strip()
    if not key:
        return
    env_path = ROOT / ".env"
    values = _read_env_values(env_path)
    if text:
        values[key] = text
        os.environ[key] = text
    elif key in values:
        values.pop(key, None)
        os.environ.pop(key, None)
    ordered = ["GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    keys = [k for k in ordered if k in values] + sorted(k for k in values if k not in ordered)
    body = "\n".join(f"{k}={values[k]}" for k in keys)
    env_path.write_text(body + ("\n" if body else ""), encoding="utf-8")


def is_placeholder(value: Any) -> bool:
    text = str(value or "").strip()
    return text in {SECRET_PLACEHOLDER, SECRET_PLACEHOLDER_VI}


def is_configured_secret(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and not is_placeholder(text)


def apply_runtime_secrets(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of cfg with env/.env secrets overlaid for runtime use."""
    out = copy.deepcopy(cfg if isinstance(cfg, dict) else {})

    gemini = env_secret("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if gemini:
        out["gemini_api_key"] = gemini

    tg = out.get("telegram")
    if not isinstance(tg, dict):
        tg = {}
        out["telegram"] = tg

    token = env_secret("TELEGRAM_BOT_TOKEN", "BOT_TOKEN")
    if token:
        tg["bot_token"] = token

    chat_id = env_secret("TELEGRAM_CHAT_ID")
    if chat_id:
        tg["chat_id"] = chat_id

    return out


def redact_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Return a public config copy with secrets replaced by placeholders."""
    out = copy.deepcopy(cfg if isinstance(cfg, dict) else {})
    runtime = apply_runtime_secrets(out)

    if is_configured_secret(runtime.get("gemini_api_key")):
        out["gemini_api_key"] = SECRET_PLACEHOLDER_VI

    tg = out.get("telegram")
    if not isinstance(tg, dict):
        tg = {}
    runtime_tg = runtime.get("telegram") if isinstance(runtime.get("telegram"), dict) else {}
    tg = dict(tg)
    if is_configured_secret(runtime_tg.get("bot_token")):
        tg["bot_token"] = SECRET_PLACEHOLDER_VI
    out["telegram"] = tg
    return out

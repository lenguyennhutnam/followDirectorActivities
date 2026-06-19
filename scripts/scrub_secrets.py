"""Move secrets from JSON config files to .env and blank them in JSON.

Run from project root:
    python scripts/scrub_secrets.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
CONFIG_PATHS = [
    ROOT / "config" / "config.json",
    ROOT / "Phan_mem" / "config" / "config.json",
]


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _read_env(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not path.is_file():
        return out
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def _write_env(path: Path, env: Dict[str, str]) -> None:
    keys = ["GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"]
    lines = [f"{key}={env.get(key, '')}" for key in keys if env.get(key)]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _put_secret(env: Dict[str, str], key: str, value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if env.get(key):
        return False
    env[key] = text
    return True


def main() -> int:
    env = _read_env(ENV_PATH)
    moved = 0
    scrubbed = 0

    for path in CONFIG_PATHS:
        cfg = _read_json(path)
        if not cfg:
            continue

        changed = False
        if _put_secret(env, "GEMINI_API_KEY", cfg.get("gemini_api_key")):
            moved += 1
        if cfg.get("gemini_api_key"):
            cfg["gemini_api_key"] = ""
            changed = True

        tg = cfg.get("telegram")
        if isinstance(tg, dict):
            if _put_secret(env, "TELEGRAM_BOT_TOKEN", tg.get("bot_token")):
                moved += 1
            if _put_secret(env, "TELEGRAM_CHAT_ID", tg.get("chat_id")):
                moved += 1
            if tg.get("bot_token"):
                tg["bot_token"] = ""
                changed = True
            if tg.get("chat_id"):
                tg["chat_id"] = ""
                changed = True

        if changed:
            _write_json(path, cfg)
            scrubbed += 1

    _write_env(ENV_PATH, env)
    print(f"Moved {moved} secret value(s) to .env; scrubbed {scrubbed} config file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

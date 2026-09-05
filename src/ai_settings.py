"""Persisted LLM provider/model preferences.

Settings > Pengaturan Model LLM (src/pages/settings_page.py) previously kept
the chosen provider, model, and endpoint only in st.session_state, so it
reset every time the browser session ended - the user had to re-pick their
provider/model/custom-model-name on every fresh visit. This module persists
just those *preference* fields to a JSON file, the same "config JSON
separate from code" pattern already used by
pple/engineering/equipment_modules.py and src/asset_registry.py.

Deliberately excludes anything key-shaped (API keys, tokens): those keep
using the existing precedence in llm_assistant.resolve_provider_key()
(session -> st.secrets -> environment -> .env file) and must never be
written to a plain JSON file on disk (CLAUDE.md: "Never hardcode API keys
... read them from environment variables or secrets.toml").
"""

import json
import os
from threading import Lock
from typing import Any, Dict

_LOCK = Lock()

# Every key this module will read/write. Anything else passed to save() is
# dropped silently - this is the enforcement point for "never persist a key".
_ALLOWED_FIELDS = {
    "ai_enabled",
    "ai_provider",
    "gemini_model",
    "groq_model",
    "opencode_model",
    "opencode_base_url",
    "ollama_model",
    "ollama_host",
}


def _default_path() -> str:
    from src.data_loader import get_data_path

    return get_data_path("config", "ai_settings.json")


def load(path: str = None) -> Dict[str, Any]:
    """Persisted preferences, or {} if none saved yet / file is unreadable."""
    path = path or _default_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k in _ALLOWED_FIELDS}


def save(fields: Dict[str, Any], path: str = None) -> Dict[str, Any]:
    """Merge `fields` into the persisted preferences and write them out.
    Silently ignores any key not in _ALLOWED_FIELDS (defense in depth against
    an API key ever being passed in here by mistake)."""
    path = path or _default_path()
    safe_fields = {k: v for k, v in fields.items() if k in _ALLOWED_FIELDS}
    with _LOCK:
        current = load(path)
        current.update(safe_fields)
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        tmp_path = path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, sort_keys=True, ensure_ascii=False)
        os.replace(tmp_path, path)
    return current

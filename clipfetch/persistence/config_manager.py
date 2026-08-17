from __future__ import annotations

import json

from clipfetch.config.constants import (
    APP_SUPPORT_DIR,
    CONFIG_FILE,
    DEFAULT_CONCURRENCY,
    DEFAULT_DOWNLOAD_FOLDER,
    DEFAULT_FORMAT,
    DEFAULT_RESOLUTION,
    DEFAULT_LANGUAGE,
    LEGACY_LANGUAGE_ALIASES,
)
from clipfetch.infrastructure.path_utils import compact_user_path


class ConfigManager:
    def __init__(self):
        APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def defaults():
        return {
            "download_folder": compact_user_path(DEFAULT_DOWNLOAD_FOLDER),
            "format": DEFAULT_FORMAT,
            "resolution": DEFAULT_RESOLUTION,
            "concurrency": DEFAULT_CONCURRENCY,
            "speed_limit": "Sem limite",
            "audio_quality": "Melhor",
            "browser_cookies": "Nenhum",
            "subtitle_mode": "Não baixar",
            "subtitle_languages": "pt.*,en.*",
            "embed_subtitles": True,
            "embed_thumbnail": True,
            "embed_metadata": True,
            "embed_chapters": True,
            "prevent_duplicates": True,
            "organization": "Todos na pasta",
            "clipboard_detection": False,
            "notifications": True,
            "language": DEFAULT_LANGUAGE,
            "appearance": "Escuro",

            # Interface técnica. O botão existe por padrão, mas o painel de
            # detalhes sempre começa fechado. O modo desenvolvedor é opt-in.
            "show_technical_button": True,
            "developer_mode": False,
        }

    @staticmethod
    def _language(value):
        text = str(value or "").strip()
        return LEGACY_LANGUAGE_ALIASES.get(text, text) or DEFAULT_LANGUAGE

    @staticmethod
    def _appearance(value):
        # Public 1.0.0 supports only explicit Light/Dark modes.
        return value if value in {"Claro", "Escuro"} else "Escuro"

    def load(self):
        data = self.defaults()
        if CONFIG_FILE.exists():
            try:
                saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    data.update(saved)
            except (OSError, json.JSONDecodeError):
                pass
        try:
            data["concurrency"] = max(1, min(6, int(data["concurrency"])))
        except (TypeError, ValueError):
            data["concurrency"] = DEFAULT_CONCURRENCY
        data["language"] = self._language(data.get("language"))
        data["appearance"] = self._appearance(data.get("appearance"))
        data["download_folder"] = compact_user_path(data.get("download_folder"))
        return data

    def save(self, values):
        APP_SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
        data = self.defaults()
        data.update(values)
        data["language"] = self._language(data.get("language"))
        data["appearance"] = self._appearance(data.get("appearance"))
        data["download_folder"] = compact_user_path(data.get("download_folder"))
        CONFIG_FILE.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

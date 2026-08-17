from __future__ import annotations

from pathlib import Path

from .metadata import (
    APP_NAME,
    BUNDLE_ID,
)

APP_SUPPORT_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
APP_LOG_DIR = Path.home() / "Library" / "Logs" / APP_NAME
APP_CACHE_DIR = Path.home() / "Library" / "Caches" / APP_NAME
APP_PREFERENCES_FILE = Path.home() / "Library" / "Preferences" / f"{BUNDLE_ID}.plist"
CONFIG_FILE = APP_SUPPORT_DIR / "config.json"
RUNTIME_BIN_DIR = APP_SUPPORT_DIR / "bin"
DATABASE_FILE = APP_SUPPORT_DIR / "history.sqlite3"
DOWNLOAD_ARCHIVE_FILE = APP_SUPPORT_DIR / "download-archive.txt"
THUMBNAIL_CACHE_DIR = APP_SUPPORT_DIR / "thumbnails"
EXTRACTOR_CACHE_FILE = APP_SUPPORT_DIR / "extractors.txt"
RUNTIME_YTDLP_VERSION_FILE = RUNTIME_BIN_DIR / "yt-dlp.version"

# Use ~ in the persisted/displayed default. It is expanded only at execution time.
DEFAULT_DOWNLOAD_FOLDER = Path("~") / "Downloads" / "Videos"
DEFAULT_FORMAT = "MP4"
DEFAULT_RESOLUTION = "Melhor disponível"
DEFAULT_CONCURRENCY = 2

AVAILABLE_FORMATS = ["MP4", "MKV", "MP3", "M4A"]
RESOLUTIONS = ["Melhor disponível", "2160p (4K)", "1440p", "1080p", "720p", "480p", "360p"]
AUDIO_QUALITIES = ["Melhor", "320K", "256K", "192K", "128K"]
SPEED_LIMITS = ["Sem limite", "1M", "2M", "5M", "10M", "20M", "50M"]
BROWSERS = ["Nenhum", "Safari", "Chrome", "Firefox", "Brave", "Edge", "Chromium", "Opera", "Vivaldi"]
SUBTITLE_MODES = ["Não baixar", "Legendas normais", "Normais + automáticas"]
APPEARANCES = ["Claro", "Escuro"]
DEFAULT_LANGUAGE = "pt-BR"
LEGACY_LANGUAGE_ALIASES = {
    "Português": "pt-BR",
    "Português (Brasil)": "pt-BR",
    "Portuguese": "pt-BR",
    "English": "en",
}


ORGANIZATION_TEMPLATES = {
    "Todos na pasta": "%(title)s.%(ext)s",
    "Canal / Título": "%(uploader,channel,creator|Sem canal)s/%(title)s.%(ext)s",
    "Playlist / Número - Título": "%(playlist|Sem playlist)s/%(playlist_index|0)03d - %(title)s.%(ext)s",
    "Ano / Título": "%(upload_date>%Y|Sem data)s/%(title)s.%(ext)s",
}

PRESETS = {
    "Melhor qualidade": {"format": "MP4", "resolution": "Melhor disponível"},
    "1080p MP4": {"format": "MP4", "resolution": "1080p"},
    "720p MP4": {"format": "MP4", "resolution": "720p"},
    "4K MKV": {"format": "MKV", "resolution": "2160p (4K)"},
    "Áudio MP3": {"format": "MP3", "resolution": "Melhor disponível"},
    "Áudio M4A": {"format": "M4A", "resolution": "Melhor disponível"},
}

PROGRESS_PREFIX = "__YTDLP_PROGRESS__"
TITLE_PREFIX = "__YTDLP_TITLE__"
FILE_PREFIX = "__YTDLP_FILE__"

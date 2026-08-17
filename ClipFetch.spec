# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path

from clipfetch.config.metadata import APP_NAME, APP_VERSION, BUILD_NUMBER, BUNDLE_ID


def required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Variável de build ausente: {name}")
    path = Path(value)
    if not path.exists():
        raise RuntimeError(f"Arquivo de build não existe: {path}")
    return str(path)


YTDLP_BIN = required_env("YTDLP_BIN")
YTDLP_VERSION_FILE = required_env("YTDLP_VERSION_FILE")
EXTRACTORS_FILE = required_env("EXTRACTORS_FILE")
FFMPEG_BIN = required_env("FFMPEG_BIN")
FFPROBE_BIN = required_env("FFPROBE_BIN")
DENO_BIN = required_env("DENO_BIN")

datas = [
    (YTDLP_BIN, "vendor/bin"),
    (YTDLP_VERSION_FILE, "vendor/bin"),
    (EXTRACTORS_FILE, "vendor/bin"),
    ("THIRD_PARTY_NOTICES.txt", "vendor"),
    ("clipfetch/i18n/locales", "clipfetch/i18n/locales"),
]
binaries = [
    (FFMPEG_BIN, "vendor/bin"),
    (FFPROBE_BIN, "vendor/bin"),
    (DENO_BIN, "vendor/bin"),
]

a = Analysis(["main.py"], pathex=[str(Path.cwd())], binaries=binaries, datas=datas, hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False, optimize=0)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=APP_NAME, debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, upx_exclude=[], name=APP_NAME)
app = BUNDLE(
    coll,
    name=f"{APP_NAME}.app",
    icon="assets/ClipFetch.icns",
    bundle_identifier=BUNDLE_ID,
    version=APP_VERSION,
    info_plist={
        "CFBundleDisplayName": APP_NAME,
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": BUILD_NUMBER,
        "NSHighResolutionCapable": True,
        "NSPrincipalClass": "NSApplication",
        "LSMinimumSystemVersion": "12.0",
    },
)

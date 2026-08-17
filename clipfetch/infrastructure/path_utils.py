from __future__ import annotations

from pathlib import Path


def compact_user_path(value) -> str:
    """Show paths inside the current home as ~/... without embedding a username."""
    text = str(value or "").strip()
    if not text:
        return ""
    path = Path(text).expanduser()
    try:
        relative = path.relative_to(Path.home())
    except ValueError:
        return str(path)
    return str(Path("~") / relative)


def expand_user_path(value) -> str:
    text = str(value or "").strip()
    return str(Path(text).expanduser()) if text else ""

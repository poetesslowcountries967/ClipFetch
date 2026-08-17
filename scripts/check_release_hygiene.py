from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_PARTS = {
    ".git",
    ".venv-build",
    "build",
    "dist",
    "vendor-src",
    "__pycache__",
}

BANNED_FILE_NAMES = {
    ".DS_Store",
    "history.sqlite3",
    "download-archive.txt",
    "crash.log",
}

TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".json",
    ".command",
    ".spec",
    ".toml",
    ".yml",
    ".yaml",
}

PERSONAL_HOME = re.compile(r"/Users/([^/\s]+)/")
TEMP_PATTERNS = (
    "/private/var/folders/",
    "/var/folders/",
)

ALLOWED_DOCUMENTATION_USERS = {
    "<name>",
    "someone",
}


def main():
    errors = []

    for path in ROOT.rglob("*"):
        relative = path.relative_to(ROOT)

        if any(part in SKIP_PARTS for part in relative.parts):
            continue

        if path.is_file() and path.name in BANNED_FILE_NAMES:
            errors.append(
                f"arquivo local não permitido: {relative}"
            )

        if not (
            path.is_file()
            and path.suffix.casefold() in TEXT_SUFFIXES
        ):
            continue

        # Do not make the checker inspect its own regex examples.
        if path.name == Path(__file__).name:
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for match in PERSONAL_HOME.finditer(text):
            username = match.group(1)
            if username not in ALLOWED_DOCUMENTATION_USERS:
                errors.append(
                    f"rota pessoal em {relative}: {match.group(0)}"
                )

        for token in TEMP_PATTERNS:
            if token in text:
                errors.append(
                    f"rota temporária em {relative}: {token}"
                )

    if errors:
        message = "ERRO DE HIGIENE DA RELEASE:\n- "
        message += "\n- ".join(sorted(set(errors)))
        raise SystemExit(message)

    print("✓ Nenhuma rota pessoal literal encontrada.")
    print("✓ Nenhum cache/banco/log local encontrado no pacote de fonte.")
    print("✓ Projeto pronto para validação de release.")


if __name__ == "__main__":
    main()

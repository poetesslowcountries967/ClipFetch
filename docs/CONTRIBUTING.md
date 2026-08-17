# Contributing to ClipFetch

Before a pull request or release build, run:

```bash
python3 scripts/check_release_hygiene.py
python3 scripts/validate_locales.py
python3 scripts/audit_codebase.py
python3 -m compileall -q clipfetch main.py scripts
```

Place new code in the package that owns that responsibility. In particular,
avoid importing anything from `clipfetch.ui` inside services, persistence,
download, infrastructure, config, or core.

Do not commit `dist/`, `build/`, `.venv-build/`, `vendor-src/`, SQLite files,
download archives, caches, logs, or user-specific absolute paths.

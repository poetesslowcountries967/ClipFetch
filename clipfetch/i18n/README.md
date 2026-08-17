# Locales

ClipFetch discovers language packs from `clipfetch/i18n/locales/*.json`.

To add a language, copy `en.json`, change the `meta` block, translate the
values in `strings` and `replacements`, then run:

```bash
python3 scripts/validate_locales.py
```

The translation layer changes presentation only. Canonical download values are
stored separately in Qt item data so a locale cannot alter yt-dlp arguments.

# ClipFetch architecture

ClipFetch is organized by responsibility to favor **high cohesion** and
**low coupling**.

```text
main.py
└── clipfetch.ui.main_window
    ├── core
    ├── download
    ├── persistence
    ├── services
    └── infrastructure

clipfetch/
├── config/          metadata and non-UI constants
├── core/            data models and domain errors
├── download/        yt-dlp download orchestration
├── i18n/            translation API and locale resources
├── infrastructure/  bundled executables and path helpers
├── persistence/     config.json and SQLite history
├── services/        metadata, thumbnails, extractors and updates
└── ui/              Qt window, dialogs, components and styles
```

## Dependency rules

- `core` does not import Qt, persistence, services, download, or UI.
- `config` does not import UI.
- `persistence` owns disk/database state and never imports UI.
- `services` never import UI; they return data/errors through callbacks.
- `download` receives collaborators through its constructor/callbacks.
- `ui` coordinates lower layers but does not own persistence or yt-dlp logic.
- `main.py` only bootstraps the process and top-level crash handling.

## Runtime data

User-specific data lives under macOS Application Support at runtime. It is not
part of the source tree. `scripts/check_release_hygiene.py` rejects common
runtime files and personal absolute paths before a build.

## Localization

Locale files are in `clipfetch/i18n/locales`. Add a JSON file and run:

```bash
python3 scripts/validate_locales.py
```

Translated labels must never become yt-dlp configuration values.

## Fork update repository

Fork maintainers change the updater route only in:

`clipfetch/config/metadata.py`

Look for the clearly marked `UPDATE_REPOSITORY` block.


## Responsive UI and notifications

`clipfetch.ui.main_window` coordinates the application but delegates Dock/tray
notification state to `clipfetch.ui.notifications.NotificationController`.

Long pages use internal scroll areas so widget size hints do not force the main
window to exceed the available macOS screen geometry.

The Dock badge represents unread completion notifications only; queue size and
download progress do not own badge state.

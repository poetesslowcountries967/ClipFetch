# Code audit for ClipFetch 1.0.0

This audit was performed before the first public release.

## Removed obsolete code

The refactor removed code that no longer had a caller after the compact queue
redesign:

- `_set_item_format_by_id`
- `_set_item_resolution_by_id`
- `_set_item_format`
- `_set_item_resolution`
- unused i18n functions `current_language` and `tr_exact`
- unused `LANGUAGES` constant
- unused Qt/import symbols left by previous UI revisions

`write_crash_log` was renamed to `format_exception_details` because the current
application intentionally keeps crash details in memory and does not write a log
file.

## Performance/lifecycle changes

- Metadata analysis keeps one bounded `ThreadPoolExecutor` and now shuts it down
  explicitly when the main window closes.
- Thumbnail fetching now uses a bounded two-worker pool instead of creating a new
  thread for every request.
- Queue progress updates continue to update only the progress/status cells; they
  do not rebuild the full queue for every yt-dlp progress line.
- Startup continues to avoid `yt-dlp --version` subprocesses on the normal fast
  path.

## Structure

UI styles were removed from application constants and placed in
`clipfetch/ui/styles.py`.

Reusable UI helpers were removed from the main-window module and placed in:

- `clipfetch/ui/components.py`
- `clipfetch/ui/signals.py`

The remaining source is grouped by responsibility under `clipfetch/`.

## Files intentionally retained

- `INSTALLATION.txt`: copied into the DMG for end users.
- `THIRD_PARTY_NOTICES.txt`: third-party redistribution/licensing notices.
- `ClipFetch.spec`: PyInstaller packaging definition.
- `build_distribution.command`: reproducible macOS build entry point.
- `requirements-build.txt`: build-time Python dependencies.
- `scripts/check_release_hygiene.py`: blocks personal/runtime artifacts.
- `scripts/validate_locales.py`: validates external locale packs.
- `scripts/audit_codebase.py`: checks obvious dead imports/functions and layer
  dependency violations.

Runtime files such as SQLite history, caches, `download-archive.txt`, logs,
`dist/`, `build/` and `vendor-src/` are not source files and are excluded.

## Static guarantees

`scripts/audit_codebase.py` checks:

1. obvious unused imports;
2. clearly unreferenced functions/methods, with an allow-list for Qt virtual
   callbacks;
3. dependency boundaries between `core`, `config`, `infrastructure`,
   `persistence`, `services`, `download`, `i18n` and `ui`.

The macOS build script also performs a real PySide6 offscreen smoke test before
PyInstaller runs.


## Final pre-release UI lifecycle checks

- Preferences and Settings remain accessible while downloads are active.
- Active download batches receive a snapshot of preferences, preventing later UI
  edits from mutating an already-running batch.
- Clearing the queue during active downloads first cancels the batch and removes
  rows only after workers have completed, avoiding callbacks into deleted rows.
- Notification/badge behavior is isolated in `NotificationController`.
- Long UI pages use scroll areas and the window respects macOS available screen
  geometry.

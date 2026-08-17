# ClipFetch for macOS

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)
![UI](https://img.shields.io/badge/UI-PySide6-green)
![Engine](https://img.shields.io/badge/engine-yt--dlp-red)

**ClipFetch** is a graphical macOS application for downloading video and audio
from sources supported by **yt-dlp**, without requiring the end user to work in
Terminal or install Python, Homebrew, yt-dlp, FFmpeg, FFprobe, or Deno.

Public version: **1.0.0**

## Application icon

The repository currently includes a bundled application icon:

```text
assets/ClipFetch.icns
assets/ClipFetch.png
```

The `.spec` file already points to `assets/ClipFetch.icns`, so local builds and
future GitHub Release builds use the same icon in the macOS app bundle.

## Download and install

Ready-to-use builds belong in **GitHub Releases**.

1. Download the `.dmg` for your Mac architecture.
2. Open the DMG.
3. Drag `ClipFetch.app` to **Applications**.
4. Open ClipFetch normally.

The current public build targets **Apple Silicon (arm64)**.

> The current build uses an ad-hoc signature. macOS may still show the usual
> unidentified-developer warning until a future Developer ID + notarized build
> is published.

## Main features

- graphical interface powered by PySide6;
- yt-dlp-based media support and dynamic supported-site discovery;
- multiple links with background metadata analysis;
- playlists;
- video/audio format and quality selection;
- compact queue with **Item**, **Progress**, and **Status**;
- thumbnails and media metadata preview;
- multiple simultaneous downloads;
- pause/cancel controls;
- scheduled downloads with date and time;
- FFmpeg/FFprobe and Deno bundled into the macOS app;
- in-app yt-dlp updater;
- application update checks through GitHub Releases;
- download history with source URLs and final file paths;
- duplicate detection based on extractor + media ID;
- automatic redownload when a previously downloaded file no longer exists;
- export of source URLs from history;
- Portuguese (Brazil) and English interface;
- extensible JSON language packs;
- explicit Light and Dark themes;
- full application-data reset without deleting downloaded media;
- memory-only technical session details;
- developer mode for deeper diagnostics;
- macOS Dock notification badge for unread completion notifications.

## Interface

ClipFetch uses four main tabs:

- **Downloads** — add links, inspect media, manage the queue, and start downloads;
- **History** — inspect processed downloads, source URLs, formats, resolution,
  status, and file paths;
- **Preferences** — format, quality, concurrency, subtitles, appearance,
  language, notifications, clipboard behavior, and advanced authentication;
- **Settings** — yt-dlp update, ClipFetch update check, diagnostics, internal
  tools, application reset, project information, and developer mode.

Downloads, Preferences, and Settings use internal scrolling so the application
remains usable on smaller MacBook displays and with the Dock visible.

## Themes

ClipFetch provides two explicit themes:

- **Light**
- **Dark**

The application does not automatically follow the macOS theme.

The operational areas on Downloads and the History table use a graphite visual
language in both themes for consistent contrast.

## Technical details and developer mode

The **Show technical details** button is available by default and its panel
starts collapsed.

Users can hide that button from Settings. Even when hidden, technical details
continue to be collected **only in memory for the current application session**.
Closing ClipFetch discards them.

Developer mode is disabled by default. It exposes additional runtime details
such as extractor information, media identifiers, speed/ETA diagnostics, and
maintainer-oriented information.

Developer mode does **not** change download quality or yt-dlp behavior.

## Notifications

The macOS Dock badge represents **unread completion notifications**, not the
number of queued downloads.

- finishing a batch while ClipFetch is active leaves no unread badge;
- finishing in the background creates an unread notification;
- activating ClipFetch clears the badge;
- disabling notifications clears the badge;
- closing the application clears the badge.

## Languages

Included locales:

- `pt-BR` — Português (Brasil)
- `en` — English

Locale files are stored under:

```text
clipfetch/i18n/locales/
```

New locales can be added without changing download logic. Internal/canonical
values are kept separate from translated labels.

Validate locale files with:

```bash
python3 scripts/validate_locales.py
```

## Persistent application data

ClipFetch resolves per-user macOS paths at runtime. The source repository does
not contain a developer-specific `/Users/...` path.

The default download folder is represented as:

```text
~/Downloads/Videos
```

Application state may include preferences, SQLite history, the yt-dlp download
archive, thumbnail/source caches, and a runtime-updated yt-dlp binary.

**Reset application** clears ClipFetch application data but does **not** delete
downloaded media files.

Technical session details are not persisted.

## Source architecture

The source follows a high-cohesion / low-coupling package layout:

```text
clipfetch/
├── config/          application metadata and constants
├── core/            domain models and errors
├── download/        download orchestration
├── i18n/            translation API and locales
├── infrastructure/  bundled executables and path helpers
├── persistence/     preferences and SQLite history
├── services/        metadata, thumbnails, extractors and updates
└── ui/              Qt windows, dialogs, widgets, notifications and styles
```

See:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)
- [`docs/CODE_AUDIT.md`](docs/CODE_AUDIT.md)

## Building from source

Requirements on the **build Mac only**:

- Apple Silicon Mac;
- Python 3.9+;
- Homebrew;
- FFmpeg installed through Homebrew;
- Deno installed through Homebrew;
- network access to fetch the official yt-dlp macOS nightly executable.

Run:

```bash
./build_distribution.command
```

The build script performs repository hygiene checks, locale validation,
architecture/static checks, Python compilation, a real PySide6 smoke test,
PyInstaller packaging, ad-hoc signing, and DMG creation.

Expected output:

```text
dist/ClipFetch.app
dist/ClipFetch_macOS_arm64.dmg
```

## Repository validation

Before a contribution or release:

```bash
python3 scripts/check_release_hygiene.py
python3 scripts/validate_locales.py
python3 scripts/audit_codebase.py
python3 -m compileall -q clipfetch main.py scripts
```

Generated build/runtime data must not be committed.

## Application updates and forks

Official builds check GitHub Releases from:

```text
JulianoMachadoS/ClipFetch
```

The updater repository is centralized in:

```text
clipfetch/config/metadata.py
```

Fork maintainers should change `UPDATE_REPOSITORY` there.

## GitHub release model

Normal Git history contains source code, documentation, locale files, and build
scripts.

Ready-to-use `.dmg` files belong in **GitHub Releases**, not in the repository
source tree.

The first public release is:

```text
Version: 1.0.0
Tag:     v1.0.0
```

Pre-release internal development versions are intentionally not part of the
public release history.

## Third-party software

ClipFetch integrates or bundles software including yt-dlp, FFmpeg/FFprobe,
Deno, PySide6/Qt, and PyInstaller.

Review [`THIRD_PARTY_NOTICES.txt`](THIRD_PARTY_NOTICES.txt) before public
redistribution and comply with the licenses applicable to the exact binaries
you distribute.

## Responsible use

ClipFetch is not affiliated with YouTube, Google, or the websites supported by
yt-dlp.

Users are responsible for ensuring they have permission to download and use
content and for complying with the terms of the source service.

---

Made by **Juliano Machado da Silva**  
GitHub: **JulianoMachadoS**

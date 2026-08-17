from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from clipfetch.config.constants import (
    APP_SUPPORT_DIR,
    EXTRACTOR_CACHE_FILE,
    RUNTIME_BIN_DIR,
    RUNTIME_YTDLP_VERSION_FILE,
)


@dataclass(frozen=True)
class ToolInfo:
    name: str
    path: Path
    exists: bool
    executable: bool
    version: Optional[str]


class BundledTools:
    """
    Locate bundled executables and maintain the writable runtime yt-dlp copy.

    Normal startup intentionally avoids running `yt-dlp --version`; version
    subprocesses are reserved for diagnostics, updates, or repair paths.
    """

    def __init__(self):
        APP_SUPPORT_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )
        RUNTIME_BIN_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )
        self._runtime_ready = False

    @staticmethod
    def bundle_root() -> Path:
        if (
            getattr(
                sys,
                "frozen",
                False,
            )
            and hasattr(
                sys,
                "_MEIPASS",
            )
        ):
            return Path(
                sys._MEIPASS
            )

        # clipfetch/infrastructure/bundled_tools.py -> project root
        return (
            Path(__file__)
            .resolve()
            .parents[2]
        )

    @property
    def bundle_bin_dir(self):
        return (
            self.bundle_root()
            / "vendor"
            / "bin"
        )

    @property
    def bundled_ytdlp(self):
        return (
            self.bundle_bin_dir
            / "yt-dlp"
        )

    @property
    def bundled_ytdlp_version_file(self):
        return (
            self.bundle_bin_dir
            / "yt-dlp.version"
        )

    @property
    def bundled_extractors_file(self):
        return (
            self.bundle_bin_dir
            / "extractors.txt"
        )

    @property
    def ffmpeg(self):
        return (
            self.bundle_bin_dir
            / "ffmpeg"
        )

    @property
    def ffprobe(self):
        return (
            self.bundle_bin_dir
            / "ffprobe"
        )

    @property
    def deno(self):
        return (
            self.bundle_bin_dir
            / "deno"
        )

    @property
    def runtime_ytdlp(self):
        return (
            RUNTIME_BIN_DIR
            / "yt-dlp"
        )

    @staticmethod
    def _version_tuple(
        version,
    ):
        return tuple(
            int(part)
            for part
            in re.findall(
                r"\d+",
                version
                or "",
            )
        )

    @staticmethod
    def _read_text(
        path,
    ):
        try:
            return (
                path.read_text(
                    encoding="utf-8"
                )
                .strip()
            )
        except OSError:
            return ""

    @staticmethod
    def _write_text(
        path,
        value,
    ):
        try:
            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            path.write_text(
                (
                    value
                    or ""
                ).strip()
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def _copy_bundled_ytdlp(
        self,
    ):
        if not self.bundled_ytdlp.exists():
            raise FileNotFoundError(
                (
                    "O yt-dlp integrado não foi "
                    "encontrado no aplicativo."
                )
            )

        temporary = (
            self.runtime_ytdlp
            .with_suffix(
                ".new"
            )
        )

        shutil.copy2(
            self.bundled_ytdlp,
            temporary,
        )

        temporary.chmod(
            0o755
        )

        temporary.replace(
            self.runtime_ytdlp
        )

        bundled_version = (
            self._read_text(
                self.bundled_ytdlp_version_file
            )
        )

        if bundled_version:
            self._write_text(
                RUNTIME_YTDLP_VERSION_FILE,
                bundled_version,
            )

    def ensure_runtime_ytdlp(
        self,
    ):
        """Return the writable runtime yt-dlp without a version subprocess."""

        if (
            self._runtime_ready
            and self.runtime_ytdlp.exists()
        ):
            return (
                self.runtime_ytdlp
            )

        if not self.runtime_ytdlp.exists():
            self._copy_bundled_ytdlp()

        else:
            try:
                self.runtime_ytdlp.chmod(
                    0o755
                )
            except OSError:
                pass

            bundled = (
                self._read_text(
                    self.bundled_ytdlp_version_file
                )
            )

            runtime = (
                self._read_text(
                    RUNTIME_YTDLP_VERSION_FILE
                )
            )

            needs_seed = (
                bundled
                and not runtime
            )

            bundled_is_newer = (
                bundled
                and runtime
                and (
                    self._version_tuple(
                        bundled
                    )
                    > self._version_tuple(
                        runtime
                    )
                )
            )

            if (
                needs_seed
                or bundled_is_newer
            ):
                self._copy_bundled_ytdlp()

        self._runtime_ready = True

        return self.runtime_ytdlp

    def runtime_environment(self):
        env = os.environ.copy()

        env["PATH"] = (
            os.pathsep.join(
                [
                    str(
                        self.bundle_bin_dir
                    ),
                    str(
                        RUNTIME_BIN_DIR
                    ),
                    env.get(
                        "PATH",
                        "",
                    ),
                ]
            )
        )

        env.setdefault(
            "DENO_DIR",
            str(
                APP_SUPPORT_DIR
                / "deno"
            ),
        )

        return env

    def run_version(
        self,
        path,
        timeout=30,
    ):
        if not path.exists():
            return None

        try:
            result = subprocess.run(
                [
                    str(path),
                    "--version",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=timeout,
                env=self.runtime_environment(),
            )
        except (
            OSError,
            subprocess.SubprocessError,
        ):
            return None

        if result.returncode != 0:
            return None

        lines = (
            result.stdout
            .strip()
            .splitlines()
        )

        return (
            lines[0]
            if lines
            else None
        )

    def repair_runtime_ytdlp(
        self,
    ):
        """Repair the runtime executable only after a real execution failure."""

        current = self.run_version(
            self.runtime_ytdlp,
            45,
        )

        if current:
            self._write_text(
                RUNTIME_YTDLP_VERSION_FILE,
                current,
            )

            return (
                False,
                (
                    "O executável respondeu à "
                    "verificação de versão: "
                    f"{current}"
                ),
            )

        try:
            self._copy_bundled_ytdlp()
        except OSError as error:
            return (
                False,
                (
                    "Falha ao restaurar o "
                    "yt-dlp integrado: "
                    f"{error}"
                ),
            )

        restored = self.run_version(
            self.runtime_ytdlp,
            45,
        )

        if restored:
            self._write_text(
                RUNTIME_YTDLP_VERSION_FILE,
                restored,
            )

            return (
                True,
                (
                    "O yt-dlp foi restaurado "
                    "para a versão "
                    f"{restored}."
                ),
            )

        return (
            True,
            (
                "O yt-dlp integrado foi restaurado, "
                "mas não respondeu à verificação de versão."
            ),
        )

    def record_runtime_version(
        self,
    ):
        version = self.run_version(
            self.runtime_ytdlp,
            60,
        )

        if version:
            self._write_text(
                RUNTIME_YTDLP_VERSION_FILE,
                version,
            )

        return version

    def inspect(
        self,
        name,
        path,
        include_version=False,
    ):
        exists = (
            path.exists()
        )
        executable = (
            exists
            and os.access(
                path,
                os.X_OK,
            )
        )

        version = (
            self.run_version(
                path,
                45,
            )
            if (
                include_version
                and executable
            )
            else None
        )

        return ToolInfo(
            name,
            path,
            exists,
            executable,
            version,
        )

    def status(
        self,
        include_versions=False,
    ):
        try:
            ytdlp = (
                self.ensure_runtime_ytdlp()
            )
        except OSError:
            ytdlp = (
                self.runtime_ytdlp
            )

        return {
            "yt-dlp": self.inspect(
                "yt-dlp",
                ytdlp,
                include_versions,
            ),
            "ffmpeg": self.inspect(
                "ffmpeg",
                self.ffmpeg,
                include_versions,
            ),
            "ffprobe": self.inspect(
                "ffprobe",
                self.ffprobe,
                include_versions,
            ),
            "deno": self.inspect(
                "deno",
                self.deno,
                include_versions,
            ),
        }

    def is_ready(self):
        """Fast startup check: no copies and no version subprocesses."""

        runtime_ok = (
            self.runtime_ytdlp.exists()
            and os.access(
                self.runtime_ytdlp,
                os.X_OK,
            )
        )

        bundled_ok = (
            self.bundled_ytdlp.exists()
        )

        ytdlp_ok = (
            runtime_ok
            or bundled_ok
        )

        other_ok = all(
            path.exists()
            and os.access(
                path,
                os.X_OK,
            )
            for path
            in (
                self.ffmpeg,
                self.ffprobe,
                self.deno,
            )
        )

        return (
            ytdlp_ok
            and other_ok
        )

    def diagnostic_text(
        self,
        include_versions=True,
    ):
        lines = [
            (
                "Arquitetura do Mac: "
                f"{platform.machine()}"
            ),
            "",
        ]

        for info in (
            self.status(
                include_versions
            ).values()
        ):
            marker = (
                "✓"
                if (
                    info.exists
                    and info.executable
                )
                else "✗"
            )

            version = (
                f" — {info.version}"
                if info.version
                else ""
            )

            lines.extend(
                [
                    (
                        f"{marker} "
                        f"{info.name}"
                        f"{version}"
                    ),
                    f"    {info.path}",
                ]
            )

        return "\n".join(
            lines
        )

    def seed_extractor_cache(
        self,
    ):
        if (
            EXTRACTOR_CACHE_FILE
            .exists()
        ):
            return True

        if not (
            self.bundled_extractors_file
            .exists()
        ):
            return False

        try:
            shutil.copy2(
                self.bundled_extractors_file,
                EXTRACTOR_CACHE_FILE,
            )
            return True

        except OSError:
            return False

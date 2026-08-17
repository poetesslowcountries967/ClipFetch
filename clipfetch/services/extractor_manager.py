from __future__ import annotations

import subprocess
import threading
from dataclasses import dataclass
from typing import (
    Callable,
    Optional,
)

from clipfetch.config.constants import EXTRACTOR_CACHE_FILE
from clipfetch.core.error_translator import ErrorTranslator
from clipfetch.core.errors import AppError


@dataclass(frozen=True)
class ExtractorLists:
    names: list[str]
    from_cache: bool = False


FinishedCallback = Callable[
    [
        bool,
        Optional[ExtractorLists],
        Optional[AppError],
    ],
    None,
]


class ExtractorManager:
    """Load yt-dlp extractor names with a fast local-cache path."""

    TIMEOUT = 180

    def __init__(
        self,
        tools,
    ):
        self.tools = tools

    @staticmethod
    def _read_names(path):
        try:
            return [
                line.strip()
                for line
                in path.read_text(
                    encoding="utf-8"
                ).splitlines()
                if line.strip()
            ]
        except OSError:
            return []

    @staticmethod
    def _write_names(
        names,
    ):
        try:
            EXTRACTOR_CACHE_FILE.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            EXTRACTOR_CACHE_FILE.write_text(
                "\n".join(names)
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def cached_names(self):
        names = self._read_names(
            EXTRACTOR_CACHE_FILE
        )

        if names:
            return names

        self.tools.seed_extractor_cache()

        return self._read_names(
            EXTRACTOR_CACHE_FILE
        )

    def load_async(
        self,
        callback,
        force_refresh=False,
    ):
        if not force_refresh:
            cached = self.cached_names()

            if cached:
                callback(
                    True,
                    ExtractorLists(
                        cached,
                        True,
                    ),
                    None,
                )
                return

        threading.Thread(
            target=self._refresh,
            args=(callback,),
            daemon=True,
        ).start()

    def _extractor_command(self):
        return [
            str(
                self.tools.ensure_runtime_ytdlp()
            ),
            "--ignore-config",
            "--list-extractors",
        ]

    def _run_command(
        self,
        command,
    ):
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self.TIMEOUT,
            env=self.tools.runtime_environment(),
        )

    def _refresh(
        self,
        callback,
    ):
        command = self._extractor_command()

        try:
            result = self._run_command(
                command
            )

        except subprocess.TimeoutExpired as error:
            technical = (
                f"Timeout após {self.TIMEOUT}s.\n\n"
                f"Comando:\n{command}\n\n"
                f"Exceção:\n{error}"
            )

            restored, repair = (
                self.tools.repair_runtime_ytdlp()
            )

            technical += (
                "\n\nDiagnóstico do executável:\n"
                + repair
            )

            if not restored:
                callback(
                    False,
                    None,
                    ErrorTranslator.timeout(
                        operation="sources",
                        seconds=self.TIMEOUT,
                        technical_details=technical,
                    ),
                )
                return

            try:
                result = self._run_command(
                    self._extractor_command()
                )

            except subprocess.TimeoutExpired as retry:
                callback(
                    False,
                    None,
                    ErrorTranslator.timeout(
                        operation="sources",
                        seconds=self.TIMEOUT,
                        technical_details=(
                            technical
                            + f"\n\nNova tentativa:\n{retry}"
                        ),
                    ),
                )
                return

        except OSError as error:
            callback(
                False,
                None,
                AppError(
                    "Não foi possível iniciar o yt-dlp",
                    (
                        "O aplicativo não conseguiu executar o componente "
                        "responsável pela lista de fontes."
                    ),
                    str(error),
                    "spawn",
                ),
            )
            return

        if result.returncode != 0:
            raw = (
                result.stderr.strip()
                or result.stdout.strip()
                or (
                    "yt-dlp terminou com código "
                    f"{result.returncode}."
                )
            )

            callback(
                False,
                None,
                ErrorTranslator.to_error(
                    raw,
                    default_title=(
                        "Não foi possível carregar as fontes"
                    ),
                    default_message=(
                        "O yt-dlp não conseguiu fornecer a lista de "
                        "integrações suportadas."
                    ),
                ),
            )
            return

        names = list(
            dict.fromkeys(
                line.strip()
                for line
                in result.stdout.splitlines()
                if line.strip()
            )
        )

        self._write_names(
            names
        )

        callback(
            True,
            ExtractorLists(
                names,
                False,
            ),
            None,
        )

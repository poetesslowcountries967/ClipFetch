from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor

from clipfetch.core.error_translator import ErrorTranslator
from clipfetch.core.errors import AppError
from clipfetch.core.models import (
    AnalysisResult,
    FormatInfo,
    MediaItem,
)
from clipfetch.infrastructure.bundled_tools import BundledTools


class MetadataService:
    """Analyze media metadata outside the UI thread."""

    ANALYSIS_TIMEOUT = 180
    ANALYSIS_WORKERS = 3

    def __init__(
        self,
        tools: BundledTools,
    ):
        self.tools = tools

        self._executor = ThreadPoolExecutor(
            max_workers=self.ANALYSIS_WORKERS,
            thread_name_prefix="metadata",
        )

    @staticmethod
    def _browser(
        value,
    ):
        browser = (
            value
            or ""
        ).strip().casefold()

        return (
            ""
            if browser in (
                "",
                "nenhum",
            )
            else browser
        )

    def _base_command(
        self,
        browser_cookies,
    ):
        command = [
            str(
                self.tools
                .ensure_runtime_ytdlp()
            ),
            "--ignore-config",
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            "--js-runtimes",
            f"deno:{self.tools.deno}",
        ]

        browser = self._browser(
            browser_cookies
        )

        if browser:
            command.extend(
                [
                    "--cookies-from-browser",
                    browser,
                ]
            )

        return command

    def _execute_json_command(
        self,
        command,
    ):
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=self.ANALYSIS_TIMEOUT,
            env=self.tools.runtime_environment(),
        )

    def _run_json(
        self,
        command,
    ):
        try:
            result = (
                self._execute_json_command(
                    command
                )
            )

        except subprocess.TimeoutExpired as error:
            technical = (
                f"Timeout após {self.ANALYSIS_TIMEOUT}s.\n\n"
                f"Comando:\n{command}\n\n"
                f"Exceção:\n{error}"
            )

            restored, details = (
                self.tools
                .repair_runtime_ytdlp()
            )

            technical += (
                "\n\nDiagnóstico do executável:\n"
                + details
            )

            if not restored:
                raise RuntimeError(
                    ErrorTranslator.timeout(
                        operation="analysis",
                        seconds=(
                            self.ANALYSIS_TIMEOUT
                        ),
                        technical_details=technical,
                    )
                )

            retry = list(command)
            retry[0] = str(
                self.tools
                .ensure_runtime_ytdlp()
            )

            try:
                result = (
                    self._execute_json_command(
                        retry
                    )
                )

            except subprocess.TimeoutExpired as retry_error:
                technical += (
                    "\n\nNova tentativa:\n"
                    f"{retry_error}"
                )

                raise RuntimeError(
                    ErrorTranslator.timeout(
                        operation="analysis",
                        seconds=(
                            self.ANALYSIS_TIMEOUT
                        ),
                        technical_details=technical,
                    )
                )

        if result.returncode != 0:
            raw = (
                result.stderr.strip()
                or result.stdout.strip()
                or (
                    "yt-dlp terminou com código "
                    f"{result.returncode}"
                )
            )

            raise RuntimeError(
                ErrorTranslator.to_error(
                    raw,
                    default_title=(
                        "Não foi possível analisar o link"
                    ),
                    default_message=(
                        "O yt-dlp não conseguiu obter os "
                        "metadados deste endereço."
                    ),
                )
            )

        try:
            return json.loads(
                result.stdout
            )

        except json.JSONDecodeError as error:
            raise RuntimeError(
                AppError(
                    "Resposta inválida do yt-dlp",
                    (
                        "O yt-dlp respondeu, mas os metadados "
                        "não puderam ser interpretados pelo aplicativo."
                    ),
                    (
                        f"{error}\n\n"
                        "Saída recebida:\n"
                        f"{result.stdout[:5000]}"
                    ),
                    "json",
                )
            )

    @staticmethod
    def _select_preview_thumbnail(
        data,
    ):
        thumbnails = [
            entry
            for entry
            in (
                data.get(
                    "thumbnails"
                )
                or []
            )
            if (
                isinstance(
                    entry,
                    dict,
                )
                and str(
                    entry.get(
                        "url"
                    )
                    or ""
                ).startswith(
                    (
                        "http://",
                        "https://",
                    )
                )
            )
        ]

        def area(entry):
            try:
                return (
                    int(
                        entry.get(
                            "width"
                        )
                        or 10000
                    )
                    * int(
                        entry.get(
                            "height"
                        )
                        or 10000
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                return 100000000

        preferred = [
            entry
            for entry
            in thumbnails
            if (
                isinstance(
                    entry.get(
                        "width"
                    ),
                    (
                        int,
                        float,
                    ),
                )
                and 120
                <= entry["width"]
                <= 360
            )
        ]

        if preferred:
            return str(
                min(
                    preferred,
                    key=area,
                ).get(
                    "url"
                )
                or ""
            )

        if thumbnails:
            return str(
                min(
                    thumbnails,
                    key=area,
                ).get(
                    "url"
                )
                or ""
            )

        return str(
            data.get(
                "thumbnail"
            )
            or ""
        )

    @staticmethod
    def _make_item(
        data,
        source_url,
        playlist_name="",
        playlist_index=None,
    ):
        raw_formats = [
            FormatInfo.from_json(
                entry
            )
            for entry
            in (
                data.get(
                    "formats"
                )
                or []
            )
            if isinstance(
                entry,
                dict,
            )
        ]

        formats = [
            fmt
            for fmt
            in raw_formats
            if fmt.is_usable_media
        ]

        extractor_key = str(
            data.get(
                "extractor_key"
            )
            or data.get(
                "ie_key"
            )
            or data.get(
                "extractor"
            )
            or ""
        )

        extractor = str(
            data.get(
                "extractor_key"
            )
            or data.get(
                "extractor"
            )
            or extractor_key
            or ""
        )

        media_id = str(
            data.get("id")
            or ""
        )

        return MediaItem(
            source_url=source_url,
            webpage_url=str(
                data.get(
                    "webpage_url"
                )
                or data.get(
                    "original_url"
                )
                or data.get(
                    "url"
                )
                or source_url
            ),
            title=str(
                data.get(
                    "title"
                )
                or "Sem título"
            ),
            uploader=str(
                data.get(
                    "uploader"
                )
                or data.get(
                    "channel"
                )
                or data.get(
                    "creator"
                )
                or ""
            ),
            extractor=extractor,
            extractor_key=(
                extractor_key
            ),
            media_id=media_id,
            duration=data.get(
                "duration"
            ),
            thumbnail_url=(
                MetadataService
                ._select_preview_thumbnail(
                    data
                )
            ),
            playlist=playlist_name,
            playlist_index=(
                playlist_index
            ),
            formats=formats,
            subtitles=sorted(
                (
                    data.get(
                        "subtitles"
                    )
                    or {}
                ).keys()
            ),
            automatic_subtitles=sorted(
                (
                    data.get(
                        "automatic_captions"
                    )
                    or {}
                ).keys()
            ),
        )

    @staticmethod
    def _normalize_error(
        error,
    ):
        if (
            isinstance(
                error,
                RuntimeError,
            )
            and error.args
            and isinstance(
                error.args[0],
                AppError,
            )
        ):
            return error.args[0]

        if isinstance(
            error,
            AppError,
        ):
            return error

        return ErrorTranslator.to_error(
            str(error),
            default_title=(
                "Não foi possível analisar o link"
            ),
            default_message=(
                "Ocorreu um erro durante a análise do endereço."
            ),
        )

    @staticmethod
    def _ensure_real_media(
        item,
        raw_data,
    ):
        if (
            (
                raw_data.get(
                    "formats"
                )
                or []
            )
            and not item.formats
        ):
            raise RuntimeError(
                AppError(
                    "Nenhum vídeo/áudio utilizável encontrado",
                    (
                        "O yt-dlp encontrou apenas imagens de "
                        "pré-visualização do conteúdo. Nenhum stream "
                        "real foi adicionado à fila."
                    ),
                    (
                        "O JSON retornou formatos, porém nenhum possuía "
                        "stream real de áudio/vídeo. Os formatos restantes "
                        "eram imagens/storyboards (por exemplo "
                        "mhtml/vcodec=images)."
                    ),
                    "storyboard",
                )
            )

    def shutdown(self):
        """Release queued analysis tasks when the application closes."""
        self._executor.shutdown(
            wait=False,
            cancel_futures=True,
        )

    def analyze_async(
        self,
        url,
        browser_cookies,
        callback,
        started_callback=None,
    ):
        self._executor.submit(
            self._analyze,
            url,
            browser_cookies,
            callback,
            started_callback,
        )

    def _analyze(
        self,
        url,
        browser_cookies,
        callback,
        started_callback=None,
    ):
        try:
            if (
                started_callback
                is not None
            ):
                started_callback(
                    url
                )

            data = self._run_json(
                self._base_command(
                    browser_cookies
                )
                + [url]
            )

            entries = data.get(
                "entries"
            )

            if isinstance(
                entries,
                list,
            ):
                playlist = str(
                    data.get(
                        "title"
                    )
                    or data.get(
                        "playlist_title"
                    )
                    or "Playlist"
                )

                items = []

                for (
                    index,
                    entry,
                ) in enumerate(
                    entries,
                    start=1,
                ):
                    if isinstance(
                        entry,
                        dict,
                    ):
                        items.append(
                            self._make_item(
                                entry,
                                url,
                                playlist,
                                (
                                    entry.get(
                                        "playlist_index"
                                    )
                                    or index
                                ),
                            )
                        )

                callback(
                    True,
                    AnalysisResult(
                        url,
                        playlist,
                        str(
                            data.get(
                                "extractor_key"
                            )
                            or data.get(
                                "extractor"
                            )
                            or ""
                        ),
                        True,
                        items,
                    ),
                    None,
                )
                return

            item = (
                self._make_item(
                    data,
                    url,
                )
            )

            self._ensure_real_media(
                item,
                data,
            )

            callback(
                True,
                AnalysisResult(
                    url,
                    item.title,
                    item.extractor,
                    False,
                    [item],
                ),
                None,
            )

        except Exception as error:
            callback(
                False,
                None,
                self._normalize_error(
                    error
                ),
            )

    def enrich_item_async(
        self,
        item,
        browser_cookies,
        callback,
    ):
        self._executor.submit(
            self._enrich,
            item,
            browser_cookies,
            callback,
        )

    def _enrich(
        self,
        item,
        browser_cookies,
        callback,
    ):
        try:
            data = self._run_json(
                self._base_command(
                    browser_cookies
                )
                + [
                    item.webpage_url
                ]
            )

            enriched = self._make_item(
                data,
                item.source_url,
                item.playlist,
                item.playlist_index,
            )

            self._ensure_real_media(
                enriched,
                data,
            )

            # Some transparent extractors may omit identity fields during the
            # enrichment call. Keep the identity already known by the queue.
            if not (
                enriched.extractor_key
            ):
                enriched.extractor_key = (
                    item.extractor_key
                )

            if not (
                enriched.media_id
            ):
                enriched.media_id = (
                    item.media_id
                )

            if not (
                enriched.extractor
            ):
                enriched.extractor = (
                    item.extractor
                )

            enriched.output_format = (
                item.output_format
            )
            enriched.resolution = (
                item.resolution
            )
            enriched.manual_format_selector = (
                item.manual_format_selector
            )

            callback(
                True,
                enriched,
                None,
            )

        except Exception as error:
            callback(
                False,
                None,
                self._normalize_error(
                    error
                ),
            )

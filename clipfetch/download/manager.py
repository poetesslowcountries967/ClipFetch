from __future__ import annotations

import os
import re
import signal
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from clipfetch.config.constants import (
    DOWNLOAD_ARCHIVE_FILE,
    FILE_PREFIX,
    ORGANIZATION_TEMPLATES,
    PROGRESS_PREFIX,
    TITLE_PREFIX,
)
from clipfetch.core.error_translator import ErrorTranslator
from clipfetch.core.models import (
    DownloadResult,
    MediaItem,
)
from clipfetch.infrastructure.bundled_tools import BundledTools

class DownloadManager:
    def __init__(
        self,
        tools: BundledTools,
        progress_callback,
        log_callback,
        result_callback,
        history_manager=None,
    ):
        self.tools = tools
        self.progress_callback = progress_callback
        self.log_callback = log_callback
        self.result_callback = result_callback
        self.history_manager = history_manager

        self._lock = threading.Lock()
        self._processes = {}
        self._cancel_event = threading.Event()
        self._paused = False

    def _previous_download(
        self,
        item: MediaItem,
    ):
        if self.history_manager is None:
            return {
                "record": None,
                "output_path": "",
                "file_exists": False,
                "matched_by": "",
            }

        try:
            return self.history_manager.find_previous_download(
                item.extractor_key
                or item.extractor,
                item.media_id,
                item.webpage_url
                or item.source_url,
            )
        except Exception as error:
            self.log_callback(
                (
                    "[HISTÓRICO] Não foi possível consultar "
                    f"duplicidade: {error}"
                )
            )

            return {
                "record": None,
                "output_path": "",
                "file_exists": False,
                "matched_by": "",
            }

    @staticmethod
    def _known_download_is_missing(
        previous,
    ):
        """
        Retorna True somente quando existe um registro anterior conhecido,
        mas nenhum arquivo desse registro está atualmente acessível.

        Um simples registro no download-archive não é suficiente para esta
        função: precisamos de um registro real do histórico do aplicativo.
        """

        return bool(
            previous.get("record")
        ) and not bool(
            previous.get("file_exists")
        )

    @classmethod
    def _should_use_download_archive(
        cls,
        prevent_duplicates,
        previous,
    ):
        """
        O archive só pode bloquear a execução quando:

        - prevenção de duplicidade está ativa; e
        - não sabemos que o arquivo anterior desapareceu.

        Se o SQLite conhece a mídia, mas o arquivo não existe mais, o
        download precisa ser permitido novamente.
        """

        if not prevent_duplicates:
            return False

        if cls._known_download_is_missing(
            previous
        ):
            return False

        return True

    @staticmethod
    def _resolution_height(
        resolution,
    ):
        heights = {
            "2160p (4K)": 2160,
            "1440p": 1440,
            "1080p": 1080,
            "720p": 720,
            "480p": 480,
            "360p": 360,
        }
        return heights.get(
            resolution
        )

    @classmethod
    def _format_selector(
        cls,
        item,
    ):
        if (
            item.manual_format_selector
        ):
            return (
                item.manual_format_selector
            )

        if item.output_format in (
            "MP3",
            "M4A",
        ):
            return "bestaudio/best"

        video_filter = (
            "[vcodec!=images][ext!=mhtml]"
        )
        height = (
            cls._resolution_height(
                item.resolution
            )
        )

        if height:
            return (
                f"bestvideo*{video_filter}"
                f"[height<={height}]"
                f"+bestaudio/"
                f"best{video_filter}"
                f"[height<={height}]"
            )

        return (
            f"bestvideo*{video_filter}"
            f"+bestaudio/"
            f"best{video_filter}"
        )

    def build_command(
        self,
        item,
        download_folder,
        settings,
        use_download_archive=None,
    ):
        output_template = (
            ORGANIZATION_TEMPLATES.get(
                settings.get(
                    "organization",
                    "Todos na pasta",
                ),
                "%(title)s.%(ext)s",
            )
        )

        command = [
            str(
                self.tools.ensure_runtime_ytdlp()
            ),
            "--ignore-config",
            "--newline",
            "--no-update",
            "--ffmpeg-location",
            str(
                self.tools.bundle_bin_dir
            ),
            "--js-runtimes",
            f"deno:{self.tools.deno}",
            "--print",
            (
                f"before_dl:{TITLE_PREFIX}"
                "%(title)s"
            ),
            "--print",
            (
                f"after_move:{FILE_PREFIX}"
                "%(filepath)s"
            ),
            "--progress-template",
            (
                f"download:{PROGRESS_PREFIX}"
                "%(progress._percent_str)s|"
                "%(progress._speed_str)s|"
                "%(progress._eta_str)s"
            ),
            "-P",
            download_folder,
            "-o",
            output_template,
        ]

        speed = settings.get(
            "speed_limit",
            "Sem limite",
        )

        if speed != "Sem limite":
            command.extend(
                [
                    "--limit-rate",
                    speed,
                ]
            )

        browser = (
            settings.get(
                "browser_cookies",
                "Nenhum",
            )
            .casefold()
        )

        if browser != "nenhum":
            command.extend(
                [
                    "--cookies-from-browser",
                    browser,
                ]
            )

        if (
            use_download_archive
            is None
        ):
            use_download_archive = bool(
                settings.get(
                    "prevent_duplicates",
                    True,
                )
            )

        if use_download_archive:
            command.extend(
                [
                    "--download-archive",
                    str(
                        DOWNLOAD_ARCHIVE_FILE
                    ),
                ]
            )

        subtitle_mode = settings.get(
            "subtitle_mode",
            "Não baixar",
        )

        if (
            subtitle_mode
            != "Não baixar"
        ):
            command.append(
                "--write-subs"
            )

            if (
                subtitle_mode
                == "Normais + automáticas"
            ):
                command.append(
                    "--write-auto-subs"
                )

            languages = (
                settings.get(
                    "subtitle_languages",
                    "",
                )
                .strip()
            )

            if languages:
                command.extend(
                    [
                        "--sub-langs",
                        languages,
                    ]
                )

            if settings.get(
                "embed_subtitles",
                True,
            ):
                command.append(
                    "--embed-subs"
                )

        if settings.get(
            "embed_thumbnail",
            True,
        ):
            command.append(
                "--embed-thumbnail"
            )

        if settings.get(
            "embed_metadata",
            True,
        ):
            command.append(
                "--embed-metadata"
            )

        if settings.get(
            "embed_chapters",
            True,
        ):
            command.append(
                "--embed-chapters"
            )

        if item.output_format in (
            "MP3",
            "M4A",
        ):
            quality = settings.get(
                "audio_quality",
                "Melhor",
            )

            command.extend(
                [
                    "-x",
                    "--audio-format",
                    item.output_format.lower(),
                    "--audio-quality",
                    (
                        "0"
                        if quality == "Melhor"
                        else quality
                    ),
                ]
            )

        else:
            command.extend(
                [
                    "-f",
                    self._format_selector(
                        item
                    ),
                    "--merge-output-format",
                    item.output_format.lower(),
                ]
            )

        command.append(
            item.webpage_url
            or item.source_url
        )

        return command

    @staticmethod
    def _suspicious_output(
        output_path,
        item,
    ):
        if not output_path:
            return False

        suffix = (
            Path(output_path)
            .suffix
            .casefold()
        )

        if suffix in {
            ".mhtml",
            ".webp",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
        }:
            return True

        if (
            item.output_format
            == "MP4"
        ):
            return (
                suffix
                not in {
                    ".mp4",
                    ".m4v",
                }
            )

        if (
            item.output_format
            == "MKV"
        ):
            return (
                suffix
                != ".mkv"
            )

        if (
            item.output_format
            == "MP3"
        ):
            return (
                suffix
                != ".mp3"
            )

        if (
            item.output_format
            == "M4A"
        ):
            return (
                suffix
                not in {
                    ".m4a",
                    ".mp4",
                }
            )

        return False

    def start(
        self,
        items,
        download_folder,
        settings,
        finished_callback,
    ):
        self._cancel_event.clear()
        self._paused = False

        Path(
            download_folder
        ).expanduser().mkdir(
            parents=True,
            exist_ok=True,
        )

        threading.Thread(
            target=self._run_batch,
            args=(
                items,
                download_folder,
                settings,
                finished_callback,
            ),
            daemon=True,
        ).start()

    def _run_batch(
        self,
        items,
        download_folder,
        settings,
        finished_callback,
    ):
        concurrency = max(
            1,
            min(
                4,
                int(
                    settings.get(
                        "concurrency",
                        2,
                    )
                ),
            ),
        )

        with ThreadPoolExecutor(
            max_workers=concurrency
        ) as executor:
            futures = [
                executor.submit(
                    self._run_one,
                    item_id,
                    item,
                    download_folder,
                    settings,
                )
                for (
                    item_id,
                    item,
                ) in items
            ]

            for future in futures:
                try:
                    future.result()
                except Exception as error:
                    self.log_callback(
                        (
                            "Erro interno na fila: "
                            f"{error}\n"
                        )
                    )

        finished_callback()

    def _run_one(self,item_id,item,download_folder,settings):
        if self._cancel_event.is_set():
            self.result_callback(
                DownloadResult(
                    item_id,
                    False,
                    True,
                    error_message="Cancelado.",
                )
            )
            return

        prevent_duplicates = bool(
            settings.get(
                "prevent_duplicates",
                True,
            )
        )

        previous = self._previous_download(
            item
        )

        known_missing_file = (
            self._known_download_is_missing(
                previous
            )
        )

        use_download_archive = (
            self._should_use_download_archive(
                prevent_duplicates,
                previous,
            )
        )

        if (
            prevent_duplicates
            and known_missing_file
        ):
            previous_path = str(
                previous.get(
                    "output_path",
                    ""
                )
                or ""
            )

            self.log_callback(
                (
                    f"[REDOWNLOAD] {item.title}\n"
                    "A mídia existe no histórico, mas o arquivo "
                    "anterior não existe mais.\n"
                    f"Identidade: {item.media_key or 'fonte legada'}\n"
                    f"Caminho anterior: "
                    f"{previous_path or 'não registrado'}\n"
                    "O download-archive será ignorado somente "
                    "para esta execução."
                )
            )

            self.progress_callback(
                item_id,
                "Arquivo ausente — baixando novamente",
                0.0,
                "",
                "",
            )

        # Se nosso próprio histórico conhece a mesma identidade e o arquivo
        # ainda existe, não precisamos nem iniciar outro processo yt-dlp.
        # A regra continua condicionada à prevenção de duplicidade.
        if (
            prevent_duplicates
            and previous["file_exists"]
        ):
            previous_path = previous[
                "output_path"
            ]

            self.log_callback(
                (
                    f"[DUPLICADO] {item.title}\n"
                    "Identidade: "
                    f"{item.media_key or 'fonte legada'}\n"
                    f"Arquivo existente: {previous_path}"
                )
            )

            self.progress_callback(
                item_id,
                "Já baixado",
                100.0,
                "",
                "",
            )

            self.result_callback(
                DownloadResult(
                    item_id=item_id,
                    success=True,
                    cancelled=False,
                    output_path=previous_path,
                    technical_error=(
                        "A mídia foi localizada no histórico do "
                        "ClipFetch e o arquivo ainda existe."
                    ),
                    already_downloaded=True,
                    file_missing=False,
                )
            )
            return

        self.progress_callback(
            item_id,
            "Preparando",
            0.0,
            "",
            "",
        )

        output_path = ""
        collected = []

        command = self.build_command(
            item,
            download_folder,
            settings,
            use_download_archive=(
                use_download_archive
            ),
        )

        self.log_callback(
            (
                f"[PROCESSO] Iniciando yt-dlp: {item.title}\n"
                f"[PROCESSO] Comando: {command}"
            )
        )

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=self.tools.runtime_environment(),
                start_new_session=True,
            )
            with self._lock:
                self._processes[
                    item_id
                ] = process

            if process.stdout:
                for raw in process.stdout:
                    line = raw.rstrip()

                    if line.startswith(
                        TITLE_PREFIX
                    ):
                        self.progress_callback(
                            item_id,
                            (
                                line[
                                    len(
                                        TITLE_PREFIX
                                    ):
                                ].strip()
                                or item.title
                            ),
                            0.0,
                            "",
                            "",
                        )
                        continue

                    if line.startswith(
                        FILE_PREFIX
                    ):
                        output_path = line[
                            len(
                                FILE_PREFIX
                            ):
                        ].strip()
                        continue

                    if line.startswith(
                        PROGRESS_PREFIX
                    ):
                        parts = line[
                            len(
                                PROGRESS_PREFIX
                            ):
                        ].split("|")

                        self.progress_callback(
                            item_id,
                            "Baixando",
                            self._parse_percent(
                                (
                                    parts[0].strip()
                                    if parts
                                    else ""
                                )
                            ),
                            (
                                parts[1].strip()
                                if len(parts) > 1
                                else ""
                            ),
                            (
                                parts[2].strip()
                                if len(parts) > 2
                                else ""
                            ),
                        )
                        continue

                    if line:
                        self.log_callback(
                            f"[{item.title}] {line}\n"
                        )

                        normalized = (
                            line.casefold()
                        )

                        if any(
                            keyword
                            in normalized
                            for keyword
                            in (
                                "error",
                                "warning",
                                "storyboard",
                                "mhtml",
                            )
                        ):
                            collected.append(
                                line
                            )
            process.wait()

            self.log_callback(
                (
                    f"[PROCESSO] yt-dlp finalizado: {item.title} | "
                    f"returncode={process.returncode}"
                )
            )

            cancelled = (
                self._cancel_event.is_set()
                or process.returncode in (-15, 143)
            )
            if cancelled:
                self.result_callback(
                    DownloadResult(
                        item_id,
                        False,
                        True,
                        output_path,
                        "Cancelado.",
                    )
                )
                return

            technical = "\n".join(
                collected
            )
            if (
                process.returncode == 0
                and self._suspicious_output(
                    output_path,
                    item,
                )
            ):
                error = ErrorTranslator.to_error(
                    (
                        technical
                        + f"\n\nO arquivo final não possui uma "
                        f"extensão de mídia válida: {output_path}"
                        "\nno real media stream"
                    ),
                    default_title=(
                        "O resultado não é um arquivo de mídia"
                    ),
                    default_message=(
                        "O download terminou, mas o arquivo criado "
                        "não é o vídeo/áudio solicitado."
                    ),
                )

                self.result_callback(
                    DownloadResult(
                        item_id,
                        False,
                        False,
                        output_path,
                        error.message,
                        error.technical_details,
                    )
                )
                return

            if process.returncode == 0:
                # after_move:filepath é o caminho confiável do arquivo final.
                # Se ele existe, houve uma saída real desta execução.
                if output_path:
                    final_path = Path(
                        output_path
                    )

                    if final_path.exists():
                        self.progress_callback(
                            item_id,
                            "Concluído",
                            100.0,
                            "",
                            "",
                        )

                        self.result_callback(
                            DownloadResult(
                                item_id=item_id,
                                success=True,
                                cancelled=False,
                                output_path=output_path,
                            )
                        )
                        return

                    error = ErrorTranslator.to_error(
                        (
                            technical
                            + "\n\nyt-dlp informou after_move:filepath, "
                            "mas o arquivo não existe no caminho retornado: "
                            + output_path
                        ),
                        default_title=(
                            "Arquivo final não encontrado"
                        ),
                        default_message=(
                            "O yt-dlp informou um caminho final, "
                            "mas o arquivo não foi encontrado nele."
                        ),
                    )

                    self.result_callback(
                        DownloadResult(
                            item_id=item_id,
                            success=False,
                            cancelled=False,
                            output_path=output_path,
                            error_message=error.message,
                            technical_error=(
                                error.technical_details
                            ),
                        )
                    )
                    return

                # Código 0 sem after_move significa que nenhum arquivo final
                # novo foi produzido.
                #
                # Se esta execução usou download-archive e não temos um
                # arquivo existente para retornar, fazemos UMA tentativa
                # adicional sem archive. Isso cobre, de forma genérica:
                #
                # - arquivo apagado manualmente;
                # - histórico antigo/incompleto;
                # - download-archive sobrevivendo após limpeza do SQLite.
                #
                # A chamada recursiva recebe prevent_duplicates=False, então
                # nunca pode entrar em um ciclo infinito.
                if use_download_archive:
                    previous = self._previous_download(
                        item
                    )

                    if previous["file_exists"]:
                        previous_path = previous[
                            "output_path"
                        ]

                        details = (
                            "yt-dlp não produziu um novo filepath, "
                            "mas o arquivo anterior foi localizado "
                            "no histórico e ainda existe.\n"
                            f"Identidade: "
                            f"{item.media_key or 'indisponível'}\n"
                            f"Caminho: {previous_path}"
                        )

                        self.log_callback(
                            (
                                f"[DUPLICADO] {item.title}\n"
                                f"{details}"
                            )
                        )

                        self.progress_callback(
                            item_id,
                            "Já baixado",
                            100.0,
                            "",
                            "",
                        )

                        self.result_callback(
                            DownloadResult(
                                item_id=item_id,
                                success=True,
                                cancelled=False,
                                output_path=previous_path,
                                technical_error=details,
                                already_downloaded=True,
                                file_missing=False,
                            )
                        )
                        return

                    self.log_callback(
                        (
                            f"[REDOWNLOAD] {item.title}\n"
                            "O yt-dlp terminou sem filepath enquanto "
                            "o download-archive estava ativo, e não "
                            "há arquivo existente conhecido.\n"
                            "Nova tentativa automática sem "
                            "download-archive."
                        )
                    )

                    self.progress_callback(
                        item_id,
                        "Arquivo ausente — baixando novamente",
                        0.0,
                        "",
                        "",
                    )

                    retry_settings = dict(
                        settings
                    )

                    retry_settings[
                        "prevent_duplicates"
                    ] = False

                    self._run_one(
                        item_id,
                        item,
                        download_folder,
                        retry_settings,
                    )
                    return

                error = ErrorTranslator.to_error(
                    (
                        technical
                        + "\n\nyt-dlp terminou com código 0, "
                        "mas não informou after_move:filepath mesmo "
                        "com o download-archive fora desta execução."
                    ),
                    default_title=(
                        "Nenhum arquivo final foi informado"
                    ),
                    default_message=(
                        "O yt-dlp terminou sem erro, mas o aplicativo "
                        "não recebeu o caminho de um arquivo final."
                    ),
                )

                self.result_callback(
                    DownloadResult(
                        item_id=item_id,
                        success=False,
                        cancelled=False,
                        error_message=error.message,
                        technical_error=(
                            error.technical_details
                        ),
                    )
                )
                return

            error = ErrorTranslator.to_error(
                technical,
                default_title="Falha no download",
                default_message=(
                    "O yt-dlp não conseguiu concluir o download."
                ),
            )

            self.result_callback(
                DownloadResult(
                    item_id,
                    False,
                    False,
                    output_path,
                    error.message,
                    error.technical_details,
                )
            )
        except OSError as error:
            (
                _,
                repair,
            ) = (
                self.tools
                .repair_runtime_ytdlp()
            )

            translated = (
                ErrorTranslator.to_error(
                    (
                        f"{error}\n\n"
                        "Diagnóstico do executável:\n"
                        f"{repair}"
                    ),
                    default_title=(
                        "Não foi possível iniciar o downloader"
                    ),
                    default_message=(
                        "O componente yt-dlp não pôde ser iniciado."
                    ),
                )
            )

            self.result_callback(
                DownloadResult(
                    item_id,
                    False,
                    False,
                    output_path,
                    translated.message,
                    translated.technical_details,
                )
            )

        except Exception as error:
            translated = (
                ErrorTranslator.to_error(
                    str(error),
                    default_title=(
                        "Falha no download"
                    ),
                    default_message=(
                        "Ocorreu um erro durante o download."
                    ),
                )
            )

            self.result_callback(
                DownloadResult(
                    item_id,
                    False,
                    False,
                    output_path,
                    translated.message,
                    translated.technical_details,
                )
            )

        finally:
            with self._lock:
                self._processes.pop(
                    item_id,
                    None,
                )

    @staticmethod
    def _parse_percent(
        text,
    ):
        match = re.search(
            r"([0-9]+(?:\.[0-9]+)?)",
            text,
        )

        if not match:
            return 0.0

        try:
            return max(
                0.0,
                min(
                    100.0,
                    float(
                        match.group(1)
                    ),
                ),
            )
        except ValueError:
            return 0.0

    def _active_processes(
        self,
    ):
        with self._lock:
            return list(
                self._processes.values()
            )

    def pause_all(self):
        for process in (
            self._active_processes()
        ):
            if (
                process.poll()
                is None
            ):
                try:
                    os.killpg(
                        os.getpgid(
                            process.pid
                        ),
                        signal.SIGSTOP,
                    )
                except OSError:
                    pass

        self._paused = True

    def resume_all(self):
        for process in (
            self._active_processes()
        ):
            if (
                process.poll()
                is None
            ):
                try:
                    os.killpg(
                        os.getpgid(
                            process.pid
                        ),
                        signal.SIGCONT,
                    )
                except OSError:
                    pass

        self._paused = False

    @property
    def paused(self):
        return self._paused

    def cancel_all(self):
        self._cancel_event.set()

        for process in (
            self._active_processes()
        ):
            if (
                process.poll()
                is not None
            ):
                continue

            try:
                os.killpg(
                    os.getpgid(
                        process.pid
                    ),
                    signal.SIGTERM,
                )
            except OSError:
                try:
                    process.terminate()
                except OSError:
                    pass

from __future__ import annotations

import subprocess
import threading
from typing import Callable

from clipfetch.infrastructure.bundled_tools import BundledTools


LogCallback = Callable[[str], None]
FinishedCallback = Callable[[bool, str], None]


class UpdateManager:
    """
    Atualiza apenas o yt-dlp.

    FFmpeg e Deno permanecem dentro do .app. O yt-dlp, por outro lado, muda
    frequentemente porque os sites alteram seus extratores. Por isso mantemos
    uma cópia atualizável em Application Support.

    A atualização usa o próprio mecanismo oficial do executável yt-dlp.
    """

    def __init__(
        self,
        tools: BundledTools,
        log_callback: LogCallback,
    ):
        self.tools = tools
        self.log_callback = log_callback

    def update_async(
        self,
        finished_callback: FinishedCallback,
    ) -> None:
        """Executa a atualização fora da thread da interface."""
        thread = threading.Thread(
            target=self._update,
            args=(finished_callback,),
            daemon=True,
        )
        thread.start()

    def _update(
        self,
        finished_callback: FinishedCallback,
    ) -> None:
        try:
            executable = self.tools.ensure_runtime_ytdlp()
        except OSError as error:
            finished_callback(
                False,
                f"Não foi possível preparar o yt-dlp: {error}",
            )
            return

        # Nightly é escolhido explicitamente para manter o aplicativo alinhado
        # ao canal recomendado pelo projeto yt-dlp para usuários regulares.
        command = [
            str(executable),
            "--update-to",
            "nightly@latest",
        ]

        self.log_callback(
            "Verificando atualização do yt-dlp...\n"
        )

        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=self.tools.runtime_environment(),
            )

            output_lines = []

            if process.stdout:
                for line in process.stdout:
                    output_lines.append(line.rstrip())
                    self.log_callback(line)

            process.wait()

        except OSError as error:
            finished_callback(
                False,
                f"Falha ao executar o atualizador: {error}",
            )
            return

        message = "\n".join(
            line for line in output_lines if line
        ).strip()

        if process.returncode == 0:
            new_version = self.tools.record_runtime_version()
            if new_version:
                message = ((message + "\n\n") if message else "") + f"Versão ativa: {new_version}"
            finished_callback(
                True,
                message or "yt-dlp atualizado.",
            )
        else:
            finished_callback(
                False,
                message or (
                    "O atualizador terminou com código "
                    f"{process.returncode}."
                ),
            )

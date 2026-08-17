from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import uuid4


@dataclass
class FormatInfo:
    format_id: str
    ext: str = ""
    resolution: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    vcodec: str = ""
    acodec: str = ""
    tbr: Optional[float] = None
    filesize: Optional[int] = None
    filesize_approx: Optional[int] = None
    dynamic_range: str = ""
    note: str = ""

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "FormatInfo":
        return cls(
            format_id=str(data.get("format_id", "")),
            ext=str(data.get("ext") or ""),
            resolution=str(data.get("resolution") or ""),
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
            vcodec=str(data.get("vcodec") or ""),
            acodec=str(data.get("acodec") or ""),
            tbr=data.get("tbr"),
            filesize=data.get("filesize"),
            filesize_approx=data.get("filesize_approx"),
            dynamic_range=str(data.get("dynamic_range") or ""),
            note=str(data.get("format_note") or ""),
        )

    @property
    def estimated_size(self) -> int:
        return int(self.filesize or self.filesize_approx or 0)

    @property
    def is_storyboard(self) -> bool:
        return (
            self.vcodec.casefold() == "images"
            or self.ext.casefold() == "mhtml"
        )

    @property
    def has_video(self) -> bool:
        return (
            self.vcodec not in ("", "none")
            and not self.is_storyboard
        )

    @property
    def has_audio(self) -> bool:
        return self.acodec not in ("", "none")

    @property
    def is_usable_media(self) -> bool:
        return self.has_video or self.has_audio

    def selector_with_audio(self) -> str:
        if self.has_video and not self.has_audio:
            return f"{self.format_id}+bestaudio/best"
        return self.format_id


@dataclass
class MediaItem:
    source_url: str
    webpage_url: str

    # ID interno estável. A linha da tabela pode mudar enquanto análises
    # de playlists terminam, mas este ID nunca muda durante a vida do item.
    queue_id: str = field(default_factory=lambda: uuid4().hex)

    title: str = "Sem título"
    uploader: str = ""

    # Nome amigável/técnico exibido na UI.
    extractor: str = ""

    # Identidade genérica fornecida pelo yt-dlp.
    # Não depende de um site específico.
    extractor_key: str = ""
    media_id: str = ""

    duration: Optional[float] = None
    thumbnail_url: str = ""
    playlist: str = ""
    playlist_index: Optional[int] = None
    formats: list[FormatInfo] = field(default_factory=list)
    subtitles: list[str] = field(default_factory=list)
    automatic_subtitles: list[str] = field(default_factory=list)

    output_format: str = "MP4"
    resolution: str = "Melhor disponível"
    manual_format_selector: str = ""

    # Estados possíveis da análise:
    # ready / waiting / analyzing / error
    analysis_state: str = "ready"

    status: str = "Pronto"
    progress: float = 0.0
    speed: str = ""
    eta: str = ""
    output_path: str = ""
    error_message: str = ""
    technical_error: str = ""


    @property
    def media_key(self) -> str:
        """
        Identidade estável usada pelo histórico do aplicativo.

        O yt-dlp trabalha com extractor + id para identificar mídia em
        mecanismos como o download archive. Aqui mantemos uma chave própria
        equivalente para recuperar o caminho final sem depender de mensagens
        específicas de cada site.
        """

        extractor = (
            self.extractor_key
            or self.extractor
            or ""
        ).strip().casefold()

        media_id = (
            self.media_id
            or ""
        ).strip()

        if not extractor or not media_id:
            return ""

        return f"{extractor}:{media_id}"

    @property
    def display_duration(self) -> str:
        if not self.duration:
            return "—"
        seconds = int(self.duration)
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"

    @property
    def site_name(self) -> str:
        return self.extractor or "—"

    @property
    def estimated_size(self) -> int:
        return max(
            (
                fmt.estimated_size
                for fmt in self.formats
                if fmt.estimated_size
            ),
            default=0,
        )

    @property
    def analysis_pending(self) -> bool:
        return self.analysis_state in ("waiting", "analyzing")

    @property
    def ready_for_download(self) -> bool:
        return (
            self.analysis_state == "ready"
            and self.status in ("Pronto", "Erro", "Cancelado")
        )


@dataclass
class AnalysisResult:
    original_url: str
    title: str
    extractor: str
    is_playlist: bool
    items: list[MediaItem]


@dataclass
class DownloadResult:
    item_id: str
    success: bool
    cancelled: bool
    output_path: str = ""
    error_message: str = ""
    technical_error: str = ""

    # Resultado genérico de prevenção de duplicidade.
    already_downloaded: bool = False
    file_missing: bool = False

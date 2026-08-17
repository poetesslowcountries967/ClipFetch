"""Thread-safe Qt signal declarations for UI/background communication."""

from PySide6.QtCore import QObject, Signal

class AppSignals(QObject):
    """
    Ponte thread-safe entre serviços em background e a interface Qt.
    """

    analysis_started = Signal(str)

    analysis_finished = Signal(
        bool,
        object,
        object,
        str,
    )

    enrich_finished = Signal(
        bool,
        object,
        object,
        str,
    )

    thumbnail_finished = Signal(
        bool,
        object,
        str,
    )

    progress = Signal(
        str,
        str,
        float,
        str,
        str,
    )

    log = Signal(str)

    download_result = Signal(object)

    downloads_finished = Signal()

    ytdlp_update_finished = Signal(
        bool,
        str,
    )

    app_update_finished = Signal(
        bool,
        object,
        str,
    )


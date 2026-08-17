from __future__ import annotations

from PySide6.QtCore import (
    QObject,
    Signal,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
)

from clipfetch.i18n import tr
from clipfetch.infrastructure.bundled_tools import BundledTools
from clipfetch.services.extractor_manager import (
    ExtractorLists,
    ExtractorManager,
)
from clipfetch.ui.error_dialog import FriendlyErrorDialog


class ExtractorSignals(QObject):
    finished = Signal(
        bool,
        object,
        object,
    )


class SupportedSitesDialog(QDialog):
    """List/search yt-dlp extractors without blocking the UI."""

    def __init__(
        self,
        tools: BundledTools,
        parent=None,
    ):
        super().__init__(parent)

        self.manager = ExtractorManager(
            tools
        )

        self.signals = ExtractorSignals()
        self.signals.finished.connect(
            self._load_finished
        )

        self.extractor_names = []

        self.setWindowTitle(
            "Fontes suportadas pelo yt-dlp"
        )
        self.resize(
            820,
            690,
        )

        self._build_ui()
        self.reload(False)

    def _build_ui(self):
        root = QVBoxLayout(self)

        title = QLabel(
            "<b>Fontes suportadas</b>"
        )
        title.setStyleSheet(
            "font-size: 18px;"
        )
        root.addWidget(title)

        explanation = QLabel(
            (
                "Esta lista é fornecida pelo próprio yt-dlp. "
                "Internamente cada integração é chamada de extractor. "
                "A pesquisa abaixo filtra localmente a lista já carregada."
            )
        )
        explanation.setWordWrap(True)
        root.addWidget(explanation)

        row = QHBoxLayout()
        row.addWidget(
            QLabel("Pesquisar:")
        )

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(
            "Ex.: YouTube, Instagram, Vimeo, Twitch..."
        )
        self.search_edit.textChanged.connect(
            self.apply_filter
        )
        row.addWidget(
            self.search_edit,
            1,
        )

        self.reload_button = QPushButton(
            "Perguntar novamente ao yt-dlp"
        )
        self.reload_button.clicked.connect(
            lambda: self.reload(True)
        )
        row.addWidget(
            self.reload_button
        )

        root.addLayout(row)

        self.count_label = QLabel(
            "Carregando..."
        )
        root.addWidget(
            self.count_label
        )

        self.list_widget = QListWidget()
        root.addWidget(
            self.list_widget,
            1,
        )

        footer = QHBoxLayout()

        self.source_label = QLabel("")
        footer.addWidget(
            self.source_label
        )
        footer.addStretch()

        close = QPushButton(
            "Fechar"
        )
        close.clicked.connect(
            self.accept
        )
        footer.addWidget(close)

        root.addLayout(footer)

    def reload(
        self,
        force_refresh=False,
    ):
        self.reload_button.setEnabled(
            False
        )

        if (
            force_refresh
            and self.extractor_names
        ):
            self.count_label.setText(
                tr(
                    (
                        "{count} fontes carregadas. "
                        "Atualizando em segundo plano..."
                    ),
                    count=len(
                        self.extractor_names
                    ),
                )
            )
        else:
            self.count_label.setText(
                tr("Carregando lista...")
            )

        self.manager.load_async(
            self.signals.finished.emit,
            force_refresh=force_refresh,
        )

    def _load_finished(
        self,
        success,
        data,
        error,
    ):
        self.reload_button.setEnabled(
            True
        )

        if (
            not success
            or data is None
        ):
            if self.extractor_names:
                self.count_label.setText(
                    tr(
                        "{count} fontes disponíveis no cache.",
                        count=len(
                            self.extractor_names
                        ),
                    )
                )
            else:
                self.count_label.setText(
                    tr(
                        "Não foi possível carregar a lista."
                    )
                )

            if error is not None:
                FriendlyErrorDialog(
                    error,
                    self,
                ).exec()

            return

        result: ExtractorLists = data

        self.extractor_names = list(
            result.names
        )

        self.source_label.setText(
            tr(
                (
                    "Lista carregada do cache."
                    if result.from_cache
                    else (
                        "Lista atualizada diretamente "
                        "pelo yt-dlp."
                    )
                )
            )
        )

        self.apply_filter()

    def apply_filter(self):
        query = (
            self.search_edit.text()
            .strip()
            .casefold()
        )

        if query:
            matches = [
                name
                for name
                in self.extractor_names
                if query in name.casefold()
            ]
        else:
            matches = list(
                self.extractor_names
            )

        self.list_widget.clear()
        self.list_widget.addItems(
            matches
        )

        if query:
            self.count_label.setText(
                tr(
                    "{matches} resultado(s) de {total} fontes.",
                    matches=len(matches),
                    total=len(
                        self.extractor_names
                    ),
                )
            )
        else:
            self.count_label.setText(
                tr(
                    "{count} fontes/extractors disponíveis.",
                    count=len(
                        self.extractor_names
                    ),
                )
            )

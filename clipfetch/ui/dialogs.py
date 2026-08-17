from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from clipfetch.core.models import (
    FormatInfo,
    MediaItem,
)
from clipfetch.i18n import tr


class PlaylistSelectionDialog(QDialog):
    def __init__(
        self,
        title: str,
        items: list[MediaItem],
        parent=None,
    ):
        super().__init__(parent)

        self.items = items

        self.setWindowTitle(
            tr("Selecionar itens — ")
            + title
        )
        self.resize(
            760,
            560,
        )

        layout = QVBoxLayout(self)

        label = QLabel(
            tr(
                (
                    "<b>{count} item(ns) encontrados.</b><br>"
                    "Desmarque o que não deseja adicionar à fila."
                ),
                count=len(items),
            )
        )
        label.setWordWrap(True)
        layout.addWidget(label)

        actions = QHBoxLayout()

        all_button = QPushButton(
            "Selecionar tudo"
        )
        all_button.clicked.connect(
            lambda: self._set_all(True)
        )

        none_button = QPushButton(
            "Desmarcar tudo"
        )
        none_button.clicked.connect(
            lambda: self._set_all(False)
        )

        actions.addWidget(
            all_button
        )
        actions.addWidget(
            none_button
        )
        actions.addStretch()

        layout.addLayout(actions)

        self.list_widget = QListWidget()

        for index, item in enumerate(
            items,
            start=1,
        ):
            list_item = QListWidgetItem(
                (
                    f"{item.playlist_index or index:03d}  "
                    f"{item.title}"
                )
            )

            list_item.setFlags(
                list_item.flags()
                | Qt.ItemIsUserCheckable
            )
            list_item.setCheckState(
                Qt.Checked
            )

            self.list_widget.addItem(
                list_item
            )

        layout.addWidget(
            self.list_widget,
            1,
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok
            | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(
            self.accept
        )
        buttons.rejected.connect(
            self.reject
        )
        layout.addWidget(buttons)

    def _set_all(
        self,
        selected,
    ):
        state = (
            Qt.Checked
            if selected
            else Qt.Unchecked
        )

        for row in range(
            self.list_widget.count()
        ):
            self.list_widget.item(
                row
            ).setCheckState(
                state
            )

    def selected_items(self):
        return [
            media
            for index, media
            in enumerate(self.items)
            if (
                self.list_widget.item(index)
                .checkState()
                == Qt.Checked
            )
        ]


class FormatDetailsDialog(QDialog):
    def __init__(
        self,
        item: MediaItem,
        parent=None,
    ):
        super().__init__(parent)

        self.media_item = item
        self.selected_selector = ""

        self.setWindowTitle(
            tr("Formatos — ")
            + item.title
        )
        self.resize(
            980,
            560,
        )

        layout = QVBoxLayout(self)

        text = QLabel(
            (
                "Selecione um formato apenas se quiser substituir a escolha "
                "automática. Formatos somente de vídeo serão combinados com "
                "o melhor áudio."
            )
        )
        text.setWordWrap(True)
        layout.addWidget(text)

        self.table = QTableWidget(
            len(item.formats),
            9,
        )
        self.table.setHorizontalHeaderLabels(
            [
                "ID",
                "Ext.",
                "Resolução",
                "FPS",
                "Vídeo",
                "Áudio",
                "Bitrate",
                "Tamanho",
                "HDR",
            ]
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SingleSelection
        )
        self.table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )

        for row, fmt in enumerate(
            item.formats
        ):
            values = [
                fmt.format_id,
                fmt.ext,
                (
                    fmt.resolution
                    or (
                        f"{fmt.width or '?'}"
                        f"x{fmt.height or '?'}"
                    )
                ),
                str(fmt.fps or ""),
                fmt.vcodec,
                fmt.acodec,
                str(fmt.tbr or ""),
                self._size(
                    fmt.estimated_size
                ),
                fmt.dynamic_range,
            ]

            for column, value in enumerate(
                values
            ):
                self.table.setItem(
                    row,
                    column,
                    QTableWidgetItem(
                        value
                    ),
                )

        self.table.resizeColumnsToContents()
        layout.addWidget(
            self.table,
            1,
        )

        buttons = QDialogButtonBox()

        use = buttons.addButton(
            "Usar formato selecionado",
            QDialogButtonBox.AcceptRole,
        )
        use.clicked.connect(
            self._use_selected
        )

        automatic = buttons.addButton(
            "Voltar ao automático",
            QDialogButtonBox.ResetRole,
        )
        automatic.clicked.connect(
            self._use_automatic
        )

        cancel = buttons.addButton(
            "Cancelar",
            QDialogButtonBox.RejectRole,
        )
        cancel.clicked.connect(
            self.reject
        )

        layout.addWidget(buttons)

    @staticmethod
    def _size(value):
        if not value:
            return "—"

        number = float(value)

        for unit in (
            "B",
            "KB",
            "MB",
            "GB",
            "TB",
        ):
            if number < 1024:
                return (
                    f"{number:.1f} "
                    f"{unit}"
                )

            number /= 1024

        return f"{number:.1f} PB"

    def _use_selected(self):
        row = self.table.currentRow()

        if row < 0:
            QMessageBox.information(
                self,
                tr("Selecione um formato"),
                tr(
                    "Clique em uma linha da tabela primeiro."
                ),
            )
            return

        fmt: FormatInfo = (
            self.media_item.formats[row]
        )

        self.selected_selector = (
            fmt.selector_with_audio()
        )

        self.accept()

    def _use_automatic(self):
        self.selected_selector = ""
        self.accept()

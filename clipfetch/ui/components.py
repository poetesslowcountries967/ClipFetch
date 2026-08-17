"""Reusable Qt widgets used by the main window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QLabel,
    QPlainTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from clipfetch.core.models import MediaItem
from clipfetch.i18n import tr

class DropInput(QPlainTextEdit):
    """
    Campo de entrada com drag & drop.

    Aceita:
    - texto/URLs;
    - arquivos .txt contendo vários links.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        mime = event.mimeData()

        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()
            return

        super().dragEnterEvent(event)

    def dropEvent(self, event):
        mime = event.mimeData()
        collected = []

        if mime.hasUrls():
            for url in mime.urls():

                if url.isLocalFile():
                    path = Path(
                        url.toLocalFile()
                    )

                    if (
                        path.is_file()
                        and path.suffix.casefold() == ".txt"
                    ):
                        try:
                            collected.extend(
                                path.read_text(
                                    encoding="utf-8"
                                ).splitlines()
                            )
                        except OSError:
                            pass

                else:
                    collected.append(
                        url.toString()
                    )

        elif mime.hasText():
            collected.extend(
                mime.text().splitlines()
            )

        clean = [
            value.strip()
            for value in collected
            if value.strip()
        ]

        if not clean:
            super().dropEvent(event)
            return

        current = (
            self.toPlainText().strip()
        )

        payload = "\n".join(clean)

        self.setPlainText(
            f"{current}\n{payload}".strip()
        )

        event.acceptProposedAction()


class QueueSummaryWidget(QWidget):
    """Célula visual compacta: título forte + metadados em segunda linha."""

    def __init__(self, item: MediaItem, parent=None):
        super().__init__(parent)
        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 8, 5)
        layout.setSpacing(2)

        title = QLabel(item.title or tr("Sem título"))
        title.setObjectName("queueItemTitle")
        title.setToolTip(item.webpage_url or item.source_url)
        title.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        parts = [
            item.site_name,
            item.output_format,
            tr(item.resolution),
        ]
        if item.display_duration != "—":
            parts.append(item.display_duration)

        meta = QLabel(" · ".join(part for part in parts if part and part != "—"))
        meta.setObjectName("queueItemMeta")
        meta.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        layout.addWidget(title)
        layout.addWidget(meta)


class SpinArrowController(QObject):
    """
    Setas explícitas para QSpinBox/QTimeEdit.

    Alguns estilos do macOS/Qt deixam os indicadores nativos invisíveis
    quando QAbstractSpinBox recebe stylesheet. O ClipFetch desenha dois
    botões reais ▲/▼ e chama stepUp()/stepDown() do próprio controle.
    """

    BUTTON_WIDTH = 25

    def __init__(self, spin_box):
        super().__init__(spin_box)

        self.spin_box = spin_box

        self.spin_box.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons
        )

        self.up_button = QToolButton(
            self.spin_box
        )
        self.up_button.setObjectName(
            "spinStepButton"
        )
        self.up_button.setProperty(
            "stepDirection",
            "up",
        )
        self.up_button.setText("▲")
        self.up_button.setAutoRepeat(True)
        self.up_button.setAutoRepeatDelay(350)
        self.up_button.setAutoRepeatInterval(90)
        self.up_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )
        self.up_button.clicked.connect(
            self.spin_box.stepUp
        )

        self.down_button = QToolButton(
            self.spin_box
        )
        self.down_button.setObjectName(
            "spinStepButton"
        )
        self.down_button.setProperty(
            "stepDirection",
            "down",
        )
        self.down_button.setText("▼")
        self.down_button.setAutoRepeat(True)
        self.down_button.setAutoRepeatDelay(350)
        self.down_button.setAutoRepeatInterval(90)
        self.down_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )
        self.down_button.clicked.connect(
            self.spin_box.stepDown
        )

        self.spin_box.installEventFilter(
            self
        )

        QTimer.singleShot(
            0,
            self._sync_geometry,
        )

    def _sync_geometry(self):
        width = self.BUTTON_WIDTH
        total_height = max(
            26,
            self.spin_box.height(),
        )

        upper_height = max(
            13,
            total_height // 2,
        )

        lower_height = max(
            13,
            total_height - upper_height,
        )

        x = max(
            0,
            self.spin_box.width()
            - width,
        )

        self.up_button.setGeometry(
            x,
            0,
            width,
            upper_height,
        )

        self.down_button.setGeometry(
            x,
            upper_height,
            width,
            lower_height,
        )

        enabled = self.spin_box.isEnabled()

        self.up_button.setEnabled(
            enabled
        )
        self.down_button.setEnabled(
            enabled
        )

        self.up_button.raise_()
        self.down_button.raise_()

    def eventFilter(
        self,
        watched,
        event,
    ):
        if (
            watched is self.spin_box
            and event.type()
            in (
                QEvent.Type.Resize,
                QEvent.Type.Show,
                QEvent.Type.EnabledChange,
                QEvent.Type.StyleChange,
                QEvent.Type.PaletteChange,
            )
        ):
            QTimer.singleShot(
                0,
                self._sync_geometry,
            )

        return super().eventFilter(
            watched,
            event,
        )


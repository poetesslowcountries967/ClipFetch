from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from clipfetch.core.errors import AppError
from clipfetch.i18n import tr


class FriendlyErrorDialog(QDialog):
    """Compact user-facing error with optional technical details."""

    def __init__(
        self,
        error: AppError,
        parent=None,
    ):
        super().__init__(parent)

        self.error = error

        self.setWindowTitle(
            tr(error.title)
        )
        self.resize(
            610,
            260,
        )

        root = QVBoxLayout(self)

        title = QLabel(
            tr(error.title)
        )
        title.setStyleSheet(
            "font-size: 18px; font-weight: 700;"
        )
        title.setWordWrap(True)
        root.addWidget(title)

        message = QLabel(
            tr(error.message)
        )
        message.setWordWrap(True)
        root.addWidget(message)

        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlainText(
            error.technical_details
            or tr("Nenhum detalhe técnico adicional.")
        )
        self.details.setMaximumHeight(135)
        self.details.hide()
        root.addWidget(self.details)

        actions = QHBoxLayout()

        self.toggle_button = QPushButton(
            "Mostrar detalhes técnicos"
        )
        self.toggle_button.setCheckable(True)
        self.toggle_button.toggled.connect(
            self._toggle_details
        )

        copy_button = QPushButton(
            "Copiar erro"
        )
        copy_button.clicked.connect(
            self._copy
        )

        close_button = QPushButton(
            "OK"
        )
        close_button.clicked.connect(
            self.accept
        )

        actions.addWidget(
            self.toggle_button
        )
        actions.addWidget(
            copy_button
        )
        actions.addStretch()
        actions.addWidget(
            close_button
        )

        root.addLayout(actions)

    def _toggle_details(
        self,
        visible: bool,
    ):
        self.details.setVisible(
            visible
        )

        self.toggle_button.setText(
            tr(
                "Ocultar detalhes técnicos"
                if visible
                else "Mostrar detalhes técnicos"
            )
        )

        self.resize(
            610,
            430 if visible else 260,
        )

    def _copy(self):
        QGuiApplication.clipboard().setText(
            (
                f"{tr(self.error.title)}\n\n"
                f"{tr(self.error.message)}\n\n"
                f"{tr('Detalhes técnicos:')}\n"
                f"{self.error.technical_details}"
            )
        )

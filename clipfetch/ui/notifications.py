from __future__ import annotations

from PySide6.QtCore import (
    QEvent,
    QObject,
)
from PySide6.QtWidgets import (
    QApplication,
    QStyle,
    QSystemTrayIcon,
)


class NotificationController(QObject):
    """
    Alertas de interface e badge do Dock.

    O badge representa notificações ainda não vistas. Ele não representa
    quantidade de itens na fila.
    """

    def __init__(
        self,
        window,
        tray_enabled=True,
    ):
        super().__init__(window)

        self.window = window
        self.tray_icon = None
        self._unread_count = 0

        self.window.installEventFilter(self)

        if tray_enabled:
            self._setup_tray()

        self.clear_unread()

    def _setup_tray(self):
        try:
            if not QSystemTrayIcon.isSystemTrayAvailable():
                return

            icon = self.window.style().standardIcon(
                QStyle.StandardPixmap.SP_ArrowDown
            )

            self.tray_icon = QSystemTrayIcon(
                icon,
                self.window,
            )
            self.tray_icon.setToolTip(
                self.window.windowTitle()
            )
            self.tray_icon.messageClicked.connect(
                self._message_clicked
            )
            self.tray_icon.show()

        except Exception:
            self.tray_icon = None

    def notify(
        self,
        title,
        message,
    ):
        try:
            if (
                self.tray_icon
                and QSystemTrayIcon.supportsMessages()
            ):
                self.tray_icon.showMessage(
                    str(title),
                    str(message),
                    QSystemTrayIcon.MessageIcon.Information,
                    8000,
                )
        except Exception:
            pass

        if self.window.isActiveWindow():
            self.clear_unread()
        else:
            self._unread_count += 1
            self._apply_badge()

        try:
            QApplication.alert(
                self.window,
                3000,
            )
        except Exception:
            pass

    def clear_unread(self):
        self._unread_count = 0
        self._apply_badge()

    def set_enabled(
        self,
        enabled,
    ):
        if not enabled:
            self.clear_unread()

    def close(self):
        self.clear_unread()

        if self.tray_icon is not None:
            try:
                self.tray_icon.hide()
            except Exception:
                pass

    def _apply_badge(self):
        app = QApplication.instance()
        setter = getattr(
            app,
            "setBadgeNumber",
            None,
        )

        if not callable(setter):
            return

        try:
            setter(
                int(self._unread_count)
            )
        except Exception:
            pass

    def _message_clicked(self):
        self.clear_unread()

        try:
            self.window.showNormal()
            self.window.raise_()
            self.window.activateWindow()
        except Exception:
            pass

    def eventFilter(
        self,
        watched,
        event,
    ):
        if (
            watched is self.window
            and event.type()
            == QEvent.Type.WindowActivate
        ):
            self.clear_unread()

        return super().eventFilter(
            watched,
            event,
        )

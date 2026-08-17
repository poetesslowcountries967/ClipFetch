from __future__ import annotations

import sys
import traceback
import shutil

from PySide6.QtWidgets import (
    QApplication,
    QMessageBox,
)

from clipfetch.config.constants import APP_LOG_DIR
from clipfetch.config.metadata import APP_NAME, APP_VERSION
from clipfetch.persistence.config_manager import ConfigManager
from clipfetch.i18n import install_translation_filter, set_language


def cleanup_legacy_logs() -> None:
    """Remove logs persistentes criados por versões de desenvolvimento antigas."""

    try:
        if APP_LOG_DIR.exists():
            shutil.rmtree(APP_LOG_DIR)
    except OSError:
        # Falha de limpeza não impede o aplicativo de iniciar; a versão atual
        # simplesmente não volta a gravar conteúdo técnico nesse diretório.
        pass


def format_exception_details(
    exc_type,
    exc_value,
    exc_traceback,
) -> str:
    """
    Mantém o traceback somente em memória.

    O ClipFetch não grava detalhes técnicos ou relatórios de crash em disco.
    Fechar o aplicativo encerra esses dados de diagnóstico da sessão.
    """

    return "".join(
        traceback.format_exception(
            exc_type,
            exc_value,
            exc_traceback,
        )
    )


def show_crash_message(
    formatted: str,
) -> None:
    """
    Mostra ao usuário uma mensagem amigável em vez de fechar silenciosamente.
    """

    try:
        details = (
            formatted[-3500:]
            if formatted
            else "Erro desconhecido."
        )

        message = QMessageBox()

        message.setIcon(
            QMessageBox.Icon.Critical
        )

        message.setWindowTitle(
            f"{APP_NAME} encontrou um erro"
        )

        message.setText(
            (
                "O aplicativo encontrou um erro e não conseguiu continuar.\n\n"
                "Os detalhes abaixo existem somente nesta sessão e não "
                "foram gravados em arquivo."
            )
        )

        message.setDetailedText(
            details
        )

        message.exec()

    except Exception:
        pass


def exception_hook(
    exc_type,
    exc_value,
    exc_traceback,
):
    formatted = format_exception_details(
        exc_type,
        exc_value,
        exc_traceback,
    )

    show_crash_message(
        formatted
    )


def main() -> int:
    cleanup_legacy_logs()

    application = QApplication(
        sys.argv
    )

    application.setApplicationName(
        APP_NAME
    )

    application.setApplicationVersion(
        APP_VERSION
    )

    application.setOrganizationName(
        "Juliano Machado da Silva"
    )

    try:
        set_language(
            ConfigManager().load().get("language")
        )
    except Exception:
        set_language("pt-BR")

    install_translation_filter(application)

    sys.excepthook = (
        exception_hook
    )

    try:
        # Importamos a janela somente depois do QApplication existir.
        # Isso também deixa erros de import capturáveis pelo bloco abaixo.
        from clipfetch.ui.main_window import MainWindow

        window = MainWindow()
        window.show()

    except Exception:
        exc_type, exc_value, exc_traceback = (
            sys.exc_info()
        )

        formatted = format_exception_details(
            exc_type,
            exc_value,
            exc_traceback,
        )

        show_crash_message(
            formatted
        )

        return 1

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )

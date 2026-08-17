from __future__ import annotations

from pathlib import Path
import os
import shutil

from PySide6.QtCore import (
    QDateTime,
    QTime,
    Qt,
    QTimer,
    QUrl,
)
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QPalette,
    QGuiApplication,
    QPixmap,
)
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QTimeEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from clipfetch.ui.components import DropInput, QueueSummaryWidget, SpinArrowController
from clipfetch.ui.notifications import NotificationController
from clipfetch.ui.signals import AppSignals
from clipfetch.ui.styles import DARK_STYLE, LIGHT_STYLE, INTERACTIVE_DARK_PANEL_STYLE
from clipfetch.services.app_update_manager import AppUpdateManager
from clipfetch.config.metadata import (
    APP_NAME,
    APP_VERSION,
    AUTHOR_GITHUB_LABEL,
    AUTHOR_GITHUB_URL,
    UPDATE_REPOSITORY,
)
from clipfetch.infrastructure.path_utils import compact_user_path, expand_user_path
from clipfetch.infrastructure.bundled_tools import BundledTools
from clipfetch.persistence.config_manager import ConfigManager
from clipfetch.config.constants import (
    APP_SUPPORT_DIR,
    APP_LOG_DIR,
    APP_CACHE_DIR,
    APP_PREFERENCES_FILE,
    APPEARANCES,
    AUDIO_QUALITIES,
    AVAILABLE_FORMATS,
    BROWSERS,
    ORGANIZATION_TEMPLATES,
    PRESETS,
    RESOLUTIONS,
    SPEED_LIMITS,
    SUBTITLE_MODES,
)
from clipfetch.ui.dialogs import (
    FormatDetailsDialog,
    PlaylistSelectionDialog,
)
from clipfetch.download.manager import DownloadManager
from clipfetch.core.errors import AppError
from clipfetch.ui.error_dialog import FriendlyErrorDialog
from clipfetch.persistence.history_manager import HistoryManager
from clipfetch.services.metadata_service import MetadataService
from clipfetch.core.models import (
    AnalysisResult,
    DownloadResult,
    MediaItem,
)
from clipfetch.ui.supported_sites_dialog import SupportedSitesDialog
from clipfetch.services.thumbnail_service import ThumbnailService
from clipfetch.services.update_manager import UpdateManager
from clipfetch.i18n import (
    TranslatableStatusBar, available_languages, combo_value, date_display_format,
    datetime_display_format, install_translation_filter, set_combo_value,
    set_language, tr, translate_widget_tree,
)











class MainWindow(QMainWindow):
    """
    Janela principal do ClipFetch.
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            f"{APP_NAME} {APP_VERSION}"
        )
        # O conteúdo alto usa rolagem interna. Assim a janela pode ser
        # reduzida para caber em MacBooks com Dock visível/resolução escalada.
        self.setMinimumSize(
            760,
            500,
        )

        # -------------------------------------------------------------
        # Estado e serviços
        # -------------------------------------------------------------

        self.config_manager = ConfigManager()
        self.settings = (
            self.config_manager.load()
        )
        self.settings["language"] = set_language(
            self.settings.get("language")
        )
        install_translation_filter(
            QApplication.instance()
        )

        self.tools = BundledTools()
        self.history_manager = (
            HistoryManager()
        )
        self.metadata_service = (
            MetadataService(self.tools)
        )
        self.thumbnail_service = (
            ThumbnailService()
        )
        self.app_update_manager = (
            AppUpdateManager()
        )

        self.signals = AppSignals()

        self.queue: list[MediaItem] = []

        # Controladores visuais das setas ▲/▼.
        self._spin_arrow_controllers = []

        # queue_id -> placeholder já visível na fila. O ID evita que um
        # resultado antigo seja aplicado a uma nova análise do mesmo URL.
        self._analysis_placeholders: dict[str, MediaItem] = {}
        self._active_analysis_urls: set[str] = set()

        self.running = False

        # Quando o usuário pede para limpar a fila durante um download,
        # o ClipFetch cancela o lote primeiro e limpa a interface assim
        # que os workers realmente terminarem. Isso evita callbacks para
        # linhas que já não existem.
        self._clear_queue_after_downloads = False

        self.scheduled_timer = None

        self.notification_controller = None

        self._connect_signals()

        self.download_manager = (
            DownloadManager(
                tools=self.tools,
                progress_callback=(
                    self.signals.progress.emit
                ),
                log_callback=(
                    self.signals.log.emit
                ),
                result_callback=(
                    self.signals.download_result.emit
                ),
                history_manager=(
                    self.history_manager
                ),
            )
        )

        self.update_manager = (
            UpdateManager(
                tools=self.tools,
                log_callback=(
                    self.signals.log.emit
                ),
            )
        )

        self._build_ui()
        self._fit_window_to_available_screen()
        translate_widget_tree(self)

        # Inicializa contador e estado do botão com a fila vazia.
        self.refresh_queue()

        self._append_log(
            f"[APP] {APP_NAME} {APP_VERSION} iniciado."
        )
        self._append_log(
            "[APP] Interface carregada. Aguardando ações do usuário."
        )

        self.apply_appearance()
        self._apply_feature_visibility()

        self.notification_controller = NotificationController(
            self,
            tray_enabled=(
                not bool(
                    os.environ.get(
                        "CLIPFETCH_SMOKE_TEST"
                    )
                )
            ),
        )

        self.clipboard = (
            QGuiApplication.clipboard()
        )
        self.clipboard.dataChanged.connect(
            self._clipboard_changed
        )

        # Verifica as ferramentas somente depois da janela existir.
        # O caminho rápido não executa processos de versão.
        if not os.environ.get("CLIPFETCH_SMOKE_TEST"):
            QTimer.singleShot(
                150,
                self.validate_internal_tools,
            )

    # =================================================================
    # SIGNALS
    # =================================================================

    def _connect_signals(self):
        self.signals.analysis_started.connect(
            self._analysis_started
        )

        self.signals.analysis_finished.connect(
            self._analysis_finished
        )

        self.signals.enrich_finished.connect(
            self._enrich_finished
        )

        self.signals.thumbnail_finished.connect(
            self._thumbnail_finished
        )

        self.signals.progress.connect(
            self._apply_progress
        )

        self.signals.log.connect(
            self._append_log
        )

        self.signals.download_result.connect(
            self._download_result
        )

        self.signals.downloads_finished.connect(
            self._downloads_finished
        )

        self.signals.ytdlp_update_finished.connect(
            self._ytdlp_update_finished
        )

        self.signals.app_update_finished.connect(
            self._app_update_finished
        )

    # =================================================================
    # CONSTRUÇÃO DA INTERFACE
    # =================================================================

    def _install_visible_spin_arrows(
        self,
        *spin_boxes,
    ):
        for spin_box in spin_boxes:
            controller = SpinArrowController(
                spin_box
            )
            self._spin_arrow_controllers.append(
                controller
            )

    def _fit_window_to_available_screen(self):
        """
        Faz o tamanho inicial respeitar a área útil real do monitor.

        No macOS, availableGeometry() desconta Menu Bar e Dock.
        """

        screen = (
            self.screen()
            or QGuiApplication.primaryScreen()
        )

        if screen is None:
            self.resize(
                1100,
                720,
            )
            return

        available = screen.availableGeometry()
        margin = 24

        safe_min_width = min(
            self.minimumWidth(),
            max(
                620,
                available.width() - 80,
            ),
        )
        safe_min_height = min(
            self.minimumHeight(),
            max(
                420,
                available.height() - 80,
            ),
        )

        self.setMinimumSize(
            safe_min_width,
            safe_min_height,
        )

        target_width = min(
            1180,
            max(
                safe_min_width,
                available.width()
                - (margin * 2),
            ),
        )
        target_height = min(
            800,
            max(
                safe_min_height,
                available.height()
                - (margin * 2),
            ),
        )

        self.resize(
            min(
                target_width,
                available.width(),
            ),
            min(
                target_height,
                available.height(),
            ),
        )

        frame = self.frameGeometry()
        frame.moveCenter(
            available.center()
        )
        self.move(
            frame.topLeft()
        )

    def _scrollable_page_layout(
        self,
        tab,
        content_object_name,
    ):
        """
        Retorna o layout de uma página com rolagem própria.

        O QScrollArea impede que o sizeHint do conteúdo force a janela
        principal a ficar maior do que a tela.
        """

        outer = QVBoxLayout(tab)
        outer.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        outer.setSpacing(0)

        scroll_area = QScrollArea(tab)
        scroll_area.setObjectName(
            "responsivePageScroll"
        )
        scroll_area.setWidgetResizable(
            True
        )
        scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        content = QWidget()
        content.setObjectName(
            content_object_name
        )

        scroll_area.setWidget(
            content
        )
        outer.addWidget(
            scroll_area
        )

        return (
            QVBoxLayout(content),
            scroll_area,
        )

    def _build_ui(self):
        self.setStatusBar(
            TranslatableStatusBar(self)
        )

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.downloads_tab = QWidget()
        self.downloads_tab.setObjectName("downloadsTab")

        self.history_tab = QWidget()
        self.history_tab.setObjectName("historyTab")

        self.preferences_tab = QWidget()
        self.preferences_tab.setObjectName("preferencesTab")

        self.settings_tab = QWidget()
        self.settings_tab.setObjectName("settingsTab")

        self.tabs.addTab(self.downloads_tab, "Downloads")
        self.tabs.addTab(self.history_tab, "Histórico")
        self.tabs.addTab(self.preferences_tab, "Preferências")
        self.tabs.addTab(self.settings_tab, "Configurações")

        self._build_downloads_tab()
        self._build_history_tab()
        self._build_preferences_tab()
        self._build_settings_tab()

    def _build_downloads_tab(self):
        """Fluxo principal: adicionar links, fila visual e execução rápida."""

        (
            root,
            self.downloads_scroll_area,
        ) = self._scrollable_page_layout(
            self.downloads_tab,
            "downloadsScrollContent",
        )
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        # -------------------------------------------------------------
        # 1. Links
        # -------------------------------------------------------------
        input_group = QGroupBox("1. Adicionar e analisar links")
        input_group.setObjectName("interactiveDarkPanel")
        input_group.setStyleSheet(INTERACTIVE_DARK_PANEL_STYLE)
        input_layout = QVBoxLayout(input_group)

        hint = QLabel(
            "Cole um ou vários links, um por linha. "
            "Você também pode arrastar um arquivo .txt."
        )
        hint.setWordWrap(True)
        input_layout.addWidget(hint)

        self.links_input = DropInput()
        self.links_input.setPlaceholderText("https://...\\nhttps://...")
        self.links_input.setMaximumHeight(86)
        input_layout.addWidget(self.links_input)

        input_actions = QHBoxLayout()
        paste_button = QPushButton("Colar")
        paste_button.clicked.connect(self.paste_clipboard)
        analyze_button = QPushButton("Analisar e adicionar")
        analyze_button.clicked.connect(self.analyze_links)
        sites_button = QPushButton("Fontes suportadas")
        sites_button.clicked.connect(self.show_supported_sites)

        for button in (paste_button, analyze_button, sites_button):
            input_actions.addWidget(button)
        input_actions.addStretch()
        input_layout.addLayout(input_actions)
        root.addWidget(input_group)

        # -------------------------------------------------------------
        # 2. Fila + preview
        # -------------------------------------------------------------
        content_splitter = QSplitter(Qt.Orientation.Horizontal)

        queue_group = QGroupBox("2. Fila")
        queue_group.setObjectName("interactiveDarkPanel")
        queue_group.setStyleSheet(INTERACTIVE_DARK_PANEL_STYLE)
        queue_layout = QVBoxLayout(queue_group)

        queue_header = QHBoxLayout()
        self.queue_count_label = QLabel("0 itens")
        queue_header.addWidget(self.queue_count_label)
        queue_header.addStretch()
        queue_layout.addLayout(queue_header)

        # A fila deixa de ser uma planilha de nove colunas. A informação do item
        # fica agrupada sob o título; progresso e status têm colunas estáveis.
        self.queue_table = QTableWidget(0, 3)
        self.queue_table.setHorizontalHeaderLabels(
            ["Item", "Progresso", "Status"]
        )
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.setShowGrid(False)
        self.queue_table.setAlternatingRowColors(False)
        self.queue_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.queue_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.queue_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.queue_table.setColumnWidth(1, 190)
        self.queue_table.setColumnWidth(2, 155)

        self.queue_table.itemSelectionChanged.connect(self.update_preview)
        self.queue_table.itemSelectionChanged.connect(
            self._update_queue_action_buttons
        )
        queue_layout.addWidget(self.queue_table, 1)

        queue_actions = QHBoxLayout()
        self.remove_button = QPushButton("Remover")
        self.remove_button.setObjectName("removeButton")
        self.remove_button.setEnabled(False)
        self.remove_button.clicked.connect(self.remove_selected)

        up_button = QPushButton("↑")
        up_button.setToolTip("Mover para cima")
        up_button.clicked.connect(lambda: self.move_selected(-1))

        down_button = QPushButton("↓")
        down_button.setToolTip("Mover para baixo")
        down_button.clicked.connect(lambda: self.move_selected(1))

        self.retry_button = QPushButton("Tentar erro novamente")
        self.retry_button.clicked.connect(self.retry_failed)
        self.retry_button.hide()

        self.clear_queue_button = QPushButton(
            "Limpar fila"
        )
        self.clear_queue_button.clicked.connect(
            self.clear_queue
        )

        for button in (
            self.remove_button,
            up_button,
            down_button,
            self.retry_button,
        ):
            queue_actions.addWidget(button)

        queue_actions.addStretch()
        queue_actions.addWidget(
            self.clear_queue_button
        )
        queue_layout.addLayout(queue_actions)
        content_splitter.addWidget(queue_group)

        preview_group = QGroupBox("Pré-visualização e análise")
        preview_group.setObjectName("interactiveDarkPanel")
        preview_group.setStyleSheet(INTERACTIVE_DARK_PANEL_STYLE)
        preview_group.setMinimumWidth(340)
        preview_layout = QVBoxLayout(preview_group)

        self.thumbnail_label = QLabel("Selecione um item da fila")
        self.thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumbnail_label.setMinimumSize(320, 176)
        self.thumbnail_label.setWordWrap(True)
        preview_layout.addWidget(self.thumbnail_label)

        note = QLabel(
            "A imagem é uma prévia pequena e leve. "
            "Ela não altera a qualidade do download final."
        )
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 11px;")
        preview_layout.addWidget(note)

        self.preview_title = QLabel("")
        self.preview_title.setWordWrap(True)
        self.preview_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        preview_layout.addWidget(self.preview_title)

        self.preview_meta = QLabel("")
        self.preview_meta.setWordWrap(True)
        preview_layout.addWidget(self.preview_meta)

        # Formato e qualidade são editados no item selecionado, não em cada
        # linha da fila. Isso mantém a lista compacta e visualmente estável.
        preview_options = QHBoxLayout()
        preview_options.addWidget(QLabel("Formato:"))
        self.preview_format_combo = QComboBox()
        self.preview_format_combo.addItems(AVAILABLE_FORMATS)
        self.preview_format_combo.setMaximumWidth(120)
        self.preview_format_combo.currentIndexChanged.connect(
            self._preview_format_changed
        )
        preview_options.addWidget(self.preview_format_combo)

        preview_options.addWidget(QLabel("Resolução:"))
        self.preview_resolution_combo = QComboBox()
        self.preview_resolution_combo.addItems(RESOLUTIONS)
        self.preview_resolution_combo.setMaximumWidth(190)
        self.preview_resolution_combo.currentIndexChanged.connect(
            self._preview_resolution_changed
        )
        preview_options.addWidget(self.preview_resolution_combo)
        preview_options.addStretch()
        preview_layout.addLayout(preview_options)

        self.preview_dev_info = QLabel("")
        self.preview_dev_info.setObjectName("developerInfoLabel")
        self.preview_dev_info.setWordWrap(True)
        self.preview_dev_info.hide()
        preview_layout.addWidget(self.preview_dev_info)

        self.format_details_button = QPushButton("Ver formatos disponíveis")
        self.format_details_button.setEnabled(False)
        self.format_details_button.clicked.connect(self.show_format_details)
        preview_layout.addWidget(self.format_details_button)
        preview_layout.addStretch()

        content_splitter.addWidget(preview_group)
        content_splitter.setStretchFactor(0, 2)
        content_splitter.setStretchFactor(1, 1)
        content_splitter.setSizes([800, 390])
        root.addWidget(content_splitter, 1)

        # -------------------------------------------------------------
        # 3. Execução rápida
        # -------------------------------------------------------------
        quick_group = QGroupBox("3. Opções e download")
        quick_group.setObjectName("interactiveDarkPanel")
        quick_group.setStyleSheet(INTERACTIVE_DARK_PANEL_STYLE)
        quick_root = QVBoxLayout(quick_group)
        quick_root.setSpacing(8)

        options = QHBoxLayout()
        options.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(list(PRESETS))
        self.preset_combo.setMaximumWidth(190)
        self.preset_combo.currentIndexChanged.connect(
            lambda _index: self.apply_preset(combo_value(self.preset_combo))
        )
        options.addWidget(self.preset_combo)

        options.addSpacing(10)
        options.addWidget(QLabel("Pasta:"))
        self.folder_edit = QLineEdit(
            compact_user_path(self.settings["download_folder"])
        )
        options.addWidget(self.folder_edit, 1)

        choose = QPushButton("Escolher...")
        choose.clicked.connect(self.choose_folder)
        options.addWidget(choose)
        quick_root.addLayout(options)

        actions = QHBoxLayout()
        self.schedule_checkbox = QCheckBox("Agendar")
        self.schedule_checkbox.toggled.connect(self._schedule_toggled)
        actions.addWidget(self.schedule_checkbox)

        initial_schedule = QDateTime.currentDateTime().addSecs(3600)

        actions.addWidget(QLabel("Data:"))
        self.schedule_date = QDateEdit(initial_schedule.date())
        self.schedule_date.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.UpDownArrows
        )
        self.schedule_date.setCalendarPopup(True)
        self.schedule_date.setDisplayFormat(date_display_format())
        self.schedule_date.setMinimumDate(QDateTime.currentDateTime().date())
        self.schedule_date.setMinimumWidth(125)
        self.schedule_date.setEnabled(False)
        self.schedule_date.dateChanged.connect(
            self._update_schedule_constraints
        )
        actions.addWidget(self.schedule_date)

        actions.addWidget(QLabel("Hora:"))
        self.schedule_time = QTimeEdit(initial_schedule.time())
        self.schedule_time.setDisplayFormat("HH:mm")
        self.schedule_time.setMinimumWidth(92)
        self.schedule_time.setEnabled(False)
        self._install_visible_spin_arrows(
            self.schedule_time
        )
        actions.addWidget(self.schedule_time)

        actions.addStretch()

        self.pause_button = QPushButton("Pausar")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)

        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_downloads)

        self.download_button = QPushButton("Baixar fila")
        self.download_button.setObjectName("downloadButton")
        self.download_button.clicked.connect(self.start_or_schedule)

        actions.addWidget(self.pause_button)
        actions.addWidget(self.cancel_button)
        actions.addWidget(self.download_button)
        quick_root.addLayout(actions)
        root.addWidget(quick_group)

        # O botão existe por padrão, mas o painel sempre inicia fechado. A opção
        # Configurações > Mostrar botão... pode ocultar somente o botão; o buffer
        # em memória continua recebendo logs durante toda a sessão.
        self.log_toggle = QPushButton("Mostrar detalhes técnicos")
        self.log_toggle.setCheckable(True)
        self.log_toggle.setChecked(False)
        self.log_toggle.toggled.connect(self._toggle_log)
        root.addWidget(self.log_toggle)

        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        self.log_text.document().setMaximumBlockCount(5000)
        self.log_text.hide()
        root.addWidget(self.log_text)
    def _build_history_tab(self):
        root = QVBoxLayout(
            self.history_tab
        )

        header = QHBoxLayout()

        header.addWidget(
            QLabel("<b>Downloads recentes</b>")
        )
        header.addStretch()

        refresh_button = QPushButton(
            "Atualizar"
        )
        refresh_button.clicked.connect(
            self.refresh_history
        )

        open_file_button = QPushButton(
            "Abrir arquivo"
        )
        open_file_button.clicked.connect(
            self.open_history_file
        )

        open_folder_button = QPushButton(
            "Abrir pasta"
        )
        open_folder_button.clicked.connect(
            self.open_history_folder
        )

        again_button = QPushButton(
            "Baixar novamente"
        )
        again_button.clicked.connect(
            self.history_download_again
        )

        export_sources_button = QPushButton(
            "Exportar fontes"
        )
        export_sources_button.setToolTip(
            (
                "Copia os links das linhas selecionadas. "
                "Links repetidos são copiados apenas uma vez."
            )
        )
        export_sources_button.clicked.connect(
            self.export_history_sources
        )

        clear_button = QPushButton(
            "Limpar histórico"
        )
        clear_button.clicked.connect(
            self.clear_history
        )

        root.addLayout(header)

        history_actions = QGridLayout()
        history_actions.setHorizontalSpacing(8)
        history_actions.setVerticalSpacing(8)
        history_actions.addWidget(refresh_button, 0, 0)
        history_actions.addWidget(open_file_button, 0, 1)
        history_actions.addWidget(open_folder_button, 0, 2)
        history_actions.addWidget(again_button, 1, 0)
        history_actions.addWidget(export_sources_button, 1, 1)
        history_actions.addWidget(clear_button, 1, 2)
        root.addLayout(history_actions)

        self.history_table = QTableWidget(
            0,
            9,
        )
        self.history_table.setObjectName(
            "historyDarkTable"
        )
        self.history_table.setAlternatingRowColors(
            True
        )

        self.history_table.setHorizontalHeaderLabels(
            [
                "ID",
                "Data",
                "Título",
                "Site",
                "Fonte",
                "Formato",
                "Resolução",
                "Status",
                "Arquivo",
            ]
        )

        self.history_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.history_table.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )

        self.history_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.history_table.verticalHeader().setVisible(
            False
        )

        table_header = (
            self.history_table.horizontalHeader()
        )

        table_header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )

        table_header.setSectionResizeMode(
            4,
            QHeaderView.ResizeMode.Stretch,
        )

        for column in (
            0, 1, 3, 5, 6, 7, 8
        ):
            table_header.setSectionResizeMode(
                column,
                QHeaderView.ResizeMode.ResizeToContents,
            )

        root.addWidget(
            self.history_table,
            1,
        )

        self.refresh_history()

    def _build_preferences_tab(self):
        (
            root,
            self.preferences_scroll_area,
        ) = self._scrollable_page_layout(
            self.preferences_tab,
            "preferencesScrollContent",
        )
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        columns = QHBoxLayout()
        columns.setSpacing(12)

        # -------------------------------------------------------------
        # Downloads
        # -------------------------------------------------------------
        download_group = QGroupBox("Downloads")
        download_form = QFormLayout(download_group)
        download_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        download_form.setHorizontalSpacing(12)
        download_form.setVerticalSpacing(8)

        self.pref_format = QComboBox()
        self.pref_format.addItems(AVAILABLE_FORMATS)
        self.pref_format.setCurrentText(self.settings["format"])

        self.pref_resolution = QComboBox()
        self.pref_resolution.addItems(RESOLUTIONS)
        self.pref_resolution.setCurrentText(self.settings["resolution"])

        self.pref_concurrency = QSpinBox()
        self.pref_concurrency.setRange(1, 6)
        self.pref_concurrency.setValue(
            self.settings["concurrency"]
        )
        self._install_visible_spin_arrows(
            self.pref_concurrency
        )

        self.pref_speed = QComboBox()
        self.pref_speed.addItems(SPEED_LIMITS)
        self.pref_speed.setCurrentText(self.settings["speed_limit"])

        self.pref_audio_quality = QComboBox()
        self.pref_audio_quality.addItems(AUDIO_QUALITIES)
        self.pref_audio_quality.setCurrentText(self.settings["audio_quality"])

        self.pref_organization = QComboBox()
        self.pref_organization.addItems(list(ORGANIZATION_TEMPLATES))
        self.pref_organization.setCurrentText(self.settings["organization"])

        for widget in (
            self.pref_format,
            self.pref_resolution,
            self.pref_speed,
            self.pref_audio_quality,
            self.pref_organization,
        ):
            widget.setMinimumWidth(190)
            widget.setMaximumWidth(250)

        self.pref_concurrency.setMinimumWidth(90)
        self.pref_concurrency.setMaximumWidth(110)

        self.pref_duplicates = QCheckBox(
            "Não baixar novamente itens já concluídos"
        )
        self.pref_duplicates.setChecked(self.settings["prevent_duplicates"])

        download_form.addRow("Formato padrão:", self.pref_format)
        download_form.addRow("Resolução padrão:", self.pref_resolution)
        download_form.addRow("Downloads simultâneos:", self.pref_concurrency)
        download_form.addRow("Limite de velocidade:", self.pref_speed)
        download_form.addRow("Qualidade do áudio:", self.pref_audio_quality)
        download_form.addRow("Organização:", self.pref_organization)
        download_form.addRow("", self.pref_duplicates)
        columns.addWidget(download_group, 1)

        # -------------------------------------------------------------
        # Legendas e metadados
        # -------------------------------------------------------------
        metadata_group = QGroupBox("Legendas e metadados")
        metadata_form = QFormLayout(metadata_group)
        metadata_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        metadata_form.setHorizontalSpacing(12)
        metadata_form.setVerticalSpacing(8)

        self.pref_subtitles = QComboBox()
        self.pref_subtitles.addItems(SUBTITLE_MODES)
        self.pref_subtitles.setCurrentText(self.settings["subtitle_mode"])
        self.pref_subtitles.setMinimumWidth(210)
        self.pref_subtitles.setMaximumWidth(260)

        self.pref_sub_langs = QLineEdit(self.settings["subtitle_languages"])
        self.pref_sub_langs.setPlaceholderText("Ex.: pt.*,en.*")
        self.pref_sub_langs.setMaximumWidth(260)

        self.pref_embed_subtitles = QCheckBox("Incorporar legendas")
        self.pref_embed_subtitles.setChecked(self.settings["embed_subtitles"])
        self.pref_thumbnail = QCheckBox("Incorporar thumbnail/capa")
        self.pref_thumbnail.setChecked(self.settings["embed_thumbnail"])
        self.pref_metadata = QCheckBox("Incorporar metadados")
        self.pref_metadata.setChecked(self.settings["embed_metadata"])
        self.pref_chapters = QCheckBox("Incorporar capítulos")
        self.pref_chapters.setChecked(self.settings["embed_chapters"])

        metadata_form.addRow("Legendas:", self.pref_subtitles)
        metadata_form.addRow("Idiomas:", self.pref_sub_langs)
        metadata_form.addRow("", self.pref_embed_subtitles)
        metadata_form.addRow("", self.pref_thumbnail)
        metadata_form.addRow("", self.pref_metadata)
        metadata_form.addRow("", self.pref_chapters)
        columns.addWidget(metadata_group, 1)

        root.addLayout(columns)

        # -------------------------------------------------------------
        # Aplicativo: só preferências do usuário. Ferramentas/sobre vão para
        # Configurações.
        # -------------------------------------------------------------
        app_group = QGroupBox("Aplicativo")
        app_layout = QGridLayout(app_group)
        app_layout.setHorizontalSpacing(14)
        app_layout.setVerticalSpacing(8)

        self.pref_clipboard = QCheckBox("Detectar links copiados")
        self.pref_clipboard.setChecked(self.settings["clipboard_detection"])

        self.pref_notifications = QCheckBox("Notificar quando a fila terminar")
        self.pref_notifications.setChecked(self.settings["notifications"])

        self.pref_appearance = QComboBox()
        self.pref_appearance.addItems(APPEARANCES)
        self.pref_appearance.setCurrentText(self.settings["appearance"])
        self.pref_appearance.setMaximumWidth(150)
        self.pref_appearance.currentIndexChanged.connect(
            self._appearance_changed
        )

        self.pref_language = QComboBox()
        for language in available_languages():
            self.pref_language.addItem(language.native_name, language.code)
        self.pref_language.setProperty("_i18n_skip_combo", True)
        set_combo_value(self.pref_language, self.settings["language"])
        self.pref_language.setMaximumWidth(210)
        self.pref_language.currentIndexChanged.connect(
            self._language_changed
        )

        app_layout.addWidget(self.pref_clipboard, 0, 0, 1, 2)
        app_layout.addWidget(self.pref_notifications, 1, 0, 1, 2)
        app_layout.addWidget(QLabel("Aparência:"), 2, 0)
        app_layout.addWidget(self.pref_appearance, 2, 1)
        app_layout.addWidget(QLabel("Idioma:"), 3, 0)
        app_layout.addWidget(self.pref_language, 3, 1)
        app_layout.setColumnStretch(2, 1)
        root.addWidget(app_group)

        # -------------------------------------------------------------
        # Cookies/autenticação: acessível a usuário comum, mas fora do caminho
        # principal. Necessário para conteúdo privado/login.
        # -------------------------------------------------------------
        self.advanced_toggle = QPushButton("Mostrar opções avançadas")
        self.advanced_toggle.setCheckable(True)
        self.advanced_toggle.toggled.connect(self._advanced_preferences_toggled)
        self.advanced_toggle.setMaximumWidth(230)
        root.addWidget(self.advanced_toggle, 0, Qt.AlignmentFlag.AlignLeft)

        self.advanced_preferences = QGroupBox("Autenticação e opções avançadas")
        advanced_form = QFormLayout(self.advanced_preferences)
        advanced_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint
        )
        self.pref_browser = QComboBox()
        self.pref_browser.addItems(BROWSERS)
        self.pref_browser.setCurrentText(self.settings["browser_cookies"])
        self.pref_browser.setMaximumWidth(220)
        advanced_form.addRow("Cookies do navegador:", self.pref_browser)
        self.advanced_preferences.hide()
        root.addWidget(self.advanced_preferences)

        save_button = QPushButton("Salvar preferências")
        save_button.setMaximumWidth(180)
        save_button.clicked.connect(self.save_preferences)
        root.addWidget(save_button, 0, Qt.AlignmentFlag.AlignLeft)
        root.addStretch()

    # =================================================================
    # IDIOMA / RESET / APARÊNCIA / NOTIFICAÇÕES / CLIPBOARD
    # =================================================================

    def _build_settings_tab(self):
        (
            root,
            self.settings_scroll_area,
        ) = self._scrollable_page_layout(
            self.settings_tab,
            "settingsScrollContent",
        )
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(10)

        # Atualizações
        updates_group = QGroupBox("Atualizações")
        updates_layout = QHBoxLayout(updates_group)

        update_ytdlp_button = QPushButton("Atualizar yt-dlp")
        update_ytdlp_button.setMaximumWidth(190)
        update_ytdlp_button.clicked.connect(self.update_ytdlp)

        update_app_button = QPushButton("Verificar atualização do app")
        update_app_button.setMaximumWidth(230)
        update_app_button.clicked.connect(self.check_app_update)

        updates_layout.addWidget(update_ytdlp_button)
        updates_layout.addWidget(update_app_button)
        updates_layout.addStretch()
        root.addWidget(updates_group)

        # Interface técnica
        interface_group = QGroupBox("Interface técnica")
        interface_layout = QVBoxLayout(interface_group)

        self.show_technical_button_check = QCheckBox(
            "Mostrar botão de detalhes técnicos em Downloads"
        )
        self.show_technical_button_check.setChecked(
            bool(self.settings.get("show_technical_button", True))
        )
        self.show_technical_button_check.toggled.connect(
            self._technical_button_visibility_changed
        )
        interface_layout.addWidget(self.show_technical_button_check)

        self.developer_mode_check = QCheckBox("Modo desenvolvedor")
        self.developer_mode_check.setChecked(
            bool(self.settings.get("developer_mode", False))
        )
        self.developer_mode_check.toggled.connect(
            self._developer_mode_changed
        )
        interface_layout.addWidget(self.developer_mode_check)

        developer_hint = QLabel(
            "O modo desenvolvedor libera informações de runtime e ferramentas "
            "de manutenção. Ele fica desativado por padrão."
        )
        developer_hint.setWordWrap(True)
        interface_layout.addWidget(developer_hint)
        root.addWidget(interface_group)

        # Diagnóstico e manutenção
        maintenance_group = QGroupBox("Diagnóstico e manutenção")
        maintenance_layout = QHBoxLayout(maintenance_group)

        diagnostic_button = QPushButton("Copiar diagnóstico")
        diagnostic_button.setMaximumWidth(180)
        diagnostic_button.clicked.connect(self.copy_diagnostic)
        maintenance_layout.addWidget(diagnostic_button)

        self.tools_button = QPushButton("Ferramentas internas")
        self.tools_button.setMaximumWidth(190)
        self.tools_button.clicked.connect(self.show_tools)
        maintenance_layout.addWidget(self.tools_button)
        maintenance_layout.addStretch()
        root.addWidget(maintenance_group)

        # Informação para forks só existe no modo desenvolvedor.
        self.developer_repository_note = QLabel(
            "As atualizações do ClipFetch usam GitHub Releases do repositório "
            f"oficial: {UPDATE_REPOSITORY}. Quem distribui um fork deve alterar "
            "UPDATE_REPOSITORY em clipfetch/config/metadata.py."
        )
        self.developer_repository_note.setWordWrap(True)
        root.addWidget(self.developer_repository_note)

        # Redefinição
        reset_group = QGroupBox("Redefinir aplicativo")
        reset_layout = QVBoxLayout(reset_group)
        reset_note = QLabel(
            "Remove configurações, histórico, cache e outros dados persistentes "
            "do ClipFetch. Os vídeos e áudios baixados não são apagados."
        )
        reset_note.setWordWrap(True)
        reset_layout.addWidget(reset_note)

        self.reset_app_button = QPushButton(
            "Apagar dados do aplicativo e restaurar padrões"
        )
        self.reset_app_button.setMaximumWidth(330)
        self.reset_app_button.clicked.connect(self.reset_application_data)
        reset_layout.addWidget(
            self.reset_app_button,
            0,
            Qt.AlignmentFlag.AlignLeft,
        )
        root.addWidget(reset_group)

        # Sobre
        about_group = QGroupBox("Sobre")
        about_layout = QVBoxLayout(about_group)
        about = QLabel(
            "Made by Juliano Machado da Silva · "
            f'<a href="{AUTHOR_GITHUB_URL}">GitHub: {AUTHOR_GITHUB_LABEL}</a>'
        )
        about.setOpenExternalLinks(True)
        about.setTextFormat(Qt.TextFormat.RichText)
        about_layout.addWidget(about)
        root.addWidget(about_group)
        root.addStretch()

    def _advanced_preferences_toggled(self, visible):
        self.advanced_preferences.setVisible(bool(visible))
        self.advanced_toggle.setText(
            tr("Ocultar opções avançadas" if visible else "Mostrar opções avançadas")
        )


    def _technical_button_visibility_changed(self, visible):
        self.settings["show_technical_button"] = bool(visible)
        self.config_manager.save(self.settings)
        self._apply_feature_visibility()


    def _developer_mode_changed(self, enabled):
        self.settings["developer_mode"] = bool(enabled)
        self.config_manager.save(self.settings)
        self._apply_feature_visibility()
        self._update_preview_developer_info()


    def _apply_feature_visibility(self):
        show_technical = bool(
            self.settings.get("show_technical_button", True)
        )
        developer_mode = bool(
            self.settings.get("developer_mode", False)
        )

        if hasattr(self, "log_toggle"):
            self.log_toggle.setVisible(show_technical)
            if not show_technical:
                self.log_toggle.setChecked(False)
                self.log_text.hide()

        if hasattr(self, "tools_button"):
            self.tools_button.setVisible(developer_mode)

        if hasattr(self, "developer_repository_note"):
            self.developer_repository_note.setVisible(developer_mode)

        if hasattr(self, "preview_dev_info"):
            self.preview_dev_info.setVisible(developer_mode)


    def _preview_format_changed(self, _index=None):
        row = self.queue_table.currentRow()
        if not (0 <= row < len(self.queue)):
            return
        item = self.queue[row]
        if item.analysis_state != "ready" or self.running:
            return
        item.output_format = combo_value(self.preview_format_combo)
        self._render_queue_row(row, item)


    def _preview_resolution_changed(self, _index=None):
        row = self.queue_table.currentRow()
        if not (0 <= row < len(self.queue)):
            return
        item = self.queue[row]
        if item.analysis_state != "ready" or self.running:
            return
        item.resolution = combo_value(self.preview_resolution_combo)
        item.manual_format_selector = ""
        self._render_queue_row(row, item)


    def _update_preview_developer_info(self, item=None):
        if not hasattr(self, "preview_dev_info"):
            return

        if not self.settings.get("developer_mode", False):
            self.preview_dev_info.clear()
            self.preview_dev_info.hide()
            return

        if item is None:
            row = self.queue_table.currentRow()
            if not (0 <= row < len(self.queue)):
                self.preview_dev_info.clear()
                self.preview_dev_info.show()
                return
            item = self.queue[row]

        values = [
            tr("Extractor: ") + (item.extractor_key or item.extractor or "—"),
            tr("ID da mídia: ") + (item.media_id or "—"),
        ]
        if item.speed:
            values.append(tr("Velocidade: ") + item.speed)
        if item.eta:
            values.append(tr("ETA: ") + item.eta)

        self.preview_dev_info.setText(" · ".join(values))
        self.preview_dev_info.show()

    def _appearance_changed(self, _index=None):
        """Aplica Claro/Escuro imediatamente, sem observar o macOS."""

        value = combo_value(self.pref_appearance)
        if value not in ("Claro", "Escuro"):
            return

        self.settings["appearance"] = value
        self.apply_appearance()

        # Aparência funciona como preferência imediata. Salvar aqui não
        # captura alterações ainda não confirmadas dos demais controles,
        # porque usamos apenas self.settings já consolidado.
        self.config_manager.save(self.settings)

    def _language_changed(self, _index=None):
        code = combo_value(self.pref_language)
        if not code:
            return

        self.settings["language"] = set_language(code)
        self.config_manager.save(self.settings)
        translate_widget_tree(self)
        self.schedule_date.setDisplayFormat(date_display_format())
        self.refresh_queue()
        self.refresh_history()
        self.update_preview()
        self._advanced_preferences_toggled(
            self.advanced_toggle.isChecked()
        )
        self._toggle_log(self.log_toggle.isChecked())
        self._apply_feature_visibility()
        self.statusBar().showMessage(tr("Idioma alterado."), 3500)

    @staticmethod
    def _persistent_paths_for_reset():
        return [
            APP_SUPPORT_DIR,
            APP_LOG_DIR,
            APP_CACHE_DIR,
            APP_PREFERENCES_FILE,
                                        ]

    def reset_application_data(self):
        if self.running or self._active_analysis_urls:
            QMessageBox.warning(
                self,
                "Não é possível redefinir agora",
                "Aguarde as análises e downloads terminarem antes de apagar os dados do aplicativo.",
            )
            return

        answer = QMessageBox.question(
            self,
            "Redefinir todos os dados?",
            (
                "Isso removerá as preferências, histórico, download-archive, "
                "cache de thumbnails, catálogo de fontes, ferramentas atualizadas "
                "em runtime e eventuais dados legados do ClipFetch.\\n\\n"
                "Os vídeos e áudios baixados NÃO serão apagados.\\n\\n"
                "Os detalhes técnicos da sessão atual já existem somente em "
                "memória e desaparecem ao fechar o aplicativo.\\n\\n"
                "O aplicativo será fechado após a limpeza. Deseja continuar?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        if self.scheduled_timer and self.scheduled_timer.isActive():
            self.scheduled_timer.stop()

        errors = []
        for path in self._persistent_paths_for_reset():
            try:
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            except OSError as error:
                errors.append(f"{path}: {error}")

        if errors:
            QMessageBox.critical(
                self,
                "Falha ao redefinir",
                "Não foi possível remover todos os dados persistentes:\\n"
                + "\\n".join(errors),
            )
            return

        QMessageBox.information(
            self,
            "Dados do aplicativo removidos",
            (
                "As configurações, histórico, cache e arquivos persistentes do "
                "ClipFetch foram removidos. Seus downloads foram preservados.\\n\\n"
                "Abra o aplicativo novamente para iniciar com os padrões."
            ),
        )
        QTimer.singleShot(0, QApplication.instance().quit)

    def apply_appearance(self):
        app = QApplication.instance()
        appearance = self.settings.get("appearance", "Escuro")
        self.settings["appearance"] = (
            appearance
            if appearance in ("Claro", "Escuro")
            else "Escuro"
        )

        try:
            app.setStyle("Fusion")
        except Exception:
            pass

        palette = QPalette()

        if self.settings["appearance"] == "Claro":
            palette.setColor(QPalette.ColorRole.Window, QColor("#F2F3F5"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#202328"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#F7F8F9"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#202328"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#202328"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#34C759"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#202328"))
            stylesheet = LIGHT_STYLE
        else:
            palette.setColor(QPalette.ColorRole.Window, QColor("#23272D"))
            palette.setColor(QPalette.ColorRole.WindowText, QColor("#EDF0F3"))
            palette.setColor(QPalette.ColorRole.Base, QColor("#383E46"))
            palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#2D3239"))
            palette.setColor(QPalette.ColorRole.Text, QColor("#F0F2F4"))
            palette.setColor(QPalette.ColorRole.Button, QColor("#3C424A"))
            palette.setColor(QPalette.ColorRole.ButtonText, QColor("#F0F2F4"))
            palette.setColor(QPalette.ColorRole.Highlight, QColor("#34C759"))
            palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#FFFFFF"))
            palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#343A42"))
            palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#FFFFFF"))
            stylesheet = DARK_STYLE

        app.setPalette(palette)
        app.setStyleSheet(stylesheet)

        for panel in self.findChildren(QGroupBox, "interactiveDarkPanel"):
            panel.setStyleSheet(INTERACTIVE_DARK_PANEL_STYLE)

    def _clipboard_changed(self):
        if not self.settings.get(
            "clipboard_detection",
            False,
        ):
            return

        text = (
            self.clipboard.text().strip()
        )

        if not (
            text.startswith("https://")
            or text.startswith("http://")
        ):
            return

        current = (
            self.links_input.toPlainText()
        )

        if text in current:
            return

        self.links_input.setPlainText(
            f"{current.strip()}\n{text}".strip()
        )

        self.statusBar().showMessage(
            "Link copiado detectado.",
            4000,
        )

    # =================================================================
    # FERRAMENTAS INTERNAS
    # =================================================================

    def validate_internal_tools(self):
        try:
            ready = self.tools.is_ready()
        except Exception as error:
            ready = False
            self._append_log(
                f"Erro ao verificar ferramentas: {error}"
            )

        if ready:
            self._append_log(
                "[FERRAMENTAS] Componentes internos encontrados e prontos."
            )
            # Nada permanente no rodapé. O log em memória continua disponível.
            return

        self._append_log(
            "[FERRAMENTAS][ERRO] Uma ou mais ferramentas internas falharam."
        )
        self.download_button.setEnabled(False)
        QMessageBox.critical(
            self,
            "Aplicativo incompleto",
            (
                "Uma ou mais ferramentas internas não foram encontradas.\\n\\n"
                "Reinstale o aplicativo a partir do DMG original.\\n\\n"
                + self.tools.diagnostic_text(include_versions=False)
            ),
        )

    # =================================================================
    # LINKS / ANÁLISE
    # =================================================================

    def paste_clipboard(self):
        text = (
            QGuiApplication.clipboard().text()
        )

        if not text.strip():
            return

        current = (
            self.links_input.toPlainText().strip()
        )

        self.links_input.setPlainText(
            f"{current}\n{text.strip()}".strip()
        )

    def _input_urls(self):
        return list(
            dict.fromkeys(
                line.strip()
                for line
                in self.links_input.toPlainText().splitlines()
                if line.strip()
            )
        )

    def _make_analysis_placeholder(self, url):
        """Cria uma linha imediatamente, antes do yt-dlp responder."""
        item = MediaItem(
            source_url=url,
            webpage_url=url,
            title=url,
            output_format=self.settings["format"],
            resolution=self.settings["resolution"],
            analysis_state="waiting",
            status="Aguardando análise",
        )
        return item

    def _queue_index_for_item(self, target):
        for index, item in enumerate(self.queue):
            if item is target:
                return index
        return -1

    def _queue_index_for_id(self, queue_id):
        for index, item in enumerate(self.queue):
            if item.queue_id == queue_id:
                return index
        return -1

    def _submit_analysis(self, url, placeholder):
        token = placeholder.queue_id
        self._analysis_placeholders[token] = placeholder
        self._active_analysis_urls.add(url)

        self.metadata_service.analyze_async(
            url,
            self.settings["browser_cookies"],
            lambda success, result, error, stable_token=token: (
                self.signals.analysis_finished.emit(
                    success,
                    result,
                    error,
                    stable_token,
                )
            ),
            started_callback=(
                lambda _url, stable_token=token: (
                    self.signals.analysis_started.emit(stable_token)
                )
            ),
        )

    def analyze_links(self):
        urls = self._input_urls()

        if not urls:
            QMessageBox.information(
                self,
                "Nenhum link",
                "Cole pelo menos um endereço.",
            )
            return

        self.save_preferences(
            show_message=False
        )

        self._append_log(
            f"[ANÁLISE] Recebidos {len(urls)} link(s)."
        )

        jobs = []
        ignored = 0

        # Todos entram visualmente na fila ANTES de iniciar os workers.
        for url in urls:
            if url in self._active_analysis_urls:
                ignored += 1
                continue

            placeholder = self._make_analysis_placeholder(
                url
            )
            self.queue.append(
                placeholder
            )
            jobs.append(
                (url, placeholder)
            )

            self._append_log(
                f"[ANÁLISE] Enfileirado: {url}"
            )

        # O campo pode ser limpo imediatamente: os links já estão visíveis.
        self.links_input.clear()
        self.refresh_queue()

        for url, placeholder in jobs:
            self._submit_analysis(url, placeholder)

        if ignored:
            self._append_log(
                (
                    f"[ANÁLISE] {ignored} link(s) ignorado(s): "
                    "já estavam sendo analisados."
                )
            )

        if jobs:
            self._append_log(
                (
                    f"[ANÁLISE] {len(jobs)} trabalho(s) enviados "
                    "aos workers."
                )
            )
            self.statusBar().showMessage(
                f"{len(jobs)} link(s) adicionados. Analisando em segundo plano..."
            )
        elif ignored:
            self.statusBar().showMessage(
                "Esses links já estão sendo analisados.",
                4000,
            )

    def _analysis_started(self, analysis_token):
        placeholder = self._analysis_placeholders.get(analysis_token)
        if placeholder is None:
            return

        row = self._queue_index_for_item(placeholder)
        if row < 0:
            return

        placeholder.analysis_state = "analyzing"
        placeholder.status = "Analisando"
        placeholder.error_message = ""

        self._append_log(
            f"[ANÁLISE] Iniciando: {placeholder.source_url}"
        )

        self._update_status_cell(row)
        self._update_queue_summary()

    @staticmethod
    def _analysis_error_parts(error):
        if isinstance(error, AppError):
            return (
                error.title or "Erro na análise",
                error.message or "Não foi possível analisar este link.",
                error.technical_details or "",
            )

        text = str(error or "Erro desconhecido")
        return (
            "Erro na análise",
            "Não foi possível analisar este link.",
            text,
        )

    def _analysis_finished(
        self,
        success,
        result,
        error,
        analysis_token,
    ):
        placeholder = self._analysis_placeholders.pop(
            analysis_token,
            None,
        )

        # O usuário pode ter removido/limpado a linha durante a análise.
        if placeholder is None:
            return

        self._active_analysis_urls.discard(placeholder.source_url)

        row = self._queue_index_for_item(placeholder)
        if row < 0:
            return

        if not success or result is None:
            title, message, technical = self._analysis_error_parts(error)
            placeholder.analysis_state = "error"
            placeholder.status = "Erro na análise"
            placeholder.error_message = f"{title}: {message}"
            placeholder.technical_error = technical

            self._append_log(
                (
                    f"[ANÁLISE][ERRO] {placeholder.source_url}\n"
                    f"Título: {title}\n"
                    f"Mensagem: {message}"
                )
            )

            if technical:
                self._append_log(
                    "[ANÁLISE][DETALHES] " + technical
                )

            self._render_queue_row(row, placeholder)
            self._update_queue_summary()

            if self.queue_table.currentRow() == row:
                self.update_preview()

            self.statusBar().showMessage(
                "Um link apresentou erro de análise. Os demais continuam normalmente.",
                5000,
            )
            return

        analysis: AnalysisResult = result
        items = list(analysis.items)

        if analysis.is_playlist and len(items) > 1:
            dialog = PlaylistSelectionDialog(
                analysis.title,
                items,
                self,
            )

            if dialog.exec() != QDialog.DialogCode.Accepted:
                self._append_log(
                    (
                        "[ANÁLISE] Seleção de playlist cancelada: "
                        f"{placeholder.source_url}"
                    )
                )
                self.queue.pop(row)
                self.refresh_queue()
                return

            items = dialog.selected_items()

        if not items:
            self._append_log(
                (
                    "[ANÁLISE] Nenhum item retornado/selecionado: "
                    f"{placeholder.source_url}"
                )
            )
            self.queue.pop(row)
            self.refresh_queue()
            return

        # O preset escolhido enquanto o placeholder aguardava é preservado.
        for item in items:
            item.output_format = placeholder.output_format
            item.resolution = placeholder.resolution
            item.analysis_state = "ready"
            item.status = "Pronto"
            item.error_message = ""
            item.technical_error = ""

        if len(items) == 1:
            # Mantém o mesmo ID visual para uma troca 1:1.
            items[0].queue_id = placeholder.queue_id
            self.queue[row] = items[0]
            self._render_queue_row(row, items[0])
        else:
            # Playlist: uma linha placeholder vira N linhas reais.
            self.queue[row:row + 1] = items
            self.refresh_queue()

        self._update_queue_summary()

        if len(items) == 1:
            analyzed_item = items[0]
            self._append_log(
                (
                    f"[ANÁLISE][OK] {analyzed_item.title}\n"
                    f"Fonte: {analyzed_item.webpage_url or analyzed_item.source_url}\n"
                    f"Site: {analyzed_item.site_name}\n"
                    f"ID da mídia: {analyzed_item.media_id or 'não informado'}\n"
                    f"Identidade: {analyzed_item.media_key or 'não disponível'}\n"
                    f"Duração: {analyzed_item.display_duration}\n"
                    f"Formatos utilizáveis: {len(analyzed_item.formats)}"
                )
            )
        else:
            self._append_log(
                (
                    f"[ANÁLISE][OK] Playlist '{analysis.title}': "
                    f"{len(items)} item(ns) prontos."
                )
            )

        self.statusBar().showMessage(
            f"{len(items)} item(ns) prontos para download.",
            4000,
        )

    # =================================================================
    # FILA
    # =================================================================

    def _status_text(self, item):
        # A coluna Status permanece curta e previsível. Mensagens completas ficam
        # no tooltip/preview e, quando necessário, no diálogo de erro.
        return tr(item.status)

    def _clear_queue_cell(self, row, column):
        """
        Remove completamente o conteúdo visual de uma célula.

        QTableWidget permite que uma célula possua:
        - um QTableWidgetItem; e
        - um QWidget instalado com setCellWidget().

        Se trocarmos de texto para QComboBox sem remover o item anterior,
        ambos podem ser desenhados no macOS e os textos ficam sobrepostos.
        """

        widget = self.queue_table.cellWidget(row, column)

        if widget is not None:
            self.queue_table.removeCellWidget(row, column)
            widget.deleteLater()

        old_item = self.queue_table.takeItem(row, column)

        # Mantemos a referência apenas até aqui para que o objeto Python/Qt
        # possa ser liberado normalmente.
        del old_item

    def _render_queue_row(self, row, item):
        for column in range(3):
            self._clear_queue_cell(row, column)

        self.queue_table.setRowHeight(row, 62)

        summary = QueueSummaryWidget(item, self.queue_table)
        self.queue_table.setCellWidget(row, 0, summary)

        progress = QProgressBar()
        progress.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        if item.analysis_pending:
            progress.setRange(0, 0)
            progress.setFormat("")
        else:
            progress.setRange(0, 100)
            progress.setValue(int(item.progress))
            if item.analysis_state == "error":
                progress.setFormat("—")
            else:
                progress.setFormat("%p%")

        self.queue_table.setCellWidget(row, 1, progress)

        status_item = QTableWidgetItem(self._status_text(item))
        status_item.setToolTip(
            item.technical_error
            or item.error_message
            or item.status
        )

        status_folded = item.status.casefold()
        if "erro" in status_folded:
            status_item.setForeground(QColor("#FF9B9B"))
        elif item.status in ("Concluído", "Já baixado"):
            status_item.setForeground(QColor("#71DD8B"))
        elif item.status in ("Baixando", "Analisando"):
            status_item.setForeground(QColor("#8EC5FF"))

        self.queue_table.setItem(row, 2, status_item)

    def _update_status_cell(self, row):
        if not (0 <= row < len(self.queue)):
            return
        item = self.queue[row]
        status_item = self.queue_table.item(row, 2)
        if status_item is None:
            status_item = QTableWidgetItem()
            self.queue_table.setItem(row, 2, status_item)
        status_item.setText(self._status_text(item))
        status_item.setToolTip(
            item.technical_error
            or item.error_message
            or item.status
        )

    def _analysis_counts(self):
        return {
            "waiting": sum(
                1 for item in self.queue
                if item.analysis_state == "waiting"
            ),
            "analyzing": sum(
                1 for item in self.queue
                if item.analysis_state == "analyzing"
            ),
            "analysis_errors": sum(
                1 for item in self.queue
                if item.analysis_state == "error"
            ),
            "ready": sum(
                1 for item in self.queue
                if (
                    item.analysis_state == "ready"
                    and item.status == "Pronto"
                )
            ),
            "downloadable": sum(
                1 for item in self.queue
                if item.ready_for_download
            ),
        }

    def _update_download_action(self):
        if self.running:
            self.download_button.setEnabled(False)
            self.download_button.setText(tr("Baixando..."))
            return

        if (
            self.scheduled_timer
            and self.scheduled_timer.isActive()
        ):
            self.download_button.setEnabled(False)
            self.download_button.setText(tr("Fila agendada"))
            return

        counts = self._analysis_counts()
        downloadable = counts["downloadable"]
        unfinished_analysis = (
            counts["waiting"]
            + counts["analyzing"]
        )

        if downloadable:
            self.download_button.setEnabled(True)
            if unfinished_analysis:
                self.download_button.setText(
                    tr("Baixar {count} pronto(s)", count=downloadable)
                )
            else:
                self.download_button.setText(tr("Baixar fila"))
            return

        self.download_button.setEnabled(False)
        if unfinished_analysis:
            self.download_button.setText(tr("Aguardando análise"))
        elif self.queue:
            self.download_button.setText(tr("Nada pendente"))
        else:
            self.download_button.setText(tr("Baixar fila"))

    def _update_queue_summary(self):
        counts = self._analysis_counts()
        total = len(self.queue)

        parts = [tr("{count} item(ns)", count=total)]
        parts.append(tr("{count} pronto(s)", count=counts["ready"]))
        if counts["analyzing"]:
            parts.append(tr("{count} analisando", count=counts["analyzing"]))
        if counts["waiting"]:
            parts.append(tr("{count} aguardando", count=counts["waiting"]))
        if counts["analysis_errors"]:
            parts.append(tr("{count} erro(s) de análise", count=counts["analysis_errors"]))

        self.queue_count_label.setText(" | ".join(parts))
        self._update_download_action()
        self._update_queue_action_buttons()

    def _update_queue_action_buttons(self):
        row = self.queue_table.currentRow()
        valid_selection = 0 <= row < len(self.queue)

        self.remove_button.setEnabled(
            not self.running and valid_selection
        )

        has_any_error = any(
            item.analysis_state == "error"
            or (
                item.analysis_state == "ready"
                and item.status == "Erro"
            )
            for item in self.queue
        )

        selected_is_error = False
        if valid_selection:
            selected = self.queue[row]
            selected_is_error = (
                selected.analysis_state == "error"
                or (
                    selected.analysis_state == "ready"
                    and selected.status == "Erro"
                )
            )

        self.retry_button.setVisible(has_any_error)
        self.retry_button.setEnabled(
            not self.running and selected_is_error
        )

        if hasattr(
            self,
            "clear_queue_button",
        ):
            self.clear_queue_button.setEnabled(
                bool(self.queue)
                and not self._clear_queue_after_downloads
            )

    def refresh_queue(self):
        selected_id = None
        selected_row = self.queue_table.currentRow()
        if 0 <= selected_row < len(self.queue):
            selected_id = self.queue[selected_row].queue_id

        # Evita dezenas/centenas de repaints e sinais durante a carga em lote.
        previous_block = self.queue_table.blockSignals(True)
        self.queue_table.setUpdatesEnabled(False)
        try:
            self.queue_table.setRowCount(len(self.queue))
            for row, item in enumerate(self.queue):
                self._render_queue_row(row, item)
        finally:
            self.queue_table.setUpdatesEnabled(True)
            self.queue_table.blockSignals(previous_block)

        self._update_queue_summary()

        # Força um repaint limpo depois de trocar items/widgets nas células.
        self.queue_table.viewport().update()

        if selected_id:
            row = self._queue_index_for_id(selected_id)
            if row >= 0:
                self.queue_table.selectRow(row)

        self._update_queue_action_buttons()





    def remove_selected(self):
        if self.running:
            return

        row = self.queue_table.currentRow()
        if not (0 <= row < len(self.queue)):
            return

        item = self.queue[row]

        if (
            self._analysis_placeholders.get(item.queue_id)
            is item
        ):
            self._analysis_placeholders.pop(item.queue_id, None)
            self._active_analysis_urls.discard(item.source_url)

        self.queue.pop(row)
        self.refresh_queue()
        self.update_preview()

    def move_selected(
        self,
        delta,
    ):
        if self.running:
            return

        row = (
            self.queue_table.currentRow()
        )

        target = row + delta

        if (
            row < 0
            or target < 0
            or target >= len(self.queue)
        ):
            return

        self.queue[row], self.queue[target] = (
            self.queue[target],
            self.queue[row],
        )

        self.refresh_queue()

        self.queue_table.selectRow(
            target
        )

    def _clear_queue_now(
        self,
        show_status=True,
    ):
        """
        Limpa a fila visual e invalida callbacks de análises antigas.

        Downloads ativos nunca chamam este método diretamente. Quando há
        processos yt-dlp em execução, clear_queue() solicita cancelamento e
        aguarda o callback _downloads_finished().
        """

        # Se havia um agendamento para esta fila, ele deixa de fazer sentido.
        if (
            self.scheduled_timer
            and self.scheduled_timer.isActive()
        ):
            self.scheduled_timer.stop()
            self.schedule_checkbox.setChecked(
                False
            )

        # Workers de análise já iniciados podem terminar em background, mas
        # os callbacks serão ignorados porque os tokens deixam de existir.
        self._analysis_placeholders.clear()
        self._active_analysis_urls.clear()

        self.queue.clear()
        self.queue_table.clearSelection()

        self.refresh_queue()
        self.clear_preview()

        self._append_log(
            "[FILA] Fila limpa pelo usuário."
        )

        if show_status:
            self.statusBar().showMessage(
                "Fila limpa.",
                3000,
            )

    def clear_queue(self):
        if not self.queue:
            self._clear_queue_now()
            return

        if self.running:
            answer = QMessageBox.question(
                self,
                "Limpar fila?",
                (
                    "Existem downloads em andamento. Para limpar toda a "
                    "fila com segurança, os downloads ativos precisam ser "
                    "cancelados primeiro.\n\n"
                    "Deseja cancelar os downloads e limpar a fila?"
                ),
                (
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.No
                ),
                QMessageBox.StandardButton.No,
            )

            if (
                answer
                != QMessageBox.StandardButton.Yes
            ):
                return

            self._clear_queue_after_downloads = True

            self._append_log(
                (
                    "[FILA] Limpeza solicitada durante download. "
                    "Cancelando o lote antes de remover as linhas."
                )
            )

            self.download_manager.cancel_all()

            self.clear_queue_button.setEnabled(
                False
            )

            self.statusBar().showMessage(
                "Cancelando downloads para limpar a fila..."
            )
            return

        self._clear_queue_now()

    def retry_failed(self):
        row = self.queue_table.currentRow()
        if not (0 <= row < len(self.queue)):
            return

        item = self.queue[row]

        if item.analysis_state == "error":
            item.analysis_state = "waiting"
            item.status = "Aguardando análise"
            item.error_message = ""
            item.technical_error = ""
            item.progress = 0.0
            item.speed = ""
            item.eta = ""
            self._render_queue_row(row, item)
            self._update_queue_action_buttons()
            self._submit_analysis(item.source_url, item)
            return

        if item.analysis_state == "ready" and item.status == "Erro":
            item.status = "Pronto"
            item.error_message = ""
            item.technical_error = ""
            item.progress = 0.0
            item.speed = ""
            item.eta = ""
            self._render_queue_row(row, item)
            self._update_queue_summary()
            self._update_queue_action_buttons()

    def apply_preset(
        self,
        preset_name,
    ):
        preset = PRESETS.get(
            preset_name
        )

        if not preset:
            return

        self.settings["format"] = (
            preset["format"]
        )
        self.settings["resolution"] = (
            preset["resolution"]
        )

        for item in self.queue:
            item.output_format = (
                preset["format"]
            )
            item.resolution = (
                preset["resolution"]
            )
            item.manual_format_selector = ""

        self.refresh_queue()

    # =================================================================
    # PREVIEW / FORMATOS
    # =================================================================

    def update_preview(self):
        row = self.queue_table.currentRow()

        if not (0 <= row < len(self.queue)):
            self.clear_preview()
            return

        item = self.queue[row]
        self.thumbnail_label.setPixmap(QPixmap())
        self.preview_title.setText(item.title)

        self.preview_format_combo.blockSignals(True)
        self.preview_resolution_combo.blockSignals(True)
        try:
            self.preview_format_combo.setCurrentText(item.output_format)
            set_combo_value(self.preview_resolution_combo, item.resolution)
        finally:
            self.preview_format_combo.blockSignals(False)
            self.preview_resolution_combo.blockSignals(False)

        editable = (
            item.analysis_state == "ready"
            and not self.running
        )
        self.preview_format_combo.setEnabled(editable)
        self.preview_resolution_combo.setEnabled(editable)

        if item.analysis_state in ("waiting", "analyzing"):
            self.preview_meta.setText(
                tr("URL: ")
                + item.source_url
                + "\\n"
                + tr("Status: ")
                + tr(item.status)
                + "\\n\\n"
                + tr(
                    "O item já está na fila visual. A análise continua em segundo plano."
                )
            )
            self.thumbnail_label.setText(tr(item.status) + "...")
            self.format_details_button.setText(
                tr("Ver formatos disponíveis")
            )
            self.format_details_button.setEnabled(False)
            self._update_preview_developer_info(item)
            return

        if item.analysis_state == "error":
            self.preview_title.setText(tr("Falha ao analisar o link"))
            self.preview_meta.setText(
                tr("URL: ")
                + item.source_url
                + "\\n\\n"
                + tr(
                    item.error_message
                    or "Não foi possível analisar este endereço."
                )
            )
            self.thumbnail_label.setText(tr("Erro na análise"))
            self.format_details_button.setText(tr("Ver erro da análise"))
            self.format_details_button.setEnabled(True)
            self._update_preview_developer_info(item)
            return

        self.format_details_button.setText(
            tr("Ver formatos disponíveis")
        )
        manual = (
            "\\n" + tr("Formato manual: ativo")
            if item.manual_format_selector
            else ""
        )
        self.preview_meta.setText(
            tr("Canal/autor: ")
            + (item.uploader or "—")
            + "\\n"
            + tr("Site: ")
            + item.site_name
            + "\\n"
            + tr("Duração: ")
            + item.display_duration
            + "\\n"
            + tr("Playlist: ")
            + (item.playlist or "—")
            + "\\n"
            + tr("Formatos conhecidos: ")
            + str(len(item.formats))
            + manual
        )

        self.format_details_button.setEnabled(True)
        self._update_preview_developer_info(item)

        if not item.thumbnail_url:
            self.thumbnail_label.setText(tr("Sem thumbnail"))
            return

        self.thumbnail_label.setText(tr("Carregando thumbnail..."))
        selected_id = item.queue_id
        self.thumbnail_service.fetch_async(
            item.thumbnail_url,
            lambda success, data, item_id=selected_id: (
                self.signals.thumbnail_finished.emit(
                    success,
                    data,
                    item_id,
                )
            ),
        )

    def clear_preview(self):
        self.preview_title.setText("")
        self.preview_meta.setText("")
        self.thumbnail_label.setPixmap(QPixmap())
        self.thumbnail_label.setText(tr("Selecione um item da fila"))
        self.format_details_button.setText(tr("Ver formatos disponíveis"))
        self.format_details_button.setEnabled(False)
        self.preview_format_combo.setEnabled(False)
        self.preview_resolution_combo.setEnabled(False)
        self.preview_dev_info.clear()
        self._update_preview_developer_info()

    def _thumbnail_finished(
        self,
        success,
        data,
        item_id,
    ):
        row = self._queue_index_for_id(item_id)
        current_row = self.queue_table.currentRow()

        if (
            row < 0
            or row != current_row
            or not success
            or not data
        ):
            return

        pixmap = QPixmap()

        if not pixmap.loadFromData(data):
            return

        self.thumbnail_label.setPixmap(
            pixmap.scaled(
                self.thumbnail_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        self.thumbnail_label.setText("")

    def show_format_details(self):
        row = self.queue_table.currentRow()
        if not (0 <= row < len(self.queue)):
            return

        item = self.queue[row]

        if item.analysis_state == "error":
            FriendlyErrorDialog(
                AppError(
                    title="Erro na análise",
                    message=(
                        item.error_message
                        or "Não foi possível analisar este link."
                    ),
                    technical_details=item.technical_error,
                    code="analysis_error",
                ),
                self,
            ).exec()
            return

        if item.analysis_state != "ready":
            return

        if not item.formats:
            self.statusBar().showMessage(
                "Consultando formatos do item..."
            )
            item_id = item.queue_id
            self.metadata_service.enrich_item_async(
                item,
                self.settings["browser_cookies"],
                lambda success, enriched, error, stable_id=item_id: (
                    self.signals.enrich_finished.emit(
                        success,
                        enriched,
                        error,
                        stable_id,
                    )
                ),
            )
            return

        self._open_format_dialog(row)

    def _enrich_finished(
        self,
        success,
        enriched,
        error,
        item_id,
    ):
        row = self._queue_index_for_id(item_id)

        if (
            not success
            or enriched is None
            or row < 0
        ):
            self._show_error(error)
            return

        enriched.queue_id = item_id
        enriched.analysis_state = "ready"
        self.queue[row] = enriched

        self.refresh_queue()
        row = self._queue_index_for_id(item_id)
        if row < 0:
            return

        self.queue_table.selectRow(row)
        self._open_format_dialog(row)

    def _open_format_dialog(
        self,
        row,
    ):
        item = self.queue[row]

        dialog = FormatDetailsDialog(
            item,
            self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        item.manual_format_selector = (
            dialog.selected_selector
        )

        if dialog.selected_selector:
            item.resolution = (
                "Melhor disponível"
            )

        self.refresh_queue()

        self.queue_table.selectRow(
            row
        )

        self.update_preview()

    # =================================================================
    # DOWNLOAD / AGENDAMENTO
    # =================================================================

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self,
            tr("Escolha a pasta de destino"),
            expand_user_path(self.folder_edit.text())
            or str(Path.home()),
        )

        if folder:
            self.folder_edit.setText(
                compact_user_path(folder)
            )

    def _schedule_toggled(
        self,
        checked,
    ):
        self.schedule_date.setEnabled(
            checked
        )
        self.schedule_time.setEnabled(
            checked
        )

        if checked:
            self._update_schedule_constraints()

    def _update_schedule_constraints(
        self,
        *_args,
    ):
        """
        Não permite datas passadas.

        Se o dia escolhido for hoje, o horário mínimo é o horário atual.
        Em dias futuros, a hora mínima volta para 00:00.
        """

        now = QDateTime.currentDateTime()

        self.schedule_date.setMinimumDate(
            now.date()
        )

        if (
            self.schedule_date.date()
            == now.date()
        ):
            self.schedule_time.setMinimumTime(
                now.time()
            )
        else:
            self.schedule_time.setMinimumTime(
                QTime(0, 0, 0)
            )

    def _scheduled_datetime(
        self,
    ):
        self._update_schedule_constraints()

        return QDateTime(
            self.schedule_date.date(),
            self.schedule_time.time(),
        )

    def start_or_schedule(self):
        if not self.queue:
            QMessageBox.information(
                self,
                "Fila vazia",
                "Cole links e use ‘Analisar e adicionar’ primeiro.",
            )
            return

        ready_count = sum(
            1 for item in self.queue
            if item.ready_for_download
        )

        if not ready_count:
            counts = self._analysis_counts()
            if counts["waiting"] or counts["analyzing"]:
                QMessageBox.information(
                    self,
                    "Análise em andamento",
                    (
                        "Os links já estão na fila, mas ainda não há "
                        "nenhum item pronto para download."
                    ),
                )
            else:
                QMessageBox.information(
                    self,
                    "Nada para baixar",
                    "Não há itens prontos para download.",
                )
            return

        self.save_preferences(show_message=False)

        if not self.schedule_checkbox.isChecked():
            self.start_downloads()
            return

        target = self._scheduled_datetime()
        milliseconds = (
            QDateTime.currentDateTime()
            .msecsTo(target)
        )

        if milliseconds <= 0:
            QMessageBox.warning(
                self,
                "Horário inválido",
                "Escolha uma data/hora no futuro.",
            )
            return

        if milliseconds > 2_000_000_000:
            QMessageBox.warning(
                self,
                "Agendamento muito distante",
                (
                    "Escolha um horário dentro dos próximos 23 dias. "
                    "O aplicativo precisa permanecer aberto."
                ),
            )
            return

        if self.scheduled_timer:
            self.scheduled_timer.stop()
            self.scheduled_timer.deleteLater()

        self.scheduled_timer = QTimer(self)
        self.scheduled_timer.setSingleShot(True)
        self.scheduled_timer.timeout.connect(self._scheduled_start)
        self.scheduled_timer.start(int(milliseconds))

        self._update_download_action()
        self.statusBar().showMessage(
            "Fila agendada para "
            + target.toString(datetime_display_format())
            + "."
        )

    def _scheduled_start(self):
        self.download_button.setEnabled(
            True
        )

        self.download_button.setText(
            tr("Baixar fila")
        )

        self.schedule_checkbox.setChecked(
            False
        )

        self.start_downloads()

    def _check_disk_space(
        self,
        folder,
    ):
        try:
            usage = shutil.disk_usage(
                folder
            )

        except OSError:
            return True

        estimated = sum(
            item.estimated_size
            for item in self.queue
            if item.status
            in (
                "Pronto",
                "Erro",
                "Na fila",
            )
        )

        if not estimated:
            return True

        required = int(
            estimated * 1.15
        )

        if required <= usage.free:
            return True

        QMessageBox.warning(
            self,
            "Pouco espaço no disco",
            (
                "A estimativa conhecida é maior que "
                "o espaço livre disponível.\n\n"
                f"Estimado: {self._human_bytes(required)}\n"
                f"Livre: {self._human_bytes(usage.free)}"
            ),
        )

        return False

    @staticmethod
    def _human_bytes(
        value,
    ):
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
                    f"{number:.1f} {unit}"
                )

            number /= 1024

        return f"{number:.1f} PB"

    def start_downloads(self):
        if self.running:
            return

        folder_display = self.folder_edit.text().strip()
        folder = expand_user_path(folder_display)

        if not folder:
            QMessageBox.warning(
                self,
                "Pasta inválida",
                "Escolha uma pasta de destino.",
            )
            return

        try:
            Path(folder).mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as error:
            QMessageBox.warning(
                self,
                "Pasta indisponível",
                str(error),
            )
            return

        if not self._check_disk_space(folder):
            return

        # Apenas itens ANALISADOS e prontos entram neste lote. Os demais
        # continuam analisando e poderão ser baixados em um próximo clique.
        pending = [
            (item.queue_id, item)
            for item in self.queue
            if item.ready_for_download
        ]

        if not pending:
            self._append_log(
                "[DOWNLOAD] Nenhum item pronto para iniciar."
            )
            QMessageBox.information(
                self,
                "Nada para baixar",
                "Ainda não há itens analisados e prontos para download.",
            )
            self._update_download_action()
            return

        self._append_log(
            (
                f"[DOWNLOAD] Iniciando lote com {len(pending)} item(ns).\n"
                f"Pasta de destino: {folder}"
            )
        )

        for _, item in pending:
            item.status = "Na fila"
            item.error_message = ""
            item.progress = 0.0
            item.speed = ""
            item.eta = ""

            self._append_log(
                (
                    f"[DOWNLOAD] Na fila: {item.title} | "
                    f"{item.output_format} | {item.resolution}"
                )
            )

        self.running = True
        self.pause_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

        # Preferências e Configurações continuam acessíveis durante o lote.
        # O DownloadManager recebe uma cópia das configurações abaixo, então
        # alterações feitas depois não modificam downloads já iniciados.
        self.refresh_queue()

        batch_settings = dict(
            self.settings
        )

        self.download_manager.start(
            pending,
            folder,
            batch_settings,
            self.signals.downloads_finished.emit,
        )

    def toggle_pause(self):
        if not self.running:
            return

        if self.download_manager.paused:
            self.download_manager.resume_all()

            self._append_log(
                "[DOWNLOAD] Downloads retomados."
            )

            self.pause_button.setText(
                tr("Pausar")
            )

            self.statusBar().showMessage(
                "Downloads retomados."
            )

        else:
            self.download_manager.pause_all()

            self._append_log(
                "[DOWNLOAD] Downloads pausados."
            )

            self.pause_button.setText(
                tr("Retomar")
            )

            self.statusBar().showMessage(
                "Downloads pausados."
            )

    def cancel_downloads(self):
        if not self.running:
            return

        answer = QMessageBox.question(
            self,
            "Cancelar downloads?",
            (
                "Deseja cancelar os downloads ativos? "
                "Arquivos já concluídos serão mantidos."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if (
            answer
            == QMessageBox.StandardButton.Yes
        ):
            self._append_log(
                "[DOWNLOAD] Cancelamento solicitado pelo usuário."
            )
            self.download_manager.cancel_all()

            self.statusBar().showMessage(
                "Cancelando..."
            )

    def _apply_progress(
        self,
        item_id,
        status,
        percent,
        speed,
        eta,
    ):
        row = self._queue_index_for_id(item_id)
        if row < 0:
            return

        item = self.queue[row]
        if status == item.title:
            item.status = "Baixando"
        else:
            item.status = status

        item.progress = percent
        item.speed = speed
        item.eta = eta

        progress = self.queue_table.cellWidget(row, 1)
        if isinstance(progress, QProgressBar):
            if progress.minimum() == 0 and progress.maximum() == 0:
                progress.setRange(0, 100)
                progress.setFormat("%p%")
            progress.setValue(int(percent))

        self._update_status_cell(row)

        if self.queue_table.currentRow() == row:
            self._update_preview_developer_info(item)

    def _download_result(self, result):
        result: DownloadResult = result

        row = self._queue_index_for_id(result.item_id)
        if row < 0:
            return

        item = self.queue[row]
        item.output_path = result.output_path
        item.technical_error = result.technical_error

        if result.cancelled:
            item.status = "Cancelado"
            item.error_message = ""
            self._append_log(
                f"[DOWNLOAD][CANCELADO] {item.title}"
            )

        elif result.already_downloaded:
            item.progress = 100.0
            item.error_message = ""

            if result.file_missing:
                item.status = (
                    "Já baixado — arquivo não encontrado"
                )
            else:
                item.status = "Já baixado"

            self._append_log(
                (
                    f"[DOWNLOAD][DUPLICADO] {item.title}\n"
                    f"Identidade: {item.media_key or 'não disponível'}\n"
                    f"Status: {item.status}\n"
                    f"Arquivo: {item.output_path or 'não encontrado'}"
                )
            )

        elif result.success:
            item.status = "Concluído"
            item.progress = 100.0
            item.error_message = ""
            self._append_log(
                (
                    f"[DOWNLOAD][OK] {item.title}\n"
                    f"Identidade: {item.media_key or 'não disponível'}\n"
                    f"Arquivo: {item.output_path or 'não informado'}"
                )
            )

        else:
            item.status = "Erro"
            item.error_message = result.error_message

            self._append_log(
                (
                    f"[DOWNLOAD][ERRO] {item.title}\n"
                    f"Mensagem: {result.error_message or 'erro não especificado'}"
                )
            )

            if result.technical_error:
                self._append_log(
                    "[DOWNLOAD][DETALHES] "
                    + result.technical_error
                )

        try:
            self.history_manager.add(
                url=item.webpage_url,
                source=(
                    item.webpage_url
                    or item.source_url
                ),
                title=item.title,
                extractor=item.extractor,
                extractor_key=(
                    item.extractor_key
                    or item.extractor
                ),
                media_id=item.media_id,
                media_key=item.media_key,
                output_path=item.output_path,
                output_format=item.output_format,
                resolution=item.resolution,
                status=item.status,
                error_message=item.error_message,
            )
        except Exception as error:
            self._append_log(
                f"Não foi possível registrar o histórico: {error}"
            )

        self._render_queue_row(row, item)
        self._update_queue_summary()
        self._update_queue_action_buttons()
        self.refresh_history()

    def _downloads_finished(self):
        self.running = False

        self._append_log(
            "[DOWNLOAD] Lote finalizado."
        )

        self.pause_button.setEnabled(False)
        self.pause_button.setText(tr("Pausar"))
        self.cancel_button.setEnabled(False)

        clear_after_downloads = (
            self._clear_queue_after_downloads
        )

        self._clear_queue_after_downloads = False

        if clear_after_downloads:
            self._clear_queue_now(
                show_status=False
            )
        else:
            # Reabilita os controles dos itens analisados e recalcula o botão.
            self.refresh_queue()

        errors = sum(
            1
            for item in self.queue
            if item.status == "Erro"
        )

        still_analyzing = sum(
            1
            for item in self.queue
            if item.analysis_pending
        )

        if clear_after_downloads:
            message = "Downloads cancelados e fila limpa."
        elif errors:
            message = f"Lote finalizado. {errors} item(ns) com erro."
        else:
            message = "Lote de downloads finalizado."

        if (
            still_analyzing
            and not clear_after_downloads
        ):
            message += (
                f" {still_analyzing} link(s) continuam em análise."
            )

        self.statusBar().showMessage(message)

        if (
            self.settings.get(
                "notifications",
                True,
            )
            and self.notification_controller
        ):
            self.notification_controller.notify(
                tr(APP_NAME),
                tr(message),
            )

    # =================================================================
    # BADGE / NOTIFICAÇÃO
    # =================================================================

    # =================================================================
    # HISTÓRICO
    # =================================================================

    def refresh_history(self):
        try:
            rows = (
                self.history_manager.list_recent()
            )

        except Exception as error:
            self._append_log(
                f"Erro no histórico: {error}"
            )
            return

        self.history_table.setRowCount(
            len(rows)
        )

        for row, record in enumerate(
            rows
        ):
            values = [
                str(record["id"]),
                str(record["created_at"]).replace(
                    "T",
                    " ",
                ),
                record["title"],
                record["extractor"] or "",
                (
                    record.get("source")
                    or record.get("url")
                    or ""
                ),
                record["output_format"] or "",
                tr(record["resolution"] or ""),
                tr(record["status"]),
                record["output_path"] or "",
            ]

            for column, value in enumerate(
                values
            ):
                cell = QTableWidgetItem(
                    str(value)
                )

                if column == 0:
                    cell.setData(
                        Qt.ItemDataRole.UserRole,
                        record["id"],
                    )

                if column in (4, 8):
                    cell.setToolTip(
                        str(value)
                    )

                self.history_table.setItem(
                    row,
                    column,
                    cell,
                )

    def _selected_history_record(self):
        row = (
            self.history_table.currentRow()
        )

        if row < 0:
            return None

        item = (
            self.history_table.item(
                row,
                0,
            )
        )

        if not item:
            return None

        record_id = item.data(
            Qt.ItemDataRole.UserRole
        )

        if record_id is None:
            return None

        return self.history_manager.get(
            int(record_id)
        )

    def open_history_file(self):
        record = (
            self._selected_history_record()
        )

        if not record:
            return

        path = (
            record.get("output_path")
            or ""
        )

        if not path or not Path(path).exists():
            QMessageBox.information(
                self,
                "Arquivo não encontrado",
                (
                    "O arquivo não existe mais "
                    "nesse caminho."
                ),
            )
            return

        QDesktopServices.openUrl(
            QUrl.fromLocalFile(
                str(Path(path))
            )
        )

    def open_history_folder(self):
        record = (
            self._selected_history_record()
        )

        if not record:
            return

        path = (
            record.get("output_path")
            or ""
        )

        if not path:
            return

        target = Path(path)

        folder = (
            target
            if target.is_dir()
            else target.parent
        )

        if folder.exists():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    str(folder)
                )
            )

    def history_download_again(self):
        record = (
            self._selected_history_record()
        )

        if not record:
            return

        url = (
            record.get("source")
            or record.get("url")
            or ""
        )

        if not url:
            return

        self.tabs.setCurrentIndex(
            0
        )

        self.links_input.setPlainText(
            url
        )

        self.analyze_links()

    def export_history_sources(self):
        """
        Copia os links das linhas selecionadas para a área de transferência.

        Links repetidos são removidos preservando a ordem visual.
        """

        selection_model = (
            self.history_table.selectionModel()
        )

        if selection_model is None:
            return

        selected_rows = sorted(
            {
                index.row()
                for index
                in selection_model.selectedRows()
            }
        )

        if not selected_rows:
            QMessageBox.information(
                self,
                "Nenhuma fonte selecionada",
                (
                    "Selecione uma ou mais linhas do histórico "
                    "antes de exportar."
                ),
            )
            return

        sources = []
        seen = set()

        for row in selected_rows:
            id_item = self.history_table.item(
                row,
                0,
            )

            if id_item is None:
                continue

            record_id = id_item.data(
                Qt.ItemDataRole.UserRole
            )

            if record_id is None:
                continue

            record = self.history_manager.get(
                int(record_id)
            )

            if not record:
                continue

            source = str(
                record.get("source")
                or record.get("url")
                or ""
            ).strip()

            if (
                not source
                or source in seen
            ):
                continue

            seen.add(
                source
            )
            sources.append(
                source
            )

        if not sources:
            QMessageBox.information(
                self,
                "Nenhuma fonte disponível",
                (
                    "As linhas selecionadas não possuem "
                    "links para exportar."
                ),
            )
            return

        QGuiApplication.clipboard().setText(
            "\n".join(sources)
        )

        QMessageBox.information(
            self,
            "Fontes copiadas",
            (
                tr(
                    "{count} fonte(s) única(s) copiadas para a área de transferência.",
                    count=len(sources),
                )
            ),
        )

    def clear_history(self):
        answer = QMessageBox.question(
            self,
            "Limpar histórico?",
            (
                "Isso apaga apenas o histórico visual. "
                "Os arquivos baixados não serão removidos."
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.history_manager.clear()

        self.refresh_history()

    # =================================================================
    # PREFERÊNCIAS
    # =================================================================

    def save_preferences(self, show_message=True):
        self.settings.update(
            {
                "download_folder": compact_user_path(
                    self.folder_edit.text().strip()
                ),
                "format": combo_value(self.pref_format),
                "resolution": combo_value(self.pref_resolution),
                "concurrency": self.pref_concurrency.value(),
                "speed_limit": combo_value(self.pref_speed),
                "audio_quality": combo_value(self.pref_audio_quality),
                "browser_cookies": combo_value(self.pref_browser),
                "organization": combo_value(self.pref_organization),
                "prevent_duplicates": self.pref_duplicates.isChecked(),
                "subtitle_mode": combo_value(self.pref_subtitles),
                "subtitle_languages": self.pref_sub_langs.text().strip(),
                "embed_subtitles": self.pref_embed_subtitles.isChecked(),
                "embed_thumbnail": self.pref_thumbnail.isChecked(),
                "embed_metadata": self.pref_metadata.isChecked(),
                "embed_chapters": self.pref_chapters.isChecked(),
                "clipboard_detection": self.pref_clipboard.isChecked(),
                "notifications": self.pref_notifications.isChecked(),
                "appearance": combo_value(self.pref_appearance),
                "language": combo_value(self.pref_language),
                "show_technical_button": self.show_technical_button_check.isChecked(),
                "developer_mode": self.developer_mode_check.isChecked(),
            }
        )

        if not self.settings["download_folder"]:
            self.settings["download_folder"] = "~/Downloads/Videos"
            self.folder_edit.setText(self.settings["download_folder"])

        self.config_manager.save(self.settings)
        self.apply_appearance()
        self._apply_feature_visibility()

        if self.notification_controller:
            self.notification_controller.set_enabled(
                bool(
                    self.settings.get(
                        "notifications",
                        True,
                    )
                )
            )

        if show_message:
            QMessageBox.information(
                self,
                "Preferências salvas",
                "As preferências foram salvas.",
            )

    # =================================================================
    # ATUALIZAÇÕES
    # =================================================================

    def update_ytdlp(self):
        if self.running:
            QMessageBox.information(
                self,
                "Download em andamento",
                (
                    "Aguarde o lote atual terminar antes de atualizar "
                    "o yt-dlp. A aba Configurações continua disponível "
                    "para consulta."
                ),
            )
            return

        answer = QMessageBox.question(
            self,
            "Atualizar yt-dlp?",
            (
                "O aplicativo verificará o canal nightly "
                "oficial do yt-dlp.\n\n"
                "Deseja continuar?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        self.statusBar().showMessage(
            "Atualizando yt-dlp..."
        )

        self.update_manager.update_async(
            self.signals.ytdlp_update_finished.emit
        )

    def _ytdlp_update_finished(
        self,
        success,
        message,
    ):
        if success:
            QMessageBox.information(
                self,
                "yt-dlp atualizado",
                message
                or "Atualização concluída.",
            )
        else:
            QMessageBox.warning(
                self,
                "Atualização falhou",
                message,
            )

    def check_app_update(self):
        if self.running:
            QMessageBox.information(
                self,
                "Download em andamento",
                (
                    "Aguarde o lote atual terminar antes de verificar "
                    "uma atualização do ClipFetch."
                ),
            )
            return

        self.save_preferences(
            show_message=False
        )

        self.statusBar().showMessage(
            "Verificando atualização do aplicativo..."
        )

        self.app_update_manager.check_async(
            self.signals.app_update_finished.emit,
        )

    def _app_update_finished(
        self,
        success,
        info,
        error,
    ):
        if not success or info is None:
            QMessageBox.warning(
                self,
                "Não foi possível verificar",
                error,
            )
            return

        if not (
            self.app_update_manager.is_newer(
                info.latest_version
            )
        ):
            QMessageBox.information(
                self,
                "Aplicativo atualizado",
                (
                    f"Versão atual: {APP_VERSION}\n"
                    f"Última release: {info.latest_version}"
                ),
            )
            return

        answer = QMessageBox.question(
            self,
            "Nova versão disponível",
            (
                f"Atual: {APP_VERSION}\n"
                f"Disponível: {info.latest_version}\n\n"
                "Deseja abrir a nova versão?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        target = (
            info.dmg_url
            or info.html_url
        )

        if target:
            QDesktopServices.openUrl(
                QUrl(target)
            )

    # =================================================================
    # SITES / DIAGNÓSTICO
    # =================================================================

    def _show_error(self, error):
        if error is None:
            error = AppError("Erro", "Ocorreu um erro sem detalhes adicionais.")
        elif not isinstance(error, AppError):
            error = AppError("Erro", "Ocorreu um erro durante a operação.", str(error))
        FriendlyErrorDialog(error, self).exec()

    def show_supported_sites(self):
        dialog = SupportedSitesDialog(
            self.tools,
            self,
        )

        dialog.exec()

    def show_tools(self):
        self.statusBar().showMessage("Obtendo versões para diagnóstico...")
        QMessageBox.information(
            self,
            "Ferramentas internas",
            self.tools.diagnostic_text(include_versions=True),
        )

    def copy_diagnostic(self):
        diagnostic = (
            f"{APP_NAME} {APP_VERSION}\n\n"
            f"{self.tools.diagnostic_text()}\n\n"
            f"{tr('Pasta: ')}{self.folder_edit.text()}\n"
            f"{tr('Formato padrão: ')}{tr(self.settings['format'])}\n"
            f"{tr('Resolução: ')}{tr(self.settings['resolution'])}\n"
            f"{tr('Cookies: ')}{tr(self.settings['browser_cookies'])}\n"
        )

        QGuiApplication.clipboard().setText(
            diagnostic
        )

        QMessageBox.information(
            self,
            "Diagnóstico copiado",
            (
                "As informações de diagnóstico "
                "foram copiadas."
            ),
        )

    # =================================================================
    # LOG
    # =================================================================

    def _append_log(
        self,
        text,
    ):
        """
        Adiciona uma entrada ao log técnico com horário.

        Não registra atualizações de porcentagem; essas ficam na tabela.
        """

        value = str(text).rstrip()

        if not value:
            return

        timestamp = (
            QDateTime.currentDateTime()
            .toString("HH:mm:ss")
        )

        for line in value.splitlines():
            self.log_text.appendPlainText(
                f"[{timestamp}] {tr(line)}"
            )

        if self.log_text.isVisible():
            scrollbar = (
                self.log_text.verticalScrollBar()
            )
            scrollbar.setValue(
                scrollbar.maximum()
            )

    def _toggle_log(
        self,
        visible,
    ):
        self.log_text.setVisible(
            visible
        )

        if visible:
            scrollbar = (
                self.log_text.verticalScrollBar()
            )
            scrollbar.setValue(
                scrollbar.maximum()
            )

        self.log_toggle.setText(
            tr(
                "Ocultar detalhes técnicos"
                if visible
                else "Mostrar detalhes técnicos"
            )
        )

    # =================================================================
    # FECHAMENTO
    # =================================================================

    def closeEvent(
        self,
        event,
    ):
        if self.running:
            answer = QMessageBox.question(
                self,
                "Fechar aplicativo?",
                (
                    "Existem downloads em andamento. "
                    "Deseja cancelar e fechar?"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if (
                answer
                != QMessageBox.StandardButton.Yes
            ):
                event.ignore()
                return

            self.download_manager.cancel_all()

        if self.notification_controller:
            self.notification_controller.close()

        # Executors are shared for the lifetime of the window. Cancelling
        # queued work avoids keeping unnecessary threads alive during exit.
        self.metadata_service.shutdown()
        self.thumbnail_service.shutdown()

        event.accept()

"""Qt stylesheets used by ClipFetch.

Visual rules live here so configuration and domain modules stay UI-agnostic.
"""

GREEN_BUTTON_STYLE = """
QPushButton#downloadButton {
    background-color: #34C759;
    color: #FFFFFF;
    border: 1px solid #55D976;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 700;
}
QPushButton#downloadButton:hover { background-color: #42CF67; }
QPushButton#downloadButton:pressed { background-color: #2EAE50; }
QPushButton#downloadButton:disabled {
    background-color: #758179;
    color: #D9DEDB;
    border-color: #7F8B83;
}
"""

# Os três blocos operacionais permanecem grafite em Claro e Escuro, mas não
# usam preto absoluto. O título ocupa uma margem própria acima da borda.
INTERACTIVE_DARK_PANEL_STYLE = """
QGroupBox#interactiveDarkPanel {
    background-color: #30363D;
    color: #F3F5F7;
    border: 1px solid #515A65;
    border-radius: 10px;
    margin-top: 24px;
    padding: 12px 10px 10px 10px;
}
QGroupBox#interactiveDarkPanel::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 2px;
    padding: 0 7px;
    color: #F3F5F7;
    background-color: transparent;
    font-weight: 700;
}
QGroupBox#interactiveDarkPanel QLabel,
QGroupBox#interactiveDarkPanel QCheckBox {
    background: transparent;
    color: #F3F5F7;
}
QGroupBox#interactiveDarkPanel QLabel#queueItemTitle {
    color: #F6F7F8;
    font-size: 14px;
    font-weight: 700;
}
QGroupBox#interactiveDarkPanel QLabel#queueItemMeta {
    color: #B7C0CA;
    font-size: 11px;
}
QGroupBox#interactiveDarkPanel QLabel#developerInfoLabel {
    color: #AEB8C3;
    font-size: 10px;
}
QGroupBox#interactiveDarkPanel QLineEdit,
QGroupBox#interactiveDarkPanel QPlainTextEdit,
QGroupBox#interactiveDarkPanel QTableWidget,
QGroupBox#interactiveDarkPanel QComboBox,
QGroupBox#interactiveDarkPanel QAbstractSpinBox {
    background-color: #3A414A;
    color: #F3F5F7;
    border: 1px solid #596572;
    border-radius: 6px;
    padding: 5px 7px;
    selection-background-color: #397A4A;
    selection-color: #FFFFFF;
}
QGroupBox#interactiveDarkPanel QTableWidget {
    background-color: #343A42;
    alternate-background-color: #30363D;
    gridline-color: transparent;
    outline: 0;
}
QGroupBox#interactiveDarkPanel QTableWidget::item {
    border-bottom: 1px solid #46505A;
    padding: 4px;
}
QGroupBox#interactiveDarkPanel QTableWidget::item:selected {
    background-color: #414B56;
}
QGroupBox#interactiveDarkPanel QHeaderView::section {
    background-color: #3A414A;
    color: #E9EDF1;
    padding: 7px;
    border: 0;
    border-bottom: 1px solid #596572;
    font-weight: 600;
}
QGroupBox#interactiveDarkPanel QProgressBar {
    background-color: #252A30;
    color: #F4F6F8;
    border: 1px solid #56616D;
    border-radius: 6px;
    min-height: 17px;
    text-align: center;
}
QGroupBox#interactiveDarkPanel QProgressBar::chunk {
    background-color: #34C759;
    border-radius: 5px;
}
QGroupBox#interactiveDarkPanel QPushButton {
    background-color: #414851;
    color: #F3F5F7;
    border: 1px solid #616C78;
    border-radius: 7px;
    padding: 7px 12px;
}
QGroupBox#interactiveDarkPanel QPushButton:hover { background-color: #4A535D; }
QGroupBox#interactiveDarkPanel QPushButton:pressed { background-color: #363D45; }
QGroupBox#interactiveDarkPanel QPushButton:disabled {
    background-color: #343A41;
    color: #858E98;
    border-color: #48515B;
}
QGroupBox#interactiveDarkPanel QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #8C97A3;
    border-radius: 4px;
    background-color: #333A42;
}
QGroupBox#interactiveDarkPanel QCheckBox::indicator:checked {
    background-color: #34C759;
    border-color: #65DB80;
}
QGroupBox#interactiveDarkPanel QAbstractSpinBox {
    padding-right: 24px;
}
QGroupBox#interactiveDarkPanel QAbstractSpinBox::up-button,
QGroupBox#interactiveDarkPanel QAbstractSpinBox::down-button {
    subcontrol-origin: border;
    width: 20px;
    background-color: #48515B;
    border-left: 1px solid #65717E;
}
QGroupBox#interactiveDarkPanel QAbstractSpinBox::up-button {
    subcontrol-position: top right;
    border-top-right-radius: 5px;
}
QGroupBox#interactiveDarkPanel QAbstractSpinBox::down-button {
    subcontrol-position: bottom right;
    border-bottom-right-radius: 5px;
}
QGroupBox#interactiveDarkPanel QPushButton#removeButton:disabled {
    background-color: #343A41;
    color: #858E98;
    border: 1px solid #48515B;
}
QGroupBox#interactiveDarkPanel QPushButton#removeButton:enabled {
    background-color: #FF9B9B;
    color: #401818;
    border: 1px solid #FFB6B6;
    font-weight: 700;
}
QGroupBox#interactiveDarkPanel QPushButton#removeButton:enabled:hover {
    background-color: #FFA9A9;
}

QGroupBox#interactiveDarkPanel QToolButton#spinStepButton {
    background-color: #4B5561;
    color: #FFFFFF;
    border: 0;
    border-left: 1px solid #6B7683;
    border-radius: 0;
    padding: 0;
    margin: 0;
    font-size: 8px;
    font-weight: 900;
}
QGroupBox#interactiveDarkPanel QToolButton#spinStepButton[stepDirection="up"] {
    border-top-right-radius: 5px;
    border-bottom: 1px solid #6B7683;
}
QGroupBox#interactiveDarkPanel QToolButton#spinStepButton[stepDirection="down"] {
    border-bottom-right-radius: 5px;
}
QGroupBox#interactiveDarkPanel QToolButton#spinStepButton:hover {
    background-color: #5B6774;
}
QGroupBox#interactiveDarkPanel QToolButton#spinStepButton:pressed {
    background-color: #3D4650;
}
QGroupBox#interactiveDarkPanel QToolButton#spinStepButton:disabled {
    background-color: #3B424A;
    color: #7F8994;
}
""" + GREEN_BUTTON_STYLE


# O Histórico é uma área operacional, por isso permanece grafite nos dois
# temas, igual aos blocos principais da aba Downloads.
HISTORY_DARK_TABLE_STYLE = """
QTableWidget#historyDarkTable {
    background-color: #30363D;
    alternate-background-color: #2B3137;
    color: #EEF1F4;
    border: 1px solid #515A65;
    border-radius: 9px;
    gridline-color: transparent;
    outline: 0;
}
QTableWidget#historyDarkTable::item {
    color: #EEF1F4;
    border-bottom: 1px solid #414A54;
    padding: 6px;
}
QTableWidget#historyDarkTable::item:selected {
    background-color: #3C6949;
    color: #FFFFFF;
}
QTableWidget#historyDarkTable QHeaderView::section {
    background-color: #3A414A;
    color: #F1F3F5;
    padding: 7px;
    border: 0;
    border-right: 1px solid #515A65;
    border-bottom: 1px solid #596572;
    font-weight: 700;
}
QTableWidget#historyDarkTable QTableCornerButton::section {
    background-color: #3A414A;
    border: 0;
    border-right: 1px solid #515A65;
    border-bottom: 1px solid #596572;
}
"""

# Escuro confortável: grafite em vez de preto/preto-cinza.
DARK_STYLE = """

QScrollArea#responsivePageScroll {
    border: 0;
    background: transparent;
}
QScrollArea#responsivePageScroll > QWidget > QWidget {
    background: transparent;
}
QMainWindow,
QDialog,
QWidget#downloadsTab,
QWidget#historyTab,
QWidget#preferencesTab,
QWidget#settingsTab,
QWidget#downloadsScrollContent,
QWidget#preferencesScrollContent,
QWidget#settingsScrollContent {
    background-color: #23272D;
    color: #EDF0F3;
}
QTabWidget::pane { border: 0; top: -1px; }
QTabBar::tab {
    background-color: #343A42;
    color: #E6E9EC;
    border: 1px solid #454D57;
    padding: 8px 17px;
    min-width: 86px;
}
QTabBar::tab:selected {
    background-color: #34C759;
    color: #FFFFFF;
    border-color: #34C759;
    font-weight: 700;
}
QTabBar::tab:hover:!selected { background-color: #3D444D; }
QLabel, QCheckBox { background: transparent; color: #EDF0F3; }
QGroupBox {
    background-color: #2D3239;
    color: #EDF0F3;
    border: 1px solid #49515B;
    border-radius: 10px;
    margin-top: 24px;
    padding: 12px 10px 10px 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 2px;
    padding: 0 7px;
    background: transparent;
    color: #EDF0F3;
    font-weight: 700;
}
QLineEdit, QPlainTextEdit, QListWidget, QTableWidget, QComboBox, QAbstractSpinBox {
    background-color: #383E46;
    color: #F0F2F4;
    border: 1px solid #59636E;
    border-radius: 6px;
    padding: 5px 7px;
    selection-background-color: #397A4A;
    selection-color: #FFFFFF;
}
QAbstractSpinBox { padding-right: 24px; }
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
    subcontrol-origin: border;
    width: 20px;
    background-color: #48515B;
    border-left: 1px solid #65717E;
}
QAbstractSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 5px; }
QAbstractSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 5px; }

QToolButton#spinStepButton {
    background-color: #4B5561;
    color: #FFFFFF;
    border: 0;
    border-left: 1px solid #6B7683;
    border-radius: 0;
    padding: 0;
    margin: 0;
    font-size: 8px;
    font-weight: 900;
}
QToolButton#spinStepButton[stepDirection="up"] {
    border-top-right-radius: 5px;
    border-bottom: 1px solid #6B7683;
}
QToolButton#spinStepButton[stepDirection="down"] {
    border-bottom-right-radius: 5px;
}
QToolButton#spinStepButton:hover { background-color: #5B6774; }
QToolButton#spinStepButton:pressed { background-color: #3D4650; }
QToolButton#spinStepButton:disabled {
    background-color: #3B424A;
    color: #7F8994;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #84909C;
    border-radius: 4px;
    background-color: #363C44;
}
QCheckBox::indicator:checked { background-color: #34C759; border-color: #65DB80; }
QTableWidget { gridline-color: #4B535D; }
QHeaderView::section {
    background-color: #353B43;
    color: #EEF0F2;
    padding: 7px;
    border: 0;
    border-right: 1px solid #4B535D;
}
QPushButton {
    background-color: #3C424A;
    color: #F0F2F4;
    border: 1px solid #5A646F;
    border-radius: 7px;
    padding: 7px 12px;
}
QPushButton:hover { background-color: #464E57; }
QPushButton:pressed { background-color: #343A41; }
QPushButton:disabled { background-color: #33383F; color: #7F8790; border-color: #464D55; }
QProgressBar {
    background-color: #343A42;
    color: #F0F2F4;
    border: 1px solid #59636E;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk { background-color: #34C759; border-radius: 4px; }
QToolTip { background-color: #343A42; color: #FFFFFF; border: 1px solid #626C77; }
""" + GREEN_BUTTON_STYLE + HISTORY_DARK_TABLE_STYLE

# Claro real para Histórico/Preferências/Configurações. Os três blocos de
# Downloads usam INTERACTIVE_DARK_PANEL_STYLE e continuam grafite.
LIGHT_STYLE = """

QScrollArea#responsivePageScroll {
    border: 0;
    background: transparent;
}
QScrollArea#responsivePageScroll > QWidget > QWidget {
    background: transparent;
}
QMainWindow,
QDialog,
QWidget#downloadsTab,
QWidget#historyTab,
QWidget#preferencesTab,
QWidget#settingsTab,
QWidget#downloadsScrollContent,
QWidget#preferencesScrollContent,
QWidget#settingsScrollContent {
    background-color: #F2F3F5;
    color: #202328;
}
QTabWidget::pane { border: 0; top: -1px; }
QTabBar::tab {
    background-color: #E3E5E8;
    color: #262A2F;
    border: 1px solid #CACED3;
    padding: 8px 17px;
    min-width: 86px;
}
QTabBar::tab:selected {
    background-color: #34C759;
    color: #FFFFFF;
    border-color: #34C759;
    font-weight: 700;
}
QTabBar::tab:hover:!selected { background-color: #D9DCE0; }
QLabel, QCheckBox { background: transparent; color: #202328; }
QGroupBox {
    background-color: #FFFFFF;
    color: #202328;
    border: 1px solid #C8CDD3;
    border-radius: 10px;
    margin-top: 24px;
    padding: 12px 10px 10px 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 2px;
    padding: 0 7px;
    background: transparent;
    color: #202328;
    font-weight: 700;
}
QLineEdit, QPlainTextEdit, QListWidget, QTableWidget, QComboBox, QAbstractSpinBox {
    background-color: #FFFFFF;
    color: #202328;
    border: 1px solid #BFC5CC;
    border-radius: 6px;
    padding: 5px 7px;
    selection-background-color: #C9F0D2;
    selection-color: #17331D;
}
QAbstractSpinBox { padding-right: 24px; }
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
    subcontrol-origin: border;
    width: 20px;
    background-color: #E7E9EC;
    border-left: 1px solid #C1C6CC;
}
QAbstractSpinBox::up-button { subcontrol-position: top right; border-top-right-radius: 5px; }
QAbstractSpinBox::down-button { subcontrol-position: bottom right; border-bottom-right-radius: 5px; }

QToolButton#spinStepButton {
    background-color: #E1E5E9;
    color: #22282E;
    border: 0;
    border-left: 1px solid #B9C0C7;
    border-radius: 0;
    padding: 0;
    margin: 0;
    font-size: 8px;
    font-weight: 900;
}
QToolButton#spinStepButton[stepDirection="up"] {
    border-top-right-radius: 5px;
    border-bottom: 1px solid #B9C0C7;
}
QToolButton#spinStepButton[stepDirection="down"] {
    border-bottom-right-radius: 5px;
}
QToolButton#spinStepButton:hover { background-color: #D2D8DE; }
QToolButton#spinStepButton:pressed { background-color: #C6CDD4; }
QToolButton#spinStepButton:disabled {
    background-color: #ECEEF0;
    color: #9CA3AA;
}
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #9AA1A9;
    border-radius: 4px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked { background-color: #34C759; border-color: #34C759; }
QTableWidget { gridline-color: #D5D9DD; }
QHeaderView::section {
    background-color: #E8EAED;
    color: #25292E;
    padding: 7px;
    border: 0;
    border-right: 1px solid #D2D6DB;
}
QPushButton {
    background-color: #FFFFFF;
    color: #202328;
    border: 1px solid #BDC3CA;
    border-radius: 7px;
    padding: 7px 12px;
}
QPushButton:hover { background-color: #F4F5F6; }
QPushButton:pressed { background-color: #E6E8EB; }
QPushButton:disabled { background-color: #E8EAED; color: #969DA5; border-color: #D2D6DB; }
QProgressBar {
    background-color: #FFFFFF;
    color: #202328;
    border: 1px solid #BFC5CC;
    border-radius: 5px;
    text-align: center;
}
QProgressBar::chunk { background-color: #34C759; border-radius: 4px; }
QToolTip { background-color: #FFFFFF; color: #202328; border: 1px solid #BFC5CC; }
""" + GREEN_BUTTON_STYLE + HISTORY_DARK_TABLE_STYLE


from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import (
    QEvent,
    QObject,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QWidget,
)

from clipfetch.config.constants import (
    DEFAULT_LANGUAGE,
    LEGACY_LANGUAGE_ALIASES,
)


@dataclass(frozen=True)
class LanguageInfo:
    code: str
    name: str
    native_name: str
    date_format: str = "dd/MM/yyyy"
    datetime_format: str = "dd/MM/yyyy HH:mm"


def locales_directory() -> Path:
    """Return locale files next to this module in source and bundled builds."""
    return (
        Path(__file__)
        .resolve()
        .parent
        / "locales"
    )


class TranslationManager:
    """Load JSON locale packs and expose stable translation primitives."""

    def __init__(self):
        self._language = (
            DEFAULT_LANGUAGE
        )
        self._catalogs = {}
        self.reload_catalogs()

    def reload_catalogs(self):
        catalogs = {}
        directory = (
            locales_directory()
        )

        if directory.is_dir():
            for path in sorted(
                directory.glob("*.json")
            ):
                try:
                    data = json.loads(
                        path.read_text(
                            encoding="utf-8"
                        )
                    )
                except (
                    OSError,
                    json.JSONDecodeError,
                ):
                    continue

                meta = (
                    data.get("meta")
                    or {}
                )

                code = str(
                    meta.get("code")
                    or path.stem
                ).strip()

                if code:
                    catalogs[code] = data

        if (
            DEFAULT_LANGUAGE
            not in catalogs
        ):
            catalogs[
                DEFAULT_LANGUAGE
            ] = {
                "meta": {
                    "code": (
                        DEFAULT_LANGUAGE
                    ),
                    "name": (
                        "Portuguese (Brazil)"
                    ),
                    "native_name": (
                        "Português (Brasil)"
                    ),
                    "date_format": (
                        "dd/MM/yyyy"
                    ),
                    "datetime_format": (
                        "dd/MM/yyyy HH:mm"
                    ),
                },
                "strings": {},
                "replacements": {},
            }

        self._catalogs = catalogs

    def normalize_language(
        self,
        value,
    ):
        text = str(
            value
            or ""
        ).strip()

        if text in self._catalogs:
            return text

        alias = (
            LEGACY_LANGUAGE_ALIASES
            .get(text)
        )

        if (
            alias
            in self._catalogs
        ):
            return alias

        folded = (
            text.casefold()
        )

        for (
            code,
            catalog,
        ) in self._catalogs.items():
            meta = (
                catalog.get("meta")
                or {}
            )

            names = {
                str(
                    meta.get("name")
                    or ""
                ).casefold(),
                str(
                    meta.get(
                        "native_name"
                    )
                    or ""
                ).casefold(),
            }

            if folded in names:
                return code

        return DEFAULT_LANGUAGE

    def set_language(
        self,
        value,
    ):
        self._language = (
            self.normalize_language(
                value
            )
        )

        return self._language

    def language_info(
        self,
        code=None,
    ):
        normalized = (
            self.normalize_language(
                self._language
                if code is None
                else code
            )
        )

        meta = (
            self._catalogs
            .get(
                normalized,
                {},
            )
            .get(
                "meta",
                {},
            )
        )

        return LanguageInfo(
            code=normalized,
            name=str(
                meta.get("name")
                or normalized
            ),
            native_name=str(
                meta.get("native_name")
                or meta.get("name")
                or normalized
            ),
            date_format=str(
                meta.get("date_format")
                or "dd/MM/yyyy"
            ),
            datetime_format=str(
                meta.get(
                    "datetime_format"
                )
                or "dd/MM/yyyy HH:mm"
            ),
        )

    def available_languages(self):
        infos = [
            self.language_info(code)
            for code
            in self._catalogs
        ]

        return sorted(
            infos,
            key=lambda item: (
                0
                if item.code
                == DEFAULT_LANGUAGE
                else 1,
                item.native_name.casefold(),
            ),
        )

    def translate(
        self,
        text,
        *,
        replacements=True,
        **values,
    ):
        source = str(
            text
            if text is not None
            else ""
        )

        if not source:
            return source

        translated = source

        if (
            self._language
            != DEFAULT_LANGUAGE
        ):
            catalog = (
                self._catalogs.get(
                    self._language
                )
                or {}
            )

            strings = (
                catalog.get(
                    "strings"
                )
                or {}
            )

            translated = str(
                strings.get(
                    source,
                    source,
                )
            )

            if (
                translated == source
                and replacements
            ):
                rules = (
                    catalog.get(
                        "replacements"
                    )
                    or {}
                )

                for old in sorted(
                    rules,
                    key=len,
                    reverse=True,
                ):
                    if old in translated:
                        translated = (
                            translated.replace(
                                old,
                                str(
                                    rules[old]
                                ),
                            )
                        )

        if values:
            try:
                translated = (
                    translated.format(
                        **values
                    )
                )
            except (
                KeyError,
                ValueError,
                IndexError,
            ):
                pass

        return translated


_manager = TranslationManager()
_filter = None


def set_language(
    value,
):
    return (
        _manager.set_language(
            value
        )
    )


def available_languages():
    return (
        _manager
        .available_languages()
    )


def date_display_format():
    return (
        _manager
        .language_info()
        .date_format
    )


def datetime_display_format():
    return (
        _manager
        .language_info()
        .datetime_format
    )


def tr(
    text,
    **values,
):
    return (
        _manager.translate(
            text,
            replacements=True,
            **values,
        )
    )


def combo_value(
    combo,
):
    data = combo.currentData()

    return (
        data
        if data is not None
        else combo.currentText()
    )


def set_combo_value(
    combo,
    value,
):
    for index in range(
        combo.count()
    ):
        if (
            combo.itemData(index)
            == value
        ):
            combo.setCurrentIndex(
                index
            )
            return True

    index = combo.findText(
        str(value)
    )

    if index >= 0:
        combo.setCurrentIndex(
            index
        )
        return True

    return False


def _source(
    obj,
    name,
    current,
):
    property_name = (
        "_i18n_source_"
        + name
    )

    value = obj.property(
        property_name
    )

    if value is None:
        value = str(
            current
            if current is not None
            else ""
        )

        obj.setProperty(
            property_name,
            value,
        )

    return str(value)


def _translate_combo(
    combo,
    replacements=False,
):
    if combo.property(
        "_i18n_skip_combo"
    ):
        return

    sources = combo.property(
        "_i18n_combo_sources"
    )

    if (
        not isinstance(
            sources,
            list,
        )
        or len(sources)
        != combo.count()
    ):
        sources = [
            combo.itemText(index)
            for index
            in range(
                combo.count()
            )
        ]

        combo.setProperty(
            "_i18n_combo_sources",
            sources,
        )

        for (
            index,
            source,
        ) in enumerate(sources):
            if (
                combo.itemData(index)
                is None
            ):
                combo.setItemData(
                    index,
                    source,
                )

    blocked = (
        combo.blockSignals(
            True
        )
    )

    try:
        for (
            index,
            source,
        ) in enumerate(sources):
            combo.setItemText(
                index,
                _manager.translate(
                    source,
                    replacements=(
                        replacements
                    ),
                ),
            )

    finally:
        combo.blockSignals(
            blocked
        )


def translate_widget_tree(
    root,
    replacements=False,
):
    """Translate an existing widget tree while retaining canonical source text."""

    widgets = [
        root,
        *root.findChildren(
            QWidget
        ),
    ]

    for widget in widgets:
        if (
            hasattr(
                widget,
                "windowTitle",
            )
            and hasattr(
                widget,
                "setWindowTitle",
            )
        ):
            current = (
                widget.windowTitle()
            )

            if current:
                source = _source(
                    widget,
                    "window_title",
                    current,
                )

                widget.setWindowTitle(
                    _manager.translate(
                        source,
                        replacements=(
                            replacements
                        ),
                    )
                )

        if isinstance(
            widget,
            QGroupBox,
        ):
            source = _source(
                widget,
                "group_title",
                widget.title(),
            )

            widget.setTitle(
                _manager.translate(
                    source,
                    replacements=(
                        replacements
                    ),
                )
            )

        elif isinstance(
            widget,
            (
                QLabel,
                QPushButton,
                QCheckBox,
            ),
        ):
            source = _source(
                widget,
                "text",
                widget.text(),
            )

            widget.setText(
                _manager.translate(
                    source,
                    replacements=(
                        replacements
                    ),
                )
            )

        if (
            isinstance(
                widget,
                (
                    QLineEdit,
                    QPlainTextEdit,
                ),
            )
            and widget.placeholderText()
        ):
            source = _source(
                widget,
                "placeholder",
                widget.placeholderText(),
            )

            widget.setPlaceholderText(
                _manager.translate(
                    source,
                    replacements=(
                        replacements
                    ),
                )
            )

        if (
            hasattr(
                widget,
                "toolTip",
            )
            and hasattr(
                widget,
                "setToolTip",
            )
            and widget.toolTip()
        ):
            source = _source(
                widget,
                "tooltip",
                widget.toolTip(),
            )

            widget.setToolTip(
                _manager.translate(
                    source,
                    replacements=(
                        replacements
                    ),
                )
            )

        if isinstance(
            widget,
            QComboBox,
        ):
            _translate_combo(
                widget,
                replacements,
            )

        if isinstance(
            widget,
            QTabWidget,
        ):
            sources = widget.property(
                "_i18n_tab_sources"
            )

            if (
                not isinstance(
                    sources,
                    list,
                )
                or len(sources)
                != widget.count()
            ):
                sources = [
                    widget.tabText(index)
                    for index
                    in range(
                        widget.count()
                    )
                ]

                widget.setProperty(
                    "_i18n_tab_sources",
                    sources,
                )

            for (
                index,
                source,
            ) in enumerate(sources):
                widget.setTabText(
                    index,
                    _manager.translate(
                        source,
                        replacements=(
                            replacements
                        ),
                    ),
                )

        if isinstance(
            widget,
            QTableWidget,
        ):
            sources = widget.property(
                "_i18n_header_sources"
            )

            if (
                not isinstance(
                    sources,
                    list,
                )
                or len(sources)
                != widget.columnCount()
            ):
                sources = []

                for column in range(
                    widget.columnCount()
                ):
                    item = (
                        widget
                        .horizontalHeaderItem(
                            column
                        )
                    )

                    sources.append(
                        item.text()
                        if item
                        else ""
                    )

                widget.setProperty(
                    "_i18n_header_sources",
                    sources,
                )

            for (
                column,
                source,
            ) in enumerate(sources):
                item = (
                    widget
                    .horizontalHeaderItem(
                        column
                    )
                )

                if item:
                    item.setText(
                        _manager.translate(
                            source,
                            replacements=(
                                replacements
                            ),
                        )
                    )


class TranslatableStatusBar(
    QStatusBar
):
    """Transient status bar that stays hidden when no message is active."""

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.setSizeGripEnabled(
            False
        )

        self.messageChanged.connect(
            self._sync_visibility
        )

        self.hide()

    def _sync_visibility(
        self,
        message,
    ):
        self.setVisible(
            bool(
                str(
                    message
                    or ""
                ).strip()
            )
        )

    def showMessage(
        self,
        message,
        timeout=0,
    ):
        text = tr(
            message
        )

        if not text:
            self.clearMessage()
            return

        effective_timeout = (
            int(timeout)
            if timeout
            else 4500
        )

        self.show()

        super().showMessage(
            text,
            effective_timeout,
        )

    def clearMessage(self):
        super().clearMessage()
        self.hide()


class TranslationEventFilter(
    QObject
):
    def eventFilter(
        self,
        watched,
        event,
    ):
        if (
            event.type()
            == QEvent.Type.Show
            and isinstance(
                watched,
                QWidget,
            )
        ):
            translate_widget_tree(
                watched,
                replacements=(
                    watched.isWindow()
                    or isinstance(
                        watched,
                        QMessageBox,
                    )
                ),
            )

        return (
            super()
            .eventFilter(
                watched,
                event,
            )
        )


def install_translation_filter(
    application,
):
    global _filter

    if (
        application is None
        or _filter is not None
    ):
        return

    _filter = (
        TranslationEventFilter(
            application
        )
    )

    application.installEventFilter(
        _filter
    )

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.resources.style import load_stylesheet
from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class LabeledRow(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("DashboardCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        label = QLabel(title)
        label.setObjectName("DashboardSectionTitle")
        layout.addWidget(label)
        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        layout.addLayout(self.body)


class SettingsScreen(QWidget):
    logged_out = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Настройки")
        title.setObjectName("TitleLabel")

        layout.addWidget(title)
        layout.addWidget(self._build_theme_block())
        layout.addWidget(self._build_background_block())
        layout.addWidget(self._build_consent_block())
        layout.addWidget(self._build_session_block())
        layout.addStretch(1)

    def _build_theme_block(self) -> QWidget:
        block = LabeledRow("Оформление")
        self.theme_select = QComboBox()
        self.theme_select.addItem("Светлая", "light")
        self.theme_select.addItem("Темная", "dark")
        self.theme_select.addItem("iOS26", "ios")
        self.theme_select.currentIndexChanged.connect(self._apply_theme)

        block.body.addWidget(QLabel("Тема"))
        block.body.addWidget(self.theme_select)
        return block

    def _build_background_block(self) -> QWidget:
        block = LabeledRow("Фон приложения")
        self.background_label = QLabel("Фон не выбран")
        self.background_label.setObjectName("Muted")
        self.background_button = QPushButton("Выбрать фон")
        self.background_button.clicked.connect(self._pick_background)
        self.background_clear = QPushButton("Сбросить фон")
        self.background_clear.setObjectName("SecondaryButton")
        self.background_clear.clicked.connect(self._clear_background)

        block.body.addWidget(self.background_label)
        block.body.addWidget(self.background_button)
        block.body.addWidget(self.background_clear)
        return block

    def _build_consent_block(self) -> QWidget:
        block = LabeledRow("Согласие и приватность")
        self.consent_status = QLabel("")
        self.consent_status.setObjectName("Muted")
        self.consent_button = QPushButton("Показать согласие")
        self.consent_button.clicked.connect(self._accept_consent)
        block.body.addWidget(self.consent_status)
        block.body.addWidget(self.consent_button)
        return block

    def _build_session_block(self) -> QWidget:
        block = LabeledRow("Сессия")
        row = QHBoxLayout()
        self.logout_button = QPushButton("Выйти из аккаунта")
        self.logout_button.clicked.connect(self._logout)
        row.addWidget(self.logout_button)
        row.addStretch(1)
        block.body.addLayout(row)
        return block

    def refresh_settings(self) -> None:
        self._load_theme()
        self._load_background()

        self._refresh_consent()

    def _refresh_consent(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            self.consent_status.setText("Выберите организацию")
            return
        try:
            status = api_client.get_consent_status(org_id)
            if status.get("accepted"):
                self.consent_status.setText("Согласие получено")
                self.consent_button.setText("Показать согласие")
            else:
                self.consent_status.setText("Требуется согласие")
                self.consent_button.setText("Дать согласие")
        except ApiError:
            self.consent_status.setText("Не удалось проверить согласие")

    def _accept_consent(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            self.consent_status.setText("Выберите организацию")
            return
        try:
            api_client.accept_consent(org_id, policy_version="v1")
            self.consent_status.setText("Согласие сохранено")
        except ApiError as exc:
            self.consent_status.setText(f"Ошибка согласия: {exc}")

    def _load_theme(self) -> None:
        theme = session_store.theme
        index = self.theme_select.findData(theme)
        if index >= 0:
            self.theme_select.setCurrentIndex(index)

    def _apply_theme(self) -> None:
        theme = self.theme_select.currentData()
        session_store.theme = theme
        app = QApplication.instance()
        if not app:
            return
        stylesheet = load_stylesheet(theme, session_store.background_path)
        app.setStyleSheet(stylesheet)

    def _load_background(self) -> None:
        if session_store.background_path:
            self.background_label.setText(session_store.background_path)
        else:
            self.background_label.setText("Фон не выбран")

    def _pick_background(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать фон",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            return
        session_store.background_path = file_path
        self.background_label.setText(file_path)
        self._apply_theme()

    def _clear_background(self) -> None:
        session_store.background_path = None
        self.background_label.setText("Фон не выбран")
        self._apply_theme()

    def _logout(self) -> None:
        session_store.clear()
        self.logged_out.emit()

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
        layout.addWidget(self._build_session_block())
        layout.addStretch(1)

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
        pass

    def _logout(self) -> None:
        session_store.clear()
        self.logged_out.emit()

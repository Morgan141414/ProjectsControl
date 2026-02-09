from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class ConsentScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Согласие и приватность")
        title.setObjectName("TitleLabel")

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        card = QFrame()
        card.setObjectName("DashboardCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        body = QTextEdit()
        body.setReadOnly(True)
        body.setObjectName("DashboardInput")
        body.setText(
            "Мы собираем данные активности только для расчёта KPI и улучшения процессов.\n"
            "Никакие личные переписки или приватные данные не анализируются.\n\n"
            "Что фиксируется:\n"
            "- активность мыши/клавиатуры и периоды простоя;\n"
            "- время в приложениях и сайтах (по категориям);\n"
            "- задачи и результаты работы.\n\n"
            "Вы всегда можете запросить выгрузку или корректировку данных."
        )

        self.accept_button = QPushButton("Я согласен")
        self.accept_button.clicked.connect(self.accept_consent)

        card_layout.addWidget(body)
        card_layout.addWidget(self.accept_button)

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(card)
        layout.addStretch(1)

    def refresh_status(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            self.status_label.setText("Сначала выберите организацию")
            return

        try:
            status = api_client.get_consent_status(org_id)
            if status.get("accepted"):
                self.status_label.setText("Согласие получено")
                self.accept_button.setEnabled(False)
            else:
                self.status_label.setText("Нужно подтверждение согласия")
                self.accept_button.setEnabled(True)
        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка: {exc}")

    def accept_consent(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            self.status_label.setText("Сначала выберите организацию")
            return

        self.accept_button.setEnabled(False)
        try:
            api_client.accept_consent(org_id, policy_version="v1")
            self.status_label.setText("Согласие сохранено")
        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
            self.accept_button.setEnabled(True)


class ConsentDialog(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Согласие и приватность")
        self.setModal(True)
        self.resize(520, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Согласие и приватность")
        title.setObjectName("TitleLabel")

        body = QTextEdit()
        body.setReadOnly(True)
        body.setObjectName("DashboardInput")
        body.setText(
            "Мы собираем данные активности только для расчёта KPI и улучшения процессов.\n"
            "Никакие личные переписки или приватные данные не анализируются.\n\n"
            "Что фиксируется:\n"
            "- активность мыши/клавиатуры и периоды простоя;\n"
            "- время в приложениях и сайтах (по категориям);\n"
            "- задачи и результаты работы.\n\n"
            "Вы всегда можете запросить выгрузку или корректировку данных."
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        self.accept_button = QPushButton("Я согласен")
        self.accept_button.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(self.status_label)
        layout.addWidget(self.accept_button)

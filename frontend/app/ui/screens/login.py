from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class LoginScreen(QWidget):
    login_success = Signal()

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        title = QLabel("Welcome back")
        title.setObjectName("TitleLabel")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        self.login_button = QPushButton("Login")
        self.login_button.clicked.connect(self.handle_login)

        card_layout.addWidget(title)
        card_layout.addWidget(self.email_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.login_button)

        layout.addWidget(card)
        layout.addStretch(1)

    def handle_login(self) -> None:
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        if not email or not password:
            self.status_label.setText("Enter email and password")
            return

        self.login_button.setEnabled(False)
        try:
            token = api_client.login(email, password)
            session_store.set_token(token)
            self.status_label.setText("Login ok")
            self.login_success.emit()
        except ApiError as exc:
            self.status_label.setText(f"Login failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Login failed: {exc}")
        finally:
            self.login_button.setEnabled(True)

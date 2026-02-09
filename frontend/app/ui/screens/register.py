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


class RegisterScreen(QWidget):
    register_success = Signal()

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

        title = QLabel("Create account")
        title.setObjectName("TitleLabel")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Full name")

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password (min 8)")
        self.password_input.setEchoMode(QLineEdit.Password)

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        self.register_button = QPushButton("Register")
        self.register_button.clicked.connect(self.handle_register)

        card_layout.addWidget(title)
        card_layout.addWidget(self.name_input)
        card_layout.addWidget(self.email_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.register_button)

        layout.addWidget(card)
        layout.addStretch(1)

    def handle_register(self) -> None:
        full_name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text().strip()
        if not full_name or not email or not password:
            self.status_label.setText("Fill all fields")
            return

        self.register_button.setEnabled(False)
        try:
            api_client.register(email=email, password=password, full_name=full_name)
            self.status_label.setText("Account created. Please login.")
            self.register_success.emit()
        except ApiError as exc:
            self.status_label.setText(f"Registration failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Registration failed: {exc}")
        finally:
            self.register_button.setEnabled(True)

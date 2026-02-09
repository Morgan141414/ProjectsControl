from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class ProfileScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Профиль")
        title.setObjectName("TitleLabel")

        card = QFrame()
        card.setObjectName("DashboardCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(10)

        self.profile_name = QLineEdit()
        self.profile_name.setPlaceholderText("ФИО")

        self.profile_patronymic = QLineEdit()
        self.profile_patronymic.setPlaceholderText("Отчество")

        self.profile_bio = QTextEdit()
        self.profile_bio.setPlaceholderText("О себе")
        self.profile_bio.setFixedHeight(90)
        self.profile_bio.setObjectName("DashboardInput")

        self.profile_specialty = QLineEdit()
        self.profile_specialty.setPlaceholderText("Специальность")

        self.profile_socials = QLineEdit()
        self.profile_socials.setPlaceholderText("Ссылки на соцсети")

        self.profile_status = QLabel("")
        self.profile_status.setObjectName("Muted")

        self.profile_save = QPushButton("Сохранить профиль")
        self.profile_save.clicked.connect(self._save_profile)

        card_layout.addWidget(self.profile_name)
        card_layout.addWidget(self.profile_patronymic)
        card_layout.addWidget(self.profile_bio)
        card_layout.addWidget(self.profile_specialty)
        card_layout.addWidget(self.profile_socials)
        card_layout.addWidget(self.profile_status)
        card_layout.addWidget(self.profile_save)

        layout.addWidget(title)
        layout.addWidget(card)
        layout.addStretch(1)

    def refresh_profile(self) -> None:
        if not session_store.token:
            return
        self.profile_status.setText("")
        try:
            profile = api_client.get_me()
            self.profile_name.setText(profile.get("full_name") or "")
            self.profile_patronymic.setText(profile.get("patronymic") or "")
            self.profile_bio.setText(profile.get("bio") or "")
            self.profile_specialty.setText(profile.get("specialty") or "")
            self.profile_socials.setText(profile.get("socials_json") or "")
        except ApiError:
            self.profile_status.setText("Не удалось загрузить профиль")

    def _save_profile(self) -> None:
        payload = {
            "full_name": self.profile_name.text().strip() or None,
            "patronymic": self.profile_patronymic.text().strip() or None,
            "bio": self.profile_bio.toPlainText().strip() or None,
            "specialty": self.profile_specialty.text().strip() or None,
            "socials_json": self.profile_socials.text().strip() or None,
        }
        self.profile_save.setEnabled(False)
        try:
            profile = api_client.update_me(payload)
            session_store.set_user_profile(
                profile.get("id"),
                profile.get("full_name"),
                profile.get("patronymic"),
            )
            self.profile_status.setText("Профиль обновлен")
        except ApiError as exc:
            self.profile_status.setText(f"Ошибка профиля: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.profile_status.setText(f"Ошибка профиля: {exc}")
        finally:
            self.profile_save.setEnabled(True)

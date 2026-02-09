import os
from pathlib import Path

import httpx
from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedLayout,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from google_auth_oauthlib.flow import InstalledAppFlow

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class AuthScreen(QWidget):
    auth_success = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._load_env_file()

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        hero = QFrame()
        hero.setObjectName("AuthHero")
        hero_stack = QStackedLayout(hero)
        hero_stack.setContentsMargins(0, 0, 0, 0)
        hero_stack.setStackingMode(QStackedLayout.StackAll)

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("AuthVideo")
        hero_stack.addWidget(self.video_widget)

        hero_overlay = QFrame()
        hero_overlay.setObjectName("AuthOverlay")
        hero_overlay_layout = QVBoxLayout(hero_overlay)
        hero_overlay_layout.setContentsMargins(48, 48, 48, 48)
        hero_overlay_layout.setSpacing(12)

        hero_title = QLabel("ProjectsControl")
        hero_title.setObjectName("HeroTitle")
        hero_subtitle = QLabel("Контроль продуктивности и проектов")
        hero_subtitle.setObjectName("HeroSubtitle")
        hero_note = QLabel("Работайте спокойно. Мы поможем держать фокус.")
        hero_note.setObjectName("HeroNote")

        hero_overlay_layout.addWidget(hero_title)
        hero_overlay_layout.addWidget(hero_subtitle)
        hero_overlay_layout.addWidget(hero_note)
        hero_overlay_layout.addStretch(1)

        hero_stack.addWidget(hero_overlay)

        card = QFrame()
        card.setObjectName("AuthCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(32, 32, 32, 32)
        card_layout.setSpacing(16)

        self.card_title = QLabel("Добро пожаловать!")
        self.card_title.setObjectName("AuthTitle")
        self.card_subtitle = QLabel("Авторизуйтесь, чтобы продолжить")
        self.card_subtitle.setObjectName("AuthSubtitle")

        toggle_row = QHBoxLayout()
        self.login_toggle = QPushButton("Вход")
        self.register_toggle = QPushButton("Регистрация")
        for toggle in (self.login_toggle, self.register_toggle):
            toggle.setCheckable(True)
            toggle.setCursor(Qt.PointingHandCursor)
            toggle.setObjectName("AuthToggle")
        self.login_toggle.setChecked(True)

        self.login_toggle.clicked.connect(lambda: self._show_panel(0))
        self.register_toggle.clicked.connect(lambda: self._show_panel(1))

        toggle_row.addWidget(self.login_toggle)
        toggle_row.addWidget(self.register_toggle)

        self.stack = QStackedWidget()
        self.login_panel = self._build_login_panel()
        self.register_panel = self._build_register_panel()
        self.stack.addWidget(self.login_panel)
        self.stack.addWidget(self.register_panel)

        card_layout.addWidget(self.card_title)
        card_layout.addWidget(self.card_subtitle)
        card_layout.addLayout(toggle_row)
        card_layout.addWidget(self.stack)

        root_layout.addWidget(hero, 3)
        root_layout.addWidget(card, 2)

        self.google_worker: OAuthWorker | None = None
        self.google_thread: QThread | None = None

        self.video_player: QMediaPlayer | None = None
        self.video_audio: QAudioOutput | None = None
        self._setup_video()

        self._show_panel(0)

    def _build_login_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.login_email_input = QLineEdit()
        self.login_email_input.setPlaceholderText("Email")

        self.login_password_input = QLineEdit()
        self.login_password_input.setPlaceholderText("Пароль")
        self.login_password_input.setEchoMode(QLineEdit.Password)

        self.login_status_label = QLabel("")
        self.login_status_label.setObjectName("Muted")

        self.login_button = QPushButton("Войти")
        self.login_button.clicked.connect(self.handle_login)

        self.google_button = QPushButton("Войти через Google")
        self.google_button.setObjectName("SecondaryButton")
        self.google_button.clicked.connect(self.handle_google_login)

        self.switch_to_register = QPushButton("Нет аккаунта? Зарегистрироваться")
        self.switch_to_register.setObjectName("LinkButton")
        self.switch_to_register.clicked.connect(lambda: self._show_panel(1))

        layout.addWidget(self.login_email_input)
        layout.addWidget(self.login_password_input)
        layout.addWidget(self.login_status_label)
        layout.addWidget(self.login_button)
        layout.addWidget(self.google_button)
        layout.addWidget(self.switch_to_register)

        return panel

    def _build_register_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.register_name_input = QLineEdit()
        self.register_name_input.setPlaceholderText("Имя и фамилия")

        self.register_email_input = QLineEdit()
        self.register_email_input.setPlaceholderText("Email")

        self.register_password_input = QLineEdit()
        self.register_password_input.setPlaceholderText("Пароль (минимум 8 символов)")
        self.register_password_input.setEchoMode(QLineEdit.Password)

        self.register_status_label = QLabel("")
        self.register_status_label.setObjectName("Muted")

        self.register_button = QPushButton("Создать аккаунт")
        self.register_button.clicked.connect(self.handle_register)

        self.switch_to_login = QPushButton("Уже есть аккаунт? Войти")
        self.switch_to_login.setObjectName("LinkButton")
        self.switch_to_login.clicked.connect(lambda: self._show_panel(0))

        layout.addWidget(self.register_name_input)
        layout.addWidget(self.register_email_input)
        layout.addWidget(self.register_password_input)
        layout.addWidget(self.register_status_label)
        layout.addWidget(self.register_button)
        layout.addWidget(self.switch_to_login)

        return panel

    def _show_panel(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.login_toggle.setChecked(index == 0)
        self.register_toggle.setChecked(index == 1)
        if index == 0:
            self.card_title.setText("Добро пожаловать!")
            self.card_subtitle.setText("Введите данные для входа")
        else:
            self.card_title.setText("Создайте аккаунт")
            self.card_subtitle.setText("Это займет меньше минуты")

    def _setup_video(self) -> None:
        source = self._resolve_video_source()
        if not source:
            self.video_widget.setVisible(False)
            return

        self.video_player = QMediaPlayer()
        self.video_audio = QAudioOutput()
        self.video_audio.setMuted(True)
        self.video_player.setAudioOutput(self.video_audio)
        self.video_player.setVideoOutput(self.video_widget)
        self.video_player.setSource(source)
        self.video_player.mediaStatusChanged.connect(self._loop_video)
        self.video_player.play()

    def _resolve_video_source(self) -> QUrl | None:
        raw = os.getenv("LOGIN_VIDEO_PATH")
        if raw:
            return QUrl.fromUserInput(raw)

        default_path = Path(__file__).resolve().parents[2] / "resources" / "login_bg.mp4"
        if default_path.exists():
            return QUrl.fromLocalFile(str(default_path))
        return None

    def _loop_video(self, status) -> None:
        if status == QMediaPlayer.EndOfMedia and self.video_player:
            self.video_player.setPosition(0)
            self.video_player.play()
        if status == QMediaPlayer.InvalidMedia:
            self.video_widget.setVisible(False)

    def handle_login(self) -> None:
        email = self.login_email_input.text().strip()
        password = self.login_password_input.text().strip()
        if not email or not password:
            self.login_status_label.setText("Введите email и пароль")
            return

        self.login_button.setEnabled(False)
        try:
            token = api_client.login(email, password)
            session_store.set_token(token)
            try:
                profile = api_client.get_me()
                session_store.set_user_profile(
                    profile.get("id"),
                    profile.get("full_name"),
                    profile.get("patronymic"),
                )
            except ApiError:
                session_store.set_user_profile(None, None, None)
            self.login_status_label.setText("Вход выполнен")
            self.auth_success.emit()
        except ApiError as exc:
            self.login_status_label.setText(f"Ошибка входа: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.login_status_label.setText(f"Ошибка входа: {exc}")
        finally:
            self.login_button.setEnabled(True)

    def handle_register(self) -> None:
        full_name = self.register_name_input.text().strip()
        email = self.register_email_input.text().strip()
        password = self.register_password_input.text().strip()
        if not full_name or not email or not password:
            self.register_status_label.setText("Заполните все поля")
            return

        self.register_button.setEnabled(False)
        try:
            api_client.register(email=email, password=password, full_name=full_name)
            self.register_status_label.setText("Аккаунт создан. Войдите.")
            self.register_name_input.clear()
            self.register_email_input.clear()
            self.register_password_input.clear()
            self._show_panel(0)
        except ApiError as exc:
            self.register_status_label.setText(f"Ошибка регистрации: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.register_status_label.setText(f"Ошибка регистрации: {exc}")
        finally:
            self.register_button.setEnabled(True)

    def handle_google_login(self) -> None:
        self._load_env_file()
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            self.login_status_label.setText(
                "Нет GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET в frontend/.env"
            )
            return

        if self.google_thread and self.google_thread.isRunning():
            self.login_status_label.setText("OAuth уже запущен")
            return

        self.google_button.setEnabled(False)
        self.login_status_label.setText("Открываем браузер для входа...")

        self.google_worker = OAuthWorker(client_id=client_id, client_secret=client_secret)
        self.google_thread = QThread()
        self.google_worker.moveToThread(self.google_thread)

        self.google_thread.started.connect(self.google_worker.run)
        self.google_worker.finished.connect(self._on_google_finished)
        self.google_worker.finished.connect(self.google_thread.quit)
        self.google_worker.finished.connect(self.google_worker.deleteLater)
        self.google_thread.finished.connect(self.google_thread.deleteLater)

        self.google_thread.start()

    def _on_google_finished(self, profile: dict, error: str) -> None:
        if error:
            self.login_status_label.setText(f"OAuth ошибка: {error}")
            self.google_button.setEnabled(True)
            return

        email = profile.get("email", "")
        name = profile.get("name", "")
        id_token = profile.get("id_token")
        if email:
            self.login_email_input.setText(email)
            self.register_email_input.setText(email)
        if name and not self.register_name_input.text().strip():
            self.register_name_input.setText(name)

        if not id_token:
            self.login_status_label.setText(
                "Google OAuth выполнен, но id_token не получен"
            )
            self.google_button.setEnabled(True)
            return

        try:
            token = api_client.google_login(id_token)
            session_store.set_token(token)
            try:
                profile = api_client.get_me()
                session_store.set_user_profile(
                    profile.get("id"),
                    profile.get("full_name"),
                    profile.get("patronymic"),
                )
            except ApiError:
                session_store.set_user_profile(None, None, None)
            self.login_status_label.setText("Вход через Google выполнен")
            self.auth_success.emit()
        except ApiError as exc:
            self.login_status_label.setText(f"Ошибка Google входа: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.login_status_label.setText(f"Ошибка Google входа: {exc}")
        finally:
            self.google_button.setEnabled(True)

    def _load_env_file(self) -> None:
        env_path = Path(__file__).resolve().parents[3] / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


class OAuthWorker(QObject):
    finished = Signal(dict, str)

    def __init__(self, client_id: str, client_secret: str) -> None:
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret

    @Slot()
    def run(self) -> None:
        try:
            config = {
                "installed": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": (
                        "https://www.googleapis.com/oauth2/v1/certs"
                    ),
                    "redirect_uris": ["http://localhost"],
                }
            }
            flow = InstalledAppFlow.from_client_config(
                config,
                scopes=[
                    "openid",
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile",
                ],
            )
            creds = flow.run_local_server(port=0, prompt="consent")
            profile = self._fetch_profile(creds.token)
            if creds.id_token:
                profile["id_token"] = creds.id_token
            self.finished.emit(profile, "")
        except Exception as exc:  # noqa: BLE001
            self.finished.emit({}, str(exc))

    def _fetch_profile(self, access_token: str) -> dict:
        response = httpx.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

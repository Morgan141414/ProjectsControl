import os
from pathlib import Path

import httpx
from PySide6.QtCore import (
    QByteArray,
    QObject,
    QSize,
    Qt,
    QThread,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtSvg import QSvgRenderer

    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

from google_auth_oauthlib.flow import InstalledAppFlow

from app.services.api_client import ApiError, api_client
from app.state.session import session_store

# ── SVG icon data ─────────────────────────────────────────────────────

_GOOGLE_SVG = (
    '<svg viewBox="0 0 48 48">'
    '<path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85'
    "C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19"
    'C12.43 13.72 17.74 9.5 24 9.5z"/>'
    '<path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02'
    "h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36"
    ' 7.09-17.65z"/>'
    '<path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27'
    "-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54"
    ' 2.56 10.78l7.97-6.19z"/>'
    '<path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6'
    "c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98"
    ' 6.19C6.51 42.62 14.62 48 24 48z"/>'
    "</svg>"
)


def _svg_icon(svg_data: str, size: int = 20) -> QIcon:
    """Create a QIcon from inline SVG data."""
    if not _HAS_SVG:
        return QIcon()
    renderer = QSvgRenderer(QByteArray(svg_data.encode()))
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


# ═══════════════════════════════════════════════════════════════════════
#  AuthScreen – GitHub-style login / registration
# ═══════════════════════════════════════════════════════════════════════


class AuthScreen(QWidget):
    """GitHub-styled authentication screen with video hero and form card."""

    auth_success = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._load_env_file()

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── LEFT: hero panel with gradient background ─────────────
        hero = QFrame()
        hero.setObjectName("GhHero")

        ov = QVBoxLayout(hero)
        ov.setContentsMargins(48, 48, 48, 48)
        ov.setSpacing(16)

        brand = QLabel("ProjectsControl")
        brand.setObjectName("GhBrand")

        tagline = QLabel("Контроль продуктивности\nи управление проектами")
        tagline.setObjectName("GhTagline")
        tagline.setWordWrap(True)

        note = QLabel("Работайте эффективно.\nМы поможем держать фокус.")
        note.setObjectName("GhNote")
        note.setWordWrap(True)

        ov.addWidget(brand)
        ov.addSpacing(8)
        ov.addWidget(tagline)
        ov.addWidget(note)
        ov.addStretch(1)

        # ── RIGHT: form panel ─────────────────────────────────────
        right = QFrame()
        right.setObjectName("GhRight")
        right_outer = QVBoxLayout(right)
        right_outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("GhScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setObjectName("GhRight")
        form = QVBoxLayout(inner)
        form.setContentsMargins(40, 32, 40, 32)
        form.setSpacing(0)

        # Top-right switch link
        top_row = QHBoxLayout()
        top_row.addStretch(1)
        self.switch_label = QLabel("")
        self.switch_label.setObjectName("GhMuted")
        self.switch_link = QPushButton("")
        self.switch_link.setObjectName("GhLink")
        self.switch_link.setCursor(Qt.PointingHandCursor)
        self.switch_link.clicked.connect(self._toggle_mode)
        top_row.addWidget(self.switch_label)
        top_row.addWidget(self.switch_link)
        form.addLayout(top_row)
        form.addSpacing(32)

        # Form title
        self.form_title = QLabel("")
        self.form_title.setObjectName("GhFormTitle")
        form.addWidget(self.form_title)
        form.addSpacing(24)

        # Google OAuth button
        self.google_btn = QPushButton("   Continue with Google")
        self.google_btn.setObjectName("GhOAuthBtn")
        self.google_btn.setCursor(Qt.PointingHandCursor)
        self.google_btn.setIcon(_svg_icon(_GOOGLE_SVG, 20))
        self.google_btn.setIconSize(QSize(20, 20))
        self.google_btn.clicked.connect(self.handle_google_login)
        form.addWidget(self.google_btn)
        form.addSpacing(20)

        # "or" divider
        div_row = QHBoxLayout()
        line_l = QFrame()
        line_l.setFrameShape(QFrame.HLine)
        line_l.setObjectName("GhDivider")
        or_lbl = QLabel("or")
        or_lbl.setObjectName("GhMuted")
        or_lbl.setAlignment(Qt.AlignCenter)
        or_lbl.setFixedWidth(36)
        line_r = QFrame()
        line_r.setFrameShape(QFrame.HLine)
        line_r.setObjectName("GhDivider")
        div_row.addWidget(line_l)
        div_row.addWidget(or_lbl)
        div_row.addWidget(line_r)
        form.addLayout(div_row)
        form.addSpacing(20)

        # Stacked form panels
        self.stack = QStackedWidget()
        self.login_panel = self._build_login_panel()
        self.register_panel = self._build_register_panel()
        self.stack.addWidget(self.login_panel)
        self.stack.addWidget(self.register_panel)
        form.addWidget(self.stack)
        form.addSpacing(16)

        # Status / error label
        self.status_label = QLabel("")
        self.status_label.setObjectName("GhStatus")
        self.status_label.setWordWrap(True)
        form.addWidget(self.status_label)

        form.addStretch(1)

        # Terms footer
        terms = QLabel(
            "By creating an account, you agree to the "
            '<a style="color:#4f8fff;text-decoration:none" href="#">'
            "Terms of Service</a>."
        )
        terms.setObjectName("GhTerms")
        terms.setWordWrap(True)
        terms.setOpenExternalLinks(False)
        form.addSpacing(24)
        form.addWidget(terms)

        scroll.setWidget(inner)
        right_outer.addWidget(scroll)

        root.addWidget(hero, 3)
        root.addWidget(right, 2)

        self.google_worker: OAuthWorker | None = None
        self.google_thread: QThread | None = None
        self._mode = 0  # 0 = sign-in, 1 = sign-up
        self._show_mode(0)

    # ── form builders ─────────────────────────────────────────────

    @staticmethod
    def _field(
        label: str,
        placeholder: str = "",
        password: bool = False,
        hint: str = "",
    ) -> tuple[QLineEdit, QWidget]:
        """Build a GitHub-style labelled input field with optional hint."""
        group = QWidget()
        lay = QVBoxLayout(group)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        lbl = QLabel(f"{label}<span style='color:#ef4444'>*</span>")
        lbl.setObjectName("GhFieldLabel")
        lbl.setTextFormat(Qt.RichText)
        lay.addWidget(lbl)

        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setObjectName("GhInput")
        if password:
            inp.setEchoMode(QLineEdit.Password)
        lay.addWidget(inp)

        if hint:
            h = QLabel(hint)
            h.setObjectName("GhFieldHint")
            h.setWordWrap(True)
            lay.addWidget(h)

        return inp, group

    def _build_login_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        self.login_email, g1 = self._field("Email", "you@example.com")
        self.login_password, g2 = self._field(
            "Password", "Password", password=True
        )

        lay.addWidget(g1)
        lay.addWidget(g2)

        self.login_btn = QPushButton("Sign in  →")
        self.login_btn.setObjectName("GhSubmit")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        lay.addWidget(self.login_btn)

        return panel

    def _build_register_panel(self) -> QWidget:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)

        self.reg_email, g1 = self._field("Email", "you@example.com")
        self.reg_password, g2 = self._field(
            "Password",
            "Create a password",
            password=True,
            hint=(
                "Password should be at least 15 characters OR at least 8 "
                "characters including a number and a lowercase letter."
            ),
        )
        self.reg_name, g3 = self._field("Full Name", "Your full name")

        lay.addWidget(g1)
        lay.addWidget(g2)
        lay.addWidget(g3)

        self.reg_btn = QPushButton("Create account  →")
        self.reg_btn.setObjectName("GhSubmit")
        self.reg_btn.setCursor(Qt.PointingHandCursor)
        self.reg_btn.clicked.connect(self.handle_register)
        lay.addWidget(self.reg_btn)

        return panel

    # ── mode switching ────────────────────────────────────────────

    def _show_mode(self, index: int) -> None:
        self._mode = index
        self.stack.setCurrentIndex(index)
        self.status_label.setText("")
        self.status_label.setStyleSheet("")
        if index == 0:
            self.form_title.setText("Sign in to ProjectsControl")
            self.switch_label.setText("New to ProjectsControl?  ")
            self.switch_link.setText("Create an account →")
        else:
            self.form_title.setText("Create your account")
            self.switch_label.setText("Already have an account?  ")
            self.switch_link.setText("Sign in →")

    def _toggle_mode(self) -> None:
        self._show_mode(1 if self._mode == 0 else 0)

    # ── handlers ──────────────────────────────────────────────────

    def handle_login(self) -> None:
        email = self.login_email.text().strip()
        password = self.login_password.text().strip()
        if not email or not password:
            self.status_label.setText("Enter email and password")
            return

        self.login_btn.setEnabled(False)
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
            self.status_label.setText("")
            self.auth_success.emit()
        except ApiError as exc:
            self.status_label.setText(f"Login error: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Login error: {exc}")
        finally:
            self.login_btn.setEnabled(True)

    def handle_register(self) -> None:
        name = self.reg_name.text().strip()
        email = self.reg_email.text().strip()
        password = self.reg_password.text().strip()
        if not name or not email or not password:
            self.status_label.setText("Please fill in all fields")
            return

        self.reg_btn.setEnabled(False)
        try:
            api_client.register(email=email, password=password, full_name=name)
            self.status_label.setText("")
            self.reg_name.clear()
            self.reg_email.clear()
            self.reg_password.clear()
            self._show_mode(0)
            self.status_label.setText("Account created! Please sign in.")
            self.status_label.setStyleSheet("color: #3b82f6;")
        except ApiError as exc:
            self.status_label.setStyleSheet("")
            self.status_label.setText(f"Registration error: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setStyleSheet("")
            self.status_label.setText(f"Registration error: {exc}")
        finally:
            self.reg_btn.setEnabled(True)

    def handle_google_login(self) -> None:
        self._load_env_file()
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not client_id or not client_secret:
            self.status_label.setText(
                "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set in frontend/.env"
            )
            return

        if self.google_thread and self.google_thread.isRunning():
            self.status_label.setText("OAuth already in progress")
            return

        self.google_btn.setEnabled(False)
        self.status_label.setText("Opening browser for Google sign in…")

        self.google_worker = OAuthWorker(
            client_id=client_id, client_secret=client_secret
        )
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
            self.status_label.setText(f"OAuth error: {error}")
            self.google_btn.setEnabled(True)
            return

        email = profile.get("email", "")
        name = profile.get("name", "")
        id_token = profile.get("id_token")

        if email:
            self.login_email.setText(email)
            self.reg_email.setText(email)
        if name and not self.reg_name.text().strip():
            self.reg_name.setText(name)

        if not id_token:
            self.status_label.setText("OAuth completed, but no id_token received")
            self.google_btn.setEnabled(True)
            return

        try:
            token = api_client.google_login(id_token)
            session_store.set_token(token)
            try:
                me = api_client.get_me()
                session_store.set_user_profile(
                    me.get("id"),
                    me.get("full_name"),
                    me.get("patronymic"),
                )
            except ApiError:
                session_store.set_user_profile(None, None, None)
            self.status_label.setText("")
            self.auth_success.emit()
        except ApiError as exc:
            self.status_label.setText(f"Google sign-in error: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Google sign-in error: {exc}")
        finally:
            self.google_btn.setEnabled(True)

    # ── helpers ───────────────────────────────────────────────────

    def _load_env_file(self) -> None:
        env_path = Path(__file__).resolve().parents[3] / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"'))


# ═══════════════════════════════════════════════════════════════════════
#  OAuthWorker – runs Google OAuth flow in a background thread
# ═══════════════════════════════════════════════════════════════════════


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

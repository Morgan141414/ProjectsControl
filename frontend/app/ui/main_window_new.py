"""Main window – sidebar navigation + onboarding flow.

Screen indices in the stack:
  0  AuthScreen
  1  ConsentBannerScreen
  2  RoleSelectScreen
  3  ProfileSetupScreen
  4  DashboardScreen
  5  ProfileScreen
  6  ActivityScreen
  7  AdminConsoleScreen
  8  SettingsScreen
"""

from PySide6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    QSize,
    Qt,
    QTimeLine,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store

from app.ui.screens.activity import ActivityScreen
from app.ui.screens.admin_console import AdminConsoleScreen
from app.ui.screens.auth import AuthScreen
from app.ui.screens.consent_banner import ConsentBannerScreen
from app.ui.screens.dashboard_new import DashboardScreen
from app.ui.screens.profile import ProfileScreen
from app.ui.screens.profile_setup import ProfileSetupScreen
from app.ui.screens.role_select import RoleSelectScreen
from app.ui.screens.settings import SettingsScreen


# ═══════════════════════════════════════════════════════════════════════
#  SidebarFrame – smooth CSS-driven hover via QTimeLine
# ═══════════════════════════════════════════════════════════════════════


class SidebarFrame(QFrame):
    """Smooth sidebar: CSS approach with QTimeLine for width animation.

    Uses 60 fps QTimeLine for buttery animation instead of
    QPropertyAnimation which can feel laggy on resize-heavy layouts.
    """

    def __init__(self, collapsed: int = 64, expanded: int = 220, parent=None) -> None:
        super().__init__(parent)
        self._collapsed = collapsed
        self._expanded = expanded
        self._current_width = collapsed

        self.setMinimumWidth(collapsed)
        self.setMaximumWidth(collapsed)

        self._timeline = QTimeLine(200, self)  # 200ms duration
        self._timeline.setFrameRange(0, 100)
        self._timeline.setEasingCurve(QEasingCurve.OutCubic)
        self._timeline.frameChanged.connect(self._on_frame)
        self._timeline.finished.connect(self._on_finished)

        self._target = "collapsed"
        self._labels: dict["QPushButton", str] = {}

    def register_button(self, btn: "QPushButton", label: str) -> None:
        self._labels[btn] = label

    def expand(self) -> None:
        if self._target == "expanded":
            return
        self._target = "expanded"
        self._animate(self.maximumWidth(), self._expanded)

    def collapse(self) -> None:
        if self._target == "collapsed":
            return
        self._target = "collapsed"
        # Hide labels immediately on collapse
        for btn in self._labels:
            btn.setText("")
        self._animate(self.maximumWidth(), self._collapsed)

    # ── internal ─────────────────────────────────────────────────

    def _animate(self, start: int, end: int) -> None:
        self._start_w = start
        self._end_w = end
        self._timeline.stop()
        self._timeline.start()

    def _on_frame(self, frame: int) -> None:
        t = frame / 100.0
        w = int(self._start_w + (self._end_w - self._start_w) * t)
        self.setMinimumWidth(w)
        self.setMaximumWidth(w)

    def _on_finished(self) -> None:
        if self._target == "expanded":
            for btn, label in self._labels.items():
                btn.setText(label)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.collapse()
        super().leaveEvent(event)


# ═══════════════════════════════════════════════════════════════════════
#  MainWindow
# ═══════════════════════════════════════════════════════════════════════

# Screen indices
_AUTH = 0
_CONSENT = 1
_ROLE = 2
_PROFILE_SETUP = 3
_DASHBOARD = 4
_PROFILE = 5
_ACTIVITY = 6
_ADMIN = 7
_SETTINGS = 8

# Screens that are part of the onboarding flow (no sidebar)
_ONBOARDING = {_AUTH, _CONSENT, _ROLE, _PROFILE_SETUP}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ProjectsControl")
        self.resize(1100, 720)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Sidebar ───────────────────────────────────────────────
        self.sidebar = SidebarFrame(collapsed=64, expanded=220)
        self.sidebar.setObjectName("Sidebar")

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(8)

        self.nav_buttons: list[QPushButton] = []

        self.btn_home = self._make_nav("Главная", QStyle.SP_DirHomeIcon)
        self.btn_profile = self._make_nav("Профиль", QStyle.SP_FileIcon)
        self.btn_settings = self._make_nav("Настройки", QStyle.SP_FileDialogListView)

        sidebar_layout.addWidget(self.btn_home)
        sidebar_layout.addWidget(self.btn_profile)
        sidebar_layout.addStretch(1)
        sidebar_layout.addWidget(self.btn_settings)

        # ── Content area ──────────────────────────────────────────
        self.stack = QStackedWidget()

        self.auth_screen = AuthScreen()
        self.consent_screen = ConsentBannerScreen()
        self.role_screen = RoleSelectScreen()
        self.profile_setup_screen = ProfileSetupScreen()
        self.dashboard_screen = DashboardScreen()
        self.profile_screen = ProfileScreen()
        self.activity_screen = ActivityScreen()
        self.admin_screen = AdminConsoleScreen()
        self.settings_screen = SettingsScreen()

        self.stack.addWidget(self.auth_screen)          # 0
        self.stack.addWidget(self.consent_screen)       # 1
        self.stack.addWidget(self.role_screen)          # 2
        self.stack.addWidget(self.profile_setup_screen) # 3
        self.stack.addWidget(self.dashboard_screen)     # 4
        self.stack.addWidget(self.profile_screen)       # 5
        self.stack.addWidget(self.activity_screen)      # 6
        self.stack.addWidget(self.admin_screen)         # 7
        self.stack.addWidget(self.settings_screen)      # 8

        content_frame = QFrame()
        self.content_layout = QVBoxLayout(content_frame)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.addWidget(self.stack)

        layout.addWidget(self.sidebar)
        layout.addWidget(content_frame)
        self.setCentralWidget(root)

        # ── Nav connections ───────────────────────────────────────
        self.btn_home.clicked.connect(lambda: self.show_screen(_DASHBOARD))
        self.btn_profile.clicked.connect(lambda: self.show_screen(_PROFILE))
        self.btn_settings.clicked.connect(lambda: self.show_screen(_SETTINGS))

        # ── Screen signals ────────────────────────────────────────
        self.auth_screen.auth_success.connect(self._handle_auth_success)
        self.consent_screen.consent_accepted.connect(self._handle_consent_accepted)
        self.consent_screen.consent_declined.connect(self._handle_consent_declined)
        self.role_screen.role_selected.connect(self._handle_role_selected)
        self.profile_setup_screen.profile_completed.connect(self._handle_profile_completed)
        self.dashboard_screen.start_work.connect(lambda: self.show_screen(_ACTIVITY))
        self.dashboard_screen.org_changed.connect(self._on_org_changed)
        self.settings_screen.logged_out.connect(self._handle_logout)

        # ── Initial state ────────────────────────────────────────
        self.sidebar.collapse()
        self._auto_login()

    # ══════════════════════════════════════════════════════════════
    #  Screen management
    # ══════════════════════════════════════════════════════════════

    def show_screen(self, index: int) -> None:
        self.stack.setCurrentIndex(index)

        # Update nav button checked states
        self.btn_home.setChecked(index == _DASHBOARD)
        self.btn_profile.setChecked(index == _PROFILE)
        self.btn_settings.setChecked(index == _SETTINGS)

        # Sidebar visibility — hide during onboarding
        self.sidebar.setVisible(index not in _ONBOARDING)

        # Full-bleed for onboarding screens
        if index in _ONBOARDING:
            self.content_layout.setContentsMargins(0, 0, 0, 0)
        else:
            self.content_layout.setContentsMargins(24, 24, 24, 24)

        # Refresh on show
        if index == _DASHBOARD:
            self.dashboard_screen.refresh_tasks()
        elif index == _PROFILE:
            self.profile_screen.refresh_profile()
        elif index == _SETTINGS:
            self.settings_screen.refresh_settings()

    # ══════════════════════════════════════════════════════════════
    #  Sidebar helpers
    # ══════════════════════════════════════════════════════════════

    def _make_nav(self, text: str, icon: QStyle.StandardPixmap) -> QPushButton:
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setIcon(self.style().standardIcon(icon))
        btn.setIconSize(QSize(18, 18))
        btn.setToolTip(text)
        self.nav_buttons.append(btn)
        self.sidebar.register_button(btn, text)
        return btn

    # ══════════════════════════════════════════════════════════════
    #  Onboarding flow
    # ══════════════════════════════════════════════════════════════

    def _auto_login(self) -> None:
        """Resume session or show auth screen."""
        if not session_store.token:
            self.show_screen(_AUTH)
            return
        try:
            profile = api_client.get_me()
            session_store.set_user_profile(
                profile.get("id"),
                profile.get("full_name"),
                profile.get("patronymic"),
            )
            self._advance_onboarding()
        except ApiError:
            session_store.clear()
            self.show_screen(_AUTH)

    def _handle_auth_success(self) -> None:
        """After login/register → go through onboarding."""
        self._advance_onboarding()

    def _handle_consent_accepted(self) -> None:
        session_store.set_consent_accepted(True)
        # Also try to persist to backend
        org_id = session_store.org_id
        if org_id:
            try:
                api_client.accept_consent(org_id, policy_version="v1")
            except (ApiError, Exception):  # noqa: BLE001
                pass
        self._advance_onboarding()

    def _handle_consent_declined(self) -> None:
        """User declined consent → log out."""
        session_store.clear()
        self.show_screen(_AUTH)

    def _handle_role_selected(self, role: str) -> None:
        session_store.set_role(role)
        self._advance_onboarding()

    def _handle_profile_completed(self) -> None:
        self._advance_onboarding()

    def _handle_logout(self) -> None:
        session_store.clear()
        self.show_screen(_AUTH)

    def _on_org_changed(self) -> None:
        """Org changed — refresh dashboard."""
        self.dashboard_screen.refresh_tasks()

    def _advance_onboarding(self) -> None:
        """Determine next screen in the onboarding flow.

        Order: Auth → Consent → Role → ProfileSetup → Dashboard
        Skip any step that is already completed.
        """
        if not session_store.token:
            self.show_screen(_AUTH)
            return

        if not session_store.consent_accepted:
            self.show_screen(_CONSENT)
            return

        if not session_store.role:
            self.show_screen(_ROLE)
            return

        if not session_store.profile_complete:
            self.show_screen(_PROFILE_SETUP)
            return

        # All done — go to dashboard
        self.show_screen(_DASHBOARD)

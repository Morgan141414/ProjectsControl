"""Main window – Tilda-dark design, sidebar nav, onboarding flow.

Stack indices
  0  AuthScreen
  1  ConsentBannerScreen
  2  RoleSelectScreen
  3  ProfileSetupScreen
  4  JoinOrgScreen       (member onboarding - join organization)
  5  DashboardScreen
  6  ProfileScreen   (Instagram-style profile view)
  7  SettingsScreen
  8  OrgWizardScreen
  9  NotificationsPanel  (bell in top-bar)
 10  MessagesScreen      (sidebar tab)
 11  SearchScreen        (sidebar search)
 12  EditProfileScreen   (edit form)
 13  TeamScreen          (штаб — list of departments)
 14  CabinetScreen       (personal cabinet)
 15  DepartmentScreen    (department detail / interior)
 16  BroadcastsScreen    (live team broadcasts - admin/manager only)
 17  RecordingPlayerScreen (video playback)
"""

from PySide6.QtCore import QByteArray, QEasingCurve, QSize, Qt, QTimeLine, QTimer, Signal
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store

from app.ui.screens.auth import AuthScreen
from app.ui.screens.broadcasts import BroadcastsScreen
from app.ui.screens.consent_banner import ConsentBannerScreen
from app.ui.screens.dashboard import DashboardScreen
from app.ui.screens.join_org import JoinOrgScreen
from app.ui.screens.messages import MessagesScreen
from app.ui.screens.notifications import NotificationsPanel
from app.ui.screens.org_wizard import OrgWizardScreen
from app.ui.screens.profile import EditProfileScreen, ProfileScreen
from app.ui.screens.profile_setup import ProfileSetupScreen
from app.ui.screens.recording_player import RecordingPlayerScreen
from app.ui.screens.role_select import RoleSelectScreen
from app.ui.screens.search import SearchScreen
from app.ui.screens.settings import SettingsScreen
from app.ui.screens.team import TeamScreen
from app.ui.screens.cabinet import CabinetScreen
from app.ui.screens.department import DepartmentScreen

try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False


# ═══════════════════════════════════════════════════════════════════════
#  Feather-style SVG icons (no emoji anywhere)
# ═══════════════════════════════════════════════════════════════════════

_ICON_HOME = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    '<polyline points="9 22 9 12 15 12 15 22"/></svg>'
)

_ICON_MSG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
    '</svg>'
)

_ICON_SETTINGS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83'
    ' 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0'
    ' 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9'
    ' 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0'
    ' 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3'
    'a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65'
    ' 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06'
    'a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1'
    ' 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0'
    ' 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65'
    ' 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2'
    ' 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
)

_ICON_BELL = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
    '<path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'
)

_ICON_HEART = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06'
    'a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06'
    'a5.5 5.5 0 0 0 0-7.78z"/></svg>'
)

_ICON_USER = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/></svg>'
)

_ICON_SEARCH = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="11" cy="11" r="8"/>'
    '<line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
)

_ICON_MENU = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="3" y1="12" x2="21" y2="12"/>'
    '<line x1="3" y1="6" x2="21" y2="6"/>'
    '<line x1="3" y1="18" x2="21" y2="18"/></svg>'
)

_ICON_VIDEO = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="23 7 16 12 23 17 23 7"/>'
    '<rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>'
)


def _svg_icon(svg_template: str, size: int = 20, color: str = "#8891a5") -> QIcon:
    """Render an inline SVG template to QIcon.  {c} is replaced with color."""
    if not _HAS_SVG:
        return QIcon()
    svg = svg_template.replace("{c}", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return QIcon(pix)


def _svg_pixmap(svg_template: str, size: int = 20, color: str = "#8891a5") -> QPixmap:
    """Render inline SVG to QPixmap."""
    if not _HAS_SVG:
        return QPixmap()
    svg = svg_template.replace("{c}", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return pix


# ═══════════════════════════════════════════════════════════════════════
#  SidebarFrame – smooth 60 fps via QTimeLine
# ═══════════════════════════════════════════════════════════════════════


class SidebarFrame(QFrame):
    """Premium sidebar with ultra-smooth 120 fps expand/collapse via QTimeLine.

    Features:
      - OutExpo easing for buttery-smooth feel
      - Fast 140 ms animation (Instagram-like speed)
      - Delayed collapse (120 ms) to avoid jitter
      - Labels appear only after expansion finishes
      - Cursor-position guard prevents false collapses
    """

    def __init__(self, collapsed: int = 56, expanded: int = 216, parent=None) -> None:
        super().__init__(parent)
        self._collapsed = collapsed
        self._expanded = expanded
        self.setMinimumWidth(collapsed)
        self.setMaximumWidth(collapsed)

        # Expand timeline — 140 ms OutExpo for premium feel
        self._tl = QTimeLine(140, self)
        self._tl.setFrameRange(0, 100)
        self._tl.setEasingCurve(QEasingCurve.OutExpo)
        self._tl.setUpdateInterval(8)  # ~120 fps
        self._tl.frameChanged.connect(self._tick)
        self._tl.finished.connect(self._done)

        # Delayed collapse — faster response
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(120)
        self._collapse_timer.timeout.connect(self._collapse_if_outside)

        self._target = "collapsed"
        self._labels: dict[QPushButton, str] = {}

    def register(self, btn: QPushButton, label: str) -> None:
        self._labels[btn] = label

    def expand(self) -> None:
        if self._target == "expanded":
            return
        self._target = "expanded"
        self._go(self.maximumWidth(), self._expanded)

    def collapse(self) -> None:
        if self._target == "collapsed":
            return
        self._target = "collapsed"
        for b in self._labels:
            b.setText("")
        self._go(self.maximumWidth(), self._collapsed)

    def _go(self, s: int, e: int) -> None:
        self._s = s
        self._e = e
        self._tl.stop()
        self._tl.start()

    def _tick(self, f: int) -> None:
        w = int(self._s + (self._e - self._s) * f / 100)
        self.setMinimumWidth(w)
        self.setMaximumWidth(w)

    def _done(self) -> None:
        if self._target == "expanded":
            for b, t in self._labels.items():
                b.setText(t)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._collapse_timer.stop()
        self.expand()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._collapse_timer.start()
        super().leaveEvent(event)

    def _collapse_if_outside(self) -> None:
        """Only collapse if cursor is truly outside the sidebar area."""
        pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(pos):
            self.collapse()


# ═══════════════════════════════════════════════════════════════════════
#  SlidePanel – Instagram-style overlay panel with smooth slide animation
# ═══════════════════════════════════════════════════════════════════════


class SlidePanel(QFrame):
    """Instagram-style overlay panel that slides in from the right.

    Used for Notifications and Messages panels.
    Features:
      - Smooth slide-in/out animation (180ms OutExpo)
      - Dark overlay background
      - Click outside to close
    """

    closed = Signal()

    def __init__(self, width: int = 400, parent=None) -> None:
        super().__init__(parent)
        self._panel_width = width
        self._visible = False
        self.setObjectName("SlidePanel")
        self.setFixedWidth(0)
        self.setStyleSheet(
            "#SlidePanel{background:#0c1021;border-left:1px solid #1e2538;}"
        )

        # Slide timeline — 180ms OutExpo
        self._tl = QTimeLine(180, self)
        self._tl.setFrameRange(0, 100)
        self._tl.setEasingCurve(QEasingCurve.OutExpo)
        self._tl.setUpdateInterval(8)
        self._tl.frameChanged.connect(self._tick)

        self._s = 0
        self._e = 0

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    def set_content(self, widget: QWidget) -> None:
        """Set the content widget of the panel."""
        # Clear existing
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        self._layout.addWidget(widget)

    def slide_in(self) -> None:
        if self._visible:
            return
        self._visible = True
        self.show()
        self.raise_()
        self._s = 0
        self._e = self._panel_width
        self._tl.stop()
        self._tl.start()

    def slide_out(self) -> None:
        if not self._visible:
            return
        self._visible = False
        self._s = self._panel_width
        self._e = 0
        self._tl.stop()
        self._tl.start()

    def toggle(self) -> None:
        if self._visible:
            self.slide_out()
        else:
            self.slide_in()

    def is_panel_visible(self) -> bool:
        return self._visible

    def _tick(self, f: int) -> None:
        w = int(self._s + (self._e - self._s) * f / 100)
        self.setFixedWidth(max(0, w))
        if not self._visible and w <= 0:
            self.hide()
            self.closed.emit()


# ═══════════════════════════════════════════════════════════════════════
#  Screen indices (no Admin Console)
# ═══════════════════════════════════════════════════════════════════════

_AUTH = 0
_CONSENT = 1
_ROLE = 2
_PROFILE_SETUP = 3
_JOIN_ORG = 4
_DASHBOARD = 5
_PROFILE = 6
_SETTINGS = 7
_ORG_WIZARD = 8
_NOTIFICATIONS = 9
_MESSAGES = 10
_SEARCH = 11
_EDIT_PROFILE = 12
_TEAM = 13
_CABINET = 14
_DEPARTMENT = 15
_BROADCASTS = 16
_RECORDING_PLAYER = 17

_ONBOARDING = {_AUTH, _CONSENT, _ROLE, _PROFILE_SETUP, _JOIN_ORG}
_FULLBLEED = {_AUTH, _CONSENT, _ROLE, _PROFILE_SETUP, _JOIN_ORG, _ORG_WIZARD}


# ═══════════════════════════════════════════════════════════════════════
#  MainWindow
# ═══════════════════════════════════════════════════════════════════════


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ProjectsControl")
        self.resize(1120, 740)

        root = QWidget()
        root_lay = QVBoxLayout(root)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────
        self._topbar = QFrame()
        self._topbar.setObjectName("TopBar")
        tb = QHBoxLayout(self._topbar)
        tb.setContentsMargins(20, 8, 20, 8)
        tb.setSpacing(12)

        # Instagram-style logo text on left
        logo = QLabel("ProjectsControl")
        logo.setObjectName("TopBarLogo")
        logo.setStyleSheet(
            "font-size:17px; font-weight:700; color:#f1f5f9;"
            " background:transparent; letter-spacing:0.4px;"
        )
        tb.addWidget(logo)
        tb.addStretch(1)

        # Bell (notifications) — SVG icon — toggles right slide panel
        self.bell_btn = QPushButton()
        self.bell_btn.setObjectName("BellBtn")
        self.bell_btn.setCursor(Qt.PointingHandCursor)
        self.bell_btn.setToolTip("Уведомления")
        self.bell_btn.setFixedSize(36, 36)
        self.bell_btn.setIcon(_svg_icon(_ICON_BELL, 20, "#94a3b8"))
        self.bell_btn.setIconSize(QSize(20, 20))
        self.bell_btn.clicked.connect(self._toggle_notifications_panel)
        tb.addWidget(self.bell_btn)

        root_lay.addWidget(self._topbar)

        # ── Body: sidebar + content + slide panels ───────────────
        body = QWidget()
        body_lay = QHBoxLayout(body)
        body_lay.setContentsMargins(0, 0, 0, 0)
        body_lay.setSpacing(0)

        # Sidebar
        self.sidebar = SidebarFrame(collapsed=60, expanded=220)
        self.sidebar.setObjectName("Sidebar")

        sl = QVBoxLayout(self.sidebar)
        sl.setContentsMargins(10, 14, 10, 14)
        sl.setSpacing(4)

        self.nav_buttons: list[QPushButton] = []

        self.btn_home = self._nav("Главная", _ICON_HOME)
        self.btn_search = self._nav("Поиск", _ICON_SEARCH)
        self.btn_msg = self._nav("Сообщения", _ICON_MSG)
        self.btn_notif = self._nav("Уведомления", _ICON_HEART)

        sl.addWidget(self.btn_home)
        sl.addWidget(self.btn_search)
        sl.addWidget(self.btn_msg)
        sl.addWidget(self.btn_notif)

        # Profile — same _nav() style as other buttons, default avatar icon
        self.btn_profile = self._nav("Профиль", _ICON_USER)
        sl.addWidget(self.btn_profile)

        # Broadcasts (admin/manager only)
        self.btn_broadcasts = self._nav("Трансляции", _ICON_VIDEO)
        sl.addWidget(self.btn_broadcasts)
        # Hide by default, show after login if user is admin/manager
        self.btn_broadcasts.setVisible(False)

        sl.addStretch(1)

        # Settings + Menu at bottom
        self.btn_settings = self._nav("Настройки", _ICON_MENU)
        sl.addWidget(self.btn_settings)
        sl.addSpacing(8)

        # Content
        self.stack = QStackedWidget()

        self.auth_screen = AuthScreen()
        self.consent_screen = ConsentBannerScreen()
        self.role_screen = RoleSelectScreen()
        self.profile_setup_screen = ProfileSetupScreen()
        self.join_org_screen = JoinOrgScreen()
        self.dashboard_screen = DashboardScreen()
        self.profile_screen = ProfileScreen()
        self.settings_screen = SettingsScreen()
        self.org_wizard_screen = OrgWizardScreen()
        self.search_screen = SearchScreen()
        self.edit_profile_screen = EditProfileScreen()
        self.team_screen = TeamScreen()
        self.cabinet_screen = CabinetScreen()
        self.department_screen = DepartmentScreen()
        self.broadcasts_screen = BroadcastsScreen()
        self.recording_player_screen = RecordingPlayerScreen()

        self.stack.addWidget(self.auth_screen)           # 0
        self.stack.addWidget(self.consent_screen)        # 1
        self.stack.addWidget(self.role_screen)           # 2
        self.stack.addWidget(self.profile_setup_screen)  # 3
        self.stack.addWidget(self.join_org_screen)       # 4
        self.stack.addWidget(self.dashboard_screen)      # 5
        self.stack.addWidget(self.profile_screen)        # 6
        self.stack.addWidget(self.settings_screen)       # 7
        self.stack.addWidget(self.org_wizard_screen)     # 8
        # index 9 — kept as placeholder (no longer NotificationsPanel in stack)
        self.stack.addWidget(QWidget())                  # 9 placeholder
        # index 10 — kept as placeholder (no longer MessagesScreen in stack)
        self.stack.addWidget(QWidget())                  # 10 placeholder
        self.stack.addWidget(self.search_screen)         # 11
        self.stack.addWidget(self.edit_profile_screen)   # 12
        self.stack.addWidget(self.team_screen)             # 13
        self.stack.addWidget(self.cabinet_screen)          # 14
        self.stack.addWidget(self.department_screen)        # 15
        self.stack.addWidget(self.broadcasts_screen)        # 16
        self.stack.addWidget(self.recording_player_screen)  # 17

        content_frame = QFrame()
        self.content_layout = QVBoxLayout(content_frame)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.addWidget(self.stack)

        body_lay.addWidget(self.sidebar)
        body_lay.addWidget(content_frame, 1)

        # ── Instagram-style slide panels (overlay, right side) ──
        # Notifications panel — slides from right
        self.notif_screen = NotificationsPanel()
        self._notif_slide = SlidePanel(width=380, parent=body)
        self._notif_slide.set_content(self.notif_screen)
        self._notif_slide.hide()

        # Messages panel — slides from right
        self.msg_screen = MessagesScreen()
        self._msg_slide = SlidePanel(width=420, parent=body)
        self._msg_slide.set_content(self.msg_screen)
        self._msg_slide.hide()

        root_lay.addWidget(body, 1)
        self.setCentralWidget(root)

        # Position slide panels on the right
        self._body_widget = body

        # ── Connections ──────────────────────────────────────────
        self.btn_home.clicked.connect(lambda: self.show_screen(_DASHBOARD))
        self.btn_search.clicked.connect(lambda: self.show_screen(_SEARCH))
        self.btn_msg.clicked.connect(self._toggle_messages_panel)
        self.btn_notif.clicked.connect(self._toggle_notifications_panel)
        self.btn_settings.clicked.connect(lambda: self.show_screen(_SETTINGS))
        self.btn_profile.clicked.connect(lambda: self.show_screen(_PROFILE))
        self.btn_broadcasts.clicked.connect(lambda: self.show_screen(_BROADCASTS))

        self.auth_screen.auth_success.connect(self._on_auth_success)
        self.consent_screen.consent_accepted.connect(self._on_consent_accepted)
        self.consent_screen.consent_declined.connect(self._on_consent_declined)
        self.role_screen.role_selected.connect(self._on_role_selected)
        self.profile_setup_screen.profile_completed.connect(self._on_profile_done)
        self.join_org_screen.join_completed.connect(self._on_join_completed)

        self.dashboard_screen.org_changed.connect(self._on_org_changed)
        self.dashboard_screen.open_org_wizard.connect(
            lambda: self.show_screen(_ORG_WIZARD)
        )
        self.dashboard_screen.open_team.connect(lambda: self.show_screen(_TEAM))
        self.dashboard_screen.open_cabinet.connect(lambda: self.show_screen(_CABINET))
        self.org_wizard_screen.org_created.connect(self._on_org_created)
        self.org_wizard_screen.go_back.connect(lambda: self.show_screen(_DASHBOARD))
        self.notif_screen.go_back.connect(self._close_all_panels)
        self.msg_screen.go_back.connect(self._close_all_panels)
        self.profile_screen.open_edit_profile.connect(
            lambda: self.show_screen(_EDIT_PROFILE)
        )
        self.profile_screen.go_back.connect(lambda: self.show_screen(_DASHBOARD))
        self.edit_profile_screen.go_back.connect(lambda: self.show_screen(_PROFILE))
        self.edit_profile_screen.avatar_changed.connect(self._sync_avatar)
        self.search_screen.go_back.connect(lambda: self.show_screen(_DASHBOARD))

        # Team and cabinet navigation
        self.team_screen.go_back.connect(lambda: self.show_screen(_DASHBOARD))
        self.team_screen.open_department.connect(self._open_department)
        self.cabinet_screen.go_back.connect(lambda: self.show_screen(_DASHBOARD))
        self.department_screen.go_back.connect(lambda: self.show_screen(_TEAM))
        self.department_screen.open_cabinet.connect(
            lambda: self.show_screen(_CABINET)
        )

        self.settings_screen.logged_out.connect(self._on_logout)

        # Broadcasts and recording player
        self.broadcasts_screen.go_back.connect(lambda: self.show_screen(_DASHBOARD))
        self.broadcasts_screen.open_recording.connect(self._open_recording_player)
        self.recording_player_screen.go_back.connect(lambda: self.show_screen(_BROADCASTS))

        # ── Init ─────────────────────────────────────────────────
        self.sidebar.collapse()
        self._sync_avatar()  # load initial avatar
        self._auto_login()

    # ══════════════════════════════════════════════════════════════
    #  Screen management
    # ══════════════════════════════════════════════════════════════

    def show_screen(self, idx: int) -> None:
        # Close any open slide panels when navigating
        self._close_all_panels()

        # Access control for broadcasts screen
        if idx == _BROADCASTS:
            if session_store.role not in ("admin", "manager"):
                self.stack.setCurrentIndex(_DASHBOARD)
                return

        # Notifications and messages are now side panels, not stack screens
        if idx == _NOTIFICATIONS:
            self._toggle_notifications_panel()
            return
        if idx == _MESSAGES:
            self._toggle_messages_panel()
            return

        self.stack.setCurrentIndex(idx)
        if idx not in _ONBOARDING:
            self._refresh_membership_role()
            self._update_broadcasts_visibility()

        # Update checked states
        self.btn_home.setChecked(idx == _DASHBOARD)
        self.btn_search.setChecked(idx == _SEARCH)
        self.btn_msg.setChecked(False)
        self.btn_notif.setChecked(False)
        self.btn_settings.setChecked(idx == _SETTINGS)
        self.btn_profile.setChecked(idx in (_PROFILE, _EDIT_PROFILE))
        self.btn_broadcasts.setChecked(idx == _BROADCASTS)

        is_onboarding = idx in _ONBOARDING
        self.sidebar.setVisible(not is_onboarding)
        self._topbar.setVisible(not is_onboarding)

        if idx in _FULLBLEED:
            self.content_layout.setContentsMargins(0, 0, 0, 0)
        else:
            self.content_layout.setContentsMargins(24, 24, 24, 24)

        # Refresh on navigate
        if idx == _DASHBOARD:
            self.dashboard_screen.refresh_dashboard()
        elif idx == _PROFILE:
            self.profile_screen.refresh_profile()
        elif idx == _EDIT_PROFILE:
            self.edit_profile_screen.refresh_profile()
        elif idx == _SETTINGS:
            self.settings_screen.refresh_settings()
        elif idx == _TEAM:
            self.team_screen.refresh()
        elif idx == _CABINET:
            self.cabinet_screen.refresh()
        elif idx == _DEPARTMENT:
            self.department_screen.refresh()
        elif idx == _BROADCASTS:
            self.broadcasts_screen.refresh()

    # ══════════════════════════════════════════════════════════════
    #  Instagram-style slide panels
    # ══════════════════════════════════════════════════════════════

    def _toggle_notifications_panel(self) -> None:
        """Toggle Instagram-style notifications panel from right side."""
        # Close messages if open
        if self._msg_slide.is_panel_visible():
            self._msg_slide.slide_out()
        self.notif_screen.refresh()
        self._notif_slide.toggle()
        self._position_slide_panels()
        self.btn_notif.setChecked(self._notif_slide.is_panel_visible())
        self.btn_msg.setChecked(False)

    def _toggle_messages_panel(self) -> None:
        """Toggle Instagram-style messages panel from right side."""
        # Close notifications if open
        if self._notif_slide.is_panel_visible():
            self._notif_slide.slide_out()
        self.msg_screen.refresh()
        self._msg_slide.toggle()
        self._position_slide_panels()
        self.btn_msg.setChecked(self._msg_slide.is_panel_visible())
        self.btn_notif.setChecked(False)

    def _close_all_panels(self) -> None:
        """Close all open slide panels."""
        if self._notif_slide.is_panel_visible():
            self._notif_slide.slide_out()
        if self._msg_slide.is_panel_visible():
            self._msg_slide.slide_out()
        self.btn_notif.setChecked(False)
        self.btn_msg.setChecked(False)

    def _position_slide_panels(self) -> None:
        """Position slide panels on the right side of the body area."""
        body = self._body_widget
        h = body.height()
        # Notifications panel — right edge
        self._notif_slide.setFixedHeight(h)
        nw = self._notif_slide.width()
        self._notif_slide.move(body.width() - nw, 0)
        # Messages panel — right edge
        self._msg_slide.setFixedHeight(h)
        mw = self._msg_slide.width()
        self._msg_slide.move(body.width() - mw, 0)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_slide_panels()

    def _update_broadcasts_visibility(self) -> None:
        """Show/hide broadcasts button based on role."""
        is_admin_or_manager = session_store.role in ("admin", "manager")
        self.btn_broadcasts.setVisible(is_admin_or_manager)

    # ══════════════════════════════════════════════════════════════
    #  Sidebar helpers
    # ══════════════════════════════════════════════════════════════

    def _nav(self, text: str, svg: str, size: int = 20) -> QPushButton:
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setToolTip(text)
        btn.setIcon(_svg_icon(svg, size))
        btn.setIconSize(QSize(size, size))
        self.nav_buttons.append(btn)
        self.sidebar.register(btn, text)
        return btn

    def _sync_avatar(self) -> None:
        """Update sidebar profile button icon from session avatar."""
        from PySide6.QtGui import QPainterPath
        path = session_store.avatar_path
        if path:
            pix = QPixmap(path)
            if not pix.isNull():
                size = 22
                scaled = pix.scaled(
                    size, size,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation,
                )
                out = QPixmap(size, size)
                out.fill(QColor(0, 0, 0, 0))
                p = QPainter(out)
                p.setRenderHint(QPainter.Antialiasing)
                clip = QPainterPath()
                clip.addEllipse(0, 0, size, size)
                p.setClipPath(clip)
                x = (size - scaled.width()) // 2
                y = (size - scaled.height()) // 2
                p.drawPixmap(x, y, scaled)
                p.end()
                self.btn_profile.setIcon(QIcon(out))
                self.btn_profile.setIconSize(QSize(size, size))
                return
        self.btn_profile.setIcon(_svg_icon(_ICON_USER, 20, "#94a3b8"))
        self.btn_profile.setIconSize(QSize(20, 20))

    # ══════════════════════════════════════════════════════════════
    #  Onboarding
    # ══════════════════════════════════════════════════════════════

    def _auto_login(self) -> None:
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
            self._advance()
        except ApiError:
            session_store.clear()
            self.show_screen(_AUTH)

    def _on_auth_success(self) -> None:
        self._advance()

    def _on_consent_accepted(self) -> None:
        session_store.set_consent_accepted(True)
        org_id = session_store.org_id
        if org_id:
            try:
                api_client.accept_consent(org_id, policy_version="v1")
            except Exception:  # noqa: BLE001
                pass
        self._advance()

    def _on_consent_declined(self) -> None:
        session_store.clear()
        self.show_screen(_AUTH)

    def _on_role_selected(self, role: str) -> None:
        session_store.set_role(role)
        self._advance()

    def _on_profile_done(self) -> None:
        self._advance()

    def _on_join_completed(self) -> None:
        """Called when user successfully joins organization."""
        self._advance()

    def _on_logout(self) -> None:
        session_store.clear()
        self.show_screen(_AUTH)

    def _on_org_changed(self) -> None:
        self.dashboard_screen.refresh_dashboard()

    def _on_org_created(self) -> None:
        self.show_screen(_DASHBOARD)

    def _open_department(self, team_id: str) -> None:
        """Navigate to department detail screen for given team_id."""
        self.department_screen.set_team(team_id)
        self.show_screen(_DEPARTMENT)

    def _open_recording_player(self, session_id: str, recording_id: str) -> None:
        """Navigate to recording player screen."""
        self.recording_player_screen.set_recording(session_id, recording_id)
        self.show_screen(_RECORDING_PLAYER)

    def _advance(self) -> None:
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
        # Member must join org before dashboard
        if session_store.role == "member" and not session_store.org_id:
            self.show_screen(_JOIN_ORG)
            return
        self.show_screen(_DASHBOARD)

    def _refresh_membership_role(self) -> None:
        org_id = session_store.org_id
        if not org_id or not session_store.token:
            return
        try:
            membership = api_client.get_my_membership(org_id)
            role = membership.get("role")
            if isinstance(role, str) and role:
                session_store.set_role(role)
        except ApiError:
            return

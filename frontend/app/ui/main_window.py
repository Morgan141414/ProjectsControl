from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStyle,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.screens.activity import ActivityScreen
from app.ui.screens.admin_console import AdminConsoleScreen
from app.ui.screens.auth import AuthScreen
from app.ui.screens.consent import ConsentDialog
from app.ui.screens.dashboard import DashboardScreen
from app.ui.screens.profile import ProfileScreen
from app.ui.screens.settings import SettingsScreen
from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class SidebarFrame(QFrame):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._on_enter = None
        self._on_leave = None

    def set_handlers(self, on_enter, on_leave) -> None:
        self._on_enter = on_enter
        self._on_leave = on_leave

    def enterEvent(self, event) -> None:  # noqa: N802
        if self._on_enter:
            self._on_enter()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        if self._on_leave:
            self._on_leave()
        super().leaveEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ProjectsControl")
        self.resize(1100, 720)

        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        self.sidebar = SidebarFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar_expanded_width = 220
        self.sidebar_collapsed_width = 64
        self.sidebar.setMinimumWidth(self.sidebar_collapsed_width)
        self.sidebar.setMaximumWidth(self.sidebar_expanded_width)
        self.sidebar_anim = QPropertyAnimation(self.sidebar, b"maximumWidth")
        self.sidebar_anim.setDuration(260)
        self.sidebar_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self.sidebar_anim.finished.connect(self._apply_sidebar_text)
        self._sidebar_target = "collapsed"
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(8)

        self.nav_buttons: list[QPushButton] = []
        self._nav_labels: dict[QPushButton, str] = {}

        self.btn_tasks = self._make_nav_button("Главная", QStyle.SP_DirHomeIcon)
        self.btn_profile = self._make_nav_button("Профиль", QStyle.SP_FileIcon)
        self.btn_settings = self._make_nav_button("Настройки", QStyle.SP_FileDialogListView)

        sidebar_layout.addWidget(self.btn_tasks)
        sidebar_layout.addWidget(self.btn_profile)

        sidebar_layout.addStretch(1)
        sidebar_layout.addWidget(self.btn_settings)

        self.stack = QStackedWidget()
        self.auth_screen = AuthScreen()
        self.dashboard_screen = DashboardScreen()
        self.profile_screen = ProfileScreen()
        self.activity_screen = ActivityScreen()
        self.admin_screen = AdminConsoleScreen()
        self.settings_screen = SettingsScreen()

        self.stack.addWidget(self.auth_screen)
        self.stack.addWidget(self.dashboard_screen)
        self.stack.addWidget(self.profile_screen)
        self.stack.addWidget(self.activity_screen)
        self.stack.addWidget(self.admin_screen)
        self.stack.addWidget(self.settings_screen)

        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.addWidget(self.stack)

        layout.addWidget(self.sidebar)
        layout.addWidget(content_frame)
        self.setCentralWidget(root)

        self.btn_tasks.clicked.connect(lambda: self.show_screen(1))
        self.btn_profile.clicked.connect(lambda: self.show_screen(2))
        self.btn_settings.clicked.connect(lambda: self.show_screen(5))

        self.auth_screen.auth_success.connect(self._handle_auth_success)
        self.dashboard_screen.start_work.connect(lambda: self.show_screen(2))
        self.dashboard_screen.org_changed.connect(self._show_consent_if_needed)
        self.settings_screen.logged_out.connect(self._handle_logout)

        self.sidebar.set_handlers(self._expand_sidebar, self._collapse_sidebar)
        self._collapse_sidebar()
        self._auto_login()

    def show_screen(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        self.btn_tasks.setChecked(index == 1)
        self.btn_profile.setChecked(index == 2)
        self.btn_settings.setChecked(index == 5)

        self.sidebar.setVisible(index >= 1)

        if index == 1:
            self.dashboard_screen.refresh_tasks()
        elif index == 2:
            self.profile_screen.refresh_profile()
        elif index == 5:
            self.settings_screen.refresh_settings()

    def _make_nav_button(self, text: str, icon: QStyle.StandardPixmap) -> QPushButton:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setIcon(self.style().standardIcon(icon))
        button.setIconSize(QSize(18, 18))
        button.setToolTip(text)
        self.nav_buttons.append(button)
        self._nav_labels[button] = text
        return button

    def _expand_sidebar(self) -> None:
        if self._sidebar_target == "expanded":
            return
        self._sidebar_target = "expanded"
        self.sidebar_anim.stop()
        self.sidebar_anim.setStartValue(self.sidebar.maximumWidth())
        self.sidebar_anim.setEndValue(self.sidebar_expanded_width)
        self.sidebar_anim.start()

    def _collapse_sidebar(self) -> None:
        if self._sidebar_target == "collapsed":
            return
        self._sidebar_target = "collapsed"
        for btn in self.nav_buttons:
            btn.setText("")
        self.sidebar_anim.stop()
        self.sidebar_anim.setStartValue(self.sidebar.maximumWidth())
        self.sidebar_anim.setEndValue(self.sidebar_collapsed_width)
        self.sidebar_anim.start()

    def _apply_sidebar_text(self) -> None:
        if self._sidebar_target != "expanded":
            return
        for btn in self.nav_buttons:
            btn.setText(self._nav_labels.get(btn, ""))

    def _auto_login(self) -> None:
        if not session_store.token:
            self.show_screen(0)
            return
        try:
            profile = api_client.get_me()
            session_store.set_user_profile(
                profile.get("id"),
                profile.get("full_name"),
                profile.get("patronymic"),
            )
            self.show_screen(1)
            self._show_consent_if_needed()
        except ApiError:
            session_store.clear()
            self.show_screen(0)

    def _handle_auth_success(self) -> None:
        self.show_screen(1)
        self._show_consent_if_needed()

    def _handle_logout(self) -> None:
        self.show_screen(0)

    def _show_consent_if_needed(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            return
        try:
            status = api_client.get_consent_status(org_id)
        except ApiError:
            return
        if status.get("accepted"):
            return

        dialog = ConsentDialog()
        result = dialog.exec()
        if result:
            try:
                api_client.accept_consent(org_id, policy_version="v1")
            except ApiError:
                return

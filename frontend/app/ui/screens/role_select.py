"""Role selection screen – choose Admin or Member after consent."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RoleCard(QFrame):
    """Clickable role card with icon, title and description."""

    clicked = Signal()

    def __init__(
        self, icon: str, title: str, subtitle: str, features: list[str], parent=None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("RoleCard")
        self.setCursor(Qt.PointingHandCursor)
        self._selected = False

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 28, 28, 28)
        lay.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("font-size: 44px; background: transparent;")
        lay.addWidget(icon_lbl, alignment=Qt.AlignCenter)

        t = QLabel(title)
        t.setObjectName("RoleCardTitle")
        t.setAlignment(Qt.AlignCenter)
        lay.addWidget(t)

        s = QLabel(subtitle)
        s.setObjectName("RoleCardSub")
        s.setAlignment(Qt.AlignCenter)
        s.setWordWrap(True)
        lay.addWidget(s)

        lay.addSpacing(8)

        for feat in features:
            f = QLabel(f"✓  {feat}")
            f.setObjectName("RoleCardFeature")
            f.setWordWrap(True)
            lay.addWidget(f)

        lay.addStretch(1)

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clicked.emit()
        super().mousePressEvent(event)


class RoleSelectScreen(QWidget):
    """Full-screen role selection: Admin or Member."""

    role_selected = Signal(str)  # emits "admin" or "member"

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Center wrapper
        wrapper = QFrame()
        wrapper.setObjectName("RoleWrapper")
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(48, 56, 48, 48)
        wl.setSpacing(16)

        title = QLabel("Выберите вашу роль")
        title.setObjectName("RoleTitle")
        title.setAlignment(Qt.AlignCenter)
        wl.addWidget(title)

        subtitle = QLabel(
            "Это определит ваш интерфейс и возможности в системе"
        )
        subtitle.setObjectName("RoleSub")
        subtitle.setAlignment(Qt.AlignCenter)
        wl.addWidget(subtitle)

        wl.addSpacing(32)

        # Cards row
        cards_row = QHBoxLayout()
        cards_row.setSpacing(24)

        self.admin_card = RoleCard(
            icon="👑",
            title="Администратор",
            subtitle="Создавайте организацию,\nуправляйте командой",
            features=[
                "Создание организации",
                "Управление участниками",
                "Назначение тимлидов",
                "Просмотр аналитики",
                "Настройка проектов",
            ],
        )

        self.member_card = RoleCard(
            icon="💼",
            title="Участник",
            subtitle="Присоединяйтесь к команде,\nвыполняйте задачи",
            features=[
                "Поиск организации",
                "Выполнение задач",
                "Ежедневные отчёты",
                "Личная аналитика",
                "Запись экрана",
            ],
        )

        self.admin_card.clicked.connect(lambda: self._select("admin"))
        self.member_card.clicked.connect(lambda: self._select("member"))

        cards_row.addStretch(1)
        cards_row.addWidget(self.admin_card)
        cards_row.addWidget(self.member_card)
        cards_row.addStretch(1)

        wl.addLayout(cards_row)
        wl.addSpacing(32)

        # Continue button
        self.continue_btn = QPushButton("Продолжить  →")
        self.continue_btn.setObjectName("RoleContinue")
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setEnabled(False)
        self.continue_btn.setFixedWidth(280)
        self.continue_btn.clicked.connect(self._confirm)

        wl.addWidget(self.continue_btn, alignment=Qt.AlignCenter)

        hint = QLabel("Вы сможете изменить роль позже в настройках")
        hint.setObjectName("RoleHint")
        hint.setAlignment(Qt.AlignCenter)
        wl.addWidget(hint)

        wl.addStretch(1)

        root.addWidget(wrapper)

        self._chosen_role: str | None = None

    def _select(self, role: str) -> None:
        self._chosen_role = role
        self.admin_card.set_selected(role == "admin")
        self.member_card.set_selected(role == "member")
        self.continue_btn.setEnabled(True)

    def _confirm(self) -> None:
        if self._chosen_role:
            self.role_selected.emit(self._chosen_role)

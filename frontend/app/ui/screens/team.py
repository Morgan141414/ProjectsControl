"""Штаб screen — shows list of отделы (departments) inside the org.

Admin can create / delete / deactivate departments.
Each department card shows: name, team lead, member count.
Clicking a department opens the DepartmentScreen.
"""

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QMessageBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store

try:
    from PySide6.QtSvg import QSvgRenderer

    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

# ── SVG icons ─────────────────────────────────────────────────────
_ICON_ARROW_LEFT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="19" y1="12" x2="5" y2="12"/>'
    '<polyline points="12 19 5 12 12 5"/></svg>'
)

_ICON_USERS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
    '<circle cx="9" cy="7" r="4"/>'
    '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
    '<path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
)

_ICON_PLUS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="12" y1="5" x2="12" y2="19"/>'
    '<line x1="5" y1="12" x2="19" y2="12"/></svg>'
)

_ICON_TRASH = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="3 6 5 6 21 6"/>'
    '<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4'
    'a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>'
)

_ICON_ARROW_RIGHT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="9 18 15 12 9 6"/></svg>'
)

_ICON_USER = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/></svg>'
)


def _svg_icon(svg_t: str, size: int = 18, color: str = "#8891a5") -> QIcon:
    if not _HAS_SVG:
        return QIcon()
    svg = svg_t.replace("{c}", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return QIcon(pix)


def _svg_pixmap(svg_t: str, size: int = 18, color: str = "#8891a5") -> QPixmap:
    if not _HAS_SVG:
        return QPixmap()
    svg = svg_t.replace("{c}", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return pix


# ── Department card widget ────────────────────────────────────────


class _DeptCard(QFrame):
    """A clickable department card showing name, lead, member count."""

    clicked = Signal(str)   # team_id
    delete_requested = Signal(str)  # team_id

    def __init__(self, team_id: str, name: str, lead_name: str,
                 member_count: int, is_admin: bool) -> None:
        super().__init__()
        self._team_id = team_id
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "_DeptCard{background:#151a2e;border:none;"
            "border-radius:16px;}"
            "_DeptCard:hover{background:#1e2538;}"
        )
        self.setMinimumHeight(100)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(24, 20, 24, 20)
        hl.setSpacing(16)

        # Icon
        icon_bg = QLabel()
        icon_bg.setFixedSize(48, 48)
        icon_bg.setAlignment(Qt.AlignCenter)
        icon_bg.setStyleSheet("background:#3b82f620;border-radius:24px;")
        px = _svg_pixmap(_ICON_USERS, 24, "#3b82f6")
        if not px.isNull():
            icon_bg.setPixmap(px)
        hl.addWidget(icon_bg)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(4)
        text_col.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:700;background:transparent;"
        )
        text_col.addWidget(name_lbl)

        info_parts = []
        if lead_name:
            info_parts.append(f"Тимлид: {lead_name}")
        info_parts.append(f"{member_count} участн.")
        info_lbl = QLabel("  •  ".join(info_parts))
        info_lbl.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )
        text_col.addWidget(info_lbl)

        hl.addLayout(text_col, 1)

        # Delete button (admin only)
        if is_admin:
            del_btn = QPushButton()
            del_btn.setFixedSize(32, 32)
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setIcon(_svg_icon(_ICON_TRASH, 16, "#ef4444"))
            del_btn.setStyleSheet(
                "QPushButton{background:transparent;border:none;border-radius:6px;}"
                "QPushButton:hover{background:#ef444420;}"
            )
            del_btn.clicked.connect(lambda: self.delete_requested.emit(self._team_id))
            hl.addWidget(del_btn)

        # Arrow
        arrow = QLabel()
        arrow.setFixedSize(20, 20)
        arrow.setStyleSheet("background:transparent;")
        ap = _svg_pixmap(_ICON_ARROW_RIGHT, 16, "#4a5068")
        if not ap.isNull():
            arrow.setPixmap(ap)
        hl.addWidget(arrow)

    def mousePressEvent(self, ev):
        self.clicked.emit(self._team_id)
        super().mousePressEvent(ev)


# ═══════════════════════════════════════════════════════════════════════
#  TeamScreen (Штаб) — list of departments
# ═══════════════════════════════════════════════════════════════════════


class TeamScreen(QWidget):
    """Штаб screen — shows all отделы (departments) in the org."""

    go_back = Signal()
    open_cabinet = Signal()
    open_department = Signal(str)  # team_id

    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet("background:#0c1021;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("background:#0c1021;border-bottom:1px solid #1e2538;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 10, 20, 10)

        back = QPushButton()
        back.setCursor(Qt.PointingHandCursor)
        back.setIcon(_svg_icon(_ICON_ARROW_LEFT, 20, "#8891a5"))
        back.setFixedSize(36, 36)
        back.setStyleSheet(
            "QPushButton{background:transparent;border:none;}"
            "QPushButton:hover{background:#1e2538;border-radius:6px;}"
        )
        back.clicked.connect(self.go_back.emit)

        title = QLabel("Ваш штаб")
        title.setStyleSheet(
            "color:#e8eaf0;font-size:18px;font-weight:700;background:transparent;"
        )

        hl.addWidget(back)
        hl.addWidget(title, 1)
        outer.addWidget(header)

        # ── Scroll body ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#0c1021;border:none;")

        body = QWidget()
        body.setStyleSheet("background:#0c1021;")
        self._body_lay = QVBoxLayout(body)
        self._body_lay.setContentsMargins(28, 24, 28, 28)
        self._body_lay.setSpacing(16)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # ── Create department section (admin only) ────────────────
        self._create_section = QFrame()
        self._create_section.setStyleSheet(
            "QFrame{background:#151a2e;border:none;border-radius:14px;}"
        )
        cs = QHBoxLayout(self._create_section)
        cs.setContentsMargins(20, 16, 20, 16)
        cs.setSpacing(12)

        self._dept_input = QLineEdit()
        self._dept_input.setPlaceholderText("Название нового отдела...")
        self._dept_input.setFixedHeight(40)
        self._dept_input.setStyleSheet(
            "QLineEdit{background:#1e2538;color:#e8eaf0;font-size:14px;"
            "border:none;border-radius:10px;padding:0 14px;}"
            "QLineEdit:focus{background:#2a3150;}"
        )
        self._dept_input.returnPressed.connect(self._create_dept)
        cs.addWidget(self._dept_input, 1)

        create_btn = QPushButton("Создать")
        create_btn.setCursor(Qt.PointingHandCursor)
        create_btn.setFixedHeight(40)
        create_btn.setStyleSheet(
            "QPushButton{background:#4f8fff;color:#0c1021;font-size:14px;"
            "font-weight:600;border:none;border-radius:10px;padding:0 20px;}"
            "QPushButton:hover{background:#6ba3ff;}"
        )
        create_btn.clicked.connect(self._create_dept)
        cs.addWidget(create_btn)

        self._body_lay.addWidget(self._create_section)

        # ── Department list ───────────────────────────────────────
        self._dept_list = QVBoxLayout()
        self._dept_list.setSpacing(12)
        self._body_lay.addLayout(self._dept_list)

        # ── Empty state ───────────────────────────────────────────
        self._empty_label = QLabel("В штабе пока нет отделов")
        self._empty_label.setStyleSheet(
            "color:#4a5068;font-size:14px;background:transparent;"
        )
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._body_lay.addWidget(self._empty_label)
        self._body_lay.addStretch(1)

    # ── Public ────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Reload departments (teams) from API."""
        is_admin = session_store.role in ("admin", "manager")
        self._create_section.setVisible(is_admin)

        # Clear existing cards
        while self._dept_list.count():
            item = self._dept_list.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        org_id = session_store.org_id
        if not org_id:
            self._empty_label.setVisible(True)
            return

        try:
            teams = api_client.list_teams(org_id)
        except Exception:  # noqa: BLE001
            teams = []

        self._empty_label.setVisible(len(teams) == 0)

        for t in teams:
            tid = t.get("id", "")
            name = t.get("name", "Отдел")
            members = t.get("members", [])
            lead_name = ""
            for m in members:
                if m.get("role") == "lead":
                    lead_name = m.get("full_name") or "Тимлид"
                    break
            card = _DeptCard(tid, name, lead_name, len(members),
                           session_store.role in ("admin", "manager"))
            card.clicked.connect(self._on_dept_clicked)
            card.delete_requested.connect(self._on_dept_delete)
            self._dept_list.addWidget(card)

    # ── Private ───────────────────────────────────────────────────

    def _on_dept_clicked(self, team_id: str) -> None:
        self.open_department.emit(team_id)

    def _on_dept_delete(self, team_id: str) -> None:
        org_id = session_store.org_id
        if not org_id:
            return
        try:
            api_client.delete_team(org_id, team_id)
        except Exception:  # noqa: BLE001
            pass
        self.refresh()

    def _create_dept(self) -> None:
        name = self._dept_input.text().strip()
        if not name:
            return
        org_id = session_store.org_id
        if not org_id:
            return
        try:
            api_client.create_team(org_id, name, None)
            self._dept_input.clear()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Ошибка создания отдела", str(exc))
        self.refresh()

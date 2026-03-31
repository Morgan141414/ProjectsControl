"""Messages screen — Instagram Direct style side panel.

Slides in from the right. Shows conversation list + empty state.
Matches Instagram direct/inbox layout.
"""

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.state.session import session_store

try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

# ── SVG icons ─────────────────────────────────────────────────────────
_ICON_EDIT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
    '<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>'
)

_ICON_SEND = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="22" y1="2" x2="11" y2="13"/>'
    '<polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>'
)

_ICON_CHEVRON_DOWN = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="6 9 12 15 18 9"/></svg>'
)

_ICON_USER = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/></svg>'
)

_ICON_X = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="18" y1="6" x2="6" y2="18"/>'
    '<line x1="6" y1="6" x2="18" y2="18"/></svg>'
)


def _svg_icon(svg_t: str, size: int = 20, color: str = "#8891a5") -> QIcon:
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


def _svg_pixmap(svg_t: str, size: int = 20, color: str = "#8891a5") -> QPixmap:
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


# ═══════════════════════════════════════════════════════════════════════
#  ChatItem — single conversation row
# ═══════════════════════════════════════════════════════════════════════

class ChatItem(QFrame):
    """Single conversation row in chat list, like Instagram DM."""

    clicked = Signal(str)  # user_id

    def __init__(self, user_id: str, name: str, last_msg: str = "",
                 time_str: str = "", parent=None) -> None:
        super().__init__(parent)
        self._uid = user_id
        self.setObjectName("ChatItem")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(68)
        self.setStyleSheet(
            "ChatItem{background:transparent;border-radius:0;}"
            "ChatItem:hover{background:#151a2e;}"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 8, 16, 8)
        lay.setSpacing(12)

        # Avatar circle
        avatar = QLabel()
        avatar.setFixedSize(48, 48)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(
            "background:#1e2538;border-radius:24px;border:1px solid #2a3150;"
        )
        ic = _svg_icon(_ICON_USER, 22, "#4a5068")
        if not ic.isNull():
            avatar.setPixmap(ic.pixmap(22, 22))
        lay.addWidget(avatar)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        name_row = QHBoxLayout()
        name_row.setSpacing(0)
        n = QLabel(name)
        n.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:600;background:transparent;"
        )
        name_row.addWidget(n)
        name_row.addStretch(1)
        if time_str:
            t = QLabel(time_str)
            t.setStyleSheet("color:#4a5068;font-size:12px;background:transparent;")
            name_row.addWidget(t)
        text_col.addLayout(name_row)

        if last_msg:
            m = QLabel(last_msg)
            m.setStyleSheet("color:#8891a5;font-size:13px;background:transparent;")
            m.setMaximumWidth(280)
            text_col.addWidget(m)

        lay.addLayout(text_col, 1)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit(self._uid)
        super().mousePressEvent(event)


# ═══════════════════════════════════════════════════════════════════════
#  MessagesScreen — Instagram Direct-style side panel
# ═══════════════════════════════════════════════════════════════════════


class MessagesScreen(QWidget):
    """Instagram Direct-style messages side panel."""

    go_back = Signal()

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setStyleSheet("background:#0c1021;")

        # ── Header: username + new message + close ────────────────
        lh = QFrame()
        lh.setStyleSheet("background:#0c1021;border-bottom:1px solid #1e2538;")
        lhl = QHBoxLayout(lh)
        lhl.setContentsMargins(16, 14, 12, 14)

        self._username_label = QLabel(session_store.full_name or "Пользователь")
        self._username_label.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:700;background:transparent;"
        )
        chevron_lbl = QLabel()
        cp = _svg_pixmap(_ICON_CHEVRON_DOWN, 16, "#e8eaf0")
        if not cp.isNull():
            chevron_lbl.setPixmap(cp)
        chevron_lbl.setStyleSheet("background:transparent;")

        new_btn = QPushButton()
        new_btn.setFixedSize(32, 32)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.setIcon(_svg_icon(_ICON_EDIT, 18, "#e8eaf0"))
        new_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;border-radius:16px;}"
            "QPushButton:hover{background:#1e2538;}"
        )

        close_btn = QPushButton()
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(32, 32)
        close_btn.setIcon(_svg_icon(_ICON_X, 18, "#8891a5"))
        close_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;border-radius:16px;}"
            "QPushButton:hover{background:#1e2538;}"
        )
        close_btn.clicked.connect(self.go_back.emit)

        lhl.addWidget(self._username_label)
        lhl.addWidget(chevron_lbl)
        lhl.addStretch(1)
        lhl.addWidget(new_btn)
        lhl.addWidget(close_btn)
        root.addWidget(lh)

        # ── Search ────────────────────────────────────────────────
        search_wrap = QWidget()
        search_wrap.setStyleSheet("background:#0c1021;")
        sw_lay = QVBoxLayout(search_wrap)
        sw_lay.setContentsMargins(16, 10, 16, 6)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск")
        self.search_input.setObjectName("MsgSearchInput")
        self.search_input.setFixedHeight(36)
        sw_lay.addWidget(self.search_input)
        root.addWidget(search_wrap)

        # ── Tabs: Сообщения / Запросы ─────────────────────────────
        tab_row = QFrame()
        tab_row.setStyleSheet("background:#0c1021;")
        trl = QHBoxLayout(tab_row)
        trl.setContentsMargins(0, 0, 0, 0)
        trl.setSpacing(0)

        self._tab_msgs = QPushButton("Сообщения")
        self._tab_msgs.setStyleSheet(
            "QPushButton{color:#e8eaf0;font-size:14px;font-weight:700;"
            "background:transparent;border:none;border-bottom:1px solid #e8eaf0;"
            "padding:10px 20px;}"
        )
        self._tab_reqs = QPushButton("Запросы")
        self._tab_reqs.setStyleSheet(
            "QPushButton{color:#4a5068;font-size:14px;font-weight:600;"
            "background:transparent;border:none;border-bottom:1px solid transparent;"
            "padding:10px 20px;}"
            "QPushButton:hover{color:#8891a5;}"
        )
        trl.addWidget(self._tab_msgs, 1)
        trl.addWidget(self._tab_reqs, 1)
        root.addWidget(tab_row)

        # ── Chat list / Empty state ───────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#0c1021;border:none;")

        self._chat_container = QWidget()
        self._chat_container.setStyleSheet("background:#0c1021;")
        self._chat_layout = QVBoxLayout(self._chat_container)
        self._chat_layout.setContentsMargins(0, 0, 0, 0)
        self._chat_layout.setSpacing(0)

        # Empty state
        self._empty_state = QWidget()
        self._empty_state.setStyleSheet("background:transparent;")
        el = QVBoxLayout(self._empty_state)
        el.setContentsMargins(0, 60, 0, 0)
        el.setSpacing(14)
        el.setAlignment(Qt.AlignCenter)

        # Send icon circle
        icon_frame = QFrame()
        icon_frame.setFixedSize(80, 80)
        icon_frame.setStyleSheet(
            "background:transparent;border:2px solid #e8eaf0;border-radius:40px;"
        )
        if_lay = QVBoxLayout(icon_frame)
        if_lay.setContentsMargins(0, 0, 0, 0)
        send_lbl = QLabel()
        send_lbl.setAlignment(Qt.AlignCenter)
        sp = _svg_pixmap(_ICON_SEND, 32, "#e8eaf0")
        if not sp.isNull():
            send_lbl.setPixmap(sp)
        send_lbl.setStyleSheet("background:transparent;border:none;")
        if_lay.addWidget(send_lbl)

        title = QLabel("Ваши сообщения")
        title.setStyleSheet(
            "color:#e8eaf0;font-size:18px;font-weight:700;background:transparent;"
        )
        title.setAlignment(Qt.AlignCenter)

        hint = QLabel("Отправляйте личные фото\nи сообщения другу или группе")
        hint.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)

        send_btn = QPushButton("Отправить сообщение")
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.setStyleSheet(
            "QPushButton{background:#3b82f6;color:#ffffff;font-size:14px;"
            "font-weight:600;border:none;border-radius:8px;padding:8px 18px;}"
            "QPushButton:hover{background:#60a5fa;}"
        )

        el.addWidget(icon_frame, 0, Qt.AlignCenter)
        el.addWidget(title)
        el.addWidget(hint)
        el.addSpacing(4)
        el.addWidget(send_btn, 0, Qt.AlignCenter)
        el.addStretch(1)

        self._chat_layout.addWidget(self._empty_state)
        self._chat_layout.addStretch(1)

        scroll.setWidget(self._chat_container)
        root.addWidget(scroll, 1)

    def refresh(self) -> None:
        """Load conversations (placeholder)."""
        self._username_label.setText(session_store.full_name or "Пользователь")

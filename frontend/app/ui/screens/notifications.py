"""Notifications panel — Instagram-style side panel.

Slides in from the right side of the screen.
Sections: Новинки / На этой неделе / В этом месяце.
Close button (X) at top right.
"""

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
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

# ── SVG icons ─────────────────────────────────────────────────────────

_ICON_USER_PLUS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
    '<circle cx="8.5" cy="7" r="4"/>'
    '<line x1="20" y1="8" x2="20" y2="14"/>'
    '<line x1="23" y1="11" x2="17" y2="11"/></svg>'
)

_ICON_USER = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/></svg>'
)

_ICON_BELL = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>'
    '<path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>'
)

_ICON_X = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="18" y1="6" x2="6" y2="18"/>'
    '<line x1="6" y1="6" x2="18" y2="18"/></svg>'
)


def _svg_icon(svg_template: str, size: int = 18, color: str = "#8891a5") -> QIcon:
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


def _svg_pixmap(svg_template: str, size: int = 18, color: str = "#8891a5") -> QPixmap:
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
#  NotifItem — single notification row (Instagram-style)
# ═══════════════════════════════════════════════════════════════════════


class NotifItem(QFrame):
    """Notification row: circular avatar + text + time + optional buttons."""

    action_taken = Signal(str, str)  # (notif_id, action)

    def __init__(
        self,
        notif_id: str,
        icon_svg: str,
        icon_color: str,
        title: str,
        body: str,
        time_str: str = "",
        actions: list[tuple[str, str]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("NotifItem")
        self._notif_id = notif_id
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(12)

        # Circular avatar with SVG icon
        avatar = QFrame()
        avatar.setFixedSize(44, 44)
        avatar.setStyleSheet(
            "background:#1e2538;border-radius:22px;border:1px solid #2a3150;"
        )
        av_lay = QVBoxLayout(avatar)
        av_lay.setContentsMargins(0, 0, 0, 0)
        av_label = QLabel()
        av_label.setAlignment(Qt.AlignCenter)
        av_label.setStyleSheet("background:transparent;border:none;")
        ic = _svg_pixmap(icon_svg, 22, icon_color)
        if not ic.isNull():
            av_label.setPixmap(ic)
        av_lay.addWidget(av_label)
        lay.addWidget(avatar)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        # Title row with inline time
        title_text = f"<b style='color:#e8eaf0'>{title}</b>"
        if body:
            title_text += f" <span style='color:#8891a5'>{body}</span>"
        if time_str:
            title_text += f" <span style='color:#4a5068'>{time_str}</span>"

        t = QLabel(title_text)
        t.setTextFormat(Qt.RichText)
        t.setWordWrap(True)
        t.setStyleSheet("font-size:13px;background:transparent;color:#e8eaf0;")
        text_col.addWidget(t)

        lay.addLayout(text_col, 1)

        # Action buttons (Подтвердить / Удалить)
        if actions:
            for label, action_key in actions:
                btn = QPushButton(label)
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFixedHeight(30)
                if action_key == "accept":
                    btn.setStyleSheet(
                        "QPushButton{background:#3b82f6;color:#ffffff;font-size:12px;"
                        "font-weight:600;border:none;border-radius:8px;padding:4px 14px;}"
                        "QPushButton:hover{background:#60a5fa;}"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton{background:#1e2538;color:#e8eaf0;font-size:12px;"
                        "font-weight:600;border:1px solid #2a3150;border-radius:8px;"
                        "padding:4px 14px;}"
                        "QPushButton:hover{background:#2a3150;}"
                    )
                btn.clicked.connect(
                    lambda checked=False, a=action_key: self.action_taken.emit(
                        self._notif_id, a
                    )
                )
                lay.addWidget(btn)


# ═══════════════════════════════════════════════════════════════════════
#  NotificationsPanel — Instagram-style side panel
# ═══════════════════════════════════════════════════════════════════════


class NotificationsPanel(QWidget):
    """Instagram-style notification side panel."""

    go_back = Signal()

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setStyleSheet("background:#0c1021;")

        # ── Header with title + close button ──────────────────────
        header = QFrame()
        header.setStyleSheet(
            "background:#0c1021;border-bottom:1px solid #1e2538;"
        )
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 14, 12, 14)

        title = QLabel("Уведомления")
        title.setStyleSheet(
            "color:#e8eaf0;font-size:20px;font-weight:700;background:transparent;"
        )
        hl.addWidget(title)
        hl.addStretch(1)

        close_btn = QPushButton()
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(32, 32)
        close_btn.setIcon(_svg_icon(_ICON_X, 18, "#8891a5"))
        close_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;border-radius:16px;}"
            "QPushButton:hover{background:#1e2538;}"
        )
        close_btn.clicked.connect(self.go_back.emit)
        hl.addWidget(close_btn)
        root.addWidget(header)

        # ── Sections scroll area ──────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#0c1021;border:none;")

        self._container = QWidget()
        self._container.setStyleSheet("background:#0c1021;")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(0, 4, 0, 16)
        self._layout.setSpacing(0)

        # Section: Новинки (Today)
        self._today_label = QLabel("Новинки")
        self._today_label.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:700;"
            "background:transparent;padding:12px 16px 6px 16px;"
        )
        self._layout.addWidget(self._today_label)

        self._today_section = QVBoxLayout()
        self._today_section.setSpacing(0)
        self._layout.addLayout(self._today_section)

        # Section: На этой неделе
        self._week_label = QLabel("На этой неделе")
        self._week_label.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:700;"
            "background:transparent;padding:16px 16px 6px 16px;"
        )
        self._layout.addWidget(self._week_label)

        self._week_section = QVBoxLayout()
        self._week_section.setSpacing(0)
        self._layout.addLayout(self._week_section)

        # Section: В этом месяце
        self._month_label = QLabel("В этом месяце")
        self._month_label.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:700;"
            "background:transparent;padding:16px 16px 6px 16px;"
        )
        self._layout.addWidget(self._month_label)

        self._month_section = QVBoxLayout()
        self._month_section.setSpacing(0)
        self._layout.addLayout(self._month_section)

        self._layout.addStretch(1)
        scroll.setWidget(self._container)
        root.addWidget(scroll, 1)

    # ══════════════════════════════════════════════════════════════
    #  Public
    # ══════════════════════════════════════════════════════════════

    def refresh(self) -> None:
        """Load notifications."""
        self._clear_section(self._today_section)
        self._clear_section(self._week_section)
        self._clear_section(self._month_section)

        org_id = session_store.org_id
        is_admin = session_store.role in ("admin", "manager")
        has_items = False

        # Load join requests for admin
        if is_admin and org_id:
            try:
                requests = api_client.list_join_requests(org_id)
                for req in requests:
                    if req.get("status") != "pending":
                        continue
                    user = req.get("user_full_name") or req.get(
                        "user_email", "Пользователь"
                    )
                    nw = NotifItem(
                        notif_id=req.get("id", ""),
                        icon_svg=_ICON_USER_PLUS,
                        icon_color="#3b82f6",
                        title=user,
                        body="запрашивает вступление в вашу компанию",
                        time_str="сейчас",
                        actions=[("Подтвердить", "accept"), ("Удалить", "decline")],
                    )
                    nw.action_taken.connect(self._handle_request_action)
                    self._today_section.addWidget(nw)
                    has_items = True
            except (ApiError, Exception):  # noqa: BLE001
                pass

        # Empty state
        if not has_items:
            empty_w = QWidget()
            empty_w.setStyleSheet("background:transparent;")
            el = QVBoxLayout(empty_w)
            el.setContentsMargins(0, 50, 0, 0)
            el.setSpacing(12)

            ic_frame = QFrame()
            ic_frame.setFixedSize(72, 72)
            ic_frame.setStyleSheet(
                "background:transparent;border:2px solid #2a3150;border-radius:36px;"
            )
            icl = QVBoxLayout(ic_frame)
            icl.setContentsMargins(0, 0, 0, 0)
            bell_lbl = QLabel()
            bell_lbl.setAlignment(Qt.AlignCenter)
            bell_lbl.setStyleSheet("background:transparent;border:none;")
            bp = _svg_pixmap(_ICON_BELL, 28, "#4a5068")
            if not bp.isNull():
                bell_lbl.setPixmap(bp)
            icl.addWidget(bell_lbl)

            et = QLabel("Нет активности")
            et.setStyleSheet(
                "color:#e8eaf0;font-size:17px;font-weight:700;background:transparent;"
            )
            et.setAlignment(Qt.AlignCenter)

            eh = QLabel(
                "Когда кто-то отправит запрос\nили упомянет вас, это появится здесь."
            )
            eh.setStyleSheet("color:#8891a5;font-size:13px;background:transparent;")
            eh.setAlignment(Qt.AlignCenter)
            eh.setWordWrap(True)

            el.addWidget(ic_frame, 0, Qt.AlignCenter)
            el.addWidget(et)
            el.addWidget(eh)
            el.addStretch(1)
            self._today_section.addWidget(empty_w)

        self._week_label.setVisible(False)
        self._month_label.setVisible(False)

    @staticmethod
    def _clear_section(section) -> None:
        while section.count():
            item = section.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _handle_request_action(self, request_id: str, action: str) -> None:
        org_id = session_store.org_id
        if not org_id or not request_id:
            return
        try:
            if action == "accept":
                api_client.approve_join_request(org_id, request_id)
            else:
                api_client.reject_join_request(org_id, request_id)
            self.refresh()
        except (ApiError, Exception):  # noqa: BLE001
            pass

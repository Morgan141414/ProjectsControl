"""Search screen — Instagram-style search overlay for finding colleagues."""

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

from app.services.api_client import api_client
from app.state.session import session_store

try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

# ── SVG icons ─────────────────────────────────────────────────────────
_ICON_SEARCH = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="11" cy="11" r="8"/>'
    '<line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>'
)

_ICON_X = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="18" y1="6" x2="6" y2="18"/>'
    '<line x1="6" y1="6" x2="18" y2="18"/></svg>'
)

_ICON_USER = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/></svg>'
)

_ICON_CLOCK = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<polyline points="12 6 12 12 16 14"/></svg>'
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


# ── User result item ─────────────────────────────────────────────────


class _UserItem(QFrame):
    """A single search result row — avatar + name + info."""

    clicked = Signal(str)  # user_id

    def __init__(self, user_id: str, full_name: str, info: str = "") -> None:
        super().__init__()
        self._uid = user_id
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "_UserItem{background:transparent;border:none;padding:8px 0;}"
            "_UserItem:hover{background:#151a2e;}"
        )

        hl = QHBoxLayout(self)
        hl.setContentsMargins(20, 8, 20, 8)
        hl.setSpacing(14)

        # Avatar
        avatar = QLabel()
        avatar.setFixedSize(48, 48)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("background:#1e2538;border-radius:24px;")
        pix = _svg_pixmap(_ICON_USER, 22, "#4a5068")
        if not pix.isNull():
            avatar.setPixmap(pix)
        hl.addWidget(avatar)

        # Text
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(full_name)
        name_lbl.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:600;background:transparent;"
        )

        info_lbl = QLabel(info)
        info_lbl.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )
        info_lbl.setVisible(bool(info))

        text_col.addWidget(name_lbl)
        text_col.addWidget(info_lbl)
        hl.addLayout(text_col, 1)

    def mousePressEvent(self, event):
        self.clicked.emit(self._uid)
        super().mousePressEvent(event)


# ── Recent search item ───────────────────────────────────────────────


class _RecentItem(QFrame):
    """A single 'recent search' row with X button."""

    remove_requested = Signal(str)

    def __init__(self, text: str) -> None:
        super().__init__()
        self.setStyleSheet(
            "_RecentItem{background:transparent;border:none;}"
            "_RecentItem:hover{background:#151a2e;}"
        )

        hl = QHBoxLayout(self)
        hl.setContentsMargins(20, 8, 20, 8)
        hl.setSpacing(14)

        # Clock icon
        clock = QLabel()
        clock.setFixedSize(24, 24)
        clock.setAlignment(Qt.AlignCenter)
        clock.setStyleSheet("background:transparent;")
        pix = _svg_pixmap(_ICON_CLOCK, 18, "#4a5068")
        if not pix.isNull():
            clock.setPixmap(pix)
        hl.addWidget(clock)

        # Text
        lbl = QLabel(text)
        lbl.setStyleSheet("color:#e8eaf0;font-size:14px;background:transparent;")
        hl.addWidget(lbl, 1)

        # X button
        x_btn = QPushButton()
        x_btn.setFixedSize(20, 20)
        x_btn.setIcon(_svg_icon(_ICON_X, 14, "#4a5068"))
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.setStyleSheet("QPushButton{background:transparent;border:none;}")
        x_btn.clicked.connect(lambda: self.remove_requested.emit(text))
        hl.addWidget(x_btn)


# ═══════════════════════════════════════════════════════════════════════
#  SearchScreen
# ═══════════════════════════════════════════════════════════════════════


class SearchScreen(QWidget):
    """Instagram-style search panel.

    - Search input at top
    - 'Недавнее' (recent) section with clear button
    - Live user search results
    """

    go_back = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet("background:#0c1021;")

        self._recent_searches: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("background:#0c1021;border-bottom:1px solid #1e2538;")
        h_lay = QVBoxLayout(header)
        h_lay.setContentsMargins(20, 16, 20, 16)
        h_lay.setSpacing(16)

        title = QLabel("Поиск")
        title.setStyleSheet(
            "color:#e8eaf0;font-size:22px;font-weight:700;background:transparent;"
        )
        h_lay.addWidget(title)

        # Search input
        search_row = QHBoxLayout()
        search_row.setSpacing(0)

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск сотрудников...")
        self._search_input.setFixedHeight(36)
        self._search_input.setStyleSheet(
            "QLineEdit{background:#1e2538;color:#e8eaf0;font-size:14px;"
            "border:none;border-radius:10px;padding:0 36px 0 36px;}"
            "QLineEdit:focus{background:#2a3150;}"
        )
        self._search_input.textChanged.connect(self._on_text_changed)

        search_row.addWidget(self._search_input)
        h_lay.addLayout(search_row)

        outer.addWidget(header)

        # ── Scrollable body ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#0c1021;border:none;")

        self._body = QWidget()
        self._body.setStyleSheet("background:#0c1021;")
        self._body_layout = QVBoxLayout(self._body)
        self._body_layout.setContentsMargins(0, 0, 0, 0)
        self._body_layout.setSpacing(0)
        self._body_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self._body)
        outer.addWidget(scroll, 1)

        # Show initial state
        self._show_recent_section()

    # ── Recent searches ───────────────────────────────────────────

    def _show_recent_section(self) -> None:
        self._clear_body()

        # Section header
        sec_header = QWidget()
        sec_header.setStyleSheet("background:transparent;")
        sh = QHBoxLayout(sec_header)
        sh.setContentsMargins(20, 16, 20, 8)

        lbl = QLabel("Недавнее")
        lbl.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:600;background:transparent;"
        )
        sh.addWidget(lbl, 1)

        if self._recent_searches:
            clear_btn = QPushButton("Очистить всё")
            clear_btn.setCursor(Qt.PointingHandCursor)
            clear_btn.setStyleSheet(
                "QPushButton{color:#4f8fff;font-size:13px;font-weight:600;"
                "background:transparent;border:none;}"
                "QPushButton:hover{color:#6ba3ff;}"
            )
            clear_btn.clicked.connect(self._clear_recent)
            sh.addWidget(clear_btn)

        self._body_layout.addWidget(sec_header)

        if not self._recent_searches:
            no_recent = QLabel("Нет недавних поисков.")
            no_recent.setStyleSheet(
                "color:#4a5068;font-size:14px;background:transparent;"
                "padding:20px;"
            )
            no_recent.setAlignment(Qt.AlignCenter)
            self._body_layout.addWidget(no_recent)
        else:
            for text in self._recent_searches:
                item = _RecentItem(text)
                item.remove_requested.connect(self._remove_recent)
                self._body_layout.addWidget(item)

    def _clear_recent(self) -> None:
        self._recent_searches.clear()
        self._show_recent_section()

    def _remove_recent(self, text: str) -> None:
        if text in self._recent_searches:
            self._recent_searches.remove(text)
        self._show_recent_section()

    # ── Search ────────────────────────────────────────────────────

    def _on_text_changed(self, text: str) -> None:
        query = text.strip()
        if not query:
            self._show_recent_section()
            return
        self._do_search(query)

    def _do_search(self, query: str) -> None:
        self._clear_body()

        # Try API search
        users = []
        try:
            if hasattr(api_client, "search_users"):
                users = api_client.search_users(query) or []
        except Exception:
            pass

        if not users:
            # Show "no results" state
            empty = QLabel(f"По запросу «{query}» ничего не найдено")
            empty.setWordWrap(True)
            empty.setStyleSheet(
                "color:#4a5068;font-size:14px;background:transparent;padding:40px 20px;"
            )
            empty.setAlignment(Qt.AlignCenter)
            self._body_layout.addWidget(empty)
            return

        for u in users:
            uid = u.get("id", "")
            name = u.get("full_name") or "Пользователь"
            spec = u.get("specialty") or ""
            item = _UserItem(uid, name, spec)
            item.clicked.connect(self._on_user_clicked)
            self._body_layout.addWidget(item)

    def _on_user_clicked(self, user_id: str) -> None:
        """Handle tap on a user result — add to recent searches."""
        query = self._search_input.text().strip()
        if query and query not in self._recent_searches:
            self._recent_searches.insert(0, query)
            if len(self._recent_searches) > 10:
                self._recent_searches.pop()

    # ── Helpers ───────────────────────────────────────────────────

    def _clear_body(self) -> None:
        while self._body_layout.count():
            item = self._body_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def refresh(self) -> None:
        """Called when screen becomes visible."""
        self._search_input.clear()
        self._show_recent_section()
        self._search_input.setFocus()

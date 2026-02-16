"""Dashboard – context-aware home screen.

No org:  greeting + unified search to join organisation
Has org: hero banner with org info + 2 navigation cards
"""

from datetime import datetime

from PySide6.QtCore import QByteArray, QPoint, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
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
_ICON_PLUS_CIRCLE = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<line x1="12" y1="8" x2="12" y2="16"/>'
    '<line x1="8" y1="12" x2="16" y2="12"/></svg>'
)

_ICON_SMILE = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<path d="M8 14s1.5 2 4 2 4-2 4-2"/>'
    '<line x1="9" y1="9" x2="9.01" y2="9"/>'
    '<line x1="15" y1="9" x2="15.01" y2="9"/></svg>'
)

_ICON_BUILDING = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="4" y="2" width="16" height="20" rx="2" ry="2"/>'
    '<path d="M9 22V12h6v10"/>'
    '<line x1="8" y1="6" x2="8.01" y2="6"/>'
    '<line x1="16" y1="6" x2="16.01" y2="6"/>'
    '<line x1="12" y1="6" x2="12.01" y2="6"/>'
    '<line x1="8" y1="10" x2="8.01" y2="10"/>'
    '<line x1="16" y1="10" x2="16.01" y2="10"/></svg>'
)

_ICON_USERS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
    '<circle cx="9" cy="7" r="4"/>'
    '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
    '<path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
)

_ICON_CLIPBOARD = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6'
    'a2 2 0 0 1 2-2h2"/>'
    '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>'
)

_ICON_ARROW = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="5" y1="12" x2="19" y2="12"/>'
    '<polyline points="12 5 19 12 12 19"/></svg>'
)

_ICON_MENU = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="3" y1="6" x2="21" y2="6"/>'
    '<line x1="3" y1="12" x2="21" y2="12"/>'
    '<line x1="3" y1="18" x2="21" y2="18"/></svg>'
)

_ICON_PALETTE = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="13.5" cy="6.5" r="0.5" fill="{c}"/>'
    '<circle cx="17.5" cy="10.5" r="0.5" fill="{c}"/>'
    '<circle cx="8.5" cy="7.5" r="0.5" fill="{c}"/>'
    '<circle cx="6.5" cy="12" r="0.5" fill="{c}"/>'
    '<path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.93 0 1.5-.67'
    ' 1.5-1.5 0-.39-.14-.74-.39-1.04-.24-.3-.39-.65-.39-1.04'
    ' 0-.83.67-1.5 1.5-1.5H16c3.31 0 6-2.69 6-6 0-5.52-4.48-9.96-10-9.96Z"/></svg>'
)


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


def _round_pixmap(pix: QPixmap, size: int) -> QPixmap:
    """Clip a pixmap to a circle."""
    scaled = pix.scaled(
        size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
    )
    out = QPixmap(size, size)
    out.fill(QColor(0, 0, 0, 0))
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)
    painter.end()
    return out


def _letter_avatar(letter: str, size: int, bg: str = "#4f8fff") -> QPixmap:
    """Create a circular avatar with a single letter."""
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.fillRect(0, 0, size, size, QColor(bg))
    font = QFont("Segoe UI", int(size * 0.42))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    from PySide6.QtCore import QRectF
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, letter.upper())
    painter.end()
    return pix


# ── Clickable navigation card ────────────────────────────────────


class _NavCard(QFrame):
    """Card with icon, title, description and click action."""

    clicked = Signal()

    def __init__(self, icon_svg: str, icon_color: str, title: str, desc: str) -> None:
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(
            "_NavCard{background:#151a2e;border:1px solid #1e2538;"
            "border-radius:18px;}"
            "_NavCard:hover{background:#1e2538;border-color:#2563eb40;}"
        )
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(200)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(12)

        # Icon circle
        icon_bg = QLabel()
        icon_bg.setFixedSize(48, 48)
        icon_bg.setAlignment(Qt.AlignCenter)
        icon_bg.setStyleSheet(f"background:{icon_color}20;border-radius:24px;")
        pix = _svg_pixmap(icon_svg, 24, icon_color)
        if not pix.isNull():
            icon_bg.setPixmap(pix)
        lay.addWidget(icon_bg)

        t = QLabel(title)
        t.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:700;background:transparent;"
        )
        t.setWordWrap(True)
        lay.addWidget(t)

        d = QLabel(desc)
        d.setStyleSheet("color:#8891a5;font-size:13px;background:transparent;")
        d.setWordWrap(True)
        lay.addWidget(d)
        lay.addStretch(1)

        # Arrow hint
        ar = QHBoxLayout()
        ar.addStretch(1)
        a_lbl = QLabel()
        a_lbl.setFixedSize(20, 20)
        a_lbl.setStyleSheet("background:transparent;")
        a = _svg_pixmap(_ICON_ARROW, 16, "#64748b")
        if not a.isNull():
            a_lbl.setPixmap(a)
        ar.addWidget(a_lbl)
        lay.addLayout(ar)

    def mousePressEvent(self, ev):
        self.clicked.emit()
        super().mousePressEvent(ev)


# ═══════════════════════════════════════════════════════════════════════
#  DashboardScreen
# ═══════════════════════════════════════════════════════════════════════


class DashboardScreen(QWidget):
    org_changed = Signal()
    open_org_wizard = Signal()
    open_notifications = Signal()
    open_team = Signal()
    open_cabinet = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet("background:#0c1021;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:#0c1021;border:none;")

        self._inner = QWidget()
        self._inner.setStyleSheet("background:#0c1021;")
        self._root = QVBoxLayout(self._inner)
        self._root.setContentsMargins(0, 0, 0, 0)
        self._root.setSpacing(0)

        scroll.setWidget(self._inner)
        outer.addWidget(scroll)

        # ── Greeting ─────────────────────────────────────────────
        greeting_w = QWidget()
        greeting_w.setStyleSheet("background:transparent;")
        g_lay = QHBoxLayout(greeting_w)
        g_lay.setContentsMargins(40, 28, 40, 8)
        self.greeting_label = QLabel("")
        self.greeting_label.setStyleSheet(
            "color:#e8eaf0;font-size:24px;font-weight:700;background:transparent;"
        )
        g_lay.addWidget(self.greeting_label, 1)
        self._root.addWidget(greeting_w)

        # ══════════════════════════════════════════════════════════
        #  ADMIN — no org
        # ══════════════════════════════════════════════════════════
        self.admin_no_org = QWidget()
        self.admin_no_org.setStyleSheet("background:transparent;")
        ano = QVBoxLayout(self.admin_no_org)
        ano.setContentsMargins(40, 20, 40, 40)
        ano.setSpacing(24)

        hero = QFrame()
        hero.setStyleSheet(
            "background:#151a2e;border:none;border-radius:16px;"
        )
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(32, 32, 32, 32)
        hl.setSpacing(16)

        h_icon = QLabel()
        h_icon.setFixedSize(56, 56)
        h_icon.setAlignment(Qt.AlignCenter)
        h_icon.setStyleSheet("background:#4f8fff20;border-radius:28px;")
        hp = _svg_pixmap(_ICON_PLUS_CIRCLE, 28, "#4f8fff")
        if not hp.isNull():
            h_icon.setPixmap(hp)
        hl.addWidget(h_icon)

        h_title = QLabel("Создайте свою организацию")
        h_title.setStyleSheet(
            "color:#e8eaf0;font-size:20px;font-weight:700;background:transparent;"
        )
        hl.addWidget(h_title)

        h_text = QLabel(
            "Настройте компанию, пригласите команду и начните управлять\n"
            "проектами. Кастомизируйте всё — аватарка, описание, цвета."
        )
        h_text.setStyleSheet("color:#8891a5;font-size:14px;background:transparent;")
        h_text.setWordWrap(True)
        hl.addWidget(h_text)

        self.create_org_btn = QPushButton("Создать организацию")
        self.create_org_btn.setCursor(Qt.PointingHandCursor)
        self.create_org_btn.setFixedHeight(48)
        self.create_org_btn.setStyleSheet(
            "QPushButton{background:#4f8fff;color:#0c1021;font-size:15px;"
            "font-weight:600;border:none;border-radius:12px;}"
            "QPushButton:hover{background:#6ba3ff;}"
        )
        self.create_org_btn.clicked.connect(self.open_org_wizard.emit)
        hl.addWidget(self.create_org_btn)
        ano.addWidget(hero)
        self._root.addWidget(self.admin_no_org)

        # ══════════════════════════════════════════════════════════
        #  MEMBER — no org
        # ══════════════════════════════════════════════════════════
        self.member_no_org = QWidget()
        self.member_no_org.setStyleSheet("background:transparent;")
        mno = QVBoxLayout(self.member_no_org)
        mno.setContentsMargins(40, 20, 40, 40)
        mno.setSpacing(24)

        w_hero = QFrame()
        w_hero.setStyleSheet(
            "background:#151a2e;border:none;border-radius:16px;"
        )
        wl = QVBoxLayout(w_hero)
        wl.setContentsMargins(32, 32, 32, 32)
        wl.setSpacing(16)

        w_icon = QLabel()
        w_icon.setFixedSize(56, 56)
        w_icon.setAlignment(Qt.AlignCenter)
        w_icon.setStyleSheet("background:#4f8fff20;border-radius:28px;")
        wp = _svg_pixmap(_ICON_SMILE, 28, "#4f8fff")
        if not wp.isNull():
            w_icon.setPixmap(wp)
        wl.addWidget(w_icon)

        w_title = QLabel("Добро пожаловать!")
        w_title.setStyleSheet(
            "color:#e8eaf0;font-size:20px;font-weight:700;background:transparent;"
        )
        wl.addWidget(w_title)

        w_text = QLabel(
            "Найдите компанию по названию или введите код приглашения,\n"
            "чтобы отправить запрос на вступление."
        )
        w_text.setStyleSheet("color:#8891a5;font-size:14px;background:transparent;")
        w_text.setWordWrap(True)
        wl.addWidget(w_text)
        mno.addWidget(w_hero)

        s_card = QFrame()
        s_card.setStyleSheet(
            "background:#151a2e;border:none;border-radius:16px;"
        )
        scl = QVBoxLayout(s_card)
        scl.setContentsMargins(32, 28, 32, 28)
        scl.setSpacing(14)

        s_t = QLabel("Поиск организации")
        s_t.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:600;background:transparent;"
        )
        scl.addWidget(s_t)
        s_h = QLabel("Введите код приглашения или название компании")
        s_h.setStyleSheet("color:#8891a5;font-size:13px;background:transparent;")
        scl.addWidget(s_h)

        sr = QHBoxLayout()
        sr.setSpacing(10)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Код или название компании...")
        self.search_input.setFixedHeight(44)
        self.search_input.setStyleSheet(
            "QLineEdit{background:#1e2538;color:#e8eaf0;font-size:14px;"
            "border:1px solid #2a3150;border-radius:10px;padding:0 14px;}"
            "QLineEdit:focus{border-color:#4f8fff;}"
        )
        self.search_input.returnPressed.connect(self._search_or_join)

        self.search_btn = QPushButton("Отправить")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setFixedHeight(44)
        self.search_btn.setStyleSheet(
            "QPushButton{background:#4f8fff;color:#0c1021;font-size:14px;"
            "font-weight:600;border:none;border-radius:10px;padding:0 20px;}"
            "QPushButton:hover{background:#6ba3ff;}"
        )
        self.search_btn.clicked.connect(self._search_or_join)

        sr.addWidget(self.search_input, 1)
        sr.addWidget(self.search_btn)
        scl.addLayout(sr)

        self.search_status = QLabel("")
        self.search_status.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )
        self.search_status.setWordWrap(True)
        scl.addWidget(self.search_status)
        mno.addWidget(s_card)
        self._root.addWidget(self.member_no_org)

        # ══════════════════════════════════════════════════════════
        #  HAS ORG — hero banner + 3 cards
        # ══════════════════════════════════════════════════════════
        self.has_org_section = QWidget()
        self.has_org_section.setStyleSheet("background:transparent;")
        org_lay = QVBoxLayout(self.has_org_section)
        org_lay.setContentsMargins(0, 0, 0, 0)
        org_lay.setSpacing(0)

        # Hero banner
        self._hero_banner = QFrame()
        self._hero_banner.setMinimumHeight(200)
        self._hero_banner.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #0f172a, stop:0.5 #1e3a5f, stop:1 #151a2e);"
            "border-radius:20px;margin:0 32px;border:1px solid rgba(37,99,235,0.25);}"
        )

        banner_vlayout = QVBoxLayout(self._hero_banner)
        banner_vlayout.setContentsMargins(32, 24, 32, 28)
        banner_vlayout.setSpacing(0)

        # Content row: avatar + text + hamburger
        hb = QHBoxLayout()
        hb.setSpacing(20)

        # Org avatar (letter-based, updated in _load_org_info)
        self._org_avatar = QLabel()
        self._org_avatar.setFixedSize(80, 80)
        self._org_avatar.setAlignment(Qt.AlignCenter)
        self._org_avatar.setScaledContents(True)
        self._org_avatar.setStyleSheet(
            "background:#2a3150;border-radius:40px;border:none;"
        )
        self._org_avatar.setPixmap(_letter_avatar("?", 80, "#2a3150"))
        hb.addWidget(self._org_avatar, 0, Qt.AlignVCenter)

        # Org text column
        otc = QVBoxLayout()
        otc.setSpacing(4)

        self._org_name_label = QLabel("")
        self._org_name_label.setStyleSheet(
            "color:#ffffff;font-size:26px;font-weight:800;background:transparent;"
        )
        otc.addWidget(self._org_name_label)

        self._org_code_label = QLabel("")
        self._org_code_label.setStyleSheet(
            "color:#8891a5;font-size:12px;background:transparent;"
        )
        otc.addWidget(self._org_code_label)

        self._admin_name_label = QLabel("")
        self._admin_name_label.setStyleSheet(
            "color:#8891a5;font-size:12px;background:transparent;"
        )
        otc.addWidget(self._admin_name_label)

        otc.addStretch(1)
        hb.addLayout(otc, 1)

        # Hamburger menu button
        self._menu_btn = QPushButton()
        self._menu_btn.setFixedSize(36, 36)
        self._menu_btn.setCursor(Qt.PointingHandCursor)
        self._menu_btn.setIcon(QIcon(_svg_pixmap(_ICON_MENU, 20, "#8891a5")))
        self._menu_btn.setStyleSheet(
            "QPushButton{background:#8891a518;border:none;"
            "border-radius:10px;}"
            "QPushButton:hover{background:#8891a530;}"
        )
        self._menu_btn.clicked.connect(self._toggle_company_settings)
        hb.addWidget(self._menu_btn, 0, Qt.AlignTop)

        banner_vlayout.addLayout(hb)

        # ── Company settings dropdown (hidden by default) ──────
        self._company_settings_panel = QFrame(self)
        self._company_settings_panel.setVisible(False)
        self._company_settings_panel.setStyleSheet(
            "QFrame{background:#151a2e;border:none;"
            "border-radius:14px;}"
        )
        shadow = QGraphicsDropShadowEffect(self._company_settings_panel)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self._company_settings_panel.setGraphicsEffect(shadow)
        self._company_settings_panel.setFixedWidth(280)

        csp_lay = QVBoxLayout(self._company_settings_panel)
        csp_lay.setContentsMargins(18, 16, 18, 16)
        csp_lay.setSpacing(8)

        hdr = QLabel("Настройки компании")
        hdr.setStyleSheet(
            "color:#e8eaf0;font-size:15px;font-weight:700;background:transparent;"
        )
        csp_lay.addWidget(hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#1e2538;")
        csp_lay.addWidget(sep)

        # Theme buttons
        themes = [
            ("Тёмная тема (по умолчанию)", "#151a2e", "dark"),
            ("Синяя тема", "#0d1b2a", "blue"),
            ("Глубокий фиолет", "#1a0a2e", "purple"),
        ]
        self._theme_buttons: list[QPushButton] = []
        for label, preview_color, theme_id in themes:
            row = QHBoxLayout()
            row.setSpacing(10)
            dot = QLabel()
            dot.setFixedSize(18, 18)
            dot.setStyleSheet(
                f"background:{preview_color};border-radius:9px;"
                f"border:2px solid #2a3150;"
            )
            row.addWidget(dot)
            btn = QPushButton(label)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                "QPushButton{background:transparent;color:#8891a5;font-size:13px;"
                "text-align:left;border:none;padding:8px 4px;}"
                "QPushButton:hover{color:#e8eaf0;}"
            )
            btn.setProperty("theme_id", theme_id)
            btn.clicked.connect(self._on_theme_selected)
            row.addWidget(btn, 1)
            csp_lay.addLayout(row)
            self._theme_buttons.append(btn)

        self._admin_only_label = QLabel("Только для администратора")
        self._admin_only_label.setStyleSheet(
            "color:#4a5068;font-size:11px;background:transparent;padding-top:6px;"
        )
        self._admin_only_label.setAlignment(Qt.AlignCenter)
        csp_lay.addWidget(self._admin_only_label)

        org_lay.addWidget(self._hero_banner)
        org_lay.addSpacing(24)

        # ── Три блока по макету: О компании, Штаб, Личный кабинет ───
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.setContentsMargins(32, 0, 32, 0)

        card_about = _NavCard(
            _ICON_BUILDING, "#3b82f6",
            "О компании",
            "Информация об организации, настройки и код приглашения.",
        )
        card_about.clicked.connect(self._on_about_company)
        cards_row.addWidget(card_about, 1)

        card_team = _NavCard(
            _ICON_USERS, "#60a5fa",
            "Штаб в котором вы работаете",
            "Отделы, тимлиды и коллеги. Перейти к списку штабов.",
        )
        card_team.clicked.connect(self.open_team.emit)
        cards_row.addWidget(card_team, 1)

        card_cabinet = _NavCard(
            _ICON_CLIPBOARD, "#2563eb",
            "Ваш личный кабинет",
            "Задачи на сегодня, отчёты и трансляция экрана.",
        )
        card_cabinet.clicked.connect(self.open_cabinet.emit)
        cards_row.addWidget(card_cabinet, 1)

        org_lay.addLayout(cards_row)
        org_lay.addSpacing(20)

        # ── KPI Summary row ───────────────────────────────────────
        kpi_row = QWidget()
        kpi_row.setStyleSheet("background:transparent;")
        kr = QHBoxLayout(kpi_row)
        kr.setContentsMargins(32, 0, 32, 0)
        kr.setSpacing(12)

        # Members count card
        mc = QFrame()
        mc.setStyleSheet(
            "QFrame{background:#151a2e;border:1px solid #1e2538;border-radius:14px;}"
        )
        mcl = QVBoxLayout(mc)
        mcl.setContentsMargins(18, 14, 18, 14)
        mcl.setSpacing(6)
        mc_t = QLabel("Сотрудники")
        mc_t.setStyleSheet(
            "color:#8891a5;font-size:12px;font-weight:600;background:transparent;"
        )
        mcl.addWidget(mc_t)
        self._org_members_label = QLabel("--")
        self._org_members_label.setStyleSheet(
            "color:#4f8fff;font-size:32px;font-weight:800;background:transparent;"
        )
        mcl.addWidget(self._org_members_label)
        kr.addWidget(mc, 1)

        org_lay.addWidget(kpi_row)
        org_lay.addSpacing(16)
        self._root.addWidget(self.has_org_section)
        self._root.addStretch(1)

    # ══════════════════════════════════════════════════════════════
    #  Public
    # ══════════════════════════════════════════════════════════════

    def refresh_dashboard(self) -> None:
        self._update_greeting()
        self._apply_visibility()
        self._load_org_info()

    refresh_tasks = refresh_dashboard

    # ══════════════════════════════════════════════════════════════
    #  Private
    # ══════════════════════════════════════════════════════════════

    def _update_greeting(self) -> None:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            g = "Доброе утро"
        elif 12 <= hour < 18:
            g = "Добрый день"
        elif 18 <= hour < 23:
            g = "Добрый вечер"
        else:
            g = "Доброй ночи"
        name = session_store.full_name or ""
        pat = session_store.patronymic or ""
        disp = " ".join(p for p in (name, pat) if p)
        self.greeting_label.setText(f"{g}, {disp}" if disp else g)

    def _apply_visibility(self) -> None:
        is_admin = session_store.role in ("admin", "manager")
        has_org = bool(session_store.org_id)
        self.admin_no_org.setVisible(is_admin and not has_org)
        self.member_no_org.setVisible(not is_admin and not has_org)
        self.has_org_section.setVisible(has_org)

    def _load_org_info(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            return
        try:
            org = api_client.get_org(org_id)
            name = org.get("name", "Организация")
            code = org.get("org_code", "")
            self._org_name_label.setText(name)
            self._org_code_label.setText(
                f"Код приглашения: {code}" if code else ""
            )
            # Set letter avatar from org name
            letter = name[0] if name else "?"
            colors = ["#4f8fff", "#3b82f6", "#a78bfa", "#f59e0b", "#ef4444",
                      "#1f6feb", "#2563eb", "#8957e5", "#d29922", "#da3633"]
            ci = sum(ord(c) for c in name) % len(colors)
            self._org_avatar.setPixmap(_letter_avatar(letter, 80, colors[ci]))

            if session_store.role in ("admin", "manager"):
                self._admin_name_label.setText(session_store.full_name or "")
            else:
                self._admin_name_label.setText("")

            # Show/hide settings depending on role
            is_admin = session_store.role in ("admin", "manager")
            self._menu_btn.setVisible(is_admin)

            # Load KPI summary
            try:
                members = api_client.list_org_members(org_id)
                self._org_members_label.setText(str(len(members)))
            except Exception:  # noqa: BLE001
                self._org_members_label.setText("--")

        except (ApiError, Exception):  # noqa: BLE001
            pass

    # ── Company settings panel ────────────────────────────────────

    def _toggle_company_settings(self) -> None:
        if session_store.role != "admin":
            return
        panel = self._company_settings_panel
        if panel.isVisible():
            panel.setVisible(False)
            return
        # Position below the hamburger button, right-aligned
        btn_pos = self._menu_btn.mapTo(self, QPoint(0, 0))
        px = btn_pos.x() + self._menu_btn.width() - panel.width()
        py = btn_pos.y() + self._menu_btn.height() + 8
        panel.move(px, py)
        panel.raise_()
        panel.setVisible(True)

    def _on_about_company(self) -> None:
        """О компании: для админа — открыть настройки, иначе ничего."""
        if session_store.role in ("admin", "manager"):
            self._toggle_company_settings()

    def _on_theme_selected(self) -> None:
        btn = self.sender()
        if not btn:
            return
        theme_id = btn.property("theme_id")
        themes_map = {
            "dark": ("stop:0 #1a1a2e, stop:0.5 #16213e, stop:1 #0f3460", "#151a2e"),
            "blue": ("stop:0 #0d1b2a, stop:0.5 #1b2838, stop:1 #0a1628", "#0d1b2a"),
            "purple": ("stop:0 #1a0a2e, stop:0.5 #2d1b4e, stop:1 #120826", "#1a0a2e"),
        }
        grad, _bg = themes_map.get(theme_id, themes_map["dark"])
        self._hero_banner.setStyleSheet(
            f"background:qlineargradient(x1:0,y1:0,x2:1,y2:1,{grad});"
            "border-radius:20px;margin:0 32px;"
        )
        self._company_settings_panel.setVisible(False)

    def _search_or_join(self) -> None:
        query = self.search_input.text().strip()
        if not query:
            self.search_status.setText("Введите код или название компании")
            return
        self.search_btn.setEnabled(False)
        self.search_status.setText("Отправляем запрос...")
        try:
            join_code = query
            # If query is not invite-code like, try organization name lookup first.
            if not (4 <= len(query) <= 16 and query.replace("-", "").isalnum()):
                matches = api_client.search_orgs(query)
                if not matches:
                    self.search_status.setText("Компания не найдена")
                    return
                join_code = matches[0].get("join_code", query)

            resp = api_client.join_org(join_code)
            session_store.set_org_id(resp.get("org_id"))
            self.org_changed.emit()
            st = resp.get("status", "pending")
            if st == "approved":
                self.search_status.setText("Вы вступили в организацию!")
                self.refresh_dashboard()
            else:
                self.search_status.setText(
                    f"Запрос отправлен (статус: {st}). Ожидайте подтверждения."
                )
        except ApiError as exc:
            self.search_status.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.search_status.setText(f"Ошибка: {exc}")
        finally:
            self.search_btn.setEnabled(True)

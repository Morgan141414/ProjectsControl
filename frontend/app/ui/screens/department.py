"""Ultra Intelligence KPI — Department dashboard.

Three-tab layout modeled after the Ultra Intelligence KPI reference:
  Tab 0  Обзор   — employee pills, KPI card, KPI dynamics
  Tab 1  Команда — best performer, ranked member list, team KPI summary
  Tab 2  Детали  — real-time activity feed, activity breakdown, AI analytics
"""

from datetime import date

from PySide6.QtCore import QByteArray, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
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

# ── Color tokens: тёмная + синий + бело-серый + ярко-синий ─────────
_BG = "#0c1021"
_CARD = "#151a2e"
_CARD_ELEV = "#1e2538"
_BORDER = "#1e2538"
_BORDER2 = "#2a3150"
_ACCENT = "#2563eb"
_ACCENT_BRIGHT = "#3b82f6"
_ORANGE = "#f59e0b"
_GREEN = "#3b82f6"
_PINK = "#ec4899"
_RED = "#ef4444"
_PURPLE = "#a78bfa"
_TXT1 = "#e8eaf0"
_TXT2 = "#94a3b8"
_TXT3 = "#64748b"

# ── SVG icons ─────────────────────────────────────────────────────
_ICON_ARROW_LEFT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="19" y1="12" x2="5" y2="12"/>'
    '<polyline points="12 19 5 12 12 5"/></svg>'
)
_ICON_ACTIVITY = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
)
_ICON_USERS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>'
    '<circle cx="9" cy="7" r="4"/>'
    '<path d="M23 21v-2a4 4 0 0 0-3-3.87"/>'
    '<path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>'
)
_ICON_SETTINGS = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83'
    'l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0'
    'v-.09a1.65 1.65 0 0 0-1.08-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0'
    ' 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3'
    'a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1.08 1.65 1.65 0 0 0-.33-1.82'
    'l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65'
    ' 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0'
    ' 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9'
    'a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>'
)
_ICON_TROPHY = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>'
    '<path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>'
    '<path d="M4 22h16"/><path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20 7 22"/>'
    '<path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20 17 22"/>'
    '<path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/></svg>'
)
_ICON_ZAPPER = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
)
_ICON_CLOCK = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<polyline points="12 6 12 12 16 14"/></svg>'
)
_ICON_BAR_CHART = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="12" y1="20" x2="12" y2="10"/>'
    '<line x1="18" y1="20" x2="18" y2="4"/>'
    '<line x1="6" y1="20" x2="6" y2="16"/></svg>'
)
_ICON_BULB = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M9 18h6"/><path d="M10 22h4"/>'
    '<path d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8'
    'c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/></svg>'
)


def _svg_icon(svg_t: str, size: int = 18, color: str = _TXT2) -> QIcon:
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


def _svg_pixmap(svg_t: str, size: int = 18, color: str = _TXT2) -> QPixmap:
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


def _letter_avatar(letter: str, size: int, bg: str = _ACCENT) -> QPixmap:
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    p.setClipPath(path)
    p.fillRect(0, 0, size, size, QColor(bg))
    font = QFont("Inter", int(size * 0.38))
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor("#ffffff"))
    from PySide6.QtCore import QRectF
    p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, letter.upper())
    p.end()
    return pix


# ═══════════════════════════════════════════════════════════════════════
#  DepartmentScreen — Ultra Intelligence KPI style
# ═══════════════════════════════════════════════════════════════════════


class DepartmentScreen(QWidget):
    """Department detail — 3-tab Ultra KPI dashboard."""

    go_back = Signal()
    open_cabinet = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._team_id: str | None = None
        self._team_data: dict | None = None
        self._live_session_id: str | None = None
        self._live_org_id: str | None = None
        self._live_preview_label: QLabel | None = None
        self._sessions_box: QVBoxLayout | None = None
        self._live_timer = QTimer(self)
        self._live_timer.setInterval(1000)  # 1 FPS live polling
        self._live_timer.timeout.connect(self._poll_live_preview)
        self._sessions_timer = QTimer(self)
        self._sessions_timer.setInterval(5000)  # refresh active sessions every 5s
        self._sessions_timer.timeout.connect(self._refresh_sessions)
        self.setStyleSheet(f"background:{_BG};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header bar ────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(f"background:{_BG};border-bottom:1px solid {_BORDER};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 12, 20, 12)
        hl.setSpacing(14)

        back = QPushButton()
        back.setCursor(Qt.PointingHandCursor)
        back.setIcon(_svg_icon(_ICON_ARROW_LEFT, 20, _TXT1))
        back.setFixedSize(36, 36)
        back.setStyleSheet(
            f"QPushButton{{background:transparent;border:none;}}"
            f"QPushButton:hover{{background:{_CARD};border-radius:8px;}}"
        )
        back.clicked.connect(self.go_back.emit)
        hl.addWidget(back)

        # Logo circle
        self._logo = QLabel()
        self._logo.setFixedSize(36, 36)
        self._logo.setAlignment(Qt.AlignCenter)
        self._logo.setStyleSheet(
            f"background:{_ACCENT}22;border-radius:18px;"
        )
        lp = _svg_pixmap(_ICON_ACTIVITY, 18, _ACCENT)
        if not lp.isNull():
            self._logo.setPixmap(lp)
        hl.addWidget(self._logo)

        # Title column
        tc = QVBoxLayout()
        tc.setSpacing(0)
        self._title = QLabel("Отдел")
        self._title.setStyleSheet(
            f"color:{_TXT1};font-size:16px;font-weight:700;background:transparent;"
        )
        self._subtitle = QLabel("Система аналитики эффективности")
        self._subtitle.setStyleSheet(
            f"color:{_TXT2};font-size:11px;background:transparent;"
        )
        tc.addWidget(self._title)
        tc.addWidget(self._subtitle)
        hl.addLayout(tc, 1)

        # Meta info
        self._meta = QLabel("")
        self._meta.setStyleSheet(
            f"color:{_TXT3};font-size:11px;background:transparent;"
        )
        hl.addWidget(self._meta)

        # Monitoring status dot + label
        self._mon_dot = QLabel()
        self._mon_dot.setFixedSize(8, 8)
        self._mon_dot.setStyleSheet(
            f"background:{_RED};border-radius:4px;"
        )
        hl.addWidget(self._mon_dot)
        self._mon_label = QLabel("Мониторинг")
        self._mon_label.setStyleSheet(
            f"color:{_TXT2};font-size:12px;background:transparent;"
        )
        hl.addWidget(self._mon_label)

        outer.addWidget(header)

        # ── Tab bar ───────────────────────────────────────────────
        tab_bar = QFrame()
        tab_bar.setStyleSheet(f"background:{_BG};")
        tbl = QHBoxLayout(tab_bar)
        tbl.setContentsMargins(24, 8, 24, 0)
        tbl.setSpacing(4)

        self._tabs: list[QPushButton] = []
        tab_defs = [
            (_ICON_ACTIVITY, "Обзор"),
            (_ICON_USERS, "Команда"),
            (_ICON_BAR_CHART, "Детали"),
        ]
        for icon_svg, label in tab_defs:
            btn = QPushButton(f"  {label}")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setIcon(_svg_icon(icon_svg, 14, _TXT2))
            btn.setCheckable(True)
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;color:{_TXT3};font-size:13px;"
                f"font-weight:600;border:none;border-bottom:2px solid transparent;"
                f"padding:10px 18px;border-radius:0;}}"
                f"QPushButton:checked{{color:{_TXT1};border-bottom:2px solid {_ACCENT};}}"
                f"QPushButton:hover{{color:{_TXT2};}}"
            )
            btn.clicked.connect(lambda checked=False, b=btn: self._on_tab(b))
            tbl.addWidget(btn)
            self._tabs.append(btn)
        tbl.addStretch(1)
        outer.addWidget(tab_bar)

        # ── Stacked content ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"background:{_BG};border:none;")

        self._content = QWidget()
        self._content.setStyleSheet(f"background:{_BG};")
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(24, 20, 24, 24)
        self._content_lay.setSpacing(16)

        scroll.setWidget(self._content)
        outer.addWidget(scroll, 1)

        # ── Footer ────────────────────────────────────────────────
        footer = QLabel(
            f"ProjectsControl KPI Engine v2.0  ·  "
            f"Алгоритм: Multi-Factor Analysis  ·  "
            f"Модель: Predictive v3.1"
        )
        footer.setStyleSheet(
            f"color:{_TXT3};font-size:11px;background:{_BG};"
            f"padding:8px 24px;border-top:1px solid {_BORDER};"
        )
        footer.setAlignment(Qt.AlignCenter)
        outer.addWidget(footer)

        self._current_tab = 0
        if self._tabs:
            self._tabs[0].setChecked(True)

    # ── Tab switching ─────────────────────────────────────────────

    def _on_tab(self, btn: QPushButton) -> None:
        for i, b in enumerate(self._tabs):
            b.setChecked(b is btn)
            if b is btn:
                self._current_tab = i
        self._rebuild_content()

    # ── Public API ────────────────────────────────────────────────

    def set_team(self, team_id: str) -> None:
        self._team_id = team_id
        self.refresh()

    def refresh(self) -> None:
        if not self._team_id:
            return
        org_id = session_store.org_id
        if not org_id:
            return

        try:
            teams = api_client.list_teams(org_id)
        except Exception:
            teams = []

        self._team_data = None
        for t in teams:
            if t.get("id") == self._team_id:
                self._team_data = t
                break

        if self._team_data:
            name = self._team_data.get("name", "Отдел")
            self._title.setText(name)
            members = self._team_data.get("members", [])
            self._meta.setText(
                f"Участников: {len(members)}  ·  "
                f"Обновлено: {date.today().isoformat()}"
            )

        self._rebuild_content()

    # ── Content builders ──────────────────────────────────────────

    def _rebuild_content(self) -> None:
        self._clear_layout(self._content_lay)
        if self._current_tab == 0:
            self._build_overview()
        elif self._current_tab == 1:
            self._build_team()
        elif self._current_tab == 2:
            self._build_details()

    def _clear_layout(self, layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
            elif item.layout():
                self._clear_layout(item.layout())

    # ══════════════════════════════════════════════════════════════
    #  TAB 0 — Обзор
    # ══════════════════════════════════════════════════════════════

    def _build_overview(self) -> None:
        members = (self._team_data or {}).get("members", [])
        org_id = session_store.org_id

        # ── По макету: тимлид + коллеги в одном ряду ─────────────────
        row_lead_cols = QHBoxLayout()
        row_lead_cols.setSpacing(16)

        # Карточка тимлида (профиль с фото и информацией)
        lead_card = QFrame()
        lead_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        lead_card.setMinimumHeight(160)
        lcl = QVBoxLayout(lead_card)
        lcl.setContentsMargins(20, 16, 20, 16)
        lcl.setSpacing(10)
        lead_title = QLabel("Тимлид")
        lead_title.setStyleSheet(
            f"color:{_TXT3};font-size:11px;font-weight:600;background:transparent;"
        )
        lcl.addWidget(lead_title)
        lead_found = None
        for m in members:
            if m.get("role") == "lead":
                lead_found = m
                break
        if lead_found:
            lead_name = lead_found.get("full_name", "—")
            lead_initials = "".join(w[0] for w in lead_name.split()[:2]).upper() if lead_name != "—" else "?"
            av = QLabel()
            av.setFixedSize(56, 56)
            av.setAlignment(Qt.AlignCenter)
            av.setPixmap(_letter_avatar(lead_initials, 56, _ACCENT))
            lcl.addWidget(av, 0, Qt.AlignLeft)
            ln = QLabel(lead_name)
            ln.setStyleSheet(
                f"color:{_TXT1};font-size:15px;font-weight:700;background:transparent;"
            )
            lcl.addWidget(ln)
            lr = QLabel("Руководитель отдела")
            lr.setStyleSheet(
                f"color:{_TXT2};font-size:12px;background:transparent;"
            )
            lcl.addWidget(lr)
        else:
            pl = QLabel("Тимлид не назначен")
            pl.setStyleSheet(f"color:{_TXT3};font-size:13px;background:transparent;")
            lcl.addWidget(pl)
        row_lead_cols.addWidget(lead_card, 1)

        # Карточка «Ваши коллеги»
        cols_card = QFrame()
        cols_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        cols_card.setMinimumHeight(160)
        ccl = QVBoxLayout(cols_card)
        ccl.setContentsMargins(20, 16, 20, 16)
        ccl.setSpacing(8)
        cols_title = QLabel("Ваши коллеги")
        cols_title.setStyleSheet(
            f"color:{_TXT3};font-size:11px;font-weight:600;background:transparent;"
        )
        ccl.addWidget(cols_title)
        colleagues = [m for m in members if m.get("role") != "lead"]
        for m in colleagues[:6]:
            name = m.get("full_name", "—")
            rl = QLabel(f"• {name}")
            rl.setStyleSheet(
                f"color:{_TXT2};font-size:13px;background:transparent;"
            )
            ccl.addWidget(rl)
        if not colleagues:
            empty_c = QLabel("Пока никого нет")
            empty_c.setStyleSheet(f"color:{_TXT3};font-size:12px;background:transparent;")
            ccl.addWidget(empty_c)
        ccl.addStretch(1)
        row_lead_cols.addWidget(cols_card, 1)

        r1w = QWidget()
        r1w.setStyleSheet("background:transparent;")
        r1w.setLayout(row_lead_cols)
        self._content_lay.addWidget(r1w)

        # ── Проекты над которыми работает штаб ───────────────────────
        proj_card = QFrame()
        proj_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        pcl = QVBoxLayout(proj_card)
        pcl.setContentsMargins(20, 16, 20, 16)
        pcl.setSpacing(8)
        proj_title = QLabel("Проекты над которыми работает данный штаб")
        proj_title.setStyleSheet(
            f"color:{_TXT1};font-size:14px;font-weight:700;background:transparent;"
        )
        pcl.addWidget(proj_title)
        project_name = "—"
        if org_id and self._team_data:
            pid = self._team_data.get("project_id")
            if pid:
                try:
                    projects = api_client.list_projects(org_id)
                    for p in projects:
                        if p.get("id") == pid:
                            project_name = p.get("name", "—")
                            break
                except Exception:
                    pass
        proj_val = QLabel(project_name)
        proj_val.setStyleSheet(
            f"color:{_TXT2};font-size:13px;background:transparent;"
        )
        pcl.addWidget(proj_val)
        self._content_lay.addWidget(proj_card)

        # ── Задачи на сегодня (пишет тимлид) ────────────────────────
        tasks_card = QFrame()
        tasks_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        tcl = QVBoxLayout(tasks_card)
        tcl.setContentsMargins(20, 16, 20, 16)
        tcl.setSpacing(8)
        tasks_title = QLabel("Задачи на сегодня")
        tasks_title.setStyleSheet(
            f"color:{_TXT1};font-size:14px;font-weight:700;background:transparent;"
        )
        tcl.addWidget(tasks_title)
        task_items: list[str] = []
        if org_id:
            try:
                project_id = (self._team_data or {}).get("project_id")
                task_list = api_client.list_today_tasks(org_id, project_id)
                for t in (task_list or [])[:10]:
                    title = t.get("title") or t.get("content", "—")
                    task_items.append(title)
            except Exception:
                pass
        for tit in task_items or ["Задач пока нет. Тимлид назначит задачи."]:
            tl = QLabel(f"• {tit}")
            tl.setStyleSheet(
                f"color:{_TXT2};font-size:13px;background:transparent;"
            )
            tl.setWordWrap(True)
            tcl.addWidget(tl)
        self._content_lay.addWidget(tasks_card)

        # Нижний ряд: совместные проекты + ваш кабинет (кнопка)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(16)
        joint_card = QFrame()
        joint_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:14px;}}"
        )
        jcl = QVBoxLayout(joint_card)
        jcl.setContentsMargins(16, 12, 16, 12)
        jtit = QLabel("Совместные проекты")
        jtit.setStyleSheet(f"color:{_TXT1};font-size:13px;font-weight:600;background:transparent;")
        jcl.addWidget(jtit)
        jl = QLabel("См. вкладку «Команда» и «Детали»")
        jl.setStyleSheet(f"color:{_TXT2};font-size:12px;background:transparent;")
        jcl.addWidget(jl)
        bottom_row.addWidget(joint_card, 1)
        cabinet_btn = QPushButton("Ваш кабинет")
        cabinet_btn.setCursor(Qt.PointingHandCursor)
        cabinet_btn.setStyleSheet(
            f"QPushButton{{background:{_ACCENT};color:#0c1021;font-size:13px;"
            f"font-weight:600;border:none;border-radius:12px;padding:12px 20px;}}"
            f"QPushButton:hover{{background:{_ACCENT_BRIGHT};}}"
        )
        cabinet_btn.clicked.connect(self.open_cabinet.emit)
        bottom_row.addWidget(cabinet_btn)
        bw = QWidget()
        bw.setStyleSheet("background:transparent;")
        bw.setLayout(bottom_row)
        self._content_lay.addWidget(bw)

        # Employee pill bar
        pills = QHBoxLayout()
        pills.setSpacing(8)
        pills_label = QLabel("Сотрудники:")
        pills_label.setStyleSheet(f"color:{_TXT2};font-size:13px;background:transparent;")
        pills.addWidget(pills_label)

        selected_uid = members[0].get("user_id", "") if members else ""
        selected_name = members[0].get("full_name", "—") if members else "—"
        selected_kpd = 0

        # Load KPD scores
        kpd_map: dict[str, int] = {}
        if org_id:
            for m in members:
                uid = m.get("user_id", "")
                try:
                    scores = api_client.get_ai_scorecards(
                        org_id, period="daily",
                        as_of=date.today().isoformat(),
                        user_id=uid, mode=None, role_profile=None, trend_limit=None,
                    )
                    if scores and isinstance(scores, list) and scores:
                        kpd_map[uid] = int(scores[0].get("score", 0))
                except Exception:
                    pass

        for m in members:
            uid = m.get("user_id", "")
            name = (m.get("full_name") or "—").split()[0]
            is_selected = uid == selected_uid
            pill = QPushButton(f"  {name}")
            pill.setCursor(Qt.PointingHandCursor)
            pill.setFixedHeight(32)
            if is_selected:
                pill.setStyleSheet(
                    f"QPushButton{{background:{_ACCENT};color:{_BG};font-size:12px;"
                    f"font-weight:600;border:none;border-radius:16px;padding:0 14px;}}"
                )
                selected_kpd = kpd_map.get(uid, 0)
            else:
                pill.setStyleSheet(
                    f"QPushButton{{background:{_CARD};color:{_TXT2};font-size:12px;"
                    f"font-weight:500;border:1px solid {_BORDER};border-radius:16px;"
                    f"padding:0 14px;}}"
                    f"QPushButton:hover{{background:{_CARD_ELEV};}}"
                )
            pills.addWidget(pill)
        pills.addStretch(1)
        pw = QWidget()
        pw.setStyleSheet("background:transparent;")
        pw.setLayout(pills)
        self._content_lay.addWidget(pw)

        # ── Two-column: KPI card + Dynamics ───────────────────────
        row = QHBoxLayout()
        row.setSpacing(16)

        # LEFT: Текущий КПД
        kpi_card = QFrame()
        kpi_card.setStyleSheet(
            f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            f"stop:0 #2a1a00,stop:1 {_CARD});"
            f"border:1px solid {_BORDER};border-radius:16px;}}"
        )
        kpi_card.setMinimumHeight(220)
        kcl = QVBoxLayout(kpi_card)
        kcl.setContentsMargins(24, 20, 24, 20)
        kcl.setSpacing(8)

        kh = QHBoxLayout()
        kh.setSpacing(8)
        k_icon = QLabel()
        k_icon.setFixedSize(20, 20)
        kpx = _svg_pixmap(_ICON_ACTIVITY, 16, _ORANGE)
        if not kpx.isNull():
            k_icon.setPixmap(kpx)
        kh.addWidget(k_icon)
        k_title = QLabel("Текущий КПД")
        k_title.setStyleSheet(
            f"color:{_TXT1};font-size:14px;font-weight:700;background:transparent;"
        )
        kh.addWidget(k_title, 1)
        k_delta = QLabel(f"~ {selected_kpd}%")
        k_delta.setStyleSheet(
            f"color:{_TXT2};font-size:12px;background:transparent;"
        )
        kh.addWidget(k_delta)
        kcl.addLayout(kh)

        # Big number
        big = QLabel(f"{selected_kpd}")
        big.setStyleSheet(
            f"color:{_ORANGE};font-size:72px;font-weight:800;background:transparent;"
            f"letter-spacing:-2px;"
        )
        pct = QLabel("%")
        pct.setStyleSheet(
            f"color:{_TXT3};font-size:28px;font-weight:600;background:transparent;"
        )
        nr = QHBoxLayout()
        nr.setSpacing(4)
        nr.addWidget(big)
        nr.addWidget(pct, 0, Qt.AlignBottom)
        nr.addStretch(1)
        kcl.addLayout(nr)

        # Name
        nm = QLabel(selected_name)
        nm.setStyleSheet(
            f"color:{_TXT1};font-size:14px;font-weight:600;background:transparent;"
        )
        kcl.addWidget(nm)

        # Progress bar
        pb = QProgressBar()
        pb.setRange(0, 100)
        pb.setValue(selected_kpd)
        pb.setFixedHeight(8)
        pb.setTextVisible(False)
        pb.setStyleSheet(
            f"QProgressBar{{background:{_CARD_ELEV};border-radius:4px;border:none;}}"
            f"QProgressBar::chunk{{background:{_ORANGE};border-radius:4px;}}"
        )
        kcl.addWidget(pb)

        # Scale
        scale = QHBoxLayout()
        for v in ("0%", "50%", "100%"):
            l = QLabel(v)
            l.setStyleSheet(f"color:{_TXT3};font-size:10px;background:transparent;")
            scale.addWidget(l)
            if v != "100%":
                scale.addStretch(1)
        kcl.addLayout(scale)

        # Goal
        goal = QLabel("Цель: 85%")
        goal.setStyleSheet(f"color:{_TXT3};font-size:11px;background:transparent;")
        kcl.addWidget(goal)
        row.addWidget(kpi_card, 2)

        # RIGHT: Динамика КПД
        dyn = QFrame()
        dyn.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        dyn.setMinimumHeight(220)
        dl = QVBoxLayout(dyn)
        dl.setContentsMargins(24, 20, 24, 20)
        dl.setSpacing(12)

        dh = QHBoxLayout()
        d_icon = QLabel()
        d_icon.setFixedSize(18, 18)
        dpx = _svg_pixmap(_ICON_BAR_CHART, 14, _ACCENT)
        if not dpx.isNull():
            d_icon.setPixmap(dpx)
        dh.addWidget(d_icon)
        d_title = QLabel("Динамика КПД")
        d_title.setStyleSheet(
            f"color:{_TXT1};font-size:14px;font-weight:700;background:transparent;"
        )
        dh.addWidget(d_title, 1)
        dl.addLayout(dh)

        # Placeholder for chart area
        chart_area = QLabel("График активности будет отображаться здесь")
        chart_area.setMinimumHeight(100)
        chart_area.setAlignment(Qt.AlignCenter)
        chart_area.setStyleSheet(
            f"color:{_TXT3};font-size:12px;background:{_BG};"
            f"border:1px dashed {_BORDER};border-radius:8px;"
        )
        dl.addWidget(chart_area, 1)

        # 4 metrics
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(0)
        for label, value in [
            ("Направление", "Стабильно"),
            ("Изменение", f"{selected_kpd}%"),
            ("Волатильность", "0%"),
            ("Паттерн", "Стабильно"),
        ]:
            mc = QVBoxLayout()
            mc.setSpacing(2)
            mc.setAlignment(Qt.AlignCenter)
            mv = QLabel(value)
            mv.setAlignment(Qt.AlignCenter)
            mv.setStyleSheet(
                f"color:{_TXT1};font-size:14px;font-weight:700;background:transparent;"
            )
            ml = QLabel(label)
            ml.setAlignment(Qt.AlignCenter)
            ml.setStyleSheet(
                f"color:{_TXT3};font-size:11px;background:transparent;"
            )
            mc.addWidget(mv)
            mc.addWidget(ml)
            metrics_row.addLayout(mc, 1)
        dl.addLayout(metrics_row)
        row.addWidget(dyn, 3)

        rw = QWidget()
        rw.setStyleSheet("background:transparent;")
        rw.setLayout(row)
        self._content_lay.addWidget(rw)
        self._content_lay.addStretch(1)

    # ══════════════════════════════════════════════════════════════
    #  TAB 1 — Команда
    # ══════════════════════════════════════════════════════════════

    def _build_team(self) -> None:
        members = (self._team_data or {}).get("members", [])
        org_id = session_store.org_id

        # Load KPD
        kpd_map: dict[str, int] = {}
        if org_id:
            for m in members:
                uid = m.get("user_id", "")
                try:
                    scores = api_client.get_ai_scorecards(
                        org_id, period="daily",
                        as_of=date.today().isoformat(),
                        user_id=uid, mode=None, role_profile=None, trend_limit=None,
                    )
                    if scores and isinstance(scores, list) and scores:
                        kpd_map[uid] = int(scores[0].get("score", 0))
                except Exception:
                    pass

        # Sort by KPD desc
        sorted_members = sorted(
            members,
            key=lambda m: kpd_map.get(m.get("user_id", ""), 0),
            reverse=True,
        )

        row = QHBoxLayout()
        row.setSpacing(16)

        # LEFT: Team list
        left_card = QFrame()
        left_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        lcl = QVBoxLayout(left_card)
        lcl.setContentsMargins(24, 20, 24, 20)
        lcl.setSpacing(12)

        # Header
        th = QHBoxLayout()
        t_icon = QLabel()
        t_icon.setFixedSize(18, 18)
        tpx = _svg_pixmap(_ICON_USERS, 14, _TXT2)
        if not tpx.isNull():
            t_icon.setPixmap(tpx)
        th.addWidget(t_icon)
        t_title = QLabel(f"Команда  {len(members)}")
        t_title.setStyleSheet(
            f"color:{_TXT1};font-size:16px;font-weight:700;background:transparent;"
        )
        th.addWidget(t_title, 1)
        avg_kpd = sum(kpd_map.values()) // max(len(kpd_map), 1) if kpd_map else 0
        t_kpi = QLabel(f"Общий КПД: {avg_kpd}%")
        t_kpi.setStyleSheet(
            f"color:{_ORANGE};font-size:13px;font-weight:600;background:transparent;"
        )
        th.addWidget(t_kpi)
        lcl.addLayout(th)

        # Best performer card
        if sorted_members:
            best = sorted_members[0]
            best_name = best.get("full_name", "—")
            best_kpd = kpd_map.get(best.get("user_id", ""), 0)
            bp = QFrame()
            bp.setStyleSheet(
                f"QFrame{{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                f"stop:0 #2a1a00,stop:1 {_CARD_ELEV});"
                f"border:1px solid #3d2800;border-radius:12px;}}"
            )
            bpl = QHBoxLayout(bp)
            bpl.setContentsMargins(16, 12, 16, 12)
            bpl.setSpacing(12)
            trophy = QLabel()
            trophy.setFixedSize(24, 24)
            tp = _svg_pixmap(_ICON_TROPHY, 18, _ORANGE)
            if not tp.isNull():
                trophy.setPixmap(tp)
            bpl.addWidget(trophy)
            bi = QVBoxLayout()
            bi.setSpacing(0)
            bl1 = QLabel("Лучший результат")
            bl1.setStyleSheet(
                f"color:{_ORANGE};font-size:12px;font-weight:600;background:transparent;"
            )
            bl2 = QLabel(best_name)
            bl2.setStyleSheet(
                f"color:{_TXT1};font-size:14px;font-weight:600;background:transparent;"
            )
            bi.addWidget(bl1)
            bi.addWidget(bl2)
            bpl.addLayout(bi, 1)
            bv = QLabel(f"{best_kpd}%")
            bv.setStyleSheet(
                f"color:{_ORANGE};font-size:22px;font-weight:800;background:transparent;"
            )
            bpl.addWidget(bv)
            bvl = QLabel("КПД")
            bvl.setStyleSheet(
                f"color:{_TXT3};font-size:11px;background:transparent;"
            )
            bpl.addWidget(bvl)
            lcl.addWidget(bp)

        # Member list
        colors = [_ACCENT, _PINK, _PURPLE, _GREEN, _ORANGE, _RED]
        for idx, m in enumerate(sorted_members):
            uid = m.get("user_id", "")
            name = m.get("full_name", "—")
            role = m.get("role", "member")
            kpd = kpd_map.get(uid, 0)
            initials = "".join(w[0] for w in name.split()[:2]).upper() if name != "—" else "?"

            mr = QFrame()
            mr.setStyleSheet(
                f"QFrame{{background:transparent;border:none;}}"
            )
            ml = QHBoxLayout(mr)
            ml.setContentsMargins(4, 6, 4, 6)
            ml.setSpacing(12)

            # Rank number
            rn = QLabel(str(idx + 1))
            rn.setFixedWidth(20)
            rn.setAlignment(Qt.AlignCenter)
            rn.setStyleSheet(f"color:{_TXT3};font-size:13px;background:transparent;")
            ml.addWidget(rn)

            # Avatar circle
            av = QLabel()
            av.setFixedSize(36, 36)
            av.setAlignment(Qt.AlignCenter)
            c = colors[idx % len(colors)]
            av.setPixmap(_letter_avatar(initials, 36, c))
            ml.addWidget(av)

            # Crown for #1
            if idx == 0:
                crown = QLabel()
                crown.setFixedSize(16, 16)
                cp = _svg_pixmap(_ICON_TROPHY, 12, _ORANGE)
                if not cp.isNull():
                    crown.setPixmap(cp)
                ml.addWidget(crown)

            # Name + role
            nc = QVBoxLayout()
            nc.setSpacing(0)
            nlbl = QLabel(name)
            nlbl.setStyleSheet(
                f"color:{_TXT1};font-size:13px;font-weight:600;background:transparent;"
            )
            rlbl = QLabel(role)
            rlbl.setStyleSheet(
                f"color:{_TXT3};font-size:11px;background:transparent;"
            )
            nc.addWidget(nlbl)
            nc.addWidget(rlbl)
            ml.addLayout(nc, 1)

            # KPD bar
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(kpd)
            bar.setFixedHeight(6)
            bar.setFixedWidth(120)
            bar.setTextVisible(False)
            bar.setStyleSheet(
                f"QProgressBar{{background:{_CARD_ELEV};border-radius:3px;border:none;}}"
                f"QProgressBar::chunk{{background:{_ACCENT};border-radius:3px;}}"
            )
            ml.addWidget(bar)

            # KPD value
            kv = QLabel(str(kpd))
            kv.setStyleSheet(
                f"color:{_ORANGE};font-size:13px;font-weight:700;background:transparent;"
            )
            ml.addWidget(kv)

            # Time label
            tl = QLabel("Сейчас")
            tl.setStyleSheet(f"color:{_TXT3};font-size:11px;background:transparent;")
            ml.addWidget(tl)

            lcl.addWidget(mr)

        row.addWidget(left_card, 3)

        # RIGHT: Общий КПД команды
        right_card = QFrame()
        right_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        rcl = QVBoxLayout(right_card)
        rcl.setContentsMargins(24, 24, 24, 24)
        rcl.setSpacing(12)

        rh = QHBoxLayout()
        r_icon = QLabel()
        r_icon.setFixedSize(18, 18)
        rpx = _svg_pixmap(_ICON_ACTIVITY, 14, _PINK)
        if not rpx.isNull():
            r_icon.setPixmap(rpx)
        rh.addWidget(r_icon)
        r_title = QLabel("Общий КПД команды")
        r_title.setStyleSheet(
            f"color:{_TXT1};font-size:15px;font-weight:700;background:transparent;"
        )
        rh.addWidget(r_title, 1)
        rcl.addLayout(rh)

        big_kpd = QLabel(f"{avg_kpd}")
        big_kpd.setStyleSheet(
            f"color:{_PINK};font-size:56px;font-weight:800;background:transparent;"
        )
        pct_l = QLabel("%")
        pct_l.setStyleSheet(
            f"color:{_TXT3};font-size:22px;background:transparent;"
        )
        brow = QHBoxLayout()
        brow.addStretch(1)
        brow.addWidget(big_kpd)
        brow.addWidget(pct_l, 0, Qt.AlignBottom)
        brow.addStretch(1)
        rcl.addLayout(brow)

        avg_label = QLabel("Среднее по всем сотрудникам")
        avg_label.setAlignment(Qt.AlignCenter)
        avg_label.setStyleSheet(
            f"color:{_TXT2};font-size:12px;background:transparent;"
        )
        rcl.addWidget(avg_label)

        # Progress bar
        rpb = QProgressBar()
        rpb.setRange(0, 100)
        rpb.setValue(avg_kpd)
        rpb.setFixedHeight(8)
        rpb.setTextVisible(False)
        rpb.setStyleSheet(
            f"QProgressBar{{background:{_CARD_ELEV};border-radius:4px;border:none;}}"
            f"QProgressBar::chunk{{background:{_PINK};border-radius:4px;}}"
        )
        rcl.addWidget(rpb)

        # Scale
        rscale = QHBoxLayout()
        for v in ("0%", "50%", "100%"):
            l = QLabel(v)
            l.setStyleSheet(f"color:{_TXT3};font-size:10px;background:transparent;")
            rscale.addWidget(l)
            if v != "100%":
                rscale.addStretch(1)
        rcl.addLayout(rscale)

        goal_l = QLabel("Цель: 85%")
        goal_l.setStyleSheet(f"color:{_TXT3};font-size:11px;background:transparent;")
        rcl.addWidget(goal_l)
        rcl.addStretch(1)

        row.addWidget(right_card, 2)

        rw = QWidget()
        rw.setStyleSheet("background:transparent;")
        rw.setLayout(row)
        self._content_lay.addWidget(rw)
        self._content_lay.addStretch(1)

    # ══════════════════════════════════════════════════════════════
    #  TAB 2 — Детали
    # ══════════════════════════════════════════════════════════════

    def _build_details(self) -> None:
        org_id = session_store.org_id

        row = QHBoxLayout()
        row.setSpacing(16)

        # LEFT: Активность в реальном времени
        act_card = QFrame()
        act_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        acl = QVBoxLayout(act_card)
        acl.setContentsMargins(24, 20, 24, 20)
        acl.setSpacing(10)

        ah = QHBoxLayout()
        a_icon = QLabel()
        a_icon.setFixedSize(18, 18)
        apx = _svg_pixmap(_ICON_CLOCK, 14, _TXT2)
        if not apx.isNull():
            a_icon.setPixmap(apx)
        ah.addWidget(a_icon)
        a_title = QLabel("Активность в реальном времени")
        a_title.setStyleSheet(
            f"color:{_TXT1};font-size:15px;font-weight:700;background:transparent;"
        )
        ah.addWidget(a_title, 1)
        live_dot = QLabel("LIVE")
        live_dot.setStyleSheet(
            f"color:{_GREEN};font-size:11px;font-weight:700;background:transparent;"
        )
        ah.addWidget(live_dot)
        acl.addLayout(ah)

        # Container for live sessions list (will be populated & refreshed)
        box = QVBoxLayout()
        box.setContentsMargins(0, 8, 0, 8)
        box.setSpacing(0)
        acl.addLayout(box)
        self._sessions_box = box
        # Initial load
        self._refresh_sessions()

        # Live preview panel
        preview = QLabel()
        preview.setFixedSize(360, 210)
        preview.setAlignment(Qt.AlignCenter)
        preview.setStyleSheet(
            f"color:{_TXT3};font-size:12px;background:{_CARD_ELEV};"
            f"border-radius:12px;"
        )
        preview.setText(
            "Выберите активную сессию, чтобы наблюдать экран сотрудника в реальном времени"
        )
        self._live_preview_label = preview
        acl.addSpacing(12)
        acl.addWidget(preview)

        acl.addStretch(1)
        row.addWidget(act_card, 1)

        # RIGHT: ИИ-аналитика
        ai_card = QFrame()
        ai_card.setStyleSheet(
            f"QFrame{{background:{_CARD};border:1px solid {_BORDER};border-radius:16px;}}"
        )
        ail = QVBoxLayout(ai_card)
        ail.setContentsMargins(24, 20, 24, 20)
        ail.setSpacing(10)

        aih = QHBoxLayout()
        ai_icon = QLabel()
        ai_icon.setFixedSize(18, 18)
        aipx = _svg_pixmap(_ICON_SETTINGS, 14, _ACCENT)
        if not aipx.isNull():
            ai_icon.setPixmap(aipx)
        aih.addWidget(ai_icon)
        ai_title = QLabel("ИИ-аналитика")
        ai_title.setStyleSheet(
            f"color:{_TXT1};font-size:15px;font-weight:700;background:transparent;"
        )
        aih.addWidget(ai_title, 1)
        ail.addLayout(aih)

        # Filter pills
        fpills = QHBoxLayout()
        fpills.setSpacing(6)
        filters = ["Все", "Улучшения", "Предупреждения", "Достижения", "Рекомендации"]
        for i, f in enumerate(filters):
            fb = QPushButton(f)
            fb.setCursor(Qt.PointingHandCursor)
            fb.setFixedHeight(28)
            if i == 0:
                fb.setStyleSheet(
                    f"QPushButton{{background:{_ACCENT};color:{_BG};font-size:11px;"
                    f"font-weight:700;border:none;border-radius:14px;padding:0 12px;}}"
                )
            else:
                fb.setStyleSheet(
                    f"QPushButton{{background:{_CARD_ELEV};color:{_TXT2};font-size:11px;"
                    f"font-weight:500;border:none;border-radius:14px;padding:0 12px;}}"
                    f"QPushButton:hover{{background:{_BORDER2};}}"
                )
            fpills.addWidget(fb)
        fpills.addStretch(1)
        ail.addLayout(fpills)

        # AI recommendations — load from backend
        recs = []
        if org_id:
            try:
                ai_data = api_client.get_ai_kpi(
                    org_id,
                    start_date=date.today().isoformat(),
                    end_date=date.today().isoformat(),
                    team_id=self._team_id,
                    project_id=None,
                )
                users = ai_data.get("users", [])
                for u in users:
                    for r in u.get("recommendations", [])[:2]:
                        recs.append(r)
                    if len(recs) >= 5:
                        break
            except Exception:
                pass

        if not recs:
            recs = [
                "Мониторинг пока не запущен. Начните сессию для получения рекомендаций.",
                "ИИ-анализ будет доступен после сбора данных активности.",
            ]

        for r in recs[:5]:
            rc = QFrame()
            rc.setStyleSheet(
                f"QFrame{{background:{_CARD_ELEV};border:none;border-radius:10px;}}"
            )
            rcl2 = QHBoxLayout(rc)
            rcl2.setContentsMargins(14, 10, 14, 10)
            rcl2.setSpacing(10)

            bulb = QLabel()
            bulb.setFixedSize(20, 20)
            bp2 = _svg_pixmap(_ICON_BULB, 14, _ACCENT)
            if not bp2.isNull():
                bulb.setPixmap(bp2)
            rcl2.addWidget(bulb)

            txt = QLabel(str(r) if isinstance(r, str) else r.get("text", str(r)))
            txt.setWordWrap(True)
            txt.setStyleSheet(
                f"color:{_TXT2};font-size:12px;background:transparent;"
            )
            rcl2.addWidget(txt, 1)

            tag2 = QLabel("NEW")
            tag2.setStyleSheet(
                f"color:{_BG};font-size:9px;font-weight:700;"
                f"background:{_GREEN};border-radius:3px;padding:1px 6px;"
            )
            rcl2.addWidget(tag2)
            ail.addWidget(rc)

        # Footer
        powered = QLabel("Powered by Ultra AI")
        powered.setAlignment(Qt.AlignRight)
        powered.setStyleSheet(
            f"color:{_TXT3};font-size:10px;background:transparent;"
        )
        ail.addWidget(powered)
        ail.addStretch(1)

        row.addWidget(ai_card, 1)

        rw = QWidget()
        rw.setStyleSheet("background:transparent;")
        rw.setLayout(row)
        self._content_lay.addWidget(rw)
        self._content_lay.addStretch(1)

    def _refresh_sessions(self) -> None:
        """Reload list of active sessions for the left LIVE card."""
        if not hasattr(self, "_sessions_box") or self._sessions_box is None:
            return
        # Clear previous widgets
        while self._sessions_box.count():
            item = self._sessions_box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        org_id = session_store.org_id
        if not org_id:
            empty = QLabel("Нет активных сессий")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color:{_TXT3};font-size:13px;background:transparent;padding:20px;"
            )
            self._sessions_box.addWidget(empty)
            self._sessions_timer.stop()
            return

        role = getattr(session_store, "role", "member")
        activities: list[dict] = []
        try:
            if role in ("admin", "manager"):
                sessions = api_client.list_org_sessions(org_id)
            else:
                # For team leads and regular members — show their own sessions
                sessions = api_client.list_my_sessions(org_id)
            for s in sessions[:12]:
                activities.append(
                    {
                        "session_id": s.get("id", ""),
                        "device": s.get("device_name", "Устройство"),
                        "time": (s.get("started_at") or "")[:19].replace("T", " "),
                        "ended": s.get("ended_at") is not None,
                    }
                )
        except Exception:
            activities = []

        if not activities:
            empty = QLabel("Нет активных сессий")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                f"color:{_TXT3};font-size:13px;background:transparent;padding:20px;"
            )
            self._sessions_box.addWidget(empty)
            # keep timer running — сессия может появиться чуть позже
            return

        for act in activities:
            ar = QFrame()
            ar.setStyleSheet(
                f"QFrame{{background:transparent;border:none;"
                f"border-bottom:1px solid {_BORDER};}}"
            )
            arl = QHBoxLayout(ar)
            arl.setContentsMargins(0, 8, 0, 8)
            arl.setSpacing(10)

            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(
                f"background:{'#4a5068' if act['ended'] else _GREEN};"
                f"border-radius:4px;"
            )
            arl.addWidget(dot)

            dev = QLabel(act["device"])
            dev.setStyleSheet(
                f"color:{_TXT1};font-size:13px;font-weight:600;background:transparent;"
            )
            arl.addWidget(dev, 1)

            tag = QLabel("Завершена" if act["ended"] else "Продуктивная")
            tag_color = _TXT3 if act["ended"] else _GREEN
            tag.setStyleSheet(
                f"color:{_BG};font-size:10px;font-weight:700;"
                f"background:{tag_color};border-radius:4px;padding:2px 8px;"
            )
            arl.addWidget(tag)

            tm = QLabel(act["time"])
            tm.setStyleSheet(
                f"color:{_TXT3};font-size:11px;background:transparent;"
            )
            arl.addWidget(tm)

            # Watch button for live preview (only for active sessions)
            if not act["ended"]:
                watch = QPushButton("Смотреть")
                watch.setCursor(Qt.PointingHandCursor)
                watch.setStyleSheet(
                    f"QPushButton{{background:{_CARD_ELEV};color:{_TXT2};"
                    f"font-size:11px;border:none;border-radius:12px;padding:4px 10px;}}"
                    f"QPushButton:hover{{background:{_BORDER2};}}"
                )
                sid = act["session_id"]
                watch.clicked.connect(
                    lambda _=False, s_id=sid: self._start_live_preview(s_id)
                )
                arl.addWidget(watch)

            self._sessions_box.addWidget(ar)

        # Ensure periodic refresh is active while details tab is shown
        if not self._sessions_timer.isActive():
            self._sessions_timer.start()
    # ══════════════════════════════════════════════════════════════
    #  Live preview helpers
    # ══════════════════════════════════════════════════════════════

    def _start_live_preview(self, session_id: str) -> None:
        """Begin polling live preview frames for the given session."""
        org_id = session_store.org_id
        if not org_id:
            return
        self._live_session_id = session_id
        self._live_org_id = org_id
        if self._live_preview_label is not None:
            self._live_preview_label.setText("Подключаемся к трансляции экрана…")
            self._live_preview_label.setPixmap(QPixmap())
        if not self._live_timer.isActive():
            self._live_timer.start()

    def _poll_live_preview(self) -> None:
        """Fetch latest preview frame and render it into the preview label."""
        if not self._live_session_id or not self._live_org_id:
            self._live_timer.stop()
            return
        if self._live_preview_label is None:
            self._live_timer.stop()
            return
        try:
            data = api_client.get_session_preview(self._live_org_id, self._live_session_id)
            if not data:
                return
            pix = QPixmap()
            if not pix.loadFromData(data):
                return
            scaled = pix.scaled(
                self._live_preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self._live_preview_label.setPixmap(scaled)
        except ApiError as exc:
            # 404 means no preview yet — show gentle placeholder
            if getattr(exc, "status_code", None) == 404:
                self._live_preview_label.setText(
                    "Нет актуального превью — сотрудник ещё не начал трансляцию"
                )
                self._live_preview_label.setPixmap(QPixmap())
            # Other errors are ignored to keep UI responsive

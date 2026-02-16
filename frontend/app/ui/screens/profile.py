"""Profile screen — Instagram-style profile page + edit profile form.

ProfileScreen = Instagram profile view (avatar, name, stats, bio, buttons).
The same class serves double duty as EditProfileScreen when used for editing.
"""

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QIcon,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
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
_ICON_ARROW_LEFT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="19" y1="12" x2="5" y2="12"/>'
    '<polyline points="12 19 5 12 12 5"/></svg>'
)

_ICON_USER = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>'
    '<circle cx="12" cy="7" r="4"/></svg>'
)

_ICON_GRID = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>'
    '<rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>'
    '</svg>'
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


def _round_pixmap(pix: QPixmap, size: int) -> QPixmap:
    """Clip a pixmap to a circle."""
    scaled = pix.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
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


# ═══════════════════════════════════════════════════════════════════════
#  ProfileScreen — Instagram profile page (VIEW)
# ═══════════════════════════════════════════════════════════════════════


class ProfileScreen(QWidget):
    """Instagram-style profile page — top part only.

    Shows: avatar, username, stats row, bio, 2 action buttons.
    Emits open_edit_profile to navigate to edit form.
    go_back returns to dashboard.
    """

    go_back = Signal()
    open_edit_profile = Signal()

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

        self._header_name = QLabel("")
        self._header_name.setStyleSheet(
            "color:#e8eaf0;font-size:18px;font-weight:700;background:transparent;"
        )

        hl.addWidget(self._header_name, 1, Qt.AlignCenter)
        outer.addWidget(header)

        # ── Body ──────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#0c1021;border:none;")

        body = QWidget()
        body.setStyleSheet("background:#0c1021;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(0)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # ── Top section: avatar + stats (horizontal like Instagram) ──
        top_section = QWidget()
        top_section.setStyleSheet("background:transparent;")
        ts = QHBoxLayout(top_section)
        ts.setContentsMargins(28, 28, 28, 16)
        ts.setSpacing(28)

        # Avatar (left)
        self._avatar_label = QLabel()
        self._avatar_label.setFixedSize(86, 86)
        self._avatar_label.setAlignment(Qt.AlignCenter)
        self._avatar_label.setStyleSheet(
            "background:#1e2538;border-radius:43px;border:2px solid #2a3150;"
        )
        user_ic = _svg_pixmap(_ICON_USER, 36, "#4a5068")
        if not user_ic.isNull():
            self._avatar_label.setPixmap(user_ic)
        ts.addWidget(self._avatar_label)

        # Stats (right): 3 columns
        stats_col = QVBoxLayout()
        stats_col.setSpacing(12)
        stats_col.setContentsMargins(0, 8, 0, 0)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(24)

        self._stat_projects = self._stat_widget("0", "проектов")
        self._stat_colleagues = self._stat_widget("0", "коллег")
        self._stat_org = self._stat_widget("0", "компания")

        stats_row.addLayout(self._stat_projects)
        stats_row.addLayout(self._stat_colleagues)
        stats_row.addLayout(self._stat_org)
        stats_row.addStretch(1)

        stats_col.addLayout(stats_row)
        ts.addLayout(stats_col, 1)

        bl.addWidget(top_section)

        # ── Bio section ───────────────────────────────────────────
        bio_section = QWidget()
        bio_section.setStyleSheet("background:transparent;")
        bio_lay = QVBoxLayout(bio_section)
        bio_lay.setContentsMargins(28, 0, 28, 16)
        bio_lay.setSpacing(4)

        self._display_name = QLabel("")
        self._display_name.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:700;background:transparent;"
        )

        self._specialty_label = QLabel("")
        self._specialty_label.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )

        self._bio_label = QLabel("")
        self._bio_label.setStyleSheet(
            "color:#8891a5;font-size:14px;background:transparent;"
        )
        self._bio_label.setWordWrap(True)

        self._org_label = QLabel("")
        self._org_label.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )

        bio_lay.addWidget(self._display_name)
        bio_lay.addWidget(self._specialty_label)
        bio_lay.addWidget(self._bio_label)
        bio_lay.addWidget(self._org_label)

        bl.addWidget(bio_section)

        # ── Action buttons ────────────────────────────────────────
        btn_section = QWidget()
        btn_section.setStyleSheet("background:transparent;")
        btn_lay = QHBoxLayout(btn_section)
        btn_lay.setContentsMargins(28, 4, 28, 16)
        btn_lay.setSpacing(8)

        self._edit_btn = QPushButton("Редактировать профиль")
        self._edit_btn.setCursor(Qt.PointingHandCursor)
        self._edit_btn.setFixedHeight(36)
        self._edit_btn.setStyleSheet(
            "QPushButton{background:#1e2538;color:#e8eaf0;font-size:14px;"
            "font-weight:600;border:1px solid #2a3150;border-radius:8px;"
            "padding:0 16px;}"
            "QPushButton:hover{background:#2a3150;}"
        )
        self._edit_btn.clicked.connect(self.open_edit_profile.emit)

        btn_lay.addWidget(self._edit_btn)

        bl.addWidget(btn_section)

        # ── Separator ─────────────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#1e2538;")
        bl.addWidget(sep)

        # ── Empty content area (placeholder) ──────────────────────
        empty_area = QWidget()
        empty_area.setStyleSheet("background:transparent;")
        ea = QVBoxLayout(empty_area)
        ea.setContentsMargins(0, 60, 0, 0)
        ea.setSpacing(12)

        empty_hint = QLabel("Ваша активность и проекты появятся здесь")
        empty_hint.setStyleSheet(
            "color:#4a5068;font-size:14px;background:transparent;"
        )
        empty_hint.setAlignment(Qt.AlignCenter)
        ea.addWidget(empty_hint)
        ea.addStretch(1)

        bl.addWidget(empty_area, 1)

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _stat_widget(value: str, label: str):
        lay = QVBoxLayout()
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignCenter)
        v = QLabel(value)
        v.setAlignment(Qt.AlignCenter)
        v.setStyleSheet(
            "color:#e8eaf0;font-size:17px;font-weight:700;background:transparent;"
        )
        l = QLabel(label)
        l.setAlignment(Qt.AlignCenter)
        l.setStyleSheet(
            "color:#8891a5;font-size:12px;background:transparent;"
        )
        v.setObjectName(f"StatVal_{label}")
        lay.addWidget(v)
        lay.addWidget(l)
        return lay

    # ── Public ────────────────────────────────────────────────────

    def refresh_profile(self) -> None:
        if not session_store.token:
            return
        # Update avatar from session
        self._update_avatar()
        try:
            profile = api_client.get_me()
            name = profile.get("full_name") or "Пользователь"
            self._header_name.setText(name)
            self._display_name.setText(name)
            self._specialty_label.setText(profile.get("specialty") or "")
            self._bio_label.setText(profile.get("bio") or "")

            # Show org info
            org_id = session_store.org_id
            if org_id:
                try:
                    org = api_client.get_org(org_id)
                    self._org_label.setText(org.get("name", ""))
                    item = self._stat_org.itemAt(0)
                    if item and item.widget():
                        item.widget().setText("1")
                except Exception:
                    pass

            self._specialty_label.setVisible(bool(profile.get("specialty")))
            self._bio_label.setVisible(bool(profile.get("bio")))
            self._org_label.setVisible(bool(org_id))
        except ApiError:
            pass

    def _update_avatar(self) -> None:
        """Load avatar from session_store.avatar_path or backend URL or show default."""
        path = session_store.avatar_path
        if path:
            pix = QPixmap(path)
            if not pix.isNull():
                self._avatar_label.setPixmap(_round_pixmap(pix, 86))
                return
        # Try loading from backend avatar_url
        try:
            profile = api_client.get_me()
            avatar_url = profile.get("avatar_url")
            if avatar_url:
                import httpx
                full_url = api_client.get_avatar_url(avatar_url)
                resp = httpx.get(full_url, timeout=5)
                if resp.status_code == 200:
                    pix = QPixmap()
                    pix.loadFromData(resp.content)
                    if not pix.isNull():
                        self._avatar_label.setPixmap(_round_pixmap(pix, 86))
                        return
        except Exception:  # noqa: BLE001
            pass
        # Default avatar
        default = QPixmap(86, 86)
        default.fill(QColor(0, 0, 0, 0))
        p = QPainter(default)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#2a3150"))
        p.drawEllipse(0, 0, 86, 86)
        p.setPen(QColor("#8891a5"))
        p.drawText(default.rect(), Qt.AlignCenter, "U")
        p.end()
        self._avatar_label.setPixmap(default)


# ═══════════════════════════════════════════════════════════════════════
#  EditProfileScreen — full edit form
# ═══════════════════════════════════════════════════════════════════════


class EditProfileScreen(QWidget):
    """Edit profile form — fields, avatar upload, save button."""

    go_back = Signal()
    avatar_changed = Signal()  # emitted when user picks new avatar

    def __init__(self) -> None:
        super().__init__()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("background:#151a2e;border-bottom:1px solid #1e2538;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 10, 16, 10)

        back_btn = QPushButton()
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setIcon(_svg_icon(_ICON_ARROW_LEFT, 20, "#8891a5"))
        back_btn.setFixedSize(36, 36)
        back_btn.setStyleSheet(
            "QPushButton{background:transparent;border:none;}"
            "QPushButton:hover{background:#1e2538;border-radius:6px;}"
        )
        back_btn.clicked.connect(self.go_back.emit)

        title = QLabel("Редактировать профиль")
        title.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:600;background:transparent;"
        )

        hl.addWidget(back_btn)
        hl.addWidget(title, 1)
        outer.addWidget(header)

        # ── Scrollable body ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("background:#0c1021;")

        body = QWidget()
        body.setStyleSheet("background:#0c1021;")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 0, 0, 40)
        bl.setSpacing(0)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # ── Avatar section ────────────────────────────────────────
        avatar_section = QWidget()
        avatar_section.setStyleSheet("background:transparent;")
        avl = QVBoxLayout(avatar_section)
        avl.setContentsMargins(0, 28, 0, 20)
        avl.setAlignment(Qt.AlignHCenter)
        avl.setSpacing(12)

        self._avatar_label = QLabel()
        self._avatar_label.setFixedSize(96, 96)
        self._avatar_label.setAlignment(Qt.AlignCenter)
        self._avatar_label.setStyleSheet(
            "background:#1e2538;border-radius:48px;"
        )
        user_pix = _svg_pixmap(_ICON_USER, 40, "#4a5068")
        if not user_pix.isNull():
            self._avatar_label.setPixmap(user_pix)

        change_photo = QPushButton("Изменить фото")
        change_photo.setCursor(Qt.PointingHandCursor)
        change_photo.setStyleSheet(
            "QPushButton{color:#4f8fff;font-size:13px;font-weight:600;"
            "background:transparent;border:none;}"
            "QPushButton:hover{text-decoration:underline;}"
        )
        change_photo.clicked.connect(self._pick_avatar)

        avl.addWidget(self._avatar_label, 0, Qt.AlignHCenter)
        avl.addWidget(change_photo, 0, Qt.AlignHCenter)
        bl.addWidget(avatar_section)

        # ── Form fields ──────────────────────────────────────────
        form = QWidget()
        form.setStyleSheet("background:transparent;")
        fl = QVBoxLayout(form)
        fl.setContentsMargins(32, 0, 32, 0)
        fl.setSpacing(20)

        self.name_input = self._make_field(fl, "Имя", "Полное имя")
        self.patronymic_input = self._make_field(fl, "Отчество", "Отчество")

        bio_label = QLabel("О себе")
        bio_label.setStyleSheet("color:#8891a5;font-size:12px;background:transparent;")
        self.bio_input = QTextEdit()
        self.bio_input.setPlaceholderText("Расскажите о себе...")
        self.bio_input.setFixedHeight(80)
        self.bio_input.setStyleSheet(
            "QTextEdit{color:#e8eaf0;font-size:14px;background:#0c1021;"
            "border:1px solid #2a3150;border-radius:8px;padding:10px;}"
            "QTextEdit:focus{border-color:#4f8fff;}"
        )
        fl.addWidget(bio_label)
        fl.addWidget(self.bio_input)

        self.specialty_input = self._make_field(fl, "Специальность", "Разработчик, дизайнер...")
        self.website_input = self._make_field(fl, "Сайт", "https://example.com")
        self.socials_input = self._make_field(fl, "Ссылки", "Telegram, GitHub...")

        gender_label = QLabel("Пол")
        gender_label.setStyleSheet("color:#8891a5;font-size:12px;background:transparent;")
        self.gender_combo = QComboBox()
        self.gender_combo.addItem("Не указан", "")
        self.gender_combo.addItem("Мужской", "male")
        self.gender_combo.addItem("Женский", "female")
        self.gender_combo.setStyleSheet(
            "QComboBox{color:#e8eaf0;font-size:14px;background:#0c1021;"
            "border:1px solid #2a3150;border-radius:8px;padding:8px 12px;}"
            "QComboBox:focus{border-color:#4f8fff;}"
            "QComboBox::drop-down{border:none;}"
            "QComboBox QAbstractItemView{background:#151a2e;color:#e8eaf0;"
            "selection-background-color:#1e2538;border:1px solid #2a3150;}"
        )
        fl.addWidget(gender_label)
        fl.addWidget(self.gender_combo)
        bl.addWidget(form)

        # ── Separator + info ─────────────────────────────────────
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#1e2538;")
        bl.addSpacing(24)
        bl.addWidget(sep)
        bl.addSpacing(16)

        info_label = QLabel("Эта информация видна другим участникам вашей организации.")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color:#4a5068;font-size:12px;background:transparent;")
        bl.addWidget(info_label)
        bl.addSpacing(20)

        # ── Status + Save ─────────────────────────────────────────
        bottom = QWidget()
        bottom.setStyleSheet("background:transparent;")
        btl = QVBoxLayout(bottom)
        btl.setContentsMargins(32, 0, 32, 0)
        btl.setSpacing(12)

        self.profile_status = QLabel("")
        self.profile_status.setAlignment(Qt.AlignCenter)
        self.profile_status.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )

        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setFixedHeight(44)
        self.save_btn.setStyleSheet(
            "QPushButton{background:#4f8fff;color:#0c1021;font-size:14px;"
            "font-weight:600;border:none;border-radius:10px;}"
            "QPushButton:hover{background:#6ba3ff;}"
            "QPushButton:disabled{background:#1e2538;color:#4a5068;}"
        )
        self.save_btn.clicked.connect(self._save_profile)

        btl.addWidget(self.profile_status)
        btl.addWidget(self.save_btn)
        bl.addWidget(bottom)
        bl.addStretch(1)

        self._avatar_path: str | None = None

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _make_field(parent_layout: QVBoxLayout, label: str, placeholder: str) -> QLineEdit:
        lbl = QLabel(label)
        lbl.setStyleSheet("color:#8891a5;font-size:12px;background:transparent;")
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setStyleSheet(
            "QLineEdit{color:#e8eaf0;font-size:14px;background:#0c1021;"
            "border:1px solid #2a3150;border-radius:8px;padding:10px 12px;}"
            "QLineEdit:focus{border-color:#4f8fff;}"
        )
        parent_layout.addWidget(lbl)
        parent_layout.addWidget(inp)
        return inp

    def _pick_avatar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Фото профиля", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        self._avatar_path = path
        session_store.set_avatar_path(path)
        pix = QPixmap(path)
        if not pix.isNull():
            self._avatar_label.setPixmap(_round_pixmap(pix, 96))
        self.avatar_changed.emit()
        # Upload to backend
        try:
            api_client.upload_avatar(path)
        except Exception:  # noqa: BLE001
            pass

    def refresh_profile(self) -> None:
        if not session_store.token:
            return
        self.profile_status.setText("")
        # Load avatar from session (local) or from backend URL
        avatar = session_store.avatar_path
        if avatar:
            pix = QPixmap(avatar)
            if not pix.isNull():
                self._avatar_label.setPixmap(_round_pixmap(pix, 96))
        try:
            profile = api_client.get_me()
            self.name_input.setText(profile.get("full_name") or "")
            self.patronymic_input.setText(profile.get("patronymic") or "")
            self.bio_input.setText(profile.get("bio") or "")
            self.specialty_input.setText(profile.get("specialty") or "")
            self.website_input.setText(profile.get("website") or "")
            self.socials_input.setText(profile.get("socials_json") or "")
            gender = profile.get("gender") or ""
            idx = self.gender_combo.findData(gender)
            if idx >= 0:
                self.gender_combo.setCurrentIndex(idx)
        except ApiError:
            self.profile_status.setText("Не удалось загрузить профиль")

    def _save_profile(self) -> None:
        payload = {
            "full_name": self.name_input.text().strip() or None,
            "patronymic": self.patronymic_input.text().strip() or None,
            "bio": self.bio_input.toPlainText().strip() or None,
            "specialty": self.specialty_input.text().strip() or None,
            "website": self.website_input.text().strip() or None,
            "socials_json": self.socials_input.text().strip() or None,
            "gender": self.gender_combo.currentData() or None,
        }
        self.save_btn.setEnabled(False)
        try:
            profile = api_client.update_me(payload)
            session_store.set_user_profile(
                profile.get("id"),
                profile.get("full_name"),
                profile.get("patronymic"),
            )
            self.profile_status.setText("Профиль обновлен")
        except ApiError as exc:
            self.profile_status.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.profile_status.setText(f"Ошибка: {exc}")
        finally:
            self.save_btn.setEnabled(True)

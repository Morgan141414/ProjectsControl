"""Organization creation wizard — Telegram/WhatsApp-style group creation.

Rich customization: avatar, name, description, industry, theme, privacy,
welcome message, website, max members.
"""

from PySide6.QtCore import QByteArray, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
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

# SVG icons
_ICON_ARROW_LEFT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="19" y1="12" x2="5" y2="12"/>'
    '<polyline points="12 19 5 12 12 5"/></svg>'
)

_ICON_CAMERA = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4'
    'a2 2 0 0 1 2 2z"/>'
    '<circle cx="12" cy="13" r="4"/></svg>'
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


class OrgWizardScreen(QWidget):
    """Full-screen org creation wizard with rich customization."""

    org_created = Signal()  # emitted after successful creation
    go_back = Signal()      # user pressed back

    def __init__(self) -> None:
        super().__init__()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("WizScroll")

        inner = QWidget()
        inner.setObjectName("WizInner")
        root = QVBoxLayout(inner)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        # ── Header bar ────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("WizHeader")
        header_lay = QHBoxLayout(header)
        header_lay.setContentsMargins(32, 16, 32, 16)

        self.back_btn = QPushButton("  Назад")
        self.back_btn.setObjectName("WizBack")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.setIcon(_svg_icon(_ICON_ARROW_LEFT, 16, "#8891a5"))
        self.back_btn.clicked.connect(self.go_back.emit)

        header_title = QLabel("Создание организации")
        header_title.setObjectName("WizHeaderTitle")

        header_lay.addWidget(self.back_btn)
        header_lay.addStretch(1)
        header_lay.addWidget(header_title)
        header_lay.addStretch(1)
        # Spacer to balance the back button
        spacer = QLabel("")
        spacer.setFixedWidth(80)
        header_lay.addWidget(spacer)

        root.addWidget(header)

        # ── Main form area ────────────────────────────────────────
        form_wrapper = QWidget()
        form_wrapper.setObjectName("WizFormArea")
        form_outer = QHBoxLayout(form_wrapper)
        form_outer.setContentsMargins(40, 32, 40, 40)
        form_outer.setSpacing(32)

        # LEFT — form fields
        left = QFrame()
        left.setObjectName("WizFormPanel")
        fl = QVBoxLayout(left)
        fl.setContentsMargins(32, 28, 32, 28)
        fl.setSpacing(16)

        # Avatar section
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(20)

        self._avatar_frame = QFrame()
        self._avatar_frame.setObjectName("WizAvatarFrame")
        self._avatar_frame.setFixedSize(96, 96)
        av_lay = QVBoxLayout(self._avatar_frame)
        av_lay.setContentsMargins(0, 0, 0, 0)
        self._avatar_icon = QLabel()
        self._avatar_icon.setAlignment(Qt.AlignCenter)
        cam = _svg_icon(_ICON_CAMERA, 36, "#4a5068")
        if not cam.isNull():
            self._avatar_icon.setPixmap(cam.pixmap(36, 36))
        self._avatar_icon.setStyleSheet("background: transparent;")
        av_lay.addWidget(self._avatar_icon)

        avatar_info = QVBoxLayout()
        avatar_info.setSpacing(6)
        av_title = QLabel("Логотип компании")
        av_title.setObjectName("WizLabel")
        av_hint = QLabel("Рекомендуемый размер: 512×512 px")
        av_hint.setObjectName("WizHint")
        self._avatar_btn = QPushButton("Загрузить")
        self._avatar_btn.setObjectName("WizSecondary")
        self._avatar_btn.setCursor(Qt.PointingHandCursor)
        self._avatar_btn.clicked.connect(self._pick_avatar)
        avatar_info.addWidget(av_title)
        avatar_info.addWidget(av_hint)
        avatar_info.addWidget(self._avatar_btn)

        avatar_row.addWidget(self._avatar_frame)
        avatar_row.addLayout(avatar_info)
        avatar_row.addStretch(1)
        fl.addLayout(avatar_row)
        fl.addSpacing(8)

        # Name
        self.name_input, g1 = self._field(
            "Название организации *", "Например: Гиперстоун"
        )
        fl.addWidget(g1)

        # Description
        desc_label = QLabel("Описание")
        desc_label.setObjectName("WizLabel")
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(
            "Расскажите о компании, миссии и целях..."
        )
        self.desc_input.setObjectName("WizTextArea")
        self.desc_input.setFixedHeight(100)
        fl.addWidget(desc_label)
        fl.addWidget(self.desc_input)

        # Industry / category
        self.industry_input, g2 = self._field(
            "Отрасль", "IT, Финансы, Образование..."
        )
        fl.addWidget(g2)

        # Theme color
        color_label = QLabel("Цвет темы")
        color_label.setObjectName("WizLabel")
        self.color_combo = QComboBox()
        self.color_combo.setObjectName("WizCombo")
        colors = [
            ("Синий (по умолчанию)", "#1f6feb"),
            ("Зелёный", "#2563eb"),
            ("Фиолетовый", "#8957e5"),
            ("Красный", "#da3633"),
            ("Оранжевый", "#d29922"),
            ("Серый", "#6e7681"),
        ]
        for label, value in colors:
            self.color_combo.addItem(label, value)
        fl.addWidget(color_label)
        fl.addWidget(self.color_combo)

        # ── New customization fields ──────────────────────────────

        # Website
        self.website_input, g_web = self._field("Сайт компании", "https://example.com")
        fl.addWidget(g_web)

        # Welcome message for new members
        welcome_label = QLabel("Приветственное сообщение")
        welcome_label.setObjectName("WizLabel")
        self.welcome_input = QTextEdit()
        self.welcome_input.setPlaceholderText(
            "Сообщение, которое увидят новые участники при вступлении..."
        )
        self.welcome_input.setObjectName("WizTextArea")
        self.welcome_input.setFixedHeight(80)
        fl.addWidget(welcome_label)
        fl.addWidget(self.welcome_input)

        # Privacy setting
        privacy_label = QLabel("Приватность")
        privacy_label.setObjectName("WizLabel")
        self.privacy_combo = QComboBox()
        self.privacy_combo.setObjectName("WizCombo")
        self.privacy_combo.addItem("Открытая — любой может запросить вступление", "open")
        self.privacy_combo.addItem("Закрытая — только по приглашению", "closed")
        fl.addWidget(privacy_label)
        fl.addWidget(self.privacy_combo)

        # Max members
        max_label = QLabel("Макс. участников")
        max_label.setObjectName("WizLabel")
        self.max_members = QSpinBox()
        self.max_members.setObjectName("WizInput")
        self.max_members.setRange(2, 10000)
        self.max_members.setValue(100)
        self.max_members.setSuffix(" чел.")
        fl.addWidget(max_label)
        fl.addWidget(self.max_members)

        # Auto-approve
        self.auto_approve = QCheckBox("Автоматически одобрять заявки")
        self.auto_approve.setObjectName("WizCheck")
        self.auto_approve.setStyleSheet(
            "color: #8891a5; font-size: 13px; background: transparent;"
        )
        fl.addWidget(self.auto_approve)

        fl.addSpacing(8)

        # Status
        self.status_label = QLabel("")
        self.status_label.setObjectName("WizStatus")
        self.status_label.setWordWrap(True)
        fl.addWidget(self.status_label)

        # Create button
        self.create_btn = QPushButton("Создать организацию")
        self.create_btn.setObjectName("WizCreate")
        self.create_btn.setCursor(Qt.PointingHandCursor)
        self.create_btn.setFixedHeight(48)
        self.create_btn.clicked.connect(self._create)
        fl.addWidget(self.create_btn)

        fl.addStretch(1)

        # RIGHT — live preview card
        right = QFrame()
        right.setObjectName("WizPreviewPanel")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(28, 24, 28, 24)
        rl.setSpacing(16)

        preview_title = QLabel("Предпросмотр")
        preview_title.setObjectName("WizPreviewTitle")
        rl.addWidget(preview_title)

        # Preview card
        self._preview_card = QFrame()
        self._preview_card.setObjectName("WizPreviewCard")
        pcl = QVBoxLayout(self._preview_card)
        pcl.setContentsMargins(24, 20, 24, 20)
        pcl.setSpacing(10)

        self._preview_avatar = QLabel()
        self._preview_avatar.setAlignment(Qt.AlignCenter)
        self._preview_avatar.setStyleSheet("background: transparent;")
        cam_preview = _svg_icon(_ICON_CAMERA, 48, "#4a5068")
        if not cam_preview.isNull():
            self._preview_avatar.setPixmap(cam_preview.pixmap(48, 48))
        self._preview_name = QLabel("Название компании")
        self._preview_name.setObjectName("WizPreviewName")
        self._preview_name.setAlignment(Qt.AlignCenter)
        self._preview_desc = QLabel("Описание организации")
        self._preview_desc.setObjectName("WizPreviewDesc")
        self._preview_desc.setAlignment(Qt.AlignCenter)
        self._preview_desc.setWordWrap(True)
        self._preview_industry = QLabel("")
        self._preview_industry.setObjectName("WizHint")
        self._preview_industry.setAlignment(Qt.AlignCenter)

        pcl.addWidget(self._preview_avatar)
        pcl.addWidget(self._preview_name)
        pcl.addWidget(self._preview_desc)
        pcl.addWidget(self._preview_industry)

        rl.addWidget(self._preview_card)

        preview_hint = QLabel(
            "Так будет выглядеть ваша организация\n"
            "для участников и гостей"
        )
        preview_hint.setObjectName("WizHint")
        preview_hint.setAlignment(Qt.AlignCenter)
        rl.addWidget(preview_hint)
        rl.addStretch(1)

        form_outer.addWidget(left, 3)
        form_outer.addWidget(right, 2)

        root.addWidget(form_wrapper, 1)

        # ── Live preview bindings ─────────────────────────────────
        self.name_input.textChanged.connect(self._update_preview)
        self.desc_input.textChanged.connect(self._update_preview)
        self.industry_input.textChanged.connect(self._update_preview)

        self._avatar_path: str | None = None

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _field(label: str, placeholder: str = "") -> tuple[QLineEdit, QWidget]:
        g = QWidget()
        lay = QVBoxLayout(g)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        lbl = QLabel(label)
        lbl.setObjectName("WizLabel")
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setObjectName("WizInput")
        lay.addWidget(lbl)
        lay.addWidget(inp)
        return inp, g

    def _pick_avatar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Логотип компании", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        self._avatar_path = path
        pix = QPixmap(path).scaled(
            88, 88, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        self._avatar_icon.setPixmap(pix)
        self._preview_avatar.setPixmap(
            QPixmap(path).scaled(64, 64, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        )

    def _update_preview(self) -> None:
        name = self.name_input.text().strip() or "Название компании"
        desc = self.desc_input.toPlainText().strip() or "Описание организации"
        ind = self.industry_input.text().strip()
        self._preview_name.setText(name)
        self._preview_desc.setText(desc)
        self._preview_industry.setText(ind)

    def _create(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            self.status_label.setText("Введите название организации")
            return

        self.create_btn.setEnabled(False)
        self.status_label.setText("Создаём...")

        try:
            org = api_client.create_org(name)
            session_store.set_org_id(org.get("id"))
            self.status_label.setText("Организация успешно создана!")
            self.org_created.emit()
        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка: {exc}")
        finally:
            self.create_btn.setEnabled(True)

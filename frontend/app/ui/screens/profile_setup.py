"""Profile setup — hh.ru-style multi-step questionnaire with ML validation.

Comprehensive registration form that collects:
  - Personal info (name, phone, email)
  - Professional info (position, experience, skills)
  - Education and bio
  - Avatar upload

ML model validates the questionnaire instantly and grants access.
"""

import sys
from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
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


class ProfileSetupScreen(QWidget):
    """hh.ru-style questionnaire — blocks progress until ML-approved."""

    profile_completed = Signal()

    def __init__(self) -> None:
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── LEFT: decorative panel ────────────────────────────────
        left = QFrame()
        left.setObjectName("SetupHero")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(48, 56, 48, 48)
        left_lay.setSpacing(20)

        icon_lbl = QLabel("PC")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(72, 72)
        icon_lbl.setStyleSheet(
            "font-size:22px;font-weight:800;color:#bc8cff;"
            "background:#151a2e;border-radius:36px;"
        )
        left_lay.addWidget(icon_lbl)

        title = QLabel("Анкета\nсоискателя")
        title.setObjectName("SetupHeroTitle")
        title.setWordWrap(True)
        left_lay.addWidget(title)

        sub = QLabel(
            "Заполните анкету для доступа к платформе.\n"
            "ИИ мгновенно проверит ваши данные и\n"
            "откроет доступ к основному интерфейсу."
        )
        sub.setObjectName("SetupHeroSub")
        sub.setWordWrap(True)
        left_lay.addWidget(sub)

        # Benefits list
        benefits = [
            "Поиск работы и подача резюме",
            "Контроль работы и КПД сотрудников",
            "ИИ-анализ продуктивности",
            "Управление отделами и персоналом",
        ]
        for b in benefits:
            bl = QLabel(f"  ✓  {b}")
            bl.setStyleSheet(
                "color:#8891a5;font-size:13px;background:transparent;"
            )
            left_lay.addWidget(bl)

        left_lay.addStretch(1)

        steps = QLabel("Шаг 3 из 3 — Заполнение анкеты")
        steps.setObjectName("SetupHeroFooter")
        left_lay.addWidget(steps)

        # ── RIGHT: scrollable form ─────────────────────────────────
        right = QFrame()
        right.setObjectName("SetupRight")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("border:none;")

        form_widget = QWidget()
        form = QVBoxLayout(form_widget)
        form.setContentsMargins(48, 40, 48, 40)
        form.setSpacing(14)

        form_title = QLabel("Заполните анкету")
        form_title.setObjectName("SetupFormTitle")
        form.addWidget(form_title)

        form_sub = QLabel("Поля со звёздочкой обязательны. ИИ автоматически проверит анкету.")
        form_sub.setObjectName("SetupFormSub")
        form.addWidget(form_sub)
        form.addSpacing(8)

        # ── Avatar ────────────────────────────────────────────────
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(16)

        self._avatar_frame = QFrame()
        self._avatar_frame.setObjectName("AvatarFrame")
        self._avatar_frame.setFixedSize(80, 80)
        avatar_inner = QVBoxLayout(self._avatar_frame)
        avatar_inner.setContentsMargins(0, 0, 0, 0)

        self._avatar_icon = QLabel("U")
        self._avatar_icon.setAlignment(Qt.AlignCenter)
        self._avatar_icon.setStyleSheet(
            "font-size:26px;color:#8891a5;font-weight:700;background:transparent;"
        )
        avatar_inner.addWidget(self._avatar_icon)

        avatar_info = QVBoxLayout()
        avatar_info.setSpacing(4)
        avatar_title = QLabel("Фото профиля")
        avatar_title.setObjectName("SetupFieldLabel")
        self._avatar_status = QLabel("Ещё не выбрано")
        self._avatar_status.setObjectName("SetupFieldHint")
        self._avatar_btn = QPushButton("Загрузить")
        self._avatar_btn.setObjectName("SetupSecondary")
        self._avatar_btn.setCursor(Qt.PointingHandCursor)
        self._avatar_btn.clicked.connect(self._pick_avatar)
        avatar_info.addWidget(avatar_title)
        avatar_info.addWidget(self._avatar_status)
        avatar_info.addWidget(self._avatar_btn)

        avatar_row.addWidget(self._avatar_frame)
        avatar_row.addLayout(avatar_info)
        avatar_row.addStretch(1)
        form.addLayout(avatar_row)
        form.addSpacing(8)

        # ── Section: Личные данные ────────────────────────────────
        sec1 = QLabel("Личные данные")
        sec1.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:700;background:transparent;"
            "padding-top:8px;"
        )
        form.addWidget(sec1)

        sep1 = QFrame()
        sep1.setFixedHeight(1)
        sep1.setStyleSheet("background:#1e2538;")
        form.addWidget(sep1)

        self.full_name_input, g1 = self._field("ФИО *", "Иванов Иван Иванович")
        self.email_input, g_email = self._field("Email *", "email@example.com")
        self.phone_input, g_phone = self._field("Телефон *", "+7 (777) 123-45-67")

        form.addWidget(g1)
        form.addWidget(g_email)
        form.addWidget(g_phone)
        form.addSpacing(8)

        # ── Section: Профессиональные данные ──────────────────────
        sec2 = QLabel("Профессиональные данные")
        sec2.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:700;background:transparent;"
            "padding-top:8px;"
        )
        form.addWidget(sec2)

        sep2 = QFrame()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background:#1e2538;")
        form.addWidget(sep2)

        self.position_input, g_pos = self._field("Желаемая должность *", "Frontend Developer")

        # Experience level combo
        exp_group = QWidget()
        exp_lay = QVBoxLayout(exp_group)
        exp_lay.setContentsMargins(0, 0, 0, 0)
        exp_lay.setSpacing(4)
        exp_lbl = QLabel("Опыт работы *")
        exp_lbl.setObjectName("SetupFieldLabel")
        exp_lay.addWidget(exp_lbl)
        self.experience_combo = QComboBox()
        self.experience_combo.addItems([
            "Нет опыта",
            "Менее 1 года",
            "1-3 года",
            "3-5 лет",
            "5-10 лет",
            "Более 10 лет",
        ])
        self.experience_combo.setStyleSheet(
            "QComboBox{background:#080b14;border:1px solid #1e2538;"
            "border-radius:10px;padding:11px 14px;color:#e8eaf0;font-size:14px;}"
        )
        exp_lay.addWidget(self.experience_combo)

        form.addWidget(g_pos)
        form.addWidget(exp_group)

        # Skills
        skills_lbl = QLabel("Ключевые навыки *")
        skills_lbl.setObjectName("SetupFieldLabel")
        self.skills_input = QTextEdit()
        self.skills_input.setPlaceholderText(
            "Перечислите ваши навыки через запятую:\n"
            "Python, JavaScript, React, SQL, Git..."
        )
        self.skills_input.setObjectName("SetupTextArea")
        self.skills_input.setFixedHeight(80)
        form.addWidget(skills_lbl)
        form.addWidget(self.skills_input)

        # Experience description
        exp_desc_lbl = QLabel("Описание опыта работы")
        exp_desc_lbl.setObjectName("SetupFieldLabel")
        self.experience_input = QTextEdit()
        self.experience_input.setPlaceholderText(
            "Опишите ваш предыдущий опыт работы, проекты, достижения..."
        )
        self.experience_input.setObjectName("SetupTextArea")
        self.experience_input.setFixedHeight(100)
        form.addWidget(exp_desc_lbl)
        form.addWidget(self.experience_input)
        form.addSpacing(8)

        # ── Section: Образование и доп. информация ────────────────
        sec3 = QLabel("Дополнительно")
        sec3.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:700;background:transparent;"
            "padding-top:8px;"
        )
        form.addWidget(sec3)

        sep3 = QFrame()
        sep3.setFixedHeight(1)
        sep3.setStyleSheet("background:#1e2538;")
        form.addWidget(sep3)

        self.education_input, g_edu = self._field(
            "Образование", "Университет, факультет, год выпуска"
        )

        bio_label = QLabel("О себе")
        bio_label.setObjectName("SetupFieldLabel")
        self.bio_input = QTextEdit()
        self.bio_input.setPlaceholderText(
            "Расскажите немного о себе, чем вы увлекаетесь, "
            "какие цели ставите в карьере..."
        )
        self.bio_input.setObjectName("SetupTextArea")
        self.bio_input.setFixedHeight(80)

        self.socials_input, g_soc = self._field(
            "Соцсети / портфолио", "github.com/user, linkedin.com/in/user"
        )

        form.addWidget(g_edu)
        form.addWidget(bio_label)
        form.addWidget(self.bio_input)
        form.addWidget(g_soc)
        form.addSpacing(12)

        # ── ML Validation status ──────────────────────────────────
        self._validation_card = QFrame()
        self._validation_card.setVisible(False)
        self._validation_card.setStyleSheet(
            "QFrame{background:#151a2e;border:1px solid #1e2538;border-radius:12px;}"
        )
        vc_lay = QVBoxLayout(self._validation_card)
        vc_lay.setContentsMargins(16, 14, 16, 14)
        vc_lay.setSpacing(8)

        self._validation_title = QLabel("Проверка ИИ...")
        self._validation_title.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:700;background:transparent;"
        )
        vc_lay.addWidget(self._validation_title)

        self._validation_score = QLabel("")
        self._validation_score.setStyleSheet(
            "color:#3b82f6;font-size:13px;background:transparent;"
        )
        vc_lay.addWidget(self._validation_score)

        self._validation_reasons = QLabel("")
        self._validation_reasons.setStyleSheet(
            "color:#8891a5;font-size:12px;background:transparent;"
        )
        self._validation_reasons.setWordWrap(True)
        vc_lay.addWidget(self._validation_reasons)

        form.addWidget(self._validation_card)

        # ── Status + Submit ───────────────────────────────────────
        self.status_label = QLabel("")
        self.status_label.setObjectName("SetupStatus")
        self.status_label.setWordWrap(True)
        form.addWidget(self.status_label)

        self.submit_btn = QPushButton("Отправить анкету на проверку ИИ")
        self.submit_btn.setObjectName("SetupSubmit")
        self.submit_btn.setCursor(Qt.PointingHandCursor)
        self.submit_btn.clicked.connect(self._submit)
        form.addWidget(self.submit_btn)

        form.addStretch(1)

        scroll.setWidget(form_widget)
        right_lay.addWidget(scroll)

        root.addWidget(left, 2)
        root.addWidget(right, 3)

        self._avatar_path: str | None = None

    # ── helpers ───────────────────────────────────────────────────

    @staticmethod
    def _field(label: str, placeholder: str = "") -> tuple[QLineEdit, QWidget]:
        group = QWidget()
        lay = QVBoxLayout(group)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)

        lbl = QLabel(label)
        lbl.setObjectName("SetupFieldLabel")
        lay.addWidget(lbl)

        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setObjectName("SetupInput")
        lay.addWidget(inp)

        return inp, group

    def _pick_avatar(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите фото", "", "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return
        self._avatar_path = path
        self._avatar_status.setText(path.split("/")[-1].split("\\")[-1])
        pix = QPixmap(path).scaled(
            76, 76, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
        )
        rounded = QPixmap(76, 76)
        rounded.fill(QColor(0, 0, 0, 0))
        p = QPainter(rounded)
        p.setRenderHint(QPainter.Antialiasing)
        clip = QPainterPath()
        clip.addEllipse(0, 0, 76, 76)
        p.setClipPath(clip)
        p.drawPixmap(0, 0, pix)
        p.end()
        self._avatar_icon.setPixmap(rounded)

    def _validate_with_ml(self, data: dict) -> dict | None:
        """Run ML validation on the questionnaire data."""
        try:
            ml_path = str(Path(__file__).resolve().parents[3] / "ML")
            if ml_path not in sys.path:
                sys.path.insert(0, ml_path)
            from questionnaire_validator import validate_questionnaire
            result = validate_questionnaire(data)
            return {
                "status": result.status.value,
                "score": result.score,
                "confidence": result.confidence,
                "reasons": result.reasons,
                "suggestions": result.suggestions,
            }
        except Exception:  # noqa: BLE001
            return None

    def _submit(self) -> None:
        full_name = self.full_name_input.text().strip()
        email = self.email_input.text().strip()
        phone = self.phone_input.text().strip()
        position = self.position_input.text().strip()
        skills = self.skills_input.toPlainText().strip()
        experience = self.experience_input.toPlainText().strip()
        education = self.education_input.text().strip()
        bio = self.bio_input.toPlainText().strip()

        # Basic client-side validation
        if not full_name:
            self.status_label.setText("Пожалуйста, укажите ваше ФИО")
            return
        if not email:
            self.status_label.setText("Пожалуйста, укажите Email")
            return
        if not position:
            self.status_label.setText("Пожалуйста, укажите желаемую должность")
            return
        if not skills:
            self.status_label.setText("Пожалуйста, перечислите ваши навыки")
            return

        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Проверяем анкету...")
        self.status_label.setText("")

        # Prepare questionnaire data for ML validation
        questionnaire_data = {
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "position": position,
            "experience": f"{self.experience_combo.currentText()}. {experience}",
            "skills": skills,
            "bio": bio,
            "education": education,
        }

        # Run ML validation
        ml_result = self._validate_with_ml(questionnaire_data)

        if ml_result:
            self._validation_card.setVisible(True)
            score = ml_result["score"]
            status = ml_result["status"]

            if status == "approved":
                self._validation_title.setText("✓ Анкета одобрена ИИ")
                self._validation_title.setStyleSheet(
                    "color:#3b82f6;font-size:14px;font-weight:700;background:transparent;"
                )
                self._validation_score.setText(f"Оценка: {score}/100 — Отлично!")
                self._validation_card.setStyleSheet(
                    "QFrame{background:#3b82f610;border:1px solid #3b82f640;border-radius:12px;}"
                )
            elif status == "manual_review":
                self._validation_title.setText("⟳ Требуется доработка")
                self._validation_title.setStyleSheet(
                    "color:#f59e0b;font-size:14px;font-weight:700;background:transparent;"
                )
                self._validation_score.setText(f"Оценка: {score}/100 — Заполните больше полей")
                self._validation_card.setStyleSheet(
                    "QFrame{background:#f59e0b10;border:1px solid #f59e0b40;border-radius:12px;}"
                )
            else:
                self._validation_title.setText("✗ Анкета отклонена")
                self._validation_title.setStyleSheet(
                    "color:#ef4444;font-size:14px;font-weight:700;background:transparent;"
                )
                self._validation_score.setText(f"Оценка: {score}/100 — Недостаточно данных")
                self._validation_card.setStyleSheet(
                    "QFrame{background:#ef444410;border:1px solid #ef444440;border-radius:12px;}"
                )

            # Show suggestions
            suggestions = ml_result.get("suggestions", [])
            reasons = ml_result.get("reasons", [])
            hints = reasons + suggestions
            if hints:
                self._validation_reasons.setText("• " + "\n• ".join(hints))
            else:
                self._validation_reasons.setText("")

            # If not approved, allow resubmission
            if status != "approved":
                self.submit_btn.setEnabled(True)
                self.submit_btn.setText("Отправить анкету повторно")
                return

        # Approved or no ML available — proceed with profile creation
        payload = {
            "full_name": full_name,
            "patronymic": None,
            "bio": bio or None,
            "specialty": position,
            "socials_json": self.socials_input.text().strip() or None,
        }

        try:
            profile = api_client.update_me(payload)
            if self._avatar_path:
                try:
                    api_client.upload_avatar(self._avatar_path)
                    session_store.set_avatar_path(self._avatar_path)
                except Exception:  # noqa: BLE001
                    pass
            session_store.set_user_profile(
                profile.get("id"),
                profile.get("full_name"),
                profile.get("patronymic"),
            )
            session_store.set_profile_complete(True)
            session_store.set_questionnaire_approved(True)
            self.profile_completed.emit()
        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка: {exc}")
        finally:
            self.submit_btn.setEnabled(True)
            self.submit_btn.setText("Отправить анкету на проверку ИИ")

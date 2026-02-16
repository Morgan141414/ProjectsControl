"""Join organization screen for members to find and join their company.

Shown after profile setup for users with 'member' role who haven't joined an org yet.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class JoinOrgScreen(QWidget):
    """Onboarding screen for members to search and join organizations."""

    join_completed = Signal()

    def __init__(self) -> None:
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── LEFT: branded info panel ──────────────────────────────
        left = QFrame()
        left.setObjectName("JoinOrgHero")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(48, 56, 48, 48)
        left_lay.setSpacing(20)

        # Icon
        icon_lbl = QLabel("🏢")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(72, 72)
        icon_lbl.setStyleSheet(
            "font-size:36px;color:#4f8fff;background:#151a2e;border-radius:36px;"
        )
        left_lay.addWidget(icon_lbl)

        # Title
        title = QLabel("Найдите свою\nорганизацию")
        title.setObjectName("JoinOrgHeroTitle")
        title.setWordWrap(True)
        left_lay.addWidget(title)

        # Subtitle
        subtitle = QLabel(
            "Введите код приглашения от администратора\n"
            "или найдите компанию по названию,\n"
            "чтобы отправить запрос на вступление."
        )
        subtitle.setObjectName("JoinOrgHeroSub")
        subtitle.setWordWrap(True)
        left_lay.addWidget(subtitle)

        left_lay.addStretch(1)

        # Footer
        footer = QLabel("Шаг 4 из 4 — Присоединение к команде")
        footer.setObjectName("JoinOrgHeroFooter")
        left_lay.addWidget(footer)

        # ── RIGHT: search and join form ───────────────────────────
        right = QFrame()
        right.setObjectName("JoinOrgRight")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(48, 48, 48, 48)
        right_lay.setSpacing(16)

        form_title = QLabel("Присоединиться к команде")
        form_title.setObjectName("JoinOrgFormTitle")
        right_lay.addWidget(form_title)

        form_sub = QLabel(
            "Введите код приглашения или название компании для поиска"
        )
        form_sub.setObjectName("JoinOrgFormSub")
        form_sub.setWordWrap(True)
        right_lay.addWidget(form_sub)

        right_lay.addSpacing(8)

        # Search card
        search_card = QFrame()
        search_card.setObjectName("JoinOrgCard")
        card_lay = QVBoxLayout(search_card)
        card_lay.setContentsMargins(24, 20, 24, 20)
        card_lay.setSpacing(14)

        # Input field
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Код приглашения или название...")
        self.search_input.setFixedHeight(44)
        self.search_input.setStyleSheet(
            "QLineEdit{background:#0c1021;color:#e8eaf0;font-size:14px;"
            "border:1px solid #2a3150;border-radius:10px;padding:0 14px;}"
            "QLineEdit:focus{border-color:#4f8fff;}"
        )
        self.search_input.returnPressed.connect(self._search_or_join)
        card_lay.addWidget(self.search_input)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.search_btn = QPushButton("Найти и отправить запрос")
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.setFixedHeight(44)
        self.search_btn.setStyleSheet(
            "QPushButton{background:#4f8fff;color:#0c1021;font-size:14px;"
            "font-weight:600;border:none;border-radius:10px;padding:0 24px;}"
            "QPushButton:hover{background:#6ba3ff;}"
            "QPushButton:disabled{background:#2a3150;color:#4a5068;}"
        )
        self.search_btn.clicked.connect(self._search_or_join)
        btn_row.addWidget(self.search_btn, 1)

        card_lay.addLayout(btn_row)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setObjectName("JoinOrgStatus")
        self.status_label.setWordWrap(True)
        card_lay.addWidget(self.status_label)

        right_lay.addWidget(search_card)

        # Info text
        info = QLabel(
            "После отправки запроса администратор организации должен его одобрить. "
            "Вы получите уведомление когда вас примут в команду."
        )
        info.setObjectName("JoinOrgInfo")
        info.setWordWrap(True)
        right_lay.addWidget(info)

        right_lay.addStretch(1)

        root.addWidget(left, 2)
        root.addWidget(right, 3)

    def _search_or_join(self) -> None:
        """Search for organization by name or join by code."""
        query = self.search_input.text().strip()
        if not query:
            self.status_label.setText("Введите код или название компании")
            self.status_label.setStyleSheet("color:#ff6b6b;font-size:13px;")
            return

        self.search_btn.setEnabled(False)
        self.status_label.setText("Отправляем запрос...")
        self.status_label.setStyleSheet("color:#8891a5;font-size:13px;")

        try:
            join_code = query

            # If query doesn't look like invite code, search by name first
            if not (4 <= len(query) <= 16 and query.replace("-", "").isalnum()):
                matches = api_client.search_orgs(query)
                if not matches:
                    self.status_label.setText(
                        "Организация не найдена. Проверьте название или попросите "
                        "код приглашения у администратора."
                    )
                    self.status_label.setStyleSheet("color:#ff6b6b;font-size:13px;")
                    return
                join_code = matches[0].get("join_code", query)

            # Send join request
            resp = api_client.join_org(join_code)
            org_id = resp.get("org_id")
            status = resp.get("status", "pending")

            if status == "approved":
                # Immediately approved - set org and advance
                session_store.set_org_id(org_id)
                self.status_label.setText("Вы вступили в организацию!")
                self.status_label.setStyleSheet("color:#3b82f6;font-size:13px;")
                self.join_completed.emit()
            else:
                # Pending approval
                self.status_label.setText(
                    f"Запрос отправлен (статус: {status}). "
                    "Ожидайте подтверждения администратора. "
                    "Вы получите уведомление когда вас примут."
                )
                self.status_label.setStyleSheet("color:#4f8fff;font-size:13px;")

        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
            self.status_label.setStyleSheet("color:#ff6b6b;font-size:13px;")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Неизвестная ошибка: {exc}")
            self.status_label.setStyleSheet("color:#ff6b6b;font-size:13px;")
        finally:
            self.search_btn.setEnabled(True)

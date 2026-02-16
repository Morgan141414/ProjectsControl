"""Full-screen consent banner shown after login.

Explains AI monitoring, data collection policies and gets user agreement
before they can proceed to use the application.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class ConsentBannerScreen(QWidget):
    """Professional consent/agreement screen with branded left panel."""

    consent_accepted = Signal()
    consent_declined = Signal()

    def __init__(self) -> None:
        super().__init__()
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── LEFT: branded info panel ──────────────────────────────
        left = QFrame()
        left.setObjectName("ConsentHero")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(48, 56, 48, 48)
        left_lay.setSpacing(20)

        icon_lbl = QLabel("AI")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFixedSize(72, 72)
        icon_lbl.setStyleSheet(
            "font-size:22px;font-weight:800;color:#4f8fff;background:#151a2e;border-radius:36px;"
        )
        left_lay.addWidget(icon_lbl)

        title = QLabel("Ваша безопасность\nнаш приоритет")
        title.setObjectName("ConsentHeroTitle")
        title.setWordWrap(True)
        left_lay.addWidget(title)

        subtitle = QLabel(
            "ProjectsControl использует ИИ для мониторинга вашей активности.\n"
            "Вся информация доступна вашему работодателю.\n"
            "Пожалуйста, ознакомьтесь с условиями."
        )
        subtitle.setObjectName("ConsentHeroSub")
        subtitle.setWordWrap(True)
        left_lay.addWidget(subtitle)

        left_lay.addStretch(1)

        # ── RIGHT: scrollable agreement ───────────────────────────
        right = QFrame()
        right.setObjectName("ConsentRight")
        right_outer = QVBoxLayout(right)
        right_outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("ConsentScroll")

        inner = QWidget()
        inner.setObjectName("ConsentRight")
        form = QVBoxLayout(inner)
        form.setContentsMargins(48, 48, 48, 48)
        form.setSpacing(16)

        form_title = QLabel("Пользовательское соглашение")
        form_title.setObjectName("ConsentFormTitle")
        form.addWidget(form_title)

        form_sub = QLabel(
            "Пожалуйста, ознакомьтесь с условиями использования системы мониторинга"
        )
        form_sub.setObjectName("ConsentFormSub")
        form_sub.setWordWrap(True)
        form.addWidget(form_sub)
        form.addSpacing(8)

        # ── Agreement sections ────────────────────────────────────
        sections = [
            (
                "Что мы собираем",
                "Активность мыши и клавиатуры (частота, без содержания ввода)\n"
                "Время работы в приложениях и на сайтах (по категориям)\n"
                "Периоды активности и простоя\n"
                "Снимки экрана во время рабочих сессий\n"
                "Результаты выполнения задач",
            ),
            (
                "Чего мы НЕ делаем",
                "Не читаем личные сообщения и переписки\n"
                "Не записываем пароли и финансовые данные\n"
                "Не отслеживаем активность вне рабочего времени\n"
                "Не передаём данные третьим лицам\n"
                "Не используем данные для увольнения сотрудников",
            ),
            (
                "Искусственный интеллект",
                "AI анализирует общие паттерны продуктивности\n"
                "Формирует KPI на основе выполненных задач\n"
                "Предлагает рекомендации по улучшению рабочего процесса\n"
                "Все решения принимаются людьми, не алгоритмами\n"
                "Ваш работодатель имеет полный доступ к собранным данным",
            ),
            (
                "Ваши права",
                "Вы можете запросить выгрузку всех ваших данных\n"
                "Вы можете отозвать согласие в любой момент\n"
                "Вы можете запросить удаление данных\n"
                "Данные хранятся в зашифрованном виде",
            ),
        ]

        for heading, body_text in sections:
            card = QFrame()
            card.setObjectName("ConsentCard")
            card_lay = QVBoxLayout(card)
            card_lay.setContentsMargins(20, 16, 20, 16)
            card_lay.setSpacing(8)

            h = QLabel(heading)
            h.setObjectName("ConsentCardTitle")
            card_lay.addWidget(h)

            b = QLabel(body_text)
            b.setObjectName("ConsentCardBody")
            b.setWordWrap(True)
            card_lay.addWidget(b)

            form.addWidget(card)

        form.addSpacing(16)

        # ── Disclaimer ────────────────────────────────────────────
        disclaimer = QLabel(
            "Нажимая «Принимаю», вы подтверждаете согласие на мониторинг "
            "вашей активности с помощью ИИ. Создатели приложения не несут "
            "ответственности за использование собранных данных "
            "администраторами организации."
        )
        disclaimer.setObjectName("ConsentDisclaimer")
        disclaimer.setWordWrap(True)
        form.addWidget(disclaimer)
        form.addSpacing(8)

        # ── Buttons ───────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.decline_btn = QPushButton("Отклонить")
        self.decline_btn.setObjectName("ConsentDecline")
        self.decline_btn.setCursor(Qt.PointingHandCursor)
        self.decline_btn.clicked.connect(self.consent_declined.emit)

        self.accept_btn = QPushButton("Принимаю условия")
        self.accept_btn.setObjectName("ConsentAccept")
        self.accept_btn.setCursor(Qt.PointingHandCursor)
        self.accept_btn.clicked.connect(self.consent_accepted.emit)

        btn_row.addWidget(self.decline_btn)
        btn_row.addWidget(self.accept_btn, 1)
        form.addLayout(btn_row)

        form.addStretch(1)

        scroll.setWidget(inner)
        right_outer.addWidget(scroll)

        root.addWidget(left, 2)
        root.addWidget(right, 3)

"""Redesigned Dashboard – role-based, clean layout.

Admin:  greeting → create/manage organization → team overview
Member: greeting → join organization → today's tasks → daily report
"""

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


# ═══════════════════════════════════════════════════════════════════════
#  Helper card builders
# ═══════════════════════════════════════════════════════════════════════


def _card(object_name: str = "DashCard") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setObjectName(object_name)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(10)
    return frame, lay


# ═══════════════════════════════════════════════════════════════════════
#  DashboardScreen
# ═══════════════════════════════════════════════════════════════════════


class DashboardScreen(QWidget):
    start_work = Signal()
    org_changed = Signal()

    def __init__(self) -> None:
        super().__init__()

        # Outer scroll area for the whole dashboard
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("DashScroll")

        self._inner = QWidget()
        self._inner.setObjectName("DashInner")
        self._root = QVBoxLayout(self._inner)
        self._root.setContentsMargins(32, 32, 32, 32)
        self._root.setSpacing(24)

        scroll.setWidget(self._inner)
        outer.addWidget(scroll)

        # ── Greeting ──────────────────────────────────────────────
        self.greeting_label = QLabel("")
        self.greeting_label.setObjectName("DashGreeting")
        self.subtitle_label = QLabel("Ваш рабочий кабинет")
        self.subtitle_label.setObjectName("DashSub")

        self._root.addWidget(self.greeting_label)
        self._root.addWidget(self.subtitle_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("DashStatus")
        self._root.addWidget(self.status_label)

        # ── Columns ───────────────────────────────────────────────
        cols = QHBoxLayout()
        cols.setSpacing(24)

        # LEFT column
        self._left = QVBoxLayout()
        self._left.setSpacing(20)

        # RIGHT column
        self._right = QVBoxLayout()
        self._right.setSpacing(20)

        cols.addLayout(self._left, 3)
        cols.addLayout(self._right, 2)
        self._root.addLayout(cols)

        # ══════════════════════════════════════════════════════════
        #  ADMIN section — create / manage org
        # ══════════════════════════════════════════════════════════
        self.admin_section = QWidget()
        admin_lay = QVBoxLayout(self.admin_section)
        admin_lay.setContentsMargins(0, 0, 0, 0)
        admin_lay.setSpacing(20)

        # Create org card
        create_card, cl = _card()
        create_title = QLabel("🏢  Создать организацию")
        create_title.setObjectName("DashSectionTitle")
        create_text = QLabel(
            "Создайте компанию и пригласите свою команду. Вы сможете\n"
            "управлять проектами, назначать задачи и отслеживать результаты."
        )
        create_text.setObjectName("DashMuted")
        create_text.setWordWrap(True)
        self.org_name_input = QLineEdit()
        self.org_name_input.setPlaceholderText("Название организации")
        self.org_name_input.setObjectName("DashInput")
        self.create_org_btn = QPushButton("Создать  →")
        self.create_org_btn.setObjectName("DashPrimary")
        self.create_org_btn.setCursor(Qt.PointingHandCursor)
        self.create_org_btn.clicked.connect(self._create_org)
        cl.addWidget(create_title)
        cl.addWidget(create_text)
        cl.addWidget(self.org_name_input)
        cl.addWidget(self.create_org_btn)
        admin_lay.addWidget(create_card)

        # Join requests card (admin)
        requests_card, rl = _card()
        req_title = QLabel("📋  Заявки на вступление")
        req_title.setObjectName("DashSectionTitle")
        self.requests_list = QListWidget()
        self.requests_list.setObjectName("DashList")
        self.requests_status = QLabel("Нет новых заявок")
        self.requests_status.setObjectName("DashMuted")
        self.refresh_requests_btn = QPushButton("Обновить")
        self.refresh_requests_btn.setObjectName("DashSecondary")
        self.refresh_requests_btn.clicked.connect(self._load_requests)
        rl.addWidget(req_title)
        rl.addWidget(self.requests_status)
        rl.addWidget(self.requests_list)
        rl.addWidget(self.refresh_requests_btn)
        admin_lay.addWidget(requests_card)

        self._left.addWidget(self.admin_section)

        # ══════════════════════════════════════════════════════════
        #  MEMBER section — join org
        # ══════════════════════════════════════════════════════════
        self.member_section = QWidget()
        member_lay = QVBoxLayout(self.member_section)
        member_lay.setContentsMargins(0, 0, 0, 0)
        member_lay.setSpacing(20)

        # Welcome card
        welcome_card, wl = _card()
        welcome_icon = QLabel("👋")
        welcome_icon.setStyleSheet("font-size: 36px; background: transparent;")
        welcome_title = QLabel("Добро пожаловать!")
        welcome_title.setObjectName("DashSectionTitle")
        welcome_text = QLabel(
            "Вступите в организацию, чтобы получить доступ к проектам,\n"
            "задачам и аналитике. Используйте код компании или ожидайте\n"
            "приглашение от администратора."
        )
        welcome_text.setObjectName("DashMuted")
        welcome_text.setWordWrap(True)
        wl.addWidget(welcome_icon)
        wl.addWidget(welcome_title)
        wl.addWidget(welcome_text)
        member_lay.addWidget(welcome_card)

        # Join card
        join_card, jl = _card()
        join_title = QLabel("🔗  Вступить в компанию")
        join_title.setObjectName("DashSectionTitle")
        join_note = QLabel("Введите код организации и отправьте запрос")
        join_note.setObjectName("DashMuted")
        join_note.setWordWrap(True)
        self.join_code_input = QLineEdit()
        self.join_code_input.setPlaceholderText("Код компании")
        self.join_code_input.setObjectName("DashInput")
        self.join_btn = QPushButton("Отправить запрос")
        self.join_btn.setObjectName("DashSecondary")
        self.join_btn.setCursor(Qt.PointingHandCursor)
        self.join_btn.clicked.connect(self._join_org)
        jl.addWidget(join_title)
        jl.addWidget(join_note)
        jl.addWidget(self.join_code_input)
        jl.addWidget(self.join_btn)
        member_lay.addWidget(join_card)

        self._left.addWidget(self.member_section)

        # ══════════════════════════════════════════════════════════
        #  RIGHT column — tasks + report (visible for everyone)
        # ══════════════════════════════════════════════════════════

        # Tasks card
        tasks_card, tl = _card()
        tasks_title = QLabel("📌  Дела на сегодня")
        tasks_title.setObjectName("DashSectionTitle")
        self.tasks_status_label = QLabel("Пока нет задач")
        self.tasks_status_label.setObjectName("DashMuted")
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("DashList")
        self.start_button = QPushButton("Начать работу")
        self.start_button.setObjectName("DashPrimary")
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.start_work.emit)
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("DashSecondary")
        self.refresh_button.clicked.connect(self.refresh_tasks)
        tl.addWidget(tasks_title)
        tl.addWidget(self.tasks_status_label)
        tl.addWidget(self.list_widget)
        tl.addWidget(self.start_button)
        tl.addWidget(self.refresh_button)
        self._right.addWidget(tasks_card)

        # Report card
        report_card, rpl = _card()
        report_title = QLabel("📝  Ежедневный отчёт")
        report_title.setObjectName("DashSectionTitle")
        report_note = QLabel("Опишите, что сделано сегодня по проекту")
        report_note.setObjectName("DashMuted")
        self.report_project = QComboBox()
        self.report_project.setPlaceholderText("Проект")
        self.report_project.setObjectName("DashCombo")
        self.report_text = QTextEdit()
        self.report_text.setPlaceholderText("Короткое описание результата...")
        self.report_text.setFixedHeight(90)
        self.report_text.setObjectName("DashTextArea")
        self.report_submit = QPushButton("Отправить")
        self.report_submit.setObjectName("DashSecondary")
        self.report_submit.clicked.connect(self._submit_report)
        rpl.addWidget(report_title)
        rpl.addWidget(report_note)
        rpl.addWidget(self.report_project)
        rpl.addWidget(self.report_text)
        rpl.addWidget(self.report_submit)
        self._right.addWidget(report_card)

        # Spacers
        self._left.addStretch(1)
        self._right.addStretch(1)
        self._root.addStretch(1)

    # ══════════════════════════════════════════════════════════════
    #  Public API
    # ══════════════════════════════════════════════════════════════

    def refresh_tasks(self) -> None:
        """Called every time the dashboard becomes visible."""
        self._update_greeting()
        self._apply_role_visibility()
        self._load_projects()
        self._load_tasks()

    # ══════════════════════════════════════════════════════════════
    #  Private helpers
    # ══════════════════════════════════════════════════════════════

    def _update_greeting(self) -> None:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greeting = "Доброе утро"
        elif 12 <= hour < 18:
            greeting = "Добрый день"
        elif 18 <= hour < 23:
            greeting = "Добрый вечер"
        else:
            greeting = "Доброй ночи"
        name = session_store.full_name or ""
        patronymic = session_store.patronymic or ""
        display_name = " ".join(p for p in (name, patronymic) if p)
        if display_name:
            self.greeting_label.setText(f"{greeting}, {display_name}")
        else:
            self.greeting_label.setText(greeting)

    def _apply_role_visibility(self) -> None:
        is_admin = session_store.role == "admin"
        self.admin_section.setVisible(is_admin)
        self.member_section.setVisible(not is_admin)

    def _load_tasks(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            self.tasks_status_label.setText("Вы ещё не в организации")
            return
        self.refresh_button.setEnabled(False)
        self.list_widget.clear()
        try:
            tasks = api_client.list_today_tasks(org_id)
            if not tasks:
                self.tasks_status_label.setText("Нет задач на сегодня")
                return
            self.tasks_status_label.setText(f"Задач: {len(tasks)}")
            for task in tasks:
                item = QListWidgetItem(f"{task['title']}  ·  {task['status']}")
                item.setData(Qt.UserRole, task)
                self.list_widget.addItem(item)
        except ApiError as exc:
            self.tasks_status_label.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.tasks_status_label.setText(f"Ошибка: {exc}")
        finally:
            self.refresh_button.setEnabled(True)

    def _load_projects(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            return
        try:
            projects = api_client.list_projects(org_id)
        except ApiError:
            return
        self.report_project.clear()
        for project in projects:
            self.report_project.addItem(project.get("name", "Проект"), project.get("id"))

    def _load_requests(self) -> None:
        """Admin: load join requests."""
        org_id = session_store.org_id
        if not org_id:
            self.requests_status.setText("Сначала создайте организацию")
            return
        self.refresh_requests_btn.setEnabled(False)
        self.requests_list.clear()
        try:
            requests = api_client.list_join_requests(org_id)
            if not requests:
                self.requests_status.setText("Нет новых заявок")
                return
            self.requests_status.setText(f"Заявок: {len(requests)}")
            for req in requests:
                user_name = req.get("user_full_name") or req.get("user_email", "—")
                item = QListWidgetItem(f"{user_name}  ·  {req.get('status', '?')}")
                item.setData(Qt.UserRole, req)
                self.requests_list.addItem(item)
        except ApiError as exc:
            self.requests_status.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.requests_status.setText(f"Ошибка: {exc}")
        finally:
            self.refresh_requests_btn.setEnabled(True)

    def _create_org(self) -> None:
        name = self.org_name_input.text().strip()
        if not name:
            self.status_label.setText("Введите название организации")
            return
        self.create_org_btn.setEnabled(False)
        try:
            org = api_client.create_org(name)
            session_store.set_org_id(org.get("id"))
            self.org_changed.emit()
            self.status_label.setText("✓ Организация создана")
            self._load_requests()
        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка: {exc}")
        finally:
            self.create_org_btn.setEnabled(True)

    def _join_org(self) -> None:
        code = self.join_code_input.text().strip()
        if not code:
            self.status_label.setText("Введите код организации")
            return
        self.join_btn.setEnabled(False)
        try:
            response = api_client.join_org(code)
            session_store.set_org_id(response.get("org_id"))
            self.org_changed.emit()
            status = response.get("status")
            self.status_label.setText(f"Статус: {status}")
            if status == "approved":
                self.refresh_tasks()
        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка: {exc}")
        finally:
            self.join_btn.setEnabled(True)

    def _submit_report(self) -> None:
        org_id = session_store.org_id
        if not org_id:
            self.status_label.setText("Сначала вступите в организацию")
            return
        project_id = self.report_project.currentData()
        if not project_id:
            self.status_label.setText("Выберите проект")
            return
        content = self.report_text.toPlainText().strip()
        if not content:
            self.status_label.setText("Введите текст отчёта")
            return
        self.report_submit.setEnabled(False)
        try:
            api_client.create_daily_report(org_id, project_id, None, content)
            self.status_label.setText("✓ Отчёт сохранён")
            self.report_text.clear()
        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка: {exc}")
        finally:
            self.report_submit.setEnabled(True)

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class DashboardScreen(QWidget):
    start_work = Signal()
    org_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(24)

        left_panel = QFrame()
        left_panel.setObjectName("DashboardMain")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(24, 24, 24, 24)
        left_layout.setSpacing(18)

        self.greeting_label = QLabel("")
        self.greeting_label.setObjectName("DashboardTitle")
        subtitle = QLabel("Ваш личный кабинет")
        subtitle.setObjectName("DashboardSubtitle")

        self.org_prompt_label = QLabel("")
        self.org_prompt_label.setAlignment(Qt.AlignCenter)
        self.org_prompt_label.setObjectName("DashboardSectionTitle")

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        self.profile_card = QFrame()
        self.profile_card.setObjectName("DashboardCard")
        profile_layout = QVBoxLayout(self.profile_card)
        profile_layout.setContentsMargins(20, 18, 20, 18)
        profile_layout.setSpacing(10)

        profile_title = QLabel("Начнем с базовых настроек")
        profile_title.setObjectName("DashboardSectionTitle")
        profile_text = QLabel(
            "Добавьте фото и краткое описание. Это поможет создать личный кабинет и аналитику."
        )
        profile_text.setWordWrap(True)
        profile_text.setObjectName("Muted")

        self.avatar_path: str | None = None
        self.avatar_label = QLabel("Фото не выбрано")
        self.avatar_label.setObjectName("Muted")
        self.avatar_button = QPushButton("Выбрать фото")
        self.avatar_button.setObjectName("SecondaryButton")
        self.avatar_button.clicked.connect(self.pick_avatar)

        self.profile_full_name = QLineEdit()
        self.profile_full_name.setPlaceholderText("ФИО")

        self.profile_patronymic = QLineEdit()
        self.profile_patronymic.setPlaceholderText("Отчество")

        self.profile_bio = QTextEdit()
        self.profile_bio.setPlaceholderText("О себе (по желанию)")
        self.profile_bio.setFixedHeight(80)
        self.profile_bio.setObjectName("DashboardInput")

        self.profile_specialty = QLineEdit()
        self.profile_specialty.setPlaceholderText("Специальность")

        self.profile_socials = QLineEdit()
        self.profile_socials.setPlaceholderText("Ссылки на соцсети (Instagram, GitHub, LinkedIn)")

        role_row = QHBoxLayout()
        self.role_admin = QRadioButton("Я администратор")
        self.role_manager = QRadioButton("Я менеджер")
        self.role_member = QRadioButton("Я специалист")
        self.role_member.setChecked(True)
        for btn in (self.role_admin, self.role_manager, self.role_member):
            btn.setObjectName("DashboardRole")
            role_row.addWidget(btn)
            btn.toggled.connect(self._update_org_prompt)
        role_row.addStretch(1)

        self.save_profile_button = QPushButton("Сохранить профиль")
        self.save_profile_button.clicked.connect(self.save_profile)

        profile_layout.addWidget(profile_title)
        profile_layout.addWidget(profile_text)
        profile_layout.addWidget(self.avatar_label)
        profile_layout.addWidget(self.avatar_button)
        profile_layout.addWidget(self.profile_full_name)
        profile_layout.addWidget(self.profile_patronymic)
        profile_layout.addWidget(self.profile_bio)
        profile_layout.addWidget(self.profile_specialty)
        profile_layout.addWidget(self.profile_socials)
        profile_layout.addLayout(role_row)
        profile_layout.addWidget(self.save_profile_button)

        team_card = QFrame()
        team_card.setObjectName("DashboardCard")
        team_layout = QVBoxLayout(team_card)
        team_layout.setContentsMargins(20, 18, 20, 18)
        team_layout.setSpacing(8)

        team_title = QLabel("Организация и штаб")
        team_title.setObjectName("DashboardSectionTitle")
        team_text = QLabel(
            "Создайте свою организацию или отправьте запрос на вступление. "
            "После подтверждения появится доступ к проектам и задачам."
        )
        team_text.setWordWrap(True)
        team_text.setObjectName("Muted")

        self.org_action_label = QLabel("")
        self.org_action_label.setObjectName("DashboardSectionTitle")

        self.org_name_input = QLineEdit()
        self.org_name_input.setPlaceholderText("Название компании")

        self.create_org_button = QPushButton("Создать компанию")
        self.create_org_button.setObjectName("SecondaryButton")
        self.create_org_button.clicked.connect(self.create_org)

        team_layout.addWidget(team_title)
        team_layout.addWidget(team_text)
        team_layout.addWidget(self.org_action_label)
        team_layout.addWidget(self.org_name_input)
        team_layout.addWidget(self.create_org_button)

        schedule_row = QHBoxLayout()
        self.schedule_start = QLabel("Начало: 09:30")
        self.schedule_end = QLabel("Конец: 18:30")
        for label in (self.schedule_start, self.schedule_end):
            label.setObjectName("DashboardPill")
            schedule_row.addWidget(label)
        schedule_row.addStretch(1)

        team_layout.addLayout(schedule_row)

        kpi_card = QFrame()
        kpi_card.setObjectName("DashboardCard")
        kpi_layout = QVBoxLayout(kpi_card)
        kpi_layout.setContentsMargins(20, 18, 20, 18)
        kpi_layout.setSpacing(8)

        kpi_title = QLabel("Ваш KPI и эффективность")
        kpi_title.setObjectName("DashboardSectionTitle")
        kpi_text = QLabel(
            "Здесь появятся показатели КПД, эффективность по задачам и "
            "рабочий график после первого дня в системе."
        )
        kpi_text.setWordWrap(True)
        kpi_text.setObjectName("Muted")

        kpi_stats = QHBoxLayout()
        self.kpi_score = QLabel("KPI: 72%")
        self.kpi_focus = QLabel("Фокус: 4.2 ч")
        self.kpi_tasks = QLabel("Задач закрыто: 3")
        for label in (self.kpi_score, self.kpi_focus, self.kpi_tasks):
            label.setObjectName("DashboardStat")
            kpi_stats.addWidget(label)
        kpi_stats.addStretch(1)

        kpi_layout.addWidget(kpi_title)
        kpi_layout.addWidget(kpi_text)
        kpi_layout.addLayout(kpi_stats)

        self._update_greeting()

        left_layout.addWidget(self.greeting_label)
        left_layout.addWidget(subtitle)
        left_layout.addWidget(self.org_prompt_label)
        left_layout.addWidget(self.status_label)
        left_layout.addWidget(self.profile_card)
        left_layout.addWidget(team_card)
        left_layout.addWidget(kpi_card)
        left_layout.addStretch(1)

        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(18)

        join_card = QFrame()
        join_card.setObjectName("DashboardSideCard")
        join_layout = QVBoxLayout(join_card)
        join_layout.setContentsMargins(20, 18, 20, 18)
        join_layout.setSpacing(10)

        join_title = QLabel("Вступить в компанию")
        join_title.setObjectName("DashboardSectionTitle")
        join_note = QLabel(
            "Введите код и отправьте запрос. После подтверждения откроется штаб."
        )
        join_note.setWordWrap(True)
        join_note.setObjectName("Muted")

        self.join_code_input = QLineEdit()
        self.join_code_input.setPlaceholderText("Код компании")

        self.join_button = QPushButton("Отправить запрос")
        self.join_button.setObjectName("SecondaryButton")
        self.join_button.clicked.connect(self.join_org)

        join_layout.addWidget(join_title)
        join_layout.addWidget(join_note)
        join_layout.addWidget(self.join_code_input)
        join_layout.addWidget(self.join_button)

        report_card = QFrame()
        report_card.setObjectName("DashboardSideCard")
        report_layout = QVBoxLayout(report_card)
        report_layout.setContentsMargins(20, 18, 20, 18)
        report_layout.setSpacing(10)

        report_title = QLabel("Ежедневный отчет")
        report_title.setObjectName("DashboardSectionTitle")
        report_note = QLabel("Опишите, что сделано сегодня по проекту.")
        report_note.setWordWrap(True)
        report_note.setObjectName("Muted")

        self.report_project = QComboBox()
        self.report_project.setPlaceholderText("Проект")

        self.report_text = QTextEdit()
        self.report_text.setPlaceholderText("Короткое описание результата")
        self.report_text.setFixedHeight(90)
        self.report_text.setObjectName("DashboardInput")

        self.report_submit = QPushButton("Отправить отчет")
        self.report_submit.clicked.connect(self.submit_report)

        report_layout.addWidget(report_title)
        report_layout.addWidget(report_note)
        report_layout.addWidget(self.report_project)
        report_layout.addWidget(self.report_text)
        report_layout.addWidget(self.report_submit)

        tasks_card = QFrame()
        tasks_card.setObjectName("DashboardSideCard")
        tasks_layout = QVBoxLayout(tasks_card)
        tasks_layout.setContentsMargins(20, 18, 20, 18)
        tasks_layout.setSpacing(10)

        tasks_title = QLabel("Дела на сегодня")
        tasks_title.setObjectName("DashboardSectionTitle")

        self.tasks_status_label = QLabel("Пока нет задач")
        self.tasks_status_label.setObjectName("Muted")

        self.list_widget = QListWidget()

        self.start_button = QPushButton("Начать работу")
        self.start_button.clicked.connect(self.start_work.emit)

        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setObjectName("SecondaryButton")
        self.refresh_button.clicked.connect(self.refresh_tasks)

        tasks_layout.addWidget(tasks_title)
        tasks_layout.addWidget(self.tasks_status_label)
        tasks_layout.addWidget(self.list_widget)
        tasks_layout.addWidget(self.start_button)
        tasks_layout.addWidget(self.refresh_button)

        right_layout.addWidget(join_card)
        right_layout.addWidget(report_card)
        right_layout.addWidget(tasks_card)
        right_layout.addStretch(1)

        root_layout.addWidget(left_panel, 3)
        root_layout.addWidget(right_panel, 2)

    def refresh_tasks(self) -> None:
        self._update_greeting()
        self._update_org_prompt()
        self._load_profile()
        self._load_projects()
        org_id = session_store.org_id
        if not org_id:
            self.tasks_status_label.setText("Вы еще не в организации")
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
                item = QListWidgetItem(f"{task['title']}  |  {task['status']}")
                item.setData(Qt.UserRole, task)
                self.list_widget.addItem(item)
        except ApiError as exc:
            self.tasks_status_label.setText(f"Не удалось загрузить: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.tasks_status_label.setText(f"Не удалось загрузить: {exc}")
        finally:
            self.refresh_button.setEnabled(True)

    def pick_avatar(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите фото",
            "",
            "Images (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.avatar_path = file_path
            self.avatar_label.setText(file_path)

    def save_profile(self) -> None:
        payload = {
            "full_name": self.profile_full_name.text().strip() or None,
            "patronymic": self.profile_patronymic.text().strip() or None,
            "bio": self.profile_bio.toPlainText().strip() or None,
            "specialty": self.profile_specialty.text().strip() or None,
            "avatar_url": self.avatar_path,
            "socials_json": self.profile_socials.text().strip() or None,
        }
        self.save_profile_button.setEnabled(False)
        try:
            profile = api_client.update_me(payload)
            session_store.set_user_profile(
                profile.get("id"),
                profile.get("full_name"),
                profile.get("patronymic"),
            )
            self.status_label.setText("Профиль сохранен")
            self.profile_card.hide()
            self._update_greeting()
        except ApiError as exc:
            self.status_label.setText(f"Ошибка профиля: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка профиля: {exc}")
        finally:
            self.save_profile_button.setEnabled(True)

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
        display_name = " ".join([part for part in (name, patronymic) if part])
        if display_name:
            self.greeting_label.setText(f"{greeting}, {display_name}")
        else:
            self.greeting_label.setText(greeting)

    def _load_profile(self) -> None:
        try:
            profile = api_client.get_me()
        except ApiError:
            return
        if profile.get("full_name"):
            self.profile_full_name.setText(profile.get("full_name"))
        if profile.get("patronymic"):
            self.profile_patronymic.setText(profile.get("patronymic"))
        if profile.get("bio"):
            self.profile_bio.setText(profile.get("bio"))
        if profile.get("specialty"):
            self.profile_specialty.setText(profile.get("specialty"))
        if profile.get("avatar_url"):
            self.avatar_path = profile.get("avatar_url")
            self.avatar_label.setText(profile.get("avatar_url"))
        if profile.get("socials_json"):
            self.profile_socials.setText(profile.get("socials_json"))

        has_profile = bool(profile.get("full_name"))
        self.profile_card.setVisible(not has_profile)

    def _update_org_prompt(self) -> None:
        if self.role_admin.isChecked():
            self.org_prompt_label.setText("Предлагаем вам создать компанию")
            self.org_action_label.setText("Создайте компанию и пригласите команду")
            self.create_org_button.setVisible(True)
            self.org_name_input.setVisible(True)
        else:
            self.org_prompt_label.setText("Предлагаем вам вступить в компанию")
            self.org_action_label.setText("Ожидайте приглашения или вступите по коду")
            self.create_org_button.setVisible(False)
            self.org_name_input.setVisible(False)

    def create_org(self) -> None:
        name = self.org_name_input.text().strip()
        if not name:
            self.status_label.setText("Введите название компании")
            return
        self.create_org_button.setEnabled(False)
        try:
            org = api_client.create_org(name)
            session_store.set_org_id(org.get("id"))
            self.org_changed.emit()
            self.status_label.setText("Компания создана")
        except ApiError as exc:
            self.status_label.setText(f"Ошибка создания: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка создания: {exc}")
        finally:
            self.create_org_button.setEnabled(True)

    def join_org(self) -> None:
        code = self.join_code_input.text().strip()
        if not code:
            self.status_label.setText("Введите код организации")
            return

        self.join_button.setEnabled(False)
        try:
            response = api_client.join_org(code)
            session_store.set_org_id(response.get("org_id"))
            self.org_changed.emit()
            status = response.get("status")
            self.status_label.setText(f"Статус запроса: {status}")
            if status == "approved":
                self.refresh_tasks()
        except ApiError as exc:
            self.status_label.setText(f"Ошибка запроса: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка запроса: {exc}")
        finally:
            self.join_button.setEnabled(True)

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

    def submit_report(self) -> None:
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
            self.status_label.setText("Введите текст отчета")
            return
        self.report_submit.setEnabled(False)
        try:
            api_client.create_daily_report(org_id, project_id, None, content)
            self.status_label.setText("Отчет сохранен")
            self.report_text.clear()
        except ApiError as exc:
            self.status_label.setText(f"Ошибка отчета: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка отчета: {exc}")
        finally:
            self.report_submit.setEnabled(True)

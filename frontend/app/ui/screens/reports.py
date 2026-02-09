import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class ReportsScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Reports and metrics")
        title.setObjectName("TitleLabel")

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        self.tabs = QTabWidget()

        self.org_kpi_tab = QWidget()
        self.project_kpi_tab = QWidget()
        self.performance_tab = QWidget()
        self.metrics_tab = QWidget()
        self.exports_tab = QWidget()
        self.ai_kpi_tab = QWidget()

        self.tabs.addTab(self.org_kpi_tab, "Org KPI")
        self.tabs.addTab(self.project_kpi_tab, "Project KPI")
        self.tabs.addTab(self.performance_tab, "Performance")
        self.tabs.addTab(self.metrics_tab, "Metrics")
        self.tabs.addTab(self.exports_tab, "Exports")
        self.tabs.addTab(self.ai_kpi_tab, "AI Аналитика")

        self._build_org_kpi()
        self._build_project_kpi()
        self._build_performance()
        self._build_metrics()
        self._build_exports()
        self._build_ai_kpi()

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabs)

    def _require_org(self) -> str | None:
        org_id = session_store.org_id
        if not org_id:
            self.status_label.setText("Join an organization first")
        return org_id

    def _build_org_kpi(self) -> None:
        layout = QVBoxLayout(self.org_kpi_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.org_start_input = QLineEdit()
        self.org_start_input.setPlaceholderText("YYYY-MM-DD")

        self.org_end_input = QLineEdit()
        self.org_end_input.setPlaceholderText("YYYY-MM-DD")

        self.org_team_input = QLineEdit()
        self.org_team_input.setPlaceholderText("Team id")

        self.org_project_input = QLineEdit()
        self.org_project_input.setPlaceholderText("Project id")

        self.org_format_input = QLineEdit("csv")
        self.org_format_input.setPlaceholderText("csv or json")

        self.org_load_button = QPushButton("Load KPI")
        self.org_load_button.clicked.connect(self.load_org_kpi)

        self.org_export_button = QPushButton("Export KPI")
        self.org_export_button.clicked.connect(self.export_org_kpi)

        action_row = QHBoxLayout()
        action_row.addWidget(self.org_load_button)
        action_row.addWidget(self.org_export_button)

        form_layout.addRow("Start date", self.org_start_input)
        form_layout.addRow("End date", self.org_end_input)
        form_layout.addRow("Team id", self.org_team_input)
        form_layout.addRow("Project id", self.org_project_input)
        form_layout.addRow("Export format", self.org_format_input)
        form_layout.addRow(action_row)

        self.org_output = QTextEdit()
        self.org_output.setReadOnly(True)

        layout.addWidget(form)
        layout.addWidget(self.org_output)

    def _build_project_kpi(self) -> None:
        layout = QVBoxLayout(self.project_kpi_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.project_start_input = QLineEdit()
        self.project_start_input.setPlaceholderText("YYYY-MM-DD")

        self.project_end_input = QLineEdit()
        self.project_end_input.setPlaceholderText("YYYY-MM-DD")

        self.project_format_input = QLineEdit("csv")
        self.project_format_input.setPlaceholderText("csv or json")

        self.project_load_button = QPushButton("Load KPI")
        self.project_load_button.clicked.connect(self.load_project_kpi)

        self.project_export_button = QPushButton("Export KPI")
        self.project_export_button.clicked.connect(self.export_project_kpi)

        action_row = QHBoxLayout()
        action_row.addWidget(self.project_load_button)
        action_row.addWidget(self.project_export_button)

        form_layout.addRow("Start date", self.project_start_input)
        form_layout.addRow("End date", self.project_end_input)
        form_layout.addRow("Export format", self.project_format_input)
        form_layout.addRow(action_row)

        self.project_output = QTextEdit()
        self.project_output.setReadOnly(True)

        layout.addWidget(form)
        layout.addWidget(self.project_output)

    def _build_performance(self) -> None:
        layout = QVBoxLayout(self.performance_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.perf_user_input = QLineEdit()
        self.perf_user_input.setPlaceholderText("User id")

        self.perf_team_input = QLineEdit()
        self.perf_team_input.setPlaceholderText("Team id")

        self.perf_project_input = QLineEdit()
        self.perf_project_input.setPlaceholderText("Project id")

        self.perf_start_input = QLineEdit()
        self.perf_start_input.setPlaceholderText("YYYY-MM-DD")

        self.perf_end_input = QLineEdit()
        self.perf_end_input.setPlaceholderText("YYYY-MM-DD")

        self.perf_load_button = QPushButton("Load activity per task")
        self.perf_load_button.clicked.connect(self.load_performance)

        form_layout.addRow("User id", self.perf_user_input)
        form_layout.addRow("Team id", self.perf_team_input)
        form_layout.addRow("Project id", self.perf_project_input)
        form_layout.addRow("Start date", self.perf_start_input)
        form_layout.addRow("End date", self.perf_end_input)
        form_layout.addRow(self.perf_load_button)

        self.perf_output = QTextEdit()
        self.perf_output.setReadOnly(True)

        layout.addWidget(form)
        layout.addWidget(self.perf_output)

    def _build_metrics(self) -> None:
        layout = QVBoxLayout(self.metrics_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.metric_session_input = QLineEdit()
        self.metric_session_input.setPlaceholderText("Session id")

        self.metric_user_input = QLineEdit()
        self.metric_user_input.setPlaceholderText("User id")

        self.metric_project_input = QLineEdit()
        self.metric_project_input.setPlaceholderText("Project id")

        self.metric_start_input = QLineEdit()
        self.metric_start_input.setPlaceholderText("YYYY-MM-DD")

        self.metric_end_input = QLineEdit()
        self.metric_end_input.setPlaceholderText("YYYY-MM-DD")

        self.metric_session_button = QPushButton("Load session metrics")
        self.metric_session_button.clicked.connect(self.load_session_metrics)

        self.metric_user_button = QPushButton("Load user metrics")
        self.metric_user_button.clicked.connect(self.load_user_metrics)

        button_row = QHBoxLayout()
        button_row.addWidget(self.metric_session_button)
        button_row.addWidget(self.metric_user_button)

        form_layout.addRow("Session id", self.metric_session_input)
        form_layout.addRow("User id", self.metric_user_input)
        form_layout.addRow("Project id", self.metric_project_input)
        form_layout.addRow("Start date", self.metric_start_input)
        form_layout.addRow("End date", self.metric_end_input)
        form_layout.addRow(button_row)

        self.metric_output = QTextEdit()
        self.metric_output.setReadOnly(True)

        layout.addWidget(form)
        layout.addWidget(self.metric_output)

    def _build_exports(self) -> None:
        layout = QVBoxLayout(self.exports_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.exports_output = QTextEdit()
        self.exports_output.setReadOnly(True)

        self.exports_refresh_button = QPushButton("Refresh exports")
        self.exports_refresh_button.clicked.connect(self.refresh_exports)

        layout.addWidget(self.exports_output)
        layout.addWidget(self.exports_refresh_button)

    def _build_ai_kpi(self) -> None:
        layout = QVBoxLayout(self.ai_kpi_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        form = QFrame()
        form_layout = QFormLayout(form)
        form_layout.setContentsMargins(0, 0, 0, 0)

        self.ai_day_button = QPushButton("День")
        self.ai_day_button.setCheckable(True)
        self.ai_day_button.setObjectName("AuthToggle")
        self.ai_week_button = QPushButton("Неделя")
        self.ai_week_button.setCheckable(True)
        self.ai_week_button.setObjectName("AuthToggle")
        self.ai_day_button.setChecked(True)

        period_group = QButtonGroup(self)
        period_group.setExclusive(True)
        period_group.addButton(self.ai_day_button)
        period_group.addButton(self.ai_week_button)

        period_row = QHBoxLayout()
        period_row.addWidget(self.ai_day_button)
        period_row.addWidget(self.ai_week_button)
        period_row.addStretch(1)

        self.ai_mode_employee = QPushButton("Сотрудник")
        self.ai_mode_employee.setCheckable(True)
        self.ai_mode_employee.setObjectName("AuthToggle")
        self.ai_mode_manager = QPushButton("Руководитель")
        self.ai_mode_manager.setCheckable(True)
        self.ai_mode_manager.setObjectName("AuthToggle")
        self.ai_mode_employee.setChecked(True)

        mode_group = QButtonGroup(self)
        mode_group.setExclusive(True)
        mode_group.addButton(self.ai_mode_employee)
        mode_group.addButton(self.ai_mode_manager)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self.ai_mode_employee)
        mode_row.addWidget(self.ai_mode_manager)
        mode_row.addStretch(1)

        self.ai_profile_dev = QPushButton("Разработчик")
        self.ai_profile_dev.setCheckable(True)
        self.ai_profile_dev.setObjectName("AuthToggle")
        self.ai_profile_pm = QPushButton("Менеджер")
        self.ai_profile_pm.setCheckable(True)
        self.ai_profile_pm.setObjectName("AuthToggle")
        self.ai_profile_office = QPushButton("Офис")
        self.ai_profile_office.setCheckable(True)
        self.ai_profile_office.setObjectName("AuthToggle")
        self.ai_profile_dev.setChecked(True)

        profile_group = QButtonGroup(self)
        profile_group.setExclusive(True)
        profile_group.addButton(self.ai_profile_dev)
        profile_group.addButton(self.ai_profile_pm)
        profile_group.addButton(self.ai_profile_office)

        profile_row = QHBoxLayout()
        profile_row.addWidget(self.ai_profile_dev)
        profile_row.addWidget(self.ai_profile_pm)
        profile_row.addWidget(self.ai_profile_office)
        profile_row.addStretch(1)

        self.ai_asof_input = QLineEdit()
        self.ai_asof_input.setPlaceholderText("YYYY-MM-DD (по умолчанию сегодня)")

        self.ai_user_input = QLineEdit()
        self.ai_user_input.setPlaceholderText("User id (опционально)")

        self.ai_load_button = QPushButton("Показать аналитику")
        self.ai_load_button.clicked.connect(self.load_ai_kpi)

        form_layout.addRow("Период", period_row)
        form_layout.addRow("Режим", mode_row)
        form_layout.addRow("Профиль", profile_row)
        form_layout.addRow("Дата", self.ai_asof_input)
        form_layout.addRow("Сотрудник", self.ai_user_input)
        form_layout.addRow(self.ai_load_button)

        header_card = QFrame()
        header_card.setObjectName("AiCard")
        header_layout = QHBoxLayout(header_card)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        self.ai_user_label = QLabel("Сотрудник: --")
        self.ai_user_label.setObjectName("AiTitle")
        self.ai_period_label = QLabel("Период: --")
        self.ai_period_label.setObjectName("AiStat")
        self.ai_hint_label = QLabel("")
        self.ai_hint_label.setObjectName("AiStat")

        header_layout.addWidget(self.ai_user_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.ai_period_label)
        header_layout.addWidget(self.ai_hint_label)

        score_card = QFrame()
        score_card.setObjectName("AiCard")
        score_layout = QHBoxLayout(score_card)
        score_layout.setContentsMargins(16, 12, 16, 12)
        score_layout.setSpacing(12)

        self.ai_score_label = QLabel("Score: --")
        self.ai_score_label.setObjectName("AiScore")
        self.ai_baseline_label = QLabel("Норма: --")
        self.ai_baseline_label.setObjectName("AiBadge")
        self.ai_delta_label = QLabel("Δ: --")
        self.ai_delta_label.setObjectName("AiBadge")

        score_layout.addWidget(self.ai_score_label)
        score_layout.addStretch(1)
        score_layout.addWidget(self.ai_baseline_label)
        score_layout.addWidget(self.ai_delta_label)

        trend_card = QFrame()
        trend_card.setObjectName("AiCard")
        trend_layout = QVBoxLayout(trend_card)
        trend_layout.setContentsMargins(16, 12, 16, 12)
        trend_layout.setSpacing(8)
        trend_title = QLabel("Тренд")
        trend_title.setObjectName("AiTitle")
        self.ai_trend = TrendChart()
        self.ai_trend.setObjectName("AiTrend")

        trend_layout.addWidget(trend_title)
        trend_layout.addWidget(self.ai_trend)

        reasons_card = QFrame()
        reasons_card.setObjectName("AiCard")
        reasons_layout = QVBoxLayout(reasons_card)
        reasons_layout.setContentsMargins(16, 12, 16, 12)
        reasons_layout.setSpacing(8)
        reasons_title = QLabel("Primary drivers")
        reasons_title.setObjectName("AiTitle")
        reasons_layout.addWidget(reasons_title)

        self.ai_reasons_container = QWidget()
        self.ai_reasons_layout = QVBoxLayout(self.ai_reasons_container)
        self.ai_reasons_layout.setContentsMargins(0, 0, 0, 0)
        self.ai_reasons_layout.setSpacing(8)
        self.ai_reasons_layout.addStretch(1)

        reasons_layout.addWidget(self.ai_reasons_container)

        summary_card = QFrame()
        summary_card.setObjectName("AiCard")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 12, 16, 12)
        summary_layout.setSpacing(8)
        summary_title = QLabel("AI-интерпретация")
        summary_title.setObjectName("AiTitle")
        self.ai_summary_label = QLabel("")
        self.ai_summary_label.setWordWrap(True)
        self.ai_summary_label.setObjectName("AiNarrative")

        summary_layout.addWidget(summary_title)
        summary_layout.addWidget(self.ai_summary_label)

        layout.addWidget(form)
        layout.addWidget(header_card)
        layout.addWidget(score_card)
        layout.addWidget(trend_card)
        layout.addWidget(reasons_card)
        layout.addWidget(summary_card)

    def load_org_kpi(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        start_date = self.org_start_input.text().strip() or None
        end_date = self.org_end_input.text().strip() or None
        team_id = self.org_team_input.text().strip() or None
        project_id = self.org_project_input.text().strip() or None

        self.org_load_button.setEnabled(False)
        try:
            response = api_client.get_org_kpi(
                org_id,
                start_date=start_date,
                end_date=end_date,
                team_id=team_id,
                project_id=project_id,
            )
            self.org_output.setText(self._pretty_json(response))
            self.status_label.setText("Org KPI loaded")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.org_load_button.setEnabled(True)

    def export_org_kpi(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        export_format = self.org_format_input.text().strip() or "csv"
        start_date = self.org_start_input.text().strip() or None
        end_date = self.org_end_input.text().strip() or None
        team_id = self.org_team_input.text().strip() or None
        project_id = self.org_project_input.text().strip() or None

        self.org_export_button.setEnabled(False)
        try:
            response = api_client.export_org_kpi(
                org_id,
                export_format=export_format,
                start_date=start_date,
                end_date=end_date,
                team_id=team_id,
                project_id=project_id,
            )
            self.org_output.setText(self._pretty_json(response))
            self.status_label.setText("Org KPI export queued")
        except ApiError as exc:
            self.status_label.setText(f"Export failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Export failed: {exc}")
        finally:
            self.org_export_button.setEnabled(True)

    def load_project_kpi(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        start_date = self.project_start_input.text().strip() or None
        end_date = self.project_end_input.text().strip() or None

        self.project_load_button.setEnabled(False)
        try:
            response = api_client.get_project_kpi(
                org_id,
                start_date=start_date,
                end_date=end_date,
            )
            self.project_output.setText(self._pretty_json(response))
            self.status_label.setText("Project KPI loaded")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.project_load_button.setEnabled(True)

    def export_project_kpi(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        export_format = self.project_format_input.text().strip() or "csv"
        start_date = self.project_start_input.text().strip() or None
        end_date = self.project_end_input.text().strip() or None

        self.project_export_button.setEnabled(False)
        try:
            response = api_client.export_project_kpi(
                org_id,
                export_format=export_format,
                start_date=start_date,
                end_date=end_date,
            )
            self.project_output.setText(self._pretty_json(response))
            self.status_label.setText("Project KPI export queued")
        except ApiError as exc:
            self.status_label.setText(f"Export failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Export failed: {exc}")
        finally:
            self.project_export_button.setEnabled(True)

    def load_performance(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        user_id = self.perf_user_input.text().strip() or None
        team_id = self.perf_team_input.text().strip() or None
        project_id = self.perf_project_input.text().strip() or None
        start_date = self.perf_start_input.text().strip() or None
        end_date = self.perf_end_input.text().strip() or None

        self.perf_load_button.setEnabled(False)
        try:
            response = api_client.get_activity_per_task(
                org_id,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                team_id=team_id,
                project_id=project_id,
            )
            self.perf_output.setText(self._pretty_json(response))
            self.status_label.setText("Performance loaded")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.perf_load_button.setEnabled(True)

    def load_session_metrics(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        session_id = self.metric_session_input.text().strip()
        if not session_id:
            self.status_label.setText("Session id is required")
            return

        self.metric_session_button.setEnabled(False)
        try:
            response = api_client.get_session_metrics(org_id, session_id)
            self.metric_output.setText(self._pretty_json(response))
            self.status_label.setText("Session metrics loaded")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.metric_session_button.setEnabled(True)

    def load_user_metrics(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        user_id = self.metric_user_input.text().strip()
        if not user_id:
            self.status_label.setText("User id is required")
            return

        start_date = self.metric_start_input.text().strip() or None
        end_date = self.metric_end_input.text().strip() or None
        project_id = self.metric_project_input.text().strip() or None

        self.metric_user_button.setEnabled(False)
        try:
            response = api_client.get_user_metrics(
                org_id,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                project_id=project_id,
            )
            self.metric_output.setText(self._pretty_json(response))
            self.status_label.setText("User metrics loaded")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.metric_user_button.setEnabled(True)

    def refresh_exports(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.exports_refresh_button.setEnabled(False)
        try:
            exports = api_client.list_report_exports(org_id)
            self.exports_output.setText(self._pretty_json(exports))
            self.status_label.setText("Exports loaded")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.exports_refresh_button.setEnabled(True)

    def load_ai_kpi(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        period = "daily" if self.ai_day_button.isChecked() else "weekly"
        mode = "executive" if self.ai_mode_manager.isChecked() else "employee"
        if self.ai_profile_pm.isChecked():
            role_profile = "manager"
        elif self.ai_profile_office.isChecked():
            role_profile = "office"
        else:
            role_profile = "developer"
        as_of = self.ai_asof_input.text().strip() or None
        user_id = self.ai_user_input.text().strip() or None
        trend_limit = 14 if period == "daily" else 8

        self.ai_load_button.setEnabled(False)
        try:
            response = api_client.get_ai_scorecards(
                org_id,
                period=period,
                as_of=as_of,
                user_id=user_id,
                mode=mode,
                role_profile=role_profile,
                trend_limit=trend_limit,
            )
            self._render_ai_scorecards(response, user_id)
            self.status_label.setText("AI аналитика обновлена")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.ai_load_button.setEnabled(True)

    def _render_ai_scorecards(self, payload: list[dict], requested_user_id: str | None) -> None:
        if not payload:
            self.ai_user_label.setText("Сотрудник: --")
            self.ai_period_label.setText("Период: --")
            self.ai_hint_label.setText("Нет данных")
            self.ai_score_label.setText("Score: --")
            self.ai_baseline_label.setText("Норма: --")
            self.ai_delta_label.setText("Δ: --")
            self.ai_trend.set_points([])
            self.ai_summary_label.setText("")
            self._clear_layout(self.ai_reasons_layout)
            self.ai_reasons_layout.addStretch(1)
            return

        scorecard = payload[0]
        if len(payload) > 1 and not requested_user_id:
            self.ai_hint_label.setText(f"Показан 1 из {len(payload)}")
        else:
            self.ai_hint_label.setText("")

        full_name = scorecard.get("full_name") or scorecard.get("user_id", "--")
        period_start = scorecard.get("period_start", "--")
        period_end = scorecard.get("period_end", "--")
        self.ai_user_label.setText(f"Сотрудник: {full_name}")
        self.ai_period_label.setText(f"Период: {period_start} → {period_end}")

        current = scorecard.get("current", {})
        score = current.get("score", 0)
        self.ai_score_label.setText(f"Score: {score}")

        baseline = scorecard.get("baseline")
        delta_score = scorecard.get("delta_score")
        delta_text = "Δ: --"
        if baseline:
            baseline_score = baseline.get("avg_score", 0)
            self.ai_baseline_label.setText(f"Норма: {baseline_score:.0f}")
            if baseline_score:
                delta_pct = ((score - baseline_score) / baseline_score) * 100
                delta_text = f"Δ: {score - baseline_score:+.0f} ({delta_pct:+.0f}%)"
            elif delta_score is not None:
                delta_text = f"Δ: {delta_score:+.0f}"
        else:
            self.ai_baseline_label.setText("Норма: --")

        self.ai_delta_label.setText(delta_text)

        trend = scorecard.get("trend", []) or []
        self.ai_trend.set_points(trend)

        self._clear_layout(self.ai_reasons_layout)
        interpretation = scorecard.get("interpretation") or {}
        drivers = interpretation.get("primary_drivers", []) or []
        for driver in drivers:
            item = QFrame()
            item.setObjectName("AiReasonCard")
            item_layout = QVBoxLayout(item)
            item_layout.setContentsMargins(12, 8, 12, 8)
            item_layout.setSpacing(4)
            impact = driver.get("impact_pct", 0)
            title = QLabel(f"{driver.get('title', '')} ({impact:+.0f}%)")
            title.setObjectName("AiTitle")
            detail = QLabel(driver.get("detail", ""))
            detail.setWordWrap(True)
            detail.setObjectName("AiStat")
            item_layout.addWidget(title)
            item_layout.addWidget(detail)
            self.ai_reasons_layout.addWidget(item)
        self.ai_reasons_layout.addStretch(1)

        summary_text = self._build_ai_summary(scorecard)
        self.ai_summary_label.setText(summary_text)

    def _clear_layout(self, layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _pretty_json(self, payload: object) -> str:
        return json.dumps(payload, indent=2, ensure_ascii=True)

    def _build_ai_summary(self, scorecard: dict) -> str:
        interpretation = scorecard.get("interpretation") or {}
        if not interpretation:
            return ""

        lines = [
            "1. Executive summary",
            interpretation.get("executive_summary", ""),
            "",
            "2. Performance vs baseline",
            interpretation.get("vs_baseline", ""),
            "",
            "3. Primary drivers",
        ]

        drivers = interpretation.get("primary_drivers", []) or []
        if drivers:
            for driver in drivers:
                impact = driver.get("impact_pct", 0)
                detail = driver.get("detail", "")
                lines.append(f"• {driver.get('title', '')}: {impact:+.0f}% — {detail}")
        else:
            lines.append("• Недостаточно данных для драйверов.")

        lines.extend(
            [
                "",
                "4. Trend interpretation",
                interpretation.get("trend", ""),
                "",
                "5. Optional optimization suggestion",
                interpretation.get("suggestion", "Опциональных рекомендаций нет."),
            ]
        )

        return "\n".join(line for line in lines if line is not None)


class TrendChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._points: list[dict] = []
        self.setMinimumHeight(140)

    def set_points(self, points: list[dict]) -> None:
        self._points = points
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(12, 12, -12, -12)

        painter.setPen(QPen(Qt.gray, 1))
        painter.drawRect(rect)

        if len(self._points) < 2:
            painter.drawText(rect, Qt.AlignCenter, "Нет данных")
            return

        scores = [point.get("score", 0) for point in self._points]
        min_score = min(scores)
        max_score = max(scores)
        if min_score == max_score:
            min_score = max(0, min_score - 5)
            max_score = min(100, max_score + 5)

        step_x = rect.width() / (len(scores) - 1)
        points = []
        for index, score in enumerate(scores):
            ratio = (score - min_score) / (max_score - min_score)
            x = rect.left() + step_x * index
            y = rect.bottom() - ratio * rect.height()
            points.append((x, y))

        painter.setPen(QPen(Qt.black, 2))
        for idx in range(len(points) - 1):
            x1, y1 = points[idx]
            x2, y2 = points[idx + 1]
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        for x, y in points:
            painter.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)

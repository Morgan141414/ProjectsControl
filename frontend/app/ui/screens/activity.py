import json
import platform

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class ActivityScreen(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.current_session_id: str | None = None
        self.recording_active = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("Активность")
        title.setObjectName("TitleLabel")

        self.status_label = QLabel("")
        self.status_label.setObjectName("Muted")

        controls_frame = QFrame()
        controls_layout = QFormLayout(controls_frame)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        self.device_input = QLineEdit(platform.node())
        self.device_input.setPlaceholderText("Устройство")

        self.os_input = QLineEdit(platform.system())
        self.os_input.setPlaceholderText("ОС")

        self.session_id_input = QLineEdit()
        self.session_id_input.setPlaceholderText("ID сессии (необязательно)")

        self.start_button = QPushButton("Начать сессию")
        self.start_button.clicked.connect(self.start_session)

        self.stop_button = QPushButton("Остановить сессию")
        self.stop_button.clicked.connect(self.stop_session)

        self.recording_start_button = QPushButton("Начать запись (заглушка)")
        self.recording_start_button.clicked.connect(self.start_recording)

        self.recording_stop_button = QPushButton("Остановить запись (заглушка)")
        self.recording_stop_button.clicked.connect(self.stop_recording)

        button_row = QHBoxLayout()
        button_row.addWidget(self.start_button)
        button_row.addWidget(self.stop_button)
        button_row.addStretch(1)
        button_row.addWidget(self.recording_start_button)
        button_row.addWidget(self.recording_stop_button)

        controls_layout.addRow("Устройство", self.device_input)
        controls_layout.addRow("ОС", self.os_input)
        controls_layout.addRow("ID сессии", self.session_id_input)
        controls_layout.addRow(button_row)

        self.tabs = QTabWidget()
        self.my_sessions_tab = QWidget()
        self.org_sessions_tab = QWidget()
        self.recordings_tab = QWidget()

        self.tabs.addTab(self.my_sessions_tab, "Мои сессии")
        self.tabs.addTab(self.org_sessions_tab, "Сессии штаба")
        self.tabs.addTab(self.recordings_tab, "Записи")

        self._build_my_sessions()
        self._build_org_sessions()
        self._build_recordings()

        layout.addWidget(title)
        layout.addWidget(self.status_label)
        layout.addWidget(controls_frame)
        layout.addWidget(self.tabs)

    def _build_my_sessions(self) -> None:
        layout = QVBoxLayout(self.my_sessions_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.my_sessions_list = QListWidget()
        self.my_sessions_list.itemSelectionChanged.connect(self._sync_selected_session)

        self.refresh_my_button = QPushButton("Обновить")
        self.refresh_my_button.clicked.connect(self.refresh_my_sessions)

        layout.addWidget(self.my_sessions_list)
        layout.addWidget(self.refresh_my_button)

    def _build_org_sessions(self) -> None:
        layout = QVBoxLayout(self.org_sessions_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.org_sessions_list = QListWidget()

        self.refresh_org_button = QPushButton("Обновить")
        self.refresh_org_button.clicked.connect(self.refresh_org_sessions)

        layout.addWidget(self.org_sessions_list)
        layout.addWidget(self.refresh_org_button)

    def _build_recordings(self) -> None:
        layout = QVBoxLayout(self.recordings_tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.recordings_list = QListWidget()

        controls = QHBoxLayout()
        self.upload_button = QPushButton("Загрузить запись")
        self.upload_button.clicked.connect(self.upload_recording)

        self.refresh_recordings_button = QPushButton("Обновить")
        self.refresh_recordings_button.clicked.connect(self.refresh_recordings)

        controls.addWidget(self.upload_button)
        controls.addWidget(self.refresh_recordings_button)
        controls.addStretch(1)

        layout.addWidget(self.recordings_list)
        layout.addLayout(controls)

    def _require_org(self) -> str | None:
        org_id = session_store.org_id
        if not org_id:
            self.status_label.setText("Join an organization first")
        return org_id

    def _sync_selected_session(self) -> None:
        selected = self.my_sessions_list.selectedItems()
        if not selected:
            return
        session_id = selected[0].data(Qt.UserRole)
        if session_id:
            self.current_session_id = session_id
            self.session_id_input.setText(session_id)
            self.refresh_recordings()

    def start_session(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        device_name = self.device_input.text().strip() or "Unknown device"
        os_name = self.os_input.text().strip() or "Unknown OS"

        self.start_button.setEnabled(False)
        try:
            response = api_client.start_session(org_id, device_name, os_name)
            self.current_session_id = response.get("id")
            if self.current_session_id:
                self.session_id_input.setText(self.current_session_id)
            self.status_label.setText("Session started")
            self.refresh_my_sessions()
        except ApiError as exc:
            self.status_label.setText(f"Start failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Start failed: {exc}")
        finally:
            self.start_button.setEnabled(True)

    def stop_session(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        session_id = self.session_id_input.text().strip() or self.current_session_id
        if not session_id:
            self.status_label.setText("Provide a session id")
            return

        self.stop_button.setEnabled(False)
        try:
            api_client.stop_session(org_id, session_id)
            self.status_label.setText("Session stopped")
            if session_id == self.current_session_id:
                self.current_session_id = None
            self.refresh_my_sessions()
        except ApiError as exc:
            self.status_label.setText(f"Stop failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Stop failed: {exc}")
        finally:
            self.stop_button.setEnabled(True)

    def start_recording(self) -> None:
        if self.recording_active:
            self.status_label.setText("Recording already active")
            return
        self.recording_active = True
        self.status_label.setText("Recording stub started")

    def stop_recording(self) -> None:
        if not self.recording_active:
            self.status_label.setText("Recording is not active")
            return
        self.recording_active = False
        self.status_label.setText("Recording stub stopped")

    def refresh_my_sessions(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_my_button.setEnabled(False)
        self.my_sessions_list.clear()
        try:
            sessions = api_client.list_my_sessions(org_id)
            for session in sessions:
                label = self._format_session(session)
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, session.get("id"))
                self.my_sessions_list.addItem(item)
            if not sessions:
                self.status_label.setText("No sessions yet")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_my_button.setEnabled(True)

    def refresh_org_sessions(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        self.refresh_org_button.setEnabled(False)
        self.org_sessions_list.clear()
        try:
            sessions = api_client.list_org_sessions(org_id)
            for session in sessions:
                label = self._format_session(session)
                item = QListWidgetItem(label)
                self.org_sessions_list.addItem(item)
            if not sessions:
                self.status_label.setText("No org sessions yet")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_org_button.setEnabled(True)

    def refresh_recordings(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        session_id = self.session_id_input.text().strip() or self.current_session_id
        if not session_id:
            self.status_label.setText("Select a session to load recordings")
            return

        self.refresh_recordings_button.setEnabled(False)
        self.recordings_list.clear()
        try:
            recordings = api_client.list_recordings(org_id, session_id)
            for recording in recordings:
                label = self._format_recording(recording)
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, recording.get("id"))
                self.recordings_list.addItem(item)
            if not recordings:
                self.status_label.setText("No recordings yet")
        except ApiError as exc:
            self.status_label.setText(f"Load failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Load failed: {exc}")
        finally:
            self.refresh_recordings_button.setEnabled(True)

    def upload_recording(self) -> None:
        org_id = self._require_org()
        if not org_id:
            return

        session_id = self.session_id_input.text().strip() or self.current_session_id
        if not session_id:
            self.status_label.setText("Select a session to upload")
            return

        file_path, _ = QFileDialog.getOpenFileName(self, "Select recording")
        if not file_path:
            return

        self.upload_button.setEnabled(False)
        try:
            api_client.upload_recording(org_id, session_id, file_path)
            self.status_label.setText("Recording uploaded")
            self.refresh_recordings()
        except ApiError as exc:
            self.status_label.setText(f"Upload failed: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Upload failed: {exc}")
        finally:
            self.upload_button.setEnabled(True)

    def _format_session(self, session: dict) -> str:
        session_id = session.get("id", "?")
        started = session.get("started_at", "?")
        ended = session.get("ended_at") or "active"
        return f"{session_id}  |  {started}  ->  {ended}"

    def _format_recording(self, recording: dict) -> str:
        payload = json.dumps(recording, ensure_ascii=True)
        return payload

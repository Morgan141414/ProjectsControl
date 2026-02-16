"""Live broadcasts screen for viewing team members' active screen recordings.

Shows Discord-like live view of all currently recording team members. Only
visible to admins and managers.
"""

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal, QByteArray, QUrl
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtNetwork import QAbstractSocket
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store

try:
    from PySide6.QtWebSockets import QWebSocket
    _HAS_WS = True
except ImportError:
    QWebSocket = None
    _HAS_WS = False


class BroadcastsScreen(QWidget):
    """Grid view of all active team broadcasts."""

    go_back = Signal()
    open_recording = Signal(str, str)  # session_id, recording_id

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("BroadcastsHeader")
        header.setFixedHeight(60)
        header.setStyleSheet(
            "QFrame#BroadcastsHeader{background:#151a2e;border-bottom:1px solid #1e2538;}"
        )
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 0, 20, 0)

        # Back button
        back_btn = QPushButton("← Трансляции команды")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#8891a5;font-size:14px;"
            "border:none;padding:8px 12px;}"
            "QPushButton:hover{color:#e8eaf0;}"
        )
        back_btn.clicked.connect(self.go_back.emit)
        hlay.addWidget(back_btn)

        hlay.addStretch(1)

        # Refresh button
        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.setCursor(QCursor(Qt.PointingHandCursor))
        refresh_btn.setFixedHeight(36)
        refresh_btn.setStyleSheet(
            "QPushButton{background:#2a3150;color:#e8eaf0;font-size:14px;"
            "font-weight:600;border:none;border-radius:8px;padding:0 16px;}"
            "QPushButton:hover{background:#3a4160;}"
        )
        refresh_btn.clicked.connect(self.refresh)
        hlay.addWidget(refresh_btn)

        root.addWidget(header)

        # ── Content Area ──────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea{background:#0c1021;border:none;}")

        content = QWidget()
        content.setStyleSheet("background:#0c1021;")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(32, 32, 32, 32)
        self.content_layout.setSpacing(16)

        # Grid container for broadcast cards
        self.grid_widget = QWidget()
        self.grid_widget.setStyleSheet("background:transparent;")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(16)
        self.content_layout.addWidget(self.grid_widget)

        # Empty state
        self.empty_state = QWidget()
        empty_lay = QVBoxLayout(self.empty_state)
        empty_lay.setContentsMargins(0, 60, 0, 60)
        empty_lay.setAlignment(Qt.AlignCenter)

        empty_icon = QLabel("📹")
        empty_icon.setStyleSheet("font-size:48px;background:transparent;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_lay.addWidget(empty_icon)

        empty_title = QLabel("Нет активных трансляций")
        empty_title.setStyleSheet(
            "color:#e8eaf0;font-size:18px;font-weight:600;background:transparent;"
        )
        empty_title.setAlignment(Qt.AlignCenter)
        empty_lay.addWidget(empty_title)

        empty_desc = QLabel(
            "Когда участники команды начнут запись экрана,\n"
            "их трансляции появятся здесь"
        )
        empty_desc.setStyleSheet(
            "color:#8891a5;font-size:14px;background:transparent;"
        )
        empty_desc.setAlignment(Qt.AlignCenter)
        empty_lay.addWidget(empty_desc)

        self.content_layout.addWidget(self.empty_state)
        self.content_layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        # Polling timer for refreshing active sessions
        self._sessions_timer = QTimer(self)
        self._sessions_timer.setInterval(5000)  # 5 seconds
        self._sessions_timer.timeout.connect(self.refresh)

        # Track cards to clean up timers
        self._cards: list[_BroadcastCard] = []

    def refresh(self) -> None:
        """Reload active sessions and update grid."""
        if not session_store.org_id:
            return

        try:
            # Get all active sessions
            sessions = api_client.list_org_sessions(session_store.org_id)
            active_sessions = [s for s in sessions if s.get("status") == "active"]

            # Clear existing cards
            self._clear_cards()

            if not active_sessions:
                self.grid_widget.hide()
                self.empty_state.show()
                return

            self.empty_state.hide()
            self.grid_widget.show()

            # Create cards in 2-column grid
            for i, session in enumerate(active_sessions):
                session_id = session.get("id")
                user_id = session.get("user_id")

                # Get user info
                try:
                    user_data = api_client.get_user(user_id) if user_id else None
                    user_name = user_data.get("full_name", "Неизвестно") if user_data else "Неизвестно"
                    position = user_data.get("specialty", "") if user_data else ""
                except Exception:  # noqa: BLE001
                    user_name = session.get("user_id", "Неизвестно")[:8]
                    position = ""

                started_at = session.get("started_at")

                card = _BroadcastCard(session_id, user_name, position, started_at)
                card.clicked.connect(self._on_card_clicked)

                row = i // 2
                col = i % 2
                self.grid_layout.addWidget(card, row, col)

                self._cards.append(card)

        except ApiError as exc:
            print(f"Error loading broadcasts: {exc}")  # noqa: T201

    def _clear_cards(self) -> None:
        """Remove all broadcast cards and stop their timers."""
        for card in self._cards:
            card.stop_timers()
            card.deleteLater()
        self._cards.clear()

        # Clear grid layout
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_card_clicked(self, session_id: str) -> None:
        """Open full-screen view of broadcast."""
        dialog = _BroadcastViewDialog(session_id, self)
        dialog.exec()

    def showEvent(self, event) -> None:  # noqa: N802
        """Start polling when screen is shown."""
        super().showEvent(event)
        self.refresh()
        self._sessions_timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        """Stop polling when screen is hidden."""
        super().hideEvent(event)
        self._sessions_timer.stop()
        self._clear_cards()


class _BroadcastCard(QFrame):
    """Individual card showing live broadcast preview."""

    clicked = Signal(str)  # session_id

    def __init__(
        self, session_id: str, user_name: str, position: str, started_at: str
    ) -> None:
        super().__init__()
        self._session_id = session_id
        self._started_at = started_at
        self._blink_visible = True

        self.setObjectName("BroadcastCard")
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(320, 260)
        self.setStyleSheet(
            "QFrame#BroadcastCard{background:#151a2e;border:1px solid #1e2538;"
            "border-radius:12px;}"
            "QFrame#BroadcastCard:hover{background:#1e2538;border-color:#2a3150;}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)

        # Live indicator
        top_row = QHBoxLayout()
        self.live_label = QLabel("● LIVE")
        self.live_label.setStyleSheet(
            "color:#ff6b6b;font-size:12px;font-weight:700;background:transparent;"
        )
        top_row.addWidget(self.live_label)
        top_row.addStretch(1)
        lay.addLayout(top_row)

        # Preview image
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(296, 166)
        self.preview_label.setScaledContents(True)
        self.preview_label.setStyleSheet(
            "background:#0c1021;border:1px solid #2a3150;border-radius:8px;"
        )
        self.preview_label.setAlignment(Qt.AlignCenter)

        # Placeholder
        placeholder = QLabel("📹")
        placeholder.setStyleSheet("font-size:48px;color:#4a5068;")
        placeholder.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("Загрузка...")
        self.preview_label.setStyleSheet(
            "background:#0c1021;border:1px solid #2a3150;border-radius:8px;"
            "color:#4a5068;font-size:14px;"
        )

        lay.addWidget(self.preview_label)

        # User info
        self.name_label = QLabel(user_name)
        self.name_label.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:600;background:transparent;"
        )
        lay.addWidget(self.name_label)

        if position:
            pos_label = QLabel(position)
            pos_label.setStyleSheet(
                "color:#8891a5;font-size:12px;background:transparent;"
            )
            lay.addWidget(pos_label)

        # Elapsed time
        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet(
            "color:#8891a5;font-size:12px;background:transparent;"
        )
        lay.addWidget(self.time_label)

        # Preview refresh timer (1.5s)
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(1500)
        self._preview_timer.timeout.connect(self._refresh_preview)
        self._preview_timer.start()

        # Blink timer for LIVE indicator (800ms)
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(800)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start()

        # Elapsed time timer (1s)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._elapsed_timer.start()

        # Initial preview load
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        """Load latest preview image."""
        try:
            data = api_client.get_session_preview(
                session_store.org_id, self._session_id
            )
            if not data:
                return
            pix = QPixmap()
            if pix.loadFromData(data):
                self.preview_label.setPixmap(pix)
                self.preview_label.setStyleSheet(
                    "background:#0c1021;border:1px solid #2a3150;border-radius:8px;"
                )
        except Exception:  # noqa: BLE001
            pass

    def _blink(self) -> None:
        """Toggle LIVE indicator visibility."""
        self._blink_visible = not self._blink_visible
        color = "#ff6b6b" if self._blink_visible else "transparent"
        self.live_label.setStyleSheet(
            f"color:{color};font-size:12px;font-weight:700;background:transparent;"
        )

    def _update_elapsed(self) -> None:
        """Update elapsed time display."""
        if not self._started_at:
            return

        try:
            started = datetime.fromisoformat(self._started_at.replace("Z", "+00:00"))
            elapsed = datetime.now(started.tzinfo) - started
            total_seconds = int(elapsed.total_seconds())

            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60

            self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        except Exception:  # noqa: BLE001
            pass

    def stop_timers(self) -> None:
        """Stop all timers."""
        self._preview_timer.stop()
        self._blink_timer.stop()
        self._elapsed_timer.stop()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        """Emit clicked signal on mouse press."""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._session_id)
        super().mousePressEvent(event)


class _BroadcastViewDialog(QDialog):
    """Full-screen modal for viewing a single broadcast."""

    def __init__(self, session_id: str, parent=None) -> None:
        super().__init__(parent)
        self._session_id = session_id

        self.setWindowTitle("Трансляция экрана")
        self.setModal(True)
        self.resize(960, 640)
        self.setStyleSheet("background:#0c1021;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(
            "background:#151a2e;border-bottom:1px solid #1e2538;"
        )
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 0, 20, 0)

        back_btn = QPushButton("← Назад")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#8891a5;font-size:14px;"
            "border:none;padding:8px 12px;}"
            "QPushButton:hover{color:#e8eaf0;}"
        )
        back_btn.clicked.connect(self.accept)
        hlay.addWidget(back_btn)

        title = QLabel("Прямая трансляция")
        title.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:600;background:transparent;"
        )
        hlay.addWidget(title, 1)

        lay.addWidget(header)

        # Preview image (large)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "background:#000;border:none;"
        )
        lay.addWidget(self.preview_label, 1)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(50)
        footer.setStyleSheet(
            "background:#151a2e;border-top:1px solid #1e2538;"
        )
        flay = QHBoxLayout(footer)
        flay.setContentsMargins(20, 0, 20, 0)

        self.live_label = QLabel("● LIVE")
        self.live_label.setStyleSheet(
            "color:#ff6b6b;font-size:14px;font-weight:700;background:transparent;"
        )
        flay.addWidget(self.live_label)

        self.time_label = QLabel("00:00:00")
        self.time_label.setStyleSheet(
            "color:#8891a5;font-size:14px;background:transparent;"
        )
        flay.addWidget(self.time_label)

        flay.addStretch(1)

        res_label = QLabel("720p")
        res_label.setStyleSheet(
            "color:#8891a5;font-size:14px;background:transparent;"
        )
        flay.addWidget(res_label)

        lay.addWidget(footer)

        # Real-time stream via WebSocket (Zoom/Discord-style) or HTTP fallback
        self._live_ws = None
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._refresh_preview)

        if _HAS_WS and QWebSocket:
            token = getattr(session_store, "token", None)
            org_id = getattr(session_store, "org_id", None)
            if org_id and token:
                url = api_client.live_stream_ws_url(org_id, self._session_id, token, "viewer")
                self._live_ws = QWebSocket(self)
                self._live_ws.binaryMessageReceived.connect(self._on_ws_frame)
                self._live_ws.open(QUrl(url))
                self.preview_label.setText("Подключение к трансляции…")
            else:
                self._refresh_timer.start()
                self._refresh_preview()
        else:
            self._refresh_timer.start()
            self._refresh_preview()

    def _on_ws_frame(self, data: QByteArray) -> None:
        """Display frame received over WebSocket."""
        if data.isEmpty():
            return
        pix = QPixmap()
        if pix.loadFromData(bytes(data)):
            scaled = pix.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.preview_label.setPixmap(scaled)
            self.preview_label.setText("")
            self.preview_label.setStyleSheet("background:#000;border:none;")

    def _refresh_preview(self) -> None:
        """HTTP fallback: load latest preview."""
        try:
            data = api_client.get_session_preview(
                session_store.org_id, self._session_id
            )
            if data:
                pix = QPixmap()
                if pix.loadFromData(data):
                    scaled = pix.scaled(
                        self.preview_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    self.preview_label.setPixmap(scaled)
                    self.preview_label.setText("")
                    return
            self.preview_label.setText("Ожидание кадра…")
            self.preview_label.setStyleSheet(
                "background:#000;border:none;color:#94a3b8;font-size:14px;"
            )
        except Exception:  # noqa: BLE001
            self.preview_label.setText("Ожидание кадра…")
            self.preview_label.setStyleSheet(
                "background:#000;border:none;color:#94a3b8;font-size:14px;"
            )

    def closeEvent(self, event) -> None:  # noqa: N802
        if getattr(self, "_live_ws", None) is not None:
            try:
                self._live_ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._live_ws.deleteLater()
            self._live_ws = None
        self._refresh_timer.stop()
        super().closeEvent(event)

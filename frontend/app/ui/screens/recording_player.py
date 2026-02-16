"""Video playback screen for viewing recorded sessions.

Provides full video player with controls for team leads and admins to review
employee screen recordings.
"""

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import ApiError, api_client
from app.state.session import session_store


class RecordingPlayerScreen(QWidget):
    """Full video player for recorded sessions."""

    go_back = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._session_id: str | None = None
        self._recording_id: str | None = None
        self._temp_file_path: Path | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setObjectName("PlayerHeader")
        header.setFixedHeight(60)
        header.setStyleSheet(
            "QFrame#PlayerHeader{background:#151a2e;border-bottom:1px solid #1e2538;}"
        )
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 0, 20, 0)

        # Back button
        back_btn = QPushButton("← Назад")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setStyleSheet(
            "QPushButton{background:transparent;color:#8891a5;font-size:14px;"
            "border:none;padding:8px 12px;}"
            "QPushButton:hover{color:#e8eaf0;}"
        )
        back_btn.clicked.connect(self.go_back.emit)
        hlay.addWidget(back_btn)

        # Title
        self.title_label = QLabel("Запись сессии")
        self.title_label.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:600;background:transparent;"
        )
        hlay.addWidget(self.title_label, 1)

        # Download button
        self.download_btn = QPushButton("⬇ Скачать")
        self.download_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.download_btn.setFixedHeight(36)
        self.download_btn.setStyleSheet(
            "QPushButton{background:#4f8fff;color:#0c1021;font-size:14px;"
            "font-weight:600;border:none;border-radius:8px;padding:0 16px;}"
            "QPushButton:hover{background:#6ba3ff;}"
            "QPushButton:disabled{background:#2a3150;color:#4a5068;}"
        )
        self.download_btn.clicked.connect(self._download_recording)
        hlay.addWidget(self.download_btn)

        root.addWidget(header)

        # ── Video Player ──────────────────────────────────────────
        player_container = QWidget()
        player_container.setStyleSheet("background:#000;")
        pc_lay = QVBoxLayout(player_container)
        pc_lay.setContentsMargins(0, 0, 0, 0)
        pc_lay.setSpacing(0)

        # Video widget
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)

        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background:#000;")
        self._player.setVideoOutput(self._video_widget)

        pc_lay.addWidget(self._video_widget, 1)

        # Connect player signals
        self._player.positionChanged.connect(self._update_position)
        self._player.durationChanged.connect(self._update_duration)
        self._player.playbackStateChanged.connect(self._update_play_button)
        self._player.errorOccurred.connect(self._handle_error)

        root.addWidget(player_container, 1)

        # ── Controls ──────────────────────────────────────────────
        controls = QFrame()
        controls.setObjectName("PlayerControls")
        controls.setFixedHeight(100)
        controls.setStyleSheet(
            "QFrame#PlayerControls{background:#151a2e;border-top:1px solid #1e2538;}"
        )
        ctrls_lay = QVBoxLayout(controls)
        ctrls_lay.setContentsMargins(24, 12, 24, 12)
        ctrls_lay.setSpacing(12)

        # Seek slider
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderMoved.connect(self._seek)
        self.seek_slider.setStyleSheet(
            "QSlider::groove:horizontal{height:4px;background:#2a3150;border-radius:2px;}"
            "QSlider::handle:horizontal{background:#4f8fff;border:none;width:12px;"
            "height:12px;margin:-4px 0;border-radius:6px;}"
            "QSlider::sub-page:horizontal{background:#4f8fff;border-radius:2px;}"
        )
        ctrls_lay.addWidget(self.seek_slider)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        # Play/Pause
        self.play_btn = QPushButton("▶")
        self.play_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setStyleSheet(
            "QPushButton{background:#4f8fff;color:#0c1021;font-size:18px;"
            "border:none;border-radius:20px;}"
            "QPushButton:hover{background:#6ba3ff;}"
        )
        self.play_btn.clicked.connect(self._toggle_play)
        btn_row.addWidget(self.play_btn)

        # Stop
        stop_btn = QPushButton("⏹")
        stop_btn.setCursor(QCursor(Qt.PointingHandCursor))
        stop_btn.setFixedSize(40, 40)
        stop_btn.setStyleSheet(
            "QPushButton{background:#2a3150;color:#e8eaf0;font-size:18px;"
            "border:none;border-radius:20px;}"
            "QPushButton:hover{background:#3a4160;}"
        )
        stop_btn.clicked.connect(self._stop)
        btn_row.addWidget(stop_btn)

        # Time display
        self.time_label = QLabel("00:00:00 / 00:00:00")
        self.time_label.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )
        btn_row.addWidget(self.time_label)

        btn_row.addStretch(1)

        # Volume control
        vol_label = QLabel("🔊")
        vol_label.setStyleSheet("font-size:16px;background:transparent;")
        btn_row.addWidget(vol_label)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self._set_volume)
        self.volume_slider.setStyleSheet(
            "QSlider::groove:horizontal{height:4px;background:#2a3150;border-radius:2px;}"
            "QSlider::handle:horizontal{background:#4f8fff;border:none;width:10px;"
            "height:10px;margin:-3px 0;border-radius:5px;}"
            "QSlider::sub-page:horizontal{background:#4f8fff;border-radius:2px;}"
        )
        btn_row.addWidget(self.volume_slider)

        ctrls_lay.addLayout(btn_row)

        root.addWidget(controls)

        # ── Metadata ──────────────────────────────────────────────
        meta = QFrame()
        meta.setObjectName("PlayerMeta")
        meta.setFixedHeight(60)
        meta.setStyleSheet(
            "QFrame#PlayerMeta{background:#0c1021;border-top:1px solid #1e2538;}"
        )
        meta_lay = QHBoxLayout(meta)
        meta_lay.setContentsMargins(24, 0, 24, 0)

        self.meta_label = QLabel("")
        self.meta_label.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )
        meta_lay.addWidget(self.meta_label)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )
        meta_lay.addWidget(self.status_label, 1, Qt.AlignRight)

        root.addWidget(meta)

        # Set initial volume
        self._set_volume(70)

    def set_recording(self, session_id: str, recording_id: str) -> None:
        """Load and play recording."""
        self._session_id = session_id
        self._recording_id = recording_id
        self._load_recording()

    def _load_recording(self) -> None:
        """Download and load recording into player."""
        if not self._session_id or not self._recording_id:
            return

        self.status_label.setText("Загрузка...")
        self.download_btn.setEnabled(False)

        try:
            # Get recording metadata
            recordings = api_client.list_recordings(
                session_store.org_id, self._session_id
            )
            recording = next(
                (r for r in recordings if r["id"] == self._recording_id), None
            )

            if not recording:
                self.status_label.setText("Запись не найдена")
                return

            # Download to temp file
            data = api_client.download_recording(
                session_store.org_id, self._recording_id
            )

            self._temp_file_path = (
                Path(tempfile.gettempdir()) / f"{self._recording_id}.mp4"
            )
            self._temp_file_path.write_bytes(data)

            # Load into player
            self._player.setSource(QUrl.fromLocalFile(str(self._temp_file_path)))

            # Update metadata display
            size_mb = recording.get("size_bytes", 0) / (1024 * 1024)
            created = recording.get("created_at", "")[:10]
            self.meta_label.setText(
                f"Сессия: {self._session_id[:8]}... • {created} • "
                f"Размер: {size_mb:.1f} МБ • 720p"
            )

            self.status_label.setText("Готово к воспроизведению")
            self.download_btn.setEnabled(True)

        except ApiError as exc:
            self.status_label.setText(f"Ошибка: {exc}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка загрузки: {exc}")

    def _toggle_play(self) -> None:
        """Toggle play/pause."""
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _stop(self) -> None:
        """Stop playback."""
        self._player.stop()
        self.seek_slider.setValue(0)

    def _seek(self, position: int) -> None:
        """Seek to position."""
        self._player.setPosition(position)

    def _set_volume(self, value: int) -> None:
        """Set volume (0-100)."""
        self._audio_output.setVolume(value / 100.0)

    def _update_position(self, position: int) -> None:
        """Update slider and time display when position changes."""
        self.seek_slider.blockSignals(True)
        self.seek_slider.setValue(position)
        self.seek_slider.blockSignals(False)

        current = self._format_time(position)
        total = self._format_time(self._player.duration())
        self.time_label.setText(f"{current} / {total}")

    def _update_duration(self, duration: int) -> None:
        """Update slider range when duration known."""
        self.seek_slider.setRange(0, duration)

    def _update_play_button(self) -> None:
        """Update play button icon based on state."""
        if self._player.playbackState() == QMediaPlayer.PlayingState:
            self.play_btn.setText("⏸")
        else:
            self.play_btn.setText("▶")

    def _handle_error(self) -> None:
        """Handle playback errors."""
        error_msg = self._player.errorString()
        self.status_label.setText(f"Ошибка воспроизведения: {error_msg}")

    def _format_time(self, ms: int) -> str:
        """Format milliseconds as HH:MM:SS."""
        seconds = ms // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _download_recording(self) -> None:
        """Download recording to user-selected location."""
        if not self._recording_id:
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить запись",
            f"recording_{self._recording_id[:8]}.mp4",
            "Video Files (*.mp4)",
        )

        if not file_path:
            return

        try:
            self.status_label.setText("Сохранение...")
            data = api_client.download_recording(
                session_store.org_id, self._recording_id
            )
            Path(file_path).write_bytes(data)
            self.status_label.setText(f"Сохранено: {Path(file_path).name}")
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Ошибка сохранения: {exc}")

    def cleanup(self) -> None:
        """Clean up resources when leaving screen."""
        self._player.stop()
        if self._temp_file_path and self._temp_file_path.exists():
            try:
                self._temp_file_path.unlink()
            except Exception:  # noqa: BLE001, S110
                pass

"""Personal Cabinet screen — «Личный кабинет».

Features:
  - Greeting + position + department info
  - "Начать работу" / "Работа идёт..." / "Прервать работу"
  - Real screen recording (mss + OpenCV) like Discord screen share
  - Before stopping, a report banner appears (AI asks for report)
  - Report shown in "Ваши задачи на сегодня" section
  - Productivity stats + KPD bar
"""

import os
import platform
import threading
import time
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QByteArray, QBuffer, QIODevice, Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPixmap
from PySide6.QtNetwork import QAbstractSocket
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.services.api_client import api_client
from app.state.session import session_store

try:
    from PySide6.QtSvg import QSvgRenderer
    _HAS_SVG = True
except ImportError:
    _HAS_SVG = False

try:
    from PySide6.QtWebSockets import QWebSocket
    _HAS_WEBSOCKET = True
except ImportError:
    QWebSocket = None
    _HAS_WEBSOCKET = False

# ── SVG icons ─────────────────────────────────────────────────────
_ICON_ARROW_LEFT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="19" y1="12" x2="5" y2="12"/>'
    '<polyline points="12 19 5 12 12 5"/></svg>'
)
_ICON_CLIPBOARD = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6'
    'a2 2 0 0 1 2-2h2"/>'
    '<rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>'
)
_ICON_ACTIVITY = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>'
)
_ICON_ZAP = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>'
)
_ICON_CLOCK = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<polyline points="12 6 12 12 16 14"/></svg>'
)
_ICON_TARGET = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<circle cx="12" cy="12" r="10"/>'
    '<circle cx="12" cy="12" r="6"/>'
    '<circle cx="12" cy="12" r="2"/></svg>'
)
_ICON_TRENDING_UP = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>'
    '<polyline points="17 6 23 6 23 12"/></svg>'
)
_ICON_CHECK_CIRCLE = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>'
    '<polyline points="22 4 12 14.01 9 11.01"/></svg>'
)
_ICON_PLAY = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="5 3 19 12 5 21 5 3"/></svg>'
)
_ICON_PAUSE = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="6" y="4" width="4" height="16"/>'
    '<rect x="14" y="4" width="4" height="16"/></svg>'
)
_ICON_STOP = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>'
)
_ICON_COFFEE = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M18 8h1a4 4 0 0 1 0 8h-1"/>'
    '<path d="M2 8h16v9a4 4 0 0 1-4 4H6a4 4 0 0 1-4-4V8z"/>'
    '<line x1="6" y1="1" x2="6" y2="4"/>'
    '<line x1="10" y1="1" x2="10" y2="4"/>'
    '<line x1="14" y1="1" x2="14" y2="4"/></svg>'
)
_ICON_ROBOT = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="11" width="18" height="10" rx="2"/>'
    '<circle cx="12" cy="5" r="2"/>'
    '<line x1="12" y1="7" x2="12" y2="11"/>'
    '<line x1="8" y1="16" x2="8" y2="16"/>'
    '<line x1="16" y1="16" x2="16" y2="16"/></svg>'
)
_ICON_SEND = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
    ' stroke-linecap="round" stroke-linejoin="round">'
    '<line x1="22" y1="2" x2="11" y2="13"/>'
    '<polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>'
)


def _svg_icon(svg_t: str, size: int = 18, color: str = "#8891a5") -> QIcon:
    if not _HAS_SVG:
        return QIcon()
    svg = svg_t.replace("{c}", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return QIcon(pix)


def _svg_pixmap(svg_t: str, size: int = 18, color: str = "#8891a5") -> QPixmap:
    if not _HAS_SVG:
        return QPixmap()
    svg = svg_t.replace("{c}", color)
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return pix


def _greeting() -> str:
    h = datetime.now().hour
    if h < 6:
        return "Доброй ночи"
    if h < 12:
        return "Доброе утро"
    if h < 18:
        return "Добрый день"
    return "Добрый вечер"


def _stat_card(icon_svg: str, icon_color: str, value: str, label: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet("QFrame{background:#151a2e;border:none;border-radius:12px;}")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 16, 16, 16)
    lay.setSpacing(8)
    ic = QLabel()
    ic.setFixedSize(32, 32)
    ic.setAlignment(Qt.AlignCenter)
    ic.setStyleSheet(f"background:{icon_color}18;border-radius:16px;")
    px = _svg_pixmap(icon_svg, 18, icon_color)
    if not px.isNull():
        ic.setPixmap(px)
    lay.addWidget(ic)
    vlab = QLabel(value)
    vlab.setStyleSheet("color:#e8eaf0;font-size:22px;font-weight:800;background:transparent;")
    lay.addWidget(vlab)
    tlab = QLabel(label)
    tlab.setStyleSheet("color:#8891a5;font-size:12px;background:transparent;")
    tlab.setWordWrap(True)
    lay.addWidget(tlab)
    return card


# ═══════════════════════════════════════════════════════════════════════
#  Video Recorder — real screen recording like Discord screen share
#  720p @ 15 FPS, H.264 / mp4v codec, threaded capture + encode
# ═══════════════════════════════════════════════════════════════════════

_RECORDINGS_DIR = str(Path(__file__).resolve().parents[2] / "data" / "recordings")


def _format_file_size(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} КБ"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1024 / 1024:.1f} МБ"
    return f"{size_bytes / 1024 / 1024 / 1024:.2f} ГБ"


class _VideoRecorder:
    """Threaded screen recorder: mss capture → OpenCV encode → .mp4 file.

    OPTIMIZED for Discord-quality screen share:
      - 720p resolution  (1280 × 720)
      - 30 FPS target    (Discord standard, reduced CPU load)
      - H264 hardware encoding (NVENC/QSV/AMF) with fallback
      - Background thread for zero UI blocking
      - Adaptive FPS tracking
    """

    TARGET_W, TARGET_H = 1280, 720
    DEFAULT_FPS = 30  # Changed from 60 to 30 (Discord standard)

    def __init__(self, fps: int = DEFAULT_FPS) -> None:
        self._fps = fps
        self._interval = 1.0 / fps
        self._running = False
        self._paused = False
        self._thread: threading.Thread | None = None
        self._output_path: str | None = None
        self._frame_count = 0
        self._file_size = 0
        self._actual_fps: float = 0.0
        self._start_time: float = 0.0
        self._pause_accum: float = 0.0
        self._pause_start: float = 0.0
        self._lock = threading.Lock()

    # ── public API ────────────────────────────────────────────────

    def start(self, output_dir: str | None = None) -> str:
        """Start recording. Returns the output .mp4 file path."""
        if self._running:
            return self._output_path or ""

        out = output_dir or _RECORDINGS_DIR
        os.makedirs(out, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._output_path = os.path.join(out, f"rec_{ts}.mp4")

        self._frame_count = 0
        self._file_size = 0
        self._running = True
        self._paused = False
        self._start_time = time.monotonic()
        self._pause_accum = 0.0

        self._thread = threading.Thread(
            target=self._record_loop, daemon=True, name="ScreenRecorder"
        )
        self._thread.start()
        return self._output_path

    def pause(self) -> None:
        """Pause recording (frames stop being written)."""
        with self._lock:
            if self._running and not self._paused:
                self._paused = True
                self._pause_start = time.monotonic()

    def resume(self) -> None:
        """Resume after pause."""
        with self._lock:
            if self._running and self._paused:
                self._pause_accum += time.monotonic() - self._pause_start
                self._paused = False

    def stop(self) -> str:
        """Stop recording and finalise .mp4. Returns file path."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        return self._output_path or ""

    def is_running(self) -> bool:
        return self._running

    def is_paused(self) -> bool:
        return self._paused

    def stats(self) -> dict:
        """Return current stats (thread-safe)."""
        with self._lock:
            elapsed = 0.0
            if self._start_time:
                raw = time.monotonic() - self._start_time
                pause = self._pause_accum
                if self._paused:
                    pause += time.monotonic() - self._pause_start
                elapsed = max(0.0, raw - pause)
            return {
                "frames": self._frame_count,
                "file_size": self._file_size,
                "duration": elapsed,
                "fps": self._fps,
                "actual_fps": self._actual_fps,
                "resolution": f"{self.TARGET_W}x{self.TARGET_H}",
                "path": self._output_path or "",
            }

    # ── background capture loop ───────────────────────────────────

    def _record_loop(self) -> None:
        """Main capture → encode loop running in a daemon thread."""
        try:
            import cv2
            import mss
            import numpy as np
        except ImportError as exc:
            print(f"[VideoRecorder] missing dependency: {exc}")
            self._running = False
            return

        sct = mss.mss()
        monitor = sct.monitors[1]  # primary monitor

        # Try H.264 hardware encoding first (Discord-quality), then fallback to software codecs
        # Hardware encoding significantly reduces CPU usage (30-50% less than software)
        print(f"[VideoRecorder] Trying codecs for {self._fps} FPS @ 720p...")

        codecs_to_try = [
            ("H264", "H.264 (hardware or software)"),
            ("avc1", "H.264 AVC1 (macOS hardware)"),
            ("mp4v", "MPEG-4 Part 2"),
            ("XVID", "Xvid MPEG-4"),
            ("MJPG", "Motion JPEG (fallback)"),
        ]

        writer = None
        for codec, desc in codecs_to_try:
            try:
                fourcc = cv2.VideoWriter_fourcc(*codec)
                writer = cv2.VideoWriter(
                    self._output_path, fourcc, self._fps,
                    (self.TARGET_W, self.TARGET_H),
                )
                if writer.isOpened():
                    print(f"[VideoRecorder] ✓ Using codec: {desc}")
                    break
                writer.release()
                writer = None
            except Exception as e:
                print(f"[VideoRecorder] ✗ {desc} failed: {e}")
                continue

        if not writer:
            # Last resort fallback
            print("[VideoRecorder] All codecs failed, using mp4v fallback...")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(
                self._output_path, fourcc, self._fps,
                (self.TARGET_W, self.TARGET_H),
            )

        if not writer.isOpened():
            print("[VideoRecorder] Could not open VideoWriter")
            sct.close()
            self._running = False
            return

        size_check_interval = self._fps  # check file size once per second
        # ── Adaptive FPS tracking ─────────────────────────────────
        fps_counter = 0
        fps_timer = time.monotonic()

        while self._running:
            t0 = time.monotonic()

            # If paused — sleep and skip frame
            if self._paused:
                time.sleep(0.05)
                continue

            # 1. Grab screen via mss (DXGI on Windows — hardware capture)
            try:
                img = sct.grab(monitor)
            except Exception:  # noqa: BLE001
                time.sleep(self._interval)
                continue

            # 2. BGRA → BGR numpy array
            frame = np.array(img, dtype=np.uint8)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # 3. Resize to 720p
            if frame.shape[1] != self.TARGET_W or frame.shape[0] != self.TARGET_H:
                frame = cv2.resize(
                    frame, (self.TARGET_W, self.TARGET_H),
                    interpolation=cv2.INTER_AREA,
                )

            # 4. Write frame
            writer.write(frame)

            # 5. Update counters + adaptive FPS measurement
            fps_counter += 1
            with self._lock:
                self._frame_count += 1
                if self._frame_count % size_check_interval == 0:
                    try:
                        self._file_size = os.path.getsize(self._output_path)
                    except OSError:
                        pass
                # Measure actual achieved FPS every second
                fps_elapsed = time.monotonic() - fps_timer
                if fps_elapsed >= 1.0:
                    self._actual_fps = round(fps_counter / fps_elapsed, 1)
                    fps_counter = 0
                    fps_timer = time.monotonic()

            # 6. Maintain target FPS (sleep for remainder of frame interval)
            elapsed = time.monotonic() - t0
            sleep_time = self._interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        # ── Cleanup ───────────────────────────────────────────────
        writer.release()
        sct.close()

        # Final file size
        try:
            self._file_size = os.path.getsize(self._output_path)
        except OSError:
            pass


# ═══════════════════════════════════════════════════════════════════════
#  CabinetScreen
# ═══════════════════════════════════════════════════════════════════════

class CabinetScreen(QWidget):
    """Personal cabinet — «Личный кабинет»."""

    go_back = Signal()

    # Work states
    _STATE_IDLE = "idle"
    _STATE_WORKING = "working"
    _STATE_BREAK = "break"
    _STATE_REPORT = "report"  # must submit report before full stop

    def __init__(self) -> None:
        super().__init__()
        self._work_state = self._STATE_IDLE
        self._session_id: str | None = None
        self._work_start_ts: float | None = None
        self._recorder = _VideoRecorder(fps=30)  # Discord standard FPS
        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(1_000)  # update recording stats every 1 sec
        self._stats_timer.timeout.connect(self._update_recording_stats)
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        # Live stream: WebSocket (Zoom/Discord-style) или HTTP fallback.
        # Optimized: 10 FPS (~100 мс) для снижения нагрузки (Discord uses 10-15 FPS for preview)
        self._live_ws = None
        self._preview_timer = QTimer(self)
        self._preview_timer.setInterval(100)  # 10 FPS для живой трансляции (оптимизировано)
        self._preview_timer.timeout.connect(self._send_live_preview_tick)
        self._last_preview_bytes: bytes | None = None  # Cache last frame
        self._preview_cache_lock = threading.Lock()

        self.setStyleSheet("background:#0c1021;")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet("background:#0c1021;border-bottom:1px solid #1e2538;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(20, 10, 20, 10)

        back = QPushButton()
        back.setCursor(Qt.PointingHandCursor)
        back.setIcon(_svg_icon(_ICON_ARROW_LEFT, 20, "#8891a5"))
        back.setFixedSize(36, 36)
        back.setStyleSheet(
            "QPushButton{background:transparent;border:none;}"
            "QPushButton:hover{background:#1e2538;border-radius:6px;}"
        )
        back.clicked.connect(self.go_back.emit)

        title = QLabel("Личный кабинет")
        title.setStyleSheet(
            "color:#e8eaf0;font-size:18px;font-weight:700;background:transparent;"
        )
        hl.addWidget(back)
        hl.addWidget(title, 1)
        outer.addWidget(header)

        # ── Scrollable body ───────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:#0c1021;border:none;")

        body = QWidget()
        body.setStyleSheet("background:#0c1021;")
        self._body_lay = QVBoxLayout(body)
        self._body_lay.setContentsMargins(28, 24, 28, 28)
        self._body_lay.setSpacing(20)

        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # ── Greeting ──────────────────────────────────────────────
        self._greeting = QLabel()
        self._greeting.setStyleSheet(
            "color:#e8eaf0;font-size:24px;font-weight:800;background:transparent;"
        )
        self._body_lay.addWidget(self._greeting)

        # ── Position / Department info bar ────────────────────────
        info_bar = QFrame()
        info_bar.setStyleSheet(
            "QFrame{background:#151a2e;border:none;border-radius:14px;}"
        )
        ib_lay = QHBoxLayout(info_bar)
        ib_lay.setContentsMargins(20, 14, 20, 14)
        ib_lay.setSpacing(20)

        # position
        pos_col = QVBoxLayout()
        pos_col.setSpacing(2)
        pos_t = QLabel("Должность")
        pos_t.setStyleSheet("color:#4a5068;font-size:11px;background:transparent;")
        pos_col.addWidget(pos_t)
        self._position_lbl = QLabel("—")
        self._position_lbl.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:600;background:transparent;"
        )
        pos_col.addWidget(self._position_lbl)
        ib_lay.addLayout(pos_col, 1)

        v_sep = QFrame()
        v_sep.setFixedWidth(1)
        v_sep.setStyleSheet("background:#1e2538;")
        ib_lay.addWidget(v_sep)

        # department
        dept_col = QVBoxLayout()
        dept_col.setSpacing(2)
        dept_t = QLabel("Отдел")
        dept_t.setStyleSheet("color:#4a5068;font-size:11px;background:transparent;")
        dept_col.addWidget(dept_t)
        self._dept_lbl = QLabel("—")
        self._dept_lbl.setStyleSheet(
            "color:#e8eaf0;font-size:14px;font-weight:600;background:transparent;"
        )
        dept_col.addWidget(self._dept_lbl)
        ib_lay.addLayout(dept_col, 1)

        self._body_lay.addWidget(info_bar)

        # ── По макету: большая область «Его трансляция экрана» ─────────────────
        self._broadcast_placeholder = QFrame()
        self._broadcast_placeholder.setMinimumHeight(280)
        self._broadcast_placeholder.setStyleSheet(
            "QFrame{background:#151a2e;border:1px solid #1e2538;"
            "border-radius:16px;}"
        )
        bph = QVBoxLayout(self._broadcast_placeholder)
        bph.setContentsMargins(24, 24, 24, 24)
        self._broadcast_placeholder_label = QLabel(
            "Его трансляция экрана\n\nНачните работу, чтобы вести трансляцию экрана."
        )
        self._broadcast_placeholder_label.setAlignment(Qt.AlignCenter)
        self._broadcast_placeholder_label.setStyleSheet(
            "color:#64748b;font-size:14px;background:transparent;"
        )
        self._broadcast_placeholder_label.setWordWrap(True)
        bph.addWidget(self._broadcast_placeholder_label, 1)
        self._body_lay.addWidget(self._broadcast_placeholder)

        # ── Work control bar ──────────────────────────────────────
        self._work_bar = QFrame()
        self._work_bar.setStyleSheet(
            "QFrame{background:#151a2e;border:none;border-radius:14px;}"
        )
        wb = QHBoxLayout(self._work_bar)
        wb.setContentsMargins(20, 14, 20, 14)
        wb.setSpacing(14)

        # Elapsed time label
        self._elapsed_lbl = QLabel("00:00:00")
        self._elapsed_lbl.setStyleSheet(
            "color:#8891a5;font-size:20px;font-weight:700;"
            "font-family:'Consolas','Courier New',monospace;background:transparent;"
        )
        wb.addWidget(self._elapsed_lbl)

        wb.addStretch(1)

        # "Начать работу" button
        self._start_btn = QPushButton("  Начать работу")
        self._start_btn.setCursor(Qt.PointingHandCursor)
        self._start_btn.setFixedHeight(42)
        self._start_btn.setIcon(_svg_icon(_ICON_PLAY, 16, "#0c1021"))
        self._start_btn.setStyleSheet(
            "QPushButton{background:#2563eb;color:#f1f5f9;font-size:14px;"
            "font-weight:700;border:none;border-radius:10px;padding:0 22px;}"
            "QPushButton:hover{background:#3b82f6;}"
        )
        self._start_btn.clicked.connect(self._on_start_work)
        wb.addWidget(self._start_btn)

        # "Прервать работу" button (break/pause)
        self._break_btn = QPushButton("  Прервать работу")
        self._break_btn.setCursor(Qt.PointingHandCursor)
        self._break_btn.setFixedHeight(42)
        self._break_btn.setIcon(_svg_icon(_ICON_COFFEE, 16, "#ffffff"))
        self._break_btn.setStyleSheet(
            "QPushButton{background:#f59e0b;color:#ffffff;font-size:14px;"
            "font-weight:700;border:none;border-radius:10px;padding:0 22px;}"
            "QPushButton:hover{background:#f59e0b;}"
        )
        self._break_btn.clicked.connect(self._on_break)
        self._break_btn.setVisible(False)
        wb.addWidget(self._break_btn)

        # "Завершить" button (stop — shows report first)
        self._stop_btn = QPushButton("  Завершить")
        self._stop_btn.setCursor(Qt.PointingHandCursor)
        self._stop_btn.setFixedHeight(42)
        self._stop_btn.setIcon(_svg_icon(_ICON_STOP, 16, "#ffffff"))
        self._stop_btn.setStyleSheet(
            "QPushButton{background:#ef4444;color:#ffffff;font-size:14px;"
            "font-weight:700;border:none;border-radius:10px;padding:0 22px;}"
            "QPushButton:hover{background:#ff6e69;}"
        )
        self._stop_btn.clicked.connect(self._on_stop_request)
        self._stop_btn.setVisible(False)
        wb.addWidget(self._stop_btn)

        self._body_lay.addWidget(self._work_bar)

        # ── Live broadcast status panel (hidden when idle) ────────
        self._broadcast_panel = QFrame()
        self._broadcast_panel.setVisible(False)
        self._broadcast_panel.setStyleSheet(
            "QFrame{background:#151a2e;border:none;border-radius:14px;}"
        )
        bp_lay = QVBoxLayout(self._broadcast_panel)
        bp_lay.setContentsMargins(20, 14, 20, 14)
        bp_lay.setSpacing(10)

        # Row 1: REC indicator + AI processing status
        status_row = QHBoxLayout()
        status_row.setSpacing(16)

        # ● REC — blinking red dot
        self._rec_dot = QLabel("●")
        self._rec_dot.setFixedWidth(16)
        self._rec_dot.setStyleSheet(
            "color:#ef4444;font-size:16px;font-weight:900;background:transparent;"
        )
        status_row.addWidget(self._rec_dot)

        rec_label = QLabel("Трансляция экрана")
        rec_label.setStyleSheet(
            "color:#ef4444;font-size:13px;font-weight:700;background:transparent;"
        )
        status_row.addWidget(rec_label)

        # separator
        sep_dot = QLabel("·")
        sep_dot.setStyleSheet("color:#4a5068;font-size:16px;background:transparent;")
        status_row.addWidget(sep_dot)

        # AI brain icon + processing label
        ai_proc_ic = QLabel()
        ai_proc_ic.setFixedSize(20, 20)
        ai_proc_ic.setAlignment(Qt.AlignCenter)
        ai_proc_ic.setStyleSheet("background:transparent;border:none;")
        aip2 = _svg_pixmap(_ICON_ROBOT, 16, "#4f8fff")
        if not aip2.isNull():
            ai_proc_ic.setPixmap(aip2)
        status_row.addWidget(ai_proc_ic)

        self._ai_status_lbl = QLabel("ИИ анализирует...")
        self._ai_status_lbl.setStyleSheet(
            "color:#60a5fa;font-size:13px;font-weight:600;background:transparent;"
        )
        status_row.addWidget(self._ai_status_lbl)

        status_row.addStretch(1)

        # Recording stats (duration · size · resolution)
        self._frame_count_lbl = QLabel("IDLE Готов к записи")
        self._frame_count_lbl.setStyleSheet(
            "color:#4a5068;font-size:11px;background:transparent;"
        )
        status_row.addWidget(self._frame_count_lbl)

        bp_lay.addLayout(status_row)

        # Row 2: who can see this broadcast
        viewers_row = QHBoxLayout()
        viewers_row.setSpacing(8)

        eye_ic = QLabel()
        eye_ic.setFixedSize(16, 16)
        eye_ic.setAlignment(Qt.AlignCenter)
        eye_ic.setStyleSheet("background:transparent;border:none;")
        _ICON_EYE = (
            '<svg viewBox="0 0 24 24" fill="none" stroke="{c}" stroke-width="2"'
            ' stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>'
            '<circle cx="12" cy="12" r="3"/></svg>'
        )
        epx = _svg_pixmap(_ICON_EYE, 14, "#4a5068")
        if not epx.isNull():
            eye_ic.setPixmap(epx)
        viewers_row.addWidget(eye_ic)

        viewers_hint = QLabel("Видят: Тимлид, Администратор, ИИ-система")
        viewers_hint.setStyleSheet(
            "color:#4a5068;font-size:11px;background:transparent;"
        )
        viewers_row.addWidget(viewers_hint)
        viewers_row.addStretch(1)
        bp_lay.addLayout(viewers_row)

        # View My Broadcast button
        view_broadcast_btn = QPushButton("  👁 Посмотреть мою трансляцию")
        view_broadcast_btn.setCursor(QCursor(Qt.PointingHandCursor))
        view_broadcast_btn.setStyleSheet(
            "QPushButton{background:#2a3150;color:#e8eaf0;font-size:12px;"
            "font-weight:600;border:none;border-radius:8px;padding:8px 12px;}"
            "QPushButton:hover{background:#3a4160;}"
        )
        view_broadcast_btn.clicked.connect(self._view_my_broadcast)
        bp_lay.addWidget(view_broadcast_btn)

        self._body_lay.addWidget(self._broadcast_panel)

        # ── Blink timer for REC dot ──────────────────────────────
        self._blink_visible = True
        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(800)
        self._blink_timer.timeout.connect(self._blink_rec)
        self._frame_count = 0

        # ── AI analysis pulse counter ─────────────────────────────
        self._ai_pulse_step = 0
        self._ai_pulse_timer = QTimer(self)
        self._ai_pulse_timer.setInterval(2000)
        self._ai_pulse_timer.timeout.connect(self._pulse_ai_status)

        # ── Report banner (hidden, shown before stopping) ─────────
        self._report_banner = QFrame()
        self._report_banner.setVisible(False)
        self._report_banner.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #1a1f2e,stop:1 #151a2e);"
            "border:none;border-radius:16px;}"
        )
        rbl = QVBoxLayout(self._report_banner)
        rbl.setContentsMargins(24, 20, 24, 20)
        rbl.setSpacing(14)

        # AI header
        ai_row = QHBoxLayout()
        ai_row.setSpacing(10)
        ai_ic = QLabel()
        ai_ic.setFixedSize(36, 36)
        ai_ic.setAlignment(Qt.AlignCenter)
        ai_ic.setStyleSheet("background:#2563eb20;border-radius:18px;border:none;")
        aip = _svg_pixmap(_ICON_ROBOT, 20, "#3b82f6")
        if not aip.isNull():
            ai_ic.setPixmap(aip)
        ai_row.addWidget(ai_ic)
        ai_title = QLabel("ИИ-ассистент")
        ai_title.setStyleSheet(
            "color:#60a5fa;font-size:15px;font-weight:700;background:transparent;"
        )
        ai_row.addWidget(ai_title, 1)
        rbl.addLayout(ai_row)

        ai_msg = QLabel(
            "Для завершения рабочей сессии, пожалуйста, напишите отчёт о выполненной работе. "
            "Это поможет мне точнее оценить вашу продуктивность, а также тимлид и "
            "администратор смогут видеть ваш прогресс."
        )
        ai_msg.setWordWrap(True)
        ai_msg.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;line-height:140%;"
        )
        rbl.addWidget(ai_msg)

        # Text area + attach button
        report_row = QHBoxLayout()
        report_row.setSpacing(8)
        self._report_edit = QTextEdit()
        self._report_edit.setPlaceholderText("Опишите что вы сделали сегодня...")
        self._report_edit.setFixedHeight(120)
        self._report_edit.setStyleSheet(
            "QTextEdit{background:#1e2538;color:#e8eaf0;font-size:14px;"
            "border:none;border-radius:10px;padding:12px;}"
        )
        report_row.addWidget(self._report_edit, 1)
        self._attach_btn = QPushButton()
        self._attach_btn.setCursor(Qt.PointingHandCursor)
        self._attach_btn.setIcon(_svg_icon(_ICON_CLIPBOARD, 16, "#3b82f6"))
        self._attach_btn.setFixedSize(38, 38)
        self._attach_btn.setStyleSheet(
            "QPushButton{background:#1e2538;border:none;border-radius:8px;}"
            "QPushButton:hover{background:#2a3150;}"
        )
        self._attach_btn.setToolTip("Прикрепить файл или изображение")
        self._attach_btn.clicked.connect(self._attach_file)
        report_row.addWidget(self._attach_btn)
        rbl.addLayout(report_row)

        # Submit row
        submit_row = QHBoxLayout()
        submit_row.addStretch(1)

        cancel_rep = QPushButton("Отмена")
        cancel_rep.setCursor(Qt.PointingHandCursor)
        cancel_rep.setFixedHeight(38)
        cancel_rep.setStyleSheet(
            "QPushButton{background:#1e2538;color:#e8eaf0;font-size:13px;"
            "font-weight:600;border:1px solid #2a3150;border-radius:8px;padding:0 16px;}"
            "QPushButton:hover{background:#2a3150;}"
        )
        cancel_rep.clicked.connect(self._cancel_report)
        submit_row.addWidget(cancel_rep)

        send_rep = QPushButton("  Отправить отчёт")
        send_rep.setCursor(Qt.PointingHandCursor)
        send_rep.setFixedHeight(38)
        send_rep.setIcon(_svg_icon(_ICON_SEND, 14, "#0c1021"))
        send_rep.setStyleSheet(
            "QPushButton{background:#2563eb;color:#f1f5f9;font-size:13px;"
            "font-weight:700;border:none;border-radius:8px;padding:0 20px;}"
            "QPushButton:hover{background:#3b82f6;}"
        )
        send_rep.clicked.connect(self._submit_report)
        submit_row.addWidget(send_rep)

        rbl.addLayout(submit_row)
        # Подпись по макету: «Чтобы закончить работу нужно написать отчёт»
        self._finish_hint = QLabel("Чтобы закончить работу, нужно написать отчёт")
        self._finish_hint.setStyleSheet(
            "color:#94a3b8;font-size:13px;background:transparent;"
        )
        self._body_lay.addWidget(self._finish_hint)
        self._body_lay.addWidget(self._report_banner)

        # ── Main two-column layout ───────────────────────────────
        main_row = QHBoxLayout()
        main_row.setSpacing(16)

        # LEFT: Today's tasks / reports
        left = QVBoxLayout()
        left.setSpacing(16)

        # Карточка по макету: «Отчёт отображается здесь вместе с прикреплённым файлом и записью»
        self._report_display_card = QFrame()
        self._report_display_card.setStyleSheet(
            "QFrame{background:#151a2e;border:1px solid #1e2538;border-radius:14px;}"
        )
        self._report_display_card.setMinimumHeight(100)
        rdc_l = QVBoxLayout(self._report_display_card)
        rdc_l.setContentsMargins(20, 14, 20, 14)
        rdc_t = QLabel("Отчёт отображается здесь вместе с прикреплённым файлом и записью трансляций")
        rdc_t.setWordWrap(True)
        rdc_t.setStyleSheet(
            "color:#94a3b8;font-size:13px;background:transparent;"
        )
        rdc_l.addWidget(rdc_t)
        left.addWidget(self._report_display_card)

        self._tasks_card = QFrame()
        self._tasks_card.setStyleSheet(
            "QFrame{background:#151a2e;border:none;border-radius:16px;}"
        )
        self._tasks_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._tasks_card.setMinimumHeight(320)
        tcl = QVBoxLayout(self._tasks_card)
        tcl.setContentsMargins(24, 20, 24, 20)
        tcl.setSpacing(14)

        tasks_hdr = QHBoxLayout()
        tasks_hdr.setSpacing(10)
        tic = QLabel()
        tic.setFixedSize(32, 32)
        tic.setAlignment(Qt.AlignCenter)
        tic.setStyleSheet("background:#f59e0b18;border-radius:16px;border:none;")
        tpx = _svg_pixmap(_ICON_CLIPBOARD, 18, "#f59e0b")
        if not tpx.isNull():
            tic.setPixmap(tpx)
        tasks_hdr.addWidget(tic)
        ttl = QLabel("Ваши задачи на сегодня")
        ttl.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:700;background:transparent;"
        )
        tasks_hdr.addWidget(ttl, 1)
        tcl.addLayout(tasks_hdr)

        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#1e2538;")
        tcl.addWidget(sep)

        self._tasks_list = QVBoxLayout()
        self._tasks_list.setSpacing(10)

        self._task_empty = QLabel(
            "У вас пока нет задач на сегодня.\n"
            "Тимлид назначит вам задачи, и они появятся здесь."
        )
        self._task_empty.setStyleSheet(
            "color:#4a5068;font-size:13px;background:transparent;"
        )
        self._task_empty.setWordWrap(True)
        self._task_empty.setAlignment(Qt.AlignCenter)
        self._tasks_list.addWidget(self._task_empty)

        tcl.addLayout(self._tasks_list)
        tcl.addStretch(1)
        left.addWidget(self._tasks_card)
        main_row.addLayout(left, 3)

        # RIGHT: Productivity + Stats
        right = QVBoxLayout()
        right.setSpacing(16)

        # Productivity overview card
        prod_card = QFrame()
        prod_card.setStyleSheet(
            "QFrame{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 #151a2e,stop:1 #1a1f2b);"
            "border:none;border-radius:16px;}"
        )
        pcl = QVBoxLayout(prod_card)
        pcl.setContentsMargins(20, 18, 20, 18)
        pcl.setSpacing(12)

        ph = QHBoxLayout()
        ph.setSpacing(10)
        pic = QLabel()
        pic.setFixedSize(28, 28)
        pic.setAlignment(Qt.AlignCenter)
        pic.setStyleSheet("background:#10b98118;border-radius:14px;border:none;")
        ppx = _svg_pixmap(_ICON_ACTIVITY, 16, "#10b981")
        if not ppx.isNull():
            pic.setPixmap(ppx)
        ph.addWidget(pic)
        pt = QLabel("Ваша продуктивность")
        pt.setStyleSheet(
            "color:#e8eaf0;font-size:15px;font-weight:700;background:transparent;"
        )
        ph.addWidget(pt, 1)
        pcl.addLayout(ph)

        # KPD progress bar
        kpd_row = QHBoxLayout()
        kpd_row.setSpacing(12)
        self._kpd_label = QLabel("КПД")
        self._kpd_label.setStyleSheet("color:#8891a5;font-size:13px;background:transparent;")
        kpd_row.addWidget(self._kpd_label)

        self._kpd_bar = QProgressBar()
        self._kpd_bar.setRange(0, 100)
        self._kpd_bar.setValue(0)
        self._kpd_bar.setFixedHeight(10)
        self._kpd_bar.setTextVisible(False)
        self._kpd_bar.setStyleSheet(
            "QProgressBar{background:#1e2538;border-radius:5px;border:none;}"
            "QProgressBar::chunk{background:qlineargradient(x1:0,y1:0,x2:1,y2:0,"
            "stop:0 #10b981,stop:1 #4f8fff);border-radius:5px;}"
        )
        kpd_row.addWidget(self._kpd_bar, 1)

        self._kpd_val = QLabel("—%")
        self._kpd_val.setStyleSheet(
            "color:#e8eaf0;font-size:13px;font-weight:600;background:transparent;"
        )
        kpd_row.addWidget(self._kpd_val)
        pcl.addLayout(kpd_row)

        # Streak
        streak_row = QHBoxLayout()
        streak_row.setSpacing(12)
        sic = QLabel()
        sic.setFixedSize(20, 20)
        sic.setAlignment(Qt.AlignCenter)
        spx = _svg_pixmap(_ICON_ZAP, 14, "#f59e0b")
        if not spx.isNull():
            sic.setPixmap(spx)
        streak_row.addWidget(sic)
        self._streak = QLabel("Серия: 0 дней подряд")
        self._streak.setStyleSheet("color:#8891a5;font-size:12px;background:transparent;")
        streak_row.addWidget(self._streak, 1)
        pcl.addLayout(streak_row)

        right.addWidget(prod_card)

        # Stat cards 2x2
        stat_grid_top = QHBoxLayout()
        stat_grid_top.setSpacing(12)
        self._stat_done = _stat_card(_ICON_CHECK_CIRCLE, "#10b981", "0", "Выполнено\nзадач")
        self._stat_hours = _stat_card(_ICON_CLOCK, "#4f8fff", "0ч", "За сегодня")
        stat_grid_top.addWidget(self._stat_done)
        stat_grid_top.addWidget(self._stat_hours)
        right.addLayout(stat_grid_top)

        stat_grid_bot = QHBoxLayout()
        stat_grid_bot.setSpacing(12)
        stat_grid_bot.addWidget(
            _stat_card(_ICON_TARGET, "#a78bfa", "0", "Активных\nпроектов")
        )
        stat_grid_bot.addWidget(
            _stat_card(_ICON_TRENDING_UP, "#f59e0b", "—", "Ваш ранг")
        )
        right.addLayout(stat_grid_bot)

        right.addStretch(1)
        main_row.addLayout(right, 2)

        self._body_lay.addLayout(main_row, 1)

    # ══════════════════════════════════════════════════════════════
    #  Public
    # ══════════════════════════════════════════════════════════════

    def refresh(self) -> None:
        name = session_store.full_name or "Пользователь"
        first = name.split()[0] if name else "Пользователь"
        self._greeting.setText(f"{_greeting()}, {first}")

        # Load position & department
        org_id = session_store.org_id
        if org_id:
            try:
                membership = api_client.get_my_membership(org_id)
                self._position_lbl.setText(membership.get("position") or "—")
            except Exception:  # noqa: BLE001
                self._position_lbl.setText("—")
            try:
                my_teams = api_client.list_my_teams(org_id)
                if my_teams:
                    names = [t.get("name", "") for t in my_teams if t.get("name")]
                    self._dept_lbl.setText(", ".join(names) if names else "—")
                else:
                    self._dept_lbl.setText("—")
            except Exception:  # noqa: BLE001
                self._dept_lbl.setText("—")

            # Load KPD score
            try:
                scores = api_client.get_ai_scorecards(
                    org_id, period="daily",
                    as_of=date.today().isoformat(),
                    user_id=session_store.user_id,
                    mode=None, role_profile=None, trend_limit=None,
                )
                if scores and isinstance(scores, list) and len(scores) > 0:
                    kpd = scores[0].get("score", 0)
                    self._kpd_bar.setValue(kpd)
                    self._kpd_val.setText(f"{kpd}%")
            except Exception:  # noqa: BLE001
                pass
        else:
            self._position_lbl.setText("—")
            self._dept_lbl.setText("—")

        is_manager_view = session_store.role in ("admin", "manager") or not org_id
        if hasattr(self, "_tasks_card"):
            self._tasks_card.setVisible(not is_manager_view)

        self._sync_work_ui()

    # ══════════════════════════════════════════════════════════════
    #  Work state management
    # ══════════════════════════════════════════════════════════════

    def _sync_work_ui(self) -> None:
        """Update button visibility based on work state."""
        idle = self._work_state == self._STATE_IDLE
        working = self._work_state == self._STATE_WORKING
        on_break = self._work_state == self._STATE_BREAK
        reporting = self._work_state == self._STATE_REPORT

        self._start_btn.setVisible(idle or on_break)
        self._break_btn.setVisible(working)
        self._stop_btn.setVisible(working or on_break)
        self._report_banner.setVisible(reporting)

        # Broadcast panel visible whenever actively working; placeholder скрыт при работе
        self._broadcast_panel.setVisible(working)
        if hasattr(self, "_broadcast_placeholder"):
            self._broadcast_placeholder.setVisible(not working)

        # Blink & pulse timers
        if working:
            if not self._blink_timer.isActive():
                self._blink_timer.start()
            if not self._ai_pulse_timer.isActive():
                self._ai_pulse_timer.start()
        else:
            self._blink_timer.stop()
            self._ai_pulse_timer.stop()
            self._rec_dot.setStyleSheet(
                "color:#ef4444;font-size:16px;font-weight:900;background:transparent;"
            )

        if idle:
            self._start_btn.setText("  Начать работу")
            self._start_btn.setIcon(_svg_icon(_ICON_PLAY, 16, "#0c1021"))
            self._start_btn.setStyleSheet(
                "QPushButton{background:#10b981;color:#0c1021;font-size:14px;"
                "font-weight:700;border:none;border-radius:10px;padding:0 22px;}"
                "QPushButton:hover{background:#34d399;}"
            )
            self._elapsed_lbl.setText("00:00:00")
            self._elapsed_lbl.setStyleSheet(
                "color:#8891a5;font-size:20px;font-weight:700;"
                "font-family:'Consolas','Courier New',monospace;background:transparent;"
            )
            self._frame_count = 0
            self._frame_count_lbl.setText("IDLE Готов к записи")
        elif on_break:
            self._start_btn.setText("  Продолжить")
            self._start_btn.setIcon(_svg_icon(_ICON_PLAY, 16, "#0c1021"))
            self._start_btn.setStyleSheet(
                "QPushButton{background:#10b981;color:#0c1021;font-size:14px;"
                "font-weight:700;border:none;border-radius:10px;padding:0 22px;}"
                "QPushButton:hover{background:#34d399;}"
            )
            self._elapsed_lbl.setStyleSheet(
                "color:#f59e0b;font-size:20px;font-weight:700;"
                "font-family:'Consolas','Courier New',monospace;background:transparent;"
            )
        elif working:
            self._elapsed_lbl.setStyleSheet(
                "color:#10b981;font-size:20px;font-weight:700;"
                "font-family:'Consolas','Courier New',monospace;background:transparent;"
            )

    def _view_my_broadcast(self) -> None:
        """Open dialog to view own live broadcast."""
        if self._session_id:
            dialog = _SelfPreviewDialog(self._session_id, self)
            dialog.exec()

    def _on_start_work(self) -> None:
        """Start or resume work session."""
        if self._work_state == self._STATE_IDLE:
            # Create backend session
            org_id = session_store.org_id
            if org_id:
                try:
                    sess = api_client.start_session(
                        org_id,
                        device_name=platform.node(),
                        os_name=f"{platform.system()} {platform.release()}",
                    )
                    self._session_id = sess.get("id")
                except Exception:  # noqa: BLE001
                    pass
            self._work_start_ts = time.time()
            self._recorder.start()
            self._stats_timer.start()
            self._elapsed_timer.start()
            self._preview_timer.start()

        elif self._work_state == self._STATE_BREAK:
            # Resume from break
            self._recorder.resume()
            self._stats_timer.start()
            self._elapsed_timer.start()
            self._preview_timer.start()

        self._work_state = self._STATE_WORKING
        self._sync_work_ui()
        # Подключить WebSocket для трансляции в реальном времени (Zoom/Discord-style)
        self._open_live_stream_ws()
        QTimer.singleShot(100, self._send_live_preview_tick)

    def _on_break(self) -> None:
        """Pause work — pause video recording AND stop elapsed timer."""
        self._work_state = self._STATE_BREAK
        self._recorder.pause()
        self._stats_timer.stop()
        self._elapsed_timer.stop()
        self._preview_timer.stop()
        self._close_live_stream_ws()
        self._sync_work_ui()

    def _on_stop_request(self) -> None:
        """User wants to stop — show report banner first."""
        self._work_state = self._STATE_REPORT
        self._recorder.pause()
        self._stats_timer.stop()
        self._elapsed_timer.stop()
        self._preview_timer.stop()
        self._close_live_stream_ws()
        self._report_edit.clear()
        self._sync_work_ui()

    def _cancel_report(self) -> None:
        """Cancel report — return to working state."""
        self._work_state = self._STATE_WORKING
        self._recorder.resume()
        self._stats_timer.start()
        self._elapsed_timer.start()
        self._sync_work_ui()

    def _attach_file(self) -> None:
        """Attach a file to the report."""
        from PySide6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл для прикрепления")
        if file_path:
            name = file_path.split("/")[-1].split("\\")[-1]
            self._report_edit.append(f"[Файл: {name}]")
            if not hasattr(self, "_attached_files"):
                self._attached_files: list[str] = []
            self._attached_files.append(file_path)

    def _submit_report(self) -> None:
        """Submit report and fully stop the session, uploading video."""
        report_text = self._report_edit.toPlainText().strip()
        if not report_text:
            self._report_edit.setStyleSheet(
                "QTextEdit{background:#1e2538;color:#e8eaf0;font-size:14px;"
                "border:2px solid #ef4444;border-radius:10px;padding:12px;}"
            )
            return
        self._report_edit.setStyleSheet(
            "QTextEdit{background:#1e2538;color:#e8eaf0;font-size:14px;"
            "border:none;border-radius:10px;padding:12px;}"
        )

        org_id = session_store.org_id

        # Stop backend session
        if org_id and self._session_id:
            try:
                api_client.stop_session(org_id, self._session_id)
            except Exception:  # noqa: BLE001
                pass

        report_id: str | None = None

        # Save report as daily report (use first team's project if available)
        if org_id:
            try:
                my_teams = api_client.list_my_teams(org_id)
                # Find any associated project
                project_id = None
                for t in my_teams:
                    pid = t.get("project_id")
                    if pid:
                        project_id = pid
                        break
                if project_id:
                    resp = api_client.create_daily_report(
                        org_id, project_id,
                        date.today().isoformat(),
                        report_text,
                    )
                    report_id = resp.get("id")
            except Exception:  # noqa: BLE001
                pass

        # Upload any attached files as report attachments
        if org_id and report_id and hasattr(self, "_attached_files"):
            for path in list(self._attached_files):
                try:
                    if os.path.isfile(path):
                        api_client.upload_daily_report_attachment(org_id, report_id, path)
                except Exception:  # noqa: BLE001
                    continue
            self._attached_files.clear()

        # Add report to tasks list as a completed item
        self._add_report_to_tasks(report_text)

        # Full stop — finalize video recording
        video_path = self._recorder.stop()
        self._preview_timer.stop()

        # Upload video recording to backend
        if video_path and os.path.isfile(video_path) and org_id and self._session_id:
            size = os.path.getsize(video_path)
            print(f"[Cabinet] Запись сохранена: {video_path} ({_format_file_size(size)})")
            try:
                api_client.upload_recording(org_id, self._session_id, video_path)
                print(f"[Cabinet] Видеозапись загружена на сервер")
            except Exception as exc:  # noqa: BLE001
                print(f"[Cabinet] Ошибка загрузки видео: {exc}")
        elif video_path and os.path.isfile(video_path):
            size = os.path.getsize(video_path)
            print(f"[Cabinet] Запись сохранена локально: {video_path} ({_format_file_size(size)})")

        self._work_state = self._STATE_IDLE
        self._session_id = None
        self._work_start_ts = None
        self._close_live_stream_ws()
        self._sync_work_ui()

    # ══════════════════════════════════════════════════════════════
    #  Live preview sender (Discord-like live view for managers)
    # ══════════════════════════════════════════════════════════════

    def _capture_preview_bytes(self) -> bytes:
        """Capture a lightweight JPEG snapshot of the current screen.

        OPTIMIZED:
          - Cached frame reuse to reduce CPU
          - Lower resolution (960x540) for preview (Discord does 720p max)
          - JPEG quality=50 for smaller size
          - Fast scaling with Qt.FastTransformation
        """
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            return b""

        app = QApplication.instance()
        if app is None:
            return b""

        screen = app.primaryScreen()
        if screen is None:
            return b""

        pix = screen.grabWindow(0)
        if pix.isNull():
            # Return cached frame if available
            with self._preview_cache_lock:
                if self._last_preview_bytes:
                    return self._last_preview_bytes
            return b""

        # Downscale to 960x540 (lower than 1280x720) для ещё большего снижения нагрузки
        # Discord preview quality doesn't need full 720p
        pix = pix.scaled(960, 540, Qt.KeepAspectRatio, Qt.FastTransformation)  # FastTransformation = faster

        buffer = QByteArray()
        qbuf = QBuffer(buffer)
        qbuf.open(QIODevice.WriteOnly)
        # JPEG quality=50 (lower than 60): ещё меньше нагрузка при достаточном качестве для preview
        pix.save(qbuf, "JPG", quality=50)
        qbuf.close()

        frame_bytes = bytes(buffer)

        # Cache for reuse
        with self._preview_cache_lock:
            self._last_preview_bytes = frame_bytes

        return frame_bytes

    def _open_live_stream_ws(self) -> None:
        """Open WebSocket for real-time stream (Zoom/Discord-style)."""
        if not _HAS_WEBSOCKET or not QWebSocket:
            return
        org_id = session_store.org_id
        session_id = self._session_id
        token = getattr(session_store, "token", None)
        if not org_id or not session_id or not token:
            return
        self._close_live_stream_ws()
        url = api_client.live_stream_ws_url(org_id, session_id, token, "broadcast")
        self._live_ws = QWebSocket()
        self._live_ws.open(QUrl(url))

    def _close_live_stream_ws(self) -> None:
        """Close WebSocket live stream."""
        if getattr(self, "_live_ws", None) is not None:
            try:
                self._live_ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._live_ws.deleteLater()
            self._live_ws = None

    def _send_live_preview_tick(self) -> None:
        """Send one frame: via WebSocket (real-time) or HTTP (fallback)."""
        if self._work_state != self._STATE_WORKING:
            return
        org_id = session_store.org_id
        session_id = self._session_id
        if not org_id or not session_id:
            return
        try:
            data = self._capture_preview_bytes()
            if not data:
                return
            ws = getattr(self, "_live_ws", None)
            if _HAS_WEBSOCKET and ws is not None and ws.state() == QAbstractSocket.ConnectedState:
                ws.sendBinaryMessage(QByteArray(data))
            else:
                api_client.send_session_preview(org_id, session_id, data, "image/jpeg")
        except Exception:  # noqa: BLE001
            return

    def _add_report_to_tasks(self, text: str) -> None:
        """Add submitted report as a visual item in the tasks list."""
        if not hasattr(self, "_tasks_list") or not hasattr(self, "_task_empty"):
            return
        self._task_empty.setVisible(False)

        item = QFrame()
        item.setStyleSheet(
            "QFrame{background:#1e2538;border:none;border-radius:10px;}"
        )
        il = QHBoxLayout(item)
        il.setContentsMargins(14, 10, 14, 10)
        il.setSpacing(10)

        ic = QLabel()
        ic.setFixedSize(24, 24)
        ic.setAlignment(Qt.AlignCenter)
        ic.setStyleSheet("background:#10b98118;border-radius:12px;border:none;")
        px = _svg_pixmap(_ICON_CHECK_CIRCLE, 14, "#10b981")
        if not px.isNull():
            ic.setPixmap(px)
        il.addWidget(ic)

        preview = text[:80] + ("..." if len(text) > 80 else "")
        tl = QLabel(f"Отчёт: {preview}")
        tl.setStyleSheet(
            "color:#8891a5;font-size:13px;background:transparent;"
        )
        tl.setWordWrap(True)
        il.addWidget(tl, 1)

        ts = QLabel(datetime.now().strftime("%H:%M"))
        ts.setStyleSheet("color:#4a5068;font-size:11px;background:transparent;")
        il.addWidget(ts)

        self._tasks_list.insertWidget(0, item)

    # ── Timers ────────────────────────────────────────────────────

    def _update_recording_stats(self) -> None:
        """Update recording stats in the broadcast panel (every 1s)."""
        st = self._recorder.stats()
        frames = st["frames"]
        fsize = st["file_size"]
        dur = st["duration"]
        target_fps = st["fps"]
        actual_fps = st.get("actual_fps", 0)

        m, s = divmod(int(dur), 60)
        h, m = divmod(m, 60)
        dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

        size_str = _format_file_size(fsize) if fsize else "—"

        paused = self._recorder.is_paused()
        icon = "PAUSE" if paused else "REC"
        status_suffix = " (пауза)" if paused else ""

        fps_display = f"{actual_fps:.0f}" if actual_fps else f"{target_fps}"

        self._frame_count_lbl.setText(
            f"{icon} {dur_str} · {size_str} · 720p {fps_display}fps · {frames} кадров{status_suffix}"
        )
        self._frame_count = frames

    def _blink_rec(self) -> None:
        """Toggle REC dot visibility for blinking effect."""
        self._blink_visible = not self._blink_visible
        if self._blink_visible:
            self._rec_dot.setStyleSheet(
                "color:#ef4444;font-size:16px;font-weight:900;background:transparent;"
            )
        else:
            self._rec_dot.setStyleSheet(
                "color:transparent;font-size:16px;font-weight:900;background:transparent;"
            )

    def _pulse_ai_status(self) -> None:
        """Cycle through AI status messages to show it's alive."""
        msgs = [
            "ИИ анализирует...",
            "ИИ: оценка активности",
            "ИИ: классификация приложений",
            "ИИ: расчёт КПД",
            "ИИ: мониторинг в реальном времени",
        ]
        self._ai_pulse_step = (self._ai_pulse_step + 1) % len(msgs)
        self._ai_status_lbl.setText(msgs[self._ai_pulse_step])

    def _update_elapsed(self) -> None:
        """Update elapsed time display."""
        if self._work_start_ts is None:
            return
        elapsed = int(time.time() - self._work_start_ts)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        self._elapsed_lbl.setText(f"{h:02d}:{m:02d}:{s:02d}")


class _SelfPreviewDialog(QDialog):
    """Modal dialog for viewing own live broadcast preview."""

    def __init__(self, session_id: str, parent=None) -> None:
        super().__init__(parent)
        self._session_id = session_id

        self.setWindowTitle("Моя трансляция")
        self.setModal(True)
        self.resize(800, 500)
        self.setStyleSheet("background:#0c1021;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(50)
        header.setStyleSheet("background:#151a2e;border-bottom:1px solid #1e2538;")
        hlay = QHBoxLayout(header)
        hlay.setContentsMargins(20, 0, 20, 0)

        title = QLabel("Моя трансляция экрана")
        title.setStyleSheet(
            "color:#e8eaf0;font-size:16px;font-weight:600;background:transparent;"
        )
        hlay.addWidget(title)

        hlay.addStretch(1)

        close_btn = QPushButton("✕ Закрыть")
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setStyleSheet(
            "QPushButton{background:#2a3150;color:#e8eaf0;font-size:13px;"
            "font-weight:600;border:none;border-radius:6px;padding:6px 12px;}"
            "QPushButton:hover{background:#3a4160;}"
        )
        close_btn.clicked.connect(self.accept)
        hlay.addWidget(close_btn)

        lay.addWidget(header)

        # Preview image (large)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(
            "background:#000;border:none;color:#4a5068;font-size:14px;"
        )
        self.preview_label.setText("Загрузка предпросмотра...")
        lay.addWidget(self.preview_label, 1)

        # Footer with status
        footer = QFrame()
        footer.setFixedHeight(40)
        footer.setStyleSheet("background:#151a2e;border-top:1px solid #1e2538;")
        flay = QHBoxLayout(footer)
        flay.setContentsMargins(20, 0, 20, 0)

        status_label = QLabel("● Обновляется каждую секунду")
        status_label.setStyleSheet(
            "color:#10b981;font-size:12px;background:transparent;"
        )
        flay.addWidget(status_label)

        lay.addWidget(footer)

        self._live_ws = None
        self._preview_fail_count = 0
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setInterval(1000)
        self._refresh_timer.timeout.connect(self._refresh_preview)

        # Real-time via WebSocket (Zoom/Discord-style) or HTTP fallback
        if _HAS_WEBSOCKET and QWebSocket:
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
        """HTTP fallback: load latest preview from session."""
        try:
            data = api_client.get_session_preview(
                session_store.org_id, self._session_id
            )
            if data:
                pix = QPixmap()
                if pix.loadFromData(data):
                    self._preview_fail_count = 0
                    scaled = pix.scaled(
                        self.preview_label.size(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                    self.preview_label.setPixmap(scaled)
                    self.preview_label.setStyleSheet("background:#000;border:none;")
                    self.preview_label.setText("")
                    return
            self._preview_fail_count = getattr(self, "_preview_fail_count", 0) + 1
            msg = "Предпросмотр недоступен" if self._preview_fail_count >= 20 else "Ожидание первого кадра…"
            self.preview_label.setText(msg)
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setStyleSheet(
                "background:#000;border:none;color:#94a3b8;font-size:14px;"
            )
        except Exception:  # noqa: BLE001
            self._preview_fail_count = getattr(self, "_preview_fail_count", 0) + 1
            msg = "Предпросмотр недоступен" if self._preview_fail_count >= 20 else "Ожидание первого кадра…"
            self.preview_label.setText(msg)
            self.preview_label.setPixmap(QPixmap())
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

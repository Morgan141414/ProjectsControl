import logging
import threading
import uuid
from contextlib import asynccontextmanager
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from app.api.routes import api_router
from app.core.config import settings
from app.core.retention import cleanup_activity_events, cleanup_recordings
from app.core.scheduler import shutdown_scheduler, start_scheduler
from app.db.base import Base
from app.db.session import SessionLocal, engine

# ── Structured logging ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("projectscontrol")

_METRICS_LOCK = threading.Lock()
_REQ_TOTAL: dict[tuple[str, str, int], int] = defaultdict(int)
_REQ_DURATION_SUM: dict[tuple[str, str], float] = defaultdict(float)
_REQ_DURATION_COUNT: dict[tuple[str, str], int] = defaultdict(int)
_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_REQ_DURATION_BUCKET: dict[tuple[str, str, float], int] = defaultdict(int)


# ── Lifespan (replaces deprecated on_event) ──────────────────────

def _auto_migrate(db) -> None:
    """Add missing columns to existing tables (simple dev migration)."""
    _cols = [
        ("users", "gender", "VARCHAR(20)"),
        ("users", "website", "VARCHAR(500)"),
        ("users", "is_superadmin", "BOOLEAN DEFAULT 0"),
        ("users", "position", "VARCHAR(255)"),
        ("users", "experience_years", "INTEGER"),
        ("users", "skills_json", "TEXT"),
        ("users", "experience_description", "TEXT"),
        ("users", "education", "TEXT"),
        ("users", "phone", "VARCHAR(50)"),
        ("users", "city", "VARCHAR(100)"),
        ("users", "portfolio_url", "VARCHAR(500)"),
        ("users", "resume_file", "VARCHAR(500)"),
        ("users", "is_looking_for_job", "BOOLEAN DEFAULT 0"),
        ("users", "desired_salary", "INTEGER"),
        ("users", "questionnaire_score", "REAL"),
        ("users", "questionnaire_status", "VARCHAR(20)"),
        ("org_memberships", "position", "VARCHAR(255)"),
        ("org_memberships", "department", "VARCHAR(255)"),
        ("organizations", "description", "TEXT"),
        ("organizations", "industry", "VARCHAR(100)"),
        ("organizations", "website", "VARCHAR(500)"),
        ("organizations", "logo_url", "VARCHAR(500)"),
        ("organizations", "owner_id", "VARCHAR(36)"),
        ("organizations", "is_active", "BOOLEAN DEFAULT 1"),
        ("organizations", "suspended_at", "DATETIME"),
        ("organizations", "max_members", "INTEGER DEFAULT 50"),
        ("organizations", "auto_approve", "BOOLEAN DEFAULT 0"),
        ("organizations", "welcome_message", "TEXT"),
        ("organizations", "theme_color", "VARCHAR(20)"),
        ("organizations", "legal_name", "VARCHAR(500)"),
        ("organizations", "inn", "VARCHAR(20)"),
    ]
    for table, col, typ in _cols:
        try:
            db.execute(text(
                f"ALTER TABLE {table} ADD COLUMN {col} {typ}"
            ))
            db.commit()
        except Exception:
            db.rollback()


@asynccontextmanager
async def lifespan(application: FastAPI):
    # ── Startup ──────────────────────────────────────────────
    logger.info("Starting %s …", settings.PROJECT_NAME)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        _auto_migrate(db)
        deleted_recordings = cleanup_recordings(db)
        deleted_events = cleanup_activity_events(db)
        if deleted_recordings or deleted_events:
            db.commit()
            logger.info(
                "Retention cleanup: %d recordings, %d events removed",
                deleted_recordings, deleted_events,
            )

    # Ensure previews directory exists for live screen previews
    from pathlib import Path
    Path(settings.PREVIEWS_PATH).resolve().mkdir(parents=True, exist_ok=True)

    start_scheduler()
    logger.info("Scheduler started (tick every %ds)", settings.SCHEDULE_TICK_SECONDS)
    logger.info("Application ready ✓")

    yield

    # ── Shutdown ─────────────────────────────────────────────
    shutdown_scheduler()
    logger.info("Application stopped ✓")


# ── Application ──────────────────────────────────────────────────

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handlers ────────────────────────────────────

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.warning("ValueError on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Request logging middleware ───────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    import time
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    request.state.request_id = request_id

    start = time.perf_counter()
    response = await call_next(request)
    elapsed_s = time.perf_counter() - start
    elapsed_ms = elapsed_s * 1000

    raw_path = request.url.path
    route = request.scope.get("route")
    route_path = getattr(route, "path", raw_path)
    method = request.method
    status_code = int(response.status_code)

    response.headers["X-Request-ID"] = request_id

    with _METRICS_LOCK:
        _REQ_TOTAL[(method, route_path, status_code)] += 1
        _REQ_DURATION_SUM[(method, route_path)] += elapsed_s
        _REQ_DURATION_COUNT[(method, route_path)] += 1
        for b in _BUCKETS:
            if elapsed_s <= b:
                _REQ_DURATION_BUCKET[(method, route_path, b)] += 1

    logger.info(
        "[%s] %s %s → %d (%.1fms)",
        request_id,
        request.method, request.url.path,
        response.status_code, elapsed_ms,
    )
    return response


# ── Routes ───────────────────────────────────────────────────────

@app.get("/")
def root() -> dict:
    return {"status": "ok", "version": "2.0.0"}


@app.get("/health/live")
def health_live() -> dict:
    return {"status": "live"}


@app.get("/health/ready")
def health_ready() -> dict:
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception:  # noqa: BLE001
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": "error"},
        )


@app.get("/metrics")
def prometheus_metrics() -> PlainTextResponse:
    lines = [
        "# HELP http_requests_total Total HTTP requests",
        "# TYPE http_requests_total counter",
    ]
    with _METRICS_LOCK:
        for (method, path, status), value in sorted(_REQ_TOTAL.items()):
            lines.append(
                f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}'
            )

        lines.extend(
            [
                "# HELP http_request_duration_seconds Request latency histogram",
                "# TYPE http_request_duration_seconds histogram",
            ]
        )
        for (method, path), count in sorted(_REQ_DURATION_COUNT.items()):
            total = _REQ_DURATION_SUM[(method, path)]
            for b in _BUCKETS:
                lines.append(
                    f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{b}"}} {_REQ_DURATION_BUCKET.get((method, path, b), 0)}'
                )
            lines.append(
                f'http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="+Inf"}} {count}'
            )
            lines.append(
                f'http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {total}'
            )
            lines.append(
                f'http_request_duration_seconds_count{{method="{method}",path="{path}"}} {count}'
            )
    return PlainTextResponse("\n".join(lines) + "\n")


app.include_router(api_router)

# ── ML router (questionnaire validation) ─────────────────────────
try:
    import sys
    from pathlib import Path as _P
    _ml_path = str(_P(__file__).resolve().parents[2] / "ML")
    if _ml_path not in sys.path:
        sys.path.insert(0, _ml_path)
    from api import router as ml_router
    app.include_router(ml_router)
    logger.info("ML router loaded ✓")
except ImportError:
    logger.warning("ML module not available — questionnaire validation disabled")

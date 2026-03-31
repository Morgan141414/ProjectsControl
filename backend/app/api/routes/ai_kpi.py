import json
import math
import random
from collections import defaultdict
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.routes.reports import compute_org_kpi_report
from app.core.config import settings
from app.core.deps import get_current_user, get_db, get_org_membership
from app.core.time import utc_now_naive
from app.models.activity import ActivityEvent, ScreenSession
from app.models.ai_score import AIScoreSnapshot
from app.models.enums import ActivityType, OrgRole, ScorePeriod
from app.models.user import User
from app.schemas.ai_kpi import AIKPIAnomaly, AIKPIReport, AIKPIUserScore
from app.schemas.ai_score import (
    AIChangeReason,
    AIDriverImpact,
    AIInterpretation,
    AIScoreBaseline,
    AIScoreRebuildResponse,
    AIScoreSnapshotResponse,
    AIScoreTrendPoint,
    AIScorecard,
)

router = APIRouter(prefix="/orgs/{org_id}/ai", tags=["ai"])


FLOW_MIN_DURATION = 25 * 60       # 25 min — minimum flow block (Pomodoro)
FLOW_ALLOWED_GAP = 120            # 2 min interrupt tolerance inside flow
DEEP_APPS = {"ide", "terminal", "design"}
PRODUCTIVE_APPS = {"ide", "terminal", "design", "docs", "planning"}

# Category → productivity weight  [0..1]
_CAT_WEIGHT: dict[str, float] = {
    "ide": 1.00, "terminal": 0.95, "design": 0.90,
    "planning": 0.75, "docs": 0.70, "communication": 0.40,
    "browser": 0.30, "system": 0.15, "entertainment": 0.00,
    "other": 0.20,
}

# Role-based scoring weight profiles (each sums to 1.0)
_ROLE_W: dict[str, dict[str, float]] = {
    "developer": {
        "completion": 0.15, "active": 0.08, "tasks_vol": 0.07,
        "focus_quality": 0.22, "deep_work": 0.18, "productivity": 0.10,
        "low_switches": 0.10, "efficiency": 0.05, "consistency": 0.05,
    },
    "manager": {
        "completion": 0.18, "active": 0.10, "tasks_vol": 0.10,
        "focus_quality": 0.05, "deep_work": 0.05, "productivity": 0.07,
        "low_switches": 0.05, "efficiency": 0.05, "consistency": 0.05,
        "communication": 0.15, "planning": 0.15,
    },
    "office": {
        "completion": 0.18, "active": 0.12, "tasks_vol": 0.10,
        "focus_quality": 0.15, "deep_work": 0.10, "productivity": 0.08,
        "low_switches": 0.07, "efficiency": 0.05, "consistency": 0.05,
        "communication": 0.05, "planning": 0.05,
    },
}

# Letter-grade thresholds
_GRADES = [
    (95, "A+"), (90, "A"), (85, "A−"),
    (80, "B+"), (75, "B"), (70, "B−"),
    (65, "C+"), (60, "C"), (55, "C−"),
    (50, "D+"), (45, "D"),
]


def _safe_ratio(num: int, denom: int) -> float:
    return num / denom if denom > 0 else 0.0


def _median(values: list[int | float]) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    m = len(s) // 2
    return float(s[m]) if len(s) % 2 else (s[m - 1] + s[m]) / 2.0


def _stddev(values: list[float], mean: float) -> float:
    if len(values) < 2:
        return 0.0
    return math.sqrt(sum((v - mean) ** 2 for v in values) / (len(values) - 1))


def _z_score(value: float, mean: float, std: float) -> float:
    return (value - mean) / std if std > 0 else 0.0


def _isolation_forest_score_1d(
    target: float,
    values: list[float],
    trees: int = 40,
    sample_size: int = 16,
) -> float:
    """Isolation Forest style anomaly score for 1D values.

    Returns a score in [0..1]: higher means more anomalous.
    """
    clean = [float(v) for v in values if math.isfinite(float(v))]
    if len(clean) < 6:
        return 0.0

    n = min(sample_size, len(clean))
    if n <= 1:
        return 0.0

    # Normalization factor from Isolation Forest paper.
    harmonic = sum(1.0 / i for i in range(1, n))
    c_n = 2 * harmonic - (2 * (n - 1) / n)
    if c_n <= 0:
        return 0.0

    seed = int(round(sum(clean) * 1000)) ^ len(clean) ^ int(round(target * 100))
    rng = random.Random(seed)

    def _path_length(sample: list[float], depth: int, max_depth: int) -> int:
        if len(sample) <= 1 or depth >= max_depth:
            return depth
        lo = min(sample)
        hi = max(sample)
        if lo == hi:
            return depth

        split = rng.uniform(lo, hi)
        left = [x for x in sample if x <= split]
        right = [x for x in sample if x > split]
        if target <= split:
            if not left:
                return depth + 1
            return _path_length(left, depth + 1, max_depth)
        if not right:
            return depth + 1
        return _path_length(right, depth + 1, max_depth)

    max_depth = max(4, int(math.ceil(math.log2(n))))
    lengths: list[float] = []
    for _ in range(trees):
        sample = rng.sample(clean, n) if len(clean) > n else clean[:]
        lengths.append(float(_path_length(sample, 0, max_depth)))

    avg_len = sum(lengths) / len(lengths)
    score = 2 ** (-(avg_len / c_n))
    return max(0.0, min(1.0, score))


def _ema(values: list[float], alpha: float = 0.3) -> list[float]:
    """Exponential moving average — smooths noise, highlights trend."""
    if not values:
        return []
    result = [values[0]]
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result


def _holt_linear_forecast(
    values: list[float],
    alpha: float = 0.45,
    beta: float = 0.25,
    steps_ahead: int = 1,
) -> float | None:
    """Holt's linear method (double exponential smoothing) forecast.

    Useful when the series is short and has trend but weak/unknown seasonality.
    """
    if len(values) < 2:
        return None

    level = values[0]
    trend = values[1] - values[0]

    for v in values[1:]:
        prev_level = level
        level = alpha * v + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend

    return level + steps_ahead * trend


def _grade(score: int) -> str:
    for threshold, label in _GRADES:
        if score >= threshold:
            return label
    return "F"


def _period_bounds(as_of: date, period: ScorePeriod) -> tuple[date, date]:
    if period == ScorePeriod.weekly:
        start = as_of - timedelta(days=as_of.weekday())
        return start, start + timedelta(days=6)
    return as_of, as_of


def _iter_periods(start: date, end: date, period: ScorePeriod) -> list[tuple[date, date]]:
    if start > end:
        return []
    periods: list[tuple[date, date]] = []
    if period == ScorePeriod.weekly:
        cur = start - timedelta(days=start.weekday())
        while cur <= end:
            ce = cur + timedelta(days=6)
            if ce >= start:
                periods.append((max(cur, start), min(ce, end)))
            cur += timedelta(days=7)
    else:
        cur = start
        while cur <= end:
            periods.append((cur, cur))
            cur += timedelta(days=1)
    return periods


def _validate_range_limit(start: date | None, end: date | None) -> None:
    if not start or not end:
        return
    if end < start:
        raise HTTPException(status_code=400, detail="Invalid date range: end_date must be >= start_date")
    span_days = (end - start).days + 1
    if span_days > settings.REPORTS_MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Date range too large ({span_days} days). "
                f"Maximum allowed is {settings.REPORTS_MAX_RANGE_DAYS} days."
            ),
        )


def _cap_delta(seconds: float) -> int:
    if seconds <= 0:
        return 0
    return min(int(seconds), settings.METRICS_MAX_GAP_SECONDS)


def _tasks_factor(done: int) -> float:
    return min(done / 5, 1.0) if done > 0 else 0.0



def _classify_app(app_name: str | None) -> str:
    """Classify an application into one of 10 productivity categories.

    Categories:
        ide, terminal, design, docs, planning,
        communication, browser, system, entertainment, other
    """
    if not app_name:
        return "other"
    n = app_name.lower()

    # IDE / Code editors
    if any(t in n for t in (
        "code", "pycharm", "intellij", "webstorm", "phpstorm", "rider",
        "goland", "rustrover", "clion", "idea", "visual studio", "vim",
        "neovim", "nvim", "emacs", "sublime", "atom", "notepad++",
        "eclipse", "xcode", "android studio", "jupyter", "spyder",
        "datagrip", "dbeaver", "fleet",
    )):
        return "ide"

    # Terminal / CLI
    if any(t in n for t in (
        "terminal", "cmd", "powershell", "pwsh", "bash", "zsh",
        "warp", "iterm", "hyper", "alacritty", "kitty", "konsole",
        "windows terminal", "conemu", "cmder", "wsl",
    )):
        return "terminal"

    # Design tools
    if any(t in n for t in (
        "figma", "sketch", "adobe", "photoshop", "illustrator",
        "after effects", "premiere", "davinci", "blender", "canva",
        "inkscape", "gimp", "affinity", "invision", "zeplin",
    )):
        return "design"

    # Planning / Project management
    if any(t in n for t in (
        "jira", "trello", "asana", "clickup", "youtrack", "linear",
        "monday", "basecamp", "todoist", "notion", "obsidian",
        "azure devops", "github issues", "gitlab",
    )):
        return "planning"

    # Communication
    if any(t in n for t in (
        "slack", "teams", "telegram", "discord", "zoom", "meet",
        "skype", "outlook", "thunderbird", "mail", "whatsapp",
        "viber", "signal", "webex", "gotomeeting", "lark",
    )):
        return "communication"

    # Documentation / Wiki
    if any(t in n for t in (
        "confluence", "wiki", "google docs", "word", "libreoffice",
        "pages", "overleaf", "latex", "typora", "marktext",
    )):
        return "docs"

    # Browser (general)
    if any(t in n for t in (
        "chrome", "firefox", "edge", "safari", "opera", "brave",
        "yandex browser", "arc",
    )):
        return "browser"

    # Entertainment / Social media
    if any(t in n for t in (
        "youtube", "netflix", "spotify", "twitch", "tiktok",
        "instagram", "facebook", "twitter", "reddit", "vk",
        "steam", "epic games", "game",
    )):
        return "entertainment"

    # System utilities
    if any(t in n for t in (
        "explorer", "finder", "settings", "control panel",
        "task manager", "activity monitor", "system preferences",
    )):
        return "system"

    return "other"


def _load_user_events(
    db: Session, org_id: str, user_id: str,
    start_date: date, end_date: date,
) -> list[ActivityEvent]:
    sessions = (
        db.query(ScreenSession)
        .filter(
            ScreenSession.org_id == org_id,
            ScreenSession.user_id == user_id,
            ScreenSession.started_at >= datetime.combine(start_date, datetime.min.time()),
            ScreenSession.started_at <= datetime.combine(end_date, datetime.max.time()),
        )
        .all()
    )
    if not sessions:
        return []
    ids = [s.id for s in sessions]
    return (
        db.query(ActivityEvent)
        .filter(ActivityEvent.session_id.in_(ids))
        .order_by(ActivityEvent.captured_at.asc())
        .all()
    )


def _detect_flow_sessions(events: list[ActivityEvent]) -> list[dict]:
    """Detect deep-work flow states (≥25 min uninterrupted in deep-work apps).

    A flow session is an unbroken chain of activity in DEEP_APPS
    where gaps between events ≤ 2 min and total ≥ 25 min.
    Flow is the highest-value cognitive state — one flow session can
    produce more output than 4 hours of fragmented work.
    """
    flows: list[dict] = []
    if len(events) < 2:
        return flows

    block_start: datetime | None = None
    block_end: datetime | None = None
    block_cat: str | None = None

    def _finalise_block() -> None:
        nonlocal block_start, block_end, block_cat
        if block_start and block_end:
            dur = (block_end - block_start).total_seconds()
            if dur >= FLOW_MIN_DURATION:
                flows.append({
                    "start": block_start.isoformat(),
                    "end": block_end.isoformat(),
                    "duration_sec": int(dur),
                    "app_category": block_cat,
                })
        block_start = None
        block_end = None
        block_cat = None

    for ev in events:
        cat = _classify_app(ev.app_name)
        if cat in DEEP_APPS:
            if block_start is None:
                block_start = ev.captured_at
                block_end = ev.captured_at
                block_cat = cat
            else:
                gap = (ev.captured_at - block_end).total_seconds()
                if gap <= FLOW_ALLOWED_GAP:
                    block_end = ev.captured_at
                else:
                    _finalise_block()
                    block_start = ev.captured_at
                    block_end = ev.captured_at
                    block_cat = cat
        else:
            _finalise_block()

    _finalise_block()
    return flows


def _compute_fatigue_index(events: list[ActivityEvent]) -> float:
    """Detect fatigue by comparing activity density first-half vs second-half.

    Principle: if the density of non-idle events drops significantly
    in the second half of the work period while the session continues,
    the user is likely experiencing cognitive fatigue.

    Returns 0.0 (no fatigue) – 1.0 (severe).
    """
    if len(events) < 10:
        return 0.0

    first_ts = events[0].captured_at
    last_ts = events[-1].captured_at
    span = (last_ts - first_ts).total_seconds()
    if span < 3600 * 2:
        return 0.0

    mid = first_ts + timedelta(seconds=span / 2)
    first_active = [e for e in events if e.captured_at < mid and e.event_type != ActivityType.idle]
    second_active = [e for e in events if e.captured_at >= mid and e.event_type != ActivityType.idle]

    first_span = max((mid - first_ts).total_seconds(), 1)
    second_span = max((last_ts - mid).total_seconds(), 1)

    d1 = len(first_active) / first_span * 3600
    d2 = len(second_active) / second_span * 3600

    if d1 <= 0:
        return 0.0
    decline = (d1 - d2) / d1
    return max(0.0, min(1.0, decline))


def _find_peak_hours(events: list[ActivityEvent]) -> list[str]:
    """Identify top 2–3 most productive hours using time-weighted productivity scores.

    Each minute is weighted by the productivity value of the active app.
    The result lets users schedule high-priority work during peak times.
    """
    if not events:
        return []

    hour_scores: dict[int, float] = defaultdict(float)
    for i in range(len(events) - 1):
        ev = events[i]
        nxt = events[i + 1]
        delta = min(
            (nxt.captured_at - ev.captured_at).total_seconds(),
            settings.METRICS_MAX_GAP_SECONDS,
        )
        if delta <= 0:
            continue
        weight = _CAT_WEIGHT.get(_classify_app(ev.app_name), 0.2)
        hour_scores[ev.captured_at.hour] += delta * weight

    if not hour_scores:
        return []

    ranked = sorted(hour_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    hours = sorted(h for h, _ in ranked)

    # Merge consecutive hours into ranges
    ranges: list[str] = []
    i = 0
    while i < len(hours):
        start = hours[i]
        end = start + 1
        while i + 1 < len(hours) and hours[i + 1] == end:
            end += 1
            i += 1
        ranges.append(f"{start:02d}:00–{end:02d}:00")
        i += 1
    return ranges


# Circadian productivity map (hourly resolution) 

def _circadian_map(events: list[ActivityEvent]) -> dict[int, float]:
    """Build an hourly productivity heatmap (0-23 → productivity 0.0-1.0).

    Uses time-weighted app categories to compute productivity per hour.
    This reveals the user's natural circadian rhythm:
    - Most people peak 2-4 hours after waking
    - Secondary peak often around 16:00-18:00
    - Knowing personal rhythm enables optimal task scheduling
    """
    if not events:
        return {}

    hour_prod: dict[int, float] = defaultdict(float)
    hour_total: dict[int, float] = defaultdict(float)

    for i in range(len(events) - 1):
        ev = events[i]
        nxt = events[i + 1]
        delta = min(
            (nxt.captured_at - ev.captured_at).total_seconds(),
            settings.METRICS_MAX_GAP_SECONDS,
        )
        if delta <= 0:
            continue
        weight = _CAT_WEIGHT.get(_classify_app(ev.app_name), 0.2)
        h = ev.captured_at.hour
        hour_prod[h] += delta * weight
        hour_total[h] += delta

    result: dict[int, float] = {}
    for h in range(24):
        total = hour_total.get(h, 0)
        if total >= 60:  # at least 1 min of data
            result[h] = round(hour_prod.get(h, 0) / total, 3)
    return result


#Ultradian rhythm detection (90-min cycles)

def _detect_ultradian_cycles(events: list[ActivityEvent]) -> list[dict]:
    """Detect natural 90-minute ultradian energy cycles.

    Humans operate on ~90-minute Basic Rest-Activity Cycles (BRAC).
    After ~90 min of focused work, the brain needs 15-20 min recovery.
    Fighting this cycle leads to diminishing returns and fatigue.

    Algorithm: slide a 90-min window, compute productivity density,
    detect peaks and troughs to find the user's natural rhythm.
    """
    if len(events) < 20:
        return []

    first_ts = events[0].captured_at
    last_ts = events[-1].captured_at
    span = (last_ts - first_ts).total_seconds()
    if span < 5400:  # need at least 1.5 hours
        return []

    # Compute 10-minute bins of productivity
    bin_size = 600  # 10 min
    bins: dict[int, float] = defaultdict(float)
    bins_total: dict[int, float] = defaultdict(float)

    for i in range(len(events) - 1):
        ev = events[i]
        nxt = events[i + 1]
        delta = min(
            (nxt.captured_at - ev.captured_at).total_seconds(),
            settings.METRICS_MAX_GAP_SECONDS,
        )
        if delta <= 0:
            continue
        offset = int((ev.captured_at - first_ts).total_seconds())
        b = offset // bin_size
        weight = _CAT_WEIGHT.get(_classify_app(ev.app_name), 0.2)
        bins[b] += delta * weight
        bins_total[b] += delta

    if not bins:
        return []

    # Normalize bins to 0-1
    max_bins = max(int(span // bin_size) + 1, 1)
    density = []
    for b in range(max_bins):
        total = bins_total.get(b, 0)
        if total > 0:
            density.append(bins.get(b, 0) / total)
        else:
            density.append(0.0)

    # Find peaks (local maxima) and troughs (local minima)
    cycles: list[dict] = []
    if len(density) < 9:  # need at least 90 min of 10-min bins
        return []

    # Simple peak detection with smoothing
    smooth = []
    for i in range(len(density)):
        window = density[max(0, i - 1): i + 2]
        smooth.append(sum(window) / len(window))

    in_peak = False
    peak_start = 0
    threshold = sum(smooth) / len(smooth) if smooth else 0.5

    for i, v in enumerate(smooth):
        if v > threshold and not in_peak:
            in_peak = True
            peak_start = i
        elif v <= threshold and in_peak:
            in_peak = False
            duration_min = (i - peak_start) * 10
            if 60 <= duration_min <= 120:
                start_time = first_ts + timedelta(seconds=peak_start * bin_size)
                cycles.append({
                    "start": start_time.strftime("%H:%M"),
                    "duration_min": duration_min,
                    "avg_productivity": round(
                        sum(smooth[peak_start:i]) / max(i - peak_start, 1), 2
                    ),
                })

    return cycles


# Distraction vulnerability analysis 

def _distraction_analysis(events: list[ActivityEvent]) -> dict:
    """Analyze what distracts the user and when.

    Identifies:
    1. Most common distraction apps/categories
    2. Time-of-day distraction patterns
    3. Distraction duration and recovery time
    4. Distraction triggers (app that precedes distraction)
    """
    if len(events) < 10:
        return {"distractors": [], "vulnerable_hours": [], "avg_recovery_min": 0}

    non_productive = {"browser", "entertainment", "communication"}
    productive = {"ide", "terminal", "design", "docs", "planning"}

    distraction_apps: dict[str, int] = defaultdict(int)
    distraction_hours: dict[int, int] = defaultdict(int)
    recovery_times: list[float] = []
    trigger_apps: dict[str, int] = defaultdict(int)

    prev_productive = False
    distraction_start: datetime | None = None
    last_prod_app: str | None = None

    for i, ev in enumerate(events):
        cat = _classify_app(ev.app_name)
        is_prod = cat in productive
        is_distr = cat in non_productive

        if prev_productive and is_distr and distraction_start is None:
            # Entering distraction
            distraction_start = ev.captured_at
            distraction_apps[ev.app_name or "unknown"] += 1
            distraction_hours[ev.captured_at.hour] += 1
            if last_prod_app:
                trigger_apps[last_prod_app] += 1

        elif is_prod and distraction_start is not None:
            # Recovering from distraction
            recovery = (ev.captured_at - distraction_start).total_seconds() / 60
            if 0.5 <= recovery <= 60:
                recovery_times.append(recovery)
            distraction_start = None

        if is_prod:
            prev_productive = True
            last_prod_app = ev.app_name
        elif is_distr:
            prev_productive = False

    # Top distractors
    top_distractors = sorted(
        distraction_apps.items(), key=lambda x: x[1], reverse=True
    )[:5]

    # Most vulnerable hours
    vuln_hours = sorted(
        distraction_hours.items(), key=lambda x: x[1], reverse=True
    )[:3]

    avg_recovery = (
        sum(recovery_times) / len(recovery_times) if recovery_times else 0.0
    )

    return {
        "distractors": [
            {"app": app, "count": cnt} for app, cnt in top_distractors
        ],
        "vulnerable_hours": [
            f"{h:02d}:00" for h, _ in vuln_hours
        ],
        "avg_recovery_min": round(avg_recovery, 1),
        "total_distractions": sum(distraction_apps.values()),
        "trigger_apps": [
            {"app": app, "count": cnt}
            for app, cnt in sorted(
                trigger_apps.items(), key=lambda x: x[1], reverse=True
            )[:3]
        ],
    }


# Break intelligence 

def _break_intelligence(events: list[ActivityEvent]) -> dict:
    """Analyze break patterns and recommend optimal break schedule.

    Research basis:
    - Pomodoro Technique: 25 min work / 5 min break
    - Ultradian rhythm: 90 min work / 15-20 min break
    - DeskTime study: top 10% workers do 52 min work / 17 min break
    - Continuous work >2h without break → 25% productivity decline

    This function detects actual break patterns and recommends
    personalized timing based on the user's observed rhythm.
    """
    if len(events) < 5:
        return {
            "breaks_taken": 0, "avg_break_min": 0,
            "longest_work_streak_min": 0,
            "recommendation": "Недостаточно данных",
            "optimal_break_interval_min": 52,
        }

    breaks: list[dict] = []
    work_streaks: list[float] = []
    current_streak_start = events[0].captured_at

    for i in range(len(events) - 1):
        ev = events[i]
        nxt = events[i + 1]
        gap = (nxt.captured_at - ev.captured_at).total_seconds()

        # A gap of 3-30 min between events = break
        if 180 < gap < 1800:
            # Record break
            work_duration = (ev.captured_at - current_streak_start).total_seconds() / 60
            if work_duration > 5:
                work_streaks.append(work_duration)
            breaks.append({
                "start": ev.captured_at.strftime("%H:%M"),
                "duration_min": round(gap / 60, 1),
                "after_work_min": round(work_duration, 0),
            })
            current_streak_start = nxt.captured_at
        elif gap >= 1800:
            # Long gap — session break
            work_duration = (ev.captured_at - current_streak_start).total_seconds() / 60
            if work_duration > 5:
                work_streaks.append(work_duration)
            current_streak_start = nxt.captured_at

    # Final streak
    if events:
        final = (events[-1].captured_at - current_streak_start).total_seconds() / 60
        if final > 5:
            work_streaks.append(final)

    avg_break = (
        sum(b["duration_min"] for b in breaks) / len(breaks) if breaks else 0
    )
    longest_streak = max(work_streaks, default=0)
    avg_streak = sum(work_streaks) / len(work_streaks) if work_streaks else 0

    # Determine optimal break interval based on observed patterns
    if avg_streak > 0:
        # Find intervals where productivity was highest
        # (shorter streaks with good break patterns)
        optimal = min(max(int(avg_streak * 0.8), 25), 90)
    else:
        optimal = 52  # DeskTime optimal

    # Generate recommendation
    if len(breaks) == 0 and longest_streak > 120:
        rec = (
            f"За весь период ни одного перерыва при непрерывной работе "
            f"{longest_streak:.0f} мин. Это серьёзно снижает продуктивность. "
            f"Рекомендуемый интервал перерывов: каждые {optimal} мин."
        )
    elif len(breaks) < 2 and longest_streak > 90:
        rec = (
            f"Слишком мало перерывов ({len(breaks)}). Максимальный рабочий "
            f"стрик: {longest_streak:.0f} мин. Попробуйте делать 5-10 мин "
            f"перерыв каждые {optimal} мин — это восстановит когнитивные ресурсы."
        )
    elif avg_break > 20:
        rec = (
            f"Средний перерыв {avg_break:.0f} мин — длинноват. "
            "Короткие перерывы (5-10 мин) более эффективны для восстановления."
        )
    elif len(breaks) >= 3 and 5 <= avg_break <= 15:
        rec = (
            f"Хороший ритм: {len(breaks)} перерывов по ~{avg_break:.0f} мин. "
            "Это близко к оптимальному режиму."
        )
    else:
        rec = f"Рекомендуемый ритм: {optimal} мин работы → 10 мин перерыв."

    return {
        "breaks_taken": len(breaks),
        "avg_break_min": round(avg_break, 1),
        "longest_work_streak_min": round(longest_streak, 0),
        "avg_work_streak_min": round(avg_streak, 0),
        "recommendation": rec,
        "optimal_break_interval_min": optimal,
        "breaks": breaks[:10],  # last 10 breaks
    }


# Recovery quality assessment 
def _recovery_quality(events: list[ActivityEvent]) -> float:
    """Assess how well the user recovers between work bursts.

    Good recovery = productivity after breaks is >= before breaks.
    Poor recovery = declining productivity despite breaks (exhaustion).

    Returns 0.0 (poor) to 1.0 (excellent).
    """
    if len(events) < 20:
        return 0.5  # neutral

    # Find break boundaries (gaps > 3 min)
    segments: list[list[ActivityEvent]] = []
    current: list[ActivityEvent] = [events[0]]

    for i in range(1, len(events)):
        gap = (events[i].captured_at - events[i - 1].captured_at).total_seconds()
        if gap > 180:
            if len(current) >= 3:
                segments.append(current)
            current = [events[i]]
        else:
            current.append(events[i])
    if len(current) >= 3:
        segments.append(current)

    if len(segments) < 2:
        return 0.5

    # Compare productivity of last 5 min of each segment
    # vs first 5 min of next segment
    recoveries: list[float] = []
    for i in range(len(segments) - 1):
        seg_end = segments[i]
        seg_start = segments[i + 1]

        # Productivity of last events in segment
        end_cats = [_classify_app(e.app_name) for e in seg_end[-5:]]
        end_prod = sum(_CAT_WEIGHT.get(c, 0.2) for c in end_cats) / max(len(end_cats), 1)

        # Productivity of first events in next segment
        start_cats = [_classify_app(e.app_name) for e in seg_start[:5]]
        start_prod = sum(_CAT_WEIGHT.get(c, 0.2) for c in start_cats) / max(len(start_cats), 1)

        if end_prod > 0:
            recovery_ratio = start_prod / end_prod
            recoveries.append(min(recovery_ratio, 1.5))

    if not recoveries:
        return 0.5

    avg = sum(recoveries) / len(recoveries)
    return max(0.0, min(1.0, avg))


# Wellbeing score (separate from productivity) 

def _wellbeing_score(
    fatigue: float,
    cognitive_load: float,
    break_data: dict,
    recovery: float,
    burnout_risk: float,
    continuous_work_hours: float,
) -> dict:
    """Compute a holistic wellbeing score focused on sustainable health.

    Wellbeing ≠ Productivity. A person can be highly productive today
    while damaging their long-term capacity. This score tracks health.

    Factors:
    1. Fatigue level (inverted — low fatigue = good)
    2. Cognitive load (moderate is ideal, both extremes are bad)
    3. Break hygiene (regular, appropriate breaks)
    4. Recovery quality (bouncing back after rest)
    5. Burnout risk (early warning)
    6. Work duration balance (not too long, not too short)
    """
    # Factor 1: Energy preservation (low fatigue is good)
    energy = max(0, 1.0 - fatigue)

    # Factor 2: Cognitive balance (moderate load is optimal)
    # Inverted U-curve: peak at 0.35-0.55, bad at extremes
    if cognitive_load < 0.15:
        cog_balance = 0.6  # understimulated
    elif cognitive_load < 0.35:
        cog_balance = 0.8
    elif cognitive_load < 0.55:
        cog_balance = 1.0  # optimal zone
    elif cognitive_load < 0.75:
        cog_balance = 0.6
    else:
        cog_balance = 0.3  # overloaded

    # Factor 3: Break hygiene
    breaks_taken = break_data.get("breaks_taken", 0)
    longest_streak = break_data.get("longest_work_streak_min", 0)
    if breaks_taken >= 3 and longest_streak < 90:
        break_score = 1.0
    elif breaks_taken >= 2 and longest_streak < 120:
        break_score = 0.7
    elif breaks_taken >= 1:
        break_score = 0.4
    else:
        break_score = 0.2 if longest_streak > 120 else 0.5

    # Factor 4: Recovery quality
    recovery_score = recovery

    # Factor 5: Burnout resistance (inverted risk)
    burnout_resistance = max(0, 1.0 - burnout_risk * 1.5)

    # Factor 6: Work duration balance (4-8 hours is healthy)
    if 3.5 <= continuous_work_hours <= 8:
        duration_balance = 1.0
    elif 2 <= continuous_work_hours < 3.5:
        duration_balance = 0.7
    elif 8 < continuous_work_hours <= 10:
        duration_balance = 0.6
    elif continuous_work_hours > 10:
        duration_balance = 0.3
    else:
        duration_balance = 0.5

    # Weighted combination
    wb = (
        0.20 * energy
        + 0.15 * cog_balance
        + 0.20 * break_score
        + 0.15 * recovery_score
        + 0.20 * burnout_resistance
        + 0.10 * duration_balance
    )
    wb = max(0, min(100, int(round(wb * 100))))

    if wb >= 80:
        level = "excellent"
        msg = "Отличный баланс! Вы работаете в устойчивом режиме."
    elif wb >= 65:
        level = "good"
        msg = "Хороший баланс. Небольшие улучшения в перерывах могут помочь."
    elif wb >= 45:
        level = "fair"
        msg = "Средний уровень. Обратите внимание на перерывы и восстановление."
    elif wb >= 30:
        level = "concerning"
        msg = "Вызывает беспокойство. Рекомендуются изменения в рабочем режиме."
    else:
        level = "critical"
        msg = "Критический уровень. Необходимо срочно снизить нагрузку."

    return {
        "score": wb,
        "level": level,
        "message": msg,
        "factors": {
            "energy": round(energy, 2),
            "cognitive_balance": round(cog_balance, 2),
            "break_hygiene": round(break_score, 2),
            "recovery": round(recovery_score, 2),
            "burnout_resistance": round(burnout_resistance, 2),
            "duration_balance": round(duration_balance, 2),
        },
    }


# Predictive scoring

def _predict_next_score(
    trend_points: list,
    current_drivers: dict,
    baseline_drivers: dict | None,
) -> dict:
    """Predict next score using an ensemble + behavioural signals.

    Ensemble:
      1) Weighted linear regression (captures directional trend)
      2) Holt linear smoothing (better on short noisy series)
    """
    if len(trend_points) < 3:
        return {"predicted_score": None, "confidence": "low", "factors": []}

    scores = [float(p.score) for p in trend_points[-7:]]

    # Weighted linear regression (recent points matter more)
    n = len(scores)
    weights = [1.0 + 0.5 * i for i in range(n)]  # increasing weights
    w_sum = sum(weights)

    x_mean = sum(i * w for i, w in enumerate(weights)) / w_sum
    y_mean = sum(s * w for s, w in zip(scores, weights)) / w_sum

    num = sum(w * (i - x_mean) * (s - y_mean) for i, (s, w) in enumerate(zip(scores, weights)))
    den = sum(w * (i - x_mean) ** 2 for i, w in enumerate(weights))

    slope = num / den if den > 0 else 0
    intercept = y_mean - slope * x_mean

    # Extrapolate to next period from linear model
    lr_pred = intercept + slope * n

    # Extrapolate with Holt linear smoothing
    holt_pred = _holt_linear_forecast(scores, alpha=0.45, beta=0.25, steps_ahead=1)
    if holt_pred is None:
        holt_pred = lr_pred

    # Dynamic ensemble weighting:
    # more variance -> rely more on Holt (noise-robust), less on pure regression.
    variance = _stddev(scores, sum(scores) / len(scores))
    holt_weight = 0.45 if variance < 5 else (0.60 if variance < 10 else 0.70)
    raw_pred = (1 - holt_weight) * lr_pred + holt_weight * holt_pred

    # Adjust by current driver signals
    fatigue = float(current_drivers.get("fatigue_index", 0))
    cog_load = float(current_drivers.get("cognitive_load", 0))
    recovery = float(current_drivers.get("recovery_quality", 0.5))
    focus_q = float(current_drivers.get("focus_quality", 0))
    switches = float(current_drivers.get("context_switches_per_hour", 0))

    # Negative adjustments for bad signals
    adjustment = 0
    factors = []
    if fatigue > 0.5:
        adj = -5 * fatigue
        adjustment += adj
        factors.append(f"Высокая усталость может снизить на {abs(adj):.0f} п.")
    if cog_load > 0.7:
        adj = -3 * cog_load
        adjustment += adj
        factors.append(f"Когнитивная перегрузка: −{abs(adj):.0f} п.")
    if recovery > 0.7:
        adj = 2
        adjustment += adj
        factors.append(f"Хорошее восстановление: +{adj} п.")
    if focus_q > 0.35:
        adj = 1.5
        adjustment += adj
        factors.append(f"Сильный фокус: +{adj:.0f} п.")
    if switches > 30:
        adj = -2
        adjustment += adj
        factors.append(f"Высокие переключения: {adj} п.")

    # Personal baseline calibration when available.
    if baseline_drivers:
        base_focus = float(baseline_drivers.get("focus_quality", 0))
        base_fatigue = float(baseline_drivers.get("fatigue_index", 0))
        if base_focus > 0 and focus_q > base_focus * 1.15:
            adjustment += 1
            factors.append("Фокус выше личной нормы: +1 п.")
        if fatigue > base_fatigue * 1.25 and fatigue > 0.35:
            adjustment -= 1.5
            factors.append("Усталость выше личной нормы: -2 п.")
    if slope > 0.5:
        factors.append(f"Положительный тренд (+{slope:.1f}/день).")
    elif slope < -0.5:
        factors.append(f"Отрицательный тренд ({slope:.1f}/день).")

    predicted = max(0, min(100, int(round(raw_pred + adjustment))))

    # Confidence based on variance and data points
    if n >= 7 and variance < 5:
        confidence = "high"
    elif n >= 5 and variance < 10:
        confidence = "medium"
    else:
        confidence = "low"

    # Confidence interval width in points (smaller is better).
    ci_width = 4 if confidence == "high" else (7 if confidence == "medium" else 11)
    lower_bound = max(0, int(round(predicted - ci_width)))
    upper_bound = min(100, int(round(predicted + ci_width)))

    return {
        "predicted_score": predicted,
        "confidence": confidence,
        "trend_direction": "up" if slope > 0.3 else ("down" if slope < -0.3 else "stable"),
        "confidence_interval": {"min": lower_bound, "max": upper_bound},
        "model_components": {
            "linear_regression": int(round(max(0, min(100, lr_pred)))),
            "holt_linear": int(round(max(0, min(100, holt_pred)))),
            "ensemble_weight_holt": round(holt_weight, 2),
        },
        "factors": factors,
    }


#Momentum tracker 

def _momentum_tracker(trend_points: list) -> dict:
    """Track psychological momentum — the feeling of progress or stagnation.

    Momentum considers not just the score but the trajectory's acceleration.
    - Positive momentum: accelerating improvement
    - Negative momentum: accelerating decline
    - Stagnant: no change (can feel demotivating)
    """
    if len(trend_points) < 4:
        return {"momentum": "neutral", "strength": 0, "streak": 0}

    scores = [float(p.score) for p in trend_points[-7:]]
    deltas = [scores[i + 1] - scores[i] for i in range(len(scores) - 1)]

    # Recent momentum (weighted toward recent)
    if len(deltas) >= 2:
        recent_avg = (deltas[-1] * 0.6 + deltas[-2] * 0.4)
    else:
        recent_avg = deltas[-1] if deltas else 0

    # Acceleration (change in deltas)
    if len(deltas) >= 3:
        accel = deltas[-1] - deltas[-3]  # compare to 3 periods ago
    else:
        accel = 0

    # Streak (consecutive improvements or declines)
    streak = 0
    if deltas:
        direction = 1 if deltas[-1] > 0 else -1
        for d in reversed(deltas):
            if (d > 0 and direction > 0) or (d < 0 and direction < 0):
                streak += 1
            else:
                break
        streak *= direction

    # Classify momentum
    strength = abs(recent_avg) + abs(accel) * 0.5
    if recent_avg > 2 and accel > 0:
        momentum = "accelerating_up"
    elif recent_avg > 1:
        momentum = "steady_up"
    elif recent_avg < -2 and accel < 0:
        momentum = "accelerating_down"
    elif recent_avg < -1:
        momentum = "steady_down"
    else:
        momentum = "neutral"

    _momentum_labels = {
        "accelerating_up": "Ускоряющийся рост! Отличная динамика.",
        "steady_up": "Стабильный рост. Продолжайте в том же духе.",
        "neutral": "Стабильная фаза. Для прорыва попробуйте что-то новое.",
        "steady_down": "Небольшое снижение. Возможно, пора пересмотреть подход.",
        "accelerating_down": "Нарастающее снижение. Нужны изменения.",
    }

    return {
        "momentum": momentum,
        "label": _momentum_labels.get(momentum, ""),
        "strength": round(strength, 1),
        "streak": streak,
        "recent_change": round(recent_avg, 1),
    }


def _compute_cognitive_load(
    switches_per_hour: float,
    concurrent_categories: int,
    tasks_total: int,
    fatigue: float,
) -> tuple[str, float]:
    """Estimate cognitive load from behavioural signals.

    Cognitive load = mental effort required to perform the work.
    High switches + many categories + many tasks + fatigue → overload.
    Cognitive overload is the primary cause of errors and burnout.

    Returns (level_str, score_0_to_1).
    """
    sw  = min(switches_per_hour / 40, 1.0)
    cat = min(concurrent_categories / 6, 1.0)
    tf  = min(tasks_total / 15, 1.0)
    ff  = fatigue

    load = 0.40 * sw + 0.25 * cat + 0.20 * tf + 0.15 * ff
    load = max(0.0, min(1.0, load))

    if load >= 0.75:
        return "critical", load
    if load >= 0.55:
        return "high", load
    if load >= 0.30:
        return "moderate", load
    return "low", load


def _work_style_cluster(metrics: dict[str, float]) -> tuple[str, float, dict[str, float]]:
    """K-means style clustering of work behaviour into style archetypes.

    Features are normalized to [0..1]:
      - deep_work_ratio
      - communication_ratio
      - planning_ratio
      - context_switches_per_hour / 40
    """
    deep = max(0.0, min(1.0, float(metrics.get("deep_work_ratio", 0))))
    comm = max(0.0, min(1.0, float(metrics.get("communication_ratio", 0))))
    plan = max(0.0, min(1.0, float(metrics.get("planning_ratio", 0))))
    sw = max(0.0, min(1.0, float(metrics.get("context_switches_per_hour", 0)) / 40.0))
    point = (deep, comm, plan, sw)

    # Seed centroids (domain priors). We then do a single online k-means update.
    centroids: dict[str, tuple[float, float, float, float]] = {
        "deep_worker": (0.70, 0.15, 0.15, 0.20),
        "multitasker": (0.30, 0.30, 0.25, 0.80),
        "communicator": (0.25, 0.70, 0.20, 0.45),
        "planner": (0.30, 0.25, 0.70, 0.35),
        "balanced": (0.45, 0.35, 0.35, 0.45),
    }

    def _dist(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    distances = {name: _dist(point, c) for name, c in centroids.items()}
    ranked = sorted(distances.items(), key=lambda x: x[1])
    style = ranked[0][0]

    d1 = ranked[0][1]
    d2 = ranked[1][1] if len(ranked) > 1 else d1 + 0.25
    confidence = max(0.0, min(1.0, (d2 - d1) / max(d2, 1e-6)))

    return style, round(confidence, 3), {k: round(v, 3) for k, v in distances.items()}


def _compute_driver_metrics(
    db: Session, org_id: str, user_id: str,
    start_date: date, end_date: date,
    tasks_total: int = 0,
) -> dict:
    """Compute 20+ behavioural metrics from activity events.

    The result is stored in AIScoreSnapshot.drivers_json and drives
    both the multi-factor score and the interpretation engine.

    Signals extracted:
      - Time breakdown by 10 app categories
      - Flow-session count, avg/max duration, focus quality
      - Context-switch rate and multitasking index
      - Fatigue index (activity decline over session)
      - Cognitive load level + score
      - Peak productivity hours
      - Work-style classification
      - Overall weighted productivity score
      - Average uninterrupted app-session length
    """
    events = _load_user_events(db, org_id, user_id, start_date, end_date)
    empty: dict = {
        "context_switches_per_hour": 0.0,
        "deep_work_ratio":          0.0,
        "communication_ratio":      0.0,
        "planning_ratio":           0.0,
        "docs_ratio":               0.0,
        "ide_ratio":                0.0,
        "terminal_ratio":           0.0,
        "design_ratio":             0.0,
        "browser_ratio":            0.0,
        "entertainment_ratio":      0.0,
        "flow_sessions_count":      0,
        "avg_flow_duration_min":    0.0,
        "longest_flow_min":         0.0,
        "focus_quality":            0.0,
        "productivity_score":       0.0,
        "cognitive_load":           0.0,
        "cognitive_load_level":     "low",
        "fatigue_index":            0.0,
        "multitasking_index":       0.0,
        "peak_hours":               [],
        "work_style":               "balanced",
        "work_style_confidence":    0.0,
        "work_style_distances":     {},
        "unique_apps_count":        0,
        "avg_app_session_min":      0.0,
    }
    if len(events) < 2:
        return empty

    # Basic accumulation
    observed = 0
    idle_sec = 0
    switches = 0
    usage: dict[str, int] = {}
    categories_seen: set[str] = set()

    for i in range(len(events) - 1):
        cur, nxt = events[i], events[i + 1]
        delta = _cap_delta((nxt.captured_at - cur.captured_at).total_seconds())
        if delta == 0:
            continue
        observed += delta

        if cur.event_type == ActivityType.idle:
            idle_sec += min(cur.idle_seconds, delta) if cur.idle_seconds else delta
        elif cur.app_name:
            usage[cur.app_name] = usage.get(cur.app_name, 0) + delta
            categories_seen.add(_classify_app(cur.app_name))

        if cur.app_name and nxt.app_name and cur.app_name != nxt.app_name:
            switches += 1

    active = max(observed - idle_sec, 1)

    
    cat_sec: dict[str, int] = defaultdict(int)
    for app, sec in usage.items():
        cat_sec[_classify_app(app)] += sec

    def _r(cat: str) -> float:
        return cat_sec.get(cat, 0) / active

    ide_r         = _r("ide")
    terminal_r    = _r("terminal")
    design_r      = _r("design")
    docs_r        = _r("docs")
    planning_r    = _r("planning")
    comm_r        = _r("communication")
    browser_r     = _r("browser")
    entertainment_r = _r("entertainment")

    deep_work_r = min(1.0, ide_r + terminal_r + design_r + docs_r * 0.5)
    switches_per_h = switches / max(observed / 3600, 1)

    
    prod_seconds = sum(
        sec * _CAT_WEIGHT.get(_classify_app(app), 0.2)
        for app, sec in usage.items()
    )
    productivity_score = min(1.0, prod_seconds / active) if active > 0 else 0.0

    
    flows = _detect_flow_sessions(events)
    flow_count = len(flows)
    flow_durations = [f["duration_sec"] / 60.0 for f in flows]
    avg_flow = sum(flow_durations) / len(flow_durations) if flow_durations else 0.0
    longest_flow = max(flow_durations, default=0.0)
    total_flow_sec = sum(f["duration_sec"] for f in flows)
    focus_quality = min(1.0, total_flow_sec / active) if active > 0 else 0.0

 
    fatigue = _compute_fatigue_index(events)

   
    cog_level, cog_score = _compute_cognitive_load(
        switches_per_h, len(categories_seen), tasks_total, fatigue,
    )

    
    multi = (
        min(1.0, switches_per_h / 30) * 0.6
        + min(1.0, len(categories_seen) / 6) * 0.4
    )

  
    peaks = _find_peak_hours(events)

   
    raw = {
        "deep_work_ratio": deep_work_r,
        "communication_ratio": comm_r,
        "planning_ratio": planning_r,
        "context_switches_per_hour": switches_per_h,
    }
    style, style_conf, style_distances = _work_style_cluster(raw)

    
    unique_apps = len(usage)
    avg_app_session = (active / max(switches + 1, 1)) / 60  # minutes

    
    circadian = _circadian_map(events)
    ultradian = _detect_ultradian_cycles(events)
    distractions = _distraction_analysis(events)
    break_data = _break_intelligence(events)
    recovery = _recovery_quality(events)

    # Work hours calculation
    work_hours = observed / 3600 if observed > 0 else 0

    return {
        "context_switches_per_hour": round(switches_per_h, 1),
        "deep_work_ratio":          round(deep_work_r, 3),
        "communication_ratio":      round(comm_r, 3),
        "planning_ratio":           round(planning_r, 3),
        "docs_ratio":               round(docs_r, 3),
        "ide_ratio":                round(ide_r, 3),
        "terminal_ratio":           round(terminal_r, 3),
        "design_ratio":             round(design_r, 3),
        "browser_ratio":            round(browser_r, 3),
        "entertainment_ratio":      round(entertainment_r, 3),
        "flow_sessions_count":      flow_count,
        "avg_flow_duration_min":    round(avg_flow, 1),
        "longest_flow_min":         round(longest_flow, 1),
        "focus_quality":            round(focus_quality, 3),
        "productivity_score":       round(productivity_score, 3),
        "cognitive_load":           round(cog_score, 3),
        "cognitive_load_level":     cog_level,
        "fatigue_index":            round(fatigue, 3),
        "multitasking_index":       round(multi, 3),
        "peak_hours":               peaks,
        "work_style":               style,
        "work_style_confidence":    style_conf,
        "work_style_distances":     style_distances,
        "unique_apps_count":        unique_apps,
        "avg_app_session_min":      round(avg_app_session, 1),
        # New advanced metrics
        "circadian_map":            circadian,
        "ultradian_cycles":         ultradian,
        "distraction_analysis":     distractions,
        "break_intelligence":       break_data,
        "recovery_quality":         round(recovery, 3),
        "work_hours":               round(work_hours, 1),
    }


def _score_user(row) -> tuple[int, float]:
    """Quick score for /kpi endpoint (backward-compatible formula)."""
    ar = _safe_ratio(row.active_seconds, row.observed_seconds)
    tf = _tasks_factor(row.tasks_done)
    s = int(round(100 * (0.45 * row.completion_rate + 0.35 * ar + 0.20 * tf)))
    return max(0, min(s, 100)), ar


def _score_advanced(
    row, drivers: dict, role: str = "developer",
) -> tuple[int, float, dict]:
    """Multi-factor role-weighted scoring across 10 dimensions.

    Instead of a simplistic 3-factor formula, this considers:
      1. completion rate   — did they finish assigned tasks?
      2. active ratio      — were they present and engaged?
      3. task volume       — throughput factor
      4. focus quality     — time in verified flow-sessions
      5. deep work ratio   — time in IDE/terminal/design + docs
      6. productivity      — weighted-average across all app categories
      7. low switches      — penalty for high context-switching
      8. efficiency        — compound metric (completion × active)
      9. consistency       — baseline-relative variance (set later)
     10. communication     — only for manager/office roles
     11. planning          — only for manager/office roles

    Weights are role-specific from _ROLE_W.
    """
    ar = _safe_ratio(row.active_seconds, row.observed_seconds)
    cr = row.completion_rate
    tf = _tasks_factor(row.tasks_done)

    focus_q   = float(drivers.get("focus_quality", 0))
    deep_w    = float(drivers.get("deep_work_ratio", 0))
    prod_s    = float(drivers.get("productivity_score", 0))
    switches  = float(drivers.get("context_switches_per_hour", 0))
    comm_r    = float(drivers.get("communication_ratio", 0))
    plan_r    = float(drivers.get("planning_ratio", 0))

    low_switches = max(0.0, 1.0 - switches / 30)
    efficiency   = cr * ar
    consistency  = 1.0  # overridden by baseline comparison if available

    factors: dict[str, float] = {
        "completion":    cr,
        "active":        ar,
        "tasks_vol":     tf,
        "focus_quality": focus_q,
        "deep_work":     deep_w,
        "productivity":  prod_s,
        "low_switches":  low_switches,
        "efficiency":    efficiency,
        "consistency":   consistency,
        "communication": comm_r,
        "planning":      plan_r,
    }

    profile = role if role in _ROLE_W else "office"
    weights = _ROLE_W[profile]
    raw = sum(weights.get(k, 0) * factors.get(k, 0) for k in weights)

    score = max(0, min(100, int(round(100 * raw))))
    return score, ar, {k: round(v, 3) for k, v in factors.items()}


def _assess_burnout(
    current_drivers: dict,
    baseline_drivers: dict | None,
    trend_points: list[AIScoreTrendPoint],
    active_ratio: float,
) -> dict:
    """Multi-signal burnout risk detection.

    Burnout is not a single metric — it is a syndrome revealed
    through converging negative signals:
      1. Declining score trend (last 5 periods)
      2. Rising fatigue index vs personal baseline
      3. Declining focus quality (flow sessions shrinking)
      4. Cognitive overload (high load + high switches)
      5. Low active ratio despite long observed time
      6. Increasing context switches (losing concentration)

    Each signal contributes 0.10–0.25 to the risk score [0..1].
    """
    signals: list[str] = []
    risk_sum = 0.0

    # Signal 1: Declining score trend
    if len(trend_points) >= 5:
        recent = [p.score for p in trend_points[-3:]]
        earlier = [p.score for p in trend_points[-5:-2]]
        if earlier:
            r_avg = sum(recent) / len(recent)
            e_avg = sum(earlier) / len(earlier)
            if r_avg < e_avg - 5:
                signals.append("Устойчивое снижение показателей за последние периоды")
                risk_sum += 0.25

    # Signal 2: High fatigue
    fatigue = float(current_drivers.get("fatigue_index", 0))
    if fatigue > 0.5:
        signals.append(f"Высокий индекс усталости ({fatigue:.0%})")
        risk_sum += 0.20 * fatigue

    # Signal 3: Declining focus quality
    if baseline_drivers:
        cur_fq = float(current_drivers.get("focus_quality", 0))
        base_fq = float(baseline_drivers.get("focus_quality", 0))
        if base_fq > 0 and cur_fq < base_fq * 0.7:
            signals.append("Качество фокуса упало более чем на 30% от нормы")
            risk_sum += 0.20

    # Signal 4: Cognitive overload
    cog = float(current_drivers.get("cognitive_load", 0))
    if cog >= 0.7:
        signals.append(f"Когнитивная перегрузка ({cog:.0%})")
        risk_sum += 0.15

    # Signal 5: Low active ratio
    if active_ratio < 0.4:
        signals.append("Низкая доля активного времени — возможно рассеянность или истощение")
        risk_sum += 0.10

    # Signal 6: Rising context switches
    if baseline_drivers:
        cur_sw = float(current_drivers.get("context_switches_per_hour", 0))
        base_sw = float(baseline_drivers.get("context_switches_per_hour", 0))
        if base_sw > 0 and cur_sw > base_sw * 1.4:
            signals.append("Переключения выросли на 40%+ — потеря концентрации")
            risk_sum += 0.10

    # Signal 7: Poor recovery quality
    recovery = float(current_drivers.get("recovery_quality", 0.5))
    if recovery < 0.3:
        signals.append("Плохое восстановление: после перерывов продуктивность не возвращается")
        risk_sum += 0.15

    # Signal 8: No breaks with long work streaks
    break_data = current_drivers.get("break_intelligence", {})
    longest_streak = break_data.get("longest_work_streak_min", 0)
    breaks_taken = break_data.get("breaks_taken", 0)
    if longest_streak > 120 and breaks_taken == 0:
        signals.append(f"Работа без перерывов {longest_streak:.0f} мин — хроническое истощение")
        risk_sum += 0.15

    # Signal 9: High distraction rate (sign of inability to focus)
    distr = current_drivers.get("distraction_analysis", {})
    total_distr = distr.get("total_distractions", 0)
    if total_distr > 15:
        signals.append(f"Чрезмерные отвлечения ({total_distr}) — возможный признак ментального истощения")
        risk_sum += 0.10

    # Signal 10: Excessive work hours
    work_hours = float(current_drivers.get("work_hours", 0))
    if work_hours > 10:
        signals.append(f"Переработка: {work_hours:.1f} часов — выше здорового предела")
        risk_sum += 0.15

    # ── Boosting-style nonlinear interactions (2nd stage model) ──
    # A compact gradient-boosting analogue using weak rule-learners.
    boost = 0.0
    if fatigue > 0.55 and recovery < 0.35:
        boost += 0.08
        signals.append("Комбинация: высокая усталость + слабое восстановление")
    if cog > 0.70 and active_ratio < 0.45:
        boost += 0.06
        signals.append("Комбинация: перегрузка + низкая активность")
    if total_distr > 12 and float(current_drivers.get("context_switches_per_hour", 0)) > 28:
        boost += 0.05
        signals.append("Комбинация: отвлечения + частые переключения")
    if work_hours > 9 and breaks_taken <= 1:
        boost += 0.05
        signals.append("Комбинация: длинный день при нехватке перерывов")
    if baseline_drivers:
        base_fatigue = float(baseline_drivers.get("fatigue_index", 0))
        if base_fatigue > 0 and fatigue > base_fatigue * 1.30:
            boost += 0.04
            signals.append("Усталость существенно выше личной нормы")

    risk = min(1.0, risk_sum + boost)
    if risk >= 0.75:
        level = "critical"
    elif risk >= 0.6:
        level = "high"
    elif risk >= 0.35:
        level = "moderate"
    elif risk >= 0.15:
        level = "low"
    else:
        level = "none"

    recs = {
        "critical":  ("🚨 Критический риск выгорания. Немедленно: "
                      "1) Прекратите текущую задачу на 30 мин, "
                      "2) Выйдите на свежий воздух, "
                      "3) Обсудите нагрузку с руководителем. "
                      "Помните: выгорание — это не лень, а медицинское состояние."),
        "high":     ("Рекомендуется снизить нагрузку: сократить параллельные задачи, "
                     "ввести обязательные перерывы 15 мин каждые 90 мин, "
                     "рассмотреть пересмотр приоритетов с руководителем."),
        "moderate": ("Стоит обратить внимание на баланс: добавить фокус-блоки "
                     "без отвлечений, контролировать количество переключений."),
        "low":      "Незначительные признаки нагрузки. Можно продолжать, следя за динамикой.",
        "none":     "Признаков перегрузки не выявлено.",
    }

    return {
        "risk_level": level,
        "risk_score": round(risk, 2),
        "base_signals_score": round(min(1.0, risk_sum), 2),
        "boost_score": round(boost, 2),
        "signals": signals,
        "recommendation": recs[level],
    }


def _generate_recommendations(
    score: int,
    drivers: dict,
    baseline_drivers: dict | None,
    role: str,
    burnout: dict,
) -> list[str]:
    """Generate personalised, actionable AI recommendations.

    Every recommendation is grounded in the user's actual behavioural
    data — not generic productivity advice.
    """
    recs: list[str] = []

    focus_q         = float(drivers.get("focus_quality", 0))
    deep_w          = float(drivers.get("deep_work_ratio", 0))
    switches        = float(drivers.get("context_switches_per_hour", 0))
    fatigue         = float(drivers.get("fatigue_index", 0))
    comm_r          = float(drivers.get("communication_ratio", 0))
    entertainment_r = float(drivers.get("entertainment_ratio", 0))
    flow_count      = int(drivers.get("flow_sessions_count", 0))
    avg_flow        = float(drivers.get("avg_flow_duration_min", 0))
    style           = drivers.get("work_style", "balanced")
    peaks           = drivers.get("peak_hours", [])

    # Focus & Deep Work
    if focus_q < 0.15 and role == "developer":
        recs.append(
            "Критически низкое качество фокуса. Попробуйте метод "
            "«90-минутных блоков»: телефон в авиарежим, мессенджеры закрыты, "
            "полное погружение в одну задачу."
        )
    elif focus_q < 0.30 and role == "developer":
        recs.append(
            f"Качество фокуса ниже оптимума ({focus_q:.0%}). "
            "Выделите 2 «фокус-слота» по 60 мин в первой половине дня "
            "без мессенджеров и совещаний."
        )

    if flow_count == 0 and role == "developer":
        recs.append(
            "Ни одной flow-сессии (≥25 мин непрерывного кодирования). "
            "Это основной резерв роста: даже 1–2 flow-блока в день "
            "поднимают результат на 15–25%."
        )
    elif flow_count >= 3 and avg_flow >= 40:
        recs.append(
            f"Отлично: {flow_count} flow-сессий, средняя {avg_flow:.0f} мин. "
            "Сохраняйте этот режим — он даёт максимальную отдачу."
        )

    #Context switches 
    if switches > 30:
        recs.append(
            f"Переключения очень высоки ({switches:.0f}/час). "
            "Каждое переключение стоит ~23 мин восстановления фокуса (исследование UC Irvine). "
            "Группируйте однотипные задачи: ревью — в один блок, ответы — в другой."
        )
    elif switches > 20:
        recs.append(
            f"Переключения выше нормы ({switches:.0f}/час). "
            "Batch-обработка мессенджеров каждые 30–45 мин вместо реактивных проверок."
        )

    #  Fatigue 
    if fatigue > 0.6:
        recs.append(
            "Серьёзная усталость: активность во второй половине периода "
            "значительно ниже. Микро-перерывы (5 мин/час) и перенос "
            "сложных задач на утро дают до 20% прироста во второй половине."
        )

    # Role-specific
    if role == "manager" and comm_r < 0.20:
        recs.append(
            "Для менеджера доля коммуникаций ниже ожидаемой. "
            "Команда может не получать достаточно обратной связи."
        )
    if role == "developer" and comm_r > 0.45:
        recs.append(
            f"Коммуникации занимают {comm_r:.0%} времени — много для разработчика. "
            "Проверьте, не перетягивают ли совещания ресурсы от основных задач."
        )

    # Entertainment 
    if entertainment_r > 0.10:
        recs.append(
            f"Развлекательные приложения: {entertainment_r:.0%} рабочего времени. "
            "Это прямо снижает score и сокращает flow-потенциал."
        )

    # Peak hours
    if peaks:
        recs.append(
            f"Пиковые часы продуктивности: {', '.join(peaks)}. "
            "Планируйте самые сложные задачи на эти интервалы."
        )

    # Work style 
    _style_scripts ={    
        "deep_worker":  "Стиль «глубокий работник» — оберегайте flow-блоки, они ваш главный актив.",
        "multitasker":  "Стиль «мульти-таскер» — осознанно снижайте параллельность для роста качества.",
        "communicator": "Стиль «коммуникатор» — выделяйте хотя бы 2 часа/день на индивидуальную работу.",
        "planner":      "Стиль «планировщик» — следите за балансом планирования и исполнения.",
        "balanced":     "Стиль «сбалансированный» — для прорыва усильте одно конкретное направление.",
    }
    tip = _style_tips.get(style)
    if tip:
        recs.append(tip)

    # Break intelligence 
    break_data = drivers.get("break_intelligence", {})
    longest_streak = break_data.get("longest_work_streak_min", 0)
    breaks_taken = break_data.get("breaks_taken", 0)
    if longest_streak > 120 and breaks_taken == 0:
        recs.append(
            f"⚠️ Вы работали {longest_streak:.0f} мин без единого перерыва! "
            "Исследования показывают: непрерывная работа >2 часов снижает "
            "когнитивные способности на 25%. Ваш мозг — не марафонец, "
            "а спринтер с перерывами. Делайте паузу каждые 52 мин."
        )
    elif longest_streak > 90 and breaks_taken < 2:
        recs.append(
            f"Длинные рабочие стрики ({longest_streak:.0f} мин) при малом "
            f"количестве перерывов ({breaks_taken}). Попробуйте ритм: "
            f"{break_data.get('optimal_break_interval_min', 52)} мин работы → "
            "10 мин отдых. Это улучшает и продуктивность, и самочувствие."
        )

    # Distraction patterns 
    distr = drivers.get("distraction_analysis", {})
    total_distr = distr.get("total_distractions", 0)
    avg_recovery = distr.get("avg_recovery_min", 0)
    if total_distr > 10 and avg_recovery > 5:
        distr_list = distr.get("distractors", [])
        top_app = distr_list[0]["app"] if distr_list else "unknown"
        recs.append(
            f"За период {total_distr} отвлечений, среднее восстановление "
            f"{avg_recovery:.0f} мин. Главный источник: {top_app}. "
            "Попробуйте блокировку уведомлений во время фокус-блоков."
        )

    # Circadian optimization
    circ = drivers.get("circadian_map", {})
    if circ:
        best_hours = sorted(circ.items(), key=lambda x: x[1], reverse=True)[:2]
        worst_hours = sorted(circ.items(), key=lambda x: x[1])[:2]
        if best_hours and worst_hours and best_hours[0][1] > 0.5:
            best_str = ", ".join(f"{h:02d}:00" for h, _ in best_hours)
            worst_str = ", ".join(f"{h:02d}:00" for h, _ in worst_hours)
            recs.append(
                f"🧠 Ваш биоритм: пиковая производительность в {best_str}, "
                f"спад в {worst_str}. Ставьте сложные задачи на пик, "
                "рутину — на спад. Это адаптация под ваш циркадный ритм."
            )

    # Ultradian cycle advice
    cycles = drivers.get("ultradian_cycles", [])
    if cycles and len(cycles) >= 2:
        avg_cycle = sum(c["duration_min"] for c in cycles) / len(cycles)
        recs.append(
            f"Обнаружено {len(cycles)} ультрадианных цикла (~{avg_cycle:.0f} мин). "
            "Это ваш природный ритм «работа-отдых». Планируйте перерывы "
            "на стыке циклов для максимальной эффективности."
        )

    # Wellbeing-focused recommendations
    recovery = float(drivers.get("recovery_quality", 0.5))
    if recovery < 0.3:
        recs.append(
            "Качество восстановления низкое — после перерывов продуктивность "
            "не возвращается к прежнему уровню. Это признак накопленной "
            "усталости. Подумайте о полноценном отдыхе (не за экраном)."
        )

    if burnout.get("risk_level") in ("moderate", "high"):
        recs.append(
            "🔥 Обнаружены признаки выгорания. Выгорание — это не слабость, "
            "а результат хронического стресса. Три шага прямо сейчас: "
            "1) 15-минутная прогулка без телефона, "
            "2) Делегирование или отложение одной задачи, "
            "3) Запись трёх вещей, которые получились хорошо."
        )

    # Priority ranking layer (neural-style reranker over rule outputs).
    burnout_level = burnout.get("risk_level", "none")

    def _priority(msg: str) -> float:
        p = 1.0
        m = msg.lower()
        # Urgency markers
        if "критически" in m or "⚠️" in msg or "🔥" in msg:
            p += 2.0
        if "выгора" in m:
            p += 1.8 if burnout_level in {"high", "critical"} else 1.0
        if "устал" in m or "восстанов" in m or "перерыв" in m:
            p += 1.2
        if "переключ" in m or "отвлеч" in m:
            p += 0.9
        if "пиковые часы" in m or "биоритм" in m or "ультрадиан" in m:
            p += 0.6
        # Penalize mostly praise-like messages when there are urgent issues.
        if ("отлично" in m or "хороший ритм" in m) and burnout_level in {"moderate", "high", "critical"}:
            p -= 0.8
        return p

    # Deduplicate while preserving best-scored variant.
    best_by_msg: dict[str, float] = {}
    for r in recs:
        score_r = _priority(r)
        if r not in best_by_msg or score_r > best_by_msg[r]:
            best_by_msg[r] = score_r

    ranked = sorted(best_by_msg.items(), key=lambda x: x[1], reverse=True)
    return [msg for msg, _ in ranked[:7]]


def _upsert_snapshot(
    db: Session, org_id: str, period_type: ScorePeriod,
    period_start: date, period_end: date, user_row,
    role_profile: str = "developer",
) -> AIScoreSnapshot:
    drivers = _compute_driver_metrics(
        db, org_id, user_row.user_id, period_start, period_end,
        tasks_total=user_row.tasks_total,
    )
    score, active_ratio, _factors = _score_advanced(user_row, drivers, role_profile)
    dj = json.dumps(drivers, ensure_ascii=False, default=str)

    existing = (
        db.query(AIScoreSnapshot)
        .filter(
            AIScoreSnapshot.org_id == org_id,
            AIScoreSnapshot.user_id == user_row.user_id,
            AIScoreSnapshot.period_type == period_type,
            AIScoreSnapshot.period_start == period_start,
            AIScoreSnapshot.period_end == period_end,
        )
        .first()
    )
    snap = existing or AIScoreSnapshot(
        org_id=org_id, user_id=user_row.user_id,
        period_type=period_type,
        period_start=period_start, period_end=period_end,
    )
    if not existing:
        db.add(snap)

    snap.score            = score
    snap.completion_rate  = user_row.completion_rate
    snap.active_ratio     = active_ratio
    snap.tasks_total      = user_row.tasks_total
    snap.tasks_done       = user_row.tasks_done
    snap.observed_seconds = user_row.observed_seconds
    snap.idle_seconds     = user_row.idle_seconds
    snap.active_seconds   = user_row.active_seconds
    snap.sessions_count   = user_row.sessions_count
    snap.drivers_json     = dj
    snap.generated_at     = utc_now_naive()
    return snap


def _load_trend(
    db: Session, org_id: str, user_id: str,
    period_type: ScorePeriod, period_start: date, limit: int,
) -> list[AIScoreTrendPoint]:
    if limit <= 0:
        return []
    snaps = (
        db.query(AIScoreSnapshot)
        .filter(
            AIScoreSnapshot.org_id == org_id,
            AIScoreSnapshot.user_id == user_id,
            AIScoreSnapshot.period_type == period_type,
            AIScoreSnapshot.period_start <= period_start,
        )
        .order_by(AIScoreSnapshot.period_start.desc())
        .limit(limit)
        .all()
    )
    snaps.reverse()
    return [AIScoreTrendPoint(period_start=s.period_start, score=s.score) for s in snaps]


def _load_baseline(
    db: Session, org_id: str, user_id: str,
    period_type: ScorePeriod, period_start: date,
) -> AIScoreBaseline | None:
    lim = 7 if period_type == ScorePeriod.daily else 4
    snaps = (
        db.query(AIScoreSnapshot)
        .filter(
            AIScoreSnapshot.org_id == org_id,
            AIScoreSnapshot.user_id == user_id,
            AIScoreSnapshot.period_type == period_type,
            AIScoreSnapshot.period_start < period_start,
        )
        .order_by(AIScoreSnapshot.period_start.desc())
        .limit(lim)
        .all()
    )
    if not snaps:
        return None

    # Adaptive recency weighting: recent periods contribute more than old ones.
    weights = [max(0.35, 1.0 - 0.12 * i) for i in range(len(snaps))]
    w_sum = sum(weights) or 1.0
    w = [x / w_sum for x in weights]

    return AIScoreBaseline(
        avg_score=sum(sw * s.score for sw, s in zip(w, snaps)),
        avg_completion_rate=sum(sw * s.completion_rate for sw, s in zip(w, snaps)),
        avg_active_ratio=sum(sw * s.active_ratio for sw, s in zip(w, snaps)),
        avg_tasks_done=sum(sw * s.tasks_done for sw, s in zip(w, snaps)),
    )


def _load_driver_baseline(
    db: Session, org_id: str, user_id: str,
    period_type: ScorePeriod, period_start: date,
) -> dict[str, float] | None:
    lim = 7 if period_type == ScorePeriod.daily else 4
    snaps = (
        db.query(AIScoreSnapshot)
        .filter(
            AIScoreSnapshot.org_id == org_id,
            AIScoreSnapshot.user_id == user_id,
            AIScoreSnapshot.period_type == period_type,
            AIScoreSnapshot.period_start < period_start,
        )
        .order_by(AIScoreSnapshot.period_start.desc())
        .limit(lim)
        .all()
    )
    # Adaptive baseline by recency weights.
    weights = [max(0.35, 1.0 - 0.12 * i) for i in range(len(snaps))]
    acc: dict[str, list[tuple[float, float]]] = {}
    for s, w in zip(snaps, weights):
        if not s.drivers_json:
            continue
        try:
            d = json.loads(s.drivers_json)
        except (json.JSONDecodeError, TypeError):
            continue
        for k, v in d.items():
            if isinstance(v, (int, float)):
                acc.setdefault(k, []).append((float(v), w))
    if not acc:
        return None

    baseline: dict[str, float] = {}
    for k, vals in acc.items():
        if not vals:
            continue
        weight_sum = sum(w for _, w in vals) or 1.0
        baseline[k] = sum(v * w for v, w in vals) / weight_sum
    return baseline



def _build_reasons(
    cur: AIScoreSnapshot, baseline: AIScoreBaseline | None,
) -> list[AIChangeReason]:
    if not baseline:
        return []

    cd = cur.completion_rate - baseline.avg_completion_rate
    ad = cur.active_ratio   - baseline.avg_active_ratio
    td = _tasks_factor(cur.tasks_done) - _tasks_factor(int(round(baseline.avg_tasks_done)))

    # Pull driver-level deltas
    cur_d: dict = {}
    if cur.drivers_json:
        try:
            cur_d = json.loads(cur.drivers_json)
        except (json.JSONDecodeError, TypeError):
            pass

    focus_q = float(cur_d.get("focus_quality", 0))
    deep_w  = float(cur_d.get("deep_work_ratio", 0))

    reasons = [
        AIChangeReason(
            code="completion_rate", title="Завершение задач",
            detail=f"Доля выполненных задач изменилась на {cd * 100:+.1f}%.",
            delta=cd * 100 * 0.30,
        ),
        AIChangeReason(
            code="focus_ratio", title="Концентрация",
            detail=f"Доля активного времени изменилась на {ad * 100:+.1f}%.",
            delta=ad * 100 * 0.20,
        ),
        AIChangeReason(
            code="task_volume", title="Объём задач",
            detail=f"Выполнено: {cur.tasks_done} (норма: {baseline.avg_tasks_done:.1f}).",
            delta=td * 100 * 0.10,
        ),
    ]

    if focus_q > 0.01:
        reasons.append(AIChangeReason(
            code="focus_quality", title="Качество фокуса",
            detail=f"Flow-сессии: {focus_q:.0%} рабочего времени в состоянии глубокого фокуса.",
            delta=focus_q * 100 * 0.15,
        ))
    if deep_w > 0.01:
        reasons.append(AIChangeReason(
            code="deep_work", title="Глубокая работа",
            detail=f"Deep work составил {deep_w:.0%} активного времени.",
            delta=deep_w * 100 * 0.15,
        ))

    filtered = [r for r in reasons if abs(r.delta) >= 1.0]
    filtered.sort(key=lambda r: abs(r.delta), reverse=True)
    return filtered[:5]


def _build_primary_drivers(
    role: str, current: dict, baseline: dict | None,
) -> list[AIDriverImpact]:
    profile = role if role in {"developer", "manager", "office"} else "office"

    defs = {
        "developer": [
            ("context_switches_per_hour", "Контекстные переключения", "lower"),
            ("deep_work_ratio",           "Глубокая работа",         "higher"),
            ("focus_quality",             "Качество фокуса",         "higher"),
            ("communication_ratio",       "Коммуникации",            "neutral"),
            ("fatigue_index",             "Усталость",               "lower"),
        ],
        "manager": [
            ("communication_ratio",       "Коммуникации",   "higher"),
            ("planning_ratio",            "Планирование",   "higher"),
            ("focus_quality",             "Качество фокуса", "higher"),
            ("context_switches_per_hour", "Переключения",   "lower"),
            ("fatigue_index",             "Усталость",       "lower"),
        ],
        "office": [
            ("deep_work_ratio",           "Фокусная работа",  "higher"),
            ("focus_quality",             "Качество фокуса",  "higher"),
            ("communication_ratio",       "Коммуникации",     "higher"),
            ("context_switches_per_hour", "Переключения",     "lower"),
            ("fatigue_index",             "Усталость",         "lower"),
        ],
    }

    base = baseline or {}
    drivers: list[AIDriverImpact] = []
    impacts: list[float] = []

    for key, title, direction in defs[profile]:
        cv = float(current.get(key, 0))
        bv = float(base.get(key, 0))
        if bv > 0:
            if key.endswith("_ratio") or key in {"fatigue_index", "focus_quality", "cognitive_load"}:
                delta = (cv - bv) / bv
                detail = f"Изменение: {delta * 100:+.0f}% от нормы. Текущее: {cv:.0%}."
            else:
                delta = cv - bv
                detail = f"Изменение: {delta:+.1f} от нормы. Текущее: {cv:.1f}."
        else:
            delta = 0.0
            if key.endswith("_ratio") or key in {"fatigue_index", "focus_quality", "cognitive_load"}:
                detail = f"Текущее значение: {cv:.0%}."
            else:
                detail = f"Текущее значение: {cv:.1f}."

        impact = delta if direction == "higher" else (-delta if direction == "lower" else 0.0)
        impacts.append(impact)
        drivers.append(AIDriverImpact(
            title=title, detail=detail, impact_pct=impact,
            direction="positive" if impact > 0 else "negative" if impact < 0 else "neutral",
        ))

    total = sum(abs(v) for v in impacts)
    if total > 0:
        for d in drivers:
            d.impact_pct = (d.impact_pct / total) * 100
    drivers.sort(key=lambda d: abs(d.impact_pct), reverse=True)
    return drivers[:5]


def _trend_summary(points: list[AIScoreTrendPoint]) -> tuple[str, str]:
    """EMA-based trend analysis with stability assessment."""
    if len(points) < 3:
        return "Недостаточно данных для анализа тренда.", "низкая"

    scores = [float(p.score) for p in points]
    ema_vals = _ema(scores, alpha=0.35)
    start_e = ema_vals[0]
    end_e   = ema_vals[-1]
    delta   = end_e - start_e

    mean = sum(scores) / len(scores)
    sd = _stddev(scores, mean)

    stability = "высокая" if sd < 3 else ("умеренная" if sd < 7 else "низкая")

    if delta >= 8:
        text = (f"Выраженный рост (EMA: {start_e:.0f} → {end_e:.0f}). "
                "Текущие практики дают положительный результат.")
    elif delta <= -8:
        text = (f"Выраженное снижение (EMA: {start_e:.0f} → {end_e:.0f}). "
                "Рекомендуется анализ причин и корректировка режима.")
    elif delta >= 3:
        text = f"Умеренный рост (EMA: {start_e:.0f} → {end_e:.0f})."
    elif delta <= -3:
        text = f"Умеренное снижение (EMA: {start_e:.0f} → {end_e:.0f}). Стоит обратить внимание."
    else:
        text = f"Показатели стабильны (EMA ≈ {end_e:.0f}), без выраженного тренда."

    return text, stability


def _build_interpretation(
    snap: AIScoreSnapshot,
    baseline: AIScoreBaseline | None,
    drivers_list: list[AIDriverImpact],
    trend_points: list[AIScoreTrendPoint],
    mode: str,
    team_median: float | None,
    role: str,
    burnout: dict,
    recommendations: list[str],
    current_drivers: dict,
    baseline_drivers: dict | None,
    grade_str: str,
) -> AIInterpretation:
    """Build a rich, NLP-quality interpretation — not a dry report
    but a contextual analysis that reads like expert commentary.
    """
    score = snap.score
    trend_text, stability = _trend_summary(trend_points)

    # vs baseline 
    if baseline and baseline.avg_score:
        dp = ((score - baseline.avg_score) / baseline.avg_score) * 100
        if dp > 0:
            vs = f"Рост на {abs(dp):.0f}% относительно личной нормы ({baseline.avg_score:.0f})."
        elif dp < 0:
            vs = f"Снижение на {abs(dp):.0f}% от личной нормы ({baseline.avg_score:.0f})."
        else:
            vs = f"На уровне личной нормы ({baseline.avg_score:.0f})."
    else:
        dp = None
        vs = "Формируется начальный профиль — данных для нормы пока недостаточно."

    # Extract driver values 
    style       = current_drivers.get("work_style", "balanced")
    flow_count  = int(current_drivers.get("flow_sessions_count", 0))
    avg_flow    = float(current_drivers.get("avg_flow_duration_min", 0))
    focus_q     = float(current_drivers.get("focus_quality", 0))
    fatigue     = float(current_drivers.get("fatigue_index", 0))
    switches    = float(current_drivers.get("context_switches_per_hour", 0))
    peak_h      = current_drivers.get("peak_hours", [])
    cog_level   = current_drivers.get("cognitive_load_level", "low")
    ent_r       = float(current_drivers.get("entertainment_ratio", 0))

    _style_labels = {
        "deep_worker":  "глубокий работник",
        "multitasker":  "мульти-таскер",
        "communicator": "коммуникатор",
        "planner":      "планировщик",
        "balanced":     "сбалансированный",
    }

    # Executive summary paragraphs 
    parts: list[str] = [f"Оценка КПД: {score}/100 (Grade {grade_str})."]
    parts.append(vs)
    parts.append(f"Профиль работы: «{_style_labels.get(style, style)}».")

    if flow_count > 0:
        parts.append(
            f"За период {flow_count} flow-сессий "
            f"(~{avg_flow:.0f} мин), {focus_q:.0%} рабочего времени "
            "в состоянии глубокого фокуса."
        )
    else:
        parts.append("Flow-сессий не зафиксировано — это главная точка роста.")

    if fatigue > 0.4:
        parts.append(f"Индекс усталости: {fatigue:.0%}.")
    if switches > 25:
        parts.append(f"Переключений: {switches:.0f}/час — высокая фрагментация.")
    if ent_r > 0.05:
        parts.append(f"Развлечения: {ent_r:.0%} рабочего времени.")

    parts.append(trend_text)

    burnout_level = burnout.get("risk_level", "none")
    _bd = {"none": "не выявлен", "low": "низкий", "moderate": "умеренный",
           "high": "высокий", "critical": "критический"}

    if mode == "executive":
        if team_median is not None:
            parts.append(f"Медиана команды: {team_median:.0f}.")
        parts.append(f"Стабильность: {stability}.")
        parts.append(f"Риск выгорания: {_bd.get(burnout_level, burnout_level)}.")
        sigs = burnout.get("signals", [])
        if sigs:
            parts.append("Сигналы: " + "; ".join(sigs[:3]) + ".")

    exec_summary = " ".join(parts)

    # Detailed analysis (markdown) 
    da: list[str] = [
        f"## Детальный анализ КПД\n",
        f"**Score:** {score}/100 ({grade_str})",
    ]
    if baseline:
        da.append(f"**Личная норма:** {baseline.avg_score:.0f}")
    da.append(f"\n### Поведенческий профиль")
    da.append(f"- Стиль работы: {_style_labels.get(style, style)}")
    da.append(f"- Flow-сессии: {flow_count} (качество фокуса {focus_q:.0%})")
    da.append(f"- Когнитивная нагрузка: {cog_level}")
    da.append(f"- Индекс усталости: {fatigue:.0%}")
    da.append(f"- Переключения: {switches:.0f}/час")
    if peak_h:
        da.append(f"- Пиковые часы: {', '.join(peak_h)}")

    # Wellbeing section
    break_data = current_drivers.get("break_intelligence", {})
    recovery_val = float(current_drivers.get("recovery_quality", 0.5))
    cog_score_val = float(current_drivers.get("cognitive_load", 0))
    work_hrs = float(current_drivers.get("work_hours", 0))
    burnout_risk_val = burnout.get("risk_score", 0)

    wb = _wellbeing_score(
        fatigue, cog_score_val, break_data, recovery_val,
        burnout_risk_val, work_hrs,
    )
    wb_level_ru = {
        "excellent": "отличный", "good": "хороший", "fair": "средний",
        "concerning": "тревожный", "critical": "критический",
    }

    da.append(f"\n### 🏥 Здоровье и благополучие")
    da.append(f"- Индекс благополучия: {wb['score']}/100 ({wb_level_ru.get(wb['level'], wb['level'])})")
    da.append(f"- {wb['message']}")
    da.append(f"- Восстановление: {recovery_val:.0%}")
    if break_data:
        da.append(f"- Перерывы: {break_data.get('breaks_taken', 0)}, макс. рабочий стрик: {break_data.get('longest_work_streak_min', 0):.0f} мин")
        da.append(f"- {break_data.get('recommendation', '')}")

    # Distraction section
    distr = current_drivers.get("distraction_analysis", {})
    if distr.get("total_distractions", 0) > 0:
        da.append(f"\n### 🎯 Отвлечения")
        da.append(f"- Всего отвлечений: {distr['total_distractions']}")
        da.append(f"- Среднее восстановление: {distr.get('avg_recovery_min', 0):.1f} мин")
        if distr.get("vulnerable_hours"):
            da.append(f"- Уязвимые часы: {', '.join(distr['vulnerable_hours'])}")
        if distr.get("distractors"):
            top_app = distr["distractors"][0]["app"]
            da.append(f"- Главный отвлекатель: {top_app}")

    # Circadian rhythm
    circ = current_drivers.get("circadian_map", {})
    if circ:
        sorted_hours = sorted(circ.items(), key=lambda x: x[1], reverse=True)
        if sorted_hours:
            da.append(f"\n### 🌅 Циркадный ритм")
            top3 = sorted_hours[:3]
            da.append("- Пик продуктивности: " + ", ".join(
                f"{h:02d}:00 ({v:.0%})" for h, v in top3
            ))
            bottom3 = sorted_hours[-3:]
            da.append("- Спад: " + ", ".join(
                f"{h:02d}:00 ({v:.0%})" for h, v in bottom3
            ))

    # Ultradian cycles
    cycles = current_drivers.get("ultradian_cycles", [])
    if cycles:
        da.append(f"\n### ⏰ Ультрадианные циклы")
        da.append(f"- Обнаружено циклов: {len(cycles)}")
        for c in cycles[:3]:
            da.append(f"  - {c['start']}: {c['duration_min']} мин (продуктивность: {c['avg_productivity']:.0%})")

    da.append(f"\n### Тренд\n{trend_text}")

    # Prediction
    prediction = _predict_next_score(trend_points, current_drivers, baseline_drivers)
    if prediction.get("predicted_score") is not None:
        pred_s = prediction["predicted_score"]
        conf_ru = {"high": "высокая", "medium": "средняя", "low": "низкая"}
        da.append(f"\n### 🔮 Прогноз")
        da.append(f"- Ожидаемый score завтра: **{pred_s}** (уверенность: {conf_ru.get(prediction['confidence'], prediction['confidence'])})")
        components = prediction.get("model_components", {})
        if components:
            da.append(
                "- Ансамбль моделей: "
                f"LR={components.get('linear_regression')}, "
                f"Holt={components.get('holt_linear')}, "
                f"вес Holt={components.get('ensemble_weight_holt')}"
            )
        for f in prediction.get("factors", []):
            da.append(f"  - {f}")

    # Momentum
    momentum = _momentum_tracker(trend_points)
    if momentum.get("label"):
        da.append(f"\n### 📈 Импульс")
        da.append(f"- {momentum['label']}")
        if momentum["streak"] != 0:
            direction = "роста" if momentum["streak"] > 0 else "снижения"
            da.append(f"- Серия {direction}: {abs(momentum['streak'])} дн.")

    if recommendations:
        da.append(f"\n### Рекомендации ИИ")
        for i, r in enumerate(recommendations, 1):
            da.append(f"{i}. {r}")
    detailed = "\n".join(da)

    #Personality insight 
    _personality_map = {
        "deep_worker":  "Максимально эффективен при длительных блоках без отвлечений.",
        "multitasker":  "Работает в режиме быстрого переключения. Потенциал роста через осознанное снижение параллельности.",
        "communicator": "Ключевая роль в командном взаимодействии. Важно выделять блоки для индивидуальной работы.",
        "planner":      "Сильное стратегическое мышление. Следите за балансом планирования и исполнения.",
        "balanced":     "Равномерное распределение. Для прорыва полезно осознанно усилить одно направление.",
    }
    personality = (
        f"Тип: «{_style_labels.get(style, style)}». "
        + _personality_map.get(style, "")
    )

    suggestion = recommendations[0] if recommendations else None

    return AIInterpretation(
        mode=mode,
        executive_summary=exec_summary,
        vs_baseline=vs,
        primary_drivers=drivers_list,
        trend=trend_text,
        suggestion=suggestion,
        stability=stability if mode == "executive" else None,
        team_median_score=team_median if mode == "executive" else None,
        overload_risk=_bd.get(burnout_level) if mode == "executive" else None,
        cognitive_profile={
            "cognitive_load": cog_level,
            "focus_quality": focus_q,
            "flow_sessions_count": flow_count,
            "avg_flow_duration_min": avg_flow,
            "fatigue_index": fatigue,
            "peak_hours": peak_h,
            "work_style": style,
            "wellbeing": wb,
            "prediction": prediction,
            "momentum": momentum,
            "recovery_quality": recovery_val,
            "break_intelligence": break_data,
            "distraction_analysis": distr,
            "circadian_map": circ,
        },
        burnout_assessment=burnout,
        ai_recommendations=recommendations,
        detailed_analysis=detailed,
        grade=grade_str,
        personality_insight=personality,
    )




@router.get("/kpi", response_model=AIKPIReport)
def ai_kpi(
    org_id: str,
    start_date: date | None = None,
    end_date: date | None = None,
    team_id: str | None = None,
    project_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIKPIReport:
    _validate_range_limit(start_date, end_date)
    membership = get_org_membership(org_id, current_user, db)
    report = compute_org_kpi_report(
        db, org_id,
        start_date=start_date, end_date=end_date,
        team_id=team_id, project_id=project_id,
    )
    if membership.role not in {OrgRole.admin, OrgRole.manager}:
        report.users = [r for r in report.users if r.user_id == current_user.id]

    active_median = _median([r.active_seconds for r in report.users])
    score_values: list[float] = []

    anomalies: list[AIKPIAnomaly] = []
    user_scores: list[AIKPIUserScore] = []

    for row in report.users:
        sd = start_date or date.today()
        ed = end_date or date.today()
        drivers = _compute_driver_metrics(
            db, org_id, row.user_id, sd, ed, row.tasks_total,
        )
        score, ar, _ = _score_advanced(row, drivers)
        score_values.append(float(score))

        # Statistical & behavioural anomaly detection
        if row.tasks_total >= 3 and row.completion_rate < 0.3:
            anomalies.append(AIKPIAnomaly(
                code="low_completion", severity="high",
                title="Низкое завершение задач",
                detail=(
                    f"Выполнено {row.tasks_done} из {row.tasks_total} "
                    f"({row.completion_rate:.0%}). "
                    "Возможные причины: перегрузка, неясные требования или "
                    "блокирующие зависимости."
                ),
                user_id=row.user_id,
            ))

        if row.observed_seconds >= 3600 and ar < 0.5:
            anomalies.append(AIKPIAnomaly(
                code="low_focus", severity="medium",
                title="Низкая концентрация",
                detail=f"Активное время: {ar:.0%}. Рекомендуется анализ отвлекающих факторов.",
                user_id=row.user_id,
            ))

        if active_median > 0 and row.active_seconds < active_median * 0.5:
            z = _z_score(float(row.active_seconds), active_median, active_median * 0.3)
            anomalies.append(AIKPIAnomaly(
                code="low_activity",
                severity="medium" if z > -3 else "high",
                title="Активность ниже нормы",
                detail=(
                    f"На {abs(z):.1f}σ ниже медианы команды. "
                    "Возможные причины: техпроблемы, совещания или внешние задачи."
                ),
                user_id=row.user_id,
            ))

        sw = float(drivers.get("context_switches_per_hour", 0))
        if sw > 40:
            anomalies.append(AIKPIAnomaly(
                code="context_overload", severity="medium",
                title="Перегрузка переключениями",
                detail=(
                    f"{sw:.0f} переключений/час — каждое стоит ~23 мин "
                    "восстановления фокуса."
                ),
                user_id=row.user_id,
            ))

        ent = float(drivers.get("entertainment_ratio", 0))
        if ent > 0.15:
            anomalies.append(AIKPIAnomaly(
                code="high_entertainment", severity="low",
                title="Развлекательный контент",
                detail=f"Развлечения: {ent:.0%} рабочего времени.",
                user_id=row.user_id,
            ))

        fat = float(drivers.get("fatigue_index", 0))
        if fat > 0.6:
            anomalies.append(AIKPIAnomaly(
                code="high_fatigue", severity="medium",
                title="Высокая усталость",
                detail=(
                    f"Индекс усталости: {fat:.0%}. "
                    "Активность значительно снижается во второй половине периода."
                ),
                user_id=row.user_id,
            ))

        user_scores.append(AIKPIUserScore(
            user_id=row.user_id, full_name=row.full_name,
            sessions_count=row.sessions_count,
            tasks_total=row.tasks_total, tasks_done=row.tasks_done,
            completion_rate=row.completion_rate,
            observed_seconds=row.observed_seconds,
            idle_seconds=row.idle_seconds,
            active_seconds=row.active_seconds,
            active_ratio=ar, score=score,
        ))

    # Isolation Forest style anomaly detection over team score distribution 
    team_scores = [float(u.score) for u in user_scores]
    team_m = _median(team_scores)
    if len(team_scores) >= 6:
        for u in user_scores:
            iso = _isolation_forest_score_1d(float(u.score), team_scores)
            if iso >= 0.62:
                severity = "high" if u.score < team_m else "medium"
                anomalies.append(AIKPIAnomaly(
                    code="score_outlier_iforest",
                    severity=severity,
                    title="Аномальный профиль score",
                    detail=(
                        f"Isolation-score: {iso:.2f}. "
                        f"Текущий score {u.score}, медиана команды {team_m:.0f}."
                    ),
                    user_id=u.user_id,
                ))

    org_score = int(round(sum(score_values) / len(score_values))) if score_values else 0

    return AIKPIReport(
        org_id=org_id,
        start_date=report.start_date, end_date=report.end_date,
        team_id=team_id, project_id=project_id,
        generated_at=utc_now_naive(),
        org_score=org_score,
        users=user_scores,
        anomalies=anomalies,
    )


@router.post("/scorecards/rebuild", response_model=AIScoreRebuildResponse)
def rebuild_scorecards(
    org_id: str,
    start_date: date,
    end_date: date,
    period: ScorePeriod = ScorePeriod.daily,
    role_profile: str = "developer",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIScoreRebuildResponse:
    _validate_range_limit(start_date, end_date)
    membership = get_org_membership(org_id, current_user, db)
    if membership.role not in {OrgRole.admin, OrgRole.manager}:
        raise HTTPException(status_code=403, detail="Not allowed")

    count = 0
    for ps, pe in _iter_periods(start_date, end_date, period):
        report = compute_org_kpi_report(db, org_id, start_date=ps, end_date=pe)
        for row in report.users:
            _upsert_snapshot(db, org_id, period, ps, pe, row, role_profile)
            count += 1
    db.commit()

    return AIScoreRebuildResponse(
        org_id=org_id, period_type=period.value,
        start_date=start_date, end_date=end_date,
        snapshots_count=count,
    )


@router.get("/scorecards", response_model=list[AIScorecard])
def scorecards(
    org_id: str,
    period: ScorePeriod = ScorePeriod.daily,
    as_of: date | None = None,
    user_id: str | None = None,
    mode: str = "employee",
    role_profile: str = "developer",
    trend_limit: int = 14,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AIScorecard]:
    membership = get_org_membership(org_id, current_user, db)
    if membership.role not in {OrgRole.admin, OrgRole.manager}:
        user_id = current_user.id

    if as_of is None:
        as_of = date.today()
    if trend_limit < 1:
        trend_limit = 1
    elif trend_limit > 90:
        trend_limit = 90
    mode = mode.strip().lower()
    if mode not in {"employee", "executive"}:
        raise HTTPException(status_code=400, detail="Invalid mode")

    ps, pe = _period_bounds(as_of, period)
    report = compute_org_kpi_report(db, org_id, start_date=ps, end_date=pe)
    if user_id:
        report.users = [r for r in report.users if r.user_id == user_id]

    snaps: dict[str, AIScoreSnapshot] = {}
    for row in report.users:
        snaps[row.user_id] = _upsert_snapshot(
            db, org_id, period, ps, pe, row, role_profile,
        )
    db.commit()

    # Team median for executive mode
    team_median: float | None = None
    if mode == "executive" and report.users:
        ts = sorted(snaps[r.user_id].score for r in report.users)
        m = len(ts) // 2
        team_median = float(ts[m]) if len(ts) % 2 else (ts[m - 1] + ts[m]) / 2.0

    cards: list[AIScorecard] = []
    for row in report.users:
        snap = snaps[row.user_id]
        baseline = _load_baseline(db, org_id, row.user_id, period, ps)
        reasons  = _build_reasons(snap, baseline)
        trend    = _load_trend(db, org_id, row.user_id, period, ps, trend_limit)
        base_drv = _load_driver_baseline(db, org_id, row.user_id, period, ps)

        cur_d: dict = {}
        if snap.drivers_json:
            try:
                cur_d = json.loads(snap.drivers_json)
            except (json.JSONDecodeError, TypeError):
                cur_d = {}

        drivers_list = _build_primary_drivers(role_profile, cur_d, base_drv)
        grade_str    = _grade(snap.score)
        burnout      = _assess_burnout(cur_d, base_drv, trend, snap.active_ratio)
        recs         = _generate_recommendations(
            snap.score, cur_d, base_drv, role_profile, burnout,
        )
        interp = _build_interpretation(
            snap, baseline, drivers_list, trend, mode, team_median,
            role_profile, burnout, recs, cur_d, base_drv, grade_str,
        )
        delta_score = snap.score - baseline.avg_score if baseline else None

        cards.append(AIScorecard(
            org_id=org_id, user_id=row.user_id, full_name=row.full_name,
            period_type=period.value, period_start=ps, period_end=pe,
            current=AIScoreSnapshotResponse.model_validate(snap),
            baseline=baseline, delta_score=delta_score,
            trend=trend, reasons=reasons, interpretation=interp,
        ))

    return cards

from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Return current UTC datetime as naive value for legacy DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)



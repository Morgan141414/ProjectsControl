import httpx

from app.core.config import settings
from app.models.enums import NotificationEvent
from app.models.notification import NotificationHook


def send_notification(
    db,
    org_id: str,
    event_type: NotificationEvent,
    payload: dict,
) -> None:
    hooks = (
        db.query(NotificationHook)
        .filter(
            NotificationHook.org_id == org_id,
            NotificationHook.event_type == event_type,
            NotificationHook.enabled.is_(True),
        )
        .all()
    )
    if not hooks:
        return

    timeout = settings.REPORTS_WEBHOOK_TIMEOUT_SECONDS
    for hook in hooks:
        try:
            httpx.post(hook.url, json=payload, timeout=timeout)
        except httpx.HTTPError:
            continue

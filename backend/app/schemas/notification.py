from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationEvent


class NotificationHookCreate(BaseModel):
    event_type: NotificationEvent
    url: str = Field(min_length=10, max_length=500)
    enabled: bool = True


class NotificationHookUpdate(BaseModel):
    url: str | None = Field(default=None, min_length=10, max_length=500)
    enabled: bool | None = None


class NotificationHookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    org_id: str
    event_type: NotificationEvent
    url: str
    enabled: bool

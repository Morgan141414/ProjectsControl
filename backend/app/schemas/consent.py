from datetime import datetime

from pydantic import BaseModel, Field


class ConsentRequest(BaseModel):
    policy_version: str = Field(min_length=1, max_length=50)


class ConsentStatus(BaseModel):
    org_id: str
    user_id: str
    accepted: bool
    accepted_at: datetime | None
    policy_version: str | None

from datetime import datetime
from pydantic import BaseModel


class InvitationCreate(BaseModel):
    email: str
    role: str = "member"
    team_id: str | None = None


class InvitationOut(BaseModel):
    id: str
    org_id: str
    email: str
    token: str
    role: str
    team_id: str | None
    status: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationAccept(BaseModel):
    token: str

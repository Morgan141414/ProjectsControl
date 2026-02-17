from datetime import datetime
from pydantic import BaseModel


class AIChatMessage(BaseModel):
    message: str


class AIChatResponse(BaseModel):
    response: str
    tokens_used: int


class AIAssistantSettings(BaseModel):
    is_enabled: bool | None = None
    model: str | None = None
    monthly_tokens_limit: int | None = None


class AIAssistantOut(BaseModel):
    id: str
    org_id: str
    is_enabled: bool
    model: str
    monthly_tokens_limit: int
    tokens_used_this_month: int
    created_at: datetime

    class Config:
        from_attributes = True


class AIConversationOut(BaseModel):
    id: str
    org_id: str
    user_id: str
    tokens_used: int
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True

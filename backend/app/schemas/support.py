from datetime import datetime
from pydantic import BaseModel


class TicketCreate(BaseModel):
    org_id: str | None = None
    category: str = "other"
    priority: str = "medium"
    subject: str
    description: str


class TicketUpdate(BaseModel):
    status: str | None = None
    priority: str | None = None
    resolution: str | None = None


class TicketOut(BaseModel):
    id: str
    ticket_number: str
    org_id: str | None
    user_id: str
    assigned_to: str | None
    category: str
    priority: str
    status: str
    subject: str
    description: str
    resolution: str | None
    satisfaction_rating: int | None
    created_at: datetime
    updated_at: datetime | None
    resolved_at: datetime | None

    class Config:
        from_attributes = True


class TicketMessageCreate(BaseModel):
    message: str
    is_internal: bool = False


class TicketMessageOut(BaseModel):
    id: str
    ticket_id: str
    sender_id: str
    message: str
    is_internal: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TicketRating(BaseModel):
    rating: int  # 1-5


class FAQCreate(BaseModel):
    category: str
    title: str
    content: str


class FAQOut(BaseModel):
    id: str
    category: str
    title: str
    content: str
    views_count: int
    helpful_count: int
    is_published: bool
    created_at: datetime

    class Config:
        from_attributes = True

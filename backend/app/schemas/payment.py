from datetime import datetime
from pydantic import BaseModel


class PaymentCreate(BaseModel):
    amount: float
    payment_type: str
    org_id: str | None = None


class PaymentOut(BaseModel):
    id: str
    user_id: str
    org_id: str | None
    amount: float
    currency: str
    payment_type: str
    status: str
    provider: str
    external_id: str | None
    created_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


class BanCreate(BaseModel):
    user_id: str
    org_id: str | None = None
    reason: str
    ban_type: str = "temporary"
    days: int | None = None


class BanOut(BaseModel):
    id: str
    user_id: str
    org_id: str | None
    reason: str
    ban_type: str
    starts_at: datetime
    ends_at: datetime | None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BanAppealCreate(BaseModel):
    reason: str
    payment_option: bool = False


class BanAppealOut(BaseModel):
    id: str
    ban_id: str
    user_id: str
    reason: str
    status: str
    payment_option: bool
    created_at: datetime

    class Config:
        from_attributes = True

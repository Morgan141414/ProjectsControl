from datetime import datetime
from pydantic import BaseModel


class CertificateCreate(BaseModel):
    org_id: str
    owner_id: str
    valid_months: int = 12
    industry: str | None = None
    legal_name: str | None = None
    inn: str | None = None
    max_employees: int = 50


class CertificateOut(BaseModel):
    id: str
    org_id: str
    certificate_number: str
    issued_at: datetime
    valid_from: datetime
    valid_until: datetime
    owner_id: str | None
    issued_by_id: str | None
    status: str
    industry: str | None
    legal_name: str | None
    inn: str | None
    max_employees: int
    created_at: datetime

    class Config:
        from_attributes = True


class CertificateRenew(BaseModel):
    months: int = 12

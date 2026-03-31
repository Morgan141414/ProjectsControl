from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import CertificateStatus
from app.utils.ids import new_id


def _new_cert_number() -> str:
    import uuid
    from datetime import datetime as dt
    return f"CERT-{dt.utcnow().strftime('%Y')}-{uuid.uuid4().hex[:8].upper()}"


class OrganizationCertificate(Base):
    __tablename__ = "organization_certificates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    certificate_number: Mapped[str] = mapped_column(String(50), unique=True, default=_new_cert_number)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    valid_from: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    owner_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    issued_by_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[CertificateStatus] = mapped_column(
        SAEnum(CertificateStatus), default=CertificateStatus.active
    )
    industry: Mapped[str | None] = mapped_column(String(100))
    legal_name: Mapped[str | None] = mapped_column(String(500))
    inn: Mapped[str | None] = mapped_column(String(20))
    max_employees: Mapped[int] = mapped_column(Integer, default=50)
    tariff_plan_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tariff_plans.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    organization = relationship("Organization", foreign_keys=[org_id])
    owner = relationship("User", foreign_keys=[owner_id])
    issued_by = relationship("User", foreign_keys=[issued_by_id])

from datetime import datetime, timedelta

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.time import utc_now_naive
from app.db.base import Base
from app.models.enums import InvitationStatus, OrgRole
from app.utils.ids import new_id


def _default_expiry() -> datetime:
    return utc_now_naive() + timedelta(days=7)


def _new_invite_token() -> str:
    import secrets
    return secrets.token_urlsafe(32)


class Invitation(Base):
    __tablename__ = "invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    invited_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(100), unique=True, default=_new_invite_token)
    role: Mapped[OrgRole] = mapped_column(SAEnum(OrgRole), default=OrgRole.member)
    team_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("teams.id"))
    status: Mapped[InvitationStatus] = mapped_column(
        SAEnum(InvitationStatus), default=InvitationStatus.pending
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, default=_default_expiry)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now_naive)

    organization = relationship("Organization", foreign_keys=[org_id])
    inviter = relationship("User", foreign_keys=[invited_by])

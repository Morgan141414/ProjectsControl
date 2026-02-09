from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import JoinStatus, OrgRole
from app.utils.codes import new_join_code
from app.utils.ids import new_id


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    join_code: Mapped[str] = mapped_column(
        String(16), unique=True, index=True, default=new_join_code
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships = relationship(
        "OrgMembership", back_populates="organization", cascade="all, delete-orphan"
    )
    join_requests = relationship(
        "OrgJoinRequest", back_populates="organization", cascade="all, delete-orphan"
    )
    teams = relationship("Team", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship(
        "Project", back_populates="organization", cascade="all, delete-orphan"
    )
    tasks = relationship("Task", back_populates="organization", cascade="all, delete-orphan")


class OrgMembership(Base):
    __tablename__ = "org_memberships"

    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), primary_key=True)
    role: Mapped[OrgRole] = mapped_column(SAEnum(OrgRole), default=OrgRole.member)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="org_memberships")


class OrgJoinRequest(Base):
    __tablename__ = "org_join_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    org_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    status: Mapped[JoinStatus] = mapped_column(SAEnum(JoinStatus), default=JoinStatus.pending)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="join_requests")
    user = relationship("User")

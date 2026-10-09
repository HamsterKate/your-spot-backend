import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def get_invite_expiration() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=7)


class GroupInvitationModel(Base):
    __tablename__ = "group_invitations"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    group_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("groups.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    created_by_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        default=generate_invite_token,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_invite_expiration,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

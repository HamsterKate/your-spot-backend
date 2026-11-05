from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.users.models import UserModel


class PlaceModel(Base):
    __tablename__ = "places"
    __table_args__ = (
        CheckConstraint(
            "latitude >= -90 AND latitude <= 90",
            name="places_latitude_valid",
        ),
        CheckConstraint(
            "longitude >= -180 AND longitude <= 180",
            name="places_longitude_valid",
        ),
        Index(
            "ix_places_latitude_longitude",
            "latitude",
            "longitude",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    creator_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    creator: Mapped["UserModel"] = relationship(
        foreign_keys=[creator_id],
        viewonly=True,
        lazy="raise",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(String(500))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    opening_hours: Mapped[JSONB | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    categories: Mapped[list["CategoryModel"]] = relationship(
        secondary="place_categories",
        viewonly=True,
        lazy="selectin",
    )
    tags: Mapped[list["TagModel"]] = relationship(
        secondary="place_tags",
        viewonly=True,
        lazy="selectin",
    )
    photos: Mapped[list["PlacePhotoModel"]] = relationship(
        back_populates="place",
        cascade="all, delete-orphan",
        order_by="PlacePhotoModel.position",
        lazy="selectin",
    )

    @property
    def creator_name(self) -> str:
        return self.creator.display_name


class PlacePhotoModel(Base):
    __tablename__ = "place_photos"
    __table_args__ = (
        UniqueConstraint(
            "place_id",
            "position",
            name="place_photos_place_id_position_unique",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    place_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
    )
    content_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    position: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    place: Mapped["PlaceModel"] = relationship(
        back_populates="photos",
    )


class CategoryModel(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class TagModel(Base):
    __tablename__ = "tags"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class PlaceCategoryModel(Base):
    __tablename__ = "place_categories"

    place_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )


class PlaceTagModel(Base):
    __tablename__ = "place_tags"

    place_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("places.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )

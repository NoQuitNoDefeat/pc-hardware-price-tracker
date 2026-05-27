"""TrackedOffer ORM model: a manually confirmed offer for a Product on one platform."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import OfferStatus

if TYPE_CHECKING:
    from app.models.price_snapshot import PriceSnapshot
    from app.models.product import Product


class TrackedOffer(Base):
    __tablename__ = "tracked_offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "products.id",
            name="fk_tracked_offers_product_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(String(64), nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_url: Mapped[str] = mapped_column(Text, nullable=False)
    url_key: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    platform_item_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    platform_sku_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title_at_confirm: Mapped[str | None] = mapped_column(String(512), nullable=True)
    shop_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manual_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=OfferStatus.NEEDS_REVIEW.value,
        server_default=text("'needs_review'"),
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    product: Mapped["Product"] = relationship("Product", back_populates="tracked_offers")
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(
        "PriceSnapshot",
        back_populates="tracked_offer",
        passive_deletes="all",
    )

    __table_args__ = (
        UniqueConstraint("url_key", name="uq_tracked_offers_url_key"),
        CheckConstraint(
            "status IN ('active', 'temporarily_failed', 'needs_review', 'unavailable', 'disabled')",
            name="ck_tracked_offers_status",
        ),
        Index("idx_tracked_offers_product_id", "product_id"),
        Index("idx_tracked_offers_platform", "platform"),
        Index("idx_tracked_offers_status", "status"),
        Index("idx_tracked_offers_last_checked_at", "last_checked_at"),
    )

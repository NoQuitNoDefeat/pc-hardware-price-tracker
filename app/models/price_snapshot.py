"""PriceSnapshot ORM model: an immutable price observation tied to one TrackedOffer."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.tracked_offer import TrackedOffer


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tracked_offer_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "tracked_offers.id",
            name="fk_price_snapshots_tracked_offer_id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    title_seen: Mapped[str | None] = mapped_column(String(512), nullable=True)
    shop_seen: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stock_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    promotion_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.current_timestamp(),
    )

    tracked_offer: Mapped["TrackedOffer"] = relationship(
        "TrackedOffer",
        back_populates="price_snapshots",
    )

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_price_snapshots_price_nonneg"),
        CheckConstraint(
            "source_type IN ('manual_input', 'web_public', 'web_logged_in', 'manual_app_check')",
            name="ck_price_snapshots_source_type",
        ),
        Index(
            "idx_price_snapshots_offer_captured",
            "tracked_offer_id",
            "captured_at",
        ),
        Index("idx_price_snapshots_source_type", "source_type"),
    )

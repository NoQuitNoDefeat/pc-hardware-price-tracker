"""initial domain tables: products, tracked_offers, price_snapshots

Revision ID: 20260527_0001
Revises:
Create Date: 2026-05-27

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260527_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("brand", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "is_archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_products"),
    )
    op.create_index("idx_products_brand_model", "products", ["brand", "model"])
    op.create_index("idx_products_category", "products", ["category"])

    op.create_table(
        "tracked_offers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("platform", sa.String(length=64), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("normalized_url", sa.Text(), nullable=False),
        sa.Column("url_key", sa.CHAR(length=64), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=True),
        sa.Column("platform_item_id", sa.String(length=128), nullable=True),
        sa.Column("platform_sku_id", sa.String(length=128), nullable=True),
        sa.Column("title_at_confirm", sa.String(length=512), nullable=True),
        sa.Column("shop_name", sa.String(length=128), nullable=True),
        sa.Column(
            "manual_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'needs_review'"),
        ),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "consecutive_failures",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_tracked_offers"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_tracked_offers_product_id",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("url_key", name="uq_tracked_offers_url_key"),
        sa.CheckConstraint(
            "status IN ('active', 'temporarily_failed', 'needs_review', 'unavailable', 'disabled')",
            name="ck_tracked_offers_status",
        ),
    )
    op.create_index("idx_tracked_offers_product_id", "tracked_offers", ["product_id"])
    op.create_index("idx_tracked_offers_platform", "tracked_offers", ["platform"])
    op.create_index("idx_tracked_offers_status", "tracked_offers", ["status"])
    op.create_index(
        "idx_tracked_offers_last_checked_at",
        "tracked_offers",
        ["last_checked_at"],
    )

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tracked_offer_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("currency", sa.CHAR(length=3), nullable=False),
        sa.Column("title_seen", sa.String(length=512), nullable=True),
        sa.Column("shop_seen", sa.String(length=128), nullable=True),
        sa.Column("stock_status", sa.String(length=32), nullable=True),
        sa.Column("promotion_text", sa.Text(), nullable=True),
        sa.Column("screenshot_path", sa.Text(), nullable=True),
        sa.Column("source_context", sa.Text(), nullable=True),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.current_timestamp(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_price_snapshots"),
        sa.ForeignKeyConstraint(
            ["tracked_offer_id"],
            ["tracked_offers.id"],
            name="fk_price_snapshots_tracked_offer_id",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "price >= 0",
            name="ck_price_snapshots_price_nonneg",
        ),
        sa.CheckConstraint(
            "source_type IN ('manual_input', 'web_public', 'web_logged_in', 'manual_app_check')",
            name="ck_price_snapshots_source_type",
        ),
    )
    op.create_index(
        "idx_price_snapshots_offer_captured",
        "price_snapshots",
        ["tracked_offer_id", "captured_at"],
    )
    op.create_index(
        "idx_price_snapshots_source_type",
        "price_snapshots",
        ["source_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_price_snapshots_source_type", table_name="price_snapshots")
    op.drop_index("idx_price_snapshots_offer_captured", table_name="price_snapshots")
    op.drop_table("price_snapshots")

    op.drop_index("idx_tracked_offers_last_checked_at", table_name="tracked_offers")
    op.drop_index("idx_tracked_offers_status", table_name="tracked_offers")
    op.drop_index("idx_tracked_offers_platform", table_name="tracked_offers")
    op.drop_index("idx_tracked_offers_product_id", table_name="tracked_offers")
    op.drop_table("tracked_offers")

    op.drop_index("idx_products_category", table_name="products")
    op.drop_index("idx_products_brand_model", table_name="products")
    op.drop_table("products")

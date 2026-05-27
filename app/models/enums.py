"""String-valued enums for domain constants. Stored as strings in the database."""

from __future__ import annotations

from enum import StrEnum


class OfferStatus(StrEnum):
    ACTIVE = "active"
    TEMPORARILY_FAILED = "temporarily_failed"
    NEEDS_REVIEW = "needs_review"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class SourceType(StrEnum):
    MANUAL_INPUT = "manual_input"
    WEB_PUBLIC = "web_public"
    WEB_LOGGED_IN = "web_logged_in"
    MANUAL_APP_CHECK = "manual_app_check"


class StockStatus(StrEnum):
    IN_STOCK = "in_stock"
    LOW_STOCK = "low_stock"
    OUT_OF_STOCK = "out_of_stock"
    PREORDER = "preorder"
    UNKNOWN = "unknown"


class ProductCategory(StrEnum):
    CPU = "cpu"
    GPU = "gpu"
    SSD = "ssd"
    RAM = "ram"
    MOBO = "mobo"
    PSU = "psu"
    CASE = "case"
    COOLER = "cooler"
    OTHER = "other"

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProductOut(BaseModel):
    id: int
    site_id: int
    name: str
    brand: str | None
    model: str | None
    season: str | None
    tire_size: str | None
    radius: str | None
    width: int | None
    profile: int | None
    diameter: int | None
    url: str
    min_price: float | None = None
    max_price: float | None = None
    current_price: float | None = None
    updated_at: datetime | None = None


class PriceHistoryPoint(BaseModel):
    scraped_at: datetime
    price: float
    old_price: float | None
    site_name: str


class SiteOut(BaseModel):
    id: int
    name: str
    base_url: str
    catalog_url: str
    is_active: bool


class AlertRuleIn(BaseModel):
    rule_type: str
    threshold_pct: float = 5.0
    brand: str | None = None
    season: str | None = None
    site_name: str | None = None
    chat_id: str


class AlertRuleOut(AlertRuleIn):
    id: int
    is_active: bool
    created_at: datetime

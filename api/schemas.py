from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProductOut(BaseModel):
    id: int
    site_id: int
    site_name: str | None = None
    name: str
    brand: str | None
    model: str | None
    season: str | None
    spike: bool | None = None
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
    in_stock: bool | None = None


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


class SiteStatusUpdateIn(BaseModel):
    is_active: bool


class SiteStatusItemIn(BaseModel):
    id: int
    is_active: bool


class SitesBulkStatusUpdateIn(BaseModel):
    items: list[SiteStatusItemIn]


class ParsingSettingsOut(BaseModel):
    winter: bool = True
    winter_studded: bool = True
    winter_non_studded: bool = True
    summer: bool = True
    parse_interval_hours: int = Field(default=6, ge=1, le=168)


class AlertSettingsOut(BaseModel):
    enabled: bool = True
    min_change_pct: float = Field(default=5.0, ge=0.1, le=100.0)
    send_price_drop: bool = True
    send_price_rise: bool = True


class RuntimeSettingsOut(BaseModel):
    parsing: ParsingSettingsOut
    alerts: AlertSettingsOut


class ParsingSettingsPatchIn(BaseModel):
    winter: bool | None = None
    winter_studded: bool | None = None
    winter_non_studded: bool | None = None
    summer: bool | None = None
    parse_interval_hours: int | None = Field(default=None, ge=1, le=168)


class AlertSettingsPatchIn(BaseModel):
    enabled: bool | None = None
    min_change_pct: float | None = Field(default=None, ge=0.1, le=100.0)
    send_price_drop: bool | None = None
    send_price_rise: bool | None = None


class RuntimeSettingsPatchIn(BaseModel):
    parsing: ParsingSettingsPatchIn | None = None
    alerts: AlertSettingsPatchIn | None = None

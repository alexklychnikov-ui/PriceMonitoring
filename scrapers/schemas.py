from __future__ import annotations

from pydantic import BaseModel


class ProductDTO(BaseModel):
    external_id: str
    name: str
    brand: str
    model: str
    season: str
    tire_size: str
    radius: str
    width: int
    profile: int
    diameter: int
    price: float
    old_price: float | None = None
    discount_pct: float | None = None
    in_stock: bool = True
    url: str
    site_name: str

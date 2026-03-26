from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    catalog_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="site", cascade="all, delete-orphan")
    parse_runs: Mapped[list["ParseRun"]] = relationship(back_populates="site")

    def __repr__(self) -> str:
        return f"Site(id={self.id!r}, name={self.name!r}, is_active={self.is_active!r})"


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("site_id", "external_id", name="uq_products_site_external"),
        Index("idx_products_tire_size_radius", "tire_size", "radius"),
        Index("idx_products_brand_tire_size_radius", "brand", "tire_size", "radius"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    brand: Mapped[Optional[str]] = mapped_column(String(255))
    model: Mapped[Optional[str]] = mapped_column(String(255))
    season: Mapped[Optional[str]] = mapped_column(String(32))
    spike: Mapped[Optional[bool]] = mapped_column(Boolean)
    tire_size: Mapped[Optional[str]] = mapped_column(String(10))
    radius: Mapped[Optional[str]] = mapped_column(String(5))
    width: Mapped[Optional[int]] = mapped_column(Integer)
    profile: Mapped[Optional[int]] = mapped_column(Integer)
    diameter: Mapped[Optional[int]] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    site: Mapped["Site"] = relationship(back_populates="products")
    price_history: Mapped[list["PriceHistory"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="product", cascade="all, delete-orphan")
    subscriptions: Mapped[list["UserSubscription"]] = relationship(back_populates="product", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"Product(id={self.id!r}, site_id={self.site_id!r}, external_id={self.external_id!r}, name={self.name!r})"


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (Index("idx_price_history_product_scraped_at", "product_id", "scraped_at"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    old_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
    discount_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    in_stock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="price_history")

    def __repr__(self) -> str:
        return f"PriceHistory(id={self.id!r}, product_id={self.product_id!r}, price={self.price!r})"


class ParseRun(Base):
    __tablename__ = "parse_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    site_id: Mapped[Optional[int]] = mapped_column(ForeignKey("sites.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(32), nullable=False, default="scheduled")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    products_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    site: Mapped[Optional["Site"]] = relationship(back_populates="parse_runs")

    def __repr__(self) -> str:
        return f"ParseRun(id={self.id!r}, site_id={self.site_id!r}, status={self.status!r})"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value: Mapped[Optional[str]] = mapped_column(Text)
    new_value: Mapped[Optional[str]] = mapped_column(Text)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    product: Mapped["Product"] = relationship(back_populates="alerts")

    def __repr__(self) -> str:
        return f"Alert(id={self.id!r}, product_id={self.product_id!r}, alert_type={self.alert_type!r})"


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"
    __table_args__ = (
        UniqueConstraint("chat_id", "product_id", name="uq_user_subscriptions_chat_product"),
        Index("idx_subscriptions_product_active", "product_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[str] = mapped_column(String(50), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    threshold_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=5.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    product: Mapped["Product"] = relationship(back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"UserSubscription(id={self.id!r}, chat_id={self.chat_id!r}, product_id={self.product_id!r})"


class AlertRuleModel(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    rule_type: Mapped[str] = mapped_column(String(32), nullable=False)
    threshold_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=5.0)
    brand: Mapped[Optional[str]] = mapped_column(String(255))
    season: Mapped[Optional[str]] = mapped_column(String(32))
    site_name: Mapped[Optional[str]] = mapped_column(String(255))
    chat_id: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self) -> str:
        return f"AlertRuleModel(id={self.id!r}, rule_type={self.rule_type!r}, chat_id={self.chat_id!r})"

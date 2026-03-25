from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel
from sqlalchemy import select

from db.database import AsyncSessionLocal
from db.models import Alert, AlertRuleModel, Product, UserSubscription


class AlertRule(BaseModel):
    rule_type: str
    threshold_pct: float
    brand: str | None = None
    season: str | None = None
    site_name: str | None = None
    chat_id: str


@dataclass
class AlertCandidate:
    rule: AlertRule
    change_pct: float


class AlertEngine:
    async def get_global_rules(self) -> list[AlertRule]:
        async with AsyncSessionLocal() as session:
            rows = list(await session.scalars(select(AlertRuleModel).where(AlertRuleModel.is_active.is_(True))))
            return [
                AlertRule(
                    rule_type=row.rule_type,
                    threshold_pct=float(row.threshold_pct),
                    brand=row.brand,
                    season=row.season,
                    site_name=row.site_name,
                    chat_id=row.chat_id,
                )
                for row in rows
            ]

    async def get_user_subscriptions(self, product_id: int) -> list[AlertRule]:
        async with AsyncSessionLocal() as session:
            rows = list(
                await session.scalars(
                    select(UserSubscription).where(
                        UserSubscription.product_id == product_id,
                        UserSubscription.is_active.is_(True),
                    )
                )
            )
            return [
                AlertRule(
                    rule_type="price_drop",
                    threshold_pct=float(row.threshold_pct),
                    chat_id=row.chat_id,
                )
                for row in rows
            ]

    async def check_and_create_alerts(
        self,
        product: Product,
        old_price: float,
        new_price: float,
        site_name: str,
    ) -> list[Alert]:
        if old_price <= 0:
            return []
        change_pct = ((new_price - old_price) / old_price) * 100
        global_rules = await self.get_global_rules()
        user_rules = await self.get_user_subscriptions(product.id)
        rules = global_rules + user_rules

        matches: list[AlertCandidate] = []
        for rule in rules:
            if rule.brand and product.brand and rule.brand.lower() != product.brand.lower():
                continue
            if rule.season and product.season and rule.season.lower() != product.season.lower():
                continue
            if rule.site_name and rule.site_name != site_name:
                continue

            threshold = abs(rule.threshold_pct)
            if rule.rule_type == "price_drop" and change_pct <= -threshold:
                matches.append(AlertCandidate(rule=rule, change_pct=change_pct))
            elif rule.rule_type == "price_rise" and change_pct >= threshold:
                matches.append(AlertCandidate(rule=rule, change_pct=change_pct))
            elif rule.rule_type == "new_low" and change_pct < 0:
                matches.append(AlertCandidate(rule=rule, change_pct=change_pct))

        created: list[Alert] = []
        if not matches:
            return created

        async with AsyncSessionLocal() as session:
            for candidate in matches:
                alert = Alert(
                    product_id=product.id,
                    alert_type=candidate.rule.rule_type,
                    old_value=str(old_price),
                    new_value=str(new_price),
                )
                session.add(alert)
                created.append(alert)
            await session.flush()
            await session.commit()
        return created

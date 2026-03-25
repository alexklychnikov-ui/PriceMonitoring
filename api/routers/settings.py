from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from api.schemas import AlertRuleIn
from db.database import AsyncSessionLocal
from db.models import AlertRuleModel, Site
from scheduler.tasks import scrape_site


router = APIRouter()


@router.get("/sites")
async def get_sites_settings() -> list[dict]:
    async with AsyncSessionLocal() as session:
        rows = list(await session.scalars(select(Site).order_by(Site.name.asc())))
        return [
            {
                "id": s.id,
                "name": s.name,
                "is_active": s.is_active,
                "base_url": s.base_url,
                "catalog_url": s.catalog_url,
            }
            for s in rows
        ]


@router.put("/sites/{site_id}")
async def update_site_status(site_id: int, is_active: bool) -> dict:
    async with AsyncSessionLocal() as session:
        site = await session.get(Site, site_id)
        if site is None:
            raise HTTPException(status_code=404, detail="Site not found")
        site.is_active = is_active
        await session.commit()
        return {"ok": True, "id": site.id, "is_active": site.is_active}


@router.post("/scrape-now/{site_name}")
async def scrape_now(site_name: str) -> dict:
    result = scrape_site.delay(site_name)
    return {"task_id": result.id, "site_name": site_name}


@router.get("/alert-rules")
async def get_alert_rules() -> list[dict]:
    async with AsyncSessionLocal() as session:
        rows = list(await session.scalars(select(AlertRuleModel).order_by(AlertRuleModel.created_at.desc())))
        return [
            {
                "id": r.id,
                "rule_type": r.rule_type,
                "threshold_pct": float(r.threshold_pct),
                "brand": r.brand,
                "season": r.season,
                "site_name": r.site_name,
                "chat_id": r.chat_id,
                "is_active": r.is_active,
                "created_at": r.created_at,
            }
            for r in rows
        ]


@router.post("/alert-rules")
async def create_alert_rule(payload: AlertRuleIn) -> dict:
    async with AsyncSessionLocal() as session:
        row = AlertRuleModel(
            rule_type=payload.rule_type,
            threshold_pct=Decimal(str(payload.threshold_pct)),
            brand=payload.brand,
            season=payload.season,
            site_name=payload.site_name,
            chat_id=payload.chat_id,
            is_active=True,
        )
        session.add(row)
        await session.flush()
        await session.commit()
        return {"id": row.id, "ok": True}


@router.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(rule_id: int) -> dict:
    async with AsyncSessionLocal() as session:
        await session.execute(delete(AlertRuleModel).where(AlertRuleModel.id == rule_id))
        await session.commit()
    return {"ok": True, "id": rule_id}

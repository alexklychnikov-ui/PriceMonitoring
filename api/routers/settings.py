from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, func, select

from api.schemas import AlertRuleIn, RuntimeSettingsPatchIn, SitesBulkStatusUpdateIn, SiteStatusUpdateIn
from db.database import AsyncSessionLocal
from db.models import AlertRuleModel, ParseRun, Site
from runtime_settings import get_runtime_settings, merge_runtime_settings, save_runtime_settings
from scheduler.tasks import scrape_all_sites, scrape_site


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
async def update_site_status(site_id: int, payload: SiteStatusUpdateIn) -> dict:
    async with AsyncSessionLocal() as session:
        site = await session.get(Site, site_id)
        if site is None:
            raise HTTPException(status_code=404, detail="Site not found")
        site.is_active = payload.is_active
        await session.commit()
        return {"ok": True, "id": site.id, "is_active": site.is_active}


@router.put("/sites")
async def update_sites_bulk_status(payload: SitesBulkStatusUpdateIn) -> dict:
    if not payload.items:
        return {"ok": True, "updated": 0, "items": []}

    async with AsyncSessionLocal() as session:
        items_by_id = {item.id: item.is_active for item in payload.items}
        rows = list(await session.scalars(select(Site).where(Site.id.in_(items_by_id.keys()))))
        if len(rows) != len(items_by_id):
            existing_ids = {row.id for row in rows}
            missing_ids = sorted(set(items_by_id.keys()) - existing_ids)
            raise HTTPException(status_code=404, detail=f"Sites not found: {missing_ids}")

        for row in rows:
            row.is_active = bool(items_by_id[row.id])
        await session.commit()
        return {
            "ok": True,
            "updated": len(rows),
            "items": [{"id": row.id, "is_active": row.is_active} for row in rows],
        }


@router.get("/parsing-status")
async def get_parsing_status() -> dict:
    runtime = await get_runtime_settings()
    interval_hours = int(runtime["parsing"]["parse_interval_hours"])

    async with AsyncSessionLocal() as session:
        active_site_ids = list(await session.scalars(select(Site.id).where(Site.is_active.is_(True))))
        active_sites_count = len(active_site_ids)
        if not active_site_ids:
            return {
                "active_sites_count": 0,
                "interval_hours": interval_hours,
                "last_started_at": None,
                "next_update_at": None,
                "running_sites": 0,
            }

        last_started_at = await session.scalar(
            select(func.max(ParseRun.started_at)).where(ParseRun.site_id.in_(active_site_ids))
        )
        running_sites = int(
            await session.scalar(
                select(func.count(ParseRun.id)).where(
                    ParseRun.site_id.in_(active_site_ids),
                    ParseRun.status == "running",
                    ParseRun.finished_at.is_(None),
                )
            )
            or 0
        )

    next_update_at = None
    if last_started_at is not None:
        next_update_at = last_started_at + timedelta(hours=max(interval_hours, 1))

    return {
        "active_sites_count": active_sites_count,
        "interval_hours": interval_hours,
        "last_started_at": last_started_at,
        "next_update_at": next_update_at,
        "running_sites": running_sites,
    }


@router.post("/scrape-now")
async def scrape_now_all_active_sites() -> dict:
    async with AsyncSessionLocal() as session:
        active_names = list(await session.scalars(select(Site.name).where(Site.is_active.is_(True)).order_by(Site.name.asc())))
    if not active_names:
        raise HTTPException(status_code=400, detail="Нет активных сайтов для запуска парсинга")

    result = scrape_all_sites.delay(True, "manual")
    return {"ok": True, "sites_count": len(active_names), "sites": active_names, "task_id": result.id}


@router.post("/scrape-now/{site_name}")
async def scrape_now(site_name: str) -> dict:
    async with AsyncSessionLocal() as session:
        site = await session.scalar(select(Site).where(Site.name == site_name))
        if site is not None and not site.is_active:
            raise HTTPException(status_code=400, detail="Site is disabled in settings")
    result = scrape_site.delay(site_name, True, "manual")
    return {"task_id": result.id, "site_name": site_name}


@router.get("/runtime")
async def get_runtime_config() -> dict:
    return await get_runtime_settings()


@router.put("/runtime")
async def update_runtime_config(payload: RuntimeSettingsPatchIn) -> dict:
    current = await get_runtime_settings()
    patch = payload.model_dump(exclude_none=True)
    merged = merge_runtime_settings(current, patch)
    return await save_runtime_settings(merged)


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

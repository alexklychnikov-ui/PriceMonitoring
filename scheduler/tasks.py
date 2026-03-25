from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from celery import chord, group
from redis.asyncio import Redis
from sqlalchemy import delete, func, select

from ai_analysis.recommendation_engine import RecommendationEngine
from config import settings
from db.database import AsyncSessionLocal
from db.models import Alert, ParseRun, PriceHistory, Product, Site
from notifications.telegram import send_alert
from notifications.telegram_bot import run_bot
from scheduler.celery_app import app
from scrapers import SCRAPERS_REGISTRY
from scrapers.db_writer import upsert_product


logger = logging.getLogger(__name__)


async def _get_or_create_site(session, site_name: str) -> Site:
    site = await session.scalar(select(Site).where(Site.name == site_name))
    if site is not None:
        return site
    scraper_cls = SCRAPERS_REGISTRY[site_name]
    site = Site(
        name=site_name,
        base_url=scraper_cls.base_url,
        catalog_url=scraper_cls.catalog_url,
        is_active=True,
    )
    session.add(site)
    await session.flush()
    return site


async def _run_scrape_site(site_name: str) -> dict[str, Any]:
    scraper_cls = SCRAPERS_REGISTRY.get(site_name)
    if scraper_cls is None:
        raise ValueError(f"Unknown site: {site_name}")

    async with AsyncSessionLocal() as session:
        site = await _get_or_create_site(session, site_name)
        run = ParseRun(
            site_id=site.id,
            status="running",
            started_at=datetime.now(timezone.utc),
            products_found=0,
            errors_count=0,
        )
        session.add(run)
        await session.flush()
        await session.commit()

    try:
        scraper = scraper_cls()
        products = await scraper.run()
        async with AsyncSessionLocal() as session:
            run = await session.get(ParseRun, run.id)
            for dto in products:
                await upsert_product(session, dto, site_id=site.id)
            run.status = "success"
            run.finished_at = datetime.now(timezone.utc)
            run.products_found = len(products)
            await session.commit()
        return {"site_name": site_name, "status": "success", "products_found": len(products)}
    except Exception as error:
        async with AsyncSessionLocal() as session:
            run = await session.get(ParseRun, run.id)
            if run is not None:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.errors_count = (run.errors_count or 0) + 1
                await session.commit()
        logger.exception("Scrape failed for site=%s error=%s", site_name, type(error).__name__)
        raise


@app.task(bind=True, max_retries=3, default_retry_delay=60, time_limit=1800, name="scheduler.tasks.scrape_site")
def scrape_site(self, site_name: str) -> dict[str, Any]:
    try:
        return asyncio.run(_run_scrape_site(site_name))
    except Exception as error:
        raise self.retry(exc=error, countdown=60)


@app.task(bind=True, name="scheduler.tasks.scrape_all_sites")
def scrape_all_sites(self) -> dict[str, Any]:
    async def _get_active_site_names() -> list[str]:
        async with AsyncSessionLocal() as session:
            rows = await session.scalars(select(Site.name).where(Site.is_active.is_(True)))
            names = list(rows)
        if names:
            return names
        return list(SCRAPERS_REGISTRY.keys())

    names = asyncio.run(_get_active_site_names())
    task_group = group(scrape_site.s(name) for name in names)
    result = chord(task_group)(analyze_prices_task.s())
    return {"group_id": result.id, "sites_count": len(names), "sites": names}


@app.task(bind=True, name="scheduler.tasks.analyze_prices")
def analyze_prices(self) -> dict[str, Any]:
    async def _analyze() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            changed_prices = await session.scalar(select(func.count(Alert.id)).where(Alert.alert_type == "price_changed"))
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "summary": "AI analysis placeholder for stage 4",
            "changed_prices_total": int(changed_prices or 0),
        }
        redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await redis.set("analysis:last", json.dumps(payload), ex=60 * 60 * 24)
        finally:
            await redis.aclose()
        return payload

    return asyncio.run(_analyze())


@app.task(bind=True, name="scheduler.tasks.analyze_prices_task")
def analyze_prices_task(self, _group_results: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    async def _run() -> dict[str, Any]:
        engine = RecommendationEngine()
        analyzed = 0
        alerts_created = 0
        weekly_report_saved = False
        try:
            async with AsyncSessionLocal() as session:
                changed_product_ids = list(
                    await session.scalars(
                        select(Alert.product_id).where(Alert.alert_type == "price_changed").distinct()
                    )
                )
                if not changed_product_ids:
                    changed_product_ids = list(
                        await session.scalars(
                            select(Product.id).order_by(Product.updated_at.desc()).limit(25)
                        )
                    )

                for product_id in changed_product_ids:
                    result = await engine.analyze_product_price(int(product_id))
                    analyzed += 1
                    change_7d = float(result.trend_stats.get("price_change_7d_pct", 0))
                    if abs(change_7d) >= settings.PRICE_ALERT_THRESHOLD_PCT:
                        session.add(
                            Alert(
                                product_id=int(product_id),
                                alert_type="ai_threshold",
                                old_value="threshold",
                                new_value=str(change_7d),
                                triggered_at=datetime.now(timezone.utc),
                            )
                        )
                        alerts_created += 1
                await session.commit()

            if datetime.now(timezone.utc).weekday() == 6:
                await engine.generate_weekly_report()
                weekly_report_saved = True
        finally:
            await engine.close()

        return {
            "analyzed_products": analyzed,
            "alerts_created": alerts_created,
            "weekly_report_saved": weekly_report_saved,
        }

    return asyncio.run(_run())


@app.task(bind=True, name="scheduler.tasks.send_pending_alerts")
def send_pending_alerts(self) -> dict[str, Any]:
    async def _send() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            alerts = list(await session.scalars(select(Alert).where(Alert.sent_at.is_(None))))
            sent = 0
            for alert in alerts:
                product = await session.get(Product, alert.product_id)
                if product is None:
                    continue
                alert.product = product
                ok = await send_alert(alert)
                if ok:
                    alert.sent_at = datetime.now(timezone.utc)
                    sent += 1
            await session.commit()
        return {"pending": len(alerts), "sent": sent}

    return asyncio.run(_send())


@app.task(bind=True, name="scheduler.tasks.start_telegram_bot")
def start_telegram_bot(self) -> dict[str, Any]:
    asyncio.run(run_bot())
    return {"ok": True}


@app.task(bind=True, name="scheduler.tasks.cleanup_old_data")
def cleanup_old_data(self) -> dict[str, int]:
    async def _cleanup() -> dict[str, int]:
        now = datetime.now(timezone.utc)
        history_cutoff = now - timedelta(days=90)
        runs_cutoff = now - timedelta(days=30)

        async with AsyncSessionLocal() as session:
            history_result = await session.execute(
                delete(PriceHistory).where(PriceHistory.scraped_at < history_cutoff)
            )
            runs_result = await session.execute(
                delete(ParseRun).where(ParseRun.finished_at.is_not(None), ParseRun.finished_at < runs_cutoff)
            )
            await session.commit()
        return {
            "deleted_price_history": int(history_result.rowcount or 0),
            "deleted_parse_runs": int(runs_result.rowcount or 0),
        }

    return asyncio.run(_cleanup())

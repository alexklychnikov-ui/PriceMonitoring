from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from celery import chord, group
from redis.asyncio import Redis
from celery.exceptions import SoftTimeLimitExceeded
from sqlalchemy import delete, exists, func, or_, select, update
from sqlalchemy.orm import aliased
from telegram.error import RetryAfter

from ai_analysis.recommendation_engine import RecommendationEngine
from config import settings
from db.database import AsyncSessionLocal
from db.models import Alert, ParseRun, PriceHistory, Product, Site, UserSubscription
from notifications.telegram import send_alert
from runtime_settings import get_runtime_settings
from notifications.telegram_bot import run_bot
from scheduler.celery_app import app
from scrapers import SCRAPERS_REGISTRY
from scrapers.db_writer import mark_missing_products_out_of_stock, upsert_product


logger = logging.getLogger(__name__)
PRICE_ALERT_TYPES = ("price_drop", "price_rise", "price_changed", "new_low")

# Celery time_limit=1800; soft limit и asyncio дают шанс записать failed до SIGKILL.
_SCRAPER_ASYNC_TIMEOUT_SEC = 25 * 60
_CELERY_SOFT_TIME_LIMIT_SEC = 29 * 60
_STALE_PARSE_RUN_AFTER = timedelta(hours=2)


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


async def _mark_last_running_failed_for_site(site_name: str) -> None:
    async with AsyncSessionLocal() as session:
        site = await session.scalar(select(Site).where(Site.name == site_name))
        if site is None:
            return
        run = await session.scalar(
            select(ParseRun)
            .where(ParseRun.site_id == site.id, ParseRun.status == "running", ParseRun.finished_at.is_(None))
            .order_by(ParseRun.started_at.desc())
            .limit(1)
        )
        if run is None:
            return
        run.status = "failed"
        run.finished_at = datetime.now(timezone.utc)
        run.errors_count = (run.errors_count or 0) + 1
        await session.commit()


async def _run_scrape_site(site_name: str, force: bool = False, trigger_type: str = "scheduled") -> dict[str, Any]:
    scraper_cls = SCRAPERS_REGISTRY.get(site_name)
    if scraper_cls is None:
        raise ValueError(f"Unknown site: {site_name}")

    runtime = await get_runtime_settings()
    parse_interval_hours = int(runtime["parsing"]["parse_interval_hours"])

    async with AsyncSessionLocal() as session:
        site = await _get_or_create_site(session, site_name)
        if not site.is_active:
            return {"site_name": site_name, "status": "skipped", "reason": "site_disabled", "products_found": 0}

        if not force:
            last_started = await session.scalar(
                select(ParseRun.started_at)
                .where(ParseRun.site_id == site.id, ParseRun.status == "success")
                .order_by(ParseRun.started_at.desc())
                .limit(1)
            )
            if last_started is not None:
                elapsed = datetime.now(timezone.utc) - last_started
                if elapsed < timedelta(hours=max(parse_interval_hours, 1)):
                    return {
                        "site_name": site_name,
                        "status": "skipped",
                        "reason": "interval_not_reached",
                        "products_found": 0,
                    }

        run = ParseRun(
            site_id=site.id,
            status="running",
            trigger_type=trigger_type,
            started_at=datetime.now(timezone.utc),
            products_found=0,
            errors_count=0,
        )
        session.add(run)
        await session.flush()
        await session.commit()

    try:
        scraper = scraper_cls()
        scraper.parse_config = runtime["parsing"]
        alert_threshold_pct = Decimal(str(runtime["alerts"].get("min_change_pct", settings.PRICE_ALERT_THRESHOLD_PCT)))
        products = await asyncio.wait_for(scraper.run(), timeout=_SCRAPER_ASYNC_TIMEOUT_SEC)
        async with AsyncSessionLocal() as session:
            run = await session.get(ParseRun, run.id)
            seen_external_ids: set[str] = set()
            for dto in products:
                await upsert_product(
                    session,
                    dto,
                    site_id=site.id,
                    alert_threshold_pct=alert_threshold_pct,
                )
                seen_external_ids.add(dto.external_id)
            if seen_external_ids:
                await mark_missing_products_out_of_stock(session, site.id, seen_external_ids)
            run.status = "success"
            run.finished_at = datetime.now(timezone.utc)
            run.products_found = len(products)
            await session.commit()
        return {"site_name": site_name, "status": "success", "products_found": len(products)}
    except TimeoutError:
        async with AsyncSessionLocal() as session:
            run = await session.get(ParseRun, run.id)
            if run is not None:
                run.status = "failed"
                run.finished_at = datetime.now(timezone.utc)
                run.errors_count = (run.errors_count or 0) + 1
                await session.commit()
        logger.error("Scrape timeout for site=%s after %ss", site_name, _SCRAPER_ASYNC_TIMEOUT_SEC)
        return {"site_name": site_name, "status": "failed", "reason": "timeout", "products_found": 0}
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


@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=_CELERY_SOFT_TIME_LIMIT_SEC,
    time_limit=1800,
    name="scheduler.tasks.scrape_site",
)
def scrape_site(self, site_name: str, force: bool = False, trigger_type: str = "scheduled") -> dict[str, Any]:
    try:
        return asyncio.run(_run_scrape_site(site_name, force=force, trigger_type=trigger_type))
    except SoftTimeLimitExceeded:
        asyncio.run(_mark_last_running_failed_for_site(site_name))
        raise
    except Exception as error:
        raise self.retry(exc=error, countdown=60)


@app.task(bind=True, name="scheduler.tasks.scrape_all_sites")
def scrape_all_sites(self, force: bool = False, trigger_type: str = "scheduled") -> dict[str, Any]:
    async def _get_site_names_to_scrape() -> list[str]:
        runtime = await get_runtime_settings()
        parse_interval_hours = int(runtime["parsing"]["parse_interval_hours"])
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            sites = list(await session.scalars(select(Site).where(Site.is_active.is_(True)).order_by(Site.name.asc())))
            if force:
                return [site.name for site in sites]
            names: list[str] = []
            for site in sites:
                last_started = await session.scalar(
                    select(ParseRun.started_at)
                    .where(ParseRun.site_id == site.id, ParseRun.status == "success")
                    .order_by(ParseRun.started_at.desc())
                    .limit(1)
                )
                if last_started is None:
                    names.append(site.name)
                    continue
                elapsed = now - last_started
                if elapsed >= timedelta(hours=max(parse_interval_hours, 1)):
                    names.append(site.name)
            return names

    names = asyncio.run(_get_site_names_to_scrape())
    if not names:
        return {"group_id": None, "sites_count": 0, "sites": [], "status": "no_sites_due"}

    task_group = group(scrape_site.s(name, force, trigger_type) for name in names)
    result = chord(task_group)(analyze_prices_task.s())
    return {"group_id": result.id, "sites_count": len(names), "sites": names}


@app.task(bind=True, name="scheduler.tasks.analyze_prices")
def analyze_prices(self) -> dict[str, Any]:
    async def _analyze() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            changed_prices = await session.scalar(
                select(func.count(Alert.id)).where(Alert.alert_type.in_(["price_drop", "price_rise", "price_changed"]))
            )
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
                        select(Alert.product_id).where(Alert.alert_type.in_(["price_drop", "price_rise", "price_changed"])).distinct()
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
                    _ = float(result.trend_stats.get("price_change_7d_pct", 0))
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
        runtime = await get_runtime_settings()
        alert_cfg = runtime["alerts"]
        if not alert_cfg.get("enabled", True):
            return {"pending": 0, "sent": 0, "skipped": 0, "reason": "alerts_disabled"}

        min_change_pct = Decimal(str(alert_cfg.get("min_change_pct", settings.PRICE_ALERT_THRESHOLD_PCT)))
        send_price_drop = bool(alert_cfg.get("send_price_drop", True))
        send_price_rise = bool(alert_cfg.get("send_price_rise", True))

        async with AsyncSessionLocal() as session:
            alerts = list(
                await session.scalars(
                    select(Alert)
                    .join(Product, Product.id == Alert.product_id)
                    .join(Site, Site.id == Product.site_id)
                    .where(Alert.sent_at.is_(None))
                    .where(Site.is_active.is_(True))
                    .order_by(Alert.triggered_at.asc())
                    .limit(50)
                )
            )
            sent = 0
            skipped = 0
            for alert in alerts:
                product = await session.get(Product, alert.product_id)
                if product is None:
                    alert.sent_at = datetime.now(timezone.utc)
                    skipped += 1
                    continue
                alert.product = product
                if alert.alert_type not in PRICE_ALERT_TYPES:
                    alert.sent_at = datetime.now(timezone.utc)
                    skipped += 1
                    continue
                if alert.alert_type == "price_drop" and not send_price_drop:
                    alert.sent_at = datetime.now(timezone.utc)
                    skipped += 1
                    continue
                if alert.alert_type == "price_rise" and not send_price_rise:
                    alert.sent_at = datetime.now(timezone.utc)
                    skipped += 1
                    continue
                try:
                    old_v = Decimal(str(alert.old_value or "0"))
                    new_v = Decimal(str(alert.new_value or "0"))
                except (InvalidOperation, TypeError, ValueError):
                    old_v = Decimal("0")
                    new_v = Decimal("0")
                change_pct = Decimal("0")
                if old_v > 0:
                    change_pct = (abs(new_v - old_v) / old_v) * Decimal("100")
                send_to_main = change_pct >= min_change_pct
                if send_to_main:
                    if alert.alert_type in ("price_drop", "new_low") and not send_price_drop:
                        send_to_main = False
                    elif alert.alert_type == "price_rise" and not send_price_rise:
                        send_to_main = False
                try:
                    ok = await send_alert(alert, send_to_main=send_to_main)
                except RetryAfter as error:
                    logger.warning("Telegram flood control, retry_after=%s sec", getattr(error, "retry_after", None))
                    break
                except Exception as error:
                    logger.exception("send_alert_failed alert_id=%s type=%s error=%s", alert.id, alert.alert_type, type(error).__name__)
                    continue
                if ok:
                    alert.sent_at = datetime.now(timezone.utc)
                    sent += 1
            await session.commit()
        return {"pending": len(alerts), "sent": sent, "skipped": skipped}

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

        prune_cutoff = now - timedelta(days=max(int(settings.PRUNE_PRODUCTS_INACTIVE_DAYS), 30))
        async with AsyncSessionLocal() as session:
            had_in_stock_recently = exists(
                select(1).where(
                    PriceHistory.product_id == Product.id,
                    PriceHistory.in_stock.is_(True),
                    PriceHistory.scraped_at >= prune_cutoff,
                )
            )
            has_any_history = exists(select(1).where(PriceHistory.product_id == Product.id))
            has_active_sub = exists(
                select(1).where(
                    UserSubscription.product_id == Product.id,
                    UserSubscription.is_active.is_(True),
                )
            )
            prune_result = await session.execute(
                delete(Product).where(
                    has_any_history,
                    ~had_in_stock_recently,
                    ~has_active_sub,
                )
            )
            history_result = await session.execute(
                delete(PriceHistory).where(PriceHistory.scraped_at < history_cutoff)
            )
            runs_result = await session.execute(
                delete(ParseRun).where(ParseRun.finished_at.is_not(None), ParseRun.finished_at < runs_cutoff)
            )
            await session.commit()
        return {
            "deleted_stale_products": int(prune_result.rowcount or 0),
            "deleted_price_history": int(history_result.rowcount or 0),
            "deleted_parse_runs": int(runs_result.rowcount or 0),
        }

    return asyncio.run(_cleanup())


@app.task(bind=True, name="scheduler.tasks.close_stale_parse_runs")
def close_stale_parse_runs(self) -> dict[str, int]:
    async def _close() -> dict[str, int]:
        cutoff = datetime.now(timezone.utc) - _STALE_PARSE_RUN_AFTER
        later = aliased(ParseRun)
        superseded = exists(
            select(1).where(
                later.site_id == ParseRun.site_id,
                later.status == "success",
                later.started_at > ParseRun.started_at,
            )
        )
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                update(ParseRun)
                .where(
                    ParseRun.status == "running",
                    ParseRun.finished_at.is_(None),
                    or_(ParseRun.started_at < cutoff, superseded),
                )
                .values(
                    status="failed",
                    finished_at=datetime.now(timezone.utc),
                    errors_count=func.coalesce(ParseRun.errors_count, 0) + 1,
                )
            )
            await session.commit()
        return {"closed_stale_parse_runs": int(result.rowcount or 0)}

    return asyncio.run(_close())
